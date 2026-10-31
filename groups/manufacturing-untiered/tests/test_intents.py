"""Organizations and engineering intent records — core functions
1 and 2 (UNION-SPEC.md).

Organization references are unique. Intent records store the
statement verbatim under an opaque author reference. An intent's
status is derived at read through the ``_derive_intent_status``
seam — ``open`` until a decision cites it, ``transformed`` after —
and the stored record provably carries no ``status`` key.
"""

import unittest

from manufacturing.errors import (NotFoundError, PermissionDenied,
                                 ValidationError)

import manufacturing_helpers as H


class TestOrganizations(unittest.TestCase):
    def test_ref_must_be_unique(self):
        store, audit, org = H.make_store()
        with self.assertRaises(ValidationError):
            store.create_organization(H.ADMIN, "acme-aerospace", "Copy")

    def test_unknown_organization_is_not_found(self):
        store, audit, org = H.make_store()
        with self.assertRaises(NotFoundError):
            store.get_organization(H.ADMIN, "org-99")
        with self.assertRaises(NotFoundError):
            store.record_intent(H.OPERATOR, "org-99", "L", "S", "eng-1")


class TestIntents(unittest.TestCase):
    def test_record_shape_and_verbatim_statement(self):
        store, audit, org = H.make_store()
        intent = H.make_intent(
            store, org, statement="Hold 40 kN shear; no fasteners "
                                  "in the bond line.")
        self.assertEqual(intent["id"], "int-1")
        self.assertEqual(intent["statement"],
                         "Hold 40 kN shear; no fasteners in the "
                         "bond line.")
        self.assertEqual(intent["author_ref"], "eng-1")
        self.assertEqual(intent["status"], "open")

    def test_author_ref_cannot_be_an_email_or_carry_whitespace(self):
        store, audit, org = H.make_store()
        for bad in ("eng@example.com", "eng one", "", None):
            with self.assertRaises(ValidationError):
                store.record_intent(H.OPERATOR, org["id"], "L", "S", bad)

    def test_status_is_derived_never_stored(self):
        store, audit, org = H.make_store()
        intent = H.make_intent(store, org)
        stored = store._intents[intent["id"]]
        self.assertNotIn("status", stored)
        self.assertEqual(store.get_intent(H.VIEWER, intent["id"])["status"],
                         "open")
        H.make_decision(store, org, intent)
        self.assertEqual(store.get_intent(H.VIEWER, intent["id"])["status"],
                         "transformed")
        # The stored record still carries no status key.
        self.assertNotIn("status", store._intents[intent["id"]])

    def test_list_filters_by_status(self):
        store, audit, org = H.make_store()
        first = H.make_intent(store, org, label="One")
        H.make_intent(store, org, label="Two")
        H.make_decision(store, org, first)
        self.assertEqual(
            [i["label"] for i in store.list_intents(
                H.VIEWER, status="transformed")], ["One"])
        self.assertEqual(
            [i["label"] for i in store.list_intents(
                H.VIEWER, status="open")], ["Two"])
        with self.assertRaises(ValidationError):
            store.list_intents(H.VIEWER, status="pending")

    def test_viewer_may_not_record_intent(self):
        store, audit, org = H.make_store()
        with self.assertRaises(PermissionDenied):
            H.make_intent(store, org, actor=H.VIEWER)


if __name__ == "__main__":
    unittest.main()
