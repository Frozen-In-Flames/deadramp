"""Final GAPS batch — Cybersecurity & Risk Management L1 extension surface.

Traces to: the 5 open entries of this group's section in the
repo-root GAPS.md and to gaps-batch/DECISION.md. Every test names
its entry.

Category discipline pinned throughout: this module builds records
forms only — no engine scans, detects, enforces, executes, or
invents a score. Stub-engine families carry ``reference_stub:
true`` on every record (playbook runs also ``executed: false``),
extension views are counts only, and identity surfaces are hooks,
never an IdP. The GRC entry (idx 170) was re-judged from its
drafted stub-engine triage to build-extension: the records form
below is the one the Moderate sibling shipped for the identical
family against a byte-identical core; grounds are recorded in
BATCH.md.
"""

import unittest

from cyber_helpers import ADMIN, ANALYST, VIEWER  # noqa: F401  (path setup)

from cyber.audit import AuditLog
from cyber.errors import NotFoundError, PermissionDenied, ValidationError
from cyber.extensions import ExtensionStore


def fresh_ext(audit=None):
    if audit is None:
        audit = AuditLog()
    return ExtensionStore(audit=audit), audit


def _all_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            keys |= _all_keys(value)
    return keys


class TestGrcAutomation(unittest.TestCase):
    """Entry idx 170: Full GRC automation suites beyond the substrate
    (3 of 5 claim the family; control mapping & assessment records
    are Core) — records form, re-judged build-extension."""

    def test_evidence_task_full_lifecycle_two_actors(self):
        ext, _ = fresh_ext()
        framework = ext.register_framework(
            "fw-fedramp-low", "FedRAMP Low baseline", actor=ADMIN)
        self.assertEqual(framework["id"], "framework-1")
        task = ext.create_evidence_task(
            framework["id"], "AU-2", "evidence-owner", actor=ANALYST)
        self.assertEqual(task["status"], "open")
        collected = ext.transition_evidence_task(
            task["id"], "collected", actor=ANALYST)
        self.assertEqual(collected["collected_by"], "bob")
        verified = ext.transition_evidence_task(
            task["id"], "verified", actor=ADMIN)
        self.assertEqual(verified["status"], "verified")
        self.assertEqual(verified["verified_by"], "alice")

    def test_evidence_task_unknown_control_rejected(self):
        ext, _ = fresh_ext()
        framework = ext.register_framework(
            "fw-a", "Framework A", actor=ADMIN)
        with self.assertRaises(ValidationError):
            ext.create_evidence_task(
                framework["id"], "XX-99", "evidence-owner", actor=ANALYST)
        # The failed create consumed no id.
        task = ext.create_evidence_task(
            framework["id"], "AC-2", "evidence-owner", actor=ANALYST)
        self.assertEqual(task["id"], "evtask-1")

    def test_evidence_task_unknown_framework_rejected(self):
        ext, _ = fresh_ext()
        with self.assertRaises(NotFoundError):
            ext.create_evidence_task(
                "framework-99", "AC-2", "evidence-owner", actor=ANALYST)

    def test_evidence_task_invalid_transition_rejected(self):
        ext, _ = fresh_ext()
        framework = ext.register_framework(
            "fw-a", "Framework A", actor=ADMIN)
        task = ext.create_evidence_task(
            framework["id"], "AC-2", "evidence-owner", actor=ANALYST)
        with self.assertRaises(ValidationError):
            ext.transition_evidence_task(task["id"], "verified", actor=ADMIN)

    def test_separation_of_duties_guard(self):
        """Negative control (canonical): the collector of a piece of
        evidence may not verify it. Mutating the guard seam
        ``_check_verifier_not_collector`` so it never fires must
        fail this test (drill recorded in tests/README.md)."""
        ext, _ = fresh_ext()
        framework = ext.register_framework(
            "fw-a", "Framework A", actor=ADMIN)
        task = ext.create_evidence_task(
            framework["id"], "AU-2", "evidence-owner", actor=ANALYST)
        ext.transition_evidence_task(task["id"], "collected", actor=ANALYST)
        with self.assertRaises(ValidationError):
            ext.transition_evidence_task(task["id"], "verified", actor=ANALYST)
        # The rejected verification changed nothing.
        tasks = ext.list_evidence_tasks(actor=ADMIN, status="collected")
        self.assertEqual(len(tasks), 1)
        self.assertIsNone(tasks[0]["verified_by"])


class TestIdentityHooks(unittest.TestCase):
    """Entry idx 172: Identity products / IdP (1; the core ships
    access-control hooks only) — hooks only, no IdP."""

    def test_hook_record_states_hook_only(self):
        ext, _ = fresh_ext()
        hook = ext.register_identity_hook(
            "idp-alpha", "sso", "service login", actor=ANALYST)
        self.assertEqual(hook["id"], "hook-1")
        self.assertTrue(hook["hook_only"])
        self.assertFalse(hook["identity_provider"])
        hooks = ext.list_identity_hooks(actor=VIEWER, hook_kind="sso")
        self.assertEqual(len(hooks), 1)

    def test_bad_hook_kind_rejected(self):
        ext, _ = fresh_ext()
        with self.assertRaises(ValidationError):
            ext.register_identity_hook(
                "idp-alpha", "kerberos", "service login", actor=ANALYST)


class TestPhishingTraining(unittest.TestCase):
    """Entry idx 173 (training half): Phishing-defense enforcement &
    simulation / training content (1; DMARC enforcement) —
    campaign program records; nothing is sent or simulated."""

    def test_campaign_and_training_counts(self):
        ext, _ = fresh_ext()
        campaign = ext.create_campaign(
            "camp-q1", "Q1 awareness", "staff-all", actor=ANALYST)
        self.assertEqual(campaign["status"], "planned")
        self.assertFalse(campaign["messages_sent"])
        ext.transition_campaign(campaign["id"], "approved", actor=ANALYST)
        first = ext.assign_training(campaign["id"], "learner-001", actor=ANALYST)
        ext.assign_training(campaign["id"], "learner-002", actor=ANALYST)
        ext.complete_training(first["id"], actor=ANALYST)
        counts = ext.campaign_counts(actor=VIEWER, campaign_id=campaign["id"])
        self.assertEqual(counts["total"], 2)
        self.assertEqual(counts["by_status"], {"assigned": 1, "completed": 1})

    def test_campaign_lifecycle_rejects_skip(self):
        ext, _ = fresh_ext()
        campaign = ext.create_campaign(
            "camp-q1", "Q1 awareness", "staff-all", actor=ANALYST)
        with self.assertRaises(ValidationError):
            ext.transition_campaign(campaign["id"], "completed", actor=ANALYST)


class TestDmarcRecords(unittest.TestCase):
    """Entry idx 173 (enforcement half): DMARC enforcement as
    records — declared policy plus aggregate reports as reported by
    the external platform; nothing is enforced here."""

    def test_policy_and_report_counts_derived(self):
        ext, _ = fresh_ext()
        policy = ext.register_dmarc_policy(
            "domain-main", "reject", actor=ANALYST)
        self.assertEqual(policy["id"], "dmarc-1")
        self.assertFalse(policy["enforced_here"])
        ext.record_dmarc_report(
            policy["id"], {"aligned": 120, "failed": 3}, actor=ANALYST)
        ext.record_dmarc_report(
            policy["id"], {"aligned": 30, "failed": 1}, actor=ANALYST)
        counts = ext.dmarc_counts(actor=VIEWER, policy_id=policy["id"])
        self.assertEqual(counts["reports"], 2)
        self.assertEqual(counts["reported_totals"],
                         {"aligned": 150, "failed": 4})

    def test_bad_policy_rejected(self):
        ext, _ = fresh_ext()
        with self.assertRaises(ValidationError):
            ext.register_dmarc_policy("domain-main", "block", actor=ANALYST)

    def test_hostname_shaped_domain_ref_rejected(self):
        ext, _ = fresh_ext()
        with self.assertRaises(ValidationError):
            ext.register_dmarc_policy("mail.example.org", "reject", actor=ANALYST)

    def test_report_counts_must_be_counts(self):
        ext, _ = fresh_ext()
        policy = ext.register_dmarc_policy("domain-main", "none", actor=ANALYST)
        for bad in ({"aligned": -1}, {"aligned": 1.5}, {"aligned": True},
                    {"aligned": "many"}, {}):
            with self.assertRaises(ValidationError):
                ext.record_dmarc_report(policy["id"], bad, actor=ANALYST)
        # No rejected report consumed an id.
        report = ext.record_dmarc_report(
            policy["id"], {"aligned": 1}, actor=ANALYST)
        self.assertEqual(report["id"], "dmarcrep-1")
        self.assertFalse(report["enforced_here"])


class TestModelReferences(unittest.TestCase):
    """Entry idx 169: AI/ML-powered analytics & anomaly detection
    models (2 of 5) — labeled reference implementation."""

    def test_model_records_are_labeled_stubs(self):
        ext, _ = fresh_ext()
        model = ext.register_model_reference(
            "model-alpha", "anomaly_detection", actor=ANALYST)
        self.assertTrue(model["reference_stub"])
        output = ext.record_model_output_reference(
            model["id"], "finding-ext-1", "anomalous", actor=ANALYST)
        self.assertTrue(output["reference_stub"])
        self.assertEqual(output["reported_label"], "anomalous")
        outputs = ext.list_model_outputs(actor=VIEWER, model_id=model["id"])
        self.assertEqual(len(outputs), 1)

    def test_model_output_requires_registered_model(self):
        ext, _ = fresh_ext()
        with self.assertRaises(NotFoundError):
            ext.record_model_output_reference(
                "model-99", "finding-ext-1", "anomalous", actor=ANALYST)

    def test_no_score_anywhere_in_model_records(self):
        ext, _ = fresh_ext()
        model = ext.register_model_reference(
            "model-alpha", "classification", actor=ANALYST)
        ext.record_model_output_reference(
            model["id"], "finding-ext-1", "benign", actor=ANALYST)
        records = ext.list_model_references(actor=ADMIN) \
            + ext.list_model_outputs(actor=ADMIN)
        for key in _all_keys(records):
            self.assertNotIn("score", key)


class TestSoarReferences(unittest.TestCase):
    """Entry idx 171: Automation & orchestration engines (SOAR /
    workflow) (1) — labeled reference implementation; the registry
    never executes."""

    def test_playbook_run_is_reference_only(self):
        ext, _ = fresh_ext()
        playbook = ext.register_playbook_reference(
            "pb-triage", "Finding triage", actor=ANALYST)
        self.assertTrue(playbook["reference_stub"])
        run = ext.record_playbook_run_reference(
            playbook["id"], "trigger-001", actor=ANALYST)
        self.assertTrue(run["reference_stub"])
        self.assertFalse(run["executed"])
        runs = ext.list_playbook_runs(actor=VIEWER, playbook_id=playbook["id"])
        self.assertEqual(len(runs), 1)


class TestAccessAndAudit(unittest.TestCase):
    """Cross-cutting: founding permission matrix, audited denials,
    counts-only summary."""

    def test_viewer_cannot_register_and_denial_is_audited(self):
        ext, audit = fresh_ext()
        with self.assertRaises(PermissionDenied):
            ext.register_identity_hook(
                "idp-alpha", "sso", "service login", actor=VIEWER)
        denied = [e for e in audit.entries()
                  if e["action"] == "hook_register:denied"]
        self.assertEqual(len(denied), 1)
        # The denial consumed no id.
        hook = ext.register_identity_hook(
            "idp-alpha", "sso", "service login", actor=ANALYST)
        self.assertEqual(hook["id"], "hook-1")

    def test_viewer_can_read(self):
        ext, _ = fresh_ext()
        ext.register_framework("fw-a", "Framework A", actor=ADMIN)
        self.assertEqual(len(ext.list_frameworks(actor=VIEWER)), 1)

    def test_extension_summary_counts_only(self):
        ext, _ = fresh_ext()
        ext.register_framework("fw-a", "Framework A", actor=ADMIN)
        ext.register_model_reference("model-a", "other", actor=ANALYST)
        summary = ext.extension_summary(actor=VIEWER)
        self.assertEqual(summary["records"]["frameworks"], 1)
        self.assertEqual(summary["records"]["models"], 1)
        self.assertEqual(summary["total"], 2)
        for key in _all_keys(summary):
            self.assertNotIn("score", key)
            self.assertNotIn("rate", key)
            self.assertNotIn("grade", key)


if __name__ == "__main__":
    unittest.main()
