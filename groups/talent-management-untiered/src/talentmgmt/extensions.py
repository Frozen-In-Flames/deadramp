"""Final GAPS batch extensions for the Talent Management untiered set.

Clean-room, standard-library-only records/derivation extensions for
the 8 open Extended entries of this set's union spec: 5 built as
in-substrate records plus deterministic derivations over the core's
own records, and 3 shipped as labeled reference implementations.
See ``BATCH.md`` in the group directory for the per-entry
disposition and the adjudication notes.

Design, following the core's doctrines and this set's tier
discipline:

- This module is a wrapper around :class:`TalentMgmtStore`; the
  core modules are untouched (byte-identical). Candidate
  existence, assessment existence, and organization access are
  always read through the core store's public API, never
  re-implemented -- so the core's membership boundary and role
  matrix bind every extension operation exactly as they bind the
  core's own.
- **Tier null binds the whole surface.** The set's forks publish
  no FedRAMP impact level, so nothing here asserts or records a
  tier, a control baseline, or an equivalence: no record shape
  carries a tier-shaped key, and the batch tests scan every record
  and view recursively for one. The forks' documented control
  claims stay where the union spec put them -- in the spec, as the
  forks' claims about themselves.
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
  candidate registry; employers and external systems are opaque
  ``*_ref`` strings. No record shape in this module can hold a
  real person's name, contact detail, or identifier, an identity
  document, session media, assessment content, or a case note's
  text -- there is no parameter that could accept one (pinned by
  TypeError tests). Case activities carry a kind label and a short
  label only.
- **No score is computed anywhere, exactly as in the core.** No
  record shape carries a score, rating, ranking, or match value.
  Matches, proctoring outcomes, and UI statuses are caller- or
  program-reported labels recorded verbatim; matching is
  inference and is never performed here (``matched_here`` is
  False on every exchange match record).
- Derived values are derived at read and never stored: learning
  progress (from module-completion check-off records), a case's
  activity counts, the exchange / employer / labor-market
  summaries, and a UI claim's current reported status (from its
  newest report record). Stored records carry no derived key;
  tests pin that. Lifecycle statuses (proctoring requested ->
  reported, posting open -> closed, case open -> closed, service
  request open -> completed / cancelled) are guarded transitions,
  stored, exactly as the core stores its lifecycles.
- The module-bounds check for learning check-offs lives at a
  single named seam (``_check_module_bounds``): a completion's
  ``module_index`` must name a module of the enrollment's program,
  ``0 <= module_index < len(modules)``, enforced before anything
  is stored -- the extension's analogue of the core's signature
  stage bounds rule, and the batch's fresh negative control.
- Nothing here executes against an external system. The three
  stub-engine families ship as labeled reference implementations:
  proctoring and UI claim records carry ``reference_stub: True``,
  integration endpoints carry ``reference_stub: True``, and
  exchange / distribution receipts carry
  ``reference_transport: True``. No identity document is checked,
  no session is monitored, no benefit is determined or paid, no
  data moves, and no content is delivered.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

PROCTORING_CHECK_KINDS = (
    "identity_document_check",
    "session_monitoring",
    "integrity_review",
)
KNOWN_PROCTORING_CHECK_KINDS = frozenset(PROCTORING_CHECK_KINDS)
PROCTORING_STATUSES = ("requested", "reported")
TUTOR_SESSION_KINDS = ("tutoring", "mentoring", "review")
KNOWN_TUTOR_SESSION_KINDS = frozenset(TUTOR_SESSION_KINDS)
INTEGRATION_KINDS = (
    "ats_integration",
    "hris_integration",
    "public_api",
    "developer_api",
    "other",
)
KNOWN_INTEGRATION_KINDS = frozenset(INTEGRATION_KINDS)
INTEGRATION_DIRECTIONS = ("inbound", "outbound", "bidirectional")
KNOWN_INTEGRATION_DIRECTIONS = frozenset(INTEGRATION_DIRECTIONS)
POSTING_STATUSES = ("open", "closed")
CASE_STATUSES = ("open", "closed")
CASE_ACTIVITY_KINDS = (
    "intake",
    "review",
    "referral",
    "enrollment",
    "follow_up",
    "appointment",
    "other",
)
KNOWN_CASE_ACTIVITY_KINDS = frozenset(CASE_ACTIVITY_KINDS)
EMPLOYER_SERVICE_KINDS = (
    "job_order",
    "recruitment_assistance",
    "training_consultation",
    "labor_market_briefing",
    "other",
)
KNOWN_EMPLOYER_SERVICE_KINDS = frozenset(EMPLOYER_SERVICE_KINDS)
SERVICE_REQUEST_STATUSES = ("open", "completed", "cancelled")
LMI_METRIC_KINDS = (
    "job_openings",
    "unemployed",
    "employed",
    "wage_postings",
    "program_participants",
    "other",
)
KNOWN_LMI_METRIC_KINDS = frozenset(LMI_METRIC_KINDS)


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

    # -- Assessment proctoring & integrity services (reference) -------
    # A proctoring session here is a reference record bound to a
    # core assessment record: the check kinds requested, as labels,
    # and -- once the proctoring service reports -- its outcome
    # label and flag count, stored verbatim as reported. No identity
    # document is held or checked, no session media exists, and no
    # integrity outcome is adjudicated here: the report is the
    # service's, recorded. ``reference_stub`` is True throughout.

    def register_proctoring_session(self, org_id, session_ref, assessment_id,
                                    check_kinds, actor):
        """Register a proctoring session reference record against a
        core assessment. Action: assessment_write."""
        self._guard(actor, "assessment_write", "ext_proctoring_register",
                    org_id)
        self._org(org_id, actor)
        _non_empty(session_ref, "session_ref")
        kinds = _label_list(check_kinds, "check_kinds")
        for kind in kinds:
            _one_of(kind, KNOWN_PROCTORING_CHECK_KINDS,
                    PROCTORING_CHECK_KINDS, "check kind")
        if len(set(kinds)) != len(kinds):
            raise ValidationError("check_kinds must not repeat a kind")
        assessment = self.store.get_assessment(org_id, assessment_id, actor)
        with self._lock:
            self._check_ref_unique("proctoring_session", org_id,
                                   "session_ref", session_ref)
            return self._create(
                "proctoring_session", "pro-",
                {"org_id": org_id,
                 "session_ref": session_ref,
                 "assessment_id": assessment_id,
                 "candidate_ref": assessment["candidate_ref"],
                 "check_kinds": kinds,
                 "status": "requested",
                 "outcome_label": None,
                 "flags_reported": None,
                 "reference_stub": True,
                 "adjudicated_here": False,
                 "identity_document_held_here": False,
                 "session_media_held_here": False},
                actor, "ext_proctoring_register")

    def record_proctoring_report(self, org_id, session_id, outcome_label,
                                 flags_reported, actor):
        """Record the proctoring service's report, verbatim.

        Action: assessment_write. The outcome label and flag count
        are the service's report; nothing is adjudicated or scored
        here. Only a requested session can be reported.
        """
        self._guard(actor, "assessment_write", "ext_proctoring_report",
                    org_id)
        self._org(org_id, actor)
        _non_empty(outcome_label, "outcome_label")
        _nonneg_int(flags_reported, "flags_reported")
        with self._lock:
            session = self._get("proctoring_session", session_id, org_id)
            if session["status"] != "requested":
                raise ValidationError(
                    "proctoring session %s is %r; only a requested "
                    "session can be reported"
                    % (session_id, session["status"])
                )
            session["status"] = "reported"
            session["outcome_label"] = outcome_label
            session["flags_reported"] = flags_reported
            self._audit(actor, "ext_proctoring_report", session_id,
                        details={"kind": "proctoring_session"})
            return copy.deepcopy(session)

    def get_proctoring_session(self, org_id, session_id, actor):
        """Return one proctoring session record. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_proctoring_read", org_id)
        self._org(org_id, actor)
        return self._fetch("proctoring_session", session_id, org_id)

    def list_proctoring_sessions(self, org_id, actor, assessment_id=None):
        """Return proctoring session records. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_proctoring_read", org_id)
        self._org(org_id, actor)
        return self._list("proctoring_session", org_id,
                          assessment_id=assessment_id)

    # -- Experiential technical learning platform (built) -------------
    # A learning program here is a definition: an ordered list of
    # module labels held as data. Enrollments bind an opaque
    # candidate reference to a program; progress is a set of
    # module-completion check-off records, and the progress view is
    # derived from them at read -- never stored. No learning
    # content is held or delivered here (``content_held_here`` is
    # False); tutor sessions are metadata records with a
    # caller-supplied outcome label, and no session content exists.

    def _check_module_bounds(self, program, module_index):
        """Module bounds seam: ``module_index`` must be an integer
        naming a module of ``program``:
        ``0 <= module_index < len(program["modules"])``. Raises
        ValidationError on a violation. (This is the seam the
        batch's fresh negative control mutates -- the extension's
        analogue of the core's stage bounds seam.)"""
        if isinstance(module_index, bool) or not isinstance(module_index, int):
            raise ValidationError("module_index must be an integer")
        if module_index < 0 or module_index >= len(program["modules"]):
            raise ValidationError(
                "module_index %d is outside the program's %d modules"
                % (module_index, len(program["modules"]))
            )

    def create_learning_program(self, org_id, program_ref, label, modules,
                                actor):
        """Define a learning program: an ordered module list held
        as data. Action: registry_write."""
        self._guard(actor, "registry_write", "ext_learning_program_create",
                    org_id)
        self._org(org_id, actor)
        _non_empty(program_ref, "program_ref")
        _non_empty(label, "label")
        module_labels = _label_list(modules, "modules")
        if len(set(module_labels)) != len(module_labels):
            raise ValidationError("module labels must be unique within a program")
        with self._lock:
            self._check_ref_unique("learning_program", org_id,
                                   "program_ref", program_ref)
            return self._create(
                "learning_program", "lrn-",
                {"org_id": org_id,
                 "program_ref": program_ref,
                 "label": label,
                 "modules": module_labels,
                 "content_held_here": False},
                actor, "ext_learning_program_create")

    def get_learning_program(self, org_id, program_id, actor):
        """Return one learning program definition. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_learning_program_read",
                         org_id)
        self._org(org_id, actor)
        return self._fetch("learning_program", program_id, org_id)

    def list_learning_programs(self, org_id, actor):
        """Return learning program definitions. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_learning_program_read",
                         org_id)
        self._org(org_id, actor)
        return self._list("learning_program", org_id)

    def enroll_candidate(self, org_id, enrollment_ref, program_id,
                         candidate_ref, actor):
        """Enroll an opaque candidate reference in a program.

        Action: registry_write. A candidate enrolls once per
        program; the enrollment record holds no progress -- progress
        is derived from completion records at read.
        """
        self._guard(actor, "registry_write", "ext_learning_enroll", org_id)
        self._org(org_id, actor)
        _non_empty(enrollment_ref, "enrollment_ref")
        self._require_candidate(org_id, candidate_ref, actor)
        with self._lock:
            self._get("learning_program", program_id, org_id)
            self._check_ref_unique("learning_enrollment", org_id,
                                   "enrollment_ref", enrollment_ref)
            for key in self._order:
                if key[0] != "learning_enrollment":
                    continue
                record = self._records[key]
                if (record["org_id"] == org_id
                        and record["program_id"] == program_id
                        and record["candidate_ref"] == candidate_ref):
                    raise ValidationError(
                        "candidate %r is already enrolled in program %s"
                        % (candidate_ref, program_id)
                    )
            return self._create(
                "learning_enrollment", "enr-",
                {"org_id": org_id,
                 "enrollment_ref": enrollment_ref,
                 "program_id": program_id,
                 "candidate_ref": candidate_ref},
                actor, "ext_learning_enroll")

    def list_learning_enrollments(self, org_id, actor, program_id=None,
                                  candidate_ref=None):
        """Return enrollment records. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_learning_enroll_read",
                         org_id)
        self._org(org_id, actor)
        return self._list("learning_enrollment", org_id,
                          program_id=program_id, candidate_ref=candidate_ref)

    def record_module_completion(self, org_id, completion_ref, enrollment_id,
                                 module_index, actor):
        """Record a module-completion check-off for an enrollment.

        Action: registry_write. The bounds seam runs before
        anything is stored; a module can be checked off once per
        enrollment. The check-off is a record -- nothing about it
        delivers or verifies learning content.
        """
        self._guard(actor, "registry_write", "ext_learning_complete", org_id)
        self._org(org_id, actor)
        _non_empty(completion_ref, "completion_ref")
        with self._lock:
            enrollment = self._get("learning_enrollment", enrollment_id,
                                   org_id)
            program = self._get("learning_program",
                                enrollment["program_id"], org_id)
            self._check_ref_unique("module_completion", org_id,
                                   "completion_ref", completion_ref,
                                   scope_field="enrollment_id",
                                   scope_value=enrollment_id)
            for key in self._order:
                if key[0] != "module_completion":
                    continue
                record = self._records[key]
                if (record["enrollment_id"] == enrollment_id
                        and record["module_index"] == module_index):
                    raise ValidationError(
                        "module %d is already completed for enrollment %s"
                        % (module_index, enrollment_id)
                    )
            self._check_module_bounds(program, module_index)
            return self._create(
                "module_completion", "mod-",
                {"org_id": org_id,
                 "completion_ref": completion_ref,
                 "enrollment_id": enrollment_id,
                 "module_index": module_index},
                actor, "ext_learning_complete")

    def list_module_completions(self, org_id, actor, enrollment_id=None):
        """Return module-completion check-off records. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_learning_complete_read",
                         org_id)
        self._org(org_id, actor)
        return self._list("module_completion", org_id,
                          enrollment_id=enrollment_id)

    def learning_progress(self, org_id, enrollment_id, actor):
        """Derived progress view for one enrollment.

        Action: report_read. Everything beyond the enrollment's own
        fields is derived at read from its completion records: the
        completed module indices and labels, the completed count,
        the program's module count, and whether every module is
        checked off. The stored enrollment record carries none of
        it (pinned by test).
        """
        self._guard_read(actor, "report_read", "ext_learning_progress_read",
                         org_id)
        self._org(org_id, actor)
        enrollment = self._fetch("learning_enrollment", enrollment_id,
                                 org_id)
        program = self._get("learning_program", enrollment["program_id"],
                            org_id)
        completions = self._list("module_completion", org_id,
                                 enrollment_id=enrollment_id)
        indices = sorted(c["module_index"] for c in completions)
        view = dict(enrollment)
        view["completed_module_indices"] = indices
        view["completed_modules"] = [program["modules"][i] for i in indices]
        view["completed_count"] = len(indices)
        view["module_count"] = len(program["modules"])
        view["program_complete"] = (
            len(indices) == len(program["modules"]) and len(indices) > 0
        )
        return view

    def record_tutor_session(self, org_id, tutor_session_ref, enrollment_id,
                             kind, actor, outcome_label=None):
        """Record a tutor session's metadata against an enrollment.

        Action: registry_write. The record is metadata -- kind and
        an optional caller-supplied outcome label; no session
        content, recording, or transcript exists anywhere here.
        """
        self._guard(actor, "registry_write", "ext_tutor_session_record",
                    org_id)
        self._org(org_id, actor)
        _non_empty(tutor_session_ref, "tutor_session_ref")
        _one_of(kind, KNOWN_TUTOR_SESSION_KINDS, TUTOR_SESSION_KINDS, "kind")
        _string_or_none(outcome_label, "outcome_label")
        with self._lock:
            self._get("learning_enrollment", enrollment_id, org_id)
            self._check_ref_unique("tutor_session", org_id,
                                   "tutor_session_ref", tutor_session_ref)
            return self._create(
                "tutor_session", "tut-",
                {"org_id": org_id,
                 "tutor_session_ref": tutor_session_ref,
                 "enrollment_id": enrollment_id,
                 "kind": kind,
                 "outcome_label": outcome_label,
                 "session_content_held_here": False},
                actor, "ext_tutor_session_record")

    def list_tutor_sessions(self, org_id, actor, enrollment_id=None):
        """Return tutor session records. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_tutor_session_read", org_id)
        self._org(org_id, actor)
        return self._list("tutor_session", org_id,
                          enrollment_id=enrollment_id)

    # -- Integration & API services layer (reference) -----------------
    # An integration endpoint here is a definition record: an opaque
    # external-system reference, a kind and direction label, held as
    # data. Exchange records are receipts: record counts and an
    # outcome label, exactly as the connected system reports them.
    # No credential is held or issued (identity stays with the
    # embedding organization), no connection opens, and no data
    # moves here. ``reference_stub`` / ``reference_transport`` are
    # True throughout.

    def register_integration_endpoint(self, org_id, endpoint_ref, label,
                                      kind, system_ref, direction, actor):
        """Register an integration endpoint definition.

        Action: registry_write."""
        self._guard(actor, "registry_write", "ext_integration_register",
                    org_id)
        self._org(org_id, actor)
        _non_empty(endpoint_ref, "endpoint_ref")
        _non_empty(label, "label")
        _one_of(kind, KNOWN_INTEGRATION_KINDS, INTEGRATION_KINDS, "kind")
        _non_empty(system_ref, "system_ref")
        _one_of(direction, KNOWN_INTEGRATION_DIRECTIONS,
                INTEGRATION_DIRECTIONS, "direction")
        with self._lock:
            self._check_ref_unique("integration_endpoint", org_id,
                                   "endpoint_ref", endpoint_ref)
            return self._create(
                "integration_endpoint", "iep-",
                {"org_id": org_id,
                 "endpoint_ref": endpoint_ref,
                 "label": label,
                 "kind": kind,
                 "system_ref": system_ref,
                 "direction": direction,
                 "reference_stub": True,
                 "credentials_held_here": False,
                 "connected_here": False},
                actor, "ext_integration_register")

    def get_integration_endpoint(self, org_id, endpoint_id, actor):
        """Return one integration endpoint definition. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_integration_read", org_id)
        self._org(org_id, actor)
        return self._fetch("integration_endpoint", endpoint_id, org_id)

    def list_integration_endpoints(self, org_id, actor):
        """Return integration endpoint definitions. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_integration_read", org_id)
        self._org(org_id, actor)
        return self._list("integration_endpoint", org_id)

    def record_integration_exchange(self, org_id, exchange_ref, endpoint_id,
                                    records_in_reported, records_out_reported,
                                    outcome_label, actor):
        """Record an integration exchange receipt, as reported.

        Action: registry_write. The counts and outcome label are
        the connected system's report, stored verbatim; this build
        moved no data (``reference_transport`` is True).
        """
        self._guard(actor, "registry_write", "ext_integration_exchange",
                    org_id)
        self._org(org_id, actor)
        _non_empty(exchange_ref, "exchange_ref")
        _nonneg_int(records_in_reported, "records_in_reported")
        _nonneg_int(records_out_reported, "records_out_reported")
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._get("integration_endpoint", endpoint_id, org_id)
            self._check_ref_unique("integration_exchange", org_id,
                                   "exchange_ref", exchange_ref)
            return self._create(
                "integration_exchange", "iex-",
                {"org_id": org_id,
                 "exchange_ref": exchange_ref,
                 "endpoint_id": endpoint_id,
                 "records_in_reported": records_in_reported,
                 "records_out_reported": records_out_reported,
                 "outcome_label": outcome_label,
                 "reference_transport": True,
                 "data_moved_here": False},
                actor, "ext_integration_exchange")

    def list_integration_exchanges(self, org_id, actor, endpoint_id=None):
        """Return integration exchange receipts. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_integration_exchange_read",
                         org_id)
        self._org(org_id, actor)
        return self._list("integration_exchange", org_id,
                          endpoint_id=endpoint_id)

    # -- Labor exchange platform (built) -------------------------------
    # The exchange's records surface: job postings listed by opaque
    # employer references, and match records. A match record is a
    # caller-reported pairing of a posting and an opaque candidate
    # reference with the reporter's outcome label, recorded
    # verbatim. Matching itself is inference: it is never computed
    # here, no score or ranking exists, and every match record
    # carries ``matched_here`` False. The summary is deterministic
    # counts derived at read.

    def create_exchange_posting(self, org_id, posting_ref, employer_ref,
                                title, actor):
        """List a job posting on the exchange. Action: requisition_write."""
        self._guard(actor, "requisition_write", "ext_posting_create", org_id)
        self._org(org_id, actor)
        _non_empty(posting_ref, "posting_ref")
        _non_empty(employer_ref, "employer_ref")
        _non_empty(title, "title")
        with self._lock:
            self._check_ref_unique("exchange_posting", org_id,
                                   "posting_ref", posting_ref)
            return self._create(
                "exchange_posting", "job-",
                {"org_id": org_id,
                 "posting_ref": posting_ref,
                 "employer_ref": employer_ref,
                 "title": title,
                 "status": "open"},
                actor, "ext_posting_create")

    def close_exchange_posting(self, org_id, posting_id, actor):
        """Close an exchange posting. Action: requisition_write.
        Only an open posting can be closed."""
        self._guard(actor, "requisition_write", "ext_posting_close", org_id)
        self._org(org_id, actor)
        with self._lock:
            posting = self._get("exchange_posting", posting_id, org_id)
            if posting["status"] != "open":
                raise ValidationError(
                    "posting %s is %r; only an open posting can be closed"
                    % (posting_id, posting["status"])
                )
            posting["status"] = "closed"
            self._audit(actor, "ext_posting_close", posting_id,
                        details={"kind": "exchange_posting"})
            return copy.deepcopy(posting)

    def get_exchange_posting(self, org_id, posting_id, actor):
        """Return one exchange posting. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_posting_read", org_id)
        self._org(org_id, actor)
        return self._fetch("exchange_posting", posting_id, org_id)

    def list_exchange_postings(self, org_id, actor, employer_ref=None,
                               status=None):
        """Return exchange postings. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_posting_read", org_id)
        self._org(org_id, actor)
        if status is not None:
            _one_of(status, frozenset(POSTING_STATUSES), POSTING_STATUSES,
                    "status")
        return self._list("exchange_posting", org_id,
                          employer_ref=employer_ref, status=status)

    def record_exchange_match(self, org_id, match_ref, posting_id,
                              candidate_ref, outcome_label, actor):
        """Record a reported exchange match.

        Action: pipeline_write. The pairing and its outcome label
        are the reporter's, recorded verbatim; this build computed
        no match and no score (``matched_here`` is False). One
        match record per posting/candidate pair.
        """
        self._guard(actor, "pipeline_write", "ext_match_record", org_id)
        self._org(org_id, actor)
        _non_empty(match_ref, "match_ref")
        _non_empty(outcome_label, "outcome_label")
        self._require_candidate(org_id, candidate_ref, actor)
        with self._lock:
            self._get("exchange_posting", posting_id, org_id)
            self._check_ref_unique("exchange_match", org_id,
                                   "match_ref", match_ref)
            for key in self._order:
                if key[0] != "exchange_match":
                    continue
                record = self._records[key]
                if (record["posting_id"] == posting_id
                        and record["candidate_ref"] == candidate_ref):
                    raise ValidationError(
                        "a match for candidate %r on posting %s is "
                        "already recorded" % (candidate_ref, posting_id)
                    )
            return self._create(
                "exchange_match", "mat-",
                {"org_id": org_id,
                 "match_ref": match_ref,
                 "posting_id": posting_id,
                 "candidate_ref": candidate_ref,
                 "outcome_label": outcome_label,
                 "matched_here": False},
                actor, "ext_match_record")

    def list_exchange_matches(self, org_id, actor, posting_id=None,
                              candidate_ref=None):
        """Return exchange match records. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_match_read", org_id)
        self._org(org_id, actor)
        return self._list("exchange_match", org_id, posting_id=posting_id,
                          candidate_ref=candidate_ref)

    def exchange_summary(self, org_id, actor):
        """Derived exchange counts for one organization.

        Action: report_read. Counts of recorded things, derived at
        read: postings by status, match records by their reported
        outcome label, and the count of distinct candidates with a
        recorded match. No rate, ranking, or score is computed.
        """
        self._guard_read(actor, "report_read", "ext_exchange_summary_read",
                         org_id)
        self._org(org_id, actor)
        postings = self._list("exchange_posting", org_id)
        matches = self._list("exchange_match", org_id)
        postings_by_status = {s: 0 for s in POSTING_STATUSES}
        for posting in postings:
            postings_by_status[posting["status"]] += 1
        matches_by_outcome = {}
        for match in matches:
            label = match["outcome_label"]
            matches_by_outcome[label] = matches_by_outcome.get(label, 0) + 1
        return {
            "org_id": org_id,
            "posting_count": len(postings),
            "postings_by_status": postings_by_status,
            "match_count": len(matches),
            "matches_by_outcome": matches_by_outcome,
            "matched_candidate_count": len(
                {m["candidate_ref"] for m in matches}
            ),
        }

    # -- Workforce case management system (built) ----------------------
    # A case here binds an opaque participant reference (a core
    # candidate) to a workforce program label. Case activities are
    # append-only records carrying a kind label and a short label --
    # never narrative text. The case view's activity counts are
    # derived at read; the stored case record carries none of them.

    def create_workforce_case(self, org_id, case_ref, candidate_ref,
                              program_label, actor):
        """Open a workforce case for a participant.

        Action: candidate_write. The participant is an opaque core
        candidate reference; the moment a hire becomes a personnel
        action it belongs to Human Resources, not here.
        """
        self._guard(actor, "candidate_write", "ext_case_create", org_id)
        self._org(org_id, actor)
        _non_empty(case_ref, "case_ref")
        _non_empty(program_label, "program_label")
        self._require_candidate(org_id, candidate_ref, actor)
        with self._lock:
            self._check_ref_unique("workforce_case", org_id,
                                   "case_ref", case_ref)
            return self._create(
                "workforce_case", "cas-",
                {"org_id": org_id,
                 "case_ref": case_ref,
                 "candidate_ref": candidate_ref,
                 "program_label": program_label,
                 "status": "open"},
                actor, "ext_case_create")

    def close_workforce_case(self, org_id, case_id, actor):
        """Close a workforce case. Action: candidate_write.
        Only an open case can be closed."""
        self._guard(actor, "candidate_write", "ext_case_close", org_id)
        self._org(org_id, actor)
        with self._lock:
            case = self._get("workforce_case", case_id, org_id)
            if case["status"] != "open":
                raise ValidationError(
                    "case %s is %r; only an open case can be closed"
                    % (case_id, case["status"])
                )
            case["status"] = "closed"
            self._audit(actor, "ext_case_close", case_id,
                        details={"kind": "workforce_case"})
            return copy.deepcopy(case)

    def record_case_activity(self, org_id, activity_ref, case_id, kind,
                             label, actor):
        """Record a case activity: a kind label and a short label.

        Action: candidate_write. Activities are append-only and
        are recorded against open cases only. No narrative note
        text exists -- there is no parameter that could accept it.
        """
        self._guard(actor, "candidate_write", "ext_case_activity_record",
                    org_id)
        self._org(org_id, actor)
        _non_empty(activity_ref, "activity_ref")
        _one_of(kind, KNOWN_CASE_ACTIVITY_KINDS, CASE_ACTIVITY_KINDS,
                "kind")
        _non_empty(label, "label")
        with self._lock:
            case = self._get("workforce_case", case_id, org_id)
            if case["status"] != "open":
                raise ValidationError(
                    "case %s is %r; activities are recorded against "
                    "open cases only" % (case_id, case["status"])
                )
            self._check_ref_unique("case_activity", org_id,
                                   "activity_ref", activity_ref,
                                   scope_field="case_id",
                                   scope_value=case_id)
            return self._create(
                "case_activity", "act-",
                {"org_id": org_id,
                 "activity_ref": activity_ref,
                 "case_id": case_id,
                 "kind": kind,
                 "label": label},
                actor, "ext_case_activity_record")

    def list_case_activities(self, org_id, actor, case_id=None):
        """Return case activity records. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_case_activity_read", org_id)
        self._org(org_id, actor)
        return self._list("case_activity", org_id, case_id=case_id)

    def get_workforce_case(self, org_id, case_id, actor):
        """Return one case with its derived activity counts.

        Action: org_read. ``activity_count`` and
        ``activities_by_kind`` are derived at read from the case's
        activity records; the stored case record carries neither
        (pinned by test).
        """
        self._guard_read(actor, "org_read", "ext_case_read", org_id)
        self._org(org_id, actor)
        case = self._fetch("workforce_case", case_id, org_id)
        activities = self._list("case_activity", org_id, case_id=case_id)
        by_kind = {}
        for activity in activities:
            kind = activity["kind"]
            by_kind[kind] = by_kind.get(kind, 0) + 1
        view = dict(case)
        view["activity_count"] = len(activities)
        view["activities_by_kind"] = by_kind
        return view

    def list_workforce_cases(self, org_id, actor, candidate_ref=None,
                             status=None):
        """Return stored case records (no derived keys). Action: org_read."""
        self._guard_read(actor, "org_read", "ext_case_read", org_id)
        self._org(org_id, actor)
        if status is not None:
            _one_of(status, frozenset(CASE_STATUSES), CASE_STATUSES,
                    "status")
        return self._list("workforce_case", org_id,
                          candidate_ref=candidate_ref, status=status)

    # -- Employer services platform (built) ----------------------------
    # Employers here are opaque references registered inside the
    # organization (a public workforce system's employer registry,
    # distinct from the core's tenancy organizations). A service
    # request carries a kind label held as data and a guarded
    # lifecycle; completion stores the caller's outcome label
    # verbatim. The summary is deterministic counts derived at
    # read. No service is dispatched or delivered here.

    def register_employer(self, org_id, employer_ref, label, actor):
        """Register an employer reference. Action: registry_write."""
        self._guard(actor, "registry_write", "ext_employer_register", org_id)
        self._org(org_id, actor)
        _non_empty(employer_ref, "employer_ref")
        _non_empty(label, "label")
        with self._lock:
            self._check_ref_unique("employer", org_id,
                                   "employer_ref", employer_ref)
            return self._create(
                "employer", "emp-",
                {"org_id": org_id,
                 "employer_ref": employer_ref,
                 "label": label},
                actor, "ext_employer_register")

    def get_employer(self, org_id, employer_id, actor):
        """Return one employer record. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_employer_read", org_id)
        self._org(org_id, actor)
        return self._fetch("employer", employer_id, org_id)

    def list_employers(self, org_id, actor):
        """Return employer records. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_employer_read", org_id)
        self._org(org_id, actor)
        return self._list("employer", org_id)

    def create_service_request(self, org_id, request_ref, employer_id, kind,
                               actor):
        """Open an employer service request. Action: registry_write.
        The kind is a label held as data; nothing is dispatched."""
        self._guard(actor, "registry_write", "ext_service_request_create",
                    org_id)
        self._org(org_id, actor)
        _non_empty(request_ref, "request_ref")
        _one_of(kind, KNOWN_EMPLOYER_SERVICE_KINDS, EMPLOYER_SERVICE_KINDS,
                "kind")
        with self._lock:
            self._get("employer", employer_id, org_id)
            self._check_ref_unique("employer_service_request", org_id,
                                   "request_ref", request_ref)
            return self._create(
                "employer_service_request", "esr-",
                {"org_id": org_id,
                 "request_ref": request_ref,
                 "employer_id": employer_id,
                 "kind": kind,
                 "status": "open",
                 "outcome_label": None},
                actor, "ext_service_request_create")

    def _transition_service_request(self, org_id, request_id, actor,
                                    target_status, outcome_label, action):
        self._guard(actor, "registry_write", action, org_id)
        self._org(org_id, actor)
        with self._lock:
            request = self._get("employer_service_request", request_id,
                                org_id)
            if request["status"] != "open":
                raise ValidationError(
                    "service request %s is %r; only an open request can "
                    "become %s" % (request_id, request["status"],
                                   target_status)
                )
            request["status"] = target_status
            request["outcome_label"] = outcome_label
            self._audit(actor, action, request_id,
                        details={"kind": "employer_service_request"})
            return copy.deepcopy(request)

    def complete_service_request(self, org_id, request_id, outcome_label,
                                 actor):
        """Complete a service request with the caller's outcome
        label, verbatim. Action: registry_write."""
        _non_empty(outcome_label, "outcome_label")
        return self._transition_service_request(
            org_id, request_id, actor, "completed", outcome_label,
            "ext_service_request_complete")

    def cancel_service_request(self, org_id, request_id, actor):
        """Cancel an open service request. Action: registry_write."""
        return self._transition_service_request(
            org_id, request_id, actor, "cancelled", None,
            "ext_service_request_cancel")

    def list_service_requests(self, org_id, actor, employer_id=None,
                              status=None):
        """Return employer service requests. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_service_request_read",
                         org_id)
        self._org(org_id, actor)
        if status is not None:
            _one_of(status, frozenset(SERVICE_REQUEST_STATUSES),
                    SERVICE_REQUEST_STATUSES, "status")
        return self._list("employer_service_request", org_id,
                          employer_id=employer_id, status=status)

    def employer_services_summary(self, org_id, actor):
        """Derived employer-services counts for one organization.

        Action: report_read. Counts of recorded things, derived at
        read: employers, service requests by kind and by status.
        No rate or score is computed.
        """
        self._guard_read(actor, "report_read",
                         "ext_employer_summary_read", org_id)
        self._org(org_id, actor)
        employers = self._list("employer", org_id)
        requests = self._list("employer_service_request", org_id)
        by_kind = {}
        by_status = {s: 0 for s in SERVICE_REQUEST_STATUSES}
        for request in requests:
            by_kind[request["kind"]] = by_kind.get(request["kind"], 0) + 1
            by_status[request["status"]] += 1
        return {
            "org_id": org_id,
            "employer_count": len(employers),
            "service_request_count": len(requests),
            "service_requests_by_kind": by_kind,
            "service_requests_by_status": by_status,
        }

    # -- Unemployment insurance integration & administration (reference)
    # A UI claim here is a reference record: an opaque claim
    # reference bound to a participant's opaque candidate reference,
    # carrying the UI program's own status label exactly as
    # reported. Status reports are append-only records; the claim's
    # current reported status is derived at read from the newest
    # report (or the registration label when no report exists).
    # Nothing is determined, administered, or paid here, and
    # exchange receipts move no data (``reference_transport``).

    def register_ui_claim(self, org_id, claim_ref, candidate_ref,
                          reported_status_label, actor):
        """Register a UI claim reference record with the program's
        reported status label. Action: candidate_write."""
        self._guard(actor, "candidate_write", "ext_ui_claim_register",
                    org_id)
        self._org(org_id, actor)
        _non_empty(claim_ref, "claim_ref")
        _non_empty(reported_status_label, "reported_status_label")
        self._require_candidate(org_id, candidate_ref, actor)
        with self._lock:
            self._check_ref_unique("ui_claim", org_id, "claim_ref",
                                   claim_ref)
            return self._create(
                "ui_claim", "uic-",
                {"org_id": org_id,
                 "claim_ref": claim_ref,
                 "candidate_ref": candidate_ref,
                 "initial_status_label": reported_status_label,
                 "reference_stub": True,
                 "determined_here": False,
                 "benefits_paid_here": False},
                actor, "ext_ui_claim_register")

    def record_ui_claim_report(self, org_id, report_ref, claim_id,
                               reported_status_label, actor):
        """Record a UI program status report for a claim, verbatim.

        Action: candidate_write. Reports are append-only; the
        claim's current reported status derives from the newest
        one at read. The label is the program's, never a
        determination made here.
        """
        self._guard(actor, "candidate_write", "ext_ui_claim_report", org_id)
        self._org(org_id, actor)
        _non_empty(report_ref, "report_ref")
        _non_empty(reported_status_label, "reported_status_label")
        with self._lock:
            self._get("ui_claim", claim_id, org_id)
            self._check_ref_unique("ui_claim_report", org_id,
                                   "report_ref", report_ref,
                                   scope_field="claim_id",
                                   scope_value=claim_id)
            return self._create(
                "ui_claim_report", "uir-",
                {"org_id": org_id,
                 "report_ref": report_ref,
                 "claim_id": claim_id,
                 "reported_status_label": reported_status_label,
                 "reference_stub": True},
                actor, "ext_ui_claim_report")

    def get_ui_claim(self, org_id, claim_id, actor):
        """Return one UI claim with its derived current status.

        Action: org_read. ``current_reported_status`` and
        ``report_count`` are derived at read from the claim's
        report records (the registration label when no report
        exists); the stored claim record carries neither.
        """
        self._guard_read(actor, "org_read", "ext_ui_claim_read", org_id)
        self._org(org_id, actor)
        claim = self._fetch("ui_claim", claim_id, org_id)
        reports = self._list("ui_claim_report", org_id, claim_id=claim_id)
        view = dict(claim)
        if reports:
            newest = max(
                reports, key=lambda r: int(r["id"].split("-", 1)[1]))
            view["current_reported_status"] = newest[
                "reported_status_label"]
        else:
            view["current_reported_status"] = claim["initial_status_label"]
        view["report_count"] = len(reports)
        return view

    def list_ui_claims(self, org_id, actor, candidate_ref=None):
        """Return stored UI claim records (no derived keys).
        Action: org_read."""
        self._guard_read(actor, "org_read", "ext_ui_claim_read", org_id)
        self._org(org_id, actor)
        return self._list("ui_claim", org_id, candidate_ref=candidate_ref)

    def list_ui_claim_reports(self, org_id, actor, claim_id=None):
        """Return UI claim report records. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_ui_claim_report_read",
                         org_id)
        self._org(org_id, actor)
        return self._list("ui_claim_report", org_id, claim_id=claim_id)

    def record_ui_exchange(self, org_id, exchange_ref, system_ref,
                           claims_reported, determinations_reported,
                           outcome_label, actor):
        """Record a UI integration exchange receipt, as reported.

        Action: registry_write. The counts are the connected
        program system's report, stored verbatim; this build
        administered nothing and moved no data
        (``reference_transport`` is True).
        """
        self._guard(actor, "registry_write", "ext_ui_exchange_record",
                    org_id)
        self._org(org_id, actor)
        _non_empty(exchange_ref, "exchange_ref")
        _non_empty(system_ref, "system_ref")
        _nonneg_int(claims_reported, "claims_reported")
        _nonneg_int(determinations_reported, "determinations_reported")
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._check_ref_unique("ui_exchange", org_id,
                                   "exchange_ref", exchange_ref)
            return self._create(
                "ui_exchange", "uie-",
                {"org_id": org_id,
                 "exchange_ref": exchange_ref,
                 "system_ref": system_ref,
                 "claims_reported": claims_reported,
                 "determinations_reported": determinations_reported,
                 "outcome_label": outcome_label,
                 "reference_stub": True,
                 "reference_transport": True,
                 "administered_here": False},
                actor, "ext_ui_exchange_record")

    def list_ui_exchanges(self, org_id, actor):
        """Return UI exchange receipts. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_ui_exchange_read", org_id)
        self._org(org_id, actor)
        return self._list("ui_exchange", org_id)

    # -- Labor market information service (built) ----------------------
    # An LMI observation here is a recorded data point: region,
    # occupation, and period labels, a metric kind label, and an
    # integer value stored exactly as reported by its source
    # (``source_ref``, opaque). Nothing is collected from any
    # external source here. The summary is a deterministic grouping
    # derived at read -- observation counts and sums of the
    # reported values; no average, rate, or index is computed.
    # Publications are definitions held as data; distribution
    # receipts carry ``reference_transport`` True and deliver
    # nothing here.

    def record_lmi_observation(self, org_id, observation_ref, region_label,
                               occupation_label, period_label, metric_kind,
                               value_reported, source_ref, actor):
        """Record a labor-market observation as reported.

        Action: registry_write. ``value_reported`` is the source's
        integer, stored verbatim; it is data about the labor
        market as reported, never a measurement made here.
        """
        self._guard(actor, "registry_write", "ext_lmi_observation_record",
                    org_id)
        self._org(org_id, actor)
        _non_empty(observation_ref, "observation_ref")
        _non_empty(region_label, "region_label")
        _non_empty(occupation_label, "occupation_label")
        _non_empty(period_label, "period_label")
        _one_of(metric_kind, KNOWN_LMI_METRIC_KINDS, LMI_METRIC_KINDS,
                "metric_kind")
        _nonneg_int(value_reported, "value_reported")
        _non_empty(source_ref, "source_ref")
        with self._lock:
            self._check_ref_unique("lmi_observation", org_id,
                                   "observation_ref", observation_ref)
            return self._create(
                "lmi_observation", "lmi-",
                {"org_id": org_id,
                 "observation_ref": observation_ref,
                 "region_label": region_label,
                 "occupation_label": occupation_label,
                 "period_label": period_label,
                 "metric_kind": metric_kind,
                 "value_reported": value_reported,
                 "source_ref": source_ref,
                 "collected_here": False},
                actor, "ext_lmi_observation_record")

    def list_lmi_observations(self, org_id, actor, region_label=None,
                              metric_kind=None):
        """Return LMI observation records. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_lmi_observation_read",
                         org_id)
        self._org(org_id, actor)
        if metric_kind is not None:
            _one_of(metric_kind, KNOWN_LMI_METRIC_KINDS, LMI_METRIC_KINDS,
                    "metric_kind")
        return self._list("lmi_observation", org_id,
                          region_label=region_label,
                          metric_kind=metric_kind)

    def lmi_summary(self, org_id, actor):
        """Derived LMI summary for one organization.

        Action: report_read. Observations are grouped by their
        recorded (region, occupation, period, metric) labels; each
        group carries its observation count and the sum of its
        reported values, derived at read. Groups are sorted by
        their label tuple so the view is deterministic. No
        average, rate, or index is computed anywhere.
        """
        self._guard_read(actor, "report_read", "ext_lmi_summary_read",
                         org_id)
        self._org(org_id, actor)
        observations = self._list("lmi_observation", org_id)
        groups = {}
        for observation in observations:
            key = (observation["region_label"],
                   observation["occupation_label"],
                   observation["period_label"],
                   observation["metric_kind"])
            group = groups.setdefault(key, {
                "region_label": key[0],
                "occupation_label": key[1],
                "period_label": key[2],
                "metric_kind": key[3],
                "observation_count": 0,
                "value_total_reported": 0,
            })
            group["observation_count"] += 1
            group["value_total_reported"] += observation["value_reported"]
        return {
            "org_id": org_id,
            "observation_count": len(observations),
            "groups": [groups[key] for key in sorted(groups)],
        }

    def create_lmi_publication(self, org_id, publication_ref, label, actor,
                               region_label=None, metric_kind=None):
        """Define an LMI publication: a label and optional filter
        labels, held as data. Action: registry_write. Nothing is
        rendered or delivered here (``delivered_here`` is False)."""
        self._guard(actor, "registry_write", "ext_lmi_publication_create",
                    org_id)
        self._org(org_id, actor)
        _non_empty(publication_ref, "publication_ref")
        _non_empty(label, "label")
        _string_or_none(region_label, "region_label")
        if metric_kind is not None:
            _one_of(metric_kind, KNOWN_LMI_METRIC_KINDS, LMI_METRIC_KINDS,
                    "metric_kind")
        with self._lock:
            self._check_ref_unique("lmi_publication", org_id,
                                   "publication_ref", publication_ref)
            return self._create(
                "lmi_publication", "pub-",
                {"org_id": org_id,
                 "publication_ref": publication_ref,
                 "label": label,
                 "region_label": region_label,
                 "metric_kind": metric_kind,
                 "definition_only": True,
                 "delivered_here": False},
                actor, "ext_lmi_publication_create")

    def list_lmi_publications(self, org_id, actor):
        """Return LMI publication definitions. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_lmi_publication_read",
                         org_id)
        self._org(org_id, actor)
        return self._list("lmi_publication", org_id)

    def record_lmi_distribution(self, org_id, distribution_ref,
                                publication_id, recipients_reported,
                                outcome_label, actor):
        """Record an LMI distribution receipt, as reported.

        Action: registry_write. The recipient count and outcome
        label are the distributing system's report; this build
        delivered nothing (``reference_transport`` is True).
        """
        self._guard(actor, "registry_write", "ext_lmi_distribution_record",
                    org_id)
        self._org(org_id, actor)
        _non_empty(distribution_ref, "distribution_ref")
        _nonneg_int(recipients_reported, "recipients_reported")
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._get("lmi_publication", publication_id, org_id)
            self._check_ref_unique("lmi_distribution", org_id,
                                   "distribution_ref", distribution_ref)
            return self._create(
                "lmi_distribution", "dst-",
                {"org_id": org_id,
                 "distribution_ref": distribution_ref,
                 "publication_id": publication_id,
                 "recipients_reported": recipients_reported,
                 "outcome_label": outcome_label,
                 "reference_transport": True,
                 "delivered_here": False},
                actor, "ext_lmi_distribution_record")

    def list_lmi_distributions(self, org_id, actor, publication_id=None):
        """Return LMI distribution receipts. Action: org_read."""
        self._guard_read(actor, "org_read", "ext_lmi_distribution_read",
                         org_id)
        self._org(org_id, actor)
        return self._list("lmi_distribution", org_id,
                          publication_id=publication_id)
