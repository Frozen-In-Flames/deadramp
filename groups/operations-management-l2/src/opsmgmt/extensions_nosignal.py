"""Final GAPS batch, third unit — No-Signal Addition (SMX).

Clean-room extension surface for the 2 OPEN entries of the
"No-Signal Addition — Operations Management L2 (SMX Elevate IAP,
F1603077867)" section of the repo-root ``GAPS.md``. See
``BATCH-NOSIGNAL.md`` in the group directory for the per-entry
disposition. The first batch unit for this group lives in
``opsmgmt/extensions.py`` (the original Group 36 section) and the
second in ``opsmgmt/verticals.py`` (the Remainder Addition
section); this module is independent of both and touches nothing
in either.

This fork arrived by a different route: the remainder census
left it unclassified (its marketplace description carries no
citable function sentence), and the live-docs research pass
resolved it to Operations Management on SMX's own capability
sheet (ADDENDUM.md section 8). It claims **zero families** under
the group's taxonomy applied verbatim. The two entries below are
built ONLY from what the section's registered entries and the
addendum's gap notes name — provisioning, monitoring, security,
and lifecycle management of multi-cloud platforms run as code,
and built-in compliance automation with policy guardrails over
the baselines the fork names in its own words — nothing inferred
from the vendor's reputation.

Design, following the core's and the prior batch units'
doctrines:

- This module wraps :class:`opsmgmt.store.OpsStore`; every core
  module and both prior batch units' modules are untouched
  (byte-identical). Core records are always read through the
  core store's public API, never re-implemented.
- The cloud platform operations entry is an engine over
  external systems — it provisions, monitors, secures, and
  lifecycle-manages platforms this build does not run — so it
  ships as a **labeled reference implementation**: every record
  carries ``reference_stub: True``, automation modes
  (Infrastructure-as-Code / Operations-as-Code / Policy and
  Compliance-as-Code, from the research pass's notes on the
  fork's own documentation) are held as data and never
  executed, and operation outcomes are stored exactly as
  reported. It is adjacent to, but not the same as, the first
  unit's platform-service references (the shipped union's
  connectivity/hosting gap, MCSS-shaped): those are service
  references; these are references to a multi-cloud platform
  operations engine and its lifecycle operations.
- The compliance automation & policy guardrails entry lands in
  its **records form**: baseline packs naming the baselines the
  fork names in its own words (CMMC, HIPAA, HITECH, CJIS, PCI,
  SOC 1/2, FedRAMP, DoD IL — ADDENDUM.md section 8) with control
  references held as data, guardrail definitions whose rule
  text is held verbatim and never evaluated, and guardrail
  check records whose outcomes are stored exactly as an
  external automation reported them. Nothing here automates,
  evaluates, or enforces: ``automated_here: False`` and
  ``enforced_here: False`` throughout. This is distinct from
  the first unit's surfaces on the same words: its generic
  policy definitions/evaluations are the MCSS policy
  enforcement plane's records, and its governance framework
  references are labeled stubs for the MCSS console engine;
  this entry is the SMX baseline-content automation — packs
  keyed to named compliance baselines with guardrails scoped
  to multi-tenant and cross-domain operations, the scopes the
  fork's own gap note names.
- A guardrail check's current state is **derived at read**:
  ``guardrail_view`` derives the check count, the counts by
  outcome, and the latest reported outcome from the check
  records; the stored guardrail definition carries no count
  and no outcome (pinned by test).
- RBAC reuses the founding 16-action matrix with **no new
  actions**; each operation maps onto an existing core action,
  checked before any state change or id allocation for
  User-like actors, mirroring the core store's convention
  (plain-string actors carry identity but no role). Successful
  mutations are recorded on the core audit log with an
  ``extn_``-prefixed action name; denied attempts are recorded
  with the same name suffixed ``:denied`` before the denial
  propagates:

  ============================  ===============  ================
  surface                       write action     read action
  ============================  ===============  ================
  cloud platform references     work_write       report_read
  lifecycle operation refs      work_write       report_read
  baseline packs / guardrails   workflow_write   workflow_read
  guardrail checks              work_write       workflow_read
  derived views / summaries     --               report_read
  ============================  ===============  ================

  (Configuration-shaped surfaces ride ``workflow_write`` — the
  admin-only configuration write, as the core workflow registry
  and the first unit's policy definitions do; operational
  records ride ``work_write``.)

- All ``*_ref`` parameters naming things outside this build are
  opaque tokens: whitespace, URLs, hostnames, and IP-shaped
  values are rejected at the boundary, so a record cannot
  quietly carry a real system's address or a real identifier.
  Links into the core substrate use core ids (``proj-``),
  validated through the core store.
- One guard is stated as a named seam.
  ``_check_checker_not_definer``: the actor who records a
  guardrail check may never be the actor who defined the
  guardrail (separation of duties) — this unit's fresh
  negative control.
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


_IP_LIKE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

# -- option sets -------------------------------------------------------

AUTOMATION_MODES = (
    "infrastructure_as_code",
    "operations_as_code",
    "policy_as_code",
    "other",
)
OPERATION_KINDS = (
    "provisioning",
    "monitoring",
    "security",
    "lifecycle",
    "other",
)
OPERATION_STATUSES = (
    "reported_completed",
    "reported_failed",
    "reported_in_progress",
)
# The baselines the fork names in its own words (ADDENDUM.md
# section 8): native controls and automations supporting CMMC,
# HIPAA, HITECH, CJIS, PCI, SOC 1/2, FedRAMP, and DoD IL
# baselines.
BASELINE_LABELS = (
    "cmmc",
    "hipaa",
    "hitech",
    "cjis",
    "pci",
    "soc_1",
    "soc_2",
    "fedramp",
    "dod_il",
    "other",
)
# The scopes the fork's own gap note names for its guardrails:
# policy-driven guardrails over multi-tenant and cross-domain
# operations.
GUARDRAIL_SCOPES = (
    "multi_tenant",
    "cross_domain",
    "single_tenant",
    "other",
)
GUARDRAIL_OUTCOMES = (
    "compliant_reported",
    "noncompliant_reported",
    "inconclusive",
)

# -- validation helpers --------------------------------------------------


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_ref(value, what):
    """Validate an opaque reference token.

    A reference names a thing in the caller's own world; it is
    never an address and never an identifier issued by a real
    system. Whitespace, URLs, hostnames, and IP-shaped values are
    rejected so records cannot carry a real system's location or
    a real identifier.
    """
    _validate_non_empty(value, what)
    if any(ch.isspace() for ch in value):
        raise ValidationError("%s must be an opaque reference (no spaces)" % (what,))
    if "://" in value or "/" in value or _IP_LIKE.match(value):
        raise ValidationError("%s must be an opaque reference, not an address" % (what,))
    if "." in value:
        raise ValidationError("%s must be an opaque reference, not a hostname" % (what,))
    if len(value) > 128:
        raise ValidationError("%s is too long for an opaque reference" % (what,))
    return value


def _validate_choice(value, options, what):
    if value not in options:
        raise ValidationError("%s must be one of %s" % (what, ", ".join(options)))
    return value


def _validate_int(value, what, minimum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if minimum is not None and value < minimum:
        raise ValidationError("%s must be at least %d" % (what, minimum))
    return value


def _validate_counts(counts, what):
    if not isinstance(counts, dict) or not counts:
        raise ValidationError("%s must be a non-empty object of counts" % (what,))
    cleaned = {}
    for key, value in counts.items():
        _validate_non_empty(key, "%s key" % (what,))
        cleaned[key] = _validate_int(value, "%s[%s]" % (what, key), minimum=0)
    return cleaned


def _validate_string_list(value, what):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError("%s must be a list of non-empty strings" % (what,))
    if len(value) > 50:
        raise ValidationError("%s may hold at most 50 entries" % (what,))
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(
                "each entry in %s must be a non-empty string" % (what,)
            )
        result.append(item)
    return result


def _validate_choice_list(value, options, what):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError("%s must be a list of choices" % (what,))
    if len(value) > 10:
        raise ValidationError("%s may hold at most 10 entries" % (what,))
    result = []
    for item in value:
        _validate_choice(item, options, "%s entry" % (what,))
        if item not in result:
            result.append(item)
    return result


def _validate_optional_text(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string or None" % (what,))
    return value


# -- guards (named seams) -------------------------------------------------


def _check_checker_not_definer(defined_by, checker):
    """Separation-of-duties seam for guardrail checks.

    The actor who records a guardrail check may never be the
    actor who defined the guardrail. The guard is the
    load-bearing invariant behind ``record_guardrail_check``
    and the fresh negative control's mutation target for this
    unit (see tests/README.md).
    """
    if defined_by is not None and checker is not None and defined_by == checker:
        raise ValidationError(
            "guardrail checker must differ from the guardrail's definer (%r)"
            % (defined_by,)
        )


class OpsNoSignal:
    """No-signal-addition extension surface over a core OpsStore."""

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

        Mirrors the core store: an actor must be present;
        User-like actors are checked against the core permission
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

    def _create(self, kind, prefix, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            record["updated_utc"] = record["created_utc"]
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            self._audit(actor, audit_action, record_id, details={"kind": kind})
            return copy.deepcopy(record)

    def _get(self, kind, record_id):
        record = self._records.get((kind, record_id))
        if record is None:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id):
        return copy.deepcopy(self._get(kind, record_id))

    def _list(self, collection, **filters):
        result = []
        for key in self._order:
            if key[0] != collection:
                continue
            record = self._records[key]
            if all(
                record.get(name) == value
                for name, value in filters.items()
                if value is not None
            ):
                result.append(copy.deepcopy(record))
        return result

    def _core_project(self, project_id):
        return self.store.get_project(project_id)

    # -- Cloud platform operations & lifecycle management engine ----
    # Stub-engine entry (idx 969): an engine over external
    # multi-cloud platforms, shipped as a labeled reference
    # implementation. Platform references plus lifecycle
    # operation references; automation modes are data, outcomes
    # are reported, and nothing is provisioned, monitored,
    # secured, or lifecycle-managed here.

    def register_cloud_platform_reference(self, platform_ref, actor,
                                          cloud_labels=None,
                                          automation_modes=None,
                                          scope_ref=None):
        """Register a reference record of an external multi-cloud
        platform operated by an external operations engine.
        Action: work_write. Carries ``reference_stub: True``;
        the platform is not provisioned, operated, monitored,
        secured, or lifecycle-managed here."""
        self._guard(actor, "work_write", "extn_cloud_platform_register",
                    platform_ref)
        _validate_ref(platform_ref, "platform_ref")
        cloud_labels = _validate_string_list(cloud_labels, "cloud_labels")
        automation_modes = _validate_choice_list(
            automation_modes, AUTOMATION_MODES, "automation_modes")
        if scope_ref is not None:
            _validate_ref(scope_ref, "scope_ref")
        return self._create(
            "cloud_platform_reference", "cpr",
            {
                "platform_ref": platform_ref,
                "cloud_labels": cloud_labels,
                "automation_modes": automation_modes,
                "scope_ref": scope_ref,
                "reference_stub": True,
                "provisioned_here": False,
                "operated_here": False,
                "monitored_here": False,
                "secured_here": False,
                "lifecycle_managed_here": False,
            },
            actor, "extn_cloud_platform_register",
        )

    def record_lifecycle_operation_reference(self, platform_id, operation_kind,
                                             reported_status, actor,
                                             counts=None, note=None):
        """Record a reference to a platform operation reported by
        an external operations engine: provisioning, monitoring,
        security, or lifecycle management of a registered
        platform. Action: work_write. Carries ``reference_stub:
        True``; counts are stored exactly as reported and no
        operation is performed or executed here."""
        self._guard(actor, "work_write", "extn_lifecycle_operation",
                    platform_id)
        self._get("cloud_platform_reference", platform_id)
        _validate_choice(operation_kind, OPERATION_KINDS, "operation_kind")
        _validate_choice(reported_status, OPERATION_STATUSES,
                         "reported_status")
        if counts is not None:
            counts = _validate_counts(counts, "counts")
        _validate_optional_text(note, "note")
        return self._create(
            "lifecycle_operation_reference", "clo",
            {
                "platform_id": platform_id,
                "operation_kind": operation_kind,
                "reported_status": reported_status,
                "counts": counts,
                "note": note,
                "reference_stub": True,
                "performed_here": False,
                "executed_here": False,
            },
            actor, "extn_lifecycle_operation",
        )

    def list_cloud_platform_references(self, actor=None):
        """List cloud platform reference records. Action:
        report_read."""
        self._guard_read(actor, "report_read", "extn_cloud_platform_read")
        return self._list("cloud_platform_reference")

    def list_lifecycle_operation_references(self, actor=None, platform_id=None,
                                            operation_kind=None):
        """List lifecycle operation reference records. Action:
        report_read."""
        self._guard_read(actor, "report_read", "extn_lifecycle_operation_read")
        return self._list("lifecycle_operation_reference",
                          platform_id=platform_id,
                          operation_kind=operation_kind)

    def cloud_platform_summary(self, actor=None):
        """Derived reference counts only: platform references,
        operation references by kind and by reported status. No
        score or state is computed. Derived at read, never
        stored. Action: report_read."""
        self._guard_read(actor, "report_read", "extn_cloud_platform_summary")
        operations = self._list("lifecycle_operation_reference")
        by_kind = {}
        by_status = {}
        for operation in operations:
            key = operation["operation_kind"]
            by_kind[key] = by_kind.get(key, 0) + 1
            status = operation["reported_status"]
            by_status[status] = by_status.get(status, 0) + 1
        return {
            "platforms": len(self._list("cloud_platform_reference")),
            "operations": len(operations),
            "operations_by_kind": by_kind,
            "operations_by_status": by_status,
            "reference_stub": True,
            "operated_here": False,
        }

    # -- Built-in compliance automation & policy guardrails engine --
    # Build-extension entry (idx 970), records form: baseline
    # packs (named baselines, control references as data),
    # guardrail definitions (rule text verbatim, never
    # evaluated), and guardrail check records (outcomes exactly
    # as reported by an external automation). Nothing automates,
    # evaluates, or enforces here.

    def register_baseline_pack(self, baseline_label, actor, name=None,
                               control_refs=None):
        """Register a baseline pack record: one of the baselines
        the fork names in its own words, with its control
        references held as data. Action: workflow_write
        (configuration, as the core workflow registry)."""
        self._guard(actor, "workflow_write", "extn_baseline_pack_register",
                    baseline_label)
        _validate_choice(baseline_label, BASELINE_LABELS, "baseline_label")
        _validate_optional_text(name, "name")
        control_refs = _validate_string_list(control_refs, "control_refs")
        return self._create(
            "baseline_pack", "bpk",
            {
                "baseline_label": baseline_label,
                "name": name,
                "control_refs": control_refs,
                "automated_here": False,
                "enforced_here": False,
            },
            actor, "extn_baseline_pack_register",
        )

    def create_guardrail(self, name, rule_text, actor, baseline_pack_id=None,
                         scope_kind="other", project_id=None):
        """Create a guardrail definition record. Action:
        workflow_write (configuration). ``rule_text`` is held
        verbatim as data; it is never evaluated by this build,
        and the guardrail is enforced nowhere here."""
        self._guard(actor, "workflow_write", "extn_guardrail_create", name)
        _validate_non_empty(name, "guardrail name")
        _validate_non_empty(rule_text, "rule_text")
        _validate_choice(scope_kind, GUARDRAIL_SCOPES, "scope_kind")
        if baseline_pack_id is not None:
            self._get("baseline_pack", baseline_pack_id)
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "guardrail", "grl",
            {
                "name": name,
                "rule_text": rule_text,
                "baseline_pack_id": baseline_pack_id,
                "scope_kind": scope_kind,
                "project_id": project_id,
                "automated_here": False,
                "enforced_here": False,
            },
            actor, "extn_guardrail_create",
        )

    def record_guardrail_check(self, guardrail_id, actor, outcome, note=None):
        """Record a guardrail check outcome **as reported by an
        external compliance automation**. Action: work_write.
        The outcome is stored as reported; this build evaluates
        no guardrail and automates nothing. Separation of
        duties: the checker may never be the guardrail's definer
        (``_check_checker_not_definer``)."""
        self._guard(actor, "work_write", "extn_guardrail_check", guardrail_id)
        guardrail = self._get("guardrail", guardrail_id)
        _check_checker_not_definer(guardrail["created_by"], actor_name(actor))
        _validate_choice(outcome, GUARDRAIL_OUTCOMES, "outcome")
        _validate_optional_text(note, "note")
        return self._create(
            "guardrail_check", "gck",
            {
                "guardrail_id": guardrail_id,
                "outcome": outcome,
                "note": note,
                "automated_here": False,
                "evaluated_here": False,
                "enforced_here": False,
            },
            actor, "extn_guardrail_check",
        )

    def get_baseline_pack(self, pack_id, actor=None):
        """Read one baseline pack. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "extn_baseline_pack_read",
                         pack_id)
        return self._fetch("baseline_pack", pack_id)

    def list_baseline_packs(self, actor=None, baseline_label=None):
        """List baseline pack records. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "extn_baseline_pack_read")
        return self._list("baseline_pack", baseline_label=baseline_label)

    def get_guardrail(self, guardrail_id, actor=None):
        """Read one guardrail definition. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "extn_guardrail_read",
                         guardrail_id)
        return self._fetch("guardrail", guardrail_id)

    def list_guardrails(self, actor=None, baseline_pack_id=None,
                        scope_kind=None):
        """List guardrail definitions. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "extn_guardrail_read")
        return self._list("guardrail", baseline_pack_id=baseline_pack_id,
                          scope_kind=scope_kind)

    def list_guardrail_checks(self, actor=None, guardrail_id=None):
        """List guardrail check records. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "extn_guardrail_read")
        return self._list("guardrail_check", guardrail_id=guardrail_id)

    def guardrail_view(self, guardrail_id, actor=None):
        """A guardrail definition plus its derived check state:
        check count, counts by outcome, and the latest reported
        outcome, all derived at read from the check records and
        never stored on the definition. Action: report_read."""
        self._guard_read(actor, "report_read", "extn_guardrail_view",
                         guardrail_id)
        guardrail = self._fetch("guardrail", guardrail_id)
        checks = self._list("guardrail_check", guardrail_id=guardrail_id)
        by_outcome = {}
        for check in checks:
            key = check["outcome"]
            by_outcome[key] = by_outcome.get(key, 0) + 1
        view = dict(guardrail)
        view["check_count"] = len(checks)
        view["checks_by_outcome"] = by_outcome
        view["latest_outcome"] = checks[-1]["outcome"] if checks else None
        return view

    def compliance_summary(self, actor=None):
        """Derived compliance-automation counts only: baseline
        packs by label, guardrail definitions by scope, checks
        by outcome. No score, rate, or grade key appears
        anywhere in the view. Derived at read, never stored.
        Action: report_read."""
        self._guard_read(actor, "report_read", "extn_compliance_summary")
        packs = self._list("baseline_pack")
        guardrails = self._list("guardrail")
        checks = self._list("guardrail_check")
        packs_by_label = {}
        for pack in packs:
            key = pack["baseline_label"]
            packs_by_label[key] = packs_by_label.get(key, 0) + 1
        guardrails_by_scope = {}
        for guardrail in guardrails:
            key = guardrail["scope_kind"]
            guardrails_by_scope[key] = guardrails_by_scope.get(key, 0) + 1
        checks_by_outcome = {}
        for check in checks:
            key = check["outcome"]
            checks_by_outcome[key] = checks_by_outcome.get(key, 0) + 1
        return {
            "baseline_packs": len(packs),
            "baseline_packs_by_label": packs_by_label,
            "guardrails": len(guardrails),
            "guardrails_by_scope": guardrails_by_scope,
            "checks": len(checks),
            "checks_by_outcome": checks_by_outcome,
            "automated_here": False,
            "enforced_here": False,
        }
