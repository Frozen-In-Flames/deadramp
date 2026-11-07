"""Final GAPS batch extensions, SECOND unit -- Health & Wellness
L2 remainder additions (+3 forks).

Clean-room, standard-library-only extensions for the 7 open
entries of the GAPS.md section "Remainder Addition -- Health &
Wellness L2 (+3 forks)" (see ``BATCH-ADDITION.md`` in the group
directory for the per-entry disposition). This is the second
batch unit in this directory: the first unit's
:mod:`health.extensions` is shipped core for this unit's
purposes and is NOT modified -- this module subclasses
:class:`HealthExtensions` and adds one new surface over the same
core :class:`HealthStore`. Every core module is untouched and
byte-identical to the shipped group build.

**The category's HARD PRIVACY RULE binds absolutely, here as in
the core and the first extension unit:** records and opaque
caller-supplied references only. No entity shape in this module
has a name, contact, date-of-birth, member-number, insurer,
diagnosis, clinical-note, or free-text clinical field -- those
fields **do not exist**. The addition forks' surfaces are engines
over clinical content (telehealth media, clinical payloads,
coding, report generation); their in-substrate forms are records
about those engines' work, never the work itself:

- Telehealth media (GTS) is media SESSION records -- opaque
  references, scheduling metadata, a recorded modality label, an
  explicit state setter. No media channel exists or is implied
  (``media_channel_here`` / ``connected_here`` are False). A
  session may bind to a Core activity (visit) record of the
  SAME participant only -- the ownership seam
  :meth:`HealthExtensionsAddition._check_activity_belongs`.
- Store-and-forward (GTS) is exchange PACKAGE records plus
  transfer EVENT records carrying direction, content-kind labels,
  and reported counts. The payload is clinical content and is
  never held, stored, or forwarded here (``payload_held_here`` /
  ``stored_here`` / ``forwarded_here`` are False); a package's
  current event label is derived at read.
- Medical coding (Solventum) is code-system VERSION records
  (the terminology content lives in the external content
  service), coding SUGGESTION records identified by opaque
  references -- the suggested code itself never enters this
  substrate, exactly as a model output enters the first unit
  only as an opaque reference -- and REVIEW records storing the
  clinician's own outcome label verbatim (``suggested_here`` /
  ``assigned_here`` are False).
- Grouper / reimbursement content (Solventum) is grouper
  DEFINITION records held as data, grouping OUTCOME records
  with coarse status labels as reported (the group assignment
  itself lives in the external engine), and reimbursement
  CONTENT PACKAGE records whose content is held elsewhere
  (``grouped_here`` / ``classified_here`` /
  ``content_held_here`` are False).
- CDI tooling (Solventum) is documentation QUERY records --
  a kind label plus an opaque reference to a document that
  lives in the external EHR -- and RESPONSE records storing
  the response outcome label verbatim. No document text and
  no query text is held or generated here
  (``document_text_held_here`` / ``generated_here`` are False).
- Diagnostic report generation (Somnoware) is report REQUEST
  records plus report REFERENCE records: the generated report
  is identified by an opaque reference and a reported status
  label; nothing is generated, interpreted, or held here
  (``generated_here`` / ``interpreted_here`` /
  ``report_held_here`` are False).
- The therapy progress console (Somnoware) is a DERIVED VIEW
  over Core records only -- per-metric deterministic aggregates
  and derived plan/activity counts for one participant in one
  program. No risk profile is computed, ever: the entry's own
  text bounds it ("no risk profile is computed in this build"),
  and the view carries ``risk_profile_computed_here: False``
  and ``predicted_here: False``.

Doctrines carried from the core and the first unit:
derived-never-stored for every computed value (package current
event label, suggestion current review outcome, grouping/CDI/
report current labels, console aggregates); append-only audit on
the core store's log with ``ext_``-prefixed actions for every
successful mutation, and denied write attempts recorded with a
``:denied`` suffix; RBAC via :mod:`health.access` with the core's
existing actions, enforced before any state change or id
allocation, so a failed operation consumes no id and changes
nothing; member scope mirrors the store's -- a member-role actor
may only read records whose participant's ``participant_ref`` is
their own name. This build is **not a medical device and claims
no FDA status**.
"""

from datetime import date

from .access import require  # noqa: F401  (re-exported for parity)
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError  # noqa: F401
from .extensions import (
    HealthExtensions,
    _REFERENCE_STATE,
    _count,
    _non_empty,
    _parse_iso_datetime,
    _utc_now,
    _validate_date,
)

MEDIA_MODALITIES = ("video", "audio", "teleconference")
MEDIA_SESSION_STATES = ("scheduled", "completed", "cancelled", "interrupted")
EXCHANGE_CONTENT_KINDS = ("lab", "image", "clinical_data")
EXCHANGE_DIRECTIONS = ("inbound", "outbound")
EXCHANGE_EVENT_LABELS = ("queued", "forwarded", "delivered",
                         "acknowledged", "failed")
CODE_SYSTEMS = ("cpt", "icd10", "hcpcs")
CODE_REVIEW_OUTCOMES = ("accepted", "rejected", "modified")
GROUPING_STATUS_LABELS = ("grouped", "ungrouped", "error")
CDI_QUERY_KINDS = ("clarification", "confirmation", "specificity")
CDI_RESPONSE_LABELS = ("responded", "declined", "pending")
REPORT_KINDS = ("sleep", "pulmonary", "diagnostic")
REPORT_STATUS_LABELS = ("reported", "failed", "pending")


class HealthExtensionsAddition(HealthExtensions):
    """Second-unit extension surface wrapping one HealthStore.

    Inherits the first unit's tables, guards, and helpers
    unchanged; every method below is new surface for the
    remainder-addition entries (idx 600-606).
    """

    def __init__(self, store):
        super().__init__(store)
        self._media_sessions = {}
        self._exchange_packages = {}
        self._exchange_events = {}
        self._code_system_versions = {}
        self._code_suggestions = {}
        self._code_reviews = {}
        self._grouper_definitions = {}
        self._grouping_outcomes = {}
        self._reimbursement_content = {}
        self._cdi_queries = {}
        self._cdi_responses = {}
        self._report_requests = {}
        self._report_references = {}
        self._counters.update({
            "tms": 0, "xpk": 0, "xev": 0, "ctv": 0, "cdg": 0,
            "cdr": 0, "grp": 0, "gpo": 0, "rcp": 0, "cdq": 0,
            "cdp": 0, "drq": 0, "drr": 0,
        })

    # -- Telehealth media engine (idx 600, GTS) --------------------------
    # Records form: a media session record is the session's
    # registry -- opaque references, scheduling metadata, and the
    # modality as a RECORDED LABEL. No media channel exists in
    # this substrate: ``media_channel_here`` and
    # ``connected_here`` are False on every session record and the
    # modality label implies no capability. (The first unit's
    # idx 191 closed the founding section's telehealth VISIT
    # records; this entry is the addition fork's MEDIA ENGINE --
    # the channel itself -- whose in-substrate form is the
    # session record bound to the visit's Core activity record.)
    # A session may bind only to an activity record of the SAME
    # participant -- the ownership seam below.

    def _check_activity_belongs(self, activity, participant_id):
        """Ownership seam for media sessions bound to Core visits.

        A media session may only bind to an activity (visit)
        record of the SAME participant the session is filed for.
        MUTATION DRILL NOTE: neutralizing this check (making the
        refusal unreachable) is this unit's negative-control
        mutation; the suite's refusal tests then fail (see
        tests/README.md for the verified record).
        """
        if activity["participant_id"] != participant_id:
            raise ValidationError(
                "activity record %r belongs to a different participant"
                % (activity["id"],))

    def create_media_session(self, participant_id, session_ref, modality,
                             starts_at, ends_at, actor, activity_id=None):
        """Schedule a telehealth media session record.

        Action: activity_write. ``activity_id`` optionally binds
        the session to the participant's own Core activity (visit)
        record; binding to another participant's activity is
        refused by the ownership seam.
        """
        self._guard(actor, "activity_write", "ext_media_session_create")
        _non_empty(session_ref, "session_ref")
        if modality not in MEDIA_MODALITIES:
            raise ValidationError(
                "modality must be one of %s" % (", ".join(MEDIA_MODALITIES),))
        start = _parse_iso_datetime(starts_at, "starts_at")
        end = _parse_iso_datetime(ends_at, "ends_at")
        if end < start:
            raise ValidationError("ends_at must not precede starts_at")
        with self._lock:
            self._check_participant(participant_id, actor)
            if activity_id is not None:
                activity = self.store.get_activity(activity_id, actor)
                self._check_activity_belongs(activity, participant_id)
            self._check_unique(self._media_sessions, "session_ref",
                               session_ref, "session_ref")
            record_id = self._next_id("tms")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "activity_id": activity_id,
                "session_ref": session_ref,
                "modality": modality,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "state": "scheduled",
                "media_channel_here": False,
                "connected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._media_sessions[record_id] = record
            self._audit(actor, "ext_media_session_create", record_id,
                        details={"participant_id": participant_id,
                                 "modality": modality})
            return dict(record)

    def set_media_session_state(self, session_id, state, actor):
        """Move a media session record to a new state.

        Action: activity_write. State moves are explicit
        records-form moves set by a clinician or admin; nothing
        about the actual session is observed or recorded.
        """
        self._guard(actor, "activity_write", "ext_media_session_set_state")
        if state not in MEDIA_SESSION_STATES:
            raise ValidationError(
                "state must be one of %s" % (", ".join(MEDIA_SESSION_STATES),))
        with self._lock:
            session = self._get(self._media_sessions, session_id,
                                "media session")
            session["state"] = state
            self._audit(actor, "ext_media_session_set_state", session_id,
                        details={"state": state})
            return dict(session)

    def list_media_sessions(self, actor=None, participant_id=None):
        """Return media session records, optionally filtered.

        Action: activity_read.
        """
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._media_sessions.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [dict(r) for r in self._scoped(actor, records)]

    def media_session_summary(self, actor, participant_id=None):
        """Derived media session counts by modality and state.

        Action: report_read (+ member scope). Deterministic
        counts over held session records, computed at read --
        ``method: deterministic_counts``. Never stored.
        """
        self._guard(actor, "report_read", "ext_media_session_summary")
        with self._lock:
            records = list(self._media_sessions.values())
            if participant_id is not None:
                self._check_participant(participant_id, actor)
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            records = self._scoped(actor, records)
            by_modality = {m: 0 for m in MEDIA_MODALITIES}
            by_state = {s: 0 for s in MEDIA_SESSION_STATES}
            for record in records:
                by_modality[record["modality"]] += 1
                by_state[record["state"]] += 1
            return {
                "participant_id": participant_id,
                "method": "deterministic_counts",
                "sessions": len(records),
                "by_modality": by_modality,
                "by_state": by_state,
                "media_channel_here": False,
            }

    # -- Store-and-forward clinical data service (idx 601, GTS) ---------
    # Records form: an exchange package record registers that a
    # bundle of clinical data (labs / images / clinical data --
    # the fork's own words) exists for a participant, under an
    # opaque package reference, with a direction and a reported
    # item count. Transfer event records carry the reported
    # progress labels of an external store-and-forward service.
    # The payload is clinical content: it is NEVER held, stored,
    # or forwarded by this substrate (``payload_held_here`` /
    # ``stored_here`` / ``forwarded_here`` are False). A package's
    # current event label is derived at read from its events.

    def create_exchange_package(self, participant_id, package_ref,
                                content_kind, direction, item_count, actor,
                                recorded_on=None):
        """Register a store-and-forward exchange package record.

        Action: activity_write. Carries the package's opaque
        reference, kind and direction labels, and the item count
        as reported -- never the payload.
        """
        self._guard(actor, "activity_write", "ext_exchange_package_create")
        _non_empty(package_ref, "package_ref")
        if content_kind not in EXCHANGE_CONTENT_KINDS:
            raise ValidationError(
                "content_kind must be one of %s"
                % (", ".join(EXCHANGE_CONTENT_KINDS),))
        if direction not in EXCHANGE_DIRECTIONS:
            raise ValidationError(
                "direction must be one of %s"
                % (", ".join(EXCHANGE_DIRECTIONS),))
        item_count = _count(item_count, "item_count")
        if recorded_on is not None:
            _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            self._check_unique(self._exchange_packages, "package_ref",
                               package_ref, "package_ref")
            record_id = self._next_id("xpk")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "package_ref": package_ref,
                "content_kind": content_kind,
                "direction": direction,
                "item_count": item_count,
                "recorded_on": recorded_on,
                "payload_held_here": False,
                "stored_here": False,
                "forwarded_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._exchange_packages[record_id] = record
            self._audit(actor, "ext_exchange_package_create", record_id,
                        details={"participant_id": participant_id,
                                 "content_kind": content_kind,
                                 "direction": direction})
            return dict(record)

    def record_exchange_event(self, package_id, event_label, actor,
                              occurred_on=None):
        """Record a reported transfer event for a package.

        Action: activity_write. The label is recorded as reported
        by the external service (``reference_transport: True`` --
        this substrate transports nothing itself).
        """
        self._guard(actor, "activity_write", "ext_exchange_event_record")
        if event_label not in EXCHANGE_EVENT_LABELS:
            raise ValidationError(
                "event_label must be one of %s"
                % (", ".join(EXCHANGE_EVENT_LABELS),))
        if occurred_on is not None:
            _validate_date(occurred_on, "occurred_on")
        with self._lock:
            package = self._get(self._exchange_packages, package_id,
                                "exchange package")
            record_id = self._next_id("xev")
            record = {
                "id": record_id,
                "package_id": package_id,
                "participant_id": package["participant_id"],
                "event_label": event_label,
                "occurred_on": occurred_on,
                "reference_transport": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._exchange_events[record_id] = record
            self._audit(actor, "ext_exchange_event_record", record_id,
                        details={"package_id": package_id,
                                 "event_label": event_label})
            return dict(record)

    def _package_view(self, package):
        events = self._sorted(
            [e for e in self._exchange_events.values()
             if e["package_id"] == package["id"]])
        view = dict(package)
        view["event_count"] = len(events)
        view["current_event_label"] = (
            events[-1]["event_label"] if events else None)
        return view

    def get_exchange_package(self, package_id, actor=None):
        """One package record with its derived event state.

        Action: activity_read (+ member scope).
        """
        self._maybe_require(actor, "activity_read")
        with self._lock:
            package = self._get(self._exchange_packages, package_id,
                                "exchange package")
            self._scope_check_record(actor, package)
            return self._package_view(package)

    def list_exchange_packages(self, actor=None, participant_id=None):
        """Return package records with derived event state.

        Action: activity_read.
        """
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._exchange_packages.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [self._package_view(r)
                    for r in self._scoped(actor, records)]

    def list_exchange_events(self, actor=None, package_id=None):
        """Return transfer event records, optionally filtered.

        Action: activity_read.
        """
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._exchange_events.values())
            if package_id is not None:
                records = [r for r in records
                           if r["package_id"] == package_id]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- Medical coding engine (idx 602, Solventum) ----------------------
    # Records form: a code-system version record registers a
    # terminology edition as data (system + version labels); the
    # terminology CONTENT lives in the external content service
    # and is never held here (``content_held_here: False``). A
    # coding suggestion record identifies one engine suggestion
    # by an opaque reference -- the suggested code itself never
    # enters this substrate (a code value attached to a
    # participant would be diagnosis-shaped content), exactly as
    # the first unit holds model outputs only as opaque
    # references. A review record stores the clinician's own
    # outcome label verbatim. Nothing is suggested or assigned
    # here (``suggested_here`` / ``assigned_here`` are False).

    def create_code_system_version(self, system_ref, code_system,
                                   version_label, actor):
        """Register a code-system version record. Action: program_write."""
        self._guard(actor, "program_write", "ext_code_system_version_create")
        _non_empty(system_ref, "system_ref")
        if code_system not in CODE_SYSTEMS:
            raise ValidationError(
                "code_system must be one of %s" % (", ".join(CODE_SYSTEMS),))
        _non_empty(version_label, "version_label")
        with self._lock:
            self._check_unique(self._code_system_versions, "system_ref",
                               system_ref, "system_ref")
            record_id = self._next_id("ctv")
            record = {
                "id": record_id,
                "system_ref": system_ref,
                "code_system": code_system,
                "version_label": version_label,
                "content_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._code_system_versions[record_id] = record
            self._audit(actor, "ext_code_system_version_create", record_id,
                        details={"system_ref": system_ref,
                                 "code_system": code_system})
            return dict(record)

    def record_code_suggestion(self, participant_id, version_id,
                               suggestion_ref, actor, recorded_on=None):
        """Record a coding suggestion reference. Action: plan_write.

        Only the opaque ``suggestion_ref`` is held; the suggestion
        itself (the code) lives in the external coding engine.
        """
        self._guard(actor, "plan_write", "ext_code_suggestion_record")
        _non_empty(suggestion_ref, "suggestion_ref")
        if recorded_on is not None:
            _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            self._get(self._code_system_versions, version_id,
                      "code system version")
            self._check_unique(self._code_suggestions, "suggestion_ref",
                               suggestion_ref, "suggestion_ref")
            record_id = self._next_id("cdg")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "version_id": version_id,
                "suggestion_ref": suggestion_ref,
                "recorded_on": recorded_on,
                "suggested_here": False,
                "assigned_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._code_suggestions[record_id] = record
            self._audit(actor, "ext_code_suggestion_record", record_id,
                        details={"participant_id": participant_id,
                                 "version_id": version_id})
            return dict(record)

    def record_code_review(self, suggestion_id, outcome_label, actor,
                           reviewed_on):
        """Record a clinician's review outcome label. Action: plan_write.

        The label is the clinician's own, stored verbatim.
        """
        self._guard(actor, "plan_write", "ext_code_review_record")
        if outcome_label not in CODE_REVIEW_OUTCOMES:
            raise ValidationError(
                "outcome_label must be one of %s"
                % (", ".join(CODE_REVIEW_OUTCOMES),))
        _validate_date(reviewed_on, "reviewed_on")
        with self._lock:
            suggestion = self._get(self._code_suggestions, suggestion_id,
                                   "code suggestion")
            record_id = self._next_id("cdr")
            record = {
                "id": record_id,
                "suggestion_id": suggestion_id,
                "participant_id": suggestion["participant_id"],
                "outcome_label": outcome_label,
                "reviewed_on": reviewed_on,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._code_reviews[record_id] = record
            self._audit(actor, "ext_code_review_record", record_id,
                        details={"suggestion_id": suggestion_id,
                                 "outcome_label": outcome_label})
            return dict(record)

    def _suggestion_view(self, suggestion):
        reviews = self._sorted(
            [r for r in self._code_reviews.values()
             if r["suggestion_id"] == suggestion["id"]])
        view = dict(suggestion)
        view["review_count"] = len(reviews)
        view["current_review_outcome"] = (
            reviews[-1]["outcome_label"] if reviews else None)
        return view

    def list_code_suggestions(self, actor=None, participant_id=None):
        """Return suggestion records with derived review state.

        Action: plan_read.
        """
        self._maybe_require(actor, "plan_read")
        with self._lock:
            records = self._sorted(self._code_suggestions.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [self._suggestion_view(r)
                    for r in self._scoped(actor, records)]

    def list_code_system_versions(self, actor=None):
        """Return code-system version records. Action: program_read."""
        self._maybe_require(actor, "program_read")
        with self._lock:
            return [dict(r)
                    for r in self._sorted(self._code_system_versions.values())]

    # -- Grouper / classification & reimbursement content (idx 603) -----
    # Records form: a grouper definition is a registry record
    # (scheme + version labels held as data); a grouping outcome
    # record carries a coarse status label as reported by the
    # external grouper plus an opaque outcome reference -- the
    # group assignment itself (a classification of the case) is
    # clinical content and lives in the external engine. A
    # reimbursement content package record registers content held
    # elsewhere under an opaque reference with a version label
    # and an effective window. Nothing is grouped, classified,
    # priced, or held here (``grouped_here`` / ``classified_here``
    # / ``content_held_here`` are False).

    def create_grouper_definition(self, grouper_ref, scheme_label,
                                  version_label, actor):
        """Register a grouper definition record. Action: program_write."""
        self._guard(actor, "program_write", "ext_grouper_definition_create")
        _non_empty(grouper_ref, "grouper_ref")
        _non_empty(scheme_label, "scheme_label")
        _non_empty(version_label, "version_label")
        with self._lock:
            self._check_unique(self._grouper_definitions, "grouper_ref",
                               grouper_ref, "grouper_ref")
            record_id = self._next_id("grp")
            record = {
                "id": record_id,
                "grouper_ref": grouper_ref,
                "scheme_label": scheme_label,
                "version_label": version_label,
                "grouped_here": False,
                "classified_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._grouper_definitions[record_id] = record
            self._audit(actor, "ext_grouper_definition_create", record_id,
                        details={"grouper_ref": grouper_ref})
            return dict(record)

    def record_grouping_outcome(self, participant_id, grouper_id,
                                outcome_ref, status_label, actor,
                                recorded_on=None):
        """Record a grouping outcome as reported. Action: plan_write.

        The status label is recorded as reported; the assignment
        itself never enters this substrate.
        """
        self._guard(actor, "plan_write", "ext_grouping_outcome_record")
        _non_empty(outcome_ref, "outcome_ref")
        if status_label not in GROUPING_STATUS_LABELS:
            raise ValidationError(
                "status_label must be one of %s"
                % (", ".join(GROUPING_STATUS_LABELS),))
        if recorded_on is not None:
            _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            self._get(self._grouper_definitions, grouper_id,
                      "grouper definition")
            self._check_unique(self._grouping_outcomes, "outcome_ref",
                               outcome_ref, "outcome_ref")
            record_id = self._next_id("gpo")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "grouper_id": grouper_id,
                "outcome_ref": outcome_ref,
                "status_label": status_label,
                "recorded_on": recorded_on,
                "grouped_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._grouping_outcomes[record_id] = record
            self._audit(actor, "ext_grouping_outcome_record", record_id,
                        details={"participant_id": participant_id,
                                 "grouper_id": grouper_id,
                                 "status_label": status_label})
            return dict(record)

    def create_reimbursement_content_package(self, content_ref, version_label,
                                             effective_from, actor,
                                             effective_to=None):
        """Register a reimbursement content package record.

        Action: program_write. The content itself is held by the
        external content service; only its opaque reference,
        version label, and effective window live here.
        """
        self._guard(actor, "program_write",
                    "ext_reimbursement_content_create")
        _non_empty(content_ref, "content_ref")
        _non_empty(version_label, "version_label")
        start = _validate_date(effective_from, "effective_from")
        if effective_to is not None:
            end = _validate_date(effective_to, "effective_to")
            if end < start:
                raise ValidationError(
                    "effective_to must not precede effective_from")
        with self._lock:
            self._check_unique(self._reimbursement_content, "content_ref",
                               content_ref, "content_ref")
            record_id = self._next_id("rcp")
            record = {
                "id": record_id,
                "content_ref": content_ref,
                "version_label": version_label,
                "effective_from": effective_from,
                "effective_to": effective_to,
                "content_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._reimbursement_content[record_id] = record
            self._audit(actor, "ext_reimbursement_content_create", record_id,
                        details={"content_ref": content_ref})
            return dict(record)

    def list_grouper_definitions(self, actor=None):
        """Return grouper definition records. Action: program_read."""
        self._maybe_require(actor, "program_read")
        with self._lock:
            return [dict(r)
                    for r in self._sorted(self._grouper_definitions.values())]

    def list_grouping_outcomes(self, actor=None, participant_id=None):
        """Return grouping outcome records. Action: plan_read."""
        self._maybe_require(actor, "plan_read")
        with self._lock:
            records = self._sorted(self._grouping_outcomes.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [dict(r) for r in self._scoped(actor, records)]

    def list_reimbursement_content_packages(self, actor=None):
        """Return reimbursement content package records.

        Action: program_read.
        """
        self._maybe_require(actor, "program_read")
        with self._lock:
            return [dict(r) for r in self._sorted(
                self._reimbursement_content.values())]

    # -- Clinical documentation integrity tooling (idx 604) -------------
    # Records form: a CDI query record registers a documentation
    # query against a participant as a KIND LABEL plus an opaque
    # reference to the document it concerns -- the document lives
    # in the external EHR and the query's own text is clinical
    # content, so neither is held or generated here
    # (``document_text_held_here`` / ``generated_here`` are
    # False). A response record stores the response outcome
    # label verbatim. A query's current response label is
    # derived at read from its response records.

    def create_cdi_query(self, participant_id, query_ref, query_kind,
                         document_ref, actor, issued_on):
        """Register a CDI query record. Action: activity_write."""
        self._guard(actor, "activity_write", "ext_cdi_query_create")
        _non_empty(query_ref, "query_ref")
        if query_kind not in CDI_QUERY_KINDS:
            raise ValidationError(
                "query_kind must be one of %s" % (", ".join(CDI_QUERY_KINDS),))
        _non_empty(document_ref, "document_ref")
        _validate_date(issued_on, "issued_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            self._check_unique(self._cdi_queries, "query_ref", query_ref,
                               "query_ref")
            record_id = self._next_id("cdq")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "query_ref": query_ref,
                "query_kind": query_kind,
                "document_ref": document_ref,
                "issued_on": issued_on,
                "document_text_held_here": False,
                "generated_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._cdi_queries[record_id] = record
            self._audit(actor, "ext_cdi_query_create", record_id,
                        details={"participant_id": participant_id,
                                 "query_kind": query_kind})
            return dict(record)

    def record_cdi_response(self, query_id, response_label, actor,
                            responded_on):
        """Record a CDI response outcome label. Action: activity_write.

        The label is recorded verbatim; the response's content
        lives in the external documentation system.
        """
        self._guard(actor, "activity_write", "ext_cdi_response_record")
        if response_label not in CDI_RESPONSE_LABELS:
            raise ValidationError(
                "response_label must be one of %s"
                % (", ".join(CDI_RESPONSE_LABELS),))
        _validate_date(responded_on, "responded_on")
        with self._lock:
            query = self._get(self._cdi_queries, query_id, "CDI query")
            record_id = self._next_id("cdp")
            record = {
                "id": record_id,
                "query_id": query_id,
                "participant_id": query["participant_id"],
                "response_label": response_label,
                "responded_on": responded_on,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._cdi_responses[record_id] = record
            self._audit(actor, "ext_cdi_response_record", record_id,
                        details={"query_id": query_id,
                                 "response_label": response_label})
            return dict(record)

    def _cdi_query_view(self, query):
        responses = self._sorted(
            [r for r in self._cdi_responses.values()
             if r["query_id"] == query["id"]])
        view = dict(query)
        view["response_count"] = len(responses)
        view["current_response_label"] = (
            responses[-1]["response_label"] if responses else None)
        return view

    def get_cdi_query(self, query_id, actor=None):
        """One CDI query record with its derived response state.

        Action: activity_read (+ member scope).
        """
        self._maybe_require(actor, "activity_read")
        with self._lock:
            query = self._get(self._cdi_queries, query_id, "CDI query")
            self._scope_check_record(actor, query)
            return self._cdi_query_view(query)

    def list_cdi_queries(self, actor=None, participant_id=None):
        """Return CDI query records with derived response state.

        Action: activity_read.
        """
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._cdi_queries.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [self._cdi_query_view(r)
                    for r in self._scoped(actor, records)]

    # -- Diagnostic report generation engine (idx 605, Somnoware) -------
    # Records form: a report request record registers that a
    # diagnostic report of a recorded kind was requested for a
    # participant; a report reference record identifies the
    # generated report by an opaque reference with a status
    # label as reported. The report itself -- generated clinical
    # content -- is never generated, interpreted, or held here
    # (``generated_here`` / ``interpreted_here`` /
    # ``report_held_here`` are False). A request's current report
    # status is derived at read from its reference records.

    def create_report_request(self, participant_id, request_ref, report_kind,
                              actor, requested_on, program_id=None):
        """Register a diagnostic report request. Action: measurement_write."""
        self._guard(actor, "measurement_write", "ext_report_request_create")
        _non_empty(request_ref, "request_ref")
        if report_kind not in REPORT_KINDS:
            raise ValidationError(
                "report_kind must be one of %s" % (", ".join(REPORT_KINDS),))
        _validate_date(requested_on, "requested_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            if program_id is not None:
                self._check_program(program_id, actor)
            self._check_unique(self._report_requests, "request_ref",
                               request_ref, "request_ref")
            record_id = self._next_id("drq")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "program_id": program_id,
                "request_ref": request_ref,
                "report_kind": report_kind,
                "requested_on": requested_on,
                "generated_here": False,
                "interpreted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._report_requests[record_id] = record
            self._audit(actor, "ext_report_request_create", record_id,
                        details={"participant_id": participant_id,
                                 "report_kind": report_kind})
            return dict(record)

    def record_report_reference(self, request_id, report_ref, status_label,
                                actor, recorded_on=None):
        """Record a generated report's reference. Action: measurement_write.

        Only the opaque ``report_ref`` and the reported status
        label are held; the report itself lives in the external
        generation system.
        """
        self._guard(actor, "measurement_write", "ext_report_reference_record")
        _non_empty(report_ref, "report_ref")
        if status_label not in REPORT_STATUS_LABELS:
            raise ValidationError(
                "status_label must be one of %s"
                % (", ".join(REPORT_STATUS_LABELS),))
        if recorded_on is not None:
            _validate_date(recorded_on, "recorded_on")
        with self._lock:
            request = self._get(self._report_requests, request_id,
                                "report request")
            self._check_unique(self._report_references, "report_ref",
                               report_ref, "report_ref")
            record_id = self._next_id("drr")
            record = {
                "id": record_id,
                "request_id": request_id,
                "participant_id": request["participant_id"],
                "report_ref": report_ref,
                "status_label": status_label,
                "recorded_on": recorded_on,
                "report_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._report_references[record_id] = record
            self._audit(actor, "ext_report_reference_record", record_id,
                        details={"request_id": request_id,
                                 "status_label": status_label})
            return dict(record)

    def _report_request_view(self, request):
        references = self._sorted(
            [r for r in self._report_references.values()
             if r["request_id"] == request["id"]])
        view = dict(request)
        view["report_count"] = len(references)
        view["current_report_status"] = (
            references[-1]["status_label"] if references else None)
        return view

    def list_report_requests(self, actor=None, participant_id=None):
        """Return report requests with derived report state.

        Action: measurement_read.
        """
        self._maybe_require(actor, "measurement_read")
        with self._lock:
            records = self._sorted(self._report_requests.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            return [self._report_request_view(r)
                    for r in self._scoped(actor, records)]

    # -- Therapy progress & risk-profile console (idx 606, Somnoware) ---
    # Records form: the console is a DERIVED VIEW over Core
    # records only -- the participant's measurement aggregates
    # and plan/activity counts in one program, computed at read
    # with the core's own aggregate shape. The console presents
    # recorded values; it computes NO risk profile, predicts
    # nothing, and flags nothing (the entry's own text:
    # "no risk profile is computed in this build"). The view
    # carries ``risk_profile_computed_here: False`` and
    # ``predicted_here: False`` so the boundary is on the record,
    # and no risk-shaped key exists anywhere in the view.

    def therapy_progress_console(self, participant_id, program_id, actor,
                                 as_of=None):
        """Derived therapy-progress view over Core records.

        Action: report_read (+ member scope). Per-metric
        count/min/max/mean over the participant's Core measurement
        records in the program, derived plan-status counts and
        activity-state counts at ``as_of`` -- ``method:
        deterministic_aggregates``. Never stored, and no risk
        profile, prediction, threshold, or interpretation is
        applied to the values.
        """
        self._guard(actor, "report_read", "ext_therapy_console")
        with self._lock:
            participant = self._check_participant(participant_id, actor)
            if self._is_member(actor) and \
                    participant["participant_ref"] != getattr(actor, "name",
                                                              None):
                raise PermissionDenied(
                    "permission denied: member %r may not access records of "
                    "another participant" % (getattr(actor, "name", None),))
            self._check_program(program_id, actor)
            if as_of is not None:
                _validate_date(as_of, "as_of")
            as_of_value = as_of if as_of is not None \
                else date.today().isoformat()
            measurements = self.store.list_measurements(
                actor, participant_id=participant_id, program_id=program_id)
            by_metric = {}
            for measurement in measurements:
                bucket = by_metric.setdefault(
                    measurement["metric_name"],
                    {"count": 0, "min": None, "max": None, "sum": 0.0})
                value = measurement["value"]
                bucket["count"] += 1
                bucket["sum"] += value
                bucket["min"] = value if bucket["min"] is None \
                    else min(bucket["min"], value)
                bucket["max"] = value if bucket["max"] is None \
                    else max(bucket["max"], value)
            measurements_by_metric = {}
            for metric_name in sorted(by_metric):
                bucket = by_metric[metric_name]
                measurements_by_metric[metric_name] = {
                    "count": bucket["count"],
                    "min": bucket["min"],
                    "max": bucket["max"],
                    "mean": bucket["sum"] / bucket["count"],
                }
            plans = self.store.list_plans(
                actor, participant_id=participant_id,
                program_id=program_id, as_of=as_of)
            plans_by_status = {"current": 0, "overdue": 0, "completed": 0}
            for plan in plans:
                plans_by_status[plan["derived_status"]] += 1
            activities = self.store.list_activities(
                actor, participant_id=participant_id, program_id=program_id)
            activities_by_state = {"scheduled": 0, "completed": 0,
                                   "cancelled": 0}
            for activity in activities:
                activities_by_state[activity["state"]] += 1
            return {
                "participant_id": participant_id,
                "program_id": program_id,
                "as_of": as_of_value,
                "method": "deterministic_aggregates",
                "measurements": len(measurements),
                "measurements_by_metric": measurements_by_metric,
                "plans": len(plans),
                "plans_by_status": plans_by_status,
                "activities": len(activities),
                "activities_by_state": activities_by_state,
                "risk_profile_computed_here": False,
                "predicted_here": False,
            }
