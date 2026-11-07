"""Final GAPS batch extensions for Energy Management L1
(Remainder Singleton 57).

Clean-room, standard-library-only extensions for the 10 open
entries of the "Remainder Singleton 57 — Energy Management L1"
section of GAPS.md (see ``BATCH.md`` in the group directory for
the per-entry disposition). This module is a wrapper around
:class:`EnergyStore`; every core module is untouched and
byte-identical to the shipped build.

**The founding discipline binds absolutely, here as in the
core:** this build holds records about energy procurement. It
conducts no auction, evaluates no trigger, delivers nothing,
produces no analysis, performs no advice, renders nothing,
executes no contract, and moves no money. Every entity shape in
this module carries metadata and opaque caller-supplied
references only, plus figures and outcomes stored exactly as
reported by the external systems and people who actually did
the work. Methods accept only their named parameters, so a
caller cannot smuggle an unlisted field into a record (pinned
by tests: an unexpected keyword raises ``TypeError``).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — session, definition, and outcome records
over the group's OWN records (core records and extension
records), plus deterministic derivations at read:

- Auction execution is session/run records referencing a core
  auction, with outcomes stored verbatim as reported. The core
  auction's outcome stays the core's own derivation from its
  bid records; a run record and its reports are pinned to leave
  that derivation untouched.
- Alert delivery is ``reference_transport`` records plus
  verbatim delivery reports; nothing is sent here.
- Market intelligence is analysis records holding conclusions
  as reported data — an analyst label, an outlook label, and
  figures held as decimal strings. No analysis is computed
  here, and no notification is created here: market-update
  notifications stay booked once, under the core alert records.
- The advisory practice is engagement-bound session records
  with verbatim reported recommendations; the fork's people
  perform the practice, this build records it.
- Charts and dashboards are chart *definition* records (whose
  series references resolve to core price-observation records)
  and dashboard configuration records; nothing is drawn here.
- Supply contracts are contract records over opaque customer
  and provider references, with the contract value and the
  lifecycle state derived at read and never stored.
- Settlement is settlement-request records plus verbatim
  outcome reports, capped by the linked contract's recorded
  amount; no money moves here.
- Stub-engine entries ship as labeled reference implementations:
  every record carries ``reference_stub: True`` and state
  ``recorded_reference_only``. Price triggers are definitions
  held as data plus verbatim reported evaluations (alert
  records stay Core — an evaluation creates none), the identity
  entry follows PLATFORM-LAYER.md decision 1 (IA-2 stays with
  the embedding organization; ``identity_provider: False``), and
  energy data integrations are feed records plus sync receipts
  holding counts exactly as reported — no feed data is held in
  any shape.

Doctrines carried from the core: derived-never-stored for every
computed value (delivery current state, contract value and
lifecycle state, settlement committed/remaining amounts, chart
series counts and latest price, all summaries); money and
prices are integer cents, with booleans and floats rejected at
the boundary; append-only audit on the core store's log with
``ext_``-prefixed actions for every successful mutation, and
denied write attempts recorded with a ``:denied`` suffix; RBAC
via :mod:`energy.access` with the core's existing actions,
enforced before any state change or id allocation, so a failed
operation consumes no id and changes nothing.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

RUN_OUTCOME_LABELS = (
    "reported_cleared",
    "reported_no_sale",
    "reported_suspended",
)
DELIVERY_REPORT_LABELS = (
    "reported_delivered",
    "reported_bounced",
    "reported_failed",
)
OUTLOOK_LABELS = ("rising", "falling", "stable")
CHART_KINDS = ("line", "bar", "area")
CONTRACT_EVENT_LABELS = (
    "recorded_amended",
    "recorded_terminated",
    "recorded_renewed",
)
SETTLEMENT_REPORT_LABELS = (
    "reported_paid",
    "reported_partial",
    "reported_failed",
)
TRIGGER_CONDITIONS = ("crosses_above", "crosses_below")
TRIGGER_EVALUATION_LABELS = ("reported_fired", "reported_not_fired")
FEED_KINDS = ("meter", "market_price", "supplier")
CONTRACT_STATES = ("pending", "active", "expired", "terminated")

_REFERENCE_STATE = "recorded_reference_only"
_FIGURE_RE = re.compile(r"^-?\d+(\.\d+)?$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _parse_moment(value, field):
    """Parse an ISO date or datetime into an aware datetime
    (mirrors the core store's moment semantics)."""
    if isinstance(value, datetime):
        moment = value
    elif isinstance(value, str):
        text = value.strip()
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
                moment = datetime.strptime(text, "%Y-%m-%d")
            else:
                moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            raise ValidationError(
                "%s is not an ISO date or datetime: %r" % (field, value))
    else:
        raise ValidationError("%s must be an ISO date or datetime string" % field)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _optional_text(value, what):
    if value is None:
        return None
    return _non_empty(value, what)


def _count(value, what):
    """A non-negative integer count; booleans and floats rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be a non-negative integer" % (what,))
    if value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


def _positive_cents(value, what):
    """A positive integer amount of cents; booleans and floats
    rejected, per the house money discipline."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents" % (what,))
    if value <= 0:
        raise ValidationError("%s must be positive" % (what,))
    return value


def _positive_units(value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError("%s must be a positive integer" % (what,))
    return value


def _check_settlement_cap(contract_value_cents, committed_cents, amount_cents):
    """Enforce the settlement cap for one settlement request.

    ``contract_value_cents`` is the linked contract's derived
    recorded amount (quantity x price per unit); ``committed_cents``
    is the total of this surface's outstanding settlement requests
    against the same contract (a request whose latest outcome
    report is ``reported_failed`` no longer counts). A request
    that would push the committed total even one cent over the
    contract's recorded amount is rejected whole. This is the
    negative control's target.
    """
    if committed_cents + amount_cents > contract_value_cents:
        raise ValidationError(
            "settlement request exceeds the contract's recorded amount: "
            "contract value %d, committed %d, requested %d"
            % (contract_value_cents, committed_cents, amount_cents)
        )
    return True


class EnergyExtensions:
    """Extension surface wrapping one :class:`EnergyStore`."""

    def __init__(self, store):
        self.store = store
        self._auction_runs = {}
        self._auction_run_reports = {}
        self._deliveries = {}
        self._delivery_reports = {}
        self._analyses = {}
        self._advisory_sessions = {}
        self._recommendations = {}
        self._charts = {}
        self._dashboards = {}
        self._contracts = {}
        self._contract_events = {}
        self._settlements = {}
        self._settlement_reports = {}
        self._trigger_definitions = {}
        self._trigger_evaluations = {}
        self._identity_references = {}
        self._feeds = {}
        self._feed_receipts = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    def _guard(self, actor, rbac_action, audit_action):
        """Enforce a write permission before any state change.

        Mirrors the core convention (a User-like actor is checked
        via :func:`energy.access.require`; a plain string carries
        identity but no role). A denied attempt is recorded on the
        audit log with a ``:denied`` suffix before the error
        propagates; a missing actor is denied outright.
        """
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (rbac_action,))
        if hasattr(actor, "role"):
            try:
                require(actor, rbac_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": rbac_action})
                raise

    @staticmethod
    def _maybe_require(actor, rbac_action):
        if actor is not None and hasattr(actor, "role"):
            require(actor, rbac_action)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _core_alert(self, actor, alert_id):
        for alert in self.store.list_alerts(actor):
            if alert["id"] == alert_id:
                return alert
        raise NotFoundError("alert not found: %r" % (alert_id,))

    def _core_subscription(self, actor, subscription_id):
        for subscription in self.store.list_subscriptions(actor):
            if subscription["id"] == subscription_id:
                return subscription
        raise NotFoundError("subscription not found: %r" % (subscription_id,))

    # -- auction execution (entry 691) ----------------------------------

    def record_auction_run(self, actor, auction_id, session_ref):
        """Record an auction execution session run against a core
        auction. Action: conduct. The run is a record of a session
        the external platform conducted; ``conducted_here`` is
        False and recording it changes no core record."""
        self._guard(actor, "conduct", "ext_auction_run_create")
        _non_empty(session_ref, "session_ref")
        self.store.get_auction(actor, auction_id)
        with self._lock:
            for existing in self._auction_runs.values():
                if existing["session_ref"] == session_ref:
                    raise ValidationError(
                        "session_ref already exists: %r" % (session_ref,))
            run = {
                "id": self._next_id("arun-"),
                "auction_id": auction_id,
                "session_ref": session_ref,
                "conducted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._auction_runs[run["id"]] = run
        self._audit(actor, "ext_auction_run_create", run["id"],
                    {"auction_id": auction_id})
        return copy.deepcopy(run)

    def record_auction_run_report(self, actor, run_id, outcome_label,
                                  reported_winner_ref=None):
        """Record the outcome of an auction run exactly as the
        conducting platform reported it. Action: conduct. The
        reported winner reference is held verbatim as reported
        data; it is not the core outcome and changes nothing in
        the core — the core outcome remains the core's derivation
        from its bid records."""
        self._guard(actor, "conduct", "ext_auction_report_create")
        if outcome_label not in RUN_OUTCOME_LABELS:
            raise ValidationError(
                "unknown run outcome label: %r" % (outcome_label,))
        _optional_text(reported_winner_ref, "reported_winner_ref")
        with self._lock:
            self._get(self._auction_runs, run_id, "auction run")
            report = {
                "id": self._next_id("arpt-"),
                "run_id": run_id,
                "outcome_label": outcome_label,
                "reported_winner_ref": reported_winner_ref,
                "conducted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._auction_run_reports[report["id"]] = report
        self._audit(actor, "ext_auction_report_create", report["id"],
                    {"run_id": run_id})
        return copy.deepcopy(report)

    def get_auction_run(self, actor, run_id):
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._auction_runs, run_id,
                                       "auction run"))

    def list_auction_runs(self, actor, auction_id=None):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._auction_runs.values()
            if auction_id is None or r["auction_id"] == auction_id
        ]

    def list_auction_run_reports(self, actor, run_id=None):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._auction_run_reports.values()
            if run_id is None or r["run_id"] == run_id
        ]

    def auction_execution_view(self, actor, run_id, now=None):
        """A run record, its reported outcomes, and the core
        auction's own derived outcome side by side — the core
        outcome is computed by the core store at read, never by
        the run or its reports."""
        self._maybe_require(actor, "read")
        run = self._get(self._auction_runs, run_id, "auction run")
        view = copy.deepcopy(run)
        view["reports"] = self.list_auction_run_reports(actor, run_id)
        view["core_outcome"] = self.store.auction_outcome(
            actor, run["auction_id"], now=now)
        return view

    # -- alert delivery transport (entry 693) ----------------------------

    def record_delivery(self, actor, alert_id, channel_ref):
        """Record a delivery of a core alert over an external
        transport. Action: alert. ``reference_transport`` is True
        and ``delivered_here`` is False: the transport is the
        embedding organization's, and what is recorded here is
        the delivery record. The customer is taken from the core
        alert record itself."""
        self._guard(actor, "alert", "ext_delivery_create")
        _non_empty(channel_ref, "channel_ref")
        alert = self._core_alert(actor, alert_id)
        with self._lock:
            delivery = {
                "id": self._next_id("dmsg-"),
                "alert_id": alert_id,
                "customer_id": alert["customer_id"],
                "channel_ref": channel_ref,
                "reference_transport": True,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._deliveries[delivery["id"]] = delivery
        self._audit(actor, "ext_delivery_create", delivery["id"],
                    {"alert_id": alert_id})
        return copy.deepcopy(delivery)

    def record_delivery_report(self, actor, delivery_id, report_label):
        """Record a delivery outcome exactly as the transport
        reported it. Action: alert."""
        self._guard(actor, "alert", "ext_delivery_report_create")
        if report_label not in DELIVERY_REPORT_LABELS:
            raise ValidationError(
                "unknown delivery report label: %r" % (report_label,))
        with self._lock:
            self._get(self._deliveries, delivery_id, "delivery")
            report = {
                "id": self._next_id("drpt-"),
                "delivery_id": delivery_id,
                "report_label": report_label,
                "reference_transport": True,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._delivery_reports[report["id"]] = report
        self._audit(actor, "ext_delivery_report_create", report["id"],
                    {"delivery_id": delivery_id})
        return copy.deepcopy(report)

    def get_delivery(self, actor, delivery_id):
        """The stored delivery record — it carries no state key;
        the current state exists only in :meth:`delivery_view`."""
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._deliveries, delivery_id,
                                       "delivery"))

    def list_deliveries(self, actor, alert_id=None):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(d) for d in self._deliveries.values()
            if alert_id is None or d["alert_id"] == alert_id
        ]

    def list_delivery_reports(self, actor, delivery_id=None):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._delivery_reports.values()
            if delivery_id is None or r["delivery_id"] == delivery_id
        ]

    @staticmethod
    def _current_delivery_label(reports):
        """Delivery current-state seam: the latest recorded report
        label wins; with no reports the state is ``recorded``.
        Derived at read, never stored."""
        if not reports:
            return "recorded"
        return reports[-1]["report_label"]

    def delivery_view(self, actor, delivery_id):
        """The delivery record plus its reports and the current
        state derived at read from the latest report."""
        self._maybe_require(actor, "read")
        delivery = self._get(self._deliveries, delivery_id, "delivery")
        reports = self.list_delivery_reports(actor, delivery_id)
        view = copy.deepcopy(delivery)
        view["reports"] = reports
        view["report_count"] = len(reports)
        view["current_state"] = self._current_delivery_label(reports)
        return view

    # -- market intelligence (entry 694) ---------------------------------

    def record_analysis(self, actor, customer_id, topic_ref,
                        analyst_label, outlook_label, figures,
                        engagement_id=None):
        """Record a market analysis exactly as the producing
        analyst reported it. Action: advise. Conclusions are held
        as reported data — an analyst label, an outlook label,
        and figures as decimal strings; ``produced_here`` is
        False and no analysis is computed here. No notification
        is created: market-update notifications stay booked once,
        under the core alert records. An optional engagement
        reference must name a core engagement of kind
        ``market_intelligence`` for the same customer."""
        self._guard(actor, "advise", "ext_analysis_create")
        _non_empty(topic_ref, "topic_ref")
        _non_empty(analyst_label, "analyst_label")
        if outlook_label not in OUTLOOK_LABELS:
            raise ValidationError(
                "unknown outlook label: %r" % (outlook_label,))
        figures = self._check_figures(figures)
        self.store.get_customer(actor, customer_id)
        if engagement_id is not None:
            engagement = self.store.get_engagement(actor, engagement_id)
            if engagement["kind"] != "market_intelligence":
                raise ValidationError(
                    "engagement %s is of kind %r, not 'market_intelligence'"
                    % (engagement_id, engagement["kind"]))
            if engagement["customer_id"] != customer_id:
                raise ValidationError(
                    "engagement %s does not belong to customer %s"
                    % (engagement_id, customer_id))
        with self._lock:
            analysis = {
                "id": self._next_id("mint-"),
                "customer_id": customer_id,
                "engagement_id": engagement_id,
                "topic_ref": topic_ref,
                "analyst_label": analyst_label,
                "outlook_label": outlook_label,
                "figures": figures,
                "produced_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._analyses[analysis["id"]] = analysis
        self._audit(actor, "ext_analysis_create", analysis["id"],
                    {"customer_id": customer_id})
        return copy.deepcopy(analysis)

    @staticmethod
    def _check_figures(figures):
        """Figures are reported data: a list of {label, value_text}
        where value_text is a decimal held as a string. Numbers
        (int/float) are refused — a figure enters this build only
        as the text the analyst reported."""
        if not isinstance(figures, (list, tuple)) or not figures:
            raise ValidationError("figures must be a non-empty list")
        checked = []
        for figure in figures:
            if not isinstance(figure, dict) \
                    or set(figure.keys()) != {"label", "value_text"}:
                raise ValidationError(
                    "each figure must be a dict with exactly the keys "
                    "'label' and 'value_text'")
            _non_empty(figure["label"], "figure label")
            value = figure["value_text"]
            if not isinstance(value, str) or not _FIGURE_RE.match(value):
                raise ValidationError(
                    "figure value_text must be a decimal held as a string: "
                    "%r" % (value,))
            checked.append({"label": figure["label"], "value_text": value})
        return checked

    def get_analysis(self, actor, analysis_id):
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._analyses, analysis_id,
                                       "analysis"))

    def list_analyses(self, actor, customer_id=None):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(a) for a in self._analyses.values()
            if customer_id is None or a["customer_id"] == customer_id
        ]

    def market_intelligence_summary(self, actor):
        """Counts of analysis records by outlook label, computed
        on read — counts of reported conclusions, never a
        computed analysis."""
        self._maybe_require(actor, "read")
        by_outlook = {label: 0 for label in OUTLOOK_LABELS}
        for analysis in self._analyses.values():
            by_outlook[analysis["outlook_label"]] += 1
        return {"analyses": len(self._analyses),
                "analyses_by_outlook": by_outlook}

    # -- advisory practice (entry 695) -------------------------------------

    def record_advisory_session(self, actor, engagement_id, session_ref):
        """Record an advisory session held under a core engagement.
        Action: advise. The fork's people perform the practice;
        ``performed_here`` is False and recording the session
        changes no core record."""
        self._guard(actor, "advise", "ext_advisory_session_create")
        _non_empty(session_ref, "session_ref")
        self.store.get_engagement(actor, engagement_id)
        with self._lock:
            for existing in self._advisory_sessions.values():
                if existing["session_ref"] == session_ref:
                    raise ValidationError(
                        "session_ref already exists: %r" % (session_ref,))
            session = {
                "id": self._next_id("ases-"),
                "engagement_id": engagement_id,
                "session_ref": session_ref,
                "performed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._advisory_sessions[session["id"]] = session
        self._audit(actor, "ext_advisory_session_create", session["id"],
                    {"engagement_id": engagement_id})
        return copy.deepcopy(session)

    def record_recommendation(self, actor, session_id, recommendation_label):
        """Record a recommendation exactly as the advising people
        reported it. Action: advise. The label is held verbatim
        as reported data; no advice is generated here."""
        self._guard(actor, "advise", "ext_recommendation_create")
        _non_empty(recommendation_label, "recommendation_label")
        with self._lock:
            self._get(self._advisory_sessions, session_id,
                      "advisory session")
            recommendation = {
                "id": self._next_id("arec-"),
                "session_id": session_id,
                "recommendation_label": recommendation_label,
                "performed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._recommendations[recommendation["id"]] = recommendation
        self._audit(actor, "ext_recommendation_create", recommendation["id"],
                    {"session_id": session_id})
        return copy.deepcopy(recommendation)

    def get_advisory_session(self, actor, session_id):
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._advisory_sessions, session_id,
                                       "advisory session"))

    def list_advisory_sessions(self, actor, engagement_id=None):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(s) for s in self._advisory_sessions.values()
            if engagement_id is None or s["engagement_id"] == engagement_id
        ]

    def list_recommendations(self, actor, session_id=None):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._recommendations.values()
            if session_id is None or r["session_id"] == session_id
        ]

    # -- price charts & dashboards (entry 696) ----------------------------

    def create_chart_definition(self, actor, region, commodity, chart_kind):
        """Define a price chart over a core observation series.
        Action: observe. The definition is held as data; its
        series reference must resolve to at least one core price
        observation for the region/commodity. ``rendered_here``
        is False — nothing is drawn here."""
        self._guard(actor, "observe", "ext_chart_create")
        _non_empty(region, "region")
        _non_empty(commodity, "commodity")
        if chart_kind not in CHART_KINDS:
            raise ValidationError("unknown chart kind: %r" % (chart_kind,))
        observations = self.store.list_observations(
            actor, region=region, commodity=commodity)
        if not observations:
            raise ValidationError(
                "no price observations recorded for series %r / %r; a chart "
                "definition must resolve to core records"
                % (region, commodity))
        with self._lock:
            chart = {
                "id": self._next_id("chrt-"),
                "region": region,
                "commodity": commodity,
                "chart_kind": chart_kind,
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._charts[chart["id"]] = chart
        self._audit(actor, "ext_chart_create", chart["id"],
                    {"region": region, "commodity": commodity})
        return copy.deepcopy(chart)

    def create_dashboard_config(self, actor, label, chart_ids):
        """Configure a dashboard as a set of chart definition
        references, held as data. Action: observe.
        ``rendered_here`` is False."""
        self._guard(actor, "observe", "ext_dashboard_create")
        _non_empty(label, "label")
        if not isinstance(chart_ids, (list, tuple)) or not chart_ids:
            raise ValidationError("chart_ids must be a non-empty list")
        chart_ids = list(chart_ids)
        if len(set(chart_ids)) != len(chart_ids):
            raise ValidationError("chart_ids must not contain duplicates")
        with self._lock:
            for chart_id in chart_ids:
                self._get(self._charts, chart_id, "chart definition")
            dashboard = {
                "id": self._next_id("dash-"),
                "label": label,
                "chart_ids": chart_ids,
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._dashboards[dashboard["id"]] = dashboard
        self._audit(actor, "ext_dashboard_create", dashboard["id"],
                    {"label": label})
        return copy.deepcopy(dashboard)

    def get_chart(self, actor, chart_id):
        """The stored chart definition — it carries no series
        counts; those exist only in :meth:`chart_view`."""
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._charts, chart_id,
                                       "chart definition"))

    def list_charts(self, actor):
        self._maybe_require(actor, "read")
        return [copy.deepcopy(c) for c in self._charts.values()]

    def get_dashboard(self, actor, dashboard_id):
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._dashboards, dashboard_id,
                                       "dashboard"))

    def list_dashboards(self, actor):
        self._maybe_require(actor, "read")
        return [copy.deepcopy(d) for d in self._dashboards.values()]

    def chart_view(self, actor, chart_id):
        """The chart definition plus the series facts derived at
        read from the core observations it references: the count
        and the latest recorded price (a recorded value selected
        by observed moment — the core summary's own derivation,
        never a computed score)."""
        self._maybe_require(actor, "read")
        chart = self._get(self._charts, chart_id, "chart definition")
        observations = self.store.list_observations(
            actor, region=chart["region"], commodity=chart["commodity"])
        latest = None
        for observation in observations:
            candidate = (
                _parse_moment(observation["observed_at"], "observed_at"),
                observation["price_cents_per_unit"],
                observation["observed_at"],
                observation["id"],
            )
            if latest is None or candidate[0] >= latest[0]:
                latest = candidate
        view = copy.deepcopy(chart)
        view["observation_count"] = len(observations)
        view["latest_price_cents_per_unit"] = latest[1] if latest else None
        view["latest_observed_at"] = latest[2] if latest else None
        view["latest_observation_id"] = latest[3] if latest else None
        return view

    # -- supply contracts (entry 697) -------------------------------------

    def create_contract(self, actor, customer_id, provider_id, commodity,
                        region, quantity_units, price_cents_per_unit,
                        term_start, term_end, auction_id=None):
        """Record a supply contract over opaque customer and
        provider references. Action: register. The value
        (quantity x price per unit) and the lifecycle state are
        derived at read and never stored; ``executed_here`` is
        False — formation, signature, and performance happen on
        the parties' own systems."""
        self._guard(actor, "register", "ext_contract_create")
        _non_empty(commodity, "commodity")
        _non_empty(region, "region")
        _positive_units(quantity_units, "quantity_units")
        _positive_cents(price_cents_per_unit, "price_cents_per_unit")
        start = _parse_moment(term_start, "term_start")
        end = _parse_moment(term_end, "term_end")
        if end < start:
            raise ValidationError("term_end must not precede term_start")
        self.store.get_customer(actor, customer_id)
        self.store.get_provider(actor, provider_id)
        if auction_id is not None:
            self.store.get_auction(actor, auction_id)
        with self._lock:
            contract = {
                "id": self._next_id("ctr-"),
                "customer_id": customer_id,
                "provider_id": provider_id,
                "auction_id": auction_id,
                "commodity": commodity,
                "region": region,
                "quantity_units": quantity_units,
                "price_cents_per_unit": price_cents_per_unit,
                "term_start": term_start,
                "term_end": term_end,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._contracts[contract["id"]] = contract
        self._audit(actor, "ext_contract_create", contract["id"],
                    {"customer_id": customer_id, "provider_id": provider_id})
        return copy.deepcopy(contract)

    def record_contract_event(self, actor, contract_id, event_label):
        """Record a lifecycle event against a contract (an
        amendment, termination, or renewal the parties effected
        elsewhere). Action: register."""
        self._guard(actor, "register", "ext_contract_event_create")
        if event_label not in CONTRACT_EVENT_LABELS:
            raise ValidationError(
                "unknown contract event label: %r" % (event_label,))
        with self._lock:
            self._get(self._contracts, contract_id, "contract")
            event = {
                "id": self._next_id("cevt-"),
                "contract_id": contract_id,
                "event_label": event_label,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._contract_events[event["id"]] = event
        self._audit(actor, "ext_contract_event_create", event["id"],
                    {"contract_id": contract_id})
        return copy.deepcopy(event)

    def get_contract(self, actor, contract_id):
        """The stored contract record — it carries no value and
        no state key; both exist only in :meth:`contract_view`."""
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._contracts, contract_id,
                                       "contract"))

    def list_contracts(self, actor, customer_id=None):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(c) for c in self._contracts.values()
            if customer_id is None or c["customer_id"] == customer_id
        ]

    def list_contract_events(self, actor, contract_id=None):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(e) for e in self._contract_events.values()
            if contract_id is None or e["contract_id"] == contract_id
        ]

    @staticmethod
    def _derive_contract_state(contract, events, moment):
        """Contract lifecycle seam: the state is derived at read
        from the recorded term window and the recorded events —
        a recorded termination overrides the window; otherwise
        the state is ``pending`` before the term, ``active``
        inside it, and ``expired`` after it. Never stored."""
        labels = [e["event_label"] for e in events]
        if "recorded_terminated" in labels:
            return "terminated"
        start = _parse_moment(contract["term_start"], "term_start")
        end = _parse_moment(contract["term_end"], "term_end")
        if moment < start:
            return "pending"
        if moment > end:
            return "expired"
        return "active"

    @staticmethod
    def _contract_value_cents(contract):
        """The contract's recorded amount, derived at read:
        quantity in whole units x integer cents per unit."""
        return contract["quantity_units"] * contract["price_cents_per_unit"]

    def contract_view(self, actor, contract_id, now=None):
        """The contract record plus its recorded events and the
        value and lifecycle state derived at read."""
        self._maybe_require(actor, "read")
        contract = self._get(self._contracts, contract_id, "contract")
        events = self.list_contract_events(actor, contract_id)
        moment = _parse_moment(now, "now") if now is not None \
            else datetime.now(timezone.utc)
        view = copy.deepcopy(contract)
        view["events"] = events
        view["value_cents"] = self._contract_value_cents(contract)
        view["lifecycle_state"] = self._derive_contract_state(
            contract, events, moment)
        return view

    # -- payment / settlement execution (entry 698) ------------------------

    def _settlement_committed_cents(self, contract_id):
        """Outstanding settlement total for a contract, derived at
        read: every request counts, except one whose latest
        outcome report is ``reported_failed`` (the rail reported
        it settled nothing, so the amount is released). A
        ``reported_paid`` or ``reported_partial`` report leaves
        the full requested amount committed."""
        committed = 0
        for request in self._settlements.values():
            if request["contract_id"] != contract_id:
                continue
            reports = [
                r for r in self._settlement_reports.values()
                if r["settlement_id"] == request["id"]
            ]
            if reports and reports[-1]["report_label"] == "reported_failed":
                continue
            committed += request["amount_cents"]
        return committed

    def request_settlement(self, actor, contract_id, amount_cents):
        """Record a settlement request against a contract.
        Action: conduct. The request is capped by the contract's
        recorded amount via :func:`_check_settlement_cap`;
        ``paid_here`` is False — settlement executes on the
        parties' banking rails, never here."""
        self._guard(actor, "conduct", "ext_settlement_create")
        _positive_cents(amount_cents, "amount_cents")
        with self._lock:
            contract = self._get(self._contracts, contract_id, "contract")
            _check_settlement_cap(
                self._contract_value_cents(contract),
                self._settlement_committed_cents(contract_id),
                amount_cents)
            settlement = {
                "id": self._next_id("stl-"),
                "contract_id": contract_id,
                "amount_cents": amount_cents,
                "paid_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._settlements[settlement["id"]] = settlement
        self._audit(actor, "ext_settlement_create", settlement["id"],
                    {"contract_id": contract_id})
        return copy.deepcopy(settlement)

    def record_settlement_report(self, actor, settlement_id, report_label):
        """Record a settlement outcome exactly as the rail
        reported it. Action: conduct."""
        self._guard(actor, "conduct", "ext_settlement_report_create")
        if report_label not in SETTLEMENT_REPORT_LABELS:
            raise ValidationError(
                "unknown settlement report label: %r" % (report_label,))
        with self._lock:
            self._get(self._settlements, settlement_id, "settlement")
            report = {
                "id": self._next_id("srpt-"),
                "settlement_id": settlement_id,
                "report_label": report_label,
                "paid_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._settlement_reports[report["id"]] = report
        self._audit(actor, "ext_settlement_report_create", report["id"],
                    {"settlement_id": settlement_id})
        return copy.deepcopy(report)

    def get_settlement(self, actor, settlement_id):
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._settlements, settlement_id,
                                       "settlement"))

    def list_settlements(self, actor, contract_id=None):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(s) for s in self._settlements.values()
            if contract_id is None or s["contract_id"] == contract_id
        ]

    def list_settlement_reports(self, actor, settlement_id=None):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._settlement_reports.values()
            if settlement_id is None or r["settlement_id"] == settlement_id
        ]

    def settlement_summary(self, actor, contract_id):
        """The settlement position of one contract, derived at
        read: the contract's recorded amount, the committed
        total under the cap rule, the remaining headroom, and
        record counts. Nothing here is stored."""
        self._maybe_require(actor, "read")
        contract = self._get(self._contracts, contract_id, "contract")
        value = self._contract_value_cents(contract)
        committed = self._settlement_committed_cents(contract_id)
        requests = self.list_settlements(actor, contract_id)
        reports = [
            r for r in self._settlement_reports.values()
            if any(r["settlement_id"] == q["id"] for q in requests)
        ]
        return {
            "contract_id": contract_id,
            "value_cents": value,
            "committed_cents": committed,
            "remaining_cents": value - committed,
            "request_count": len(requests),
            "report_count": len(reports),
        }

    # -- price-trigger evaluation (entry 692, reference stub) ---------------

    def record_trigger_definition(self, actor, subscription_id,
                                  condition_label):
        """Record a price-trigger definition against a core alert
        subscription, as a labeled reference implementation.
        Action: alert. The condition is held as data;
        ``evaluated_here`` is False — the engine that would watch
        prices against it is the fork's, not this build's."""
        self._guard(actor, "alert", "ext_trigger_definition_create")
        if condition_label not in TRIGGER_CONDITIONS:
            raise ValidationError(
                "unknown trigger condition: %r" % (condition_label,))
        self._core_subscription(actor, subscription_id)
        with self._lock:
            definition = {
                "id": self._next_id("trgd-"),
                "subscription_id": subscription_id,
                "condition_label": condition_label,
                "reference_stub": True,
                "evaluated_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._trigger_definitions[definition["id"]] = definition
        self._audit(actor, "ext_trigger_definition_create", definition["id"],
                    {"subscription_id": subscription_id})
        return copy.deepcopy(definition)

    def record_trigger_evaluation(self, actor, definition_id,
                                  evaluation_label):
        """Record a trigger evaluation exactly as the evaluating
        engine reported it. Action: alert. Alert records stay
        Core: recording an evaluation — even a reported firing —
        creates no alert record here."""
        self._guard(actor, "alert", "ext_trigger_evaluation_create")
        if evaluation_label not in TRIGGER_EVALUATION_LABELS:
            raise ValidationError(
                "unknown trigger evaluation label: %r" % (evaluation_label,))
        with self._lock:
            self._get(self._trigger_definitions, definition_id,
                      "trigger definition")
            evaluation = {
                "id": self._next_id("trge-"),
                "definition_id": definition_id,
                "evaluation_label": evaluation_label,
                "reference_stub": True,
                "evaluated_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._trigger_evaluations[evaluation["id"]] = evaluation
        self._audit(actor, "ext_trigger_evaluation_create", evaluation["id"],
                    {"definition_id": definition_id})
        return copy.deepcopy(evaluation)

    def get_trigger_definition(self, actor, definition_id):
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._trigger_definitions,
                                       definition_id, "trigger definition"))

    def list_trigger_definitions(self, actor, subscription_id=None):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(d) for d in self._trigger_definitions.values()
            if subscription_id is None
            or d["subscription_id"] == subscription_id
        ]

    def list_trigger_evaluations(self, actor, definition_id=None):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(e) for e in self._trigger_evaluations.values()
            if definition_id is None or e["definition_id"] == definition_id
        ]

    # -- identity provider (entry 699, reference stub) -----------------------

    def record_identity_reference(self, actor, provider_ref, provider_label):
        """Record the external identity provider in use, as a
        labeled reference implementation. Action: register. Per
        PLATFORM-LAYER.md decision 1, identity proofing,
        authenticator management, and any identity-provider
        service stay with the embedding organization;
        ``identity_provider`` is False and the core's demo
        identities remain hooks, not an IdP."""
        self._guard(actor, "register", "ext_identity_reference_create")
        _non_empty(provider_ref, "provider_ref")
        _non_empty(provider_label, "provider_label")
        with self._lock:
            for existing in self._identity_references.values():
                if existing["provider_ref"] == provider_ref:
                    raise ValidationError(
                        "provider_ref already exists: %r" % (provider_ref,))
            reference = {
                "id": self._next_id("idr-"),
                "provider_ref": provider_ref,
                "provider_label": provider_label,
                "reference_stub": True,
                "identity_provider": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._identity_references[reference["id"]] = reference
        self._audit(actor, "ext_identity_reference_create", reference["id"],
                    {"provider_ref": provider_ref})
        return copy.deepcopy(reference)

    def get_identity_reference(self, actor, reference_id):
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._identity_references,
                                       reference_id, "identity reference"))

    def list_identity_references(self, actor):
        self._maybe_require(actor, "read")
        return [copy.deepcopy(r) for r in self._identity_references.values()]

    # -- energy data integrations (entry 700, reference stub) -----------------

    def record_feed(self, actor, feed_ref, feed_kind):
        """Record an external energy data feed the platform
        consumes, as a labeled reference implementation. Action:
        observe. Receipts carry ``reference_transport: True``;
        no feed data is held in any shape here."""
        self._guard(actor, "observe", "ext_feed_create")
        _non_empty(feed_ref, "feed_ref")
        if feed_kind not in FEED_KINDS:
            raise ValidationError("unknown feed kind: %r" % (feed_kind,))
        with self._lock:
            for existing in self._feeds.values():
                if existing["feed_ref"] == feed_ref:
                    raise ValidationError(
                        "feed_ref already exists: %r" % (feed_ref,))
            feed = {
                "id": self._next_id("feed-"),
                "feed_ref": feed_ref,
                "feed_kind": feed_kind,
                "reference_stub": True,
                "reference_transport": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._feeds[feed["id"]] = feed
        self._audit(actor, "ext_feed_create", feed["id"],
                    {"feed_ref": feed_ref})
        return copy.deepcopy(feed)

    def record_feed_receipt(self, actor, feed_id, records_reported):
        """Record a feed sync receipt with its count exactly as
        the feed reported it. Action: observe.
        ``data_held_here`` is False: the receipt holds a count,
        never feed data."""
        self._guard(actor, "observe", "ext_feed_receipt_create")
        _count(records_reported, "records_reported")
        with self._lock:
            self._get(self._feeds, feed_id, "feed")
            receipt = {
                "id": self._next_id("frcp-"),
                "feed_id": feed_id,
                "records_reported": records_reported,
                "reference_stub": True,
                "reference_transport": True,
                "data_held_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._feed_receipts[receipt["id"]] = receipt
        self._audit(actor, "ext_feed_receipt_create", receipt["id"],
                    {"feed_id": feed_id})
        return copy.deepcopy(receipt)

    def get_feed(self, actor, feed_id):
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._feeds, feed_id, "feed"))

    def list_feeds(self, actor, feed_kind=None):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(f) for f in self._feeds.values()
            if feed_kind is None or f["feed_kind"] == feed_kind
        ]

    def list_feed_receipts(self, actor, feed_id=None):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._feed_receipts.values()
            if feed_id is None or r["feed_id"] == feed_id
        ]

    # -- extension summary ------------------------------------------------------

    def extensions_summary(self, actor):
        """Counts over every extension record type, computed on
        read from the records only. Counts — never scores."""
        self._maybe_require(actor, "read")
        return {
            "auction_runs": len(self._auction_runs),
            "auction_run_reports": len(self._auction_run_reports),
            "deliveries": len(self._deliveries),
            "delivery_reports": len(self._delivery_reports),
            "analyses": len(self._analyses),
            "advisory_sessions": len(self._advisory_sessions),
            "recommendations": len(self._recommendations),
            "charts": len(self._charts),
            "dashboards": len(self._dashboards),
            "contracts": len(self._contracts),
            "contract_events": len(self._contract_events),
            "settlements": len(self._settlements),
            "settlement_reports": len(self._settlement_reports),
            "trigger_definitions": len(self._trigger_definitions),
            "trigger_evaluations": len(self._trigger_evaluations),
            "identity_references": len(self._identity_references),
            "feeds": len(self._feeds),
            "feed_receipts": len(self._feed_receipts),
        }
