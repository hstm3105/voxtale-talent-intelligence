import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path(__file__).parent / "resume_shortlister.db"

def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if tables do not exist and updates schema columns safely."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Table: Pipeline Runs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                jd_filename TEXT NOT NULL,
                jd_title TEXT,
                total_resumes INTEGER NOT NULL,
                status TEXT NOT NULL
            )
        """)

        # Table: Stored Resumes Repository
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                resume_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size_bytes INTEGER,
                raw_text TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            )
        """)

        # Table: Shortlisting Results (with email & phone columns)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                resume_filename TEXT NOT NULL,
                candidate_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                decision TEXT NOT NULL,
                score_0_100 INTEGER NOT NULL,
                key_strengths TEXT,
                key_gaps TEXT,
                flags TEXT NOT NULL,
                rationale TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            )
        """)

        # Safely add email and phone columns if missing from older DB versions
        try:
            cursor.execute("ALTER TABLE results ADD COLUMN email TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE results ADD COLUMN phone TEXT")
        except sqlite3.OperationalError:
            pass

        # Table: System Execution Logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                stage TEXT NOT NULL,
                message TEXT NOT NULL,
                level TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            )
        """)

        # Table: Recruiter Feedback & Corrections (Bonus Section 6)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                resume_filename TEXT NOT NULL,
                candidate_name TEXT NOT NULL,
                original_decision TEXT NOT NULL,
                original_score INTEGER NOT NULL,
                corrected_decision TEXT NOT NULL,
                feedback_notes TEXT NOT NULL,
                is_validated INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            )
        """)
        conn.commit()

def save_run(run_id: str, jd_filename: str, jd_title: str, total_resumes: int, status: str = "COMPLETED"):
    """Inserts a new run record."""
    init_db()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.cursor().execute(
            "INSERT OR REPLACE INTO runs (run_id, timestamp, jd_filename, jd_title, total_resumes, status) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, now_str, jd_filename, jd_title, total_resumes, status)
        )
        conn.commit()

def save_resume(run_id: str, filename: str, file_type: str, file_size: int, raw_text: str):
    """Saves a resume document in the database repository."""
    init_db()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.cursor().execute(
            "INSERT INTO resumes (run_id, filename, file_type, file_size_bytes, raw_text, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, filename, file_type, file_size, raw_text, now_str)
        )
        conn.commit()

def save_result(run_id: str, res: Any):
    """Saves a candidate evaluation result record including email and phone."""
    init_db()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    email = getattr(res, "email", "N/A") or "N/A"
    phone = getattr(res, "phone", "N/A") or "N/A"

    with get_connection() as conn:
        conn.cursor().execute(
            """INSERT INTO results (
                run_id, resume_filename, candidate_name, email, phone, decision, score_0_100, key_strengths, key_gaps, flags, rationale, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id, res.resume_filename, res.candidate_name, email, phone, res.decision,
                res.score_0_100, res.key_strengths, res.key_gaps, res.flags, res.rationale, now_str
            )
        )
        conn.commit()

def save_log(run_id: str, stage: str, message: str, level: str = "INFO"):
    """Saves a pipeline execution log event."""
    init_db()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.cursor().execute(
            "INSERT INTO logs (run_id, timestamp, stage, message, level) VALUES (?, ?, ?, ?, ?)",
            (run_id, now_str, stage, message, level)
        )
        conn.commit()

def save_feedback(run_id: str, resume_filename: str, candidate_name: str, original_decision: str, original_score: int, corrected_decision: str, feedback_notes: str, is_validated: int = 0):
    """Saves recruiter feedback / correction record (defaults to is_validated = 0, pending admin review)."""
    init_db()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.cursor().execute(
            """INSERT INTO feedback (
                run_id, resume_filename, candidate_name, original_decision, original_score, corrected_decision, feedback_notes, is_validated, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, resume_filename, candidate_name, original_decision, original_score, corrected_decision, feedback_notes, is_validated, now_str)
        )
        conn.commit()

def approve_feedback(feedback_id: int):
    """Approves a recruiter feedback / correction record (sets is_validated = 1)."""
    init_db()
    with get_connection() as conn:
        conn.cursor().execute(
            "UPDATE feedback SET is_validated = 1 WHERE feedback_id = ?",
            (feedback_id,)
        )
        conn.commit()

def get_pending_feedback() -> List[Dict[str, Any]]:
    """Fetches all recruiter feedback entries awaiting approval (is_validated = 0)."""
    init_db()
    with get_connection() as conn:
        rows = conn.cursor().execute(
            "SELECT * FROM feedback WHERE is_validated = 0 ORDER BY timestamp DESC"
        ).fetchall()
        return [dict(r) for r in rows]

def get_validated_feedback(limit: int = 5) -> List[Dict[str, Any]]:
    """Fetches top validated recruiter feedback items for few-shot prompt context (is_validated = 1)."""
    init_db()
    with get_connection() as conn:
        rows = conn.cursor().execute(
            "SELECT * FROM feedback WHERE is_validated = 1 ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

def get_all_feedback() -> List[Dict[str, Any]]:
    """Fetches all recruiter feedback entries."""
    init_db()
    with get_connection() as conn:
        rows = conn.cursor().execute("SELECT * FROM feedback ORDER BY timestamp DESC").fetchall()
        return [dict(r) for r in rows]

def get_all_runs() -> List[Dict[str, Any]]:
    """Fetches all past pipeline runs."""
    init_db()
    with get_connection() as conn:
        rows = conn.cursor().execute("SELECT * FROM runs ORDER BY timestamp DESC").fetchall()
        return [dict(r) for r in rows]

def get_results_by_run(run_id: str) -> List[Dict[str, Any]]:
    """Fetches evaluation results for a specific run."""
    init_db()
    with get_connection() as conn:
        rows = conn.cursor().execute("SELECT * FROM results WHERE run_id = ? ORDER BY score_0_100 DESC", (run_id,)).fetchall()
        return [dict(r) for r in rows]

def get_resumes_by_run(run_id: str) -> List[Dict[str, Any]]:
    """Fetches stored resumes for a specific run."""
    init_db()
    with get_connection() as conn:
        rows = conn.cursor().execute("SELECT * FROM resumes WHERE run_id = ?", (run_id,)).fetchall()
        return [dict(r) for r in rows]

def get_logs_by_run(run_id: str) -> List[Dict[str, Any]]:
    """Fetches execution logs for a specific run."""
    init_db()
    with get_connection() as conn:
        rows = conn.cursor().execute("SELECT * FROM logs WHERE run_id = ? ORDER BY log_id ASC", (run_id,)).fetchall()
        return [dict(r) for r in rows]

def get_all_roles_with_candidates() -> List[Dict[str, Any]]:
    """Fetches list of unique JD roles stored in history along with run and count statistics."""
    init_db()
    with get_connection() as conn:
        query = """
            SELECT 
                r.jd_title,
                r.jd_filename,
                COUNT(DISTINCT LOWER(TRIM(res.candidate_name))) as total_evaluated,
                COUNT(DISTINCT CASE WHEN res.decision IN ('Shortlist', 'Maybe') THEN LOWER(TRIM(res.candidate_name)) END) as shortlisted_count,
                MAX(r.timestamp) as last_run_timestamp
            FROM runs r
            LEFT JOIN results res ON r.run_id = res.run_id
            GROUP BY r.jd_title, r.jd_filename
            ORDER BY last_run_timestamp DESC
        """
        rows = conn.cursor().execute(query).fetchall()
        return [dict(row) for row in rows]

def get_shortlisted_candidates_by_role(jd_title: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches shortlisted/maybe candidate details with strict deduplication (most recent evaluation per candidate)."""
    init_db()
    with get_connection() as conn:
        if jd_title and jd_title != "All Roles":
            query = """
                WITH RankedResults AS (
                    SELECT 
                        r.jd_title,
                        r.jd_filename,
                        r.run_id,
                        res.resume_filename,
                        res.candidate_name,
                        COALESCE(res.email, 'N/A') as email,
                        COALESCE(res.phone, 'N/A') as phone,
                        res.decision,
                        res.score_0_100,
                        res.key_strengths,
                        res.key_gaps,
                        res.flags,
                        res.rationale,
                        res.timestamp,
                        ROW_NUMBER() OVER (
                            PARTITION BY LOWER(TRIM(res.candidate_name)), LOWER(TRIM(r.jd_title)) 
                            ORDER BY res.timestamp DESC, res.result_id DESC
                        ) as rn
                    FROM results res
                    JOIN runs r ON res.run_id = r.run_id
                    WHERE res.decision IN ('Shortlist', 'Maybe') AND LOWER(TRIM(r.jd_title)) = LOWER(TRIM(?))
                )
                SELECT 
                    jd_title, jd_filename, run_id, resume_filename, candidate_name,
                    email, phone, decision, score_0_100, key_strengths, key_gaps,
                    flags, rationale, timestamp
                FROM RankedResults
                WHERE rn = 1
                ORDER BY score_0_100 DESC, timestamp DESC
            """
            rows = conn.cursor().execute(query, (jd_title,)).fetchall()
        else:
            query = """
                WITH RankedResults AS (
                    SELECT 
                        r.jd_title,
                        r.jd_filename,
                        r.run_id,
                        res.resume_filename,
                        res.candidate_name,
                        COALESCE(res.email, 'N/A') as email,
                        COALESCE(res.phone, 'N/A') as phone,
                        res.decision,
                        res.score_0_100,
                        res.key_strengths,
                        res.key_gaps,
                        res.flags,
                        res.rationale,
                        res.timestamp,
                        ROW_NUMBER() OVER (
                            PARTITION BY LOWER(TRIM(res.candidate_name)) 
                            ORDER BY res.timestamp DESC, res.result_id DESC
                        ) as rn
                    FROM results res
                    JOIN runs r ON res.run_id = r.run_id
                    WHERE res.decision IN ('Shortlist', 'Maybe')
                )
                SELECT 
                    jd_title, jd_filename, run_id, resume_filename, candidate_name,
                    email, phone, decision, score_0_100, key_strengths, key_gaps,
                    flags, rationale, timestamp
                FROM RankedResults
                WHERE rn = 1
                ORDER BY score_0_100 DESC, timestamp DESC
            """
            rows = conn.cursor().execute(query).fetchall()
        return [dict(row) for row in rows]
