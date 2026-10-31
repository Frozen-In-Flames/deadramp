"""Assessment & authorization-readiness record tests.

Traces to: Core function 6 (assessment & authorization-readiness
records — assessment records against a system/framework with scope,
assessor reference, date, and the result recorded verbatim; and
authorization status records whose transitions are guarded);
control families CA-2 / CA-6.
"""

import unittest

from grc_helpers import ADMIN, MEMBER, VIEWER, SEED_FRAMEWORK_ID, SYSTEM_REF, make_store
from grc.errors import NotFoundError, PermissionDenied, ValidationError
from grc.store import AUTH_STATUSES, AUTH_TRANSITIONS

# Shortest legal path from "not_started" to each status.
PATH_TO = {
    "not_started": [],
    "in_progress": ["in_progress"],
    "authorized": ["in_progress", "authorized"],
    "denied": ["in_progress", "denied"],
    "expired": ["in_progress", "authorized", "expired"],
    "revoked": ["in_progress", "authorized", "revoked"],
}


class TestAssessments(unittest.TestCase):
    """Core 6: assessment records."""

    def setUp(self):
        self.store, self.system, self.indicator = make_store()

    def _assess(self, **kwargs):
        kwargs.setdefault("actor", MEMBER)
        return self.store.create_assessment(
            SYSTEM_REF,
            SEED_FRAMEWORK_ID,
            "full system, all controls",
            "assessor-7",
            "2026-09-15",
            "Satisfied (as reported)",
            **kwargs,
        )

    def test_create_assessment_shape(self):
        """Core 6. An assessment record carries system, framework,
        scope, assessor reference, date, result, notes, and
        provenance, with a sequential asmt- id."""
        assessment = self._assess()
        self.assertEqual(assessment["id"], "asmt-1")
        self.assertEqual(assessment["system_ref"], SYSTEM_REF)
        self.assertEqual(assessment["framework_id"], SEED_FRAMEWORK_ID)
        self.assertEqual(assessment["scope"], "full system, all controls")
        self.assertEqual(assessment["assessor"], "assessor-7")
        self.assertEqual(assessment["date"], "2026-09-15")
        self.assertEqual(assessment["result"], "Satisfied (as reported)")
        self.assertEqual(assessment["created_by"], "bob")

    def test_assessment_result_recorded_verbatim(self):
        """Core 6. The assessment result is stored exactly as the
        assessor reported it — never normalized, mapped, or computed."""
        for result in ["pass", "Other Than Satisfied", "2 of 21 controls open"]:
            record = self.store.create_assessment(
                SYSTEM_REF, SEED_FRAMEWORK_ID, "scoped", "assessor-1",
                "2026-09-15", result, actor=MEMBER,
            )
            self.assertEqual(record["result"], result)

    def test_assessment_requires_known_system_and_framework(self):
        """Core 6. An unknown system or framework is a NotFoundError
        and consumes no assessment id."""
        with self.assertRaises(NotFoundError):
            self.store.create_assessment(
                "NOPE", SEED_FRAMEWORK_ID, "s", "a", "2026-09-15", "r", actor=MEMBER
            )
        with self.assertRaises(NotFoundError):
            self.store.create_assessment(
                SYSTEM_REF, "NOPE", "s", "a", "2026-09-15", "r", actor=MEMBER
            )
        self.assertEqual(self._assess()["id"], "asmt-1")

    def test_assessment_validation(self):
        """Core 6. Empty scope/assessor/result and a malformed date
        are each a ValidationError."""
        base = dict(
            system_ref=SYSTEM_REF, framework_id=SEED_FRAMEWORK_ID,
            scope="s", assessor="a", assessment_date="2026-09-15",
            result="r", actor=MEMBER,
        )
        for override in [
            {"scope": ""}, {"assessor": ""}, {"result": ""},
            {"assessment_date": "15/09/2026"},
        ]:
            with self.assertRaises(ValidationError):
                self.store.create_assessment(**{**base, **override})

    def test_assessment_list_filters_and_get(self):
        """Core 6. Assessments list with system/framework filters;
        an unknown id is a NotFoundError."""
        first = self._assess()
        self.store.create_system("SYS-002", "second", actor=MEMBER)
        second = self.store.create_assessment(
            "SYS-002", SEED_FRAMEWORK_ID, "s", "a", "2026-09-16", "open items",
            actor=MEMBER,
        )
        by_system = self.store.list_assessments(actor=ADMIN, system_ref="SYS-002")
        self.assertEqual([a["id"] for a in by_system], [second["id"]])
        self.assertEqual(
            self.store.get_assessment(first["id"], actor=VIEWER)["id"], first["id"]
        )
        with self.assertRaises(NotFoundError):
            self.store.get_assessment("asmt-404", actor=ADMIN)


class TestAuthorizations(unittest.TestCase):
    """Core 6: authorization status records with guarded transitions."""

    def setUp(self):
        self.store, self.system, self.indicator = make_store()

    def _auth(self, **kwargs):
        kwargs.setdefault("actor", ADMIN)
        return self.store.create_authorization(
            SYSTEM_REF, SEED_FRAMEWORK_ID, **kwargs
        )

    def auth_in(self, status):
        record = self._auth()
        for step in PATH_TO[status]:
            record = self.store.transition_authorization(
                record["id"], step, actor=ADMIN
            )
        self.assertEqual(record["status"], status)
        return record

    def test_transition_map_matches_the_contract(self):
        """Core 6. AUTH_TRANSITIONS is exactly {not_started:
        {in_progress}, in_progress: {authorized, denied}, denied:
        {in_progress}, authorized: {expired, revoked}, expired:
        {in_progress}, revoked: {}}."""
        self.assertEqual(
            AUTH_TRANSITIONS,
            {
                "not_started": {"in_progress"},
                "in_progress": {"authorized", "denied"},
                "denied": {"in_progress"},
                "authorized": {"expired", "revoked"},
                "expired": {"in_progress"},
                "revoked": set(),
            },
        )
        self.assertEqual(
            set(AUTH_STATUSES),
            {"not_started", "in_progress", "authorized", "denied", "expired", "revoked"},
        )

    def test_create_authorization_shape_and_history(self):
        """Core 6. A new authorization record starts in the recorded
        initial status with a one-step history (from None) carrying
        the actor and a UTC timestamp."""
        record = self._auth()
        self.assertEqual(record["id"], "auth-1")
        self.assertEqual(record["status"], "not_started")
        self.assertEqual(record["system_ref"], SYSTEM_REF)
        self.assertEqual(record["framework_id"], SEED_FRAMEWORK_ID)
        self.assertEqual(len(record["history"]), 1)
        self.assertIsNone(record["history"][0]["from"])
        self.assertEqual(record["history"][0]["to"], "not_started")
        self.assertEqual(record["history"][0]["by"], "alice")

    def test_create_authorization_bad_initial_status(self):
        """Core 6. An initial status outside AUTH_STATUSES is a
        ValidationError; unknown system/framework is NotFoundError."""
        with self.assertRaises(ValidationError):
            self._auth(status="banana")
        with self.assertRaises(NotFoundError):
            self.store.create_authorization("NOPE", SEED_FRAMEWORK_ID, actor=ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.create_authorization(SYSTEM_REF, "NOPE", actor=ADMIN)

    def test_legal_path_and_history_growth(self):
        """Core 6. not_started -> in_progress -> authorized succeeds,
        and each guarded transition appends a history step with
        from/to/actor."""
        record = self.auth_in("authorized")
        self.assertEqual(
            [(h["from"], h["to"]) for h in record["history"]],
            [(None, "not_started"), ("not_started", "in_progress"),
             ("in_progress", "authorized")],
        )
        self.assertTrue(all(h["by"] == "alice" for h in record["history"]))

    def test_denied_and_expired_can_reenter_in_progress(self):
        """Core 6. denied -> in_progress and expired -> in_progress
        are legal reopen paths."""
        denied = self.auth_in("denied")
        moved = self.store.transition_authorization(denied["id"], "in_progress", actor=ADMIN)
        self.assertEqual(moved["status"], "in_progress")
        expired = self.auth_in("expired")
        moved = self.store.transition_authorization(expired["id"], "in_progress", actor=ADMIN)
        self.assertEqual(moved["status"], "in_progress")

    def test_illegal_transitions_denied(self):
        """Core 6. Skipping states, jumping straight to authorized,
        and anything out of terminal "revoked" is a ValidationError
        and leaves the status unchanged."""
        cases = [
            ("not_started", "authorized"), ("not_started", "revoked"),
            ("in_progress", "expired"), ("in_progress", "not_started"),
            ("authorized", "in_progress"), ("authorized", "denied"),
            ("denied", "authorized"), ("expired", "authorized"),
            ("revoked", "in_progress"), ("revoked", "revoked"),
        ]
        for start, target in cases:
            record = self.auth_in(start)
            with self.assertRaises(ValidationError, msg="%s -> %s" % (start, target)):
                self.store.transition_authorization(record["id"], target, actor=ADMIN)
            stored = self.store.get_authorization(record["id"], actor=ADMIN)
            self.assertEqual(stored["status"], start)

    def test_authorization_requires_admin(self):
        """Core 6 + Core 9 RBAC. Creating or transitioning an
        authorization record is admin-only (manage_authorizations):
        member and viewer are PermissionDenied."""
        with self.assertRaises(PermissionDenied):
            self.store.create_authorization(SYSTEM_REF, SEED_FRAMEWORK_ID, actor=MEMBER)
        record = self._auth()
        with self.assertRaises(PermissionDenied):
            self.store.transition_authorization(record["id"], "in_progress", actor=MEMBER)
        with self.assertRaises(PermissionDenied):
            self.store.transition_authorization(record["id"], "in_progress", actor=VIEWER)

    def test_authorization_list_filters(self):
        """Core 6. Authorizations list with system/status filters."""
        first = self._auth()
        self.store.transition_authorization(first["id"], "in_progress", actor=ADMIN)
        self._auth()
        by_status = self.store.list_authorizations(actor=ADMIN, status="not_started")
        self.assertEqual(len(by_status), 1)
        by_system = self.store.list_authorizations(actor=VIEWER, system_ref=SYSTEM_REF)
        self.assertEqual(len(by_system), 2)


if __name__ == "__main__":
    unittest.main()
