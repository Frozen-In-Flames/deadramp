"""Final GAPS batch — Contract Management L2 extension surface.

Traces to: GAPS.md section "Remainder Group 1 — Contract
Management L2 (2 forks, new category)" — the 9 open entries, and
the dispositions in the group's BATCH.md: regulatory corpus
records (metadata + SHA-256 digests, text never held), analytics
as deterministic derivation at read over the core records, portal
front-end definitions as data, reverse-auction reported bid /
outcome records (nothing ranked, no price discovered), the three
transports as receipt / transport / exchange records carrying
``reference_transport: True``, payment rails as settlement
records capped by the linked payment's recorded amount, and the
workflow engine as a labeled reference implementation.

Every test docstring names the entry it pins. The batch's fresh
negative control is TestSettlementBoundsNegativeControl: the
settlement bound seam ``_check_settlement_bounds`` in
``contractmgmt/extensions.py``.
"""

import unittest

import contractmgmt_helpers as H
from contractmgmt.errors import NotFoundError, PermissionDenied, ValidationError
from contractmgmt.extensions import (
    ContractExtensions,
    _check_settlement_bounds,
    _palt_seconds,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64

BANNED_KEYS = {
    "content", "text", "message", "score", "rating", "rank",
    "ranking", "lowest_bid", "winning_bid", "clause_text",
    "guidance_text", "bid_content", "submission_content",
}


def mutant_bounds(payment_amount_cents, committed_cents, amount_cents):
    """The mutant settlement gate: performs no check at all, so
    any settlement is waved through. Mirrors the canonical seam's
    signature."""
    return True


def _scan_keys(node, found):
    if isinstance(node, dict):
        for key, value in node.items():
            found.add(key)
            _scan_keys(value, found)
    elif isinstance(node, (list, tuple)):
        for value in node:
            _scan_keys(value, found)


class BatchFixture(unittest.TestCase):
    """Canonical fixture: core store + organization (per
    contractmgmt_helpers) with the extension surface over it."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        self.ext = ContractExtensions(self.store)
        self.oid = self.org["id"]

    def make_payment(self, ref="PAY-1", amount=10000, kind="subscription"):
        return self.store.record_payment(self.oid, ref, kind, amount,
                                         H.MEMBER)

    def make_auction_opportunity(self, ref="OPP-AUC-1"):
        return H.make_opportunity(
            self.store, self.org, opportunity_ref=ref,
            title="Reverse Auction", kind="reverse_auction")


class TestRegulatoryCorpus(BatchFixture):
    """Entry: Regulatory content & interpretation — corpus
    records as metadata + digests; interpretation as reported
    guidance records. Regulation text is never held."""

    def test_clause_shape_pinned(self):
        """The clause record carries exactly the extension's
        keys — metadata, citation, digest, source reference; no
        text field exists."""
        clause = self.ext.record_clause(
            self.oid, "CLZ-1", "FAR 52.212-4", DIGEST_A, "CORPUS-REF",
            H.MEMBER, label="Commercial terms")
        self.assertEqual(
            set(clause),
            {"id", "org_id", "clause_ref", "citation", "digest_sha256",
             "source_ref", "label", "content_held_here", "created_by",
             "created_utc"})
        self.assertEqual(clause["id"], "clz-1")
        self.assertIs(clause["content_held_here"], False)
        self.assertEqual(clause["digest_sha256"], DIGEST_A)

    def test_clause_text_cannot_be_supplied(self):
        """A smuggled text kwarg raises TypeError: the method
        signature has no parameter that can accept clause text."""
        with self.assertRaises(TypeError):
            self.ext.record_clause(
                self.oid, "CLZ-1", "FAR 52.212-4", DIGEST_A, "CORPUS-REF",
                H.MEMBER, text="the clause text itself")

    def test_digest_validated(self):
        """A digest must be a 64-character hex SHA-256; anything
        else is rejected whole and consumes no id."""
        for bad in ("abc", "g" * 64, 12345, None):
            with self.assertRaises(ValidationError):
                self.ext.record_clause(
                    self.oid, "CLZ-1", "FAR 52.212-4", bad, "CORPUS-REF",
                    H.MEMBER)
        clause = self.ext.record_clause(
            self.oid, "CLZ-1", "FAR 52.212-4", DIGEST_A.upper(),
            "CORPUS-REF", H.MEMBER)
        self.assertEqual(clause["id"], "clz-1")
        self.assertEqual(clause["digest_sha256"], DIGEST_A)

    def test_duplicate_clause_ref_rejected_no_id_consumed(self):
        self.ext.record_clause(self.oid, "CLZ-1", "FAR 52.212-4",
                               DIGEST_A, "CORPUS-REF", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_clause(self.oid, "CLZ-1", "FAR 52.212-5",
                                   DIGEST_B, "CORPUS-REF", H.MEMBER)
        second = self.ext.record_clause(self.oid, "CLZ-2", "DFARS 252.2",
                                        DIGEST_B, "CORPUS-REF", H.MEMBER)
        self.assertEqual(second["id"], "clz-2")

    def test_clause_view_derives_current_digest(self):
        """Derived-never-stored: before any update the current
        digest is the clause's own; after updates it is the
        latest update's. The stored clause record carries no
        current-digest key."""
        clause = self.ext.record_clause(
            self.oid, "CLZ-1", "FAR 52.212-4", DIGEST_A, "CORPUS-REF",
            H.MEMBER)
        view = self.ext.clause_view(self.oid, clause["id"], H.MEMBER)
        self.assertEqual(view["current_digest_sha256"], DIGEST_A)
        self.ext.record_clause_update(self.oid, clause["id"], "UPD-1",
                                      DIGEST_B, H.MEMBER)
        self.ext.record_clause_update(self.oid, clause["id"], "UPD-2",
                                      DIGEST_C, H.MEMBER)
        view = self.ext.clause_view(self.oid, clause["id"], H.MEMBER)
        self.assertEqual(view["current_digest_sha256"], DIGEST_C)
        self.assertEqual(len(view["updates"]), 2)
        stored = self.ext.list_clauses(self.oid, H.MEMBER)[0]
        self.assertNotIn("current_digest_sha256", stored)
        self.assertNotIn("updates", stored)

    def test_clause_update_unknown_clause(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_clause_update(self.oid, "clz-99", "UPD-1",
                                          DIGEST_B, H.MEMBER)

    def test_guidance_shape_and_links(self):
        """Guidance is a reported interpretation record: reporter
        reference, digest of the guidance text (held elsewhere),
        optional clause / core-requirement links, and
        interpreted_here False."""
        clause = self.ext.record_clause(
            self.oid, "CLZ-1", "FAR 52.212-4", DIGEST_A, "CORPUS-REF",
            H.MEMBER)
        requirement = self.store.create_requirement(
            self.oid, "REQ-1", "FAR compliance", H.MEMBER)
        guidance = self.ext.record_guidance(
            self.oid, "GUI-1", "COUNSEL-REF", DIGEST_B, H.MEMBER,
            clause_id=clause["id"], requirement_id=requirement["id"],
            label="Applicability note")
        self.assertEqual(
            set(guidance),
            {"id", "org_id", "guidance_ref", "clause_id",
             "requirement_id", "reporter_ref", "digest_sha256", "label",
             "interpreted_here", "created_by", "created_utc"})
        self.assertIs(guidance["interpreted_here"], False)
        with self.assertRaises(TypeError):
            self.ext.record_guidance(
                self.oid, "GUI-2", "COUNSEL-REF", DIGEST_B, H.MEMBER,
                guidance_text="the interpretation itself")
        with self.assertRaises(NotFoundError):
            self.ext.record_guidance(
                self.oid, "GUI-3", "COUNSEL-REF", DIGEST_B, H.MEMBER,
                clause_id="clz-99")


class TestAnalytics(BatchFixture):
    """Entry: Analytics engine — PALT measurement, bottleneck /
    spend analysis as deterministic derivations at read over the
    core records. Nothing estimated, scored, or ranked."""

    def test_palt_seam_exact_arithmetic(self):
        """The seam is exact day/second arithmetic over recorded
        timestamps."""
        self.assertEqual(
            _palt_seconds("2026-01-01T00:00:00+00:00",
                          "2026-01-11T12:00:00+00:00"), 907200)
        self.assertEqual(
            _palt_seconds("2026-01-01", "2026-01-02"), 86400)
        self.assertEqual(
            _palt_seconds("2026-01-01T00:00:00Z",
                          "2026-01-01T00:00:00Z"), 0)
        with self.assertRaises(ValidationError):
            _palt_seconds("2026-01-02T00:00:00Z", "2026-01-01T00:00:00Z")

    def _awarded_opportunity(self):
        H.make_participant(self.store)
        opp = H.make_opportunity(self.store, self.org)
        sub = self.store.record_submission(
            self.oid, opp["id"], "SUB-1", H.PARTICIPANT_REF, H.MEMBER)
        award = self.store.record_award(
            self.oid, opp["id"], sub["id"], "AWD-1", 5000, H.MEMBER)
        return opp, award

    def test_palt_report_over_core_records(self):
        """The report's span for an award is the seam applied to
        the recorded opportunity / award timestamps; the summary
        is exact arithmetic over the spans."""
        opp, award = self._awarded_opportunity()
        report = self.ext.palt_report(self.oid, H.MEMBER)
        self.assertEqual(len(report["entries"]), 1)
        entry = report["entries"][0]
        self.assertEqual(entry["opportunity_id"], opp["id"])
        self.assertEqual(entry["award_id"], award["id"])
        expected = _palt_seconds(opp["created_utc"], award["created_utc"])
        self.assertEqual(entry["palt_seconds"], expected)
        self.assertEqual(report["summary"]["award_count"], 1)
        self.assertEqual(report["summary"]["total_seconds"], expected)
        self.assertEqual(report["summary"]["mean_seconds"], expected)
        self.assertEqual(report["summary"]["min_seconds"], expected)
        self.assertEqual(report["summary"]["max_seconds"], expected)

    def test_palt_report_empty(self):
        report = self.ext.palt_report(self.oid, H.MEMBER)
        self.assertEqual(report["entries"], [])
        self.assertEqual(report["summary"]["award_count"], 0)
        self.assertIsNone(report["summary"]["mean_seconds"])

    def test_spend_report_by_kind_and_net_modifications(self):
        """Spend sums group recorded award cents by the
        opportunity kind the records carry; modification cents
        net across contracts."""
        contract = H.make_contract(self.store, self.org)
        self.store.record_modification(self.oid, contract["id"], "MOD-1",
                                       250, H.MEMBER)
        self.store.record_modification(self.oid, contract["id"], "MOD-2",
                                       -50, H.MEMBER)
        self._awarded_opportunity()
        auction = self.make_auction_opportunity()
        H.make_participant(self.store, participant_ref=H.PARTICIPANT2_REF,
                           label="Registered Vendor Two")
        sub = self.store.record_submission(
            self.oid, auction["id"], "SUB-9", H.PARTICIPANT2_REF, H.MEMBER)
        self.store.record_award(self.oid, auction["id"], sub["id"],
                                "AWD-9", 7000, H.MEMBER)
        spend = self.ext.spend_report(self.oid, H.MEMBER)
        self.assertEqual(spend["award_cents_by_kind"],
                         {"erfx": 5000, "reverse_auction": 7000})
        self.assertEqual(spend["award_count_by_kind"],
                         {"erfx": 1, "reverse_auction": 1})
        self.assertEqual(spend["net_modification_cents"], 200)

    def test_bottleneck_report_counts(self):
        """Each count is the core's own derived flag or status,
        counted at read: past-close open opportunities, unawarded
        submissions, overdue open cases, elapsed active
        contracts, open requirements."""
        past = H.make_opportunity(self.store, self.org,
                                  opportunity_ref="OPP-OLD",
                                  closes_at="2020-06-01")
        open_opp = H.make_opportunity(self.store, self.org,
                                      opportunity_ref="OPP-OPEN")
        H.make_participant(self.store)
        self.store.record_submission(self.oid, open_opp["id"], "SUB-1",
                                     H.PARTICIPANT_REF, H.MEMBER)
        contract = H.make_contract(self.store, self.org,
                                   period_start="2020-01-01",
                                   period_end="2020-12-31")
        self.store.create_protest(self.oid, "PRO-1", "Protest",
                                  "2020-01-01", H.MEMBER,
                                  contract_id=contract["id"])
        self.store.create_datacall(self.oid, "DCL-1", "REQ-REF",
                                   "Data call", "2020-01-01", H.MEMBER)
        self.store.create_requirement(self.oid, "REQ-1", "Requirement",
                                      H.MEMBER)
        bottlenecks = self.ext.bottleneck_report(self.oid, H.MEMBER)
        self.assertEqual(bottlenecks["opportunities_open_past_close"], 1)
        self.assertEqual(bottlenecks["submissions_awaiting_award"], 1)
        self.assertEqual(bottlenecks["protests_open_overdue"], 1)
        self.assertEqual(bottlenecks["datacalls_open_overdue"], 1)
        self.assertEqual(bottlenecks["contracts_active_period_elapsed"], 1)
        self.assertEqual(bottlenecks["requirements_open"], 1)
        self.assertEqual(past["status"], "open")

    def test_analytics_report_combined_and_no_score_keys(self):
        """The combined report names its method and carries no
        score / rating / ranking key anywhere, recursively."""
        self._awarded_opportunity()
        report = self.ext.analytics_report(self.oid, H.MEMBER)
        self.assertEqual(report["method"], "deterministic_derivation")
        self.assertEqual(set(report),
                         {"org_id", "method", "palt", "bottlenecks", "spend"})
        found = set()
        _scan_keys(report, found)
        self.assertFalse(found & BANNED_KEYS)

    def test_analytics_outsider_denied(self):
        """The membership boundary binds analytics too."""
        with self.assertRaises(PermissionDenied):
            self.ext.analytics_report(self.oid, H.OUTSIDER)


class TestPortalDefinitions(BatchFixture):
    """Entry: Opportunity portal front-end — portal and page
    definition records held as data; nothing rendered or
    served."""

    def test_portal_and_page_shapes(self):
        portal = self.ext.define_portal(self.oid, "POR-1", "Public portal",
                                        H.MEMBER)
        self.assertEqual(
            set(portal),
            {"id", "org_id", "portal_ref", "label", "rendered_here",
             "served_here", "created_by", "created_utc"})
        self.assertIs(portal["rendered_here"], False)
        self.assertIs(portal["served_here"], False)
        opp = H.make_opportunity(self.store, self.org)
        page = self.ext.define_page(self.oid, portal["id"], "PGE-1",
                                    H.MEMBER, label="Opportunity detail",
                                    opportunity_id=opp["id"])
        self.assertEqual(
            set(page),
            {"id", "org_id", "portal_id", "page_ref", "label",
             "opportunity_id", "rendered_here", "created_by",
             "created_utc"})
        view = self.ext.portal_view(self.oid, portal["id"], H.MEMBER)
        self.assertEqual([p["id"] for p in view["pages"]], [page["id"]])

    def test_page_unknown_opportunity_rejected(self):
        portal = self.ext.define_portal(self.oid, "POR-1", "Public portal",
                                        H.MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.define_page(self.oid, portal["id"], "PGE-1", H.MEMBER,
                                 opportunity_id="opp-99")

    def test_duplicate_portal_ref_rejected(self):
        self.ext.define_portal(self.oid, "POR-1", "Public portal", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.define_portal(self.oid, "POR-1", "Directed portal",
                                   H.MEMBER)


class TestReverseAuction(BatchFixture):
    """Entry: Reverse auction engine — reported bid and outcome
    records held as data. Nothing is ordered, ranked, or
    compared; no winner or price is derived; recording them
    leaves every core record byte-identical."""

    def setUp(self):
        super().setUp()
        H.make_participant(self.store)
        self.auction = self.make_auction_opportunity()

    def test_bid_shape_and_recording_order(self):
        """Bids are listed in recording order with amounts
        exactly as reported — the surface applies no ordering by
        amount."""
        first = self.ext.record_auction_bid(
            self.oid, self.auction["id"], "BID-1", H.PARTICIPANT_REF,
            900, H.MEMBER)
        second = self.ext.record_auction_bid(
            self.oid, self.auction["id"], "BID-2", H.PARTICIPANT_REF,
            500, H.MEMBER)
        self.assertEqual(
            set(first),
            {"id", "org_id", "opportunity_id", "bid_ref",
             "participant_ref", "amount_cents", "discovered_here",
             "conducted_here", "created_by", "created_utc"})
        self.assertIs(first["discovered_here"], False)
        self.assertIs(first["conducted_here"], False)
        bids = self.ext.list_auction_bids(self.oid, self.auction["id"],
                                          H.MEMBER)
        self.assertEqual([b["id"] for b in bids],
                         [first["id"], second["id"]])
        self.assertEqual([b["amount_cents"] for b in bids], [900, 500])

    def test_bid_guards(self):
        """Kind, registration, and money discipline: a non-auction
        opportunity, an unregistered participant, and non-integer
        amounts are all rejected whole."""
        erfx = H.make_opportunity(self.store, self.org,
                                  opportunity_ref="OPP-E1")
        with self.assertRaises(ValidationError):
            self.ext.record_auction_bid(self.oid, erfx["id"], "BID-1",
                                        H.PARTICIPANT_REF, 100, H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_auction_bid(self.oid, self.auction["id"],
                                        "BID-1", "PAR-UNKNOWN", 100,
                                        H.MEMBER)
        for bad in (10.5, True, "100", -1):
            with self.assertRaises(ValidationError):
                self.ext.record_auction_bid(self.oid, self.auction["id"],
                                            "BID-1", H.PARTICIPANT_REF,
                                            bad, H.MEMBER)
        self.assertEqual(
            self.ext.list_auction_bids(self.oid, self.auction["id"],
                                       H.MEMBER), [])

    def test_outcome_verbatim_and_core_records_unchanged(self):
        """The reported outcome (including a reported winner
        reference) is held verbatim as reported data, and
        recording bids + an outcome leaves the core opportunity
        view, submissions, and awards byte-identical."""
        sub = self.store.record_submission(
            self.oid, self.auction["id"], "SUB-1", H.PARTICIPANT_REF,
            H.MEMBER)
        before = (
            self.store.get_opportunity(self.oid, self.auction["id"],
                                       H.MEMBER),
            self.store.list_submissions(self.oid, self.auction["id"],
                                        H.MEMBER),
            self.store.list_awards(self.oid, self.auction["id"], H.MEMBER),
        )
        self.ext.record_auction_bid(self.oid, self.auction["id"], "BID-1",
                                    H.PARTICIPANT_REF, 900, H.MEMBER)
        outcome = self.ext.record_auction_outcome(
            self.oid, self.auction["id"], "AUC-1", "reported_completed",
            H.MEMBER, reported_winner_ref="EXT-WINNER-REF")
        self.assertEqual(outcome["reported_winner_ref"], "EXT-WINNER-REF")
        self.assertIs(outcome["discovered_here"], False)
        after = (
            self.store.get_opportunity(self.oid, self.auction["id"],
                                       H.MEMBER),
            self.store.list_submissions(self.oid, self.auction["id"],
                                        H.MEMBER),
            self.store.list_awards(self.oid, self.auction["id"], H.MEMBER),
        )
        self.assertEqual(before, after)
        self.assertEqual(sub["id"], before[1][0]["id"])

    def test_auction_view_has_no_derived_winner(self):
        """The view's keys are exactly the core view, the bid and
        outcome records, and their counts — no winner, lowest, or
        ranking key exists anywhere in it."""
        self.ext.record_auction_bid(self.oid, self.auction["id"], "BID-1",
                                    H.PARTICIPANT_REF, 900, H.MEMBER)
        view = self.ext.auction_view(self.oid, self.auction["id"], H.MEMBER)
        self.assertEqual(set(view), {"opportunity", "bids", "outcomes",
                                     "bid_count", "outcome_count"})
        self.assertEqual(view["bid_count"], 1)
        found = set()
        _scan_keys(view, found)
        self.assertFalse(found & BANNED_KEYS)
        self.assertNotIn("winner", found)
        self.assertNotIn("lowest_bid_cents", found)


class TestIntakeReceipts(BatchFixture):
    """Entry: Submission intake transport — receipt records over
    core submissions, carrying reference_transport: True. The
    received content itself is never held."""

    def setUp(self):
        super().setUp()
        H.make_participant(self.store)
        self.opp = H.make_opportunity(self.store, self.org)
        self.sub = self.store.record_submission(
            self.oid, self.opp["id"], "SUB-1", H.PARTICIPANT_REF, H.MEMBER)

    def test_receipt_shape(self):
        receipt = self.ext.record_intake_receipt(
            self.oid, self.sub["id"], "RCP-1", "CHANNEL-REF", H.MEMBER,
            reported_digest_sha256=DIGEST_A)
        self.assertEqual(
            set(receipt),
            {"id", "org_id", "submission_id", "receipt_ref",
             "channel_ref", "reported_digest_sha256",
             "reference_transport", "transmitted_here",
             "content_held_here", "created_by", "created_utc"})
        self.assertIs(receipt["reference_transport"], True)
        self.assertIs(receipt["transmitted_here"], False)
        self.assertIs(receipt["content_held_here"], False)
        listed = self.ext.list_intake_receipts(
            self.oid, H.MEMBER, submission_id=self.sub["id"])
        self.assertEqual([r["id"] for r in listed], [receipt["id"]])

    def test_receipt_guards(self):
        """Unknown submission, a malformed reported digest, and a
        smuggled content kwarg are all refused."""
        with self.assertRaises(NotFoundError):
            self.ext.record_intake_receipt(self.oid, "sub-99", "RCP-1",
                                           "CHANNEL-REF", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_intake_receipt(
                self.oid, self.sub["id"], "RCP-1", "CHANNEL-REF", H.MEMBER,
                reported_digest_sha256="not-a-digest")
        with self.assertRaises(TypeError):
            self.ext.record_intake_receipt(
                self.oid, self.sub["id"], "RCP-1", "CHANNEL-REF", H.MEMBER,
                content="the proposal itself")


class TestSettlements(BatchFixture):
    """Entry: Payment processing rails — settlement records over
    core payment records, capped cumulatively by the payment's
    recorded amount. No money moves here."""

    def test_settlement_shape_and_labels(self):
        payment = self.make_payment()
        settlement = self.ext.record_settlement(
            self.oid, payment["id"], "SET-1", 6000, H.MEMBER)
        self.assertEqual(
            set(settlement),
            {"id", "org_id", "payment_id", "settlement_ref",
             "amount_cents", "settled_here", "moved_here", "created_by",
             "created_utc"})
        self.assertIs(settlement["settled_here"], False)
        self.assertIs(settlement["moved_here"], False)
        view = self.ext.settlement_view(self.oid, settlement["id"],
                                        H.MEMBER)
        self.assertEqual(view["current_outcome"], "recorded")
        self.assertNotIn("current_outcome", settlement)

    def test_settlement_money_discipline(self):
        """Booleans, floats, strings, zero, and negatives are
        rejected at the boundary and consume no id."""
        payment = self.make_payment()
        for bad in (10.5, True, "100", 0, -5):
            with self.assertRaises(ValidationError):
                self.ext.record_settlement(self.oid, payment["id"],
                                           "SET-1", bad, H.MEMBER)
        settlement = self.ext.record_settlement(
            self.oid, payment["id"], "SET-1", 100, H.MEMBER)
        self.assertEqual(settlement["id"], "set-1")

    def test_unknown_payment_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_settlement(self.oid, "pay-99", "SET-1", 100,
                                       H.MEMBER)

    def test_report_flow_and_derived_outcome(self):
        """Outcome labels are stored verbatim; the current
        outcome is the latest label, derived at read."""
        payment = self.make_payment()
        settlement = self.ext.record_settlement(
            self.oid, payment["id"], "SET-1", 6000, H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_settlement_report(
                self.oid, settlement["id"], "SR-1", "settled", H.MEMBER)
        self.ext.record_settlement_report(
            self.oid, settlement["id"], "SR-1", "reported_partial",
            H.MEMBER)
        view = self.ext.settlement_view(self.oid, settlement["id"],
                                        H.MEMBER)
        self.assertEqual(view["current_outcome"], "reported_partial")
        self.ext.record_settlement_report(
            self.oid, settlement["id"], "SR-2", "reported_settled",
            H.MEMBER)
        view = self.ext.settlement_view(self.oid, settlement["id"],
                                        H.MEMBER)
        self.assertEqual(view["current_outcome"], "reported_settled")
        self.assertEqual(len(view["reports"]), 2)

    def test_failed_report_releases_the_commitment(self):
        """A settlement whose latest report is reported_failed
        no longer commits the payment; a partial report leaves
        the full amount committed. The summary is derived at
        read."""
        payment = self.make_payment(amount=10000)
        first = self.ext.record_settlement(self.oid, payment["id"],
                                           "SET-1", 6000, H.MEMBER)
        summary = self.ext.payment_settlement_summary(
            self.oid, payment["id"], H.MEMBER)
        self.assertEqual(summary["committed_cents"], 6000)
        self.assertEqual(summary["remaining_cents"], 4000)
        self.ext.record_settlement_report(
            self.oid, first["id"], "SR-1", "reported_failed", H.MEMBER)
        summary = self.ext.payment_settlement_summary(
            self.oid, payment["id"], H.MEMBER)
        self.assertEqual(summary["committed_cents"], 0)
        self.assertEqual(summary["remaining_cents"], 10000)
        second = self.ext.record_settlement(self.oid, payment["id"],
                                            "SET-2", 9000, H.MEMBER)
        self.ext.record_settlement_report(
            self.oid, second["id"], "SR-2", "reported_partial", H.MEMBER)
        summary = self.ext.payment_settlement_summary(
            self.oid, payment["id"], H.MEMBER)
        self.assertEqual(summary["committed_cents"], 9000)
        self.assertEqual(summary["settlement_count"], 2)


class TestSettlementBoundsNegativeControl(BatchFixture):
    """Fresh negative control for the batch: the settlement
    bound seam ``_check_settlement_bounds`` in
    ``contractmgmt/extensions.py``.

    Traced claim: **the settlement bound is the SI-10 integrity
    boundary of the payment rails surface** — outstanding
    settlement amounts against a core payment never exceed the
    payment's recorded amount. Each canonical case asserts (1)
    the real implementation raises ValidationError and stores
    nothing / consumes no id, (2) the mutant gate would NOT
    raise, and (3) treating the mutant's outcome as expected
    fails."""

    def _assert_mutant_rejected(self, mutant_outcome):
        self.assertNotEqual(mutant_outcome, "rejected")
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, "rejected")

    def test_single_settlement_one_cent_over_payment(self):
        payment = self.make_payment(amount=10000)
        with self.assertRaises(ValidationError):
            _check_settlement_bounds(10000, 0, 10001)
        with self.assertRaises(ValidationError):
            self.ext.record_settlement(self.oid, payment["id"], "SET-1",
                                       10001, H.MEMBER)
        self.assertEqual(self.ext.list_settlements(self.oid, H.MEMBER), [])
        mutant_outcome = ("within bound" if mutant_bounds(10000, 0, 10001)
                          else "rejected")
        self.assertEqual(mutant_outcome, "within bound")
        self._assert_mutant_rejected(mutant_outcome)
        good = self.ext.record_settlement(self.oid, payment["id"],
                                          "SET-1", 5000, H.MEMBER)
        self.assertEqual(good["id"], "set-1")

    def test_two_settlements_each_within_whose_sum_exceeds(self):
        payment = self.make_payment(amount=10000)
        first = self.ext.record_settlement(self.oid, payment["id"],
                                           "SET-1", 6000, H.MEMBER)
        self.assertEqual(first["id"], "set-1")
        with self.assertRaises(ValidationError):
            _check_settlement_bounds(10000, 6000, 4001)
        with self.assertRaises(ValidationError):
            self.ext.record_settlement(self.oid, payment["id"], "SET-2",
                                       4001, H.MEMBER)
        self.assertEqual(
            len(self.ext.list_settlements(self.oid, H.MEMBER)), 1)
        mutant_outcome = ("within bound" if mutant_bounds(10000, 6000, 4001)
                          else "rejected")
        self.assertEqual(mutant_outcome, "within bound")
        self._assert_mutant_rejected(mutant_outcome)
        second = self.ext.record_settlement(self.oid, payment["id"],
                                            "SET-2", 4000, H.MEMBER)
        self.assertEqual(second["id"], "set-2")


class TestMessageTransports(BatchFixture):
    """Entry: Communication transport — transport records over
    core communication records, carrying reference_transport:
    True. The core communication is metadata only; no content
    field exists here either."""

    def setUp(self):
        super().setUp()
        self.comm = self.store.record_communication(
            self.oid, "COM-1", H.COUNTERPARTY_REF, "outbound",
            "Award notification", H.MEMBER)

    def test_transport_shape_and_report_flow(self):
        transport = self.ext.record_message_transport(
            self.oid, self.comm["id"], "MTR-1", "CHANNEL-REF", H.MEMBER)
        self.assertEqual(
            set(transport),
            {"id", "org_id", "communication_id", "transport_ref",
             "channel_ref", "reference_transport", "transmitted_here",
             "created_by", "created_utc"})
        self.assertIs(transport["reference_transport"], True)
        self.assertIs(transport["transmitted_here"], False)
        view = self.ext.message_transport_view(self.oid, transport["id"],
                                               H.MEMBER)
        self.assertEqual(view["current_outcome"], "recorded")
        self.ext.record_message_report(
            self.oid, transport["id"], "MR-1", "reported_delivered",
            H.MEMBER)
        view = self.ext.message_transport_view(self.oid, transport["id"],
                                               H.MEMBER)
        self.assertEqual(view["current_outcome"], "reported_delivered")
        self.assertNotIn("current_outcome", transport)

    def test_transport_guards(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_message_transport(self.oid, "com-99", "MTR-1",
                                              "CHANNEL-REF", H.MEMBER)
        with self.assertRaises(TypeError):
            self.ext.record_message_transport(
                self.oid, self.comm["id"], "MTR-1", "CHANNEL-REF",
                H.MEMBER, content="the message itself")


class TestWorkflowReference(BatchFixture):
    """Entry: Workflow execution engine — shipped as its
    drafted labeled reference implementation: run-request and
    reported-outcome records, reference_stub: True,
    executed_here: False. The core registry never executes, and
    neither does this surface."""

    def setUp(self):
        super().setUp()
        self.workflow = self.store.register_workflow(
            self.oid, "WFL-1", "Standard contracting workflow", H.MEMBER)

    def test_request_and_report_shapes(self):
        request = self.ext.request_workflow_run(
            self.oid, self.workflow["id"], "WRQ-1", H.MEMBER)
        self.assertEqual(
            set(request),
            {"id", "org_id", "workflow_id", "request_ref",
             "reference_stub", "executed_here", "state", "created_by",
             "created_utc"})
        self.assertIs(request["reference_stub"], True)
        self.assertIs(request["executed_here"], False)
        self.assertEqual(request["state"], "recorded_reference_only")
        report = self.ext.record_workflow_report(
            self.oid, request["id"], "WR-1", "reported_completed",
            H.MEMBER)
        self.assertIs(report["reference_stub"], True)
        self.assertIs(report["executed_here"], False)

    def test_requests_change_no_core_record(self):
        """Recording a run request and a report leaves the core
        workflow registry byte-identical: the registry stays a
        registry."""
        before = self.store.list_workflows(self.oid, H.MEMBER)
        request = self.ext.request_workflow_run(
            self.oid, self.workflow["id"], "WRQ-1", H.MEMBER)
        self.ext.record_workflow_report(
            self.oid, request["id"], "WR-1", "reported_failed", H.MEMBER)
        after = self.store.list_workflows(self.oid, H.MEMBER)
        self.assertEqual(before, after)

    def test_no_execute_operation_exists(self):
        """No method on the extension surface can execute
        anything: no callable name contains 'execute'."""
        executors = [name for name in dir(self.ext)
                     if "execute" in name and callable(getattr(self.ext,
                                                               name))]
        self.assertEqual(executors, [])


class TestIntegrationExchanges(BatchFixture):
    """Entry: Integration transport — exchange records over core
    integration records, carrying reference_transport: True and
    connected_here: False. Counts ride as reported; no exchanged
    content is held."""

    def setUp(self):
        super().setUp()
        self.integration = self.store.register_integration(
            self.oid, "INT-1", "GRANTS-SYS-REF", "Contracting/Grants "
            "interface", H.MEMBER)

    def test_exchange_shape_and_report_flow(self):
        exchange = self.ext.record_integration_exchange(
            self.oid, self.integration["id"], "XCH-1", "outbound", 42,
            H.MEMBER)
        self.assertEqual(
            set(exchange),
            {"id", "org_id", "integration_id", "exchange_ref",
             "direction", "records_reported", "reference_transport",
             "transmitted_here", "connected_here", "created_by",
             "created_utc"})
        self.assertIs(exchange["reference_transport"], True)
        self.assertIs(exchange["transmitted_here"], False)
        self.assertIs(exchange["connected_here"], False)
        self.assertEqual(exchange["records_reported"], 42)
        view = self.ext.exchange_view(self.oid, exchange["id"], H.MEMBER)
        self.assertEqual(view["current_outcome"], "recorded")
        self.ext.record_exchange_report(
            self.oid, exchange["id"], "XR-1", "reported_received",
            H.MEMBER)
        view = self.ext.exchange_view(self.oid, exchange["id"], H.MEMBER)
        self.assertEqual(view["current_outcome"], "reported_received")

    def test_exchange_guards(self):
        """Unknown integration, unknown direction, a non-integer
        count, and a smuggled content kwarg are all refused."""
        with self.assertRaises(NotFoundError):
            self.ext.record_integration_exchange(
                self.oid, "int-99", "XCH-1", "outbound", 1, H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_integration_exchange(
                self.oid, self.integration["id"], "XCH-1", "sideways", 1,
                H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_integration_exchange(
                self.oid, self.integration["id"], "XCH-1", "outbound",
                1.5, H.MEMBER)
        with self.assertRaises(TypeError):
            self.ext.record_integration_exchange(
                self.oid, self.integration["id"], "XCH-1", "outbound", 1,
                H.MEMBER, payload="the exchanged records themselves")


class TestAccessAndAudit(BatchFixture):
    """Batch-wide discipline: RBAC through the core matrix with
    denied User attempts audited ':denied', successful mutations
    audited with the ext_ prefix, and the membership boundary on
    every extension operation."""

    def test_viewer_write_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_clause(self.oid, "CLZ-1", "FAR 52.212-4",
                                   DIGEST_A, "CORPUS-REF", H.VIEWER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_clause_create:denied", actions)
        self.assertEqual(self.ext.list_clauses(self.oid, H.MEMBER), [])

    def test_outsider_denied_by_membership(self):
        """A platform member outside the organization is denied
        by the core membership boundary, enforced through the
        core store."""
        with self.assertRaises(PermissionDenied):
            self.ext.record_clause(self.oid, "CLZ-1", "FAR 52.212-4",
                                   DIGEST_A, "CORPUS-REF", H.OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.ext.list_clauses(self.oid, H.OUTSIDER)

    def test_successful_mutations_audited_with_ext_prefix(self):
        self.ext.record_clause(self.oid, "CLZ-1", "FAR 52.212-4",
                               DIGEST_A, "CORPUS-REF", H.MEMBER)
        actions = [e["action"] for e in self.audit.entries()
                   if e["action"].startswith("ext_")]
        self.assertEqual(actions, ["ext_clause_create"])
        entry = [e for e in self.audit.entries()
                 if e["action"] == "ext_clause_create"][0]
        self.assertEqual(entry["target"], "clz-1")
        self.assertEqual(entry["actor"], "bob")


class TestPrivacyScan(BatchFixture):
    """Privacy discipline across the whole extension surface:
    no record, view, or report carries a banned key (content,
    text, score, rating, ranking, winner derivations)."""

    def test_no_banned_keys_anywhere(self):
        clause = self.ext.record_clause(
            self.oid, "CLZ-1", "FAR 52.212-4", DIGEST_A, "CORPUS-REF",
            H.MEMBER)
        self.ext.record_guidance(self.oid, "GUI-1", "COUNSEL-REF",
                                 DIGEST_B, H.MEMBER,
                                 clause_id=clause["id"])
        payment = self.make_payment()
        settlement = self.ext.record_settlement(
            self.oid, payment["id"], "SET-1", 100, H.MEMBER)
        surface = [
            self.ext.list_clauses(self.oid, H.MEMBER),
            self.ext.clause_view(self.oid, clause["id"], H.MEMBER),
            self.ext.list_guidance(self.oid, H.MEMBER),
            self.ext.settlement_view(self.oid, settlement["id"], H.MEMBER),
            self.ext.payment_settlement_summary(self.oid, payment["id"],
                                                H.MEMBER),
            self.ext.analytics_report(self.oid, H.MEMBER),
        ]
        found = set()
        for node in surface:
            _scan_keys(node, found)
        self.assertFalse(found & BANNED_KEYS)
