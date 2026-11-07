"""Final GAPS batch extensions for the Storage L2 singleton.

Clean-room, standard-library-only extensions for the 10 open
entries of the singleton's GAPS.md section (see ``BATCH.md`` in
the group directory for the per-entry disposition). This module
is a wrapper around :class:`StorageStore`; every core module is
untouched and byte-identical to the shipped singleton build.

**The founding disciplines bind absolutely, here as in the
core.** The core holds metadata records only -- no field on any
core shape can hold a subject, a body, or any content -- and
neither can any shape here. This module stores no archived
payload, performs no cryptography of any kind (PLATFORM-LAYER.md
decisions 2 and 3: no build claims a validated module, and
encryption at rest / in transit is a deployment-layer property),
deletes nothing (decision 4: disposition enforcement is the
embedding organization's records schedule, executed at the
deployment layer), connects to nothing, and executes nothing.
Custodians, keys, payloads, and external systems are named only
by opaque references and labels held as data. Methods accept
only their named parameters, so a caller cannot smuggle a
forbidden field into a record (pinned by tests: a ``content=``,
``key_material=``, or ``query_text=`` keyword raises
``TypeError``).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form -- records plus deterministic derivations over
this group's OWN records (core records and extension records):

- The payload storage plane lands as payload *custody* records
  bound to core message records: a custodian reference, a
  reported byte count, and a checksum reference. The view
  derives whether the reported count matches the core record's
  recorded size. No payload byte is held, so
  ``content_held_here`` is False on every record.
- The ingest pipeline lands as ingest-batch records whose counts
  are stored **as reported** by the external capture system
  (``captured_here`` False); recording a batch changes no core
  archive record (pinned by test).
- The encryption engine lands as encryption *profile* records
  extending the core's key-custody records: an algorithm label
  and the fork's own stated validation posture, held as data and
  recorded as the fork's (``validation_transfers`` False,
  PLATFORM-LAYER.md decision 2). ``encrypted_here`` is False;
  no cryptographic operation exists anywhere in this module.
- Retrieval delivery lands as delivery records and export
  manifests: files and transports are *described*, never
  produced or performed (``delivered_here`` /
  ``files_produced_here`` False, receipts carry
  ``reference_transport: True``); a delivery view derives the
  linked core retrieval's current status at read.
- Policy enforcement execution lands as enforcement *decision*
  records gated by a derivation over the core message's derived
  retention state through the single seam
  :meth:`StorageExtensions._derive_enforcement_eligibility`
  (``executed_here`` False); recording a decision changes no
  core record (pinned by test).
- Disposition execution lands as disposition *outcome* records:
  the deployment layer's reported outcome of destroying the
  payload, gated on the core disposition record's existence,
  with the current outcome derived at read (``destroyed_here``
  False -- this build holds no payloads to destroy).
- Stub-engine entries ship as labeled reference implementations:
  every record carries ``reference_stub: True`` -- the full-text
  index reference (no query surface of any kind exists here;
  ``index_built_here`` False), key-management hardware inventory
  records (``key_material_held_here`` False), supervision
  console definitions and routing assignments held as data
  (``executed_here`` / ``routed_here`` False; reviewer decisions
  stay in the core review records, recorded verbatim there),
  and connector sync receipts (``connected_here`` False,
  ``reference_transport: True``).

Doctrines carried from the core: derived-never-stored for every
computed value (payload size match, retrieval status, manifest
file count, enforcement eligibility and current state,
disposition outcome -- each through a single derivation seam);
append-only audit on the core store's log with ``ext_``-prefixed
actions for every successful mutation, and denied write attempts
recorded with a ``:denied`` suffix; RBAC via
:mod:`storage.access` with the core's existing actions, enforced
before any state change or id allocation, so a failed operation
consumes no id and changes nothing; sizes and counts are
integers only -- booleans and floats are rejected at the
boundary, as in the core.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import ENFORCEMENT_ACTIONS

DISPOSITION_OUTCOME_LABELS = (
    "reported_destroyed",
    "reported_failed",
    "reported_pending",
)
CONNECTOR_DIRECTIONS = ("inbound", "outbound", "bidirectional")

# Keys that may never appear on any extension record or view: the
# founding discipline is that no shape here can hold content, key
# material, a free-text query, or a computed score. The test suite
# scans every record and view recursively against this set.
FORBIDDEN_KEYS = frozenset({
    "content", "body", "subject", "payload", "attachment",
    "message_text", "extracted_text", "key_material",
    "private_key", "secret", "password",
    "query", "query_text", "search_text", "full_text",
    "score", "rating", "rank",
})


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _parse_moment(value, field):
    """Parse an ISO date or datetime into an aware datetime
    (the core store's convention, restated for the ``at`` /
    ``now`` parameters of the gated and derived surfaces)."""
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
            raise ValidationError(
                "%s is not an ISO date or datetime: %r" % (field, value))
    else:
        raise ValidationError(
            "%s must be an ISO date or datetime string" % field)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _count(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(
            "%s must be a non-negative integer" % field)
    return value


def _id_num(record_id):
    return int(record_id.rsplit("-", 1)[1])


class StorageExtensions:
    """Final-batch extension surface wrapping a core
    :class:`StorageStore`. Holds only extension records; every
    core record it names is resolved through the core store's own
    read API, so the core's permission checks and derivations
    govern throughout."""

    def __init__(self, store):
        self.store = store
        self._payload_custodies = {}
        self._ingest_batches = {}
        self._index_references = {}
        self._encryption_profiles = {}
        self._key_hardware = {}
        self._deliveries = {}
        self._export_manifests = {}
        self._console_definitions = {}
        self._console_assignments = {}
        self._enforcement_decisions = {}
        self._disposition_outcomes = {}
        self._connector_syncs = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    def _guard(self, actor, rbac_action, audit_action):
        """Enforce a write permission before any state change.

        Mirrors the core convention (a User-like actor is checked
        via :func:`storage.access.require`; a plain string carries
        identity but no role). A denied attempt is recorded on the
        audit log with a ``:denied`` suffix before the error
        propagates; a missing actor is denied outright.
        """
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (rbac_action,))
        if hasattr(actor, "role"):
            try:
                require(actor, rbac_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": rbac_action})
                raise

    @staticmethod
    def _maybe_require(actor, rbac_action):
        if actor is not None and hasattr(actor, "role"):
            require(actor, rbac_action)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _create(self, table, prefix, fields, actor, audit_action):
        record = {"id": self._next_id(prefix)}
        record.update(fields)
        record["created_by"] = actor_name(actor)
        record["created_utc"] = _utc_now()
        table[record["id"]] = record
        self._audit(actor, audit_action, record["id"])
        return copy.deepcopy(record)

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    # Core-record resolution, always through the core's read API.

    def _core_message(self, actor, message_id, now=None):
        return self.store.get_message(actor, message_id, now=now)

    def _core_custody(self, actor, custody_id):
        for custody in self.store.list_custodies(actor):
            if custody["id"] == custody_id:
                return custody
        raise NotFoundError("no such key custody record: %r" % (custody_id,))

    def _core_integration(self, actor, integration_id):
        for integration in self.store.list_integrations(actor):
            if integration["id"] == integration_id:
                return integration
        raise NotFoundError(
            "no such integration record: %r" % (integration_id,))

    def _core_retrieval(self, actor, retrieval_id):
        for retrieval in self.store.list_retrievals(actor):
            if retrieval["id"] == retrieval_id:
                return retrieval
        raise NotFoundError("no such retrieval: %r" % (retrieval_id,))

    def _core_disposition(self, actor, disposition_id):
        for disposition in self.store.list_dispositions(actor):
            if disposition["id"] == disposition_id:
                return disposition
        raise NotFoundError(
            "no such disposition record: %r" % (disposition_id,))

    def _core_review(self, actor, review_id):
        for review in self.store.list_reviews(actor):
            if review["id"] == review_id:
                return review
        raise NotFoundError("no such review: %r" % (review_id,))

    # -- archived payload storage plane (idx 725) ----------------------
    # Payload custody records: the custody accounting of the
    # payload plane, bound to core message records. The plane
    # itself -- byte storage -- is not here and cannot be: this
    # substrate holds no content, by founding decision.

    def record_payload_custody(self, actor, message_id, custodian_ref,
                               reported_size_bytes, checksum_ref):
        """Record payload custody for one archived message: the
        custodian (opaque reference) reported to hold the archived
        payload bytes, the byte count as reported by that
        custodian, and an opaque checksum reference. Action:
        custody. Ids: pay-{n}. One custody record per message.
        Nothing is stored here but the accounting: the record
        carries ``content_held_here: False`` and no field that
        could hold the payload itself."""
        self._guard(actor, "custody", "ext_payload_custody_record")
        message = self._core_message(actor, message_id)
        _text(custodian_ref, "custodian_ref")
        _count(reported_size_bytes, "reported_size_bytes")
        _text(checksum_ref, "checksum_ref")
        with self._lock:
            for existing in self._payload_custodies.values():
                if existing["message_id"] == message_id:
                    raise ValidationError(
                        "message %s already has a payload custody "
                        "record: %s" % (message_id, existing["id"]))
            return self._create(
                self._payload_custodies, "pay-",
                {"message_id": message_id,
                 "collection_id": message["collection_id"],
                 "custodian_ref": custodian_ref,
                 "reported_size_bytes": reported_size_bytes,
                 "checksum_ref": checksum_ref,
                 "content_held_here": False},
                actor, "ext_payload_custody_record")

    def payload_custody_view(self, actor, custody_id):
        """One payload custody record plus its derived size check:
        ``recorded_size_bytes`` is the core message record's
        recorded size, and ``size_matches_record`` derives at read
        whether the custodian's reported count equals it. Neither
        derived key is stored."""
        self._maybe_require(actor, "read")
        record = self._get(self._payload_custodies, custody_id,
                           "payload custody record")
        message = self._core_message(actor, record["message_id"])
        view = copy.deepcopy(record)
        view["recorded_size_bytes"] = message["size_bytes"]
        view["size_matches_record"] = (
            record["reported_size_bytes"] == message["size_bytes"])
        return view

    def list_payload_custodies(self, actor, message_id=None):
        self._maybe_require(actor, "read")
        if message_id is not None:
            self._core_message(actor, message_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._payload_custodies.values())
                if message_id is None or r["message_id"] == message_id]

    # -- archive ingest pipeline (idx 726) ------------------------------

    def record_ingest_batch(self, actor, collection_id, integration_id,
                            source_label, reported_message_count,
                            reported_byte_total):
        """Record one ingest batch as reported by the external
        capture system (journaling or connector based) behind a
        registered mail-platform integration. Action: archive.
        Ids: ing-{n}. The counts are stored **as reported** --
        ``captured_here`` is False, and recording a batch archives
        nothing: no core message record is created or changed
        (pinned by test)."""
        self._guard(actor, "archive", "ext_ingest_batch_record")
        self.store.get_collection(actor, collection_id)
        integration = self._core_integration(actor, integration_id)
        if integration["kind"] != "mail_platform":
            raise ValidationError(
                "integration %s is a %r integration; ingest batches "
                "are recorded against mail-platform integrations"
                % (integration_id, integration["kind"]))
        _text(source_label, "source_label")
        _count(reported_message_count, "reported_message_count")
        _count(reported_byte_total, "reported_byte_total")
        with self._lock:
            return self._create(
                self._ingest_batches, "ing-",
                {"collection_id": collection_id,
                 "integration_id": integration_id,
                 "source_label": source_label,
                 "reported_message_count": reported_message_count,
                 "reported_byte_total": reported_byte_total,
                 "captured_here": False},
                actor, "ext_ingest_batch_record")

    def list_ingest_batches(self, actor, collection_id=None):
        self._maybe_require(actor, "read")
        if collection_id is not None:
            self.store.get_collection(actor, collection_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._ingest_batches.values())
                if collection_id is None
                or r["collection_id"] == collection_id]

    # -- full-text content indexing & search (idx 727, stub) -----------

    def record_index_reference(self, actor, collection_id, engine_label,
                               reported_document_count):
        """Record a reference to an external full-text index over
        a collection: the engine's label and its document count as
        reported. Action: discover. Ids: idx-{n}. Labeled
        reference implementation (``reference_stub: True``): no
        index is built here (``index_built_here`` False) -- this
        substrate holds no content to index -- and **no search or
        query surface of any kind exists on this module**: there
        is no parameter, here or anywhere in the extension, that
        accepts query text."""
        self._guard(actor, "discover", "ext_index_reference_record")
        self.store.get_collection(actor, collection_id)
        _text(engine_label, "engine_label")
        _count(reported_document_count, "reported_document_count")
        with self._lock:
            return self._create(
                self._index_references, "idx-",
                {"collection_id": collection_id,
                 "engine_label": engine_label,
                 "reported_document_count": reported_document_count,
                 "reference_stub": True,
                 "index_built_here": False},
                actor, "ext_index_reference_record")

    def list_index_references(self, actor, collection_id=None):
        self._maybe_require(actor, "read")
        if collection_id is not None:
            self.store.get_collection(actor, collection_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._index_references.values())
                if collection_id is None
                or r["collection_id"] == collection_id]

    # -- encryption & decryption engine (idx 728) ------------------------
    # Encryption profile records extending the core's key-custody
    # records. Labels as data; the fork's posture stays the fork's.

    def record_encryption_profile(self, actor, custody_id,
                                  algorithm_label, validation_label):
        """Record an encryption profile for one core key-custody
        record: the algorithm named by an opaque label, and the
        fork's own stated validation posture, recorded verbatim
        **as the fork's** -- per PLATFORM-LAYER.md decision 2 a
        fork's validation posture is recorded as the fork's and
        does not transfer (``validation_transfers`` False). Action:
        custody. Ids: enc-{n}. One profile per custody record.
        ``encrypted_here`` is False: this build performs no
        cryptography, and no cryptographic operation or key
        material exists anywhere in this module."""
        self._guard(actor, "custody", "ext_encryption_profile_record")
        custody = self._core_custody(actor, custody_id)
        _text(algorithm_label, "algorithm_label")
        _text(validation_label, "validation_label")
        with self._lock:
            for existing in self._encryption_profiles.values():
                if existing["custody_id"] == custody_id:
                    raise ValidationError(
                        "custody record %s already has an encryption "
                        "profile: %s" % (custody_id, existing["id"]))
            return self._create(
                self._encryption_profiles, "enc-",
                {"custody_id": custody_id,
                 "collection_id": custody["collection_id"],
                 "algorithm_label": algorithm_label,
                 "validation_label": validation_label,
                 "validation_transfers": False,
                 "encrypted_here": False},
                actor, "ext_encryption_profile_record")

    def list_encryption_profiles(self, actor, custody_id=None):
        self._maybe_require(actor, "read")
        if custody_id is not None:
            self._core_custody(actor, custody_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._encryption_profiles.values())
                if custody_id is None or r["custody_id"] == custody_id]

    # -- key management hardware & premise equipment (idx 729, stub) -----

    def record_key_hardware(self, actor, custody_id, equipment_label,
                            location_label):
        """Record one item of key-management premise equipment as
        inventory data bound to a core custody record: what the
        equipment is called and where it sits, by labels. Action:
        custody. Ids: khw-{n}. Labeled reference implementation
        (``reference_stub: True``): the equipment is the
        custodian's, in the customer environment; this record is
        its inventory landing form. ``key_material_held_here`` is
        False -- no key material exists in this substrate."""
        self._guard(actor, "custody", "ext_key_hardware_record")
        custody = self._core_custody(actor, custody_id)
        _text(equipment_label, "equipment_label")
        _text(location_label, "location_label")
        with self._lock:
            return self._create(
                self._key_hardware, "khw-",
                {"custody_id": custody_id,
                 "collection_id": custody["collection_id"],
                 "equipment_label": equipment_label,
                 "location_label": location_label,
                 "reference_stub": True,
                 "key_material_held_here": False},
                actor, "ext_key_hardware_record")

    def list_key_hardware(self, actor, custody_id=None):
        self._maybe_require(actor, "read")
        if custody_id is not None:
            self._core_custody(actor, custody_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._key_hardware.values())
                if custody_id is None or r["custody_id"] == custody_id]

    # -- retrieval delivery transport & export files (idx 730) -----------

    def record_delivery(self, actor, retrieval_id, transport_label):
        """Record the delivery transport for one core retrieval:
        the transport named by label, as a reference receipt.
        Action: retrieve. Ids: dlv-{n}. One delivery record per
        retrieval. The file is described, never produced, and the
        message is never placed anywhere: ``delivered_here`` is
        False and the record carries ``reference_transport:
        True``. Whether the core retrieval has completed is a
        derivation, exposed by :meth:`delivery_view`."""
        self._guard(actor, "retrieve", "ext_delivery_record")
        retrieval = self._core_retrieval(actor, retrieval_id)
        _text(transport_label, "transport_label")
        with self._lock:
            for existing in self._deliveries.values():
                if existing["retrieval_id"] == retrieval_id:
                    raise ValidationError(
                        "retrieval %s already has a delivery record: "
                        "%s" % (retrieval_id, existing["id"]))
            return self._create(
                self._deliveries, "dlv-",
                {"retrieval_id": retrieval_id,
                 "message_id": retrieval["message_id"],
                 "transport_label": transport_label,
                 "reference_transport": True,
                 "delivered_here": False},
                actor, "ext_delivery_record")

    def delivery_view(self, actor, delivery_id):
        """One delivery record plus ``retrieval_status`` derived
        at read from the linked core retrieval record. The derived
        key is never stored."""
        self._maybe_require(actor, "read")
        record = self._get(self._deliveries, delivery_id,
                           "delivery record")
        retrieval = self._core_retrieval(actor, record["retrieval_id"])
        view = copy.deepcopy(record)
        view["retrieval_status"] = retrieval["status"]
        return view

    def list_deliveries(self, actor, retrieval_id=None):
        self._maybe_require(actor, "read")
        if retrieval_id is not None:
            self._core_retrieval(actor, retrieval_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._deliveries.values())
                if retrieval_id is None
                or r["retrieval_id"] == retrieval_id]

    def record_export_manifest(self, actor, collection_id, format_label,
                               message_ids):
        """Record an export manifest for a collection: the format
        named by label and the archived messages the export would
        contain, each resolved against the core records of that
        collection. Action: retrieve. Ids: exp-{n}. The manifest
        *describes* the export file; no file is produced here
        (``files_produced_here`` False, ``reference_transport``
        True). The file count is derived in the view, never
        stored."""
        self._guard(actor, "retrieve", "ext_export_manifest_record")
        self.store.get_collection(actor, collection_id)
        _text(format_label, "format_label")
        if not isinstance(message_ids, (list, tuple)) \
                or not message_ids:
            raise ValidationError(
                "message_ids must be a non-empty list of message ids")
        ids = []
        for message_id in message_ids:
            message = self._core_message(actor, message_id)
            if message["collection_id"] != collection_id:
                raise ValidationError(
                    "message %s does not belong to collection %s"
                    % (message_id, collection_id))
            ids.append(message_id)
        with self._lock:
            return self._create(
                self._export_manifests, "exp-",
                {"collection_id": collection_id,
                 "format_label": format_label,
                 "message_ids": ids,
                 "reference_transport": True,
                 "files_produced_here": False},
                actor, "ext_export_manifest_record")

    def export_manifest_view(self, actor, manifest_id):
        """One export manifest plus ``file_count`` derived at read
        from the manifest's own message list (one described file
        per message). The derived key is never stored."""
        self._maybe_require(actor, "read")
        record = self._get(self._export_manifests, manifest_id,
                           "export manifest")
        view = copy.deepcopy(record)
        view["file_count"] = len(record["message_ids"])
        return view

    def list_export_manifests(self, actor, collection_id=None):
        self._maybe_require(actor, "read")
        if collection_id is not None:
            self.store.get_collection(actor, collection_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._export_manifests.values())
                if collection_id is None
                or r["collection_id"] == collection_id]

    # -- supervision review console & workflow (idx 731, stub) -----------

    def record_console_definition(self, actor, collection_id,
                                  definition_label, reviewer_refs):
        """Record a supervision console / workflow definition as
        data: a label and the reviewer references the console
        would route to. Action: supervise. Ids: wfd-{n}. Labeled
        reference implementation (``reference_stub: True``):
        definitions are held, never executed (``executed_here``
        False) -- the house rule that registries hold definitions
        only. Reviewer decisions themselves live in the core
        review records, recorded verbatim there; nothing here
        samples, queues, or routes."""
        self._guard(actor, "supervise", "ext_console_definition_record")
        self.store.get_collection(actor, collection_id)
        _text(definition_label, "definition_label")
        if not isinstance(reviewer_refs, (list, tuple)) \
                or not reviewer_refs:
            raise ValidationError(
                "reviewer_refs must be a non-empty list of references")
        refs = []
        for ref in reviewer_refs:
            _text(ref, "reviewer_ref")
            refs.append(ref)
        with self._lock:
            return self._create(
                self._console_definitions, "wfd-",
                {"collection_id": collection_id,
                 "definition_label": definition_label,
                 "reviewer_refs": refs,
                 "reference_stub": True,
                 "executed_here": False},
                actor, "ext_console_definition_record")

    def record_console_assignment(self, actor, definition_id, review_id):
        """Record a console routing assignment as data: a core
        review bound to a console definition and to the reviewer
        reference the definition names. Action: supervise. Ids:
        wfa-{n}. Labeled reference implementation
        (``reference_stub: True``, ``routed_here`` False):
        recording an assignment routes nothing and changes no
        core review record (pinned by test)."""
        self._guard(actor, "supervise", "ext_console_assignment_record")
        definition = self._get(self._console_definitions, definition_id,
                               "console definition")
        review = self._core_review(actor, review_id)
        if review["reviewer_ref"] not in definition["reviewer_refs"]:
            raise ValidationError(
                "review %s names reviewer %r, whom definition %s "
                "does not name" % (review_id, review["reviewer_ref"],
                                   definition_id))
        with self._lock:
            return self._create(
                self._console_assignments, "wfa-",
                {"definition_id": definition_id,
                 "review_id": review_id,
                 "message_id": review["message_id"],
                 "reviewer_ref": review["reviewer_ref"],
                 "reference_stub": True,
                 "routed_here": False},
                actor, "ext_console_assignment_record")

    def list_console_definitions(self, actor, collection_id=None):
        self._maybe_require(actor, "read")
        if collection_id is not None:
            self.store.get_collection(actor, collection_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._console_definitions.values())
                if collection_id is None
                or r["collection_id"] == collection_id]

    def list_console_assignments(self, actor, definition_id=None):
        self._maybe_require(actor, "read")
        if definition_id is not None:
            self._get(self._console_definitions, definition_id,
                      "console definition")
        return [copy.deepcopy(r) for r in
                self._sorted(self._console_assignments.values())
                if definition_id is None
                or r["definition_id"] == definition_id]

    # -- policy enforcement execution (idx 732) ---------------------------
    # Enforcement decision records, gated by the eligibility seam.

    @staticmethod
    def _derive_enforcement_eligibility(retention_state):
        """Enforcement-eligibility seam: an enforcement decision
        may be recorded for a message in any derived retention
        state except ``disposed`` -- once disposition has been
        recorded there is nothing left in this substrate for a
        decision to concern. Pure function over the core's derived
        state string; the fresh negative control mutates it (see
        tests/README.md)."""
        return retention_state != "disposed"

    def record_enforcement_decision(self, actor, message_id, action,
                                    policy_ref, at=None):
        """Record an enforcement decision for an archived message:
        an action from the core's enforcement vocabulary, taken
        under a stated policy reference. Action: enforce. Ids:
        dec-{n}. The decision is **gated**: the message's derived
        retention state at the decision moment is computed through
        the core's seam, and a decision for a ``disposed`` message
        is refused whole via
        :meth:`_derive_enforcement_eligibility`. The record states
        that a decision was recorded; executing it in a connected
        system is the platform layer's (``executed_here`` False),
        and recording one changes no core record (pinned by
        test)."""
        self._guard(actor, "enforce", "ext_enforcement_decision_record")
        if action not in ENFORCEMENT_ACTIONS:
            raise ValidationError(
                "unknown enforcement action: %r" % (action,))
        _text(policy_ref, "policy_ref")
        moment = _parse_moment(at, "at") if at is not None else None
        view = self._core_message(actor, message_id, now=moment)
        if not self._derive_enforcement_eligibility(
                view["retention_state"]):
            raise ValidationError(
                "message %s is 'disposed'; enforcement decisions "
                "are recorded only for messages not yet disposed"
                % (message_id,))
        with self._lock:
            return self._create(
                self._enforcement_decisions, "dec-",
                {"message_id": message_id,
                 "action": action,
                 "policy_ref": policy_ref,
                 "executed_here": False},
                actor, "ext_enforcement_decision_record")

    def enforcement_decision_view(self, actor, decision_id, now=None):
        """One enforcement decision record plus the message's
        *current* derived retention state and whether a decision
        would still be recordable for it, both derived at read
        through the core's seam and this module's eligibility
        seam. Neither derived key is stored."""
        self._maybe_require(actor, "read")
        record = self._get(self._enforcement_decisions, decision_id,
                           "enforcement decision")
        moment = _parse_moment(now, "now") if now is not None else None
        view = self._core_message(actor, record["message_id"],
                                  now=moment)
        out = copy.deepcopy(record)
        out["current_retention_state"] = view["retention_state"]
        out["currently_actionable"] = \
            self._derive_enforcement_eligibility(
                view["retention_state"])
        return out

    def list_enforcement_decisions(self, actor, message_id=None):
        self._maybe_require(actor, "read")
        if message_id is not None:
            self._core_message(actor, message_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._enforcement_decisions.values())
                if message_id is None
                or r["message_id"] == message_id]

    # -- disposition execution (idx 734) ----------------------------------
    # Disposition outcome records: the deployment layer's reported
    # outcome for the core's gated disposition record.

    @staticmethod
    def _current_outcome_label(outcome_records):
        """Disposition-outcome derivation seam: the current
        outcome is the latest recorded outcome record's label, or
        ``unreported`` when no outcome has been recorded. Pure
        function over this module's own records, in creation
        order; the current outcome is never stored anywhere."""
        if not outcome_records:
            return "unreported"
        return outcome_records[-1]["outcome_label"]

    def record_disposition_outcome(self, actor, disposition_id,
                                   outcome_label):
        """Record the reported outcome of a core disposition: what
        the deployment layer reports happened to the payload when
        it executed the disposition the core's gate allowed.
        Action: archive. Ids: dout-{n}. The label is stored as
        reported from the ``reported_*`` vocabulary.
        ``destroyed_here`` is False: this build holds no payloads
        to destroy (PLATFORM-LAYER.md decision 4 -- disposition
        of the payload is executed at the deployment layer, and
        its outcome lands here as a record)."""
        self._guard(actor, "archive", "ext_disposition_outcome_record")
        disposition = self._core_disposition(actor, disposition_id)
        if outcome_label not in DISPOSITION_OUTCOME_LABELS:
            raise ValidationError(
                "unknown disposition outcome label: %r"
                % (outcome_label,))
        with self._lock:
            return self._create(
                self._disposition_outcomes, "dout-",
                {"disposition_id": disposition_id,
                 "message_id": disposition["message_id"],
                 "outcome_label": outcome_label,
                 "destroyed_here": False},
                actor, "ext_disposition_outcome_record")

    def disposition_outcome_view(self, actor, disposition_id):
        """The disposition-outcome state for one core disposition:
        the outcome records' count and the current outcome label,
        derived at read through
        :meth:`_current_outcome_label`. No outcome state is
        stored on the core disposition record (which the core
        keeps byte-identical) or anywhere else."""
        self._maybe_require(actor, "read")
        disposition = self._core_disposition(actor, disposition_id)
        outcomes = [r for r in
                    self._sorted(self._disposition_outcomes.values())
                    if r["disposition_id"] == disposition_id]
        return {
            "disposition_id": disposition_id,
            "message_id": disposition["message_id"],
            "outcome_count": len(outcomes),
            "current_outcome_label":
                self._current_outcome_label(outcomes),
            "destroyed_here": False,
        }

    def list_disposition_outcomes(self, actor, disposition_id=None):
        self._maybe_require(actor, "read")
        if disposition_id is not None:
            self._core_disposition(actor, disposition_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._disposition_outcomes.values())
                if disposition_id is None
                or r["disposition_id"] == disposition_id]

    # -- mail platform & directory connectors (idx 733, stub) -------------

    def record_connector_sync(self, actor, integration_id, direction_label,
                              reported_synced_count):
        """Record a connector sync receipt for a registered
        integration: the direction and the synced count, stored as
        reported by the external connector. Action: register.
        Ids: syn-{n}. Labeled reference implementation
        (``reference_stub: True``, ``reference_transport: True``):
        ``connected_here`` is False -- registering or syncing
        against this substrate opens no connection, authenticates
        no one (identity stays with the embedding organization,
        PLATFORM-LAYER.md decision 1), and moves no message;
        recording a receipt changes no core record (pinned by
        test)."""
        self._guard(actor, "register", "ext_connector_sync_record")
        integration = self._core_integration(actor, integration_id)
        if direction_label not in CONNECTOR_DIRECTIONS:
            raise ValidationError(
                "unknown connector direction: %r" % (direction_label,))
        _count(reported_synced_count, "reported_synced_count")
        with self._lock:
            return self._create(
                self._connector_syncs, "syn-",
                {"integration_id": integration_id,
                 "org_id": integration["org_id"],
                 "kind": integration["kind"],
                 "direction_label": direction_label,
                 "reported_synced_count": reported_synced_count,
                 "reference_stub": True,
                 "reference_transport": True,
                 "connected_here": False},
                actor, "ext_connector_sync_record")

    def list_connector_syncs(self, actor, integration_id=None):
        self._maybe_require(actor, "read")
        if integration_id is not None:
            self._core_integration(actor, integration_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._connector_syncs.values())
                if integration_id is None
                or r["integration_id"] == integration_id]
