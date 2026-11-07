"""Final GAPS batch tests — second unit, Group 9 (AI L2).

Pins the addition surface in ``src/aigateway/extensions_addition.py``
against the remainder addition fork's 3 gap entries (see
``../BATCH-ADDITION.md``):

- Infrastructure Digital Twin & infrastructure performance
  management engine (idx 649) — built: twin profiles and
  performance observation records whose figures are the twin
  operator's reports, held verbatim and never aggregated; the
  twin itself is not operated here.
- Service transition management (idx 650) — built: transition
  plans with steps as data, step-status records, configuration
  changes recorded never applied, capacity figures verbatim
  never computed.
- EIS service management suite (idx 651) — reference: service,
  lifecycle, SLA, CLIN, invoice, reconciliation, dispute, and
  credit records, all labeled ``reference_stub: True``; no
  amount exists in any field shape.

Plus this unit's fresh negative control: the latest-record seam
``_latest_record`` — a mutant that reads the earliest record
instead must misstate every current-state view (a twin's latest
report, a step's current status, a service's current lifecycle
status).
"""

import unittest

import aigateway_helpers as helpers
from aigateway.errors import (
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from aigateway.extensions_addition import AIGatewayExtensionsAddition

ADMIN = helpers.ADMIN
MEMBER = helpers.MEMBER
VIEWER = helpers.VIEWER


def make_ext():
    """Fresh core store (helpers fixture) + addition wrapper."""
    store, audit, model = helpers.make_store()
    return store, audit, model, AIGatewayExtensionsAddition(store)


def scenario(ext):
    """One twin, one plan, one EIS service, each with two reports.

    Returns the created anchor records; the second report of
    each pair is the current one under the latest-record rule.
    """
    twin = ext.register_twin("net-twin", "scope-7", ADMIN)
    ext.record_performance_observation(twin["id"], "latency_p95", "12ms",
                                       MEMBER)
    ext.record_performance_observation(twin["id"], "latency_p95", "9ms",
                                       MEMBER)
    plan = ext.create_transition_plan(
        "ipv6-transition", ADMIN, subject_ref="mandate-ipv6",
        steps=["assess", "migrate"])
    ext.record_transition_step_status(plan["id"], "assess", "in_progress",
                                      MEMBER)
    ext.record_transition_step_status(plan["id"], "assess", "complete",
                                      MEMBER)
    service = ext.register_eis_service("svc-100", ADMIN,
                                       provider_label="provider-a")
    ext.record_eis_lifecycle_status(service["id"], "ordered", MEMBER)
    ext.record_eis_lifecycle_status(service["id"], "active", MEMBER)
    return twin, plan, service


class TestDigitalTwinBuilt(unittest.TestCase):
    """Idx 649 — twin profiles + verbatim reports; twin not run."""

    def setUp(self):
        self.store, self.audit, self.model, self.ext = make_ext()

    def test_profile_shape_and_labels(self):
        twin = self.ext.register_twin("net-twin", "scope-7", ADMIN)
        self.assertEqual(twin["id"], "idt-1")
        self.assertEqual(twin["scope_ref"], "scope-7")
        self.assertIsNone(twin["model"])
        self.assertFalse(twin["twin_operated_here"])
        self.assertFalse(twin["measured_here"])
        self.assertEqual(twin["state"], "recorded_profile")

    def test_model_binding_and_unknown_model(self):
        twin = self.ext.register_twin(
            "net-twin", "scope-7", ADMIN, model_name="echoer")
        self.assertEqual(twin["model"], "echoer")
        with self.assertRaises(NotFoundError):
            self.ext.register_twin(
                "net-twin", "scope-8", ADMIN, model_name="nope")

    def test_observation_is_verbatim_and_never_a_figure(self):
        twin = self.ext.register_twin("net-twin", "scope-7", ADMIN)
        obs = self.ext.record_performance_observation(
            twin["id"], "latency_p95", "12ms", MEMBER)
        self.assertEqual(obs["id"], "ipo-1")
        self.assertEqual(obs["reported_value"], "12ms")
        self.assertIsInstance(obs["reported_value"], str)
        self.assertFalse(obs["measured_here"])
        self.assertFalse(obs["computed_here"])
        with self.assertRaises(ValidationError):
            self.ext.record_performance_observation(
                twin["id"], "latency_p95", 12, MEMBER)

    def test_no_content_parameter(self):
        with self.assertRaises(TypeError):
            self.ext.register_twin(
                "net-twin", "scope-7", ADMIN, telemetry="...")
        twin = self.ext.register_twin("net-twin", "scope-7", ADMIN)
        with self.assertRaises(TypeError):
            self.ext.record_performance_observation(
                twin["id"], "latency_p95", "12ms", MEMBER, payload="...")

    def test_view_derives_counts_labels_and_latest(self):
        twin, _plan, _service = scenario(self.ext)
        view = self.ext.twin_view(twin["id"], ADMIN)
        self.assertTrue(view["derived"])
        self.assertEqual(view["observation_total"], 2)
        self.assertEqual(view["metric_labels"], ["latency_p95"])
        self.assertEqual(view["latest_observation"],
                         {"metric_label": "latency_p95",
                          "reported_value": "9ms"})
        stored = self.ext.get_twin(twin["id"], ADMIN)
        self.assertNotIn("observation_total", stored)
        self.assertNotIn("latest_observation", stored)

    def test_unknown_twin_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_performance_observation(
                "idt-99", "latency_p95", "12ms", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.twin_view("idt-99", ADMIN)


class TestTransitionManagementBuilt(unittest.TestCase):
    """Idx 650 — plans/steps as data; changes never applied."""

    def setUp(self):
        self.store, self.audit, self.model, self.ext = make_ext()

    def test_plan_shape(self):
        plan = self.ext.create_transition_plan(
            "ipv6-transition", ADMIN, subject_ref="mandate-ipv6",
            steps=["assess", "migrate"], model_name="echoer")
        self.assertEqual(plan["id"], "stp-1")
        self.assertEqual(plan["steps"], ["assess", "migrate"])
        self.assertEqual(plan["model"], "echoer")
        self.assertTrue(plan["definition_only"])
        self.assertFalse(plan["executed_here"])
        self.assertNotIn("status", plan)

    def test_step_status_binds_to_declared_steps(self):
        plan = self.ext.create_transition_plan(
            "ipv6-transition", ADMIN, steps=["assess", "migrate"])
        rec = self.ext.record_transition_step_status(
            plan["id"], "assess", "in_progress", MEMBER)
        self.assertEqual(rec["id"], "sts-1")
        self.assertFalse(rec["executed_here"])
        with self.assertRaises(ValidationError):
            self.ext.record_transition_step_status(
                plan["id"], "undeclared", "in_progress", MEMBER)
        rec2 = self.ext.record_transition_step_status(
            plan["id"], "migrate", "not_started", MEMBER)
        self.assertEqual(rec2["id"], "sts-2")

    def test_view_derives_current_status_per_step(self):
        _twin, plan, _service = scenario(self.ext)
        view = self.ext.transition_plan_view(plan["id"], ADMIN)
        self.assertTrue(view["derived"])
        self.assertEqual(view["step_status"],
                         {"assess": "complete", "migrate": None})
        self.assertEqual(view["status_records_total"], 2)
        stored = self.ext.get_transition_plan(plan["id"], ADMIN)
        self.assertNotIn("step_status", stored)
        self.assertNotIn("status_records_total", stored)

    def test_configuration_change_recorded_never_applied(self):
        plan = self.ext.create_transition_plan("ipv6-transition", ADMIN)
        change = self.ext.record_configuration_change(
            plan["id"], "dual_stack_enabled", MEMBER, target_ref="ci-9")
        self.assertEqual(change["id"], "stc-1")
        self.assertFalse(change["applied_here"])
        self.assertFalse(change["automated_here"])
        with self.assertRaises(TypeError):
            self.ext.record_configuration_change(
                plan["id"], "x", MEMBER, config_body="...")

    def test_capacity_report_verbatim_never_computed(self):
        plan = self.ext.create_transition_plan("ipv6-transition", ADMIN)
        rep = self.ext.record_capacity_report(
            plan["id"], "address_pool_utilization", "62 percent", MEMBER)
        self.assertEqual(rep["id"], "scp-1")
        self.assertEqual(rep["reported_value"], "62 percent")
        self.assertFalse(rep["computed_here"])
        with self.assertRaises(ValidationError):
            self.ext.record_capacity_report(
                plan["id"], "address_pool_utilization", 62, MEMBER)
        view = self.ext.transition_plan_view(plan["id"], ADMIN)
        self.assertEqual(view["capacity_reports_total"], 1)
        self.assertEqual(view["configuration_changes_total"], 0)


class TestEisSuiteReference(unittest.TestCase):
    """Idx 651 — the EIS suite ships as labeled records only."""

    def setUp(self):
        self.store, self.audit, self.model, self.ext = make_ext()

    def test_service_shape_and_labels(self):
        svc = self.ext.register_eis_service(
            "svc-100", ADMIN, provider_label="provider-a")
        self.assertEqual(svc["id"], "esi-1")
        self.assertTrue(svc["reference_stub"])
        self.assertFalse(svc["operated_here"])
        self.assertFalse(svc["monitored_here"])
        self.assertEqual(svc["state"], "recorded_reference_only")

    def test_current_status_derived_from_latest_record(self):
        _twin, _plan, svc = scenario(self.ext)
        view = self.ext.eis_service_view(svc["id"], ADMIN)
        self.assertEqual(view["current_status"], "active")
        self.assertEqual(view["lifecycle_records_total"], 2)
        stored = self.ext.get_eis_service(svc["id"], ADMIN)
        self.assertNotIn("current_status", stored)

    def test_sla_report_verbatim_no_attainment(self):
        svc = self.ext.register_eis_service("svc-100", ADMIN)
        rep = self.ext.record_sla_report(
            svc["id"], "service_availability", "99.95 percent", MEMBER)
        self.assertEqual(rep["id"], "esla-1")
        self.assertEqual(rep["reported_value"], "99.95 percent")
        self.assertTrue(rep["reference_stub"])
        self.assertFalse(rep["monitored_here"])
        self.assertFalse(rep["computed_here"])
        self.assertFalse(rep["attainment_determined_here"])

    def test_clin_and_invoice_hold_no_amount(self):
        svc = self.ext.register_eis_service("svc-100", ADMIN)
        line = self.ext.record_clin_line(
            svc["id"], "clin-0001", MEMBER, status_label="billed")
        self.assertEqual(line["id"], "ecl-1")
        self.assertFalse(line["managed_here"])
        inv = self.ext.record_invoice(
            svc["id"], "inv-500", MEMBER, status_label="received")
        self.assertEqual(inv["id"], "einv-1")
        self.assertFalse(inv["paid_here"])
        with self.assertRaises(TypeError):
            self.ext.record_clin_line(
                svc["id"], "clin-0002", MEMBER, amount=100)
        with self.assertRaises(TypeError):
            self.ext.record_invoice(
                svc["id"], "inv-501", MEMBER, document="...")

    def test_reconciliation_dispute_and_credit_outcomes(self):
        svc = self.ext.register_eis_service("svc-100", ADMIN)
        inv = self.ext.record_invoice(svc["id"], "inv-500", MEMBER)
        rec = self.ext.record_reconciliation(
            inv["id"], "matched_with_variance", MEMBER)
        self.assertFalse(rec["reconciled_here"])
        dis = self.ext.record_dispute(inv["id"], "opened", MEMBER)
        self.assertFalse(dis["resolved_here"])
        credit = self.ext.record_credit_recovery(
            svc["id"], "credit_reported", MEMBER, credit_ref="cr-1")
        self.assertFalse(credit["recovered_here"])
        for record in (rec, dis, credit):
            self.assertTrue(record["reference_stub"])

    def test_view_counts_across_the_suite(self):
        svc = self.ext.register_eis_service("svc-100", ADMIN)
        self.ext.record_sla_report(svc["id"], "availability", "99.9", MEMBER)
        self.ext.record_clin_line(svc["id"], "clin-0001", MEMBER)
        inv = self.ext.record_invoice(svc["id"], "inv-500", MEMBER)
        self.ext.record_reconciliation(inv["id"], "matched", MEMBER)
        self.ext.record_dispute(inv["id"], "closed", MEMBER)
        self.ext.record_credit_recovery(svc["id"], "reported", MEMBER)
        view = self.ext.eis_service_view(svc["id"], ADMIN)
        self.assertTrue(view["derived"])
        self.assertIsNone(view["current_status"])
        self.assertEqual(view["sla_reports_total"], 1)
        self.assertEqual(view["clin_lines_total"], 1)
        self.assertEqual(view["invoices_total"], 1)
        self.assertEqual(view["reconciliations_total"], 1)
        self.assertEqual(view["disputes_total"], 1)
        self.assertEqual(view["credit_recoveries_total"], 1)

    def test_every_suite_record_is_a_labeled_reference(self):
        svc = self.ext.register_eis_service("svc-100", ADMIN)
        records = [svc]
        records.append(self.ext.record_eis_lifecycle_status(
            svc["id"], "ordered", MEMBER))
        records.append(self.ext.record_sla_report(
            svc["id"], "availability", "99.9", MEMBER))
        records.append(self.ext.record_clin_line(svc["id"], "clin-1", MEMBER))
        inv = self.ext.record_invoice(svc["id"], "inv-1", MEMBER)
        records.append(inv)
        records.append(self.ext.record_reconciliation(
            inv["id"], "matched", MEMBER))
        records.append(self.ext.record_dispute(inv["id"], "opened", MEMBER))
        records.append(self.ext.record_credit_recovery(
            svc["id"], "reported", MEMBER))
        for record in records:
            self.assertTrue(record["reference_stub"], record["id"])


class _EarliestRecordAddition(AIGatewayExtensionsAddition):
    """Mutant: current state reads the earliest record instead."""

    @staticmethod
    def _latest_record(records):
        return records[0] if records else None


class TestLatestRecordNegativeControl(unittest.TestCase):
    """Fresh negative control for the latest-record seam.

    Canonical rule: a twin's latest report, a plan step's
    current status, and a service's current lifecycle status
    are the LAST records reported for them. The mutant seam
    reads the earliest record and must misstate all three.
    """

    def setUp(self):
        self.store, self.audit, self.model, self.ext = make_ext()
        self.twin, self.plan, self.service = scenario(self.ext)
        _s, _a, _m, self.mutant_store = make_ext()
        self.mutant = _EarliestRecordAddition(self.mutant_store)
        scenario(self.mutant)

    def test_canonical_reads_the_latest_records(self):
        self.assertEqual(
            self.ext.twin_view(self.twin["id"], ADMIN)
            ["latest_observation"]["reported_value"], "9ms")
        self.assertEqual(
            self.ext.transition_plan_view(self.plan["id"], ADMIN)
            ["step_status"]["assess"], "complete")
        self.assertEqual(
            self.ext.eis_service_view(self.service["id"], ADMIN)
            ["current_status"], "active")

    def test_mutant_misstates_every_current_state(self):
        self.assertEqual(
            self.mutant.twin_view("idt-1", ADMIN)
            ["latest_observation"]["reported_value"], "12ms")
        self.assertEqual(
            self.mutant.transition_plan_view("stp-1", ADMIN)
            ["step_status"]["assess"], "in_progress")
        self.assertEqual(
            self.mutant.eis_service_view("esi-1", ADMIN)
            ["current_status"], "ordered")

    def test_mutant_outcome_is_not_the_canonical_expectation(self):
        with self.assertRaises(AssertionError):
            self.assertEqual(
                self.mutant.eis_service_view("esi-1", ADMIN)
                ["current_status"], "active")


FORBIDDEN_KEY_PARTS = ("content", "payload", "amount", "score")


def _walk(obj):
    """Yield every (key, value) pair in nested dicts/lists."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key, value
            yield from _walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item)


class TestSurfaceDiscipline(unittest.TestCase):
    """Cross-cutting: no content, no computed figure, audit."""

    def setUp(self):
        self.store, self.audit, self.model, self.ext = make_ext()

    def test_no_content_or_computed_figure_keys_anywhere(self):
        twin, plan, svc = scenario(self.ext)
        inv = self.ext.record_invoice(svc["id"], "inv-500", MEMBER)
        self.ext.record_reconciliation(inv["id"], "matched", MEMBER)
        surface = [
            self.ext.list_twins(ADMIN),
            self.ext.list_performance_observations(actor=ADMIN),
            self.ext.twin_view(twin["id"], ADMIN),
            self.ext.list_transition_plans(ADMIN),
            self.ext.transition_plan_view(plan["id"], ADMIN),
            self.ext.list_eis_services(ADMIN),
            self.ext.eis_service_view(svc["id"], ADMIN),
            self.ext.list_invoices(actor=ADMIN),
            self.ext.list_reconciliations(actor=ADMIN),
            self.ext.addition_summary(ADMIN),
        ]
        for obj in surface:
            for key, value in _walk(obj):
                for part in FORBIDDEN_KEY_PARTS:
                    self.assertNotIn(part, key,
                                     "forbidden key %r" % (key,))
                self.assertNotIsInstance(
                    value, float,
                    "no computed float figure may appear (%r)" % (key,))

    def test_addition_creates_no_core_records(self):
        scenario(self.ext)
        self.assertEqual(self.store.list_requests(ADMIN), [])
        self.assertEqual(self.store.list_sessions(ADMIN), [])

    def test_summary_and_audit_trail(self):
        twin, plan, svc = scenario(self.ext)
        summary = self.ext.addition_summary(ADMIN)
        self.assertTrue(summary["derived"])
        self.assertEqual(summary["by_kind"]["twin"], 1)
        self.assertEqual(summary["by_kind"]["performance_observation"], 2)
        self.assertEqual(summary["by_kind"]["transition_plan"], 1)
        self.assertEqual(summary["by_kind"]["eis_service"], 1)
        self.assertEqual(summary["by_kind"]["eis_lifecycle_status"], 2)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("exta_twin_register", actions)
        self.assertIn("exta_transition_plan_create", actions)
        self.assertIn("exta_eis_service_register", actions)

    def test_viewer_denied_and_denial_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_twin("net-twin", "scope-7", VIEWER)
        twin = self.ext.register_twin("net-twin", "scope-7", ADMIN)
        with self.assertRaises(PermissionDenied):
            self.ext.record_performance_observation(
                twin["id"], "latency_p95", "12ms", VIEWER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("exta_twin_register:denied", actions)
        self.assertIn("exta_performance_observation_record:denied", actions)
        self.assertEqual(
            len(self.ext.list_performance_observations(actor=ADMIN)), 0)


if __name__ == "__main__":
    unittest.main()
