"""Incidents tests.

Traces to: Core -- Incidents (inc-) lifecycle and severity
validation; SEVERITIES = (info, warning, critical).
"""

import unittest

from construct_helpers import ADMIN, OPERATOR, VIEWER, make_store
from construct.errors import ValidationError
from construct.store import SEVERITIES


class TestIncidents(unittest.TestCase):
    """Incidents: creation, lifecycle, guards."""

    def test_create_shape_and_severities(self):
        """Incidents. create makes inc- reported; every severity accepted; default info."""
        store, project, prime, sub = make_store()
        for i, sev in enumerate(SEVERITIES):
            rec = store.create_incident(OPERATOR, project["id"], "safety", "Event %s" % sev, severity=sev)
            self.assertEqual(rec["id"], "inc-%d" % (i + 1))
            self.assertEqual(rec["severity"], sev)
            self.assertEqual(rec["status"], "reported")
        default = store.create_incident(OPERATOR, project["id"], "note", "Plain event")
        self.assertEqual(default["severity"], "info")

    def test_validation(self):
        """Incidents. Bad severity / empty category / empty description -> ValidationError."""
        store, project, prime, sub = make_store()
        with self.assertRaises(ValidationError):
            store.create_incident(OPERATOR, project["id"], "safety", "X", severity="fatal")
        with self.assertRaises(ValidationError):
            store.create_incident(OPERATOR, project["id"], "", "X")
        with self.assertRaises(ValidationError):
            store.create_incident(OPERATOR, project["id"], "safety", "  ")
        rec = store.create_incident(OPERATOR, project["id"], "safety", "Good")
        self.assertEqual(rec["id"], "inc-1")

    def test_lifecycle_and_return_path(self):
        """Incidents. reported->under_review->reported->under_review->closed succeeds."""
        store, project, prime, sub = make_store()
        rec = store.create_incident(OPERATOR, project["id"], "safety", "Near miss")
        for to in ("under_review", "reported", "under_review", "closed"):
            rec = store.transition_incident(rec["id"], OPERATOR, to)
            self.assertEqual(rec["status"], to)

    def test_guards(self):
        """Incidents. reported->closed directly and closed->reported -> ValidationError."""
        store, project, prime, sub = make_store()
        rec = store.create_incident(OPERATOR, project["id"], "safety", "Near miss")
        with self.assertRaises(ValidationError):
            store.transition_incident(rec["id"], OPERATOR, "closed")
        store.transition_incident(rec["id"], OPERATOR, "under_review")
        store.transition_incident(rec["id"], OPERATOR, "closed")
        with self.assertRaises(ValidationError):
            store.transition_incident(rec["id"], OPERATOR, "reported")

    def test_list_filters(self):
        """Incidents. list_incidents filters by project_id and status."""
        store, project, prime, sub = make_store()
        store.create_incident(OPERATOR, project["id"], "safety", "One")
        r2 = store.create_incident(OPERATOR, project["id"], "quality", "Two")
        store.transition_incident(r2["id"], OPERATOR, "under_review")
        self.assertEqual(len(store.list_incidents(VIEWER, project_id=project["id"])), 2)
        self.assertEqual(len(store.list_incidents(VIEWER, status="reported")), 1)
        self.assertEqual(len(store.list_incidents(VIEWER, status="under_review")), 1)


if __name__ == "__main__":
    unittest.main()
