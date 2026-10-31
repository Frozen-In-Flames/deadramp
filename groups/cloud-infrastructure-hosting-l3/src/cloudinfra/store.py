"""The Cloud Infrastructure & Hosting records substrate.

Clean-room implementation of the Cloud Infrastructure & Hosting
union spec's core, carried up whole from the founding L2 build and
uplifted to the High baseline: organization registry & membership, cloud
tenancy records, hosting environment records, infrastructure
provider registry, hosted deployment records, deployment template
registry, monitoring records, platform security service records,
backup & recovery records, identity configuration records,
operations task records, cloud account & utilization records,
recommendation records, registry reporting, and registry search —
over an append-only audit log.

These are records ABOUT infrastructure. The store provisions
nothing, orchestrates nothing, and operates no network: it records
tenancies, environments, deployments, services, and tasks as the
embedding organization records them. Template records hold their
settings verbatim and are never executed; registries record, they
do not run.

Privacy discipline (hard rule): every entity is keyed by an opaque
caller-supplied reference and carries only the fields in the
contract. Workloads, targets, and accounts are opaque references.
There is no field anywhere that can hold workload content, message
content, a credential or secret, or any real identifier of a
person: identity configuration records name a configuration kind
and a label, never a credential. Validation always precedes
mutation: a failed operation changes nothing, consumes no id, and
records nothing.

Two boundaries are enforced on every organization-scoped
operation:

1. Membership -- the actor must be a member of the organization,
   or hold the platform ``admin`` role, else
   :class:`PermissionDenied`.
2. Role permission -- the action named for the operation must be
   in the actor's role permission set (see
   :mod:`cloudinfra.access`) when the actor is a
   :class:`~cloudinfra.access.User`. A plain string actor carries
   identity (for provenance) but no role, so role enforcement for
   those happens in the service layer.

Derivation discipline: a tenancy's ``deployment_count`` and
``active_deployment_count`` and an operations task's ``overdue``
are derived at read time and never stored. The stored records
carry none of those keys. Lifecycles (environment
``provisioned`` -> ``active`` -> ``retired``, deployment
``recorded`` -> ``active`` -> ``stopped``, task ``open`` ->
``completed`` / ``cancelled``, account ``open`` -> ``closed``) are
guarded transitions, not date derivations, so those statuses are
stored.

Deployment slot seam: within one tenancy, at most one deployment
of a given workload reference may be ``active`` at a time.
:meth:`CloudInfraStore._check_deployment_slot` runs before a
deployment is activated and raises :class:`ValidationError` when
another deployment of the same workload is already active in the
tenancy. This is the group's negative control.

Money discipline: there is none — deliberately. No fork's
description states an amount, a rate, or a fee schedule, so this
build holds no money shape anywhere: utilization is recorded in
integer service units, and booleans, floats, and strings are
rejected for unit counts at the boundary.

The store records every successful mutation to its audit log (when
one is attached). Reads are not audited here; denied attempts and
audit reads are the HTTP layer's responsibility, so nothing is
recorded twice.

Fail-closed audit writes (AU-5) [L3]: every mutating method below
is wrapped by :func:`_fail_closed` -- it runs against a snapshot of
the store state; if it raises
:class:`~cloudinfra.errors.AuditWriteError` (its audit entry could
not be durably recorded), the snapshot is restored and the error
propagates, so an operation whose audit write fails does not
proceed. Read methods are not wrapped: they record no audit entry
on success, so there is no write to fail closed on. This is the
High-baseline uplift of the sibling High groups
(``groups/storage-l3`` and its precedents), applied here; the
founding L2 store has no such wrapper.
"""

import copy
import functools
import re
import threading
from datetime import datetime, timezone

from .access import User, require
from .audit import actor_name
from .errors import (
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)

HOSTING_MODELS = ("boundary_protected", "managed", "enclave", "shared")
ENVIRONMENT_STATUSES = ("provisioned", "active", "retired")
DEPLOYMENT_STATUSES = ("recorded", "active", "stopped")
MONITOR_KINDS = ("continuous", "network", "log_ingestion", "observability")
SECURITY_KINDS = (
    "intrusion_prevention",
    "intrusion_detection",
    "web_application_firewall",
    "endpoint_protection",
    "endpoint_detection_response",
    "antivirus",
    "file_integrity_monitoring",
)
PROTECTION_KINDS = ("backup", "restore", "disaster_recovery")
IDENTITY_KINDS = ("single_sign_on", "iam_policy", "directory", "authentication")
OPERATIONS_KINDS = (
    "patching",
    "vulnerability_scanning",
    "configuration_management",
    "support",
)
TASK_STATUSES = ("open", "completed", "cancelled")
ACCOUNT_STATUSES = ("open", "closed")
RECOMMENDATION_KINDS = ("resource_optimization", "ai_recommendation")


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


def _units(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be an integer >= 0 (service units)" % field)
    return value


def _period(value, field):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise ValidationError("%s must be a YYYY-MM period: %r" % (field, value))
    return value


def _fail_closed(method):
    """Wrap a store operation so an audit write failure rolls it back.

    High-baseline uplift (AU-5) [L3]: the wrapped method runs against a
    snapshot of the store state; if it raises
    :class:`~cloudinfra.errors.AuditWriteError` (its audit entry could
    not be durably recorded), the snapshot is restored and the error
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


class CloudInfraStore:
    """In-memory Cloud Infrastructure & Hosting records store with
    an optional audit log."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._organizations = {}
        self._tenancies = {}
        self._environments = {}
        self._providers = {}
        self._deployments = {}
        self._templates = {}
        self._monitors = {}
        self._security_services = {}
        self._protection_records = {}
        self._identity_configs = {}
        self._operations_tasks = {}
        self._accounts = {}
        self._utilization = {}
        self._recommendations = {}
        self._counters = {}

    # -- internal helpers -------------------------------------------------

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
            copy.deepcopy(self._tenancies),
            copy.deepcopy(self._environments),
            copy.deepcopy(self._providers),
            copy.deepcopy(self._deployments),
            copy.deepcopy(self._templates),
            copy.deepcopy(self._monitors),
            copy.deepcopy(self._security_services),
            copy.deepcopy(self._protection_records),
            copy.deepcopy(self._identity_configs),
            copy.deepcopy(self._operations_tasks),
            copy.deepcopy(self._accounts),
            copy.deepcopy(self._utilization),
            copy.deepcopy(self._recommendations),
            dict(self._counters),
        )

    def _restore_state(self, snapshot):
        """Restore a snapshot taken by :meth:`_snapshot_state` [L3]."""
        (
            self._organizations,
            self._tenancies,
            self._environments,
            self._providers,
            self._deployments,
            self._templates,
            self._monitors,
            self._security_services,
            self._protection_records,
            self._identity_configs,
            self._operations_tasks,
            self._accounts,
            self._utilization,
            self._recommendations,
            self._counters,
        ) = snapshot

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

    def _entity_in(self, collection, org_id, entity_id, label):
        entity = collection.get(entity_id)
        if entity is None or entity["org_id"] != org_id:
            raise NotFoundError(
                "no such %s in organization %s: %r" % (label, org_id, entity_id)
            )
        return entity

    def _check_ref_free(self, collection, org_id, field, value, label):
        for existing in collection.values():
            if existing["org_id"] == org_id and existing[field] == value:
                raise ValidationError(
                    "%s already exists in organization %s: %r"
                    % (label, org_id, value)
                )

    # -- organizations ------------------------------------------------------

    @_fail_closed
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

    @_fail_closed
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

    # -- tenancies ----------------------------------------------------------

    def _tenancy_view(self, tenancy):
        view = dict(tenancy)
        deployments = [d for d in self._deployments.values()
                       if d["tenancy_id"] == tenancy["id"]]
        view["deployment_count"] = len(deployments)
        view["active_deployment_count"] = sum(
            1 for d in deployments if d["status"] == "active"
        )
        return view

    @_fail_closed
    def create_tenancy(self, org_id, tenancy_ref, label, hosting_model,
                       actor, provider_id=None):
        """Record a cloud tenancy under a hosting model (Treasury
        Cloud's two named models, Rackspace's enclaves, and the
        shared-service form). Recording a tenancy provisions
        nothing."""
        self._scoped_org(org_id, actor, "tenancy_write")
        _text(tenancy_ref, "tenancy_ref")
        _text(label, "label")
        if hosting_model not in HOSTING_MODELS:
            raise ValidationError(
                "hosting_model must be one of %s: %r"
                % (", ".join(HOSTING_MODELS), hosting_model)
            )
        if provider_id is not None:
            self._entity_in(self._providers, org_id, provider_id, "provider")
        with self._lock:
            self._check_ref_free(self._tenancies, org_id, "tenancy_ref",
                                 tenancy_ref, "tenancy_ref")
            tenancy = {
                "id": self._mint("ten-"),
                "org_id": org_id,
                "tenancy_ref": tenancy_ref,
                "label": label,
                "hosting_model": hosting_model,
                "provider_id": provider_id,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._tenancies[tenancy["id"]] = tenancy
        self._record(actor, "tenancy_create", tenancy["id"],
                     {"tenancy_ref": tenancy_ref, "hosting_model": hosting_model})
        return self._tenancy_view(tenancy)

    def list_tenancies(self, org_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return [self._tenancy_view(t) for t in self._tenancies.values()
                if t["org_id"] == org_id]

    def get_tenancy(self, org_id, tenancy_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return self._tenancy_view(
            self._entity_in(self._tenancies, org_id, tenancy_id, "tenancy"))

    # -- environments ---------------------------------------------------------

    @_fail_closed
    def create_environment(self, org_id, environment_ref, label, actor,
                           tenancy_id=None, residency_label=None):
        """Record a hosting environment. The optional
        ``residency_label`` is caller-stated (for example a U.S.
        soil residency label as the forks state it); the build
        verifies no residency claim."""
        self._scoped_org(org_id, actor, "environment_write")
        _text(environment_ref, "environment_ref")
        _text(label, "label")
        _optional_text(residency_label, "residency_label")
        if tenancy_id is not None:
            self._entity_in(self._tenancies, org_id, tenancy_id, "tenancy")
        with self._lock:
            self._check_ref_free(self._environments, org_id, "environment_ref",
                                 environment_ref, "environment_ref")
            environment = {
                "id": self._mint("env-"),
                "org_id": org_id,
                "tenancy_id": tenancy_id,
                "environment_ref": environment_ref,
                "label": label,
                "residency_label": residency_label,
                "status": "provisioned",
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._environments[environment["id"]] = environment
        self._record(actor, "environment_create", environment["id"],
                     {"environment_ref": environment_ref})
        return dict(environment)

    def list_environments(self, org_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return [dict(e) for e in self._environments.values()
                if e["org_id"] == org_id]

    def get_environment(self, org_id, environment_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return dict(self._entity_in(self._environments, org_id,
                                    environment_id, "environment"))

    @_fail_closed
    def set_environment_status(self, org_id, environment_id, status, actor):
        """Guarded lifecycle: provisioned -> active -> retired
        (provisioned may also retire directly); retired is
        terminal."""
        self._scoped_org(org_id, actor, "environment_write")
        environment = self._entity_in(self._environments, org_id,
                                      environment_id, "environment")
        allowed = {
            "provisioned": ("active", "retired"),
            "active": ("retired",),
            "retired": (),
        }
        if status not in allowed[environment["status"]]:
            raise ValidationError(
                "environment %s cannot move from %s to %s"
                % (environment_id, environment["status"], status)
            )
        with self._lock:
            environment["status"] = status
        self._record(actor, "environment_status", environment_id,
                     {"status": status})
        return dict(environment)

    # -- providers ------------------------------------------------------------

    @_fail_closed
    def register_provider(self, org_id, provider_ref, label, actor):
        """Register an underlying infrastructure provider the
        organization's hosting runs on (the forks name public cloud
        providers and infrastructure by name). A registration names
        a provider; it integrates with nothing."""
        self._scoped_org(org_id, actor, "provider_write")
        _text(provider_ref, "provider_ref")
        _text(label, "label")
        with self._lock:
            self._check_ref_free(self._providers, org_id, "provider_ref",
                                 provider_ref, "provider_ref")
            provider = {
                "id": self._mint("prv-"),
                "org_id": org_id,
                "provider_ref": provider_ref,
                "label": label,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._providers[provider["id"]] = provider
        self._record(actor, "provider_register", provider["id"],
                     {"provider_ref": provider_ref})
        return dict(provider)

    def list_providers(self, org_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return [dict(p) for p in self._providers.values()
                if p["org_id"] == org_id]

    def get_provider(self, org_id, provider_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return dict(self._entity_in(self._providers, org_id,
                                    provider_id, "provider"))

    # -- deployments ----------------------------------------------------------

    def _check_deployment_slot(self, tenancy_id, workload_ref,
                               exclude_deployment_id=None):
        """The deployment slot rule: within one tenancy, at most one
        deployment of a given workload reference may be active at a
        time. Raises ValidationError on a violation."""
        for existing in self._deployments.values():
            if (
                existing["tenancy_id"] == tenancy_id
                and existing["workload_ref"] == workload_ref
                and existing["status"] == "active"
                and existing["id"] != exclude_deployment_id
            ):
                raise ValidationError(
                    "workload %r already has an active deployment (%s) "
                    "in tenancy %s"
                    % (workload_ref, existing["id"], tenancy_id)
                )

    @_fail_closed
    def create_deployment(self, org_id, tenancy_id, deployment_ref,
                          workload_ref, actor, environment_id=None,
                          template_id=None, encryption_label=None):
        """Record a hosted deployment of a workload (an opaque
        reference) inside a tenancy. Recording a deployment
        deploys nothing. The optional ``encryption_label`` is
        caller-stated (for example an encryption-at-rest label as
        the forks state it); the build performs no cryptography."""
        self._scoped_org(org_id, actor, "deployment_write")
        _text(deployment_ref, "deployment_ref")
        _text(workload_ref, "workload_ref")
        _optional_text(encryption_label, "encryption_label")
        self._entity_in(self._tenancies, org_id, tenancy_id, "tenancy")
        if environment_id is not None:
            self._entity_in(self._environments, org_id, environment_id,
                            "environment")
        if template_id is not None:
            self._entity_in(self._templates, org_id, template_id, "template")
        with self._lock:
            self._check_ref_free(self._deployments, org_id, "deployment_ref",
                                 deployment_ref, "deployment_ref")
            deployment = {
                "id": self._mint("dep-"),
                "org_id": org_id,
                "tenancy_id": tenancy_id,
                "environment_id": environment_id,
                "deployment_ref": deployment_ref,
                "workload_ref": workload_ref,
                "template_id": template_id,
                "encryption_label": encryption_label,
                "status": "recorded",
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._deployments[deployment["id"]] = deployment
        self._record(actor, "deployment_create", deployment["id"],
                     {"deployment_ref": deployment_ref,
                      "workload_ref": workload_ref})
        return dict(deployment)

    def list_deployments(self, org_id, actor, tenancy_id=None):
        self._scoped_org(org_id, actor, "org_read")
        result = [dict(d) for d in self._deployments.values()
                  if d["org_id"] == org_id]
        if tenancy_id is not None:
            result = [d for d in result if d["tenancy_id"] == tenancy_id]
        return result

    def get_deployment(self, org_id, deployment_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return dict(self._entity_in(self._deployments, org_id,
                                    deployment_id, "deployment"))

    @_fail_closed
    def activate_deployment(self, org_id, deployment_id, actor):
        """Move a recorded deployment to active. The deployment
        slot seam runs first: another active deployment of the same
        workload in the same tenancy refuses the activation whole —
        nothing changes."""
        self._scoped_org(org_id, actor, "deployment_write")
        deployment = self._entity_in(self._deployments, org_id,
                                     deployment_id, "deployment")
        if deployment["status"] != "recorded":
            raise ValidationError(
                "deployment %s cannot activate from %s"
                % (deployment_id, deployment["status"])
            )
        with self._lock:
            self._check_deployment_slot(
                deployment["tenancy_id"], deployment["workload_ref"],
                exclude_deployment_id=deployment_id)
            deployment["status"] = "active"
        self._record(actor, "deployment_status", deployment_id,
                     {"status": "active"})
        return dict(deployment)

    @_fail_closed
    def stop_deployment(self, org_id, deployment_id, actor):
        """Move an active deployment to stopped (terminal for this
        substrate)."""
        self._scoped_org(org_id, actor, "deployment_write")
        deployment = self._entity_in(self._deployments, org_id,
                                     deployment_id, "deployment")
        if deployment["status"] != "active":
            raise ValidationError(
                "deployment %s cannot stop from %s"
                % (deployment_id, deployment["status"])
            )
        with self._lock:
            deployment["status"] = "stopped"
        self._record(actor, "deployment_status", deployment_id,
                     {"status": "stopped"})
        return dict(deployment)

    # -- deployment templates ---------------------------------------------------

    @_fail_closed
    def register_template(self, org_id, template_ref, label, settings_text,
                          actor):
        """Register a deployment template. The settings text is
        stored verbatim as a record; this substrate has no
        operation that executes, applies, or launches a template —
        the registry records, it does not run."""
        self._scoped_org(org_id, actor, "template_write")
        _text(template_ref, "template_ref")
        _text(label, "label")
        _text(settings_text, "settings_text")
        with self._lock:
            self._check_ref_free(self._templates, org_id, "template_ref",
                                 template_ref, "template_ref")
            template = {
                "id": self._mint("tpl-"),
                "org_id": org_id,
                "template_ref": template_ref,
                "label": label,
                "settings_text": settings_text,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._templates[template["id"]] = template
        self._record(actor, "template_register", template["id"],
                     {"template_ref": template_ref})
        return dict(template)

    def list_templates(self, org_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return [dict(t) for t in self._templates.values()
                if t["org_id"] == org_id]

    def get_template(self, org_id, template_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return dict(self._entity_in(self._templates, org_id,
                                    template_id, "template"))

    # -- monitoring records -------------------------------------------------------

    @_fail_closed
    def register_monitor(self, org_id, monitor_ref, kind, target_ref, label,
                         actor):
        """Record a monitoring arrangement over an opaque target
        reference (the forks name continuous monitoring, network
        monitoring, log ingestion and monitoring, and
        observability). The record collects no telemetry; actual
        monitoring is an engine outside this substrate."""
        self._scoped_org(org_id, actor, "service_write")
        _text(monitor_ref, "monitor_ref")
        _text(target_ref, "target_ref")
        _text(label, "label")
        if kind not in MONITOR_KINDS:
            raise ValidationError(
                "kind must be one of %s: %r" % (", ".join(MONITOR_KINDS), kind)
            )
        with self._lock:
            self._check_ref_free(self._monitors, org_id, "monitor_ref",
                                 monitor_ref, "monitor_ref")
            monitor = {
                "id": self._mint("mon-"),
                "org_id": org_id,
                "monitor_ref": monitor_ref,
                "kind": kind,
                "target_ref": target_ref,
                "label": label,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._monitors[monitor["id"]] = monitor
        self._record(actor, "monitor_register", monitor["id"],
                     {"monitor_ref": monitor_ref, "kind": kind})
        return dict(monitor)

    def list_monitors(self, org_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return [dict(m) for m in self._monitors.values()
                if m["org_id"] == org_id]

    def get_monitor(self, org_id, monitor_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return dict(self._entity_in(self._monitors, org_id,
                                    monitor_id, "monitor"))

    # -- platform security service records -----------------------------------------

    @_fail_closed
    def register_security_service(self, org_id, service_ref, kind, target_ref,
                                  label, actor):
        """Record a platform security service arrangement over an
        opaque target reference (the forks name intrusion
        prevention and detection, web application firewall,
        endpoint protection and detection-and-response, anti-virus,
        and file integrity monitoring). The record operates no
        engine."""
        self._scoped_org(org_id, actor, "service_write")
        _text(service_ref, "service_ref")
        _text(target_ref, "target_ref")
        _text(label, "label")
        if kind not in SECURITY_KINDS:
            raise ValidationError(
                "kind must be one of %s: %r" % (", ".join(SECURITY_KINDS), kind)
            )
        with self._lock:
            self._check_ref_free(self._security_services, org_id, "service_ref",
                                 service_ref, "service_ref")
            service = {
                "id": self._mint("sec-"),
                "org_id": org_id,
                "service_ref": service_ref,
                "kind": kind,
                "target_ref": target_ref,
                "label": label,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._security_services[service["id"]] = service
        self._record(actor, "security_service_register", service["id"],
                     {"service_ref": service_ref, "kind": kind})
        return dict(service)

    def list_security_services(self, org_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return [dict(s) for s in self._security_services.values()
                if s["org_id"] == org_id]

    def get_security_service(self, org_id, service_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return dict(self._entity_in(self._security_services, org_id,
                                    service_id, "security service"))

    # -- backup & recovery records ----------------------------------------------------

    @_fail_closed
    def record_protection(self, org_id, protection_ref, kind, target_ref,
                          label, actor, occurred_at=None):
        """Record a backup, restore, or disaster-recovery event or
        arrangement over an opaque target reference. The record
        backs nothing up and restores nothing; execution is an
        engine outside this substrate."""
        self._scoped_org(org_id, actor, "service_write")
        _text(protection_ref, "protection_ref")
        _text(target_ref, "target_ref")
        _text(label, "label")
        _optional_text(occurred_at, "occurred_at")
        if occurred_at is not None:
            _parse_moment(occurred_at, "occurred_at")
        if kind not in PROTECTION_KINDS:
            raise ValidationError(
                "kind must be one of %s: %r"
                % (", ".join(PROTECTION_KINDS), kind)
            )
        with self._lock:
            self._check_ref_free(self._protection_records, org_id,
                                 "protection_ref", protection_ref,
                                 "protection_ref")
            record = {
                "id": self._mint("pro-"),
                "org_id": org_id,
                "protection_ref": protection_ref,
                "kind": kind,
                "target_ref": target_ref,
                "label": label,
                "occurred_at": occurred_at,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._protection_records[record["id"]] = record
        self._record(actor, "protection_record", record["id"],
                     {"protection_ref": protection_ref, "kind": kind})
        return dict(record)

    def list_protection_records(self, org_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return [dict(r) for r in self._protection_records.values()
                if r["org_id"] == org_id]

    def get_protection_record(self, org_id, record_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return dict(self._entity_in(self._protection_records, org_id,
                                    record_id, "protection record"))

    # -- identity configuration records -------------------------------------------------

    @_fail_closed
    def register_identity_config(self, org_id, identity_ref, kind, label,
                                 actor, provider_ref=None):
        """Record an identity configuration (single sign-on, IAM
        policy, directory, or authentication configuration, as the
        forks name them). The record names a configuration kind and
        a label only — there is no field that can hold a credential
        or secret, and the identity provider itself stays with the
        embedding organization (IA-2)."""
        self._scoped_org(org_id, actor, "service_write")
        _text(identity_ref, "identity_ref")
        _text(label, "label")
        _optional_text(provider_ref, "provider_ref")
        if kind not in IDENTITY_KINDS:
            raise ValidationError(
                "kind must be one of %s: %r"
                % (", ".join(IDENTITY_KINDS), kind)
            )
        with self._lock:
            self._check_ref_free(self._identity_configs, org_id, "identity_ref",
                                 identity_ref, "identity_ref")
            config = {
                "id": self._mint("idc-"),
                "org_id": org_id,
                "identity_ref": identity_ref,
                "kind": kind,
                "label": label,
                "provider_ref": provider_ref,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._identity_configs[config["id"]] = config
        self._record(actor, "identity_config_register", config["id"],
                     {"identity_ref": identity_ref, "kind": kind})
        return dict(config)

    def list_identity_configs(self, org_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return [dict(c) for c in self._identity_configs.values()
                if c["org_id"] == org_id]

    def get_identity_config(self, org_id, config_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return dict(self._entity_in(self._identity_configs, org_id,
                                    config_id, "identity configuration"))

    # -- operations task records ------------------------------------------------------

    def _task_view(self, task, now):
        view = dict(task)
        view["overdue"] = bool(
            task["status"] == "open"
            and _parse_moment(task["due_at"], "due_at") < now
        )
        return view

    @_fail_closed
    def create_operations_task(self, org_id, task_ref, kind, target_ref,
                               label, due_at, actor):
        """Record a managed-operations task (the forks name OS
        patching, vulnerability scanning, configuration management,
        and operations support) with a required due date. Recording
        a task executes nothing."""
        self._scoped_org(org_id, actor, "operations_write")
        _text(task_ref, "task_ref")
        _text(target_ref, "target_ref")
        _text(label, "label")
        _parse_moment(due_at, "due_at")
        if kind not in OPERATIONS_KINDS:
            raise ValidationError(
                "kind must be one of %s: %r"
                % (", ".join(OPERATIONS_KINDS), kind)
            )
        with self._lock:
            self._check_ref_free(self._operations_tasks, org_id, "task_ref",
                                 task_ref, "task_ref")
            task = {
                "id": self._mint("ops-"),
                "org_id": org_id,
                "task_ref": task_ref,
                "kind": kind,
                "target_ref": target_ref,
                "label": label,
                "due_at": due_at,
                "status": "open",
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._operations_tasks[task["id"]] = task
        self._record(actor, "operations_task_create", task["id"],
                     {"task_ref": task_ref, "kind": kind})
        return self._task_view(task, _utc_now())

    def list_operations_tasks(self, org_id, actor, at=None):
        self._scoped_org(org_id, actor, "org_read")
        now = _parse_moment(at, "at") if at is not None else _utc_now()
        return [self._task_view(t, now) for t in self._operations_tasks.values()
                if t["org_id"] == org_id]

    def get_operations_task(self, org_id, task_id, actor, at=None):
        self._scoped_org(org_id, actor, "org_read")
        now = _parse_moment(at, "at") if at is not None else _utc_now()
        return self._task_view(
            self._entity_in(self._operations_tasks, org_id, task_id,
                            "operations task"), now)

    @_fail_closed
    def set_operations_task_status(self, org_id, task_id, status, actor):
        """Guarded lifecycle: open -> completed / cancelled; both
        are terminal."""
        self._scoped_org(org_id, actor, "operations_write")
        task = self._entity_in(self._operations_tasks, org_id, task_id,
                               "operations task")
        if task["status"] != "open" or status not in ("completed", "cancelled"):
            raise ValidationError(
                "operations task %s cannot move from %s to %s"
                % (task_id, task["status"], status)
            )
        with self._lock:
            task["status"] = status
        self._record(actor, "operations_task_status", task_id,
                     {"status": status})
        return self._task_view(task, _utc_now())

    # -- cloud accounts & utilization ---------------------------------------------------

    @_fail_closed
    def open_account(self, org_id, account_ref, label, actor):
        """Open a cloud account record (Treasury Cloud names account
        provisioning for its tenant agencies). Opening a record
        provisions no account."""
        self._scoped_org(org_id, actor, "operations_write")
        _text(account_ref, "account_ref")
        _text(label, "label")
        with self._lock:
            self._check_ref_free(self._accounts, org_id, "account_ref",
                                 account_ref, "account_ref")
            account = {
                "id": self._mint("acc-"),
                "org_id": org_id,
                "account_ref": account_ref,
                "label": label,
                "status": "open",
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._accounts[account["id"]] = account
        self._record(actor, "account_open", account["id"],
                     {"account_ref": account_ref})
        return dict(account)

    def list_accounts(self, org_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return [dict(a) for a in self._accounts.values()
                if a["org_id"] == org_id]

    def get_account(self, org_id, account_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return dict(self._entity_in(self._accounts, org_id,
                                    account_id, "account"))

    @_fail_closed
    def close_account(self, org_id, account_id, actor):
        """Guarded lifecycle: open -> closed; closed is terminal."""
        self._scoped_org(org_id, actor, "operations_write")
        account = self._entity_in(self._accounts, org_id, account_id, "account")
        if account["status"] != "open":
            raise ValidationError(
                "account %s cannot close from %s" % (account_id, account["status"])
            )
        with self._lock:
            account["status"] = "closed"
        self._record(actor, "account_status", account_id, {"status": "closed"})
        return dict(account)

    @_fail_closed
    def record_utilization(self, org_id, account_id, period, units, actor):
        """Record one period of service utilization for an account,
        in integer service units (utilization transparency is the
        forks' own function — Treasury Cloud names FinOps
        dashboards for resource utilization). One record per
        account per period. Units are counts, never money:
        booleans, floats, and strings are rejected at the
        boundary."""
        self._scoped_org(org_id, actor, "operations_write")
        _period(period, "period")
        _units(units, "units")
        account = self._entity_in(self._accounts, org_id, account_id, "account")
        if account["status"] != "open":
            raise ValidationError(
                "account %s is closed; utilization cannot be recorded"
                % account_id
            )
        with self._lock:
            for existing in self._utilization.values():
                if (existing["account_id"] == account_id
                        and existing["period"] == period):
                    raise ValidationError(
                        "utilization already recorded for account %s in %s"
                        % (account_id, period)
                    )
            record = {
                "id": self._mint("utl-"),
                "org_id": org_id,
                "account_id": account_id,
                "period": period,
                "units": units,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._utilization[record["id"]] = record
        self._record(actor, "utilization_record", record["id"],
                     {"account_id": account_id, "period": period,
                      "units": units})
        return dict(record)

    def list_utilization(self, org_id, actor, account_id=None):
        self._scoped_org(org_id, actor, "org_read")
        result = [dict(u) for u in self._utilization.values()
                  if u["org_id"] == org_id]
        if account_id is not None:
            result = [u for u in result if u["account_id"] == account_id]
        return result

    # -- recommendation records --------------------------------------------------------------

    @_fail_closed
    def record_recommendation(self, org_id, recommendation_ref, kind,
                              target_ref, label, actor, detail=None):
        """Record a recommendation issued elsewhere (IBM names
        dynamic resource allocation and AI-driven recommendations).
        The detail text is stored verbatim as the record of what was
        recommended; this substrate generates no recommendations —
        the engines are outside it."""
        self._scoped_org(org_id, actor, "operations_write")
        _text(recommendation_ref, "recommendation_ref")
        _text(target_ref, "target_ref")
        _text(label, "label")
        _optional_text(detail, "detail")
        if kind not in RECOMMENDATION_KINDS:
            raise ValidationError(
                "kind must be one of %s: %r"
                % (", ".join(RECOMMENDATION_KINDS), kind)
            )
        with self._lock:
            self._check_ref_free(self._recommendations, org_id,
                                 "recommendation_ref", recommendation_ref,
                                 "recommendation_ref")
            record = {
                "id": self._mint("rec-"),
                "org_id": org_id,
                "recommendation_ref": recommendation_ref,
                "kind": kind,
                "target_ref": target_ref,
                "label": label,
                "detail": detail,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._recommendations[record["id"]] = record
        self._record(actor, "recommendation_record", record["id"],
                     {"recommendation_ref": recommendation_ref, "kind": kind})
        return dict(record)

    def list_recommendations(self, org_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return [dict(r) for r in self._recommendations.values()
                if r["org_id"] == org_id]

    def get_recommendation(self, org_id, record_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return dict(self._entity_in(self._recommendations, org_id,
                                    record_id, "recommendation"))

    # -- reporting ----------------------------------------------------------------------------

    def org_report(self, org_id, actor, at=None):
        """Counts and unit sums for one organization, computed on
        read. Counts only: no scores and no money exist anywhere in
        this substrate to report."""
        org = self._scoped_org(org_id, actor, "report_read")
        now = _parse_moment(at, "at") if at is not None else _utc_now()

        def mine(collection):
            return [e for e in collection.values() if e["org_id"] == org_id]

        def by(records, field):
            counts = {}
            for record in records:
                counts[record[field]] = counts.get(record[field], 0) + 1
            return counts

        tenancies = mine(self._tenancies)
        environments = mine(self._environments)
        deployments = mine(self._deployments)
        monitors = mine(self._monitors)
        security = mine(self._security_services)
        protection = mine(self._protection_records)
        identity = mine(self._identity_configs)
        tasks = mine(self._operations_tasks)
        accounts = mine(self._accounts)
        utilization = mine(self._utilization)
        recommendations = mine(self._recommendations)
        units_by_period = {}
        for record in utilization:
            units_by_period[record["period"]] = (
                units_by_period.get(record["period"], 0) + record["units"]
            )
        return {
            "org_id": org_id,
            "org_ref": org["org_ref"],
            "tenancies": {
                "total": len(tenancies),
                "by_hosting_model": by(tenancies, "hosting_model"),
            },
            "environments": {
                "total": len(environments),
                "by_status": by(environments, "status"),
            },
            "providers": {"total": len(mine(self._providers))},
            "deployments": {
                "total": len(deployments),
                "by_status": by(deployments, "status"),
            },
            "templates": {"total": len(mine(self._templates))},
            "monitors": {"total": len(monitors), "by_kind": by(monitors, "kind")},
            "security_services": {
                "total": len(security),
                "by_kind": by(security, "kind"),
            },
            "protection_records": {
                "total": len(protection),
                "by_kind": by(protection, "kind"),
            },
            "identity_configs": {
                "total": len(identity),
                "by_kind": by(identity, "kind"),
            },
            "operations_tasks": {
                "total": len(tasks),
                "by_status": by(tasks, "status"),
                "overdue": sum(
                    1 for t in tasks if self._task_view(t, now)["overdue"]
                ),
            },
            "accounts": {
                "total": len(accounts),
                "by_status": by(accounts, "status"),
            },
            "utilization": {
                "records": len(utilization),
                "units_by_period": units_by_period,
            },
            "recommendations": {
                "total": len(recommendations),
                "by_kind": by(recommendations, "kind"),
            },
        }

    # -- search -----------------------------------------------------------------------------------

    def search(self, org_id, query, actor):
        """Literal substring search over the organization's record
        references, labels, and kinds. Membership-scoped: other
        organizations' records are never visible."""
        self._scoped_org(org_id, actor, "org_read")
        _text(query, "query")
        needle = query.lower()

        def hit(record, fields):
            return any(
                needle in str(record.get(field) or "").lower()
                for field in fields
            )

        def collect(collection, fields):
            return [
                dict(e) for e in collection.values()
                if e["org_id"] == org_id and hit(e, fields)
            ]

        tenancies = [
            self._tenancy_view(t) for t in self._tenancies.values()
            if t["org_id"] == org_id
            and hit(t, ("tenancy_ref", "label", "hosting_model"))
        ]
        return {
            "tenancies": tenancies,
            "environments": collect(
                self._environments,
                ("environment_ref", "label", "residency_label", "status")),
            "providers": collect(self._providers, ("provider_ref", "label")),
            "deployments": collect(
                self._deployments,
                ("deployment_ref", "workload_ref", "encryption_label", "status")),
            "templates": collect(self._templates, ("template_ref", "label")),
            "monitors": collect(
                self._monitors, ("monitor_ref", "kind", "target_ref", "label")),
            "security_services": collect(
                self._security_services,
                ("service_ref", "kind", "target_ref", "label")),
            "protection_records": collect(
                self._protection_records,
                ("protection_ref", "kind", "target_ref", "label")),
            "identity_configs": collect(
                self._identity_configs,
                ("identity_ref", "kind", "label", "provider_ref")),
            "operations_tasks": collect(
                self._operations_tasks,
                ("task_ref", "kind", "target_ref", "label", "status")),
            "accounts": collect(
                self._accounts, ("account_ref", "label", "status")),
            "recommendations": collect(
                self._recommendations,
                ("recommendation_ref", "kind", "target_ref", "label")),
        }
