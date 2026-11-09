"""Final GAPS batch tests — Manufacturing untiered (Set 26).

Pins the extension surface in ``manufacturing.extensions`` for
the section's 1 open entry (idx 958, the engineering-intent
transformation engine including the manufacturing-intelligence
engine entire), closed as a labeled reference implementation
(re-judged from its drafted build-extension disposition; grounds
in BATCH.md).

The pins: request records under the core decision-basis guard's
records form (empty / duplicate / unknown / cross-organization
bases refused with no id consumed); outcome records holding the
external engine's reported label verbatim; the reference labels
on every record; derived-at-read views through the
``_latest_outcome_label`` seam with the stored request's exact
key set free of derived keys; a full flow leaving every core
record byte-identical; RBAC (viewer writes denied, no id
consumed); the no-content signature discipline; and the
recursive scans — no tier / baseline / impact / equivalence key,
no score or money key (the core's forbidden parts), and no float
value anywhere on the surface (tier null, preserved).

The negative control is the fresh one for this surface: the
latest-outcome seam. Its in-suite form is three-legged
(canonical / earliest-reading mutant / assertRaises), and the
live drill on the real module is recorded in tests/README.md.
"""

import copy
import inspect
import unittest

import manufacturing_helpers as H
from manufacturing import extensions as ext_module
from manufacturing.errors import NotFoundError, PermissionDenied, ValidationError
from manufacturing.extensions import ManufacturingExtensions

REQUEST_KEYS = {
    "id", "org_id", "label", "basis_intent_ids", "requested_by_ref",
    "reference_stub", "state", "transformed_here",
    "intelligence_exercised_here", "manufacturability_judged_here",
    "created_by", "created_utc",
}
OUTCOME_KEYS = {
    "id", "request_id", "org_id", "outcome_label", "outcome_basis",
    "reported_decision_ref", "core_decision_id", "reference_stub",
    "state", "transformed_here", "intelligence_exercised_here",
    "manufacturability_judged_here", "recorded_by", "recorded_utc",
}

FORBIDDEN_KEY_PARTS = (
    "score", "grade", "rank", "rating", "rate", "email", "ssn",
    "password", "secret", "salary", "wage", "price", "fee",
    "amount", "cost", "budget",
    "tier", "cmmc", "baseline", "fedramp", "impact", "equivalence",
)


def _scan(obj, path="root"):
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = key.lower()
            for part in FORBIDDEN_KEY_PARTS:
                if part in lowered:
                    raise AssertionError(
                        "forbidden key part %r in key %r at %s"
                        % (part, key, path))
            _scan(value, "%s.%s" % (path, key))
    elif isinstance(obj, (list, tuple)):
        for i, value in enumerate(obj):
            _scan(value, "%s[%d]" % (path, i))
    elif isinstance(obj, float):
        raise AssertionError("float value at %s: %r" % (path, obj))


def make_ext():
    store, audit, org = H.make_store()
    return ManufacturingExtensions(store), store, audit, org


def make_request(ext, store, org, actor=H.OPERATOR):
    intent = H.make_intent(store, org)
    request = ext.register_transformation_request(
        actor, org["id"], "Bracket transformation", [intent["id"]],
        "eng-1")
    return request, intent


class TestTransformationRequests(unittest.TestCase):
    def test_request_record_shape_and_labels(self):
        ext, store, audit, org = make_ext()
        request, intent = make_request(ext, store, org)
        self.assertEqual(request["id"], "trq-1")
        self.assertEqual(set(request), REQUEST_KEYS)
        self.assertEqual(request["basis_intent_ids"], [intent["id"]])
        self.assertIs(request["reference_stub"], True)
        self.assertEqual(request["state"], "recorded_reference_only")
        self.assertIs(request["transformed_here"], False)
        self.assertIs(request["intelligence_exercised_here"], False)
        self.assertIs(request["manufacturability_judged_here"], False)

    def test_empty_basis_refused_and_consumes_no_id(self):
        ext, store, audit, org = make_ext()
        with self.assertRaises(ValidationError):
            ext.register_transformation_request(
                H.OPERATOR, org["id"], "L", [], "eng-1")
        request, _ = make_request(ext, store, org)
        self.assertEqual(request["id"], "trq-1")

    def test_duplicate_basis_refused(self):
        ext, store, audit, org = make_ext()
        intent = H.make_intent(store, org)
        with self.assertRaises(ValidationError):
            ext.register_transformation_request(
                H.OPERATOR, org["id"], "L",
                [intent["id"], intent["id"]], "eng-1")

    def test_unknown_basis_refused(self):
        ext, store, audit, org = make_ext()
        with self.assertRaises(ValidationError):
            ext.register_transformation_request(
                H.OPERATOR, org["id"], "L", ["int-999"], "eng-1")

    def test_cross_organization_basis_refused(self):
        ext, store, audit, org = make_ext()
        other = store.create_organization(H.ADMIN, "other-org", "Other")
        foreign = H.make_intent(store, other)
        with self.assertRaises(ValidationError):
            ext.register_transformation_request(
                H.OPERATOR, org["id"], "L", [foreign["id"]], "eng-1")

    def test_unknown_organization_refused(self):
        ext, store, audit, org = make_ext()
        intent = H.make_intent(store, org)
        with self.assertRaises(NotFoundError):
            ext.register_transformation_request(
                H.OPERATOR, "org-999", "L", [intent["id"]], "eng-1")

    def test_requester_ref_cannot_be_an_email(self):
        ext, store, audit, org = make_ext()
        intent = H.make_intent(store, org)
        with self.assertRaises(ValidationError):
            ext.register_transformation_request(
                H.OPERATOR, org["id"], "L", [intent["id"]],
                "eng@example.com")

    def test_basis_list_is_copied_at_the_boundary(self):
        ext, store, audit, org = make_ext()
        intent = H.make_intent(store, org)
        basis = [intent["id"]]
        request = ext.register_transformation_request(
            H.OPERATOR, org["id"], "L", basis, "eng-1")
        basis.append("int-999")
        stored = ext._requests[request["id"]]
        self.assertEqual(stored["basis_intent_ids"], [intent["id"]])

    def test_viewer_write_denied_and_consumes_no_id(self):
        ext, store, audit, org = make_ext()
        intent = H.make_intent(store, org)
        with self.assertRaises(PermissionDenied):
            ext.register_transformation_request(
                H.VIEWER, org["id"], "L", [intent["id"]], "eng-1")
        request, _ = make_request(ext, store, org)
        self.assertEqual(request["id"], "trq-1")

    def test_request_is_audited_with_ext_prefix(self):
        ext, store, audit, org = make_ext()
        make_request(ext, store, org)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("ext_transformation_request", actions)


class TestTransformationOutcomes(unittest.TestCase):
    def test_outcome_record_shape_and_labels(self):
        ext, store, audit, org = make_ext()
        request, _ = make_request(ext, store, org)
        outcome = ext.record_transformation_outcome(
            H.OPERATOR, request["id"], "reported_transformed",
            reported_decision_ref="ext-dec-1")
        self.assertEqual(outcome["id"], "tro-1")
        self.assertEqual(set(outcome), OUTCOME_KEYS)
        self.assertEqual(outcome["outcome_label"], "reported_transformed")
        self.assertEqual(outcome["outcome_basis"], "engine_reported")
        self.assertIs(outcome["reference_stub"], True)
        self.assertIs(outcome["transformed_here"], False)

    def test_outcome_label_must_be_reported_vocabulary(self):
        ext, store, audit, org = make_ext()
        request, _ = make_request(ext, store, org)
        with self.assertRaises(ValidationError):
            ext.record_transformation_outcome(
                H.OPERATOR, request["id"], "transformed")
        outcome = ext.record_transformation_outcome(
            H.OPERATOR, request["id"], "reported_failed")
        self.assertEqual(outcome["id"], "tro-1")

    def test_outcome_for_unknown_request_refused(self):
        ext, store, audit, org = make_ext()
        with self.assertRaises(NotFoundError):
            ext.record_transformation_outcome(
                H.OPERATOR, "trq-999", "reported_failed")

    def test_outcome_may_cite_a_core_decision_of_the_same_org(self):
        ext, store, audit, org = make_ext()
        request, intent = make_request(ext, store, org)
        decision = H.make_decision(store, org, intent)
        outcome = ext.record_transformation_outcome(
            H.OPERATOR, request["id"], "reported_transformed",
            core_decision_id=decision["id"])
        self.assertEqual(outcome["core_decision_id"], decision["id"])

    def test_outcome_citing_a_foreign_core_decision_refused(self):
        ext, store, audit, org = make_ext()
        request, _ = make_request(ext, store, org)
        other = store.create_organization(H.ADMIN, "other-org", "Other")
        foreign_intent = H.make_intent(store, other)
        foreign_decision = H.make_decision(store, other, foreign_intent)
        with self.assertRaises(ValidationError):
            ext.record_transformation_outcome(
                H.OPERATOR, request["id"], "reported_transformed",
                core_decision_id=foreign_decision["id"])

    def test_outcome_creates_no_core_decision(self):
        ext, store, audit, org = make_ext()
        request, _ = make_request(ext, store, org)
        before = len(store.list_decisions(H.ADMIN))
        ext.record_transformation_outcome(
            H.OPERATOR, request["id"], "reported_transformed",
            reported_decision_ref="ext-dec-1")
        self.assertEqual(len(store.list_decisions(H.ADMIN)), before)


class TestDerivedViewsAndSummary(unittest.TestCase):
    def test_view_derives_count_and_latest_outcome(self):
        ext, store, audit, org = make_ext()
        request, _ = make_request(ext, store, org)
        view = ext.get_transformation_request(H.ADMIN, request["id"])
        self.assertEqual(view["outcome_count"], 0)
        self.assertIsNone(view["latest_outcome_label"])
        ext.record_transformation_outcome(
            H.OPERATOR, request["id"], "reported_partial")
        ext.record_transformation_outcome(
            H.OPERATOR, request["id"], "reported_transformed")
        view = ext.get_transformation_request(H.ADMIN, request["id"])
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_outcome_label"],
                         "reported_transformed")
        stored = ext._requests[request["id"]]
        self.assertEqual(set(stored), REQUEST_KEYS)
        self.assertNotIn("outcome_count", stored)
        self.assertNotIn("latest_outcome_label", stored)

    def test_summary_is_counts_only(self):
        ext, store, audit, org = make_ext()
        request, _ = make_request(ext, store, org)
        ext.record_transformation_outcome(
            H.OPERATOR, request["id"], "reported_partial")
        ext.record_transformation_outcome(
            H.OPERATOR, request["id"], "reported_transformed")
        summary = ext.transformation_summary(H.VIEWER)
        self.assertEqual(summary, {
            "transformation_requests": 1,
            "transformation_outcomes": 2,
            "requests_with_outcomes": 1,
            "outcomes_by_label": {
                "reported_transformed": 1,
                "reported_partial": 1,
                "reported_no_decision": 0,
                "reported_failed": 0,
            },
        })


class TestDiscipline(unittest.TestCase):
    def test_full_flow_leaves_core_records_byte_identical(self):
        ext, store, audit, org = make_ext()
        intent = H.make_intent(store, org)
        decision = H.make_decision(store, org, intent)
        before = copy.deepcopy({
            "organizations": store._organizations,
            "intents": store._intents,
            "decisions": store._decisions,
        })
        request = ext.register_transformation_request(
            H.OPERATOR, org["id"], "L", [intent["id"]], "eng-1")
        ext.record_transformation_outcome(
            H.OPERATOR, request["id"], "reported_transformed",
            core_decision_id=decision["id"])
        ext.get_transformation_request(H.ADMIN, request["id"])
        ext.transformation_summary(H.ADMIN)
        after = {
            "organizations": store._organizations,
            "intents": store._intents,
            "decisions": store._decisions,
        }
        self.assertEqual(before, after)

    def test_no_content_shaped_parameter_exists(self):
        source = inspect.getsource(ext_module)
        self.assertNotIn("**kwargs", source)
        forbidden = {"content", "statement", "body", "payload",
                     "telemetry", "decision_text", "intent_text"}
        for name, member in inspect.getmembers(
                ManufacturingExtensions, inspect.isfunction):
            params = set(inspect.signature(member).parameters)
            self.assertEqual(params & forbidden, set(),
                             "%s accepts %s" % (name, params & forbidden))

    def test_smuggled_content_kwarg_raises_type_error(self):
        ext, store, audit, org = make_ext()
        intent = H.make_intent(store, org)
        with self.assertRaises(TypeError):
            ext.register_transformation_request(
                H.OPERATOR, org["id"], "L", [intent["id"]], "eng-1",
                content="the intent text")
        request, _ = make_request(ext, store, org)
        with self.assertRaises(TypeError):
            ext.record_transformation_outcome(
                H.OPERATOR, request["id"], "reported_failed",
                statement="the decision text")

    def test_recursive_scans_over_the_whole_surface(self):
        ext, store, audit, org = make_ext()
        request, intent = make_request(ext, store, org)
        decision = H.make_decision(store, org, intent)
        ext.record_transformation_outcome(
            H.OPERATOR, request["id"], "reported_partial")
        ext.record_transformation_outcome(
            H.OPERATOR, request["id"], "reported_transformed",
            core_decision_id=decision["id"])
        surface = {
            "requests": ext.list_transformation_requests(H.ADMIN),
            "outcomes": ext.list_transformation_outcomes(H.ADMIN),
            "view": ext.get_transformation_request(H.ADMIN, request["id"]),
            "summary": ext.transformation_summary(H.ADMIN),
        }
        _scan(surface)


class EarliestOutcomeExtensions(ManufacturingExtensions):
    """Mutant subclass: the latest-outcome seam reading the
    earliest outcome instead of the latest. Shares the canonical
    record tables by construction (same instance state layout)."""

    @staticmethod
    def _latest_outcome_label(outcomes):
        return outcomes[0]["outcome_label"] if outcomes else None


class TestNegativeControlLatestOutcome(unittest.TestCase):
    def _populated(self, ext_cls):
        store, audit, org = H.make_store()
        ext = ext_cls(store)
        intent = H.make_intent(store, org)
        request = ext.register_transformation_request(
            H.OPERATOR, org["id"], "L", [intent["id"]], "eng-1")
        ext.record_transformation_outcome(
            H.OPERATOR, request["id"], "reported_partial")
        ext.record_transformation_outcome(
            H.OPERATOR, request["id"], "reported_transformed")
        return ext, request

    def test_canonical_view_uses_latest_outcome(self):
        ext, request = self._populated(ManufacturingExtensions)
        view = ext.get_transformation_request(H.ADMIN, request["id"])
        self.assertEqual(view["latest_outcome_label"],
                         "reported_transformed")

    def test_mutant_view_uses_earliest_outcome(self):
        ext, request = self._populated(EarliestOutcomeExtensions)
        view = ext.get_transformation_request(H.ADMIN, request["id"])
        self.assertEqual(view["latest_outcome_label"], "reported_partial")

    def test_treating_mutant_outcome_as_canonical_fails(self):
        ext, request = self._populated(EarliestOutcomeExtensions)
        view = ext.get_transformation_request(H.ADMIN, request["id"])
        with self.assertRaises(AssertionError):
            self.assertEqual(view["latest_outcome_label"],
                             "reported_transformed")

    def test_seam_directly(self):
        outcomes = [{"outcome_label": "reported_partial"},
                    {"outcome_label": "reported_transformed"}]
        self.assertEqual(
            ManufacturingExtensions._latest_outcome_label(outcomes),
            "reported_transformed")
        self.assertIsNone(
            ManufacturingExtensions._latest_outcome_label([]))


if __name__ == "__main__":
    unittest.main()
