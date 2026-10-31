"""The CLI entry point: argument handling and demo-user wiring."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from marketsales.__main__ import DEMO_USERS, main  # noqa: E402


class MainCliTests(unittest.TestCase):
    def test_demo_users(self):
        self.assertEqual(DEMO_USERS,
                         {"alice": "admin", "bob": "operator",
                          "carol": "viewer"})

    def test_no_command_is_an_error(self):
        with self.assertRaises(SystemExit):
            main([])

    def test_bad_port_is_an_error(self):
        with self.assertRaises(SystemExit):
            main(["serve", "--port", "not-a-number"])


if __name__ == "__main__":
    unittest.main()
