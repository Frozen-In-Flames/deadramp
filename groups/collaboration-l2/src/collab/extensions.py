"""Final GAPS batch extensions for Collaboration L2.

Clean-room, standard-library-only extensions for the 8 open
entries of the GAPS.md section "Group 2 — Collaboration L2 (57
forks)" (inventory idx 14-20 and 22; see ``BATCH.md`` in the group
directory for the per-entry disposition). This module is a wrapper
around :class:`CollabStore`; every core module is untouched and
byte-identical to the shipped build. The forms mirror the sibling
tiers' batch units (``../collaboration-l3`` and
``../collaboration-l1``), held at this group's Moderate apparatus:
the core's plain append-only audit log (AU-2/AU-3/AU-6/AU-9, which
at Moderate holds on both sides of the crosswalk), no hash-chained
audit and no auditor role (those are the High tier's uplifts), and
no FAR-side-only audit note (that is the Low tier's precision).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form -- records plus deterministic derivations over
the group's OWN records (core records and extension records):

- Records & governance is retention-policy, legal-hold, and
  disposition-decision records over core workspace/file records.
  Current hold state and disposition eligibility are derived at
  read from recorded states; nothing is retained, disposed of, or
  deleted here -- retention-period enforcement and disposition
  are the embedding organization's records schedule, executed at
  the deployment layer (PLATFORM-LAYER.md decision 4). Recording
  a governance record changes no core file record (pinned by
  test).
- Task & project management is project, milestone, card-link,
  dependency, and card-state records over core board cards, with
  card state and project counts derived at read from recorded
  state labels -- counts and states only; no progress score is
  computed anywhere.
- Learning / training / mentoring is course, enrollment, and
  completion records over core workspaces. Completions are
  recorded verbatim; nothing is taught or assessed here.
- Knowledge management is article records whose stored shape
  holds only tags and provenance, with the text in append-only
  revisions; the current text is derived at read from the latest
  revision (the Customer Service knowledge-base form).
- The four stub-engine entries ship as labeled reference
  implementations: every record carries ``reference_stub: True``.
  Workflow definitions are held as data and never run -- the
  house registry-never-executes doctrine, pinned behaviorally
  (registering a definition changes no core record). AI
  assistance holds reported outputs as opaque references only;
  no inference runs here and no output text exists in any shape.
  Speech is transcription-job records with reported outcomes.
  Voice/telephony is session records only -- no media exists in
  this build and nothing connects or streams. E-signature holds
  envelope and ceremony records only -- no field can hold a
  signature value, and nothing is signed.

Access discipline, carried from the core: every operation
resolves its workspace through the core store, so the membership
boundary and the ``read`` permission bind reads and writes alike.
Extension writes additionally map to the core ``post`` action
(the content-contribution action held by the member and admin
roles): the viewer role is read-only on this surface. Denied
write attempts by role-holding actors are recorded on the core
audit log with a ``:denied`` suffix; successful extension
mutations are recorded with ``ext_``-prefixed actions on the
same append-only log. The audit entry is recorded before the
extension record is committed, so an audit write failure
changes nothing and consumes no id. Validation precedes
mutation throughout: a failed operation consumes no id and
changes nothing.
"""

import copy
import threading
from datetime import datetime, timedelta, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

#: The core RBAC action extension writes map to.
_WRITE_ACTION = "post"

HOLD_STATES = (
    "reported_issued", "reported_acknowledged", "reported_released",
)
HOLD_ACTIVE_STATES = ("reported_issued", "reported_acknowledged")
DISPOSITION_LABELS = (
    "retain_reported", "dispose_reported", "hold_reported",
)
CARD_STATES = (
    "reported_not_started", "reported_in_progress", "reported_blocked",
    "reported_done",
)
CARD_DEFAULT_STATE = "reported_not_started"
COURSE_KINDS = ("training", "mentoring", "learning")
COMPLETION_LABELS = (
    "reported_completed", "reported_in_progress", "reported_withdrawn",
)
ASSISTANT_KINDS = ("assistance", "speech", "analytics")
TRANSCRIPTION_LABELS = (
    "reported_completed", "reported_failed", "reported_partial",
)
VOICE_KINDS = ("voice", "telephony", "contact_center")
CEREMONY_LABELS = (
    "reported_sent", "reported_viewed", "reported_signed",
    "reported_declined", "reported_completed", "reported_voided",
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


def _parse_iso_datetime(value, what):
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 datetime string" % (what,))
    text = value.strip()
    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(
            "%s is not a valid ISO-8601 datetime: %r" % (what, value)) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class CollabExtensions:
    """Extension surface wrapping one :class:`CollabStore`."""

    def __init__(self, store):
        self.store = store
        self._policies = {}
        self._decisions = {}
        self._holds = {}
        self._hold_states = {}
        self._projects = {}
        self._milestones = {}
        self._card_links = {}
        self._card_states = {}
        self._dependencies = {}
        self._courses = {}
        self._enrollments = {}
        self._completions = {}
        self._articles = {}
        self._revisions = {}
        self._workflow_definitions = {}
        self._assistants = {}
        self._ai_outputs = {}
        self._transcription_jobs = {}
        self._transcription_outcomes = {}
        self._voice_channels = {}
        self._call_sessions = {}
        self._envelopes = {}
        self._ceremonies = {}
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

    def _guard(self, actor, audit_action):
        """Enforce the extension write permission before any state
        change. Extension writes map to the core ``post`` action. A
        denied attempt is recorded on the audit log with a
        ``:denied`` suffix before the error propagates; a missing
        actor is denied outright. A plain string carries identity
        but no role (the service layer enforces its role), matching
        the core convention."""
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (_WRITE_ACTION,))
        if hasattr(actor, "role"):
            try:
                require(actor, _WRITE_ACTION)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": _WRITE_ACTION})
                raise

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

    # -- records & governance (idx 19) ---------------------------------
    # Retention-policy, legal-hold, and disposition-decision records
    # over core workspace/file records. Current hold state and
    # disposition eligibility are derived at read; nothing is
    # retained, disposed of, or deleted here (PLATFORM-LAYER.md
    # decision 4).

    def create_governance_policy(self, actor, workspace_id, policy_ref,
                                 retention_days):
        """Create a retention-policy record for a workspace. Action:
        post. Ids: gpol-{n}. ``retention_days`` is a non-negative
        integer held as data; enforcing it is the deployment
        layer's records schedule, never this build's."""
        _non_empty(policy_ref, "policy_ref")
        _count(retention_days, "retention_days")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_governance_policy_create")
            return self._create(self._policies, "gpol-", {
                "workspace_id": workspace_id,
                "policy_ref": policy_ref,
                "retention_days": retention_days,
                "retention_enforced_here": False,
            }, actor, "ext_governance_policy_create")

    def get_governance_policy(self, actor, workspace_id, policy_id):
        """One retention-policy record. Action: read (via core)."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._policies, policy_id, workspace_id,
                             "governance policy"))

    def list_governance_policies(self, actor, workspace_id):
        """All retention-policy records of a workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._policies, workspace_id))]

    def create_legal_hold(self, actor, workspace_id, hold_ref, file_ids):
        """Create a legal-hold record covering core file records.
        Action: post. Ids: hold-{n}. Preservation itself is
        performed by the custodian's systems, never here."""
        _non_empty(hold_ref, "hold_ref")
        file_ids = _string_list(file_ids, "file_ids", allow_empty=False)
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_hold_create")
            for file_id in file_ids:
                self.store.get_file(workspace_id, file_id, actor)
            return self._create(self._holds, "hold-", {
                "workspace_id": workspace_id,
                "hold_ref": hold_ref,
                "file_ids": list(file_ids),
                "preserved_here": False,
            }, actor, "ext_hold_create")

    def get_legal_hold(self, actor, workspace_id, hold_id):
        """One legal-hold record (no derived state key)."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._holds, hold_id, workspace_id,
                             "legal hold"))

    def record_hold_state(self, actor, workspace_id, hold_id, state_label):
        """Record one reported state label for a legal hold. Action:
        post. Ids: hst-{n}. States are verbatim labels; the hold's
        current state is derived at read, never stored."""
        _label(state_label, HOLD_STATES, "state_label")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_hold_state_record")
            self._scoped(self._holds, hold_id, workspace_id, "legal hold")
            return self._create(self._hold_states, "hst-", {
                "workspace_id": workspace_id,
                "hold_id": hold_id,
                "state_label": state_label,
                "preserved_here": False,
            }, actor, "ext_hold_state_record")

    def list_hold_states(self, actor, workspace_id, hold_id):
        """All recorded state labels of a hold, in record order."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._holds, hold_id, workspace_id, "legal hold")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._hold_states.values()
                if r["hold_id"] == hold_id)]

    def _hold_states_for(self, hold_id):
        return self._sorted(
            r for r in self._hold_states.values() if r["hold_id"] == hold_id)

    @staticmethod
    def _current_hold_label(states):
        """The current state of a hold: the latest recorded label,
        or ``recorded`` when no state has been recorded yet.

        MUTATION DRILL NOTE: this derivation is the batch's fresh
        negative control target -- if it read the earliest label
        instead, a released hold would still read as active and
        disposition eligibility would stay shut after release (see
        tests/README.md)."""
        if not states:
            return "recorded"
        return states[-1]["state_label"]

    def _hold_is_active(self, hold_id):
        return (self._current_hold_label(self._hold_states_for(hold_id))
                in HOLD_ACTIVE_STATES)

    def _active_hold_for_file(self, workspace_id, file_id):
        for hold in self._in_workspace(self._holds, workspace_id):
            if file_id in hold["file_ids"] and self._hold_is_active(hold["id"]):
                return hold
        return None

    def hold_view(self, actor, workspace_id, hold_id):
        """A legal-hold record plus its derived current state.
        The derivation is computed here at read and stored nowhere."""
        with self._lock:
            self._workspace(actor, workspace_id)
            hold = copy.deepcopy(
                self._scoped(self._holds, hold_id, workspace_id,
                             "legal hold"))
            states = self._hold_states_for(hold_id)
            current = self._current_hold_label(states)
            hold["current_state"] = current
            hold["active"] = current in HOLD_ACTIVE_STATES
            hold["state_record_count"] = len(states)
            hold["derived"] = True
            return hold

    def list_legal_holds(self, actor, workspace_id):
        """All legal-hold records of a workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._holds, workspace_id))]

    def _retention_elapsed(self, policy, file_record, now_dt):
        created = _parse_iso_datetime(file_record["created_utc"],
                                      "file created_utc")
        return now_dt >= created + timedelta(days=policy["retention_days"])

    def _disposition_eligible(self, policy, file_record, workspace_id,
                              now_dt):
        """Derived at read: retention has elapsed under the policy
        and no active legal hold covers the file."""
        if self._active_hold_for_file(workspace_id,
                                      file_record["id"]) is not None:
            return False
        return self._retention_elapsed(policy, file_record, now_dt)

    def governance_view(self, actor, workspace_id, policy_id, file_id,
                        now=None):
        """The derived governance state of one core file record
        under one policy: retention elapsed, active hold, and
        disposition eligibility, computed at read from the core
        file record and the recorded hold/decision states. Stored
        nowhere."""
        with self._lock:
            self._workspace(actor, workspace_id)
            policy = self._scoped(self._policies, policy_id, workspace_id,
                                  "governance policy")
            file_record = self.store.get_file(workspace_id, file_id, actor)
            now_dt = (_parse_iso_datetime(now, "now") if now is not None
                      else datetime.now(timezone.utc))
            hold = self._active_hold_for_file(workspace_id, file_id)
            decisions = [r for r in self._decisions.values()
                         if r["policy_id"] == policy_id
                         and r["file_id"] == file_id]
            return {
                "workspace_id": workspace_id,
                "policy_id": policy_id,
                "file_id": file_id,
                "retention_days": policy["retention_days"],
                "file_created_utc": file_record["created_utc"],
                "retention_elapsed": self._retention_elapsed(
                    policy, file_record, now_dt),
                "active_hold_id": hold["id"] if hold is not None else None,
                "disposition_eligible": self._disposition_eligible(
                    policy, file_record, workspace_id, now_dt),
                "decision_count": len(decisions),
                "derived": True,
            }

    def record_retention_decision(self, actor, workspace_id, policy_id,
                                  file_id, decision_label, now=None):
        """Record a disposition decision for a core file record
        under a policy. Action: post. Ids: rdec-{n}. A
        ``dispose_reported`` decision is refused whole while the
        derived eligibility is shut (retention not yet elapsed, or
        an active legal hold covers the file). The decision is
        recorded; executing it is the deployment layer's records
        schedule (``executed_here`` False), and recording one
        changes no core file record."""
        _label(decision_label, DISPOSITION_LABELS, "decision_label")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_retention_decision_record")
            policy = self._scoped(self._policies, policy_id, workspace_id,
                                  "governance policy")
            file_record = self.store.get_file(workspace_id, file_id, actor)
            now_dt = (_parse_iso_datetime(now, "now") if now is not None
                      else datetime.now(timezone.utc))
            eligible = self._disposition_eligible(
                policy, file_record, workspace_id, now_dt)
            if decision_label == "dispose_reported" and not eligible:
                raise ValidationError(
                    "disposition decision %r refused: file %r is not "
                    "disposition-eligible under policy %r (retention not "
                    "elapsed or an active legal hold covers it)"
                    % (decision_label, file_id, policy_id))
            return self._create(self._decisions, "rdec-", {
                "workspace_id": workspace_id,
                "policy_id": policy_id,
                "file_id": file_id,
                "decision_label": decision_label,
                "eligible_at_record": eligible,
                "executed_here": False,
            }, actor, "ext_retention_decision_record")

    def list_retention_decisions(self, actor, workspace_id, policy_id=None,
                                 file_id=None):
        """Recorded disposition decisions of a workspace, optionally
        filtered by policy and/or file."""
        with self._lock:
            self._workspace(actor, workspace_id)
            records = self._in_workspace(self._decisions, workspace_id)
            if policy_id is not None:
                records = [r for r in records if r["policy_id"] == policy_id]
            if file_id is not None:
                records = [r for r in records if r["file_id"] == file_id]
            return [copy.deepcopy(r) for r in self._sorted(records)]

    # -- task & project management (idx 17) -----------------------------
    # Project, milestone, card-link, dependency, and card-state
    # records over core boards and cards. Card state and project
    # counts are derived at read from recorded state labels; the
    # core card record itself is never touched.

    def _board(self, actor, workspace_id, board_id):
        for board in self.store.list_boards(workspace_id, actor):
            if board["id"] == board_id:
                return board
        raise NotFoundError("board not found: %r" % (board_id,))

    def _card(self, actor, workspace_id, board_id, card_id):
        for card in self.store.list_cards(workspace_id, board_id, actor):
            if card["id"] == card_id:
                return card
        raise NotFoundError("card not found: %r" % (card_id,))

    def create_project(self, actor, workspace_id, board_id, project_ref,
                       title):
        """Create a project record over a core board. Action: post.
        Ids: proj-{n}."""
        _non_empty(project_ref, "project_ref")
        _non_empty(title, "title")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_project_create")
            self._board(actor, workspace_id, board_id)
            return self._create(self._projects, "proj-", {
                "workspace_id": workspace_id,
                "board_id": board_id,
                "project_ref": project_ref,
                "title": title,
            }, actor, "ext_project_create")

    def get_project(self, actor, workspace_id, project_id):
        """One project record."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._projects, project_id, workspace_id,
                             "project"))

    def list_projects(self, actor, workspace_id):
        """All project records of a workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._projects, workspace_id))]

    def create_milestone(self, actor, workspace_id, project_id,
                         milestone_ref, title):
        """Create a milestone record inside a project. Action: post.
        Ids: mile-{n}."""
        _non_empty(milestone_ref, "milestone_ref")
        _non_empty(title, "title")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_milestone_create")
            self._scoped(self._projects, project_id, workspace_id, "project")
            return self._create(self._milestones, "mile-", {
                "workspace_id": workspace_id,
                "project_id": project_id,
                "milestone_ref": milestone_ref,
                "title": title,
            }, actor, "ext_milestone_create")

    def list_milestones(self, actor, workspace_id, project_id):
        """All milestone records of a project, in creation order."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._projects, project_id, workspace_id, "project")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._milestones.values()
                if r["project_id"] == project_id)]

    def link_card(self, actor, workspace_id, project_id, milestone_id,
                  card_id):
        """Link a core board card to a project milestone. Action:
        post. Ids: lnk-{n}. The card must sit on the project's
        board; the core card record is not modified."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_card_link")
            project = self._scoped(self._projects, project_id, workspace_id,
                                   "project")
            milestone = self._scoped(self._milestones, milestone_id,
                                     workspace_id, "milestone")
            if milestone["project_id"] != project_id:
                raise NotFoundError(
                    "milestone not found in project: %r" % (milestone_id,))
            self._card(actor, workspace_id, project["board_id"], card_id)
            for link in self._card_links.values():
                if (link["milestone_id"] == milestone_id
                        and link["card_id"] == card_id):
                    raise ValidationError(
                        "card %r is already linked to milestone %r"
                        % (card_id, milestone_id))
            return self._create(self._card_links, "lnk-", {
                "workspace_id": workspace_id,
                "project_id": project_id,
                "milestone_id": milestone_id,
                "card_id": card_id,
            }, actor, "ext_card_link")

    def list_card_links(self, actor, workspace_id, project_id):
        """All card links of a project, in creation order."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._projects, project_id, workspace_id, "project")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._card_links.values()
                if r["project_id"] == project_id)]

    def record_card_state(self, actor, workspace_id, project_id, card_id,
                          state_label):
        """Record one reported state label for a linked card.
        Action: post. Ids: cst-{n}. The card's current state is
        derived at read from the latest label; nothing is written
        to the core card."""
        _label(state_label, CARD_STATES, "state_label")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_card_state_record")
            project = self._scoped(self._projects, project_id, workspace_id,
                                   "project")
            self._card(actor, workspace_id, project["board_id"], card_id)
            if not any(link["project_id"] == project_id
                       and link["card_id"] == card_id
                       for link in self._card_links.values()):
                raise ValidationError(
                    "card %r is not linked to project %r"
                    % (card_id, project_id))
            return self._create(self._card_states, "cst-", {
                "workspace_id": workspace_id,
                "project_id": project_id,
                "card_id": card_id,
                "state_label": state_label,
            }, actor, "ext_card_state_record")

    def list_card_states(self, actor, workspace_id, project_id, card_id):
        """All recorded state labels for one card in a project."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._projects, project_id, workspace_id, "project")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._card_states.values()
                if r["project_id"] == project_id and r["card_id"] == card_id)]

    @staticmethod
    def _current_card_label(states):
        """The current state of a card: the latest recorded label,
        or the default ``reported_not_started`` when none has been
        recorded."""
        if not states:
            return CARD_DEFAULT_STATE
        return states[-1]["state_label"]

    def _card_current_state(self, project_id, card_id):
        states = self._sorted(
            r for r in self._card_states.values()
            if r["project_id"] == project_id and r["card_id"] == card_id)
        return self._current_card_label(states)

    def link_dependency(self, actor, workspace_id, project_id,
                        from_milestone_id, to_milestone_id):
        """Record a dependency between two milestones of one
        project (``from`` depends on ``to``). Action: post. Ids:
        dep-{n}. A milestone may not depend on itself."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_dependency_link")
            self._scoped(self._projects, project_id, workspace_id, "project")
            if from_milestone_id == to_milestone_id:
                raise ValidationError(
                    "a milestone may not depend on itself: %r"
                    % (from_milestone_id,))
            for milestone_id in (from_milestone_id, to_milestone_id):
                milestone = self._scoped(self._milestones, milestone_id,
                                         workspace_id, "milestone")
                if milestone["project_id"] != project_id:
                    raise NotFoundError(
                        "milestone not found in project: %r"
                        % (milestone_id,))
            return self._create(self._dependencies, "dep-", {
                "workspace_id": workspace_id,
                "project_id": project_id,
                "from_milestone_id": from_milestone_id,
                "to_milestone_id": to_milestone_id,
            }, actor, "ext_dependency_link")

    def list_dependencies(self, actor, workspace_id, project_id):
        """All dependency records of a project, in creation order."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._projects, project_id, workspace_id, "project")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._dependencies.values()
                if r["project_id"] == project_id)]

    def project_view(self, actor, workspace_id, project_id):
        """The derived state of a project: its milestones, each
        linked card's current state (derived at read from recorded
        labels), and exact counts. Counts and states only -- no
        progress score, percentage, or rating is computed or stored
        anywhere in this surface."""
        with self._lock:
            self._workspace(actor, workspace_id)
            project = copy.deepcopy(
                self._scoped(self._projects, project_id, workspace_id,
                             "project"))
            milestones = []
            cards_by_state = {label: 0 for label in CARD_STATES}
            total_cards = 0
            for milestone in self._sorted(
                    r for r in self._milestones.values()
                    if r["project_id"] == project_id):
                cards = []
                for link in self._sorted(
                        r for r in self._card_links.values()
                        if r["milestone_id"] == milestone["id"]):
                    state = self._card_current_state(project_id,
                                                     link["card_id"])
                    cards_by_state[state] += 1
                    total_cards += 1
                    cards.append({
                        "card_id": link["card_id"],
                        "link_id": link["id"],
                        "current_state": state,
                    })
                entry = dict(milestone)
                entry["cards"] = cards
                entry["card_count"] = len(cards)
                milestones.append(entry)
            project["milestones"] = milestones
            project["milestone_count"] = len(milestones)
            project["card_count"] = total_cards
            project["cards_by_state"] = cards_by_state
            project["dependency_count"] = len(
                [r for r in self._dependencies.values()
                 if r["project_id"] == project_id])
            project["derived"] = True
            return project

    # -- learning, training, mentoring (idx 16) -------------------------
    # Course, enrollment, and completion records over core
    # workspaces. Learners are held as opaque references (the
    # people noun stays minimal; the embedding organization owns
    # its rosters); completions are reported labels, recorded
    # verbatim; nothing is taught or assessed here.

    def create_course(self, actor, workspace_id, course_ref, title, kind):
        """Create a course record. Action: post. Ids: crs-{n}.
        ``kind`` is one of the recorded course kinds."""
        _non_empty(course_ref, "course_ref")
        _non_empty(title, "title")
        _label(kind, COURSE_KINDS, "kind")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_course_create")
            return self._create(self._courses, "crs-", {
                "workspace_id": workspace_id,
                "course_ref": course_ref,
                "title": title,
                "kind": kind,
            }, actor, "ext_course_create")

    def get_course(self, actor, workspace_id, course_id):
        """One course record."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._courses, course_id, workspace_id,
                             "course"))

    def list_courses(self, actor, workspace_id):
        """All course records of a workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._courses, workspace_id))]

    def record_enrollment(self, actor, workspace_id, course_id,
                          learner_ref):
        """Enroll one learner in a course. Action: post. Ids:
        enr-{n}. ``learner_ref`` is an opaque caller-held reference;
        no roster data is held here."""
        _non_empty(learner_ref, "learner_ref")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_enrollment_record")
            self._scoped(self._courses, course_id, workspace_id, "course")
            return self._create(self._enrollments, "enr-", {
                "workspace_id": workspace_id,
                "course_id": course_id,
                "learner_ref": learner_ref,
            }, actor, "ext_enrollment_record")

    def list_enrollments(self, actor, workspace_id, course_id):
        """All enrollment records of a course, in creation order."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._courses, course_id, workspace_id, "course")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._enrollments.values()
                if r["course_id"] == course_id)]

    def record_completion(self, actor, workspace_id, enrollment_id,
                          outcome_label):
        """Record one reported completion outcome for an enrollment.
        Action: post. Ids: cmp-{n}. The outcome is a verbatim
        reported label; nothing is assessed here."""
        _label(outcome_label, COMPLETION_LABELS, "outcome_label")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_completion_record")
            self._scoped(self._enrollments, enrollment_id, workspace_id,
                         "enrollment")
            return self._create(self._completions, "cmp-", {
                "workspace_id": workspace_id,
                "enrollment_id": enrollment_id,
                "outcome_label": outcome_label,
                "assessed_here": False,
            }, actor, "ext_completion_record")

    def course_view(self, actor, workspace_id, course_id):
        """A course record plus derived counts: enrollments and
        completions per reported outcome label, computed at read.
        Counts only -- no pass rate, grade, or score is computed or
        stored anywhere in this surface."""
        with self._lock:
            self._workspace(actor, workspace_id)
            course = copy.deepcopy(
                self._scoped(self._courses, course_id, workspace_id,
                             "course"))
            enrollments = [r for r in self._enrollments.values()
                           if r["course_id"] == course_id]
            enrollment_ids = {r["id"] for r in enrollments}
            by_outcome = {label: 0 for label in COMPLETION_LABELS}
            for completion in self._completions.values():
                if completion["enrollment_id"] in enrollment_ids:
                    by_outcome[completion["outcome_label"]] += 1
            course["enrollment_count"] = len(enrollments)
            course["completions_by_outcome"] = by_outcome
            course["derived"] = True
            return course

    # -- knowledge management (idx 20) ----------------------------------
    # Article records whose stored shape holds exactly {id,
    # workspace_id, tags, created_by, created_utc}; the article
    # text lives in append-only revision records and the current
    # text is derived at read from the latest revision (the
    # Customer Service knowledge-base form).

    def create_article(self, actor, workspace_id, title, body, tags=None):
        """Create a knowledge-base article: a stored record holding
        only tags and provenance, plus its first revision. Action:
        post. Ids: kb-{n} (article), kbrev-{n} (revision)."""
        _non_empty(title, "title")
        _non_empty(body, "body")
        tags = _string_list(tags if tags is not None else [], "tags")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_article_create")
            article = self._create(self._articles, "kb-", {
                "workspace_id": workspace_id,
                "tags": tags,
            }, actor, "ext_article_create")
            self._create(self._revisions, "kbrev-", {
                "workspace_id": workspace_id,
                "article_id": article["id"],
                "title": title,
                "body": body,
            }, actor, "ext_article_revise")
            return self._article_view(article["id"])

    def revise_article(self, actor, workspace_id, article_id, title, body):
        """Append one revision to an article. Action: post. Ids:
        kbrev-{n}. Revisions are append-only: prior text is never
        edited or removed."""
        _non_empty(title, "title")
        _non_empty(body, "body")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_article_revise")
            self._scoped(self._articles, article_id, workspace_id, "article")
            self._create(self._revisions, "kbrev-", {
                "workspace_id": workspace_id,
                "article_id": article_id,
                "title": title,
                "body": body,
            }, actor, "ext_article_revise")
            return self._article_view(article_id)

    def _revisions_for(self, article_id):
        return self._sorted(
            r for r in self._revisions.values()
            if r["article_id"] == article_id)

    def _article_view(self, article_id):
        article = copy.deepcopy(self._articles[article_id])
        revisions = self._revisions_for(article_id)
        latest = revisions[-1]
        article["title"] = latest["title"]
        article["body"] = latest["body"]
        article["revision_count"] = len(revisions)
        article["derived"] = True
        return article

    def get_article(self, actor, workspace_id, article_id):
        """One article with its current (latest-revision) text,
        derived at read."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._articles, article_id, workspace_id, "article")
            return self._article_view(article_id)

    def list_articles(self, actor, workspace_id, tag=None):
        """Articles of a workspace with current text, optionally
        filtered to one tag."""
        with self._lock:
            self._workspace(actor, workspace_id)
            articles = self._in_workspace(self._articles, workspace_id)
            if tag is not None:
                articles = [a for a in articles if tag in a["tags"]]
            return [self._article_view(a["id"])
                    for a in self._sorted(articles)]

    def list_article_revisions(self, actor, workspace_id, article_id):
        """All revisions of an article, in record order (the full
        append-only history)."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._articles, article_id, workspace_id, "article")
            return [copy.deepcopy(r)
                    for r in self._revisions_for(article_id)]

    def search_articles(self, actor, workspace_id, query):
        """Literal case-insensitive substring search over the
        current (latest-revision) title and body of each article --
        the core search doctrine, applied to the knowledge surface:
        literal containment only, no ranking or relevance score."""
        _non_empty(query, "query")
        with self._lock:
            self._workspace(actor, workspace_id)
            needle = query.lower()
            hits = []
            for article in self._sorted(
                    self._in_workspace(self._articles, workspace_id)):
                view = self._article_view(article["id"])
                if (needle in view["title"].lower()
                        or needle in view["body"].lower()):
                    hits.append(view)
            return hits

    # -- workflow / process-automation reference records (idx 14) ------
    # Labeled reference implementation: workflow definitions are
    # held as data and are NEVER executed -- the house
    # registry-never-executes doctrine. Registering a definition
    # changes no core record and no extension record outside this
    # table (pinned by test).

    def register_workflow_definition(self, actor, workspace_id,
                                     definition_ref, steps):
        """Record one workflow/process-automation definition as
        data. Action: post. Ids: wfd-{n}. The definition is never
        run, triggered, or scheduled; it exists so the group's #2
        claim family has an honest records surface for definitions
        an embedding platform executes elsewhere."""
        _non_empty(definition_ref, "definition_ref")
        steps = _string_list(steps, "steps", allow_empty=False)
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_workflow_register")
            return self._create(self._workflow_definitions, "wfd-", {
                "workspace_id": workspace_id,
                "definition_ref": definition_ref,
                "steps": steps,
                "state": _REFERENCE_STATE,
                "reference_stub": True,
                "executed_here": False,
            }, actor, "ext_workflow_register")

    def get_workflow_definition(self, actor, workspace_id, definition_id):
        """One workflow definition record."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._workflow_definitions, definition_id,
                             workspace_id, "workflow definition"))

    def list_workflow_definitions(self, actor, workspace_id):
        """All workflow definition records of a workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._workflow_definitions, workspace_id))]

    # -- AI assistance, speech, and analytics reference records (idx 15)
    # Labeled reference implementation: assistant registrations and
    # reported outputs as opaque references only. No inference runs
    # here; no shape in this surface can hold output text (the
    # method signature carries no such parameter, so smuggling one
    # in raises TypeError). Speech is transcription-job records
    # with reported outcomes; nothing is transcribed here.

    def register_assistant(self, actor, workspace_id, assistant_ref, kind):
        """Register one AI assistant/speech/analytics capability as
        a reference record. Action: post. Ids: ai-{n}. ``kind`` is
        one of the recorded assistant kinds."""
        _non_empty(assistant_ref, "assistant_ref")
        _label(kind, ASSISTANT_KINDS, "kind")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_assistant_register")
            return self._create(self._assistants, "ai-", {
                "workspace_id": workspace_id,
                "assistant_ref": assistant_ref,
                "kind": kind,
                "method": "recorded_declaration_only",
                "reference_stub": True,
                "inference_here": False,
            }, actor, "ext_assistant_register")

    def get_assistant(self, actor, workspace_id, assistant_id):
        """One assistant reference record."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._assistants, assistant_id, workspace_id,
                             "assistant"))

    def list_assistants(self, actor, workspace_id):
        """All assistant reference records of a workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._assistants, workspace_id))]

    def record_ai_output(self, actor, workspace_id, assistant_id,
                         output_ref, target_ref=None):
        """Record one reported AI output as an opaque reference.
        Action: post. Ids: aio-{n}. The output itself lives with the
        assistant that produced it; only its reference (and an
        optional opaque target reference) is held here."""
        _non_empty(output_ref, "output_ref")
        if target_ref is not None:
            _non_empty(target_ref, "target_ref")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_ai_output_record")
            self._scoped(self._assistants, assistant_id, workspace_id,
                         "assistant")
            return self._create(self._ai_outputs, "aio-", {
                "workspace_id": workspace_id,
                "assistant_id": assistant_id,
                "output_ref": output_ref,
                "target_ref": target_ref,
                "reference_stub": True,
                "inference_here": False,
            }, actor, "ext_ai_output_record")

    def list_ai_outputs(self, actor, workspace_id, assistant_id):
        """All reported-output records of one assistant."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._assistants, assistant_id, workspace_id,
                         "assistant")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._ai_outputs.values()
                if r["assistant_id"] == assistant_id)]

    def record_transcription_job(self, actor, workspace_id, assistant_id,
                                 job_ref, media_ref):
        """Record one transcription job against a speech assistant.
        Action: post. Ids: trj-{n}. The media is an opaque
        reference; nothing is transcribed here."""
        _non_empty(job_ref, "job_ref")
        _non_empty(media_ref, "media_ref")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_transcription_job_record")
            self._scoped(self._assistants, assistant_id, workspace_id,
                         "assistant")
            return self._create(self._transcription_jobs, "trj-", {
                "workspace_id": workspace_id,
                "assistant_id": assistant_id,
                "job_ref": job_ref,
                "media_ref": media_ref,
                "reference_stub": True,
                "transcribed_here": False,
            }, actor, "ext_transcription_job_record")

    def record_transcription_outcome(self, actor, workspace_id, job_id,
                                     outcome_label, result_ref):
        """Record one reported transcription outcome. Action: post.
        Ids: tro-{n}. The transcript itself is an opaque reference;
        only the reported outcome label is held here."""
        _label(outcome_label, TRANSCRIPTION_LABELS, "outcome_label")
        _non_empty(result_ref, "result_ref")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_transcription_outcome_record")
            self._scoped(self._transcription_jobs, job_id, workspace_id,
                         "transcription job")
            return self._create(self._transcription_outcomes, "tro-", {
                "workspace_id": workspace_id,
                "job_id": job_id,
                "outcome_label": outcome_label,
                "result_ref": result_ref,
                "reference_stub": True,
                "transcribed_here": False,
            }, actor, "ext_transcription_outcome_record")

    def list_transcription_outcomes(self, actor, workspace_id, job_id):
        """All outcome records of one transcription job."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._transcription_jobs, job_id, workspace_id,
                         "transcription job")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._transcription_outcomes.values()
                if r["job_id"] == job_id)]

    # -- voice / telephony / contact center reference records (idx 18) -
    # Labeled reference implementation: voice-channel registrations
    # and call-session records only. No call is placed, connected,
    # or streamed; participant identities are opaque references.

    def register_voice_channel(self, actor, workspace_id, channel_ref,
                               kind):
        """Register one voice/telephony/contact-center channel as a
        reference record. Action: post. Ids: vch-{n}. ``kind`` is
        one of the recorded voice kinds."""
        _non_empty(channel_ref, "channel_ref")
        _label(kind, VOICE_KINDS, "kind")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_voice_channel_register")
            return self._create(self._voice_channels, "vch-", {
                "workspace_id": workspace_id,
                "channel_ref": channel_ref,
                "kind": kind,
                "reference_stub": True,
                "connected_here": False,
                "media_here": False,
            }, actor, "ext_voice_channel_register")

    def get_voice_channel(self, actor, workspace_id, channel_id):
        """One voice channel reference record."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._voice_channels, channel_id, workspace_id,
                             "voice channel"))

    def list_voice_channels(self, actor, workspace_id):
        """All voice channel reference records of a workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._voice_channels, workspace_id))]

    def record_call_session(self, actor, workspace_id, channel_id,
                            session_ref, participant_refs):
        """Record one call session against a registered channel.
        Action: post. Ids: call-{n}. Participants are opaque
        references; no media exists in this build."""
        _non_empty(session_ref, "session_ref")
        participant_refs = _string_list(participant_refs, "participant_refs",
                                        allow_empty=False)
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_call_session_record")
            self._scoped(self._voice_channels, channel_id, workspace_id,
                         "voice channel")
            return self._create(self._call_sessions, "call-", {
                "workspace_id": workspace_id,
                "channel_id": channel_id,
                "session_ref": session_ref,
                "participant_refs": participant_refs,
                "reference_stub": True,
                "media_here": False,
            }, actor, "ext_call_session_record")

    def list_call_sessions(self, actor, workspace_id, channel_id):
        """All call-session records of one channel."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._voice_channels, channel_id, workspace_id,
                         "voice channel")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._call_sessions.values()
                if r["channel_id"] == channel_id)]

    # -- e-signature reference records (idx 22) -------------------------
    # Labeled reference implementation in the Legal & Policy form:
    # envelope and ceremony records only. No field in any shape can
    # hold a signature value (the method signatures carry no such
    # parameter, so smuggling one in raises TypeError) and nothing
    # is signed here; participants are recorded as opaque signer
    # references, matching this group's minimal-people noun.

    def record_envelope(self, actor, workspace_id, envelope_ref,
                        file_id=None):
        """Record one signature envelope, optionally over a core
        file record. Action: post. Ids: env-{n}. The stored shape
        is pinned: exactly {id, workspace_id, envelope_ref, file_id,
        reference_stub, signed_here, created_by, created_utc}."""
        _non_empty(envelope_ref, "envelope_ref")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_envelope_record")
            if file_id is not None:
                self.store.get_file(workspace_id, file_id, actor)
            return self._create(self._envelopes, "env-", {
                "workspace_id": workspace_id,
                "envelope_ref": envelope_ref,
                "file_id": file_id,
                "reference_stub": True,
                "signed_here": False,
            }, actor, "ext_envelope_record")

    def get_envelope(self, actor, workspace_id, envelope_id):
        """One envelope record."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._envelopes, envelope_id, workspace_id,
                             "envelope"))

    def list_envelopes(self, actor, workspace_id):
        """All envelope records of a workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._envelopes, workspace_id))]

    def record_ceremony_event(self, actor, workspace_id, envelope_id,
                              signer_ref, event_label):
        """Record one reported ceremony event for an envelope.
        Action: post. Ids: sgn-{n}. The event is a verbatim reported
        label against an opaque signer reference; nothing is signed
        here. The stored shape is pinned: exactly {id, workspace_id,
        envelope_id, signer_ref, event_label, reference_stub,
        signed_here, created_by, created_utc}."""
        _non_empty(signer_ref, "signer_ref")
        _label(event_label, CEREMONY_LABELS, "event_label")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "ext_ceremony_event_record")
            self._scoped(self._envelopes, envelope_id, workspace_id,
                         "envelope")
            return self._create(self._ceremonies, "sgn-", {
                "workspace_id": workspace_id,
                "envelope_id": envelope_id,
                "signer_ref": signer_ref,
                "event_label": event_label,
                "reference_stub": True,
                "signed_here": False,
            }, actor, "ext_ceremony_event_record")

    def list_ceremony_events(self, actor, workspace_id, envelope_id):
        """All ceremony-event records of one envelope."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._envelopes, envelope_id, workspace_id,
                         "envelope")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._ceremonies.values()
                if r["envelope_id"] == envelope_id)]
