"""Final GAPS batch extensions — Group 24 (CMS L1).

Records-form implementations and labeled reference implementations
for the eight open entries of this group's union spec, built over
the founding CMS substrate in :mod:`cms.store`. This module is the
only code the batch adds; every core module is unchanged.

This is the project's thinnest-evidence group: applying Group 20's
taxonomy verbatim, the two fork descriptions tag exactly one claim
in the whole group, and several entries below are families carried
from the Group 20 (CMS L2) union at 0 claims here. Their forms are
carried from the CMS L2 and CMS untiered batch units' adjudicated
records forms, mirrored at this tier — they are not claimed from
this group's evidence (see ``../BATCH.md``). The baseline framing
is this group's own: the Low baseline, audit on the FedRAMP Low
side only, and the Moderate selection SI-7 is not claimed at this
tier (asset checksums remain an implementation integrity
property, exactly as the union spec states).

Honesty labels, per family:

- **Library ILS vertical** (this group's dominant vertical) is
  this group's own records form over its own substrate —
  circulation-style loan records over opaque patron and item
  references (recorded state events; current state derived at
  read time), acquisition order records holding integer-cent
  amounts as data and never transmitted
  (``transmitted_here: False``), interlibrary-loan request
  records with partner-reported outcomes recorded verbatim
  (``fulfilled_here: False`` — fulfillment is the partner
  library's system), collection records, knowledgebase article
  records in the article-revisions form (bodies held as data and
  versioned; nothing is published or rendered here), access
  proxying as configuration records (``proxied_here: False``),
  digital collection records as metadata plus SHA-256 digests
  (bytes are never held), and union-catalog contribution /
  holding records (``network_here: False`` — the union catalog
  network is other libraries' systems). MARC21-shaped cataloging
  field records are held as data and never parsed. Discovery
  stays the core's literal substring search over registry
  metadata. **Boundary, stated plainly:** a dedicated Library
  Systems category exists elsewhere in this repo
  (``groups/library-systems-l1``); this entry closes as THIS
  group's vertical records form and imports nothing from that
  group.
- **Mobile application delivery** is application and release
  *definition records* plus reported distribution outcome
  records. No application binary is held and nothing is
  delivered here (``delivered_here: False``).
- **Templates, fragments & editor configurations** are definition
  records. A template body is held as data and versioned;
  placeholder names are derived at read time by scanning the held
  text. Nothing is rendered, served, or executed: every record
  carries ``rendered_here: False``.
- **Analytics & reporting beyond registry reporting** is report
  *definition records* plus run records. A run record stores no
  figures; its figures are deterministic counts over this
  substrate's own core registry, derived at read time from the
  core's registry report. The union spec records OCLC's "custom
  reports" / "Report Designer" as taxonomy near-misses; this
  build is registry-derived reporting, not that designer.
- **Bulk ingestion** is ingestion-batch records (reported counts
  and checksum references; no content held,
  ``content_held: False``) and ingestion-*job* records bound to
  core content records with verbatim reported counts
  (``executed_here: False`` — no ingestion engine runs here).
  **Index-in-place** is index declaration records — field lists
  held as data; no index is built
  (``indexing_performed_here: False``).
- **BPM / case management** is case records over opaque subject
  references with recorded state events (current state derived
  at read) and decision records. No case record shape can hold
  case content: the exact key set is pinned by test. Decisions
  are recorded under the separation-of-duties seam
  :meth:`CmsExtensions._check_decider_not_opener` — the decider
  is never the case's opener. Nothing is investigated or
  adjudicated here (``adjudicated_here: False`` on decisions).
  The case-type vocabulary is generic at this tier: the family
  is carried at 0 claims here, so no fork's casework kinds are
  imported.
- **Participant engagement** is participation records over opaque
  program and participant references with outcome labels recorded
  verbatim as reported, and counts derived at read time. No
  participant is recruited or engaged by this build.
- **Personalization** is audience segment definitions (match
  conditions held as data), subject attribute records keyed by
  opaque references, and rule records binding a segment to a
  content reference. Matching is *derived at read time* by the
  seam :func:`_condition_holds` (the untiered set's adjudicated
  form). No optimization is computed and no content is served
  (``served_here: False``, ``optimized_here: False``).
- The two engine families (CDN / runtime serving, enterprise
  search indexing & discovery) ship as **labeled reference
  implementations**: records carry ``reference_stub: True`` (and
  ``reference_transport: True`` where the family is a transport),
  and each family's own not-here flag is False. Serving follows
  PLATFORM-LAYER.md decision 6 (``served_here`` False — runtime
  serving is a deployment property). Discovery query records
  hold a SHA-256 digest of the query plus opaque result
  references only — the raw query text is never stored, per this
  substrate's metadata-plus-digest discipline.

Access control reuses the founding permission matrix — no new
actions exist. The mapping is: template, fragment, editor
configuration, mobile application / release, analytics report
definition, and stub-reference writes use ``type_write``
(registry configuration) with ``type_read`` reads; ingestion
batches, index declarations, ingestion jobs, the ILS records,
and distribution outcome records use ``asset_write`` /
``asset_read``; case opens and state events use ``item_edit``
with ``item_read`` reads, and case decisions use ``item_review``;
participation, audience segment, subject-attribute, and
personalization-rule writes use ``tag_write`` with ``tag_read``
reads; analytics run views and the ingestion summary use
``report_read``. Write enforcement mirrors the core store: a
missing actor is denied, a User-like actor is checked against
the matrix, and denials are recorded in the core audit log as
``<action>:denied``. Reads enforce only when a User-like actor
is supplied, as in the core.

Ids are sequential per object type with fixed prefixes
(``tpl-``, ``edc-``, ``ing-``, ``idx-``, ``ingj-``, ``loan-``,
``cat-``, ``acq-``, ``ill-``, ``col-``, ``kb-``, ``proxy-``,
``dig-``, ``union-``, ``app-``, ``rel-``, ``dist-``, ``rpt-``,
``run-``, ``case-``, ``dec-``, ``part-``, ``seg-``, ``subj-``,
``prule-``, ``ref-``, ``dqry-``). A failed operation consumes no
id and changes nothing: all validation happens before any
mutation. All timestamps are UTC ISO-8601. Records returned are
copies; mutating a returned record changes nothing stored.
"""

import copy
import hashlib
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

__all__ = ["CmsExtensions"]

CASE_TYPES = (
    "general",
    "service_request",
    "access_request",
    "program_case",
    "other",
)

REPORT_DIMENSIONS = ("status", "site", "type", "asset_kind")

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


def _validate_money_cents(value, what):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValidationError(
            "%s must be a non-negative integer number of cents" % (what,))
    return value


def _validate_sha256(value, what):
    if not isinstance(value, str) or not _SHA256_RE.match(value):
        raise ValidationError(
            "%s must be a 64-character hex SHA-256" % (what,))
    return value.lower()


_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}")


def _condition_holds(condition, attributes):
    """Personalization matching seam (the untiered set's form).

    True iff one recorded match ``condition`` holds against a
    subject's recorded ``attributes``: ``present`` requires the
    key to be recorded; ``equals`` requires the recorded value
    to equal the condition's value exactly.
    """
    key = condition["key"]
    if condition["op"] == "present":
        return key in attributes
    return attributes.get(key) == condition["value"]


def _current_loan_state(events):
    """Loan current-state seam: the latest recorded event's label.

    The current state of a loan is derived at read time from its
    recorded state events and stored nowhere; this is the single
    derivation point.
    """
    return events[-1]["state"]


def _latest_label(events):
    """Latest recorded event label (shared derivation helper)."""
    return events[-1]["state"]


class CmsExtensions:
    """Extension register wrapping a core :class:`cms.store.CmsStore`."""

    def __init__(self, store):
        self.store = store
        self.audit = getattr(store, "audit", None)
        self._templates = {}
        self._editor_configs = {}
        self._ingestions = {}
        self._index_declarations = {}
        self._ingestion_jobs = {}
        self._loans = {}
        self._catalog_records = {}
        self._acquisitions = {}
        self._ill_requests = {}
        self._collections = {}
        self._kb_articles = {}
        self._proxy_configs = {}
        self._digital_collections = {}
        self._digital_items = {}
        self._union_holdings = {}
        self._apps = {}
        self._releases = {}
        self._distribution_outcomes = {}
        self._report_definitions = {}
        self._report_runs = {}
        self._cases = {}
        self._decisions = {}
        self._participations = {}
        self._segments = {}
        self._subjects = {}
        self._rules = {}
        self._references = {}
        self._discovery_queries = {}
        self._counters = {
            "tpl": 0, "edc": 0, "ing": 0, "idx": 0, "ingj": 0,
            "loan": 0, "cat": 0, "acq": 0, "ill": 0, "col": 0,
            "kb": 0, "proxy": 0, "dig": 0, "union": 0, "app": 0,
            "rel": 0, "dist": 0, "rpt": 0, "run": 0, "case": 0,
            "dec": 0, "part": 0, "seg": 0, "subj": 0, "prule": 0,
            "ref": 0, "dqry": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers -------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

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

    # -- templates, fragments & editor configurations ----------------
    # Rendering & templating engines and visual/WYSIWYG editors:
    # definition records only. Bodies and settings are held as
    # data and versioned; nothing is rendered or served.

    def create_template(self, actor, name, body, kind="template"):
        """Create a template or fragment definition record.

        Action: type_write. Ids: tpl-{n}. The body is held as
        data; it is never rendered. ``rendered_here`` is False on
        every record.
        """
        self._require(actor, "type_write", "ext_template_create")
        _validate_non_empty(name, "template name")
        _validate_text(body, "template body")
        if kind not in ("template", "fragment"):
            raise ValidationError("kind must be 'template' or 'fragment'")
        with self._lock:
            template_id = self._next_id("tpl")
            now = _utc_now()
            record = {
                "id": template_id,
                "name": name,
                "kind": kind,
                "body": body,
                "version": 1,
                "history": [],
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._templates[template_id] = record
            self._audit(actor, "ext_template_create", template_id,
                        details={"kind": kind})
            return self._template_view(record)

    def update_template(self, actor, template_id, body):
        """Replace a template body, versioning the prior body.

        Action: type_write. The previous body is retained in the
        record's ``history`` as data; nothing is rendered.
        """
        self._require(actor, "type_write", "ext_template_update", template_id)
        _validate_text(body, "template body")
        with self._lock:
            record = self._get(self._templates, template_id, "template")
            record["history"].append(
                {"version": record["version"], "body": record["body"]})
            record["body"] = body
            record["version"] += 1
            record["updated_utc"] = _utc_now()
            self._audit(actor, "ext_template_update", template_id,
                        details={"version": record["version"]})
            return self._template_view(record)

    def _template_view(self, record):
        view = copy.deepcopy(record)
        view["placeholder_names"] = sorted(
            set(_PLACEHOLDER_RE.findall(record["body"])))
        view["version_count"] = record["version"]
        return view

    def get_template(self, template_id, actor=None):
        """Return one template record with derived placeholders.

        Action: type_read.
        """
        self._require_read(actor, "type_read", "ext_template_read")
        with self._lock:
            return self._template_view(
                self._get(self._templates, template_id, "template"))

    def list_templates(self, actor=None, kind=None):
        """Return template records sorted by id. Action: type_read."""
        self._require_read(actor, "type_read", "ext_template_read")
        with self._lock:
            records = sorted(self._templates.values(),
                             key=lambda r: _id_num(r["id"]))
            if kind is not None:
                records = [r for r in records if r["kind"] == kind]
            return [self._template_view(r) for r in records]

    def create_editor_config(self, actor, name, mode, settings):
        """Create a visual-editor configuration record.

        Action: type_write. Ids: edc-{n}. ``mode`` is a recorded
        label (for example "wysiwyg" or "source"); ``settings``
        are held as data (deep-copied at the boundary). The
        configuration is the definition layer an editor UI would
        manipulate; no editor runs and nothing is rendered here
        (``rendered_here`` is False).
        """
        self._require(actor, "type_write", "ext_editor_config_create")
        _validate_non_empty(name, "editor config name")
        _validate_non_empty(mode, "editor config mode")
        if not isinstance(settings, dict):
            raise ValidationError("settings must be an object")
        with self._lock:
            config_id = self._next_id("edc")
            now = _utc_now()
            record = {
                "id": config_id,
                "name": name,
                "mode": mode,
                "settings": copy.deepcopy(settings),
                "version": 1,
                "history": [],
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._editor_configs[config_id] = record
            self._audit(actor, "ext_editor_config_create", config_id,
                        details={"mode": mode})
            return copy.deepcopy(record)

    def update_editor_config(self, actor, config_id, settings):
        """Replace an editor configuration's settings, versioned.

        Action: type_write. The prior settings are retained in
        the record's ``history`` as data.
        """
        self._require(actor, "type_write", "ext_editor_config_update",
                      config_id)
        if not isinstance(settings, dict):
            raise ValidationError("settings must be an object")
        with self._lock:
            record = self._get(self._editor_configs, config_id,
                               "editor configuration")
            record["history"].append(
                {"version": record["version"],
                 "settings": record["settings"]})
            record["settings"] = copy.deepcopy(settings)
            record["version"] += 1
            record["updated_utc"] = _utc_now()
            self._audit(actor, "ext_editor_config_update", config_id,
                        details={"version": record["version"]})
            return copy.deepcopy(record)

    def get_editor_config(self, config_id, actor=None):
        """Return one editor configuration record. Action: type_read."""
        self._require_read(actor, "type_read", "ext_editor_config_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._editor_configs, config_id,
                          "editor configuration"))

    def list_editor_configs(self, actor=None):
        """Return editor configuration records. Action: type_read."""
        self._require_read(actor, "type_read", "ext_editor_config_read")
        with self._lock:
            records = sorted(self._editor_configs.values(),
                             key=lambda r: _id_num(r["id"]))
            return [copy.deepcopy(r) for r in records]

    # -- bulk ingestion & index-in-place ------------------------------
    # Ingestion-batch records (reported counts + checksum refs;
    # no content held), ingestion-job records bound to core
    # content records (reported counts; no engine runs), and
    # index declaration records (field lists held as data; no
    # index built).

    def create_ingestion_batch(self, actor, name, source_ref,
                               documents_reported, checksum_refs=None):
        """Create an ingestion-batch record.

        Action: asset_write. Ids: ing-{n}. The document count is
        stored exactly as reported by the ingesting system and
        the checksum references are opaque references to content
        held elsewhere; no content is ingested or held here
        (``content_held`` is False).
        """
        self._require(actor, "asset_write", "ext_ingestion_create")
        _validate_non_empty(name, "ingestion batch name")
        _validate_non_empty(source_ref, "source_ref")
        _validate_count(documents_reported, "documents_reported")
        if checksum_refs is None:
            checksum_refs = []
        if not isinstance(checksum_refs, list):
            raise ValidationError("checksum_refs must be a list")
        refs = [_validate_non_empty(ref, "checksum ref")
                for ref in checksum_refs]
        with self._lock:
            batch_id = self._next_id("ing")
            record = {
                "id": batch_id,
                "name": name,
                "source_ref": source_ref,
                "documents_reported": documents_reported,
                "checksum_refs": refs,
                "content_held": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._ingestions[batch_id] = record
            self._audit(actor, "ext_ingestion_create", batch_id,
                        details={"source_ref": source_ref})
            return copy.deepcopy(record)

    def get_ingestion_batch(self, batch_id, actor=None):
        """Return one ingestion-batch record. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_ingestion_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._ingestions, batch_id, "ingestion batch"))

    def list_ingestion_batches(self, actor=None):
        """Return ingestion-batch records. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_ingestion_read")
        with self._lock:
            records = sorted(self._ingestions.values(),
                             key=lambda r: _id_num(r["id"]))
            return [copy.deepcopy(r) for r in records]

    def create_ingestion_job(self, actor, name, item_id,
                             documents_reported):
        """Create an ingestion-job record bound to a core item.

        Action: asset_write. Ids: ingj-{n}. The job is bound to
        an existing core content record (an unknown item is
        rejected with no id consumed); the document count is
        stored exactly as reported. Ingested content is handled
        exactly as the core's discipline allows — the registry
        holds records, metadata, and checksums, never file
        bytes — and no ingestion engine runs here
        (``executed_here`` is False).
        """
        self._require(actor, "asset_write", "ext_ingestion_job_create")
        _validate_non_empty(name, "ingestion job name")
        _validate_non_empty(item_id, "item_id")
        _validate_count(documents_reported, "documents_reported")
        with self._lock:
            self.store.get_item(item_id, actor=actor)
            job_id = self._next_id("ingj")
            record = {
                "id": job_id,
                "name": name,
                "item_id": item_id,
                "documents_reported": documents_reported,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._ingestion_jobs[job_id] = record
            self._audit(actor, "ext_ingestion_job_create", job_id,
                        details={"item_id": item_id})
            return copy.deepcopy(record)

    def get_ingestion_job(self, job_id, actor=None):
        """Return one ingestion-job record. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_ingestion_job_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._ingestion_jobs, job_id, "ingestion job"))

    def list_ingestion_jobs(self, actor=None, item_id=None):
        """Return ingestion-job records. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_ingestion_job_read")
        with self._lock:
            records = sorted(self._ingestion_jobs.values(),
                             key=lambda r: _id_num(r["id"]))
            if item_id is not None:
                records = [r for r in records if r["item_id"] == item_id]
            return [copy.deepcopy(r) for r in records]

    def create_index_declaration(self, actor, name, target_ref, fields):
        """Create an index-in-place declaration record.

        Action: asset_write. Ids: idx-{n}. The declaration holds
        the target reference and the field list as data; building
        the index is an external engine's work and no index is
        built here (``indexing_performed_here`` is False).
        """
        self._require(actor, "asset_write", "ext_index_declaration_create")
        _validate_non_empty(name, "index declaration name")
        _validate_non_empty(target_ref, "target_ref")
        if not isinstance(fields, list) or not fields:
            raise ValidationError("fields must be a non-empty list")
        clean_fields = [_validate_non_empty(f, "index field")
                        for f in fields]
        with self._lock:
            declaration_id = self._next_id("idx")
            record = {
                "id": declaration_id,
                "name": name,
                "target_ref": target_ref,
                "fields": clean_fields,
                "indexing_performed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._index_declarations[declaration_id] = record
            self._audit(actor, "ext_index_declaration_create", declaration_id,
                        details={"target_ref": target_ref})
            return copy.deepcopy(record)

    def get_index_declaration(self, declaration_id, actor=None):
        """Return one index declaration record. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_index_declaration_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._index_declarations, declaration_id,
                          "index declaration"))

    def list_index_declarations(self, actor=None):
        """Return index declaration records. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_index_declaration_read")
        with self._lock:
            records = sorted(self._index_declarations.values(),
                             key=lambda r: _id_num(r["id"]))
            return [copy.deepcopy(r) for r in records]

    def ingestion_summary(self, actor=None):
        """Derive ingestion totals at read time. Action: report_read.

        Counts only, computed from the batch, job, and
        declaration records; stored nowhere.
        """
        self._require_read(actor, "report_read", "ext_ingestion_summary")
        with self._lock:
            batches = list(self._ingestions.values())
            jobs = list(self._ingestion_jobs.values())
            return {
                "batch_count": len(batches),
                "documents_reported_total": sum(
                    b["documents_reported"] for b in batches),
                "checksum_ref_count": sum(
                    len(b["checksum_refs"]) for b in batches),
                "job_count": len(jobs),
                "job_documents_reported_total": sum(
                    j["documents_reported"] for j in jobs),
                "index_declaration_count": len(self._index_declarations),
                "content_held": False,
            }

    # -- library ILS vertical ------------------------------------------
    # This group's dominant vertical, in this group's own records
    # form: circulation loans over opaque refs, cataloging field
    # records held as data, acquisition orders as integer-cent
    # data, ILL request records with partner-reported outcomes,
    # collection records, knowledgebase articles in the
    # article-revisions form, access-proxy configuration records,
    # digital collection records as metadata + digests, and
    # union-catalog holding records. Discovery is the core's
    # literal metadata search, unchanged. A dedicated Library
    # Systems category exists elsewhere in this repo; nothing is
    # imported from it.

    def record_loan(self, actor, patron_ref, item_ref,
                    state_label="checked_out"):
        """Record a circulation loan and its initial state event.

        Action: asset_write. Ids: loan-{n}. ``patron_ref`` and
        ``item_ref`` are opaque references; the state label is
        recorded verbatim as the circulation system's reported
        state. The loan's current state is derived at read time
        (see :meth:`loan_view`); it is stored nowhere.
        """
        self._require(actor, "asset_write", "ext_loan_record")
        _validate_non_empty(patron_ref, "patron_ref")
        _validate_non_empty(item_ref, "item_ref")
        _validate_non_empty(state_label, "state_label")
        with self._lock:
            loan_id = self._next_id("loan")
            now = _utc_now()
            record = {
                "id": loan_id,
                "patron_ref": patron_ref,
                "item_ref": item_ref,
                "events": [{
                    "state": state_label,
                    "recorded_by": actor_name(actor),
                    "recorded_utc": now,
                }],
                "created_by": actor_name(actor),
                "created_utc": now,
            }
            self._loans[loan_id] = record
            self._audit(actor, "ext_loan_record", loan_id,
                        details={"item_ref": item_ref})
            return self.loan_view(loan_id, actor=actor)

    def record_loan_event(self, actor, loan_id, state_label):
        """Append a recorded state event to a loan.

        Action: asset_write. The label is stored verbatim (for
        example "renewed" or "checked_in"); the loan's current
        state is re-derived at read from the latest event.
        """
        self._require(actor, "asset_write", "ext_loan_event", loan_id)
        _validate_non_empty(state_label, "state_label")
        with self._lock:
            record = self._get(self._loans, loan_id, "loan")
            record["events"].append({
                "state": state_label,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            })
            self._audit(actor, "ext_loan_event", loan_id,
                        details={"state": state_label})
            return self.loan_view(loan_id, actor=actor)

    def loan_view(self, loan_id, actor=None):
        """Return a loan with its current state derived at read.

        Action: asset_read. ``current_state`` is the latest
        recorded event's label, computed by
        :func:`_current_loan_state`; the stored record carries
        no such key.
        """
        self._require_read(actor, "asset_read", "ext_loan_read")
        with self._lock:
            record = self._get(self._loans, loan_id, "loan")
            view = copy.deepcopy(record)
            view["current_state"] = _current_loan_state(record["events"])
            view["event_count"] = len(record["events"])
            return view

    def list_loans(self, actor=None, patron_ref=None):
        """Return loan views sorted by id. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_loan_read")
        with self._lock:
            records = sorted(self._loans.values(),
                             key=lambda r: _id_num(r["id"]))
            if patron_ref is not None:
                records = [r for r in records
                           if r["patron_ref"] == patron_ref]
            views = []
            for record in records:
                view = copy.deepcopy(record)
                view["current_state"] = _current_loan_state(record["events"])
                view["event_count"] = len(record["events"])
                views.append(view)
            return views

    @staticmethod
    def _validate_catalog_fields(fields):
        if not isinstance(fields, list) or not fields:
            raise ValidationError("fields must be a non-empty list")
        validated = []
        for field in fields:
            if not isinstance(field, dict):
                raise ValidationError("each catalog field must be an object")
            if set(field.keys()) != {"tag", "value"}:
                raise ValidationError(
                    "each catalog field must have exactly 'tag' and 'value'")
            _validate_non_empty(field["tag"], "catalog field tag")
            _validate_text(field["value"], "catalog field value")
            validated.append({"tag": field["tag"], "value": field["value"]})
        return validated

    def create_catalog_record(self, actor, item_ref, fields):
        """Create a MARC21-shaped cataloging field record.

        Action: asset_write. Ids: cat-{n}. The fields (tag/value
        pairs) are held as data, exactly as recorded; they are
        never parsed, and no discovery engine reads them
        (``discovery_engine_here`` is False) — discovery remains
        the core's literal metadata search.
        """
        self._require(actor, "asset_write", "ext_catalog_record_create")
        _validate_non_empty(item_ref, "item_ref")
        fields = self._validate_catalog_fields(fields)
        with self._lock:
            record_id = self._next_id("cat")
            record = {
                "id": record_id,
                "item_ref": item_ref,
                "fields": fields,
                "discovery_engine_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._catalog_records[record_id] = record
            self._audit(actor, "ext_catalog_record_create", record_id,
                        details={"item_ref": item_ref})
            return copy.deepcopy(record)

    def get_catalog_record(self, record_id, actor=None):
        """Return one cataloging field record. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_catalog_record_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._catalog_records, record_id,
                          "catalog record"))

    def list_catalog_records(self, actor=None, item_ref=None):
        """Return cataloging field records. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_catalog_record_read")
        with self._lock:
            records = sorted(self._catalog_records.values(),
                             key=lambda r: _id_num(r["id"]))
            if item_ref is not None:
                records = [r for r in records if r["item_ref"] == item_ref]
            return [copy.deepcopy(r) for r in records]

    def create_acquisition_order(self, actor, supplier_ref, item_ref,
                                 amount_cents, state_label="ordered"):
        """Create an acquisition order record.

        Action: asset_write. Ids: acq-{n}. The amount is an
        integer number of cents held as data (floats and
        booleans are rejected at the boundary); the state label
        is recorded verbatim. No order is transmitted anywhere
        (``transmitted_here`` is False).
        """
        self._require(actor, "asset_write", "ext_acquisition_create")
        _validate_non_empty(supplier_ref, "supplier_ref")
        _validate_non_empty(item_ref, "item_ref")
        _validate_money_cents(amount_cents, "amount_cents")
        _validate_non_empty(state_label, "state_label")
        with self._lock:
            order_id = self._next_id("acq")
            record = {
                "id": order_id,
                "supplier_ref": supplier_ref,
                "item_ref": item_ref,
                "amount_cents": amount_cents,
                "state_label": state_label,
                "transmitted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._acquisitions[order_id] = record
            self._audit(actor, "ext_acquisition_create", order_id,
                        details={"supplier_ref": supplier_ref})
            return copy.deepcopy(record)

    def get_acquisition_order(self, order_id, actor=None):
        """Return one acquisition order record. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_acquisition_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._acquisitions, order_id,
                          "acquisition order"))

    def list_acquisition_orders(self, actor=None):
        """Return acquisition order records. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_acquisition_read")
        with self._lock:
            records = sorted(self._acquisitions.values(),
                             key=lambda r: _id_num(r["id"]))
            return [copy.deepcopy(r) for r in records]

    def record_ill_request(self, actor, patron_ref, item_ref, partner_ref,
                           state_label="requested"):
        """Record an interlibrary-loan (resource sharing) request.

        Action: asset_write. Ids: ill-{n}. All references are
        opaque; the initial state label is recorded verbatim as
        reported. Fulfillment is the partner library's system —
        this build fulfills nothing (the view carries
        ``fulfilled_here: False``); outcomes arrive as recorded
        events (see :meth:`record_ill_event`).
        """
        self._require(actor, "asset_write", "ext_ill_record")
        _validate_non_empty(patron_ref, "patron_ref")
        _validate_non_empty(item_ref, "item_ref")
        _validate_non_empty(partner_ref, "partner_ref")
        _validate_non_empty(state_label, "state_label")
        with self._lock:
            ill_id = self._next_id("ill")
            now = _utc_now()
            record = {
                "id": ill_id,
                "patron_ref": patron_ref,
                "item_ref": item_ref,
                "partner_ref": partner_ref,
                "events": [{
                    "state": state_label,
                    "recorded_by": actor_name(actor),
                    "recorded_utc": now,
                }],
                "created_by": actor_name(actor),
                "created_utc": now,
            }
            self._ill_requests[ill_id] = record
            self._audit(actor, "ext_ill_record", ill_id,
                        details={"partner_ref": partner_ref})
            return self.ill_view(ill_id, actor=actor)

    def record_ill_event(self, actor, ill_id, outcome_label):
        """Append a partner-reported outcome event to an ILL request.

        Action: asset_write. The outcome label is stored verbatim
        as reported by the partner library (for example
        "shipped" or "unfilled"); the request's current state is
        re-derived at read from the latest event.
        """
        self._require(actor, "asset_write", "ext_ill_event", ill_id)
        _validate_non_empty(outcome_label, "outcome_label")
        with self._lock:
            record = self._get(self._ill_requests, ill_id, "ILL request")
            record["events"].append({
                "state": outcome_label,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            })
            self._audit(actor, "ext_ill_event", ill_id,
                        details={"state": outcome_label})
            return self.ill_view(ill_id, actor=actor)

    def ill_view(self, ill_id, actor=None):
        """Return an ILL request with derived state. Action: asset_read.

        ``current_state`` is the latest recorded event's label;
        the stored record carries no such key.
        ``fulfilled_here`` is False: fulfillment happens in the
        partner library's system, never here.
        """
        self._require_read(actor, "asset_read", "ext_ill_read")
        with self._lock:
            record = self._get(self._ill_requests, ill_id, "ILL request")
            view = copy.deepcopy(record)
            view["current_state"] = _latest_label(record["events"])
            view["event_count"] = len(record["events"])
            view["fulfilled_here"] = False
            return view

    def list_ill_requests(self, actor=None, patron_ref=None):
        """Return ILL request views sorted by id. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_ill_read")
        with self._lock:
            records = sorted(self._ill_requests.values(),
                             key=lambda r: _id_num(r["id"]))
            if patron_ref is not None:
                records = [r for r in records
                           if r["patron_ref"] == patron_ref]
            views = []
            for record in records:
                view = copy.deepcopy(record)
                view["current_state"] = _latest_label(record["events"])
                view["event_count"] = len(record["events"])
                view["fulfilled_here"] = False
                views.append(view)
            return views

    def create_collection_record(self, actor, name, item_ref,
                                 collection_label):
        """Create a collection-management record.

        Action: asset_write. Ids: col-{n}. The record binds an
        opaque item reference to a recorded collection label as
        data; collection state beyond the label is the library's
        own system.
        """
        self._require(actor, "asset_write", "ext_collection_create")
        _validate_non_empty(name, "collection record name")
        _validate_non_empty(item_ref, "item_ref")
        _validate_non_empty(collection_label, "collection_label")
        with self._lock:
            record_id = self._next_id("col")
            record = {
                "id": record_id,
                "name": name,
                "item_ref": item_ref,
                "collection_label": collection_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._collections[record_id] = record
            self._audit(actor, "ext_collection_create", record_id,
                        details={"collection_label": collection_label})
            return copy.deepcopy(record)

    def get_collection_record(self, record_id, actor=None):
        """Return one collection record. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_collection_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._collections, record_id,
                          "collection record"))

    def list_collection_records(self, actor=None, collection_label=None):
        """Return collection records. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_collection_read")
        with self._lock:
            records = sorted(self._collections.values(),
                             key=lambda r: _id_num(r["id"]))
            if collection_label is not None:
                records = [r for r in records
                           if r["collection_label"] == collection_label]
            return [copy.deepcopy(r) for r in records]

    def collection_summary(self, actor=None):
        """Derive collection counts at read time. Action: report_read.

        Counts only, grouped by recorded collection label;
        stored nowhere.
        """
        self._require_read(actor, "report_read", "ext_collection_summary")
        with self._lock:
            by_label = {}
            for record in self._collections.values():
                label = record["collection_label"]
                by_label[label] = by_label.get(label, 0) + 1
            return {
                "collection_record_count": len(self._collections),
                "records_by_label": by_label,
            }

    def create_kb_article(self, actor, title, body):
        """Create a knowledgebase article record (revision 1).

        Action: asset_write. Ids: kb-{n}. The article body is
        held as data in the article-revisions form: every update
        mints a new revision and retains the prior body in
        ``history``. Nothing is published or rendered here
        (``published_here`` is False on every record).
        """
        self._require(actor, "asset_write", "ext_kb_article_create")
        _validate_non_empty(title, "article title")
        _validate_text(body, "article body")
        with self._lock:
            article_id = self._next_id("kb")
            now = _utc_now()
            record = {
                "id": article_id,
                "title": title,
                "body": body,
                "version": 1,
                "history": [],
                "published_here": False,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._kb_articles[article_id] = record
            self._audit(actor, "ext_kb_article_create", article_id)
            return copy.deepcopy(record)

    def update_kb_article(self, actor, article_id, body):
        """Replace a knowledgebase article body, versioning the prior.

        Action: asset_write. The previous body is retained in
        the record's ``history`` as data.
        """
        self._require(actor, "asset_write", "ext_kb_article_update",
                      article_id)
        _validate_text(body, "article body")
        with self._lock:
            record = self._get(self._kb_articles, article_id,
                               "knowledgebase article")
            record["history"].append(
                {"version": record["version"], "body": record["body"]})
            record["body"] = body
            record["version"] += 1
            record["updated_utc"] = _utc_now()
            self._audit(actor, "ext_kb_article_update", article_id,
                        details={"version": record["version"]})
            return copy.deepcopy(record)

    def get_kb_article(self, article_id, actor=None):
        """Return one knowledgebase article record. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_kb_article_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._kb_articles, article_id,
                          "knowledgebase article"))

    def list_kb_articles(self, actor=None):
        """Return knowledgebase article records. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_kb_article_read")
        with self._lock:
            records = sorted(self._kb_articles.values(),
                             key=lambda r: _id_num(r["id"]))
            return [copy.deepcopy(r) for r in records]

    def create_proxy_config(self, actor, name, target_ref, settings):
        """Create an access-proxying configuration record.

        Action: asset_write. Ids: proxy-{n}. The configuration
        (target reference plus settings held as data, deep-copied
        at the boundary) is the record an EZproxy-style service
        would consume; this build proxies no traffic
        (``proxied_here`` is False).
        """
        self._require(actor, "asset_write", "ext_proxy_config_create")
        _validate_non_empty(name, "proxy config name")
        _validate_non_empty(target_ref, "target_ref")
        if not isinstance(settings, dict):
            raise ValidationError("settings must be an object")
        with self._lock:
            config_id = self._next_id("proxy")
            record = {
                "id": config_id,
                "name": name,
                "target_ref": target_ref,
                "settings": copy.deepcopy(settings),
                "proxied_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._proxy_configs[config_id] = record
            self._audit(actor, "ext_proxy_config_create", config_id,
                        details={"target_ref": target_ref})
            return copy.deepcopy(record)

    def get_proxy_config(self, config_id, actor=None):
        """Return one proxy configuration record. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_proxy_config_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._proxy_configs, config_id,
                          "proxy configuration"))

    def list_proxy_configs(self, actor=None):
        """Return proxy configuration records. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_proxy_config_read")
        with self._lock:
            records = sorted(self._proxy_configs.values(),
                             key=lambda r: _id_num(r["id"]))
            return [copy.deepcopy(r) for r in records]

    def create_digital_collection(self, actor, name, site_id):
        """Create a digital collection record over a core site.

        Action: asset_write. Ids: dig-{n}. The collection is a
        metadata record bound to an existing core site (an
        unknown site is rejected with no id consumed). Its
        member items are metadata-plus-digest records (see
        :meth:`add_digital_item`); no bytes are held here
        (``bytes_held`` is False).
        """
        self._require(actor, "asset_write", "ext_digital_collection_create")
        _validate_non_empty(name, "digital collection name")
        _validate_non_empty(site_id, "site_id")
        with self._lock:
            self.store.get_site(site_id, actor=actor)
            collection_id = self._next_id("dig")
            record = {
                "id": collection_id,
                "name": name,
                "site_id": site_id,
                "bytes_held": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._digital_collections[collection_id] = record
            self._audit(actor, "ext_digital_collection_create",
                        collection_id, details={"site_id": site_id})
            return self.digital_collection_view(collection_id, actor=actor)

    def add_digital_item(self, actor, collection_id, asset_ref,
                         content_sha256):
        """Add a metadata-plus-digest member to a digital collection.

        Action: asset_write. The member record holds an opaque
        asset reference and its SHA-256 digest only — exactly
        the core asset registry's discipline (metadata +
        checksum, never bytes). One member per asset reference
        per collection; duplicates are rejected with no state
        change.
        """
        self._require(actor, "asset_write", "ext_digital_item_add",
                      collection_id)
        _validate_non_empty(asset_ref, "asset_ref")
        digest = _validate_sha256(content_sha256, "content_sha256")
        with self._lock:
            self._get(self._digital_collections, collection_id,
                      "digital collection")
            members = self._digital_items.setdefault(collection_id, [])
            for member in members:
                if member["asset_ref"] == asset_ref:
                    raise ValidationError(
                        "asset %r is already a member of collection %r"
                        % (asset_ref, collection_id))
            member = {
                "asset_ref": asset_ref,
                "content_sha256": digest,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            members.append(member)
            self._audit(actor, "ext_digital_item_add", collection_id,
                        details={"asset_ref": asset_ref})
            return copy.deepcopy(member)

    def digital_collection_view(self, collection_id, actor=None):
        """Return a digital collection with derived member count.

        Action: asset_read. ``member_count`` is derived at read
        time from the member records; it is stored nowhere.
        """
        self._require_read(actor, "asset_read",
                           "ext_digital_collection_read")
        with self._lock:
            record = self._get(self._digital_collections, collection_id,
                               "digital collection")
            view = copy.deepcopy(record)
            members = self._digital_items.get(collection_id, [])
            view["members"] = copy.deepcopy(members)
            view["member_count"] = len(members)
            return view

    def list_digital_collections(self, actor=None):
        """Return digital collection views. Action: asset_read."""
        self._require_read(actor, "asset_read",
                           "ext_digital_collection_read")
        with self._lock:
            return [self.digital_collection_view(r["id"], actor=actor)
                    for r in sorted(self._digital_collections.values(),
                                    key=lambda r: _id_num(r["id"]))]

    def record_union_holding(self, actor, catalog_ref, library_ref,
                             state_label="held"):
        """Record a union-catalog holding / contribution.

        Action: asset_write. Ids: union-{n}. The record states
        that a library (opaque ``library_ref``) is recorded as
        holding or contributing a catalog record (opaque
        ``catalog_ref``), with the state label recorded verbatim.
        The union-catalog data network itself is other
        libraries' systems (``network_here`` is False); current
        state is derived at read from the recorded events.
        """
        self._require(actor, "asset_write", "ext_union_holding_record")
        _validate_non_empty(catalog_ref, "catalog_ref")
        _validate_non_empty(library_ref, "library_ref")
        _validate_non_empty(state_label, "state_label")
        with self._lock:
            holding_id = self._next_id("union")
            now = _utc_now()
            record = {
                "id": holding_id,
                "catalog_ref": catalog_ref,
                "library_ref": library_ref,
                "events": [{
                    "state": state_label,
                    "recorded_by": actor_name(actor),
                    "recorded_utc": now,
                }],
                "network_here": False,
                "created_by": actor_name(actor),
                "created_utc": now,
            }
            self._union_holdings[holding_id] = record
            self._audit(actor, "ext_union_holding_record", holding_id,
                        details={"catalog_ref": catalog_ref})
            return self.union_holding_view(holding_id, actor=actor)

    def record_union_event(self, actor, holding_id, state_label):
        """Append a recorded state event to a union holding.

        Action: asset_write. The label is stored verbatim; the
        holding's current state is re-derived at read.
        """
        self._require(actor, "asset_write", "ext_union_event", holding_id)
        _validate_non_empty(state_label, "state_label")
        with self._lock:
            record = self._get(self._union_holdings, holding_id,
                               "union holding")
            record["events"].append({
                "state": state_label,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            })
            self._audit(actor, "ext_union_event", holding_id,
                        details={"state": state_label})
            return self.union_holding_view(holding_id, actor=actor)

    def union_holding_view(self, holding_id, actor=None):
        """Return a union holding with derived state. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_union_holding_read")
        with self._lock:
            record = self._get(self._union_holdings, holding_id,
                               "union holding")
            view = copy.deepcopy(record)
            view["current_state"] = _latest_label(record["events"])
            view["event_count"] = len(record["events"])
            return view

    def list_union_holdings(self, actor=None, catalog_ref=None):
        """Return union holding views. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_union_holding_read")
        with self._lock:
            records = sorted(self._union_holdings.values(),
                             key=lambda r: _id_num(r["id"]))
            if catalog_ref is not None:
                records = [r for r in records
                           if r["catalog_ref"] == catalog_ref]
            views = []
            for record in records:
                view = copy.deepcopy(record)
                view["current_state"] = _latest_label(record["events"])
                view["event_count"] = len(record["events"])
                views.append(view)
            return views

    # -- mobile application delivery ------------------------------------
    # Application and release definition records plus reported
    # distribution outcome records. No application binary is held
    # and nothing is delivered here.

    def create_app_definition(self, actor, name, platform_label,
                              site_id=None):
        """Create a mobile application definition record.

        Action: type_write. Ids: app-{n}. The definition holds
        the application's name and a recorded platform label as
        data, optionally bound to an existing core site (an
        unknown site is rejected with no id consumed). No
        application binary is held (``binary_held`` False) and
        the companion application itself is not delivered by
        this build (``delivered_here`` False).
        """
        self._require(actor, "type_write", "ext_app_create")
        _validate_non_empty(name, "application name")
        _validate_non_empty(platform_label, "platform_label")
        with self._lock:
            if site_id is not None:
                self.store.get_site(site_id, actor=actor)
            app_id = self._next_id("app")
            record = {
                "id": app_id,
                "name": name,
                "platform_label": platform_label,
                "site_id": site_id,
                "binary_held": False,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._apps[app_id] = record
            self._audit(actor, "ext_app_create", app_id,
                        details={"platform_label": platform_label})
            return copy.deepcopy(record)

    def get_app_definition(self, app_id, actor=None):
        """Return one application definition record. Action: type_read."""
        self._require_read(actor, "type_read", "ext_app_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._apps, app_id, "application definition"))

    def list_app_definitions(self, actor=None):
        """Return application definition records. Action: type_read."""
        self._require_read(actor, "type_read", "ext_app_read")
        with self._lock:
            records = sorted(self._apps.values(),
                             key=lambda r: _id_num(r["id"]))
            return [copy.deepcopy(r) for r in records]

    def create_app_release(self, actor, app_id, version_label):
        """Create a release record for an application definition.

        Action: type_write. Ids: rel-{n}. The release is a
        definition record (application reference plus a recorded
        version label); publishing content to the application
        and distributing the release are external systems'
        work (``delivered_here`` False).
        """
        self._require(actor, "type_write", "ext_app_release_create")
        _validate_non_empty(version_label, "version_label")
        with self._lock:
            self._get(self._apps, app_id, "application definition")
            release_id = self._next_id("rel")
            record = {
                "id": release_id,
                "app_id": app_id,
                "version_label": version_label,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._releases[release_id] = record
            self._audit(actor, "ext_app_release_create", release_id,
                        details={"app_id": app_id})
            return copy.deepcopy(record)

    def get_app_release(self, release_id, actor=None):
        """Return one release record. Action: type_read."""
        self._require_read(actor, "type_read", "ext_app_release_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._releases, release_id, "app release"))

    def list_app_releases(self, actor=None, app_id=None):
        """Return release records. Action: type_read."""
        self._require_read(actor, "type_read", "ext_app_release_read")
        with self._lock:
            records = sorted(self._releases.values(),
                             key=lambda r: _id_num(r["id"]))
            if app_id is not None:
                records = [r for r in records if r["app_id"] == app_id]
            return [copy.deepcopy(r) for r in records]

    def record_distribution_outcome(self, actor, release_id, channel_ref,
                                    installs_reported):
        """Record a reported distribution outcome for a release.

        Action: asset_write. Ids: dist-{n}. The install count is
        stored exactly as reported by the distribution channel;
        nothing was distributed by this build
        (``delivered_here`` False).
        """
        self._require(actor, "asset_write", "ext_distribution_record")
        _validate_non_empty(channel_ref, "channel_ref")
        _validate_count(installs_reported, "installs_reported")
        with self._lock:
            self._get(self._releases, release_id, "app release")
            outcome_id = self._next_id("dist")
            record = {
                "id": outcome_id,
                "release_id": release_id,
                "channel_ref": channel_ref,
                "installs_reported": installs_reported,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._distribution_outcomes[outcome_id] = record
            self._audit(actor, "ext_distribution_record", outcome_id,
                        details={"release_id": release_id})
            return copy.deepcopy(record)

    def list_distribution_outcomes(self, actor=None, release_id=None):
        """Return distribution outcome records. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_distribution_read")
        with self._lock:
            records = sorted(self._distribution_outcomes.values(),
                             key=lambda r: _id_num(r["id"]))
            if release_id is not None:
                records = [r for r in records
                           if r["release_id"] == release_id]
            return [copy.deepcopy(r) for r in records]

    def distribution_summary(self, actor=None):
        """Derive distribution totals at read time. Action: report_read.

        Counts only, computed from the outcome records; stored
        nowhere.
        """
        self._require_read(actor, "report_read", "ext_distribution_summary")
        with self._lock:
            outcomes = list(self._distribution_outcomes.values())
            return {
                "outcome_count": len(outcomes),
                "installs_reported_total": sum(
                    o["installs_reported"] for o in outcomes),
                "release_count": len(self._releases),
                "delivered_here": False,
            }

    # -- analytics & reporting beyond registry reporting -----------------
    # Report definition records plus run records. A run record
    # stores no figures; figures are deterministic counts over
    # this substrate's own core registry, derived at read time.
    # This is registry-derived reporting — the union spec records
    # the forks' "custom reports / Report Designer" as taxonomy
    # near-misses, and this build is not that designer.

    def create_report_definition(self, actor, name, dimension):
        """Create a report definition record.

        Action: type_write. Ids: rpt-{n}. ``dimension`` selects
        which core registry breakdown a run of this report
        derives (``status``, ``site``, ``type``, or
        ``asset_kind``); the definition holds the selection as
        data and computes nothing.
        """
        self._require(actor, "type_write", "ext_report_definition_create")
        _validate_non_empty(name, "report definition name")
        if dimension not in REPORT_DIMENSIONS:
            raise ValidationError(
                "dimension must be one of %s"
                % (", ".join(REPORT_DIMENSIONS),))
        with self._lock:
            definition_id = self._next_id("rpt")
            record = {
                "id": definition_id,
                "name": name,
                "dimension": dimension,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._report_definitions[definition_id] = record
            self._audit(actor, "ext_report_definition_create",
                        definition_id, details={"dimension": dimension})
            return copy.deepcopy(record)

    def get_report_definition(self, definition_id, actor=None):
        """Return one report definition record. Action: type_read."""
        self._require_read(actor, "type_read", "ext_report_definition_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._report_definitions, definition_id,
                          "report definition"))

    def list_report_definitions(self, actor=None):
        """Return report definition records. Action: type_read."""
        self._require_read(actor, "type_read", "ext_report_definition_read")
        with self._lock:
            records = sorted(self._report_definitions.values(),
                             key=lambda r: _id_num(r["id"]))
            return [copy.deepcopy(r) for r in records]

    def record_report_run(self, actor, definition_id):
        """Record a run of a report definition.

        Action: type_write. Ids: run-{n}. The run record stores
        the definition reference and provenance ONLY — its exact
        key set is pinned by test and contains no figure field.
        Figures exist only in the derived view (see
        :meth:`report_run_view`).
        """
        self._require(actor, "type_write", "ext_report_run_record")
        with self._lock:
            self._get(self._report_definitions, definition_id,
                      "report definition")
            run_id = self._next_id("run")
            record = {
                "id": run_id,
                "definition_id": definition_id,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._report_runs[run_id] = record
            self._audit(actor, "ext_report_run_record", run_id,
                        details={"definition_id": definition_id})
            return copy.deepcopy(record)

    def report_run_view(self, run_id, actor=None):
        """Return a run with its figures derived at read time.

        Action: report_read. The figures are the core registry
        report's breakdown for the definition's dimension,
        computed now from registry state — deterministic counts
        over this substrate's own records, stored nowhere
        (``figures_stored`` is False on the view).
        """
        self._require_read(actor, "report_read", "ext_report_run_view")
        with self._lock:
            run = self._get(self._report_runs, run_id, "report run")
            definition = self._get(self._report_definitions,
                                   run["definition_id"],
                                   "report definition")
            report = self.store.registry_report(actor=actor)
            dimension = definition["dimension"]
            if dimension == "status":
                figures = dict(report["items_by_status"])
            elif dimension == "site":
                figures = dict(report["items_by_site"])
            elif dimension == "type":
                figures = dict(report["items_by_type"])
            else:
                figures = dict(report["assets_by_kind"])
            view = copy.deepcopy(run)
            view["dimension"] = dimension
            view["figures"] = figures
            view["figures_stored"] = False
            return view

    def list_report_runs(self, actor=None, definition_id=None):
        """Return run views sorted by id. Action: report_read."""
        self._require_read(actor, "report_read", "ext_report_run_view")
        with self._lock:
            records = sorted(self._report_runs.values(),
                             key=lambda r: _id_num(r["id"]))
            if definition_id is not None:
                records = [r for r in records
                           if r["definition_id"] == definition_id]
            return [self.report_run_view(r["id"], actor=actor)
                    for r in records]

    # -- BPM / case management ------------------------------------------
    # Case records over opaque subject references: recorded state
    # events, current state derived at read, decisions under a
    # separation-of-duties guard. No shape can hold case content.
    # The mechanism is the CMS L2 unit's adjudicated form; the
    # case-type vocabulary is generic here because the family is
    # carried at 0 claims in this group.

    def _check_decider_not_opener(self, case, actor):
        """Separation-of-duties seam for case decisions.

        The decider of a case is never the user who opened it
        (compared by name, as in the core's editorial guard).

        MUTATION DRILL NOTE: this seam is the batch unit's fresh
        negative control — if the check waves through, a case's
        opener can record its decision (see tests/README.md).
        """
        if actor_name(actor) == case["opened_by"]:
            self._audit_denied(actor, "ext_case_decision", case["id"])
            raise PermissionDenied(
                "permission denied: the decider of case %r may not be "
                "its opener %r" % (case["id"], case["opened_by"]))

    def open_case(self, actor, case_ref, subject_ref, case_type):
        """Open a case-management record.

        Action: item_edit. Ids: case-{n}. ``case_ref`` and
        ``subject_ref`` are opaque references supplied by the
        embedding organization. The record holds references,
        type, provenance, and recorded state events only — its
        exact key set is pinned by test and contains no field
        that could hold case content. The initial recorded state
        is "opened"; the current state is derived at read time.
        """
        self._require(actor, "item_edit", "ext_case_open")
        _validate_non_empty(case_ref, "case_ref")
        _validate_non_empty(subject_ref, "subject_ref")
        if case_type not in CASE_TYPES:
            raise ValidationError(
                "case_type must be one of %s" % (", ".join(CASE_TYPES),))
        with self._lock:
            case_id = self._next_id("case")
            now = _utc_now()
            record = {
                "id": case_id,
                "case_ref": case_ref,
                "subject_ref": subject_ref,
                "case_type": case_type,
                "opened_by": actor_name(actor),
                "created_utc": now,
                "events": [{
                    "state": "opened",
                    "recorded_by": actor_name(actor),
                    "recorded_utc": now,
                }],
            }
            self._cases[case_id] = record
            self._audit(actor, "ext_case_open", case_id,
                        details={"case_type": case_type})
            return self.case_view(case_id, actor=actor)

    def record_case_event(self, actor, case_id, state_label):
        """Append a recorded state event to a case.

        Action: item_edit. The label is stored verbatim as a
        reported workflow state; recording it performs no
        workflow step here.
        """
        self._require(actor, "item_edit", "ext_case_event", case_id)
        _validate_non_empty(state_label, "state_label")
        with self._lock:
            record = self._get(self._cases, case_id, "case")
            record["events"].append({
                "state": state_label,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            })
            self._audit(actor, "ext_case_event", case_id,
                        details={"state": state_label})
            return self.case_view(case_id, actor=actor)

    def record_case_decision(self, actor, case_id, decision_label):
        """Record a decision on a case, by a non-opener.

        Action: item_review. Ids: dec-{n}. The decision label is
        recorded verbatim as reported; the decider is never the
        case's opener (separation of duties, enforced by
        :meth:`_check_decider_not_opener` before any state
        change, so a denied decision consumes no id). This build
        adjudicates nothing (``adjudicated_here`` is False on
        every decision record).
        """
        self._require(actor, "item_review", "ext_case_decision", case_id)
        _validate_non_empty(decision_label, "decision_label")
        with self._lock:
            case = self._get(self._cases, case_id, "case")
            self._check_decider_not_opener(case, actor)
            decision_id = self._next_id("dec")
            record = {
                "id": decision_id,
                "case_id": case_id,
                "decision_label": decision_label,
                "decided_by": actor_name(actor),
                "adjudicated_here": False,
                "created_utc": _utc_now(),
            }
            self._decisions[decision_id] = record
            self._audit(actor, "ext_case_decision", decision_id,
                        details={"case_id": case_id})
            return copy.deepcopy(record)

    def _case_view(self, record):
        view = copy.deepcopy(record)
        view["current_state"] = record["events"][-1]["state"]
        view["event_count"] = len(record["events"])
        view["decision_count"] = sum(
            1 for d in self._decisions.values()
            if d["case_id"] == record["id"])
        return view

    def case_view(self, case_id, actor=None):
        """Return a case with derived state/counts. Action: item_read."""
        self._require_read(actor, "item_read", "ext_case_read")
        with self._lock:
            return self._case_view(self._get(self._cases, case_id, "case"))

    def list_cases(self, actor=None, case_type=None):
        """Return case views sorted by id. Action: item_read."""
        self._require_read(actor, "item_read", "ext_case_read")
        with self._lock:
            records = sorted(self._cases.values(),
                             key=lambda r: _id_num(r["id"]))
            if case_type is not None:
                records = [r for r in records
                           if r["case_type"] == case_type]
            return [self._case_view(r) for r in records]

    def list_case_decisions(self, case_id=None, actor=None):
        """Return decision records sorted by id. Action: item_read."""
        self._require_read(actor, "item_read", "ext_case_decision_read")
        with self._lock:
            records = sorted(self._decisions.values(),
                             key=lambda r: _id_num(r["id"]))
            if case_id is not None:
                records = [r for r in records if r["case_id"] == case_id]
            return [copy.deepcopy(r) for r in records]

    # -- participant engagement ------------------------------------------
    # Participation records over opaque program and participant
    # references; outcome labels recorded verbatim as reported;
    # counts derived at read time.

    def record_participation(self, actor, program_ref, participant_ref,
                             outcome_label):
        """Record a participation record with a reported outcome.

        Action: tag_write. Ids: part-{n}. ``program_ref`` and
        ``participant_ref`` are opaque references; the outcome
        label is stored exactly as reported by the engagement
        program. This build records no participant identity of
        its own and engages no participant — the record is the
        reported outcome, nothing more.
        """
        self._require(actor, "tag_write", "ext_participation_record")
        _validate_non_empty(program_ref, "program_ref")
        _validate_non_empty(participant_ref, "participant_ref")
        _validate_non_empty(outcome_label, "outcome_label")
        with self._lock:
            record_id = self._next_id("part")
            record = {
                "id": record_id,
                "program_ref": program_ref,
                "participant_ref": participant_ref,
                "outcome_label": outcome_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._participations[record_id] = record
            self._audit(actor, "ext_participation_record", record_id,
                        details={"program_ref": program_ref})
            return copy.deepcopy(record)

    def get_participation(self, record_id, actor=None):
        """Return one participation record. Action: tag_read."""
        self._require_read(actor, "tag_read", "ext_participation_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._participations, record_id,
                          "participation record"))

    def list_participations(self, actor=None, program_ref=None):
        """Return participation records. Action: tag_read."""
        self._require_read(actor, "tag_read", "ext_participation_read")
        with self._lock:
            records = sorted(self._participations.values(),
                             key=lambda r: _id_num(r["id"]))
            if program_ref is not None:
                records = [r for r in records
                           if r["program_ref"] == program_ref]
            return [copy.deepcopy(r) for r in records]

    def participation_summary(self, program_ref, actor=None):
        """Derive participation counts for one program, at read time.

        Action: tag_read. Counts only, grouped by recorded
        outcome label; stored nowhere.
        """
        self._require_read(actor, "tag_read", "ext_participation_read")
        _validate_non_empty(program_ref, "program_ref")
        with self._lock:
            records = [r for r in self._participations.values()
                       if r["program_ref"] == program_ref]
            by_outcome = {}
            for record in records:
                label = record["outcome_label"]
                by_outcome[label] = by_outcome.get(label, 0) + 1
            return {
                "program_ref": program_ref,
                "participation_count": len(records),
                "by_outcome": by_outcome,
            }

    # -- personalization (segments, subjects, rules) -----------------
    # The untiered set's adjudicated records form: segment
    # definitions, opaque-ref subject attributes, rules; matching
    # derived at read by _condition_holds.

    @staticmethod
    def _validate_conditions(conditions):
        if not isinstance(conditions, list) or not conditions:
            raise ValidationError("conditions must be a non-empty list")
        validated = []
        for cond in conditions:
            if not isinstance(cond, dict):
                raise ValidationError("each condition must be an object")
            key = cond.get("key")
            op = cond.get("op")
            _validate_non_empty(key, "condition key")
            if op not in ("present", "equals"):
                raise ValidationError(
                    "condition op must be 'present' or 'equals'")
            entry = {"key": key, "op": op}
            if op == "equals":
                value = cond.get("value")
                if not isinstance(value, (str, int)) or isinstance(value, bool):
                    raise ValidationError(
                        "an 'equals' condition value must be a string or int")
                entry["value"] = value
            validated.append(entry)
        return validated

    def create_segment(self, actor, name, conditions):
        """Create an audience segment definition.

        Action: tag_write. Ids: seg-{n}. Match conditions are
        held as data; whether any subject satisfies them is
        derived at read time, never stored.
        """
        self._require(actor, "tag_write", "ext_segment_create")
        _validate_non_empty(name, "segment name")
        conditions = self._validate_conditions(conditions)
        with self._lock:
            segment_id = self._next_id("seg")
            record = {
                "id": segment_id,
                "name": name,
                "conditions": conditions,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._segments[segment_id] = record
            self._audit(actor, "ext_segment_create", segment_id)
            return copy.deepcopy(record)

    def get_segment(self, segment_id, actor=None):
        """Return one segment definition. Action: tag_read."""
        self._require_read(actor, "tag_read", "ext_segment_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._segments, segment_id, "segment"))

    def list_segments(self, actor=None):
        """Return segment definitions sorted by id. Action: tag_read."""
        self._require_read(actor, "tag_read", "ext_segment_read")
        with self._lock:
            records = sorted(self._segments.values(),
                             key=lambda r: _id_num(r["id"]))
            return [copy.deepcopy(r) for r in records]

    @staticmethod
    def _validate_attributes(attributes):
        if not isinstance(attributes, dict):
            raise ValidationError("attributes must be an object")
        for key, value in attributes.items():
            if not isinstance(key, str) or not key.strip():
                raise ValidationError("attribute keys must be non-empty strings")
            if not isinstance(value, (str, int)) or isinstance(value, bool):
                raise ValidationError(
                    "attribute values must be strings or ints")
        return dict(attributes)

    def record_subject_attributes(self, actor, subject_ref, attributes):
        """Record (or replace) a subject's recorded attributes.

        Action: tag_write. Ids: subj-{n}. ``subject_ref`` is an
        opaque reference supplied by the embedding organization;
        this build records no visitor identity of its own. One
        record per subject_ref: re-recording replaces the
        attributes and keeps the id.
        """
        self._require(actor, "tag_write", "ext_subject_record")
        _validate_non_empty(subject_ref, "subject_ref")
        attributes = self._validate_attributes(attributes)
        with self._lock:
            existing = None
            for rec in self._subjects.values():
                if rec["subject_ref"] == subject_ref:
                    existing = rec
                    break
            now = _utc_now()
            if existing is None:
                subject_id = self._next_id("subj")
                record = {
                    "id": subject_id,
                    "subject_ref": subject_ref,
                    "attributes": attributes,
                    "created_by": actor_name(actor),
                    "created_utc": now,
                    "updated_utc": now,
                }
                self._subjects[subject_id] = record
            else:
                existing["attributes"] = attributes
                existing["updated_utc"] = now
                record = existing
            self._audit(actor, "ext_subject_record", record["id"],
                        details={"subject_ref": subject_ref})
            return copy.deepcopy(record)

    def _subject_record(self, subject_ref):
        for rec in self._subjects.values():
            if rec["subject_ref"] == subject_ref:
                return rec
        raise NotFoundError("subject not found: %r" % (subject_ref,))

    def segment_match(self, segment_id, subject_ref, actor=None):
        """Derive whether a subject matches a segment, at read time.

        Action: tag_read. The result is computed from the
        segment's recorded conditions and the subject's recorded
        attributes via :func:`_condition_holds`; it is stored
        nowhere, and no content is served.
        """
        self._require_read(actor, "tag_read", "ext_segment_match")
        with self._lock:
            segment = self._get(self._segments, segment_id, "segment")
            subject = self._subject_record(subject_ref)
            attributes = subject["attributes"]
            holds = [_condition_holds(c, attributes)
                     for c in segment["conditions"]]
            return {
                "segment_id": segment_id,
                "subject_ref": subject_ref,
                "matched": all(holds),
                "matched_conditions": sum(1 for h in holds if h),
                "total_conditions": len(holds),
                "method": "deterministic_recorded_attributes",
                "served_here": False,
            }

    def segment_match_counts(self, segment_id, actor=None):
        """Derive match counts for a segment over recorded subjects.

        Action: tag_read. Counts only — no subject list, no
        ranking, no optimization value.
        """
        self._require_read(actor, "tag_read", "ext_segment_match")
        with self._lock:
            segment = self._get(self._segments, segment_id, "segment")
            subjects = list(self._subjects.values())
            matching = sum(
                1 for rec in subjects
                if all(_condition_holds(c, rec["attributes"])
                       for c in segment["conditions"]))
            return {
                "segment_id": segment_id,
                "subjects_recorded": len(subjects),
                "subjects_matching": matching,
                "optimized_here": False,
            }

    def create_rule(self, actor, name, segment_id, content_ref):
        """Create a personalization rule record.

        Action: tag_write. Ids: prule-{n}. The rule binds a
        segment to an opaque content reference as data; applying
        it is a read-time derivation (see :meth:`rule_view`), and
        nothing is served or optimized here.
        """
        self._require(actor, "tag_write", "ext_rule_create")
        _validate_non_empty(name, "rule name")
        _validate_non_empty(content_ref, "content_ref")
        with self._lock:
            self._get(self._segments, segment_id, "segment")
            rule_id = self._next_id("prule")
            record = {
                "id": rule_id,
                "name": name,
                "segment_id": segment_id,
                "content_ref": content_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._rules[rule_id] = record
            self._audit(actor, "ext_rule_create", rule_id,
                        details={"segment_id": segment_id})
            return copy.deepcopy(record)

    def rule_view(self, rule_id, subject_ref, actor=None):
        """Derive a rule's application to one subject, at read time.

        Action: tag_read. Reports whether the subject's recorded
        attributes satisfy the rule's segment; the content itself
        is neither fetched nor served here.
        """
        self._require_read(actor, "tag_read", "ext_rule_read")
        with self._lock:
            rule = self._get(self._rules, rule_id, "rule")
            match = self.segment_match(rule["segment_id"], subject_ref, actor)
            return {
                "rule_id": rule_id,
                "content_ref": rule["content_ref"],
                "subject_ref": subject_ref,
                "segment_matched": match["matched"],
                "served_here": False,
                "optimized_here": False,
            }

    # -- labeled reference implementations (stub engines) -------------

    def _create_reference(self, actor, family, name, audit_action,
                          flags, extra=None):
        _validate_non_empty(name, "reference name")
        with self._lock:
            ref_id = self._next_id("ref")
            record = {
                "id": ref_id,
                "family": family,
                "name": name,
                "reference_stub": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            record.update(flags)
            if extra:
                record.update(extra)
            self._references[ref_id] = record
            self._audit(actor, audit_action, ref_id, details={"family": family})
            return copy.deepcopy(record)

    def _get_reference(self, ref_id, family):
        record = self._get(self._references, ref_id, "reference")
        if record["family"] != family:
            raise NotFoundError(
                "reference %r is not a %s reference" % (ref_id, family))
        return record

    def get_reference(self, ref_id, actor=None):
        """Return one reference record. Action: type_read."""
        self._require_read(actor, "type_read", "ext_reference_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._references, ref_id, "reference"))

    def list_references(self, family=None, actor=None):
        """Return reference records sorted by id. Action: type_read."""
        self._require_read(actor, "type_read", "ext_reference_read")
        with self._lock:
            records = sorted(self._references.values(),
                             key=lambda r: _id_num(r["id"]))
            if family is not None:
                records = [r for r in records if r["family"] == family]
            return [copy.deepcopy(r) for r in records]

    def register_cdn_reference(self, actor, name):
        """Register a CDN / delivery network reference.

        Action: type_write. Per PLATFORM-LAYER.md decision 6,
        runtime serving is a deployment property; this build
        serves no site (``served_here`` False) and its delivery
        receipts are transport references
        (``reference_transport`` True). The union spec records
        one sibling's "content delivery functionality" as a
        taxonomy near-miss; the reference form stands either way.
        """
        self._require(actor, "type_write", "ext_reference_create")
        return self._create_reference(
            actor, "cdn_delivery", name, "ext_reference_create",
            {"reference_transport": True, "served_here": False})

    def record_cdn_receipt(self, actor, ref_id, channel_ref):
        """Record a transport receipt against a CDN reference.

        Action: type_write. The receipt records that the external
        delivery network reported a delivery against an opaque
        channel reference; nothing was served by this build.
        """
        self._require(actor, "type_write", "ext_reference_run", ref_id)
        _validate_non_empty(channel_ref, "channel_ref")
        with self._lock:
            record = self._get_reference(ref_id, "cdn_delivery")
            receipts = record.setdefault("receipts", [])
            receipts.append({
                "channel_ref": channel_ref,
                "reference_transport": True,
                "reported_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            })
            self._audit(actor, "ext_reference_run", ref_id,
                        details={"family": "cdn_delivery"})
            return copy.deepcopy(record)

    def register_search_index_reference(self, actor, name, scope_ref):
        """Register an enterprise search indexing / discovery reference.

        Action: type_write. This build's search stays the core's
        literal substring search over registry metadata; the
        reference records that an indexing and discovery engine
        is an external system. ``indexed_here`` is False. The
        union spec records one sibling's discovery service as a
        near-miss under the verbatim taxonomy; the reference
        form stands either way.
        """
        self._require(actor, "type_write", "ext_reference_create")
        _validate_non_empty(scope_ref, "scope_ref")
        return self._create_reference(
            actor, "search_index", name, "ext_reference_create",
            {"indexed_here": False}, {"scope_ref": scope_ref})

    def record_index_run_reference(self, actor, ref_id, documents_reported):
        """Record an engine-reported indexing run against a reference.

        Action: type_write. The document count is stored exactly
        as reported by the external engine; nothing was indexed
        here.
        """
        self._require(actor, "type_write", "ext_reference_run", ref_id)
        _validate_count(documents_reported, "documents_reported")
        with self._lock:
            record = self._get_reference(ref_id, "search_index")
            runs = record.setdefault("runs", [])
            runs.append({
                "documents_reported": documents_reported,
                "reported_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            })
            self._audit(actor, "ext_reference_run", ref_id,
                        details={"family": "search_index"})
            return copy.deepcopy(record)

    def record_discovery_query(self, actor, query_text, result_refs=None):
        """Record a discovery query as a digest-plus-references record.

        Action: type_write. Ids: dqry-{n}. Per this substrate's
        discipline (records hold metadata and digests, not
        content), the record stores the SHA-256 digest of the
        query text and the opaque result references reported by
        the external discovery engine — the raw query text is
        never stored, and no index is consulted here
        (``indexed_here`` False, ``reference_stub`` True).
        """
        self._require(actor, "type_write", "ext_discovery_query_record")
        _validate_non_empty(query_text, "query_text")
        if result_refs is None:
            result_refs = []
        if not isinstance(result_refs, list):
            raise ValidationError("result_refs must be a list")
        refs = [_validate_non_empty(ref, "result ref")
                for ref in result_refs]
        digest = hashlib.sha256(query_text.encode("utf-8")).hexdigest()
        with self._lock:
            query_id = self._next_id("dqry")
            record = {
                "id": query_id,
                "query_sha256": digest,
                "result_refs": refs,
                "reference_stub": True,
                "indexed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._discovery_queries[query_id] = record
            self._audit(actor, "ext_discovery_query_record", query_id)
            return copy.deepcopy(record)

    def get_discovery_query(self, query_id, actor=None):
        """Return one discovery query record. Action: type_read."""
        self._require_read(actor, "type_read", "ext_discovery_query_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._discovery_queries, query_id,
                          "discovery query"))

    def list_discovery_queries(self, actor=None):
        """Return discovery query records. Action: type_read."""
        self._require_read(actor, "type_read", "ext_discovery_query_read")
        with self._lock:
            records = sorted(self._discovery_queries.values(),
                             key=lambda r: _id_num(r["id"]))
            return [copy.deepcopy(r) for r in records]
