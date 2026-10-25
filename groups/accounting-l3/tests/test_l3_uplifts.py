"""L3 High-baseline uplift tests (Group 23, Accounting L3-adjacent).

Traces to: the six uplifts carried from the Analytics L3 pattern --
hash-chained tamper-evident audit (AU-9 / AU-3), fail-closed audit
writes (AU-5), audit query / reduction (AU-7), the chain-verification
endpoint, unsuccessful-logon lockout (AC-7), and the auditor role
(AC-5) -- applied to the Group 5 accounting build. Includes NEGATIVE
CONTROL #2: an in-place mutated audit entry must be detected by
``verify_chain()`` at exactly its index.
"""

import hashlib
import http.client
import json
import os
import tempfile
import threading
import time
import unittest
from urllib.parse import urlencode

from accounting_helpers import (
    ADMIN,
    AUDITOR,
    MEMBER,
    USERS_REGISTRY,
    VIEWER,
    balanced_lines,
    fresh_store,
    make_chart,
    make_store,
)
from accounting.access import PERMISSIONS, ROLES, can, permissions_for, require
from accounting.audit import AuditLog
from accounting.errors import AccountingError, AuditWriteError, PermissionDenied
from accounting.service import make_server
from accounting.store import AccountingStore

GENESIS = "0" * 64
ALL_OPERATIONAL = {
    "read", "create_book", "enter", "submit", "approve", "pay", "close",
    "manage_members", "admin",
}


def _expected_hash(entry):
    payload = {
        "seq": entry["seq"],
        "ts": entry["ts"],
        "actor": entry["actor"],
        "action": entry["action"],
        "target": entry["target"],
        "details": entry["details"],
        "prev_hash": entry["prev_hash"],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _populated_log(n=4):
    log = AuditLog()
    for i in range(n):
        log.record("alice", "op-%d" % i, "book-%d" % i, {"i": i})
    return log


def _break_log_file(log):
    """Make a file-backed log's path unwritable mid-flight: replace
    the JSONL file with a directory of the same name, so the next
    append raises IsADirectoryError (an OSError)."""
    if os.path.exists(log.path) and os.path.isfile(log.path):
        os.remove(log.path)
    if not os.path.exists(log.path):
        os.mkdir(log.path)


def _heal_log_file(log):
    """Undo _break_log_file: remove the directory so the next append
    recreates the JSONL file."""
    if os.path.isdir(log.path):
        os.rmdir(log.path)


class TestHashChainFields(unittest.TestCase):
    """AU-3 / AU-9 [L3]: entries carry seq, prev_hash and hash."""

    def test_entries_carry_chain_fields(self):
        """AU-3: every recorded entry gains seq (0-based), prev_hash
        and hash alongside the original ts/actor/action/target/details."""
        entries = _populated_log(3).entries()
        self.assertEqual([e["seq"] for e in entries], [0, 1, 2])
        for entry in entries:
            self.assertEqual(len(entry["hash"]), 64)
            self.assertEqual(len(entry["prev_hash"]), 64)
            int(entry["hash"], 16)  # hex, must not raise
            self.assertEqual(entry["actor"], "alice")

    def test_genesis_prev_hash_is_all_zeros(self):
        """AU-9: the first entry chains from the genesis prev_hash
        "0"*64."""
        entry = _populated_log(1).entries()[0]
        self.assertEqual(entry["prev_hash"], GENESIS)

    def test_hash_is_sha256_of_canonical_json(self):
        """AU-3 / AU-9: hash equals an independent recomputation of
        SHA-256 over the canonical JSON of the hashed fields."""
        for entry in _populated_log(3).entries():
            self.assertEqual(entry["hash"], _expected_hash(entry))

    def test_chain_links_correctly(self):
        """AU-9: each entry's prev_hash equals the previous entry's
        hash, so the trail is one continuous chain."""
        entries = _populated_log(5).entries()
        for previous, current in zip(entries, entries[1:]):
            self.assertEqual(current["prev_hash"], previous["hash"])


class TestVerifyChain(unittest.TestCase):
    """AU-9 [L3]: verify_chain() detects tampering, at the right index."""

    def test_verify_chain_ok_on_clean_log(self):
        """AU-9: an untouched log verifies: (True, None)."""
        ok, first_bad = _populated_log(4).verify_chain()
        self.assertTrue(ok)
        self.assertIsNone(first_bad)

    def test_verify_chain_ok_on_empty_log(self):
        """AU-9: an empty log is trivially a valid chain."""
        self.assertEqual(AuditLog().verify_chain(), (True, None))

    def test_negative_control_2_mutated_entry_fails_at_index_1(self):
        """NEGATIVE CONTROL #2 (AU-9): mutating a stored entry in
        place -- log._entries[1]["actor"] = "mallory" -- must make
        verify_chain() report failure at index 1, proving the chain
        detects edits rather than merely existing."""
        log = _populated_log(4)
        self.assertEqual(log.verify_chain(), (True, None))
        log._entries[1]["actor"] = "mallory"
        ok, first_bad = log.verify_chain()
        self.assertFalse(ok)
        self.assertEqual(first_bad, 1)

    def test_verify_chain_detects_missing_hash_fields(self):
        """AU-9: an entry stripped of its hash fields (e.g. a legacy
        or forged line) fails verification at its own index."""
        log = _populated_log(3)
        del log._entries[2]["hash"]
        ok, first_bad = log.verify_chain()
        self.assertFalse(ok)
        self.assertEqual(first_bad, 2)

    def test_verify_chain_detects_broken_link(self):
        """AU-9: rewriting an entry's prev_hash breaks the link and is
        detected at that entry."""
        log = _populated_log(3)
        log._entries[2]["prev_hash"] = GENESIS
        ok, first_bad = log.verify_chain()
        self.assertFalse(ok)
        self.assertEqual(first_bad, 2)


class TestHashChainPersistence(unittest.TestCase):
    """AU-9 [L3]: the chain survives the JSONL round-trip and detects
    file-level edits after reload."""

    def test_jsonl_roundtrip_verifies_ok(self):
        """AU-9: write entries to JSONL, reload into a new AuditLog,
        and the chain still verifies; it continues seamlessly."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            for i in range(3):
                log.record("alice", "op-%d" % i, "book-1")
            reloaded = AuditLog(path)
            self.assertEqual(len(reloaded.entries()), 3)
            self.assertEqual(reloaded.verify_chain(), (True, None))
            reloaded.record("bob", "entry_create", "book-1")
            self.assertEqual(reloaded.verify_chain(), (True, None))
            self.assertEqual(reloaded.entries()[3]["seq"], 3)

    def test_edited_jsonl_line_fails_verification_after_reload(self):
        """AU-9: editing one line of the JSONL file (changing the
        actor) is detected after reload, at that line's index."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            for i in range(3):
                log.record("alice", "op-%d" % i, "book-1")
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
            forged = json.loads(lines[1])
            forged["actor"] = "mallory"
            lines[1] = json.dumps(forged)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            reloaded = AuditLog(path)
            ok, first_bad = reloaded.verify_chain()
            self.assertFalse(ok)
            self.assertEqual(first_bad, 1)


class TestRecordFailClosed(unittest.TestCase):
    """AU-5 [L3]: record() fails closed on OSError."""

    def test_failed_record_raises_audit_write_error_and_rolls_back(self):
        """AU-5: an unwritable JSONL path makes record() raise
        AuditWriteError and leaves entries() exactly as it was."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "book_create", "book-1")
            before = log.entries()
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "entry_create", "book-1")
            self.assertEqual(log.entries(), before)

    def test_chain_still_verifies_after_failed_record(self):
        """AU-5 / AU-9: the rollback leaves no partial entry behind --
        the surviving chain still verifies and seq stays contiguous."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "book_create", "book-1")
            log.record("alice", "entry_create", "book-1")
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "entry_submit", "book-1")
            self.assertEqual(log.verify_chain(), (True, None))
            self.assertEqual([e["seq"] for e in log.entries()], [0, 1])

    def test_audit_write_error_is_an_accounting_error(self):
        """AU-5: AuditWriteError derives from AccountingError, so the
        package's single error hierarchy (and the service layer's
        mapping) covers audit failures."""
        self.assertTrue(issubclass(AuditWriteError, AccountingError))

    def test_in_memory_log_without_path_never_raises(self):
        """AU-5: an in-memory log (no path) has no write to fail --
        record() keeps the inherited Group 5 behavior."""
        log = AuditLog()
        entry = log.record("alice", "book_create", "book-1")
        self.assertEqual(entry["action"], "book_create")
        self.assertEqual(len(log.entries()), 1)


class TestStoreFailClosed(unittest.TestCase):
    """AU-5 [L3]: the store rolls the whole mutation back when its
    audit write fails -- no object created, no id consumed, state
    exactly as before the call."""

    def test_create_book_with_broken_audit_creates_nothing_and_consumes_no_id(self):
        """AU-5: create_book backed by a broken audit log raises
        AuditWriteError, creates no book, and the next successful
        book is still book-1."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = fresh_store(audit=audit)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.create_book("doomed-books", MEMBER)
            self.assertEqual(store.list_books(ADMIN), [])
            _heal_log_file(audit)
            book = store.create_book("doomed-books", MEMBER)
            self.assertEqual(book["id"], "book-1")

    def test_create_account_with_broken_audit_consumes_no_account_id(self):
        """AU-5: a failed account creation stores nothing; after the
        log heals, the next account takes the id the failed call
        would have used (acct-6 after the five chart accounts)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store, book_id = make_store(audit=audit)
            chart = make_chart(store, book_id)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.create_account(book_id, "9000", "Doomed", "asset", MEMBER)
            self.assertEqual(len(store.list_accounts(book_id, MEMBER)), 5)
            _heal_log_file(audit)
            account = store.create_account(
                book_id, "9000", "Doomed", "asset", MEMBER
            )
            self.assertEqual(account["id"], "acct-6")
            self.assertEqual(chart["cash"]["id"], "acct-1")

    def test_submit_with_broken_audit_leaves_entry_exactly_as_before(self):
        """AU-5: a state transition whose audit write fails is rolled
        back in full -- the entry stays draft with submitted_by None --
        and succeeds once the log heals."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store, book_id = make_store(audit=audit)
            chart = make_chart(store, book_id)
            entry = store.create_entry(
                book_id, "2026-01-05", "Invest",
                balanced_lines(chart["cash"]["id"], chart["equity"]["id"],
                               1000),
                MEMBER,
            )
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.submit_entry(book_id, entry["id"], MEMBER)
            after = store.get_entry(book_id, entry["id"], MEMBER)
            self.assertEqual(after["status"], "draft")
            self.assertIsNone(after["submitted_by"])
            _heal_log_file(audit)
            submitted = store.submit_entry(book_id, entry["id"], MEMBER)
            self.assertEqual(submitted["status"], "pending")

    def test_record_payment_with_broken_audit_leaves_invoice_unpaid(self):
        """AU-5: record_payment is atomic against audit failure -- no
        payment stored, the invoice's paid_cents and status unchanged,
        and the next successful payment takes the unconsumed id."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store, book_id = make_store(audit=audit)
            invoice = store.create_invoice(
                book_id, "Customer Co", "2026-01-05", "2026-02-04",
                [{"description": "Services", "quantity": 1,
                  "unit_price_cents": 5000}],
                MEMBER,
            )
            store.submit_invoice(book_id, invoice["id"], MEMBER)
            store.approve_invoice(book_id, invoice["id"], ADMIN)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.record_payment(
                    book_id, invoice["id"], 5000, "2026-01-07", MEMBER
                )
            after = store.get_invoice(book_id, invoice["id"], MEMBER)
            self.assertEqual(after["paid_cents"], 0)
            self.assertEqual(after["status"], "issued")
            self.assertEqual(store.list_payments(book_id, MEMBER), [])
            _heal_log_file(audit)
            payment = store.record_payment(
                book_id, invoice["id"], 5000, "2026-01-07", MEMBER
            )
            self.assertEqual(payment["id"], "pay-1")


class HttpBase(unittest.TestCase):
    """A fresh server per test class, on an ephemeral port."""

    users = None

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = AccountingStore(audit=cls.audit)
        cls.server = make_server(
            "127.0.0.1", 0, cls.store, cls.audit,
            dict(cls.users or USERS_REGISTRY),
        )
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = None
        hdrs = dict(headers or {})
        if body is not None:
            payload = json.dumps(body)
            hdrs.setdefault("Content-Type", "application/json")
        conn.request(method, path, body=payload, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
        conn.close()
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except ValueError:
            parsed = None
        return status, parsed


class TestServiceFailClosed(unittest.TestCase):
    """AU-5 [L3] over HTTP: the service does not silently proceed when
    the audit write fails."""

    def test_create_book_over_http_fails_closed(self):
        """AU-5: POST /books against a store whose audit log cannot
        write is not a success, and no book is created."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = AccountingStore(audit=audit)
            _break_log_file(audit)
            server = make_server(
                "127.0.0.1", 0, store, audit, dict(USERS_REGISTRY)
            )
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                conn.request(
                    "POST", "/books",
                    body=json.dumps({"name": "doomed"}),
                    headers={"X-User": "bob", "X-Role": "member",
                             "Content-Type": "application/json"},
                )
                resp = conn.getresponse()
                resp.read()
                status = resp.status
                conn.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
            self.assertNotIn(status, (200, 201))
            self.assertEqual(store.list_books(ADMIN), [])


# Fixed timestamps make the since/until windows deterministic.
_TS = [
    "2026-01-01T00:00:00+00:00",
    "2026-01-02T00:00:00+00:00",
    "2026-01-03T00:00:00+00:00",
    "2026-01-04T00:00:00+00:00",
]


def _pinned_log():
    log = AuditLog()
    log.record("alice", "book_create", "book-1")
    log.record("bob", "entry_create", "book-1")
    log.record("alice", "entry_submit", "book-1")
    log.record("carol", "entry_create", "book-2")
    for entry, ts in zip(log._entries, _TS):
        entry["ts"] = ts
    return log


class TestAuditQuery(unittest.TestCase):
    """AU-7 [L3]: AuditLog.query filters the trail."""

    def setUp(self):
        self.log = _pinned_log()

    def test_query_no_filters_returns_all(self):
        """AU-7: query() with no filters is the full trail, in order."""
        result = self.log.query()
        self.assertEqual(len(result), 4)
        self.assertEqual(
            [e["action"] for e in result],
            ["book_create", "entry_create", "entry_submit", "entry_create"],
        )

    def test_query_filters_by_actor(self):
        """AU-7: actor filter returns only that actor's entries."""
        result = self.log.query(actor="alice")
        self.assertEqual(len(result), 2)
        self.assertTrue(all(e["actor"] == "alice" for e in result))
        self.assertEqual(
            [e["action"] for e in result], ["book_create", "entry_submit"]
        )

    def test_query_filters_by_action(self):
        """AU-7: action filter returns only entries with that action."""
        result = self.log.query(action="entry_create")
        self.assertEqual(len(result), 2)
        self.assertEqual([e["actor"] for e in result], ["bob", "carol"])

    def test_query_filters_by_target(self):
        """AU-7: target filter returns only entries for that target."""
        result = self.log.query(target="book-2")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["actor"], "carol")

    def test_query_since_is_inclusive(self):
        """AU-7: since compares against the ts string, inclusively."""
        result = self.log.query(since=_TS[1])
        self.assertEqual([e["ts"] for e in result], _TS[1:])

    def test_query_until_is_inclusive(self):
        """AU-7: until compares against the ts string, inclusively."""
        result = self.log.query(until=_TS[2])
        self.assertEqual([e["ts"] for e in result], _TS[:3])

    def test_query_window_since_and_until(self):
        """AU-7: since+until together select the window between them."""
        result = self.log.query(since=_TS[1], until=_TS[2])
        self.assertEqual([e["ts"] for e in result], _TS[1:3])
        self.assertEqual([e["actor"] for e in result], ["bob", "alice"])

    def test_query_combines_filters(self):
        """AU-7: filters compose (AND) -- actor plus action narrows to
        the intersection."""
        result = self.log.query(actor="alice", action="entry_submit")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["target"], "book-1")
        self.assertEqual(self.log.query(actor="alice", action="entry_create"), [])


class TestAuditQueryEndpoint(HttpBase):
    """AU-7 [L3] over HTTP: GET /audit passes actor/action/target/
    since/until through to AuditLog.query (audit_read required), and
    keeps the existing convention of recording the audit_read after
    the entries are read."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.audit.record("alice", "seed_create", "book-1")
        cls.audit.record("bob", "seed_entry", "book-1")
        cls.audit.record("alice", "seed_submit", "book-2")

    def _get_audit(self, params=None, headers=None):
        path = "/audit"
        if params:
            path += "?" + urlencode(params)
        return self.request(
            "GET", path,
            headers=headers or {"X-User": "alice", "X-Role": "admin"},
        )

    def test_audit_endpoint_filters_by_actor(self):
        """AU-7: GET /audit?actor=alice returns only alice's entries."""
        status, payload = self._get_audit({"actor": "alice"})
        self.assertEqual(status, 200)
        entries = payload["entries"]
        self.assertTrue(entries)
        self.assertTrue(all(e["actor"] == "alice" for e in entries))
        self.assertTrue(any(e["action"] == "seed_create" for e in entries))

    def test_audit_endpoint_filters_by_action(self):
        """AU-7: GET /audit?action=seed_entry returns only those."""
        status, payload = self._get_audit({"action": "seed_entry"})
        self.assertEqual(status, 200)
        entries = payload["entries"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["actor"], "bob")

    def test_audit_endpoint_filters_by_target(self):
        """AU-7: GET /audit?target=book-2 returns only that target."""
        status, payload = self._get_audit({"target": "book-2"})
        self.assertEqual(status, 200)
        entries = payload["entries"]
        self.assertTrue(entries)
        self.assertTrue(all(e["target"] == "book-2" for e in entries))
        self.assertTrue(any(e["action"] == "seed_submit" for e in entries))

    def test_audit_endpoint_filters_by_window(self):
        """AU-7: GET /audit?since=...&until=... selects by the ts
        window -- a window after all activity is empty, and a window
        bracketing everything returns the seeded trail."""
        status, payload = self._get_audit(
            {"since": "2999-01-01T00:00:00+00:00"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["entries"], [])
        status, payload = self._get_audit(
            {"since": "2000-01-01T00:00:00+00:00",
             "until": "2999-01-01T00:00:00+00:00"}
        )
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(payload["entries"]), 3)

    def test_audit_endpoint_unfiltered_unchanged(self):
        """AU-7: GET /audit with no parameters keeps the Group 5
        behavior (full trail in {"entries": [...]})."""
        status, payload = self._get_audit()
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(payload["entries"]), 3)

    def test_audit_endpoint_filters_usable_by_auditor(self):
        """AC-5 / AU-7: the auditor role can use the reduced audit
        search, not just administrators."""
        status, payload = self._get_audit(
            {"actor": "bob"},
            headers={"X-User": "dana", "X-Role": "auditor"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(
            all(e["actor"] == "bob" for e in payload["entries"])
        )


class TestAuditVerifyEndpoint(HttpBase):
    """AU-9 [L3] over HTTP: GET /audit/verify requires audit_read and
    reports {ok, entries, first_bad_index} from verify_chain()."""

    def test_verify_endpoint_reports_clean_chain(self):
        """AU-9: GET /audit/verify on a clean log returns ok=true,
        the entry count, and first_bad_index=null; the count is read
        before the endpoint's own audit_read entry is appended."""
        before = len(self.audit.entries())
        status, payload = self.request(
            "GET", "/audit/verify", headers={"X-User": "alice", "X-Role": "admin"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIsNone(payload["first_bad_index"])
        self.assertEqual(payload["entries"], before)

    def test_verify_endpoint_denies_viewer_and_member(self):
        """AU-6: roles without audit_read (viewer, member) get 403."""
        for headers in ({"X-User": "carol", "X-Role": "viewer"},
                        {"X-User": "bob", "X-Role": "member"}):
            with self.subTest(headers=headers):
                status, payload = self.request(
                    "GET", "/audit/verify", headers=headers
                )
                self.assertEqual(status, 403)
                self.assertIn("error", payload)

    def test_verify_endpoint_reports_tamper_at_exact_index(self):
        """AU-9: after an in-place mutation of the shared log, the
        endpoint reports ok=false at exactly that entry's index
        (dedicated server, so the tamper pollutes nothing else)."""
        audit = AuditLog()
        store = AccountingStore(audit=audit)
        server = make_server(
            "127.0.0.1", 0, store, audit, dict(USERS_REGISTRY)
        )
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            audit.record("alice", "book_create", "book-1")
            audit.record("alice", "entry_create", "book-1")
            audit.record("alice", "entry_submit", "book-1")
            audit._entries[1]["actor"] = "mallory"
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            conn.request(
                "GET", "/audit/verify",
                headers={"X-User": "alice", "X-Role": "admin"},
            )
            resp = conn.getresponse()
            payload = json.loads(resp.read().decode("utf-8"))
            status = resp.status
            conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertEqual(status, 200)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["first_bad_index"], 1)
        self.assertEqual(payload["entries"], 3)


class LockoutBase(unittest.TestCase):
    """A fresh server per test, so failure counters never leak
    between tests (each make_server call gets its own AC-7 state)."""

    max_failures = 3
    lockout_seconds = 300

    def setUp(self):
        self.audit = AuditLog()
        self.store = AccountingStore(audit=self.audit)
        self.server = make_server(
            "127.0.0.1", 0, self.store, self.audit, dict(USERS_REGISTRY),
            max_failures=self.max_failures,
            lockout_seconds=self.lockout_seconds,
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def get_books(self, user, role):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request(
            "GET", "/books", headers={"X-User": user, "X-Role": role}
        )
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
        conn.close()
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except ValueError:
            parsed = None
        return status, parsed

    def fail(self, user, wrong_role, times=1):
        return [self.get_books(user, wrong_role)[0] for _ in range(times)]


class TestLockout(LockoutBase):
    """AC-7 [L3]: lockout at the failure threshold."""

    def test_locked_after_max_failures_correct_role_still_403(self):
        """AC-7: max_failures bad-role attempts are ordinary 401s;
        the next attempt -- with the CORRECT role -- is refused 403
        while the lock holds."""
        self.assertEqual(self.fail("bob", "admin", times=3), [401, 401, 401])
        status, parsed = self.get_books("bob", "member")
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_locked_attempt_is_audited_as_auth_locked(self):
        """AC-7: an attempt made while locked is audited with action
        "auth:locked" naming the locked username."""
        self.fail("bob", "admin", times=3)
        self.get_books("bob", "member")  # the locked attempt
        locked = [
            e for e in self.audit.entries()
            if e["action"] == "auth:locked" and e["actor"] == "bob"
        ]
        self.assertTrue(locked, "no auth:locked audit entry for bob")

    def test_unknown_user_failures_also_lock(self):
        """AC-7: failures are tracked per username even for users
        outside the registry -- mallory locks like anyone else."""
        self.assertEqual(
            self.fail("mallory", "admin", times=3), [401, 401, 401]
        )
        status, _ = self.get_books("mallory", "admin")
        self.assertEqual(status, 403)

    def test_lockout_is_per_user(self):
        """AC-7: one user's lockout does not affect anyone else --
        alice still authenticates while bob is locked."""
        self.fail("bob", "admin", times=3)
        status, _ = self.get_books("bob", "member")
        self.assertEqual(status, 403)
        status, _ = self.get_books("alice", "admin")
        self.assertEqual(status, 200)
        status, _ = self.get_books("carol", "viewer")
        self.assertEqual(status, 200)

    def test_success_before_threshold_resets_counter(self):
        """AC-7: a successful authentication resets the consecutive
        failure counter -- fail, fail, succeed, fail, fail is NOT
        locked (the count restarted at the success)."""
        self.assertEqual(self.fail("bob", "admin", times=2), [401, 401])
        status, _ = self.get_books("bob", "member")
        self.assertEqual(status, 200)  # success resets the counter
        self.assertEqual(self.fail("bob", "admin", times=2), [401, 401])
        status, _ = self.get_books("bob", "member")
        self.assertEqual(status, 200)  # only 2 consecutive: not locked


class TestLockoutExpiry(LockoutBase):
    """AC-7 [L3]: lock expiry lets the user in again."""

    max_failures = 2
    lockout_seconds = 1

    def test_lock_expires_and_user_can_log_on(self):
        """AC-7: after lockout_seconds elapse, the correct role is
        accepted again."""
        self.assertEqual(self.fail("bob", "admin", times=2), [401, 401])
        status, _ = self.get_books("bob", "member")
        self.assertEqual(status, 403)  # locked
        time.sleep(1.2)
        status, _ = self.get_books("bob", "member")
        self.assertEqual(status, 200)  # lock expired


class TestAuditorRole(unittest.TestCase):
    """AC-5 [L3]: the auditor role holds exactly {audit_read}."""

    def test_auditor_in_roles_tuple(self):
        """AC-5: ROLES includes auditor alongside the Group 5 roles."""
        self.assertIn("auditor", ROLES)
        self.assertEqual(
            set(ROLES), {"admin", "member", "viewer", "auditor"}
        )

    def test_auditor_permissions_exact(self):
        """AC-5: auditor = {"audit_read"} exactly, nothing more."""
        self.assertEqual(set(PERMISSIONS["auditor"]), {"audit_read"})
        self.assertEqual(set(permissions_for("auditor")), {"audit_read"})

    def test_auditor_may_audit_read(self):
        """AC-5 / AU-6: the auditor can review the audit trail."""
        require(AUDITOR, "audit_read")  # must not raise
        self.assertTrue(can(AUDITOR, "audit_read"))

    def test_auditor_denied_every_operational_action(self):
        """AC-5: auditor holds no operational permission -- read,
        create_book, enter, submit, approve, pay, close,
        manage_members and admin are all denied."""
        for action in sorted(ALL_OPERATIONAL):
            with self.subTest(action=action):
                self.assertFalse(can(AUDITOR, action))
                with self.assertRaises(PermissionDenied):
                    require(AUDITOR, action)

    def test_auditor_permissions_disjoint_from_operations(self):
        """AC-5: no operational permission leaks into the auditor
        role."""
        self.assertEqual(
            set(PERMISSIONS["auditor"]) & ALL_OPERATIONAL, set()
        )

    def test_existing_roles_unchanged_by_auditor_addition(self):
        """AC-5: adding auditor moved no existing role's permissions
        (admin still all ten, member its seven, viewer {read})."""
        self.assertEqual(len(PERMISSIONS["admin"]), 10)
        self.assertEqual(
            set(PERMISSIONS["member"]),
            {"read", "create_book", "enter", "submit", "approve", "pay",
             "close"},
        )
        self.assertEqual(set(PERMISSIONS["viewer"]), {"read"})


class TestAuditorEndpoints(HttpBase):
    """AC-5 [L3] over HTTP: dana (auditor) reads /audit and
    /audit/verify, and is 403 on operational endpoints."""

    DANA = {"X-User": "dana", "X-Role": "auditor"}

    def test_auditor_reads_audit(self):
        """AC-5 / AU-6: GET /audit as dana -> 200 with entries."""
        status, payload = self.request("GET", "/audit", headers=self.DANA)
        self.assertEqual(status, 200)
        self.assertIsInstance(payload["entries"], list)

    def test_auditor_reads_audit_verify(self):
        """AC-5 / AU-9: GET /audit/verify as dana -> 200, ok chain."""
        status, payload = self.request(
            "GET", "/audit/verify", headers=self.DANA
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIsNone(payload["first_bad_index"])

    def test_auditor_denied_operational_reads(self):
        """AC-5: GET /books as dana -> 403 (auditor lacks read)."""
        status, payload = self.request("GET", "/books", headers=self.DANA)
        self.assertEqual(status, 403)
        self.assertIn("error", payload)

    def test_auditor_denied_operational_writes(self):
        """AC-5: POST /books as dana -> 403 (auditor lacks
        create_book), and no book is created."""
        status, payload = self.request(
            "POST", "/books", headers=self.DANA, body={"name": "nope"}
        )
        self.assertEqual(status, 403)
        self.assertIn("error", payload)
        self.assertEqual(self.store.list_books(ADMIN), [])


if __name__ == "__main__":
    unittest.main()
