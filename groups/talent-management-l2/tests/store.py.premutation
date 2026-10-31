"""The Talent Management records substrate.

Clean-room implementation of the Talent Management L2 union spec's
core: organization registry & membership, candidate registry,
requisition records, pipeline definitions, candidate placements
with append-only stage-movement records, recruitment event
records, event registration records, assessment records,
interview records, workflow definition registry, registry
reporting, and registry search — over an append-only audit log.

Privacy discipline (hard rule): every entity is keyed by an opaque
caller-supplied reference and carries only the fields in the
contract. Candidates are opaque references; there is no field
anywhere that can hold a real person's name, contact detail, or
identifier, a resume, an assessment's content, or an interview's
recording or transcript. Assessment outcomes are caller-supplied
labels recorded verbatim — the store computes no score, ranking,
or match for any candidate, ever. Validation always precedes
mutation: a failed operation changes nothing, consumes no id, and
records nothing.

Two boundaries are enforced on every organization-scoped
operation:

1. Membership -- the actor must be a member of the organization,
   or hold the platform ``admin`` role, else
   :class:`PermissionDenied`.
2. Role permission -- the action named for the operation must be
   in the actor's role permission set (see
   :mod:`talentmgmt.access`) when the actor is a
   :class:`~talentmgmt.access.User`. A plain string actor
   carries identity (for provenance) but no role, so role
   enforcement for those happens in the service layer.

Derivation discipline: a requisition's ``past_close`` and a
placement's ``current_stage_index`` / ``current_stage`` are
derived at read time and never stored. A placement's current
stage is the stage of its most recent movement record, or the
pipeline's first stage when no movement exists — movements are
append-only records, so the position is a derivation over them,
not a field. Lifecycles (requisition ``open`` -> ``closed``,
placement ``active`` -> ``withdrawn``, event ``scheduled`` ->
``completed`` / ``cancelled``, registration ``registered`` ->
``checked_in``, assessment ``assigned`` -> ``completed``,
interview ``scheduled`` -> ``completed`` / ``cancelled``) are
guarded transitions, not date derivations, so those statuses are
stored.

Stage bounds seam: a movement's ``stage_index`` must name a stage
of the placement's pipeline: ``0 <= stage_index < len(stages)``.
:meth:`TalentMgmtStore._check_stage_bounds` runs before every
movement is recorded and raises :class:`ValidationError` on a
violation. This is the group's negative control.

The store records every successful mutation to its audit log (when
one is attached). Reads are not audited here; denied attempts and
audit reads are the HTTP layer's responsibility, so nothing is
recorded twice.
"""

import re
import threading
from datetime import datetime, timezone

from .access import User, require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

REQUISITION_STATUSES = ("open", "closed")
PLACEMENT_STATUSES = ("active", "withdrawn")
EVENT_KINDS = ("in_person", "virtual")
EVENT_STATUSES = ("scheduled", "completed", "cancelled")
REGISTRATION_STATUSES = ("registered", "checked_in")
ASSESSMENT_STATUSES = ("assigned", "completed")
INTERVIEW_KINDS = ("video", "in_person")
INTERVIEW_STATUSES = ("scheduled", "completed", "cancelled")


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
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % field)
    return value


class TalentMgmtStore:
    """In-memory Talent Management records store with an optional audit log."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._organizations = {}
        self._candidates = {}
        self._requisitions = {}
        self._pipelines = {}
        self._placements = {}
        self._movements = {}
        self._events = {}
        self._registrations = {}
        self._assessments = {}
        self._interviews = {}
        self._workflows = {}
        self._counters = {}

    # -- internal helpers -------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _record(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor, action, target, details)

    @staticmethod
    def _name(actor):
        return actor_name(actor)

    @staticmethod
    def _require_role(actor, action):
        # A User carries a role and is enforced here; a plain string
        # carries identity only (the service layer enforces its role).
        if isinstance(actor, User):
            require(actor, action)

    @staticmethod
    def _is_admin(actor):
        return isinstance(actor, User) and actor.role == "admin"

    def _organization(self, org_id):
        org = self._organizations.get(org_id)
        if org is None:
            raise NotFoundError("no such organization: %r" % (org_id,))
        return org

    def _require_org_access(self, org, actor):
        if self._is_admin(actor):
            return
        if self._name(actor) not in org["members"]:
            raise PermissionDenied(
                "actor %r is not a member of organization %s"
                % (self._name(actor), org["id"])
            )

    def _scoped_org(self, org_id, actor, action):
        org = self._organization(org_id)
        self._require_role(actor, action)
        self._require_org_access(org, actor)
        return org

    @staticmethod
    def _org_view(org):
        view = dict(org)
        view["members"] = list(org["members"])
        return view

    def _candidate_by_ref(self, org_id, candidate_ref):
        for candidate in self._candidates.values():
            if (candidate["org_id"] == org_id
                    and candidate["candidate_ref"] == candidate_ref):
                return candidate
        return None

    def _require_candidate(self, org_id, candidate_ref):
        _text(candidate_ref, "candidate_ref")
        if self._candidate_by_ref(org_id, candidate_ref) is None:
            raise ValidationError(
                "candidate is not registered in organization %s: %r"
                % (org_id, candidate_ref)
            )

    def _requisition_in(self, org_id, requisition_id):
        requisition = self._requisitions.get(requisition_id)
        if requisition is None or requisition["org_id"] != org_id:
            raise NotFoundError(
                "no such requisition in organization %s: %r"
                % (org_id, requisition_id)
            )
        return requisition

    def _pipeline_in(self, org_id, pipeline_id):
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None or pipeline["org_id"] != org_id:
            raise NotFoundError(
                "no such pipeline in organization %s: %r" % (org_id, pipeline_id)
            )
        return pipeline

    def _placement_in(self, org_id, placement_id):
        placement = self._placements.get(placement_id)
        if placement is None or placement["org_id"] != org_id:
            raise NotFoundError(
                "no such placement in organization %s: %r"
                % (org_id, placement_id)
            )
        return placement

    def _event_in(self, org_id, event_id):
        event = self._events.get(event_id)
        if event is None or event["org_id"] != org_id:
            raise NotFoundError(
                "no such event in organization %s: %r" % (org_id, event_id)
            )
        return event

    # -- organizations -----------------------------------------------------------

    def create_organization(self, org_ref, label, actor):
        """Create an organization. The creator is the first member."""
        self._require_role(actor, "org_write")
        _text(org_ref, "org_ref")
        _text(label, "label")
        with self._lock:
            for existing in self._organizations.values():
                if existing["org_ref"] == org_ref:
                    raise ValidationError(
                        "org_ref already exists: %r" % (org_ref,)
                    )
            org = {
                "id": self._mint("org-"),
                "org_ref": org_ref,
                "label": label,
                "members": [self._name(actor)],
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._organizations[org["id"]] = org
        self._record(actor, "organization_create", org["id"], {"org_ref": org_ref})
        return self._org_view(org)

    def list_organizations(self, actor):
        """Organizations the actor is a member of, or all for an admin."""
        self._require_role(actor, "org_read")
        result = []
        for org in self._organizations.values():
            if self._is_admin(actor) or self._name(actor) in org["members"]:
                result.append(self._org_view(org))
        return result

    def get_organization(self, org_id, actor):
        org = self._scoped_org(org_id, actor, "org_read")
        return self._org_view(org)

    def add_member(self, org_id, username, actor):
        """Add a member to an organization. Only the organization's
        creator or a platform admin may add; the gate is
        creator-or-admin, layered on the membership boundary."""
        org = self._organization(org_id)
        self._require_org_access(org, actor)
        if not (self._is_admin(actor) or org["created_by"] == self._name(actor)):
            raise PermissionDenied(
                "only the organization creator or a platform admin may add members"
            )
        _text(username, "username")
        with self._lock:
            if username in org["members"]:
                raise ValidationError(
                    "%r is already a member of organization %s" % (username, org_id)
                )
            org["members"].append(username)
        self._record(actor, "member_add", org_id, {"username": username})
        return self._org_view(org)

    # -- candidates ---------------------------------------------------------------

    def register_candidate(self, org_id, candidate_ref, label, actor):
        """Register a candidate as an opaque reference. Registration
        records hold no name, contact detail, or identifier of a
        real person — the reference is the whole record of identity
        here (IA-2 stays with the embedding organization)."""
        self._scoped_org(org_id, actor, "candidate_write")
        _text(candidate_ref, "candidate_ref")
        _text(label, "label")
        with self._lock:
            for existing in self._candidates.values():
                if (existing["org_id"] == org_id
                        and existing["candidate_ref"] == candidate_ref):
                    raise ValidationError(
                        "candidate_ref %r already exists in organization %s"
                        % (candidate_ref, org_id)
                    )
            candidate = {
                "id": self._mint("can-"),
                "org_id": org_id,
                "candidate_ref": candidate_ref,
                "label": label,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._candidates[candidate["id"]] = candidate
        self._record(actor, "candidate_register", candidate["id"],
                     {"org_id": org_id})
        return dict(candidate)

    def get_candidate(self, org_id, candidate_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        candidate = self._candidates.get(candidate_id)
        if candidate is None or candidate["org_id"] != org_id:
            raise NotFoundError(
                "no such candidate in organization %s: %r" % (org_id, candidate_id)
            )
        return dict(candidate)

    def list_candidates(self, org_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return [
            dict(c) for c in self._candidates.values() if c["org_id"] == org_id
        ]

    # -- requisitions ---------------------------------------------------------------

    @staticmethod
    def _requisition_view(requisition, now=None):
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        past_close = False
        if requisition["closes_at"] is not None:
            past_close = moment > _parse_moment(
                requisition["closes_at"], "closes_at")
        view = dict(requisition)
        view["past_close"] = past_close
        return view

    def create_requisition(self, org_id, requisition_ref, title, actor,
                           opens_at=None, closes_at=None):
        self._scoped_org(org_id, actor, "requisition_write")
        _text(requisition_ref, "requisition_ref")
        _text(title, "title")
        opens_moment = None
        closes_moment = None
        if opens_at is not None:
            opens_moment = _parse_moment(opens_at, "opens_at")
        if closes_at is not None:
            closes_moment = _parse_moment(closes_at, "closes_at")
        if (opens_moment is not None and closes_moment is not None
                and closes_moment < opens_moment):
            raise ValidationError("closes_at must not precede opens_at")
        with self._lock:
            for existing in self._requisitions.values():
                if (existing["org_id"] == org_id
                        and existing["requisition_ref"] == requisition_ref):
                    raise ValidationError(
                        "requisition_ref %r already exists in organization %s"
                        % (requisition_ref, org_id)
                    )
            requisition = {
                "id": self._mint("req-"),
                "org_id": org_id,
                "requisition_ref": requisition_ref,
                "title": title,
                "opens_at": opens_at,
                "closes_at": closes_at,
                "status": "open",
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._requisitions[requisition["id"]] = requisition
        self._record(actor, "requisition_create", requisition["id"],
                     {"org_id": org_id})
        return dict(requisition)

    def get_requisition(self, org_id, requisition_id, actor, now=None):
        self._scoped_org(org_id, actor, "org_read")
        requisition = self._requisition_in(org_id, requisition_id)
        return self._requisition_view(requisition, now=now)

    def list_requisitions(self, org_id, actor, now=None):
        self._scoped_org(org_id, actor, "org_read")
        return [
            self._requisition_view(r, now=now)
            for r in self._requisitions.values() if r["org_id"] == org_id
        ]

    def close_requisition(self, org_id, requisition_id, actor):
        self._scoped_org(org_id, actor, "requisition_write")
        requisition = self._requisition_in(org_id, requisition_id)
        with self._lock:
            if requisition["status"] != "open":
                raise ValidationError(
                    "requisition %s is %r; only an open requisition can "
                    "be closed" % (requisition_id, requisition["status"])
                )
            requisition["status"] = "closed"
        self._record(actor, "requisition_close", requisition_id,
                     {"org_id": org_id})
        return dict(requisition)

    # -- pipelines ---------------------------------------------------------------

    @staticmethod
    def _pipeline_view(pipeline):
        view = dict(pipeline)
        view["stages"] = list(pipeline["stages"])
        return view

    def create_pipeline(self, org_id, pipeline_ref, requisition_id, stages,
                        actor, label=None):
        """Define a pipeline: an ordered list of stage labels against
        one requisition. The definition is a record; nothing about
        it executes or moves anyone."""
        self._scoped_org(org_id, actor, "pipeline_write")
        _text(pipeline_ref, "pipeline_ref")
        self._requisition_in(org_id, requisition_id)
        if not isinstance(stages, list) or not stages:
            raise ValidationError("stages must be a non-empty list of stage labels")
        for stage in stages:
            _text(stage, "stage label")
        if len(set(stages)) != len(stages):
            raise ValidationError("stage labels must be unique within a pipeline")
        _optional_text(label, "label")
        with self._lock:
            for existing in self._pipelines.values():
                if (existing["org_id"] == org_id
                        and existing["pipeline_ref"] == pipeline_ref):
                    raise ValidationError(
                        "pipeline_ref %r already exists in organization %s"
                        % (pipeline_ref, org_id)
                    )
            pipeline = {
                "id": self._mint("pip-"),
                "org_id": org_id,
                "pipeline_ref": pipeline_ref,
                "requisition_id": requisition_id,
                "stages": list(stages),
                "label": label,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._pipelines[pipeline["id"]] = pipeline
        self._record(actor, "pipeline_create", pipeline["id"], {"org_id": org_id})
        return self._pipeline_view(pipeline)

    def get_pipeline(self, org_id, pipeline_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return self._pipeline_view(self._pipeline_in(org_id, pipeline_id))

    def list_pipelines(self, org_id, actor, requisition_id=None):
        self._scoped_org(org_id, actor, "org_read")
        if requisition_id is not None:
            self._requisition_in(org_id, requisition_id)
        return [
            self._pipeline_view(p) for p in self._pipelines.values()
            if p["org_id"] == org_id
            and (requisition_id is None or p["requisition_id"] == requisition_id)
        ]

    # -- placements & stage movements ------------------------------------------------

    def _check_stage_bounds(self, pipeline, stage_index):
        """Stage bounds seam: ``stage_index`` must be an integer
        naming a stage of ``pipeline``:
        ``0 <= stage_index < len(pipeline["stages"])``. Raises
        ValidationError on a violation. (This is the seam the
        negative control mutates.)"""
        if isinstance(stage_index, bool) or not isinstance(stage_index, int):
            raise ValidationError("stage_index must be an integer")
        if stage_index < 0 or stage_index >= len(pipeline["stages"]):
            raise ValidationError(
                "stage_index %d is outside the pipeline's %d stages"
                % (stage_index, len(pipeline["stages"]))
            )

    def _current_stage_index(self, placement):
        movements = [
            m for m in self._movements.values()
            if m["placement_id"] == placement["id"]
        ]
        if not movements:
            return 0
        # Ids are sequential and never reused; the greatest id is the
        # most recent movement.
        latest = max(movements, key=lambda m: int(m["id"].split("-", 1)[1]))
        return latest["stage_index"]

    def _placement_view(self, placement):
        pipeline = self._pipelines[placement["pipeline_id"]]
        index = self._current_stage_index(placement)
        view = dict(placement)
        view["current_stage_index"] = index
        view["current_stage"] = pipeline["stages"][index]
        return view

    def place_candidate(self, org_id, pipeline_id, placement_ref,
                        candidate_ref, actor):
        self._scoped_org(org_id, actor, "pipeline_write")
        pipeline = self._pipeline_in(org_id, pipeline_id)
        _text(placement_ref, "placement_ref")
        self._require_candidate(org_id, candidate_ref)
        with self._lock:
            for existing in self._placements.values():
                if (existing["pipeline_id"] == pipeline_id
                        and existing["placement_ref"] == placement_ref):
                    raise ValidationError(
                        "placement_ref %r already exists in pipeline %s"
                        % (placement_ref, pipeline_id)
                    )
                if (existing["pipeline_id"] == pipeline_id
                        and existing["candidate_ref"] == candidate_ref
                        and existing["status"] == "active"):
                    raise ValidationError(
                        "candidate %r is already actively placed in "
                        "pipeline %s" % (candidate_ref, pipeline_id)
                    )
            placement = {
                "id": self._mint("plc-"),
                "org_id": org_id,
                "pipeline_id": pipeline_id,
                "placement_ref": placement_ref,
                "candidate_ref": candidate_ref,
                "status": "active",
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._placements[placement["id"]] = placement
        self._record(actor, "placement_create", placement["id"],
                     {"org_id": org_id, "pipeline_id": pipeline_id})
        return dict(placement)

    def get_placement(self, org_id, placement_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return self._placement_view(self._placement_in(org_id, placement_id))

    def list_placements(self, org_id, actor, pipeline_id=None):
        self._scoped_org(org_id, actor, "org_read")
        if pipeline_id is not None:
            self._pipeline_in(org_id, pipeline_id)
        return [
            self._placement_view(p) for p in self._placements.values()
            if p["org_id"] == org_id
            and (pipeline_id is None or p["pipeline_id"] == pipeline_id)
        ]

    def withdraw_placement(self, org_id, placement_id, actor):
        self._scoped_org(org_id, actor, "pipeline_write")
        placement = self._placement_in(org_id, placement_id)
        with self._lock:
            if placement["status"] != "active":
                raise ValidationError(
                    "placement %s is %r; only an active placement can be "
                    "withdrawn" % (placement_id, placement["status"])
                )
            placement["status"] = "withdrawn"
        self._record(actor, "placement_withdraw", placement_id,
                     {"org_id": org_id})
        return dict(placement)

    def record_movement(self, org_id, placement_id, movement_ref,
                        stage_index, actor, label=None):
        """Record a stage movement for a placement. The bounds seam
        runs before anything is stored; the movement is an
        append-only record and the placement's current stage is
        derived from the movement set at read."""
        self._scoped_org(org_id, actor, "pipeline_write")
        placement = self._placement_in(org_id, placement_id)
        pipeline = self._pipeline_in(org_id, placement["pipeline_id"])
        _text(movement_ref, "movement_ref")
        _optional_text(label, "label")
        with self._lock:
            if placement["status"] != "active":
                raise ValidationError(
                    "placement %s is %r; movements are recorded against "
                    "active placements only"
                    % (placement_id, placement["status"])
                )
            for existing in self._movements.values():
                if (existing["placement_id"] == placement_id
                        and existing["movement_ref"] == movement_ref):
                    raise ValidationError(
                        "movement_ref %r already exists in placement %s"
                        % (movement_ref, placement_id)
                    )
            self._check_stage_bounds(pipeline, stage_index)
            movement = {
                "id": self._mint("mov-"),
                "org_id": org_id,
                "placement_id": placement_id,
                "movement_ref": movement_ref,
                "stage_index": stage_index,
                "label": label,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._movements[movement["id"]] = movement
        self._record(actor, "movement_record", movement["id"],
                     {"org_id": org_id, "placement_id": placement_id})
        return dict(movement)

    def list_movements(self, org_id, placement_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        self._placement_in(org_id, placement_id)
        return [
            dict(m) for m in self._movements.values()
            if m["org_id"] == org_id and m["placement_id"] == placement_id
        ]

    # -- recruitment events -----------------------------------------------------------

    def create_event(self, org_id, event_ref, title, kind, starts_at, actor,
                     requisition_id=None, label=None):
        self._scoped_org(org_id, actor, "event_write")
        _text(event_ref, "event_ref")
        _text(title, "title")
        if kind not in EVENT_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(EVENT_KINDS),)
            )
        if starts_at is None:
            raise ValidationError("starts_at is required")
        _parse_moment(starts_at, "starts_at")
        if requisition_id is not None:
            self._requisition_in(org_id, requisition_id)
        _optional_text(label, "label")
        with self._lock:
            for existing in self._events.values():
                if (existing["org_id"] == org_id
                        and existing["event_ref"] == event_ref):
                    raise ValidationError(
                        "event_ref %r already exists in organization %s"
                        % (event_ref, org_id)
                    )
            event = {
                "id": self._mint("evt-"),
                "org_id": org_id,
                "event_ref": event_ref,
                "title": title,
                "kind": kind,
                "starts_at": starts_at,
                "requisition_id": requisition_id,
                "label": label,
                "status": "scheduled",
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._events[event["id"]] = event
        self._record(actor, "event_create", event["id"], {"org_id": org_id})
        return dict(event)

    def get_event(self, org_id, event_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return dict(self._event_in(org_id, event_id))

    def list_events(self, org_id, actor, kind=None, requisition_id=None):
        self._scoped_org(org_id, actor, "org_read")
        if kind is not None and kind not in EVENT_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(EVENT_KINDS),)
            )
        if requisition_id is not None:
            self._requisition_in(org_id, requisition_id)
        return [
            dict(e) for e in self._events.values()
            if e["org_id"] == org_id
            and (kind is None or e["kind"] == kind)
            and (requisition_id is None or e["requisition_id"] == requisition_id)
        ]

    def _transition_event(self, org_id, event_id, actor, target_status, action):
        self._scoped_org(org_id, actor, "event_write")
        event = self._event_in(org_id, event_id)
        with self._lock:
            if event["status"] != "scheduled":
                raise ValidationError(
                    "event %s is %r; only a scheduled event can become %s"
                    % (event_id, event["status"], target_status)
                )
            event["status"] = target_status
        self._record(actor, action, event_id, {"org_id": org_id})
        return dict(event)

    def complete_event(self, org_id, event_id, actor):
        return self._transition_event(
            org_id, event_id, actor, "completed", "event_complete")

    def cancel_event(self, org_id, event_id, actor):
        return self._transition_event(
            org_id, event_id, actor, "cancelled", "event_cancel")

    # -- event registrations -----------------------------------------------------------

    def register_for_event(self, org_id, event_id, registration_ref,
                           candidate_ref, actor):
        self._scoped_org(org_id, actor, "event_write")
        event = self._event_in(org_id, event_id)
        _text(registration_ref, "registration_ref")
        self._require_candidate(org_id, candidate_ref)
        with self._lock:
            if event["status"] != "scheduled":
                raise ValidationError(
                    "event %s is %r; registrations are recorded against "
                    "scheduled events only" % (event_id, event["status"])
                )
            for existing in self._registrations.values():
                if existing["event_id"] == event_id:
                    if existing["registration_ref"] == registration_ref:
                        raise ValidationError(
                            "registration_ref %r already exists in event %s"
                            % (registration_ref, event_id)
                        )
                    if existing["candidate_ref"] == candidate_ref:
                        raise ValidationError(
                            "candidate %r is already registered for event %s"
                            % (candidate_ref, event_id)
                        )
            registration = {
                "id": self._mint("reg-"),
                "org_id": org_id,
                "event_id": event_id,
                "registration_ref": registration_ref,
                "candidate_ref": candidate_ref,
                "status": "registered",
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._registrations[registration["id"]] = registration
        self._record(actor, "registration_create", registration["id"],
                     {"org_id": org_id, "event_id": event_id})
        return dict(registration)

    def _registration_in(self, org_id, registration_id):
        registration = self._registrations.get(registration_id)
        if registration is None or registration["org_id"] != org_id:
            raise NotFoundError(
                "no such registration in organization %s: %r"
                % (org_id, registration_id)
            )
        return registration

    def check_in_registration(self, org_id, registration_id, actor):
        self._scoped_org(org_id, actor, "event_write")
        registration = self._registration_in(org_id, registration_id)
        with self._lock:
            if registration["status"] != "registered":
                raise ValidationError(
                    "registration %s is %r; only a registered registration "
                    "can be checked in"
                    % (registration_id, registration["status"])
                )
            registration["status"] = "checked_in"
        self._record(actor, "registration_check_in", registration_id,
                     {"org_id": org_id})
        return dict(registration)

    def list_registrations(self, org_id, event_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        self._event_in(org_id, event_id)
        return [
            dict(r) for r in self._registrations.values()
            if r["org_id"] == org_id and r["event_id"] == event_id
        ]

    # -- assessments ---------------------------------------------------------------

    def record_assessment(self, org_id, assessment_ref, candidate_ref,
                          instrument_label, actor, requisition_id=None):
        """Record an assessment assignment. The instrument is an
        opaque caller-supplied label; no assessment content, item,
        or response is stored anywhere."""
        self._scoped_org(org_id, actor, "assessment_write")
        _text(assessment_ref, "assessment_ref")
        self._require_candidate(org_id, candidate_ref)
        _text(instrument_label, "instrument_label")
        if requisition_id is not None:
            self._requisition_in(org_id, requisition_id)
        with self._lock:
            for existing in self._assessments.values():
                if (existing["org_id"] == org_id
                        and existing["assessment_ref"] == assessment_ref):
                    raise ValidationError(
                        "assessment_ref %r already exists in organization %s"
                        % (assessment_ref, org_id)
                    )
            assessment = {
                "id": self._mint("asm-"),
                "org_id": org_id,
                "assessment_ref": assessment_ref,
                "candidate_ref": candidate_ref,
                "instrument_label": instrument_label,
                "requisition_id": requisition_id,
                "status": "assigned",
                "outcome_label": None,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._assessments[assessment["id"]] = assessment
        self._record(actor, "assessment_record", assessment["id"],
                     {"org_id": org_id})
        return dict(assessment)

    def _assessment_in(self, org_id, assessment_id):
        assessment = self._assessments.get(assessment_id)
        if assessment is None or assessment["org_id"] != org_id:
            raise NotFoundError(
                "no such assessment in organization %s: %r"
                % (org_id, assessment_id)
            )
        return assessment

    def complete_assessment(self, org_id, assessment_id, outcome_label, actor):
        """Complete an assessment with the caller's outcome label,
        recorded verbatim. The label is a human/provider-supplied
        outcome string; this build computes no score from it or
        from anything else."""
        self._scoped_org(org_id, actor, "assessment_write")
        assessment = self._assessment_in(org_id, assessment_id)
        _text(outcome_label, "outcome_label")
        with self._lock:
            if assessment["status"] != "assigned":
                raise ValidationError(
                    "assessment %s is %r; only an assigned assessment can "
                    "be completed" % (assessment_id, assessment["status"])
                )
            assessment["status"] = "completed"
            assessment["outcome_label"] = outcome_label
        self._record(actor, "assessment_complete", assessment_id,
                     {"org_id": org_id})
        return dict(assessment)

    def get_assessment(self, org_id, assessment_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return dict(self._assessment_in(org_id, assessment_id))

    def list_assessments(self, org_id, actor, candidate_ref=None, status=None):
        self._scoped_org(org_id, actor, "org_read")
        if status is not None and status not in ASSESSMENT_STATUSES:
            raise ValidationError(
                "status must be one of %s" % (", ".join(ASSESSMENT_STATUSES),)
            )
        return [
            dict(a) for a in self._assessments.values()
            if a["org_id"] == org_id
            and (candidate_ref is None or a["candidate_ref"] == candidate_ref)
            and (status is None or a["status"] == status)
        ]

    # -- interviews ---------------------------------------------------------------

    def schedule_interview(self, org_id, interview_ref, candidate_ref, kind,
                           actor, requisition_id=None, scheduled_at=None):
        """Schedule an interview record. The record is metadata —
        kind, candidate reference, time; no recording, transcript,
        or note content exists anywhere in this build."""
        self._scoped_org(org_id, actor, "interview_write")
        _text(interview_ref, "interview_ref")
        self._require_candidate(org_id, candidate_ref)
        if kind not in INTERVIEW_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(INTERVIEW_KINDS),)
            )
        if requisition_id is not None:
            self._requisition_in(org_id, requisition_id)
        if scheduled_at is not None:
            _parse_moment(scheduled_at, "scheduled_at")
        with self._lock:
            for existing in self._interviews.values():
                if (existing["org_id"] == org_id
                        and existing["interview_ref"] == interview_ref):
                    raise ValidationError(
                        "interview_ref %r already exists in organization %s"
                        % (interview_ref, org_id)
                    )
            interview = {
                "id": self._mint("int-"),
                "org_id": org_id,
                "interview_ref": interview_ref,
                "candidate_ref": candidate_ref,
                "kind": kind,
                "requisition_id": requisition_id,
                "scheduled_at": scheduled_at,
                "status": "scheduled",
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._interviews[interview["id"]] = interview
        self._record(actor, "interview_schedule", interview["id"],
                     {"org_id": org_id})
        return dict(interview)

    def _interview_in(self, org_id, interview_id):
        interview = self._interviews.get(interview_id)
        if interview is None or interview["org_id"] != org_id:
            raise NotFoundError(
                "no such interview in organization %s: %r"
                % (org_id, interview_id)
            )
        return interview

    def _transition_interview(self, org_id, interview_id, actor,
                              target_status, action):
        self._scoped_org(org_id, actor, "interview_write")
        interview = self._interview_in(org_id, interview_id)
        with self._lock:
            if interview["status"] != "scheduled":
                raise ValidationError(
                    "interview %s is %r; only a scheduled interview can "
                    "become %s" % (interview_id, interview["status"],
                                   target_status)
                )
            interview["status"] = target_status
        self._record(actor, action, interview_id, {"org_id": org_id})
        return dict(interview)

    def complete_interview(self, org_id, interview_id, actor):
        return self._transition_interview(
            org_id, interview_id, actor, "completed", "interview_complete")

    def cancel_interview(self, org_id, interview_id, actor):
        return self._transition_interview(
            org_id, interview_id, actor, "cancelled", "interview_cancel")

    def get_interview(self, org_id, interview_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return dict(self._interview_in(org_id, interview_id))

    def list_interviews(self, org_id, actor, candidate_ref=None, kind=None):
        self._scoped_org(org_id, actor, "org_read")
        if kind is not None and kind not in INTERVIEW_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(INTERVIEW_KINDS),)
            )
        return [
            dict(i) for i in self._interviews.values()
            if i["org_id"] == org_id
            and (candidate_ref is None or i["candidate_ref"] == candidate_ref)
            and (kind is None or i["kind"] == kind)
        ]

    # -- workflow definitions (records only, never execute) ----------------------

    def register_workflow(self, org_id, workflow_ref, label, actor):
        self._scoped_org(org_id, actor, "registry_write")
        _text(workflow_ref, "workflow_ref")
        _text(label, "label")
        with self._lock:
            for existing in self._workflows.values():
                if (existing["org_id"] == org_id
                        and existing["workflow_ref"] == workflow_ref):
                    raise ValidationError(
                        "workflow_ref %r already exists in organization %s"
                        % (workflow_ref, org_id)
                    )
            workflow = {
                "id": self._mint("wfl-"),
                "org_id": org_id,
                "workflow_ref": workflow_ref,
                "label": label,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._workflows[workflow["id"]] = workflow
        self._record(actor, "workflow_register", workflow["id"],
                     {"org_id": org_id})
        return dict(workflow)

    def list_workflows(self, org_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return [dict(w) for w in self._workflows.values() if w["org_id"] == org_id]

    # -- reporting & registry search ---------------------------------------------------

    def org_report(self, org_id, actor, now=None):
        """Counts for one organization, computed on read. This is
        the applicant-metrics surface the forks' analytics claims
        presuppose: counts of recorded things, including the
        current-stage distribution of active placements (derived
        from their movement records at the read clock). No score,
        ranking, ratio, or return-on-investment figure is computed
        anywhere in this build."""
        self._scoped_org(org_id, actor, "report_read")
        candidates = [c for c in self._candidates.values() if c["org_id"] == org_id]
        requisitions = [
            r for r in self._requisitions.values() if r["org_id"] == org_id
        ]
        requisitions_by_status = {s: 0 for s in REQUISITION_STATUSES}
        for requisition in requisitions:
            requisitions_by_status[requisition["status"]] += 1
        pipelines = [p for p in self._pipelines.values() if p["org_id"] == org_id]
        placements = [p for p in self._placements.values() if p["org_id"] == org_id]
        placements_by_stage = {}
        for placement in placements:
            if placement["status"] != "active":
                continue
            stage = self._placement_view(placement)["current_stage"]
            placements_by_stage[stage] = placements_by_stage.get(stage, 0) + 1
        events = [e for e in self._events.values() if e["org_id"] == org_id]
        events_by_kind = {k: 0 for k in EVENT_KINDS}
        events_by_status = {s: 0 for s in EVENT_STATUSES}
        for event in events:
            events_by_kind[event["kind"]] += 1
            events_by_status[event["status"]] += 1
        registrations = [
            r for r in self._registrations.values() if r["org_id"] == org_id
        ]
        assessments = [
            a for a in self._assessments.values() if a["org_id"] == org_id
        ]
        assessments_by_status = {s: 0 for s in ASSESSMENT_STATUSES}
        for assessment in assessments:
            assessments_by_status[assessment["status"]] += 1
        interviews = [i for i in self._interviews.values() if i["org_id"] == org_id]
        interviews_by_kind = {k: 0 for k in INTERVIEW_KINDS}
        interviews_by_status = {s: 0 for s in INTERVIEW_STATUSES}
        for interview in interviews:
            interviews_by_kind[interview["kind"]] += 1
            interviews_by_status[interview["status"]] += 1
        return {
            "org_id": org_id,
            "candidate_count": len(candidates),
            "requisition_count": len(requisitions),
            "requisitions_by_status": requisitions_by_status,
            "pipeline_count": len(pipelines),
            "placement_count": len(placements),
            "placements_by_stage": placements_by_stage,
            "event_count": len(events),
            "events_by_kind": events_by_kind,
            "events_by_status": events_by_status,
            "registration_count": len(registrations),
            "checked_in_count": sum(
                1 for r in registrations if r["status"] == "checked_in"
            ),
            "assessment_count": len(assessments),
            "assessments_by_status": assessments_by_status,
            "interview_count": len(interviews),
            "interviews_by_kind": interviews_by_kind,
            "interviews_by_status": interviews_by_status,
            "workflow_count": sum(
                1 for w in self._workflows.values() if w["org_id"] == org_id
            ),
        }

    def search_registry(self, actor, query):
        """Literal case-insensitive substring search over registry
        metadata (references, titles, labels, kinds, stage labels),
        scoped to organizations the actor belongs to (or all for a
        platform admin)."""
        self._require_role(actor, "org_read")
        if not isinstance(query, str) or not query.strip():
            raise ValidationError("query must be a non-empty string")
        needle = query.strip().lower()

        def hit(*fields):
            return any(
                f is not None and needle in str(f).lower() for f in fields
            )

        visible = {
            o["id"] for o in self._organizations.values()
            if self._is_admin(actor) or self._name(actor) in o["members"]
        }
        return {
            "organizations": [
                self._org_view(o) for o in self._organizations.values()
                if o["id"] in visible and hit(o["org_ref"], o["label"])
            ],
            "candidates": [
                dict(c) for c in self._candidates.values()
                if c["org_id"] in visible
                and hit(c["candidate_ref"], c["label"])
            ],
            "requisitions": [
                self._requisition_view(r) for r in self._requisitions.values()
                if r["org_id"] in visible
                and hit(r["requisition_ref"], r["title"])
            ],
            "pipelines": [
                self._pipeline_view(p) for p in self._pipelines.values()
                if p["org_id"] in visible
                and hit(p["pipeline_ref"], p["label"], *p["stages"])
            ],
            "events": [
                dict(e) for e in self._events.values()
                if e["org_id"] in visible
                and hit(e["event_ref"], e["title"], e["kind"], e["label"])
            ],
            "workflows": [
                dict(w) for w in self._workflows.values()
                if w["org_id"] in visible and hit(w["workflow_ref"], w["label"])
            ],
        }
