"""Tests for the Group 17 final GAPS batch extensions.

Pins the extension surface per entry (see BATCH.md in the group
directory): pipeline run requests + verbatim outcome records
(idx 174), toolchain declarations (idx 176), artifact storage
backends + custody records (idx 182), and the six labeled
reference implementations (idx 175, 177, 178, 179, 180, 181) --
plus the house invariants the batch carries: nothing executes,
reported values are stored verbatim and never interpreted, no
computed compliance score exists anywhere, derived state is
never stored, core records are untouched by the stub surface,
and the batch's fresh mutation-verified negative control (the
pipeline-run status derivation seam).
"""

import hashlib
import unittest

from devtools.errors import NotFoundError, PermissionDenied, ValidationError
from devtools.extensions import (
    ASSESSMENT_VIEW_METHOD,
    BACKEND_SUMMARY_METHOD,
    DevToolsExtensions,
)
from devtools_helpers import ADMIN, DEVELOPER, VIEWER, make_store

BINARY = b"devtools-l1-batch-binary"
BINARY_SHA = hashlib.sha256(BINARY).hexdigest()
X_SHA = hashlib.sha256(b"x").hexdigest()


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.project = make_store()
        self.audit = self.store.audit
        self.ext = DevToolsExtensions(self.store)
        self.proj_id = self.project["id"]
        self.build = self.store.record_build(
            self.proj_id, DEVELOPER, ref="main",
            status="succeeded", config={"pipeline": "ci"},
        )
        self.artifact = self.store.register_artifact(
            self.proj_id, "app.zip", DEVELOPER, content=BINARY,
        )
        self.checksum_only = self.store.register_artifact(
            self.proj_id, "checksums.txt", DEVELOPER, checksum=X_SHA,
        )
        self.environment = self.store.create_environment(
            "prod", ADMIN, tier="low",
        )

    def core_counts(self):
        pid = self.proj_id
        return {
            "projects": len(self.store.list_projects()),
            "issues": len(self.store.list_issues(pid)),
            "reviews": len(self.store.list_reviews(pid)),
            "builds": len(self.store.list_builds(pid)),
            "releases": len(self.store.list_releases(pid)),
            "artifacts": len(self.store.list_artifacts(pid)),
            "environments": len(self.store.list_environments()),
            "deployments": len(self.store.list_deployments(project_id=pid)),
        }


def all_keys(value):
    """Yield every dict key in a nested record structure."""
    if isinstance(value, dict):
        for key, sub in value.items():
            yield key
            yield from all_keys(sub)
    elif isinstance(value, list):
        for item in value:
            yield from all_keys(item)


# -- idx 174: CI/CD execution engines ------------------------------------


class TestPipelineRunRequests(BatchFixture):
    def test_request_record_shape(self):
        run = self.ext.request_pipeline_run(
            self.proj_id, DEVELOPER, build_id=self.build["id"],
            runner_ref="runner://ci-1", stage_label="build",
        )
        self.assertEqual(run["id"], "run-1")
        self.assertEqual(run["project_id"], self.proj_id)
        self.assertEqual(run["build_id"], self.build["id"])
        self.assertEqual(run["runner_ref"], "runner://ci-1")
        self.assertEqual(run["stage_label"], "build")
        self.assertIs(run["executed_here"], False)
        # The reported status is derived at read, never stored.
        self.assertNotIn("status", run)

    def test_request_without_build_binding(self):
        run = self.ext.request_pipeline_run(self.proj_id, DEVELOPER)
        self.assertIsNone(run["build_id"])

    def test_unknown_build_consumes_no_id(self):
        with self.assertRaises(NotFoundError):
            self.ext.request_pipeline_run(
                self.proj_id, DEVELOPER, build_id="bld-99"
            )
        run = self.ext.request_pipeline_run(self.proj_id, DEVELOPER)
        self.assertEqual(run["id"], "run-1")

    def test_build_of_another_project_rejected(self):
        other = self.store.create_project("Other Service", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.request_pipeline_run(
                other["id"], DEVELOPER, build_id=self.build["id"]
            )

    def test_outcomes_verbatim_and_view_derives_latest(self):
        run = self.ext.request_pipeline_run(
            self.proj_id, DEVELOPER, build_id=self.build["id"]
        )
        view = self.ext.pipeline_run_view(run["id"])
        self.assertEqual(view["reported_status"], "requested")
        self.assertEqual(view["outcome_count"], 0)
        first = self.ext.record_run_outcome(run["id"], DEVELOPER, "failed")
        second = self.ext.record_run_outcome(run["id"], DEVELOPER, "succeeded")
        self.assertEqual(first["id"], "out-1")
        self.assertEqual(second["status"], "succeeded")
        self.assertIs(second["executed_here"], False)
        view = self.ext.pipeline_run_view(run["id"])
        self.assertEqual(view["reported_status"], "succeeded")
        self.assertEqual(view["outcome_count"], 2)
        self.assertIs(view["executed_here"], False)
        outcomes = self.ext.list_run_outcomes(run_id=run["id"])
        self.assertEqual([o["status"] for o in outcomes],
                         ["failed", "succeeded"])

    def test_outcome_rejects_unknown_status_no_id_consumed(self):
        run = self.ext.request_pipeline_run(self.proj_id, DEVELOPER)
        with self.assertRaises(ValidationError):
            self.ext.record_run_outcome(run["id"], DEVELOPER, "green")
        outcome = self.ext.record_run_outcome(run["id"], DEVELOPER, "failed")
        self.assertEqual(outcome["id"], "out-1")

    def test_request_and_outcome_leave_core_build_unchanged(self):
        before = self.store.get_build(self.build["id"])
        run = self.ext.request_pipeline_run(
            self.proj_id, DEVELOPER, build_id=self.build["id"]
        )
        self.ext.record_run_outcome(run["id"], DEVELOPER, "succeeded")
        self.assertEqual(self.store.get_build(self.build["id"]), before)

    def test_viewer_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.request_pipeline_run(self.proj_id, VIEWER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("build_write:denied", actions)

    def test_unknown_run_view_raises(self):
        with self.assertRaises(NotFoundError):
            self.ext.pipeline_run_view("run-99")


# -- idx 176: compilers & build toolchains --------------------------------


class TestToolchains(BatchFixture):
    def test_register_shape(self):
        toolchain = self.ext.register_toolchain(
            self.proj_id, "gcc", DEVELOPER,
            language="c", version_label="13.2",
        )
        self.assertEqual(toolchain["id"], "tch-1")
        self.assertEqual(toolchain["name"], "gcc")
        self.assertEqual(toolchain["language"], "c")
        self.assertEqual(toolchain["version_label"], "13.2")
        self.assertIs(toolchain["executed_here"], False)

    def test_unknown_project_raises(self):
        with self.assertRaises(NotFoundError):
            self.ext.register_toolchain("prj-99", "gcc", DEVELOPER)

    def test_list_filtered_by_project(self):
        self.ext.register_toolchain(self.proj_id, "gcc", DEVELOPER)
        other = self.store.create_project("Other Service", ADMIN)
        self.ext.register_toolchain(other["id"], "clang", DEVELOPER)
        self.assertEqual(len(self.ext.list_toolchains()), 2)
        mine = self.ext.list_toolchains(project_id=self.proj_id)
        self.assertEqual([t["name"] for t in mine], ["gcc"])


# -- idx 182: artifact binary storage backends -----------------------------


class TestArtifactCustody(BatchFixture):
    def test_backend_record_shape(self):
        backend = self.ext.register_storage_backend(
            "artifact-store", ADMIN, kind="object_store"
        )
        self.assertEqual(backend["id"], "stb-1")
        self.assertEqual(backend["kind"], "object_store")
        self.assertIs(backend["content_held_here"], False)

    def test_custody_copies_checksum_and_size_only(self):
        backend = self.ext.register_storage_backend("store", ADMIN)
        custody = self.ext.record_artifact_custody(
            self.artifact["id"], backend["id"], ADMIN,
            custodian_ref="vault://east",
        )
        self.assertEqual(custody["id"], "plm-1")
        self.assertEqual(custody["sha256"], BINARY_SHA)
        self.assertEqual(custody["size_bytes"], len(BINARY))
        self.assertEqual(custody["custodian_ref"], "vault://east")
        self.assertIs(custody["content_held_here"], False)
        self.assertNotIn("content", custody)

    def test_checksum_only_artifact_custody_size_is_none(self):
        backend = self.ext.register_storage_backend("store", ADMIN)
        custody = self.ext.record_artifact_custody(
            self.checksum_only["id"], backend["id"], ADMIN
        )
        self.assertIsNone(custody["size_bytes"])
        self.assertEqual(custody["sha256"], X_SHA)

    def test_backend_summary_derivation(self):
        backend = self.ext.register_storage_backend("store", ADMIN)
        self.ext.record_artifact_custody(
            self.artifact["id"], backend["id"], ADMIN
        )
        self.ext.record_artifact_custody(
            self.checksum_only["id"], backend["id"], ADMIN
        )
        summary = self.ext.storage_backend_summary(backend["id"])
        self.assertEqual(summary["placements"], 2)
        self.assertEqual(summary["total_size_bytes"], len(BINARY))
        self.assertEqual(summary["unknown_size_count"], 1)
        self.assertEqual(summary["method"], BACKEND_SUMMARY_METHOD)

    def test_verify_by_content_unchanged_after_custody(self):
        backend = self.ext.register_storage_backend("store", ADMIN)
        self.ext.record_artifact_custody(
            self.artifact["id"], backend["id"], ADMIN
        )
        self.assertTrue(
            self.store.verify_artifact(self.artifact["id"], BINARY)
        )
        self.assertFalse(
            self.store.verify_artifact(self.artifact["id"], b"other")
        )

    def test_unknown_backend_and_artifact_raise(self):
        backend = self.ext.register_storage_backend("store", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.record_artifact_custody("art-99", backend["id"], ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.record_artifact_custody(
                self.artifact["id"], "stb-99", ADMIN
            )

    def test_viewer_denied_backend_registration(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_storage_backend("store", VIEWER)


# -- idx 175: code hosting internals ---------------------------------------


class TestRepositoryReferences(BatchFixture):
    def test_reference_shape_and_labels(self):
        ref = self.ext.record_repository_reference(
            self.proj_id, "git-host://org/repo", DEVELOPER,
            default_branch_label="main",
        )
        self.assertEqual(ref["id"], "ref-1")
        self.assertEqual(ref["kind"], "repository")
        self.assertIs(ref["reference_stub"], True)
        self.assertEqual(ref["status"], "recorded_reference_only")
        self.assertIs(ref["stored_here"], False)
        self.assertIs(ref["merged_here"], False)
        self.assertNotIn("content", ref)

    def test_branch_record_is_metadata_only(self):
        ref = self.ext.record_repository_reference(
            self.proj_id, "git-host://org/repo", DEVELOPER
        )
        branch = self.ext.record_branch_record(
            ref["id"], "feature/login", DEVELOPER, base_branch_label="main"
        )
        self.assertEqual(branch["id"], "brn-1")
        self.assertIs(branch["reference_stub"], True)
        self.assertIs(branch["stored_here"], False)
        self.assertIs(branch["merged_here"], False)
        listed = self.ext.list_branch_records(reference_id=ref["id"])
        self.assertEqual(len(listed), 1)

    def test_branch_on_configuration_reference_rejected(self):
        ref = self.ext.record_configuration_reference(
            self.proj_id, "cfg://app", DEVELOPER
        )
        with self.assertRaises(ValidationError):
            self.ext.record_branch_record(ref["id"], "topic", DEVELOPER)

    def test_unknown_project_raises(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_repository_reference(
                "prj-99", "git-host://org/repo", DEVELOPER
            )


# -- idx 177: configuration-as-code execution & orchestration --------------


class TestConfigurationReferences(BatchFixture):
    def test_reference_shape_and_labels(self):
        ref = self.ext.record_configuration_reference(
            self.proj_id, "cfg://app/prod", DEVELOPER, format_label="yaml"
        )
        self.assertEqual(ref["kind"], "configuration")
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["applied_here"], False)
        self.assertIs(ref["executed_here"], False)

    def test_apply_outcome_verbatim(self):
        ref = self.ext.record_configuration_reference(
            self.proj_id, "cfg://app/prod", DEVELOPER
        )
        outcome = self.ext.record_apply_outcome(
            ref["id"], "applied cleanly", DEVELOPER
        )
        self.assertEqual(outcome["id"], "apl-1")
        self.assertEqual(outcome["outcome_label"], "applied cleanly")
        self.assertIs(outcome["applied_here"], False)
        self.assertIs(outcome["reference_stub"], True)

    def test_apply_outcome_on_repository_reference_rejected(self):
        ref = self.ext.record_repository_reference(
            self.proj_id, "git-host://org/repo", DEVELOPER
        )
        with self.assertRaises(ValidationError):
            self.ext.record_apply_outcome(ref["id"], "applied", DEVELOPER)


# -- idx 178: compliance assessment & KSI status automation -----------------


class TestAssessmentJobs(BatchFixture):
    def test_job_shape(self):
        job = self.ext.create_assessment_job(
            self.proj_id, "fedramp-20x", DEVELOPER, ksi_ref="ksi://sca"
        )
        self.assertEqual(job["id"], "asj-1")
        self.assertIs(job["reference_stub"], True)
        self.assertEqual(job["status"], "recorded_reference_only")
        self.assertIs(job["assessed_here"], False)
        self.assertEqual(job["ksi_ref"], "ksi://sca")
        self.assertNotIn("status_label", job)

    def test_status_verbatim_and_view_derives_latest(self):
        job = self.ext.create_assessment_job(
            self.proj_id, "fedramp-20x", DEVELOPER
        )
        view = self.ext.assessment_job_view(job["id"])
        self.assertIsNone(view["latest_reported_status"])
        self.ext.record_assessment_status(
            job["id"], "evidence collection", DEVELOPER
        )
        report = self.ext.record_assessment_status(
            job["id"], "KSI validation in progress", DEVELOPER
        )
        self.assertEqual(report["status_label"], "KSI validation in progress")
        self.assertIs(report["assessed_here"], False)
        view = self.ext.assessment_job_view(job["id"])
        self.assertEqual(
            view["latest_reported_status"], "KSI validation in progress"
        )
        self.assertEqual(view["status_report_count"], 2)
        self.assertEqual(view["method"], ASSESSMENT_VIEW_METHOD)
        self.assertIs(view["assessed_here"], False)

    def test_unknown_job_raises(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_assessment_status("asj-99", "x", DEVELOPER)

    def test_viewer_denied_job_creation(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_assessment_job(self.proj_id, "fw", VIEWER)


# -- idx 179: business modeling & automation engines -------------------------


class TestModelReferences(BatchFixture):
    def test_model_reference_and_execution_request(self):
        ref = self.ext.record_model_reference(
            self.proj_id, "model://onboarding", DEVELOPER,
            kind="workflow_automation",
        )
        self.assertEqual(ref["kind"], "model")
        self.assertEqual(ref["model_kind"], "workflow_automation")
        self.assertIs(ref["executed_here"], False)
        request = self.ext.request_model_execution(
            ref["id"], DEVELOPER, requester_ref="team://ops"
        )
        self.assertEqual(request["id"], "exq-1")
        self.assertEqual(request["status"], "requested")
        self.assertIs(request["reference_stub"], True)
        self.assertIs(request["executed_here"], False)

    def test_execution_request_on_repository_reference_rejected(self):
        ref = self.ext.record_repository_reference(
            self.proj_id, "git-host://org/repo", DEVELOPER
        )
        with self.assertRaises(ValidationError):
            self.ext.request_model_execution(ref["id"], DEVELOPER)

    def test_bad_model_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.record_model_reference(
                self.proj_id, "model://x", DEVELOPER, kind="other"
            )


# -- idx 180: course & content authoring tools --------------------------------


class TestCourseRecords(BatchFixture):
    def test_course_asset_and_outcome_records(self):
        course = self.ext.create_course_record(
            self.proj_id, "Onboarding 101", DEVELOPER, format_label="scorm"
        )
        self.assertEqual(course["id"], "crs-1")
        self.assertIs(course["reference_stub"], True)
        self.assertIs(course["authored_here"], False)
        self.assertNotIn("content", course)
        asset = self.ext.record_course_asset(
            course["id"], "asset://intro-video", DEVELOPER,
            format_label="video",
        )
        self.assertEqual(asset["id"], "ast-1")
        self.assertIs(asset["authored_here"], False)
        self.assertNotIn("content", asset)
        outcome = self.ext.record_course_outcome(
            course["id"], "published by authoring tool", DEVELOPER
        )
        self.assertEqual(outcome["id"], "cou-1")
        self.assertEqual(
            outcome["outcome_label"], "published by authoring tool"
        )
        self.assertIs(outcome["authored_here"], False)

    def test_asset_on_unknown_course_raises(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_course_asset("crs-99", "asset://x", DEVELOPER)


# -- idx 181: landing-zone / tenant provisioning & hosting ---------------------


class TestProvisioningReferences(BatchFixture):
    def test_reference_shape_and_labels(self):
        ref = self.ext.record_provisioning_reference(
            self.proj_id, "zone://tenant-a", ADMIN,
            environment_id=self.environment["id"],
        )
        self.assertEqual(ref["kind"], "provisioning")
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["provisioned_here"], False)
        self.assertIs(ref["hosted_here"], False)
        self.assertEqual(ref["environment_id"], self.environment["id"])

    def test_unknown_environment_raises(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_provisioning_reference(
                self.proj_id, "zone://tenant-a", ADMIN,
                environment_id="env-99",
            )


# -- Surface invariants ---------------------------------------------------------


class TestStubSurfaceInvariants(BatchFixture):
    def _build_all_stubs(self):
        repo = self.ext.record_repository_reference(
            self.proj_id, "git-host://org/repo", DEVELOPER
        )
        self.ext.record_branch_record(repo["id"], "topic", DEVELOPER)
        cfg = self.ext.record_configuration_reference(
            self.proj_id, "cfg://app", DEVELOPER
        )
        self.ext.record_apply_outcome(cfg["id"], "applied", DEVELOPER)
        job = self.ext.create_assessment_job(
            self.proj_id, "fedramp-20x", DEVELOPER
        )
        self.ext.record_assessment_status(job["id"], "open", DEVELOPER)
        model = self.ext.record_model_reference(
            self.proj_id, "model://m", DEVELOPER
        )
        self.ext.request_model_execution(model["id"], DEVELOPER)
        course = self.ext.create_course_record(
            self.proj_id, "Course", DEVELOPER
        )
        self.ext.record_course_asset(course["id"], "asset://a", DEVELOPER)
        self.ext.record_course_outcome(course["id"], "draft", DEVELOPER)
        self.ext.record_provisioning_reference(
            self.proj_id, "zone://z", ADMIN
        )
        return repo, cfg, job, model, course

    def test_stubs_change_no_core_record(self):
        before = self.core_counts()
        self._build_all_stubs()
        self.assertEqual(self.core_counts(), before)

    def test_all_stub_records_carry_reference_stub(self):
        repo, cfg, job, model, course = self._build_all_stubs()
        records = []
        records += self.ext.list_reference_records()
        records += self.ext.list_branch_records()
        records += self.ext.list_apply_outcomes()
        records += self.ext.list_assessment_jobs()
        records += self.ext.list_assessment_reports()
        records += self.ext.list_model_executions()
        records += self.ext.list_course_records()
        records += self.ext.list_course_assets()
        records += self.ext.list_course_outcomes()
        self.assertTrue(records)
        for record in records:
            self.assertIs(record["reference_stub"], True, record["id"])

    def test_no_score_field_anywhere(self):
        run = self.ext.request_pipeline_run(self.proj_id, DEVELOPER)
        self.ext.record_run_outcome(run["id"], DEVELOPER, "succeeded")
        self.ext.register_toolchain(self.proj_id, "gcc", DEVELOPER)
        backend = self.ext.register_storage_backend("store", ADMIN)
        self.ext.record_artifact_custody(
            self.artifact["id"], backend["id"], ADMIN
        )
        repo, cfg, job, model, course = self._build_all_stubs()
        outputs = [
            self.ext.list_pipeline_runs(),
            self.ext.list_run_outcomes(),
            self.ext.pipeline_run_view(run["id"]),
            self.ext.list_toolchains(),
            self.ext.list_storage_backends(),
            self.ext.list_artifact_custody(),
            self.ext.storage_backend_summary(backend["id"]),
            self.ext.list_reference_records(),
            self.ext.list_branch_records(),
            self.ext.list_apply_outcomes(),
            self.ext.list_assessment_jobs(),
            self.ext.list_assessment_reports(),
            self.ext.assessment_job_view(job["id"]),
            self.ext.list_model_executions(),
            self.ext.list_course_records(),
            self.ext.list_course_assets(),
            self.ext.list_course_outcomes(),
        ]
        for output in outputs:
            for key in all_keys(output):
                self.assertNotIn("score", key)


# -- Fresh negative control: the run-status derivation seam ---------------------


class EarliestOutcomeExtensions(DevToolsExtensions):
    """Mutant: the run view reads the *earliest* outcome, not the latest."""

    def _derive_run_status(self, outcomes):
        if not outcomes:
            return "requested"
        return outcomes[0]["status"]


class TestNegativeControlRunStatusDerivation(BatchFixture):
    def _run_with_two_outcomes(self, ext):
        run = ext.request_pipeline_run(
            self.proj_id, DEVELOPER, build_id=self.build["id"]
        )
        ext.record_run_outcome(run["id"], DEVELOPER, "failed")
        ext.record_run_outcome(run["id"], DEVELOPER, "succeeded")
        return run["id"]

    def test_control_passes(self):
        run_id = self._run_with_two_outcomes(self.ext)
        view = self.ext.pipeline_run_view(run_id)
        self.assertEqual(view["reported_status"], "succeeded")

    def test_mutant_fails(self):
        mutant = EarliestOutcomeExtensions(self.store)
        run_id = self._run_with_two_outcomes(mutant)
        view = mutant.pipeline_run_view(run_id)
        with self.assertRaises(AssertionError):
            self.assertEqual(view["reported_status"], "succeeded")

    def test_mutant_check_is_not_vacuous(self):
        mutant = EarliestOutcomeExtensions(self.store)
        run = mutant.request_pipeline_run(self.proj_id, DEVELOPER)
        mutant.record_run_outcome(run["id"], DEVELOPER, "failed")
        view = mutant.pipeline_run_view(run["id"])
        self.assertEqual(view["reported_status"], "failed")


if __name__ == "__main__":
    unittest.main()
