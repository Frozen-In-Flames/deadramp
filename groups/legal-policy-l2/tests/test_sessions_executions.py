"""Agent session records; execution records; the single-use rule.

Traces to: Core functions 3 (Agent session records) and 4
(Execution records) in UNION-SPEC.md — sessions carry a guarded
lifecycle (active -> closed); `expired` and `sandbox_consumed` are
derived at read and never stored; a sandbox session accepts exactly
one execution, enforced by the store's `_check_sandbox_unused` seam
(SI-10). Non-sandbox sessions accept multiple executions; closed
sessions accept none.
"""

import unittest

import legalpol_helpers as H
from legalpol.errors import NotFoundError, PermissionDenied, ValidationError

STORED_SESSION_KEYS = {
    "id", "agency_id", "workspace_id", "session_ref", "purpose",
    "sandbox", "status", "expires_at", "created_by", "created_utc",
}


class SessionFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.agency = H.make_store()
        self.aid = self.agency["id"]
        self.workspace = H.make_workspace(self.store, self.agency)
        self.wid = self.workspace["id"]


class TestSessions(SessionFixture):
    """Core 3: session records and the derived-at-read discipline."""

    def test_create_session_stored_shape(self):
        """Core 3: create returns the stored shape — no derived keys."""
        session = H.make_session(self.store, self.agency, self.workspace,
                                 purpose="draft review")
        self.assertEqual(set(session.keys()), STORED_SESSION_KEYS)
        self.assertEqual(session["id"], "ses-1")
        self.assertEqual(session["status"], "active")
        self.assertFalse(session["sandbox"])
        self.assertIsNone(session["expires_at"])

    def test_session_ref_unique_within_workspace(self):
        """Core 3 / SI-10: duplicate session_ref in one workspace is
        rejected; the same ref in another workspace is fine."""
        H.make_session(self.store, self.agency, self.workspace)
        with self.assertRaises(ValidationError):
            H.make_session(self.store, self.agency, self.workspace)
        other_ws = H.make_workspace(self.store, self.agency,
                                    workspace_ref="WSP-REF-002", title="Two")
        twin = H.make_session(self.store, self.agency, other_ws)
        self.assertEqual(twin["session_ref"], "SES-REF-001")

    def test_session_validation(self):
        """Core 3 / SI-10: non-bool sandbox, unparseable expires_at,
        and a workspace from another agency are all rejected."""
        with self.assertRaises(ValidationError):
            H.make_session(self.store, self.agency, self.workspace,
                           session_ref="SES-BAD-1", sandbox="yes")
        with self.assertRaises(ValidationError):
            H.make_session(self.store, self.agency, self.workspace,
                           session_ref="SES-BAD-2", expires_at="not-a-date")
        with self.assertRaises(ValidationError):
            H.make_session(self.store, self.agency, self.workspace,
                           session_ref="")
        other = self.store.create_agency("AGY-REF-002", "Second", H.ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.create_session(other["id"], self.wid, "SES-X", H.ADMIN)

    def test_stored_record_carries_no_derived_keys(self):
        """Core 3: the raw stored record has neither `expired` nor
        `sandbox_consumed`; the read views derive both."""
        session = H.make_session(self.store, self.agency, self.workspace,
                                 sandbox=True)
        raw = self.store._sessions[session["id"]]
        self.assertNotIn("expired", raw)
        self.assertNotIn("sandbox_consumed", raw)
        view = self.store.get_session(self.aid, session["id"], H.MEMBER)
        self.assertEqual(set(view.keys()),
                         STORED_SESSION_KEYS | {"expired", "sandbox_consumed"})
        listed = self.store.list_sessions(self.aid, H.MEMBER)
        self.assertIn("expired", listed[0])
        self.assertIn("sandbox_consumed", listed[0])

    def test_expired_flips_with_the_read_clock(self):
        """Core 3: `expired` is computed from expires_at against the
        `now` supplied at read — the stored record never changes."""
        session = H.make_session(
            self.store, self.agency, self.workspace,
            expires_at="2026-06-01T00:00:00+00:00")
        before = self.store.get_session(
            self.aid, session["id"], H.MEMBER, now="2026-05-01T00:00:00+00:00")
        after = self.store.get_session(
            self.aid, session["id"], H.MEMBER, now="2026-07-01T00:00:00+00:00")
        self.assertFalse(before["expired"])
        self.assertTrue(after["expired"])
        raw = self.store._sessions[session["id"]]
        self.assertEqual(raw["expires_at"], "2026-06-01T00:00:00+00:00")
        no_expiry = H.make_session(self.store, self.agency, self.workspace,
                                   session_ref="SES-REF-002")
        view = self.store.get_session(
            self.aid, no_expiry["id"], H.MEMBER, now="2999-01-01T00:00:00+00:00")
        self.assertFalse(view["expired"])

    def test_sandbox_consumed_flips_after_execution(self):
        """Core 3/4: `sandbox_consumed` derives from the existence of
        an execution record for the sandbox session."""
        session = H.make_session(self.store, self.agency, self.workspace,
                                 sandbox=True)
        view = self.store.get_session(self.aid, session["id"], H.MEMBER)
        self.assertFalse(view["sandbox_consumed"])
        self.store.record_execution(self.aid, session["id"], "EXE-1", H.MEMBER)
        view = self.store.get_session(self.aid, session["id"], H.MEMBER)
        self.assertTrue(view["sandbox_consumed"])
        plain = H.make_session(self.store, self.agency, self.workspace,
                               session_ref="SES-REF-002")
        self.store.record_execution(self.aid, plain["id"], "EXE-1", H.MEMBER)
        view = self.store.get_session(self.aid, plain["id"], H.MEMBER)
        self.assertFalse(view["sandbox_consumed"])

    def test_close_session_lifecycle(self):
        """Core 3: active -> closed is guarded; a second close is
        rejected and the stored status is the lifecycle, not a
        derivation."""
        session = H.make_session(self.store, self.agency, self.workspace)
        closed = self.store.close_session(self.aid, session["id"], H.MEMBER)
        self.assertEqual(closed["status"], "closed")
        with self.assertRaises(ValidationError):
            self.store.close_session(self.aid, session["id"], H.MEMBER)

    def test_list_sessions_workspace_filter(self):
        """Core 3: list_sessions filters by workspace when asked."""
        H.make_session(self.store, self.agency, self.workspace)
        other_ws = H.make_workspace(self.store, self.agency,
                                    workspace_ref="WSP-REF-002", title="Two")
        H.make_session(self.store, self.agency, other_ws)
        self.assertEqual(len(self.store.list_sessions(self.aid, H.MEMBER)), 2)
        only = self.store.list_sessions(self.aid, H.MEMBER,
                                        workspace_id=self.wid)
        self.assertEqual([s["workspace_id"] for s in only], [self.wid])

    def test_session_membership_boundary(self):
        """Core 3 / AC: outsider reads and writes are denied; the
        viewer may read but not write."""
        session = H.make_session(self.store, self.agency, self.workspace)
        with self.assertRaises(PermissionDenied):
            self.store.get_session(self.aid, session["id"], H.OUTSIDER)
        with self.assertRaises(PermissionDenied):
            H.make_session(self.store, self.agency, self.workspace,
                           actor=H.VIEWER, session_ref="SES-V")
        self.assertEqual(
            self.store.get_session(self.aid, session["id"], H.VIEWER)["id"],
            session["id"])


class TestExecutions(SessionFixture):
    """Core 4: execution records and the single-use sandbox rule."""

    def test_record_execution_shape_and_defaults(self):
        """Core 4: execution shape is pinned; kind defaults to code."""
        session = H.make_session(self.store, self.agency, self.workspace)
        execution = self.store.record_execution(
            self.aid, session["id"], "EXE-REF-1", H.MEMBER, language="python")
        self.assertEqual(set(execution.keys()), {
            "id", "agency_id", "session_id", "execution_ref", "kind",
            "language", "created_by", "created_utc"})
        self.assertEqual(execution["id"], "exe-1")
        self.assertEqual(execution["kind"], "code")
        self.assertEqual(execution["language"], "python")

    def test_execution_kind_validation_and_ref_uniqueness(self):
        """Core 4 / SI-10: unknown kinds and duplicate refs within a
        session are rejected."""
        session = H.make_session(self.store, self.agency, self.workspace)
        with self.assertRaises(ValidationError):
            self.store.record_execution(self.aid, session["id"], "EXE-1",
                                        H.MEMBER, kind="shell")
        self.store.record_execution(self.aid, session["id"], "EXE-1",
                                    H.MEMBER, kind="document")
        with self.assertRaises(ValidationError):
            self.store.record_execution(self.aid, session["id"], "EXE-1",
                                        H.MEMBER)

    def test_single_use_rule(self):
        """Core 4 (signature invariant): a second execution on a
        sandbox session raises ValidationError, consumes no id, and
        changes nothing; the next successful execution elsewhere
        gets the expected sequential id."""
        sandbox = H.make_session(self.store, self.agency, self.workspace,
                                 sandbox=True)
        first = self.store.record_execution(self.aid, sandbox["id"],
                                            "EXE-1", H.MEMBER)
        self.assertEqual(first["id"], "exe-1")
        with self.assertRaises(ValidationError):
            self.store.record_execution(self.aid, sandbox["id"], "EXE-2",
                                        H.MEMBER)
        recorded = self.store.list_executions(self.aid, sandbox["id"], H.MEMBER)
        self.assertEqual([e["id"] for e in recorded], ["exe-1"])
        plain = H.make_session(self.store, self.agency, self.workspace,
                               session_ref="SES-REF-002")
        nxt = self.store.record_execution(self.aid, plain["id"], "EXE-9",
                                          H.MEMBER)
        self.assertEqual(nxt["id"], "exe-2")

    def test_non_sandbox_sessions_accept_multiple_executions(self):
        """Core 4: the single-use rule binds sandbox sessions only."""
        session = H.make_session(self.store, self.agency, self.workspace)
        self.store.record_execution(self.aid, session["id"], "EXE-1", H.MEMBER)
        self.store.record_execution(self.aid, session["id"], "EXE-2", H.MEMBER)
        self.assertEqual(
            len(self.store.list_executions(self.aid, session["id"], H.MEMBER)),
            2)

    def test_executions_on_closed_sessions_rejected(self):
        """Core 4: a closed session accepts no executions, sandbox
        or not, and the rejection consumes no id."""
        session = H.make_session(self.store, self.agency, self.workspace)
        self.store.close_session(self.aid, session["id"], H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.record_execution(self.aid, session["id"], "EXE-1",
                                        H.MEMBER)
        other = H.make_session(self.store, self.agency, self.workspace,
                               session_ref="SES-REF-002")
        execution = self.store.record_execution(self.aid, other["id"],
                                                "EXE-1", H.MEMBER)
        self.assertEqual(execution["id"], "exe-1")


if __name__ == "__main__":
    unittest.main()
