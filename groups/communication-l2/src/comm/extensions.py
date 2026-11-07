"""Final GAPS batch extensions for the Communication L2 merged build.

Records/derivation extensions for the 12 Extended entries of the
Group 11 section: 4 built as in-substrate records plus deterministic
derivations over the core's own records, 1 (archiving & eDiscovery)
re-judged to a labeled reference implementation on the grounds in
``BATCH.md``, and 7 shipped as labeled reference implementations.

Design, following the core's doctrines:

- Wrapper around :class:`CommStore`; core modules byte-identical.
  Core records (messages, deliveries, contacts) are read through the
  core store's public API, never re-implemented.
- RBAC goes through :mod:`comm.access`: each extension operation maps
  onto an existing core action, checked *before* any state change or
  id allocation for User-like actors; denied attempts are recorded on
  the core audit log with a ``:denied`` suffix. Successful mutations
  are audited with an ``ext_`` prefix.
- All references are opaque ``*_ref`` strings. No record shape in this
  module can hold message content, a location/coordinate, a geofence
  geometry, key material, or signature bytes; tests pin key sets.
- Derived values are derived at read and never stored: disposition
  eligibility, case status, tracking current state, permit status,
  survey tallies, payment totals.
- Nothing executes against an external system: no capture at scale,
  no disposition execution, no FOIA production or release, no
  cryptography (PLATFORM-LAYER.md decisions 2-3), no identity
  decision (decision 1), no media transport, no charge or settlement.
"""

import threading
from datetime import datetime, timedelta, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

CASE_KINDS = ("foia", "grants", "correspondence", "general")
PROOFING_METHODS = ("document_check", "knowledge_check", "biometric_check", "manual_review")
PROOFING_OUTCOMES = ("verified_declared", "not_verified", "escalated")
TRACK_STATES = ("reported_active", "reported_idle", "reported_offline", "reported_unknown")
PERMIT_DECISIONS = ("approve", "deny", "request_information")
PAYMENT_STATES = ("recorded_authorized", "recorded_captured", "recorded_voided", "recorded_refunded")
DISPOSITION_DECISIONS = ("approve", "defer", "reject")
DETECTION_VERDICTS = ("reported_malicious", "reported_suspicious", "reported_benign")
SIGNATURE_OUTCOMES = ("reported_signed", "reported_declined", "reported_expired")


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


def _check_disposition_eligible(capture, policy, holds_active, at_dt):
    """THE batch seam (fresh negative control): a capture is eligible
    for a disposition decision only when its retention window has
    elapsed AND no legal hold is active. Mutating this to ignore
    holds must fail the suite."""
    if holds_active:
        return False
    created = _parse_dt(capture["created_utc"], "created_utc")
    return at_dt >= created + timedelta(days=policy["retention_days"])


class CommExtensions:
    """Extension surface wrapping a CommStore."""

    def __init__(self, store):
        self.store = store
        self.audit = store.audit
        self._lock = threading.RLock()
        self._counters = {}
        self._captures = {}
        self._policies = {}
        self._holds = {}
        self._disp_decisions = {}
        self._foia = {}
        self._cases = {}
        self._exchanges = {}
        self._envelopes = {}
        self._proofing = {}
        self._track_services = {}
        self._assets = {}
        self._track_states = {}
        self._permits = {}
        self._passes = {}
        self._surveys = {}
        self._payments = {}
        self._stub_profiles = {}
        self._stub_reports = {}

    # -- plumbing ---------------------------------------------------
    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _require(self, actor, action):
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
        if hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                if self.audit is not None:
                    self.audit.record(actor_name(actor), "ext_%s:denied" % action, "extensions")
                raise

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), "ext_" + action, target, details=details)

    def _get(self, table, obj_id, what):
        rec = table.get(obj_id)
        if rec is None:
            raise NotFoundError("%s not found: %r" % (what, obj_id))
        return rec

    # -- 117 ARCHIVING & eDISCOVERY (re-judged: reference) ----------
    def record_capture(self, message_ref, channel_kind, checksum_ref, actor):
        """Capture RECORD: metadata + checksum ref only; no content."""
        self._require(actor, "message_compose")
        _non_empty(message_ref, "message_ref"); _non_empty(channel_kind, "channel_kind")
        _non_empty(checksum_ref, "checksum_ref")
        with self._lock:
            cid = self._next_id("arc")
            rec = {"id": cid, "message_ref": message_ref, "channel_kind": channel_kind,
                   "checksum_ref": checksum_ref, "content_held": False,
                   "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._captures[cid] = rec
            self._audit(actor, "capture_record", cid)
            return dict(rec)

    def create_retention_policy(self, name, retention_days, actor):
        self._require(actor, "message_compose")
        _non_empty(name, "name")
        if isinstance(retention_days, bool) or not isinstance(retention_days, int) or retention_days < 0:
            raise ValidationError("retention_days must be a non-negative int")
        with self._lock:
            pid = self._next_id("pol")
            rec = {"id": pid, "name": name, "retention_days": retention_days,
                   "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._policies[pid] = rec
            self._audit(actor, "retention_policy_create", pid)
            return dict(rec)

    def place_legal_hold(self, capture_id, reason_ref, actor):
        self._require(actor, "message_compose")
        _non_empty(reason_ref, "reason_ref")
        with self._lock:
            self._get(self._captures, capture_id, "capture")
            hid = self._next_id("hold")
            rec = {"id": hid, "capture_id": capture_id, "reason_ref": reason_ref,
                   "released_utc": None, "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._holds[hid] = rec
            self._audit(actor, "legal_hold_place", hid)
            return dict(rec)

    def release_legal_hold(self, hold_id, actor):
        self._require(actor, "message_compose")
        with self._lock:
            rec = self._get(self._holds, hold_id, "legal hold")
            if rec["released_utc"] is not None:
                raise ValidationError("hold %r already released" % hold_id)
            rec["released_utc"] = _utc_now()
            self._audit(actor, "legal_hold_release", hold_id)
            return dict(rec)

    def _active_holds(self, capture_id):
        return [h for h in self._holds.values()
                if h["capture_id"] == capture_id and h["released_utc"] is None]

    def disposition_eligibility(self, capture_id, policy_id, actor=None, now=None):
        self._require(actor, "records_read") if actor is not None else None
        with self._lock:
            cap = self._get(self._captures, capture_id, "capture")
            pol = self._get(self._policies, policy_id, "retention policy")
            at = _parse_dt(now, "now") if now is not None else datetime.now(timezone.utc)
            eligible = _check_disposition_eligible(cap, pol, bool(self._active_holds(capture_id)), at)
            return {"capture_id": capture_id, "policy_id": policy_id,
                    "eligible": eligible, "active_holds": len(self._active_holds(capture_id))}

    def record_disposition_decision(self, capture_id, policy_id, decision, actor, now=None, reason=None):
        """Disposition DECISION record only. Execution is the embedding
        organization's records schedule (PLATFORM-LAYER decision 4);
        the capture record is never deleted or altered."""
        self._require(actor, "message_compose")
        if decision not in DISPOSITION_DECISIONS:
            raise ValidationError("decision must be one of %s" % (", ".join(DISPOSITION_DECISIONS),))
        with self._lock:
            view = self.disposition_eligibility(capture_id, policy_id, now=now)
            did = self._next_id("ddec")
            rec = {"id": did, "capture_id": capture_id, "policy_id": policy_id,
                   "decision": decision, "eligible": view["eligible"],
                   "reason": reason, "reference_stub": True,
                   "disposition_executed": False,
                   "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._disp_decisions[did] = rec
            self._audit(actor, "disposition_decision_record", did)
            return dict(rec)

    def record_foia_production(self, case_ref, reported_state, actor):
        """FOIA production as recorded reported states; nothing is
        produced or released here."""
        self._require(actor, "message_compose")
        _non_empty(case_ref, "case_ref"); _non_empty(reported_state, "reported_state")
        with self._lock:
            fid = self._next_id("foia")
            rec = {"id": fid, "case_ref": case_ref, "reported_state": reported_state,
                   "reference_stub": True, "produced_here": False, "released_here": False,
                   "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._foia[fid] = rec
            self._audit(actor, "foia_production_record", fid)
            return dict(rec)

    # -- 118 CORRESPONDENCE / CASEWORK (built) ----------------------
    def open_case(self, case_ref, kind, actor, suspense_at=None):
        self._require(actor, "message_compose")
        _non_empty(case_ref, "case_ref")
        if kind not in CASE_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(CASE_KINDS),))
        if suspense_at is not None:
            _parse_dt(suspense_at, "suspense_at")
        with self._lock:
            cid = self._next_id("case")
            rec = {"id": cid, "case_ref": case_ref, "kind": kind,
                   "suspense_at": suspense_at, "steps": [],
                   "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._cases[cid] = rec
            self._audit(actor, "case_open", cid)
            return self._case_view(rec)

    def record_case_step(self, case_id, step_label, actor):
        self._require(actor, "message_compose")
        _non_empty(step_label, "step_label")
        with self._lock:
            rec = self._get(self._cases, case_id, "case")
            rec["steps"].append({"label": step_label, "recorded_utc": _utc_now(),
                                 "recorded_by": actor_name(actor)})
            self._audit(actor, "case_step_record", case_id)
            return self._case_view(rec)

    def close_case(self, case_id, actor):
        self._require(actor, "message_compose")
        with self._lock:
            rec = self._get(self._cases, case_id, "case")
            if rec.get("closed_utc"):
                raise ValidationError("case %r already closed" % case_id)
            rec["closed_utc"] = _utc_now()
            self._audit(actor, "case_close", case_id)
            return self._case_view(rec)

    def _case_view(self, rec, now=None):
        view = dict(rec)
        view["steps"] = [dict(s) for s in rec["steps"]]
        if rec.get("closed_utc"):
            view["status"] = "closed"
        elif rec.get("suspense_at"):
            at = _parse_dt(now, "now") if now is not None else datetime.now(timezone.utc)
            view["status"] = "overdue" if at > _parse_dt(rec["suspense_at"], "suspense_at") else "open"
        else:
            view["status"] = "open"
        return view

    def get_case(self, case_id, actor=None, now=None):
        if actor is not None:
            self._require(actor, "records_read")
        with self._lock:
            return self._case_view(self._get(self._cases, case_id, "case"), now=now)

    def record_exchange(self, case_id, partner_org_ref, direction, actor):
        """Inter-organization exchange receipt: reference transport."""
        self._require(actor, "dispatch")
        _non_empty(partner_org_ref, "partner_org_ref")
        if direction not in ("outbound", "inbound"):
            raise ValidationError("direction must be outbound or inbound")
        with self._lock:
            self._get(self._cases, case_id, "case")
            xid = self._next_id("xchg")
            rec = {"id": xid, "case_id": case_id, "partner_org_ref": partner_org_ref,
                   "direction": direction, "reference_transport": True,
                   "transmitted_here": False,
                   "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._exchanges[xid] = rec
            self._audit(actor, "exchange_record", xid)
            return dict(rec)

    # -- 120 E2E ENVELOPE + PROOFING (built, records form) ----------
    def record_envelope(self, message_id, algorithm_label, actor):
        """Encrypted-transport envelope record over a core message.
        No cryptography is performed or claimed."""
        self._require(actor, "message_compose")
        _non_empty(algorithm_label, "algorithm_label")
        with self._lock:
            self.store.get_message(message_id, actor)
            eid = self._next_id("env")
            rec = {"id": eid, "message_id": message_id,
                   "algorithm_label": algorithm_label,
                   "reference_transport": True, "transmitted_here": False,
                   "cryptography_performed": False,
                   "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._envelopes[eid] = rec
            self._audit(actor, "envelope_record", eid)
            return dict(rec)

    def open_proofing_case(self, subject_ref, method, actor):
        self._require(actor, "message_compose")
        _non_empty(subject_ref, "subject_ref")
        if method not in PROOFING_METHODS:
            raise ValidationError("method must be one of %s" % (", ".join(PROOFING_METHODS),))
        with self._lock:
            pid = self._next_id("prf")
            rec = {"id": pid, "subject_ref": subject_ref, "method": method,
                   "outcomes": [], "identity_provider": False,
                   "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._proofing[pid] = rec
            self._audit(actor, "proofing_open", pid)
            return self._proofing_view(rec)

    def record_proofing_outcome(self, case_id, outcome, actor):
        """Reported outcome, stored verbatim; never a decision."""
        self._require(actor, "message_compose")
        if outcome not in PROOFING_OUTCOMES:
            raise ValidationError("outcome must be one of %s" % (", ".join(PROOFING_OUTCOMES),))
        with self._lock:
            rec = self._get(self._proofing, case_id, "proofing case")
            rec["outcomes"].append({"outcome": outcome, "recorded_utc": _utc_now(),
                                     "recorded_by": actor_name(actor)})
            self._audit(actor, "proofing_outcome_record", case_id)
            return self._proofing_view(rec)

    def _proofing_view(self, rec):
        view = dict(rec)
        view["outcomes"] = [dict(o) for o in rec["outcomes"]]
        view["current_outcome"] = rec["outcomes"][-1]["outcome"] if rec["outcomes"] else None
        view["decision_made"] = False
        return view

    def get_proofing_case(self, case_id, actor=None):
        if actor is not None:
            self._require(actor, "records_read")
        with self._lock:
            return self._proofing_view(self._get(self._proofing, case_id, "proofing case"))

    # -- 121 TRACKING (built, MDM adjudicated form) -----------------
    def create_track_service(self, service_ref, label, actor):
        self._require(actor, "message_compose")
        _non_empty(service_ref, "service_ref"); _non_empty(label, "label")
        with self._lock:
            sid = self._next_id("trk")
            rec = {"id": sid, "service_ref": service_ref, "label": label,
                   "location_data_held": False,
                   "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._track_services[sid] = rec
            self._audit(actor, "track_service_create", sid)
            return dict(rec)

    def register_tracked_asset(self, service_id, asset_ref, actor):
        self._require(actor, "message_compose")
        _non_empty(asset_ref, "asset_ref")
        with self._lock:
            self._get(self._track_services, service_id, "tracking service")
            aid = self._next_id("ast")
            rec = {"id": aid, "service_id": service_id, "asset_ref": asset_ref,
                   "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._assets[aid] = rec
            self._audit(actor, "tracked_asset_register", aid)
            return dict(rec)

    def record_track_state(self, asset_id, state, actor):
        self._require(actor, "message_compose")
        if state not in TRACK_STATES:
            raise ValidationError("state must be one of %s" % (", ".join(TRACK_STATES),))
        with self._lock:
            self._get(self._assets, asset_id, "tracked asset")
            rid = self._next_id("tst")
            rec = {"id": rid, "asset_id": asset_id, "state": state,
                   "location_data_held": False,
                   "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._track_states[rid] = rec
            self._audit(actor, "track_state_record", rid)
            return dict(rec)

    def tracked_asset_view(self, asset_id, actor=None):
        if actor is not None:
            self._require(actor, "records_read")
        with self._lock:
            asset = dict(self._get(self._assets, asset_id, "tracked asset"))
            states = [s for s in self._track_states.values() if s["asset_id"] == asset_id]
            asset["current_state"] = states[-1]["state"] if states else None
            asset["state_count"] = len(states)
            asset["location_data_held"] = False
            return asset

    # -- 122 PERMITS / PASSES / SURVEYS / PAYMENTS (built) ----------
    def apply_permit(self, applicant_ref, permit_kind, actor):
        self._require(actor, "message_compose")
        _non_empty(applicant_ref, "applicant_ref"); _non_empty(permit_kind, "permit_kind")
        with self._lock:
            pid = self._next_id("pmt")
            rec = {"id": pid, "applicant_ref": applicant_ref, "permit_kind": permit_kind,
                   "decision": None, "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._permits[pid] = rec
            self._audit(actor, "permit_apply", pid)
            return self._permit_view(rec)

    def decide_permit(self, permit_id, decision, actor):
        self._require(actor, "message_compose")
        if decision not in PERMIT_DECISIONS:
            raise ValidationError("decision must be one of %s" % (", ".join(PERMIT_DECISIONS),))
        with self._lock:
            rec = self._get(self._permits, permit_id, "permit")
            if rec["decision"] is not None:
                raise ValidationError("permit %r already decided" % permit_id)
            rec["decision"] = decision
            self._audit(actor, "permit_decide", permit_id)
            return self._permit_view(rec)

    def _permit_view(self, rec):
        view = dict(rec)
        view["status"] = rec["decision"] if rec["decision"] else "pending"
        return view

    def issue_pass(self, permit_id, actor):
        self._require(actor, "message_compose")
        with self._lock:
            rec = self._get(self._permits, permit_id, "permit")
            if rec["decision"] != "approve":
                raise ValidationError("pass requires an approved permit")
            pid = self._next_id("pass")
            pas = {"id": pid, "permit_id": permit_id,
                   "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._passes[pid] = pas
            self._audit(actor, "pass_issue", pid)
            return dict(pas)

    def create_survey(self, title, question_refs, actor):
        self._require(actor, "template_write")
        _non_empty(title, "title")
        if not isinstance(question_refs, (list, tuple)) or not question_refs:
            raise ValidationError("question_refs must be a non-empty list")
        for q in question_refs:
            _non_empty(q, "question_ref")
        with self._lock:
            sid = self._next_id("srv")
            rec = {"id": sid, "title": title, "question_refs": list(question_refs),
                   "responses": [], "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._surveys[sid] = rec
            self._audit(actor, "survey_create", sid)
            return self._survey_view(rec)

    def record_survey_response(self, survey_id, question_ref, value, actor):
        self._require(actor, "message_compose")
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError("survey response value must be an int")
        with self._lock:
            rec = self._get(self._surveys, survey_id, "survey")
            if question_ref not in rec["question_refs"]:
                raise ValidationError("unknown question_ref for survey: %r" % (question_ref,))
            rec["responses"].append({"question_ref": question_ref, "value": value})
            self._audit(actor, "survey_response_record", survey_id)
            return self._survey_view(rec)

    def _survey_view(self, rec):
        view = dict(rec)
        view["responses"] = [dict(r) for r in rec["responses"]]
        tally = {}
        for r in rec["responses"]:
            tally[r["question_ref"]] = tally.get(r["question_ref"], 0) + 1
        view["response_counts"] = tally
        return view

    def record_payment(self, payer_ref, amount_cents, state, actor):
        """Payment RECORD with a recorded state; nothing is charged
        or settled."""
        self._require(actor, "message_compose")
        _non_empty(payer_ref, "payer_ref")
        _check_int_cents(amount_cents, "amount_cents")
        if state not in PAYMENT_STATES:
            raise ValidationError("state must be one of %s" % (", ".join(PAYMENT_STATES),))
        with self._lock:
            pid = self._next_id("pay")
            rec = {"id": pid, "payer_ref": payer_ref, "amount_cents": amount_cents,
                   "state": state, "charged_here": False, "settled_here": False,
                   "created_by": actor_name(actor), "created_utc": _utc_now()}
            self._payments[pid] = rec
            self._audit(actor, "payment_record", pid)
            return dict(rec)

    def payment_totals(self, actor=None):
        if actor is not None:
            self._require(actor, "records_read")
        with self._lock:
            totals = {}
            for p in self._payments.values():
                totals[p["state"]] = totals.get(p["state"], 0) + p["amount_cents"]
            return {"totals_by_state": totals, "count": len(self._payments)}

    # -- STUB-ENGINE families (113,114,115,116,119,123,124) ---------
    def register_stub_profile(self, family, name, actor, **extra):
        """Generic labeled reference profile. Extra kwargs are refused
        by signature discipline in the family wrappers below."""
        self._require(actor, "message_compose")
        _non_empty(name, "name")
        with self._lock:
            pid = self._next_id("stub")
            rec = {"id": pid, "family": family, "name": name,
                   "reference_stub": True, "executed_here": False,
                   "created_by": actor_name(actor), "created_utc": _utc_now()}
            rec.update(extra)
            self._stub_profiles[pid] = rec
            self._audit(actor, "stub_profile_register", pid)
            return dict(rec)

    def record_stub_report(self, profile_id, reported, actor):
        self._require(actor, "message_compose")
        _non_empty(reported, "reported")
        with self._lock:
            prof = self._get(self._stub_profiles, profile_id, "stub profile")
            rid = self._next_id("srep")
            rec = {"id": rid, "profile_id": profile_id, "family": prof["family"],
                   "reported": reported, "reference_stub": True,
                   "executed_here": False,
                   "created_by": actor_name(actor), "created_utc": _utc_now()}
            if prof["family"] in ("voice_telephony", "video_media"):
                rec["reference_transport"] = True
                rec["media_here"] = False
            self._stub_reports[rid] = rec
            self._audit(actor, "stub_report_record", rid)
            return dict(rec)

    # Family wrappers (each pins its family's labels):
    def register_email_security_profile(self, name, actor):
        return self.register_stub_profile("email_security", name, actor,
                                          detection_performed=False, quarantined_here=False)

    def record_detection_report(self, profile_id, verdict, actor):
        if verdict not in DETECTION_VERDICTS:
            raise ValidationError("verdict must be one of %s" % (", ".join(DETECTION_VERDICTS),))
        return self.record_stub_report(profile_id, verdict, actor)

    def register_assistant_profile(self, name, actor):
        return self.register_stub_profile("ai_assistant", name, actor,
                                          inference_here=False, generated_text_held=False)

    def register_telephony_profile(self, name, actor):
        return self.register_stub_profile("voice_telephony", name, actor,
                                          media_here=False)

    def register_video_profile(self, name, actor):
        return self.register_stub_profile("video_media", name, actor,
                                          media_here=False, claimed_by_descriptions=0)

    def register_certificate_record(self, subject_ref, issuer_label, actor):
        """Certificate metadata record: exact shape, no key material
        parameter exists."""
        self._require(actor, "message_compose")
        _non_empty(subject_ref, "subject_ref"); _non_empty(issuer_label, "issuer_label")
        return self.register_stub_profile("key_certificate", subject_ref, actor,
                                          issuer_label=issuer_label,
                                          issued_here=False, key_material_held=False)

    def register_signature_request(self, document_ref, signer_ref, actor):
        """E-signature request record: exact shape, no signature bytes
        can be held."""
        self._require(actor, "message_compose")
        _non_empty(document_ref, "document_ref"); _non_empty(signer_ref, "signer_ref")
        return self.register_stub_profile("esignature", document_ref, actor,
                                          signer_ref=signer_ref, signed_here=False)

    def record_signature_outcome(self, profile_id, outcome, actor):
        if outcome not in SIGNATURE_OUTCOMES:
            raise ValidationError("outcome must be one of %s" % (", ".join(SIGNATURE_OUTCOMES),))
        return self.record_stub_report(profile_id, outcome, actor)

    def register_workflow_definition(self, name, definition, actor):
        """Workflow definition copied as data; never executes and
        changes no core record (registry-never-executes)."""
        self._require(actor, "template_write")
        if not isinstance(definition, dict):
            raise ValidationError("definition must be a dict")
        prof = self.register_stub_profile("workflow_reporting", name, actor)
        with self._lock:
            self._stub_profiles[prof["id"]]["definition"] = dict(definition)
            return dict(self._stub_profiles[prof["id"]])

    def report_summary(self, actor=None):
        """Deterministic counts over core + extension records."""
        if actor is not None:
            self._require(actor, "records_read")
        with self._lock:
            messages = self.store.list_messages(actor)
            return {"core_messages": len(messages),
                    "captures": len(self._captures), "cases": len(self._cases),
                    "envelopes": len(self._envelopes), "payments": len(self._payments),
                    "stub_profiles": len(self._stub_profiles),
                    "method": "deterministic_counts"}
