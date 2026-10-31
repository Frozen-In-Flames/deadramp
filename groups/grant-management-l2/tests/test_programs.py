"""Core: Grant program registry. Traces to UNION-SPEC core function 1
(grant_process_administration / opportunity_exploration substrate)
and SI-10 input validation."""

import unittest

import grants_helpers as H
from grants.errors import NotFoundError, PermissionDenied, ValidationError


class TestProgramCreation(unittest.TestCase):
    def setUp(self):
        self.store = H.fresh_store()

    def test_create_shape_and_defaults(self):
        program = H.make_program(self.store)
        self.assertTrue(program["id"].startswith("gp-"))
        self.assertEqual(program["owner"], "bob")
        self.assertEqual(program["members"], ["bob"])
        self.assertEqual(program["budget_cents"], H.BUDGET_CENTS)
        self.assertEqual(program["awarded_cents"], 0)
        self.assertEqual(program["remaining_cents"], H.BUDGET_CENTS)

    def test_duplicate_name_rejected(self):
        H.make_program(self.store)
        with self.assertRaises(ValidationError):
            H.make_program(self.store)

    def test_bad_inputs_rejected_whole(self):
        for overrides in (
            {"budget_cents": 100.0},          # float money
            {"budget_cents": True},           # bool money
            {"budget_cents": -1},             # negative budget
            {"opens_at": "not-a-date"},
            {"closes_at": "2025-01-01"},      # closes before opens
            {"title": "  "},
            {"sponsor_ref": ""},
        ):
            with self.assertRaises(ValidationError, msg=repr(overrides)):
                H.make_program(self.store, **overrides)
        # Nothing was stored and no id was consumed by the failures.
        program = H.make_program(self.store)
        self.assertEqual(program["id"], "gp-1")

    def test_viewer_cannot_create_program(self):
        with self.assertRaises(PermissionDenied):
            H.make_program(self.store, actor=H.VIEWER)


class TestDerivedProgramStatus(unittest.TestCase):
    """Program open status is derived at read, never stored."""

    def setUp(self):
        self.store, self.program, self.org = H.make_store()

    def test_status_follows_the_read_clock(self):
        pid = self.program["id"]
        self.assertEqual(
            self.store.get_program(H.MEMBER, pid, now="2025-06-01")["status"],
            "upcoming")
        self.assertEqual(
            self.store.get_program(H.MEMBER, pid, now=H.NOW_OPEN)["status"],
            "open")
        self.assertEqual(
            self.store.get_program(H.MEMBER, pid, now="2027-06-01")["status"],
            "closed")

    def test_stored_record_carries_no_status(self):
        raw = self.store._programs[self.program["id"]]
        self.assertNotIn("status", raw)
        self.assertNotIn("awarded_cents", raw)
        self.assertNotIn("remaining_cents", raw)


class TestMembershipBoundary(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.org = H.make_store()

    def test_outsider_cannot_read_program(self):
        with self.assertRaises(PermissionDenied):
            self.store.get_program(H.OUTSIDER, self.program["id"])

    def test_admin_reaches_program_without_membership(self):
        view = self.store.get_program(H.ADMIN, self.program["id"])
        self.assertEqual(view["name"], H.PROGRAM_NAME)

    def test_unknown_program_is_not_found(self):
        with self.assertRaises(NotFoundError):
            self.store.get_program(H.ADMIN, "gp-99")

    def test_add_member_then_member_can_read(self):
        self.store.add_member(H.ADMIN, self.program["id"], H.OUTSIDER.name)
        view = self.store.get_program(H.OUTSIDER, self.program["id"])
        self.assertIn("dave", view["members"])

    def test_member_role_cannot_manage_members(self):
        with self.assertRaises(PermissionDenied):
            self.store.add_member(H.MEMBER, self.program["id"], "zoe")

    def test_list_programs_scoped_to_membership(self):
        self.assertEqual(len(self.store.list_programs(H.MEMBER)), 1)
        self.assertEqual(self.store.list_programs(H.OUTSIDER), [])
        self.assertEqual(len(self.store.list_programs(H.ADMIN)), 1)


if __name__ == "__main__":
    unittest.main()
