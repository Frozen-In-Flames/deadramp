import unittest

from talentdev.__main__ import DEMO_USERS, main


class TestMainCli(unittest.TestCase):
    def test_demo_users(self):
        self.assertEqual(DEMO_USERS["alice"].role, "admin")
        self.assertEqual(DEMO_USERS["bob"].role, "operator")
        self.assertEqual(DEMO_USERS["carol"].role, "viewer")

    def test_no_command_prints_help_and_returns_2(self):
        self.assertEqual(main([]), 2)


if __name__ == "__main__":
    unittest.main()
