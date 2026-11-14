import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from prowrestling_data.adapters import ajpw_listing, discover_official, parse_official
from prowrestling_data.http import Fetcher


def test_ajpw_detail_and_listing():
    html = (Path(__file__).parent / "fixtures/synthetic_ajpw.html").read_text()
    row = parse_official("ajpw", html, "https://www.all-japan.co.jp/match/900001/")
    assert (row["event_date"], row["start_time"], row["attendance_reported"]) == ("2025-01-02", "11:30", 1000)
    assert row["country_code"] == "JP" and row["prefecture_raw"] == "東京都"
    listing = '<select name="years"><option value="2025">2025</option></select><section class="cont__item"><a class="cont__item__link" href="/match/900001/"><time class="cont__item__date" datetime="2025-01-02"></time></a></section><div class="wp-pagenavi"><a class="nextpostslink" href="/match/page/2/?years=2025">次</a></div>'
    events, pages, years = ajpw_listing(listing, "https://www.all-japan.co.jp/match/?years=2025")
    assert events[0]["event_date"] == "2025-01-02" and len(pages) == 1 and years == [2025]
    with pytest.raises(ValueError):
        parse_official("ajpw", "<p>changed</p>", "https://www.all-japan.co.jp/match/900001/")


def test_njpw_json_and_id_check():
    obj = {
        "post_id": 900001,
        "event_start_date": "2025-01-04T00:00:00+09:00",
        "start_time": "未定",
        "schedule_title": "合成大会",
        "venue": {"stadium_name": "テストドーム", "prefecture": "東京都"},
        "spectators": "未公表",
    }
    row = parse_official("njpw", json.dumps(obj), "https://www.njpw.co.jp/tournament/result/900001")
    assert row["attendance_reported"] is None and row["start_time"] is None
    assert row["country_code"] == "JP" and row["event_date"] == "2025-01-04"
    with pytest.raises(ValueError, match="ID mismatch"):
        parse_official("njpw", json.dumps(obj), "https://www.njpw.co.jp/tournament/result/900002")


def test_njpw_pagination_uses_published_count():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if str(request.url).endswith("search-year.json"):
            return httpx.Response(200, json=[{"year": 2025}])
        return httpx.Response(
            200,
            json={
                "all_count": 2,
                "Series": [
                    {"tournaments": [{"post_id": 900001, "event_start_date": "2025-01-04T00:00:00+09:00"}]}
                ],
            },
        )

    f = Fetcher(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _: None,
        allowed_hosts=["app.njpw.co.jp"],
    )
    events, report = discover_official(
        f, {"adapter": "njpw", "max_pages": 10}, date(2025, 1, 1), date(2025, 12, 31)
    )
    assert len(events) == 1 and len(calls) == 3 and not report["listing_failures"]
    assert events[0]["fetch_url"].endswith("/900001.json")


def test_robots_are_host_specific():
    def handler(request):
        return httpx.Response(
            200, text="User-agent: *\nDisallow: /private/" if request.url.path == "/robots.txt" else "ok"
        )

    f = Fetcher(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _: None,
        allowed_hosts=["www.njpw.co.jp", "app.njpw.co.jp"],
    )
    f.check_robots("https://www.njpw.co.jp")
    assert f.get("https://app.njpw.co.jp/private/public.json").status_code == 200
