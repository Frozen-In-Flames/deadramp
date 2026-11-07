"""Final GAPS batch extensions, second unit, for Collaboration L2.

Clean-room, standard-library-only extensions for the 5 open
entries of the GAPS.md section "Remainder Addition —
Collaboration L2 (+3 forks)" (inventory idx 595-599; see
``BATCH-ADDITION.md`` in the group directory for the per-entry
disposition). These are the gap functions ``ADDENDUM.md`` section
5 registered when the remainder forks Webex for Government,
Huddle, and IdeaScale Gov joined the founding union. This module
is a second wrapper around :class:`CollabStore`, independent of
the first batch unit's ``extensions.py``; every pre-existing
module, the first unit's included, is untouched and
byte-identical to the shipped build.

The forms follow the first unit's conventions (actor-first
signatures, audit-before-commit on the core's plain append-only
audit log, validation before mutation, a failed operation
consumes no id and changes nothing), with this unit's mutations
audited under the ``exta_`` action prefix so the two units' audit
trails stay distinguishable. Held at this group's Moderate
apparatus throughout: no hash-chained audit and no auditor role
(those are the High tier's uplifts).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form -- records plus deterministic derivations over
the group's OWN records (core records and extension records):

- Innovation management & crowdsourcing (IdeaScale) is campaign,
  idea, idea-state, endorsement, and plan-link records over core
  workspaces and boards. An idea's current state is derived at
  read from its recorded state labels; the transformation of an
  adopted idea into a project plan is recorded as a link to a
  core board (refused while the derived state is not
  ``reported_adopted``); the plan content itself is authored by
  members on that board, never generated here.
- The centralized administration console (Webex Control Hub) is
  administered-service records, configuration revision records
  whose settings are held as data (the current settings are
  derived at read from the latest revision; the stored service
  record holds no settings), administrative action records with
  verbatim reported outcomes, and a console view derived at read
  across the workspace's services. The console surface is a
  records function in its own name (ADDENDUM.md section 5), so
  PLATFORM-LAYER.md decision 6 does not close it; applying a
  configuration to a running service, and effecting an
  administrative action on an external system, are the
  platform's work, never this build's. Console writes map to
  the core ``admin`` action (the platform-administrator action
  only the admin role holds): a console is operated by
  administrators. Every other surface in this module maps
  writes to the core ``post`` action, as in the first unit.
- The three stub-engine entries ship as labeled reference
  implementations: every record carries ``reference_stub:
  True``. The virtual visitation portal is visit records bound
  to core calendar events (the portal's scheduling surface is
  the Core calendaring function), business-rule / workflow
  definitions held as data and never executed (the house
  registry-never-executes doctrine), and device-connection
  records -- no visit is conducted and no media exists here, no
  rule runs, and no device connects from here. Collaboration
  hardware endpoints are endpoint registration and
  reported-status records: the devices are manufactured
  hardware, named platform layer in the addendum itself; nothing
  is manufactured, provisioned, or connected here.
  Product-specific connector engines are connector definition
  records and exchange records naming the exchanged object by
  opaque reference only -- no content is held and nothing is
  transmitted from here.

Access discipline, carried from the core: every operation
resolves its workspace through the core store, so the membership
boundary and the ``read`` permission bind reads and writes
alike. Denied write attempts by role-holding actors are recorded
on the core audit log with a ``:denied`` suffix; successful
extension mutations are recorded with ``exta_``-prefixed actions
on the same append-only log. The audit entry is recorded before
the extension record is committed, so an audit write failure
changes nothing and consumes no id.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

#: The core RBAC action most extension writes map to.
_WRITE_ACTION = "post"

#: The core RBAC action administration-console writes map to.
_ADMIN_ACTION = "admin"

IDEA_STATES = (
    "reported_submitted", "reported_under_review", "reported_adopted",
    "reported_declined", "reported_merged",
)
IDEA_DEFAULT_STATE = "reported_submitted"
IDEA_ADOPTED_STATE = "reported_adopted"
ADMIN_OUTCOME_LABELS = (
    "reported_applied", "reported_refused", "reported_failed",
)
VISIT_OUTCOME_LABELS = (
    "reported_completed", "reported_no_show", "reported_cancelled",
    "reported_failed",
)
RULE_KINDS = ("business_rule", "workflow")
CONNECTION_OUTCOME_LABELS = (
    "reported_connected", "reported_failed", "reported_pending",
)
ENDPOINT_KINDS = (
    "room_system", "desk_device", "whiteboard_device", "phone",
    "camera", "other",
)
ENDPOINT_STATUS_LABELS = (
    "reported_online", "reported_offline", "reported_provisioning",
    "reported_error",
)
EXCHANGE_DIRECTIONS = ("inbound", "outbound")
EXCHANGE_OUTCOME_LABELS = (
    "reported_delivered", "reported_failed", "reported_queued",
)

_REFERENCE_STATE = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _label(value, known, what):
    names = ", ".join(repr(n) for n in known)
    _non_empty(value, what)
    if value not in known:
        raise ValidationError("%s must be one of %s" % (what, names))
    return value


def _string_list(value, what, allow_empty=True):
    if not isinstance(value, (list, tuple)):
        raise ValidationError("%s must be a list of strings" % (what,))
    items = list(value)
    if not allow_empty and not items:
        raise ValidationError("%s must be a non-empty list" % (what,))
    for item in items:
        _non_empty(item, what)
    return items


def _settings(value, what="settings"):
    """A configuration revision's settings, held as data: a flat
    mapping of non-empty string keys to string values. Anything
    else (nested structures, non-string values) is rejected --
    the revision records what the console was told, verbatim."""
    if not isinstance(value, dict):
        raise ValidationError("%s must be a mapping of strings" % (what,))
    items = {}
    for key, item in value.items():
        _non_empty(key, "settings key")
        if not isinstance(item, str):
            raise ValidationError(
                "%s values must be strings" % (what,))
        items[key] = item
    return items


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class CollabExtensionsAddition:
    """Second extension surface wrapping one :class:`CollabStore`."""

    def __init__(self, store):
        self.store = store
        self._campaigns = {}
        self._ideas = {}
        self._idea_states = {}
        self._endorsements = {}
        self._plan_links = {}
        self._admin_services = {}
        self._config_revisions = {}
        self._admin_actions = {}
        self._visits = {}
        self._visit_outcomes = {}
        self._visitation_rules = {}
        self._device_connections = {}
        self._endpoints = {}
        self._endpoint_statuses = {}
        self._connectors = {}
        self._exchanges = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    def _workspace(self, actor, workspace_id):
        """Resolve a workspace through the core store, which enforces
        the membership boundary and the ``read`` permission."""
        return self.store.get_workspace(workspace_id, actor)

    def _enforce(self, actor, action, audit_action):
        """Enforce one core RBAC action before any state change. A
        denied attempt is recorded on the audit log with a
        ``:denied`` suffix before the error propagates; a missing
        actor is denied outright. A plain string carries identity
        but no role (the service layer enforces its role), matching
        the core convention."""
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (action,))
        if hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": action})
                raise

    def _guard(self, actor, audit_action):
        """Extension writes map to the core ``post`` action."""
        self._enforce(actor, _WRITE_ACTION, audit_action)

    def _guard_admin(self, actor, audit_action):
        """Console writes map to the core ``admin`` action: the
        administration console is operated by platform
        administrators."""
        self._enforce(actor, _ADMIN_ACTION, audit_action)

    def _create(self, table, prefix, fields, actor, audit_action):
        """Commit one extension record, audit-before-commit: the
        audit entry is recorded first, so an audit write failure
        changes nothing and consumes no id."""
        record = {"id": "%s%d" % (prefix, self._counters.get(prefix, 0) + 1)}
        record.update(fields)
        record["created_by"] = actor_name(actor)
        record["created_utc"] = _utc_now()
        self._audit(actor, audit_action, record["id"])
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        table[record["id"]] = record
        return copy.deepcopy(record)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _scoped(self, table, record_id, workspace_id, what):
        """Fetch an extension record, treating a record from another
        workspace as not found."""
        record = self._get(table, record_id, what)
        if record["workspace_id"] != workspace_id:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    def _in_workspace(self, table, workspace_id):
        return [r for r in table.values() if r["workspace_id"] == workspace_id]

    @staticmethod
    def _latest_label(records, key):
        """The most recently recorded label under ``key``, or None."""
        return records[-1][key] if records else None

    def _core_event(self, actor, workspace_id, event_id):
        """Resolve a core calendar event of the workspace, treating
        an event from another workspace as not found."""
        for event in self.store.list_events(workspace_id, actor):
            if event["id"] == event_id:
                return event
        raise NotFoundError("event not found: %r" % (event_id,))

    def _core_board(self, actor, workspace_id, board_id):
        """Resolve a core board of the workspace, treating a board
        from another workspace as not found."""
        for board in self.store.list_boards(workspace_id, actor):
            if board["id"] == board_id:
                return board
        raise NotFoundError("board not found: %r" % (board_id,))

    # -- innovation management & crowdsourcing (idx 595) ---------------
    # Campaign, idea, idea-state, endorsement, and plan-link
    # records over core workspaces and boards. An idea's current
    # state is derived at read from its recorded state labels and
    # stored nowhere; counts are exact counts of records.

    def create_campaign(self, actor, workspace_id, campaign_ref, title):
        """Create an innovation campaign record in a workspace.
        Action: post. Ids: inc-{n}. ``campaign_ref`` is unique
        within the workspace."""
        _non_empty(campaign_ref, "campaign_ref")
        _non_empty(title, "title")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "exta_campaign_create")
            for existing in self._in_workspace(self._campaigns,
                                               workspace_id):
                if existing["campaign_ref"] == campaign_ref:
                    raise ValidationError(
                        "campaign_ref already recorded in this "
                        "workspace: %r" % (campaign_ref,))
            return self._create(self._campaigns, "inc-", {
                "workspace_id": workspace_id,
                "campaign_ref": campaign_ref,
                "title": title,
            }, actor, "exta_campaign_create")

    def get_campaign(self, actor, workspace_id, campaign_id):
        """One campaign record. Action: read (via core)."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._campaigns, campaign_id, workspace_id,
                             "campaign"))

    def list_campaigns(self, actor, workspace_id):
        """All campaign records of a workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._campaigns, workspace_id))]

    def submit_idea(self, actor, workspace_id, campaign_id, idea_ref,
                    title):
        """Submit an idea record to a campaign. Action: post. Ids:
        idea-{n}. ``idea_ref`` is unique within the campaign. The
        idea is workspace content contributed by a member, like a
        board card; its short text is its ``title``."""
        _non_empty(idea_ref, "idea_ref")
        _non_empty(title, "title")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "exta_idea_submit")
            self._scoped(self._campaigns, campaign_id, workspace_id,
                         "campaign")
            for existing in self._ideas.values():
                if (existing["campaign_id"] == campaign_id
                        and existing["idea_ref"] == idea_ref):
                    raise ValidationError(
                        "idea_ref already recorded in this campaign: "
                        "%r" % (idea_ref,))
            return self._create(self._ideas, "idea-", {
                "workspace_id": workspace_id,
                "campaign_id": campaign_id,
                "idea_ref": idea_ref,
                "title": title,
            }, actor, "exta_idea_submit")

    def get_idea(self, actor, workspace_id, idea_id):
        """One idea record (no derived state key)."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._ideas, idea_id, workspace_id, "idea"))

    def list_ideas(self, actor, workspace_id, campaign_id):
        """All idea records of a campaign."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._campaigns, campaign_id, workspace_id,
                         "campaign")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._ideas.values()
                if r["campaign_id"] == campaign_id)]

    def record_idea_state(self, actor, workspace_id, idea_id,
                          state_label):
        """Append one reported state record to an idea. Action:
        post. Ids: ist-{n}. State records are append-only; the
        idea's current state is derived from them at read and
        never written back."""
        _label(state_label, IDEA_STATES, "state_label")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "exta_idea_state_record")
            idea = self._scoped(self._ideas, idea_id, workspace_id,
                                "idea")
            return self._create(self._idea_states, "ist-", {
                "workspace_id": workspace_id,
                "campaign_id": idea["campaign_id"],
                "idea_id": idea_id,
                "state_label": state_label,
            }, actor, "exta_idea_state_record")

    def list_idea_states(self, actor, workspace_id, idea_id):
        """All recorded state labels of an idea, in record order."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._ideas, idea_id, workspace_id, "idea")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._idea_states.values()
                if r["idea_id"] == idea_id)]

    @staticmethod
    def _current_idea_label(states):
        """The current state label of an idea: the latest recorded
        state label, or None when no state has been recorded."""
        return states[-1]["state_label"] if states else None

    def _idea_current_state(self, idea_id):
        states = self._sorted(
            r for r in self._idea_states.values()
            if r["idea_id"] == idea_id)
        label = self._current_idea_label(states)
        return label if label is not None else IDEA_DEFAULT_STATE

    def record_endorsement(self, actor, workspace_id, idea_id,
                           supporter_ref):
        """Record one crowd endorsement of an idea. Action: post.
        Ids: sup-{n}. The supporter is an opaque stakeholder
        reference (a campaign's crowd is wider than the workspace
        roster, which belongs to the embedding organization); a
        second endorsement by the same supporter of the same idea
        is refused."""
        _non_empty(supporter_ref, "supporter_ref")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "exta_endorsement_record")
            idea = self._scoped(self._ideas, idea_id, workspace_id,
                                "idea")
            for existing in self._endorsements.values():
                if (existing["idea_id"] == idea_id
                        and existing["supporter_ref"] == supporter_ref):
                    raise ValidationError(
                        "supporter has already endorsed this idea: "
                        "%r" % (supporter_ref,))
            return self._create(self._endorsements, "sup-", {
                "workspace_id": workspace_id,
                "campaign_id": idea["campaign_id"],
                "idea_id": idea_id,
                "supporter_ref": supporter_ref,
            }, actor, "exta_endorsement_record")

    def list_endorsements(self, actor, workspace_id, idea_id):
        """All endorsement records of an idea."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._ideas, idea_id, workspace_id, "idea")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._endorsements.values()
                if r["idea_id"] == idea_id)]

    def link_idea_to_plan(self, actor, workspace_id, idea_id,
                          board_id):
        """Record the transformation of an adopted idea into a
        project plan: a link from the idea to a core board, where
        the plan is authored by members. Action: post. Ids:
        pln-{n}. The link is refused whole while the idea's
        derived current state is not ``reported_adopted``, and a
        duplicate link to the same board is refused. No plan
        content is generated here (``generated_here: False``)."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "exta_plan_link_create")
            idea = self._scoped(self._ideas, idea_id, workspace_id,
                                "idea")
            self._core_board(actor, workspace_id, board_id)
            if self._idea_current_state(idea_id) != IDEA_ADOPTED_STATE:
                raise ValidationError(
                    "idea %r is not in state %r; plan links record "
                    "adopted ideas only" % (idea_id, IDEA_ADOPTED_STATE))
            for existing in self._plan_links.values():
                if (existing["idea_id"] == idea_id
                        and existing["board_id"] == board_id):
                    raise ValidationError(
                        "idea %r is already linked to board %r"
                        % (idea_id, board_id))
            return self._create(self._plan_links, "pln-", {
                "workspace_id": workspace_id,
                "campaign_id": idea["campaign_id"],
                "idea_id": idea_id,
                "board_id": board_id,
                "generated_here": False,
            }, actor, "exta_plan_link_create")

    def list_plan_links(self, actor, workspace_id, idea_id):
        """All plan-link records of an idea."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._ideas, idea_id, workspace_id, "idea")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._plan_links.values()
                if r["idea_id"] == idea_id)]

    def idea_view(self, actor, workspace_id, idea_id):
        """One idea with its derived state: the current state
        (derived at read from recorded labels, defaulting to
        ``reported_submitted``), and exact endorsement and
        plan-link counts. Counts and states only."""
        with self._lock:
            self._workspace(actor, workspace_id)
            idea = copy.deepcopy(
                self._scoped(self._ideas, idea_id, workspace_id, "idea"))
            idea["current_state"] = self._idea_current_state(idea_id)
            idea["endorsement_count"] = len(
                [r for r in self._endorsements.values()
                 if r["idea_id"] == idea_id])
            idea["plan_link_count"] = len(
                [r for r in self._plan_links.values()
                 if r["idea_id"] == idea_id])
            idea["derived"] = True
            return idea

    def campaign_view(self, actor, workspace_id, campaign_id):
        """One campaign with derived aggregates: the idea count,
        each idea counted under its derived current state, and
        exact endorsement and plan-link totals across the
        campaign's ideas. Counts and states only."""
        with self._lock:
            self._workspace(actor, workspace_id)
            campaign = copy.deepcopy(
                self._scoped(self._campaigns, campaign_id, workspace_id,
                             "campaign"))
            ideas = [r for r in self._ideas.values()
                     if r["campaign_id"] == campaign_id]
            ideas_by_state = {label: 0 for label in IDEA_STATES}
            for idea in ideas:
                ideas_by_state[self._idea_current_state(idea["id"])] += 1
            campaign["idea_count"] = len(ideas)
            campaign["ideas_by_state"] = ideas_by_state
            campaign["endorsement_count"] = len(
                [r for r in self._endorsements.values()
                 if r["campaign_id"] == campaign_id])
            campaign["plan_link_count"] = len(
                [r for r in self._plan_links.values()
                 if r["campaign_id"] == campaign_id])
            campaign["derived"] = True
            return campaign

    # -- centralized administration console (idx 596) ------------------
    # Administered-service, configuration-revision, and
    # administrative-action records. The stored service record
    # holds no settings: settings live in append-only revision
    # records and the current settings are derived at read from
    # the latest revision. Nothing recorded here is applied to a
    # running service, and no administrative action is effected
    # on an external system from here. Console writes map to the
    # core ``admin`` action.

    def register_admin_service(self, actor, workspace_id, service_ref,
                               service_label):
        """Register one administered collaboration service of a
        workspace. Action: admin. Ids: svc-{n}. ``service_ref``
        is unique within the workspace."""
        _non_empty(service_ref, "service_ref")
        _non_empty(service_label, "service_label")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard_admin(actor, "exta_admin_service_register")
            for existing in self._in_workspace(self._admin_services,
                                               workspace_id):
                if existing["service_ref"] == service_ref:
                    raise ValidationError(
                        "service_ref already recorded in this "
                        "workspace: %r" % (service_ref,))
            return self._create(self._admin_services, "svc-", {
                "workspace_id": workspace_id,
                "service_ref": service_ref,
                "service_label": service_label,
            }, actor, "exta_admin_service_register")

    def get_admin_service(self, actor, workspace_id, service_id):
        """One administered-service record (no settings key)."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._admin_services, service_id,
                             workspace_id, "administered service"))

    def list_admin_services(self, actor, workspace_id):
        """All administered-service records of a workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._admin_services, workspace_id))]

    def record_configuration_revision(self, actor, workspace_id,
                                      service_id, settings):
        """Append one configuration revision to a service. Action:
        admin. Ids: svr-{n}. The settings are held as data,
        verbatim; recording a revision applies nothing anywhere
        (the platform applies configuration; this build records
        it)."""
        settings = _settings(settings)
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard_admin(actor, "exta_config_revision_record")
            self._scoped(self._admin_services, service_id, workspace_id,
                         "administered service")
            return self._create(self._config_revisions, "svr-", {
                "workspace_id": workspace_id,
                "service_id": service_id,
                "settings": settings,
                "applied_here": False,
            }, actor, "exta_config_revision_record")

    def list_configuration_revisions(self, actor, workspace_id,
                                     service_id):
        """All configuration revision records of a service, in
        record order."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._admin_services, service_id, workspace_id,
                         "administered service")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._config_revisions.values()
                if r["service_id"] == service_id)]

    def _revisions_for(self, service_id):
        return self._sorted(
            r for r in self._config_revisions.values()
            if r["service_id"] == service_id)

    def service_view(self, actor, workspace_id, service_id):
        """One administered service with its derived configuration:
        the current settings (derived at read from the latest
        revision; empty until one is recorded) and the exact
        revision count."""
        with self._lock:
            self._workspace(actor, workspace_id)
            service = copy.deepcopy(
                self._scoped(self._admin_services, service_id,
                             workspace_id, "administered service"))
            revisions = self._revisions_for(service_id)
            service["current_settings"] = (
                copy.deepcopy(revisions[-1]["settings"])
                if revisions else {})
            service["revision_count"] = len(revisions)
            service["derived"] = True
            return service

    def record_admin_action(self, actor, workspace_id, action_ref,
                            action_label, target_ref, outcome_label,
                            service_id=None):
        """Record one administrative action taken through the
        console. Action: admin. Ids: adm-{n}. The action label
        and target are held verbatim / as an opaque reference;
        the outcome is the platform's reported label. Effecting
        the action on the named system is the platform's work
        (``effected_here: False``)."""
        _non_empty(action_ref, "action_ref")
        _non_empty(action_label, "action_label")
        _non_empty(target_ref, "target_ref")
        _label(outcome_label, ADMIN_OUTCOME_LABELS, "outcome_label")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard_admin(actor, "exta_admin_action_record")
            if service_id is not None:
                self._scoped(self._admin_services, service_id,
                             workspace_id, "administered service")
            return self._create(self._admin_actions, "adm-", {
                "workspace_id": workspace_id,
                "service_id": service_id,
                "action_ref": action_ref,
                "action_label": action_label,
                "target_ref": target_ref,
                "outcome_label": outcome_label,
                "effected_here": False,
            }, actor, "exta_admin_action_record")

    def list_admin_actions(self, actor, workspace_id):
        """All administrative action records of a workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._admin_actions, workspace_id))]

    def console_view(self, actor, workspace_id):
        """The console's derived summary of a workspace: exact
        counts of administered services, configuration revisions,
        and administrative actions, and the most recently recorded
        action's label (derived at read, or None). Counts and
        labels only."""
        with self._lock:
            self._workspace(actor, workspace_id)
            actions = self._sorted(
                self._in_workspace(self._admin_actions, workspace_id))
            return {
                "workspace_id": workspace_id,
                "service_count": len(self._in_workspace(
                    self._admin_services, workspace_id)),
                "revision_count": len(self._in_workspace(
                    self._config_revisions, workspace_id)),
                "action_count": len(actions),
                "latest_action_label": self._latest_label(
                    actions, "action_label"),
                "derived": True,
            }

    # -- virtual visitation scheduling portal (idx 597) ----------------
    # Labeled reference implementation: visit records bound to
    # core calendar events (the portal's scheduling surface is
    # the Core calendaring function), business-rule / workflow
    # definitions held as data and never executed, and
    # device-connection records. Every record carries
    # ``reference_stub: True``. No visit is conducted and no
    # media exists in this build; no device connects from here.

    def record_visit(self, actor, workspace_id, visit_ref, event_id,
                     visitor_ref, participant_ref):
        """Record one virtual visit against a core calendar event.
        Action: post. Ids: vst-{n}. ``visit_ref`` is unique within
        the workspace. The visitor and the visited participant
        are opaque references (they are not workspace members;
        the roster belongs to the embedding organization). The
        visit itself is conducted elsewhere (``conducted_here:
        False``, ``media_here: False``)."""
        _non_empty(visit_ref, "visit_ref")
        _non_empty(visitor_ref, "visitor_ref")
        _non_empty(participant_ref, "participant_ref")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "exta_visit_record")
            self._core_event(actor, workspace_id, event_id)
            for existing in self._in_workspace(self._visits,
                                               workspace_id):
                if existing["visit_ref"] == visit_ref:
                    raise ValidationError(
                        "visit_ref already recorded in this "
                        "workspace: %r" % (visit_ref,))
            return self._create(self._visits, "vst-", {
                "workspace_id": workspace_id,
                "visit_ref": visit_ref,
                "event_id": event_id,
                "visitor_ref": visitor_ref,
                "participant_ref": participant_ref,
                "reference_stub": True,
                "reference_transport": True,
                "conducted_here": False,
                "media_here": False,
            }, actor, "exta_visit_record")

    def get_visit(self, actor, workspace_id, visit_id):
        """One visit record."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._visits, visit_id, workspace_id,
                             "visit"))

    def list_visits(self, actor, workspace_id):
        """All visit records of a workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._visits, workspace_id))]

    def record_visit_outcome(self, actor, workspace_id, visit_id,
                             outcome_label):
        """Append one reported outcome record to a visit. Action:
        post. Ids: vso-{n}. The outcome is the portal platform's
        report, held verbatim as a label."""
        _label(outcome_label, VISIT_OUTCOME_LABELS, "outcome_label")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "exta_visit_outcome_record")
            self._scoped(self._visits, visit_id, workspace_id, "visit")
            return self._create(self._visit_outcomes, "vso-", {
                "workspace_id": workspace_id,
                "visit_id": visit_id,
                "outcome_label": outcome_label,
                "reference_stub": True,
            }, actor, "exta_visit_outcome_record")

    def list_visit_outcomes(self, actor, workspace_id, visit_id):
        """All reported outcome records of a visit."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._visits, visit_id, workspace_id, "visit")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._visit_outcomes.values()
                if r["visit_id"] == visit_id)]

    def visit_view(self, actor, workspace_id, visit_id):
        """One visit with its derived outcome state: the exact
        outcome count and the latest reported outcome label
        (derived at read, or None)."""
        with self._lock:
            self._workspace(actor, workspace_id)
            visit = copy.deepcopy(
                self._scoped(self._visits, visit_id, workspace_id,
                             "visit"))
            outcomes = self._sorted(
                r for r in self._visit_outcomes.values()
                if r["visit_id"] == visit_id)
            visit["outcome_count"] = len(outcomes)
            visit["latest_outcome"] = self._latest_label(
                outcomes, "outcome_label")
            visit["derived"] = True
            return visit

    def register_visitation_rule(self, actor, workspace_id, rule_ref,
                                 rule_kind, steps):
        """Record one business-rule / workflow definition of the
        portal as data. Action: post. Ids: vrul-{n}. The
        definition is never run, triggered, or evaluated -- the
        house registry-never-executes doctrine; it exists so the
        portal's configuration has an honest records surface for
        definitions the platform executes elsewhere."""
        _non_empty(rule_ref, "rule_ref")
        _label(rule_kind, RULE_KINDS, "rule_kind")
        steps = _string_list(steps, "steps", allow_empty=False)
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "exta_visitation_rule_register")
            return self._create(self._visitation_rules, "vrul-", {
                "workspace_id": workspace_id,
                "rule_ref": rule_ref,
                "rule_kind": rule_kind,
                "steps": steps,
                "state": _REFERENCE_STATE,
                "reference_stub": True,
                "executed_here": False,
            }, actor, "exta_visitation_rule_register")

    def get_visitation_rule(self, actor, workspace_id, rule_id):
        """One visitation rule definition record."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._visitation_rules, rule_id,
                             workspace_id, "visitation rule"))

    def list_visitation_rules(self, actor, workspace_id):
        """All visitation rule definition records of a workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._visitation_rules, workspace_id))]

    def record_device_connection(self, actor, workspace_id, device_ref,
                                 outcome_label, visit_id=None):
        """Record one zero-touch device connection report. Action:
        post. Ids: vcon-{n}. The device is an opaque reference and
        the outcome is the platform's reported label; provisioning
        and connection happen on the platform, never here
        (``connected_here: False``, ``provisioned_here:
        False``)."""
        _non_empty(device_ref, "device_ref")
        _label(outcome_label, CONNECTION_OUTCOME_LABELS,
               "outcome_label")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "exta_device_connection_record")
            if visit_id is not None:
                self._scoped(self._visits, visit_id, workspace_id,
                             "visit")
            return self._create(self._device_connections, "vcon-", {
                "workspace_id": workspace_id,
                "device_ref": device_ref,
                "visit_id": visit_id,
                "outcome_label": outcome_label,
                "reference_stub": True,
                "reference_transport": True,
                "connected_here": False,
                "provisioned_here": False,
            }, actor, "exta_device_connection_record")

    def list_device_connections(self, actor, workspace_id,
                                visit_id=None):
        """Device connection records of a workspace, optionally
        only those reported against one visit."""
        with self._lock:
            self._workspace(actor, workspace_id)
            records = self._in_workspace(self._device_connections,
                                         workspace_id)
            if visit_id is not None:
                self._scoped(self._visits, visit_id, workspace_id,
                             "visit")
                records = [r for r in records
                           if r["visit_id"] == visit_id]
            return [copy.deepcopy(r) for r in self._sorted(records)]

    # -- collaboration hardware endpoints (idx 598) --------------------
    # Labeled reference implementation: endpoint registration and
    # reported-status records. The endpoints are manufactured
    # hardware (the addendum names them platform layer); their
    # current status is derived at read from reported labels.
    # Nothing is manufactured, provisioned, or connected here.

    def register_endpoint(self, actor, workspace_id, device_ref, kind):
        """Register one collaboration hardware endpoint. Action:
        post. Ids: dve-{n}. The endpoint is named by an opaque
        device reference and a kind label; the record is the
        registry entry, not the device."""
        _non_empty(device_ref, "device_ref")
        _label(kind, ENDPOINT_KINDS, "kind")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "exta_endpoint_register")
            return self._create(self._endpoints, "dve-", {
                "workspace_id": workspace_id,
                "device_ref": device_ref,
                "kind": kind,
                "reference_stub": True,
                "manufactured_here": False,
                "connected_here": False,
            }, actor, "exta_endpoint_register")

    def get_endpoint(self, actor, workspace_id, endpoint_id):
        """One endpoint registration record (no derived status
        key)."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._endpoints, endpoint_id, workspace_id,
                             "endpoint"))

    def list_endpoints(self, actor, workspace_id):
        """All endpoint registration records of a workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._endpoints, workspace_id))]

    def record_endpoint_status(self, actor, workspace_id, endpoint_id,
                               status_label):
        """Append one reported status record to an endpoint.
        Action: post. Ids: dvs-{n}. The status is the platform's
        report, held verbatim as a label; the endpoint's current
        status is derived from these records at read."""
        _label(status_label, ENDPOINT_STATUS_LABELS, "status_label")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "exta_endpoint_status_record")
            self._scoped(self._endpoints, endpoint_id, workspace_id,
                         "endpoint")
            return self._create(self._endpoint_statuses, "dvs-", {
                "workspace_id": workspace_id,
                "endpoint_id": endpoint_id,
                "status_label": status_label,
                "reference_stub": True,
            }, actor, "exta_endpoint_status_record")

    def list_endpoint_statuses(self, actor, workspace_id, endpoint_id):
        """All reported status records of an endpoint."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._endpoints, endpoint_id, workspace_id,
                         "endpoint")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._endpoint_statuses.values()
                if r["endpoint_id"] == endpoint_id)]

    def endpoint_view(self, actor, workspace_id, endpoint_id):
        """One endpoint with its derived status: the current
        status (the latest reported label, derived at read, or
        None) and the exact status-record count."""
        with self._lock:
            self._workspace(actor, workspace_id)
            endpoint = copy.deepcopy(
                self._scoped(self._endpoints, endpoint_id, workspace_id,
                             "endpoint"))
            statuses = self._sorted(
                r for r in self._endpoint_statuses.values()
                if r["endpoint_id"] == endpoint_id)
            endpoint["current_status"] = self._latest_label(
                statuses, "status_label")
            endpoint["status_count"] = len(statuses)
            endpoint["derived"] = True
            return endpoint

    # -- product-specific connector engines (idx 599) ------------------
    # Labeled reference implementation: connector definition
    # records and exchange records. An exchange names the
    # exchanged object by opaque reference only (optionally bound
    # to a core file record); no content is held and nothing is
    # transmitted from here (``reference_transport: True``).

    def register_connector(self, actor, workspace_id, connector_ref,
                           product_label):
        """Register one product-specific connector definition.
        Action: post. Ids: con-{n}. ``connector_ref`` is unique
        within the workspace; ``product_label`` is the caller's
        verbatim name for the connected product, held as data.
        The connector itself runs on the platform, never here
        (``connected_here: False``)."""
        _non_empty(connector_ref, "connector_ref")
        _non_empty(product_label, "product_label")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "exta_connector_register")
            for existing in self._in_workspace(self._connectors,
                                               workspace_id):
                if existing["connector_ref"] == connector_ref:
                    raise ValidationError(
                        "connector_ref already recorded in this "
                        "workspace: %r" % (connector_ref,))
            return self._create(self._connectors, "con-", {
                "workspace_id": workspace_id,
                "connector_ref": connector_ref,
                "product_label": product_label,
                "state": _REFERENCE_STATE,
                "reference_stub": True,
                "reference_transport": True,
                "connected_here": False,
            }, actor, "exta_connector_register")

    def get_connector(self, actor, workspace_id, connector_id):
        """One connector definition record."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._connectors, connector_id,
                             workspace_id, "connector"))

    def list_connectors(self, actor, workspace_id):
        """All connector definition records of a workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._connectors, workspace_id))]

    def record_exchange(self, actor, workspace_id, connector_id,
                        direction, object_ref, outcome_label,
                        file_id=None):
        """Record one connector exchange. Action: post. Ids:
        cex-{n}. The exchanged object is named by an opaque
        reference only (optionally the id of a core file record,
        validated through the core store); its content is never
        held here and nothing is transmitted from here
        (``transmitted_here: False``, ``content_held:
        False``). The outcome is the connector's reported
        label."""
        _label(direction, EXCHANGE_DIRECTIONS, "direction")
        _non_empty(object_ref, "object_ref")
        _label(outcome_label, EXCHANGE_OUTCOME_LABELS,
               "outcome_label")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "exta_exchange_record")
            self._scoped(self._connectors, connector_id, workspace_id,
                         "connector")
            if file_id is not None:
                self.store.get_file(workspace_id, file_id, actor)
            return self._create(self._exchanges, "cex-", {
                "workspace_id": workspace_id,
                "connector_id": connector_id,
                "direction": direction,
                "object_ref": object_ref,
                "file_id": file_id,
                "outcome_label": outcome_label,
                "reference_stub": True,
                "reference_transport": True,
                "transmitted_here": False,
                "content_held": False,
            }, actor, "exta_exchange_record")

    def list_exchanges(self, actor, workspace_id, connector_id):
        """All exchange records of a connector."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._connectors, connector_id, workspace_id,
                         "connector")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._exchanges.values()
                if r["connector_id"] == connector_id)]

    def connector_view(self, actor, workspace_id, connector_id):
        """One connector with derived exchange aggregates: the
        exact exchange count and the counts per reported outcome
        label. Counts and labels only."""
        with self._lock:
            self._workspace(actor, workspace_id)
            connector = copy.deepcopy(
                self._scoped(self._connectors, connector_id,
                             workspace_id, "connector"))
            exchanges = [r for r in self._exchanges.values()
                         if r["connector_id"] == connector_id]
            by_outcome = {label: 0 for label in EXCHANGE_OUTCOME_LABELS}
            for exchange in exchanges:
                by_outcome[exchange["outcome_label"]] += 1
            connector["exchange_count"] = len(exchanges)
            connector["exchanges_by_outcome"] = by_outcome
            connector["derived"] = True
            return connector
