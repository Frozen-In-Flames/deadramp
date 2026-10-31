"""Live smoke driver (not a unittest): start the real server on an
ephemeral port, hit /health, create an agency + workspace + sandbox
session, record two executions, confirm the second is rejected 400.
Run: PYTHONPATH=src python3 tests/smoke.py
"""

import http.client
import json
import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))

from legalpol.audit import AuditLog
from legalpol.service import make_server
from legalpol.store import LegalPolStore

USERS = {"alice": "admin", "bob": "member", "carol": "viewer"}
ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "member"}


def call(port, method, path, headers=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    conn.request(method, path,
                 body=json.dumps(body) if body is not None else None,
                 headers=hdrs)
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    return resp.status, json.loads(raw) if raw else {}


def main():
    audit = AuditLog()
    store = LegalPolStore(audit=audit)
    server = make_server("127.0.0.1", 0, store, audit, dict(USERS))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        print("port:", port)
        print("health:", call(port, "GET", "/health"))
        status, agency = call(port, "POST", "/agencies", ALICE,
                              {"agency_ref": "SMOKE-AGY", "label": "Smoke"})
        print("create agency:", status, agency["id"])
        aid = agency["id"]
        print("add bob:", call(port, "POST", "/agencies/%s/members" % aid,
                               ALICE, {"username": "bob"})[0])
        status, ws = call(port, "POST", "/agencies/%s/workspaces" % aid, BOB,
                          {"workspace_ref": "SMOKE-WSP", "title": "Smoke WS"})
        print("create workspace:", status, ws["id"])
        status, ses = call(port, "POST", "/agencies/%s/sessions" % aid, BOB,
                           {"workspace_id": ws["id"],
                            "session_ref": "SMOKE-SES", "sandbox": True})
        print("create sandbox session:", status, ses["id"], "sandbox=",
              ses["sandbox"])
        print("execution 1:", call(
            port, "POST",
            "/agencies/%s/sessions/%s/executions" % (aid, ses["id"]), BOB,
            {"execution_ref": "EXE-1"})[0])
        status, body = call(
            port, "POST",
            "/agencies/%s/sessions/%s/executions" % (aid, ses["id"]), BOB,
            {"execution_ref": "EXE-2"})
        print("execution 2 (must be 400):", status, body)
        assert status == 400, "single-use rule not enforced over HTTP"
        print("SMOKE OK")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
