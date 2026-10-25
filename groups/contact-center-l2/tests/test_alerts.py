"""Alert tests: lifecycle guards.

Traces to: Core function 6 -- Alerts; contract for
``ContactStore.raise_alert/acknowledge_alert/resolve_alert/
get_alert/list_alerts``. Sibling claim family: observability
alerting (LogicMonitor-style raise/ack/resolve records).
"""

import unittest

from contact_helpers import OPERATOR, VIEWER, fresh_store, make_store
from contact.errors import NotFoundError, PermissionDenied, ValidationError


class TestRaiseAlert(unittest.TestCase):
    """Core 6: Alerts -- raising."""

    def test_raise_shape(self):
        """Core 6: Alerts. raise_alert returns alr- id, status raised, severity/message/source stored."""
        store, agent, contact, queue = make_store()
        case = store.create_case(OPERATOR, "claim", "s")
        alert = store.raise_alert(OPERATOR, "critical", "Queue down", source="monitor",
                                  case_id=case["id"])
        self.assertEqual(alert["id"], "alr-1")
        self.assertEqual(alert["status"], "raised")
        self.assertEqual(alert["severity"], "critical")
        self.assertEqual(alert["case_id"], case["id"])

    def test_all_severities(self):
        """Core 6: Alerts. severity in {info, warning, critical} all accepted."""
        store = fresh_store()
        for severity in ("info", "warning", "critical"):
            self.assertEqual(store.raise_alert(OPERATOR, severity, "m")["severity"], severity)

    def test_raise_validation_no_id_on_failure(self):
        """Core 6: Alerts (SI-10). Bad severity / empty message -> ValidationError; unknown case -> NotFoundError; no id consumed."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.raise_alert(OPERATOR, "fatal", "m")
        with self.assertRaises(ValidationError):
            store.raise_alert(OPERATOR, "info", "")
        with self.assertRaises(NotFoundError):
            store.raise_alert(OPERATOR, "info", "m", case_id="case-999")
        self.assertEqual(store.raise_alert(OPERATOR, "info", "ok")["id"], "alr-1")

    def test_viewer_cannot_raise(self):
        """Core 6/11: Alerts/RBAC. Viewer raise_alert -> PermissionDenied."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.raise_alert(VIEWER, "info", "m")


class TestAlertLifecycle(unittest.TestCase):
    """Core 6: Alerts -- acknowledge/resolve lifecycle guards."""

    def test_ack_then_resolve(self):
        """Core 6: Alerts. raised->acknowledged->resolved."""
        store = fresh_store()
        alert = store.raise_alert(OPERATOR, "warning", "m")
        self.assertEqual(store.acknowledge_alert(alert["id"], OPERATOR)["status"], "acknowledged")
        self.assertEqual(store.resolve_alert(alert["id"], OPERATOR)["status"], "resolved")

    def test_resolve_directly_from_raised(self):
        """Core 6: Alerts. raised->resolved directly is allowed."""
        store = fresh_store()
        alert = store.raise_alert(OPERATOR, "info", "m")
        self.assertEqual(store.resolve_alert(alert["id"], OPERATOR)["status"], "resolved")

    def test_lifecycle_guards(self):
        """Core 6: Alerts. Ack from acknowledged/resolved and resolve from resolved -> ValidationError."""
        store = fresh_store()
        alert = store.raise_alert(OPERATOR, "info", "m")
        store.acknowledge_alert(alert["id"], OPERATOR)
        with self.assertRaises(ValidationError):
            store.acknowledge_alert(alert["id"], OPERATOR)
        store.resolve_alert(alert["id"], OPERATOR)
        with self.assertRaises(ValidationError):
            store.acknowledge_alert(alert["id"], OPERATOR)
        with self.assertRaises(ValidationError):
            store.resolve_alert(alert["id"], OPERATOR)
        self.assertEqual(store.get_alert(alert["id"], OPERATOR)["status"], "resolved")

    def test_unknown_alert_not_found_and_list(self):
        """Core 6: Alerts. Unknown id -> NotFoundError; list_alerts returns all for viewer."""
        store = fresh_store()
        store.raise_alert(OPERATOR, "info", "a")
        store.raise_alert(OPERATOR, "warning", "b")
        self.assertEqual(len(store.list_alerts(VIEWER)), 2)
        with self.assertRaises(NotFoundError):
            store.get_alert("alr-999", OPERATOR)
        with self.assertRaises(NotFoundError):
            store.acknowledge_alert("alr-999", OPERATOR)


if __name__ == "__main__":
    unittest.main()
