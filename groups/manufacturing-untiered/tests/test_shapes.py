"""Pinned record shapes and the no-score / no-money discipline.

Exact key sets for all three record types (the stored intent set
proves no stored ``status``; the intent view adds exactly the
derived ``status``). A recursive scan over a fully populated
store's public surface proves no forbidden key part exists
anywhere — nothing in this build can hold a score or a money
figure, because neither description grounds one.
"""

import unittest

import manufacturing_helpers as H

ORG_KEYS = {"id", "ref", "label", "created_by", "created_utc"}
INTENT_KEYS = {"id", "org_id", "label", "statement", "author_ref",
               "created_by", "created_utc"}
DECISION_KEYS = {"id", "org_id", "label", "statement",
                 "basis_intent_ids", "decided_by_ref", "decided_at",
                 "created_by", "created_utc"}

FORBIDDEN_KEY_PARTS = (
    "score", "grade", "rank", "rating", "rate", "email", "ssn",
    "password", "secret", "salary", "wage", "price", "fee",
    "amount", "cost", "budget",
)


def _scan_keys(obj, path="root"):
    if isinstance(obj, dict):
        for key, value in obj.items():
            for part in FORBIDDEN_KEY_PARTS:
                if part in key.lower():
                    raise AssertionError(
                        "forbidden key part %r in key %r at %s"
                        % (part, key, path))
            _scan_keys(value, "%s.%s" % (path, key))
    elif isinstance(obj, (list, tuple)):
        for i, value in enumerate(obj):
            _scan_keys(value, "%s[%d]" % (path, i))


class TestShapes(unittest.TestCase):
    def test_exact_key_sets(self):
        store, audit, org = H.make_store()
        self.assertEqual(set(org), ORG_KEYS)
        intent = H.make_intent(store, org)
        self.assertEqual(set(store._intents[intent["id"]]), INTENT_KEYS)
        self.assertEqual(set(intent), INTENT_KEYS | {"status"})
        decision = H.make_decision(store, org, intent)
        self.assertEqual(set(decision), DECISION_KEYS)

    def test_no_forbidden_key_anywhere(self):
        store, audit, org = H.make_store()
        intent = H.make_intent(store, org)
        H.make_decision(store, org, intent)
        surface = {
            "organizations": store.list_organizations(H.ADMIN),
            "intents": store.list_intents(H.ADMIN),
            "decisions": store.list_decisions(H.ADMIN),
            "search": store.search(H.ADMIN, "bracket"),
            "summary": store.summary(H.ADMIN),
            "audit": store.audit_read(H.ADMIN),
        }
        _scan_keys(surface)

    def test_summary_is_counts_only(self):
        store, audit, org = H.make_store()
        first = H.make_intent(store, org, label="One")
        H.make_intent(store, org, label="Two")
        H.make_decision(store, org, first)
        summary = store.summary(H.VIEWER)
        self.assertEqual(summary, {
            "organizations": 1,
            "intents": 2,
            "intents_by_status": {"open": 1, "transformed": 1},
            "decisions": 1,
        })


if __name__ == "__main__":
    unittest.main()
