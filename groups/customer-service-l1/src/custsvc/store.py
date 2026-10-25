"""In-memory store for the customer-service records substrate.

Clean-room implementation of the Group 26 union core (see
``../UNION-SPEC.md``). The store holds records only: cases with a
lifecycle, requesters keyed by opaque caller-supplied references,
responders, alert records, on-call schedules, automation rule records,
and status updates. It executes nothing: automation rules are
registered, never run; alert records are the substrate that detection
engines (Extended) would feed, not a detection engine.

Derivations are computed at read time, never stored:

- a case's ``breached`` flag: past its ``due_at`` and not in a terminal
  status (``resolved`` / ``closed``) -- :meth:`CustsvcStore._is_breached`
  is the single load-bearing derivation point (see the negative control
  in ``tests/README.md``);
- a schedule's current on-call responder: pure date arithmetic over the
  rotation records (anchor date + period), no engine;
- the public status view: derived from open-case severities and the
  public updates posted against them.

Privacy discipline (structural, tested): requester records hold an
opaque caller-supplied ``ref`` and a display ``label`` only. No field
in any entity can hold a phone number, email address, or other real
identifier; alert sources are opaque ``source_ref`` strings supplied
by the caller.
"""

import threading
from datetime import datetime, date, timezone

from .access import User, require
from .audit import AuditLog, actor_name
from .errors import NotFoundError, ValidationError

PRIORITIES = ("low", "normal", "high", "critical")
CASE_STATUSES = ("new", "open", "in_progress", "resolved", "closed")
TERMINAL_STATUSES = ("resolved", "closed")
ALERT_SEVERITIES = ("info", "warning", "major", "critical")
ALERT_STATES = ("new", "acknowledged", "resolved")

# Lifecycle: current status -> set of statuses it may move to.
# Reopen is resolved/closed -> open.
_TRANSITIONS = {
    "new": {"open", "closed"},
    "open": {"in_progress", "resolved", "closed"},
    "in_progress": {"open", "resolved", "closed"},
    "resolved": {"closed", "open"},
    "closed": {"open"},
}


def _utc_now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso_datetime(value, field):
    """Parse an ISO-8601 datetime; naive values are read as UTC."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise ValidationError("%s is not a valid ISO-8601 datetime: %r" % (field, value))
    else:
        raise ValidationError("%s must be an ISO-8601 datetime string" % (field,))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_iso_date(value, field):
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise ValidationError("%s is not a valid ISO date: %r" % (field, value))
    raise ValidationError("%s must be an ISO date string" % (field,))


def _require_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (field,))
    return value


class CustsvcStore:
    """The customer-service records substrate (single-tenant, in memory)."""

    def __init__(self, audit=None):
        self.audit = audit if audit is not None else AuditLog()
        self._lock = threading.Lock()
        self._requesters = {}
        self._requester_id_by_ref = {}
        self._responders = {}
        self._cases = {}
        self._updates = {}
        self._alerts = {}
        self._schedules = {}
        self._rules = {}
        self._counters = {"req": 0, "rsp": 0, "case": 0, "upd": 0,
                          "alert": 0, "sched": 0, "rule": 0}

    # -- internals -----------------------------------------------------

    def _next_id(self, kind):
        self._counters[kind] += 1
        return "%s-%d" % (kind, self._counters[kind])

    def _check(self, actor, action):
        # Plain-string actors carry identity only; enforcement happens
        # for User actors here and for everyone at the service layer.
        if isinstance(actor, User):
            require(actor, action)

    def _record(self, actor, action, target, details=None):
        self.audit.record(actor_name(actor), action, target, details)

    def _get(self, table, obj_id, kind):
        obj = table.get(obj_id)
        if obj is None:
            raise NotFoundError("%s not found: %r" % (kind, obj_id))
        return obj

    # -- requesters (opaque references only) ---------------------------

    def create_requester(self, ref, label, actor):
        """Register a requester by opaque caller-supplied reference.

        The record shape is exactly ``{id, ref, label, created_utc,
        created_by}`` -- there is deliberately no field that could hold
        a phone number, email address, or real identifier.
        """
        self._check(actor, "requester_write")
        _require_text(ref, "ref")
        _require_text(label, "label")
        with self._lock:
            if ref in self._requester_id_by_ref:
                raise ValidationError("requester ref already registered: %r" % (ref,))
            rid = self._next_id("req")
            rec = {"id": rid, "ref": ref, "label": label,
                   "created_utc": _iso(_utc_now()), "created_by": actor_name(actor)}
            self._requesters[rid] = rec
            self._requester_id_by_ref[ref] = rid
        self._record(actor, "requester_create", rid, {"ref": ref})
        return dict(rec)

    def get_requester(self, requester_id, actor):
        self._check(actor, "requester_read")
        return dict(self._get(self._requesters, requester_id, "requester"))

    def get_requester_by_ref(self, ref, actor):
        self._check(actor, "requester_read")
        rid = self._requester_id_by_ref.get(ref)
        if rid is None:
            raise NotFoundError("requester ref not found: %r" % (ref,))
        return dict(self._requesters[rid])

    def list_requesters(self, actor):
        self._check(actor, "requester_read")
        return [dict(r) for r in self._requesters.values()]

    # -- responders (directory) ----------------------------------------

    def create_responder(self, label, team, actor):
        """Register a responder (agent) record: labels only."""
        self._check(actor, "responder_write")
        _require_text(label, "label")
        _require_text(team, "team")
        with self._lock:
            rid = self._next_id("rsp")
            rec = {"id": rid, "label": label, "team": team,
                   "created_utc": _iso(_utc_now()), "created_by": actor_name(actor)}
            self._responders[rid] = rec
        self._record(actor, "responder_create", rid, {"team": team})
        return dict(rec)

    def get_responder(self, responder_id, actor):
        self._check(actor, "responder_read")
        return dict(self._get(self._responders, responder_id, "responder"))

    def list_responders(self, actor):
        self._check(actor, "responder_read")
        return [dict(r) for r in self._responders.values()]

    # -- cases -----------------------------------------------------------

    def create_case(self, title, body, requester_ref, actor, priority="normal",
                    channel=None, due_at=None, assignee=None):
        """Open a case. Id prefix: case-. Referenced ids must exist."""
        self._check(actor, "case_write")
        _require_text(title, "title")
        if not isinstance(body, str):
            raise ValidationError("body must be a string")
        if priority not in PRIORITIES:
            raise ValidationError("priority must be one of %s" % (PRIORITIES,))
        if requester_ref not in self._requester_id_by_ref:
            raise NotFoundError("requester ref not found: %r" % (requester_ref,))
        if assignee is not None and assignee not in self._responders:
            raise NotFoundError("responder not found: %r" % (assignee,))
        due_iso = None
        if due_at is not None:
            due_iso = _iso(_parse_iso_datetime(due_at, "due_at"))
        with self._lock:
            cid = self._next_id("case")
            rec = {"id": cid, "title": title, "body": body,
                   "requester_ref": requester_ref, "priority": priority,
                   "channel": channel, "status": "new", "assignee": assignee,
                   "due_at": due_iso, "created_utc": _iso(_utc_now()),
                   "created_by": actor_name(actor), "update_ids": []}
            self._cases[cid] = rec
        self._record(actor, "case_create", cid,
                     {"priority": priority, "requester_ref": requester_ref})
        return self._case_view(rec, _utc_now())

    def _is_breached(self, case, now_dt):
        """True iff the case is past due and not in a terminal status.

        Single derivation point for breach state; see the mutation
        record in tests/README.md (negative control).
        """
        if case.get("due_at") is None or case["status"] in TERMINAL_STATUSES:
            return False
        return now_dt > _parse_iso_datetime(case["due_at"], "due_at")

    def _case_view(self, case, now_dt):
        view = dict(case)
        view["update_ids"] = list(case["update_ids"])
        view["breached"] = self._is_breached(case, now_dt)
        return view

    def get_case(self, case_id, actor, now=None):
        self._check(actor, "case_read")
        now_dt = _parse_iso_datetime(now, "now") if now is not None else _utc_now()
        return self._case_view(self._get(self._cases, case_id, "case"), now_dt)

    def list_cases(self, actor, now=None, status=None, priority=None, assignee=None):
        self._check(actor, "case_read")
        now_dt = _parse_iso_datetime(now, "now") if now is not None else _utc_now()
        out = []
        for case in self._cases.values():
            if status is not None and case["status"] != status:
                continue
            if priority is not None and case["priority"] != priority:
                continue
            if assignee is not None and case["assignee"] != assignee:
                continue
            out.append(self._case_view(case, now_dt))
        return out

    def set_case_status(self, case_id, status, actor):
        """Move a case along its lifecycle; invalid moves are rejected."""
        self._check(actor, "case_write")
        case = self._get(self._cases, case_id, "case")
        if status not in CASE_STATUSES:
            raise ValidationError("status must be one of %s" % (CASE_STATUSES,))
        if status not in _TRANSITIONS[case["status"]]:
            raise ValidationError(
                "case %s may not move from %s to %s" % (case_id, case["status"], status))
        old = case["status"]
        case["status"] = status
        self._record(actor, "case_status", case_id, {"from": old, "to": status})
        return self._case_view(case, _utc_now())

    def assign_case(self, case_id, responder_id, actor):
        """Assign (or reassign) a case to a responder."""
        self._check(actor, "case_write")
        case = self._get(self._cases, case_id, "case")
        if responder_id not in self._responders:
            raise NotFoundError("responder not found: %r" % (responder_id,))
        old = case["assignee"]
        case["assignee"] = responder_id
        self._record(actor, "case_assign", case_id, {"from": old, "to": responder_id})
        return self._case_view(case, _utc_now())

    def add_case_update(self, case_id, body, actor, public=False):
        """Post an update against a case; ``public`` updates feed the
        status view, internal ones do not."""
        self._check(actor, "case_write")
        case = self._get(self._cases, case_id, "case")
        _require_text(body, "body")
        with self._lock:
            uid = self._next_id("upd")
            rec = {"id": uid, "case_id": case_id, "body": body,
                   "public": bool(public), "created_utc": _iso(_utc_now()),
                   "created_by": actor_name(actor)}
            self._updates[uid] = rec
            case["update_ids"].append(uid)
        self._record(actor, "case_update", case_id, {"update": uid, "public": bool(public)})
        return dict(rec)

    def list_case_updates(self, case_id, actor):
        self._check(actor, "case_read")
        case = self._get(self._cases, case_id, "case")
        return [dict(self._updates[u]) for u in case["update_ids"]]

    # -- alert records ---------------------------------------------------

    def ingest_alert(self, source_ref, summary, severity, actor, case_id=None):
        """Record one alert/event. Ingestion is record-keeping: the
        detection that produced the alert belongs to source systems
        (Extended); this substrate stores, triages and links it."""
        self._check(actor, "alert_write")
        _require_text(source_ref, "source_ref")
        _require_text(summary, "summary")
        if severity not in ALERT_SEVERITIES:
            raise ValidationError("severity must be one of %s" % (ALERT_SEVERITIES,))
        if case_id is not None and case_id not in self._cases:
            raise NotFoundError("case not found: %r" % (case_id,))
        with self._lock:
            aid = self._next_id("alert")
            rec = {"id": aid, "source_ref": source_ref, "summary": summary,
                   "severity": severity, "state": "new", "case_id": case_id,
                   "created_utc": _iso(_utc_now()), "created_by": actor_name(actor)}
            self._alerts[aid] = rec
        self._record(actor, "alert_ingest", aid,
                     {"severity": severity, "source_ref": source_ref})
        return dict(rec)

    def ingest_alerts(self, alerts, actor):
        """Bulk ingest: a list of alert dicts, applied atomically --
        if any entry is invalid, none are recorded."""
        if not isinstance(alerts, list) or not alerts:
            raise ValidationError("alerts must be a non-empty list")
        # Validate the whole batch first, so a bad entry means nothing
        # is recorded at all (records or audit).
        for item in alerts:
            if not isinstance(item, dict):
                raise ValidationError("each alert must be an object")
            _require_text(item.get("source_ref"), "source_ref")
            _require_text(item.get("summary"), "summary")
            if item.get("severity") not in ALERT_SEVERITIES:
                raise ValidationError(
                    "severity must be one of %s" % (ALERT_SEVERITIES,))
            if item.get("case_id") is not None and item["case_id"] not in self._cases:
                raise NotFoundError("case not found: %r" % (item["case_id"],))
        return [self.ingest_alert(item.get("source_ref"), item.get("summary"),
                                  item.get("severity"), actor,
                                  case_id=item.get("case_id"))
                for item in alerts]

    def _alert_transition(self, alert_id, state, actor, action):
        self._check(actor, "alert_write")
        alert = self._get(self._alerts, alert_id, "alert")
        alert["state"] = state
        self._record(actor, action, alert_id, {"state": state})
        return dict(alert)

    def acknowledge_alert(self, alert_id, actor):
        return self._alert_transition(alert_id, "acknowledged", actor, "alert_acknowledge")

    def resolve_alert(self, alert_id, actor):
        return self._alert_transition(alert_id, "resolved", actor, "alert_resolve")

    def link_alert(self, alert_id, case_id, actor):
        self._check(actor, "alert_write")
        alert = self._get(self._alerts, alert_id, "alert")
        if case_id not in self._cases:
            raise NotFoundError("case not found: %r" % (case_id,))
        alert["case_id"] = case_id
        self._record(actor, "alert_link", alert_id, {"case_id": case_id})
        return dict(alert)

    def list_alerts(self, actor, state=None, case_id=None):
        self._check(actor, "alert_read")
        out = []
        for alert in self._alerts.values():
            if state is not None and alert["state"] != state:
                continue
            if case_id is not None and alert["case_id"] != case_id:
                continue
            out.append(dict(alert))
        return out

    # -- on-call schedules -----------------------------------------------

    def create_schedule(self, name, responder_ids, actor, period_days=7,
                        anchor=None):
        """Register an on-call rotation: an ordered list of responder
        ids, each on call for ``period_days`` starting at ``anchor``
        (an ISO date; defaults to today, UTC)."""
        self._check(actor, "schedule_write")
        _require_text(name, "name")
        if not isinstance(responder_ids, list) or not responder_ids:
            raise ValidationError("responder_ids must be a non-empty list")
        for rid in responder_ids:
            if rid not in self._responders:
                raise NotFoundError("responder not found: %r" % (rid,))
        if not isinstance(period_days, int) or isinstance(period_days, bool) \
                or period_days < 1:
            raise ValidationError("period_days must be a positive integer")
        anchor_date = _parse_iso_date(anchor, "anchor") if anchor is not None \
            else _utc_now().date()
        with self._lock:
            sid = self._next_id("sched")
            rec = {"id": sid, "name": name, "responder_ids": list(responder_ids),
                   "period_days": period_days, "anchor": anchor_date.isoformat(),
                   "created_utc": _iso(_utc_now()), "created_by": actor_name(actor)}
            self._schedules[sid] = rec
        self._record(actor, "schedule_create", sid, {"members": len(responder_ids)})
        return self._schedule_view(rec)

    def _schedule_view(self, sched):
        view = dict(sched)
        view["responder_ids"] = list(sched["responder_ids"])
        return view

    def get_schedule(self, schedule_id, actor):
        self._check(actor, "schedule_read")
        return self._schedule_view(self._get(self._schedules, schedule_id, "schedule"))

    def list_schedules(self, actor):
        self._check(actor, "schedule_read")
        return [self._schedule_view(s) for s in self._schedules.values()]

    def on_call(self, schedule_id, actor, at=None):
        """Derive who is on call at ``at`` (ISO datetime or date;
        default now). Pure date arithmetic over the rotation records:
        whole periods elapsed since the anchor, modulo rotation size.
        Dates before the anchor wrap backwards through the rotation."""
        self._check(actor, "schedule_read")
        sched = self._get(self._schedules, schedule_id, "schedule")
        if at is None:
            at_date = _utc_now().date()
        elif isinstance(at, str) and "T" not in at:
            at_date = _parse_iso_date(at, "at")
        else:
            at_date = _parse_iso_datetime(at, "at").date()
        anchor = date.fromisoformat(sched["anchor"])
        periods = (at_date - anchor).days // sched["period_days"]
        idx = periods % len(sched["responder_ids"])
        responder = self._responders[sched["responder_ids"][idx]]
        return {"schedule_id": schedule_id, "date": at_date.isoformat(),
                "responder_id": responder["id"], "responder_label": responder["label"]}

    # -- automation rule registry (records only, never executed) ---------

    def create_rule(self, name, trigger, condition, action_text, actor):
        """Register an automation rule as a RECORD. The registry never
        evaluates conditions and never executes actions; execution
        engines are an Extended function (UNION-SPEC.md)."""
        self._check(actor, "rule_write")
        _require_text(name, "name")
        _require_text(trigger, "trigger")
        _require_text(condition, "condition")
        _require_text(action_text, "action_text")
        with self._lock:
            rid = self._next_id("rule")
            rec = {"id": rid, "name": name, "trigger": trigger,
                   "condition": condition, "action_text": action_text,
                   "enabled": True, "created_utc": _iso(_utc_now()),
                   "created_by": actor_name(actor)}
            self._rules[rid] = rec
        self._record(actor, "rule_create", rid, {"trigger": trigger})
        return dict(rec)

    def set_rule_enabled(self, rule_id, enabled, actor):
        self._check(actor, "rule_write")
        rule = self._get(self._rules, rule_id, "rule")
        rule["enabled"] = bool(enabled)
        self._record(actor, "rule_enabled", rule_id, {"enabled": bool(enabled)})
        return dict(rule)

    def list_rules(self, actor):
        self._check(actor, "rule_read")
        return [dict(r) for r in self._rules.values()]

    # -- status view, reporting, search (all derived at read) ------------

    def public_status(self, actor, now=None):
        """The external-facing status view, derived at read: overall
        state from open-case priorities, plus the public updates posted
        against open cases. Internal updates never appear here."""
        self._check(actor, "case_read")
        now_dt = _parse_iso_datetime(now, "now") if now is not None else _utc_now()
        open_cases = [c for c in self._cases.values()
                      if c["status"] not in TERMINAL_STATUSES]
        if any(c["priority"] == "critical" for c in open_cases):
            overall = "outage"
        elif any(c["priority"] == "high" or self._is_breached(c, now_dt)
                 for c in open_cases):
            overall = "degraded"
        else:
            overall = "operational"
        updates = []
        for case in open_cases:
            for uid in case["update_ids"]:
                upd = self._updates[uid]
                if upd["public"]:
                    updates.append({"case_id": case["id"], "update_id": uid,
                                    "body": upd["body"],
                                    "created_utc": upd["created_utc"]})
        updates.sort(key=lambda u: u["created_utc"])
        return {"overall": overall, "open_cases": len(open_cases),
                "breached_cases": sum(1 for c in open_cases
                                      if self._is_breached(c, now_dt)),
                "public_updates": updates}

    def report_summary(self, actor, now=None):
        """Registry reporting: counts over the substrate's own records.
        (Reporting engines beyond this are Extended.)"""
        self._check(actor, "report_read")
        now_dt = _parse_iso_datetime(now, "now") if now is not None else _utc_now()
        by_status = {s: 0 for s in CASE_STATUSES}
        by_priority = {p: 0 for p in PRIORITIES}
        breached = 0
        for case in self._cases.values():
            by_status[case["status"]] += 1
            by_priority[case["priority"]] += 1
            if self._is_breached(case, now_dt):
                breached += 1
        alerts_by_state = {s: 0 for s in ALERT_STATES}
        for alert in self._alerts.values():
            alerts_by_state[alert["state"]] += 1
        on_call_now = []
        for sched in self._schedules.values():
            oc = self.on_call(sched["id"], actor, at=now_dt)
            on_call_now.append({"schedule_id": sched["id"], "name": sched["name"],
                                "responder_id": oc["responder_id"]})
        return {"cases_by_status": by_status, "cases_by_priority": by_priority,
                "breached_cases": breached, "alerts_by_state": alerts_by_state,
                "requesters": len(self._requesters),
                "responders": len(self._responders),
                "rules": len(self._rules), "on_call_now": on_call_now}

    def search_cases(self, query, actor, now=None):
        """Substring search over case titles, bodies and requester
        labels (registry metadata search, not a search engine)."""
        self._check(actor, "case_read")
        _require_text(query, "query")
        now_dt = _parse_iso_datetime(now, "now") if now is not None else _utc_now()
        needle = query.lower()
        out = []
        for case in self._cases.values():
            label = ""
            rid = self._requester_id_by_ref.get(case["requester_ref"])
            if rid is not None:
                label = self._requesters[rid]["label"]
            if needle in case["title"].lower() or needle in case["body"].lower() \
                    or needle in label.lower():
                out.append(self._case_view(case, now_dt))
        return out
