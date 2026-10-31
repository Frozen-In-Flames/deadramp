"""Command-line entry point: ``python -m manufacturing serve``.

Demo identities are hooks for local evaluation, not an identity
provider: the embedding organization supplies real identity (see
UNION-SPEC.md). The demo users are alice (admin), bob (operator),
and carol (viewer).
"""

import argparse
import sys

from .access import User
from .audit import AuditLog
from .service import make_server
from .store import ManufacturingStore

DEMO_USERS = {
    "alice": User("alice", "admin"),
    "bob": User("bob", "operator"),
    "carol": User("carol", "viewer"),
}


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="manufacturing",
        description="Manufacturing — untiered set (Operation DeadRamp).")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="run the HTTP service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--audit-log", default=None,
                       help="path to a JSONL audit log file")
    serve.add_argument("--certfile", default=None, help="TLS certificate file")
    serve.add_argument("--keyfile", default=None, help="TLS key file")

    args = parser.parse_args(argv)
    if args.command != "serve":
        parser.print_help()
        return 2

    audit = AuditLog(args.audit_log) if args.audit_log else AuditLog()
    store = ManufacturingStore(audit=audit)
    server = make_server(
        args.host,
        args.port,
        store=store,
        audit=audit,
        users=DEMO_USERS,
        certfile=args.certfile,
        keyfile=args.keyfile,
    )
    scheme = "https" if args.certfile else "http"
    print("manufacturing listening on %s://%s:%d"
          % (scheme, args.host, args.port), file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
