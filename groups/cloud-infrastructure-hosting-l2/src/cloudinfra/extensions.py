"""Final GAPS batch extensions for the Cloud Infrastructure &
Hosting L2 merged build.

Clean-room, standard-library-only records/derivation extensions for
the 14 open Extended entries of this group: 6 built as in-substrate
records plus deterministic derivations over the core's own records,
8 shipped as labeled reference implementations. See ``BATCH.md``
in the group directory for the per-entry disposition.

Design, following the core's doctrines:

- This module is a wrapper around :class:`CloudInfraStore`; the
  core modules are untouched (byte-identical). Core entities
  (tenancies, templates, deployments, environments, accounts,
  monitors, security services, protection records) are always read
  through the core store's public API, never re-implemented.
- RBAC goes through :mod:`cloudinfra.access` exactly as the core
  enforces it: each extension operation maps onto an existing core
  action (the core action set is fixed), User actors are checked
  *before* any state change or id allocation, and denied attempts
  are recorded on the core audit log with the extension action name
  suffixed ``:denied``. Organization membership is enforced through
  the core store's own organization read, so the membership
  boundary is the core's, not a copy. Plain-string actors carry
  identity only, mirroring the core convention.
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``.
- All references are opaque ``*_ref`` strings. Nothing here
  provisions, orchestrates, executes, collects telemetry, carries
  traffic, backs anything up, performs cryptography, or verifies
  anything against an external source: this remains a records
  substrate *about* hosting, never a host (PLATFORM-LAYER.md
  decision 6 — a fork's hosting substrate does not transfer).
- Derived values are derived at read and never stored: a
  deployment intent's template settings text, a verification
  case's status and current outcome, and every summary are
  computed on read; stored records carry no derived key, pinned
  by test.
- Money discipline: there is none — deliberately, as in the core.
  No fork states an amount, a rate, or a fee, so no record in
  this module holds a money shape anywhere: the invoicing surface
  is invoice records with opaque references and recorded status
  labels only, and the FinOps summary derives counts and integer
  service-unit sums from the core's utilization records. A
  recursive key scan pins the absence, by test.
- Verification cases carry the batch's fresh negative control in
  a new surface: the actor who records a verification outcome may
  never be the actor who opened the case, enforced at a single
  named seam (``_check_verification_decider_not_opener``).
- The 8 stub-engine entries ship as labeled reference
  implementations: every record they create carries
  ``reference_stub: True`` and status ``recorded_reference_only``
  (telemetry-pipeline and CDN references also carry
  ``reference_transport: True`` — the reference moves nothing).
  Key-management records are metadata only — no field can hold
  key material, and no cryptography is performed or claimed
  (PLATFORM-LAYER.md decisions 2 and 3).
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import User, require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import MONITOR_KINDS, OPERATIONS_KINDS, PROTECTION_KINDS

SECURITY_CHECK_OUTCOMES = (
    "reported_pass",
    "reported_fail",
    "reported_inconclusive",
)
OPERATION_OUTCOMES = ("reported_completed", "reported_failed")
INVOICE_STATUSES = ("issued", "settled", "void")
RESOURCE_KINDS = ("compute", "memory", "storage", "network")
VERIFICATION_KINDS = (
    "data_residency",
    "personnel_us_citizenship",
    "operations_residency",
)
VERIFICATION_OUTCOMES = (
    "reported_verified",
    "reported_not_verified",
    "reported_inconclusive",
)
KEY_KINDS = ("symmetric_key", "asymmetric_key_pair", "certificate", "key_store")
ELASTIC_DELIVERY_FORMS = ("hosted", "serverless")

# Record kinds held by this extension (the built surfaces).
KIND_INTENT = "deployment_intent"
KIND_SECURITY_CONFIG = "security_service_config"
KIND_SECURITY_CHECK = "security_check_result"
KIND_OPERATION = "operation_request"
KIND_INVOICE = "invoice"
KIND_ALLOCATION = "resource_allocation"
KIND_VERIFICATION_CASE = "verification_case"
KIND_VERIFICATION_OUTCOME = "verification_outcome"
# Record kinds for the labeled reference implementations.
KIND_PROVISIONING_REF = "provisioning_reference"
KIND_ELASTIC_REF = "elastic_hosting_reference"
KIND_TELEMETRY_REF = "telemetry_reference"
KIND_BACKUP_REF = "backup_execution_reference"
KIND_KEY_METADATA = "key_metadata"
KIND_AI_ENGINE_REF = "ai_engine_reference"
KIND_CDN_REF = "cdn_reference"
KIND_AA_SUPPORT_REF = "authorization_support_reference"

REFERENCE_KINDS = (
    KIND_PROVISIONING_REF,
    KIND_ELASTIC_REF,
    KIND_TELEMETRY_REF,
    KIND_BACKUP_REF,
    KIND_KEY_METADATA,
    KIND_AI_ENGINE_REF,
    KIND_CDN_REF,
    KIND_AA_SUPPORT_REF,
)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _optional_text(value, field):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % field)
    return value


def _units(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(
            "%s must be an integer >= 0 (service units)" % field)
    return value


def _period(value, field):
    if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-(0[1-9]|1[0-2])", value):
        raise ValidationError("%s must be a YYYY-MM period: %r" % (field, value))
    return value


def _moment(value, field):
    """Validate an ISO date or datetime string (mirrors the core)."""
    if not isinstance(value, str):
        raise ValidationError("%s must be an ISO date or datetime string" % field)
    text = value.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            datetime.strptime(text, "%Y-%m-%d")
        else:
            datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise ValidationError(
            "%s is not an ISO date or datetime: %r" % (field, value))
    return value


def _one_of(value, known, field):
    if value not in known:
        raise ValidationError(
            "%s must be one of %s: %r" % (field, ", ".join(known), value))
    return value


class CloudInfraExtensions:
    """GAPS-batch extension surface over a core CloudInfraStore."""

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

        Mirrors the sibling extension modules: an actor must be
        present; User actors are checked against the core
        permission matrix before anything changes; plain strings
        carry identity only (the service layer enforces roles for
        those, as in the core).
        """
        try:
            if actor is None:
                raise PermissionDenied(
                    "permission denied: no user supplied for %r" % (core_action,))
            if isinstance(actor, User):
                require(actor, core_action)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", target)
            raise

    def _guard_read(self, actor, core_action, audit_action, target=None):
        """Enforce a read permission when the actor carries a role."""
        if isinstance(actor, User):
            try:
                require(actor, core_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", target)
                raise

    def _org(self, org_id, actor, audit_action):
        """Resolve the organization through the core store, so the
        membership boundary (and admin bypass) is the core's own.
        A membership denial is audited with the extension action."""
        try:
            return self.store.get_organization(org_id, actor)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", org_id)
            raise

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
            self._audit(actor, audit_action, record_id, details={"kind": kind})
            return copy.deepcopy(record)

    def _entity(self, kind, org_id, record_id, label):
        record = self._records.get((kind, record_id))
        if record is None or record["org_id"] != org_id:
            raise NotFoundError(
                "no such %s in organization %s: %r" % (label, org_id, record_id))
        return record

    def _check_ref_free(self, kind, org_id, field, value, label):
        for (held_kind, _rid), record in self._records.items():
            if (held_kind == kind and record["org_id"] == org_id
                    and record[field] == value):
                raise ValidationError(
                    "%s already exists in organization %s: %r"
                    % (label, org_id, value))

    def _list(self, kind, org_id):
        return [copy.deepcopy(self._records[key])
                for key in self._order
                if key[0] == kind and self._records[key]["org_id"] == org_id]

    # -- template execution: deployment-intent records ----------------
    #
    # The entry's own text binds the form: the template registry
    # stores settings verbatim and never executes. The extension
    # therefore records deployment *intents* that reference a core
    # template, a tenancy, and a workload; the settings text is
    # derived into the read view from the core template record and
    # is never copied onto the stored intent, and no operation in
    # this module executes, applies, or launches anything.

    def record_deployment_intent(self, org_id, intent_ref, template_id,
                                 tenancy_id, workload_ref, actor,
                                 environment_id=None, deployment_id=None,
                                 note=None):
        """Record an intent to deploy a workload under a template.
        Recording an intent executes nothing: the template's
        settings are data, referenced here, never run."""
        self._guard(actor, "template_write", "ext_deployment_intent_record")
        self._org(org_id, actor, "ext_deployment_intent_record")
        _text(intent_ref, "intent_ref")
        _text(workload_ref, "workload_ref")
        _optional_text(note, "note")
        self.store.get_template(org_id, template_id, actor)
        self.store.get_tenancy(org_id, tenancy_id, actor)
        if environment_id is not None:
            self.store.get_environment(org_id, environment_id, actor)
        if deployment_id is not None:
            self.store.get_deployment(org_id, deployment_id, actor)
        with self._lock:
            self._check_ref_free(KIND_INTENT, org_id, "intent_ref",
                                 intent_ref, "intent_ref")
            return self._create(
                KIND_INTENT, "int",
                {
                    "org_id": org_id,
                    "intent_ref": intent_ref,
                    "template_id": template_id,
                    "tenancy_id": tenancy_id,
                    "environment_id": environment_id,
                    "deployment_id": deployment_id,
                    "workload_ref": workload_ref,
                    "note": note,
                    "status": "recorded",
                    "executed": False,
                },
                actor, "ext_deployment_intent_record")

    def _intent_view(self, record, actor):
        view = copy.deepcopy(record)
        template = self.store.get_template(
            record["org_id"], record["template_id"], actor)
        view["template_ref"] = template["template_ref"]
        view["settings_text"] = template["settings_text"]
        return view

    def get_deployment_intent(self, org_id, intent_id, actor):
        self._guard_read(actor, "org_read", "ext_deployment_intent_read")
        self._org(org_id, actor, "ext_deployment_intent_read")
        record = self._entity(KIND_INTENT, org_id, intent_id,
                              "deployment intent")
        return self._intent_view(record, actor)

    def list_deployment_intents(self, org_id, actor):
        self._guard_read(actor, "org_read", "ext_deployment_intent_read")
        self._org(org_id, actor, "ext_deployment_intent_read")
        return [self._intent_view(record, actor)
                for record in self._list(KIND_INTENT, org_id)]

    def cancel_deployment_intent(self, org_id, intent_id, actor):
        """Guarded lifecycle: recorded -> cancelled; cancelled is
        terminal. Cancelling an intent record undoes nothing in the
        world — nothing was ever executed."""
        self._guard(actor, "template_write", "ext_deployment_intent_cancel")
        self._org(org_id, actor, "ext_deployment_intent_cancel")
        record = self._entity(KIND_INTENT, org_id, intent_id,
                              "deployment intent")
        if record["status"] != "recorded":
            raise ValidationError(
                "deployment intent %s cannot cancel from %s"
                % (intent_id, record["status"]))
        with self._lock:
            record["status"] = "cancelled"
        self._audit(actor, "ext_deployment_intent_cancel", intent_id,
                    details={"kind": KIND_INTENT})
        return copy.deepcopy(record)

    # -- platform security service engines: configurations & results --

    def record_security_service_config(self, org_id, config_ref, service_id,
                                       settings_text, actor, label=None):
        """Record a configuration for a core platform security
        service record. The settings text is stored verbatim as a
        record; no engine is configured or operated by recording
        it."""
        self._guard(actor, "service_write", "ext_security_config_record")
        self._org(org_id, actor, "ext_security_config_record")
        _text(config_ref, "config_ref")
        _text(settings_text, "settings_text")
        _optional_text(label, "label")
        self.store.get_security_service(org_id, service_id, actor)
        with self._lock:
            self._check_ref_free(KIND_SECURITY_CONFIG, org_id, "config_ref",
                                 config_ref, "config_ref")
            return self._create(
                KIND_SECURITY_CONFIG, "scc",
                {
                    "org_id": org_id,
                    "config_ref": config_ref,
                    "service_id": service_id,
                    "label": label,
                    "settings_text": settings_text,
                    "state": "recorded",
                },
                actor, "ext_security_config_record")

    def record_security_check_result(self, org_id, result_ref, service_id,
                                     outcome, actor, checked_at=None,
                                     detail=None):
        """Record a check result as reported by the platform
        security engine that ran it (outside this substrate). The
        outcome vocabulary is report-shaped by construction: this
        build runs no check of its own."""
        self._guard(actor, "service_write", "ext_security_check_record")
        self._org(org_id, actor, "ext_security_check_record")
        _text(result_ref, "result_ref")
        _one_of(outcome, SECURITY_CHECK_OUTCOMES, "outcome")
        _optional_text(detail, "detail")
        if checked_at is not None:
            _moment(checked_at, "checked_at")
        self.store.get_security_service(org_id, service_id, actor)
        with self._lock:
            self._check_ref_free(KIND_SECURITY_CHECK, org_id, "result_ref",
                                 result_ref, "result_ref")
            return self._create(
                KIND_SECURITY_CHECK, "scr",
                {
                    "org_id": org_id,
                    "result_ref": result_ref,
                    "service_id": service_id,
                    "outcome": outcome,
                    "checked_at": checked_at,
                    "detail": detail,
                },
                actor, "ext_security_check_record")

    def list_security_service_configs(self, org_id, actor):
        self._guard_read(actor, "org_read", "ext_security_config_read")
        self._org(org_id, actor, "ext_security_config_read")
        return self._list(KIND_SECURITY_CONFIG, org_id)

    def list_security_check_results(self, org_id, actor, service_id=None):
        self._guard_read(actor, "org_read", "ext_security_check_read")
        self._org(org_id, actor, "ext_security_check_read")
        results = self._list(KIND_SECURITY_CHECK, org_id)
        if service_id is not None:
            results = [r for r in results if r["service_id"] == service_id]
        return results

    def security_service_summary(self, org_id, service_id, actor):
        """Derived at read: configuration and reported-result
        counts for one core security service record, with the
        latest reported outcome. Nothing here is stored."""
        self._guard_read(actor, "org_read", "ext_security_summary_read")
        self._org(org_id, actor, "ext_security_summary_read")
        self.store.get_security_service(org_id, service_id, actor)
        configs = [r for r in self._list(KIND_SECURITY_CONFIG, org_id)
                   if r["service_id"] == service_id]
        results = [r for r in self._list(KIND_SECURITY_CHECK, org_id)
                   if r["service_id"] == service_id]
        by_outcome = {}
        for result in results:
            by_outcome[result["outcome"]] = by_outcome.get(result["outcome"], 0) + 1
        return {
            "org_id": org_id,
            "service_id": service_id,
            "config_count": len(configs),
            "result_count": len(results),
            "results_by_outcome": by_outcome,
            "latest_outcome": results[-1]["outcome"] if results else None,
        }

    # -- operations execution engines: operation request records -------

    def request_operation(self, org_id, request_ref, kind, target_ref,
                          label, actor, task_id=None):
        """Record a request for an operations execution (patch
        deployment, vulnerability scan, configuration enforcement,
        support action). The request is a record with a recorded
        state; nothing is executed by requesting it."""
        self._guard(actor, "operations_write", "ext_operation_request")
        self._org(org_id, actor, "ext_operation_request")
        _text(request_ref, "request_ref")
        _text(target_ref, "target_ref")
        _text(label, "label")
        _one_of(kind, OPERATIONS_KINDS, "kind")
        if task_id is not None:
            self.store.get_operations_task(org_id, task_id, actor)
        with self._lock:
            self._check_ref_free(KIND_OPERATION, org_id, "request_ref",
                                 request_ref, "request_ref")
            return self._create(
                KIND_OPERATION, "opr",
                {
                    "org_id": org_id,
                    "request_ref": request_ref,
                    "kind": kind,
                    "target_ref": target_ref,
                    "label": label,
                    "task_id": task_id,
                    "status": "requested",
                    "executed": False,
                },
                actor, "ext_operation_request")

    def record_operation_outcome(self, org_id, request_id, outcome, actor,
                                 detail=None):
        """Record the outcome of an operation request as reported
        by the executing system (outside this substrate).
        Guarded: only a requested operation can take an outcome,
        and the outcome is a reported state, not an effect here."""
        self._guard(actor, "operations_write", "ext_operation_outcome")
        self._org(org_id, actor, "ext_operation_outcome")
        _one_of(outcome, OPERATION_OUTCOMES, "outcome")
        _optional_text(detail, "detail")
        record = self._entity(KIND_OPERATION, org_id, request_id,
                              "operation request")
        if record["status"] != "requested":
            raise ValidationError(
                "operation request %s cannot take an outcome from %s"
                % (request_id, record["status"]))
        with self._lock:
            record["status"] = outcome
            record["outcome_detail"] = detail
        self._audit(actor, "ext_operation_outcome", request_id,
                    details={"kind": KIND_OPERATION, "outcome": outcome})
        return copy.deepcopy(record)

    def cancel_operation_request(self, org_id, request_id, actor):
        """Guarded lifecycle: requested -> cancelled; terminal."""
        self._guard(actor, "operations_write", "ext_operation_cancel")
        self._org(org_id, actor, "ext_operation_cancel")
        record = self._entity(KIND_OPERATION, org_id, request_id,
                              "operation request")
        if record["status"] != "requested":
            raise ValidationError(
                "operation request %s cannot cancel from %s"
                % (request_id, record["status"]))
        with self._lock:
            record["status"] = "cancelled"
        self._audit(actor, "ext_operation_cancel", request_id,
                    details={"kind": KIND_OPERATION})
        return copy.deepcopy(record)

    def get_operation_request(self, org_id, request_id, actor):
        self._guard_read(actor, "org_read", "ext_operation_read")
        self._org(org_id, actor, "ext_operation_read")
        return copy.deepcopy(self._entity(
            KIND_OPERATION, org_id, request_id, "operation request"))

    def list_operation_requests(self, org_id, actor):
        self._guard_read(actor, "org_read", "ext_operation_read")
        self._org(org_id, actor, "ext_operation_read")
        return self._list(KIND_OPERATION, org_id)

    def operations_summary(self, org_id, actor):
        """Derived at read: operation request counts by kind and
        by recorded status. Counts only."""
        self._guard_read(actor, "report_read", "ext_operations_summary_read")
        self._org(org_id, actor, "ext_operations_summary_read")
        requests = self._list(KIND_OPERATION, org_id)
        by_kind = {}
        by_status = {}
        for request in requests:
            by_kind[request["kind"]] = by_kind.get(request["kind"], 0) + 1
            by_status[request["status"]] = by_status.get(request["status"], 0) + 1
        return {
            "org_id": org_id,
            "operation_requests": {
                "total": len(requests),
                "by_kind": by_kind,
                "by_status": by_status,
            },
        }

    # -- invoicing / billing & FinOps: records with no money shape -----
    #
    # No fork states an amount, a rate, or a fee, so this surface
    # holds no money shape anywhere: an invoice is a reference, an
    # account link, a period, an optional label, and a recorded
    # status. The FinOps summary derives counts and integer
    # service-unit sums from the core's utilization records.

    def record_invoice(self, org_id, invoice_ref, account_id, period,
                       actor, label=None):
        """Record an invoice as issued by the billing process
        (outside this substrate). One invoice record per account
        per period, mirroring the core's utilization discipline.
        The record denominates nothing."""
        self._guard(actor, "operations_write", "ext_invoice_record")
        self._org(org_id, actor, "ext_invoice_record")
        _text(invoice_ref, "invoice_ref")
        _period(period, "period")
        _optional_text(label, "label")
        self.store.get_account(org_id, account_id, actor)
        with self._lock:
            self._check_ref_free(KIND_INVOICE, org_id, "invoice_ref",
                                 invoice_ref, "invoice_ref")
            for existing in self._list(KIND_INVOICE, org_id):
                if (existing["account_id"] == account_id
                        and existing["period"] == period):
                    raise ValidationError(
                        "invoice already recorded for account %s in %s"
                        % (account_id, period))
            return self._create(
                KIND_INVOICE, "inv",
                {
                    "org_id": org_id,
                    "invoice_ref": invoice_ref,
                    "account_id": account_id,
                    "period": period,
                    "label": label,
                    "status": "issued",
                },
                actor, "ext_invoice_record")

    def set_invoice_status(self, org_id, invoice_id, status, actor):
        """Guarded lifecycle over recorded states: issued ->
        settled / void; both terminal. Recording a status settles
        nothing — settlement happens in the billing process, and
        there is no amount here for it to settle."""
        self._guard(actor, "operations_write", "ext_invoice_status")
        self._org(org_id, actor, "ext_invoice_status")
        _one_of(status, INVOICE_STATUSES, "status")
        record = self._entity(KIND_INVOICE, org_id, invoice_id, "invoice")
        if record["status"] != "issued" or status == "issued":
            raise ValidationError(
                "invoice %s cannot move from %s to %s"
                % (invoice_id, record["status"], status))
        with self._lock:
            record["status"] = status
        self._audit(actor, "ext_invoice_status", invoice_id,
                    details={"kind": KIND_INVOICE, "status": status})
        return copy.deepcopy(record)

    def get_invoice(self, org_id, invoice_id, actor):
        self._guard_read(actor, "org_read", "ext_invoice_read")
        self._org(org_id, actor, "ext_invoice_read")
        return copy.deepcopy(self._entity(
            KIND_INVOICE, org_id, invoice_id, "invoice"))

    def list_invoices(self, org_id, actor):
        self._guard_read(actor, "org_read", "ext_invoice_read")
        self._org(org_id, actor, "ext_invoice_read")
        return self._list(KIND_INVOICE, org_id)

    def finops_summary(self, org_id, actor, period=None):
        """Derived at read from the core's account and utilization
        records plus this module's invoice records: account counts,
        integer service-unit sums, and invoice counts. There is no
        money anywhere in this substrate to summarize."""
        self._guard_read(actor, "report_read", "ext_finops_summary_read")
        self._org(org_id, actor, "ext_finops_summary_read")
        if period is not None:
            _period(period, "period")
        accounts = self.store.list_accounts(org_id, actor)
        utilization = self.store.list_utilization(org_id, actor)
        invoices = self._list(KIND_INVOICE, org_id)
        if period is not None:
            utilization = [u for u in utilization if u["period"] == period]
            invoices = [i for i in invoices if i["period"] == period]
        units_by_period = {}
        for record in utilization:
            units_by_period[record["period"]] = (
                units_by_period.get(record["period"], 0) + record["units"])
        accounts_by_status = {}
        for account in accounts:
            accounts_by_status[account["status"]] = (
                accounts_by_status.get(account["status"], 0) + 1)
        invoices_by_status = {}
        for invoice in invoices:
            invoices_by_status[invoice["status"]] = (
                invoices_by_status.get(invoice["status"], 0) + 1)
        return {
            "org_id": org_id,
            "period": period,
            "accounts": {
                "total": len(accounts),
                "by_status": accounts_by_status,
            },
            "utilization": {
                "records": len(utilization),
                "units_by_period": units_by_period,
                "units_total": sum(units_by_period.values()),
            },
            "invoices": {
                "total": len(invoices),
                "by_status": invoices_by_status,
            },
        }

    # -- application resource management: allocation records -----------

    def record_resource_allocation(self, org_id, allocation_ref, target_ref,
                                   resource_kind, units, actor,
                                   deployment_id=None):
        """Record a resource allocation over an opaque target (a
        workload or deployment reference), in integer service
        units. Recording an allocation schedules nothing and moves
        no resource; the allocation engine is outside this
        substrate."""
        self._guard(actor, "operations_write", "ext_allocation_record")
        self._org(org_id, actor, "ext_allocation_record")
        _text(allocation_ref, "allocation_ref")
        _text(target_ref, "target_ref")
        _one_of(resource_kind, RESOURCE_KINDS, "resource_kind")
        _units(units, "units")
        if deployment_id is not None:
            self.store.get_deployment(org_id, deployment_id, actor)
        with self._lock:
            self._check_ref_free(KIND_ALLOCATION, org_id, "allocation_ref",
                                 allocation_ref, "allocation_ref")
            return self._create(
                KIND_ALLOCATION, "ral",
                {
                    "org_id": org_id,
                    "allocation_ref": allocation_ref,
                    "target_ref": target_ref,
                    "resource_kind": resource_kind,
                    "units": units,
                    "deployment_id": deployment_id,
                    "status": "active",
                },
                actor, "ext_allocation_record")

    def release_resource_allocation(self, org_id, allocation_id, actor):
        """Guarded lifecycle: active -> released; terminal.
        Releasing a record releases no resource."""
        self._guard(actor, "operations_write", "ext_allocation_release")
        self._org(org_id, actor, "ext_allocation_release")
        record = self._entity(KIND_ALLOCATION, org_id, allocation_id,
                              "resource allocation")
        if record["status"] != "active":
            raise ValidationError(
                "resource allocation %s cannot release from %s"
                % (allocation_id, record["status"]))
        with self._lock:
            record["status"] = "released"
        self._audit(actor, "ext_allocation_release", allocation_id,
                    details={"kind": KIND_ALLOCATION})
        return copy.deepcopy(record)

    def get_resource_allocation(self, org_id, allocation_id, actor):
        self._guard_read(actor, "org_read", "ext_allocation_read")
        self._org(org_id, actor, "ext_allocation_read")
        return copy.deepcopy(self._entity(
            KIND_ALLOCATION, org_id, allocation_id, "resource allocation"))

    def list_resource_allocations(self, org_id, actor):
        self._guard_read(actor, "org_read", "ext_allocation_read")
        self._org(org_id, actor, "ext_allocation_read")
        return self._list(KIND_ALLOCATION, org_id)

    def resource_summary(self, org_id, actor):
        """Derived at read: allocation counts and integer
        service-unit sums over active allocations, by resource
        kind. A derivation over records — no scheduler runs."""
        self._guard_read(actor, "report_read", "ext_resource_summary_read")
        self._org(org_id, actor, "ext_resource_summary_read")
        allocations = self._list(KIND_ALLOCATION, org_id)
        by_kind = {}
        by_status = {}
        active_units_by_kind = {}
        for allocation in allocations:
            by_kind[allocation["resource_kind"]] = (
                by_kind.get(allocation["resource_kind"], 0) + 1)
            by_status[allocation["status"]] = (
                by_status.get(allocation["status"], 0) + 1)
            if allocation["status"] == "active":
                active_units_by_kind[allocation["resource_kind"]] = (
                    active_units_by_kind.get(allocation["resource_kind"], 0)
                    + allocation["units"])
        return {
            "org_id": org_id,
            "allocations": {
                "total": len(allocations),
                "by_kind": by_kind,
                "by_status": by_status,
            },
            "active_units_by_kind": active_units_by_kind,
            "active_units_total": sum(active_units_by_kind.values()),
        }

    # -- residency & personnel verification: case records ---------------
    #
    # The core records caller-stated residency labels; verifying
    # the claim behind a label is an organizational process outside
    # this substrate. The extension records verification *cases*
    # and the outcomes that process reports. Nothing is verified
    # against any external source here.

    def _check_verification_decider_not_opener(self, case, actor):
        """Separation-of-duties seam for verification outcomes.

        The actor who records a verification outcome (the decider,
        for this substrate's purposes) may never be the actor who
        opened the case. This seam is the batch's fresh
        negative-control target (see tests/README.md and
        tests/test_gaps_batch.py)."""
        if actor_name(actor) == case["created_by"]:
            raise PermissionDenied(
                "the recorder of a verification outcome is never "
                "the actor who opened the case")

    def open_verification_case(self, org_id, case_ref, subject_ref,
                               check_kind, actor, environment_id=None,
                               note=None):
        """Open a residency or personnel verification case over an
        opaque subject reference (an environment, a tenancy, or a
        personnel roster held elsewhere — the reference is opaque
        and no identifier of a person is recorded). The stored
        case carries no status: its state is derived at read from
        its outcome records."""
        self._guard(actor, "service_write", "ext_verification_case_open")
        self._org(org_id, actor, "ext_verification_case_open")
        _text(case_ref, "case_ref")
        _text(subject_ref, "subject_ref")
        _one_of(check_kind, VERIFICATION_KINDS, "check_kind")
        _optional_text(note, "note")
        if environment_id is not None:
            self.store.get_environment(org_id, environment_id, actor)
        with self._lock:
            self._check_ref_free(KIND_VERIFICATION_CASE, org_id, "case_ref",
                                 case_ref, "case_ref")
            return self._create(
                KIND_VERIFICATION_CASE, "vfc",
                {
                    "org_id": org_id,
                    "case_ref": case_ref,
                    "subject_ref": subject_ref,
                    "check_kind": check_kind,
                    "environment_id": environment_id,
                    "note": note,
                },
                actor, "ext_verification_case_open")

    def record_verification_outcome(self, org_id, case_id, outcome, actor,
                                    detail=None):
        """Record a verification outcome as reported by the
        embedding organization's verification process. The
        separation-of-duties seam runs first: the case opener may
        not record its outcome. The outcome is recorded verbatim
        as reported; this build verifies nothing itself."""
        audit_action = "ext_verification_outcome"
        self._guard(actor, "service_write", audit_action)
        self._org(org_id, actor, audit_action)
        _one_of(outcome, VERIFICATION_OUTCOMES, "outcome")
        _optional_text(detail, "detail")
        case = self._entity(KIND_VERIFICATION_CASE, org_id, case_id,
                            "verification case")
        try:
            self._check_verification_decider_not_opener(case, actor)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", case_id)
            raise
        with self._lock:
            return self._create(
                KIND_VERIFICATION_OUTCOME, "vfo",
                {
                    "org_id": org_id,
                    "case_id": case_id,
                    "outcome": outcome,
                    "detail": detail,
                },
                actor, audit_action)

    def _verification_case_view(self, record):
        view = copy.deepcopy(record)
        outcomes = [r for r in self._list(KIND_VERIFICATION_OUTCOME,
                                          record["org_id"])
                    if r["case_id"] == record["id"]]
        view["outcome_count"] = len(outcomes)
        view["current_outcome"] = outcomes[-1]["outcome"] if outcomes else None
        view["status"] = "decided" if outcomes else "open"
        return view

    def get_verification_case(self, org_id, case_id, actor):
        self._guard_read(actor, "org_read", "ext_verification_read")
        self._org(org_id, actor, "ext_verification_read")
        record = self._entity(KIND_VERIFICATION_CASE, org_id, case_id,
                              "verification case")
        return self._verification_case_view(record)

    def list_verification_cases(self, org_id, actor):
        self._guard_read(actor, "org_read", "ext_verification_read")
        self._org(org_id, actor, "ext_verification_read")
        return [self._verification_case_view(record)
                for record in self._list(KIND_VERIFICATION_CASE, org_id)]

    def list_verification_outcomes(self, org_id, case_id, actor):
        self._guard_read(actor, "org_read", "ext_verification_read")
        self._org(org_id, actor, "ext_verification_read")
        self._entity(KIND_VERIFICATION_CASE, org_id, case_id,
                     "verification case")
        return [r for r in self._list(KIND_VERIFICATION_OUTCOME, org_id)
                if r["case_id"] == case_id]

    # -- labeled reference implementations (stub-engine entries) --------
    #
    # Each record below stands for an engine or service that runs
    # outside this substrate. Every record carries
    # ``reference_stub: True`` and status ``recorded_reference_only``;
    # creating one changes nothing outside this module's records.

    def _reference(self, kind, prefix, fields, actor, audit_action,
                   core_action):
        self._guard(actor, core_action, audit_action)
        self._org(fields["org_id"], actor, audit_action)
        fields = dict(fields)
        fields["reference_stub"] = True
        fields["status"] = "recorded_reference_only"
        with self._lock:
            self._check_ref_free(kind, fields["org_id"], "reference_ref",
                                 fields["reference_ref"], "reference_ref")
            return self._create(kind, prefix, fields, actor, audit_action)

    def record_provisioning_reference(self, org_id, reference_ref,
                                      target_ref, label, actor, detail=None):
        """Reference for the hosting platform / provisioning &
        orchestration engines (the platform layer entire,
        PLATFORM-LAYER.md decision 6). A provisioning plan
        reference: recording it provisions nothing."""
        _text(reference_ref, "reference_ref")
        _text(target_ref, "target_ref")
        _text(label, "label")
        _optional_text(detail, "detail")
        return self._reference(
            KIND_PROVISIONING_REF, "pvr",
            {
                "org_id": org_id,
                "reference_ref": reference_ref,
                "target_ref": target_ref,
                "label": label,
                "detail": detail,
                "provisioned": False,
            },
            actor, "ext_provisioning_reference", "deployment_write")

    def record_elastic_hosting_reference(self, org_id, reference_ref,
                                         target_ref, label, actor,
                                         delivery_form="hosted", detail=None):
        """Reference for the Elastic Stack hosting engine,
        including its serverless delivery form (a recorded label).
        Recording the reference hosts nothing here."""
        _text(reference_ref, "reference_ref")
        _text(target_ref, "target_ref")
        _text(label, "label")
        _one_of(delivery_form, ELASTIC_DELIVERY_FORMS, "delivery_form")
        _optional_text(detail, "detail")
        return self._reference(
            KIND_ELASTIC_REF, "elr",
            {
                "org_id": org_id,
                "reference_ref": reference_ref,
                "target_ref": target_ref,
                "label": label,
                "delivery_form": delivery_form,
                "detail": detail,
                "hosted_here": False,
            },
            actor, "ext_elastic_hosting_reference", "deployment_write")

    def record_telemetry_reference(self, org_id, reference_ref, kind,
                                   target_ref, label, actor, monitor_id=None,
                                   detail=None):
        """Reference for the monitoring & observability engines
        (telemetry collection, tracing, alerting pipelines). The
        receipt is transport-shaped and labeled as such: the
        reference collects no telemetry and moves nothing."""
        _text(reference_ref, "reference_ref")
        _text(target_ref, "target_ref")
        _text(label, "label")
        _one_of(kind, MONITOR_KINDS, "kind")
        _optional_text(detail, "detail")
        self._guard(actor, "service_write", "ext_telemetry_reference")
        self._org(org_id, actor, "ext_telemetry_reference")
        if monitor_id is not None:
            self.store.get_monitor(org_id, monitor_id, actor)
        return self._reference(
            KIND_TELEMETRY_REF, "tlr",
            {
                "org_id": org_id,
                "reference_ref": reference_ref,
                "kind": kind,
                "target_ref": target_ref,
                "label": label,
                "monitor_id": monitor_id,
                "detail": detail,
                "reference_transport": True,
                "telemetry_collected": False,
            },
            actor, "ext_telemetry_reference", "service_write")

    def record_backup_execution_reference(self, org_id, reference_ref, kind,
                                          target_ref, label, actor,
                                          protection_id=None, detail=None):
        """Reference for backup execution & disaster-recovery
        orchestration. It may name a core protection record;
        recording the reference backs nothing up and restores
        nothing."""
        _text(reference_ref, "reference_ref")
        _text(target_ref, "target_ref")
        _text(label, "label")
        _one_of(kind, PROTECTION_KINDS, "kind")
        _optional_text(detail, "detail")
        self._guard(actor, "service_write", "ext_backup_execution_reference")
        self._org(org_id, actor, "ext_backup_execution_reference")
        if protection_id is not None:
            self.store.get_protection_record(org_id, protection_id, actor)
        return self._reference(
            KIND_BACKUP_REF, "bkr",
            {
                "org_id": org_id,
                "reference_ref": reference_ref,
                "kind": kind,
                "target_ref": target_ref,
                "label": label,
                "protection_id": protection_id,
                "detail": detail,
                "executed": False,
            },
            actor, "ext_backup_execution_reference", "service_write")

    def record_key_metadata(self, org_id, key_ref, key_kind, label, actor,
                            algorithm_label=None, note=None):
        """Reference for encryption implementation & key
        management: key and certificate *metadata* only. There is
        no parameter that can carry key material and no field that
        can hold it; the algorithm label is caller-stated metadata,
        exactly as the core's encryption labels are caller-stated.
        This build performs no cryptography and claims no
        FIPS-validated module (PLATFORM-LAYER.md decisions 2–3)."""
        _text(key_ref, "key_ref")
        _text(label, "label")
        _one_of(key_kind, KEY_KINDS, "key_kind")
        _optional_text(algorithm_label, "algorithm_label")
        _optional_text(note, "note")
        audit_action = "ext_key_metadata_record"
        self._guard(actor, "service_write", audit_action)
        self._org(org_id, actor, audit_action)
        fields = {
            "org_id": org_id,
            "reference_ref": key_ref,
            "key_ref": key_ref,
            "key_kind": key_kind,
            "label": label,
            "algorithm_label": algorithm_label,
            "note": note,
            "reference_stub": True,
            "status": "recorded_reference_only",
        }
        with self._lock:
            self._check_ref_free(KIND_KEY_METADATA, org_id, "key_ref",
                                 key_ref, "key_ref")
            return self._create(KIND_KEY_METADATA, "kym", fields, actor,
                                audit_action)

    def record_ai_engine_reference(self, org_id, reference_ref, label, actor,
                                   target_ref=None, detail=None):
        """Reference for the AI recommendation engine (IBM Concert
        class). Recommendations issued by that engine are recorded
        by the core's recommendation records; this reference
        generates none."""
        _text(reference_ref, "reference_ref")
        _text(label, "label")
        _optional_text(target_ref, "target_ref")
        _optional_text(detail, "detail")
        return self._reference(
            KIND_AI_ENGINE_REF, "air",
            {
                "org_id": org_id,
                "reference_ref": reference_ref,
                "target_ref": target_ref,
                "label": label,
                "detail": detail,
                "issues_recommendations": False,
            },
            actor, "ext_ai_engine_reference", "operations_write")

    def record_cdn_reference(self, org_id, reference_ref, target_ref, label,
                             actor, provider_label=None, detail=None):
        """Reference for CDN operation (the network a fork delivers
        through). The receipt is transport-shaped and labeled as
        such: the reference carries no traffic."""
        _text(reference_ref, "reference_ref")
        _text(target_ref, "target_ref")
        _text(label, "label")
        _optional_text(provider_label, "provider_label")
        _optional_text(detail, "detail")
        return self._reference(
            KIND_CDN_REF, "cdr",
            {
                "org_id": org_id,
                "reference_ref": reference_ref,
                "target_ref": target_ref,
                "label": label,
                "provider_label": provider_label,
                "detail": detail,
                "reference_transport": True,
                "traffic_carried": False,
            },
            actor, "ext_cdn_reference", "service_write")

    def record_authorization_support_reference(self, org_id, reference_ref,
                                               label, actor, target_ref=None,
                                               detail=None):
        """Reference for Assessment & Authorization support
        services (a vendor support practice, outside this
        substrate). Recording the reference prepares no
        authorization package and asserts no authorization."""
        _text(reference_ref, "reference_ref")
        _text(label, "label")
        _optional_text(target_ref, "target_ref")
        _optional_text(detail, "detail")
        return self._reference(
            KIND_AA_SUPPORT_REF, "aar",
            {
                "org_id": org_id,
                "reference_ref": reference_ref,
                "target_ref": target_ref,
                "label": label,
                "detail": detail,
                "package_prepared": False,
            },
            actor, "ext_authorization_support_reference", "service_write")

    def get_reference_record(self, org_id, record_id, actor):
        """Any labeled reference record, by id, org-scoped."""
        self._guard_read(actor, "org_read", "ext_reference_read")
        self._org(org_id, actor, "ext_reference_read")
        for kind in REFERENCE_KINDS:
            record = self._records.get((kind, record_id))
            if record is not None and record["org_id"] == org_id:
                return copy.deepcopy(record)
        raise NotFoundError(
            "no such reference record in organization %s: %r"
            % (org_id, record_id))

    def list_reference_records(self, org_id, actor, kind=None):
        """All labeled reference records for an organization, in
        creation order, optionally restricted to one kind."""
        self._guard_read(actor, "org_read", "ext_reference_read")
        self._org(org_id, actor, "ext_reference_read")
        kinds = REFERENCE_KINDS if kind is None else (kind,)
        return [copy.deepcopy(self._records[key])
                for key in self._order
                if key[0] in kinds
                and self._records[key]["org_id"] == org_id]
