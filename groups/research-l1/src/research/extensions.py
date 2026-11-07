"""Final GAPS batch extensions for the Research L1 singleton.

Clean-room, standard-library-only extensions for the 11 open
entries of the singleton's GAPS.md section (see ``BATCH.md`` in
the group directory for the per-entry disposition). This module
is a wrapper around :class:`ResearchStore`; every core module is
untouched and byte-identical to the shipped singleton build.

**The founding privacy discipline binds absolutely, here as in
the core — and pointedly for this fork.** The core holds no
review contents, protocol text, screening results, or extracted
study data, and neither does this extension. Studies are opaque
caller-supplied references; protocols hold criterion
*references* as data; screening holds reviewer decisions recorded
verbatim as reported labels; extraction holds field references
and recorded state labels; suggestions are recorded as reported.
No entity shape in this module has a field for a study's title or
abstract text, a protocol's prose, an extracted value, a result,
or a score — those fields **do not exist**. Methods accept only
their named parameters, so a caller cannot smuggle a forbidden
field into a record (pinned by tests: an unexpected keyword
raises ``TypeError``).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — records plus deterministic derivations over
this group's OWN records (core records and extension records):

- The screening "pipeline" records stage decisions and moves
  nothing automatically: a full-text record does not follow from
  a title/abstract record here, and no record advances a study.
- Extraction "from studies" is form definitions (field
  references held as data) plus extraction records carrying field
  references and a recorded state label — never a value.
- Meta-analysis "export" is a manifest record whose view derives
  counts over the held screening/extraction records; it carries
  ``reference_transport: True`` and ``exported_here`` False —
  nothing is exported and no statistic is computed.
- The AI suggestion surface is human-in-the-loop by
  construction: a suggestion is a recorded report, a human
  decision is a separate verbatim record, and recording either
  changes no screening state (pinned by test: the screening
  record is byte-identical before and after).
- Stub-engine entries ship as labeled reference implementations:
  every record carries ``reference_stub: True`` and state
  ``recorded_reference_only``; nothing executes, assesses,
  verifies, or updates a review.

Doctrines carried from the core: derived-never-stored for every
computed value (current protocol version, current term revision,
current suggestion decision, all summaries — each through a
single derivation seam); append-only audit on the core store's
log with ``ext_``-prefixed actions for every successful
mutation, and denied write attempts recorded with a ``:denied``
suffix; RBAC via :mod:`research.access` with the core's existing
actions, enforced before any state change or id allocation, so
a failed operation consumes no id and changes nothing; the
commons membership boundary is enforced through the core store's
own commons access check on every operation.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

SCREENING_STAGES = ("title_abstract", "full_text")
SCREENING_DECISIONS = (
    "reported_include",
    "reported_exclude",
    "reported_undecided",
)
EXTRACTION_STATES = (
    "reported_not_started",
    "reported_in_progress",
    "reported_complete",
)
SUGGESTION_LABELS = (
    "reported_suggest_include",
    "reported_suggest_exclude",
    "reported_suggest_review",
)
HUMAN_DECISIONS = (
    "reported_accepted",
    "reported_rejected",
    "reported_deferred",
)
QUALITY_OUTCOMES = (
    "reported_meets",
    "reported_partial",
    "reported_not_met",
)

_REFERENCE_STATE = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _count(value, what):
    """A non-negative integer count; booleans and floats rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be a non-negative integer" % (what,))
    if value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


def _ref_list(value, what, allow_empty=False):
    """A list of opaque references, duplicates refused."""
    if not isinstance(value, (list, tuple)):
        raise ValidationError("%s must be a list of references" % (what,))
    items = list(value)
    if not items and not allow_empty:
        raise ValidationError("%s must be a non-empty list" % (what,))
    for item in items:
        _non_empty(item, what)
    if len(set(items)) != len(items):
        raise ValidationError("%s must not contain duplicates" % (what,))
    return items


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class ResearchExtensions:
    """Extension surface wrapping one :class:`ResearchStore`."""

    def __init__(self, store):
        self.store = store
        self._programs = {}
        self._program_members = {}
        self._protocols = {}
        self._screening_records = {}
        self._extraction_forms = {}
        self._extraction_records = {}
        self._export_manifests = {}
        self._dictionaries = {}
        self._terms = {}
        self._suggestions = {}
        self._human_decisions = {}
        self._automation_references = {}
        self._automation_events = {}
        self._search_strategies = {}
        self._strategy_executions = {}
        self._quality_criteria = {}
        self._quality_outcomes = {}
        self._quality_verifications = {}
        self._workflow_definitions = {}
        self._workflow_runs = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    def _guard(self, actor, rbac_action, audit_action):
        """Enforce a write permission before any state change.

        Mirrors the core convention (a User-like actor is checked
        via :func:`research.access.require`; a plain string carries
        identity but no role). A denied attempt is recorded on the
        audit log with a ``:denied`` suffix before the error
        propagates; a missing actor is denied outright.
        """
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (rbac_action,))
        if hasattr(actor, "role"):
            try:
                require(actor, rbac_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": rbac_action})
                raise

    @staticmethod
    def _maybe_require(actor, rbac_action):
        if actor is not None and hasattr(actor, "role"):
            require(actor, rbac_action)

    def _commons(self, actor, commons_id):
        """Resolve a commons through the core store, which enforces
        the read permission and the membership boundary (the
        platform admin reaches every commons)."""
        return self.store.get_commons(actor, commons_id)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _check_commons_of(self, actor, record):
        self._commons(actor, record["commons_id"])

    def _program(self, actor, program_id):
        program = self._get(self._programs, program_id, "review program")
        self._check_commons_of(actor, program)
        return program

    def _create(self, table, prefix, fields, actor, audit_action):
        record = {"id": self._next_id(prefix)}
        record.update(fields)
        record["created_by"] = actor_name(actor)
        record["created_utc"] = _utc_now()
        table[record["id"]] = record
        self._audit(actor, audit_action, record["id"])
        return copy.deepcopy(record)

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    def _in_commons(self, table, commons_id):
        return [r for r in table.values() if r["commons_id"] == commons_id]

    def _in_program(self, table, program_id):
        return [r for r in table.values() if r["program_id"] == program_id]

    # -- Review programs, teams & roles (idx 722, built) ----------------
    # Records form: a review program is a registry record inside a
    # commons; its team is a set of membership records binding an
    # opaque member reference to a role label recorded verbatim.
    # No identity data exists in either shape -- a member is an
    # opaque reference and a role is a label, nothing more.

    def create_review_program(self, actor, commons_id, program_ref, label):
        """Create one review program record. Action: record."""
        self._guard(actor, "record", "ext_program_create")
        self._commons(actor, commons_id)
        _non_empty(program_ref, "program_ref")
        _non_empty(label, "label")
        with self._lock:
            for existing in self._in_commons(self._programs, commons_id):
                if existing["program_ref"] == program_ref:
                    raise ValidationError(
                        "program_ref %r is already recorded in this commons"
                        % (program_ref,))
            return self._create(
                self._programs, "prg-",
                {"commons_id": commons_id, "program_ref": program_ref,
                 "label": label},
                actor, "ext_program_create")

    def get_review_program(self, actor, program_id):
        """Return one review program record. Action: read."""
        self._maybe_require(actor, "read")
        program = self._program(actor, program_id)
        return copy.deepcopy(program)

    def list_review_programs(self, actor, commons_id):
        """List review programs in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._programs, commons_id)))

    def add_program_member(self, actor, program_id, member_ref, role_label):
        """Record one team membership: an opaque member reference
        bound to a role label. Action: enter."""
        self._guard(actor, "enter", "ext_program_member_add")
        program = self._program(actor, program_id)
        _non_empty(member_ref, "member_ref")
        _non_empty(role_label, "role_label")
        with self._lock:
            for existing in self._in_program(self._program_members,
                                             program_id):
                if (existing["member_ref"] == member_ref
                        and existing["role_label"] == role_label):
                    raise ValidationError(
                        "member %r already holds role %r in this program"
                        % (member_ref, role_label))
            return self._create(
                self._program_members, "pmb-",
                {"commons_id": program["commons_id"],
                 "program_id": program_id, "member_ref": member_ref,
                 "role_label": role_label},
                actor, "ext_program_member_add")

    def list_program_members(self, actor, program_id):
        """List a program's membership records. Action: read."""
        self._maybe_require(actor, "read")
        self._program(actor, program_id)
        return copy.deepcopy(
            self._sorted(self._in_program(self._program_members,
                                          program_id)))

    def program_summary(self, actor, program_id):
        """Derived counts for one program. Action: read.

        Method ``deterministic_counts`` -- counts over held records
        only; nothing is scored."""
        self._maybe_require(actor, "read")
        program = self._program(actor, program_id)
        members = self._in_program(self._program_members, program_id)
        by_role = {}
        for member in members:
            by_role[member["role_label"]] = \
                by_role.get(member["role_label"], 0) + 1
        protocol_refs = {p["protocol_ref"] for p in
                         self._in_program(self._protocols, program_id)}
        return {"program_id": program_id,
                "commons_id": program["commons_id"],
                "members": len(members),
                "members_by_role": by_role,
                "protocols": len(protocol_refs),
                "method": "deterministic_counts"}

    # -- Review protocol creation (idx 719, built) ----------------------
    # Records form: a protocol record holds criterion REFERENCES
    # as data -- the protocol's prose is never held here
    # (``protocol_text_held_here`` is False). Versions are
    # append-only records under one reference; which version is
    # current is DERIVED at read through the single seam
    # ``_current_protocol_record`` and never stored.

    def _protocol_versions(self, commons_id, protocol_ref):
        versions = [p for p in self._in_commons(self._protocols, commons_id)
                    if p["protocol_ref"] == protocol_ref]
        return sorted(versions, key=lambda p: p["version"])

    def _current_protocol_record(self, versions):
        """The current protocol version: the record with the
        HIGHEST ``version`` in ``versions`` (non-empty, sorted by
        version).

        MUTATION DRILL NOTE: this is the single derivation point
        for protocol currency -- the batch's fresh negative
        control mutates it to read the earliest version (see
        tests/README.md)."""
        return versions[-1]

    def create_protocol(self, actor, program_id, protocol_ref,
                        criteria_refs):
        """Create version 1 of a protocol record. Action: record."""
        self._guard(actor, "record", "ext_protocol_create")
        program = self._program(actor, program_id)
        _non_empty(protocol_ref, "protocol_ref")
        criteria = _ref_list(criteria_refs, "criteria_refs")
        with self._lock:
            if self._protocol_versions(program["commons_id"], protocol_ref):
                raise ValidationError(
                    "protocol_ref %r already exists in this commons; "
                    "revise it instead" % (protocol_ref,))
            return self._create(
                self._protocols, "pro-",
                {"commons_id": program["commons_id"],
                 "program_id": program_id, "protocol_ref": protocol_ref,
                 "version": 1, "criteria_refs": criteria,
                 "protocol_text_held_here": False},
                actor, "ext_protocol_create")

    def revise_protocol(self, actor, protocol_id, criteria_refs):
        """Append the next version of a protocol. Action: record.

        The prior versions are untouched; the new record carries
        ``version`` one higher than the family's current maximum.
        """
        self._guard(actor, "record", "ext_protocol_revise")
        base = self._get(self._protocols, protocol_id, "protocol")
        self._check_commons_of(actor, base)
        criteria = _ref_list(criteria_refs, "criteria_refs")
        with self._lock:
            versions = self._protocol_versions(base["commons_id"],
                                               base["protocol_ref"])
            return self._create(
                self._protocols, "pro-",
                {"commons_id": base["commons_id"],
                 "program_id": base["program_id"],
                 "protocol_ref": base["protocol_ref"],
                 "version": versions[-1]["version"] + 1,
                 "criteria_refs": criteria,
                 "protocol_text_held_here": False},
                actor, "ext_protocol_revise")

    def _protocol_view(self, record):
        versions = self._protocol_versions(record["commons_id"],
                                           record["protocol_ref"])
        current = self._current_protocol_record(versions)
        view = copy.deepcopy(record)
        view["latest_version"] = current["version"]
        view["is_latest"] = record["id"] == current["id"]
        view["criterion_count"] = len(record["criteria_refs"])
        return view

    def get_protocol(self, actor, protocol_id):
        """Return one protocol version record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._protocols, protocol_id, "protocol")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def protocol_view(self, actor, protocol_id):
        """One protocol version plus its derived currency.

        Action: read. ``latest_version`` and ``is_latest`` are
        derived at read and never stored."""
        self._maybe_require(actor, "read")
        record = self._get(self._protocols, protocol_id, "protocol")
        self._check_commons_of(actor, record)
        return self._protocol_view(record)

    def current_protocol(self, actor, commons_id, protocol_ref):
        """The current version's view for a protocol reference.

        Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        versions = self._protocol_versions(commons_id, protocol_ref)
        if not versions:
            raise NotFoundError(
                "protocol not found: %r" % (protocol_ref,))
        return self._protocol_view(
            self._current_protocol_record(versions))

    def list_protocols(self, actor, commons_id, program_id=None):
        """List protocol version records in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        records = self._in_commons(self._protocols, commons_id)
        if program_id is not None:
            records = [p for p in records
                       if p["program_id"] == program_id]
        records.sort(key=lambda p: (p["protocol_ref"], p["version"]))
        return copy.deepcopy(records)

    # -- Screening pipeline (idx 716, built) -----------------------------
    # Records form: a screening record binds an opaque study
    # reference to a stage and a reviewer decision recorded
    # VERBATIM as a reported label. No engine screens anything
    # (``screened_by_engine`` is False) and the pipeline moves
    # nothing automatically: stages are independent records a
    # human workflow drives. Screening binds to the CURRENT
    # protocol version -- screening against a superseded version
    # is refused whole, through the currency seam above.

    def record_screening_decision(self, actor, program_id, protocol_id,
                                  study_ref, stage, decision_label,
                                  reviewer_ref):
        """Record one reviewer's screening decision. Action: record."""
        self._guard(actor, "record", "ext_screening_record")
        program = self._program(actor, program_id)
        protocol = self._get(self._protocols, protocol_id, "protocol")
        _non_empty(study_ref, "study_ref")
        _non_empty(reviewer_ref, "reviewer_ref")
        if stage not in SCREENING_STAGES:
            raise ValidationError(
                "stage must be one of %s" % (", ".join(SCREENING_STAGES),))
        if decision_label not in SCREENING_DECISIONS:
            raise ValidationError(
                "decision_label must be one of %s"
                % (", ".join(SCREENING_DECISIONS),))
        with self._lock:
            if protocol["commons_id"] != program["commons_id"]:
                raise ValidationError(
                    "protocol is in a different commons than the program")
            if protocol["program_id"] != program_id:
                raise ValidationError(
                    "protocol does not belong to this program")
            versions = self._protocol_versions(protocol["commons_id"],
                                               protocol["protocol_ref"])
            if self._current_protocol_record(versions)["id"] != protocol_id:
                raise ValidationError(
                    "protocol %s is superseded; screening binds to the "
                    "current version" % (protocol_id,))
            for existing in self._in_program(self._screening_records,
                                             program_id):
                if (existing["study_ref"] == study_ref
                        and existing["stage"] == stage
                        and existing["reviewer_ref"] == reviewer_ref):
                    raise ValidationError(
                        "reviewer %r already recorded a %s decision for "
                        "study %r" % (reviewer_ref, stage, study_ref))
            return self._create(
                self._screening_records, "scr-",
                {"commons_id": program["commons_id"],
                 "program_id": program_id, "protocol_id": protocol_id,
                 "study_ref": study_ref, "stage": stage,
                 "decision_label": decision_label,
                 "reviewer_ref": reviewer_ref,
                 "screened_by_engine": False},
                actor, "ext_screening_record")

    def get_screening_record(self, actor, record_id):
        """Return one screening record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._screening_records, record_id,
                           "screening record")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_screening_records(self, actor, commons_id, program_id=None,
                               stage=None, study_ref=None):
        """List screening records in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        records = self._in_commons(self._screening_records, commons_id)
        if program_id is not None:
            records = [r for r in records
                       if r["program_id"] == program_id]
        if stage is not None:
            records = [r for r in records if r["stage"] == stage]
        if study_ref is not None:
            records = [r for r in records
                       if r["study_ref"] == study_ref]
        return copy.deepcopy(self._sorted(records))

    def screening_summary(self, actor, program_id):
        """Derived screening counts for one program. Action: read.

        Method ``deterministic_counts`` -- counts of recorded
        decisions by stage and label, and the distinct study
        references seen. Nothing is advanced or decided here."""
        self._maybe_require(actor, "read")
        self._program(actor, program_id)
        records = self._in_program(self._screening_records, program_id)
        by_stage = {}
        for record in records:
            stage_counts = by_stage.setdefault(record["stage"], {})
            label = record["decision_label"]
            stage_counts[label] = stage_counts.get(label, 0) + 1
        return {"program_id": program_id,
                "records": len(records),
                "studies": len({r["study_ref"] for r in records}),
                "by_stage": by_stage,
                "method": "deterministic_counts",
                "advanced_automatically_here": False}

    # -- Data extraction from studies (idx 717, built) -------------------
    # Records form: an extraction form DEFINITION holds field
    # references as data; an extraction record carries field
    # references and a recorded state label. No parameter of any
    # method can accept an extracted VALUE -- values do not exist
    # in this substrate (``values_held_here`` is False).

    def define_extraction_form(self, actor, program_id, form_ref,
                               field_refs):
        """Define one extraction form. Action: record."""
        self._guard(actor, "record", "ext_extraction_form_define")
        program = self._program(actor, program_id)
        _non_empty(form_ref, "form_ref")
        fields = _ref_list(field_refs, "field_refs")
        with self._lock:
            for existing in self._in_commons(self._extraction_forms,
                                             program["commons_id"]):
                if existing["form_ref"] == form_ref:
                    raise ValidationError(
                        "form_ref %r is already defined in this commons"
                        % (form_ref,))
            return self._create(
                self._extraction_forms, "exf-",
                {"commons_id": program["commons_id"],
                 "program_id": program_id, "form_ref": form_ref,
                 "field_refs": fields, "values_held_here": False},
                actor, "ext_extraction_form_define")

    def extraction_form_view(self, actor, form_id):
        """One form definition plus its derived field count.

        Action: read. ``field_count`` is derived at read, never
        stored."""
        self._maybe_require(actor, "read")
        form = self._get(self._extraction_forms, form_id,
                         "extraction form")
        self._check_commons_of(actor, form)
        view = copy.deepcopy(form)
        view["field_count"] = len(form["field_refs"])
        return view

    def record_extraction(self, actor, form_id, study_ref, field_refs,
                          state_label, extractor_ref):
        """Record one extraction state for a study. Action: record.

        ``field_refs`` names the form fields the record addresses;
        every one must be a field of the form. No value is, or can
        be, supplied."""
        self._guard(actor, "record", "ext_extraction_record")
        form = self._get(self._extraction_forms, form_id,
                         "extraction form")
        self._check_commons_of(actor, form)
        _non_empty(study_ref, "study_ref")
        _non_empty(extractor_ref, "extractor_ref")
        fields = _ref_list(field_refs, "field_refs", allow_empty=True)
        if state_label not in EXTRACTION_STATES:
            raise ValidationError(
                "state_label must be one of %s"
                % (", ".join(EXTRACTION_STATES),))
        with self._lock:
            unknown = [f for f in fields if f not in form["field_refs"]]
            if unknown:
                raise ValidationError(
                    "field_refs not in form %s: %s"
                    % (form_id, ", ".join(unknown)))
            return self._create(
                self._extraction_records, "exr-",
                {"commons_id": form["commons_id"],
                 "program_id": form["program_id"], "form_id": form_id,
                 "study_ref": study_ref, "field_refs": fields,
                 "state_label": state_label,
                 "extractor_ref": extractor_ref,
                 "values_held_here": False},
                actor, "ext_extraction_record")

    def list_extraction_records(self, actor, commons_id, form_id=None,
                                study_ref=None):
        """List extraction records in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        records = self._in_commons(self._extraction_records, commons_id)
        if form_id is not None:
            records = [r for r in records if r["form_id"] == form_id]
        if study_ref is not None:
            records = [r for r in records
                       if r["study_ref"] == study_ref]
        return copy.deepcopy(self._sorted(records))

    def extraction_summary(self, actor, program_id):
        """Derived extraction counts for one program. Action: read."""
        self._maybe_require(actor, "read")
        self._program(actor, program_id)
        records = self._in_program(self._extraction_records, program_id)
        by_state = {}
        for record in records:
            label = record["state_label"]
            by_state[label] = by_state.get(label, 0) + 1
        return {"program_id": program_id,
                "records": len(records),
                "studies": len({r["study_ref"] for r in records}),
                "fields_addressed": sum(len(r["field_refs"])
                                         for r in records),
                "by_state": by_state,
                "method": "deterministic_counts",
                "values_held_here": False}

    # -- Meta-analysis export (idx 720, built) ----------------------------
    # Records form: an export manifest is a record ABOUT a would-be
    # export. Its view derives counts over the program's held
    # screening and extraction records at read; the manifest
    # carries ``reference_transport: True`` and
    # ``exported_here`` False -- nothing leaves this substrate and
    # no meta-analytic statistic is computed anywhere.

    def create_export_manifest(self, actor, program_id, manifest_ref):
        """Create one export manifest record. Action: record."""
        self._guard(actor, "record", "ext_export_manifest_create")
        program = self._program(actor, program_id)
        _non_empty(manifest_ref, "manifest_ref")
        with self._lock:
            for existing in self._in_commons(self._export_manifests,
                                             program["commons_id"]):
                if existing["manifest_ref"] == manifest_ref:
                    raise ValidationError(
                        "manifest_ref %r is already recorded in this "
                        "commons" % (manifest_ref,))
            return self._create(
                self._export_manifests, "exp-",
                {"commons_id": program["commons_id"],
                 "program_id": program_id, "manifest_ref": manifest_ref,
                 "reference_transport": True, "exported_here": False,
                 "statistics_computed_here": False},
                actor, "ext_export_manifest_create")

    def export_manifest_view(self, actor, manifest_id):
        """One manifest plus counts derived over held records.

        Action: read. Method ``deterministic_counts``."""
        self._maybe_require(actor, "read")
        manifest = self._get(self._export_manifests, manifest_id,
                             "export manifest")
        self._check_commons_of(actor, manifest)
        program_id = manifest["program_id"]
        screening = self._in_program(self._screening_records, program_id)
        extraction = self._in_program(self._extraction_records, program_id)
        included = {r["study_ref"] for r in screening
                    if r["stage"] == "full_text"
                    and r["decision_label"] == "reported_include"}
        view = copy.deepcopy(manifest)
        view["screening_records"] = len(screening)
        view["studies_screened"] = len({r["study_ref"] for r in screening})
        view["studies_with_full_text_include"] = len(included)
        view["extraction_records"] = len(extraction)
        view["fields_addressed"] = sum(len(r["field_refs"])
                                        for r in extraction)
        view["method"] = "deterministic_counts"
        return view

    def list_export_manifests(self, actor, commons_id):
        """List export manifests in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._export_manifests,
                                          commons_id)))

    # -- Shared dictionary management (idx 721, built) --------------------
    # Records form: a dictionary record plus term records. A term
    # holds an opaque DEFINITION REFERENCE -- the definition text
    # lives elsewhere and is never held here. Revisions are
    # append-only records under one term reference; the current
    # revision is derived at read and never stored.

    def create_dictionary(self, actor, commons_id, dictionary_ref, label):
        """Create one shared dictionary record. Action: record."""
        self._guard(actor, "record", "ext_dictionary_create")
        self._commons(actor, commons_id)
        _non_empty(dictionary_ref, "dictionary_ref")
        _non_empty(label, "label")
        with self._lock:
            for existing in self._in_commons(self._dictionaries, commons_id):
                if existing["dictionary_ref"] == dictionary_ref:
                    raise ValidationError(
                        "dictionary_ref %r is already recorded in this "
                        "commons" % (dictionary_ref,))
            return self._create(
                self._dictionaries, "dic-",
                {"commons_id": commons_id,
                 "dictionary_ref": dictionary_ref, "label": label},
                actor, "ext_dictionary_create")

    def _term_family(self, dictionary_id, term_ref):
        family = [t for t in self._terms.values()
                  if t["dictionary_id"] == dictionary_id
                  and t["term_ref"] == term_ref]
        return sorted(family, key=lambda t: t["revision"])

    @staticmethod
    def _current_term_record(family):
        """The current term revision: the HIGHEST ``revision`` in
        the family. Derived at read, never stored."""
        return family[-1]

    def add_term(self, actor, dictionary_id, term_ref, definition_ref):
        """Add revision 1 of a term. Action: record."""
        self._guard(actor, "record", "ext_term_add")
        dictionary = self._get(self._dictionaries, dictionary_id,
                               "dictionary")
        self._check_commons_of(actor, dictionary)
        _non_empty(term_ref, "term_ref")
        _non_empty(definition_ref, "definition_ref")
        with self._lock:
            if self._term_family(dictionary_id, term_ref):
                raise ValidationError(
                    "term_ref %r already exists in this dictionary; "
                    "revise it instead" % (term_ref,))
            return self._create(
                self._terms, "trm-",
                {"commons_id": dictionary["commons_id"],
                 "dictionary_id": dictionary_id, "term_ref": term_ref,
                 "definition_ref": definition_ref, "revision": 1,
                 "definition_text_held_here": False},
                actor, "ext_term_add")

    def revise_term(self, actor, term_id, definition_ref):
        """Append the next revision of a term. Action: record."""
        self._guard(actor, "record", "ext_term_revise")
        base = self._get(self._terms, term_id, "term")
        self._check_commons_of(actor, base)
        _non_empty(definition_ref, "definition_ref")
        with self._lock:
            family = self._term_family(base["dictionary_id"],
                                       base["term_ref"])
            return self._create(
                self._terms, "trm-",
                {"commons_id": base["commons_id"],
                 "dictionary_id": base["dictionary_id"],
                 "term_ref": base["term_ref"],
                 "definition_ref": definition_ref,
                 "revision": family[-1]["revision"] + 1,
                 "definition_text_held_here": False},
                actor, "ext_term_revise")

    def term_view(self, actor, term_id):
        """One term revision plus its derived currency. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._terms, term_id, "term")
        self._check_commons_of(actor, record)
        family = self._term_family(record["dictionary_id"],
                                   record["term_ref"])
        current = self._current_term_record(family)
        view = copy.deepcopy(record)
        view["latest_revision"] = current["revision"]
        view["is_latest"] = record["id"] == current["id"]
        return view

    def list_terms(self, actor, dictionary_id, current_only=False):
        """List term records in a dictionary. Action: read."""
        self._maybe_require(actor, "read")
        dictionary = self._get(self._dictionaries, dictionary_id,
                               "dictionary")
        self._check_commons_of(actor, dictionary)
        records = [t for t in self._terms.values()
                   if t["dictionary_id"] == dictionary_id]
        if current_only:
            refs = {t["term_ref"] for t in records}
            records = [self._current_term_record(
                self._term_family(dictionary_id, ref)) for ref in refs]
        records.sort(key=lambda t: (t["term_ref"], t["revision"]))
        return copy.deepcopy(records)

    def dictionary_summary(self, actor, dictionary_id):
        """Derived counts for one dictionary. Action: read."""
        self._maybe_require(actor, "read")
        dictionary = self._get(self._dictionaries, dictionary_id,
                               "dictionary")
        self._check_commons_of(actor, dictionary)
        records = [t for t in self._terms.values()
                   if t["dictionary_id"] == dictionary_id]
        return {"dictionary_id": dictionary_id,
                "terms": len({t["term_ref"] for t in records}),
                "revisions": len(records),
                "method": "deterministic_counts"}

    # -- Human-in-the-loop AI suggestion surface (idx 724, built) ---------
    # Records form: a suggestion record holds a label recorded as
    # reported and the source label it arrived under;
    # ``generated_here`` is False -- nothing is generated here. A
    # human decision is a separate record holding the decider's
    # label verbatim. Recording a suggestion or a decision changes
    # NO screening state: the screening record it concerns is
    # byte-identical before and after (pinned by test). The
    # current decision state is derived at read through the single
    # seam ``_current_decision_label`` and never stored.

    def record_suggestion(self, actor, program_id, study_ref,
                          suggestion_label, source_label,
                          screening_record_id=None):
        """Record one AI suggestion as reported. Action: record."""
        self._guard(actor, "record", "ext_suggestion_record")
        program = self._program(actor, program_id)
        _non_empty(study_ref, "study_ref")
        _non_empty(source_label, "source_label")
        if suggestion_label not in SUGGESTION_LABELS:
            raise ValidationError(
                "suggestion_label must be one of %s"
                % (", ".join(SUGGESTION_LABELS),))
        with self._lock:
            if screening_record_id is not None:
                screening = self._get(self._screening_records,
                                      screening_record_id,
                                      "screening record")
                if screening["program_id"] != program_id:
                    raise ValidationError(
                        "screening record does not belong to this program")
            return self._create(
                self._suggestions, "sug-",
                {"commons_id": program["commons_id"],
                 "program_id": program_id, "study_ref": study_ref,
                 "screening_record_id": screening_record_id,
                 "suggestion_label": suggestion_label,
                 "source_label": source_label, "generated_here": False},
                actor, "ext_suggestion_record")

    def record_human_decision(self, actor, suggestion_id, decision_label,
                              decider_ref):
        """Record one human's decision on a suggestion.

        Action: decide. The label is the human's, recorded
        verbatim; the suggestion and any screening record are
        untouched."""
        self._guard(actor, "decide", "ext_human_decision_record")
        suggestion = self._get(self._suggestions, suggestion_id,
                               "suggestion")
        self._check_commons_of(actor, suggestion)
        _non_empty(decider_ref, "decider_ref")
        if decision_label not in HUMAN_DECISIONS:
            raise ValidationError(
                "decision_label must be one of %s"
                % (", ".join(HUMAN_DECISIONS),))
        with self._lock:
            return self._create(
                self._human_decisions, "hdc-",
                {"commons_id": suggestion["commons_id"],
                 "program_id": suggestion["program_id"],
                 "suggestion_id": suggestion_id,
                 "decision_label": decision_label,
                 "decider_ref": decider_ref},
                actor, "ext_human_decision_record")

    def _decision_history(self, suggestion_id):
        history = [d for d in self._human_decisions.values()
                   if d["suggestion_id"] == suggestion_id]
        return self._sorted(history)

    @staticmethod
    def _current_decision_label(history):
        """The current human-decision state: the LATEST recorded
        decision label in ``history``, or ``None`` when no human
        has decided. Derived at read, never stored."""
        if not history:
            return None
        return history[-1]["decision_label"]

    def suggestion_view(self, actor, suggestion_id):
        """One suggestion plus its derived decision state.

        Action: read. ``current_decision`` is the latest recorded
        human decision label, or ``undecided`` when none exists;
        it is derived at read and never stored on the record."""
        self._maybe_require(actor, "read")
        suggestion = self._get(self._suggestions, suggestion_id,
                               "suggestion")
        self._check_commons_of(actor, suggestion)
        history = self._decision_history(suggestion_id)
        current = self._current_decision_label(history)
        view = copy.deepcopy(suggestion)
        view["decision_count"] = len(history)
        view["current_decision"] = \
            current if current is not None else "undecided"
        view["derived"] = True
        return view

    def list_suggestions(self, actor, commons_id, program_id=None):
        """List suggestion records in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        records = self._in_commons(self._suggestions, commons_id)
        if program_id is not None:
            records = [s for s in records
                       if s["program_id"] == program_id]
        return copy.deepcopy(self._sorted(records))

    def suggestion_summary(self, actor, program_id):
        """Derived suggestion counts for one program. Action: read.

        Current-decision counts are derived per suggestion through
        the same seam the view uses."""
        self._maybe_require(actor, "read")
        self._program(actor, program_id)
        records = self._in_program(self._suggestions, program_id)
        by_label = {}
        by_decision = {}
        for record in records:
            label = record["suggestion_label"]
            by_label[label] = by_label.get(label, 0) + 1
            current = self._current_decision_label(
                self._decision_history(record["id"]))
            key = current if current is not None else "undecided"
            by_decision[key] = by_decision.get(key, 0) + 1
        return {"program_id": program_id,
                "suggestions": len(records),
                "by_label": by_label,
                "by_current_decision": by_decision,
                "method": "deterministic_counts",
                "generated_here": False}

    # -- Systematic review automation (idx 714, reference) ----------------
    # Labeled reference implementation: an automation reference
    # records that a living-review automation exists elsewhere;
    # update events are recorded as reported. Nothing here runs,
    # updates a review, or keeps anything "living"
    # (``automation_active_here`` / ``reviews_updated_here``
    # False).

    def record_automation_reference(self, actor, program_id,
                                    automation_ref, source_label):
        """Record one automation reference. Action: record."""
        self._guard(actor, "record", "ext_automation_reference_record")
        program = self._program(actor, program_id)
        _non_empty(automation_ref, "automation_ref")
        _non_empty(source_label, "source_label")
        with self._lock:
            for existing in self._in_commons(
                    self._automation_references, program["commons_id"]):
                if existing["automation_ref"] == automation_ref:
                    raise ValidationError(
                        "automation_ref %r is already recorded in this "
                        "commons" % (automation_ref,))
            return self._create(
                self._automation_references, "aut-",
                {"commons_id": program["commons_id"],
                 "program_id": program_id,
                 "automation_ref": automation_ref,
                 "source_label": source_label,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "automation_active_here": False,
                 "reviews_updated_here": False},
                actor, "ext_automation_reference_record")

    def record_automation_event(self, actor, automation_id, event_label):
        """Record one living-update event as reported.

        Action: record. The event happened elsewhere, if it
        happened; recording it updates nothing here."""
        self._guard(actor, "record", "ext_automation_event_record")
        reference = self._get(self._automation_references, automation_id,
                              "automation reference")
        self._check_commons_of(actor, reference)
        _non_empty(event_label, "event_label")
        with self._lock:
            return self._create(
                self._automation_events, "aue-",
                {"commons_id": reference["commons_id"],
                 "program_id": reference["program_id"],
                 "automation_id": automation_id,
                 "event_label": event_label,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "applied_here": False},
                actor, "ext_automation_event_record")

    def list_automation_references(self, actor, commons_id):
        """List automation references in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._automation_references,
                                          commons_id)))

    def list_automation_events(self, actor, automation_id):
        """List recorded events for one automation reference.

        Action: read."""
        self._maybe_require(actor, "read")
        reference = self._get(self._automation_references, automation_id,
                              "automation reference")
        self._check_commons_of(actor, reference)
        events = [e for e in self._automation_events.values()
                  if e["automation_id"] == automation_id]
        return copy.deepcopy(self._sorted(events))

    # -- Literature search-strategy execution (idx 715, reference) --------
    # Labeled reference implementation: a strategy record holds an
    # opaque QUERY REFERENCE and source references as data -- the
    # strategy text lives elsewhere and is never held or run here
    # (``executed_here`` False). An execution reference records a
    # run as reported, with its result count as reported.

    def record_search_strategy(self, actor, program_id, strategy_ref,
                               query_ref, source_refs):
        """Record one search-strategy reference. Action: record."""
        self._guard(actor, "record", "ext_search_strategy_record")
        program = self._program(actor, program_id)
        _non_empty(strategy_ref, "strategy_ref")
        _non_empty(query_ref, "query_ref")
        sources = _ref_list(source_refs, "source_refs")
        with self._lock:
            for existing in self._in_commons(self._search_strategies,
                                             program["commons_id"]):
                if existing["strategy_ref"] == strategy_ref:
                    raise ValidationError(
                        "strategy_ref %r is already recorded in this "
                        "commons" % (strategy_ref,))
            return self._create(
                self._search_strategies, "sst-",
                {"commons_id": program["commons_id"],
                 "program_id": program_id, "strategy_ref": strategy_ref,
                 "query_ref": query_ref, "source_refs": sources,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "executed_here": False,
                 "strategy_text_held_here": False},
                actor, "ext_search_strategy_record")

    def record_strategy_execution(self, actor, strategy_id, run_label,
                                  results_reported):
        """Record one strategy execution as reported.

        Action: record. ``results_reported`` is a count as
        reported by the external run; nothing was searched here."""
        self._guard(actor, "record", "ext_strategy_execution_record")
        strategy = self._get(self._search_strategies, strategy_id,
                             "search strategy")
        self._check_commons_of(actor, strategy)
        _non_empty(run_label, "run_label")
        _count(results_reported, "results_reported")
        with self._lock:
            return self._create(
                self._strategy_executions, "sex-",
                {"commons_id": strategy["commons_id"],
                 "program_id": strategy["program_id"],
                 "strategy_id": strategy_id, "run_label": run_label,
                 "results_reported": results_reported,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "executed_here": False, "searched_here": False},
                actor, "ext_strategy_execution_record")

    def list_search_strategies(self, actor, commons_id):
        """List search-strategy references in a commons.

        Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._search_strategies,
                                          commons_id)))

    def list_strategy_executions(self, actor, strategy_id):
        """List recorded executions for one strategy. Action: read."""
        self._maybe_require(actor, "read")
        strategy = self._get(self._search_strategies, strategy_id,
                             "search strategy")
        self._check_commons_of(actor, strategy)
        runs = [r for r in self._strategy_executions.values()
                if r["strategy_id"] == strategy_id]
        return copy.deepcopy(self._sorted(runs))

    # -- Quality assessment & verification support (idx 718, reference) ---
    # Labeled reference implementation: criteria sets hold
    # criterion references as data; outcome records hold an
    # assessor's label verbatim as reported; verification records
    # hold a verifier's label as reported. Nothing here assesses
    # or verifies anything (``assessed_here`` / ``verified_here``
    # False) -- this substrate is the records form a quality
    # process's outcomes land in, which is the support the entry
    # names.

    def record_quality_criteria(self, actor, program_id, criteria_set_ref,
                                criteria_refs):
        """Record one quality criteria set. Action: record."""
        self._guard(actor, "record", "ext_quality_criteria_record")
        program = self._program(actor, program_id)
        _non_empty(criteria_set_ref, "criteria_set_ref")
        criteria = _ref_list(criteria_refs, "criteria_refs")
        with self._lock:
            for existing in self._in_commons(self._quality_criteria,
                                             program["commons_id"]):
                if existing["criteria_set_ref"] == criteria_set_ref:
                    raise ValidationError(
                        "criteria_set_ref %r is already recorded in "
                        "this commons" % (criteria_set_ref,))
            return self._create(
                self._quality_criteria, "qac-",
                {"commons_id": program["commons_id"],
                 "program_id": program_id,
                 "criteria_set_ref": criteria_set_ref,
                 "criteria_refs": criteria,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "assessed_here": False},
                actor, "ext_quality_criteria_record")

    def record_quality_outcome(self, actor, criteria_set_id, target_ref,
                               outcome_label, assessor_ref):
        """Record one quality outcome as reported. Action: record."""
        self._guard(actor, "record", "ext_quality_outcome_record")
        criteria = self._get(self._quality_criteria, criteria_set_id,
                             "quality criteria set")
        self._check_commons_of(actor, criteria)
        _non_empty(target_ref, "target_ref")
        _non_empty(assessor_ref, "assessor_ref")
        if outcome_label not in QUALITY_OUTCOMES:
            raise ValidationError(
                "outcome_label must be one of %s"
                % (", ".join(QUALITY_OUTCOMES),))
        with self._lock:
            return self._create(
                self._quality_outcomes, "qao-",
                {"commons_id": criteria["commons_id"],
                 "program_id": criteria["program_id"],
                 "criteria_set_id": criteria_set_id,
                 "target_ref": target_ref,
                 "outcome_label": outcome_label,
                 "assessor_ref": assessor_ref,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "assessed_here": False, "verified_here": False},
                actor, "ext_quality_outcome_record")

    def record_quality_verification(self, actor, outcome_id,
                                    verification_label, verifier_ref):
        """Record one regulator/sponsor verification as reported.

        Action: record. The verification happened elsewhere; this
        record is its landing form."""
        self._guard(actor, "record", "ext_quality_verification_record")
        outcome = self._get(self._quality_outcomes, outcome_id,
                            "quality outcome")
        self._check_commons_of(actor, outcome)
        _non_empty(verification_label, "verification_label")
        _non_empty(verifier_ref, "verifier_ref")
        with self._lock:
            return self._create(
                self._quality_verifications, "qav-",
                {"commons_id": outcome["commons_id"],
                 "program_id": outcome["program_id"],
                 "outcome_id": outcome_id,
                 "verification_label": verification_label,
                 "verifier_ref": verifier_ref,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "verified_here": False},
                actor, "ext_quality_verification_record")

    def quality_summary(self, actor, program_id):
        """Derived counts over quality records. Action: read.

        Method ``deterministic_counts`` -- counts of recorded
        outcome labels; no outcome is computed here."""
        self._maybe_require(actor, "read")
        self._program(actor, program_id)
        outcomes = self._in_program(self._quality_outcomes, program_id)
        by_label = {}
        for outcome in outcomes:
            label = outcome["outcome_label"]
            by_label[label] = by_label.get(label, 0) + 1
        verifications = self._in_program(self._quality_verifications,
                                         program_id)
        return {"program_id": program_id,
                "criteria_sets": len(self._in_program(
                    self._quality_criteria, program_id)),
                "outcomes": len(outcomes),
                "outcomes_by_label": by_label,
                "verifications": len(verifications),
                "method": "deterministic_counts",
                "assessed_here": False, "verified_here": False}

    # -- Customizable review workflows (idx 723, reference) ---------------
    # Labeled reference implementation: a workflow definition
    # holds step references as data; a run record holds a label as
    # reported. Definitions are never executed here
    # (``executed_here`` False), mirroring the substrate rule that
    # registries hold definitions only.

    def record_workflow_definition(self, actor, program_id, workflow_ref,
                                   step_refs):
        """Record one workflow definition. Action: record."""
        self._guard(actor, "record", "ext_workflow_definition_record")
        program = self._program(actor, program_id)
        _non_empty(workflow_ref, "workflow_ref")
        steps = _ref_list(step_refs, "step_refs")
        with self._lock:
            for existing in self._in_commons(self._workflow_definitions,
                                             program["commons_id"]):
                if existing["workflow_ref"] == workflow_ref:
                    raise ValidationError(
                        "workflow_ref %r is already recorded in this "
                        "commons" % (workflow_ref,))
            return self._create(
                self._workflow_definitions, "wfd-",
                {"commons_id": program["commons_id"],
                 "program_id": program_id, "workflow_ref": workflow_ref,
                 "step_refs": steps,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "executed_here": False},
                actor, "ext_workflow_definition_record")

    def record_workflow_run(self, actor, workflow_id, run_label):
        """Record one workflow run as reported. Action: record."""
        self._guard(actor, "record", "ext_workflow_run_record")
        workflow = self._get(self._workflow_definitions, workflow_id,
                             "workflow definition")
        self._check_commons_of(actor, workflow)
        _non_empty(run_label, "run_label")
        with self._lock:
            return self._create(
                self._workflow_runs, "wfr-",
                {"commons_id": workflow["commons_id"],
                 "program_id": workflow["program_id"],
                 "workflow_id": workflow_id, "run_label": run_label,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "executed_here": False},
                actor, "ext_workflow_run_record")

    def list_workflow_definitions(self, actor, commons_id):
        """List workflow definitions in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._workflow_definitions,
                                          commons_id)))

    def list_workflow_runs(self, actor, workflow_id):
        """List recorded runs for one workflow. Action: read."""
        self._maybe_require(actor, "read")
        workflow = self._get(self._workflow_definitions, workflow_id,
                             "workflow definition")
        self._check_commons_of(actor, workflow)
        runs = [r for r in self._workflow_runs.values()
                if r["workflow_id"] == workflow_id]
        return copy.deepcopy(self._sorted(runs))
