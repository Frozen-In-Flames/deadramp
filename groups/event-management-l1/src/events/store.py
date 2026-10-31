"""Events store: organizer and vendor registries, event and
session records, preparation task records, outreach records, and
matchmaking rounds with participation records and derived matches.

Clean-room implementation of the union spec's implementation
contract.

Role permission is enforced on every operation when the actor is a
User-like object: the action named for the operation must be in the
actor's role permission set (see :mod:`events.access`). A plain
string actor carries identity (for provenance) but no role, so role
enforcement for those happens in the service layer (the sibling
builds' convention).

Every operation validates fully before it mutates anything: a
failed operation consumes no id and changes nothing. Ids are
sequential per object type with fixed prefixes (``org-``, ``ven-``,
``evt-``, ``prep-``, ``ses-``, ``out-``, ``rnd-``, ``part-``).

Derivation discipline: any status that depends on a date is derived
at read time and never stored. An event's (or session's) status
(``upcoming`` / ``live`` / ``concluded``) is computed from its
recorded window against the read clock; the stored record carries
no status key. Event-driven state, by contrast, is stored, as in
the sibling builds' record lifecycles: a preparation task's done
flag and a matchmaking round's ``open`` / ``closed`` state change
only through recorded actions.

Match discipline (the signature invariant): a matchmaking round
records the capability tags an organizer requires; a vendor's
participation record states the capability tags the vendor records
for itself. The round's matches -- the participations whose tag
set *covers* the round's required tags -- are computed on read
from the participation records alone by the single seam
:func:`_derive_matches`. No match is ever stored, and there is no
score anywhere: coverage is set inclusion, a yes-or-no fact about
recorded tags, not a rating of any vendor. The view returns the
qualifying participations in participation sequence order --
registration order, not a ranking.

Money discipline: there is none, because there is nothing to
apply it to. The fork's description names no fees, prices,
payments, ticketing, or sponsorship amounts (a checked absence),
so no record shape carries a money field.

Privacy discipline: organizers and vendors are known only by a
caller-supplied opaque ``ref`` and a label; speakers are opaque
references; capability tags are caller-stated text. No entity
shape has a field that can hold a real name, address, email, or
phone number.

The store records every successful mutation to its audit log (when
one is attached). Reads are not audited here; denied attempts and
audit reads are the HTTP layer's responsibility, so nothing is
recorded twice.
"""

import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, ValidationError

EVENT_FORMATS = ("onsite", "hybrid", "virtual")
SESSION_KINDS = ("webinar", "roundtable", "speaker_engagement")
WINDOW_STATUSES = ("upcoming", "live", "concluded")
ROUND_STATUSES = ("open", "closed")


def _utc_now():
    return datetime.now(timezone.utc)


def _parse_moment(value, field):
    """Parse an ISO date or datetime into an aware datetime."""
    if isinstance(value, datetime):
        moment = value
    elif isinstance(value, str):
        text = value.strip()
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
                moment = datetime.strptime(text, "%Y-%m-%d")
            else:
                moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            raise ValidationError("%s is not an ISO date or datetime: %r" % (field, value))
    else:
        raise ValidationError("%s must be an ISO date or datetime string" % field)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _optional_text(value, field):
    if value is None:
        return None
    return _text(value, field)


def _tags(value, field):
    """Validate and normalize a capability-tag list.

    Tags are caller-stated text, normalized to stripped lowercase,
    deduplicated preserving first-seen order. The value must be a
    list (possibly empty) of non-empty strings.
    """
    if not isinstance(value, list):
        raise ValidationError("%s must be a list of tag strings" % field)
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError("%s must contain only non-empty strings" % field)
        tag = item.strip().lower()
        if tag not in result:
            result.append(tag)
    return result


def _derive_matches(participations, required_tags):
    """Match derivation seam: the participations whose recorded
    capability tags cover the round's recorded required tags.

    Pure function over the participation record list. Returns the
    qualifying participation records in sequence (registration)
    order. Coverage is set inclusion -- a yes-or-no fact about
    recorded tags. This is the round's own qualification rule, not
    a score, rating, or ranking of any vendor: a participation
    either covers the required tags or it does not, and the
    returned order is registration order.
    """
    required = set(required_tags)
    ordered = sorted(participations, key=lambda p: p["seq"])
    return [p for p in ordered if required.issubset(p["capability_tags"])]


class EventsStore:
    """In-memory event-management records store with an optional
    audit log."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._organizers = {}
        self._vendors = {}
        self._events = {}
        self._preparation = {}
        self._sessions = {}
        self._outreach = {}
        self._rounds = {}
        self._participations = {}
        self._counters = {}

    # -- internal helpers -------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _record(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor, action, target, details)

    @staticmethod
    def _check_role(actor, action):
        if hasattr(actor, "role"):
            require(actor, action)

    def _organizer(self, organizer_id):
        organizer = self._organizers.get(organizer_id)
        if organizer is None:
            raise NotFoundError("no such organizer: %r" % (organizer_id,))
        return organizer

    def _vendor(self, vendor_id):
        vendor = self._vendors.get(vendor_id)
        if vendor is None:
            raise NotFoundError("no such vendor: %r" % (vendor_id,))
        return vendor

    def _event(self, event_id):
        event = self._events.get(event_id)
        if event is None:
            raise NotFoundError("no such event: %r" % (event_id,))
        return event

    def _round(self, round_id):
        round_ = self._rounds.get(round_id)
        if round_ is None:
            raise NotFoundError("no such matchmaking round: %r" % (round_id,))
        return round_

    # -- registries ---------------------------------------------------------

    def _create_party(self, actor, table, prefix, kind, ref, label):
        self._check_role(actor, "register")
        _text(ref, "ref")
        _text(label, "label")
        with self._lock:
            for existing in table.values():
                if existing["ref"] == ref:
                    raise ValidationError("%s ref already exists: %r" % (kind, ref))
            party = {
                "id": self._mint(prefix),
                "ref": ref,
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            table[party["id"]] = party
        self._record(actor, "%s_create" % kind, party["id"], {"ref": ref})
        return dict(party)

    def create_organizer(self, actor, ref, label):
        """Register an event organizer by opaque reference."""
        return self._create_party(actor, self._organizers, "org-",
                                  "organizer", ref, label)

    def get_organizer(self, actor, organizer_id):
        self._check_role(actor, "read")
        return dict(self._organizer(organizer_id))

    def list_organizers(self, actor):
        self._check_role(actor, "read")
        return [dict(o) for o in self._organizers.values()]

    def create_vendor(self, actor, ref, label):
        """Register a vendor organization by opaque reference."""
        return self._create_party(actor, self._vendors, "ven-",
                                  "vendor", ref, label)

    def get_vendor(self, actor, vendor_id):
        self._check_role(actor, "read")
        return dict(self._vendor(vendor_id))

    def list_vendors(self, actor):
        self._check_role(actor, "read")
        return [dict(v) for v in self._vendors.values()]

    # -- events -----------------------------------------------------------

    @staticmethod
    def _window_status(record, moment):
        if moment < _parse_moment(record["starts_at"], "starts_at"):
            return "upcoming"
        if moment > _parse_moment(record["ends_at"], "ends_at"):
            return "concluded"
        return "live"

    def _event_view(self, event, now=None):
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        view = dict(event)
        view["status"] = self._window_status(event, moment)
        view["session_count"] = sum(
            1 for s in self._sessions.values() if s["event_id"] == event["id"]
        )
        view["round_count"] = sum(
            1 for r in self._rounds.values() if r["event_id"] == event["id"]
        )
        return view

    def create_event(self, actor, organizer_id, title, format,
                     starts_at, ends_at, location_note=None):
        """Record an event for an organizer. ``format`` is one of
        the claimed formats (onsite / hybrid / virtual). The
        event's status is derived at read; nothing about it is
        stored, ever."""
        self._check_role(actor, "manage")
        self._organizer(organizer_id)
        _text(title, "title")
        if format not in EVENT_FORMATS:
            raise ValidationError("unknown event format: %r" % (format,))
        _optional_text(location_note, "location_note")
        starts = _parse_moment(starts_at, "starts_at")
        ends = _parse_moment(ends_at, "ends_at")
        if ends < starts:
            raise ValidationError("ends_at must not precede starts_at")
        with self._lock:
            event = {
                "id": self._mint("evt-"),
                "organizer_id": organizer_id,
                "title": title,
                "format": format,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "location_note": location_note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._events[event["id"]] = event
        self._record(actor, "event_create", event["id"],
                     {"organizer_id": organizer_id})
        return self._event_view(event)

    def get_event(self, actor, event_id, now=None):
        self._check_role(actor, "read")
        return self._event_view(self._event(event_id), now=now)

    def list_events(self, actor, organizer_id=None, format=None,
                    status=None, now=None):
        self._check_role(actor, "read")
        if organizer_id is not None:
            self._organizer(organizer_id)
        if format is not None and format not in EVENT_FORMATS:
            raise ValidationError("unknown event format: %r" % (format,))
        if status is not None and status not in WINDOW_STATUSES:
            raise ValidationError("unknown event status: %r" % (status,))
        result = []
        for event in self._events.values():
            if organizer_id is not None and event["organizer_id"] != organizer_id:
                continue
            if format is not None and event["format"] != format:
                continue
            view = self._event_view(event, now=now)
            if status is not None and view["status"] != status:
                continue
            result.append(view)
        return result

    # -- preparation tasks ---------------------------------------------------

    def add_preparation_task(self, actor, event_id, label):
        """Record a preparation task for an event -- the records
        form of the claimed event-preparation function. A task is
        created not-done and completed by a recorded action."""
        self._check_role(actor, "manage")
        self._event(event_id)
        _text(label, "label")
        with self._lock:
            task = {
                "id": self._mint("prep-"),
                "event_id": event_id,
                "label": label,
                "done": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._preparation[task["id"]] = task
        self._record(actor, "preparation_add", task["id"],
                     {"event_id": event_id})
        return dict(task)

    def complete_preparation_task(self, actor, task_id):
        """Mark a preparation task done, by recorded action."""
        self._check_role(actor, "manage")
        task = self._preparation.get(task_id)
        if task is None:
            raise NotFoundError("no such preparation task: %r" % (task_id,))
        with self._lock:
            if task["done"]:
                raise ValidationError(
                    "preparation task %s is already done" % task_id)
            task["done"] = True
        self._record(actor, "preparation_complete", task_id, {})
        return dict(task)

    def list_preparation_tasks(self, actor, event_id, done=None):
        self._check_role(actor, "read")
        self._event(event_id)
        return [
            dict(t) for t in self._preparation.values()
            if t["event_id"] == event_id
            and (done is None or t["done"] == done)
        ]

    # -- sessions (gatherings) -------------------------------------------------

    def _session_view(self, session, now=None):
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        view = dict(session)
        view["status"] = self._window_status(session, moment)
        return view

    def create_session(self, actor, event_id, kind, title,
                       starts_at, ends_at, speaker_ref=None):
        """Record a gathering session within an event: a webinar,
        a networking roundtable, or a speaker engagement (the
        claimed gathering kinds). The session's window must lie
        within its event's window. A speaker is named only by an
        opaque ``speaker_ref``."""
        self._check_role(actor, "manage")
        event = self._event(event_id)
        if kind not in SESSION_KINDS:
            raise ValidationError("unknown session kind: %r" % (kind,))
        _text(title, "title")
        _optional_text(speaker_ref, "speaker_ref")
        starts = _parse_moment(starts_at, "starts_at")
        ends = _parse_moment(ends_at, "ends_at")
        if ends < starts:
            raise ValidationError("ends_at must not precede starts_at")
        if starts < _parse_moment(event["starts_at"], "starts_at") \
                or ends > _parse_moment(event["ends_at"], "ends_at"):
            raise ValidationError(
                "session window must lie within its event's window")
        with self._lock:
            session = {
                "id": self._mint("ses-"),
                "event_id": event_id,
                "kind": kind,
                "title": title,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "speaker_ref": speaker_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._sessions[session["id"]] = session
        self._record(actor, "session_create", session["id"],
                     {"event_id": event_id, "kind": kind})
        return self._session_view(session)

    def get_session(self, actor, session_id, now=None):
        self._check_role(actor, "read")
        session = self._sessions.get(session_id)
        if session is None:
            raise NotFoundError("no such session: %r" % (session_id,))
        return self._session_view(session, now=now)

    def list_sessions(self, actor, event_id=None, kind=None,
                      status=None, now=None):
        self._check_role(actor, "read")
        if event_id is not None:
            self._event(event_id)
        if kind is not None and kind not in SESSION_KINDS:
            raise ValidationError("unknown session kind: %r" % (kind,))
        if status is not None and status not in WINDOW_STATUSES:
            raise ValidationError("unknown session status: %r" % (status,))
        result = []
        for session in self._sessions.values():
            if event_id is not None and session["event_id"] != event_id:
                continue
            if kind is not None and session["kind"] != kind:
                continue
            view = self._session_view(session, now=now)
            if status is not None and view["status"] != status:
                continue
            result.append(view)
        return result

    # -- outreach records -----------------------------------------------------

    def record_outreach(self, actor, organizer_id, vendor_id, event_id,
                        channel, subject):
        """Record an outreach from an organizer to a vendor about
        one of the organizer's own events. Delivery is Extended --
        what is recorded here is the outreach itself; nothing is
        sent."""
        self._check_role(actor, "outreach")
        self._organizer(organizer_id)
        self._vendor(vendor_id)
        event = self._event(event_id)
        if event["organizer_id"] != organizer_id:
            raise ValidationError(
                "event %s does not belong to organizer %s"
                % (event_id, organizer_id))
        _text(channel, "channel")
        _text(subject, "subject")
        with self._lock:
            outreach = {
                "id": self._mint("out-"),
                "organizer_id": organizer_id,
                "vendor_id": vendor_id,
                "event_id": event_id,
                "channel": channel,
                "subject": subject,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._outreach[outreach["id"]] = outreach
        self._record(actor, "outreach_record", outreach["id"],
                     {"organizer_id": organizer_id, "vendor_id": vendor_id})
        return dict(outreach)

    def list_outreach(self, actor, organizer_id=None, vendor_id=None,
                      event_id=None):
        self._check_role(actor, "read")
        if organizer_id is not None:
            self._organizer(organizer_id)
        if vendor_id is not None:
            self._vendor(vendor_id)
        if event_id is not None:
            self._event(event_id)
        return [
            dict(o) for o in self._outreach.values()
            if (organizer_id is None or o["organizer_id"] == organizer_id)
            and (vendor_id is None or o["vendor_id"] == vendor_id)
            and (event_id is None or o["event_id"] == event_id)
        ]

    # -- matchmaking rounds and participations ---------------------------------

    def create_round(self, actor, event_id, required_tags):
        """Open a matchmaking round for an event, recording the
        capability tags the organizer requires. An empty required
        list is allowed: it is satisfied by every participation
        (the empty set is a subset of every set), stated plainly
        rather than special-cased."""
        self._check_role(actor, "matchmake")
        self._event(event_id)
        tags = _tags(required_tags, "required_tags")
        with self._lock:
            round_ = {
                "id": self._mint("rnd-"),
                "event_id": event_id,
                "required_tags": tags,
                "status": "open",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._rounds[round_["id"]] = round_
        self._record(actor, "round_create", round_["id"],
                     {"event_id": event_id})
        result = dict(round_)
        result["required_tags"] = list(tags)
        return result

    def close_round(self, actor, round_id):
        """Close a matchmaking round by recorded action.
        Participations are recorded only while a round is open;
        matches remain derivable after closing."""
        self._check_role(actor, "matchmake")
        round_ = self._round(round_id)
        with self._lock:
            if round_["status"] == "closed":
                raise ValidationError("round %s is already closed" % round_id)
            round_["status"] = "closed"
        self._record(actor, "round_close", round_id, {})
        result = dict(round_)
        result["required_tags"] = list(round_["required_tags"])
        return result

    def get_round(self, actor, round_id):
        self._check_role(actor, "read")
        round_ = self._round(round_id)
        result = dict(round_)
        result["required_tags"] = list(round_["required_tags"])
        return result

    def list_rounds(self, actor, event_id=None, status=None):
        self._check_role(actor, "read")
        if event_id is not None:
            self._event(event_id)
        if status is not None and status not in ROUND_STATUSES:
            raise ValidationError("unknown round status: %r" % (status,))
        result = []
        for round_ in self._rounds.values():
            if event_id is not None and round_["event_id"] != event_id:
                continue
            if status is not None and round_["status"] != status:
                continue
            copied = dict(round_)
            copied["required_tags"] = list(round_["required_tags"])
            result.append(copied)
        return result

    def record_participation(self, actor, round_id, vendor_id,
                             capability_tags):
        """Record a vendor's participation in an open matchmaking
        round, stating the capability tags the vendor records for
        itself. One participation per vendor per round.
        Participations are immutable: there is no update or
        delete."""
        self._check_role(actor, "matchmake")
        round_ = self._round(round_id)
        self._vendor(vendor_id)
        tags = _tags(capability_tags, "capability_tags")
        with self._lock:
            if round_["status"] != "open":
                raise ValidationError(
                    "round %s is %r; participations are recorded only "
                    "while it is open" % (round_id, round_["status"]))
            for existing in self._participations.values():
                if existing["round_id"] == round_id \
                        and existing["vendor_id"] == vendor_id:
                    raise ValidationError(
                        "vendor %s already participates in round %s"
                        % (vendor_id, round_id))
            participation = {
                "id": self._mint("part-"),
                "round_id": round_id,
                "vendor_id": vendor_id,
                "capability_tags": tags,
                "seq": self._counters["part-"],
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._participations[participation["id"]] = participation
        self._record(actor, "participation_record", participation["id"],
                     {"round_id": round_id, "vendor_id": vendor_id})
        result = dict(participation)
        result["capability_tags"] = list(tags)
        return result

    def list_participations(self, actor, round_id):
        self._check_role(actor, "read")
        self._round(round_id)
        result = []
        for participation in sorted(
                (p for p in self._participations.values()
                 if p["round_id"] == round_id),
                key=lambda p: p["seq"]):
            copied = dict(participation)
            copied["capability_tags"] = list(participation["capability_tags"])
            result.append(copied)
        return result

    def round_matches(self, actor, round_id):
        """The round's matches, derived at read from its
        participation records by the single seam
        :func:`_derive_matches`: the participations whose recorded
        capability tags cover the round's recorded required tags,
        in participation sequence order. Nothing about the matches
        is stored, and no score is computed -- coverage is set
        inclusion, not a rating."""
        self._check_role(actor, "read")
        round_ = self._round(round_id)
        participations = [
            p for p in self._participations.values()
            if p["round_id"] == round_id
        ]
        matches = _derive_matches(participations, round_["required_tags"])
        return {
            "round_id": round_id,
            "event_id": round_["event_id"],
            "round_status": round_["status"],
            "required_tags": list(round_["required_tags"]),
            "participation_count": len(participations),
            "match_count": len(matches),
            "matches": [
                {
                    "participation_id": p["id"],
                    "vendor_id": p["vendor_id"],
                    "capability_tags": list(p["capability_tags"]),
                }
                for p in matches
            ],
        }

    def audit_read(self, actor):
        """Return the audit trail. Requires the ``audit_read``
        permission (admin-only in the permission matrix)."""
        self._check_role(actor, "audit_read")
        entries = self.audit.entries() if self.audit is not None else []
        return {"entries": entries, "count": len(entries)}

    # -- search and summary -----------------------------------------------------------

    def search(self, actor, query):
        """Literal case-insensitive substring search over organizers
        and vendors (ref and label), events (title), and outreach
        records (subject)."""
        self._check_role(actor, "read")
        _text(query, "query")
        needle = query.lower()
        organizers = [
            dict(o) for o in self._organizers.values()
            if needle in o["ref"].lower() or needle in o["label"].lower()
        ]
        vendors = [
            dict(v) for v in self._vendors.values()
            if needle in v["ref"].lower() or needle in v["label"].lower()
        ]
        events = [
            self._event_view(e) for e in self._events.values()
            if needle in e["title"].lower()
        ]
        outreach = [
            dict(o) for o in self._outreach.values()
            if needle in o["subject"].lower()
        ]
        return {
            "organizers": organizers,
            "vendors": vendors,
            "events": events,
            "outreach": outreach,
        }

    def summary(self, actor, now=None):
        """Counts over the whole registry, computed on read from
        records only. The matches total is a count of derived
        matches across rounds -- a count, never a score."""
        self._check_role(actor, "read")
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        events_by_status = {status: 0 for status in WINDOW_STATUSES}
        events_by_format = {format_: 0 for format_ in EVENT_FORMATS}
        for event in self._events.values():
            events_by_status[self._window_status(event, moment)] += 1
            events_by_format[event["format"]] += 1
        sessions_by_kind = {kind: 0 for kind in SESSION_KINDS}
        for session in self._sessions.values():
            sessions_by_kind[session["kind"]] += 1
        matches_total = 0
        for round_ in self._rounds.values():
            participations = [
                p for p in self._participations.values()
                if p["round_id"] == round_["id"]
            ]
            matches_total += len(
                _derive_matches(participations, round_["required_tags"]))
        return {
            "organizers": len(self._organizers),
            "vendors": len(self._vendors),
            "events_by_status": events_by_status,
            "events_by_format": events_by_format,
            "sessions_by_kind": sessions_by_kind,
            "preparation_open": sum(
                1 for t in self._preparation.values() if not t["done"]),
            "preparation_done": sum(
                1 for t in self._preparation.values() if t["done"]),
            "outreach": len(self._outreach),
            "rounds_open": sum(
                1 for r in self._rounds.values() if r["status"] == "open"),
            "rounds_closed": sum(
                1 for r in self._rounds.values() if r["status"] == "closed"),
            "participations": len(self._participations),
            "matches_total": matches_total,
        }
