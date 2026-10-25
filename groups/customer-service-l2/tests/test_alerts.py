"""Alert/event records (Core function 5).

Claim trace: PagerDuty "automated detection, diagnosis, and response
to a wide range of events, including customer support alerts"
(event_detection_response). The records are Core; the detection and
orchestration ENGINES are Extended.
"""

import unittest

from custsvc.errors import NotFoundError, ValidationError
from custsvc_helpers import AGENT, make_case, make_store


class TestAlerts(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.requester, _, _ = make_store()

    def test_ingest_shape_and_state(self):
        alert = self.store.ingest_alert("monitor-7", "Portal latency high",
                                        "major", AGENT)
        self.assertTrue(alert["id"].startswith("alert-"))
        self.assertEqual(alert["state"], "new")
        self.assertIsNone(alert["case_id"])

    def test_source_is_opaque_ref_only(self):
        alert = self.store.ingest_alert("opaque-source-ref", "s", "info", AGENT)
        self.assertEqual(alert["source_ref"], "opaque-source-ref")
        for forbidden in ("phone", "email", "url"):
            self.assertNotIn(forbidden, alert)

    def test_bad_severity_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.ingest_alert("src", "s", "catastrophic", AGENT)

    def test_acknowledge_and_resolve(self):
        alert = self.store.ingest_alert("src", "s", "warning", AGENT)
        alert = self.store.acknowledge_alert(alert["id"], AGENT)
        self.assertEqual(alert["state"], "acknowledged")
        alert = self.store.resolve_alert(alert["id"], AGENT)
        self.assertEqual(alert["state"], "resolved")

    def test_link_to_case(self):
        case = make_case(self.store, self.requester)
        alert = self.store.ingest_alert("src", "s", "major", AGENT)
        alert = self.store.link_alert(alert["id"], case["id"], AGENT)
        self.assertEqual(alert["case_id"], case["id"])
        with self.assertRaises(NotFoundError):
            self.store.link_alert(alert["id"], "case-999", AGENT)

    def test_bulk_ingest(self):
        created = self.store.ingest_alerts([
            {"source_ref": "a", "summary": "one", "severity": "info"},
            {"source_ref": "b", "summary": "two", "severity": "critical"},
        ], AGENT)
        self.assertEqual(len(created), 2)
        self.assertEqual(len(self.store.list_alerts(AGENT)), 2)

    def test_bulk_ingest_is_atomic(self):
        with self.assertRaises(ValidationError):
            self.store.ingest_alerts([
                {"source_ref": "a", "summary": "one", "severity": "info"},
                {"source_ref": "b", "summary": "two", "severity": "bogus"},
            ], AGENT)
        self.assertEqual(self.store.list_alerts(AGENT), [])

    def test_list_filters(self):
        self.store.ingest_alert("a", "one", "info", AGENT)
        b = self.store.ingest_alert("b", "two", "major", AGENT)
        self.store.resolve_alert(b["id"], AGENT)
        self.assertEqual(len(self.store.list_alerts(AGENT, state="resolved")), 1)
        self.assertEqual(len(self.store.list_alerts(AGENT, state="new")), 1)


if __name__ == "__main__":
    unittest.main()
