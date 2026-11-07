"""Final GAPS batch extensions — Untiered Set 27 (Media).

Records-form implementations and labeled reference implementations
for the five open Extended families of this set's union spec,
built over the founding Media substrate in :mod:`media.store`.
This module is the only code the batch adds; every core module is
unchanged.

Tier discipline: this set is untiered and this module keeps it
that way. No record, view, or summary in this module carries a
tier, a baseline, an impact level, or a CMMC equivalence key or
value; tier stays null, exactly as the set's spec sheet records
it. Nothing here computes a score, a rating, a quality metric, or
a latency figure — the founding build's disciplines bind the
extension whole: records about media, never media; no record
shape has a field that could hold video, audio, a stream payload,
or a file.

Honesty labels, per family:

- **Live video transport & routing engine** (idx 960) ships as a
  **labeled reference implementation**: transport run records
  naming a core route (and optionally one of its core sessions)
  plus outcome records holding the transport service's reported
  outcome labels verbatim. Every record carries
  ``reference_stub: True`` and ``reference_transport: True``;
  nothing is transported here (``transported_here: False``), and
  recording a run starts no session and changes no route.
- **Stream encryption implementation** (idx 961) ships as a
  **labeled reference implementation**: encryption reference
  records naming a core route and holding the mechanism label
  verbatim as the fork documents it (e.g. "AES-256"), plus
  reported status records. This build performs no cryptography
  of any kind and holds no key material
  (``cryptography_performed_here: False``,
  ``encrypted_here: False``); a reference record snapshots the
  route's caller-stated encryption label as a recorded value and
  never changes it — pinned by test.
- **Device control channel** (idx 962) is built in its records
  form: dispatch records bound one-to-one to core control-action
  records (a second dispatch of the same action is refused), and
  delivery outcome records holding the channel's reported
  outcome labels verbatim. Dispatches are the records layer over
  the core's control registry: every record carries
  ``reference_transport: True`` and nothing is sent to any device
  (``sent_here: False``, ``delivered_here: False``) — the entry's
  own text bounds it: control actions are recorded, never sent.
  Per-device counts are derived at read, never stored.
- **Stream optimization engine** (idx 963) is built in its
  records form, on the CMS set's personalization precedent:
  assignment records binding a core optimization profile to a
  core route of the same organization, outcome records holding
  reported outcome labels verbatim, and a route view derived at
  read (assignment counts, the recorded profile ids, and the
  enabled count joined from the core profiles' recorded flags).
  No stream is adapted and no profile is applied by this build
  (``applied_here: False``, ``adapted_here: False``,
  ``optimized_here: False``); what is built is the
  records-and-derivation layer the engine's operation would be
  recorded through, and that bound is stated, not smoothed over.
- **Status & monitoring telemetry collection** (idx 964) ships
  as a **labeled reference implementation**: collection source
  records naming a core route or device subject and a probe
  label held as data, plus collection outcome records holding
  reported outcome labels and reported snapshot counts exactly
  as reported. No probe runs here (``collected_here: False``),
  and recording a collection reference creates no core status
  snapshot — pinned by test. A view's total is the sum of the
  *reported* counts over the recorded outcomes, derived at read;
  it counts reports, not measurements taken here.

Access control reuses the founding permission matrix — no new
actions exist. The mapping is: transport runs and encryption
references use ``routes``; control dispatches use ``control``;
optimization assignments use ``optimize``; telemetry collection
references use ``monitor``; all reads and the summary use
``read``. Enforcement mirrors the core store's ``_check_role``:
a User-like actor is checked against the matrix and denials are
recorded in the core audit log under a ``:denied`` suffix; a
plain string actor carries identity without a role, as in the
core.

Ids are sequential per object type with fixed prefixes
(``trn-``, ``tro-``, ``enc-``, ``enr-``, ``dsp-``, ``dlo-``,
``asn-``, ``oto-``, ``col-``, ``crn-``). A failed operation
consumes no id and changes nothing: all validation happens
before any mutation. All timestamps are UTC ISO-8601. Records
returned are copies; mutating a returned record changes nothing
stored.

The single derivation seam for "latest reported label" views is
:meth:`MediaExtensions._latest_label`: the label of the most
recently **recorded** record in a list, in this register's
recording order. It is the seam the batch's fresh negative
control mutates (see tests/README.md).
"""

import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import SUBJECT_KINDS

__all__ = ["MediaExtensions"]


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _optional_text(value, field):
    if value is None:
        return None
    return _text(value, field)


def _reported_count(value, field):
    """A count reported by an external system, stored exactly as
    reported. Must be a non-negative integer; booleans and floats
    are refused, as everywhere in this substrate."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(
            "%s must be a non-negative integer or None" % field)
    return value


class MediaExtensions:
    """Extension register wrapping a core :class:`media.store.MediaStore`."""

    def __init__(self, store):
        self.store = store
        self.audit = getattr(store, "audit", None)
        self._transport_runs = {}
        self._transport_outcomes = {}
        self._encryption_refs = {}
        self._encryption_statuses = {}
        self._dispatches = {}
        self._delivery_outcomes = {}
        self._assignments = {}
        self._optimization_outcomes = {}
        self._collection_sources = {}
        self._collection_outcomes = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers -------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor, action, target, details)

    def _require(self, actor, action, audit_action, target=None):
        """Write/read enforcement, mirroring the core store's
        ``_check_role``: User-like actors are checked against the
        founding matrix; denials are audited with a ``:denied``
        suffix before the error propagates."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit(actor, "%s:denied" % audit_action, target)
                raise

    def _get(self, collection, obj_id, what):
        record = collection.get(obj_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, obj_id))
        return record

    @staticmethod
    def _latest_label(records, key):
        """Latest-label derivation seam: the value of ``key`` on
        the most recently recorded record in ``records`` (this
        register's recording order), or None when the list is
        empty. Derived at read; nothing about it is stored."""
        return records[-1][key] if records else None

    # -- core lookups (existence + binding checks) -------------------

    def _core_route(self, actor, route_id):
        return self.store.get_route(actor, route_id)

    def _core_session(self, actor, session_id):
        return self.store.get_session(actor, session_id)

    def _core_device(self, actor, device_id):
        return self.store.get_device(actor, device_id)

    def _core_control_action(self, actor, control_action_id):
        for action in self.store.list_control_actions(actor):
            if action["id"] == control_action_id:
                return action
        raise NotFoundError(
            "control action not found: %r" % (control_action_id,))

    def _core_profile(self, actor, profile_id):
        for profile in self.store.list_profiles(actor):
            if profile["id"] == profile_id:
                return profile
        raise NotFoundError(
            "optimization profile not found: %r" % (profile_id,))

    def _core_subject(self, actor, subject_kind, subject_id):
        if subject_kind == "route":
            return self.store.get_route(actor, subject_id)
        return self.store.get_device(actor, subject_id)

    # ================================================================
    # Live video transport & routing engine (idx 960) — reference
    # ================================================================

    def record_transport_run(self, actor, route_id, session_id=None,
                             note=None):
        """Record one transport run of the external routing
        engine over a core route.

        Action: routes. Id prefix: trn-. Reference
        implementation: the run names the route (and optionally
        one of the route's core sessions) whose transport it
        reports on; the transport itself happens in the fork's
        network, not here (``transported_here: False``).
        Recording a run starts no session and changes no route.
        """
        self._require(actor, "routes", "ext_transport_run_record",
                      target=route_id)
        _optional_text(note, "note")
        with self._lock:
            self._core_route(actor, route_id)
            if session_id is not None:
                session = self._core_session(actor, session_id)
                if session["route_id"] != route_id:
                    raise ValidationError(
                        "session %r does not belong to route %r"
                        % (session_id, route_id))
            record = {
                "id": self._next_id("trn"),
                "route_id": route_id,
                "session_id": session_id,
                "note": note,
                "reference_stub": True,
                "reference_transport": True,
                "transported_here": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._transport_runs[record["id"]] = record
        self._audit(actor, "ext_transport_run_record", record["id"],
                    {"route_id": route_id})
        return dict(record)

    def record_transport_outcome(self, actor, run_id, outcome_label,
                                 detail=None):
        """Record a transport outcome, verbatim as reported.

        Action: routes. Id prefix: tro-. The label is the
        external engine's own report; nothing was transported
        here (``transported_here: False``).
        """
        self._require(actor, "routes", "ext_transport_outcome_record",
                      target=run_id)
        _text(outcome_label, "outcome_label")
        _optional_text(detail, "detail")
        with self._lock:
            self._get(self._transport_runs, run_id, "transport run")
            record = {
                "id": self._next_id("tro"),
                "run_id": run_id,
                "outcome_label": outcome_label,
                "detail": detail,
                "reference_stub": True,
                "reference_transport": True,
                "transported_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._transport_outcomes[record["id"]] = record
        self._audit(actor, "ext_transport_outcome_record", record["id"],
                    {"run_id": run_id})
        return dict(record)

    def get_transport_run(self, run_id, actor=None):
        """One transport run record. Action: read."""
        self._require(actor, "read", "ext_transport_run_read",
                      target=run_id)
        return dict(self._get(self._transport_runs, run_id,
                              "transport run"))

    def list_transport_runs(self, actor=None, route_id=None):
        """Transport run records, optionally for one route.
        Action: read."""
        self._require(actor, "read", "ext_transport_run_read")
        return [dict(r) for r in self._transport_runs.values()
                if route_id is None or r["route_id"] == route_id]

    def list_transport_outcomes(self, run_id, actor=None):
        """Outcome records for one transport run. Action: read."""
        self._require(actor, "read", "ext_transport_outcome_read",
                      target=run_id)
        with self._lock:
            self._get(self._transport_runs, run_id, "transport run")
            return [dict(o) for o in self._transport_outcomes.values()
                    if o["run_id"] == run_id]

    def transport_view(self, run_id, actor=None):
        """A transport run with its derived outcome summary:
        outcome count and the latest reported outcome label,
        derived at read. Action: read."""
        self._require(actor, "read", "ext_transport_run_read",
                      target=run_id)
        with self._lock:
            run = self._get(self._transport_runs, run_id,
                            "transport run")
            outcomes = [o for o in self._transport_outcomes.values()
                        if o["run_id"] == run_id]
            view = dict(run)
            view["outcome_count"] = len(outcomes)
            view["latest_outcome_label"] = self._latest_label(
                outcomes, "outcome_label")
            view["derived"] = True
            return view

    # ================================================================
    # Stream encryption implementation (idx 961) — reference
    # ================================================================

    def record_encryption_reference(self, actor, route_id,
                                    mechanism_label, note=None):
        """Record an encryption reference for a core route.

        Action: routes. Id prefix: enc-. Reference
        implementation: ``mechanism_label`` is the mechanism as
        the fork documents it (e.g. "AES-256"), held verbatim as
        data. The record snapshots the route's caller-stated
        encryption label — a recorded value — and never changes
        it. No cryptography is performed and no key material is
        held (``cryptography_performed_here: False``,
        ``encrypted_here: False``).
        """
        self._require(actor, "routes", "ext_encryption_reference_record",
                      target=route_id)
        _text(mechanism_label, "mechanism_label")
        _optional_text(note, "note")
        with self._lock:
            route = self._core_route(actor, route_id)
            record = {
                "id": self._next_id("enc"),
                "route_id": route_id,
                "mechanism_label": mechanism_label,
                "route_encryption_label": route["encryption"],
                "note": note,
                "reference_stub": True,
                "cryptography_performed_here": False,
                "encrypted_here": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._encryption_refs[record["id"]] = record
        self._audit(actor, "ext_encryption_reference_record",
                    record["id"], {"route_id": route_id})
        return dict(record)

    def record_encryption_status(self, actor, reference_id,
                                 status_label):
        """Record an encryption status report, verbatim as
        reported (e.g. a key-lifecycle report from the external
        implementation).

        Action: routes. Id prefix: enr-. The status is the
        external implementation's report; no key operation
        happens here.
        """
        self._require(actor, "routes", "ext_encryption_status_record",
                      target=reference_id)
        _text(status_label, "status_label")
        with self._lock:
            self._get(self._encryption_refs, reference_id,
                      "encryption reference")
            record = {
                "id": self._next_id("enr"),
                "reference_id": reference_id,
                "status_label": status_label,
                "reference_stub": True,
                "cryptography_performed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._encryption_statuses[record["id"]] = record
        self._audit(actor, "ext_encryption_status_record", record["id"],
                    {"reference_id": reference_id})
        return dict(record)

    def get_encryption_reference(self, reference_id, actor=None):
        """One encryption reference record. Action: read."""
        self._require(actor, "read", "ext_encryption_reference_read",
                      target=reference_id)
        return dict(self._get(self._encryption_refs, reference_id,
                              "encryption reference"))

    def list_encryption_references(self, actor=None, route_id=None):
        """Encryption reference records, optionally for one
        route. Action: read."""
        self._require(actor, "read", "ext_encryption_reference_read")
        return [dict(r) for r in self._encryption_refs.values()
                if route_id is None or r["route_id"] == route_id]

    def list_encryption_statuses(self, reference_id, actor=None):
        """Status records for one encryption reference.
        Action: read."""
        self._require(actor, "read", "ext_encryption_status_read",
                      target=reference_id)
        with self._lock:
            self._get(self._encryption_refs, reference_id,
                      "encryption reference")
            return [dict(s) for s in self._encryption_statuses.values()
                    if s["reference_id"] == reference_id]

    def encryption_view(self, reference_id, actor=None):
        """An encryption reference with its derived status
        summary: status count and the latest reported status
        label, derived at read. Action: read."""
        self._require(actor, "read", "ext_encryption_reference_read",
                      target=reference_id)
        with self._lock:
            reference = self._get(self._encryption_refs, reference_id,
                                  "encryption reference")
            statuses = [s for s in self._encryption_statuses.values()
                        if s["reference_id"] == reference_id]
            view = dict(reference)
            view["status_count"] = len(statuses)
            view["latest_status_label"] = self._latest_label(
                statuses, "status_label")
            view["derived"] = True
            return view

    # ================================================================
    # Device control channel (idx 962) — built, records form
    # ================================================================

    def record_control_dispatch(self, actor, control_action_id):
        """Record the dispatch of one core control action
        through the control channel.

        Action: control. Id prefix: dsp-. The dispatch binds
        one-to-one to a core control-action record — a second
        dispatch of the same action is refused and consumes no
        id. The record names the action and its device as the
        core recorded them; the channel's delivery happens
        outside this build (``sent_here: False``).
        """
        self._require(actor, "control", "ext_control_dispatch_record",
                      target=control_action_id)
        with self._lock:
            action_record = self._core_control_action(
                actor, control_action_id)
            for existing in self._dispatches.values():
                if existing["control_action_id"] == control_action_id:
                    raise ValidationError(
                        "control action %r already has a dispatch "
                        "record (%s)"
                        % (control_action_id, existing["id"]))
            record = {
                "id": self._next_id("dsp"),
                "control_action_id": control_action_id,
                "device_id": action_record["device_id"],
                "action": action_record["action"],
                "reference_transport": True,
                "sent_here": False,
                "delivered_here": False,
                "state": "recorded_dispatch_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._dispatches[record["id"]] = record
        self._audit(actor, "ext_control_dispatch_record", record["id"],
                    {"control_action_id": control_action_id})
        return dict(record)

    def record_delivery_outcome(self, actor, dispatch_id,
                                outcome_label, detail=None):
        """Record a delivery outcome for a dispatch, verbatim as
        reported by the channel.

        Action: control. Id prefix: dlo-. The label is the
        channel's own report; nothing was delivered by this
        build (``delivered_here: False``).
        """
        self._require(actor, "control", "ext_delivery_outcome_record",
                      target=dispatch_id)
        _text(outcome_label, "outcome_label")
        _optional_text(detail, "detail")
        with self._lock:
            self._get(self._dispatches, dispatch_id, "dispatch")
            record = {
                "id": self._next_id("dlo"),
                "dispatch_id": dispatch_id,
                "outcome_label": outcome_label,
                "detail": detail,
                "reference_transport": True,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._delivery_outcomes[record["id"]] = record
        self._audit(actor, "ext_delivery_outcome_record", record["id"],
                    {"dispatch_id": dispatch_id})
        return dict(record)

    def get_dispatch(self, dispatch_id, actor=None):
        """One dispatch record. Action: read."""
        self._require(actor, "read", "ext_control_dispatch_read",
                      target=dispatch_id)
        return dict(self._get(self._dispatches, dispatch_id,
                              "dispatch"))

    def list_dispatches(self, actor=None, device_id=None):
        """Dispatch records, optionally for one device.
        Action: read."""
        self._require(actor, "read", "ext_control_dispatch_read")
        return [dict(d) for d in self._dispatches.values()
                if device_id is None or d["device_id"] == device_id]

    def list_delivery_outcomes(self, dispatch_id, actor=None):
        """Delivery outcome records for one dispatch.
        Action: read."""
        self._require(actor, "read", "ext_delivery_outcome_read",
                      target=dispatch_id)
        with self._lock:
            self._get(self._dispatches, dispatch_id, "dispatch")
            return [dict(o) for o in self._delivery_outcomes.values()
                    if o["dispatch_id"] == dispatch_id]

    def device_dispatch_view(self, device_id, actor=None):
        """A device's dispatch picture, derived at read: the
        dispatch count, the count of outcome records by reported
        label, the count of dispatches with no outcome recorded,
        and the latest reported outcome label. Counts over
        recorded values only; nothing is stored. Action: read.
        """
        self._require(actor, "read", "ext_control_dispatch_read",
                      target=device_id)
        with self._lock:
            self._core_device(actor, device_id)
            dispatches = [d for d in self._dispatches.values()
                          if d["device_id"] == device_id]
            dispatch_ids = {d["id"] for d in dispatches}
            outcomes = [o for o in self._delivery_outcomes.values()
                        if o["dispatch_id"] in dispatch_ids]
            by_label = {}
            for outcome in outcomes:
                label = outcome["outcome_label"]
                by_label[label] = by_label.get(label, 0) + 1
            reported = {o["dispatch_id"] for o in outcomes}
            return {
                "device_id": device_id,
                "dispatch_count": len(dispatches),
                "outcome_count": len(outcomes),
                "outcomes_by_label": by_label,
                "dispatches_without_outcome": sum(
                    1 for d in dispatches if d["id"] not in reported),
                "latest_outcome_label": self._latest_label(
                    outcomes, "outcome_label"),
                "derived": True,
            }

    # ================================================================
    # Stream optimization engine (idx 963) — built, records form
    # ================================================================

    def record_optimization_assignment(self, actor, profile_id,
                                       route_id):
        """Record the assignment of a core optimization profile
        to a core route.

        Action: optimize. Id prefix: asn-. The profile and the
        route must belong to the same organization (the core's
        own rule for profile-route binding); a second assignment
        of the same profile to the same route is refused and
        consumes no id. The assignment is a record: no profile
        is applied to any stream by this build
        (``applied_here: False``).
        """
        self._require(actor, "optimize",
                      "ext_optimization_assignment_record",
                      target=route_id)
        with self._lock:
            profile = self._core_profile(actor, profile_id)
            route = self._core_route(actor, route_id)
            if profile["org_id"] != route["org_id"]:
                raise ValidationError(
                    "profile %r and route %r belong to different "
                    "organizations" % (profile_id, route_id))
            for existing in self._assignments.values():
                if (existing["profile_id"] == profile_id
                        and existing["route_id"] == route_id):
                    raise ValidationError(
                        "profile %r is already assigned to route "
                        "%r (%s)"
                        % (profile_id, route_id, existing["id"]))
            record = {
                "id": self._next_id("asn"),
                "profile_id": profile_id,
                "route_id": route_id,
                "org_id": route["org_id"],
                "applied_here": False,
                "adapted_here": False,
                "optimized_here": False,
                "state": "recorded_assignment_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assignments[record["id"]] = record
        self._audit(actor, "ext_optimization_assignment_record",
                    record["id"],
                    {"profile_id": profile_id, "route_id": route_id})
        return dict(record)

    def record_optimization_outcome(self, actor, assignment_id,
                                    outcome_label, detail=None):
        """Record an optimization outcome for an assignment,
        verbatim as reported by the external engine.

        Action: optimize. Id prefix: oto-. The label is the
        engine's own report; no figure is computed or stored
        here and no stream was adapted by this build
        (``optimized_here: False``).
        """
        self._require(actor, "optimize",
                      "ext_optimization_outcome_record",
                      target=assignment_id)
        _text(outcome_label, "outcome_label")
        _optional_text(detail, "detail")
        with self._lock:
            self._get(self._assignments, assignment_id, "assignment")
            record = {
                "id": self._next_id("oto"),
                "assignment_id": assignment_id,
                "outcome_label": outcome_label,
                "detail": detail,
                "applied_here": False,
                "optimized_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._optimization_outcomes[record["id"]] = record
        self._audit(actor, "ext_optimization_outcome_record",
                    record["id"], {"assignment_id": assignment_id})
        return dict(record)

    def get_assignment(self, assignment_id, actor=None):
        """One assignment record. Action: read."""
        self._require(actor, "read", "ext_optimization_assignment_read",
                      target=assignment_id)
        return dict(self._get(self._assignments, assignment_id,
                              "assignment"))

    def list_assignments(self, actor=None, route_id=None):
        """Assignment records, optionally for one route.
        Action: read."""
        self._require(actor, "read", "ext_optimization_assignment_read")
        return [dict(a) for a in self._assignments.values()
                if route_id is None or a["route_id"] == route_id]

    def list_optimization_outcomes(self, assignment_id, actor=None):
        """Outcome records for one assignment. Action: read."""
        self._require(actor, "read", "ext_optimization_outcome_read",
                      target=assignment_id)
        with self._lock:
            self._get(self._assignments, assignment_id, "assignment")
            return [dict(o)
                    for o in self._optimization_outcomes.values()
                    if o["assignment_id"] == assignment_id]

    def route_optimization_view(self, route_id, actor=None):
        """A route's optimization picture, derived at read: the
        assignment count, the recorded profile ids in recording
        order, how many of those profiles are currently recorded
        enabled in the core registry (a join over recorded
        values), the outcome count over the route's assignments,
        and the latest reported outcome label. Nothing is
        stored; no stream figure of any kind is computed.
        Action: read.
        """
        self._require(actor, "read", "ext_optimization_assignment_read",
                      target=route_id)
        with self._lock:
            self._core_route(actor, route_id)
            assignments = [a for a in self._assignments.values()
                           if a["route_id"] == route_id]
            assignment_ids = {a["id"] for a in assignments}
            outcomes = [o
                        for o in self._optimization_outcomes.values()
                        if o["assignment_id"] in assignment_ids]
            enabled = 0
            for assignment in assignments:
                profile = self._core_profile(actor,
                                             assignment["profile_id"])
                if profile["enabled"]:
                    enabled += 1
            return {
                "route_id": route_id,
                "assignment_count": len(assignments),
                "assigned_profile_ids": [a["profile_id"]
                                         for a in assignments],
                "assigned_profiles_enabled": enabled,
                "outcome_count": len(outcomes),
                "latest_outcome_label": self._latest_label(
                    outcomes, "outcome_label"),
                "derived": True,
            }

    # ================================================================
    # Status & monitoring telemetry collection (idx 964) — reference
    # ================================================================

    def record_collection_source(self, actor, subject_kind,
                                 subject_id, probe_label):
        """Record a telemetry collection source for a core route
        or device subject.

        Action: monitor. Id prefix: col-. Reference
        implementation: ``probe_label`` names the external probe
        as data; the probe itself runs in the fork's operation,
        not here (``collected_here: False``). Recording a source
        creates no core status snapshot.
        """
        self._require(actor, "monitor", "ext_collection_source_record",
                      target=subject_id)
        if subject_kind not in SUBJECT_KINDS:
            raise ValidationError(
                "subject_kind must be one of %r" % (SUBJECT_KINDS,))
        _text(probe_label, "probe_label")
        with self._lock:
            self._core_subject(actor, subject_kind, subject_id)
            record = {
                "id": self._next_id("col"),
                "subject_kind": subject_kind,
                "subject_id": subject_id,
                "probe_label": probe_label,
                "reference_stub": True,
                "collected_here": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._collection_sources[record["id"]] = record
        self._audit(actor, "ext_collection_source_record", record["id"],
                    {"subject_kind": subject_kind,
                     "subject_id": subject_id})
        return dict(record)

    def record_collection_outcome(self, actor, source_id,
                                  outcome_label,
                                  reported_snapshot_count=None):
        """Record a collection outcome, verbatim as reported.

        Action: monitor. Id prefix: crn-.
        ``reported_snapshot_count`` is the collector's own
        reported count, stored exactly as reported; it is a
        record of a report, not a measurement taken here
        (``collected_here: False``).
        """
        self._require(actor, "monitor", "ext_collection_outcome_record",
                      target=source_id)
        _text(outcome_label, "outcome_label")
        reported = _reported_count(reported_snapshot_count,
                                   "reported_snapshot_count")
        with self._lock:
            self._get(self._collection_sources, source_id,
                      "collection source")
            record = {
                "id": self._next_id("crn"),
                "source_id": source_id,
                "outcome_label": outcome_label,
                "reported_snapshot_count": reported,
                "reference_stub": True,
                "collected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._collection_outcomes[record["id"]] = record
        self._audit(actor, "ext_collection_outcome_record", record["id"],
                    {"source_id": source_id})
        return dict(record)

    def get_collection_source(self, source_id, actor=None):
        """One collection source record. Action: read."""
        self._require(actor, "read", "ext_collection_source_read",
                      target=source_id)
        return dict(self._get(self._collection_sources, source_id,
                              "collection source"))

    def list_collection_sources(self, actor=None, subject_kind=None,
                                subject_id=None):
        """Collection source records, optionally filtered.
        Action: read."""
        self._require(actor, "read", "ext_collection_source_read")
        if subject_kind is not None and subject_kind not in SUBJECT_KINDS:
            raise ValidationError(
                "subject_kind must be one of %r" % (SUBJECT_KINDS,))
        return [dict(s) for s in self._collection_sources.values()
                if (subject_kind is None
                    or s["subject_kind"] == subject_kind)
                and (subject_id is None
                     or s["subject_id"] == subject_id)]

    def list_collection_outcomes(self, source_id, actor=None):
        """Outcome records for one collection source.
        Action: read."""
        self._require(actor, "read", "ext_collection_outcome_read",
                      target=source_id)
        with self._lock:
            self._get(self._collection_sources, source_id,
                      "collection source")
            return [dict(o) for o in self._collection_outcomes.values()
                    if o["source_id"] == source_id]

    def collection_view(self, source_id, actor=None):
        """A collection source with its derived outcome summary:
        outcome count, the total of the *reported* snapshot
        counts over its recorded outcomes (a sum of reports,
        derived at read — not a measurement), and the latest
        reported outcome label. Action: read."""
        self._require(actor, "read", "ext_collection_source_read",
                      target=source_id)
        with self._lock:
            source = self._get(self._collection_sources, source_id,
                               "collection source")
            outcomes = [o for o in self._collection_outcomes.values()
                        if o["source_id"] == source_id]
            view = dict(source)
            view["outcome_count"] = len(outcomes)
            view["total_reported_snapshots"] = sum(
                o["reported_snapshot_count"] or 0 for o in outcomes)
            view["latest_outcome_label"] = self._latest_label(
                outcomes, "outcome_label")
            view["derived"] = True
            return view

    # ================================================================
    # Extension summary — counts only, derived at read
    # ================================================================

    def extension_summary(self, actor=None):
        """Counts over the extension register, derived at read.
        Counts and recorded values only: no score, no rate, no
        latency figure, and no tier or baseline key of any kind.
        Action: read.
        """
        self._require(actor, "read", "ext_summary_read")
        with self._lock:
            return {
                "transport_runs": len(self._transport_runs),
                "transport_outcomes": len(self._transport_outcomes),
                "encryption_references": len(self._encryption_refs),
                "encryption_statuses": len(self._encryption_statuses),
                "control_dispatches": len(self._dispatches),
                "delivery_outcomes": len(self._delivery_outcomes),
                "optimization_assignments": len(self._assignments),
                "optimization_outcomes":
                    len(self._optimization_outcomes),
                "collection_sources": len(self._collection_sources),
                "collection_outcomes": len(self._collection_outcomes),
            }
