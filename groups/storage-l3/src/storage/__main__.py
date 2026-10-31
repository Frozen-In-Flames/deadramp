"""Command line entry point: ``python -m storage serve``.

Starts the REST API with demo users ``alice=admin, bob=operator,
carol=viewer, dana=auditor`` (dana holds ``audit_read`` only --
AC-5 separation of duties [L3]). Demo identities are hooks for
local evaluation; a real deployment is embedded behind the
operating organization's identity provider.
"""

import argparse
import sys

from .audit import AuditLog
from .service import make_server
from .store import StorageStore

DEMO_USERS = {"alice": "admin", "bob": "operator", "carol": "viewer",
              "dana": "auditor"}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="storage")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the REST API server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--audit-log", default=None,
                       help="path to a JSONL audit log file")
    serve.add_argument("--certfile", default=None,
                       help="TLS certificate file (enables HTTPS)")
    serve.add_argument("--keyfile", default=None,
                       help="TLS private key file")
    serve.add_argument("--max-failed-logins", type=int, default=3,
                       help="consecutive failed logons before lockout (AC-7)")
    serve.add_argument("--lockout-seconds", type=int, default=300,
                       help="logon lockout duration in seconds (AC-7)")
    args = parser.parse_args(argv)

    if args.command == "serve":
        audit = AuditLog(args.audit_log)
        store = StorageStore(audit=audit)
        server = make_server(args.host, args.port, store=store, audit=audit,
                             users=DEMO_USERS, certfile=args.certfile,
                             keyfile=args.keyfile,
                             max_failures=args.max_failed_logins,
                             lockout_seconds=args.lockout_seconds)
        scheme = "https" if args.certfile else "http"
        print("storage listening on %s://%s:%d" % (scheme, args.host, args.port),
              file=sys.stderr)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
