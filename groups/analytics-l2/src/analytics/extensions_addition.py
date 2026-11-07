"""Final GAPS batch additions for the Analytics L2 merged build.

Second batch unit in this group directory: clean-room,
standard-library-only records extensions for the 4 gap entries the
remainder addition fork (NetComm / Beacon) registered from its own
service catalogue (see ``ADDENDUM.md`` section 5 and
``BATCH-ADDITION.md`` in the group directory). The first batch
unit's module is ``extensions.py``; this module is separate and
every existing module, that one included, is untouched.

Design, following the group's doctrines and the first unit's forms:

- This module is a second wrapper around :class:`DatasetStore`;
  the core modules are untouched (byte-identical). It keeps its own
  record collections and reads nothing from the core except the
  audit log it writes to.
- RBAC goes through :mod:`analytics.access` exactly as the core
  and the first extension module enforce it: each operation maps
  onto an existing core action (record creation/registration ->
  ``ingest``; derivations and views -> ``query``), checked *before*
  any state change or id allocation for User-like actors. Denied
  attempts are recorded on the core audit log under this unit's
  own ``exta_`` action prefix (distinct from the first unit's
  ``ext_``), and every successful mutation as ``exta_<action>``.
- Derived values are derived at read and never stored: run
  rollups and reported-count totals are computed from the recorded
  records at view time; stored records carry no derived key, and
  tests pin that. Every total over reported counts is a sum of
  *reported* values, labeled as such -- nothing here measures
  anything.
- Nothing here executes an automation, signs a document, runs a
  workflow, or ships a client. The two engine-substance entries
  (digital signature, e-workflow tooling) ship as labeled
  reference implementations: their records carry
  ``reference_stub: True``.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


# -- vocabularies -----------------------------------------------------

SERVICE_TOOL_DOMAINS = ("hr", "finance", "property_management")
KNOWN_SERVICE_TOOL_DOMAINS = frozenset(SERVICE_TOOL_DOMAINS)
SERVICE_RUN_OUTCOMES = ("completed", "failed", "partial")
KNOWN_SERVICE_RUN_OUTCOMES = frozenset(SERVICE_RUN_OUTCOMES)

SIGNATURE_STATUSES = ("signed", "declined", "expired", "pending")
KNOWN_SIGNATURE_STATUSES = frozenset(SIGNATURE_STATUSES)
SHA256_PATTERN = re.compile(r"[0-9a-fA-F]{64}")

WORKFLOW_RUN_OUTCOMES = ("completed", "failed", "cancelled")
KNOWN_WORKFLOW_RUN_OUTCOMES = frozenset(WORKFLOW_RUN_OUTCOMES)

CLIENT_PLATFORMS = ("ios", "android", "mobile_web")
KNOWN_CLIENT_PLATFORMS = frozenset(CLIENT_PLATFORMS)
CLIENT_CAPABILITIES = (
    "dataset_query",
    "dataset_export",
    "dashboard_view",
    "report_view",
)
KNOWN_CLIENT_CAPABILITIES = frozenset(CLIENT_CAPABILITIES)


# -- shared validators ---------------------------------------------------


def _require_text(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_choice(value, known, what):
    if value not in known:
        raise ValidationError(
            "unknown %s: %r (expected one of %s)"
            % (what, value, ", ".join(sorted(known)))
        )
    return value


def _validate_count(value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


def _validate_sha256(value, what):
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise ValidationError("%s must be a SHA-256 hex digest" % (what,))
    return value


class AnalyticsExtensionsAddition:
    """Records extension surface for the addition fork's catalogue gaps."""

    def __init__(self, store):
        self.store = store
        self._lock = threading.RLock()
        self._counters = {}
        self._service_tools = {}
        self._service_tool_runs = {}
        self._signature_requests = {}
        self._signature_events = {}
        self._workflow_refs = {}
        self._workflow_runs = {}
        self._mobile_clients = {}
        self._mobile_client_ids_by_ref = {}
        self._client_capabilities = {}
        self._client_usage = {}

    # -- plumbing ------------------------------------------------------

    @property
    def _audit(self):
        return getattr(self.store, "audit", None)

    def _record(self, actor, action, target, details=None):
        audit = self._audit
        if audit is not None:
            audit.record(actor_name(actor), action, target, details=details)

    def _guard(self, actor, core_action, ext_action, target=None):
        """Enforce RBAC for User-like actors, auditing denials.

        Mirrors the core convention: plain-string actors carry
        identity but no role, so there is nothing to enforce
        against; User-like actors are checked through the core
        permission matrix before any state change or id allocation.
        """
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, core_action)
            except PermissionDenied:
                self._record(actor, ext_action + ":denied", target)
                raise

    def _next_id(self, prefix):
        """Allocate the next sequential id. Call only after validation."""
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s-%d" % (prefix, self._counters[prefix])

    @staticmethod
    def _get(collection, record_id, what):
        record = collection.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return copy.deepcopy(record)

    # -- Automated back-office service tools ------------------------------

    def register_service_tool(self, name, domain, actor):
        """Register one of the catalogue's back-office tools as data.

        The registry records which automated tools the fork's
        catalogue names (HR, finance, property management) and the
        automation runs reported for them. The automation itself
        executes on the back-office systems, never here: run
        records are recorded as reported and carry
        ``executed_here: False``.
        """
        self._guard(actor, "ingest", "exta_register_service_tool")
        _require_text(name, "service tool name")
        _validate_choice(domain, KNOWN_SERVICE_TOOL_DOMAINS,
                         "service tool domain")
        with self._lock:
            tool_id = self._next_id("bto")
            record = {
                "id": tool_id,
                "name": name,
                "domain": domain,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._service_tools[tool_id] = record
            self._record(actor, "exta_register_service_tool", tool_id,
                         details={"domain": domain})
            return copy.deepcopy(record)

    def record_service_tool_run(self, tool_id, outcome, actor,
                                reported_items=None, note=None):
        """Record an automation run for a registered tool, as reported.

        The outcome label and the item count are the external
        tool's own report, stored verbatim; the build executed
        nothing (``executed_here`` is False on every run record).
        """
        self._guard(actor, "ingest", "exta_record_service_tool_run", tool_id)
        self._get(self._service_tools, tool_id, "service tool")
        _validate_choice(outcome, KNOWN_SERVICE_RUN_OUTCOMES,
                         "service run outcome")
        if reported_items is not None:
            _validate_count(reported_items, "reported_items")
        if note is not None:
            _require_text(note, "run note")
        with self._lock:
            run_id = self._next_id("btr")
            record = {
                "id": run_id,
                "tool_id": tool_id,
                "outcome": outcome,
                "reported_items": reported_items,
                "note": note,
                "reported": True,
                "executed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._service_tool_runs[run_id] = record
            self._record(actor, "exta_record_service_tool_run", tool_id,
                         details={"outcome": outcome})
            return copy.deepcopy(record)

    def service_tool_view(self, tool_id, actor):
        """Tool record plus run rollup derived at read.

        ``reported_items_total`` is a sum of the runs' *reported*
        item counts, derived here -- it is not a measurement of
        anything the build did.
        """
        self._guard(actor, "query", "exta_service_tool_view", tool_id)
        record = self._get(self._service_tools, tool_id, "service tool")
        with self._lock:
            runs = [copy.deepcopy(r) for r in self._service_tool_runs.values()
                    if r["tool_id"] == tool_id]
        by_outcome = {}
        for run in runs:
            by_outcome[run["outcome"]] = by_outcome.get(run["outcome"], 0) + 1
        record["runs"] = runs
        record["run_count"] = len(runs)
        record["runs_by_outcome"] = by_outcome
        record["reported_items_total"] = sum(
            r["reported_items"] for r in runs
            if r["reported_items"] is not None)
        record["last_outcome"] = runs[-1]["outcome"] if runs else None
        return record

    def get_service_tool(self, tool_id, actor):
        """The stored tool record (registration only, no rollup)."""
        self._guard(actor, "query", "exta_get_service_tool", tool_id)
        return self._get(self._service_tools, tool_id, "service tool")

    # -- Digital signature engine (reference implementation) ---------------

    def record_signature_request(self, document_ref, signer_ref, actor,
                                 document_sha256=None):
        """Record a request for a document signature, as a reference.

        Reference implementation only: signing is a cryptographic
        operation over a document this substrate never holds, and
        the build performs no cryptography of its own (see
        PLATFORM-LAYER.md decisions 2-3). The request names the
        document by opaque ref and optional SHA-256 digest, and the
        signer by opaque ref; there is deliberately no sign or
        verify method on this surface.
        """
        self._guard(actor, "ingest", "exta_record_signature_request")
        _require_text(document_ref, "document ref")
        _require_text(signer_ref, "signer ref")
        if document_sha256 is not None:
            _validate_sha256(document_sha256, "document_sha256")
        with self._lock:
            request_id = self._next_id("sgq")
            record = {
                "id": request_id,
                "document_ref": document_ref,
                "document_sha256": document_sha256,
                "signer_ref": signer_ref,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "signed_here": False,
                "cryptography_performed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._signature_requests[request_id] = record
            self._record(actor, "exta_record_signature_request", request_id,
                         details={"document_ref": document_ref})
            return copy.deepcopy(record)

    def record_signature_event(self, request_id, status, actor):
        """Record a signature event as reported by the external engine.

        The status is the engine's own report, stored verbatim from
        the fixed vocabulary; nothing was signed here.
        """
        self._guard(actor, "ingest", "exta_record_signature_event", request_id)
        self._get(self._signature_requests, request_id, "signature request")
        _validate_choice(status, KNOWN_SIGNATURE_STATUSES,
                         "signature status")
        with self._lock:
            event_id = self._next_id("sge")
            record = {
                "id": event_id,
                "request_id": request_id,
                "status": status,
                "reference_stub": True,
                "signed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._signature_events[event_id] = record
            self._record(actor, "exta_record_signature_event", request_id,
                         details={"status": status})
            return copy.deepcopy(record)

    def signature_view(self, request_id, actor):
        """Signature request plus reported-event rollup, derived."""
        self._guard(actor, "query", "exta_signature_view", request_id)
        record = self._get(self._signature_requests, request_id,
                           "signature request")
        with self._lock:
            events = [copy.deepcopy(e) for e in self._signature_events.values()
                      if e["request_id"] == request_id]
        record["events"] = events
        record["event_count"] = len(events)
        record["latest_status"] = events[-1]["status"] if events else None
        return record

    # -- E-workflow tooling (reference implementation) -----------------------

    def define_workflow_reference(self, name, steps, actor):
        """Record an e-workflow definition as data, as a reference.

        Reference implementation only, and explicitly distinct
        from the group's Extended scheduling & workflow automation
        family (the first batch unit's schedule records, which
        target this build's own analytics artifacts): e-workflows
        orchestrate business processes on the back-office systems,
        so the definition is held as stated step data and its runs
        are recorded as reported; the registry never executes a
        step (``executed_here`` is False throughout).
        """
        self._guard(actor, "ingest", "exta_define_workflow_reference")
        _require_text(name, "workflow name")
        validated = self._validate_workflow_steps(steps)
        with self._lock:
            workflow_id = self._next_id("wfr")
            record = {
                "id": workflow_id,
                "name": name,
                "steps": validated,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workflow_refs[workflow_id] = record
            self._record(actor, "exta_define_workflow_reference", workflow_id,
                         details={"name": name})
            return copy.deepcopy(record)

    @staticmethod
    def _validate_workflow_steps(steps):
        if not isinstance(steps, list) or not steps:
            raise ValidationError("workflow steps must be a non-empty list")
        validated = []
        for step in steps:
            if not isinstance(step, dict):
                raise ValidationError("each workflow step must be an object")
            label = step.get("step")
            action = step.get("action")
            _require_text(label, "workflow step label")
            _require_text(action, "workflow step action")
            validated.append({"step": label, "action": action})
        return validated

    def record_workflow_run_reference(self, workflow_id, outcome, actor,
                                      reported_steps=None):
        """Record an e-workflow run as reported; nothing executed."""
        self._guard(actor, "ingest", "exta_record_workflow_run_reference",
                    workflow_id)
        self._get(self._workflow_refs, workflow_id, "workflow reference")
        _validate_choice(outcome, KNOWN_WORKFLOW_RUN_OUTCOMES,
                         "workflow run outcome")
        if reported_steps is not None:
            _validate_count(reported_steps, "reported_steps")
        with self._lock:
            run_id = self._next_id("wfx")
            record = {
                "id": run_id,
                "workflow_id": workflow_id,
                "outcome": outcome,
                "reported_steps": reported_steps,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "executed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._workflow_runs[run_id] = record
            self._record(actor, "exta_record_workflow_run_reference",
                         workflow_id, details={"outcome": outcome})
            return copy.deepcopy(record)

    def workflow_view(self, workflow_id, actor):
        """Workflow definition plus reported-run rollup, derived."""
        self._guard(actor, "query", "exta_workflow_view", workflow_id)
        record = self._get(self._workflow_refs, workflow_id,
                           "workflow reference")
        with self._lock:
            runs = [copy.deepcopy(r) for r in self._workflow_runs.values()
                    if r["workflow_id"] == workflow_id]
        record["runs"] = runs
        record["run_count"] = len(runs)
        record["last_outcome"] = runs[-1]["outcome"] if runs else None
        return record

    # -- Mobile client capabilities ------------------------------------------

    def register_mobile_client(self, client_ref, platform, actor):
        """Register a mobile client as a record.

        The build ships no client software: this registry records
        the clients the fork's platform reports (opaque ref,
        platform label) and the capability declarations and
        reported usage recorded for them. There are no build-side
        sessions (PLATFORM-LAYER.md decision 5), so no session
        record exists on this surface.
        """
        self._guard(actor, "ingest", "exta_register_mobile_client")
        _require_text(client_ref, "client ref")
        _validate_choice(platform, KNOWN_CLIENT_PLATFORMS, "client platform")
        with self._lock:
            if client_ref in self._mobile_client_ids_by_ref:
                raise ValidationError(
                    "client ref already registered: %r" % (client_ref,))
            client_id = self._next_id("mbc")
            record = {
                "id": client_id,
                "client_ref": client_ref,
                "platform": platform,
                "client_software_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._mobile_clients[client_id] = record
            self._mobile_client_ids_by_ref[client_ref] = client_id
            self._record(actor, "exta_register_mobile_client", client_id,
                         details={"platform": platform})
            return copy.deepcopy(record)

    def declare_client_capability(self, client_id, capability, actor):
        """Declare, as data, one capability a registered client surfaces.

        A declaration is a record about the client; nothing is
        delivered to or enabled on a device here.
        """
        self._guard(actor, "ingest", "exta_declare_client_capability",
                    client_id)
        self._get(self._mobile_clients, client_id, "mobile client")
        _validate_choice(capability, KNOWN_CLIENT_CAPABILITIES,
                         "client capability")
        with self._lock:
            for existing in self._client_capabilities.values():
                if existing["client_id"] == client_id \
                        and existing["capability"] == capability:
                    raise ValidationError(
                        "capability already declared for this client: %r"
                        % (capability,))
            declaration_id = self._next_id("mbp")
            record = {
                "id": declaration_id,
                "client_id": client_id,
                "capability": capability,
                "declared_by": actor_name(actor),
                "declared_utc": _utc_now(),
            }
            self._client_capabilities[declaration_id] = record
            self._record(actor, "exta_declare_client_capability", client_id,
                         details={"capability": capability})
            return copy.deepcopy(record)

    def record_client_usage(self, client_id, capability, reported_count,
                            actor):
        """Record a mobile client's usage count, as reported.

        The count is the client's own report, stored verbatim; the
        build measures nothing (``measured_here`` is False on every
        usage record).
        """
        self._guard(actor, "ingest", "exta_record_client_usage", client_id)
        self._get(self._mobile_clients, client_id, "mobile client")
        _validate_choice(capability, KNOWN_CLIENT_CAPABILITIES,
                         "client capability")
        _validate_count(reported_count, "reported_count")
        with self._lock:
            usage_id = self._next_id("mbu")
            record = {
                "id": usage_id,
                "client_id": client_id,
                "capability": capability,
                "reported_count": reported_count,
                "measured_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._client_usage[usage_id] = record
            self._record(actor, "exta_record_client_usage", client_id,
                         details={"capability": capability})
            return copy.deepcopy(record)

    @staticmethod
    def _derive_reported_usage_total(usage_records):
        """Sum the records' reported counts. The batch addition's
        fresh negative-control seam: the total is a sum of
        *reported* counts derived at read -- a mutant that echoes
        one record's count instead of summing is the defect the
        drill rejects."""
        return sum(r["reported_count"] for r in usage_records)

    def mobile_client_view(self, client_id, actor):
        """Client record plus declarations and reported usage, derived.

        ``reported_usage_total`` is the seam's sum over the recorded
        usage reports -- a sum of reports, never a measurement.
        """
        self._guard(actor, "query", "exta_mobile_client_view", client_id)
        record = self._get(self._mobile_clients, client_id, "mobile client")
        with self._lock:
            declarations = [copy.deepcopy(d)
                            for d in self._client_capabilities.values()
                            if d["client_id"] == client_id]
            usage = [copy.deepcopy(u) for u in self._client_usage.values()
                     if u["client_id"] == client_id]
        record["capabilities"] = declarations
        record["capability_count"] = len(declarations)
        record["usage_records"] = usage
        record["usage_record_count"] = len(usage)
        record["reported_usage_total"] = self._derive_reported_usage_total(usage)
        return record

    def get_mobile_client(self, client_id, actor):
        """The stored client record (registration only, no rollup)."""
        self._guard(actor, "query", "exta_get_mobile_client", client_id)
        return self._get(self._mobile_clients, client_id, "mobile client")
