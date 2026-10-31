"""Negative control: the award-cap invariant must be load-bearing.

The group's signature invariant is that the awards recorded against
a grant program never exceed the program's budget. The canonical
expectation is that an over-cap decision is rejected whole. The
mutant is a GrantsStore subclass whose cap check does nothing: if
the suite still passed against the mutant, the cap tests would be
testing that code ran, not that the invariant holds.
"""

import unittest

import grants_helpers as H
from grants.errors import ValidationError
from grants.store import GrantsStore


class MutantGrantsStore(GrantsStore):
    """A store with the award-cap check removed (the mutant)."""

    def _check_award_cap(self, program, amount_cents):
        return None


def _fixture(store):
    program = store.create_program(
        H.MEMBER, H.PROGRAM_NAME, "Community Grants Program", "SPONSOR-1",
        H.OPENS_AT, H.CLOSES_AT, H.BUDGET_CENTS)
    store.add_member(H.ADMIN, program["id"], H.STAFF.name)
    org = store.create_organization(H.MEMBER, "ORG-100",
                                    "Community Builders Alliance")
    return program, org


def _under_review(store, program, org):
    app = store.create_application(H.MEMBER, program["id"], org["id"],
                                   400_000, "After-school tutoring expansion")
    store.submit_application(H.MEMBER, app["id"])
    store.start_review(H.STAFF, app["id"])
    return app


class TestNegativeControlAwardCap(unittest.TestCase):
    def test_canonical_expectation_rejects_over_cap(self):
        """Canonical: budget 1,000,000; an award of 1,000,001 is rejected."""
        store = H.fresh_store()
        program, org = _fixture(store)
        app = _under_review(store, program, org)
        with self.assertRaises(ValidationError):
            store.decide_application(H.STAFF, app["id"], True,
                                     amount_cents=H.BUDGET_CENTS + 1)

    def test_implementation_matches_canonical_across_awards(self):
        """Implementation: 700,000 awarded; a further 300,001 is
        rejected whole and the recorded total stays 700,000."""
        store = H.fresh_store()
        program, org = _fixture(store)
        first = _under_review(store, program, org)
        store.decide_application(H.STAFF, first["id"], True,
                                 amount_cents=700_000)
        second = _under_review(store, program, org)
        with self.assertRaises(ValidationError):
            store.decide_application(H.STAFF, second["id"], True,
                                     amount_cents=300_001)
        view = store.get_program(H.MEMBER, program["id"])
        self.assertEqual(view["awarded_cents"], 700_000)

    def test_mutant_would_not_reject(self):
        """Mutant: with the cap check removed, the same over-cap
        decision succeeds and the recorded awards exceed the budget —
        so the canonical expectation, applied to the mutant's output,
        fails (asserted literally with assertRaises)."""
        store = MutantGrantsStore()
        program, org = _fixture(store)
        app = _under_review(store, program, org)
        result = store.decide_application(H.STAFF, app["id"], True,
                                          amount_cents=H.BUDGET_CENTS + 1)
        self.assertEqual(result["award"]["amount_cents"], H.BUDGET_CENTS + 1)
        view = store.get_program(H.MEMBER, program["id"])
        self.assertGreater(view["awarded_cents"], H.BUDGET_CENTS)
        with self.assertRaises(AssertionError):
            self.assertLessEqual(view["awarded_cents"], H.BUDGET_CENTS)


if __name__ == "__main__":
    unittest.main()
