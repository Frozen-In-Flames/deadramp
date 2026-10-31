"""Service contract: the HTTP layer over a live socket.

Traces to: UNION-SPEC.md implementation contract for
``contractmgmt/service.py`` — header auth against the user
registry, JSON errors (400/401/403/404), denied attempts audited
with a ``:denied`` suffix, the full portal flow, and the
modification bounds rule surfacing as a 400.
"""

import http.client
import json
import threading
import unittest

import contractmgmt_helpers as H
from contractmgmt.audit import AuditLog
from contractmgmt.service import make_server
from contractmgmt.store import ContractMgmtStore


class _Client:
    def __init__(self, port):
        self.port = port

    def call(self, method, path, user=None, role=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Content-Type": "application/json"}
        if user is not None:
            headers["X-User"] = user
        if role is not None:
            headers["X-Role"] = role
        payload = json.dumps(body) if body is not None else None
        conn.request(method, path, body=payload, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        conn.close()
        return response.status, json.loads(raw) if raw else {}


class TestService(unittest.TestCase):
    """Live HTTP against an ephemeral port."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = ContractMgmtStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit,
                                 dict(H.USERS_REGISTRY))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()
        cls.client = _Client(cls.port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health_needs_no_auth(self):
        """Service: GET /health answers 200 without credentials."""
        status, body = self.client.call("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_unknown_user_and_role_mismatch_are_401(self):
        """Service / IA-2 hooks: unknown users and role mismatches
        are 401, and the denial is audited."""
        status, _ = self.client.call("GET", "/organizations",
                                     user="mallory", role="admin")
        self.assertEqual(status, 401)
        status, _ = self.client.call("GET", "/organizations",
                                     user="alice", role="member")
        self.assertEqual(status, 401)
        denied = [e for e in self.audit.entries()
                  if e["action"].endswith(":denied")]
        self.assertGreaterEqual(len(denied), 2)

    def test_member_creating_organization_is_403(self):
        """Service / AC: org_write is admin-only — a member's create
        is 403, an admin's is 201."""
        status, _ = self.client.call(
            "POST", "/organizations", user="bob", role="member",
            body={"org_ref": "ORG-NO", "label": "Nope"})
        self.assertEqual(status, 403)
        status, body = self.client.call(
            "POST", "/organizations", user="alice", role="admin",
            body={"org_ref": "ORG-SVC", "label": "Service Org"})
        self.assertEqual(status, 201)
        self.assertEqual(body["org_ref"], "ORG-SVC")

    def test_unknown_route_is_404(self):
        """Service: an unmatched route is a JSON 404, never a stack
        trace."""
        status, body = self.client.call("GET", "/nope", user="alice",
                                        role="admin")
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_full_flow_and_bounds_over_http(self):
        """Service: the full flow — organization, members,
        participant, contract, in-bounds and out-of-bounds
        modifications (400), opportunity, submission, award,
        payment, report — plus audit access rules."""
        c = self.client
        status, org = c.call("POST", "/organizations", user="alice",
                             role="admin",
                             body={"org_ref": "ORG-FLOW",
                                   "label": "Flow Org"})
        self.assertEqual(status, 201)
        org_id = org["id"]
        for username in ("bob", "carol"):
            status, _ = c.call("POST", "/organizations/%s/members" % org_id,
                               user="alice", role="admin",
                               body={"username": username})
            self.assertEqual(status, 200)
        status, participant = c.call(
            "POST", "/participants", user="bob", role="member",
            body={"participant_ref": "PAR-SVC", "label": "Svc Vendor"})
        self.assertEqual(status, 201)

        status, contract = c.call(
            "POST", "/organizations/%s/contracts" % org_id, user="bob",
            role="member",
            body={"contract_ref": "CON-SVC", "title": "Svc Contract",
                  "counterparty_ref": "VENDOR-REF",
                  "ceiling_cents": 1000, "award_cents": 400})
        self.assertEqual(status, 201)
        contract_id = contract["id"]
        status, _ = c.call(
            "POST",
            "/organizations/%s/contracts/%s/modifications"
            % (org_id, contract_id),
            user="bob", role="member",
            body={"mod_ref": "MOD-1", "amount_cents": 500})
        self.assertEqual(status, 201)
        # One cent past the ceiling: 400, the bounds rule over HTTP.
        status, body = c.call(
            "POST",
            "/organizations/%s/contracts/%s/modifications"
            % (org_id, contract_id),
            user="bob", role="member",
            body={"mod_ref": "MOD-2", "amount_cents": 101})
        self.assertEqual(status, 400)
        self.assertIn("ceiling", body["error"])
        # A float amount is a 400, never stored.
        status, _ = c.call(
            "POST",
            "/organizations/%s/contracts/%s/modifications"
            % (org_id, contract_id),
            user="bob", role="member",
            body={"mod_ref": "MOD-3", "amount_cents": 1.5})
        self.assertEqual(status, 400)
        status, contracts = c.call("GET",
                                   "/organizations/%s/contracts" % org_id,
                                   user="carol", role="viewer")
        self.assertEqual(status, 200)
        self.assertEqual(contracts["contracts"][0]["obligated_cents"], 900)

        status, opp = c.call(
            "POST", "/organizations/%s/opportunities" % org_id,
            user="bob", role="member",
            body={"opportunity_ref": "OPP-SVC", "title": "Svc Opp",
                  "kind": "reverse_auction"})
        self.assertEqual(status, 201)
        opp_id = opp["id"]
        status, sub = c.call(
            "POST",
            "/organizations/%s/opportunities/%s/submissions"
            % (org_id, opp_id),
            user="bob", role="member",
            body={"submission_ref": "SUB-SVC",
                  "participant_ref": "PAR-SVC"})
        self.assertEqual(status, 201)
        status, award = c.call(
            "POST",
            "/organizations/%s/opportunities/%s/awards" % (org_id, opp_id),
            user="bob", role="member",
            body={"submission_id": sub["id"], "award_ref": "AWD-SVC",
                  "amount_cents": 900})
        self.assertEqual(status, 201)
        status, _ = c.call(
            "POST", "/organizations/%s/payments" % org_id, user="bob",
            role="member",
            body={"payment_ref": "PAY-SVC", "kind": "award_fee",
                  "amount_cents": 25, "opportunity_id": opp_id,
                  "award_id": award["id"]})
        self.assertEqual(status, 201)
        status, report = c.call("GET", "/organizations/%s/report" % org_id,
                                user="carol", role="viewer")
        self.assertEqual(status, 200)
        self.assertEqual(report["award_cents_total"], 900)
        self.assertEqual(report["payment_cents_total"], 25)

        # Audit: members are denied (403), admin reads, and the read
        # itself is audited.
        status, _ = c.call("GET", "/audit", user="bob", role="member")
        self.assertEqual(status, 403)
        status, audit_body = c.call("GET", "/audit", user="alice",
                                    role="admin")
        self.assertEqual(status, 200)
        actions = [e["action"] for e in audit_body["entries"]]
        self.assertIn("audit_read", actions)
        self.assertIn("modification_record", actions)

    def test_outsider_read_is_403(self):
        """Service / AC: a platform member outside the organization
        is denied its records with 403."""
        c = self.client
        status, org = c.call("POST", "/organizations", user="alice",
                             role="admin",
                             body={"org_ref": "ORG-PRIVATE",
                                   "label": "Private Org"})
        self.assertEqual(status, 201)
        status, _ = c.call("GET", "/organizations/%s/contracts" % org["id"],
                           user="dave", role="member")
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
