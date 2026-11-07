"""Tests for the final GAPS batch additions (remainder-addition unit).

Pins the second-unit extension surface in
``src/devtools/extensions_addition.py`` against the 2 open
entries of the GAPS.md section "Remainder Addition --
Development Tools L2 (+4 forks)" (see ``../BATCH-ADDITION.md``):

- No-code / low-code application development platform: visual
  application builder & runtime (idx 578) -- built as drafted:
  application definition records (components held as inert
  data, versioned on revision; ``built_here`` / ``run_here`` /
  ``executed_here`` / ``rendered_here`` all False) plus
  publication records reported by the external platform, and an
  application view derived at read. No application is built or
  run anywhere in this build.
- Compliance documentation & SSP generation tooling (idx 579)
  -- reference as drafted: labeled reference records naming the
  document, the framework / control-documentation source, and
  the system by opaque reference only, plus outcome records
  with status labels verbatim as reported
  (``reference_stub: True``, ``generated_here: False``,
  ``document_held_here: False``). No document content exists in
  this build and nothing is generated.

Plus the unit's fresh negative control: the latest-label seam
``DevToolsExtensionsAddition._latest_label`` -- a mutant that
reads the earliest record must not satisfy the canonical
expectation that the current reported state is the *latest*
record reported.
"""

import unittest

from devtools.errors import NotFoundError, PermissionDenied, ValidationError
from devtools.extensions_addition import (
    APPLICATION_VIEW_METHOD,
    DOCUMENT_GENERATION_VIEW_METHOD,
    DevToolsExtensionsAddition,
)

from devtools_helpers import ADMIN, DEVELOPER, VIEWER, make_store

COMPONENTS = [
    {"component_ref": "intake-form", "kind": "form"},
    {"component_ref": "case-page", "kind": "page"},
    "approval-flow",
]


def make_addition(audit=None):
    store, project = make_store(audit=audit)
    return DevToolsExtensionsAddition(store), store, project


def core_counts(store):
    """Counts of all eight core record sets (the unchanged pin)."""
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


class ApplicationDefinitionTests(unittest.TestCase):
    """Idx 578 -- definitions held as data; nothing built or run."""

    def setUp(self):
        self.ext, self.store, self.project = make_addition()
        self.pid = self.project["id"]

    def test_define_application_shape_and_labels(self):
        app = self.ext.define_application(
            self.pid, "Permit Intake", ADMIN, COMPONENTS)
        self.assertEqual(app["id"], "app-1")
        self.assertEqual(app["project_id"], self.pid)
        self.assertEqual(app["revision"], 1)
        self.assertIs(app["definition_only"], True)
        self.assertIs(app["built_here"], False)
        self.assertIs(app["run_here"], False)
        self.assertIs(app["executed_here"], False)
        self.assertIs(app["rendered_here"], False)
        self.assertEqual(
            app["components"],
            [{"component_ref": "intake-form", "kind": "form"},
             {"component_ref": "case-page", "kind": "page"},
             {"component_ref": "approval-flow", "kind": "custom"}],
        )

    def test_components_are_copied_at_the_boundary(self):
        components = [{"component_ref": "a-page", "kind": "page"}]
        app = self.ext.define_application(self.pid, "App", ADMIN, components)
        components[0]["component_ref"] = "mutated"
        components.append({"component_ref": "extra", "kind": "form"})
        stored = self.ext.get_application(app["id"])
        self.assertEqual(
            stored["components"],
            [{"component_ref": "a-page", "kind": "page"}],
        )

    def test_component_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.define_application(self.pid, "Empty", ADMIN, [])
        with self.assertRaises(ValidationError):
            self.ext.define_application(
                self.pid, "BadKind", ADMIN,
                [{"component_ref": "x", "kind": "quantum"}])
        with self.assertRaises(ValidationError):
            self.ext.define_application(
                self.pid, "Dup", ADMIN,
                [{"component_ref": "x", "kind": "page"},
                 {"component_ref": "x", "kind": "form"}])
        with self.assertRaises(ValidationError):
            self.ext.define_application(self.pid, "", ADMIN, COMPONENTS)
        # Failed operations consume no id.
        app = self.ext.define_application(self.pid, "Ok", ADMIN, COMPONENTS)
        self.assertEqual(app["id"], "app-1")

    def test_define_requires_a_core_project(self):
        with self.assertRaises(NotFoundError):
            self.ext.define_application("prj-99", "Nope", ADMIN, COMPONENTS)

    def test_revise_application_versions_the_definition(self):
        app = self.ext.define_application(
            self.pid, "Permit Intake", ADMIN, COMPONENTS)
        revised = self.ext.revise_application(
            app["id"], DEVELOPER,
            [{"component_ref": "intake-form", "kind": "form"}])
        self.assertEqual(revised["revision"], 2)
        self.assertEqual(len(revised["components"]), 1)
        stored = self.ext.get_application(app["id"])
        self.assertEqual(stored["revision"], 2)
        with self.assertRaises(NotFoundError):
            self.ext.revise_application("app-99", ADMIN, COMPONENTS)

    def test_list_applications_filters_by_project(self):
        self.ext.define_application(self.pid, "One", ADMIN, COMPONENTS)
        self.assertEqual(len(self.ext.list_applications()), 1)
        self.assertEqual(len(self.ext.list_applications(self.pid)), 1)
        self.assertEqual(len(self.ext.list_applications("prj-99")), 0)


class ApplicationPublicationTests(unittest.TestCase):
    """Idx 578 -- publication outcomes recorded as reported."""

    def setUp(self):
        self.ext, self.store, self.project = make_addition()
        self.pid = self.project["id"]
        self.app = self.ext.define_application(
            self.pid, "Permit Intake", ADMIN, COMPONENTS)

    def test_publication_record_shape(self):
        pub = self.ext.record_application_publication(
            self.app["id"], DEVELOPER, application_ref="built-app-7")
        self.assertEqual(pub["id"], "apu-1")
        self.assertEqual(pub["application_id"], self.app["id"])
        self.assertEqual(pub["status"], "reported_published")
        self.assertEqual(pub["definition_revision"], 1)
        self.assertEqual(pub["application_ref"], "built-app-7")
        self.assertIs(pub["built_here"], False)
        self.assertIs(pub["run_here"], False)
        self.assertIs(pub["executed_here"], False)

    def test_publication_snapshots_the_current_revision(self):
        self.ext.revise_application(
            self.app["id"], ADMIN,
            [{"component_ref": "only", "kind": "page"}])
        pub = self.ext.record_application_publication(self.app["id"], ADMIN)
        self.assertEqual(pub["definition_revision"], 2)

    def test_publication_status_vocabulary(self):
        with self.assertRaises(ValidationError):
            self.ext.record_application_publication(
                self.app["id"], ADMIN, status="published")
        pub = self.ext.record_application_publication(
            self.app["id"], ADMIN, status="reported_failed")
        self.assertEqual(pub["status"], "reported_failed")
        self.assertEqual(pub["id"], "apu-1")  # failure consumed no id

    def test_publication_binds_a_core_environment(self):
        env = self.store.create_environment("prod", ADMIN)
        pub = self.ext.record_application_publication(
            self.app["id"], ADMIN, environment_id=env["id"])
        self.assertEqual(pub["environment_id"], env["id"])
        with self.assertRaises(NotFoundError):
            self.ext.record_application_publication(
                self.app["id"], ADMIN, environment_id="env-99")

    def test_application_view_derives_and_stores_nothing(self):
        self.assertEqual(
            self.ext.application_view(self.app["id"]),
            {"application_id": self.app["id"],
             "project_id": self.pid,
             "revision": 1,
             "component_count": 3,
             "publication_count": 0,
             "latest_publication_status": None,
             "method": APPLICATION_VIEW_METHOD},
        )
        self.ext.record_application_publication(
            self.app["id"], ADMIN, status="reported_published")
        self.ext.record_application_publication(
            self.app["id"], ADMIN, status="reported_failed")
        view = self.ext.application_view(self.app["id"])
        self.assertEqual(view["publication_count"], 2)
        self.assertEqual(view["latest_publication_status"], "reported_failed")
        # The stored definition record never gains a count or status.
        stored = self.ext.get_application(self.app["id"])
        self.assertNotIn("publication_count", stored)
        self.assertNotIn("latest_publication_status", stored)
        self.assertNotIn("status", stored)


class DocumentGenerationReferenceTests(unittest.TestCase):
    """Idx 579 -- labeled reference implementation; nothing generated."""

    def setUp(self):
        self.ext, self.store, self.project = make_addition()
        self.pid = self.project["id"]

    def test_reference_record_shape_and_labels(self):
        ref = self.ext.record_document_generation_reference(
            self.pid, "ssp-doc-1", ADMIN,
            framework_ref="nist-800-53-doc", system_ref="sys-1")
        self.assertEqual(ref["id"], "dgr-1")
        self.assertEqual(ref["kind"], "documentation_generation")
        self.assertIs(ref["reference_stub"], True)
        self.assertEqual(ref["status"], "recorded_reference_only")
        self.assertIs(ref["generated_here"], False)
        self.assertIs(ref["document_held_here"], False)
        self.assertEqual(ref["document_ref"], "ssp-doc-1")
        self.assertEqual(ref["framework_ref"], "nist-800-53-doc")

    def test_outcome_record_shape_and_verbatim_label(self):
        ref = self.ext.record_document_generation_reference(
            self.pid, "ssp-doc-1", ADMIN)
        outcome = self.ext.record_document_generation_outcome(
            ref["id"], "generated_by_platform", DEVELOPER,
            output_ref="ssp-out-1")
        self.assertEqual(outcome["id"], "dgo-1")
        self.assertEqual(outcome["status_label"], "generated_by_platform")
        self.assertEqual(outcome["output_ref"], "ssp-out-1")
        self.assertIs(outcome["reference_stub"], True)
        self.assertIs(outcome["generated_here"], False)
        self.assertIs(outcome["document_held_here"], False)
        with self.assertRaises(NotFoundError):
            self.ext.record_document_generation_outcome(
                "dgr-99", "anything", ADMIN)

    def test_reference_requires_a_core_project(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_document_generation_reference(
                "prj-99", "ssp-doc-1", ADMIN)

    def test_view_derives_latest_outcome_and_stores_nothing(self):
        ref = self.ext.record_document_generation_reference(
            self.pid, "ssp-doc-1", ADMIN)
        view = self.ext.document_generation_view(ref["id"])
        self.assertEqual(
            view,
            {"reference_id": ref["id"],
             "outcome_count": 0,
             "latest_outcome_label": None,
             "method": DOCUMENT_GENERATION_VIEW_METHOD},
        )
        self.ext.record_document_generation_outcome(
            ref["id"], "draft_exported", ADMIN)
        self.ext.record_document_generation_outcome(
            ref["id"], "final_generated", ADMIN)
        view = self.ext.document_generation_view(ref["id"])
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_outcome_label"], "final_generated")
        stored = self.ext.get_document_generation_reference(ref["id"])
        self.assertNotIn("outcome_count", stored)
        self.assertNotIn("latest_outcome_label", stored)

    def test_creating_references_changes_no_core_record(self):
        before = core_counts(self.store)
        ref = self.ext.record_document_generation_reference(
            self.pid, "ssp-doc-1", ADMIN)
        self.ext.record_document_generation_outcome(
            ref["id"], "generated_by_platform", ADMIN)
        self.assertEqual(core_counts(self.store), before)


class _EarliestLabelAddition(DevToolsExtensionsAddition):
    """Mutant: the latest-label seam reads the earliest record."""

    @staticmethod
    def _latest_label(records, key):
        return records[0][key] if records else None


class LatestLabelNegativeControlTests(unittest.TestCase):
    """Fresh negative control for the latest-label seam.

    Canonical expectation: the current reported state of an
    application (and of a document generation) is the *latest*
    record reported for it. The mutant seam reads the earliest
    record instead and must report the superseded state.
    """

    def setUp(self):
        self.ext, self.store, self.project = make_addition()
        self.mutant = _EarliestLabelAddition(self.store)
        self.mutant._applications = self.ext._applications
        self.mutant._publications = self.ext._publications
        self.mutant._doc_references = self.ext._doc_references
        self.mutant._doc_outcomes = self.ext._doc_outcomes
        self.pid = self.project["id"]

    def _traffic(self):
        app = self.ext.define_application(self.pid, "App", ADMIN, COMPONENTS)
        self.ext.record_application_publication(
            app["id"], ADMIN, status="reported_published")
        self.ext.record_application_publication(
            app["id"], ADMIN, status="reported_failed")
        return app

    def test_canonical_latest_publication_status(self):
        app = self._traffic()
        view = self.ext.application_view(app["id"])
        self.assertEqual(view["latest_publication_status"], "reported_failed")

    def test_mutant_reports_the_superseded_status(self):
        app = self._traffic()
        view = self.mutant.application_view(app["id"])
        self.assertEqual(
            view["latest_publication_status"], "reported_published")

    def test_mutant_outcome_is_not_the_canonical_expectation(self):
        app = self._traffic()
        with self.assertRaises(AssertionError):
            self.assertEqual(
                self.mutant.application_view(app["id"])
                ["latest_publication_status"],
                "reported_failed")


class AdditionCrossCuttingTests(unittest.TestCase):
    """RBAC, audit, and the derived summary across both entries."""

    def setUp(self):
        self.ext, self.store, self.project = make_addition()
        self.pid = self.project["id"]

    def test_viewer_writes_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.define_application(self.pid, "Nope", VIEWER, COMPONENTS)
        with self.assertRaises(PermissionDenied):
            self.ext.record_document_generation_reference(
                self.pid, "ssp-doc-1", VIEWER)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("build_write:denied", actions)
        self.assertIn("project_write:denied", actions)
        # Denied attempts consumed no ids.
        app = self.ext.define_application(self.pid, "Ok", ADMIN, COMPONENTS)
        self.assertEqual(app["id"], "app-1")

    def test_mutations_audited_under_the_exta_prefix(self):
        app = self.ext.define_application(self.pid, "App", ADMIN, COMPONENTS)
        self.ext.record_application_publication(app["id"], ADMIN)
        ref = self.ext.record_document_generation_reference(
            self.pid, "ssp-doc-1", ADMIN)
        self.ext.record_document_generation_outcome(
            ref["id"], "generated_by_platform", ADMIN)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("exta_application_define", actions)
        self.assertIn("exta_application_publication_record", actions)
        self.assertIn("exta_document_generation_reference", actions)
        self.assertIn("exta_document_generation_outcome", actions)

    def test_addition_summary_counts(self):
        self.assertEqual(self.ext.addition_summary()["applications"], 0)
        app = self.ext.define_application(self.pid, "App", ADMIN, COMPONENTS)
        self.ext.record_application_publication(app["id"], ADMIN)
        ref = self.ext.record_document_generation_reference(
            self.pid, "ssp-doc-1", ADMIN)
        self.ext.record_document_generation_outcome(
            ref["id"], "generated_by_platform", ADMIN)
        summary = self.ext.addition_summary()
        self.assertEqual(summary["applications"], 1)
        self.assertEqual(summary["application_publications"], 1)
        self.assertEqual(summary["document_generation_references"], 1)
        self.assertEqual(summary["document_generation_outcomes"], 1)

    def test_addition_surface_changes_only_the_audit_log_in_core(self):
        before = core_counts(self.store)
        app = self.ext.define_application(self.pid, "App", ADMIN, COMPONENTS)
        self.ext.record_application_publication(app["id"], ADMIN)
        self.assertEqual(core_counts(self.store), before)


if __name__ == "__main__":
    unittest.main()
