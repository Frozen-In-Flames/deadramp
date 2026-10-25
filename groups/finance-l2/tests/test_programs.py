"""Programs and participant-registry tests.

Traces to: UNION-SPEC Core function 1 (Programs & members — named
programs with an owner, a member list, and provenance) and Core
function 2 (Participant & traveler registry, opaque references — the
record shape is pinned so no field can hold a real identifier);
Implementation contract for ``finance/store.py`` program and
participant methods; control families AC-2/AC-3 (membership is the
boundary) and SI-10 (a failed operation consumes no id and changes
nothing).
"""

import unittest
from datetime import datetime

from finance_helpers import (
    ADMIN,
    MEMBER,
    OUTSIDER,
    VIEWER,
    fresh_store,
    make_employee,
    make_store,
    make_traveler,
)
from finance.errors import NotFoundError, PermissionDenied, ValidationError

PROGRAM_KEYS = {"id", "name", "owner", "members", "created_by", "created_utc"}
# The privacy pin: exactly these keys, nothing that could hold a real
# name, account number, card number, or government identifier.
PARTICIPANT_KEYS = {
    "id", "program_id", "ref", "kind", "status", "created_by", "created_utc",
}


class TestCreateProgram(unittest.TestCase):
    """Core 1: Programs & members — creation shape/provenance/ids."""

    def setUp(self):
        self.store = fresh_store()

    def test_create_returns_the_contract_dict(self):
        """Core 1: Programs. Contract: create_program returns {id,
        name, owner, members, created_by, created_utc}."""
        program = self.store.create_program("acme-program", MEMBER)
        self.assertEqual(set(program.keys()), PROGRAM_KEYS)
        self.assertEqual(program["name"], "acme-program")
        self.assertEqual(program["created_by"], "bob")

    def test_creator_is_owner_and_first_member(self):
        """Core 1: Programs. Contract: 'the creator is owner and first
        member'."""
        program = self.store.create_program("acme-program", MEMBER)
        self.assertEqual(program["owner"], "bob")
        self.assertEqual(program["members"], ["bob"])

    def test_first_program_id_is_prog_1_and_ids_are_sequential(self):
        """Core 1: Programs. Contract: ids are sequential per object
        type with the prog- prefix."""
        first = self.store.create_program("a", MEMBER)
        second = self.store.create_program("b", ADMIN)
        third = self.store.create_program("c", MEMBER)
        self.assertEqual(
            [first["id"], second["id"], third["id"]],
            ["prog-1", "prog-2", "prog-3"],
        )

    def test_created_utc_is_a_parseable_timestamp(self):
        """Core 1: Programs. Contract: all timestamps are UTC
        ISO-8601."""
        program = self.store.create_program("acme-program", MEMBER)
        parsed = datetime.fromisoformat(
            str(program["created_utc"]).replace("Z", "+00:00")
        )
        self.assertIsNotNone(parsed)

    def test_admin_and_member_may_create_but_viewer_may_not(self):
        """Core 1: Programs + Core 10 Access control. create_program
        is in the admin and member permission sets and not in
        viewer's."""
        self.store.create_program("by-admin", ADMIN)
        self.store.create_program("by-member", MEMBER)
        with self.assertRaises(PermissionDenied):
            self.store.create_program("by-viewer", VIEWER)

    def test_failed_create_consumes_no_id(self):
        """Core 1: Programs (SI-10). A denied creation changes
        nothing: the next successful program is still prog-1."""
        with self.assertRaises(PermissionDenied):
            self.store.create_program("denied", VIEWER)
        program = self.store.create_program("real", MEMBER)
        self.assertEqual(program["id"], "prog-1")


class TestGetAndListPrograms(unittest.TestCase):
    """Core 1: Programs — visibility is membership (or platform admin)."""

    def setUp(self):
        self.store, self.audit, self.program_id = make_store()

    def test_get_program_by_owner_and_member(self):
        """Core 1: Programs. Members can get their program dict."""
        for actor in (MEMBER, VIEWER):
            with self.subTest(actor=actor.name):
                program = self.store.get_program(self.program_id, actor)
                self.assertEqual(program["id"], self.program_id)
                self.assertEqual(set(program.keys()), PROGRAM_KEYS)

    def test_get_program_by_platform_admin_non_member(self):
        """Core 1: Programs + Core 10 Access control. Contract: the
        platform admin role reaches programs without membership."""
        program = self.store.get_program(self.program_id, ADMIN)
        self.assertEqual(program["id"], self.program_id)

    def test_get_program_by_non_member_is_denied(self):
        """Core 1: Programs (AC-3). Contract: get_program for a
        non-member raises PermissionDenied."""
        with self.assertRaises(PermissionDenied):
            self.store.get_program(self.program_id, OUTSIDER)

    def test_get_unknown_program_is_not_found(self):
        """Core 1: Programs. Unknown id -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_program("prog-999999", ADMIN)

    def test_list_programs_shows_only_visible_programs(self):
        """Core 1: Programs. Contract: list_programs returns the
        program dicts the actor may see (member of, or platform
        admin)."""
        other = self.store.create_program("admin-only-program", ADMIN)
        member_ids = [p["id"] for p in self.store.list_programs(MEMBER)]
        self.assertEqual(member_ids, [self.program_id])
        viewer_ids = [p["id"] for p in self.store.list_programs(VIEWER)]
        self.assertEqual(viewer_ids, [self.program_id])
        admin_ids = [p["id"] for p in self.store.list_programs(ADMIN)]
        self.assertEqual(admin_ids, [self.program_id, other["id"]])
        self.assertEqual(self.store.list_programs(OUTSIDER), [])


class TestAddMember(unittest.TestCase):
    """Core 1: Programs — only the owner or a platform admin may add."""

    def setUp(self):
        self.store, self.audit, self.program_id = make_store()

    def test_owner_can_add_member_and_gets_updated_program(self):
        """Core 1: Programs. Contract: add_member returns the updated
        program dict; a member added by the owner can then read the
        program."""
        updated = self.store.add_member(self.program_id, "dave", MEMBER)
        self.assertEqual(set(updated.keys()), PROGRAM_KEYS)
        self.assertIn("dave", updated["members"])
        program = self.store.get_program(self.program_id, OUTSIDER)
        self.assertEqual(program["id"], self.program_id)

    def test_platform_admin_can_add_member(self):
        """Core 1: Programs. Contract: a platform admin may add
        members to a program they do not own or belong to."""
        updated = self.store.add_member(self.program_id, "dave", ADMIN)
        self.assertIn("dave", updated["members"])

    def test_plain_member_cannot_add_member(self):
        """Core 1: Programs (AC-3). A member who is neither owner nor
        platform admin cannot add members."""
        with self.assertRaises(PermissionDenied):
            self.store.add_member(self.program_id, "dave", VIEWER)

    def test_non_member_cannot_add_member(self):
        """Core 1: Programs (AC-3). A non-member cannot add anyone."""
        with self.assertRaises(PermissionDenied):
            self.store.add_member(self.program_id, "erin", OUTSIDER)

    def test_adding_an_existing_member_is_a_validation_error(self):
        """Core 1: Programs. Contract: 'adding an existing member
        raises ValidationError'."""
        with self.assertRaises(ValidationError):
            self.store.add_member(self.program_id, VIEWER.name, MEMBER)
        with self.assertRaises(ValidationError):
            self.store.add_member(self.program_id, MEMBER.name, MEMBER)

    def test_duplicate_add_changes_nothing(self):
        """Core 1: Programs (SI-10). A failed duplicate add leaves the
        member list exactly as it was."""
        before = list(
            self.store.get_program(self.program_id, MEMBER)["members"]
        )
        with self.assertRaises(ValidationError):
            self.store.add_member(self.program_id, VIEWER.name, MEMBER)
        after = self.store.get_program(self.program_id, MEMBER)["members"]
        self.assertEqual(after, before)


class TestParticipants(unittest.TestCase):
    """Core 2: Participant registry — the privacy-pinned record shape."""

    def setUp(self):
        self.store, self.audit, self.program_id = make_store()

    def test_create_participant_returns_exactly_the_pinned_keys(self):
        """Core 2: Participant registry (privacy pin). Contract: the
        returned dict has exactly {id, program_id, ref, kind, status,
        created_by, created_utc} — no field can hold a real identifier."""
        participant = make_employee(self.store, self.program_id)
        self.assertEqual(set(participant.keys()), PARTICIPANT_KEYS)
        self.assertEqual(participant["id"], "part-1")
        self.assertEqual(participant["program_id"], self.program_id)
        self.assertEqual(participant["ref"], "emp-1")
        self.assertEqual(participant["kind"], "employee")
        self.assertEqual(participant["status"], "active")
        self.assertEqual(participant["created_by"], "bob")

    def test_participant_ids_are_sequential_with_part_prefix(self):
        """Core 2: Participant registry. Contract: ids are sequential
        per object type with the part- prefix."""
        first = make_employee(self.store, self.program_id, ref="emp-1")
        second = make_traveler(self.store, self.program_id, ref="trav-1")
        self.assertEqual([first["id"], second["id"]], ["part-1", "part-2"])

    def test_duplicate_ref_in_same_program_is_a_validation_error(self):
        """Core 2: Participant registry. Contract: ref must be unique
        within the program (duplicate -> ValidationError)."""
        make_employee(self.store, self.program_id, ref="emp-1")
        with self.assertRaises(ValidationError):
            make_traveler(self.store, self.program_id, ref="emp-1")
        participants = self.store.list_participants(self.program_id, MEMBER)
        self.assertEqual(len(participants), 1)

    def test_same_ref_in_another_program_is_ok(self):
        """Core 2: Participant registry. Ref uniqueness is per
        program: the same ref in another program is accepted."""
        make_employee(self.store, self.program_id, ref="emp-1")
        other = self.store.create_program("other-program", MEMBER)
        participant = make_employee(self.store, other["id"], ref="emp-1")
        self.assertEqual(participant["ref"], "emp-1")
        self.assertEqual(participant["program_id"], other["id"])

    def test_bad_kind_is_a_validation_error(self):
        """Core 2: Participant registry. Contract: kind must be one of
        employee, traveler."""
        for bad in ("manager", "Employee", "", "guest"):
            with self.subTest(kind=bad):
                with self.assertRaises(ValidationError):
                    self.store.create_participant(
                        self.program_id, "ref-x", bad, MEMBER
                    )
        self.assertEqual(
            self.store.list_participants(self.program_id, MEMBER), []
        )

    def test_empty_ref_is_a_validation_error(self):
        """Core 2: Participant registry (SI-10). Contract: ref must be
        a non-empty string."""
        for bad in ("", None, 42):
            with self.subTest(ref=bad):
                with self.assertRaises(ValidationError):
                    self.store.create_participant(
                        self.program_id, bad, "employee", MEMBER
                    )

    def test_failed_participant_create_consumes_no_id(self):
        """Core 2: Participant registry (SI-10). A failed creation
        changes nothing: the next successful participant keeps the
        sequence."""
        with self.assertRaises(ValidationError):
            self.store.create_participant(
                self.program_id, "ref-x", "bogus-kind", MEMBER
            )
        participant = make_employee(self.store, self.program_id)
        self.assertEqual(participant["id"], "part-1")
        with self.assertRaises(ValidationError):
            make_employee(self.store, self.program_id, ref="emp-1")
        second = make_traveler(self.store, self.program_id)
        self.assertEqual(second["id"], "part-2")

    def test_non_member_create_is_denied(self):
        """Core 2: Participant registry (AC-3). Contract: a non-member
        create raises PermissionDenied."""
        with self.assertRaises(PermissionDenied):
            self.store.create_participant(
                self.program_id, "emp-x", "employee", OUTSIDER
            )

    def test_viewer_create_is_denied_by_role(self):
        """Core 2: Participant registry + Core 10 Access control.
        create_participant is action ``enter``; a viewer program
        member lacks it, so the store denies her."""
        with self.assertRaises(PermissionDenied):
            self.store.create_participant(
                self.program_id, "emp-x", "employee", VIEWER
            )

    def test_get_participant_by_member_and_admin(self):
        """Core 2: Participant registry. Members and the platform
        admin can get a participant dict, with exactly the pinned
        keys."""
        participant = make_employee(self.store, self.program_id)
        for actor in (MEMBER, VIEWER, ADMIN):
            with self.subTest(actor=actor.name):
                got = self.store.get_participant(
                    self.program_id, participant["id"], actor
                )
                self.assertEqual(got["id"], participant["id"])
                self.assertEqual(set(got.keys()), PARTICIPANT_KEYS)

    def test_cross_program_get_is_not_found(self):
        """Core 2: Participant registry. Contract: an id that belongs
        to another program raises NotFoundError."""
        participant = make_employee(self.store, self.program_id)
        other = self.store.create_program("other-program", MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.get_participant(other["id"], participant["id"], MEMBER)

    def test_get_unknown_participant_is_not_found(self):
        """Core 2: Participant registry. Unknown participant id ->
        NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_participant(self.program_id, "part-999999", MEMBER)

    def test_non_member_cannot_list_or_get_participants(self):
        """Core 2: Participant registry (AC-3). Program membership
        gates the registry: a non-member can neither list nor get."""
        participant = make_employee(self.store, self.program_id)
        with self.assertRaises(PermissionDenied):
            self.store.list_participants(self.program_id, OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.store.get_participant(
                self.program_id, participant["id"], OUTSIDER
            )

    def test_list_participants_is_in_creation_order(self):
        """Core 2: Participant registry. Contract: list_participants
        returns participants in creation order."""
        make_traveler(self.store, self.program_id, ref="trav-1")
        make_employee(self.store, self.program_id, ref="emp-1")
        make_traveler(self.store, self.program_id, ref="trav-2")
        refs = [
            p["ref"]
            for p in self.store.list_participants(self.program_id, MEMBER)
        ]
        self.assertEqual(refs, ["trav-1", "emp-1", "trav-2"])

    def test_list_participants_kind_filter(self):
        """Core 2: Participant registry. Contract: list_participants
        honours kind= — employees only, travelers only."""
        make_employee(self.store, self.program_id, ref="emp-1")
        make_traveler(self.store, self.program_id, ref="trav-1")
        make_employee(self.store, self.program_id, ref="emp-2")
        employees = self.store.list_participants(
            self.program_id, MEMBER, kind="employee"
        )
        self.assertEqual([p["ref"] for p in employees], ["emp-1", "emp-2"])
        travelers = self.store.list_participants(
            self.program_id, MEMBER, kind="traveler"
        )
        self.assertEqual([p["ref"] for p in travelers], ["trav-1"])

    def test_list_participants_unknown_kind_filter_is_validation_error(self):
        """Core 2: Participant registry. Contract: 'an unknown kind
        filter -> ValidationError'."""
        with self.assertRaises(ValidationError):
            self.store.list_participants(
                self.program_id, MEMBER, kind="manager"
            )

    def test_set_participant_status_roundtrip(self):
        """Core 2: Participant registry. Contract:
        set_participant_status with active/inactive returns the
        updated participant dict (action ``enter``)."""
        participant = make_employee(self.store, self.program_id)
        updated = self.store.set_participant_status(
            self.program_id, participant["id"], "inactive", MEMBER
        )
        self.assertEqual(updated["status"], "inactive")
        self.assertEqual(set(updated.keys()), PARTICIPANT_KEYS)
        back = self.store.set_participant_status(
            self.program_id, participant["id"], "active", MEMBER
        )
        self.assertEqual(back["status"], "active")

    def test_set_participant_status_invalid_status_is_validation_error(self):
        """Core 2: Participant registry. Contract: status must be
        active or inactive (else ValidationError), and a failed set
        changes nothing."""
        participant = make_employee(self.store, self.program_id)
        for bad in ("suspended", "Active", "", None):
            with self.subTest(status=bad):
                with self.assertRaises(ValidationError):
                    self.store.set_participant_status(
                        self.program_id, participant["id"], bad, MEMBER
                    )
        got = self.store.get_participant(
            self.program_id, participant["id"], MEMBER
        )
        self.assertEqual(got["status"], "active")

    def test_set_status_on_unknown_participant_is_not_found(self):
        """Core 2: Participant registry. set_participant_status on a
        missing participant -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.set_participant_status(
                self.program_id, "part-999999", "inactive", MEMBER
            )


if __name__ == "__main__":
    unittest.main()
