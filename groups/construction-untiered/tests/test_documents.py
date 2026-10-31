"""Documents tests.

Traces to: Core -- Documents (doc-) with versioned updates;
contract for ``ConstructStore.create_document`` / ``update_document``.
DOC_TYPES = (drawing, specification, contract, submittal, form, report, other).
"""

import unittest

from construct_helpers import ADMIN, OPERATOR, VIEWER, fresh_store, make_store
from construct.errors import NotFoundError, PermissionDenied, ValidationError
from construct.store import DOC_TYPES


class TestDocumentCreation(unittest.TestCase):
    """Documents: creation and version 1."""

    def test_create_shape_version1(self):
        """Documents. create_document makes doc- at version 1 mirroring checksum/note."""
        store, project, prime, sub = make_store()
        doc = store.create_document(OPERATOR, "Structural spec", project_id=project["id"],
                                    doc_type="specification", checksum="abc123", note="issued")
        self.assertEqual(doc["id"], "doc-1")
        self.assertEqual(doc["version"], 1)
        self.assertEqual(doc["checksum"], "abc123")
        self.assertEqual(doc["note"], "issued")
        self.assertEqual(doc["doc_type"], "specification")
        self.assertEqual(len(doc["versions"]), 1)
        v1 = doc["versions"][0]
        self.assertEqual(v1["version"], 1)
        self.assertEqual(v1["checksum"], "abc123")
        self.assertEqual(v1["note"], "issued")
        self.assertIn("ts", v1)
        self.assertEqual(doc["created_by"], "bob")

    def test_create_defaults(self):
        """Documents. doc_type defaults to 'other', project/checksum/note default None."""
        store = fresh_store()
        doc = store.create_document(ADMIN, "Loose note")
        self.assertEqual(doc["doc_type"], "other")
        self.assertIsNone(doc["project_id"])
        self.assertIsNone(doc["checksum"])
        self.assertIsNone(doc["note"])

    def test_all_doc_types_accepted(self):
        """Documents. Every DOC_TYPES value is accepted."""
        store = fresh_store()
        for i, dt in enumerate(DOC_TYPES):
            doc = store.create_document(ADMIN, "Doc %s" % dt, doc_type=dt)
            self.assertEqual(doc["doc_type"], dt)
            self.assertEqual(doc["id"], "doc-%d" % (i + 1))

    def test_bad_doc_type_and_unknown_project_no_id(self):
        """Documents. Bad doc_type / unknown project / empty title -> error, no id consumed."""
        store, project, prime, sub = make_store()
        with self.assertRaises(ValidationError):
            store.create_document(OPERATOR, "X", doc_type="blueprint")
        with self.assertRaises(NotFoundError):
            store.create_document(OPERATOR, "X", project_id="prj-99")
        with self.assertRaises(ValidationError):
            store.create_document(OPERATOR, "")
        doc = store.create_document(OPERATOR, "First good", project_id=project["id"])
        self.assertEqual(doc["id"], "doc-1")


class TestDocumentUpdate(unittest.TestCase):
    """Documents: versioned updates carrying fields forward."""

    def test_update_appends_and_carries_forward(self):
        """Documents. update appends a version; the unchanged field carries forward."""
        store, project, prime, sub = make_store()
        doc = store.create_document(OPERATOR, "Spec", checksum="c1", note="n1")
        updated = store.update_document(doc["id"], OPERATOR, checksum="c2")
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["checksum"], "c2")
        self.assertEqual(updated["note"], "n1")
        self.assertEqual(len(updated["versions"]), 2)
        self.assertEqual(updated["versions"][1]["checksum"], "c2")
        self.assertEqual(updated["versions"][1]["note"], "n1")
        updated2 = store.update_document(doc["id"], OPERATOR, note="n2")
        self.assertEqual(updated2["version"], 3)
        self.assertEqual(updated2["checksum"], "c2")
        self.assertEqual(updated2["note"], "n2")
        self.assertEqual(len(store.get_document(doc["id"], VIEWER)["versions"]), 3)

    def test_update_neither_field_is_validation_error(self):
        """Documents. update_document with neither checksum nor note -> ValidationError."""
        store, project, prime, sub = make_store()
        doc = store.create_document(OPERATOR, "Spec", checksum="c1")
        with self.assertRaises(ValidationError):
            store.update_document(doc["id"], OPERATOR)
        self.assertEqual(store.get_document(doc["id"], ADMIN)["version"], 1)

    def test_update_unknown_and_viewer_denied(self):
        """Documents. Unknown id -> NotFoundError; viewer update -> PermissionDenied."""
        store, project, prime, sub = make_store()
        doc = store.create_document(OPERATOR, "Spec")
        with self.assertRaises(NotFoundError):
            store.update_document("doc-99", ADMIN, note="x")
        with self.assertRaises(PermissionDenied):
            store.update_document(doc["id"], VIEWER, note="x")

    def test_copies_are_copies(self):
        """Documents. Mutating a returned document/versions does not mutate the store."""
        store, project, prime, sub = make_store()
        doc = store.create_document(OPERATOR, "Spec", checksum="c1")
        doc["versions"].append({"version": 99, "checksum": "x", "note": "x", "ts": "x"})
        doc["checksum"] = "hacked"
        again = store.get_document(doc["id"], ADMIN)
        self.assertEqual(len(again["versions"]), 1)
        self.assertEqual(again["checksum"], "c1")

    def test_list_project_filter(self):
        """Documents. list_documents(project_id=) filters; unfiltered lists all."""
        store, project, prime, sub = make_store()
        other = store.create_project("Other", ADMIN)
        store.create_document(OPERATOR, "A", project_id=project["id"])
        store.create_document(OPERATOR, "B", project_id=other["id"])
        store.create_document(OPERATOR, "C")
        self.assertEqual(len(store.list_documents(VIEWER)), 3)
        mine = store.list_documents(VIEWER, project_id=project["id"])
        self.assertEqual([d["title"] for d in mine], ["A"])


if __name__ == "__main__":
    unittest.main()
