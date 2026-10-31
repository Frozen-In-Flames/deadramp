"""Command line entry point: ``python -m events serve``.

Starts the REST API with demo users ``alice=admin, bob=member,
carol=viewer``. Demo identities are hooks for local evaluation; a
real deployment is embedded behind the operating organization's
identity provider.
"""

import argparse
import sys

from .audit import AuditLog
from .service import make_server
from .store import EventsStore

DEMO_USERS = {"alice": "admin", "bob": "member", "carol": "viewer"}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="events")
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
    args = parser.parse_args(argv)

    if args.command == "serve":
        audit = AuditLog(args.audit_log)
        store = EventsStore(audit=audit)
        server = make_server(args.host, args.port, store=store, audit=audit,
                             users=DEMO_USERS, certfile=args.certfile,
                             keyfile=args.keyfile)
        scheme = "https" if args.certfile else "http"
        print("events listening on %s://%s:%d" % (scheme, args.host, args.port),
              file=sys.stderr)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
