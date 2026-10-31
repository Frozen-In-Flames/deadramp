"""Mutation-verified negative control for the suppression gate.

An oracle that passes whether or not suppression is enforced is
testing that code ran, not that the gate holds. So the canonical
gate expectation is asserted here against a MUTANT seam that
never refuses a delivery — under the mutant, a suppressed contact
can be recorded ``delivered`` — and the test asserts the
canonical check FAILS against the mutant. If the gate tests ever
stopped discriminating, this test fails.

The external drill (the same patch applied to the real
``src/marketsales/store.py``, suite re-run, file restored
byte-identical) is recorded in tests/README.md.
"""

import unittest

from marketsales_helpers import (ADMIN, CONTACT_A, OCCURRED, OPERATOR,
                                 make_campaign, make_org, make_store)

import marketsales.store as store_module

from marketsales.errors import ValidationError


def _mutant_gate(active_suppression, outcome):
    """Mutant seam: the gate never refuses."""
    return None


def canonical_gate_refuses_suppressed_delivery(store, campaign_id, list_id):
    """The gate suite's core expectation, stated once.

    Raises AssertionError (or lets an unexpected success escape as
    one) when a ``delivered`` outcome for an actively suppressed
    contact is recorded, or when the refusal leaves a record
    behind.
    """
    store.record_suppression(OPERATOR, list_id, CONTACT_A, "unsubscribe")
    try:
        store.record_delivery(OPERATOR, campaign_id, CONTACT_A,
                              "delivered", OCCURRED)
    except ValidationError:
        pass
    else:
        raise AssertionError(
            "a 'delivered' outcome was recorded for a suppressed "
            "contact; the gate did not refuse")
    assert store.list_deliveries(ADMIN, campaign_id=campaign_id) == [], (
        "the refused delivery left a record behind")


class NegativeControlTests(unittest.TestCase):
    def _setup(self):
        store, _audit = make_store()
        org = make_org(store)
        campaign, contact_list, _seg = make_campaign(store, org)
        return store, campaign["id"], contact_list["id"]

    def test_canonical_check_passes_on_the_real_store(self):
        store, campaign_id, list_id = self._setup()
        canonical_gate_refuses_suppressed_delivery(store, campaign_id,
                                                   list_id)

    def test_canonical_check_fails_on_the_mutant(self):
        store, campaign_id, list_id = self._setup()
        original = store_module._check_delivery_allowed
        store_module._check_delivery_allowed = _mutant_gate
        try:
            with self.assertRaises(AssertionError):
                canonical_gate_refuses_suppressed_delivery(
                    store, campaign_id, list_id)
        finally:
            store_module._check_delivery_allowed = original

    def test_gate_binds_only_the_delivered_outcome_on_the_real_store(self):
        """The other arm discriminates too: on the canonical store
        a ``bounced`` outcome for the same suppressed contact IS
        recorded, so the invariant is not simply 'suppressed
        contacts reject everything'."""
        store, campaign_id, list_id = self._setup()
        store.record_suppression(OPERATOR, list_id, CONTACT_A,
                                 "unsubscribe")
        record = store.record_delivery(OPERATOR, campaign_id, CONTACT_A,
                                       "bounced", OCCURRED)
        self.assertEqual(record["outcome"], "bounced")


ORACLE_EXPECTED = (
    "test_negative_control.NegativeControlTests."
    "test_canonical_check_passes_on_the_real_store, "
    "test_suppression_gate.SuppressionGateTests."
    "test_delivered_refused_for_suppressed_contact, "
    "test_service.ServiceTests.test_full_flow_with_suppression_gate"
)

if __name__ == "__main__":
    unittest.main()
