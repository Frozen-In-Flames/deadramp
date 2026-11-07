"""Final GAPS batch extensions for the Cybersecurity L2 build.

Clean-room extension surface for the Extended families named in
``UNION-SPEC.md`` and registered in the repo-root ``GAPS.md``. The
category discipline of the founding build is unchanged and is the
whole point of this module:

- This is the shared **defensive substrate only**. Nothing here
  scans, detects, enforces, blocks, trains, monitors, or executes.
  Where an entry names an engine, a plane, or an agent, this module
  implements the **records form** of that family: registries of the
  thing, ingestion records for its output, and tracking workflows
  around it.
- Families whose honest form is an engine over external systems ship
  as **labeled reference implementations**: their records carry
  ``reference_stub: true`` (pipeline receipts additionally carry
  ``reference_transport: true``), and run-shaped records carry
  ``executed: false``. Nothing here runs a model, a playbook, a
  backup, a DLP monitor, or a pipeline.
- **No scoring is invented.** The only scores in this package remain
  the founding build's published formulas in :mod:`cyber.store`.
  Extension posture views are counts only.
- **Identity is hooks, never an IdP** (PLATFORM-LAYER.md decision 1):
  identity-product records describe an integration hook and carry
  ``identity_provider: false``; proofing records store an outcome
  *reported by* an external service and make no decision.
- References are **opaque**: asset, subject, learner, and system
  references are caller-chosen opaque tokens. Values that look like
  IP addresses, URLs, or hostnames are rejected at the boundary, so a
  record cannot quietly carry a real system's address; no record
  shape has a field for a credential or for PII.

Access control reuses the founding permission matrix (no new
actions): registry creates use ``manage_assets``, ingestion-shaped
records use ``ingest``, lifecycle transitions use ``triage``, GRC
automation records use ``assess_controls``, and reads use ``read``.
Denied attempts are recorded to the audit log with a ``:denied``
suffix before the denial propagates, following the founding build's
practice of auditing denied attempts.
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

PLANE_KINDS = (
    "segmentation",
    "firewall",
    "waf",
    "ztna",
    "sse",
    "browser_isolation",
)

FEED_KINDS = ("ioc", "vulnerability", "actor_tracking", "research")

INDICATOR_KINDS = ("hash", "domain_ref", "file_ref", "technique", "other")

REPORTED_LEVELS = ("low", "medium", "high", "critical")

INTEL_ITEM_TRANSITIONS = {
    "new": {"reviewed", "retired"},
    "reviewed": {"retired"},
    "retired": set(),
}

EVIDENCE_TASK_TRANSITIONS = {
    "open": {"collected", "cancelled"},
    "collected": {"verified"},
    "verified": set(),
    "cancelled": set(),
}

HOOK_KINDS = ("sso", "mfa", "pam", "iga", "directory")

AGENT_REPORTED_STATUSES = ("healthy", "degraded", "offline", "unknown")

CAMPAIGN_TRANSITIONS = {
    "planned": {"approved", "cancelled"},
    "approved": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}

APPSEC_ENGINE_KINDS = ("sast", "dast", "sca", "pentest", "api")

POSTURE_ENGINE_KINDS = ("cspm", "cnapp", "sspm")

PATCH_STATUSES = ("applied", "pending", "failed")

MGMT_CAPABILITIES = ("patching", "configuration", "automation")

PROOFING_METHODS = ("document", "knowledge_based", "biometric_assertion")

REPORTED_OUTCOMES = ("passed", "failed", "inconclusive")

MODEL_KINDS = ("anomaly_detection", "classification", "triage_assist", "other")

DLP_CHANNELS = ("endpoint", "network", "email", "cloud", "other")


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
        "planes",
        "feeds",
        "intel_items",
        "frameworks",
        "evidence_tasks",
        "hooks",
        "edr_agents",
        "campaigns",
        "assignments",
        "appsec_engines",
        "appsec_runs",
        "posture_engines",
        "snapshots",
        "scanners",
        "scan_records",
        "enclaves",
        "sessions",
        "mgmt_agents",
        "patch_records",
        "proofing_records",
        "models",
        "model_outputs",
        "playbooks",
        "playbook_runs",
        "backup_products",
        "backup_jobs",
        "dlp_engines",
        "dlp_alerts",
        "pipelines",
        "pipeline_receipts",
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

    # -- network enforcement planes (records form) ---------------------

    def register_enforcement_point(self, plane_ref, kind, scope_ref,
                                   policy_ref, actor):
        """Register one enforcement point (a firewall, a segmentation
        plane, a ZTNA broker, ...) as a record. Nothing is enforced:
        the record names the plane, the opaque scope it covers, and
        the opaque policy reference it answers to."""
        _validate_ref(plane_ref, "plane reference")
        _validate_choice(kind, PLANE_KINDS, "plane kind")
        _validate_ref(scope_ref, "scope reference")
        _validate_ref(policy_ref, "policy reference")
        self._require(actor, "manage_assets", "plane_register", plane_ref)
        with self._lock:
            return self._insert(
                "planes", "plane",
                {
                    "plane_ref": plane_ref,
                    "kind": kind,
                    "scope_ref": scope_ref,
                    "policy_ref": policy_ref,
                    "status": "registered",
                },
                actor, "plane_register",
            )

    def retire_enforcement_point(self, plane_id, actor):
        """Retire a registered enforcement point record."""
        self._require(actor, "triage", "plane_retire", plane_id)
        with self._lock:
            record = self._get("planes", plane_id, "enforcement point")
            if record["status"] != "registered":
                raise ValidationError(
                    "enforcement point cannot move from %r to 'retired'"
                    % (record["status"],)
                )
            record["status"] = "retired"
            record["updated_utc"] = _utc_now()
            self._audit(actor, "plane_retire", plane_id)
            return copy.deepcopy(record)

    def list_enforcement_points(self, actor, kind=None, status=None):
        return self._list("planes", actor, {"kind": kind, "status": status})

    def enforcement_coverage(self, actor):
        """Derived coverage view: counts of registered enforcement
        points by kind. Counts only; computed at read, never stored."""
        self._require(actor, "read", "plane_coverage", "planes")
        with self._lock:
            by_kind = {name: 0 for name in PLANE_KINDS}
            total = 0
            for record in self._data["planes"].values():
                if record["status"] == "registered":
                    by_kind[record["kind"]] += 1
                    total += 1
            return {"total_registered": total, "by_kind": by_kind}

    # -- threat-intelligence feeds (records form) -----------------------

    def register_intel_feed(self, feed_ref, provider_ref, kind, actor):
        """Register a threat-intelligence feed as a record. No feed
        is fetched or curated here; items arrive by ingestion."""
        _validate_ref(feed_ref, "feed reference")
        _validate_ref(provider_ref, "provider reference")
        _validate_choice(kind, FEED_KINDS, "feed kind")
        self._require(actor, "manage_assets", "feed_register", feed_ref)
        with self._lock:
            return self._insert(
                "feeds", "feed",
                {"feed_ref": feed_ref, "provider_ref": provider_ref,
                 "kind": kind, "status": "registered"},
                actor, "feed_register",
            )

    def list_intel_feeds(self, actor, kind=None):
        return self._list("feeds", actor, {"kind": kind})

    def ingest_intel_item(self, feed_id, indicator_ref, indicator_kind,
                          reported_level, actor, summary=""):
        """Ingest one intelligence item reported by a registered
        feed. ``reported_level`` is the feed's own level, stored as
        reported; this build computes no score for it."""
        _validate_ref(indicator_ref, "indicator reference")
        _validate_choice(indicator_kind, INDICATOR_KINDS, "indicator kind")
        _validate_choice(reported_level, REPORTED_LEVELS, "reported level")
        if not isinstance(summary, str):
            raise ValidationError("summary must be a string")
        self._require(actor, "ingest", "intel_ingest", indicator_ref)
        with self._lock:
            self._get("feeds", feed_id, "intel feed")
            return self._insert(
                "intel_items", "intel",
                {
                    "feed_id": feed_id,
                    "indicator_ref": indicator_ref,
                    "indicator_kind": indicator_kind,
                    "reported_level": reported_level,
                    "summary": summary,
                    "status": "new",
                },
                actor, "intel_ingest",
            )

    def transition_intel_item(self, item_id, new_status, actor):
        self._require(actor, "triage", "intel_transition", item_id)
        with self._lock:
            record = self._get("intel_items", item_id, "intel item")
            current = record["status"]
            if new_status not in INTEL_ITEM_TRANSITIONS[current]:
                raise ValidationError(
                    "intel item cannot move from %r to %r" % (current, new_status)
                )
            record["status"] = new_status
            record["updated_utc"] = _utc_now()
            self._audit(actor, "intel_transition", item_id,
                        details={"from": current, "to": new_status})
            return copy.deepcopy(record)

    def list_intel_items(self, actor, feed_id=None, status=None):
        return self._list("intel_items", actor,
                          {"feed_id": feed_id, "status": status})

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

    # -- EDR / XDR agents (records form) ----------------------------------

    def register_edr_agent(self, agent_ref, asset_ref, actor):
        """Register an endpoint agent enrollment record. No agent
        runs here; health arrives as reported status records."""
        _validate_ref(agent_ref, "agent reference")
        _validate_ref(asset_ref, "asset reference")
        self._require(actor, "manage_assets", "edr_register", agent_ref)
        with self._lock:
            return self._insert(
                "edr_agents", "edr",
                {
                    "agent_ref": agent_ref,
                    "asset_ref": asset_ref,
                    "last_reported_status": "unknown",
                },
                actor, "edr_register",
            )

    def record_agent_report(self, agent_id, reported_status, actor):
        """Record a health status reported by an external agent."""
        _validate_choice(reported_status, AGENT_REPORTED_STATUSES,
                         "reported status")
        self._require(actor, "ingest", "edr_report", agent_id)
        with self._lock:
            record = self._get("edr_agents", agent_id, "EDR agent")
            record["last_reported_status"] = reported_status
            record["updated_utc"] = _utc_now()
            self._audit(actor, "edr_report", agent_id,
                        details={"reported_status": reported_status})
            return copy.deepcopy(record)

    def list_edr_agents(self, actor, asset_ref=None):
        return self._list("edr_agents", actor, {"asset_ref": asset_ref})

    # -- phishing simulation & training (records form) --------------------

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

    # -- AppSec testing engines (records form) ------------------------------

    def register_appsec_engine(self, engine_ref, kind, actor):
        """Register an application-security testing engine record.
        No test is executed here; runs arrive as records."""
        _validate_ref(engine_ref, "engine reference")
        _validate_choice(kind, APPSEC_ENGINE_KINDS, "engine kind")
        self._require(actor, "manage_assets", "appsec_register", engine_ref)
        with self._lock:
            return self._insert(
                "appsec_engines", "appsec",
                {"engine_ref": engine_ref, "kind": kind},
                actor, "appsec_register",
            )

    def list_appsec_engines(self, actor, kind=None):
        return self._list("appsec_engines", actor, {"kind": kind})

    def record_appsec_run(self, engine_id, asset_ref, reported_finding_count,
                          actor):
        """Record one test run reported by an external engine,
        including the finding count it reported (stored as reported;
        the findings themselves belong in the core register)."""
        _validate_ref(asset_ref, "asset reference")
        _validate_count(reported_finding_count, "reported finding count")
        self._require(actor, "ingest", "appsec_run_record", engine_id)
        with self._lock:
            self._get("appsec_engines", engine_id, "AppSec engine")
            return self._insert(
                "appsec_runs", "run",
                {
                    "engine_id": engine_id,
                    "asset_ref": asset_ref,
                    "reported_finding_count": reported_finding_count,
                    "executed_here": False,
                },
                actor, "appsec_run_record",
            )

    def list_appsec_runs(self, actor, engine_id=None):
        return self._list("appsec_runs", actor, {"engine_id": engine_id})

    # -- posture engines CSPM/CNAPP/SSPM (records form, counts only) --------

    def register_posture_engine(self, engine_ref, kind, scope_ref, actor):
        """Register a cloud/SaaS posture engine record. Its output
        arrives as count snapshots; this build computes no posture
        score of its own."""
        _validate_ref(engine_ref, "engine reference")
        _validate_choice(kind, POSTURE_ENGINE_KINDS, "engine kind")
        _validate_ref(scope_ref, "scope reference")
        self._require(actor, "manage_assets", "posture_register", engine_ref)
        with self._lock:
            return self._insert(
                "posture_engines", "posture",
                {"engine_ref": engine_ref, "kind": kind,
                 "scope_ref": scope_ref},
                actor, "posture_register",
            )

    def list_posture_engines(self, actor, kind=None):
        return self._list("posture_engines", actor, {"kind": kind})

    def record_posture_snapshot(self, engine_id, counts, actor):
        """Record one posture snapshot: a mapping of category name
        to non-negative integer count, exactly as reported. Counts
        only — a snapshot with any non-count value is rejected."""
        counts = _validate_counts(counts, "snapshot counts")
        self._require(actor, "ingest", "snapshot_record", engine_id)
        with self._lock:
            self._get("posture_engines", engine_id, "posture engine")
            return self._insert(
                "snapshots", "snapshot",
                {"engine_id": engine_id, "counts": counts},
                actor, "snapshot_record",
            )

    def list_snapshots(self, actor, engine_id=None):
        return self._list("snapshots", actor, {"engine_id": engine_id})

    def posture_counts(self, actor, engine_id):
        """Derived aggregate over one engine's snapshots: counts
        summed per category, computed at read, never stored. The
        result contains counts only — no score, rate, or grade."""
        self._require(actor, "read", "posture_counts", engine_id)
        with self._lock:
            self._get("posture_engines", engine_id, "posture engine")
            totals = {}
            snapshots = 0
            for record in self._data["snapshots"].values():
                if record["engine_id"] == engine_id:
                    snapshots += 1
                    for key, value in record["counts"].items():
                        totals[key] = totals.get(key, 0) + value
            return {
                "engine_id": engine_id,
                "snapshots": snapshots,
                "counts": totals,
            }

    # -- vulnerability scanners (registry + scan records) -------------------

    def register_scanner(self, scanner_ref, actor):
        """Register a vulnerability scanner product record. Scanning
        is not performed; scanner output lands in the core register
        as findings, and scan events are tracked here."""
        _validate_ref(scanner_ref, "scanner reference")
        self._require(actor, "manage_assets", "scanner_register", scanner_ref)
        with self._lock:
            return self._insert(
                "scanners", "scanner",
                {"scanner_ref": scanner_ref},
                actor, "scanner_register",
            )

    def list_scanners(self, actor):
        return self._list("scanners", actor)

    def record_scan(self, scanner_id, asset_ref, actor):
        """Record that a scan of an opaque asset reference was
        reported by a registered scanner."""
        _validate_ref(asset_ref, "asset reference")
        self._require(actor, "ingest", "scan_record", scanner_id)
        with self._lock:
            self._get("scanners", scanner_id, "scanner")
            return self._insert(
                "scan_records", "scan",
                {"scanner_id": scanner_id, "asset_ref": asset_ref,
                 "executed_here": False},
                actor, "scan_record",
            )

    def list_scan_records(self, actor, scanner_id=None, asset_ref=None):
        return self._list("scan_records", actor,
                          {"scanner_id": scanner_id, "asset_ref": asset_ref})

    # -- CUI enclaves / VDI (records form) ------------------------------------

    def register_enclave(self, enclave_ref, data_label, actor):
        """Register a secure enclave / VDI environment record. No
        environment is hosted here; sessions are tracked records."""
        _validate_ref(enclave_ref, "enclave reference")
        _validate_non_empty(data_label, "data label")
        self._require(actor, "manage_assets", "enclave_register", enclave_ref)
        with self._lock:
            return self._insert(
                "enclaves", "enclave",
                {"enclave_ref": enclave_ref, "data_label": data_label,
                 "hosted_here": False},
                actor, "enclave_register",
            )

    def list_enclaves(self, actor):
        return self._list("enclaves", actor)

    def start_enclave_session(self, enclave_id, user_ref, actor):
        """Record the start of an enclave session for an opaque
        user reference."""
        _validate_ref(user_ref, "user reference")
        self._require(actor, "ingest", "session_start", enclave_id)
        with self._lock:
            self._get("enclaves", enclave_id, "enclave")
            return self._insert(
                "sessions", "session",
                {"enclave_id": enclave_id, "user_ref": user_ref,
                 "status": "active"},
                actor, "session_start",
            )

    def end_enclave_session(self, session_id, actor):
        self._require(actor, "triage", "session_end", session_id)
        with self._lock:
            record = self._get("sessions", session_id, "enclave session")
            if record["status"] != "active":
                raise ValidationError(
                    "enclave session cannot move from %r to 'ended'"
                    % (record["status"],)
                )
            record["status"] = "ended"
            record["updated_utc"] = _utc_now()
            self._audit(actor, "session_end", session_id)
            return copy.deepcopy(record)

    def list_sessions(self, actor, enclave_id=None, status=None):
        return self._list("sessions", actor,
                          {"enclave_id": enclave_id, "status": status})

    def active_session_count(self, actor, enclave_id):
        """Derived count of active sessions on one enclave, computed
        at read, never stored."""
        self._require(actor, "read", "session_count", enclave_id)
        with self._lock:
            self._get("enclaves", enclave_id, "enclave")
            count = sum(
                1
                for record in self._data["sessions"].values()
                if record["enclave_id"] == enclave_id
                and record["status"] == "active"
            )
            return {"enclave_id": enclave_id, "active_sessions": count}

    # -- endpoint management agents (records form) -----------------------------

    def register_mgmt_agent(self, agent_ref, asset_ref, capabilities, actor):
        """Register an endpoint management agent record with its
        declared capabilities. No patching or automation runs here."""
        _validate_ref(agent_ref, "agent reference")
        _validate_ref(asset_ref, "asset reference")
        if not isinstance(capabilities, list) or not capabilities:
            raise ValidationError("capabilities must be a non-empty list")
        for capability in capabilities:
            _validate_choice(capability, MGMT_CAPABILITIES, "capability")
        self._require(actor, "manage_assets", "mgmt_register", agent_ref)
        with self._lock:
            return self._insert(
                "mgmt_agents", "mgmt",
                {
                    "agent_ref": agent_ref,
                    "asset_ref": asset_ref,
                    "capabilities": list(capabilities),
                },
                actor, "mgmt_register",
            )

    def list_mgmt_agents(self, actor, asset_ref=None):
        return self._list("mgmt_agents", actor, {"asset_ref": asset_ref})

    def record_patch_status(self, agent_id, patch_ref, reported_status, actor):
        """Record a patch status reported by an external management
        agent (stored as reported; nothing is applied here)."""
        _validate_ref(patch_ref, "patch reference")
        _validate_choice(reported_status, PATCH_STATUSES, "reported status")
        self._require(actor, "ingest", "patch_record", agent_id)
        with self._lock:
            self._get("mgmt_agents", agent_id, "management agent")
            return self._insert(
                "patch_records", "patch",
                {
                    "agent_id": agent_id,
                    "patch_ref": patch_ref,
                    "reported_status": reported_status,
                    "applied_here": False,
                },
                actor, "patch_record",
            )

    def list_patch_records(self, actor, agent_id=None, reported_status=None):
        return self._list("patch_records", actor,
                          {"agent_id": agent_id,
                           "reported_status": reported_status})

    # -- identity proofing / fraud (reported-outcome records only) -------------

    def record_proofing_check(self, subject_ref, method, reported_outcome,
                              actor):
        """Record an identity-proofing check performed by an
        external service. The outcome is stored exactly as reported;
        this build proof-checks no one, scores no one, and makes no
        decision — the record itself carries ``decision_made:
        false``."""
        _validate_ref(subject_ref, "subject reference")
        _validate_choice(method, PROOFING_METHODS, "proofing method")
        _validate_choice(reported_outcome, REPORTED_OUTCOMES, "reported outcome")
        self._require(actor, "ingest", "proofing_record", subject_ref)
        with self._lock:
            return self._insert(
                "proofing_records", "proof",
                {
                    "subject_ref": subject_ref,
                    "method": method,
                    "reported_outcome": reported_outcome,
                    "decision_made": False,
                },
                actor, "proofing_record",
            )

    def list_proofing_records(self, actor, subject_ref=None):
        return self._list("proofing_records", actor,
                          {"subject_ref": subject_ref})

    # -- AI/ML detection models (labeled reference implementation) -------------

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
        reported; nothing is inferred."""
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

    # -- SOAR / orchestration (labeled reference implementation) ----------------

    def register_playbook_reference(self, playbook_ref, title, actor):
        """Register a reference record for an external SOAR
        playbook. Labeled ``reference_stub``: no playbook executes
        here, ever."""
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

    # -- backup / recovery products (labeled reference implementation) -----------

    def register_backup_product_reference(self, product_ref, actor):
        """Register a reference record for an external backup /
        recovery product. Labeled ``reference_stub``: no backup is
        taken and nothing is restored here."""
        _validate_ref(product_ref, "product reference")
        self._require(actor, "manage_assets", "backup_register", product_ref)
        with self._lock:
            return self._insert(
                "backup_products", "backup",
                {"product_ref": product_ref, "reference_stub": True},
                actor, "backup_register",
            )

    def list_backup_product_references(self, actor):
        return self._list("backup_products", actor)

    def record_backup_job_reference(self, product_id, asset_ref,
                                    reported_status, actor):
        """Record one backup job reported by an external product,
        labeled as a reference record with its status as reported."""
        _validate_ref(asset_ref, "asset reference")
        _validate_non_empty(reported_status, "reported status")
        self._require(actor, "ingest", "backup_job_record", product_id)
        with self._lock:
            self._get("backup_products", product_id, "backup product reference")
            return self._insert(
                "backup_jobs", "backupjob",
                {
                    "product_id": product_id,
                    "asset_ref": asset_ref,
                    "reported_status": reported_status,
                    "reference_stub": True,
                    "executed_here": False,
                },
                actor, "backup_job_record",
            )

    def list_backup_jobs(self, actor, product_id=None):
        return self._list("backup_jobs", actor, {"product_id": product_id})

    # -- DLP / insider monitoring (labeled reference implementation) --------------

    def register_dlp_engine_reference(self, engine_ref, channel, actor):
        """Register a reference record for an external DLP /
        insider-monitoring engine. Labeled ``reference_stub``: no
        content is inspected and no one is monitored here."""
        _validate_ref(engine_ref, "engine reference")
        _validate_choice(channel, DLP_CHANNELS, "DLP channel")
        self._require(actor, "manage_assets", "dlp_register", engine_ref)
        with self._lock:
            return self._insert(
                "dlp_engines", "dlp",
                {"engine_ref": engine_ref, "channel": channel,
                 "reference_stub": True},
                actor, "dlp_register",
            )

    def list_dlp_engine_references(self, actor, channel=None):
        return self._list("dlp_engines", actor, {"channel": channel})

    def record_dlp_alert_reference(self, engine_id, asset_ref,
                                   reported_level, actor):
        """Record one DLP alert reported by an external engine,
        labeled as a reference record with its level as reported."""
        _validate_ref(asset_ref, "asset reference")
        _validate_choice(reported_level, REPORTED_LEVELS, "reported level")
        self._require(actor, "ingest", "dlp_alert_record", engine_id)
        with self._lock:
            self._get("dlp_engines", engine_id, "DLP engine reference")
            return self._insert(
                "dlp_alerts", "dlpalert",
                {
                    "engine_id": engine_id,
                    "asset_ref": asset_ref,
                    "reported_level": reported_level,
                    "reference_stub": True,
                },
                actor, "dlp_alert_record",
            )

    def list_dlp_alerts(self, actor, engine_id=None):
        return self._list("dlp_alerts", actor, {"engine_id": engine_id})

    # -- log / telemetry pipelines (labeled reference implementation) -------------

    def register_pipeline_reference(self, pipeline_ref, actor):
        """Register a reference record for an external log /
        telemetry pipeline. Labeled ``reference_stub``: no events
        flow through here; movement is recorded as receipts."""
        _validate_ref(pipeline_ref, "pipeline reference")
        self._require(actor, "manage_assets", "pipeline_register", pipeline_ref)
        with self._lock:
            return self._insert(
                "pipelines", "pipeline",
                {"pipeline_ref": pipeline_ref, "reference_stub": True},
                actor, "pipeline_register",
            )

    def list_pipeline_references(self, actor):
        return self._list("pipelines", actor)

    def record_pipeline_receipt(self, pipeline_id, batch_ref, event_count,
                                actor):
        """Record a transport receipt for one batch an external
        pipeline reports having moved. The receipt carries
        ``reference_transport: true``: it attests a record of
        movement, not movement through this build."""
        _validate_ref(batch_ref, "batch reference")
        _validate_count(event_count, "event count")
        self._require(actor, "ingest", "pipeline_receipt_record", pipeline_id)
        with self._lock:
            self._get("pipelines", pipeline_id, "pipeline reference")
            return self._insert(
                "pipeline_receipts", "receipt",
                {
                    "pipeline_id": pipeline_id,
                    "batch_ref": batch_ref,
                    "event_count": event_count,
                    "reference_stub": True,
                    "reference_transport": True,
                },
                actor, "pipeline_receipt_record",
            )

    def list_pipeline_receipts(self, actor, pipeline_id=None):
        return self._list("pipeline_receipts", actor,
                          {"pipeline_id": pipeline_id})

    # -- derived extension summary (counts only) ----------------------------------

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
