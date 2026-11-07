"""Final GAPS batch extensions for the Research untiered set.

Clean-room, standard-library-only extensions for the 11 open
entries of Untiered Set 9 (see ``BATCH.md`` in the group directory
for the per-entry disposition). This module is a wrapper around
:class:`ResearchStore`; every core module is untouched and
byte-identical to the shipped set build.

**Tier discipline carries into the extension:** this set is
untiered -- every member's FedRAMP impact level is "Unknown" in
the source dataset -- so nothing here asserts a baseline, a tier,
or a CMMC equivalence either. No record or view in this module
carries a tier-, baseline-, or equivalence-shaped key, and the
spec sheets' ``cmmc_tier: null`` is untouched.

**The founding privacy discipline binds absolutely, here as in
the core:** records carry metadata and opaque caller-supplied
references only. Research subjects, trial participants, patients,
and investigated persons are opaque references -- no entity shape
in this module has a name, identifier, clinical-value,
consent-signature, or background-content field; those fields
**do not exist**. Capture forms hold field *references* as data;
submissions hold counts and recorded status labels; consent
records hold a recorded state label per opaque participant
reference; linkage is recorded as reported pairs between opaque
references and no match is ever computed here. Methods accept
only their named parameters, so a caller cannot smuggle a
forbidden field into a record (pinned by tests: an unexpected
keyword raises ``TypeError``).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form -- records plus deterministic derivations over
the set's OWN records (core records and extension records):

- Intelligence, supplier, and investigation content is recorded
  with its source label, exactly as reported; nothing is gathered,
  searched, discovered, or verified here.
- Contract-award "analysis" and clinical "reporting" are
  deterministic sums and counts over held records, method-labeled
  ``deterministic_sums`` / ``deterministic_counts`` -- never a
  learned model, never a score, never a ranking.
- Relationship-graph "analytics" are deterministic degree and
  label counts over recorded edges; no inference is drawn from a
  graph.
- Identity resolution follows the Data Management units' PPRL
  precedent: reported linkage pairs between opaque references,
  ``match_computed_here`` False on every record.
- Consent is a recorded state, not a legal act: no signature is
  captured or possible, and no consent is effected here.
- Stub-engine entries ship as labeled reference implementations:
  every record carries ``reference_stub: True`` and state
  ``recorded_reference_only``; nothing executes, alerts, monitors,
  or discovers.

Doctrines carried from the core: derived-never-stored for every
computed value (summaries, degrees, current consent state);
append-only audit on the core store's log with ``ext_``-prefixed
actions for every successful mutation, and denied write attempts
recorded with a ``:denied`` suffix; RBAC via
:mod:`research.access` with the core's existing actions, enforced
before any state change or id allocation, so a failed operation
consumes no id and changes nothing; the commons membership
boundary is enforced through the core store's own commons access
check on every operation.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

INTELLIGENCE_KINDS = ("directory_entry", "legislation", "hearing", "policy_item")
AWARD_KINDS = ("prime", "subaward")
ENTITY_KINDS = ("organization", "person", "program", "place", "other")
SUBMISSION_STATES = (
    "reported_submitted",
    "reported_partial",
    "reported_locked",
)
CONSENT_STATES = (
    "reported_consented",
    "reported_declined",
    "reported_withdrawn",
    "reported_pending",
)
OUTCOME_KINDS = ("questionnaire", "diary", "assessment")
LINKAGE_METHODS = (
    "reported_token_match",
    "reported_key_match",
    "reported_manual_review",
)

_REFERENCE_STATE = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _count(value, what):
    """A non-negative integer count; booleans and floats rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be a non-negative integer" % (what,))
    if value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


def _cents(value, what):
    """An integer number of cents; booleans and floats rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents" % (what,))
    if value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


def _string_list(value, what):
    if not isinstance(value, (list, tuple)):
        raise ValidationError("%s must be a list of strings" % (what,))
    items = list(value)
    if not items:
        raise ValidationError("%s must be a non-empty list" % (what,))
    for item in items:
        _non_empty(item, what)
    return items


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class ResearchExtensions:
    """Extension surface wrapping one :class:`ResearchStore`."""

    def __init__(self, store):
        self.store = store
        self._intelligence_items = {}
        self._awards = {}
        self._entities = {}
        self._relationships = {}
        self._saved_searches = {}
        self._tracking_records = {}
        self._capture_forms = {}
        self._submissions = {}
        self._consent_instruments = {}
        self._consent_states = {}
        self._outcome_instruments = {}
        self._outcome_responses = {}
        self._linkage_pairs = {}
        self._investigation_cases = {}
        self._investigation_findings = {}
        self._monitoring_references = {}
        self._discovery_references = {}
        self._supplier_profiles = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    def _guard(self, actor, rbac_action, audit_action):
        """Enforce a write permission before any state change.

        Mirrors the core convention (a User-like actor is checked
        via :func:`research.access.require`; a plain string carries
        identity but no role). A denied attempt is recorded on the
        audit log with a ``:denied`` suffix before the error
        propagates; a missing actor is denied outright.
        """
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (rbac_action,))
        if hasattr(actor, "role"):
            try:
                require(actor, rbac_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": rbac_action})
                raise

    @staticmethod
    def _maybe_require(actor, rbac_action):
        if actor is not None and hasattr(actor, "role"):
            require(actor, rbac_action)

    def _commons(self, actor, commons_id):
        """Resolve a commons through the core store, which enforces
        the read permission and the membership boundary (the
        platform admin reaches every commons)."""
        return self.store.get_commons(actor, commons_id)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _check_commons_of(self, actor, record):
        self._commons(actor, record["commons_id"])

    def _create(self, table, prefix, fields, actor, audit_action):
        record = {"id": self._next_id(prefix)}
        record.update(fields)
        record["created_by"] = actor_name(actor)
        record["created_utc"] = _utc_now()
        table[record["id"]] = record
        self._audit(actor, audit_action, record["id"])
        return copy.deepcopy(record)

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    def _in_commons(self, table, commons_id):
        return [r for r in table.values() if r["commons_id"] == commons_id]

    # -- Market & policy intelligence (idx 828, built) ------------------
    # Records form: an intelligence item is a registry record --
    # topic reference, source label recorded verbatim, and an
    # opaque reference to content held elsewhere. This substrate
    # gathers nothing: ``gathered_here`` is False on every record.

    def record_intelligence_item(self, actor, commons_id, kind, topic_ref,
                                 source_label, detail_ref):
        """Record one intelligence item. Action: record."""
        self._guard(actor, "record", "ext_intelligence_record")
        self._commons(actor, commons_id)
        if kind not in INTELLIGENCE_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(INTELLIGENCE_KINDS),))
        _non_empty(topic_ref, "topic_ref")
        _non_empty(source_label, "source_label")
        _non_empty(detail_ref, "detail_ref")
        with self._lock:
            return self._create(
                self._intelligence_items, "int-",
                {"commons_id": commons_id, "kind": kind,
                 "topic_ref": topic_ref, "source_label": source_label,
                 "detail_ref": detail_ref, "gathered_here": False},
                actor, "ext_intelligence_record")

    def get_intelligence_item(self, actor, item_id):
        """Return one intelligence item. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._intelligence_items, item_id,
                           "intelligence item")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_intelligence_items(self, actor, commons_id, kind=None):
        """List intelligence items in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        items = self._in_commons(self._intelligence_items, commons_id)
        if kind is not None:
            items = [i for i in items if i["kind"] == kind]
        return copy.deepcopy(self._sorted(items))

    def intelligence_summary(self, actor, commons_id):
        """Counts of intelligence items by kind, derived at read.

        Action: read. Method ``deterministic_counts`` -- counts
        only; nothing is gathered or ranked."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        items = self._in_commons(self._intelligence_items, commons_id)
        by_kind = {}
        for item in items:
            by_kind[item["kind"]] = by_kind.get(item["kind"], 0) + 1
        return {"commons_id": commons_id, "total": len(items),
                "by_kind": by_kind, "method": "deterministic_counts",
                "gathered_here": False}

    # -- Contract award & subaward analysis (idx 829, built) ------------
    # Records form: award records hold amounts as integer cents
    # (data, exactly as recorded); "analysis" is a deterministic
    # sums/counts derivation over the held records at read. No
    # funds move: ``funds_moved_here`` is False on every record.

    def record_award(self, actor, commons_id, award_ref, awardee_ref, kind,
                     amount_cents, parent_award_id=None):
        """Record one contract award or subaward. Action: record."""
        self._guard(actor, "record", "ext_award_record")
        self._commons(actor, commons_id)
        _non_empty(award_ref, "award_ref")
        _non_empty(awardee_ref, "awardee_ref")
        if kind not in AWARD_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(AWARD_KINDS),))
        _cents(amount_cents, "amount_cents")
        with self._lock:
            for existing in self._in_commons(self._awards, commons_id):
                if existing["award_ref"] == award_ref:
                    raise ValidationError(
                        "award_ref %r is already recorded in this commons"
                        % (award_ref,))
            if parent_award_id is not None:
                parent = self._get(self._awards, parent_award_id, "award")
                if parent["commons_id"] != commons_id:
                    raise ValidationError(
                        "parent award is in a different commons")
                if parent["kind"] != "prime":
                    raise ValidationError(
                        "parent award must be a prime award")
                if kind != "subaward":
                    raise ValidationError(
                        "only a subaward may name a parent award")
            return self._create(
                self._awards, "awd-",
                {"commons_id": commons_id, "award_ref": award_ref,
                 "awardee_ref": awardee_ref, "kind": kind,
                 "amount_cents": amount_cents,
                 "parent_award_id": parent_award_id,
                 "funds_moved_here": False},
                actor, "ext_award_record")

    def list_awards(self, actor, commons_id, kind=None):
        """List award records in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        awards = self._in_commons(self._awards, commons_id)
        if kind is not None:
            awards = [a for a in awards if a["kind"] == kind]
        return copy.deepcopy(self._sorted(awards))

    def list_subawards(self, actor, award_id):
        """List the recorded subawards under one prime. Action: read."""
        self._maybe_require(actor, "read")
        parent = self._get(self._awards, award_id, "award")
        self._check_commons_of(actor, parent)
        subs = [a for a in self._awards.values()
                if a["parent_award_id"] == award_id]
        return copy.deepcopy(self._sorted(subs))

    def award_analysis(self, actor, commons_id):
        """Deterministic sums and counts over award records.

        Action: read. Method ``deterministic_sums`` -- arithmetic
        over recorded integer cents only; no award is scored or
        ranked and no funds move."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        awards = self._in_commons(self._awards, commons_id)
        primes = [a for a in awards if a["kind"] == "prime"]
        subs = [a for a in awards if a["kind"] == "subaward"]
        return {
            "commons_id": commons_id,
            "award_count": len(awards),
            "prime_count": len(primes),
            "subaward_count": len(subs),
            "total_cents": sum(a["amount_cents"] for a in awards),
            "prime_cents": sum(a["amount_cents"] for a in primes),
            "subaward_cents": sum(a["amount_cents"] for a in subs),
            "method": "deterministic_sums",
            "funds_moved_here": False,
        }

    # -- Entity / relationship-graph analytics (idx 830, built) ---------
    # Records form: entities are opaque references; relationships
    # are recorded edges between them with a verbatim label.
    # "Analytics" are deterministic degree / label counts over the
    # recorded edges at read: no inference is drawn from the graph
    # and nothing is scored (``inference_here`` is False).

    def register_entity(self, actor, commons_id, entity_ref, kind):
        """Register one entity reference in a commons. Action: record."""
        self._guard(actor, "record", "ext_entity_register")
        self._commons(actor, commons_id)
        _non_empty(entity_ref, "entity_ref")
        if kind not in ENTITY_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(ENTITY_KINDS),))
        with self._lock:
            for existing in self._in_commons(self._entities, commons_id):
                if existing["entity_ref"] == entity_ref:
                    raise ValidationError(
                        "entity_ref %r is already registered in this commons"
                        % (entity_ref,))
            return self._create(
                self._entities, "ent-",
                {"commons_id": commons_id, "entity_ref": entity_ref,
                 "kind": kind},
                actor, "ext_entity_register")

    def record_relationship(self, actor, commons_id, source_entity_id,
                            target_entity_id, relationship_label):
        """Record one directed relationship edge. Action: record."""
        self._guard(actor, "record", "ext_relationship_record")
        self._commons(actor, commons_id)
        _non_empty(relationship_label, "relationship_label")
        with self._lock:
            source = self._get(self._entities, source_entity_id, "entity")
            target = self._get(self._entities, target_entity_id, "entity")
            if source["commons_id"] != commons_id \
                    or target["commons_id"] != commons_id:
                raise ValidationError(
                    "both entities must belong to this commons")
            if source_entity_id == target_entity_id:
                raise ValidationError(
                    "an entity may not record a relationship to itself")
            for existing in self._in_commons(self._relationships, commons_id):
                if existing["source_entity_id"] == source_entity_id \
                        and existing["target_entity_id"] == target_entity_id \
                        and existing["relationship_label"] == relationship_label:
                    raise ValidationError(
                        "this relationship is already recorded")
            return self._create(
                self._relationships, "rel-",
                {"commons_id": commons_id,
                 "source_entity_id": source_entity_id,
                 "target_entity_id": target_entity_id,
                 "relationship_label": relationship_label},
                actor, "ext_relationship_record")

    def _degrees(self, entity_id):
        out_degree = sum(1 for r in self._relationships.values()
                         if r["source_entity_id"] == entity_id)
        in_degree = sum(1 for r in self._relationships.values()
                        if r["target_entity_id"] == entity_id)
        return out_degree, in_degree

    def entity_view(self, actor, entity_id):
        """One entity with its derived degrees. Action: read.

        Degrees are derived at read from the recorded edges and
        never stored on the entity record."""
        self._maybe_require(actor, "read")
        entity = self._get(self._entities, entity_id, "entity")
        self._check_commons_of(actor, entity)
        view = copy.deepcopy(entity)
        out_degree, in_degree = self._degrees(entity_id)
        view["out_degree"] = out_degree
        view["in_degree"] = in_degree
        view["total_degree"] = out_degree + in_degree
        view["method"] = "deterministic_counts"
        view["inference_here"] = False
        return view

    def list_neighbors(self, actor, entity_id):
        """Recorded neighbor entity ids, by direction. Action: read."""
        self._maybe_require(actor, "read")
        entity = self._get(self._entities, entity_id, "entity")
        self._check_commons_of(actor, entity)
        outgoing = {r["target_entity_id"]
                    for r in self._relationships.values()
                    if r["source_entity_id"] == entity_id}
        incoming = {r["source_entity_id"]
                    for r in self._relationships.values()
                    if r["target_entity_id"] == entity_id}
        by_num = lambda ids: sorted(ids, key=_id_num)  # noqa: E731
        return {"entity_id": entity_id,
                "outgoing": by_num(outgoing),
                "incoming": by_num(incoming),
                "method": "deterministic_counts",
                "inference_here": False}

    def relationship_counts(self, actor, commons_id):
        """Edge counts by verbatim label, derived at read. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        edges = self._in_commons(self._relationships, commons_id)
        by_label = {}
        for edge in edges:
            label = edge["relationship_label"]
            by_label[label] = by_label.get(label, 0) + 1
        return {"commons_id": commons_id, "edge_count": len(edges),
                "entity_count": len(self._in_commons(self._entities,
                                                     commons_id)),
                "by_label": by_label, "method": "deterministic_counts",
                "inference_here": False}

    # -- Saved-search, alerting & entity-tracking (idx 831, reference) --
    # Labeled reference implementation: a saved search is a
    # reference record (an opaque search reference and a scope
    # label). Nothing is executed, no alert is ever sent, and no
    # entity is tracked by this substrate.

    def record_saved_search(self, actor, commons_id, search_ref, scope_label):
        """Record a saved-search reference. Action: record."""
        self._guard(actor, "record", "ext_saved_search_record")
        self._commons(actor, commons_id)
        _non_empty(search_ref, "search_ref")
        _non_empty(scope_label, "scope_label")
        with self._lock:
            return self._create(
                self._saved_searches, "sst-",
                {"commons_id": commons_id, "search_ref": search_ref,
                 "scope_label": scope_label, "reference_stub": True,
                 "state": _REFERENCE_STATE, "executed_here": False,
                 "alerts_sent_here": False},
                actor, "ext_saved_search_record")

    def record_entity_tracking(self, actor, commons_id, entity_id,
                               tracking_label):
        """Record an entity-tracking reference. Action: record."""
        self._guard(actor, "record", "ext_tracking_record")
        self._commons(actor, commons_id)
        _non_empty(tracking_label, "tracking_label")
        with self._lock:
            entity = self._get(self._entities, entity_id, "entity")
            if entity["commons_id"] != commons_id:
                raise ValidationError("entity is in a different commons")
            return self._create(
                self._tracking_records, "trk-",
                {"commons_id": commons_id, "entity_id": entity_id,
                 "tracking_label": tracking_label, "reference_stub": True,
                 "state": _REFERENCE_STATE, "tracking_active_here": False},
                actor, "ext_tracking_record")

    def list_saved_searches(self, actor, commons_id):
        """List saved-search reference records. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(self._sorted(
            self._in_commons(self._saved_searches, commons_id)))

    def list_tracking_records(self, actor, commons_id):
        """List entity-tracking reference records. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(self._sorted(
            self._in_commons(self._tracking_records, commons_id)))

    # -- Clinical-trial EDC (idx 832, built) -----------------------------
    # Records form: a capture form is a definition record -- its
    # fields are opaque field REFERENCES held as data, never
    # rendered or executed. A submission record carries counts and
    # a recorded status label only. No captured value can exist in
    # any shape here: ``captured_values_held_here`` is False on
    # every form and submission record.

    def define_capture_form(self, actor, commons_id, form_ref, title,
                            field_refs):
        """Define one capture form (field references as data).

        Action: record."""
        self._guard(actor, "record", "ext_form_define")
        self._commons(actor, commons_id)
        _non_empty(form_ref, "form_ref")
        _non_empty(title, "title")
        refs = _string_list(field_refs, "field_refs")
        if len(set(refs)) != len(refs):
            raise ValidationError("field_refs must not contain duplicates")
        with self._lock:
            for existing in self._in_commons(self._capture_forms, commons_id):
                if existing["form_ref"] == form_ref:
                    raise ValidationError(
                        "form_ref %r is already defined in this commons"
                        % (form_ref,))
            return self._create(
                self._capture_forms, "frm-",
                {"commons_id": commons_id, "form_ref": form_ref,
                 "title": title, "field_refs": refs,
                 "captured_values_held_here": False},
                actor, "ext_form_define")

    def form_view(self, actor, form_id):
        """One capture form with its derived field count. Action: read."""
        self._maybe_require(actor, "read")
        form = self._get(self._capture_forms, form_id, "capture form")
        self._check_commons_of(actor, form)
        view = copy.deepcopy(form)
        view["field_count"] = len(form["field_refs"])
        return view

    def record_submission(self, actor, commons_id, form_id, site_ref,
                          fields_reported, queries_reported=0,
                          subject_ref=None,
                          recorded_status="reported_submitted"):
        """Record one form submission (counts + recorded status only).

        Action: enter. ``subject_ref``, when given, is an opaque
        participant reference; no captured value is accepted by any
        parameter of this method."""
        self._guard(actor, "enter", "ext_submission_record")
        self._commons(actor, commons_id)
        _non_empty(site_ref, "site_ref")
        if subject_ref is not None:
            _non_empty(subject_ref, "subject_ref")
        if recorded_status not in SUBMISSION_STATES:
            raise ValidationError(
                "recorded_status must be one of %s"
                % (", ".join(SUBMISSION_STATES),))
        _count(fields_reported, "fields_reported")
        _count(queries_reported, "queries_reported")
        with self._lock:
            form = self._get(self._capture_forms, form_id, "capture form")
            if form["commons_id"] != commons_id:
                raise ValidationError("form is in a different commons")
            return self._create(
                self._submissions, "sub-",
                {"commons_id": commons_id, "form_id": form_id,
                 "site_ref": site_ref, "subject_ref": subject_ref,
                 "recorded_status": recorded_status,
                 "fields_reported": fields_reported,
                 "queries_reported": queries_reported,
                 "captured_values_held_here": False},
                actor, "ext_submission_record")

    def list_submissions(self, actor, commons_id, form_id=None):
        """List submission records in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        subs = self._in_commons(self._submissions, commons_id)
        if form_id is not None:
            subs = [s for s in subs if s["form_id"] == form_id]
        return copy.deepcopy(self._sorted(subs))

    # -- eConsent & eCOA (idx 833, built) --------------------------------
    # Records form: a consent instrument is a reference record
    # (instrument reference + version label). A consent STATE is a
    # recorded label per opaque participant reference; the current
    # state is derived at read from the recorded history and never
    # stored. Nothing is signed -- no signature bytes can exist in
    # any shape -- and no consent is legally effected here
    # (``consent_effected_here`` is False). eCOA instruments are
    # definitions; a response record carries a COUNT only, never
    # response content.

    def define_consent_instrument(self, actor, commons_id, instrument_ref,
                                  version_label):
        """Define one consent instrument reference. Action: record."""
        self._guard(actor, "record", "ext_consent_instrument_define")
        self._commons(actor, commons_id)
        _non_empty(instrument_ref, "instrument_ref")
        _non_empty(version_label, "version_label")
        with self._lock:
            for existing in self._in_commons(self._consent_instruments,
                                            commons_id):
                if existing["instrument_ref"] == instrument_ref:
                    raise ValidationError(
                        "instrument_ref %r is already defined in this commons"
                        % (instrument_ref,))
            return self._create(
                self._consent_instruments, "cin-",
                {"commons_id": commons_id,
                 "instrument_ref": instrument_ref,
                 "version_label": version_label,
                 "signature_possible_here": False,
                 "consent_effected_here": False},
                actor, "ext_consent_instrument_define")

    def record_consent_state(self, actor, commons_id, instrument_id,
                             participant_ref, state_label):
        """Record one consent state for an opaque participant ref.

        Action: enter. The label is stored exactly as reported;
        states are append-only history records."""
        self._guard(actor, "enter", "ext_consent_state_record")
        self._commons(actor, commons_id)
        _non_empty(participant_ref, "participant_ref")
        if state_label not in CONSENT_STATES:
            raise ValidationError(
                "state_label must be one of %s"
                % (", ".join(CONSENT_STATES),))
        with self._lock:
            instrument = self._get(self._consent_instruments, instrument_id,
                                   "consent instrument")
            if instrument["commons_id"] != commons_id:
                raise ValidationError(
                    "instrument is in a different commons")
            return self._create(
                self._consent_states, "cns-",
                {"commons_id": commons_id, "instrument_id": instrument_id,
                 "participant_ref": participant_ref,
                 "state_label": state_label, "signature_held_here": False,
                 "consent_effected_here": False},
                actor, "ext_consent_state_record")

    def _consent_history(self, instrument_id, participant_ref):
        return self._sorted(
            [r for r in self._consent_states.values()
             if r["instrument_id"] == instrument_id
             and r["participant_ref"] == participant_ref])

    def _current_consent_label(self, history):
        """The current consent state: the label of the LATEST
        recorded state in ``history`` (creation order).

        This is the single derivation point for current consent
        state -- the batch's fresh negative control mutates it
        (see tests/README.md)."""
        return history[-1]["state_label"]

    def consent_current_state(self, actor, instrument_id, participant_ref):
        """Derive a participant's current consent state at read.

        Action: read. The current state is the latest recorded
        label; it is derived here and never stored on any record."""
        self._maybe_require(actor, "read")
        instrument = self._get(self._consent_instruments, instrument_id,
                               "consent instrument")
        self._check_commons_of(actor, instrument)
        history = self._consent_history(instrument_id, participant_ref)
        if not history:
            raise NotFoundError(
                "no consent state recorded for participant %r on "
                "instrument %r" % (participant_ref, instrument_id))
        return {"instrument_id": instrument_id,
                "participant_ref": participant_ref,
                "current_state": self._current_consent_label(history),
                "state_record_count": len(history),
                "derived": True, "method": "latest_recorded_state",
                "consent_effected_here": False}

    def define_outcome_instrument(self, actor, commons_id, instrument_ref,
                                  kind):
        """Define one eCOA outcome instrument. Action: record."""
        self._guard(actor, "record", "ext_outcome_instrument_define")
        self._commons(actor, commons_id)
        _non_empty(instrument_ref, "instrument_ref")
        if kind not in OUTCOME_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(OUTCOME_KINDS),))
        with self._lock:
            for existing in self._in_commons(self._outcome_instruments,
                                            commons_id):
                if existing["instrument_ref"] == instrument_ref:
                    raise ValidationError(
                        "instrument_ref %r is already defined in this commons"
                        % (instrument_ref,))
            return self._create(
                self._outcome_instruments, "oin-",
                {"commons_id": commons_id,
                 "instrument_ref": instrument_ref, "kind": kind,
                 "response_content_held_here": False},
                actor, "ext_outcome_instrument_define")

    def record_outcome_response_count(self, actor, commons_id, instrument_id,
                                      participant_ref, responses_reported):
        """Record an eCOA response COUNT for an opaque participant.

        Action: enter. Only the count is recorded; response content
        is accepted by no parameter."""
        self._guard(actor, "enter", "ext_outcome_response_record")
        self._commons(actor, commons_id)
        _non_empty(participant_ref, "participant_ref")
        _count(responses_reported, "responses_reported")
        with self._lock:
            instrument = self._get(self._outcome_instruments, instrument_id,
                                   "outcome instrument")
            if instrument["commons_id"] != commons_id:
                raise ValidationError(
                    "instrument is in a different commons")
            return self._create(
                self._outcome_responses, "ors-",
                {"commons_id": commons_id, "instrument_id": instrument_id,
                 "participant_ref": participant_ref,
                 "responses_reported": responses_reported,
                 "response_content_held_here": False},
                actor, "ext_outcome_response_record")

    # -- Clinical-trial reporting & analytics (idx 834, built) -----------
    # A deterministic counts derivation over the EDC and eConsent /
    # eCOA records held in this substrate. Counts only -- no trial
    # result is interpreted and nothing is scored.

    def clinical_summary(self, actor, commons_id):
        """Deterministic counts over the clinical records. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        subs = self._in_commons(self._submissions, commons_id)
        by_status = {}
        for sub in subs:
            label = sub["recorded_status"]
            by_status[label] = by_status.get(label, 0) + 1
        consent_counts = {}
        pairs = {(r["instrument_id"], r["participant_ref"])
                 for r in self._in_commons(self._consent_states, commons_id)}
        for instrument_id, participant_ref in pairs:
            label = self._current_consent_label(
                self._consent_history(instrument_id, participant_ref))
            consent_counts[label] = consent_counts.get(label, 0) + 1
        responses = self._in_commons(self._outcome_responses, commons_id)
        return {
            "commons_id": commons_id,
            "capture_forms": len(self._in_commons(self._capture_forms,
                                                 commons_id)),
            "submissions": len(subs),
            "submissions_by_recorded_status": by_status,
            "fields_reported_total": sum(s["fields_reported"] for s in subs),
            "queries_reported_total": sum(s["queries_reported"]
                                          for s in subs),
            "consent_instruments": len(self._in_commons(
                self._consent_instruments, commons_id)),
            "consent_current_states": consent_counts,
            "outcome_instruments": len(self._in_commons(
                self._outcome_instruments, commons_id)),
            "outcome_responses_reported_total": sum(
                r["responses_reported"] for r in responses),
            "method": "deterministic_counts",
        }

    # -- Identity resolution & background investigation (idx 835, built) --
    # PPRL precedent (Data Management units): linkage is recorded
    # as REPORTED pairs between opaque references; the method label
    # is one of the reported-method vocabulary and the match was
    # computed elsewhere -- ``match_computed_here`` is False on
    # every record, and no identifier is ever accepted as input
    # (references are opaque caller tokens, stored as given).
    # A background investigation is a case record over an opaque
    # subject reference; findings are labels recorded verbatim as
    # reported. Nothing is searched and nothing is verified here.

    def record_linkage_pair(self, actor, commons_id, left_ref, right_ref,
                            method, source_label):
        """Record one reported linkage pair. Action: record."""
        self._guard(actor, "record", "ext_linkage_record")
        self._commons(actor, commons_id)
        _non_empty(left_ref, "left_ref")
        _non_empty(right_ref, "right_ref")
        _non_empty(source_label, "source_label")
        if method not in LINKAGE_METHODS:
            raise ValidationError(
                "method must be one of %s" % (", ".join(LINKAGE_METHODS),))
        if left_ref == right_ref:
            raise ValidationError(
                "a linkage pair needs two distinct references")
        with self._lock:
            return self._create(
                self._linkage_pairs, "lnk-",
                {"commons_id": commons_id, "left_ref": left_ref,
                 "right_ref": right_ref, "method": method,
                 "source_label": source_label,
                 "match_computed_here": False,
                 "identity_verified_here": False},
                actor, "ext_linkage_record")

    def linkage_counts(self, actor, commons_id):
        """Pair counts by reported method, derived at read. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        pairs = self._in_commons(self._linkage_pairs, commons_id)
        by_method = {}
        for pair in pairs:
            by_method[pair["method"]] = by_method.get(pair["method"], 0) + 1
        return {"commons_id": commons_id, "pair_count": len(pairs),
                "by_method": by_method, "method": "deterministic_counts",
                "match_computed_here": False}

    def open_investigation_case(self, actor, commons_id, case_ref,
                                subject_ref):
        """Open one background-investigation case record.

        Action: record. ``subject_ref`` is an opaque reference; no
        field of the case can hold background content."""
        self._guard(actor, "record", "ext_investigation_open")
        self._commons(actor, commons_id)
        _non_empty(case_ref, "case_ref")
        _non_empty(subject_ref, "subject_ref")
        with self._lock:
            for existing in self._in_commons(self._investigation_cases,
                                            commons_id):
                if existing["case_ref"] == case_ref:
                    raise ValidationError(
                        "case_ref %r is already open in this commons"
                        % (case_ref,))
            return self._create(
                self._investigation_cases, "inv-",
                {"commons_id": commons_id, "case_ref": case_ref,
                 "subject_ref": subject_ref, "state": "opened",
                 "outcome_label": None, "searched_here": False,
                 "verified_here": False},
                actor, "ext_investigation_open")

    def record_investigation_finding(self, actor, case_id, finding_label):
        """Record one reported finding label on an open case.

        Action: record. The label is stored verbatim, exactly as
        reported; it is verified nowhere here."""
        self._guard(actor, "record", "ext_investigation_finding")
        _non_empty(finding_label, "finding_label")
        with self._lock:
            case = self._get(self._investigation_cases, case_id,
                             "investigation case")
            self._commons(actor, case["commons_id"])
            if case["state"] != "opened":
                raise ValidationError(
                    "findings may only be recorded on an opened case")
            return self._create(
                self._investigation_findings, "inf-",
                {"case_id": case_id, "finding_label": finding_label,
                 "verified_here": False},
                actor, "ext_investigation_finding")

    def close_investigation_case(self, actor, case_id, outcome_label):
        """Close a case with its outcome recorded verbatim. Action: record."""
        self._guard(actor, "record", "ext_investigation_close")
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            case = self._get(self._investigation_cases, case_id,
                             "investigation case")
            self._commons(actor, case["commons_id"])
            if case["state"] != "opened":
                raise ValidationError("case is already closed")
            case["state"] = "closed"
            case["outcome_label"] = outcome_label
            self._audit(actor, "ext_investigation_close", case_id)
            return copy.deepcopy(case)

    def investigation_case_view(self, actor, case_id):
        """One case with its findings and derived finding count.

        Action: read."""
        self._maybe_require(actor, "read")
        case = self._get(self._investigation_cases, case_id,
                         "investigation case")
        self._check_commons_of(actor, case)
        view = copy.deepcopy(case)
        findings = self._sorted(
            [f for f in self._investigation_findings.values()
             if f["case_id"] == case_id])
        view["findings"] = copy.deepcopy(findings)
        view["finding_count"] = len(findings)
        return view

    # -- Ongoing identity monitoring (idx 836, reference) -----------------
    # Labeled reference implementation: a monitoring reference
    # record. No monitoring runs here, no source is watched, and no
    # alert is ever sent by this substrate.

    def record_monitoring_reference(self, actor, commons_id, subject_ref,
                                    source_label):
        """Record an ongoing-monitoring reference. Action: record."""
        self._guard(actor, "record", "ext_monitoring_record")
        self._commons(actor, commons_id)
        _non_empty(subject_ref, "subject_ref")
        _non_empty(source_label, "source_label")
        with self._lock:
            return self._create(
                self._monitoring_references, "mon-",
                {"commons_id": commons_id, "subject_ref": subject_ref,
                 "source_label": source_label, "reference_stub": True,
                 "state": _REFERENCE_STATE, "monitoring_active_here": False,
                 "alerts_sent_here": False},
                actor, "ext_monitoring_record")

    def list_monitoring_references(self, actor, commons_id):
        """List monitoring reference records. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(self._sorted(
            self._in_commons(self._monitoring_references, commons_id)))

    # -- Supplier discovery & market research (idx 837, reference) --------
    # Labeled reference implementation: a discovery inquiry
    # reference record. No supplier is searched for, discovered, or
    # contacted by this substrate.

    def record_discovery_reference(self, actor, commons_id, inquiry_ref,
                                   scope_label):
        """Record a supplier-discovery reference. Action: record."""
        self._guard(actor, "record", "ext_discovery_record")
        self._commons(actor, commons_id)
        _non_empty(inquiry_ref, "inquiry_ref")
        _non_empty(scope_label, "scope_label")
        with self._lock:
            return self._create(
                self._discovery_references, "dis-",
                {"commons_id": commons_id, "inquiry_ref": inquiry_ref,
                 "scope_label": scope_label, "reference_stub": True,
                 "state": _REFERENCE_STATE,
                 "discovery_performed_here": False, "searched_here": False},
                actor, "ext_discovery_record")

    def list_discovery_references(self, actor, commons_id):
        """List discovery reference records. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(self._sorted(
            self._in_commons(self._discovery_references, commons_id)))

    # -- Supplier intelligence & capabilities data (idx 838, built) -------
    # Records form: a supplier profile is a registry record --
    # opaque supplier reference, capability labels recorded
    # verbatim, and a source label. Derivations are counts and a
    # recorded-label lookup over the held profiles; no supplier is
    # discovered or evaluated here.

    def record_supplier_profile(self, actor, commons_id, supplier_ref,
                                capability_labels, source_label):
        """Record one supplier capabilities profile. Action: record."""
        self._guard(actor, "record", "ext_supplier_record")
        self._commons(actor, commons_id)
        _non_empty(supplier_ref, "supplier_ref")
        _non_empty(source_label, "source_label")
        labels = _string_list(capability_labels, "capability_labels")
        labels = list(dict.fromkeys(labels))
        with self._lock:
            for existing in self._in_commons(self._supplier_profiles,
                                            commons_id):
                if existing["supplier_ref"] == supplier_ref:
                    raise ValidationError(
                        "supplier_ref %r is already recorded in this commons"
                        % (supplier_ref,))
            return self._create(
                self._supplier_profiles, "sup-",
                {"commons_id": commons_id, "supplier_ref": supplier_ref,
                 "capability_labels": labels, "source_label": source_label,
                 "evaluated_here": False},
                actor, "ext_supplier_record")

    def supplier_capability_counts(self, actor, commons_id):
        """Profile counts per recorded capability label. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        profiles = self._in_commons(self._supplier_profiles, commons_id)
        by_capability = {}
        for profile in profiles:
            for label in profile["capability_labels"]:
                by_capability[label] = by_capability.get(label, 0) + 1
        return {"commons_id": commons_id,
                "supplier_count": len(profiles),
                "by_capability": by_capability,
                "method": "deterministic_counts",
                "evaluated_here": False}

    def suppliers_with_capability(self, actor, commons_id, capability_label):
        """Recorded-label lookup: supplier refs carrying a label.

        Action: read. A lookup over recorded labels only -- the
        suppliers were recorded, never discovered here."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        _non_empty(capability_label, "capability_label")
        refs = sorted(p["supplier_ref"]
                      for p in self._in_commons(self._supplier_profiles,
                                                commons_id)
                      if capability_label in p["capability_labels"])
        return {"commons_id": commons_id,
                "capability_label": capability_label,
                "supplier_refs": refs, "count": len(refs),
                "method": "recorded_label_lookup",
                "evaluated_here": False}
