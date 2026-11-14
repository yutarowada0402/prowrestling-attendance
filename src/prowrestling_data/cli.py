import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .collect import run
from .storage import atomic, dumps, utcnow


def main():
    parser = argparse.ArgumentParser(description="Official wrestling attendance pipeline")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project/data root (default cwd)")
    subs = parser.add_subparsers(dest="command", required=True)
    for command in ("discover", "collect", "update"):
        p = subs.add_parser(command)
        p.add_argument("--source", choices=["noah", "njpw", "ajpw"], default="noah")
        p.add_argument("--from", dest="start", type=date.fromisoformat)
        p.add_argument("--to", dest="end", type=date.fromisoformat)
        p.add_argument("--limit", type=int, help="Maximum detail requests; discovery still checks listings")
        p.add_argument(
            "--retry-failed",
            action="store_true",
            help="Recheck listings, then fetch only URLs with saved failures",
        )
        p.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch robots/listings to discover URLs; no details or file writes",
        )
        if command == "update":
            p.add_argument("--lookback-days", type=int, default=30)
    for command in ("build", "export", "validate"):
        subs.add_parser(command)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command in ("build", "export", "validate"):
        from .build import build, export, validate

        {"build": build, "export": export, "validate": validate}[args.command](root)
        return
    today = datetime.now(ZoneInfo("Asia/Tokyo")).date()
    if args.command == "update":
        if args.lookback_days < 1:
            parser.error("lookback-days must be positive")
        args.start = args.start or today - timedelta(days=args.lookback_days - 1)
        args.end = args.end or today
    if not args.start or not args.end or args.start > args.end:
        parser.error("valid --from and --to required")
    if args.limit is not None and args.limit < 0:
        parser.error("limit must be nonnegative")
    try:
        report = run(
            root,
            args.source,
            args.start,
            args.end,
            args.limit,
            args.dry_run,
            args.command == "discover",
            args.command == "update",
            retry_failed=args.retry_failed,
        )
    except Exception as e:
        if not args.dry_run:
            atomic(
                root / "var/run-summary.json",
                dumps(
                    {
                        "source": args.source,
                        "date_from": str(args.start),
                        "date_to": str(args.end),
                        "status": "failed",
                        "checked_at": utcnow(),
                        "failures": [{"url": "preflight", "error": str(e)}],
                        "failed": 1,
                    }
                )
                + "\n",
            )
        parser.exit(1, f"Collection failed before completion: {e}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["failed"] or report["listing_failures"] or report["unsupported_years"]:
        raise SystemExit(2)
