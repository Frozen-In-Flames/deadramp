"""Final-GAPS-batch extension surface for the GRC L2 core.

One new module, following the batch pattern in
``../../gaps-batch/DECISION.md``: :class:`GrcExtensions` wraps a
core :class:`grc.store.GrcStore` and adds records for the seven
Extended functions registered under this group's GAPS.md section.
The core modules are untouched.

The category doctrine binds every surface here, exactly as it
binds the core (see ``../UNION-SPEC.md`` and the core posture
tests): **posture is counts only — no computed score, rating,
grade, or percentage exists anywhere**, enforced over this
surface by the same recursive key scan the founding suite pins
(no key may contain ``score`` / ``rating`` / ``grade`` /
``percent`` — which is also why the boundary on the
reported-value records below is spelled ``computed_here``).
Statuses a person or an external engine reports are recorded
**verbatim**, never computed. Anything date-based is **derived
at read, never stored**.

What each engine-shaped entry becomes here (per-entry record in
``../BATCH.md``):

- **Evidence-validation engine / API & telemetry collection**
  (idx 353) — collection-source records (definitions of external
  sources, ``reference_transport: True``, ``collected_here:
  False``), validation-job records (``reference_stub: True``,
  ``validated_here: False``), and validation-report records
  holding the engine's reported status verbatim. A report never
  changes the core evidence record: its recorded validation
  status is set only by a reviewer's core review operation.
- **Monitoring feeds & scanner integrations** (idx 354) —
  feed-definition records (``reference_stub: True``,
  ``reference_transport: True``, ``connected_here: False``,
  ``ingested_here: False``) and feed-receipt records holding
  what a feed reported. A receipt creates no core indicator
  result and no core finding.
- **Vulnerability scanning engine** (idx 355) — scan-job records
  (``scanned_here: False``), scan-report records holding the
  scanner's reported outcome and reported finding count, and
  priority records holding a scanner-reported priority label
  verbatim against a core finding (``prioritized_here: False``,
  ``computed_here: False``). The build scans nothing and
  computes no priority; a scan report creates no core finding.
- **Automated KSI validation** (idx 356) — validation-run
  records (``reference_stub: True``, ``validated_here: False``,
  ``evaluated_here: False``) and run-report records holding the
  engine's reported status verbatim. A report creates **no**
  core indicator result: core results are recorded through the
  core's own operation, by a person.
- **Posture / risk scoring engines** (idx 357) — reported-value
  records: values an external scoring engine or assessor
  reported, stored verbatim as labels with their reported
  scale, carrying ``computed_here: False``. Nothing here
  computes a value from records; aggregates over this surface
  are counts of the recorded labels only, and the core posture
  summary is untouched.
- **Hosted enclave & PaaS operations** (idx 358) —
  environment records over core governed systems
  (``reference_stub: True``, ``hosted_here: False``,
  ``operated_here: False``) and operation records holding
  reported outcomes verbatim. Nothing is hosted or operated
  here; hosting is the deployment layer (PLATFORM-LAYER.md
  decision 6).
- **FedRAMP authorization package generation** (idx 359) —
  package records that store **no figures at all** (a request
  for a package against a system and framework, with
  ``submitted_here: False`` and ``exported_here: False``), plus
  a package view derived at read from the core's records —
  component references and counts only — so the manifest always
  tracks registry state. No document is generated, exported,
  or submitted.

Permissions ride the core's matrix unchanged (the same actions
the core enforces for the analogous records); reads require
``read``. Denied attempts raise :class:`PermissionDenied` and
change nothing — at this store-level surface, auditing a denial
is the HTTP layer's responsibility, exactly as in the core.
Successful extension mutations are written to the core's
append-only audit log (when one is attached) under ``ext_``
action names. Every operation validates fully before it
mutates: a failed operation consumes no id and changes nothing.
"""

import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, ValidationError
from .store import derive_finding_status

COLLECTION_KINDS = ("api", "telemetry")
FEED_KINDS = ("monitoring_feed", "scanner_integration")


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


class GrcExtensions:
    """The final-GAPS-batch extension surface over a core store."""

    def __init__(self, store):
        self.store = store
        self.audit = store.audit
        self._collection_sources = {}  # id -> collection source record
        self._validation_jobs = {}  # id -> evidence validation job record
        self._validation_reports = {}  # id -> validation report record
        self._feeds = {}  # id -> feed definition record
        self._feed_receipts = {}  # id -> feed receipt record
        self._scan_jobs = {}  # id -> scan job record
        self._scan_reports = {}  # id -> scan report record
        self._finding_priorities = {}  # id -> reported priority record
        self._ksi_runs = {}  # id -> KSI validation run record
        self._ksi_reports = {}  # id -> KSI run report record
        self._reported_values = {}  # id -> reported value record
        self._environments = {}  # id -> enclave environment record
        self._operations = {}  # id -> enclave operation record
        self._packages = {}  # id -> authorization package record
        self._counters = {
            "col": 0, "vjob": 0, "vrep": 0, "feed": 0, "rcpt": 0,
            "scan": 0, "srep": 0, "prio": 0, "krun": 0, "krep": 0,
            "rval": 0, "env": 0, "op": 0, "pkg": 0,
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

    def _require_framework(self, framework_id, actor):
        self.store.get_framework(framework_id, actor)

    def _require_indicator(self, indicator_id, actor):
        self.store.get_indicator(indicator_id, actor)

    def _require_evidence(self, evidence_id, actor):
        self.store.get_evidence(evidence_id, actor)

    def _require_finding(self, finding_id, actor):
        self.store.get_finding(finding_id, actor)

    @staticmethod
    def _get(table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    # -- collection sources & evidence validation (idx 353) ----------

    def register_collection_source(self, kind, system_ref, label, actor, note=""):
        """Register a definition of an external evidence-collection
        source (an API or telemetry source an external engine
        collects through). This build collects nothing: the record
        carries ``reference_transport: True`` and
        ``collected_here: False``. Action: manage_evidence.
        Id prefix: col-."""
        if kind not in COLLECTION_KINDS:
            raise ValidationError(
                "collection kind must be one of %s" % (", ".join(COLLECTION_KINDS),)
            )
        _validate_non_empty(system_ref, "system reference")
        _validate_non_empty(label, "source label")
        note = _validate_text(note, "source note")
        self._require(actor, "manage_evidence")
        with self._lock:
            self._require_system(system_ref, actor)
            source_id = self._next_id("col")
            record = {
                "id": source_id,
                "kind": kind,
                "system_ref": system_ref,
                "label": label,
                "note": note,
                "reference_transport": True,
                "collected_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._collection_sources[source_id] = record
            self._audit(actor, "ext_collection_source_create", source_id,
                        details={"kind": kind, "system_ref": system_ref})
            return dict(record)

    def get_collection_source(self, source_id, actor):
        """Return one collection-source record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._collection_sources, source_id,
                                  "collection source"))

    def list_collection_sources(self, actor, system_ref=None):
        """Return collection-source records, optionally filtered by
        system, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._collection_sources.values()
                if system_ref is None or record["system_ref"] == system_ref
            ]

    def create_validation_job(self, evidence_id, engine_label, actor):
        """Register a validation job an external evidence-validation
        engine is reported to run against a core evidence record.
        This build validates nothing: the record carries
        ``reference_stub: True`` and ``validated_here: False``.
        Action: manage_evidence. Id prefix: vjob-."""
        _validate_non_empty(evidence_id, "evidence id")
        _validate_non_empty(engine_label, "engine label")
        self._require(actor, "manage_evidence")
        with self._lock:
            self._require_evidence(evidence_id, actor)
            job_id = self._next_id("vjob")
            record = {
                "id": job_id,
                "evidence_id": evidence_id,
                "engine_label": engine_label,
                "reference_stub": True,
                "validated_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._validation_jobs[job_id] = record
            self._audit(actor, "ext_validation_job_create", job_id,
                        details={"evidence_id": evidence_id})
            return dict(record)

    def get_validation_job(self, job_id, actor):
        """Return one validation-job record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._validation_jobs, job_id, "validation job"))

    def list_validation_jobs(self, actor, evidence_id=None):
        """Return validation-job records, optionally filtered by
        evidence, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._validation_jobs.values()
                if evidence_id is None or record["evidence_id"] == evidence_id
            ]

    def record_validation_report(self, job_id, reported_status, actor,
                                 reported_utc=None, note=""):
        """Record the outcome an external validation engine reported
        for a validation job. ``reported_status`` is stored
        **verbatim**. Recording a report changes nothing in the
        core: in particular it never sets the core evidence
        record's validation status, which only a reviewer's core
        review operation sets. Action: record_results.
        Id prefix: vrep-."""
        _validate_non_empty(reported_status, "reported status")
        note = _validate_text(note, "report note")
        if reported_utc is not None:
            reported_utc = _validate_timestamp(reported_utc, "reported timestamp")
        self._require(actor, "record_results")
        with self._lock:
            job = self._get(self._validation_jobs, job_id, "validation job")
            report_id = self._next_id("vrep")
            record = {
                "id": report_id,
                "job_id": job_id,
                "evidence_id": job["evidence_id"],
                "reported_status": reported_status,
                "reported_utc": reported_utc if reported_utc is not None else _utc_now(),
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._validation_reports[report_id] = record
            self._audit(actor, "ext_validation_report_record", report_id,
                        details={"job_id": job_id,
                                 "evidence_id": job["evidence_id"]})
            return dict(record)

    def list_validation_reports(self, actor, job_id=None, evidence_id=None):
        """Return validation-report records, optionally filtered by
        job and/or evidence, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._validation_reports.values()
                if (job_id is None or record["job_id"] == job_id)
                and (evidence_id is None or record["evidence_id"] == evidence_id)
            ]

    # -- monitoring feeds & scanner integrations (idx 354) -----------

    def register_feed(self, kind, system_ref, label, actor, note=""):
        """Register a definition of a continuous-monitoring feed or
        scanner integration. This build connects to nothing and
        ingests nothing: the record carries ``reference_stub:
        True``, ``reference_transport: True``, ``connected_here:
        False``, ``ingested_here: False``. Action:
        manage_indicators. Id prefix: feed-."""
        if kind not in FEED_KINDS:
            raise ValidationError(
                "feed kind must be one of %s" % (", ".join(FEED_KINDS),)
            )
        _validate_non_empty(system_ref, "system reference")
        _validate_non_empty(label, "feed label")
        note = _validate_text(note, "feed note")
        self._require(actor, "manage_indicators")
        with self._lock:
            self._require_system(system_ref, actor)
            feed_id = self._next_id("feed")
            record = {
                "id": feed_id,
                "kind": kind,
                "system_ref": system_ref,
                "label": label,
                "note": note,
                "reference_stub": True,
                "reference_transport": True,
                "connected_here": False,
                "ingested_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._feeds[feed_id] = record
            self._audit(actor, "ext_feed_create", feed_id,
                        details={"kind": kind, "system_ref": system_ref})
            return dict(record)

    def get_feed(self, feed_id, actor):
        """Return one feed-definition record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._feeds, feed_id, "feed"))

    def list_feeds(self, actor, system_ref=None):
        """Return feed-definition records, optionally filtered by
        system, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._feeds.values()
                if system_ref is None or record["system_ref"] == system_ref
            ]

    def record_feed_receipt(self, feed_id, reported_status, reported_count,
                            actor, reported_utc=None, note=""):
        """Record what a feed or scanner integration reported: a
        status stored **verbatim** and a count **as reported**.
        A receipt is a record about the feed; it creates no core
        indicator result and no core finding. Action:
        record_results. Id prefix: rcpt-."""
        _validate_non_empty(reported_status, "reported status")
        reported_count = _validate_reported_count(reported_count, "reported count")
        note = _validate_text(note, "receipt note")
        if reported_utc is not None:
            reported_utc = _validate_timestamp(reported_utc, "reported timestamp")
        self._require(actor, "record_results")
        with self._lock:
            self._get(self._feeds, feed_id, "feed")
            receipt_id = self._next_id("rcpt")
            record = {
                "id": receipt_id,
                "feed_id": feed_id,
                "reported_status": reported_status,
                "reported_count": reported_count,
                "reported_utc": reported_utc if reported_utc is not None else _utc_now(),
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._feed_receipts[receipt_id] = record
            self._audit(actor, "ext_feed_receipt_record", receipt_id,
                        details={"feed_id": feed_id})
            return dict(record)

    def list_feed_receipts(self, actor, feed_id=None):
        """Return feed-receipt records, optionally filtered by feed,
        in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._feed_receipts.values()
                if feed_id is None or record["feed_id"] == feed_id
            ]

    # -- vulnerability scanning records (idx 355) --------------------

    def create_scan_job(self, system_ref, scanner_label, actor, scope_label=""):
        """Register a scan job an external vulnerability scanner is
        reported to run against a governed system. This build
        scans nothing: the record carries ``scanned_here:
        False``. Action: manage_findings. Id prefix: scan-."""
        _validate_non_empty(system_ref, "system reference")
        _validate_non_empty(scanner_label, "scanner label")
        scope_label = _validate_text(scope_label, "scope label")
        self._require(actor, "manage_findings")
        with self._lock:
            self._require_system(system_ref, actor)
            scan_id = self._next_id("scan")
            record = {
                "id": scan_id,
                "system_ref": system_ref,
                "scanner_label": scanner_label,
                "scope_label": scope_label,
                "scanned_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._scan_jobs[scan_id] = record
            self._audit(actor, "ext_scan_job_create", scan_id,
                        details={"system_ref": system_ref})
            return dict(record)

    def get_scan_job(self, scan_id, actor):
        """Return one scan-job record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._scan_jobs, scan_id, "scan job"))

    def list_scan_jobs(self, actor, system_ref=None):
        """Return scan-job records, optionally filtered by system,
        in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._scan_jobs.values()
                if system_ref is None or record["system_ref"] == system_ref
            ]

    def record_scan_report(self, scan_id, reported_outcome, findings_reported,
                           actor, reported_utc=None, note=""):
        """Record the outcome a scanner reported for a scan job:
        the outcome label **verbatim** and the finding count **as
        reported**. A scan report creates no core finding — core
        findings are created through the core's own operation.
        Action: manage_findings. Id prefix: srep-."""
        _validate_non_empty(reported_outcome, "reported outcome")
        findings_reported = _validate_reported_count(
            findings_reported, "findings reported")
        note = _validate_text(note, "report note")
        if reported_utc is not None:
            reported_utc = _validate_timestamp(reported_utc, "reported timestamp")
        self._require(actor, "manage_findings")
        with self._lock:
            job = self._get(self._scan_jobs, scan_id, "scan job")
            report_id = self._next_id("srep")
            record = {
                "id": report_id,
                "scan_id": scan_id,
                "system_ref": job["system_ref"],
                "reported_outcome": reported_outcome,
                "findings_reported": findings_reported,
                "reported_utc": reported_utc if reported_utc is not None else _utc_now(),
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._scan_reports[report_id] = record
            self._audit(actor, "ext_scan_report_record", report_id,
                        details={"scan_id": scan_id})
            return dict(record)

    def list_scan_reports(self, actor, scan_id=None):
        """Return scan-report records, optionally filtered by scan
        job, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._scan_reports.values()
                if scan_id is None or record["scan_id"] == scan_id
            ]

    def record_finding_priority(self, finding_id, reported_priority, actor,
                                reporter="", note=""):
        """Record a priority label a scanner or assessor reported
        for a core finding. The label is stored **verbatim**;
        this build prioritizes nothing and computes nothing from
        the label — the record carries ``prioritized_here:
        False`` and ``computed_here: False``. Recording a
        priority never changes the core finding. Action:
        manage_findings. Id prefix: prio-."""
        _validate_non_empty(finding_id, "finding id")
        _validate_non_empty(reported_priority, "reported priority")
        reporter = _validate_text(reporter, "reporter")
        note = _validate_text(note, "priority note")
        self._require(actor, "manage_findings")
        with self._lock:
            self._require_finding(finding_id, actor)
            priority_id = self._next_id("prio")
            record = {
                "id": priority_id,
                "finding_id": finding_id,
                "reported_priority": reported_priority,
                "reporter": reporter,
                "note": note,
                "prioritized_here": False,
                "computed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._finding_priorities[priority_id] = record
            self._audit(actor, "ext_finding_priority_record", priority_id,
                        details={"finding_id": finding_id})
            return dict(record)

    def list_finding_priorities(self, actor, finding_id=None):
        """Return reported-priority records, optionally filtered by
        finding, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._finding_priorities.values()
                if finding_id is None or record["finding_id"] == finding_id
            ]

    # -- automated KSI validation records (idx 356) ------------------

    def create_ksi_run(self, indicator_id, system_ref, engine_label, actor):
        """Register a validation run an external engine is reported
        to perform for a core indicator on a governed system.
        This build evaluates nothing: the record carries
        ``reference_stub: True``, ``validated_here: False``, and
        ``evaluated_here: False``. Action: manage_indicators.
        Id prefix: krun-."""
        _validate_non_empty(indicator_id, "indicator id")
        _validate_non_empty(system_ref, "system reference")
        _validate_non_empty(engine_label, "engine label")
        self._require(actor, "manage_indicators")
        with self._lock:
            self._require_indicator(indicator_id, actor)
            self._require_system(system_ref, actor)
            run_id = self._next_id("krun")
            record = {
                "id": run_id,
                "indicator_id": indicator_id,
                "system_ref": system_ref,
                "engine_label": engine_label,
                "reference_stub": True,
                "validated_here": False,
                "evaluated_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._ksi_runs[run_id] = record
            self._audit(actor, "ext_ksi_run_create", run_id,
                        details={"indicator_id": indicator_id,
                                 "system_ref": system_ref})
            return dict(record)

    def get_ksi_run(self, run_id, actor):
        """Return one KSI validation-run record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._ksi_runs, run_id, "KSI validation run"))

    def list_ksi_runs(self, actor, indicator_id=None, system_ref=None):
        """Return KSI validation-run records, optionally filtered,
        in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._ksi_runs.values()
                if (indicator_id is None or record["indicator_id"] == indicator_id)
                and (system_ref is None or record["system_ref"] == system_ref)
            ]

    def record_ksi_report(self, run_id, reported_status, actor,
                          reported_utc=None, note=""):
        """Record the status an external engine reported for a KSI
        validation run, stored **verbatim**. A run report creates
        **no** core indicator result: core results are recorded
        through the core's own operation, by a person. Action:
        record_results. Id prefix: krep-."""
        _validate_non_empty(reported_status, "reported status")
        note = _validate_text(note, "report note")
        if reported_utc is not None:
            reported_utc = _validate_timestamp(reported_utc, "reported timestamp")
        self._require(actor, "record_results")
        with self._lock:
            run = self._get(self._ksi_runs, run_id, "KSI validation run")
            report_id = self._next_id("krep")
            record = {
                "id": report_id,
                "run_id": run_id,
                "indicator_id": run["indicator_id"],
                "system_ref": run["system_ref"],
                "reported_status": reported_status,
                "reported_utc": reported_utc if reported_utc is not None else _utc_now(),
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._ksi_reports[report_id] = record
            self._audit(actor, "ext_ksi_report_record", report_id,
                        details={"run_id": run_id})
            return dict(record)

    def list_ksi_reports(self, actor, run_id=None):
        """Return KSI run-report records, optionally filtered by
        run, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._ksi_reports.values()
                if run_id is None or record["run_id"] == run_id
            ]

    # -- reported values from external scoring engines (idx 357) -----

    def record_reported_value(self, system_ref, reporter, value_label, actor,
                              scale_label="", framework_id=None,
                              reported_utc=None, note=""):
        """Record a value an external scoring engine or assessor
        reported for a governed system. ``value_label`` and
        ``scale_label`` are stored **verbatim**, exactly as the
        reporter supplied them; this build computes no value from
        any record — the record carries ``computed_here:
        False``. Recording a reported value changes nothing in
        the core, and the core posture summary neither reads nor
        reflects these records: posture stays counts of core
        records only. Action: record_results. Id prefix: rval-."""
        _validate_non_empty(system_ref, "system reference")
        _validate_non_empty(reporter, "reporter")
        _validate_non_empty(value_label, "reported value label")
        scale_label = _validate_text(scale_label, "scale label")
        note = _validate_text(note, "value note")
        if reported_utc is not None:
            reported_utc = _validate_timestamp(reported_utc, "reported timestamp")
        self._require(actor, "record_results")
        with self._lock:
            self._require_system(system_ref, actor)
            if framework_id is not None:
                self._require_framework(framework_id, actor)
            value_id = self._next_id("rval")
            record = {
                "id": value_id,
                "system_ref": system_ref,
                "framework_id": framework_id,
                "reporter": reporter,
                "value_label": value_label,
                "scale_label": scale_label,
                "reported_utc": reported_utc if reported_utc is not None else _utc_now(),
                "note": note,
                "computed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._reported_values[value_id] = record
            self._audit(actor, "ext_reported_value_record", value_id,
                        details={"system_ref": system_ref, "reporter": reporter})
            return dict(record)

    def get_reported_value(self, value_id, actor):
        """Return one reported-value record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._reported_values, value_id,
                                  "reported value"))

    def list_reported_values(self, actor, system_ref=None, reporter=None):
        """Return reported-value records, optionally filtered, in
        recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._reported_values.values()
                if (system_ref is None or record["system_ref"] == system_ref)
                and (reporter is None or record["reporter"] == reporter)
            ]

    # -- hosted enclave & PaaS operations records (idx 358) ----------

    def register_environment(self, system_ref, environment_label, actor, note=""):
        """Register an enclave/hosting environment record over a
        core governed system. This build hosts nothing and
        operates nothing: the record carries ``reference_stub:
        True``, ``hosted_here: False``, and ``operated_here:
        False``. Action: manage_systems. Id prefix: env-."""
        _validate_non_empty(system_ref, "system reference")
        _validate_non_empty(environment_label, "environment label")
        note = _validate_text(note, "environment note")
        self._require(actor, "manage_systems")
        with self._lock:
            self._require_system(system_ref, actor)
            environment_id = self._next_id("env")
            record = {
                "id": environment_id,
                "system_ref": system_ref,
                "environment_label": environment_label,
                "note": note,
                "reference_stub": True,
                "hosted_here": False,
                "operated_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._environments[environment_id] = record
            self._audit(actor, "ext_environment_create", environment_id,
                        details={"system_ref": system_ref})
            return dict(record)

    def get_environment(self, environment_id, actor):
        """Return one environment record. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._environments, environment_id,
                                  "environment"))

    def list_environments(self, actor, system_ref=None):
        """Return environment records, optionally filtered by
        system, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._environments.values()
                if system_ref is None or record["system_ref"] == system_ref
            ]

    def record_operation(self, environment_id, operation_kind, reported_outcome,
                         actor, reported_utc=None, note=""):
        """Record an enclave operation and its reported outcome,
        both stored **verbatim** as labels. The operation is not
        performed here; the record is the account of what the
        platform's operators reported. Action: manage_systems.
        Id prefix: op-."""
        _validate_non_empty(operation_kind, "operation kind")
        _validate_non_empty(reported_outcome, "reported outcome")
        note = _validate_text(note, "operation note")
        if reported_utc is not None:
            reported_utc = _validate_timestamp(reported_utc, "reported timestamp")
        self._require(actor, "manage_systems")
        with self._lock:
            environment = self._get(self._environments, environment_id,
                                    "environment")
            operation_id = self._next_id("op")
            record = {
                "id": operation_id,
                "environment_id": environment_id,
                "system_ref": environment["system_ref"],
                "operation_kind": operation_kind,
                "reported_outcome": reported_outcome,
                "reported_utc": reported_utc if reported_utc is not None else _utc_now(),
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._operations[operation_id] = record
            self._audit(actor, "ext_operation_record", operation_id,
                        details={"environment_id": environment_id})
            return dict(record)

    def list_operations(self, actor, environment_id=None):
        """Return operation records, optionally filtered by
        environment, in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._operations.values()
                if environment_id is None
                or record["environment_id"] == environment_id
            ]

    # -- authorization package records & derived view (idx 359) ------

    def create_package(self, system_ref, framework_id, actor, note=""):
        """Register an authorization-package record: a request that
        a package be assembled for a governed system under a
        framework. The record stores **no figures** — the manifest
        is derived at read by :meth:`package_view`, so it always
        tracks the registry. No document is generated, exported,
        or submitted: the record carries ``submitted_here:
        False`` and ``exported_here: False``. Action:
        manage_assessments. Id prefix: pkg-."""
        _validate_non_empty(system_ref, "system reference")
        _validate_non_empty(framework_id, "framework id")
        note = _validate_text(note, "package note")
        self._require(actor, "manage_assessments")
        with self._lock:
            self._require_system(system_ref, actor)
            self._require_framework(framework_id, actor)
            package_id = self._next_id("pkg")
            record = {
                "id": package_id,
                "system_ref": system_ref,
                "framework_id": framework_id,
                "note": note,
                "submitted_here": False,
                "exported_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._packages[package_id] = record
            self._audit(actor, "ext_package_create", package_id,
                        details={"system_ref": system_ref,
                                 "framework_id": framework_id})
            return dict(record)

    def get_package(self, package_id, actor):
        """Return one package record (which stores no figures).
        Action: read."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._packages, package_id, "package"))

    def list_packages(self, actor, system_ref=None):
        """Return package records, optionally filtered by system,
        in recording order. Action: read."""
        self._require(actor, "read")
        with self._lock:
            return [
                dict(record)
                for record in self._packages.values()
                if system_ref is None or record["system_ref"] == system_ref
            ]

    def _package_overdue_count(self, findings, as_of_date):
        """Count past-due open findings for a package view.

        The single derivation point for the package manifest's
        overdue figure: it applies the core's read-time derivation
        (:func:`grc.store.derive_finding_status`) to each stored
        finding record. The batch's fresh negative control
        targets this seam (see tests/README.md).
        """
        count = 0
        for finding in findings:
            if derive_finding_status(finding, as_of_date) == "overdue":
                count += 1
        return count

    def package_view(self, package_id, actor, as_of=None):
        """Derive a package manifest at read from the core's
        records: component references and **counts only** — the
        authorizations and assessments a package would assemble,
        the framework's control count, and evidence / finding /
        indicator-result counts for the package's system. The
        view is computed on every call and never stored, so it
        tracks registry state exactly. Action: read."""
        self._require(actor, "read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            package = self._get(self._packages, package_id, "package")
            system_ref = package["system_ref"]
            framework_id = package["framework_id"]

            authorizations = [
                {"id": record["id"], "status": record["status"]}
                for record in self.store.list_authorizations(
                    actor, system_ref=system_ref)
                if record["framework_id"] == framework_id
            ]
            assessments = [
                record["id"]
                for record in self.store.list_assessments(
                    actor, system_ref=system_ref, framework_id=framework_id)
            ]
            controls_total = len(
                self.store.list_controls(actor, framework_id=framework_id))

            evidence = self.store.list_evidence(actor, system_ref=system_ref)
            evidence_by_status = {}
            for item in evidence:
                status = item["validation_status"]
                evidence_by_status[status] = evidence_by_status.get(status, 0) + 1

            findings = self.store.list_findings(actor, system_ref=system_ref)
            findings_by_status = {}
            for finding in findings:
                status = finding["status"]
                findings_by_status[status] = findings_by_status.get(status, 0) + 1

            results = self.store.list_indicator_results(
                actor, system_ref=system_ref)
            results_by_status = {}
            for result in results:
                status = result["status"]
                results_by_status[status] = results_by_status.get(status, 0) + 1

            return {
                "package_id": package_id,
                "system_ref": system_ref,
                "framework_id": framework_id,
                "as_of": as_of_date.isoformat(),
                "authorizations": authorizations,
                "assessments": assessments,
                "controls_total": controls_total,
                "evidence": {
                    "total": len(evidence),
                    "by_validation_status": evidence_by_status,
                },
                "findings": {
                    "total": len(findings),
                    "by_status": findings_by_status,
                    "overdue": self._package_overdue_count(findings, as_of_date),
                },
                "indicator_results": {
                    "total": len(results),
                    "by_status": results_by_status,
                },
                "submitted_here": False,
                "exported_here": False,
            }

    # -- extension summary (counts only) ------------------------------

    def extension_summary(self, actor):
        """Return counts over the extension surface, computed on
        read: totals and counts by recorded label for each record
        kind. Counts and sums of caller-reported counts only —
        no computed value of any kind. Writes no audit entry.
        Action: read."""
        self._require(actor, "read")
        with self._lock:

            def by(records, field):
                counts = {}
                for record in records:
                    key = record[field]
                    counts[key] = counts.get(key, 0) + 1
                return counts

            sources = list(self._collection_sources.values())
            feeds = list(self._feeds.values())
            scan_reports = list(self._scan_reports.values())
            return {
                "collection_sources": {
                    "total": len(sources),
                    "by_kind": by(sources, "kind"),
                },
                "validation_jobs": {"total": len(self._validation_jobs)},
                "validation_reports": {
                    "total": len(self._validation_reports),
                    "by_reported_status": by(
                        self._validation_reports.values(), "reported_status"),
                },
                "feeds": {
                    "total": len(feeds),
                    "by_kind": by(feeds, "kind"),
                },
                "feed_receipts": {"total": len(self._feed_receipts)},
                "scan_jobs": {"total": len(self._scan_jobs)},
                "scan_reports": {
                    "total": len(scan_reports),
                    "findings_reported_total": sum(
                        record["findings_reported"] for record in scan_reports),
                },
                "finding_priorities": {
                    "total": len(self._finding_priorities),
                    "by_reported_priority": by(
                        self._finding_priorities.values(), "reported_priority"),
                },
                "ksi_runs": {"total": len(self._ksi_runs)},
                "ksi_reports": {
                    "total": len(self._ksi_reports),
                    "by_reported_status": by(
                        self._ksi_reports.values(), "reported_status"),
                },
                "reported_values": {
                    "total": len(self._reported_values),
                    "by_value_label": by(
                        self._reported_values.values(), "value_label"),
                    "by_reporter": by(
                        self._reported_values.values(), "reporter"),
                },
                "environments": {"total": len(self._environments)},
                "operations": {
                    "total": len(self._operations),
                    "by_kind": by(self._operations.values(), "operation_kind"),
                },
                "packages": {"total": len(self._packages)},
            }
