"""CLI: python -m librarysys serve --host --port [--audit-log PATH]
[--certfile --keyfile]. Demo users alice=admin, bob=member,
carol=viewer (demo identities; production identity is the embedding
organization's, per IA-2)."""
import argparse, ssl
from .audit import AuditLog
from .service import make_server
from .store import LibrarySysStore

DEMO_USERS = {"alice": "admin", "bob": "member", "carol": "viewer"}

def main(argv=None):
    p = argparse.ArgumentParser(prog="librarysys")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8821)
    s.add_argument("--audit-log", default=None)
    s.add_argument("--certfile", default=None)
    s.add_argument("--keyfile", default=None)
    args = p.parse_args(argv)
    audit = AuditLog(args.audit_log)
    server = make_server(args.host, args.port, LibrarySysStore(audit), audit, DEMO_USERS)
    if args.certfile:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(args.certfile, args.keyfile)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
    print("listening on %s:%d" % (args.host, args.port))
    server.serve_forever()

if __name__ == "__main__":
    main()
