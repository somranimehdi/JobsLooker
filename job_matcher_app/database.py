import hashlib
import json
import sqlite3
from datetime import datetime

import pandas as pd

from .config import DB_PATH, LOG_DIR


class DatabaseManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        LOG_DIR.mkdir(exist_ok=True)

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self):
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS resumes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    content_hash TEXT NOT NULL UNIQUE,
                    text_content TEXT NOT NULL,
                    inferred_role TEXT,
                    skills_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS search_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resume_id INTEGER,
                    query TEXT NOT NULL,
                    countries TEXT NOT NULL,
                    days INTEGER NOT NULL,
                    sources TEXT NOT NULL,
                    results_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(resume_id) REFERENCES resumes(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quality_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_run_id INTEGER NOT NULL,
                    check_name TEXT NOT NULL,
                    check_value TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(search_run_id) REFERENCES search_runs(id)
                )
                """
            )
            conn.commit()

    def save_resume(self, name, text_content, inferred_role, skills):
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        content_hash = hashlib.sha256(text_content.encode("utf-8", errors="ignore")).hexdigest()
        skills_json = json.dumps(skills, ensure_ascii=False)

        with self.connect() as conn:
            row = conn.execute("SELECT id FROM resumes WHERE content_hash = ?", (content_hash,)).fetchone()
            if row:
                resume_id = int(row["id"])
                conn.execute(
                    "UPDATE resumes SET name = ?, inferred_role = ?, skills_json = ?, updated_at = ? WHERE id = ?",
                    (name, inferred_role, skills_json, now, resume_id),
                )
            else:
                cur = conn.execute(
                    """
                    INSERT INTO resumes (name, content_hash, text_content, inferred_role, skills_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (name, content_hash, text_content, inferred_role, skills_json, now, now),
                )
                resume_id = int(cur.lastrowid)
            conn.commit()
        return resume_id

    def get_resume(self, resume_id):
        with self.connect() as conn:
            return conn.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()

    def list_resumes(self, limit=200):
        with self.connect() as conn:
            return conn.execute(
                "SELECT id, name, inferred_role, skills_json, created_at, updated_at FROM resumes ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

    def save_search_run(self, resume_id, query, countries, days, sources, results_count):
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO search_runs (resume_id, query, countries, days, sources, results_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (resume_id, query, countries, int(days), sources, int(results_count), now),
            )
            conn.commit()
            return int(cur.lastrowid)

    def save_quality_checks(self, search_run_id, quality_df):
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        rows = [
            (search_run_id, str(row["check"]), str(row["value"]), str(row["status"]), now)
            for _, row in quality_df.iterrows()
        ]
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO quality_checks (search_run_id, check_name, check_value, status, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()

    def get_search_history(self, limit=500):
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT sr.id, sr.created_at, r.name AS resume_name, sr.query, sr.countries,
                       sr.days, sr.sources, sr.results_count
                FROM search_runs sr
                LEFT JOIN resumes r ON r.id = sr.resume_id
                ORDER BY sr.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def get_quality_history(self, limit=1000):
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT qc.id, qc.created_at, qc.search_run_id, qc.check_name, qc.check_value, qc.status,
                       r.name AS resume_name
                FROM quality_checks qc
                LEFT JOIN search_runs sr ON sr.id = qc.search_run_id
                LEFT JOIN resumes r ON r.id = sr.resume_id
                ORDER BY qc.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    @staticmethod
    def rows_to_df(rows):
        return pd.DataFrame([dict(row) for row in rows]) if rows else pd.DataFrame()
