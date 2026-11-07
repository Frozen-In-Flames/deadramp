"""Final-GAPS-batch extension surface, second unit: the
remainder-addition section of the GRC L2 group.

One new module, following the batch pattern in
``../../gaps-batch/DECISION.md`` and the second-unit mechanics of
the sibling addition units: :class:`GrcExtensionsAddition` wraps
a core :class:`grc.store.GrcStore` and adds records for the seven
Extended functions registered under the **Remainder Addition —
GRC L2 (+5 forks)** GAPS.md section (inventory idx 571–577; see
``../ADDENDUM.md`` §5). The first batch unit's module
(``extensions.py``) and every core module are untouched.

The category doctrine binds every surface here, exactly as it
binds the core and the first batch unit (see ``../UNION-SPEC.md``,
``../ADDENDUM.md`` §3, and the founding posture tests): **posture
is counts only — no computed score, rating, grade, or percentage
exists anywhere**, enforced over this surface by the same
recursive key scan (no key may contain ``score`` / ``rating`` /
``grade`` / ``percent`` — which is also why "not computed here"
boundaries are spelled ``computed_here``). Statuses, outcomes,
severities, priorities, and values a person or an external
engine reports are recorded **verbatim**, never computed.
Anything state-like or date-based is **derived at read, never
stored**.

What each entry becomes here (per-entry record in
``../BATCH-ADDITION.md``):

- **Policy lifecycle management engine** (idx 571) — policy
  lifecycle records bound to the policy's Core records form (a
  policy document held as a core evidence record, or a policy
  set held as a catalog framework, per ADDENDUM §3), plus an
  append-only stage-event stream. The current stage is derived
  at read from the event stream, never stored; an approval may
  not be recorded by the actor who registered the lifecycle
  (the core's filer-may-not-review separation, applied to
  policies). This build authors no policy text and enforces
  nothing: ``authored_here: False``, ``enforced_here: False``
  on every lifecycle record; enforcement arrives only as a
  reported stage event.
- **Agentic workflow execution engine** (idx 572) — agent
  definitions held as data (``reference_stub: True``), run
  records, and run-report records holding the agent's reported
  status verbatim (``executed_here: False``). No run executes
  anything, here or in the core: a run and its report change no
  core record.
- **AI control-narrative & assessment-response generation /
  secure AI enclave** (idx 573) — generation-request records
  bound to a core assessment, naming the reported enclave as
  data (``reference_stub: True``, ``generated_here: False``),
  and generation-report records holding the engine's reported
  outcome verbatim plus, where the generated artifact was filed,
  the reference of the core evidence record it was filed as.
  No narrative text is generated or held here, and a report
  never changes the core assessment it answers.
- **Data-integration connector engine** (idx 574) —
  connector-definition records (``reference_stub: True``,
  ``reference_transport: True``, ``connected_here: False``,
  ``synced_here: False``) and sync-receipt records holding what
  an external connector reported, counts as reported. A receipt
  imports nothing: it creates no core record of any kind.
- **IT service management suite (ITSM / ESM)** (idx 575) —
  configuration-item records keyed by opaque caller-supplied
  references (registered, never discovered:
  ``discovered_here: False``), ticket records whose current
  status is derived at read from their event stream and never
  stored, and SLA policy records holding the reported terms
  verbatim as data (``evaluated_here: False`` — no SLA clock
  runs and no attainment is computed).
- **Healthcare quality management suite** (idx 576) —
  personnel records keyed by opaque references only (no field
  can hold a name or contact detail, exactly as in the core's
  governed-system records), certification records whose
  currency (current / expired) is derived at read from the
  recorded expiry date and never stored, training records and
  maintenance records holding reported outcomes verbatim
  (``assessed_here: False`` — this build administers no
  assessment), and non-conforming event records with
  corrective-action records holding reported outcomes
  verbatim. No patient data exists anywhere in this surface;
  these are workforce quality records.
- **Connected financial & regulatory reporting / publishing
  platform** (idx 577) — report records bound to a core system
  and framework (``filed_here: False``,
  ``published_here: False``), data-point records holding a
  connected source's reported value **verbatim as a label**
  (``computed_here: False`` — values are never summed, rolled
  up, or otherwise computed over), publication records
  holding reported outcomes verbatim, and a report view
  derived at read carrying counts of records only.

Permissions ride the core's matrix unchanged; reads require
``read``. Denied attempts raise :class:`PermissionDenied` and
change nothing — at this store-level surface, auditing a denial
is the HTTP layer's responsibility, exactly as in the core.
Successful mutations are written to the core's append-only
audit log (when one is attached) under ``exta_`` action names.
Every operation validates fully before it mutates: a failed
operation consumes no id and changes nothing.
"""

import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

POLICY_SUBJECT_KINDS = ("evidence", "framework")
POLICY_STAGES = (
    "drafted",
    "in_review",
    "approved",
    "rejected",
    "enforcement_reported",
    "retired",
)
# Lifecycle transitions, keyed by the stage derived from the
# event stream so far ("registered" = no events yet). "retired"
# is terminal.
POLICY_STAGE_TRANSITIONS = {
    "registered": ("drafted",),
    "drafted": ("in_review", "retired"),
    "in_review": ("approved", "rejected"),
    "rejected": ("drafted", "retired"),
    "approved": ("enforcement_reported", "retired"),
    "enforcement_reported": ("retired",),
    "retired": (),
}
GENERATION_KINDS = ("control_narrative", "assessment_response")
CONNECTOR_KINDS = ("system_sync", "data_import", "data_export")
TICKET_KINDS = ("incident", "service_request", "change")


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


def _validate_reported_count(value, what):
    """Validate a caller-reported count: an integer >= 0.

    Booleans and floats are rejected at the boundary: a reported
    count is a whole number a reporter supplied, never a computed
    quantity.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if value < 0:
        raise ValidationError("%s must be >= 0" % (what,))
    return value


def _validate_timestamp(value, what):
    """Validate an ISO-8601 timestamp string; return it verbatim."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 timestamp string" % (what,))
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        datetime.fromisoformat(candidate)
    except ValueError:
        raise ValidationError(
            "%s must be an ISO-8601 timestamp: %r" % (what, value)
        ) from None
    return value


def _validate_date(value, what):
    """Validate an ISO calendar date string; return it verbatim."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO date string" % (what,))
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValidationError(
            "%s must be an ISO date (YYYY-MM-DD): %r" % (what, value)
        ) from None
    return value


def _coerce_as_of(as_of):
    """Coerce an as-of parameter to a :class:`datetime.date`.

    Mirrors the core's coercion: ``None`` means today (UTC).
    """
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


class GrcExtensionsAddition:
    """The remainder-addition batch surface over a core store."""

    def __init__(self, store):
        self.store = store
        self.audit = store.audit
        self._policies = {}  # id -> policy lifecycle record
        self._policy_events = {}  # id -> policy stage event record
        self._agent_definitions = {}  # id -> agent definition record
        self._agent_runs = {}  # id -> agent run record
        self._agent_run_reports = {}  # id -> agent run report record
        self._generation_requests = {}  # id -> generation request record
        self._generation_reports = {}  # id -> generation report record
        self._connectors = {}  # id -> connector definition record
        self._sync_receipts = {}  # id -> sync receipt record
        self._config_items = {}  # id -> configuration item record
        self._tickets = {}  # id -> ticket record
        self._ticket_events = {}  # id -> ticket event record
        self._sla_policies = {}  # id -> SLA policy record
        self._personnel = {}  # id -> personnel record
        self._certifications = {}  # id -> certification record
        self._training_records = {}  # id -> training record
        self._quality_events = {}  # id -> non-conforming event record
        self._corrective_actions = {}  # id -> corrective action record
        self._maintenance_records = {}  # id -> maintenance record
        self._reports = {}  # id -> connected report record
        self._data_points = {}  # id -> report data point record
        self._publications = {}  # id -> publication record
        self._counters = {
            "plc": 0, "pev": 0, "agt": 0, "arun": 0, "arep": 0,
            "gen": 0, "gnr": 0, "con": 0, "syn": 0, "ci": 0,
            "tkt": 0, "tev": 0, "sla": 0, "per": 0, "crt": 0,
            "trn": 0, "qev": 0, "cor": 0, "mnt": 0, "rpt": 0,
            "dpt": 0, "pub": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers -------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    @staticmethod
    def _require(actor, action):
        require(actor, action)

    def _require_system(self, system_ref, actor):
        """Raise NotFoundError unless ``system_ref`` is governed."""
        self.store.get_system(system_ref, actor)

    @staticmethod
    def _get(table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    # -- policy lifecycle (idx 571) ---------------------------------

    def create_policy_lifecycle(self, subject_kind, subject_ref, title,
                                actor, note=""):
        """Register a policy lifecycle over the policy's Core
        records form: ``subject_kind`` ``"evidence"`` binds a
        policy document held as a core evidence record;
        ``"framework"`` binds a policy set held as a catalog
        framework (ADDENDUM §3). This build authors no policy
        text and enforces nothing: the record carries
        ``authored_here: False`` and ``enforced_here: False``.
        Action: manage_evidence. Id prefix: plc-."""
        if subject_kind not in POLICY_SUBJECT_KINDS:
            raise ValidationError(
                "policy subject kind must be one of %s"
                % (", ".join(POLICY_SUBJECT_KINDS),)
            )
        _validate_non_empty(subject_ref, "policy subject reference")
        _validate_non_empty(title, "policy title")
        note = _validate_text(note, "policy note")
        self._require(actor, "manage_evidence")
        with self._lock:
            if subject_kind == "evidence":
                self.store.get_evidence(subject_ref, actor)
            else:
                self.store.get_framework(subject_ref, actor)
            lifecycle_id = self._next_id("plc")
            record = {
                "id": lifecycle_id,
                "subject_kind": subject_kind,
                "subject_ref": subject_ref,
                "title": title,
                "note": note,
                "authored_here": False,
                "enforced_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._policies[lifecycle_id] = record
            self._audit(actor, "exta_policy_lifecycle_create", lifecycle_id,
                        details={"subject_kind": subject_kind,
                                 "subject_ref": subject_ref})
            return dict(record)

    def get_policy_lifecycle(self, lifecycle_id, actor):
        """Return one stored policy lifecycle record (no stage is
        stored; see :meth:`policy_lifecycle_view`). Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._policies, lifecycle_id,
                                  "policy lifecycle"))

    def list_policy_lifecycles(self, actor, subject_ref=None):
        """Return policy lifecycle records, optionally filtered by
        subject, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._policies.values()
                if subject_ref is None or record["subject_ref"] == subject_ref
            ]

    def _policy_events_for(self, lifecycle_id):
        return [
            event for event in self._policy_events.values()
            if event["lifecycle_id"] == lifecycle_id
        ]

    @staticmethod
    def _derive_policy_stage(events):
        """Derive a policy lifecycle's current stage from its
        event stream: the stage of the most recent event, or
        ``"registered"`` when no event has been recorded. The
        stage is derived at read, never stored — this is the
        seam the addition's fresh negative control targets (see
        tests/README.md)."""
        if not events:
            return "registered"
        return events[-1]["stage"]

    def record_policy_stage_event(self, lifecycle_id, stage, actor,
                                  reported_outcome="", note=""):
        """Record one stage event in a policy lifecycle's stream.
        ``stage`` must be a legal next stage for the stage
        derived from the stream so far
        (:data:`POLICY_STAGE_TRANSITIONS`); an illegal transition
        is rejected whole and records nothing. ``reported_outcome``
        is stored **verbatim** (an enforcement outcome, for the
        ``enforcement_reported`` stage, arrives only this way —
        nothing is enforced here). Separation of duties, mirroring
        the core's evidence rule that the filer may not review:
        the actor who registered the lifecycle may not record its
        ``approved`` event. Action: manage_evidence.
        Id prefix: pev-."""
        if stage not in POLICY_STAGES:
            raise ValidationError(
                "policy stage must be one of %s" % (", ".join(POLICY_STAGES),)
            )
        reported_outcome = _validate_text(
            reported_outcome, "reported outcome")
        note = _validate_text(note, "stage event note")
        self._require(actor, "manage_evidence")
        with self._lock:
            lifecycle = self._get(self._policies, lifecycle_id,
                                  "policy lifecycle")
            current = self._derive_policy_stage(
                self._policy_events_for(lifecycle_id))
            if stage not in POLICY_STAGE_TRANSITIONS[current]:
                raise ValidationError(
                    "policy stage %r cannot follow %r" % (stage, current))
            if (stage == "approved"
                    and actor_name(actor) == lifecycle["recorded_by"]):
                raise PermissionDenied(
                    "the actor who registered a policy lifecycle may "
                    "not record its approval")
            event_id = self._next_id("pev")
            record = {
                "id": event_id,
                "lifecycle_id": lifecycle_id,
                "stage": stage,
                "reported_outcome": reported_outcome,
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._policy_events[event_id] = record
            self._audit(actor, "exta_policy_stage_event_record", event_id,
                        details={"lifecycle_id": lifecycle_id,
                                 "stage": stage})
            return dict(record)

    def list_policy_stage_events(self, actor, lifecycle_id=None):
        """Return policy stage-event records, optionally filtered
        by lifecycle, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._policy_events.values()
                if lifecycle_id is None
                or record["lifecycle_id"] == lifecycle_id
            ]

    def policy_lifecycle_view(self, lifecycle_id, actor):
        """Return a policy lifecycle record plus its stage derived
        at read from the event stream (``current_stage``) and the
        stream's length (``event_count``). The stored record
        itself carries no stage. Action: read."""
        self._require(actor, "read")
        with self._lock:
            record = dict(self._get(self._policies, lifecycle_id,
                                    "policy lifecycle"))
            events = self._policy_events_for(lifecycle_id)
            record["current_stage"] = self._derive_policy_stage(events)
            record["event_count"] = len(events)
            return record

    # -- agentic workflow execution (idx 572) ------------------------

    def register_agent_definition(self, agent_label, system_ref,
                                  workflow_label, actor, note=""):
        """Register a definition of an agentic workflow an
        external engine is reported to execute. The definition is
        held as data only: the record carries
        ``reference_stub: True`` and ``executed_here: False``.
        Action: manage_assessments. Id prefix: agt-."""
        _validate_non_empty(agent_label, "agent label")
        _validate_non_empty(system_ref, "system reference")
        _validate_non_empty(workflow_label, "workflow label")
        note = _validate_text(note, "agent note")
        self._require(actor, "manage_assessments")
        with self._lock:
            self._require_system(system_ref, actor)
            definition_id = self._next_id("agt")
            record = {
                "id": definition_id,
                "agent_label": agent_label,
                "system_ref": system_ref,
                "workflow_label": workflow_label,
                "note": note,
                "reference_stub": True,
                "executed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._agent_definitions[definition_id] = record
            self._audit(actor, "exta_agent_definition_create", definition_id,
                        details={"system_ref": system_ref})
            return dict(record)

    def get_agent_definition(self, definition_id, actor):
        """Return one agent-definition record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._agent_definitions, definition_id,
                                  "agent definition"))

    def list_agent_definitions(self, actor, system_ref=None):
        """Return agent-definition records, optionally filtered by
        system, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._agent_definitions.values()
                if system_ref is None or record["system_ref"] == system_ref
            ]

    def create_agent_run(self, definition_id, actor):
        """Register a run an external agentic engine is reported
        to have started against an agent definition. Registering
        a run executes nothing: the record carries
        ``reference_stub: True`` and ``executed_here: False``.
        Action: manage_assessments. Id prefix: arun-."""
        _validate_non_empty(definition_id, "agent definition id")
        self._require(actor, "manage_assessments")
        with self._lock:
            definition = self._get(self._agent_definitions, definition_id,
                                   "agent definition")
            run_id = self._next_id("arun")
            record = {
                "id": run_id,
                "definition_id": definition_id,
                "system_ref": definition["system_ref"],
                "reference_stub": True,
                "executed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._agent_runs[run_id] = record
            self._audit(actor, "exta_agent_run_create", run_id,
                        details={"definition_id": definition_id})
            return dict(record)

    def get_agent_run(self, run_id, actor):
        """Return one agent-run record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._agent_runs, run_id, "agent run"))

    def list_agent_runs(self, actor, definition_id=None):
        """Return agent-run records, optionally filtered by
        definition, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._agent_runs.values()
                if definition_id is None
                or record["definition_id"] == definition_id
            ]

    def record_agent_run_report(self, run_id, reported_status, actor,
                                reported_utc=None, note=""):
        """Record the outcome an external agentic engine reported
        for a run. ``reported_status`` is stored **verbatim**.
        Recording a report executes nothing and changes nothing
        in the core: agent outcomes land in this surface's
        records only, never as core findings, results, or
        assessment records. Action: record_results.
        Id prefix: arep-."""
        _validate_non_empty(reported_status, "reported status")
        note = _validate_text(note, "report note")
        if reported_utc is not None:
            reported_utc = _validate_timestamp(reported_utc, "reported timestamp")
        self._require(actor, "record_results")
        with self._lock:
            run = self._get(self._agent_runs, run_id, "agent run")
            report_id = self._next_id("arep")
            record = {
                "id": report_id,
                "run_id": run_id,
                "definition_id": run["definition_id"],
                "reported_status": reported_status,
                "reported_utc": reported_utc if reported_utc is not None else _utc_now(),
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._agent_run_reports[report_id] = record
            self._audit(actor, "exta_agent_run_report_record", report_id,
                        details={"run_id": run_id})
            return dict(record)

    def list_agent_run_reports(self, actor, run_id=None):
        """Return agent-run-report records, optionally filtered by
        run, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._agent_run_reports.values()
                if run_id is None or record["run_id"] == run_id
            ]

    # -- AI narrative / response generation (idx 573) ----------------

    def create_generation_request(self, assessment_id, narrative_kind,
                                  enclave_label, actor, note=""):
        """Register a request for an external AI engine to
        generate a control narrative or an assessment response
        for a core assessment. ``enclave_label`` names, as data,
        the secure enclave the engine is reported to run in; the
        enclave itself is the fork's platform (PLATFORM-LAYER.md
        decision 6) and is not operated here. This build
        generates no text: the record carries
        ``reference_stub: True`` and ``generated_here: False``.
        Action: manage_assessments. Id prefix: gen-."""
        if narrative_kind not in GENERATION_KINDS:
            raise ValidationError(
                "generation kind must be one of %s"
                % (", ".join(GENERATION_KINDS),)
            )
        _validate_non_empty(assessment_id, "assessment id")
        _validate_non_empty(enclave_label, "enclave label")
        note = _validate_text(note, "request note")
        self._require(actor, "manage_assessments")
        with self._lock:
            assessment = self.store.get_assessment(assessment_id, actor)
            request_id = self._next_id("gen")
            record = {
                "id": request_id,
                "assessment_id": assessment_id,
                "system_ref": assessment["system_ref"],
                "narrative_kind": narrative_kind,
                "enclave_label": enclave_label,
                "note": note,
                "reference_stub": True,
                "generated_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._generation_requests[request_id] = record
            self._audit(actor, "exta_generation_request_create", request_id,
                        details={"assessment_id": assessment_id})
            return dict(record)

    def get_generation_request(self, request_id, actor):
        """Return one generation-request record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._generation_requests, request_id,
                                  "generation request"))

    def list_generation_requests(self, actor, assessment_id=None):
        """Return generation-request records, optionally filtered
        by assessment, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._generation_requests.values()
                if assessment_id is None
                or record["assessment_id"] == assessment_id
            ]

    def record_generation_report(self, request_id, reported_status, actor,
                                 filed_evidence_id=None, reported_utc=None,
                                 note=""):
        """Record the outcome an external AI generation engine
        reported for a generation request. ``reported_status`` is
        stored **verbatim**. Where the generated artifact was
        filed into the core evidence registry, ``filed_evidence_id``
        references that existing core evidence record (validated
        to exist; the report files nothing itself). Recording a
        report changes nothing in the core: the assessment the
        narrative answers keeps the result its assessor recorded,
        and no narrative text is held here. Action:
        record_results. Id prefix: gnr-."""
        _validate_non_empty(reported_status, "reported status")
        note = _validate_text(note, "report note")
        if reported_utc is not None:
            reported_utc = _validate_timestamp(reported_utc, "reported timestamp")
        self._require(actor, "record_results")
        with self._lock:
            request = self._get(self._generation_requests, request_id,
                                "generation request")
            if filed_evidence_id is not None:
                _validate_non_empty(filed_evidence_id, "filed evidence id")
                self.store.get_evidence(filed_evidence_id, actor)
            report_id = self._next_id("gnr")
            record = {
                "id": report_id,
                "request_id": request_id,
                "assessment_id": request["assessment_id"],
                "reported_status": reported_status,
                "filed_evidence_id": filed_evidence_id,
                "reported_utc": reported_utc if reported_utc is not None else _utc_now(),
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._generation_reports[report_id] = record
            self._audit(actor, "exta_generation_report_record", report_id,
                        details={"request_id": request_id})
            return dict(record)

    def list_generation_reports(self, actor, request_id=None):
        """Return generation-report records, optionally filtered
        by request, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._generation_reports.values()
                if request_id is None or record["request_id"] == request_id
            ]

    # -- data-integration connectors (idx 574) -----------------------

    def register_connector(self, kind, system_ref, label, actor, note=""):
        """Register a definition of a data-integration connector
        an external engine operates between systems. This build
        connects to nothing and moves no data: the record carries
        ``reference_stub: True``, ``reference_transport: True``,
        ``connected_here: False``, and ``synced_here: False``.
        Action: manage_systems. Id prefix: con-."""
        if kind not in CONNECTOR_KINDS:
            raise ValidationError(
                "connector kind must be one of %s"
                % (", ".join(CONNECTOR_KINDS),)
            )
        _validate_non_empty(system_ref, "system reference")
        _validate_non_empty(label, "connector label")
        note = _validate_text(note, "connector note")
        self._require(actor, "manage_systems")
        with self._lock:
            self._require_system(system_ref, actor)
            connector_id = self._next_id("con")
            record = {
                "id": connector_id,
                "kind": kind,
                "system_ref": system_ref,
                "label": label,
                "note": note,
                "reference_stub": True,
                "reference_transport": True,
                "connected_here": False,
                "synced_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._connectors[connector_id] = record
            self._audit(actor, "exta_connector_create", connector_id,
                        details={"kind": kind, "system_ref": system_ref})
            return dict(record)

    def get_connector(self, connector_id, actor):
        """Return one connector-definition record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._connectors, connector_id, "connector"))

    def list_connectors(self, actor, system_ref=None):
        """Return connector-definition records, optionally
        filtered by system, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._connectors.values()
                if system_ref is None or record["system_ref"] == system_ref
            ]

    def record_sync_receipt(self, connector_id, reported_status, actor,
                            records_reported=0, reported_utc=None, note=""):
        """Record what an external connector reported for one
        sync: the status **verbatim** and the record count **as
        reported** (``records_reported``; booleans, floats, and
        negative counts are rejected at the boundary). A receipt
        imports nothing: it creates no core system, evidence,
        finding, or result — the records a sync moved live in
        the systems it connected, not in this registry.
        Action: record_results. Id prefix: syn-."""
        _validate_non_empty(reported_status, "reported status")
        records_reported = _validate_reported_count(
            records_reported, "records reported")
        note = _validate_text(note, "receipt note")
        if reported_utc is not None:
            reported_utc = _validate_timestamp(reported_utc, "reported timestamp")
        self._require(actor, "record_results")
        with self._lock:
            connector = self._get(self._connectors, connector_id, "connector")
            receipt_id = self._next_id("syn")
            record = {
                "id": receipt_id,
                "connector_id": connector_id,
                "system_ref": connector["system_ref"],
                "reported_status": reported_status,
                "records_reported": records_reported,
                "reported_utc": reported_utc if reported_utc is not None else _utc_now(),
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._sync_receipts[receipt_id] = record
            self._audit(actor, "exta_sync_receipt_record", receipt_id,
                        details={"connector_id": connector_id})
            return dict(record)

    def list_sync_receipts(self, actor, connector_id=None):
        """Return sync-receipt records, optionally filtered by
        connector, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._sync_receipts.values()
                if connector_id is None
                or record["connector_id"] == connector_id
            ]

    # -- ITSM / ESM suite records (idx 575) ---------------------------

    def register_config_item(self, ref, label, kind_label, actor,
                             system_ref=None, note=""):
        """Register a configuration item under an opaque
        caller-supplied reference (the CMDB records form). Items
        are registered by a person, never discovered by a scan:
        the record carries ``discovered_here: False``.
        ``system_ref``, when given, links the item to a governed
        system and is validated to exist. A reference may be
        registered once. Action: manage_systems. Id prefix: ci-."""
        _validate_non_empty(ref, "configuration item reference")
        _validate_non_empty(label, "configuration item label")
        _validate_non_empty(kind_label, "configuration item kind")
        note = _validate_text(note, "configuration item note")
        self._require(actor, "manage_systems")
        with self._lock:
            if system_ref is not None:
                _validate_non_empty(system_ref, "system reference")
                self._require_system(system_ref, actor)
            for existing in self._config_items.values():
                if existing["ref"] == ref:
                    raise ValidationError(
                        "configuration item reference already registered: "
                        "%r" % (ref,))
            item_id = self._next_id("ci")
            record = {
                "id": item_id,
                "ref": ref,
                "label": label,
                "kind_label": kind_label,
                "system_ref": system_ref,
                "note": note,
                "discovered_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._config_items[item_id] = record
            self._audit(actor, "exta_config_item_create", item_id,
                        details={"ref": ref})
            return dict(record)

    def get_config_item(self, item_id, actor):
        """Return one configuration-item record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._config_items, item_id,
                                  "configuration item"))

    def list_config_items(self, actor, system_ref=None):
        """Return configuration-item records, optionally filtered
        by governed system, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._config_items.values()
                if system_ref is None or record["system_ref"] == system_ref
            ]

    def create_ticket(self, kind, title, actor, ci_id=None,
                      system_ref=None, reported_priority="", note=""):
        """Open a service ticket record (incident, service
        request, or change). ``reported_priority`` is a label a
        reporter supplied, stored **verbatim** — this build
        assigns no priority. The stored record carries **no
        status**: a ticket's current status is derived at read
        from its event stream (see :meth:`ticket_view`).
        Action: manage_findings. Id prefix: tkt-."""
        if kind not in TICKET_KINDS:
            raise ValidationError(
                "ticket kind must be one of %s" % (", ".join(TICKET_KINDS),)
            )
        _validate_non_empty(title, "ticket title")
        reported_priority = _validate_text(
            reported_priority, "reported priority")
        note = _validate_text(note, "ticket note")
        self._require(actor, "manage_findings")
        with self._lock:
            if ci_id is not None:
                self._get(self._config_items, ci_id, "configuration item")
            if system_ref is not None:
                _validate_non_empty(system_ref, "system reference")
                self._require_system(system_ref, actor)
            ticket_id = self._next_id("tkt")
            record = {
                "id": ticket_id,
                "kind": kind,
                "title": title,
                "ci_id": ci_id,
                "system_ref": system_ref,
                "reported_priority": reported_priority,
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._tickets[ticket_id] = record
            self._audit(actor, "exta_ticket_create", ticket_id,
                        details={"kind": kind})
            return dict(record)

    def get_ticket(self, ticket_id, actor):
        """Return one stored ticket record (no status is stored;
        see :meth:`ticket_view`). Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._tickets, ticket_id, "ticket"))

    def list_tickets(self, actor, kind=None, system_ref=None):
        """Return ticket records, optionally filtered by kind
        and/or system, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._tickets.values()
                if (kind is None or record["kind"] == kind)
                and (system_ref is None or record["system_ref"] == system_ref)
            ]

    def _ticket_events_for(self, ticket_id):
        return [
            event for event in self._ticket_events.values()
            if event["ticket_id"] == ticket_id
        ]

    @staticmethod
    def _derive_ticket_status(events):
        """Derive a ticket's current status from its event
        stream: the status label of the most recent event,
        recorded verbatim, or ``"recorded"`` when no event has
        been recorded. Derived at read, never stored."""
        if not events:
            return "recorded"
        return events[-1]["status_label"]

    def record_ticket_event(self, ticket_id, status_label, actor, note=""):
        """Record one status event against a ticket.
        ``status_label`` is stored **verbatim** — the working
        status a person or an external service desk reported;
        this build runs no ticket workflow. Action:
        manage_findings. Id prefix: tev-."""
        _validate_non_empty(status_label, "ticket status label")
        note = _validate_text(note, "ticket event note")
        self._require(actor, "manage_findings")
        with self._lock:
            self._get(self._tickets, ticket_id, "ticket")
            event_id = self._next_id("tev")
            record = {
                "id": event_id,
                "ticket_id": ticket_id,
                "status_label": status_label,
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._ticket_events[event_id] = record
            self._audit(actor, "exta_ticket_event_record", event_id,
                        details={"ticket_id": ticket_id})
            return dict(record)

    def list_ticket_events(self, actor, ticket_id=None):
        """Return ticket-event records, optionally filtered by
        ticket, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._ticket_events.values()
                if ticket_id is None or record["ticket_id"] == ticket_id
            ]

    def ticket_view(self, ticket_id, actor):
        """Return a ticket record plus its status derived at read
        from the event stream (``current_status``) and the
        stream's length (``event_count``). The stored record
        itself carries no status. Action: read."""
        self._require(actor, "read")
        with self._lock:
            record = dict(self._get(self._tickets, ticket_id, "ticket"))
            events = self._ticket_events_for(ticket_id)
            record["current_status"] = self._derive_ticket_status(events)
            record["event_count"] = len(events)
            return record

    def register_sla_policy(self, label, terms_label, actor,
                            ticket_kind=None, note=""):
        """Register an SLA policy as data: the terms a service
        agreement states, held **verbatim** as a label (for
        example "respond within 4 business hours, as reported").
        No SLA clock runs here and no attainment is computed or
        derived: the record carries ``evaluated_here: False``.
        Action: manage_systems. Id prefix: sla-."""
        _validate_non_empty(label, "SLA policy label")
        _validate_non_empty(terms_label, "SLA terms label")
        if ticket_kind is not None and ticket_kind not in TICKET_KINDS:
            raise ValidationError(
                "ticket kind must be one of %s" % (", ".join(TICKET_KINDS),)
            )
        note = _validate_text(note, "SLA policy note")
        self._require(actor, "manage_systems")
        with self._lock:
            policy_id = self._next_id("sla")
            record = {
                "id": policy_id,
                "label": label,
                "terms_label": terms_label,
                "ticket_kind": ticket_kind,
                "note": note,
                "evaluated_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._sla_policies[policy_id] = record
            self._audit(actor, "exta_sla_policy_create", policy_id,
                        details={"label": label})
            return dict(record)

    def get_sla_policy(self, policy_id, actor):
        """Return one SLA-policy record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._sla_policies, policy_id, "SLA policy"))

    def list_sla_policies(self, actor):
        """Return SLA-policy records in recording order.
        Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [dict(record) for record in self._sla_policies.values()]

    # -- healthcare quality management records (idx 576) --------------

    def register_personnel(self, person_ref, role_label, actor, note=""):
        """Register a workforce personnel record keyed by an
        opaque caller-supplied reference. No field on the record
        can hold a name, contact detail, or patient datum — the
        reference is the identity, exactly as in the core's
        governed-system records. A reference may be registered
        once. Action: manage_systems. Id prefix: per-."""
        _validate_non_empty(person_ref, "personnel reference")
        _validate_non_empty(role_label, "personnel role label")
        note = _validate_text(note, "personnel note")
        self._require(actor, "manage_systems")
        with self._lock:
            for existing in self._personnel.values():
                if existing["person_ref"] == person_ref:
                    raise ValidationError(
                        "personnel reference already registered: %r"
                        % (person_ref,))
            personnel_id = self._next_id("per")
            record = {
                "id": personnel_id,
                "person_ref": person_ref,
                "role_label": role_label,
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._personnel[personnel_id] = record
            self._audit(actor, "exta_personnel_create", personnel_id,
                        details={"person_ref": person_ref})
            return dict(record)

    def get_personnel(self, personnel_id, actor):
        """Return one personnel record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._personnel, personnel_id, "personnel"))

    def list_personnel(self, actor):
        """Return personnel records in recording order.
        Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [dict(record) for record in self._personnel.values()]

    def record_certification(self, personnel_id, credential_label,
                             issuer_label, expires_on, actor, note=""):
        """Record a certification held by a personnel record:
        the credential and issuer labels and the expiry date,
        all as recorded. Currency is **not** stored — it is
        derived at read from the expiry date (see
        :meth:`certification_view`). This build administers no
        examination and assesses no competency:
        ``assessed_here: False``. Action: manage_systems.
        Id prefix: crt-."""
        _validate_non_empty(credential_label, "credential label")
        _validate_non_empty(issuer_label, "issuer label")
        expires_on = _validate_date(expires_on, "certification expiry date")
        note = _validate_text(note, "certification note")
        self._require(actor, "manage_systems")
        with self._lock:
            self._get(self._personnel, personnel_id, "personnel")
            cert_id = self._next_id("crt")
            record = {
                "id": cert_id,
                "personnel_id": personnel_id,
                "credential_label": credential_label,
                "issuer_label": issuer_label,
                "expires_on": expires_on,
                "note": note,
                "assessed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._certifications[cert_id] = record
            self._audit(actor, "exta_certification_record", cert_id,
                        details={"personnel_id": personnel_id})
            return dict(record)

    def list_certifications(self, actor, personnel_id=None):
        """Return certification records, optionally filtered by
        personnel, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._certifications.values()
                if personnel_id is None
                or record["personnel_id"] == personnel_id
            ]

    @staticmethod
    def _derive_certification_currency(record, as_of_date):
        """Derive a certification's currency at a date:
        ``"current"`` on or before its recorded expiry date,
        ``"expired"`` after it. Derived at read, never stored."""
        expiry = date.fromisoformat(record["expires_on"])
        return "expired" if as_of_date > expiry else "current"

    def certification_view(self, cert_id, actor, as_of=None):
        """Return a certification record plus its currency
        derived at read (``currency``) against ``as_of`` (today
        UTC when omitted). The stored record carries no
        currency. Action: read."""
        self._require(actor, "read")
        with self._lock:
            record = dict(self._get(self._certifications, cert_id,
                                    "certification"))
            record["currency"] = self._derive_certification_currency(
                record, _coerce_as_of(as_of))
            return record

    def record_training(self, personnel_id, course_label, reported_outcome,
                        actor, reported_utc=None, note=""):
        """Record a training / continuing-education outcome for a
        personnel record. ``reported_outcome`` is stored
        **verbatim** — the outcome the training provider or
        assessor reported; this build delivers no course and
        assesses no competency: ``assessed_here: False``.
        Action: record_results. Id prefix: trn-."""
        _validate_non_empty(course_label, "course label")
        _validate_non_empty(reported_outcome, "reported outcome")
        note = _validate_text(note, "training note")
        if reported_utc is not None:
            reported_utc = _validate_timestamp(reported_utc, "reported timestamp")
        self._require(actor, "record_results")
        with self._lock:
            self._get(self._personnel, personnel_id, "personnel")
            record_id = self._next_id("trn")
            record = {
                "id": record_id,
                "personnel_id": personnel_id,
                "course_label": course_label,
                "reported_outcome": reported_outcome,
                "reported_utc": reported_utc if reported_utc is not None else _utc_now(),
                "note": note,
                "assessed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._training_records[record_id] = record
            self._audit(actor, "exta_training_record", record_id,
                        details={"personnel_id": personnel_id})
            return dict(record)

    def list_training_records(self, actor, personnel_id=None):
        """Return training records, optionally filtered by
        personnel, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._training_records.values()
                if personnel_id is None
                or record["personnel_id"] == personnel_id
            ]

    def record_quality_event(self, kind_label, title, actor,
                             reported_severity="", personnel_id=None,
                             system_ref=None, note=""):
        """Record a non-conforming / quality event.
        ``reported_severity`` is a label a reporter supplied,
        stored **verbatim** — this build triages nothing and
        computes no severity. Action: manage_findings.
        Id prefix: qev-."""
        _validate_non_empty(kind_label, "quality event kind")
        _validate_non_empty(title, "quality event title")
        reported_severity = _validate_text(
            reported_severity, "reported severity")
        note = _validate_text(note, "quality event note")
        self._require(actor, "manage_findings")
        with self._lock:
            if personnel_id is not None:
                self._get(self._personnel, personnel_id, "personnel")
            if system_ref is not None:
                _validate_non_empty(system_ref, "system reference")
                self._require_system(system_ref, actor)
            event_id = self._next_id("qev")
            record = {
                "id": event_id,
                "kind_label": kind_label,
                "title": title,
                "reported_severity": reported_severity,
                "personnel_id": personnel_id,
                "system_ref": system_ref,
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._quality_events[event_id] = record
            self._audit(actor, "exta_quality_event_create", event_id,
                        details={"kind_label": kind_label})
            return dict(record)

    def get_quality_event(self, event_id, actor):
        """Return one quality-event record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._quality_events, event_id,
                                  "quality event"))

    def list_quality_events(self, actor, personnel_id=None):
        """Return quality-event records, optionally filtered by
        personnel, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._quality_events.values()
                if personnel_id is None
                or record["personnel_id"] == personnel_id
            ]

    def record_corrective_action(self, event_id, reported_outcome, actor,
                                 note=""):
        """Record a corrective action taken against a quality
        event. ``reported_outcome`` is stored **verbatim** — the
        outcome the action's owner reported; this build performs
        no corrective action. Action: manage_findings.
        Id prefix: cor-."""
        _validate_non_empty(reported_outcome, "reported outcome")
        note = _validate_text(note, "corrective action note")
        self._require(actor, "manage_findings")
        with self._lock:
            self._get(self._quality_events, event_id, "quality event")
            action_id = self._next_id("cor")
            record = {
                "id": action_id,
                "event_id": event_id,
                "reported_outcome": reported_outcome,
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._corrective_actions[action_id] = record
            self._audit(actor, "exta_corrective_action_record", action_id,
                        details={"event_id": event_id})
            return dict(record)

    def list_corrective_actions(self, actor, event_id=None):
        """Return corrective-action records, optionally filtered
        by event, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._corrective_actions.values()
                if event_id is None or record["event_id"] == event_id
            ]

    def record_maintenance(self, instrument_ref, label, reported_outcome,
                           actor, performed_on=None, note=""):
        """Record an instrument-maintenance event against an
        opaque instrument reference. ``reported_outcome`` is
        stored **verbatim** — the outcome the maintainer
        reported; this build services no instrument.
        ``performed_on``, when given, is the ISO date the work
        was reported performed. Action: record_results.
        Id prefix: mnt-."""
        _validate_non_empty(instrument_ref, "instrument reference")
        _validate_non_empty(label, "maintenance label")
        _validate_non_empty(reported_outcome, "reported outcome")
        if performed_on is not None:
            performed_on = _validate_date(performed_on, "performed date")
        note = _validate_text(note, "maintenance note")
        self._require(actor, "record_results")
        with self._lock:
            record_id = self._next_id("mnt")
            record = {
                "id": record_id,
                "instrument_ref": instrument_ref,
                "label": label,
                "reported_outcome": reported_outcome,
                "performed_on": performed_on,
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._maintenance_records[record_id] = record
            self._audit(actor, "exta_maintenance_record", record_id,
                        details={"instrument_ref": instrument_ref})
            return dict(record)

    def list_maintenance_records(self, actor, instrument_ref=None):
        """Return maintenance records, optionally filtered by
        instrument reference, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._maintenance_records.values()
                if instrument_ref is None
                or record["instrument_ref"] == instrument_ref
            ]

    # -- connected reporting / publishing records (idx 577) -----------

    def create_report(self, system_ref, framework_id, period_label, title,
                      actor, note=""):
        """Register a connected financial / regulatory report
        against a governed system and framework for a reporting
        period (``period_label`` held verbatim as data). This
        build files and publishes nothing: the record carries
        ``filed_here: False`` and ``published_here: False``.
        Action: manage_assessments. Id prefix: rpt-."""
        _validate_non_empty(system_ref, "system reference")
        _validate_non_empty(framework_id, "framework id")
        _validate_non_empty(period_label, "reporting period label")
        _validate_non_empty(title, "report title")
        note = _validate_text(note, "report note")
        self._require(actor, "manage_assessments")
        with self._lock:
            self._require_system(system_ref, actor)
            self.store.get_framework(framework_id, actor)
            report_id = self._next_id("rpt")
            record = {
                "id": report_id,
                "system_ref": system_ref,
                "framework_id": framework_id,
                "period_label": period_label,
                "title": title,
                "note": note,
                "filed_here": False,
                "published_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._reports[report_id] = record
            self._audit(actor, "exta_report_create", report_id,
                        details={"system_ref": system_ref,
                                 "framework_id": framework_id})
            return dict(record)

    def get_report(self, report_id, actor):
        """Return one stored report record (counts live only on
        the derived view). Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._reports, report_id, "report"))

    def list_reports(self, actor, system_ref=None):
        """Return report records, optionally filtered by system,
        in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._reports.values()
                if system_ref is None or record["system_ref"] == system_ref
            ]

    def record_data_point(self, report_id, source_ref, value_label, actor,
                          note=""):
        """Record one connected data point on a report: the value
        a connected source reported, stored **verbatim as a
        label** (``value_label``), with ``source_ref`` naming the
        connected source it arrived from, as data. Values are
        never parsed, summed, or rolled up:
        ``computed_here: False``. Action: record_results.
        Id prefix: dpt-."""
        _validate_non_empty(source_ref, "data point source reference")
        _validate_non_empty(value_label, "data point value label")
        note = _validate_text(note, "data point note")
        self._require(actor, "record_results")
        with self._lock:
            self._get(self._reports, report_id, "report")
            point_id = self._next_id("dpt")
            record = {
                "id": point_id,
                "report_id": report_id,
                "source_ref": source_ref,
                "value_label": value_label,
                "note": note,
                "computed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._data_points[point_id] = record
            self._audit(actor, "exta_data_point_record", point_id,
                        details={"report_id": report_id})
            return dict(record)

    def list_data_points(self, actor, report_id=None):
        """Return data-point records, optionally filtered by
        report, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._data_points.values()
                if report_id is None or record["report_id"] == report_id
            ]

    def record_publication(self, report_id, reported_outcome, actor,
                           channel_label="", reported_utc=None, note=""):
        """Record a publication outcome for a report.
        ``reported_outcome`` is stored **verbatim** — where and
        when an external publishing platform reported the report
        published; this build publishes nothing:
        ``published_here: False`` on the record. Action:
        record_results. Id prefix: pub-."""
        _validate_non_empty(reported_outcome, "reported outcome")
        channel_label = _validate_text(channel_label, "channel label")
        note = _validate_text(note, "publication note")
        if reported_utc is not None:
            reported_utc = _validate_timestamp(reported_utc, "reported timestamp")
        self._require(actor, "record_results")
        with self._lock:
            self._get(self._reports, report_id, "report")
            publication_id = self._next_id("pub")
            record = {
                "id": publication_id,
                "report_id": report_id,
                "reported_outcome": reported_outcome,
                "channel_label": channel_label,
                "reported_utc": reported_utc if reported_utc is not None else _utc_now(),
                "note": note,
                "published_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._publications[publication_id] = record
            self._audit(actor, "exta_publication_record", publication_id,
                        details={"report_id": report_id})
            return dict(record)

    def list_publications(self, actor, report_id=None):
        """Return publication records, optionally filtered by
        report, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._publications.values()
                if report_id is None or record["report_id"] == report_id
            ]

    def report_view(self, report_id, actor):
        """Return a report record plus figures derived at read:
        counts of its data points (total and by source reference)
        and of its publication records. Counts of records only —
        data-point values are labels and are never summed.
        Action: read."""
        self._require(actor, "read")
        with self._lock:
            record = dict(self._get(self._reports, report_id, "report"))
            points = [
                point for point in self._data_points.values()
                if point["report_id"] == report_id
            ]
            by_source = {}
            for point in points:
                key = point["source_ref"]
                by_source[key] = by_source.get(key, 0) + 1
            record["data_point_count"] = len(points)
            record["data_points_by_source"] = by_source
            record["publication_count"] = len([
                pub for pub in self._publications.values()
                if pub["report_id"] == report_id
            ])
            return record

    # -- addition summary (counts only) -------------------------------

    def addition_summary(self, actor):
        """Return counts over the addition surface, computed on
        read: totals and counts by recorded label for each record
        kind. Counts of records and of recorded labels only — no
        computed value of any kind. Writes no audit entry.
        Action: read."""
        self._require(actor, "read")
        with self._lock:

            def by(records, field):
                counts = {}
                for record in records:
                    key = record[field]
                    counts[key] = counts.get(key, 0) + 1
                return counts

            policies = list(self._policies.values())
            tickets = list(self._tickets.values())
            return {
                "policy_lifecycles": {
                    "total": len(policies),
                    "by_subject_kind": by(policies, "subject_kind"),
                    "by_current_stage": by(
                        [self.policy_lifecycle_view(p["id"], actor)
                         for p in policies], "current_stage"),
                },
                "policy_stage_events": {"total": len(self._policy_events)},
                "agent_definitions": {"total": len(self._agent_definitions)},
                "agent_runs": {"total": len(self._agent_runs)},
                "agent_run_reports": {
                    "total": len(self._agent_run_reports),
                    "by_reported_status": by(
                        self._agent_run_reports.values(), "reported_status"),
                },
                "generation_requests": {
                    "total": len(self._generation_requests),
                    "by_kind": by(
                        self._generation_requests.values(), "narrative_kind"),
                },
                "generation_reports": {
                    "total": len(self._generation_reports),
                    "by_reported_status": by(
                        self._generation_reports.values(), "reported_status"),
                },
                "connectors": {
                    "total": len(self._connectors),
                    "by_kind": by(self._connectors.values(), "kind"),
                },
                "sync_receipts": {
                    "total": len(self._sync_receipts),
                    "records_reported_total": sum(
                        record["records_reported"]
                        for record in self._sync_receipts.values()),
                },
                "config_items": {"total": len(self._config_items)},
                "tickets": {
                    "total": len(tickets),
                    "by_kind": by(tickets, "kind"),
                },
                "ticket_events": {"total": len(self._ticket_events)},
                "sla_policies": {"total": len(self._sla_policies)},
                "personnel": {"total": len(self._personnel)},
                "certifications": {"total": len(self._certifications)},
                "training_records": {"total": len(self._training_records)},
                "quality_events": {
                    "total": len(self._quality_events),
                    "by_kind": by(self._quality_events.values(), "kind_label"),
                },
                "corrective_actions": {"total": len(self._corrective_actions)},
                "maintenance_records": {
                    "total": len(self._maintenance_records)},
                "reports": {"total": len(self._reports)},
                "data_points": {"total": len(self._data_points)},
                "publications": {"total": len(self._publications)},
            }
