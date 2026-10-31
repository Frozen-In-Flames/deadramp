"""Core 9 (communication records), Core 13 (fee & payment
records), Core 14 (workflow definition registry), and Core 15
(integration registry).

Traces to: UNION-SPEC.md core functions 9, 13, 14, 15 — metadata
only communications (no content parameter exists), integer-cent
payments, registries that record and never execute.
"""

import inspect
import unittest

import contractmgmt_helpers as H
from contractmgmt.errors import NotFoundError, ValidationError
from contractmgmt.store import ContractMgmtStore


class TestCommunications(unittest.TestCase):
    """Core 9: communication records are metadata only."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()

    def test_communication_shape_pinned(self):
        """Core 9: the record carries exactly the contract's keys —
        there is no content field."""
        comm = self.store.record_communication(
            self.org["id"], "COM-1", H.COUNTERPARTY_REF, "outbound",
            "Award notification", H.MEMBER)
        self.assertEqual(
            set(comm.keys()),
            {"id", "org_id", "comm_ref", "counterparty_ref", "direction",
             "label", "created_by", "created_utc"},
        )

    def test_store_has_no_content_parameter(self):
        """Core 9 privacy pin: record_communication's signature has
        no parameter that could accept message content, and a
        smuggled content kwarg raises TypeError."""
        params = inspect.signature(
            ContractMgmtStore.record_communication).parameters
        self.assertNotIn("content", params)
        self.assertNotIn("body", params)
        self.assertNotIn("message", params)
        with self.assertRaises(TypeError):
            self.store.record_communication(
                self.org["id"], "COM-X", H.COUNTERPARTY_REF, "inbound",
                "Label", H.MEMBER, content="secret bid text")

    def test_direction_validated_and_filter(self):
        """Core 9: direction is inbound/outbound; listing filters
        by it."""
        with self.assertRaises(ValidationError):
            self.store.record_communication(
                self.org["id"], "COM-BAD", H.COUNTERPARTY_REF, "sideways",
                "Label", H.MEMBER)
        self.store.record_communication(
            self.org["id"], "COM-1", H.COUNTERPARTY_REF, "inbound",
            "Vendor question", H.MEMBER)
        self.store.record_communication(
            self.org["id"], "COM-2", H.COUNTERPARTY_REF, "outbound",
            "Answer", H.MEMBER)
        inbound = self.store.list_communications(
            self.org["id"], H.MEMBER, direction="inbound")
        self.assertEqual([c["comm_ref"] for c in inbound], ["COM-1"])


class TestPayments(unittest.TestCase):
    """Core 13: fee & payment records in integer cents."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        H.make_participant(self.store)
        self.opp = H.make_opportunity(self.store, self.org)
        self.sub = self.store.record_submission(
            self.org["id"], self.opp["id"], "SUB-1", H.PARTICIPANT_REF,
            H.MEMBER)
        self.award = self.store.record_award(
            self.org["id"], self.opp["id"], self.sub["id"], "AWD-1",
            500_000, H.MEMBER)

    def test_payment_shape_and_kinds(self):
        """Core 13: shape pinned; kinds are subscription and
        award_fee (the description's two fee mechanisms)."""
        payment = self.store.record_payment(
            self.org["id"], "PAY-1", "award_fee", 25_000, H.MEMBER,
            opportunity_id=self.opp["id"], award_id=self.award["id"])
        self.assertEqual(
            set(payment.keys()),
            {"id", "org_id", "payment_ref", "kind", "amount_cents",
             "opportunity_id", "award_id", "created_by", "created_utc"},
        )
        sub_payment = self.store.record_payment(
            self.org["id"], "PAY-2", "subscription", 120_000, H.MEMBER)
        self.assertEqual(sub_payment["kind"], "subscription")
        with self.assertRaises(ValidationError):
            self.store.record_payment(
                self.org["id"], "PAY-3", "invoice", 1, H.MEMBER)

    def test_payment_amount_positive_int_cents(self):
        """Core 13 / SI-10: payment amounts are positive integer
        cents — zero, negatives, booleans, floats, strings
        rejected."""
        for bad in (0, -1, True, 9.99, "100"):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.store.record_payment(
                    self.org["id"], "PAY-BAD", "subscription", bad, H.MEMBER)
        self.assertEqual(self.store.list_payments(self.org["id"], H.MEMBER),
                         [])

    def test_payment_links_must_exist_and_agree(self):
        """Core 13: linked opportunities/awards must exist in the
        organization, and an award link must belong to the linked
        opportunity."""
        with self.assertRaises(NotFoundError):
            self.store.record_payment(
                self.org["id"], "PAY-X", "subscription", 1, H.MEMBER,
                opportunity_id="opp-99")
        other = H.make_opportunity(self.store, self.org,
                                   opportunity_ref="OPP-2")
        with self.assertRaises(ValidationError):
            self.store.record_payment(
                self.org["id"], "PAY-Y", "award_fee", 1, H.MEMBER,
                opportunity_id=other["id"], award_id=self.award["id"])


class TestWorkflowRegistry(unittest.TestCase):
    """Core 14: workflow definitions are records only."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()

    def test_workflow_shape_and_uniqueness(self):
        """Core 14: shape pinned; refs unique within the
        organization."""
        workflow = self.store.register_workflow(
            self.org["id"], "WFL-1", "Standardized award workflow",
            H.MEMBER)
        self.assertEqual(
            set(workflow.keys()),
            {"id", "org_id", "workflow_ref", "label", "created_by",
             "created_utc"},
        )
        with self.assertRaises(ValidationError):
            self.store.register_workflow(
                self.org["id"], "WFL-1", "Clone", H.MEMBER)

    def test_registry_never_executes(self):
        """Core 14 doctrine pin: the store exposes no execute/run
        operation for workflows — the registry records definitions
        and nothing in the build runs them."""
        for name in dir(ContractMgmtStore):
            self.assertNotIn("execut", name.lower())
            self.assertNotIn("run_workflow", name.lower())


class TestIntegrationRegistry(unittest.TestCase):
    """Core 15: integration records are records of interfaces."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()

    def test_integration_shape_and_uniqueness(self):
        """Core 15: shape pinned; refs unique within the
        organization."""
        integration = self.store.register_integration(
            self.org["id"], "INT-1", "CONTRACTING-SYSTEM-REF",
            "System-to-system interface to the contracting system",
            H.MEMBER)
        self.assertEqual(
            set(integration.keys()),
            {"id", "org_id", "integration_ref", "system_ref", "label",
             "created_by", "created_utc"},
        )
        with self.assertRaises(ValidationError):
            self.store.register_integration(
                self.org["id"], "INT-1", "OTHER", "Clone", H.MEMBER)
        self.assertEqual(
            len(self.store.list_integrations(self.org["id"], H.MEMBER)), 1)


if __name__ == "__main__":
    unittest.main()
