import unittest

from travel.__main__ import DEMO_USERS, build_parser, main


class TestMainCli(unittest.TestCase):
    def test_demo_users(self):
        self.assertEqual(DEMO_USERS, {"alice": "admin", "bob": "member",
                                      "carol": "viewer"})

    def test_serve_defaults(self):
        args = build_parser().parse_args(["serve"])
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8799)
        self.assertIsNone(args.audit_log)

    def test_no_command_returns_2(self):
        self.assertEqual(main([]), 2)

    def test_certfile_without_keyfile_errors(self):
        with self.assertRaises(SystemExit):
            main(["serve", "--certfile", "cert.pem"])


if __name__ == "__main__":
    unittest.main()
