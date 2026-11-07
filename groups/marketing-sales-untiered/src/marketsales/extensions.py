"""Final GAPS batch extensions for the Marketing & Sales build.

One new module, per gaps-batch/DECISION.md: the eight open entries
of GAPS.md's "Untiered Set 18 — Marketing & Sales" section land
here as records over the core `marketsales` substrate. Every core
module is byte-identical; this module wraps a core
:class:`~marketsales.store.MarketSalesStore` and keeps its own
record tables.

Tier discipline binds the whole surface: this set is untiered —
``fedramp_impact_level`` "Unknown", ``cmmc_tier`` null — and no
record or view created here carries a tier, baseline, impact
level, or equivalence key of any kind (pinned by a recursive scan
in the batch tests, the Data Management untiered model).

Dispositions (see BATCH.md for the per-entry record):

- **Built** in records form: market intelligence & competitor /
  forecast analytics (idx 914 — analyst-recorded intelligence and
  forecast reports, plus a market view of deterministic counts
  derived at read over the substrate's own opportunity,
  evaluation, and pipeline records; nothing is gathered, analyzed,
  or projected here, and the view states its method and returns
  counts only — no rates, per the core's scoring discipline); and
  bounce/complaint handling automation, campaign template
  management, preference management (idx 919 — handling-rule
  definitions held as data, a handling queue derived at read from
  core delivery and suppression records, handling-decision
  records, template metadata versions in the core content
  records' form, and preference records with the current value
  derived at read).
- **Reference** (labeled reference implementations,
  ``reference_stub: True`` on every record): AI models / agents
  (idx 912, as drafted — request records and reported outcomes;
  the signature refuses result content, so no inference result
  can be held); live opportunity-discovery feeds &
  contract-search engines (idx 913, as drafted — feed definitions
  as data and the feed's own reported counts; additionally
  ``reference_transport: True``); workflow execution engine
  (idx 916, as drafted — execution-request records and reported
  outcomes; the core workflow record is pinned unchanged).
- **Reference, re-judged from the drafted build-extension**
  (DECISION.md qualification 1; grounds in BATCH.md): proposal
  generation engine (idx 915 — generation is drafting; the core
  holds content as metadata only by a pinned invariant, so a
  generator in this substrate would fabricate text it cannot
  hold or be a generator in name only); segmentation engine
  (idx 917 — membership computation needs a contact universe,
  and this substrate holds counts and opaque references only, by
  the founding privacy design; there is nothing to derive
  membership over); email sending transport & deliverability
  (idx 918 — the entry names the transport itself; sending is
  execution against external networks, and the substrate's
  delivery-outcome records already hold the records side of
  delivery).

Access mapping: the core action set is fixed, so each extension
operation rides an existing core action, checked through the
core matrix before any state change or id allocation — AI
surface and proposal generation on ``propose`` (CLEATUS's AI
claim sits in its proposal-support sentence), agent definitions
and workflow execution on ``workflow``, discovery feeds on
``register``, intelligence and forecasts on ``evaluate``,
segmentation on ``segments``, send requests and transport
receipts on ``deliver``, handling rules and templates on
``campaigns``, handling records on ``suppress``, preferences on
``lists``, and every read on ``read``. Successful mutations are
recorded on the core audit log as ``ext_<operation>``; denied
attempts are the HTTP layer's responsibility in this group's
convention and are not recorded here. If an audit write fails,
the record insertion and its id roll back before the error
propagates (pinned by test): no extension record exists whose
audit entry does not.

Nothing here sends, fetches, searches, computes membership,
drafts text, executes a workflow or an agent, runs a model, or
collects anything. Records that report an external system's
figures store them verbatim as data and say so on their face.
"""

import threading

from .access import require
from .audit import actor_name
from .errors import NotFoundError, ValidationError
from .store import _contact_ref, _count, _optional_text, _text, _utc_now

HANDLING_TRIGGERS = ("bounced_outcome", "complaint_suppression")
HANDLING_RULE_ACTIONS = ("record_suppression", "flag_for_review",
                         "note_only")
HANDLING_ACTIONS = ("suppression_recorded", "suppression_released",
                    "reviewed_no_action")
PREFERENCE_KINDS = ("channel", "frequency", "topic")

_FORBIDDEN_KEY_PARTS = ("score", "grade", "rank", "rate", "email",
                        "body", "content_text", "text_body", "ssn",
                        "password", "secret")


def _check_data_keys(node, field):
    if isinstance(node, dict):
        for key, value in node.items():
            if not isinstance(key, str):
                raise ValidationError("%s keys must be strings" % field)
            for part in _FORBIDDEN_KEY_PARTS:
                if part in key.lower():
                    raise ValidationError(
                        "%s may not carry a %r key" % (field, part))
            _check_data_keys(value, field)
    elif isinstance(node, (list, tuple)):
        for value in node:
            _check_data_keys(value, field)


def _scalar_data(value, field):
    """Validate and copy caller-supplied definition data.

    Scalars (string / integer / boolean / None), lists, and dicts
    of scalars are held as data. Floats are rejected at the
    boundary (a recorded figure is exact or it is a label), and
    score-shaped keys are refused, per the build's no-score
    discipline.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        raise ValidationError("%s must not contain floats" % field)
    if isinstance(value, dict):
        _check_data_keys(value, field)
        return {key: _scalar_data(item, field)
                for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scalar_data(item, field) for item in value]
    raise ValidationError(
        "%s must be scalar data (strings, integers, booleans, "
        "lists, dicts)" % field)


def _handling_covered(covered_keys, key):
    """Handling-coverage seam: the single check the derived
    handling queue reads to decide whether a candidate item has
    been handled.

    A candidate (a bounced delivery, an active complaint
    suppression) is covered exactly when a handling record exists
    for its (list, contact, trigger) key. Pure function over
    recorded values; the queue derivation reads coverage only
    through this seam, so what counts as handled can never drift
    between the queue and its tests.
    """
    return key in covered_keys


def _derive_pending_handling(candidates, covered_keys):
    """The pending-handling derivation: the candidates with no
    covering handling record, in candidate order. Derived at
    read, never stored."""
    return [candidate for candidate in candidates
            if not _handling_covered(
                covered_keys,
                (candidate["list_id"], candidate["contact_ref"],
                 candidate["trigger"]))]


def _latest_preference(records):
    """Current-preference seam: of a (list, contact, kind) record
    sequence, the latest recorded record is the current one.
    Preferences are facts recorded over time; the current value
    is derived at read through this seam and stored nowhere."""
    return records[-1] if records else None


class MarketSalesExtensions:
    """GAPS-batch extension surface over a core MarketSalesStore."""

    def __init__(self, store):
        self._store = store
        self._lock = threading.Lock()
        self._ai_requests = {}
        self._ai_reports = {}
        self._ai_evaluations = {}
        self._agent_definitions = {}
        self._feeds = {}
        self._discovery_reports = {}
        self._intelligence_reports = {}
        self._forecasts = {}
        self._generation_requests = {}
        self._generation_reports = {}
        self._workflow_executions = {}
        self._workflow_execution_reports = {}
        self._segmentation_requests = {}
        self._segmentation_reports = {}
        self._send_requests = {}
        self._transport_receipts = {}
        self._handling_rules = {}
        self._handling_records = {}
        self._templates = {}
        self._preferences = {}
        self._counters = {}

    # -- internal helpers ---------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _unmint(self, prefix):
        self._counters[prefix] -= 1

    @staticmethod
    def _check_role(actor, action):
        if hasattr(actor, "role"):
            require(actor, action)

    def _insert(self, actor, table, prefix, record, action, details):
        """Insert a record and write its audit entry as one step:
        if the audit write fails, the insertion and the minted id
        roll back before the error propagates."""
        with self._lock:
            table[record["id"]] = record
            try:
                if self._store.audit is not None:
                    self._store.audit.record(actor, action,
                                             record["id"], details)
            except Exception:
                del table[record["id"]]
                self._unmint(prefix)
                raise
        return dict(record)

    # -- AI models / agents (idx 912 — reference, as drafted) ---------------

    def register_ai_request(self, actor, org_id, model_ref,
                            purpose_label, opportunity_id=None,
                            campaign_id=None):
        """Register a request to an external AI model or agent.

        A reference record: the model is the vendor's, named here
        only by an opaque ``model_ref``. There is deliberately no
        parameter that could carry a result — a request records
        intent, and outcomes arrive as report records. Nothing is
        run: ``inference_here`` is False on every record.
        """
        self._check_role(actor, "propose")
        _text(model_ref, "model_ref")
        _text(purpose_label, "purpose_label")
        self._store.get_organization(actor, org_id)
        if opportunity_id is not None:
            self._store.get_opportunity(actor, opportunity_id)
        if campaign_id is not None:
            self._store.get_campaign(actor, campaign_id)
        record = {
            "id": self._mint("aireq-"),
            "org_id": org_id,
            "model_ref": model_ref,
            "purpose_label": purpose_label,
            "opportunity_id": opportunity_id,
            "campaign_id": campaign_id,
            "reference_stub": True,
            "inference_here": False,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._ai_requests, "aireq-", record,
                            "ext_register_ai_request",
                            {"org_id": org_id, "model_ref": model_ref})

    def record_ai_report(self, actor, request_id, outcome_label,
                         result_ref=None):
        """Record an external model's reported outcome for a
        request. The outcome label is stored verbatim; the result
        itself is named only by an opaque ``result_ref`` and is
        never held here (``result_held_here`` False)."""
        self._check_role(actor, "propose")
        _text(outcome_label, "outcome_label")
        _optional_text(result_ref, "result_ref")
        if request_id not in self._ai_requests:
            raise NotFoundError("no such AI request: %r" % (request_id,))
        record = {
            "id": self._mint("air-"),
            "request_id": request_id,
            "outcome_label": outcome_label,
            "result_ref": result_ref,
            "result_held_here": False,
            "inference_here": False,
            "reference_stub": True,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._ai_reports, "air-", record,
                            "ext_record_ai_report",
                            {"request_id": request_id,
                             "outcome_label": outcome_label})

    def record_ai_evaluation(self, actor, request_id, figure,
                             figure_label=None):
        """Record an external model's evaluation figure exactly as
        reported — an integer or a verbatim label. Booleans and
        floats are rejected at the boundary, and nothing is
        computed from the figure (``computed_here`` False): the
        build's no-score discipline binds reported figures too."""
        self._check_role(actor, "propose")
        if isinstance(figure, bool) or isinstance(figure, float):
            raise ValidationError(
                "figure must be an integer or a verbatim label")
        if isinstance(figure, int):
            if figure < 0:
                raise ValidationError("figure must be zero or greater")
        elif isinstance(figure, str):
            _text(figure, "figure")
        else:
            raise ValidationError(
                "figure must be an integer or a verbatim label")
        _optional_text(figure_label, "figure_label")
        if request_id not in self._ai_requests:
            raise NotFoundError("no such AI request: %r" % (request_id,))
        record = {
            "id": self._mint("aieval-"),
            "request_id": request_id,
            "reported_figure": figure,
            "figure_label": figure_label,
            "computed_here": False,
            "reference_stub": True,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._ai_evaluations, "aieval-",
                            record, "ext_record_ai_evaluation",
                            {"request_id": request_id})

    def register_agent_definition(self, actor, org_id, label, steps):
        """Register an agent definition as data: an ordered list of
        action labels. A definition is a record, not a program —
        registering one runs nothing, and this surface has no
        execution entry point (``executed_here`` False)."""
        self._check_role(actor, "workflow")
        _text(label, "label")
        if not isinstance(steps, (list, tuple)) or not steps:
            raise ValidationError(
                "steps must be a non-empty list of action labels")
        normalized = []
        for index, step in enumerate(steps):
            _text(step, "steps[%d]" % index)
            normalized.append({"step": index + 1, "action_label": step})
        self._store.get_organization(actor, org_id)
        record = {
            "id": self._mint("agent-"),
            "org_id": org_id,
            "label": label,
            "steps": normalized,
            "executed_here": False,
            "reference_stub": True,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._agent_definitions, "agent-",
                            record, "ext_register_agent_definition",
                            {"org_id": org_id, "label": label})

    def list_ai_requests(self, actor, org_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._ai_requests.values()
                if org_id is None or r["org_id"] == org_id]

    def list_ai_reports(self, actor, request_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._ai_reports.values()
                if request_id is None or r["request_id"] == request_id]

    def list_ai_evaluations(self, actor, request_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._ai_evaluations.values()
                if request_id is None or r["request_id"] == request_id]

    def list_agent_definitions(self, actor, org_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._agent_definitions.values()
                if org_id is None or r["org_id"] == org_id]

    # -- discovery feeds & search engines (idx 913 — reference) -------------

    def register_discovery_feed(self, actor, org_id, label,
                                source_label, query_label=None):
        """Register a live discovery feed / contract-search source
        as a definition record. The feed itself — fetching,
        searching, polling external sources — is the vendor's
        transport; this record names it so its reports have
        something to hang off (``fetched_here`` and
        ``searched_here`` False, ``reference_transport`` True)."""
        self._check_role(actor, "register")
        _text(label, "label")
        _text(source_label, "source_label")
        _optional_text(query_label, "query_label")
        self._store.get_organization(actor, org_id)
        record = {
            "id": self._mint("feed-"),
            "org_id": org_id,
            "label": label,
            "source_label": source_label,
            "query_label": query_label,
            "active": True,
            "fetched_here": False,
            "searched_here": False,
            "reference_stub": True,
            "reference_transport": True,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._feeds, "feed-", record,
                            "ext_register_discovery_feed",
                            {"org_id": org_id, "label": label})

    def set_discovery_feed_active(self, actor, feed_id, active):
        """Record a feed definition's active flag. Toggling it
        fetches nothing; it is a recorded state, exactly as the
        core workflow registry's flag is."""
        self._check_role(actor, "register")
        if not isinstance(active, bool):
            raise ValidationError("active must be a boolean")
        with self._lock:
            feed = self._feeds.get(feed_id)
            if feed is None:
                raise NotFoundError(
                    "no such discovery feed: %r" % (feed_id,))
            feed["active"] = active
            result = dict(feed)
        if self._store.audit is not None:
            self._store.audit.record(
                actor, "ext_set_discovery_feed_active", feed_id,
                {"active": active})
        return result

    def record_discovery_report(self, actor, feed_id, reported_count,
                                reported_new_count=None,
                                period_label=None):
        """Record a feed's own reported yield for a period: counts
        the feed states about itself, stored as data. Recording a
        report registers no opportunity — opportunities enter the
        core only through the core's own registration, by a human
        who chose to track them."""
        self._check_role(actor, "register")
        count = _count(reported_count, "reported_count")
        new_count = None
        if reported_new_count is not None:
            new_count = _count(reported_new_count,
                               "reported_new_count")
        _optional_text(period_label, "period_label")
        if feed_id not in self._feeds:
            raise NotFoundError(
                "no such discovery feed: %r" % (feed_id,))
        record = {
            "id": self._mint("dscr-"),
            "feed_id": feed_id,
            "reported_count": count,
            "reported_new_count": new_count,
            "period_label": period_label,
            "fetched_here": False,
            "reference_stub": True,
            "reference_transport": True,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._discovery_reports, "dscr-",
                            record, "ext_record_discovery_report",
                            {"feed_id": feed_id})

    def list_discovery_feeds(self, actor, org_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._feeds.values()
                if org_id is None or r["org_id"] == org_id]

    def list_discovery_reports(self, actor, feed_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._discovery_reports.values()
                if feed_id is None or r["feed_id"] == feed_id]

    # -- market intelligence & forecasts (idx 914 — built) -------------------

    def record_intelligence_report(self, actor, org_id, subject_label,
                                   observation_label, source_ref,
                                   competitor_label=None):
        """Record a market-intelligence observation: an analyst's
        recorded note about a market subject (optionally a
        competitor), with the source named by reference. The
        observation is the analyst's work product recorded as
        data; this build gathers nothing and analyzes nothing —
        the derived side of this family is the market view's
        counts over the substrate's own records."""
        self._check_role(actor, "evaluate")
        _text(subject_label, "subject_label")
        _text(observation_label, "observation_label")
        _text(source_ref, "source_ref")
        _optional_text(competitor_label, "competitor_label")
        self._store.get_organization(actor, org_id)
        record = {
            "id": self._mint("intel-"),
            "org_id": org_id,
            "subject_label": subject_label,
            "observation_label": observation_label,
            "competitor_label": competitor_label,
            "source_ref": source_ref,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._intelligence_reports,
                            "intel-", record,
                            "ext_record_intelligence_report",
                            {"org_id": org_id,
                             "subject_label": subject_label})

    def record_forecast(self, actor, org_id, label, horizon_label,
                        reported_count, source_ref, basis_label=None):
        """Record a forecast exactly as its source states it: a
        label, a horizon label, and the source's own expected
        count, stored verbatim as data. No projection is computed
        here (``computed_here`` False) — a forecast record is a
        citation, not a computation."""
        self._check_role(actor, "evaluate")
        _text(label, "label")
        _text(horizon_label, "horizon_label")
        count = _count(reported_count, "reported_count")
        _text(source_ref, "source_ref")
        _optional_text(basis_label, "basis_label")
        self._store.get_organization(actor, org_id)
        record = {
            "id": self._mint("fcst-"),
            "org_id": org_id,
            "label": label,
            "horizon_label": horizon_label,
            "reported_count": count,
            "basis_label": basis_label,
            "source_ref": source_ref,
            "computed_here": False,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._forecasts, "fcst-", record,
                            "ext_record_forecast",
                            {"org_id": org_id, "label": label})

    def market_view(self, actor, org_id=None):
        """The market view: deterministic counts over the
        substrate's own recorded records, derived at read and
        stored nowhere. Counts only — no win rate, no share, no
        projection: the honest ceiling of this substrate, stated
        on the view itself as its method."""
        self._check_role(actor, "read")
        opportunities = self._store.list_opportunities(actor,
                                                       org_id=org_id)
        evaluations = self._store.list_evaluations(actor)
        pipeline = self._store.list_pipeline(actor)
        if org_id is not None:
            opp_ids = {o["id"] for o in opportunities}
            evaluations = [e for e in evaluations
                           if e["opportunity_id"] in opp_ids]
            pipeline = [p for p in pipeline
                        if p["opportunity_id"] in opp_ids]
        by_agency = {}
        for opportunity in opportunities:
            label = opportunity["agency_label"]
            by_agency[label] = by_agency.get(label, 0) + 1
        by_decision = {}
        for evaluation in evaluations:
            decision = evaluation["decision"]
            by_decision[decision] = by_decision.get(decision, 0) + 1
        by_stage = {}
        for entry in pipeline:
            stage = entry["stage"]
            by_stage[stage] = by_stage.get(stage, 0) + 1
        intelligence = [r for r in self._intelligence_reports.values()
                        if org_id is None or r["org_id"] == org_id]
        forecasts = [r for r in self._forecasts.values()
                     if org_id is None or r["org_id"] == org_id]
        return {
            "method": "deterministic_counts_over_recorded_records",
            "counts_only": True,
            "opportunities_total": len(opportunities),
            "opportunities_by_agency_label": by_agency,
            "evaluations_by_decision": by_decision,
            "pipeline_by_stage": by_stage,
            "intelligence_reports": len(intelligence),
            "forecasts_recorded": len(forecasts),
        }

    def list_intelligence_reports(self, actor, org_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._intelligence_reports.values()
                if org_id is None or r["org_id"] == org_id]

    def list_forecasts(self, actor, org_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._forecasts.values()
                if org_id is None or r["org_id"] == org_id]

    # -- proposal generation engine (idx 915 — reference, re-judged) ---------

    def request_proposal_generation(self, actor, opportunity_id,
                                    item_label, kind_label,
                                    request_label=None):
        """Register a generation request for one proposal content
        item. A reference record: drafting is the generator's
        work, and this build holds content as metadata only — the
        signature has no parameter that could carry drafted text,
        and ``drafted_here`` is False on every record."""
        self._check_role(actor, "propose")
        _text(item_label, "item_label")
        _text(kind_label, "kind_label")
        _optional_text(request_label, "request_label")
        self._store.get_opportunity(actor, opportunity_id)
        record = {
            "id": self._mint("genreq-"),
            "opportunity_id": opportunity_id,
            "item_label": item_label,
            "kind_label": kind_label,
            "request_label": request_label,
            "drafted_here": False,
            "reference_stub": True,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._generation_requests,
                            "genreq-", record,
                            "ext_request_proposal_generation",
                            {"opportunity_id": opportunity_id,
                             "item_label": item_label})

    def record_generation_report(self, actor, request_id,
                                 outcome_label,
                                 result_content_id=None):
        """Record a generator's reported outcome for a request.
        The outcome label is stored verbatim; a reported result is
        named by the id of an existing core content-version record
        for the same opportunity (existence enforced, the core
        record never modified) and is not held here."""
        self._check_role(actor, "propose")
        _text(outcome_label, "outcome_label")
        request = self._generation_requests.get(request_id)
        if request is None:
            raise NotFoundError(
                "no such generation request: %r" % (request_id,))
        if result_content_id is not None:
            versions = self._store.list_content(
                actor, opportunity_id=request["opportunity_id"])
            if result_content_id not in {v["id"] for v in versions}:
                raise NotFoundError(
                    "no such content version for this opportunity: "
                    "%r" % (result_content_id,))
        record = {
            "id": self._mint("genrep-"),
            "request_id": request_id,
            "outcome_label": outcome_label,
            "result_content_id": result_content_id,
            "result_held_here": False,
            "drafted_here": False,
            "reference_stub": True,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._generation_reports,
                            "genrep-", record,
                            "ext_record_generation_report",
                            {"request_id": request_id,
                             "outcome_label": outcome_label})

    def list_generation_requests(self, actor, opportunity_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._generation_requests.values()
                if opportunity_id is None
                or r["opportunity_id"] == opportunity_id]

    def list_generation_reports(self, actor, request_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._generation_reports.values()
                if request_id is None or r["request_id"] == request_id]

    # -- workflow execution engine (idx 916 — reference, as drafted) ---------

    def request_workflow_execution(self, actor, workflow_id,
                                   parameters=None):
        """Register an execution request against a core workflow
        record: the would-be parameters, held as validated scalar
        data. A request only — the registry's founding discipline
        stands, nothing executes, and the core workflow record is
        untouched (``executed_here`` False,
        ``state: recorded_request_only``)."""
        self._check_role(actor, "workflow")
        params = {}
        if parameters is not None:
            if not isinstance(parameters, dict):
                raise ValidationError("parameters must be a dict")
            params = _scalar_data(parameters, "parameters")
        workflows = self._store.list_workflows(actor)
        if workflow_id not in {w["id"] for w in workflows}:
            raise NotFoundError("no such workflow: %r" % (workflow_id,))
        record = {
            "id": self._mint("wexec-"),
            "workflow_id": workflow_id,
            "parameters": params,
            "state": "recorded_request_only",
            "executed_here": False,
            "reference_stub": True,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._workflow_executions,
                            "wexec-", record,
                            "ext_request_workflow_execution",
                            {"workflow_id": workflow_id})

    def record_workflow_execution_report(self, actor, request_id,
                                         outcome_label):
        """Record an external executor's reported outcome for an
        execution request, the label stored verbatim. Recording a
        report executes nothing either."""
        self._check_role(actor, "workflow")
        _text(outcome_label, "outcome_label")
        if request_id not in self._workflow_executions:
            raise NotFoundError(
                "no such workflow execution request: %r"
                % (request_id,))
        record = {
            "id": self._mint("wexecr-"),
            "request_id": request_id,
            "outcome_label": outcome_label,
            "executed_here": False,
            "reference_stub": True,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._workflow_execution_reports,
                            "wexecr-", record,
                            "ext_record_workflow_execution_report",
                            {"request_id": request_id,
                             "outcome_label": outcome_label})

    def list_workflow_execution_requests(self, actor, workflow_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._workflow_executions.values()
                if workflow_id is None
                or r["workflow_id"] == workflow_id]

    def list_workflow_execution_reports(self, actor, request_id=None):
        self._check_role(actor, "read")
        return [dict(r)
                for r in self._workflow_execution_reports.values()
                if request_id is None or r["request_id"] == request_id]

    # -- segmentation engine (idx 917 — reference, re-judged) ----------------

    def request_segmentation(self, actor, segment_id, criteria):
        """Register a membership-computation request against a
        core segment record: the criteria, held as validated data.
        A reference record — membership computation needs a
        contact universe, and this substrate holds counts and
        opaque references only, so there is nothing here to
        compute membership over. The core segment record is
        untouched (``computed_here`` False)."""
        self._check_role(actor, "segments")
        if not isinstance(criteria, (dict, list)):
            raise ValidationError(
                "criteria must be definition data (dict or list)")
        checked = _scalar_data(criteria, "criteria")
        segments = self._store.list_segments(actor)
        if segment_id not in {s["id"] for s in segments}:
            raise NotFoundError("no such segment: %r" % (segment_id,))
        record = {
            "id": self._mint("segreq-"),
            "segment_id": segment_id,
            "criteria": checked,
            "state": "recorded_request_only",
            "computed_here": False,
            "reference_stub": True,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._segmentation_requests,
                            "segreq-", record,
                            "ext_request_segmentation",
                            {"segment_id": segment_id})

    def record_segmentation_report(self, actor, request_id,
                                   reported_member_count):
        """Record a segmentation engine's reported membership
        count for a computation request, stored as data. The
        count is the engine's statement about its own universe;
        no membership is computed or held here."""
        self._check_role(actor, "segments")
        count = _count(reported_member_count, "reported_member_count")
        if request_id not in self._segmentation_requests:
            raise NotFoundError(
                "no such segmentation request: %r" % (request_id,))
        record = {
            "id": self._mint("segrep-"),
            "request_id": request_id,
            "reported_member_count": count,
            "computed_here": False,
            "reference_stub": True,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._segmentation_reports,
                            "segrep-", record,
                            "ext_record_segmentation_report",
                            {"request_id": request_id})

    def list_segmentation_requests(self, actor, segment_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._segmentation_requests.values()
                if segment_id is None or r["segment_id"] == segment_id]

    def list_segmentation_reports(self, actor, request_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._segmentation_reports.values()
                if request_id is None or r["request_id"] == request_id]

    # -- email transport & deliverability (idx 918 — reference, re-judged) ---

    def request_send(self, actor, campaign_id, note_label=None):
        """Register a send request for a core campaign. A
        reference record: the transport that would send is an
        external system; this record states that a send was
        requested and nothing more (``sent_here`` and
        ``transmitted_here`` False, ``reference_transport``
        True). No core delivery record is created — delivery
        outcomes enter the core only as facts recorded after the
        fact."""
        self._check_role(actor, "deliver")
        _optional_text(note_label, "note_label")
        self._store.get_campaign(actor, campaign_id)
        record = {
            "id": self._mint("send-"),
            "campaign_id": campaign_id,
            "note_label": note_label,
            "state": "recorded_request_only",
            "sent_here": False,
            "transmitted_here": False,
            "reference_stub": True,
            "reference_transport": True,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._send_requests, "send-",
                            record, "ext_request_send",
                            {"campaign_id": campaign_id})

    def record_transport_receipt(self, actor, send_request_id,
                                 reported_delivered, reported_bounced,
                                 reported_deferred, period_label=None):
        """Record a transport's delivery receipt for a send
        request: the transport's own reported outcome counts,
        stored as data. A receipt is not a delivery record — it
        creates no core delivery, engagement, or suppression
        record, and the campaign's derived status does not move."""
        self._check_role(actor, "deliver")
        delivered = _count(reported_delivered, "reported_delivered")
        bounced = _count(reported_bounced, "reported_bounced")
        deferred = _count(reported_deferred, "reported_deferred")
        _optional_text(period_label, "period_label")
        if send_request_id not in self._send_requests:
            raise NotFoundError(
                "no such send request: %r" % (send_request_id,))
        record = {
            "id": self._mint("rcpt-"),
            "send_request_id": send_request_id,
            "reported_delivered": delivered,
            "reported_bounced": bounced,
            "reported_deferred": deferred,
            "period_label": period_label,
            "transmitted_here": False,
            "reference_stub": True,
            "reference_transport": True,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._transport_receipts, "rcpt-",
                            record, "ext_record_transport_receipt",
                            {"send_request_id": send_request_id})

    def list_send_requests(self, actor, campaign_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._send_requests.values()
                if campaign_id is None
                or r["campaign_id"] == campaign_id]

    def list_transport_receipts(self, actor, send_request_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._transport_receipts.values()
                if send_request_id is None
                or r["send_request_id"] == send_request_id]

    # -- handling, templates, preferences (idx 919 — built) ------------------

    def register_handling_rule(self, actor, org_id, trigger,
                               action_label):
        """Register a bounce/complaint handling rule as a
        definition held as data: when ``trigger`` occurs, the
        handling ``action_label`` is what an operator records.
        Registering a rule applies it to nothing — definitions
        never execute in this substrate (``applied_here``
        False); the queue below is derived, and handling itself
        is recorded by operators, one decision at a time."""
        self._check_role(actor, "campaigns")
        if trigger not in HANDLING_TRIGGERS:
            raise ValidationError(
                "trigger must be one of %r" % (HANDLING_TRIGGERS,))
        if action_label not in HANDLING_RULE_ACTIONS:
            raise ValidationError(
                "action_label must be one of %r"
                % (HANDLING_RULE_ACTIONS,))
        self._store.get_organization(actor, org_id)
        record = {
            "id": self._mint("hrule-"),
            "org_id": org_id,
            "trigger": trigger,
            "action_label": action_label,
            "active": True,
            "applied_here": False,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._handling_rules, "hrule-",
                            record, "ext_register_handling_rule",
                            {"org_id": org_id, "trigger": trigger})

    def set_handling_rule_active(self, actor, rule_id, active):
        """Record a handling rule's active flag. Toggling it
        handles nothing; it is a recorded state."""
        self._check_role(actor, "campaigns")
        if not isinstance(active, bool):
            raise ValidationError("active must be a boolean")
        with self._lock:
            rule = self._handling_rules.get(rule_id)
            if rule is None:
                raise NotFoundError(
                    "no such handling rule: %r" % (rule_id,))
            rule["active"] = active
            result = dict(rule)
        if self._store.audit is not None:
            self._store.audit.record(
                actor, "ext_set_handling_rule_active", rule_id,
                {"active": active})
        return result

    def record_handling(self, actor, list_id, contact_ref, trigger,
                        action_label, campaign_id=None):
        """Record one handling decision for one contact on one
        list: the trigger that raised it and the action an
        operator took, from fixed vocabularies. A decision record
        only — it creates, releases, and modifies no core
        suppression (an operator performs that through the core,
        and this record is the handling trail for it); what it
        changes is the derived queue, which reads coverage through
        :func:`_handling_covered`."""
        self._check_role(actor, "suppress")
        _contact_ref(contact_ref)
        if trigger not in HANDLING_TRIGGERS:
            raise ValidationError(
                "trigger must be one of %r" % (HANDLING_TRIGGERS,))
        if action_label not in HANDLING_ACTIONS:
            raise ValidationError(
                "action_label must be one of %r"
                % (HANDLING_ACTIONS,))
        self._store.get_contact_list(actor, list_id)
        if campaign_id is not None:
            campaign = self._store.get_campaign(actor, campaign_id)
            if campaign["list_id"] != list_id:
                raise ValidationError(
                    "campaign %r does not use list %r"
                    % (campaign_id, list_id))
        record = {
            "id": self._mint("hndl-"),
            "list_id": list_id,
            "campaign_id": campaign_id,
            "contact_ref": contact_ref,
            "trigger": trigger,
            "action_label": action_label,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._handling_records, "hndl-",
                            record, "ext_record_handling",
                            {"list_id": list_id, "trigger": trigger})

    def pending_handling(self, actor, org_id=None):
        """The handling queue, derived at read and stored
        nowhere: every bounced delivery outcome and every active
        complaint suppression that no handling record covers.
        Derived from core records through
        :func:`_derive_pending_handling`, so the queue can never
        disagree with the records it is derived from."""
        self._check_role(actor, "read")
        campaigns = {c["id"]: c
                     for c in self._store.list_campaigns(actor)}
        list_org = {}
        candidates = []
        seen = set()
        for delivery in self._store.list_deliveries(actor):
            if delivery["outcome"] != "bounced":
                continue
            campaign = campaigns.get(delivery["campaign_id"])
            if campaign is None:
                continue
            if org_id is not None and campaign["org_id"] != org_id:
                continue
            key = (campaign["list_id"], delivery["contact_ref"],
                   "bounced_outcome", campaign["id"])
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                "campaign_id": campaign["id"],
                "list_id": campaign["list_id"],
                "contact_ref": delivery["contact_ref"],
                "trigger": "bounced_outcome",
                "source_delivery_id": delivery["id"],
                "source_suppression_id": None,
            })
        for suppression in self._store.list_suppressions(
                actor, state="active"):
            if suppression["reason"] != "complaint":
                continue
            if org_id is not None:
                if suppression["list_id"] not in list_org:
                    contact_list = self._store.get_contact_list(
                        actor, suppression["list_id"])
                    list_org[suppression["list_id"]] = \
                        contact_list["org_id"]
                if list_org[suppression["list_id"]] != org_id:
                    continue
            key = (suppression["list_id"], suppression["contact_ref"],
                   "complaint_suppression", None)
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                "campaign_id": None,
                "list_id": suppression["list_id"],
                "contact_ref": suppression["contact_ref"],
                "trigger": "complaint_suppression",
                "source_delivery_id": None,
                "source_suppression_id": suppression["id"],
            })
        covered = {(h["list_id"], h["contact_ref"], h["trigger"])
                   for h in self._handling_records.values()}
        return _derive_pending_handling(candidates, covered)

    def list_handling_rules(self, actor, org_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._handling_rules.values()
                if org_id is None or r["org_id"] == org_id]

    def list_handling_records(self, actor, list_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._handling_records.values()
                if list_id is None or r["list_id"] == list_id]

    def register_template(self, actor, org_id, label, kind_label,
                          version, size_bytes):
        """Record one version of a campaign template: metadata
        only — a label, a kind label, a version, a recorded size
        in bytes — in exactly the core proposal-content records'
        form. The template itself is never accepted or stored;
        there is no field on this shape that could hold it, and
        ``version`` is unique per (organization, label)."""
        self._check_role(actor, "campaigns")
        _text(label, "label")
        _text(kind_label, "kind_label")
        if isinstance(version, bool) or not isinstance(version, int):
            raise ValidationError("version must be an integer")
        if version < 1:
            raise ValidationError("version must be at least 1")
        size = _count(size_bytes, "size_bytes")
        self._store.get_organization(actor, org_id)
        for existing in self._templates.values():
            if (existing["org_id"] == org_id
                    and existing["label"] == label
                    and existing["version"] == version):
                raise ValidationError(
                    "template %r already has a version %d for "
                    "this organization" % (label, version))
        record = {
            "id": self._mint("tmpl-"),
            "org_id": org_id,
            "label": label,
            "kind_label": kind_label,
            "version": version,
            "size_bytes": size,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._templates, "tmpl-",
                            record, "ext_register_template",
                            {"org_id": org_id, "label": label,
                             "version": version})

    def list_templates(self, actor, org_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._templates.values()
                if org_id is None or r["org_id"] == org_id]

    def record_preference(self, actor, list_id, contact_ref, kind,
                          value_label):
        """Record one contact preference on one list: a kind from
        a fixed vocabulary (channel / frequency / topic) and the
        preference value as a verbatim label, keyed by the same
        opaque contact reference the core uses — no field can hold
        an address or a name. Preferences are recorded over time;
        the current value is derived, never updated in place."""
        self._check_role(actor, "lists")
        _contact_ref(contact_ref)
        if kind not in PREFERENCE_KINDS:
            raise ValidationError(
                "kind must be one of %r" % (PREFERENCE_KINDS,))
        _text(value_label, "value_label")
        self._store.get_contact_list(actor, list_id)
        record = {
            "id": self._mint("pref-"),
            "list_id": list_id,
            "contact_ref": contact_ref,
            "kind": kind,
            "value_label": value_label,
            "created_by": actor_name(actor),
            "created_utc": _utc_now().isoformat(),
        }
        return self._insert(actor, self._preferences, "pref-",
                            record, "ext_record_preference",
                            {"list_id": list_id, "kind": kind})

    def current_preferences(self, actor, list_id, contact_ref):
        """A contact's current preferences on a list, derived at
        read through :func:`_latest_preference`: for each kind,
        the latest recorded value. Kinds never recorded are
        absent — absence is stated, never defaulted."""
        self._check_role(actor, "read")
        _contact_ref(contact_ref)
        self._store.get_contact_list(actor, list_id)
        by_kind = {}
        for record in self._preferences.values():
            if (record["list_id"] == list_id
                    and record["contact_ref"] == contact_ref):
                by_kind.setdefault(record["kind"], []).append(record)
        result = {}
        for kind, records in by_kind.items():
            latest = _latest_preference(records)
            result[kind] = latest["value_label"]
        return result

    def list_preferences(self, actor, list_id=None):
        self._check_role(actor, "read")
        return [dict(r) for r in self._preferences.values()
                if list_id is None or r["list_id"] == list_id]

    # -- summary ---------------------------------------------------------------

    def extension_summary(self, actor):
        """Counts of the extension record kinds, computed on read.
        Counts only, like the core summary."""
        self._check_role(actor, "read")
        return {
            "ai_requests": len(self._ai_requests),
            "ai_reports": len(self._ai_reports),
            "ai_evaluations": len(self._ai_evaluations),
            "agent_definitions": len(self._agent_definitions),
            "discovery_feeds": len(self._feeds),
            "discovery_reports": len(self._discovery_reports),
            "intelligence_reports": len(self._intelligence_reports),
            "forecasts": len(self._forecasts),
            "generation_requests": len(self._generation_requests),
            "generation_reports": len(self._generation_reports),
            "workflow_execution_requests":
                len(self._workflow_executions),
            "workflow_execution_reports":
                len(self._workflow_execution_reports),
            "segmentation_requests": len(self._segmentation_requests),
            "segmentation_reports": len(self._segmentation_reports),
            "send_requests": len(self._send_requests),
            "transport_receipts": len(self._transport_receipts),
            "handling_rules": len(self._handling_rules),
            "handling_records": len(self._handling_records),
            "templates": len(self._templates),
            "preferences": len(self._preferences),
        }
