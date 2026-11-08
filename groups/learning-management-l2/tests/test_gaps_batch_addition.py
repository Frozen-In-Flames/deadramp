"""Final GAPS batch, second unit — LMS L2 remainder addition.

Pins the second extension surface in
``src/lms/extensions_addition.py`` (``LmsExtensionsAddition``,
wrapping the core ``LmsStore``): the one open entry of the
GAPS.md section "Remainder Addition — Learning Management
L2 (+1 fork)" (idx 678) — the licensed content library &
practice-lab environments registered from the addition fork
Percipio's described function (``../ADDENDUM.md`` §5) — closed
as drafted (stub-engine) as a labeled reference implementation;
see ``../BATCH-ADDITION.md``.

Every record on the surface is pinned as a labeled reference
record (``reference_stub: True``, ``reference_transport: True``,
state ``recorded_reference_only``, with its not-here flags
False); platform reports are held verbatim; views derive the
latest reported outcome at read via the ``_latest_outcome_label``
seam — that seam is this unit's fresh negative control (last
test class). Cross-cutting pins: the founding no-score invariant
over the whole addition surface (recursive key scan), no
``**kwargs`` on any public method (signature scan), core records
byte-identical across a full addition flow, RBAC denials
consuming no id, and ``exta_``-prefixed audit actions.
"""

import copy
import inspect
import unittest

from lms_helpers import ADMIN, AUDITOR, INSTRUCTOR, LEARNER, make_store
from lms.errors import NotFoundError, PermissionDenied, ValidationError
from lms.extensions_addition import LmsExtensionsAddition


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


class AdditionFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.learner, self.course = make_store()
        self.store.create_learner("erin", "Erin Learner", ADMIN)
        self.ext = LmsExtensionsAddition(self.store)

    def make_item(self, title="Video Course A", format_kind="video_course"):
        return self.ext.create_library_item(
            title, format_kind, ADMIN, provider_ref="provider-percipio")


class TestLibraryItems(AdditionFixture):
    """Entry idx 678 (library half): records ABOUT the external
    catalogue, labeled reference, content never held or hosted."""

    def test_item_shape_and_labels(self):
        item = self.make_item()
        self.assertEqual(item["id"], "lib-1")
        self.assertEqual(set(item.keys()), {
            "id", "title", "format_kind", "provider_ref",
            "core_course_id", "core_content_id", "reference_stub",
            "reference_transport", "hosted_here", "content_held",
            "delivered_here", "administered_here", "state",
            "created_by", "created_utc",
        })
        self.assertIs(item["reference_stub"], True)
        self.assertIs(item["reference_transport"], True)
        self.assertIs(item["hosted_here"], False)
        self.assertIs(item["content_held"], False)
        self.assertIs(item["delivered_here"], False)
        self.assertIs(item["administered_here"], False)
        self.assertEqual(item["state"], "recorded_reference_only")

    def test_forks_own_format_vocabulary(self):
        kinds = ["video_course", "ebook", "audiobook", "boot_camp",
                 "practice_lab", "assessment_content"]
        for i, kind in enumerate(kinds, start=1):
            item = self.ext.create_library_item(
                "Item %s" % kind, kind, ADMIN,
                provider_ref="provider-percipio")
            self.assertEqual(item["id"], "lib-%d" % i)
        self.assertEqual(len(self.ext.list_library_items(ADMIN)), 6)
        self.assertEqual(
            len(self.ext.list_library_items(ADMIN,
                                            format_kind="ebook")), 1)
        with self.assertRaises(ValidationError):
            self.ext.create_library_item("X", "streaming_video", ADMIN,
                                         provider_ref="provider-percipio")
        with self.assertRaises(ValidationError):
            self.ext.list_library_items(ADMIN, format_kind="streaming_video")

    def test_assessment_content_is_catalogue_not_administration(self):
        item = self.make_item("Skills Check Pack", "assessment_content")
        self.assertEqual(item["format_kind"], "assessment_content")
        self.assertIs(item["administered_here"], False)
        # no administration-shaped method exists on the surface
        for name in dir(self.ext):
            self.assertNotIn("administer", name)
            self.assertNotIn("score", name)

    def test_core_binding_by_id_and_mismatch_rejected(self):
        content = self.store.create_content_item(
            "Safety SCORM", "scorm_2004", ADMIN,
            course_id=self.course["id"])
        other = self.store.create_course("Other Course", ADMIN)
        item = self.ext.create_library_item(
            "Bound", "video_course", ADMIN,
            provider_ref="provider-percipio",
            core_course_id=self.course["id"],
            core_content_id=content["id"])
        self.assertEqual(item["core_content_id"], content["id"])
        with self.assertRaises(ValidationError):
            self.ext.create_library_item(
                "Mismatch", "ebook", ADMIN,
                provider_ref="provider-percipio",
                core_course_id=other["id"],
                core_content_id=content["id"])
        with self.assertRaises(NotFoundError):
            self.ext.create_library_item(
                "Ghost", "ebook", ADMIN,
                provider_ref="provider-percipio", core_course_id="crs-999")
        with self.assertRaises(NotFoundError):
            self.ext.create_library_item(
                "Ghost", "ebook", ADMIN,
                provider_ref="provider-percipio", core_content_id="cnt-999")

    def test_core_records_byte_identical_across_full_flow(self):
        content = self.store.create_content_item(
            "Safety SCORM", "scorm_2004", ADMIN,
            course_id=self.course["id"])
        course_before = copy.deepcopy(
            self.store.get_course(self.course["id"], ADMIN))
        content_before = copy.deepcopy(
            self.store.get_content_item(content["id"], ADMIN))
        item = self.ext.create_library_item(
            "Bound", "practice_lab", ADMIN,
            provider_ref="provider-percipio",
            core_course_id=self.course["id"],
            core_content_id=content["id"])
        self.ext.record_access_report(item["id"], "web_browser",
                                      "reported_available", ADMIN)
        self.ext.record_lab_environment(item["id"], "lab-env-1", ADMIN)
        self.ext.library_item_view(item["id"], ADMIN)
        self.ext.library_summary(ADMIN)
        self.assertEqual(
            self.store.get_course(self.course["id"], ADMIN), course_before)
        self.assertEqual(
            self.store.get_content_item(content["id"], ADMIN),
            content_before)


class TestAccessReports(AdditionFixture):
    """Entry idx 678 (reports): platform outcomes verbatim,
    counts held exactly as reported, nothing transmitted."""

    def test_report_shape_labels_and_verbatim_label(self):
        item = self.make_item()
        report = self.ext.record_access_report(
            item["id"], "mobile_app", "reported_available", ADMIN,
            reported_item_count=1200)
        self.assertEqual(report["id"], "acc-1")
        self.assertEqual(report["outcome_label"], "reported_available")
        self.assertEqual(report["outcome_basis"], "platform_reported")
        self.assertEqual(report["reported_item_count"], 1200)
        self.assertIs(report["reference_stub"], True)
        self.assertIs(report["reference_transport"], True)
        self.assertIs(report["transmitted_here"], False)
        self.assertEqual(report["state"], "recorded_reference_only")

    def test_view_derives_count_and_latest_outcome(self):
        item = self.make_item()
        stored = self.ext.get_library_item(item["id"], ADMIN)
        self.assertNotIn("latest_outcome_label", stored)
        self.assertNotIn("access_report_count", stored)
        self.ext.record_access_report(item["id"], "web_browser",
                                      "reported_available", ADMIN)
        self.ext.record_access_report(item["id"], "mobile_app",
                                      "reported_updated", ADMIN)
        view = self.ext.library_item_view(item["id"], ADMIN)
        self.assertEqual(view["access_report_count"], 2)
        self.assertEqual(view["latest_outcome_label"], "reported_updated")
        self.assertEqual(view["outcome_method"],
                         "latest_recorded_platform_report")
        # a second item with no reports derives None, never a guess
        other = self.make_item("Quiet Ebook", "ebook")
        view = self.ext.library_item_view(other["id"], ADMIN)
        self.assertEqual(view["access_report_count"], 0)
        self.assertIsNone(view["latest_outcome_label"])

    def test_bad_channel_and_bad_counts_rejected_no_id_consumed(self):
        item = self.make_item()
        with self.assertRaises(ValidationError):
            self.ext.record_access_report(item["id"], "carrier_pigeon",
                                          "reported_available", ADMIN)
        for bad in (True, 1.5, -1, "1200"):
            with self.assertRaises(ValidationError):
                self.ext.record_access_report(
                    item["id"], "web_browser", "reported_available", ADMIN,
                    reported_item_count=bad)
        with self.assertRaises(NotFoundError):
            self.ext.record_access_report("lib-999", "web_browser",
                                          "reported_available", ADMIN)
        report = self.ext.record_access_report(
            item["id"], "web_browser", "reported_available", ADMIN)
        self.assertEqual(report["id"], "acc-1")


class TestLabEnvironments(AdditionFixture):
    """Entry idx 678 (lab half): environments named by opaque
    reference only, bound to practice_lab items, never run."""

    def test_lab_record_shape_and_labels(self):
        item = self.make_item("Cloud Lab Pack", "practice_lab")
        lab = self.ext.record_lab_environment(item["id"], "lab-env-9",
                                              ADMIN)
        self.assertEqual(lab["id"], "lab-1")
        self.assertIs(lab["reference_stub"], True)
        self.assertIs(lab["reference_transport"], True)
        self.assertIs(lab["provisioned_here"], False)
        self.assertIs(lab["executed_here"], False)
        self.assertIs(lab["content_held"], False)
        self.assertEqual(lab["state"], "recorded_reference_only")
        self.assertEqual(
            len(self.ext.list_lab_environments(ADMIN,
                                               library_item_id=item["id"])),
            1)

    def test_lab_requires_practice_lab_item(self):
        item = self.make_item()
        with self.assertRaises(ValidationError):
            self.ext.record_lab_environment(item["id"], "lab-env-1", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.record_lab_environment("lib-999", "lab-env-1", ADMIN)
        lab_item = self.make_item("Real Lab", "practice_lab")
        lab = self.ext.record_lab_environment(lab_item["id"], "lab-env-1",
                                              ADMIN)
        self.assertEqual(lab["id"], "lab-1")


class TestLibrarySummary(AdditionFixture):
    """Summary: deterministic counts over the recorded reference
    records only, latest outcome derived at read."""

    def test_summary_counts_and_latest(self):
        self.make_item()
        self.make_item("Book", "ebook")
        lab_item = self.make_item("Lab", "practice_lab")
        self.ext.record_lab_environment(lab_item["id"], "lab-env-1", ADMIN)
        self.ext.record_access_report("lib-1", "web_browser",
                                      "reported_available", ADMIN)
        self.ext.record_access_report("lib-2", "mobile_app",
                                      "reported_retired", ADMIN)
        summary = self.ext.library_summary(ADMIN)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["counts_basis"],
                         "recorded_reference_records_only")
        self.assertEqual(summary["library_items"], 3)
        self.assertEqual(summary["items_by_format"]["video_course"], 1)
        self.assertEqual(summary["items_by_format"]["boot_camp"], 0)
        self.assertEqual(summary["access_reports"], 2)
        self.assertEqual(summary["lab_environments"], 1)
        self.assertEqual(summary["latest_outcome_label"], "reported_retired")

    def test_summary_empty_and_learner_denied(self):
        summary = self.ext.library_summary(AUDITOR)
        self.assertEqual(summary["library_items"], 0)
        self.assertIsNone(summary["latest_outcome_label"])
        with self.assertRaises(PermissionDenied):
            self.ext.library_summary(LEARNER)


class TestCrossCutting(AdditionFixture):
    """Cross-cutting pins: no-score/content key scan, no kwargs
    smuggling, RBAC, exta_ audit actions."""

    def test_no_score_or_content_key_anywhere_on_surface(self):
        item = self.make_item("Check Pack", "assessment_content")
        lab_item = self.make_item("Lab", "practice_lab")
        surfaces = [
            item,
            self.ext.record_access_report(item["id"], "web_browser",
                                          "reported_available", ADMIN,
                                          reported_item_count=42),
            self.ext.record_lab_environment(lab_item["id"], "lab-env-1",
                                            ADMIN),
            self.ext.library_item_view(item["id"], ADMIN),
            self.ext.list_library_items(ADMIN),
            self.ext.list_access_reports(ADMIN),
            self.ext.list_lab_environments(ADMIN),
            self.ext.library_summary(ADMIN),
        ]
        for surface in surfaces:
            with self.subTest(surface=type(surface).__name__):
                self.assertEqual(_bad_keys(surface), set())

    def test_no_kwargs_smuggling_and_no_float_values(self):
        item = self.make_item()
        with self.assertRaises(TypeError):
            self.ext.create_library_item(
                "X", "ebook", ADMIN, provider_ref="p", content="bytes")
        with self.assertRaises(TypeError):
            self.ext.record_lab_environment(
                item["id"], "lab-1", ADMIN, password="secret")
        for name, member in inspect.getmembers(
                LmsExtensionsAddition, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue
            for param in inspect.signature(member).parameters.values():
                self.assertNotEqual(param.kind, inspect.Parameter.VAR_KEYWORD,
                                    "%s accepts **kwargs" % name)
        surfaces = [
            item,
            self.ext.record_access_report(item["id"], "web_browser",
                                          "reported_available", ADMIN,
                                          reported_item_count=7),
            self.ext.library_item_view(item["id"], ADMIN),
            self.ext.library_summary(ADMIN),
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
            self.ext.create_library_item("X", "ebook", INSTRUCTOR,
                                         provider_ref="p")
        with self.assertRaises(PermissionDenied):
            self.ext.create_library_item("X", "ebook", LEARNER,
                                         provider_ref="p")
        with self.assertRaises(PermissionDenied):
            self.ext.create_library_item("X", "ebook", AUDITOR,
                                         provider_ref="p")
        item = self.make_item()
        self.assertEqual(item["id"], "lib-1")
        # reads: learner and auditor may read the reference records
        self.assertEqual(
            self.ext.get_library_item(item["id"], LEARNER)["id"], "lib-1")
        self.assertEqual(
            self.ext.get_library_item(item["id"], AUDITOR)["id"], "lib-1")
        with self.assertRaises(PermissionDenied):
            self.ext.record_access_report(item["id"], "web_browser",
                                          "reported_available", INSTRUCTOR)

    def test_audit_actions_are_exta_prefixed(self):
        item = self.make_item("Lab Pack", "practice_lab")
        self.ext.record_access_report(item["id"], "web_browser",
                                      "reported_available", ADMIN)
        self.ext.record_lab_environment(item["id"], "lab-env-1", ADMIN)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("exta_library_item_create", actions)
        self.assertIn("exta_access_report_record", actions)
        self.assertIn("exta_lab_environment_record", actions)


class MutantAddition(LmsExtensionsAddition):
    """Mutant: the latest-outcome seam reads the FIRST report."""

    @staticmethod
    def _latest_outcome_label(reports):
        return reports[0]["outcome_label"] if reports else None


class TestNegativeControlLatestOutcome(AdditionFixture):
    """Fresh mutation-verified negative control: the
    ``_latest_outcome_label`` seam. Canonical views read the
    LATEST recorded report's label; a first-reading mutant reads
    the earliest and must NOT satisfy the canonical expectation."""

    def _two_reports(self, ext):
        item = ext.create_library_item(
            "Course", "video_course", ADMIN,
            provider_ref="provider-percipio")
        ext.record_access_report(item["id"], "web_browser",
                                 "reported_available", ADMIN)
        ext.record_access_report(item["id"], "mobile_app",
                                 "reported_retired", ADMIN)
        return item

    def test_canonical_view_uses_latest_outcome(self):
        item = self._two_reports(self.ext)
        view = self.ext.library_item_view(item["id"], ADMIN)
        self.assertEqual(view["latest_outcome_label"], "reported_retired")
        summary = self.ext.library_summary(ADMIN)
        self.assertEqual(summary["latest_outcome_label"], "reported_retired")

    def test_mutant_earliest_differs(self):
        mutant = MutantAddition(self.store)
        item = self._two_reports(mutant)
        view = mutant.library_item_view(item["id"], ADMIN)
        self.assertEqual(view["latest_outcome_label"], "reported_available")
        with self.assertRaises(AssertionError):
            self.assertEqual(view["latest_outcome_label"], "reported_retired")

    def test_seam_directly(self):
        reports = [{"outcome_label": "first"},
                   {"outcome_label": "second"}]
        self.assertEqual(
            LmsExtensionsAddition._latest_outcome_label(reports), "second")
        self.assertIsNone(LmsExtensionsAddition._latest_outcome_label([]))
        self.assertEqual(
            MutantAddition._latest_outcome_label(reports), "first")


if __name__ == "__main__":
    unittest.main()
