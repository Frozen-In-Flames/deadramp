"""Final GAPS batch singleton unit for System Administration L2.

Clean-room, standard-library-only extension surface for the 6 open
entries of the GAPS.md section "Singleton 54 -- System Administration
L2 (1 fork, new category)" (inventory idx 515-520; see
``BATCH-SINGLETON.md`` in the group directory for the per-entry
disposition). This module is a wrapper around
:class:`SysadminStore`; every pre-existing module -- the founding
core and the remainder-addition unit's ``addition.py`` alike -- is
untouched and byte-identical to its shipped build. This is the third
extension surface in the directory and keeps its own module, its own
test module, and its own batch note.

Honesty of form, per the batch brief and this group's founding
doctrine: the six entries are the founding fork's own operations --
the work and engines behind the records Core already holds. They
close here as records ABOUT those operations over this group's own
substrate (customer organizations, managed systems, applications).
Records about administration are not administration: nothing in this
module administers, provisions, hosts, virtualizes, fails over, or
operates any live system or network.

- Managed administration operations close as operation DEFINITIONS
  held as data plus operation records with verbatim reported
  outcomes (``operated_here: False``, ``executed_here: False``);
  the full management itself is the operator's work, performed by
  its people and platforms elsewhere.
- System provisioning & deployment closes as a labeled reference
  implementation: provisioning-job records naming their target by
  an opaque reference (the instance does not exist yet, so there
  is no core system to bind) plus reported outcome records
  (``reference_stub: True``; ``provisioned_here: False``,
  ``deployed_here: False``).
- Application delivery & hosting runtime closes as a labeled
  reference implementation: hosting-profile records bound to a
  core application plus reported hosting records
  (``reference_stub: True``; ``hosted_here: False``,
  ``delivered_here: False``). The runtime is the CSP's
  environment; per PLATFORM-LAYER.md decision 6 the hosting
  substrate does not transfer to this build.
- The virtualization engine is the CSP's; what closes here is the
  records surface it presupposes: virtual-instance records held as
  REPORTED data (``virtualized_here: False``) with append-only
  reported state labels whose current state derives at read.
- High-availability network operation closes as redundancy
  configuration records held as data plus reported availability
  event records; a configuration's current availability state
  derives at read from its latest recorded event label
  (``operated_here: False``, ``failover_performed_here: False``)
  -- no failover is executed and no network is operated here.
- Third-party CSP hosting platforms close as labeled reference
  declarations: platform records naming the external platform by
  the same opaque ``platform_ref`` Core systems already carry,
  plus reported platform records (``reference_stub: True``;
  ``hosted_here: False``, ``operated_here: False``). The platforms
  are outside the fork's own boundary by its own statement
  (PLATFORM-LAYER.md decision 6).

Doctrines carried from the core: derived-never-stored for every
computed value (current instance / availability state, all summary
counts); opaque references only -- no entity shape has a field for
a hostname, address, credential, or any live-system identifier;
validation before mutation, so a failed operation consumes no id
and changes nothing; append-only audit on the core store's log with
``exts_``-prefixed actions for every successful extension mutation,
and denied write attempts recorded with a ``:denied`` suffix; RBAC
via :mod:`sysadmin.access` -- extension writes map to the core
``enter`` action, and organization membership (the fork's
contract-gated access boundary) is enforced by resolving the
organization through the core store on every operation.
"""

import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

OPERATION_KINDS = (
    "configure", "patch", "harden", "maintain", "administer", "other",
)
INSTANCE_STATES = (
    "reported_provisioning", "reported_running", "reported_stopped",
    "reported_terminated",
)
HA_EVENT_LABELS = (
    "reported_healthy", "reported_degraded", "reported_failover",
    "reported_recovered",
)

_REFERENCE_STATE = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _count(value, field):
    """A non-negative integer count of reported things; bools/floats rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be a non-negative integer" % (field,))
    if value < 0:
        raise ValidationError("%s must be a non-negative integer" % (field,))
    return value


class SysadminSingletonExtensions:
    """GAPS-batch singleton extension surface wrapping one store."""

    def __init__(self, store):
        self.store = store
        self._lock = threading.Lock()
        self._counters = {}
        # idx 515 -- managed administration operations
        self._operation_definitions = {}
        self._operation_records = {}
        # idx 516 -- provisioning & deployment (reference stub)
        self._provisioning_jobs = {}
        self._provisioning_outcomes = {}
        # idx 517 -- application delivery & hosting runtime (reference stub)
        self._hosting_profiles = {}
        self._hosting_reports = {}
        # idx 518 -- virtualization engine (records surface)
        self._virtual_instances = {}
        self._instance_states = {}
        # idx 519 -- high-availability network operation
        self._ha_configurations = {}
        self._ha_events = {}
        # idx 520 -- third-party CSP hosting platforms (reference stub)
        self._platform_declarations = {}
        self._platform_reports = {}

    # -- internal helpers ---------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor, action, target, details)

    def _guard(self, actor, audit_action):
        """Enforce the extension write permission before any mutation.

        Extension writes map to the core ``enter`` action. A denied
        attempt is recorded on the audit log with a ``:denied``
        suffix before the error propagates; a missing actor is
        denied outright. A plain string carries identity but no
        role (the service layer enforces its role), matching the
        core convention.
        """
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for 'enter'")
        if hasattr(actor, "role"):
            try:
                require(actor, "enter")
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": "enter"})
                raise

    def _org(self, actor, org_id):
        """Resolve an organization through the core store.

        The core enforces the ``read`` role permission and the
        organization membership boundary (or platform admin) and
        raises NotFoundError for an unknown organization.
        """
        return self.store.get_organization(actor, org_id)

    def _system_in_org(self, actor, org_id, system_id):
        system = self.store.get_system(actor, system_id)
        if system["org_id"] != org_id:
            raise ValidationError("system belongs to another organization")
        return system

    def _application_in_org(self, actor, org_id, application_id):
        application = self.store.get_application(actor, application_id)
        if application["org_id"] != org_id:
            raise ValidationError(
                "application belongs to another organization")
        return application

    @staticmethod
    def _latest_state_label(state_records):
        """The current state of a record: its latest recorded label.

        State records are append-only and kept in recording order;
        the current state is the LAST label recorded, or
        ``recorded`` when no state has been recorded yet. This
        derivation is this unit's fresh negative-control seam (see
        tests/README.md): reading the earliest label instead would
        resurrect superseded states.
        """
        if not state_records:
            return "recorded"
        return state_records[-1]["state_label"]

    def _state_view(self, record, state_records):
        view = dict(record)
        view["current_state"] = self._latest_state_label(state_records)
        return view

    def _states_for(self, table, key, record_id):
        return [r for r in table.values() if r[key] == record_id]

    def _record_state(self, actor, org_id, table, prefix, key, record_id,
                      state_label, allowed, action):
        self._guard(actor, action)
        self._org(actor, org_id)
        if state_label not in allowed:
            raise ValidationError(
                "state_label must be one of %r" % (allowed,))
        with self._lock:
            record = {
                "id": self._mint(prefix),
                "org_id": org_id,
                key: record_id,
                "state_label": state_label,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            table[record["id"]] = record
        self._audit(actor, action, record["id"],
                    {"state_label": state_label})
        return dict(record)

    # -- idx 515: managed OS & services administration operations -------------

    def create_operation_definition(self, actor, org_id, ref, label,
                                    operation_kind):
        """Record an administration-operation definition as data.

        The definition describes a class of management work the
        operator performs; holding it performs none of it
        (``executed_here: False``).
        """
        action = "exts_operation_definition_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        if operation_kind not in OPERATION_KINDS:
            raise ValidationError(
                "operation_kind must be one of %r" % (OPERATION_KINDS,))
        with self._lock:
            for existing in self._operation_definitions.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "operation definition ref already exists in this "
                        "organization: %r" % (ref,))
            record = {
                "id": self._mint("aod-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "operation_kind": operation_kind,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._operation_definitions[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _operation_definition(self, definition_id):
        record = self._operation_definitions.get(definition_id)
        if record is None:
            raise NotFoundError(
                "no such operation definition: %r" % (definition_id,))
        return record

    def get_operation_definition(self, actor, definition_id):
        record = self._operation_definition(definition_id)
        self._org(actor, record["org_id"])
        return dict(record)

    def list_operation_definitions(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._operation_definitions.values()
                if r["org_id"] == org_id]

    def record_admin_operation(self, actor, org_id, definition_id, system_id,
                               outcome_label):
        """Record one performed-elsewhere administration operation.

        The operation record is the records form of management work
        the operator's people and platforms carried out against a
        core managed system; its outcome is carried verbatim and
        nothing was operated here (``operated_here: False``).
        Recording it alters no system record.
        """
        action = "exts_admin_operation_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        definition = self._operation_definition(definition_id)
        if definition["org_id"] != org_id:
            raise ValidationError(
                "operation definition belongs to another organization")
        self._system_in_org(actor, org_id, system_id)
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("aop-"),
                "org_id": org_id,
                "definition_id": definition_id,
                "system_id": system_id,
                "outcome_label": outcome_label,
                "operated_here": False,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._operation_records[record["id"]] = record
        self._audit(actor, action, record["id"],
                    {"definition_id": definition_id})
        return dict(record)

    def list_admin_operations(self, actor, org_id, definition_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._operation_records.values()
                if r["org_id"] == org_id
                and (definition_id is None
                     or r["definition_id"] == definition_id)]

    def admin_operations_summary(self, actor, org_id):
        """Counts only, derived at read: definitions by kind,
        operations by verbatim outcome label."""
        self._org(actor, org_id)
        by_kind = {kind: 0 for kind in OPERATION_KINDS}
        for record in self._operation_definitions.values():
            if record["org_id"] == org_id:
                by_kind[record["operation_kind"]] += 1
        by_outcome = {}
        operations = 0
        for record in self._operation_records.values():
            if record["org_id"] == org_id:
                operations += 1
                by_outcome[record["outcome_label"]] = \
                    by_outcome.get(record["outcome_label"], 0) + 1
        return {
            "org_id": org_id,
            "operation_definitions": sum(by_kind.values()),
            "definitions_by_kind": by_kind,
            "admin_operations": operations,
            "operations_by_outcome": by_outcome,
        }

    # -- idx 516: system provisioning & deployment (reference stub) ------------

    def create_provisioning_job(self, actor, org_id, ref, label, target_ref):
        """Record a provisioning job as a labeled reference.

        Reference implementation only: nothing is provisioned or
        deployed here (``provisioned_here: False``,
        ``deployed_here: False``). ``target_ref`` is an opaque
        caller-supplied reference to the instance the operator's
        platform would stand up; it names no core system, because
        the system does not exist until the platform creates it.
        """
        action = "exts_provisioning_job_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        _text(target_ref, "target_ref")
        with self._lock:
            record = {
                "id": self._mint("pvj-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "target_ref": target_ref,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "provisioned_here": False,
                "deployed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._provisioning_jobs[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _provisioning_job(self, job_id):
        record = self._provisioning_jobs.get(job_id)
        if record is None:
            raise NotFoundError("no such provisioning job: %r" % (job_id,))
        return record

    def record_provisioning_outcome(self, actor, org_id, job_id, outcome_label,
                                    reported_count=None):
        """Record a provisioning job's verbatim reported outcome.

        ``reported_count`` is the platform's own reported count of
        instances stood up, carried as reported data; it is never
        derived or checked against anything here.
        """
        action = "exts_provisioning_outcome_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        job = self._provisioning_job(job_id)
        if job["org_id"] != org_id:
            raise ValidationError(
                "provisioning job belongs to another organization")
        _text(outcome_label, "outcome_label")
        if reported_count is not None:
            _count(reported_count, "reported_count")
        with self._lock:
            record = {
                "id": self._mint("pvo-"),
                "org_id": org_id,
                "job_id": job_id,
                "outcome_label": outcome_label,
                "reported_count": reported_count,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "provisioned_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._provisioning_outcomes[record["id"]] = record
        self._audit(actor, action, record["id"], {"job_id": job_id})
        return dict(record)

    def list_provisioning_jobs(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._provisioning_jobs.values()
                if r["org_id"] == org_id]

    def list_provisioning_outcomes(self, actor, org_id, job_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._provisioning_outcomes.values()
                if r["org_id"] == org_id
                and (job_id is None or r["job_id"] == job_id)]

    # -- idx 517: application delivery & hosting runtime (reference stub) -------

    def create_hosting_profile(self, actor, org_id, ref, label,
                               application_id):
        """Record a hosting profile for a core application.

        Reference implementation only: the delivery / hosting
        runtime is the CSP's environment and does not transfer to
        this build (PLATFORM-LAYER.md decision 6); nothing is
        hosted or delivered here (``hosted_here: False``,
        ``delivered_here: False``).
        """
        action = "exts_hosting_profile_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        self._application_in_org(actor, org_id, application_id)
        with self._lock:
            record = {
                "id": self._mint("dlp-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "application_id": application_id,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "hosted_here": False,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._hosting_profiles[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _hosting_profile(self, profile_id):
        record = self._hosting_profiles.get(profile_id)
        if record is None:
            raise NotFoundError("no such hosting profile: %r" % (profile_id,))
        return record

    def record_hosting_report(self, actor, org_id, profile_id, outcome_label):
        """Record a hosting profile's verbatim reported outcome."""
        action = "exts_hosting_report_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        profile = self._hosting_profile(profile_id)
        if profile["org_id"] != org_id:
            raise ValidationError(
                "hosting profile belongs to another organization")
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("dlr-"),
                "org_id": org_id,
                "profile_id": profile_id,
                "outcome_label": outcome_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "hosted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._hosting_reports[record["id"]] = record
        self._audit(actor, action, record["id"], {"profile_id": profile_id})
        return dict(record)

    def list_hosting_profiles(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._hosting_profiles.values()
                if r["org_id"] == org_id]

    def list_hosting_reports(self, actor, org_id, profile_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._hosting_reports.values()
                if r["org_id"] == org_id
                and (profile_id is None or r["profile_id"] == profile_id)]

    # -- idx 518: virtualization engine (records surface) ------------------------

    def create_virtual_instance(self, actor, org_id, ref, label, platform_ref,
                                system_id=None):
        """Record a virtual instance as REPORTED data.

        The virtualization engine is the underlying cloud
        provider's; an instance record here is a report of an
        instance that platform runs, held verbatim
        (``virtualized_here: False``). ``platform_ref`` is the
        same opaque platform reference Core systems carry. The
        instance's current state is never stored on the record;
        it derives at read from recorded state labels (see
        :meth:`record_instance_state`).
        """
        action = "exts_virtual_instance_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        _text(platform_ref, "platform_ref")
        if system_id is not None:
            self._system_in_org(actor, org_id, system_id)
        with self._lock:
            for existing in self._virtual_instances.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "virtual instance ref already exists in this "
                        "organization: %r" % (ref,))
            record = {
                "id": self._mint("vin-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "platform_ref": platform_ref,
                "system_id": system_id,
                "virtualized_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._virtual_instances[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _virtual_instance(self, instance_id):
        record = self._virtual_instances.get(instance_id)
        if record is None:
            raise NotFoundError(
                "no such virtual instance: %r" % (instance_id,))
        return record

    def record_instance_state(self, actor, org_id, instance_id, state_label):
        """Append one reported state label to a virtual instance."""
        instance = self._virtual_instance(instance_id)
        if instance["org_id"] != org_id:
            raise ValidationError(
                "virtual instance belongs to another organization")
        return self._record_state(
            actor, org_id, self._instance_states, "vins-", "instance_id",
            instance_id, state_label, INSTANCE_STATES,
            "exts_instance_state_record")

    def get_virtual_instance(self, actor, instance_id):
        instance = self._virtual_instance(instance_id)
        self._org(actor, instance["org_id"])
        return self._state_view(
            instance, self._states_for(self._instance_states, "instance_id",
                                       instance_id))

    def list_virtual_instances(self, actor, org_id):
        self._org(actor, org_id)
        return [
            self._state_view(v, self._states_for(
                self._instance_states, "instance_id", v["id"]))
            for v in self._virtual_instances.values()
            if v["org_id"] == org_id
        ]

    def virtualization_summary(self, actor, org_id):
        """Counts only, derived at read: instances by derived
        current state."""
        self._org(actor, org_id)
        by_state = {}
        instances = 0
        for instance in self._virtual_instances.values():
            if instance["org_id"] != org_id:
                continue
            instances += 1
            state = self._latest_state_label(self._states_for(
                self._instance_states, "instance_id", instance["id"]))
            by_state[state] = by_state.get(state, 0) + 1
        return {
            "org_id": org_id,
            "virtual_instances": instances,
            "instances_by_current_state": by_state,
        }

    # -- idx 519: high-availability network operation ----------------------------

    def create_ha_configuration(self, actor, org_id, ref, label,
                                redundancy_label, system_id=None):
        """Record a high-availability configuration as data.

        ``redundancy_label`` carries the operator's own redundancy
        arrangement verbatim (for example "active-passive"). The
        configuration is a record about the network arrangement;
        no network is operated and no failover is performed here
        (``operated_here: False``,
        ``failover_performed_here: False``). Its current
        availability state derives at read from recorded event
        labels (see :meth:`record_ha_event`).
        """
        action = "exts_ha_configuration_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        _text(redundancy_label, "redundancy_label")
        if system_id is not None:
            self._system_in_org(actor, org_id, system_id)
        with self._lock:
            for existing in self._ha_configurations.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "HA configuration ref already exists in this "
                        "organization: %r" % (ref,))
            record = {
                "id": self._mint("hac-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "redundancy_label": redundancy_label,
                "system_id": system_id,
                "operated_here": False,
                "failover_performed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._ha_configurations[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _ha_configuration(self, config_id):
        record = self._ha_configurations.get(config_id)
        if record is None:
            raise NotFoundError(
                "no such HA configuration: %r" % (config_id,))
        return record

    def record_ha_event(self, actor, org_id, config_id, event_label):
        """Append one reported availability event label.

        Events are reports of the operating network's behavior
        (health observations, failovers that happened elsewhere);
        recording one performs no failover and changes no network.
        """
        config = self._ha_configuration(config_id)
        if config["org_id"] != org_id:
            raise ValidationError(
                "HA configuration belongs to another organization")
        return self._record_state(
            actor, org_id, self._ha_events, "hae-", "config_id",
            config_id, event_label, HA_EVENT_LABELS,
            "exts_ha_event_record")

    def get_ha_configuration(self, actor, config_id):
        config = self._ha_configuration(config_id)
        self._org(actor, config["org_id"])
        return self._state_view(
            config, self._states_for(self._ha_events, "config_id", config_id))

    def list_ha_configurations(self, actor, org_id):
        self._org(actor, org_id)
        return [
            self._state_view(c, self._states_for(
                self._ha_events, "config_id", c["id"]))
            for c in self._ha_configurations.values()
            if c["org_id"] == org_id
        ]

    def ha_summary(self, actor, org_id):
        """Counts only, derived at read: configurations by derived
        current state, events by verbatim label."""
        self._org(actor, org_id)
        by_state = {}
        configurations = 0
        for config in self._ha_configurations.values():
            if config["org_id"] != org_id:
                continue
            configurations += 1
            state = self._latest_state_label(self._states_for(
                self._ha_events, "config_id", config["id"]))
            by_state[state] = by_state.get(state, 0) + 1
        by_label = {}
        events = 0
        for event in self._ha_events.values():
            if event["org_id"] == org_id:
                events += 1
                by_label[event["state_label"]] = \
                    by_label.get(event["state_label"], 0) + 1
        return {
            "org_id": org_id,
            "ha_configurations": configurations,
            "configurations_by_current_state": by_state,
            "ha_events": events,
            "events_by_label": by_label,
        }

    # -- idx 520: third-party CSP hosting platforms (reference stub) --------------

    def create_platform_declaration(self, actor, org_id, platform_ref, label):
        """Declare a third-party hosting platform as a reference.

        Reference implementation only: the platform is outside the
        fork's own boundary by its own statement, and its hosting
        substrate does not transfer to this build
        (PLATFORM-LAYER.md decision 6). ``platform_ref`` is the
        opaque reference Core systems already carry; this record
        declares the platform relationship itself. Nothing is
        hosted or operated here (``hosted_here: False``,
        ``operated_here: False``).
        """
        action = "exts_platform_declaration_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(platform_ref, "platform_ref")
        _text(label, "label")
        with self._lock:
            for existing in self._platform_declarations.values():
                if (existing["org_id"] == org_id
                        and existing["platform_ref"] == platform_ref):
                    raise ValidationError(
                        "platform already declared in this organization: "
                        "%r" % (platform_ref,))
            record = {
                "id": self._mint("pld-"),
                "org_id": org_id,
                "platform_ref": platform_ref,
                "label": label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "hosted_here": False,
                "operated_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._platform_declarations[record["id"]] = record
        self._audit(actor, action, record["id"],
                    {"platform_ref": platform_ref})
        return dict(record)

    def _platform_declaration(self, declaration_id):
        record = self._platform_declarations.get(declaration_id)
        if record is None:
            raise NotFoundError(
                "no such platform declaration: %r" % (declaration_id,))
        return record

    def record_platform_report(self, actor, org_id, declaration_id,
                               outcome_label):
        """Record a platform declaration's verbatim reported outcome."""
        action = "exts_platform_report_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        declaration = self._platform_declaration(declaration_id)
        if declaration["org_id"] != org_id:
            raise ValidationError(
                "platform declaration belongs to another organization")
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("plr-"),
                "org_id": org_id,
                "declaration_id": declaration_id,
                "outcome_label": outcome_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "hosted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._platform_reports[record["id"]] = record
        self._audit(actor, action, record["id"],
                    {"declaration_id": declaration_id})
        return dict(record)

    def list_platform_declarations(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._platform_declarations.values()
                if r["org_id"] == org_id]

    def list_platform_reports(self, actor, org_id, declaration_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._platform_reports.values()
                if r["org_id"] == org_id
                and (declaration_id is None
                     or r["declaration_id"] == declaration_id)]
