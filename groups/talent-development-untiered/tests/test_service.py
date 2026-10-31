"""End-to-end tests over real HTTP against the service layer."""

import http.client
import json
import threading
import unittest

from talentdev.access import User
from talentdev.audit import AuditLog
from talentdev.service import make_server
from talentdev.store import TalentDevStore

USERS = {
    "alice": User("alice", "admin"),
    "bob": User("bob", "operator"),
    "carol": User("carol", "viewer"),
}


class Client:
    def __init__(self, port):
        self.port = port

    def request(self, method, path, body=None, user=None, role=None,
                headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdrs = {"Content-Type": "application/json"}
        if user is not None:
            hdrs["X-User"] = user
        if role is not None:
            hdrs["X-Role"] = role
        if headers:
            hdrs.update(headers)
        payload = json.dumps(body) if body is not None else None
        conn.request(method, path, body=payload, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            parsed = {"_raw": raw.decode("utf-8", "replace")}
        return resp.status, parsed


class TestService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = TalentDevStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, store=cls.store,
                                 audit=cls.audit, users=USERS)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()
        cls.client = Client(cls.port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health_is_public(self):
        status, payload = self.client.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["service"], "talentdev")

    def test_missing_or_bad_auth_is_401(self):
        status, _ = self.client.request("GET", "/organizations")
        self.assertEqual(status, 401)
        status, _ = self.client.request("GET", "/organizations",
                                        user="alice", role="viewer")
        self.assertEqual(status, 401)
        status, _ = self.client.request("GET", "/organizations",
                                        user="mallory", role="admin")
        self.assertEqual(status, 401)

    def test_full_flow(self):
        c = self.client
        status, org = c.request(
            "POST", "/organizations",
            {"ref": "agency-alpha", "label": "Agency Alpha"},
            user="bob", role="operator")
        self.assertEqual(status, 201)
        org_id = org["id"]

        status, program = c.request(
            "POST", "/programs",
            {"org_id": org_id, "label": "Leadership Path",
             "kind": "behavioral_mindset_development",
             "goal_label": "mission-readiness"},
            user="bob", role="operator")
        self.assertEqual(status, 201)

        # The coaching kind does not exist in this category's core.
        status, payload = c.request(
            "POST", "/programs",
            {"org_id": org_id, "label": "Coach", "kind": "coaching"},
            user="bob", role="operator")
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

        status, enrollment = c.request(
            "POST", "/participations",
            {"program_id": program["id"], "participant_ref": "person-001",
             "enrolled_at": "2026-10-01"},
            user="bob", role="operator")
        self.assertEqual(status, 201)
        self.assertEqual(enrollment["status"], "enrolled")

        status, done = c.request(
            "POST", "/participations/%s/complete" % enrollment["id"],
            {"completed_at": "2026-10-20"}, user="bob", role="operator")
        self.assertEqual(status, 200)
        self.assertEqual(done["status"], "completed")

        status, assessment = c.request(
            "POST", "/assessments",
            {"org_id": org_id, "label": "Baseline",
             "instrument_label": "Panel Instrument v2"},
            user="bob", role="operator")
        self.assertEqual(status, 201)

        status, result = c.request(
            "POST", "/results",
            {"assessment_id": assessment["id"], "subject_ref": "person-001",
             "outcome": "completed", "administered_at": "2026-10-05"},
            user="bob", role="operator")
        self.assertEqual(status, 201)

        # A judgment outcome is refused end to end.
        status, _ = c.request(
            "POST", "/results",
            {"assessment_id": assessment["id"], "subject_ref": "person-002",
             "outcome": "passed", "administered_at": "2026-10-05"},
            user="bob", role="operator")
        self.assertEqual(status, 400)

        status, snapshot = c.request(
            "POST", "/snapshots",
            {"org_id": org_id, "metric_label": "trend-index",
             "period_label": "2026-Q4", "cohort_size": 40,
             "value_count": 12},
            user="bob", role="operator")
        self.assertEqual(status, 201)

        # The small-cohort guard binds end to end: a snapshot over
        # a cohort of three is a 400 and records nothing.
        status, payload = c.request(
            "POST", "/snapshots",
            {"org_id": org_id, "metric_label": "trend-index",
             "period_label": "2026-Q4", "cohort_size": 3,
             "value_count": 1},
            user="bob", role="operator")
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

        status, decision = c.request(
            "POST", "/decisions",
            {"org_id": org_id, "label": "Expand the program",
             "decision": "approved", "decided_by_ref": "board-ref-1",
             "basis_assessment_ids": [assessment["id"]],
             "basis_snapshot_ids": [snapshot["id"]]},
            user="bob", role="operator")
        self.assertEqual(status, 201)

        status, summary = c.request("GET", "/summary",
                                    user="carol", role="viewer")
        self.assertEqual(status, 200)
        self.assertEqual(summary["organizations"], 1)
        self.assertEqual(summary["snapshots"], 1)
        self.assertEqual(summary["participations_by_status"],
                         {"enrolled": 0, "completed": 1})

        status, found = c.request("GET", "/search?q=leadership",
                                  user="carol", role="viewer")
        self.assertEqual(status, 200)
        self.assertEqual(len(found["programs"]), 1)

    def test_denied_write_is_403_and_audited(self):
        before = len(self.audit.entries())
        status, payload = self.client.request(
            "POST", "/organizations", {"ref": "agency-x", "label": "X"},
            user="carol", role="viewer")
        self.assertEqual(status, 403)
        self.assertIn("error", payload)
        entries = self.audit.entries()
        self.assertGreater(len(entries), before)
        self.assertTrue(any(e["action"].endswith(":denied")
                            for e in entries[before:]))

    def test_audit_endpoint_requires_audit_read(self):
        status, _ = self.client.request("GET", "/audit",
                                        user="bob", role="operator")
        self.assertEqual(status, 403)
        status, payload = self.client.request("GET", "/audit",
                                              user="alice", role="admin")
        self.assertEqual(status, 200)
        self.assertIn("entries", payload)

    def test_not_found_and_method_not_allowed(self):
        status, _ = self.client.request("GET", "/organizations/org-99",
                                        user="alice", role="admin")
        self.assertEqual(status, 404)
        status, _ = self.client.request("DELETE", "/organizations",
                                        user="alice", role="admin")
        self.assertIn(status, (404, 405))
        status, _ = self.client.request("GET", "/nope",
                                        user="alice", role="admin")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
