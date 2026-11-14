import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def utcnow():
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(value)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def observations(root):
    return [
        json.loads(line)
        for p in sorted((root / "data/observations").glob("*/*.jsonl"))
        for line in p.read_text().splitlines()
        if line.strip()
    ]


def save_observation(root, extracted, html, timestamp=None):
    now = timestamp or utcnow()
    from .parser import PARSER_VERSION

    # Fetch metadata and ads never participate in the identity.
    oid = digest(dumps([extracted, PARSER_VERSION]))
    existing = observations(root)
    if any(o["observation_id"] == oid for o in existing):
        return oid, False
    prior = [
        o
        for o in existing
        if (o["source"], o["source_event_id"]) == (extracted["source"], extracted["source_event_id"])
    ]
    obs = {
        **extracted,
        "observation_id": oid,
        "parser_version": PARSER_VERSION,
        "first_observed_at": min([o["first_observed_at"] for o in prior] + [now]),
        "fetched_at": now,
        "response_hash": digest(html),
    }
    path = root / "data/observations" / extracted["source"] / (extracted["event_date"][:4] + ".jsonl")
    rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    rows.append(obs)
    rows.sort(key=lambda o: (o["source_event_id"], o["fetched_at"], o["observation_id"]))
    atomic(path, "".join(dumps(o) + "\n" for o in rows))
    return oid, True
