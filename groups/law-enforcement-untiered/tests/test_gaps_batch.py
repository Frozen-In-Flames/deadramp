"""Final GAPS batch tests for the Law Enforcement untiered set.

Traces to: the 9 open Extended entries of this set's union spec
(``UNION-SPEC.md`` gap list, GAPS.md section "Untiered Set 17 --
Law Enforcement (2 forks, tier null)"), closed by
``lawenf/extensions.py`` under ``../../gaps-batch/DECISION.md``:
7 built as records in-substrate, 1 shipped as a labeled
reference implementation (operational risk-assessment tooling),
and 1 re-judged to a written re-scope under PLATFORM-LAYER.md
decision 6 (workspace multi-tenancy / platform layer -- no code,
see ``BATCH.md``).

Every test names the entry it pins. Cross-cutting pins: the hard
privacy rule binds the whole extension surface (exact key sets;
no parameter can accept content, query/note text, or a person's
identifier -- ``TypeError`` by signature); tier null binds the
whole surface (a recursive scan finds no tier-shaped key, no
float, and no numeric list in any extension record or view); no
key anywhere names a score (ratings are records; scoring is an
engine, and no engine is built here); stub records carry
``reference_stub: True``; coordination records carry
``reference_transport: True``; denied attempts are audited
``ext_<action>:denied``; failed operations consume no id.

The fresh negative control is in
:class:`TestChainDegreeNegativeControl`: the chain-degree seam
``LawEnfExtensions._chain_degree`` mutated to swap in/out degree
must not produce the canonical degrees.
"""

import unittest

from lawenf.errors import NotFoundError, PermissionDenied, ValidationError
from lawenf.extensions import LawEnfExtensions

from lawenf_helpers import (
    ADMIN, MEMBER, OUTSIDER, VIEWER, DOC_SHA256, fresh_store, make_store,
)


class MutantExtensions(LawEnfExtensions):
    """Negative-control mutant: the degree seam swaps in/out."""

    @staticmethod
    def _chain_degree(edges, reference_id):
        in_degree, out_degree = LawEnfExtensions._chain_degree(
            edges, reference_id)
        return out_degree, in_degree


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.matter = make_store()
        self.ext = LawEnfExtensions(self.store)
        self.mid = self.matter["id"]

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]


def _walk(value):
    """Yield every (key, value) pair and scalar in a record/view."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


class TestOperationsAndPlans(BatchFixture):
    """Entry: Command-and-control & operational planning platform
    (built -- planning records; nothing is commanded here)."""

    def test_operation_shape_and_labels(self):
        op = self.ext.record_operation(self.mid, "OP-ALPHA", MEMBER,
                                       plan_ref="PLAN-1")
        self.assertEqual(op["id"], "opn-1")
        self.assertEqual(
            set(op.keys()),
            {"id", "matter_id", "operation_ref", "plan_ref",
             "commanded_here", "orders_issued_here", "status",
             "created_by", "created_utc"})
        self.assertIs(op["commanded_here"], False)
        self.assertIs(op["orders_issued_here"], False)
        self.assertEqual(op["status"], "recorded")

    def test_plan_shape_and_labels(self):
        op = self.ext.record_operation(self.mid, "OP-ALPHA", MEMBER)
        plan = self.ext.record_plan(self.mid, "PLAN-1", MEMBER,
                                    operation_id=op["id"])
        self.assertEqual(plan["id"], "pln-1")
        self.assertEqual(
            set(plan.keys()),
            {"id", "matter_id", "plan_ref", "operation_id",
             "definition_only", "executed_here", "status",
             "created_by", "created_utc"})
        self.assertIs(plan["definition_only"], True)
        self.assertIs(plan["executed_here"], False)

    def test_duplicate_ref_rejected_and_no_id_consumed(self):
        self.ext.record_operation(self.mid, "OP-ALPHA", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_operation(self.mid, "OP-ALPHA", MEMBER)
        op2 = self.ext.record_operation(self.mid, "OP-BETA", MEMBER)
        self.assertEqual(op2["id"], "opn-2")

    def test_plan_for_unknown_operation_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_plan(self.mid, "PLAN-1", MEMBER,
                                 operation_id="opn-999")

    def test_operation_view_counts_derived_not_stored(self):
        op = self.ext.record_operation(self.mid, "OP-ALPHA", MEMBER)
        self.ext.record_coordination_message(
            self.mid, "MSG-1", MEMBER, operation_id=op["id"])
        self.ext.record_location_report(
            self.mid, "LOC-1", MEMBER, operation_id=op["id"])
        self.ext.register_after_action_report(
            self.mid, "AAR-1", MEMBER, operation_id=op["id"])
        view = self.ext.operation_view(self.mid, op["id"], MEMBER)
        self.assertEqual(view["message_count"], 1)
        self.assertEqual(view["location_report_count"], 1)
        self.assertEqual(view["after_action_report_count"], 1)
        self.assertIs(view["derived_at_read"], True)
        stored = self.ext.get_operation(self.mid, op["id"], MEMBER)
        self.assertNotIn("message_count", stored)


class TestCoordinationMessages(BatchFixture):
    """Entry: Real-time team coordination & encrypted messaging
    engines / real transports (built -- records in the
    Communication adjudicated form: digest-only bodies, receipts
    over a labeled reference transport; nothing transmitted,
    nothing encrypted here)."""

    def test_message_shape_and_labels(self):
        msg = self.ext.record_coordination_message(
            self.mid, "MSG-1", MEMBER, channel_ref="CH-OPS",
            body_sha256=DOC_SHA256)
        self.assertEqual(msg["id"], "msg-1")
        self.assertEqual(
            set(msg.keys()),
            {"id", "matter_id", "message_ref", "channel_ref",
             "operation_id", "body_sha256", "content_held",
             "reference_transport", "transmitted_here",
             "encrypted_here", "status", "created_by", "created_utc"})
        self.assertEqual(msg["body_sha256"], DOC_SHA256)
        self.assertIs(msg["content_held"], False)
        self.assertIs(msg["reference_transport"], True)
        self.assertIs(msg["transmitted_here"], False)
        self.assertIs(msg["encrypted_here"], False)

    def test_body_must_be_a_digest_never_text(self):
        with self.assertRaises(ValidationError):
            self.ext.record_coordination_message(
                self.mid, "MSG-1", MEMBER, body_sha256="not-a-digest")
        with self.assertRaises(ValidationError):
            self.ext.record_coordination_message(
                self.mid, "MSG-1", MEMBER, body_sha256="A" * 64)
        msg = self.ext.record_coordination_message(self.mid, "MSG-1",
                                                   MEMBER)
        self.assertEqual(msg["id"], "msg-1")
        self.assertIsNone(msg["body_sha256"])

    def test_receipts_verbatim_and_view_derives_latest(self):
        msg = self.ext.record_coordination_message(self.mid, "MSG-1",
                                                   MEMBER)
        r1 = self.ext.record_delivery_receipt(self.mid, msg["id"],
                                              "delivered", MEMBER)
        self.assertEqual(
            set(r1.keys()),
            {"id", "matter_id", "message_id", "outcome",
             "reference_transport", "transmitted_here", "created_by",
             "created_utc"})
        self.assertIs(r1["reference_transport"], True)
        self.ext.record_delivery_receipt(self.mid, msg["id"],
                                         "Acknowledged by Team 2", MEMBER)
        view = self.ext.message_view(self.mid, msg["id"], MEMBER)
        self.assertEqual(view["receipt_count"], 2)
        self.assertEqual(view["latest_outcome"], "Acknowledged by Team 2")
        stored = self.ext.get_coordination_message(self.mid, msg["id"],
                                                   MEMBER)
        self.assertNotIn("latest_outcome", stored)
        self.assertNotIn("receipt_count", stored)

    def test_receipt_for_unknown_message_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_delivery_receipt(self.mid, "msg-999",
                                             "delivered", MEMBER)


class TestLocationReports(BatchFixture):
    """Entry: GPS mapping & location services (built --
    caller-reported location records; nothing sensed or tracked,
    and no coordinate value exists in any shape)."""

    def test_location_shape_and_labels(self):
        loc = self.ext.record_location_report(
            self.mid, "LOC-1", MEMBER, place_ref="SECTOR-7",
            label="staging area, as reported")
        self.assertEqual(loc["id"], "loc-1")
        self.assertEqual(
            set(loc.keys()),
            {"id", "matter_id", "location_ref", "place_ref", "label",
             "operation_id", "tracked_here", "sensed_here", "status",
             "created_by", "created_utc"})
        self.assertEqual(loc["label"], "staging area, as reported")
        self.assertIs(loc["tracked_here"], False)
        self.assertIs(loc["sensed_here"], False)
        self.assertEqual(loc["status"], "recorded_report")

    def test_duplicate_location_ref_rejected(self):
        self.ext.record_location_report(self.mid, "LOC-1", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_location_report(self.mid, "LOC-1", MEMBER)


class TestAfterActionReports(BatchFixture):
    """Entry: After-action documentation & reporting engine
    (built -- registry records with digests; reports are
    assembled by humans elsewhere, generated nowhere here)."""

    def test_report_shape_and_labels(self):
        aar = self.ext.register_after_action_report(
            self.mid, "AAR-1", MEMBER, report_sha256=DOC_SHA256)
        self.assertEqual(aar["id"], "aar-1")
        self.assertEqual(
            set(aar.keys()),
            {"id", "matter_id", "report_ref", "report_sha256",
             "operation_id", "content_held", "generated_here",
             "assembled_here", "status", "created_by", "created_utc"})
        self.assertIs(aar["content_held"], False)
        self.assertIs(aar["generated_here"], False)
        self.assertIs(aar["assembled_here"], False)

    def test_report_digest_validated(self):
        with self.assertRaises(ValidationError):
            self.ext.register_after_action_report(
                self.mid, "AAR-1", MEMBER, report_sha256="short")


class TestChainReferencesAndLinks(BatchFixture):
    """Entry: Blockchain intelligence & multi-chain investigation
    graph engine (built -- reference and reported-link records;
    degrees derived at read; the graph is never traversed and no
    attribution is computed)."""

    def _refs(self):
        a = self.ext.register_chain_reference(self.mid, "CHAIN-A", MEMBER,
                                              network_label="net-1")
        b = self.ext.register_chain_reference(self.mid, "CHAIN-B", MEMBER)
        c = self.ext.register_chain_reference(self.mid, "CHAIN-C", MEMBER)
        return a, b, c

    def test_reference_shape_and_labels(self):
        a, _, _ = self._refs()
        self.assertEqual(a["id"], "chn-1")
        self.assertEqual(
            set(a.keys()),
            {"id", "matter_id", "chain_ref", "network_label",
             "analyzed_here", "status", "created_by", "created_utc"})
        self.assertIs(a["analyzed_here"], False)

    def test_link_shape_and_labels(self):
        a, b, _ = self._refs()
        link = self.ext.record_chain_link(self.mid, a["id"], b["id"],
                                          "reported_transfer", MEMBER)
        self.assertEqual(link["id"], "lnk-1")
        self.assertEqual(
            set(link.keys()),
            {"id", "matter_id", "from_reference_id", "to_reference_id",
             "relation_label", "reported_only", "traversed_here",
             "attribution_computed_here", "created_by", "created_utc"})
        self.assertIs(link["reported_only"], True)
        self.assertIs(link["traversed_here"], False)
        self.assertIs(link["attribution_computed_here"], False)

    def test_degrees_derived_at_read_not_stored(self):
        a, b, c = self._refs()
        self.ext.record_chain_link(self.mid, a["id"], b["id"], "r", MEMBER)
        self.ext.record_chain_link(self.mid, a["id"], c["id"], "r", MEMBER)
        self.ext.record_chain_link(self.mid, b["id"], c["id"], "r", MEMBER)
        view_a = self.ext.chain_reference_view(self.mid, a["id"], MEMBER)
        self.assertEqual(view_a["in_degree"], 0)
        self.assertEqual(view_a["out_degree"], 2)
        self.assertEqual(view_a["degree"], 2)
        view_c = self.ext.chain_reference_view(self.mid, c["id"], MEMBER)
        self.assertEqual(view_c["in_degree"], 2)
        self.assertEqual(view_c["out_degree"], 0)
        stored = self.ext.get_chain_reference(self.mid, a["id"], MEMBER)
        self.assertNotIn("degree", stored)
        self.assertNotIn("in_degree", stored)

    def test_link_endpoints_must_exist_and_no_id_consumed(self):
        a, _, _ = self._refs()
        with self.assertRaises(NotFoundError):
            self.ext.record_chain_link(self.mid, a["id"], "chn-999", "r",
                                       MEMBER)
        link = self.ext.record_chain_link(self.mid, a["id"], a["id"], "r",
                                          MEMBER)
        self.assertEqual(link["id"], "lnk-1")

    def test_cross_matter_reference_is_not_found(self):
        a, _, _ = self._refs()
        other = self.store.create_matter("MATTER-REF-002", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.get_chain_reference(other["id"], a["id"], MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_chain_link(other["id"], a["id"], a["id"], "r",
                                       MEMBER)


class TestChainDegreeNegativeControl(BatchFixture):
    """Fresh negative control: the chain-degree seam.

    Traced claim: **a chain reference's in-degree counts the
    recorded links whose target it is, and its out-degree counts
    the recorded links whose source it is** (the investigation
    graph entry's only derivation). Each canonical case asserts
    (1) the real implementation's outcome, (2) the mutant seam
    (in/out swapped) would NOT produce it, and (3) treating the
    mutant's outcome as the expected outcome fails.
    """

    def _setup_graph(self, ext):
        a = ext.register_chain_reference(self.mid, "CHAIN-A", MEMBER)
        b = ext.register_chain_reference(self.mid, "CHAIN-B", MEMBER)
        c = ext.register_chain_reference(self.mid, "CHAIN-C", MEMBER)
        ext.record_chain_link(self.mid, a["id"], b["id"], "r", MEMBER)
        ext.record_chain_link(self.mid, a["id"], c["id"], "r", MEMBER)
        ext.record_chain_link(self.mid, b["id"], c["id"], "r", MEMBER)
        return a, b, c

    def test_source_degree_canonical(self):
        a, _, _ = self._setup_graph(self.ext)
        view = self.ext.chain_reference_view(self.mid, a["id"], MEMBER)
        self.assertEqual(view["in_degree"], 0)
        self.assertEqual(view["out_degree"], 2)
        mutant = MutantExtensions(self.store)
        ma, _, _ = self._setup_graph(mutant)
        mview = mutant.chain_reference_view(self.mid, ma["id"], MEMBER)
        self.assertEqual(mview["in_degree"], 2)
        self.assertEqual(mview["out_degree"], 0)
        with self.assertRaises(AssertionError):
            self.assertEqual(mview["out_degree"], 2)

    def test_sink_degree_canonical(self):
        _, _, c = self._setup_graph(self.ext)
        view = self.ext.chain_reference_view(self.mid, c["id"], MEMBER)
        self.assertEqual(view["in_degree"], 2)
        self.assertEqual(view["out_degree"], 0)
        mutant = MutantExtensions(self.store)
        _, _, mc = self._setup_graph(mutant)
        mview = mutant.chain_reference_view(self.mid, mc["id"], MEMBER)
        with self.assertRaises(AssertionError):
            self.assertEqual(mview["in_degree"], 2)

    def test_isolated_reference_has_zero_degree(self):
        ref = self.ext.register_chain_reference(self.mid, "CHAIN-Z",
                                                MEMBER)
        view = self.ext.chain_reference_view(self.mid, ref["id"], MEMBER)
        self.assertEqual(view["in_degree"], 0)
        self.assertEqual(view["out_degree"], 0)
        self.assertEqual(view["degree"], 0)


class TestLeadsAndReportedLinks(BatchFixture):
    """Entry: All-source fusion & lead/identity resolution (built
    -- lead records and caller-reported link records; a link
    exists only because someone reported it, nothing is resolved
    or inferred, and no shape can hold an identity value)."""

    def test_lead_shape_and_labels(self):
        lead = self.ext.record_lead(self.mid, "LEAD-1", MEMBER)
        self.assertEqual(lead["id"], "led-1")
        self.assertEqual(
            set(lead.keys()),
            {"id", "matter_id", "lead_ref", "source_id",
             "resolved_here", "identified_here", "status",
             "created_by", "created_utc"})
        self.assertIs(lead["resolved_here"], False)
        self.assertIs(lead["identified_here"], False)

    def test_lead_may_bind_a_core_source(self):
        source = self.store.create_source(self.mid, "SRC-1", "secondary",
                                          MEMBER)
        lead = self.ext.record_lead(self.mid, "LEAD-1", MEMBER,
                                    source_id=source["id"])
        self.assertEqual(lead["source_id"], source["id"])
        with self.assertRaises(NotFoundError):
            self.ext.record_lead(self.mid, "LEAD-2", MEMBER,
                                 source_id="src-999")

    def test_reported_link_shape_and_labels(self):
        lead = self.ext.record_lead(self.mid, "LEAD-1", MEMBER)
        link = self.ext.record_reported_link(self.mid, lead["id"],
                                             "EXT-REF-9", "reported_same",
                                             MEMBER)
        self.assertEqual(link["id"], "rlk-1")
        self.assertEqual(
            set(link.keys()),
            {"id", "matter_id", "lead_id", "other_ref",
             "relation_label", "reported_only", "resolved_here",
             "inferred_here", "created_by", "created_utc"})
        self.assertIs(link["reported_only"], True)
        self.assertIs(link["resolved_here"], False)
        self.assertIs(link["inferred_here"], False)

    def test_lead_view_count_derived_not_stored(self):
        lead = self.ext.record_lead(self.mid, "LEAD-1", MEMBER)
        self.ext.record_reported_link(self.mid, lead["id"], "X-1", "r",
                                      MEMBER)
        self.ext.record_reported_link(self.mid, lead["id"], "X-2", "r",
                                      MEMBER)
        view = self.ext.lead_view(self.mid, lead["id"], MEMBER)
        self.assertEqual(view["reported_link_count"], 2)
        stored = self.ext.get_lead(self.mid, lead["id"], MEMBER)
        self.assertNotIn("reported_link_count", stored)

    def test_recording_links_changes_no_core_record(self):
        source = self.store.create_source(self.mid, "SRC-1", "secondary",
                                          MEMBER)
        before_report = self.store.matter_report(self.mid, MEMBER)
        before_sources = self.store.list_sources(self.mid, MEMBER)
        lead = self.ext.record_lead(self.mid, "LEAD-1", MEMBER,
                                    source_id=source["id"])
        self.ext.record_reported_link(self.mid, lead["id"], "X-1", "r",
                                      MEMBER)
        self.assertEqual(self.store.matter_report(self.mid, MEMBER),
                         before_report)
        self.assertEqual(self.store.list_sources(self.mid, MEMBER),
                         before_sources)


class TestInvestigationModels(BatchFixture):
    """Entry: AI investigation models (built records form --
    request records and opaque result references; no model runs
    and no result content is held)."""

    def test_request_shape_and_labels(self):
        req = self.ext.record_investigation_request(
            self.mid, "REQ-1", MEMBER, model_label="vendor-model-x")
        self.assertEqual(req["id"], "air-1")
        self.assertEqual(
            set(req.keys()),
            {"id", "matter_id", "request_ref", "model_label", "lead_id",
             "inference_here", "status", "created_by", "created_utc"})
        self.assertIs(req["inference_here"], False)
        self.assertEqual(req["model_label"], "vendor-model-x")

    def test_result_is_an_opaque_reference_only(self):
        req = self.ext.record_investigation_request(self.mid, "REQ-1",
                                                    MEMBER)
        res = self.ext.record_investigation_result(
            self.mid, req["id"], "RESULT-REF-1", MEMBER,
            outcome="reported_complete")
        self.assertEqual(res["id"], "ars-1")
        self.assertEqual(
            set(res.keys()),
            {"id", "matter_id", "request_id", "result_ref", "outcome",
             "inference_here", "output_held", "created_by", "created_utc"})
        self.assertIs(res["inference_here"], False)
        self.assertIs(res["output_held"], False)
        with self.assertRaises(NotFoundError):
            self.ext.record_investigation_result(
                self.mid, "air-999", "RESULT-REF-2", MEMBER)


class TestRiskAssessments(BatchFixture):
    """Entry: Operational risk-assessment tooling (reference --
    labeled reference implementation; outcomes are reported
    labels recorded verbatim, and no score is computed or
    storable)."""

    def test_assessment_shape_and_stub_labels(self):
        rsk = self.ext.register_risk_assessment(self.mid, "RISK-1", MEMBER)
        self.assertEqual(rsk["id"], "rsk-1")
        self.assertEqual(
            set(rsk.keys()),
            {"id", "matter_id", "assessment_ref", "operation_id",
             "reference_stub", "assessed_here", "status",
             "created_by", "created_utc"})
        self.assertIs(rsk["reference_stub"], True)
        self.assertIs(rsk["assessed_here"], False)
        self.assertEqual(rsk["status"], "recorded_reference_only")

    def test_outcome_is_a_verbatim_label_never_a_score(self):
        rsk = self.ext.register_risk_assessment(self.mid, "RISK-1", MEMBER)
        out = self.ext.record_risk_outcome(
            self.mid, rsk["id"], "Elevated, per platform report", MEMBER)
        self.assertEqual(out["id"], "rko-1")
        self.assertEqual(
            set(out.keys()),
            {"id", "matter_id", "assessment_id", "outcome_label",
             "reference_stub", "assessed_here", "computed_here",
             "created_by", "created_utc"})
        self.assertEqual(out["outcome_label"],
                         "Elevated, per platform report")
        self.assertIs(out["computed_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_risk_outcome(self.mid, rsk["id"], 5, MEMBER)
        with self.assertRaises(TypeError):
            self.ext.record_risk_outcome(self.mid, rsk["id"], "ok",
                                         MEMBER, score=5)


class TestPrivacyShapePins(BatchFixture):
    """Cross-cutting: the hard privacy rule, by signature.

    No extension method can accept content, message/report body
    text, query text, note text, a person's name or identifier,
    an address value, or coordinates: passing any such keyword
    raises ``TypeError`` before anything is recorded.
    """

    def test_no_content_or_text_parameters(self):
        with self.assertRaises(TypeError):
            self.ext.record_coordination_message(
                self.mid, "MSG-1", MEMBER, body_text="hello")
        with self.assertRaises(TypeError):
            self.ext.record_coordination_message(
                self.mid, "MSG-1", MEMBER, content="hello")
        with self.assertRaises(TypeError):
            self.ext.register_after_action_report(
                self.mid, "AAR-1", MEMBER, report_text="after action")
        with self.assertRaises(TypeError):
            self.ext.record_investigation_request(
                self.mid, "REQ-1", MEMBER, prompt="investigate")
        with self.assertRaises(TypeError):
            self.ext.record_investigation_request(
                self.mid, "REQ-1", MEMBER, query_text="investigate")
        with self.assertRaises(TypeError):
            self.ext.record_investigation_result(
                self.mid, "air-1", "R-1", MEMBER, result_text="found")
        msg = self.ext.record_coordination_message(self.mid, "MSG-1",
                                                   MEMBER)
        self.assertEqual(msg["id"], "msg-1")

    def test_no_person_or_identity_parameters(self):
        with self.assertRaises(TypeError):
            self.ext.record_operation(self.mid, "OP-1", MEMBER,
                                      subject_name="someone")
        with self.assertRaises(TypeError):
            self.ext.record_lead(self.mid, "LEAD-1", MEMBER,
                                 name="someone")
        with self.assertRaises(TypeError):
            self.ext.record_lead(self.mid, "LEAD-1", MEMBER,
                                 address="1 Main St")
        with self.assertRaises(TypeError):
            self.ext.record_lead(self.mid, "LEAD-1", MEMBER,
                                 identifier="ID-1")
        with self.assertRaises(TypeError):
            self.ext.record_reported_link(self.mid, "led-1", "X-1", "r",
                                          MEMBER, identity="someone")
        with self.assertRaises(TypeError):
            self.ext.record_chain_link(self.mid, "chn-1", "chn-2", "r",
                                       MEMBER, note_text="a note")

    def test_no_coordinate_parameters(self):
        with self.assertRaises(TypeError):
            self.ext.record_location_report(self.mid, "LOC-1", MEMBER,
                                            latitude=1)
        with self.assertRaises(TypeError):
            self.ext.record_location_report(self.mid, "LOC-1", MEMBER,
                                            longitude=2)
        with self.assertRaises(TypeError):
            self.ext.record_location_report(self.mid, "LOC-1", MEMBER,
                                            coordinates=[1, 2])


class TestAccessAndBoundaries(BatchFixture):
    """Cross-cutting: RBAC mapped onto the core action set, the
    matter-membership boundary, the closed-matter rule, and the
    audit discipline (successes as ``ext_<action>``, denials as
    ``ext_<action>:denied``)."""

    def test_viewer_writes_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_operation(self.mid, "OP-1", VIEWER)
        with self.assertRaises(PermissionDenied):
            self.ext.record_lead(self.mid, "LEAD-1", VIEWER)
        with self.assertRaises(PermissionDenied):
            self.ext.register_risk_assessment(self.mid, "RISK-1", VIEWER)
        actions = self.audit_actions()
        self.assertIn("ext_operation_record:denied", actions)
        self.assertIn("ext_lead_record:denied", actions)
        self.assertIn("ext_risk_assessment_register:denied", actions)

    def test_outsider_denied_by_membership_and_audited(self):
        self.ext.record_operation(self.mid, "OP-1", MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.record_operation(self.mid, "OP-2", OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.ext.list_operations(self.mid, OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.ext.chain_reference_view(self.mid, "chn-1", OUTSIDER)
        self.assertIn("ext_operation_record:denied", self.audit_actions())

    def test_successes_are_audited_with_ext_prefix(self):
        self.ext.record_operation(self.mid, "OP-1", MEMBER)
        ref = self.ext.register_chain_reference(self.mid, "CHAIN-A",
                                                MEMBER)
        self.ext.record_chain_link(self.mid, ref["id"], ref["id"], "r",
                                   MEMBER)
        actions = self.audit_actions()
        self.assertIn("ext_operation_record", actions)
        self.assertIn("ext_chain_reference_register", actions)
        self.assertIn("ext_chain_link_record", actions)

    def test_closed_matter_rejects_extension_writes(self):
        self.ext.record_operation(self.mid, "OP-1", MEMBER)
        self.store.close_matter(self.mid, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_location_report(self.mid, "LOC-1", MEMBER)
        self.assertEqual(len(self.ext.list_operations(self.mid, MEMBER)),
                         1)

    def test_unknown_matter_is_not_found(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_operation("mat-999", "OP-1", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.list_operations("mat-999", MEMBER)


class TestTierNullAndShapeScan(BatchFixture):
    """Cross-cutting: tier null and shape discipline.

    Every extension record and derived view is scanned
    recursively: no key may name a tier, a baseline, or an
    equivalence; no key may name a score, a rating, or a person /
    content field; no value may be a float; no list may hold
    numbers.
    """

    FORBIDDEN_KEY_PARTS = ("tier", "cmmc", "baseline", "equivalence",
                           "impact_level", "score", "rating", "grade")
    FORBIDDEN_KEYS = {"name", "subject", "subject_name", "party",
                      "address", "content", "body", "body_text",
                      "query", "query_text", "note", "note_text",
                      "person", "identity", "identifier", "latitude",
                      "longitude", "coordinates"}

    def _everything(self):
        ext = self.ext
        mid = self.mid
        op = ext.record_operation(mid, "OP-1", MEMBER, plan_ref="PLAN-1")
        plan = ext.record_plan(mid, "PLAN-1", MEMBER,
                               operation_id=op["id"])
        msg = ext.record_coordination_message(
            mid, "MSG-1", MEMBER, channel_ref="CH-1",
            body_sha256=DOC_SHA256, operation_id=op["id"])
        rcp = ext.record_delivery_receipt(mid, msg["id"], "delivered",
                                          MEMBER)
        msg_view = ext.message_view(mid, msg["id"], MEMBER)
        loc = ext.record_location_report(mid, "LOC-1", MEMBER,
                                         place_ref="SECTOR-7",
                                         label="as reported",
                                         operation_id=op["id"])
        aar = ext.register_after_action_report(
            mid, "AAR-1", MEMBER, report_sha256=DOC_SHA256,
            operation_id=op["id"])
        a = ext.register_chain_reference(mid, "CHAIN-A", MEMBER,
                                         network_label="net-1")
        b = ext.register_chain_reference(mid, "CHAIN-B", MEMBER)
        link = ext.record_chain_link(mid, a["id"], b["id"], "reported",
                                     MEMBER)
        chain_view = ext.chain_reference_view(mid, a["id"], MEMBER)
        lead = ext.record_lead(mid, "LEAD-1", MEMBER)
        rlink = ext.record_reported_link(mid, lead["id"], "EXT-1",
                                         "reported", MEMBER)
        lead_view = ext.lead_view(mid, lead["id"], MEMBER)
        req = ext.record_investigation_request(
            mid, "REQ-1", MEMBER, model_label="vendor-model-x",
            lead_id=lead["id"])
        res = ext.record_investigation_result(
            mid, req["id"], "RESULT-1", MEMBER, outcome="reported")
        rsk = ext.register_risk_assessment(mid, "RISK-1", MEMBER,
                                           operation_id=op["id"])
        rko = ext.record_risk_outcome(mid, rsk["id"], "reported label",
                                      MEMBER)
        op_view = ext.operation_view(mid, op["id"], MEMBER)
        return [op, plan, msg, rcp, msg_view, loc, aar, a, b, link,
                chain_view, lead, rlink, lead_view, req, res, rsk, rko,
                op_view]

    def test_no_tier_key_no_score_key_no_float_no_numeric_list(self):
        for record in self._everything():
            for key, value in _walk(record):
                lowered = key.lower()
                for part in self.FORBIDDEN_KEY_PARTS:
                    self.assertNotIn(
                        part, lowered,
                        "forbidden key part %r in key %r of %r"
                        % (part, key, record))
                self.assertNotIn(
                    lowered, self.FORBIDDEN_KEYS,
                    "forbidden key %r in %r" % (key, record))
                self.assertNotIsInstance(
                    value, float,
                    "float value at %r in %r" % (key, record))
                if isinstance(value, list):
                    for item in value:
                        self.assertNotIsInstance(
                            item, (int, float),
                            "numeric list at %r in %r" % (key, record))

    def test_stub_and_transport_labels_present(self):
        records = self._everything()
        by_id = {r["id"]: r for r in records if "id" in r}
        self.assertIs(by_id["rsk-1"]["reference_stub"], True)
        self.assertIs(by_id["rko-1"]["reference_stub"], True)
        self.assertIs(by_id["msg-1"]["reference_transport"], True)
        self.assertIs(by_id["rcp-1"]["reference_transport"], True)

    def test_extension_surface_is_audited(self):
        self.ext.record_operation(self.mid, "OP-1", MEMBER)
        self.assertIn("ext_operation_record", self.audit_actions())


class TestBareStoreFixture(unittest.TestCase):
    """The extension surface works over a bare core store too."""

    def test_bare_store(self):
        store = fresh_store()
        ext = LawEnfExtensions(store)
        matter = store.create_matter("MATTER-REF-BARE", MEMBER)
        op = ext.record_operation(matter["id"], "OP-1", MEMBER)
        self.assertEqual(op["matter_id"], matter["id"])
        with self.assertRaises(NotFoundError):
            ext.get_operation(matter["id"], "opn-999", MEMBER)
        with self.assertRaises(PermissionDenied):
            ext.list_operations(matter["id"], OUTSIDER)


if __name__ == "__main__":
    unittest.main()
