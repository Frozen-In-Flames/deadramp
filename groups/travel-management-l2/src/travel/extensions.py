"""Final GAPS batch extensions for Travel Management L2
(Singleton 55).

Clean-room, standard-library-only extensions for the 8 open
entries of the "Singleton 55 — Travel Management L2 (1 fork, new
category)" section of GAPS.md (see ``BATCH.md`` in the group
directory for the per-entry disposition). This module is a
wrapper around :class:`TravelStore`; every core module is
untouched and byte-identical to the shipped build.

**The founding discipline binds absolutely, here as in the
core:** this build holds records about travel. It books nothing
with any supplier, tickets nothing, pays no one, captures no
receipt image, executes no connector, delivers no notification,
and generates no report. Every entity shape in this module
carries metadata and opaque caller-supplied references only,
plus figures and outcomes stored exactly as reported by the
external systems and people who actually did the work. Methods
accept only their named parameters, so a caller cannot smuggle
an unlisted field into a record (pinned by tests: an unexpected
keyword raises ``TypeError`` — no passenger name, no document
number, no image bytes, no credential can enter any shape).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — request, definition, and outcome records
over the group's OWN records (core records and extension
records), plus deterministic derivations at read:

- Booking is booking-request records bound to a core trip
  authorization (copying its traveler id), plus outcome reports
  stored verbatim as the booking system reported them; the
  current outcome derives at read from the latest report. No
  inventory is held and no supplier is contacted
  (``booked_here`` / ``ticketed_here`` are False).
- Carrier, hotel & GDS reservation integrations ship as labeled
  reference implementations: integration records plus sync
  receipts holding counts exactly as reported, every receipt
  ``reference_transport: True``; nothing connects and nothing is
  transmitted.
- Payment & disbursement execution is disbursement-request
  records against an approved core expense report, capped
  cumulatively by the report's own derived total (the seam
  :meth:`TravelExtensions._check_disbursement_cap`, the fresh
  negative control's target), plus outcome reports stored
  verbatim. Vouchers stay core records; no money moves
  (``paid_here`` / ``disbursed_here`` / ``moved_here`` False).
- Receipt capture is receipt registration records bound to a
  core expense line item — an opaque receipt reference and an
  optional SHA-256 digest, never image content — plus
  extraction outcome reports holding the capture system's
  reported figure verbatim (``content_held_here`` /
  ``imaged_here`` / ``ocr_performed_here`` False).
- Integration connector engines ship as labeled reference
  implementations bound to core integration definitions (the
  registry holds definitions only and never executes, in the
  core as here): connector records plus run reports with counts
  as reported; nothing executes and nothing connects.
- Notification delivery transport is delivery-attempt records
  bound to core notification records, labeled
  ``reference_transport: True``, plus delivery outcome reports
  stored verbatim; nothing is sent (``delivered_here`` /
  ``transmitted_here`` False).
- Report generation is report *definition* records (the
  definition text held verbatim as data, never executed or
  rendered) plus run records that store no figures — the run
  view derives its figures from the core organization summary
  at read, so the figures track registry state. Dashboards are
  configuration records held as data; nothing is drawn.
- The identity provider entry follows PLATFORM-LAYER.md
  decision 1 (IA-2 stays with the embedding organization;
  ``identity_provider`` False) as labeled reference records
  naming the external provider in use; the core's demo
  identities remain hooks, not an IdP.

Doctrines carried from the core: derived-never-stored for every
computed value (booking current outcomes, disbursement
committed amounts, delivery current outcomes, report-run
figures, all summaries); money is integer cents, with booleans
and floats rejected at the boundary; append-only audit on the
core store's log with ``ext_``-prefixed actions for every
successful mutation, and denied write attempts recorded with a
``:denied`` suffix; RBAC via :mod:`travel.access` with the
core's existing actions (``enter`` for request/definition
records, ``record`` for reports, receipts, and attempts),
enforced before any state change or id allocation, so a failed
operation consumes no id and changes nothing; organization
membership enforced through the core store's own access checks
on every org-scoped or core-bound operation.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

SEGMENT_KINDS = ("air", "rail", "lodging", "ground", "other")
BOOKING_OUTCOME_LABELS = (
    "reported_booked",
    "reported_ticketed",
    "reported_waitlisted",
    "reported_failed",
)
RESERVATION_SYSTEM_KINDS = ("carrier", "hotel", "gds", "rail", "other")
RESERVATION_OUTCOME_LABELS = (
    "reported_confirmed",
    "reported_pending",
    "reported_failed",
)
DISBURSEMENT_OUTCOME_LABELS = (
    "reported_paid",
    "reported_partial",
    "reported_failed",
    "reported_returned",
)
RECEIPT_OUTCOME_LABELS = (
    "reported_extracted",
    "reported_partial",
    "reported_unreadable",
    "reported_failed",
)
CONNECTOR_OUTCOME_LABELS = (
    "reported_synced",
    "reported_partial",
    "reported_failed",
)
DELIVERY_CHANNELS = ("email", "sms", "push", "mail", "other")
DELIVERY_OUTCOME_LABELS = (
    "reported_delivered",
    "reported_bounced",
    "reported_failed",
)
REPORT_RUN_OUTCOME_LABELS = ("reported_generated", "reported_failed")

_REFERENCE_STATE = "recorded_reference_only"
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_RELEASE_OUTCOMES = ("reported_failed", "reported_returned")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _optional_text(value, field):
    if value is None:
        return None
    return _text(value, field)


def _money(value, field, allow_zero=True):
    """Integer cents; booleans and floats rejected (core discipline)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents" % field)
    if allow_zero and value < 0:
        raise ValidationError("%s must not be negative" % field)
    if not allow_zero and value <= 0:
        raise ValidationError("%s must be positive" % field)
    return value


def _count(value, field):
    """A non-negative integer count; booleans and floats rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be a non-negative integer" % (field,))
    if value < 0:
        raise ValidationError("%s must be a non-negative integer" % (field,))
    return value


def _latest_outcome(reports):
    """The current outcome of a request: the latest report's
    outcome label, or None when no report exists. Derived at
    read; never stored on the request record."""
    if not reports:
        return None
    return reports[-1]["outcome_label"]


class TravelExtensions:
    """Extension surface wrapping one :class:`TravelStore`."""

    def __init__(self, store):
        self.store = store
        self._booking_requests = {}
        self._booking_reports = {}
        self._reservation_integrations = {}
        self._reservation_receipts = {}
        self._disbursement_requests = {}
        self._disbursement_reports = {}
        self._receipts = {}
        self._receipt_reports = {}
        self._connector_references = {}
        self._connector_reports = {}
        self._delivery_attempts = {}
        self._delivery_reports = {}
        self._report_definitions = {}
        self._report_runs = {}
        self._dashboards = {}
        self._identity_references = {}
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
        via :func:`travel.access.require`; a plain string carries
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

    def _org(self, actor, org_id):
        """Enforce role + organization membership via the core
        store's own access check, and return the organization."""
        return self.store.get_organization(actor, org_id)

    def _core_authorization(self, actor, authorization_id):
        return self.store.get_authorization(actor, authorization_id)

    def _core_report(self, actor, report_id):
        return self.store.get_expense_report(actor, report_id)

    def _core_item(self, actor, report_id, item_id):
        for item in self.store.list_expense_items(actor, report_id):
            if item["id"] == item_id:
                return item
        raise NotFoundError("expense item not found: %r" % (item_id,))

    def _core_notification(self, actor, org_id, notification_id):
        for note in self.store.list_notifications(actor, org_id):
            if note["id"] == notification_id:
                return note
        raise NotFoundError("notification not found: %r" % (notification_id,))

    def _core_integration(self, actor, org_id, integration_id):
        for integration in self.store.list_integrations(actor, org_id):
            if integration["id"] == integration_id:
                return integration
        raise NotFoundError("integration not found: %r" % (integration_id,))

    # -- travel booking & reservation engine (entry 531, built) ----------

    def create_booking_request(self, actor, authorization_id, segment_kind,
                               provider_label, fare_cents):
        """Record a booking request against a core trip
        authorization. Action: enter. The request is a record of
        an intended booking; no inventory is held, no supplier is
        contacted, and nothing is booked or ticketed here. The
        traveler id is copied from the core authorization, as in
        the Finance line's booking-execution form."""
        self._guard(actor, "enter", "ext_booking_request_create")
        authorization = self._core_authorization(actor, authorization_id)
        if segment_kind not in SEGMENT_KINDS:
            raise ValidationError(
                "segment_kind must be one of %r" % (SEGMENT_KINDS,))
        _text(provider_label, "provider_label")
        _money(fare_cents, "fare_cents", allow_zero=False)
        with self._lock:
            request = {
                "id": self._next_id("bkr-"),
                "org_id": authorization["org_id"],
                "authorization_id": authorization_id,
                "traveler_id": authorization["traveler_id"],
                "segment_kind": segment_kind,
                "provider_label": provider_label,
                "fare_cents": fare_cents,
                "booked_here": False,
                "ticketed_here": False,
                "state": "recorded_request_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._booking_requests[request["id"]] = request
        self._audit(actor, "ext_booking_request_create", request["id"],
                    {"authorization_id": authorization_id})
        return copy.deepcopy(request)

    def record_booking_report(self, actor, request_id, outcome_label,
                              reported_reference=""):
        """Record the outcome of a booking request exactly as the
        booking system reported it. Action: record. The reported
        confirmation reference is held verbatim as reported data;
        it is not a booking made here and changes nothing in the
        core — the core authorization stays byte-identical."""
        self._guard(actor, "record", "ext_booking_report_create")
        if outcome_label not in BOOKING_OUTCOME_LABELS:
            raise ValidationError(
                "unknown booking outcome label: %r" % (outcome_label,))
        if not isinstance(reported_reference, str):
            raise ValidationError("reported_reference must be a string")
        with self._lock:
            self._get(self._booking_requests, request_id, "booking request")
            report = {
                "id": self._next_id("bkrp-"),
                "request_id": request_id,
                "outcome_label": outcome_label,
                "reported_reference": reported_reference,
                "booked_here": False,
                "ticketed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._booking_reports[report["id"]] = report
        self._audit(actor, "ext_booking_report_create", report["id"],
                    {"request_id": request_id})
        return copy.deepcopy(report)

    def get_booking_request(self, actor, request_id):
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._booking_requests, request_id,
                                       "booking request"))

    def list_booking_requests(self, actor, authorization_id):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._booking_requests.values()
            if r["authorization_id"] == authorization_id
        ]

    def list_booking_reports(self, actor, request_id):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._booking_reports.values()
            if r["request_id"] == request_id
        ]

    def booking_view(self, actor, request_id):
        """A booking request, its reported outcomes, and the
        current outcome derived at read from the latest report."""
        self._maybe_require(actor, "read")
        request = self._get(self._booking_requests, request_id,
                            "booking request")
        view = copy.deepcopy(request)
        reports = self.list_booking_reports(actor, request_id)
        view["reports"] = reports
        view["current_outcome"] = _latest_outcome(reports)
        return view

    # -- carrier, hotel & GDS reservation integrations (entry 532, ------
    #    reference stub)

    def record_reservation_integration(self, actor, org_id, system_ref,
                                       system_kind, provider_label):
        """Record an external reservation system the platform
        integrates with, as a labeled reference implementation.
        Action: enter. Nothing connects and nothing is
        transmitted; the record names the external system in
        use."""
        self._guard(actor, "enter", "ext_reservation_integration_create")
        self._org(actor, org_id)
        _text(system_ref, "system_ref")
        if system_kind not in RESERVATION_SYSTEM_KINDS:
            raise ValidationError(
                "system_kind must be one of %r" % (RESERVATION_SYSTEM_KINDS,))
        _text(provider_label, "provider_label")
        with self._lock:
            for existing in self._reservation_integrations.values():
                if existing["org_id"] == org_id \
                        and existing["system_ref"] == system_ref:
                    raise ValidationError(
                        "system_ref already exists in this organization: %r"
                        % (system_ref,))
            integration = {
                "id": self._next_id("rsv-"),
                "org_id": org_id,
                "system_ref": system_ref,
                "system_kind": system_kind,
                "provider_label": provider_label,
                "reference_stub": True,
                "reference_transport": True,
                "connected_here": False,
                "transmitted_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._reservation_integrations[integration["id"]] = integration
        self._audit(actor, "ext_reservation_integration_create",
                    integration["id"], {"org_id": org_id})
        return copy.deepcopy(integration)

    def record_reservation_receipt(self, actor, integration_id,
                                   outcome_label, reported_count):
        """Record a reservation sync receipt exactly as the
        external system reported it. Action: record. The count
        is reported data; no reservation data is held in any
        shape here."""
        self._guard(actor, "record", "ext_reservation_receipt_create")
        if outcome_label not in RESERVATION_OUTCOME_LABELS:
            raise ValidationError(
                "unknown reservation outcome label: %r" % (outcome_label,))
        _count(reported_count, "reported_count")
        with self._lock:
            self._get(self._reservation_integrations, integration_id,
                      "reservation integration")
            receipt = {
                "id": self._next_id("rsvr-"),
                "integration_id": integration_id,
                "outcome_label": outcome_label,
                "reported_count": reported_count,
                "reference_stub": True,
                "reference_transport": True,
                "transmitted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._reservation_receipts[receipt["id"]] = receipt
        self._audit(actor, "ext_reservation_receipt_create", receipt["id"],
                    {"integration_id": integration_id})
        return copy.deepcopy(receipt)

    def list_reservation_integrations(self, actor, org_id):
        self._maybe_require(actor, "read")
        self._org(actor, org_id)
        return [
            copy.deepcopy(i) for i in self._reservation_integrations.values()
            if i["org_id"] == org_id
        ]

    def list_reservation_receipts(self, actor, integration_id):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._reservation_receipts.values()
            if r["integration_id"] == integration_id
        ]

    def reservation_integration_view(self, actor, integration_id):
        """An integration record plus its receipts, with the
        receipt count and reported total derived at read."""
        self._maybe_require(actor, "read")
        integration = self._get(self._reservation_integrations,
                                integration_id, "reservation integration")
        view = copy.deepcopy(integration)
        receipts = self.list_reservation_receipts(actor, integration_id)
        view["receipts"] = receipts
        view["receipt_count"] = len(receipts)
        view["reported_total"] = sum(r["reported_count"] for r in receipts)
        return view

    # -- payment & disbursement execution (entry 533, built) -------------

    def _disbursement_committed(self, report_id):
        """Cents committed against an expense report by this
        surface: the sum of disbursement requests whose latest
        outcome report is not a release outcome (failed /
        returned). A request with no report is committed.
        Derived at read from the request and report records."""
        committed = 0
        for request in self._disbursement_requests.values():
            if request["report_id"] != report_id:
                continue
            reports = [r for r in self._disbursement_reports.values()
                       if r["request_id"] == request["id"]]
            if reports and reports[-1]["outcome_label"] in _RELEASE_OUTCOMES:
                continue
            committed += request["amount_cents"]
        return committed

    def _check_disbursement_cap(self, report_total_cents, committed_cents,
                                amount_cents):
        """Enforce the disbursement cap for one request.

        ``report_total_cents`` is the linked core expense
        report's derived total; ``committed_cents`` is this
        surface's outstanding committed total against the same
        report (see :meth:`_disbursement_committed`). A request
        that would push the committed total even one cent over
        the report's total is rejected whole — the same shape as
        the core's signature voucher cap, over this surface's
        requests. This is the fresh negative control's target.
        """
        if committed_cents + amount_cents > report_total_cents:
            raise ValidationError(
                "disbursement request exceeds the expense report total: "
                "report total %d, committed %d, requested %d"
                % (report_total_cents, committed_cents, amount_cents))
        return True

    def request_disbursement(self, actor, report_id, amount_cents):
        """Record a disbursement request against an approved core
        expense report. Action: record. The request is a record
        of an intended payment; no money moves here and no one is
        paid. Cumulative outstanding requests never exceed the
        report's derived total (the cap above)."""
        self._guard(actor, "record", "ext_disbursement_request_create")
        report = self._core_report(actor, report_id)
        _money(amount_cents, "amount_cents", allow_zero=False)
        if report["status"] != "approved":
            raise ValidationError(
                "disbursement requests require an approved expense "
                "report; status is %r" % report["status"])
        with self._lock:
            committed = self._disbursement_committed(report_id)
            self._check_disbursement_cap(report["total_cents"], committed,
                                         amount_cents)
            request = {
                "id": self._next_id("dis-"),
                "org_id": report["org_id"],
                "report_id": report_id,
                "amount_cents": amount_cents,
                "paid_here": False,
                "disbursed_here": False,
                "moved_here": False,
                "state": "recorded_request_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._disbursement_requests[request["id"]] = request
        self._audit(actor, "ext_disbursement_request_create", request["id"],
                    {"report_id": report_id, "amount_cents": amount_cents})
        return copy.deepcopy(request)

    def record_disbursement_report(self, actor, request_id, outcome_label):
        """Record the outcome of a disbursement request exactly
        as the paying system reported it. Action: record. The
        outcome is reported data; the request record is unchanged
        and no money moved here."""
        self._guard(actor, "record", "ext_disbursement_report_create")
        if outcome_label not in DISBURSEMENT_OUTCOME_LABELS:
            raise ValidationError(
                "unknown disbursement outcome label: %r" % (outcome_label,))
        with self._lock:
            self._get(self._disbursement_requests, request_id,
                      "disbursement request")
            report = {
                "id": self._next_id("disr-"),
                "request_id": request_id,
                "outcome_label": outcome_label,
                "paid_here": False,
                "disbursed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._disbursement_reports[report["id"]] = report
        self._audit(actor, "ext_disbursement_report_create", report["id"],
                    {"request_id": request_id})
        return copy.deepcopy(report)

    def list_disbursement_requests(self, actor, report_id):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._disbursement_requests.values()
            if r["report_id"] == report_id
        ]

    def list_disbursement_reports(self, actor, request_id):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._disbursement_reports.values()
            if r["request_id"] == request_id
        ]

    def disbursement_view(self, actor, request_id):
        """A disbursement request, its reported outcomes, and the
        current outcome derived at read from the latest report."""
        self._maybe_require(actor, "read")
        request = self._get(self._disbursement_requests, request_id,
                            "disbursement request")
        view = copy.deepcopy(request)
        reports = self.list_disbursement_reports(actor, request_id)
        view["reports"] = reports
        view["current_outcome"] = _latest_outcome(reports)
        return view

    def report_disbursement_summary(self, actor, report_id):
        """Per-report disbursement totals derived at read: the
        core report's total, the sum of all requests, the
        committed (outstanding) sum, and the request count.
        Counts and money sums only — no score is computed."""
        self._maybe_require(actor, "read")
        report = self._core_report(actor, report_id)
        requests = [r for r in self._disbursement_requests.values()
                    if r["report_id"] == report_id]
        return {
            "report_id": report_id,
            "report_total_cents": report["total_cents"],
            "requested_cents": sum(r["amount_cents"] for r in requests),
            "committed_cents": self._disbursement_committed(report_id),
            "request_count": len(requests),
        }

    # -- receipt capture & imaging / OCR (entry 534, built) --------------

    def register_receipt(self, actor, report_id, item_id, receipt_ref,
                         sha256_digest=""):
        """Register a receipt record against a core expense line
        item. Action: record. The record holds an opaque receipt
        reference and an optional SHA-256 digest of the receipt
        image held elsewhere — image content itself is never
        held in any shape here, and no capture or OCR occurs."""
        self._guard(actor, "record", "ext_receipt_create")
        report = self._core_report(actor, report_id)
        self._core_item(actor, report_id, item_id)
        _text(receipt_ref, "receipt_ref")
        if not isinstance(sha256_digest, str):
            raise ValidationError("sha256_digest must be a string")
        if sha256_digest and not _DIGEST_RE.match(sha256_digest):
            raise ValidationError(
                "sha256_digest must be a 64-character lowercase hex digest")
        with self._lock:
            receipt = {
                "id": self._next_id("rcp-"),
                "org_id": report["org_id"],
                "report_id": report_id,
                "item_id": item_id,
                "receipt_ref": receipt_ref,
                "sha256_digest": sha256_digest,
                "content_held_here": False,
                "imaged_here": False,
                "ocr_performed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._receipts[receipt["id"]] = receipt
        self._audit(actor, "ext_receipt_create", receipt["id"],
                    {"report_id": report_id, "item_id": item_id})
        return copy.deepcopy(receipt)

    def record_receipt_extraction_report(self, actor, receipt_id,
                                         outcome_label,
                                         extracted_total_cents=None):
        """Record a receipt extraction (OCR) outcome exactly as
        the capture system reported it. Action: record. The
        extracted total, when present, is the capture system's
        reported figure stored verbatim — nothing is extracted
        here and the core line item is unchanged."""
        self._guard(actor, "record", "ext_receipt_report_create")
        if outcome_label not in RECEIPT_OUTCOME_LABELS:
            raise ValidationError(
                "unknown receipt outcome label: %r" % (outcome_label,))
        if extracted_total_cents is not None:
            _money(extracted_total_cents, "extracted_total_cents")
        with self._lock:
            self._get(self._receipts, receipt_id, "receipt")
            report = {
                "id": self._next_id("rcpx-"),
                "receipt_id": receipt_id,
                "outcome_label": outcome_label,
                "extracted_total_cents": extracted_total_cents,
                "extracted_here": False,
                "ocr_performed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._receipt_reports[report["id"]] = report
        self._audit(actor, "ext_receipt_report_create", report["id"],
                    {"receipt_id": receipt_id})
        return copy.deepcopy(report)

    def list_receipts(self, actor, report_id):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._receipts.values()
            if r["report_id"] == report_id
        ]

    def list_receipt_reports(self, actor, receipt_id):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._receipt_reports.values()
            if r["receipt_id"] == receipt_id
        ]

    def receipt_view(self, actor, receipt_id):
        """A receipt record, its extraction reports, and the
        current outcome derived at read from the latest report."""
        self._maybe_require(actor, "read")
        receipt = self._get(self._receipts, receipt_id, "receipt")
        view = copy.deepcopy(receipt)
        reports = self.list_receipt_reports(actor, receipt_id)
        view["reports"] = reports
        view["current_outcome"] = _latest_outcome(reports)
        return view

    # -- integration connector engines (entry 535, reference stub) -------

    def record_connector_reference(self, actor, org_id, integration_id,
                                   engine_label):
        """Record a connector engine for a core integration
        definition, as a labeled reference implementation.
        Action: enter. The core registry holds definitions only
        and never executes; a connector here is likewise a
        record — nothing executes and nothing connects."""
        self._guard(actor, "enter", "ext_connector_reference_create")
        self._core_integration(actor, org_id, integration_id)
        _text(engine_label, "engine_label")
        with self._lock:
            reference = {
                "id": self._next_id("con-"),
                "org_id": org_id,
                "integration_id": integration_id,
                "engine_label": engine_label,
                "reference_stub": True,
                "reference_transport": True,
                "executed_here": False,
                "connected_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._connector_references[reference["id"]] = reference
        self._audit(actor, "ext_connector_reference_create", reference["id"],
                    {"integration_id": integration_id})
        return copy.deepcopy(reference)

    def record_connector_run_report(self, actor, connector_id,
                                    outcome_label, reported_records):
        """Record a connector run outcome exactly as the external
        connector reported it. Action: record. The record count
        is reported data; nothing ran here."""
        self._guard(actor, "record", "ext_connector_report_create")
        if outcome_label not in CONNECTOR_OUTCOME_LABELS:
            raise ValidationError(
                "unknown connector outcome label: %r" % (outcome_label,))
        _count(reported_records, "reported_records")
        with self._lock:
            self._get(self._connector_references, connector_id,
                      "connector reference")
            report = {
                "id": self._next_id("conr-"),
                "connector_id": connector_id,
                "outcome_label": outcome_label,
                "reported_records": reported_records,
                "reference_stub": True,
                "reference_transport": True,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._connector_reports[report["id"]] = report
        self._audit(actor, "ext_connector_report_create", report["id"],
                    {"connector_id": connector_id})
        return copy.deepcopy(report)

    def list_connector_references(self, actor, org_id):
        self._maybe_require(actor, "read")
        self._org(actor, org_id)
        return [
            copy.deepcopy(r) for r in self._connector_references.values()
            if r["org_id"] == org_id
        ]

    def list_connector_run_reports(self, actor, connector_id):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._connector_reports.values()
            if r["connector_id"] == connector_id
        ]

    # -- notification delivery transport (entry 536, built) --------------

    def record_delivery_attempt(self, actor, org_id, notification_id,
                                channel):
        """Record a delivery attempt for a core notification
        record. Action: record. The attempt is a record labeled
        ``reference_transport: True``; nothing is sent or
        delivered here — the core notification stays a record,
        and this surface adds only the transport bookkeeping."""
        self._guard(actor, "record", "ext_delivery_attempt_create")
        self._core_notification(actor, org_id, notification_id)
        if channel not in DELIVERY_CHANNELS:
            raise ValidationError(
                "channel must be one of %r" % (DELIVERY_CHANNELS,))
        with self._lock:
            attempt = {
                "id": self._next_id("dlv-"),
                "org_id": org_id,
                "notification_id": notification_id,
                "channel": channel,
                "reference_transport": True,
                "delivered_here": False,
                "transmitted_here": False,
                "state": "recorded_attempt_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._delivery_attempts[attempt["id"]] = attempt
        self._audit(actor, "ext_delivery_attempt_create", attempt["id"],
                    {"notification_id": notification_id})
        return copy.deepcopy(attempt)

    def record_delivery_report(self, actor, attempt_id, outcome_label):
        """Record a delivery outcome exactly as the transport
        reported it. Action: record. The outcome is reported
        data; nothing was delivered by this build."""
        self._guard(actor, "record", "ext_delivery_report_create")
        if outcome_label not in DELIVERY_OUTCOME_LABELS:
            raise ValidationError(
                "unknown delivery outcome label: %r" % (outcome_label,))
        with self._lock:
            self._get(self._delivery_attempts, attempt_id, "delivery attempt")
            report = {
                "id": self._next_id("dlvr-"),
                "attempt_id": attempt_id,
                "outcome_label": outcome_label,
                "reference_transport": True,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._delivery_reports[report["id"]] = report
        self._audit(actor, "ext_delivery_report_create", report["id"],
                    {"attempt_id": attempt_id})
        return copy.deepcopy(report)

    def list_delivery_attempts(self, actor, notification_id):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(a) for a in self._delivery_attempts.values()
            if a["notification_id"] == notification_id
        ]

    def list_delivery_reports(self, actor, attempt_id):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._delivery_reports.values()
            if r["attempt_id"] == attempt_id
        ]

    def delivery_view(self, actor, attempt_id):
        """A delivery attempt, its reported outcomes, and the
        current outcome derived at read from the latest report."""
        self._maybe_require(actor, "read")
        attempt = self._get(self._delivery_attempts, attempt_id,
                            "delivery attempt")
        view = copy.deepcopy(attempt)
        reports = self.list_delivery_reports(actor, attempt_id)
        view["reports"] = reports
        view["current_outcome"] = _latest_outcome(reports)
        return view

    # -- report generation engine & dashboards (entry 537, built) --------

    def register_report_definition(self, actor, org_id, name,
                                   definition_text):
        """Register a report definition as data. Action: enter.
        The definition text is held verbatim and never executed
        or rendered here; generation is an external system's
        work, recorded through run records."""
        self._guard(actor, "enter", "ext_report_definition_create")
        self._org(actor, org_id)
        _text(name, "name")
        _text(definition_text, "definition_text")
        with self._lock:
            definition = {
                "id": self._next_id("rpt-"),
                "org_id": org_id,
                "name": name,
                "definition_text": definition_text,
                "generated_here": False,
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._report_definitions[definition["id"]] = definition
        self._audit(actor, "ext_report_definition_create", definition["id"],
                    {"org_id": org_id})
        return copy.deepcopy(definition)

    def record_report_run(self, actor, definition_id, outcome_label):
        """Record a report generation run. Action: record. The
        run record is pinned to exactly five keys and stores no
        figures: the figures a run reports are derived at read
        from the core organization summary (see
        :meth:`report_run_view`), so they track registry state.
        The outcome label records whether the external generator
        reported success."""
        self._guard(actor, "record", "ext_report_run_create")
        if outcome_label not in REPORT_RUN_OUTCOME_LABELS:
            raise ValidationError(
                "unknown report run outcome label: %r" % (outcome_label,))
        with self._lock:
            definition = self._get(self._report_definitions, definition_id,
                                   "report definition")
            run = {
                "id": self._next_id("rptr-"),
                "definition_id": definition_id,
                "outcome_label": outcome_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._report_runs[run["id"]] = run
        self._audit(actor, "ext_report_run_create", run["id"],
                    {"definition_id": definition_id})
        return copy.deepcopy(run)

    def get_report_definition(self, actor, definition_id):
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._report_definitions,
                                       definition_id, "report definition"))

    def list_report_definitions(self, actor, org_id):
        self._maybe_require(actor, "read")
        self._org(actor, org_id)
        return [
            copy.deepcopy(d) for d in self._report_definitions.values()
            if d["org_id"] == org_id
        ]

    def list_report_runs(self, actor, definition_id):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(r) for r in self._report_runs.values()
            if r["definition_id"] == definition_id
        ]

    def report_run_view(self, actor, run_id):
        """A run record plus the figures derived at read from
        the core organization summary for the definition's
        organization — computed now, never stored on the run."""
        self._maybe_require(actor, "read")
        run = self._get(self._report_runs, run_id, "report run")
        definition = self._get(self._report_definitions,
                               run["definition_id"], "report definition")
        view = copy.deepcopy(run)
        view["figures"] = self.store.summary(actor, definition["org_id"])
        return view

    def register_dashboard(self, actor, org_id, name, definition_text):
        """Register a dashboard configuration as data. Action:
        enter. The configuration is held verbatim; nothing is
        drawn or rendered here — the dashboard view derives its
        figures from the core organization summary at read."""
        self._guard(actor, "enter", "ext_dashboard_create")
        self._org(actor, org_id)
        _text(name, "name")
        _text(definition_text, "definition_text")
        with self._lock:
            dashboard = {
                "id": self._next_id("dsh-"),
                "org_id": org_id,
                "name": name,
                "definition_text": definition_text,
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._dashboards[dashboard["id"]] = dashboard
        self._audit(actor, "ext_dashboard_create", dashboard["id"],
                    {"org_id": org_id})
        return copy.deepcopy(dashboard)

    def dashboard_view(self, actor, dashboard_id):
        """A dashboard configuration plus the figures derived at
        read from the core organization summary."""
        self._maybe_require(actor, "read")
        dashboard = self._get(self._dashboards, dashboard_id, "dashboard")
        view = copy.deepcopy(dashboard)
        view["figures"] = self.store.summary(actor, dashboard["org_id"])
        return view

    def list_dashboards(self, actor, org_id):
        self._maybe_require(actor, "read")
        self._org(actor, org_id)
        return [
            copy.deepcopy(d) for d in self._dashboards.values()
            if d["org_id"] == org_id
        ]

    # -- identity provider (entry 538, reference stub) -------------------

    def record_identity_reference(self, actor, org_id, provider_ref,
                                  provider_label):
        """Record the external identity provider in use, as a
        labeled reference implementation. Action: enter. Per
        PLATFORM-LAYER.md decision 1, identity proofing,
        authenticator management, and any identity-provider
        service stay with the embedding organization;
        ``identity_provider`` is False and the core's demo
        identities remain hooks, not an IdP."""
        self._guard(actor, "enter", "ext_identity_reference_create")
        self._org(actor, org_id)
        _text(provider_ref, "provider_ref")
        _text(provider_label, "provider_label")
        with self._lock:
            for existing in self._identity_references.values():
                if existing["org_id"] == org_id \
                        and existing["provider_ref"] == provider_ref:
                    raise ValidationError(
                        "provider_ref already exists in this organization: "
                        "%r" % (provider_ref,))
            reference = {
                "id": self._next_id("idr-"),
                "org_id": org_id,
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
                    {"org_id": org_id, "provider_ref": provider_ref})
        return copy.deepcopy(reference)

    def get_identity_reference(self, actor, reference_id):
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._identity_references,
                                       reference_id, "identity reference"))

    def list_identity_references(self, actor, org_id):
        self._maybe_require(actor, "read")
        self._org(actor, org_id)
        return [
            copy.deepcopy(r) for r in self._identity_references.values()
            if r["org_id"] == org_id
        ]
