"""Negative control: the deployment slot rule must be
load-bearing.

Traces to: the group's required negative control (Core function 5,
SI-10). The group's signature invariant is the deployment slot
rule: within one tenancy, at most one deployment of a given
workload reference may be active at a time, enforced by the store's
_check_deployment_slot seam on activation. The mutant is a
CloudInfraStore subclass whose _check_deployment_slot does
nothing: if the suite still passed against the mutant, the slot
tests would be testing that code ran, not that the invariant
holds. Each test asserts (1) the canonical expectation from the
real implementation, (2) the mutant would NOT produce that
expectation, and (3) a literal assertRaises(AssertionError)
showing that treating the mutant's outcome as the expected outcome
fails.

The file-level mutation drill (seam body replaced in a copy of
store.py, full suite re-run, failures recorded, file restored
byte-identical) is recorded in tests/mutation-run.txt and pinned
by TestDrillRecord below.

[L3] This tier adds a second seam: the audit hash chain's
``_entry_hash`` in audit.py (AU-9). Its in-suite discrimination
lives in test_audit_chain.py (the hash is recomputed independently
with hashlib, and tamper cases expect verify_chain to fail); its
file-level drill (constant-hash mutant, full suite re-run,
failures recorded, file restored byte-identical) is recorded in
tests/audit-mutation-run.txt and pinned by TestAuditDrillRecord
below.
"""

import hashlib
import os
import re
import unittest

import cloudinfra_helpers as H
from cloudinfra.errors import ValidationError
from cloudinfra.store import CloudInfraStore

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
STORE_PATH = os.path.join(TESTS_DIR, "..", "src", "cloudinfra", "store.py")
AUDIT_PATH = os.path.join(TESTS_DIR, "..", "src", "cloudinfra", "audit.py")


class MutantCloudInfraStore(CloudInfraStore):
    """A store with the deployment slot check removed (the mutant)."""

    def _check_deployment_slot(self, tenancy_id, workload_ref,
                               exclude_deployment_id=None):
        return None


def _scenario(store):
    org = store.create_organization(H.ORG_REF, H.ORG_LABEL, H.ADMIN)
    store.add_member(org["id"], H.MEMBER.name, H.ADMIN)
    tenancy = store.create_tenancy(
        org["id"], "ten-a", "A", "shared", H.MEMBER)
    first = store.create_deployment(
        org["id"], tenancy["id"], "dep-1", "wl-1", H.MEMBER)
    second = store.create_deployment(
        org["id"], tenancy["id"], "dep-2", "wl-1", H.MEMBER)
    store.activate_deployment(org["id"], first["id"], H.MEMBER)
    return org, second


class TestNegativeControlDeploymentSlot(unittest.TestCase):
    """Canonical: the second activation is refused; the mutant
    waves it through."""

    def test_canonical_expectation_refuses_second_activation(self):
        store, _audit = H.make_store()
        org, second = _scenario(store)
        # (1) Canonical expectation: refused, and nothing changed.
        with self.assertRaises(ValidationError):
            store.activate_deployment(org["id"], second["id"], H.MEMBER)
        self.assertEqual(
            store.get_deployment(org["id"], second["id"], H.MEMBER)["status"],
            "recorded")

    def test_mutant_would_not_produce_that_expectation(self):
        mutant = MutantCloudInfraStore(audit=H.AuditLog())
        org, second = _scenario(mutant)
        # (2) The mutant's outcome: the second activation succeeds.
        activated = mutant.activate_deployment(org["id"], second["id"], H.MEMBER)
        self.assertEqual(activated["status"], "active")
        # (3) Treating the mutant's outcome as the canonical
        # expectation fails, by construction.
        with self.assertRaises(AssertionError):
            self.assertEqual(activated["status"], "recorded")


class TestDrillRecord(unittest.TestCase):
    """The recorded file-level drill must exist, name its failure
    count, and the shipped store must hash to the recorded value."""

    def test_mutation_run_recorded(self):
        path = os.path.join(TESTS_DIR, "mutation-run.txt")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        match = re.search(r"failures recorded by the drill: (\d+)", text)
        self.assertIsNotNone(match, "mutation-run.txt must record a count")
        self.assertGreaterEqual(int(match.group(1)), 1)
        self.assertIn("_check_deployment_slot", text)

    def test_store_restored_byte_identical(self):
        with open(os.path.join(TESTS_DIR, "store.py.sha256"),
                  encoding="utf-8") as fh:
            recorded = fh.read().split()[0]
        with open(STORE_PATH, "rb") as fh:
            current = hashlib.sha256(fh.read()).hexdigest()
        self.assertEqual(current, recorded)


class TestAuditDrillRecord(unittest.TestCase):
    """[L3] The recorded audit-hash file-level drill must exist,
    name its failure count, and the shipped audit.py must hash to
    the recorded value."""

    def test_audit_mutation_run_recorded(self):
        path = os.path.join(TESTS_DIR, "audit-mutation-run.txt")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        match = re.search(r"failures recorded by the drill: (\d+)", text)
        self.assertIsNotNone(match,
                             "audit-mutation-run.txt must record a count")
        self.assertGreaterEqual(int(match.group(1)), 1)
        self.assertIn("_entry_hash", text)

    def test_audit_restored_byte_identical(self):
        with open(os.path.join(TESTS_DIR, "audit.py.sha256"),
                  encoding="utf-8") as fh:
            recorded = fh.read().split()[0]
        with open(AUDIT_PATH, "rb") as fh:
            current = hashlib.sha256(fh.read()).hexdigest()
        self.assertEqual(current, recorded)


if __name__ == "__main__":
    unittest.main()
