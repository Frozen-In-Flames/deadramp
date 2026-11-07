"""Final GAPS batch extensions, second unit, for Law Enforcement
L3-adjacent -- the TRAPWIRE remainder addition's own verticals.

Clean-room, standard-library-only records extensions for the 6
open Extended entries registered for the remainder addition fork
(TRAPWIRE Threat Detection and Analysis System) in
``ADDENDUM.md`` section 5 and in the GAPS.md section "Remainder
Addition -- Law Enforcement L3-adjacent (+1 fork)": threat
detection & real-time alerting; incident reporting & structured
suspicious-activity reporting; pattern analysis & analyst
support; originator-controlled cross-organizational information
sharing; mass warning & notification; integration API &
system-of-systems data integration. Per-entry dispositions and
any re-judgment are in ``BATCH-ADDITION.md`` in the group
directory: 4 entries built as records in-substrate, 2 shipped as
labeled reference implementations (threat detection & real-time
alerting; the integration API), exactly as drafted in the batch
inventory.

Design, following the core's doctrines, the first batch unit's
forms (``lawenf/extensions.py``, untouched by this module), and
this group's High baseline:

- This module is a second wrapper around
  :class:`LawEnfStore`, parallel to the first unit's; every
  pre-existing module -- the founding core and the first unit's
  extension module alike -- is untouched (byte-identical).
  Matter existence, membership, and lifecycle state are always
  read through the core store's public API, never
  re-implemented.
- **The hard privacy rule binds the whole surface.** Every
  record is keyed by an opaque caller-supplied ``*_ref`` string
  or a core / extension record id, and holds metadata and
  SHA-256 digests only. An incident report's *content* never
  enters here: the record is the filing's registry metadata
  (an opaque report reference, the channel it arrived on, and
  optionally the filed report's SHA-256 as computed by the
  filer's own system). There is no parameter anywhere in this
  module that could accept a report's text, a pattern's
  description, a warning's message, a person's name, or any
  identifier of a person -- the batch tests pin that by
  signature (``TypeError``). Nothing here holds a case subject,
  case substance, or criminal-history data of any kind, and no
  key anywhere on the surface is score-shaped: nothing is
  scored, rated, ranked, or predicted.
- **Records of the network's work, never the network.** The
  fork's described inputs are human-filed incident reports, and
  its described functions operate over report content and live
  reporting flows, which this substrate never holds. Detection
  and alerting are engines over those flows: they close as
  labeled reference implementations (request records plus
  outcome labels recorded verbatim as reported by whatever
  external capability the embedding organization operates;
  ``reference_stub: True``, ``detected_here: False``,
  ``alerted_here: False``). The integration API is a runtime
  surface over external systems: it too closes as a labeled
  reference implementation (connector definitions and exchange
  outcome records; nothing connects and no data moves). The
  remaining four entries close as records: incident-report
  filings, pattern-analysis records whose findings are reported
  labels (no pattern is computed here), originator sharing
  authorizations and their recorded authorization events (the
  originator's control is recorded as their instruction, never
  enforced here -- there is no content here to control), and
  mass-warning records with verbatim delivery reports (nothing
  is sent; ``reference_transport: True``).
- **High apparatus binds the new surface.** Extension
  mutations are audited on the core store's hash-chained audit
  log **audit-before-commit** (AU-5), under ``ext2_`` action
  names (the first unit's are ``ext_``): the audit entry is
  written before the record is committed, so a failed audit
  write (:class:`~lawenf.errors.AuditWriteError`) leaves no
  record and consumes no id -- fail-closed, exactly as the
  core's ``_atomic`` guard and the first unit's surface. The
  auditor role (``audit_read`` only) holds no core action any
  operation here maps to, so it is denied every operation,
  read and write; denials are audited ``ext2_<action>:denied``.
- RBAC goes through :mod:`lawenf.access` exactly as the core
  enforces it: each operation maps onto an existing core action
  (the core action set is fixed -- see the mapping in
  ``BATCH-ADDITION.md``), checked *before* any state change or
  id allocation for actors that carry a role. Matter
  membership -- the core's second boundary -- is enforced
  through the core store on every operation, and writes
  additionally require an open matter, mirroring the core's
  ``need_open`` discipline.
- Derived values are derived at read and never stored: view
  counts, latest reported outcomes, an incident report's
  analysis count, and a share authorization's current state.
  Stored records carry no derived key; tests pin that. The
  current-authorization derivation lives at a single named
  seam (``_current_authorization_label``): this unit's fresh
  negative control.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

#: The fork's own three reporting channels (ADDENDUM.md section 5,
#: entry "Incident reporting & structured suspicious-activity
#: reporting": the web suite, the Mobile App's field reporting,
#: the Community Member App's structured community reporting).
REPORT_CHANNELS = ("web", "mobile_field", "community")

#: What an originator share authorization may target on this
#: surface: this unit's own report-side records. (The first
#: unit's evidence-side share surface is a different vertical
#: with a different object and control model -- the
#: non-conflation precedent recorded in the addendum.)
SHARE_TARGET_KINDS = ("incident_report", "pattern_analysis")

#: The authorization state in force before any authorization
#: event is recorded: the authorization stands as recorded.
INITIAL_AUTHORIZATION_LABEL = "authorized_as_recorded"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None:
        _non_empty(value, what)
    return value


def _sha256_or_none(value, what):
    if value is not None:
        if not isinstance(value, str) or not _SHA256_RE.match(value):
            raise ValidationError(
                "%s must be exactly 64 lowercase hex characters" % (what,)
            )
    return value


class LawEnfExtensionsAddition:
    """Second GAPS-batch extension surface over a core LawEnfStore."""

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

        Mirrors the core store and the first unit's surface: an
        actor must be present; actors carrying a role are checked
        against the core permission matrix before anything
        changes; plain strings carry identity only. The auditor
        role holds none of the write actions, so it is denied
        here on every write.
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
        """Enforce a read permission when the actor carries a role.

        The auditor role holds neither ``matter_read`` nor
        ``report_read``, so it is denied here on every read and
        view as well.
        """
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, core_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", target)
                raise

    def _matter(self, actor, matter_id, audit_action, need_open=False):
        """Resolve a matter through the core store (existence and
        membership enforced there); a membership denial is audited
        under the extension action name. Writes pass
        ``need_open=True`` and require an open matter, mirroring
        the core's child-record discipline."""
        try:
            matter = self.store.get_matter(matter_id, actor)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", matter_id)
            raise
        if need_open and matter["status"] != "open":
            raise ValidationError(
                "matter %s is closed; no new records may be added" % (matter_id,)
            )
        return matter

    def _create(self, kind, prefix, fields, actor, audit_action):
        """Commit a record, auditing BEFORE the commit (AU-5).

        The audit entry is written to the core hash-chained log
        first; only when it is durably recorded is the record
        inserted and the id counter advanced. If the audit write
        fails, :class:`AuditWriteError` propagates with nothing
        inserted and no id consumed -- the extension surface is
        fail-closed exactly as the core store is.
        """
        with self._lock:
            record_id = "%s-%d" % (prefix, self._counters.get(prefix, 0) + 1)
            record = {"id": record_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._audit(actor, audit_action, record_id,
                        details={"kind": kind})
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            return copy.deepcopy(record)

    def _get(self, kind, record_id, matter_id=None):
        record = self._records.get((kind, record_id))
        if record is None or (matter_id is not None
                              and record["matter_id"] != matter_id):
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id, matter_id=None):
        return copy.deepcopy(self._get(kind, record_id, matter_id))

    def _list(self, kind, **filters):
        result = []
        for key in self._order:
            if key[0] != kind:
                continue
            record = self._records[key]
            if all(record.get(name) == value for name, value in filters.items()
                   if value is not None):
                result.append(copy.deepcopy(record))
        return result

    def _check_ref_unique(self, kind, matter_id, field, value, what):
        for record in self._list(kind, matter_id=matter_id):
            if record[field] == value:
                raise ValidationError(
                    "%s %r already exists in matter %s"
                    % (what, value, matter_id))

    # -- Threat detection & real-time alerting -------------------------
    # Shipped as a LABELED REFERENCE IMPLEMENTATION, exactly as
    # drafted (stub-engine): detection and alerting are an engine
    # over live reporting flows -- matching human incident
    # reports against each other across time and geography as
    # they arrive -- and an engine is not records. What the
    # substrate can honestly hold is the request registry the
    # capability's use presupposes: detection request records
    # (an opaque request reference and an optional verbatim scope
    # label naming, in the requester's own words, the report set
    # or watch the request concerns -- never report content) and
    # detection outcome records (the outcome label recorded
    # verbatim as reported by whatever external capability the
    # embedding organization operates). Every record carries
    # ``reference_stub: True``, ``detected_here: False``, and
    # ``alerted_here: False``. Nothing here detects anything,
    # matches anything, or raises any alert; the addendum's
    # discipline note stands -- the described input is a human
    # incident-reporting network, not feeds or sensors, and no
    # feed or sensor is ingested here either.

    def record_detection_request(self, matter_id, request_ref, actor,
                                 scope_label=None):
        """Record a detection request (reference). Action: search_write."""
        self._guard(actor, "search_write", "ext2_detection_request_record",
                    matter_id)
        _non_empty(request_ref, "request_ref")
        _string_or_none(scope_label, "scope_label")
        with self._lock:
            self._matter(actor, matter_id, "ext2_detection_request_record",
                         need_open=True)
            self._check_ref_unique("detection_request", matter_id,
                                   "request_ref", request_ref, "request_ref")
            return self._create(
                "detection_request", "det",
                {"matter_id": matter_id, "request_ref": request_ref,
                 "scope_label": scope_label, "reference_stub": True,
                 "detected_here": False, "alerted_here": False,
                 "status": "recorded_reference_only"},
                actor, "ext2_detection_request_record")

    def get_detection_request(self, matter_id, request_id, actor=None):
        """Return one detection request record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext2_detection_request_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_detection_request_read")
            return self._fetch("detection_request", request_id, matter_id)

    def list_detection_requests(self, matter_id, actor=None):
        """Return detection request records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext2_detection_request_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_detection_request_read")
            return self._list("detection_request", matter_id=matter_id)

    def record_detection_outcome(self, matter_id, request_id, outcome_label,
                                 actor):
        """Record a detection outcome label as reported, verbatim.

        Action: search_write. The label is the external
        capability's report; nothing was detected or alerted
        here.
        """
        self._guard(actor, "search_write", "ext2_detection_outcome_record",
                    matter_id)
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._matter(actor, matter_id, "ext2_detection_outcome_record",
                         need_open=True)
            self._get("detection_request", request_id, matter_id)
            return self._create(
                "detection_outcome", "dto",
                {"matter_id": matter_id, "request_id": request_id,
                 "outcome_label": outcome_label, "reference_stub": True,
                 "detected_here": False, "alerted_here": False},
                actor, "ext2_detection_outcome_record")

    def list_detection_outcomes(self, matter_id, request_id=None,
                                actor=None):
        """Return detection outcome records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext2_detection_outcome_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_detection_outcome_read")
            if request_id is not None:
                self._get("detection_request", request_id, matter_id)
            return self._list("detection_outcome", matter_id=matter_id,
                              request_id=request_id)

    def detection_request_view(self, matter_id, request_id, actor=None):
        """Derived view of a detection request. Action: report_read.

        The outcome count and latest reported outcome label are
        computed at read; the stored request carries neither.
        """
        self._guard_read(actor, "report_read", "ext2_detection_request_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_detection_request_view")
            request = self._get("detection_request", request_id, matter_id)
            outcomes = self._list("detection_outcome", matter_id=matter_id,
                                  request_id=request_id)
            view = dict(request)
            view["outcome_count"] = len(outcomes)
            view["latest_outcome"] = (
                outcomes[-1]["outcome_label"] if outcomes else None)
            view["derived_at_read"] = True
            return view

    # -- Incident reporting & structured suspicious-activity reporting -
    # Built as records. A filed incident report is registered
    # the way this substrate registers everything: an opaque
    # report reference, the channel the fork's own description
    # names (web suite, mobile field app, community member app),
    # and optionally the filed report's SHA-256 digest as
    # computed by the filer's own system -- metadata and a
    # checksum, never the report. There is no parameter that
    # could accept what the report says, who filed it, or whom
    # it concerns: a report here proves *that* a report was
    # filed, on which channel, and (when a digest is supplied)
    # which filing it was -- never what it reported. The intake
    # channels themselves (the web suite, the apps) are the
    # fork's products; this surface is their registry record.

    def file_incident_report(self, matter_id, report_ref, channel, actor,
                             report_sha256=None):
        """Register a filed incident report. Action: search_write.

        ``channel`` is one of the fork's three described
        channels: ``web``, ``mobile_field``, ``community``.
        ``report_sha256``, when given, is the filed report's
        digest as computed by the filer's system (64 lowercase
        hex); the report itself is never held here.
        """
        self._guard(actor, "search_write", "ext2_incident_report_file",
                    matter_id)
        _non_empty(report_ref, "report_ref")
        if channel not in REPORT_CHANNELS:
            raise ValidationError(
                "channel must be one of %s"
                % (", ".join(REPORT_CHANNELS),)
            )
        _sha256_or_none(report_sha256, "report_sha256")
        with self._lock:
            self._matter(actor, matter_id, "ext2_incident_report_file",
                         need_open=True)
            self._check_ref_unique("incident_report", matter_id,
                                   "report_ref", report_ref, "report_ref")
            return self._create(
                "incident_report", "inc",
                {"matter_id": matter_id, "report_ref": report_ref,
                 "channel": channel, "report_sha256": report_sha256,
                 "content_held": False, "status": "filed"},
                actor, "ext2_incident_report_file")

    def get_incident_report(self, matter_id, report_id, actor=None):
        """Return one incident report record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext2_incident_report_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_incident_report_read")
            return self._fetch("incident_report", report_id, matter_id)

    def list_incident_reports(self, matter_id, channel=None, actor=None):
        """Return incident report records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext2_incident_report_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_incident_report_read")
            return self._list("incident_report", matter_id=matter_id,
                              channel=channel)

    def incident_report_view(self, matter_id, report_id, actor=None):
        """Derived view of an incident report. Action: report_read.

        The count of pattern analyses bound to this report is
        computed at read from the analysis records; the stored
        report carries no count.
        """
        self._guard_read(actor, "report_read", "ext2_incident_report_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_incident_report_view")
            report = self._get("incident_report", report_id, matter_id)
            analyses = self._list("pattern_analysis", matter_id=matter_id,
                                  incident_report_id=report_id)
            view = dict(report)
            view["analysis_count"] = len(analyses)
            view["derived_at_read"] = True
            return view

    # -- Pattern analysis & analyst support -----------------------------
    # Built as records, under the Group 21 precedent and this
    # substrate's standing rule: ratings and findings are
    # records; scoring and computing are engines. An analysis
    # record names the analysis (an opaque reference, an
    # optional verbatim scope label naming the report set in the
    # analyst's own words, an optional binding to one registered
    # incident report) and finding records hold an opaque result
    # reference plus an optional verbatim reported label. No
    # pattern is computed here, no report content is read here
    # (none is held), and no finding's text can enter: there is
    # no parameter that could accept one. The analyst support
    # tooling itself is the fork's product; this surface is its
    # record.

    def record_pattern_analysis(self, matter_id, analysis_ref, actor,
                                incident_report_id=None, scope_label=None):
        """Record a pattern analysis. Action: search_write.

        ``incident_report_id``, when given, binds the analysis
        to one incident report registered in this matter.
        ``scope_label`` names the wider report set in the
        analyst's own words, recorded verbatim.
        """
        self._guard(actor, "search_write", "ext2_pattern_analysis_record",
                    matter_id)
        _non_empty(analysis_ref, "analysis_ref")
        _string_or_none(scope_label, "scope_label")
        with self._lock:
            self._matter(actor, matter_id, "ext2_pattern_analysis_record",
                         need_open=True)
            if incident_report_id is not None:
                self._get("incident_report", incident_report_id, matter_id)
            self._check_ref_unique("pattern_analysis", matter_id,
                                   "analysis_ref", analysis_ref,
                                   "analysis_ref")
            return self._create(
                "pattern_analysis", "ana",
                {"matter_id": matter_id, "analysis_ref": analysis_ref,
                 "incident_report_id": incident_report_id,
                 "scope_label": scope_label, "analyzed_here": False,
                 "patterns_computed_here": False, "content_held": False,
                 "status": "recorded"},
                actor, "ext2_pattern_analysis_record")

    def get_pattern_analysis(self, matter_id, analysis_id, actor=None):
        """Return one pattern analysis record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext2_pattern_analysis_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_pattern_analysis_read")
            return self._fetch("pattern_analysis", analysis_id, matter_id)

    def list_pattern_analyses(self, matter_id, incident_report_id=None,
                              actor=None):
        """Return pattern analysis records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext2_pattern_analysis_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_pattern_analysis_read")
            if incident_report_id is not None:
                self._get("incident_report", incident_report_id, matter_id)
            return self._list("pattern_analysis", matter_id=matter_id,
                              incident_report_id=incident_report_id)

    def record_analysis_finding(self, matter_id, analysis_id, result_ref,
                                actor, label=None):
        """Record an analysis finding as reported. Action: search_write.

        The finding is an opaque result reference plus an
        optional label recorded verbatim as reported by the
        analyst's tooling. No finding is computed here and no
        finding's text can be supplied.
        """
        self._guard(actor, "search_write", "ext2_analysis_finding_record",
                    matter_id)
        _non_empty(result_ref, "result_ref")
        _string_or_none(label, "label")
        with self._lock:
            self._matter(actor, matter_id, "ext2_analysis_finding_record",
                         need_open=True)
            self._get("pattern_analysis", analysis_id, matter_id)
            return self._create(
                "analysis_finding", "anf",
                {"matter_id": matter_id, "analysis_id": analysis_id,
                 "result_ref": result_ref, "label": label,
                 "analyzed_here": False, "computed_here": False,
                 "content_held": False},
                actor, "ext2_analysis_finding_record")

    def list_analysis_findings(self, matter_id, analysis_id=None,
                               actor=None):
        """Return analysis finding records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext2_analysis_finding_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_analysis_finding_read")
            if analysis_id is not None:
                self._get("pattern_analysis", analysis_id, matter_id)
            return self._list("analysis_finding", matter_id=matter_id,
                              analysis_id=analysis_id)

    def pattern_analysis_view(self, matter_id, analysis_id, actor=None):
        """Derived view of a pattern analysis. Action: report_read.

        The finding count and the latest reported finding label
        are computed at read; the stored analysis carries
        neither.
        """
        self._guard_read(actor, "report_read", "ext2_pattern_analysis_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_pattern_analysis_view")
            analysis = self._get("pattern_analysis", analysis_id, matter_id)
            findings = self._list("analysis_finding", matter_id=matter_id,
                                  analysis_id=analysis_id)
            view = dict(analysis)
            view["finding_count"] = len(findings)
            view["latest_finding_label"] = (
                findings[-1]["label"] if findings else None)
            view["derived_at_read"] = True
            return view

    # -- Originator-controlled cross-organizational information sharing -
    # Built as records, and kept distinct from the first unit's
    # information-sharing-over-evidence vertical on the
    # non-conflation precedent: that surface shares forensic
    # objects under a custody model; this one records an
    # originator's authorization to share report-side records
    # (an incident report or a pattern analysis registered on
    # this surface) with another organization, under the
    # originator's continuing control. An authorization record
    # binds a target on this surface to an opaque recipient
    # organization reference and an opaque originator reference
    # -- organizations are named by reference only, never by a
    # person's identifier. Authorization event records hold the
    # originator's subsequent instructions (grant, narrowing,
    # revocation, in the originator's own labels) verbatim as
    # reported. The control itself is NOT enforced here:
    # ``control_enforced_here: False`` on every record -- there
    # is no content in this substrate for control to operate
    # over, and whether a sharing system elsewhere honors the
    # originator's instruction is that system's property. The
    # authorization's current state derives at read from the
    # recorded events, through the seam
    # ``_current_authorization_label`` (this unit's fresh
    # negative control). Every record carries
    # ``reference_transport: True`` and ``transmitted_here:
    # False``: this build transmits nothing; the records
    # describe authorizations and shares effected on systems
    # owned elsewhere.

    @staticmethod
    def _current_authorization_label(events):
        """The authorization state in force, derived at read.

        The label on the LATEST recorded authorization event,
        or the recorded initial state when no event has been
        recorded. The stored authorization record carries no
        current state; this seam is the only place it is
        computed.
        """
        if events:
            return events[-1]["event_label"]
        return INITIAL_AUTHORIZATION_LABEL

    def record_share_authorization(self, matter_id, share_ref, target_kind,
                                   target_id, recipient_org_ref,
                                   originator_ref, actor, scope_label=None):
        """Record an originator share authorization.

        Action: annotation_write. ``target_kind`` is
        ``incident_report`` or ``pattern_analysis`` (a record on
        this surface, in this matter); ``recipient_org_ref`` and
        ``originator_ref`` are opaque references to
        organizations -- never a name or an identifier of a
        person.
        """
        self._guard(actor, "annotation_write",
                    "ext2_share_authorization_record", matter_id)
        _non_empty(share_ref, "share_ref")
        _non_empty(recipient_org_ref, "recipient_org_ref")
        _non_empty(originator_ref, "originator_ref")
        _string_or_none(scope_label, "scope_label")
        if target_kind not in SHARE_TARGET_KINDS:
            raise ValidationError(
                "target_kind must be one of %s"
                % (", ".join(SHARE_TARGET_KINDS),)
            )
        with self._lock:
            self._matter(actor, matter_id,
                         "ext2_share_authorization_record", need_open=True)
            self._get(target_kind, target_id, matter_id)
            self._check_ref_unique("share_authorization", matter_id,
                                   "share_ref", share_ref, "share_ref")
            return self._create(
                "share_authorization", "osh",
                {"matter_id": matter_id, "share_ref": share_ref,
                 "target_kind": target_kind, "target_id": target_id,
                 "recipient_org_ref": recipient_org_ref,
                 "originator_ref": originator_ref,
                 "scope_label": scope_label, "reference_transport": True,
                 "transmitted_here": False, "shared_here": False,
                 "content_held": False, "control_enforced_here": False,
                 "status": "recorded"},
                actor, "ext2_share_authorization_record")

    def get_share_authorization(self, matter_id, share_id, actor=None):
        """Return one share authorization record. Action: matter_read."""
        self._guard_read(actor, "matter_read",
                         "ext2_share_authorization_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_share_authorization_read")
            return self._fetch("share_authorization", share_id, matter_id)

    def list_share_authorizations(self, matter_id, target_id=None,
                                  actor=None):
        """Return share authorization records. Action: matter_read."""
        self._guard_read(actor, "matter_read",
                         "ext2_share_authorization_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_share_authorization_read")
            return self._list("share_authorization", matter_id=matter_id,
                              target_id=target_id)

    def record_authorization_event(self, matter_id, share_id, event_label,
                                   actor):
        """Record an originator authorization event, verbatim.

        Action: annotation_write. The label is the originator's
        instruction as reported (a grant, a narrowing, a
        revocation, in their own words); the current state is
        derived from these events at read, never stored.
        """
        self._guard(actor, "annotation_write",
                    "ext2_authorization_event_record", matter_id)
        _non_empty(event_label, "event_label")
        with self._lock:
            self._matter(actor, matter_id,
                         "ext2_authorization_event_record", need_open=True)
            self._get("share_authorization", share_id, matter_id)
            return self._create(
                "share_authorization_event", "ose",
                {"matter_id": matter_id, "share_id": share_id,
                 "event_label": event_label, "reference_transport": True,
                 "transmitted_here": False,
                 "control_enforced_here": False},
                actor, "ext2_authorization_event_record")

    def list_authorization_events(self, matter_id, share_id=None,
                                  actor=None):
        """Return authorization event records. Action: matter_read."""
        self._guard_read(actor, "matter_read",
                         "ext2_authorization_event_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_authorization_event_read")
            if share_id is not None:
                self._get("share_authorization", share_id, matter_id)
            return self._list("share_authorization_event",
                              matter_id=matter_id, share_id=share_id)

    def share_authorization_view(self, matter_id, share_id, actor=None):
        """Derived view of a share authorization. Action: report_read.

        The authorization event count and the current
        authorization label are computed at read from the
        recorded events, through the seam
        ``_current_authorization_label``; the stored
        authorization carries neither.
        """
        self._guard_read(actor, "report_read",
                         "ext2_share_authorization_view", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_share_authorization_view")
            share = self._get("share_authorization", share_id, matter_id)
            events = self._list("share_authorization_event",
                                matter_id=matter_id, share_id=share_id)
            view = dict(share)
            view["authorization_event_count"] = len(events)
            view["current_authorization_label"] = (
                self._current_authorization_label(events))
            view["derived_at_read"] = True
            return view

    # -- Mass warning & notification ------------------------------------
    # Built as records, in the Communication adjudicated form:
    # a warning record names the warning by an opaque reference
    # and its audience by a verbatim label (a population label
    # recorded as reported -- never a list of persons, and there
    # is no parameter that could accept a recipient's identifier
    # or the warning's message), and delivery report records
    # hold distribution outcomes verbatim as reported by the
    # distribution system the embedding organization operates.
    # Every record carries ``reference_transport: True`` and
    # ``sent_here: False`` (the warning also ``distributed_here:
    # False``): this build warns no one and sends nothing; the
    # records describe warnings effected on systems owned
    # elsewhere. The distribution engine is the fork's product;
    # this surface is its record.

    def record_mass_warning(self, matter_id, warning_ref, audience_label,
                            actor):
        """Record a mass warning. Action: annotation_write.

        ``audience_label`` is the recipient population's label
        recorded verbatim as reported -- a label, never a list
        of persons or their identifiers.
        """
        self._guard(actor, "annotation_write", "ext2_mass_warning_record",
                    matter_id)
        _non_empty(warning_ref, "warning_ref")
        _non_empty(audience_label, "audience_label")
        with self._lock:
            self._matter(actor, matter_id, "ext2_mass_warning_record",
                         need_open=True)
            self._check_ref_unique("mass_warning", matter_id, "warning_ref",
                                   warning_ref, "warning_ref")
            return self._create(
                "mass_warning", "wrn",
                {"matter_id": matter_id, "warning_ref": warning_ref,
                 "audience_label": audience_label,
                 "reference_transport": True, "sent_here": False,
                 "distributed_here": False, "content_held": False,
                 "status": "recorded"},
                actor, "ext2_mass_warning_record")

    def get_mass_warning(self, matter_id, warning_id, actor=None):
        """Return one mass warning record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext2_mass_warning_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_mass_warning_read")
            return self._fetch("mass_warning", warning_id, matter_id)

    def list_mass_warnings(self, matter_id, actor=None):
        """Return mass warning records. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext2_mass_warning_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_mass_warning_read")
            return self._list("mass_warning", matter_id=matter_id)

    def record_warning_delivery(self, matter_id, warning_id, outcome_label,
                                actor):
        """Record a warning delivery outcome as reported, verbatim.

        Action: annotation_write. The label is the distribution
        system's report; nothing was sent here.
        """
        self._guard(actor, "annotation_write",
                    "ext2_warning_delivery_record", matter_id)
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._matter(actor, matter_id, "ext2_warning_delivery_record",
                         need_open=True)
            self._get("mass_warning", warning_id, matter_id)
            return self._create(
                "warning_delivery_report", "wnr",
                {"matter_id": matter_id, "warning_id": warning_id,
                 "outcome_label": outcome_label,
                 "reference_transport": True, "sent_here": False},
                actor, "ext2_warning_delivery_record")

    def list_warning_deliveries(self, matter_id, warning_id=None,
                                actor=None):
        """Return warning delivery report records. Action: matter_read."""
        self._guard_read(actor, "matter_read",
                         "ext2_warning_delivery_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_warning_delivery_read")
            if warning_id is not None:
                self._get("mass_warning", warning_id, matter_id)
            return self._list("warning_delivery_report",
                              matter_id=matter_id, warning_id=warning_id)

    def mass_warning_view(self, matter_id, warning_id, actor=None):
        """Derived view of a mass warning. Action: report_read.

        The delivery report count and the latest reported
        outcome are computed at read; the stored warning
        carries neither.
        """
        self._guard_read(actor, "report_read", "ext2_mass_warning_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext2_mass_warning_view")
            warning = self._get("mass_warning", warning_id, matter_id)
            reports = self._list("warning_delivery_report",
                                 matter_id=matter_id, warning_id=warning_id)
            view = dict(warning)
            view["delivery_report_count"] = len(reports)
            view["latest_outcome"] = (
                reports[-1]["outcome_label"] if reports else None)
            view["derived_at_read"] = True
            return view

    # -- Integration API & system-of-systems data integration -----------
    # Shipped as a LABELED REFERENCE IMPLEMENTATION, exactly as
    # drafted (stub-engine): an integration API is a runtime
    # surface over external systems -- it connects, translates,
    # and moves data between a deployment and legacy or other
    # enterprise systems -- and a runtime is not records. What
    # the substrate can honestly hold is the connector registry
    # the runtime's use presupposes: connector definition
    # records (an opaque connector reference, an opaque
    # reference to the external system, an optional verbatim
    # direction label) and exchange records (outcome labels
    # recorded verbatim as reported by whatever integration
    # runtime the embedding organization operates). Every
    # record carries ``reference_stub: True`` and
    # ``reference_transport: True``, with ``connected_here:
    # False`` and ``data_moved_here: False``; there is no
    # parameter that could accept a payload, an endpoint
    # address, or a credential -- nothing connects here and no
    # data moves here. The substrate's own records API (the
    # core service layer) is unchanged and is not this entry:
    # source-system integration is the fork's product.

    def record_integration_connector(self, matter_id, connector_ref,
                                     system_ref, actor, direction_label=None):
        """Record an integration connector (reference).

        Action: source_write. ``system_ref`` is an opaque
        reference to the external system -- never an address,
        an endpoint, or a credential.
        """
        self._guard(actor, "source_write",
                    "ext2_integration_connector_record", matter_id)
        _non_empty(connector_ref, "connector_ref")
        _non_empty(system_ref, "system_ref")
        _string_or_none(direction_label, "direction_label")
        with self._lock:
            self._matter(actor, matter_id,
                         "ext2_integration_connector_record",
                         need_open=True)
            self._check_ref_unique("integration_connector", matter_id,
                                   "connector_ref", connector_ref,
                                   "connector_ref")
            return self._create(
                "integration_connector", "int",
                {"matter_id": matter_id, "connector_ref": connector_ref,
                 "system_ref": system_ref,
                 "direction_label": direction_label,
                 "reference_stub": True, "reference_transport": True,
                 "connected_here": False, "data_moved_here": False,
                 "status": "recorded_reference_only"},
                actor, "ext2_integration_connector_record")

    def get_integration_connector(self, matter_id, connector_id,
                                  actor=None):
        """Return one integration connector record. Action: matter_read."""
        self._guard_read(actor, "matter_read",
                         "ext2_integration_connector_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id,
                         "ext2_integration_connector_read")
            return self._fetch("integration_connector", connector_id,
                               matter_id)

    def list_integration_connectors(self, matter_id, actor=None):
        """Return integration connector records. Action: matter_read."""
        self._guard_read(actor, "matter_read",
                         "ext2_integration_connector_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id,
                         "ext2_integration_connector_read")
            return self._list("integration_connector", matter_id=matter_id)

    def record_integration_exchange(self, matter_id, connector_id,
                                    outcome_label, actor):
        """Record an integration exchange outcome as reported.

        Action: source_write. The label is the external
        runtime's report; nothing connected and no data moved
        here.
        """
        self._guard(actor, "source_write",
                    "ext2_integration_exchange_record", matter_id)
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._matter(actor, matter_id,
                         "ext2_integration_exchange_record",
                         need_open=True)
            self._get("integration_connector", connector_id, matter_id)
            return self._create(
                "integration_exchange", "ino",
                {"matter_id": matter_id, "connector_id": connector_id,
                 "outcome_label": outcome_label, "reference_stub": True,
                 "reference_transport": True, "connected_here": False,
                 "data_moved_here": False},
                actor, "ext2_integration_exchange_record")

    def list_integration_exchanges(self, matter_id, connector_id=None,
                                   actor=None):
        """Return integration exchange records. Action: matter_read."""
        self._guard_read(actor, "matter_read",
                         "ext2_integration_exchange_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id,
                         "ext2_integration_exchange_read")
            if connector_id is not None:
                self._get("integration_connector", connector_id, matter_id)
            return self._list("integration_exchange", matter_id=matter_id,
                              connector_id=connector_id)

    def integration_connector_view(self, matter_id, connector_id,
                                   actor=None):
        """Derived view of an integration connector. Action: report_read.

        The exchange count and latest reported outcome label
        are computed at read; the stored connector carries
        neither.
        """
        self._guard_read(actor, "report_read",
                         "ext2_integration_connector_view", matter_id)
        with self._lock:
            self._matter(actor, matter_id,
                         "ext2_integration_connector_view")
            connector = self._get("integration_connector", connector_id,
                                  matter_id)
            exchanges = self._list("integration_exchange",
                                   matter_id=matter_id,
                                   connector_id=connector_id)
            view = dict(connector)
            view["exchange_count"] = len(exchanges)
            view["latest_outcome"] = (
                exchanges[-1]["outcome_label"] if exchanges else None)
            view["derived_at_read"] = True
            return view
