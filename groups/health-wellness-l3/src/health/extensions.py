"""Final GAPS batch extensions for Health & Wellness L3-adjacent
(Singleton 46).

Clean-room, standard-library-only extensions for the 5 open
entries of the Singleton 46 section (see ``BATCH.md`` in the group
directory for the per-entry disposition). This module is a wrapper
around :class:`HealthStore`; every core module is untouched and
byte-identical to the shipped group build.

**What this section is.** All five entries are the fork's own
clinical engines, named from its marketplace description: EEG
signal acquisition & streaming, EEG waveform review rendering,
continuous AI seizure monitoring & Seizure Burden quantification,
seizure detection & alerting, and bedside diagnostic support. The
group's UNION-SPEC and the GAPS.md section preamble state the
bound plainly: per this category's hard privacy rule these
engines **may not be built on this substrate**, and nothing in
this build performs or claims any diagnostic function. The three
stub-engine entries ship as labeled reference implementations, as
drafted; the two build-extension drafts (waveform review
rendering, bedside diagnostic support) are re-judged to reference
under DECISION.md qualification 1, with grounds in ``BATCH.md``:
rendering is a function over a waveform this substrate may never
hold, and diagnostic support is the diagnostic function itself --
neither has a records form that is the function's own substance
the way, at L2, a guideline citation plus a clinician's own label
was the substance of decision *records*. What lands here is the
registry of those engines' reported activity: session, report,
review, and outcome records against opaque references, every one
carrying ``reference_stub: True`` and state
``recorded_reference_only``.

**The category's HARD PRIVACY RULE binds absolutely, here as in
the core:** records and opaque caller-supplied references only.
No entity shape in this module has a name, contact, date-of-birth,
member-number, insurer, diagnosis, clinical-note, EEG-data,
waveform, or signal-content field -- those fields **do not
exist**. The one clinical figure that appears, a Seizure Burden
value, enters only as a number **recorded verbatim as reported**
by the external engine (``computed_here`` / ``quantified_here``
are False on the record); this build computes no clinical
quantity of any kind, applies no threshold, and interprets
nothing (``interpreted_here`` is False wherever an outcome is
recorded). Methods accept only their named parameters, so a
caller cannot smuggle a forbidden field into a record (pinned by
tests: an unexpected keyword raises ``TypeError``). This build
is **not a medical device and claims no FDA status**; the fork's
FDA clearance belongs to the fork's own product.

**High apparatus [L3] binds the extension surface**, as it binds
the core:

- Every extension mutation writes to the core store's
  **hash-chained** audit log (``ext_``-prefixed actions), so the
  chain covers extension activity and ``verify_chain()`` proves
  it; denied write attempts are recorded with a ``:denied``
  suffix.
- Extension writes are **fail-closed** (AU-5): each mutating
  method runs against a snapshot of the extension state, and an
  :class:`~health.errors.AuditWriteError` restores records and
  id counters in full before propagating -- an operation whose
  audit write fails does not proceed and consumes no id.
- The **auditor role holds ``audit_read`` only** (AC-5): it is
  denied every extension read and write (it holds none of the
  record actions), while its core audit duty -- reading and
  verifying the chain -- is untouched.
- RBAC uses the core's existing actions via
  :mod:`health.access`, enforced before any state change or id
  allocation; member scope mirrors the store's -- a member-role
  actor may only read records whose participant's
  ``participant_ref`` is their own name.

Derived-never-stored holds throughout: report counts, outcome
counts, and latest reported labels/values are computed at read
from the held records and never stored on them. Latest values
are **selections** of verbatim reported values, never
computations over them; summaries are deterministic counts only
(``method: deterministic_counts``) and aggregate no clinical
figure.
"""

import copy
import functools
import math
import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import (
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
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


def _reported_number(value, what):
    """A finite int/float as reported; booleans, strings, NaN and
    inf rejected. The value is held as data, never interpreted."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("%s must be a number" % (what,))
    if not math.isfinite(value):
        raise ValidationError("%s must be finite" % (what,))
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


def _fail_closed(method):
    """Wrap an extension mutation so an audit write failure rolls
    it back [L3] (AU-5, mirroring the core store's wrapper).

    The wrapped method runs against a snapshot of the extension
    state; if it raises :class:`AuditWriteError` (its audit entry
    could not be durably recorded on the hash-chained log), the
    snapshot is restored in full (records and id counters) and the
    error propagates.
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        snapshot = self._snapshot_state()
        try:
            return method(self, *args, **kwargs)
        except AuditWriteError:
            self._restore_state(snapshot)
            raise

    return wrapper


class HealthExtensions:
    """Extension surface wrapping one :class:`HealthStore`."""

    _TABLES = (
        "_stream_sessions", "_stream_reports",
        "_review_sessions", "_review_outcomes",
        "_monitoring_profiles", "_burden_reports",
        "_alert_references", "_alert_outcomes",
        "_diagnostic_sessions", "_diagnostic_outcomes",
    )

    def __init__(self, store):
        self.store = store
        self._stream_sessions = {}
        self._stream_reports = {}
        self._review_sessions = {}
        self._review_outcomes = {}
        self._monitoring_profiles = {}
        self._burden_reports = {}
        self._alert_references = {}
        self._alert_outcomes = {}
        self._diagnostic_sessions = {}
        self._diagnostic_outcomes = {}
        self._counters = {
            "sts": 0, "srp": 0, "rvw": 0, "rvo": 0, "mnp": 0,
            "bur": 0, "alr": 0, "alo": 0, "dgs": 0, "dgo": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _snapshot_state(self):
        return (
            {name: copy.deepcopy(getattr(self, name)) for name in self._TABLES},
            dict(self._counters),
        )

    def _restore_state(self, snapshot):
        tables, counters = snapshot
        for name, value in tables.items():
            setattr(self, name, value)
        self._counters = counters

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
        propagates; a missing actor is denied outright. At this
        tier the auditor role holds ``audit_read`` only, so it is
        denied here like any other role lacking the action.
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

    def _check_unique(self, table, field, value, what, participant_id=None):
        for existing in table.values():
            if existing[field] != value:
                continue
            if participant_id is not None and \
                    existing["participant_id"] != participant_id:
                continue
            raise ValidationError("%s %r is already registered" % (what, value))

    # -- EEG signal acquisition & real-time streaming pipeline --------
    # STUB-ENGINE, reference implementation (as drafted): a stream
    # session record names a bedside device by the caller's opaque
    # ``device_ref`` against a participant; a stream report records
    # a status label and a record count **as reported** by the
    # external acquisition pipeline. No signal is acquired, held,
    # or streamed here: ``signal_held_here`` / ``streamed_here``
    # are False on every session record, transport is labeled
    # (``reference_transport: True``), and no field in either shape
    # could hold EEG data.

    def _check_stream_device_unique(self, participant_id, device_ref):
        """Uniqueness seam for stream sessions.

        A device reference names one bedside device for one
        participant; a second stream session for the same
        participant + ``device_ref`` pair is refused, so a session
        record always names exactly one reported stream.
        MUTATION DRILL NOTE: neutralizing this check (making the
        refusal unreachable) is the batch unit's negative-control
        mutation; the suite's refusal tests then fail (see
        tests/README.md for the verified record).
        """
        for existing in self._stream_sessions.values():
            if (existing["participant_id"] == participant_id
                    and existing["device_ref"] == device_ref):
                raise ValidationError(
                    "device_ref %r already has a stream session for this "
                    "participant" % (device_ref,))

    @_fail_closed
    def create_stream_session(self, participant_id, device_ref, actor,
                              started_on=None):
        """Register an EEG stream session reference. Action: measurement_write."""
        self._guard(actor, "measurement_write", "ext_stream_session_create")
        _non_empty(device_ref, "device_ref")
        if started_on is not None:
            _validate_date(started_on, "started_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            self._check_stream_device_unique(participant_id, device_ref)
            record_id = self._next_id("sts")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "device_ref": device_ref,
                "started_on": started_on,
                "reference_stub": True,
                "reference_transport": True,
                "signal_held_here": False,
                "streamed_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._stream_sessions[record_id] = record
            self._audit(actor, "ext_stream_session_create", record_id,
                        details={"participant_id": participant_id,
                                 "device_ref": device_ref})
            return dict(record)

    @_fail_closed
    def record_stream_report(self, session_id, status_label, record_count,
                             actor, recorded_on=None):
        """Record a reported stream status. Action: measurement_write.

        Carries a status label and a record count as reported by
        the external pipeline -- never signal data.
        """
        self._guard(actor, "measurement_write", "ext_stream_report_record")
        _non_empty(status_label, "status_label")
        record_count = _count(record_count, "record_count")
        if recorded_on is not None:
            _validate_date(recorded_on, "recorded_on")
        with self._lock:
            session = self._get(self._stream_sessions, session_id,
                                "stream session")
            record_id = self._next_id("srp")
            record = {
                "id": record_id,
                "session_id": session_id,
                "participant_id": session["participant_id"],
                "status_label": status_label,
                "record_count": record_count,
                "recorded_on": recorded_on,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._stream_reports[record_id] = record
            self._audit(actor, "ext_stream_report_record", record_id,
                        details={"session_id": session_id,
                                 "status_label": status_label})
            return dict(record)

    def _stream_session_view(self, session):
        reports = self._sorted(
            [r for r in self._stream_reports.values()
             if r["session_id"] == session["id"]])
        view = dict(session)
        view["report_count"] = len(reports)
        view["latest_status_label"] = reports[-1]["status_label"] if reports else None
        return view

    def get_stream_session(self, session_id, actor=None):
        """One stream session with derived report state. Action: measurement_read."""
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            session = self._get(self._stream_sessions, session_id,
                                "stream session")
            self._scope_check_record(actor, session)
            return self._stream_session_view(session)

    def list_stream_sessions(self, actor=None, participant_id=None):
        """Return stream sessions with derived report state. Action: measurement_read."""
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            records = self._sorted(self._stream_sessions.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [self._stream_session_view(r)
                    for r in self._scoped(actor, records)]

    def list_stream_reports(self, actor=None, session_id=None):
        """Return stream reports, optionally filtered. Action: measurement_read."""
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            records = self._sorted(self._stream_reports.values())
            if session_id is not None:
                records = [r for r in records if r["session_id"] == session_id]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- EEG waveform review rendering (physician review surface) -----
    # RE-JUDGED build-extension -> reference (grounds in BATCH.md):
    # rendering is a function over the waveform itself, and this
    # substrate holds no clinical signal by constitutive rule, so
    # nothing here renders. The in-substrate form is the review's
    # registry: a review session record names the waveform only by
    # an opaque ``signal_ref`` held in the external review system,
    # and an outcome record holds the reviewer's outcome label
    # verbatim as reported (``rendered_here`` /
    # ``interpreted_here`` are False). Mirrors the L2 unit's
    # documentation-depth reasoning: the honest in-substrate form
    # of an artifact this build must not produce is its opaque
    # reference.

    @_fail_closed
    def record_review_session(self, participant_id, signal_ref, actor,
                              reviewed_on=None):
        """Register a waveform review session reference. Action: activity_write."""
        self._guard(actor, "activity_write", "ext_review_session_record")
        _non_empty(signal_ref, "signal_ref")
        if reviewed_on is not None:
            _validate_date(reviewed_on, "reviewed_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            self._check_unique(self._review_sessions, "signal_ref", signal_ref,
                               "signal_ref", participant_id=participant_id)
            record_id = self._next_id("rvw")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "signal_ref": signal_ref,
                "reviewed_on": reviewed_on,
                "reference_stub": True,
                "waveform_held_here": False,
                "rendered_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._review_sessions[record_id] = record
            self._audit(actor, "ext_review_session_record", record_id,
                        details={"participant_id": participant_id,
                                 "signal_ref": signal_ref})
            return dict(record)

    @_fail_closed
    def record_review_outcome(self, review_id, outcome_label, actor, decided_on):
        """Record a review outcome as reported. Action: plan_write.

        The label is the reviewer's own, stored verbatim; nothing
        is interpreted here (``interpreted_here`` is False).
        """
        self._guard(actor, "plan_write", "ext_review_outcome_record")
        _non_empty(outcome_label, "outcome_label")
        _validate_date(decided_on, "decided_on")
        with self._lock:
            review = self._get(self._review_sessions, review_id,
                               "review session")
            record_id = self._next_id("rvo")
            record = {
                "id": record_id,
                "review_id": review_id,
                "participant_id": review["participant_id"],
                "outcome_label": outcome_label,
                "decided_on": decided_on,
                "interpreted_here": False,
                "reference_stub": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._review_outcomes[record_id] = record
            self._audit(actor, "ext_review_outcome_record", record_id,
                        details={"review_id": review_id,
                                 "outcome_label": outcome_label})
            return dict(record)

    def _review_session_view(self, review):
        outcomes = self._sorted(
            [o for o in self._review_outcomes.values()
             if o["review_id"] == review["id"]])
        view = dict(review)
        view["outcome_count"] = len(outcomes)
        view["latest_outcome_label"] = \
            outcomes[-1]["outcome_label"] if outcomes else None
        return view

    def get_review_session(self, review_id, actor=None):
        """One review session with derived outcome state. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            review = self._get(self._review_sessions, review_id,
                              "review session")
            self._scope_check_record(actor, review)
            return self._review_session_view(review)

    def list_review_sessions(self, actor=None, participant_id=None):
        """Return review sessions with derived outcome state. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._review_sessions.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [self._review_session_view(r)
                    for r in self._scoped(actor, records)]

    def list_review_outcomes(self, actor=None, review_id=None):
        """Return review outcomes, optionally filtered. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._review_outcomes.values())
            if review_id is not None:
                records = [r for r in records if r["review_id"] == review_id]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Continuous AI seizure monitoring & Seizure Burden ------------
    # STUB-ENGINE, reference implementation (as drafted): a
    # monitoring profile record names the external model by an
    # opaque ``model_ref``; a burden report holds a Seizure Burden
    # figure **verbatim as reported** by that engine. No model is
    # trained, run, or inferred here (``inference_here`` /
    # ``monitoring_here`` are False), and the burden figure is
    # never computed, aggregated, thresholded, or interpreted by
    # this build (``computed_here`` / ``quantified_here`` are
    # False on the report; the profile view's
    # ``latest_reported_value`` is a verbatim selection of the
    # most recent report, not a computation; summaries count
    # reports and never touch the values).

    @_fail_closed
    def create_monitoring_profile(self, participant_id, model_ref, actor):
        """Register an AI monitoring profile reference. Action: measurement_write."""
        self._guard(actor, "measurement_write", "ext_monitoring_profile_create")
        _non_empty(model_ref, "model_ref")
        with self._lock:
            self._check_participant(participant_id, actor)
            self._check_unique(self._monitoring_profiles, "model_ref",
                               model_ref, "model_ref",
                               participant_id=participant_id)
            record_id = self._next_id("mnp")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "model_ref": model_ref,
                "reference_stub": True,
                "inference_here": False,
                "monitoring_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._monitoring_profiles[record_id] = record
            self._audit(actor, "ext_monitoring_profile_create", record_id,
                        details={"participant_id": participant_id,
                                 "model_ref": model_ref})
            return dict(record)

    @_fail_closed
    def record_burden_report(self, profile_id, burden_value, actor, reported_on):
        """Record a Seizure Burden figure as reported. Action: measurement_write.

        ``burden_value`` is the external engine's own output,
        stored verbatim as data under the profile's opaque
        references; this build quantifies nothing itself.
        """
        self._guard(actor, "measurement_write", "ext_burden_report_record")
        burden_value = _reported_number(burden_value, "burden_value")
        _validate_date(reported_on, "reported_on")
        with self._lock:
            profile = self._get(self._monitoring_profiles, profile_id,
                                "monitoring profile")
            record_id = self._next_id("bur")
            record = {
                "id": record_id,
                "profile_id": profile_id,
                "participant_id": profile["participant_id"],
                "burden_value": burden_value,
                "reported_on": reported_on,
                "computed_here": False,
                "quantified_here": False,
                "reference_stub": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._burden_reports[record_id] = record
            self._audit(actor, "ext_burden_report_record", record_id,
                        details={"profile_id": profile_id,
                                 "reported_on": reported_on})
            return dict(record)

    def _monitoring_profile_view(self, profile):
        reports = self._sorted(
            [r for r in self._burden_reports.values()
             if r["profile_id"] == profile["id"]])
        view = dict(profile)
        view["report_count"] = len(reports)
        view["latest_reported_value"] = \
            reports[-1]["burden_value"] if reports else None
        return view

    def get_monitoring_profile(self, profile_id, actor=None):
        """One monitoring profile with derived report state. Action: measurement_read."""
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            profile = self._get(self._monitoring_profiles, profile_id,
                                "monitoring profile")
            self._scope_check_record(actor, profile)
            return self._monitoring_profile_view(profile)

    def list_monitoring_profiles(self, actor=None, participant_id=None):
        """Return monitoring profiles with derived report state. Action: measurement_read."""
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            records = self._sorted(self._monitoring_profiles.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [self._monitoring_profile_view(r)
                    for r in self._scoped(actor, records)]

    def list_burden_reports(self, actor=None, profile_id=None):
        """Return burden reports, optionally filtered. Action: measurement_read."""
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            records = self._sorted(self._burden_reports.values())
            if profile_id is not None:
                records = [r for r in records if r["profile_id"] == profile_id]
            return [dict(r) for r in self._scoped(actor, records)]

    def monitoring_summary(self, participant_id, actor):
        """Derived monitoring counts for one participant.

        Action: report_read (+ member scope). Deterministic
        counts of held profile and report records only --
        ``method: deterministic_counts``. Burden values are never
        aggregated: no sum, mean, min, or max over them exists.
        """
        self._guard(actor, "report_read", "ext_monitoring_summary")
        with self._lock:
            participant = self._check_participant(participant_id, actor)
            if self._is_member(actor) and \
                    participant["participant_ref"] != getattr(actor, "name", None):
                raise PermissionDenied(
                    "permission denied: member %r may not access records of "
                    "another participant" % (getattr(actor, "name", None),))
            profiles = [p for p in self._monitoring_profiles.values()
                        if p["participant_id"] == participant_id]
            profile_ids = {p["id"] for p in profiles}
            reports = [r for r in self._burden_reports.values()
                       if r["profile_id"] in profile_ids]
            return {
                "participant_id": participant_id,
                "method": "deterministic_counts",
                "profiles": len(profiles),
                "burden_reports": len(reports),
            }

    # -- Seizure detection & alerting ----------------------------------
    # STUB-ENGINE, reference implementation (as drafted): an alert
    # reference record holds a detection label **verbatim as
    # reported** by the external detection engine, under an opaque
    # ``alert_ref``; an outcome record holds the alert's outcome
    # label as reported. Nothing is detected here and no one is
    # alerted: ``detected_here`` / ``alerted_here`` /
    # ``sent_here`` are False on every alert record, and delivery
    # is labeled transport (``reference_transport: True``) that
    # never happens in this substrate.

    @_fail_closed
    def record_alert_reference(self, participant_id, alert_ref,
                               detection_label, actor, recorded_on=None):
        """Record a reported seizure-detection alert. Action: activity_write."""
        self._guard(actor, "activity_write", "ext_alert_reference_record")
        _non_empty(alert_ref, "alert_ref")
        _non_empty(detection_label, "detection_label")
        if recorded_on is not None:
            _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            self._check_unique(self._alert_references, "alert_ref", alert_ref,
                               "alert_ref", participant_id=participant_id)
            record_id = self._next_id("alr")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "alert_ref": alert_ref,
                "detection_label": detection_label,
                "recorded_on": recorded_on,
                "reference_stub": True,
                "reference_transport": True,
                "detected_here": False,
                "alerted_here": False,
                "sent_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._alert_references[record_id] = record
            self._audit(actor, "ext_alert_reference_record", record_id,
                        details={"participant_id": participant_id,
                                 "alert_ref": alert_ref})
            return dict(record)

    @_fail_closed
    def record_alert_outcome(self, alert_id, outcome_label, actor,
                             decided_on=None):
        """Record an alert outcome as reported. Action: activity_write."""
        self._guard(actor, "activity_write", "ext_alert_outcome_record")
        _non_empty(outcome_label, "outcome_label")
        if decided_on is not None:
            _validate_date(decided_on, "decided_on")
        with self._lock:
            alert = self._get(self._alert_references, alert_id,
                              "alert reference")
            record_id = self._next_id("alo")
            record = {
                "id": record_id,
                "alert_id": alert_id,
                "participant_id": alert["participant_id"],
                "outcome_label": outcome_label,
                "decided_on": decided_on,
                "reference_stub": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._alert_outcomes[record_id] = record
            self._audit(actor, "ext_alert_outcome_record", record_id,
                        details={"alert_id": alert_id,
                                 "outcome_label": outcome_label})
            return dict(record)

    def _alert_reference_view(self, alert):
        outcomes = self._sorted(
            [o for o in self._alert_outcomes.values()
             if o["alert_id"] == alert["id"]])
        view = dict(alert)
        view["outcome_count"] = len(outcomes)
        view["latest_outcome_label"] = \
            outcomes[-1]["outcome_label"] if outcomes else None
        return view

    def get_alert_reference(self, alert_id, actor=None):
        """One alert reference with derived outcome state. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            alert = self._get(self._alert_references, alert_id,
                              "alert reference")
            self._scope_check_record(actor, alert)
            return self._alert_reference_view(alert)

    def list_alert_references(self, actor=None, participant_id=None):
        """Return alert references with derived outcome state. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._alert_references.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [self._alert_reference_view(r)
                    for r in self._scoped(actor, records)]

    def list_alert_outcomes(self, actor=None, alert_id=None):
        """Return alert outcomes, optionally filtered. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._alert_outcomes.values())
            if alert_id is not None:
                records = [r for r in records if r["alert_id"] == alert_id]
            return [dict(r) for r in self._scoped(actor, records)]

    def alert_summary(self, participant_id, actor):
        """Derived alert counts for one participant.

        Action: report_read (+ member scope). Deterministic
        counts of held alert and outcome records only --
        ``method: deterministic_counts``. Never stored.
        """
        self._guard(actor, "report_read", "ext_alert_summary")
        with self._lock:
            participant = self._check_participant(participant_id, actor)
            if self._is_member(actor) and \
                    participant["participant_ref"] != getattr(actor, "name", None):
                raise PermissionDenied(
                    "permission denied: member %r may not access records of "
                    "another participant" % (getattr(actor, "name", None),))
            alerts = [a for a in self._alert_references.values()
                      if a["participant_id"] == participant_id]
            alert_ids = {a["id"] for a in alerts}
            outcomes = [o for o in self._alert_outcomes.values()
                        if o["alert_id"] in alert_ids]
            return {
                "participant_id": participant_id,
                "method": "deterministic_counts",
                "alerts": len(alerts),
                "alert_outcomes": len(outcomes),
            }

    # -- Bedside diagnostic support ------------------------------------
    # RE-JUDGED build-extension -> reference (grounds in BATCH.md):
    # the entry names the diagnostic function itself, and this
    # build performs no diagnosis and claims none (UNION-SPEC).
    # The in-substrate form is a reference registry of the
    # external clinical system's reported activity: a session
    # record under an opaque ``session_ref``, and an outcome
    # record holding the outcome label verbatim as reported
    # (``diagnosed_here`` / ``support_rendered_here`` /
    # ``interpreted_here`` are False). No diagnostic content, no
    # finding, and no recommendation field exists in either shape.

    @_fail_closed
    def record_diagnostic_session(self, participant_id, session_ref, actor,
                                  recorded_on=None):
        """Register a bedside diagnostic session reference. Action: activity_write."""
        self._guard(actor, "activity_write", "ext_diagnostic_session_record")
        _non_empty(session_ref, "session_ref")
        if recorded_on is not None:
            _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            self._check_unique(self._diagnostic_sessions, "session_ref",
                               session_ref, "session_ref",
                               participant_id=participant_id)
            record_id = self._next_id("dgs")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "session_ref": session_ref,
                "recorded_on": recorded_on,
                "reference_stub": True,
                "diagnosed_here": False,
                "support_rendered_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._diagnostic_sessions[record_id] = record
            self._audit(actor, "ext_diagnostic_session_record", record_id,
                        details={"participant_id": participant_id,
                                 "session_ref": session_ref})
            return dict(record)

    @_fail_closed
    def record_diagnostic_outcome(self, session_id, outcome_label, actor,
                                  decided_on):
        """Record a diagnostic outcome as reported. Action: plan_write.

        The label is recorded verbatim as reported by the
        external clinical workflow; nothing is interpreted here
        (``interpreted_here`` is False) and no diagnosis is made.
        """
        self._guard(actor, "plan_write", "ext_diagnostic_outcome_record")
        _non_empty(outcome_label, "outcome_label")
        _validate_date(decided_on, "decided_on")
        with self._lock:
            session = self._get(self._diagnostic_sessions, session_id,
                                "diagnostic session")
            record_id = self._next_id("dgo")
            record = {
                "id": record_id,
                "session_id": session_id,
                "participant_id": session["participant_id"],
                "outcome_label": outcome_label,
                "decided_on": decided_on,
                "interpreted_here": False,
                "reference_stub": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._diagnostic_outcomes[record_id] = record
            self._audit(actor, "ext_diagnostic_outcome_record", record_id,
                        details={"session_id": session_id,
                                 "outcome_label": outcome_label})
            return dict(record)

    def _diagnostic_session_view(self, session):
        outcomes = self._sorted(
            [o for o in self._diagnostic_outcomes.values()
             if o["session_id"] == session["id"]])
        view = dict(session)
        view["outcome_count"] = len(outcomes)
        view["latest_outcome_label"] = \
            outcomes[-1]["outcome_label"] if outcomes else None
        return view

    def get_diagnostic_session(self, session_id, actor=None):
        """One diagnostic session with derived outcome state. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            session = self._get(self._diagnostic_sessions, session_id,
                                "diagnostic session")
            self._scope_check_record(actor, session)
            return self._diagnostic_session_view(session)

    def list_diagnostic_sessions(self, actor=None, participant_id=None):
        """Return diagnostic sessions with derived outcome state. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._diagnostic_sessions.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [self._diagnostic_session_view(r)
                    for r in self._scoped(actor, records)]

    def list_diagnostic_outcomes(self, actor=None, session_id=None):
        """Return diagnostic outcomes, optionally filtered. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._diagnostic_outcomes.values())
            if session_id is not None:
                records = [r for r in records if r["session_id"] == session_id]
            return [dict(r) for r in self._scoped(actor, records)]
