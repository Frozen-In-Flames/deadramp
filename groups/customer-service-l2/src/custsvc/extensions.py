"""Final GAPS batch extensions for the Customer Service L2 merged
build (Group 27).

Clean-room, standard-library-only records/derivation extensions for
the 13 open Extended entries this group's GAPS.md section carries:
7 built as in-substrate records plus deterministic derivations over
the core's own records, and 6 shipped as labeled reference
implementations (the drafted stub-engine families). See ``BATCH.md``
in the group directory for the per-entry disposition.

Design, following the core's doctrines:

- This module is a wrapper around :class:`CustsvcStore`; the core
  modules are untouched (byte-identical). Core state (cases, rules,
  requesters, alerts) is always read through the core store's public
  API, never re-implemented, and no extension operation writes core
  state.
- RBAC goes through :mod:`custsvc.access` exactly as the core
  enforces it: the extension maps each of its operations onto an
  existing core action (the core action set is fixed), checks it
  *before* any state change or id allocation for User-like actors,
  and records denied attempts on the core audit log with the
  extension action name suffixed ``:denied``. Plain-string actors
  carry identity but no role, mirroring the core convention. The
  mapping is:

  - automation execution requests -> ``rule_write`` / ``rule_read``
    (operations against rule records ride the rules' own actions);
  - SLA policy records -> ``rule_write`` / ``rule_read`` (registry
    configuration, the same genus as rules);
  - GRC posture, survey tallies, analytics reports -> ``report_read``;
  - everything else operational -> the matching ``case_write`` /
    ``case_read`` (or ``alert_read`` where the record binds alerts).

- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``. If the
  audit write raises, the record insertion and its id are rolled
  back before the error propagates: no extension record exists
  whose audit entry does not.
- All references to people, systems, and domains are opaque
  ``*_ref`` strings, exactly as in the core. Where a record binds a
  person (survey respondent, relocation employee, signer) the ref
  must be a requester ref already registered in the core, so the
  pinned requester shape -- which cannot hold a phone number, email
  address, or real identifier -- governs those records too. No
  record shape in this module can hold an identifier value, a
  signature, message content in transit, or money in motion.
- Derived values are derived at read and never stored: SLA breach
  state under a recorded policy, GRC posture counts, survey
  tallies, notification rollups, analytics reports. Stored records
  carry no derived key; tests pin that.
- The founding doctrine is not repealed: the core automation rule
  registry never executes, and nothing in this module evaluates a
  rule's condition or performs its action. The automation entry
  lands as execution-*request* records plus outcome reports stored
  verbatim as reported by executors elsewhere.
- Nothing here executes against an external system. The
  stub-engine families ship as labeled reference implementations:
  every record they create carries ``reference_stub: True``
  (notification delivery receipts carry ``reference_transport:
  True``), and no site is hosted, no relocation is processed, no
  signature is made, nothing is detected, no channel connects, and
  no assistant infers.
"""

import copy
import threading
from datetime import datetime, timedelta, timezone
from fractions import Fraction

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import PRIORITIES, TERMINAL_STATUSES

COMMERCE_DOMAINS = ("grocery", "fuel", "loyalty", "food_ordering", "general_retail")
KNOWN_COMMERCE_DOMAINS = frozenset(COMMERCE_DOMAINS)
COMMERCE_REPORT_OUTCOMES = (
    "reported_operational",
    "reported_degraded",
    "reported_down",
)
KNOWN_COMMERCE_REPORT_OUTCOMES = frozenset(COMMERCE_REPORT_OUTCOMES)
RELOCATION_STEPS = (
    "obligation_recorded",
    "voucher_submitted",
    "voucher_processed",
    "supplier_billed",
    "financial_interface_reported",
    "certified",
)
KNOWN_RELOCATION_STEPS = frozenset(RELOCATION_STEPS)
SIGNATURE_OUTCOMES = ("reported_signed", "reported_declined", "reported_expired")
KNOWN_SIGNATURE_OUTCOMES = frozenset(SIGNATURE_OUTCOMES)
EXECUTION_REPORT_OUTCOMES = (
    "reported_completed",
    "reported_failed",
    "reported_noop",
)
KNOWN_EXECUTION_REPORT_OUTCOMES = frozenset(EXECUTION_REPORT_OUTCOMES)
ORCHESTRATION_OUTCOMES = (
    "reported_completed",
    "reported_failed",
    "reported_partial",
)
KNOWN_ORCHESTRATION_OUTCOMES = frozenset(ORCHESTRATION_OUTCOMES)
DELIVERY_OUTCOMES = ("reported_delivered", "reported_failed", "reported_bounced")
KNOWN_DELIVERY_OUTCOMES = frozenset(DELIVERY_OUTCOMES)
CHANNEL_KINDS = ("live_chat", "voice", "video")
KNOWN_CHANNEL_KINDS = frozenset(CHANNEL_KINDS)
DEFLECTION_OUTCOMES = (
    "reported_deflected",
    "reported_escalated",
    "reported_answered",
)
KNOWN_DEFLECTION_OUTCOMES = frozenset(DEFLECTION_OUTCOMES)


def _utc_now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso_datetime(value, field):
    """Parse an ISO-8601 datetime; naive values are read as UTC.
    Mirrors the core store's parsing discipline."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise ValidationError(
                "%s is not a valid ISO-8601 datetime: %r" % (field, value))
    else:
        raise ValidationError("%s must be an ISO-8601 datetime string" % (field,))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    return value


def _pos_int(value, what):
    _int(value, what)
    if value < 1:
        raise ValidationError("%s must be a positive integer" % (what,))
    return value


def _nonneg_int(value, what):
    _int(value, what)
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _money(value, what):
    """Integer cents; booleans and floats are rejected (house rule).
    Recorded amounts are data about a workflow recorded elsewhere;
    no money moves in this build."""
    return _nonneg_int(value, what)


def _one_of(value, known, names, what):
    if value not in known:
        raise ValidationError("%s must be one of %s" % (what, ", ".join(names)))
    return value


def _string_list(value, what):
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
                "each entry in %s must be a non-empty string" % (what,))
        result.append(item)
    return result


class CustsvcExtensions:
    """GAPS-batch extension surface over a core CustsvcStore."""

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

        Mirrors the core store: an actor must be present; User-like
        actors are checked against the core permission matrix before
        anything changes; plain strings carry identity only.
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
            record["created_utc"] = _iso(_utc_now())
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            try:
                self._audit(actor, audit_action, record_id,
                            details={"kind": kind})
            except Exception:
                # Fail closed, mirroring the batch pattern: an
                # operation whose audit write fails does not proceed
                # -- the insertion and the id roll back before the
                # error propagates.
                del self._records[(kind, record_id)]
                self._order.pop()
                self._counters[prefix] -= 1
                raise
            return copy.deepcopy(record)

    def _get(self, kind, record_id):
        record = self._records.get((kind, record_id))
        if record is None:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id):
        return copy.deepcopy(self._get(kind, record_id))

    def _list(self, kind, **filters):
        result = []
        for key in self._order:
            if key[0] != kind:
                continue
            record = self._records[key]
            if all(record.get(f) == v for f, v in filters.items()):
                result.append(copy.deepcopy(record))
        return result

    def _core_case(self, case_id, actor):
        """Return the core case view (NotFoundError if absent)."""
        return self.store.get_case(case_id, actor)

    def _core_requester_ref(self, ref, actor):
        """Return the core requester for an opaque ref."""
        return self.store.get_requester_by_ref(ref, actor)

    # -- automation execution requests (Extended: execution engines) --
    #
    # The core rule registry never evaluates a condition and never
    # executes an action, and this surface does not repeal that: an
    # execution request is a RECORD that a run of a registered rule
    # was requested, and an execution report stores, verbatim, the
    # outcome an executor elsewhere reported. ``executed_here`` is
    # False on every record this surface creates.

    def request_rule_execution(self, rule_id, actor, note=None):
        """Record a request to execute a core automation rule.

        The rule must exist in the core registry. Nothing is
        evaluated and nothing runs: the request is lodged as a
        record with ``executed_here: False`` and
        ``state: recorded_request_only``.
        """
        self._guard(actor, "rule_write", "ext_rule_execution_request",
                    target=rule_id)
        _string_or_none(note, "note")
        rule = None
        for candidate in self.store.list_rules(actor):
            if candidate["id"] == rule_id:
                rule = candidate
                break
        if rule is None:
            raise NotFoundError("rule not found: %r" % (rule_id,))
        return self._create(
            "rule_execution_request", "exec",
            {"rule_id": rule_id, "rule_name": rule["name"],
             "rule_enabled_at_request": bool(rule["enabled"]),
             "note": note, "executed_here": False,
             "state": "recorded_request_only"},
            actor, "ext_rule_execution_request")

    def record_execution_report(self, request_id, outcome, actor, detail=None):
        """Record an executor's reported outcome for a request.

        The outcome is stored verbatim as reported; the build
        executed nothing, so the report itself also carries
        ``executed_here: False``.
        """
        self._guard(actor, "rule_write", "ext_rule_execution_report",
                    target=request_id)
        _one_of(outcome, KNOWN_EXECUTION_REPORT_OUTCOMES,
                EXECUTION_REPORT_OUTCOMES, "outcome")
        _string_or_none(detail, "detail")
        self._get("rule_execution_request", request_id)
        return self._create(
            "rule_execution_report", "execr",
            {"request_id": request_id, "outcome": outcome,
             "detail": detail, "reported": True, "executed_here": False},
            actor, "ext_rule_execution_report")

    def get_rule_execution_request(self, request_id, actor):
        self._guard_read(actor, "rule_read", "ext_rule_execution_get",
                         target=request_id)
        return self._fetch("rule_execution_request", request_id)

    def list_rule_execution_requests(self, actor, rule_id=None):
        self._guard_read(actor, "rule_read", "ext_rule_execution_list")
        filters = {}
        if rule_id is not None:
            filters["rule_id"] = rule_id
        return self._list("rule_execution_request", **filters)

    def execution_summary(self, actor):
        """Derived at read: request/report counts over this surface's
        own records. Nothing is stored on any record."""
        self._guard_read(actor, "report_read", "ext_execution_summary")
        requests = self._list("rule_execution_request")
        reports = self._list("rule_execution_report")
        by_outcome = {o: 0 for o in EXECUTION_REPORT_OUTCOMES}
        for report in reports:
            by_outcome[report["outcome"]] += 1
        return {"requests": len(requests), "reports": len(reports),
                "reports_by_outcome": by_outcome,
                "executed_here": False, "derived": True,
                "method": "counts_over_execution_request_records"}

    # -- GRC platform (Extended) ---------------------------------------
    #
    # Framework and control records, plus mapping records binding
    # core cases to controls. Posture is counts derived at read over
    # the mappings and the core case views; no framework is assessed
    # and no control is evaluated.

    def register_framework(self, name, actor, version_label=None):
        """Register a compliance framework record (a label set, not
        an assessment)."""
        self._guard(actor, "case_write", "ext_framework_register")
        _non_empty(name, "name")
        _string_or_none(version_label, "version_label")
        return self._create(
            "framework", "fw",
            {"name": name, "version_label": version_label},
            actor, "ext_framework_register")

    def get_framework(self, framework_id, actor):
        self._guard_read(actor, "case_read", "ext_framework_get",
                         target=framework_id)
        return self._fetch("framework", framework_id)

    def list_frameworks(self, actor):
        self._guard_read(actor, "case_read", "ext_framework_list")
        return self._list("framework")

    def register_control(self, framework_id, control_ref, title, actor):
        """Register a control record under a framework. ``control_ref``
        is the caller's own opaque label for the control (for example
        a framework's clause number, held as data)."""
        self._guard(actor, "case_write", "ext_control_register",
                    target=framework_id)
        _non_empty(control_ref, "control_ref")
        _non_empty(title, "title")
        self._get("framework", framework_id)
        return self._create(
            "control", "ctl",
            {"framework_id": framework_id, "control_ref": control_ref,
             "title": title},
            actor, "ext_control_register")

    def get_control(self, control_id, actor):
        self._guard_read(actor, "case_read", "ext_control_get",
                         target=control_id)
        return self._fetch("control", control_id)

    def list_controls(self, actor, framework_id=None):
        self._guard_read(actor, "case_read", "ext_control_list")
        filters = {}
        if framework_id is not None:
            filters["framework_id"] = framework_id
        return self._list("control", **filters)

    def map_case_to_control(self, case_id, control_id, actor, note=None):
        """Record a mapping between a core case and a control.

        Both ends must exist. The mapping is a record about the
        case; it changes no core state.
        """
        self._guard(actor, "case_write", "ext_case_control_map",
                    target=case_id)
        _string_or_none(note, "note")
        self._core_case(case_id, actor)
        self._get("control", control_id)
        return self._create(
            "case_control_mapping", "cmap",
            {"case_id": case_id, "control_id": control_id, "note": note},
            actor, "ext_case_control_map")

    def list_case_control_mappings(self, actor, case_id=None, control_id=None):
        self._guard_read(actor, "case_read", "ext_case_control_map_list")
        filters = {}
        if case_id is not None:
            filters["case_id"] = case_id
        if control_id is not None:
            filters["control_id"] = control_id
        return self._list("case_control_mapping", **filters)

    def framework_posture(self, framework_id, actor, now=None):
        """Derived at read: counts over the framework's controls,
        the mappings onto them, and the mapped core cases (status
        counts and the core's own derived breach flag). Posture is
        counts only; no score is computed and nothing is stored."""
        self._guard_read(actor, "report_read", "ext_framework_posture",
                         target=framework_id)
        self._get("framework", framework_id)
        controls = self._list("control", framework_id=framework_id)
        control_ids = {c["id"] for c in controls}
        mappings = [m for m in self._list("case_control_mapping")
                    if m["control_id"] in control_ids]
        case_ids = []
        for mapping in mappings:
            if mapping["case_id"] not in case_ids:
                case_ids.append(mapping["case_id"])
        by_status = {}
        breached = 0
        for case_id in case_ids:
            view = self.store.get_case(case_id, actor, now=now)
            by_status[view["status"]] = by_status.get(view["status"], 0) + 1
            if view["breached"]:
                breached += 1
        return {"framework_id": framework_id,
                "controls": len(controls), "mappings": len(mappings),
                "mapped_cases": len(case_ids),
                "mapped_cases_by_status": by_status,
                "mapped_cases_breached": breached,
                "derived": True, "method": "counts_over_mapping_records"}

    # -- knowledge base (Extended: named absence at both tiers) --------
    #
    # Article records with append-only revisions. A revision is a
    # new record; no revision is ever edited or deleted, and the
    # article's current title/body are derived at read from its
    # latest revision.

    def create_article(self, title, body, actor, tags=None):
        """Create a knowledge-base article (its first revision)."""
        self._guard(actor, "case_write", "ext_article_create")
        _non_empty(title, "title")
        if not isinstance(body, str):
            raise ValidationError("body must be a string")
        tags = _string_list(tags, "tags")
        article = self._create(
            "article", "kb",
            {"tags": tags},
            actor, "ext_article_create")
        self._append_revision(article["id"], title, body, actor)
        return self.get_article(article["id"], actor)

    def _append_revision(self, article_id, title, body, actor):
        existing = self._list("article_revision", article_id=article_id)
        return self._create(
            "article_revision", "kbrev",
            {"article_id": article_id, "revision": len(existing) + 1,
             "title": title, "body": body},
            actor, "ext_article_revision")

    def revise_article(self, article_id, actor, title=None, body=None):
        """Append a revision to an article. At least one of
        ``title`` / ``body`` must be given; the other carries over
        from the current revision. Earlier revisions never change."""
        self._guard(actor, "case_write", "ext_article_revision",
                    target=article_id)
        self._get("article", article_id)
        if title is None and body is None:
            raise ValidationError("a revision must change title or body")
        if title is not None:
            _non_empty(title, "title")
        if body is not None and not isinstance(body, str):
            raise ValidationError("body must be a string")
        current = self._current_revision(article_id)
        self._append_revision(
            article_id,
            title if title is not None else current["title"],
            body if body is not None else current["body"],
            actor)
        return self.get_article(article_id, actor)

    def _current_revision(self, article_id):
        revisions = self._list("article_revision", article_id=article_id)
        if not revisions:
            raise NotFoundError("article not found: %r" % (article_id,))
        return revisions[-1]

    def get_article(self, article_id, actor):
        """The article view: current title/body derived at read from
        the latest revision, with the revision count. The stored
        article record itself holds neither."""
        self._guard_read(actor, "case_read", "ext_article_get",
                         target=article_id)
        article = self._fetch("article", article_id)
        revisions = self._list("article_revision", article_id=article_id)
        current = revisions[-1]
        view = dict(article)
        view["title"] = current["title"]
        view["body"] = current["body"]
        view["revision_count"] = len(revisions)
        view["current_revision_id"] = current["id"]
        return view

    def list_articles(self, actor):
        self._guard_read(actor, "case_read", "ext_article_list")
        return [self.get_article(a["id"], actor)
                for a in self._list("article")]

    def list_article_revisions(self, article_id, actor):
        """All revisions of an article, oldest first (append-only:
        the full history is the record)."""
        self._guard_read(actor, "case_read", "ext_article_revision_list",
                         target=article_id)
        self._get("article", article_id)
        return self._list("article_revision", article_id=article_id)

    def search_articles(self, query, actor):
        """Substring search over current article titles and bodies
        (registry metadata search over this surface's records, not
        a search engine)."""
        self._guard_read(actor, "case_read", "ext_article_search")
        _non_empty(query, "query")
        needle = query.lower()
        out = []
        for article in self._list("article"):
            view = self.get_article(article["id"], actor)
            if needle in view["title"].lower() or needle in view["body"].lower():
                out.append(view)
        return out

    # -- satisfaction / CSAT surveys (Extended: named absence) ---------
    #
    # Survey instruments and response records. A response stores the
    # rating exactly as recorded (verbatim) plus an optional comment
    # exactly as given. Tallies are derived at read: counts, the
    # rating distribution, and the mean as an exact rational
    # (numerator/denominator over the recorded ratings) -- never a
    # stored score, never a float.

    def create_survey(self, title, actor, case_id=None, scale_max=5):
        """Create a survey instrument record. ``scale_max`` bounds
        the rating scale (2..10, default 5) and is part of the
        instrument's recorded terms."""
        self._guard(actor, "case_write", "ext_survey_create")
        _non_empty(title, "title")
        _int(scale_max, "scale_max")
        if scale_max < 2 or scale_max > 10:
            raise ValidationError("scale_max must be between 2 and 10")
        if case_id is not None:
            self._core_case(case_id, actor)
        return self._create(
            "survey", "svy",
            {"title": title, "case_id": case_id, "scale_max": scale_max},
            actor, "ext_survey_create")

    def get_survey(self, survey_id, actor):
        self._guard_read(actor, "case_read", "ext_survey_get",
                         target=survey_id)
        return self._fetch("survey", survey_id)

    def list_surveys(self, actor):
        self._guard_read(actor, "case_read", "ext_survey_list")
        return self._list("survey")

    def record_survey_response(self, survey_id, requester_ref, rating,
                               actor, comment=None):
        """Record one survey response. The respondent is a core
        requester, named by opaque ref only; the rating must be an
        integer within the instrument's recorded scale and is
        stored verbatim."""
        self._guard(actor, "case_write", "ext_survey_response",
                    target=survey_id)
        _string_or_none(comment, "comment")
        survey = self._get("survey", survey_id)
        self._core_requester_ref(requester_ref, actor)
        _int(rating, "rating")
        if rating < 1 or rating > survey["scale_max"]:
            raise ValidationError(
                "rating must be between 1 and the survey's scale_max (%d)"
                % (survey["scale_max"],))
        return self._create(
            "survey_response", "svr",
            {"survey_id": survey_id, "requester_ref": requester_ref,
             "rating": rating, "comment": comment},
            actor, "ext_survey_response")

    def list_survey_responses(self, survey_id, actor):
        self._guard_read(actor, "case_read", "ext_survey_response_list",
                         target=survey_id)
        self._get("survey", survey_id)
        return self._list("survey_response", survey_id=survey_id)

    def survey_tally(self, survey_id, actor):
        """Derived at read over the recorded responses: the count,
        the full-scale distribution, and the mean as an exact
        rational. The stored survey and response records carry no
        tally or score key."""
        self._guard_read(actor, "report_read", "ext_survey_tally",
                         target=survey_id)
        survey = self._get("survey", survey_id)
        responses = self._list("survey_response", survey_id=survey_id)
        distribution = {str(r): 0
                        for r in range(1, survey["scale_max"] + 1)}
        total = 0
        for response in responses:
            distribution[str(response["rating"])] += 1
            total += response["rating"]
        mean = None
        if responses:
            exact = Fraction(total, len(responses))
            mean = {"numerator": exact.numerator,
                    "denominator": exact.denominator}
        return {"survey_id": survey_id,
                "response_count": len(responses),
                "distribution": distribution,
                "mean_rating": mean,
                "derived": True,
                "method": "exact_rational_mean_of_recorded_ratings"}

    # -- SLA policy engine (Extended) -----------------------------------
    #
    # Policy records hold SLA terms as data: per-priority resolution
    # targets in minutes. Breach state under a policy is derived at
    # read from the core case record (created_utc, priority, status)
    # against the recorded terms -- the seam is
    # ``_is_breached_under_policy`` -- and is never stored, never
    # written back onto the case. This derivation coexists with the
    # core's own due_at derivation; neither replaces the other.

    def create_sla_policy(self, name, targets_minutes, actor):
        """Register an SLA policy record. ``targets_minutes`` maps
        priority -> resolution target in minutes (positive ints);
        priorities outside the core set are rejected."""
        self._guard(actor, "rule_write", "ext_sla_policy_create")
        _non_empty(name, "name")
        if not isinstance(targets_minutes, dict) or not targets_minutes:
            raise ValidationError("targets_minutes must be a non-empty object")
        targets = {}
        for priority, minutes in targets_minutes.items():
            if priority not in PRIORITIES:
                raise ValidationError(
                    "priority must be one of %s" % (PRIORITIES,))
            targets[priority] = _pos_int(minutes,
                                         "targets_minutes[%s]" % (priority,))
        return self._create(
            "sla_policy", "sla",
            {"name": name, "targets_minutes": targets},
            actor, "ext_sla_policy_create")

    def get_sla_policy(self, policy_id, actor):
        self._guard_read(actor, "rule_read", "ext_sla_policy_get",
                         target=policy_id)
        return self._fetch("sla_policy", policy_id)

    def list_sla_policies(self, actor):
        self._guard_read(actor, "rule_read", "ext_sla_policy_list")
        return self._list("sla_policy")

    def _is_breached_under_policy(self, case, policy, now_dt):
        """True iff ``case`` is past the resolution target its
        priority carries in ``policy`` and not in a terminal status.

        Single derivation point for policy breach state; see the
        mutation record in tests/README.md (the batch's fresh
        negative control). Cases whose priority the policy does not
        cover are never breached under it.
        """
        target = policy["targets_minutes"].get(case["priority"])
        if target is None or case["status"] in TERMINAL_STATUSES:
            return False
        created = _parse_iso_datetime(case["created_utc"], "created_utc")
        return now_dt > created + timedelta(minutes=target)

    def sla_case_view(self, policy_id, case_id, actor, now=None):
        """Derived at read: the case's standing under one recorded
        policy. Nothing is stored and the core case is untouched."""
        self._guard_read(actor, "case_read", "ext_sla_case_view",
                         target=case_id)
        policy = self._get("sla_policy", policy_id)
        case = self._core_case(case_id, actor)
        now_dt = _parse_iso_datetime(now, "now") if now is not None \
            else _utc_now()
        target = policy["targets_minutes"].get(case["priority"])
        effective_due = None
        if target is not None:
            created = _parse_iso_datetime(case["created_utc"], "created_utc")
            effective_due = _iso(created + timedelta(minutes=target))
        return {"policy_id": policy_id, "case_id": case_id,
                "priority": case["priority"], "status": case["status"],
                "covered": target is not None,
                "target_minutes": target,
                "effective_due_at": effective_due,
                "breached": self._is_breached_under_policy(case, policy, now_dt),
                "derived": True,
                "method": "recorded_policy_terms_over_core_case_record"}

    def sla_breach_report(self, policy_id, actor, now=None):
        """Derived at read: breach counts under one recorded policy
        over all core cases, overall and per priority."""
        self._guard_read(actor, "report_read", "ext_sla_breach_report",
                         target=policy_id)
        policy = self._get("sla_policy", policy_id)
        now_dt = _parse_iso_datetime(now, "now") if now is not None \
            else _utc_now()
        by_priority = {p: {"evaluated": 0, "breached": 0} for p in PRIORITIES}
        breached_ids = []
        evaluated = 0
        for case in self.store.list_cases(actor, now=now):
            if case["priority"] not in policy["targets_minutes"]:
                continue
            evaluated += 1
            by_priority[case["priority"]]["evaluated"] += 1
            if self._is_breached_under_policy(case, policy, now_dt):
                breached_ids.append(case["id"])
                by_priority[case["priority"]]["breached"] += 1
        return {"policy_id": policy_id, "evaluated": evaluated,
                "breached": len(breached_ids),
                "breached_case_ids": breached_ids,
                "by_priority": by_priority,
                "derived": True,
                "method": "recorded_policy_terms_over_core_case_record"}

    # -- notification delivery & status-page hosting (Extended) --------
    #
    # Delivery: notification records plus delivery reports stored
    # verbatim as reported by delivery systems elsewhere. Every
    # record carries ``reference_transport: True`` and
    # ``delivered_here: False`` -- nothing is delivered by this
    # build. Status pages: a page record is configuration over the
    # core's derived public status view; the view itself stays the
    # core's derivation, served from core records, not hosted here.

    def record_notification(self, case_id, channel_label, recipient_ref,
                            actor):
        """Record a notification intended for a case's requester.
        The recipient is named by opaque requester ref; the channel
        is a caller-supplied label held as data."""
        self._guard(actor, "case_write", "ext_notification_record",
                    target=case_id)
        _non_empty(channel_label, "channel_label")
        _non_empty(recipient_ref, "recipient_ref")
        self._core_case(case_id, actor)
        self._core_requester_ref(recipient_ref, actor)
        return self._create(
            "notification", "ntf",
            {"case_id": case_id, "channel_label": channel_label,
             "recipient_ref": recipient_ref,
             "reference_transport": True, "delivered_here": False,
             "state": "recorded_reference_only"},
            actor, "ext_notification_record")

    def record_delivery_report(self, notification_id, outcome, actor,
                               detail=None):
        """Record a delivery system's reported outcome for a
        notification, verbatim. The build delivered nothing."""
        self._guard(actor, "case_write", "ext_delivery_report",
                    target=notification_id)
        _one_of(outcome, KNOWN_DELIVERY_OUTCOMES, DELIVERY_OUTCOMES,
                "outcome")
        _string_or_none(detail, "detail")
        self._get("notification", notification_id)
        return self._create(
            "delivery_report", "ntr",
            {"notification_id": notification_id, "outcome": outcome,
             "detail": detail, "reported": True,
             "reference_transport": True, "delivered_here": False},
            actor, "ext_delivery_report")

    def get_notification(self, notification_id, actor):
        self._guard_read(actor, "case_read", "ext_notification_get",
                         target=notification_id)
        return self._fetch("notification", notification_id)

    def list_notifications(self, actor, case_id=None):
        self._guard_read(actor, "case_read", "ext_notification_list")
        filters = {}
        if case_id is not None:
            filters["case_id"] = case_id
        return self._list("notification", **filters)

    def notification_summary(self, actor):
        """Derived at read: notification and delivery-report counts
        over this surface's own records."""
        self._guard_read(actor, "report_read", "ext_notification_summary")
        notifications = self._list("notification")
        reports = self._list("delivery_report")
        by_outcome = {o: 0 for o in DELIVERY_OUTCOMES}
        for report in reports:
            by_outcome[report["outcome"]] += 1
        return {"notifications": len(notifications),
                "delivery_reports": len(reports),
                "reports_by_outcome": by_outcome,
                "delivered_here": False, "derived": True,
                "method": "counts_over_notification_records"}

    def record_status_page(self, name, actor):
        """Register a status-page record: configuration naming the
        core's derived public status view as its source. The page
        is not hosted here (``hosted_here: False``)."""
        self._guard(actor, "case_write", "ext_status_page_record")
        _non_empty(name, "name")
        return self._create(
            "status_page", "stp",
            {"name": name, "reference_stub": True, "hosted_here": False,
             "view_source": "core_public_status_derivation",
             "state": "recorded_reference_only"},
            actor, "ext_status_page_record")

    def get_status_page(self, page_id, actor):
        self._guard_read(actor, "case_read", "ext_status_page_get",
                         target=page_id)
        return self._fetch("status_page", page_id)

    def status_page_view(self, page_id, actor, now=None):
        """The page's content: the core store's derived public
        status view, labeled as served from core records. The page
        record adds no content of its own."""
        self._guard_read(actor, "case_read", "ext_status_page_view",
                         target=page_id)
        page = self._get("status_page", page_id)
        view = self.store.public_status(actor, now=now)
        view = dict(view)
        view["page_id"] = page["id"]
        view["served_from"] = "core_public_status_derivation"
        view["hosted_here"] = False
        return view

    # -- reporting / analytics beyond registry reporting (Extended) ----
    #
    # Deterministic derivations over core records, computed at read
    # and stored nowhere. Counts and exact count pairs only -- the
    # same honesty bound as the core's registry reporting, one level
    # up: no learned model, no float rate.

    def analytics_report(self, actor, now=None):
        """Derived at read over the core's cases and alerts:
        distributions the registry summary does not carry (channel,
        assignee, requester, severity, linkage, breach by
        priority)."""
        self._guard_read(actor, "report_read", "ext_analytics_report")
        now_dt = _parse_iso_datetime(now, "now") if now is not None \
            else _utc_now()
        cases = self.store.list_cases(actor, now=now)
        by_channel = {}
        by_assignee = {}
        breached_by_priority = {p: 0 for p in PRIORITIES}
        requesters = set()
        for case in cases:
            channel = case["channel"] if case["channel"] is not None \
                else "unspecified"
            by_channel[channel] = by_channel.get(channel, 0) + 1
            assignee = case["assignee"] if case["assignee"] is not None \
                else "unassigned"
            bucket = by_assignee.setdefault(
                assignee, {"cases": 0, "breached": 0})
            bucket["cases"] += 1
            if case["breached"]:
                bucket["breached"] += 1
                breached_by_priority[case["priority"]] += 1
            requesters.add(case["requester_ref"])
        alerts = self.store.list_alerts(actor)
        by_severity = {}
        linked = 0
        for alert in alerts:
            by_severity[alert["severity"]] = \
                by_severity.get(alert["severity"], 0) + 1
            if alert["case_id"] is not None:
                linked += 1
        return {"cases": len(cases),
                "cases_by_channel": by_channel,
                "cases_by_assignee": by_assignee,
                "breached_by_priority": breached_by_priority,
                "distinct_requesters_with_cases": len(requesters),
                "alerts": len(alerts),
                "alerts_by_severity": by_severity,
                "alert_linkage": {"linked": linked,
                                  "unlinked": len(alerts) - linked,
                                  "total": len(alerts)},
                "derived": True,
                "method": "deterministic_counts_over_core_records"}

    # -- commerce platform hosting & POS (stub-engine) ------------------
    #
    # One sibling's entire domain, shipped as labeled reference
    # records: site registrations over opaque site refs and state
    # reports stored verbatim. No site is hosted, no transaction is
    # processed, and no record shape can hold a payment instrument
    # or an amount in motion.

    def register_commerce_site(self, site_ref, domain, actor):
        """Register a commerce site reference record."""
        self._guard(actor, "case_write", "ext_commerce_site_register")
        _non_empty(site_ref, "site_ref")
        _one_of(domain, KNOWN_COMMERCE_DOMAINS, COMMERCE_DOMAINS, "domain")
        return self._create(
            "commerce_site", "pos",
            {"site_ref": site_ref, "domain": domain,
             "reference_stub": True, "hosted_here": False,
             "state": "recorded_reference_only"},
            actor, "ext_commerce_site_register")

    def get_commerce_site(self, site_id, actor):
        self._guard_read(actor, "case_read", "ext_commerce_site_get",
                         target=site_id)
        return self._fetch("commerce_site", site_id)

    def list_commerce_sites(self, actor):
        self._guard_read(actor, "case_read", "ext_commerce_site_list")
        return self._list("commerce_site")

    def record_commerce_report(self, site_id, outcome, actor, detail=None):
        """Record a commerce platform's reported state, verbatim."""
        self._guard(actor, "case_write", "ext_commerce_report",
                    target=site_id)
        _one_of(outcome, KNOWN_COMMERCE_REPORT_OUTCOMES,
                COMMERCE_REPORT_OUTCOMES, "outcome")
        _string_or_none(detail, "detail")
        self._get("commerce_site", site_id)
        return self._create(
            "commerce_report", "posr",
            {"site_id": site_id, "outcome": outcome, "detail": detail,
             "reported": True, "reference_stub": True},
            actor, "ext_commerce_report")

    # -- PCS relocation platform (stub-engine) ---------------------------
    #
    # The other sibling's entire domain, shipped as labeled
    # reference records: relocation cases over opaque employee refs
    # (registered core requesters) and workflow step records with
    # recorded states. Amounts, where a step carries one, are
    # integer cents held as data about the recorded workflow; no
    # obligation is created, no voucher is paid, and no financial
    # system is interfaced.

    def create_relocation_case(self, employee_ref, actor):
        """Open a relocation case reference record. The employee is
        a core requester, named by opaque ref only."""
        self._guard(actor, "case_write", "ext_relocation_case_create")
        _non_empty(employee_ref, "employee_ref")
        self._core_requester_ref(employee_ref, actor)
        return self._create(
            "relocation_case", "pcs",
            {"employee_ref": employee_ref, "reference_stub": True,
             "processed_here": False, "state": "recorded_reference_only"},
            actor, "ext_relocation_case_create")

    def get_relocation_case(self, case_id, actor):
        self._guard_read(actor, "case_read", "ext_relocation_case_get",
                         target=case_id)
        return self._fetch("relocation_case", case_id)

    def list_relocation_cases(self, actor):
        self._guard_read(actor, "case_read", "ext_relocation_case_list")
        return self._list("relocation_case")

    def record_relocation_step(self, case_id, step, actor, amount_cents=None,
                               note=None):
        """Record one workflow step against a relocation case. The
        step is a recorded state in the workflow's shape; recording
        it performs nothing."""
        self._guard(actor, "case_write", "ext_relocation_step",
                    target=case_id)
        _one_of(step, KNOWN_RELOCATION_STEPS, RELOCATION_STEPS, "step")
        if amount_cents is not None:
            amount_cents = _money(amount_cents, "amount_cents")
        _string_or_none(note, "note")
        self._get("relocation_case", case_id)
        return self._create(
            "relocation_step", "pcss",
            {"case_id": case_id, "step": step,
             "amount_cents": amount_cents, "note": note,
             "reference_stub": True, "executed_here": False},
            actor, "ext_relocation_step")

    def list_relocation_steps(self, case_id, actor):
        self._guard_read(actor, "case_read", "ext_relocation_step_list",
                         target=case_id)
        self._get("relocation_case", case_id)
        return self._list("relocation_step", case_id=case_id)

    # -- e-signature & PIV signer identity assurance (stub-engine) -------
    #
    # Signature request records against core cases, and assurance
    # reports stored verbatim. Nothing is signed: no record shape
    # can hold signature bytes, a certificate, or a credential, and
    # the signer is a core requester named by opaque ref. The
    # assurance label is whatever the signing system elsewhere
    # reported, held as data -- identity proofing stays with the
    # embedding organization (PLATFORM-LAYER.md decision 1).

    def record_signature_request(self, case_id, signer_ref, actor):
        """Record a signature request against a core case."""
        self._guard(actor, "case_write", "ext_signature_request",
                    target=case_id)
        _non_empty(signer_ref, "signer_ref")
        self._core_case(case_id, actor)
        self._core_requester_ref(signer_ref, actor)
        return self._create(
            "signature_request", "sig",
            {"case_id": case_id, "signer_ref": signer_ref,
             "reference_stub": True, "signed_here": False,
             "state": "recorded_reference_only"},
            actor, "ext_signature_request")

    def get_signature_request(self, request_id, actor):
        self._guard_read(actor, "case_read", "ext_signature_request_get",
                         target=request_id)
        return self._fetch("signature_request", request_id)

    def record_signature_report(self, request_id, outcome, assurance_label,
                                actor):
        """Record a signing system's reported outcome and its
        reported signer-assurance label, verbatim."""
        self._guard(actor, "case_write", "ext_signature_report",
                    target=request_id)
        _one_of(outcome, KNOWN_SIGNATURE_OUTCOMES, SIGNATURE_OUTCOMES,
                "outcome")
        _non_empty(assurance_label, "assurance_label")
        self._get("signature_request", request_id)
        return self._create(
            "signature_report", "sigr",
            {"request_id": request_id, "outcome": outcome,
             "assurance_label": assurance_label, "reported": True,
             "reference_stub": True, "signature_held": False},
            actor, "ext_signature_report")

    def list_signature_reports(self, request_id, actor):
        self._guard_read(actor, "case_read", "ext_signature_report_list",
                         target=request_id)
        self._get("signature_request", request_id)
        return self._list("signature_report", request_id=request_id)

    # -- event detection, diagnosis & orchestration (stub-engine) --------
    #
    # Detection-source registrations and orchestration run records
    # stored verbatim as reported. Detection happens in source
    # systems elsewhere; the core's alert ingest remains the only
    # path by which an alert record comes to exist, and an
    # orchestration record creates none.

    def register_detection_source(self, source_ref, actor):
        """Register a detection source reference record."""
        self._guard(actor, "case_write", "ext_detection_source_register")
        _non_empty(source_ref, "source_ref")
        return self._create(
            "detection_source", "det",
            {"source_ref": source_ref, "reference_stub": True,
             "detects_here": False, "state": "recorded_reference_only"},
            actor, "ext_detection_source_register")

    def get_detection_source(self, source_id, actor):
        self._guard_read(actor, "case_read", "ext_detection_source_get",
                         target=source_id)
        return self._fetch("detection_source", source_id)

    def record_orchestration_run(self, source_id, outcome, actor,
                                 alert_id=None, detail=None):
        """Record an orchestration engine's reported run. ``alert_id``,
        when given, must name an existing core alert -- the run
        record references it; it does not create or modify it."""
        self._guard(actor, "case_write", "ext_orchestration_run",
                    target=source_id)
        _one_of(outcome, KNOWN_ORCHESTRATION_OUTCOMES,
                ORCHESTRATION_OUTCOMES, "outcome")
        _string_or_none(detail, "detail")
        self._get("detection_source", source_id)
        if alert_id is not None:
            found = [a for a in self.store.list_alerts(actor)
                     if a["id"] == alert_id]
            if not found:
                raise NotFoundError("alert not found: %r" % (alert_id,))
        return self._create(
            "orchestration_run", "orc",
            {"source_id": source_id, "outcome": outcome,
             "alert_id": alert_id, "detail": detail, "reported": True,
             "reference_stub": True, "executed_here": False},
            actor, "ext_orchestration_run")

    def list_orchestration_runs(self, source_id, actor):
        self._guard_read(actor, "alert_read", "ext_orchestration_run_list",
                         target=source_id)
        self._get("detection_source", source_id)
        return self._list("orchestration_run", source_id=source_id)

    # -- real-time channels: live chat, voice / telephony (stub-engine) --
    #
    # Channel registrations and session records. No media exists in
    # this build: a session record states that a session was
    # reported against a case; nothing connects, streams, or is
    # recorded as media.

    def register_channel(self, channel_ref, kind, actor):
        """Register a real-time channel reference record."""
        self._guard(actor, "case_write", "ext_channel_register")
        _non_empty(channel_ref, "channel_ref")
        _one_of(kind, KNOWN_CHANNEL_KINDS, CHANNEL_KINDS, "kind")
        return self._create(
            "channel", "chn",
            {"channel_ref": channel_ref, "kind": kind,
             "reference_stub": True, "media_here": False,
             "state": "recorded_reference_only"},
            actor, "ext_channel_register")

    def get_channel(self, channel_id, actor):
        self._guard_read(actor, "case_read", "ext_channel_get",
                         target=channel_id)
        return self._fetch("channel", channel_id)

    def record_channel_session(self, channel_id, case_id, actor):
        """Record a reported channel session against a core case."""
        self._guard(actor, "case_write", "ext_channel_session",
                    target=channel_id)
        self._get("channel", channel_id)
        self._core_case(case_id, actor)
        return self._create(
            "channel_session", "chs",
            {"channel_id": channel_id, "case_id": case_id,
             "reference_stub": True, "connected_here": False},
            actor, "ext_channel_session")

    def list_channel_sessions(self, channel_id, actor):
        self._guard_read(actor, "case_read", "ext_channel_session_list",
                         target=channel_id)
        self._get("channel", channel_id)
        return self._list("channel_session", channel_id=channel_id)

    # -- AI assistance / deflection (stub-engine) -------------------------
    #
    # Assistant registrations and deflection reports stored verbatim
    # as reported. No model runs: the build deflects nothing, answers
    # nothing, and decides nothing about any case.

    def register_assistant(self, assistant_ref, actor):
        """Register an AI assistant reference record."""
        self._guard(actor, "case_write", "ext_assistant_register")
        _non_empty(assistant_ref, "assistant_ref")
        return self._create(
            "assistant", "ai",
            {"assistant_ref": assistant_ref, "reference_stub": True,
             "inference_here": False,
             "method": "recorded_declaration_only",
             "state": "recorded_reference_only"},
            actor, "ext_assistant_register")

    def get_assistant(self, assistant_id, actor):
        self._guard_read(actor, "case_read", "ext_assistant_get",
                         target=assistant_id)
        return self._fetch("assistant", assistant_id)

    def record_deflection_report(self, assistant_id, case_id, outcome,
                                 actor):
        """Record an assistant's reported outcome for a core case,
        verbatim. The case itself is untouched."""
        self._guard(actor, "case_write", "ext_deflection_report",
                    target=assistant_id)
        _one_of(outcome, KNOWN_DEFLECTION_OUTCOMES, DEFLECTION_OUTCOMES,
                "outcome")
        self._get("assistant", assistant_id)
        self._core_case(case_id, actor)
        return self._create(
            "deflection_report", "air",
            {"assistant_id": assistant_id, "case_id": case_id,
             "outcome": outcome, "reported": True,
             "reference_stub": True, "decided_here": False},
            actor, "ext_deflection_report")

    def list_deflection_reports(self, assistant_id, actor):
        self._guard_read(actor, "case_read", "ext_deflection_report_list",
                         target=assistant_id)
        self._get("assistant", assistant_id)
        return self._list("deflection_report", assistant_id=assistant_id)
