"""Live smoke driver (not a unittest): real server, real requests.

Run: PYTHONPATH=src python3 tests/smoke.py

Flow: health; organization + members; participant; contract;
in-bounds modification; over-ceiling modification rejected (400);
opportunity + submission + award; report shows the derived
obligated total. Prints SMOKE OK on success.
"""

import http.client
import json
import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))

from contractmgmt.audit import AuditLog  # noqa: E402
from contractmgmt.service import USERS, make_server  # noqa: E402
from contractmgmt.store import ContractMgmtStore  # noqa: E402


def call(port, method, path, user=None, role=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"Content-Type": "application/json"}
    if user is not None:
        headers["X-User"] = user
    if role is not None:
        headers["X-Role"] = role
    conn.request(method, path,
                 body=json.dumps(body) if body is not None else None,
                 headers=headers)
    response = conn.getresponse()
    raw = response.read()
    conn.close()
    return response.status, json.loads(raw) if raw else {}


def main():
    audit = AuditLog()
    store = ContractMgmtStore(audit=audit)
    server = make_server("127.0.0.1", 0, store, audit, dict(USERS))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, body = call(port, "GET", "/health")
        assert (status, body) == (200, {"status": "ok"}), (status, body)
        print("GET /health -> 200 {\"status\": \"ok\"}")

        status, org = call(port, "POST", "/organizations", "alice", "admin",
                           {"org_ref": "ORG-SMOKE", "label": "Smoke Org"})
        assert status == 201, (status, org)
        org_id = org["id"]
        print("organization %s created (201)" % org_id)
        status, _ = call(port, "POST", "/organizations/%s/members" % org_id,
                         "alice", "admin", {"username": "bob"})
        assert status == 200, status
        status, _ = call(port, "POST", "/participants", "bob", "member",
                         {"participant_ref": "PAR-SMOKE",
                          "label": "Smoke Vendor"})
        assert status == 201, status

        status, contract = call(
            port, "POST", "/organizations/%s/contracts" % org_id,
            "bob", "member",
            {"contract_ref": "CON-SMOKE", "title": "Smoke Contract",
             "counterparty_ref": "VENDOR-REF", "ceiling_cents": 1000,
             "award_cents": 400})
        assert status == 201, (status, contract)
        contract_id = contract["id"]
        status, _ = call(
            port, "POST",
            "/organizations/%s/contracts/%s/modifications"
            % (org_id, contract_id),
            "bob", "member", {"mod_ref": "MOD-1", "amount_cents": 500})
        assert status == 201, status
        print("modification MOD-1 recorded (201); obligated 900 of 1000")
        status, body = call(
            port, "POST",
            "/organizations/%s/contracts/%s/modifications"
            % (org_id, contract_id),
            "bob", "member", {"mod_ref": "MOD-2", "amount_cents": 101})
        assert status == 400, (status, body)
        print("over-ceiling modification -> 400: %s" % body["error"])

        status, opp = call(
            port, "POST", "/organizations/%s/opportunities" % org_id,
            "bob", "member",
            {"opportunity_ref": "OPP-SMOKE", "title": "Smoke Opp",
             "kind": "erfx"})
        assert status == 201, (status, opp)
        status, sub = call(
            port, "POST",
            "/organizations/%s/opportunities/%s/submissions"
            % (org_id, opp["id"]),
            "bob", "member",
            {"submission_ref": "SUB-SMOKE",
             "participant_ref": "PAR-SMOKE"})
        assert status == 201, (status, sub)
        status, _ = call(
            port, "POST",
            "/organizations/%s/opportunities/%s/awards"
            % (org_id, opp["id"]),
            "bob", "member",
            {"submission_id": sub["id"], "award_ref": "AWD-SMOKE",
             "amount_cents": 900})
        assert status == 201, status
        status, report = call(port, "GET",
                              "/organizations/%s/report" % org_id,
                              "alice", "admin")
        assert status == 200, (status, report)
        assert report["obligated_cents_total"] == 900, report
        assert report["award_cents_total"] == 900, report
        print("report: obligated_cents_total=900, award_cents_total=900")
        print("SMOKE OK")
        return 0
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())
