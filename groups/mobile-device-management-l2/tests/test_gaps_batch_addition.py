"""Final GAPS batch, second unit — Remainder Addition — Mobile
Device Management (MDM) L2 (inventory idx 679–680).

Pins the extension surface in ``src/mdm/extensions_addition.py``
(``MdmExtensionsAddition``, wrapping the core ``MdmStore``; see
``../BATCH-ADDITION.md`` for the per-entry disposition):

- idx 679, zero-trust access validation (built, records form):
  validation profiles as definitions-as-data; decision records
  holding the external plane's reported dimension results and
  reported access level verbatim; the access view deriving the
  current reported level at read from the latest decision.
  ``evaluated_here`` / ``decided_here`` / ``validated_here``
  are False throughout — nothing is evaluated or decided here.
- idx 680, mobile threat defense (reference, stub-engine):
  deployment and threat-event records carrying
  ``reference_stub: True`` and state ``recorded_reference_only``;
  detections and remediations recorded as reported; creating
  one changes no core record.

Plus cross-cutting pins: the founding privacy invariant over
the whole addition surface (no identifier or location key on
any stored record, using the first unit's ``FORBIDDEN_KEYS``
set), ``exta_``-prefixed audit actions, and RBAC denials
consuming no id.

The unit's fresh negative control is the current-decision
derivation seam (``MdmExtensionsAddition._current_decision``):
``TestAccessViewNegativeControl`` pins the canonical
expectation (the LATEST recorded decision is current), and the
external mutation drill is recorded in ``tests/README.md``.

Fixtures: ``make_store()`` (organization AGENCY-1 by MEMBER/bob,
STAFF/erin a member) from ``mdm_helpers``.
"""

import unittest

from mdm_helpers import (
    ADMIN, MEMBER, OUTSIDER, STAFF, VIEWER, make_store,
)

from mdm.errors import NotFoundError, PermissionDenied, ValidationError
from mdm.extensions import FORBIDDEN_KEYS
from mdm.extensions_addition import MdmExtensionsAddition


def _all_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(str(key))
            keys |= _all_keys(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            keys |= _all_keys(value)
    return keys


class AdditionFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.org = make_store()
        self.ext = MdmExtensionsAddition(self.store)
        self.oid = self.org["id"]

    def make_profile(self, actor=MEMBER, **overrides):
        kwargs = {
            "profile_ref": "ZT-CORE",
            "name": "Core zero-trust profile",
            "dimensions": ["device", "identity", "context", "privacy"],
            "access_levels": ["full", "limited", "denied"],
        }
        kwargs.update(overrides)
        return self.ext.create_validation_profile(
            actor, self.oid, **kwargs)

    def make_deployment(self, actor=MEMBER, **overrides):
        kwargs = {"device_ref": "DEV-100", "deployment_mode": "silent"}
        kwargs.update(overrides)
        return self.ext.record_threat_deployment(actor, self.oid, **kwargs)


class TestValidationProfiles(AdditionFixture):
    """Entry (idx 679): validation profiles are definitions as
    data — declared dimensions and access levels, nothing
    evaluated."""

    def test_record_shape_and_labels(self):
        profile = self.make_profile()
        self.assertEqual(profile["id"], "zvp-1")
        self.assertEqual(profile["dimensions"],
                         ["device", "identity", "context", "privacy"])
        self.assertEqual(profile["access_levels"], ["full", "limited", "denied"])
        self.assertIs(profile["evaluated_here"], False)
        self.assertIs(profile["decided_here"], False)
        self.assertEqual(set(profile), {
            "id", "org_id", "profile_ref", "name", "dimensions",
            "access_levels", "evaluated_here", "decided_here",
            "created_by", "created_utc",
        })

    def test_undeclared_dimension_rejected_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.make_profile(dimensions=["device", "biometric"])
        profile = self.make_profile()
        self.assertEqual(profile["id"], "zvp-1")

    def test_duplicate_profile_ref_rejected(self):
        self.make_profile()
        with self.assertRaises(ValidationError):
            self.make_profile(name="Second profile, same ref")

    def test_viewer_cannot_create_and_outsider_cannot_read(self):
        with self.assertRaises(PermissionDenied):
            self.make_profile(actor=VIEWER)
        profile = self.make_profile()
        with self.assertRaises(PermissionDenied):
            self.ext.get_validation_profile(OUTSIDER, profile["id"])
        self.assertEqual(
            self.ext.get_validation_profile(STAFF, profile["id"])["id"],
            "zvp-1")


class TestValidationDecisions(AdditionFixture):
    """Entry (idx 679): decision records hold the plane's
    reported results and reported access level verbatim."""

    def setUp(self):
        super().setUp()
        self.profile = self.make_profile()

    def record(self, **overrides):
        kwargs = {
            "device_ref": "DEV-100",
            "subject_ref": "SUBJ-7",
            "dimension_results": {"device": "pass", "identity": "pass"},
            "reported_access_level": "full",
        }
        kwargs.update(overrides)
        return self.ext.record_validation_decision(
            MEMBER, self.profile["id"], **kwargs)

    def test_record_shape_and_labels(self):
        decision = self.record()
        self.assertEqual(decision["id"], "zvd-1")
        self.assertEqual(decision["dimension_results"],
                         {"device": "pass", "identity": "pass"})
        self.assertEqual(decision["reported_access_level"], "full")
        self.assertIs(decision["validated_here"], False)
        self.assertIs(decision["decided_here"], False)
        self.assertEqual(set(decision), {
            "id", "org_id", "profile_id", "device_ref", "subject_ref",
            "dimension_results", "reported_access_level",
            "validated_here", "decided_here", "created_by", "created_utc",
        })

    def test_result_for_undeclared_dimension_rejected(self):
        # The profile declares all four dimensions; a narrower
        # profile is the honest pin.
        narrow = self.make_profile(
            profile_ref="ZT-DEV", name="Device only",
            dimensions=["device"], access_levels=["full", "denied"])
        with self.assertRaises(ValidationError):
            self.ext.record_validation_decision(
                MEMBER, narrow["id"], "DEV-100", "SUBJ-7",
                {"identity": "pass"}, "full")
        decision = self.record()
        self.assertEqual(decision["id"], "zvd-1")

    def test_undeclared_access_level_rejected(self):
        with self.assertRaises(ValidationError):
            self.record(reported_access_level="root")
        with self.assertRaises(ValidationError):
            self.record(dimension_results={"device": "maybe"})
        decision = self.record()
        self.assertEqual(decision["id"], "zvd-1")

    def test_decision_changes_no_core_record(self):
        before = self.store.organization_summary(MEMBER, self.oid)
        self.record()
        after = self.store.organization_summary(MEMBER, self.oid)
        self.assertEqual(before, after)

    def test_missing_profile_is_not_found(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_validation_decision(
                MEMBER, "zvp-99", "DEV-100", "SUBJ-7",
                {"device": "pass"}, "full")


class TestAccessView(AdditionFixture):
    """Entry (idx 679): the current reported access level is
    derived at read from the latest recorded decision."""

    def setUp(self):
        super().setUp()
        self.profile = self.make_profile()

    def decide(self, level, results=None, device_ref="DEV-100"):
        return self.ext.record_validation_decision(
            MEMBER, self.profile["id"], device_ref, "SUBJ-7",
            results or {"device": "pass"}, level)

    def test_unreported_before_any_decision(self):
        view = self.ext.access_view(MEMBER, self.profile["id"], "DEV-100")
        self.assertEqual(view["state"], "unreported")
        self.assertIsNone(view["current_access_level"])
        self.assertEqual(view["decisions"], 0)
        self.assertIsNone(view["latest_decision_id"])
        self.assertIs(view["derived"], True)
        self.assertIs(view["stored"], False)
        self.assertIs(view["decided_here"], False)

    def test_latest_decision_is_current(self):
        self.decide("limited", {"device": "pass", "context": "fail"})
        second = self.decide("full")
        view = self.ext.access_view(MEMBER, self.profile["id"], "DEV-100")
        self.assertEqual(view["state"], "reported")
        self.assertEqual(view["current_access_level"], "full")
        self.assertEqual(view["decisions"], 2)
        self.assertEqual(view["latest_decision_id"], second["id"])
        self.assertEqual(view["method"], "derived_from_recorded_decisions")

    def test_view_is_per_device(self):
        self.decide("denied", device_ref="DEV-200")
        view = self.ext.access_view(MEMBER, self.profile["id"], "DEV-100")
        self.assertEqual(view["state"], "unreported")
        other = self.ext.access_view(MEMBER, self.profile["id"], "DEV-200")
        self.assertEqual(other["current_access_level"], "denied")


class MutantExtensionsAddition(MdmExtensionsAddition):
    """Earliest-reading mutant: the current decision is read
    from the FIRST recorded decision instead of the latest."""

    def _current_decision(self, decisions):
        return decisions[0] if decisions else None


class TestAccessViewNegativeControl(AdditionFixture):
    """Fresh negative control: the current-decision derivation.

    Canonical expectation: after two decisions reporting
    different access levels, the view's current level is the
    LATEST decision's level. The earliest-reading mutant
    reports the superseded level instead, and the canonical
    expectation rejects that outcome.
    """

    def _two_decisions(self, ext):
        profile = ext.create_validation_profile(
            MEMBER, self.oid, "ZT-NC", "Negative control profile",
            ["device"], ["limited", "full"])
        ext.record_validation_decision(
            MEMBER, profile["id"], "DEV-100", "SUBJ-7",
            {"device": "pass"}, "limited")
        ext.record_validation_decision(
            MEMBER, profile["id"], "DEV-100", "SUBJ-7",
            {"device": "pass"}, "full")
        return profile

    def test_canonical_expectation(self):
        profile = self._two_decisions(self.ext)
        view = self.ext.access_view(MEMBER, profile["id"], "DEV-100")
        self.assertEqual(view["current_access_level"], "full")

    def test_implementation_matches_canonical(self):
        profile = self._two_decisions(self.ext)
        view = self.ext.access_view(MEMBER, profile["id"], "DEV-100")
        self.assertEqual(view["latest_decision_id"], "zvd-2")

    def test_mutant_outcome_is_rejected(self):
        mutant = MutantExtensionsAddition(self.store)
        profile = self._two_decisions(mutant)
        view = mutant.access_view(MEMBER, profile["id"], "DEV-100")
        self.assertEqual(view["current_access_level"], "limited")
        with self.assertRaises(AssertionError):
            self.assertEqual(view["current_access_level"], "full")


class TestThreatDeployments(AdditionFixture):
    """Entry (idx 680): deployment records are labeled
    reference records; nothing is deployed here."""

    def test_record_shape_and_stub_labels(self):
        deployment = self.make_deployment()
        self.assertEqual(deployment["id"], "mtd-1")
        self.assertIs(deployment["reference_stub"], True)
        self.assertEqual(deployment["status"], "recorded_reference_only")
        self.assertIs(deployment["deployed_here"], False)
        self.assertEqual(set(deployment), {
            "id", "org_id", "device_ref", "deployment_mode",
            "reference_stub", "status", "deployed_here",
            "created_by", "created_utc",
        })

    def test_invalid_mode_rejected_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.make_deployment(deployment_mode="forced")
        deployment = self.make_deployment()
        self.assertEqual(deployment["id"], "mtd-1")

    def test_viewer_cannot_record(self):
        with self.assertRaises(PermissionDenied):
            self.make_deployment(actor=VIEWER)


class TestThreatEvents(AdditionFixture):
    """Entry (idx 680): threat events are the external engine's
    detections and remediations, recorded as reported."""

    def setUp(self):
        super().setUp()
        self.deployment = self.make_deployment()

    def record(self, **overrides):
        kwargs = {
            "scope": "network",
            "threat_label": "command-and-control beaconing",
            "connectivity": "off_connectivity",
            "reported_remediation": "reported_contained",
        }
        kwargs.update(overrides)
        return self.ext.record_threat_event(
            MEMBER, self.deployment["id"], **kwargs)

    def test_record_shape_stub_labels_and_device_from_deployment(self):
        event = self.record()
        self.assertEqual(event["id"], "mte-1")
        self.assertEqual(event["device_ref"], "DEV-100")
        self.assertIs(event["reference_stub"], True)
        self.assertEqual(event["status"], "recorded_reference_only")
        self.assertIs(event["detected_here"], False)
        self.assertIs(event["remediated_here"], False)

    def test_invalid_labels_rejected(self):
        with self.assertRaises(ValidationError):
            self.record(scope="perimeter")
        with self.assertRaises(ValidationError):
            self.record(connectivity="sometimes")
        with self.assertRaises(ValidationError):
            self.record(reported_remediation="remediated")
        event = self.record()
        self.assertEqual(event["id"], "mte-1")

    def test_reference_records_change_no_core_record(self):
        before = self.store.organization_summary(MEMBER, self.oid)
        self.record()
        self.record(scope="app", threat_label="sideloaded package",
                    connectivity="on_connectivity",
                    reported_remediation="reported_remediated")
        after = self.store.organization_summary(MEMBER, self.oid)
        self.assertEqual(before, after)

    def test_missing_deployment_is_not_found(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_threat_event(
                MEMBER, "mtd-99", "device", "label",
                "on_connectivity", "reported_contained")


class TestThreatSummary(AdditionFixture):
    """Entry (idx 680): summary counts derive at read over the
    recorded reference records."""

    def test_counts_derived_and_labeled(self):
        deployment = self.make_deployment()
        self.ext.record_threat_event(
            MEMBER, deployment["id"], "device", "rootkit signature",
            "on_connectivity", "reported_remediated")
        self.ext.record_threat_event(
            MEMBER, deployment["id"], "network", "beaconing",
            "off_connectivity", "reported_contained")
        self.ext.record_threat_event(
            MEMBER, deployment["id"], "network", "beaconing again",
            "on_connectivity", "reported_contained")
        summary = self.ext.threat_summary(MEMBER, self.oid)
        self.assertEqual(summary["deployments"], 1)
        self.assertEqual(summary["threat_events"], 3)
        self.assertEqual(summary["events_by_scope"],
                         {"device": 1, "network": 2})
        self.assertEqual(
            summary["events_by_reported_remediation"],
            {"reported_remediated": 1, "reported_contained": 2})
        self.assertIs(summary["reference_stub"], True)
        self.assertIs(summary["detected_here"], False)
        self.assertIs(summary["remediated_here"], False)
        self.assertIs(summary["derived"], True)
        self.assertIs(summary["stored"], False)


class TestCrossCutting(AdditionFixture):
    """The founding privacy invariant and the audit convention
    bind the whole addition surface."""

    def test_no_forbidden_key_on_any_stored_record(self):
        profile = self.make_profile()
        self.ext.record_validation_decision(
            MEMBER, profile["id"], "DEV-100", "SUBJ-7",
            {"device": "pass", "identity": "pass"}, "full")
        deployment = self.make_deployment()
        self.ext.record_threat_event(
            MEMBER, deployment["id"], "device", "label",
            "on_connectivity", "reported_contained")
        tables = (
            self.ext._validation_profiles, self.ext._validation_decisions,
            self.ext._threat_deployments, self.ext._threat_events,
        )
        for table in tables:
            self.assertTrue(table)
            for record in table.values():
                self.assertFalse(_all_keys(record) & FORBIDDEN_KEYS, record)

    def test_addition_mutations_audit_with_exta_prefix(self):
        profile = self.make_profile()
        self.ext.record_validation_decision(
            MEMBER, profile["id"], "DEV-100", "SUBJ-7",
            {"device": "pass"}, "full")
        self.make_deployment()
        actions = [e["action"] for e in self.store.audit.entries()]
        exta_actions = [a for a in actions if a.startswith("exta_")]
        self.assertEqual(exta_actions, [
            "exta_validation_profile_create",
            "exta_validation_decision_record",
            "exta_threat_deployment_record",
        ])


if __name__ == "__main__":
    unittest.main()
