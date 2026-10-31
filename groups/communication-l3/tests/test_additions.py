"""Remainder-addition tests — unit addition:communication-l3.

Traces to: the ADDENDUM.md for this group (the GovSlack addition).
Pins the addition's spec integrity (sheet count/order, membership
against ../../remainder.json, the literal claim table, the
zero-claim family set, verbatim evidence, census citations,
near-miss pins, group totals) and exercises the newcomer's claimed
shape against the substrate: channels-shaped group messaging with
dispatch + acknowledgement, the send gate with no enabled channel,
and the High-baseline audit chain + auditor boundary.

The taxonomy was applied verbatim (see
scratch/additions_extract.py, which ast-parses the original
extractor's taxonomy, asserts triple-equality, and reproduces the
original 6 forks' shipped claim tables exactly before tagging the
newcomer).
"""

import json
import os
import unittest

from comm_helpers import ADMIN, AUDITOR, OPERATOR, fresh_store, make_store
from comm.errors import PermissionDenied

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

NEW_FORK = "FR2230252267"
EVIDENCE = (
    "It's the leading channels-based messaging platform, used by "
    "millions to align their teams, unify their systems, and drive "
    "their business forward."
)
EXPECTED_CLAIMS = {"messaging": EVIDENCE}
ALL_FAMILIES = [
    "email_security", "ai_ml", "notifications_alerts",
    "delivery_verification", "messaging", "voice_telephony",
    "contacts_directory", "archiving_records", "search_ediscovery",
    "correspondence_casework", "secure_transmission",
    "key_certificate", "identity_access", "audit",
    "reporting_analytics", "workflow_automation",
    "scheduling_events", "tracking_awareness", "permits_surveys",
    "esignature", "payments",
]


def _load_sheets():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else data["specs"]


def _new_sheet():
    return [s for s in _load_sheets() if s["fork_id"] == NEW_FORK][0]


class TestAdditionsSpecIntegrity(unittest.TestCase):
    """The appended sheet: membership, claims, evidence, totals."""

    def test_sheet_count_and_membership(self):
        """Addendum §1: 7 sheets; the appended sheet is the unit's
        only fork, in unit order after the original 6."""
        sheets = _load_sheets()
        self.assertEqual(len(sheets), 7)
        with open(os.path.join(_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = [u for u in rem["build_units"]
                if u.get("unit_id") == "addition:communication-l3"][0]
        self.assertEqual(unit["fork_ids"], [NEW_FORK])
        self.assertEqual(sheets[-1]["fork_id"], NEW_FORK)
        originals = {s["fork_id"] for s in sheets[:6]}
        with open(os.path.join(_GROUP_ROOT, "scratch",
                               "member_ids.json")) as fh:
            self.assertEqual(originals, set(json.load(fh)))

    def test_registry_fields_as_published(self):
        """Addendum §1: vendor/product/tier/status recorded as the
        source publishes them (Slack Technologies / GovSlack,
        High, FedRAMP Certified, SaaS, Public Cloud)."""
        s = _new_sheet()
        self.assertEqual(s["vendor"], "Slack Technologies")
        self.assertEqual(s["product"], "GovSlack")
        self.assertEqual(s["fedramp_impact_level"], "High")
        self.assertEqual(s["cmmc_tier"], "L3-adjacent")
        self.assertEqual(s["authorization_status"], "FedRAMP Certified")
        self.assertEqual(s["service_model"], ["SaaS"])
        self.assertEqual(s["deployment_model"], "Public Cloud")
        self.assertEqual(s["deadramp_category"], "Communication")

    def test_literal_claim_table(self):
        """Addendum §2: exactly one claim — messaging, on the
        channels-based messaging sentence."""
        s = _new_sheet()
        got = {c["function_id"]: c["evidence"]
               for c in s["functions_claimed"]}
        self.assertEqual(got, EXPECTED_CLAIMS)
        labels = {c["function_id"]: c["function"]
                  for c in s["functions_claimed"]}
        self.assertEqual(labels, {"messaging": "Email & messaging channels"})

    def test_zero_claim_family_set(self):
        """Addendum §2: the other 20 families are unclaimed."""
        claimed = {c["function_id"] for c in _new_sheet()["functions_claimed"]}
        self.assertEqual(set(ALL_FAMILIES) - claimed,
                         set(ALL_FAMILIES) - {"messaging"})

    def test_group_totals(self):
        """Addendum §4: 7 forks, 12 claims total, 6 of 7 claiming
        (Akamai's zero-claim sheet stands)."""
        sheets = _load_sheets()
        total = sum(len(s["functions_claimed"]) for s in sheets)
        claiming = sum(1 for s in sheets if s["functions_claimed"])
        self.assertEqual(total, 12)
        self.assertEqual(claiming, 6)

    def test_evidence_and_description_verbatim(self):
        """Addendum §1/§2: the claim evidence is a verbatim
        substring of the sheet description, and the description is
        byte-equal to the cached marketplace record."""
        s = _new_sheet()
        self.assertIn(EVIDENCE, s["description"])
        with open(os.path.join(_ROOT, "raw", "data_dump.json")) as fh:
            dump = json.load(fh)
        prods = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
        rec = [p for p in prods if p["id"] == NEW_FORK][0]
        self.assertEqual(s["description"],
                         (rec.get("service_desc") or "").strip())

    def test_census_citations_verify(self):
        """Addendum §1: both census citations verify verbatim
        (verification is not a claim: the first citation,
        'Slack has transformed business communication.', tags no
        family)."""
        desc = _new_sheet()["description"]
        self.assertIn("Slack has transformed business communication.", desc)
        self.assertIn(EVIDENCE, desc)

    def test_near_miss_pins(self):
        """Addendum §2: the near-miss tokens are as recorded —
        search substance without the token, a secure-environment
        phrase with no contiguous secure-transmission phrase and
        no 'encrypt', and the standing absences (video, voice,
        audit, workflow, email) hold at the token level."""
        low = _new_sheet()["description"].lower()
        self.assertIn("find information", low)
        self.assertNotIn("search", low)
        self.assertIn("secure, enterprise-grade environment", low)
        self.assertNotIn("encrypt", low)
        self.assertIn("connect all their other software tools", low)
        for absent in ("video", "voice", "audit", "workflow", "email"):
            self.assertNotIn(absent, low)


class TestAdditionsSubstrate(unittest.TestCase):
    """The newcomer's claimed shape against the shipped core."""

    def test_govslack_group_messaging_flow(self):
        """Addendum §3 (messaging → Core 4/5/6/8): a message
        addressed to the team group is composed, dispatched via
        the reference transport with a labelled receipt, and
        acknowledged; records hold references and metadata only."""
        store, contact, group, _channel = make_store()
        msg = store.compose_message(
            OPERATOR, subject="Standup moved", body="Channel notice",
            group_ids=[group["id"]], channel_kinds=["email"],
            require_ack=True,
        )
        summary = store.dispatch_due(OPERATOR)
        self.assertEqual(summary, {"dispatched": 1, "delivered": 1,
                                   "failed": 0})
        d = store.list_deliveries(msg["id"], OPERATOR)[0]
        self.assertEqual(d["status"], "delivered")
        self.assertTrue(d["receipt"]["reference_transport"])
        status = store.ack_status(msg["id"], OPERATOR)
        self.assertEqual(status["pending_contact_ids"], [contact["id"]])
        store.acknowledge(d["id"], OPERATOR)
        status = store.ack_status(msg["id"], OPERATOR)
        self.assertEqual(status["acknowledged"], 1)
        self.assertEqual(status["pending_contact_ids"], [])

    def test_govslack_send_gate_no_enabled_channel(self):
        """Addendum §3 / Drill 1 shape: with no channel configured,
        dispatch fails the delivery with no_enabled_channel (this
        case trips under the send-gate mutant)."""
        store = fresh_store()
        contact = store.create_contact(
            "Erin Example", {"email": "erin@example.com"}, OPERATOR)
        msg = store.compose_message(
            OPERATOR, subject="Hi", body="B",
            contact_ids=[contact["id"]], channel_kinds=["email"])
        summary = store.dispatch_due(OPERATOR)
        self.assertEqual(summary["failed"], 1)
        d = store.list_deliveries(msg["id"], OPERATOR)[0]
        self.assertEqual(d["status"], "failed")
        self.assertEqual(d["failure_reason"], "no_enabled_channel")

    def test_govslack_high_baseline_chain_and_auditor(self):
        """Addendum §3 (High baseline unchanged): after the
        messaging flow the audit chain verifies, the compose is in
        the trail, and the auditor holds no compose permission."""
        store, contact, _group, _channel = make_store()
        store.compose_message(
            OPERATOR, subject="Hi", body="B",
            contact_ids=[contact["id"]], channel_kinds=["email"])
        self.assertEqual(store.audit.verify_chain(), (True, None))
        actions = [e["action"] for e in
                   store.audit.query(action="message_compose")]
        self.assertTrue(actions)
        with self.assertRaises(PermissionDenied):
            store.compose_message(
                AUDITOR, subject="Hi", body="B",
                contact_ids=[contact["id"]], channel_kinds=["email"])


if __name__ == "__main__":
    unittest.main()
