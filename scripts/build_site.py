"""Build a self-contained static GitHub Pages artifact from factual exports only."""

import json
import shutil
from pathlib import Path

from prowrestling_data.storage import atomic, dumps

root = Path(__file__).resolve().parents[1]
out = root / "dist"
out.mkdir(exist_ok=True)
for p in (root / "site").iterdir():
    if p.is_file():
        shutil.copyfile(p, out / p.name)
(out / "data").mkdir(exist_ok=True)
for name in ("events.json", "events.csv", "coverage.json", "attendance_monthly.csv", "attendance_yearly.csv"):
    shutil.copyfile(root / "exports" / name, out / "data" / name)
checks = [
    json.loads(p.read_text()).get("checked_at") for p in (root / "data/coverage").glob("*/latest_run.json")
]
atomic(
    out / "data/manifest.json",
    dumps(
        {
            "last_checked_at": max([c for c in checks if c], default=None),
            "sources": ["noah", "njpw", "ajpw"],
            "data_basis": "official_reported_attendance",
            "license": "source rights reserved; reuse permission unconfirmed",
        }
    )
    + "\n",
)
(out / ".nojekyll").touch()
assert (out / "index.html").exists()
print(f"Static Pages artifact: {out}")
