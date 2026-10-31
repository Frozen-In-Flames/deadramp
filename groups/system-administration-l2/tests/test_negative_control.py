"""Negative control: the derived-overdue invariant must be
load-bearing.

The group's signature invariant is that a service request's
``overdue`` flag is *derived at read* -- true when the request is
still open or in progress and its due date is before the read
date, false otherwise (and never for resolved or cancelled
requests) -- computed every time, never stored. The canonical
expectations use the fixture request due 2026-06-10: at the
2026-06-05 read clock it is not overdue, at 2026-06-15 it is. The
mutant is a SysadminStore subclass whose derivation always
reports not overdue: if the suite still passed against the
mutant, the request tests would be testing that code ran, not
that the derivation holds. (The sibling groups verified the same
derivation discipline with the same drill shape.)
"""

import unittest

import sysadmin_helpers as H
from sysadmin.store import SysadminStore


class MutantSysadminStore(SysadminStore):
    """A store whose overdue derivation always reports False."""

    def _is_overdue(self, request, as_of_dt):
        return False


def _fixture(store):
    org = H.make_org(store)
    store.add_member(H.ADMIN, org["id"], H.STAFF.name)
    system = H.make_system(store, org)
    request = H.make_request(store, org, system)
    return org, request


class TestNegativeControlDerivedOverdue(unittest.TestCase):
    def test_canonical_expectation(self):
        """Canonical: the fixture request is not overdue five days
        before its due date and overdue five days after it."""
        store = H.fresh_store()
        org, request = _fixture(store)
        before = store.get_request(H.MEMBER, request["id"],
                                   as_of=H.AS_OF_BEFORE_DUE)
        self.assertFalse(before["overdue"])
        after = store.get_request(H.MEMBER, request["id"],
                                  as_of=H.AS_OF_AFTER_DUE)
        self.assertTrue(after["overdue"])

    def test_implementation_matches_canonical_in_summary(self):
        """Implementation: the org summary's overdue count (as_of =
        now, long after the June 2026 fixture due date) agrees with
        the same derivation, not a stored flag."""
        store = H.fresh_store()
        org, request = _fixture(store)
        summary = store.organization_summary(H.MEMBER, org["id"])
        self.assertEqual(summary["requests_overdue"], 1)

    def test_mutant_would_not_derive(self):
        """Mutant: with the derivation stubbed to always report
        False, the request reads not overdue at the after-due read
        clock -- so the canonical expectation, applied to the
        mutant's output, fails (asserted literally)."""
        store = MutantSysadminStore()
        org, request = _fixture(store)
        view = store.get_request(H.MEMBER, request["id"],
                                 as_of=H.AS_OF_AFTER_DUE)
        self.assertFalse(view["overdue"])
        with self.assertRaises(AssertionError):
            self.assertTrue(view["overdue"])


if __name__ == "__main__":
    unittest.main()
