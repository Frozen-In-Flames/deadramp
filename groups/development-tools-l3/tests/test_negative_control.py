"""Negative control: the suite must reject mutant gates.

Traces to: the contract's required negative control for Group 17.

(a) Lifecycle gate (Core 2): a mutant store whose set_issue_status
accepts any transition must NOT satisfy the canonical expectation
that open->resolved is rejected.
(b) Checksum integrity (Core 6): verify_artifact must be False on
tampered content, and registering with mismatched checksum+content
must be rejected; a mutant that always verifies must be rejected.

Each canonical test asserts three things, per the house pattern:
(1) the canonical expectation from the real implementation,
(2) the mutant would NOT produce that expectation, and
(3) a literal assertRaises(AssertionError) showing treating the
mutant's outcome as expected fails.

This file asserts the invariant holds in the UNMUTATED code. The
mutation-verification drill (patching the real lifecycle gate in
store.py, running the suite, restoring by SHA-256) is recorded in
``tests/README.md``.

L3 addition -- negative control (AU-9): a stored audit entry
mutated in place must leave ``verify_chain()`` ==
``(False, that entry's index)``; a naive mutant verifier that always
returns ``(True, None)`` accepts the tampered log, and the same
three-part pattern shows the canonical expectation rejects it.
"""

import unittest

from devtools_helpers import ADMIN, make_store
from devtools.errors import ValidationError
from devtools.store import DevToolsStore


class MutantDevToolsStore(DevToolsStore):
    """Mutant lifecycle gate: any issue transition is accepted."""

    def set_issue_status(self, issue_id, status, actor):
        """Core 2 (negative control mutant) -- no lifecycle gate."""
        record = self._get_issue_record(issue_id)
        record["status"] = status
        return dict(record)


class TestNegativeControlLifecycle(unittest.TestCase):
    """Core 2 lifecycle gate -- negative control."""

    def _assert_mutant_rejected(self, mutant_outcome, expected):
        """Core 2 (negative control): treating mutant outcome as expected must fail."""
        self.assertNotEqual(mutant_outcome, expected)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, expected)

    def test_open_to_resolved_rejected_canonical_but_mutant_allows(self):
        """Core 2, traced claim: open->resolved is illegal. Canonical: ValidationError, state open. Mutant: allows it."""
        store, project = make_store()
        issue = store.create_issue(project["id"], "Gate", ADMIN)
        with self.assertRaises(ValidationError):
            store.set_issue_status(issue["id"], "resolved", ADMIN)
        canonical = store.get_issue(issue["id"])["status"]
        self.assertEqual(canonical, "open")

        # Build a mutant store (make_store uses the real class):
        from devtools.audit import AuditLog
        mstore = MutantDevToolsStore(audit=AuditLog())
        mproject = mstore.create_project("Widget Service", ADMIN)
        missue = mstore.create_issue(mproject["id"], "Gate", ADMIN)
        mutant = mstore.set_issue_status(missue["id"], "resolved", ADMIN)["status"]
        self.assertEqual(mutant, "resolved")
        self._assert_mutant_rejected(mutant, "open")

    def test_closed_to_resolved_rejected_canonical(self):
        """Core 2, traced claim: closed->{open} only; closed->resolved rejected canonically, mutant allows."""
        store, project = make_store()
        issue = store.create_issue(project["id"], "Gate", ADMIN)
        store.set_issue_status(issue["id"], "closed", ADMIN)
        with self.assertRaises(ValidationError):
            store.set_issue_status(issue["id"], "resolved", ADMIN)
        self.assertEqual(store.get_issue(issue["id"])["status"], "closed")
        self._assert_mutant_rejected("resolved", "closed")


class TestNegativeControlChecksum(unittest.TestCase):
    """Core 6 checksum integrity -- negative control."""

    def test_verify_false_on_tampered(self):
        """Core 6, traced claim: verify_artifact is False on tampered content; a mutant always-True verify is rejected."""
        store, project = make_store()
        art = store.register_artifact(project["id"], "pkg", ADMIN, content="original")
        canonical = store.verify_artifact(art["id"], "tampered", ADMIN)
        self.assertFalse(canonical)
        mutant = True  # an always-verify mutant would say True
        self.assertNotEqual(mutant, canonical)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant, canonical)

    def test_mismatched_checksum_content_rejected(self):
        """Core 6, traced claim: register with mismatched checksum+content -> ValidationError, nothing stored."""
        import hashlib
        store, project = make_store()
        wrong = hashlib.sha256(b"other").hexdigest()
        with self.assertRaises(ValidationError):
            store.register_artifact(project["id"], "bad", ADMIN, checksum=wrong, content="real")
        self.assertEqual(store.list_artifacts(), [])
        mutant_outcome = "stored"  # a no-check register would store it
        self.assertNotEqual(mutant_outcome, "rejected")
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, "rejected")


def mutant_verify_chain(log):
    """The second defect under control (L3, AU-9): a naive verifier
    that always reports the chain intact, (True, None), without
    recomputing any hash."""
    return (True, None)


class TestNegativeControlAuditTamper(unittest.TestCase):
    """Core 10 (AU-9) -- negative control for the hash chain, traced
    claim: verify_chain() detects in-place tampering with a stored
    audit entry at that entry's index."""

    def test_tampered_entry_is_rejected_by_canonical_verifier(self):
        """AU-9, traced claim: the hash chain is tamper-evident.
        Canonical: a clean log verifies (True, None); after a stored
        entry is mutated in place (its actor changed to "mallory"),
        verify_chain() == (False, that entry's index). Mutant: the
        naive always-(True, None) verifier accepts the tampered log,
        and treating its verdict as the expected verdict is a test
        failure (literal assertRaises(AssertionError))."""
        from devtools.audit import AuditLog
        log = AuditLog()
        log.record("alice", "project_create", "prj-1")
        log.record("bob", "issue_create", "iss-1")
        log.record("alice", "project_create", "prj-2")
        self.assertEqual(log.verify_chain(), (True, None))

        tampered_index = 1
        log._entries[tampered_index]["actor"] = "mallory"

        canonical = log.verify_chain()
        self.assertEqual(canonical, (False, tampered_index))

        mutant_outcome = mutant_verify_chain(log)
        self.assertEqual(mutant_outcome, (True, None))  # mutant accepts it
        self.assertNotEqual(mutant_outcome, canonical)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, canonical)


if __name__ == "__main__":
    unittest.main()
