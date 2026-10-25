"""Contact-center store: directory (agents/contacts), queues, cases,
callbacks, interactions, alerts, rules registry, reports, and search.

Clean-room implementation of the contract.

Permission convention (mirrors the communication group): store
methods take an ``actor``. When the actor is a User-like object (it
has a ``role`` attribute) the store calls
:func:`contact.access.require` for the method's action *before* any
state change or id allocation, so a denied operation consumes no id
and changes nothing. Where a plain string is passed it carries
identity (for provenance) but no role, so there is nothing to enforce
against at this layer; the service layer, which knows the role
registry, is responsible for enforcement in that case -- and it
always passes User objects.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``agt-``, ``ct-``, ``que-``,
``case-``, ``cb-``, ``int-``, ``alr-``, ``rule-``).

Derived status (mirrors the education-training group's pattern):
a case's SLA breach and a callback's overdue state are DERIVED at
read time from stored timestamps and the reference ``now`` -- they
are never stored. Derivation lives in exactly two small methods,
:meth:`ContactStore._is_breached` and
:meth:`ContactStore._callback_state`, which the negative-control
drill patches.

Design constraint: a contact's ``reference`` is an opaque external
reference string. This build NEVER stores a real phone number as
such; callbacks are records about a requested contact, not telephony.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

CASE_TYPES = ("claim", "callback", "activity", "inquiry", "general")
KNOWN_CASE_TYPES = frozenset(CASE_TYPES)
PRIORITIES = ("low", "normal", "high", "critical")
KNOWN_PRIORITIES = frozenset(PRIORITIES)
CHANNELS = ("voice", "chat", "email", "in_person", "remote_session", "system")
KNOWN_CHANNELS = frozenset(CHANNELS)
DIRECTIONS = ("inbound", "outbound", "internal")
KNOWN_DIRECTIONS = frozenset(DIRECTIONS)
SEVERITIES = ("info", "warning", "critical")
KNOWN_SEVERITIES = frozenset(SEVERITIES)

CASE_TRANSITIONS = {
    "open": frozenset({"in_progress", "cancelled"}),
    "in_progress": frozenset({"resolved", "open", "cancelled"}),
    "resolved": frozenset({"closed", "in_progress"}),
    "closed": frozenset(),
    "cancelled": frozenset(),
}
NON_BREACHING_STATUSES = frozenset({"resolved", "closed", "cancelled"})


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _maybe_require(actor, action):
    """Enforce permissions when ``actor`` is a User-like object.

    Plain string actors carry identity (for provenance) but no role,
    so there is nothing to enforce against; enforcement for those
    happens in the service layer, which knows the role registry.
    """
    if actor is not None and hasattr(actor, "role"):
        require(actor, action)


def _require_actor(actor, action):
    """For writes: an actor must be present, then _maybe_require."""
    if actor is None:
        raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
    _maybe_require(actor, action)


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _parse_iso_datetime(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 datetime string" % (what,))
    text = value.strip()
    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO-8601 datetime: %r" % (what, value)) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _coerce_now(now, what="now"):
    if now is None:
        return datetime.now(timezone.utc)
    if isinstance(now, datetime):
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now
    if isinstance(now, str):
        return _parse_iso_datetime(now, what)
    raise ValidationError("%s must be an ISO-8601 string or datetime" % (what,))


def _validate_skills(skills):
    if skills is None:
        return []
    if not isinstance(skills, (list, tuple)):
        raise ValidationError("skills must be a list of strings")
    result = []
    for skill in skills:
        if not isinstance(skill, str) or not skill.strip():
            raise ValidationError("each skill must be a non-empty string")
        result.append(skill)
    return result


def _validate_attributes(attributes):
    if attributes is None:
        return {}
    if not isinstance(attributes, dict):
        raise ValidationError("attributes must be a dict")
    return copy.deepcopy(attributes)


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class ContactStore:
    """In-memory store for the contact-center service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._agents = {}
        self._contacts = {}
        self._queues = {}
        self._cases = {}
        self._callbacks = {}
        self._interactions = {}
        self._alerts = {}
        self._rules = {}
        self._counters = {
            "agt": 0, "ct": 0, "que": 0, "case": 0,
            "cb": 0, "int": 0, "alr": 0, "rule": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _get_agent_record(self, agent_id):
        record = self._agents.get(agent_id)
        if record is None:
            raise NotFoundError("agent not found: %r" % (agent_id,))
        return record

    def _get_contact_record(self, contact_id):
        record = self._contacts.get(contact_id)
        if record is None:
            raise NotFoundError("contact not found: %r" % (contact_id,))
        return record

    def _get_queue_record(self, queue_id):
        record = self._queues.get(queue_id)
        if record is None:
            raise NotFoundError("queue not found: %r" % (queue_id,))
        return record

    def _get_case_record(self, case_id):
        record = self._cases.get(case_id)
        if record is None:
            raise NotFoundError("case not found: %r" % (case_id,))
        return record

    def _get_callback_record(self, callback_id):
        record = self._callbacks.get(callback_id)
        if record is None:
            raise NotFoundError("callback not found: %r" % (callback_id,))
        return record

    def _get_interaction_record(self, interaction_id):
        record = self._interactions.get(interaction_id)
        if record is None:
            raise NotFoundError("interaction not found: %r" % (interaction_id,))
        return record

    def _get_alert_record(self, alert_id):
        record = self._alerts.get(alert_id)
        if record is None:
            raise NotFoundError("alert not found: %r" % (alert_id,))
        return record

    def _get_rule_record(self, rule_id):
        record = self._rules.get(rule_id)
        if record is None:
            raise NotFoundError("rule not found: %r" % (rule_id,))
        return record

    @staticmethod
    def _copy_agent(agent):
        copied = dict(agent)
        copied["skills"] = list(agent["skills"])
        copied["attributes"] = copy.deepcopy(agent["attributes"])
        return copied

    @staticmethod
    def _copy_contact(contact):
        copied = dict(contact)
        copied["attributes"] = copy.deepcopy(contact["attributes"])
        return copied

    @staticmethod
    def _copy_queue(queue):
        copied = dict(queue)
        copied["members"] = list(queue["members"])
        return copied

    @staticmethod
    def _copy_rule(rule):
        copied = dict(rule)
        copied["versions"] = copy.deepcopy(rule["versions"])
        return copied

    # -- derivation (single points; see module docstring) -------------

    def _is_breached(self, case, now_dt):
        """True iff the case is past due and not in a terminal-ish status.

        MUTATION DRILL NOTE: this method
        (``ContactStore._is_breached`` in ``src/contact/store.py``)
        is one of the two load-bearing derivation points for the
        negative-control drill: an overdue open case must read
        ``breached=True``.
        """
        if case.get("due_at") is None:
            return False
        if case["status"] in NON_BREACHING_STATUSES:
            return False
        due_dt = _parse_iso_datetime(case["due_at"], "due_at")
        return now_dt > due_dt

    def _callback_state(self, callback, now_dt):
        """Derived callback state: stored status if terminal, else
        ``overdue`` when past ``requested_for``, else ``scheduled``.

        MUTATION DRILL NOTE: this method
        (``ContactStore._callback_state`` in ``src/contact/store.py``)
        is the second load-bearing derivation point: an overdue
        scheduled callback must read ``state='overdue'``.
        """
        if callback["status"] in ("completed", "cancelled"):
            return callback["status"]
        requested_dt = _parse_iso_datetime(callback["requested_for"], "requested_for")
        if now_dt > requested_dt:
            return "overdue"
        return "scheduled"

    def _case_view(self, case, now_dt):
        view = dict(case)
        view["breached"] = self._is_breached(case, now_dt)
        return view

    def _callback_view(self, callback, now_dt):
        view = dict(callback)
        view["state"] = self._callback_state(callback, now_dt)
        return view

    # -- directory: agents ---------------------------------------------

    def create_agent(self, name, actor, skills=None, attributes=None):
        """Create an agent. Action: directory_write. Id prefix: agt-."""
        _require_actor(actor, "directory_write")
        _validate_non_empty(name, "agent name")
        skills = _validate_skills(skills)
        attributes = _validate_attributes(attributes)
        with self._lock:
            agent_id = self._next_id("agt")
            agent = {
                "id": agent_id,
                "name": name,
                "skills": skills,
                "attributes": attributes,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._agents[agent_id] = agent
            self._audit(actor, "agent_create", agent_id, details={"name": name})
            return self._copy_agent(agent)

    def get_agent(self, agent_id, actor=None):
        """Return one agent. Action: directory_read."""
        _maybe_require(actor, "directory_read")
        with self._lock:
            return self._copy_agent(self._get_agent_record(agent_id))

    def list_agents(self, actor=None):
        """Return agents sorted by id. Action: directory_read."""
        _maybe_require(actor, "directory_read")
        with self._lock:
            agents = sorted(self._agents.values(), key=lambda a: _id_num(a["id"]))
            return [self._copy_agent(a) for a in agents]

    # -- directory: contacts --------------------------------------------

    def create_contact(self, name, actor, reference=None, attributes=None):
        """Create a contact. Action: directory_write. Id prefix: ct-.

        ``reference`` is an opaque external reference string -- never
        a real phone number (stated design constraint).
        """
        _require_actor(actor, "directory_write")
        _validate_non_empty(name, "contact name")
        if reference is not None and not isinstance(reference, str):
            raise ValidationError("reference must be a string or None")
        attributes = _validate_attributes(attributes)
        with self._lock:
            contact_id = self._next_id("ct")
            contact = {
                "id": contact_id,
                "name": name,
                "reference": reference,
                "attributes": attributes,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._contacts[contact_id] = contact
            self._audit(actor, "contact_create", contact_id, details={"name": name})
            return self._copy_contact(contact)

    def get_contact(self, contact_id, actor=None):
        """Return one contact. Action: directory_read."""
        _maybe_require(actor, "directory_read")
        with self._lock:
            return self._copy_contact(self._get_contact_record(contact_id))

    def list_contacts(self, actor=None):
        """Return contacts sorted by id. Action: directory_read."""
        _maybe_require(actor, "directory_read")
        with self._lock:
            contacts = sorted(self._contacts.values(), key=lambda c: _id_num(c["id"]))
            return [self._copy_contact(c) for c in contacts]

    # -- queues -----------------------------------------------------------

    def create_queue(self, name, actor):
        """Create a queue. Action: queue_write. Id prefix: que-."""
        _require_actor(actor, "queue_write")
        _validate_non_empty(name, "queue name")
        with self._lock:
            queue_id = self._next_id("que")
            queue = {
                "id": queue_id,
                "name": name,
                "members": [],
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._queues[queue_id] = queue
            self._audit(actor, "queue_create", queue_id, details={"name": name})
            return self._copy_queue(queue)

    def add_agent_to_queue(self, queue_id, agent_id, actor):
        """Add an agent to a queue. Action: queue_write.

        Duplicate membership -> ValidationError; unknown ids ->
        NotFoundError.
        """
        _require_actor(actor, "queue_write")
        with self._lock:
            queue = self._get_queue_record(queue_id)
            self._get_agent_record(agent_id)
            if agent_id in queue["members"]:
                raise ValidationError(
                    "agent %r is already a member of queue %r" % (agent_id, queue_id)
                )
            queue["members"].append(agent_id)
            self._audit(actor, "queue_add_agent", queue_id, details={"agent_id": agent_id})
            return self._copy_queue(queue)

    def get_queue(self, queue_id, actor=None):
        """Return one queue. Action: queue_read."""
        _maybe_require(actor, "queue_read")
        with self._lock:
            return self._copy_queue(self._get_queue_record(queue_id))

    def list_queues(self, actor=None):
        """Return queues in creation order. Action: queue_read."""
        _maybe_require(actor, "queue_read")
        with self._lock:
            return [self._copy_queue(q) for q in self._queues.values()]

    def list_queue_members(self, queue_id, actor=None):
        """Return the queue's member agent dicts. Action: queue_read."""
        _maybe_require(actor, "queue_read")
        with self._lock:
            queue = self._get_queue_record(queue_id)
            return [self._copy_agent(self._agents[aid]) for aid in queue["members"]]

    # -- cases ---------------------------------------------------------------

    def create_case(self, actor, case_type, subject, contact_id=None, queue_id=None,
                    agent_id=None, priority="normal", due_at=None):
        """Create a case with status ``open``. Action: case_write.

        Id prefix: case-. Referenced ids must exist; ``due_at`` must
        be a valid ISO-8601 datetime string when given.
        """
        _require_actor(actor, "case_write")
        if case_type not in KNOWN_CASE_TYPES:
            raise ValidationError("case_type must be one of %s" % (", ".join(CASE_TYPES),))
        _validate_non_empty(subject, "case subject")
        if priority not in KNOWN_PRIORITIES:
            raise ValidationError("priority must be one of %s" % (", ".join(PRIORITIES),))
        if due_at is not None:
            _parse_iso_datetime(due_at, "due_at")
        with self._lock:
            if contact_id is not None:
                self._get_contact_record(contact_id)
            if queue_id is not None:
                self._get_queue_record(queue_id)
            if agent_id is not None:
                self._get_agent_record(agent_id)
            case_id = self._next_id("case")
            case = {
                "id": case_id,
                "case_type": case_type,
                "subject": subject,
                "contact_id": contact_id,
                "queue_id": queue_id,
                "agent_id": agent_id,
                "priority": priority,
                "status": "open",
                "due_at": due_at,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
                "updated_utc": _utc_now(),
            }
            self._cases[case_id] = case
            self._audit(actor, "case_create", case_id,
                        details={"case_type": case_type, "subject": subject})
            return self._case_view(case, _coerce_now(None))

    def assign_case(self, case_id, actor, agent_id=None, queue_id=None):
        """Assign a case to an agent and/or a queue. Action: case_write.

        At least one of ``agent_id`` / ``queue_id`` is required.
        """
        _require_actor(actor, "case_write")
        if agent_id is None and queue_id is None:
            raise ValidationError("assign_case requires at least one of agent_id, queue_id")
        with self._lock:
            case = self._get_case_record(case_id)
            if agent_id is not None:
                self._get_agent_record(agent_id)
            if queue_id is not None:
                self._get_queue_record(queue_id)
            if agent_id is not None:
                case["agent_id"] = agent_id
            if queue_id is not None:
                case["queue_id"] = queue_id
            case["updated_utc"] = _utc_now()
            self._audit(actor, "case_assign", case_id,
                        details={"agent_id": agent_id, "queue_id": queue_id})
            return self._case_view(case, _coerce_now(None))

    def transition_case(self, case_id, actor, to_status):
        """Transition a case's status along the lifecycle.

        Action: case_write. Lifecycle: open->{in_progress, cancelled},
        in_progress->{resolved, open, cancelled},
        resolved->{closed, in_progress}, closed->{}, cancelled->{}.
        Any other transition -> ValidationError.
        """
        _require_actor(actor, "case_write")
        with self._lock:
            case = self._get_case_record(case_id)
            allowed = CASE_TRANSITIONS[case["status"]]
            if to_status not in allowed:
                raise ValidationError(
                    "case %r cannot transition from %r to %r"
                    % (case_id, case["status"], to_status)
                )
            case["status"] = to_status
            case["updated_utc"] = _utc_now()
            self._audit(actor, "case_transition", case_id,
                        details={"to_status": to_status})
            return self._case_view(case, _coerce_now(None))

    def get_case(self, case_id, actor=None, now=None):
        """Return one case with derived ``breached``. Action: case_read."""
        _maybe_require(actor, "case_read")
        now_dt = _coerce_now(now)
        with self._lock:
            return self._case_view(self._get_case_record(case_id), now_dt)

    def list_cases(self, actor=None, now=None, status=None, queue_id=None, case_type=None):
        """Return cases with derived ``breached``, optionally filtered.

        Action: case_read. ``status`` filters on the stored status.
        """
        _maybe_require(actor, "case_read")
        now_dt = _coerce_now(now)
        with self._lock:
            cases = list(self._cases.values())
            if status is not None:
                cases = [c for c in cases if c["status"] == status]
            if queue_id is not None:
                cases = [c for c in cases if c["queue_id"] == queue_id]
            if case_type is not None:
                cases = [c for c in cases if c["case_type"] == case_type]
            return [self._case_view(c, now_dt) for c in cases]

    # -- callbacks --------------------------------------------------------------

    def schedule_callback(self, actor, contact_id, requested_for, case_id=None,
                          agent_id=None, note=None):
        """Schedule a callback. Action: callback_write. Id prefix: cb-.

        Stored status starts ``scheduled``; the overdue state is
        derived at read time (see :meth:`_callback_state`).
        """
        _require_actor(actor, "callback_write")
        _parse_iso_datetime(requested_for, "requested_for")
        if note is not None and not isinstance(note, str):
            raise ValidationError("note must be a string or None")
        with self._lock:
            self._get_contact_record(contact_id)
            if case_id is not None:
                self._get_case_record(case_id)
            if agent_id is not None:
                self._get_agent_record(agent_id)
            callback_id = self._next_id("cb")
            callback = {
                "id": callback_id,
                "contact_id": contact_id,
                "case_id": case_id,
                "agent_id": agent_id,
                "requested_for": requested_for,
                "note": note,
                "status": "scheduled",
                "outcome": None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
                "updated_utc": _utc_now(),
            }
            self._callbacks[callback_id] = callback
            self._audit(actor, "callback_create", callback_id,
                        details={"contact_id": contact_id})
            return self._callback_view(callback, _coerce_now(None))

    def complete_callback(self, callback_id, actor, outcome=None):
        """Complete a scheduled callback. Action: callback_write.

        Terminal transition: only from stored status ``scheduled``.
        """
        _require_actor(actor, "callback_write")
        if outcome is not None and not isinstance(outcome, str):
            raise ValidationError("outcome must be a string or None")
        with self._lock:
            callback = self._get_callback_record(callback_id)
            if callback["status"] != "scheduled":
                raise ValidationError(
                    "callback %r cannot be completed from status %r"
                    % (callback_id, callback["status"])
                )
            callback["status"] = "completed"
            callback["outcome"] = outcome
            callback["updated_utc"] = _utc_now()
            self._audit(actor, "callback_complete", callback_id,
                        details={"outcome": outcome})
            return self._callback_view(callback, _coerce_now(None))

    def cancel_callback(self, callback_id, actor):
        """Cancel a scheduled callback. Action: callback_write.

        Terminal transition: only from stored status ``scheduled``.
        """
        _require_actor(actor, "callback_write")
        with self._lock:
            callback = self._get_callback_record(callback_id)
            if callback["status"] != "scheduled":
                raise ValidationError(
                    "callback %r cannot be cancelled from status %r"
                    % (callback_id, callback["status"])
                )
            callback["status"] = "cancelled"
            callback["updated_utc"] = _utc_now()
            self._audit(actor, "callback_cancel", callback_id, details={})
            return self._callback_view(callback, _coerce_now(None))

    def get_callback(self, callback_id, actor=None, now=None):
        """Return one callback with derived ``state``. Action: callback_read."""
        _maybe_require(actor, "callback_read")
        now_dt = _coerce_now(now)
        with self._lock:
            return self._callback_view(self._get_callback_record(callback_id), now_dt)

    def list_callbacks(self, actor=None, now=None):
        """Return callbacks with derived ``state``. Action: callback_read."""
        _maybe_require(actor, "callback_read")
        now_dt = _coerce_now(now)
        with self._lock:
            return [self._callback_view(cb, now_dt) for cb in self._callbacks.values()]

    # -- interactions ---------------------------------------------------------------

    def record_interaction(self, actor, channel, direction, summary, case_id=None,
                           contact_id=None, agent_id=None, outcome=None,
                           external_ref=None):
        """Record an interaction. Action: interaction_write. Id prefix: int-.

        Interactions are IMMUTABLE records: there is deliberately no
        update or delete API for them.
        """
        _require_actor(actor, "interaction_write")
        if channel not in KNOWN_CHANNELS:
            raise ValidationError("channel must be one of %s" % (", ".join(CHANNELS),))
        if direction not in KNOWN_DIRECTIONS:
            raise ValidationError("direction must be one of %s" % (", ".join(DIRECTIONS),))
        _validate_non_empty(summary, "interaction summary")
        if outcome is not None and not isinstance(outcome, str):
            raise ValidationError("outcome must be a string or None")
        if external_ref is not None and not isinstance(external_ref, str):
            raise ValidationError("external_ref must be a string or None")
        with self._lock:
            if case_id is not None:
                self._get_case_record(case_id)
            if contact_id is not None:
                self._get_contact_record(contact_id)
            if agent_id is not None:
                self._get_agent_record(agent_id)
            interaction_id = self._next_id("int")
            interaction = {
                "id": interaction_id,
                "channel": channel,
                "direction": direction,
                "summary": summary,
                "case_id": case_id,
                "contact_id": contact_id,
                "agent_id": agent_id,
                "outcome": outcome,
                "external_ref": external_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._interactions[interaction_id] = interaction
            self._audit(actor, "interaction_record", interaction_id,
                        details={"channel": channel, "direction": direction})
            return dict(interaction)

    def get_interaction(self, interaction_id, actor=None):
        """Return one interaction. Action: interaction_read."""
        _maybe_require(actor, "interaction_read")
        with self._lock:
            return dict(self._get_interaction_record(interaction_id))

    def list_interactions(self, actor=None, case_id=None):
        """Return interactions, optionally for one case.

        Action: interaction_read.
        """
        _maybe_require(actor, "interaction_read")
        with self._lock:
            if case_id is not None:
                self._get_case_record(case_id)
            return [
                dict(i) for i in self._interactions.values()
                if case_id is None or i["case_id"] == case_id
            ]

    # -- alerts -------------------------------------------------------------------------

    def raise_alert(self, actor, severity, message, source=None, case_id=None):
        """Raise an alert with status ``raised``. Action: alert_write.

        Id prefix: alr-.
        """
        _require_actor(actor, "alert_write")
        if severity not in KNOWN_SEVERITIES:
            raise ValidationError("severity must be one of %s" % (", ".join(SEVERITIES),))
        _validate_non_empty(message, "alert message")
        if source is not None and not isinstance(source, str):
            raise ValidationError("source must be a string or None")
        with self._lock:
            if case_id is not None:
                self._get_case_record(case_id)
            alert_id = self._next_id("alr")
            alert = {
                "id": alert_id,
                "severity": severity,
                "message": message,
                "source": source,
                "case_id": case_id,
                "status": "raised",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
                "updated_utc": _utc_now(),
            }
            self._alerts[alert_id] = alert
            self._audit(actor, "alert_raise", alert_id, details={"severity": severity})
            return dict(alert)

    def acknowledge_alert(self, alert_id, actor):
        """Acknowledge a raised alert: raised -> acknowledged.

        Action: alert_write.
        """
        _require_actor(actor, "alert_write")
        with self._lock:
            alert = self._get_alert_record(alert_id)
            if alert["status"] != "raised":
                raise ValidationError(
                    "alert %r cannot be acknowledged from status %r"
                    % (alert_id, alert["status"])
                )
            alert["status"] = "acknowledged"
            alert["updated_utc"] = _utc_now()
            self._audit(actor, "alert_ack", alert_id, details={})
            return dict(alert)

    def resolve_alert(self, alert_id, actor):
        """Resolve an alert: raised|acknowledged -> resolved.

        Action: alert_write.
        """
        _require_actor(actor, "alert_write")
        with self._lock:
            alert = self._get_alert_record(alert_id)
            if alert["status"] not in ("raised", "acknowledged"):
                raise ValidationError(
                    "alert %r cannot be resolved from status %r"
                    % (alert_id, alert["status"])
                )
            alert["status"] = "resolved"
            alert["updated_utc"] = _utc_now()
            self._audit(actor, "alert_resolve", alert_id, details={})
            return dict(alert)

    def get_alert(self, alert_id, actor=None):
        """Return one alert. Action: alert_read."""
        _maybe_require(actor, "alert_read")
        with self._lock:
            return dict(self._get_alert_record(alert_id))

    def list_alerts(self, actor=None):
        """Return alerts in creation order. Action: alert_read."""
        _maybe_require(actor, "alert_read")
        with self._lock:
            return [dict(a) for a in self._alerts.values()]

    # -- rules registry ----------------------------------------------------------------------

    def create_rule(self, actor, name, case_type, condition, action_text):
        """Create a rule at version 1. Action: rule_write (admin only).

        Id prefix: rule-. ``case_type`` must be a known case type or
        ``"all"``. The rule carries a ``versions`` list; each version
        is ``{version, condition, action_text, enabled, ts}``.
        """
        _require_actor(actor, "rule_write")
        _validate_non_empty(name, "rule name")
        if case_type != "all" and case_type not in KNOWN_CASE_TYPES:
            raise ValidationError(
                "case_type must be one of %s or 'all'" % (", ".join(CASE_TYPES),)
            )
        _validate_non_empty(condition, "rule condition")
        _validate_non_empty(action_text, "rule action_text")
        with self._lock:
            rule_id = self._next_id("rule")
            now = _utc_now()
            first = {
                "version": 1,
                "condition": condition,
                "action_text": action_text,
                "enabled": True,
                "ts": now,
            }
            rule = {
                "id": rule_id,
                "name": name,
                "case_type": case_type,
                "condition": condition,
                "action_text": action_text,
                "enabled": True,
                "version": 1,
                "versions": [first],
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._rules[rule_id] = rule
            self._audit(actor, "rule_create", rule_id, details={"name": name})
            return self._copy_rule(rule)

    def update_rule(self, rule_id, actor, condition=None, action_text=None, enabled=None):
        """Append a new version to a rule. Action: rule_write (admin only).

        Unchanged fields are carried forward from the current
        version; the version counter is bumped by one.
        """
        _require_actor(actor, "rule_write")
        if condition is not None:
            _validate_non_empty(condition, "rule condition")
        if action_text is not None:
            _validate_non_empty(action_text, "rule action_text")
        if enabled is not None and not isinstance(enabled, bool):
            raise ValidationError("enabled must be a bool")
        with self._lock:
            rule = self._get_rule_record(rule_id)
            new_version = {
                "version": rule["version"] + 1,
                "condition": condition if condition is not None else rule["condition"],
                "action_text": action_text if action_text is not None else rule["action_text"],
                "enabled": enabled if enabled is not None else rule["enabled"],
                "ts": _utc_now(),
            }
            rule["versions"].append(new_version)
            rule["version"] = new_version["version"]
            rule["condition"] = new_version["condition"]
            rule["action_text"] = new_version["action_text"]
            rule["enabled"] = new_version["enabled"]
            rule["updated_utc"] = new_version["ts"]
            self._audit(actor, "rule_update", rule_id,
                        details={"version": new_version["version"]})
            return self._copy_rule(rule)

    def get_rule(self, rule_id, actor=None):
        """Return one rule. Action: rule_read."""
        _maybe_require(actor, "rule_read")
        with self._lock:
            return self._copy_rule(self._get_rule_record(rule_id))

    def list_rules(self, actor=None):
        """Return rules in creation order. Action: rule_read."""
        _maybe_require(actor, "rule_read")
        with self._lock:
            return [self._copy_rule(r) for r in self._rules.values()]

    # -- reports ----------------------------------------------------------------------------

    def report(self, actor=None, now=None):
        """Deterministic aggregate report at ``now``. Action: report_read.

        All counts are derived at call time; case breach counts and
        callback state counts use the same derivation points as the
        read views. A case with no queue counts under ``"unassigned"``
        and an interaction with no outcome under ``"none"``.
        """
        _maybe_require(actor, "report_read")
        now_dt = _coerce_now(now)
        with self._lock:
            by_status = {}
            by_type = {}
            by_queue = {}
            breached = 0
            for case in self._cases.values():
                by_status[case["status"]] = by_status.get(case["status"], 0) + 1
                by_type[case["case_type"]] = by_type.get(case["case_type"], 0) + 1
                queue_key = case["queue_id"] if case["queue_id"] is not None else "unassigned"
                by_queue[queue_key] = by_queue.get(queue_key, 0) + 1
                if self._is_breached(case, now_dt):
                    breached += 1
            by_channel = {}
            by_outcome = {}
            for interaction in self._interactions.values():
                by_channel[interaction["channel"]] = by_channel.get(interaction["channel"], 0) + 1
                outcome_key = interaction["outcome"] if interaction["outcome"] is not None else "none"
                by_outcome[outcome_key] = by_outcome.get(outcome_key, 0) + 1
            by_severity = {}
            by_alert_status = {}
            for alert in self._alerts.values():
                by_severity[alert["severity"]] = by_severity.get(alert["severity"], 0) + 1
                by_alert_status[alert["status"]] = by_alert_status.get(alert["status"], 0) + 1
            by_state = {}
            for callback in self._callbacks.values():
                state = self._callback_state(callback, now_dt)
                by_state[state] = by_state.get(state, 0) + 1
            return {
                "cases": {
                    "total": len(self._cases),
                    "by_status": by_status,
                    "by_type": by_type,
                    "by_queue": by_queue,
                    "breached": breached,
                },
                "interactions": {
                    "total": len(self._interactions),
                    "by_channel": by_channel,
                    "by_outcome": by_outcome,
                },
                "alerts": {
                    "total": len(self._alerts),
                    "by_severity": by_severity,
                    "by_status": by_alert_status,
                },
                "callbacks": {
                    "total": len(self._callbacks),
                    "by_state": by_state,
                },
            }

    # -- search ---------------------------------------------------------------------------------

    def search(self, query, actor):
        """Literal case-insensitive substring search.

        Over agents/contacts (name, plus contact reference), cases
        (subject), interactions (summary + external_ref), and alerts
        (message). Returns {people, cases, interactions, alerts},
        where ``people`` combines matching agents and contacts.
        Action: case_read. An empty query -> ValidationError.
        Records a 'search' audit entry.
        """
        _require_actor(actor, "case_read")
        if not isinstance(query, str) or not query.strip():
            raise ValidationError("query must be a non-empty string")
        needle = query.lower()
        with self._lock:
            people = []
            for agent in self._agents.values():
                if needle in agent["name"].lower():
                    people.append(self._copy_agent(agent))
            for contact in self._contacts.values():
                if needle in contact["name"].lower() or (
                    contact["reference"] is not None
                    and needle in contact["reference"].lower()
                ):
                    people.append(self._copy_contact(contact))
            now_dt = _coerce_now(None)
            result = {
                "people": people,
                "cases": [
                    self._case_view(c, now_dt)
                    for c in self._cases.values()
                    if needle in c["subject"].lower()
                ],
                "interactions": [
                    dict(i)
                    for i in self._interactions.values()
                    if needle in i["summary"].lower()
                    or (i["external_ref"] is not None
                        and needle in i["external_ref"].lower())
                ],
                "alerts": [
                    dict(a)
                    for a in self._alerts.values()
                    if needle in a["message"].lower()
                ],
            }
            self._audit(actor, "search", "search", details={"query": query})
            return result
