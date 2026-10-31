"""Core function 7: dispute records & lifecycle."""

import unittest

import mdm_helpers as H
from mdm.errors import ValidationError


class TestDisputes(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()
        self.contract = H.make_contract(self.store, self.org)
        self.bill = H.make_bill(self.store, self.org, self.contract,
                                stated_cents=50_000)

    def _dispute(self, **kw):
        kwargs = {"amount_cents": 5_000, "reason": "Duplicate line charge"}
        kwargs.update(kw)
        return self.store.create_dispute(H.MEMBER, self.bill["id"], **kwargs)

    def test_dispute_never_exceeds_its_bill(self):
        """The dispute cap: a dispute over more than the bill states
        is malformed input, rejected whole (SI-10)."""
        with self.assertRaises(ValidationError):
            self._dispute(amount_cents=50_001)
        at_cap = self._dispute(amount_cents=50_000)
        self.assertEqual(at_cap["status"], "open")
        self.assertEqual(len(self.store.list_disputes(H.MEMBER, self.bill["id"])), 1)

    def test_lifecycle_and_verbatim_resolution(self):
        dispute = self._dispute()
        self.store.start_dispute(H.MEMBER, dispute["id"])
        resolved = self.store.resolve_dispute(
            H.STAFF, dispute["id"], "Carrier credited the duplicate charge")
        self.assertEqual(resolved["status"], "resolved")
        self.assertEqual(resolved["resolution"],
                         "Carrier credited the duplicate charge")
        self.assertIsNotNone(resolved["resolved_utc"])
        with self.assertRaises(ValidationError):
            self.store.resolve_dispute(H.STAFF, dispute["id"], "Again")

    def test_resolve_directly_from_open(self):
        dispute = self._dispute()
        resolved = self.store.resolve_dispute(
            H.STAFF, dispute["id"], "Charge was correct; dispute withdrawn")
        self.assertEqual(resolved["status"], "resolved")

    def test_start_requires_open(self):
        dispute = self._dispute()
        self.store.resolve_dispute(H.STAFF, dispute["id"], "Done")
        with self.assertRaises(ValidationError):
            self.store.start_dispute(H.MEMBER, dispute["id"])


if __name__ == "__main__":
    unittest.main()
