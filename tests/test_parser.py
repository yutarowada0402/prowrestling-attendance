from datetime import date
from pathlib import Path

import pytest

from prowrestling_data.parser import attendance, listing, normalize_url, parse_event


@pytest.mark.parametrize(
    "raw,n,status",
    [
        ("1,560人（札止め）", 1560, "reported"),
        ("１，２３４人（超満員）", 1234, "reported"),
        ("1万2,000人", 12000, "reported"),
        ("２万人", 20000, "reported"),
        ("満員", None, "unknown"),
        (None, None, "unknown"),
        ("未公表", None, "unknown"),
        ("無観客試合", 0, "explicitly_zero"),
        ("0人", 0, "explicitly_zero"),
    ],
)
def test_attendance(raw, n, status):
    assert attendance(raw)[:2] == (n, status)


def test_date_and_time(html):
    event = parse_event(
        html.replace("18:30", "未定"), "https://www.noah.co.jp/schedule/900001/", today=date(2026, 1, 1)
    )
    assert event["event_date"] == "2025-01-01"
    assert event["start_time"] is None
    assert event["attendance_note"] == "(札止め)"


def test_missing_date_fails(html):
    with pytest.raises(ValueError, match="event_date_missing"):
        parse_event(html.replace("2025年01月01日", "未定"), "https://www.noah.co.jp/schedule/900001/")


def test_scheduled_is_not_held(html):
    html = html.replace("<dt>観衆</dt><dd>1,234人（札止め）</dd>", "")
    event = parse_event(
        html, "https://www.noah.co.jp/schedule/900001/", today=date(2026, 1, 1), discovered_as="schedule"
    )
    assert event["event_status"] == "unknown"
    assert event["attendance_reported"] is None


def test_listing_and_normalization():
    html = (Path(__file__).parent / "fixtures/synthetic_listing.html").read_text()
    events, _, years = listing(html, "https://www.noah.co.jp/result/?y=2025")
    assert len(events) == 2
    assert years == [2025]
    assert normalize_url("http://www.noah.co.jp/schedule/900001?utm=foo#x") == events[0]["url"]
    with pytest.raises(ValueError):
        normalize_url("https://example.com/schedule/1/")
