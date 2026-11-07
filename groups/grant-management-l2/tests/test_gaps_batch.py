"""Final GAPS batch tests — Singleton 45, Grant Management L2.

Traces to: GAPS.md "Singleton 45 — Grant Management L2" (the 11
open entries), gaps-batch/DECISION.md (batch pattern), and the
group's UNION-SPEC.md core-boundary decisions — above all (2)
*Scoring*: nothing is scored in this build, by design, and no
record shape carries a score field. The extension surface in
``grants.extensions`` is pinned here entry by entry:

- portal configurations, form layouts, and vault records are data
  records (``rendered_here`` / ``served_here`` / ``content_held``
  False), with vault verification derived by content hash;
- disbursement records sit under the disbursement-cap invariant
  (the fresh negative control below), with totals derived at read;
- dashboards derive every panel value at run time and store
  nothing; export manifests are counts derived at creation;
- delivery receipts carry ``reference_transport: True``;
- matching is a deterministic presence match with per-application
  evidence; eligibility is a deterministic criteria check derived
  at read and never stored;
- merit scoring is records form only (rules held as data, never
  applied; outcomes verbatim as reported), per the re-judgment in
  BATCH.md;
- reconciliation variances derive at read in exact integer cents,
  and closeout records are gated on a derived readiness;
- the workflow-execution and e-signature entries are labeled
  reference implementations (``reference_stub: True``) that change
  no core record;
- a recursive key scan pins the founding no-score invariant over
  the whole extension surface: no score-, rating-, grade-, or
  rank-shaped key appears in any returned value.
"""

import hashlib
import unittest

from grants_helpers import (
    ADMIN,
    MEMBER,
    OUTSIDER,
    STAFF,
    VIEWER,
    make_application,
    make_award,
    make_store,
)
from grants.audit import AuditLog
from grants.errors import NotFoundError, PermissionDenied, ValidationError
from grants.extensions import GrantsExtensions

BANNED_KEY_PARTS = ("score", "rating", "grade", "rank")


def make_extensions(audit=None):
    store, program, org = make_store(audit=audit)
    return GrantsExtensions(store), store, program, org


def assert_no_score_keys(case, value, path="root"):
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            for part in BANNED_KEY_PARTS:
                case.assertNotIn(
                    part, lowered,
                    "banned key part %r at %s.%s" % (part, path, key))
            assert_no_score_keys(case, item, "%s.%s" % (path, key))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            assert_no_score_keys(case, item, "%s[%d]" % (path, index))


class TestPortalConfiguration(unittest.TestCase):
    """Entry: Applicant portal web application — built as portal
    configuration records; nothing is rendered or served."""

    def _create(self, ext, program):
        return ext.create_portal_configuration(
            program["id"], "Community Grants",
            {"primary": "#003366", "accent": "#cc6600"},
            [{"name": "home", "title": "Home"},
             {"name": "apply", "title": "Apply"}],
            ["desktop", "mobile"], MEMBER)

    def test_configuration_shape_and_labels(self):
        ext, store, program, org = make_extensions()
        record = self._create(ext, program)
        self.assertEqual(record["id"], "ptl-1")
        self.assertEqual(record["program_id"], program["id"])
        self.assertIs(record["rendered_here"], False)
        self.assertIs(record["served_here"], False)
        self.assertEqual(record["device_modes"], ["desktop", "mobile"])
        fetched = ext.get_portal_configuration(MEMBER, program["id"])
        self.assertEqual(fetched, record)

    def test_one_configuration_per_program(self):
        ext, store, program, org = make_extensions()
        self._create(ext, program)
        with self.assertRaises(ValidationError):
            self._create(ext, program)

    def test_validation(self):
        ext, store, program, org = make_extensions()
        with self.assertRaises(ValidationError):
            ext.create_portal_configuration(
                program["id"], "X", {}, [{"name": "h", "title": "H"}],
                ["watch"], MEMBER)
        with self.assertRaises(ValidationError):
            ext.create_portal_configuration(
                program["id"], "X", {},
                [{"name": "h", "title": "H"}, {"name": "h", "title": "H2"}],
                ["desktop"], MEMBER)
        with self.assertRaises(ValidationError):
            ext.create_portal_configuration(
                program["id"], "X", {"primary": ""},
                [{"name": "h", "title": "H"}], ["desktop"], MEMBER)

    def test_access_boundaries(self):
        ext, store, program, org = make_extensions()
        with self.assertRaises(PermissionDenied):
            self._create_as(ext, program, VIEWER)
        with self.assertRaises(PermissionDenied):
            self._create_as(ext, program, OUTSIDER)

    def _create_as(self, ext, program, actor):
        return ext.create_portal_configuration(
            program["id"], "X", {}, [{"name": "h", "title": "H"}],
            ["desktop"], actor)


class TestFormDesigner(unittest.TestCase):
    """Entry: Form designer & form rendering engine — built as
    layout records validated against the core form definition."""

    def _form(self, store, program):
        return store.create_form(
            MEMBER, program["id"], "Intake",
            [{"name": "region", "kind": "text", "required": True},
             {"name": "amount_note", "kind": "text", "required": False}])

    def test_layout_shape_and_labels(self):
        ext, store, program, org = make_extensions()
        form = self._form(store, program)
        layout = ext.create_form_layout(
            form["id"],
            [{"title": "About", "field_names": ["region"]},
             {"title": "Notes", "field_names": ["amount_note"]}], MEMBER)
        self.assertEqual(layout["id"], "fly-1")
        self.assertIs(layout["rendered_here"], False)
        self.assertEqual(ext.get_form_layout(MEMBER, layout["id"]), layout)
        self.assertEqual(ext.list_form_layouts(MEMBER, form["id"]), [layout])

    def test_unknown_field_rejected(self):
        ext, store, program, org = make_extensions()
        form = self._form(store, program)
        with self.assertRaises(ValidationError):
            ext.create_form_layout(
                form["id"],
                [{"title": "Bad", "field_names": ["nope"]}], MEMBER)

    def test_duplicate_placement_rejected_and_consumes_no_id(self):
        ext, store, program, org = make_extensions()
        form = self._form(store, program)
        with self.assertRaises(ValidationError):
            ext.create_form_layout(
                form["id"],
                [{"title": "A", "field_names": ["region"]},
                 {"title": "B", "field_names": ["region"]}], MEMBER)
        layout = ext.create_form_layout(
            form["id"], [{"title": "A", "field_names": ["region"]}], MEMBER)
        self.assertEqual(layout["id"], "fly-1")


class TestDocumentVault(unittest.TestCase):
    """Entry: Document storage & content management engine — built
    as vault records; content is never held, verification derives
    from the recorded checksum."""

    CONTENT = b"grant agreement bytes"

    def _document(self, store, program):
        digest = hashlib.sha256(self.CONTENT).hexdigest()
        return store.create_document(
            MEMBER, "program", program["id"], "Agreement", "agreement",
            digest, len(self.CONTENT))

    def test_vault_record_shape(self):
        ext, store, program, org = make_extensions()
        doc = self._document(store, program)
        record = ext.create_vault_record(doc["id"], "vault://grants/1",
                                         MEMBER, retention_label="7y")
        self.assertEqual(record["id"], "vlt-1")
        self.assertIs(record["content_held"], False)
        self.assertEqual(ext.get_vault_record(MEMBER, record["id"]), record)
        self.assertEqual(ext.list_vault_records(MEMBER, doc["id"]), [record])

    def test_verify_by_content(self):
        ext, store, program, org = make_extensions()
        doc = self._document(store, program)
        record = ext.create_vault_record(doc["id"], "vault://grants/1",
                                         MEMBER)
        good = ext.verify_vault_content(MEMBER, record["id"], self.CONTENT)
        self.assertEqual(good, {
            "vault_id": record["id"],
            "document_id": doc["id"],
            "matches": True,
            "method": "sha256_verify_by_content",
            "content_stored": False,
        })
        bad = ext.verify_vault_content(MEMBER, record["id"], b"other bytes")
        self.assertIs(bad["matches"], False)

    def test_verify_rejects_non_bytes(self):
        ext, store, program, org = make_extensions()
        doc = self._document(store, program)
        record = ext.create_vault_record(doc["id"], "vault://grants/1",
                                         MEMBER)
        with self.assertRaises(ValidationError):
            ext.verify_vault_content(MEMBER, record["id"], "text")


class TestDisbursements(unittest.TestCase):
    """Entry: Payment / disbursement execution for awards — built
    as disbursement records under the disbursement cap; no money
    moves (``disbursed_here`` / ``paid_here`` False)."""

    def _award(self, store, program, org, amount=400_000):
        _, result = make_award(store, program, org, amount_cents=amount)
        return result["award"]

    def test_record_shape_and_labels(self):
        ext, store, program, org = make_extensions()
        award = self._award(store, program, org)
        record = ext.record_disbursement(award["id"], 100_000, STAFF,
                                         payee_ref="PAYEE-1", note="Q1")
        self.assertEqual(record["id"], "dis-1")
        self.assertIs(record["disbursed_here"], False)
        self.assertIs(record["paid_here"], False)
        self.assertEqual(ext.get_disbursement(STAFF, "dis-1"), record)
        self.assertEqual(ext.list_disbursements(STAFF, award["id"]), [record])

    def test_summary_derived_at_read(self):
        ext, store, program, org = make_extensions()
        award = self._award(store, program, org)
        self.assertEqual(ext.disbursement_summary(STAFF, award["id"]), {
            "award_id": award["id"],
            "award_cents": 400_000,
            "disbursed_cents": 0,
            "remaining_cents": 400_000,
            "disbursements": 0,
            "method": "deterministic_sums",
        })
        ext.record_disbursement(award["id"], 250_000, STAFF)
        summary = ext.disbursement_summary(STAFF, award["id"])
        self.assertEqual(summary["disbursed_cents"], 250_000)
        self.assertEqual(summary["remaining_cents"], 150_000)
        self.assertEqual(summary["disbursements"], 1)

    def test_float_amount_rejected(self):
        ext, store, program, org = make_extensions()
        award = self._award(store, program, org)
        with self.assertRaises(ValidationError):
            ext.record_disbursement(award["id"], 100.5, STAFF)
        with self.assertRaises(ValidationError):
            ext.record_disbursement(award["id"], True, STAFF)
        with self.assertRaises(ValidationError):
            ext.record_disbursement(award["id"], 0, STAFF)

    def test_exactly_at_cap_is_recorded(self):
        ext, store, program, org = make_extensions()
        award = self._award(store, program, org)
        ext.record_disbursement(award["id"], 250_000, STAFF)
        record = ext.record_disbursement(award["id"], 150_000, STAFF)
        self.assertEqual(record["id"], "dis-2")
        summary = ext.disbursement_summary(STAFF, award["id"])
        self.assertEqual(summary["remaining_cents"], 0)

    def test_one_cent_over_cap_rejected_whole(self):
        ext, store, program, org = make_extensions()
        award = self._award(store, program, org)
        ext.record_disbursement(award["id"], 400_000, STAFF)
        with self.assertRaises(ValidationError):
            ext.record_disbursement(award["id"], 1, STAFF)
        summary = ext.disbursement_summary(STAFF, award["id"])
        self.assertEqual(summary["disbursed_cents"], 400_000)
        self.assertEqual(summary["disbursements"], 1)

    def test_rejected_disbursement_consumes_no_id(self):
        ext, store, program, org = make_extensions()
        _, result = make_award(store, program, org, amount_cents=100)
        award = result["award"]
        first = ext.record_disbursement(award["id"], 60, STAFF)
        self.assertEqual(first["id"], "dis-1")
        with self.assertRaises(ValidationError):
            ext.record_disbursement(award["id"], 41, STAFF)
        second = ext.record_disbursement(award["id"], 40, STAFF)
        self.assertEqual(second["id"], "dis-2")


class MutantGrantsExtensions(GrantsExtensions):
    """The batch negative control's mutant: the disbursement-cap
    seam removed, so recorded disbursements may exceed the award."""

    def _check_disbursement_cap(self, award, amount_cents):
        return None


class TestDisbursementCapNegativeControl(unittest.TestCase):
    """Fresh negative control (mutation-verified live — see
    tests/README.md): the canonical expectation is that recorded
    disbursements against an award never exceed the award amount;
    the mutant accepts an over-cap disbursement the canonical
    surface rejects."""

    def test_canonical_expectation_rejects_over_cap(self):
        ext, store, program, org = make_extensions()
        _, result = make_award(store, program, org)
        award = result["award"]
        ext.record_disbursement(award["id"], 400_000, STAFF)
        with self.assertRaises(ValidationError):
            ext.record_disbursement(award["id"], 1, STAFF)

    def test_mutant_accepts_what_canonical_rejects(self):
        store, program, org = make_store()
        ext = MutantGrantsExtensions(store)
        _, result = make_award(store, program, org)
        award = result["award"]
        ext.record_disbursement(award["id"], 400_000, STAFF)
        record = ext.record_disbursement(award["id"], 1, STAFF)
        self.assertEqual(record["amount_cents"], 1)
        # Treating the mutant's outcome as the canonical expectation
        # (total recorded disbursements stay within the award) fails:
        with self.assertRaises(AssertionError):
            self.assertEqual(
                ext.disbursement_summary(STAFF, award["id"])
                ["disbursed_cents"],
                400_000)

    def test_implementation_matches_canonical_across_disbursements(self):
        ext, store, program, org = make_extensions()
        _, result = make_award(store, program, org)
        award = result["award"]
        ext.record_disbursement(award["id"], 250_000, STAFF)
        ext.record_disbursement(award["id"], 150_000, STAFF)
        with self.assertRaises(ValidationError):
            ext.record_disbursement(award["id"], 1, STAFF)
        summary = ext.disbursement_summary(STAFF, award["id"])
        self.assertEqual(summary["disbursed_cents"], 400_000)
        self.assertEqual(summary["remaining_cents"], 0)


class TestReportingDashboardsExports(unittest.TestCase):
    """Entry: Reporting & analytics engines beyond registry
    summaries — built as dashboard definitions whose runs derive
    values at read, and export records with derived manifests."""

    def _dashboard(self, ext, program):
        return ext.create_dashboard(
            program["id"], "Overview",
            [{"title": "Applications", "metric": "applications_total"},
             {"title": "By status", "metric": "applications_by_status"},
             {"title": "Awarded", "metric": "awarded_cents"}], MEMBER)

    def test_dashboard_run_derives_and_stores_nothing(self):
        ext, store, program, org = make_extensions()
        dashboard = self._dashboard(ext, program)
        make_application(store, program, org)
        run = ext.run_dashboard(MEMBER, dashboard["id"], now="2026-06-01")
        panels = {p["metric"]: p["value"] for p in run["panels"]}
        self.assertEqual(panels["applications_total"], 1)
        self.assertEqual(panels["applications_by_status"]["draft"], 1)
        self.assertEqual(panels["awarded_cents"], 0)
        self.assertEqual(run["method"], "deterministic_counts")
        # Running again returns the same derivation and creates no
        # record anywhere on the extension surface.
        self.assertEqual(ext.run_dashboard(MEMBER, dashboard["id"],
                                           now="2026-06-01"), run)
        self.assertEqual(len(ext._dashboards), 1)

    def test_unknown_metric_rejected(self):
        ext, store, program, org = make_extensions()
        with self.assertRaises(ValidationError):
            ext.create_dashboard(
                program["id"], "Bad",
                [{"title": "X", "metric": "success_rate"}], MEMBER)

    def test_export_manifest_derived_counts(self):
        ext, store, program, org = make_extensions()
        make_application(store, program, org)
        record = ext.create_export_record(program["id"], "quarterly",
                                          MEMBER)
        self.assertIs(record["delivered_here"], False)
        self.assertEqual(record["manifest"]["applications"], 1)
        self.assertEqual(record["manifest"]["awards"], 0)
        self.assertEqual(record["manifest"]["reports"], 0)
        self.assertEqual(ext.list_export_records(MEMBER, program["id"]),
                         [record])


class TestDeliveryReceipts(unittest.TestCase):
    """Entry: Notification & message delivery transport — built as
    labeled reference-transport receipts; nothing is delivered."""

    def test_receipt_shape_and_labels(self):
        ext, store, program, org = make_extensions()
        note = store.create_notification(MEMBER, program["id"], org["id"],
                                         "Window closing soon")
        receipt = ext.record_delivery(program["id"], note["id"], "email",
                                      MEMBER)
        self.assertEqual(receipt["id"], "dlv-1")
        self.assertIs(receipt["reference_transport"], True)
        self.assertEqual(receipt["state"], "recorded_reference_only")
        self.assertIs(receipt["delivered_here"], False)
        self.assertEqual(ext.list_deliveries(MEMBER, program["id"]),
                         [receipt])
        # The core notification surface is unchanged: still exactly
        # the one recorded notification.
        self.assertEqual(
            len(store.list_notifications(MEMBER, program["id"])), 1)

    def test_unknown_notification_and_channel_rejected(self):
        ext, store, program, org = make_extensions()
        note = store.create_notification(MEMBER, program["id"], org["id"],
                                         "Hello")
        with self.assertRaises(NotFoundError):
            ext.record_delivery(program["id"], "ntf-99", "email", MEMBER)
        with self.assertRaises(ValidationError):
            ext.record_delivery(program["id"], note["id"], "fax", MEMBER)


class TestMatching(unittest.TestCase):
    """Entry: Applicant matching & opportunity recommendation —
    built as a deterministic presence match over recorded form
    responses, with missing fields as evidence and no ranking."""

    def _setup(self):
        ext, store, program, org = make_extensions()
        criteria = ext.create_match_criteria(
            program["id"], ["region", "ein_confirmed"], MEMBER)
        full = make_application(
            store, program, org,
            responses={"region": "south", "ein_confirmed": "yes"})
        partial = make_application(
            store, program, org, responses={"region": "north"})
        return ext, store, program, org, criteria, full, partial

    def test_presence_match_evidence(self):
        ext, store, program, org, criteria, full, partial = self._setup()
        result = ext.evaluate_matches(MEMBER, criteria["id"])
        self.assertEqual(result["method"], "deterministic_presence_match")
        by_id = {m["application_id"]: m for m in result["matches"]}
        self.assertEqual(by_id[full["id"]], {
            "application_id": full["id"], "org_id": org["id"],
            "matched": True, "missing_fields": []})
        self.assertEqual(by_id[partial["id"]]["matched"], False)
        self.assertEqual(by_id[partial["id"]]["missing_fields"],
                         ["ein_confirmed"])
        # Application (creation) order is preserved — no ranking.
        self.assertEqual([m["application_id"] for m in result["matches"]],
                         [full["id"], partial["id"]])

    def test_match_stores_nothing(self):
        ext, store, program, org, criteria, full, partial = self._setup()
        first = ext.evaluate_matches(MEMBER, criteria["id"])
        self.assertEqual(ext.evaluate_matches(MEMBER, criteria["id"]), first)


class TestEligibility(unittest.TestCase):
    """Entry: Eligibility determination & merit-scoring engines —
    eligibility built as a deterministic criteria check, derived at
    read and never stored (nothing is scored, by design)."""

    CRITERIA = [
        {"kind": "max_requested_cents", "value_cents": 500_000},
        {"kind": "required_response_field", "field": "region"},
        {"kind": "response_field_equals", "field": "region",
         "value": "south"},
        {"kind": "application_status_in", "statuses": ["draft"]},
    ]

    def _setup(self):
        ext, store, program, org = make_extensions()
        criteria = ext.create_eligibility_criteria(
            program["id"], self.CRITERIA, MEMBER)
        return ext, store, program, org, criteria

    def test_determination_derived_per_criterion(self):
        ext, store, program, org, criteria = self._setup()
        app = make_application(store, program, org,
                               responses={"region": "south"})
        result = ext.evaluate_eligibility(MEMBER, app["id"], criteria["id"])
        self.assertIs(result["eligible"], True)
        self.assertIs(result["stored"], False)
        self.assertEqual(result["method"], "deterministic_criteria_check")
        self.assertEqual([c["satisfied"] for c in result["checks"]],
                         [True, True, True, True])

    def test_failing_criterion_makes_ineligible(self):
        ext, store, program, org, criteria = self._setup()
        app = make_application(store, program, org, requested_cents=900_000,
                               responses={"region": "north"})
        result = ext.evaluate_eligibility(MEMBER, app["id"], criteria["id"])
        self.assertIs(result["eligible"], False)
        self.assertEqual([c["satisfied"] for c in result["checks"]],
                         [False, True, False, True])

    def test_latest_criteria_used_by_default_and_none_recorded(self):
        ext, store, program, org = make_extensions()
        app = make_application(store, program, org)
        with self.assertRaises(NotFoundError):
            ext.evaluate_eligibility(MEMBER, app["id"])
        criteria = ext.create_eligibility_criteria(
            program["id"],
            [{"kind": "max_requested_cents", "value_cents": 500_000}],
            MEMBER)
        result = ext.evaluate_eligibility(MEMBER, app["id"])
        self.assertEqual(result["criteria_id"], criteria["id"])
        self.assertIs(result["eligible"], True)

    def test_evaluation_stores_no_determination(self):
        ext, store, program, org, criteria = self._setup()
        app = make_application(store, program, org,
                               responses={"region": "south"})
        first = ext.evaluate_eligibility(MEMBER, app["id"], criteria["id"])
        counts = (len(ext._eligibility_criteria), len(ext._review_outcomes))
        second = ext.evaluate_eligibility(MEMBER, app["id"], criteria["id"])
        self.assertEqual(first, second)
        self.assertEqual(counts, (len(ext._eligibility_criteria),
                                  len(ext._review_outcomes)))

    def test_bad_criterion_rejected(self):
        ext, store, program, org = make_extensions()
        with self.assertRaises(ValidationError):
            ext.create_eligibility_criteria(
                program["id"], [{"kind": "credit_check"}], MEMBER)
        with self.assertRaises(ValidationError):
            ext.create_eligibility_criteria(
                program["id"],
                [{"kind": "max_requested_cents", "value_cents": 1.5}],
                MEMBER)


class TestMeritScoringRecordsForm(unittest.TestCase):
    """Entry (same GAPS entry, merit half): scoring rules held as
    data and never applied; review outcomes verbatim as reported.
    See BATCH.md for the re-judgment of form."""

    def test_scoring_rule_held_as_data(self):
        ext, store, program, org = make_extensions()
        rule = ext.create_scoring_rule(
            program["id"], "Panels weigh community impact first.", MEMBER)
        self.assertEqual(rule["method"], "recorded_rules_only")
        self.assertIs(rule["applied_here"], False)
        self.assertEqual(ext.list_scoring_rules(MEMBER, program["id"]),
                         [rule])

    def test_review_outcome_verbatim_and_core_untouched(self):
        ext, store, program, org = make_extensions()
        app = make_application(store, program, org)
        before = store.get_application(MEMBER, app["id"])
        record = ext.record_review_outcome(
            app["id"], "Panel consensus: strong fit, fund at ask.",
            STAFF, reported_by_ref="PANEL-7")
        self.assertEqual(record["outcome_text"],
                         "Panel consensus: strong fit, fund at ask.")
        self.assertIs(record["computed_here"], False)
        self.assertEqual(ext.list_review_outcomes(MEMBER, app["id"]),
                         [record])
        self.assertEqual(store.get_application(MEMBER, app["id"]), before)


class TestReconciliationCloseout(unittest.TestCase):
    """Entry: Closeout automation & financial reconciliation
    engines — built as reconciliation records with variances
    derived at read, and closeout records gated on derived
    readiness. No automation executes."""

    def _award_with_reports(self, store, program, org):
        _, result = make_award(store, program, org)
        award = result["award"]
        r1 = store.create_report(STAFF, award["id"], "progress",
                                 "2026-09-30")
        r2 = store.create_report(STAFF, award["id"], "final", "2026-12-31")
        return award, r1, r2

    def test_reconciliation_variances_derived_exact(self):
        ext, store, program, org = make_extensions()
        award, r1, r2 = self._award_with_reports(store, program, org)
        ext.record_disbursement(award["id"], 300_000, STAFF)
        view = ext.create_reconciliation(award["id"], 250_000, STAFF,
                                         note="per recipient ledger")
        self.assertEqual(view["award_cents"], 400_000)
        self.assertEqual(view["recorded_disbursed_cents"], 300_000)
        self.assertEqual(view["remaining_vs_award_cents"], 100_000)
        self.assertEqual(view["variance_vs_reported_cents"], -50_000)
        # The stored record holds only the reported input.
        stored = ext._reconciliations[view["id"]]
        self.assertNotIn("variance_vs_reported_cents", stored)
        self.assertNotIn("recorded_disbursed_cents", stored)

    def test_float_reported_figure_rejected(self):
        ext, store, program, org = make_extensions()
        award, r1, r2 = self._award_with_reports(store, program, org)
        with self.assertRaises(ValidationError):
            ext.create_reconciliation(award["id"], 250_000.0, STAFF)

    def test_closeout_gated_on_derived_readiness(self):
        ext, store, program, org = make_extensions()
        award, r1, r2 = self._award_with_reports(store, program, org)
        readiness = ext.closeout_readiness(STAFF, award["id"],
                                           now="2026-06-01")
        self.assertIs(readiness["ready"], False)
        self.assertEqual(readiness["blockers"],
                         ["reports_outstanding:2", "reconciliation_missing"])
        with self.assertRaises(ValidationError):
            ext.record_closeout(award["id"], STAFF)
        ext.create_reconciliation(award["id"], 0, STAFF)
        store.submit_report(STAFF, r1["id"], "Progress filed")
        readiness = ext.closeout_readiness(STAFF, award["id"],
                                           now="2026-06-01")
        self.assertEqual(readiness["blockers"], ["reports_outstanding:1"])
        store.submit_report(STAFF, r2["id"], "Final filed")
        readiness = ext.closeout_readiness(STAFF, award["id"],
                                           now="2026-06-01")
        self.assertIs(readiness["ready"], True)
        record = ext.record_closeout(award["id"], STAFF, note="Complete")
        self.assertEqual(record["state"], "recorded_only")
        self.assertIs(record["executed_here"], False)
        self.assertIs(record["automation_here"], False)
        with self.assertRaises(ValidationError):
            ext.record_closeout(award["id"], STAFF)


class TestWorkflowExecutionStub(unittest.TestCase):
    """Entry: Workflow execution engine — stub-engine, shipped as a
    labeled reference implementation. A run reference copies the
    definition's steps as data and changes no application."""

    def test_run_reference_labels_and_core_untouched(self):
        ext, store, program, org = make_extensions()
        workflow = store.create_workflow(
            MEMBER, program["id"], "Intake flow",
            ["receive", "review", "decide"])
        app = make_application(store, program, org)
        before_app = store.get_application(MEMBER, app["id"])
        before_wf = store.get_workflow(MEMBER, workflow["id"])
        record = ext.create_workflow_run_reference(workflow["id"], MEMBER)
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertIs(record["executed_here"], False)
        self.assertEqual(record["steps"], ["receive", "review", "decide"])
        self.assertEqual(store.get_application(MEMBER, app["id"]), before_app)
        self.assertEqual(store.get_workflow(MEMBER, workflow["id"]),
                         before_wf)
        self.assertEqual(
            ext.list_workflow_run_references(MEMBER, workflow["id"]),
            [record])


class TestESignatureStub(unittest.TestCase):
    """Entry: E-signature signing engine — stub-engine, shipped as
    a labeled reference implementation. A signing reference does
    not sign the core document."""

    def test_signing_reference_labels_and_document_unsigned(self):
        ext, store, program, org = make_extensions()
        digest = hashlib.sha256(b"agreement").hexdigest()
        doc = store.create_document(MEMBER, "program", program["id"],
                                    "Agreement", "agreement", digest, 9)
        record = ext.create_signing_reference(doc["id"], MEMBER,
                                              signer_ref="SIGNER-1")
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertIs(record["ceremony_here"], False)
        self.assertIs(record["cryptographic_binding"], False)
        after = store.get_document(MEMBER, doc["id"])
        self.assertIsNone(after["signed_by"])
        self.assertIsNone(after["signed_at"])
        self.assertEqual(ext.list_signing_references(MEMBER, doc["id"]),
                         [record])


class TestNoScoreInvariant(unittest.TestCase):
    """The founding doctrine (UNION-SPEC core-boundary decision 2)
    over the whole extension surface: no score-, rating-, grade-,
    or rank-shaped key in any returned value."""

    def test_no_score_keys_anywhere(self):
        audit = AuditLog()
        ext, store, program, org = make_extensions(audit=audit)
        outputs = []
        outputs.append(ext.create_portal_configuration(
            program["id"], "Brand", {}, [{"name": "h", "title": "H"}],
            ["desktop"], MEMBER))
        form = store.create_form(
            MEMBER, program["id"], "Intake",
            [{"name": "region", "kind": "text", "required": True}])
        outputs.append(ext.create_form_layout(
            form["id"], [{"title": "A", "field_names": ["region"]}], MEMBER))
        digest = hashlib.sha256(b"doc").hexdigest()
        doc = store.create_document(MEMBER, "program", program["id"],
                                    "Doc", "other", digest, 3)
        outputs.append(ext.create_vault_record(doc["id"], "vault://x",
                                               MEMBER))
        outputs.append(ext.verify_vault_content(MEMBER, "vlt-1", b"doc"))
        _, result = make_award(store, program, org)
        award = result["award"]
        outputs.append(ext.record_disbursement(award["id"], 100_000, STAFF))
        outputs.append(ext.disbursement_summary(STAFF, award["id"]))
        dashboard = ext.create_dashboard(
            program["id"], "D",
            [{"title": "T", "metric": "applications_total"}], MEMBER)
        outputs.append(ext.run_dashboard(MEMBER, dashboard["id"]))
        outputs.append(ext.create_export_record(program["id"], "k", MEMBER))
        note = store.create_notification(MEMBER, program["id"], org["id"],
                                         "Hi")
        outputs.append(ext.record_delivery(program["id"], note["id"],
                                           "sms", MEMBER))
        app = make_application(store, program, org,
                               responses={"region": "south"})
        criteria = ext.create_match_criteria(program["id"], ["region"],
                                             MEMBER)
        outputs.append(ext.evaluate_matches(MEMBER, criteria["id"]))
        ecriteria = ext.create_eligibility_criteria(
            program["id"],
            [{"kind": "required_response_field", "field": "region"}], MEMBER)
        outputs.append(ext.evaluate_eligibility(MEMBER, app["id"],
                                                ecriteria["id"]))
        outputs.append(ext.create_scoring_rule(program["id"], "Rule.",
                                               MEMBER))
        outputs.append(ext.record_review_outcome(app["id"], "Reported.",
                                                 STAFF))
        outputs.append(ext.create_reconciliation(award["id"], 90_000, STAFF))
        outputs.append(ext.closeout_readiness(STAFF, award["id"]))
        workflow = store.create_workflow(MEMBER, program["id"], "W",
                                         ["step"])
        outputs.append(ext.create_workflow_run_reference(workflow["id"],
                                                         MEMBER))
        outputs.append(ext.create_signing_reference(doc["id"], MEMBER))
        for output in outputs:
            assert_no_score_keys(self, output)


class TestAccessAndAudit(unittest.TestCase):
    """Cross-cutting: ext_-prefixed audit actions on the core log,
    denied writes recorded with a :denied suffix, program
    membership enforced through the core's own checks."""

    def test_ext_mutations_audited(self):
        audit = AuditLog()
        ext, store, program, org = make_extensions(audit=audit)
        _, result = make_award(store, program, org)
        ext.record_disbursement(result["award"]["id"], 10_000, STAFF)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("ext_disbursement_create", actions)

    def test_viewer_write_denied_and_audited(self):
        audit = AuditLog()
        ext, store, program, org = make_extensions(audit=audit)
        _, result = make_award(store, program, org)
        with self.assertRaises(PermissionDenied):
            ext.record_disbursement(result["award"]["id"], 10_000, VIEWER)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("ext_disbursement_create:denied", actions)

    def test_outsider_denied_by_membership(self):
        ext, store, program, org = make_extensions()
        with self.assertRaises(PermissionDenied):
            ext.create_portal_configuration(
                program["id"], "X", {}, [{"name": "h", "title": "H"}],
                ["desktop"], OUTSIDER)
        _, result = make_award(store, program, org)
        with self.assertRaises(PermissionDenied):
            ext.disbursement_summary(OUTSIDER, result["award"]["id"])


if __name__ == "__main__":
    unittest.main()
