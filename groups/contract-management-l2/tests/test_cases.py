"""Core 5 (compliance requirements), Core 6 (protests), Core 7
(data calls), and Core 8 (risk records).

Traces to: UNION-SPEC.md core functions 5-8 — guarded lifecycles,
exactly-one-link protests, due dates with derived overdue status.
"""

import unittest

import contractmgmt_helpers as H
from contractmgmt.errors import NotFoundError, ValidationError


class TestRequirements(unittest.TestCase):
    """Core 5: compliance requirement records."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()

    def _req(self, ref="REQ-1", label="FAR 52.204-21 safeguarding"):
        return self.store.create_requirement(
            self.org["id"], ref, label, H.MEMBER)

    def test_requirement_shape_and_lifecycle(self):
        """Core 5: shape pinned; lifecycle open -> satisfied and
        open -> waived, both guarded."""
        req = self._req()
        self.assertEqual(
            set(req.keys()),
            {"id", "org_id", "requirement_ref", "label", "status",
             "created_by", "created_utc"},
        )
        self.assertEqual(req["status"], "open")
        done = self.store.satisfy_requirement(self.org["id"], req["id"],
                                              H.MEMBER)
        self.assertEqual(done["status"], "satisfied")
        with self.assertRaises(ValidationError):
            self.store.waive_requirement(self.org["id"], req["id"], H.MEMBER)
        req2 = self._req("REQ-2")
        waived = self.store.waive_requirement(self.org["id"], req2["id"],
                                              H.MEMBER)
        self.assertEqual(waived["status"], "waived")
        with self.assertRaises(ValidationError):
            self.store.satisfy_requirement(self.org["id"], req2["id"],
                                           H.MEMBER)

    def test_duplicate_requirement_ref_rejected(self):
        """Core 5: requirement refs are unique within the
        organization."""
        self._req()
        with self.assertRaises(ValidationError):
            self._req(label="Clone")

    def test_list_filter_by_status(self):
        """Core 5: listing filters by lifecycle status; a bogus
        status is rejected."""
        self._req()
        req2 = self._req("REQ-2")
        self.store.satisfy_requirement(self.org["id"], req2["id"], H.MEMBER)
        self.assertEqual(
            len(self.store.list_requirements(self.org["id"], H.MEMBER)), 2)
        satisfied = self.store.list_requirements(
            self.org["id"], H.MEMBER, status="satisfied")
        self.assertEqual([r["id"] for r in satisfied], [req2["id"]])
        with self.assertRaises(ValidationError):
            self.store.list_requirements(self.org["id"], H.MEMBER,
                                         status="pending")


class TestProtests(unittest.TestCase):
    """Core 6: protest records — exactly one link, derived overdue."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        self.contract = H.make_contract(self.store, self.org)

    def _protest(self, **kw):
        kwargs = {
            "protest_ref": "PRO-1",
            "label": "Award protest response",
            "due_at": "2026-02-01",
            "contract_id": self.contract["id"],
        }
        kwargs.update(kw)
        return self.store.create_protest(self.org["id"], actor=H.MEMBER,
                                         **kwargs)

    def test_protest_shape_pinned_no_overdue_stored(self):
        """Core 6: the stored record carries exactly the contract's
        keys — overdue is derived, never stored."""
        protest = self._protest()
        self.assertEqual(
            set(protest.keys()),
            {"id", "org_id", "protest_ref", "contract_id",
             "opportunity_id", "label", "due_at", "status", "created_by",
             "created_utc"},
        )
        raw = self.store._protests[protest["id"]]
        self.assertNotIn("overdue", raw)

    def test_derived_overdue_flips_with_clock_and_close(self):
        """Core 6: overdue is derived at read — false before the due
        date, true after it while open, false once closed."""
        protest = self._protest()
        early = self.store.get_protest(self.org["id"], protest["id"],
                                       H.MEMBER, now="2026-01-15")
        self.assertFalse(early["overdue"])
        late = self.store.get_protest(self.org["id"], protest["id"],
                                      H.MEMBER, now="2026-03-01")
        self.assertTrue(late["overdue"])
        self.store.close_protest(self.org["id"], protest["id"], H.MEMBER)
        closed = self.store.get_protest(self.org["id"], protest["id"],
                                        H.MEMBER, now="2026-03-01")
        self.assertFalse(closed["overdue"])

    def test_exactly_one_link_required(self):
        """Core 6 / SI-10: a protest links to exactly one of a
        contract or an opportunity — both or neither is rejected."""
        with self.assertRaises(ValidationError):
            self._protest(opportunity_id="opp-x")  # both given
        with self.assertRaises(ValidationError):
            self._protest(contract_id=None)  # neither given

    def test_link_must_exist_in_org(self):
        """Core 6: the linked contract must exist in this
        organization."""
        with self.assertRaises(NotFoundError):
            self._protest(contract_id="con-99")

    def test_due_at_required_and_parseable(self):
        """Core 6: due_at is required and must parse."""
        with self.assertRaises(ValidationError):
            self._protest(due_at=None)
        with self.assertRaises(ValidationError):
            self._protest(due_at="next friday")

    def test_close_guarded(self):
        """Core 6: closing is a guarded open -> closed transition."""
        protest = self._protest()
        closed = self.store.close_protest(self.org["id"], protest["id"],
                                          H.MEMBER)
        self.assertEqual(closed["status"], "closed")
        with self.assertRaises(ValidationError):
            self.store.close_protest(self.org["id"], protest["id"], H.MEMBER)


class TestDatacalls(unittest.TestCase):
    """Core 7: data-call records."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()

    def _datacall(self, ref="DCL-1", due="2026-02-01"):
        return self.store.create_datacall(
            self.org["id"], ref, "AUDITOR-REF-001",
            "Quarterly contracting data call", due, H.MEMBER)

    def test_datacall_shape_and_derived_overdue(self):
        """Core 7: shape pinned; overdue derived at read, never
        stored."""
        datacall = self._datacall()
        self.assertEqual(
            set(datacall.keys()),
            {"id", "org_id", "datacall_ref", "requester_ref", "label",
             "due_at", "status", "created_by", "created_utc"},
        )
        self.assertNotIn("overdue", self.store._datacalls[datacall["id"]])
        view = self.store.get_datacall(self.org["id"], datacall["id"],
                                       H.MEMBER, now="2026-03-01")
        self.assertTrue(view["overdue"])
        view = self.store.get_datacall(self.org["id"], datacall["id"],
                                       H.MEMBER, now="2026-01-01")
        self.assertFalse(view["overdue"])

    def test_datacall_close_guarded_and_due_required(self):
        """Core 7: due_at is required; closing is guarded."""
        with self.assertRaises(ValidationError):
            self.store.create_datacall(
                self.org["id"], "DCL-X", "REQ-REF", "Label", None, H.MEMBER)
        datacall = self._datacall()
        self.store.close_datacall(self.org["id"], datacall["id"], H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.close_datacall(self.org["id"], datacall["id"],
                                      H.MEMBER)


class TestRisks(unittest.TestCase):
    """Core 8: risk records — visibility only, nothing scored."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()

    def test_risk_shape_lifecycle_and_contract_filter(self):
        """Core 8: shape pinned (no score field exists); lifecycle
        guarded; listing filters by contract link."""
        contract = H.make_contract(self.store, self.org)
        risk = self.store.create_risk(
            self.org["id"], "RSK-1", "Vendor concentration risk", H.MEMBER,
            contract_id=contract["id"])
        self.assertEqual(
            set(risk.keys()),
            {"id", "org_id", "risk_ref", "contract_id", "label", "status",
             "created_by", "created_utc"},
        )
        self.store.create_risk(self.org["id"], "RSK-2", "Unlinked risk",
                               H.MEMBER)
        linked = self.store.list_risks(self.org["id"], H.MEMBER,
                                       contract_id=contract["id"])
        self.assertEqual([r["risk_ref"] for r in linked], ["RSK-1"])
        closed = self.store.close_risk(self.org["id"], risk["id"], H.MEMBER)
        self.assertEqual(closed["status"], "closed")
        with self.assertRaises(ValidationError):
            self.store.close_risk(self.org["id"], risk["id"], H.MEMBER)

    def test_risk_contract_link_must_exist(self):
        """Core 8: a contract link must name a contract in this
        organization."""
        with self.assertRaises(NotFoundError):
            self.store.create_risk(
                self.org["id"], "RSK-X", "Bad link", H.MEMBER,
                contract_id="con-99")


if __name__ == "__main__":
    unittest.main()
