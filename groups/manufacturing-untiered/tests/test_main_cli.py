"""The CLI entry point: demo-user wiring; no command returns 2."""

import unittest

from manufacturing.__main__ import DEMO_USERS, main


class TestMainCli(unittest.TestCase):
    def test_no_command_returns_2(self):
        self.assertEqual(main([]), 2)

    def test_demo_users(self):
        self.assertEqual(DEMO_USERS["alice"].role, "admin")
        self.assertEqual(DEMO_USERS["bob"].role, "operator")
        self.assertEqual(DEMO_USERS["carol"].role, "viewer")


if __name__ == "__main__":
    unittest.main()
