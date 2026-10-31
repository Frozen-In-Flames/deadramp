"""The CLI entry point: demo-user wiring; usage errors."""

import unittest

import media.__main__ as main_module


class MainCliTests(unittest.TestCase):
    def test_demo_users(self):
        self.assertEqual(main_module.DEMO_USERS,
                         {"alice": "admin", "bob": "operator",
                          "carol": "viewer"})

    def test_missing_command_is_a_usage_error(self):
        with self.assertRaises(SystemExit):
            main_module.main([])

    def test_bad_port_is_a_usage_error(self):
        with self.assertRaises(SystemExit):
            main_module.main(["serve", "--port", "not-a-port"])


if __name__ == "__main__":
    unittest.main()
