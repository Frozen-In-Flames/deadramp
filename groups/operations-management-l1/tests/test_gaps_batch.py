"""Final GAPS batch tests — Singleton 52, Operations Management L1.

Pins the extension surface in ``src/opsmgmt/extensions.py``
(``OpsExtensions``, wrapping the core ``OpsStore``): one test
class per open GAPS.md entry for this group (see ``../BATCH.md``
for the per-entry disposition), plus cross-cutting pins --
``ext_``-prefixed actions and ``:denied`` denials on the core
audit log, stub labels on every reference record,
derived-never-stored values (current reviewers, current payment
status, report figures, session conflicts), the founding
verbatim-only discipline for review scores (stored as reported,
never aggregated), integer-cent payment amounts, and the batch's
fresh negative control: the session-overlap derivation
``_windows_overlap``.

Fixtures: ``make_store()`` (a person, an organization, and a
project with the person as member) from ``opsmgmt_helpers``;
ADMIN=alice/admin, OPERATOR=bob/operator, VIEWER=carol/viewer.
"""

import unittest

import opsmgmt.extensions as extensions_module
from opsmgmt_helpers import ADMIN, OPERATOR, VIEWER, make_store

from opsmgmt.errors import NotFoundError, PermissionDenied, ValidationError
from opsmgmt.extensions import OpsExtensions


class ExtFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.person, self.org, self.project = make_store()
        self.ext = OpsExtensions(self.store)
        self.pid = self.person["id"]
        self.proj = self.project["id"]

    def audit_actions(self):
        return [e["action"] for e in self.store.audit.entries()]

    def make_second_person(self):
        return self.store.create_person(
            "Second Person", ADMIN, reference="EXT-1002")

    def make_form(self, fields=None, project_id=None):
        if fields is None:
            fields = [{"name": "title", "kind": "text"},
                      {"name": "track", "kind": "choice"}]
        return self.ext.create_form_definition(
            "Awards Intake", ADMIN, project_id=project_id, fields=fields)

    def make_submission(self, form=None, values=None):
        if form is None:
            form = self.make_form()
        if values is None:
            values = {"title": "entry-42", "track": "finalist"}
        return self.ext.record_submission(
            form["id"], OPERATOR, "submitter-ref-1", field_values=values)


class TestSubmissionForms(ExtFixture):
    """Entry: Submission management engine -- built as form
    definition records held as data; nothing is rendered."""

    def test_form_shape_and_labels(self):
        form = self.make_form(project_id=self.proj)
        self.assertEqual(form["id"], "frm-1")
        self.assertEqual(form["version"], 1)
        self.assertIs(form["rendered_here"], False)
        self.assertEqual(form["fields"][0]["name"], "title")
        # Returned records are copies; mutating one changes nothing.
        form["fields"].append({"name": "bogus", "kind": "x"})
        stored = self.ext.get_form_definition(form["id"], ADMIN)
        self.assertEqual(len(stored["fields"]), 2)

    def test_form_update_bumps_version(self):
        form = self.make_form()
        updated = self.ext.update_form_definition(
            form["id"], ADMIN,
            fields=[{"name": "title", "kind": "text"}])
        self.assertEqual(updated["version"], 2)
        self.assertEqual(len(updated["fields"]), 1)

    def test_form_field_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.create_form_definition(
                "Bad", ADMIN,
                fields=[{"name": "a", "kind": "text"},
                        {"name": "a", "kind": "text"}])
        with self.assertRaises(ValidationError):
            self.ext.create_form_definition(
                "Bad", ADMIN, fields=[{"name": "", "kind": "text"}])
        with self.assertRaises(ValidationError):
            self.ext.create_form_definition(
                "Bad", ADMIN, fields=[{"kind": "text"}])
        # Failed creations consume no id.
        form = self.make_form()
        self.assertEqual(form["id"], "frm-1")

    def test_form_unknown_project_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_form_definition(
                "Bad", ADMIN, project_id="proj-999")


class TestSubmissions(ExtFixture):
    """Entry: Submission management engine -- submission records
    bound to a form definition, values as labels for defined
    fields only."""

    def test_submission_shape(self):
        submission = self.make_submission()
        self.assertEqual(submission["id"], "sub-1")
        self.assertEqual(submission["status"], "recorded")
        self.assertEqual(submission["field_values"]["track"], "finalist")

    def test_submission_values_only_for_defined_fields(self):
        form = self.make_form()
        with self.assertRaises(ValidationError):
            self.ext.record_submission(
                form["id"], OPERATOR, "submitter-ref-1",
                field_values={"undefined_field": "x"})
        # The failed intake consumed no id.
        submission = self.ext.record_submission(
            form["id"], OPERATOR, "submitter-ref-1",
            field_values={"title": "ok"})
        self.assertEqual(submission["id"], "sub-1")

    def test_submission_values_are_labels_not_content(self):
        form = self.make_form()
        with self.assertRaises(ValidationError):
            self.ext.record_submission(
                form["id"], OPERATOR, "submitter-ref-1",
                field_values={"title": {"document": "body"}})
        with self.assertRaises(ValidationError):
            self.ext.record_submission(
                form["id"], OPERATOR, "submitter-ref-1",
                field_values={"title": 42})

    def test_submission_ref_is_opaque(self):
        form = self.make_form()
        with self.assertRaises(ValidationError):
            self.ext.record_submission(
                form["id"], OPERATOR, "https://example.com/person")
        with self.assertRaises(NotFoundError):
            self.ext.record_submission("frm-999", OPERATOR, "ref-1")


class TestReviewerAssignments(ExtFixture):
    """Entry: Submission management engine -- reviewer-assignment
    records; current reviewers derive at read."""

    def test_assign_and_view_derives_current_reviewers(self):
        submission = self.make_submission()
        second = self.make_second_person()
        self.ext.assign_reviewer(submission["id"], self.pid, OPERATOR)
        self.ext.assign_reviewer(submission["id"], second["id"], OPERATOR)
        view = self.ext.submission_view(submission["id"], OPERATOR)
        self.assertEqual(view["current_reviewer_ids"],
                         [self.pid, second["id"]])
        # The stored submission record carries no derived key.
        stored = self.ext.get_submission(submission["id"], OPERATOR)
        self.assertNotIn("current_reviewer_ids", stored)
        self.assertNotIn("review_count", stored)

    def test_duplicate_active_assignment_rejected(self):
        submission = self.make_submission()
        self.ext.assign_reviewer(submission["id"], self.pid, OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.assign_reviewer(submission["id"], self.pid, OPERATOR)

    def test_withdraw_frees_and_reassignment_allowed(self):
        submission = self.make_submission()
        assignment = self.ext.assign_reviewer(
            submission["id"], self.pid, OPERATOR)
        self.ext.withdraw_reviewer_assignment(assignment["id"], OPERATOR)
        view = self.ext.submission_view(submission["id"], OPERATOR)
        self.assertEqual(view["current_reviewer_ids"], [])
        again = self.ext.assign_reviewer(
            submission["id"], self.pid, OPERATOR)
        self.assertEqual(again["status"], "active")
        with self.assertRaises(ValidationError):
            self.ext.withdraw_reviewer_assignment(assignment["id"], OPERATOR)

    def test_assignment_requires_core_person_and_submission(self):
        submission = self.make_submission()
        with self.assertRaises(NotFoundError):
            self.ext.assign_reviewer(submission["id"], "per-999", OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.assign_reviewer("sub-999", self.pid, OPERATOR)


class TestReviews(ExtFixture):
    """Entry: Review & evaluation engine -- scores and feedback
    stored VERBATIM as reported; nothing is computed from them."""

    def test_review_stores_score_verbatim(self):
        submission = self.make_submission()
        review = self.ext.record_review(
            submission["id"], OPERATOR, 9, reviewer_id=self.pid,
            feedback="strong entry")
        self.assertEqual(review["id"], "rev-1")
        self.assertEqual(review["score"], 9)
        self.assertEqual(review["feedback"], "strong entry")
        self.assertIs(review["score_computed_here"], False)
        label_review = self.ext.record_review(
            submission["id"], OPERATOR, "finalist")
        self.assertEqual(label_review["score"], "finalist")

    def test_review_score_must_be_a_scalar(self):
        submission = self.make_submission()
        with self.assertRaises(ValidationError):
            self.ext.record_review(submission["id"], OPERATOR, True)
        with self.assertRaises(ValidationError):
            self.ext.record_review(submission["id"], OPERATOR, [9])
        with self.assertRaises(ValidationError):
            self.ext.record_review(submission["id"], OPERATOR, None)

    def test_reviews_are_immutable_records(self):
        # As with the core inspection records, there is no update
        # or delete API for review records.
        self.assertFalse(hasattr(self.ext, "update_review"))
        self.assertFalse(hasattr(self.ext, "delete_review"))

    def test_review_summary_is_counts_only(self):
        submission = self.make_submission()
        other = self.make_submission()
        self.ext.record_review(submission["id"], OPERATOR, 9)
        self.ext.record_review(submission["id"], OPERATOR, 3)
        self.ext.record_review(other["id"], OPERATOR, "pass")
        summary = self.ext.review_summary(ADMIN)
        self.assertEqual(summary["reviews"], 3)
        self.assertEqual(summary["reviews_by_submission"],
                         {submission["id"]: 2, other["id"]: 1})
        self.assertIs(summary["scores_aggregated"], False)
        # No aggregate/average/ranking key exists anywhere in it.
        for key in summary:
            for banned in ("average", "mean", "rank", "total_score",
                           "score"):
                if key != "scores_aggregated":
                    self.assertNotIn(banned, key)


class TestAutomatedCommunications(ExtFixture):
    """Entry: Automated communications -- template records plus
    dispatch-request records with verbatim reported outcomes;
    nothing is sent."""

    def make_template(self):
        return self.ext.create_message_template(
            "Decision Notice", ADMIN, "Your result is ready.",
            subject_label="Program decision", project_id=self.proj)

    def test_template_shape_and_versioning(self):
        template = self.make_template()
        self.assertEqual(template["id"], "msg-1")
        self.assertIs(template["rendered_here"], False)
        updated = self.ext.update_message_template(
            template["id"], ADMIN, body_text="Updated body.")
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["body_text"], "Updated body.")

    def test_dispatch_request_and_outcome(self):
        template = self.make_template()
        request = self.ext.record_dispatch_request(
            template["id"], "recipient-ref-9", OPERATOR)
        self.assertEqual(request["status"], "recorded")
        self.assertIs(request["sent_here"], False)
        outcome = self.ext.record_dispatch_outcome(
            request["id"], "reported_sent", OPERATOR)
        self.assertEqual(outcome["reported_status"], "reported_sent")
        self.assertIs(outcome["sent_here"], False)

    def test_dispatch_outcome_status_validated(self):
        template = self.make_template()
        request = self.ext.record_dispatch_request(
            template["id"], "recipient-ref-9", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_dispatch_outcome(
                request["id"], "definitely_sent", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_dispatch_request(
                template["id"], "not a ref with spaces", OPERATOR)


class TestReporting(ExtFixture):
    """Entry: Reporting -- definitions as data plus run records
    whose figures derive at read (counts and recorded sums only)."""

    def make_definition(self, metrics=None, project_id=None):
        if metrics is None:
            metrics = ["submission_count", "review_count",
                       "payment_total_cents"]
        return self.ext.create_report_definition(
            "Program Report", ADMIN, metrics, project_id=project_id)

    def test_definition_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.create_report_definition(
                "Bad", ADMIN, ["submission_count", "engagement_score"])
        with self.assertRaises(ValidationError):
            self.ext.create_report_definition("Bad", ADMIN, [])
        definition = self.make_definition()
        self.assertEqual(definition["id"], "rpd-1")
        self.assertIs(definition["computed_here"], False)

    def test_run_record_stores_no_figures(self):
        definition = self.make_definition()
        run = self.ext.record_report_run(definition["id"], OPERATOR)
        self.assertNotIn("figures", run)
        stored = self.ext.list_report_runs(ADMIN)[0]
        self.assertNotIn("figures", stored)

    def test_run_view_derives_figures_at_read(self):
        definition = self.make_definition()
        run = self.ext.record_report_run(definition["id"], OPERATOR)
        submission = self.make_submission()
        self.ext.record_review(submission["id"], OPERATOR, 8)
        self.ext.record_payment(OPERATOR, 1500, project_id=self.proj)
        view = self.ext.report_run_view(run["id"], ADMIN)
        self.assertEqual(view["figures"]["submission_count"], 1)
        self.assertEqual(view["figures"]["review_count"], 1)
        self.assertEqual(view["figures"]["payment_total_cents"], 1500)
        # Derived at read: new records change the next view of the
        # same run; nothing was stored.
        self.make_submission()
        view = self.ext.report_run_view(run["id"], ADMIN)
        self.assertEqual(view["figures"]["submission_count"], 2)

    def test_scoped_definition_counts_only_its_project(self):
        scoped = self.make_definition(metrics=["submission_count"],
                                      project_id=self.proj)
        run = self.ext.record_report_run(scoped["id"], OPERATOR)
        in_project_form = self.make_form(project_id=self.proj)
        self.ext.record_submission(in_project_form["id"], OPERATOR,
                                   "submitter-ref-1",
                                   field_values={"title": "a"})
        unscoped_form = self.make_form()
        self.ext.record_submission(unscoped_form["id"], OPERATOR,
                                   "submitter-ref-2",
                                   field_values={"title": "b"})
        view = self.ext.report_run_view(run["id"], ADMIN)
        self.assertEqual(view["figures"]["submission_count"], 1)


class TestWebsiteBuilder(ExtFixture):
    """Entry: Program website builder -- site/page definitions as
    data; nothing is published or rendered."""

    def test_site_shape_and_labels(self):
        site = self.ext.create_site_definition(
            "Program Site", ADMIN, project_id=self.proj,
            pages=[{"kind": "landing", "label": "Home"},
                   {"kind": "form", "label": "Apply"}])
        self.assertEqual(site["id"], "site-1")
        self.assertIs(site["published_here"], False)
        self.assertIs(site["rendered_here"], False)
        self.assertEqual(site["pages"][1]["label"], "Apply")

    def test_site_update_bumps_version_and_validates_pages(self):
        site = self.ext.create_site_definition("Program Site", ADMIN)
        updated = self.ext.update_site_definition(
            site["id"], ADMIN,
            pages=[{"kind": "gallery", "label": "Photos"}])
        self.assertEqual(updated["version"], 2)
        with self.assertRaises(ValidationError):
            self.ext.create_site_definition(
                "Bad", ADMIN, pages=[{"kind": "landing"}])


class TestGalleries(ExtFixture):
    """Entry: Galleries -- gallery definitions plus item records
    holding opaque media references only; nothing is hosted."""

    def test_gallery_and_item_shape(self):
        gallery = self.ext.create_gallery(
            "Ceremony Photos", OPERATOR, project_id=self.proj)
        self.assertEqual(gallery["id"], "gal-1")
        self.assertIs(gallery["hosted_here"], False)
        item = self.ext.add_gallery_item(
            gallery["id"], "media-ref-77", OPERATOR,
            caption_label="Winners")
        self.assertIs(item["hosted_here"], False)
        self.assertEqual(item["media_ref"], "media-ref-77")
        # No field on the item can hold media content.
        self.assertNotIn("content", item)
        self.assertNotIn("data", item)

    def test_gallery_item_count_derived_not_stored(self):
        gallery = self.ext.create_gallery("Photos", OPERATOR)
        self.ext.add_gallery_item(gallery["id"], "media-ref-1", OPERATOR)
        self.ext.add_gallery_item(gallery["id"], "media-ref-2", OPERATOR)
        view = self.ext.gallery_view(gallery["id"], OPERATOR)
        self.assertEqual(view["item_count"], 2)
        stored = self.ext.get_gallery(gallery["id"], OPERATOR)
        self.assertNotIn("item_count", stored)

    def test_gallery_media_ref_is_opaque(self):
        gallery = self.ext.create_gallery("Photos", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.add_gallery_item(
                gallery["id"], "https://cdn.example.com/x.jpg", OPERATOR)


class TestSessions(ExtFixture):
    """Entry: Conference session scheduling -- session records
    with conflicts derived at read from recorded times."""

    def make_session(self, title, starts, ends, room="Main Hall",
                     speaker=None):
        return self.ext.create_session(
            title, OPERATOR, starts, ends, room_label=room,
            project_id=self.proj, speaker_id=speaker)

    def test_session_shape_has_no_conflict_state(self):
        session = self.make_session(
            "Keynote", "2026-06-01T09:00:00Z", "2026-06-01T10:00:00Z")
        self.assertEqual(session["id"], "ses-1")
        self.assertNotIn("conflict", session)
        self.assertNotIn("conflicts", session)

    def test_session_window_validated(self):
        with self.assertRaises(ValidationError):
            self.make_session("Bad", "2026-06-01T10:00:00Z",
                              "2026-06-01T09:00:00Z")
        with self.assertRaises(NotFoundError):
            self.ext.create_session(
                "Bad", OPERATOR, "2026-06-01T09:00:00Z",
                "2026-06-01T10:00:00Z", speaker_id="per-999")

    def test_room_conflict_derived_at_read(self):
        self.make_session("A", "2026-06-01T09:00:00Z",
                          "2026-06-01T10:00:00Z")
        self.make_session("B", "2026-06-01T09:30:00Z",
                          "2026-06-01T10:30:00Z")
        view = self.ext.session_conflicts(ADMIN)
        self.assertEqual(view["conflict_count"], 1)
        self.assertEqual(view["conflicts"][0]["reason"], "room")
        self.assertIs(view["booked_here"], False)

    def test_adjacent_sessions_do_not_conflict(self):
        # Half-open windows: ending exactly when another begins
        # is not an overlap.
        self.make_session("A", "2026-06-01T09:00:00Z",
                          "2026-06-01T10:00:00Z")
        self.make_session("B", "2026-06-01T10:00:00Z",
                          "2026-06-01T11:00:00Z")
        view = self.ext.session_conflicts(ADMIN)
        self.assertEqual(view["conflict_count"], 0)

    def test_different_rooms_do_not_conflict(self):
        self.make_session("A", "2026-06-01T09:00:00Z",
                          "2026-06-01T10:00:00Z", room="Main Hall")
        self.make_session("B", "2026-06-01T09:30:00Z",
                          "2026-06-01T10:30:00Z", room="Annex")
        view = self.ext.session_conflicts(ADMIN)
        self.assertEqual(view["conflict_count"], 0)

    def test_speaker_conflict_derived(self):
        second = self.make_second_person()
        self.make_session("A", "2026-06-01T09:00:00Z",
                          "2026-06-01T10:00:00Z", room="Main Hall",
                          speaker=second["id"])
        self.make_session("B", "2026-06-01T09:15:00Z",
                          "2026-06-01T10:15:00Z", room="Annex",
                          speaker=second["id"])
        view = self.ext.session_conflicts(ADMIN)
        self.assertEqual(view["conflict_count"], 1)
        self.assertEqual(view["conflicts"][0]["reason"], "speaker")


class TestSessionOverlapNegativeControl(ExtFixture):
    """Fresh negative control for the batch: session conflicts
    derive at read from the recorded windows via the
    ``_windows_overlap`` seam in ``opsmgmt/extensions.py``.

    Three legs, the house form: (1) the canonical expectation
    from the real implementation, (2) the mutant (the seam
    patched to always report no overlap) would NOT produce it --
    the conflict vanishes, and (3) treating the mutant's outcome
    as the expected outcome fails.
    """

    def test_overlap_derivation_canonical_but_mutant_not(self):
        self.ext.create_session(
            "A", OPERATOR, "2026-06-01T09:00:00Z",
            "2026-06-01T10:00:00Z", room_label="Main Hall",
            project_id=self.proj)
        self.ext.create_session(
            "B", OPERATOR, "2026-06-01T09:30:00Z",
            "2026-06-01T10:30:00Z", room_label="Main Hall",
            project_id=self.proj)

        # (1) Canonical: the overlapping pair reads as one room
        # conflict.
        canonical = self.ext.session_conflicts(ADMIN)
        self.assertEqual(canonical["conflict_count"], 1)
        self.assertEqual(canonical["conflicts"][0]["reason"], "room")

        # (2) Mutant: with the seam disabled, the same records
        # derive no conflict -- the mutant would NOT produce the
        # canonical outcome.
        original = extensions_module._windows_overlap
        extensions_module._windows_overlap = (
            lambda a_start, a_end, b_start, b_end: False)
        try:
            mutant = self.ext.session_conflicts(ADMIN)
        finally:
            extensions_module._windows_overlap = original
        self.assertEqual(mutant["conflict_count"], 0)

        # (3) Treating the mutant's outcome as the expectation
        # fails.
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant["conflict_count"],
                             canonical["conflict_count"])


class TestPayments(ExtFixture):
    """Entry: Payments -- payment records over integer-cent
    amounts with verbatim reported outcomes; records, never
    execution."""

    def test_payment_shape_and_labels(self):
        payment = self.ext.record_payment(
            OPERATOR, 2500, payer_ref="payer-ref-3",
            project_id=self.proj)
        self.assertEqual(payment["id"], "pay-1")
        self.assertEqual(payment["amount_cents"], 2500)
        self.assertEqual(payment["status"], "recorded")
        self.assertIs(payment["paid_here"], False)

    def test_payment_amount_is_integer_cents_only(self):
        with self.assertRaises(ValidationError):
            self.ext.record_payment(OPERATOR, 25.0)
        with self.assertRaises(ValidationError):
            self.ext.record_payment(OPERATOR, True)
        with self.assertRaises(ValidationError):
            self.ext.record_payment(OPERATOR, 0)
        payment = self.ext.record_payment(OPERATOR, 100)
        self.assertEqual(payment["id"], "pay-1")

    def test_payment_current_status_derived_from_outcomes(self):
        payment = self.ext.record_payment(OPERATOR, 2500)
        view = self.ext.payment_view(payment["id"], OPERATOR)
        self.assertEqual(view["current_reported_status"], "recorded")
        self.ext.record_payment_outcome(
            payment["id"], "reported_paid", OPERATOR)
        view = self.ext.payment_view(payment["id"], OPERATOR)
        self.assertEqual(view["current_reported_status"], "reported_paid")
        # The stored payment record itself never changes status.
        stored = self.ext.get_payment(payment["id"], OPERATOR)
        self.assertEqual(stored["status"], "recorded")
        self.assertNotIn("current_reported_status", stored)

    def test_payments_summary_sums_recorded_cents(self):
        self.ext.record_payment(OPERATOR, 1500)
        second = self.ext.record_payment(OPERATOR, 2500)
        self.ext.record_payment_outcome(
            second["id"], "reported_failed", OPERATOR)
        summary = self.ext.payments_summary(ADMIN)
        self.assertEqual(summary["payments"], 2)
        self.assertEqual(summary["total_recorded_cents"], 4000)
        self.assertEqual(summary["outcomes_by_reported_status"],
                         {"reported_failed": 1})
        self.assertIs(summary["paid_here"], False)


class TestIntegrations(ExtFixture):
    """Entry: Third-party integrations -- labeled reference
    implementation; nothing connects or syncs."""

    def test_integration_reference_labels(self):
        reference = self.ext.register_integration_reference(
            "crm-connector-1", "api", OPERATOR, scope_ref="program-7")
        self.assertEqual(reference["id"], "int-1")
        self.assertIs(reference["reference_stub"], True)
        self.assertIs(reference["connected_here"], False)
        self.assertIs(reference["synced_here"], False)

    def test_integration_event_reference_labels(self):
        reference = self.ext.register_integration_reference(
            "crm-connector-1", "api", OPERATOR)
        event = self.ext.record_integration_event_reference(
            reference["id"], "reported_success", OPERATOR)
        self.assertIs(event["reference_stub"], True)
        self.assertIs(event["reference_transport"], True)
        self.assertIs(event["connected_here"], False)
        self.assertIs(event["synced_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.register_integration_reference(
                "bad kind", "carrier_pigeon", OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.record_integration_event_reference(
                "int-999", "reported_success", OPERATOR)


class TestCrossCutting(ExtFixture):
    """Cross-cutting pins: RBAC on the founding matrix with no
    new actions, denied attempts audited as ``ext_*:denied``,
    no-id-on-failure, copies-are-copies."""

    def test_viewer_write_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_payment(VIEWER, 100)
        self.assertIn("ext_payment_record:denied", self.audit_actions())

    def test_operator_denied_configuration_writes(self):
        # Form definitions ride workflow_write (admin-only), as
        # the core workflow registry does.
        with self.assertRaises(PermissionDenied):
            self.ext.create_form_definition("Nope", OPERATOR)
        self.assertIn("ext_form_create:denied", self.audit_actions())
        form = self.ext.create_form_definition("Ok", ADMIN)
        self.assertEqual(form["id"], "frm-1")

    def test_successful_mutations_audit_ext_actions(self):
        submission = self.make_submission()
        self.ext.record_review(submission["id"], OPERATOR, 7)
        actions = self.audit_actions()
        self.assertIn("ext_submission_record", actions)
        self.assertIn("ext_review_record", actions)

    def test_none_actor_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_payment(None, 100)

    def test_records_are_copies(self):
        gallery = self.ext.create_gallery("Photos", OPERATOR)
        gallery["name"] = "Mutated"
        stored = self.ext.get_gallery(gallery["id"], OPERATOR)
        self.assertEqual(stored["name"], "Photos")


if __name__ == "__main__":
    unittest.main()
