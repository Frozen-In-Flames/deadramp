"""Final GAPS batch, second unit — Communication L2 addition tests.

Traces to: GAPS.md section "Remainder Addition — Communication
L2 (+1 fork)" (1 entry, idx 657), gaps-batch/DECISION.md,
PLATFORM-LAYER.md, groups/communication-l2/ADDENDUM.md section 5.
Pins the addition extension surface: the marketing automation &
citizen-engagement campaign engine as a labeled reference
implementation (definitions as data + reported outcomes), the
no-content discipline, derived-never-stored shapes, and the
latest-label seam (the unit's fresh negative control).
"""

import inspect
import os
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from comm_helpers import ADMIN, OPERATOR, VIEWER, make_store  # noqa: E402
from comm.errors import NotFoundError, PermissionDenied, ValidationError  # noqa: E402
from comm.extensions_addition import CommExtensionsAddition, _latest_label  # noqa: E402

FORBIDDEN_KEYS = ("content", "body", "subject", "payload", "message_text",
                  "segment_members", "audience_members", "targeted_contact_ids",
                  "member_contact_ids", "score")
FORBIDDEN_PARAMS = ("content", "body", "subject", "payload", "message_text",
                    "document", "audience", "members")


def make_ext():
    store, contact, group, channel = make_store()
    return CommExtensionsAddition(store), store, contact, group


def scan_keys(obj, found=None):
    if found is None:
        found = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.add(k)
            scan_keys(v, found)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            scan_keys(v, found)
    return found


class TestCampaignReference(unittest.TestCase):
    """idx 657 — re-judged reference: definitions + reported outcomes."""

    def test_campaign_definition_is_labeled_reference_data(self):
        ext, store, contact, group = make_ext()
        camp = ext.define_campaign("camp-2026-census", "Census outreach",
                                   OPERATOR, channel_kinds=["email", "sms"])
        self.assertTrue(camp["id"].startswith("mcam-"))
        self.assertTrue(camp["reference_stub"])
        self.assertTrue(camp["reference_transport"])
        self.assertFalse(camp["executed_here"])
        self.assertFalse(camp["targeted_here"])
        self.assertFalse(camp["segmented_here"])
        self.assertFalse(camp["sent_here"])
        self.assertFalse(camp["transmitted_here"])
        self.assertFalse(camp["content_held"])
        self.assertEqual(camp["channel_kinds"], ["email", "sms"])
        self.assertIsNone(camp["template_id"])

    def test_campaign_definition_binds_template_by_id_only(self):
        ext, store, contact, group = make_ext()
        tpl = store.create_template("outreach", "Hello {name}", "Body {name}",
                                    OPERATOR)
        camp = ext.define_campaign("camp-tpl", "Templated", OPERATOR,
                                   template_id=tpl["id"])
        self.assertEqual(camp["template_id"], tpl["id"])
        keys = scan_keys(camp)
        self.assertNotIn("subject", keys)
        self.assertNotIn("body", keys)
        with self.assertRaises(NotFoundError):
            ext.define_campaign("camp-bad", "Bad", OPERATOR, template_id="tpl-999")

    def test_campaign_definition_validation_and_uniqueness(self):
        ext, store, contact, group = make_ext()
        ext.define_campaign("camp-1", "One", OPERATOR)
        with self.assertRaises(ValidationError):
            ext.define_campaign("camp-1", "Duplicate", OPERATOR)
        with self.assertRaises(ValidationError):
            ext.define_campaign("camp-2", "Bad kind", OPERATOR,
                                channel_kinds=["carrier_pigeon"])
        with self.assertRaises(ValidationError):
            ext.define_campaign("", "Empty ref", OPERATOR)
        # Failed definitions consumed no id: the next good one is mcam-2.
        nxt = ext.define_campaign("camp-3", "Three", OPERATOR)
        self.assertEqual(nxt["id"], "mcam-2")

    def test_segment_definition_records_groups_without_resolving(self):
        ext, store, contact, group = make_ext()
        seg = ext.define_audience_segment("seg-team", "Team audience", OPERATOR,
                                          group_ids=[group["id"]],
                                          criterion_refs=["crit-region-north"])
        self.assertTrue(seg["id"].startswith("mseg-"))
        self.assertTrue(seg["reference_stub"])
        self.assertFalse(seg["audience_computed"])
        self.assertFalse(seg["targeted_here"])
        view = ext.segment_view(seg["id"], OPERATOR)
        self.assertEqual(view["definition"]["group_ids"], [group["id"]])
        self.assertFalse(view["audience_computed"])
        keys = scan_keys(view) | scan_keys(seg)
        for bad in FORBIDDEN_KEYS:
            self.assertNotIn(bad, keys)
        with self.assertRaises(NotFoundError):
            ext.define_audience_segment("seg-bad", "Bad", OPERATOR,
                                        group_ids=["grp-999"])

    def test_outcome_records_hold_reported_figures_verbatim(self):
        ext, store, contact, group = make_ext()
        camp = ext.define_campaign("camp-1", "One", OPERATOR)
        rep = ext.record_campaign_outcome(camp["id"], "reported_launched",
                                          OPERATOR, messages_reported=120,
                                          deliveries_reported=118)
        self.assertTrue(rep["id"].startswith("mrep-"))
        self.assertTrue(rep["reference_stub"])
        self.assertFalse(rep["measured_here"])
        self.assertFalse(rep["sent_here"])
        self.assertEqual(rep["figures_basis"], "reported_by_platform")
        self.assertEqual(rep["messages_reported"], 120)
        with self.assertRaises(ValidationError):
            ext.record_campaign_outcome(camp["id"], "bad", OPERATOR,
                                        messages_reported=1.5)
        with self.assertRaises(ValidationError):
            ext.record_campaign_outcome(camp["id"], "bad", OPERATOR,
                                        deliveries_reported=True)
        with self.assertRaises(ValidationError):
            ext.record_campaign_outcome(camp["id"], "bad", OPERATOR,
                                        messages_reported=-1)
        with self.assertRaises(NotFoundError):
            ext.record_campaign_outcome("mcam-999", "reported_x", OPERATOR)

    def test_outcome_view_derives_current_and_reported_totals(self):
        ext, store, contact, group = make_ext()
        camp = ext.define_campaign("camp-1", "One", OPERATOR)
        empty = ext.campaign_view(camp["id"], OPERATOR)
        self.assertEqual(empty["current_outcome"], "unreported")
        ext.record_campaign_outcome(camp["id"], "reported_launched", OPERATOR,
                                    messages_reported=10, deliveries_reported=9)
        ext.record_campaign_outcome(camp["id"], "reported_completed", OPERATOR,
                                    messages_reported=5, deliveries_reported=5)
        ext.record_campaign_outcome(camp["id"], "reported_archived", OPERATOR)
        view = ext.campaign_view(camp["id"], OPERATOR)
        self.assertEqual(view["current_outcome"], "reported_archived")
        self.assertEqual(view["outcome_count"], 3)
        self.assertEqual(view["total_messages_reported"], 15)
        self.assertEqual(view["total_deliveries_reported"], 14)
        self.assertEqual(view["outcomes_without_counts"], 1)
        self.assertEqual(view["totals_basis"], "sum_of_reported_counts")
        # Derived values are never stored on the definition record.
        stored = ext._campaigns[camp["id"]]
        self.assertNotIn("current_outcome", stored)
        self.assertNotIn("total_messages_reported", stored)
        self.assertNotIn("total_deliveries_reported", stored)

    def test_full_flow_changes_no_core_record(self):
        ext, store, contact, group = make_ext()
        msg = store.compose_message(OPERATOR, subject="S", body="B",
                                    contact_ids=[contact["id"]],
                                    channel_kinds=["email"])
        before_messages = store.list_messages(OPERATOR)
        before_deliveries = store.list_deliveries(actor=OPERATOR)
        camp = ext.define_campaign("camp-1", "One", OPERATOR)
        seg = ext.define_audience_segment("seg-1", "Seg", OPERATOR,
                                          group_ids=[group["id"]])
        ext.record_campaign_outcome(camp["id"], "reported_completed", OPERATOR,
                                    messages_reported=3, deliveries_reported=3)
        ext.campaign_view(camp["id"], OPERATOR)
        self.assertEqual(store.list_messages(OPERATOR), before_messages)
        self.assertEqual(store.list_deliveries(actor=OPERATOR), before_deliveries)
        # The bound delivery was never dispatched by this surface.
        self.assertEqual(store.list_deliveries(actor=OPERATOR)[0]["status"], "queued")

    def test_viewer_denied_writes_and_failed_ops_consume_no_ids(self):
        ext, store, contact, group = make_ext()
        with self.assertRaises(PermissionDenied):
            ext.define_campaign("camp-v", "Viewer", VIEWER)
        with self.assertRaises(PermissionDenied):
            ext.define_audience_segment("seg-v", "Viewer", VIEWER)
        camp = ext.define_campaign("camp-1", "One", OPERATOR)
        self.assertEqual(camp["id"], "mcam-1")
        with self.assertRaises(PermissionDenied):
            ext.record_campaign_outcome(camp["id"], "reported_x", VIEWER)
        # Reads stay open to the viewer role (records_read), as in core.
        self.assertEqual(ext.campaign_view(camp["id"], VIEWER)["outcome_count"], 0)

    def test_no_content_signature_and_key_scan(self):
        ext, store, contact, group = make_ext()
        camp = ext.define_campaign("camp-1", "One", OPERATOR)
        with self.assertRaises(TypeError):
            ext.define_campaign("camp-x", "X", OPERATOR, content="hello")
        with self.assertRaises(TypeError):
            ext.define_campaign("camp-x", "X", OPERATOR, body="hello")
        with self.assertRaises(TypeError):
            ext.define_audience_segment("seg-x", "X", OPERATOR, payload="p")
        with self.assertRaises(TypeError):
            ext.record_campaign_outcome(camp["id"], "reported_x", OPERATOR,
                                        subject="s")
        for name in ("define_campaign", "define_audience_segment",
                     "record_campaign_outcome", "campaign_view", "segment_view"):
            params = set(inspect.signature(getattr(ext, name)).parameters)
            for bad in FORBIDDEN_PARAMS:
                self.assertNotIn(bad, params, "%s accepts %s" % (name, bad))
        seg = ext.define_audience_segment("seg-1", "Seg", OPERATOR,
                                          group_ids=[group["id"]])
        rep = ext.record_campaign_outcome(camp["id"], "reported_done", OPERATOR,
                                          messages_reported=1)
        everything = [camp, seg, rep, ext.campaign_view(camp["id"], OPERATOR),
                      ext.segment_view(seg["id"], OPERATOR),
                      ext.addition_campaign_summary(OPERATOR)]
        keys = set()
        for obj in everything:
            keys |= scan_keys(obj)
        for bad in FORBIDDEN_KEYS:
            self.assertNotIn(bad, keys)

    def test_summary_is_deterministic_counts(self):
        ext, store, contact, group = make_ext()
        self.assertEqual(ext.addition_campaign_summary(OPERATOR),
                         {"method": "deterministic_counts", "campaigns": 0,
                          "audience_segments": 0, "campaign_outcomes": 0})
        ext.define_campaign("camp-1", "One", OPERATOR)
        ext.define_audience_segment("seg-1", "Seg", OPERATOR)
        summary = ext.addition_campaign_summary(OPERATOR)
        self.assertEqual(summary["campaigns"], 1)
        self.assertEqual(summary["audience_segments"], 1)
        self.assertNotIn("score", scan_keys(summary))


class TestNegativeControlLatestLabelAddition(unittest.TestCase):
    """Fresh negative control: the latest-label seam.

    Canonical: a campaign's current reported outcome is its
    LATEST outcome record's label. The mutant (earliest record)
    would resurrect the superseded launch outcome on the view.
    """

    def _two_outcomes(self):
        ext, store, contact, group = make_ext()
        camp = ext.define_campaign("camp-1", "One", OPERATOR)
        ext.record_campaign_outcome(camp["id"], "reported_launched", OPERATOR)
        ext.record_campaign_outcome(camp["id"], "reported_completed", OPERATOR)
        return ext, camp

    def test_canonical_view_uses_latest_outcome(self):
        ext, camp = self._two_outcomes()
        view = ext.campaign_view(camp["id"], OPERATOR)
        self.assertEqual(view["current_outcome"], "reported_completed")

    def test_seam_directly(self):
        records = [{"outcome_label": "reported_launched"},
                   {"outcome_label": "reported_completed"}]
        self.assertEqual(_latest_label(records, "outcome_label"),
                         "reported_completed")
        self.assertIsNone(_latest_label([], "outcome_label"))
        # Treating the earliest (mutant) outcome as the expected
        # current outcome must fail:
        with self.assertRaises(AssertionError):
            self.assertEqual("reported_launched",
                             _latest_label(records, "outcome_label"))

    def test_mutant_earliest_differs(self):
        records = [{"outcome_label": "reported_launched"},
                   {"outcome_label": "reported_completed"}]

        def mutant_latest_label(recs, key):
            return recs[0][key] if recs else None

        self.assertNotEqual(mutant_latest_label(records, "outcome_label"),
                            _latest_label(records, "outcome_label"))
        # The literal canonical value, asserted against the real
        # implementation (trips under the live mutation by design):
        self.assertEqual(_latest_label(records, "outcome_label"),
                         "reported_completed")


if __name__ == "__main__":
    unittest.main()
