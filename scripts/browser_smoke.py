"""Optional browser QA: uv run --with playwright python scripts/browser_smoke.py URL."""

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8877/"
out = Path("var/browser")
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    assert page.goto(url).status == 200
    page.wait_for_selector(".metric-value")
    assert page.locator("#error").is_hidden()
    assert page.locator("#monthly svg").count() == 1
    records = page.request.get(url + "data/events.json").json()
    for source in ("noah", "njpw", "ajpw"):
        page.locator("#promotion").select_option(source)
        expected = len({r["event_id"] for r in records if r["primary_promotion_id"] == source
                        and r["event_date"].startswith("2025") and r["country_code"] == "JP"
                        and r["event_status"] == "held"})
        shown = int(re.sub(r"\D", "", page.locator(".metric-value").first.inner_text()))
        assert shown == expected, (source, shown, expected)
    page.locator("#promotion").select_option("all")
    assert page.locator("#comparison .empty").count() == 1
    page.screenshot(path=str(out / "desktop.png"), full_page=True)
    page.locator("#promotion").select_option("ajpw")
    assert "全日本プロレス" in page.locator("#scope").inner_text()
    page.locator('[data-metric="mean"]').click()
    assert page.locator('[data-metric="mean"]').get_attribute("aria-pressed") == "true"
    page.locator('[data-tab="events"]').click()
    assert page.locator("#events").is_visible()
    page.locator("#search").fill("後楽園")
    assert page.locator("#event-rows tr").count() > 0
    assert "後楽園" in page.locator("#event-rows").inner_text()
    page.locator('[data-tab="coverage"]').click()
    assert page.locator("#coverage-grid table").count() == 1
    csv_url = page.locator(".download").get_attribute("href")
    assert page.request.get(url + csv_url.removeprefix("./")).status == 200
    page.locator('[data-tab="overview"]').click()
    page.locator("#promotion").select_option("all")
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(out / "mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert not errors, errors
    print(
        json.dumps(
            {
                "url": url,
                "filters": "passed",
                "tabs": "passed",
                "search": "passed",
                "csv": "passed",
                "mobile_overflow": False,
                "javascript_errors": errors,
            }
        )
    )
    browser.close()
