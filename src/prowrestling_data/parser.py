"""NOAH selectors verified against official HTML on 2026-11-14."""

import re
import unicodedata
from datetime import date
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

PARSER_VERSION = "noah-1"


def normalize_url(url, base="https://www.noah.co.jp"):
    p = urlsplit(urljoin(base, url))
    if p.hostname != "www.noah.co.jp" or p.username or p.port:
        raise ValueError("Unexpected source host")
    return urlunsplit(("https", p.hostname, p.path.rstrip("/") + "/", "", ""))


def attendance(raw):
    if raw is None or not raw.strip():
        return None, "unknown", None
    s = unicodedata.normalize("NFKC", raw).strip()
    if re.search(r"(?:無観客|観衆\s*0\s*人|^0\s*人)", s):
        return 0, "explicitly_zero", s
    m = re.search(r"(?<![\d.])([\d,]+)(?:万([\d,]*))?\s*人", s)
    if not m:
        return None, "unknown", s
    n = int(m[1].replace(",", ""))
    if m[2] is not None:
        n = n * 10000 + int(m[2].replace(",", "") or "0")
    if n == 0:
        return 0, "explicitly_zero", s
    return n, "reported", (s[: m.start()] + s[m.end() :]).strip() or None


def fields(node):
    return {dt.get_text(strip=True): dt.find_next_sibling("dd") for dt in node.find_all("dt")}


def text(node):
    return node.get_text(" ", strip=True) if node else None


def parse_date(value):
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", value or "")
    if not m:
        raise ValueError("event_date_missing: 日程 must contain the event date")
    return date(*map(int, m.groups())).isoformat()


def listing(html, base):
    soup = BeautifulSoup(html, "html.parser")
    events = {}
    for article in soup.select("article.c-schedule-item"):
        a = article.select_one('a[href*="/schedule/"]')
        if not a:
            continue
        f = fields(article)
        url = normalize_url(a["href"], base)
        events[url] = {
            "url": url,
            "event_date": parse_date(text(f.get("日程"))),
            "discovered_as": "result" if "/result/" in base else "schedule",
        }
    if not events:
        raise ValueError("listing_structure_changed: no dated event links")
    pages = []
    for a in soup.select('a[rel="next"], .pager a[href], .pagination a[href]'):
        u = urljoin(base, a["href"])
        if urlsplit(u).hostname == "www.noah.co.jp" and urlsplit(u).path == urlsplit(base).path:
            pages.append(u.split("#")[0])
    years = [int(o["value"]) for o in soup.select("select.yearselect option[value]") if o["value"].isdigit()]
    return list(events.values()), sorted(set(pages)), years


def parse_event(html, url, today=None, discovered_as="result"):
    soup = BeautifulSoup(html, "html.parser")
    block = soup.select_one("dl.desc-list")
    if not block:
        raise ValueError("detail_structure_changed: dl.desc-list absent")
    f = fields(block)
    d = parse_date(text(f.get("日程")))
    raw = text(f.get("観衆"))
    n, status, note = attendance(raw)
    start = re.search(r"(?<!\d)([0-2]?\d):([0-5]\d)", text(f.get("開始")) or "")
    time_value = f"{int(start[1]):02}:{start[2]}" if start and int(start[1]) < 24 else None
    title = block.find_parent("dd").find_previous_sibling("dt")
    name = text(title)
    venue = text(f.get("会場"))
    if not venue or not name:
        raise ValueError("event_identity_missing")
    # Domestic attribution needs an explicit Japanese region, never assume from promotion.
    regions = [
        "北海道",
        "青森",
        "岩手",
        "宮城",
        "秋田",
        "山形",
        "福島",
        "茨城",
        "栃木",
        "群馬",
        "埼玉",
        "千葉",
        "東京",
        "神奈川",
        "新潟",
        "富山",
        "石川",
        "福井",
        "山梨",
        "長野",
        "岐阜",
        "静岡",
        "愛知",
        "三重",
        "滋賀",
        "京都",
        "大阪",
        "兵庫",
        "奈良",
        "和歌山",
        "鳥取",
        "島根",
        "岡山",
        "広島",
        "山口",
        "徳島",
        "香川",
        "愛媛",
        "高知",
        "福岡",
        "佐賀",
        "長崎",
        "熊本",
        "大分",
        "宮崎",
        "鹿児島",
        "沖縄",
    ]
    domestic = any(venue.startswith(r) for r in regions)
    now = (today or date.today()).isoformat()
    held = d <= now and (discovered_as == "result" or n is not None)
    event_status = "held" if held else "scheduled" if d > now else "unknown"
    # Only explicit event-title declarations override status; body can mention other events.
    if re.search(r"(?:大会中止|開催中止|【中止】)", name):
        event_status = "cancelled"
    elif re.search(r"(?:開催延期|【延期】)", name):
        event_status = "postponed"
    warnings = []
    if not time_value:
        warnings.append("start_time_unknown")
    if raw and n is None:
        warnings.append("attendance_numeric_unknown")
    if not domestic:
        warnings.append("country_unclassified")
    return {
        "source": "noah",
        "source_event_id": urlsplit(normalize_url(url)).path.split("/")[-2],
        "source_url": normalize_url(url),
        "event_date": d,
        "start_time": time_value,
        "timezone": "Asia/Tokyo" if domestic else None,
        "country_code": "JP" if domestic else None,
        "promotion_raw": "プロレスリング・ノア",
        "event_name_raw": name,
        "venue_raw": venue,
        "attendance_raw": raw,
        "attendance_reported": n,
        "attendance_status": status,
        "attendance_note": note,
        "event_status": event_status,
        "extraction_warnings": warnings,
    }
