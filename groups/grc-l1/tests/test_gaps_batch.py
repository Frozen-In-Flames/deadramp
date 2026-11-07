"""Final GAPS batch tests — Singleton 43 (GRC L1).

Pins the extension surface in ``src/grc/extensions.py`` against
the group's 4 open Extended entries (see ``../BATCH.md``):

- Questionnaire automation engine (idx 415) — reference:
  definitions holding questions as data, responses verbatim;
  nothing administered, no answer reused.
- Trust Center publication (idx 416) — built: publication
  records storing no figures, release records verbatim, and a
  view derived at read from the core's records.
- Vendor risk assessment engine (idx 417) — reference: rules
  held as data and never applied; reported outcomes and values
  verbatim; nothing evaluated or computed.
- Continuous-monitoring engine & evidence-collection
  integrations (idx 418) — reference: source definitions,
  observation intake (monitored_here: False) creating no core
  indicator result, collection runs creating no core evidence.

Plus the batch's fresh negative control: the latest-label seam
``_latest_label`` — a mutant that reads the earliest record
must misstate every derived "latest" label.
"""

import unittest

import grc_helpers as helpers
from grc.audit import AuditLog
from grc.errors import NotFoundError, PermissionDenied, ValidationError
from grc.extensions import GrcExtensions

ADMIN = helpers.ADMIN
MEMBER = helpers.MEMBER
VIEWER = helpers.VIEWER
SYSTEM_REF = helpers.SYSTEM_REF


def make_ext():
    """Fresh core store + audit + system, plus the extension."""
    audit = AuditLog()
    store, system, indicator = helpers.make_store(audit=audit)
    return store, audit, system, GrcExtensions(store)


FORBIDDEN_KEY_PARTS = ("score", "rating", "grade", "percent")


def assert_no_score_keys(case, node, path="$"):
    """Recursive scan (the founding suite's invariant): no key
    anywhere mentions score / rating / grade / percent."""
    if isinstance(node, dict):
        for key, value in node.items():
            lowered = str(key).lower()
            for part in FORBIDDEN_KEY_PARTS:
                case.assertNotIn(
                    part, lowered,
                    "forbidden key part %r at %s.%s" % (part, path, key))
            assert_no_score_keys(case, value, "%s.%s" % (path, key))
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            assert_no_score_keys(case, value, "%s[%d]" % (path, index))


class TestQuestionnairesReference(unittest.TestCase):
    """Idx 415 — definitions as data, responses verbatim;
    nothing administered, no answer reused."""

    def setUp(self):
        self.store, self.audit, self.system, self.ext = make_ext()

    def test_definition_shape_and_stub_labels(self):
        qnr = self.ext.create_questionnaire(
            SYSTEM_REF, "Annual security questionnaire", MEMBER,
            questions=["Is MFA enforced?", "Are backups tested?"])
        self.assertEqual(qnr["id"], "qnr-1")
        self.assertEqual(set(qnr), {
            "id", "system_ref", "title", "questions", "note",
            "reference_stub", "administered_here", "reuse_applied_here",
            "created_by", "created_utc"})
        self.assertTrue(qnr["reference_stub"])
        self.assertFalse(qnr["administered_here"])
        self.assertFalse(qnr["reuse_applied_here"])
        # The questions are data on the record, verbatim.
        self.assertEqual(
            qnr["questions"], ["Is MFA enforced?", "Are backups tested?"])
        self.assertNotIn("response_count", qnr)

    def test_unknown_system_rejected_and_no_id_consumed(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_questionnaire("SYS-404", "x", MEMBER)
        qnr = self.ext.create_questionnaire(SYSTEM_REF, "x", MEMBER)
        self.assertEqual(qnr["id"], "qnr-1")

    def test_response_verbatim_and_view_derives(self):
        qnr = self.ext.create_questionnaire(SYSTEM_REF, "Q", MEMBER)
        first = self.ext.record_questionnaire_response(
            qnr["id"], "in_progress", MEMBER, respondent_ref="VENDOR-7",
            answers={"mfa_enforced": "yes, since March"})
        self.assertEqual(first["id"], "qrs-1")
        self.assertTrue(first["reference_stub"])
        self.assertEqual(first["answers"], {"mfa_enforced": "yes, since March"})
        self.ext.record_questionnaire_response(qnr["id"], "submitted", MEMBER)
        view = self.ext.questionnaire_view(qnr["id"], ADMIN)
        self.assertTrue(view["derived"])
        self.assertEqual(view["response_count"], 2)
        self.assertEqual(
            view["responses_by_status"],
            {"in_progress": 1, "submitted": 1})
        self.assertEqual(view["latest_response_status"], "submitted")
        # The stored definition carries no derived key.
        stored = self.ext.get_questionnaire(qnr["id"], ADMIN)
        self.assertNotIn("response_count", stored)
        self.assertNotIn("latest_response_status", stored)

    def test_unknown_questionnaire_response_consumes_no_id(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_questionnaire_response("qnr-99", "submitted",
                                                   MEMBER)
        qnr = self.ext.create_questionnaire(SYSTEM_REF, "Q", MEMBER)
        response = self.ext.record_questionnaire_response(
            qnr["id"], "submitted", MEMBER)
        self.assertEqual(response["id"], "qrs-1")

    def test_bad_answers_rejected(self):
        qnr = self.ext.create_questionnaire(SYSTEM_REF, "Q", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_questionnaire_response(
                qnr["id"], "submitted", MEMBER, answers={"q": 42})
        with self.assertRaises(ValidationError):
            self.ext.record_questionnaire_response(
                qnr["id"], "submitted", MEMBER, answers=["not-a-mapping"])


class TestPublicationsBuilt(unittest.TestCase):
    """Idx 416 — the stored record holds no figures; the view
    derives the published posture at read."""

    def setUp(self):
        self.store, self.audit, self.system, self.ext = make_ext()

    def test_stored_record_exact_keys_no_figures(self):
        pub = self.ext.create_publication(SYSTEM_REF, "Trust Center", MEMBER)
        self.assertEqual(pub["id"], "pub-1")
        self.assertEqual(set(pub), {
            "id", "system_ref", "title", "note", "published_here",
            "exported_here", "created_by", "created_utc"})
        self.assertFalse(pub["published_here"])
        self.assertFalse(pub["exported_here"])
        self.assertNotIn("reference_stub", pub)

    def test_view_derives_posture_and_tracks_registry_state(self):
        pub = self.ext.create_publication(SYSTEM_REF, "Trust Center", MEMBER)
        empty = self.ext.publication_view(pub["id"], ADMIN, as_of="2026-07-01")
        self.assertTrue(empty["derived"])
        self.assertEqual(empty["posture"]["findings"]["total"], 0)
        self.assertEqual(empty["system_name"], helpers.SYSTEM_NAME)
        finding = helpers.make_finding(self.store)
        view = self.ext.publication_view(pub["id"], ADMIN, as_of="2026-07-01")
        self.assertEqual(view["posture"]["findings"]["total"], 1)
        self.assertEqual(view["posture"]["findings"]["overdue"], 1)
        # The core finding itself is untouched by the view.
        self.assertEqual(
            self.store.get_finding(finding["id"], ADMIN)["status"], "open")
        # The stored publication record never gained a figure.
        stored = self.ext.get_publication(pub["id"], ADMIN)
        self.assertNotIn("posture", stored)
        self.assertNotIn("findings", stored)

    def test_releases_verbatim_and_view_derives_latest(self):
        pub = self.ext.create_publication(SYSTEM_REF, "Trust Center", MEMBER)
        first = self.ext.record_publication_release(
            pub["id"], "2026-Q1 review", MEMBER)
        self.assertEqual(first["id"], "prl-1")
        self.assertNotIn("reference_stub", first)
        self.ext.record_publication_release(pub["id"], "2026-Q2 review",
                                            MEMBER)
        view = self.ext.publication_view(pub["id"], ADMIN)
        self.assertEqual(view["release_count"], 2)
        self.assertEqual(view["latest_release_label"], "2026-Q2 review")
        stored = self.ext.get_publication(pub["id"], ADMIN)
        self.assertNotIn("release_count", stored)
        self.assertNotIn("latest_release_label", stored)


class TestVendorAssessmentReference(unittest.TestCase):
    """Idx 417 — rules as data, never applied; outcomes and
    values verbatim; nothing evaluated or computed."""

    def setUp(self):
        self.store, self.audit, self.system, self.ext = make_ext()

    def test_rule_shape_and_never_applied(self):
        rule = self.ext.create_vendor_rule(
            "Critical vendor bar", "Vendor must report MFA coverage.",
            MEMBER, system_ref=SYSTEM_REF)
        self.assertEqual(rule["id"], "vru-1")
        self.assertEqual(rule["method"], "recorded_rules_only")
        self.assertTrue(rule["reference_stub"])
        self.assertFalse(rule["applied_here"])
        self.assertEqual(rule["rule_text"], "Vendor must report MFA coverage.")
        before = self.ext.get_vendor_rule(rule["id"], ADMIN)
        self.ext.record_vendor_assessment(
            SYSTEM_REF, "reported pass", MEMBER, rule_id=rule["id"])
        # Recording an assessment never applies or alters the rule.
        self.assertEqual(self.ext.get_vendor_rule(rule["id"], ADMIN), before)

    def test_assessment_verbatim_and_creates_no_core_finding(self):
        record = self.ext.record_vendor_assessment(
            SYSTEM_REF, "Meets bar (assessor wording)", MEMBER,
            reported_label="Tier 2 per assessor", assessor_ref="ASSESSOR-9")
        self.assertEqual(record["id"], "vas-1")
        self.assertTrue(record["reference_stub"])
        self.assertFalse(record["evaluated_here"])
        self.assertFalse(record["computed_here"])
        self.assertEqual(record["outcome"], "Meets bar (assessor wording)")
        self.assertEqual(record["reported_label"], "Tier 2 per assessor")
        # The engine's records land nowhere in the core: no finding,
        # and the core posture is unchanged.
        self.assertEqual(self.store.list_findings(MEMBER), [])
        self.assertEqual(
            self.store.posture_summary(MEMBER)["findings"]["total"], 0)

    def test_summary_counts_verbatim_labels_only(self):
        self.ext.record_vendor_assessment(SYSTEM_REF, "pass", MEMBER,
                                          reported_label="Tier 2")
        self.ext.record_vendor_assessment(SYSTEM_REF, "pass", MEMBER,
                                          reported_label="Tier 2")
        self.ext.record_vendor_assessment(SYSTEM_REF, "watch", MEMBER)
        summary = self.ext.vendor_assessment_summary(ADMIN)
        self.assertEqual(summary["vendor_assessments_total"], 3)
        self.assertEqual(summary["by_outcome"], {"pass": 2, "watch": 1})
        self.assertEqual(summary["by_reported_label"], {"Tier 2": 2})

    def test_unknown_system_and_rule_rejected_no_id_consumed(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_vendor_assessment("SYS-404", "pass", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_vendor_assessment(
                SYSTEM_REF, "pass", MEMBER, rule_id="vru-99")
        record = self.ext.record_vendor_assessment(SYSTEM_REF, "pass", MEMBER)
        self.assertEqual(record["id"], "vas-1")


class TestMonitoringReference(unittest.TestCase):
    """Idx 418 — source definitions, observation intake creating
    no core indicator result, collection runs creating no core
    evidence."""

    def setUp(self):
        self.store, self.audit, self.system, self.ext = make_ext()

    def test_source_shape_and_stub_labels(self):
        source = self.ext.register_collection_source(
            "api", SYSTEM_REF, "config API feed", MEMBER)
        self.assertEqual(source["id"], "csrc-1")
        self.assertTrue(source["reference_stub"])
        self.assertTrue(source["reference_transport"])
        self.assertFalse(source["connected_here"])
        self.assertFalse(source["collected_here"])
        with self.assertRaises(ValidationError):
            self.ext.register_collection_source(
                "carrier_pigeon", SYSTEM_REF, "x", MEMBER)

    def test_observation_intake_creates_no_core_result(self):
        source = self.ext.register_collection_source(
            "telemetry", SYSTEM_REF, "telemetry feed", MEMBER)
        obs = self.ext.record_monitoring_observation(
            source["id"], "All Controls Green-ish", MEMBER, control_id="CA-7")
        self.assertEqual(obs["id"], "obs-1")
        self.assertTrue(obs["reference_stub"])
        self.assertFalse(obs["monitored_here"])
        self.assertEqual(obs["status"], "All Controls Green-ish")
        self.assertEqual(obs["system_ref"], SYSTEM_REF)
        # Intake is a record of a report: the core's indicator
        # results are recorded by a person, through the core.
        self.assertEqual(self.store.list_indicator_results(MEMBER), [])

    def test_observation_unknown_control_rejected_no_id_consumed(self):
        source = self.ext.register_collection_source(
            "api", SYSTEM_REF, "feed", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_monitoring_observation(
                source["id"], "ok", MEMBER, control_id="ZZ-9")
        obs = self.ext.record_monitoring_observation(source["id"], "ok",
                                                     MEMBER)
        self.assertEqual(obs["id"], "obs-1")

    def test_collection_run_creates_no_core_evidence(self):
        source = self.ext.register_collection_source(
            "api", SYSTEM_REF, "evidence API", MEMBER)
        run = self.ext.record_collection_run(
            source["id"], "completed (collector wording)", MEMBER,
            artifact_count=12)
        self.assertEqual(run["id"], "crun-1")
        self.assertTrue(run["reference_stub"])
        self.assertTrue(run["reference_transport"])
        self.assertFalse(run["collected_here"])
        self.assertEqual(run["artifact_count"], 12)
        for bad in (True, 1.5, -1):
            with self.assertRaises(ValidationError):
                self.ext.record_collection_run(
                    source["id"], "x", MEMBER, artifact_count=bad)
        # Nothing was collected into the core registry.
        self.assertEqual(self.store.list_evidence(MEMBER), [])

    def test_source_view_derives_counts_and_latest(self):
        source = self.ext.register_collection_source(
            "api", SYSTEM_REF, "feed", MEMBER)
        empty = self.ext.collection_source_view(source["id"], ADMIN)
        self.assertEqual(empty["observation_count"], 0)
        self.assertIsNone(empty["latest_observation_status"])
        self.ext.record_monitoring_observation(source["id"], "degraded",
                                               MEMBER)
        self.ext.record_monitoring_observation(source["id"], "nominal",
                                               MEMBER)
        self.ext.record_collection_run(source["id"], "done", MEMBER,
                                       artifact_count=3)
        self.ext.record_collection_run(source["id"], "done", MEMBER,
                                       artifact_count=4)
        view = self.ext.collection_source_view(source["id"], ADMIN)
        self.assertTrue(view["derived"])
        self.assertEqual(view["observation_count"], 2)
        self.assertEqual(
            view["observations_by_status"], {"degraded": 1, "nominal": 1})
        self.assertEqual(view["latest_observation_status"], "nominal")
        self.assertEqual(view["collection_run_count"], 2)
        # A sum of *reported* counts, stated as such.
        self.assertEqual(view["reported_artifacts_total"], 7)
        stored = self.ext.get_collection_source(source["id"], ADMIN)
        self.assertNotIn("observation_count", stored)
        self.assertNotIn("latest_observation_status", stored)


class TestExtensionInvariants(unittest.TestCase):
    """Cross-cutting doctrine pins over the whole new surface."""

    def setUp(self):
        self.store, self.audit, self.system, self.ext = make_ext()
        qnr = self.ext.create_questionnaire(
            SYSTEM_REF, "Q", MEMBER, questions=["MFA?"])
        self.ext.record_questionnaire_response(
            qnr["id"], "submitted", MEMBER, answers={"mfa": "yes"})
        pub = self.ext.create_publication(SYSTEM_REF, "Trust Center", MEMBER)
        self.ext.record_publication_release(pub["id"], "2026-Q2", MEMBER)
        self.ext.create_vendor_rule("bar", "rule text", MEMBER)
        self.ext.record_vendor_assessment(
            SYSTEM_REF, "pass", MEMBER, reported_label="Tier 2")
        source = self.ext.register_collection_source(
            "api", SYSTEM_REF, "feed", MEMBER)
        self.ext.record_monitoring_observation(source["id"], "nominal",
                                               MEMBER)
        self.ext.record_collection_run(source["id"], "done", MEMBER,
                                       artifact_count=2)
        self.qnr, self.pub, self.source = qnr, pub, source

    def test_no_score_keys_anywhere_on_the_surface(self):
        surface = [
            self.ext.list_questionnaires(ADMIN),
            self.ext.questionnaire_view(self.qnr["id"], ADMIN),
            self.ext.list_questionnaire_responses(self.qnr["id"], ADMIN),
            self.ext.get_publication(self.pub["id"], ADMIN),
            self.ext.publication_view(self.pub["id"], ADMIN,
                                      as_of="2026-07-01"),
            self.ext.list_publication_releases(self.pub["id"], ADMIN),
            self.ext.list_vendor_rules(ADMIN),
            self.ext.list_vendor_assessments(ADMIN),
            self.ext.vendor_assessment_summary(ADMIN),
            self.ext.list_collection_sources(ADMIN),
            self.ext.collection_source_view(self.source["id"], ADMIN),
            self.ext.extension_summary(ADMIN),
            # The core posture the publication view embeds is held
            # to the same founding invariant.
            self.store.posture_summary(ADMIN),
        ]
        for node in surface:
            assert_no_score_keys(self, node)

    def test_extension_writes_audited_under_ext_actions(self):
        actions = [e["action"] for e in self.audit.entries()]
        for expected in (
                "ext_questionnaire_create",
                "ext_questionnaire_response_record",
                "ext_publication_create",
                "ext_publication_release_record",
                "ext_vendor_rule_create",
                "ext_vendor_assessment_record",
                "ext_collection_source_create",
                "ext_monitoring_observation_record",
                "ext_collection_run_record"):
            self.assertIn(expected, actions)

    def test_viewer_denied_writes_and_no_audit_forgery(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_questionnaire(SYSTEM_REF, "Q2", VIEWER)
        with self.assertRaises(PermissionDenied):
            self.ext.create_publication(SYSTEM_REF, "P2", VIEWER)
        with self.assertRaises(PermissionDenied):
            self.ext.register_collection_source(
                "api", SYSTEM_REF, "feed2", VIEWER)
        with self.assertRaises(PermissionDenied):
            self.ext.record_vendor_assessment(SYSTEM_REF, "pass", VIEWER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertEqual(actions.count("ext_questionnaire_create"), 1)
        self.assertEqual(actions.count("ext_publication_create"), 1)

    def test_extension_summary_counts(self):
        summary = self.ext.extension_summary(ADMIN)
        self.assertEqual(summary["questionnaires"]["total"], 1)
        self.assertEqual(summary["questionnaires"]["responses_total"], 1)
        self.assertEqual(summary["publications"]["total"], 1)
        self.assertEqual(summary["publications"]["releases_total"], 1)
        self.assertEqual(summary["vendor"]["rules_total"], 1)
        self.assertEqual(summary["vendor"]["assessments_total"], 1)
        self.assertEqual(summary["monitoring"]["sources_total"], 1)
        self.assertEqual(summary["monitoring"]["observations_total"], 1)
        self.assertEqual(summary["monitoring"]["collection_runs_total"], 1)


class _EarliestLabelExtensions(GrcExtensions):
    """Mutant: the latest-label seam reads the earliest record."""

    @staticmethod
    def _latest_label(records, key):
        return records[0][key] if records else None


def _build_stream(ext):
    """The canonical stream: two responses, two observations,
    two releases, in a fixed order, on a given extension."""
    qnr = ext.create_questionnaire(SYSTEM_REF, "Q", MEMBER)
    ext.record_questionnaire_response(qnr["id"], "in_progress", MEMBER)
    ext.record_questionnaire_response(qnr["id"], "submitted", MEMBER)
    source = ext.register_collection_source("api", SYSTEM_REF, "feed", MEMBER)
    ext.record_monitoring_observation(source["id"], "degraded", MEMBER)
    ext.record_monitoring_observation(source["id"], "nominal", MEMBER)
    return qnr, source


class TestLatestLabelNegativeControl(unittest.TestCase):
    """Fresh negative control for the latest-label seam.

    Canonical expectation: a derived view's "latest" label is the
    most recently recorded one. The mutant seam reads the
    earliest record and must misstate it.
    """

    def setUp(self):
        self.store, self.audit, self.system, self.ext = make_ext()
        self.mutant = _EarliestLabelExtensions(self.store)
        self.qnr, self.source = _build_stream(self.ext)
        self.m_qnr, self.m_source = _build_stream(self.mutant)

    def test_canonical_latest_is_most_recent(self):
        view = self.ext.questionnaire_view(self.qnr["id"], ADMIN)
        self.assertEqual(view["latest_response_status"], "submitted")
        source_view = self.ext.collection_source_view(self.source["id"],
                                                      ADMIN)
        self.assertEqual(source_view["latest_observation_status"], "nominal")

    def test_mutant_reports_earliest(self):
        view = self.mutant.questionnaire_view(self.m_qnr["id"], ADMIN)
        self.assertEqual(view["latest_response_status"], "in_progress")
        source_view = self.mutant.collection_source_view(self.m_source["id"],
                                                         ADMIN)
        self.assertEqual(
            source_view["latest_observation_status"], "degraded")

    def test_mutant_outcome_is_not_the_canonical_expectation(self):
        with self.assertRaises(AssertionError):
            self.assertEqual(
                self.mutant.questionnaire_view(self.m_qnr["id"], ADMIN)
                ["latest_response_status"],
                "submitted")


if __name__ == "__main__":
    unittest.main()
