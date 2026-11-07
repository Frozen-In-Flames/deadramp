"""Final GAPS batch extensions for Law Enforcement L2.

Clean-room, standard-library-only records extensions for the 6
open Extended entries of this group's union spec -- the legal
research platform long tail shared by both siblings (Lexis+ for
Government; Thomson Reuters Legal Research). Per-entry
dispositions and the not-covered list are in ``BATCH.md`` in the
group directory: 4 entries built as records in-substrate, 2
shipped as labeled reference implementations (corpus search &
relevance engines; AI/ML research assistance), exactly as
drafted in the batch inventory.

Design, following the core's doctrines:

- This module is a wrapper around :class:`LawEnfStore`; the
  core modules are untouched (byte-identical). Matter
  existence, membership, and lifecycle state are always read
  through the core store's public API, never re-implemented.
- **The hard privacy rule binds the whole surface.** Every
  record is keyed by an opaque caller-supplied ``*_ref`` string
  or a core record id, and holds metadata and SHA-256 digests
  only. No legal content, document content, headnote text,
  query text, or note text is ever held: queries and headnotes
  are named by their SHA-256 digest, exactly as the core's
  saved-search and annotation records name theirs. There is no
  parameter anywhere in this module that could accept content,
  a query's or note's text, a prompt, or a person's identifier
  -- the batch tests pin that by signature (``TypeError``).
- **Records of the platforms' work, never the platforms'
  engines.** The corpora themselves, the citation-validation
  engines, the editorial systems, and the content operations
  are the vendors' products; what this substrate builds is the
  records surface those functions presuppose -- corpus
  registrations and their maintenance / license records,
  validation requests and their reported determinations,
  enhancement records over registered sources, and content
  operation records over registered documents. Every record
  carries its boundary label (``content_held`` /
  ``determined_here`` / ``assigned_here`` / ``enriched_here`` /
  ``stored_here`` / ``rendered_here`` / ``redacted_here`` are
  False). Treatments, class labels, stage labels, and outcome
  labels are recorded **verbatim** as reported -- the core's
  citation discipline: never normalized, never scored, never
  aggregated into a computed status.
- **The two engine entries ship as labeled reference
  implementations.** Corpus search runs over content this
  substrate never holds, and AI/ML assistance is a running
  model: both close as request / run records plus reported
  outcome records, every record carrying
  ``reference_stub: True`` and ``status:
  "recorded_reference_only"``.
- RBAC goes through :mod:`lawenf.access` exactly as the core
  enforces it: the extension maps each operation onto an
  existing core action (the core action set is fixed -- see
  the mapping in ``BATCH.md``), checks it *before* any state
  change or id allocation for actors that carry a role, and
  records denied attempts on the core audit log as
  ``ext_<action>:denied``. Matter membership -- the core's
  second boundary -- is enforced through the core store on
  every operation, and writes additionally require an open
  matter, mirroring the core's ``need_open`` discipline.
- Derived values are derived at read and never stored: view
  counts and latest reported labels. Stored records carry no
  derived key; tests pin that. The latest-label derivation
  lives at a single named seam (``_latest_label``): the
  batch's fresh negative control.
- The extension surface is in-process only: the founding HTTP
  service layer is unchanged and does not expose extension
  operations.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


def _count_or_none(value, what):
    if value is not None:
        _count(value, what)
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

        Mirrors the core store: actors carrying a role are
        checked against the core permission matrix before
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
        """Commit a record, auditing before the commit.

        The audit entry is written to the core audit log first;
        only then is the record inserted and the id counter
        advanced -- a failed operation consumes no id and
        changes nothing, exactly as in the core store.
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

    @staticmethod
    def _latest_label(records, key):
        """The latest-label seam: the current reported label of a
        record stream is its most recently recorded label.

        Every derived view that reports a "latest" label goes
        through this single point. MUTATION DRILL NOTE: this seam
        is the batch unit's fresh negative-control target --
        reading the earliest record instead would silently
        misstate every current label while leaving the stored
        record shapes intact (see tests/README.md).
        """
        if not records:
            return None
        return records[-1][key]

    # -- The legal corpora themselves ---------------------------------
    # Built as the corpus registry surface: corpus registrations,
    # links from registered sources to the corpus they are drawn
    # from, editorial-maintenance event records, and license
    # records. The content databases themselves are the vendors'
    # product and are never held here -- the privacy rule admits
    # no content in any field shape, and every record carries
    # ``content_held: False``.

    def register_corpus(self, matter_id, corpus_ref, coverage_label, actor):
        """Register a corpus collection record. Action: source_write."""
        self._guard(actor, "source_write", "ext_corpus_register", matter_id)
        _non_empty(corpus_ref, "corpus_ref")
        _non_empty(coverage_label, "coverage_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_register",
                         need_open=True)
            self._check_ref_unique("corpus", matter_id, "corpus_ref",
                                   corpus_ref, "corpus_ref")
            return self._create(
                "corpus", "cor",
                {"matter_id": matter_id, "corpus_ref": corpus_ref,
                 "coverage_label": coverage_label, "content_held": False},
                actor, "ext_corpus_register")

    def get_corpus(self, matter_id, corpus_id, actor=None):
        """Return one corpus record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_corpus_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_read")
            return self._fetch("corpus", corpus_id, matter_id)

    def list_corpora(self, matter_id, actor=None):
        """List corpus records in a matter. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_corpus_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_read")
            return self._list("corpus", matter_id=matter_id)

    def link_corpus_source(self, matter_id, corpus_id, source_id, actor):
        """Link a core source record to a corpus. Action: source_write."""
        self._guard(actor, "source_write", "ext_corpus_link", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_link", need_open=True)
            self._get("corpus", corpus_id, matter_id)
            # The core store enforces existence (and matter scope).
            self.store.get_source(matter_id, source_id, actor)
            return self._create(
                "corpus_source_link", "csl",
                {"matter_id": matter_id, "corpus_id": corpus_id,
                 "source_id": source_id, "content_held": False},
                actor, "ext_corpus_link")

    def list_corpus_links(self, matter_id, corpus_id, actor=None):
        """List corpus-source links for a corpus. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_corpus_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_read")
            self._get("corpus", corpus_id, matter_id)
            return self._list("corpus_source_link", matter_id=matter_id,
                              corpus_id=corpus_id)

    def record_corpus_maintenance(self, matter_id, corpus_id, event_label,
                                  actor):
        """Record an editorial-maintenance event, verbatim.

        Action: source_write."""
        self._guard(actor, "source_write", "ext_corpus_maintenance",
                    matter_id)
        _non_empty(event_label, "event_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_maintenance",
                         need_open=True)
            self._get("corpus", corpus_id, matter_id)
            return self._create(
                "corpus_maintenance", "cmn",
                {"matter_id": matter_id, "corpus_id": corpus_id,
                 "event_label": event_label, "maintained_here": False},
                actor, "ext_corpus_maintenance")

    def list_corpus_maintenance(self, matter_id, corpus_id, actor=None):
        """List maintenance records for a corpus. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_corpus_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_read")
            self._get("corpus", corpus_id, matter_id)
            return self._list("corpus_maintenance", matter_id=matter_id,
                              corpus_id=corpus_id)

    def record_corpus_license(self, matter_id, corpus_id, license_label,
                              actor):
        """Record a corpus license, label verbatim. Action: source_write."""
        self._guard(actor, "source_write", "ext_corpus_license", matter_id)
        _non_empty(license_label, "license_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_license",
                         need_open=True)
            self._get("corpus", corpus_id, matter_id)
            return self._create(
                "corpus_license", "lic",
                {"matter_id": matter_id, "corpus_id": corpus_id,
                 "license_label": license_label, "content_held": False},
                actor, "ext_corpus_license")

    def list_corpus_licenses(self, matter_id, corpus_id, actor=None):
        """List license records for a corpus. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_corpus_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_read")
            self._get("corpus", corpus_id, matter_id)
            return self._list("corpus_license", matter_id=matter_id,
                              corpus_id=corpus_id)

    def corpus_view(self, matter_id, corpus_id, actor=None):
        """Derived corpus view: counts and the latest maintenance
        label, computed at read. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_corpus_view", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_view")
            corpus = self._fetch("corpus", corpus_id, matter_id)
            maintenance = self._list("corpus_maintenance",
                                     matter_id=matter_id, corpus_id=corpus_id)
            return {
                "matter_id": matter_id,
                "corpus_id": corpus_id,
                "corpus_ref": corpus["corpus_ref"],
                "derived": True,
                "linked_source_count": len(self._list(
                    "corpus_source_link", matter_id=matter_id,
                    corpus_id=corpus_id)),
                "maintenance_count": len(maintenance),
                "license_count": len(self._list(
                    "corpus_license", matter_id=matter_id,
                    corpus_id=corpus_id)),
                "latest_maintenance_label": self._latest_label(
                    maintenance, "event_label"),
            }

    # -- Citation-validation engines ----------------------------------
    # Built as the validation request registry: a request bound to
    # a registered source, and determination records holding the
    # treatment exactly as reported by whatever external editorial
    # system the embedding organization uses. No treatment is
    # determined here -- the entry's own bound, carried on every
    # record as ``determined_here: False`` (the core's citation
    # discipline: treatments are records, never computations).

    def request_citation_validation(self, matter_id, validation_ref, actor,
                                    source_id=None):
        """Record a citation-validation request. Action: citation_write."""
        self._guard(actor, "citation_write", "ext_validation_request",
                    matter_id)
        _non_empty(validation_ref, "validation_ref")
        with self._lock:
            self._matter(actor, matter_id, "ext_validation_request",
                         need_open=True)
            if source_id is not None:
                self.store.get_source(matter_id, source_id, actor)
            self._check_ref_unique("validation_request", matter_id,
                                   "validation_ref", validation_ref,
                                   "validation_ref")
            return self._create(
                "validation_request", "val",
                {"matter_id": matter_id, "validation_ref": validation_ref,
                 "source_id": source_id, "determined_here": False},
                actor, "ext_validation_request")

    def get_validation_request(self, matter_id, validation_id, actor=None):
        """Return one validation request. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_validation_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_validation_read")
            return self._fetch("validation_request", validation_id, matter_id)

    def list_validation_requests(self, matter_id, actor=None):
        """List validation requests in a matter. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_validation_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_validation_read")
            return self._list("validation_request", matter_id=matter_id)

    def record_validation_determination(self, matter_id, validation_id,
                                        treatment, actor, engine_label=None):
        """Record a reported determination; the treatment is stored
        verbatim and determined elsewhere. Action: citation_write."""
        self._guard(actor, "citation_write", "ext_validation_determination",
                    matter_id)
        _non_empty(treatment, "treatment")
        _string_or_none(engine_label, "engine_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_validation_determination",
                         need_open=True)
            self._get("validation_request", validation_id, matter_id)
            return self._create(
                "validation_determination", "vdt",
                {"matter_id": matter_id, "validation_id": validation_id,
                 "treatment": treatment, "engine_label": engine_label,
                 "determined_here": False},
                actor, "ext_validation_determination")

    def list_validation_determinations(self, matter_id, validation_id,
                                       actor=None):
        """List determinations for a request. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_validation_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_validation_read")
            self._get("validation_request", validation_id, matter_id)
            return self._list("validation_determination",
                              matter_id=matter_id, validation_id=validation_id)

    def validation_view(self, matter_id, validation_id, actor=None):
        """Derived validation view: determination count and the
        latest reported treatment. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_validation_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_validation_view")
            request = self._fetch("validation_request", validation_id,
                                  matter_id)
            determinations = self._list("validation_determination",
                                        matter_id=matter_id,
                                        validation_id=validation_id)
            return {
                "matter_id": matter_id,
                "validation_id": validation_id,
                "validation_ref": request["validation_ref"],
                "derived": True,
                "determination_count": len(determinations),
                "latest_treatment": self._latest_label(
                    determinations, "treatment"),
            }

    # -- Editorial enhancement systems --------------------------------
    # Built as enhancement records over registered sources:
    # headnote records naming the headnote by its SHA-256 digest
    # (the core's annotation discipline -- the text is never
    # held), taxonomy assignment records holding the class label
    # verbatim as reported, and enrichment stage report records.
    # Nothing is enhanced here: ``assigned_here`` /
    # ``enriched_here`` are False on every record.

    def record_headnote(self, matter_id, headnote_ref, source_id,
                        note_sha256, actor):
        """Record a headnote by digest over a source.

        Action: annotation_write."""
        self._guard(actor, "annotation_write", "ext_headnote_record",
                    matter_id)
        _non_empty(headnote_ref, "headnote_ref")
        _sha256(note_sha256, "note_sha256")
        with self._lock:
            self._matter(actor, matter_id, "ext_headnote_record",
                         need_open=True)
            self.store.get_source(matter_id, source_id, actor)
            self._check_ref_unique("headnote", matter_id, "headnote_ref",
                                   headnote_ref, "headnote_ref")
            return self._create(
                "headnote", "hed",
                {"matter_id": matter_id, "headnote_ref": headnote_ref,
                 "source_id": source_id, "note_sha256": note_sha256,
                 "content_held": False},
                actor, "ext_headnote_record")

    def list_headnotes(self, matter_id, source_id, actor=None):
        """List headnote records for a source. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_headnote_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_headnote_read")
            self.store.get_source(matter_id, source_id, actor)
            return self._list("headnote", matter_id=matter_id,
                              source_id=source_id)

    def record_taxonomy_assignment(self, matter_id, assignment_ref,
                                   source_id, class_label, actor):
        """Record a taxonomy assignment; the class label is stored
        verbatim as reported. Action: annotation_write."""
        self._guard(actor, "annotation_write", "ext_taxonomy_assignment",
                    matter_id)
        _non_empty(assignment_ref, "assignment_ref")
        _non_empty(class_label, "class_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_taxonomy_assignment",
                         need_open=True)
            self.store.get_source(matter_id, source_id, actor)
            self._check_ref_unique("taxonomy_assignment", matter_id,
                                   "assignment_ref", assignment_ref,
                                   "assignment_ref")
            return self._create(
                "taxonomy_assignment", "txa",
                {"matter_id": matter_id, "assignment_ref": assignment_ref,
                 "source_id": source_id, "class_label": class_label,
                 "assigned_here": False},
                actor, "ext_taxonomy_assignment")

    def list_taxonomy_assignments(self, matter_id, source_id, actor=None):
        """List assignments for a source. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_taxonomy_assignment_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_taxonomy_assignment_read")
            self.store.get_source(matter_id, source_id, actor)
            return self._list("taxonomy_assignment", matter_id=matter_id,
                              source_id=source_id)

    def record_enrichment_report(self, matter_id, report_ref, source_id,
                                 stage_label, outcome_label, actor):
        """Record an enrichment pipeline stage report, labels
        verbatim. Action: annotation_write."""
        self._guard(actor, "annotation_write", "ext_enrichment_report",
                    matter_id)
        _non_empty(report_ref, "report_ref")
        _non_empty(stage_label, "stage_label")
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_enrichment_report",
                         need_open=True)
            self.store.get_source(matter_id, source_id, actor)
            self._check_ref_unique("enrichment_report", matter_id,
                                   "report_ref", report_ref, "report_ref")
            return self._create(
                "enrichment_report", "enr",
                {"matter_id": matter_id, "report_ref": report_ref,
                 "source_id": source_id, "stage_label": stage_label,
                 "outcome_label": outcome_label, "enriched_here": False},
                actor, "ext_enrichment_report")

    def list_enrichment_reports(self, matter_id, source_id, actor=None):
        """List enrichment reports for a source. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_enrichment_report_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_enrichment_report_read")
            self.store.get_source(matter_id, source_id, actor)
            return self._list("enrichment_report", matter_id=matter_id,
                              source_id=source_id)

    def enhancement_view(self, matter_id, source_id, actor=None):
        """Derived enhancement view over a source: counts per kind
        and the latest reported class label. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_enhancement_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_enhancement_view")
            self.store.get_source(matter_id, source_id, actor)
            assignments = self._list("taxonomy_assignment",
                                     matter_id=matter_id, source_id=source_id)
            return {
                "matter_id": matter_id,
                "source_id": source_id,
                "derived": True,
                "headnote_count": len(self._list(
                    "headnote", matter_id=matter_id, source_id=source_id)),
                "assignment_count": len(assignments),
                "enrichment_count": len(self._list(
                    "enrichment_report", matter_id=matter_id,
                    source_id=source_id)),
                "latest_class_label": self._latest_label(
                    assignments, "class_label"),
            }

    # -- Corpus search & relevance engines ----------------------------
    # Labeled reference implementation, as drafted (stub-engine):
    # full-text indexing and ranking run over the legal corpus,
    # which this substrate never holds. The records hold a search
    # run -- its query named by SHA-256 digest only, exactly as
    # the core's saved-search records name theirs; there is no
    # parameter that could accept query text -- and its reported
    # outcome. Every record carries ``reference_stub: True``,
    # ``searched_here: False``, and ``ranked_here: False``.

    def record_corpus_search_run(self, matter_id, run_ref, query_sha256,
                                 actor, engine_label=None):
        """Record a corpus search run (reference). Action: search_write."""
        self._guard(actor, "search_write", "ext_corpus_search_run",
                    matter_id)
        _non_empty(run_ref, "run_ref")
        _sha256(query_sha256, "query_sha256")
        _string_or_none(engine_label, "engine_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_search_run",
                         need_open=True)
            self._check_ref_unique("corpus_search_run", matter_id, "run_ref",
                                   run_ref, "run_ref")
            return self._create(
                "corpus_search_run", "csr",
                {"matter_id": matter_id, "run_ref": run_ref,
                 "query_sha256": query_sha256, "engine_label": engine_label,
                 "reference_stub": True, "searched_here": False,
                 "ranked_here": False, "status": "recorded_reference_only"},
                actor, "ext_corpus_search_run")

    def get_corpus_search_run(self, matter_id, run_id, actor=None):
        """Return one corpus search run. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_corpus_search_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_search_read")
            return self._fetch("corpus_search_run", run_id, matter_id)

    def list_corpus_search_runs(self, matter_id, actor=None):
        """List corpus search runs in a matter. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_corpus_search_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_search_read")
            return self._list("corpus_search_run", matter_id=matter_id)

    def record_corpus_search_outcome(self, matter_id, run_id, outcome_label,
                                     actor, result_count=None):
        """Record a reported corpus search outcome (reference).

        Action: search_write."""
        self._guard(actor, "search_write", "ext_corpus_search_outcome",
                    matter_id)
        _non_empty(outcome_label, "outcome_label")
        _count_or_none(result_count, "result_count")
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_search_outcome",
                         need_open=True)
            self._get("corpus_search_run", run_id, matter_id)
            return self._create(
                "corpus_search_outcome", "cso",
                {"matter_id": matter_id, "run_id": run_id,
                 "outcome_label": outcome_label,
                 "result_count": result_count, "reference_stub": True},
                actor, "ext_corpus_search_outcome")

    def list_corpus_search_outcomes(self, matter_id, run_id, actor=None):
        """List outcomes for a run. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_corpus_search_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_search_read")
            self._get("corpus_search_run", run_id, matter_id)
            return self._list("corpus_search_outcome", matter_id=matter_id,
                              run_id=run_id)

    def corpus_search_view(self, matter_id, run_id, actor=None):
        """Derived run view: outcome count and latest outcome.

        Action: report_read."""
        self._guard_read(actor, "report_read", "ext_corpus_search_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_corpus_search_view")
            run = self._fetch("corpus_search_run", run_id, matter_id)
            outcomes = self._list("corpus_search_outcome",
                                  matter_id=matter_id, run_id=run_id)
            return {
                "matter_id": matter_id,
                "run_id": run_id,
                "run_ref": run["run_ref"],
                "derived": True,
                "outcome_count": len(outcomes),
                "latest_outcome": self._latest_label(
                    outcomes, "outcome_label"),
            }

    # -- AI/ML research assistance ------------------------------------
    # Labeled reference implementation, as drafted (stub-engine;
    # 0 claims in the two descriptions -- named for union
    # completeness). Assistance is a running model's work; the
    # records hold a request -- its prompt named by an optional
    # SHA-256 digest only; there is no parameter that could
    # accept prompt text -- and its reported outcome, the result
    # named by an opaque reference. Every record carries
    # ``reference_stub: True`` and ``inference_here: False``.

    def record_assistance_request(self, matter_id, request_ref, actor,
                                  model_label=None, prompt_sha256=None):
        """Record an assistance request (reference). Action: search_write."""
        self._guard(actor, "search_write", "ext_assistance_request",
                    matter_id)
        _non_empty(request_ref, "request_ref")
        _string_or_none(model_label, "model_label")
        _sha256_or_none(prompt_sha256, "prompt_sha256")
        with self._lock:
            self._matter(actor, matter_id, "ext_assistance_request",
                         need_open=True)
            self._check_ref_unique("assistance_request", matter_id,
                                   "request_ref", request_ref, "request_ref")
            return self._create(
                "assistance_request", "asr",
                {"matter_id": matter_id, "request_ref": request_ref,
                 "model_label": model_label, "prompt_sha256": prompt_sha256,
                 "reference_stub": True, "inference_here": False,
                 "assisted_here": False, "status": "recorded_reference_only"},
                actor, "ext_assistance_request")

    def get_assistance_request(self, matter_id, request_id, actor=None):
        """Return one assistance request. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_assistance_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_assistance_read")
            return self._fetch("assistance_request", request_id, matter_id)

    def list_assistance_requests(self, matter_id, actor=None):
        """List assistance requests in a matter. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_assistance_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_assistance_read")
            return self._list("assistance_request", matter_id=matter_id)

    def record_assistance_outcome(self, matter_id, request_id, outcome_label,
                                  actor, result_ref=None):
        """Record a reported assistance outcome (reference).

        Action: search_write."""
        self._guard(actor, "search_write", "ext_assistance_outcome",
                    matter_id)
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(result_ref, "result_ref")
        with self._lock:
            self._matter(actor, matter_id, "ext_assistance_outcome",
                         need_open=True)
            self._get("assistance_request", request_id, matter_id)
            return self._create(
                "assistance_outcome", "aso",
                {"matter_id": matter_id, "request_id": request_id,
                 "outcome_label": outcome_label, "result_ref": result_ref,
                 "reference_stub": True, "output_held": False},
                actor, "ext_assistance_outcome")

    def list_assistance_outcomes(self, matter_id, request_id, actor=None):
        """List outcomes for a request. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_assistance_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_assistance_read")
            self._get("assistance_request", request_id, matter_id)
            return self._list("assistance_outcome", matter_id=matter_id,
                              request_id=request_id)

    def assistance_view(self, matter_id, request_id, actor=None):
        """Derived assistance view: outcome count and latest
        outcome. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_assistance_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_assistance_view")
            request = self._fetch("assistance_request", request_id, matter_id)
            outcomes = self._list("assistance_outcome", matter_id=matter_id,
                                  request_id=request_id)
            return {
                "matter_id": matter_id,
                "request_id": request_id,
                "request_ref": request["request_ref"],
                "derived": True,
                "outcome_count": len(outcomes),
                "latest_outcome": self._latest_label(
                    outcomes, "outcome_label"),
            }

    # -- Document content storage, rendering & redaction --------------
    # Built as content operation records over core document
    # records, under the privacy rule the entry itself states:
    # the registry holds metadata + checksums only, so content
    # storage is a deposit record naming an opaque external
    # storage reference (``stored_here: False``), rendering is a
    # render record naming its output by digest, and redaction
    # is a redaction record with its outcome verbatim and its
    # output named by reference + digest. No parameter can
    # accept document content; recording an operation never
    # changes the core document record (pinned by test).

    def record_content_deposit(self, matter_id, deposit_ref, document_id,
                               storage_ref, actor):
        """Record a content deposit elsewhere. Action: document_write."""
        self._guard(actor, "document_write", "ext_content_deposit",
                    matter_id)
        _non_empty(deposit_ref, "deposit_ref")
        _non_empty(storage_ref, "storage_ref")
        with self._lock:
            self._matter(actor, matter_id, "ext_content_deposit",
                         need_open=True)
            self.store.get_document(matter_id, document_id, actor)
            self._check_ref_unique("content_deposit", matter_id,
                                   "deposit_ref", deposit_ref, "deposit_ref")
            return self._create(
                "content_deposit", "dep",
                {"matter_id": matter_id, "deposit_ref": deposit_ref,
                 "document_id": document_id, "storage_ref": storage_ref,
                 "stored_here": False, "content_held": False},
                actor, "ext_content_deposit")

    def list_content_deposits(self, matter_id, document_id, actor=None):
        """List deposits for a document. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_content_deposit_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_content_deposit_read")
            self.store.get_document(matter_id, document_id, actor)
            return self._list("content_deposit", matter_id=matter_id,
                              document_id=document_id)

    def record_render(self, matter_id, render_ref, document_id, format_label,
                      actor, output_sha256=None):
        """Record a rendering performed elsewhere; the output is
        named by digest. Action: document_write."""
        self._guard(actor, "document_write", "ext_render_record", matter_id)
        _non_empty(render_ref, "render_ref")
        _non_empty(format_label, "format_label")
        _sha256_or_none(output_sha256, "output_sha256")
        with self._lock:
            self._matter(actor, matter_id, "ext_render_record",
                         need_open=True)
            self.store.get_document(matter_id, document_id, actor)
            self._check_ref_unique("render_record", matter_id, "render_ref",
                                   render_ref, "render_ref")
            return self._create(
                "render_record", "ren",
                {"matter_id": matter_id, "render_ref": render_ref,
                 "document_id": document_id, "format_label": format_label,
                 "output_sha256": output_sha256, "rendered_here": False,
                 "content_held": False},
                actor, "ext_render_record")

    def list_render_records(self, matter_id, document_id, actor=None):
        """List render records for a document. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_render_record_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_render_record_read")
            self.store.get_document(matter_id, document_id, actor)
            return self._list("render_record", matter_id=matter_id,
                              document_id=document_id)

    def record_redaction(self, matter_id, redaction_ref, document_id,
                         outcome_label, actor, output_ref=None,
                         output_sha256=None):
        """Record a redaction performed elsewhere; outcome verbatim,
        output named by reference + digest. Action: document_write."""
        self._guard(actor, "document_write", "ext_redaction_record",
                    matter_id)
        _non_empty(redaction_ref, "redaction_ref")
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(output_ref, "output_ref")
        _sha256_or_none(output_sha256, "output_sha256")
        with self._lock:
            self._matter(actor, matter_id, "ext_redaction_record",
                         need_open=True)
            self.store.get_document(matter_id, document_id, actor)
            self._check_ref_unique("redaction_record", matter_id,
                                   "redaction_ref", redaction_ref,
                                   "redaction_ref")
            return self._create(
                "redaction_record", "red",
                {"matter_id": matter_id, "redaction_ref": redaction_ref,
                 "document_id": document_id, "outcome_label": outcome_label,
                 "output_ref": output_ref, "output_sha256": output_sha256,
                 "redacted_here": False, "content_held": False},
                actor, "ext_redaction_record")

    def list_redaction_records(self, matter_id, document_id, actor=None):
        """List redaction records for a document. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_redaction_record_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_redaction_record_read")
            self.store.get_document(matter_id, document_id, actor)
            return self._list("redaction_record", matter_id=matter_id,
                              document_id=document_id)

    def document_operations_view(self, matter_id, document_id, actor=None):
        """Derived operations view over a document: counts per kind
        and the latest redaction outcome. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_document_operations_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_document_operations_view")
            self.store.get_document(matter_id, document_id, actor)
            redactions = self._list("redaction_record", matter_id=matter_id,
                                    document_id=document_id)
            return {
                "matter_id": matter_id,
                "document_id": document_id,
                "derived": True,
                "deposit_count": len(self._list(
                    "content_deposit", matter_id=matter_id,
                    document_id=document_id)),
                "render_count": len(self._list(
                    "render_record", matter_id=matter_id,
                    document_id=document_id)),
                "redaction_count": len(redactions),
                "latest_redaction_outcome": self._latest_label(
                    redactions, "outcome_label"),
            }
