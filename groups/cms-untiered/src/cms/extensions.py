"""Final GAPS batch extensions — Untiered Set 14 (CMS).

Records-form implementations and labeled reference implementations
for the twelve open Extended families of this set's union spec,
built over the founding CMS substrate in :mod:`cms.store`. This
module is the only code the batch adds; every core module is
unchanged.

Tier discipline: this set is untiered and this module keeps it
that way. No record, view, or summary in this module carries a
tier, a baseline, an impact level, or an equivalence key or value;
tier stays null, exactly as the set's spec sheets record it.

Honesty labels, per family:

- **Templates & fragments** are definition records. A template
  body is held as data and versioned; placeholder names are
  derived at read time by scanning the held text. Nothing is
  rendered and nothing is served: every record carries
  ``rendered_here: False``.
- **Personalization** is audience segment definitions (match
  conditions held as data), subject attribute records keyed by
  opaque references, and rule records binding a segment to a
  content reference. Matching is *derived at read time* by the
  single seam :func:`_condition_holds` over recorded attributes:
  deterministic presence/equality checks and counts of matched
  conditions. No optimization is computed, no visitor is tracked,
  and no content is served (``served_here: False``,
  ``optimized_here: False`` on rule views).
- **Versioning depth** is records over the core's own revision
  and asset registries: version-chain views derived at read time
  from core revision records, comparison records whose labels
  are recorded verbatim (no diff is computed over content —
  ``diff_computed_here: False``), and asset version groups
  linking core asset records under recorded version labels.
- **Low-code definitions** are application/form definition
  records held as data and versioned. Nothing executes and
  nothing renders (``executed_here: False``,
  ``rendered_here: False``).
- **Multi-site / multilingual depth** is locale records over
  core sites with item linkages; every count (locales per site,
  linked items per locale, per-site registry counts) is derived
  at read time, never stored.
- The seven engine families (enterprise search indexing,
  editorial workflow engines, document generation, identity
  federation/SSO, headless delivery, CDN/runtime serving,
  platform hosting) ship as **labeled reference
  implementations**: records carry ``reference_stub: True`` (and
  ``reference_transport: True`` where the family is a transport),
  and each family's own not-here flag is False. Identity hooks
  follow PLATFORM-LAYER.md decision 1 (``hook_only: True``,
  ``identity_provider: False`` — this build is not an IdP);
  hosting and CDN records follow decision 6 (``hosted_here`` /
  ``served_here`` False — the substrate a fork runs on does not
  transfer).

Access control reuses the founding permission matrix — no new
actions exist. The mapping is: template, fragment, low-code
definition, and stub-reference writes use ``type_write`` (registry
configuration) with ``type_read`` reads; audience segment,
subject-attribute, and personalization-rule writes use
``tag_write`` with ``tag_read`` reads; comparison records use
``item_edit`` / ``item_read``; asset version groups use
``asset_write`` / ``asset_read``; locale records and the
platform-level hook/hosting records use ``site_write`` /
``site_read``; derived summaries use ``report_read``. Write
enforcement mirrors the core store: a missing actor is denied,
a User-like actor is checked against the matrix, and denials are
recorded in the core audit log as ``<action>:denied``. Reads
enforce only when a User-like actor is supplied, as in the core.

Ids are sequential per object type with fixed prefixes
(``tpl-``, ``seg-``, ``subj-``, ``prule-``, ``cmp-``, ``avg-``,
``avm-``, ``def-``, ``loc-``, ``ref-``). A failed operation
consumes no id and changes nothing: all validation happens
before any mutation. All timestamps are UTC ISO-8601. Records
returned are copies; mutating a returned record changes nothing
stored.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

__all__ = ["CmsExtensions"]


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


_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}")


def _condition_holds(condition, attributes):
    """Single derivation seam for personalization matching.

    True iff one recorded match ``condition`` holds against a
    subject's recorded ``attributes``: ``present`` requires the
    key to be recorded; ``equals`` requires the recorded value
    to equal the condition's value exactly. This is the seam the
    batch's fresh negative control mutates (see tests/README.md):
    if condition checks wave through, subjects match segments
    they do not satisfy.
    """
    key = condition["key"]
    if condition["op"] == "present":
        return key in attributes
    return attributes.get(key) == condition["value"]


class CmsExtensions:
    """Extension register wrapping a core :class:`cms.store.CmsStore`."""

    def __init__(self, store):
        self.store = store
        self.audit = getattr(store, "audit", None)
        self._templates = {}
        self._segments = {}
        self._subjects = {}
        self._rules = {}
        self._comparisons = {}
        self._asset_groups = {}
        self._definitions = {}
        self._locales = {}
        self._references = {}
        self._counters = {
            "tpl": 0, "seg": 0, "subj": 0, "prule": 0, "cmp": 0,
            "avg": 0, "def": 0, "loc": 0, "ref": 0,
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

    # -- templates & fragments (rendering/templating gap) -----------

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

    # -- personalization (segments, subjects, rules) -----------------

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
        nowhere.
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

    # -- versioning depth (chains, comparisons, asset groups) --------

    def item_version_chain(self, item_id, actor=None):
        """Derive an item's version chain from core revision records.

        Action: item_read. The chain is computed at read time
        from the core store's revision registry; the stored item
        and revision records are unchanged.
        """
        self._require_read(actor, "item_read", "ext_version_chain")
        item = self.store.get_item(item_id, actor=actor)
        revisions = self.store.list_revisions(item_id, actor=actor)
        chain = [
            {
                "revision": rev["revision"],
                "revision_id": rev["id"],
                "edited_by": rev["edited_by"],
                "created_utc": rev["created_utc"],
            }
            for rev in revisions
        ]
        return {
            "item_id": item_id,
            "current_revision": item["revision"],
            "chain_length": len(chain),
            "chain": chain,
        }

    def record_comparison(self, actor, item_id, from_revision, to_revision,
                          label):
        """Record a comparison between two revisions of an item.

        Action: item_edit. Ids: cmp-{n}. Both revision numbers
        must exist in the core revision registry for the item.
        The ``label`` is recorded verbatim as the comparison's
        recorded outcome; no diff is computed over the revisions'
        content (``diff_computed_here`` is False).
        """
        self._require(actor, "item_edit", "ext_comparison_record", item_id)
        _validate_non_empty(label, "comparison label")
        for number in (from_revision, to_revision):
            if not isinstance(number, int) or isinstance(number, bool) \
                    or number < 1:
                raise ValidationError("revision numbers must be positive ints")
        revisions = self.store.list_revisions(item_id, actor=actor)
        known = {rev["revision"] for rev in revisions}
        for number in (from_revision, to_revision):
            if number not in known:
                raise ValidationError(
                    "item %r has no revision %r" % (item_id, number))
        with self._lock:
            comparison_id = self._next_id("cmp")
            record = {
                "id": comparison_id,
                "item_id": item_id,
                "from_revision": from_revision,
                "to_revision": to_revision,
                "label": label,
                "diff_computed_here": False,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._comparisons[comparison_id] = record
            self._audit(actor, "ext_comparison_record", comparison_id,
                        details={"item_id": item_id})
            return copy.deepcopy(record)

    def list_comparisons(self, item_id=None, actor=None):
        """Return comparison records sorted by id. Action: item_read."""
        self._require_read(actor, "item_read", "ext_comparison_read")
        with self._lock:
            records = sorted(self._comparisons.values(),
                             key=lambda r: _id_num(r["id"]))
            if item_id is not None:
                records = [r for r in records if r["item_id"] == item_id]
            return [copy.deepcopy(r) for r in records]

    def create_asset_version_group(self, actor, name):
        """Create an asset version group. Action: asset_write. Ids: avg-{n}."""
        self._require(actor, "asset_write", "ext_asset_group_create")
        _validate_non_empty(name, "asset version group name")
        with self._lock:
            group_id = self._next_id("avg")
            record = {
                "id": group_id,
                "name": name,
                "members": [],
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._asset_groups[group_id] = record
            self._audit(actor, "ext_asset_group_create", group_id)
            return self._asset_group_view(record)

    def add_asset_version(self, actor, group_id, asset_id, version_label):
        """Link a core asset into a group under a recorded version label.

        Action: asset_write. The asset must exist in the core
        registry; one version entry per asset per group. The
        label is recorded verbatim — it asserts the filer's
        versioning of the asset, and no file content is compared
        or stored here (the core registry holds checksums only).
        """
        self._require(actor, "asset_write", "ext_asset_version_add", group_id)
        _validate_non_empty(version_label, "version_label")
        self.store.get_asset(asset_id, actor=actor)
        with self._lock:
            group = self._get(self._asset_groups, group_id,
                              "asset version group")
            if any(m["asset_id"] == asset_id for m in group["members"]):
                raise ValidationError(
                    "asset %r is already a member of group %r"
                    % (asset_id, group_id))
            group["members"].append({
                "asset_id": asset_id,
                "version_label": version_label,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            })
            self._audit(actor, "ext_asset_version_add", group_id,
                        details={"asset_id": asset_id})
            return self._asset_group_view(group)

    @staticmethod
    def _asset_group_view(group):
        view = copy.deepcopy(group)
        view["member_count"] = len(group["members"])
        view["version_labels"] = [m["version_label"] for m in group["members"]]
        return view

    def get_asset_version_group(self, group_id, actor=None):
        """Return one asset version group view. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_asset_group_read")
        with self._lock:
            return self._asset_group_view(
                self._get(self._asset_groups, group_id, "asset version group"))

    def list_asset_version_groups(self, actor=None):
        """Return asset version group views sorted by id. Action: asset_read."""
        self._require_read(actor, "asset_read", "ext_asset_group_read")
        with self._lock:
            records = sorted(self._asset_groups.values(),
                             key=lambda r: _id_num(r["id"]))
            return [self._asset_group_view(r) for r in records]

    # -- low-code application & form definitions ----------------------

    def create_definition(self, actor, kind, name, definition):
        """Create a low-code application or form definition record.

        Action: type_write. Ids: def-{n}. The definition is held
        as data (deep-copied) and versioned on update; it is
        never executed and never rendered.
        """
        self._require(actor, "type_write", "ext_definition_create")
        _validate_non_empty(name, "definition name")
        if kind not in ("application", "form"):
            raise ValidationError("kind must be 'application' or 'form'")
        if not isinstance(definition, dict):
            raise ValidationError("definition must be an object")
        with self._lock:
            definition_id = self._next_id("def")
            now = _utc_now()
            record = {
                "id": definition_id,
                "kind": kind,
                "name": name,
                "definition": copy.deepcopy(definition),
                "version": 1,
                "history": [],
                "executed_here": False,
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._definitions[definition_id] = record
            self._audit(actor, "ext_definition_create", definition_id,
                        details={"kind": kind})
            return copy.deepcopy(record)

    def update_definition(self, actor, definition_id, definition):
        """Replace a definition, versioning the prior definition as data.

        Action: type_write.
        """
        self._require(actor, "type_write", "ext_definition_update",
                      definition_id)
        if not isinstance(definition, dict):
            raise ValidationError("definition must be an object")
        with self._lock:
            record = self._get(self._definitions, definition_id, "definition")
            record["history"].append(
                {"version": record["version"],
                 "definition": record["definition"]})
            record["definition"] = copy.deepcopy(definition)
            record["version"] += 1
            record["updated_utc"] = _utc_now()
            self._audit(actor, "ext_definition_update", definition_id,
                        details={"version": record["version"]})
            return copy.deepcopy(record)

    def get_definition(self, definition_id, actor=None):
        """Return one definition record. Action: type_read."""
        self._require_read(actor, "type_read", "ext_definition_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._definitions, definition_id, "definition"))

    def list_definitions(self, actor=None, kind=None):
        """Return definition records sorted by id. Action: type_read."""
        self._require_read(actor, "type_read", "ext_definition_read")
        with self._lock:
            records = sorted(self._definitions.values(),
                             key=lambda r: _id_num(r["id"]))
            if kind is not None:
                records = [r for r in records if r["kind"] == kind]
            return [copy.deepcopy(r) for r in records]

    # -- multi-site & multilingual operations depth -------------------

    def create_locale(self, actor, site_id, code, label=""):
        """Create a locale record for a core site.

        Action: site_write. Ids: loc-{n}. The site must exist in
        the core registry; locale codes are unique per site.
        Content linkage counts are derived at read time.
        """
        self._require(actor, "site_write", "ext_locale_create", site_id)
        _validate_non_empty(code, "locale code")
        _validate_text(label, "locale label")
        self.store.get_site(site_id, actor=actor)
        with self._lock:
            for rec in self._locales.values():
                if rec["site_id"] == site_id and rec["code"] == code:
                    raise ValidationError(
                        "site %r already has locale %r" % (site_id, code))
            locale_id = self._next_id("loc")
            record = {
                "id": locale_id,
                "site_id": site_id,
                "code": code,
                "label": label,
                "item_ids": [],
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._locales[locale_id] = record
            self._audit(actor, "ext_locale_create", locale_id,
                        details={"site_id": site_id, "code": code})
            return self._locale_view(record)

    def link_item_to_locale(self, actor, locale_id, item_id):
        """Link a core item to a locale record.

        Action: site_write. The item must exist in the core
        registry and belong to the locale's site; duplicate links
        are rejected. The linkage is a record — no localized
        content is produced here.
        """
        self._require(actor, "site_write", "ext_locale_link", locale_id)
        item = self.store.get_item(item_id, actor=actor)
        with self._lock:
            locale = self._get(self._locales, locale_id, "locale")
            if item["site_id"] != locale["site_id"]:
                raise ValidationError(
                    "item %r does not belong to site %r"
                    % (item_id, locale["site_id"]))
            if item_id in locale["item_ids"]:
                raise ValidationError(
                    "item %r is already linked to locale %r"
                    % (item_id, locale_id))
            locale["item_ids"].append(item_id)
            self._audit(actor, "ext_locale_link", locale_id,
                        details={"item_id": item_id})
            return self._locale_view(locale)

    @staticmethod
    def _locale_view(record):
        view = copy.deepcopy(record)
        view["linked_item_count"] = len(record["item_ids"])
        return view

    def get_locale(self, locale_id, actor=None):
        """Return one locale record view. Action: site_read."""
        self._require_read(actor, "site_read", "ext_locale_read")
        with self._lock:
            return self._locale_view(
                self._get(self._locales, locale_id, "locale"))

    def list_locales(self, site_id=None, actor=None):
        """Return locale record views sorted by id. Action: site_read."""
        self._require_read(actor, "site_read", "ext_locale_read")
        with self._lock:
            records = sorted(self._locales.values(),
                             key=lambda r: _id_num(r["id"]))
            if site_id is not None:
                records = [r for r in records if r["site_id"] == site_id]
            return [self._locale_view(r) for r in records]

    def site_locale_summary(self, site_id, actor=None):
        """Derive a site's locale/linkage counts at read time.

        Action: report_read. Counts only, computed from the
        locale records and the core registry; stored nowhere.
        """
        self._require_read(actor, "report_read", "ext_locale_summary")
        self.store.get_site(site_id, actor=actor)
        with self._lock:
            locales = [r for r in self._locales.values()
                       if r["site_id"] == site_id]
            linked = set()
            for rec in locales:
                linked.update(rec["item_ids"])
            items = self.store.list_items(site_id=site_id, actor=actor)
            return {
                "site_id": site_id,
                "locale_count": len(locales),
                "locales": sorted(rec["code"] for rec in locales),
                "linked_item_count": len(linked),
                "site_item_count": len(items),
            }

    def multi_site_summary(self, actor=None):
        """Derive per-site operations counts across the registry.

        Action: report_read. For every core site: sections and
        items from the core registry, locales and linked items
        from this module — all computed at read time.
        """
        self._require_read(actor, "report_read", "ext_multi_site_summary")
        sites = self.store.list_sites(actor=actor)
        summary = []
        for site in sites:
            sections = self.store.list_sections(site["id"], actor=actor)
            items = self.store.list_items(site_id=site["id"], actor=actor)
            with self._lock:
                locales = [r for r in self._locales.values()
                           if r["site_id"] == site["id"]]
                linked = set()
                for rec in locales:
                    linked.update(rec["item_ids"])
            summary.append({
                "site_id": site["id"],
                "section_count": len(sections),
                "item_count": len(items),
                "locale_count": len(locales),
                "linked_item_count": len(linked),
            })
        return {"sites": summary, "site_count": len(summary)}

    # -- labeled reference implementations (stub engines) -------------

    def _create_reference(self, actor, family, name, write_action,
                          audit_action, flags, extra=None):
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
        reference records that an indexing engine is an external
        system. ``indexing_performed_here`` is False.
        """
        self._require(actor, "type_write", "ext_reference_create")
        _validate_non_empty(scope_ref, "scope_ref")
        return self._create_reference(
            actor, "search_index", name, "type_write", "ext_reference_create",
            {"indexing_performed_here": False}, {"scope_ref": scope_ref})

    def record_index_run_reference(self, actor, ref_id, documents_reported):
        """Record an engine-reported indexing run against a reference.

        Action: type_write. The document count is stored exactly
        as reported by the external engine; nothing was indexed
        here.
        """
        self._require(actor, "type_write", "ext_reference_run", ref_id)
        if not isinstance(documents_reported, int) \
                or isinstance(documents_reported, bool) \
                or documents_reported < 0:
            raise ValidationError(
                "documents_reported must be a non-negative int")
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

        Action: type_write. The engine's workflow definition is
        held as data on the reference record. Registering it
        changes no core item: the editorial lifecycle mechanics
        stay the core's, and no workflow executes here
        (``executed_here`` is False).
        """
        self._require(actor, "type_write", "ext_reference_create")
        if not isinstance(definition, dict):
            raise ValidationError("definition must be an object")
        return self._create_reference(
            actor, "workflow_engine", name, "type_write",
            "ext_reference_create",
            {"executed_here": False},
            {"definition": copy.deepcopy(definition)})

    def register_document_generation_reference(self, actor, name, source_ref):
        """Register a document generation engine reference.

        Action: type_write. Document generation is the zero-claim
        fork's whole function and has no family in this set's
        taxonomy; the reference records it as an external engine.
        No document is generated here (``generated_here`` False).
        """
        self._require(actor, "type_write", "ext_reference_create")
        _validate_non_empty(source_ref, "source_ref")
        return self._create_reference(
            actor, "document_generation", name, "type_write",
            "ext_reference_create",
            {"generated_here": False}, {"source_ref": source_ref})

    def record_generation_reference(self, actor, ref_id, package_ref):
        """Record an engine-reported generated package reference.

        Action: type_write. Only the opaque package reference is
        recorded; the package itself was produced by the external
        engine and is not held here.
        """
        self._require(actor, "type_write", "ext_reference_run", ref_id)
        _validate_non_empty(package_ref, "package_ref")
        with self._lock:
            record = self._get_reference(ref_id, "document_generation")
            packages = record.setdefault("packages", [])
            packages.append({
                "package_ref": package_ref,
                "reported_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            })
            self._audit(actor, "ext_reference_run", ref_id,
                        details={"family": "document_generation"})
            return copy.deepcopy(record)

    def register_identity_hook(self, actor, name, protocol_label):
        """Register an identity federation / SSO hook record.

        Action: site_write. Per PLATFORM-LAYER.md decision 1,
        identity provision stays with the embedding organization:
        this record is a hook (``hook_only`` True) and this build
        is not an identity provider (``identity_provider``
        False). The protocol label (for example "SAML 2.0") is
        recorded verbatim as the fork documents it.
        """
        self._require(actor, "site_write", "ext_reference_create")
        _validate_non_empty(protocol_label, "protocol_label")
        return self._create_reference(
            actor, "identity_federation", name, "site_write",
            "ext_reference_create",
            {"hook_only": True, "identity_provider": False},
            {"protocol_label": protocol_label})

    def register_headless_delivery_reference(self, actor, name):
        """Register a headless delivery / integration engine reference.

        Action: type_write. The build's own REST API over the
        registry is Core; headless delivery to external channels
        is an external system, recorded here as a reference with
        transport receipts (``reference_transport`` True) and
        nothing delivered (``delivered_here`` False).
        """
        self._require(actor, "type_write", "ext_reference_create")
        return self._create_reference(
            actor, "headless_delivery", name, "type_write",
            "ext_reference_create",
            {"reference_transport": True, "delivered_here": False})

    def record_delivery_receipt(self, actor, ref_id, channel_ref):
        """Record a transport receipt against a headless reference.

        Action: type_write. The receipt records that the external
        delivery system reported a delivery against an opaque
        channel reference; nothing was delivered by this build.
        """
        self._require(actor, "type_write", "ext_reference_run", ref_id)
        _validate_non_empty(channel_ref, "channel_ref")
        with self._lock:
            record = self._get_reference(ref_id, "headless_delivery")
            receipts = record.setdefault("receipts", [])
            receipts.append({
                "channel_ref": channel_ref,
                "reference_transport": True,
                "reported_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            })
            self._audit(actor, "ext_reference_run", ref_id,
                        details={"family": "headless_delivery"})
            return copy.deepcopy(record)

    def register_cdn_reference(self, actor, name):
        """Register a CDN / delivery network reference.

        Action: type_write. Per PLATFORM-LAYER.md decision 6,
        runtime serving is a deployment property; this build
        serves no site (``served_here`` False).
        """
        self._require(actor, "type_write", "ext_reference_create")
        return self._create_reference(
            actor, "cdn_delivery", name, "type_write",
            "ext_reference_create",
            {"reference_transport": True, "served_here": False})

    def register_hosting_reference(self, actor, name, substrate_label):
        """Register a platform hosting reference.

        Action: site_write. Per PLATFORM-LAYER.md decision 6, a
        fork's hosting substrate does not transfer to the build;
        the substrate label is recorded as the fork's own and
        nothing is hosted here (``hosted_here`` False).
        """
        self._require(actor, "site_write", "ext_reference_create")
        _validate_non_empty(substrate_label, "substrate_label")
        return self._create_reference(
            actor, "platform_hosting", name, "site_write",
            "ext_reference_create",
            {"hosted_here": False}, {"substrate_label": substrate_label})
