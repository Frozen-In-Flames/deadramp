"""Final GAPS batch extensions for the Travel Management
untiered set (Untiered Set 28).

Clean-room, standard-library-only records extensions for the 1
open entry this set's GAPS.md section carries. See ``BATCH.md``
in the group directory for the per-entry disposition.

This set is **untiered**: the member fork's FedRAMP impact level
is Unknown in the source, tier stays null, no baseline is
asserted, and no CMMC equivalence is drawn. Nothing in this
module names a tier, a baseline, or an impact level; the records
and views it produces carry no such key (pinned by recursive
scan in ``tests/test_gaps_batch.py``).

The entry — the travel data aggregation & analytics engine — is
the fork's described function entire ("Aggregation of travel
data to support comprehensive reporting and analysis."). It has
two halves, and this surface keeps them apart on every record's
face:

- **Collection** — travel data arriving from source systems —
  is an act against external systems. It ships as a labeled
  reference implementation: aggregation source records naming a
  source system by an opaque caller-supplied reference (never a
  URL, host, or credential — no field shape can hold one), plus
  collection report records holding what a source reported,
  verbatim: an outcome label and a count of records, stated as
  reported. Nothing here connects, polls, or collects:
  ``reference_stub: True``, ``reference_transport: True``,
  ``collected_here: False`` on every collection-side record.
- **Aggregation & analysis over the records this substrate
  holds** is a deterministic derivation, and it is built:
  aggregation profile records hold a grouping as data
  (``definition_only: True`` — defining a profile aggregates
  nothing), and an aggregation view derives counts and integer-
  cent sums at read over the core's own recorded authorizations,
  expense reports, and expense items for the profile's
  organization, through the accumulation seam
  :meth:`TravelExtensions._accumulate` — the batch's fresh
  negative-control target. A view is never stored; its basis is
  stated on its face, and a full extension flow writes no core
  state (pinned by test: the core summary is deep-equal before
  and after).

Doctrines carried from the core, unchanged:

- **Money is integer cents, everywhere.** Every ``*_cents``
  figure a view reports is a sum of the core's recorded integer
  cents; the only money-shaped input on this surface (a reported
  record count) is an integer count, never money, and booleans
  and floats are rejected at the boundary. A rejected operation
  consumes no id and stores nothing.
- **No per-diem shape exists here.** Per-diem computation is a
  recorded absence in this category (it survives on this fork's
  own words, token-verified in the union spec): no method on
  this surface accepts a rate, a day count, or an allowance, and
  no record or view carries a per-diem key (pinned by recursive
  scan). Nothing here computes one.
- **No booking or travel act happens here.** Aggregation reads
  records; it books, reserves, and pays nothing
  (``booked_here: False`` on views), and relocation is not a
  trip: no record on this surface binds anything to a trip
  authorization except the core's own expense-report linkage,
  read, never written.
- **No scores.** Views and summaries are counts and money sums
  over recorded data, stated as such; no record shape has a
  field for a score, rating, or risk value (pinned by recursive
  key scan).
- RBAC goes through :mod:`travel.access` exactly as the core
  enforces it: each extension operation maps onto an existing
  core action — profile definitions onto ``enter``, source and
  collection records onto ``record``, reads and derived views
  onto ``read`` — checked *before* any state change or id
  allocation for User-like actors, with role denials recorded on
  the core audit log as ``ext_<action>:denied``. Organization
  membership (the second boundary) is enforced through the core
  store's own access-checked organization read. Plain-string
  actors carry identity but no role, mirroring the core
  convention.
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``. If
  the audit write raises, the mutation and its id roll back
  before the error propagates: no extension record exists whose
  audit entry does not.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

SOURCE_KINDS = (
    "travel_system",
    "expense_system",
    "carrier_feed",
    "manual_import",
    "other",
)
KNOWN_SOURCE_KINDS = frozenset(SOURCE_KINDS)

COLLECTION_OUTCOMES = (
    "reported_collected",
    "reported_partial",
    "reported_failed",
    "reported_no_data",
)
KNOWN_COLLECTION_OUTCOMES = frozenset(COLLECTION_OUTCOMES)

GROUPINGS = (
    "expense_category",
    "authorization_status",
    "report_status",
    "traveler",
)
KNOWN_GROUPINGS = frozenset(GROUPINGS)

# What each grouping sums, stated on every view's face as its
# amount basis. All figures are sums of the core's recorded
# integer cents, derived at read; none is stored.
AMOUNT_BASIS = {
    "expense_category": "recorded_expense_item_amounts",
    "authorization_status": "recorded_authorized_amounts",
    "report_status": "recorded_expense_report_totals",
    "traveler": "recorded_authorized_amounts",
}


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_count(value, what="records_reported"):
    """A reported record count: a non-negative integer.

    Booleans and floats are rejected at the boundary, exactly as
    the core rejects them for money.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer count" % (what,))
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


class TravelExtensions:
    """GAPS-batch extension surface over a core TravelStore."""

    def __init__(self, store):
        self.store = store
        self._records = {}  # (kind, id) -> dict
        self._order = []  # (kind, id) in creation order
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self.store, "audit", None)
        if audit is not None:
            audit.record(actor_name(actor), action, target, details=details)

    def _guard(self, actor, core_action, audit_action, target=None):
        """Enforce a permission, auditing a denial.

        Mirrors the core convention: an actor must be present;
        User-like actors are checked against the core permission
        matrix before anything changes; plain strings carry
        identity only.
        """
        try:
            if actor is None:
                raise PermissionDenied(
                    "permission denied: no user supplied for %r" % (core_action,)
                )
            if hasattr(actor, "role"):
                require(actor, core_action)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", target)
            raise

    def _organization(self, actor, org_id):
        """Core access-checked organization read.

        Raises NotFoundError for an unknown organization and
        PermissionDenied for a non-member, exactly as the core
        does.
        """
        return self.store.get_organization(actor, org_id)

    def _create(self, kind, prefix, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            try:
                self._audit(actor, audit_action, record_id,
                            details={"kind": kind})
            except Exception:
                # Fail closed: an operation whose audit write fails
                # does not proceed — the insertion and the id roll
                # back before the error propagates.
                del self._records[(kind, record_id)]
                self._order.pop()
                self._counters[prefix] -= 1
                raise
            return copy.deepcopy(record)

    def _get(self, kind, record_id, org_id):
        record = self._records.get((kind, record_id))
        if record is None or record["org_id"] != org_id:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _list(self, kind, org_id, **filters):
        result = []
        for key in self._order:
            if key[0] != kind:
                continue
            record = self._records[key]
            if record["org_id"] != org_id:
                continue
            if all(record.get(f) == v for f, v in filters.items()):
                result.append(copy.deepcopy(record))
        return result

    @staticmethod
    def _latest_label(records, key):
        """The latest recorded label, or None — derived, never stored."""
        if not records:
            return None
        return records[-1][key]

    # -- aggregation sources (idx 966, collection half: reference) ----

    def _check_source_ref_unique(self, org_id, source_ref):
        """Refuse a second source with the same ref in one org.

        The surface's uniqueness seam: source references name
        external systems, and two records naming the same system
        in one organization would double-count its reports.
        """
        for record in self._list("aggregation_source", org_id):
            if record["source_ref"] == source_ref:
                raise ValidationError(
                    "duplicate aggregation source ref in organization: %r"
                    % (source_ref,))

    def register_aggregation_source(self, actor, org_id, source_ref,
                                    label, kind, integration_id=None):
        """Register an aggregation source as a labeled reference.

        The source is named by an opaque caller-supplied
        ``source_ref`` only — no field on the record can hold a
        URL, host, credential, or any connection detail. An
        optional ``integration_id`` binds the source to one of
        the organization's core integration definitions (which
        the core registry holds as data and never executes).
        Registering a source collects nothing.
        """
        self._guard(actor, "record", "ext_source_create")
        self._organization(actor, org_id)
        _validate_non_empty(source_ref, "source_ref")
        _validate_non_empty(label, "label")
        if kind not in KNOWN_SOURCE_KINDS:
            raise ValidationError(
                "source kind must be one of %s"
                % (", ".join(SOURCE_KINDS),))
        if integration_id is not None:
            known = {i["id"] for i in
                     self.store.list_integrations(actor, org_id)}
            if integration_id not in known:
                raise NotFoundError(
                    "integration not found in organization: %r"
                    % (integration_id,))
        self._check_source_ref_unique(org_id, source_ref)
        fields = {
            "org_id": org_id,
            "source_ref": source_ref,
            "label": label,
            "kind": kind,
            "integration_id": integration_id,
            "reference_stub": True,
            "reference_transport": True,
            "collected_here": False,
            "connected_here": False,
            "state": "recorded_reference_only",
        }
        return self._create(
            "aggregation_source", "ags", fields, actor, "ext_source_create")

    def get_aggregation_source(self, actor, source_id, org_id):
        self._guard(actor, "read", "ext_source_read", target=source_id)
        self._organization(actor, org_id)
        with self._lock:
            return copy.deepcopy(
                self._get("aggregation_source", source_id, org_id))

    def list_aggregation_sources(self, actor, org_id):
        self._guard(actor, "read", "ext_source_read")
        self._organization(actor, org_id)
        with self._lock:
            return self._list("aggregation_source", org_id)

    # -- collection reports (idx 966, collection half: reference) -----

    def record_collection_report(self, actor, org_id, source_id,
                                 outcome_label, records_reported):
        """Record what a source system reported about a collection.

        The outcome label and the record count are stored
        verbatim as reported (``outcome_basis: source_reported``);
        this build collected nothing, so the count is a report,
        never a measurement taken here.
        """
        self._guard(actor, "record", "ext_collection_create")
        self._organization(actor, org_id)
        with self._lock:
            self._get("aggregation_source", source_id, org_id)
        if outcome_label not in KNOWN_COLLECTION_OUTCOMES:
            raise ValidationError(
                "outcome_label must be one of %s"
                % (", ".join(COLLECTION_OUTCOMES),))
        _validate_count(records_reported)
        fields = {
            "org_id": org_id,
            "source_id": source_id,
            "outcome_label": outcome_label,
            "records_reported": records_reported,
            "outcome_basis": "source_reported",
            "reference_stub": True,
            "reference_transport": True,
            "collected_here": False,
        }
        return self._create(
            "collection_report", "col", fields, actor,
            "ext_collection_create")

    def list_collection_reports(self, actor, org_id, source_id=None):
        self._guard(actor, "read", "ext_collection_read")
        self._organization(actor, org_id)
        filters = {}
        if source_id is not None:
            filters["source_id"] = source_id
        with self._lock:
            return self._list("collection_report", org_id, **filters)

    # -- aggregation profiles & views (idx 966, aggregation half) -----

    def create_aggregation_profile(self, actor, org_id, label, group_by):
        """Define an aggregation profile: a grouping, as data.

        A profile is a definition only (``definition_only:
        True``): creating one aggregates nothing. The figures
        exist only in the derived view.
        """
        self._guard(actor, "enter", "ext_profile_create")
        self._organization(actor, org_id)
        _validate_non_empty(label, "label")
        if group_by not in KNOWN_GROUPINGS:
            raise ValidationError(
                "group_by must be one of %s" % (", ".join(GROUPINGS),))
        fields = {
            "org_id": org_id,
            "label": label,
            "group_by": group_by,
            "definition_only": True,
            "aggregated_here": False,
        }
        return self._create(
            "aggregation_profile", "agp", fields, actor,
            "ext_profile_create")

    def get_aggregation_profile(self, actor, profile_id, org_id):
        self._guard(actor, "read", "ext_profile_read", target=profile_id)
        self._organization(actor, org_id)
        with self._lock:
            return copy.deepcopy(
                self._get("aggregation_profile", profile_id, org_id))

    def list_aggregation_profiles(self, actor, org_id):
        self._guard(actor, "read", "ext_profile_read")
        self._organization(actor, org_id)
        with self._lock:
            return self._list("aggregation_profile", org_id)

    @staticmethod
    def _accumulate(totals, label, amount_cents):
        """The aggregation seam: fold one recorded figure in.

        Every figure in every aggregation view routes through
        here: the label's record count increments by one and its
        amount total grows by the recorded integer cents. This
        is the batch's negative-control target — a mutant that
        folds nothing in leaves every group at zero.
        """
        entry = totals.setdefault(label, [0, 0])
        entry[0] += 1
        entry[1] += amount_cents
        return totals

    def _group_pairs(self, actor, org_id, group_by):
        """(label, amount_cents) pairs from the core's records.

        Read through the core store's public, access-checked API
        only; nothing here writes core state. The pairs are the
        core's recorded figures — authorized amounts, expense
        item amounts, derived report totals — never recomputed
        from anything outside the substrate's own records.
        """
        pairs = []
        authorizations = self.store.list_authorizations(actor, org_id)
        if group_by == "authorization_status":
            for auth in authorizations:
                pairs.append((auth["status"], auth["authorized_cents"]))
        elif group_by == "traveler":
            for auth in authorizations:
                pairs.append((auth["traveler_id"],
                              auth["authorized_cents"]))
        elif group_by == "report_status":
            for auth in authorizations:
                for report in self.store.list_expense_reports(
                        actor, auth["id"]):
                    pairs.append((report["status"],
                                  report["total_cents"]))
        elif group_by == "expense_category":
            for auth in authorizations:
                for report in self.store.list_expense_reports(
                        actor, auth["id"]):
                    for item in self.store.list_expense_items(
                            actor, report["id"]):
                        pairs.append((item["category"],
                                      item["amount_cents"]))
        return pairs

    def aggregation_view(self, actor, profile_id, org_id):
        """Derive the profile's aggregation at read. Never stored.

        Groups are the profile's grouping over the core's own
        recorded figures for the organization; totals are the
        sums of the groups, stated with their basis. No external
        system is contacted: the collection half of the entry
        lives on the reference surface above, and its reported
        counts are never folded into these figures (pinned by
        test).
        """
        self._guard(actor, "read", "ext_profile_read", target=profile_id)
        self._organization(actor, org_id)
        with self._lock:
            profile = copy.deepcopy(
                self._get("aggregation_profile", profile_id, org_id))
        totals = {}
        for label, amount in self._group_pairs(
                actor, org_id, profile["group_by"]):
            self._accumulate(totals, label, amount)
        groups = [
            {"label": label,
             "record_count": totals[label][0],
             "amount_cents": totals[label][1]}
            for label in sorted(totals)
        ]
        return {
            "profile_id": profile["id"],
            "org_id": org_id,
            "group_by": profile["group_by"],
            "amount_basis": AMOUNT_BASIS[profile["group_by"]],
            "figures_basis": "core_records_only",
            "groups": groups,
            "total_records": sum(g["record_count"] for g in groups),
            "total_amount_cents": sum(g["amount_cents"] for g in groups),
            "derived_at_read": True,
            "stored": False,
            "booked_here": False,
            "collected_here": False,
        }

    def aggregation_summary(self, actor, org_id):
        """Counts over this surface's own records, derived at read.

        The collection side is summarized as what it is: counts
        of source and report records, the sum of the counts those
        reports carried (stated as a sum of reported counts), and
        the latest reported outcome label. No score, rate, or
        grade is computed anywhere.
        """
        self._guard(actor, "read", "ext_summary_read")
        self._organization(actor, org_id)
        with self._lock:
            sources = self._list("aggregation_source", org_id)
            reports = self._list("collection_report", org_id)
            profiles = self._list("aggregation_profile", org_id)
        by_outcome = {label: 0 for label in COLLECTION_OUTCOMES}
        for report in reports:
            by_outcome[report["outcome_label"]] += 1
        return {
            "org_id": org_id,
            "sources": len(sources),
            "collection_reports": len(reports),
            "collection_reports_by_outcome": by_outcome,
            "records_reported_total": sum(
                r["records_reported"] for r in reports),
            "records_reported_basis": "sum_of_reported_counts",
            "profiles": len(profiles),
            "latest_collection_outcome": self._latest_label(
                reports, "outcome_label"),
            "collected_here": False,
        }
