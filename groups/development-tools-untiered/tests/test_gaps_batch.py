"""Final GAPS batch — Untiered Set 6 (Development Tools, tier null).

Traces to: the 7 open entries of the GAPS.md section "Untiered
Set 6 — Development Tools (7 forks, tier null)" (inventory idx
796–802) and ``BATCH.md`` in the group directory for the
per-entry disposition.

Pins: the extension surface per entry (idx 796 AI engines —
reference form after re-judgment; idx 797 workspaces; idx 798
conversion jobs; idx 799 governance gating; idx 800 detection —
reference as drafted; idx 801 governance configuration records;
idx 802 support cases); the honesty labels on every family
(``reference_stub`` / ``reference_transport`` / the ``*_here:
False`` set); derived-never-stored state (conversion stage
status, promotion state, support case state); validation before
mutation (failed operations consume no id); RBAC parity with the
core (denied attempts audited ``<action>:denied``); extension
writes changing no core record; and the TIER-NULL scan — no
extension record or derived view carries a tier, baseline, or
impact-level key, the extension-surface counterpart of
``test_specs.py``'s sheet pins.

The negative control is the conversion stage derivation seam
(:meth:`DevToolsExtensions._derive_conversion_stage`): the
latest recorded outcome decides a stage's current reported
status. The mutant derives from the earliest outcome instead.
"""

import hashlib
import unittest

from devtools_helpers import ADMIN, DEVELOPER, VIEWER, fresh_store

from devtools.errors import NotFoundError, PermissionDenied, ValidationError
from devtools.extensions import DevToolsExtensions

DIGEST = hashlib.sha256(b"legacy-source").hexdigest()

BANNED_TIER_KEYS = {
    "tier", "cmmc_tier", "baseline", "fedramp_baseline",
    "fedramp_impact_level", "impact_level",
}


def make_ext():
    """Fresh store + one core project + the extension surface."""
    store = fresh_store()
    project = store.create_project("Widget Service", ADMIN)
    return store, project, DevToolsExtensions(store)


def walk_keys(value):
    """Every dict key in a nested record/view structure."""
    keys = set()
    if isinstance(value, dict):
        for key, sub in value.items():
            keys.add(key)
            keys |= walk_keys(sub)
    elif isinstance(value, list):
        for item in value:
            keys |= walk_keys(item)
    return keys


class TestAIReferenceRecords(unittest.TestCase):
    """idx 796 — AI code-generation & AI-agent development engines
    (reference form; re-judged, see BATCH.md)."""

    def test_request_shape_and_labels(self):
        _, project, ext = make_ext()
        rec = ext.record_ai_request(
            project["id"], "code_generation", "req://gen-1", DEVELOPER,
            model_ref="model://codegen",
        )
        self.assertEqual(rec["id"], "air-1")
        self.assertEqual(rec["kind"], "code_generation")
        self.assertIs(rec["reference_stub"], True)
        self.assertEqual(rec["status"], "recorded_reference_only")
        self.assertIs(rec["inference_here"], False)
        self.assertIs(rec["generated_here"], False)
        self.assertIs(rec["agent_executed_here"], False)

    def test_outcome_verbatim_and_view_derives_latest(self):
        _, project, ext = make_ext()
        req = ext.record_ai_request(
            project["id"], "agent_task", "req://agent-1", DEVELOPER)
        ext.record_ai_outcome(req["id"], "reported_running", DEVELOPER)
        ext.record_ai_outcome(
            req["id"], "reported_completed", DEVELOPER,
            result_ref="artifact://out-1")
        view = ext.ai_request_view(req["id"])
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["current_outcome_label"], "reported_completed")
        self.assertEqual(view["outcomes"][1]["result_ref"], "artifact://out-1")
        self.assertIs(view["outcomes"][1]["generated_here"], False)
        # The stored request record carries no outcome field.
        stored = ext.get_ai_request(req["id"])
        self.assertNotIn("outcome_label", stored)
        self.assertNotIn("current_outcome_label", stored)

    def test_bad_kind_rejected_no_id_consumed(self):
        _, project, ext = make_ext()
        with self.assertRaises(ValidationError):
            ext.record_ai_request(
                project["id"], "teleportation", "req://x", DEVELOPER)
        rec = ext.record_ai_request(
            project["id"], "code_generation", "req://ok", DEVELOPER)
        self.assertEqual(rec["id"], "air-1")

    def test_unknown_project_not_found(self):
        _, _, ext = make_ext()
        with self.assertRaises(NotFoundError):
            ext.record_ai_request(
                "prj-999", "code_generation", "req://x", DEVELOPER)

    def test_viewer_write_denied_and_audited(self):
        store, project, ext = make_ext()
        with self.assertRaises(PermissionDenied):
            ext.record_ai_request(
                project["id"], "code_generation", "req://x", VIEWER)
        actions = [e["action"] for e in store.audit.entries()]
        self.assertIn("project_write:denied", actions)


class TestWorkspaces(unittest.TestCase):
    """idx 797 — Cloud development environments (hosted IDE workspaces)."""

    def test_workspace_shape_and_labels(self):
        _, project, ext = make_ext()
        ws = ext.create_workspace(project["id"], "Dev Box", DEVELOPER)
        self.assertEqual(ws["id"], "wsp-1")
        self.assertEqual(ws["access_modes"], ["browser"])
        self.assertIs(ws["hosted_here"], False)
        self.assertIs(ws["provisioned_here"], False)
        self.assertIs(ws["filesystem_held_here"], False)
        ws2 = ext.create_workspace(
            project["id"], "Pair Box", DEVELOPER,
            access_modes=["browser", "ssh", "browser"])
        self.assertEqual(ws2["access_modes"], ["browser", "ssh"])

    def test_sessions_and_view_derives_latest(self):
        _, project, ext = make_ext()
        ws = ext.create_workspace(project["id"], "Dev Box", DEVELOPER)
        ext.record_workspace_session(ws["id"], "dev://bob", "reported_active",
                                     DEVELOPER)
        ext.record_workspace_session(ws["id"], "dev://bob", "reported_idle",
                                     DEVELOPER)
        ext.record_workspace_session(ws["id"], "dev://amy", "reported_active",
                                     DEVELOPER)
        view = ext.workspace_view(ws["id"])
        self.assertEqual(view["session_count"], 3)
        self.assertEqual(view["sessions_by_reported_status"],
                         {"reported_active": 2, "reported_idle": 1})
        self.assertEqual(view["latest_reported_status"], "reported_active")
        # The stored workspace record carries no status field.
        self.assertNotIn("status", ext.get_workspace(ws["id"]))

    def test_bad_access_mode_and_bad_status_rejected(self):
        _, project, ext = make_ext()
        with self.assertRaises(ValidationError):
            ext.create_workspace(project["id"], "Box", DEVELOPER,
                                 access_modes=["telepathy"])
        ws = ext.create_workspace(project["id"], "Box", DEVELOPER)
        with self.assertRaises(ValidationError):
            ext.record_workspace_session(ws["id"], "dev://bob", "busy",
                                         DEVELOPER)

    def test_session_unknown_workspace_not_found(self):
        _, _, ext = make_ext()
        with self.assertRaises(NotFoundError):
            ext.record_workspace_session("wsp-999", "dev://bob",
                                         "reported_active", DEVELOPER)


class TestConversionJobs(unittest.TestCase):
    """idx 798 — Legacy modernization & code-conversion engines."""

    def test_job_shape_stages_and_labels(self):
        _, project, ext = make_ext()
        job = ext.create_conversion_job(
            project["id"], "COBOL to Python", "src://legacy", DEVELOPER,
            target_ref="tgt://modern", source_digest=DIGEST)
        self.assertEqual(job["id"], "cnv-1")
        self.assertEqual(job["stages"],
                         ["blueprint", "contract", "code", "testing",
                          "deploy"])
        self.assertEqual(job["source_digest"], DIGEST)
        self.assertIs(job["converted_here"], False)
        self.assertIs(job["code_held_here"], False)
        self.assertNotIn("status", job)

    def test_job_view_derives_latest_stage_status(self):
        _, project, ext = make_ext()
        job = ext.create_conversion_job(
            project["id"], "Conv", "src://legacy", DEVELOPER)
        ext.record_conversion_stage(job["id"], "blueprint",
                                    "reported_in_progress", DEVELOPER)
        ext.record_conversion_stage(job["id"], "blueprint",
                                    "reported_completed", DEVELOPER)
        view = ext.conversion_job_view(job["id"])
        self.assertEqual(view["stages"]["blueprint"], "reported_completed")
        self.assertIsNone(view["stages"]["contract"])
        self.assertEqual(view["overall"], "in_progress")

    def test_view_overall_completed_and_failed(self):
        _, project, ext = make_ext()
        job = ext.create_conversion_job(
            project["id"], "Conv", "src://legacy", DEVELOPER)
        for stage in job["stages"]:
            ext.record_conversion_stage(job["id"], stage,
                                        "reported_completed", DEVELOPER)
        self.assertEqual(
            ext.conversion_job_view(job["id"])["overall"], "completed")
        job2 = ext.create_conversion_job(
            project["id"], "Conv 2", "src://legacy2", DEVELOPER)
        ext.record_conversion_stage(job2["id"], "code", "reported_failed",
                                    DEVELOPER)
        self.assertEqual(
            ext.conversion_job_view(job2["id"])["overall"], "failed")

    def test_unknown_stage_and_bad_status_rejected_no_id(self):
        _, project, ext = make_ext()
        job = ext.create_conversion_job(
            project["id"], "Conv", "src://legacy", DEVELOPER)
        with self.assertRaises(ValidationError):
            ext.record_conversion_stage(job["id"], "polish",
                                        "reported_completed", DEVELOPER)
        with self.assertRaises(ValidationError):
            ext.record_conversion_stage(job["id"], "code", "done",
                                        DEVELOPER)
        rec = ext.record_conversion_stage(job["id"], "code",
                                          "reported_completed", DEVELOPER)
        self.assertEqual(rec["id"], "cns-1")

    def test_bad_digest_rejected(self):
        _, project, ext = make_ext()
        with self.assertRaises(ValidationError):
            ext.create_conversion_job(
                project["id"], "Conv", "src://legacy", DEVELOPER,
                source_digest="not-a-digest")
        with self.assertRaises(ValidationError):
            ext.create_conversion_job(
                project["id"], "Conv", "src://legacy", DEVELOPER,
                target_digest=DIGEST.upper())


class TestGovernanceGating(unittest.TestCase):
    """idx 799 — CI/CD governance & promotion-gating engines."""

    def test_gate_check_binds_core_subject_and_changes_nothing(self):
        store, project, ext = make_ext()
        build = store.record_build(project["id"], DEVELOPER, ref="main")
        before = store.get_build(build["id"])
        check = ext.record_gate_check(
            project["id"], "pull_request", DEVELOPER,
            outcome_label="reported_passed", subject_build_id=build["id"])
        self.assertEqual(check["id"], "gtc-1")
        self.assertIs(check["gated_here"], False)
        self.assertIs(check["enforced_here"], False)
        self.assertEqual(store.get_build(build["id"]), before)

    def test_gate_check_cross_project_subject_rejected(self):
        store, project, ext = make_ext()
        other = store.create_project("Other Service", ADMIN)
        build = store.record_build(other["id"], DEVELOPER, ref="main")
        with self.assertRaises(ValidationError):
            ext.record_gate_check(
                project["id"], "coverage", DEVELOPER,
                subject_build_id=build["id"])

    def test_gate_check_two_subjects_rejected(self):
        store, project, ext = make_ext()
        build = store.record_build(project["id"], DEVELOPER, ref="main")
        review = store.create_review(project["id"], "Review", DEVELOPER)
        with self.assertRaises(ValidationError):
            ext.record_gate_check(
                project["id"], "approval", DEVELOPER,
                subject_build_id=build["id"],
                subject_review_id=review["id"])

    def test_promotion_view_derives_latest_outcome(self):
        store, project, ext = make_ext()
        env_a = store.create_environment("Dev", DEVELOPER)
        env_b = store.create_environment("Prod", DEVELOPER)
        promo = ext.record_promotion(
            project["id"], env_a["id"], env_b["id"], DEVELOPER)
        self.assertIs(promo["promoted_here"], False)
        self.assertNotIn("status", promo)
        self.assertEqual(
            ext.promotion_view(promo["id"])["current_state"], "recorded")
        ext.record_promotion_outcome(promo["id"], "reported_mismatch",
                                     DEVELOPER)
        ext.record_promotion_outcome(promo["id"], "reported_promoted",
                                     DEVELOPER)
        view = ext.promotion_view(promo["id"])
        self.assertEqual(view["current_state"], "reported_promoted")
        self.assertEqual(view["outcome_count"], 2)

    def test_promotion_same_environment_rejected(self):
        store, project, ext = make_ext()
        env_a = store.create_environment("Dev", DEVELOPER)
        with self.assertRaises(ValidationError):
            ext.record_promotion(
                project["id"], env_a["id"], env_a["id"], DEVELOPER)


class TestGovernancePolicies(unittest.TestCase):
    """idx 801 — Pipeline governance configuration records."""

    RULES = [
        {"rule_ref": "rule://pr-gate", "kind": "gate",
         "requirement": "pull requests require two approvals"},
        {"rule_ref": "rule://coverage", "kind": "coverage",
         "requirement": "coverage threshold applies at promotion"},
    ]

    def test_policy_shape_rules_as_data(self):
        _, project, ext = make_ext()
        policy = ext.create_governance_policy(
            project["id"], "Delivery Governance", self.RULES, DEVELOPER,
            promotion_sequence=["Dev", "Test", "Stage", "Prod"],
            coverage_threshold=80)
        self.assertEqual(policy["id"], "gov-1")
        self.assertEqual(policy["rules"], self.RULES)
        self.assertEqual(policy["promotion_sequence"],
                         ["Dev", "Test", "Stage", "Prod"])
        self.assertEqual(policy["coverage_threshold"], 80)
        self.assertIs(policy["enforced_here"], False)
        self.assertIs(policy["executed_here"], False)

    def test_policy_validation(self):
        _, project, ext = make_ext()
        with self.assertRaises(ValidationError):
            ext.create_governance_policy(
                project["id"], "P", [{"rule_ref": "r", "kind": "magic",
                                      "requirement": "x"}], DEVELOPER)
        with self.assertRaises(ValidationError):
            ext.create_governance_policy(
                project["id"], "P", self.RULES + self.RULES[:1], DEVELOPER)
        with self.assertRaises(ValidationError):
            ext.create_governance_policy(
                project["id"], "P", self.RULES, DEVELOPER,
                coverage_threshold=101)
        with self.assertRaises(ValidationError):
            ext.create_governance_policy(
                project["id"], "P", self.RULES, DEVELOPER,
                promotion_sequence=["Dev", "Dev"])
        policy = ext.create_governance_policy(
            project["id"], "P", self.RULES, DEVELOPER)
        self.assertEqual(policy["id"], "gov-1")

    def test_gate_check_rejects_policy_of_other_project(self):
        store, project, ext = make_ext()
        other = store.create_project("Other Service", ADMIN)
        policy = ext.create_governance_policy(
            other["id"], "Theirs", self.RULES, DEVELOPER)
        with self.assertRaises(ValidationError):
            ext.record_gate_check(
                project["id"], "promotion", DEVELOPER,
                policy_id=policy["id"])


class TestDetectionReference(unittest.TestCase):
    """idx 800 — Secrets & sensitive-data detection engines (reference)."""

    def test_scan_shape_and_stub_labels(self):
        _, project, ext = make_ext()
        scan = ext.record_detection_scan(
            project["id"], "scan://run-1", DEVELOPER,
            target_ref="repo://widget")
        self.assertEqual(scan["id"], "ref-1")
        self.assertEqual(scan["kind"], "detection_scan")
        self.assertIs(scan["reference_stub"], True)
        self.assertEqual(scan["status"], "recorded_reference_only")
        self.assertIs(scan["scanned_here"], False)
        self.assertIs(scan["detected_here"], False)

    def test_findings_reported_verbatim(self):
        _, project, ext = make_ext()
        scan = ext.record_detection_scan(
            project["id"], "scan://run-1", DEVELOPER)
        finding = ext.record_detection_finding(
            scan["id"], "credential", "src://config.py:14", DEVELOPER,
            severity_label="reported_high")
        self.assertEqual(finding["id"], "dtf-1")
        self.assertEqual(finding["severity_label"], "reported_high")
        self.assertIs(finding["reference_stub"], True)
        self.assertIs(finding["detected_here"], False)
        findings = ext.list_detection_findings(scan_id=scan["id"])
        self.assertEqual(len(findings), 1)

    def test_bad_finding_kind_rejected_no_id(self):
        _, project, ext = make_ext()
        scan = ext.record_detection_scan(
            project["id"], "scan://run-1", DEVELOPER)
        with self.assertRaises(ValidationError):
            ext.record_detection_finding(
                scan["id"], "vibe", "src://x", DEVELOPER)
        finding = ext.record_detection_finding(
            scan["id"], "secret", "src://x", DEVELOPER)
        self.assertEqual(finding["id"], "dtf-1")

    def test_finding_unknown_scan_not_found(self):
        _, _, ext = make_ext()
        with self.assertRaises(NotFoundError):
            ext.record_detection_finding(
                "ref-999", "secret", "src://x", DEVELOPER)


class TestSupportCases(unittest.TestCase):
    """idx 802 — Fork excess: customer support platform."""

    def test_case_shape_labels_no_status(self):
        _, project, ext = make_ext()
        case = ext.create_support_case(
            project["id"], "in_app_chat", DEVELOPER,
            subject_ref="user://requester-1")
        self.assertEqual(case["id"], "sup-1")
        self.assertIs(case["reference_transport"], True)
        self.assertIs(case["messages_held_here"], False)
        self.assertIs(case["delivered_here"], False)
        self.assertNotIn("status", case)
        self.assertNotIn("message", case)

    def test_case_view_derives_state_from_events(self):
        _, project, ext = make_ext()
        case = ext.create_support_case(
            project["id"], "support_email", DEVELOPER)
        self.assertEqual(
            ext.support_case_view(case["id"])["current_state"], "opened")
        ext.record_support_event(case["id"], "responded", DEVELOPER)
        ext.record_support_event(case["id"], "resolved", DEVELOPER)
        view = ext.support_case_view(case["id"])
        self.assertEqual(view["current_state"], "resolved")
        self.assertEqual(view["event_count"], 2)

    def test_bad_channel_and_bad_event_rejected(self):
        _, project, ext = make_ext()
        with self.assertRaises(ValidationError):
            ext.create_support_case(project["id"], "carrier_pigeon",
                                    DEVELOPER)
        case = ext.create_support_case(
            project["id"], "support_phone", DEVELOPER)
        with self.assertRaises(ValidationError):
            ext.record_support_event(case["id"], "shouted", DEVELOPER)


class TestTierNullAndCrossCutting(unittest.TestCase):
    """Tier-null scan + cross-cutting batch invariants."""

    def _populate(self, store, project, ext):
        req = ext.record_ai_request(
            project["id"], "code_generation", "req://1", DEVELOPER)
        outcome = ext.record_ai_outcome(req["id"], "reported_completed",
                                        DEVELOPER, result_ref="out://1")
        ws = ext.create_workspace(project["id"], "Box", DEVELOPER,
                                  access_modes=["browser", "ssh"])
        session = ext.record_workspace_session(
            ws["id"], "dev://bob", "reported_active", DEVELOPER)
        job = ext.create_conversion_job(
            project["id"], "Conv", "src://legacy", DEVELOPER,
            source_digest=DIGEST)
        stage = ext.record_conversion_stage(
            job["id"], "code", "reported_completed", DEVELOPER)
        policy = ext.create_governance_policy(
            project["id"], "Gov", TestGovernancePolicies.RULES, DEVELOPER,
            promotion_sequence=["Dev", "Prod"], coverage_threshold=75)
        check = ext.record_gate_check(
            project["id"], "promotion", DEVELOPER,
            outcome_label="reported_passed", policy_id=policy["id"])
        env_a = store.create_environment("Dev", DEVELOPER)
        env_b = store.create_environment("Prod", DEVELOPER)
        promo = ext.record_promotion(
            project["id"], env_a["id"], env_b["id"], DEVELOPER,
            policy_id=policy["id"])
        pout = ext.record_promotion_outcome(promo["id"], "reported_promoted",
                                            DEVELOPER)
        scan = ext.record_detection_scan(
            project["id"], "scan://1", DEVELOPER)
        finding = ext.record_detection_finding(
            scan["id"], "token", "src://a.py:3", DEVELOPER)
        case = ext.create_support_case(
            project["id"], "support_ticket", DEVELOPER)
        event = ext.record_support_event(case["id"], "responded", DEVELOPER)
        surface = [
            req, outcome, ext.ai_request_view(req["id"]),
            ws, session, ext.workspace_view(ws["id"]),
            job, stage, ext.conversion_job_view(job["id"]),
            policy, check, promo, pout, ext.promotion_view(promo["id"]),
            scan, finding,
            case, event, ext.support_case_view(case["id"]),
        ]
        return surface

    def test_tier_null_scan_over_extension_surface(self):
        store, project, ext = make_ext()
        surface = self._populate(store, project, ext)
        for item in surface:
            keys = {k.lower() for k in walk_keys(item)}
            self.assertEqual(keys & BANNED_TIER_KEYS, set(),
                             "tier-shaped key in %r" % (item,))

    def test_extension_writes_change_no_core_records(self):
        store, project, ext = make_ext()
        store.create_issue(project["id"], "Seed issue", DEVELOPER)

        def counts():
            return {
                "projects": len(store.list_projects()),
                "issues": len(store.list_issues()),
                "reviews": len(store.list_reviews()),
                "builds": len(store.list_builds()),
                "releases": len(store.list_releases()),
                "artifacts": len(store.list_artifacts()),
                "environments": len(store.list_environments()),
                "deployments": len(store.list_deployments()),
            }

        before = counts()
        self._populate(store, project, ext)
        # The populate helper itself creates two core environments
        # (promotion endpoints are core records by design).
        after = counts()
        expected = dict(before)
        expected["environments"] = before["environments"] + 2
        self.assertEqual(after, expected)

    def test_failed_operations_consume_no_ids(self):
        _, project, ext = make_ext()
        with self.assertRaises(ValidationError):
            ext.create_workspace(project["id"], "Box", DEVELOPER,
                                 access_modes=["nope"])
        with self.assertRaises(ValidationError):
            ext.create_support_case(project["id"], "smoke_signal",
                                    DEVELOPER)
        ws = ext.create_workspace(project["id"], "Box", DEVELOPER)
        case = ext.create_support_case(
            project["id"], "support_ticket", DEVELOPER)
        self.assertEqual(ws["id"], "wsp-1")
        self.assertEqual(case["id"], "sup-1")


class EarliestOutcomeMutantExtensions(DevToolsExtensions):
    """Mutant: stage derivation reads the EARLIEST outcome."""

    @staticmethod
    def _derive_conversion_stage(outcomes):
        if not outcomes:
            return None
        return outcomes[0]["status_label"]


class TestNegativeControlConversionDerivation(unittest.TestCase):
    """Negative control: the latest recorded outcome decides.

    Traced claim: a conversion stage's current reported status
    is its LATEST recorded outcome — after ``reported_in_progress``
    then ``reported_completed``, the stage reads
    ``reported_completed``.
    """

    def _scenario(self, ext, project):
        job = ext.create_conversion_job(
            project["id"], "Conv", "src://legacy", DEVELOPER)
        ext.record_conversion_stage(job["id"], "blueprint",
                                    "reported_in_progress", DEVELOPER)
        ext.record_conversion_stage(job["id"], "blueprint",
                                    "reported_completed", DEVELOPER)
        return ext.conversion_job_view(job["id"])["stages"]["blueprint"]

    def test_control_passes(self):
        _, project, ext = make_ext()
        self.assertEqual(
            self._scenario(ext, project), "reported_completed")

    def test_earliest_outcome_mutant_is_rejected(self):
        store, project, ext = make_ext()
        canonical = self._scenario(ext, project)
        self.assertEqual(canonical, "reported_completed")
        mutant = EarliestOutcomeMutantExtensions(store)
        mutant_outcome = self._scenario(mutant, project)
        self.assertEqual(mutant_outcome, "reported_in_progress")
        self.assertNotEqual(mutant_outcome, canonical)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, canonical)


if __name__ == "__main__":
    unittest.main()
