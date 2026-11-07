"""Final GAPS batch extensions — Group 20 (CMS L2).

Records-form implementations and labeled reference implementations
for the ten open Extended families of this group's union spec,
built over the founding CMS substrate in :mod:`cms.store`. This
module is the only code the batch adds; every core module is
unchanged.

Honesty labels, per family:

- **Templates, fragments & editor configurations** are definition
  records. A template body is held as data and versioned;
  placeholder names are derived at read time by scanning the held
  text. Nothing is rendered, served, or executed: every record
  carries ``rendered_here: False``. (The untiered set's batch unit
  adjudicated this same form; it is mirrored here.)
- **Bulk ingestion** is ingestion-batch records: a source
  reference, a document count stored exactly as reported, and
  checksum references. No content is ingested or held
  (``content_held: False``). **Index-in-place** is index
  declaration records — field lists held as data; no index is
  built (``indexing_performed_here: False``).
- **Library ILS vertical** is this group's own records form —
  circulation-style loan records over opaque patron and item
  references (recorded state events; current state derived at
  read time), MARC21 cataloging field records held as data and
  never parsed into a discovery engine, and EDI acquisition order
  records holding integer-cent amounts as data, never transmitted
  (``transmitted_here: False``). Discovery stays the core's
  literal substring search over registry metadata. A dedicated
  Library Systems category exists elsewhere in this repo; this
  entry closes as this group's vertical records form and imports
  nothing from that group.
- **BPM / case management** is case records over opaque subject
  references with recorded state events (current state derived
  at read) and decision records. No case record shape can hold
  case content: the exact key set is pinned by test and contains
  no content, narrative, or evidence field. Decisions are
  recorded under the separation-of-duties seam
  :meth:`CmsExtensions._check_decider_not_opener` — the decider
  is never the case's opener. Nothing is investigated or
  adjudicated here (``adjudicated_here: False`` on decisions).
- **Personalization** is audience segment definitions (match
  conditions held as data), subject attribute records keyed by
  opaque references, and rule records binding a segment to a
  content reference. Matching is *derived at read time* by the
  seam :func:`_condition_holds` (the same records form the
  untiered set adjudicated). No optimization is computed and no
  content is served (``served_here: False``,
  ``optimized_here: False``).
- The five engine families (CDN / runtime serving, enterprise
  search indexing, participant engagement vertical, platform
  hosting, editorial workflow engines) ship as **labeled
  reference implementations**: records carry
  ``reference_stub: True`` (and ``reference_transport: True``
  where the family is a transport), and each family's own
  not-here flag is False. Hosting follows PLATFORM-LAYER.md
  decision 6 (``hosted_here`` False — a fork's substrate does
  not transfer to the build).

Access control reuses the founding permission matrix — no new
actions exist. The mapping is: template, fragment, editor
configuration, and stub-reference writes use ``type_write``
(registry configuration) with ``type_read`` reads, except hosting
references, which use ``site_write`` / ``site_read``; ingestion
batches, index declarations, and the ILS records use
``asset_write`` / ``asset_read``; case opens and state events use
``item_edit`` with ``item_read`` reads, and case decisions use
``item_review``; audience segment, subject-attribute, and
personalization-rule writes use ``tag_write`` with ``tag_read``
reads; the ingestion summary uses ``report_read``. Write
enforcement mirrors the core store: a missing actor is denied, a
User-like actor is checked against the matrix, and denials are
recorded in the core audit log as ``<action>:denied``. Reads
enforce only when a User-like actor is supplied, as in the core.

Ids are sequential per object type with fixed prefixes
(``tpl-``, ``edc-``, ``ing-``, ``idx-``, ``loan-``, ``cat-``,
``acq-``, ``case-``, ``dec-``, ``seg-``, ``subj-``, ``prule-``,
``ref-``). A failed operation consumes no id and changes nothing:
all validation happens before any mutation. All timestamps are
UTC ISO-8601. Records returned are copies; mutating a returned
record changes nothing stored.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

__all__ = ["CmsExtensions"]

CASE_TYPES = (
    "eeo",
    "labor_relations",
    "accommodation",
    "background_investigation",
    "ig_casework",
    "other",
)


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


_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}")


def _condition_holds(condition, attributes):
    """Personalization matching seam (mirrors the untiered set's).

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


class CmsExtensions:
    """Extension register wrapping a core :class:`cms.store.CmsStore`."""

    def __init__(self, store):
        self.store = store
        self.audit = getattr(store, "audit", None)
        self._templates = {}
        self._editor_configs = {}
        self._ingestions = {}
        self._index_declarations = {}
        self._loans = {}
        self._catalog_records = {}
        self._acquisitions = {}
        self._cases = {}
        self._decisions = {}
        self._segments = {}
        self._subjects = {}
        self._rules = {}
        self._references = {}
        self._counters = {
            "tpl": 0, "edc": 0, "ing": 0, "idx": 0, "loan": 0,
            "cat": 0, "acq": 0, "case": 0, "dec": 0, "seg": 0,
            "subj": 0, "prule": 0, "ref": 0,
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
    # no content held) and index declaration records (field lists
    # held as data; no index built).

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

        Counts only, computed from the batch and declaration
        records; stored nowhere.
        """
        self._require_read(actor, "report_read", "ext_ingestion_summary")
        with self._lock:
            batches = list(self._ingestions.values())
            return {
                "batch_count": len(batches),
                "documents_reported_total": sum(
                    b["documents_reported"] for b in batches),
                "checksum_ref_count": sum(
                    len(b["checksum_refs"]) for b in batches),
                "index_declaration_count": len(self._index_declarations),
                "content_held": False,
            }

    # -- library ILS vertical ------------------------------------------
    # This group's own records form: circulation-style loans over
    # opaque refs, MARC21 cataloging field records held as data,
    # EDI acquisition orders as integer-cent data. Discovery is
    # the core's literal metadata search, unchanged.

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
        """Create a MARC21 cataloging field record.

        Action: asset_write. Ids: cat-{n}. The fields (tag/value
        pairs, MARC21-shaped) are held as data, exactly as
        recorded; they are never parsed, and no discovery engine
        reads them (``discovery_engine_here`` is False) —
        discovery remains the core's literal metadata search.
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
        """Create an EDI acquisition order record.

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

    # -- BPM / case management ------------------------------------------
    # Case records over opaque subject references: recorded state
    # events, current state derived at read, decisions under a
    # separation-of-duties guard. No shape can hold case content.

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

    # -- personalization (segments, subjects, rules) -----------------
    # Mirrors the untiered set's adjudicated records form:
    # segment definitions, opaque-ref subject attributes, rules;
    # matching derived at read by _condition_holds.

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

    def register_search_index_reference(self, actor, name, scope_ref):
        """Register an enterprise search indexing engine reference.

        Action: type_write. This build's search stays the core's
        literal substring search over registry metadata; the
        reference records that an indexing engine (Boolean /
        concept / fuzzy / multilingual / hierarchical /
        geospatial) is an external system.
        ``indexing_performed_here`` is False.
        """
        self._require(actor, "type_write", "ext_reference_create")
        _validate_non_empty(scope_ref, "scope_ref")
        return self._create_reference(
            actor, "search_index", name, "ext_reference_create",
            {"indexing_performed_here": False}, {"scope_ref": scope_ref})

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

    def register_workflow_engine_reference(self, actor, name, definition):
        """Register an editorial workflow engine reference.

        Action: type_write. The engine's workflow definition
        (parallel review steps, routing, notification points) is
        held as data on the reference record. Registering it
        changes no core item: the editorial lifecycle mechanics
        stay the core's, and no workflow executes here
        (``executed_here`` is False).
        """
        self._require(actor, "type_write", "ext_reference_create")
        if not isinstance(definition, dict):
            raise ValidationError("definition must be an object")
        return self._create_reference(
            actor, "workflow_engine", name, "ext_reference_create",
            {"executed_here": False},
            {"definition": copy.deepcopy(definition)})

    def register_cdn_reference(self, actor, name):
        """Register a CDN / delivery network reference.

        Action: type_write. Per PLATFORM-LAYER.md decision 6,
        runtime serving is a deployment property; this build
        serves no site (``served_here`` False) and its delivery
        receipts are transport references
        (``reference_transport`` True).
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

    def register_engagement_reference(self, actor, name, program_ref):
        """Register a participant engagement platform reference.

        Action: type_write. The engagement & research platform
        vertical (recruitment, participant portal, longitudinal
        study tooling) is an external system; this reference
        records its channel surface as transport references and
        engages no participant here (``engaged_here`` False).
        """
        self._require(actor, "type_write", "ext_reference_create")
        _validate_non_empty(program_ref, "program_ref")
        return self._create_reference(
            actor, "participant_engagement", name, "ext_reference_create",
            {"reference_transport": True, "engaged_here": False},
            {"program_ref": program_ref})

    def record_engagement_receipt(self, actor, ref_id, channel_ref,
                                  participants_reported):
        """Record an engagement receipt against a reference.

        Action: type_write. The participant count is stored
        exactly as reported by the external platform; no
        participant was engaged by this build.
        """
        self._require(actor, "type_write", "ext_reference_run", ref_id)
        _validate_non_empty(channel_ref, "channel_ref")
        _validate_count(participants_reported, "participants_reported")
        with self._lock:
            record = self._get_reference(ref_id, "participant_engagement")
            receipts = record.setdefault("receipts", [])
            receipts.append({
                "channel_ref": channel_ref,
                "participants_reported": participants_reported,
                "reference_transport": True,
                "reported_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            })
            self._audit(actor, "ext_reference_run", ref_id,
                        details={"family": "participant_engagement"})
            return copy.deepcopy(record)

    def register_hosting_reference(self, actor, name, substrate_label):
        """Register a platform hosting reference.

        Action: site_write. Per PLATFORM-LAYER.md decision 6, a
        fork's hosting substrate (its PaaS runtime) does not
        transfer to the build; the substrate label is recorded
        as the fork's own and nothing is hosted here
        (``hosted_here`` False).
        """
        self._require(actor, "site_write", "ext_reference_create")
        _validate_non_empty(substrate_label, "substrate_label")
        return self._create_reference(
            actor, "platform_hosting", name, "ext_reference_create",
            {"hosted_here": False}, {"substrate_label": substrate_label})
