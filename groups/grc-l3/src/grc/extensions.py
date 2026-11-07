"""Final GAPS batch extensions for the GRC L3-adjacent group.

One new module, per the batch pattern (gaps-batch/DECISION.md):
:class:`GrcExtensions` wraps the core :class:`~grc.store.GrcStore`
and adds the records surfaces that close this group's registered
Extended entries (GAPS.md section "Singleton 44 — GRC L3-adjacent
(1 fork)"). The core modules are untouched and byte-identical.

The category doctrine binds every surface here, exactly as it binds
the Core:

- **No computed score, rating, grade, or prediction value anywhere.**
  The fork's two claimed families are AI *prediction* engines; this
  module records prediction *outputs* — labels stored verbatim,
  exactly as the producing engine reported them — and aggregates
  them as counts of recorded labels only. Every prediction record
  carries ``inference_here: False``: no model runs here, nothing is
  inferred, and no value is computed from a label.
- **Derived, never stored.** A grant record's date-based status is
  derived at read time from its stage, due date, and an as-of date
  (the single derivation point is :func:`_grant_is_overdue` /
  :func:`derive_grant_status`), mirroring the Core's finding
  derivation. Stored records carry no derived key.
- **Opaque references only.** Governed systems, counterparties,
  programs, and movement subjects are caller-supplied opaque refs.
  No record shape here can hold a real identifier, a clinical value,
  a location, or a monetary amount (this group has no monetary
  field anywhere, and the extension adds none).
- **High-baseline tier adaptations stay intact.** Mutations write
  to the same hash-chained audit log as the Core, and every
  mutation is fail-closed (AU-5): if the audit write raises
  :class:`~grc.errors.AuditWriteError`, the extension state is
  rolled back from a snapshot and the error propagates — the
  operation does not proceed. The ``auditor`` role holds
  ``audit_read`` only and is denied every extension operation
  (AC-5), as it is denied every Core registry operation.

Permissions reuse the Core's action vocabulary (no new actions):
prediction records and automation run records are recorded work
(``record_results``); provenance records are evidence-shaped
(``manage_evidence``); process configuration definitions are
catalog-shaped configuration (``manage_frameworks``); movement,
supply-chain, health-program, and emergency records ride on
governed systems (``manage_systems``); grant lifecycle records are
finding-shaped work records (``manage_findings``); reference
records are recorded work (``record_results``). All reads require
``read``.

Stub-engine entries ship as labeled reference implementations:
records carrying ``reference_stub: True`` and a surface flag stating
plainly that nothing is monitored, inferred, or hosted here.
"""

import copy
import functools
import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import AuditWriteError, NotFoundError, ValidationError
from .store import checksum_content

# -- prediction records ------------------------------------------------

PREDICTION_KINDS = ("accreditation", "risk")

# -- grants ------------------------------------------------------------

GRANT_STAGES = ("pre_award", "award", "active", "closeout", "closed")

GRANT_TRANSITIONS = {
    "pre_award": {"award", "closed"},
    "award": {"active", "closed"},
    "active": {"closeout", "closed"},
    "closeout": {"closed"},
    "closed": set(),
}

#: Grant stages in which a due date can make the record overdue.
GRANT_OPEN_STAGES = frozenset({"pre_award", "award", "active", "closeout"})

# -- emergency coordination ---------------------------------------------

EMERGENCY_STATES = ("reported", "coordinating", "resolved", "closed")

EMERGENCY_TRANSITIONS = {
    "reported": {"coordinating", "closed"},
    "coordinating": {"resolved", "closed"},
    "resolved": {"closed"},
    "closed": set(),
}

# -- reference (stub-engine) surfaces ------------------------------------

#: surface -> the flag each record carries, always False, stating
#: what does not happen here.
REFERENCE_SURFACES = {
    "device_log_monitoring": "monitoring_here",
    "ml_data_lake": "inference_here",
    "software_factory_hosting": "hosted_here",
}


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


def _grant_is_overdue(grant, as_of_date):
    """True iff ``grant`` is in an open stage and past its due date.

    The single derivation point for grant date-based status; see
    the mutation record in tests/README.md (the batch's fresh
    negative control patches this function's return line).
    """
    if grant["stage"] not in GRANT_OPEN_STAGES:
        return False
    if grant["due_date"] is None:
        return False
    due = _parse_date(grant["due_date"], "due_date")
    return as_of_date > due


def derive_grant_status(grant, as_of=None):
    """Derive a grant record's date-based status at read time.

    Returns ``"overdue"`` when the grant is in an open stage and
    its due date is before the as-of date; otherwise returns the
    grant's recorded stage unchanged. Computed on every call and
    never written back onto the record — the same derivation
    discipline as the Core's :func:`grc.store.derive_finding_status`.
    """
    if _grant_is_overdue(grant, _coerce_as_of(as_of)):
        return "overdue"
    return grant["stage"]


def _fail_closed_ext(method):
    """Wrap an extension mutation so an audit write failure rolls
    the extension state back (AU-5, mirroring the Core's wrapper)."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        snapshot = self._snapshot_state()
        try:
            return method(self, *args, **kwargs)
        except AuditWriteError:
            self._restore_state(snapshot)
            raise

    return wrapper


class GrcExtensions:
    """The final-GAPS-batch extension surface over a core store."""

    def __init__(self, store):
        self.store = store
        self.audit = store.audit
        self._predictions = {}  # id -> prediction record
        self._provenance = {}  # id -> provenance record
        self._process_definitions = {}  # id -> process definition record
        self._movements = {}  # id -> movement record
        self._grants = {}  # id -> grant record
        self._supply_events = {}  # id -> supply-chain event record
        self._health_records = {}  # id -> health program record
        self._emergency_events = {}  # id -> emergency event record
        self._automation_runs = {}  # id -> automation run record
        self._reference_records = {}  # id -> reference (stub) record
        self._counters = {
            "pred": 0, "prov": 0, "pdef": 0, "move": 0, "grant": 0,
            "sc": 0, "hlth": 0, "emg": 0, "run": 0, "ref": 0,
        }
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
            copy.deepcopy(self._predictions),
            copy.deepcopy(self._provenance),
            copy.deepcopy(self._process_definitions),
            copy.deepcopy(self._movements),
            copy.deepcopy(self._grants),
            copy.deepcopy(self._supply_events),
            copy.deepcopy(self._health_records),
            copy.deepcopy(self._emergency_events),
            copy.deepcopy(self._automation_runs),
            copy.deepcopy(self._reference_records),
            dict(self._counters),
        )

    def _restore_state(self, snapshot):
        (
            self._predictions,
            self._provenance,
            self._process_definitions,
            self._movements,
            self._grants,
            self._supply_events,
            self._health_records,
            self._emergency_events,
            self._automation_runs,
            self._reference_records,
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

    def _validate_control_ids(self, control_ids, actor):
        """Validate control ids against the core catalog registry."""
        if control_ids is None:
            return []
        if not isinstance(control_ids, list) or any(
            not isinstance(control_id, str) for control_id in control_ids
        ):
            raise ValidationError("control_ids must be a list of control id strings")
        known = {c["id"] for c in self.store.list_controls(actor)}
        for control_id in control_ids:
            if control_id not in known:
                raise ValidationError("unknown control id: %r" % (control_id,))
        return list(control_ids)

    @staticmethod
    def _copy(record, list_fields=(), dict_fields=()):
        copied = dict(record)
        for field in list_fields:
            copied[field] = list(record[field])
        for field in dict_fields:
            copied[field] = copy.deepcopy(record[field])
        return copied

    # -- prediction records (entries 419, 421) ---------------------------
    #
    # The fork's accreditation-prediction and risk-prediction engines
    # produce labels; this surface records them verbatim against
    # governed systems and controls. No inference happens here and no
    # value is computed from a label: aggregates are counts of the
    # recorded labels only.

    @_fail_closed_ext
    def create_prediction(self, kind, system_ref, predicted_label, actor,
                          source_ref="", control_ids=None):
        """Record a prediction label reported by an external engine.

        ``kind`` is ``"accreditation"`` or ``"risk"``. The label is
        stored **verbatim**; the record carries ``inference_here:
        False`` because this build performs no inference of any
        kind. Action: record_results. Id prefix: pred-.
        """
        if kind not in PREDICTION_KINDS:
            raise ValidationError(
                "prediction kind must be one of %s" % (", ".join(PREDICTION_KINDS),)
            )
        _validate_non_empty(system_ref, "system reference")
        _validate_non_empty(predicted_label, "predicted label")
        source_ref = _validate_text(source_ref, "source reference")
        self._require(actor, "record_results")
        with self._lock:
            self._require_system(system_ref, actor)
            control_ids = self._validate_control_ids(control_ids, actor)
            prediction_id = self._next_id("pred")
            record = {
                "id": prediction_id,
                "kind": kind,
                "system_ref": system_ref,
                "control_ids": control_ids,
                "predicted_label": predicted_label,
                "source_ref": source_ref,
                "inference_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._predictions[prediction_id] = record
            self._audit(actor, "ext_prediction_create", prediction_id,
                        details={"kind": kind, "system_ref": system_ref})
            return self._copy(record, ("control_ids",))

    def get_prediction(self, prediction_id, actor):
        """Return one prediction record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            record = self._predictions.get(prediction_id)
            if record is None:
                raise NotFoundError("prediction not found: %r" % (prediction_id,))
            return self._copy(record, ("control_ids",))

    def list_predictions(self, actor, kind=None, system_ref=None):
        """Return prediction records, optionally filtered.
        Action: read."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._predictions.values())
            if kind is not None:
                records = [r for r in records if r["kind"] == kind]
            if system_ref is not None:
                records = [r for r in records if r["system_ref"] == system_ref]
            return [self._copy(r, ("control_ids",)) for r in records]

    # -- provenance records (entry 424) ----------------------------------
    #
    # Provenance entries link an artifact (opaque ref) to its recorded
    # source with a SHA-256 content hash, riding the Core's evidence
    # discipline: content is hashed, never retained, and verification
    # is by re-supplying content. An entry may instead link a Core
    # evidence record and inherit its recorded checksum.

    @_fail_closed_ext
    def create_provenance(self, artifact_ref, source_ref, actor,
                          content=None, evidence_id=None):
        """Record a provenance link for an artifact.

        Exactly one of ``content`` (hashed here; the content itself
        is not retained) or ``evidence_id`` (a Core evidence record
        whose recorded checksum is inherited) supplies the content
        hash. Action: manage_evidence. Id prefix: prov-.
        """
        _validate_non_empty(artifact_ref, "artifact reference")
        _validate_non_empty(source_ref, "source reference")
        if (content is None) == (evidence_id is None):
            raise ValidationError(
                "provenance requires exactly one of content or evidence_id"
            )
        self._require(actor, "manage_evidence")
        with self._lock:
            if evidence_id is not None:
                evidence = self.store.get_evidence(evidence_id, actor)
                digest = evidence["sha256"]
            else:
                digest = checksum_content(content)
            provenance_id = self._next_id("prov")
            record = {
                "id": provenance_id,
                "artifact_ref": artifact_ref,
                "source_ref": source_ref,
                "content_sha256": digest,
                "evidence_id": evidence_id,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._provenance[provenance_id] = record
            self._audit(actor, "ext_provenance_create", provenance_id,
                        details={"artifact_ref": artifact_ref})
            return dict(record)

    def get_provenance(self, provenance_id, actor):
        """Return one provenance record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            record = self._provenance.get(provenance_id)
            if record is None:
                raise NotFoundError("provenance not found: %r" % (provenance_id,))
            return dict(record)

    def list_provenance(self, actor, artifact_ref=None):
        """Return provenance records, optionally filtered by
        artifact. Action: read."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._provenance.values())
            if artifact_ref is not None:
                records = [r for r in records if r["artifact_ref"] == artifact_ref]
            return [dict(r) for r in records]

    def verify_provenance(self, provenance_id, content, actor):
        """Verify supplied content against a provenance record's
        recorded checksum. Returns True/False; changes nothing.
        Action: read."""
        digest = checksum_content(content)
        self._require(actor, "read")
        with self._lock:
            record = self._provenance.get(provenance_id)
            if record is None:
                raise NotFoundError("provenance not found: %r" % (provenance_id,))
            return digest == record["content_sha256"]

    # -- process configuration & movement tracking (entry 425) -----------
    #
    # Configuration definitions are data: versioned records of a
    # designer's configuration, never executed and never rendered.
    # Movement / service tracking records note that an opaque subject
    # was recorded at a governed system under a verbatim kind label.

    @_fail_closed_ext
    def create_process_definition(self, name, definition, actor):
        """Register a process configuration definition as data.

        The definition dict is held verbatim (deep-copied) as
        version 1. It is never executed and never rendered:
        ``executed_here`` and ``rendered_here`` are False on the
        record. Action: manage_frameworks. Id prefix: pdef-.
        """
        _validate_non_empty(name, "process definition name")
        if not isinstance(definition, dict):
            raise ValidationError("definition must be a dict of configuration data")
        self._require(actor, "manage_frameworks")
        with self._lock:
            definition_id = self._next_id("pdef")
            now = _utc_now()
            record = {
                "id": definition_id,
                "name": name,
                "definition": copy.deepcopy(definition),
                "version": 1,
                "versions": [
                    {
                        "version": 1,
                        "definition": copy.deepcopy(definition),
                        "recorded_by": actor_name(actor),
                        "recorded_utc": now,
                    }
                ],
                "executed_here": False,
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._process_definitions[definition_id] = record
            self._audit(actor, "ext_process_create", definition_id,
                        details={"name": name})
            return self._copy(record, (), ("definition", "versions"))

    @_fail_closed_ext
    def update_process_definition(self, definition_id, definition, actor):
        """Append a new version to a process definition record.
        Action: manage_frameworks."""
        if not isinstance(definition, dict):
            raise ValidationError("definition must be a dict of configuration data")
        self._require(actor, "manage_frameworks")
        with self._lock:
            record = self._process_definitions.get(definition_id)
            if record is None:
                raise NotFoundError(
                    "process definition not found: %r" % (definition_id,)
                )
            now = _utc_now()
            record["version"] += 1
            record["definition"] = copy.deepcopy(definition)
            record["versions"].append(
                {
                    "version": record["version"],
                    "definition": copy.deepcopy(definition),
                    "recorded_by": actor_name(actor),
                    "recorded_utc": now,
                }
            )
            record["updated_utc"] = now
            self._audit(actor, "ext_process_update", definition_id,
                        details={"version": record["version"]})
            return self._copy(record, (), ("definition", "versions"))

    def get_process_definition(self, definition_id, actor):
        """Return one process definition record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            record = self._process_definitions.get(definition_id)
            if record is None:
                raise NotFoundError(
                    "process definition not found: %r" % (definition_id,)
                )
            return self._copy(record, (), ("definition", "versions"))

    def list_process_definitions(self, actor):
        """Return all process definition records. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                self._copy(r, (), ("definition", "versions"))
                for r in self._process_definitions.values()
            ]

    @_fail_closed_ext
    def record_movement(self, system_ref, subject_ref, movement_kind, actor,
                        definition_id=None):
        """Record a movement / service-tracking event.

        ``subject_ref`` is an opaque caller-supplied reference;
        ``movement_kind`` is a verbatim label (entry, exit, service
        request, ...). Nothing is tracked in real time and no
        location is recorded — the record is the tracking surface.
        Action: manage_systems. Id prefix: move-.
        """
        _validate_non_empty(system_ref, "system reference")
        _validate_non_empty(subject_ref, "subject reference")
        _validate_non_empty(movement_kind, "movement kind")
        self._require(actor, "manage_systems")
        with self._lock:
            self._require_system(system_ref, actor)
            if definition_id is not None and (
                definition_id not in self._process_definitions
            ):
                raise NotFoundError(
                    "process definition not found: %r" % (definition_id,)
                )
            movement_id = self._next_id("move")
            record = {
                "id": movement_id,
                "system_ref": system_ref,
                "subject_ref": subject_ref,
                "movement_kind": movement_kind,
                "definition_id": definition_id,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._movements[movement_id] = record
            self._audit(actor, "ext_movement_create", movement_id,
                        details={"system_ref": system_ref})
            return dict(record)

    def list_movements(self, actor, system_ref=None, definition_id=None):
        """Return movement records, optionally filtered.
        Action: read."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._movements.values())
            if system_ref is not None:
                records = [r for r in records if r["system_ref"] == system_ref]
            if definition_id is not None:
                records = [r for r in records if r["definition_id"] == definition_id]
            return [dict(r) for r in records]

    # -- grants lifecycle records (entry 426) ------------------------------
    #
    # Grant records over opaque program references, with a guarded
    # stage lifecycle and full stage history. No monetary field
    # exists: a stage record is not an award transaction, and no
    # money moves here. Due-date status is derived at read.

    @_fail_closed_ext
    def create_grant(self, program_ref, actor, system_ref=None, due_date=None):
        """Create a grant lifecycle record in ``pre_award``.
        Action: manage_findings. Id prefix: grant-."""
        _validate_non_empty(program_ref, "program reference")
        if due_date is not None:
            _parse_date(due_date, "due_date")
        self._require(actor, "manage_findings")
        with self._lock:
            if system_ref is not None:
                self._require_system(system_ref, actor)
            grant_id = self._next_id("grant")
            now = _utc_now()
            record = {
                "id": grant_id,
                "program_ref": program_ref,
                "system_ref": system_ref,
                "stage": "pre_award",
                "stage_history": [
                    {"stage": "pre_award", "recorded_by": actor_name(actor),
                     "recorded_utc": now}
                ],
                "due_date": due_date,
                "created_by": actor_name(actor),
                "created_utc": now,
            }
            self._grants[grant_id] = record
            self._audit(actor, "ext_grant_create", grant_id,
                        details={"program_ref": program_ref})
            return self._copy(record, ("stage_history",))

    @_fail_closed_ext
    def transition_grant(self, grant_id, new_stage, actor):
        """Transition a grant record along its stage lifecycle.
        Action: manage_findings."""
        if new_stage not in GRANT_STAGES:
            raise ValidationError(
                "grant stage must be one of %s" % (", ".join(GRANT_STAGES),)
            )
        self._require(actor, "manage_findings")
        with self._lock:
            record = self._grants.get(grant_id)
            if record is None:
                raise NotFoundError("grant not found: %r" % (grant_id,))
            allowed = GRANT_TRANSITIONS[record["stage"]]
            if new_stage not in allowed:
                raise ValidationError(
                    "grant %r cannot transition from %r to %r"
                    % (grant_id, record["stage"], new_stage)
                )
            record["stage"] = new_stage
            record["stage_history"].append(
                {"stage": new_stage, "recorded_by": actor_name(actor),
                 "recorded_utc": _utc_now()}
            )
            self._audit(actor, "ext_grant_transition", grant_id,
                        details={"stage": new_stage})
            return self._copy(record, ("stage_history",))

    def _grant_view(self, record, as_of):
        view = self._copy(record, ("stage_history",))
        if as_of is not None:
            view["derived_status"] = derive_grant_status(record, as_of)
        return view

    def get_grant(self, grant_id, actor, as_of=None):
        """Return one grant record; with ``as_of``, the copy gains a
        read-time ``derived_status`` (the stored record never does).
        Action: read."""
        self._require(actor, "read")
        with self._lock:
            record = self._grants.get(grant_id)
            if record is None:
                raise NotFoundError("grant not found: %r" % (grant_id,))
            return self._grant_view(record, as_of)

    def list_grants(self, actor, stage=None, system_ref=None, as_of=None):
        """Return grant records, optionally filtered; ``stage``
        filters on the recorded stage. Action: read."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._grants.values())
            if stage is not None:
                records = [r for r in records if r["stage"] == stage]
            if system_ref is not None:
                records = [r for r in records if r["system_ref"] == system_ref]
            return [self._grant_view(r, as_of) for r in records]

    # -- supply-chain ecosystem records (entry 427) ------------------------

    @_fail_closed_ext
    def record_supply_event(self, system_ref, counterparty_ref, event_kind,
                            actor, note=""):
        """Record a supply-chain ecosystem event against a governed
        system and an opaque counterparty reference. The event kind
        is a verbatim label; no goods move and no contract action is
        performed. Action: manage_systems. Id prefix: sc-."""
        _validate_non_empty(system_ref, "system reference")
        _validate_non_empty(counterparty_ref, "counterparty reference")
        _validate_non_empty(event_kind, "event kind")
        note = _validate_text(note, "note")
        self._require(actor, "manage_systems")
        with self._lock:
            self._require_system(system_ref, actor)
            event_id = self._next_id("sc")
            record = {
                "id": event_id,
                "system_ref": system_ref,
                "counterparty_ref": counterparty_ref,
                "event_kind": event_kind,
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._supply_events[event_id] = record
            self._audit(actor, "ext_supply_event_create", event_id,
                        details={"system_ref": system_ref})
            return dict(record)

    def list_supply_events(self, actor, system_ref=None):
        """Return supply-chain event records, optionally filtered.
        Action: read."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._supply_events.values())
            if system_ref is not None:
                records = [r for r in records if r["system_ref"] == system_ref]
            return [dict(r) for r in records]

    # -- healthcare ecosystem records (entry 428) --------------------------
    #
    # Program records over opaque references only. The record shape
    # is fixed and small: there is no parameter and no field that
    # can hold a patient identifier or any clinical value.

    @_fail_closed_ext
    def record_health_record(self, program_ref, record_kind, actor,
                             system_ref=None, subject_ref=None):
        """Record a healthcare-ecosystem program record.

        ``subject_ref``, when given, is an opaque caller-supplied
        reference — never an identifier. Action: manage_systems.
        Id prefix: hlth-."""
        _validate_non_empty(program_ref, "program reference")
        _validate_non_empty(record_kind, "record kind")
        if subject_ref is not None:
            _validate_non_empty(subject_ref, "subject reference")
        self._require(actor, "manage_systems")
        with self._lock:
            if system_ref is not None:
                self._require_system(system_ref, actor)
            record_id = self._next_id("hlth")
            record = {
                "id": record_id,
                "program_ref": program_ref,
                "record_kind": record_kind,
                "system_ref": system_ref,
                "subject_ref": subject_ref,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._health_records[record_id] = record
            self._audit(actor, "ext_health_record_create", record_id,
                        details={"program_ref": program_ref})
            return dict(record)

    def list_health_records(self, actor, program_ref=None):
        """Return health program records, optionally filtered.
        Action: read."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._health_records.values())
            if program_ref is not None:
                records = [r for r in records if r["program_ref"] == program_ref]
            return [dict(r) for r in records]

    # -- emergency-response coordination records (entry 429) ---------------
    #
    # Coordination event records with a guarded state lifecycle.
    # There are no responder, location, or health fields: nothing is
    # dispatched, nobody is tracked, and no matching is performed.

    @_fail_closed_ext
    def create_emergency_event(self, system_ref, event_kind, actor):
        """Create a coordination event record in ``reported``.
        Action: manage_systems. Id prefix: emg-."""
        _validate_non_empty(system_ref, "system reference")
        _validate_non_empty(event_kind, "event kind")
        self._require(actor, "manage_systems")
        with self._lock:
            self._require_system(system_ref, actor)
            event_id = self._next_id("emg")
            now = _utc_now()
            record = {
                "id": event_id,
                "system_ref": system_ref,
                "event_kind": event_kind,
                "state": "reported",
                "state_history": [
                    {"state": "reported", "recorded_by": actor_name(actor),
                     "recorded_utc": now}
                ],
                "recorded_by": actor_name(actor),
                "recorded_utc": now,
            }
            self._emergency_events[event_id] = record
            self._audit(actor, "ext_emergency_create", event_id,
                        details={"system_ref": system_ref})
            return self._copy(record, ("state_history",))

    @_fail_closed_ext
    def transition_emergency_event(self, event_id, new_state, actor):
        """Transition a coordination event along its lifecycle.
        Action: manage_systems."""
        if new_state not in EMERGENCY_STATES:
            raise ValidationError(
                "emergency state must be one of %s"
                % (", ".join(EMERGENCY_STATES),)
            )
        self._require(actor, "manage_systems")
        with self._lock:
            record = self._emergency_events.get(event_id)
            if record is None:
                raise NotFoundError("emergency event not found: %r" % (event_id,))
            allowed = EMERGENCY_TRANSITIONS[record["state"]]
            if new_state not in allowed:
                raise ValidationError(
                    "emergency event %r cannot transition from %r to %r"
                    % (event_id, record["state"], new_state)
                )
            record["state"] = new_state
            record["state_history"].append(
                {"state": new_state, "recorded_by": actor_name(actor),
                 "recorded_utc": _utc_now()}
            )
            self._audit(actor, "ext_emergency_transition", event_id,
                        details={"state": new_state})
            return self._copy(record, ("state_history",))

    def list_emergency_events(self, actor, system_ref=None, state=None):
        """Return coordination event records, optionally filtered;
        ``state`` filters on the recorded state. Action: read."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._emergency_events.values())
            if system_ref is not None:
                records = [r for r in records if r["system_ref"] == system_ref]
            if state is not None:
                records = [r for r in records if r["state"] == state]
            return [self._copy(r, ("state_history",)) for r in records]

    # -- automation run records (entry 430, RPA half) ----------------------
    #
    # Ledger-style append-only records are native to this substrate
    # (the Core's audit trail is itself a hash chain). Automation
    # *runs* are recorded here as reported outcomes; no robotic
    # process executes and no distributed-ledger consensus exists.

    @_fail_closed_ext
    def record_automation_run(self, automation_ref, outcome_label, actor):
        """Record an automation run's reported outcome verbatim.

        The run happened elsewhere (or did not); this record is the
        ledger entry for it and carries ``executed_here: False``.
        Action: record_results. Id prefix: run-."""
        _validate_non_empty(automation_ref, "automation reference")
        _validate_non_empty(outcome_label, "outcome label")
        self._require(actor, "record_results")
        with self._lock:
            run_id = self._next_id("run")
            record = {
                "id": run_id,
                "automation_ref": automation_ref,
                "outcome_label": outcome_label,
                "executed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._automation_runs[run_id] = record
            self._audit(actor, "ext_automation_run_create", run_id,
                        details={"automation_ref": automation_ref})
            return dict(record)

    def list_automation_runs(self, actor, automation_ref=None):
        """Return automation run records, optionally filtered.
        Action: read."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._automation_runs.values())
            if automation_ref is not None:
                records = [r for r in records if r["automation_ref"] == automation_ref]
            return [dict(r) for r in records]

    # -- reference records (stub-engine entries 420, 422, 423) -------------
    #
    # Labeled reference implementations: a record that a surface of
    # the named kind was registered, carrying reference_stub: True
    # and the surface's own flag set False. Nothing is monitored,
    # no model is loaded or run, and nothing is hosted.

    @_fail_closed_ext
    def create_reference_record(self, surface, label, actor):
        """Register a labeled reference record for a stub surface.

        ``surface`` is one of :data:`REFERENCE_SURFACES`. The
        record carries ``reference_stub: True`` and the surface's
        flag (``monitoring_here`` / ``inference_here`` /
        ``hosted_here``) set False. Action: record_results.
        Id prefix: ref-."""
        if surface not in REFERENCE_SURFACES:
            raise ValidationError(
                "reference surface must be one of %s"
                % (", ".join(sorted(REFERENCE_SURFACES)),)
            )
        _validate_non_empty(label, "reference label")
        self._require(actor, "record_results")
        with self._lock:
            record_id = self._next_id("ref")
            record = {
                "id": record_id,
                "surface": surface,
                "label": label,
                "reference_stub": True,
                REFERENCE_SURFACES[surface]: False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._reference_records[record_id] = record
            self._audit(actor, "ext_reference_create", record_id,
                        details={"surface": surface})
            return dict(record)

    def list_reference_records(self, actor, surface=None):
        """Return reference records, optionally filtered by surface.
        Action: read."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._reference_records.values())
            if surface is not None:
                records = [r for r in records if r["surface"] == surface]
            return [dict(r) for r in records]

    # -- extension summary (counts only) -----------------------------------

    def extension_summary(self, actor, as_of=None):
        """Return the extension summary, computed on read: counts
        of recorded records and of their verbatim recorded labels
        only. No score, rating, grade, or computed value of any
        kind is produced — the same doctrine as the Core's posture
        summary. Does not audit. Action: read."""
        self._require(actor, "read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            predictions_by_kind = {name: 0 for name in PREDICTION_KINDS}
            predictions_by_label = {}
            for record in self._predictions.values():
                predictions_by_kind[record["kind"]] += 1
                label = record["predicted_label"]
                predictions_by_label[label] = predictions_by_label.get(label, 0) + 1

            movements_by_kind = {}
            for record in self._movements.values():
                kind = record["movement_kind"]
                movements_by_kind[kind] = movements_by_kind.get(kind, 0) + 1

            grants_by_stage = {name: 0 for name in GRANT_STAGES}
            grants_overdue = 0
            for record in self._grants.values():
                grants_by_stage[record["stage"]] += 1
                if _grant_is_overdue(record, as_of_date):
                    grants_overdue += 1

            supply_by_kind = {}
            for record in self._supply_events.values():
                kind = record["event_kind"]
                supply_by_kind[kind] = supply_by_kind.get(kind, 0) + 1

            health_by_kind = {}
            for record in self._health_records.values():
                kind = record["record_kind"]
                health_by_kind[kind] = health_by_kind.get(kind, 0) + 1

            emergency_by_state = {name: 0 for name in EMERGENCY_STATES}
            for record in self._emergency_events.values():
                emergency_by_state[record["state"]] += 1

            runs_by_outcome = {}
            for record in self._automation_runs.values():
                label = record["outcome_label"]
                runs_by_outcome[label] = runs_by_outcome.get(label, 0) + 1

            reference_by_surface = {name: 0 for name in REFERENCE_SURFACES}
            for record in self._reference_records.values():
                reference_by_surface[record["surface"]] += 1

            return {
                "as_of": as_of_date.isoformat(),
                "predictions": {
                    "total": len(self._predictions),
                    "by_kind": predictions_by_kind,
                    "by_label": predictions_by_label,
                },
                "provenance": {"total": len(self._provenance)},
                "process_definitions": {
                    "total": len(self._process_definitions),
                },
                "movements": {
                    "total": len(self._movements),
                    "by_kind": movements_by_kind,
                },
                "grants": {
                    "total": len(self._grants),
                    "by_stage": grants_by_stage,
                    "overdue": grants_overdue,
                },
                "supply_events": {
                    "total": len(self._supply_events),
                    "by_kind": supply_by_kind,
                },
                "health_records": {
                    "total": len(self._health_records),
                    "by_kind": health_by_kind,
                },
                "emergency_events": {
                    "total": len(self._emergency_events),
                    "by_state": emergency_by_state,
                },
                "automation_runs": {
                    "total": len(self._automation_runs),
                    "by_outcome": runs_by_outcome,
                },
                "reference_records": {
                    "total": len(self._reference_records),
                    "by_surface": reference_by_surface,
                },
            }
