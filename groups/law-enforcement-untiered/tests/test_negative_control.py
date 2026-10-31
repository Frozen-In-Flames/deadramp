"""Negative control: the suite must reject two mutants.

Traces to: the contract's required negative control for Group 34.

Canonical expectations under test:

1. **The membership guard** (Core 1 + Core 10) -- an authenticated
   platform member who is not a member of a matter must get
   ``PermissionDenied`` from every matter-scoped read, and the matter
   must not appear in their list or in their registry search.
2. **Verify-by-content** (Core 4, SI-7) -- bytes that differ from the
   registered document's content must read ``matches: False``.

The mutants below suppress exactly those behaviors: a store whose
membership guard is a no-op, and a store whose verify always reports
a match. Each canonical test asserts (1) the canonical expectation
from the real implementation, (2) the mutant would NOT produce that
expectation, and (3) a literal ``assertRaises(AssertionError)``
showing that treating the mutant's outcome as the expected outcome
fails.
"""

import unittest

from lawenf.errors import PermissionDenied
from lawenf.store import LawEnfStore
from lawenf_helpers import DOC_CONTENT, DOC_SHA256, MEMBER, OUTSIDER, make_store


class MutantMembershipStore(LawEnfStore):
    """Mutant guard: the membership check performs nothing."""

    def _require_matter_access(self, matter, actor):
        """Core 1 (negative control mutant) -- no membership check."""
        return


class MutantVerifyStore(LawEnfStore):
    """Mutant verify: any content 'matches' any document."""

    def verify_document(self, matter_id, doc_id, content, actor):
        """Core 4 (negative control mutant) -- always a match."""
        result = super().verify_document(matter_id, doc_id, content, actor)
        result["matches"] = True
        result["computed_sha256"] = result["sha256"]
        return result


class TestMembershipGuardNegativeControl(unittest.TestCase):
    """Canonical: an outsider read is denied; the mutant waves it through."""

    def test_canonical_denial_and_mutant_rejection(self):
        # (1) canonical expectation from the real implementation
        store, _audit, matter = make_store()
        with self.assertRaises(PermissionDenied):
            store.get_matter(matter["id"], OUTSIDER)
        self.assertEqual(store.list_matters(OUTSIDER), [])
        hits = store.search_registry(OUTSIDER, "MATTER")
        self.assertEqual(hits["matters"], [])

        # (2) the mutant does NOT produce that expectation
        mutant = MutantMembershipStore()
        m = mutant.create_matter("MATTER-REF-001", MEMBER)
        leaked = mutant.get_matter(m["id"], OUTSIDER)  # no denial
        self.assertEqual(leaked["id"], m["id"])

        # (3) treating the mutant's outcome as expected fails
        with self.assertRaises(AssertionError):
            self.assertRaises(PermissionDenied,
                              mutant.get_matter, m["id"], OUTSIDER)


class TestVerifyNegativeControl(unittest.TestCase):
    """Canonical: tampered content does not verify; the mutant says it does."""

    def test_canonical_mismatch_and_mutant_rejection(self):
        # (1) canonical expectation from the real implementation
        store, _audit, matter = make_store()
        doc = store.register_document(
            matter["id"], "DOC-1", DOC_SHA256, len(DOC_CONTENT), MEMBER)
        tampered = DOC_CONTENT + b" -- altered after filing"
        self.assertFalse(
            store.verify_document(matter["id"], doc["id"], tampered, MEMBER)
            ["matches"])
        self.assertTrue(
            store.verify_document(matter["id"], doc["id"], DOC_CONTENT, MEMBER)
            ["matches"])

        # (2) the mutant waves the tampering through
        mutant = MutantVerifyStore()
        m = mutant.create_matter("MATTER-REF-001", MEMBER)
        d = mutant.register_document(
            m["id"], "DOC-1", DOC_SHA256, len(DOC_CONTENT), MEMBER)
        self.assertTrue(
            mutant.verify_document(m["id"], d["id"], tampered, MEMBER)
            ["matches"])

        # (3) treating the mutant's outcome as expected fails
        with self.assertRaises(AssertionError):
            self.assertFalse(
                mutant.verify_document(m["id"], d["id"], tampered, MEMBER)
                ["matches"])


if __name__ == "__main__":
    unittest.main()
