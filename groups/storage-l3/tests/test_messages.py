"""Core function 4: message archive records -- metadata only.

The pinned shape is the privacy discipline in executable form: an
archive record carries an opaque message reference, opaque
sender/recipient references, a moment, a recorded size, and a
format label. There is no field that could hold a subject, a body,
or any content, and the recursive scan below keeps it that way.
"""

import unittest

from storage.errors import NotFoundError, ValidationError

from storage_helpers import (ADMIN, OPERATOR, VIEWER, make_archive,
                             make_custody, make_message, make_store)

MESSAGE_KEYS = {"id", "collection_id", "message_ref", "sender_ref",
                "recipient_refs", "archived_at", "size_bytes",
                "format_label", "custody_id", "seq", "created_by",
                "created_utc"}
FORBIDDEN_KEYS = {"subject", "body", "content", "text", "html",
                  "attachment", "attachments", "payload", "data"}


def scan_no_content(obj, path="root"):
    if isinstance(obj, dict):
        for key, value in obj.items():
            assert key not in FORBIDDEN_KEYS, "%s.%s" % (path, key)
            scan_no_content(value, "%s.%s" % (path, key))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            scan_no_content(value, "%s[%d]" % (path, i))


class MessageTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org, self.policy, self.collection = make_archive(self.store)

    def test_archive_shape_is_metadata_only(self):
        message = make_message(self.store, self.collection)
        stored_keys = set(message) - {"retention_state", "retention_until"}
        self.assertEqual(stored_keys, MESSAGE_KEYS)
        scan_no_content(message)
        raw = self.store._messages[message["id"]]
        self.assertEqual(set(raw), MESSAGE_KEYS)
        scan_no_content(raw)

    def test_message_ref_unique_within_collection_only(self):
        make_message(self.store, self.collection, ref="MSG-1")
        with self.assertRaises(ValidationError):
            make_message(self.store, self.collection, ref="MSG-1")
        other = self.store.create_collection(
            ADMIN, self.org["id"], "Second archive", self.policy["id"],
            "native")
        twin = make_message(self.store, other, ref="MSG-1")
        self.assertEqual(twin["message_ref"], "MSG-1")

    def test_validation(self):
        col = self.collection["id"]
        for kwargs in (
            {"message_ref": ""},
            {"sender_ref": None},
            {"recipient_refs": "not-a-list"},
            {"recipient_refs": ["ok", ""]},
            {"archived_at": "not-a-date"},
            {"size_bytes": -1},
            {"size_bytes": 1.5},
            {"size_bytes": True},
            {"format_label": ""},
        ):
            call = dict(collection_id=col, message_ref="M", sender_ref="S",
                        recipient_refs=[], archived_at="2024-01-01",
                        size_bytes=10, format_label="native")
            call.update(kwargs)
            with self.assertRaises(ValidationError, msg=repr(kwargs)):
                self.store.archive_message(OPERATOR, **call)
        self.assertEqual(self.store.list_messages(ADMIN), [])
        with self.assertRaises(NotFoundError):
            self.store.archive_message(OPERATOR, "col-99", "M", "S", [],
                                       "2024-01-01", 10, "native")

    def test_failed_archive_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.store.archive_message(OPERATOR, self.collection["id"],
                                       "M", "S", [], "2024-01-01", -1,
                                       "native")
        message = make_message(self.store, self.collection)
        self.assertEqual(message["id"], "msg-1")
        self.assertEqual(message["seq"], 1)

    def test_custody_linkage_guards(self):
        custody = make_custody(self.store, self.org, self.collection)
        message = make_message(self.store, self.collection,
                               custody_id=custody["id"])
        self.assertEqual(message["custody_id"], custody["id"])
        other = self.store.create_collection(
            ADMIN, self.org["id"], "Other archive", self.policy["id"],
            "native")
        with self.assertRaises(ValidationError):
            make_message(self.store, other, custody_id=custody["id"])
        self.store.retire_custody(OPERATOR, custody["id"])
        with self.assertRaises(ValidationError):
            make_message(self.store, self.collection, ref="MSG-LATE",
                         custody_id=custody["id"])
        with self.assertRaises(NotFoundError):
            make_message(self.store, self.collection, ref="MSG-GHOST",
                         custody_id="key-99")

    def test_list_filters_and_order(self):
        first = make_message(self.store, self.collection, ref="MSG-A")
        second = make_message(self.store, self.collection, ref="MSG-B")
        listed = self.store.list_messages(ADMIN,
                                          collection_id=self.collection["id"])
        self.assertEqual([m["id"] for m in listed],
                         [first["id"], second["id"]])
        self.assertEqual(self.store.get_message(VIEWER, first["id"])["id"],
                         first["id"])


if __name__ == "__main__":
    unittest.main()
