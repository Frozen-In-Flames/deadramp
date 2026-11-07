"""Final GAPS batch extensions for the Law Enforcement untiered set.

Clean-room, standard-library-only records extensions for the 9
open Extended entries of this set's union spec: 7 built as
in-substrate records over the core's own substrate, 1 shipped as
a labeled reference implementation, and 1 re-judged to a written
re-scope under PLATFORM-LAYER.md decision 6 (see ``BATCH.md`` in
the group directory for the per-entry disposition, the
re-judgment grounds, and the adjudication notes).

Design, following the core's doctrines and this set's tier
discipline:

- This module is a wrapper around :class:`LawEnfStore`; the core
  modules are untouched (byte-identical). Matter existence,
  membership, and lifecycle state are always read through the
  core store's public API, never re-implemented.
- **Tier null binds the whole surface.** The set's forks publish
  no FedRAMP impact level, so nothing here asserts or records a
  tier, a control baseline, or an equivalence: no record shape
  carries a tier-shaped key, and the batch tests scan every
  record and view recursively for one (and for floats and
  numeric lists).
- **The hard privacy rule binds the whole surface.** Every
  record is keyed by an opaque caller-supplied ``*_ref`` string
  or a core record id. No record shape can hold a real name, a
  case subject, a party, an address, an identifier of a person,
  or any content: message bodies and report bodies exist only
  as SHA-256 digests, exactly as the core holds queries and
  notes. There is no parameter anywhere in this module that
  could accept content, query text, note text, or a person's
  identifier -- the batch tests pin that by signature
  (``TypeError``).
- RBAC goes through :mod:`lawenf.access` exactly as the core
  enforces it: the extension maps each operation onto an
  existing core action (the core action set is fixed), checks it
  *before* any state change or id allocation for actors that
  carry a role, and records denied attempts on the core audit
  log as ``ext_<action>:denied``. Matter membership -- the
  core's second boundary -- is enforced through the core store
  on every operation, and writes additionally require an open
  matter, mirroring the core's ``need_open`` discipline.
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``.
- Derived values are derived at read and never stored: an
  operation's linked-record counts, a message's receipt count
  and latest reported outcome, a chain reference's in/out
  degree, a lead's reported-link count. Stored records carry
  no derived key; tests pin that.
- The chain-degree derivation lives at a single named seam
  (``_chain_degree``): a deterministic count over the recorded
  link records. The seam is the batch's fresh negative control.
  The graph is never traversed and no attribution is computed:
  a link record exists only because a caller reported it.
- Nothing here executes against an external system, and the
  build performs no cryptography of its own: coordination
  receipts carry ``reference_transport: True`` and
  ``encrypted_here: False`` (the one fork's encryption claim is
  the fork's own, recorded in the union spec; PLATFORM-LAYER.md
  decisions 2-3). The risk-assessment family ships as a labeled
  reference implementation: every record carries
  ``reference_stub: True``, outcomes are recorded verbatim as
  reported labels, and no risk score is computed or storable
  anywhere on this surface.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None:
        _non_empty(value, what)
    return value


def _sha256_or_none(value, what):
    if value is not None:
        if not isinstance(value, str) or not _SHA256_RE.match(value):
            raise ValidationError(
                "%s must be exactly 64 lowercase hex characters" % (what,)
            )
    return value


class LawEnfExtensions:
    """GAPS-batch extension surface over a core LawEnfStore."""

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

        Mirrors the core store: an actor must be present; actors
        carrying a role are checked against the core permission
        matrix before anything changes; plain strings carry
        identity only.
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

    def _matter(self, actor, matter_id, audit_action, need_open=False):
        """Resolve a matter through the core store (existence and
        membership enforced there); a membership denial is audited
        under the extension action name. Writes pass
        ``need_open=True`` and require an open matter, mirroring
        the core's child-record discipline."""
        try:
            matter = self.store.get_matter(matter_id, actor)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", matter_id)
            raise
        if need_open and matter["status"] != "open":
            raise ValidationError(
                "matter %s is closed; no new records may be added" % (matter_id,)
            )
        return matter

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

    def _get(self, kind, record_id, matter_id=None):
        record = self._records.get((kind, record_id))
        if record is None or (matter_id is not None
                              and record["matter_id"] != matter_id):
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id, matter_id=None):
        return copy.deepcopy(self._get(kind, record_id, matter_id))

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

    def _check_ref_unique(self, kind, matter_id, field, value, what):
        for record in self._list(kind, matter_id=matter_id):
            if record[field] == value:
                raise ValidationError(
                    "%s %r already exists in matter %s"
                    % (what, value, matter_id))

    # -- Command-and-control & operational planning -------------------
    # An operation here is a planning record: an opaque reference,
    # an optional plan reference, and provenance. Plans are
    # definition records held as data. Nothing is commanded and
    # no order is issued (``commanded_here`` / ``orders_issued_here``
    # / ``executed_here`` are False); the operational platform is
    # the fork's product. Linked coordination messages, location
    # reports, and after-action reports bind to an operation by
    # id; the operation view derives their counts at read.

    def record_operation(self, matter_id, operation_ref, actor,
                         plan_ref=None):
        """Record an operation (planning record). Action: matter_write."""
        self._guard(actor, "matter_write", "ext_operation_record", matter_id)
        _non_empty(operation_ref, "operation_ref")
        _string_or_none(plan_ref, "plan_ref")
        with self._lock:
            self._matter(actor, matter_id, "ext_operation_record",
                         need_open=True)
            self._check_ref_unique("operation", matter_id, "operation_ref",
                                   operation_ref, "operation_ref")
            return self._create(
                "operation", "opn",
                {"matter_id": matter_id, "operation_ref": operation_ref,
                 "plan_ref": plan_ref, "commanded_here": False,
                 "orders_issued_here": False, "status": "recorded"},
                actor, "ext_operation_record")

    def get_operation(self, matter_id, operation_id, actor=None):
        """Return one operation record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_operation_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_operation_read")
            return self._fetch("operation", operation_id, matter_id)

    def list_operations(self, matter_id, actor=None):
        """Return operation records for a matter. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_operation_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_operation_read")
            return self._list("operation", matter_id=matter_id)

    def record_plan(self, matter_id, plan_ref, actor, operation_id=None):
        """Record an operational plan definition. Action: matter_write.

        A plan is a definition held as data; it is never executed
        here (``executed_here`` is False).
        """
        self._guard(actor, "matter_write", "ext_plan_record", matter_id)
        _non_empty(plan_ref, "plan_ref")
        with self._lock:
            self._matter(actor, matter_id, "ext_plan_record", need_open=True)
            if operation_id is not None:
                self._get("operation", operation_id, matter_id)
            self._check_ref_unique("plan", matter_id, "plan_ref",
                                   plan_ref, "plan_ref")
            return self._create(
                "plan", "pln",
                {"matter_id": matter_id, "plan_ref": plan_ref,
                 "operation_id": operation_id, "definition_only": True,
                 "executed_here": False, "status": "recorded"},
                actor, "ext_plan_record")

    def get_plan(self, matter_id, plan_id, actor=None):
        """Return one plan record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_plan_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_plan_read")
            return self._fetch("plan", plan_id, matter_id)

    def list_plans(self, matter_id, operation_id=None, actor=None):
        """Return plan records for a matter. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_plan_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_plan_read")
            if operation_id is not None:
                self._get("operation", operation_id, matter_id)
            return self._list("plan", matter_id=matter_id,
                              operation_id=operation_id)

    def operation_view(self, matter_id, operation_id, actor=None):
        """Derived view of an operation. Action: report_read.

        Counts of the coordination messages, location reports,
        and after-action reports recorded against the operation
        are computed at read; the stored operation record carries
        no counts.
        """
        self._guard_read(actor, "report_read", "ext_operation_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_operation_view")
            operation = self._get("operation", operation_id, matter_id)
            view = dict(operation)
            view["message_count"] = len(self._list(
                "coordination_message", matter_id=matter_id,
                operation_id=operation_id))
            view["location_report_count"] = len(self._list(
                "location_report", matter_id=matter_id,
                operation_id=operation_id))
            view["after_action_report_count"] = len(self._list(
                "after_action_report", matter_id=matter_id,
                operation_id=operation_id))
            view["derived_at_read"] = True
            return view

    # -- Real-time team coordination & messaging ----------------------
    # The Communication adjudicated form: a message record holds
    # an opaque reference, an optional channel reference, and the
    # body's SHA-256 digest -- never the body (the core's digest
    # discipline for queries and notes, applied to messages).
    # Delivery receipts record outcomes verbatim as reported.
    # Every record carries ``reference_transport: True`` and
    # ``transmitted_here: False``: this build transports nothing.
    # The build performs no cryptography of its own, so
    # ``encrypted_here`` is False; the fork's "encrypted
    # messaging" claim is the fork's own (union spec, Documented
    # control claims; PLATFORM-LAYER.md decisions 2-3).

    def record_coordination_message(self, matter_id, message_ref, actor,
                                    channel_ref=None, body_sha256=None,
                                    operation_id=None):
        """Record a coordination message. Action: annotation_write."""
        self._guard(actor, "annotation_write", "ext_message_record",
                    matter_id)
        _non_empty(message_ref, "message_ref")
        _string_or_none(channel_ref, "channel_ref")
        _sha256_or_none(body_sha256, "body_sha256")
        with self._lock:
            self._matter(actor, matter_id, "ext_message_record",
                         need_open=True)
            if operation_id is not None:
                self._get("operation", operation_id, matter_id)
            self._check_ref_unique("coordination_message", matter_id,
                                   "message_ref", message_ref, "message_ref")
            return self._create(
                "coordination_message", "msg",
                {"matter_id": matter_id, "message_ref": message_ref,
                 "channel_ref": channel_ref, "operation_id": operation_id,
                 "body_sha256": body_sha256, "content_held": False,
                 "reference_transport": True, "transmitted_here": False,
                 "encrypted_here": False, "status": "recorded"},
                actor, "ext_message_record")

    def get_coordination_message(self, matter_id, message_id, actor=None):
        """Return one coordination message record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_message_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_message_read")
            return self._fetch("coordination_message", message_id, matter_id)

    def list_coordination_messages(self, matter_id, operation_id=None,
                                   actor=None):
        """Return coordination message records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_message_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_message_read")
            if operation_id is not None:
                self._get("operation", operation_id, matter_id)
            return self._list("coordination_message", matter_id=matter_id,
                              operation_id=operation_id)

    def record_delivery_receipt(self, matter_id, message_id, outcome, actor):
        """Record a delivery outcome as reported, verbatim.

        Action: annotation_write. The outcome is the channel's
        report, stored verbatim; nothing was transmitted here.
        """
        self._guard(actor, "annotation_write", "ext_receipt_record",
                    matter_id)
        _non_empty(outcome, "outcome")
        with self._lock:
            self._matter(actor, matter_id, "ext_receipt_record",
                         need_open=True)
            self._get("coordination_message", message_id, matter_id)
            return self._create(
                "delivery_receipt", "rcp",
                {"matter_id": matter_id, "message_id": message_id,
                 "outcome": outcome, "reference_transport": True,
                 "transmitted_here": False},
                actor, "ext_receipt_record")

    def list_delivery_receipts(self, matter_id, message_id=None, actor=None):
        """Return delivery receipt records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_receipt_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_receipt_read")
            if message_id is not None:
                self._get("coordination_message", message_id, matter_id)
            return self._list("delivery_receipt", matter_id=matter_id,
                              message_id=message_id)

    def message_view(self, matter_id, message_id, actor=None):
        """Derived view of a coordination message. Action: report_read.

        The receipt count and the latest reported outcome are
        computed at read from the stored receipt records; the
        stored message record carries neither.
        """
        self._guard_read(actor, "report_read", "ext_message_view", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_message_view")
            message = self._get("coordination_message", message_id, matter_id)
            receipts = self._list("delivery_receipt", matter_id=matter_id,
                                  message_id=message_id)
            view = dict(message)
            view["receipt_count"] = len(receipts)
            view["latest_outcome"] = (
                receipts[-1]["outcome"] if receipts else None)
            view["derived_at_read"] = True
            return view

    # -- GPS mapping & location services ------------------------------
    # A location report here is a caller-reported record: an
    # opaque location reference, an optional opaque place
    # reference, and a caller-supplied label stored verbatim.
    # There is no parameter that could accept coordinates, and
    # nothing is sensed or tracked (``tracked_here`` /
    # ``sensed_here`` are False): the mapping and location
    # services are the fork's platform.

    def record_location_report(self, matter_id, location_ref, actor,
                               place_ref=None, label=None, operation_id=None):
        """Record a caller-reported location report.

        Action: annotation_write.
        """
        self._guard(actor, "annotation_write", "ext_location_record",
                    matter_id)
        _non_empty(location_ref, "location_ref")
        _string_or_none(place_ref, "place_ref")
        _string_or_none(label, "label")
        with self._lock:
            self._matter(actor, matter_id, "ext_location_record",
                         need_open=True)
            if operation_id is not None:
                self._get("operation", operation_id, matter_id)
            self._check_ref_unique("location_report", matter_id,
                                   "location_ref", location_ref,
                                   "location_ref")
            return self._create(
                "location_report", "loc",
                {"matter_id": matter_id, "location_ref": location_ref,
                 "place_ref": place_ref, "label": label,
                 "operation_id": operation_id, "tracked_here": False,
                 "sensed_here": False, "status": "recorded_report"},
                actor, "ext_location_record")

    def get_location_report(self, matter_id, report_id, actor=None):
        """Return one location report record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_location_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_location_read")
            return self._fetch("location_report", report_id, matter_id)

    def list_location_reports(self, matter_id, operation_id=None, actor=None):
        """Return location report records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_location_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_location_read")
            if operation_id is not None:
                self._get("operation", operation_id, matter_id)
            return self._list("location_report", matter_id=matter_id,
                              operation_id=operation_id)

    # -- After-action documentation & reporting -----------------------
    # An after-action report here is a registry record: an opaque
    # reference, an optional link to an operation record, and the
    # report's SHA-256 digest. Reports are assembled by humans
    # elsewhere; this build generates nothing (``generated_here``
    # / ``assembled_here`` are False) and holds no report content.

    def register_after_action_report(self, matter_id, report_ref, actor,
                                     report_sha256=None, operation_id=None):
        """Register an after-action report record.

        Action: document_write.
        """
        self._guard(actor, "document_write", "ext_after_action_register",
                    matter_id)
        _non_empty(report_ref, "report_ref")
        _sha256_or_none(report_sha256, "report_sha256")
        with self._lock:
            self._matter(actor, matter_id, "ext_after_action_register",
                         need_open=True)
            if operation_id is not None:
                self._get("operation", operation_id, matter_id)
            self._check_ref_unique("after_action_report", matter_id,
                                   "report_ref", report_ref, "report_ref")
            return self._create(
                "after_action_report", "aar",
                {"matter_id": matter_id, "report_ref": report_ref,
                 "report_sha256": report_sha256,
                 "operation_id": operation_id, "content_held": False,
                 "generated_here": False, "assembled_here": False,
                 "status": "registered"},
                actor, "ext_after_action_register")

    def get_after_action_report(self, matter_id, report_id, actor=None):
        """Return one after-action report record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_after_action_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_after_action_read")
            return self._fetch("after_action_report", report_id, matter_id)

    def list_after_action_reports(self, matter_id, operation_id=None,
                                  actor=None):
        """Return after-action report records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_after_action_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_after_action_read")
            if operation_id is not None:
                self._get("operation", operation_id, matter_id)
            return self._list("after_action_report", matter_id=matter_id,
                              operation_id=operation_id)

    # -- Blockchain intelligence & investigation graph ----------------
    # The graph engine's substrate in records form: chain
    # references are opaque references with an optional network
    # label, and links are recorded relationships between two
    # registered references. A link exists here only because a
    # caller reported it. Degrees are derived at read by the
    # seam ``_chain_degree``; the stored reference record carries
    # no degree. The graph is never traversed and no attribution
    # is computed (``analyzed_here`` / ``traversed_here`` /
    # ``attribution_computed_here`` are False): the fork's
    # "glass-box attribution" is its product, not this build's.

    def register_chain_reference(self, matter_id, chain_ref, actor,
                                 network_label=None):
        """Register a blockchain reference record.

        Action: document_write. ``chain_ref`` is an opaque
        reference supplied by the caller and is unique in the
        matter; nothing about the referenced chain is fetched or
        analyzed here.
        """
        self._guard(actor, "document_write", "ext_chain_reference_register",
                    matter_id)
        _non_empty(chain_ref, "chain_ref")
        _string_or_none(network_label, "network_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_chain_reference_register",
                         need_open=True)
            self._check_ref_unique("chain_reference", matter_id, "chain_ref",
                                   chain_ref, "chain_ref")
            return self._create(
                "chain_reference", "chn",
                {"matter_id": matter_id, "chain_ref": chain_ref,
                 "network_label": network_label, "analyzed_here": False,
                 "status": "registered"},
                actor, "ext_chain_reference_register")

    def get_chain_reference(self, matter_id, reference_id, actor=None):
        """Return one chain reference record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_chain_reference_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_chain_reference_read")
            return self._fetch("chain_reference", reference_id, matter_id)

    def list_chain_references(self, matter_id, actor=None):
        """Return chain reference records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_chain_reference_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_chain_reference_read")
            return self._list("chain_reference", matter_id=matter_id)

    def record_chain_link(self, matter_id, from_reference_id,
                          to_reference_id, relation_label, actor):
        """Record a reported link between two registered references.

        Action: document_write. The link is a caller's report,
        stored as recorded; it is not the output of any analysis
        performed here.
        """
        self._guard(actor, "document_write", "ext_chain_link_record",
                    matter_id)
        _non_empty(relation_label, "relation_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_chain_link_record",
                         need_open=True)
            self._get("chain_reference", from_reference_id, matter_id)
            self._get("chain_reference", to_reference_id, matter_id)
            return self._create(
                "chain_link", "lnk",
                {"matter_id": matter_id,
                 "from_reference_id": from_reference_id,
                 "to_reference_id": to_reference_id,
                 "relation_label": relation_label,
                 "reported_only": True, "traversed_here": False,
                 "attribution_computed_here": False},
                actor, "ext_chain_link_record")

    def list_chain_links(self, matter_id, reference_id=None, actor=None):
        """Return chain link records. Action: matter_read.

        With ``reference_id``, links touching the reference in
        either direction.
        """
        self._guard_read(actor, "matter_read", "ext_chain_link_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_chain_link_read")
            links = self._list("chain_link", matter_id=matter_id)
            if reference_id is not None:
                self._get("chain_reference", reference_id, matter_id)
                links = [e for e in links
                         if e["from_reference_id"] == reference_id
                         or e["to_reference_id"] == reference_id]
            return links

    @staticmethod
    def _chain_degree(edges, reference_id):
        """(in_degree, out_degree) of a chain reference.

        Counts over the recorded link records only: in_degree is
        the number of recorded links whose target is the
        reference, out_degree the number whose source it is.

        MUTATION DRILL NOTE: this seam is the single derivation
        point for chain-reference degrees -- the batch's fresh
        negative control mutates it (swapping in/out must not
        produce the canonical degrees).
        """
        out_degree = sum(1 for e in edges
                         if e["from_reference_id"] == reference_id)
        in_degree = sum(1 for e in edges
                        if e["to_reference_id"] == reference_id)
        return in_degree, out_degree

    def chain_reference_view(self, matter_id, reference_id, actor=None):
        """Derived view of a chain reference. Action: report_read.

        In/out/total degree are computed at read from the stored
        link records by the seam ``_chain_degree``; nothing
        derived is written back onto the reference record.
        """
        self._guard_read(actor, "report_read", "ext_chain_reference_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_chain_reference_view")
            reference = self._get("chain_reference", reference_id, matter_id)
            edges = self._list("chain_link", matter_id=matter_id)
            in_degree, out_degree = self._chain_degree(edges, reference_id)
            view = dict(reference)
            view["in_degree"] = in_degree
            view["out_degree"] = out_degree
            view["degree"] = in_degree + out_degree
            view["derived_at_read"] = True
            return view

    # -- All-source fusion & lead / identity resolution ---------------
    # A lead here is an opaque reference, optionally bound to a
    # core source record. A reported link records that a caller
    # reported a relationship between a lead and another opaque
    # reference. No resolution is performed and no identity is
    # inferred (``resolved_here`` / ``inferred_here`` /
    # ``identified_here`` are False): a link exists here only
    # because someone reported it, and no record shape can hold
    # a name, an account value, or an address -- the fork's own
    # description names those as the things its product resolves;
    # this substrate holds references to them, never the values.

    def record_lead(self, matter_id, lead_ref, actor, source_id=None):
        """Record a lead. Action: search_write.

        ``source_id`` optionally binds the lead to a core source
        record in the same matter. ``lead_ref`` is opaque and
        unique in the matter.
        """
        self._guard(actor, "search_write", "ext_lead_record", matter_id)
        _non_empty(lead_ref, "lead_ref")
        with self._lock:
            self._matter(actor, matter_id, "ext_lead_record", need_open=True)
            if source_id is not None:
                self.store.get_source(matter_id, source_id, actor)
            self._check_ref_unique("lead", matter_id, "lead_ref",
                                   lead_ref, "lead_ref")
            return self._create(
                "lead", "led",
                {"matter_id": matter_id, "lead_ref": lead_ref,
                 "source_id": source_id, "resolved_here": False,
                 "identified_here": False, "status": "recorded"},
                actor, "ext_lead_record")

    def get_lead(self, matter_id, lead_id, actor=None):
        """Return one lead record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_lead_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_lead_read")
            return self._fetch("lead", lead_id, matter_id)

    def list_leads(self, matter_id, actor=None):
        """Return lead records for a matter. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_lead_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_lead_read")
            return self._list("lead", matter_id=matter_id)

    def record_reported_link(self, matter_id, lead_id, other_ref,
                             relation_label, actor):
        """Record a caller-reported link from a lead to a reference.

        Action: search_write. The link is recorded exactly as
        reported; recording it resolves and infers nothing.
        """
        self._guard(actor, "search_write", "ext_reported_link_record",
                    matter_id)
        _non_empty(other_ref, "other_ref")
        _non_empty(relation_label, "relation_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_reported_link_record",
                         need_open=True)
            self._get("lead", lead_id, matter_id)
            return self._create(
                "reported_link", "rlk",
                {"matter_id": matter_id, "lead_id": lead_id,
                 "other_ref": other_ref, "relation_label": relation_label,
                 "reported_only": True, "resolved_here": False,
                 "inferred_here": False},
                actor, "ext_reported_link_record")

    def list_reported_links(self, matter_id, lead_id=None, actor=None):
        """Return reported link records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_reported_link_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_reported_link_read")
            if lead_id is not None:
                self._get("lead", lead_id, matter_id)
            return self._list("reported_link", matter_id=matter_id,
                              lead_id=lead_id)

    def lead_view(self, matter_id, lead_id, actor=None):
        """Derived view of a lead. Action: report_read.

        The reported-link count is computed at read from the
        stored link records; the stored lead record carries no
        count, and the view resolves nothing.
        """
        self._guard_read(actor, "report_read", "ext_lead_view", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_lead_view")
            lead = self._get("lead", lead_id, matter_id)
            links = self._list("reported_link", matter_id=matter_id,
                               lead_id=lead_id)
            view = dict(lead)
            view["reported_link_count"] = len(links)
            view["derived_at_read"] = True
            return view

    # -- AI investigation models --------------------------------------
    # The records form of the model surface: an investigation
    # request record (an opaque reference, an optional model
    # label recorded verbatim, an optional lead binding) and
    # result records that hold an opaque result reference and an
    # outcome label as reported. No model runs here
    # (``inference_here`` is False), no result content is held,
    # and there is no parameter that could accept prompt text or
    # result text. The models are the fork's product; this
    # surface is the request/result registry the product's use
    # presupposes, in the same records form as the Data
    # Management untiered set's built vector-collection
    # definitions (records built, engine not claimed).

    def record_investigation_request(self, matter_id, request_ref, actor,
                                     model_label=None, lead_id=None):
        """Record an AI investigation request. Action: search_write."""
        self._guard(actor, "search_write", "ext_investigation_request",
                    matter_id)
        _non_empty(request_ref, "request_ref")
        _string_or_none(model_label, "model_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_investigation_request",
                         need_open=True)
            if lead_id is not None:
                self._get("lead", lead_id, matter_id)
            self._check_ref_unique("investigation_request", matter_id,
                                   "request_ref", request_ref, "request_ref")
            return self._create(
                "investigation_request", "air",
                {"matter_id": matter_id, "request_ref": request_ref,
                 "model_label": model_label, "lead_id": lead_id,
                 "inference_here": False, "status": "recorded"},
                actor, "ext_investigation_request")

    def get_investigation_request(self, matter_id, request_id, actor=None):
        """Return one investigation request record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_investigation_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_investigation_read")
            return self._fetch("investigation_request", request_id, matter_id)

    def list_investigation_requests(self, matter_id, lead_id=None,
                                    actor=None):
        """Return investigation request records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_investigation_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_investigation_read")
            if lead_id is not None:
                self._get("lead", lead_id, matter_id)
            return self._list("investigation_request", matter_id=matter_id,
                              lead_id=lead_id)

    def record_investigation_result(self, matter_id, request_id, result_ref,
                                    actor, outcome=None):
        """Record an investigation result as an opaque reference.

        Action: search_write. ``result_ref`` references a result
        held by the owning platform; no result content enters
        this build and no inference ran here.
        """
        self._guard(actor, "search_write", "ext_investigation_result",
                    matter_id)
        _non_empty(result_ref, "result_ref")
        _string_or_none(outcome, "outcome")
        with self._lock:
            self._matter(actor, matter_id, "ext_investigation_result",
                         need_open=True)
            self._get("investigation_request", request_id, matter_id)
            return self._create(
                "investigation_result", "ars",
                {"matter_id": matter_id, "request_id": request_id,
                 "result_ref": result_ref, "outcome": outcome,
                 "inference_here": False, "output_held": False},
                actor, "ext_investigation_result")

    def list_investigation_results(self, matter_id, request_id=None,
                                   actor=None):
        """Return investigation result records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_investigation_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_investigation_read")
            if request_id is not None:
                self._get("investigation_request", request_id, matter_id)
            return self._list("investigation_result", matter_id=matter_id,
                              request_id=request_id)

    # -- Stub-engine family: labeled reference implementation ---------
    # Operational risk-assessment tooling. Assessments and their
    # outcomes are records about assessments an external platform
    # performs: every record carries ``reference_stub: True`` and
    # a status of ``recorded_reference_only``; outcomes are
    # recorded verbatim as reported labels (the citation-treatment
    # discipline: ratings are records, scoring is an engine, and
    # no engine is built here). Nothing is assessed here
    # (``assessed_here`` is False), and no parameter or record
    # shape can hold a numeric score.

    def register_risk_assessment(self, matter_id, assessment_ref, actor,
                                 operation_id=None):
        """Register a risk-assessment reference record.

        Action: citation_write.
        """
        self._guard(actor, "citation_write", "ext_risk_assessment_register",
                    matter_id)
        _non_empty(assessment_ref, "assessment_ref")
        with self._lock:
            self._matter(actor, matter_id, "ext_risk_assessment_register",
                         need_open=True)
            if operation_id is not None:
                self._get("operation", operation_id, matter_id)
            self._check_ref_unique("risk_assessment", matter_id,
                                   "assessment_ref", assessment_ref,
                                   "assessment_ref")
            return self._create(
                "risk_assessment", "rsk",
                {"matter_id": matter_id, "assessment_ref": assessment_ref,
                 "operation_id": operation_id, "reference_stub": True,
                 "assessed_here": False, "status": "recorded_reference_only"},
                actor, "ext_risk_assessment_register")

    def get_risk_assessment(self, matter_id, assessment_id, actor=None):
        """Return one risk-assessment record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_risk_assessment_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_risk_assessment_read")
            return self._fetch("risk_assessment", assessment_id, matter_id)

    def list_risk_assessments(self, matter_id, operation_id=None, actor=None):
        """Return risk-assessment records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_risk_assessment_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_risk_assessment_read")
            if operation_id is not None:
                self._get("operation", operation_id, matter_id)
            return self._list("risk_assessment", matter_id=matter_id,
                              operation_id=operation_id)

    def record_risk_outcome(self, matter_id, assessment_id, outcome_label,
                            actor):
        """Record a risk assessment's outcome label as reported.

        Action: citation_write. The label is the assessing
        platform's report, stored verbatim; nothing is computed
        here (``computed_here`` is False) and no numeric outcome
        is accepted.
        """
        self._guard(actor, "citation_write", "ext_risk_outcome_record",
                    matter_id)
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_risk_outcome_record",
                         need_open=True)
            self._get("risk_assessment", assessment_id, matter_id)
            return self._create(
                "risk_outcome", "rko",
                {"matter_id": matter_id, "assessment_id": assessment_id,
                 "outcome_label": outcome_label, "reference_stub": True,
                 "assessed_here": False, "computed_here": False},
                actor, "ext_risk_outcome_record")

    def list_risk_outcomes(self, matter_id, assessment_id=None, actor=None):
        """Return risk outcome records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_risk_outcome_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_risk_outcome_read")
            if assessment_id is not None:
                self._get("risk_assessment", assessment_id, matter_id)
            return self._list("risk_outcome", matter_id=matter_id,
                              assessment_id=assessment_id)
