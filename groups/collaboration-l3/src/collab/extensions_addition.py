"""Final GAPS batch extensions, second unit — Collaboration
L3-adjacent remainder addition.

Clean-room, standard-library-only extension for the 1 open entry of
the GAPS.md section "Remainder Addition — Collaboration L3-adjacent
(+1 fork)" (inventory idx 656; see ``BATCH-ADDITION.md`` in the group
directory for the disposition). This module is a second wrapper
around :class:`CollabStore`, independent of the first batch unit's
``collab/extensions.py``; every pre-existing module — the seven core
modules and the first unit's extensions — is untouched and
byte-identical to the shipped build.

The entry names a *service*: the agency–vendor collaborative
continuous-monitoring arrangement the addition fork's listing closes
with ("Federal agencies interested in collaborative continuous
monitoring with Microsoft should reach out to: …", ADDENDUM.md §2/§5).
A monitoring service runs against live systems and agency networks;
nothing in a records substrate monitors anything. Per the drafted
disposition (stub-engine) and the house precedent for engine entries,
the entry therefore ships as a **labeled reference implementation**:
arrangement records and monitoring-report records, every record
carrying ``reference_stub: True`` and ``monitored_here: False``.
Reports record the arrangement's own reported outcomes verbatim —
outcome labels and a findings count held exactly as reported — and
the views derive only counts and the latest reported outcome over
those records. This build's audit trail is the substrate such an
arrangement reports *from* (ADDENDUM.md §5), not the arrangement
itself, and nothing here watches, scans, or collects telemetry from
any system.

Access discipline is carried from the core and from the first batch
unit: every operation resolves its workspace through the core store,
so the membership boundary and the ``read`` permission bind reads
and writes alike. Writes map to the core ``post`` action; the
**auditor role holds no extension permission** — it is not a
workspace member and holds no ``read``, so it is denied on every
operation on this surface, matching this tree's High-baseline AC-5
posture, while its core audit duty (reading the trail through the
core service) is untouched. Denied write attempts are recorded on
the core audit log with a ``:denied`` suffix; successful mutations
land on the same append-only, hash-chained log under the ``exta_``
action prefix (distinct from the first unit's ``ext_``), recorded
before the record commits (AU-5), so an audit write failure changes
nothing and consumes no id. Validation precedes mutation
throughout. Nothing in this surface computes a score: a recursive
key scan over the records and views finds no
score/grade/rating/percent/rank key (pinned by test).
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

#: The core RBAC action extension writes map to.
_WRITE_ACTION = "post"

CADENCE_LABELS = ("continuous", "monthly", "quarterly", "annual")
REPORT_LABELS = (
    "reported_current", "reported_findings", "reported_clean",
    "reported_delayed",
)

_REFERENCE_STATE = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _count(value, what):
    """A non-negative integer count; booleans and floats rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be a non-negative integer" % (what,))
    if value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


def _label(value, known, what):
    names = ", ".join(repr(n) for n in known)
    _non_empty(value, what)
    if value not in known:
        raise ValidationError("%s must be one of %s" % (what, names))
    return value


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class CollabExtensionsAddition:
    """Second-unit extension surface wrapping one :class:`CollabStore`."""

    def __init__(self, store):
        self.store = store
        self._arrangements = {}
        self._reports = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    def _workspace(self, actor, workspace_id):
        """Resolve a workspace through the core store, which enforces
        the membership boundary and the ``read`` permission. The
        auditor role holds neither, so it is denied here on every
        operation on this surface."""
        return self.store.get_workspace(workspace_id, actor)

    def _guard(self, actor, audit_action):
        """Enforce the extension write permission before any state
        change. Writes map to the core ``post`` action. A denied
        attempt is recorded on the audit log with a ``:denied``
        suffix before the error propagates; a missing actor is
        denied outright. A plain string carries identity but no role
        (the service layer enforces its role), matching the core
        convention."""
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (_WRITE_ACTION,))
        if hasattr(actor, "role"):
            try:
                require(actor, _WRITE_ACTION)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": _WRITE_ACTION})
                raise

    def _create(self, table, prefix, fields, actor, audit_action):
        """Commit one record, audit-before-commit (AU-5): the audit
        entry is recorded first, so an audit write failure changes
        nothing and consumes no id."""
        record = {"id": "%s%d" % (prefix, self._counters.get(prefix, 0) + 1)}
        record.update(fields)
        record["created_by"] = actor_name(actor)
        record["created_utc"] = _utc_now()
        self._audit(actor, audit_action, record["id"])
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        table[record["id"]] = record
        return copy.deepcopy(record)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _scoped(self, table, record_id, workspace_id, what):
        """Fetch a record, treating a record from another workspace
        as not found."""
        record = self._get(table, record_id, what)
        if record["workspace_id"] != workspace_id:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    def _in_workspace(self, table, workspace_id):
        return [r for r in table.values() if r["workspace_id"] == workspace_id]

    # -- collaborative continuous monitoring (idx 656, reference) --------
    # Labeled reference implementation: arrangement records naming the
    # agency–vendor monitoring arrangement as opaque references, and
    # monitoring-report records holding the arrangement's reported
    # outcomes verbatim. Nothing is monitored here.

    def register_monitoring_arrangement(self, actor, workspace_id,
                                        arrangement_ref, agency_ref,
                                        vendor_ref, cadence_label):
        """Register a collaborative continuous-monitoring arrangement
        as a reference record. Action: post. Ids: mon-{n}. The
        agency and vendor are opaque references only; the
        arrangement itself — the monitoring service the fork's
        listing names — is operated by the parties, never here
        (``monitored_here`` False), and registering one changes no
        core record."""
        _non_empty(arrangement_ref, "arrangement_ref")
        _non_empty(agency_ref, "agency_ref")
        _non_empty(vendor_ref, "vendor_ref")
        _label(cadence_label, CADENCE_LABELS, "cadence_label")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "exta_monitoring_arrangement_register")
            return self._create(self._arrangements, "mon-", {
                "workspace_id": workspace_id,
                "arrangement_ref": arrangement_ref,
                "agency_ref": agency_ref,
                "vendor_ref": vendor_ref,
                "cadence_label": cadence_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "monitored_here": False,
            }, actor, "exta_monitoring_arrangement_register")

    def get_monitoring_arrangement(self, actor, workspace_id,
                                   arrangement_id):
        """One monitoring-arrangement reference record."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return copy.deepcopy(
                self._scoped(self._arrangements, arrangement_id,
                             workspace_id, "monitoring arrangement"))

    def list_monitoring_arrangements(self, actor, workspace_id):
        """All monitoring-arrangement reference records of a
        workspace."""
        with self._lock:
            self._workspace(actor, workspace_id)
            return [copy.deepcopy(r) for r in self._sorted(
                self._in_workspace(self._arrangements, workspace_id))]

    def record_monitoring_report(self, actor, workspace_id,
                                 arrangement_id, period_label,
                                 outcome_label, findings_reported=0):
        """Record one monitoring report of an arrangement. Action:
        post. Ids: monr-{n}. The outcome label and the findings
        count are the arrangement's own reported values, held
        verbatim as data; no finding is produced, verified, or
        scored here (``monitored_here`` False). There is no field
        that could hold report content — a report is named by its
        period label and its reported outcome only."""
        _non_empty(period_label, "period_label")
        _label(outcome_label, REPORT_LABELS, "outcome_label")
        _count(findings_reported, "findings_reported")
        with self._lock:
            self._workspace(actor, workspace_id)
            self._guard(actor, "exta_monitoring_report_record")
            self._scoped(self._arrangements, arrangement_id, workspace_id,
                         "monitoring arrangement")
            return self._create(self._reports, "monr-", {
                "workspace_id": workspace_id,
                "arrangement_id": arrangement_id,
                "period_label": period_label,
                "outcome_label": outcome_label,
                "findings_reported": findings_reported,
                "reference_stub": True,
                "monitored_here": False,
            }, actor, "exta_monitoring_report_record")

    def list_monitoring_reports(self, actor, workspace_id, arrangement_id):
        """All monitoring-report records of an arrangement, in
        record order."""
        with self._lock:
            self._workspace(actor, workspace_id)
            self._scoped(self._arrangements, arrangement_id, workspace_id,
                         "monitoring arrangement")
            return [copy.deepcopy(r) for r in self._sorted(
                r for r in self._reports.values()
                if r["arrangement_id"] == arrangement_id)]

    def _reports_for(self, arrangement_id):
        return self._sorted(
            r for r in self._reports.values()
            if r["arrangement_id"] == arrangement_id)

    @staticmethod
    def _latest_report_label(reports):
        """The current reported outcome of an arrangement: the
        latest recorded report's outcome label, or ``recorded``
        when no report has been recorded yet.

        MUTATION DRILL NOTE: this derivation is this unit's fresh
        negative control target — if it read the earliest label
        instead, an arrangement whose latest report superseded an
        earlier one would still read as the earlier outcome (see
        tests/README.md)."""
        if not reports:
            return "recorded"
        return reports[-1]["outcome_label"]

    def monitoring_view(self, actor, workspace_id, arrangement_id):
        """A monitoring-arrangement record plus derived reporting
        state: report count, counts by reported outcome label, the
        total of the recorded reports' findings counts (a sum of
        reported values, stated as such), and the current reported
        outcome — all computed at read from the recorded reports
        and stored nowhere. Counts and labels only."""
        with self._lock:
            self._workspace(actor, workspace_id)
            arrangement = copy.deepcopy(
                self._scoped(self._arrangements, arrangement_id,
                             workspace_id, "monitoring arrangement"))
            reports = self._reports_for(arrangement_id)
            by_outcome = {label: 0 for label in REPORT_LABELS}
            for report in reports:
                by_outcome[report["outcome_label"]] += 1
            arrangement["report_count"] = len(reports)
            arrangement["reports_by_outcome"] = by_outcome
            arrangement["findings_reported_total"] = sum(
                r["findings_reported"] for r in reports)
            arrangement["current_outcome"] = self._latest_report_label(
                reports)
            arrangement["derived"] = True
            return arrangement

    def monitoring_summary(self, actor, workspace_id):
        """Workspace-level derived counts over the arrangement and
        report records: arrangements, reports, reports by outcome
        label, and the sum of reported findings counts. Computed at
        read; counts and labels only."""
        with self._lock:
            self._workspace(actor, workspace_id)
            arrangements = self._in_workspace(self._arrangements,
                                              workspace_id)
            arrangement_ids = {r["id"] for r in arrangements}
            reports = [r for r in self._reports.values()
                       if r["arrangement_id"] in arrangement_ids]
            by_outcome = {label: 0 for label in REPORT_LABELS}
            for report in reports:
                by_outcome[report["outcome_label"]] += 1
            return {
                "workspace_id": workspace_id,
                "arrangement_count": len(arrangements),
                "report_count": len(reports),
                "reports_by_outcome": by_outcome,
                "findings_reported_total": sum(
                    r["findings_reported"] for r in reports),
                "derived": True,
            }
