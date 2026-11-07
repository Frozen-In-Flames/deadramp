"""Final GAPS batch — Remainder Group 2, Learning Management L1.

Traces to: the 6 open Extended entries of the group's GAPS.md
section (idx 633-638 in gaps-batch/inventory.json) and BATCH.md's
per-entry dispositions. Pins the extension surface in
``lms/extensions.py``: the authoring environment, course posting
workflow, and system integration engines as labeled reference
records (``reference_stub: True``, state ``recorded_reference_only``);
the branded portal presentation, CE renewal-cycle, and certificate
issuance/verification surfaces as records with values derived at
read; the founding no-score/no-grade invariant over the whole
extension surface; RBAC denials consuming no id; and the fresh
mutation-verified negative controls (CE cycle coverage derivation,
portal current-presentation derivation).
"""

import unittest

from lms_helpers import (
    ADMIN,
    AUDITOR,
    INSTRUCTOR,
    LEARNER,
    fresh_store,
    make_certificate,
    make_ce_record,
    make_org_store,
    make_organization,
    make_store,
)
from lms.errors import NotFoundError, PermissionDenied, ValidationError
from lms.extensions import LmsExtensions, _validate_date


class BatchFixture(unittest.TestCase):
    """Store + learner carol + course, extension wrapping the store."""

    def setUp(self):
        self.store, self.learner, self.course = make_store()
        self.ext = LmsExtensions(self.store)


# -- idx 633: authoring environment (reference) -----------------------


class TestAuthoringReference(BatchFixture):

    def test_draft_is_labeled_reference(self):
        draft = self.ext.create_authoring_draft(
            "Anatomy 101 draft", ADMIN, course_id=self.course["id"])
        self.assertEqual(draft["id"], "dft-1")
        self.assertIs(draft["reference_stub"], True)
        self.assertEqual(draft["working_state"], "recorded_reference_only")
        self.assertEqual(draft["course_id"], self.course["id"])

    def test_draft_rejects_unknown_course(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_authoring_draft("X", ADMIN, course_id="crs-99")

    def test_draft_rejects_mismatched_content_item(self):
        other = self.store.create_course("Other Course", ADMIN)
        item = self.store.create_content_item(
            "Loose Item", "pdf", ADMIN, course_id=other["id"])
        with self.assertRaises(ValidationError):
            self.ext.create_authoring_draft(
                "X", ADMIN, course_id=self.course["id"],
                content_item_id=item["id"])

    def test_session_records_modes(self):
        draft = self.ext.create_authoring_draft("Draft", ADMIN)
        solo = self.ext.record_authoring_session(draft["id"], ADMIN,
                                                 "individual")
        team = self.ext.record_authoring_session(
            draft["id"], ADMIN, "collaborative", note="pair work")
        self.assertEqual(solo["mode"], "individual")
        self.assertEqual(team["mode"], "collaborative")
        self.assertIs(team["reference_stub"], True)
        sessions = self.ext.list_authoring_sessions(
            ADMIN, draft_id=draft["id"])
        self.assertEqual(len(sessions), 2)
        with self.assertRaises(ValidationError):
            self.ext.record_authoring_session(draft["id"], ADMIN, "group")

    def test_check_outcome_is_caller_reported(self):
        draft = self.ext.create_authoring_draft("Draft", ADMIN)
        check = self.ext.record_authoring_check(
            draft["id"], ADMIN, "section_508", "tool reports conformance")
        self.assertEqual(check["outcome"], "tool reports conformance")
        self.assertEqual(check["outcome_basis"], "caller_reported")
        self.assertIs(check["reference_stub"], True)
        with self.assertRaises(ValidationError):
            self.ext.record_authoring_check(
                draft["id"], ADMIN, "spellcheck", "ok")

    def test_authoring_surface_leaves_core_untouched(self):
        before = self.store.report(ADMIN, as_of="2026-06-01")
        draft = self.ext.create_authoring_draft(
            "Draft", ADMIN, course_id=self.course["id"])
        self.ext.record_authoring_session(draft["id"], ADMIN, "individual")
        self.ext.record_authoring_check(draft["id"], ADMIN,
                                        "plugin_review", "reported ok")
        after = self.store.report(ADMIN, as_of="2026-06-01")
        self.assertEqual(before, after)


# -- idx 634: course posting & publication workflow (reference) -------


class TestPublicationReference(BatchFixture):

    def test_publication_record_is_labeled_reference(self):
        record = self.ext.create_publication_record(
            self.course["id"], "community_catalog", ADMIN)
        self.assertEqual(record["id"], "pub-1")
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertIs(record["published_here"], False)

    def test_portal_channel_requires_resolving_org(self):
        with self.assertRaises(ValidationError):
            self.ext.create_publication_record(
                self.course["id"], "organization_portal", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.create_publication_record(
                self.course["id"], "organization_portal", ADMIN,
                target_org_ref="nope")
        make_organization(self.store)
        record = self.ext.create_publication_record(
            self.course["id"], "organization_portal", ADMIN,
            target_org_ref="acme")
        self.assertEqual(record["target_org_ref"], "acme")

    def test_publication_changes_no_core_record(self):
        before = self.store.get_course(self.course["id"], actor=ADMIN)
        self.ext.create_publication_record(
            self.course["id"], "external_link", ADMIN)
        after = self.store.get_course(self.course["id"], actor=ADMIN)
        self.assertEqual(before, after)

    def test_invalid_channel_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_publication_record(
                self.course["id"], "billboard", ADMIN)


# -- idx 635: branded portal presentation (built) ----------------------


class TestPortalPresentation(unittest.TestCase):

    def setUp(self):
        self.store, self.organization, self.learner = make_org_store()
        self.ext = LmsExtensions(self.store)

    def test_presentation_is_data_with_rendered_here_false(self):
        view = self.ext.create_portal_presentation(
            "acme", ADMIN, "Acme Health Portal", theme="teal",
            menu_labels=["Courses", "My Certificates"])
        self.assertEqual(view["id"], "ppr-1")
        self.assertIs(view["rendered_here"], False)
        self.assertEqual(view["revision_count"], 0)
        self.assertEqual(view["current"]["brand_label"],
                         "Acme Health Portal")
        self.assertEqual(view["current"]["menu_labels"],
                         ["Courses", "My Certificates"])

    def test_current_presentation_is_latest_revision(self):
        view = self.ext.create_portal_presentation(
            "acme", ADMIN, "Old Brand", theme="blue")
        revised = self.ext.revise_portal_presentation(
            view["id"], ADMIN, "New Brand", theme="green",
            menu_labels=["Home"], note="rebrand")
        self.assertEqual(revised["revision_count"], 1)
        self.assertEqual(revised["current"]["brand_label"], "New Brand")
        self.assertEqual(revised["current"]["theme"], "green")
        fetched = self.ext.get_portal_presentation(view["id"], ADMIN)
        self.assertEqual(fetched["current"]["brand_label"], "New Brand")

    def test_presentation_requires_known_org_and_is_unique(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_portal_presentation("nope", ADMIN, "Brand")
        self.ext.create_portal_presentation("acme", ADMIN, "Brand")
        with self.assertRaises(ValidationError):
            self.ext.create_portal_presentation("acme", ADMIN, "Again")

    def test_presentation_write_is_admin_only(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_portal_presentation(
                "acme", INSTRUCTOR, "Brand")
        view = self.ext.create_portal_presentation("acme", ADMIN, "Brand")
        with self.assertRaises(PermissionDenied):
            self.ext.revise_portal_presentation(
                view["id"], INSTRUCTOR, "Other")

    def test_core_organization_record_unchanged(self):
        before = self.store.get_organization(
            self.organization["id"], actor=ADMIN)
        view = self.ext.create_portal_presentation("acme", ADMIN, "Brand")
        self.ext.revise_portal_presentation(view["id"], ADMIN, "Brand 2")
        after = self.store.get_organization(
            self.organization["id"], actor=ADMIN)
        self.assertEqual(before, after)


# -- idx 636: continuing education management engine (built) -----------


def canonical_ce_expectations(case, ext, as_of="2026-06-01"):
    """Canonical CE derivation expectations, run against any surface.

    The fixture (built by the caller): carol's cycle over 2026 with
    one in-period core CE record reads ``satisfied`` with the credit
    text verbatim; a second learner's empty cycle over the same
    period reads ``open`` at the same as_of and ``lapsed`` after the
    period ends.
    """
    view = ext.get_ce_cycle("crc-1", ADMIN, as_of=as_of)
    case.assertEqual(view["status"], "satisfied")
    case.assertEqual(view["recorded_record_count"], 1)
    case.assertEqual(view["covered_activity_refs"], ["act-1"])
    case.assertEqual(view["credit_texts"], ["3.5 credits"])
    empty = ext.get_ce_cycle("crc-2", ADMIN, as_of=as_of)
    case.assertEqual(empty["status"], "open")
    late = ext.get_ce_cycle("crc-2", ADMIN, as_of="2027-02-01")
    case.assertEqual(late["status"], "lapsed")


class TestContinuingEducationEngine(BatchFixture):

    def _cycles(self):
        self.store.create_learner("erin", "Erin Learner", ADMIN)
        cycle = self.ext.create_ce_cycle(
            "carol", "Annual CE requirement", INSTRUCTOR,
            "2026-01-01", "2026-12-31", "6 credits")
        empty = self.ext.create_ce_cycle(
            "erin", "Annual CE requirement", INSTRUCTOR,
            "2026-01-01", "2026-12-31", "6 credits")
        return cycle, empty

    def test_cycle_status_derived_from_core_records(self):
        self._cycles()
        make_ce_record(self.store, recorded_on="2026-03-01")
        canonical_ce_expectations(self, self.ext)

    def test_cycle_view_carries_credit_text_verbatim_only(self):
        self._cycles()
        make_ce_record(self.store, recorded_on="2026-03-01")
        view = self.ext.get_ce_cycle("crc-1", ADMIN, as_of="2026-06-01")
        self.assertEqual(view["required_credit_text"], "6 credits")
        for key, value in view.items():
            if "credit" in key:
                self.assertNotIsInstance(value, (int, float), key)
        self.assertTrue(
            all(isinstance(t, str) for t in view["credit_texts"]))

    def test_out_of_period_and_undated_records(self):
        self._cycles()
        make_ce_record(self.store, activity_ref="act-old",
                       recorded_on="2025-06-01")
        view = self.ext.get_ce_cycle("crc-1", ADMIN, as_of="2026-06-01")
        self.assertEqual(view["status"], "open")
        self.assertEqual(view["recorded_record_count"], 0)
        make_ce_record(self.store, activity_ref="act-undated",
                       recorded_on=None)
        view = self.ext.get_ce_cycle("crc-1", ADMIN, as_of="2026-06-01")
        self.assertEqual(view["status"], "satisfied")
        self.assertEqual(view["covered_activity_refs"], ["act-undated"])

    def test_cycle_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.create_ce_cycle(
                "carol", "Req", INSTRUCTOR,
                "2026-12-31", "2026-01-01", "6 credits")
        with self.assertRaises(NotFoundError):
            self.ext.create_ce_cycle(
                "ghost", "Req", INSTRUCTOR,
                "2026-01-01", "2026-12-31", "6 credits")

    def test_cycle_learner_scope(self):
        self._cycles()
        with self.assertRaises(PermissionDenied):
            self.ext.get_ce_cycle("crc-2", LEARNER, as_of="2026-06-01")
        mine = self.ext.list_ce_cycles(LEARNER, as_of="2026-06-01")
        self.assertEqual([v["learner_ref"] for v in mine], ["carol"])


# -- idx 637: certificate issuance & verification service (built) ------


class TestCertificateService(BatchFixture):

    def test_issuance_record_binds_core_award(self):
        cert = make_certificate(self.store, course_id=self.course["id"])
        record = self.ext.create_issuance_record(
            cert["id"], INSTRUCTOR, "portal")
        self.assertEqual(record["id"], "iss-1")
        self.assertEqual(record["learner_ref"], "carol")
        self.assertEqual(record["state"], "recorded")
        self.assertIs(record["issued_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.create_issuance_record(cert["id"], INSTRUCTOR, "fax")
        with self.assertRaises(NotFoundError):
            self.ext.create_issuance_record("crt-99", INSTRUCTOR, "portal")

    def test_verification_outcome_is_verbatim_not_verified(self):
        cert = make_certificate(self.store)
        query = self.ext.record_verification_query(
            cert["id"], INSTRUCTOR, "presented_by_holder")
        self.assertEqual(query["outcome_label"], "presented_by_holder")
        self.assertIs(query["verified_here"], False)

    def test_service_view_derives_counts_and_leaves_core_untouched(self):
        cert = make_certificate(self.store)
        before = self.store.get_certificate(cert["id"], actor=ADMIN)
        self.ext.create_issuance_record(cert["id"], INSTRUCTOR, "email")
        self.ext.create_issuance_record(cert["id"], INSTRUCTOR, "print")
        self.ext.record_verification_query(
            cert["id"], INSTRUCTOR, "presented_by_holder")
        view = self.ext.certificate_service_view(cert["id"], ADMIN)
        self.assertEqual(view["issuance_count"], 2)
        self.assertEqual(view["verification_count"], 1)
        after = self.store.get_certificate(cert["id"], actor=ADMIN)
        self.assertEqual(before, after)
        self.assertEqual(view["certificate"], before)

    def test_service_view_respects_learner_scope(self):
        self.store.create_learner("erin", "Erin Learner", ADMIN)
        cert = make_certificate(self.store, learner_ref="erin")
        with self.assertRaises(PermissionDenied):
            self.ext.certificate_service_view(cert["id"], LEARNER)


# -- idx 638: system integration engines (reference) -------------------


class TestIntegrationReference(BatchFixture):

    def test_integration_record_is_labeled_reference(self):
        record = self.ext.create_integration_record(
            "ehr-system", "outbound", INSTRUCTOR, note="EHRI-adjacent HRIS")
        self.assertEqual(record["id"], "int-1")
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["state"], "recorded_reference_only")
        with self.assertRaises(ValidationError):
            self.ext.create_integration_record("x", "sideways", INSTRUCTOR)

    def test_sync_report_is_caller_reported(self):
        record = self.ext.create_integration_record("lrs-peer", "inbound",
                                                    INSTRUCTOR)
        report = self.ext.record_sync_report(
            record["id"], INSTRUCTOR, "reported_complete", record_count=42)
        self.assertEqual(report["outcome_label"], "reported_complete")
        self.assertEqual(report["record_count"], 42)
        self.assertIs(report["reference_stub"], True)
        with self.assertRaises(ValidationError):
            self.ext.record_sync_report(
                record["id"], INSTRUCTOR, "ok", record_count=True)
        with self.assertRaises(NotFoundError):
            self.ext.record_sync_report("int-99", INSTRUCTOR, "ok")

    def test_integrations_change_no_core_record(self):
        before = self.store.report(ADMIN, as_of="2026-06-01")
        record = self.ext.create_integration_record("x", "bidirectional",
                                                    INSTRUCTOR)
        self.ext.record_sync_report(record["id"], INSTRUCTOR, "ok")
        after = self.store.report(ADMIN, as_of="2026-06-01")
        self.assertEqual(before, after)


# -- cross-cutting ------------------------------------------------------


def _scan_keys(value, found):
    if isinstance(value, dict):
        for key, item in value.items():
            found.append(key)
            _scan_keys(item, found)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _scan_keys(item, found)


class TestCrossCutting(BatchFixture):

    def _all_surfaces(self):
        store, organization, learner = make_org_store()
        ext = LmsExtensions(store)
        course = store.create_course("Safety Basics", ADMIN)
        cert = make_certificate(store, course_id=course["id"])
        make_ce_record(store, recorded_on="2026-03-01")
        draft = ext.create_authoring_draft("D", ADMIN,
                                           course_id=course["id"])
        surfaces = [
            draft,
            ext.record_authoring_session(draft["id"], ADMIN, "individual"),
            ext.record_authoring_check(draft["id"], ADMIN,
                                       "section_508", "reported"),
            ext.create_publication_record(course["id"],
                                          "community_catalog", ADMIN),
            ext.create_portal_presentation("acme", ADMIN, "Brand"),
            ext.create_ce_cycle("carol", "Req", INSTRUCTOR,
                                "2026-01-01", "2026-12-31", "6 credits"),
            ext.get_ce_cycle("crc-1", ADMIN, as_of="2026-06-01"),
            ext.create_issuance_record(cert["id"], INSTRUCTOR, "portal"),
            ext.record_verification_query(cert["id"], INSTRUCTOR,
                                          "presented_by_holder"),
            ext.certificate_service_view(cert["id"], ADMIN),
            ext.create_integration_record("sys", "inbound", INSTRUCTOR),
        ]
        surfaces.append(ext.record_sync_report("int-1", INSTRUCTOR, "ok"))
        surfaces.append(ext.list_portal_presentations(ADMIN))
        surfaces.append(ext.list_ce_cycles(ADMIN, as_of="2026-06-01"))
        return surfaces

    def test_no_score_or_grade_key_anywhere(self):
        keys = []
        for surface in self._all_surfaces():
            _scan_keys(surface, keys)
        self.assertTrue(keys)
        for key in keys:
            lowered = key.lower()
            self.assertNotIn("score", lowered, key)
            self.assertNotIn("grade", lowered, key)

    def test_every_mutation_audits_with_ext_prefix(self):
        draft = self.ext.create_authoring_draft("D", ADMIN)
        self.ext.create_integration_record("sys", "inbound", INSTRUCTOR)
        actions = [e["action"] for e in self.store.audit.entries()
                   if e["action"].startswith("ext_")]
        self.assertIn("ext_authoring_draft_create", actions)
        self.assertIn("ext_integration_record_create", actions)
        self.assertTrue(draft["id"])

    def test_denied_writes_consume_no_id(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_authoring_draft("D", LEARNER)
        with self.assertRaises(PermissionDenied):
            self.ext.create_integration_record("sys", "inbound", AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.create_ce_cycle("carol", "Req", LEARNER,
                                     "2026-01-01", "2026-12-31", "6")
        draft = self.ext.create_authoring_draft("D", ADMIN)
        record = self.ext.create_integration_record("sys", "inbound",
                                                    INSTRUCTOR)
        cycle = self.ext.create_ce_cycle("carol", "Req", INSTRUCTOR,
                                         "2026-01-01", "2026-12-31", "6")
        self.assertEqual(draft["id"], "dft-1")
        self.assertEqual(record["id"], "int-1")
        self.assertEqual(cycle["id"], "crc-1")


# -- fresh negative controls (mutation-verified) ------------------------


class MutantCeExtensions(LmsExtensions):
    """Mutant: the coverage branch of the CE derivation is inverted.

    A cycle WITH a qualifying core CE record reads as uncovered, and
    a cycle with none reads satisfied — the canonical expectations
    must fail against this surface.
    """

    def _derive_ce_cycle_status(self, cycle, as_of_date):
        qualifying = self._qualifying_ce_records(cycle)
        if not qualifying:
            return "satisfied"
        end = _validate_date(cycle["period_end"], "period_end")
        if as_of_date > end:
            return "lapsed"
        return "open"


class MutantPortalExtensions(LmsExtensions):
    """Mutant: the current presentation ignores revisions entirely."""

    def _current_presentation(self, record):
        return {
            "brand_label": record["brand_label"],
            "theme": record["theme"],
            "menu_labels": list(record["menu_labels"]),
        }


class TestNegativeControl(unittest.TestCase):

    def _fixture(self, ext_class):
        store, learner, course = make_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        ext = ext_class(store)
        ext.create_ce_cycle("carol", "Annual CE requirement", INSTRUCTOR,
                            "2026-01-01", "2026-12-31", "6 credits")
        ext.create_ce_cycle("erin", "Annual CE requirement", INSTRUCTOR,
                            "2026-01-01", "2026-12-31", "6 credits")
        make_ce_record(store, recorded_on="2026-03-01")
        return store, ext

    def test_ce_canonical_expectations_hold_on_real_surface(self):
        _, ext = self._fixture(LmsExtensions)
        canonical_ce_expectations(self, ext)

    def test_ce_mutant_fails_canonical_expectations(self):
        _, ext = self._fixture(MutantCeExtensions)
        with self.assertRaises(AssertionError):
            canonical_ce_expectations(self, ext)

    def test_portal_mutant_fails_freshness_expectation(self):
        store, organization, learner = make_org_store()
        real = LmsExtensions(store)
        view = real.create_portal_presentation("acme", ADMIN, "Old Brand")
        real.revise_portal_presentation(view["id"], ADMIN, "New Brand")
        self.assertEqual(
            real.get_portal_presentation(view["id"], ADMIN)
            ["current"]["brand_label"], "New Brand")

        store2, organization2, learner2 = make_org_store()
        mutant = MutantPortalExtensions(store2)
        view2 = mutant.create_portal_presentation("acme", ADMIN,
                                                  "Old Brand")
        mutant.revise_portal_presentation(view2["id"], ADMIN, "New Brand")
        with self.assertRaises(AssertionError):
            self.assertEqual(
                mutant.get_portal_presentation(view2["id"], ADMIN)
                ["current"]["brand_label"], "New Brand")


if __name__ == "__main__":
    unittest.main()
