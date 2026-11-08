"""Final GAPS batch, second unit — Remainder Addition extensions
for the GRC L3-adjacent group.

One new module, per the batch pattern (gaps-batch/DECISION.md):
:class:`GrcExtensionsAddition` wraps the core
:class:`~grc.store.GrcStore` and adds the records surfaces that
close this group's Remainder Addition entries (GAPS.md section
"Remainder Addition — GRC L3-adjacent (+1 fork)", the Exiger
addition's two registered gaps). The core modules — and the first
batch unit's ``extensions.py`` — are untouched and byte-identical.

The category doctrine binds every surface here, exactly as it
binds the Core and the first batch unit:

- **No computed score, rating, grade, or percentage anywhere.**
  The addition fork's second entry names "analytics"; per the
  ADDENDUM's own registration, bare "Analytics" is not the
  posture-reporting family and no score follows from it. The
  analytics surface here is counts of this substrate's own
  recorded records, derived at read — the Core's posture
  discipline, nothing more.
- **Reported outcomes are stored verbatim, never computed.**
  A due-diligence outcome and a supply-chain observation's
  reported value are labels exactly as the party that performed
  the diligence or made the observation reported them. No
  research is performed here (``researched_here: False`` on
  third-party and diligence records) and nothing is measured
  here (``measured_here: False`` / ``computed_here: False`` on
  observation records): the intelligence and visibility engines
  are the addition fork's; their reported outputs are records.
- **Derived, never stored.** A third party's review status is
  derived at read time from its recorded review due date and an
  as-of date (the single derivation point is
  :func:`_third_party_review_is_overdue` /
  :func:`derive_third_party_review_status`), mirroring the
  Core's finding derivation and the first unit's grant
  derivation. Stored records carry no derived key.
- **Opaque references only.** Third parties, governed systems,
  and sources are caller-supplied opaque refs. A diligence
  record may link a Core evidence record (the artifact the
  diligence produced, filed in the Core's evidence registry —
  the ADDENDUM notes the findings such work produces are
  ingestible by the Core today); the link is validated to exist
  and this surface files nothing itself. Recording anything on
  this surface creates no Core finding, evidence, or indicator
  result (test-pinned).
- **High-baseline tier adaptations stay intact.** Mutations
  write to the same hash-chained audit log as the Core (action
  names prefixed ``exta_``), and every mutation is fail-closed
  (AU-5): if the audit write raises
  :class:`~grc.errors.AuditWriteError`, the addition state is
  rolled back from a snapshot and the error propagates. The
  ``auditor`` role holds ``audit_read`` only and is denied every
  addition operation (AC-5), as it is denied every Core registry
  operation; its core audit duty (trail read, chain
  verification) is unaffected.

Permissions reuse the Core's action vocabulary (no new actions):
third-party registration rides on governed systems
(``manage_systems``); diligence and supply-observation records
are recorded work (``record_results``). All reads require
``read``.
"""

import copy
import functools
import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import AuditWriteError, NotFoundError, ValidationError


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_text(value, what):
    """Validate an optional free-text field (a string, may be empty)."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _parse_date(value, what):
    """Parse an ISO ``YYYY-MM-DD`` date string, or raise."""
    if not isinstance(value, str):
        raise ValidationError("%s must be an ISO date string" % (what,))
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationError(
            "%s must be an ISO date (YYYY-MM-DD): %r" % (what, value)
        ) from None


def _coerce_as_of(as_of):
    """Coerce an as-of parameter to a :class:`datetime.date`.

    Mirrors the Core's coercion: ``None`` means today (UTC)."""
    if as_of is None:
        return datetime.now(timezone.utc).date()
    if isinstance(as_of, datetime):
        return as_of.date()
    if isinstance(as_of, date):
        return as_of
    if isinstance(as_of, str):
        try:
            return date.fromisoformat(as_of)
        except ValueError:
            pass
        candidate = as_of[:-1] + "+00:00" if as_of.endswith("Z") else as_of
        try:
            return datetime.fromisoformat(candidate).date()
        except ValueError:
            raise ValidationError(
                "as_of must be an ISO date or timestamp: %r" % (as_of,)
            ) from None
    raise ValidationError("as_of must be an ISO date or timestamp")


def _third_party_review_is_overdue(record, as_of_date):
    """True iff ``record`` carries a review due date before the
    as-of date.

    The single derivation point for third-party review status;
    see the mutation record in tests/README.md (this unit's fresh
    negative control patches this function's return line).
    """
    if record["review_due_date"] is None:
        return False
    due = _parse_date(record["review_due_date"], "review_due_date")
    return as_of_date > due


def derive_third_party_review_status(record, as_of=None):
    """Derive a third-party record's review status at read time.

    Returns ``"review_overdue"`` when the record's review due
    date is before the as-of date; otherwise returns
    ``"current"``. Computed on every call and never written back
    onto the record — the same derivation discipline as the
    Core's :func:`grc.store.derive_finding_status`.
    """
    if _third_party_review_is_overdue(record, _coerce_as_of(as_of)):
        return "review_overdue"
    return "current"


def _fail_closed_exta(method):
    """Wrap an addition mutation so an audit write failure rolls
    the addition state back (AU-5, mirroring the Core's wrapper
    and the first batch unit's)."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        snapshot = self._snapshot_state()
        try:
            return method(self, *args, **kwargs)
        except AuditWriteError:
            self._restore_state(snapshot)
            raise

    return wrapper


class GrcExtensionsAddition:
    """The remainder-addition extension surface over a core store."""

    def __init__(self, store):
        self.store = store
        self.audit = store.audit
        self._third_parties = {}  # id -> third-party record
        self._diligence = {}  # id -> due-diligence record
        self._supply_observations = {}  # id -> supply observation record
        self._counters = {"tpa": 0, "ddq": 0, "sco": 0}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _snapshot_state(self):
        return (
            copy.deepcopy(self._third_parties),
            copy.deepcopy(self._diligence),
            copy.deepcopy(self._supply_observations),
            dict(self._counters),
        )

    def _restore_state(self, snapshot):
        (
            self._third_parties,
            self._diligence,
            self._supply_observations,
            self._counters,
        ) = snapshot

    @staticmethod
    def _require(actor, action):
        """Enforce permissions when ``actor`` is a User-like object
        (mirrors the Core store's convention)."""
        if actor is not None and hasattr(actor, "role"):
            require(actor, action)

    def _require_system(self, system_ref, actor):
        """Raise NotFoundError unless ``system_ref`` is a governed
        system in the core store."""
        self.store.get_system(system_ref, actor)

    def _get_third_party_record(self, third_party_id):
        record = self._third_parties.get(third_party_id)
        if record is None:
            raise NotFoundError(
                "third party not found: %r" % (third_party_id,)
            )
        return record

    # -- third-party records (idx 670) -----------------------------------
    #
    # The fork's Due Diligence Intelligence (DDIQ) and Third Party
    # Management (3PM) modules are a research/intelligence engine
    # over vendors and counterparties. This surface is the registry
    # that work presupposes: third parties registered by opaque
    # reference, and due-diligence records holding the outcome of
    # diligence performed elsewhere, verbatim. No research is
    # performed here and no third party is investigated here.

    @_fail_closed_exta
    def register_third_party(self, third_party_ref, actor, system_ref=None,
                              review_due_date=None, note=""):
        """Register a third party (vendor / counterparty) by opaque
        reference.

        ``third_party_ref`` is unique on this surface: a duplicate
        registration is rejected whole. ``review_due_date``, when
        given, is the recorded date by which the next diligence
        review falls due; the review *status* is derived from it
        at read, never stored. The record carries
        ``researched_here: False`` — registering a third party
        researches nothing about it. Action: manage_systems.
        Id prefix: tpa-.
        """
        _validate_non_empty(third_party_ref, "third-party reference")
        if review_due_date is not None:
            _parse_date(review_due_date, "review_due_date")
        note = _validate_text(note, "note")
        self._require(actor, "manage_systems")
        with self._lock:
            if system_ref is not None:
                self._require_system(system_ref, actor)
            for existing in self._third_parties.values():
                if existing["third_party_ref"] == third_party_ref:
                    raise ValidationError(
                        "third party already registered: %r" % (third_party_ref,)
                    )
            third_party_id = self._next_id("tpa")
            record = {
                "id": third_party_id,
                "third_party_ref": third_party_ref,
                "system_ref": system_ref,
                "review_due_date": review_due_date,
                "note": note,
                "researched_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._third_parties[third_party_id] = record
            self._audit(actor, "exta_third_party_create", third_party_id,
                        details={"third_party_ref": third_party_ref})
            return dict(record)

    def _third_party_view(self, record, as_of):
        view = dict(record)
        if as_of is not None:
            view["derived_status"] = derive_third_party_review_status(
                record, as_of
            )
        return view

    def get_third_party(self, third_party_id, actor, as_of=None):
        """Return one third-party record; with ``as_of``, the copy
        gains a read-time ``derived_status`` (the stored record
        never does). Action: read."""
        self._require(actor, "read")
        with self._lock:
            record = self._get_third_party_record(third_party_id)
            return self._third_party_view(record, as_of)

    def list_third_parties(self, actor, system_ref=None, as_of=None):
        """Return third-party records, optionally filtered by
        governed system; ``as_of`` attaches the read-time derived
        review status to each copy. Action: read."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._third_parties.values())
            if system_ref is not None:
                records = [r for r in records if r["system_ref"] == system_ref]
            return [self._third_party_view(r, as_of) for r in records]

    @_fail_closed_exta
    def record_diligence(self, third_party_id, diligence_kind, outcome_label,
                         actor, evidence_id=None):
        """Record a due-diligence outcome reported for a registered
        third party.

        ``diligence_kind`` (initial diligence, periodic review,
        ...) and ``outcome_label`` are verbatim labels: the
        outcome is whatever the diligence performed elsewhere
        reported, stored exactly as reported and never computed
        from anything. ``evidence_id``, when given, links the
        Core evidence record the diligence produced; it is
        validated to exist, and this surface files nothing
        itself. The record carries ``researched_here: False``.
        Action: record_results. Id prefix: ddq-.
        """
        _validate_non_empty(diligence_kind, "diligence kind")
        _validate_non_empty(outcome_label, "diligence outcome label")
        self._require(actor, "record_results")
        with self._lock:
            self._get_third_party_record(third_party_id)
            if evidence_id is not None:
                self.store.get_evidence(evidence_id, actor)
            diligence_id = self._next_id("ddq")
            record = {
                "id": diligence_id,
                "third_party_id": third_party_id,
                "diligence_kind": diligence_kind,
                "outcome_label": outcome_label,
                "evidence_id": evidence_id,
                "researched_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._diligence[diligence_id] = record
            self._audit(actor, "exta_diligence_create", diligence_id,
                        details={"third_party_id": third_party_id})
            return dict(record)

    def list_diligence(self, actor, third_party_id=None):
        """Return due-diligence records, optionally filtered by
        third party, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._diligence.values())
            if third_party_id is not None:
                records = [
                    r for r in records if r["third_party_id"] == third_party_id
                ]
            return [dict(r) for r in records]

    # -- supply-chain observation records (idx 671) ----------------------
    #
    # The fork's Supply Dynamics (SDX) and Analytics modules are a
    # visibility/analytics engine over supply chains. This surface
    # records the observations such an engine (or a person) reports
    # about a registered third party's supply chain: a dimension
    # label and a reported value, both verbatim. Nothing is
    # measured here and no value is computed from another: the
    # "analytics" this substrate performs is the counts-only
    # summary below, derived at read over these records.

    @_fail_closed_exta
    def record_supply_observation(self, third_party_id, dimension_label,
                                  reported_label, actor, system_ref=None,
                                  source_ref=""):
        """Record a supply-chain observation reported for a
        registered third party.

        ``dimension_label`` (lead time, capacity, ...) and
        ``reported_label`` are verbatim: the reported value is
        held as the label it was reported as — never parsed,
        summed, or rolled up. The record carries
        ``measured_here: False`` and ``computed_here: False``.
        Action: record_results. Id prefix: sco-.
        """
        _validate_non_empty(dimension_label, "dimension label")
        _validate_non_empty(reported_label, "reported label")
        source_ref = _validate_text(source_ref, "source reference")
        self._require(actor, "record_results")
        with self._lock:
            self._get_third_party_record(third_party_id)
            if system_ref is not None:
                self._require_system(system_ref, actor)
            observation_id = self._next_id("sco")
            record = {
                "id": observation_id,
                "third_party_id": third_party_id,
                "system_ref": system_ref,
                "dimension_label": dimension_label,
                "reported_label": reported_label,
                "source_ref": source_ref,
                "measured_here": False,
                "computed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._supply_observations[observation_id] = record
            self._audit(actor, "exta_supply_observation_create", observation_id,
                        details={"third_party_id": third_party_id})
            return dict(record)

    def list_supply_observations(self, actor, third_party_id=None,
                                 dimension_label=None):
        """Return supply observation records, optionally filtered.
        Action: read."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._supply_observations.values())
            if third_party_id is not None:
                records = [
                    r for r in records if r["third_party_id"] == third_party_id
                ]
            if dimension_label is not None:
                records = [
                    r for r in records
                    if r["dimension_label"] == dimension_label
                ]
            return [dict(r) for r in records]

    # -- derived third-party view -----------------------------------------

    def third_party_view(self, third_party_id, actor, as_of=None):
        """Return the derived view of one third party: the stored
        record plus values derived at read from this surface's own
        records — the diligence record count, the latest recorded
        diligence outcome, and the supply observation count (and,
        with ``as_of``, the derived review status). The stored
        record never gains any of these keys (test-pinned: the
        view tracks registry state added after registration).
        Action: read."""
        self._require(actor, "read")
        with self._lock:
            record = self._get_third_party_record(third_party_id)
            view = self._third_party_view(record, as_of)
            diligence = [
                r for r in self._diligence.values()
                if r["third_party_id"] == third_party_id
            ]
            view["diligence_count"] = len(diligence)
            view["latest_diligence_outcome"] = (
                diligence[-1]["outcome_label"] if diligence else None
            )
            view["supply_observation_count"] = sum(
                1 for r in self._supply_observations.values()
                if r["third_party_id"] == third_party_id
            )
            return view

    # -- addition summary (counts only) ------------------------------------

    def addition_summary(self, actor, as_of=None):
        """Return the addition summary, computed on read: counts
        of this surface's recorded records and of their verbatim
        recorded labels only — third parties by derived review
        status at the as-of date, diligence records by kind and
        by reported outcome, supply observations by dimension.
        No score, rating, grade, or computed value of any kind is
        produced — the same doctrine as the Core's posture
        summary. Does not audit. Action: read."""
        self._require(actor, "read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            by_review_status = {"current": 0, "review_overdue": 0}
            for record in self._third_parties.values():
                status = derive_third_party_review_status(record, as_of_date)
                by_review_status[status] += 1

            diligence_by_kind = {}
            diligence_by_outcome = {}
            for record in self._diligence.values():
                kind = record["diligence_kind"]
                diligence_by_kind[kind] = diligence_by_kind.get(kind, 0) + 1
                outcome = record["outcome_label"]
                diligence_by_outcome[outcome] = (
                    diligence_by_outcome.get(outcome, 0) + 1
                )

            observations_by_dimension = {}
            for record in self._supply_observations.values():
                dimension = record["dimension_label"]
                observations_by_dimension[dimension] = (
                    observations_by_dimension.get(dimension, 0) + 1
                )

            return {
                "as_of": as_of_date.isoformat(),
                "third_parties": {
                    "total": len(self._third_parties),
                    "by_review_status": by_review_status,
                },
                "diligence": {
                    "total": len(self._diligence),
                    "by_kind": diligence_by_kind,
                    "by_outcome": diligence_by_outcome,
                },
                "supply_observations": {
                    "total": len(self._supply_observations),
                    "by_dimension": observations_by_dimension,
                },
            }
