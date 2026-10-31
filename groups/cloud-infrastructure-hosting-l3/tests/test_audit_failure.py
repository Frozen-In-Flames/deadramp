"""[L3] AU-5: audit writes fail closed.

If the JSONL append raises OSError, AuditLog.record rolls back the
in-memory append and raises AuditWriteError; a mutating store
operation whose audit write fails rolls back whole (records and id
counters, snapshot pattern); and the HTTP layer answers exactly
500 {"error": "audit write failed"} — never a 400, never a silent
success.
"""

import http.client
import json
import os
import tempfile
import threading
import unittest

import cloudinfra_helpers as H
from cloudinfra.audit import AuditLog
from cloudinfra.errors import AuditWriteError
from cloudinfra.service import USERS, make_server
from cloudinfra.store import CloudInfraStore


def call(port, method, path, user=None, role=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"Content-Type": "application/json"}
    if user is not None:
        headers["X-User"] = user
    if role is not None:
        headers["X-Role"] = role
    conn.request(method, path,
                 body=json.dumps(body) if body is not None else None,
                 headers=headers)
    response = conn.getresponse()
    raw = response.read().decode("utf-8")
    conn.close()
    return response.status, json.loads(raw) if raw else {}


def _broken_log(tmp):
    """An AuditLog whose JSONL path has become a directory, so the
    next append raises IsADirectoryError (an OSError)."""
    path = os.path.join(tmp, "audit.jsonl")
    log = AuditLog(path=path)
    log.path = tmp  # a directory: open(..., "a") raises OSError
    return log


class TestRecordFailsClosed(unittest.TestCase):
    def test_failed_append_raises_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = _broken_log(tmp)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "organization_create", "org-1")
            # The in-memory append was rolled back: memory and the
            # (unwritable) file never diverge.
            self.assertEqual(log.entries(), [])
            self.assertEqual(log.verify_chain(), (True, None))

    def test_chain_continues_after_a_failed_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path=path)
            log.record("alice", "organization_create", "org-1")
            log.path = tmp
            with self.assertRaises(AuditWriteError):
                log.record("alice", "tenancy_create", "ten-1")
            log.path = path
            log.record("alice", "tenancy_create", "ten-1")
            entries = log.entries()
            self.assertEqual([e["seq"] for e in entries], [0, 1])
            self.assertEqual(log.verify_chain(), (True, None))


class TestStoreFailsClosed(unittest.TestCase):
    def test_mutation_rolls_back_when_audit_write_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = _broken_log(tmp)
            store = CloudInfraStore(audit=log)
            with self.assertRaises(AuditWriteError):
                store.create_organization("org-x", "X", H.ADMIN)
            # Nothing was created and no id was consumed: with a
            # working log the same call yields org-1.
            store.audit = AuditLog()
            org = store.create_organization("org-x", "X", H.ADMIN)
            self.assertEqual(org["id"], "org-1")

    def test_later_mutation_rolls_back_to_prior_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = AuditLog()
            store = CloudInfraStore(audit=good)
            org = store.create_organization("org-x", "X", H.ADMIN)
            store.audit = _broken_log(tmp)
            with self.assertRaises(AuditWriteError):
                store.create_tenancy(org["id"], "ten-a", "A", "shared",
                                     H.ADMIN)
            store.audit = good
            self.assertEqual(
                store.list_tenancies(org["id"], H.ADMIN), [])
            tenancy = store.create_tenancy(
                org["id"], "ten-a", "A", "shared", H.ADMIN)
            self.assertEqual(tenancy["id"], "ten-1")


class TestServiceFailsClosed(unittest.TestCase):
    def test_audit_failure_is_exactly_500(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = _broken_log(tmp)
            store = CloudInfraStore(audit=audit)
            server = make_server("127.0.0.1", 0, store, audit, dict(USERS))
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever,
                                      daemon=True)
            thread.start()
            try:
                status, body = call(
                    port, "POST", "/organizations", user="alice",
                    role="admin", body={"org_ref": "org-500",
                                        "label": "Five Hundred"})
                self.assertEqual(status, 500)
                self.assertEqual(body, {"error": "audit write failed"})
                # The operation did not proceed.
                status, body = call(port, "GET", "/organizations",
                                    user="alice", role="admin")
                self.assertEqual(status, 200)
                self.assertEqual(body, {"organizations": []})
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
