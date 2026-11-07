"""Final GAPS batch extensions for the Communication L3-adjacent
merged build (Group 14).

Reference-implementation extensions for the 6 Extended entries of
the Group 14 section of GAPS.md (inventory idx 163-168). All six
were drafted ``stub-engine`` and all six close ``reference``: each
names an engine whose substance is execution against systems this
substrate does not hold (workflow execution, encrypted/fax/carrier
transport, CA issuance, voice media and conversation, workspace
streaming and edge delivery, and the carried Group 11 bundle of
detection / inference / archiving / tracking / signature / payment
engines). What ships here is the records surface around those
engines -- definitions, profiles, requests, attempts and reported
outcomes -- every record labeled ``reference_stub: True`` (and
``reference_transport: True`` where the shape is transport), with
the operating half stated absent on the record itself. Full
per-entry dispositions and grounds: ``BATCH.md``.

Design, following the core's doctrines:

- Wrapper around :class:`CommStore`; core modules byte-identical.
  Core records (messages, deliveries, contacts) are read through
  the core store's public API, never re-implemented.
- RBAC goes through :mod:`comm.access`: each extension operation
  maps onto an existing core action, checked *before* any state
  change or id allocation for User-like actors; denied attempts
  are recorded on the core audit log with a ``:denied`` suffix.
  Successful mutations are audited with an ``ext_`` prefix.
- Fail closed (AU-5, the High core's posture): a mutation's audit
  entry is recorded *before* the record is committed; an audit
  write failure leaves the extension store completely unchanged
  and consumes no id.
- All references are opaque ``*_ref`` strings. No record shape in
  this module can hold message content, key material, signature
  bytes, media, or a coordinate: the signatures accept no such
  parameter (a ``content=`` / ``body=`` / ``key_material=`` /
  ``transcript=`` call raises ``TypeError``), and tests pin the
  exact key sets.
- Derived values are derived at read and never stored: workflow
  current outcome, certificate current event and validity state,
  carried payment totals, and the deterministic-counts report
  summary. Stored records carry no derived key; tests pin that.
- Nothing executes against an external system: no workflow runs,
  no cryptography is performed (PLATFORM-LAYER.md decisions 2-3),
  no certificate is issued or deployed, no call is placed, no
  workspace is streamed, no payment is charged or settled, and no
  identity decision is made (decision 1 -- the build ships hooks,
  not an IdP).
"""

import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

TRANSPORT_PROFILE_KINDS = (
    "e2e_message_transport",
    "secure_data_exchange",
    "fax_network",
    "carrier_integration",
)
VOICE_PROFILE_KINDS = (
    "telephony_media",
    "ivr_engine",
    "virtual_agent",
    "mission_critical_voice",
)
DELIVERY_PROFILE_KINDS = (
    "workspace_streaming",
    "remote_experience",
    "edge_delivery",
    "cdn_platform",
)
CERT_EVENT_LABELS = (
    "reported_issued",
    "reported_deployed",
    "reported_renewed",
    "reported_revoked",
    "reported_expired",
)
CARRIED_FAMILIES = (
    "email_security",
    "ai_ml_models",
    "archiving_ediscovery",
    "correspondence_casework",
    "personnel_asset_tracking",
    "permits_passes_surveys",
    "esignature_execution",
    "payment_processing",
    "reporting_analytics",
)
PAYMENT_STATES = (
    "recorded_authorized",
    "recorded_captured",
    "recorded_voided",
    "recorded_refunded",
)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value, what):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 datetime string" % what)
    text = value.strip()
    cand = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(cand)
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO-8601 datetime: %r" % (what, value)) from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % what)
    return value


def _check_int_cents(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be integer cents" % what)
    if value < 0:
        raise ValidationError("%s must be >= 0" % what)
    return value


def _latest_label(records, key):
    """THE batch seam (fresh negative control): the current reported
    label of an append-only record stream is its LATEST record's
    label. Reading the earliest record instead would silently
    resurrect superseded outcomes on every derived view while
    leaving the stored shapes intact. Mutating this seam must fail
    the suite."""
    if not records:
        return None
    return records[-1][key]


class CommExtensions:
    """Extension surface wrapping a CommStore (Group 14 batch)."""

    def __init__(self, store):
        self.store = store
        self.audit = store.audit
        self._lock = threading.RLock()
        self._counters = {}
        self._workflows = {}
        self._workflow_outcomes = {}
        self._transport_profiles = {}
        self._transport_attempts = {}
        self._certificates = {}
        self._cert_events = {}
        self._voice_profiles = {}
        self._voice_reports = {}
        self._delivery_profiles = {}
        self._delivery_reports = {}
        self._carried_refs = {}
        self._carried_reports = {}
        self._carried_payments = {}

    # -- plumbing ---------------------------------------------------

    def _require(self, actor, action):
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
        if hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                if self.audit is not None:
                    self.audit.record(
                        actor_name(actor), "ext_%s:denied" % action, "extensions"
                    )
                raise

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), "ext_" + action, target, details=details)

    def _commit(self, actor, action, prefix, table, record):
        """Audit-before-commit (AU-5): the audit entry is recorded
        before the record is stored; if the audit write raises, the
        record is not stored and no id is consumed."""
        n = self._counters.get(prefix, 0) + 1
        record["id"] = "%s-%d" % (prefix, n)
        self._audit(actor, action, record["id"])
        self._counters[prefix] = n
        table[record["id"]] = record
        return dict(record)

    def _get(self, table, obj_id, what):
        rec = table.get(obj_id)
        if rec is None:
            raise NotFoundError("%s not found: %r" % (what, obj_id))
        return rec

    def _base(self, actor):
        return {"created_by": actor_name(actor), "created_utc": _utc_now()}

    # -- 163 WORKFLOW / BPM ENGINES (reference) ---------------------

    def record_workflow_definition(self, name, steps, actor, channel_kind=None):
        """Workflow definition held as data. The registry never
        executes: no step runs, no approval gates anything (the
        approval-less dispatch substrate remains Core, exactly as
        the entry's own text records)."""
        self._require(actor, "message_compose")
        _non_empty(name, "name")
        if not isinstance(steps, (list, tuple)) or not steps:
            raise ValidationError("steps must be a non-empty list of step labels")
        for step in steps:
            _non_empty(step, "step label")
        if channel_kind is not None:
            _non_empty(channel_kind, "channel_kind")
        with self._lock:
            rec = {"name": name, "steps": list(steps), "channel_kind": channel_kind,
                   "reference_stub": True, "definition_only": True,
                   "executed_here": False, "approvals_enforced_here": False}
            rec.update(self._base(actor))
            return self._commit(actor, "workflow_definition_record",
                                "wfl", self._workflows, rec)

    def record_workflow_outcome(self, workflow_id, outcome_label, actor):
        """Reported outcome record: the outcome is a verbatim label
        reported about an execution that happened elsewhere."""
        self._require(actor, "message_compose")
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._get(self._workflows, workflow_id, "workflow definition")
            rec = {"workflow_id": workflow_id, "outcome_label": outcome_label,
                   "reference_stub": True, "executed_here": False}
            rec.update(self._base(actor))
            return self._commit(actor, "workflow_outcome_record",
                                "woc", self._workflow_outcomes, rec)

    def workflow_view(self, workflow_id, actor):
        self._require(actor, "records_read")
        with self._lock:
            definition = dict(self._get(self._workflows, workflow_id, "workflow definition"))
            outcomes = [dict(r) for r in self._workflow_outcomes.values()
                        if r["workflow_id"] == workflow_id]
            current = _latest_label(outcomes, "outcome_label")
            return {"definition": definition, "outcomes": outcomes,
                    "outcome_count": len(outcomes),
                    "current_outcome": current if current is not None else "unreported"}

    # -- 164 E2E TRANSPORT / FAX / CARRIER (reference) --------------

    def record_transport_profile(self, profile_kind, label, actor):
        """Transport profile declaration. The algorithm, carrier,
        and network are labels only: no cryptography is performed
        (PLATFORM-LAYER.md decisions 2-3), no carrier is connected,
        and nothing is transmitted."""
        self._require(actor, "message_compose")
        if profile_kind not in TRANSPORT_PROFILE_KINDS:
            raise ValidationError(
                "profile_kind must be one of %s" % (", ".join(TRANSPORT_PROFILE_KINDS),))
        _non_empty(label, "label")
        with self._lock:
            rec = {"profile_kind": profile_kind, "label": label,
                   "reference_stub": True, "reference_transport": True,
                   "transmitted_here": False, "cryptography_performed": False,
                   "carrier_connected_here": False}
            rec.update(self._base(actor))
            return self._commit(actor, "transport_profile_record",
                                "trp", self._transport_profiles, rec)

    def record_transport_attempt(self, profile_id, actor, message_id=None):
        """Delivery-attempt record in the adjudicated form: it
        binds a profile to an optional core message and records
        that an attempt was reported. Recording it dispatches
        nothing and changes no core delivery."""
        self._require(actor, "message_compose")
        with self._lock:
            self._get(self._transport_profiles, profile_id, "transport profile")
            if message_id is not None:
                self.store.get_message(message_id, actor)
            rec = {"profile_id": profile_id, "message_id": message_id,
                   "reference_stub": True, "reference_transport": True,
                   "delivered_here": False, "transmitted_here": False}
            rec.update(self._base(actor))
            return self._commit(actor, "transport_attempt_record",
                                "tra", self._transport_attempts, rec)

    # -- 165 KEY & CERTIFICATE LIFECYCLE (reference) ----------------

    def record_certificate(self, subject_ref, issuer_label, not_before, not_after, actor):
        """Certificate metadata record with an exact shape: no
        parameter can carry key material and no cryptography is
        performed. Issuance and deployment are reported events,
        never acts of this build (admin-only, mirroring the core's
        channel-configuration discipline)."""
        self._require(actor, "channel_write")
        _non_empty(subject_ref, "subject_ref")
        _non_empty(issuer_label, "issuer_label")
        nb = _parse_dt(not_before, "not_before")
        na = _parse_dt(not_after, "not_after")
        if na <= nb:
            raise ValidationError("not_after must be after not_before")
        with self._lock:
            rec = {"subject_ref": subject_ref, "issuer_label": issuer_label,
                   "not_before": nb.isoformat(), "not_after": na.isoformat(),
                   "reference_stub": True, "key_material_held": False,
                   "issued_here": False, "deployed_here": False}
            rec.update(self._base(actor))
            return self._commit(actor, "certificate_record",
                                "crt", self._certificates, rec)

    def record_certificate_event(self, certificate_id, event_label, actor):
        """Reported lifecycle event (issuance, deployment, renewal,
        revocation, expiry as reported by the CA / deployment
        layer). The event is a label; nothing is issued, deployed,
        or revoked here."""
        self._require(actor, "channel_write")
        if event_label not in CERT_EVENT_LABELS:
            raise ValidationError(
                "event_label must be one of %s" % (", ".join(CERT_EVENT_LABELS),))
        with self._lock:
            self._get(self._certificates, certificate_id, "certificate")
            rec = {"certificate_id": certificate_id, "event_label": event_label,
                   "reference_stub": True, "issued_here": False, "deployed_here": False}
            rec.update(self._base(actor))
            return self._commit(actor, "certificate_event_record",
                                "cev", self._cert_events, rec)

    def certificate_view(self, certificate_id, actor, at=None):
        self._require(actor, "records_read")
        with self._lock:
            cert = dict(self._get(self._certificates, certificate_id, "certificate"))
            events = [dict(r) for r in self._cert_events.values()
                      if r["certificate_id"] == certificate_id]
            at_dt = _parse_dt(at, "at") if at is not None else datetime.now(timezone.utc)
            nb = _parse_dt(cert["not_before"], "not_before")
            na = _parse_dt(cert["not_after"], "not_after")
            if at_dt < nb:
                validity = "not_yet_valid"
            elif at_dt > na:
                validity = "past_validity"
            else:
                validity = "within_validity"
            current = _latest_label(events, "event_label")
            return {"certificate": cert, "events": events,
                    "event_count": len(events),
                    "current_event": current if current is not None else "none_reported",
                    "validity_state": validity}

    # -- 166 VOICE / IVR / VIRTUAL AGENT (reference) ----------------

    def record_voice_profile(self, profile_kind, label, actor):
        """Voice/conversation engine profile. No media is carried,
        no call is placed, no conversation is performed, and no
        generated text is held: the engine is a labeled stub."""
        self._require(actor, "message_compose")
        if profile_kind not in VOICE_PROFILE_KINDS:
            raise ValidationError(
                "profile_kind must be one of %s" % (", ".join(VOICE_PROFILE_KINDS),))
        _non_empty(label, "label")
        with self._lock:
            rec = {"profile_kind": profile_kind, "label": label,
                   "reference_stub": True, "reference_transport": True,
                   "media_here": False, "calls_placed_here": False,
                   "conversation_performed": False, "generated_text_held": False}
            rec.update(self._base(actor))
            return self._commit(actor, "voice_profile_record",
                                "vcp", self._voice_profiles, rec)

    def record_voice_session_report(self, profile_id, outcome_label, actor, contact_id=None):
        """Reported session outcome: kind and outcome labels are
        stored verbatim as reported by the external engine. An
        optional core contact may be bound (validated, never
        called)."""
        self._require(actor, "message_compose")
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._get(self._voice_profiles, profile_id, "voice profile")
            if contact_id is not None:
                self.store.get_contact(contact_id, actor)
            rec = {"profile_id": profile_id, "contact_id": contact_id,
                   "outcome_label": outcome_label,
                   "reference_stub": True, "reference_transport": True,
                   "media_here": False}
            rec.update(self._base(actor))
            return self._commit(actor, "voice_session_report_record",
                                "vcs", self._voice_reports, rec)

    # -- 167 WORKSPACE STREAMING / EDGE / CDN (reference) -----------

    def record_delivery_profile(self, profile_kind, label, actor):
        """Streaming / edge-delivery profile declaration. Hosting
        and delivery are deployment properties (PLATFORM-LAYER.md
        decision 6): nothing is streamed, hosted, or delivered
        here, and no content is held."""
        self._require(actor, "message_compose")
        if profile_kind not in DELIVERY_PROFILE_KINDS:
            raise ValidationError(
                "profile_kind must be one of %s" % (", ".join(DELIVERY_PROFILE_KINDS),))
        _non_empty(label, "label")
        with self._lock:
            rec = {"profile_kind": profile_kind, "label": label,
                   "reference_stub": True, "streamed_here": False,
                   "hosted_here": False, "delivered_here": False,
                   "content_held": False}
            rec.update(self._base(actor))
            return self._commit(actor, "delivery_profile_record",
                                "dlp", self._delivery_profiles, rec)

    def record_delivery_report(self, profile_id, outcome_label, actor):
        """Reported delivery outcome, verbatim."""
        self._require(actor, "message_compose")
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._get(self._delivery_profiles, profile_id, "delivery profile")
            rec = {"profile_id": profile_id, "outcome_label": outcome_label,
                   "reference_stub": True, "delivered_here": False}
            rec.update(self._base(actor))
            return self._commit(actor, "delivery_report_record",
                                "dlr", self._delivery_reports, rec)

    def delivery_view(self, profile_id, actor):
        self._require(actor, "records_read")
        with self._lock:
            profile = dict(self._get(self._delivery_profiles, profile_id, "delivery profile"))
            reports = [dict(r) for r in self._delivery_reports.values()
                       if r["profile_id"] == profile_id]
            current = _latest_label(reports, "outcome_label")
            return {"profile": profile, "reports": reports,
                    "report_count": len(reports),
                    "current_outcome": current if current is not None else "unreported"}

    # -- 168 CARRIED GROUP 11 BUNDLE (reference) --------------------

    def record_carried_reference(self, family, label, actor):
        """One reference record per carried family. The record
        itself carries the founding fact: these families were
        claimed by 0 of this group's descriptions and are named so
        the union is complete; the engines are not implemented."""
        self._require(actor, "message_compose")
        if family not in CARRIED_FAMILIES:
            raise ValidationError(
                "family must be one of %s" % (", ".join(CARRIED_FAMILIES),))
        _non_empty(label, "label")
        with self._lock:
            rec = {"family": family, "label": label,
                   "reference_stub": True, "claimed_by_descriptions": 0,
                   "implemented_here": False}
            rec.update(self._base(actor))
            return self._commit(actor, "carried_reference_record",
                                "crf", self._carried_refs, rec)

    def record_carried_report(self, carried_id, outcome_label, actor):
        """Reported outcome for a carried family (a detection
        verdict, a signature outcome, a casework state, a tracking
        state -- the label is stored verbatim as reported; nothing
        is detected, signed, tracked, or decided here)."""
        self._require(actor, "message_compose")
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._get(self._carried_refs, carried_id, "carried reference")
            rec = {"carried_id": carried_id, "outcome_label": outcome_label,
                   "reference_stub": True, "performed_here": False}
            rec.update(self._base(actor))
            return self._commit(actor, "carried_report_record",
                                "crr", self._carried_reports, rec)

    def carried_view(self, carried_id, actor):
        self._require(actor, "records_read")
        with self._lock:
            ref = dict(self._get(self._carried_refs, carried_id, "carried reference"))
            reports = [dict(r) for r in self._carried_reports.values()
                       if r["carried_id"] == carried_id]
            current = _latest_label(reports, "outcome_label")
            return {"reference": ref, "reports": reports,
                    "report_count": len(reports),
                    "current_outcome": current if current is not None else "unreported"}

    def record_carried_payment(self, carried_id, amount_cents, state_label, actor):
        """Payment RECORD for the carried payment_processing
        family: integer cents, recorded states only. Nothing is
        charged or settled; totals derive at read."""
        self._require(actor, "message_compose")
        _check_int_cents(amount_cents, "amount_cents")
        if state_label not in PAYMENT_STATES:
            raise ValidationError(
                "state_label must be one of %s" % (", ".join(PAYMENT_STATES),))
        with self._lock:
            ref = self._get(self._carried_refs, carried_id, "carried reference")
            if ref["family"] != "payment_processing":
                raise ValidationError(
                    "payments bind only to a payment_processing carried reference")
            rec = {"carried_id": carried_id, "amount_cents": amount_cents,
                   "state_label": state_label, "reference_stub": True,
                   "charged_here": False, "settled_here": False}
            rec.update(self._base(actor))
            return self._commit(actor, "carried_payment_record",
                                "crp", self._carried_payments, rec)

    def carried_payment_total(self, carried_id, actor):
        """Derived at read, never stored: the recorded total and
        per-state counts for one carried payment reference."""
        self._require(actor, "records_read")
        with self._lock:
            self._get(self._carried_refs, carried_id, "carried reference")
            payments = [r for r in self._carried_payments.values()
                        if r["carried_id"] == carried_id]
            by_state = {}
            for p in payments:
                by_state[p["state_label"]] = by_state.get(p["state_label"], 0) + 1
            return {"carried_id": carried_id,
                    "payment_count": len(payments),
                    "total_cents": sum(p["amount_cents"] for p in payments),
                    "by_state": by_state,
                    "method": "derived_at_read"}

    def extension_report_summary(self, actor):
        """The carried reporting/analytics family's honest form:
        deterministic counts over core + extension records,
        computed at read on every call (``method`` stated). No
        report result is ever stored, no score is computed, and no
        dashboard is rendered."""
        self._require(actor, "records_read")
        with self._lock:
            messages = self.store.list_messages(actor)
            deliveries = self.store.list_deliveries(actor=actor)
            by_status = {}
            for d in deliveries:
                by_status[d["status"]] = by_status.get(d["status"], 0) + 1
            return {
                "method": "deterministic_counts",
                "core": {"messages": len(messages), "deliveries": len(deliveries),
                         "deliveries_by_status": by_status},
                "extensions": {
                    "workflow_definitions": len(self._workflows),
                    "workflow_outcomes": len(self._workflow_outcomes),
                    "transport_profiles": len(self._transport_profiles),
                    "transport_attempts": len(self._transport_attempts),
                    "certificates": len(self._certificates),
                    "certificate_events": len(self._cert_events),
                    "voice_profiles": len(self._voice_profiles),
                    "voice_reports": len(self._voice_reports),
                    "delivery_profiles": len(self._delivery_profiles),
                    "delivery_reports": len(self._delivery_reports),
                    "carried_references": len(self._carried_refs),
                    "carried_reports": len(self._carried_reports),
                    "carried_payments": len(self._carried_payments),
                },
            }
