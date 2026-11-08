"""Final GAPS batch tests — Remainder Singleton 62, Human Resources L1.

Traces to: the 1 open entry of the section (workforce scheduling
& call-scheduling engine, idx 713) and its in-substrate records
form in ``hr/extensions.py``: shift definitions and rotation
definitions held as data, caller-recorded roster assignments, and
coverage derived at read through the ``_derive_pair_state`` seam.
Also pins the founding privacy discipline over the new surface
(forbidden-key walk + signature scan + TypeError pins) and the
fresh mutation-verified negative control for the coverage seam.
"""

import inspect
import unittest

from hr_helpers import ADMIN, AUDITOR, EMPLOYEE, SPECIALIST, make_store
from hr.errors import NotFoundError, PermissionDenied, ValidationError
from hr.extensions import (
    FORBIDDEN_KEYS,
    FORBIDDEN_PARAMS,
    SHIFT_KINDS,
    HrExtensions,
    _derive_pair_state,
)


def make_extensions():
    """Store (position pos-1, person carol) + extension surface."""
    store, position, person = make_store()
    store.create_person("staff-2", ADMIN, kind="employee")
    store.create_person("staff-3", ADMIN, kind="employee")
    return store, position, HrExtensions(store)


def make_schedule():
    """Extensions + one day shift + one call shift + one rotation."""
    store, position, ext = make_extensions()
    day = ext.create_shift_definition("day", "07:00", "19:00", SPECIALIST)
    call = ext.create_shift_definition("call", "19:00", "07:00", SPECIALIST)
    rotation = ext.create_rotation(
        position["id"], "Ward A rotation", ["carol", "staff-2"], SPECIALIST
    )
    return store, position, ext, day, call, rotation


def _walk_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _walk_keys(value)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            keys |= _walk_keys(item)
    return keys


class TestShiftDefinitions(unittest.TestCase):
    """Entry idx 713: shift definitions are definitions held as data."""

    def test_create_shift_definition_shape_and_flags(self):
        """A shift definition holds kind + clock labels as data and states generated_here False on its face."""
        _, _, ext = make_extensions()
        shift = ext.create_shift_definition("day", "07:00", "19:00", SPECIALIST,
                                            title="Day shift")
        self.assertEqual(shift["id"], "shf-1")
        self.assertEqual(shift["kind"], "day")
        self.assertEqual(shift["start_label"], "07:00")
        self.assertEqual(shift["end_label"], "19:00")
        self.assertTrue(shift["definition_only"])
        self.assertFalse(shift["generated_here"])
        self.assertFalse(shift["optimized_here"])

    def test_shift_kind_vocabulary(self):
        """Every kind in SHIFT_KINDS is accepted; a kind outside the vocabulary is rejected."""
        _, _, ext = make_extensions()
        for kind in SHIFT_KINDS:
            ext.create_shift_definition(kind, "08:00", "16:00", SPECIALIST)
        self.assertEqual(len(ext.list_shift_definitions(SPECIALIST)), 4)
        with self.assertRaises(ValidationError):
            ext.create_shift_definition("swing", "08:00", "16:00", SPECIALIST)

    def test_clock_labels_validated_and_no_id_consumed(self):
        """Malformed clock labels are rejected whole and consume no id."""
        _, _, ext = make_extensions()
        with self.assertRaises(ValidationError):
            ext.create_shift_definition("day", "7am", "19:00", SPECIALIST)
        with self.assertRaises(ValidationError):
            ext.create_shift_definition("day", "07:00", "24:00", SPECIALIST)
        shift = ext.create_shift_definition("day", "07:00", "19:00", SPECIALIST)
        self.assertEqual(shift["id"], "shf-1")

    def test_shift_definition_write_denied_for_employee_and_auditor(self):
        """RBAC: employee and auditor roles may not create shift definitions (performance_write)."""
        _, _, ext = make_extensions()
        with self.assertRaises(PermissionDenied):
            ext.create_shift_definition("day", "07:00", "19:00", EMPLOYEE)
        with self.assertRaises(PermissionDenied):
            ext.create_shift_definition("day", "07:00", "19:00", AUDITOR)


class TestRotationDefinitions(unittest.TestCase):
    """Entry idx 713: rotation definitions bind opaque refs to a core position."""

    def test_create_rotation_shape_and_flags(self):
        """A rotation record binds a core position and the caller's ordered person_refs, with the engine absence stated on its face."""
        _, position, ext, _, _, rotation = make_schedule()
        self.assertEqual(rotation["id"], "rot-1")
        self.assertEqual(rotation["position_id"], position["id"])
        self.assertEqual(rotation["person_refs"], ["carol", "staff-2"])
        self.assertTrue(rotation["definition_only"])
        self.assertFalse(rotation["generated_here"])
        self.assertFalse(rotation["optimized_here"])
        self.assertFalse(rotation["automated_here"])

    def test_rotation_stored_record_carries_no_derived_key(self):
        """The stored rotation record carries no coverage/status key: coverage derives at read only."""
        _, _, ext, _, _, rotation = make_schedule()
        stored = ext.get_rotation(rotation["id"], SPECIALIST)
        self.assertEqual(_walk_keys(stored) & {"coverage", "state", "status",
                                               "filled_count", "unfilled_count"},
                         set())

    def test_rotation_requires_existing_position_and_persons(self):
        """A rotation naming an unknown position or an unknown person is rejected whole."""
        _, position, ext = make_extensions()
        with self.assertRaises(NotFoundError):
            ext.create_rotation("pos-99", "R", ["carol"], SPECIALIST)
        with self.assertRaises(NotFoundError):
            ext.create_rotation(position["id"], "R", ["ghost"], SPECIALIST)

    def test_rotation_person_refs_validated(self):
        """Empty and duplicate person_ref lists are rejected before any id is allocated."""
        _, position, ext = make_extensions()
        with self.assertRaises(ValidationError):
            ext.create_rotation(position["id"], "R", [], SPECIALIST)
        with self.assertRaises(ValidationError):
            ext.create_rotation(position["id"], "R", ["carol", "carol"], SPECIALIST)
        rotation = ext.create_rotation(position["id"], "R", ["carol"], SPECIALIST)
        self.assertEqual(rotation["id"], "rot-1")

    def test_rotation_person_refs_deep_copied(self):
        """Mutating the returned person_refs list does not reach the stored record."""
        _, _, ext, _, _, rotation = make_schedule()
        rotation["person_refs"].append("staff-3")
        stored = ext.get_rotation(rotation["id"], SPECIALIST)
        self.assertEqual(stored["person_refs"], ["carol", "staff-2"])

    def test_rotation_employee_scope(self):
        """Employee readers see only rotations they are a member of; a non-member get is denied."""
        _, _, ext, _, _, rotation = make_schedule()
        member_view = ext.list_rotations(EMPLOYEE)
        self.assertEqual([r["id"] for r in member_view], [rotation["id"]])
        outsider = ext.list_rotations(
            type(EMPLOYEE)("staff-3", "employee"))
        self.assertEqual(outsider, [])
        with self.assertRaises(PermissionDenied):
            ext.get_rotation(rotation["id"],
                             type(EMPLOYEE)("staff-3", "employee"))


class TestRosterAssignments(unittest.TestCase):
    """Entry idx 713: roster assignments are caller-recorded records."""

    def test_record_assignment_shape_and_flags(self):
        """An assignment record is source 'recorded' and states decided_here / assigned_automatically False on its face."""
        _, position, ext, day, _, _ = make_schedule()
        record = ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "carol", SPECIALIST)
        self.assertEqual(record["id"], "ros-1")
        self.assertEqual(record["source"], "recorded")
        self.assertFalse(record["decided_here"])
        self.assertFalse(record["assigned_automatically"])
        self.assertFalse(record["optimized_here"])
        self.assertFalse(record["cancelled"])

    def test_assignment_requires_existing_records(self):
        """An assignment naming an unknown shift, position, or person is rejected whole."""
        _, position, ext, day, _, _ = make_schedule()
        with self.assertRaises(NotFoundError):
            ext.record_roster_assignment(
                "2026-11-09", "shf-99", position["id"], "carol", SPECIALIST)
        with self.assertRaises(NotFoundError):
            ext.record_roster_assignment(
                "2026-11-09", day["id"], "pos-99", "carol", SPECIALIST)
        with self.assertRaises(NotFoundError):
            ext.record_roster_assignment(
                "2026-11-09", day["id"], position["id"], "ghost", SPECIALIST)

    def test_assignment_date_validated(self):
        """A non-ISO date is rejected and consumes no id."""
        _, position, ext, day, _, _ = make_schedule()
        with self.assertRaises(ValidationError):
            ext.record_roster_assignment(
                "Nov 9", day["id"], position["id"], "carol", SPECIALIST)
        record = ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "carol", SPECIALIST)
        self.assertEqual(record["id"], "ros-1")

    def test_duplicate_active_assignment_refused(self):
        """A second active assignment for the same person, date, and shift is refused with no id consumed."""
        _, position, ext, day, _, _ = make_schedule()
        ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "carol", SPECIALIST)
        with self.assertRaises(ValidationError):
            ext.record_roster_assignment(
                "2026-11-09", day["id"], position["id"], "carol", SPECIALIST)
        other = ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "staff-2", SPECIALIST)
        self.assertEqual(other["id"], "ros-2")

    def test_cancel_then_rerecord_allowed(self):
        """Cancelling is a recorded flag, never a deletion; re-recording the same slot is then allowed."""
        _, position, ext, day, _, _ = make_schedule()
        record = ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "carol", SPECIALIST)
        cancelled = ext.cancel_roster_assignment(record["id"], SPECIALIST)
        self.assertTrue(cancelled["cancelled"])
        self.assertEqual(
            ext.get_roster_assignment(record["id"], SPECIALIST)["id"], "ros-1")
        with self.assertRaises(ValidationError):
            ext.cancel_roster_assignment(record["id"], SPECIALIST)
        again = ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "carol", SPECIALIST)
        self.assertEqual(again["id"], "ros-2")

    def test_assignment_flow_changes_no_core_record(self):
        """Recording and cancelling assignments leaves every core record byte-identical: the extension binds core records, it never modifies them."""
        store, position, ext, day, _, rotation = make_schedule()
        before_persons = store.list_persons(ADMIN)
        before_positions = store.list_positions(ADMIN)
        record = ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "carol", SPECIALIST)
        ext.cancel_roster_assignment(record["id"], SPECIALIST)
        self.assertEqual(store.list_persons(ADMIN), before_persons)
        self.assertEqual(store.list_positions(ADMIN), before_positions)

    def test_assignment_employee_scope(self):
        """Employee readers see only their own assignments; reading another person's is denied."""
        _, position, ext, day, _, _ = make_schedule()
        mine = ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "carol", SPECIALIST)
        theirs = ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "staff-2", SPECIALIST)
        self.assertEqual(
            [r["id"] for r in ext.list_roster_assignments(EMPLOYEE)],
            [mine["id"]])
        with self.assertRaises(PermissionDenied):
            ext.get_roster_assignment(theirs["id"], EMPLOYEE)
        with self.assertRaises(PermissionDenied):
            ext.list_roster_assignments(EMPLOYEE, person_ref="staff-2")


class TestRotationView(unittest.TestCase):
    """Entry idx 713: coverage derives at read through the seam."""

    def test_view_derives_filled_and_unfilled(self):
        """With a day assignment recorded and no call assignment, the view reads day filled, call unfilled."""
        _, position, ext, day, call, rotation = make_schedule()
        ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "carol", SPECIALIST)
        view = ext.rotation_view(rotation["id"], "2026-11-09", SPECIALIST)
        states = {c["shift_id"]: c["state"] for c in view["coverage"]}
        self.assertEqual(states[day["id"]], "filled")
        self.assertEqual(states[call["id"]], "unfilled")
        self.assertEqual(view["filled_count"], 1)
        self.assertEqual(view["unfilled_count"], 1)
        day_entry = [c for c in view["coverage"]
                     if c["shift_id"] == day["id"]][0]
        self.assertEqual(day_entry["assignment_count"], 1)
        self.assertEqual(day_entry["person_refs"], ["carol"])

    def test_view_cancelled_assignment_does_not_fill(self):
        """A cancelled assignment leaves the pair unfilled: derivation reads the recorded flag."""
        _, position, ext, day, _, rotation = make_schedule()
        record = ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "carol", SPECIALIST)
        ext.cancel_roster_assignment(record["id"], SPECIALIST)
        view = ext.rotation_view(rotation["id"], "2026-11-09", SPECIALIST)
        states = {c["shift_id"]: c["state"] for c in view["coverage"]}
        self.assertEqual(states[day["id"]], "unfilled")

    def test_view_nonmember_assignment_does_not_fill(self):
        """An assignment for a person outside the rotation does not fill the rotation's pair."""
        _, position, ext, day, _, rotation = make_schedule()
        ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "staff-3", SPECIALIST)
        view = ext.rotation_view(rotation["id"], "2026-11-09", SPECIALIST)
        states = {c["shift_id"]: c["state"] for c in view["coverage"]}
        self.assertEqual(states[day["id"]], "unfilled")

    def test_view_other_date_unfilled(self):
        """Coverage is per-date: an assignment on one date leaves another date unfilled."""
        _, position, ext, day, _, rotation = make_schedule()
        ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "carol", SPECIALIST)
        view = ext.rotation_view(rotation["id"], "2026-11-10", SPECIALIST)
        self.assertEqual(view["filled_count"], 0)

    def test_view_requires_report_read(self):
        """The coverage view is an aggregate derivation: the employee role (no report_read) is denied."""
        _, _, ext, _, _, rotation = make_schedule()
        with self.assertRaises(PermissionDenied):
            ext.rotation_view(rotation["id"], "2026-11-09", EMPLOYEE)


class TestScheduleSummary(unittest.TestCase):
    """Entry idx 713: the summary is deterministic counts over the records."""

    def test_summary_counts(self):
        """Counts and per-kind assignment counts derive at read from the recorded records only."""
        _, position, ext, day, call, _ = make_schedule()
        ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "carol", SPECIALIST)
        second = ext.record_roster_assignment(
            "2026-11-09", call["id"], position["id"], "staff-2", SPECIALIST)
        ext.cancel_roster_assignment(second["id"], SPECIALIST)
        summary = ext.schedule_summary(SPECIALIST)
        self.assertEqual(summary["shift_definitions"], 2)
        self.assertEqual(summary["rotation_definitions"], 1)
        self.assertEqual(summary["roster_assignments"], 2)
        self.assertEqual(summary["active_assignments"], 1)
        self.assertEqual(summary["cancelled_assignments"], 1)
        self.assertEqual(summary["assignments_by_shift_kind"]["day"], 1)
        self.assertEqual(summary["assignments_by_shift_kind"]["call"], 0)
        self.assertEqual(summary["method"], "deterministic_counts")


class TestPrivacyAndSignatures(unittest.TestCase):
    """Privacy discipline over the new surface (founding hard rule)."""

    def _all_surface_objects(self):
        store, position, ext, day, call, rotation = make_schedule()
        record = ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "carol", SPECIALIST)
        return [
            day, call, rotation, record,
            ext.rotation_view(rotation["id"], "2026-11-09", SPECIALIST),
            ext.schedule_summary(SPECIALIST),
            ext.list_roster_assignments(SPECIALIST),
        ]

    def test_no_forbidden_keys_on_surface(self):
        """Walking every extension record and view finds no key in the core privacy forbidden set."""
        for obj in self._all_surface_objects():
            self.assertEqual(_walk_keys(obj) & FORBIDDEN_KEYS, set())

    def test_signature_scan_no_pii_or_content_params(self):
        """No public method accepts a PII/content-shaped parameter, and none takes **kwargs."""
        for name, method in inspect.getmembers(HrExtensions,
                                               predicate=inspect.isfunction):
            if name.startswith("_"):
                continue
            params = inspect.signature(method).parameters
            for param_name, param in params.items():
                self.assertNotIn(param_name, FORBIDDEN_PARAMS,
                                 "%s.%s" % (name, param_name))
                self.assertNotEqual(param.kind, inspect.Parameter.VAR_KEYWORD,
                                    "%s takes **kwargs" % name)

    def test_smuggled_kwargs_raise_type_error(self):
        """Smuggled name=/email=/salary=/content= keyword arguments raise TypeError on the surface."""
        _, position, ext, day, _, _ = make_schedule()
        with self.assertRaises(TypeError):
            ext.create_shift_definition("day", "07:00", "19:00", SPECIALIST,
                                        email="x@example.org")
        with self.assertRaises(TypeError):
            ext.create_rotation(position["id"], "R", ["carol"], SPECIALIST,
                                name="Jane Doe")
        with self.assertRaises(TypeError):
            ext.record_roster_assignment(
                "2026-11-09", day["id"], position["id"], "carol", SPECIALIST,
                salary=100)
        with self.assertRaises(TypeError):
            ext.record_roster_assignment(
                "2026-11-09", day["id"], position["id"], "carol", SPECIALIST,
                content="night notes")


class TestAuditTrail(unittest.TestCase):
    """Successful extension mutations audit on the core log with ext_ actions."""

    def test_extension_actions_audited(self):
        """Creating a shift, a rotation, an assignment, and a cancellation each append an ext_ entry to the core audit log."""
        store, position, ext, day, _, _ = make_schedule()
        record = ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "carol", SPECIALIST)
        ext.cancel_roster_assignment(record["id"], SPECIALIST)
        actions = [e["action"] for e in store.audit.entries()]
        for expected in ("ext_shift_create", "ext_rotation_create",
                         "ext_assignment_create", "ext_assignment_cancel"):
            self.assertIn(expected, actions)


class TestNegativeControlPairState(unittest.TestCase):
    """Fresh negative control: the coverage derivation seam."""

    def test_canonical_pair_state(self):
        """Control (canonical): an active assignment fills the pair; no assignment and a cancelled-only assignment leave it unfilled."""
        active = {"cancelled": False}
        cancelled = {"cancelled": True}
        self.assertEqual(_derive_pair_state([active]), "filled")
        self.assertEqual(_derive_pair_state([]), "unfilled")
        self.assertEqual(_derive_pair_state([cancelled]), "unfilled")
        self.assertEqual(_derive_pair_state([cancelled, active]), "filled")

    def test_mutant_pair_state_is_rejected_by_the_canonical_expectation(self):
        """Control (mutant): with the module seam rebound to read every pair as filled, an unfilled pair reports filled — and the canonical expectation fails against it, proving the view's state assertions load on the seam."""
        import hr.extensions as extensions_module

        _, position, ext, day, call, rotation = make_schedule()
        ext.record_roster_assignment(
            "2026-11-09", day["id"], position["id"], "carol", SPECIALIST)
        canonical = ext.rotation_view(rotation["id"], "2026-11-09", SPECIALIST)
        canonical_states = {c["shift_id"]: c["state"]
                            for c in canonical["coverage"]}
        self.assertEqual(canonical_states[call["id"]], "unfilled")

        original = extensions_module._derive_pair_state
        extensions_module._derive_pair_state = lambda assignments: "filled"
        try:
            mutant = ext.rotation_view(rotation["id"], "2026-11-09", SPECIALIST)
        finally:
            extensions_module._derive_pair_state = original
        mutant_states = {c["shift_id"]: c["state"] for c in mutant["coverage"]}
        self.assertEqual(mutant_states[call["id"]], "filled")
        self.assertNotEqual(mutant_states[call["id"]],
                            canonical_states[call["id"]])
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_states[call["id"]], "unfilled")
        restored = ext.rotation_view(rotation["id"], "2026-11-09", SPECIALIST)
        restored_states = {c["shift_id"]: c["state"]
                           for c in restored["coverage"]}
        self.assertEqual(restored_states[call["id"]], "unfilled")


if __name__ == "__main__":
    unittest.main()
