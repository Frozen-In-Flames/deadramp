"""[L3] Fail-closed audit writes (Core function 10; AU-5).

If the audit log cannot durably record an entry, the operation being
audited does not proceed: ``AuditLog.record`` rolls back its in-memory
append and raises ``AuditWriteError``; the store rolls the whole
operation back (snapshot: no record, no id consumed); the service
layer never reports success.
"""

import http.client
import json
import os
import shutil
import threading
import unittest

from custsvc.audit import AuditLog
from custsvc.errors import AuditWriteError
from custsvc.service import USERS, make_server
from custsvc.store import CustsvcStore

from custsvc_helpers import ADMIN

GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(GROUP_ROOT, "scratch")


def _broken_log():
    """An AuditLog whose JSONL path is replaced by a directory, so the
    next append raises OSError deterministically on any platform."""
    path = os.path.join(SCRATCH, "test-failure-audit.jsonl")
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)
    log = AuditLog(path=path)
    log.record("setup", "seed", "seed")  # one good entry on disk
    os.remove(path)
    os.mkdir(path)  # same name, now a directory: appends fail
    return log, path


def _cleanup(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)


class TestRecordRollback(unittest.TestCase):
    def setUp(self):
        self.log, self.path = _broken_log()

    def tearDown(self):
        _cleanup(self.path)

    def test_failed_write_raises_audit_write_error(self):
        with self.assertRaises(AuditWriteError):
            self.log.record("alice", "case_create", "case-1")

    def test_failed_write_rolls_back_memory(self):
        before = len(self.log.entries())
        with self.assertRaises(AuditWriteError):
            self.log.record("alice", "case_create", "case-1")
        self.assertEqual(len(self.log.entries()), before)
        self.assertEqual(self.log.verify_chain(), (True, None))


class TestStoreRollback(unittest.TestCase):
    def setUp(self):
        self.log, self.path = _broken_log()
        self.store = CustsvcStore(audit=self.log)

    def tearDown(self):
        _cleanup(self.path)

    def test_create_rolls_back_record_and_id(self):
        with self.assertRaises(AuditWriteError):
            self.store.create_requester("citizen-001", "Citizen One", ADMIN)
        self.assertEqual(self.store.list_requesters(ADMIN), [])
        # Repair the log; the next create must get id req-1, proving
        # the failed operation consumed no id (snapshot restored the
        # counters as well as the records).
        _cleanup(self.path)
        self.log.path = os.path.join(SCRATCH, "test-failure-audit2.jsonl")
        rec = self.store.create_requester("citizen-001", "Citizen One", ADMIN)
        self.assertEqual(rec["id"], "req-1")
        _cleanup(self.log.path)

    def test_case_status_rolls_back(self):
        _cleanup(self.path)
        self.log.path = os.path.join(SCRATCH, "test-failure-audit3.jsonl")
        store = CustsvcStore(audit=self.log)
        req = store.create_requester("citizen-001", "Citizen One", ADMIN)
        case = store.create_case("Title", "Body", req["ref"], ADMIN)
        # Break the log again mid-flight.
        _cleanup(self.log.path)
        os.mkdir(self.log.path)
        with self.assertRaises(AuditWriteError):
            store.set_case_status(case["id"], "open", ADMIN)
        self.assertEqual(store.get_case(case["id"], ADMIN)["status"], "new")
        _cleanup(self.log.path)


class TestServiceFailClosed(unittest.TestCase):
    def setUp(self):
        self.log, self.path = _broken_log()
        self.store = CustsvcStore(audit=self.log)
        self.server = make_server("127.0.0.1", 0, self.store, self.log,
                                  dict(USERS))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        _cleanup(self.path)

    def test_service_create_is_not_a_success(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = json.dumps({"ref": "citizen-001", "label": "Citizen One"})
        status = None
        try:
            conn.request("POST", "/requesters", body=payload, headers={
                "X-User": "alice", "X-Role": "admin",
                "Content-Type": "application/json"})
            resp = conn.getresponse()
            resp.read()
            status = resp.status
        except Exception:
            status = None  # connection dropped: the operation failed
        finally:
            conn.close()
        self.assertNotEqual(status, 201)
        self.assertEqual(self.store.list_requesters(ADMIN), [])


if __name__ == "__main__":
    unittest.main()
