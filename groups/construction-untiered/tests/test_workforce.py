"""Workforce tests: workers, time entries, payrolls, violations, compliance.

Traces to: Core -- Workforce records (wrk-/time-/pay-/vio-) and the
compliance derivation ``ConstructStore._contractor_compliance``
(THE mutation-drill point): noncompliant if any open violation,
else compliant if a certified payroll exists, else no_records.
violation_write is ADMIN ONLY via the permission matrix.
"""

import unittest

from construct_helpers import ADMIN, OPERATOR, VIEWER, make_store
from construct.errors import NotFoundError, PermissionDenied, ValidationError

PS = "2025-01-01T00:00:00Z"
PE = "2025-01-15T00:00:00Z"


class TestWorkers(unittest.TestCase):
    """Workers: opaque reference required."""

    def test_create_shape(self):
        """Workers. create_worker makes wrk- with opaque reference, trade, attributes."""
        store, project, prime, sub = make_store()
        w = store.create_worker(OPERATOR, project["id"], prime["id"], "EMP-REF-42",
                                trade="welder", attributes={"crew": "A"})
        self.assertEqual(w["id"], "wrk-1")
        self.assertEqual(w["reference"], "EMP-REF-42")
        self.assertEqual(w["trade"], "welder")
        self.assertEqual(w["project_id"], project["id"])
        self.assertEqual(store.get_worker(w["id"], VIEWER)["reference"], "EMP-REF-42")

    def test_reference_required_and_refs_must_exist(self):
        """Workers. Empty/missing reference -> ValidationError; unknown project/org -> NotFoundError."""
        store, project, prime, sub = make_store()
        for bad in ("", "  ", None, 42):
            with self.subTest(reference=bad):
                with self.assertRaises(ValidationError):
                    store.create_worker(OPERATOR, project["id"], prime["id"], bad)
        with self.assertRaises(NotFoundError):
            store.create_worker(OPERATOR, "prj-99", prime["id"], "REF-1")
        with self.assertRaises(NotFoundError):
            store.create_worker(OPERATOR, project["id"], "org-99", "REF-1")
        w = store.create_worker(OPERATOR, project["id"], prime["id"], "REF-1")
        self.assertEqual(w["id"], "wrk-1")

    def test_list_filters(self):
        """Workers. list_workers filters by project_id and org_id."""
        store, project, prime, sub = make_store()
        store.create_worker(OPERATOR, project["id"], prime["id"], "R1")
        store.create_worker(OPERATOR, project["id"], sub["id"], "R2")
        self.assertEqual(len(store.list_workers(VIEWER, project_id=project["id"])), 2)
        self.assertEqual(len(store.list_workers(VIEWER, org_id=sub["id"])), 1)


class TestTimeEntries(unittest.TestCase):
    """Time entries: minutes rule, worker existence, immutability."""

    def _worker(self, store, project, prime):
        """Workforce helper: one worker on the fixture project."""
        return store.create_worker(OPERATOR, project["id"], prime["id"], "REF-T")

    def test_create_shape(self):
        """Time. create_time_entry makes time- with minutes/occurred_on/note."""
        store, project, prime, sub = make_store()
        w = self._worker(store, project, prime)
        e = store.create_time_entry(OPERATOR, w["id"], 480, occurred_on="2025-03-01T00:00:00Z", note="shift")
        self.assertEqual(e["id"], "time-1")
        self.assertEqual(e["minutes"], 480)
        self.assertEqual(e["worker_id"], w["id"])
        self.assertEqual(store.get_time_entry(e["id"], VIEWER)["note"], "shift")

    def test_minutes_must_be_positive_int(self):
        """Time. minutes bool/float/zero/negative/string -> ValidationError, no id consumed."""
        store, project, prime, sub = make_store()
        w = self._worker(store, project, prime)
        for bad in (True, False, 1.5, 0, -30, "60", None):
            with self.subTest(minutes=bad):
                with self.assertRaises(ValidationError):
                    store.create_time_entry(OPERATOR, w["id"], bad)
        e = store.create_time_entry(OPERATOR, w["id"], 15)
        self.assertEqual(e["id"], "time-1")

    def test_worker_must_exist_and_occurred_validated(self):
        """Time. Unknown worker -> NotFoundError; bad occurred_on -> ValidationError."""
        store, project, prime, sub = make_store()
        w = self._worker(store, project, prime)
        with self.assertRaises(NotFoundError):
            store.create_time_entry(OPERATOR, "wrk-99", 60)
        with self.assertRaises(ValidationError):
            store.create_time_entry(OPERATOR, w["id"], 60, occurred_on="junk")

    def test_immutable_and_project_filter(self):
        """Time. No update API; list project filter resolves through the worker."""
        store, project, prime, sub = make_store()
        self.assertFalse(hasattr(store, "update_time_entry"))
        w = self._worker(store, project, prime)
        store.create_time_entry(OPERATOR, w["id"], 60)
        other_project = store.create_project("Other", ADMIN)
        w2 = store.create_worker(OPERATOR, other_project["id"], prime["id"], "REF-O")
        store.create_time_entry(OPERATOR, w2["id"], 30)
        self.assertEqual(len(store.list_time_entries(VIEWER)), 2)
        self.assertEqual(len(store.list_time_entries(VIEWER, worker_id=w["id"])), 1)
        self.assertEqual(len(store.list_time_entries(VIEWER, project_id=project["id"])), 1)
        self.assertEqual(len(store.list_time_entries(VIEWER, project_id=other_project["id"])), 1)


class TestPayrolls(unittest.TestCase):
    """Payrolls: period, certified, money rules; immutability."""

    def test_create_shape(self):
        """Payrolls. create_payroll makes pay- with all fields."""
        store, project, prime, sub = make_store()
        p = store.create_payroll(OPERATOR, project["id"], prime["id"], PS, PE,
                                 certified=True, worker_count=12, total_wages_cents=99900)
        self.assertEqual(p["id"], "pay-1")
        self.assertTrue(p["certified"])
        self.assertEqual(p["worker_count"], 12)
        self.assertEqual(p["total_wages_cents"], 99900)

    def test_period_end_before_start_rejected(self):
        """Payrolls. period_end < period_start -> ValidationError; equal endpoints ok."""
        store, project, prime, sub = make_store()
        with self.assertRaises(ValidationError):
            store.create_payroll(OPERATOR, project["id"], prime["id"], PE, PS)
        ok = store.create_payroll(OPERATOR, project["id"], prime["id"], PS, PS)
        self.assertEqual(ok["id"], "pay-1")
        with self.assertRaises(ValidationError):
            store.create_payroll(OPERATOR, project["id"], prime["id"], None, PE)
        with self.assertRaises(ValidationError):
            store.create_payroll(OPERATOR, project["id"], prime["id"], PS, "junk")

    def test_certified_must_be_bool(self):
        """Payrolls. certified non-bool (incl. 1/'true') -> ValidationError."""
        store, project, prime, sub = make_store()
        for bad in (1, 0, "true", None):
            with self.subTest(certified=bad):
                with self.assertRaises(ValidationError):
                    store.create_payroll(OPERATOR, project["id"], prime["id"], PS, PE, certified=bad)

    def test_worker_count_and_money_rules(self):
        """Payrolls. worker_count bool/float/negative rejected; wages follow the money rule."""
        store, project, prime, sub = make_store()
        for bad in (True, 1.5, -1, "3"):
            with self.subTest(worker_count=bad):
                with self.assertRaises(ValidationError):
                    store.create_payroll(OPERATOR, project["id"], prime["id"], PS, PE, worker_count=bad)
        for bad in (1.5, True, -5, "100"):
            with self.subTest(wages=bad):
                with self.assertRaises(ValidationError):
                    store.create_payroll(OPERATOR, project["id"], prime["id"], PS, PE, total_wages_cents=bad)
        p = store.create_payroll(OPERATOR, project["id"], prime["id"], PS, PE, worker_count=0)
        self.assertEqual(p["worker_count"], 0)
        self.assertIsNone(p["total_wages_cents"])

    def test_immutable_and_filters(self):
        """Payrolls. No update API; list filters by project/org; unknown refs -> NotFoundError."""
        store, project, prime, sub = make_store()
        self.assertFalse(hasattr(store, "update_payroll"))
        store.create_payroll(OPERATOR, project["id"], prime["id"], PS, PE)
        store.create_payroll(OPERATOR, project["id"], sub["id"], PS, PE)
        self.assertEqual(len(store.list_payrolls(VIEWER, project_id=project["id"])), 2)
        self.assertEqual(len(store.list_payrolls(VIEWER, org_id=sub["id"])), 1)
        with self.assertRaises(NotFoundError):
            store.create_payroll(OPERATOR, "prj-99", prime["id"], PS, PE)


class TestViolations(unittest.TestCase):
    """Violations: admin-only writes, resolve guards."""

    def test_create_shape_admin(self):
        """Violations. Admin create makes vio- open with resolution/resolved_utc None."""
        store, project, prime, sub = make_store()
        v = store.create_violation(ADMIN, project["id"], prime["id"], "wage", "Late payroll")
        self.assertEqual(v["id"], "vio-1")
        self.assertEqual(v["status"], "open")
        self.assertIsNone(v["resolution"])
        self.assertIsNone(v["resolved_utc"])

    def test_operator_and_viewer_create_denied(self):
        """Violations. Operator/viewer create -> PermissionDenied (violation_write admin-only), no id consumed."""
        store, project, prime, sub = make_store()
        with self.assertRaises(PermissionDenied):
            store.create_violation(OPERATOR, project["id"], prime["id"], "wage", "X")
        with self.assertRaises(PermissionDenied):
            store.create_violation(VIEWER, project["id"], prime["id"], "wage", "X")
        v = store.create_violation(ADMIN, project["id"], prime["id"], "wage", "X")
        self.assertEqual(v["id"], "vio-1")

    def test_resolve_only_from_open(self):
        """Violations. resolve sets resolved/resolution/resolved_utc; second resolve -> ValidationError."""
        store, project, prime, sub = make_store()
        v = store.create_violation(ADMIN, project["id"], prime["id"], "wage", "Late")
        done = store.resolve_violation(v["id"], ADMIN, resolution="corrected and paid")
        self.assertEqual(done["status"], "resolved")
        self.assertEqual(done["resolution"], "corrected and paid")
        self.assertIsNotNone(done["resolved_utc"])
        with self.assertRaises(ValidationError):
            store.resolve_violation(v["id"], ADMIN)
        with self.assertRaises(PermissionDenied):
            store.resolve_violation(v["id"], OPERATOR)
        self.assertEqual(len(store.list_violations(VIEWER, status="resolved")), 1)
        self.assertEqual(len(store.list_violations(VIEWER, status="open")), 0)

    def test_validation(self):
        """Violations. Empty kind/description -> ValidationError; unknown refs -> NotFoundError."""
        store, project, prime, sub = make_store()
        with self.assertRaises(ValidationError):
            store.create_violation(ADMIN, project["id"], prime["id"], "", "X")
        with self.assertRaises(ValidationError):
            store.create_violation(ADMIN, project["id"], prime["id"], "wage", "")
        with self.assertRaises(NotFoundError):
            store.create_violation(ADMIN, project["id"], "org-99", "wage", "X")


class TestCompliance(unittest.TestCase):
    """Compliance: _contractor_compliance derivation (drill point)."""

    def test_no_records_with_nothing(self):
        """Compliance. Participant with nothing reads no_records with zero counts."""
        store, project, prime, sub = make_store()
        view = store.contractor_compliance(project["id"], prime["id"], VIEWER)
        self.assertEqual(view, {"project_id": project["id"], "org_id": prime["id"],
                                "status": "no_records", "certified_payrolls": 0,
                                "open_violations": 0})

    def test_compliant_after_certified_payroll(self):
        """Compliance. A certified payroll makes the pair compliant (count 1)."""
        store, project, prime, sub = make_store()
        store.create_payroll(OPERATOR, project["id"], prime["id"], PS, PE, certified=True)
        view = store.contractor_compliance(project["id"], prime["id"], OPERATOR)
        self.assertEqual(view["status"], "compliant")
        self.assertEqual(view["certified_payrolls"], 1)

    def test_uncertified_payroll_still_no_records(self):
        """Compliance. An uncertified payroll alone still reads no_records."""
        store, project, prime, sub = make_store()
        store.create_payroll(OPERATOR, project["id"], prime["id"], PS, PE, certified=False)
        view = store.contractor_compliance(project["id"], prime["id"], OPERATOR)
        self.assertEqual(view["status"], "no_records")
        self.assertEqual(view["certified_payrolls"], 0)

    def test_noncompliant_with_open_violation_even_with_certified_payroll(self):
        """Compliance. An open violation dominates: noncompliant even with a certified payroll."""
        store, project, prime, sub = make_store()
        store.create_payroll(OPERATOR, project["id"], prime["id"], PS, PE, certified=True)
        store.create_violation(ADMIN, project["id"], prime["id"], "wage", "Issue")
        view = store.contractor_compliance(project["id"], prime["id"], OPERATOR)
        self.assertEqual(view["status"], "noncompliant")
        self.assertEqual(view["open_violations"], 1)
        self.assertEqual(view["certified_payrolls"], 1)

    def test_back_to_compliant_after_resolve(self):
        """Compliance. Resolving the only open violation returns the pair to compliant."""
        store, project, prime, sub = make_store()
        store.create_payroll(OPERATOR, project["id"], prime["id"], PS, PE, certified=True)
        v = store.create_violation(ADMIN, project["id"], prime["id"], "wage", "Issue")
        self.assertEqual(store.contractor_compliance(project["id"], prime["id"], ADMIN)["status"], "noncompliant")
        store.resolve_violation(v["id"], ADMIN, resolution="fixed")
        view = store.contractor_compliance(project["id"], prime["id"], ADMIN)
        self.assertEqual(view["status"], "compliant")
        self.assertEqual(view["open_violations"], 0)

    def test_unknown_project_org_not_found(self):
        """Compliance. Unknown project or org -> NotFoundError."""
        store, project, prime, sub = make_store()
        with self.assertRaises(NotFoundError):
            store.contractor_compliance("prj-99", prime["id"], ADMIN)
        with self.assertRaises(NotFoundError):
            store.contractor_compliance(project["id"], "org-99", ADMIN)

    def test_pairs_are_independent(self):
        """Compliance. A violation for the sub does not affect the prime's status."""
        store, project, prime, sub = make_store()
        store.create_payroll(OPERATOR, project["id"], prime["id"], PS, PE, certified=True)
        store.create_violation(ADMIN, project["id"], sub["id"], "safety", "Issue")
        self.assertEqual(store.contractor_compliance(project["id"], prime["id"], ADMIN)["status"], "compliant")
        self.assertEqual(store.contractor_compliance(project["id"], sub["id"], ADMIN)["status"], "noncompliant")


if __name__ == "__main__":
    unittest.main()
