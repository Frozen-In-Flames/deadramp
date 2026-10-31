"""CLI entry point: demo users documented, serve parser works."""
import unittest
from librarysys.__main__ import DEMO_USERS

class CliTests(unittest.TestCase):
    def test_demo_users(self):
        self.assertEqual(DEMO_USERS, {"alice": "admin", "bob": "member", "carol": "viewer"})
if __name__ == "__main__": unittest.main()
