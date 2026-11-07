"""Final GAPS batch, second unit — Remainder Addition extensions.

This module is the extension surface for the two OPEN entries of the
GAPS.md section "Remainder Addition — Cybersecurity L3-adjacent
(+2 forks)" (the Cisco Security Cloud and XTec AuthentX addition
forks; see ``ADDENDUM.md`` §5). It is a NEW module added by the final
GAPS batch's second unit in this group: every pre-existing module in
this package — including the first batch unit's ``extensions.py`` —
stays byte-identical, and nothing here weakens the High-baseline
uplifts (hash-chained audit, fail-closed writes, audit
query/reduction, the auditor role, logon lockout). The shared
validators, the ``count_by`` counting seam, and the fail-closed
decorator are reused from ``cyber.extensions`` (DeadRamp's own code,
reuse stated here per the package's convention).

The two entries land in two different honest forms, per their
drafted triage in ``gaps-batch/inventory.json``:

- **Firewall management & orchestration plane** (idx 620,
  stub-engine) ships as a **labeled reference implementation**. The
  plane is an engine over external systems: it manages NGFW
  devices, pushes policy to them, provisions them zero-touch, and
  analyzes policy with an AIOps engine. What lands here is the
  reference surface for that plane: device, policy-definition,
  provisioning-report, and analysis-report records, every one
  carrying ``reference_stub: True`` and the status ``recorded``.
  Nothing here manages a device, pushes a rule, provisions
  anything, or analyzes a policy; provisioning outcomes and
  analysis labels are the external plane's own reported data.

- **Inline email security platform** (idx 622, build-extension)
  lands in its **records form**, the same adjudication the founding
  unit applied to the DLP and network-enforcement families:
  gateway registrations, declared policy records (the platform's
  configured disposition intent, recorded as data; recording it
  delivers, quarantines, and blocks nothing), and disposition
  records reported by the external platform. This surface is named
  separately from the phishing family's simulation / training
  content (``cyber.extensions`` campaigns): no message is composed,
  sent, inspected, or stored here, and **no function on this
  surface can accept message content or a mail address** — a
  message is named by an opaque ``message_ref`` token only, and
  address-shaped tokens (anything containing ``@``) are refused at
  the boundary, so no field can hold a sender, a recipient, or any
  other PII.

Doctrines, carried from the core and the first extension unit and
applied unchanged:

- **No computed score on this surface.** Dispositions, outcomes,
  and analysis labels arriving from external engines are recorded
  as the source's own data; every rollup is counts and buckets
  only. The founding build's deterministic finding/risk scoring
  (``cyber.store``) remains the only scoring in the package and is
  not re-implemented or extended here.
- **Derived, never stored.** Provisioning counts, latest outcomes,
  disposition counts, and latest dispositions are computed at read
  time in the ``*_view`` / ``*_summary`` functions and are never
  keys on a stored record (pinned by tests).
- **Opaque references only.** Devices, gateways, and messages are
  caller-supplied opaque ``*_ref`` tokens under the founding
  validator (no IPv4 literal, dotted hostname, URL, or whitespace),
  tightened on the mail surface with the ``@`` refusal above.
- **RBAC via the core access module.** Registrations and policy
  definitions require ``manage_assets``; reported-outcome ingestion
  requires ``ingest``; views and summaries require ``read``. The
  auditor role (``audit_read`` only, AC-5) therefore holds no
  permission on this surface at all.
- **Append-only audit (AU), fail-closed (AU-5).** Every successful
  mutation is recorded on the same hash-chained ``AuditLog`` the
  core uses; if the audit write raises ``AuditWriteError`` the
  whole mutation rolls back (no object created, no id consumed).
  Denied attempts on this surface are audit-recorded (action
  ``extension_addition_denied``) before the denial propagates.
"""

import copy
import threading

from .access import require
from .audit import actor_name
from .errors import AuditWriteError, NotFoundError, PermissionDenied, ValidationError
from .extensions import (
    _fail_closed,
    _utc_now,
    _validate_choice,
    _validate_non_empty,
    _validate_ref,
    _validate_string_list,
    count_by,
)

# -- vocabularies ------------------------------------------------------

FW_MODEL_LABELS = ("asa", "ftd", "other")
PROVISIONING_OUTCOMES = ("completed", "failed", "cancelled")
ANALYSIS_LABELS = (
    "conflict_reported",
    "optimization_reported",
    "no_issue_reported",
    "other",
)
MAIL_DEPLOYMENTS = ("inline", "api_based", "other")
MAIL_THREAT_CATEGORIES = (
    "bec", "phishing", "malware", "spam", "qr_code", "other",
)
MAIL_DECLARED_ACTIONS = ("deliver", "quarantine", "block", "tag")
MAIL_DISPOSITIONS = ("delivered", "quarantined", "blocked", "tagged")
MAIL_CATEGORIES = MAIL_THREAT_CATEGORIES + ("clean",)


def latest_label(records, key):
    """The ``key`` value of the most recent record, or ``None``.

    The single latest-value seam for this module's derived views.
    The batch's fresh negative control mutates this function to an
    earliest-reading form; see tests/README.md.
    """
    return records[-1][key] if records else None


def _validate_message_ref(value):
    """Validate an opaque message reference token.

    The founding opaque-ref rules apply, tightened for the mail
    surface: a token containing ``@`` is address-shaped — it names
    a mailbox, which is PII — and is refused at the boundary.
    """
    _validate_ref(value, "message_ref")
    if "@" in value:
        raise ValidationError(
            "message_ref must be an opaque reference, not an address"
        )
    return value


class ExtensionAdditionStore:
    """In-memory records substrate for the Remainder Addition entries."""

    _COLLECTIONS = (
        "fw_devices", "fw_policies", "fw_provisioning", "fw_analyses",
        "mail_gateways", "mail_policies", "mail_dispositions",
    )

    _PREFIXES = {
        "fw_devices": "fwd", "fw_policies": "fwp",
        "fw_provisioning": "fwpr", "fw_analyses": "fwa",
        "mail_gateways": "mlg", "mail_policies": "mlp",
        "mail_dispositions": "mld",
    }

    # Collections whose records are labeled reference implementations
    # (the firewall management & orchestration plane, idx 620).
    _STUB_COLLECTIONS = frozenset(
        ("fw_devices", "fw_policies", "fw_provisioning", "fw_analyses")
    )

    def __init__(self, audit=None):
        self.audit = audit
        self._data = {name: {} for name in self._COLLECTIONS}
        self._counters = {name: 0 for name in self._COLLECTIONS}
        self._lock = threading.RLock()

    # -- internal helpers (mirroring cyber.extensions) -------------------

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _require(self, actor, action, target):
        """Enforce a permission; denied attempts are audit-recorded."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit(
                    actor, "extension_addition_denied", target,
                    details={"action": action},
                )
                raise

    def _create(self, collection, fields, actor, action_name):
        """Assign an id, stamp provenance, store, audit, return a copy."""
        self._counters[collection] += 1
        record_id = "%s-%d" % (self._PREFIXES[collection], self._counters[collection])
        record = {"id": record_id}
        record.update(fields)
        if collection in self._STUB_COLLECTIONS:
            record["reference_stub"] = True
        record["created_by"] = actor_name(actor)
        record["created_utc"] = _utc_now()
        self._data[collection][record_id] = record
        self._audit(actor, action_name, record_id)
        return copy.deepcopy(record)

    def _get(self, collection, record_id, what):
        record = self._data[collection].get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _list(self, collection):
        return [copy.deepcopy(r) for r in self._data[collection].values()]

    def _children(self, collection, key, parent_id):
        return [
            copy.deepcopy(r)
            for r in self._data[collection].values()
            if r[key] == parent_id
        ]

    # -- firewall management & orchestration plane -------------------------
    # Labeled reference implementation (idx 620, stub-engine).

    @_fail_closed
    def register_fw_device(self, device_ref, model_label, actor):
        """Register an NGFW device the external plane manages.

        Reference implementation: the record describes a device the
        embedding organization's firewall management plane manages
        elsewhere. Nothing here enrolls, configures, or contacts
        any device.
        """
        _validate_ref(device_ref, "device_ref")
        _validate_choice(model_label, FW_MODEL_LABELS, "model_label")
        self._require(actor, "manage_assets", "fw_devices")
        with self._lock:
            return self._create(
                "fw_devices",
                {"device_ref": device_ref, "model_label": model_label,
                 "status": "recorded"},
                actor, "fw_device_register",
            )

    @_fail_closed
    def create_fw_policy(self, name, device_id, rules, actor):
        """Record a firewall policy definition as a reference record.

        Reference implementation: ``rules`` are stored as the
        definition's own text, exactly as a playbook's steps are in
        the first extension unit. The definition is never pushed to
        a device, applied, or enforced by anything here.
        """
        _validate_non_empty(name, "policy name")
        rules = _validate_string_list(rules, "rules")
        if not rules:
            raise ValidationError("rules must be a non-empty list")
        self._require(actor, "manage_assets", "fw_policies")
        with self._lock:
            self._get("fw_devices", device_id, "firewall device")
            return self._create(
                "fw_policies",
                {"name": name, "device_id": device_id, "rules": rules,
                 "status": "recorded"},
                actor, "fw_policy_create",
            )

    @_fail_closed
    def record_fw_provisioning(self, device_id, outcome, actor):
        """Record one zero-touch provisioning outcome reported by
        the external plane. Nothing is provisioned here."""
        _validate_choice(outcome, PROVISIONING_OUTCOMES, "outcome")
        self._require(actor, "ingest", "fw_provisioning")
        with self._lock:
            self._get("fw_devices", device_id, "firewall device")
            return self._create(
                "fw_provisioning",
                {"device_id": device_id, "outcome": outcome,
                 "status": "recorded"},
                actor, "fw_provisioning_record",
            )

    @_fail_closed
    def record_fw_analysis(self, policy_id, label, actor):
        """Record one AIOps policy-analysis result reported by the
        external plane.

        ``label`` is the analyzer's own reported result, recorded as
        source data. No policy is analyzed here, and no score,
        confidence, or recommendation is computed from the label.
        """
        _validate_choice(label, ANALYSIS_LABELS, "label")
        self._require(actor, "ingest", "fw_analyses")
        with self._lock:
            self._get("fw_policies", policy_id, "firewall policy")
            return self._create(
                "fw_analyses",
                {"policy_id": policy_id, "label": label,
                 "status": "recorded"},
                actor, "fw_analysis_record",
            )

    def fw_device_view(self, device_id, actor):
        """One device plus its derived policy/provisioning counts and
        latest reported provisioning outcome (never stored)."""
        self._require(actor, "read", "fw_devices")
        with self._lock:
            device = copy.deepcopy(
                self._get("fw_devices", device_id, "firewall device")
            )
            policies = self._children("fw_policies", "device_id", device_id)
            provisioning = self._children(
                "fw_provisioning", "device_id", device_id
            )
            device["policy_count"] = len(policies)
            device["provisioning_count"] = len(provisioning)
            device["latest_provisioning_outcome"] = latest_label(
                provisioning, "outcome"
            )
            return device

    # -- inline email security platform (records form, idx 622) -----------

    @_fail_closed
    def register_mail_gateway(self, gateway_ref, deployment, actor):
        """Register an inline email security gateway run elsewhere.

        Records form only: nothing here receives, inspects, or
        routes any message; the gateway is the external platform's.
        """
        _validate_ref(gateway_ref, "gateway_ref")
        _validate_choice(deployment, MAIL_DEPLOYMENTS, "deployment")
        self._require(actor, "manage_assets", "mail_gateways")
        with self._lock:
            return self._create(
                "mail_gateways",
                {"gateway_ref": gateway_ref, "deployment": deployment},
                actor, "mail_gateway_register",
            )

    @_fail_closed
    def create_mail_policy(self, name, threat_category, declared_action,
                           actor):
        """Record a mail policy as configured on the external platform.

        ``declared_action`` is the policy's declared disposition
        intent, recorded as data about the external platform's
        configuration. Recording it delivers, quarantines, blocks,
        and tags nothing: no message exists in this substrate.
        """
        _validate_non_empty(name, "policy name")
        _validate_choice(
            threat_category, MAIL_THREAT_CATEGORIES, "threat_category"
        )
        _validate_choice(
            declared_action, MAIL_DECLARED_ACTIONS, "declared_action"
        )
        self._require(actor, "manage_assets", "mail_policies")
        with self._lock:
            return self._create(
                "mail_policies",
                {"name": name, "threat_category": threat_category,
                 "declared_action": declared_action},
                actor, "mail_policy_create",
            )

    @_fail_closed
    def record_mail_disposition(self, gateway_id, message_ref, disposition,
                                category, actor):
        """Ingest one message disposition reported by the platform.

        ``disposition`` and ``category`` are the external platform's
        own reported outcome for a message this substrate never saw:
        the message is named by an opaque ``message_ref`` only, and
        no content, header, sender, or recipient enters here. Unlike
        a core finding, a disposition record is never scored.
        """
        _validate_message_ref(message_ref)
        _validate_choice(disposition, MAIL_DISPOSITIONS, "disposition")
        _validate_choice(category, MAIL_CATEGORIES, "category")
        self._require(actor, "ingest", "mail_dispositions")
        with self._lock:
            self._get("mail_gateways", gateway_id, "mail gateway")
            return self._create(
                "mail_dispositions",
                {"gateway_id": gateway_id, "message_ref": message_ref,
                 "disposition": disposition, "category": category},
                actor, "mail_disposition_record",
            )

    def mail_gateway_view(self, gateway_id, actor):
        """One gateway plus its derived disposition counts and latest
        reported disposition (never stored)."""
        self._require(actor, "read", "mail_gateways")
        with self._lock:
            gateway = copy.deepcopy(
                self._get("mail_gateways", gateway_id, "mail gateway")
            )
            dispositions = self._children(
                "mail_dispositions", "gateway_id", gateway_id
            )
            gateway["disposition_count"] = len(dispositions)
            gateway["dispositions_by_disposition"] = count_by(
                [d["disposition"] for d in dispositions], MAIL_DISPOSITIONS
            )
            gateway["latest_disposition"] = latest_label(
                dispositions, "disposition"
            )
            return gateway

    def mail_summary(self, actor):
        """Counts across the mail surface (counts/buckets only)."""
        self._require(actor, "read", "mail_dispositions")
        with self._lock:
            dispositions = self._list("mail_dispositions")
            return {
                "gateways": len(self._data["mail_gateways"]),
                "policies": len(self._data["mail_policies"]),
                "dispositions": len(dispositions),
                "dispositions_by_disposition": count_by(
                    [d["disposition"] for d in dispositions],
                    MAIL_DISPOSITIONS,
                ),
                "dispositions_by_category": count_by(
                    [d["category"] for d in dispositions], MAIL_CATEGORIES
                ),
            }
