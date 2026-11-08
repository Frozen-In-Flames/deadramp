"""Final GAPS batch, second unit -- remainder-addition extensions
for the Customer Service L3-adjacent build.

Clean-room, standard-library-only records extensions for the 2 open
entries of the "Remainder Addition -- Customer Service L3-adjacent
(+1 fork)" GAPS.md section (the Medallia GovCloud addition; see
``../BATCH-ADDITION.md`` for the per-entry dispositions and
``../ADDENDUM.md`` for the claims these entries rest on):

- the survey & feedback-collection entry, built as records: survey
  instrument definitions, survey response records holding each
  reported value **verbatim**, and feedback-signal records over
  opaque references. Nothing is captured on any channel here, no
  reported figure is ever computed, aggregated or ranked, and
  conversation or message content is never held -- a response is a
  reported value on a recorded scale, a signal is an opaque
  reference on a named channel;
- the platform connectors & integration API entry, shipped as a
  labeled reference implementation: connector definitions and
  exchange records with ``reference_stub: True`` and
  ``reference_transport: True``; nothing connects, syncs or
  executes here.

Design, following the core's doctrines, the first batch unit's
forms (``custsvc/extensions.py``) and the High apparatus:

- This module is a second wrapper around :class:`CustsvcStore`;
  every existing module, the first unit's ``extensions.py``
  included, is untouched (byte-identical). Core state is read
  through the core store's public API only, and no addition
  operation writes core state: a test pins that recording survey
  responses and feedback signals creates no core case and no core
  alert -- the records a flagged signal would write remain the
  core's own ingest paths' business, exactly as ADDENDUM.md
  states.
- RBAC goes through :mod:`custsvc.access` exactly as the core and
  the first unit enforce it: operations map onto ``case_write`` /
  ``case_read`` (records) and ``report_read`` (summaries), checked
  before any state change or id allocation; denied attempts are
  recorded on the core audit log as ``exta_<action>:denied``. The
  auditor role (``audit_read`` only, AC-5) is therefore denied
  every operation on this surface, reads included, while its core
  audit duty still works.
- Every successful mutation is recorded on the core store's
  hash-chained audit log with an action name prefixed ``exta_``
  (AU-9 / AU-5). If the audit write raises, the record insertion
  and its id roll back before the error propagates:
  audit-before-commit.
- Survey figures are reports, not judgments: a response's value is
  validated against its instrument's recorded scale and stored
  verbatim as ``reported_value``. No view computes a mean, a
  distribution, a tally of values, a ranking or any other
  aggregate over reported values -- the only numbers a view
  derives are counts of this surface's own records and the
  identity of the latest record, derived at read via the single
  seam :meth:`CustsvcExtensionsAddition._latest_record` and never
  stored. Stored records carry no derived key; tests pin the
  exact stored key sets.
- Respondents are requesters already registered in the core, by
  opaque ``requester_ref``, so the core's pinned record shape --
  which cannot hold a phone number, email address or real
  identifier -- governs them too. Every other party, signal and
  platform is an opaque ``*_ref`` string or a label held as data.
  No parameter on this surface can accept conversation content,
  message text, a transcript, a body or a comment: content-shaped
  arguments raise ``TypeError`` (pinned), and a recursive scan
  over every record and view finds no content- or score-shaped
  key and no float.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

# The capture channels the addition fork names in its own claim
# evidence (ADDENDUM.md SS2): in-person, traditional surveys, calls,
# digital channels, video, social media and IoT interactions. Held
# as the recorded vocabulary for instruments, responses and
# signals; naming a channel here captures nothing on it.
SURVEY_CHANNELS = (
    "in_person",
    "survey",
    "call",
    "digital",
    "video",
    "social_media",
    "iot",
)
KNOWN_SURVEY_CHANNELS = frozenset(SURVEY_CHANNELS)
CONNECTOR_KINDS = ("platform_connector", "api_surface")
KNOWN_CONNECTOR_KINDS = frozenset(CONNECTOR_KINDS)
EXCHANGE_DIRECTIONS = ("inbound", "outbound")
KNOWN_EXCHANGE_DIRECTIONS = frozenset(EXCHANGE_DIRECTIONS)
EXCHANGE_OUTCOMES = (
    "reported_completed",
    "reported_partial",
    "reported_failed",
)
KNOWN_EXCHANGE_OUTCOMES = frozenset(EXCHANGE_OUTCOMES)


def _utc_now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _one_of(value, known, names, what):
    if value not in known:
        raise ValidationError("%s must be one of %s" % (what, ", ".join(names)))
    return value


def _int_value(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    return value


def _channel_list(value, what):
    if not isinstance(value, list) or not value:
        raise ValidationError("%s must be a non-empty list of channels" % (what,))
    result = []
    for item in value:
        _one_of(item, KNOWN_SURVEY_CHANNELS, SURVEY_CHANNELS, what)
        if item not in result:
            result.append(item)
    return result


class CustsvcExtensionsAddition:
    """Second GAPS-batch extension surface over a core CustsvcStore."""

    def __init__(self, store):
        self.store = store
        self._records = {}  # (kind, id) -> dict
        self._order = []  # (kind, id) in creation order
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers (mirroring custsvc/extensions.py) -----------

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self.store, "audit", None)
        if audit is not None:
            audit.record(actor_name(actor), action, target, details=details)

    def _guard(self, actor, core_action, audit_action, target=None):
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

    def _latest_record(self, records):
        """The latest of a record list, or None -- the single seam
        every "current / latest" derivation on this surface reads
        through (a survey view's latest reported response, a
        connector view's latest exchange). See the mutation record
        in tests/README.md (this unit's fresh negative control)."""
        if not records:
            return None
        return records[-1]

    def _core_requester(self, requester_ref, actor):
        return self.store.get_requester_by_ref(requester_ref, actor)

    def _core_case(self, case_id, actor):
        return self.store.get_case(case_id, actor)

    def _core_alert(self, alert_id, actor):
        for alert in self.store.list_alerts(actor):
            if alert["id"] == alert_id:
                return alert
        raise NotFoundError("alert not found: %r" % (alert_id,))

    # -- survey & feedback collection (built, records form) -----------
    #
    # Instrument definitions (name, capture channels and response
    # scale held as recorded terms), response records (a registered
    # requester's reported value on the instrument's scale, stored
    # verbatim), and feedback-signal records (an opaque signal ref
    # on a named channel, optionally bound to an existing core case
    # or alert). Collection itself -- capturing a signal on a
    # channel -- happens in the platform elsewhere; this surface is
    # the records layer those captures report into. No figure is
    # computed from reported values anywhere on this surface.

    def create_survey_instrument(self, name, channels, scale_low,
                                 scale_high, actor):
        """Register a survey instrument definition: its capture
        channels and its response scale, held as recorded terms.
        The scale bounds are integers with ``scale_low`` below
        ``scale_high``; booleans and floats are rejected. The
        stored record carries no tally or aggregate key."""
        self._guard(actor, "case_write", "exta_survey_instrument_create")
        _non_empty(name, "name")
        channel_labels = _channel_list(channels, "channels")
        _int_value(scale_low, "scale_low")
        _int_value(scale_high, "scale_high")
        if scale_low >= scale_high:
            raise ValidationError("scale_low must be below scale_high")
        return self._create(
            "survey_instrument", "survey",
            {"name": name, "channels": channel_labels,
             "scale_low": scale_low, "scale_high": scale_high,
             "collected_here": False},
            actor, "exta_survey_instrument_create")

    def get_survey_instrument(self, survey_id, actor):
        """The stored instrument record. It carries no tally,
        total or latest-response key; those exist only as the
        read-time derivation in :meth:`survey_view`."""
        self._guard_read(actor, "case_read", "exta_survey_instrument_get",
                         target=survey_id)
        return self._fetch("survey_instrument", survey_id)

    def list_survey_instruments(self, actor):
        self._guard_read(actor, "case_read", "exta_survey_instrument_list")
        return self._list("survey_instrument")

    def record_survey_response(self, survey_id, requester_ref, channel,
                               reported_value, actor):
        """Record one survey response as reported. The respondent
        must be a requester already registered in the core (by
        opaque ref); ``channel`` must be one of the instrument's
        recorded channels; ``reported_value`` must be an integer
        on the instrument's recorded scale (booleans and floats
        rejected) and is stored **verbatim** -- it is a report,
        never combined with any other value anywhere here."""
        self._guard(actor, "case_write", "exta_survey_response",
                    target=survey_id)
        instrument = self._get("survey_instrument", survey_id)
        self._core_requester(requester_ref, actor)
        if channel not in instrument["channels"]:
            raise ValidationError(
                "channel must be one of the instrument's channels: %s"
                % (", ".join(instrument["channels"]),))
        _int_value(reported_value, "reported_value")
        if not instrument["scale_low"] <= reported_value <= instrument["scale_high"]:
            raise ValidationError(
                "reported_value must lie on the instrument's recorded "
                "scale (%d..%d)" % (instrument["scale_low"],
                                    instrument["scale_high"]))
        return self._create(
            "survey_response", "sresp",
            {"survey_id": survey_id, "requester_ref": requester_ref,
             "channel": channel, "reported_value": reported_value,
             "reported": True, "collected_here": False},
            actor, "exta_survey_response")

    def list_survey_responses(self, survey_id, actor):
        self._guard_read(actor, "case_read", "exta_survey_response_list",
                         target=survey_id)
        self._get("survey_instrument", survey_id)
        return self._list("survey_response", survey_id=survey_id)

    def record_feedback_signal(self, signal_ref, channel, actor,
                               survey_id=None, requester_ref=None,
                               case_id=None, alert_id=None):
        """Record one feedback signal as reported: an opaque
        ``signal_ref`` on a named channel, optionally bound to the
        survey instrument it was collected under, to a registered
        core requester, and to an existing core case or alert.
        Every named binding must exist. Recording a signal writes
        no core record: a flagged signal's case or alert comes to
        exist only through the core's own ingest paths (pinned by
        test). No signal content is held -- there is no field for
        it."""
        self._guard(actor, "case_write", "exta_feedback_signal")
        _non_empty(signal_ref, "signal_ref")
        _one_of(channel, KNOWN_SURVEY_CHANNELS, SURVEY_CHANNELS, "channel")
        if survey_id is not None:
            self._get("survey_instrument", survey_id)
        if requester_ref is not None:
            self._core_requester(requester_ref, actor)
        if case_id is not None:
            self._core_case(case_id, actor)
        if alert_id is not None:
            self._core_alert(alert_id, actor)
        return self._create(
            "feedback_signal", "fsig",
            {"signal_ref": signal_ref, "channel": channel,
             "survey_id": survey_id, "requester_ref": requester_ref,
             "case_id": case_id, "alert_id": alert_id,
             "reported": True, "collected_here": False},
            actor, "exta_feedback_signal")

    def list_feedback_signals(self, actor, survey_id=None, channel=None):
        self._guard_read(actor, "case_read", "exta_feedback_signal_list")
        filters = {}
        if survey_id is not None:
            filters["survey_id"] = survey_id
        if channel is not None:
            filters["channel"] = channel
        return self._list("feedback_signal", **filters)

    def survey_view(self, survey_id, actor):
        """Derived at read: the instrument record plus counts of
        its recorded responses and signals (overall and per
        channel) and the latest recorded response, read through
        the :meth:`_latest_record` seam. Counts are counts of
        records; no reported value is summed, averaged, tallied
        or ranked, and nothing derived is stored."""
        self._guard_read(actor, "case_read", "exta_survey_view",
                         target=survey_id)
        record = self._fetch("survey_instrument", survey_id)
        responses = self._list("survey_response", survey_id=survey_id)
        signals = self._list("feedback_signal", survey_id=survey_id)
        by_channel = {}
        for response in responses:
            by_channel[response["channel"]] = \
                by_channel.get(response["channel"], 0) + 1
        latest = self._latest_record(responses)
        view = dict(record)
        view["response_count"] = len(responses)
        view["signal_count"] = len(signals)
        view["responses_by_channel"] = by_channel
        view["latest_response_id"] = latest["id"] if latest else None
        view["latest_reported_value"] = \
            latest["reported_value"] if latest else None
        view["derived"] = True
        view["method"] = "counts_over_survey_records"
        return view

    def feedback_summary(self, actor):
        """Derived at read: counts over this surface's own records
        -- instruments, responses and signals, responses and
        signals by channel. Counts only; no reported figure is
        aggregated anywhere in the summary."""
        self._guard_read(actor, "report_read", "exta_feedback_summary")
        responses = self._list("survey_response")
        signals = self._list("feedback_signal")
        responses_by_channel = {}
        for response in responses:
            responses_by_channel[response["channel"]] = \
                responses_by_channel.get(response["channel"], 0) + 1
        signals_by_channel = {}
        for signal in signals:
            signals_by_channel[signal["channel"]] = \
                signals_by_channel.get(signal["channel"], 0) + 1
        return {"instruments": len(self._list("survey_instrument")),
                "responses": len(responses),
                "signals": len(signals),
                "responses_by_channel": responses_by_channel,
                "signals_by_channel": signals_by_channel,
                "collected_here": False, "derived": True,
                "method": "counts_over_survey_records"}

    # -- platform connectors & integration API surface (reference) ----
    #
    # Connector definitions (an opaque connector ref, a kind, and
    # the external platform's label held as data -- the fork names
    # two platforms in its closing bullet; a label here asserts no
    # integration with it) and exchange records (direction, the
    # platform's reported outcome verbatim, an optional reported
    # record count). Every record carries reference_stub: True and
    # reference_transport: True; nothing connects, syncs, imports
    # or executes here.

    def register_connector(self, connector_ref, kind, platform_label,
                           actor):
        """Register a connector definition record. ``connector_ref``
        is unique on this surface: re-registering the same ref is
        refused."""
        self._guard(actor, "case_write", "exta_connector_register")
        _non_empty(connector_ref, "connector_ref")
        _one_of(kind, KNOWN_CONNECTOR_KINDS, CONNECTOR_KINDS, "kind")
        _non_empty(platform_label, "platform_label")
        if self._list("connector", connector_ref=connector_ref):
            raise ValidationError(
                "connector_ref already registered: %r" % (connector_ref,))
        return self._create(
            "connector", "conn",
            {"connector_ref": connector_ref, "kind": kind,
             "platform_label": platform_label,
             "reference_stub": True, "reference_transport": True,
             "connected_here": False, "synced_here": False,
             "state": "recorded_reference_only"},
            actor, "exta_connector_register")

    def get_connector(self, connector_id, actor):
        self._guard_read(actor, "case_read", "exta_connector_get",
                         target=connector_id)
        return self._fetch("connector", connector_id)

    def list_connectors(self, actor):
        self._guard_read(actor, "case_read", "exta_connector_list")
        return self._list("connector")

    def record_exchange(self, connector_id, direction, outcome, actor,
                        records_reported=None, case_id=None):
        """Record one connector exchange as reported by the
        platform: direction, outcome verbatim, and an optional
        non-negative integer count of records the platform reports
        having moved (booleans, floats and negatives rejected --
        the count is the platform's report, held as data; nothing
        was imported or exported by this build). ``case_id``, when
        given, must name an existing core case."""
        self._guard(actor, "case_write", "exta_connector_exchange",
                    target=connector_id)
        _one_of(direction, KNOWN_EXCHANGE_DIRECTIONS, EXCHANGE_DIRECTIONS,
                "direction")
        _one_of(outcome, KNOWN_EXCHANGE_OUTCOMES, EXCHANGE_OUTCOMES,
                "outcome")
        if records_reported is not None:
            _int_value(records_reported, "records_reported")
            if records_reported < 0:
                raise ValidationError("records_reported must be non-negative")
        self._get("connector", connector_id)
        if case_id is not None:
            self._core_case(case_id, actor)
        return self._create(
            "connector_exchange", "exch",
            {"connector_id": connector_id, "direction": direction,
             "outcome": outcome, "records_reported": records_reported,
             "case_id": case_id, "reported": True,
             "reference_stub": True, "reference_transport": True,
             "imported_here": False, "executed_here": False},
            actor, "exta_connector_exchange")

    def list_exchanges(self, connector_id, actor):
        self._guard_read(actor, "case_read", "exta_connector_exchange_list",
                         target=connector_id)
        self._get("connector", connector_id)
        return self._list("connector_exchange", connector_id=connector_id)

    def connector_view(self, connector_id, actor):
        """Derived at read: the connector record plus its exchange
        count and latest recorded exchange outcome, read through
        the :meth:`_latest_record` seam. Nothing derived is stored
        on the connector record."""
        self._guard_read(actor, "case_read", "exta_connector_view",
                         target=connector_id)
        record = self._fetch("connector", connector_id)
        exchanges = self._list("connector_exchange",
                               connector_id=connector_id)
        latest = self._latest_record(exchanges)
        view = dict(record)
        view["exchange_count"] = len(exchanges)
        view["latest_exchange_outcome"] = latest["outcome"] if latest else None
        view["derived"] = True
        return view
