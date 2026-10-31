"""Manufacturable decision records and the decision-basis guard —
core function 3 (UNION-SPEC.md).

A decision record states the decision verbatim, names the decider
by opaque reference, and rests on a basis of engineering intent
records. The guard: the basis must be non-empty, distinct,
existing, and of the same organization — a decision resting on no
intent transforms nothing. Refusals record nothing and consume no
id.
"""

import unittest

from manufacturing.errors import (NotFoundError, PermissionDenied,
                                 ValidationError)

import manufacturing_helpers as H


class TestDecisions(unittest.TestCase):
    def test_decision_records_its_basis(self):
        store, audit, org = H.make_store()
        intent = H.make_intent(store, org)
        decision = H.make_decision(store, org, intent)
        self.assertEqual(decision["id"], "dec-1")
        self.assertEqual(decision["basis_intent_ids"], [intent["id"]])
        self.assertEqual(decision["decided_by_ref"], "eng-2")
        self.assertEqual(
            store.list_decisions(H.VIEWER, intent_id=intent["id"]),
            [decision])

    def test_empty_basis_is_refused_and_consumes_no_id(self):
        store, audit, org = H.make_store()
        intent = H.make_intent(store, org)
        for bad_basis in ([], None):
            with self.assertRaises(ValidationError):
                store.record_decision(H.OPERATOR, org["id"], "L", "S",
                                      bad_basis, "eng-2")
        self.assertEqual(store.list_decisions(H.ADMIN), [])
        decision = H.make_decision(store, org, intent)
        self.assertEqual(decision["id"], "dec-1")

    def test_unknown_basis_intent_is_refused(self):
        store, audit, org = H.make_store()
        with self.assertRaises(ValidationError):
            store.record_decision(H.OPERATOR, org["id"], "L", "S",
                                  ["int-99"], "eng-2")

    def test_cross_organization_basis_is_refused(self):
        store, audit, org = H.make_store()
        other = store.create_organization(H.ADMIN, "globex-defense",
                                          "Globex Defense Team")
        foreign = H.make_intent(store, other)
        with self.assertRaises(ValidationError):
            store.record_decision(H.OPERATOR, org["id"], "L", "S",
                                  [foreign["id"]], "eng-2")

    def test_duplicate_basis_is_refused(self):
        store, audit, org = H.make_store()
        intent = H.make_intent(store, org)
        with self.assertRaises(ValidationError):
            store.record_decision(H.OPERATOR, org["id"], "L", "S",
                                  [intent["id"], intent["id"]], "eng-2")

    def test_decider_ref_cannot_be_an_email(self):
        store, audit, org = H.make_store()
        intent = H.make_intent(store, org)
        with self.assertRaises(ValidationError):
            store.record_decision(H.OPERATOR, org["id"], "L", "S",
                                  [intent["id"]], "lead@example.com")

    def test_multi_intent_basis_and_unknown_decision(self):
        store, audit, org = H.make_store()
        one = H.make_intent(store, org, label="One")
        two = H.make_intent(store, org, label="Two")
        decision = store.record_decision(
            H.OPERATOR, org["id"], "L", "S", [one["id"], two["id"]],
            "eng-2")
        self.assertEqual(decision["basis_intent_ids"],
                         [one["id"], two["id"]])
        with self.assertRaises(NotFoundError):
            store.get_decision(H.ADMIN, "dec-99")

    def test_viewer_may_not_record_decision(self):
        store, audit, org = H.make_store()
        intent = H.make_intent(store, org)
        with self.assertRaises(PermissionDenied):
            H.make_decision(store, org, intent, actor=H.VIEWER)


if __name__ == "__main__":
    unittest.main()
