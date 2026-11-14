import gzip
from datetime import date

import yaml

from .http import Fetcher, SourceStopped
from .parser import listing, parse_event
from .storage import atomic, digest, dumps, read_json, save_observation, utcnow


def discover(fetcher, config, start, end, max_pages=None, include_schedule=False):
    base = config["base_url"]
    queue = [base + config["listing_path"]]
    visited, found, failures, supported = set(), {}, [], []
    cap = max_pages or config["max_pages"]
    while queue and len(visited) < cap:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        try:
            response = fetcher.get(url)
            events, pages, years = listing(response.text, url)
            if url == base + config["listing_path"]:
                supported = years
                queue.extend(
                    base + config["listing_path"] + f"?y={y}" for y in years if start.year <= y <= end.year
                )
                if include_schedule:
                    queue.append(base + config["schedule_path"])
            for event in events:
                if start.isoformat() <= event["event_date"] <= end.isoformat():
                    if event["url"] not in found or event["discovered_as"] == "result":
                        found[event["url"]] = event
            queue.extend(p for p in pages if p not in visited and p not in queue)
        except Exception as e:
            failures.append({"url": url, "error": str(e)})
            if isinstance(e, SourceStopped):
                break
    if queue:
        failures.append({"url": "listing", "error": "pagination incomplete / source stopped"})
    unsupported = [y for y in range(start.year, end.year + 1) if y not in supported]
    return sorted(found.values(), key=lambda e: (e["event_date"], e["url"])), {
        "listing_pages": sorted(visited),
        "listing_failures": failures,
        "supported_year_options": supported,
        "unsupported_years": unsupported,
    }


def run(
    root,
    source,
    start,
    end,
    limit=None,
    dry_run=False,
    discover_only=False,
    include_schedule=False,
    fetcher=None,
):
    cfgs = yaml.safe_load((root / "config/sources.yml").read_text())
    if source not in cfgs or not cfgs[source]["enabled"]:
        raise ValueError(f"Unsupported source: {source}")
    cfg = cfgs[source]
    fetcher = fetcher or Fetcher(cfg["min_interval"])
    robots = fetcher.check_robots(cfg["base_url"])
    events, report = discover(fetcher, cfg, start, end, include_schedule=include_schedule)
    state_path = root / "data/state" / f"{source}.json"
    state = read_json(state_path, {"urls": {}})
    # Previously discovered failures remain retryable, even when removed from a listing.
    known = {e["url"]: e for e in events}
    for url, item in state["urls"].items():
        if start.isoformat() <= item.get("event_date", "") <= end.isoformat():
            known.setdefault(
                url,
                {
                    "url": url,
                    "event_date": item["event_date"],
                    "discovered_as": item.get("discovered_as", "schedule"),
                },
            )
    events = sorted(known.values(), key=lambda e: (e["event_date"], e["url"]))
    selected = events[:limit] if limit is not None else events
    report.update(
        source=source,
        date_from=start.isoformat(),
        date_to=end.isoformat(),
        robots=robots,
        discovered=len(events),
        selected=len(selected),
        fetched=0,
        changed=0,
        unchanged=0,
        failed=0,
        unpublished=0,
        conflicts=0,
        dry_run=dry_run,
        failures=[],
    )
    if dry_run:
        return {**report, "planned_urls": selected, "note": "listing/robots HTTP only; no detail or writes"}
    for event in events:
        state["urls"].setdefault(event["url"], {}).update(event)
    if not discover_only:
        for event in selected:
            url = event["url"]
            item = state["urls"][url]
            try:
                # Full recheck intentionally avoids conditional 304 parser-version ambiguities.
                response = fetcher.get(url)
                report["fetched"] += 1
                html = response.text
                raw = root / "var/raw" / source / f"{digest(html)}.html.gz"
                raw.parent.mkdir(parents=True, exist_ok=True)
                if not raw.exists():
                    raw.write_bytes(gzip.compress(html.encode(), mtime=0))
                extracted = parse_event(html, url, discovered_as=event["discovered_as"])
                oid, changed = save_observation(root, extracted, html)
                report["changed" if changed else "unchanged"] += 1
                report["unpublished"] += int(extracted["attendance_reported"] is None)
                item.update(
                    last_checked_at=utcnow(),
                    last_observation_id=oid,
                    error=None,
                    etag=response.headers.get("etag"),
                    last_modified=response.headers.get("last-modified"),
                    event_date=extracted["event_date"],
                )
            except Exception as e:
                item.update(last_checked_at=utcnow(), error=str(e))
                report["failed"] += 1
                report["failures"].append({"url": url, "error": str(e)})
                if isinstance(e, SourceStopped):
                    break
            finally:
                # Each observation is durable before the state pointer is advanced.
                atomic(state_path, dumps(state) + "\n")
    atomic(state_path, dumps(state) + "\n")
    report["checked_at"] = utcnow()
    report["status"] = (
        "partial"
        if (
            report["listing_failures"]
            or report["failed"]
            or report["unsupported_years"]
            or discover_only
            or report["changed"] + report["unchanged"] < len(events)
        )
        else "listing_complete"
    )
    # Coverage is request-scoped: overlapping limited runs cannot claim cumulative completeness.
    for year in range(start.year, end.year + 1):
        for month in range(1, 13):
            first = date(year, month, 1)
            if first > end or (year, month) < (start.year, start.month):
                continue
            key = f"{year}-{month:02}"
            month_events = [e for e in events if e["event_date"].startswith(key)]
            errors = [e for e in month_events if state["urls"][e["url"]].get("error")]
            checked = [e for e in month_events if state["urls"][e["url"]].get("last_observation_id")]
            coverage = {
                "month": key,
                "source": source,
                "checked_at": report["checked_at"],
                "status": "unsupported"
                if year in report["unsupported_years"]
                else "partial"
                if report["listing_failures"] or errors or len(checked) != len(month_events)
                else "listing_complete",
                "discovered": len(month_events),
                "collected": len(checked),
                "failed": len(errors),
                "scope_from": start.isoformat(),
                "scope_to": end.isoformat(),
                "meaning": "checked source listing only; not all real-world events",
            }
            atomic(root / "data/coverage" / source / f"{key}.json", dumps(coverage) + "\n")
    atomic(root / "data/coverage" / source / "latest_run.json", dumps(report) + "\n")
    atomic(root / "var/run-summary.json", dumps(report) + "\n")
    return report
