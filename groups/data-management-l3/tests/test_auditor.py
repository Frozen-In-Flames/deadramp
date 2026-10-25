"""Auditor-role tests (L3 High uplift, AC-5 separation of duties).

Traces to: UNION-SPEC Core function 11 (Access control) as uplifted to
the FedRAMP High baseline -- AC-5: the ``auditor`` role (demo identity
``dana``) holds ``audit_read`` and nothing else, so audit review
exists as a duty separable from administration and stewardship. The
auditor may read the trail and verify its chain, and is denied every
operational surface -- datasets, search, sources, grants, exports --
at both the store layer and over HTTP.
"""

import http.client
import json
import threading
import unittest

from datamgmt_helpers import AUDITOR, STEWARD, USERS, make_store
from datamgmt.errors import PermissionDenied

DANA = {"X-User": "dana", "X-Role": "auditor"}


class TestAuditorStoreLevel(unittest.TestCase):
    """AC-5: the store enforces the auditor's single permission."""

    def test_auditor_denied_operational_reads_and_writes(self):
        """AC-5: AUDITOR raises PermissionDenied for dataset reads,
        catalog search, source reads, exports, and every write --
        while the same calls succeed for a steward."""
        store, dataset, source = make_store()
        for call in (
            lambda: store.list_datasets(AUDITOR),
            lambda: store.get_dataset(dataset["id"], AUDITOR),
            lambda: store.search("claims", AUDITOR),
            lambda: store.list_sources(AUDITOR),
            lambda: store.list_grants(actor=AUDITOR),
            lambda: store.create_dataset("X", "Y", AUDITOR),
            lambda: store.register_source("s", "api", AUDITOR),
            lambda: store.export_dataset(dataset["id"], AUDITOR),
        ):
            with self.assertRaises(PermissionDenied):
                call()
        # Control: the steward passes the same gates.
        self.assertEqual(len(store.list_datasets(STEWARD)), 1)


class AuditorServiceBase(unittest.TestCase):
    """A fresh server per test class run, seeded via the store."""

    @classmethod
    def setUpClass(cls):
        from datamgmt.audit import AuditLog
        from datamgmt.service import make_server
        from datamgmt.store import DataMgmtStore

        cls.audit = AuditLog()
        cls.store = DataMgmtStore(audit=cls.audit)
        make_store(audit=cls.audit)  # separate store; seeds audit entries
        cls.store.create_dataset(
            "Claims Extract", "Nightly extract", STEWARD
        )
        cls.server = make_server(
            "127.0.0.1", 0, cls.store, cls.audit, dict(USERS)
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

    def request(self, method, path, headers, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = json.dumps(body) if body is not None else None
        hdrs = dict(headers)
        if body is not None:
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


class TestAuditorServiceLevel(AuditorServiceBase):
    """AC-5 over HTTP: dana reviews the audit trail and nothing else."""

    def test_auditor_can_read_audit(self):
        """AC-5 / AU-6: GET /audit as dana -> 200 with entries."""
        status, parsed = self.request("GET", "/audit", DANA)
        self.assertEqual(status, 200)
        self.assertIn("entries", parsed)
        self.assertTrue(parsed["entries"])

    def test_auditor_can_verify_chain(self):
        """AC-5 / AU-9: GET /audit/verify as dana -> 200, ok true."""
        status, parsed = self.request("GET", "/audit/verify", DANA)
        self.assertEqual(status, 200)
        self.assertTrue(parsed["ok"])

    def test_auditor_denied_operational_endpoints(self):
        """AC-5: GET /datasets, GET /search, GET /sources, GET
        /grants and POST /datasets as dana are all 403."""
        for method, path in (
            ("GET", "/datasets"),
            ("GET", "/search?q=claims"),
            ("GET", "/sources"),
            ("GET", "/grants"),
            ("GET", "/retention-due"),
        ):
            with self.subTest(method=method, path=path):
                status, parsed = self.request(method, path, DANA)
                self.assertEqual(status, 403)
                self.assertIn("error", parsed)
        status, parsed = self.request(
            "POST", "/datasets", DANA,
            body={"name": "X", "description": "Y"},
        )
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
