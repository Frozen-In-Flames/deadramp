"""CRM store: account/contact registry, service cases, interaction
records, guidance content registry, gap-finding records, module
configuration registry, reports, and search.

Clean-room implementation of the contract in UNION-SPEC.md.

Permission convention (mirrors the shipped groups): store methods
take an ``actor``. When the actor is a User-like object (it has a
``role`` attribute) the store calls :func:`crm.access.require` for
the method's action *before* any state change or id allocation, so
a denied operation consumes no id and changes nothing. Where a
plain string is passed it carries identity (for provenance) but no
role, so there is nothing to enforce against at this layer; the
service layer, which knows the role registry, is responsible for
enforcement in that case -- and it always passes User objects.

Every operation validates fully before it mutates anything: a
failed operation consumes no id and changes nothing. Ids are
sequential per object type with fixed prefixes (``acct-``,
``ct-``, ``case-``, ``int-``, ``guide-``, ``find-``, ``mod-``).

Privacy discipline (hard rule of this build): accounts and contacts
are keyed by an OPAQUE caller-supplied ``reference`` string. No
entity in this store has a field that can hold a real name, email,
phone number, SSN, date of birth, address, or salary. ``label`` is
a caller-chosen display string, never interpreted. Findings carry
their vendor-stated ``detail`` text verbatim; there is no score
field anywhere in this store, and no aggregate the claims do not
define is ever computed.

Derived status: a case's SLA breach is DERIVED at read time from
its stored ``due_at`` and the reference ``now`` -- it is never
stored. Derivation lives in exactly one small method,
:meth:`CrmStore._is_breached`, which the negative-control drill
patches.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

CASE_TYPES = ("inquiry", "problem", "request", "feedback", "general")
KNOWN_CASE_TYPES = frozenset(CASE_TYPES)
PRIORITIES = ("low", "normal", "high", "critical")
KNOWN_PRIORITIES = frozenset(PRIORITIES)
CHANNELS = ("guidance_session", "call", "chat", "email", "portal", "in_person", "system")
KNOWN_CHANNELS = frozenset(CHANNELS)
DIRECTIONS = ("inbound", "outbound", "internal")
KNOWN_DIRECTIONS = frozenset(DIRECTIONS)
GUIDE_KINDS = ("walkthrough", "tooltip", "checklist", "announcement")
KNOWN_GUIDE_KINDS = frozenset(GUIDE_KINDS)
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

FINDING_TRANSITIONS = {
    "open": frozenset({"acknowledged", "dismissed"}),
    "acknowledged": frozenset({"addressed", "dismissed"}),
    "addressed": frozenset(),
    "dismissed": frozenset(),
}


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


def _validate_optional_str(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string or None" % (what,))
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


def _validate_attributes(attributes):
    if attributes is None:
        return {}
    if not isinstance(attributes, dict):
        raise ValidationError("attributes must be a dict")
    return copy.deepcopy(attributes)


def _validate_steps(steps):
    if steps is None:
        return []
    if not isinstance(steps, (list, tuple)):
        raise ValidationError("steps must be a list of strings")
    result = []
    for step in steps:
        if not isinstance(step, str) or not step.strip():
            raise ValidationError("each step must be a non-empty string")
        result.append(step)
    return result


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class CrmStore:
    """In-memory store for the CRM records service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._accounts = {}
        self._contacts = {}
        self._cases = {}
        self._interactions = {}
        self._guides = {}
        self._findings = {}
        self._modules = {}
        self._counters = {
            "acct": 0, "ct": 0, "case": 0, "int": 0,
            "guide": 0, "find": 0, "mod": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _get_account_record(self, account_id):
        record = self._accounts.get(account_id)
        if record is None:
            raise NotFoundError("account not found: %r" % (account_id,))
        return record

    def _get_contact_record(self, contact_id):
        record = self._contacts.get(contact_id)
        if record is None:
            raise NotFoundError("contact not found: %r" % (contact_id,))
        return record

    def _get_case_record(self, case_id):
        record = self._cases.get(case_id)
        if record is None:
            raise NotFoundError("case not found: %r" % (case_id,))
        return record

    def _get_interaction_record(self, interaction_id):
        record = self._interactions.get(interaction_id)
        if record is None:
            raise NotFoundError("interaction not found: %r" % (interaction_id,))
        return record

    def _get_guide_record(self, guide_id):
        record = self._guides.get(guide_id)
        if record is None:
            raise NotFoundError("guide not found: %r" % (guide_id,))
        return record

    def _get_finding_record(self, finding_id):
        record = self._findings.get(finding_id)
        if record is None:
            raise NotFoundError("finding not found: %r" % (finding_id,))
        return record

    def _get_module_record(self, module_id):
        record = self._modules.get(module_id)
        if record is None:
            raise NotFoundError("module not found: %r" % (module_id,))
        return record

    @staticmethod
    def _copy_registry(record):
        copied = dict(record)
        copied["attributes"] = copy.deepcopy(record["attributes"])
        return copied

    @staticmethod
    def _copy_guide(guide):
        copied = dict(guide)
        copied["steps"] = list(guide["steps"])
        copied["versions"] = copy.deepcopy(guide["versions"])
        return copied

    @staticmethod
    def _copy_module(module):
        copied = dict(module)
        copied["versions"] = copy.deepcopy(module["versions"])
        return copied

    def _check_contact_account(self, contact, account_id):
        """A contact linked alongside an account must belong to it."""
        if account_id is not None and contact["account_id"] != account_id:
            raise ValidationError(
                "contact %r does not belong to account %r"
                % (contact["id"], account_id)
            )

    # -- derivation (single point; see module docstring) -------------

    def _is_breached(self, case, now_dt):
        """True iff the case is past due and not in a terminal-ish status.

        MUTATION DRILL NOTE: this method (``CrmStore._is_breached``
        in ``src/crm/store.py``) is the load-bearing derivation
        point for the negative-control drill: an overdue open case
        must read ``breached=True``.
        """
        if case.get("due_at") is None:
            return False
        if case["status"] in NON_BREACHING_STATUSES:
            return False
        due_dt = _parse_iso_datetime(case["due_at"], "due_at")
        return now_dt > due_dt

    def _case_view(self, case, now_dt):
        view = dict(case)
        view["breached"] = self._is_breached(case, now_dt)
        return view

    # -- registry: accounts ------------------------------------------

    def create_account(self, actor, reference, label=None, attributes=None):
        """Create an account keyed by an opaque ``reference``.

        Action: registry_write. Id prefix: acct-. ``reference`` is
        required, non-empty, and unique among accounts -- it is the
        embedding organization's own key for the account, never a
        real-world identifier interpreted by this build.
        """
        _require_actor(actor, "registry_write")
        _validate_non_empty(reference, "account reference")
        _validate_optional_str(label, "account label")
        attributes = _validate_attributes(attributes)
        with self._lock:
            for existing in self._accounts.values():
                if existing["reference"] == reference:
                    raise ValidationError(
                        "account reference %r already exists" % (reference,)
                    )
            account_id = self._next_id("acct")
            account = {
                "id": account_id,
                "reference": reference,
                "label": label,
                "attributes": attributes,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._accounts[account_id] = account
            self._audit(actor, "account_create", account_id,
                        details={"reference": reference})
            return self._copy_registry(account)

    def get_account(self, account_id, actor=None):
        """Return one account. Action: registry_read."""
        _maybe_require(actor, "registry_read")
        with self._lock:
            return self._copy_registry(self._get_account_record(account_id))

    def list_accounts(self, actor=None):
        """Return accounts sorted by id. Action: registry_read."""
        _maybe_require(actor, "registry_read")
        with self._lock:
            accounts = sorted(self._accounts.values(), key=lambda a: _id_num(a["id"]))
            return [self._copy_registry(a) for a in accounts]

    # -- registry: contacts ------------------------------------------

    def create_contact(self, actor, account_id, reference, label=None, attributes=None):
        """Create a contact under an account, keyed by an opaque
        ``reference`` unique among contacts.

        Action: registry_write. Id prefix: ct-. The account must
        exist.
        """
        _require_actor(actor, "registry_write")
        _validate_non_empty(reference, "contact reference")
        _validate_optional_str(label, "contact label")
        attributes = _validate_attributes(attributes)
        with self._lock:
            self._get_account_record(account_id)
            for existing in self._contacts.values():
                if existing["reference"] == reference:
                    raise ValidationError(
                        "contact reference %r already exists" % (reference,)
                    )
            contact_id = self._next_id("ct")
            contact = {
                "id": contact_id,
                "account_id": account_id,
                "reference": reference,
                "label": label,
                "attributes": attributes,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._contacts[contact_id] = contact
            self._audit(actor, "contact_create", contact_id,
                        details={"account_id": account_id, "reference": reference})
            return self._copy_registry(contact)

    def get_contact(self, contact_id, actor=None):
        """Return one contact. Action: registry_read."""
        _maybe_require(actor, "registry_read")
        with self._lock:
            return self._copy_registry(self._get_contact_record(contact_id))

    def list_contacts(self, actor=None, account_id=None):
        """Return contacts, optionally for one account.

        Action: registry_read.
        """
        _maybe_require(actor, "registry_read")
        with self._lock:
            if account_id is not None:
                self._get_account_record(account_id)
            contacts = sorted(self._contacts.values(), key=lambda c: _id_num(c["id"]))
            return [
                self._copy_registry(c) for c in contacts
                if account_id is None or c["account_id"] == account_id
            ]

    # -- cases ---------------------------------------------------------

    def create_case(self, actor, case_type, subject, account_id=None, contact_id=None,
                    assignee_ref=None, priority="normal", due_at=None):
        """Create a service case with status ``open``.

        Action: case_write. Id prefix: case-. Referenced ids must
        exist; a contact linked alongside an account must belong to
        that account. ``assignee_ref`` is an opaque caller-supplied
        staff reference. ``due_at`` must be a valid ISO-8601
        datetime string when given.
        """
        _require_actor(actor, "case_write")
        if case_type not in KNOWN_CASE_TYPES:
            raise ValidationError("case_type must be one of %s" % (", ".join(CASE_TYPES),))
        _validate_non_empty(subject, "case subject")
        if priority not in KNOWN_PRIORITIES:
            raise ValidationError("priority must be one of %s" % (", ".join(PRIORITIES),))
        _validate_optional_str(assignee_ref, "assignee_ref")
        if due_at is not None:
            _parse_iso_datetime(due_at, "due_at")
        with self._lock:
            if account_id is not None:
                self._get_account_record(account_id)
            if contact_id is not None:
                contact = self._get_contact_record(contact_id)
                self._check_contact_account(contact, account_id)
            case_id = self._next_id("case")
            case = {
                "id": case_id,
                "case_type": case_type,
                "subject": subject,
                "account_id": account_id,
                "contact_id": contact_id,
                "assignee_ref": assignee_ref,
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

    def assign_case(self, case_id, actor, assignee_ref):
        """Set a case's assignee reference. Action: case_write."""
        _require_actor(actor, "case_write")
        _validate_non_empty(assignee_ref, "assignee_ref")
        with self._lock:
            case = self._get_case_record(case_id)
            case["assignee_ref"] = assignee_ref
            case["updated_utc"] = _utc_now()
            self._audit(actor, "case_assign", case_id,
                        details={"assignee_ref": assignee_ref})
            return self._case_view(case, _coerce_now(None))

    def transition_case(self, case_id, actor, to_status):
        """Transition a case's status along the lifecycle.

        Action: case_write. Lifecycle: open->{in_progress,
        cancelled}, in_progress->{resolved, open, cancelled},
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

    def list_cases(self, actor=None, now=None, status=None, case_type=None,
                   account_id=None):
        """Return cases with derived ``breached``, optionally filtered.

        Action: case_read. ``status`` filters on the stored status.
        """
        _maybe_require(actor, "case_read")
        now_dt = _coerce_now(now)
        with self._lock:
            cases = list(self._cases.values())
            if status is not None:
                cases = [c for c in cases if c["status"] == status]
            if case_type is not None:
                cases = [c for c in cases if c["case_type"] == case_type]
            if account_id is not None:
                cases = [c for c in cases if c["account_id"] == account_id]
            return [self._case_view(c, now_dt) for c in cases]

    # -- interactions ----------------------------------------------------

    def record_interaction(self, actor, channel, direction, summary, account_id=None,
                           contact_id=None, case_id=None, guide_id=None,
                           outcome=None, external_ref=None):
        """Record an interaction. Action: interaction_write.

        Id prefix: int-. Interactions are IMMUTABLE records: there
        is deliberately no update or delete API for them. Referenced
        ids must exist; a contact linked alongside an account must
        belong to that account.
        """
        _require_actor(actor, "interaction_write")
        if channel not in KNOWN_CHANNELS:
            raise ValidationError("channel must be one of %s" % (", ".join(CHANNELS),))
        if direction not in KNOWN_DIRECTIONS:
            raise ValidationError("direction must be one of %s" % (", ".join(DIRECTIONS),))
        _validate_non_empty(summary, "interaction summary")
        _validate_optional_str(outcome, "outcome")
        _validate_optional_str(external_ref, "external_ref")
        with self._lock:
            if account_id is not None:
                self._get_account_record(account_id)
            if contact_id is not None:
                contact = self._get_contact_record(contact_id)
                self._check_contact_account(contact, account_id)
            if case_id is not None:
                self._get_case_record(case_id)
            if guide_id is not None:
                self._get_guide_record(guide_id)
            interaction_id = self._next_id("int")
            interaction = {
                "id": interaction_id,
                "channel": channel,
                "direction": direction,
                "summary": summary,
                "account_id": account_id,
                "contact_id": contact_id,
                "case_id": case_id,
                "guide_id": guide_id,
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

    def list_interactions(self, actor=None, case_id=None, account_id=None):
        """Return interactions, optionally filtered by case/account.

        Action: interaction_read.
        """
        _maybe_require(actor, "interaction_read")
        with self._lock:
            if case_id is not None:
                self._get_case_record(case_id)
            if account_id is not None:
                self._get_account_record(account_id)
            return [
                dict(i) for i in self._interactions.values()
                if (case_id is None or i["case_id"] == case_id)
                and (account_id is None or i["account_id"] == account_id)
            ]

    # -- guides (guidance content registry) ------------------------------

    def create_guide(self, actor, title, kind, target_ref, steps=None, enabled=True):
        """Create a guidance content record at version 1.

        Action: guide_write. Id prefix: guide-. ``target_ref`` is
        an opaque caller-supplied string naming the host surface
        the guidance belongs to; this build stores the record and
        renders nothing into any application. The guide carries a
        ``versions`` list; each version is ``{version, steps,
        enabled, target_ref, ts}``.
        """
        _require_actor(actor, "guide_write")
        _validate_non_empty(title, "guide title")
        if kind not in KNOWN_GUIDE_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(GUIDE_KINDS),))
        _validate_non_empty(target_ref, "target_ref")
        steps = _validate_steps(steps)
        if not isinstance(enabled, bool):
            raise ValidationError("enabled must be a bool")
        with self._lock:
            guide_id = self._next_id("guide")
            now = _utc_now()
            first = {
                "version": 1,
                "steps": list(steps),
                "enabled": enabled,
                "target_ref": target_ref,
                "ts": now,
            }
            guide = {
                "id": guide_id,
                "title": title,
                "kind": kind,
                "target_ref": target_ref,
                "steps": list(steps),
                "enabled": enabled,
                "version": 1,
                "versions": [first],
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._guides[guide_id] = guide
            self._audit(actor, "guide_create", guide_id, details={"title": title})
            return self._copy_guide(guide)

    def update_guide(self, guide_id, actor, steps=None, enabled=None, target_ref=None):
        """Append a new version to a guide. Action: guide_write.

        Unchanged fields are carried forward from the current
        version; the version counter is bumped by one.
        """
        _require_actor(actor, "guide_write")
        if steps is not None:
            steps = _validate_steps(steps)
        if enabled is not None and not isinstance(enabled, bool):
            raise ValidationError("enabled must be a bool")
        if target_ref is not None:
            _validate_non_empty(target_ref, "target_ref")
        with self._lock:
            guide = self._get_guide_record(guide_id)
            new_version = {
                "version": guide["version"] + 1,
                "steps": list(steps) if steps is not None else list(guide["steps"]),
                "enabled": enabled if enabled is not None else guide["enabled"],
                "target_ref": target_ref if target_ref is not None else guide["target_ref"],
                "ts": _utc_now(),
            }
            guide["versions"].append(new_version)
            guide["version"] = new_version["version"]
            guide["steps"] = list(new_version["steps"])
            guide["enabled"] = new_version["enabled"]
            guide["target_ref"] = new_version["target_ref"]
            guide["updated_utc"] = new_version["ts"]
            self._audit(actor, "guide_update", guide_id,
                        details={"version": new_version["version"]})
            return self._copy_guide(guide)

    def get_guide(self, guide_id, actor=None):
        """Return one guide. Action: guide_read."""
        _maybe_require(actor, "guide_read")
        with self._lock:
            return self._copy_guide(self._get_guide_record(guide_id))

    def list_guides(self, actor=None):
        """Return guides in creation order. Action: guide_read."""
        _maybe_require(actor, "guide_read")
        with self._lock:
            return [self._copy_guide(g) for g in self._guides.values()]

    # -- findings (gap-finding records) -----------------------------------

    def create_finding(self, actor, title, detail=None, severity="info",
                       account_id=None, source=None):
        """Record a gap / problem-area finding with status ``open``.

        Action: finding_write. Id prefix: find-. ``detail`` is the
        finding's text stored VERBATIM as supplied; ``source`` names
        where the finding came from. This build records findings --
        the engine that identifies gaps in a live application is
        Extended (see UNION-SPEC.md). No score is computed or stored.
        """
        _require_actor(actor, "finding_write")
        _validate_non_empty(title, "finding title")
        _validate_optional_str(detail, "finding detail")
        _validate_optional_str(source, "finding source")
        if severity not in KNOWN_SEVERITIES:
            raise ValidationError("severity must be one of %s" % (", ".join(SEVERITIES),))
        with self._lock:
            if account_id is not None:
                self._get_account_record(account_id)
            finding_id = self._next_id("find")
            finding = {
                "id": finding_id,
                "title": title,
                "detail": detail,
                "severity": severity,
                "source": source,
                "account_id": account_id,
                "status": "open",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
                "updated_utc": _utc_now(),
            }
            self._findings[finding_id] = finding
            self._audit(actor, "finding_create", finding_id,
                        details={"title": title, "severity": severity})
            return dict(finding)

    def transition_finding(self, finding_id, actor, to_status):
        """Transition a finding along its lifecycle.

        Action: finding_write. Lifecycle: open->{acknowledged,
        dismissed}, acknowledged->{addressed, dismissed},
        addressed->{}, dismissed->{}. Any other transition ->
        ValidationError.
        """
        _require_actor(actor, "finding_write")
        with self._lock:
            finding = self._get_finding_record(finding_id)
            allowed = FINDING_TRANSITIONS[finding["status"]]
            if to_status not in allowed:
                raise ValidationError(
                    "finding %r cannot transition from %r to %r"
                    % (finding_id, finding["status"], to_status)
                )
            finding["status"] = to_status
            finding["updated_utc"] = _utc_now()
            self._audit(actor, "finding_transition", finding_id,
                        details={"to_status": to_status})
            return dict(finding)

    def get_finding(self, finding_id, actor=None):
        """Return one finding. Action: finding_read."""
        _maybe_require(actor, "finding_read")
        with self._lock:
            return dict(self._get_finding_record(finding_id))

    def list_findings(self, actor=None, status=None, account_id=None):
        """Return findings, optionally filtered. Action: finding_read."""
        _maybe_require(actor, "finding_read")
        with self._lock:
            findings = list(self._findings.values())
            if status is not None:
                findings = [f for f in findings if f["status"] == status]
            if account_id is not None:
                findings = [f for f in findings if f["account_id"] == account_id]
            return [dict(f) for f in findings]

    # -- modules (configuration registry) ---------------------------------

    def create_module(self, actor, label, scope, settings_text, enabled=True):
        """Create a configuration module record at version 1.

        Action: config_write (admin only). Id prefix: mod-.
        ``settings_text`` is configuration text stored verbatim; it
        is never executed. The module carries a ``versions`` list;
        each version is ``{version, settings_text, enabled, ts}``.
        """
        _require_actor(actor, "config_write")
        _validate_non_empty(label, "module label")
        _validate_non_empty(scope, "module scope")
        _validate_non_empty(settings_text, "module settings_text")
        if not isinstance(enabled, bool):
            raise ValidationError("enabled must be a bool")
        with self._lock:
            module_id = self._next_id("mod")
            now = _utc_now()
            first = {
                "version": 1,
                "settings_text": settings_text,
                "enabled": enabled,
                "ts": now,
            }
            module = {
                "id": module_id,
                "label": label,
                "scope": scope,
                "settings_text": settings_text,
                "enabled": enabled,
                "version": 1,
                "versions": [first],
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._modules[module_id] = module
            self._audit(actor, "module_create", module_id, details={"label": label})
            return self._copy_module(module)

    def update_module(self, module_id, actor, settings_text=None, enabled=None):
        """Append a new version to a module. Action: config_write (admin).

        Unchanged fields are carried forward from the current
        version; the version counter is bumped by one.
        """
        _require_actor(actor, "config_write")
        if settings_text is not None:
            _validate_non_empty(settings_text, "module settings_text")
        if enabled is not None and not isinstance(enabled, bool):
            raise ValidationError("enabled must be a bool")
        with self._lock:
            module = self._get_module_record(module_id)
            new_version = {
                "version": module["version"] + 1,
                "settings_text": (
                    settings_text if settings_text is not None
                    else module["settings_text"]
                ),
                "enabled": enabled if enabled is not None else module["enabled"],
                "ts": _utc_now(),
            }
            module["versions"].append(new_version)
            module["version"] = new_version["version"]
            module["settings_text"] = new_version["settings_text"]
            module["enabled"] = new_version["enabled"]
            module["updated_utc"] = new_version["ts"]
            self._audit(actor, "module_update", module_id,
                        details={"version": new_version["version"]})
            return self._copy_module(module)

    def get_module(self, module_id, actor=None):
        """Return one module. Action: config_read."""
        _maybe_require(actor, "config_read")
        with self._lock:
            return self._copy_module(self._get_module_record(module_id))

    def list_modules(self, actor=None):
        """Return modules in creation order. Action: config_read."""
        _maybe_require(actor, "config_read")
        with self._lock:
            return [self._copy_module(m) for m in self._modules.values()]

    # -- reports ------------------------------------------------------------

    def report(self, actor=None, now=None):
        """Deterministic aggregate report at ``now``. Action: report_read.

        All counts are derived at call time over the registry's own
        records; the case breach count uses the same derivation
        point as the read views. An unlinked case counts under
        ``"unassigned"``, an interaction with no outcome under
        ``"none"``. No score or aggregate the claims do not define
        is computed -- counts of records only.
        """
        _maybe_require(actor, "report_read")
        now_dt = _coerce_now(now)
        with self._lock:
            by_status = {}
            by_type = {}
            by_account = {}
            breached = 0
            for case in self._cases.values():
                by_status[case["status"]] = by_status.get(case["status"], 0) + 1
                by_type[case["case_type"]] = by_type.get(case["case_type"], 0) + 1
                account_key = (
                    case["account_id"] if case["account_id"] is not None
                    else "unassigned"
                )
                by_account[account_key] = by_account.get(account_key, 0) + 1
                if self._is_breached(case, now_dt):
                    breached += 1
            by_channel = {}
            by_outcome = {}
            for interaction in self._interactions.values():
                by_channel[interaction["channel"]] = (
                    by_channel.get(interaction["channel"], 0) + 1
                )
                outcome_key = (
                    interaction["outcome"] if interaction["outcome"] is not None
                    else "none"
                )
                by_outcome[outcome_key] = by_outcome.get(outcome_key, 0) + 1
            by_kind = {}
            guides_enabled = 0
            for guide in self._guides.values():
                by_kind[guide["kind"]] = by_kind.get(guide["kind"], 0) + 1
                if guide["enabled"]:
                    guides_enabled += 1
            by_severity = {}
            by_finding_status = {}
            for finding in self._findings.values():
                by_severity[finding["severity"]] = (
                    by_severity.get(finding["severity"], 0) + 1
                )
                by_finding_status[finding["status"]] = (
                    by_finding_status.get(finding["status"], 0) + 1
                )
            modules_enabled = sum(1 for m in self._modules.values() if m["enabled"])
            return {
                "accounts": {"total": len(self._accounts)},
                "contacts": {"total": len(self._contacts)},
                "cases": {
                    "total": len(self._cases),
                    "by_status": by_status,
                    "by_type": by_type,
                    "by_account": by_account,
                    "breached": breached,
                },
                "interactions": {
                    "total": len(self._interactions),
                    "by_channel": by_channel,
                    "by_outcome": by_outcome,
                },
                "guides": {
                    "total": len(self._guides),
                    "by_kind": by_kind,
                    "enabled": guides_enabled,
                },
                "findings": {
                    "total": len(self._findings),
                    "by_severity": by_severity,
                    "by_status": by_finding_status,
                },
                "modules": {
                    "total": len(self._modules),
                    "enabled": modules_enabled,
                },
            }

    # -- search -----------------------------------------------------------------

    def search(self, query, actor):
        """Literal case-insensitive substring search.

        Over accounts/contacts (label + reference), cases (subject),
        interactions (summary + external_ref), findings (title +
        detail), and guides (title). Returns {accounts, contacts,
        cases, interactions, findings, guides}. Action: case_read.
        An empty query -> ValidationError. Records a 'search' audit
        entry.
        """
        _require_actor(actor, "case_read")
        if not isinstance(query, str) or not query.strip():
            raise ValidationError("query must be a non-empty string")
        needle = query.lower()
        with self._lock:
            def _label_ref_match(record):
                label = record.get("label")
                return (
                    (label is not None and needle in label.lower())
                    or needle in record["reference"].lower()
                )

            now_dt = _coerce_now(None)
            result = {
                "accounts": [
                    self._copy_registry(a) for a in self._accounts.values()
                    if _label_ref_match(a)
                ],
                "contacts": [
                    self._copy_registry(c) for c in self._contacts.values()
                    if _label_ref_match(c)
                ],
                "cases": [
                    self._case_view(c, now_dt) for c in self._cases.values()
                    if needle in c["subject"].lower()
                ],
                "interactions": [
                    dict(i) for i in self._interactions.values()
                    if needle in i["summary"].lower()
                    or (i["external_ref"] is not None
                        and needle in i["external_ref"].lower())
                ],
                "findings": [
                    dict(f) for f in self._findings.values()
                    if needle in f["title"].lower()
                    or (f["detail"] is not None and needle in f["detail"].lower())
                ],
                "guides": [
                    self._copy_guide(g) for g in self._guides.values()
                    if needle in g["title"].lower()
                ],
            }
            self._audit(actor, "search", "search", details={"query": query})
            return result
