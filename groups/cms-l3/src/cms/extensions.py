"""Final GAPS batch extensions — Singleton 39 (CMS L3-adjacent).

Records-form implementations and labeled reference implementations
for the five open Extended entries of this group's union spec,
built over the founding CMS substrate in :mod:`cms.store`. This
module is the only code the batch adds; every core module is
unchanged.

This group's fork is an information-governance platform whose own
engines are learned ML/AI over physical and digital content. The
substrate holds registry metadata and checksums only — never
content bodies — and derives no metadata of its own (the
enrichment entry's registered text says so). The dispositions,
per entry (full record in ``BATCH.md``):

- **Learned ML/AI classification, extraction, and enrichment
  engines** (idx 394–396) ship as **labeled reference
  implementations**, re-judged from the drafted build-extension
  triage under DECISION.md qualification 1: the entries name
  learned engines, and a learned engine's substance is inference
  over content this substrate never holds. There is no
  deterministic derivation over this group's own records that
  constitutes classifying, extracting from, or enriching content.
  What is built is the reference surface the batch's
  learned-inference precedent (the AI groups at every tier)
  established: job records (the target named by an opaque
  reference, by a core item/asset reference, and/or by an
  optional SHA-256 digest of the content — never the content)
  plus outcome records holding the external engine's reported
  labels, extracted fields, or metadata **verbatim as reported**
  (``outcome_basis: "engine_reported"``). Every record carries
  ``reference_stub: True`` and its family's not-here flag
  (``classified_here`` / ``extracted_here`` / ``derived_here``
  False). An enrichment outcome is recorded as a report and is
  **not applied** to the core item (``applied_here: False``);
  caller-supplied metadata stays the core's own function.
- **Physical-content intake & digitization pipeline** (idx 397)
  is built in its records form, mirroring the CMS L2 unit's
  built bulk-ingestion form: physical-intake records (a source
  reference, a form label, a page count stored exactly as
  reported — metadata about physical records, never the records
  themselves, ``content_held: False``), pipeline stage events
  recorded verbatim with the current stage **derived at read
  time** by the seam :meth:`CmsExtensions._current_intake_stage`
  and stored nowhere, and digitization outcome records binding
  an intake to the core asset registration that is its digitized
  surrogate (registration stays the core's own function; the
  asset registry holds metadata + checksum, as everywhere in
  this substrate). Scanning, conversion, and OCR are not
  performed here (``scanned_here`` / ``converted_here`` False).
- **The content services platform runtime itself** (idx 398)
  ships as a labeled reference record, as drafted: per
  PLATFORM-LAYER.md decision 6, hosting/delivery of the SaaS
  platform is a deployment property and does not transfer to
  the build (``hosted_here: False``, ``delivered_here: False``,
  ``reference_transport: True``).

High-baseline posture binds the extension, as it binds the core:
extension mutations are written to the core's hash-chained audit
log and are **fail-closed** — the audit entry is recorded
*before* the extension record commits, so an audit write failure
raises :class:`cms.errors.AuditWriteError`, leaves no record,
and consumes no id (AU-5/AU-9). The ``auditor`` role holds
``audit_read`` only, so it is denied every extension read and
write (denials audited) while its core audit duty — reading the
log and verifying the chain — works unchanged (AC-5).

Access control reuses the founding permission matrix — no new
actions exist. The mapping is: classification, extraction, and
enrichment job/outcome writes use ``type_write`` with
``type_read`` reads (registry-level reference records, the CMS
L2 reference-register form); physical intakes, digitization
steps, and digitization outcomes use ``asset_write`` /
``asset_read`` (the physical side of asset registration); the
digitization summary uses ``report_read``; the platform-runtime
reference registers under ``site_write`` (the CMS L2 hosting
form) and reference reads use ``type_read``. Write enforcement
mirrors the core store: a missing actor is denied, a User-like
actor is checked against the matrix, and denials are recorded
in the core audit log as ``<action>:denied``. Reads enforce
only when a User-like actor is supplied, as in the core.

Ids are sequential per object type with fixed prefixes
(``clsjob-``, ``clsout-``, ``extjob-``, ``extout-``,
``enrjob-``, ``enrout-``, ``int-``, ``ref-``). A failed
operation consumes no id and changes nothing: all validation
happens before any mutation, and the audit write precedes the
commit. All timestamps are UTC ISO-8601. Records returned are
copies; mutating a returned record changes nothing stored.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

__all__ = ["CmsExtensions"]

TARGET_KINDS = ("item", "asset", "external")
SOURCE_KINDS = ("asset", "item", "external")

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_text(value, what):
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _validate_count(value, what):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValidationError("%s must be a non-negative int" % (what,))
    return value


def _validate_string_list(value, what):
    if not isinstance(value, (list, tuple)) or not value:
        raise ValidationError("%s must be a non-empty list of strings" % (what,))
    items = list(value)
    for item in items:
        _validate_non_empty(item, what)
    return items


def _validate_digest(value, what):
    if value is None:
        return None
    if not isinstance(value, str) or not _SHA256_RE.match(value):
        raise ValidationError(
            "%s must be a 64-character hex SHA-256" % (what,))
    return value.lower()


def _validate_reported_fields(value, what):
    """Extraction outcome fields: [{field_label, value}] verbatim.

    The pair shape is exact — a reported extraction field is a
    label and the value the external engine reported for it,
    both strings, held as data. Anything else is rejected.
    """
    if not isinstance(value, (list, tuple)) or not value:
        raise ValidationError(
            "%s must be a non-empty list of field objects" % (what,))
    fields = []
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != {"field_label", "value"}:
            raise ValidationError(
                "%s entries must be objects with exactly "
                "'field_label' and 'value'" % (what,))
        _validate_non_empty(entry["field_label"], "field_label")
        _validate_text(entry["value"], "field value")
        fields.append({"field_label": entry["field_label"],
                       "value": entry["value"]})
    return fields


def _validate_metadata_report(value, what):
    """Enrichment outcome metadata: {key: value} strings, verbatim."""
    if not isinstance(value, dict) or not value:
        raise ValidationError(
            "%s must be a non-empty object of string values" % (what,))
    metadata = {}
    for key, val in value.items():
        _validate_non_empty(key, "metadata key")
        _validate_text(val, "metadata value")
        metadata[key] = val
    return metadata


class CmsExtensions:
    """Extension register wrapping a core :class:`cms.store.CmsStore`."""

    def __init__(self, store):
        self.store = store
        self.audit = getattr(store, "audit", None)
        self._classification_jobs = {}
        self._classification_outcomes = {}
        self._extraction_jobs = {}
        self._extraction_outcomes = {}
        self._enrichment_jobs = {}
        self._enrichment_outcomes = {}
        self._intakes = {}
        self._references = {}
        self._counters = {
            "clsjob": 0, "clsout": 0, "extjob": 0, "extout": 0,
            "enrjob": 0, "enrout": 0, "int": 0, "ref": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers -------------------------------------------

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _audit_denied(self, actor, action, target):
        self._audit(actor, "%s:denied" % (action,), target)

    def _require(self, actor, action, audit_action, target=None):
        """Write enforcement, mirroring the core store's `_require`."""
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (action,))
        if hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit_denied(actor, audit_action, target)
                raise

    def _require_read(self, actor, action, audit_action):
        """Read enforcement, mirroring the core store's `_require_read`."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit_denied(actor, audit_action, None)
                raise

    def _get(self, collection, obj_id, what):
        rec = collection.get(obj_id)
        if rec is None:
            raise NotFoundError("%s not found: %r" % (what, obj_id))
        return rec

    def _create(self, collection, prefix, fields, actor, audit_action,
                details=None):
        """Commit a new extension record, fail-closed (AU-5).

        The audit entry is recorded before the record commits:
        if the audit write fails, :class:`AuditWriteError`
        propagates, no record is stored, and no id is consumed —
        the High baseline's fail-closed posture applied to the
        extension surface. Caller must hold ``self._lock`` and
        must have completed all validation.
        """
        record_id = "%s-%d" % (prefix, self._counters[prefix] + 1)
        record = {"id": record_id}
        record.update(fields)
        record["created_by"] = actor_name(actor)
        record["created_utc"] = _utc_now()
        self._audit(actor, audit_action, record_id, details=details)
        self._counters[prefix] += 1
        collection[record_id] = record
        return copy.deepcopy(record)

    def _resolve_core(self, kind, ref):
        """Resolve a core item/asset reference or raise NotFoundError."""
        if kind == "item":
            return self.store.get_item(ref, actor=None)
        return self.store.get_asset(ref, actor=None)

    # -- Learned ML/AI classification engine (reference) -------------
    # Job records name the classification target by reference;
    # outcome records hold the external engine's reported labels
    # verbatim. No model runs here and nothing is classified here.

    def register_classification_job(self, actor, target_ref,
                                    target_kind="external",
                                    taxonomy_ref=None, content_digest=None):
        """Record a classification job for an external ML engine.

        Action: type_write. Ids: clsjob-{n}. The target is named
        by reference only: a core item or asset reference (which
        must resolve), or an opaque external reference. The
        content itself is never held; it may be named by an
        optional SHA-256 digest. ``reference_stub`` is True and
        ``classified_here`` is False on every record.
        """
        self._require(actor, "type_write", "ext_classification_job_register")
        _validate_non_empty(target_ref, "target_ref")
        if target_kind not in TARGET_KINDS:
            raise ValidationError(
                "target_kind must be one of %s" % (", ".join(TARGET_KINDS),))
        if taxonomy_ref is not None:
            _validate_non_empty(taxonomy_ref, "taxonomy_ref")
        content_digest = _validate_digest(content_digest, "content_digest")
        with self._lock:
            if target_kind in ("item", "asset"):
                self._resolve_core(target_kind, target_ref)
            return self._create(
                self._classification_jobs, "clsjob",
                {"target_ref": target_ref, "target_kind": target_kind,
                 "taxonomy_ref": taxonomy_ref,
                 "content_digest": content_digest,
                 "reference_stub": True, "classified_here": False,
                 "state": "recorded_reference_only"},
                actor, "ext_classification_job_register",
                details={"target_kind": target_kind})

    def record_classification_outcome(self, actor, job_id, labels,
                                      confidence_label=None):
        """Record a classification outcome, verbatim as reported.

        Action: type_write. Ids: clsout-{n}. ``labels`` are the
        external engine's reported labels, stored exactly as
        reported; ``confidence_label`` is likewise a verbatim
        reported label (a string — this build records no numeric
        confidence and computes no score). Nothing was classified
        by this build.
        """
        self._require(actor, "type_write", "ext_classification_outcome_record",
                      job_id)
        labels = _validate_string_list(labels, "labels")
        if confidence_label is not None:
            _validate_non_empty(confidence_label, "confidence_label")
        with self._lock:
            self._get(self._classification_jobs, job_id, "classification job")
            return self._create(
                self._classification_outcomes, "clsout",
                {"job_id": job_id, "labels": labels,
                 "confidence_label": confidence_label,
                 "outcome_basis": "engine_reported",
                 "reference_stub": True, "classified_here": False},
                actor, "ext_classification_outcome_record",
                details={"job_id": job_id})

    def _classification_job_view(self, record):
        view = copy.deepcopy(record)
        outcomes = [o for o in self._classification_outcomes.values()
                    if o["job_id"] == record["id"]]
        outcomes.sort(key=lambda o: _id_num(o["id"]))
        view["outcome_count"] = len(outcomes)
        view["latest_labels"] = (
            list(outcomes[-1]["labels"]) if outcomes else [])
        return view

    def get_classification_job(self, job_id, actor=None):
        """Return one classification job with derived outcome data.

        Action: type_read.
        """
        self._require_read(actor, "type_read", "ext_classification_read")
        with self._lock:
            return self._classification_job_view(
                self._get(self._classification_jobs, job_id,
                          "classification job"))

    def list_classification_jobs(self, actor=None):
        """Return classification jobs sorted by id. Action: type_read."""
        self._require_read(actor, "type_read", "ext_classification_read")
        with self._lock:
            records = sorted(self._classification_jobs.values(),
                             key=lambda r: _id_num(r["id"]))
            return [self._classification_job_view(r) for r in records]

    def list_classification_outcomes(self, job_id=None, actor=None):
        """Return classification outcomes, optionally per job.

        Action: type_read.
        """
        self._require_read(actor, "type_read", "ext_classification_read")
        with self._lock:
            records = sorted(self._classification_outcomes.values(),
                             key=lambda r: _id_num(r["id"]))
            if job_id is not None:
                records = [r for r in records if r["job_id"] == job_id]
            return [copy.deepcopy(r) for r in records]

    # -- Learned ML/AI extraction engine (reference) -----------------
    # Job records name the extraction source by reference;
    # outcome records hold the external engine's reported fields
    # verbatim. The substrate holds no content to extract from,
    # and nothing is extracted here.

    def register_extraction_job(self, actor, source_ref,
                                source_kind="external", field_labels=None,
                                content_digest=None):
        """Record an extraction job for an external ML engine.

        Action: type_write. Ids: extjob-{n}. The source is named
        by reference only: a core asset or item reference (which
        must resolve), or an opaque external reference; the
        content may be named by an optional SHA-256 digest and is
        never held. ``field_labels`` optionally records the field
        names the engine was asked to extract, as data.
        ``reference_stub`` is True and ``extracted_here`` is False
        on every record.
        """
        self._require(actor, "type_write", "ext_extraction_job_register")
        _validate_non_empty(source_ref, "source_ref")
        if source_kind not in SOURCE_KINDS:
            raise ValidationError(
                "source_kind must be one of %s" % (", ".join(SOURCE_KINDS),))
        if field_labels is not None:
            field_labels = _validate_string_list(field_labels, "field_labels")
        content_digest = _validate_digest(content_digest, "content_digest")
        with self._lock:
            if source_kind in ("item", "asset"):
                self._resolve_core(source_kind, source_ref)
            return self._create(
                self._extraction_jobs, "extjob",
                {"source_ref": source_ref, "source_kind": source_kind,
                 "field_labels": field_labels,
                 "content_digest": content_digest,
                 "reference_stub": True, "extracted_here": False,
                 "state": "recorded_reference_only"},
                actor, "ext_extraction_job_register",
                details={"source_kind": source_kind})

    def record_extraction_outcome(self, actor, job_id, fields):
        """Record an extraction outcome, verbatim as reported.

        Action: type_write. Ids: extout-{n}. ``fields`` are
        {field_label, value} pairs the external engine reported,
        stored exactly as reported; nothing was extracted by
        this build.
        """
        self._require(actor, "type_write", "ext_extraction_outcome_record",
                      job_id)
        fields = _validate_reported_fields(fields, "fields")
        with self._lock:
            self._get(self._extraction_jobs, job_id, "extraction job")
            return self._create(
                self._extraction_outcomes, "extout",
                {"job_id": job_id, "fields": fields,
                 "outcome_basis": "engine_reported",
                 "reference_stub": True, "extracted_here": False},
                actor, "ext_extraction_outcome_record",
                details={"job_id": job_id})

    def get_extraction_job(self, job_id, actor=None):
        """Return one extraction job record. Action: type_read."""
        self._require_read(actor, "type_read", "ext_extraction_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._extraction_jobs, job_id, "extraction job"))

    def list_extraction_jobs(self, actor=None):
        """Return extraction jobs sorted by id. Action: type_read."""
        self._require_read(actor, "type_read", "ext_extraction_read")
        with self._lock:
            records = sorted(self._extraction_jobs.values(),
                             key=lambda r: _id_num(r["id"]))
            return [copy.deepcopy(r) for r in records]

    def list_extraction_outcomes(self, job_id=None, actor=None):
        """Return extraction outcomes, optionally per job.

        Action: type_read.
        """
        self._require_read(actor, "type_read", "ext_extraction_read")
        with self._lock:
            records = sorted(self._extraction_outcomes.values(),
                             key=lambda r: _id_num(r["id"]))
            if job_id is not None:
                records = [r for r in records if r["job_id"] == job_id]
            return [copy.deepcopy(r) for r in records]

    # -- Learned ML/AI enrichment engine (reference) -----------------
    # Job records bind an enrichment request to a core item;
    # outcome records hold the external engine's reported
    # metadata verbatim. The substrate derives no metadata, and
    # a reported outcome is never applied to the core item.

    def register_enrichment_job(self, actor, item_id):
        """Record an enrichment job against a core content item.

        Action: type_write. Ids: enrjob-{n}. The item must
        resolve in the core registry. ``reference_stub`` is True
        and ``derived_here`` is False on every record: this
        substrate stores caller-supplied metadata only and
        derives none.
        """
        self._require(actor, "type_write", "ext_enrichment_job_register",
                      item_id)
        _validate_non_empty(item_id, "item_id")
        with self._lock:
            self.store.get_item(item_id, actor=None)
            return self._create(
                self._enrichment_jobs, "enrjob",
                {"item_id": item_id,
                 "reference_stub": True, "derived_here": False,
                 "state": "recorded_reference_only"},
                actor, "ext_enrichment_job_register",
                details={"item_id": item_id})

    def record_enrichment_outcome(self, actor, job_id, metadata):
        """Record an enrichment outcome, verbatim as reported.

        Action: type_write. Ids: enrout-{n}. ``metadata`` is the
        external engine's reported key/value metadata, stored
        exactly as reported on this outcome record only. It is
        **not applied** to the core item (``applied_here``
        False): caller-supplied metadata reaches an item only
        through the core's own authoring functions.
        """
        self._require(actor, "type_write", "ext_enrichment_outcome_record",
                      job_id)
        metadata = _validate_metadata_report(metadata, "metadata")
        with self._lock:
            job = self._get(self._enrichment_jobs, job_id, "enrichment job")
            return self._create(
                self._enrichment_outcomes, "enrout",
                {"job_id": job_id, "item_id": job["item_id"],
                 "metadata": metadata,
                 "outcome_basis": "engine_reported",
                 "reference_stub": True, "derived_here": False,
                 "applied_here": False},
                actor, "ext_enrichment_outcome_record",
                details={"job_id": job_id})

    def get_enrichment_job(self, job_id, actor=None):
        """Return one enrichment job record. Action: type_read."""
        self._require_read(actor, "type_read", "ext_enrichment_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._enrichment_jobs, job_id, "enrichment job"))

    def list_enrichment_jobs(self, actor=None):
        """Return enrichment jobs sorted by id. Action: type_read."""
        self._require_read(actor, "type_read", "ext_enrichment_read")
        with self._lock:
            records = sorted(self._enrichment_jobs.values(),
                             key=lambda r: _id_num(r["id"]))
            return [copy.deepcopy(r) for r in records]

    def list_enrichment_outcomes(self, job_id=None, actor=None):
        """Return enrichment outcomes, optionally per job.

        Action: type_read.
        """
        self._require_read(actor, "type_read", "ext_enrichment_read")
        with self._lock:
            records = sorted(self._enrichment_outcomes.values(),
                             key=lambda r: _id_num(r["id"]))
            if job_id is not None:
                records = [r for r in records if r["job_id"] == job_id]
            return [copy.deepcopy(r) for r in records]

    # -- Physical-content intake & digitization pipeline (built) -----
    # Intake records describe physical records as metadata;
    # stage events are recorded verbatim and the current stage
    # is derived at read. A digitization outcome binds the
    # intake to the core asset registration that is its
    # digitized surrogate. Nothing is scanned or converted here.

    @staticmethod
    def _current_intake_stage(steps):
        """Intake current-stage seam: the latest stage event's label.

        The current stage of an intake is derived at read time
        from its recorded stage events and stored nowhere; an
        intake with no stage events reads ``received``. This is
        the single derivation point — the batch's fresh negative
        control mutates it.
        """
        if not steps:
            return "received"
        return steps[-1]["label"]

    def register_physical_intake(self, actor, source_ref, form_label,
                                 pages_reported=None, condition_label=None):
        """Register a physical-content intake record.

        Action: asset_write. Ids: int-{n}. The record describes
        physical records as metadata: an opaque source
        reference, a form label (for example "paper file" or
        "microfilm"), a page count stored exactly as reported,
        and an optional condition label. The physical records
        themselves are never held (``content_held`` False) and
        nothing is scanned here (``scanned_here`` False).
        """
        self._require(actor, "asset_write", "ext_intake_register")
        _validate_non_empty(source_ref, "source_ref")
        _validate_non_empty(form_label, "form_label")
        if pages_reported is not None:
            _validate_count(pages_reported, "pages_reported")
        if condition_label is not None:
            _validate_non_empty(condition_label, "condition_label")
        with self._lock:
            return self._create(
                self._intakes, "int",
                {"source_ref": source_ref, "form_label": form_label,
                 "pages_reported": pages_reported,
                 "condition_label": condition_label,
                 "steps": [], "digitization": None,
                 "scanned_here": False, "converted_here": False,
                 "content_held": False},
                actor, "ext_intake_register",
                details={"form_label": form_label})

    def record_digitization_step(self, actor, intake_id, step_label):
        """Record a pipeline stage event against an intake.

        Action: asset_write. Stage labels are recorded verbatim
        (for example "in_transit", "prep_complete",
        "scan_complete", "quality_checked"); the intake's
        current stage is derived from these events at read time
        and stored nowhere. Recording a stage event performs no
        stage — nothing is scanned or converted here.
        """
        self._require(actor, "asset_write", "ext_digitization_step", intake_id)
        _validate_non_empty(step_label, "step_label")
        with self._lock:
            record = self._get(self._intakes, intake_id, "intake")
            self._audit(actor, "ext_digitization_step", intake_id,
                        details={"step_label": step_label})
            record["steps"].append({
                "label": step_label,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            })
            return self._intake_view(record)

    def record_digitization_outcome(self, actor, intake_id, asset_id,
                                    outcome_label):
        """Bind an intake to its digitized surrogate asset.

        Action: asset_write. ``asset_id`` must resolve in the
        core asset registry: that registration (metadata +
        checksum, made through the core's own function) is the
        digitized surrogate this pipeline tracks. The outcome is
        recorded once per intake; the outcome label is also
        appended as a stage event so the derived current stage
        reflects it. The conversion itself was not performed
        here (``converted_here`` False on the outcome and on
        the intake).
        """
        self._require(actor, "asset_write", "ext_digitization_outcome",
                      intake_id)
        _validate_non_empty(asset_id, "asset_id")
        _validate_non_empty(outcome_label, "outcome_label")
        with self._lock:
            record = self._get(self._intakes, intake_id, "intake")
            if record["digitization"] is not None:
                raise ValidationError(
                    "intake %r already has a digitization outcome"
                    % (intake_id,))
            self.store.get_asset(asset_id, actor=None)
            self._audit(actor, "ext_digitization_outcome", intake_id,
                        details={"asset_id": asset_id})
            now = _utc_now()
            record["digitization"] = {
                "asset_id": asset_id,
                "outcome_label": outcome_label,
                "converted_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": now,
            }
            record["steps"].append({
                "label": outcome_label,
                "recorded_by": actor_name(actor),
                "recorded_utc": now,
            })
            return self._intake_view(record)

    def _intake_view(self, record):
        view = copy.deepcopy(record)
        view["current_stage"] = self._current_intake_stage(record["steps"])
        view["step_count"] = len(record["steps"])
        view["digitized"] = record["digitization"] is not None
        return view

    def get_intake(self, intake_id, actor=None):
        """Return one intake with its derived current stage.

        Action: asset_read.
        """
        self._require_read(actor, "asset_read", "ext_intake_read")
        with self._lock:
            return self._intake_view(
                self._get(self._intakes, intake_id, "intake"))

    def list_intakes(self, actor=None):
        """Return intakes with derived stages, sorted by id.

        Action: asset_read.
        """
        self._require_read(actor, "asset_read", "ext_intake_read")
        with self._lock:
            records = sorted(self._intakes.values(),
                             key=lambda r: _id_num(r["id"]))
            return [self._intake_view(r) for r in records]

    def digitization_summary(self, actor=None):
        """Derived counts over the intake register. Action: report_read.

        Counts only, computed at read time: intakes, how many
        are bound to a digitized surrogate, and intakes by
        derived current stage.
        """
        self._require_read(actor, "report_read", "ext_digitization_summary")
        with self._lock:
            views = [self._intake_view(r) for r in self._intakes.values()]
            by_stage = {}
            for view in views:
                by_stage[view["current_stage"]] = (
                    by_stage.get(view["current_stage"], 0) + 1)
            return {
                "intakes": len(views),
                "digitized": sum(1 for v in views if v["digitized"]),
                "by_stage": by_stage,
            }

    # -- Content services platform runtime (reference) ---------------
    # Hosting/delivery of the SaaS platform is a deployment
    # property (PLATFORM-LAYER.md decision 6); the reference
    # record holds the fork's substrate label as the fork's own.

    def _create_reference(self, actor, family, name, audit_action, flags,
                          extra=None):
        _validate_non_empty(name, "reference name")
        fields = {"family": family, "name": name, "reference_stub": True}
        fields.update(flags)
        if extra:
            fields.update(extra)
        with self._lock:
            return self._create(self._references, "ref", fields, actor,
                                audit_action, details={"family": family})

    def register_platform_runtime_reference(self, actor, name,
                                            substrate_label):
        """Register a content services platform runtime reference.

        Action: site_write. Per PLATFORM-LAYER.md decision 6,
        hosting/delivery of the fork's SaaS platform is a
        deployment property and does not transfer to the build;
        the substrate label is recorded verbatim as the fork's
        own. Nothing is hosted or delivered here
        (``hosted_here`` / ``delivered_here`` False) and the
        family's surface is a transport reference
        (``reference_transport`` True).
        """
        self._require(actor, "site_write", "ext_reference_create")
        _validate_non_empty(substrate_label, "substrate_label")
        return self._create_reference(
            actor, "platform_runtime", name, "ext_reference_create",
            {"reference_transport": True, "hosted_here": False,
             "delivered_here": False},
            {"substrate_label": substrate_label})

    def get_reference(self, ref_id, actor=None):
        """Return one reference record. Action: type_read."""
        self._require_read(actor, "type_read", "ext_reference_read")
        with self._lock:
            return copy.deepcopy(self._get(self._references, ref_id,
                                           "reference"))

    def list_references(self, family=None, actor=None):
        """Return reference records sorted by id. Action: type_read."""
        self._require_read(actor, "type_read", "ext_reference_read")
        with self._lock:
            records = sorted(self._references.values(),
                             key=lambda r: _id_num(r["id"]))
            if family is not None:
                records = [r for r in records if r["family"] == family]
            return [copy.deepcopy(r) for r in records]
