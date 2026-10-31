"""Core 10 (opportunity records), Core 11 (submission records),
and Core 12 (award records) — the FedConnect portal surface.

Traces to: UNION-SPEC.md core functions 10-12 — kinds from the
fork's own vocabulary, public/directed audiences, the submission
guards (open, not past close, registered, directed membership),
derived past_close and awarded, and the award-consumes-submission
rule.
"""

import unittest

import contractmgmt_helpers as H
from contractmgmt.errors import NotFoundError, PermissionDenied, ValidationError


class TestOpportunities(unittest.TestCase):
    """Core 10: opportunity records."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        H.make_participant(self.store)

    def test_opportunity_shape_and_kinds(self):
        """Core 10: shape pinned; the three kinds are the fork's own
        vocabulary (eRFX, reverse auction, financial assistance)."""
        opp = H.make_opportunity(self.store, self.org)
        self.assertEqual(
            set(opp.keys()),
            {"id", "org_id", "opportunity_ref", "title", "kind",
             "audience", "directed_to", "closes_at", "status",
             "created_by", "created_utc"},
        )
        self.assertEqual(opp["audience"], "public")
        self.assertEqual(opp["directed_to"], [])
        for kind in ("reverse_auction", "financial_assistance"):
            made = H.make_opportunity(
                self.store, self.org, opportunity_ref="OPP-%s" % kind,
                kind=kind)
            self.assertEqual(made["kind"], kind)
        with self.assertRaises(ValidationError):
            H.make_opportunity(self.store, self.org,
                               opportunity_ref="OPP-BAD", kind="sealed_bid")

    def test_stored_record_has_no_past_close(self):
        """Core 10: past_close is derived at read, never stored."""
        opp = H.make_opportunity(self.store, self.org,
                                 closes_at="2026-02-01")
        raw = self.store._opportunities[opp["id"]]
        self.assertNotIn("past_close", raw)
        early = self.store.get_opportunity(self.org["id"], opp["id"],
                                           H.MEMBER, now="2026-01-01")
        self.assertFalse(early["past_close"])
        late = self.store.get_opportunity(self.org["id"], opp["id"],
                                          H.MEMBER, now="2026-03-01")
        self.assertTrue(late["past_close"])

    def test_directed_requires_registered_participants(self):
        """Core 10: a directed opportunity needs a non-empty
        directed_to list of registered participants; a public one
        takes none."""
        with self.assertRaises(ValidationError):
            H.make_opportunity(self.store, self.org,
                               opportunity_ref="OPP-D1", audience="directed")
        with self.assertRaises(ValidationError):
            H.make_opportunity(self.store, self.org,
                               opportunity_ref="OPP-D2", audience="directed",
                               directed_to=["PAR-UNKNOWN"])
        with self.assertRaises(ValidationError):
            H.make_opportunity(self.store, self.org,
                               opportunity_ref="OPP-D3",
                               directed_to=[H.PARTICIPANT_REF])
        directed = H.make_opportunity(
            self.store, self.org, opportunity_ref="OPP-D4",
            audience="directed", directed_to=[H.PARTICIPANT_REF])
        self.assertEqual(directed["directed_to"], [H.PARTICIPANT_REF])

    def test_close_guarded(self):
        """Core 10: closing is a guarded open -> closed transition."""
        opp = H.make_opportunity(self.store, self.org)
        closed = self.store.close_opportunity(self.org["id"], opp["id"],
                                              H.MEMBER)
        self.assertEqual(closed["status"], "closed")
        with self.assertRaises(ValidationError):
            self.store.close_opportunity(self.org["id"], opp["id"], H.MEMBER)


class TestSubmissions(unittest.TestCase):
    """Core 11: submission records and their guards."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        H.make_participant(self.store)
        H.make_participant(self.store, participant_ref=H.PARTICIPANT2_REF,
                           label="Registered Vendor Two")

    def _submit(self, opp, ref="SUB-1", participant=H.PARTICIPANT_REF):
        return self.store.record_submission(
            self.org["id"], opp["id"], ref, participant, H.MEMBER)

    def test_submission_shape_and_derived_awarded(self):
        """Core 11: shape pinned; awarded is derived from award
        records, never stored."""
        opp = H.make_opportunity(self.store, self.org)
        sub = self._submit(opp)
        self.assertEqual(
            set(sub.keys()),
            {"id", "org_id", "opportunity_id", "submission_ref",
             "participant_ref", "created_by", "created_utc"},
        )
        self.assertNotIn("awarded", self.store._submissions[sub["id"]])
        view = self.store.get_submission(self.org["id"], sub["id"], H.MEMBER)
        self.assertFalse(view["awarded"])
        self.store.record_award(self.org["id"], opp["id"], sub["id"],
                                "AWD-1", 500_000, H.MEMBER)
        view = self.store.get_submission(self.org["id"], sub["id"], H.MEMBER)
        self.assertTrue(view["awarded"])

    def test_unregistered_participant_rejected(self):
        """Core 11: the submitter must be a registered participant."""
        opp = H.make_opportunity(self.store, self.org)
        with self.assertRaises(ValidationError):
            self._submit(opp, participant="PAR-GHOST")

    def test_directed_membership_guard(self):
        """Core 11: on a directed opportunity, only directed-to
        participants may submit — others are PermissionDenied."""
        opp = H.make_opportunity(
            self.store, self.org, opportunity_ref="OPP-DIR",
            audience="directed", directed_to=[H.PARTICIPANT_REF])
        ok = self._submit(opp)
        self.assertEqual(ok["participant_ref"], H.PARTICIPANT_REF)
        with self.assertRaises(PermissionDenied):
            self._submit(opp, ref="SUB-2", participant=H.PARTICIPANT2_REF)

    def test_closed_opportunity_rejects_submissions(self):
        """Core 11: submissions are recorded against open
        opportunities only."""
        opp = H.make_opportunity(self.store, self.org)
        self.store.close_opportunity(self.org["id"], opp["id"], H.MEMBER)
        with self.assertRaises(ValidationError):
            self._submit(opp)

    def test_past_close_opportunity_rejects_submissions(self):
        """Core 11: an opportunity past its close time accepts no
        further submissions."""
        opp = H.make_opportunity(self.store, self.org,
                                 closes_at="2020-01-01")
        with self.assertRaises(ValidationError):
            self._submit(opp)

    def test_duplicate_submission_ref_rejected(self):
        """Core 11: submission refs are unique within the
        opportunity."""
        opp = H.make_opportunity(self.store, self.org)
        self._submit(opp)
        with self.assertRaises(ValidationError):
            self._submit(opp, participant=H.PARTICIPANT2_REF)


class TestAwards(unittest.TestCase):
    """Core 12: award records."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        H.make_participant(self.store)
        self.opp = H.make_opportunity(self.store, self.org)
        self.sub = self.store.record_submission(
            self.org["id"], self.opp["id"], "SUB-1", H.PARTICIPANT_REF,
            H.MEMBER)

    def test_award_shape_and_money_discipline(self):
        """Core 12: shape pinned; amounts are integer cents >= 0 —
        booleans, floats, strings, negatives rejected."""
        award = self.store.record_award(
            self.org["id"], self.opp["id"], self.sub["id"], "AWD-1",
            750_000, H.MEMBER)
        self.assertEqual(
            set(award.keys()),
            {"id", "org_id", "opportunity_id", "submission_id",
             "award_ref", "amount_cents", "created_by", "created_utc"},
        )
        other = H.make_opportunity(self.store, self.org,
                                   opportunity_ref="OPP-2")
        sub2 = self.store.record_submission(
            self.org["id"], other["id"], "SUB-9", H.PARTICIPANT_REF,
            H.MEMBER)
        for bad in (True, 1.5, "10", -5):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.store.record_award(
                    self.org["id"], other["id"], sub2["id"], "AWD-BAD",
                    bad, H.MEMBER)

    def test_submission_awarded_at_most_once(self):
        """Core 12: recording an award consumes the submission; a
        second award against it is rejected."""
        self.store.record_award(self.org["id"], self.opp["id"],
                                self.sub["id"], "AWD-1", 1, H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.record_award(self.org["id"], self.opp["id"],
                                    self.sub["id"], "AWD-2", 2, H.MEMBER)

    def test_award_submission_must_belong_to_opportunity(self):
        """Core 12: a submission from another opportunity reads as
        NotFound here."""
        other = H.make_opportunity(self.store, self.org,
                                   opportunity_ref="OPP-2")
        with self.assertRaises(NotFoundError):
            self.store.record_award(self.org["id"], other["id"],
                                    self.sub["id"], "AWD-X", 1, H.MEMBER)


if __name__ == "__main__":
    unittest.main()
