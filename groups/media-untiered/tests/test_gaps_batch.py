"""Final GAPS batch tests — Untiered Set 27 (Media).

Pins the extension surface in ``src/media/extensions.py``
against the set's 5 open Extended entries (see ``../BATCH.md``):

- Live video transport & routing engine (idx 960) — reference:
  transport run/outcome records over core routes, every record
  labeled ``reference_stub`` / ``reference_transport``; recording
  a run starts no session and changes no route.
- Stream encryption implementation (idx 961) — reference:
  encryption reference/status records; no cryptography here, and
  a reference never changes the route's stated label.
- Device control channel (idx 962) — built, records form:
  dispatch records bound one-to-one to core control actions,
  delivery outcomes verbatim, per-device counts derived at read;
  nothing is sent.
- Stream optimization engine (idx 963) — built, records form:
  profile-to-route assignment records and a route view derived
  at read; no stream is adapted and no profile is applied.
- Status & monitoring telemetry collection (idx 964) —
  reference: collection source/outcome records; recording one
  creates no core status snapshot.

Plus the untiered discipline scan (no tier, baseline,
equivalence, score, latency, or media-content key anywhere on
the new surface) and the batch's fresh negative control: the
latest-label seam ``MediaExtensions._latest_label`` — a mutant
that reads the earliest record must misstate every derived
"latest" label.
"""

import unittest

import media_helpers as helpers
from media.errors import (
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from media.extensions import MediaExtensions

ADMIN = helpers.ADMIN
OPERATOR = helpers.OPERATOR
VIEWER = helpers.VIEWER


def make_ext():
    store, audit = helpers.make_store()
    org = helpers.make_org(store)
    route, source, destination = helpers.make_route(store, org)
    return store, audit, org, route, MediaExtensions(store)


class TestTransportReference(unittest.TestCase):
    """Idx 960 — transport runs are labeled reference records;
    the transport itself happens elsewhere."""

    def setUp(self):
        self.store, self.audit, self.org, self.route, self.ext = \
            make_ext()

    def test_run_shape_and_labels(self):
        run = self.ext.record_transport_run(
            OPERATOR, self.route["id"], note="contribution window")
        self.assertEqual(run["id"], "trn-1")
        self.assertEqual(run["route_id"], self.route["id"])
        self.assertIsNone(run["session_id"])
        self.assertTrue(run["reference_stub"])
        self.assertTrue(run["reference_transport"])
        self.assertFalse(run["transported_here"])
        self.assertEqual(run["state"], "recorded_reference_only")

    def test_unknown_route_rejected_and_no_id_consumed(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_transport_run(OPERATOR, "rou-99")
        run = self.ext.record_transport_run(OPERATOR, self.route["id"])
        self.assertEqual(run["id"], "trn-1")

    def test_session_binding_must_match_route(self):
        other_route, _, _ = helpers.make_route(
            self.store, self.org, tag="-B")
        session = self.store.start_session(
            OPERATOR, self.route["id"], started_at=helpers.STARTED)
        run = self.ext.record_transport_run(
            OPERATOR, self.route["id"], session_id=session["id"])
        self.assertEqual(run["session_id"], session["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_transport_run(
                OPERATOR, other_route["id"], session_id=session["id"])

    def test_recording_a_run_changes_no_core_record(self):
        before_route = self.store.get_route(ADMIN, self.route["id"])
        self.ext.record_transport_run(OPERATOR, self.route["id"])
        self.assertEqual(
            self.store.list_sessions(ADMIN, route_id=self.route["id"]),
            [])
        self.assertEqual(
            self.store.get_route(ADMIN, self.route["id"]), before_route)

    def test_outcome_verbatim_and_view_derives_latest(self):
        run = self.ext.record_transport_run(OPERATOR, self.route["id"])
        first = self.ext.record_transport_outcome(
            OPERATOR, run["id"], "carried (reported)")
        self.assertEqual(first["id"], "tro-1")
        self.assertTrue(first["reference_transport"])
        self.assertFalse(first["transported_here"])
        self.ext.record_transport_outcome(
            OPERATOR, run["id"], "rerouted (reported)")
        view = self.ext.transport_view(run["id"], actor=ADMIN)
        self.assertTrue(view["derived"])
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_outcome_label"],
                         "rerouted (reported)")
        # The stored run record carries no derived key.
        stored = self.ext.get_transport_run(run["id"], actor=ADMIN)
        self.assertNotIn("outcome_count", stored)
        self.assertNotIn("latest_outcome_label", stored)

    def test_outcome_for_unknown_run_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_transport_outcome(
                OPERATOR, "trn-99", "carried (reported)")


class TestEncryptionReference(unittest.TestCase):
    """Idx 961 — encryption references hold the fork's mechanism
    label as data; no cryptography is performed here."""

    def setUp(self):
        self.store, self.audit, self.org, self.route, self.ext = \
            make_ext()

    def test_reference_shape_and_labels(self):
        ref = self.ext.record_encryption_reference(
            OPERATOR, self.route["id"], "AES-256")
        self.assertEqual(ref["id"], "enc-1")
        self.assertEqual(ref["mechanism_label"], "AES-256")
        self.assertEqual(ref["route_encryption_label"], "aes_256")
        self.assertTrue(ref["reference_stub"])
        self.assertFalse(ref["cryptography_performed_here"])
        self.assertFalse(ref["encrypted_here"])
        self.assertEqual(ref["state"], "recorded_reference_only")

    def test_snapshot_reflects_the_routes_stated_label(self):
        plain_route, _, _ = helpers.make_route(
            self.store, self.org, tag="-P", encryption="none_stated")
        ref = self.ext.record_encryption_reference(
            OPERATOR, plain_route["id"], "none stated by operator")
        self.assertEqual(ref["route_encryption_label"], "none_stated")

    def test_reference_never_changes_the_route(self):
        before = self.store.get_route(ADMIN, self.route["id"])
        ref = self.ext.record_encryption_reference(
            OPERATOR, self.route["id"], "AES-256")
        self.ext.record_encryption_status(
            OPERATOR, ref["id"], "keys rotated (reported)")
        self.assertEqual(
            self.store.get_route(ADMIN, self.route["id"]), before)

    def test_status_verbatim_and_view(self):
        ref = self.ext.record_encryption_reference(
            OPERATOR, self.route["id"], "AES-256")
        status = self.ext.record_encryption_status(
            OPERATOR, ref["id"], "provisioned (reported)")
        self.assertEqual(status["id"], "enr-1")
        self.assertTrue(status["reference_stub"])
        self.ext.record_encryption_status(
            OPERATOR, ref["id"], "keys rotated (reported)")
        view = self.ext.encryption_view(ref["id"], actor=ADMIN)
        self.assertEqual(view["status_count"], 2)
        self.assertEqual(view["latest_status_label"],
                         "keys rotated (reported)")

    def test_unknown_route_rejected_and_no_id_consumed(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_encryption_reference(
                OPERATOR, "rou-99", "AES-256")
        ref = self.ext.record_encryption_reference(
            OPERATOR, self.route["id"], "AES-256")
        self.assertEqual(ref["id"], "enc-1")


class TestControlDispatchBuilt(unittest.TestCase):
    """Idx 962 — dispatches bind core control actions one-to-one;
    delivery is reported, never performed."""

    def setUp(self):
        self.store, self.audit, self.org, self.route, self.ext = \
            make_ext()
        _, source, _ = helpers.make_route(self.store, self.org,
                                          tag="-D")
        self.device = helpers.make_device(self.store, self.org,
                                          endpoint=source)
        self.action = self.store.record_control_action(
            OPERATOR, self.device["id"], "start", at=helpers.AT)

    def test_dispatch_shape_binds_core_action(self):
        dispatch = self.ext.record_control_dispatch(
            OPERATOR, self.action["id"])
        self.assertEqual(dispatch["id"], "dsp-1")
        self.assertEqual(dispatch["control_action_id"],
                         self.action["id"])
        self.assertEqual(dispatch["device_id"], self.device["id"])
        self.assertEqual(dispatch["action"], "start")
        self.assertTrue(dispatch["reference_transport"])
        self.assertFalse(dispatch["sent_here"])
        self.assertFalse(dispatch["delivered_here"])
        self.assertEqual(dispatch["state"], "recorded_dispatch_only")
        # Built form: the record is this substrate's own surface,
        # not a stub of an external engine's registry.
        self.assertNotIn("reference_stub", dispatch)

    def test_duplicate_dispatch_refused_and_no_id_consumed(self):
        self.ext.record_control_dispatch(OPERATOR, self.action["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_control_dispatch(
                OPERATOR, self.action["id"])
        second_action = self.store.record_control_action(
            OPERATOR, self.device["id"], "restart", at=helpers.AT)
        dispatch = self.ext.record_control_dispatch(
            OPERATOR, second_action["id"])
        self.assertEqual(dispatch["id"], "dsp-2")

    def test_unknown_action_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_control_dispatch(OPERATOR, "ctl-99")

    def test_outcome_verbatim_and_device_view_derives(self):
        dispatch = self.ext.record_control_dispatch(
            OPERATOR, self.action["id"])
        outcome = self.ext.record_delivery_outcome(
            OPERATOR, dispatch["id"], "acknowledged (reported)")
        self.assertEqual(outcome["id"], "dlo-1")
        self.assertTrue(outcome["reference_transport"])
        self.assertFalse(outcome["delivered_here"])
        self.ext.record_delivery_outcome(
            OPERATOR, dispatch["id"], "applied (reported)")
        second_action = self.store.record_control_action(
            OPERATOR, self.device["id"], "stop", at=helpers.AT)
        self.ext.record_control_dispatch(OPERATOR, second_action["id"])
        view = self.ext.device_dispatch_view(self.device["id"],
                                             actor=ADMIN)
        self.assertTrue(view["derived"])
        self.assertEqual(view["dispatch_count"], 2)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["outcomes_by_label"],
                         {"acknowledged (reported)": 1,
                          "applied (reported)": 1})
        self.assertEqual(view["dispatches_without_outcome"], 1)
        self.assertEqual(view["latest_outcome_label"],
                         "applied (reported)")

    def test_dispatch_records_nothing_in_the_core(self):
        before_summary = self.store.summary(ADMIN)
        before_device = self.store.get_device(ADMIN,
                                              self.device["id"])
        dispatch = self.ext.record_control_dispatch(
            OPERATOR, self.action["id"])
        self.ext.record_delivery_outcome(
            OPERATOR, dispatch["id"], "applied (reported)")
        self.assertEqual(self.store.summary(ADMIN), before_summary)
        self.assertEqual(
            self.store.get_device(ADMIN, self.device["id"]),
            before_device)


class TestOptimizationBuilt(unittest.TestCase):
    """Idx 963 — assignments and derived views over core profiles;
    no stream is adapted and no profile is applied."""

    def setUp(self):
        self.store, self.audit, self.org, self.route, self.ext = \
            make_ext()
        self.profile = self.store.create_optimization_profile(
            OPERATOR, self.org["id"], helpers.PROFILE_LABEL,
            helpers.PROFILE_SETTINGS)

    def test_assignment_shape_and_flags(self):
        assignment = self.ext.record_optimization_assignment(
            OPERATOR, self.profile["id"], self.route["id"])
        self.assertEqual(assignment["id"], "asn-1")
        self.assertEqual(assignment["profile_id"], self.profile["id"])
        self.assertEqual(assignment["route_id"], self.route["id"])
        self.assertFalse(assignment["applied_here"])
        self.assertFalse(assignment["adapted_here"])
        self.assertFalse(assignment["optimized_here"])
        self.assertEqual(assignment["state"],
                         "recorded_assignment_only")
        self.assertNotIn("reference_stub", assignment)

    def test_cross_organization_route_rejected(self):
        org2 = self.store.create_organization(ADMIN, "ORG-0002",
                                              "Second agency")
        foreign_route, _, _ = helpers.make_route(self.store, org2,
                                                 tag="-F")
        with self.assertRaises(ValidationError):
            self.ext.record_optimization_assignment(
                OPERATOR, self.profile["id"], foreign_route["id"])
        assignment = self.ext.record_optimization_assignment(
            OPERATOR, self.profile["id"], self.route["id"])
        self.assertEqual(assignment["id"], "asn-1")

    def test_unknown_profile_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_optimization_assignment(
                OPERATOR, "opt-99", self.route["id"])

    def test_duplicate_assignment_refused(self):
        self.ext.record_optimization_assignment(
            OPERATOR, self.profile["id"], self.route["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_optimization_assignment(
                OPERATOR, self.profile["id"], self.route["id"])

    def test_outcome_and_route_view_derives_from_records(self):
        assignment = self.ext.record_optimization_assignment(
            OPERATOR, self.profile["id"], self.route["id"])
        outcome = self.ext.record_optimization_outcome(
            OPERATOR, assignment["id"], "profile live (reported)")
        self.assertEqual(outcome["id"], "oto-1")
        self.assertFalse(outcome["optimized_here"])
        self.ext.record_optimization_outcome(
            OPERATOR, assignment["id"], "profile updated (reported)")
        view = self.ext.route_optimization_view(self.route["id"],
                                                actor=ADMIN)
        self.assertTrue(view["derived"])
        self.assertEqual(view["assignment_count"], 1)
        self.assertEqual(view["assigned_profile_ids"],
                         [self.profile["id"]])
        self.assertEqual(view["assigned_profiles_enabled"], 1)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_outcome_label"],
                         "profile updated (reported)")
        # The enabled count is a read-time join over the core's
        # recorded flag: toggling the core profile changes the
        # view without touching the assignment record.
        self.store.set_profile_enabled(OPERATOR, self.profile["id"],
                                       False)
        view = self.ext.route_optimization_view(self.route["id"],
                                                actor=ADMIN)
        self.assertEqual(view["assigned_profiles_enabled"], 0)
        stored = self.ext.get_assignment(assignment["id"], actor=ADMIN)
        self.assertEqual(stored["state"], "recorded_assignment_only")

    def test_assignment_changes_no_core_record(self):
        before_profile = self.store.list_profiles(ADMIN)[0]
        before_route = self.store.get_route(ADMIN, self.route["id"])
        self.ext.record_optimization_assignment(
            OPERATOR, self.profile["id"], self.route["id"])
        self.assertEqual(self.store.list_profiles(ADMIN)[0],
                         before_profile)
        self.assertEqual(self.store.get_route(ADMIN, self.route["id"]),
                         before_route)


class TestTelemetryReference(unittest.TestCase):
    """Idx 964 — collection sources are labeled reference
    records; no probe runs here and no snapshot is created."""

    def setUp(self):
        self.store, self.audit, self.org, self.route, self.ext = \
            make_ext()

    def test_source_shape_and_labels(self):
        source = self.ext.record_collection_source(
            OPERATOR, "route", self.route["id"], "hub-probe/1")
        self.assertEqual(source["id"], "col-1")
        self.assertEqual(source["subject_kind"], "route")
        self.assertEqual(source["probe_label"], "hub-probe/1")
        self.assertTrue(source["reference_stub"])
        self.assertFalse(source["collected_here"])
        self.assertEqual(source["state"], "recorded_reference_only")

    def test_device_subject_and_bad_kind(self):
        device = helpers.make_device(self.store, self.org)
        source = self.ext.record_collection_source(
            OPERATOR, "device", device["id"], "encoder-agent/2")
        self.assertEqual(source["subject_id"], device["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_collection_source(
                OPERATOR, "session", "ses-1", "probe")
        with self.assertRaises(NotFoundError):
            self.ext.record_collection_source(
                OPERATOR, "route", "rou-99", "probe")

    def test_outcome_reported_count_stored_verbatim(self):
        source = self.ext.record_collection_source(
            OPERATOR, "route", self.route["id"], "hub-probe/1")
        outcome = self.ext.record_collection_outcome(
            OPERATOR, source["id"], "cycle complete (reported)",
            reported_snapshot_count=12)
        self.assertEqual(outcome["id"], "crn-1")
        self.assertEqual(outcome["reported_snapshot_count"], 12)
        self.assertTrue(outcome["reference_stub"])
        self.assertFalse(outcome["collected_here"])
        for bad in (True, 1.5, -1):
            with self.assertRaises(ValidationError):
                self.ext.record_collection_outcome(
                    OPERATOR, source["id"], "x",
                    reported_snapshot_count=bad)

    def test_view_sums_reports_and_derives_latest(self):
        source = self.ext.record_collection_source(
            OPERATOR, "route", self.route["id"], "hub-probe/1")
        self.ext.record_collection_outcome(
            OPERATOR, source["id"], "cycle 1 (reported)",
            reported_snapshot_count=4)
        self.ext.record_collection_outcome(
            OPERATOR, source["id"], "cycle 2 (reported)",
            reported_snapshot_count=5)
        view = self.ext.collection_view(source["id"], actor=ADMIN)
        self.assertTrue(view["derived"])
        self.assertEqual(view["outcome_count"], 2)
        # The total sums the recorded reports; it is not a count
        # of snapshots this build holds (it holds none — below).
        self.assertEqual(view["total_reported_snapshots"], 9)
        self.assertEqual(view["latest_outcome_label"],
                         "cycle 2 (reported)")

    def test_collection_records_create_no_core_snapshot(self):
        source = self.ext.record_collection_source(
            OPERATOR, "route", self.route["id"], "hub-probe/1")
        self.ext.record_collection_outcome(
            OPERATOR, source["id"], "cycle complete (reported)",
            reported_snapshot_count=3)
        self.assertEqual(self.store.list_snapshots(ADMIN), [])
        self.assertEqual(self.store.summary(ADMIN)["snapshots"], 0)


class TestAccessAndAudit(unittest.TestCase):
    """The founding matrix binds the extension; denials are
    audited with the ``:denied`` suffix."""

    def setUp(self):
        self.store, self.audit, self.org, self.route, self.ext = \
            make_ext()

    def test_viewer_write_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_transport_run(VIEWER, self.route["id"])
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_transport_run_record:denied", actions)

    def test_viewer_read_allowed(self):
        self.ext.record_transport_run(OPERATOR, self.route["id"])
        runs = self.ext.list_transport_runs(actor=VIEWER)
        self.assertEqual(len(runs), 1)

    def test_extension_mutations_are_audited(self):
        self.ext.record_transport_run(OPERATOR, self.route["id"])
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_transport_run_record", actions)


FORBIDDEN_KEY_PARTS = (
    "tier", "baseline", "impact_level", "cmmc", "equivalen",
    "fedramp", "score", "grade", "rank", "rating", "quality",
    "latency", "bitrate", "popularity", "payload", "video",
    "audio", "secret", "password", "price", "money", "cents",
    "email", "ssn", "key_material",
)


def _scan_keys(value, path="root"):
    if isinstance(value, dict):
        for key, sub in value.items():
            lowered = str(key).lower()
            for part in FORBIDDEN_KEY_PARTS:
                if part in lowered:
                    raise AssertionError(
                        "forbidden key part %r in key %r at %s"
                        % (part, key, path))
            _scan_keys(sub, "%s.%s" % (path, key))
    elif isinstance(value, (list, tuple)):
        for index, sub in enumerate(value):
            _scan_keys(sub, "%s[%d]" % (path, index))


class TestTierNullNoScoreScan(unittest.TestCase):
    """Untiered discipline over the whole new surface: a
    recursive key scan over every extension record, view, and
    the summary finds no tier, baseline, equivalence, score,
    latency, or media-content key."""

    def setUp(self):
        self.store, self.audit, self.org, self.route, self.ext = \
            make_ext()
        device = helpers.make_device(self.store, self.org)
        action = self.store.record_control_action(
            OPERATOR, device["id"], "start", at=helpers.AT)
        profile = self.store.create_optimization_profile(
            OPERATOR, self.org["id"], helpers.PROFILE_LABEL,
            helpers.PROFILE_SETTINGS)
        run = self.ext.record_transport_run(OPERATOR,
                                            self.route["id"])
        self.ext.record_transport_outcome(OPERATOR, run["id"],
                                          "carried (reported)")
        ref = self.ext.record_encryption_reference(
            OPERATOR, self.route["id"], "AES-256")
        self.ext.record_encryption_status(OPERATOR, ref["id"],
                                          "provisioned (reported)")
        dispatch = self.ext.record_control_dispatch(
            OPERATOR, action["id"])
        self.ext.record_delivery_outcome(OPERATOR, dispatch["id"],
                                         "applied (reported)")
        assignment = self.ext.record_optimization_assignment(
            OPERATOR, profile["id"], self.route["id"])
        self.ext.record_optimization_outcome(
            OPERATOR, assignment["id"], "profile live (reported)")
        source = self.ext.record_collection_source(
            OPERATOR, "route", self.route["id"], "hub-probe/1")
        self.ext.record_collection_outcome(
            OPERATOR, source["id"], "cycle complete (reported)",
            reported_snapshot_count=2)
        self.device_id = device["id"]
        self.run_id = run["id"]
        self.ref_id = ref["id"]
        self.source_id = source["id"]

    def test_scan_over_records_views_and_summary(self):
        surface = [
            self.ext.list_transport_runs(actor=ADMIN),
            self.ext.transport_view(self.run_id, actor=ADMIN),
            self.ext.list_encryption_references(actor=ADMIN),
            self.ext.encryption_view(self.ref_id, actor=ADMIN),
            self.ext.list_dispatches(actor=ADMIN),
            self.ext.device_dispatch_view(self.device_id,
                                          actor=ADMIN),
            self.ext.list_assignments(actor=ADMIN),
            self.ext.route_optimization_view(self.route["id"],
                                             actor=ADMIN),
            self.ext.list_collection_sources(actor=ADMIN),
            self.ext.collection_view(self.source_id, actor=ADMIN),
            self.ext.extension_summary(actor=ADMIN),
        ]
        for item in surface:
            _scan_keys(item)

    def test_summary_is_counts_only(self):
        summary = self.ext.extension_summary(actor=ADMIN)
        self.assertEqual(set(summary), {
            "transport_runs", "transport_outcomes",
            "encryption_references", "encryption_statuses",
            "control_dispatches", "delivery_outcomes",
            "optimization_assignments", "optimization_outcomes",
            "collection_sources", "collection_outcomes",
        })
        self.assertTrue(
            all(isinstance(v, int) for v in summary.values()))


class _EarliestLabelExtensions(MediaExtensions):
    """Mutant: the latest-label seam reads the earliest record."""

    @staticmethod
    def _latest_label(records, key):
        return records[0][key] if records else None


class TestLatestLabelNegativeControl(unittest.TestCase):
    """Fresh negative control for the latest-label seam.

    Canonical expectation: a derived view's "latest" label is
    the most recently recorded one. The mutant seam reads the
    earliest record and must misstate it.
    """

    def setUp(self):
        self.store, self.audit, self.org, self.route, self.ext = \
            make_ext()
        self.mutant = _EarliestLabelExtensions(self.store)
        run = self.ext.record_transport_run(OPERATOR,
                                            self.route["id"])
        self.run_id = run["id"]
        self.ext.record_transport_outcome(OPERATOR, run["id"],
                                          "first-report")
        self.ext.record_transport_outcome(OPERATOR, run["id"],
                                          "second-report")
        mrun = self.mutant.record_transport_run(OPERATOR,
                                                self.route["id"])
        self.mrun_id = mrun["id"]
        self.mutant.record_transport_outcome(OPERATOR, mrun["id"],
                                             "first-report")
        self.mutant.record_transport_outcome(OPERATOR, mrun["id"],
                                             "second-report")

    def test_canonical_latest_is_most_recent(self):
        view = self.ext.transport_view(self.run_id, actor=ADMIN)
        self.assertEqual(view["latest_outcome_label"],
                         "second-report")
        self.assertEqual(view["outcome_count"], 2)

    def test_mutant_reports_earliest(self):
        view = self.mutant.transport_view(self.mrun_id, actor=ADMIN)
        self.assertEqual(view["latest_outcome_label"],
                         "first-report")

    def test_mutant_outcome_is_not_the_canonical_expectation(self):
        with self.assertRaises(AssertionError):
            self.assertEqual(
                self.mutant.transport_view(self.mrun_id, actor=ADMIN)
                ["latest_outcome_label"],
                "second-report")


if __name__ == "__main__":
    unittest.main()
