"""File-sharing tests.

Traces to: UNION-SPEC Core function 3 (File sharing — files shared into
a workspace as versioned records: name, content type, size, SHA-256
digest, who shared it, when; re-sharing the same name creates the next
version) / ranking row 12 (File sharing, storage & content management,
9 siblings); Implementation contract for ``collab/store.py`` file
methods; control families AC-3 (membership boundary) and SI-10
(failed operations consume no id).
"""

import hashlib
import unittest

from collab_helpers import (
    ADMIN,
    MEMBER,
    OUTSIDER,
    VIEWER,
    fresh_store,
    make_store,
    share_sample_file,
)
from collab.errors import NotFoundError, PermissionDenied

FILE_KEYS = {
    "id", "workspace_id", "name", "version", "size_bytes", "sha256",
    "content_type", "shared_by", "created_utc",
}


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestShareFile(unittest.TestCase):
    """Core: File sharing — the versioned record and its digest."""

    def setUp(self):
        self.store, self.ws_id = make_store()

    def test_share_returns_the_contract_dict(self):
        """Core: File sharing. Contract: share_file returns {id,
        workspace_id, name, version, size_bytes, sha256, content_type,
        shared_by, created_utc} with a file- id."""
        rec = share_sample_file(
            self.store, self.ws_id, name="notes.txt", content="hello files"
        )
        self.assertEqual(set(rec.keys()), FILE_KEYS)
        self.assertEqual(rec["id"], "file-1")
        self.assertEqual(rec["workspace_id"], self.ws_id)
        self.assertEqual(rec["name"], "notes.txt")
        self.assertEqual(rec["shared_by"], "bob")
        self.assertEqual(rec["content_type"], "text/plain")

    def test_first_share_is_version_1(self):
        """Core: File sharing. Contract: 'version is 1 for the first
        share of that name in the workspace'."""
        rec = share_sample_file(self.store, self.ws_id)
        self.assertEqual(rec["version"], 1)

    def test_sha256_matches_hashlib_of_utf8_content(self):
        """Core: File sharing. Contract: sha256 is the digest of the
        content stored as UTF-8."""
        content = "quarterly numbers: 10, 20, 30"
        rec = share_sample_file(self.store, self.ws_id, content=content)
        self.assertEqual(rec["sha256"], _sha(content))

    def test_size_bytes_is_the_utf8_length(self):
        """Core: File sharing. Contract: size_bytes counts the UTF-8
        bytes (a non-ASCII character counts for more than one)."""
        content = "héllo"  # 5 characters, 6 UTF-8 bytes
        rec = share_sample_file(self.store, self.ws_id, content=content)
        self.assertEqual(rec["size_bytes"], len(content.encode("utf-8")))
        self.assertEqual(rec["size_bytes"], 6)
        self.assertEqual(rec["sha256"], _sha(content))

    def test_empty_content_has_zero_size_and_empty_digest(self):
        """Core: File sharing. An empty file is a valid versioned
        record with the well-known empty SHA-256."""
        rec = share_sample_file(self.store, self.ws_id, content="")
        self.assertEqual(rec["size_bytes"], 0)
        self.assertEqual(rec["sha256"], hashlib.sha256(b"").hexdigest())

    def test_custom_content_type_is_stored(self):
        """Core: File sharing. The content_type argument overrides the
        text/plain default."""
        rec = share_sample_file(
            self.store, self.ws_id, name="data.csv", content="a,b",
            content_type="text/csv",
        )
        self.assertEqual(rec["content_type"], "text/csv")

    def test_reshare_of_same_name_increments_version(self):
        """Core: File sharing. Contract: version 'increments per
        re-share' of the same name, under a new sequential file id."""
        first = share_sample_file(self.store, self.ws_id, content="v1 body")
        second = share_sample_file(self.store, self.ws_id, content="v2 body")
        third = share_sample_file(self.store, self.ws_id, content="v3 body")
        self.assertEqual(
            [first["version"], second["version"], third["version"]],
            [1, 2, 3],
        )
        self.assertEqual(
            [first["id"], second["id"], third["id"]],
            ["file-1", "file-2", "file-3"],
        )
        self.assertNotEqual(first["sha256"], second["sha256"])

    def test_different_name_starts_at_version_1(self):
        """Core: File sharing. Versioning is per name, not per
        workspace."""
        share_sample_file(self.store, self.ws_id, name="a.txt")
        other = share_sample_file(self.store, self.ws_id, name="b.txt")
        self.assertEqual(other["version"], 1)

    def test_same_name_in_another_workspace_starts_at_version_1(self):
        """Core: File sharing. Version counters are scoped to one
        workspace."""
        share_sample_file(self.store, self.ws_id, name="notes.txt")
        other_ws = self.store.create_workspace("dave-space", OUTSIDER)
        rec = share_sample_file(
            self.store, other_ws["id"], name="notes.txt", actor=OUTSIDER
        )
        self.assertEqual(rec["version"], 1)


class TestGetAndListFiles(unittest.TestCase):
    """Core: File sharing — retrieval, listing, access boundary."""

    def setUp(self):
        self.store, self.ws_id = make_store()

    def test_get_file_returns_record_plus_content(self):
        """Core: File sharing. Contract: get_file returns 'the file
        dict plus a content key' with the exact stored text."""
        rec = share_sample_file(
            self.store, self.ws_id, content="the body of the file"
        )
        got = self.store.get_file(self.ws_id, rec["id"], VIEWER)
        self.assertEqual(set(got.keys()), FILE_KEYS | {"content"})
        self.assertEqual(got["content"], "the body of the file")
        self.assertEqual(got["sha256"], rec["sha256"])

    def test_get_file_returns_the_requested_version(self):
        """Core: File sharing. Each version keeps its own content."""
        first = share_sample_file(self.store, self.ws_id, content="old body")
        second = share_sample_file(self.store, self.ws_id, content="new body")
        self.assertEqual(
            self.store.get_file(self.ws_id, first["id"], MEMBER)["content"],
            "old body",
        )
        self.assertEqual(
            self.store.get_file(self.ws_id, second["id"], MEMBER)["content"],
            "new body",
        )

    def test_list_files_returns_all_versions(self):
        """Core: File sharing. list_files returns every file record in
        the workspace for a member (read)."""
        share_sample_file(self.store, self.ws_id, name="a.txt")
        share_sample_file(self.store, self.ws_id, name="a.txt")
        share_sample_file(self.store, self.ws_id, name="b.txt")
        files = self.store.list_files(self.ws_id, VIEWER)
        self.assertEqual(len(files), 3)
        self.assertEqual(
            sorted((f["name"], f["version"]) for f in files),
            [("a.txt", 1), ("a.txt", 2), ("b.txt", 1)],
        )

    def test_get_unknown_file_is_not_found(self):
        """Core: File sharing. Unknown file id -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_file(self.ws_id, "file-999999", MEMBER)

    def test_non_member_is_denied_share_list_and_get(self):
        """Core: File sharing (AC-3). A non-member cannot share, list,
        or read the workspace's files."""
        rec = share_sample_file(self.store, self.ws_id)
        with self.assertRaises(PermissionDenied):
            share_sample_file(self.store, self.ws_id, actor=OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.store.list_files(self.ws_id, OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.store.get_file(self.ws_id, rec["id"], OUTSIDER)

    def test_viewer_member_can_read_but_cannot_share(self):
        """Core: File sharing + Access control. Viewer holds read, not
        share."""
        rec = share_sample_file(self.store, self.ws_id)
        self.assertEqual(
            self.store.get_file(self.ws_id, rec["id"], VIEWER)["id"],
            rec["id"],
        )
        with self.assertRaises(PermissionDenied):
            share_sample_file(self.store, self.ws_id, actor=VIEWER)

    def test_failed_share_consumes_no_file_id(self):
        """Core: File sharing (SI-10). A denied share leaves the next
        successful share at file-1."""
        store = fresh_store()
        ws = store.create_workspace("solo", MEMBER)
        store.add_member(ws["id"], "carol", MEMBER)
        with self.assertRaises(PermissionDenied):
            store.share_file(ws["id"], "x.txt", "body", VIEWER)
        rec = store.share_file(ws["id"], "x.txt", "body", MEMBER)
        self.assertEqual(rec["id"], "file-1")
        self.assertEqual(rec["version"], 1)


class TestFileShareNotifications(unittest.TestCase):
    """Core: File sharing + Notifications — other members are notified."""

    def setUp(self):
        self.store, self.ws_id = make_store()

    def test_other_members_get_a_file_share_notification(self):
        """Core: File sharing. Contract: 'every other workspace member
        gets a notification (kind file_share, ref_id = the file id)'."""
        rec = share_sample_file(self.store, self.ws_id)
        notes = self.store.notifications_for("carol")
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["kind"], "file_share")
        self.assertEqual(notes[0]["ref_id"], rec["id"])
        self.assertEqual(notes[0]["workspace_id"], self.ws_id)

    def test_author_gets_no_notification_for_own_share(self):
        """Core: File sharing. The sharer is not notified of their own
        share."""
        share_sample_file(self.store, self.ws_id)
        self.assertEqual(self.store.notifications_for("bob"), [])

    def test_every_member_is_notified_on_each_share(self):
        """Core: File sharing + Notifications. With three members, a
        share notifies both non-authors; a second share notifies
        them again."""
        self.store.add_member(self.ws_id, "dave", MEMBER)
        share_sample_file(self.store, self.ws_id, name="one.txt")
        share_sample_file(self.store, self.ws_id, name="two.txt")
        for name in ("carol", "dave"):
            with self.subTest(user=name):
                kinds = [
                    n["kind"] for n in self.store.notifications_for(name)
                ]
                self.assertEqual(kinds, ["file_share", "file_share"])
        # The platform admin is not a member and is not notified.
        self.assertEqual(self.store.notifications_for("alice"), [])


if __name__ == "__main__":
    unittest.main()
