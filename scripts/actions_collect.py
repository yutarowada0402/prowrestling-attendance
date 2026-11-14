"""No shell interpolation of workflow_dispatch inputs."""

import os
import subprocess
from datetime import date

mode = os.environ.get("COLLECT_MODE", "update")
limit = int(os.environ.get("COLLECT_LIMIT", "100"))
if not 0 <= limit <= 500:
    raise ValueError("limit must be 0..500")
args = ["uv", "run", "--frozen", "wrestling", mode, "--source", "noah", "--limit", str(limit)]
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
    result = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT)
raise SystemExit(result.returncode)
