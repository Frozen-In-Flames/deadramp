"""Privacy discipline: exact key-set pins for every entity shape,
no person/content/score field anywhere, and smuggled-field
rejection.

Traces to: UNION-SPEC.md "Privacy discipline (hard rule)" — records
hold metadata and opaque references, not substance; communications
have no content parameter; nothing is scored.
"""

import unittest

import contractmgmt_helpers as H


def _scan_no_banned(obj, path="root"):
    """Recursively assert no key names a score/rating/ranking or a
    content/person field."""
    banned = ("score", "rating", "rank", "grade", "content", "ssn",
              "email", "phone", "address", "name_of")
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = str(key).lower()
            for word in banned:
                if word in lowered:
                    raise AssertionError(
                        "banned key %r at %s" % (key, path))
            _scan_no_banned(value, path + "." + str(key))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            _scan_no_banned(value, "%s[%d]" % (path, index))


class TestPrivacyShapes(unittest.TestCase):
    """Exact key sets for every entity the store can produce."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        self.participant = H.make_participant(self.store)
        self.contract = H.make_contract(self.store, self.org)
        self.mod = self.store.record_modification(
            self.org["id"], self.contract["id"], "MOD-1", 100, H.MEMBER)
        self.requirement = self.store.create_requirement(
            self.org["id"], "REQ-1", "Label", H.MEMBER)
        self.protest = self.store.create_protest(
            self.org["id"], "PRO-1", "Label", "2027-01-01", H.MEMBER,
            contract_id=self.contract["id"])
        self.datacall = self.store.create_datacall(
            self.org["id"], "DCL-1", "REQ-REF", "Label", "2027-01-01",
            H.MEMBER)
        self.risk = self.store.create_risk(
            self.org["id"], "RSK-1", "Label", H.MEMBER)
        self.comm = self.store.record_communication(
            self.org["id"], "COM-1", H.COUNTERPARTY_REF, "inbound",
            "Label", H.MEMBER)
        self.opp = H.make_opportunity(self.store, self.org)
        self.sub = self.store.record_submission(
            self.org["id"], self.opp["id"], "SUB-1", H.PARTICIPANT_REF,
            H.MEMBER)
        self.award = self.store.record_award(
            self.org["id"], self.opp["id"], self.sub["id"], "AWD-1",
            100, H.MEMBER)
        self.payment = self.store.record_payment(
            self.org["id"], "PAY-1", "subscription", 100, H.MEMBER)
        self.workflow = self.store.register_workflow(
            self.org["id"], "WFL-1", "Label", H.MEMBER)
        self.integration = self.store.register_integration(
            self.org["id"], "INT-1", "SYS-REF", "Label", H.MEMBER)

    def test_all_shapes_pinned(self):
        """Privacy: every entity shape is pinned exactly."""
        expected = {
            "organization": (self.org, {
                "id", "org_ref", "label", "members", "created_by",
                "created_utc"}),
            "participant": (self.participant, {
                "id", "participant_ref", "label", "created_by",
                "created_utc"}),
            "contract": (self.store._contracts[self.contract["id"]], {
                "id", "org_id", "contract_ref", "title",
                "counterparty_ref", "ceiling_cents", "award_cents",
                "period_start", "period_end", "status", "created_by",
                "created_utc"}),
            "modification": (self.mod, {
                "id", "org_id", "contract_id", "mod_ref",
                "amount_cents", "label", "created_by", "created_utc"}),
            "requirement": (self.requirement, {
                "id", "org_id", "requirement_ref", "label", "status",
                "created_by", "created_utc"}),
            "protest": (self.protest, {
                "id", "org_id", "protest_ref", "contract_id",
                "opportunity_id", "label", "due_at", "status",
                "created_by", "created_utc"}),
            "datacall": (self.datacall, {
                "id", "org_id", "datacall_ref", "requester_ref",
                "label", "due_at", "status", "created_by",
                "created_utc"}),
            "risk": (self.risk, {
                "id", "org_id", "risk_ref", "contract_id", "label",
                "status", "created_by", "created_utc"}),
            "communication": (self.comm, {
                "id", "org_id", "comm_ref", "counterparty_ref",
                "direction", "label", "created_by", "created_utc"}),
            "opportunity": (self.store._opportunities[self.opp["id"]], {
                "id", "org_id", "opportunity_ref", "title", "kind",
                "audience", "directed_to", "closes_at", "status",
                "created_by", "created_utc"}),
            "submission": (self.store._submissions[self.sub["id"]], {
                "id", "org_id", "opportunity_id", "submission_ref",
                "participant_ref", "created_by", "created_utc"}),
            "award": (self.award, {
                "id", "org_id", "opportunity_id", "submission_id",
                "award_ref", "amount_cents", "created_by",
                "created_utc"}),
            "payment": (self.payment, {
                "id", "org_id", "payment_ref", "kind", "amount_cents",
                "opportunity_id", "award_id", "created_by",
                "created_utc"}),
            "workflow": (self.workflow, {
                "id", "org_id", "workflow_ref", "label", "created_by",
                "created_utc"}),
            "integration": (self.integration, {
                "id", "org_id", "integration_ref", "system_ref",
                "label", "created_by", "created_utc"}),
        }
        for name, (record, keys) in expected.items():
            self.assertEqual(set(record.keys()), keys, name)

    def test_derived_views_add_only_the_derived_keys(self):
        """Privacy/derivation: read views add exactly the derived
        keys and nothing else."""
        contract_view = self.store.get_contract(
            self.org["id"], self.contract["id"], H.MEMBER)
        self.assertEqual(
            set(contract_view.keys())
            - set(self.store._contracts[self.contract["id"]].keys()),
            {"obligated_cents", "period_elapsed"})
        protest_view = self.store.get_protest(
            self.org["id"], self.protest["id"], H.MEMBER)
        self.assertEqual(
            set(protest_view.keys())
            - set(self.store._protests[self.protest["id"]].keys()),
            {"overdue"})
        opp_view = self.store.get_opportunity(
            self.org["id"], self.opp["id"], H.MEMBER)
        self.assertEqual(
            set(opp_view.keys())
            - set(self.store._opportunities[self.opp["id"]].keys()),
            {"past_close"})
        sub_view = self.store.get_submission(
            self.org["id"], self.sub["id"], H.MEMBER)
        self.assertEqual(
            set(sub_view.keys())
            - set(self.store._submissions[self.sub["id"]].keys()),
            {"awarded"})

    def test_no_banned_keys_anywhere(self):
        """Privacy: a recursive scan over every stored record, view,
        and the report finds no score/content/person field."""
        everything = [
            self.org, self.participant,
            list(self.store._contracts.values()),
            list(self.store._modifications.values()),
            list(self.store._requirements.values()),
            list(self.store._protests.values()),
            list(self.store._datacalls.values()),
            list(self.store._risks.values()),
            list(self.store._communications.values()),
            list(self.store._opportunities.values()),
            list(self.store._submissions.values()),
            list(self.store._awards.values()),
            list(self.store._payments.values()),
            list(self.store._workflows.values()),
            list(self.store._integrations.values()),
            self.store.org_report(self.org["id"], H.MEMBER),
        ]
        _scan_no_banned(everything)

    def test_smuggled_kwargs_raise_type_error(self):
        """Privacy / SI-10: store signatures reject smuggled fields
        (a score on a risk, content on a communication, a stored
        status on a contract) with TypeError."""
        with self.assertRaises(TypeError):
            self.store.create_risk(
                self.org["id"], "RSK-X", "Label", H.MEMBER, score=5)
        with self.assertRaises(TypeError):
            self.store.create_contract(
                self.org["id"], "CON-X", "T", "CP", 100, 50, H.MEMBER,
                obligated_cents=50)
        with self.assertRaises(TypeError):
            self.store.record_submission(
                self.org["id"], self.opp["id"], "SUB-X",
                H.PARTICIPANT_REF, H.MEMBER, awarded=True)
        with self.assertRaises(TypeError):
            self.store.create_protest(
                self.org["id"], "PRO-X", "Label", "2027-01-01", H.MEMBER,
                contract_id=self.contract["id"], overdue=False)


if __name__ == "__main__":
    unittest.main()
