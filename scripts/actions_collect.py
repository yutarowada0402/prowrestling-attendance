"""No shell interpolation of workflow_dispatch inputs."""

import json
import os
import subprocess
from datetime import date
from pathlib import Path

from prowrestling_data.storage import atomic, dumps

mode = os.environ.get("COLLECT_MODE", "update")
limit = int(os.environ.get("COLLECT_LIMIT", "100"))
if not 0 <= limit <= 500:
    raise ValueError("limit must be 0..500")
source = os.environ.get("COLLECT_SOURCE", "all")
if source not in ("all", "noah", "njpw", "ajpw"):
    raise ValueError("Unknown source")
args = ["uv", "run", "--frozen", "wrestling", mode, "--limit", str(limit)]
if mode == "collect":
    start = date.fromisoformat(os.environ["COLLECT_FROM"])
    end = date.fromisoformat(os.environ["COLLECT_TO"])
    if start > end or (end - start).days > 366:
        raise ValueError("Backfill must be <= 367 days and ordered")
    args.extend(["--from", str(start), "--to", str(end)])
elif mode == "update":
    args.extend(["--lookback-days", "30"])
else:
    raise ValueError("Unknown collection mode")
with open("var/collect.log", "w") as log:
    reports, codes = [], []
    for item in ["noah", "njpw", "ajpw"] if source == "all" else [source]:
        result = subprocess.run([*args, "--source", item], stdout=log, stderr=subprocess.STDOUT)
        codes.append(result.returncode)
        reports.append(json.loads(Path("var/run-summary.json").read_text()))
combined = {
    key: sum(r.get(key, 0) for r in reports)
    for key in ("discovered", "fetched", "changed", "unchanged", "failed", "unpublished", "conflicts")
}
combined.update(
    source=source,
    date_from=reports[0].get("date_from"),
    date_to=reports[0].get("date_to"),
    status="partial"
    if any(codes) or any(r.get("status") != "listing_complete" for r in reports)
    else "listing_complete",
    source_reports=reports,
    failures=[e for r in reports for e in r.get("failures", [])],
    listing_failures=[e for r in reports for e in r.get("listing_failures", [])],
)
atomic(Path("var/run-summary.json"), dumps(combined) + "\n")
raise SystemExit(max(codes))
