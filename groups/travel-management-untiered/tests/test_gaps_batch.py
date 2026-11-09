"""Final GAPS batch tests — Travel Management untiered set
(Untiered Set 28).

Pins the extension surface built for the section's 1 open entry
(idx 966, the travel data aggregation & analytics engine). The
section's other entry (idx 967, "Platform layer") was already
closed ``re-scoped`` at the batch foundation under
PLATFORM-LAYER.md and is not part of this unit.

The surface keeps the entry's two halves apart:

- Collection (source systems reporting travel data in) is a
  labeled reference implementation: source records named by
  opaque references only, collection reports holding outcome
  labels and record counts verbatim as reported, every record
  carrying ``reference_stub: True`` / ``reference_transport:
  True`` / ``collected_here: False``.
- Aggregation over the core's own recorded figures is built:
  profile definitions as data, views deriving counts and
  integer-cent sums at read through the ``_accumulate`` seam —
  never stored, basis stated on the view's face, and collection
  reports never folded into the figures.

``TestAggregationAccumulationNegativeControl``: the
``_accumulate`` seam is the derivation's only folding point —
an amount-blind mutant sharing the same core store produces
views whose counts stand but whose amounts are all zero,
proving the seam is what carries the recorded figures into the
aggregation.

Tier discipline: this set is untiered. A recursive scan pins
that no record, view, or summary on the new surface carries a
tier, baseline, impact-level, equivalence, score, or per-diem
key, and no float value appears anywhere.
"""

import inspect
import unittest

import travel_helpers as H
from travel.audit import AuditLog
from travel.errors import NotFoundError, PermissionDenied, ValidationError
from travel.extensions import TravelExtensions
from travel.store import TravelStore


def make_extensions():
    """Extensions over a core store with one organization.

    Returns (ext, store, audit, org). ADMIN created the org;
    MEMBER, VIEWER and DECIDER are members; OUTSIDER is not.
    """
    audit = AuditLog()
    store = TravelStore(audit=audit)
    ext = TravelExtensions(store)
    org = store.create_organization(H.ADMIN, H.ORG_REF, "Agency One")
    store.add_member(H.ADMIN, org["id"], H.MEMBER.name)
    store.add_member(H.ADMIN, org["id"], H.VIEWER.name)
    store.add_member(H.ADMIN, org["id"], H.DECIDER.name)
    return ext, store, audit, org


def make_travel_data(store, org):
    """Two travelers, one approved trip + report, one draft trip.

    auth-1: traveler one, approved, authorized 500_000, with an
    approved expense report whose items are lodging 120_000 and
    meals 30_000 (total 150_000). auth-2: traveler two, draft,
    authorized 200_000, no reports.
    """
    traveler1 = H.make_traveler(store, org)
    auth1 = H.make_approved_authorization(store, org, traveler1)
    H.make_approved_report(store, auth1)
    traveler2 = H.make_traveler(store, org, traveler_ref="TRV-200",
                                label="Traveler Two")
    auth2 = H.make_authorization(store, org, traveler2,
                                 authorized_cents=200_000)
    return traveler1, auth1, traveler2, auth2


def walk(value):
    """Yield every (key, value) pair in a nested structure."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from walk(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from walk(item)


FORBIDDEN_KEYS = {
    "tier", "cmmc", "cmmc_tier", "baseline", "fedramp_impact_level",
    "impact_level", "equivalence", "score", "rating", "risk",
    "per_diem", "perdiem", "daily_rate", "day_count", "allowance",
    "url", "host", "hostname", "password", "credential",
    "credentials", "api_key", "token",
}


class TestAggregationSources(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.audit, self.org = make_extensions()

    def test_source_record_shape_and_labels(self):
        source = self.ext.register_aggregation_source(
            H.MEMBER, self.org["id"], "SRC-TRAVEL-1", "Travel system",
            "travel_system")
        self.assertEqual(
            set(source),
            {"id", "org_id", "source_ref", "label", "kind",
             "integration_id", "reference_stub", "reference_transport",
             "collected_here", "connected_here", "state",
             "created_by", "created_utc"})
        self.assertEqual(source["id"], "ags-1")
        self.assertTrue(source["reference_stub"])
        self.assertTrue(source["reference_transport"])
        self.assertFalse(source["collected_here"])
        self.assertFalse(source["connected_here"])
        self.assertEqual(source["state"], "recorded_reference_only")
        self.assertIsNone(source["integration_id"])

    def test_source_kind_validated(self):
        with self.assertRaises(ValidationError):
            self.ext.register_aggregation_source(
                H.MEMBER, self.org["id"], "SRC-X", "X", "hyperlink")

    def test_duplicate_source_ref_refused_no_id_consumed(self):
        self.ext.register_aggregation_source(
            H.MEMBER, self.org["id"], "SRC-1", "One", "other")
        with self.assertRaises(ValidationError):
            self.ext.register_aggregation_source(
                H.MEMBER, self.org["id"], "SRC-1", "Dupe", "other")
        second = self.ext.register_aggregation_source(
            H.MEMBER, self.org["id"], "SRC-2", "Two", "other")
        self.assertEqual(second["id"], "ags-2")

    def test_source_binds_core_integration_definition(self):
        integration = self.store.register_integration(
            H.MEMBER, self.org["id"], "Feed", "file", "Nightly file")
        source = self.ext.register_aggregation_source(
            H.MEMBER, self.org["id"], "SRC-F", "Feed source",
            "manual_import", integration_id=integration["id"])
        self.assertEqual(source["integration_id"], integration["id"])
        with self.assertRaises(NotFoundError):
            self.ext.register_aggregation_source(
                H.MEMBER, self.org["id"], "SRC-G", "Ghost",
                "manual_import", integration_id="int-999")

    def test_viewer_create_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_aggregation_source(
                H.VIEWER, self.org["id"], "SRC-V", "V", "other")
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_source_create:denied", actions)

    def test_outsider_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_aggregation_source(
                H.OUTSIDER, self.org["id"], "SRC-O", "O", "other")


class TestCollectionReports(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.audit, self.org = make_extensions()
        self.source = self.ext.register_aggregation_source(
            H.MEMBER, self.org["id"], "SRC-1", "One", "travel_system")

    def test_report_holds_outcome_verbatim_as_reported(self):
        report = self.ext.record_collection_report(
            H.MEMBER, self.org["id"], self.source["id"],
            "reported_partial", 42)
        self.assertEqual(report["outcome_label"], "reported_partial")
        self.assertEqual(report["records_reported"], 42)
        self.assertEqual(report["outcome_basis"], "source_reported")
        self.assertTrue(report["reference_stub"])
        self.assertFalse(report["collected_here"])

    def test_report_count_rejects_bool_float_negative(self):
        for bad in (True, 1.5, -1):
            with self.assertRaises(ValidationError):
                self.ext.record_collection_report(
                    H.MEMBER, self.org["id"], self.source["id"],
                    "reported_collected", bad)
        report = self.ext.record_collection_report(
            H.MEMBER, self.org["id"], self.source["id"],
            "reported_collected", 0)
        self.assertEqual(report["id"], "col-1")

    def test_report_outcome_validated(self):
        with self.assertRaises(ValidationError):
            self.ext.record_collection_report(
                H.MEMBER, self.org["id"], self.source["id"],
                "collected_fine", 1)

    def test_report_requires_source_in_same_org(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_collection_report(
                H.MEMBER, self.org["id"], "ags-999",
                "reported_collected", 1)


class TestAggregationProfilesAndViews(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.audit, self.org = make_extensions()
        (self.traveler1, self.auth1,
         self.traveler2, self.auth2) = make_travel_data(
            self.store, self.org)

    def profile(self, group_by):
        return self.ext.create_aggregation_profile(
            H.MEMBER, self.org["id"], "P", group_by)

    def test_profile_is_definition_only(self):
        profile = self.profile("expense_category")
        self.assertTrue(profile["definition_only"])
        self.assertFalse(profile["aggregated_here"])
        self.assertEqual(
            set(profile),
            {"id", "org_id", "label", "group_by", "definition_only",
             "aggregated_here", "created_by", "created_utc"})

    def test_group_by_validated(self):
        with self.assertRaises(ValidationError):
            self.profile("destination")

    def test_category_view_sums_recorded_items(self):
        view = self.ext.aggregation_view(
            H.MEMBER, self.profile("expense_category")["id"],
            self.org["id"])
        groups = {g["label"]: g for g in view["groups"]}
        self.assertEqual(groups["lodging"],
                         {"label": "lodging", "record_count": 1,
                          "amount_cents": 120_000})
        self.assertEqual(groups["meals"]["amount_cents"], 30_000)
        self.assertEqual(view["total_records"], 2)
        self.assertEqual(view["total_amount_cents"], 150_000)
        self.assertEqual(view["amount_basis"],
                         "recorded_expense_item_amounts")
        self.assertEqual(view["figures_basis"], "core_records_only")
        self.assertTrue(view["derived_at_read"])
        self.assertFalse(view["stored"])
        self.assertFalse(view["booked_here"])

    def test_authorization_status_view(self):
        view = self.ext.aggregation_view(
            H.MEMBER, self.profile("authorization_status")["id"],
            self.org["id"])
        groups = {g["label"]: g for g in view["groups"]}
        self.assertEqual(groups["approved"]["amount_cents"], 500_000)
        self.assertEqual(groups["draft"]["amount_cents"], 200_000)
        self.assertEqual(view["total_amount_cents"], 700_000)

    def test_report_status_view(self):
        view = self.ext.aggregation_view(
            H.MEMBER, self.profile("report_status")["id"],
            self.org["id"])
        groups = {g["label"]: g for g in view["groups"]}
        self.assertEqual(groups["approved"],
                         {"label": "approved", "record_count": 1,
                          "amount_cents": 150_000})

    def test_traveler_view(self):
        view = self.ext.aggregation_view(
            H.MEMBER, self.profile("traveler")["id"], self.org["id"])
        groups = {g["label"]: g for g in view["groups"]}
        self.assertEqual(
            groups[self.traveler1["id"]]["amount_cents"], 500_000)
        self.assertEqual(
            groups[self.traveler2["id"]]["amount_cents"], 200_000)

    def test_collection_reports_never_fold_into_figures(self):
        source = self.ext.register_aggregation_source(
            H.MEMBER, self.org["id"], "SRC-1", "One", "travel_system")
        self.ext.record_collection_report(
            H.MEMBER, self.org["id"], source["id"],
            "reported_collected", 999)
        view = self.ext.aggregation_view(
            H.MEMBER, self.profile("expense_category")["id"],
            self.org["id"])
        self.assertEqual(view["total_records"], 2)
        self.assertEqual(view["total_amount_cents"], 150_000)

    def test_view_requires_profile_in_same_org(self):
        profile = self.profile("traveler")
        org2 = self.store.create_organization(
            H.ADMIN, "ORG-200", "Agency Two")
        with self.assertRaises(NotFoundError):
            self.ext.aggregation_view(
                H.ADMIN, profile["id"], org2["id"])


class TestAggregationSummary(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.audit, self.org = make_extensions()

    def test_summary_counts_and_reported_sums(self):
        source = self.ext.register_aggregation_source(
            H.MEMBER, self.org["id"], "SRC-1", "One", "travel_system")
        self.ext.record_collection_report(
            H.MEMBER, self.org["id"], source["id"],
            "reported_collected", 10)
        self.ext.record_collection_report(
            H.MEMBER, self.org["id"], source["id"],
            "reported_partial", 5)
        self.ext.create_aggregation_profile(
            H.MEMBER, self.org["id"], "P", "traveler")
        summary = self.ext.aggregation_summary(H.MEMBER, self.org["id"])
        self.assertEqual(summary["sources"], 1)
        self.assertEqual(summary["collection_reports"], 2)
        self.assertEqual(
            summary["collection_reports_by_outcome"]
            ["reported_partial"], 1)
        self.assertEqual(summary["records_reported_total"], 15)
        self.assertEqual(summary["records_reported_basis"],
                         "sum_of_reported_counts")
        self.assertEqual(summary["latest_collection_outcome"],
                         "reported_partial")
        self.assertEqual(summary["profiles"], 1)
        self.assertFalse(summary["collected_here"])

    def test_summary_empty(self):
        summary = self.ext.aggregation_summary(H.MEMBER, self.org["id"])
        self.assertEqual(summary["sources"], 0)
        self.assertIsNone(summary["latest_collection_outcome"])


class AmountBlindExtensions(TravelExtensions):
    """Mutant: the accumulation seam folds counts, never amounts."""

    @staticmethod
    def _accumulate(totals, label, amount_cents):
        entry = totals.setdefault(label, [0, 0])
        entry[0] += 1
        return totals


class TestAggregationAccumulationNegativeControl(unittest.TestCase):
    """Three-leg control on the ``_accumulate`` seam.

    Canonical: the category view's total is the recorded items'
    sum. Mutant (amount-blind, same core store): counts stand,
    every amount is zero. Treating the mutant's outcome as the
    canonical expectation fails.
    """

    def setUp(self):
        self.ext, self.store, self.audit, self.org = make_extensions()
        make_travel_data(self.store, self.org)
        self.profile = self.ext.create_aggregation_profile(
            H.MEMBER, self.org["id"], "P", "expense_category")

    def test_canonical_view_carries_recorded_amounts(self):
        view = self.ext.aggregation_view(
            H.MEMBER, self.profile["id"], self.org["id"])
        self.assertEqual(view["total_records"], 2)
        self.assertEqual(view["total_amount_cents"], 150_000)

    def blind_mutant(self):
        """The mutant subclass, sharing the canonical record tables."""
        mutant = AmountBlindExtensions(self.store)
        mutant._records = self.ext._records
        mutant._order = self.ext._order
        mutant._counters = self.ext._counters
        return mutant

    def test_mutant_amounts_vanish_counts_stand(self):
        mutant = self.blind_mutant()
        view = mutant.aggregation_view(
            H.MEMBER, self.profile["id"], self.org["id"])
        self.assertEqual(view["total_records"], 2)
        self.assertEqual(view["total_amount_cents"], 0)

    def test_mutant_outcome_as_expectation_fails(self):
        mutant = self.blind_mutant()
        view = mutant.aggregation_view(
            H.MEMBER, self.profile["id"], self.org["id"])
        with self.assertRaises(AssertionError):
            self.assertEqual(view["total_amount_cents"], 150_000)


class BoomAudit:
    """An audit sink whose write always fails."""

    def record(self, actor, action, target, details=None):
        raise RuntimeError("audit unavailable")


class TestAuditFailureAndCoreIsolation(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.audit, self.org = make_extensions()

    def test_failed_audit_rolls_back_create_and_id(self):
        self.store.audit = BoomAudit()
        with self.assertRaises(RuntimeError):
            self.ext.register_aggregation_source(
                H.MEMBER, self.org["id"], "SRC-1", "One", "other")
        self.store.audit = self.audit
        self.assertEqual(
            self.ext.list_aggregation_sources(H.MEMBER, self.org["id"]),
            [])
        source = self.ext.register_aggregation_source(
            H.MEMBER, self.org["id"], "SRC-1", "One", "other")
        self.assertEqual(source["id"], "ags-1")

    def test_full_flow_leaves_core_summary_byte_identical(self):
        make_travel_data(self.store, self.org)
        before = self.store.summary(H.MEMBER, self.org["id"])
        source = self.ext.register_aggregation_source(
            H.MEMBER, self.org["id"], "SRC-1", "One", "travel_system")
        self.ext.record_collection_report(
            H.MEMBER, self.org["id"], source["id"],
            "reported_collected", 7)
        profile = self.ext.create_aggregation_profile(
            H.MEMBER, self.org["id"], "P", "expense_category")
        self.ext.aggregation_view(H.MEMBER, profile["id"],
                                  self.org["id"])
        self.ext.aggregation_summary(H.MEMBER, self.org["id"])
        after = self.store.summary(H.MEMBER, self.org["id"])
        self.assertEqual(before, after)

    def test_audit_trail_records_extension_actions(self):
        self.ext.register_aggregation_source(
            H.MEMBER, self.org["id"], "SRC-1", "One", "other")
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_source_create", actions)


class TestTierNullAndSurfaceDiscipline(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.audit, self.org = make_extensions()
        make_travel_data(self.store, self.org)

    def test_no_tier_score_perdiem_or_float_anywhere(self):
        source = self.ext.register_aggregation_source(
            H.MEMBER, self.org["id"], "SRC-1", "One", "travel_system")
        report = self.ext.record_collection_report(
            H.MEMBER, self.org["id"], source["id"],
            "reported_collected", 3)
        profile = self.ext.create_aggregation_profile(
            H.MEMBER, self.org["id"], "P", "expense_category")
        view = self.ext.aggregation_view(
            H.MEMBER, profile["id"], self.org["id"])
        summary = self.ext.aggregation_summary(
            H.MEMBER, self.org["id"])
        for surface in (source, report, profile, view, summary):
            for key, value in walk(surface):
                self.assertNotIn(key, FORBIDDEN_KEYS)
                self.assertNotIsInstance(value, float)

    def test_no_public_method_accepts_connection_or_perdiem_input(self):
        forbidden_params = {
            "url", "host", "hostname", "password", "credential",
            "api_key", "token", "per_diem", "daily_rate",
            "day_count", "rate", "content",
        }
        for name in dir(TravelExtensions):
            if name.startswith("_"):
                continue
            member = getattr(TravelExtensions, name)
            if not callable(member):
                continue
            params = inspect.signature(member).parameters
            self.assertNotIn(
                inspect.Parameter.VAR_KEYWORD,
                [p.kind for p in params.values()],
                "public method %s must not accept **kwargs" % name)
            self.assertFalse(
                forbidden_params & set(params),
                "public method %s accepts a forbidden parameter"
                % name)


if __name__ == "__main__":
    unittest.main()
