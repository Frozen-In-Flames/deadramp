"""Service contract: the HTTP layer over the store.

Traces to: UNION-SPEC.md "Implementation contract" (service.py) —
live HTTP on an ephemeral port: /health without auth; 401 for
unknown users and role mismatches (audited :denied); 403 for a
member creating an organization and for an outsider reading one;
404 for unknown routes; the full acquisition flow; the stage
bounds rule over HTTP (out-of-bounds and non-integer stage
indices -> 400); the audit endpoint is admin-only and the read
itself is audited.
"""

import http.client
import json
import threading
import unittest

import talentmgmt_helpers as H
from talentmgmt.audit import AuditLog
from talentmgmt.service import make_server
from talentmgmt.store import TalentMgmtStore


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


class TestService(unittest.TestCase):
    """The HTTP service honors the contract end to end."""

    def setUp(self):
        self.audit = AuditLog()
        self.store = TalentMgmtStore(audit=self.audit)
        self.server = make_server("127.0.0.1", 0, self.store, self.audit,
                                  dict(H.USERS_REGISTRY))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def _org(self):
        status, org = call(self.port, "POST", "/organizations",
                           "alice", "admin",
                           {"org_ref": H.ORG_REF, "label": H.ORG_LABEL})
        assert status == 201, (status, org)
        call(self.port, "POST", "/organizations/%s/members" % org["id"],
             "alice", "admin", {"username": "bob"})
        call(self.port, "POST", "/organizations/%s/members" % org["id"],
             "alice", "admin", {"username": "carol"})
        return org["id"]

    def test_health_needs_no_auth(self):
        """Service: GET /health answers 200 without credentials."""
        status, body = call(self.port, "GET", "/health")
        self.assertEqual((status, body), (200, {"status": "ok"}))

    def test_401_unknown_user_and_role_mismatch_audited(self):
        """Service / AU: unknown users and role mismatches get
        401, and the denials are audited with :denied."""
        status, _ = call(self.port, "GET", "/organizations",
                         "mallory", "admin")
        self.assertEqual(status, 401)
        status, _ = call(self.port, "GET", "/organizations",
                         "alice", "viewer")
        self.assertEqual(status, 401)
        denied = [e for e in self.audit.entries()
                  if e["action"].endswith(":denied")]
        self.assertEqual(len(denied), 2)

    def test_403_member_creating_org_and_outsider_reading(self):
        """Service / AC: a member cannot create an organization
        (org_write is admin's), and an outsider cannot read one."""
        status, _ = call(self.port, "POST", "/organizations",
                         "bob", "member", {"org_ref": "O", "label": "L"})
        self.assertEqual(status, 403)
        org_id = self._org()
        status, _ = call(self.port, "GET", "/organizations/%s" % org_id,
                         "dave", "member")
        self.assertEqual(status, 403)

    def test_404_unknown_route(self):
        """Service: an unmatched route returns 404 JSON."""
        status, body = call(self.port, "GET", "/nope", "alice", "admin")
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_full_flow_and_bounds_over_http(self):
        """Service (Core 2-5, 11): candidate -> requisition ->
        pipeline -> placement -> movement over HTTP; the derived
        stage appears in the placements list and the report; an
        out-of-bounds index and a string index both return 400."""
        org_id = self._org()
        status, candidate = call(
            self.port, "POST", "/organizations/%s/candidates" % org_id,
            "bob", "member",
            {"candidate_ref": H.CANDIDATE_REF, "label": H.CANDIDATE_LABEL})
        self.assertEqual(status, 201, candidate)
        status, requisition = call(
            self.port, "POST", "/organizations/%s/requisitions" % org_id,
            "bob", "member",
            {"requisition_ref": H.REQUISITION_REF,
             "title": H.REQUISITION_TITLE})
        self.assertEqual(status, 201, requisition)
        status, pipeline = call(
            self.port, "POST", "/organizations/%s/pipelines" % org_id,
            "bob", "member",
            {"pipeline_ref": H.PIPELINE_REF,
             "requisition_id": requisition["id"], "stages": H.STAGES})
        self.assertEqual(status, 201, pipeline)
        status, placement = call(
            self.port, "POST",
            "/organizations/%s/pipelines/%s/placements"
            % (org_id, pipeline["id"]),
            "bob", "member",
            {"placement_ref": H.PLACEMENT_REF,
             "candidate_ref": H.CANDIDATE_REF})
        self.assertEqual(status, 201, placement)
        self.assertNotIn("current_stage", placement)
        status, _ = call(
            self.port, "POST",
            "/organizations/%s/placements/%s/movements"
            % (org_id, placement["id"]),
            "bob", "member", {"movement_ref": "MOV-1", "stage_index": 2})
        self.assertEqual(status, 201)
        status, body = call(
            self.port, "POST",
            "/organizations/%s/placements/%s/movements"
            % (org_id, placement["id"]),
            "bob", "member", {"movement_ref": "MOV-2", "stage_index": 99})
        self.assertEqual(status, 400, body)
        status, body = call(
            self.port, "POST",
            "/organizations/%s/placements/%s/movements"
            % (org_id, placement["id"]),
            "bob", "member", {"movement_ref": "MOV-3", "stage_index": "2"})
        self.assertEqual(status, 400, body)
        status, placements = call(
            self.port, "GET", "/organizations/%s/placements" % org_id,
            "carol", "viewer")
        self.assertEqual(status, 200)
        self.assertEqual(placements["placements"][0]["current_stage"],
                         "Interview")
        status, report = call(
            self.port, "GET", "/organizations/%s/report" % org_id,
            "carol", "viewer")
        self.assertEqual(status, 200)
        self.assertEqual(report["placements_by_stage"], {"Interview": 1})

    def test_audit_endpoint_admin_only_and_read_audited(self):
        """Service / AU: /audit requires audit_read (admin only),
        and the successful read is itself recorded."""
        org_id = self._org()
        status, _ = call(self.port, "GET", "/audit", "bob", "member")
        self.assertEqual(status, 403)
        status, body = call(self.port, "GET", "/audit", "alice", "admin")
        self.assertEqual(status, 200)
        actions = [e["action"] for e in body["entries"]]
        self.assertIn("organization_create", actions)
        self.assertEqual(actions[-1], "audit_read")


if __name__ == "__main__":
    unittest.main()
