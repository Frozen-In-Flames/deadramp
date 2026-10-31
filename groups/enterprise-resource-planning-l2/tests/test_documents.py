"""Core function 13: document records -- metadata only (SI-10).

A document record names a business document by opaque reference
with a label and a business-purpose label. The shape is pinned
and scanned recursively: no field could hold document content.
"""

import unittest

from erp.errors import ValidationError

from erp_helpers import OPERATOR, make_org, make_store

DOCUMENT_KEYS = {"id", "org_id", "doc_ref", "label", "purpose_label",
                 "created_by", "created_utc"}
FORBIDDEN_KEY_PARTS = ("content", "body", "text", "attachment", "file",
                       "payload", "blob")


def _all_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            keys |= _all_keys(value)
    return keys


class DocumentTests(unittest.TestCase):
    def test_shape_is_metadata_only(self):
        store, _ = make_store()
        org = make_org(store)
        document = store.create_document(
            OPERATOR, org["id"], "DOC-0001", "Vendor agreement (label)",
            "Procurement (label)")
        self.assertEqual(set(document.keys()), DOCUMENT_KEYS)
        for key in _all_keys(document):
            for part in FORBIDDEN_KEY_PARTS:
                self.assertNotIn(part, key.lower(),
                                 "document record carries key %r" % key)

    def test_doc_ref_unique_per_org(self):
        store, _ = make_store()
        org = make_org(store)
        store.create_document(OPERATOR, org["id"], "DOC-1", "A", "P")
        with self.assertRaises(ValidationError):
            store.create_document(OPERATOR, org["id"], "DOC-1", "B", "P")


if __name__ == "__main__":
    unittest.main()
