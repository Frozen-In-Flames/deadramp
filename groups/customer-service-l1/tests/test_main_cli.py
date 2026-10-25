"""CLI entry point behavior (no server is started)."""

import unittest

from custsvc.__main__ import build_parser, main


class TestMainCli(unittest.TestCase):
    def test_no_command_returns_2(self):
        self.assertEqual(main([]), 2)

    def test_certfile_without_keyfile_is_a_parser_error(self):
        with self.assertRaises(SystemExit):
            main(["serve", "--certfile", "only.pem"])

    def test_parser_defaults(self):
        args = build_parser().parse_args(["serve"])
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8799)


if __name__ == "__main__":
    unittest.main()
