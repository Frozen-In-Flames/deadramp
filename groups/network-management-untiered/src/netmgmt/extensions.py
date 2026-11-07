"""Final GAPS batch extensions — Untiered Set 19, Network Management.

Eight gap entries from this set's union spec, closed over the
founding records substrate (see ``BATCH.md`` for the per-entry
dispositions). This module is new code; every founding module in
this package is byte-identical to its pre-batch state.

The discipline is the substrate's discipline, extended:

- **Records only.** Nothing here authenticates a user, issues a
  certificate, detects a threat, serves a portal, provisions a
  terminal, locates an asset, schedules a GPU, pushes a
  configuration, or polls a device. Callers *report* outcomes;
  the build records the reports. Surfaces whose substance is a
  running engine over an external system carry
  ``reference_stub: True`` and an ``*_here: False`` flag naming
  what does not happen here.
- **Derived, never stored.** Lifecycle states (certificate,
  guest-access window, incident, terminal, GPU job) are derived
  at read from the recorded event/outcome stream by a single
  seam each; the stored records carry no state key.
- **No live-network identifiers, no coordinates.** No record
  shape has a field for an IP address, a MAC address, a serial
  number, a credential, or a geographic coordinate. References
  are opaque and caller-chosen; fleet positions are coarse
  caller-chosen region labels, never coordinates — there is no
  parameter that could accept one.
- **Tier null binds.** No record or view carries a tier, a
  baseline, or an equivalence key; nothing computes a score.
- **Access discipline.** Every operation checks the core role
  matrix (``netmgmt.access``) and organization membership through
  the core store before any state change or id allocation.
  Denied attempts are recorded on the core audit log as
  ``ext_<action>:denied``; successful mutations as ``ext_<action>``.
  Failed operations consume no id and change nothing.
"""

import threading

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import _parse_iso, _text, _utc_now

AUTH_METHODS = ("eap_tls", "eap_ttls", "peap", "mac_auth", "other")
AUTH_OUTCOMES = ("authenticated", "rejected", "failed")
CERT_EVENT_KINDS = ("issued", "renewed", "revoked", "expired",
                    "suspended", "reinstated")
ITDR_KINDS = ("credential_misuse", "anomalous_access", "rogue_client",
              "certificate_anomaly", "other")
ITDR_SEVERITY_LABELS = ("low", "medium", "high", "critical")
GUEST_ACCESS_KINDS = ("voucher", "sponsored", "open_roaming",
                      "portal_self_register")
TERMINAL_OUTCOMES = ("provisioned", "activated", "deactivated",
                     "failed", "suspended")
LINK_KINDS = ("connected_to", "managed_with", "located_with", "other")
INCIDENT_EVENT_KINDS = ("acknowledged", "escalated", "mitigated",
                        "resolved", "closed", "reopened", "note")
INCIDENT_STATES = ("opened", "acknowledged", "escalated", "mitigated",
                   "resolved", "closed", "reopened")
GPU_OUTCOMES = ("scheduled", "running", "completed", "failed",
                "cancelled")


def _count(value, field):
    """Validate a non-negative integer count; bools/floats rejected."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be a non-negative integer" % field)
    return value


def _iso_text(value, field):
    """Validate an ISO-8601 timestamp supplied as a string.

    Stored verbatim (the core telemetry discipline); parsing is
    validation only. Returns the parsed datetime for ordering.
    """
    if not isinstance(value, str):
        raise ValidationError("%s must be an ISO-8601 string" % field)
    return _parse_iso(value, field)


def _public(record):
    """A copy of a stored record with internal ordering keys removed."""
    return {key: value for key, value in record.items()
            if not key.startswith("_")}


class NetmgmtExtensions:
    """GAPS-batch extension surface wrapping a core NetmgmtStore."""

    def __init__(self, store):
        self._store = store
        self._lock = threading.Lock()
        self._counters = {}
        self._seq = 0
        self._auth_events = {}
        self._certificates = {}
        self._certificate_events = {}
        self._itdr_findings = {}
        self._guest_access = {}
        self._terminals = {}
        self._terminal_outcomes = {}
        self._positions = {}
        self._links = {}
        self._incidents = {}
        self._incident_events = {}
        self._gpu_jobs = {}
        self._gpu_outcomes = {}

    # -- internal helpers -------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _next_seq(self):
        self._seq += 1
        return self._seq

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self._store, "audit", None)
        if audit is not None:
            audit.record(actor, action, target, details)

    def _scoped(self, actor, org_id, action, audit_action):
        """Role check + org lookup + membership check, in that order.

        Mirrors the core store's ``_scoped``; a permission denial
        is recorded on the audit log as ``ext_<action>:denied``
        before the error propagates.
        """
        try:
            require(actor, action)
            org = self._store.get_organization(actor, org_id)
        except PermissionDenied:
            self._audit(actor, "ext_%s:denied" % audit_action, org_id, {})
            raise
        return org

    def _check_network_link(self, actor, org_id, network_id):
        if network_id is None:
            return
        network = self._store.get_network(actor, network_id)
        if network["org_id"] != org_id:
            raise ValidationError("network belongs to another organization")

    def _check_device_link(self, actor, org_id, device_id):
        if device_id is None:
            return
        device = self._store.get_device(actor, device_id)
        if device["org_id"] != org_id:
            raise ValidationError("device belongs to another organization")

    @staticmethod
    def _ordered(records):
        """Records in reported-time order (creation order breaks ties)."""
        return sorted(records,
                      key=lambda r: (r["_occurred_dt"], r["_seq"]))

    # -- 921: network access authentication records -------------------------
    # The RADIUS / 802.1X engine itself authenticates against live
    # supplicants and identity stores; that engine is not built.
    # What is built is the records surface of reported outcomes:
    # one record per authentication outcome a caller reports, over
    # the substrate's own networks and devices. The build
    # authenticates no one (``authenticated_here`` is False on
    # every record) and no credential can be recorded — there is
    # no parameter that could accept one.

    def record_auth_event(self, actor, org_id, method, outcome,
                          subject_ref, occurred_utc, network_id=None,
                          device_id=None):
        """Record one reported network-access authentication outcome.

        ``subject_ref`` is the caller's opaque reference for the
        authenticating identity; ``method`` and ``outcome`` are
        the reported values, stored verbatim. The outcome is the
        caller's report — this build performed no authentication.
        """
        self._scoped(actor, org_id, "record", "auth_event_create")
        if method not in AUTH_METHODS:
            raise ValidationError("method must be one of %r" % (AUTH_METHODS,))
        if outcome not in AUTH_OUTCOMES:
            raise ValidationError(
                "outcome must be one of %r" % (AUTH_OUTCOMES,))
        _text(subject_ref, "subject_ref")
        occurred_dt = _iso_text(occurred_utc, "occurred_utc")
        self._check_network_link(actor, org_id, network_id)
        self._check_device_link(actor, org_id, device_id)
        with self._lock:
            record = {
                "id": self._mint("aev-"),
                "org_id": org_id,
                "network_id": network_id,
                "device_id": device_id,
                "method": method,
                "outcome": outcome,
                "subject_ref": subject_ref,
                "occurred_utc": occurred_utc,
                "authenticated_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "_occurred_dt": occurred_dt,
                "_seq": self._next_seq(),
            }
            self._auth_events[record["id"]] = record
        self._audit(actor, "ext_auth_event_create", record["id"],
                    {"method": method, "outcome": outcome})
        return _public(record)

    def list_auth_events(self, actor, org_id):
        self._scoped(actor, org_id, "read", "auth_event_list")
        return [_public(r) for r in self._ordered(
            [r for r in self._auth_events.values()
             if r["org_id"] == org_id])]

    def auth_summary(self, actor, org_id):
        """Counts of reported authentication outcomes. Counts only."""
        self._scoped(actor, org_id, "read", "auth_summary")
        by_method = {method: 0 for method in AUTH_METHODS}
        by_outcome = {outcome: 0 for outcome in AUTH_OUTCOMES}
        total = 0
        for record in self._auth_events.values():
            if record["org_id"] != org_id:
                continue
            by_method[record["method"]] += 1
            by_outcome[record["outcome"]] += 1
            total += 1
        return {"org_id": org_id, "total": total,
                "by_method": by_method, "by_outcome": by_outcome}

    # -- 922: cloud PKI & certificate lifecycle (reference) -----------------
    # Issuance and renewal over SCEP are a running PKI's work.
    # This surface registers certificates as reported by the
    # external PKI and records their reported lifecycle events;
    # it issues, renews, and revokes nothing (``issued_here`` /
    # ``executed_here`` False, ``reference_stub`` True throughout).
    # The reported lifecycle state is derived at read from the
    # event stream and never stored.

    def register_certificate(self, actor, org_id, certificate_ref,
                             subject_ref, issuer_ref, not_before_utc,
                             not_after_utc, device_id=None):
        """Register one certificate as reported by an external PKI."""
        self._scoped(actor, org_id, "enter", "certificate_create")
        _text(certificate_ref, "certificate_ref")
        _text(subject_ref, "subject_ref")
        _text(issuer_ref, "issuer_ref")
        not_before_dt = _iso_text(not_before_utc, "not_before_utc")
        not_after_dt = _iso_text(not_after_utc, "not_after_utc")
        if not_after_dt <= not_before_dt:
            raise ValidationError(
                "not_after_utc must be after not_before_utc")
        self._check_device_link(actor, org_id, device_id)
        with self._lock:
            for existing in self._certificates.values():
                if (existing["org_id"] == org_id
                        and existing["certificate_ref"] == certificate_ref):
                    raise ValidationError(
                        "certificate ref already exists in this "
                        "organization: %r" % (certificate_ref,))
            record = {
                "id": self._mint("crt-"),
                "org_id": org_id,
                "device_id": device_id,
                "certificate_ref": certificate_ref,
                "subject_ref": subject_ref,
                "issuer_ref": issuer_ref,
                "not_before_utc": not_before_utc,
                "not_after_utc": not_after_utc,
                "reference_stub": True,
                "issued_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "_seq": self._next_seq(),
            }
            self._certificates[record["id"]] = record
        self._audit(actor, "ext_certificate_create", record["id"],
                    {"certificate_ref": certificate_ref})
        return _public(record)

    def _certificate(self, certificate_id):
        record = self._certificates.get(certificate_id)
        if record is None:
            raise NotFoundError(
                "no such certificate: %r" % (certificate_id,))
        return record

    def record_certificate_event(self, actor, org_id, certificate_id,
                                 event_kind, occurred_utc, note_ref=None):
        """Record one reported certificate lifecycle event."""
        certificate = self._certificate(certificate_id)
        self._scoped(actor, org_id, "record", "certificate_event_create")
        if certificate["org_id"] != org_id:
            raise ValidationError(
                "certificate belongs to another organization")
        if event_kind not in CERT_EVENT_KINDS:
            raise ValidationError(
                "event_kind must be one of %r" % (CERT_EVENT_KINDS,))
        occurred_dt = _iso_text(occurred_utc, "occurred_utc")
        if note_ref is not None:
            _text(note_ref, "note_ref")
        with self._lock:
            record = {
                "id": self._mint("cev-"),
                "org_id": org_id,
                "certificate_id": certificate_id,
                "event_kind": event_kind,
                "occurred_utc": occurred_utc,
                "note_ref": note_ref,
                "reference_stub": True,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "_occurred_dt": occurred_dt,
                "_seq": self._next_seq(),
            }
            self._certificate_events[record["id"]] = record
        self._audit(actor, "ext_certificate_event_create", record["id"],
                    {"certificate_id": certificate_id,
                     "event_kind": event_kind})
        return _public(record)

    def _derive_cert_state(self, events):
        """The reported lifecycle state of one certificate.

        The kind of the latest reported lifecycle event, or
        ``registered`` when no event has been reported. Derived
        at read; never stored on the certificate record.
        """
        if not events:
            return "registered"
        return self._ordered(events)[-1]["event_kind"]

    def _certificate_view(self, record):
        view = _public(record)
        events = [e for e in self._certificate_events.values()
                  if e["certificate_id"] == record["id"]]
        view["reported_lifecycle_state"] = self._derive_cert_state(events)
        return view

    def get_certificate(self, actor, certificate_id):
        record = self._certificate(certificate_id)
        self._scoped(actor, record["org_id"], "read", "certificate_get")
        return self._certificate_view(record)

    def list_certificates(self, actor, org_id):
        self._scoped(actor, org_id, "read", "certificate_list")
        return [self._certificate_view(r)
                for r in self._certificates.values()
                if r["org_id"] == org_id]

    # -- 923: Wi-Fi identity threat detection (reference) -------------------
    # A verdict that an access pattern is credential misuse or an
    # anomaly is a running detector's work. This surface records
    # findings *reported* by an external detector: the severity
    # label is the reporter's, stored verbatim, and the build
    # computes no severity and renders no verdict
    # (``detected_here`` False, ``reference_stub`` True).

    def record_itdr_finding(self, actor, org_id, finding_kind,
                            severity_label, subject_ref, reported_utc,
                            network_id=None, device_id=None,
                            detail_ref=None):
        """Record one threat-detection finding reported by a detector."""
        self._scoped(actor, org_id, "record", "itdr_finding_create")
        if finding_kind not in ITDR_KINDS:
            raise ValidationError(
                "finding_kind must be one of %r" % (ITDR_KINDS,))
        if severity_label not in ITDR_SEVERITY_LABELS:
            raise ValidationError(
                "severity_label must be one of %r"
                % (ITDR_SEVERITY_LABELS,))
        _text(subject_ref, "subject_ref")
        reported_dt = _iso_text(reported_utc, "reported_utc")
        if detail_ref is not None:
            _text(detail_ref, "detail_ref")
        self._check_network_link(actor, org_id, network_id)
        self._check_device_link(actor, org_id, device_id)
        with self._lock:
            record = {
                "id": self._mint("itd-"),
                "org_id": org_id,
                "network_id": network_id,
                "device_id": device_id,
                "finding_kind": finding_kind,
                "severity_label": severity_label,
                "subject_ref": subject_ref,
                "detail_ref": detail_ref,
                "reported_utc": reported_utc,
                "reference_stub": True,
                "detected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "_occurred_dt": reported_dt,
                "_seq": self._next_seq(),
            }
            self._itdr_findings[record["id"]] = record
        self._audit(actor, "ext_itdr_finding_create", record["id"],
                    {"finding_kind": finding_kind})
        return _public(record)

    def list_itdr_findings(self, actor, org_id):
        self._scoped(actor, org_id, "read", "itdr_finding_list")
        return [_public(r) for r in self._ordered(
            [r for r in self._itdr_findings.values()
             if r["org_id"] == org_id])]

    def itdr_summary(self, actor, org_id):
        """Counts of reported findings, by kind and reported label."""
        self._scoped(actor, org_id, "read", "itdr_summary")
        by_kind = {kind: 0 for kind in ITDR_KINDS}
        by_severity_label = {label: 0 for label in ITDR_SEVERITY_LABELS}
        total = 0
        for record in self._itdr_findings.values():
            if record["org_id"] != org_id:
                continue
            by_kind[record["finding_kind"]] += 1
            by_severity_label[record["severity_label"]] += 1
            total += 1
        return {"org_id": org_id, "total": total, "by_kind": by_kind,
                "by_severity_label": by_severity_label}

    # -- 924: captive portal & guest / roaming access records ----------------
    # The records surface of guest access: grants a caller
    # registers against a network (voucher, sponsored,
    # open-roaming, portal self-registration), each with its
    # validity window. The build serves no portal and admits no
    # guest (``portal_served_here`` / ``admitted_here`` False);
    # a grant's window state is derived at read, never stored.

    def create_guest_access(self, actor, org_id, network_id, access_kind,
                            sponsor_ref, valid_from_utc, valid_until_utc,
                            voucher_ref=None, guest_ref=None):
        """Register one guest / roaming access grant against a network."""
        self._scoped(actor, org_id, "enter", "guest_access_create")
        network = self._store.get_network(actor, network_id)
        if network["org_id"] != org_id:
            raise ValidationError("network belongs to another organization")
        if access_kind not in GUEST_ACCESS_KINDS:
            raise ValidationError(
                "access_kind must be one of %r" % (GUEST_ACCESS_KINDS,))
        _text(sponsor_ref, "sponsor_ref")
        from_dt = _iso_text(valid_from_utc, "valid_from_utc")
        until_dt = _iso_text(valid_until_utc, "valid_until_utc")
        if until_dt <= from_dt:
            raise ValidationError(
                "valid_until_utc must be after valid_from_utc")
        if voucher_ref is not None:
            _text(voucher_ref, "voucher_ref")
        if guest_ref is not None:
            _text(guest_ref, "guest_ref")
        with self._lock:
            record = {
                "id": self._mint("gst-"),
                "org_id": org_id,
                "network_id": network_id,
                "access_kind": access_kind,
                "sponsor_ref": sponsor_ref,
                "guest_ref": guest_ref,
                "voucher_ref": voucher_ref,
                "valid_from_utc": valid_from_utc,
                "valid_until_utc": valid_until_utc,
                "portal_served_here": False,
                "admitted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "_from_dt": from_dt,
                "_until_dt": until_dt,
                "_seq": self._next_seq(),
            }
            self._guest_access[record["id"]] = record
        self._audit(actor, "ext_guest_access_create", record["id"],
                    {"access_kind": access_kind})
        return _public(record)

    def _guest_grant(self, grant_id):
        record = self._guest_access.get(grant_id)
        if record is None:
            raise NotFoundError("no such guest access grant: %r" % (grant_id,))
        return record

    @staticmethod
    def _derive_guest_state(record, as_of_dt):
        """A grant's window state at ``as_of_dt``.

        ``scheduled`` before the window opens, ``active`` inside
        it (both bounds inclusive), ``expired`` after it closes.
        Derived at read; never stored.
        """
        if as_of_dt < record["_from_dt"]:
            return "scheduled"
        if as_of_dt > record["_until_dt"]:
            return "expired"
        return "active"

    def _guest_view(self, record, as_of=None):
        view = _public(record)
        if as_of is None:
            as_of_dt = _utc_now()
        else:
            as_of_dt = _parse_iso(as_of, "as_of")
        view["derived_state"] = self._derive_guest_state(record, as_of_dt)
        return view

    def get_guest_access(self, actor, grant_id, as_of=None):
        record = self._guest_grant(grant_id)
        self._scoped(actor, record["org_id"], "read", "guest_access_get")
        return self._guest_view(record, as_of=as_of)

    def list_guest_access(self, actor, org_id, as_of=None):
        self._scoped(actor, org_id, "read", "guest_access_list")
        return [self._guest_view(r, as_of=as_of)
                for r in self._guest_access.values()
                if r["org_id"] == org_id]

    # -- 925: satellite terminal provisioning (reference) --------------------
    # Provisioning and connecting a live satellite terminal is
    # the fork's platform work against real hardware. This
    # surface registers provisioning requests as records and the
    # outcomes callers report; it provisions and connects
    # nothing (``provisioned_here`` / ``connected_here`` False,
    # ``reference_stub`` True). The reported state derives at
    # read from the outcome stream.

    def register_terminal_provisioning(self, actor, org_id, terminal_ref,
                                       network_id=None, plan_ref=None):
        """Register one satellite terminal provisioning record."""
        self._scoped(actor, org_id, "enter", "terminal_create")
        _text(terminal_ref, "terminal_ref")
        if plan_ref is not None:
            _text(plan_ref, "plan_ref")
        self._check_network_link(actor, org_id, network_id)
        with self._lock:
            for existing in self._terminals.values():
                if (existing["org_id"] == org_id
                        and existing["terminal_ref"] == terminal_ref):
                    raise ValidationError(
                        "terminal ref already exists in this "
                        "organization: %r" % (terminal_ref,))
            record = {
                "id": self._mint("trm-"),
                "org_id": org_id,
                "network_id": network_id,
                "terminal_ref": terminal_ref,
                "plan_ref": plan_ref,
                "reference_stub": True,
                "provisioned_here": False,
                "connected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "_seq": self._next_seq(),
            }
            self._terminals[record["id"]] = record
        self._audit(actor, "ext_terminal_create", record["id"],
                    {"terminal_ref": terminal_ref})
        return _public(record)

    def _terminal(self, terminal_id):
        record = self._terminals.get(terminal_id)
        if record is None:
            raise NotFoundError("no such terminal: %r" % (terminal_id,))
        return record

    def record_terminal_outcome(self, actor, org_id, terminal_id, outcome,
                                reported_utc, detail_ref=None):
        """Record one provisioning/connectivity outcome as reported."""
        terminal = self._terminal(terminal_id)
        self._scoped(actor, org_id, "record", "terminal_outcome_create")
        if terminal["org_id"] != org_id:
            raise ValidationError(
                "terminal belongs to another organization")
        if outcome not in TERMINAL_OUTCOMES:
            raise ValidationError(
                "outcome must be one of %r" % (TERMINAL_OUTCOMES,))
        reported_dt = _iso_text(reported_utc, "reported_utc")
        if detail_ref is not None:
            _text(detail_ref, "detail_ref")
        with self._lock:
            record = {
                "id": self._mint("tro-"),
                "org_id": org_id,
                "terminal_id": terminal_id,
                "outcome": outcome,
                "reported_utc": reported_utc,
                "detail_ref": detail_ref,
                "reference_stub": True,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "_occurred_dt": reported_dt,
                "_seq": self._next_seq(),
            }
            self._terminal_outcomes[record["id"]] = record
        self._audit(actor, "ext_terminal_outcome_create", record["id"],
                    {"terminal_id": terminal_id, "outcome": outcome})
        return _public(record)

    @staticmethod
    def _latest_outcome_label(records, field):
        """The latest reported outcome label, or ``registered``."""
        if not records:
            return "registered"
        ordered = sorted(records,
                         key=lambda r: (r["_occurred_dt"], r["_seq"]))
        return ordered[-1][field]

    def _terminal_view(self, record):
        view = _public(record)
        outcomes = [o for o in self._terminal_outcomes.values()
                    if o["terminal_id"] == record["id"]]
        view["reported_state"] = self._latest_outcome_label(
            outcomes, "outcome")
        return view

    def get_terminal_provisioning(self, actor, terminal_id):
        record = self._terminal(terminal_id)
        self._scoped(actor, record["org_id"], "read", "terminal_get")
        return self._terminal_view(record)

    def list_terminal_provisionings(self, actor, org_id):
        self._scoped(actor, org_id, "read", "terminal_list")
        return [self._terminal_view(r)
                for r in self._terminals.values()
                if r["org_id"] == org_id]

    # -- 926: fleet mapping & geospatial awareness (reference) ---------------
    # A map of live assets is a geospatial platform's work, and a
    # position is a sensed fact. This surface records position
    # *reports*: each names an asset by opaque reference and a
    # coarse caller-chosen region label — never a coordinate;
    # there is no parameter that could accept one — plus recorded
    # links between references. The fleet view is counts and
    # link degrees derived at read. Nothing is located, sensed,
    # or mapped here (``located_here`` / ``mapped_here`` False,
    # ``reference_stub`` True).

    def record_asset_position(self, actor, org_id, asset_ref, region_ref,
                              reported_utc, device_id=None):
        """Record one reported asset position (a region label only)."""
        self._scoped(actor, org_id, "record", "asset_position_create")
        _text(asset_ref, "asset_ref")
        _text(region_ref, "region_ref")
        reported_dt = _iso_text(reported_utc, "reported_utc")
        self._check_device_link(actor, org_id, device_id)
        with self._lock:
            record = {
                "id": self._mint("pos-"),
                "org_id": org_id,
                "device_id": device_id,
                "asset_ref": asset_ref,
                "region_ref": region_ref,
                "reported_utc": reported_utc,
                "reference_stub": True,
                "located_here": False,
                "mapped_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "_occurred_dt": reported_dt,
                "_seq": self._next_seq(),
            }
            self._positions[record["id"]] = record
        self._audit(actor, "ext_asset_position_create", record["id"],
                    {"asset_ref": asset_ref})
        return _public(record)

    def record_asset_link(self, actor, org_id, source_ref, target_ref,
                          link_kind, reported_utc):
        """Record one reported link between two opaque references."""
        self._scoped(actor, org_id, "enter", "asset_link_create")
        _text(source_ref, "source_ref")
        _text(target_ref, "target_ref")
        if source_ref == target_ref:
            raise ValidationError("a link's endpoints must differ")
        if link_kind not in LINK_KINDS:
            raise ValidationError(
                "link_kind must be one of %r" % (LINK_KINDS,))
        reported_dt = _iso_text(reported_utc, "reported_utc")
        with self._lock:
            record = {
                "id": self._mint("lnk-"),
                "org_id": org_id,
                "source_ref": source_ref,
                "target_ref": target_ref,
                "link_kind": link_kind,
                "reported_utc": reported_utc,
                "reference_stub": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "_occurred_dt": reported_dt,
                "_seq": self._next_seq(),
            }
            self._links[record["id"]] = record
        self._audit(actor, "ext_asset_link_create", record["id"],
                    {"link_kind": link_kind})
        return _public(record)

    def list_asset_positions(self, actor, org_id):
        self._scoped(actor, org_id, "read", "asset_position_list")
        return [_public(r) for r in self._ordered(
            [r for r in self._positions.values()
             if r["org_id"] == org_id])]

    def list_asset_links(self, actor, org_id):
        self._scoped(actor, org_id, "read", "asset_link_list")
        return [_public(r) for r in self._ordered(
            [r for r in self._links.values() if r["org_id"] == org_id])]

    @staticmethod
    def _link_degrees(links):
        """In-plus-out degree per reference, over recorded links."""
        degrees = {}
        for link in links:
            for ref in (link["source_ref"], link["target_ref"]):
                degrees[ref] = degrees.get(ref, 0) + 1
        return degrees

    def fleet_view(self, actor, org_id):
        """Counts over reported positions and links. Counts only."""
        self._scoped(actor, org_id, "read", "fleet_view")
        positions = [r for r in self._positions.values()
                     if r["org_id"] == org_id]
        links = [r for r in self._links.values()
                 if r["org_id"] == org_id]
        regions = {}
        assets = set()
        for position in positions:
            assets.add(position["asset_ref"])
            regions[position["region_ref"]] = (
                regions.get(position["region_ref"], 0) + 1)
        return {
            "org_id": org_id,
            "assets_reported": len(assets),
            "position_reports": len(positions),
            "links": len(links),
            "regions": regions,
            "asset_degrees": self._link_degrees(links),
        }

    # -- 927: incident lifecycle records --------------------------------------
    # The lifecycle the union spec names as not the substrate's
    # change records: an incident record plus its event stream.
    # The incident's state is derived at read from the stream by
    # ``_derive_incident_state`` and is never stored — the stored
    # incident record carries no state key. Recording an incident
    # changes no device, network, or change record.

    def open_incident(self, actor, org_id, title, network_id=None,
                      device_id=None):
        """Open one incident record. Its state derives from events."""
        self._scoped(actor, org_id, "enter", "incident_create")
        _text(title, "title")
        self._check_network_link(actor, org_id, network_id)
        self._check_device_link(actor, org_id, device_id)
        with self._lock:
            record = {
                "id": self._mint("inc-"),
                "org_id": org_id,
                "network_id": network_id,
                "device_id": device_id,
                "title": title,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "_seq": self._next_seq(),
            }
            self._incidents[record["id"]] = record
        self._audit(actor, "ext_incident_create", record["id"], {})
        return _public(record)

    def _incident(self, incident_id):
        record = self._incidents.get(incident_id)
        if record is None:
            raise NotFoundError("no such incident: %r" % (incident_id,))
        return record

    def record_incident_event(self, actor, org_id, incident_id,
                              event_kind, occurred_utc, reported_by=None,
                              note=None):
        """Record one incident lifecycle event as it is reported."""
        incident = self._incident(incident_id)
        self._scoped(actor, org_id, "record", "incident_event_create")
        if incident["org_id"] != org_id:
            raise ValidationError(
                "incident belongs to another organization")
        if event_kind not in INCIDENT_EVENT_KINDS:
            raise ValidationError(
                "event_kind must be one of %r" % (INCIDENT_EVENT_KINDS,))
        occurred_dt = _iso_text(occurred_utc, "occurred_utc")
        if reported_by is not None:
            _text(reported_by, "reported_by")
        if note is not None:
            _text(note, "note")
        with self._lock:
            record = {
                "id": self._mint("iev-"),
                "org_id": org_id,
                "incident_id": incident_id,
                "event_kind": event_kind,
                "occurred_utc": occurred_utc,
                "reported_by": (reported_by if reported_by is not None
                                else actor_name(actor)),
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "_occurred_dt": occurred_dt,
                "_seq": self._next_seq(),
            }
            self._incident_events[record["id"]] = record
        self._audit(actor, "ext_incident_event_create", record["id"],
                    {"incident_id": incident_id, "event_kind": event_kind})
        return _public(record)

    def _derive_incident_state(self, events):
        """Derive an incident's lifecycle state from its events.

        The state is the kind of the latest state-changing event
        in reported-time order (``note`` events never change it),
        or ``opened`` when no state-changing event has been
        recorded. This is the batch's fresh negative control's
        target: an implementation that reads the *first* event
        instead of the latest reports a lifecycle that has
        already moved on. Derived at read; never stored.
        """
        ordered = self._ordered(events)
        states = [e["event_kind"] for e in ordered
                  if e["event_kind"] != "note"]
        if not states:
            return "opened"
        return states[-1]

    def _incident_events_for(self, incident_id):
        return [e for e in self._incident_events.values()
                if e["incident_id"] == incident_id]

    def _incident_view(self, record):
        view = _public(record)
        events = self._incident_events_for(record["id"])
        view["derived_state"] = self._derive_incident_state(events)
        view["event_count"] = len(events)
        return view

    def get_incident(self, actor, incident_id):
        record = self._incident(incident_id)
        self._scoped(actor, record["org_id"], "read", "incident_get")
        return self._incident_view(record)

    def list_incidents(self, actor, org_id):
        self._scoped(actor, org_id, "read", "incident_list")
        return [self._incident_view(r)
                for r in self._incidents.values()
                if r["org_id"] == org_id]

    def list_incident_events(self, actor, incident_id):
        record = self._incident(incident_id)
        self._scoped(actor, record["org_id"], "read",
                     "incident_event_list")
        return [_public(e) for e in self._ordered(
            self._incident_events_for(incident_id))]

    def incident_summary(self, actor, org_id):
        """Incident counts by derived state. Counts only."""
        self._scoped(actor, org_id, "read", "incident_summary")
        by_state = {state: 0 for state in INCIDENT_STATES}
        incidents = [r for r in self._incidents.values()
                     if r["org_id"] == org_id]
        for record in incidents:
            state = self._derive_incident_state(
                self._incident_events_for(record["id"]))
            by_state[state] += 1
        return {
            "org_id": org_id,
            "incidents": len(incidents),
            "events": sum(1 for e in self._incident_events.values()
                          if e["org_id"] == org_id),
            "by_state": by_state,
        }

    # -- 928: GPU orchestration (reference; fork excess) ----------------------
    # Orchestrating GPU hardware is the fork's Bridge platform
    # work. This surface registers orchestration job records and
    # the outcomes callers report; it schedules and runs nothing
    # (``orchestrated_here`` / ``scheduled_here`` False,
    # ``reference_stub`` True). The reported state derives at
    # read from the outcome stream.

    def register_gpu_job(self, actor, org_id, job_ref, workload_ref,
                         requested_units):
        """Register one GPU orchestration job record."""
        self._scoped(actor, org_id, "enter", "gpu_job_create")
        _text(job_ref, "job_ref")
        _text(workload_ref, "workload_ref")
        _count(requested_units, "requested_units")
        with self._lock:
            for existing in self._gpu_jobs.values():
                if (existing["org_id"] == org_id
                        and existing["job_ref"] == job_ref):
                    raise ValidationError(
                        "job ref already exists in this organization: %r"
                        % (job_ref,))
            record = {
                "id": self._mint("gpu-"),
                "org_id": org_id,
                "job_ref": job_ref,
                "workload_ref": workload_ref,
                "requested_units": requested_units,
                "reference_stub": True,
                "orchestrated_here": False,
                "scheduled_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "_seq": self._next_seq(),
            }
            self._gpu_jobs[record["id"]] = record
        self._audit(actor, "ext_gpu_job_create", record["id"],
                    {"job_ref": job_ref})
        return _public(record)

    def _gpu_job(self, job_id):
        record = self._gpu_jobs.get(job_id)
        if record is None:
            raise NotFoundError("no such GPU job: %r" % (job_id,))
        return record

    def record_gpu_outcome(self, actor, org_id, job_id, outcome,
                           reported_utc, reported_units=None,
                           detail_ref=None):
        """Record one GPU job outcome as reported by the platform."""
        job = self._gpu_job(job_id)
        self._scoped(actor, org_id, "record", "gpu_outcome_create")
        if job["org_id"] != org_id:
            raise ValidationError("GPU job belongs to another organization")
        if outcome not in GPU_OUTCOMES:
            raise ValidationError(
                "outcome must be one of %r" % (GPU_OUTCOMES,))
        reported_dt = _iso_text(reported_utc, "reported_utc")
        if reported_units is not None:
            _count(reported_units, "reported_units")
        if detail_ref is not None:
            _text(detail_ref, "detail_ref")
        with self._lock:
            record = {
                "id": self._mint("guo-"),
                "org_id": org_id,
                "job_id": job_id,
                "outcome": outcome,
                "reported_units": reported_units,
                "reported_utc": reported_utc,
                "detail_ref": detail_ref,
                "reference_stub": True,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "_occurred_dt": reported_dt,
                "_seq": self._next_seq(),
            }
            self._gpu_outcomes[record["id"]] = record
        self._audit(actor, "ext_gpu_outcome_create", record["id"],
                    {"job_id": job_id, "outcome": outcome})
        return _public(record)

    def _gpu_job_view(self, record):
        view = _public(record)
        outcomes = [o for o in self._gpu_outcomes.values()
                    if o["job_id"] == record["id"]]
        view["reported_state"] = self._latest_outcome_label(
            outcomes, "outcome")
        return view

    def get_gpu_job(self, actor, job_id):
        record = self._gpu_job(job_id)
        self._scoped(actor, record["org_id"], "read", "gpu_job_get")
        return self._gpu_job_view(record)

    def list_gpu_jobs(self, actor, org_id):
        self._scoped(actor, org_id, "read", "gpu_job_list")
        return [self._gpu_job_view(r)
                for r in self._gpu_jobs.values()
                if r["org_id"] == org_id]
