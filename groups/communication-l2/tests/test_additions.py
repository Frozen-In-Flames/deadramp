"""Remainder additions — unit addition:communication-l2 (1 fork).

Traces to: the addendum for Granicus / GovDelivery Communications
Cloud (F1311252652), appended to the shipped Communication L2 group
under its existing 21-family taxonomy applied verbatim. Pins: sheet
count and append order, unit membership against ../../remainder.json,
the literal claim table, verbatim evidence, the census citations
(verified as text; neither tags a family), the near-miss pins, and
the group's updated totals. Two substrate cases exercise the fork's
"Targeted Messaging Service" shape on the shipped Core: a targeted
group message dispatched through the reference transport with a
labelled receipt, and a send-gate case (an sms delivery with no sms
channel configured fails with no_enabled_channel) that trips under
the group's signature send-gate mutant.
"""

import json
import os
import unittest

from comm_helpers import ADMIN, OPERATOR, fresh_store, make_store

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

FORK_ID = "F1311252652"
ORIGINAL_IDS = [
    "FR2425960757", "FR2410560133", "F1512017637", "FR1728351539",
    "FR2309954376", "FR2529113288", "FR1830842316", "FR2335051964",
    "F1412165928", "FR2621751490",
]
EXPECTED_CLAIMS = {FORK_ID: ["messaging"]}
MESSAGING_EVIDENCE = (
    "The Advanced Package for Communications Cloud and the Targeted "
    "Messaging Service are feature offerings available with Granicus' "
    "GovDelivery Communications Cloud."
)


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _sheet(fork_id):
    for row in _load_specs():
        if row["fork_id"] == fork_id:
            return row
    raise AssertionError("sheet missing: %s" % fork_id)


class TestAdditionSpecIntegrity(unittest.TestCase):
    """Addendum section 1/2: membership, order, literal claims."""

    def test_sheet_count_and_append_order(self):
        """11 sheets: the original 10 in shipped order, newcomer last."""
        ids = [r["fork_id"] for r in _load_specs()]
        self.assertEqual(len(ids), 11)
        self.assertEqual(sorted(ids[:10]), sorted(ORIGINAL_IDS))
        self.assertEqual(ids[10], FORK_ID)

    def test_membership_matches_remainder_unit(self):
        """The appended sheet is exactly the census unit's fork list."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = [u for u in rem["build_units"]
                if u.get("unit_id") == "addition:communication-l2"]
        self.assertEqual(len(unit), 1)
        self.assertEqual(unit[0]["fork_ids"], [FORK_ID])
        self.assertIn(FORK_ID, [r["fork_id"] for r in _load_specs()])

    def test_literal_claim_table(self):
        """The newcomer claims exactly {messaging} under the verbatim taxonomy."""
        got = {c["function_id"] for c in _sheet(FORK_ID)["functions_claimed"]}
        self.assertEqual(got, set(EXPECTED_CLAIMS[FORK_ID]))

    def test_evidence_is_verbatim_and_exact(self):
        """The messaging evidence is the description's third sentence, verbatim."""
        sheet = _sheet(FORK_ID)
        claim = sheet["functions_claimed"][0]
        self.assertEqual(claim["evidence"], MESSAGING_EVIDENCE)
        self.assertIn(claim["evidence"], sheet["description"])

    def test_registry_fields_as_published(self):
        """Sheet fields record the source as published (Moderate, Certified, SaaS)."""
        sheet = _sheet(FORK_ID)
        self.assertEqual(sheet["vendor"], "Granicus")
        self.assertEqual(sheet["product"], "GovDelivery Communications Cloud")
        self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["business_categories_in_source"], [])

    def test_census_citations_verify_but_tag_nothing(self):
        """Both census citations are verbatim description text; neither
        is the claim's evidence (verification is not a claim)."""
        with open(os.path.join(_REPO_ROOT, "remainder", "class_all.json")) as fh:
            cls = json.load(fh)
        entry = [r for r in cls if r.get("fork_id") == FORK_ID]
        self.assertEqual(len(entry), 1)
        citations = entry[0]["citations"]
        self.assertEqual(len(citations), 2)
        sheet = _sheet(FORK_ID)
        for cit in citations:
            self.assertIn(cit, sheet["description"])
            self.assertNotEqual(cit, MESSAGING_EVIDENCE)

    def test_near_miss_pins(self):
        """Family-adjacent phrases are present in the text yet tag no
        family: marketing automation (workflow_automation needs an
        automat+object phrase), highly secure cloud communications
        (secure_transmission needs adjacency), customers (contacts_
        directory needs constituent/contacts phrasing)."""
        desc = _sheet(FORK_ID)["description"]
        self.assertIn("marketing automation platform", desc)
        self.assertIn("highly secure cloud communications", desc)
        self.assertIn("Targeted Messaging Service", desc)
        claimed = {c["function_id"] for c in _sheet(FORK_ID)["functions_claimed"]}
        for fam in ("workflow_automation", "secure_transmission",
                    "contacts_directory", "notifications_alerts", "ai_ml"):
            self.assertNotIn(fam, claimed)

    def test_group_totals(self):
        """Updated union: 11 forks, 53 claims, 11 of 11 claiming."""
        rows = _load_specs()
        total = sum(len(r["functions_claimed"]) for r in rows)
        claiming = sum(1 for r in rows if r["functions_claimed"])
        self.assertEqual(total, 53)
        self.assertEqual(claiming, 11)


class TestGranicusSubstrate(unittest.TestCase):
    """The fork's shape on the shipped Core (messaging substrate)."""

    def test_targeted_group_message_reference_receipt(self):
        """A message targeted at a directory group composes per
        recipient and dispatches through the reference transport:
        delivered, receipt labelled reference_transport: true."""
        store, contact, group, _channel = make_store()
        msg = store.compose_message(
            OPERATOR, subject="Service notice", body="Targeted notice body",
            group_ids=[group["id"]], channel_kinds=["email"],
            require_ack=True)
        summary = store.dispatch_due(OPERATOR)
        self.assertEqual(summary["delivered"], 1)
        d = store.list_deliveries(msg["id"], OPERATOR)[0]
        self.assertEqual(d["status"], "delivered")
        self.assertEqual(d["receipt"]["transport"], "reference")
        self.assertTrue(d["receipt"]["reference_transport"])
        store.acknowledge(d["id"], OPERATOR)
        status = store.ack_status(msg["id"], OPERATOR)
        self.assertEqual(status["acknowledged"], 1)
        self.assertEqual(status["pending_contact_ids"], [])

    def test_send_gate_absent_sms_channel_fails(self):
        """Send gate: an sms delivery with no sms channel configured
        fails with no_enabled_channel (trips under the send-gate
        mutant; see tests/README.md drill record)."""
        store, contact, _group, _channel = make_store()
        msg = store.compose_message(
            OPERATOR, subject="Alert", body="Alert body",
            contact_ids=[contact["id"]], channel_kinds=["sms"])
        summary = store.dispatch_due(OPERATOR)
        self.assertEqual(summary["failed"], 1)
        d = store.list_deliveries(msg["id"], OPERATOR)[0]
        self.assertEqual(d["status"], "failed")
        self.assertEqual(d["failure_reason"], "no_enabled_channel")


if __name__ == "__main__":
    unittest.main()
