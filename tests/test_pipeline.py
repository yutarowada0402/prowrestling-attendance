import json
from datetime import date
from pathlib import Path

import duckdb
import httpx

from prowrestling_data.build import build, export
from prowrestling_data.collect import run
from prowrestling_data.parser import parse_event
from prowrestling_data.storage import atomic, dumps, observations, save_observation

URL = "https://www.noah.co.jp/schedule/900001/"


def test_unclassified_venue_with_different_country_evidence(root, html):
    event = {**parse_event(html, URL), "venue_raw": "合成未登録会場", "country_code": None}
    save_observation(root, event, html, "2026-01-01T00:00:00Z")
    second = {
        **event,
        "source_event_id": "900002",
        "source_url": URL.replace("900001", "900002"),
        "country_code": "JP",
    }
    save_observation(root, second, html, "2026-01-02T00:00:00Z")
    build(root)
    with duckdb.connect(str(root / "var/attendance.duckdb")) as con:
        assert (
            con.execute("select count(*) from dim_venues where display_name='合成未登録会場'").fetchone()[0]
            == 1
        )


def test_history_rebuild_overrides_and_aggregates(root, html):
    event = parse_event(html, URL)
    oid, changed = save_observation(root, event, html, "2026-01-01T00:00:00Z")
    assert changed
    assert save_observation(root, event, html + "<!-- ad -->")[1] is False
    corrected = {**event, "attendance_reported": 1500, "attendance_raw": "1,500人"}
    save_observation(root, corrected, html, "2026-01-02T00:00:00Z")
    night = {
        **event,
        "source_event_id": "900002",
        "source_url": URL.replace("900001", "900002"),
        "start_time": "20:30",
        "attendance_raw": None,
        "attendance_reported": None,
        "attendance_status": "unknown",
    }
    save_observation(root, night, html, "2026-01-02T01:00:00Z")
    # A second source ID is the same joint event only by explicit override.
    joint = {
        **event,
        "source_event_id": "900003",
        "source_url": URL.replace("900001", "900003"),
        "attendance_reported": 1500,
    }
    save_observation(root, joint, html, "2026-01-03T00:00:00Z")
    override = root / "data/overrides/events.csv"
    atomic(
        override,
        override.read_text()
        + "noah,900003,evt_noah_900001,noah,noah|guest,,,,,synthetic joint event merge\n",
    )
    build(root)
    export(root)
    with duckdb.connect(str(root / "var/attendance.duckdb")) as c:
        assert c.execute("select count(*) from fct_events").fetchone()[0] == 2
        assert c.execute(
            "select events_held,attendance_known,attendance_total,attendance_mean,attendance_known_rate from attendance_monthly"
        ).fetchone() == (2, 1, 1500, 1500, 0.5)
        assert (
            c.execute(
                "select count(*) from bridge_event_promotions where event_id='evt_noah_900001'"
            ).fetchone()[0]
            == 2
        )
        assert c.execute("select count(*) from merge_candidates").fetchone()[0] == 1
    exported = (root / "exports/events.json").read_bytes()
    # Rebuild from tracked history and overrides; identical exports with no network.
    build(root)
    export(root)
    assert (root / "exports/events.json").read_bytes() == exported
    assert len(observations(root)) == 4
    # A later blank must not silently delete the official figure.
    blank = {**corrected, "attendance_reported": None, "attendance_raw": None, "attendance_status": "unknown"}
    save_observation(root, blank, html, "2026-01-04T00:00:00Z")
    build(root)
    with duckdb.connect(str(root / "var/attendance.duckdb")) as c:
        assert c.execute(
            "select attendance_reported,attendance_disappeared,conflict_flag from fct_events where event_id='evt_noah_900001'"
        ).fetchone() == (1500, True, True)


class FakeFetcher:
    def __init__(self, html, fail=False):
        self.html, self.fail = html, fail

    def check_robots(self, base):
        return "synthetic robots check"

    def get(self, url):
        if "/result/" in url:
            body = (Path(__file__).parent / "fixtures/synthetic_listing.html").read_text()
        elif url.endswith("900002/") and self.fail == "403":
            from prowrestling_data.http import SourceStopped

            raise SourceStopped("HTTP 403: synthetic source stop")
        elif url.endswith("900002/") and self.fail:
            body = "<html>malformed</html>"
        else:
            body = self.html
        return httpx.Response(200, text=body, request=httpx.Request("GET", url))


def test_partial_failure_preserves_previous_and_dry_run(root, html):
    start, end = date(2025, 1, 1), date(2025, 12, 31)
    result = run(root, "noah", start, end, fetcher=FakeFetcher(html))
    assert result["changed"] == 2
    before = observations(root)
    result = run(root, "noah", start, end, fetcher=FakeFetcher(html, fail=True))
    assert result["failed"] == 1 and result["unchanged"] == 1
    assert observations(root) == before
    assert result["status"] == "partial"
    state = json.loads((root / "data/state/noah.json").read_text())
    assert state["urls"][URL.replace("900001", "900002")]["error"]
    tracked = {str(p): p.read_bytes() for p in (root / "data").rglob("*") if p.is_file()}
    result = run(root, "noah", start, end, dry_run=True, fetcher=FakeFetcher(html))
    assert result["fetched"] == 0
    assert tracked == {str(p): p.read_bytes() for p in (root / "data").rglob("*") if p.is_file()}
    result = run(root, "noah", start, end, fetcher=FakeFetcher(html, fail="403"))
    assert result["failed"] == 1 and observations(root) == before


def test_explicit_zero_all_unknown_and_date_correction(root, html):
    event = parse_event(html, URL)
    zero = {
        **event,
        "attendance_reported": 0,
        "attendance_raw": "無観客",
        "attendance_status": "explicitly_zero",
    }
    save_observation(root, zero, html, "2026-01-01T00:00:00Z")
    unknown = {
        **event,
        "source_event_id": "900002",
        "source_url": URL.replace("900001", "900002"),
        "event_date": "2025-02-01",
        "attendance_reported": None,
        "attendance_raw": None,
        "attendance_status": "unknown",
    }
    save_observation(root, unknown, html, "2026-01-02T00:00:00Z")
    corrected = {**zero, "event_date": "2025-01-02"}
    oid, _ = save_observation(root, corrected, html, "2026-01-03T00:00:00Z")
    # Reversion to an already-observed content ID must be picked through the persisted pointer.
    original_oid, changed = save_observation(root, zero, html, "2026-01-04T00:00:00Z")
    assert not changed and original_oid != oid
    atomic(
        root / "data/state/noah.json",
        dumps(
            {"urls": {URL: {"last_observation_id": original_oid, "last_checked_at": "2026-01-04T00:00:00Z"}}}
        ),
    )
    build(root)
    with duckdb.connect(str(root / "var/attendance.duckdb")) as c:
        assert c.execute(
            "select event_id,event_date::varchar from fct_events where attendance_reported=0"
        ).fetchone() == ("evt_noah_900001", "2025-01-01")
        assert c.execute(
            "select attendance_total,attendance_mean,attendance_known_rate from attendance_monthly where month='2025-01'"
        ).fetchone() == (0, 0, 1)
        assert c.execute(
            "select attendance_total,attendance_mean,attendance_known_rate from attendance_monthly where month='2025-02'"
        ).fetchone() == (None, None, 0)
        assert c.execute("select events_held,attendance_known from attendance_overall").fetchone() == (2, 1)
