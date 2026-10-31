"""Storage store: organization, retention-policy, and
archive-collection registries; message archive records (metadata
only); retention derivation and disposition records; discovery,
supervision, enforcement, retrieval, key-custody, and integration
records.

Clean-room implementation of the union spec's implementation
contract.

Role permission is enforced on every operation when the actor is
a User-like object: the action named for the operation must be in
the actor's role permission set (see :mod:`storage.access`). A
plain string actor carries identity (for provenance) but no role,
so role enforcement for those happens in the service layer (the
sibling builds' convention).

Every operation validates fully before it mutates anything: a
failed operation consumes no id and changes nothing. Ids are
sequential per object type with fixed prefixes (``org-``,
``pol-``, ``col-``, ``msg-``, ``dsp-``, ``dsc-``, ``sup-``,
``enf-``, ``ret-``, ``key-``, ``int-``).

Metadata discipline: this store holds records ABOUT archived
messages -- an opaque message reference, opaque sender/recipient
references, an archived-at moment, a recorded size, a format
label. It stores no message payload, no subject line, no body, no
attachment content: there is no field on any shape that could hold
one, and the shape is pinned by test. It likewise stores no key
material: a key-custody record names a custodian by opaque
reference and a key by an opaque label, and nothing else about the
key exists here. The actual byte storage of archived messages is
the Extended payload plane.

Derivation discipline: a message's retention state is derived at
read time and never stored. The single seam
:func:`_derive_retention_state` computes ``retained`` /
``disposition_eligible`` / ``disposed`` from the archived-at
moment, the collection's retention policy, and the presence of a
disposition record. The stored message record carries no
retention-state key. A disposition may be recorded only when the
derived state at the disposition moment is
``disposition_eligible`` -- the retention gate. Event-driven
lifecycle state, by contrast, is stored, as in the sibling
builds' record lifecycles: a supervision review's pending /
reviewed / escalated state, a retrieval's requested / completed
state, a custody record's active / retired state, and an
integration record's active / inactive state change only through
recorded actions.

Scoring discipline: nothing in this store computes a score, a
rating, or a ranking of any organization, message, or custodian,
and no record shape carries a field for one. The summary returns
counts and recorded values only.

Registry discipline: integration records describe connections to
external systems; the registry never performs one. Recording an
integration changes no external system, opens no connection, and
moves no message.

The store records every successful mutation to its audit log
(when one is attached). Reads are not audited here; denied
attempts and audit reads are the HTTP layer's responsibility, so
nothing is recorded twice.

High-baseline uplift [L3] (AU-5 fail closed): every mutating method
is wrapped by :func:`_fail_closed` -- it runs against a snapshot of
the store state, and if its audit write raises
:class:`~storage.errors.AuditWriteError` (the entry could not be
durably recorded), the snapshot is restored in full (records and id
counters) and the error propagates, so an operation whose audit
write fails does not proceed. The snapshot pattern is the proven
one from the sibling High groups (``groups/accounting-l3`` /
``groups/ai-l3``, carried through ``groups/development-tools-l3``;
our own Apache-2.0 code), applied to this store's eleven record
dicts. Read methods are not wrapped: in this package they record
no audit entry on success, so there is no audit write to fail
closed on.
"""

import copy
import functools
import re
import threading
from datetime import datetime, timedelta, timezone

from .access import require
from .audit import actor_name
from .errors import AuditWriteError, NotFoundError, ValidationError

RETENTION_STATES = ("retained", "disposition_eligible", "disposed")
SUPERVISION_STATES = ("pending", "reviewed", "escalated")
ENFORCEMENT_ACTIONS = (
    "block_access",
    "block_export",
    "extend_retention",
    "block_disposition",
    "flag_for_review",
)
RETRIEVAL_MODES = ("realtime", "batch")
RETRIEVAL_DESTINATIONS = ("inbox", "data_file", "interface")
INTEGRATION_KINDS = ("mail_platform", "directory")
CUSTODY_STATES = ("active", "retired")
INTEGRATION_STATES = ("active", "inactive")


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


def _derive_retention_state(archived_at, retention_days, disposed, now):
    """Retention derivation seam: a message's retention state,
    computed from its archived-at moment, its collection's
    retention period in days, and whether a disposition has been
    recorded for it.

    - ``disposed`` once a disposition record exists, at any clock;
    - ``disposition_eligible`` when ``now`` has reached
      ``archived_at + retention_days``;
    - ``retained`` before that boundary.

    Pure function over recorded values. Nothing about the state is
    stored anywhere; the message view and the summary both compute
    it through this seam, and the disposition gate reads it too,
    so the three can never disagree.
    """
    if disposed:
        return "disposed"
    boundary = archived_at + timedelta(days=retention_days)
    if now >= boundary:
        return "disposition_eligible"
    return "retained"


def _fail_closed(method):
    """Wrap a store operation so an audit write failure rolls it back.

    High-baseline uplift (AU-5) [L3]: the wrapped method runs against a
    snapshot of the store state; if it raises
    :class:`~storage.errors.AuditWriteError` (its audit entry could not
    be durably recorded), the snapshot is restored and the error
    propagates. Other exceptions keep the store's existing guarantee
    (validation happens before mutation, so nothing is half-applied).
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        snapshot = self._snapshot_state()
        try:
            return method(self, *args, **kwargs)
        except AuditWriteError:
            self._restore_state(snapshot)
            raise

    return wrapper


class StorageStore:
    """In-memory message-archiving records store with an optional
    audit log."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._organizations = {}
        self._policies = {}
        self._collections = {}
        self._messages = {}
        self._dispositions = {}
        self._discoveries = {}
        self._supervisions = {}
        self._enforcements = {}
        self._retrievals = {}
        self._custodies = {}
        self._integrations = {}
        self._counters = {}

    # -- internal helpers ---------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _record(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor, action, target, details)

    def _snapshot_state(self):
        """Deep-copy the mutable store state (AU-5 rollback image) [L3]."""
        return (
            copy.deepcopy(self._organizations),
            copy.deepcopy(self._policies),
            copy.deepcopy(self._collections),
            copy.deepcopy(self._messages),
            copy.deepcopy(self._dispositions),
            copy.deepcopy(self._discoveries),
            copy.deepcopy(self._supervisions),
            copy.deepcopy(self._enforcements),
            copy.deepcopy(self._retrievals),
            copy.deepcopy(self._custodies),
            copy.deepcopy(self._integrations),
            dict(self._counters),
        )

    def _restore_state(self, snapshot):
        """Restore a snapshot taken by :meth:`_snapshot_state` [L3]."""
        (
            self._organizations,
            self._policies,
            self._collections,
            self._messages,
            self._dispositions,
            self._discoveries,
            self._supervisions,
            self._enforcements,
            self._retrievals,
            self._custodies,
            self._integrations,
            self._counters,
        ) = snapshot

    @staticmethod
    def _check_role(actor, action):
        if hasattr(actor, "role"):
            require(actor, action)

    def _organization(self, org_id):
        organization = self._organizations.get(org_id)
        if organization is None:
            raise NotFoundError("no such organization: %r" % (org_id,))
        return organization

    def _policy(self, policy_id):
        policy = self._policies.get(policy_id)
        if policy is None:
            raise NotFoundError("no such retention policy: %r" % (policy_id,))
        return policy

    def _collection(self, collection_id):
        collection = self._collections.get(collection_id)
        if collection is None:
            raise NotFoundError("no such collection: %r" % (collection_id,))
        return collection

    def _message(self, message_id):
        message = self._messages.get(message_id)
        if message is None:
            raise NotFoundError("no such archived message: %r" % (message_id,))
        return message

    def _custody(self, custody_id):
        custody = self._custodies.get(custody_id)
        if custody is None:
            raise NotFoundError("no such key custody record: %r" % (custody_id,))
        return custody

    # -- organizations ---------------------------------------------------------

    @_fail_closed
    def create_organization(self, actor, ref, label):
        """Register an organization by opaque reference."""
        self._check_role(actor, "register")
        _text(ref, "ref")
        _text(label, "label")
        with self._lock:
            for existing in self._organizations.values():
                if existing["ref"] == ref:
                    raise ValidationError(
                        "organization ref already exists: %r" % (ref,))
            organization = {
                "id": self._mint("org-"),
                "ref": ref,
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._organizations[organization["id"]] = organization
        self._record(actor, "organization_create", organization["id"],
                     {"ref": ref})
        return dict(organization)

    def get_organization(self, actor, org_id):
        self._check_role(actor, "read")
        return dict(self._organization(org_id))

    def list_organizations(self, actor):
        self._check_role(actor, "read")
        return [dict(o) for o in self._organizations.values()]

    # -- retention policies -------------------------------------------------------

    @_fail_closed
    def create_policy(self, actor, label, retention_days):
        """Record a retention policy: a label and a retention
        period in whole days. Policies are immutable once recorded
        (there is deliberately no update operation), so a retention
        derivation is always reproducible against the policy the
        collection named. The period is an integer; booleans and
        floats are rejected whole."""
        self._check_role(actor, "register")
        _text(label, "label")
        if isinstance(retention_days, bool) or not isinstance(retention_days, int) \
                or retention_days <= 0:
            raise ValidationError("retention_days must be a positive integer")
        with self._lock:
            policy = {
                "id": self._mint("pol-"),
                "label": label,
                "retention_days": retention_days,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._policies[policy["id"]] = policy
        self._record(actor, "policy_create", policy["id"],
                     {"retention_days": retention_days})
        return dict(policy)

    def get_policy(self, actor, policy_id):
        self._check_role(actor, "read")
        return dict(self._policy(policy_id))

    def list_policies(self, actor):
        self._check_role(actor, "read")
        return [dict(p) for p in self._policies.values()]

    # -- collections -----------------------------------------------------------------

    @_fail_closed
    def create_collection(self, actor, org_id, label, policy_id, format_label):
        """Open an archive collection for an organization under a
        retention policy. ``format_label`` is caller-stated text
        (for example, the native format of the archived messages);
        it is a label, not a conversion -- format conversion is
        Extended."""
        self._check_role(actor, "register")
        self._organization(org_id)
        self._policy(policy_id)
        _text(label, "label")
        _text(format_label, "format_label")
        with self._lock:
            collection = {
                "id": self._mint("col-"),
                "org_id": org_id,
                "label": label,
                "policy_id": policy_id,
                "format_label": format_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._collections[collection["id"]] = collection
        self._record(actor, "collection_create", collection["id"],
                     {"org_id": org_id, "policy_id": policy_id})
        return dict(collection)

    def get_collection(self, actor, collection_id):
        self._check_role(actor, "read")
        return dict(self._collection(collection_id))

    def list_collections(self, actor, org_id=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        return [
            dict(c) for c in self._collections.values()
            if org_id is None or c["org_id"] == org_id
        ]

    # -- message archive records -------------------------------------------------------

    def _message_view(self, message, now=None):
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        collection = self._collections[message["collection_id"]]
        policy = self._policies[collection["policy_id"]]
        archived = _parse_moment(message["archived_at"], "archived_at")
        view = dict(message)
        view["recipient_refs"] = list(message["recipient_refs"])
        view["retention_until"] = (
            archived + timedelta(days=policy["retention_days"])
        ).isoformat()
        view["retention_state"] = _derive_retention_state(
            archived,
            policy["retention_days"],
            message["id"] in self._dispositions_by_message(),
            moment,
        )
        return view

    def _dispositions_by_message(self):
        return {d["message_id"]: d for d in self._dispositions.values()}

    @_fail_closed
    def archive_message(self, actor, collection_id, message_ref, sender_ref,
                        recipient_refs, archived_at, size_bytes,
                        format_label, custody_id=None):
        """Record an archived message's metadata in a collection.

        Metadata only: the caller supplies an opaque
        ``message_ref``, opaque sender/recipient references, the
        archived-at moment, a recorded size in bytes, and a format
        label. No payload, subject, or content is accepted -- the
        record shape has no field for one. ``message_ref`` is
        unique within the collection. If a key-custody record is
        named, it must belong to the same collection and be
        active: a message is archived under live custody or under
        none that is claimed.
        """
        self._check_role(actor, "archive")
        collection = self._collection(collection_id)
        _text(message_ref, "message_ref")
        _text(sender_ref, "sender_ref")
        if not isinstance(recipient_refs, (list, tuple)):
            raise ValidationError("recipient_refs must be a list of references")
        recipients = []
        for ref in recipient_refs:
            _text(ref, "recipient_ref")
            recipients.append(ref)
        stamp = _parse_moment(archived_at, "archived_at").isoformat()
        if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) \
                or size_bytes < 0:
            raise ValidationError("size_bytes must be a non-negative integer")
        _text(format_label, "format_label")
        if custody_id is not None:
            custody = self._custody(custody_id)
            if custody["collection_id"] != collection_id:
                raise ValidationError(
                    "custody record %s does not belong to collection %s"
                    % (custody_id, collection_id))
            if custody["status"] != "active":
                raise ValidationError(
                    "custody record %s is %r; messages are archived "
                    "only under active custody" % (custody_id, custody["status"]))
        with self._lock:
            for existing in self._messages.values():
                if existing["collection_id"] == collection_id \
                        and existing["message_ref"] == message_ref:
                    raise ValidationError(
                        "message_ref %r already exists in collection %s"
                        % (message_ref, collection_id))
            message = {
                "id": self._mint("msg-"),
                "collection_id": collection_id,
                "message_ref": message_ref,
                "sender_ref": sender_ref,
                "recipient_refs": recipients,
                "archived_at": stamp,
                "size_bytes": size_bytes,
                "format_label": format_label,
                "custody_id": custody_id,
                "seq": self._counters["msg-"],
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._messages[message["id"]] = message
        self._record(actor, "message_archive", message["id"],
                     {"collection_id": collection_id})
        return self._message_view(message)

    def get_message(self, actor, message_id, now=None):
        self._check_role(actor, "read")
        return self._message_view(self._message(message_id), now=now)

    def list_messages(self, actor, collection_id=None, retention_state=None,
                      now=None):
        self._check_role(actor, "read")
        if collection_id is not None:
            self._collection(collection_id)
        if retention_state is not None and retention_state not in RETENTION_STATES:
            raise ValidationError(
                "unknown retention state: %r" % (retention_state,))
        result = []
        for message in self._messages.values():
            if collection_id is not None \
                    and message["collection_id"] != collection_id:
                continue
            view = self._message_view(message, now=now)
            if retention_state is not None \
                    and view["retention_state"] != retention_state:
                continue
            result.append(view)
        result.sort(key=lambda m: m["seq"])
        return result

    # -- dispositions (the retention gate) ----------------------------------------------

    @_fail_closed
    def record_disposition(self, actor, message_id, method_label, at=None):
        """Record the disposition of an archived message.

        The retention gate: a disposition is recorded only when
        the message's derived retention state at the disposition
        moment is ``disposition_eligible``. A message still inside
        its retention period cannot be disposed of, and a message
        already disposed of cannot be disposed of again. This
        records that disposition occurred; destruction of the
        archived payload bytes is the Extended storage plane's --
        this store holds no payloads to destroy.
        """
        self._check_role(actor, "archive")
        message = self._message(message_id)
        _text(method_label, "method_label")
        moment = _parse_moment(at, "at") if at is not None else _utc_now()
        collection = self._collections[message["collection_id"]]
        policy = self._policies[collection["policy_id"]]
        state = _derive_retention_state(
            _parse_moment(message["archived_at"], "archived_at"),
            policy["retention_days"],
            message["id"] in self._dispositions_by_message(),
            moment,
        )
        if state != "disposition_eligible":
            raise ValidationError(
                "message %s is %r; disposition is recorded only for "
                "disposition-eligible messages" % (message_id, state))
        with self._lock:
            disposition = {
                "id": self._mint("dsp-"),
                "message_id": message_id,
                "method_label": method_label,
                "disposed_at": moment.isoformat(),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._dispositions[disposition["id"]] = disposition
        self._record(actor, "disposition_record", disposition["id"],
                     {"message_id": message_id})
        return dict(disposition)

    def list_dispositions(self, actor, message_id=None):
        self._check_role(actor, "read")
        if message_id is not None:
            self._message(message_id)
        return [
            dict(d) for d in self._dispositions.values()
            if message_id is None or d["message_id"] == message_id
        ]

    # -- discovery records -----------------------------------------------------------------

    def _match_messages(self, collection_id, sender_ref, from_at, to_at):
        matched = []
        for message in self._messages.values():
            if message["collection_id"] != collection_id:
                continue
            if sender_ref is not None and message["sender_ref"] != sender_ref:
                continue
            archived = _parse_moment(message["archived_at"], "archived_at")
            if from_at is not None and archived < from_at:
                continue
            if to_at is not None and archived > to_at:
                continue
            matched.append(message)
        matched.sort(key=lambda m: m["seq"])
        return matched

    @_fail_closed
    def record_discovery(self, actor, matter_ref, collection_id,
                         sender_ref=None, from_at=None, to_at=None):
        """Record a search & discovery request and its scope.

        The record names the matter (an opaque reference), the
        collection, and optional sender / date-range scope; the
        result count is computed from the archive records at
        recording time. There is deliberately no free-text query
        field: discovery over this substrate runs over record
        metadata (references and moments), and the content search
        engine over message bodies is Extended -- this store holds
        no bodies to search.
        """
        self._check_role(actor, "discover")
        self._collection(collection_id)
        _text(matter_ref, "matter_ref")
        _optional_text(sender_ref, "sender_ref")
        start = _parse_moment(from_at, "from_at") if from_at is not None else None
        end = _parse_moment(to_at, "to_at") if to_at is not None else None
        if start is not None and end is not None and end < start:
            raise ValidationError("to_at must not precede from_at")
        matched = self._match_messages(collection_id, sender_ref, start, end)
        with self._lock:
            discovery = {
                "id": self._mint("dsc-"),
                "matter_ref": matter_ref,
                "collection_id": collection_id,
                "sender_ref": sender_ref,
                "from_at": from_at,
                "to_at": to_at,
                "result_count": len(matched),
                "result_message_ids": [m["id"] for m in matched],
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._discoveries[discovery["id"]] = discovery
        self._record(actor, "discovery_record", discovery["id"],
                     {"collection_id": collection_id,
                      "result_count": discovery["result_count"]})
        return dict(discovery)

    def list_discoveries(self, actor, collection_id=None):
        self._check_role(actor, "read")
        if collection_id is not None:
            self._collection(collection_id)
        result = []
        for discovery in self._discoveries.values():
            if collection_id is not None \
                    and discovery["collection_id"] != collection_id:
                continue
            copied = dict(discovery)
            copied["result_message_ids"] = list(discovery["result_message_ids"])
            result.append(copied)
        return result

    # -- supervision review records ----------------------------------------------------------

    @_fail_closed
    def create_review(self, actor, message_id, reviewer_ref):
        """Open a supervision review of an archived message for a
        reviewer (opaque reference). The review console and its
        sampling machinery are Extended; this is the review
        record."""
        self._check_role(actor, "supervise")
        self._message(message_id)
        _text(reviewer_ref, "reviewer_ref")
        with self._lock:
            review = {
                "id": self._mint("sup-"),
                "message_id": message_id,
                "reviewer_ref": reviewer_ref,
                "status": "pending",
                "note": None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "outcome_by": None,
                "outcome_utc": None,
            }
            self._supervisions[review["id"]] = review
        self._record(actor, "review_create", review["id"],
                     {"message_id": message_id})
        return dict(review)

    @_fail_closed
    def record_review_outcome(self, actor, review_id, outcome, note=None):
        """Record a review's outcome by recorded action:
        ``pending -> reviewed``, ``pending -> escalated``, or
        ``escalated -> reviewed``. ``reviewed`` is terminal."""
        self._check_role(actor, "supervise")
        review = self._supervisions.get(review_id)
        if review is None:
            raise NotFoundError("no such review: %r" % (review_id,))
        if outcome not in ("reviewed", "escalated"):
            raise ValidationError("unknown review outcome: %r" % (outcome,))
        _optional_text(note, "note")
        allowed = {
            "pending": ("reviewed", "escalated"),
            "escalated": ("reviewed",),
            "reviewed": (),
        }
        with self._lock:
            if outcome not in allowed[review["status"]]:
                raise ValidationError(
                    "review %s is %r; outcome %r is not reachable"
                    % (review_id, review["status"], outcome))
            review["status"] = outcome
            review["note"] = note
            review["outcome_by"] = actor_name(actor)
            review["outcome_utc"] = _utc_now().isoformat()
        self._record(actor, "review_outcome", review_id, {"outcome": outcome})
        return dict(review)

    def list_reviews(self, actor, message_id=None, status=None):
        self._check_role(actor, "read")
        if message_id is not None:
            self._message(message_id)
        if status is not None and status not in SUPERVISION_STATES:
            raise ValidationError("unknown review status: %r" % (status,))
        return [
            dict(r) for r in self._supervisions.values()
            if (message_id is None or r["message_id"] == message_id)
            and (status is None or r["status"] == status)
        ]

    # -- enforcement action records -------------------------------------------------------------

    @_fail_closed
    def record_enforcement(self, actor, action, target_ref, policy_ref,
                           note=None):
        """Record an enforcement action taken under a stated
        policy. This records the action; executing enforcement in
        connected systems is Extended, and a record here changes
        nothing outside this store -- in particular, an
        ``extend_retention`` record does not alter any retention
        derivation, which answers only to the collection's policy
        record."""
        self._check_role(actor, "enforce")
        if action not in ENFORCEMENT_ACTIONS:
            raise ValidationError("unknown enforcement action: %r" % (action,))
        _text(target_ref, "target_ref")
        _text(policy_ref, "policy_ref")
        _optional_text(note, "note")
        with self._lock:
            enforcement = {
                "id": self._mint("enf-"),
                "action": action,
                "target_ref": target_ref,
                "policy_ref": policy_ref,
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._enforcements[enforcement["id"]] = enforcement
        self._record(actor, "enforcement_record", enforcement["id"],
                     {"action": action})
        return dict(enforcement)

    def list_enforcements(self, actor, action=None):
        self._check_role(actor, "read")
        if action is not None and action not in ENFORCEMENT_ACTIONS:
            raise ValidationError("unknown enforcement action: %r" % (action,))
        return [
            dict(e) for e in self._enforcements.values()
            if action is None or e["action"] == action
        ]

    # -- retrieval & export records -----------------------------------------------------------------

    @_fail_closed
    def create_retrieval(self, actor, message_id, mode, destination,
                         requester_ref):
        """Record a retrieval/export request for an archived
        message: realtime or batch, to an inbox, a data file, or
        the interface. Delivery itself -- producing the file,
        placing the message in an inbox -- is Extended transport;
        this is the request record and its recorded completion."""
        self._check_role(actor, "retrieve")
        self._message(message_id)
        if mode not in RETRIEVAL_MODES:
            raise ValidationError("unknown retrieval mode: %r" % (mode,))
        if destination not in RETRIEVAL_DESTINATIONS:
            raise ValidationError(
                "unknown retrieval destination: %r" % (destination,))
        _text(requester_ref, "requester_ref")
        with self._lock:
            retrieval = {
                "id": self._mint("ret-"),
                "message_id": message_id,
                "mode": mode,
                "destination": destination,
                "requester_ref": requester_ref,
                "status": "requested",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "completed_by": None,
                "completed_utc": None,
            }
            self._retrievals[retrieval["id"]] = retrieval
        self._record(actor, "retrieval_create", retrieval["id"],
                     {"message_id": message_id, "mode": mode})
        return dict(retrieval)

    @_fail_closed
    def complete_retrieval(self, actor, retrieval_id):
        """Record a retrieval's completion by recorded action."""
        self._check_role(actor, "retrieve")
        retrieval = self._retrievals.get(retrieval_id)
        if retrieval is None:
            raise NotFoundError("no such retrieval: %r" % (retrieval_id,))
        with self._lock:
            if retrieval["status"] == "completed":
                raise ValidationError(
                    "retrieval %s is already completed" % retrieval_id)
            retrieval["status"] = "completed"
            retrieval["completed_by"] = actor_name(actor)
            retrieval["completed_utc"] = _utc_now().isoformat()
        self._record(actor, "retrieval_complete", retrieval_id, {})
        return dict(retrieval)

    def list_retrievals(self, actor, message_id=None, status=None):
        self._check_role(actor, "read")
        if message_id is not None:
            self._message(message_id)
        if status is not None and status not in ("requested", "completed"):
            raise ValidationError("unknown retrieval status: %r" % (status,))
        return [
            dict(r) for r in self._retrievals.values()
            if (message_id is None or r["message_id"] == message_id)
            and (status is None or r["status"] == status)
        ]

    # -- key custody records ---------------------------------------------------------------------------

    @_fail_closed
    def create_custody(self, actor, org_id, collection_id, custodian_ref,
                       key_label):
        """Record key custody for a collection: the custodian
        (opaque reference -- the premise equipment's operator,
        stated generically) and the key (an opaque label).

        No key material is accepted or stored: the shape has no
        field that could hold any. At most one custody record per
        collection may be active at a time -- the fork's own
        statement is that a single holder holds the keys, and the
        registry keeps that discipline as a record invariant.
        """
        self._check_role(actor, "custody")
        self._organization(org_id)
        collection = self._collection(collection_id)
        if collection["org_id"] != org_id:
            raise ValidationError(
                "collection %s does not belong to organization %s"
                % (collection_id, org_id))
        _text(custodian_ref, "custodian_ref")
        _text(key_label, "key_label")
        with self._lock:
            for existing in self._custodies.values():
                if existing["collection_id"] == collection_id \
                        and existing["status"] == "active":
                    raise ValidationError(
                        "collection %s already has an active custody "
                        "record: %s" % (collection_id, existing["id"]))
            custody = {
                "id": self._mint("key-"),
                "org_id": org_id,
                "collection_id": collection_id,
                "custodian_ref": custodian_ref,
                "key_label": key_label,
                "status": "active",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "retired_by": None,
                "retired_utc": None,
            }
            self._custodies[custody["id"]] = custody
        self._record(actor, "custody_create", custody["id"],
                     {"collection_id": collection_id})
        return dict(custody)

    @_fail_closed
    def retire_custody(self, actor, custody_id):
        """Retire a custody record by recorded action. Messages
        already archived under it keep their recorded linkage;
        new archival under a retired record is refused."""
        self._check_role(actor, "custody")
        custody = self._custody(custody_id)
        with self._lock:
            if custody["status"] == "retired":
                raise ValidationError(
                    "custody record %s is already retired" % custody_id)
            custody["status"] = "retired"
            custody["retired_by"] = actor_name(actor)
            custody["retired_utc"] = _utc_now().isoformat()
        self._record(actor, "custody_retire", custody_id, {})
        return dict(custody)

    def list_custodies(self, actor, collection_id=None, status=None):
        self._check_role(actor, "read")
        if collection_id is not None:
            self._collection(collection_id)
        if status is not None and status not in CUSTODY_STATES:
            raise ValidationError("unknown custody status: %r" % (status,))
        return [
            dict(c) for c in self._custodies.values()
            if (collection_id is None or c["collection_id"] == collection_id)
            and (status is None or c["status"] == status)
        ]

    # -- integration registry (records only) -------------------------------------------------------------

    @_fail_closed
    def create_integration(self, actor, org_id, kind, label):
        """Register an integration record (mail platform or
        directory) for an organization. Records only: registering
        an integration connects nothing, authenticates no one, and
        moves no message. The live connectors are Extended, and
        identity itself stays with the embedding organization."""
        self._check_role(actor, "register")
        self._organization(org_id)
        if kind not in INTEGRATION_KINDS:
            raise ValidationError("unknown integration kind: %r" % (kind,))
        _text(label, "label")
        with self._lock:
            integration = {
                "id": self._mint("int-"),
                "org_id": org_id,
                "kind": kind,
                "label": label,
                "status": "active",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._integrations[integration["id"]] = integration
        self._record(actor, "integration_create", integration["id"],
                     {"org_id": org_id, "kind": kind})
        return dict(integration)

    @_fail_closed
    def deactivate_integration(self, actor, integration_id):
        """Deactivate an integration record by recorded action."""
        self._check_role(actor, "register")
        integration = self._integrations.get(integration_id)
        if integration is None:
            raise NotFoundError(
                "no such integration: %r" % (integration_id,))
        with self._lock:
            if integration["status"] == "inactive":
                raise ValidationError(
                    "integration %s is already inactive" % integration_id)
            integration["status"] = "inactive"
        self._record(actor, "integration_deactivate", integration_id, {})
        return dict(integration)

    def list_integrations(self, actor, org_id=None, kind=None):
        self._check_role(actor, "read")
        if org_id is not None:
            self._organization(org_id)
        if kind is not None and kind not in INTEGRATION_KINDS:
            raise ValidationError("unknown integration kind: %r" % (kind,))
        return [
            dict(i) for i in self._integrations.values()
            if (org_id is None or i["org_id"] == org_id)
            and (kind is None or i["kind"] == kind)
        ]

    def audit_read(self, actor):
        """Return the audit trail. Requires the ``audit_read``
        permission (held by admin and, at this tier, by the
        separated ``auditor`` role -- AC-5 [L3])."""
        self._check_role(actor, "audit_read")
        entries = self.audit.entries() if self.audit is not None else []
        return {"entries": entries, "count": len(entries)}

    # -- search and summary ---------------------------------------------------------------------------------

    def search(self, actor, query):
        """Literal case-insensitive substring search over
        organizations and policies (ref and label), collections
        (label), and archived-message metadata (message, sender,
        and recipient references). Metadata only -- there is no
        content in this store to search."""
        self._check_role(actor, "read")
        _text(query, "query")
        needle = query.lower()
        organizations = [
            dict(o) for o in self._organizations.values()
            if needle in o["ref"].lower() or needle in o["label"].lower()
        ]
        policies = [
            dict(p) for p in self._policies.values()
            if needle in p["label"].lower()
        ]
        collections = [
            dict(c) for c in self._collections.values()
            if needle in c["label"].lower()
        ]
        messages = [
            self._message_view(m) for m in self._messages.values()
            if needle in m["message_ref"].lower()
            or needle in m["sender_ref"].lower()
            or any(needle in r.lower() for r in m["recipient_refs"])
        ]
        messages.sort(key=lambda m: m["seq"])
        return {
            "organizations": organizations,
            "policies": policies,
            "collections": collections,
            "messages": messages,
        }

    def summary(self, actor, now=None):
        """Counts over the whole registry, computed on read from
        records only. Retention-state counts go through the same
        derivation seam as the message views, at the stated
        ``now``. Counts and recorded values -- never scores."""
        self._check_role(actor, "read")
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        by_retention = {state: 0 for state in RETENTION_STATES}
        for message in self._messages.values():
            view = self._message_view(message, now=moment)
            by_retention[view["retention_state"]] += 1
        supervision_by_status = {state: 0 for state in SUPERVISION_STATES}
        for review in self._supervisions.values():
            supervision_by_status[review["status"]] += 1
        integrations_by_kind = {kind: 0 for kind in INTEGRATION_KINDS}
        for integration in self._integrations.values():
            integrations_by_kind[integration["kind"]] += 1
        return {
            "organizations": len(self._organizations),
            "policies": len(self._policies),
            "collections": len(self._collections),
            "messages": len(self._messages),
            "messages_by_retention_state": by_retention,
            "dispositions": len(self._dispositions),
            "discoveries": len(self._discoveries),
            "supervision_by_status": supervision_by_status,
            "enforcement_actions": len(self._enforcements),
            "retrievals": len(self._retrievals),
            "retrievals_completed": sum(
                1 for r in self._retrievals.values()
                if r["status"] == "completed"
            ),
            "custody_active": sum(
                1 for c in self._custodies.values() if c["status"] == "active"
            ),
            "integrations_by_kind": integrations_by_kind,
        }
