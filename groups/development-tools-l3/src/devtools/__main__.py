"""Command-line entry point: ``python -m devtools serve ...``.

Demo users (documented demo identities, not an identity provider):

- ``alice`` -- admin
- ``bob``   -- developer
- ``carol`` -- viewer
- ``dana``  -- auditor (audit_read only; AC-5 separation of duties) [L3]

Callers authenticate with ``X-User`` / ``X-Role`` headers matching
these names and roles. When ``--certfile`` and ``--keyfile`` are given,
the server serves over TLS using the standard library ``ssl`` module.
"""

import argparse
import ssl
import sys

from .audit import AuditLog
from .service import USERS, make_server
from .store import DevToolsStore

DEMO_USERS = dict(USERS)


def build_parser():
    parser = argparse.ArgumentParser(prog="devtools")
    subparsers = parser.add_subparsers(dest="command")
    serve = subparsers.add_parser("serve", help="run the devtools HTTP service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8792)
    serve.add_argument("--audit-log", default=None, help="path to a JSONL audit log")
    serve.add_argument("--certfile", default=None, help="TLS certificate file (PEM)")
    serve.add_argument("--keyfile", default=None, help="TLS private key file (PEM)")
    serve.add_argument(
        "--max-failed-logins",
        type=int,
        default=3,
        help="consecutive failed logons before lockout (AC-7)",
    )
    serve.add_argument(
        "--lockout-seconds",
        type=int,
        default=300,
        help="logon lockout duration in seconds (AC-7)",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "serve":
        parser.print_help()
        return 2
    if bool(args.certfile) != bool(args.keyfile):
        parser.error("--certfile and --keyfile must be given together")

    audit = AuditLog(path=args.audit_log)
    store = DevToolsStore(audit=audit)
    server = make_server(
        args.host,
        args.port,
        store,
        audit,
        dict(DEMO_USERS),
        max_failures=args.max_failed_logins,
        lockout_seconds=args.lockout_seconds,
    )

    scheme = "http"
    if args.certfile and args.keyfile:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=args.certfile, keyfile=args.keyfile)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        scheme = "https"

    host, port = server.server_address[0], server.server_address[1]
    print(
        "devtools service listening on %s://%s:%d (demo users: alice=admin, bob=developer, carol=viewer, dana=auditor)"
        % (scheme, host, port),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
