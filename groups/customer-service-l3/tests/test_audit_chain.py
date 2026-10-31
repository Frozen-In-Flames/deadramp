"""[L3] Hash-chained audit (Core function 10; AU-9 / AU-3).

Every audit entry carries ``seq`` / ``prev_hash`` / ``hash``;
``verify_chain()`` recomputes the chain and localizes the first bad
entry. Includes negative control #2: an in-place tampered entry MUST
make ``verify_chain()`` report failure at exactly that index -- an
oracle that passes on a tampered chain would be testing that code
ran, not that the chain detects tampering.
"""

import http.client
import json
import os
import threading
import unittest

from custsvc.audit import GENESIS_PREV_HASH, AuditLog
from custsvc.service import USERS, make_server
from custsvc.store import CustsvcStore

GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(GROUP_ROOT, "scratch")

ADMIN_H = {"X-User": "alice", "X-Role": "admin"}
AGENT_H = {"X-User": "bob", "X-Role": "agent"}
VIEWER_H = {"X-User": "carol", "X-Role": "viewer"}
AUDITOR_H = {"X-User": "dana", "X-Role": "auditor"}


def _log_with(n=3):
    log = AuditLog()
    for i in range(n):
        log.record("alice", "action-%d" % i, "target-%d" % i)
    return log


class TestChainFields(unittest.TestCase):
    def test_entries_carry_chain_fields(self):
        entries = _log_with(3).entries()
        self.assertEqual([e["seq"] for e in entries], [0, 1, 2])
        self.assertEqual(entries[0]["prev_hash"], GENESIS_PREV_HASH)
        self.assertEqual(entries[1]["prev_hash"], entries[0]["hash"])
        self.assertEqual(entries[2]["prev_hash"], entries[1]["hash"])
        for e in entries:
            self.assertEqual(len(e["hash"]), 64)

    def test_clean_chain_verifies(self):
        self.assertEqual(_log_with(4).verify_chain(), (True, None))

    def test_empty_chain_verifies(self):
        self.assertEqual(AuditLog().verify_chain(), (True, None))


class TestTamperDetection(unittest.TestCase):
    def test_negative_control_2_mutated_entry_fails_at_index_1(self):
        log = _log_with(3)
        self.assertEqual(log.verify_chain(), (True, None))
        log._entries[1]["actor"] = "mallory"
        self.assertEqual(log.verify_chain(), (False, 1))

    def test_stripped_hash_field_detected(self):
        log = _log_with(3)
        del log._entries[2]["hash"]
        self.assertEqual(log.verify_chain(), (False, 2))

    def test_rewritten_prev_hash_detected(self):
        log = _log_with(3)
        log._entries[2]["prev_hash"] = "f" * 64
        self.assertEqual(log.verify_chain(), (False, 2))

    def test_deleted_middle_entry_detected(self):
        log = _log_with(3)
        del log._entries[1]
        ok, bad = log.verify_chain()
        self.assertFalse(ok)
        self.assertEqual(bad, 1)


class TestChainPersistence(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(SCRATCH, "test-chain-audit.jsonl")
        if os.path.exists(self.path):
            os.remove(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_jsonl_roundtrip_verifies(self):
        log = AuditLog(path=self.path)
        log.record("alice", "case_create", "case-1")
        log.record("bob", "case_status", "case-1")
        reloaded = AuditLog(path=self.path)
        self.assertEqual(len(reloaded.entries()), 2)
        self.assertEqual(reloaded.verify_chain(), (True, None))

    def test_edited_jsonl_line_detected_after_reload(self):
        log = AuditLog(path=self.path)
        log.record("alice", "case_create", "case-1")
        log.record("bob", "case_status", "case-1")
        with open(self.path, encoding="utf-8") as fh:
            lines = fh.readlines()
        entry = json.loads(lines[1])
        entry["actor"] = "mallory"
        lines[1] = json.dumps(entry) + "\n"
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
        reloaded = AuditLog(path=self.path)
        self.assertEqual(reloaded.verify_chain(), (False, 1))


class VerifyEndpointFixture(unittest.TestCase):
    def setUp(self):
        self.audit = AuditLog()
        self.store = CustsvcStore(audit=self.audit)
        self.server = make_server("127.0.0.1", 0, self.store, self.audit,
                                  dict(USERS))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def call(self, method, path, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = json.dumps(body) if body is not None else None
        hdrs = dict(headers or {})
        if payload is not None:
            hdrs["Content-Type"] = "application/json"
        conn.request(method, path, body=payload, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        return resp.status, json.loads(raw) if raw else {}


class TestVerifyEndpoint(VerifyEndpointFixture):
    def test_admin_can_verify(self):
        status, body = self.call("GET", "/audit/verify", headers=ADMIN_H)
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertIsNone(body["first_bad_index"])

    def test_auditor_can_verify(self):
        status, body = self.call("GET", "/audit/verify", headers=AUDITOR_H)
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

    def test_agent_and_viewer_cannot_verify(self):
        for headers in (AGENT_H, VIEWER_H):
            status, _ = self.call("GET", "/audit/verify", headers=headers)
            self.assertEqual(status, 403)

    def test_verify_reports_entry_count(self):
        self.call("POST", "/requesters", headers=ADMIN_H,
                  body={"ref": "citizen-001", "label": "Citizen One"})
        status, body = self.call("GET", "/audit/verify", headers=ADMIN_H)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(body["entries"], 1)


if __name__ == "__main__":
    unittest.main()
