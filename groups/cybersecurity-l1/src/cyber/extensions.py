"""Final GAPS batch extensions for the Cybersecurity L1 build.

Clean-room extension surface for the 5 open Extended entries of
Group 16 registered in the repo-root ``GAPS.md`` (see ``BATCH.md``
in the group directory for the per-entry disposition). The category
discipline of the founding build is unchanged and is the whole
point of this module:

- This is the shared **defensive substrate only**. Nothing here
  scans, detects, enforces, blocks, trains, simulates, or executes.
  Where an entry names an engine or a suite, this module implements
  the **records form** of that family: registries of the thing,
  ingestion records for its output, and tracking workflows around
  it — the same forms the Moderate sibling (Group 4) shipped for
  these families, against a core that is byte-identical to it.
- Families whose honest form is an engine over external systems
  ship as **labeled reference implementations**: their records
  carry ``reference_stub: true``, and run-shaped records carry
  ``executed: false``. Nothing here runs a model or a playbook.
- **No scoring is invented.** The only scores in this package
  remain the founding build's published formulas in
  :mod:`cyber.store` (severity x criticality; likelihood x
  impact). Extension posture views are counts only.
- **Identity is hooks, never an IdP** (PLATFORM-LAYER.md
  decision 1): identity-product records describe an integration
  hook and carry ``identity_provider: false`` in their own shape.
  At this tier there is likewise no auditor role and no
  hash-chained audit — the extension writes to the founding
  build's plain append-only audit log, like the core does.
- References are **opaque**: asset, subject, learner, domain, and
  system references are caller-chosen opaque tokens. Values that
  look like IP addresses, URLs, or hostnames are rejected at the
  boundary, so a record cannot quietly carry a real system's
  address; no record shape has a field for a credential or PII.
  (A DMARC "domain" here is therefore an opaque domain *reference*
  token, never a resolvable domain name.)

Access control reuses the founding permission matrix (no new
actions): registry creates use ``manage_assets``, ingestion-shaped
records use ``ingest``, lifecycle transitions use ``triage``, GRC
records use ``assess_controls``, campaign creates/assignments use
``manage_risks``, and reads use ``read``. Denied attempts are
recorded to the audit log with a ``:denied`` suffix before the
denial propagates, following the founding build's practice of
auditing denied attempts.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .catalog import CONTROL_IDS
from .errors import NotFoundError, PermissionDenied, ValidationError


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


_IP_LIKE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

# -- option sets -------------------------------------------------------

EVIDENCE_TASK_TRANSITIONS = {
    "open": {"collected", "cancelled"},
    "collected": {"verified"},
    "verified": set(),
    "cancelled": set(),
}

HOOK_KINDS = ("sso", "mfa", "pam", "iga", "directory")

CAMPAIGN_TRANSITIONS = {
    "planned": {"approved", "cancelled"},
    "approved": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}

DMARC_POLICIES = ("none", "quarantine", "reject")

MODEL_KINDS = ("anomaly_detection", "classification", "triage_assist", "other")


# -- validation helpers --------------------------------------------------


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_ref(value, what):
    """Validate an opaque reference token.

    A reference names a thing in the caller's own world; it is never
    an address. Whitespace, URLs, hostnames, and IP-shaped values are
    rejected so records cannot carry a real system's location.
    """
    _validate_non_empty(value, what)
    if any(ch.isspace() for ch in value):
        raise ValidationError("%s must be an opaque reference (no spaces)" % (what,))
    if "://" in value or "/" in value or _IP_LIKE.match(value):
        raise ValidationError(
            "%s must be an opaque reference, not an address" % (what,)
        )
    if "." in value:
        raise ValidationError(
            "%s must be an opaque reference, not a hostname" % (what,)
        )
    if len(value) > 128:
        raise ValidationError("%s is too long for an opaque reference" % (what,))
    return value


def _validate_choice(value, options, what):
    if value not in options:
        raise ValidationError(
            "%s must be one of %s" % (what, ", ".join(options))
        )
    return value


def _validate_count(value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


def _validate_counts(counts, what):
    if not isinstance(counts, dict) or not counts:
        raise ValidationError("%s must be a non-empty object of counts" % (what,))
    cleaned = {}
    for key, value in counts.items():
        _validate_non_empty(key, "%s key" % (what,))
        cleaned[key] = _validate_count(value, "%s[%s]" % (what, key))
    return cleaned


def _check_verifier_not_collector(collected_by, verifier):
    """Separation-of-duties seam for evidence verification.

    The actor who collected a piece of evidence may not be the actor
    who verifies it. This guard is the fresh negative control's
    mutation target for the gaps batch (see tests/README.md).
    """
    if collected_by is not None and verifier is not None and collected_by == verifier:
        raise ValidationError(
            "evidence verifier must differ from its collector (%r)" % (collected_by,)
        )


class ExtensionStore:
    """In-memory register for the gaps-batch extension families.

    One store holds every extension collection. Ids are sequential
    per collection with fixed prefixes. Every operation validates
    fully before it mutates anything: a failed operation consumes no
    id and changes nothing. Successful mutations and denied attempts
    are recorded to the attached audit log (when one is attached).
    """

    _COLLECTIONS = (
        "frameworks",
        "evidence_tasks",
        "hooks",
        "campaigns",
        "assignments",
        "dmarc_policies",
        "dmarc_reports",
        "models",
        "model_outputs",
        "playbooks",
        "playbook_runs",
    )

    def __init__(self, audit=None):
        self.audit = audit
        self._data = {name: {} for name in self._COLLECTIONS}
        self._counters = {name: 0 for name in self._COLLECTIONS}
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _require(self, actor, action, audit_action, target):
        """Enforce a founding permission, auditing a denial first."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", target)
                raise

    def _insert(self, collection, prefix, fields, actor, audit_action):
        self._counters[collection] += 1
        record_id = "%s-%d" % (prefix, self._counters[collection])
        now = _utc_now()
        record = {"id": record_id}
        record.update(fields)
        record["created_by"] = actor_name(actor)
        record["created_utc"] = now
        record["updated_utc"] = now
        self._data[collection][record_id] = record
        self._audit(actor, audit_action, record_id)
        return copy.deepcopy(record)

    def _get(self, collection, record_id, what):
        record = self._data[collection].get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _list(self, collection, actor, filters=None):
        self._require(actor, "read", collection + "_list", collection)
        with self._lock:
            records = list(self._data[collection].values())
            for key, wanted in (filters or {}).items():
                if wanted is not None:
                    records = [r for r in records if r.get(key) == wanted]
            return copy.deepcopy(records)

    # -- GRC automation suites (records form beyond core mapping) -------

    def register_framework(self, framework_ref, title, actor):
        """Register a compliance framework an automation suite would
        track. Control ids used by its tasks validate against the
        founding build's 34-control catalog."""
        _validate_ref(framework_ref, "framework reference")
        _validate_non_empty(title, "framework title")
        self._require(actor, "assess_controls", "framework_register", framework_ref)
        with self._lock:
            return self._insert(
                "frameworks", "framework",
                {"framework_ref": framework_ref, "title": title},
                actor, "framework_register",
            )

    def list_frameworks(self, actor):
        return self._list("frameworks", actor)

    def create_evidence_task(self, framework_id, control_id, owner_ref, actor):
        """Create an evidence-collection task: the auditor-workflow
        record a GRC suite presupposes. Collection and verification
        are separate steps by separate actors (see the guard)."""
        _validate_ref(owner_ref, "owner reference")
        if control_id not in CONTROL_IDS:
            raise ValidationError("unknown control id: %r" % (control_id,))
        self._require(actor, "assess_controls", "evidence_task_create", control_id)
        with self._lock:
            self._get("frameworks", framework_id, "framework")
            return self._insert(
                "evidence_tasks", "evtask",
                {
                    "framework_id": framework_id,
                    "control_id": control_id,
                    "owner_ref": owner_ref,
                    "status": "open",
                    "collected_by": None,
                    "verified_by": None,
                },
                actor, "evidence_task_create",
            )

    def transition_evidence_task(self, task_id, new_status, actor):
        """Move an evidence task open -> collected -> verified (or
        open -> cancelled). Verifying requires an actor other than
        the collector: separation of duties, enforced by
        :func:`_check_verifier_not_collector`."""
        self._require(actor, "assess_controls", "evidence_task_transition", task_id)
        with self._lock:
            record = self._get("evidence_tasks", task_id, "evidence task")
            current = record["status"]
            if new_status not in EVIDENCE_TASK_TRANSITIONS[current]:
                raise ValidationError(
                    "evidence task cannot move from %r to %r"
                    % (current, new_status)
                )
            if new_status == "verified":
                _check_verifier_not_collector(
                    record["collected_by"], actor_name(actor)
                )
                record["verified_by"] = actor_name(actor)
            if new_status == "collected":
                record["collected_by"] = actor_name(actor)
            record["status"] = new_status
            record["updated_utc"] = _utc_now()
            self._audit(actor, "evidence_task_transition", task_id,
                        details={"from": current, "to": new_status})
            return copy.deepcopy(record)

    def list_evidence_tasks(self, actor, framework_id=None, status=None):
        return self._list("evidence_tasks", actor,
                          {"framework_id": framework_id, "status": status})

    # -- identity products (hooks only, no IdP) ---------------------------

    def register_identity_hook(self, product_ref, hook_kind,
                               integration_point, actor):
        """Register an identity-product integration hook. The record
        describes where an external identity product plugs in; this
        build authenticates no one and provides no identity service,
        which the record states in its own fields."""
        _validate_ref(product_ref, "product reference")
        _validate_choice(hook_kind, HOOK_KINDS, "hook kind")
        _validate_non_empty(integration_point, "integration point")
        self._require(actor, "manage_assets", "hook_register", product_ref)
        with self._lock:
            return self._insert(
                "hooks", "hook",
                {
                    "product_ref": product_ref,
                    "hook_kind": hook_kind,
                    "integration_point": integration_point,
                    "hook_only": True,
                    "identity_provider": False,
                },
                actor, "hook_register",
            )

    def list_identity_hooks(self, actor, hook_kind=None):
        return self._list("hooks", actor, {"hook_kind": hook_kind})

    # -- phishing defense & training (records form) -----------------------

    def create_campaign(self, campaign_ref, title, audience_ref, actor):
        """Create a phishing-awareness campaign record. This module
        sends nothing and simulates nothing; the campaign is a
        program record with a lifecycle and training assignments."""
        _validate_ref(campaign_ref, "campaign reference")
        _validate_non_empty(title, "campaign title")
        _validate_ref(audience_ref, "audience reference")
        self._require(actor, "manage_risks", "campaign_create", campaign_ref)
        with self._lock:
            return self._insert(
                "campaigns", "campaign",
                {
                    "campaign_ref": campaign_ref,
                    "title": title,
                    "audience_ref": audience_ref,
                    "status": "planned",
                    "messages_sent": False,
                },
                actor, "campaign_create",
            )

    def transition_campaign(self, campaign_id, new_status, actor):
        self._require(actor, "triage", "campaign_transition", campaign_id)
        with self._lock:
            record = self._get("campaigns", campaign_id, "campaign")
            current = record["status"]
            if new_status not in CAMPAIGN_TRANSITIONS[current]:
                raise ValidationError(
                    "campaign cannot move from %r to %r" % (current, new_status)
                )
            record["status"] = new_status
            record["updated_utc"] = _utc_now()
            self._audit(actor, "campaign_transition", campaign_id,
                        details={"from": current, "to": new_status})
            return copy.deepcopy(record)

    def list_campaigns(self, actor, status=None):
        return self._list("campaigns", actor, {"status": status})

    def assign_training(self, campaign_id, learner_ref, actor):
        """Assign training under a campaign to an opaque learner
        reference. No name, address, or other PII is recordable."""
        _validate_ref(learner_ref, "learner reference")
        self._require(actor, "manage_risks", "training_assign", campaign_id)
        with self._lock:
            self._get("campaigns", campaign_id, "campaign")
            return self._insert(
                "assignments", "assign",
                {
                    "campaign_id": campaign_id,
                    "learner_ref": learner_ref,
                    "status": "assigned",
                },
                actor, "training_assign",
            )

    def complete_training(self, assignment_id, actor):
        self._require(actor, "triage", "training_complete", assignment_id)
        with self._lock:
            record = self._get("assignments", assignment_id, "training assignment")
            if record["status"] != "assigned":
                raise ValidationError(
                    "training assignment cannot move from %r to 'completed'"
                    % (record["status"],)
                )
            record["status"] = "completed"
            record["updated_utc"] = _utc_now()
            self._audit(actor, "training_complete", assignment_id)
            return copy.deepcopy(record)

    def list_assignments(self, actor, campaign_id=None, status=None):
        return self._list("assignments", actor,
                          {"campaign_id": campaign_id, "status": status})

    def campaign_counts(self, actor, campaign_id):
        """Derived training counts for one campaign: totals by
        assignment status, computed at read. Counts only."""
        self._require(actor, "read", "campaign_counts", campaign_id)
        with self._lock:
            self._get("campaigns", campaign_id, "campaign")
            by_status = {"assigned": 0, "completed": 0}
            for record in self._data["assignments"].values():
                if record["campaign_id"] == campaign_id:
                    by_status[record["status"]] += 1
            return {
                "campaign_id": campaign_id,
                "total": by_status["assigned"] + by_status["completed"],
                "by_status": by_status,
            }

    # -- DMARC enforcement (records form) ---------------------------------

    def register_dmarc_policy(self, domain_ref, policy, actor):
        """Register a DMARC policy record for an opaque domain
        reference. ``policy`` is DMARC's own published vocabulary
        (none / quarantine / reject), stored as the external
        platform's declared policy. This module enforces nothing:
        the record states ``enforced_here: false``."""
        _validate_ref(domain_ref, "domain reference")
        _validate_choice(policy, DMARC_POLICIES, "DMARC policy")
        self._require(actor, "manage_assets", "dmarc_policy_register", domain_ref)
        with self._lock:
            return self._insert(
                "dmarc_policies", "dmarc",
                {
                    "domain_ref": domain_ref,
                    "policy": policy,
                    "enforced_here": False,
                },
                actor, "dmarc_policy_register",
            )

    def list_dmarc_policies(self, actor, policy=None):
        return self._list("dmarc_policies", actor, {"policy": policy})

    def record_dmarc_report(self, policy_id, reported_counts, actor):
        """Record one aggregate DMARC report as reported by the
        external enforcement platform: message counts keyed by the
        reporter's own outcome labels, stored as reported. No
        message is inspected, aligned, or rejected here."""
        counts = _validate_counts(reported_counts, "reported counts")
        self._require(actor, "ingest", "dmarc_report_record", policy_id)
        with self._lock:
            self._get("dmarc_policies", policy_id, "DMARC policy")
            return self._insert(
                "dmarc_reports", "dmarcrep",
                {
                    "policy_id": policy_id,
                    "reported_counts": counts,
                    "enforced_here": False,
                },
                actor, "dmarc_report_record",
            )

    def list_dmarc_reports(self, actor, policy_id=None):
        return self._list("dmarc_reports", actor, {"policy_id": policy_id})

    def dmarc_counts(self, actor, policy_id):
        """Derived totals for one DMARC policy record: the number
        of reports recorded and the sum of their reported message
        counts per outcome label, computed at read. These are sums
        of data the external platform reported, not a score."""
        self._require(actor, "read", "dmarc_counts", policy_id)
        with self._lock:
            self._get("dmarc_policies", policy_id, "DMARC policy")
            reports = 0
            totals = {}
            for record in self._data["dmarc_reports"].values():
                if record["policy_id"] == policy_id:
                    reports += 1
                    for key, value in record["reported_counts"].items():
                        totals[key] = totals.get(key, 0) + value
            return {
                "policy_id": policy_id,
                "reports": reports,
                "reported_totals": totals,
            }

    # -- AI/ML detection models (labeled reference implementation) ---------

    def register_model_reference(self, model_ref, kind, actor):
        """Register a reference record for an external detection
        model. Labeled ``reference_stub``: no model is loaded, no
        inference runs, and no score is produced here."""
        _validate_ref(model_ref, "model reference")
        _validate_choice(kind, MODEL_KINDS, "model kind")
        self._require(actor, "manage_assets", "model_register", model_ref)
        with self._lock:
            return self._insert(
                "models", "model",
                {"model_ref": model_ref, "kind": kind,
                 "reference_stub": True},
                actor, "model_register",
            )

    def list_model_references(self, actor, kind=None):
        return self._list("models", actor, {"kind": kind})

    def record_model_output_reference(self, model_id, finding_ref,
                                      reported_label, actor):
        """Record one model output reported by an external model,
        labeled as a reference record. The label is stored as
        reported; nothing is inferred and no verdict is computed —
        a detector's verdict is its own inference, recorded here,
        never reproduced."""
        _validate_ref(finding_ref, "finding reference")
        _validate_non_empty(reported_label, "reported label")
        self._require(actor, "ingest", "model_output_record", model_id)
        with self._lock:
            self._get("models", model_id, "model reference")
            return self._insert(
                "model_outputs", "modelout",
                {
                    "model_id": model_id,
                    "finding_ref": finding_ref,
                    "reported_label": reported_label,
                    "reference_stub": True,
                },
                actor, "model_output_record",
            )

    def list_model_outputs(self, actor, model_id=None):
        return self._list("model_outputs", actor, {"model_id": model_id})

    # -- SOAR / orchestration (labeled reference implementation) -----------

    def register_playbook_reference(self, playbook_ref, title, actor):
        """Register a reference record for an external SOAR
        playbook: a definition held as data. Labeled
        ``reference_stub``: no playbook executes here, ever — the
        registry never executes."""
        _validate_ref(playbook_ref, "playbook reference")
        _validate_non_empty(title, "playbook title")
        self._require(actor, "manage_assets", "playbook_register", playbook_ref)
        with self._lock:
            return self._insert(
                "playbooks", "playbook",
                {"playbook_ref": playbook_ref, "title": title,
                 "reference_stub": True},
                actor, "playbook_register",
            )

    def list_playbook_references(self, actor):
        return self._list("playbooks", actor)

    def record_playbook_run_reference(self, playbook_id, trigger_ref, actor):
        """Record that an external playbook run was reported. The
        record is a reference stub and states ``executed: false`` —
        the run did not happen here."""
        _validate_ref(trigger_ref, "trigger reference")
        self._require(actor, "ingest", "playbook_run_record", playbook_id)
        with self._lock:
            self._get("playbooks", playbook_id, "playbook reference")
            return self._insert(
                "playbook_runs", "playrun",
                {
                    "playbook_id": playbook_id,
                    "trigger_ref": trigger_ref,
                    "reference_stub": True,
                    "executed": False,
                },
                actor, "playbook_run_record",
            )

    def list_playbook_runs(self, actor, playbook_id=None):
        return self._list("playbook_runs", actor, {"playbook_id": playbook_id})

    # -- summary ------------------------------------------------------------

    def extension_summary(self, actor):
        """Derived summary over every extension collection: record
        counts only, computed at read, never stored. By design there
        is no score, rate, or grade anywhere in this view."""
        self._require(actor, "read", "extension_summary", "extensions")
        with self._lock:
            return {
                "records": {
                    name: len(self._data[name]) for name in self._COLLECTIONS
                },
                "total": sum(
                    len(records) for records in self._data.values()
                ),
            }
