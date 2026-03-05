"""
Article search over extension PDF URLs stored in SQLite.
Searchable text is derived from URL path/filename (normalized).
"""

import re
import sqlite3
from pathlib import Path
from urllib.parse import urlparse


def url_to_searchable(url: str) -> str:
    path = urlparse(url).path.strip("/")
    parts = path.replace("-", " ").replace("_", " ").replace(".pdf", " ")
    return re.sub(r"\s+", " ", parts).strip().lower()


def url_to_title(url: str) -> str:
    path = urlparse(url).path
    name = path.rsplit("/", 1)[-1] if "/" in path else path
    return name.replace("_", " ").replace("-", " ").replace(".pdf", "").strip()


def search_articles(query: str, db_path: Path) -> list[dict]:
    if not query or not db_path or not db_path.exists():
        return []
    q = url_to_searchable(query)
    if not q:
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT url, searchable_text FROM articles WHERE searchable_text LIKE ?",
            ("%" + q + "%",),
        )
        rows = cur.fetchall()
        return [{"url": r["url"], "title": url_to_title(r["url"])} for r in rows]
    finally:
        conn.close()


def resolve_uploaded_link(link: str, db_path: Path) -> str:
    """
    If link is uploaded://... try to find a matching real URL in extension_articles.
    Returns real URL if one match, else original link.
    """
    if not link or not link.strip().lower().startswith("uploaded://"):
        return link or ""
    path = link.split("uploaded://", 1)[-1].strip()
    if not path:
        return link
    # Search by filename-ish: "Article_2332 (2).pdf" -> "article 2332 2"
    q = path.replace("-", " ").replace("_", " ").replace(".pdf", "").replace("(", "").replace(")", "").strip()
    q = re.sub(r"\s+", " ", q).lower()
    if not q or not db_path or not Path(db_path).exists():
        return link
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT url FROM articles WHERE searchable_text LIKE ? LIMIT 1",
            ("%" + q + "%",),
        )
        row = cur.fetchone()
        return row["url"] if row else link
    finally:
        conn.close()
