"""Final GAPS batch tests — Untiered Set 19, Network Management.

The 8 open entries of this set's gap registration
(``UNION-SPEC.md`` "Gaps", GAPS.md section "Untiered Set 19 —
Network Management (2 forks, tier null)"), closed by
``netmgmt/extensions.py`` (``NetmgmtExtensions``). Every test
names the entry it pins. Cross-cutting pins: tier null binds the
whole extension surface (a recursive scan finds no tier-shaped
key, no float, and no numeric list); no record shape can hold a
credential, a coordinate, or any live-network identifier; RBAC
and organization membership are enforced through the core matrix
before any id is allocated; denied attempts are audited with the
``:denied`` suffix; lifecycle states are derived at read and
never stored.

Entry key (GAPS.md texts, verbatim):
  921 Network access authentication / RADIUS & 802.1X engine
  922 Cloud PKI & certificate lifecycle engine
  923 Wi-Fi ITDR engine
  924 Captive portal & guest / roaming access services
  925 Satellite terminal provisioning & connectivity management
  926 Fleet mapping & geospatial awareness platform
  927 Incident lifecycle management engine
  928 GPU orchestration (fork excess)
"""

import unittest

import netmgmt_helpers as H
from netmgmt.errors import NotFoundError, PermissionDenied, ValidationError
from netmgmt.extensions import NetmgmtExtensions

T1 = "2026-06-01T08:00:00+00:00"
T2 = "2026-06-01T09:00:00+00:00"
T3 = "2026-06-01T10:00:00+00:00"
T4 = "2026-06-01T11:00:00+00:00"
T5 = "2026-06-01T12:00:00+00:00"


class BatchFixture(unittest.TestCase):
    """Canonical org / network / device plus the extension surface."""

    def setUp(self):
        self.audit = H.AuditLog()
        self.store, self.org = H.make_store(audit=self.audit)
        self.network, self.device = H.make_estate(self.store, self.org)
        self.org_id = self.org["id"]
        self.ext = NetmgmtExtensions(self.store)


class TestAuthEvents(BatchFixture):
    """Entry 921 — authentication outcome records (built).

    The build authenticates no one: outcomes are caller reports,
    stored verbatim, and no credential can be recorded.
    """

    def _event(self, **overrides):
        kwargs = {"method": "eap_tls", "outcome": "authenticated",
                  "subject_ref": "USER-REF-1", "occurred_utc": T1,
                  "network_id": self.network["id"],
                  "device_id": self.device["id"]}
        kwargs.update(overrides)
        return self.ext.record_auth_event(H.MEMBER, self.org_id, **kwargs)

    def test_record_shape_and_labels(self):
        event = self._event()
        self.assertEqual(event["id"], "aev-1")
        self.assertEqual(set(event), {
            "id", "org_id", "network_id", "device_id", "method",
            "outcome", "subject_ref", "occurred_utc",
            "authenticated_here", "created_by", "created_utc"})
        self.assertIs(event["authenticated_here"], False)
        self.assertEqual(event["outcome"], "authenticated")

    def test_no_credential_parameter_exists(self):
        with self.assertRaises(TypeError):
            self._event(password="hunter2")
        with self.assertRaises(TypeError):
            self._event(shared_secret="abc")

    def test_method_and_outcome_validated(self):
        with self.assertRaises(ValidationError):
            self._event(method="kerberos")
        with self.assertRaises(ValidationError):
            self._event(outcome="maybe")

    def test_cross_org_device_rejected(self):
        org2 = self.store.create_organization(
            H.MEMBER, "AGENCY-2", "Agency Two Networks")
        net2 = self.store.create_network(
            H.MEMBER, org2["id"], "NET-2", "Second network", "SITE-2")
        dev2 = self.store.create_device(
            H.MEMBER, org2["id"], net2["id"], "DEV-2", "wireless",
            "MODEL-2")
        with self.assertRaises(ValidationError):
            self._event(device_id=dev2["id"])

    def test_summary_counts_only(self):
        self._event()
        self._event(method="peap", outcome="rejected", occurred_utc=T2)
        self._event(method="eap_tls", outcome="authenticated",
                    occurred_utc=T3)
        summary = self.ext.auth_summary(H.MEMBER, self.org_id)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["by_method"]["eap_tls"], 2)
        self.assertEqual(summary["by_method"]["peap"], 1)
        self.assertEqual(summary["by_outcome"]["authenticated"], 2)
        self.assertEqual(summary["by_outcome"]["rejected"], 1)
        self.assertEqual(summary["by_outcome"]["failed"], 0)


class TestCertificates(BatchFixture):
    """Entry 922 — certificate records + reported lifecycle (reference)."""

    def _cert(self, **overrides):
        kwargs = {"certificate_ref": "CERT-1", "subject_ref": "DEV-REF-1",
                  "issuer_ref": "PKI-REF-1",
                  "not_before_utc": "2026-01-01T00:00:00+00:00",
                  "not_after_utc": "2027-01-01T00:00:00+00:00",
                  "device_id": self.device["id"]}
        kwargs.update(overrides)
        return self.ext.register_certificate(H.MEMBER, self.org_id, **kwargs)

    def test_record_shape_and_labels(self):
        cert = self._cert()
        self.assertEqual(cert["id"], "crt-1")
        self.assertEqual(set(cert), {
            "id", "org_id", "device_id", "certificate_ref",
            "subject_ref", "issuer_ref", "not_before_utc",
            "not_after_utc", "reference_stub", "issued_here",
            "created_by", "created_utc"})
        self.assertIs(cert["reference_stub"], True)
        self.assertIs(cert["issued_here"], False)

    def test_no_certificate_material_parameter_exists(self):
        with self.assertRaises(TypeError):
            self._cert(certificate_bytes=b"-----BEGIN")
        with self.assertRaises(TypeError):
            self._cert(private_key="abc")

    def test_duplicate_ref_and_bad_window_rejected(self):
        self._cert()
        with self.assertRaises(ValidationError):
            self._cert()
        with self.assertRaises(ValidationError):
            self._cert(certificate_ref="CERT-2",
                       not_after_utc="2025-01-01T00:00:00+00:00")

    def test_lifecycle_state_derived_never_stored(self):
        cert = self._cert()
        view = self.ext.get_certificate(H.MEMBER, cert["id"])
        self.assertEqual(view["reported_lifecycle_state"], "registered")
        self.ext.record_certificate_event(
            H.MEMBER, self.org_id, cert["id"], "issued", T1)
        self.ext.record_certificate_event(
            H.MEMBER, self.org_id, cert["id"], "renewed", T3)
        view = self.ext.get_certificate(H.MEMBER, cert["id"])
        self.assertEqual(view["reported_lifecycle_state"], "renewed")
        raw = self.ext._certificates[cert["id"]]
        self.assertNotIn("reported_lifecycle_state", raw)
        self.assertNotIn("state", raw)
        self.assertNotIn("status", raw)

    def test_event_shape_labels_and_kind_validation(self):
        cert = self._cert()
        event = self.ext.record_certificate_event(
            H.MEMBER, self.org_id, cert["id"], "revoked", T2,
            note_ref="CASE-9")
        self.assertEqual(set(event), {
            "id", "org_id", "certificate_id", "event_kind",
            "occurred_utc", "note_ref", "reference_stub",
            "executed_here", "created_by", "created_utc"})
        self.assertIs(event["reference_stub"], True)
        self.assertIs(event["executed_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_certificate_event(
                H.MEMBER, self.org_id, cert["id"], "teleported", T2)
        with self.assertRaises(NotFoundError):
            self.ext.record_certificate_event(
                H.MEMBER, self.org_id, "crt-99", "issued", T2)


class TestItdrFindings(BatchFixture):
    """Entry 923 — reported detection findings (reference, re-judged).

    A verdict is a running detector's work; the severity label is
    the reporter's, stored verbatim, never computed here.
    """

    def _finding(self, **overrides):
        kwargs = {"finding_kind": "credential_misuse",
                  "severity_label": "high", "subject_ref": "USER-REF-7",
                  "reported_utc": T2, "network_id": self.network["id"],
                  "device_id": self.device["id"],
                  "detail_ref": "DET-1"}
        kwargs.update(overrides)
        return self.ext.record_itdr_finding(H.MEMBER, self.org_id, **kwargs)

    def test_record_shape_and_labels(self):
        finding = self._finding()
        self.assertEqual(finding["id"], "itd-1")
        self.assertEqual(set(finding), {
            "id", "org_id", "network_id", "device_id", "finding_kind",
            "severity_label", "subject_ref", "detail_ref",
            "reported_utc", "reference_stub", "detected_here",
            "created_by", "created_utc"})
        self.assertIs(finding["reference_stub"], True)
        self.assertIs(finding["detected_here"], False)
        self.assertEqual(finding["severity_label"], "high")

    def test_kind_and_label_validated(self):
        with self.assertRaises(ValidationError):
            self._finding(finding_kind="vibes")
        with self.assertRaises(ValidationError):
            self._finding(severity_label="spicy")

    def test_summary_counts_reported_labels(self):
        self._finding()
        self._finding(finding_kind="anomalous_access",
                      severity_label="low", reported_utc=T3)
        summary = self.ext.itdr_summary(H.MEMBER, self.org_id)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["by_kind"]["credential_misuse"], 1)
        self.assertEqual(summary["by_severity_label"]["high"], 1)
        self.assertEqual(summary["by_severity_label"]["critical"], 0)


class TestGuestAccess(BatchFixture):
    """Entry 924 — guest / roaming access grant records (built)."""

    def _grant(self, **overrides):
        kwargs = {"network_id": self.network["id"],
                  "access_kind": "voucher", "sponsor_ref": "STAFF-REF-1",
                  "valid_from_utc": T2, "valid_until_utc": T4,
                  "voucher_ref": "VCH-1", "guest_ref": "GUEST-REF-1"}
        kwargs.update(overrides)
        return self.ext.create_guest_access(H.MEMBER, self.org_id, **kwargs)

    def test_record_shape_and_labels(self):
        grant = self._grant()
        self.assertEqual(grant["id"], "gst-1")
        self.assertEqual(set(grant), {
            "id", "org_id", "network_id", "access_kind", "sponsor_ref",
            "guest_ref", "voucher_ref", "valid_from_utc",
            "valid_until_utc", "portal_served_here", "admitted_here",
            "created_by", "created_utc"})
        self.assertIs(grant["portal_served_here"], False)
        self.assertIs(grant["admitted_here"], False)

    def test_window_state_derived_at_read(self):
        grant = self._grant()
        self.assertEqual(
            self.ext.get_guest_access(H.MEMBER, grant["id"], as_of=T1)
            ["derived_state"], "scheduled")
        self.assertEqual(
            self.ext.get_guest_access(H.MEMBER, grant["id"], as_of=T3)
            ["derived_state"], "active")
        self.assertEqual(
            self.ext.get_guest_access(H.MEMBER, grant["id"], as_of=T5)
            ["derived_state"], "expired")
        raw = self.ext._guest_access[grant["id"]]
        self.assertNotIn("derived_state", raw)
        self.assertNotIn("state", raw)

    def test_kind_window_and_network_validated(self):
        with self.assertRaises(ValidationError):
            self._grant(access_kind="open_bar")
        with self.assertRaises(ValidationError):
            self._grant(valid_until_utc=T1)
        with self.assertRaises(NotFoundError):
            self._grant(network_id="net-99")


class TestTerminals(BatchFixture):
    """Entry 925 — satellite terminal provisioning records (reference)."""

    def _terminal(self, **overrides):
        kwargs = {"terminal_ref": "TERM-1",
                  "network_id": self.network["id"], "plan_ref": "PLAN-1"}
        kwargs.update(overrides)
        return self.ext.register_terminal_provisioning(
            H.MEMBER, self.org_id, **kwargs)

    def test_record_shape_and_labels(self):
        terminal = self._terminal()
        self.assertEqual(terminal["id"], "trm-1")
        self.assertEqual(set(terminal), {
            "id", "org_id", "network_id", "terminal_ref", "plan_ref",
            "reference_stub", "provisioned_here", "connected_here",
            "created_by", "created_utc"})
        self.assertIs(terminal["reference_stub"], True)
        self.assertIs(terminal["provisioned_here"], False)
        self.assertIs(terminal["connected_here"], False)

    def test_duplicate_ref_rejected(self):
        self._terminal()
        with self.assertRaises(ValidationError):
            self._terminal()

    def test_reported_state_derived_from_outcomes(self):
        terminal = self._terminal()
        view = self.ext.get_terminal_provisioning(H.MEMBER, terminal["id"])
        self.assertEqual(view["reported_state"], "registered")
        outcome = self.ext.record_terminal_outcome(
            H.MEMBER, self.org_id, terminal["id"], "provisioned", T2)
        self.assertEqual(set(outcome), {
            "id", "org_id", "terminal_id", "outcome", "reported_utc",
            "detail_ref", "reference_stub", "executed_here",
            "created_by", "created_utc"})
        self.assertIs(outcome["executed_here"], False)
        self.ext.record_terminal_outcome(
            H.MEMBER, self.org_id, terminal["id"], "activated", T3)
        view = self.ext.get_terminal_provisioning(H.MEMBER, terminal["id"])
        self.assertEqual(view["reported_state"], "activated")
        with self.assertRaises(ValidationError):
            self.ext.record_terminal_outcome(
                H.MEMBER, self.org_id, terminal["id"], "beamed", T4)


class TestFleet(BatchFixture):
    """Entry 926 — reported positions and links (reference, re-judged).

    Positions are coarse caller-chosen region labels. No
    coordinate exists anywhere: there is no parameter for one.
    """

    def _position(self, **overrides):
        kwargs = {"asset_ref": "ASSET-1", "region_ref": "REGION-NORTH",
                  "reported_utc": T1, "device_id": self.device["id"]}
        kwargs.update(overrides)
        return self.ext.record_asset_position(H.MEMBER, self.org_id,
                                              **kwargs)

    def test_position_shape_and_labels(self):
        position = self._position()
        self.assertEqual(position["id"], "pos-1")
        self.assertEqual(set(position), {
            "id", "org_id", "device_id", "asset_ref", "region_ref",
            "reported_utc", "reference_stub", "located_here",
            "mapped_here", "created_by", "created_utc"})
        self.assertIs(position["reference_stub"], True)
        self.assertIs(position["located_here"], False)
        self.assertIs(position["mapped_here"], False)

    def test_no_coordinate_parameter_exists(self):
        with self.assertRaises(TypeError):
            self._position(latitude=32)
        with self.assertRaises(TypeError):
            self._position(longitude=-96)
        with self.assertRaises(TypeError):
            self._position(coordinates="32,-96")

    def test_link_shape_and_self_link_rejected(self):
        link = self.ext.record_asset_link(
            H.MEMBER, self.org_id, "ASSET-1", "ASSET-2", "connected_to", T2)
        self.assertEqual(set(link), {
            "id", "org_id", "source_ref", "target_ref", "link_kind",
            "reported_utc", "reference_stub", "created_by", "created_utc"})
        with self.assertRaises(ValidationError):
            self.ext.record_asset_link(
                H.MEMBER, self.org_id, "ASSET-1", "ASSET-1",
                "connected_to", T2)

    def test_fleet_view_counts_and_degrees_derived(self):
        self._position()
        self._position(asset_ref="ASSET-2", region_ref="REGION-NORTH",
                       reported_utc=T2)
        self._position(asset_ref="ASSET-1", region_ref="REGION-SOUTH",
                       reported_utc=T3)
        self.ext.record_asset_link(H.MEMBER, self.org_id, "ASSET-1",
                                   "ASSET-2", "connected_to", T2)
        self.ext.record_asset_link(H.MEMBER, self.org_id, "ASSET-2",
                                   "ASSET-3", "managed_with", T3)
        view = self.ext.fleet_view(H.MEMBER, self.org_id)
        self.assertEqual(view["assets_reported"], 2)
        self.assertEqual(view["position_reports"], 3)
        self.assertEqual(view["links"], 2)
        self.assertEqual(view["regions"],
                         {"REGION-NORTH": 2, "REGION-SOUTH": 1})
        self.assertEqual(view["asset_degrees"],
                         {"ASSET-1": 1, "ASSET-2": 2, "ASSET-3": 1})


class TestIncidents(BatchFixture):
    """Entry 927 — incident lifecycle records (built).

    The stored incident record carries no state key; the state
    derives at read from the event stream.
    """

    def _incident(self, **overrides):
        kwargs = {"title": "HQ uplink degradation",
                  "network_id": self.network["id"],
                  "device_id": self.device["id"]}
        kwargs.update(overrides)
        return self.ext.open_incident(H.MEMBER, self.org_id, **kwargs)

    def _lifecycle(self, ext, incident_id):
        ext.record_incident_event(H.STAFF, self.org_id, incident_id,
                                  "acknowledged", T2)
        ext.record_incident_event(H.STAFF, self.org_id, incident_id,
                                  "resolved", T3)
        ext.record_incident_event(H.STAFF, self.org_id, incident_id,
                                  "note", T4, note="awaiting vendor")
        ext.record_incident_event(H.STAFF, self.org_id, incident_id,
                                  "reopened", T5)

    def test_record_shape_no_state_stored(self):
        incident = self._incident()
        self.assertEqual(incident["id"], "inc-1")
        self.assertEqual(set(incident), {
            "id", "org_id", "network_id", "device_id", "title",
            "created_by", "created_utc"})
        raw = self.ext._incidents[incident["id"]]
        self.assertNotIn("state", raw)
        self.assertNotIn("status", raw)
        self.assertNotIn("derived_state", raw)

    def test_state_opened_with_no_events(self):
        incident = self._incident()
        view = self.ext.get_incident(H.MEMBER, incident["id"])
        self.assertEqual(view["derived_state"], "opened")
        self.assertEqual(view["event_count"], 0)

    def test_event_shape_and_kind_validation(self):
        incident = self._incident()
        event = self.ext.record_incident_event(
            H.STAFF, self.org_id, incident["id"], "acknowledged", T2)
        self.assertEqual(set(event), {
            "id", "org_id", "incident_id", "event_kind", "occurred_utc",
            "reported_by", "note", "created_by", "created_utc"})
        self.assertEqual(event["reported_by"], "erin")
        with self.assertRaises(ValidationError):
            self.ext.record_incident_event(
                H.STAFF, self.org_id, incident["id"], "ignored", T2)

    def test_summary_counts_by_derived_state(self):
        first = self._incident()
        second = self._incident(title="Second incident")
        self._lifecycle(self.ext, first["id"])
        self.ext.record_incident_event(
            H.STAFF, self.org_id, second["id"], "acknowledged", T2)
        summary = self.ext.incident_summary(H.MEMBER, self.org_id)
        self.assertEqual(summary["incidents"], 2)
        self.assertEqual(summary["events"], 5)
        self.assertEqual(summary["by_state"]["reopened"], 1)
        self.assertEqual(summary["by_state"]["acknowledged"], 1)
        self.assertEqual(summary["by_state"]["opened"], 0)


class TestGpuJobs(BatchFixture):
    """Entry 928 — GPU orchestration job records (reference)."""

    def _job(self, **overrides):
        kwargs = {"job_ref": "JOB-1", "workload_ref": "WORKLOAD-1",
                  "requested_units": 16}
        kwargs.update(overrides)
        return self.ext.register_gpu_job(H.MEMBER, self.org_id, **kwargs)

    def test_record_shape_and_labels(self):
        job = self._job()
        self.assertEqual(job["id"], "gpu-1")
        self.assertEqual(set(job), {
            "id", "org_id", "job_ref", "workload_ref",
            "requested_units", "reference_stub", "orchestrated_here",
            "scheduled_here", "created_by", "created_utc"})
        self.assertIs(job["reference_stub"], True)
        self.assertIs(job["orchestrated_here"], False)
        self.assertIs(job["scheduled_here"], False)
        self.assertEqual(job["requested_units"], 16)

    def test_units_must_be_a_non_negative_integer(self):
        with self.assertRaises(ValidationError):
            self._job(requested_units=1.5)
        with self.assertRaises(ValidationError):
            self._job(requested_units=True)
        with self.assertRaises(ValidationError):
            self._job(requested_units=-1)

    def test_reported_state_derived_from_outcomes(self):
        job = self._job()
        view = self.ext.get_gpu_job(H.MEMBER, job["id"])
        self.assertEqual(view["reported_state"], "registered")
        outcome = self.ext.record_gpu_outcome(
            H.MEMBER, self.org_id, job["id"], "completed", T3,
            reported_units=14, detail_ref="RUN-1")
        self.assertEqual(set(outcome), {
            "id", "org_id", "job_id", "outcome", "reported_units",
            "reported_utc", "detail_ref", "reference_stub",
            "executed_here", "created_by", "created_utc"})
        self.assertIs(outcome["executed_here"], False)
        view = self.ext.get_gpu_job(H.MEMBER, job["id"])
        self.assertEqual(view["reported_state"], "completed")


class TestAccessAndAudit(BatchFixture):
    """Cross-cutting: core RBAC + membership, audit, id discipline."""

    def test_viewer_member_cannot_write_and_denial_is_audited(self):
        self.store.add_member(H.ADMIN, self.org_id, H.VIEWER.name)
        with self.assertRaises(PermissionDenied):
            self.ext.record_auth_event(
                H.VIEWER, self.org_id, "eap_tls", "authenticated",
                "USER-REF-1", T1)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_auth_event_create:denied", actions)

    def test_outsider_cannot_read_or_write(self):
        with self.assertRaises(PermissionDenied):
            self.ext.list_auth_events(H.OUTSIDER, self.org_id)
        with self.assertRaises(PermissionDenied):
            self.ext.open_incident(H.OUTSIDER, self.org_id, "Nope")

    def test_successful_mutation_is_audited(self):
        self.ext.record_auth_event(H.MEMBER, self.org_id, "eap_tls",
                                   "authenticated", "USER-REF-1", T1)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_auth_event_create", actions)

    def test_failed_operation_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.ext.record_auth_event(H.MEMBER, self.org_id, "kerberos",
                                       "authenticated", "USER-REF-1", T1)
        event = self.ext.record_auth_event(
            H.MEMBER, self.org_id, "eap_tls", "authenticated",
            "USER-REF-1", T1)
        self.assertEqual(event["id"], "aev-1")

    def test_extension_writes_leave_core_records_untouched(self):
        before = dict(self.store._devices[self.device["id"]])
        self.ext.record_auth_event(
            H.MEMBER, self.org_id, "eap_tls", "authenticated",
            "USER-REF-1", T1, device_id=self.device["id"])
        incident = self.ext.open_incident(
            H.MEMBER, self.org_id, "Check", device_id=self.device["id"])
        self.ext.record_incident_event(
            H.STAFF, self.org_id, incident["id"], "resolved", T2)
        after = dict(self.store._devices[self.device["id"]])
        self.assertEqual(before, after)
        self.assertEqual(len(after), 9)


class MutantExtensions(NetmgmtExtensions):
    """Reads the FIRST state-changing event instead of the latest."""

    def _derive_incident_state(self, events):
        ordered = self._ordered(events)
        states = [e["event_kind"] for e in ordered
                  if e["event_kind"] != "note"]
        if not states:
            return "opened"
        return states[0]


class TestNegativeControl(BatchFixture):
    """Fresh negative control: incident state derivation (entry 927).

    Canonical lifecycle: acknowledged -> resolved -> note ->
    reopened. The canonical derived state is ``reopened`` (the
    latest state-changing event; the note changes nothing). A
    mutant reading the first event reports ``acknowledged`` — a
    lifecycle that has already moved on — and must be rejected
    by the canonical expectation.
    """

    CANONICAL_STATE = "reopened"

    def _build(self, ext):
        incident = ext.open_incident(H.MEMBER, self.org_id,
                                     "HQ uplink degradation")
        ext.record_incident_event(H.STAFF, self.org_id, incident["id"],
                                  "acknowledged", T2)
        ext.record_incident_event(H.STAFF, self.org_id, incident["id"],
                                  "resolved", T3)
        ext.record_incident_event(H.STAFF, self.org_id, incident["id"],
                                  "note", T4, note="awaiting vendor")
        ext.record_incident_event(H.STAFF, self.org_id, incident["id"],
                                  "reopened", T5)
        return incident

    def test_canonical_expectation(self):
        incident = self._build(self.ext)
        view = self.ext.get_incident(H.MEMBER, incident["id"])
        self.assertEqual(view["derived_state"], self.CANONICAL_STATE)
        self.assertEqual(view["event_count"], 4)

    def test_note_event_never_changes_state(self):
        incident = self.ext.open_incident(H.MEMBER, self.org_id, "Quiet")
        self.ext.record_incident_event(
            H.STAFF, self.org_id, incident["id"], "resolved", T2)
        self.ext.record_incident_event(
            H.STAFF, self.org_id, incident["id"], "note", T3,
            note="still resolved")
        view = self.ext.get_incident(H.MEMBER, incident["id"])
        self.assertEqual(view["derived_state"], "resolved")

    def test_mutant_reports_the_first_state(self):
        mutant = MutantExtensions(self.store)
        incident = self._build(mutant)
        view = mutant.get_incident(H.MEMBER, incident["id"])
        self.assertEqual(view["derived_state"], "acknowledged")

    def test_canonical_expectation_rejects_the_mutant(self):
        mutant = MutantExtensions(self.store)
        incident = self._build(mutant)
        mutant_state = mutant.get_incident(
            H.MEMBER, incident["id"])["derived_state"]
        with self.assertRaises(AssertionError):
            self.assertEqual(self.CANONICAL_STATE, mutant_state)


class TestTierNullAndShapeScan(BatchFixture):
    """Cross-cutting: tier null and shape discipline.

    Every extension record and derived view is scanned
    recursively: no field name may name a tier, a baseline, an
    equivalence, a score, a coordinate, or a live-network
    identifier; no value may be a float; no list may hold
    numbers. The keys of a counts mapping (a dict whose values
    are all integers) are enumeration labels drawn from the
    pinned vocabularies — data, not fields — so the field-name
    check skips them; the field names holding those mappings
    (``by_kind``, ``by_method``, ...) are checked.
    """

    FORBIDDEN_KEY_PARTS = ("tier", "cmmc", "baseline", "equivalence",
                           "impact_level", "score", "rating", "health",
                           "latitude", "longitude", "coordinate",
                           "serial", "password", "credential", "secret",
                           "mac_address", "ip_address")

    def _everything(self):
        ext = self.ext
        event = ext.record_auth_event(
            H.MEMBER, self.org_id, "eap_tls", "authenticated",
            "USER-REF-1", T1, network_id=self.network["id"],
            device_id=self.device["id"])
        auth_summary = ext.auth_summary(H.MEMBER, self.org_id)
        cert = ext.register_certificate(
            H.MEMBER, self.org_id, "CERT-1", "DEV-REF-1", "PKI-REF-1",
            "2026-01-01T00:00:00+00:00", "2027-01-01T00:00:00+00:00",
            device_id=self.device["id"])
        cert_event = ext.record_certificate_event(
            H.MEMBER, self.org_id, cert["id"], "issued", T1)
        cert_view = ext.get_certificate(H.MEMBER, cert["id"])
        finding = ext.record_itdr_finding(
            H.MEMBER, self.org_id, "credential_misuse", "high",
            "USER-REF-7", T2, detail_ref="DET-1")
        itdr_summary = ext.itdr_summary(H.MEMBER, self.org_id)
        grant = ext.create_guest_access(
            H.MEMBER, self.org_id, self.network["id"], "voucher",
            "STAFF-REF-1", T2, T4, voucher_ref="VCH-1")
        grant_view = ext.get_guest_access(H.MEMBER, grant["id"], as_of=T3)
        terminal = ext.register_terminal_provisioning(
            H.MEMBER, self.org_id, "TERM-1",
            network_id=self.network["id"], plan_ref="PLAN-1")
        term_outcome = ext.record_terminal_outcome(
            H.MEMBER, self.org_id, terminal["id"], "activated", T3)
        term_view = ext.get_terminal_provisioning(H.MEMBER,
                                                  terminal["id"])
        position = ext.record_asset_position(
            H.MEMBER, self.org_id, "ASSET-1", "REGION-NORTH", T1)
        link = ext.record_asset_link(
            H.MEMBER, self.org_id, "ASSET-1", "ASSET-2",
            "connected_to", T2)
        fleet = ext.fleet_view(H.MEMBER, self.org_id)
        incident = ext.open_incident(
            H.MEMBER, self.org_id, "HQ uplink degradation",
            network_id=self.network["id"], device_id=self.device["id"])
        inc_event = ext.record_incident_event(
            H.STAFF, self.org_id, incident["id"], "acknowledged", T2)
        inc_view = ext.get_incident(H.MEMBER, incident["id"])
        inc_summary = ext.incident_summary(H.MEMBER, self.org_id)
        job = ext.register_gpu_job(H.MEMBER, self.org_id, "JOB-1",
                                   "WORKLOAD-1", 16)
        gpu_outcome = ext.record_gpu_outcome(
            H.MEMBER, self.org_id, job["id"], "completed", T3,
            reported_units=14)
        gpu_view = ext.get_gpu_job(H.MEMBER, job["id"])
        return [event, auth_summary, cert, cert_event, cert_view,
                finding, itdr_summary, grant, grant_view, terminal,
                term_outcome, term_view, position, link, fleet,
                incident, inc_event, inc_view, inc_summary, job,
                gpu_outcome, gpu_view]

    def _scan(self, node, root):
        if isinstance(node, dict):
            is_counts = bool(node) and all(
                isinstance(v, int) and not isinstance(v, bool)
                for v in node.values())
            for key, value in node.items():
                if not is_counts:
                    lowered = key.lower()
                    for part in self.FORBIDDEN_KEY_PARTS:
                        self.assertNotIn(
                            part, lowered,
                            "forbidden field %r in %r" % (key, root))
                self.assertNotIsInstance(
                    value, float,
                    "float value at %r in %r" % (key, root))
                self._scan(value, root)
        elif isinstance(node, list):
            for item in node:
                self.assertNotIsInstance(
                    item, (int, float),
                    "numeric list in %r" % (root,))
                self._scan(item, root)

    def test_no_tier_shaped_key_no_float_no_numeric_list(self):
        for record in self._everything():
            self._scan(record, record)

    def test_stub_records_carry_their_labels(self):
        records = self._everything()
        by_id = {r["id"]: r for r in records if "id" in r}
        for stub_id in ("crt-1", "cev-1", "itd-1", "trm-1", "tro-1",
                        "pos-1", "lnk-1", "gpu-1", "guo-1"):
            self.assertIs(by_id[stub_id]["reference_stub"], True)


if __name__ == "__main__":
    unittest.main()
