"""Audit-log tests.

Traces to: Core function -- Append-only audit log / records_management;
contract for ``cms/audit.py``; AU-2/AU-3/AU-6/AU-9. JSONL files are
written into the group's ``scratch/`` directory.
"""

import json
import os
import unittest
from datetime import datetime

from cms_helpers import ADMIN, AUTHOR, EDITOR, PUBLISHER, VIEWER, drive_to_published, fresh_store, make_item, make_store
from cms.audit import AuditLog

GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(GROUP_ROOT, "scratch")


class TestAuditLog(unittest.TestCase):
    """Core: Audit log -- record()/entries() contract (records_management)."""

    def test_record_roundtrip(self):
        """Core: Audit log. entries() returns {ts, actor, action, target, details}."""
        log = AuditLog()
        log.record("alice", "site_create", "site-1", {"slug": "x"})
        e = log.entries()[0]
        self.assertEqual(set(e.keys()), {"ts", "actor", "action", "target", "details"})
        self.assertEqual(e["details"], {"slug": "x"})
        datetime.fromisoformat(e["ts"].replace("Z", "+00:00"))

    def test_user_actor_normalised(self):
        """Core: Audit log. A User actor is recorded as its name string."""
        log = AuditLog()
        log.record(ADMIN, "site_create", "site-1")
        self.assertEqual(log.entries()[0]["actor"], "alice")

    def test_append_only_and_copies(self):
        """Core: Audit log (AU-2/AU-9). Order preserved, no delete/update API, entries are copies."""
        log = AuditLog()
        log.record("alice", "site_create", "site-1")
        snap = dict(log.entries()[0])
        log.record("bob", "search", "q")
        self.assertEqual(log.entries()[0], snap)
        self.assertFalse(hasattr(log, "delete"))
        self.assertFalse(hasattr(log, "update"))
        log.entries()[0]["action"] = "hacked"
        self.assertEqual(log.entries()[0]["action"], "site_create")

    def test_empty(self):
        """Core: Audit log. A fresh log is empty."""
        self.assertEqual(AuditLog().entries(), [])

    def test_jsonl_round_trip(self):
        """Core: Audit log. JSONL save/load: file lines reload identically on construction."""
        os.makedirs(SCRATCH, exist_ok=True)
        path = os.path.join(SCRATCH, "test_audit_cms.jsonl")
        if os.path.exists(path):
            os.remove(path)
        try:
            log = AuditLog(path)
            log.record("alice", "site_create", "site-1")
            log.record("bob", "search", "hello")
            with open(path, encoding="utf-8") as fh:
                lines = [ln for ln in fh.read().splitlines() if ln.strip()]
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["actor"], "alice")
            reloaded = AuditLog(path)
            self.assertEqual(len(reloaded.entries()), 2)
            self.assertEqual(reloaded.entries()[1]["action"], "search")
        finally:
            if os.path.exists(path):
                os.remove(path)


class TestStoreAudit(unittest.TestCase):
    """Core: Audit log -- store records mutations, search, and denied attempts."""

    def test_store_records_each_mutation(self):
        """Core: Audit log. site/section/type/item/submit/approve/publish/asset/tag actions recorded."""
        audit = AuditLog()
        store, site, section = make_store(audit=audit)
        store.create_type(PUBLISHER, "release-note")
        tag = store.create_tag(EDITOR, "News Tag", "news-tag")
        item = make_item(store, site, tag_ids=[tag["id"]])
        store.update_item(AUTHOR, item["id"], body="v2")
        drive_to_published(store, store.get_item(item["id"], AUTHOR) if False else item)
        store.archive_item(PUBLISHER, item["id"])
        store.register_asset(EDITOR, site["id"], "a.pdf", "document", 10)
        actions = [e["action"] for e in audit.entries()]
        for expected in ("site_create", "section_create", "type_create", "tag_create",
                         "item_create", "item_update", "item_submit", "item_approve",
                         "item_publish", "item_archive", "asset_register"):
            with self.subTest(action=expected):
                self.assertIn(expected, actions)

    def test_search_audited(self):
        """Core: Audit log. search records a 'search' entry."""
        audit = AuditLog()
        store, site, _ = make_store(audit=audit)
        store.search(EDITOR, "main")
        self.assertIn("search", [e["action"] for e in audit.entries()])

    def test_denied_attempt_recorded_denied_suffix(self):
        """Core: Audit log (AC-3). A permission-denied write is recorded as '<action>:denied' and consumes no id."""
        audit = AuditLog()
        store = fresh_store(audit=audit)
        try:
            store.create_site(VIEWER, "Nope", "nope")
        except Exception:
            pass
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("site_write:denied", actions)
        self.assertEqual(store.list_sites(ADMIN), [])

    def test_failed_validation_records_no_success(self):
        """Core: Audit log / SI-10. A failed validation records no mutation entry."""
        audit = AuditLog()
        store = fresh_store(audit=audit)
        try:
            store.create_site(PUBLISHER, "Bad", "BAD SLUG!")
        except Exception:
            pass
        self.assertEqual([e for e in audit.entries() if e["action"] == "site_create"], [])


if __name__ == "__main__":
    unittest.main()
