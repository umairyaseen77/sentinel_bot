import unittest
import sys
import os
import sqlite3
from unittest.mock import patch

# Adjust path to import from app module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.state_manager import StateManager

class TestStateManagerDatabase(unittest.TestCase):
    def setUp(self):
        # Patch sqlite3.connect to use an in-memory database
        self.original_connect = sqlite3.connect

        def fake_connect(*args, **kwargs):
            self.conn = self.original_connect(':memory:')
            return self.conn

        self.patcher = patch('sqlite3.connect', side_effect=fake_connect)
        self.patcher.start()
        self.state_manager = StateManager('test_profile')

    def tearDown(self):
        self.state_manager.close()
        self.patcher.stop()

    def test_save_and_get_seen_urls(self):
        jobs = [
            {'url': 'http://example.com/1', 'title': 'Job 1'},
            {'url': 'http://example.com/2', 'title': 'Job 2'},
        ]
        self.state_manager.save_jobs(jobs)
        seen = self.state_manager.get_seen_urls()
        self.assertEqual(seen, {'http://example.com/1', 'http://example.com/2'})

        # Attempt to save a duplicate job
        self.state_manager.save_jobs([{'url': 'http://example.com/1', 'title': 'Dup'}])
        seen_after = self.state_manager.get_seen_urls()
        self.assertEqual(seen_after, seen)

if __name__ == '__main__':
    unittest.main()
