import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedupe_key TEXT UNIQUE NOT NULL,
    title TEXT,
    procuring_entity TEXT,
    tender_reference TEXT,
    procurement_type TEXT,
    opportunity_category TEXT,
    sector TEXT,
    deadline TEXT,
    publication_date TEXT,
    source_platform TEXT,
    source_group TEXT,
    source_website TEXT,
    original_link TEXT,
    document_links TEXT,
    ppp_flag INTEGER,
    newspaper_flag INTEGER,
    social_signal_flag INTEGER,
    donor_funded_flag INTEGER,
    manual_review_flag INTEGER,
    relevance_score INTEGER,
    priority TEXT,
    recommendation_reason TEXT,
    raw_text_summary TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
);
"""


FIELDS = [
    "title", "procuring_entity", "tender_reference", "procurement_type",
    "opportunity_category", "sector", "deadline", "publication_date",
    "source_platform", "source_group", "source_website", "original_link", "document_links",
    "ppp_flag", "newspaper_flag", "social_signal_flag", "donor_funded_flag",
    "manual_review_flag", "relevance_score", "priority", "recommendation_reason", "raw_text_summary",
]


def init_db(path: str) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(SCHEMA)
        _ensure_columns(conn)
        conn.commit()
        return conn
    except sqlite3.OperationalError as exc:
        conn.close()
        if "readonly" not in str(exc).lower():
            raise
        fallback_path = db_path.with_name(f"{db_path.stem}_writable{db_path.suffix}")
        if fallback_path.exists():
            os.chmod(str(fallback_path), 0o666)
            fallback_path.unlink()
        conn = sqlite3.connect(str(fallback_path))
        conn.row_factory = sqlite3.Row
        conn.execute(SCHEMA)
        _ensure_columns(conn)
        conn.commit()
        return conn


def _ensure_columns(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(opportunities)").fetchall()}
    additions = {
        "source_group": "TEXT",
        "manual_review_flag": "INTEGER",
    }
    for column, column_type in additions.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE opportunities ADD COLUMN {column} {column_type}")


def dedupe_key(item: Dict) -> str:
    parts = [
        item.get("tender_reference") or "",
        item.get("title") or "",
        item.get("procuring_entity") or "",
        item.get("deadline") or "",
        item.get("original_link") or "",
    ]
    normalized = "|".join(str(part).strip().lower() for part in parts if part is not None)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_item(item: Dict) -> Dict:
    normalized = {field: item.get(field) for field in FIELDS}
    normalized["title"] = normalized.get("title") or "Untitled opportunity signal"
    normalized["document_links"] = json.dumps(normalized.get("document_links") or [], ensure_ascii=False)
    for flag in ("ppp_flag", "newspaper_flag", "social_signal_flag", "donor_funded_flag", "manual_review_flag"):
        normalized[flag] = 1 if normalized.get(flag) else 0
    normalized["relevance_score"] = int(normalized.get("relevance_score") or 0)
    return normalized


def upsert_opportunities(conn: sqlite3.Connection, items: Iterable[Dict]) -> Tuple[List[Dict], int]:
    new_items: List[Dict] = []
    duplicate_count = 0
    now = datetime.now(timezone.utc).isoformat()

    for item in items:
        row = normalize_item(item)
        row["dedupe_key"] = dedupe_key(row)
        row["first_seen"] = now
        row["last_seen"] = now

        columns = ["dedupe_key"] + FIELDS + ["first_seen", "last_seen"]
        placeholders = ", ".join("?" for _ in columns)
        values = [row.get(column) for column in columns]
        try:
            conn.execute(
                f"INSERT INTO opportunities ({', '.join(columns)}) VALUES ({placeholders})",
                values,
            )
            saved = dict(row)
            saved["document_links"] = json.loads(saved.get("document_links") or "[]")
            new_items.append(saved)
        except sqlite3.IntegrityError:
            duplicate_count += 1
            conn.execute(
                "UPDATE opportunities SET last_seen = ? WHERE dedupe_key = ?",
                (now, row["dedupe_key"]),
            )
    conn.commit()
    return new_items, duplicate_count


def fetch_recent(conn: sqlite3.Connection, limit: int = 100) -> List[Dict]:
    rows = conn.execute(
        "SELECT * FROM opportunities ORDER BY first_seen DESC LIMIT ?",
        (limit,),
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["document_links"] = json.loads(item.get("document_links") or "[]")
        result.append(item)
    return result
