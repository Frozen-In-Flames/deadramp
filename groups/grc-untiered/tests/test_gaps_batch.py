"""Final GAPS batch — Untiered Set 3, Governance, Risk, and
Compliance (GRC): the extension surface in ``src/grc/extensions.py``.

Traces to: the 12 OPEN entries in GAPS.md under "Untiered Set 3 —
Governance, Risk, and Compliance (GRC) (15 forks, tier null)", as
triaged in ``gaps-batch/inventory.json`` and recorded per entry in
``BATCH.md``. Pins, per entry: the records form built, the house
labels (``reference_stub`` / ``reference_transport``) on every stub
record, verbatim storage of reported statuses and outcomes,
derived-never-stored for every computed value, RBAC via the core
``grc.access`` actions with denied writes audited, and failed
operations consuming no id.

Cross-cutting pins for the whole surface: the category's founding
**no-score invariant** (a recursive key scan finds no score-shaped
key in any returned value, extension or core posture) and the set's
**tier-null discipline** (a recursive key scan finds no tier-shaped
or baseline-shaped key anywhere on the extension surface).
"""

import unittest

import grc_helpers as H
from grc.access import User
from grc.audit import AuditLog
from grc.errors import NotFoundError, PermissionDenied, ValidationError
from grc.extensions import GrcExtensions, _check_reviewer_not_filer

ADMIN = H.ADMIN
MEMBER = H.MEMBER
VIEWER = H.VIEWER
DANA = User("dana", "admin")
SYS = H.SYSTEM_REF
FW = H.SEED_FRAMEWORK_ID

SCORE_FRAGMENTS = ("score", "rating", "grade", "percent")
TIER_FRAGMENTS = ("tier", "baseline", "cmmc", "fedramp", "impact_level")


def make_extensions():
    """Fresh core store (canonical system + indicator) + extensions."""
    audit = AuditLog()
    store, _system, _indicator = H.make_store(audit=audit)
    return GrcExtensions(store), store, audit


def _all_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _all_keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _all_keys(item)


def audit_actions(audit):
    return [entry["action"] for entry in audit.entries()]


class TestEvidenceCollectionValidation(unittest.TestCase):
    """Entry: Automated evidence collection & validation engine —
    built as collection-run records plus batch evidence-review
    records (outcomes verbatim, filer != reviewer)."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def test_collection_run_shape_and_labels(self):
        run = self.ext.create_collection_run(
            "nightly sync", SYS, "telemetry export", MEMBER,
            control_ids=["IA-2"],
        )
        self.assertEqual(run["id"], "col-1")
        self.assertIs(run["reference_transport"], True)
        self.assertIs(run["collected_here"], False)
        self.assertEqual(run["state"], "recorded_reference_only")
        self.assertEqual(run["control_ids"], ["IA-2"])
        self.assertEqual(run["created_by"], "bob")

    def test_collection_run_changes_no_core_record(self):
        before = self.store.posture_summary(MEMBER)
        self.ext.create_collection_run("nightly sync", SYS, "export", MEMBER)
        self.assertEqual(self.store.posture_summary(MEMBER), before)
        self.assertEqual(self.store.list_evidence(MEMBER), [])

    def test_collection_run_unknown_system_consumes_no_id(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_collection_run("x", "SYS-404", "export", MEMBER)
        run = self.ext.create_collection_run("x", SYS, "export", MEMBER)
        self.assertEqual(run["id"], "col-1")

    def test_collection_run_unknown_control_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_collection_run(
                "x", SYS, "export", MEMBER, control_ids=["ZZ-9"]
            )

    def test_collection_run_viewer_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_collection_run("x", SYS, "export", VIEWER)
        self.assertIn("ext_collection_run_create:denied", audit_actions(self.audit))

    def _filed_evidence(self):
        return self.store.create_evidence(
            "config export", "payload", ["IA-2"], [SYS], ADMIN
        )

    def test_review_verbatim_and_core_record_untouched(self):
        evidence = self._filed_evidence()
        review = self.ext.record_evidence_review(
            evidence["id"], "Accepted (assessor wording)", DANA, note="looks right"
        )
        self.assertEqual(review["id"], "evr-1")
        self.assertEqual(review["validation_status"], "Accepted (assessor wording)")
        self.assertIs(review["applied_to_core"], False)
        # The core evidence record — including its own recorded
        # validation status — is exactly as the core left it.
        core = self.store.get_evidence(evidence["id"], ADMIN)
        self.assertEqual(core["validation_status"], "unvalidated")
        self.assertIsNone(core["validated_by"])

    def test_review_outcome_summary_counts(self):
        first = self._filed_evidence()
        second = self.store.create_evidence(
            "scan output", "other", ["IA-2"], [SYS], ADMIN
        )
        self.ext.record_evidence_review(first["id"], "accepted", DANA)
        self.ext.record_evidence_review(second["id"], "accepted", DANA)
        summary = self.ext.evidence_review_summary(VIEWER)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["by_validation_status"], {"accepted": 2})
        self.assertEqual(summary["method"], "deterministic_counts")

    def test_member_may_not_review(self):
        evidence = self.store.create_evidence(
            "member-filed", "payload", ["IA-2"], [SYS], MEMBER
        )
        with self.assertRaises(PermissionDenied):
            self.ext.record_evidence_review(evidence["id"], "accepted", MEMBER)


class TestVulnerabilityScanning(unittest.TestCase):
    """Entry: Vulnerability scanning engine — built as a scanner
    registry plus scan-report records whose findings land as core
    finding records, severity verbatim."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()
        self.ext.create_scanner("SCAN-1", "scanner one", MEMBER)

    def test_scanner_duplicate_ref_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_scanner("SCAN-1", "again", MEMBER)

    def test_scanner_viewer_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_scanner("SCAN-2", "two", VIEWER)

    def test_scan_report_lands_core_findings_verbatim(self):
        report = self.ext.record_scan_report(
            "SCAN-1", SYS, "2026-07-01T00:00:00Z", MEMBER,
            findings_reported=[
                {"title": "Old TLS", "severity": "Moderate-ish",
                 "source": "SCAN-1", "due_date": "2026-06-30",
                 "control_ids": ["IA-2"]},
                {"title": "Weak cipher", "severity": "HIGH!!",
                 "source": "SCAN-1", "due_date": "2026-12-31"},
            ],
        )
        self.assertEqual(report["id"], "scr-1")
        self.assertIs(report["executed_here"], False)
        self.assertEqual(report["reported_count"], 2)
        findings = self.store.list_findings(MEMBER, system_ref=SYS)
        self.assertEqual([f["id"] for f in findings], report["finding_ids"])
        self.assertEqual(findings[0]["severity"], "Moderate-ish")
        self.assertEqual(findings[1]["severity"], "HIGH!!")
        self.assertEqual(findings[0]["status"], "open")
        # The landed findings carry the core's read-time derivation.
        view = self.store.get_finding(findings[0]["id"], MEMBER, as_of="2026-07-15")
        self.assertEqual(view["derived_status"], "overdue")

    def test_scan_report_validates_all_before_recording(self):
        with self.assertRaises(ValidationError):
            self.ext.record_scan_report(
                "SCAN-1", SYS, "2026-07-01T00:00:00Z", MEMBER,
                findings_reported=[
                    {"title": "fine", "severity": "low", "source": "SCAN-1",
                     "due_date": "2026-06-30"},
                    {"title": "bad date", "severity": "low", "source": "SCAN-1",
                     "due_date": "30/06/2026"},
                ],
            )
        self.assertEqual(self.store.list_findings(MEMBER), [])
        report = self.ext.record_scan_report(
            "SCAN-1", SYS, "2026-07-01T00:00:00Z", MEMBER, findings_reported=[]
        )
        self.assertEqual(report["id"], "scr-1")

    def test_scan_report_unknown_scanner(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_scan_report(
                "SCAN-404", SYS, "2026-07-01T00:00:00Z", MEMBER
            )

    def test_scan_summary_counts(self):
        self.ext.record_scan_report(
            "SCAN-1", SYS, "2026-07-01T00:00:00Z", MEMBER,
            findings_reported=[
                {"title": "a", "severity": "low", "source": "SCAN-1",
                 "due_date": "2026-06-30"},
            ],
        )
        summary = self.ext.scan_report_summary(VIEWER)
        self.assertEqual(summary["reports_total"], 1)
        self.assertEqual(summary["scanners_total"], 1)
        self.assertEqual(summary["findings_reported_total"], 1)


class TestScoringRecordsForm(unittest.TestCase):
    """Entry: Posture & risk scoring engines — built in records form
    only (BATCH.md re-judgment of form): rules held as data, never
    applied; score labels recorded verbatim, never computed."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def test_rule_held_as_data(self):
        rule = self.ext.create_scoring_rule(
            "PAIN-style bands", "N1..N5 by reported exposure", ADMIN
        )
        self.assertEqual(rule["id"], "srl-1")
        self.assertEqual(rule["method"], "recorded_rules_only")
        self.assertIs(rule["applied_here"], False)
        self.assertEqual(rule["rule_text"], "N1..N5 by reported exposure")

    def test_rule_is_admin_only_and_denial_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_scoring_rule("x", "y", MEMBER)
        self.assertIn("ext_scoring_rule_create:denied", audit_actions(self.audit))

    def test_reported_score_verbatim(self):
        record = self.ext.record_reported_score(
            SYS, "PAIN N3 (vendor band)", MEMBER, source_ref="northwatch-export"
        )
        self.assertEqual(record["id"], "rps-1")
        self.assertEqual(record["label"], "PAIN N3 (vendor band)")
        self.assertIs(record["computed_here"], False)
        self.assertEqual(record["state"], "recorded_reference_only")

    def test_reported_score_summary_counts_labels_only(self):
        self.ext.record_reported_score(SYS, "N3", MEMBER)
        self.ext.record_reported_score(SYS, "N3", MEMBER)
        self.ext.record_reported_score(SYS, "N1", MEMBER)
        summary = self.ext.reported_score_summary(VIEWER)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["by_label"], {"N3": 2, "N1": 1})
        for key in _all_keys(summary):
            self.assertFalse(
                any(fragment in key.lower() for fragment in SCORE_FRAGMENTS), key
            )

    def test_reported_score_unknown_system_consumes_no_id(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_reported_score("SYS-404", "N3", MEMBER)
        record = self.ext.record_reported_score(SYS, "N3", MEMBER)
        self.assertEqual(record["id"], "rps-1")

    def test_rules_unaffected_by_recorded_scores(self):
        rule = self.ext.create_scoring_rule("bands", "text", ADMIN)
        self.ext.record_reported_score(SYS, "N3", MEMBER)
        self.assertEqual(self.ext.get_scoring_rule(rule["id"], VIEWER), rule)


class TestEnclaveRecords(unittest.TestCase):
    """Entry: Hosted enclave & PaaS operations — built in records
    form: enclave records plus hosting states stored as reported;
    nothing is hosted here."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def test_enclave_shape_and_labels(self):
        enclave = self.ext.create_enclave(
            "ENC-1", "enclave one", MEMBER, system_refs=[SYS]
        )
        self.assertIs(enclave["hosted_here"], False)
        self.assertEqual(enclave["state"], "recorded_reference_only")
        self.assertNotIn("current_reported_state", enclave)

    def test_current_reported_state_derived_at_read(self):
        self.ext.create_enclave("ENC-1", "enclave one", MEMBER)
        self.assertIsNone(self.ext.get_enclave("ENC-1", VIEWER)["current_reported_state"])
        self.ext.record_hosting_state("ENC-1", "provisioning (reported)", MEMBER)
        self.ext.record_hosting_state("ENC-1", "operational (reported)", MEMBER)
        view = self.ext.get_enclave("ENC-1", VIEWER)
        self.assertEqual(view["current_reported_state"], "operational (reported)")
        self.assertEqual(len(view["reported_states"]), 2)

    def test_enclave_duplicate_and_unknown_system(self):
        self.ext.create_enclave("ENC-1", "one", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.create_enclave("ENC-1", "again", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.create_enclave("ENC-2", "two", MEMBER, system_refs=["SYS-404"])

    def test_enclave_viewer_may_not_create(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_enclave("ENC-1", "one", VIEWER)

    def test_enclave_summary_counts(self):
        self.ext.create_enclave("ENC-1", "one", MEMBER)
        self.ext.record_hosting_state("ENC-1", "operational (reported)", MEMBER)
        summary = self.ext.enclave_summary(VIEWER)
        self.assertEqual(summary["enclaves_total"], 1)
        self.assertEqual(summary["states_by_reported_state"],
                         {"operational (reported)": 1})


class TestPackageGeneration(unittest.TestCase):
    """Entry: FedRAMP package generation — built as package records
    whose manifest deterministically assembles held records."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()
        self.evidence = self.store.create_evidence(
            "config export", "payload", ["IA-2"], [SYS], ADMIN
        )
        self.finding = H.make_finding(self.store)
        self.store.create_assessment(
            SYS, FW, "full scope", "assessor-7", "2026-06-01",
            "Satisfactory-ish", MEMBER,
        )
        auth = self.store.create_authorization(SYS, FW, ADMIN)
        self.store.transition_authorization(auth["id"], "in_progress", ADMIN)
        policy = self.ext.create_policy(
            "Access control policy", ADMIN, system_ref=SYS, framework_id=FW
        )
        self.ext.transition_policy(policy["id"], "in_review", ADMIN)
        self.ext.transition_policy(policy["id"], "approved", ADMIN)

    def test_manifest_assembles_held_records(self):
        package = self.ext.create_package(SYS, FW, MEMBER, as_of="2026-07-15")
        self.assertEqual(package["id"], "pkg-1")
        self.assertEqual(package["method"], "deterministic_manifest_assembly")
        self.assertIs(package["narrative_generated"], False)
        self.assertIs(package["documents_emitted"], False)
        counts = package["counts"]
        self.assertEqual(counts["controls_total"], 21)
        self.assertEqual(counts["evidence_total"], 1)
        self.assertEqual(counts["findings_total"], 1)
        self.assertEqual(counts["assessments_total"], 1)
        self.assertEqual(counts["authorizations_total"], 1)
        self.assertEqual(counts["policies_total"], 1)
        manifest = package["manifest"]
        self.assertEqual(manifest["evidence"][0]["sha256"],
                         self.evidence["sha256"])
        self.assertEqual(manifest["findings"][0]["derived_status"], "overdue")
        self.assertEqual(manifest["assessments"][0]["result"], "Satisfactory-ish")
        self.assertEqual(manifest["authorizations"][0]["status"], "in_progress")
        self.assertEqual(manifest["policies"][0]["current_state"], "approved")
        self.assertEqual(len(manifest["controls"]), 21)

    def test_package_is_a_snapshot(self):
        package = self.ext.create_package(SYS, FW, MEMBER, as_of="2026-07-15")
        H.make_finding(self.store, title="later finding")
        again = self.ext.get_package(package["id"], VIEWER)
        self.assertEqual(again["counts"]["findings_total"], 1)

    def test_package_unknown_system_or_framework(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_package("SYS-404", FW, MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.create_package(SYS, "FW-404", MEMBER)

    def test_package_viewer_may_not_create(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_package(SYS, FW, VIEWER)


class TestPolicyLifecycle(unittest.TestCase):
    """Entry: Policy lifecycle engine — built as policy records with
    a guarded lifecycle; current state and attestation status are
    derived at read, never stored."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def _policy(self, **kwargs):
        return self.ext.create_policy("Access control policy", ADMIN, **kwargs)

    def test_current_state_derived_never_stored(self):
        policy = self._policy()
        self.assertNotIn("current_state", policy)
        self.assertEqual(policy["initial_state"], "draft")
        view = self.ext.get_policy(policy["id"], VIEWER)
        self.assertEqual(view["current_state"], "draft")
        self.assertEqual(view["transitions"], [])
        self.ext.transition_policy(policy["id"], "in_review", ADMIN)
        moved = self.ext.transition_policy(policy["id"], "approved", ADMIN)
        self.assertEqual(moved["current_state"], "approved")
        self.assertEqual(
            [(t["from"], t["to"]) for t in moved["transitions"]],
            [("draft", "in_review"), ("in_review", "approved")],
        )
        # The stored record still carries no current_state key.
        self.assertNotIn("current_state", self.ext._policies[policy["id"]])

    def test_illegal_transition_denied_and_state_unchanged(self):
        policy = self._policy()
        with self.assertRaises(ValidationError):
            self.ext.transition_policy(policy["id"], "approved", ADMIN)
        view = self.ext.get_policy(policy["id"], VIEWER)
        self.assertEqual(view["current_state"], "draft")
        self.assertEqual(view["transitions"], [])

    def test_attestation_status_derivation(self):
        policy = self._policy(expires_on="2026-06-30")
        self.ext.transition_policy(policy["id"], "in_review", ADMIN)
        self.ext.transition_policy(policy["id"], "approved", ADMIN)
        early = self.ext.get_policy(policy["id"], VIEWER, as_of="2026-06-15")
        self.assertEqual(early["attestation_status"], "unattested")
        late = self.ext.get_policy(policy["id"], VIEWER, as_of="2026-07-15")
        self.assertEqual(late["attestation_status"], "expired")
        self.ext.transition_policy(policy["id"], "attested", ADMIN)
        attested = self.ext.get_policy(policy["id"], VIEWER, as_of="2026-07-15")
        self.assertEqual(attested["attestation_status"], "attested")

    def test_attestation_record_verbatim_and_decides_nothing(self):
        policy = self._policy()
        record = self.ext.record_attestation(
            policy["id"], "attestor-9",
            "Attested with reservations (attestor wording)", ADMIN,
        )
        self.assertEqual(
            record["outcome"], "Attested with reservations (attestor wording)"
        )
        self.assertIs(record["decision_made"], False)
        view = self.ext.get_policy(policy["id"], VIEWER)
        self.assertEqual(view["current_state"], "draft")

    def test_policy_writes_are_admin_only(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_policy("x", MEMBER)
        self.assertIn("ext_policy_create:denied", audit_actions(self.audit))

    def test_policy_summary_counts(self):
        first = self._policy()
        self._policy()
        self.ext.transition_policy(first["id"], "in_review", ADMIN)
        summary = self.ext.policy_summary(VIEWER)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["by_current_state"],
                         {"draft": 1, "in_review": 1})


class TestFeedsReference(unittest.TestCase):
    """Entry: Continuous-monitoring feeds & scanner integrations —
    stub-engine, labeled reference (reference_stub +
    reference_transport on every record)."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def test_feed_labels(self):
        feed = self.ext.create_feed("FEED-1", "conmon feed", MEMBER)
        self.assertIs(feed["reference_stub"], True)
        self.assertIs(feed["reference_transport"], True)
        self.assertIs(feed["connected_here"], False)
        self.assertEqual(feed["state"], "recorded_reference_only")

    def test_receipt_totals_derived(self):
        self.ext.create_feed("FEED-1", "conmon feed", MEMBER)
        self.ext.record_feed_receipt("FEED-1", MEMBER, items_reported=12)
        receipt = self.ext.record_feed_receipt("FEED-1", MEMBER, items_reported=3)
        self.assertIs(receipt["ingested_here"], False)
        self.assertIs(receipt["reference_transport"], True)
        view = self.ext.get_feed("FEED-1", VIEWER)
        self.assertEqual(view["receipt_count"], 2)
        self.assertEqual(view["items_reported_total"], 15)

    def test_receipt_count_validation(self):
        self.ext.create_feed("FEED-1", "conmon feed", MEMBER)
        for bad in (-1, 1.5, True):
            with self.assertRaises(ValidationError):
                self.ext.record_feed_receipt("FEED-1", MEMBER, items_reported=bad)

    def test_feed_records_change_no_core_record(self):
        before = self.store.posture_summary(MEMBER)
        self.ext.create_feed("FEED-1", "conmon feed", MEMBER)
        self.ext.record_feed_receipt("FEED-1", MEMBER, items_reported=5)
        self.assertEqual(self.store.posture_summary(MEMBER), before)
        self.assertEqual(self.store.list_indicator_results(MEMBER), [])


class TestKsiValidationReference(unittest.TestCase):
    """Entry: Automated KSI validation — stub-engine, labeled
    reference: rules held as data, never evaluated; outcomes
    recorded verbatim as reported."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()
        self.ext.create_ksi_rule("KSI-RULE-1", "KSI-1", "all results pass", MEMBER)

    def test_rule_labels(self):
        rule = self.ext.get_ksi_rule("KSI-RULE-1", VIEWER)
        self.assertIs(rule["reference_stub"], True)
        self.assertIs(rule["evaluated_here"], False)
        self.assertEqual(rule["indicator_id"], "KSI-1")

    def test_rule_unknown_indicator(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_ksi_rule("KSI-RULE-2", "KSI-404", "text", MEMBER)

    def test_evaluation_outcome_verbatim(self):
        evaluation = self.ext.record_ksi_evaluation(
            "KSI-RULE-1", SYS, "pass (vendor wording)", MEMBER
        )
        self.assertEqual(evaluation["outcome"], "pass (vendor wording)")
        self.assertIs(evaluation["evaluated_here"], False)
        summary = self.ext.ksi_evaluation_summary(VIEWER)
        self.assertEqual(summary["by_outcome"], {"pass (vendor wording)": 1})

    def test_evaluation_changes_no_core_result(self):
        self.ext.record_ksi_evaluation("KSI-RULE-1", SYS, "pass", MEMBER)
        self.assertEqual(self.store.list_indicator_results(MEMBER), [])


class TestWorkflowExecutionReference(unittest.TestCase):
    """Entry: Agentic workflow execution — stub-engine, labeled
    reference: run and step records with reported statuses; nothing
    executes."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def test_run_labels_and_steps(self):
        run = self.ext.create_workflow_run(
            "WF-1", "ato workflow", MEMBER, system_ref=SYS
        )
        self.assertIs(run["reference_stub"], True)
        self.assertIs(run["executed"], False)
        step = self.ext.record_workflow_step(
            "WF-1", "collect evidence", "done (reported)", MEMBER
        )
        self.assertIs(step["executed_here"], False)
        view = self.ext.get_workflow_run("WF-1", VIEWER)
        self.assertEqual(view["step_count"], 1)
        self.assertEqual(view["steps"][0]["reported_status"], "done (reported)")

    def test_step_unknown_run(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_workflow_step("WF-404", "x", "done", MEMBER)

    def test_workflow_records_change_no_core_record(self):
        before = self.store.posture_summary(MEMBER)
        self.ext.create_workflow_run("WF-1", "w", MEMBER, system_ref=SYS)
        self.ext.record_workflow_step("WF-1", "s", "done", MEMBER)
        self.assertEqual(self.store.posture_summary(MEMBER), before)


class TestNarrativeGenerationReference(unittest.TestCase):
    """Entry: AI control-narrative & assessment-response generation
    — stub-engine, labeled reference: request records only; no text
    is generated."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def test_request_generates_nothing(self):
        request = self.ext.create_narrative_request(
            SYS, "control_narrative", MEMBER, control_ids=["IA-2"]
        )
        self.assertIs(request["reference_stub"], True)
        self.assertIs(request["generated_here"], False)
        self.assertIsNone(request["narrative_text"])

    def test_bad_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_narrative_request(SYS, "poetry", MEMBER)

    def test_outcome_recorded_verbatim(self):
        request = self.ext.create_narrative_request(
            SYS, "assessment_response", MEMBER
        )
        outcome = self.ext.record_narrative_outcome(
            request["id"], "draft produced externally", MEMBER
        )
        self.assertEqual(outcome["reported_outcome"], "draft produced externally")
        self.assertIs(outcome["generated_here"], False)
        view = self.ext.get_narrative_request(request["id"], VIEWER)
        self.assertEqual(len(view["outcomes"]), 1)
        self.assertIsNone(view["narrative_text"])


class TestConnectorReference(unittest.TestCase):
    """Entry: Data-integration connector engine — stub-engine,
    labeled reference (reference_stub + reference_transport); no
    data moves."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def test_connector_labels_and_totals(self):
        connector = self.ext.create_connector("CONN-1", "siem connector", MEMBER)
        self.assertIs(connector["reference_stub"], True)
        self.assertIs(connector["reference_transport"], True)
        self.assertIs(connector["connected_here"], False)
        run = self.ext.record_connector_run("CONN-1", MEMBER, records_reported=40)
        self.assertIs(run["moved_here"], False)
        self.ext.record_connector_run("CONN-1", MEMBER, records_reported=2)
        view = self.ext.get_connector("CONN-1", VIEWER)
        self.assertEqual(view["run_count"], 2)
        self.assertEqual(view["records_reported_total"], 42)

    def test_connector_run_count_validation(self):
        self.ext.create_connector("CONN-1", "c", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_connector_run("CONN-1", MEMBER, records_reported=True)


class TestForkExcessReference(unittest.TestCase):
    """Entry: Fork excess (healthcare quality suite; AI/ML
    governance evaluation engine; digital-twin OSCAL analysis
    engine; no-code BPM platform) — stub-engine, labeled reference
    profiles, one per kind."""

    KINDS = (
        "healthcare_quality",
        "ai_ml_governance_evaluation",
        "digital_twin_oscal_analysis",
        "no_code_bpm",
    )

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def test_all_four_kinds_labeled(self):
        for kind in self.KINDS:
            profile = self.ext.create_excess_profile(
                kind, kind + " profile", MEMBER, system_ref=SYS
            )
            self.assertIs(profile["reference_stub"], True)
            self.assertIs(profile["executed_here"], False)
            self.assertEqual(profile["kind"], kind)
        summary = self.ext.excess_summary(VIEWER)
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["by_kind"], {kind: 1 for kind in self.KINDS})

    def test_bad_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_excess_profile("something_else", "x", MEMBER)

    def test_outcome_verbatim_not_computed(self):
        profile = self.ext.create_excess_profile(
            "ai_ml_governance_evaluation", "ace profile", MEMBER
        )
        outcome = self.ext.record_excess_outcome(
            profile["id"], "claims gated (reported)", MEMBER
        )
        self.assertEqual(outcome["outcome_label"], "claims gated (reported)")
        self.assertIs(outcome["computed_here"], False)


def populate(ext, store):
    """Build one of everything on the extension surface."""
    run = ext.create_collection_run(
        "nightly sync", SYS, "telemetry export", MEMBER, control_ids=["IA-2"]
    )
    evidence = store.create_evidence(
        "config export", "payload", ["IA-2"], [SYS], ADMIN
    )
    review = ext.record_evidence_review(evidence["id"], "accepted", DANA)
    ext.create_scanner("SCAN-1", "scanner one", MEMBER)
    report = ext.record_scan_report(
        "SCAN-1", SYS, "2026-07-01T00:00:00Z", MEMBER,
        findings_reported=[
            {"title": "Old TLS", "severity": "Moderate-ish", "source": "SCAN-1",
             "due_date": "2026-06-30", "control_ids": ["IA-2"]},
        ],
    )
    rule = ext.create_scoring_rule("bands", "N1..N5", ADMIN)
    score = ext.record_reported_score(SYS, "N3", MEMBER)
    ext.create_enclave("ENC-1", "enclave one", MEMBER, system_refs=[SYS])
    ext.record_hosting_state("ENC-1", "operational (reported)", MEMBER)
    policy = ext.create_policy(
        "Access control policy", ADMIN, system_ref=SYS, framework_id=FW,
        expires_on="2026-06-30",
    )
    ext.transition_policy(policy["id"], "in_review", ADMIN)
    ext.transition_policy(policy["id"], "approved", ADMIN)
    ext.record_attestation(policy["id"], "attestor-9", "attested", ADMIN)
    package = ext.create_package(SYS, FW, MEMBER, as_of="2026-07-15")
    ext.create_feed("FEED-1", "conmon feed", MEMBER)
    ext.record_feed_receipt("FEED-1", MEMBER, items_reported=12)
    ext.create_ksi_rule("KSI-RULE-1", "KSI-1", "all results pass", MEMBER)
    ext.record_ksi_evaluation("KSI-RULE-1", SYS, "pass", MEMBER)
    ext.create_workflow_run("WF-1", "ato workflow", MEMBER, system_ref=SYS)
    ext.record_workflow_step("WF-1", "collect", "done (reported)", MEMBER)
    request = ext.create_narrative_request(
        SYS, "control_narrative", MEMBER, control_ids=["IA-2"]
    )
    ext.record_narrative_outcome(request["id"], "draft produced externally", MEMBER)
    ext.create_connector("CONN-1", "siem connector", MEMBER)
    ext.record_connector_run("CONN-1", MEMBER, records_reported=40)
    profiles = [
        ext.create_excess_profile(kind, kind, MEMBER, system_ref=SYS)
        for kind in TestForkExcessReference.KINDS
    ]
    ext.record_excess_outcome(profiles[0]["id"], "reported ok", MEMBER)
    return {
        "run": run, "review": review, "report": report, "rule": rule,
        "score": score, "policy": policy, "package": package,
        "request": request, "profiles": profiles,
    }


def all_surfaces(ext, store):
    """Every value the extension surface returns, plus core posture."""
    return [
        ext.list_collection_runs(VIEWER),
        ext.list_evidence_reviews(VIEWER),
        ext.evidence_review_summary(VIEWER),
        ext.list_scanners(VIEWER),
        ext.list_scan_reports(VIEWER),
        ext.scan_report_summary(VIEWER),
        ext.list_scoring_rules(VIEWER),
        ext.list_reported_scores(VIEWER),
        ext.reported_score_summary(VIEWER),
        ext.list_enclaves(VIEWER),
        ext.enclave_summary(VIEWER),
        ext.list_packages(VIEWER),
        ext.list_policies(VIEWER),
        ext.policy_summary(VIEWER),
        ext.list_feeds(VIEWER),
        ext.list_feed_receipts(VIEWER),
        ext.list_ksi_rules(VIEWER),
        ext.list_ksi_evaluations(VIEWER),
        ext.ksi_evaluation_summary(VIEWER),
        ext.list_workflow_runs(VIEWER),
        ext.list_workflow_steps(VIEWER),
        ext.list_narrative_requests(VIEWER),
        ext.list_connectors(VIEWER),
        ext.list_connector_runs(VIEWER),
        ext.list_excess_profiles(VIEWER),
        ext.excess_summary(VIEWER),
        store.posture_summary(VIEWER),
    ]


class TestExtensionInvariants(unittest.TestCase):
    """Cross-cutting: the no-score key scan and the tier-null key
    scan over the whole extension surface; stub labels; stub records
    changing no core record."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()
        populate(self.ext, self.store)

    def test_no_score_shaped_key_anywhere(self):
        for surface in all_surfaces(self.ext, self.store):
            for key in _all_keys(surface):
                self.assertFalse(
                    any(f in key.lower() for f in SCORE_FRAGMENTS),
                    "score-shaped key %r" % key,
                )

    def test_no_tier_shaped_key_anywhere(self):
        for surface in all_surfaces(self.ext, self.store):
            for key in _all_keys(surface):
                self.assertFalse(
                    any(f in key.lower() for f in TIER_FRAGMENTS),
                    "tier-shaped key %r" % key,
                )

    def test_every_stub_record_carries_reference_stub(self):
        stubs = [
            self.ext.get_feed("FEED-1", VIEWER),
            self.ext.get_ksi_rule("KSI-RULE-1", VIEWER),
            self.ext.get_workflow_run("WF-1", VIEWER),
            self.ext.list_narrative_requests(VIEWER)[0],
            self.ext.get_connector("CONN-1", VIEWER),
        ] + self.ext.list_excess_profiles(VIEWER)
        for record in stubs:
            self.assertIs(record["reference_stub"], True, record)
            self.assertEqual(record["state"], "recorded_reference_only", record)

    def test_transport_stubs_carry_reference_transport(self):
        self.assertIs(self.ext.get_feed("FEED-1", VIEWER)["reference_transport"], True)
        self.assertIs(
            self.ext.get_connector("CONN-1", VIEWER)["reference_transport"], True
        )
        self.assertIs(
            self.ext.list_collection_runs(VIEWER)[0]["reference_transport"], True
        )


class TestStubCreationsChangeNoCoreRecord(unittest.TestCase):
    """Every stub-engine surface is records-only: creating the full
    stub set changes no core record (core posture deep-equal)."""

    def test_stubs_change_nothing_in_core(self):
        ext, store, _audit = make_extensions()
        before = store.posture_summary(MEMBER)
        ext.create_feed("FEED-1", "feed", MEMBER)
        ext.record_feed_receipt("FEED-1", MEMBER, items_reported=3)
        ext.create_ksi_rule("KSI-RULE-1", "KSI-1", "text", MEMBER)
        ext.record_ksi_evaluation("KSI-RULE-1", SYS, "pass", MEMBER)
        ext.create_workflow_run("WF-1", "w", MEMBER, system_ref=SYS)
        ext.record_workflow_step("WF-1", "s", "done", MEMBER)
        request = ext.create_narrative_request(SYS, "control_narrative", MEMBER)
        ext.record_narrative_outcome(request["id"], "done externally", MEMBER)
        ext.create_connector("CONN-1", "c", MEMBER)
        ext.record_connector_run("CONN-1", MEMBER, records_reported=7)
        ext.create_excess_profile("no_code_bpm", "bpm", MEMBER, system_ref=SYS)
        self.assertEqual(store.posture_summary(MEMBER), before)
        self.assertEqual(store.list_findings(MEMBER), [])
        self.assertEqual(store.list_evidence(MEMBER), [])
        self.assertEqual(store.list_indicator_results(MEMBER), [])


def _mutant_reviewer_check(filed_by, reviewer):
    """The negative control's mutant: a separation-of-duties check
    whose guard never fires — any reviewer, including the filer, is
    waved through."""
    return True


class TestReviewerNotFilerNegativeControl(unittest.TestCase):
    """Fresh negative control for this unit's new code.

    Traced claim: a batch evidence review may never be recorded by
    the actor who filed the artifact — ``_check_reviewer_not_filer``
    is the single seam enforcing it behind
    ``GrcExtensions.record_evidence_review``. For the canonical pair
    (filer ``alice``, reviewer ``alice``) the test asserts the real
    seam raises, that the mutant (guard never fires) would wave the
    review through, and — via a literal ``assertRaises(
    AssertionError)`` — that treating the mutant's outcome as the
    expected outcome fails. An end-to-end arm repeats the separation
    through the extension surface: the filer's self-review is denied,
    consumes no review id, and another reviewer's review is
    ``evr-1``.
    """

    def test_real_guard_blocks_the_filer(self):
        with self.assertRaises(ValidationError):
            _check_reviewer_not_filer("alice", "alice")

    def test_real_guard_allows_another_reviewer(self):
        self.assertIsNone(_check_reviewer_not_filer("alice", "dana"))
        self.assertIsNone(_check_reviewer_not_filer("alice", "bob"))

    def test_mutant_waves_the_filer_through(self):
        self.assertTrue(_mutant_reviewer_check("alice", "alice"))

    def test_mutant_outcome_as_expectation_fails(self):
        with self.assertRaises(AssertionError):
            with self.assertRaises(ValidationError):
                _mutant_reviewer_check("alice", "alice")

    def test_end_to_end_self_review_denied_and_consumes_no_id(self):
        ext, store, _audit = make_extensions()
        evidence = store.create_evidence(
            "config export", "payload", ["IA-2"], [SYS], ADMIN
        )
        with self.assertRaises(ValidationError):
            ext.record_evidence_review(evidence["id"], "accepted", ADMIN)
        self.assertEqual(ext.list_evidence_reviews(VIEWER), [])
        review = ext.record_evidence_review(evidence["id"], "accepted", DANA)
        self.assertEqual(review["id"], "evr-1")


if __name__ == "__main__":
    unittest.main()
