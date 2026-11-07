"""Final GAPS batch extensions for Talent Management L2.

Clean-room, standard-library-only records/derivation extensions for
the 7 open Extended entries of this group's union spec (the eighth,
identity provider / candidate identity verification, was closed
``re-scoped`` under PLATFORM-LAYER.md decision 1 before this unit).
2 entries ship as labeled reference implementations and 5 are built
as in-substrate records plus deterministic derivations over the
core's own records. See ``BATCH.md`` in the group directory for the
per-entry disposition and the adjudication notes.

Design, following the core's doctrines and this group's Moderate
baseline:

- This module is a wrapper around :class:`TalentMgmtStore`; the
  core modules are untouched (byte-identical). Candidate,
  assessment, interview, event, registration, workflow, and
  organization existence are always read through the core store's
  public API, never re-implemented -- so the core's membership
  boundary and role matrix bind every extension operation exactly
  as they bind the core's own.
- RBAC goes through :mod:`talentmgmt.access` exactly as the core
  enforces it: the extension maps each of its operations onto an
  existing core action (the core action set is fixed), checks it
  *before* any state change or id allocation for User-like actors,
  and records denied attempts on the core audit log with the
  extension action name suffixed ``:denied``. Plain-string actors
  carry identity but no role, mirroring the core convention.
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``.
- **Privacy is structural, exactly as in the core.** Every person
  is an opaque ``candidate_ref`` validated against the core
  candidate registry. No record shape in this module can hold a
  real person's name, contact detail, or identifier, a resume,
  assessment content or responses, interview media or a
  transcript, or development content -- there is no parameter
  that could accept one (pinned by TypeError tests).
- **No score is computed anywhere, exactly as in the core.** No
  record shape carries a score, rating, ranking, or match value,
  and no key anywhere in the surface contains one of those words
  (the counts-only scan forbids the word itself, so the
  computation boundary is carried as ``computed_here``).
  Predictions, delivery outcomes, automation outcomes, attendance
  figures, and ROI figures are caller-reported labels or counts
  recorded verbatim; inference, grading, matching, and ROI
  determination are never performed here.
- Derived values are derived at read and never stored: the
  analytics snapshot (deterministic counts over the core registry
  report plus the extension's own records) and development
  progress (from module-milestone check-off records). Stored
  records carry no derived key; tests pin that. Lifecycle
  statuses on reference records (declared -> reported, requested
  -> reported, recorded -> reported) are guarded transitions,
  stored, exactly as the core stores its lifecycles.
- The development module-bounds check lives at a single named
  seam (``_check_development_module_bounds``): a milestone's
  ``module_index`` must name a module of the enrollment's
  program, ``0 <= module_index < len(modules)``, enforced before
  anything is stored -- the extension's analogue of the core's
  signature stage bounds rule, and the batch's fresh negative
  control.
- Nothing here executes against an external system. The two
  stub-engine families ship as labeled reference implementations:
  video session and delivery session records carry
  ``reference_stub: True``, and invitation records carry
  ``reference_transport: True``. No video is streamed or
  recorded, no instrument is delivered, no response is captured,
  no workflow runs, no invitation is sent, and no venue is
  hosted.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

VIDEO_SESSION_STATUSES = ("declared", "reported")
DELIVERY_SESSION_STATUSES = ("declared", "reported")
AUTOMATION_RUN_STATUSES = ("requested", "reported")
INVITATION_STATUSES = ("recorded", "reported")
DEVELOPMENT_SESSION_KINDS = (
    "coaching",
    "mentoring",
    "training_session",
    "review",
)
KNOWN_DEVELOPMENT_SESSION_KINDS = frozenset(DEVELOPMENT_SESSION_KINDS)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _nonneg_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _one_of(value, known, names, what):
    if value not in known:
        raise ValidationError("%s must be one of %s" % (what, ", ".join(names)))
    return value


def _label_list(value, what, maximum=50):
    if not isinstance(value, list) or not value:
        raise ValidationError("%s must be a non-empty list of labels" % (what,))
    if len(value) > maximum:
        raise ValidationError("%s may hold at most %d entries" % (what, maximum))
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(
                "each entry in %s must be a non-empty string" % (what,))
        result.append(item)
    return result


class TalentMgmtExtensions:
    """GAPS-batch extension surface over a core TalentMgmtStore."""

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
        """Enforce a write permission, auditing a denial.

        Mirrors the core store: an actor must be present; User-like
        actors are checked against the core permission matrix before
        anything changes; plain strings carry identity only.
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

    def _guard_read(self, actor, core_action, audit_action, target=None):
        """Enforce a read permission when the actor carries a role."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, core_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", target)
                raise

    def _org(self, org_id, actor):
        """Resolve the organization through the core store, which
        enforces existence, the membership boundary, and (for
        User-like actors) the org_read role check."""
        return self.store.get_organization(org_id, actor)

    def _require_candidate(self, org_id, candidate_ref, actor):
        _non_empty(candidate_ref, "candidate_ref")
        for candidate in self.store.list_candidates(org_id, actor):
            if candidate["candidate_ref"] == candidate_ref:
                return candidate
        raise ValidationError(
            "candidate is not registered in organization %s: %r"
            % (org_id, candidate_ref)
        )

    def _create(self, kind, prefix, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            self._audit(actor, audit_action, record_id,
                        details={"kind": kind})
            return copy.deepcopy(record)

    def _get(self, kind, record_id, org_id=None):
        record = self._records.get((kind, record_id))
        if record is None or (org_id is not None
                              and record["org_id"] != org_id):
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id, org_id=None):
        return copy.deepcopy(self._get(kind, record_id, org_id))

    def _list(self, kind, org_id, **filters):
        result = []
        for key in self._order:
            if key[0] != kind:
                continue
            record = self._records[key]
            if record["org_id"] != org_id:
                continue
            if all(record.get(name) == value for name, value in filters.items()
                   if value is not None):
                result.append(copy.deepcopy(record))
        return result

    def _check_ref_unique(self, kind, org_id, field, value, scope_field=None,
                          scope_value=None):
        for key in self._order:
            if key[0] != kind:
                continue
            record = self._records[key]
            if record["org_id"] != org_id or record[field] != value:
                continue
            if scope_field is not None and record[scope_field] != scope_value:
                continue
            raise ValidationError(
                "%s %r already exists in organization %s"
                % (field, value, org_id)
            )

    def _transition(self, kind, record_id, org_id, from_status, to_status,
                    updates, actor, audit_action):
        """Guarded lifecycle transition on an extension record."""
        with self._lock:
            record = self._get(kind, record_id, org_id)
            if record["status"] != from_status:
                raise ValidationError(
                    "%s %s is %r; only a %s record can become %s"
                    % (kind, record_id, record["status"], from_status,
                       to_status)
                )
            record.update(updates)
            record["status"] = to_status
            self._audit(actor, audit_action, record_id,
                        details={"kind": kind})
            return copy.deepcopy(record)

    def _workflow_in(self, org_id, workflow_id, actor):
        for workflow in self.store.list_workflows(org_id, actor):
            if workflow["id"] == workflow_id:
                return workflow
        raise NotFoundError(
            "no such workflow in organization %s: %r" % (org_id, workflow_id)
        )

    def _registration_in(self, org_id, event_id, registration_id, actor):
        for registration in self.store.list_registrations(
                org_id, event_id, actor):
            if registration["id"] == registration_id:
                return registration
        raise NotFoundError(
            "no such registration for event %s: %r" % (event_id, registration_id)
        )

    # -- video interview sessions (entry 639, reference) ---------------

    def register_video_session(self, org_id, session_ref, interview_id,
                               actor):
        """Declare a video-interview session record bound to a core
        video interview. Reference implementation: the record
        carries ``reference_stub: True`` and the platform is not
        operated here (``streamed_here`` / ``recorded_here`` /
        ``media_held_here`` all False); binding to an in-person
        interview is refused, because the union spec's video
        sessions belong to video interviews."""
        self._guard(actor, "interview_write", "ext_video_session_register",
                    interview_id)
        self._org(org_id, actor)
        _non_empty(session_ref, "session_ref")
        interview = self.store.get_interview(org_id, interview_id, actor)
        if interview["kind"] != "video":
            raise ValidationError(
                "a video session can only bind to a video interview; "
                "interview %s is %r" % (interview_id, interview["kind"])
            )
        self._check_ref_unique("video_session", org_id, "session_ref",
                               session_ref)
        return self._create(
            "video_session", "vid-",
            {
                "org_id": org_id,
                "session_ref": session_ref,
                "interview_id": interview_id,
                "candidate_ref": interview["candidate_ref"],
                "status": "declared",
                "outcome_label": None,
                "reference_stub": True,
                "streamed_here": False,
                "recorded_here": False,
                "media_held_here": False,
            },
            actor, "ext_video_session_register",
        )

    def record_video_session_report(self, org_id, session_id, outcome_label,
                                    actor):
        """Report on a declared video session: the caller's outcome
        label, stored verbatim. Guarded declared -> reported;
        nothing about the session itself is captured."""
        self._guard(actor, "interview_write", "ext_video_session_report",
                    session_id)
        self._org(org_id, actor)
        _non_empty(outcome_label, "outcome_label")
        return self._transition(
            "video_session", session_id, org_id, "declared", "reported",
            {"outcome_label": outcome_label},
            actor, "ext_video_session_report")

    def list_video_sessions(self, org_id, actor, interview_id=None):
        self._guard_read(actor, "org_read", "ext_video_session_list", org_id)
        self._org(org_id, actor)
        return self._list("video_session", org_id, interview_id=interview_id)

    # -- assessment delivery sessions (entry 640, reference) -----------

    def register_delivery_session(self, org_id, delivery_ref, assessment_id,
                                  actor):
        """Declare an assessment delivery record bound to a core
        assessment. Reference implementation: the record carries
        ``reference_stub: True``; the instrument is not delivered
        here (``delivered_here`` False), no response is captured
        (``responses_held_here`` False), and nothing is computed
        (``computed_here`` False)."""
        self._guard(actor, "assessment_write", "ext_delivery_register",
                    assessment_id)
        self._org(org_id, actor)
        _non_empty(delivery_ref, "delivery_ref")
        assessment = self.store.get_assessment(org_id, assessment_id, actor)
        self._check_ref_unique("delivery_session", org_id, "delivery_ref",
                               delivery_ref)
        return self._create(
            "delivery_session", "dlv-",
            {
                "org_id": org_id,
                "delivery_ref": delivery_ref,
                "assessment_id": assessment_id,
                "candidate_ref": assessment["candidate_ref"],
                "status": "declared",
                "delivery_outcome_label": None,
                "reported_outcome_label": None,
                "reference_stub": True,
                "delivered_here": False,
                "responses_held_here": False,
                "computed_here": False,
            },
            actor, "ext_delivery_register",
        )

    def record_delivery_report(self, org_id, delivery_id,
                               delivery_outcome_label,
                               reported_outcome_label, actor):
        """Report a delivery: the caller's delivery outcome label
        and the assessment outcome label the caller's system
        produced, both stored verbatim. Guarded declared ->
        reported. Neither label is computed, graded, or checked
        here, and the core assessment record is never touched."""
        self._guard(actor, "assessment_write", "ext_delivery_report",
                    delivery_id)
        self._org(org_id, actor)
        _non_empty(delivery_outcome_label, "delivery_outcome_label")
        _non_empty(reported_outcome_label, "reported_outcome_label")
        return self._transition(
            "delivery_session", delivery_id, org_id, "declared", "reported",
            {"delivery_outcome_label": delivery_outcome_label,
             "reported_outcome_label": reported_outcome_label},
            actor, "ext_delivery_report")

    def list_delivery_sessions(self, org_id, actor, assessment_id=None):
        self._guard_read(actor, "org_read", "ext_delivery_list", org_id)
        self._org(org_id, actor)
        return self._list("delivery_session", org_id,
                          assessment_id=assessment_id)

    # -- predictive I-O models (entry 641, built) ----------------------

    def register_model_profile(self, org_id, profile_ref, model_label,
                               actor, validation_label=None):
        """Register a predictive model profile: an opaque model
        label plus, optionally, the validation status reported by
        the caller's own process. Nothing is validated, trained,
        or run here (``validated_here`` / ``inference_here``
        False)."""
        self._guard(actor, "registry_write", "ext_model_profile_register",
                    profile_ref)
        self._org(org_id, actor)
        _non_empty(profile_ref, "profile_ref")
        _non_empty(model_label, "model_label")
        _string_or_none(validation_label, "validation_label")
        self._check_ref_unique("model_profile", org_id, "profile_ref",
                               profile_ref)
        return self._create(
            "model_profile", "mdl-",
            {
                "org_id": org_id,
                "profile_ref": profile_ref,
                "model_label": model_label,
                "validation_label": validation_label,
                "validated_here": False,
                "inference_here": False,
            },
            actor, "ext_model_profile_register",
        )

    def record_prediction(self, org_id, prediction_ref, model_label,
                          predicted_label, actor, assessment_id=None,
                          interview_id=None):
        """Record one prediction about a candidate: the output of
        a caller's model, stored as the model's opaque label plus
        the predicted outcome label verbatim. Exactly one core
        record must be linked (an assessment or an interview);
        the candidate is read from it. The prediction is reported,
        never computed: ``computed_here`` and ``inference_here``
        are False, and there is no numeric parameter a predicted
        value could travel in."""
        self._guard(actor, "assessment_write", "ext_prediction_record",
                    prediction_ref)
        self._org(org_id, actor)
        _non_empty(prediction_ref, "prediction_ref")
        _non_empty(model_label, "model_label")
        _non_empty(predicted_label, "predicted_label")
        if (assessment_id is None) == (interview_id is None):
            raise ValidationError(
                "exactly one of assessment_id or interview_id must be given"
            )
        if assessment_id is not None:
            linked = self.store.get_assessment(org_id, assessment_id, actor)
        else:
            linked = self.store.get_interview(org_id, interview_id, actor)
        self._check_ref_unique("prediction", org_id, "prediction_ref",
                               prediction_ref)
        return self._create(
            "prediction", "prd-",
            {
                "org_id": org_id,
                "prediction_ref": prediction_ref,
                "assessment_id": assessment_id,
                "interview_id": interview_id,
                "candidate_ref": linked["candidate_ref"],
                "model_label": model_label,
                "predicted_label": predicted_label,
                "computed_here": False,
                "inference_here": False,
            },
            actor, "ext_prediction_record",
        )

    def list_model_profiles(self, org_id, actor):
        self._guard_read(actor, "org_read", "ext_model_profile_list", org_id)
        self._org(org_id, actor)
        return self._list("model_profile", org_id)

    def list_predictions(self, org_id, actor, candidate_ref=None):
        self._guard_read(actor, "org_read", "ext_prediction_list", org_id)
        self._org(org_id, actor)
        return self._list("prediction", org_id, candidate_ref=candidate_ref)

    # -- virtual event platform (entry 642, built) ---------------------

    def register_event_venue(self, org_id, venue_ref, event_id, venue_label,
                             actor):
        """Declare the virtual venue for a core virtual event: an
        opaque venue label bound to the event record. The venue
        itself is not operated here (``hosted_here`` /
        ``operated_here`` False); binding to an in-person event is
        refused, and each event carries at most one venue
        declaration."""
        self._guard(actor, "event_write", "ext_venue_register", event_id)
        self._org(org_id, actor)
        _non_empty(venue_ref, "venue_ref")
        _non_empty(venue_label, "venue_label")
        event = self.store.get_event(org_id, event_id, actor)
        if event["kind"] != "virtual":
            raise ValidationError(
                "a virtual venue can only bind to a virtual event; "
                "event %s is %r" % (event_id, event["kind"])
            )
        self._check_ref_unique("event_venue", org_id, "venue_ref", venue_ref)
        self._check_ref_unique("event_venue", org_id, "event_id", event_id)
        return self._create(
            "event_venue", "ven-",
            {
                "org_id": org_id,
                "venue_ref": venue_ref,
                "event_id": event_id,
                "venue_label": venue_label,
                "hosted_here": False,
                "operated_here": False,
            },
            actor, "ext_venue_register",
        )

    def record_venue_attendance_report(self, org_id, report_ref, venue_id,
                                       registered_reported,
                                       checked_in_reported, outcome_label,
                                       actor):
        """Record an attendance report for a venue: the counts the
        venue or the caller reports, stored as reported
        (``counted_here`` False). A report creates no core
        registration and changes no core registration or event
        status -- attendance of record stays with the core
        registry."""
        self._guard(actor, "event_write", "ext_venue_attendance_report",
                    venue_id)
        self._org(org_id, actor)
        _non_empty(report_ref, "report_ref")
        _non_empty(outcome_label, "outcome_label")
        _nonneg_int(registered_reported, "registered_reported")
        _nonneg_int(checked_in_reported, "checked_in_reported")
        venue = self._get("event_venue", venue_id, org_id)
        self._check_ref_unique("venue_attendance_report", org_id,
                               "report_ref", report_ref)
        return self._create(
            "venue_attendance_report", "var-",
            {
                "org_id": org_id,
                "report_ref": report_ref,
                "venue_id": venue_id,
                "event_id": venue["event_id"],
                "registered_reported": registered_reported,
                "checked_in_reported": checked_in_reported,
                "outcome_label": outcome_label,
                "counted_here": False,
            },
            actor, "ext_venue_attendance_report",
        )

    def record_event_invitation(self, org_id, invitation_ref, venue_id,
                                registration_id, actor):
        """Record an invitation for one core registration of the
        venue's event. The record is data for the communications
        layer, never a send: ``reference_transport: True`` and
        ``sent_here: False``, exactly as completion notices were
        adjudicated in the Communication category."""
        self._guard(actor, "event_write", "ext_invitation_record",
                    registration_id)
        self._org(org_id, actor)
        _non_empty(invitation_ref, "invitation_ref")
        venue = self._get("event_venue", venue_id, org_id)
        registration = self._registration_in(
            org_id, venue["event_id"], registration_id, actor)
        self._check_ref_unique("event_invitation", org_id,
                               "invitation_ref", invitation_ref)
        self._check_ref_unique("event_invitation", org_id,
                               "registration_id", registration_id)
        return self._create(
            "event_invitation", "inv-",
            {
                "org_id": org_id,
                "invitation_ref": invitation_ref,
                "venue_id": venue_id,
                "event_id": venue["event_id"],
                "registration_id": registration_id,
                "candidate_ref": registration["candidate_ref"],
                "status": "recorded",
                "outcome_label": None,
                "reference_transport": True,
                "sent_here": False,
            },
            actor, "ext_invitation_record",
        )

    def record_invitation_outcome(self, org_id, invitation_id, outcome_label,
                                  actor):
        """Report an invitation's outcome as the caller's
        communications system reports it, stored verbatim.
        Guarded recorded -> reported."""
        self._guard(actor, "event_write", "ext_invitation_outcome",
                    invitation_id)
        self._org(org_id, actor)
        _non_empty(outcome_label, "outcome_label")
        return self._transition(
            "event_invitation", invitation_id, org_id, "recorded",
            "reported", {"outcome_label": outcome_label},
            actor, "ext_invitation_outcome")

    def list_event_venues(self, org_id, actor, event_id=None):
        self._guard_read(actor, "org_read", "ext_venue_list", org_id)
        self._org(org_id, actor)
        return self._list("event_venue", org_id, event_id=event_id)

    def list_venue_attendance_reports(self, org_id, actor, venue_id=None):
        self._guard_read(actor, "org_read", "ext_venue_attendance_list",
                         org_id)
        self._org(org_id, actor)
        return self._list("venue_attendance_report", org_id,
                          venue_id=venue_id)

    def list_event_invitations(self, org_id, actor, venue_id=None):
        self._guard_read(actor, "org_read", "ext_invitation_list", org_id)
        self._org(org_id, actor)
        return self._list("event_invitation", org_id, venue_id=venue_id)

    # -- pipeline automation runs (entry 643, reference) ---------------

    def register_automation_run(self, org_id, run_ref, workflow_id, actor):
        """Register a requested automation run over a core workflow
        definition. Reference implementation: the core workflow
        registry is records-only by doctrine (no execute operation
        exists, and the founding suite pins that), so a run here is
        a request record carrying ``reference_stub: True`` and
        ``executed_here: False`` -- nothing is run."""
        self._guard(actor, "registry_write", "ext_automation_run_register",
                    workflow_id)
        self._org(org_id, actor)
        _non_empty(run_ref, "run_ref")
        self._workflow_in(org_id, workflow_id, actor)
        self._check_ref_unique("automation_run", org_id, "run_ref", run_ref)
        return self._create(
            "automation_run", "run-",
            {
                "org_id": org_id,
                "run_ref": run_ref,
                "workflow_id": workflow_id,
                "status": "requested",
                "outcome_label": None,
                "movements_reported": None,
                "reference_stub": True,
                "executed_here": False,
            },
            actor, "ext_automation_run_register",
        )

    def record_automation_report(self, org_id, run_id, outcome_label, actor,
                                 movements_reported=0):
        """Report what an external automation did, as the caller
        reports it: the outcome label verbatim and the count of
        stage movements the caller reports. Guarded requested ->
        reported. The report itself moves nothing: no core
        placement stage changes and no core movement record is
        created (pinned by test)."""
        self._guard(actor, "registry_write", "ext_automation_report",
                    run_id)
        self._org(org_id, actor)
        _non_empty(outcome_label, "outcome_label")
        _nonneg_int(movements_reported, "movements_reported")
        return self._transition(
            "automation_run", run_id, org_id, "requested", "reported",
            {"outcome_label": outcome_label,
             "movements_reported": movements_reported},
            actor, "ext_automation_report")

    def list_automation_runs(self, org_id, actor, workflow_id=None):
        self._guard_read(actor, "org_read", "ext_automation_run_list",
                         org_id)
        self._org(org_id, actor)
        return self._list("automation_run", org_id, workflow_id=workflow_id)

    # -- analytics & ROI (entry 644, built) ----------------------------

    def register_dashboard_definition(self, org_id, dashboard_ref, label,
                                      metric_labels, actor):
        """Register an analytics dashboard definition: an opaque
        label plus the metric labels the dashboard would show,
        held as data. Nothing is rendered here
        (``rendered_here`` False, ``definition_only`` True)."""
        self._guard(actor, "registry_write", "ext_dashboard_register",
                    dashboard_ref)
        self._org(org_id, actor)
        _non_empty(dashboard_ref, "dashboard_ref")
        _non_empty(label, "label")
        metrics = _label_list(metric_labels, "metric_labels")
        self._check_ref_unique("dashboard_definition", org_id,
                               "dashboard_ref", dashboard_ref)
        return self._create(
            "dashboard_definition", "dsh-",
            {
                "org_id": org_id,
                "dashboard_ref": dashboard_ref,
                "label": label,
                "metric_labels": metrics,
                "definition_only": True,
                "rendered_here": False,
            },
            actor, "ext_dashboard_register",
        )

    def record_roi_report(self, org_id, roi_ref, figure_label, actor,
                          requisition_id=None):
        """Record an ROI figure as reported by the caller's own
        analytics: the figure travels as a verbatim caller-supplied
        label, never as a number -- a numeric figure raises
        ValidationError, because computing or even normalizing an
        ROI figure would pretend a determination happened here.
        ``determined_here`` and ``computed_here`` are False."""
        self._guard(actor, "registry_write", "ext_roi_report_record",
                    roi_ref)
        self._org(org_id, actor)
        _non_empty(roi_ref, "roi_ref")
        if not isinstance(figure_label, str) or not figure_label.strip():
            raise ValidationError(
                "figure_label must be a non-empty string label; an ROI "
                "figure is recorded exactly as reported, never as a "
                "number computed or normalized here"
            )
        if requisition_id is not None:
            self.store.get_requisition(org_id, requisition_id, actor)
        self._check_ref_unique("roi_report", org_id, "roi_ref", roi_ref)
        return self._create(
            "roi_report", "roi-",
            {
                "org_id": org_id,
                "roi_ref": roi_ref,
                "requisition_id": requisition_id,
                "figure_label": figure_label,
                "determined_here": False,
                "computed_here": False,
            },
            actor, "ext_roi_report_record",
        )

    def analytics_snapshot(self, org_id, actor, now=None):
        """Derived analytics view: the core registry report
        (deterministic counts over the core's recorded quantities)
        plus counts over this extension's own records, computed at
        read and never stored. No ratio, percentage, or ROI figure
        is computed: ``ratios_computed_here`` and
        ``roi_determined_here`` are False, and the method is
        stated on the view."""
        self._guard_read(actor, "report_read", "ext_analytics_snapshot",
                         org_id)
        core_report = self.store.org_report(org_id, actor, now=now)
        extension_counts = {}
        for kind in (
                "video_session", "delivery_session", "model_profile",
                "prediction", "event_venue", "venue_attendance_report",
                "event_invitation", "automation_run",
                "dashboard_definition", "roi_report",
                "development_program", "development_enrollment",
                "program_milestone", "development_session"):
            records = self._list(kind, org_id)
            entry = {"count": len(records)}
            by_status = {}
            for record in records:
                if "status" in record:
                    by_status[record["status"]] = (
                        by_status.get(record["status"], 0) + 1)
            if by_status:
                entry["by_status"] = by_status
            extension_counts[kind] = entry
        return {
            "org_id": org_id,
            "core_report": core_report,
            "extension_counts": extension_counts,
            "method": "deterministic_counts_over_recorded_quantities",
            "ratios_computed_here": False,
            "roi_determined_here": False,
            "rendered_here": False,
        }

    def list_dashboard_definitions(self, org_id, actor):
        self._guard_read(actor, "org_read", "ext_dashboard_list", org_id)
        self._org(org_id, actor)
        return self._list("dashboard_definition", org_id)

    def list_roi_reports(self, org_id, actor, requisition_id=None):
        self._guard_read(actor, "org_read", "ext_roi_report_list", org_id)
        self._org(org_id, actor)
        return self._list("roi_report", org_id,
                          requisition_id=requisition_id)

    # -- talent development programs (entry 645, built) ----------------

    def create_development_program(self, org_id, program_ref, label, modules,
                                   actor):
        """Create a talent development program definition: an
        ordered list of module labels held as data, exactly as
        the core holds pipeline stages (``content_held_here``
        False). A program here is a development track a candidate
        may be enrolled in; it is not a personnel record, and the
        moment participation becomes a personnel action it belongs
        to the personnel system of record, which is a different
        category in this map."""
        self._guard(actor, "registry_write",
                    "ext_development_program_create", program_ref)
        self._org(org_id, actor)
        _non_empty(program_ref, "program_ref")
        _non_empty(label, "label")
        module_labels = _label_list(modules, "modules")
        self._check_ref_unique("development_program", org_id,
                               "program_ref", program_ref)
        return self._create(
            "development_program", "dvp-",
            {
                "org_id": org_id,
                "program_ref": program_ref,
                "label": label,
                "modules": module_labels,
                "content_held_here": False,
            },
            actor, "ext_development_program_create",
        )

    def enroll_in_development_program(self, org_id, enrollment_ref,
                                      program_id, candidate_ref, actor):
        """Enroll a registered candidate in a development program.
        One enrollment per candidate per program."""
        self._guard(actor, "candidate_write", "ext_development_enroll",
                    program_id)
        self._org(org_id, actor)
        _non_empty(enrollment_ref, "enrollment_ref")
        self._get("development_program", program_id, org_id)
        self._require_candidate(org_id, candidate_ref, actor)
        self._check_ref_unique("development_enrollment", org_id,
                               "enrollment_ref", enrollment_ref)
        self._check_ref_unique("development_enrollment", org_id,
                               "candidate_ref", candidate_ref,
                               scope_field="program_id",
                               scope_value=program_id)
        return self._create(
            "development_enrollment", "dve-",
            {
                "org_id": org_id,
                "enrollment_ref": enrollment_ref,
                "program_id": program_id,
                "candidate_ref": candidate_ref,
            },
            actor, "ext_development_enroll",
        )

    def _check_development_module_bounds(self, program, module_index):
        """The module bounds rule -- the batch's signature seam.

        A module-milestone's ``module_index`` must name a module
        of the enrollment's program: an integer satisfying
        ``0 <= module_index < len(program["modules"])``. Checked
        before anything is stored, so a violation consumes no id
        and changes nothing -- the extension's analogue of the
        core's signature stage bounds rule.
        """
        if isinstance(module_index, bool) or not isinstance(module_index, int):
            raise ValidationError("module_index must be an integer")
        if not 0 <= module_index < len(program["modules"]):
            raise ValidationError(
                "module_index %r is out of bounds for program %s "
                "with %d module(s)"
                % (module_index, program["id"], len(program["modules"]))
            )

    def record_program_milestone(self, org_id, milestone_ref, enrollment_id,
                                 module_index, actor):
        """Record one module check-off for an enrollment -- an
        append-only milestone record, the development analogue of
        a core pipeline movement. Progress is never written onto
        the enrollment; it is derived from these records."""
        self._guard(actor, "candidate_write",
                    "ext_development_milestone_record", enrollment_id)
        self._org(org_id, actor)
        _non_empty(milestone_ref, "milestone_ref")
        enrollment = self._get("development_enrollment", enrollment_id,
                               org_id)
        program = self._get("development_program", enrollment["program_id"],
                            org_id)
        self._check_ref_unique("program_milestone", org_id,
                               "milestone_ref", milestone_ref,
                               scope_field="enrollment_id",
                               scope_value=enrollment_id)
        # The module bounds seam: runs before storage.
        self._check_development_module_bounds(program, module_index)
        return self._create(
            "program_milestone", "dvm-",
            {
                "org_id": org_id,
                "milestone_ref": milestone_ref,
                "enrollment_id": enrollment_id,
                "module_index": module_index,
            },
            actor, "ext_development_milestone_record",
        )

    def development_progress(self, org_id, enrollment_id, actor):
        """Derived development progress for one enrollment: the
        completed module indices and labels, computed at read from
        the milestone records. The enrollment record itself stores
        no progress; a milestone whose index names no module (only
        reachable if the bounds seam is broken) makes this view
        raise, which is what the negative control demonstrates."""
        self._guard_read(actor, "org_read", "ext_development_progress",
                         enrollment_id)
        self._org(org_id, actor)
        enrollment = self._fetch("development_enrollment", enrollment_id,
                                 org_id)
        program = self._fetch("development_program",
                              enrollment["program_id"], org_id)
        milestones = self._list("program_milestone", org_id,
                                enrollment_id=enrollment_id)
        indices = sorted({m["module_index"] for m in milestones})
        return {
            "enrollment_id": enrollment_id,
            "program_id": program["id"],
            "candidate_ref": enrollment["candidate_ref"],
            "modules_total": len(program["modules"]),
            "completed_module_indices": indices,
            "completed_module_labels": [program["modules"][i]
                                        for i in indices],
            "completed_count": len(indices),
            "complete": len(indices) == len(program["modules"]),
        }

    def record_development_session(self, org_id, session_ref, enrollment_id,
                                   kind, actor, outcome_label=None):
        """Record a development session for an enrollment:
        metadata only (kind plus an optional caller-reported
        outcome label). No session content is held
        (``content_held_here`` False)."""
        self._guard(actor, "registry_write",
                    "ext_development_session_record", enrollment_id)
        self._org(org_id, actor)
        _non_empty(session_ref, "session_ref")
        _one_of(kind, KNOWN_DEVELOPMENT_SESSION_KINDS,
                DEVELOPMENT_SESSION_KINDS, "kind")
        _string_or_none(outcome_label, "outcome_label")
        self._get("development_enrollment", enrollment_id, org_id)
        self._check_ref_unique("development_session", org_id,
                               "session_ref", session_ref)
        return self._create(
            "development_session", "dvs-",
            {
                "org_id": org_id,
                "session_ref": session_ref,
                "enrollment_id": enrollment_id,
                "kind": kind,
                "outcome_label": outcome_label,
                "content_held_here": False,
            },
            actor, "ext_development_session_record",
        )

    def list_development_programs(self, org_id, actor):
        self._guard_read(actor, "org_read", "ext_development_program_list",
                         org_id)
        self._org(org_id, actor)
        return self._list("development_program", org_id)

    def list_development_enrollments(self, org_id, actor, program_id=None):
        self._guard_read(actor, "org_read", "ext_development_enrollment_list",
                         org_id)
        self._org(org_id, actor)
        return self._list("development_enrollment", org_id,
                          program_id=program_id)

    def list_program_milestones(self, org_id, actor, enrollment_id=None):
        self._guard_read(actor, "org_read", "ext_development_milestone_list",
                         org_id)
        self._org(org_id, actor)
        return self._list("program_milestone", org_id,
                          enrollment_id=enrollment_id)

    def list_development_sessions(self, org_id, actor, enrollment_id=None):
        self._guard_read(actor, "org_read", "ext_development_session_list",
                         org_id)
        self._org(org_id, actor)
        return self._list("development_session", org_id,
                          enrollment_id=enrollment_id)

    # -- summary --------------------------------------------------------

    def extension_summary(self, org_id, actor):
        """Derived summary over the extension's own records:
        counts per kind (with lifecycle breakdowns where a kind
        carries a status), computed at read. Counts only -- no
        totals over values, no ratios, no ROI."""
        self._guard_read(actor, "report_read", "ext_summary", org_id)
        self._org(org_id, actor)
        summary = {"org_id": org_id}
        for kind in (
                "video_session", "delivery_session", "model_profile",
                "prediction", "event_venue", "venue_attendance_report",
                "event_invitation", "automation_run",
                "dashboard_definition", "roi_report",
                "development_program", "development_enrollment",
                "program_milestone", "development_session"):
            records = self._list(kind, org_id)
            summary["%s_count" % kind] = len(records)
            if records and "status" in records[0]:
                by_status = {}
                for record in records:
                    by_status[record["status"]] = (
                        by_status.get(record["status"], 0) + 1)
                summary["%ss_by_status" % kind] = by_status
        summary["method"] = "deterministic_counts_over_recorded_quantities"
        return summary
