"""Finding / remediation (POA&M-style) record tests.

Traces to: Core function 5 (finding / remediation records — severity
recorded verbatim, source, due date, lifecycle enforced by a transition
table, accepted_risk requires a recorded rationale; any date-based
status such as "overdue" is DERIVED at read time from due date +
lifecycle state + an as_of parameter, NEVER stored); control family
CA-5 (plan of action and milestones).
"""

import unittest

from grc_helpers import ADMIN, MEMBER, VIEWER, SYSTEM_REF, make_finding, make_store
from grc.errors import NotFoundError, PermissionDenied, ValidationError
from grc.store import (
    FINDING_STATUSES,
    FINDING_TRANSITIONS,
    OVERDUE_STATES,
    derive_finding_status,
)

# Shortest legal path from "open" to each status, per FINDING_TRANSITIONS.
PATH_TO = {
    "open": [],
    "in_progress": ["in_progress"],
    "remediated": ["in_progress", "remediated"],
    "validated": ["in_progress", "remediated", "validated"],
    "closed": ["in_progress", "remediated", "validated", "closed"],
    "accepted_risk": ["accepted_risk"],
}

ALLOWED = [
    ("open", "in_progress"), ("open", "accepted_risk"),
    ("in_progress", "remediated"), ("in_progress", "accepted_risk"),
    ("remediated", "validated"), ("remediated", "in_progress"),
    ("validated", "closed"),
    ("accepted_risk", "in_progress"), ("accepted_risk", "closed"),
]

FORBIDDEN = [
    ("open", "remediated"), ("open", "validated"), ("open", "closed"),
    ("open", "open"),
    ("in_progress", "validated"), ("in_progress", "closed"),
    ("in_progress", "open"),
    ("remediated", "closed"), ("remediated", "accepted_risk"),
    ("remediated", "open"),
    ("validated", "in_progress"), ("validated", "remediated"),
    ("validated", "accepted_risk"), ("validated", "open"),
    ("accepted_risk", "remediated"), ("accepted_risk", "validated"),
    ("accepted_risk", "open"),
    ("closed", "open"), ("closed", "in_progress"), ("closed", "closed"),
]


class FindingBase(unittest.TestCase):
    """A fresh store with one system; findings are created per test."""

    def setUp(self):
        self.store, self.system, self.indicator = make_store()

    def finding_in(self, status, **kwargs):
        """Create a finding and drive it to ``status`` legally."""
        kwargs.setdefault("due_date", "2026-06-30")
        finding = make_finding(self.store, **kwargs)
        for step in PATH_TO[status]:
            extra = {}
            if step == "accepted_risk":
                extra["rationale"] = "documented compensating control"
            finding = self.store.transition_finding(
                finding["id"], step, actor=MEMBER, **extra
            )
        self.assertEqual(finding["status"], status)
        return finding


class TestFindingCreation(FindingBase):
    """Core 5: finding record creation."""

    def test_create_finding_shape(self):
        """Core 5. A finding record carries title, system, severity,
        source, due date, control links, lifecycle status "open", a
        null risk rationale, and provenance."""
        finding = make_finding(self.store, control_ids=["SI-2"])
        self.assertEqual(finding["id"], "find-1")
        self.assertEqual(finding["title"], "Unpatched component")
        self.assertEqual(finding["system_ref"], SYSTEM_REF)
        self.assertEqual(finding["severity"], "high")
        self.assertEqual(finding["source"], "assessment")
        self.assertEqual(finding["due_date"], "2026-06-30")
        self.assertEqual(finding["control_ids"], ["SI-2"])
        self.assertEqual(finding["status"], "open")
        self.assertIsNone(finding["risk_rationale"])
        self.assertEqual(finding["created_by"], "bob")

    def test_severity_is_recorded_verbatim(self):
        """Core 5. Severity is stored exactly as supplied — house,
        vendor, or free wording is never normalized or scored."""
        for severity in ["high", "HIGH", "Sev-2 (vendor wording)", "urgent-ish"]:
            finding = make_finding(self.store, severity=severity)
            self.assertEqual(finding["severity"], severity)
        severities = [
            f["severity"] for f in self.store.list_findings(actor=ADMIN)
        ]
        self.assertEqual(
            severities, ["high", "HIGH", "Sev-2 (vendor wording)", "urgent-ish"]
        )

    def test_create_finding_validation(self):
        """Core 5. Unknown system (NotFoundError), unknown control,
        malformed due date, and empty title/severity/source are each
        rejected; failures consume no finding id."""
        with self.assertRaises(NotFoundError):
            make_finding(self.store, system_ref="NOPE")
        with self.assertRaises(ValidationError):
            make_finding(self.store, control_ids=["ZZ-9"])
        with self.assertRaises(ValidationError):
            make_finding(self.store, due_date="June 30 2026")
        with self.assertRaises(ValidationError):
            make_finding(self.store, due_date="2026-13-40")
        with self.assertRaises(ValidationError):
            make_finding(self.store, title="")
        with self.assertRaises(ValidationError):
            make_finding(self.store, severity="")
        with self.assertRaises(ValidationError):
            make_finding(self.store, source="")
        finding = make_finding(self.store)
        self.assertEqual(finding["id"], "find-1")

    def test_no_score_or_rating_fields_anywhere(self):
        """Core 5 + Core 7. A finding record carries no computed score,
        rating, band, or derived status key — severity is a recorded
        string, nothing is computed from it."""
        finding = make_finding(self.store)
        for key in finding:
            lowered = key.lower()
            self.assertNotIn("score", lowered)
            self.assertNotIn("rating", lowered)
            self.assertNotIn("band", lowered)
            self.assertNotIn("derived", lowered)
            self.assertNotIn("overdue", lowered)


class TestFindingLifecycle(FindingBase):
    """Core 5: the lifecycle transition table."""

    def test_transition_map_matches_the_contract(self):
        """Core 5. FINDING_TRANSITIONS is exactly {open: {in_progress,
        accepted_risk}, in_progress: {remediated, accepted_risk},
        remediated: {validated, in_progress}, validated: {closed},
        accepted_risk: {in_progress, closed}, closed: {}} and the
        status set is exactly the six lifecycle states."""
        self.assertEqual(
            FINDING_TRANSITIONS,
            {
                "open": {"in_progress", "accepted_risk"},
                "in_progress": {"remediated", "accepted_risk"},
                "remediated": {"validated", "in_progress"},
                "validated": {"closed"},
                "accepted_risk": {"in_progress", "closed"},
                "closed": set(),
            },
        )
        self.assertEqual(
            set(FINDING_STATUSES),
            {"open", "in_progress", "remediated", "validated", "closed", "accepted_risk"},
        )

    def test_every_allowed_transition_succeeds(self):
        """Core 5. Every (from, to) pair in the transition table is
        accepted along a legal path."""
        for start, target in ALLOWED:
            finding = self.finding_in(start)
            extra = {}
            if target == "accepted_risk":
                extra["rationale"] = "documented compensating control"
            moved = self.store.transition_finding(
                finding["id"], target, actor=MEMBER, **extra
            )
            self.assertEqual(moved["status"], target, "%s -> %s" % (start, target))

    def test_forbidden_transitions_are_denied(self):
        """Core 5. A representative forbidden set (skipping states,
        going backwards, same-status, anything out of terminal
        "closed") is a ValidationError and leaves the status
        unchanged."""
        for start, target in FORBIDDEN:
            finding = self.finding_in(start)
            extra = {}
            if target == "accepted_risk":
                extra["rationale"] = "documented compensating control"
            with self.assertRaises(ValidationError, msg="%s -> %s" % (start, target)):
                self.store.transition_finding(
                    finding["id"], target, actor=MEMBER, **extra
                )
            stored = self.store.get_finding(finding["id"], actor=ADMIN)
            self.assertEqual(stored["status"], start)

    def test_full_legal_path_open_to_closed(self):
        """Core 5. The canonical POA&M path open -> in_progress ->
        remediated -> validated -> closed succeeds end to end."""
        finding = make_finding(self.store)
        for step in ["in_progress", "remediated", "validated", "closed"]:
            finding = self.store.transition_finding(finding["id"], step, actor=MEMBER)
        self.assertEqual(finding["status"], "closed")

    def test_accepted_risk_requires_recorded_rationale(self):
        """Core 5. open -> accepted_risk without a rationale (or with
        an empty one) is a ValidationError; with a rationale the
        transition succeeds and the rationale is recorded on the
        finding."""
        finding = make_finding(self.store)
        with self.assertRaises(ValidationError):
            self.store.transition_finding(finding["id"], "accepted_risk", actor=MEMBER)
        with self.assertRaises(ValidationError):
            self.store.transition_finding(
                finding["id"], "accepted_risk", actor=MEMBER, rationale="  "
            )
        moved = self.store.transition_finding(
            finding["id"],
            "accepted_risk",
            actor=MEMBER,
            rationale="compensating control verified 2026-05-01",
        )
        self.assertEqual(moved["status"], "accepted_risk")
        self.assertEqual(
            moved["risk_rationale"], "compensating control verified 2026-05-01"
        )

    def test_transition_unknown_status_and_missing_finding(self):
        """Core 5. An unknown target status is a ValidationError; a
        missing finding is a NotFoundError."""
        finding = make_finding(self.store)
        with self.assertRaises(ValidationError):
            self.store.transition_finding(finding["id"], "banana", actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.transition_finding("find-404", "in_progress", actor=MEMBER)

    def test_viewer_may_not_transition(self):
        """Core 5 + Core 9 RBAC. A viewer may read a finding but may
        not move it (PermissionDenied)."""
        finding = make_finding(self.store)
        self.assertEqual(
            self.store.get_finding(finding["id"], actor=VIEWER)["status"], "open"
        )
        with self.assertRaises(PermissionDenied):
            self.store.transition_finding(finding["id"], "in_progress", actor=VIEWER)


class TestDerivedStatus(FindingBase):
    """Core 5: overdue is derived at read time, never stored."""

    def test_overdue_states_are_the_open_work_states(self):
        """Core 5. Only open / in_progress findings can be overdue."""
        self.assertEqual(set(OVERDUE_STATES), {"open", "in_progress"})

    def test_current_before_and_on_due_date(self):
        """Core 5 derivation. An open finding due 2026-06-30 derives
        its lifecycle status (not overdue) before the due date and on
        the due date itself."""
        finding = make_finding(self.store, due_date="2026-06-30")
        self.assertEqual(derive_finding_status(finding, "2026-06-29"), "open")
        self.assertEqual(derive_finding_status(finding, "2026-06-30"), "open")

    def test_overdue_after_due_date(self):
        """Core 5 derivation. The same open finding derives "overdue"
        the day after its due date, and an in_progress finding past
        due derives "overdue" too."""
        finding = make_finding(self.store, due_date="2026-06-30")
        self.assertEqual(derive_finding_status(finding, "2026-07-01"), "overdue")
        moved = self.store.transition_finding(finding["id"], "in_progress", actor=MEMBER)
        self.assertEqual(derive_finding_status(moved, "2026-07-01"), "overdue")

    def test_not_overdue_once_remediated_validated_or_closed(self):
        """Core 5 derivation. Past its due date, a finding that has
        been remediated (then validated, then closed) never derives
        "overdue" — it derives its lifecycle status."""
        for status in ["remediated", "validated", "closed"]:
            finding = self.finding_in(status, due_date="2026-06-30")
            self.assertEqual(
                derive_finding_status(finding, "2027-01-01"), status
            )

    def test_not_overdue_once_risk_accepted(self):
        """Core 5 derivation. A risk-accepted finding past due derives
        "accepted_risk", not "overdue": the recorded rationale, not
        the calendar, governs it."""
        finding = self.finding_in("accepted_risk", due_date="2026-06-30")
        self.assertEqual(
            derive_finding_status(finding, "2027-01-01"), "accepted_risk"
        )

    def test_stored_record_carries_no_derived_status(self):
        """Core 5 derivation. The stored record is shown to carry no
        derived status key: get_finding without as_of returns exactly
        the stored fields; asking with as_of adds derived_status to
        the returned copy only, and a later plain read still has no
        derived key (nothing was written back)."""
        finding = make_finding(self.store, due_date="2026-06-30")
        plain = self.store.get_finding(finding["id"], actor=ADMIN)
        self.assertNotIn("derived_status", plain)
        self.assertNotIn("overdue", plain)
        derived = self.store.get_finding(
            finding["id"], actor=ADMIN, as_of="2026-07-15"
        )
        self.assertEqual(derived["derived_status"], "overdue")
        again = self.store.get_finding(finding["id"], actor=ADMIN)
        self.assertNotIn("derived_status", again)
        for listed in self.store.list_findings(actor=ADMIN):
            self.assertNotIn("derived_status", listed)

    def test_list_findings_with_as_of_attaches_derivation(self):
        """Core 5 derivation. list_findings(as_of=...) attaches the
        read-time derivation per finding: past-due open is "overdue",
        past-due remediated is its lifecycle status."""
        open_finding = make_finding(self.store, due_date="2026-06-30")
        done = self.finding_in("remediated", due_date="2026-06-30")
        listed = {
            f["id"]: f
            for f in self.store.list_findings(actor=ADMIN, as_of="2026-12-31")
        }
        self.assertEqual(listed[open_finding["id"]]["derived_status"], "overdue")
        self.assertEqual(listed[done["id"]]["derived_status"], "remediated")

    def test_list_findings_filters(self):
        """Core 5. list_findings filters by system and by lifecycle
        status."""
        self.store.create_system("SYS-002", "second", actor=MEMBER)
        first = make_finding(self.store)
        second = make_finding(self.store, system_ref="SYS-002")
        self.store.transition_finding(second["id"], "in_progress", actor=MEMBER)
        by_system = self.store.list_findings(actor=ADMIN, system_ref="SYS-002")
        self.assertEqual([f["id"] for f in by_system], [second["id"]])
        by_status = self.store.list_findings(actor=ADMIN, status="open")
        self.assertEqual([f["id"] for f in by_status], [first["id"]])


if __name__ == "__main__":
    unittest.main()
