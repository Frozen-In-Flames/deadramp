"""Final GAPS batch, second unit — addition surface tests.

Traces to: GAPS.md "Remainder Addition — Analytics L2 (+1 fork)",
the 4 catalogue-excess entries ADDENDUM.md section 5 registered
for the NetComm / Beacon addition fork, closed per
../../gaps-batch/DECISION.md in
``analytics/extensions_addition.py``: back-office service tools
and mobile client capabilities built as records, digital
signature and e-workflow tooling shipped as labeled reference
implementations (the signature entry re-judged from its
build-extension draft; grounds in ../BATCH-ADDITION.md).
See ../BATCH-ADDITION.md.

Fixtures use the canonical sales dataset from analytics_helpers;
the addition surface itself is dataset-independent, so the dataset
exists to prove the reference records leave the core untouched.
"""

import hashlib
import unittest

from analytics.audit import AuditLog
from analytics.errors import NotFoundError, PermissionDenied, ValidationError
from analytics.extensions_addition import AnalyticsExtensionsAddition
from analytics.store import DatasetStore

from analytics_helpers import ADMIN, ANALYST, VIEWER, sales_json_text

DOC_SHA256 = hashlib.sha256(b"a document's bytes").hexdigest()


def make_addition():
    audit = AuditLog()
    store = DatasetStore(audit=audit)
    dataset = store.ingest_json("sales", sales_json_text(), ADMIN)
    return AnalyticsExtensionsAddition(store), store, dataset["id"], audit


class AdditionFixture(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.ds, self.audit = make_addition()

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]


# -- idx 652: Automated back-office service tools (built) ------------------


class TestServiceTools(AdditionFixture):
    def test_register_shape_and_domains(self):
        """Back-office tools: registration records as data, exact keys."""
        tool = self.ext.register_service_tool("HR onboarding automation",
                                              "hr", ANALYST)
        self.assertEqual(tool["id"], "bto-1")
        self.assertEqual(set(tool.keys()),
                         {"id", "name", "domain", "created_by", "created_utc"})
        self.assertEqual(tool["domain"], "hr")
        with self.assertRaises(ValidationError):
            self.ext.register_service_tool("Legal automation", "legal", ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.register_service_tool("  ", "finance", ANALYST)

    def test_runs_recorded_as_reported_and_rollup_derived(self):
        """Runs are the external tool's reports, verbatim; rollups are
        derived at read and never stored on the tool record."""
        tool = self.ext.register_service_tool("Invoice processing",
                                              "finance", ANALYST)
        run = self.ext.record_service_tool_run(
            tool["id"], "completed", ANALYST, reported_items=12)
        self.assertEqual(run["id"], "btr-1")
        self.assertEqual(set(run.keys()),
                         {"id", "tool_id", "outcome", "reported_items",
                          "note", "reported", "executed_here",
                          "recorded_by", "recorded_utc"})
        self.assertTrue(run["reported"])
        self.assertFalse(run["executed_here"])
        self.ext.record_service_tool_run(tool["id"], "failed", ANALYST,
                                         reported_items=3)
        self.ext.record_service_tool_run(tool["id"], "completed", ANALYST)
        view = self.ext.service_tool_view(tool["id"], VIEWER)
        self.assertEqual(view["run_count"], 3)
        self.assertEqual(view["runs_by_outcome"],
                         {"completed": 2, "failed": 1})
        # The total sums the runs' *reported* item counts (12 + 3);
        # the run without a count contributes nothing.
        self.assertEqual(view["reported_items_total"], 15)
        self.assertEqual(view["last_outcome"], "completed")
        stored = self.ext.get_service_tool(tool["id"], ADMIN)
        self.assertNotIn("run_count", stored)
        self.assertNotIn("reported_items_total", stored)

    def test_run_validation(self):
        tool = self.ext.register_service_tool("Property inspections",
                                              "property_management", ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.record_service_tool_run(tool["id"], "done", ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.record_service_tool_run(tool["id"], "completed", ANALYST,
                                             reported_items=-1)
        with self.assertRaises(ValidationError):
            self.ext.record_service_tool_run(tool["id"], "completed", ANALYST,
                                             reported_items=True)
        with self.assertRaises(NotFoundError):
            self.ext.record_service_tool_run("bto-99", "completed", ANALYST)
        # Rejected runs consume no id.
        run = self.ext.record_service_tool_run(tool["id"], "partial", ANALYST)
        self.assertEqual(run["id"], "btr-1")


# -- idx 653: Digital signature engine (reference; re-judged) ---------------


class TestSignatureReference(AdditionFixture):
    def test_request_shape_and_stub_labels(self):
        """Signature requests are labeled reference records naming the
        document and signer by opaque ref/digest only."""
        req = self.ext.record_signature_request(
            "doc-ref-7", "signer-ref-3", ANALYST, document_sha256=DOC_SHA256)
        self.assertEqual(req["id"], "sgq-1")
        self.assertEqual(set(req.keys()),
                         {"id", "document_ref", "document_sha256",
                          "signer_ref", "reference_stub", "state",
                          "signed_here", "cryptography_performed_here",
                          "created_by", "created_utc"})
        self.assertTrue(req["reference_stub"])
        self.assertEqual(req["state"], "recorded_reference_only")
        self.assertFalse(req["signed_here"])
        self.assertFalse(req["cryptography_performed_here"])

    def test_bad_digest_rejected_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.record_signature_request(
                "doc-ref-1", "signer-1", ANALYST, document_sha256="abc123")
        req = self.ext.record_signature_request("doc-ref-1", "signer-1",
                                                ANALYST)
        self.assertEqual(req["id"], "sgq-1")
        self.assertIsNone(req["document_sha256"])

    def test_events_verbatim_and_view_derived(self):
        req = self.ext.record_signature_request("doc-ref-9", "signer-2",
                                                ANALYST)
        empty = self.ext.signature_view(req["id"], VIEWER)
        self.assertEqual(empty["event_count"], 0)
        self.assertIsNone(empty["latest_status"])
        event = self.ext.record_signature_event(req["id"], "signed", ANALYST)
        self.assertEqual(set(event.keys()),
                         {"id", "request_id", "status", "reference_stub",
                          "signed_here", "recorded_by", "recorded_utc"})
        self.assertTrue(event["reference_stub"])
        self.assertFalse(event["signed_here"])
        with self.assertRaises(ValidationError):
            self.ext.record_signature_event(req["id"], "verified", ANALYST)
        with self.assertRaises(NotFoundError):
            self.ext.record_signature_event("sgq-99", "signed", ANALYST)
        view = self.ext.signature_view(req["id"], VIEWER)
        self.assertEqual(view["event_count"], 1)
        self.assertEqual(view["latest_status"], "signed")

    def test_no_sign_or_verify_surface(self):
        """The reference form is the whole surface: no method here can
        produce or check a signature."""
        for name in ("sign", "sign_document", "verify",
                     "verify_signature", "apply_signature"):
            self.assertFalse(hasattr(self.ext, name), name)


# -- idx 654: E-workflow tooling (reference, as drafted) ----------------------


class TestWorkflowReference(AdditionFixture):
    STEPS = [{"step": "intake", "action": "collect forms"},
             {"step": "approval", "action": "route to approver"}]

    def test_definition_shape_and_stub_labels(self):
        """Workflow definitions are stated step data, labeled reference,
        never executed."""
        wf = self.ext.define_workflow_reference("Leave request flow",
                                                self.STEPS, ANALYST)
        self.assertEqual(wf["id"], "wfr-1")
        self.assertEqual(set(wf.keys()),
                         {"id", "name", "steps", "reference_stub", "state",
                          "executed_here", "created_by", "created_utc"})
        self.assertTrue(wf["reference_stub"])
        self.assertEqual(wf["state"], "recorded_reference_only")
        self.assertFalse(wf["executed_here"])
        self.assertEqual(wf["steps"], self.STEPS)

    def test_step_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.define_workflow_reference("Empty", [], ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.define_workflow_reference(
                "Bad", [{"step": "only"}], ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.define_workflow_reference(
                "Bad", [{"step": "a", "action": "  "}], ANALYST)

    def test_runs_recorded_as_reported(self):
        wf = self.ext.define_workflow_reference("Travel voucher flow",
                                                self.STEPS, ANALYST)
        run = self.ext.record_workflow_run_reference(
            wf["id"], "completed", ANALYST, reported_steps=2)
        self.assertEqual(run["id"], "wfx-1")
        self.assertEqual(set(run.keys()),
                         {"id", "workflow_id", "outcome", "reported_steps",
                          "reference_stub", "state", "executed_here",
                          "recorded_by", "recorded_utc"})
        self.assertTrue(run["reference_stub"])
        self.assertFalse(run["executed_here"])
        with self.assertRaises(ValidationError):
            self.ext.record_workflow_run_reference(wf["id"], "ran", ANALYST)
        view = self.ext.workflow_view(wf["id"], VIEWER)
        self.assertEqual(view["run_count"], 1)
        self.assertEqual(view["last_outcome"], "completed")

    def test_definition_does_not_execute(self):
        """Defining a workflow and recording a run creates no core
        dataset and touches no core state."""
        before = [d["id"] for d in self.store.list()]
        wf = self.ext.define_workflow_reference("Flow", self.STEPS, ANALYST)
        self.ext.record_workflow_run_reference(wf["id"], "failed", ANALYST)
        self.assertEqual([d["id"] for d in self.store.list()], before)


# -- idx 655: Mobile client capabilities (built) ------------------------------


class TestMobileClients(AdditionFixture):
    def test_register_shape_labels_and_uniqueness(self):
        """Client registrations are records about clients; no client
        software ships here."""
        client = self.ext.register_mobile_client("agency-ios-app", "ios",
                                                 ANALYST)
        self.assertEqual(client["id"], "mbc-1")
        self.assertEqual(set(client.keys()),
                         {"id", "client_ref", "platform",
                          "client_software_here", "created_by", "created_utc"})
        self.assertFalse(client["client_software_here"])
        with self.assertRaises(ValidationError):
            self.ext.register_mobile_client("agency-ios-app", "android",
                                            ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.register_mobile_client("other-app", "windows", ANALYST)
        # Rejected registrations consume no id.
        second = self.ext.register_mobile_client("field-android", "android",
                                                 ANALYST)
        self.assertEqual(second["id"], "mbc-2")

    def test_capability_declarations_as_data(self):
        client = self.ext.register_mobile_client("app", "mobile_web", ANALYST)
        decl = self.ext.declare_client_capability(
            client["id"], "dashboard_view", ANALYST)
        self.assertEqual(decl["id"], "mbp-1")
        self.assertEqual(set(decl.keys()),
                         {"id", "client_id", "capability", "declared_by",
                          "declared_utc"})
        with self.assertRaises(ValidationError):
            self.ext.declare_client_capability(client["id"], "dashboard_view",
                                               ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.declare_client_capability(client["id"], "push_notify",
                                               ANALYST)
        with self.assertRaises(NotFoundError):
            self.ext.declare_client_capability("mbc-99", "report_view",
                                               ANALYST)

    def test_usage_recorded_as_reported(self):
        client = self.ext.register_mobile_client("app", "ios", ANALYST)
        usage = self.ext.record_client_usage(
            client["id"], "dataset_query", 4, ANALYST)
        self.assertEqual(usage["id"], "mbu-1")
        self.assertEqual(set(usage.keys()),
                         {"id", "client_id", "capability", "reported_count",
                          "measured_here", "recorded_by", "recorded_utc"})
        self.assertFalse(usage["measured_here"])
        with self.assertRaises(ValidationError):
            self.ext.record_client_usage(client["id"], "dataset_query", -1,
                                         ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.record_client_usage(client["id"], "dataset_query", 1.5,
                                         ANALYST)

    def test_view_derives_declarations_and_reported_total(self):
        client = self.ext.register_mobile_client("app", "android", ANALYST)
        self.ext.declare_client_capability(client["id"], "dataset_query",
                                           ANALYST)
        self.ext.declare_client_capability(client["id"], "report_view",
                                           ANALYST)
        self.ext.record_client_usage(client["id"], "dataset_query", 4,
                                     ANALYST)
        self.ext.record_client_usage(client["id"], "report_view", 3, ANALYST)
        view = self.ext.mobile_client_view(client["id"], VIEWER)
        self.assertEqual(view["capability_count"], 2)
        self.assertEqual(view["usage_record_count"], 2)
        # The total is the sum of the *reported* counts (4 + 3).
        self.assertEqual(view["reported_usage_total"], 7)
        stored = self.ext.get_mobile_client(client["id"], ADMIN)
        self.assertNotIn("reported_usage_total", stored)
        self.assertNotIn("capability_count", stored)


# -- Fresh negative control: the reported-usage total seam ---------------------


def _canonical_usage_total_expectation(case, ext):
    """Canonical expectation for the reported-usage total seam.

    Usage reports of 4 and 3 for one client derive a total of 7:
    the total is the SUM of the recorded reports. Stated once here
    so the real implementation and the mutant are judged by exactly
    the same expectation.
    """
    client = ext.register_mobile_client("drill-app", "ios", ANALYST)
    ext.record_client_usage(client["id"], "dataset_query", 4, ANALYST)
    ext.record_client_usage(client["id"], "report_view", 3, ANALYST)
    view = ext.mobile_client_view(client["id"], VIEWER)
    case.assertEqual(view["usage_record_count"], 2)
    case.assertEqual(view["reported_usage_total"], 7)


class _FirstCountEchoAddition(AnalyticsExtensionsAddition):
    """Mutant: the total seam echoes the first report's count
    instead of summing the reports."""

    @staticmethod
    def _derive_reported_usage_total(usage_records):
        return usage_records[0]["reported_count"] if usage_records else 0


class TestReportedUsageNegativeControl(AdditionFixture):
    def test_canonical_expectation_holds(self):
        _canonical_usage_total_expectation(self, self.ext)

    def test_mutant_is_rejected(self):
        """Fresh negative control, in the house three-part form: the
        canonical expectation is stated, the real implementation
        meets it, and the first-count-echo mutant is rejected by
        it -- proving the suite catches a non-summing total, not
        merely that code ran. Verified against the real file by the
        drill recorded in tests/README.md."""
        _canonical_usage_total_expectation(self, self.ext)
        audit = AuditLog()
        store = DatasetStore(audit=audit)
        store.ingest_json("sales", sales_json_text(), ADMIN)
        mutant = _FirstCountEchoAddition(store)
        with self.assertRaises(AssertionError):
            _canonical_usage_total_expectation(self, mutant)


# -- Cross-cutting --------------------------------------------------------------


def _all_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _all_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _all_keys(item)


class TestCrossCutting(AdditionFixture):
    def test_viewer_write_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_service_tool("Tool", "hr", VIEWER)
        self.assertIn("exta_register_service_tool:denied",
                      self.audit_actions())
        # The denial allocated nothing: the next valid id is still 1.
        tool = self.ext.register_service_tool("Tool", "hr", ANALYST)
        self.assertEqual(tool["id"], "bto-1")
        self.assertIn("exta_register_service_tool", self.audit_actions())

    def test_reference_records_leave_core_untouched(self):
        """Recording the reference surfaces creates no core dataset
        and changes no core row."""
        before_ids = [d["id"] for d in self.store.list()]
        before_rows = self.store.rows(self.ds)
        req = self.ext.record_signature_request(
            "doc-1", "signer-1", ANALYST, document_sha256=DOC_SHA256)
        self.ext.record_signature_event(req["id"], "signed", ANALYST)
        wf = self.ext.define_workflow_reference(
            "Flow", [{"step": "a", "action": "b"}], ANALYST)
        self.ext.record_workflow_run_reference(wf["id"], "completed", ANALYST)
        self.assertEqual([d["id"] for d in self.store.list()], before_ids)
        self.assertEqual(self.store.rows(self.ds), before_rows)

    def test_no_score_keys_anywhere_on_new_surface(self):
        """Analytics doctrine: no computed scores. A recursive scan
        of one record of every new kind, plus every view, finds no
        score-shaped key; reported counts stay counts."""
        tool = self.ext.register_service_tool("Tool", "finance", ANALYST)
        self.ext.record_service_tool_run(tool["id"], "completed", ANALYST,
                                         reported_items=2)
        req = self.ext.record_signature_request(
            "doc-1", "signer-1", ANALYST, document_sha256=DOC_SHA256)
        self.ext.record_signature_event(req["id"], "pending", ANALYST)
        wf = self.ext.define_workflow_reference(
            "Flow", [{"step": "a", "action": "b"}], ANALYST)
        self.ext.record_workflow_run_reference(wf["id"], "completed", ANALYST)
        client = self.ext.register_mobile_client("app", "ios", ANALYST)
        self.ext.declare_client_capability(client["id"], "dataset_query",
                                           ANALYST)
        self.ext.record_client_usage(client["id"], "dataset_query", 5,
                                     ANALYST)
        surfaces = [
            tool,
            self.ext.service_tool_view(tool["id"], ADMIN),
            req,
            self.ext.signature_view(req["id"], ADMIN),
            wf,
            self.ext.workflow_view(wf["id"], ADMIN),
            client,
            self.ext.mobile_client_view(client["id"], ADMIN),
        ]
        banned = ("score", "rating", "rank", "grade", "percentile")
        for surface in surfaces:
            for key in _all_keys(surface):
                for fragment in banned:
                    self.assertNotIn(fragment, key.lower(),
                                     "%s in %r" % (fragment, key))


if __name__ == "__main__":
    unittest.main()
