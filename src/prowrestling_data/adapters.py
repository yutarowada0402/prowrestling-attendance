"""Official AJPW HTML and NJPW public SPA JSON; verified 2026-11-14.

NJPW endpoints are observed frontend resources, not a documented public API.
"""

import json
import re
from datetime import date, datetime
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from .http import SourceStopped
from .parser import attendance, parse_date, text

REGIONS = "北海道 青森 岩手 宮城 秋田 山形 福島 茨城 栃木 群馬 埼玉 千葉 東京 神奈川 新潟 富山 石川 福井 山梨 長野 岐阜 静岡 愛知 三重 滋賀 京都 大阪 兵庫 奈良 和歌山 鳥取 島根 岡山 広島 山口 徳島 香川 愛媛 高知 福岡 佐賀 長崎 熊本 大分 宮崎 鹿児島 沖縄".split()


def canonical(url, host):
    p = urlsplit(url)
    if p.hostname != host or p.username or p.port:
        raise ValueError("Unexpected source URL")
    return f"https://{host}" + p.path.rstrip("/") + ("/" if host.endswith("all-japan.co.jp") else "")


def ajpw_listing(html, url):
    soup = BeautifulSoup(html, "html.parser")
    events = []
    for a in soup.select("section.cont__item a.cont__item__link[href]"):
        t = a.select_one("time.cont__item__date[datetime]")
        if not t:
            raise ValueError("AJPW event date missing in listing")
        d = date.fromisoformat(t["datetime"][:10]).isoformat()
        u = canonical(urljoin(url, a["href"]), "www.all-japan.co.jp")
        events.append({"url": u, "event_date": d, "discovered_as": "result"})
    if not events:
        raise ValueError("AJPW listing structure changed / empty year")
    pages = [urljoin(url, a["href"]) for a in soup.select(".wp-pagenavi a.nextpostslink[href]")]
    if any(urlsplit(p).hostname != "www.all-japan.co.jp" for p in pages):
        raise ValueError("Unexpected pagination host")
    years = [int(o["value"]) for o in soup.select("select[name=years] option[value]") if o["value"].isdigit()]
    return events, pages, years


def discover_official(fetcher, config, start, end):
    source = config["adapter"]
    visited, failures, events = [], [], {}
    years = []
    cap = config["max_pages"]
    if source == "njpw":
        root = "https://app.njpw.co.jp/series/tournaments/results/"
        year_url = root + "search-year.json"
        try:
            years = [int(r["year"]) for r in fetcher.get(year_url).json()]
            visited.append(year_url)
        except Exception as e:
            failures.append({"url": year_url, "error": str(e)})
        for year in years:
            if not start.year <= year <= end.year:
                continue
            page, pages = 1, 1
            while page <= pages and len(visited) < cap:
                u = root + f"year/{year}/{page}.json"
                visited.append(u)
                try:
                    data = fetcher.get(u).json()
                    pages = int(data["all_count"])
                    for series in data["Series"]:
                        for item in series["tournaments"]:
                            d = date.fromisoformat(item["event_start_date"][:10]).isoformat()
                            sid = str(int(item["post_id"]))
                            link = f"https://www.njpw.co.jp/tournament/result/{sid}"
                            if start.isoformat() <= d <= end.isoformat():
                                events[link] = {
                                    "url": link,
                                    "event_date": d,
                                    "discovered_as": "result",
                                    "fetch_url": f"https://app.njpw.co.jp/tournament/posts/{sid}.json",
                                }
                except Exception as e:
                    failures.append({"url": u, "error": str(e)})
                    if isinstance(e, SourceStopped):
                        return sorted(events.values(), key=lambda x: (x["event_date"], x["url"])), _report(
                            visited, failures, years, start, end
                        )
                page += 1
            if page <= pages:
                failures.append({"url": str(year), "error": "max_pages reached"})
    else:
        base = config["base_url"]
        queue = [base + "/match/"]
        while queue and len(visited) < cap:
            u = queue.pop(0)
            if u in visited:
                continue
            visited.append(u)
            try:
                items, pages, options = ajpw_listing(fetcher.get(u).text, u)
                if u == base + "/match/":
                    years = options
                    queue.extend(base + f"/match/?years={y}" for y in years if start.year <= y <= end.year)
                else:
                    queue.extend(p for p in pages if p not in visited and p not in queue)
                for item in items:
                    if start.isoformat() <= item["event_date"] <= end.isoformat():
                        events[item["url"]] = item
            except Exception as e:
                failures.append({"url": u, "error": str(e)})
                if isinstance(e, SourceStopped):
                    break
        if queue:
            failures.append({"url": "listing", "error": "incomplete pagination / source stopped"})
    return sorted(events.values(), key=lambda x: (x["event_date"], x["url"])), _report(
        visited, failures, years, start, end
    )


def _report(visited, failures, years, start, end):
    return {
        "listing_pages": visited,
        "listing_failures": failures,
        "supported_year_options": sorted(years),
        "unsupported_years": [y for y in range(start.year, end.year + 1) if y not in years],
    }


def parse_official(source, raw, url, context=None):
    if source == "njpw":
        obj = json.loads(raw)
        d = date.fromisoformat(obj["event_start_date"][:10]).isoformat()
        sid = str(obj["post_id"])
        if url.rstrip("/").split("/")[-1] != sid:
            raise ValueError("NJPW detail ID mismatch")
        venue_obj = obj.get("venue") or {}
        venue = venue_obj.get("stadium_name") or obj.get("stadium_name")
        hint = str(venue_obj.get("prefecture") or "")
        name, start, att = obj.get("schedule_title"), obj.get("start_time"), obj.get("spectators")
        url = canonical(url, "www.njpw.co.jp")
    else:
        soup = BeautifulSoup(raw, "html.parser")
        f = {
            text(r.select_one("th.match__contentInfo__term")): r.select_one("td.match__contentInfo__desc")
            for r in soup.select("table.match__contentInfo__table tr.match__contentInfo__list")
        }
        if not f:
            raise ValueError("AJPW detail structure changed")
        d = parse_date(text(f.get("開催日")))
        name, start, att = (
            text(soup.select_one("h3.match__title")),
            text(f.get("開始時間")),
            text(f.get("観衆")),
        )
        venue = text(f.get("会場"))
        hint = name or ""
        url = canonical(url, "www.all-japan.co.jp")
        sid = url.rstrip("/").split("/")[-1]
    if not name or not venue:
        raise ValueError(f"{source}: event identity missing")
    name = BeautifulSoup(name, "html.parser").get_text(" ", strip=True)
    n, att_status, note = attendance(att)
    region = next(
        (
            r
            for r in REGIONS
            if venue.startswith(r) or re.search(re.escape(r) + r"(?:[都道府県]?・|[都道府県]?$)", hint)
        ),
        None,
    )
    pref = (
        (
            region
            if region == "北海道"
            else region + ("都" if region == "東京" else "府" if region in ("京都", "大阪") else "県")
        )
        if region
        else None
    )
    clock = re.search(r"(?<!\d)([0-2]?\d):([0-5]\d)", start or "")
    start_time = f"{int(clock[1]):02}:{clock[2]}" if clock and int(clock[1]) < 24 else None
    today = datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()
    status = "held" if d <= today else "scheduled"
    if re.search("開催中止|大会中止|【中止】", name):
        status = "cancelled"
    elif re.search("開催延期|【延期】", name):
        status = "postponed"
    warnings = ([] if region else ["country_unclassified"]) + ([] if start_time else ["start_time_unknown"])
    if att and n is None:
        warnings.append("attendance_numeric_unknown")
    return {
        "source": source,
        "source_event_id": sid,
        "source_url": url,
        "event_date": d,
        "start_time": start_time,
        "timezone": "Asia/Tokyo" if region else None,
        "country_code": "JP" if region else None,
        "prefecture_raw": pref,
        "promotion_raw": "新日本プロレス" if source == "njpw" else "全日本プロレス",
        "event_name_raw": name,
        "venue_raw": venue,
        "attendance_raw": att,
        "attendance_reported": n,
        "attendance_status": att_status,
        "attendance_note": note,
        "event_status": status,
        "extraction_warnings": warnings,
    }
