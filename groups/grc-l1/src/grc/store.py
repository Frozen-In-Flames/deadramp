"""GRC store: frameworks, controls, governed systems, indicators,
evidence, findings, assessments, and authorization records.

Clean-room records substrate. The store is an in-memory register of
*records*; it performs no validation engines, no scanning, no feed
ingestion, and no scoring:

- **Frameworks & controls** -- a registry of framework records
  (``id`` / ``name`` / ``version``) and the controls within them,
  seeded from :mod:`grc.catalog` (a modest, generic 800-53-style
  catalog) and open to caller-registered frameworks and controls.
- **Governed systems** -- systems under governance, keyed by opaque
  caller-supplied references. Free-text names are labels only.
- **Indicators** -- indicator definitions linked to controls, plus
  recorded validation *results* (indicator, system, status,
  timestamp, recorded-by). Results are records: this build performs
  no automated validation, and a result ``status`` is stored verbatim
  exactly as the recording user supplied it.
- **Evidence** -- artifact metadata records plus the SHA-256
  checksum of supplied content (verification by content is supported
  against that checksum). An artifact's validation status is a
  recorded field set by an authorized reviewer, never computed.
- **Findings** -- POA&M-style remediation records with a severity
  recorded verbatim, a source, a due date, and a lifecycle enforced
  by a transition table. Any date-based status (``overdue``) is
  *derived at read time* from due date + lifecycle state + an
  as-of date; it is never stored on the record.
- **Assessments & authorizations** -- assessment records against a
  system/framework with the result recorded verbatim, and
  authorization status records whose transitions are guarded by a
  transition table.

Posture reporting is computed on read from the records and returns
counts and summaries only. There is no computed risk score or
aggregate rating anywhere in this build, and no monetary field.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Sequential ids are
issued per object type with fixed prefixes (``ev-``, ``find-``,
``result-``, ``asmt-``, ``auth-``); frameworks, controls, systems,
and indicators are keyed by caller-supplied ids/references. The store
records every successful mutation to its audit log (when one is
attached). Plain reads and the posture summary are not audited here;
denied attempts and audit reads are the HTTP layer's responsibility,
so nothing is recorded twice.
"""

import hashlib
import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .catalog import CONTROL_CATALOG, SEED_FRAMEWORK
from .errors import NotFoundError, ValidationError

FINDING_STATUSES = (
    "open",
    "in_progress",
    "remediated",
    "validated",
    "closed",
    "accepted_risk",
)

FINDING_TRANSITIONS = {
    "open": {"in_progress", "accepted_risk"},
    "in_progress": {"remediated", "accepted_risk"},
    "remediated": {"validated", "in_progress"},
    "validated": {"closed"},
    "accepted_risk": {"in_progress", "closed"},
    "closed": set(),
}

# Lifecycle states in which a past-due finding counts as overdue.
# Once a finding is remediated, validated, closed, or risk-accepted,
# the date alone no longer makes it overdue.
OVERDUE_STATES = ("open", "in_progress")

# Finding lifecycle states counted as "open" in posture reporting.
OPEN_STATES = ("open", "in_progress", "accepted_risk")

AUTH_STATUSES = (
    "not_started",
    "in_progress",
    "authorized",
    "denied",
    "expired",
    "revoked",
)

AUTH_TRANSITIONS = {
    "not_started": {"in_progress"},
    "in_progress": {"authorized", "denied"},
    "denied": {"in_progress"},
    "authorized": {"expired", "revoked"},
    "expired": {"in_progress"},
    "revoked": set(),
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


def _coerce_as_of(as_of):
    """Coerce an as-of parameter (date, datetime, or ISO string) to a
    :class:`datetime.date`. ``None`` means today (UTC)."""
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


def derive_finding_status(finding, as_of=None):
    """Derive a finding's date-based status at read time.

    Returns ``"overdue"`` when the finding is still in an open
    lifecycle state (``open`` / ``in_progress``) and its due date is
    before the as-of date; otherwise returns the finding's lifecycle
    status unchanged. The result is computed from the record on every
    call and is never written back onto the record.
    """
    status = finding["status"]
    if status in OVERDUE_STATES:
        due = _parse_date(finding["due_date"], "due_date")
        if _coerce_as_of(as_of) > due:
            return "overdue"
    return status


def checksum_content(content):
    """Return the SHA-256 hex digest of ``content`` (str or bytes)."""
    if isinstance(content, str):
        data = content.encode("utf-8")
    elif isinstance(content, (bytes, bytearray)):
        data = bytes(content)
    else:
        raise ValidationError("content must be a string or bytes")
    return hashlib.sha256(data).hexdigest()


def _maybe_require(actor, action):
    """Enforce permissions when ``actor`` is a User-like object.

    Plain string actors carry identity (for provenance) but no role, so
    there is nothing to enforce against; enforcement for those happens
    in the service layer, which knows the role registry.
    """
    if actor is not None and hasattr(actor, "role"):
        require(actor, action)


class GrcStore:
    """In-memory store for the GRC records substrate."""

    def __init__(self, audit=None):
        self.audit = audit
        self._frameworks = {}  # id -> framework dict
        self._controls = {}  # (framework_id, control_id) -> control dict
        self._systems = {}  # ref -> system dict
        self._indicators = {}  # id -> indicator dict
        self._results = {}  # id -> indicator result dict
        self._evidence = {}  # id -> evidence dict
        self._findings = {}  # id -> finding dict
        self._assessments = {}  # id -> assessment dict
        self._authorizations = {}  # id -> authorization dict
        self._counters = {"ev": 0, "find": 0, "result": 0, "asmt": 0, "auth": 0}
        self._lock = threading.RLock()
        # Seed the registry from the built-in catalog. Seeding is data
        # loading, not a mutation: it writes no audit entries.
        framework = dict(SEED_FRAMEWORK)
        self._frameworks[framework["id"]] = framework
        for entry in CONTROL_CATALOG:
            control = {
                "framework_id": framework["id"],
                "id": entry["id"],
                "family": entry["family"],
                "title": entry["title"],
            }
            self._controls[(framework["id"], entry["id"])] = control

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _get_framework_record(self, framework_id):
        framework = self._frameworks.get(framework_id)
        if framework is None:
            raise NotFoundError("framework not found: %r" % (framework_id,))
        return framework

    def _get_system_record(self, ref):
        system = self._systems.get(ref)
        if system is None:
            raise NotFoundError("system not found: %r" % (ref,))
        return system

    def _get_indicator_record(self, indicator_id):
        indicator = self._indicators.get(indicator_id)
        if indicator is None:
            raise NotFoundError("indicator not found: %r" % (indicator_id,))
        return indicator

    def _validate_control_ids(self, control_ids):
        """Validate control ids against the registry (any framework)."""
        if control_ids is None:
            return []
        if not isinstance(control_ids, list) or any(
            not isinstance(control_id, str) for control_id in control_ids
        ):
            raise ValidationError("control_ids must be a list of control id strings")
        known = {control_id for (_, control_id) in self._controls}
        for control_id in control_ids:
            if control_id not in known:
                raise ValidationError("unknown control id: %r" % (control_id,))
        return list(control_ids)

    def _validate_system_refs(self, system_refs):
        if system_refs is None:
            return []
        if not isinstance(system_refs, list) or any(
            not isinstance(ref, str) for ref in system_refs
        ):
            raise ValidationError("system_refs must be a list of system references")
        for ref in system_refs:
            if ref not in self._systems:
                raise ValidationError("unknown system reference: %r" % (ref,))
        return list(system_refs)

    @staticmethod
    def _copy(record, list_fields=()):
        copied = dict(record)
        for field in list_fields:
            copied[field] = list(record[field])
        return copied

    # -- frameworks & controls ----------------------------------------

    def create_framework(self, framework_id, name, version, actor, description=""):
        """Register a framework record (id / name / version)."""
        _validate_non_empty(framework_id, "framework id")
        _validate_non_empty(name, "framework name")
        _validate_non_empty(version, "framework version")
        description = _validate_text(description, "framework description")
        _maybe_require(actor, "manage_frameworks")
        with self._lock:
            if framework_id in self._frameworks:
                raise ValidationError(
                    "framework id already registered: %r" % (framework_id,)
                )
            framework = {
                "id": framework_id,
                "name": name,
                "version": version,
                "description": description,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._frameworks[framework_id] = framework
            self._audit(actor, "framework_create", framework_id, details={"name": name})
            return dict(framework)

    def get_framework(self, framework_id, actor):
        """Return one framework dict."""
        _maybe_require(actor, "read")
        with self._lock:
            return dict(self._get_framework_record(framework_id))

    def list_frameworks(self, actor):
        """Return framework dicts in registration order."""
        _maybe_require(actor, "read")
        with self._lock:
            return [dict(framework) for framework in self._frameworks.values()]

    def create_control(self, framework_id, control_id, title, actor, family=None):
        """Register a control within a framework."""
        _validate_non_empty(control_id, "control id")
        _validate_non_empty(title, "control title")
        if family is None:
            family = control_id.split("-", 1)[0]
        _validate_non_empty(family, "control family")
        _maybe_require(actor, "manage_frameworks")
        with self._lock:
            self._get_framework_record(framework_id)
            key = (framework_id, control_id)
            if key in self._controls:
                raise ValidationError(
                    "control already registered in framework %r: %r"
                    % (framework_id, control_id)
                )
            control = {
                "framework_id": framework_id,
                "id": control_id,
                "family": family,
                "title": title,
            }
            self._controls[key] = control
            self._audit(
                actor,
                "control_create",
                control_id,
                details={"framework_id": framework_id},
            )
            return dict(control)

    def get_control(self, framework_id, control_id, actor):
        """Return one control dict within its framework."""
        _maybe_require(actor, "read")
        with self._lock:
            self._get_framework_record(framework_id)
            control = self._controls.get((framework_id, control_id))
            if control is None:
                raise NotFoundError(
                    "control not found in framework %r: %r"
                    % (framework_id, control_id)
                )
            return dict(control)

    def list_controls(self, actor, framework_id=None):
        """Return control dicts, optionally within one framework, in
        registration order."""
        _maybe_require(actor, "read")
        with self._lock:
            if framework_id is not None:
                self._get_framework_record(framework_id)
            return [
                dict(control)
                for (fw_id, _), control in self._controls.items()
                if framework_id is None or fw_id == framework_id
            ]

    # -- governed systems ----------------------------------------------

    def create_system(self, ref, name, actor, description=""):
        """Register a governed system under an opaque caller-supplied
        reference. ``name`` is a free-text label only."""
        _validate_non_empty(ref, "system reference")
        _validate_non_empty(name, "system name")
        description = _validate_text(description, "system description")
        _maybe_require(actor, "manage_systems")
        with self._lock:
            if ref in self._systems:
                raise ValidationError("system reference already registered: %r" % (ref,))
            now = _utc_now()
            system = {
                "ref": ref,
                "name": name,
                "description": description,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._systems[ref] = system
            self._audit(actor, "system_create", ref, details={"name": name})
            return dict(system)

    def get_system(self, ref, actor):
        """Return one governed-system dict."""
        _maybe_require(actor, "read")
        with self._lock:
            return dict(self._get_system_record(ref))

    def list_systems(self, actor):
        """Return governed-system dicts in registration order."""
        _maybe_require(actor, "read")
        with self._lock:
            return [dict(system) for system in self._systems.values()]

    # -- indicators & recorded results ----------------------------------

    def create_indicator(self, indicator_id, name, control_ids, actor, description=""):
        """Register an indicator definition linked to controls."""
        _validate_non_empty(indicator_id, "indicator id")
        _validate_non_empty(name, "indicator name")
        description = _validate_text(description, "indicator description")
        _maybe_require(actor, "manage_indicators")
        with self._lock:
            control_ids = self._validate_control_ids(control_ids)
            if indicator_id in self._indicators:
                raise ValidationError(
                    "indicator id already registered: %r" % (indicator_id,)
                )
            indicator = {
                "id": indicator_id,
                "name": name,
                "description": description,
                "control_ids": control_ids,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._indicators[indicator_id] = indicator
            self._audit(actor, "indicator_create", indicator_id, details={"name": name})
            return self._copy(indicator, ("control_ids",))

    def get_indicator(self, indicator_id, actor):
        """Return one indicator definition dict."""
        _maybe_require(actor, "read")
        with self._lock:
            return self._copy(self._get_indicator_record(indicator_id), ("control_ids",))

    def list_indicators(self, actor):
        """Return indicator definition dicts in registration order."""
        _maybe_require(actor, "read")
        with self._lock:
            return [
                self._copy(indicator, ("control_ids",))
                for indicator in self._indicators.values()
            ]

    def record_indicator_result(
        self, indicator_id, system_ref, status, actor, timestamp=None, note=""
    ):
        """Record one validation result for an indicator on a system.

        The ``status`` is recorded verbatim, exactly as supplied.
        This build performs no automated validation: a result is a
        record of what a person or an external process reported, with
        its timestamp and the identity that recorded it.
        """
        _validate_non_empty(status, "result status")
        note = _validate_text(note, "result note")
        if timestamp is not None:
            timestamp = _validate_timestamp(timestamp, "result timestamp")
        _maybe_require(actor, "record_results")
        with self._lock:
            self._get_indicator_record(indicator_id)
            self._get_system_record(system_ref)
            result_id = self._next_id("result")
            result = {
                "id": result_id,
                "indicator_id": indicator_id,
                "system_ref": system_ref,
                "status": status,
                "timestamp": timestamp if timestamp is not None else _utc_now(),
                "recorded_by": actor_name(actor),
                "note": note,
            }
            self._results[result_id] = result
            self._audit(
                actor,
                "indicator_result_record",
                result_id,
                details={"indicator_id": indicator_id, "system_ref": system_ref},
            )
            return dict(result)

    def list_indicator_results(self, actor, indicator_id=None, system_ref=None):
        """Return recorded indicator results, optionally filtered by
        indicator and/or system, in recording order."""
        _maybe_require(actor, "read")
        with self._lock:
            if indicator_id is not None:
                self._get_indicator_record(indicator_id)
            if system_ref is not None:
                self._get_system_record(system_ref)
            return [
                dict(result)
                for result in self._results.values()
                if (indicator_id is None or result["indicator_id"] == indicator_id)
                and (system_ref is None or result["system_ref"] == system_ref)
            ]

    # -- evidence ---------------------------------------------------------

    def create_evidence(
        self, name, content, control_ids, system_refs, actor, description=""
    ):
        """Register an evidence artifact: a metadata record plus the
        SHA-256 checksum of the supplied content. The content itself
        is not retained; verification is by re-supplying content and
        comparing checksums (see :meth:`verify_evidence`)."""
        _validate_non_empty(name, "evidence name")
        description = _validate_text(description, "evidence description")
        checksum = checksum_content(content)
        if isinstance(content, str):
            size = len(content.encode("utf-8"))
        else:
            size = len(bytes(content))
        _maybe_require(actor, "manage_evidence")
        with self._lock:
            control_ids = self._validate_control_ids(control_ids)
            system_refs = self._validate_system_refs(system_refs)
            evidence_id = self._next_id("ev")
            now = _utc_now()
            evidence = {
                "id": evidence_id,
                "name": name,
                "description": description,
                "sha256": checksum,
                "size_bytes": size,
                "control_ids": control_ids,
                "system_refs": system_refs,
                "validation_status": "unvalidated",
                "validated_by": None,
                "validated_utc": None,
                "review_note": "",
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._evidence[evidence_id] = evidence
            self._audit(actor, "evidence_create", evidence_id, details={"name": name})
            return self._copy(evidence, ("control_ids", "system_refs"))

    def _get_evidence_record(self, evidence_id):
        evidence = self._evidence.get(evidence_id)
        if evidence is None:
            raise NotFoundError("evidence not found: %r" % (evidence_id,))
        return evidence

    def get_evidence(self, evidence_id, actor):
        """Return one evidence metadata record."""
        _maybe_require(actor, "read")
        with self._lock:
            return self._copy(
                self._get_evidence_record(evidence_id),
                ("control_ids", "system_refs"),
            )

    def list_evidence(self, actor, system_ref=None, control_id=None):
        """Return evidence records, optionally filtered by linked
        system and/or control, in id order."""
        _maybe_require(actor, "read")
        with self._lock:
            records = list(self._evidence.values())
            if system_ref is not None:
                records = [e for e in records if system_ref in e["system_refs"]]
            if control_id is not None:
                records = [e for e in records if control_id in e["control_ids"]]
            return [
                self._copy(e, ("control_ids", "system_refs")) for e in records
            ]

    def verify_evidence(self, evidence_id, content, actor):
        """Verify supplied content against the stored checksum.

        Returns True when the SHA-256 of ``content`` matches the
        checksum recorded for the artifact, False otherwise. This is
        a read: it changes nothing and writes no audit entry.
        """
        checksum = checksum_content(content)
        _maybe_require(actor, "read")
        with self._lock:
            evidence = self._get_evidence_record(evidence_id)
            return checksum == evidence["sha256"]

    def review_evidence(self, evidence_id, validation_status, actor, note=""):
        """Set an artifact's recorded validation status as a reviewer.

        The status is a recorded field: it is stored verbatim, exactly
        as the authorized reviewer supplied it, and is never computed
        by this build.
        """
        _validate_non_empty(validation_status, "validation status")
        note = _validate_text(note, "review note")
        _maybe_require(actor, "review_evidence")
        with self._lock:
            evidence = self._get_evidence_record(evidence_id)
            evidence["validation_status"] = validation_status
            evidence["validated_by"] = actor_name(actor)
            evidence["validated_utc"] = _utc_now()
            evidence["review_note"] = note
            evidence["updated_utc"] = _utc_now()
            self._audit(
                actor,
                "evidence_review",
                evidence_id,
                details={"validation_status": validation_status},
            )
            return self._copy(evidence, ("control_ids", "system_refs"))

    # -- findings (POA&M-style remediation records) ------------------------

    def create_finding(
        self,
        title,
        system_ref,
        severity,
        source,
        due_date,
        actor,
        description="",
        control_ids=None,
    ):
        """Create a finding / remediation record in ``open`` state.

        ``severity`` is recorded verbatim, exactly as supplied; this
        build computes no severity, score, or rating from it.
        """
        _validate_non_empty(title, "finding title")
        _validate_non_empty(severity, "finding severity")
        _validate_non_empty(source, "finding source")
        _parse_date(due_date, "due_date")
        description = _validate_text(description, "finding description")
        _maybe_require(actor, "manage_findings")
        with self._lock:
            self._get_system_record(system_ref)
            control_ids = self._validate_control_ids(control_ids)
            finding_id = self._next_id("find")
            now = _utc_now()
            finding = {
                "id": finding_id,
                "title": title,
                "description": description,
                "system_ref": system_ref,
                "severity": severity,
                "source": source,
                "due_date": due_date,
                "control_ids": control_ids,
                "status": "open",
                "risk_rationale": None,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._findings[finding_id] = finding
            self._audit(actor, "finding_create", finding_id, details={"title": title})
            return self._copy(finding, ("control_ids",))

    def _get_finding_record(self, finding_id):
        finding = self._findings.get(finding_id)
        if finding is None:
            raise NotFoundError("finding not found: %r" % (finding_id,))
        return finding

    def _finding_view(self, finding, as_of):
        copied = self._copy(finding, ("control_ids",))
        if as_of is not None:
            copied["derived_status"] = derive_finding_status(finding, as_of)
        return copied

    def get_finding(self, finding_id, actor, as_of=None):
        """Return one finding dict. The stored record carries no
        derived status; when ``as_of`` is given, the returned copy
        gains a ``derived_status`` key computed at read time."""
        _maybe_require(actor, "read")
        with self._lock:
            return self._finding_view(self._get_finding_record(finding_id), as_of)

    def list_findings(self, actor, system_ref=None, status=None, as_of=None):
        """Return finding dicts matching the filters, in id order.
        With ``as_of``, each returned copy gains a read-time
        ``derived_status`` (see :meth:`get_finding`)."""
        _maybe_require(actor, "read")
        with self._lock:
            findings = list(self._findings.values())
            if system_ref is not None:
                findings = [f for f in findings if f["system_ref"] == system_ref]
            if status is not None:
                findings = [f for f in findings if f["status"] == status]
            return [self._finding_view(f, as_of) for f in findings]

    def transition_finding(self, finding_id, new_status, actor, rationale=None):
        """Move a finding through its lifecycle, per
        ``FINDING_TRANSITIONS``. Moving to ``accepted_risk`` requires
        a recorded rationale."""
        if rationale is not None:
            rationale = _validate_text(rationale, "risk rationale")
        _maybe_require(actor, "manage_findings")
        with self._lock:
            finding = self._get_finding_record(finding_id)
            current = finding["status"]
            if (
                new_status not in FINDING_STATUSES
                or new_status not in FINDING_TRANSITIONS[current]
            ):
                raise ValidationError(
                    "finding cannot move from %r to %r" % (current, new_status)
                )
            if new_status == "accepted_risk" and not (
                isinstance(rationale, str) and rationale.strip()
            ):
                raise ValidationError(
                    "accepting risk requires a recorded rationale"
                )
            finding["status"] = new_status
            if new_status == "accepted_risk":
                finding["risk_rationale"] = rationale
            finding["updated_utc"] = _utc_now()
            self._audit(
                actor,
                "finding_transition",
                finding_id,
                details={"from": current, "to": new_status},
            )
            return self._copy(finding, ("control_ids",))

    # -- assessments & authorizations --------------------------------------

    def create_assessment(
        self,
        system_ref,
        framework_id,
        scope,
        assessor,
        assessment_date,
        result,
        actor,
        notes="",
    ):
        """Record an assessment against a system and framework.

        ``result`` is recorded verbatim, exactly as the assessor
        reported it; this build computes no assessment outcome.
        """
        _validate_non_empty(scope, "assessment scope")
        _validate_non_empty(assessor, "assessor reference")
        _parse_date(assessment_date, "assessment date")
        _validate_non_empty(result, "assessment result")
        notes = _validate_text(notes, "assessment notes")
        _maybe_require(actor, "manage_assessments")
        with self._lock:
            self._get_system_record(system_ref)
            self._get_framework_record(framework_id)
            assessment_id = self._next_id("asmt")
            assessment = {
                "id": assessment_id,
                "system_ref": system_ref,
                "framework_id": framework_id,
                "scope": scope,
                "assessor": assessor,
                "date": assessment_date,
                "result": result,
                "notes": notes,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assessments[assessment_id] = assessment
            self._audit(
                actor,
                "assessment_create",
                assessment_id,
                details={"system_ref": system_ref, "framework_id": framework_id},
            )
            return dict(assessment)

    def get_assessment(self, assessment_id, actor):
        """Return one assessment record."""
        _maybe_require(actor, "read")
        with self._lock:
            assessment = self._assessments.get(assessment_id)
            if assessment is None:
                raise NotFoundError("assessment not found: %r" % (assessment_id,))
            return dict(assessment)

    def list_assessments(self, actor, system_ref=None, framework_id=None):
        """Return assessment records, optionally filtered, in id order."""
        _maybe_require(actor, "read")
        with self._lock:
            records = list(self._assessments.values())
            if system_ref is not None:
                records = [a for a in records if a["system_ref"] == system_ref]
            if framework_id is not None:
                records = [a for a in records if a["framework_id"] == framework_id]
            return [dict(a) for a in records]

    def create_authorization(
        self, system_ref, framework_id, actor, status="not_started", note=""
    ):
        """Create an authorization status record for a system under a
        framework. The initial status is recorded as supplied and
        must be one of ``AUTH_STATUSES``."""
        if status not in AUTH_STATUSES:
            raise ValidationError(
                "status must be one of %s" % (", ".join(AUTH_STATUSES),)
            )
        note = _validate_text(note, "authorization note")
        _maybe_require(actor, "manage_authorizations")
        with self._lock:
            self._get_system_record(system_ref)
            self._get_framework_record(framework_id)
            auth_id = self._next_id("auth")
            now = _utc_now()
            record = {
                "id": auth_id,
                "system_ref": system_ref,
                "framework_id": framework_id,
                "status": status,
                "note": note,
                "history": [
                    {"from": None, "to": status, "by": actor_name(actor), "utc": now}
                ],
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._authorizations[auth_id] = record
            self._audit(
                actor,
                "authorization_create",
                auth_id,
                details={"system_ref": system_ref, "status": status},
            )
            return self._copy_auth(record)

    @staticmethod
    def _copy_auth(record):
        copied = dict(record)
        copied["history"] = [dict(step) for step in record["history"]]
        return copied

    def _get_auth_record(self, auth_id):
        record = self._authorizations.get(auth_id)
        if record is None:
            raise NotFoundError("authorization not found: %r" % (auth_id,))
        return record

    def get_authorization(self, auth_id, actor):
        """Return one authorization status record."""
        _maybe_require(actor, "read")
        with self._lock:
            return self._copy_auth(self._get_auth_record(auth_id))

    def list_authorizations(self, actor, system_ref=None, status=None):
        """Return authorization records, optionally filtered, in id order."""
        _maybe_require(actor, "read")
        with self._lock:
            records = list(self._authorizations.values())
            if system_ref is not None:
                records = [a for a in records if a["system_ref"] == system_ref]
            if status is not None:
                records = [a for a in records if a["status"] == status]
            return [self._copy_auth(a) for a in records]

    def transition_authorization(self, auth_id, new_status, actor, note=None):
        """Move an authorization record through its guarded lifecycle,
        per ``AUTH_TRANSITIONS``, appending to its history."""
        if note is not None:
            note = _validate_text(note, "authorization note")
        _maybe_require(actor, "manage_authorizations")
        with self._lock:
            record = self._get_auth_record(auth_id)
            current = record["status"]
            if (
                new_status not in AUTH_STATUSES
                or new_status not in AUTH_TRANSITIONS[current]
            ):
                raise ValidationError(
                    "authorization cannot move from %r to %r" % (current, new_status)
                )
            now = _utc_now()
            record["status"] = new_status
            if note is not None:
                record["note"] = note
            record["history"].append(
                {"from": current, "to": new_status, "by": actor_name(actor), "utc": now}
            )
            record["updated_utc"] = now
            self._audit(
                actor,
                "authorization_transition",
                auth_id,
                details={"from": current, "to": new_status},
            )
            return self._copy_auth(record)

    # -- posture reporting ---------------------------------------------------

    def posture_summary(self, actor, as_of=None):
        """Return the posture summary, computed on read from the
        records: counts by framework / system / status only. No
        computed risk score or aggregate rating is produced. The
        ``overdue`` count is derived at read time from due dates,
        lifecycle states, and the as-of date (default: today, UTC).
        Does not audit."""
        _maybe_require(actor, "read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            controls_by_framework = {}
            for (framework_id, _) in self._controls:
                controls_by_framework[framework_id] = (
                    controls_by_framework.get(framework_id, 0) + 1
                )

            findings_by_status = {name: 0 for name in FINDING_STATUSES}
            findings_by_severity = {}
            findings_by_system = {}
            open_count = 0
            overdue_count = 0
            for finding in self._findings.values():
                findings_by_status[finding["status"]] += 1
                severity = finding["severity"]
                findings_by_severity[severity] = (
                    findings_by_severity.get(severity, 0) + 1
                )
                findings_by_system[finding["system_ref"]] = (
                    findings_by_system.get(finding["system_ref"], 0) + 1
                )
                if finding["status"] in OPEN_STATES:
                    open_count += 1
                if derive_finding_status(finding, as_of_date) == "overdue":
                    overdue_count += 1

            results_by_status = {}
            for result in self._results.values():
                status = result["status"]
                results_by_status[status] = results_by_status.get(status, 0) + 1

            evidence_by_status = {}
            for evidence in self._evidence.values():
                status = evidence["validation_status"]
                evidence_by_status[status] = evidence_by_status.get(status, 0) + 1

            assessments_by_result = {}
            for assessment in self._assessments.values():
                result = assessment["result"]
                assessments_by_result[result] = (
                    assessments_by_result.get(result, 0) + 1
                )

            auth_by_status = {name: 0 for name in AUTH_STATUSES}
            for record in self._authorizations.values():
                auth_by_status[record["status"]] += 1

            return {
                "as_of": as_of_date.isoformat(),
                "frameworks": {
                    "total": len(self._frameworks),
                    "controls_total": len(self._controls),
                    "controls_by_framework": controls_by_framework,
                },
                "systems": {"total": len(self._systems)},
                "indicators": {
                    "total": len(self._indicators),
                    "results_total": len(self._results),
                    "results_by_status": results_by_status,
                },
                "evidence": {
                    "total": len(self._evidence),
                    "by_validation_status": evidence_by_status,
                },
                "findings": {
                    "total": len(self._findings),
                    "by_status": findings_by_status,
                    "by_severity": findings_by_severity,
                    "by_system": findings_by_system,
                    "open": open_count,
                    "overdue": overdue_count,
                },
                "assessments": {
                    "total": len(self._assessments),
                    "by_result": assessments_by_result,
                },
                "authorizations": {
                    "total": len(self._authorizations),
                    "by_status": auth_by_status,
                },
            }
