"""Cybersecurity store: assets, findings, risks, and control assessments.

Clean-room implementation of the union spec's implementation contract.

The store is an in-memory register:

- **Assets** -- the inventory every finding lands on. Changing an
  asset's criticality recomputes the score and band of every finding
  on that asset.
- **Findings** -- the output of scanners, posture engines, detection
  platforms, and tests, ingested one at a time, in bulk (JSON), or as
  CSV scan results. Bulk and CSV ingestion are atomic: every item is
  validated before any is created, so a bad row rejects the whole
  batch, consumes no ids, and writes no audit entry.
- **Risks** -- standing risks scored likelihood x impact, linked to
  the findings that evidence them.
- **Controls** -- the built-in 34-control catalog (see
  :mod:`cyber.catalog`), each carrying an assessment status and an
  evidence note.

Risk scoring is a deterministic, published formula (severity weight x
asset criticality weight for findings; likelihood x impact for risks)
-- no ML, no hidden model. Same inputs, same score, always.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``asset-``, ``find-``, ``risk-``).
The store records every successful mutation and every search to its
audit log (when one is attached). Reads other than search, and the
posture summary, are not audited here; denied attempts and audit reads
are the HTTP layer's responsibility, so nothing is recorded twice.
"""

import csv
import io
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .catalog import CONTROL_CATALOG, CONTROL_IDS, control_by_id
from .errors import NotFoundError, ValidationError

SEVERITIES = ("critical", "high", "medium", "low", "info")

SEVERITY_WEIGHTS = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}

CRITICALITIES = ("critical", "high", "medium", "low")

CRITICALITY_WEIGHTS = {"critical": 2.0, "high": 1.5, "medium": 1.0, "low": 0.5}

ASSET_KINDS = (
    "server",
    "workstation",
    "mobile",
    "network",
    "cloud",
    "application",
    "database",
    "other",
)

FINDING_STATUSES = (
    "new",
    "triaged",
    "in_progress",
    "mitigated",
    "accepted",
    "false_positive",
    "closed",
)

FINDING_TRANSITIONS = {
    "new": {"triaged", "false_positive"},
    "triaged": {"in_progress", "accepted", "false_positive"},
    "in_progress": {"mitigated", "accepted"},
    "mitigated": {"closed", "in_progress"},
    "accepted": {"in_progress", "closed"},
    "false_positive": {"closed"},
    "closed": set(),
}

RISK_STATUSES = ("open", "monitoring", "treated", "closed")

RISK_TRANSITIONS = {
    "open": {"monitoring", "treated", "closed"},
    "monitoring": {"open", "treated", "closed"},
    "treated": {"monitoring", "closed"},
    "closed": {"open"},
}

ASSESSMENT_STATUSES = (
    "not_assessed",
    "implemented",
    "partially_implemented",
    "not_implemented",
)

_BANDS = ("critical", "high", "medium", "low")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def score_finding(severity, criticality):
    """Return ``(score, band)`` for a finding: severity weight times
    asset criticality weight, banded at 8 / 5 / 2.5."""
    if severity not in SEVERITY_WEIGHTS:
        raise ValidationError("severity must be one of %s" % (", ".join(SEVERITIES),))
    if criticality not in CRITICALITY_WEIGHTS:
        raise ValidationError(
            "criticality must be one of %s" % (", ".join(CRITICALITIES),)
        )
    score = SEVERITY_WEIGHTS[severity] * CRITICALITY_WEIGHTS[criticality]
    if score >= 8:
        band = "critical"
    elif score >= 5:
        band = "high"
    elif score >= 2.5:
        band = "medium"
    else:
        band = "low"
    return (score, band)


def risk_score(likelihood, impact):
    """Return the risk score for ``likelihood`` x ``impact``."""
    return likelihood * impact


def risk_band(score):
    """Return the band for a risk score: critical >= 15, high >= 10,
    medium >= 5, else low."""
    if score >= 15:
        return "critical"
    if score >= 10:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


def _maybe_require(actor, action):
    """Enforce permissions when ``actor`` is a User-like object.

    Plain string actors carry identity (for provenance) but no role, so
    there is nothing to enforce against; enforcement for those happens
    in the service layer, which knows the role registry.
    """
    if actor is not None and hasattr(actor, "role"):
        require(actor, action)


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_tags(tags):
    if tags is None:
        return []
    if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
        raise ValidationError("tags must be a list of strings")
    return list(tags)


def _validate_control_ids(control_ids):
    if control_ids is None:
        return []
    if not isinstance(control_ids, list) or any(
        not isinstance(control_id, str) for control_id in control_ids
    ):
        raise ValidationError("control_ids must be a list of control id strings")
    for control_id in control_ids:
        if control_id not in CONTROL_IDS:
            raise ValidationError("unknown control id: %r" % (control_id,))
    return list(control_ids)


def _id_sort_key(object_id):
    """Sort key ordering prefixed sequential ids numerically."""
    try:
        return int(object_id.rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


def _finding_sort_key(finding):
    return (-finding["score"], _id_sort_key(finding["id"]))


def _risk_sort_key(risk):
    return (-risk["score"], _id_sort_key(risk["id"]))


class CyberStore:
    """In-memory store for the cybersecurity register."""

    def __init__(self, audit=None):
        self.audit = audit
        self._assets = {}  # id -> asset dict
        self._findings = {}  # id -> finding dict
        self._risks = {}  # id -> risk dict
        self._control_state = {
            entry["id"]: {
                "status": "not_assessed",
                "evidence": "",
                "assessed_by": None,
                "assessed_utc": None,
            }
            for entry in CONTROL_CATALOG
        }
        self._counters = {"asset": 0, "find": 0, "risk": 0}
        self._lock = threading.RLock()

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    @staticmethod
    def _copy_asset(asset):
        copied = dict(asset)
        copied["tags"] = list(asset["tags"])
        return copied

    @staticmethod
    def _copy_finding(finding):
        copied = dict(finding)
        copied["control_ids"] = list(finding["control_ids"])
        return copied

    @staticmethod
    def _copy_risk(risk):
        copied = dict(risk)
        copied["finding_ids"] = list(risk["finding_ids"])
        return copied

    def _get_asset_record(self, asset_id):
        asset = self._assets.get(asset_id)
        if asset is None:
            raise NotFoundError("asset not found: %r" % (asset_id,))
        return asset

    def _get_finding_record(self, finding_id):
        finding = self._findings.get(finding_id)
        if finding is None:
            raise NotFoundError("finding not found: %r" % (finding_id,))
        return finding

    def _get_risk_record(self, risk_id):
        risk = self._risks.get(risk_id)
        if risk is None:
            raise NotFoundError("risk not found: %r" % (risk_id,))
        return risk

    # -- assets --------------------------------------------------------

    def create_asset(self, name, kind, owner, criticality, actor, tags=None):
        """Create an asset in the inventory."""
        _validate_non_empty(name, "asset name")
        if kind not in ASSET_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(ASSET_KINDS),))
        _validate_non_empty(owner, "asset owner")
        if criticality not in CRITICALITIES:
            raise ValidationError(
                "criticality must be one of %s" % (", ".join(CRITICALITIES),)
            )
        tags = _validate_tags(tags)
        _maybe_require(actor, "manage_assets")
        with self._lock:
            asset_id = self._next_id("asset")
            now = _utc_now()
            asset = {
                "id": asset_id,
                "name": name,
                "kind": kind,
                "owner": owner,
                "criticality": criticality,
                "tags": tags,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._assets[asset_id] = asset
            self._audit(actor, "asset_create", asset_id, details={"name": name})
            return self._copy_asset(asset)

    def get_asset(self, asset_id, actor):
        """Return one asset dict."""
        _maybe_require(actor, "read")
        with self._lock:
            return self._copy_asset(self._get_asset_record(asset_id))

    def list_assets(self, actor, q=None):
        """Return asset dicts in id order, optionally filtered by a
        case-insensitive substring over name and owner."""
        if q is not None and not isinstance(q, str):
            raise ValidationError("q must be a string")
        _maybe_require(actor, "read")
        with self._lock:
            assets = [self._copy_asset(asset) for asset in self._assets.values()]
            if q is not None:
                needle = q.lower()
                assets = [
                    asset
                    for asset in assets
                    if needle in asset["name"].lower()
                    or needle in asset["owner"].lower()
                ]
            return assets

    def update_asset(self, asset_id, actor, owner=None, criticality=None, tags=None):
        """Update an asset's owner, criticality, and/or tags.

        Changing ``criticality`` recomputes the score and band of every
        finding on the asset.
        """
        if owner is None and criticality is None and tags is None:
            raise ValidationError(
                "at least one of owner, criticality, or tags must be given"
            )
        if owner is not None:
            _validate_non_empty(owner, "asset owner")
        if criticality is not None and criticality not in CRITICALITIES:
            raise ValidationError(
                "criticality must be one of %s" % (", ".join(CRITICALITIES),)
            )
        if tags is not None:
            tags = _validate_tags(tags)
        _maybe_require(actor, "manage_assets")
        with self._lock:
            asset = self._get_asset_record(asset_id)
            if owner is not None:
                asset["owner"] = owner
            if tags is not None:
                asset["tags"] = tags
            if criticality is not None and criticality != asset["criticality"]:
                asset["criticality"] = criticality
                for finding in self._findings.values():
                    if finding["asset_id"] == asset_id:
                        score, band = score_finding(finding["severity"], criticality)
                        finding["score"] = score
                        finding["band"] = band
            asset["updated_utc"] = _utc_now()
            self._audit(actor, "asset_update", asset_id)
            return self._copy_asset(asset)

    # -- findings --------------------------------------------------------

    def _validate_finding_item(self, item):
        """Validate one raw finding item and return a normalized dict.

        Callers hold the lock; asset existence is checked against the
        live register here so bulk ingestion can validate every item
        before creating any of them.
        """
        if not isinstance(item, dict):
            raise ValidationError("finding item must be an object")
        title = _validate_non_empty(item.get("title"), "finding title")
        severity = item.get("severity")
        if severity not in SEVERITIES:
            raise ValidationError(
                "severity must be one of %s" % (", ".join(SEVERITIES),)
            )
        asset_id = item.get("asset_id")
        if not isinstance(asset_id, str) or asset_id not in self._assets:
            raise ValidationError(
                "asset_id must name an existing asset: %r" % (asset_id,)
            )
        source = _validate_non_empty(item.get("source"), "finding source")
        description = item.get("description", "")
        if description is None:
            description = ""
        if not isinstance(description, str):
            raise ValidationError("description must be a string")
        cve = item.get("cve", None)
        if cve is not None and not isinstance(cve, str):
            raise ValidationError("cve must be a string or None")
        control_ids = _validate_control_ids(item.get("control_ids", []))
        return {
            "title": title,
            "severity": severity,
            "asset_id": asset_id,
            "source": source,
            "description": description,
            "cve": cve,
            "control_ids": control_ids,
        }

    def ingest_findings(self, items, actor):
        """Ingest a list of findings atomically.

        Every item is validated before any is created; on any error
        nothing is created, no ids are consumed, and no audit entry is
        written. One audit entry records the whole batch.
        """
        if not isinstance(items, (list, tuple)):
            raise ValidationError("findings must be a list of finding objects")
        if len(items) == 0:
            raise ValidationError("findings list must not be empty")
        _maybe_require(actor, "ingest")
        with self._lock:
            normalized = [self._validate_finding_item(item) for item in items]
            created = []
            now = _utc_now()
            for item in normalized:
                asset = self._assets[item["asset_id"]]
                score, band = score_finding(item["severity"], asset["criticality"])
                finding_id = self._next_id("find")
                finding = {
                    "id": finding_id,
                    "title": item["title"],
                    "severity": item["severity"],
                    "asset_id": item["asset_id"],
                    "source": item["source"],
                    "description": item["description"],
                    "cve": item["cve"],
                    "control_ids": item["control_ids"],
                    "status": "new",
                    "assignee": None,
                    "score": score,
                    "band": band,
                    "created_by": actor_name(actor),
                    "created_utc": now,
                    "updated_utc": now,
                }
                self._findings[finding_id] = finding
                created.append(finding)
            ids = [finding["id"] for finding in created]
            self._audit(
                actor,
                "finding_ingest",
                ids[0],
                details={"count": len(ids), "ids": ids},
            )
            return [self._copy_finding(finding) for finding in created]

    def ingest_finding(self, item, actor):
        """Ingest a single finding; see :meth:`ingest_findings`."""
        return self.ingest_findings([item], actor)[0]

    def ingest_findings_csv(self, text, actor):
        """Ingest findings from CSV scan results, atomically.

        The CSV must have a header row naming at least ``title``,
        ``severity``, ``asset_id``, and ``source``; ``description``,
        ``cve``, and ``control_ids`` (a semicolon-separated list, empty
        cell = ``[]``) are optional. Parsed rows go through the same
        validation as :meth:`ingest_findings`.
        """
        if not isinstance(text, str) or not text.strip():
            raise ValidationError("CSV input must be a non-empty string")
        _maybe_require(actor, "ingest")
        try:
            reader = csv.DictReader(io.StringIO(text))
            fieldnames = reader.fieldnames
            if not fieldnames:
                raise ValidationError("CSV input has no header row")
            fieldnames = [name.strip() if isinstance(name, str) else name
                          for name in fieldnames]
            required = ("title", "severity", "asset_id", "source")
            missing = [name for name in required if name not in fieldnames]
            if missing:
                raise ValidationError(
                    "CSV header is missing required columns: %s"
                    % (", ".join(missing),)
                )
            items = []
            for row in reader:
                if row is None:
                    continue
                cleaned = {}
                for key, value in row.items():
                    if key is None:
                        continue
                    cleaned[key.strip() if isinstance(key, str) else key] = value
                if all(
                    value is None or (isinstance(value, str) and not value.strip())
                    for value in cleaned.values()
                ):
                    continue
                control_cell = cleaned.get("control_ids")
                if control_cell is None or (
                    isinstance(control_cell, str) and not control_cell.strip()
                ):
                    control_ids = []
                else:
                    control_ids = [
                        part.strip()
                        for part in str(control_cell).split(";")
                        if part.strip()
                    ]
                cve = cleaned.get("cve")
                if isinstance(cve, str) and not cve.strip():
                    cve = None
                items.append(
                    {
                        "title": cleaned.get("title"),
                        "severity": cleaned.get("severity"),
                        "asset_id": cleaned.get("asset_id"),
                        "source": cleaned.get("source"),
                        "description": cleaned.get("description") or "",
                        "cve": cve,
                        "control_ids": control_ids,
                    }
                )
        except csv.Error as exc:
            raise ValidationError("malformed CSV: %s" % (exc,)) from exc
        return self.ingest_findings(items, actor)

    def get_finding(self, finding_id, actor):
        """Return one finding dict."""
        _maybe_require(actor, "read")
        with self._lock:
            return self._copy_finding(self._get_finding_record(finding_id))

    def list_findings(
        self, actor, severity=None, status=None, asset_id=None, source=None, q=None
    ):
        """Return finding dicts matching all given filters, sorted by
        score descending, then id ascending. ``q`` is a
        case-insensitive substring over title, description, and
        source."""
        if q is not None and not isinstance(q, str):
            raise ValidationError("q must be a string")
        _maybe_require(actor, "read")
        with self._lock:
            findings = list(self._findings.values())
            if severity is not None:
                findings = [f for f in findings if f["severity"] == severity]
            if status is not None:
                findings = [f for f in findings if f["status"] == status]
            if asset_id is not None:
                findings = [f for f in findings if f["asset_id"] == asset_id]
            if source is not None:
                findings = [f for f in findings if f["source"] == source]
            if q is not None:
                needle = q.lower()
                findings = [
                    f
                    for f in findings
                    if needle in f["title"].lower()
                    or needle in f["description"].lower()
                    or needle in f["source"].lower()
                ]
            findings.sort(key=_finding_sort_key)
            return [self._copy_finding(f) for f in findings]

    def transition_finding(self, finding_id, new_status, actor):
        """Move a finding through its lifecycle."""
        _maybe_require(actor, "triage")
        with self._lock:
            finding = self._get_finding_record(finding_id)
            current = finding["status"]
            if (
                new_status not in FINDING_STATUSES
                or new_status not in FINDING_TRANSITIONS[current]
            ):
                raise ValidationError(
                    "finding cannot move from %r to %r" % (current, new_status)
                )
            finding["status"] = new_status
            finding["updated_utc"] = _utc_now()
            self._audit(
                actor,
                "finding_transition",
                finding_id,
                details={"from": current, "to": new_status},
            )
            return self._copy_finding(finding)

    def assign_finding(self, finding_id, assignee, actor):
        """Assign a finding, or unassign it with ``assignee=None``."""
        if assignee is not None:
            _validate_non_empty(assignee, "assignee")
        _maybe_require(actor, "triage")
        with self._lock:
            finding = self._get_finding_record(finding_id)
            finding["assignee"] = assignee
            finding["updated_utc"] = _utc_now()
            self._audit(
                actor, "finding_assign", finding_id, details={"assignee": assignee}
            )
            return self._copy_finding(finding)

    # -- risks -----------------------------------------------------------

    @staticmethod
    def _validate_risk_score_input(value, what):
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise ValidationError("%s must be an integer in 1..5" % (what,))
        return value

    def create_risk(
        self, title, description, likelihood, impact, actor, owner="", finding_ids=None
    ):
        """Create a standing risk in the register."""
        _validate_non_empty(title, "risk title")
        if not isinstance(description, str):
            raise ValidationError("description must be a string")
        likelihood = self._validate_risk_score_input(likelihood, "likelihood")
        impact = self._validate_risk_score_input(impact, "impact")
        if not isinstance(owner, str):
            raise ValidationError("owner must be a string")
        if finding_ids is None:
            finding_ids = []
        if not isinstance(finding_ids, list) or any(
            not isinstance(finding_id, str) for finding_id in finding_ids
        ):
            raise ValidationError("finding_ids must be a list of finding id strings")
        _maybe_require(actor, "manage_risks")
        with self._lock:
            for finding_id in finding_ids:
                if finding_id not in self._findings:
                    raise ValidationError(
                        "finding_ids must name existing findings: %r" % (finding_id,)
                    )
            score = risk_score(likelihood, impact)
            risk_id = self._next_id("risk")
            now = _utc_now()
            risk = {
                "id": risk_id,
                "title": title,
                "description": description,
                "likelihood": likelihood,
                "impact": impact,
                "score": score,
                "band": risk_band(score),
                "status": "open",
                "owner": owner,
                "finding_ids": list(finding_ids),
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._risks[risk_id] = risk
            self._audit(actor, "risk_create", risk_id, details={"title": title})
            return self._copy_risk(risk)

    def get_risk(self, risk_id, actor):
        """Return one risk dict."""
        _maybe_require(actor, "read")
        with self._lock:
            return self._copy_risk(self._get_risk_record(risk_id))

    def list_risks(self, actor, status=None, q=None):
        """Return risk dicts matching the filters, sorted by score
        descending, then id ascending. ``q`` is a case-insensitive
        substring over title and description."""
        if q is not None and not isinstance(q, str):
            raise ValidationError("q must be a string")
        _maybe_require(actor, "read")
        with self._lock:
            risks = list(self._risks.values())
            if status is not None:
                risks = [r for r in risks if r["status"] == status]
            if q is not None:
                needle = q.lower()
                risks = [
                    r
                    for r in risks
                    if needle in r["title"].lower()
                    or needle in r["description"].lower()
                ]
            risks.sort(key=_risk_sort_key)
            return [self._copy_risk(r) for r in risks]

    def transition_risk(self, risk_id, new_status, actor):
        """Move a risk through its lifecycle."""
        _maybe_require(actor, "manage_risks")
        with self._lock:
            risk = self._get_risk_record(risk_id)
            current = risk["status"]
            if (
                new_status not in RISK_STATUSES
                or new_status not in RISK_TRANSITIONS[current]
            ):
                raise ValidationError(
                    "risk cannot move from %r to %r" % (current, new_status)
                )
            risk["status"] = new_status
            risk["updated_utc"] = _utc_now()
            self._audit(
                actor,
                "risk_transition",
                risk_id,
                details={"from": current, "to": new_status},
            )
            return self._copy_risk(risk)

    # -- controls ----------------------------------------------------------

    def _control_entry(self, control):
        """Build the public control dict for one catalog entry.
        Callers hold the lock."""
        state = self._control_state[control["id"]]
        finding_count = sum(
            1
            for finding in self._findings.values()
            if control["id"] in finding["control_ids"]
        )
        return {
            "id": control["id"],
            "family": control["family"],
            "title": control["title"],
            "status": state["status"],
            "evidence": state["evidence"],
            "assessed_by": state["assessed_by"],
            "assessed_utc": state["assessed_utc"],
            "finding_count": finding_count,
        }

    def list_controls(self, actor):
        """Return one dict per catalog control, in catalog order."""
        _maybe_require(actor, "read")
        with self._lock:
            return [self._control_entry(control) for control in CONTROL_CATALOG]

    def assess_control(self, control_id, status, actor, evidence=""):
        """Record an assessment for one control."""
        _maybe_require(actor, "assess_controls")
        with self._lock:
            control = control_by_id(control_id)
            if control is None:
                raise NotFoundError("control not found: %r" % (control_id,))
            if status not in ASSESSMENT_STATUSES or status == "not_assessed":
                raise ValidationError(
                    "status must be one of %s"
                    % (
                        ", ".join(
                            s for s in ASSESSMENT_STATUSES if s != "not_assessed"
                        ),
                    )
                )
            if not isinstance(evidence, str):
                raise ValidationError("evidence must be a string")
            state = self._control_state[control_id]
            state["status"] = status
            state["evidence"] = evidence
            state["assessed_by"] = actor_name(actor)
            state["assessed_utc"] = _utc_now()
            self._audit(
                actor, "control_assess", control_id, details={"status": status}
            )
            return self._control_entry(control)

    # -- search and posture --------------------------------------------------

    def search(self, actor, q):
        """Cross-object case-insensitive substring search: findings
        over title/description/source, assets over name/owner, risks
        over title/description."""
        if not isinstance(q, str):
            raise ValidationError("q must be a string")
        _maybe_require(actor, "read")
        needle = q.lower()
        with self._lock:
            findings = [
                f
                for f in self._findings.values()
                if needle in f["title"].lower()
                or needle in f["description"].lower()
                or needle in f["source"].lower()
            ]
            findings.sort(key=_finding_sort_key)
            assets = [
                a
                for a in self._assets.values()
                if needle in a["name"].lower() or needle in a["owner"].lower()
            ]
            risks = [
                r
                for r in self._risks.values()
                if needle in r["title"].lower()
                or needle in r["description"].lower()
            ]
            risks.sort(key=_risk_sort_key)
            result = {
                "findings": [self._copy_finding(f) for f in findings],
                "assets": [self._copy_asset(a) for a in assets],
                "risks": [self._copy_risk(r) for r in risks],
            }
            self._audit(actor, "search", q, details={"q": q})
            return result

    def posture_summary(self, actor):
        """Return the posture summary. Does not audit."""
        _maybe_require(actor, "read")
        with self._lock:
            by_criticality = {name: 0 for name in CRITICALITIES}
            for asset in self._assets.values():
                by_criticality[asset["criticality"]] += 1

            by_severity = {name: 0 for name in SEVERITIES}
            by_status = {name: 0 for name in FINDING_STATUSES}
            open_findings = []
            for finding in self._findings.values():
                by_severity[finding["severity"]] += 1
                by_status[finding["status"]] += 1
                if finding["status"] not in ("closed", "false_positive"):
                    open_findings.append(finding)
            open_findings.sort(key=_finding_sort_key)
            top_open = [self._copy_finding(f) for f in open_findings[:5]]

            risks_by_status = {name: 0 for name in RISK_STATUSES}
            risks_by_band = {name: 0 for name in _BANDS}
            for risk in self._risks.values():
                risks_by_status[risk["status"]] += 1
                risks_by_band[risk["band"]] += 1

            total_controls = len(CONTROL_CATALOG)
            assessed = sum(
                1
                for state in self._control_state.values()
                if state["status"] != "not_assessed"
            )
            implemented = sum(
                1
                for state in self._control_state.values()
                if state["status"] == "implemented"
            )
            coverage_pct = round(100 * implemented / total_controls, 1)

            return {
                "assets": {
                    "total": len(self._assets),
                    "by_criticality": by_criticality,
                },
                "findings": {
                    "total": len(self._findings),
                    "by_severity": by_severity,
                    "by_status": by_status,
                    "open": len(open_findings),
                    "top_open": top_open,
                },
                "risks": {
                    "total": len(self._risks),
                    "by_status": risks_by_status,
                    "by_band": risks_by_band,
                },
                "controls": {
                    "total": total_controls,
                    "assessed": assessed,
                    "implemented": implemented,
                    "coverage_pct": coverage_pct,
                },
            }
