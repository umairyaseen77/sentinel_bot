import sqlite3
import datetime
from typing import List, Dict, Set
from .logger import log
import os
import re

def sanitize_filename(name: str) -> str:
    """Sanitizes a string to be a valid filename."""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

class StateManager:
    """Handles the SQLite database for storing job data for a specific profile."""

    def __init__(self, profile_name: str):
        """
        Initializes the database connection for a given profile.
        """
        db_filename = f"{sanitize_filename(profile_name)}.db"
        db_path = os.path.join('data', db_filename)
        
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        self.conn = sqlite3.connect(db_path)
        log.info(f"Initialized state manager for profile '{profile_name}' at '{db_path}'")
        self.create_table()

    def create_table(self):
        """Creates the 'jobs' table if it doesn't already exist."""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY,
                    url TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    date_seen TEXT NOT NULL
                )
            """)

    def save_jobs(self, jobs: List[Dict[str, str]]):
        """
        Saves a list of new jobs to the database.
        Jobs are provided as a list of dictionaries, each with 'url' and 'title'.
        """
        if not jobs:
            return

        now = datetime.datetime.now().isoformat()
        job_data = [(job['url'], job['title'], now) for job in jobs]

        with self.conn:
            try:
                self.conn.executemany(
                    "INSERT OR IGNORE INTO jobs (url, title, date_seen) VALUES (?, ?, ?)",
                    job_data
                )
                self.conn.commit()
                log.info(f"Successfully saved {len(job_data)} new jobs to the database.")
            except sqlite3.Error as e:
                log.error(f"Error saving jobs to database: {e}")


    def get_seen_urls(self) -> Set[str]:
        """
        Retrieves a set of all job URLs currently in the database.
        """
        try:
            with self.conn:
                cursor = self.conn.execute("SELECT url FROM jobs")
                return {row[0] for row in cursor.fetchall()}
        except sqlite3.Error as e:
            log.error(f"Could not retrieve seen URLs from database: {e}")
            return set()

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            log.info("Database connection closed.")

    def __del__(self):
        """Ensures the database connection is closed when the object is destroyed."""
        self.close() 