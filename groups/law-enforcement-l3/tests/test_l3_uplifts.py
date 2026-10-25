"""High-baseline uplifts [L3].

Traces to: the Group 35 union spec's tier-uplift analysis -- the
hash-chained tamper-evident audit (AU-9, AU-3) with chain
verification, fail-closed audit writes with full store rollback
(AU-5), audit query / reduction (AU-6, AU-7), unsuccessful-logon
lockout (AC-7), the auditor role (AC-5), and the CLI lockout flags.

This file also carries the group's [L3] **negative control**: the
audit-tamper control. Mutating a stored audit entry in place must
make ``verify_chain()`` report failure at exactly that entry's
index, and editing one line of the JSONL file must be detected after
reload -- proving the chain catches the tampering defect class
rather than merely existing.
"""

import http.client
import json
import os
import threading
import unittest

from lawenf.__main__ import build_parser
from lawenf.audit import GENESIS_PREV_HASH, AuditLog
from lawenf.errors import AuditWriteError
from lawenf.service import make_server
from lawenf.store import LawEnfStore
from lawenf_helpers import ADMIN, MEMBER, USERS, make_store

SCRATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scratch")

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "member"}
BOB_WRONG_ROLE = {"X-User": "bob", "X-Role": "admin"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}
DANA = {"X-User": "dana", "X-Role": "auditor"}
MALLORY = {"X-User": "mallory", "X-Role": "member"}
MALLORY_WRONG_ROLE = {"X-User": "mallory", "X-Role": "viewer"}


def _scratch_file(name):
    path = os.path.join(SCRATCH, name)
    if os.path.exists(path):
        os.remove(path)
    return path


class TestHashChain(unittest.TestCase):
    """Uplift 1 (AU-9, AU-3): entries are hash-chained; the chain verifies."""

    def test_chain_fields_link_and_genesis(self):
        _store, audit, _matter = make_store()
        entries = audit.entries()
        self.assertEqual([e["seq"] for e in entries], list(range(len(entries))))
        self.assertEqual(entries[0]["prev_hash"], GENESIS_PREV_HASH)
        self.assertEqual(entries[0]["prev_hash"], "0" * 64)
        for prev, cur in zip(entries, entries[1:]):
            self.assertEqual(cur["prev_hash"], prev["hash"])
        for entry in entries:
            self.assertEqual(len(entry["hash"]), 64)
            int(entry["hash"], 16)  # hex

    def test_verify_chain_clean(self):
        _store, audit, _matter = make_store()
        self.assertEqual(audit.verify_chain(), (True, None))

    def test_verify_chain_empty_log(self):
        self.assertEqual(AuditLog().verify_chain(), (True, None))

    def test_tamper_in_place_localized_at_exact_index(self):
        # NEGATIVE CONTROL (canonical): a pristine chain verifies; an
        # in-place edit is caught at exactly the edited entry's index.
        _store, audit, _matter = make_store()
        self.assertEqual(audit.verify_chain(), (True, None))
        audit._entries[1]["actor"] = "eve"
        self.assertEqual(audit.verify_chain(), (False, 1))

    def test_tamper_stripped_hash_field_detected(self):
        _store, audit, _matter = make_store()
        del audit._entries[0]["hash"]
        self.assertEqual(audit.verify_chain(), (False, 0))

    def test_tamper_rewritten_prev_hash_detected(self):
        _store, audit, matter = make_store()
        _store.create_source(matter["id"], "SRC-1", "statute", MEMBER)
        audit._entries[2]["prev_hash"] = "f" * 64
        self.assertEqual(audit.verify_chain(), (False, 2))

    def test_jsonl_reload_verifies_and_tamper_detected(self):
        path = _scratch_file("audit-chain-test.jsonl")
        log = AuditLog(path=path)
        log.record("bob", "matter_create", "mat-1")
        log.record("bob", "member_add", "mat-1")
        log.record("alice", "matter_close", "mat-1")
        reloaded = AuditLog(path=path)
        self.assertEqual(reloaded.verify_chain(), (True, None))
        # Edit one line of the file: the chain must catch it at index 1.
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        edited = json.loads(lines[1])
        edited["actor"] = "eve"
        lines[1] = json.dumps(edited) + "\n"
        with open(path, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
        tampered = AuditLog(path=path)
        self.assertEqual(tampered.verify_chain(), (False, 1))


class TestAuditQuery(unittest.TestCase):
    """Uplift 3 (AU-6, AU-7): filtered audit reduction."""

    def setUp(self):
        self.store, self.audit, self.matter = make_store()
        self.src = self.store.create_source(
            self.matter["id"], "SRC-1", "statute", MEMBER)

    def test_query_by_actor(self):
        got = self.audit.query(actor="bob")
        self.assertTrue(got)
        self.assertTrue(all(e["actor"] == "bob" for e in got))
        self.assertEqual(self.audit.query(actor="nobody"), [])

    def test_query_by_action_and_target(self):
        got = self.audit.query(action="source_create")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["target"], self.src["id"])
        self.assertEqual(
            self.audit.query(target=self.src["id"])[0]["action"],
            "source_create")
        self.assertEqual(self.audit.query(action="no_such_action"), [])

    def test_query_time_window(self):
        all_entries = self.audit.entries()
        self.assertEqual(self.audit.query(since="9999-01-01"), [])
        self.assertEqual(self.audit.query(until="0000-01-01"), [])
        windowed = self.audit.query(
            since=all_entries[0]["ts"], until=all_entries[-1]["ts"])
        self.assertEqual(len(windowed), len(all_entries))


class TestFailClosed(unittest.TestCase):
    """Uplift 2 (AU-5): a failed audit write rolls the operation back."""

    def _broken_path(self, good_path):
        # A path under an existing *file*: opening it raises
        # NotADirectoryError, an OSError -- the write cannot succeed.
        return os.path.join(good_path, "child.jsonl")

    def test_record_rolls_back_on_write_failure(self):
        path = _scratch_file("audit-failclosed-test.jsonl")
        log = AuditLog(path=path)
        log.record("bob", "matter_create", "mat-1")
        log.path = self._broken_path(path)
        with self.assertRaises(AuditWriteError):
            log.record("bob", "source_create", "src-1")
        self.assertEqual(len(log.entries()), 1)
        self.assertEqual(log.verify_chain(), (True, None))

    def test_store_operation_rolls_back_in_full(self):
        path = _scratch_file("audit-store-failclosed-test.jsonl")
        audit = AuditLog(path=path)
        store = LawEnfStore(audit=audit)
        matter = store.create_matter("MATTER-REF-FC", ADMIN)
        audit.path = self._broken_path(path)
        with self.assertRaises(AuditWriteError):
            store.create_source(matter["id"], "SRC-1", "statute", ADMIN)
        with self.assertRaises(AuditWriteError):
            store.add_member(matter["id"], "carol", ADMIN)
        audit.path = path
        # Nothing was created, no member added, no id consumed.
        self.assertEqual(store.list_sources(matter["id"], ADMIN), [])
        self.assertEqual(store.get_matter(matter["id"], ADMIN)["members"],
                         ["alice"])
        src = store.create_source(matter["id"], "SRC-1", "statute", ADMIN)
        self.assertEqual(src["id"], "src-1")
        self.assertEqual(audit.verify_chain(), (True, None))


class UpliftServiceFixture(unittest.TestCase):
    """Spin the real server (with lockout kwargs) per test class."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = LawEnfStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit,
                                 USERS, max_failures=3, lockout_seconds=300)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def call(self, method, path, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = json.dumps(body) if body is not None else None
        conn.request(method, path, body=payload, headers=headers or {})
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        return resp.status, json.loads(raw) if raw else {}


class TestAuditorOverHttp(UpliftServiceFixture):
    """Uplift 5 (AC-5): dana reads the audit trail and nothing else."""

    def test_auditor_reads_audit_and_verify(self):
        status, _body = self.call("GET", "/audit", DANA)
        self.assertEqual(status, 200)
        # /audit/verify reports the count at verification time; the
        # audit_read entry the call itself records lands after.
        before = len(self.audit.entries())
        status, body = self.call("GET", "/audit/verify", DANA)
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertIsNone(body["first_bad_index"])
        self.assertEqual(body["entries"], before)

    def test_auditor_has_no_registry_access(self):
        status, _ = self.call("GET", "/matters", DANA)
        self.assertEqual(status, 403)
        status, _ = self.call("POST", "/matters", DANA,
                              {"matter_ref": "DANA-REF-1"})
        self.assertEqual(status, 403)

    def test_verify_endpoint_requires_audit_read(self):
        status, _ = self.call("GET", "/audit/verify", BOB)
        self.assertEqual(status, 403)
        status, body = self.call("GET", "/audit/verify", ALICE)
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])


class TestAuditFiltersOverHttp(UpliftServiceFixture):
    """Uplift 3 (AU-7): GET /audit filter parameters pass through."""

    def test_filters(self):
        status, _matter = self.call("POST", "/matters", BOB,
                                    {"matter_ref": "FILTER-REF-1"})
        self.assertEqual(status, 201)
        status, body = self.call("GET", "/audit?action=matter_create", ALICE)
        self.assertEqual(status, 200)
        self.assertTrue(body["entries"])
        self.assertTrue(all(e["action"] == "matter_create"
                            for e in body["entries"]))
        status, body = self.call("GET", "/audit?actor=bob", ALICE)
        self.assertTrue(body["entries"])
        self.assertTrue(all(e["actor"] == "bob" for e in body["entries"]))
        status, body = self.call("GET", "/audit?actor=nobody", ALICE)
        self.assertEqual(body["entries"], [])


class TestLockoutOverHttp(UpliftServiceFixture):
    """Uplift 4 (AC-7): consecutive failures lock the username."""

    def test_lockout_after_max_failures(self):
        for _ in range(3):
            status, _ = self.call("GET", "/matters", BOB_WRONG_ROLE)
            self.assertEqual(status, 401)
        # Even correct credentials are refused during the lock.
        status, _ = self.call("GET", "/matters", BOB)
        self.assertEqual(status, 403)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("auth:locked", actions)
        # Other users are unaffected.
        status, _ = self.call("GET", "/matters", CAROL)
        self.assertEqual(status, 200)

    def test_success_resets_the_failure_counter(self):
        for _ in range(2):
            status, _ = self.call("GET", "/matters", MALLORY_WRONG_ROLE)
            self.assertEqual(status, 401)
        status, _ = self.call("GET", "/matters", MALLORY)
        self.assertEqual(status, 200)
        for _ in range(2):
            status, _ = self.call("GET", "/matters", MALLORY_WRONG_ROLE)
            self.assertEqual(status, 401)
        # Two + success + two never reaches the lock threshold.
        status, _ = self.call("GET", "/matters", MALLORY)
        self.assertEqual(status, 200)


class TestCliLockoutFlags(unittest.TestCase):
    """Uplift 4 (AC-7): the CLI exposes the lockout knobs."""

    def test_flag_defaults_and_overrides(self):
        args = build_parser().parse_args(["serve"])
        self.assertEqual(args.max_failed_logins, 3)
        self.assertEqual(args.lockout_seconds, 300)
        args = build_parser().parse_args(
            ["serve", "--max-failed-logins", "5", "--lockout-seconds", "60"])
        self.assertEqual(args.max_failed_logins, 5)
        self.assertEqual(args.lockout_seconds, 60)


if __name__ == "__main__":
    unittest.main()
