"""Core: Application records & lifecycle. Traces to UNION-SPEC core
function 3 (application_submission_management) and SI-10."""

import unittest

import grants_helpers as H
from grants.errors import NotFoundError, PermissionDenied, ValidationError


class TestApplicationCreation(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.org = H.make_store()

    def test_create_shape(self):
        app = H.make_application(self.store, self.program, self.org)
        self.assertTrue(app["id"].startswith("app-"))
        self.assertEqual(app["status"], "draft")
        self.assertEqual(app["submitted_by"], "bob")
        self.assertEqual(app["requested_cents"], 400_000)
        self.assertEqual(app["responses"], {})

    def test_money_must_be_positive_integer_cents(self):
        for bad in (100.0, True, "4000", 0, -5, None):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                H.make_application(self.store, self.program,
                                   self.org, requested_cents=bad)

    def test_unknown_org_and_program(self):
        with self.assertRaises(NotFoundError):
            self.store.create_application(H.MEMBER, self.program["id"],
                                          "org-99", 100, "x")
        with self.assertRaises(NotFoundError):
            self.store.create_application(H.MEMBER, "gp-99",
                                          self.org["id"], 100, "x")

    def test_responses_must_be_an_object(self):
        with self.assertRaises(ValidationError):
            H.make_application(self.store, self.program, self.org,
                               responses=["not", "an", "object"])

    def test_outsider_cannot_create(self):
        with self.assertRaises(PermissionDenied):
            H.make_application(self.store, self.program, self.org,
                               actor=H.OUTSIDER)

    def test_form_must_belong_to_program(self):
        form = self.store.create_form(
            H.MEMBER, self.program["id"], "Intake",
            [{"name": "lead", "kind": "text", "required": True}])
        app = H.make_application(self.store, self.program, self.org,
                                 form_id=form["id"])
        self.assertEqual(app["form_id"], form["id"])
        other = H.make_program(self.store, name="other-program")
        foreign = self.store.create_form(
            H.MEMBER, other["id"], "Foreign",
            [{"name": "x", "kind": "text", "required": False}])
        with self.assertRaises(NotFoundError):
            H.make_application(self.store, self.program, self.org,
                               form_id=foreign["id"])


class TestLifecycle(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.org = H.make_store()

    def test_happy_path(self):
        app = H.make_application(self.store, self.program, self.org)
        self.assertEqual(
            self.store.submit_application(H.MEMBER, app["id"])["status"],
            "submitted")
        self.assertEqual(
            self.store.start_review(H.STAFF, app["id"])["status"],
            "under_review")

    def test_invalid_transitions_change_nothing(self):
        app = H.make_application(self.store, self.program, self.org)
        with self.assertRaises(ValidationError):
            self.store.start_review(H.STAFF, app["id"])  # draft, not submitted
        self.assertEqual(
            self.store.get_application(H.MEMBER, app["id"])["status"], "draft")
        self.store.submit_application(H.MEMBER, app["id"])
        with self.assertRaises(ValidationError):
            self.store.submit_application(H.MEMBER, app["id"])  # already submitted
        self.assertEqual(
            self.store.get_application(H.MEMBER, app["id"])["status"], "submitted")

    def test_withdraw_from_open_states_only(self):
        app = H.make_application(self.store, self.program, self.org)
        self.assertEqual(
            self.store.withdraw_application(H.MEMBER, app["id"])["status"],
            "withdrawn")
        with self.assertRaises(ValidationError):
            self.store.withdraw_application(H.MEMBER, app["id"])

    def test_start_review_needs_decide_permission(self):
        app = H.make_application(self.store, self.program, self.org)
        self.store.submit_application(H.MEMBER, app["id"])
        self.store.add_member(H.ADMIN, self.program["id"], H.VIEWER.name)
        with self.assertRaises(PermissionDenied):
            self.store.start_review(H.VIEWER, app["id"])

    def test_list_filter_and_bad_status(self):
        H.make_application(self.store, self.program, self.org)
        second = H.make_application(self.store, self.program, self.org,
                                    summary="Library program")
        self.store.submit_application(H.MEMBER, second["id"])
        self.assertEqual(
            len(self.store.list_applications(H.MEMBER, self.program["id"])), 2)
        self.assertEqual(
            len(self.store.list_applications(H.MEMBER, self.program["id"],
                                             status="draft")), 1)
        with self.assertRaises(ValidationError):
            self.store.list_applications(H.MEMBER, self.program["id"],
                                         status="bogus")


if __name__ == "__main__":
    unittest.main()
