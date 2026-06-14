import sqlite3
import os
import uuid
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "pipeline_state.db")

def get_db_connection():
    """Returns a connection to the SQLite database and ensures the tables exist."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Create runs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            product TEXT NOT NULL,
            iso_week TEXT NOT NULL,
            status TEXT NOT NULL,
            review_count INTEGER,
            window_weeks INTEGER,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT,
            UNIQUE(product, iso_week) ON CONFLICT REPLACE
        )
    """)
    
    # 2. Create deliveries table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            channel TEXT NOT NULL, -- 'google_doc' or 'gmail'
            external_id TEXT,      -- heading_id or message_id/draft_id
            url TEXT,              -- Doc URL or email link
            idempotency_key TEXT,
            FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    return conn

def is_already_run(product, iso_week):
    """Checks if a completed run already exists for the product and ISO week."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT run_id FROM runs WHERE product = ? AND iso_week = ? AND status = 'COMPLETED'",
        (product.lower(), iso_week)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None

def start_run(product, iso_week, review_count, window_weeks):
    """Logs the start of a run and returns a unique run_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Generate run_id
    suffix = uuid.uuid4().hex[:6]
    run_id = f"{product.lower()}-{iso_week}-{suffix}"
    
    cursor.execute(
        """
        INSERT INTO runs (run_id, product, iso_week, status, review_count, window_weeks, started_at, completed_at, error_message)
        VALUES (?, ?, ?, 'IN_PROGRESS', ?, ?, CURRENT_TIMESTAMP, NULL, NULL)
        """,
        (run_id, product.lower(), iso_week, review_count, window_weeks)
    )
    conn.commit()
    conn.close()
    return run_id

def complete_run(run_id, doc_id, heading_id, doc_url, email_message_id, email_idempotency_key):
    """Updates the run status to COMPLETED and adds delivery records."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Update run status
    cursor.execute(
        "UPDATE runs SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP WHERE run_id = ?",
        (run_id,)
    )
    
    # Add Google Doc delivery
    cursor.execute(
        "INSERT INTO deliveries (run_id, channel, external_id, url) VALUES (?, 'google_doc', ?, ?)",
        (run_id, heading_id, doc_url)
    )
    
    # Add Gmail delivery
    cursor.execute(
        "INSERT INTO deliveries (run_id, channel, external_id, idempotency_key) VALUES (?, 'gmail', ?, ?)",
        (run_id, email_message_id, email_idempotency_key)
    )
    
    conn.commit()
    conn.close()

def fail_run(run_id, error_message):
    """Updates the run status to FAILED."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE runs SET status = 'FAILED', error_message = ? WHERE run_id = ?",
        (error_message, run_id)
    )
    conn.commit()
    conn.close()
