import json
import os
from pathlib import Path

report_path = Path("var/run-summary.json")
report = json.loads(report_path.read_text()) if report_path.exists() else {"status": "failed before summary"}
quality_path = Path("exports/quality_summary.json")
if quality_path.exists():
    report["conflicts"] = json.loads(quality_path.read_text())["conflicts"]
with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
    f.write("### NOAH collection\n\n")
    for key in (
        "date_from",
        "date_to",
        "status",
        "discovered",
        "fetched",
        "changed",
        "unchanged",
        "failed",
        "unpublished",
        "conflicts",
    ):
        f.write(f"- {key}: {report.get(key, 'unavailable')}\n")
    f.write("\nCoverage describes source-list traversal, not completeness of all real-world events.\n")
    for failure in report.get("listing_failures", []) + report.get("failures", []):
        f.write(f"- Failure: {failure}\n")
