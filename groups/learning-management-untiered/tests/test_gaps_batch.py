"""Final GAPS batch tests — Learning Management untiered set extensions.

Traces to: the 6 open entries of "Untiered Set 25 — Learning
Management (1 fork, tier null)" in ../../../GAPS.md (idx 951–956 in
../../../gaps-batch/inventory.json), built in
``src/lms/extensions.py`` (see ../BATCH.md for dispositions).

Per entry: idx 951 virtual classroom (built, records form),
idx 952 real-time collaboration & recording (reference, re-judged),
idx 953 authoring workspace (reference stub), idx 954 media
repository (built, metadata registry), idx 955 assignments /
evaluations / grading (built, records form — no score computed),
idx 956 user administration (built, action records).

Cross-cutting pins: the founding no-score invariant extended to
grade-shaped keys over every extension record and view; a
tier-null key scan (no tier/baseline key exists on this surface at
all); denied writes consume no id; every extension mutation lands
on the core audit log with an ``ext_``-prefixed action; extension
operations never modify a core record.
"""

import inspect
import os
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from lms_helpers import ADMIN, AUDITOR, INSTRUCTOR, LEARNER, make_store  # noqa: E402

from lms.errors import NotFoundError, PermissionDenied, ValidationError  # noqa: E402
from lms.extensions import LmsExtensions, NO_RECORDED_ACTION  # noqa: E402

SHA256 = "a" * 64


def _battery(store, course):
    """One record or view from every extension surface."""
    ext = LmsExtensions(store)
    session = ext.create_classroom_session(
        course["id"], "Algebra Live", "2027-01-10T15:00:00", INSTRUCTOR,
        participant_refs=["carol"])
    outcome = ext.record_classroom_outcome(session["id"], "held", INSTRUCTOR)
    collaboration = ext.create_collaboration_record(
        INSTRUCTOR, course_id=course["id"], session_id=session["id"],
        participant_refs=["carol"], shared_content_refs=["deck-1"])
    recording = ext.record_recording_record(
        collaboration["id"], "rec-1", INSTRUCTOR, sha256=SHA256,
        duration_seconds=1800)
    draft = ext.create_authoring_draft("New Lesson", ADMIN,
                                       course_id=course["id"], body="draft")
    item = ext.create_media_item("Lecture Capture", "media-1", "video",
                                 ADMIN, course_id=course["id"],
                                 sha256=SHA256, size_bytes=1024)
    share = ext.record_media_share(item["id"], ADMIN, learner_ref="carol")
    assignment = ext.create_coursework_assignment(
        course["id"], "Essay 1", INSTRUCTOR, due_date="2027-02-01")
    submission = ext.record_submission(assignment["id"], "carol", "work-1",
                                       INSTRUCTOR, sha256=SHA256)
    evaluation = ext.record_evaluation(submission["id"], "meets standard",
                                       ADMIN)
    admin_action = ext.record_user_admin_action("carol", "provisioned", ADMIN)
    return ext, [
        session, outcome, collaboration, recording, draft, item, share,
        ext.get_media_item(item["id"], ADMIN), assignment,
        ext.get_coursework_assignment(assignment["id"], ADMIN), submission,
        evaluation, admin_action, ext.user_admin_view("carol", ADMIN),
        ext.classroom_summary(ADMIN), ext.coursework_summary(ADMIN),
    ]


class TestClassroomSessions(unittest.TestCase):
    """Idx 951 — virtual classroom delivery runtime (built, records)."""

    def setUp(self):
        self.store, self.learner, self.course = make_store()
        self.ext = LmsExtensions(self.store)

    def test_session_record_shape_and_not_delivered(self):
        """Idx 951: a session is an administration record — schedule,
        course binding, participants — carrying delivered_here False;
        nothing is delivered to anyone by recording it."""
        session = self.ext.create_classroom_session(
            self.course["id"], "Algebra Live", "2027-01-10T15:00:00",
            INSTRUCTOR, ends_at="2027-01-10T16:00:00",
            participant_refs=["carol"])
        self.assertEqual(session["id"], "vcs-1")
        self.assertEqual(session["course_id"], self.course["id"])
        self.assertEqual(session["participant_refs"], ["carol"])
        self.assertIs(session["delivered_here"], False)
        view = self.ext.get_classroom_session(session["id"], INSTRUCTOR)
        self.assertEqual(view["outcome_count"], 0)
        self.assertIsNone(view["latest_outcome_label"])

    def test_session_binds_core_event_with_course_rule(self):
        """Idx 951: a session may bind one of the course's core events;
        an event of another course is rejected (the L2 delivery rule)."""
        other = self.store.create_course("Other Course", ADMIN)
        event = self.store.create_event(
            "Kickoff", "2027-01-10T15:00:00", INSTRUCTOR,
            course_id=self.course["id"])
        session = self.ext.create_classroom_session(
            self.course["id"], "Kickoff Live", "2027-01-10T15:00:00",
            INSTRUCTOR, event_id=event["id"])
        self.assertEqual(session["event_id"], event["id"])
        with self.assertRaises(ValidationError):
            self.ext.create_classroom_session(
                other["id"], "Wrong Course", "2027-01-10T15:00:00",
                INSTRUCTOR, event_id=event["id"])

    def test_session_validation(self):
        """Idx 951: bad datetimes, an end before the start, an unknown
        course, and an unknown participant are all rejected whole."""
        with self.assertRaises(ValidationError):
            self.ext.create_classroom_session(
                self.course["id"], "Bad", "not-a-date", INSTRUCTOR)
        with self.assertRaises(ValidationError):
            self.ext.create_classroom_session(
                self.course["id"], "Bad", "2027-01-10T16:00:00", INSTRUCTOR,
                ends_at="2027-01-10T15:00:00")
        with self.assertRaises(NotFoundError):
            self.ext.create_classroom_session(
                "crs-99", "Bad", "2027-01-10T15:00:00", INSTRUCTOR)
        with self.assertRaises(NotFoundError):
            self.ext.create_classroom_session(
                self.course["id"], "Bad", "2027-01-10T15:00:00", INSTRUCTOR,
                participant_refs=["ghost"])

    def test_outcomes_recorded_verbatim_and_derived_at_read(self):
        """Idx 951: outcome labels are caller-reported text stored
        verbatim; the view's count and latest label are derived at
        read from the outcome records, never stored."""
        session = self.ext.create_classroom_session(
            self.course["id"], "Algebra Live", "2027-01-10T15:00:00",
            INSTRUCTOR, participant_refs=["carol"])
        first = self.ext.record_classroom_outcome(
            session["id"], "held — connection dropped twice", INSTRUCTOR)
        self.assertEqual(first["outcome_label"],
                         "held — connection dropped twice")
        self.assertEqual(first["outcome_basis"], "caller_reported")
        self.ext.record_classroom_outcome(session["id"], "rescheduled",
                                          INSTRUCTOR)
        view = self.ext.get_classroom_session(session["id"], INSTRUCTOR)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_outcome_label"], "rescheduled")
        self.assertNotIn("latest_outcome_label", self.ext._classroom_sessions[session["id"]])

    def test_classroom_summary_counts(self):
        """Idx 951: the summary is deterministic counts over the
        records, labeled with its method (report_read)."""
        session = self.ext.create_classroom_session(
            self.course["id"], "A", "2027-01-10T15:00:00", INSTRUCTOR)
        self.ext.create_classroom_session(
            self.course["id"], "B", "2027-01-11T15:00:00", INSTRUCTOR)
        self.ext.record_classroom_outcome(session["id"], "held", INSTRUCTOR)
        summary = self.ext.classroom_summary(ADMIN)
        self.assertEqual(summary["classroom_sessions"], 2)
        self.assertEqual(summary["classroom_outcomes"], 1)
        self.assertEqual(summary["sessions_with_outcomes"], 1)
        self.assertEqual(summary["method"], "deterministic_counts")
        with self.assertRaises(PermissionDenied):
            self.ext.classroom_summary(LEARNER)

    def test_learner_scope_is_participation(self):
        """Idx 951: a learner-role actor reads only sessions they
        participate in — in lists and in single reads."""
        mine = self.ext.create_classroom_session(
            self.course["id"], "Mine", "2027-01-10T15:00:00", INSTRUCTOR,
            participant_refs=["carol"])
        self.store.create_learner("erin", "Erin Learner", ADMIN)
        theirs = self.ext.create_classroom_session(
            self.course["id"], "Theirs", "2027-01-11T15:00:00", INSTRUCTOR,
            participant_refs=["erin"])
        self.assertEqual(
            self.ext.get_classroom_session(mine["id"], LEARNER)["id"],
            mine["id"])
        with self.assertRaises(PermissionDenied):
            self.ext.get_classroom_session(theirs["id"], LEARNER)
        listed = self.ext.list_classroom_sessions(LEARNER)
        self.assertEqual([s["id"] for s in listed], [mine["id"]])


class TestCollaborationReference(unittest.TestCase):
    """Idx 952 — real-time collaboration & recording (reference)."""

    def setUp(self):
        self.store, self.learner, self.course = make_store()
        self.ext = LmsExtensions(self.store)

    def test_collaboration_record_is_labeled_reference(self):
        """Idx 952: the record is session metadata only, carrying
        reference_stub and reference_transport True, the recorded-only
        state, and collaborated_here False — no collaboration happens
        here and no content is held."""
        record = self.ext.create_collaboration_record(
            INSTRUCTOR, course_id=self.course["id"],
            participant_refs=["carol"], shared_content_refs=["deck-1"])
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["reference_transport"], True)
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertIs(record["collaborated_here"], False)
        self.assertEqual(record["shared_content_refs"], ["deck-1"])

    def test_recording_record_is_metadata_only(self):
        """Idx 952: a recording record names the recording by opaque
        reference with an optional checksum and a caller-reported
        duration; content_held and recorded_here are False — the
        capture did not happen in this substrate."""
        collaboration = self.ext.create_collaboration_record(
            INSTRUCTOR, course_id=self.course["id"])
        recording = self.ext.record_recording_record(
            collaboration["id"], "rec-1", INSTRUCTOR, sha256=SHA256,
            duration_seconds=1800)
        self.assertIs(recording["reference_stub"], True)
        self.assertIs(recording["content_held"], False)
        self.assertIs(recording["recorded_here"], False)
        self.assertEqual(recording["duration_seconds"], 1800)
        with self.assertRaises(ValidationError):
            self.ext.record_recording_record(
                collaboration["id"], "rec-2", INSTRUCTOR, sha256="nope")
        with self.assertRaises(ValidationError):
            self.ext.record_recording_record(
                collaboration["id"], "rec-2", INSTRUCTOR,
                duration_seconds=True)


class TestAuthoringReference(unittest.TestCase):
    """Idx 953 — course material authoring workspace (reference stub)."""

    def setUp(self):
        self.store, self.learner, self.course = make_store()
        self.ext = LmsExtensions(self.store)

    def test_draft_revisions_append_only_and_stub_labeled(self):
        """Idx 953: drafts carry reference_stub True and the
        recorded-only state; revisions append, the view derives the
        current body and version count at read."""
        draft = self.ext.create_authoring_draft(
            "New Lesson", ADMIN, course_id=self.course["id"], body="v1")
        self.assertIs(draft["reference_stub"], True)
        self.assertEqual(draft["state"], "recorded_reference_only")
        self.assertEqual(draft["version_count"], 1)
        revised = self.ext.revise_authoring_draft(draft["id"], "v2", ADMIN)
        self.assertEqual(revised["body"], "v2")
        self.assertEqual(revised["version_count"], 2)

    def test_draft_changes_no_core_record(self):
        """Idx 953: a draft bound to a core lesson plan leaves the
        core plan, course, and content records byte-identical."""
        item = self.store.create_content_item(
            "Slides", "mp4", ADMIN, course_id=self.course["id"])
        plan = self.store.create_lesson_plan(
            "Plan", self.course["id"], ADMIN, item_refs=[item["id"]])
        before = (
            self.store.get_lesson_plan(plan["id"]),
            self.store.get_course(self.course["id"]),
            self.store.get_content_item(item["id"]),
        )
        draft = self.ext.create_authoring_draft(
            "Rework", ADMIN, course_id=self.course["id"],
            content_id=item["id"], lesson_plan_id=plan["id"], body="x")
        self.ext.revise_authoring_draft(draft["id"], "y", ADMIN)
        after = (
            self.store.get_lesson_plan(plan["id"]),
            self.store.get_course(self.course["id"]),
            self.store.get_content_item(item["id"]),
        )
        self.assertEqual(before, after)

    def test_authoring_writes_are_admin_only_in_this_matrix(self):
        """Idx 953: catalog_write is admin-only in the shipped
        permission matrix — an instructor draft is denied, and the
        denial consumes no id."""
        with self.assertRaises(PermissionDenied):
            self.ext.create_authoring_draft("Nope", INSTRUCTOR)
        draft = self.ext.create_authoring_draft("Ok", ADMIN)
        self.assertEqual(draft["id"], "dft-1")


class TestMediaRepository(unittest.TestCase):
    """Idx 954 — media & shared-materials repository (built)."""

    def setUp(self):
        self.store, self.learner, self.course = make_store()
        self.ext = LmsExtensions(self.store)

    def test_media_item_is_metadata_registry(self):
        """Idx 954: an item is metadata — opaque reference, kind,
        optional checksum and reported size — with content_held
        False; no content bytes exist anywhere on the record."""
        item = self.ext.create_media_item(
            "Lecture Capture", "media-1", "video", ADMIN,
            course_id=self.course["id"], sha256=SHA256, size_bytes=1024)
        self.assertIs(item["content_held"], False)
        self.assertEqual(item["sha256"], SHA256)
        self.assertEqual(item["share_count"], 0)
        with self.assertRaises(TypeError):
            self.ext.create_media_item(
                "Bad", "media-2", "video", ADMIN, content=b"bytes")
        with self.assertRaises(ValidationError):
            self.ext.create_media_item(
                "Bad", "media-2", "hologram", ADMIN)

    def test_share_records_and_derived_view(self):
        """Idx 954: shares are records with exactly one resolving
        target; the item view derives its share count and shared-with
        lists at read, and distributed_here stays False."""
        self.store.create_learner("erin", "Erin Learner", ADMIN)
        item = self.ext.create_media_item("Doc", "media-9", "document", ADMIN)
        share = self.ext.record_media_share(item["id"], ADMIN,
                                            learner_ref="carol")
        self.assertIs(share["distributed_here"], False)
        self.assertEqual(share["state"], "recorded")
        self.ext.record_media_share(item["id"], ADMIN, learner_ref="erin")
        self.ext.record_media_share(item["id"], ADMIN,
                                    course_id=self.course["id"])
        view = self.ext.get_media_item(item["id"], ADMIN)
        self.assertEqual(view["share_count"], 3)
        self.assertEqual(view["shared_learner_refs"], ["carol", "erin"])
        self.assertEqual(view["shared_course_ids"], [self.course["id"]])
        with self.assertRaises(ValidationError):
            self.ext.record_media_share(item["id"], ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_media_share(item["id"], ADMIN,
                                        learner_ref="carol",
                                        course_id=self.course["id"])
        with self.assertRaises(NotFoundError):
            self.ext.record_media_share(item["id"], ADMIN,
                                        learner_ref="ghost")

    def test_learner_sees_only_own_shares(self):
        """Idx 954: learner scope — a learner's share list and the
        item view's shared-learner list are filtered to their own
        reference."""
        self.store.create_learner("erin", "Erin Learner", ADMIN)
        item = self.ext.create_media_item("Doc", "media-9", "document", ADMIN)
        self.ext.record_media_share(item["id"], ADMIN, learner_ref="carol")
        self.ext.record_media_share(item["id"], ADMIN, learner_ref="erin")
        own = self.ext.list_media_shares(LEARNER, media_id=item["id"])
        self.assertEqual([s["learner_ref"] for s in own], ["carol"])
        view = self.ext.get_media_item(item["id"], LEARNER)
        self.assertEqual(view["shared_learner_refs"], ["carol"])
        self.assertEqual(view["share_count"], 2)


class TestCoursework(unittest.TestCase):
    """Idx 955 — assignment, evaluation & grading (built, records)."""

    def setUp(self):
        self.store, self.learner, self.course = make_store()
        self.ext = LmsExtensions(self.store)
        self.assignment = self.ext.create_coursework_assignment(
            self.course["id"], "Essay 1", INSTRUCTOR, due_date="2027-02-01")

    def test_assignment_record_has_no_status_or_outcome(self):
        """Idx 955: the assignment record is a definition bound to a
        core course — no status key, no outcome field is stored."""
        self.assertEqual(self.assignment["course_id"], self.course["id"])
        self.assertNotIn("status", self.assignment)
        view = self.ext.get_coursework_assignment(self.assignment["id"],
                                                  INSTRUCTOR)
        self.assertEqual(view["submission_count"], 0)
        self.assertEqual(view["evaluation_count"], 0)

    def test_submission_names_work_by_reference_only(self):
        """Idx 955: a submission names the work by opaque reference
        with an optional checksum; content_held is False and an
        unknown learner or assignment is rejected."""
        submission = self.ext.record_submission(
            self.assignment["id"], "carol", "work-1", INSTRUCTOR,
            sha256=SHA256)
        self.assertIs(submission["content_held"], False)
        with self.assertRaises(NotFoundError):
            self.ext.record_submission(self.assignment["id"], "ghost",
                                       "work-2", INSTRUCTOR)
        with self.assertRaises(NotFoundError):
            self.ext.record_submission("asn-99", "carol", "work-2",
                                       INSTRUCTOR)

    def test_evaluation_outcome_is_verbatim_text_never_computed(self):
        """Idx 955: the evaluation outcome is caller-supplied text
        stored exactly as given — a score-looking string stays a
        string — with computed_here False on the record."""
        submission = self.ext.record_submission(
            self.assignment["id"], "carol", "work-1", INSTRUCTOR)
        evaluation = self.ext.record_evaluation(
            submission["id"], "score: 88/100 — pass", ADMIN)
        self.assertEqual(evaluation["outcome_text"], "score: 88/100 — pass")
        self.assertIs(evaluation["computed_here"], False)
        self.assertEqual(evaluation["outcome_basis"], "caller_reported")
        view = self.ext.get_coursework_assignment(self.assignment["id"],
                                                  ADMIN)
        self.assertEqual(view["submission_count"], 1)
        self.assertEqual(view["evaluation_count"], 1)

    def test_evaluation_separation_of_duties_and_uniqueness(self):
        """Idx 955: whoever recorded a submission may not record its
        evaluation (the core SF-182 rule), and a submission carries
        at most one evaluation."""
        submission = self.ext.record_submission(
            self.assignment["id"], "carol", "work-1", INSTRUCTOR)
        with self.assertRaises(PermissionDenied):
            self.ext.record_evaluation(submission["id"], "ok", INSTRUCTOR)
        self.ext.record_evaluation(submission["id"], "ok", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_evaluation(submission["id"], "again", ADMIN)

    def test_coursework_summary_and_learner_scope(self):
        """Idx 955: summary counts are deterministic record counts;
        a learner reads only their own submissions and evaluations."""
        self.store.create_learner("erin", "Erin Learner", ADMIN)
        mine = self.ext.record_submission(
            self.assignment["id"], "carol", "work-1", INSTRUCTOR)
        theirs = self.ext.record_submission(
            self.assignment["id"], "erin", "work-2", INSTRUCTOR)
        self.ext.record_evaluation(mine["id"], "done", ADMIN)
        summary = self.ext.coursework_summary(ADMIN)
        self.assertEqual(summary["coursework_assignments"], 1)
        self.assertEqual(summary["submissions"], 2)
        self.assertEqual(summary["evaluations"], 1)
        own = self.ext.list_submissions(LEARNER)
        self.assertEqual([s["id"] for s in own], [mine["id"]])
        with self.assertRaises(PermissionDenied):
            self.ext.get_submission(theirs["id"], LEARNER)
        own_evals = self.ext.list_evaluations(LEARNER)
        self.assertEqual(len(own_evals), 1)


class TestUserAdministration(unittest.TestCase):
    """Idx 956 — user administration service (built, action records)."""

    def setUp(self):
        self.store, self.learner, self.course = make_store()
        self.ext = LmsExtensions(self.store)

    def test_action_record_shape(self):
        """Idx 956: an admin action is a record over a core learner
        reference carrying identity_provider False — this surface is
        not an IdP and holds no credential."""
        action = self.ext.record_user_admin_action("carol", "provisioned",
                                                   ADMIN)
        self.assertEqual(action["id"], "uad-1")
        self.assertIs(action["identity_provider"], False)
        with self.assertRaises(TypeError):
            self.ext.record_user_admin_action("carol", "provisioned", ADMIN,
                                              password="hunter2")
        with self.assertRaises(ValidationError):
            self.ext.record_user_admin_action("carol", "annihilated", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.record_user_admin_action("ghost", "provisioned", ADMIN)

    def test_current_state_derived_from_latest_action(self):
        """Idx 956: the current administrative state is the LATEST
        recorded action's label, derived at read — the stored
        records are never rewritten and no state is stored."""
        self.assertEqual(
            self.ext.user_admin_view("carol", ADMIN)["current_admin_state"],
            NO_RECORDED_ACTION)
        self.ext.record_user_admin_action("carol", "provisioned", ADMIN)
        self.ext.record_user_admin_action("carol", "suspended", ADMIN)
        view = self.ext.user_admin_view("carol", ADMIN)
        self.assertEqual(view["current_admin_state"], "suspended")
        self.assertEqual(view["action_count"], 2)
        self.assertEqual(view["method"], "derived_from_recorded_actions")
        self.ext.record_user_admin_action("carol", "reinstated", ADMIN)
        self.assertEqual(
            self.ext.user_admin_view("carol", ADMIN)["current_admin_state"],
            "reinstated")

    def test_admin_actions_never_modify_core_learner(self):
        """Idx 956: recording a deprovisioning action changes no core
        learner record — administration here is records about the
        registry, enforced by the registry's own owners elsewhere."""
        before = self.store.get_learner(self.learner["id"])
        self.ext.record_user_admin_action("carol", "provisioned", ADMIN)
        self.ext.record_user_admin_action("carol", "deprovisioned", ADMIN)
        self.assertEqual(self.store.get_learner(self.learner["id"]), before)

    def test_admin_writes_admin_only_and_learner_scope(self):
        """Idx 956: learner_write is admin-only in the shipped
        matrix (instructor denied); a learner reads only their own
        administration view and action list."""
        with self.assertRaises(PermissionDenied):
            self.ext.record_user_admin_action("carol", "provisioned",
                                              INSTRUCTOR)
        with self.assertRaises(PermissionDenied):
            self.ext.record_user_admin_action("carol", "provisioned", LEARNER)
        self.ext.record_user_admin_action("carol", "provisioned", ADMIN)
        self.store.create_learner("erin", "Erin Learner", ADMIN)
        self.ext.record_user_admin_action("erin", "provisioned", ADMIN)
        own = self.ext.list_user_admin_actions(LEARNER)
        self.assertEqual([a["learner_ref"] for a in own], ["carol"])
        with self.assertRaises(PermissionDenied):
            self.ext.user_admin_view("erin", LEARNER)


class EarliestAdminStateExtensions(LmsExtensions):
    """Mutant: the current state reads the EARLIEST action instead."""

    @staticmethod
    def _current_admin_state(actions):
        if not actions:
            return NO_RECORDED_ACTION
        return actions[0]["action_label"]


class TestAdminStateNegativeControl(unittest.TestCase):
    """Fresh negative control for idx 956's derivation.

    The traced claim: a learner's current administrative state is
    derived from the LATEST recorded administration action. For the
    canonical case (provisioned, then suspended) the test asserts
    the canonical expectation from the real implementation, that
    the earliest-reading mutant would NOT produce it, and — via a
    literal assertRaises — that treating the mutant's outcome as
    the expected outcome fails.
    """

    def test_latest_action_wins_canonical_but_mutant_earliest(self):
        store, learner, course = make_store()
        canonical = LmsExtensions(store)
        canonical.record_user_admin_action("carol", "provisioned", ADMIN)
        canonical.record_user_admin_action("carol", "suspended", ADMIN)
        expected = "suspended"
        canonical_state = canonical.user_admin_view(
            "carol", ADMIN)["current_admin_state"]
        self.assertEqual(canonical_state, expected)
        mutant = EarliestAdminStateExtensions(store)
        mutant._user_admin_actions = canonical._user_admin_actions
        mutant_state = mutant.user_admin_view(
            "carol", ADMIN)["current_admin_state"]
        self.assertEqual(mutant_state, "provisioned")
        self.assertNotEqual(mutant_state, expected)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_state, expected)

    def test_no_actions_reads_the_empty_state_in_both(self):
        """Companion: with no recorded actions both implementations
        read the empty state — the mutant differs only in ORDER."""
        store, learner, course = make_store()
        canonical = LmsExtensions(store)
        mutant = EarliestAdminStateExtensions(store)
        self.assertEqual(
            canonical.user_admin_view("carol", ADMIN)["current_admin_state"],
            NO_RECORDED_ACTION)
        self.assertEqual(
            mutant.user_admin_view("carol", ADMIN)["current_admin_state"],
            NO_RECORDED_ACTION)

    def test_learner_cannot_record_admin_actions(self):
        """Companion RBAC gate: a learner recording an administration
        action is denied and nothing is stored."""
        store, learner, course = make_store()
        ext = LmsExtensions(store)
        with self.assertRaises(PermissionDenied):
            ext.record_user_admin_action("carol", "provisioned", LEARNER)
        self.assertEqual(ext.list_user_admin_actions(ADMIN), [])


class TestCrossCutting(unittest.TestCase):
    """Batch-wide pins over the whole extension surface."""

    def setUp(self):
        self.store, self.learner, self.course = make_store()

    def test_no_score_or_grade_key_anywhere(self):
        """Doctrines: recursively, no key on any extension record or
        view is a score key (the core's rule: exactly 'score',
        'score_*', '*_score') or contains 'grade' — the founding
        no-score invariant, extended to grade-shaped keys for
        idx 955, whose outcomes are verbatim text only."""
        _, battery = _battery(self.store, self.course)
        offenders = []

        def walk(obj, path):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    lowered = str(key).lower()
                    if (lowered == "score" or lowered.startswith("score_")
                            or lowered.endswith("_score")
                            or "grade" in lowered):
                        offenders.append((path, key))
                    walk(value, path + "/" + str(key))
            elif isinstance(obj, (list, tuple)):
                for index, value in enumerate(obj):
                    walk(value, "%s[%d]" % (path, index))

        for record in battery:
            walk(record, record.get("id", "?"))
        self.assertEqual(offenders, [])

    def test_no_tier_key_anywhere(self):
        """Tier discipline: this set is untiered — recursively, no
        key on any extension record or view names a tier, a CMMC
        value, a baseline, or a FedRAMP impact level. The surface
        asserts no baseline and draws no equivalence."""
        _, battery = _battery(self.store, self.course)
        offenders = []

        def walk(obj, path):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    lowered = str(key).lower()
                    if any(token in lowered for token in
                           ("tier", "cmmc", "baseline", "fedramp")):
                        offenders.append((path, key))
                    walk(value, path + "/" + str(key))
            elif isinstance(obj, (list, tuple)):
                for index, value in enumerate(obj):
                    walk(value, "%s[%d]" % (path, index))

        for record in battery:
            walk(record, record.get("id", "?"))
        self.assertEqual(offenders, [])

    def test_stub_labels_present_where_required(self):
        """Stub pins: every reference-form record carries its label —
        reference_stub True on collaboration, recording, and draft
        records; reference_transport True on the transport-shaped
        pair."""
        ext, _ = _battery(self.store, self.course)
        collaboration = ext.list_collaboration_records(ADMIN)[0]
        recording = ext.list_recording_records(ADMIN)[0]
        draft = ext.list_authoring_drafts(ADMIN)[0]
        for record in (collaboration, recording, draft):
            self.assertIs(record["reference_stub"], True)
        for record in (collaboration, recording):
            self.assertIs(record["reference_transport"], True)
            self.assertEqual(record["state"], "recorded_reference_only")

    def test_every_mutation_audited_with_ext_prefix(self):
        """Audit: every successful extension mutation lands on the
        core audit log with an ext_-prefixed action."""
        ext, _ = _battery(self.store, self.course)
        actions = [e["action"] for e in self.store.audit.entries()
                   if e["action"].startswith("ext_")]
        self.assertEqual(set(actions), {
            "ext_classroom_session_create", "ext_classroom_outcome_record",
            "ext_collaboration_record", "ext_recording_record",
            "ext_authoring_draft_create", "ext_media_item_create",
            "ext_media_share_record", "ext_coursework_assignment_create",
            "ext_submission_record", "ext_evaluation_record",
            "ext_user_admin_action_record",
        })

    def test_denied_writes_consume_no_id(self):
        """RBAC: a denied write allocates nothing — the next allowed
        write on each surface still takes the first id."""
        ext = LmsExtensions(self.store)
        with self.assertRaises(PermissionDenied):
            ext.create_classroom_session(
                self.course["id"], "X", "2027-01-10T15:00:00", LEARNER)
        with self.assertRaises(PermissionDenied):
            ext.record_user_admin_action("carol", "provisioned", AUDITOR)
        session = ext.create_classroom_session(
            self.course["id"], "X", "2027-01-10T15:00:00", INSTRUCTOR)
        self.assertEqual(session["id"], "vcs-1")
        action = ext.record_user_admin_action("carol", "provisioned", ADMIN)
        self.assertEqual(action["id"], "uad-1")

    def test_no_var_keyword_parameters(self):
        """Signature pin: no public extension method accepts
        **kwargs, so no content-, credential-, or score-shaped
        argument can be smuggled past the signatures."""
        for name, member in inspect.getmembers(LmsExtensions,
                                               inspect.isfunction):
            if name.startswith("_"):
                continue
            for parameter in inspect.signature(member).parameters.values():
                self.assertNotEqual(
                    parameter.kind, inspect.Parameter.VAR_KEYWORD,
                    "%s accepts **kwargs" % (name,))


if __name__ == "__main__":
    unittest.main()
