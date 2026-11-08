"""Final GAPS batch extensions for Health & Wellness L1
(Remainder Singleton 61).

Clean-room, standard-library-only extensions for the 2 open
entries of the "Remainder Singleton 61 -- Health & Wellness L1"
section (see ``BATCH.md`` in the group directory for the per-entry
disposition and the re-judgment grounds). This module is a wrapper
around :class:`HealthStore`; every core module is untouched and
byte-identical to the shipped singleton build.

**Both entries are this fork's own clinical/diagnostic engines**,
named from its description's own words, and this group's
UNION-SPEC states the bound plainly: they are clinical/diagnostic
surfaces, and per the category's hard privacy rule they are never
built here -- nothing in this build claims any diagnostic
function, dispatches a device, initializes one, collects a study,
or reviews one. Both entries therefore ship as **labeled
reference implementations**, following the sibling tier's ruling
for the same shape (Singleton 46's batch unit re-judged its two
build-extension drafts to reference on these grounds): a registry
of the external engine's reported activity -- dispatch,
initialization, collection, and review records against opaque
references. Every record carries ``reference_stub: True`` and
state ``recorded_reference_only``; outcome labels are the external
engine's own, stored verbatim; nothing here is computed from
clinical content, because no clinical content exists in any shape.

**The category's HARD PRIVACY RULE binds absolutely, here as in
the core:** records and opaque caller-supplied references only.
No entity shape in this module has a name, contact, date-of-birth,
member-number, insurer, diagnosis, clinical-note, study-data,
test-result, finding, waveform, signal, or hardware-identifier
field -- those fields **do not exist**. A study is named only by
an opaque ``study_ref`` held in the external system; a device only
by an opaque ``device_ref``; a collection carries a reported
record count and nothing else. Methods accept only their named
parameters, so a caller cannot smuggle a forbidden field into a
record (pinned by tests: an unexpected keyword raises
``TypeError``). This build is **not a medical device and claims
no FDA status** -- the fork's device clearance belongs to the
fork's product.

Tier discipline (L1, the lightest tier): the extension writes to
the core's plain append-only audit log with ``ext_``-prefixed
actions, and denied write attempts are recorded with a
``:denied`` suffix. There is no hash chain, no fail-closed audit
machinery, and no lockout here -- those are Singleton 46's High
uplifts and are not inherited downward. The auditor keeps this
tier's core read set (the 7 record reads + ``report_read`` +
``audit_read``) and no writes. RBAC via :mod:`health.access` with
the core's existing actions, enforced before any state change or
id allocation, so a failed operation consumes no id and changes
nothing; member scope mirrors the store's -- a member-role actor
may only read records whose participant's ``participant_ref`` is
their own name. Derived values (outcome counts, latest outcome
labels, reported-record totals stated as sums of reports) are
computed at read and never stored.
"""

import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

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


def _validate_date(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO date string (YYYY-MM-DD)" % (what,))
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO date: %r" % (what, value)) from exc


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class HealthExtensions:
    """Reference-implementation surface wrapping one :class:`HealthStore`."""

    def __init__(self, store):
        self.store = store
        self._dispatch_references = {}
        self._initialization_outcomes = {}
        self._collection_references = {}
        self._review_outcomes = {}
        self._counters = {"dsp": 0, "ini": 0, "col": 0, "rvw": 0}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    def _guard(self, actor, rbac_action, audit_action):
        """Enforce a write permission before any state change.

        Mirrors the core store's convention (a User-like actor is
        checked via :func:`health.access.require`; a plain string
        carries identity but no role). A denied attempt is recorded
        on the audit log with a ``:denied`` suffix before the error
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

    @staticmethod
    def _is_member(actor):
        return actor is not None and getattr(actor, "role", None) == "member"

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _check_participant(self, participant_id, actor):
        """Validate that a participant exists (core getter; the
        core enforces the actor's participant_read and, for a
        member actor, member scope)."""
        return self.store.get_participant(participant_id, actor)

    def _check_program(self, program_id, actor):
        return self.store.get_program(program_id, actor)

    def _member_participant_ids(self, actor):
        """The participant ids a member actor may read (their own)."""
        return {p["id"] for p in self.store.list_participants(actor)}

    def _scoped(self, actor, records, key="participant_id"):
        if self._is_member(actor):
            own = self._member_participant_ids(actor)
            return [r for r in records if r.get(key) in own]
        return list(records)

    def _scope_check_record(self, actor, record, key="participant_id"):
        if self._is_member(actor):
            own = self._member_participant_ids(actor)
            if record.get(key) not in own:
                raise PermissionDenied(
                    "permission denied: member %r may not access records of "
                    "another participant" % (getattr(actor, "name", None),))

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    @staticmethod
    def _latest_label(records, key):
        """The most recent record's label for ``key``, or None.

        The single latest-value seam for the extension views:
        derived-never-stored means every current value a view
        reports is selected here, at read, from the record list --
        the canonical record list is in id order, so the latest
        record is the last one.
        """
        return records[-1][key] if records else None

    def _check_dispatch_device_unique(self, participant_id, device_ref):
        """Uniqueness seam for dispatch references.

        A dispatch reference names exactly one reported dispatch
        of a device to a participant, so a second dispatch
        reference for the same participant + ``device_ref`` pair
        is refused. MUTATION DRILL NOTE: neutralizing this scan
        (iterating nothing) is this unit's negative-control
        mutation; the suite's duplicate-refusal tests then fail
        (see tests/README.md for the verified record).
        """
        for existing in self._dispatch_references.values():
            if (existing["participant_id"] == participant_id
                    and existing["device_ref"] == device_ref):
                raise ValidationError(
                    "device_ref %r is already dispatch-referenced to this "
                    "participant" % (device_ref,))

    # -- Home sleep-test dispatch & device initialization --------------
    # REFERENCE IMPLEMENTATION (re-judged from build-extension; see
    # BATCH.md): dispatching a device into a patient's home and
    # initializing it are acts on a physical device, performed by
    # the fork's platform -- no derivation over registry records
    # dispatches or initializes anything, and this group's spec
    # rules these surfaces are never built here. The honest
    # in-substrate form is the reference registry: a dispatch
    # reference records that a dispatch was requested/reported for
    # an opaque device reference against a core participant (and
    # optionally a core program); an initialization outcome
    # records the outcome label the external platform reported,
    # verbatim. Every record carries ``reference_stub: True``,
    # ``dispatched_here: False`` and ``initialized_here: False``.
    # No device payload, serial, or study data exists in any shape.

    def create_dispatch_reference(self, participant_id, device_ref, actor,
                                  program_id=None, requested_on=None):
        """Register a dispatch reference. Action: activity_write.

        A reference record only: this substrate dispatches no
        device and initializes none.
        """
        self._guard(actor, "activity_write", "ext_dispatch_reference_create")
        _non_empty(device_ref, "device_ref")
        if requested_on is not None:
            _validate_date(requested_on, "requested_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            if program_id is not None:
                self._check_program(program_id, actor)
            self._check_dispatch_device_unique(participant_id, device_ref)
            record_id = self._next_id("dsp")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "program_id": program_id,
                "device_ref": device_ref,
                "requested_on": requested_on,
                "reference_stub": True,
                "dispatched_here": False,
                "initialized_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._dispatch_references[record_id] = record
            self._audit(actor, "ext_dispatch_reference_create", record_id,
                        details={"participant_id": participant_id,
                                 "device_ref": device_ref})
            return dict(record)

    def record_initialization_outcome(self, dispatch_id, outcome_label, actor,
                                      occurred_on=None):
        """Record a reported initialization outcome. Action: activity_write.

        The outcome label is the external platform's own, stored
        verbatim; the device was initialized elsewhere, never here
        (``initialized_here: False``).
        """
        self._guard(actor, "activity_write",
                    "ext_initialization_outcome_record")
        _non_empty(outcome_label, "outcome_label")
        if occurred_on is not None:
            _validate_date(occurred_on, "occurred_on")
        with self._lock:
            dispatch = self._get(self._dispatch_references, dispatch_id,
                                 "dispatch reference")
            record_id = self._next_id("ini")
            record = {
                "id": record_id,
                "dispatch_id": dispatch_id,
                "participant_id": dispatch["participant_id"],
                "outcome_label": outcome_label,
                "occurred_on": occurred_on,
                "reference_stub": True,
                "initialized_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._initialization_outcomes[record_id] = record
            self._audit(actor, "ext_initialization_outcome_record", record_id,
                        details={"dispatch_id": dispatch_id,
                                 "outcome_label": outcome_label})
            return dict(record)

    def _dispatch_view(self, dispatch):
        outcomes = self._sorted(
            [o for o in self._initialization_outcomes.values()
             if o["dispatch_id"] == dispatch["id"]])
        view = dict(dispatch)
        view["outcome_count"] = len(outcomes)
        view["latest_outcome_label"] = self._latest_label(
            outcomes, "outcome_label")
        return view

    def get_dispatch_reference(self, dispatch_id, actor=None):
        """One dispatch reference with derived outcome state.

        Action: activity_read (+ member scope).
        """
        self._maybe_require(actor, "activity_read")
        with self._lock:
            dispatch = self._get(self._dispatch_references, dispatch_id,
                                 "dispatch reference")
            self._scope_check_record(actor, dispatch)
            return self._dispatch_view(dispatch)

    def list_dispatch_references(self, actor=None, participant_id=None):
        """Return dispatch references with derived outcome state.

        Action: activity_read (+ member scope).
        """
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._dispatch_references.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [self._dispatch_view(r)
                    for r in self._scoped(actor, records)]

    def list_initialization_outcomes(self, actor=None, dispatch_id=None):
        """Return initialization outcome records. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._initialization_outcomes.values())
            if dispatch_id is not None:
                records = [r for r in records
                           if r["dispatch_id"] == dispatch_id]
            return [dict(r) for r in self._scoped(actor, records)]

    def dispatch_summary(self, actor, participant_id=None):
        """Derived dispatch counts. Action: report_read (+ member scope).

        Deterministic counts over held reference records only --
        ``method: deterministic_counts``. Never stored.
        """
        self._guard(actor, "report_read", "ext_dispatch_summary")
        with self._lock:
            if participant_id is not None:
                self._check_participant(participant_id, actor)
            dispatches = list(self._dispatch_references.values())
            outcomes = list(self._initialization_outcomes.values())
            if participant_id is not None:
                dispatches = [d for d in dispatches
                              if d["participant_id"] == participant_id]
                outcomes = [o for o in outcomes
                            if o["participant_id"] == participant_id]
            dispatches = self._scoped(actor, dispatches)
            outcomes = self._scoped(actor, outcomes)
            by_latest_outcome = {}
            unreported = 0
            for dispatch in dispatches:
                label = self._dispatch_view(dispatch)["latest_outcome_label"]
                if label is None:
                    unreported += 1
                else:
                    by_latest_outcome[label] = by_latest_outcome.get(label, 0) + 1
            return {
                "participant_id": participant_id,
                "method": "deterministic_counts",
                "dispatches": len(dispatches),
                "initialization_outcomes": len(outcomes),
                "by_latest_outcome": by_latest_outcome,
                "without_outcome": unreported,
            }

    # -- Sleep study results collection & provider review --------------
    # REFERENCE IMPLEMENTATION (re-judged from build-extension; see
    # BATCH.md): the entry's substance is the study data and test
    # results themselves -- clinical content, Extended by
    # construction in this category; the entry's own text records
    # that the substrate cannot hold it. No records form over
    # registry data collects a result the build may not hold, so
    # the honest in-substrate form is the reference registry: a
    # collection reference names a study only by an opaque
    # ``study_ref`` in the external system and carries a direction
    # and a reported record count -- never a payload, result,
    # finding, or waveform; and a review outcome records the
    # reviewer's outcome label verbatim, with ``decided_here`` and
    # ``interpreted_here`` False. Nothing is collected, held,
    # reviewed, or decided here.

    def record_collection_reference(self, participant_id, study_ref, actor,
                                    record_count=0, program_id=None,
                                    collected_on=None):
        """Record a reported results collection. Action: measurement_write.

        Carries the reported ``record_count`` of study records the
        external pipeline collected -- metadata only. The study
        data itself never enters this substrate
        (``content_held_here: False``, ``collected_here: False``).
        """
        self._guard(actor, "measurement_write",
                    "ext_collection_reference_record")
        _non_empty(study_ref, "study_ref")
        record_count = _count(record_count, "record_count")
        if collected_on is not None:
            _validate_date(collected_on, "collected_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            if program_id is not None:
                self._check_program(program_id, actor)
            record_id = self._next_id("col")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "program_id": program_id,
                "study_ref": study_ref,
                "record_count": record_count,
                "collected_on": collected_on,
                "reference_stub": True,
                "reference_transport": True,
                "content_held_here": False,
                "collected_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._collection_references[record_id] = record
            self._audit(actor, "ext_collection_reference_record", record_id,
                        details={"participant_id": participant_id,
                                 "study_ref": study_ref,
                                 "record_count": record_count})
            return dict(record)

    def record_review_outcome(self, collection_id, outcome_label, actor,
                              reviewed_on=None):
        """Record a provider review outcome. Action: plan_write.

        The outcome label is the reviewer's own, stored verbatim
        as reported; this build reviews nothing and decides
        nothing (``decided_here: False``,
        ``interpreted_here: False``).
        """
        self._guard(actor, "plan_write", "ext_review_outcome_record")
        _non_empty(outcome_label, "outcome_label")
        if reviewed_on is not None:
            _validate_date(reviewed_on, "reviewed_on")
        with self._lock:
            collection = self._get(self._collection_references, collection_id,
                                   "collection reference")
            record_id = self._next_id("rvw")
            record = {
                "id": record_id,
                "collection_id": collection_id,
                "participant_id": collection["participant_id"],
                "outcome_label": outcome_label,
                "reviewed_on": reviewed_on,
                "reference_stub": True,
                "decided_here": False,
                "interpreted_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._review_outcomes[record_id] = record
            self._audit(actor, "ext_review_outcome_record", record_id,
                        details={"collection_id": collection_id,
                                 "outcome_label": outcome_label})
            return dict(record)

    def _collection_view(self, collection):
        reviews = self._sorted(
            [r for r in self._review_outcomes.values()
             if r["collection_id"] == collection["id"]])
        view = dict(collection)
        view["review_count"] = len(reviews)
        view["latest_outcome_label"] = self._latest_label(
            reviews, "outcome_label")
        return view

    def get_collection_reference(self, collection_id, actor=None):
        """One collection reference with derived review state.

        Action: measurement_read (+ member scope).
        """
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            collection = self._get(self._collection_references, collection_id,
                                   "collection reference")
            self._scope_check_record(actor, collection)
            return self._collection_view(collection)

    def list_collection_references(self, actor=None, participant_id=None):
        """Return collection references with derived review state.

        Action: measurement_read (+ member scope).
        """
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            records = self._sorted(self._collection_references.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [self._collection_view(r)
                    for r in self._scoped(actor, records)]

    def list_review_outcomes(self, actor=None, collection_id=None):
        """Return review outcome records. Action: plan_read."""
        self._maybe_require(actor, "plan_read")
        with self._lock:
            records = self._sorted(self._review_outcomes.values())
            if collection_id is not None:
                records = [r for r in records
                           if r["collection_id"] == collection_id]
            return [dict(r) for r in self._scoped(actor, records)]

    def collection_summary(self, actor, participant_id=None):
        """Derived collection/review counts. Action: report_read (+ scope).

        Deterministic counts over held reference records only --
        ``method: deterministic_counts``. ``reported_records_total``
        is the sum of the collections' reported record counts,
        stated as a sum of reports; no study content is summed,
        because none is held. Never stored.
        """
        self._guard(actor, "report_read", "ext_collection_summary")
        with self._lock:
            if participant_id is not None:
                self._check_participant(participant_id, actor)
            collections = list(self._collection_references.values())
            reviews = list(self._review_outcomes.values())
            if participant_id is not None:
                collections = [c for c in collections
                               if c["participant_id"] == participant_id]
                reviews = [r for r in reviews
                           if r["participant_id"] == participant_id]
            collections = self._scoped(actor, collections)
            reviews = self._scoped(actor, reviews)
            by_outcome = {}
            for review in reviews:
                label = review["outcome_label"]
                by_outcome[label] = by_outcome.get(label, 0) + 1
            return {
                "participant_id": participant_id,
                "method": "deterministic_counts",
                "collections": len(collections),
                "reported_records_total": sum(
                    c["record_count"] for c in collections),
                "reviews": len(reviews),
                "by_outcome": by_outcome,
            }
