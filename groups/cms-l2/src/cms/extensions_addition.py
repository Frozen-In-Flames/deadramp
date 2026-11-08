"""Final GAPS batch extensions, second unit — CMS L2 remainder addition.

Labeled reference implementation for the one open entry of the
GAPS.md section "Remainder Addition — CMS L2 (+1 fork)": the
ML/AI content classification, extraction & enrichment engine
registered from the addition fork Iron Mountain InSight's
described headline function (ADDENDUM.md §5). This module is the
only code this unit adds; every existing module — including the
first batch unit's :mod:`cms.extensions` — is unchanged.

Disposition: the entry was drafted build-extension in the batch
triage and is **re-judged to a labeled reference implementation**
under ``gaps-batch/DECISION.md`` qualification 1 (grounds in
``BATCH-ADDITION.md``). The entry names a *learned* ML/AI engine,
and a learned engine's substance is inference over content. This
substrate's hard rule is that **content is never held**: content
items and asset registrations are registry metadata, tags, and
SHA-256 digests only, and no field shape on this surface can
hold a document body (signatures refuse content outright). There
is therefore nothing here for a classifier, extractor, or
enrichment engine to run over, and no deterministic derivation
over the group's own records constitutes classifying, extracting
from, or enriching content. The build contains no model.

What ships is the batch's established learned-inference form —
the form the sibling CMS L3-adjacent build adjudicated for this
same fork family's three engine entries (its idx 394–396), and
the AI groups at every tier:

- **Classification** — job records naming the target by
  reference only (a core item or asset reference, which must
  resolve, or an opaque external reference), the content
  optionally named by a validated SHA-256 digest, plus outcome
  records holding the external engine's reported labels
  **verbatim as reported** (``outcome_basis: "engine_reported"``).
  A confidence is held only as a verbatim reported *label*
  (a string); a numeric confidence is rejected at the boundary,
  and a recursive scan pins that no score-shaped key exists
  anywhere on the surface. ``classified_here`` is False on
  every record.
- **Extraction** — job records naming the source by reference
  (core asset/item, resolving, or opaque external) with the
  requested field labels held as data, plus outcome records
  holding the engine's reported ``{field_label, value}`` pairs
  verbatim under an exact pair-shape validation, deep-copied at
  the boundary. ``extracted_here`` is False on every record.
- **Enrichment** — job records bound to a core content item,
  plus outcome records holding the engine's reported key/value
  metadata verbatim **on the outcome record only**: it is never
  applied to the core item (``applied_here`` False,
  ``derived_here`` False, ``enriched_here`` False). This
  substrate stores caller-supplied metadata only and derives
  none; caller-supplied metadata reaches an item only through
  the core's own authoring functions.

Every record carries ``reference_stub: True`` and
``state: "recorded_reference_only"`` (jobs) — records *about*
the engine's work, never the engine. Job views derive outcome
counts and the latest reported outcome at read time via the
seam :meth:`CmsExtensionsAddition._latest_outcome`; nothing
derived is stored. An ``engine_summary`` view derives counts
only, at read.

Access control reuses the founding permission matrix — no new
actions exist. Following the CMS L2 first unit's
reference-register form: job and outcome writes use
``type_write`` with ``type_read`` reads; the summary uses
``report_read``. Audit actions are prefixed ``exta_`` (the
second-unit convention). Write enforcement mirrors the core
store: a missing actor is denied, a User-like actor is checked
against the matrix, and denials are recorded in the core audit
log as ``<action>:denied``. Reads enforce only when a User-like
actor is supplied, as in the core. This tier is L2: the audit
log is the core's plain append-only log — no High-tier
apparatus is imported downward.

Ids are sequential per object type with fixed prefixes
(``clsjob-``, ``clsout-``, ``extjob-``, ``extout-``,
``enrjob-``, ``enrout-``). A failed operation consumes no id
and changes nothing: all validation happens before any
mutation. All timestamps are UTC ISO-8601. Records returned
are copies; mutating a returned record changes nothing stored.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

__all__ = ["CmsExtensionsAddition"]

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


def _validate_string_list(value, what):
    if not isinstance(value, (list, tuple)) or not value:
        raise ValidationError(
            "%s must be a non-empty list of strings" % (what,))
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


class CmsExtensionsAddition:
    """Second-unit extension register wrapping a core CmsStore."""

    def __init__(self, store):
        self.store = store
        self.audit = getattr(store, "audit", None)
        self._classification_jobs = {}
        self._classification_outcomes = {}
        self._extraction_jobs = {}
        self._extraction_outcomes = {}
        self._enrichment_jobs = {}
        self._enrichment_outcomes = {}
        self._counters = {
            "clsjob": 0, "clsout": 0, "extjob": 0, "extout": 0,
            "enrjob": 0, "enrout": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers -------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(
                actor_name(actor), action, target, details=details)

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

    def _resolve_core(self, kind, ref):
        """Resolve a core item/asset reference or raise NotFoundError."""
        if kind == "item":
            return self.store.get_item(ref, actor=None)
        return self.store.get_asset(ref, actor=None)

    @staticmethod
    def _latest_outcome(outcomes):
        """Latest-outcome seam: the most recently recorded outcome.

        Every "latest reported" derivation on this surface — a
        classification job's latest labels, an extraction job's
        latest fields, an enrichment job's latest metadata — is
        the *last* outcome recorded for the job, derived at read
        time and stored nowhere. ``outcomes`` is the job's
        outcome list sorted by id. This is the single derivation
        point — the unit's fresh negative control mutates it.

        MUTATION DRILL NOTE: if this seam reads the earliest
        outcome instead, every job view reports stale engine
        output as current (see tests/README.md).
        """
        return outcomes[-1] if outcomes else None

    def _outcomes_for(self, collection, job_id):
        outcomes = [o for o in collection.values()
                    if o["job_id"] == job_id]
        outcomes.sort(key=lambda o: _id_num(o["id"]))
        return outcomes

    # -- ML/AI classification engine (reference) ---------------------
    # Job records name the classification target by reference;
    # outcome records hold the external engine's reported labels
    # verbatim. No model runs here and nothing is classified here.

    def register_classification_job(self, actor, target_ref,
                                    target_kind="external",
                                    taxonomy_ref=None,
                                    content_digest=None):
        """Record a classification job for an external ML engine.

        Action: type_write. Ids: clsjob-{n}. The target is named
        by reference only: a core item or asset reference (which
        must resolve), or an opaque external reference. The
        content itself is never held; it may be named by an
        optional SHA-256 digest. ``reference_stub`` is True and
        ``classified_here`` is False on every record.
        """
        self._require(actor, "type_write", "exta_classification_job_register")
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
            job_id = self._next_id("clsjob")
            record = {
                "id": job_id,
                "target_ref": target_ref,
                "target_kind": target_kind,
                "taxonomy_ref": taxonomy_ref,
                "content_digest": content_digest,
                "reference_stub": True,
                "classified_here": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._classification_jobs[job_id] = record
            self._audit(actor, "exta_classification_job_register", job_id,
                        details={"target_kind": target_kind})
            return copy.deepcopy(record)

    def record_classification_outcome(self, actor, job_id, labels,
                                      confidence_label=None):
        """Record a classification outcome, verbatim as reported.

        Action: type_write. Ids: clsout-{n}. ``labels`` are the
        external engine's reported labels, stored exactly as
        reported; ``confidence_label`` is likewise a verbatim
        reported label (a string — this build records no numeric
        confidence and computes no score). Nothing was
        classified by this build.
        """
        self._require(actor, "type_write",
                      "exta_classification_outcome_record", job_id)
        labels = _validate_string_list(labels, "labels")
        if confidence_label is not None:
            _validate_non_empty(confidence_label, "confidence_label")
        with self._lock:
            self._get(self._classification_jobs, job_id,
                      "classification job")
            outcome_id = self._next_id("clsout")
            record = {
                "id": outcome_id,
                "job_id": job_id,
                "labels": labels,
                "confidence_label": confidence_label,
                "outcome_basis": "engine_reported",
                "reference_stub": True,
                "classified_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._classification_outcomes[outcome_id] = record
            self._audit(actor, "exta_classification_outcome_record",
                        outcome_id, details={"job_id": job_id})
            return copy.deepcopy(record)

    def _classification_job_view(self, record):
        view = copy.deepcopy(record)
        outcomes = self._outcomes_for(
            self._classification_outcomes, record["id"])
        latest = self._latest_outcome(outcomes)
        view["outcome_count"] = len(outcomes)
        view["latest_labels"] = (
            list(latest["labels"]) if latest is not None else [])
        return view

    def get_classification_job(self, job_id, actor=None):
        """Return one classification job with derived outcome data.

        Action: type_read.
        """
        self._require_read(actor, "type_read", "exta_classification_read")
        with self._lock:
            return self._classification_job_view(
                self._get(self._classification_jobs, job_id,
                          "classification job"))

    def list_classification_jobs(self, actor=None):
        """Return classification jobs sorted by id. Action: type_read."""
        self._require_read(actor, "type_read", "exta_classification_read")
        with self._lock:
            records = sorted(self._classification_jobs.values(),
                             key=lambda r: _id_num(r["id"]))
            return [self._classification_job_view(r) for r in records]

    def list_classification_outcomes(self, job_id=None, actor=None):
        """Return classification outcomes, optionally per job.

        Action: type_read.
        """
        self._require_read(actor, "type_read", "exta_classification_read")
        with self._lock:
            records = sorted(self._classification_outcomes.values(),
                             key=lambda r: _id_num(r["id"]))
            if job_id is not None:
                records = [r for r in records if r["job_id"] == job_id]
            return [copy.deepcopy(r) for r in records]

    # -- ML/AI extraction engine (reference) -------------------------
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
        content may be named by an optional SHA-256 digest and
        is never held. ``field_labels`` optionally records the
        field names the engine was asked to extract, as data.
        ``reference_stub`` is True and ``extracted_here`` is
        False on every record.
        """
        self._require(actor, "type_write", "exta_extraction_job_register")
        _validate_non_empty(source_ref, "source_ref")
        if source_kind not in SOURCE_KINDS:
            raise ValidationError(
                "source_kind must be one of %s" % (", ".join(SOURCE_KINDS),))
        if field_labels is not None:
            field_labels = _validate_string_list(
                field_labels, "field_labels")
        content_digest = _validate_digest(content_digest, "content_digest")
        with self._lock:
            if source_kind in ("item", "asset"):
                self._resolve_core(source_kind, source_ref)
            job_id = self._next_id("extjob")
            record = {
                "id": job_id,
                "source_ref": source_ref,
                "source_kind": source_kind,
                "field_labels": field_labels,
                "content_digest": content_digest,
                "reference_stub": True,
                "extracted_here": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._extraction_jobs[job_id] = record
            self._audit(actor, "exta_extraction_job_register", job_id,
                        details={"source_kind": source_kind})
            return copy.deepcopy(record)

    def record_extraction_outcome(self, actor, job_id, fields):
        """Record an extraction outcome, verbatim as reported.

        Action: type_write. Ids: extout-{n}. ``fields`` are
        {field_label, value} pairs the external engine reported,
        stored exactly as reported; nothing was extracted by
        this build.
        """
        self._require(actor, "type_write",
                      "exta_extraction_outcome_record", job_id)
        fields = _validate_reported_fields(fields, "fields")
        with self._lock:
            self._get(self._extraction_jobs, job_id, "extraction job")
            outcome_id = self._next_id("extout")
            record = {
                "id": outcome_id,
                "job_id": job_id,
                "fields": fields,
                "outcome_basis": "engine_reported",
                "reference_stub": True,
                "extracted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._extraction_outcomes[outcome_id] = record
            self._audit(actor, "exta_extraction_outcome_record",
                        outcome_id, details={"job_id": job_id})
            return copy.deepcopy(record)

    def _extraction_job_view(self, record):
        view = copy.deepcopy(record)
        outcomes = self._outcomes_for(
            self._extraction_outcomes, record["id"])
        latest = self._latest_outcome(outcomes)
        view["outcome_count"] = len(outcomes)
        view["latest_fields"] = (
            copy.deepcopy(latest["fields"]) if latest is not None else [])
        return view

    def get_extraction_job(self, job_id, actor=None):
        """Return one extraction job with derived outcome data.

        Action: type_read.
        """
        self._require_read(actor, "type_read", "exta_extraction_read")
        with self._lock:
            return self._extraction_job_view(
                self._get(self._extraction_jobs, job_id, "extraction job"))

    def list_extraction_jobs(self, actor=None):
        """Return extraction jobs sorted by id. Action: type_read."""
        self._require_read(actor, "type_read", "exta_extraction_read")
        with self._lock:
            records = sorted(self._extraction_jobs.values(),
                             key=lambda r: _id_num(r["id"]))
            return [self._extraction_job_view(r) for r in records]

    def list_extraction_outcomes(self, job_id=None, actor=None):
        """Return extraction outcomes, optionally per job.

        Action: type_read.
        """
        self._require_read(actor, "type_read", "exta_extraction_read")
        with self._lock:
            records = sorted(self._extraction_outcomes.values(),
                             key=lambda r: _id_num(r["id"]))
            if job_id is not None:
                records = [r for r in records if r["job_id"] == job_id]
            return [copy.deepcopy(r) for r in records]

    # -- ML/AI enrichment engine (reference) -------------------------
    # Job records bind an enrichment request to a core item;
    # outcome records hold the external engine's reported
    # metadata verbatim. The substrate derives no metadata, and
    # a reported outcome is never applied to the core item.

    def register_enrichment_job(self, actor, item_id):
        """Record an enrichment job against a core content item.

        Action: type_write. Ids: enrjob-{n}. The item must
        resolve in the core registry. ``reference_stub`` is True
        and ``derived_here`` / ``enriched_here`` are False on
        every record: this substrate stores caller-supplied
        metadata only and derives none.
        """
        self._require(actor, "type_write",
                      "exta_enrichment_job_register", item_id)
        _validate_non_empty(item_id, "item_id")
        with self._lock:
            self.store.get_item(item_id, actor=None)
            job_id = self._next_id("enrjob")
            record = {
                "id": job_id,
                "item_id": item_id,
                "reference_stub": True,
                "derived_here": False,
                "enriched_here": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._enrichment_jobs[job_id] = record
            self._audit(actor, "exta_enrichment_job_register", job_id,
                        details={"item_id": item_id})
            return copy.deepcopy(record)

    def record_enrichment_outcome(self, actor, job_id, metadata):
        """Record an enrichment outcome, verbatim as reported.

        Action: type_write. Ids: enrout-{n}. ``metadata`` is the
        external engine's reported key/value metadata, stored
        exactly as reported on this outcome record only. It is
        **not applied** to the core item (``applied_here``
        False): caller-supplied metadata reaches an item only
        through the core's own authoring functions.
        """
        self._require(actor, "type_write",
                      "exta_enrichment_outcome_record", job_id)
        metadata = _validate_metadata_report(metadata, "metadata")
        with self._lock:
            job = self._get(self._enrichment_jobs, job_id,
                            "enrichment job")
            outcome_id = self._next_id("enrout")
            record = {
                "id": outcome_id,
                "job_id": job_id,
                "item_id": job["item_id"],
                "metadata": metadata,
                "outcome_basis": "engine_reported",
                "reference_stub": True,
                "derived_here": False,
                "enriched_here": False,
                "applied_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._enrichment_outcomes[outcome_id] = record
            self._audit(actor, "exta_enrichment_outcome_record",
                        outcome_id, details={"job_id": job_id})
            return copy.deepcopy(record)

    def _enrichment_job_view(self, record):
        view = copy.deepcopy(record)
        outcomes = self._outcomes_for(
            self._enrichment_outcomes, record["id"])
        latest = self._latest_outcome(outcomes)
        view["outcome_count"] = len(outcomes)
        view["latest_metadata"] = (
            dict(latest["metadata"]) if latest is not None else {})
        return view

    def get_enrichment_job(self, job_id, actor=None):
        """Return one enrichment job with derived outcome data.

        Action: type_read.
        """
        self._require_read(actor, "type_read", "exta_enrichment_read")
        with self._lock:
            return self._enrichment_job_view(
                self._get(self._enrichment_jobs, job_id,
                          "enrichment job"))

    def list_enrichment_jobs(self, actor=None):
        """Return enrichment jobs sorted by id. Action: type_read."""
        self._require_read(actor, "type_read", "exta_enrichment_read")
        with self._lock:
            records = sorted(self._enrichment_jobs.values(),
                             key=lambda r: _id_num(r["id"]))
            return [self._enrichment_job_view(r) for r in records]

    def list_enrichment_outcomes(self, job_id=None, actor=None):
        """Return enrichment outcomes, optionally per job.

        Action: type_read.
        """
        self._require_read(actor, "type_read", "exta_enrichment_read")
        with self._lock:
            records = sorted(self._enrichment_outcomes.values(),
                             key=lambda r: _id_num(r["id"]))
            if job_id is not None:
                records = [r for r in records if r["job_id"] == job_id]
            return [copy.deepcopy(r) for r in records]

    # -- derived summary ----------------------------------------------

    def engine_summary(self, actor=None):
        """Derive engine-surface counts at read time.

        Action: report_read. Counts only, computed from the job
        and outcome registers; stored nowhere. The flags restate
        the surface's honesty labels: no classification,
        extraction, or enrichment is performed here.
        """
        self._require_read(actor, "report_read", "exta_engine_summary")
        with self._lock:
            return {
                "classification_jobs": len(self._classification_jobs),
                "classification_outcomes": len(
                    self._classification_outcomes),
                "extraction_jobs": len(self._extraction_jobs),
                "extraction_outcomes": len(self._extraction_outcomes),
                "enrichment_jobs": len(self._enrichment_jobs),
                "enrichment_outcomes": len(self._enrichment_outcomes),
                "reference_stub": True,
                "classified_here": False,
                "extracted_here": False,
                "enriched_here": False,
            }
