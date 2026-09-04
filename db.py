"""
db.py — Local SQLite storage for tracked jobs.
100% free, no account, no internet needed to read/write.
Lives at data/jobs.db
"""
import sqlite3
import os
import hashlib
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "jobs.db")


def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,       -- hash of title+company+url, used to dedupe
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT,
            source TEXT,
            found_at TEXT,
            status TEXT DEFAULT 'new', -- new | sent | applied | reminded | ignored
            applied_at TEXT,
            reminded_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def make_job_id(title, company, url):
    raw = f"{title}|{company}|{url}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def add_job(title, company, location, url, source):
    conn = _connect()
    job_id = make_job_id(title, company, url)
    try:
        conn.execute(
            """INSERT INTO jobs (id, title, company, location, url, source, found_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'new')""",
            (job_id, title, company, location, url, source, datetime.now().isoformat()),
        )
        conn.commit()
        inserted = True
    except sqlite3.IntegrityError:
        inserted = False  # already have this job
    conn.close()
    return inserted


def get_new_jobs():
    conn = _connect()
    rows = conn.execute("SELECT * FROM jobs WHERE status = 'new' ORDER BY found_at DESC").fetchall()
    conn.close()
    return rows


def mark_status(job_id, status, extra_field=None):
    conn = _connect()
    if extra_field == "applied_at":
        conn.execute("UPDATE jobs SET status=?, applied_at=? WHERE id=?",
                     (status, datetime.now().isoformat(), job_id))
    elif extra_field == "reminded_at":
        conn.execute("UPDATE jobs SET status=?, reminded_at=? WHERE id=?",
                     (status, datetime.now().isoformat(), job_id))
    else:
        conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
    conn.commit()
    conn.close()


def mark_sent_batch(job_ids):
    conn = _connect()
    conn.executemany("UPDATE jobs SET status='sent' WHERE id=?", [(j,) for j in job_ids])
    conn.commit()
    conn.close()


def get_applied_jobs_needing_reminder(days_threshold):
    """Jobs applied >= days_threshold days ago that haven't been reminded yet."""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM jobs WHERE status='applied' AND applied_at IS NOT NULL"
    ).fetchall()
    conn.close()
    due = []
    for r in rows:
        applied_dt = datetime.fromisoformat(r["applied_at"])
        if (datetime.now() - applied_dt).days >= days_threshold:
            due.append(r)
    return due


def search_jobs(query):
    conn = _connect()
    like = f"%{query}%"
    rows = conn.execute(
        "SELECT * FROM jobs WHERE title LIKE ? OR company LIKE ? ORDER BY found_at DESC",
        (like, like),
    ).fetchall()
    conn.close()
    return rows


def list_all(limit=50):
    conn = _connect()
    rows = conn.execute("SELECT * FROM jobs ORDER BY found_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows
