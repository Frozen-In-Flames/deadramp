"""Final GAPS batch, third unit — LMS L2 no-signal addition.

Pins the third extension surface in
``src/lms/extensions_nosignal.py`` (``LmsExtensionsNoSignal``,
wrapping the core ``LmsStore``): the one open entry of the
GAPS.md section "No-Signal Addition — Learning Management L2
(Skillsoft Private Cloud, F1207261443)" (idx 971) — the
private-cloud hosting & managed delivery service registered
from the no-signal fork's classified function (``../ADDENDUM.md``
sections 7-9) — closed as drafted (stub-engine) as a labeled
reference implementation; see ``../BATCH-NOSIGNAL.md``.

Every record on the surface is pinned as a labeled reference
record (``reference_stub: True``, ``reference_transport: True``,
state ``recorded_reference_only``, with its not-here flags
False); vendor reports are held verbatim; views derive the
latest reported outcome at read via the ``_latest_outcome_label``
seam — that seam is this unit's fresh negative control (last
test class). Cross-cutting pins: the founding no-score invariant
over the whole no-signal surface (recursive key scan), no
``**kwargs`` on any public method (signature scan), core records
byte-identical across a full no-signal flow, RBAC denials
consuming no id, and ``extn_``-prefixed audit actions.
"""

import copy
import inspect
import unittest

from lms_helpers import ADMIN, AUDITOR, INSTRUCTOR, LEARNER, make_store
from lms.errors import NotFoundError, PermissionDenied, ValidationError
from lms.extensions_nosignal import LmsExtensionsNoSignal


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


def _bad_keys(obj):
    bad = set()
    for key in _all_keys(obj):
        lowered = key.lower()
        if (lowered == "score" or lowered.startswith("score_")
                or lowered.endswith("_score") or "grade" in lowered
                or lowered in ("content", "body", "payload", "url",
                               "password", "credential")):
            bad.add(key)
    return bad


class NoSignalFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.learner, self.course = make_store()
        self.ext = LmsExtensionsNoSignal(self.store)

    def make_deployment(self, title="Private Cloud A",
                        kind="private_cloud"):
        return self.ext.create_hosting_deployment(
            title, kind, ADMIN, provider_ref="provider-skillsoft",
            platform_ref="platform-percipio")


class TestHostingDeployments(NoSignalFixture):
    """Entry idx 971 (deployment half): records ABOUT a
    vendor-operated deployment, labeled reference, nothing
    hosted, provisioned, managed, or delivered here."""

    def test_deployment_shape_and_labels(self):
        dep = self.make_deployment()
        self.assertEqual(dep["id"], "hst-1")
        self.assertEqual(set(dep.keys()), {
            "id", "title", "deployment_kind", "provider_ref",
            "platform_ref", "core_course_id", "reference_stub",
            "reference_transport", "hosted_here", "provisioned_here",
            "managed_here", "delivered_here", "content_held", "state",
            "created_by", "created_utc",
        })
        self.assertIs(dep["reference_stub"], True)
        self.assertIs(dep["reference_transport"], True)
        self.assertIs(dep["hosted_here"], False)
        self.assertIs(dep["provisioned_here"], False)
        self.assertIs(dep["managed_here"], False)
        self.assertIs(dep["delivered_here"], False)
        self.assertIs(dep["content_held"], False)
        self.assertEqual(dep["state"], "recorded_reference_only")

    def test_deployment_kind_vocabulary(self):
        a = self.make_deployment("A", "private_cloud")
        b = self.make_deployment("B", "dedicated_private_cloud")
        self.assertEqual((a["id"], b["id"]), ("hst-1", "hst-2"))
        self.assertEqual(len(self.ext.list_hosting_deployments(ADMIN)), 2)
        self.assertEqual(
            len(self.ext.list_hosting_deployments(
                ADMIN, deployment_kind="private_cloud")), 1)
        with self.assertRaises(ValidationError):
            self.ext.create_hosting_deployment(
                "X", "public_cloud", ADMIN,
                provider_ref="provider-skillsoft",
                platform_ref="platform-percipio")
        with self.assertRaises(ValidationError):
            self.ext.list_hosting_deployments(
                ADMIN, deployment_kind="public_cloud")

    def test_core_binding_by_id_only(self):
        dep = self.ext.create_hosting_deployment(
            "Bound", "private_cloud", ADMIN,
            provider_ref="provider-skillsoft",
            platform_ref="platform-percipio",
            core_course_id=self.course["id"])
        self.assertEqual(dep["core_course_id"], self.course["id"])
        with self.assertRaises(NotFoundError):
            self.ext.create_hosting_deployment(
                "Ghost", "private_cloud", ADMIN,
                provider_ref="provider-skillsoft",
                platform_ref="platform-percipio",
                core_course_id="crs-999")
        nxt = self.make_deployment("Next")
        self.assertEqual(nxt["id"], "hst-2")

    def test_core_records_byte_identical_across_full_flow(self):
        course_before = copy.deepcopy(
            self.store.get_course(self.course["id"], ADMIN))
        dep = self.ext.create_hosting_deployment(
            "Bound", "private_cloud", ADMIN,
            provider_ref="provider-skillsoft",
            platform_ref="platform-percipio",
            core_course_id=self.course["id"])
        self.ext.record_delivery_report(dep["id"], "web_browser",
                                        "reported_available", ADMIN)
        self.ext.deployment_view(dep["id"], ADMIN)
        self.ext.hosting_summary(ADMIN)
        self.assertEqual(
            self.store.get_course(self.course["id"], ADMIN), course_before)


class TestDeliveryReports(NoSignalFixture):
    """Entry idx 971 (delivery half): vendor outcomes verbatim,
    counts held exactly as reported, nothing transmitted."""

    def test_report_shape_labels_and_verbatim_label(self):
        dep = self.make_deployment()
        report = self.ext.record_delivery_report(
            dep["id"], "hosted_platform", "reported_available", ADMIN,
            reported_learner_count=5000)
        self.assertEqual(report["id"], "dlr-1")
        self.assertEqual(report["outcome_label"], "reported_available")
        self.assertEqual(report["outcome_basis"], "vendor_reported")
        self.assertEqual(report["reported_learner_count"], 5000)
        self.assertIs(report["reference_stub"], True)
        self.assertIs(report["reference_transport"], True)
        self.assertIs(report["transmitted_here"], False)
        self.assertIs(report["hosted_here"], False)
        self.assertIs(report["delivered_here"], False)
        self.assertEqual(report["state"], "recorded_reference_only")

    def test_view_derives_count_and_latest_outcome(self):
        dep = self.make_deployment()
        stored = self.ext.get_hosting_deployment(dep["id"], ADMIN)
        self.assertNotIn("latest_outcome_label", stored)
        self.assertNotIn("delivery_report_count", stored)
        self.ext.record_delivery_report(dep["id"], "web_browser",
                                        "reported_available", ADMIN)
        self.ext.record_delivery_report(dep["id"], "mobile_app",
                                        "reported_updated", ADMIN)
        view = self.ext.deployment_view(dep["id"], ADMIN)
        self.assertEqual(view["delivery_report_count"], 2)
        self.assertEqual(view["latest_outcome_label"], "reported_updated")
        self.assertEqual(view["outcome_method"],
                         "latest_recorded_vendor_report")
        other = self.make_deployment("Quiet Deployment")
        view = self.ext.deployment_view(other["id"], ADMIN)
        self.assertEqual(view["delivery_report_count"], 0)
        self.assertIsNone(view["latest_outcome_label"])

    def test_bad_channel_and_bad_counts_rejected_no_id_consumed(self):
        dep = self.make_deployment()
        with self.assertRaises(ValidationError):
            self.ext.record_delivery_report(dep["id"], "carrier_pigeon",
                                            "reported_available", ADMIN)
        for bad in (True, 1.5, -1, "5000"):
            with self.assertRaises(ValidationError):
                self.ext.record_delivery_report(
                    dep["id"], "web_browser", "reported_available", ADMIN,
                    reported_learner_count=bad)
        with self.assertRaises(NotFoundError):
            self.ext.record_delivery_report("hst-999", "web_browser",
                                            "reported_available", ADMIN)
        report = self.ext.record_delivery_report(
            dep["id"], "web_browser", "reported_available", ADMIN)
        self.assertEqual(report["id"], "dlr-1")


class TestHostingSummary(NoSignalFixture):
    """Summary: deterministic counts over the recorded reference
    records only, latest outcome derived at read."""

    def test_summary_counts_and_latest(self):
        self.make_deployment()
        self.make_deployment("Dedicated B", "dedicated_private_cloud")
        self.ext.record_delivery_report("hst-1", "web_browser",
                                        "reported_available", ADMIN)
        self.ext.record_delivery_report("hst-2", "mobile_app",
                                        "reported_retired", ADMIN)
        summary = self.ext.hosting_summary(ADMIN)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["counts_basis"],
                         "recorded_reference_records_only")
        self.assertIs(summary["reference_stub"], True)
        self.assertIs(summary["hosted_here"], False)
        self.assertEqual(summary["deployments"], 2)
        self.assertEqual(summary["deployments_by_kind"]["private_cloud"], 1)
        self.assertEqual(
            summary["deployments_by_kind"]["dedicated_private_cloud"], 1)
        self.assertEqual(summary["delivery_reports"], 2)
        self.assertEqual(summary["latest_outcome_label"], "reported_retired")

    def test_summary_empty_and_learner_denied(self):
        summary = self.ext.hosting_summary(AUDITOR)
        self.assertEqual(summary["deployments"], 0)
        self.assertIsNone(summary["latest_outcome_label"])
        with self.assertRaises(PermissionDenied):
            self.ext.hosting_summary(LEARNER)


class TestCrossCutting(NoSignalFixture):
    """Cross-cutting pins: no-score/content key scan, no kwargs
    smuggling, no floats, RBAC, extn_ audit actions."""

    def test_no_score_or_content_key_anywhere_on_surface(self):
        dep = self.make_deployment()
        surfaces = [
            dep,
            self.ext.record_delivery_report(
                dep["id"], "web_browser", "reported_available", ADMIN,
                reported_learner_count=42),
            self.ext.deployment_view(dep["id"], ADMIN),
            self.ext.list_hosting_deployments(ADMIN),
            self.ext.list_delivery_reports(ADMIN),
            self.ext.hosting_summary(ADMIN),
        ]
        for surface in surfaces:
            with self.subTest(surface=type(surface).__name__):
                self.assertEqual(_bad_keys(surface), set())
        # no hosting/delivery-shaped execution method exists
        for name in dir(self.ext):
            self.assertNotIn("provision", name)
            self.assertNotIn("execute", name)

    def test_no_kwargs_smuggling_and_no_float_values(self):
        dep = self.make_deployment()
        with self.assertRaises(TypeError):
            self.ext.create_hosting_deployment(
                "X", "private_cloud", ADMIN,
                provider_ref="p", platform_ref="q", content="bytes")
        with self.assertRaises(TypeError):
            self.ext.record_delivery_report(
                dep["id"], "web_browser", "reported_available", ADMIN,
                password="secret")
        for name, member in inspect.getmembers(
                LmsExtensionsNoSignal, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue
            for param in inspect.signature(member).parameters.values():
                self.assertNotEqual(param.kind, inspect.Parameter.VAR_KEYWORD,
                                    "%s accepts **kwargs" % name)
        surfaces = [
            dep,
            self.ext.record_delivery_report(
                dep["id"], "web_browser", "reported_available", ADMIN,
                reported_learner_count=7),
            self.ext.deployment_view(dep["id"], ADMIN),
            self.ext.hosting_summary(ADMIN),
        ]

        def _floats(obj):
            found = []
            if isinstance(obj, float):
                found.append(obj)
            elif isinstance(obj, dict):
                for value in obj.values():
                    found += _floats(value)
            elif isinstance(obj, (list, tuple)):
                for value in obj:
                    found += _floats(value)
            return found

        for surface in surfaces:
            self.assertEqual(_floats(surface), [])

    def test_rbac_denials_consume_no_id(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_hosting_deployment(
                "X", "private_cloud", INSTRUCTOR,
                provider_ref="p", platform_ref="q")
        with self.assertRaises(PermissionDenied):
            self.ext.create_hosting_deployment(
                "X", "private_cloud", LEARNER,
                provider_ref="p", platform_ref="q")
        with self.assertRaises(PermissionDenied):
            self.ext.create_hosting_deployment(
                "X", "private_cloud", AUDITOR,
                provider_ref="p", platform_ref="q")
        dep = self.make_deployment()
        self.assertEqual(dep["id"], "hst-1")
        self.assertEqual(
            self.ext.get_hosting_deployment(dep["id"], LEARNER)["id"],
            "hst-1")
        self.assertEqual(
            self.ext.get_hosting_deployment(dep["id"], AUDITOR)["id"],
            "hst-1")
        with self.assertRaises(PermissionDenied):
            self.ext.record_delivery_report(dep["id"], "web_browser",
                                            "reported_available", INSTRUCTOR)

    def test_audit_actions_are_extn_prefixed(self):
        dep = self.make_deployment()
        self.ext.record_delivery_report(dep["id"], "web_browser",
                                        "reported_available", ADMIN)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("extn_hosting_deployment_create", actions)
        self.assertIn("extn_delivery_report_record", actions)


class MutantNoSignal(LmsExtensionsNoSignal):
    """Mutant: the latest-outcome seam reads the FIRST report."""

    @staticmethod
    def _latest_outcome_label(reports):
        return reports[0]["outcome_label"] if reports else None


class TestNegativeControlLatestOutcome(NoSignalFixture):
    """Fresh mutation-verified negative control: the
    ``_latest_outcome_label`` seam. Canonical views read the
    LATEST recorded report's label; a first-reading mutant reads
    the earliest and must NOT satisfy the canonical expectation."""

    def _two_reports(self, ext):
        dep = ext.create_hosting_deployment(
            "Deployment", "private_cloud", ADMIN,
            provider_ref="provider-skillsoft",
            platform_ref="platform-percipio")
        ext.record_delivery_report(dep["id"], "web_browser",
                                   "reported_available", ADMIN)
        ext.record_delivery_report(dep["id"], "mobile_app",
                                   "reported_retired", ADMIN)
        return dep

    def test_canonical_view_uses_latest_outcome(self):
        dep = self._two_reports(self.ext)
        view = self.ext.deployment_view(dep["id"], ADMIN)
        self.assertEqual(view["latest_outcome_label"], "reported_retired")
        summary = self.ext.hosting_summary(ADMIN)
        self.assertEqual(summary["latest_outcome_label"], "reported_retired")

    def test_mutant_earliest_differs(self):
        mutant = MutantNoSignal(self.store)
        dep = self._two_reports(mutant)
        view = mutant.deployment_view(dep["id"], ADMIN)
        self.assertEqual(view["latest_outcome_label"], "reported_available")
        with self.assertRaises(AssertionError):
            self.assertEqual(view["latest_outcome_label"], "reported_retired")

    def test_seam_directly(self):
        reports = [{"outcome_label": "first"},
                   {"outcome_label": "second"}]
        self.assertEqual(
            LmsExtensionsNoSignal._latest_outcome_label(reports), "second")
        self.assertIsNone(LmsExtensionsNoSignal._latest_outcome_label([]))
        self.assertEqual(
            MutantNoSignal._latest_outcome_label(reports), "first")


if __name__ == "__main__":
    unittest.main()
