"""Final GAPS batch extensions for Law Enforcement L3-adjacent.

Clean-room, standard-library-only records extensions for the 8
open Extended entries of this group's union spec -- the group's
own forensic verticals, claimed in the two forks' own words
(Cellebrite Government Cloud; Magnet One). Per-entry
dispositions, the re-judgment grounds, and the not-covered list
are in ``BATCH.md`` in the group directory: 6 entries built as
records in-substrate, 2 re-judged to labeled reference
implementations (device unlocking; evidence extraction from
mobile devices).

Design, following the core's doctrines and this group's High
baseline:

- This module is a wrapper around :class:`LawEnfStore`; the
  core modules are untouched (byte-identical). Matter
  existence, membership, and lifecycle state are always read
  through the core store's public API, never re-implemented.
- **The hard privacy rule binds the whole surface.** Every
  record is keyed by an opaque caller-supplied ``*_ref`` string
  or a core record id, and holds metadata and SHA-256 digests
  only. Artifact content is never held: extraction and ingest
  records carry an artifact's digest and byte count, exactly as
  the core's document registry does, and integrity is checkable
  by verify-by-content (the caller supplies bytes; the build
  hashes and compares, storing nothing). There is no parameter
  anywhere in this module that could accept evidence content,
  a finding's text, a report's text, or a person's identifier
  -- the batch tests pin that by signature (``TypeError``).
- **Records of forensic work, never forensic engines.** Every
  vertical closes as records: examination and analysis results
  are recorded as reported (verbatim labels, opaque result
  references); no finding is computed, no device is examined,
  no evidence is processed here. Each record carries its
  boundary label (``analyzed_here`` / ``extracted_here`` /
  ``processed_here`` / ... are False).
- **Device unlocking and extraction capability are not built in
  any form.** Those two entries are re-judged to labeled
  reference implementations: their records hold only a request
  (an opaque device reference) and its reported outcome label,
  and every record carries ``reference_stub: True`` and
  ``capability_held_here: False``. Nothing here defeats, or
  describes defeating, a device access control; grounds in
  ``BATCH.md``.
- **Chain of custody is records, not enforcement.** Custody
  closes as transfer records over artifact digests. The
  substrate's checksums, verify-by-content, and hash-chained
  audit are records-side analogues of custody enforcement --
  stated as analogues, not equivalents, in the union spec --
  and every custody record carries
  ``custody_enforced_here: False``.
- **High apparatus binds the new surface.** Extension
  mutations are audited on the core store's hash-chained audit
  log **audit-before-commit** (AU-5): the audit entry is
  written before the record is committed, so a failed audit
  write (:class:`~lawenf.errors.AuditWriteError`) leaves no
  record and consumes no id -- fail-closed, exactly as the
  core's ``_atomic`` guard. The auditor role (``audit_read``
  only) holds no core action any extension operation maps to,
  so it is denied every extension operation, read and write;
  denials are audited ``ext_<action>:denied``.
- RBAC goes through :mod:`lawenf.access` exactly as the core
  enforces it: the extension maps each operation onto an
  existing core action (the core action set is fixed -- see the
  mapping in ``BATCH.md``), checks it *before* any state change
  or id allocation for actors that carry a role, and records
  denied attempts on the core audit log. Matter membership --
  the core's second boundary -- is enforced through the core
  store on every operation, and writes additionally require an
  open matter, mirroring the core's ``need_open`` discipline.
- Derived values are derived at read and never stored: an
  artifact's current holder and transfer count, view counts
  and latest reported outcomes, a forensic report's registry
  counts. Stored records carry no derived key; tests pin that.
  The current-holder derivation lives at a single named seam
  (``_current_holder``): the batch's fresh negative control.
"""

import copy
import hashlib
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

REVIEW_TARGET_KINDS = ("document", "ingest_artifact")
SHARE_TARGET_KINDS = ("document", "artifact", "custody_transfer")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None:
        _non_empty(value, what)
    return value


def _sha256(value, what):
    if not isinstance(value, str) or not _SHA256_RE.match(value):
        raise ValidationError(
            "%s must be exactly 64 lowercase hex characters" % (what,)
        )
    return value


def _sha256_or_none(value, what):
    if value is not None:
        _sha256(value, what)
    return value


def _count(value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be an integer >= 0" % (what,))
    return value


class LawEnfExtensions:
    """GAPS-batch extension surface over a core LawEnfStore."""

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

        Mirrors the core store: an actor must be present; actors
        carrying a role are checked against the core permission
        matrix before anything changes; plain strings carry
        identity only. The auditor role holds none of the write
        actions, so it is denied here on every write.
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
        """Enforce a read permission when the actor carries a role.

        The auditor role holds neither ``matter_read`` nor
        ``report_read``, so it is denied here on every read and
        view as well.
        """
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, core_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", target)
                raise

    def _matter(self, actor, matter_id, audit_action, need_open=False):
        """Resolve a matter through the core store (existence and
        membership enforced there); a membership denial is audited
        under the extension action name. Writes pass
        ``need_open=True`` and require an open matter, mirroring
        the core's child-record discipline."""
        try:
            matter = self.store.get_matter(matter_id, actor)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", matter_id)
            raise
        if need_open and matter["status"] != "open":
            raise ValidationError(
                "matter %s is closed; no new records may be added" % (matter_id,)
            )
        return matter

    def _create(self, kind, prefix, fields, actor, audit_action):
        """Commit a record, auditing BEFORE the commit (AU-5).

        The audit entry is written to the core hash-chained log
        first; only when it is durably recorded is the record
        inserted and the id counter advanced. If the audit write
        fails, :class:`AuditWriteError` propagates with nothing
        inserted and no id consumed -- the extension surface is
        fail-closed exactly as the core store is.
        """
        with self._lock:
            record_id = "%s-%d" % (prefix, self._counters.get(prefix, 0) + 1)
            record = {"id": record_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._audit(actor, audit_action, record_id,
                        details={"kind": kind})
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            return copy.deepcopy(record)

    def _get(self, kind, record_id, matter_id=None):
        record = self._records.get((kind, record_id))
        if record is None or (matter_id is not None
                              and record["matter_id"] != matter_id):
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id, matter_id=None):
        return copy.deepcopy(self._get(kind, record_id, matter_id))

    def _list(self, kind, **filters):
        result = []
        for key in self._order:
            if key[0] != kind:
                continue
            record = self._records[key]
            if all(record.get(name) == value for name, value in filters.items()
                   if value is not None):
                result.append(copy.deepcopy(record))
        return result

    def _check_ref_unique(self, kind, matter_id, field, value, what):
        for record in self._list(kind, matter_id=matter_id):
            if record[field] == value:
                raise ValidationError(
                    "%s %r already exists in matter %s"
                    % (what, value, matter_id))

    # -- Device unlocking (Cellebrite) --------------------------------
    # RE-JUDGED to a labeled reference implementation (grounds in
    # BATCH.md): the entry's substance is a capability that
    # defeats device access controls, and no such capability is
    # built here in any form. The records hold only a request --
    # an opaque device reference -- and its outcome label as
    # reported by whatever external capability the embedding
    # organization operates. Every record carries
    # ``reference_stub: True``, ``unlocked_here: False``, and
    # ``capability_held_here: False``; there is no parameter that
    # could accept a credential, a bypass code, or device data.

    def record_unlock_request(self, matter_id, request_ref, device_ref,
                              actor):
        """Record a device-unlock request (reference). Action: search_write."""
        self._guard(actor, "search_write", "ext_unlock_request_record",
                    matter_id)
        _non_empty(request_ref, "request_ref")
        _non_empty(device_ref, "device_ref")
        with self._lock:
            self._matter(actor, matter_id, "ext_unlock_request_record",
                         need_open=True)
            self._check_ref_unique("unlock_request", matter_id, "request_ref",
                                   request_ref, "request_ref")
            return self._create(
                "unlock_request", "unl",
                {"matter_id": matter_id, "request_ref": request_ref,
                 "device_ref": device_ref, "reference_stub": True,
                 "unlocked_here": False, "capability_held_here": False,
                 "status": "recorded_reference_only"},
                actor, "ext_unlock_request_record")

    def get_unlock_request(self, matter_id, request_id, actor=None):
        """Return one unlock request record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_unlock_request_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_unlock_request_read")
            return self._fetch("unlock_request", request_id, matter_id)

    def list_unlock_requests(self, matter_id, actor=None):
        """Return unlock request records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_unlock_request_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_unlock_request_read")
            return self._list("unlock_request", matter_id=matter_id)

    def record_unlock_outcome(self, matter_id, request_id, outcome_label,
                              actor):
        """Record an unlock outcome label as reported, verbatim.

        Action: search_write. The label is the external
        capability's report; nothing was unlocked here.
        """
        self._guard(actor, "search_write", "ext_unlock_outcome_record",
                    matter_id)
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_unlock_outcome_record",
                         need_open=True)
            self._get("unlock_request", request_id, matter_id)
            return self._create(
                "unlock_outcome", "uno",
                {"matter_id": matter_id, "request_id": request_id,
                 "outcome_label": outcome_label, "reference_stub": True,
                 "unlocked_here": False},
                actor, "ext_unlock_outcome_record")

    def list_unlock_outcomes(self, matter_id, request_id=None, actor=None):
        """Return unlock outcome records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_unlock_outcome_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_unlock_outcome_read")
            if request_id is not None:
                self._get("unlock_request", request_id, matter_id)
            return self._list("unlock_outcome", matter_id=matter_id,
                              request_id=request_id)

    def unlock_request_view(self, matter_id, request_id, actor=None):
        """Derived view of an unlock request. Action: report_read.

        The outcome count and latest reported outcome label are
        computed at read; the stored request carries neither.
        """
        self._guard_read(actor, "report_read", "ext_unlock_request_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_unlock_request_view")
            request = self._get("unlock_request", request_id, matter_id)
            outcomes = self._list("unlock_outcome", matter_id=matter_id,
                                  request_id=request_id)
            view = dict(request)
            view["outcome_count"] = len(outcomes)
            view["latest_outcome"] = (
                outcomes[-1]["outcome_label"] if outcomes else None)
            view["derived_at_read"] = True
            return view

    # -- Evidence extraction from mobile devices (Cellebrite) ---------
    # RE-JUDGED to a labeled reference implementation (grounds in
    # BATCH.md): extraction is the capability that pulls data off
    # a device past its access controls; the artifacts it
    # produces are registered by the ingest surface below and by
    # the core document registry. The records here hold only a
    # request (an opaque device reference) and its outcome label
    # as reported. Every record carries ``reference_stub: True``,
    # ``extracted_here: False``, and ``capability_held_here:
    # False``; nothing is extracted here and no device data of
    # any kind enters this build through this surface.

    def record_extraction_request(self, matter_id, request_ref, device_ref,
                                  actor):
        """Record an extraction request (reference). Action: search_write."""
        self._guard(actor, "search_write", "ext_extraction_request_record",
                    matter_id)
        _non_empty(request_ref, "request_ref")
        _non_empty(device_ref, "device_ref")
        with self._lock:
            self._matter(actor, matter_id, "ext_extraction_request_record",
                         need_open=True)
            self._check_ref_unique("extraction_request", matter_id,
                                   "request_ref", request_ref, "request_ref")
            return self._create(
                "extraction_request", "exr",
                {"matter_id": matter_id, "request_ref": request_ref,
                 "device_ref": device_ref, "reference_stub": True,
                 "extracted_here": False, "capability_held_here": False,
                 "status": "recorded_reference_only"},
                actor, "ext_extraction_request_record")

    def get_extraction_request(self, matter_id, request_id, actor=None):
        """Return one extraction request record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_extraction_request_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_extraction_request_read")
            return self._fetch("extraction_request", request_id, matter_id)

    def list_extraction_requests(self, matter_id, actor=None):
        """Return extraction request records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_extraction_request_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_extraction_request_read")
            return self._list("extraction_request", matter_id=matter_id)

    def record_extraction_outcome(self, matter_id, request_id, outcome_label,
                                  actor):
        """Record an extraction outcome label as reported, verbatim.

        Action: search_write. The label is the external
        capability's report; nothing was extracted here.
        """
        self._guard(actor, "search_write", "ext_extraction_outcome_record",
                    matter_id)
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_extraction_outcome_record",
                         need_open=True)
            self._get("extraction_request", request_id, matter_id)
            return self._create(
                "extraction_outcome", "exo",
                {"matter_id": matter_id, "request_id": request_id,
                 "outcome_label": outcome_label, "reference_stub": True,
                 "extracted_here": False},
                actor, "ext_extraction_outcome_record")

    def list_extraction_outcomes(self, matter_id, request_id=None, actor=None):
        """Return extraction outcome records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_extraction_outcome_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_extraction_outcome_read")
            if request_id is not None:
                self._get("extraction_request", request_id, matter_id)
            return self._list("extraction_outcome", matter_id=matter_id,
                              request_id=request_id)

    def extraction_request_view(self, matter_id, request_id, actor=None):
        """Derived view of an extraction request. Action: report_read.

        The outcome count and latest reported outcome label are
        computed at read; the stored request carries neither.
        """
        self._guard_read(actor, "report_read", "ext_extraction_request_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_extraction_request_view")
            request = self._get("extraction_request", request_id, matter_id)
            outcomes = self._list("extraction_outcome", matter_id=matter_id,
                                  request_id=request_id)
            view = dict(request)
            view["outcome_count"] = len(outcomes)
            view["latest_outcome"] = (
                outcomes[-1]["outcome_label"] if outcomes else None)
            view["derived_at_read"] = True
            return view

    # -- Forensic analysis engines (both siblings) --------------------
    # The records form of the analysis surface: an analysis
    # record (an opaque reference, an optional method label
    # recorded verbatim, an optional binding to a core document
    # record) and finding records that hold an opaque result
    # reference and a verbatim reported label. No finding is
    # computed and nothing is analyzed here (``analyzed_here`` /
    # ``findings_computed_here`` / ``computed_here`` are False);
    # there is no parameter that could accept a finding's text
    # or any evidence content -- the analysis engines are the
    # forks' products.

    def record_analysis(self, matter_id, analysis_ref, actor,
                        method_label=None, target_document_id=None):
        """Record a forensic analysis. Action: search_write.

        ``target_document_id`` optionally binds the analysis to
        a core document record in the same matter.
        """
        self._guard(actor, "search_write", "ext_analysis_record", matter_id)
        _non_empty(analysis_ref, "analysis_ref")
        _string_or_none(method_label, "method_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_analysis_record",
                         need_open=True)
            if target_document_id is not None:
                self.store.get_document(matter_id, target_document_id, actor)
            self._check_ref_unique("analysis_record", matter_id,
                                   "analysis_ref", analysis_ref, "analysis_ref")
            return self._create(
                "analysis_record", "ana",
                {"matter_id": matter_id, "analysis_ref": analysis_ref,
                 "method_label": method_label,
                 "target_document_id": target_document_id,
                 "analyzed_here": False, "findings_computed_here": False,
                 "status": "recorded"},
                actor, "ext_analysis_record")

    def get_analysis(self, matter_id, analysis_id, actor=None):
        """Return one analysis record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_analysis_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_analysis_read")
            return self._fetch("analysis_record", analysis_id, matter_id)

    def list_analyses(self, matter_id, actor=None):
        """Return analysis records for a matter. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_analysis_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_analysis_read")
            return self._list("analysis_record", matter_id=matter_id)

    def record_analysis_finding(self, matter_id, analysis_id, result_ref,
                                actor, finding_label=None):
        """Record an analysis finding as reported.

        Action: search_write. ``result_ref`` is an opaque
        reference to a result held by the owning platform; the
        optional ``finding_label`` is the platform's report,
        stored verbatim. No finding content enters this build
        and no finding was computed here.
        """
        self._guard(actor, "search_write", "ext_analysis_finding_record",
                    matter_id)
        _non_empty(result_ref, "result_ref")
        _string_or_none(finding_label, "finding_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_analysis_finding_record",
                         need_open=True)
            self._get("analysis_record", analysis_id, matter_id)
            return self._create(
                "analysis_finding", "anf",
                {"matter_id": matter_id, "analysis_id": analysis_id,
                 "result_ref": result_ref, "finding_label": finding_label,
                 "reported_only": True, "computed_here": False,
                 "content_held": False},
                actor, "ext_analysis_finding_record")

    def list_analysis_findings(self, matter_id, analysis_id=None, actor=None):
        """Return analysis finding records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_analysis_finding_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_analysis_finding_read")
            if analysis_id is not None:
                self._get("analysis_record", analysis_id, matter_id)
            return self._list("analysis_finding", matter_id=matter_id,
                              analysis_id=analysis_id)

    def analysis_view(self, matter_id, analysis_id, actor=None):
        """Derived view of an analysis record. Action: report_read.

        The finding count is computed at read from the stored
        finding records; the stored analysis record carries no
        count, and the view computes no finding.
        """
        self._guard_read(actor, "report_read", "ext_analysis_view", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_analysis_view")
            analysis = self._get("analysis_record", analysis_id, matter_id)
            findings = self._list("analysis_finding", matter_id=matter_id,
                                  analysis_id=analysis_id)
            view = dict(analysis)
            view["finding_count"] = len(findings)
            view["derived_at_read"] = True
            return view

    # -- Evidence ingest & processing pipelines (Magnet One) ----------
    # The records form of the pipeline surface: ingest batch
    # records, artifact records holding an artifact's SHA-256
    # digest and byte count (the core document registry's
    # discipline applied to pipeline artifacts -- content is
    # never held), and processing-stage reports recorded
    # verbatim as reported. No artifact is ingested or processed
    # here (``ingested_here`` / ``processed_here`` are False):
    # the pipeline is the fork's product; this surface is the
    # batch/artifact/report registry its operation presupposes.

    def record_ingest_batch(self, matter_id, batch_ref, actor,
                            source_label=None):
        """Record an evidence ingest batch. Action: document_write."""
        self._guard(actor, "document_write", "ext_ingest_batch_record",
                    matter_id)
        _non_empty(batch_ref, "batch_ref")
        _string_or_none(source_label, "source_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_ingest_batch_record",
                         need_open=True)
            self._check_ref_unique("ingest_batch", matter_id, "batch_ref",
                                   batch_ref, "batch_ref")
            return self._create(
                "ingest_batch", "ing",
                {"matter_id": matter_id, "batch_ref": batch_ref,
                 "source_label": source_label, "ingested_here": False,
                 "processed_here": False, "status": "recorded"},
                actor, "ext_ingest_batch_record")

    def get_ingest_batch(self, matter_id, batch_id, actor=None):
        """Return one ingest batch record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_ingest_batch_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_ingest_batch_read")
            return self._fetch("ingest_batch", batch_id, matter_id)

    def list_ingest_batches(self, matter_id, actor=None):
        """Return ingest batch records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_ingest_batch_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_ingest_batch_read")
            return self._list("ingest_batch", matter_id=matter_id)

    def record_ingest_artifact(self, matter_id, batch_id, artifact_ref,
                               sha256, size_bytes, actor):
        """Record an ingested artifact as metadata + SHA-256.

        Action: document_write. Exactly the core document
        registry's discipline: the artifact's content never
        enters this build; the record holds its opaque
        reference, its checksum, and its byte count.
        ``artifact_ref`` is unique within the batch.
        """
        self._guard(actor, "document_write", "ext_ingest_artifact_record",
                    matter_id)
        _non_empty(artifact_ref, "artifact_ref")
        _sha256(sha256, "sha256")
        _count(size_bytes, "size_bytes")
        with self._lock:
            self._matter(actor, matter_id, "ext_ingest_artifact_record",
                         need_open=True)
            self._get("ingest_batch", batch_id, matter_id)
            for record in self._list("ingest_artifact", matter_id=matter_id,
                                     batch_id=batch_id):
                if record["artifact_ref"] == artifact_ref:
                    raise ValidationError(
                        "artifact_ref %r already exists in batch %s"
                        % (artifact_ref, batch_id))
            return self._create(
                "ingest_artifact", "ina",
                {"matter_id": matter_id, "batch_id": batch_id,
                 "artifact_ref": artifact_ref, "sha256": sha256,
                 "size_bytes": size_bytes, "content_held": False},
                actor, "ext_ingest_artifact_record")

    def list_ingest_artifacts(self, matter_id, batch_id=None, actor=None):
        """Return ingest artifact records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_ingest_artifact_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_ingest_artifact_read")
            if batch_id is not None:
                self._get("ingest_batch", batch_id, matter_id)
            return self._list("ingest_artifact", matter_id=matter_id,
                              batch_id=batch_id)

    def record_processing_report(self, matter_id, batch_id, stage_label,
                                 outcome_label, actor):
        """Record a processing-stage report as reported, verbatim.

        Action: document_write. The stage and outcome labels are
        the pipeline's report, stored exactly as supplied; no
        processing ran here.
        """
        self._guard(actor, "document_write", "ext_processing_report_record",
                    matter_id)
        _non_empty(stage_label, "stage_label")
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_processing_report_record",
                         need_open=True)
            self._get("ingest_batch", batch_id, matter_id)
            return self._create(
                "processing_report", "inp",
                {"matter_id": matter_id, "batch_id": batch_id,
                 "stage_label": stage_label, "outcome_label": outcome_label,
                 "reported_only": True, "processed_here": False},
                actor, "ext_processing_report_record")

    def list_processing_reports(self, matter_id, batch_id=None, actor=None):
        """Return processing report records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_processing_report_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_processing_report_read")
            if batch_id is not None:
                self._get("ingest_batch", batch_id, matter_id)
            return self._list("processing_report", matter_id=matter_id,
                              batch_id=batch_id)

    def ingest_batch_view(self, matter_id, batch_id, actor=None):
        """Derived view of an ingest batch. Action: report_read.

        The artifact count, the total recorded byte count, and
        the processing-report count are computed at read from
        the stored records (sums and counts over recorded
        values only); the stored batch record carries none of
        them.
        """
        self._guard_read(actor, "report_read", "ext_ingest_batch_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_ingest_batch_view")
            batch = self._get("ingest_batch", batch_id, matter_id)
            artifacts = self._list("ingest_artifact", matter_id=matter_id,
                                   batch_id=batch_id)
            reports = self._list("processing_report", matter_id=matter_id,
                                 batch_id=batch_id)
            view = dict(batch)
            view["artifact_count"] = len(artifacts)
            view["total_size_bytes"] = sum(a["size_bytes"] for a in artifacts)
            view["processing_report_count"] = len(reports)
            view["derived_at_read"] = True
            return view

    # -- Evidence review (Magnet One) ---------------------------------
    # A review here is a record about a review: an opaque review
    # reference, a target (a core document record or an ingest
    # artifact record in the same matter), and an outcome label
    # recorded verbatim as reported. Nothing is rendered and no
    # content is held (``rendered_here`` / ``content_held`` are
    # False): the review workspace is the fork's product.

    def record_evidence_review(self, matter_id, review_ref, target_kind,
                               target_id, actor, outcome_label=None):
        """Record an evidence review. Action: annotation_write.

        ``target_kind`` is ``document`` (a core document record)
        or ``ingest_artifact`` (an ingest artifact record); the
        target must exist in this matter.
        """
        self._guard(actor, "annotation_write", "ext_evidence_review_record",
                    matter_id)
        _non_empty(review_ref, "review_ref")
        _string_or_none(outcome_label, "outcome_label")
        if target_kind not in REVIEW_TARGET_KINDS:
            raise ValidationError(
                "target_kind must be one of %s"
                % (", ".join(REVIEW_TARGET_KINDS),)
            )
        with self._lock:
            self._matter(actor, matter_id, "ext_evidence_review_record",
                         need_open=True)
            if target_kind == "document":
                self.store.get_document(matter_id, target_id, actor)
            else:
                self._get("ingest_artifact", target_id, matter_id)
            self._check_ref_unique("evidence_review", matter_id, "review_ref",
                                   review_ref, "review_ref")
            return self._create(
                "evidence_review", "evr",
                {"matter_id": matter_id, "review_ref": review_ref,
                 "target_kind": target_kind, "target_id": target_id,
                 "outcome_label": outcome_label, "rendered_here": False,
                 "content_held": False, "status": "recorded"},
                actor, "ext_evidence_review_record")

    def get_evidence_review(self, matter_id, review_id, actor=None):
        """Return one evidence review record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_evidence_review_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_evidence_review_read")
            return self._fetch("evidence_review", review_id, matter_id)

    def list_evidence_reviews(self, matter_id, target_id=None, actor=None):
        """Return evidence review records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_evidence_review_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_evidence_review_read")
            return self._list("evidence_review", matter_id=matter_id,
                              target_id=target_id)

    # -- Chain-of-custody enforcement over evidence (Cellebrite) ------
    # Custody in records form: an artifact registration (an
    # opaque reference, its SHA-256 digest, its byte count, and
    # the holder at registration as reported) and custody
    # transfer records between opaque holder references. This is
    # a custody LEDGER, not custody enforcement
    # (``custody_enforced_here`` is False on every record): the
    # substrate's checksums, verify-by-content, and hash-chained
    # audit are records-side analogues of enforcement, stated as
    # analogues, not equivalents (union spec). An artifact's
    # current holder is derived at read through the seam
    # ``_current_holder``; the stored registration carries no
    # current holder.

    def register_artifact(self, matter_id, artifact_ref, sha256, size_bytes,
                          actor, holder_ref=None):
        """Register a custody artifact as metadata + SHA-256.

        Action: document_write. ``holder_ref`` is the holder at
        registration, as reported (opaque); the artifact's
        content never enters this build.
        """
        self._guard(actor, "document_write", "ext_artifact_register",
                    matter_id)
        _non_empty(artifact_ref, "artifact_ref")
        _sha256(sha256, "sha256")
        _count(size_bytes, "size_bytes")
        _string_or_none(holder_ref, "holder_ref")
        with self._lock:
            self._matter(actor, matter_id, "ext_artifact_register",
                         need_open=True)
            self._check_ref_unique("artifact_registration", matter_id,
                                   "artifact_ref", artifact_ref, "artifact_ref")
            return self._create(
                "artifact_registration", "art",
                {"matter_id": matter_id, "artifact_ref": artifact_ref,
                 "sha256": sha256, "size_bytes": size_bytes,
                 "holder_ref": holder_ref, "content_held": False,
                 "custody_enforced_here": False, "status": "registered"},
                actor, "ext_artifact_register")

    def get_artifact(self, matter_id, artifact_id, actor=None):
        """Return one artifact registration. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_artifact_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_artifact_read")
            return self._fetch("artifact_registration", artifact_id, matter_id)

    def list_artifacts(self, matter_id, actor=None):
        """Return artifact registrations. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_artifact_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_artifact_read")
            return self._list("artifact_registration", matter_id=matter_id)

    def record_custody_transfer(self, matter_id, artifact_id,
                                from_holder_ref, to_holder_ref, actor,
                                transfer_label=None):
        """Record a custody transfer between holder references.

        Action: document_write. Both holders are opaque
        references recorded as reported; recording the transfer
        enforces nothing -- it is the ledger entry an enforcement
        system would be audited against.
        """
        self._guard(actor, "document_write", "ext_custody_transfer_record",
                    matter_id)
        _non_empty(from_holder_ref, "from_holder_ref")
        _non_empty(to_holder_ref, "to_holder_ref")
        _string_or_none(transfer_label, "transfer_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_custody_transfer_record",
                         need_open=True)
            self._get("artifact_registration", artifact_id, matter_id)
            return self._create(
                "custody_transfer", "cus",
                {"matter_id": matter_id, "artifact_id": artifact_id,
                 "from_holder_ref": from_holder_ref,
                 "to_holder_ref": to_holder_ref,
                 "transfer_label": transfer_label,
                 "custody_enforced_here": False},
                actor, "ext_custody_transfer_record")

    def list_custody_transfers(self, matter_id, artifact_id=None, actor=None):
        """Return custody transfer records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_custody_transfer_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_custody_transfer_read")
            if artifact_id is not None:
                self._get("artifact_registration", artifact_id, matter_id)
            return self._list("custody_transfer", matter_id=matter_id,
                              artifact_id=artifact_id)

    @staticmethod
    def _current_holder(transfers, registered_holder_ref):
        """The current holder of an artifact, derived at read.

        The holder named by the latest recorded custody
        transfer, or the holder at registration when no transfer
        has been recorded.

        MUTATION DRILL NOTE: this seam is the single derivation
        point for an artifact's current holder -- the batch's
        fresh negative control mutates it (reading the first
        transfer instead of the latest must not produce the
        canonical holder after two or more transfers).
        """
        if transfers:
            return transfers[-1]["to_holder_ref"]
        return registered_holder_ref

    def artifact_view(self, matter_id, artifact_id, actor=None):
        """Derived view of an artifact registration. Action: report_read.

        The transfer count and current holder are computed at
        read from the stored transfer records by the seam
        ``_current_holder``; nothing derived is written back
        onto the registration record.
        """
        self._guard_read(actor, "report_read", "ext_artifact_view", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_artifact_view")
            artifact = self._get("artifact_registration", artifact_id,
                                 matter_id)
            transfers = self._list("custody_transfer", matter_id=matter_id,
                                   artifact_id=artifact_id)
            view = dict(artifact)
            view["transfer_count"] = len(transfers)
            view["current_holder_ref"] = self._current_holder(
                transfers, artifact["holder_ref"])
            view["derived_at_read"] = True
            return view

    def verify_artifact(self, matter_id, artifact_id, content, actor=None):
        """Verify caller-supplied bytes against an artifact's digest.

        Action: matter_read. The records-side integrity analogue
        of custody checking, mirroring the core's
        verify-by-content: the bytes are hashed and compared;
        nothing is stored and nothing is enforced.
        """
        self._guard_read(actor, "matter_read", "ext_artifact_verify",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_artifact_verify")
            artifact = self._get("artifact_registration", artifact_id,
                                 matter_id)
            if isinstance(content, str):
                content = content.encode("utf-8")
            if not isinstance(content, (bytes, bytearray)):
                raise ValidationError("content must be bytes")
            computed = hashlib.sha256(bytes(content)).hexdigest()
            return {
                "artifact_id": artifact_id,
                "sha256": artifact["sha256"],
                "computed_sha256": computed,
                "matches": computed == artifact["sha256"],
            }

    # -- Information sharing / collaboration over evidence (both) -----
    # Sharing in records form (the Communication adjudicated
    # form): a share record binds a target -- a core document
    # record, an artifact registration, or a custody transfer
    # record in the same matter -- to an opaque recipient
    # reference, and receipts record delivery outcomes verbatim
    # as reported. Every record carries ``reference_transport:
    # True`` and ``transmitted_here: False`` (and the share
    # record ``shared_here: False``): this build shares nothing;
    # the records describe shares effected on systems owned
    # elsewhere, and no content moves or is held here.

    def record_share(self, matter_id, share_ref, target_kind, target_id,
                     recipient_ref, actor, access_label=None):
        """Record an information share. Action: annotation_write.

        ``target_kind`` is ``document`` (a core document
        record), ``artifact`` (an artifact registration), or
        ``custody_transfer`` (a custody transfer record); the
        target must exist in this matter. ``recipient_ref`` is
        an opaque reference to the recipient system or party --
        never a name or an identifier of a person.
        """
        self._guard(actor, "annotation_write", "ext_share_record", matter_id)
        _non_empty(share_ref, "share_ref")
        _non_empty(recipient_ref, "recipient_ref")
        _string_or_none(access_label, "access_label")
        if target_kind not in SHARE_TARGET_KINDS:
            raise ValidationError(
                "target_kind must be one of %s"
                % (", ".join(SHARE_TARGET_KINDS),)
            )
        with self._lock:
            self._matter(actor, matter_id, "ext_share_record", need_open=True)
            if target_kind == "document":
                self.store.get_document(matter_id, target_id, actor)
            elif target_kind == "artifact":
                self._get("artifact_registration", target_id, matter_id)
            else:
                self._get("custody_transfer", target_id, matter_id)
            self._check_ref_unique("share_record", matter_id, "share_ref",
                                   share_ref, "share_ref")
            return self._create(
                "share_record", "shr",
                {"matter_id": matter_id, "share_ref": share_ref,
                 "target_kind": target_kind, "target_id": target_id,
                 "recipient_ref": recipient_ref,
                 "access_label": access_label, "reference_transport": True,
                 "transmitted_here": False, "shared_here": False,
                 "content_held": False, "status": "recorded"},
                actor, "ext_share_record")

    def get_share(self, matter_id, share_id, actor=None):
        """Return one share record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_share_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_share_read")
            return self._fetch("share_record", share_id, matter_id)

    def list_shares(self, matter_id, target_id=None, actor=None):
        """Return share records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_share_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_share_read")
            return self._list("share_record", matter_id=matter_id,
                              target_id=target_id)

    def record_share_receipt(self, matter_id, share_id, outcome, actor):
        """Record a share delivery outcome as reported, verbatim.

        Action: annotation_write. The outcome is the receiving
        system's report; nothing was transmitted here.
        """
        self._guard(actor, "annotation_write", "ext_share_receipt_record",
                    matter_id)
        _non_empty(outcome, "outcome")
        with self._lock:
            self._matter(actor, matter_id, "ext_share_receipt_record",
                         need_open=True)
            self._get("share_record", share_id, matter_id)
            return self._create(
                "share_receipt", "shp",
                {"matter_id": matter_id, "share_id": share_id,
                 "outcome": outcome, "reference_transport": True,
                 "transmitted_here": False},
                actor, "ext_share_receipt_record")

    def list_share_receipts(self, matter_id, share_id=None, actor=None):
        """Return share receipt records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_share_receipt_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_share_receipt_read")
            if share_id is not None:
                self._get("share_record", share_id, matter_id)
            return self._list("share_receipt", matter_id=matter_id,
                              share_id=share_id)

    def share_view(self, matter_id, share_id, actor=None):
        """Derived view of a share record. Action: report_read.

        The receipt count and the latest reported outcome are
        computed at read from the stored receipt records; the
        stored share record carries neither.
        """
        self._guard_read(actor, "report_read", "ext_share_view", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_share_view")
            share = self._get("share_record", share_id, matter_id)
            receipts = self._list("share_receipt", matter_id=matter_id,
                                  share_id=share_id)
            view = dict(share)
            view["receipt_count"] = len(receipts)
            view["latest_outcome"] = (
                receipts[-1]["outcome"] if receipts else None)
            view["derived_at_read"] = True
            return view

    # -- Forensic reporting (Cellebrite) ------------------------------
    # A forensic report here is a registry record: an opaque
    # reference and the report's SHA-256 digest. Reports are
    # generated by the forks' platforms elsewhere; this build
    # generates nothing (``generated_here`` is False) and holds
    # no report content. The report view derives the matter's
    # forensic-registry counts at read -- counts over this
    # extension surface's own records, beyond the core's
    # counts-only registry reporting over core records.

    def register_forensic_report(self, matter_id, report_ref, actor,
                                 report_sha256=None):
        """Register a forensic report record. Action: document_write."""
        self._guard(actor, "document_write", "ext_forensic_report_register",
                    matter_id)
        _non_empty(report_ref, "report_ref")
        _sha256_or_none(report_sha256, "report_sha256")
        with self._lock:
            self._matter(actor, matter_id, "ext_forensic_report_register",
                         need_open=True)
            self._check_ref_unique("forensic_report", matter_id, "report_ref",
                                   report_ref, "report_ref")
            return self._create(
                "forensic_report", "frp",
                {"matter_id": matter_id, "report_ref": report_ref,
                 "report_sha256": report_sha256, "generated_here": False,
                 "content_held": False, "status": "registered"},
                actor, "ext_forensic_report_register")

    def get_forensic_report(self, matter_id, report_id, actor=None):
        """Return one forensic report record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_forensic_report_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_forensic_report_read")
            return self._fetch("forensic_report", report_id, matter_id)

    def list_forensic_reports(self, matter_id, actor=None):
        """Return forensic report records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_forensic_report_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_forensic_report_read")
            return self._list("forensic_report", matter_id=matter_id)

    def forensic_report_view(self, matter_id, report_id, actor=None):
        """Derived view of a forensic report. Action: report_read.

        The matter's forensic-registry counts are computed at
        read from the extension records themselves, so the
        figures track registry state; the stored report record
        carries no figures.
        """
        self._guard_read(actor, "report_read", "ext_forensic_report_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_forensic_report_view")
            report = self._get("forensic_report", report_id, matter_id)
            counts = {}
            for kind, key in (
                ("artifact_registration", "artifact_registrations"),
                ("custody_transfer", "custody_transfers"),
                ("ingest_batch", "ingest_batches"),
                ("ingest_artifact", "ingest_artifacts"),
                ("analysis_record", "analysis_records"),
                ("evidence_review", "evidence_reviews"),
                ("share_record", "share_records"),
            ):
                counts[key] = len(self._list(kind, matter_id=matter_id))
            view = dict(report)
            view["counts_by_kind"] = counts
            view["derived_at_read"] = True
            return view
