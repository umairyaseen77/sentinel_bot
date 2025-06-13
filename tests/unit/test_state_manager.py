import unittest
import sys
import os

# Adjust path to import from app module
# This assumes tests are run from the project root directory (e.g., python -m unittest discover tests)
# If app module is not found, this might need adjustment based on execution context
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.state_manager import sanitize_filename

class TestSanitizeFilename(unittest.TestCase):

    def test_valid_filename(self):
        self.assertEqual(sanitize_filename("profile1"), "profile1")

    def test_filename_with_spaces(self):
        self.assertEqual(sanitize_filename("my profile"), "my_profile")

    def test_filename_with_special_chars(self):
        # Based on re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        self.assertEqual(sanitize_filename("prof!@#$%^&*()_+={}[]|\\:;\"'<>,.?/"), "prof___________________________")

    def test_filename_with_mixed_case(self):
        self.assertEqual(sanitize_filename("MyProfile"), "MyProfile")

    def test_empty_string(self):
        self.assertEqual(sanitize_filename(""), "")

    def test_path_like_string(self):
        self.assertEqual(sanitize_filename("profiles/profile1"), "profiles_profile1")

    def test_leading_and_trailing_underscores_hyphens(self):
        self.assertEqual(sanitize_filename("-profile-"), "-profile-")
        self.assertEqual(sanitize_filename("_profile_"), "_profile_")

    def test_already_sanitized(self):
        self.assertEqual(sanitize_filename("already_sanitized-123"), "already_sanitized-123")

if __name__ == '__main__':
    unittest.main()
