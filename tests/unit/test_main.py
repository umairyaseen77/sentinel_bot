import unittest
import sys
import os

# Adjust path to import from app module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.main import filter_jobs
# Mock the logger for tests to avoid errors if logger is not configured during tests
from unittest.mock import MagicMock
import app.main # Import the module itself to mock 'log'
app.main.log = MagicMock()


class TestFilterJobs(unittest.TestCase):

    def setUp(self):
        self.sample_jobs = [
            {"title": "Python Developer", "location": "London, UK", "url": "url1"},
            {"title": "Software Engineer (Java)", "location": "New York, USA", "url": "url2"},
            {"title": "Junior Python Developer", "location": "London", "url": "url3"},
            {"title": "Data Scientist (Python)", "location": "Manchester, UK", "url": "url4"},
            {"title": "Web Developer", "location": "london", "url": "url5"}
        ]

    def test_no_jobs_input(self):
        self.assertEqual(filter_jobs([], {}, {}), [])

    def test_required_keywords(self):
        keywords_config = {"required": ["Python"]}
        result = filter_jobs(self.sample_jobs, keywords_config, {})
        self.assertEqual(len(result), 3)
        self.assertTrue(all("python" in job["title"].lower() for job in result))

    def test_required_keywords_case_insensitive(self):
        keywords_config = {"required": ["python"]} # Lowercase keyword
        result = filter_jobs(self.sample_jobs, keywords_config, {})
        self.assertEqual(len(result), 3)

    def test_no_required_keywords_match(self):
        keywords_config = {"required": ["NonExistent"]}
        result = filter_jobs(self.sample_jobs, keywords_config, {})
        self.assertEqual(len(result), 0)

    def test_excluded_keywords(self):
        keywords_config = {"excluded": ["Java", "Scientist"]}
        # Expected: Python Dev, Junior Python Dev, Web Developer
        result = filter_jobs(self.sample_jobs, keywords_config, {})
        self.assertEqual(len(result), 3)
        self.assertFalse(any("java" in job["title"].lower() or "scientist" in job["title"].lower() for job in result))

    def test_excluded_keywords_case_insensitive(self):
        keywords_config = {"excluded": ["java", "scientist"]}
        result = filter_jobs(self.sample_jobs, keywords_config, {})
        self.assertEqual(len(result), 3)

    def test_required_and_excluded_keywords(self):
        keywords_config = {"required": ["Developer"], "excluded": ["Java"]}
        # Expected: Python Dev, Junior Python Dev, Web Developer
        result = filter_jobs(self.sample_jobs, keywords_config, {})
        self.assertEqual(len(result), 3)

    def test_required_and_excluded_conflict(self):
        # Requires "Python", Excludes "Developer"
        keywords_config = {"required": ["Python"], "excluded": ["Developer"]}
        # Expected: Data Scientist (Python)
        result = filter_jobs(self.sample_jobs, keywords_config, {})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Data Scientist (Python)")

    def test_location_filter(self):
        filters_config = {"cities": ["London"]}
        result = filter_jobs(self.sample_jobs, {}, filters_config)
        # Python Dev (London, UK), Junior Python Dev (London), Web Developer (london)
        self.assertEqual(len(result), 3)
        self.assertTrue(all("london" in job["location"].lower() for job in result))

    def test_location_filter_case_insensitive_city(self):
        filters_config = {"cities": ["london"]}
        result = filter_jobs(self.sample_jobs, {}, filters_config)
        self.assertEqual(len(result), 3)

    def test_location_filter_no_match(self):
        filters_config = {"cities": ["Berlin"]}
        result = filter_jobs(self.sample_jobs, {}, filters_config)
        self.assertEqual(len(result), 0)

    def test_location_filter_job_missing_location(self):
        job_no_loc = {"title": "Remote Python Role", "url": "url_remote"} # No 'location' key
        filters_config = {"cities": ["London"]}
        # If job has no "location" key, it should not match city filters and not cause error
        result = filter_jobs([job_no_loc] + self.sample_jobs, {"required": ["Python"]}, filters_config)
        # Only Python Developer and Junior Python Developer from self.sample_jobs should match
        # (Data Scientist is Python but not London, job_no_loc is Python but no location)
        # This test logic needs to be precise based on how filter_jobs handles missing 'location'
        # Assuming it defaults to empty string or similar, it won't match "London"

        # Re-evaluating expected:
        # Python Developer (London, UK) - YES
        # Junior Python Developer (London) - YES
        # Data Scientist (Python) (Manchester) - NO (location)
        # Web Developer (london) - NO (keyword)
        # Remote Python Role (no location) - NO (location)

        # Let's test job_no_loc separately for clarity on missing key behavior
        res_no_loc_only = filter_jobs([job_no_loc], {}, filters_config)
        self.assertEqual(len(res_no_loc_only), 0, "Job with missing location key should not match city filter")

        # Test with mixed list again, focusing on Python + London
        keywords_config = {"required": ["Python"]}
        filters_config_london = {"cities": ["London"]}
        expected_titles = ["Python Developer", "Junior Python Developer"]

        # Create a list that should match
        matching_jobs = [j for j in self.sample_jobs if j["title"] in expected_titles]

        result_mixed = filter_jobs(self.sample_jobs + [job_no_loc], keywords_config, filters_config_london)

        self.assertEqual(len(result_mixed), len(expected_titles))
        self.assertTrue(all(job["title"] in expected_titles for job in result_mixed))


    def test_combined_filters(self):
        keywords_config = {"required": ["Python"], "excluded": ["Junior"]}
        filters_config = {"cities": ["London"]}
        # Expected: Python Developer (London, UK)
        result = filter_jobs(self.sample_jobs, keywords_config, filters_config)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Python Developer")

    def test_empty_filter_configs(self):
        # No keywords, no city filters - should return all jobs
        result = filter_jobs(self.sample_jobs, {}, {})
        self.assertEqual(len(result), len(self.sample_jobs))

    def test_empty_keyword_lists_in_config(self):
        keywords_config = {"required": [], "excluded": []}
        result = filter_jobs(self.sample_jobs, keywords_config, {})
        self.assertEqual(len(result), len(self.sample_jobs))

    def test_empty_cities_list_in_config(self):
        filters_config = {"cities": []}
        result = filter_jobs(self.sample_jobs, {}, filters_config)
        self.assertEqual(len(result), len(self.sample_jobs))

if __name__ == '__main__':
    unittest.main()
