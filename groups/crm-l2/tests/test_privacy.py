"""Privacy-discipline tests.

Traces to: the build's hard privacy rule (UNION-SPEC.md) -- records
are keyed by opaque caller-supplied references; NO entity shape can
hold a real name, email, phone number, SSN, date of birth, address,
or salary figure; and no score field exists anywhere, because no
claim defines one (vendor-stated text is stored verbatim instead).
"""

import unittest

import crm_helpers as H

FORBIDDEN_FIELDS = {
    "name", "email", "phone", "phone_number", "ssn", "dob",
    "date_of_birth", "address", "salary", "score", "lead_score",
}


def _all_entities(store, account, contact):
    case = store.create_case(H.OPERATOR, "problem", "Widget broken",
                             account_id=account["id"], contact_id=contact["id"])
    interaction = store.record_interaction(
        H.OPERATOR, "email", "inbound", "Status exchange",
        account_id=account["id"], case_id=case["id"])
    guide = store.create_guide(H.OPERATOR, "Onboarding", "walkthrough",
                                "surface:portal", steps=["Open portal"])
    finding = store.create_finding(H.OPERATOR, "Gap: checkout step",
                                    detail="42% drop-off (vendor-stated)",
                                    source="adoption review")
    module = store.create_module(H.ADMIN, "svc", "service", "flag=on")
    return {
        "account": account, "contact": contact, "case": case,
        "interaction": interaction, "guide": guide,
        "finding": finding, "module": module,
    }


class TestPrivacyShapes(unittest.TestCase):
    """Privacy: entity shapes carry no real-identifier fields."""

    def setUp(self):
        self.store, self.account, self.contact = H.make_store()
        self.entities = _all_entities(self.store, self.account, self.contact)

    def test_no_forbidden_fields_anywhere(self):
        """Privacy: no entity has a name/email/phone/ssn/dob/address/
        salary/score field."""
        for kind, entity in self.entities.items():
            bad = FORBIDDEN_FIELDS & set(entity.keys())
            self.assertEqual(bad, set(), "%s carries forbidden fields %s" % (kind, bad))

    def test_account_keyed_by_reference(self):
        """Privacy: accounts are keyed by the opaque reference."""
        self.assertEqual(self.account["reference"], "ACCT-100")

    def test_finding_detail_verbatim_no_score(self):
        """Privacy/claims discipline: finding detail is stored
        verbatim (including the vendor-stated figure) and no score
        is computed from it -- the report carries counts only."""
        finding = self.entities["finding"]
        self.assertEqual(finding["detail"], "42% drop-off (vendor-stated)")
        report = self.store.report(H.ADMIN)
        self.assertEqual(set(report["findings"].keys()),
                         {"total", "by_severity", "by_status"})

    def test_report_has_no_score_aggregate(self):
        """Claims discipline: the report contains no score/average
        aggregate anywhere -- counts of records only."""
        report = self.store.report(H.ADMIN)
        flat = str(report).lower()
        self.assertNotIn("score", flat)
        self.assertNotIn("average", flat)


if __name__ == "__main__":
    unittest.main()
