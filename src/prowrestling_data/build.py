import csv
import io
import json
import os
import subprocess

import duckdb

from .storage import atomic, dumps, observations, read_json

COLS = {
    "observation_id": "VARCHAR",
    "source": "VARCHAR",
    "source_event_id": "VARCHAR",
    "source_url": "VARCHAR",
    "first_observed_at": "VARCHAR",
    "fetched_at": "VARCHAR",
    "parser_version": "VARCHAR",
    "response_hash": "VARCHAR",
    "event_date": "VARCHAR",
    "start_time": "VARCHAR",
    "timezone": "VARCHAR",
    "country_code": "VARCHAR",
    "prefecture_raw": "VARCHAR",
    "promotion_raw": "VARCHAR",
    "event_name_raw": "VARCHAR",
    "venue_raw": "VARCHAR",
    "attendance_raw": "VARCHAR",
    "attendance_reported": "BIGINT",
    "attendance_status": "VARCHAR",
    "attendance_note": "VARCHAR",
    "event_status": "VARCHAR",
    "extraction_warnings": "VARCHAR",
}
OVERRIDE_COLS = [
    "source",
    "source_event_id",
    "event_id",
    "primary_promotion_id",
    "promotion_ids",
    "event_date",
    "event_status",
    "venue_id",
    "attendance_reported",
    "reason",
]


def load(root):
    (root / "var").mkdir(exist_ok=True)
    con = duckdb.connect(str(root / "var/attendance.duckdb"))
    con.execute(
        "create or replace table raw_observations (" + ",".join(f'"{k}" {t}' for k, t in COLS.items()) + ")"
    )
    rows = observations(root)
    mapping_path = root / "data/mappings/event_ids.csv"
    mappings = {}
    if mapping_path.exists():
        for row in csv.DictReader(mapping_path.open()):
            key = (row["source"], row["source_event_id"])
            if key in mappings:
                raise ValueError("Duplicate source event ID in permanent mapping")
            mappings[key] = row["event_id"]
    for row in rows:
        key = (row["source"], row["source_event_id"])
        mappings.setdefault(key, f"evt_{key[0]}_{key[1]}")
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["source", "source_event_id", "event_id"])
    writer.writerows([*key, value] for key, value in sorted(mappings.items()))
    atomic(mapping_path, out.getvalue())
    con.execute(
        "create or replace table raw_event_ids (source varchar, source_event_id varchar, event_id varchar)"
    )
    for key, value in mappings.items():
        con.execute("insert into raw_event_ids values (?, ?, ?)", [*key, value])
    for row in rows:
        values = [dumps(row.get(c, [])) if c == "extraction_warnings" else row.get(c) for c in COLS]
        con.execute("insert into raw_observations values (" + ",".join("?" for _ in COLS) + ")", values)
    con.execute(
        "create or replace table raw_checks (source_url varchar, observation_id varchar, checked_at varchar)"
    )
    for path in sorted((root / "data/state").glob("*.json")):
        for url, item in read_json(path, {"urls": {}})["urls"].items():
            if item.get("last_observation_id"):
                con.execute(
                    "insert into raw_checks values (?, ?, ?)",
                    [url, item["last_observation_id"], item.get("last_checked_at")],
                )
    con.execute(
        "create or replace table raw_overrides (" + ",".join(f'"{c}" varchar' for c in OVERRIDE_COLS) + ")"
    )
    path = root / "data/overrides/events.csv"
    if path.exists():
        for row in csv.DictReader(path.open()):
            if not row.get("reason"):
                raise ValueError("Override requires reason")
            con.execute(
                "insert into raw_overrides values (" + ",".join("?" for _ in OVERRIDE_COLS) + ")",
                [row.get(c) or None for c in OVERRIDE_COLS],
            )
    # Every source ID has a permanent, date-independent default ID. Overrides are persistent mappings.
    for name, columns in {
        "promotions": ["promotion_id", "display_name"],
        "promotion_aliases": ["alias", "promotion_id"],
        "venues": ["venue_id", "display_name", "country_code", "prefecture", "city"],
        "venue_aliases": ["alias", "venue_id"],
    }.items():
        con.execute(
            f"create or replace table raw_{name} (" + ",".join(f'"{c}" varchar' for c in columns) + ")"
        )
        path = root / f"data/seeds/{name}.csv"
        for row in csv.DictReader(path.open()):
            con.execute(
                f"insert into raw_{name} values (" + ",".join("?" for _ in columns) + ")",
                [row.get(c) or None for c in columns],
            )
    coverage = [json.loads(p.read_text()) for p in sorted((root / "data/coverage").glob("*/????-??.json"))]
    con.execute(
        "create or replace table raw_coverage (source varchar, month varchar, status varchar, discovered bigint, collected bigint, failed bigint)"
    )
    for row in coverage:
        con.execute(
            "insert into raw_coverage values (?, ?, ?, ?, ?, ?)",
            [row[c] for c in ("source", "month", "status", "discovered", "collected", "failed")],
        )
    con.close()


def build(root):
    load(root)
    env = {**os.environ, "WRESTLING_DB_PATH": str(root / "var/attendance.duckdb")}
    subprocess.run(
        ["dbt", "build", "--project-dir", str(root / "dbt"), "--profiles-dir", str(root / "dbt")],
        check=True,
        cwd=root,
        env=env,
    )
    validate(root)


def validate(root):
    with duckdb.connect(str(root / "var/attendance.duckdb"), read_only=True) as con:
        bad = con.execute(
            "select count(*) from fct_events where event_id is null or event_date is null or attendance_reported < 0"
        ).fetchone()[0]
        duplicates = con.execute("select count(*)-count(distinct event_id) from fct_events").fetchone()[0]
        if bad or duplicates:
            raise ValueError(f"Quality failure: invalid={bad}, duplicate={duplicates}")
    print("Quality validation passed")


def records(con, sql):
    cursor = con.execute(sql)
    names = [c[0] for c in cursor.description]
    return [
        {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in zip(names, row, strict=False)}
        for row in cursor.fetchall()
    ]


def export(root):
    validate(root)
    with duckdb.connect(str(root / "var/attendance.duckdb"), read_only=True) as con:
        for output, model in [
            ("events", "fct_events"),
            ("attendance_monthly", "attendance_monthly"),
            ("attendance_yearly", "attendance_yearly"),
            ("attendance_overall", "attendance_overall"),
            ("attendance_by_venue", "attendance_by_venue"),
            ("attendance_by_weekday", "attendance_by_weekday"),
            ("attendance_by_region", "attendance_by_region"),
            ("attendance_ytd", "attendance_ytd"),
            ("attendance_copromoted_reference", "attendance_copromoted_reference"),
            ("coverage", "period_coverage"),
            ("merge_candidates", "merge_candidates"),
        ]:
            rows = records(con, f"select * from {model} order by all")
            names = [d[0] for d in con.execute(f"select * from {model} limit 0").description]
            out = io.StringIO(newline="")
            writer = csv.DictWriter(out, fieldnames=names, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            atomic(root / f"exports/{output}.csv", out.getvalue())
            atomic(root / f"exports/{output}.json", dumps(rows) + "\n")
        quality = records(con, "select * from data_quality")[0]
        quality["coverage"] = records(con, "select * from period_coverage order by source, month")
        quality["definition"] = (
            "Domestic held primary-promotion events; reported attendance is not unique people or sales"
        )
        atomic(root / "exports/quality_summary.json", dumps(quality) + "\n")
    print(dumps(quality))
