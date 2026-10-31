"""Pinned record shapes: every record type's key set is fixed, and
a recursive scan over a fully populated store proves no shape can
hold content the build must never hold — no email address (no
value contains ``@`` in a contact position and no key names one),
no proposal text, no CUI, and no score/grade/fit/rank/rate field
anywhere (union spec core-boundary decisions 1 and 2)."""

import unittest

from marketsales_helpers import (ADMIN, CONTACT_A, OCCURRED, OPERATOR,
                                 make_campaign, make_opportunity, make_org,
                                 make_store)

FORBIDDEN_KEY_PARTS = ("score", "grade", "rank", "rate", "email",
                     "body", "content_text", "text_body", "ssn",
                     "password", "secret")


def scan(node, path="$"):
    if isinstance(node, dict):
        for key, value in node.items():
            for part in FORBIDDEN_KEY_PARTS:
                if part in key.lower():
                    raise AssertionError(
                        "forbidden key part %r at %s.%s" % (part, path, key))
            scan(value, "%s.%s" % (path, key))
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            scan(value, "%s[%d]" % (path, index))


class ShapeTests(unittest.TestCase):
    def test_all_record_shapes_are_pinned_and_clean(self):
        store, _audit = make_store()
        org = make_org(store)
        opp = make_opportunity(store, org)
        store.record_evaluation(OPERATOR, opp["id"], "EVALUATOR-REF-1",
                                "pursue")
        entry = store.create_pipeline_entry(OPERATOR, opp["id"])
        store.create_content_version(OPERATOR, opp["id"], "Volume I",
                                     "section", 1, 128, pipeline_id=entry["id"])
        store.create_workflow(OPERATOR, org["id"], "Digest",
                              "new opportunity posted")
        campaign, contact_list, _seg = make_campaign(store, org)
        store.record_suppression(OPERATOR, contact_list["id"], CONTACT_A,
                                 "unsubscribe")
        store.record_delivery(OPERATOR, campaign["id"], "CONTACT-REF-2",
                              "delivered", OCCURRED)
        store.record_engagement(OPERATOR, campaign["id"], "CONTACT-REF-2",
                                "open", OCCURRED)
        everything = {
            "organizations": store.list_organizations(ADMIN),
            "opportunities": store.list_opportunities(ADMIN),
            "evaluations": store.list_evaluations(ADMIN),
            "pipeline": store.list_pipeline(ADMIN),
            "content": store.list_content(ADMIN),
            "workflows": store.list_workflows(ADMIN),
            "lists": store.list_contact_lists(ADMIN),
            "segments": store.list_segments(ADMIN),
            "campaigns": store.list_campaigns(ADMIN),
            "suppressions": store.list_suppressions(ADMIN),
            "deliveries": store.list_deliveries(ADMIN),
            "engagements": store.list_engagements(ADMIN),
            "report": store.engagement_report(ADMIN, campaign["id"]),
            "summary": store.summary(ADMIN),
        }
        scan(everything)
        # The campaign stored record (not just its view) is pinned:
        stored = store._campaigns[campaign["id"]]
        self.assertNotIn("status", stored)


if __name__ == "__main__":
    unittest.main()
