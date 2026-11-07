"""Tests for the final GAPS batch extensions (Group 29 unit).

Pins the extension surface per GAPS entry: pipeline definitions
and reported run records (idx 303), toolchain registry records
(305), artifact storage backends as records + checksums (311),
the feature-flag evaluation derivation incl. the kill switch
(312), experiment assignment / outcome records and exact-count
summaries (313), static-analysis rule sets, quality profiles,
reported results, and gate derivations (314), release plans,
stage records, migration records, and the derived plan view
(316), and the eight labeled reference implementations
(304, 306, 307, 308, 309, 310, 315, 317).

The fresh negative control lives in
:class:`FlagKillSwitchNegativeControlTests`: a subclass that
breaks the kill-switch seam must not satisfy the canonical
expectation that a killed flag serves no subject.
"""

import hashlib
import unittest

from devtools.audit import AuditLog
from devtools.errors import NotFoundError, PermissionDenied, ValidationError
from devtools.extensions import DevToolsExtensions

from devtools_helpers import ADMIN, DEVELOPER, VIEWER, make_store


def make_extensions(audit=None):
    store, project = make_store(audit=audit)
    return DevToolsExtensions(store), store, project


def bucket_of(scope_id, subject_ref):
    """Independent recomputation of the stated bucketing rule."""
    digest = hashlib.sha256(
        ("%s:%s" % (scope_id, subject_ref)).encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16) % 100


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.project = make_extensions()
        self.pid = self.project["id"]

    def test_define_pipeline_shape(self):
        pipeline = self.ext.define_pipeline(
            self.pid, "Main pipeline", ADMIN,
            stages=[{"name": "compile", "kind": "build"},
                    {"name": "tests", "kind": "test"},
                    "ship"],
        )
        self.assertTrue(pipeline["id"].startswith("pip-"))
        self.assertIs(pipeline["executed_here"], False)
        self.assertEqual(
            pipeline["stages"],
            [{"name": "compile", "kind": "build"},
             {"name": "tests", "kind": "test"},
             {"name": "ship", "kind": "custom"}],
        )

    def test_pipeline_stage_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.define_pipeline(self.pid, "Empty", ADMIN, stages=[])
        with self.assertRaises(ValidationError):
            self.ext.define_pipeline(
                self.pid, "BadKind", ADMIN,
                stages=[{"name": "x", "kind": "quantum"}],
            )
        with self.assertRaises(ValidationError):
            self.ext.define_pipeline(
                self.pid, "Dup", ADMIN, stages=["a", "a"],
            )
        with self.assertRaises(NotFoundError):
            self.ext.define_pipeline("prj-404", "Nope", ADMIN, stages=["a"])

    def test_run_records_are_reported_not_executed(self):
        pipeline = self.ext.define_pipeline(
            self.pid, "CI", ADMIN, stages=["build"],
        )
        run = self.ext.record_pipeline_run(
            pipeline["id"], DEVELOPER, status="failed",
            runner_ref="runner://ext-1",
        )
        self.assertEqual(run["status"], "failed")
        self.assertIs(run["executed_here"], False)
        self.assertEqual(run["runner_ref"], "runner://ext-1")
        # Recording runs creates no core build records.
        self.assertEqual(self.store._builds, {})
        with self.assertRaises(ValidationError):
            self.ext.record_pipeline_run(
                pipeline["id"], DEVELOPER, status="exploded",
            )
        with self.assertRaises(NotFoundError):
            self.ext.record_pipeline_run(
                pipeline["id"], DEVELOPER, build_id="bld-404",
            )

    def test_run_can_bind_core_build(self):
        build = self.store.record_build(self.pid, DEVELOPER, ref="main")
        pipeline = self.ext.define_pipeline(
            self.pid, "CI", ADMIN, stages=["build"],
        )
        run = self.ext.record_pipeline_run(
            pipeline["id"], DEVELOPER, build_id=build["id"],
        )
        self.assertEqual(run["build_id"], build["id"])


class ToolchainTests(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.project = make_extensions()
        self.pid = self.project["id"]

    def test_register_toolchain(self):
        toolchain = self.ext.register_toolchain(
            self.pid, "Rust stable", ADMIN,
            language="rust", version_label="1.81",
        )
        self.assertTrue(toolchain["id"].startswith("tch-"))
        self.assertIs(toolchain["executed_here"], False)
        self.assertEqual(toolchain["language"], "rust")
        self.assertEqual(len(self.ext.list_toolchains(self.pid)), 1)

    def test_toolchain_unknown_project(self):
        with self.assertRaises(NotFoundError):
            self.ext.register_toolchain("prj-404", "Ghost", ADMIN)


class StorageBackendTests(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.project = make_extensions()
        self.pid = self.project["id"]

    def test_backend_and_placement_copy_checksum_only(self):
        artifact = self.store.register_artifact(
            self.pid, "app.tgz", ADMIN, content=b"payload-bytes",
        )
        backend = self.ext.register_storage_backend(
            "Primary vault", ADMIN, kind="object_store",
        )
        placement = self.ext.place_artifact(artifact["id"], backend["id"], ADMIN)
        self.assertEqual(placement["sha256"], artifact["sha256"])
        self.assertEqual(placement["size_bytes"], len(b"payload-bytes"))
        self.assertIs(placement["stored_here"], False)
        # No content key anywhere on the placement record.
        self.assertNotIn("content", placement)
        self.assertIs(backend["stored_here"], False)

    def test_placement_unknowns(self):
        backend = self.ext.register_storage_backend("Vault", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.place_artifact("art-404", backend["id"], ADMIN)
        artifact = self.store.register_artifact(
            self.pid, "a.bin", ADMIN, checksum="a" * 64,
        )
        with self.assertRaises(NotFoundError):
            self.ext.place_artifact(artifact["id"], "stb-404", ADMIN)

    def test_backend_summary_derivation(self):
        sized = self.store.register_artifact(
            self.pid, "sized.bin", ADMIN, content=b"12345",
        )
        unsized = self.store.register_artifact(
            self.pid, "checksum-only.bin", ADMIN, checksum="b" * 64,
        )
        backend = self.ext.register_storage_backend("Vault", ADMIN)
        self.ext.place_artifact(sized["id"], backend["id"], ADMIN)
        self.ext.place_artifact(unsized["id"], backend["id"], ADMIN)
        summary = self.ext.storage_backend_summary(backend["id"])
        self.assertEqual(summary["placements"], 2)
        self.assertEqual(summary["total_size_bytes"], 5)
        self.assertEqual(summary["unknown_size_count"], 1)
        # Derivation is not stored on the backend record.
        self.assertNotIn("placements", self.ext.get_storage_backend(backend["id"]))

    def test_backend_kind_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.register_storage_backend("Bad", ADMIN, kind="tape-magic")


class FeatureFlagTests(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.project = make_extensions()
        self.pid = self.project["id"]
        self.flag = self.ext.create_flag(self.pid, "new-checkout", ADMIN)
        self.fid = self.flag["id"]

    def test_flag_defaults_serve_nothing(self):
        result = self.ext.evaluate_flag(self.fid, "subject://a")
        self.assertIs(result["served"], False)
        self.assertEqual(result["reason"], "rollout_miss")

    def test_flag_key_unique_per_project(self):
        with self.assertRaises(ValidationError):
            self.ext.create_flag(self.pid, "new-checkout", ADMIN)
        other = self.store.create_project("Other Service", ADMIN)
        flag = self.ext.create_flag(other["id"], "new-checkout", ADMIN)
        self.assertNotEqual(flag["id"], self.fid)

    def test_rollout_zero_and_hundred(self):
        subject = "subject://rollout"
        self.ext.set_flag_rollout(self.fid, 0, ADMIN)
        self.assertIs(self.ext.evaluate_flag(self.fid, subject)["served"], False)
        self.ext.set_flag_rollout(self.fid, 100, ADMIN)
        result = self.ext.evaluate_flag(self.fid, subject)
        self.assertIs(result["served"], True)
        self.assertEqual(result["reason"], "rollout")

    def test_rollout_percentage_validation(self):
        for bad in (True, -1, 101, 12.5, "50"):
            with self.assertRaises(ValidationError):
                self.ext.set_flag_rollout(self.fid, bad, ADMIN)

    def test_bucket_matches_stated_rule_and_is_deterministic(self):
        subject = "subject://deterministic"
        expected = bucket_of(self.fid, subject)
        first = self.ext.evaluate_flag(self.fid, subject)
        second = self.ext.evaluate_flag(self.fid, subject)
        self.assertEqual(first, second)
        self.assertEqual(first["bucket"], expected)
        self.assertTrue(0 <= first["bucket"] <= 99)
        self.assertEqual(
            first["method"], "sha256_bucket_over_flag_and_subject",
        )

    def test_rollout_boundary_is_bucket_below_percentage(self):
        subject = "subject://boundary"
        bucket = bucket_of(self.fid, subject)
        self.ext.set_flag_rollout(self.fid, bucket, ADMIN)
        self.assertIs(self.ext.evaluate_flag(self.fid, subject)["served"], False)
        self.ext.set_flag_rollout(self.fid, bucket + 1, ADMIN)
        self.assertIs(self.ext.evaluate_flag(self.fid, subject)["served"], True)

    def test_targeting_overrides_rollout_miss(self):
        self.ext.set_flag_rollout(self.fid, 0, ADMIN)
        self.ext.set_flag_targeting(self.fid, ["subject://vip"], ADMIN)
        result = self.ext.evaluate_flag(self.fid, "subject://vip")
        self.assertIs(result["served"], True)
        self.assertEqual(result["reason"], "targeted")
        other = self.ext.evaluate_flag(self.fid, "subject://other")
        self.assertIs(other["served"], False)

    def test_disabled_flag_serves_nothing(self):
        self.ext.set_flag_rollout(self.fid, 100, ADMIN)
        self.ext.set_flag_enabled(self.fid, False, ADMIN)
        result = self.ext.evaluate_flag(self.fid, "subject://a")
        self.assertIs(result["served"], False)
        self.assertEqual(result["reason"], "flag_disabled")
        with self.assertRaises(ValidationError):
            self.ext.set_flag_enabled(self.fid, "yes", ADMIN)

    def test_kill_switch_and_restore(self):
        self.ext.set_flag_rollout(self.fid, 100, ADMIN)
        self.ext.set_flag_targeting(self.fid, ["subject://vip"], ADMIN)
        killed = self.ext.kill_flag(self.fid, ADMIN)
        self.assertIs(killed["killed"], True)
        result = self.ext.evaluate_flag(self.fid, "subject://vip")
        self.assertIs(result["served"], False)
        self.assertEqual(result["reason"], "kill_switch")
        self.ext.restore_flag(self.fid, ADMIN)
        restored = self.ext.evaluate_flag(self.fid, "subject://vip")
        self.assertIs(restored["served"], True)

    def test_evaluation_stores_nothing(self):
        before = self.ext.get_flag(self.fid)
        self.ext.evaluate_flag(self.fid, "subject://a")
        self.ext.evaluate_flag(self.fid, "subject://b")
        self.assertEqual(self.ext.get_flag(self.fid), before)
        self.assertEqual(len(self.ext.list_flags(self.pid)), 1)

    def test_viewer_cannot_mutate_flag_but_can_evaluate(self):
        with self.assertRaises(PermissionDenied):
            self.ext.kill_flag(self.fid, VIEWER)
        result = self.ext.evaluate_flag(self.fid, "subject://a", actor=VIEWER)
        self.assertIn("served", result)


class FlagKillSwitchNegativeControlTests(unittest.TestCase):
    """Negative control for the batch's load-bearing invariant.

    A killed flag must serve NO subject, whatever its targeting
    or rollout says. The mutant ignores the recorded kill state
    -- the production failure this batch exists to reject.
    """

    def _flag_at_full_blast(self, ext, project_id):
        flag = ext.create_flag(project_id, "nc-flag", ADMIN)
        ext.set_flag_rollout(flag["id"], 100, ADMIN)
        ext.set_flag_targeting(flag["id"], ["subject://vip"], ADMIN)
        ext.kill_flag(flag["id"], ADMIN)
        return flag["id"]

    def test_kill_switch_ignoring_mutant_is_rejected(self):
        ext, store, project = make_extensions()

        class KillSwitchBlindExtensions(DevToolsExtensions):
            """Deliberately broken: never sees a thrown kill switch."""

            def _kill_switch_active(self, flag):
                return False

        flag_id = self._flag_at_full_blast(ext, project["id"])

        # (1) Canonical expectation from the real implementation.
        canonical = ext.evaluate_flag(flag_id, "subject://vip")
        self.assertIs(canonical["served"], False)
        self.assertEqual(canonical["reason"], "kill_switch")

        # (2) The mutant would NOT produce it: the killed flag
        # serves the targeted subject at 100% rollout. The mutant
        # shares the recorded flag table (extension records live in
        # the extension object); its ONLY difference is the seam.
        mutant = KillSwitchBlindExtensions(store)
        mutant._flags = ext._flags
        mutant_outcome = mutant.evaluate_flag(flag_id, "subject://vip")
        self.assertIs(mutant_outcome["served"], True)
        self.assertEqual(mutant_outcome["reason"], "targeted")

        # (3) Treating the mutant outcome as the expectation is
        # an explicit failure.
        with self.assertRaises(AssertionError):
            self.assertIs(mutant_outcome["served"], canonical["served"])


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.project = make_extensions()
        self.pid = self.project["id"]
        self.exp = self.ext.create_experiment(
            self.pid, "Checkout variants", ADMIN,
            variants=["control", "treatment"],
        )
        self.eid = self.exp["id"]

    def test_experiment_creation_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.create_experiment(self.pid, "One", ADMIN, variants=["only"])
        with self.assertRaises(ValidationError):
            self.ext.create_experiment(
                self.pid, "Dup", ADMIN, variants=["a", "a"],
            )
        self.assertEqual(self.exp["status"], "draft")

    def test_status_transitions_gated(self):
        with self.assertRaises(ValidationError):
            self.ext.set_experiment_status(self.eid, "concluded", ADMIN)
        self.ext.set_experiment_status(self.eid, "running", ADMIN)
        self.ext.set_experiment_status(self.eid, "concluded", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.set_experiment_status(self.eid, "running", ADMIN)

    def test_assignment_requires_running_and_follows_rule(self):
        with self.assertRaises(ValidationError):
            self.ext.assign_subject(self.eid, "subject://1", ADMIN)
        self.ext.set_experiment_status(self.eid, "running", ADMIN)
        subject = "subject://assignee"
        assignment = self.ext.assign_subject(self.eid, subject, ADMIN)
        bucket = bucket_of(self.eid, subject)
        expected_variant = ["control", "treatment"][(bucket * 2) // 100]
        self.assertEqual(assignment["variant"], expected_variant)
        self.assertEqual(assignment["bucket"], bucket)
        self.assertEqual(
            assignment["method"], "sha256_bucket_over_experiment_and_subject",
        )
        with self.assertRaises(ValidationError):
            self.ext.assign_subject(self.eid, subject, ADMIN)

    def test_outcome_requires_assignment_and_is_verbatim(self):
        self.ext.set_experiment_status(self.eid, "running", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_experiment_outcome(
                self.eid, "subject://ghost", "converted", ADMIN,
            )
        self.ext.assign_subject(self.eid, "subject://1", ADMIN)
        outcome = self.ext.record_experiment_outcome(
            self.eid, "subject://1", "converted (verified by hand)", ADMIN,
        )
        self.assertEqual(outcome["outcome"], "converted (verified by hand)")

    def test_summary_is_exact_counts(self):
        self.ext.set_experiment_status(self.eid, "running", ADMIN)
        subjects = ["subject://%d" % i for i in range(10)]
        for subject in subjects:
            self.ext.assign_subject(self.eid, subject, ADMIN)
        for subject in subjects[:3]:
            self.ext.record_experiment_outcome(
                self.eid, subject, "converted", ADMIN,
            )
        self.ext.record_experiment_outcome(
            self.eid, subjects[3], "bounced", ADMIN,
        )
        summary = self.ext.experiment_summary(self.eid)
        self.assertEqual(summary["total_assignments"], 10)
        self.assertEqual(
            sum(summary["assignments_by_variant"].values()), 10,
        )
        self.assertEqual(
            summary["outcomes_by_label"], {"converted": 3, "bounced": 1},
        )
        self.assertEqual(summary["total_outcomes"], 4)
        # The summary is derived: the experiment record holds no counts.
        record = self.ext.get_experiment(self.eid)
        self.assertNotIn("total_assignments", record)
        self.assertNotIn("outcomes_by_label", record)

    def test_experiment_flag_binding(self):
        flag = self.ext.create_flag(self.pid, "bound-flag", ADMIN)
        exp = self.ext.create_experiment(
            self.pid, "Bound", ADMIN, variants=["a", "b"], flag_id=flag["id"],
        )
        self.assertEqual(exp["flag_id"], flag["id"])
        other = self.store.create_project("Other", ADMIN)
        foreign = self.ext.create_flag(other["id"], "foreign", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_experiment(
                self.pid, "Mismatch", ADMIN,
                variants=["a", "b"], flag_id=foreign["id"],
            )


RULES = [
    {"rule_ref": "no-eval", "severity": "critical"},
    {"rule_ref": "line-length", "severity": "low"},
    {"rule_ref": "todo-comment", "severity": "info"},
]


class StaticAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.project = make_extensions()
        self.pid = self.project["id"]
        self.rule_set = self.ext.create_rule_set(
            self.pid, "Baseline rules", ADMIN, rules=RULES,
        )
        self.rid = self.rule_set["id"]

    def test_rule_set_shape_and_validation(self):
        self.assertIs(self.rule_set["analyzed_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.create_rule_set(
                self.pid, "Bad severity", ADMIN,
                rules=[{"rule_ref": "x", "severity": "blocker"}],
            )
        with self.assertRaises(ValidationError):
            self.ext.create_rule_set(
                self.pid, "Dup rules", ADMIN,
                rules=[{"rule_ref": "x", "severity": "low"},
                       {"rule_ref": "x", "severity": "high"}],
            )
        with self.assertRaises(ValidationError):
            self.ext.create_rule_set(self.pid, "Empty", ADMIN, rules=[])

    def test_profile_gate_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.create_quality_profile(
                self.pid, "Neg", ADMIN, self.rid, gate={"low": -1},
            )
        with self.assertRaises(ValidationError):
            self.ext.create_quality_profile(
                self.pid, "Bool", ADMIN, self.rid, gate={"low": True},
            )
        with self.assertRaises(ValidationError):
            self.ext.create_quality_profile(
                self.pid, "Foreign severity", ADMIN, self.rid,
                gate={"blocker": 0},
            )
        profile = self.ext.create_quality_profile(
            self.pid, "Team gate", ADMIN, self.rid,
            gate={"critical": 0, "low": 5},
        )
        self.assertEqual(profile["gate"], {"critical": 0, "low": 5})

    def _record_result(self, findings, profile_id=None):
        return self.ext.record_analysis_result(
            self.pid, DEVELOPER, analyzer_ref="analyzer://external-1",
            rule_set_id=self.rid, profile_id=profile_id, findings=findings,
        )

    def test_result_records_are_reported_not_analyzed(self):
        result = self._record_result(
            [{"rule_ref": "line-length", "severity": "low", "count": 3}],
        )
        self.assertIs(result["analyzed_here"], False)
        self.assertEqual(result["findings"][0]["count"], 3)
        with self.assertRaises(ValidationError):
            self._record_result(
                [{"rule_ref": "unknown-rule", "severity": "low", "count": 1}],
            )

    def test_gate_evaluation_pass_and_breach(self):
        profile = self.ext.create_quality_profile(
            self.pid, "Team gate", ADMIN, self.rid,
            gate={"critical": 0, "low": 5},
        )
        passing = self._record_result(
            [{"rule_ref": "line-length", "severity": "low", "count": 5}],
            profile_id=profile["id"],
        )
        verdict = self.ext.evaluate_quality_gate(passing["id"])
        self.assertIs(verdict["passed"], True)
        self.assertEqual(verdict["breaches"], [])
        failing = self._record_result(
            [{"rule_ref": "no-eval", "severity": "critical", "count": 1},
             {"rule_ref": "line-length", "severity": "low", "count": 4},
             {"rule_ref": "todo-comment", "severity": "info", "count": 9}],
            profile_id=profile["id"],
        )
        verdict = self.ext.evaluate_quality_gate(failing["id"])
        self.assertIs(verdict["passed"], False)
        self.assertEqual(
            verdict["breaches"],
            [{"severity": "critical", "count": 1, "limit": 0}],
        )
        self.assertEqual(verdict["ungated_severities"], ["info"])
        # The verdict is derived: nothing was written onto the result.
        self.assertNotIn(
            "passed", self.ext.get_analysis_result(failing["id"]),
        )

    def test_gate_evaluation_requires_gate(self):
        bare = self._record_result([])
        with self.assertRaises(ValidationError):
            self.ext.evaluate_quality_gate(bare["id"])
        profile = self.ext.create_quality_profile(
            self.pid, "No gate", ADMIN, self.rid,
        )
        gated = self._record_result([], profile_id=profile["id"])
        with self.assertRaises(ValidationError):
            self.ext.evaluate_quality_gate(gated["id"])


class ReleaseAutomationTests(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.project = make_extensions()
        self.pid = self.project["id"]
        self.plan = self.ext.create_release_plan(
            self.pid, ADMIN,
            stages=[{"name": "deploy", "kind": "deployment"},
                    {"name": "migrate", "kind": "data_migration"},
                    {"name": "verify", "kind": "verification"}],
        )
        self.plan_id = self.plan["id"]

    def test_plan_shape(self):
        self.assertIs(self.plan["executed_here"], False)
        self.assertNotIn("overall_status", self.plan)
        view = self.ext.release_plan_view(self.plan_id)
        self.assertEqual(view["overall_status"], "not_started")
        self.assertEqual(
            [s["latest_status"] for s in view["stages"]],
            [None, None, None],
        )

    def test_plan_binds_core_records(self):
        release = self.store.create_release(self.pid, "1.4.0", DEVELOPER)
        env = self.store.create_environment("prod", ADMIN, tier="production")
        plan = self.ext.create_release_plan(
            self.pid, ADMIN, stages=["deploy"],
            release_id=release["id"], environment_id=env["id"],
        )
        self.assertEqual(plan["release_id"], release["id"])
        with self.assertRaises(NotFoundError):
            self.ext.create_release_plan(
                self.pid, ADMIN, stages=["deploy"], release_id="rel-404",
            )

    def test_stage_records_and_view_derivation(self):
        self.ext.record_release_stage(self.plan_id, "deploy", "succeeded", ADMIN)
        view = self.ext.release_plan_view(self.plan_id)
        self.assertEqual(view["overall_status"], "in_progress")
        with self.assertRaises(ValidationError):
            self.ext.record_release_stage(
                self.plan_id, "not-a-stage", "succeeded", ADMIN,
            )
        self.ext.record_release_stage(self.plan_id, "migrate", "failed", ADMIN)
        view = self.ext.release_plan_view(self.plan_id)
        self.assertEqual(view["overall_status"], "failed")
        # A later report supersedes: latest status wins.
        self.ext.record_release_stage(self.plan_id, "migrate", "succeeded", ADMIN)
        self.ext.record_release_stage(self.plan_id, "verify", "skipped", ADMIN)
        view = self.ext.release_plan_view(self.plan_id)
        self.assertEqual(view["overall_status"], "completed")
        self.assertEqual(
            view["method"], "derived_from_recorded_stage_records",
        )

    def test_data_migration_records(self):
        migration = self.ext.record_data_migration(
            self.plan_id, "migration://users-v2", "reported_succeeded",
            ADMIN, rows_reported=1200,
        )
        self.assertIs(migration["executed_here"], False)
        self.assertEqual(migration["rows_reported"], 1200)
        with self.assertRaises(ValidationError):
            self.ext.record_data_migration(
                self.plan_id, "migration://x", "done", ADMIN,
            )
        with self.assertRaises(ValidationError):
            self.ext.record_data_migration(
                self.plan_id, "migration://x", "planned", ADMIN,
                rows_reported=-5,
            )


class ReferenceStubTests(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.project = make_extensions()
        self.pid = self.project["id"]

    def _all_stubs(self, env=None):
        if env is None:
            env = self.store.create_environment("sandbox", ADMIN)
        return [
            self.ext.record_repository_reference(
                self.pid, "git-host://org/repo", ADMIN,
                default_branch_label="main",
            ),
            self.ext.record_configuration_reference(
                self.pid, "config://stack/prod", ADMIN, format_label="hcl",
            ),
            self.ext.record_assessment_reference(
                self.pid, "framework://cmmc-l2", "reported: tracking", ADMIN,
            ),
            self.ext.record_model_reference(
                self.pid, "model://onboarding-flow", ADMIN,
                kind="workflow_automation",
            ),
            self.ext.record_authoring_reference(
                self.pid, "course://safety-101", ADMIN, format_label="scorm",
            ),
            self.ext.record_provisioning_reference(
                self.pid, "zone://tenant-a", ADMIN, environment_id=env["id"],
            ),
            self.ext.record_posture_reference(
                self.pid, "monitor://posture-1", ADMIN,
                finding_ref="finding://9", remediation_status="reported_open",
            ),
            self.ext.record_integration_reference(
                self.pid, "system://ticketing", ADMIN, direction="inbound",
            ),
        ]

    def test_stub_labels_and_honesty_flags(self):
        stubs = self._all_stubs()
        self.assertEqual(len(stubs), 8)
        for stub in stubs:
            self.assertIs(stub["reference_stub"], True)
            self.assertEqual(stub["status"], "recorded_reference_only")
        by_kind = {s["kind"]: s for s in stubs}
        self.assertIs(by_kind["repository"]["stored_here"], False)
        self.assertIs(by_kind["configuration"]["executed_here"], False)
        self.assertIs(by_kind["assessment"]["assessed_here"], False)
        self.assertEqual(
            by_kind["assessment"]["status_label"], "reported: tracking",
        )
        self.assertIs(by_kind["model"]["executed_here"], False)
        self.assertIs(by_kind["authoring"]["authored_here"], False)
        self.assertIs(by_kind["provisioning"]["provisioned_here"], False)
        self.assertIs(by_kind["posture"]["monitored_here"], False)
        self.assertIs(by_kind["posture"]["remediated_here"], False)
        self.assertIs(by_kind["integration"]["executed_here"], False)
        self.assertIs(by_kind["integration"]["reference_transport"], True)
        self.assertEqual(
            len(self.ext.list_reference_records(project_id=self.pid)), 8,
        )
        self.assertEqual(
            len(self.ext.list_reference_records(kind="integration")), 1,
        )

    def test_stubs_change_no_core_records(self):
        # The environment the provisioning reference binds to is a
        # core record created BEFORE the snapshot; the claim under
        # test is that creating the eight reference records
        # themselves changes no core record set.
        env = self.store.create_environment("sandbox", ADMIN)
        counts_before = (
            len(self.store._projects), len(self.store._issues),
            len(self.store._reviews), len(self.store._builds),
            len(self.store._releases), len(self.store._artifacts),
            len(self.store._environments), len(self.store._deployments),
        )
        self._all_stubs(env=env)
        counts_after = (
            len(self.store._projects), len(self.store._issues),
            len(self.store._reviews), len(self.store._builds),
            len(self.store._releases), len(self.store._artifacts),
            len(self.store._environments), len(self.store._deployments),
        )
        self.assertEqual(counts_before, counts_after)

    def test_stub_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.record_model_reference(
                self.pid, "model://x", ADMIN, kind="spreadsheet",
            )
        with self.assertRaises(ValidationError):
            self.ext.record_posture_reference(
                self.pid, "monitor://x", ADMIN, remediation_status="fixed",
            )
        with self.assertRaises(ValidationError):
            self.ext.record_integration_reference(
                self.pid, "system://x", ADMIN, direction="sideways",
            )
        with self.assertRaises(PermissionDenied):
            self.ext.record_repository_reference(
                self.pid, "git-host://org/repo", VIEWER,
            )


class AuditAndRbacTests(unittest.TestCase):
    def test_extension_mutations_audited_and_denials_recorded(self):
        audit = AuditLog()
        ext, store, project = make_extensions(audit=audit)
        pid = project["id"]
        ext.create_flag(pid, "audited-flag", ADMIN)
        entries = audit.entries()
        self.assertTrue(
            any(e["action"] == "ext_flag_create" for e in entries),
        )
        with self.assertRaises(PermissionDenied):
            ext.create_flag(pid, "viewer-flag", VIEWER)
        entries = audit.entries()
        self.assertTrue(
            any(e["action"] == "deployment_write:denied" for e in entries),
        )

    def test_no_actor_write_denied(self):
        ext, store, project = make_extensions()
        with self.assertRaises(PermissionDenied):
            ext.create_flag(project["id"], "nope", None)

    def test_failed_operation_consumes_no_id(self):
        ext, store, project = make_extensions()
        pid = project["id"]
        with self.assertRaises(ValidationError):
            ext.create_flag(pid, "", ADMIN)
        flag = ext.create_flag(pid, "first", ADMIN)
        self.assertEqual(flag["id"], "flg-1")
        with self.assertRaises(ValidationError):
            ext.set_flag_rollout(flag["id"], 500, ADMIN)
        second = ext.create_flag(pid, "second", ADMIN)
        self.assertEqual(second["id"], "flg-2")


if __name__ == "__main__":
    unittest.main()
