"""Final GAPS batch extensions for the Communication L1 singleton.

Clean-room, standard-library-only records extensions for the 8 open
entries of this singleton's union spec gap list (the fork's excess
over the messaging substrate): 4 built as in-substrate records plus
deterministic derivations over the core's own records, and 4 shipped
as labeled reference implementations. See ``BATCH.md`` in the group
directory for the per-entry disposition.

Design, following the core's doctrines and this group's baseline
(Low / L1, written fresh for this tier in UNION-SPEC.md):

- This module is a wrapper around :class:`CommStore`; the core
  modules are untouched (byte-identical). Contact, group, template,
  and message existence is always read through the core store's
  public API, never re-implemented.
- RBAC goes through :mod:`comm.access` exactly as the core
  enforces it: the extension maps each of its operations onto an
  existing core action (the core action set is fixed), checks it
  *before* any state change or id allocation for User-like actors,
  and records denied attempts on the core audit log with the
  extension action name suffixed ``:denied``. Extension record
  writes map to the core ``message_compose`` action (the
  substrate's produce-records write); execution-channel
  configuration maps to ``channel_write``, matching the core's
  channel discipline (admin only); reads map to ``records_read``.
  Plain-string actors carry identity but no role, mirroring the
  core convention.
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``.
- Records hold opaque references, labels, and core record ids
  only -- never message contents. There is no parameter anywhere
  in this module that could accept a message subject or body, and
  no record shape carries one. The category's standing discipline
  (records are metadata and references, never contents) binds the
  extension surface exactly as it binds the core.
- Derived values are computed at read and never stored: a
  campaign's current lifecycle state and an interaction's current
  outcome derive from append-only records by the latest-record
  seam; segment membership derives from the segment's criteria
  over the core directory by the seam ``_criteria_match`` (the
  batch's fresh negative control); profile contact sets, report
  figures, and operation counts likewise derive at read. Stored
  records carry no derived key.
- Nothing here executes against an external system, transmits
  anything, or resolves an identity. The four stub-engine
  families ship as labeled reference implementations: every
  record they create carries ``reference_stub: True``. Campaign
  sends and channel executions bind core messages and carry
  ``reference_transport: True`` with ``transmitted_here: False``:
  the core's labelled reference transport remains the only
  transport, and recording a send or an execution changes no
  core delivery.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import KNOWN_CHANNEL_KINDS

CAMPAIGN_STATES = ("draft", "scheduled", "active", "paused",
                   "completed", "cancelled")
KNOWN_CAMPAIGN_STATES = frozenset(CAMPAIGN_STATES)
SEGMENT_CRITERION_KINDS = ("has_channel_kind", "in_group", "name_contains")
KNOWN_SEGMENT_CRITERION_KINDS = frozenset(SEGMENT_CRITERION_KINDS)
EXECUTION_KINDS = ("email", "sms", "voice", "push", "postal")
KNOWN_EXECUTION_KINDS = frozenset(EXECUTION_KINDS)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _one_of(value, known, names, what):
    if value not in known:
        raise ValidationError("%s must be one of %s" % (what, ", ".join(names)))
    return value


def _validate_iso(value, what):
    """Validate an ISO-8601 datetime string (mirrors the core)."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 datetime string" % (what,))
    text = value.strip()
    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(
            "%s is not a valid ISO-8601 datetime: %r" % (what, value)) from exc
    return value


def _string_list(value, what):
    """A list of non-empty strings, deduplicated, order-stable."""
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValidationError("%s must be a list of strings" % (what,))
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(
                "each entry in %s must be a non-empty string" % (what,))
        if item not in result:
            result.append(item)
    return result


def _steps(value, allowed_optional, what):
    """Validate a steps-as-data list (campaign / workflow steps).

    Each step is a dict with a non-empty ``label`` and, optionally,
    only the keys in ``allowed_optional`` (each a non-empty string,
    except ``channel_kind`` which must be a known channel kind).
    Steps are held verbatim as data; nothing executes them.
    """
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValidationError("%s must be a list of step dicts" % (what,))
    result = []
    for item in value:
        if not isinstance(item, dict):
            raise ValidationError("each entry in %s must be a dict" % (what,))
        extra = set(item) - {"label"} - set(allowed_optional)
        if extra:
            raise ValidationError(
                "unknown keys in %s step: %s"
                % (what, ", ".join(sorted(extra))))
        step = {"label": _non_empty(item.get("label"), "step label")}
        for key in allowed_optional:
            if key in item:
                if key == "channel_kind":
                    step[key] = _one_of(item[key], KNOWN_CHANNEL_KINDS,
                                        tuple(sorted(KNOWN_CHANNEL_KINDS)),
                                        "step channel_kind")
                else:
                    step[key] = _non_empty(item[key], "step %s" % (key,))
        result.append(step)
    return result


def _criteria(value):
    """Validate audience-segment criteria (held as data).

    Each criterion is a dict with exactly ``kind`` and ``value``:
    ``has_channel_kind`` (value a known channel kind), ``in_group``
    (value a core group id; existence is checked by the caller), or
    ``name_contains`` (value a substring matched case-insensitively
    against contact names). A contact is a segment member only when
    every criterion holds (AND semantics).
    """
    if not isinstance(value, (list, tuple)) or not value:
        raise ValidationError("criteria must be a non-empty list")
    result = []
    for item in value:
        if not isinstance(item, dict):
            raise ValidationError("each criterion must be a dict")
        extra = set(item) - {"kind", "value"}
        if extra:
            raise ValidationError(
                "unknown keys in criterion: %s" % (", ".join(sorted(extra)),))
        kind = item.get("kind")
        if kind not in KNOWN_SEGMENT_CRITERION_KINDS:
            raise ValidationError(
                "criterion kind must be one of %s"
                % (", ".join(SEGMENT_CRITERION_KINDS),))
        val = _non_empty(item.get("value"), "criterion value")
        if kind == "has_channel_kind" and val not in KNOWN_CHANNEL_KINDS:
            raise ValidationError("unknown channel kind: %r" % (val,))
        result.append({"kind": kind, "value": val})
    return result


def _criterion_holds(criterion, contact, group_members):
    """Evaluate one criterion against one core contact record."""
    kind = criterion["kind"]
    if kind == "has_channel_kind":
        return criterion["value"] in contact["addresses"]
    if kind == "in_group":
        return contact["id"] in group_members.get(criterion["value"], set())
    if kind == "name_contains":
        return criterion["value"].lower() in contact["name"].lower()
    return False


class CommExtensions:
    """GAPS-batch extension surface over a core CommStore."""

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

        Mirrors the core store: an actor must be present; User-like
        actors are checked against the core permission matrix before
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

    def _create(self, kind, prefix, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            self._audit(actor, audit_action, record_id,
                        details={"kind": kind})
            return copy.deepcopy(record)

    def _get(self, kind, record_id):
        record = self._records.get((kind, record_id))
        if record is None:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id):
        return copy.deepcopy(self._get(kind, record_id))

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

    def _contact(self, contact_id):
        """Return the core contact record (NotFoundError if absent)."""
        return self.store.get_contact(contact_id)

    @staticmethod
    def _latest_record(records):
        """The latest-recorded record of an append-only list, or None.

        The single derivation point behind the campaign lifecycle
        view and the interaction outcome view: current state is the
        latest recorded state/outcome record; nothing derived is
        stored on the parent record.
        """
        if not records:
            return None
        return records[-1]

    # -- Campaign orchestration (reference implementation) ------------
    # A campaign is a definition held as data (name, steps, channel
    # kinds, optional core template binding) plus append-only
    # lifecycle state records and send records binding the campaign
    # to core messages. The orchestration engine itself -- visual
    # authoring, journey execution -- does not exist here: every
    # record carries reference_stub: True, the registry never
    # executes a definition, and a send record dispatches nothing
    # (the core's own dispatch, through the labelled reference
    # transport, remains the only dispatch).

    def define_campaign(self, name, actor, steps=None, channel_kinds=None,
                        template_id=None):
        """Define a campaign (definition as data). Action:
        message_compose. Audit: ext_campaign_define."""
        self._guard(actor, "message_compose", "ext_campaign_define")
        _non_empty(name, "campaign name")
        steps = _steps(steps, ("channel_kind", "template_id"),
                       "campaign steps")
        kinds = []
        if channel_kinds is not None:
            if not isinstance(channel_kinds, (list, tuple)) \
                    or not channel_kinds:
                raise ValidationError(
                    "channel_kinds must be a non-empty list")
            for kind in channel_kinds:
                _one_of(kind, KNOWN_CHANNEL_KINDS,
                        tuple(sorted(KNOWN_CHANNEL_KINDS)), "channel kind")
                if kind not in kinds:
                    kinds.append(kind)
        if template_id is not None:
            self.store.get_template(template_id)
        return self._create(
            "campaign_definition", "cmp",
            {"name": name, "steps": steps, "channel_kinds": kinds,
             "template_id": template_id,
             "reference_stub": True,
             "definition_only": True,
             "orchestrated_here": False,
             "executed_here": False},
            actor, "ext_campaign_define")

    def list_campaigns(self, actor=None):
        """Return campaign definitions in creation order."""
        self._guard_read(actor, "records_read", "ext_campaign_list")
        return self._list("campaign_definition")

    def get_campaign(self, campaign_id, actor=None):
        """Return one campaign definition."""
        self._guard_read(actor, "records_read", "ext_campaign_get",
                         target=campaign_id)
        return self._fetch("campaign_definition", campaign_id)

    def record_campaign_state(self, campaign_id, state, actor):
        """Record one lifecycle state for a campaign (append-only).

        Action: message_compose. Audit: ext_campaign_state.
        """
        self._guard(actor, "message_compose", "ext_campaign_state",
                    target=campaign_id)
        _one_of(state, KNOWN_CAMPAIGN_STATES, CAMPAIGN_STATES,
                "campaign state")
        self._get("campaign_definition", campaign_id)
        return self._create(
            "campaign_state", "cst",
            {"campaign_id": campaign_id, "state": state,
             "reference_stub": True},
            actor, "ext_campaign_state")

    def list_campaign_states(self, campaign_id, actor=None):
        """Return a campaign's state records in recording order."""
        self._guard_read(actor, "records_read", "ext_campaign_state_list",
                         target=campaign_id)
        self._get("campaign_definition", campaign_id)
        return self._list("campaign_state", campaign_id=campaign_id)

    def record_campaign_send(self, campaign_id, message_id, actor):
        """Record that a core message belongs to a campaign.

        The record binds the campaign definition to an existing
        core message; it dispatches nothing and changes no core
        delivery. The core's own dispatch (through the labelled
        reference transport) remains the only dispatch. Action:
        message_compose. Audit: ext_campaign_send.
        """
        self._guard(actor, "message_compose", "ext_campaign_send",
                    target=campaign_id)
        self._get("campaign_definition", campaign_id)
        self.store.get_message(message_id)
        return self._create(
            "campaign_send", "csn",
            {"campaign_id": campaign_id, "message_id": message_id,
             "reference_stub": True,
             "reference_transport": True,
             "transmitted_here": False,
             "dispatched_by_extension": False},
            actor, "ext_campaign_send")

    def list_campaign_sends(self, campaign_id, actor=None):
        """Return a campaign's send records in recording order."""
        self._guard_read(actor, "records_read", "ext_campaign_send_list",
                         target=campaign_id)
        self._get("campaign_definition", campaign_id)
        return self._list("campaign_send", campaign_id=campaign_id)

    def campaign_view(self, campaign_id, actor=None):
        """Campaign definition plus derived lifecycle/send state.

        ``current_state`` is the latest recorded state record's
        state (``not_started`` when none), derived at read by the
        latest-record seam; the stored definition carries no state
        or count key.
        """
        self._guard_read(actor, "records_read", "ext_campaign_view",
                         target=campaign_id)
        record = self._fetch("campaign_definition", campaign_id)
        states = self._list("campaign_state", campaign_id=campaign_id)
        sends = self._list("campaign_send", campaign_id=campaign_id)
        latest = self._latest_record(states)
        record["current_state"] = latest["state"] if latest else "not_started"
        record["state_count"] = len(states)
        record["send_count"] = len(sends)
        record["derived"] = True
        return record

    # -- Audience segmentation (built) --------------------------------
    # A segment is a definition whose criteria are held as data.
    # Membership is derived at read over the core directory by the
    # seam _criteria_match: the stored definition carries no member
    # list and no count. No external audience is built or held.

    @staticmethod
    def _criteria_match(criteria, contact, group_members):
        """The segmentation derivation seam.

        A contact matches a segment only when **every** criterion
        holds (AND semantics). This is the single evaluation point
        behind :meth:`segment_view` -- the batch's fresh negative
        control mutates it (see tests/README.md): an implementation
        that waves every contact through must not produce the
        canonical membership.
        """
        return all(_criterion_holds(criterion, contact, group_members) for criterion in criteria)

    def _segment_members(self, definition):
        """Derive a segment's member contacts from the core directory."""
        contacts = self.store.list_contacts()
        group_members = {}
        for criterion in definition["criteria"]:
            if criterion["kind"] == "in_group" \
                    and criterion["value"] not in group_members:
                group = self.store.get_group(criterion["value"])
                group_members[criterion["value"]] = set(group["members"])
        return [contact for contact in contacts
                if self._criteria_match(definition["criteria"], contact,
                                        group_members)]

    def define_segment(self, name, criteria, actor):
        """Define an audience segment (criteria as data).

        Action: message_compose. Audit: ext_segment_define.
        """
        self._guard(actor, "message_compose", "ext_segment_define")
        _non_empty(name, "segment name")
        criteria = _criteria(criteria)
        for criterion in criteria:
            if criterion["kind"] == "in_group":
                self.store.get_group(criterion["value"])
        return self._create(
            "segment_definition", "seg",
            {"name": name, "criteria": criteria,
             "audience_source": "core_directory",
             "external_audience_here": False},
            actor, "ext_segment_define")

    def list_segments(self, actor=None):
        """Return segment definitions in creation order."""
        self._guard_read(actor, "records_read", "ext_segment_list")
        return self._list("segment_definition")

    def get_segment(self, segment_id, actor=None):
        """Return one segment definition (no derived keys)."""
        self._guard_read(actor, "records_read", "ext_segment_get",
                         target=segment_id)
        return self._fetch("segment_definition", segment_id)

    def segment_view(self, segment_id, actor=None):
        """Segment definition plus membership derived at read.

        ``member_contact_ids`` and ``member_count`` are computed
        from the core directory by the seam on every call; the
        stored definition carries neither.
        """
        self._guard_read(actor, "records_read", "ext_segment_view",
                         target=segment_id)
        record = self._fetch("segment_definition", segment_id)
        members = self._segment_members(record)
        record["member_contact_ids"] = [c["id"] for c in members]
        record["member_count"] = len(members)
        record["derived"] = True
        return record

    # -- Customer profiles (built; identity resolution NOT performed) --
    # A profile is a record keyed by a caller-supplied opaque
    # profile_ref, with caller-asserted links to core contacts.
    # Links are records of what a caller asserted; nothing here
    # infers, merges, or deduplicates identities, and every record
    # states so (resolved_here: False). Profiles hold labels and
    # references only -- never message contents.

    def create_profile(self, profile_ref, actor, contact_ids=None,
                       attribute_labels=None):
        """Create a customer profile record. Action: message_compose.

        Audit: ext_profile_create. A duplicate ``profile_ref`` is
        rejected whole (no id consumed): refs are caller-supplied
        keys, and silently merging two profiles under one ref
        would be a resolution this build does not perform.
        """
        self._guard(actor, "message_compose", "ext_profile_create")
        _non_empty(profile_ref, "profile_ref")
        contact_ids = _string_list(contact_ids, "contact_ids")
        labels = _string_list(attribute_labels, "attribute_labels")
        for contact_id in contact_ids:
            self._contact(contact_id)
        with self._lock:
            for record in self._records.values():
                if record.get("profile_ref") == profile_ref \
                        and "profile_ref" in record:
                    raise ValidationError(
                        "profile_ref already exists: %r" % (profile_ref,))
            return self._create(
                "profile", "prf",
                {"profile_ref": profile_ref,
                 "contact_ids": contact_ids,
                 "attribute_labels": labels,
                 "resolved_here": False,
                 "identity_resolution_performed": False,
                 "merged_here": False},
                actor, "ext_profile_create")

    def list_profiles(self, actor=None):
        """Return profile records in creation order."""
        self._guard_read(actor, "records_read", "ext_profile_list")
        return self._list("profile")

    def get_profile(self, profile_id, actor=None):
        """Return one profile record (no derived keys)."""
        self._guard_read(actor, "records_read", "ext_profile_get",
                         target=profile_id)
        return self._fetch("profile", profile_id)

    def record_profile_link(self, profile_id, contact_id, actor,
                            link_label=None):
        """Record a caller-asserted profile<->contact link.

        Action: message_compose. Audit: ext_profile_link. A
        duplicate link (same profile, same contact) is rejected
        whole, mirroring the core's group-membership rule.
        """
        self._guard(actor, "message_compose", "ext_profile_link",
                    target=profile_id)
        _string_or_none(link_label, "link_label")
        self._get("profile", profile_id)
        self._contact(contact_id)
        with self._lock:
            for existing in self._list("profile_link",
                                       profile_id=profile_id):
                if existing["contact_id"] == contact_id:
                    raise ValidationError(
                        "contact %r is already linked to profile %r"
                        % (contact_id, profile_id))
            return self._create(
                "profile_link", "plk",
                {"profile_id": profile_id, "contact_id": contact_id,
                 "link_label": link_label,
                 "asserted_by_caller": True,
                 "resolved_here": False},
                actor, "ext_profile_link")

    def profile_view(self, profile_id, actor=None):
        """Profile record plus its contact set derived at read.

        The contact set is the union of the contacts asserted at
        creation and the contacts asserted by later link records,
        in assertion order; the stored profile record is unchanged.
        """
        self._guard_read(actor, "records_read", "ext_profile_view",
                         target=profile_id)
        record = self._fetch("profile", profile_id)
        contact_ids = list(record["contact_ids"])
        links = self._list("profile_link", profile_id=profile_id)
        for link in links:
            if link["contact_id"] not in contact_ids:
                contact_ids.append(link["contact_id"])
        record["all_contact_ids"] = contact_ids
        record["contact_count"] = len(contact_ids)
        record["link_count"] = len(links)
        record["derived"] = True
        return record

    # -- Real-time interaction management (built, records form) --------
    # An interaction is a session record over a core contact and a
    # channel kind, with decision and outcome labels stored verbatim
    # as reported by the caller. No decisioning happens here and no
    # session is live: the labels are reports, and every record
    # carries live_here: False / decisioning_here: False. Follow-up
    # outcomes are append-only records; the current outcome derives
    # at read by the latest-record seam.

    def record_interaction(self, contact_id, channel_kind, actor,
                           decision_label=None, outcome_label=None,
                           interaction_ref=None, occurred_utc=None):
        """Record one interaction session. Action: message_compose.

        Audit: ext_interaction_record.
        """
        self._guard(actor, "message_compose", "ext_interaction_record",
                    target=contact_id)
        _one_of(channel_kind, KNOWN_CHANNEL_KINDS,
                tuple(sorted(KNOWN_CHANNEL_KINDS)), "channel kind")
        _string_or_none(decision_label, "decision_label")
        _string_or_none(outcome_label, "outcome_label")
        _string_or_none(interaction_ref, "interaction_ref")
        if occurred_utc is not None:
            _validate_iso(occurred_utc, "occurred_utc")
        self._contact(contact_id)
        return self._create(
            "interaction", "int",
            {"contact_id": contact_id, "channel_kind": channel_kind,
             "decision_label": decision_label,
             "outcome_label": outcome_label,
             "interaction_ref": interaction_ref,
             "occurred_utc": occurred_utc,
             "live_here": False,
             "decisioning_here": False,
             "decided_here": False},
            actor, "ext_interaction_record")

    def list_interactions(self, actor=None, contact_id=None):
        """Return interaction records, optionally for one contact."""
        self._guard_read(actor, "records_read", "ext_interaction_list")
        if contact_id is not None:
            self._contact(contact_id)
        return self._list("interaction", contact_id=contact_id)

    def record_interaction_outcome(self, interaction_id, outcome_label,
                                   actor):
        """Record a follow-up outcome for an interaction (append-only).

        Action: message_compose. Audit: ext_interaction_outcome.
        """
        self._guard(actor, "message_compose", "ext_interaction_outcome",
                    target=interaction_id)
        _non_empty(outcome_label, "outcome_label")
        self._get("interaction", interaction_id)
        return self._create(
            "interaction_outcome", "ioc",
            {"interaction_id": interaction_id,
             "outcome_label": outcome_label,
             "reported_by_caller": True,
             "live_here": False},
            actor, "ext_interaction_outcome")

    def interaction_view(self, interaction_id, actor=None):
        """Interaction record plus current outcome derived at read.

        The current outcome is the latest recorded outcome record's
        label, falling back to the session's own reported outcome
        label when no follow-up exists (``unreported`` when neither
        exists). Derived at read; nothing is written back.
        """
        self._guard_read(actor, "records_read", "ext_interaction_view",
                         target=interaction_id)
        record = self._fetch("interaction", interaction_id)
        outcomes = self._list("interaction_outcome",
                              interaction_id=interaction_id)
        latest = self._latest_record(outcomes)
        if latest is not None:
            current = latest["outcome_label"]
        elif record["outcome_label"] is not None:
            current = record["outcome_label"]
        else:
            current = "unreported"
        record["current_outcome"] = current
        record["outcome_count"] = len(outcomes)
        record["derived"] = True
        return record

    # -- Workflow / BPM (reference implementation) ----------------------
    # A workflow is a definition held as data (steps, including
    # approval-chain steps whose approver is a role label) plus
    # reported outcome records. The engine does not exist here:
    # definitions are never executed, approval steps gate nothing,
    # and defining a workflow or recording an outcome changes no
    # core record (pinned by test). The approval-less dispatch
    # substrate remains Core, exactly as the union spec records.

    def define_workflow(self, name, steps, actor):
        """Define a workflow (definition as data). Action:
        message_compose. Audit: ext_workflow_define."""
        self._guard(actor, "message_compose", "ext_workflow_define")
        _non_empty(name, "workflow name")
        steps = _steps(steps, ("approver_role",), "workflow steps")
        if not steps:
            raise ValidationError("workflow steps must be a non-empty list")
        return self._create(
            "workflow_definition", "wfl",
            {"name": name, "steps": steps,
             "reference_stub": True,
             "definition_only": True,
             "executed_here": False,
             "approvals_enforced_here": False},
            actor, "ext_workflow_define")

    def list_workflows(self, actor=None):
        """Return workflow definitions in creation order."""
        self._guard_read(actor, "records_read", "ext_workflow_list")
        return self._list("workflow_definition")

    def record_workflow_outcome(self, workflow_id, outcome_label, actor,
                                step_label=None):
        """Record a reported workflow outcome (verbatim label).

        Action: message_compose. Audit: ext_workflow_outcome. The
        outcome is a report about an external run; nothing here ran.
        """
        self._guard(actor, "message_compose", "ext_workflow_outcome",
                    target=workflow_id)
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(step_label, "step_label")
        self._get("workflow_definition", workflow_id)
        return self._create(
            "workflow_outcome", "woc",
            {"workflow_id": workflow_id,
             "outcome_label": outcome_label,
             "step_label": step_label,
             "reference_stub": True,
             "reported_by_caller": True,
             "executed_here": False},
            actor, "ext_workflow_outcome")

    def workflow_view(self, workflow_id, actor=None):
        """Workflow definition plus reported outcomes (count derived)."""
        self._guard_read(actor, "records_read", "ext_workflow_view",
                         target=workflow_id)
        record = self._fetch("workflow_definition", workflow_id)
        outcomes = self._list("workflow_outcome", workflow_id=workflow_id)
        record["outcomes"] = outcomes
        record["outcome_count"] = len(outcomes)
        record["derived"] = True
        return record

    # -- Reporting / analytics beyond the substrate (built) -------------
    # Deterministic counts over core + extension records, computed
    # at read on every call. No report result is ever stored: the
    # figures track the records as they stand when read (pinned by
    # test). This is the records-substrate reporting form; no
    # campaign-effectiveness engine or dashboard renderer exists.

    def report_summary(self, actor=None):
        """Deterministic counts over the whole substrate, derived.

        Action: records_read (via _guard_read). Nothing is stored.
        """
        self._guard_read(actor, "records_read", "ext_report_summary")
        contacts = self.store.list_contacts()
        groups = self.store.list_groups()
        messages = self.store.list_messages()
        deliveries = self.store.list_deliveries()
        by_status = {"queued": 0, "delivered": 0, "failed": 0,
                     "acknowledged": 0}
        for delivery in deliveries:
            by_status[delivery["status"]] = \
                by_status.get(delivery["status"], 0) + 1
        return {
            "method": "deterministic_counts",
            "derived": True,
            "contacts": len(contacts),
            "groups": len(groups),
            "messages": len(messages),
            "deliveries": len(deliveries),
            "deliveries_by_status": by_status,
            "campaigns": len(self._list("campaign_definition")),
            "campaign_sends": len(self._list("campaign_send")),
            "segments": len(self._list("segment_definition")),
            "profiles": len(self._list("profile")),
            "interactions": len(self._list("interaction")),
            "workflows": len(self._list("workflow_definition")),
        }

    def campaign_effectiveness(self, campaign_id, actor=None):
        """Per-campaign delivery figures, derived at read.

        Walks the campaign's send records to their core messages
        and counts those messages' core deliveries by status. The
        figures are the core's own delivery records, counted; no
        effectiveness score is computed and none is stored.
        """
        self._guard_read(actor, "records_read", "ext_campaign_effectiveness",
                         target=campaign_id)
        self._get("campaign_definition", campaign_id)
        sends = self._list("campaign_send", campaign_id=campaign_id)
        by_status = {"queued": 0, "delivered": 0, "failed": 0,
                     "acknowledged": 0}
        total = 0
        message_ids = []
        for send in sends:
            if send["message_id"] not in message_ids:
                message_ids.append(send["message_id"])
            for delivery in self.store.list_deliveries(
                    message_id=send["message_id"]):
                total += 1
                by_status[delivery["status"]] = \
                    by_status.get(delivery["status"], 0) + 1
        return {
            "campaign_id": campaign_id,
            "method": "deterministic_counts",
            "derived": True,
            "message_ids": message_ids,
            "deliveries": total,
            "deliveries_by_status": by_status,
            "acknowledged": by_status.get("acknowledged", 0),
        }

    # -- Real channel execution (reference implementation) --------------
    # Execution channels are configuration records (a channel kind
    # label plus an opaque provider label; "postal" names direct
    # mail, which has no core channel kind) and execution records
    # binding a configuration to an optional core message or an
    # opaque fulfillment reference. Nothing is transmitted or
    # fulfilled: every record carries reference_transport: True and
    # transmitted_here: False, and recording an execution changes
    # no core delivery. The core's labelled reference transport
    # remains the only transport, exactly as the entry's own text
    # bounds it.

    def configure_execution_channel(self, kind_label, provider_label,
                                    actor):
        """Configure an execution channel (record only).

        Action: channel_write (admin only, matching the core's
        channel discipline). Audit: ext_execution_configure.
        """
        self._guard(actor, "channel_write", "ext_execution_configure")
        _one_of(kind_label, KNOWN_EXECUTION_KINDS, EXECUTION_KINDS,
                "execution channel kind")
        _non_empty(provider_label, "provider_label")
        return self._create(
            "execution_channel", "exc",
            {"kind_label": kind_label, "provider_label": provider_label,
             "reference_stub": True,
             "reference_transport": True,
             "real_channel_here": False,
             "transmitted_here": False},
            actor, "ext_execution_configure")

    def list_execution_channels(self, actor=None):
        """Return execution channel configurations in creation order."""
        self._guard_read(actor, "records_read", "ext_execution_list")
        return self._list("execution_channel")

    def record_execution(self, execution_channel_id, actor, message_id=None,
                         fulfillment_ref=None):
        """Record one channel execution (reference form).

        Action: message_compose. Audit: ext_execution_record. If
        ``message_id`` is given it must name an existing core
        message; recording changes none of its deliveries.
        """
        self._guard(actor, "message_compose", "ext_execution_record",
                    target=execution_channel_id)
        _string_or_none(fulfillment_ref, "fulfillment_ref")
        self._get("execution_channel", execution_channel_id)
        if message_id is not None:
            self.store.get_message(message_id)
        return self._create(
            "execution_record", "exr",
            {"execution_channel_id": execution_channel_id,
             "message_id": message_id,
             "fulfillment_ref": fulfillment_ref,
             "reference_stub": True,
             "reference_transport": True,
             "transmitted_here": False,
             "fulfilled_here": False,
             "status": "recorded_reference_only"},
            actor, "ext_execution_record")

    def execution_channel_view(self, execution_channel_id, actor=None):
        """Execution channel plus its execution count, derived at read."""
        self._guard_read(actor, "records_read", "ext_execution_view",
                         target=execution_channel_id)
        record = self._fetch("execution_channel", execution_channel_id)
        executions = self._list("execution_record",
                                execution_channel_id=execution_channel_id)
        record["executions"] = executions
        record["execution_count"] = len(executions)
        record["derived"] = True
        return record

    # -- Managed-service operations (reference implementation) ----------
    # Operation records are reports about the platform's operation,
    # recorded verbatim. Hosting and operating the platform itself
    # are deployment properties (PLATFORM-LAYER.md decision 6);
    # nothing here hosts or operates anything, and every record
    # states so. Counts derive at read.

    def record_service_operation(self, operation_label, outcome_label,
                                 actor):
        """Record one managed-service operation report.

        Action: message_compose. Audit: ext_operation_record.
        """
        self._guard(actor, "message_compose", "ext_operation_record")
        _non_empty(operation_label, "operation_label")
        _non_empty(outcome_label, "outcome_label")
        return self._create(
            "service_operation", "sop",
            {"operation_label": operation_label,
             "outcome_label": outcome_label,
             "reference_stub": True,
             "reported_by_caller": True,
             "hosted_here": False,
             "operated_here": False},
            actor, "ext_operation_record")

    def list_service_operations(self, actor=None):
        """Return operation records in recording order."""
        self._guard_read(actor, "records_read", "ext_operation_list")
        return self._list("service_operation")

    def operations_summary(self, actor=None):
        """Counts of operation records by label, derived at read."""
        self._guard_read(actor, "records_read", "ext_operation_summary")
        operations = self._list("service_operation")
        by_operation = {}
        by_outcome = {}
        for operation in operations:
            by_operation[operation["operation_label"]] = \
                by_operation.get(operation["operation_label"], 0) + 1
            by_outcome[operation["outcome_label"]] = \
                by_outcome.get(operation["outcome_label"], 0) + 1
        return {
            "method": "deterministic_counts",
            "derived": True,
            "total": len(operations),
            "by_operation": by_operation,
            "by_outcome": by_outcome,
        }
