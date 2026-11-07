"""Final GAPS batch extensions — Untiered Set 3, Governance, Risk,
and Compliance (GRC).

This module is the set's final-GAPS-batch extension surface (see
``BATCH.md`` in the group directory and
``gaps-batch/DECISION.md`` at the repo root). It wraps the carried
core substrate (:class:`grc.store.GrcStore`) without modifying it:
every pre-existing core module stays byte-identical.

What lives here, per GAPS.md entry (Untiered Set 3 section):

Built (records plus the substrate's derivations):

- **Automated evidence collection & validation engine** —
  collection-run records (a run is a record of a reported
  collection; nothing is collected here) and evidence-review
  records. A review outcome is recorded verbatim by a reviewer and
  never computed, and it never modifies the core evidence record:
  the core's recorded validation status remains the core reviewer's
  field. Separation of duties: the actor who filed an evidence
  artifact in the core may not record its batch review
  (``_check_reviewer_not_filer``).
- **Vulnerability scanning engine** — a scanner registry plus scan
  report records. A report's findings land as ordinary core finding
  records with severity recorded verbatim; no scan executes and no
  prioritization is computed.
- **Posture & risk scoring engines** — built in records form only
  (re-judgment of form, recorded in BATCH.md): scoring-RULE records
  whose text is held as data and never applied, and REPORTED score
  records whose label is stored verbatim as an external engine
  reported it. This build computes no score anywhere; posture over
  the extension surface is counts of recorded labels only.
- **Hosted enclave & PaaS operations** — enclave records plus
  hosting-state records stored exactly as reported; nothing is
  hosted here (PLATFORM-LAYER.md decision 6).
- **FedRAMP package generation** — package records whose manifest
  deterministically assembles records the substrate already holds
  (controls, evidence, findings, assessments, authorizations,
  policies) for one system under one framework. Assembly only: no
  narrative text is generated and no document is emitted.
- **Policy lifecycle engine** — policy records with a guarded
  lifecycle; the current state is derived at read from the recorded
  transition history and never stored, and attestation status is
  derived at read from the current state plus the recorded expiry
  date. Attestation outcome records store the attestor's reported
  outcome verbatim.

Labeled reference implementations (``reference_stub: True`` on every
record; records only, never execution):

- **Continuous-monitoring feeds & scanner integrations** — feed
  records plus receipt records (also ``reference_transport: True``;
  nothing is connected to or ingested).
- **Automated KSI validation** — machine-checkable rule records
  plus evaluation records whose outcomes are stored verbatim as
  reported; no rule is ever evaluated here.
- **Agentic workflow execution** — workflow-run records plus step
  records with reported statuses; nothing executes.
- **AI control-narrative & assessment-response generation** —
  generation-request records plus reported-outcome records; no text
  is generated (``narrative_text`` is null on every request).
- **Data-integration connector engine** — connector records plus
  run records (also ``reference_transport: True``; nothing is
  connected to and no data moves).
- **Fork excess** (healthcare quality suite; AI/ML governance
  evaluation engine; digital-twin OSCAL analysis engine; no-code
  BPM platform) — one reference profile record per excess kind plus
  reported-outcome records; nothing is computed or executed.

Cross-cutting doctrines, inherited from the set: **tier stays
null** — nothing here asserts a baseline, a tier, or any
equivalence, and no record carries a tier-shaped or baseline-shaped
key (pinned by a recursive key scan in the tests); **no score is
computed anywhere** — the same recursive scan pins that no
score-shaped key appears on any returned value; statuses and
outcomes the forks' engines produced are **recorded verbatim**;
every computed value is **derived at read, never stored**; RBAC via
the existing :mod:`grc.access` actions, enforced before any state
change or id allocation, so failed operations consume no id; every
successful mutation is recorded on the core audit log with an
``ext_``-prefixed action, and denied write attempts are recorded
with a ``:denied`` suffix. Records hold opaque references only.
"""

import copy
import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

POLICY_STATES = (
    "draft",
    "in_review",
    "approved",
    "published",
    "attested",
    "superseded",
    "retired",
)

POLICY_TRANSITIONS = {
    "draft": {"in_review", "retired"},
    "in_review": {"approved", "draft", "retired"},
    "approved": {"published", "attested", "superseded", "retired"},
    "published": {"attested", "superseded", "retired"},
    "attested": {"published", "superseded", "retired"},
    "superseded": {"retired"},
    "retired": set(),
}

FEED_KINDS = ("monitoring_feed", "scanner_integration")

NARRATIVE_KINDS = ("control_narrative", "assessment_response")

EXCESS_KINDS = (
    "healthcare_quality",
    "ai_ml_governance_evaluation",
    "digital_twin_oscal_analysis",
    "no_code_bpm",
)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_text(value, what):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _validate_count(value, what):
    """Validate a reported count: a non-negative int (booleans and
    floats are rejected, never coerced)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if value < 0:
        raise ValidationError("%s must be non-negative" % (what,))
    return value


def _validate_ref_list(value, what):
    """Validate an optional list of non-empty reference strings;
    duplicates collapse, order is preserved."""
    if value is None:
        return []
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValidationError(
            "%s must be a list of non-empty strings" % (what,)
        )
    result = []
    for item in value:
        if item not in result:
            result.append(item)
    return result


def _validate_date(value, what):
    if not isinstance(value, str):
        raise ValidationError("%s must be an ISO date string" % (what,))
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationError(
            "%s must be an ISO date (YYYY-MM-DD): %r" % (what, value)
        ) from None


def _validate_timestamp(value, what):
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


def _as_of_date(as_of):
    """Coerce an as-of parameter to a :class:`datetime.date`
    (``None`` means today, UTC), mirroring the core's coercion."""
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


def _check_reviewer_not_filer(filed_by, reviewer):
    """Separation-of-duties seam for batch evidence reviews.

    The actor who filed an evidence artifact in the core may not
    record its batch review: a review outcome must come from a
    different actor than the filer. This is the load-bearing guard
    behind :meth:`GrcExtensions.record_evidence_review` and the
    mutation target of this unit's fresh negative control (see
    tests/README.md).
    """
    if filed_by is not None and reviewer is not None and filed_by == reviewer:
        raise ValidationError(
            "evidence reviewer must differ from the artifact's filer (%r)"
            % (filed_by,)
        )


class GrcExtensions:
    """The final-GAPS-batch extension surface over a core store."""

    def __init__(self, store):
        self.store = store
        self.audit = store.audit
        self._lock = threading.RLock()
        self._counters = {
            "col": 0, "evr": 0, "scr": 0, "srl": 0, "rps": 0, "hst": 0,
            "pkg": 0, "pol": 0, "att": 0, "frc": 0, "kev": 0,
            "wfs": 0, "nar": 0, "nao": 0, "cnr": 0, "exc": 0,
            "exo": 0,
        }
        self._collection_runs = {}
        self._evidence_reviews = {}
        self._scanners = {}  # caller-supplied ref -> record
        self._scan_reports = {}
        self._scoring_rules = {}
        self._reported_scores = {}
        self._enclaves = {}  # caller-supplied ref -> record
        self._hosting_states = {}
        self._packages = {}
        self._policies = {}
        self._policy_transitions = {}  # policy id -> [transition dicts]
        self._attestations = {}
        self._feeds = {}  # caller-supplied ref -> record
        self._feed_receipts = {}
        self._ksi_rules = {}  # caller-supplied ref -> record
        self._ksi_evaluations = {}
        self._workflow_runs = {}  # caller-supplied ref -> record
        self._workflow_steps = {}
        self._narrative_requests = {}
        self._narrative_outcomes = {}
        self._connectors = {}  # caller-supplied ref -> record
        self._connector_runs = {}
        self._excess_profiles = {}
        self._excess_outcomes = {}

    # -- internal helpers ---------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _guard(self, actor, action, audit_action, target):
        """Enforce ``action`` for a write; a denial is audited with a
        ``:denied`` suffix before the error propagates."""
        try:
            require(actor, action)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", target)
            raise

    @staticmethod
    def _get(collection, key, what):
        record = collection.get(key)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, key))
        return record

    @staticmethod
    def _copy(record, list_fields=()):
        copied = dict(record)
        for field in list_fields:
            copied[field] = list(record[field])
        return copied

    # -- automated evidence collection & validation (built) ------------

    def create_collection_run(
        self, name, system_ref, source_label, actor,
        control_ids=None, description="",
    ):
        """Record an evidence collection run against a governed
        system. Action: manage_evidence. Id prefix: ``col-``.

        A run is a *record* of a collection reported to have
        happened elsewhere: the record carries
        ``reference_transport: True`` and ``collected_here: False``,
        and creating one changes no core record — evidence artifacts
        themselves are filed through the core evidence registry.
        """
        self._guard(actor, "manage_evidence", "ext_collection_run_create", name)
        _validate_non_empty(name, "collection run name")
        _validate_non_empty(source_label, "collection source label")
        description = _validate_text(description, "collection run description")
        control_ids = _validate_ref_list(control_ids, "control ids")
        with self._lock:
            self.store.get_system(system_ref, actor)
            known = {c["id"] for c in self.store.list_controls(actor)}
            for control_id in control_ids:
                if control_id not in known:
                    raise ValidationError("unknown control id: %r" % (control_id,))
            run_id = self._next_id("col")
            run = {
                "id": run_id,
                "name": name,
                "system_ref": system_ref,
                "source_label": source_label,
                "control_ids": control_ids,
                "description": description,
                "reference_transport": True,
                "collected_here": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._collection_runs[run_id] = run
            self._audit(
                actor, "ext_collection_run_create", run_id,
                details={"system_ref": system_ref},
            )
            return self._copy(run, ("control_ids",))

    def get_collection_run(self, run_id, actor):
        """Return one collection-run record. Action: read."""
        require(actor, "read")
        with self._lock:
            return self._copy(
                self._get(self._collection_runs, run_id, "collection run"),
                ("control_ids",),
            )

    def list_collection_runs(self, actor, system_ref=None):
        """Return collection-run records, optionally filtered by
        system, in id order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [
                self._copy(run, ("control_ids",))
                for run in self._collection_runs.values()
                if system_ref is None or run["system_ref"] == system_ref
            ]

    def record_evidence_review(self, evidence_id, validation_status, actor, note=""):
        """Record a batch review outcome for a core evidence
        artifact. Action: review_evidence. Id prefix: ``evr-``.

        The outcome is stored **verbatim**, exactly as the reviewer
        supplied it; nothing is computed. The record is a batch-layer
        record only — the core evidence record, including its own
        recorded validation status, is never modified by this
        surface (``applied_to_core: False``). Separation of duties:
        the artifact's filer may not record its review
        (``_check_reviewer_not_filer``).
        """
        self._guard(
            actor, "review_evidence", "ext_evidence_review_create", evidence_id
        )
        _validate_non_empty(validation_status, "validation status")
        note = _validate_text(note, "review note")
        with self._lock:
            evidence = self.store.get_evidence(evidence_id, actor)
            _check_reviewer_not_filer(evidence["created_by"], actor_name(actor))
            review_id = self._next_id("evr")
            review = {
                "id": review_id,
                "evidence_id": evidence_id,
                "validation_status": validation_status,
                "note": note,
                "reviewed_by": actor_name(actor),
                "reviewed_utc": _utc_now(),
                "applied_to_core": False,
                "state": "recorded_reference_only",
            }
            self._evidence_reviews[review_id] = review
            self._audit(
                actor, "ext_evidence_review_create", review_id,
                details={"evidence_id": evidence_id},
            )
            return dict(review)

    def list_evidence_reviews(self, actor, evidence_id=None):
        """Return batch evidence-review records, optionally filtered
        by evidence artifact, in id order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [
                dict(review)
                for review in self._evidence_reviews.values()
                if evidence_id is None or review["evidence_id"] == evidence_id
            ]

    def evidence_review_summary(self, actor):
        """Counts of batch evidence reviews by recorded validation
        status, derived at read. Counts only. Action: read."""
        require(actor, "read")
        with self._lock:
            by_status = {}
            for review in self._evidence_reviews.values():
                status = review["validation_status"]
                by_status[status] = by_status.get(status, 0) + 1
            return {
                "total": len(self._evidence_reviews),
                "by_validation_status": by_status,
                "method": "deterministic_counts",
            }

    # -- vulnerability scanning (built) ---------------------------------

    def create_scanner(self, scanner_ref, name, actor, description=""):
        """Register a scanner under a caller-supplied opaque
        reference. Action: manage_findings.

        Registration is a record: the scanner is an external engine;
        this build runs no scan."""
        self._guard(actor, "manage_findings", "ext_scanner_create", scanner_ref)
        _validate_non_empty(scanner_ref, "scanner reference")
        _validate_non_empty(name, "scanner name")
        description = _validate_text(description, "scanner description")
        with self._lock:
            if scanner_ref in self._scanners:
                raise ValidationError(
                    "scanner reference already registered: %r" % (scanner_ref,)
                )
            scanner = {
                "ref": scanner_ref,
                "name": name,
                "description": description,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._scanners[scanner_ref] = scanner
            self._audit(
                actor, "ext_scanner_create", scanner_ref, details={"name": name}
            )
            return dict(scanner)

    def get_scanner(self, scanner_ref, actor):
        """Return one scanner record. Action: read."""
        require(actor, "read")
        with self._lock:
            return dict(self._get(self._scanners, scanner_ref, "scanner"))

    def list_scanners(self, actor):
        """Return scanner records in registration order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [dict(scanner) for scanner in self._scanners.values()]

    def record_scan_report(
        self, scanner_ref, system_ref, reported_at, actor,
        findings_reported=(), note="",
    ):
        """Record a scan report from a registered scanner against a
        governed system. Action: manage_findings. Id prefix:
        ``scr-``.

        ``findings_reported`` is a list of finding-shaped dicts
        (``title``, ``severity``, ``source``, ``due_date``, optional
        ``description`` and ``control_ids``). Every item is validated
        fully before anything is recorded; each then lands as an
        ordinary **core finding record** through the core store —
        severity verbatim, lifecycle and read-time derivation exactly
        the core's. The report record links the created finding ids.
        No scan executes here (``executed_here: False``) and no
        prioritization is computed from the reported severities.
        """
        self._guard(actor, "manage_findings", "ext_scan_report_create", scanner_ref)
        reported_at = _validate_timestamp(reported_at, "reported_at")
        note = _validate_text(note, "scan report note")
        if findings_reported is None:
            findings_reported = ()
        if not isinstance(findings_reported, (list, tuple)):
            raise ValidationError("findings_reported must be a list of dicts")
        with self._lock:
            self._get(self._scanners, scanner_ref, "scanner")
            self.store.get_system(system_ref, actor)
            known = {c["id"] for c in self.store.list_controls(actor)}
            items = []
            for index, item in enumerate(findings_reported):
                if not isinstance(item, dict):
                    raise ValidationError(
                        "findings_reported[%d] must be a dict" % index
                    )
                title = _validate_non_empty(
                    item.get("title"), "reported finding title"
                )
                severity = _validate_non_empty(
                    item.get("severity"), "reported finding severity"
                )
                source = _validate_non_empty(
                    item.get("source"), "reported finding source"
                )
                due_date = item.get("due_date")
                _validate_date(due_date, "reported finding due_date")
                description = _validate_text(
                    item.get("description"), "reported finding description"
                )
                control_ids = _validate_ref_list(
                    item.get("control_ids"), "reported finding control ids"
                )
                for control_id in control_ids:
                    if control_id not in known:
                        raise ValidationError(
                            "unknown control id: %r" % (control_id,)
                        )
                items.append(
                    {
                        "title": title,
                        "severity": severity,
                        "source": source,
                        "due_date": due_date,
                        "description": description,
                        "control_ids": control_ids,
                    }
                )
            finding_ids = []
            for item in items:
                finding = self.store.create_finding(
                    item["title"],
                    system_ref,
                    item["severity"],
                    item["source"],
                    item["due_date"],
                    actor,
                    description=item["description"],
                    control_ids=item["control_ids"],
                )
                finding_ids.append(finding["id"])
            report_id = self._next_id("scr")
            report = {
                "id": report_id,
                "scanner_ref": scanner_ref,
                "system_ref": system_ref,
                "reported_at": reported_at,
                "finding_ids": finding_ids,
                "reported_count": len(finding_ids),
                "executed_here": False,
                "state": "recorded_reference_only",
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._scan_reports[report_id] = report
            self._audit(
                actor, "ext_scan_report_create", report_id,
                details={"scanner_ref": scanner_ref, "system_ref": system_ref},
            )
            return self._copy(report, ("finding_ids",))

    def get_scan_report(self, report_id, actor):
        """Return one scan-report record. Action: read."""
        require(actor, "read")
        with self._lock:
            return self._copy(
                self._get(self._scan_reports, report_id, "scan report"),
                ("finding_ids",),
            )

    def list_scan_reports(self, actor, scanner_ref=None, system_ref=None):
        """Return scan-report records, optionally filtered, in id
        order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [
                self._copy(report, ("finding_ids",))
                for report in self._scan_reports.values()
                if (scanner_ref is None or report["scanner_ref"] == scanner_ref)
                and (system_ref is None or report["system_ref"] == system_ref)
            ]

    def scan_report_summary(self, actor):
        """Counts over scan reports, derived at read: report total
        and total findings landed. Counts only. Action: read."""
        require(actor, "read")
        with self._lock:
            return {
                "reports_total": len(self._scan_reports),
                "scanners_total": len(self._scanners),
                "findings_reported_total": sum(
                    report["reported_count"]
                    for report in self._scan_reports.values()
                ),
                "method": "deterministic_counts",
            }

    # -- posture & risk scoring engines (built, records form only) -------

    def create_scoring_rule(self, name, rule_text, actor, description=""):
        """Record a scoring rule as data. Action: manage_frameworks.
        Id prefix: ``srl-``.

        The rule's text is held verbatim and is **never applied** to
        any record by this substrate (``method:
        recorded_rules_only``, ``applied_here: False``). This is the
        records form of the scoring entry: the claiming forks' own
        engines score; this build holds their rules as data.
        """
        self._guard(actor, "manage_frameworks", "ext_scoring_rule_create", name)
        _validate_non_empty(name, "scoring rule name")
        _validate_non_empty(rule_text, "scoring rule text")
        description = _validate_text(description, "scoring rule description")
        with self._lock:
            rule_id = self._next_id("srl")
            rule = {
                "id": rule_id,
                "name": name,
                "rule_text": rule_text,
                "description": description,
                "method": "recorded_rules_only",
                "applied_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._scoring_rules[rule_id] = rule
            self._audit(
                actor, "ext_scoring_rule_create", rule_id, details={"name": name}
            )
            return dict(rule)

    def get_scoring_rule(self, rule_id, actor):
        """Return one scoring-rule record. Action: read."""
        require(actor, "read")
        with self._lock:
            return dict(self._get(self._scoring_rules, rule_id, "scoring rule"))

    def list_scoring_rules(self, actor):
        """Return scoring-rule records in id order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [dict(rule) for rule in self._scoring_rules.values()]

    def record_reported_score(
        self, system_ref, label, actor,
        source_ref=None, framework_id=None, note="",
    ):
        """Record a score label exactly as an external engine
        reported it. Action: record_results. Id prefix: ``rps-``.

        ``label`` is stored **verbatim** — a fork's own rating in the
        fork's own words (for example a PAIN-style band). This build
        computes nothing from it (``computed_here: False``); the
        label is data the fork's engine produced, recorded here.
        """
        self._guard(actor, "record_results", "ext_reported_score_create", system_ref)
        _validate_non_empty(label, "reported score label")
        if source_ref is not None:
            _validate_non_empty(source_ref, "score source reference")
        note = _validate_text(note, "reported score note")
        with self._lock:
            self.store.get_system(system_ref, actor)
            if framework_id is not None:
                self.store.get_framework(framework_id, actor)
            record_id = self._next_id("rps")
            record = {
                "id": record_id,
                "system_ref": system_ref,
                "framework_id": framework_id,
                "label": label,
                "source_ref": source_ref,
                "note": note,
                "reported_by": actor_name(actor),
                "reported_utc": _utc_now(),
                "computed_here": False,
                "state": "recorded_reference_only",
            }
            self._reported_scores[record_id] = record
            self._audit(
                actor, "ext_reported_score_create", record_id,
                details={"system_ref": system_ref},
            )
            return dict(record)

    def list_reported_scores(self, actor, system_ref=None):
        """Return reported-score records, optionally filtered by
        system, in id order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._reported_scores.values()
                if system_ref is None or record["system_ref"] == system_ref
            ]

    def reported_score_summary(self, actor):
        """Counts of reported-score records by their verbatim label,
        derived at read. The labels are counted, never aggregated
        into any value. Action: read."""
        require(actor, "read")
        with self._lock:
            by_label = {}
            for record in self._reported_scores.values():
                label = record["label"]
                by_label[label] = by_label.get(label, 0) + 1
            return {
                "total": len(self._reported_scores),
                "by_label": by_label,
                "method": "deterministic_counts",
            }

    # -- hosted enclave & PaaS operations (built, records form) ----------

    def create_enclave(
        self, enclave_ref, name, actor, system_refs=None, description="",
    ):
        """Register an enclave record under a caller-supplied opaque
        reference. Action: manage_systems.

        The record describes a hosting arrangement the forks'
        platforms operate; this build hosts nothing
        (``hosted_here: False``, PLATFORM-LAYER.md decision 6) and
        the record's state is ``recorded_reference_only``."""
        self._guard(actor, "manage_systems", "ext_enclave_create", enclave_ref)
        _validate_non_empty(enclave_ref, "enclave reference")
        _validate_non_empty(name, "enclave name")
        description = _validate_text(description, "enclave description")
        system_refs = _validate_ref_list(system_refs, "system references")
        with self._lock:
            if enclave_ref in self._enclaves:
                raise ValidationError(
                    "enclave reference already registered: %r" % (enclave_ref,)
                )
            for ref in system_refs:
                self.store.get_system(ref, actor)
            now = _utc_now()
            enclave = {
                "ref": enclave_ref,
                "name": name,
                "description": description,
                "system_refs": system_refs,
                "hosted_here": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._enclaves[enclave_ref] = enclave
            self._audit(
                actor, "ext_enclave_create", enclave_ref, details={"name": name}
            )
            return self._copy(enclave, ("system_refs",))

    def record_hosting_state(self, enclave_ref, reported_state, actor, note=""):
        """Record a hosting state for an enclave exactly as reported.
        Action: manage_systems. Id prefix: ``hst-``.

        The state is an external platform's reported condition,
        stored verbatim; this build observes and changes nothing."""
        self._guard(actor, "manage_systems", "ext_hosting_state_create", enclave_ref)
        _validate_non_empty(reported_state, "reported hosting state")
        note = _validate_text(note, "hosting state note")
        with self._lock:
            enclave = self._get(self._enclaves, enclave_ref, "enclave")
            state_id = self._next_id("hst")
            record = {
                "id": state_id,
                "enclave_ref": enclave_ref,
                "reported_state": reported_state,
                "note": note,
                "reported_by": actor_name(actor),
                "reported_utc": _utc_now(),
            }
            self._hosting_states[state_id] = record
            enclave["updated_utc"] = record["reported_utc"]
            self._audit(
                actor, "ext_hosting_state_create", state_id,
                details={"enclave_ref": enclave_ref},
            )
            return dict(record)

    def _enclave_view(self, enclave):
        view = self._copy(enclave, ("system_refs",))
        states = [
            dict(record)
            for record in self._hosting_states.values()
            if record["enclave_ref"] == enclave["ref"]
        ]
        view["reported_states"] = states
        # The current reported state is the latest record's state,
        # derived at read from the state records — never stored.
        view["current_reported_state"] = (
            states[-1]["reported_state"] if states else None
        )
        return view

    def get_enclave(self, enclave_ref, actor):
        """Return one enclave record with its reported states and
        the derived current reported state. Action: read."""
        require(actor, "read")
        with self._lock:
            return self._enclave_view(
                self._get(self._enclaves, enclave_ref, "enclave")
            )

    def list_enclaves(self, actor):
        """Return enclave views in registration order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [
                self._enclave_view(enclave)
                for enclave in self._enclaves.values()
            ]

    def enclave_summary(self, actor):
        """Counts over enclave and hosting-state records, derived at
        read. Counts only. Action: read."""
        require(actor, "read")
        with self._lock:
            by_state = {}
            for record in self._hosting_states.values():
                state = record["reported_state"]
                by_state[state] = by_state.get(state, 0) + 1
            return {
                "enclaves_total": len(self._enclaves),
                "states_total": len(self._hosting_states),
                "states_by_reported_state": by_state,
                "method": "deterministic_counts",
            }

    # -- FedRAMP package generation (built, manifest assembly) -----------

    def create_package(self, system_ref, framework_id, actor, as_of=None, note=""):
        """Assemble an authorization-package record for one system
        under one framework. Action: manage_assessments. Id prefix:
        ``pkg-``.

        The package's manifest deterministically assembles records
        the substrate already holds — the framework's controls, the
        system's evidence (with recorded validation statuses), its
        findings (with read-time derived statuses at ``as_of``), its
        assessments and authorization records under the framework,
        and this extension's policy records for the system under the
        framework — plus counts derived from that assembly. Assembly
        only: no narrative text is generated
        (``narrative_generated: False``) and no document is emitted
        (``documents_emitted: False``). The manifest is a snapshot of
        the held records at creation; later changes do not rewrite
        it.
        """
        self._guard(actor, "manage_assessments", "ext_package_create", system_ref)
        note = _validate_text(note, "package note")
        as_of_date = _as_of_date(as_of)
        with self._lock:
            system = self.store.get_system(system_ref, actor)
            framework = self.store.get_framework(framework_id, actor)
            controls = [
                {
                    "id": control["id"],
                    "family": control["family"],
                    "title": control["title"],
                }
                for control in self.store.list_controls(actor, framework_id)
            ]
            evidence = [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "sha256": item["sha256"],
                    "validation_status": item["validation_status"],
                    "control_ids": list(item["control_ids"]),
                }
                for item in self.store.list_evidence(actor, system_ref=system_ref)
            ]
            findings = []
            findings_by_status = {}
            for finding in self.store.list_findings(
                actor, system_ref=system_ref, as_of=as_of_date
            ):
                findings.append(
                    {
                        "id": finding["id"],
                        "title": finding["title"],
                        "severity": finding["severity"],
                        "status": finding["status"],
                        "derived_status": finding["derived_status"],
                        "due_date": finding["due_date"],
                    }
                )
                status = finding["status"]
                findings_by_status[status] = findings_by_status.get(status, 0) + 1
            assessments = [
                {
                    "id": item["id"],
                    "result": item["result"],
                    "date": item["date"],
                    "assessor": item["assessor"],
                }
                for item in self.store.list_assessments(
                    actor, system_ref=system_ref, framework_id=framework_id
                )
            ]
            authorizations = [
                {"id": item["id"], "status": item["status"]}
                for item in self.store.list_authorizations(
                    actor, system_ref=system_ref
                )
                if item["framework_id"] == framework_id
            ]
            policies = []
            for policy in self._policies.values():
                if (
                    policy["system_ref"] == system_ref
                    and policy["framework_id"] == framework_id
                ):
                    policies.append(
                        {
                            "id": policy["id"],
                            "title": policy["title"],
                            "current_state": self._policy_current_state(policy),
                        }
                    )
            manifest = {
                "system": {"ref": system["ref"], "name": system["name"]},
                "framework": {
                    "id": framework["id"],
                    "name": framework["name"],
                    "version": framework["version"],
                },
                "controls": controls,
                "evidence": evidence,
                "findings": findings,
                "assessments": assessments,
                "authorizations": authorizations,
                "policies": policies,
            }
            counts = {
                "controls_total": len(controls),
                "evidence_total": len(evidence),
                "findings_total": len(findings),
                "findings_by_status": findings_by_status,
                "assessments_total": len(assessments),
                "authorizations_total": len(authorizations),
                "policies_total": len(policies),
            }
            package_id = self._next_id("pkg")
            package = {
                "id": package_id,
                "system_ref": system_ref,
                "framework_id": framework_id,
                "as_of": as_of_date.isoformat(),
                "manifest": manifest,
                "counts": counts,
                "method": "deterministic_manifest_assembly",
                "narrative_generated": False,
                "documents_emitted": False,
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._packages[package_id] = package
            self._audit(
                actor, "ext_package_create", package_id,
                details={"system_ref": system_ref, "framework_id": framework_id},
            )
            return copy.deepcopy(package)

    def get_package(self, package_id, actor):
        """Return one package record (a deep copy; the stored
        manifest snapshot is never aliased). Action: read."""
        require(actor, "read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._packages, package_id, "package")
            )

    def list_packages(self, actor, system_ref=None):
        """Return package records, optionally filtered by system, in
        id order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [
                copy.deepcopy(package)
                for package in self._packages.values()
                if system_ref is None or package["system_ref"] == system_ref
            ]

    # -- policy lifecycle engine (built) ----------------------------------

    def create_policy(
        self, title, actor, system_ref=None, framework_id=None,
        expires_on=None, initial_state="draft", description="",
    ):
        """Create a policy record. Action: manage_frameworks. Id
        prefix: ``pol-``.

        The record stores its *initial* lifecycle state only; the
        current state is derived at read from the recorded
        transition history (see :meth:`get_policy`) and is never
        stored on the record."""
        self._guard(actor, "manage_frameworks", "ext_policy_create", title)
        _validate_non_empty(title, "policy title")
        description = _validate_text(description, "policy description")
        if initial_state not in POLICY_STATES:
            raise ValidationError(
                "initial_state must be one of %s" % (", ".join(POLICY_STATES),)
            )
        if expires_on is not None:
            _validate_date(expires_on, "policy expiry date")
        with self._lock:
            if system_ref is not None:
                self.store.get_system(system_ref, actor)
            if framework_id is not None:
                self.store.get_framework(framework_id, actor)
            policy_id = self._next_id("pol")
            now = _utc_now()
            policy = {
                "id": policy_id,
                "title": title,
                "description": description,
                "system_ref": system_ref,
                "framework_id": framework_id,
                "expires_on": expires_on,
                "initial_state": initial_state,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._policies[policy_id] = policy
            self._policy_transitions[policy_id] = []
            self._audit(
                actor, "ext_policy_create", policy_id, details={"title": title}
            )
            return dict(policy)

    def _policy_current_state(self, policy):
        """Derive a policy's current lifecycle state: the last
        recorded transition's target, or the initial state when no
        transition has been recorded. Computed on every call; never
        stored."""
        transitions = self._policy_transitions[policy["id"]]
        if transitions:
            return transitions[-1]["to"]
        return policy["initial_state"]

    def transition_policy(self, policy_id, to_state, actor, note=""):
        """Move a policy through its lifecycle, per
        ``POLICY_TRANSITIONS``. Action: manage_frameworks.

        The transition is appended to the policy's history; the
        stored policy record itself gains no state field."""
        self._guard(actor, "manage_frameworks", "ext_policy_transition", policy_id)
        note = _validate_text(note, "policy transition note")
        with self._lock:
            policy = self._get(self._policies, policy_id, "policy")
            current = self._policy_current_state(policy)
            if (
                to_state not in POLICY_STATES
                or to_state not in POLICY_TRANSITIONS[current]
            ):
                raise ValidationError(
                    "policy cannot move from %r to %r" % (current, to_state)
                )
            now = _utc_now()
            self._policy_transitions[policy_id].append(
                {
                    "from": current,
                    "to": to_state,
                    "by": actor_name(actor),
                    "utc": now,
                    "note": note,
                }
            )
            policy["updated_utc"] = now
            self._audit(
                actor, "ext_policy_transition", policy_id,
                details={"from": current, "to": to_state},
            )
            return self._policy_view(policy, None)

    def record_attestation(self, policy_id, attestor_ref, outcome, actor, note=""):
        """Record an attestation outcome for a policy. Action:
        manage_frameworks. Id prefix: ``att-``.

        ``outcome`` is stored **verbatim**, exactly as the attestor
        reported it. The record decides nothing about the policy
        (``decision_made: False``); the policy's lifecycle moves only
        through :meth:`transition_policy`."""
        self._guard(actor, "manage_frameworks", "ext_attestation_create", policy_id)
        _validate_non_empty(attestor_ref, "attestor reference")
        _validate_non_empty(outcome, "attestation outcome")
        note = _validate_text(note, "attestation note")
        with self._lock:
            self._get(self._policies, policy_id, "policy")
            attestation_id = self._next_id("att")
            record = {
                "id": attestation_id,
                "policy_id": policy_id,
                "attestor_ref": attestor_ref,
                "outcome": outcome,
                "note": note,
                "decision_made": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._attestations[attestation_id] = record
            self._audit(
                actor, "ext_attestation_create", attestation_id,
                details={"policy_id": policy_id},
            )
            return dict(record)

    def list_attestations(self, actor, policy_id=None):
        """Return attestation records, optionally filtered by
        policy, in id order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._attestations.values()
                if policy_id is None or record["policy_id"] == policy_id
            ]

    def _policy_view(self, policy, as_of):
        view = dict(policy)
        transitions = [
            dict(step) for step in self._policy_transitions[policy["id"]]
        ]
        view["transitions"] = transitions
        current = self._policy_current_state(policy)
        view["current_state"] = current
        # Attestation status is derived at read: a policy in the
        # attested state reads "attested"; an approved or published
        # policy past its recorded expiry date reads "expired";
        # anything else has not been attested.
        if current == "attested":
            view["attestation_status"] = "attested"
        elif (
            current in ("approved", "published")
            and policy["expires_on"] is not None
            and _as_of_date(as_of) > _validate_date(policy["expires_on"], "expires_on")
        ):
            view["attestation_status"] = "expired"
        else:
            view["attestation_status"] = "unattested"
        return view

    def get_policy(self, policy_id, actor, as_of=None):
        """Return one policy view: the stored record plus its
        transition history, the derived ``current_state``, and the
        derived ``attestation_status`` at ``as_of``. The stored
        record carries neither derived key. Action: read."""
        require(actor, "read")
        with self._lock:
            return self._policy_view(
                self._get(self._policies, policy_id, "policy"), as_of
            )

    def list_policies(self, actor, system_ref=None):
        """Return policy views, optionally filtered by system, in id
        order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [
                self._policy_view(policy, None)
                for policy in self._policies.values()
                if system_ref is None or policy["system_ref"] == system_ref
            ]

    def policy_summary(self, actor, as_of=None):
        """Counts of policies by derived current state and derived
        attestation status at ``as_of``, computed at read. Counts
        only. Action: read."""
        require(actor, "read")
        with self._lock:
            by_state = {}
            by_attestation = {}
            for policy in self._policies.values():
                view = self._policy_view(policy, as_of)
                state = view["current_state"]
                by_state[state] = by_state.get(state, 0) + 1
                status = view["attestation_status"]
                by_attestation[status] = by_attestation.get(status, 0) + 1
            return {
                "total": len(self._policies),
                "by_current_state": by_state,
                "by_attestation_status": by_attestation,
                "method": "deterministic_counts",
            }

    # -- continuous-monitoring feeds & scanner integrations (reference) ---

    def create_feed(self, feed_ref, name, actor, kind="monitoring_feed", description=""):
        """Register a feed / integration reference. Action:
        manage_indicators.

        Labeled reference implementation: the record carries
        ``reference_stub: True`` and ``reference_transport: True``;
        no feed is connected to and nothing is ingested."""
        self._guard(actor, "manage_indicators", "ext_feed_create", feed_ref)
        _validate_non_empty(feed_ref, "feed reference")
        _validate_non_empty(name, "feed name")
        if kind not in FEED_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(FEED_KINDS),)
            )
        description = _validate_text(description, "feed description")
        with self._lock:
            if feed_ref in self._feeds:
                raise ValidationError(
                    "feed reference already registered: %r" % (feed_ref,)
                )
            feed = {
                "ref": feed_ref,
                "name": name,
                "kind": kind,
                "description": description,
                "reference_stub": True,
                "reference_transport": True,
                "connected_here": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._feeds[feed_ref] = feed
            self._audit(actor, "ext_feed_create", feed_ref, details={"name": name})
            return dict(feed)

    def record_feed_receipt(self, feed_ref, actor, items_reported=0, note=""):
        """Record a feed delivery receipt. Action: record_results.
        Id prefix: ``frc-``.

        ``items_reported`` is a count as reported by the external
        feed; the items themselves never arrive here
        (``ingested_here: False``)."""
        self._guard(actor, "record_results", "ext_feed_receipt_create", feed_ref)
        items_reported = _validate_count(items_reported, "items_reported")
        note = _validate_text(note, "feed receipt note")
        with self._lock:
            self._get(self._feeds, feed_ref, "feed")
            receipt_id = self._next_id("frc")
            receipt = {
                "id": receipt_id,
                "feed_ref": feed_ref,
                "items_reported": items_reported,
                "note": note,
                "ingested_here": False,
                "reference_transport": True,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._feed_receipts[receipt_id] = receipt
            self._audit(
                actor, "ext_feed_receipt_create", receipt_id,
                details={"feed_ref": feed_ref},
            )
            return dict(receipt)

    def _feed_view(self, feed):
        view = dict(feed)
        receipts = [
            dict(receipt)
            for receipt in self._feed_receipts.values()
            if receipt["feed_ref"] == feed["ref"]
        ]
        view["receipts"] = receipts
        view["receipt_count"] = len(receipts)
        view["items_reported_total"] = sum(
            receipt["items_reported"] for receipt in receipts
        )
        return view

    def get_feed(self, feed_ref, actor):
        """Return one feed record with its receipts and derived
        totals. Action: read."""
        require(actor, "read")
        with self._lock:
            return self._feed_view(self._get(self._feeds, feed_ref, "feed"))

    def list_feeds(self, actor):
        """Return feed views in registration order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [self._feed_view(feed) for feed in self._feeds.values()]

    def list_feed_receipts(self, actor, feed_ref=None):
        """Return feed receipt records, optionally filtered, in id
        order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [
                dict(receipt)
                for receipt in self._feed_receipts.values()
                if feed_ref is None or receipt["feed_ref"] == feed_ref
            ]

    # -- automated KSI validation (reference) ------------------------------

    def create_ksi_rule(self, rule_ref, indicator_id, rule_text, actor, description=""):
        """Register a machine-checkable KSI rule as data against a
        core indicator. Action: manage_indicators.

        Labeled reference implementation: the rule text is held
        verbatim and is **never evaluated** here
        (``evaluated_here: False``)."""
        self._guard(actor, "manage_indicators", "ext_ksi_rule_create", rule_ref)
        _validate_non_empty(rule_ref, "KSI rule reference")
        _validate_non_empty(rule_text, "KSI rule text")
        description = _validate_text(description, "KSI rule description")
        with self._lock:
            if rule_ref in self._ksi_rules:
                raise ValidationError(
                    "KSI rule reference already registered: %r" % (rule_ref,)
                )
            self.store.get_indicator(indicator_id, actor)
            rule = {
                "ref": rule_ref,
                "indicator_id": indicator_id,
                "rule_text": rule_text,
                "description": description,
                "reference_stub": True,
                "evaluated_here": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._ksi_rules[rule_ref] = rule
            self._audit(
                actor, "ext_ksi_rule_create", rule_ref,
                details={"indicator_id": indicator_id},
            )
            return dict(rule)

    def record_ksi_evaluation(self, rule_ref, system_ref, outcome, actor, note=""):
        """Record an evaluation outcome for a KSI rule on a system.
        Action: record_results. Id prefix: ``kev-``.

        ``outcome`` is stored **verbatim**, exactly as the external
        validator reported it; this build evaluates nothing."""
        self._guard(actor, "record_results", "ext_ksi_evaluation_create", rule_ref)
        _validate_non_empty(outcome, "evaluation outcome")
        note = _validate_text(note, "evaluation note")
        with self._lock:
            rule = self._get(self._ksi_rules, rule_ref, "KSI rule")
            self.store.get_system(system_ref, actor)
            evaluation_id = self._next_id("kev")
            evaluation = {
                "id": evaluation_id,
                "rule_ref": rule_ref,
                "indicator_id": rule["indicator_id"],
                "system_ref": system_ref,
                "outcome": outcome,
                "note": note,
                "evaluated_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._ksi_evaluations[evaluation_id] = evaluation
            self._audit(
                actor, "ext_ksi_evaluation_create", evaluation_id,
                details={"rule_ref": rule_ref, "system_ref": system_ref},
            )
            return dict(evaluation)

    def get_ksi_rule(self, rule_ref, actor):
        """Return one KSI rule record. Action: read."""
        require(actor, "read")
        with self._lock:
            return dict(self._get(self._ksi_rules, rule_ref, "KSI rule"))

    def list_ksi_rules(self, actor):
        """Return KSI rule records in registration order. Action:
        read."""
        require(actor, "read")
        with self._lock:
            return [dict(rule) for rule in self._ksi_rules.values()]

    def list_ksi_evaluations(self, actor, rule_ref=None, system_ref=None):
        """Return KSI evaluation records, optionally filtered, in id
        order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [
                dict(evaluation)
                for evaluation in self._ksi_evaluations.values()
                if (rule_ref is None or evaluation["rule_ref"] == rule_ref)
                and (system_ref is None or evaluation["system_ref"] == system_ref)
            ]

    def ksi_evaluation_summary(self, actor):
        """Counts of KSI evaluations by recorded outcome, derived at
        read. Counts only. Action: read."""
        require(actor, "read")
        with self._lock:
            by_outcome = {}
            for evaluation in self._ksi_evaluations.values():
                outcome = evaluation["outcome"]
                by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
            return {
                "total": len(self._ksi_evaluations),
                "by_outcome": by_outcome,
                "method": "deterministic_counts",
            }

    # -- agentic workflow execution (reference) -----------------------------

    def create_workflow_run(
        self, workflow_ref, name, actor, system_ref=None, note="",
    ):
        """Register a workflow-run reference. Action:
        manage_assessments.

        Labeled reference implementation: the record carries
        ``reference_stub: True`` and ``executed: False`` — an agentic
        engine's run is recorded here as reported; no workflow
        executes in this substrate."""
        self._guard(actor, "manage_assessments", "ext_workflow_run_create", workflow_ref)
        _validate_non_empty(workflow_ref, "workflow run reference")
        _validate_non_empty(name, "workflow run name")
        note = _validate_text(note, "workflow run note")
        with self._lock:
            if workflow_ref in self._workflow_runs:
                raise ValidationError(
                    "workflow run reference already registered: %r" % (workflow_ref,)
                )
            if system_ref is not None:
                self.store.get_system(system_ref, actor)
            run = {
                "ref": workflow_ref,
                "name": name,
                "system_ref": system_ref,
                "note": note,
                "reference_stub": True,
                "executed": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workflow_runs[workflow_ref] = run
            self._audit(
                actor, "ext_workflow_run_create", workflow_ref,
                details={"name": name},
            )
            return dict(run)

    def record_workflow_step(self, run_ref, step_label, reported_status, actor, note=""):
        """Record one step of a workflow run, with its status exactly
        as reported. Action: manage_assessments. Id prefix:
        ``wfs-``. Nothing executes (``executed_here: False``)."""
        self._guard(actor, "manage_assessments", "ext_workflow_step_create", run_ref)
        _validate_non_empty(step_label, "workflow step label")
        _validate_non_empty(reported_status, "workflow step reported status")
        note = _validate_text(note, "workflow step note")
        with self._lock:
            self._get(self._workflow_runs, run_ref, "workflow run")
            step_id = self._next_id("wfs")
            step = {
                "id": step_id,
                "run_ref": run_ref,
                "step_label": step_label,
                "reported_status": reported_status,
                "note": note,
                "executed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._workflow_steps[step_id] = step
            self._audit(
                actor, "ext_workflow_step_create", step_id,
                details={"run_ref": run_ref},
            )
            return dict(step)

    def _workflow_run_view(self, run):
        view = dict(run)
        steps = [
            dict(step)
            for step in self._workflow_steps.values()
            if step["run_ref"] == run["ref"]
        ]
        view["steps"] = steps
        view["step_count"] = len(steps)
        return view

    def get_workflow_run(self, run_ref, actor):
        """Return one workflow-run record with its step records and
        derived step count. Action: read."""
        require(actor, "read")
        with self._lock:
            return self._workflow_run_view(
                self._get(self._workflow_runs, run_ref, "workflow run")
            )

    def list_workflow_runs(self, actor):
        """Return workflow-run views in registration order. Action:
        read."""
        require(actor, "read")
        with self._lock:
            return [
                self._workflow_run_view(run)
                for run in self._workflow_runs.values()
            ]

    def list_workflow_steps(self, actor, run_ref=None):
        """Return workflow step records, optionally filtered, in id
        order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [
                dict(step)
                for step in self._workflow_steps.values()
                if run_ref is None or step["run_ref"] == run_ref
            ]

    # -- AI control-narrative & assessment-response generation (reference) --

    def create_narrative_request(
        self, system_ref, kind, actor, control_ids=None, note="",
    ):
        """Register a narrative-generation request. Action:
        manage_assessments. Id prefix: ``nar-``.

        Labeled reference implementation: the request is recorded and
        no text is generated in response to it — ``generated_here``
        is False and ``narrative_text`` is null on every request
        record."""
        self._guard(actor, "manage_assessments", "ext_narrative_request_create", system_ref)
        if kind not in NARRATIVE_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(NARRATIVE_KINDS),)
            )
        note = _validate_text(note, "narrative request note")
        control_ids = _validate_ref_list(control_ids, "control ids")
        with self._lock:
            self.store.get_system(system_ref, actor)
            known = {c["id"] for c in self.store.list_controls(actor)}
            for control_id in control_ids:
                if control_id not in known:
                    raise ValidationError("unknown control id: %r" % (control_id,))
            request_id = self._next_id("nar")
            request = {
                "id": request_id,
                "system_ref": system_ref,
                "kind": kind,
                "control_ids": control_ids,
                "note": note,
                "reference_stub": True,
                "generated_here": False,
                "narrative_text": None,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._narrative_requests[request_id] = request
            self._audit(
                actor, "ext_narrative_request_create", request_id,
                details={"system_ref": system_ref, "kind": kind},
            )
            return self._copy(request, ("control_ids",))

    def record_narrative_outcome(self, request_id, reported_outcome, actor, note=""):
        """Record the reported outcome of a narrative request.
        Action: manage_assessments. Id prefix: ``nao-``.

        The outcome label is stored verbatim as reported; no text
        accompanies it and none is generated here."""
        self._guard(actor, "manage_assessments", "ext_narrative_outcome_create", request_id)
        _validate_non_empty(reported_outcome, "narrative reported outcome")
        note = _validate_text(note, "narrative outcome note")
        with self._lock:
            self._get(self._narrative_requests, request_id, "narrative request")
            outcome_id = self._next_id("nao")
            outcome = {
                "id": outcome_id,
                "request_id": request_id,
                "reported_outcome": reported_outcome,
                "note": note,
                "generated_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._narrative_outcomes[outcome_id] = outcome
            self._audit(
                actor, "ext_narrative_outcome_create", outcome_id,
                details={"request_id": request_id},
            )
            return dict(outcome)

    def get_narrative_request(self, request_id, actor):
        """Return one narrative request with its outcome records.
        Action: read."""
        require(actor, "read")
        with self._lock:
            request = self._get(
                self._narrative_requests, request_id, "narrative request"
            )
            view = self._copy(request, ("control_ids",))
            view["outcomes"] = [
                dict(outcome)
                for outcome in self._narrative_outcomes.values()
                if outcome["request_id"] == request_id
            ]
            return view

    def list_narrative_requests(self, actor, system_ref=None):
        """Return narrative request records, optionally filtered by
        system, in id order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [
                self._copy(request, ("control_ids",))
                for request in self._narrative_requests.values()
                if system_ref is None or request["system_ref"] == system_ref
            ]

    # -- data-integration connector engine (reference) -----------------------

    def create_connector(
        self, connector_ref, name, actor, target_label="", description="",
    ):
        """Register a connector reference. Action: manage_indicators.

        Labeled reference implementation: the record carries
        ``reference_stub: True`` and ``reference_transport: True``;
        nothing is connected to."""
        self._guard(actor, "manage_indicators", "ext_connector_create", connector_ref)
        _validate_non_empty(connector_ref, "connector reference")
        _validate_non_empty(name, "connector name")
        target_label = _validate_text(target_label, "connector target label")
        description = _validate_text(description, "connector description")
        with self._lock:
            if connector_ref in self._connectors:
                raise ValidationError(
                    "connector reference already registered: %r" % (connector_ref,)
                )
            connector = {
                "ref": connector_ref,
                "name": name,
                "target_label": target_label,
                "description": description,
                "reference_stub": True,
                "reference_transport": True,
                "connected_here": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._connectors[connector_ref] = connector
            self._audit(
                actor, "ext_connector_create", connector_ref,
                details={"name": name},
            )
            return dict(connector)

    def record_connector_run(self, connector_ref, actor, records_reported=0, note=""):
        """Record a connector run. Action: record_results. Id
        prefix: ``cnr-``.

        ``records_reported`` is a count as reported by the external
        connector; the records themselves never move through this
        substrate (``moved_here: False``)."""
        self._guard(actor, "record_results", "ext_connector_run_create", connector_ref)
        records_reported = _validate_count(records_reported, "records_reported")
        note = _validate_text(note, "connector run note")
        with self._lock:
            self._get(self._connectors, connector_ref, "connector")
            run_id = self._next_id("cnr")
            run = {
                "id": run_id,
                "connector_ref": connector_ref,
                "records_reported": records_reported,
                "note": note,
                "moved_here": False,
                "reference_transport": True,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._connector_runs[run_id] = run
            self._audit(
                actor, "ext_connector_run_create", run_id,
                details={"connector_ref": connector_ref},
            )
            return dict(run)

    def _connector_view(self, connector):
        view = dict(connector)
        runs = [
            dict(run)
            for run in self._connector_runs.values()
            if run["connector_ref"] == connector["ref"]
        ]
        view["runs"] = runs
        view["run_count"] = len(runs)
        view["records_reported_total"] = sum(
            run["records_reported"] for run in runs
        )
        return view

    def get_connector(self, connector_ref, actor):
        """Return one connector record with its runs and derived
        totals. Action: read."""
        require(actor, "read")
        with self._lock:
            return self._connector_view(
                self._get(self._connectors, connector_ref, "connector")
            )

    def list_connectors(self, actor):
        """Return connector views in registration order. Action:
        read."""
        require(actor, "read")
        with self._lock:
            return [
                self._connector_view(connector)
                for connector in self._connectors.values()
            ]

    def list_connector_runs(self, actor, connector_ref=None):
        """Return connector run records, optionally filtered, in id
        order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [
                dict(run)
                for run in self._connector_runs.values()
                if connector_ref is None or run["connector_ref"] == connector_ref
            ]

    # -- fork excess (reference) ----------------------------------------------

    def create_excess_profile(
        self, kind, name, actor, system_ref=None, description="",
    ):
        """Register a reference profile for one fork-excess kind.
        Action: manage_systems. Id prefix: ``exc-``.

        The four kinds are product surface outside the category's
        records substrate (healthcare quality suite; AI/ML
        governance evaluation engine; digital-twin OSCAL analysis
        engine; no-code BPM platform). Labeled reference
        implementation: ``reference_stub: True``,
        ``executed_here: False`` — the profile records that the
        surface exists in a fork's product; nothing of it runs or is
        computed here."""
        self._guard(actor, "manage_systems", "ext_excess_profile_create", kind)
        if kind not in EXCESS_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(EXCESS_KINDS),)
            )
        _validate_non_empty(name, "excess profile name")
        description = _validate_text(description, "excess profile description")
        with self._lock:
            if system_ref is not None:
                self.store.get_system(system_ref, actor)
            profile_id = self._next_id("exc")
            profile = {
                "id": profile_id,
                "kind": kind,
                "name": name,
                "system_ref": system_ref,
                "description": description,
                "reference_stub": True,
                "executed_here": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._excess_profiles[profile_id] = profile
            self._audit(
                actor, "ext_excess_profile_create", profile_id,
                details={"kind": kind},
            )
            return dict(profile)

    def record_excess_outcome(self, profile_id, outcome_label, actor, note=""):
        """Record an outcome label for an excess profile exactly as
        reported. Action: manage_systems. Id prefix: ``exo-``.
        Nothing is computed from the label (``computed_here:
        False``)."""
        self._guard(actor, "manage_systems", "ext_excess_outcome_create", profile_id)
        _validate_non_empty(outcome_label, "excess outcome label")
        note = _validate_text(note, "excess outcome note")
        with self._lock:
            self._get(self._excess_profiles, profile_id, "excess profile")
            outcome_id = self._next_id("exo")
            outcome = {
                "id": outcome_id,
                "profile_id": profile_id,
                "outcome_label": outcome_label,
                "note": note,
                "computed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._excess_outcomes[outcome_id] = outcome
            self._audit(
                actor, "ext_excess_outcome_create", outcome_id,
                details={"profile_id": profile_id},
            )
            return dict(outcome)

    def get_excess_profile(self, profile_id, actor):
        """Return one excess profile with its outcome records.
        Action: read."""
        require(actor, "read")
        with self._lock:
            profile = self._get(
                self._excess_profiles, profile_id, "excess profile"
            )
            view = dict(profile)
            view["outcomes"] = [
                dict(outcome)
                for outcome in self._excess_outcomes.values()
                if outcome["profile_id"] == profile_id
            ]
            return view

    def list_excess_profiles(self, actor, kind=None):
        """Return excess profile records, optionally filtered by
        kind, in id order. Action: read."""
        require(actor, "read")
        with self._lock:
            return [
                dict(profile)
                for profile in self._excess_profiles.values()
                if kind is None or profile["kind"] == kind
            ]

    def excess_summary(self, actor):
        """Counts of excess profiles by kind, derived at read.
        Counts only. Action: read."""
        require(actor, "read")
        with self._lock:
            by_kind = {}
            for profile in self._excess_profiles.values():
                kind = profile["kind"]
                by_kind[kind] = by_kind.get(kind, 0) + 1
            return {
                "total": len(self._excess_profiles),
                "by_kind": by_kind,
                "method": "deterministic_counts",
            }
