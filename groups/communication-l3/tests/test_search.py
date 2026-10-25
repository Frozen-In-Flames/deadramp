"""Search tests.

Traces to: Core function -- Immutable records + search; contract for
``CommStore.search`` -- literal case-insensitive substring over
contacts (name + addresses), messages (subject + body), deliveries
(address); returns {contacts, messages, deliveries}.
"""

import unittest

from comm_helpers import OPERATOR, VIEWER, make_store
from comm.errors import PermissionDenied, ValidationError


class TestSearch(unittest.TestCase):
    """Core: Search."""

    def setUp(self):
        self.store, self.contact, self.group, self.channel = make_store()
        self.msg = self.store.compose_message(
            OPERATOR, subject="Quarterly Alert", body="Something happened",
            contact_ids=[self.contact["id"]], channel_kinds=["email"],
        )

    def test_search_contacts_by_name_and_address(self):
        """Core: Search. Contact matched by name substring and by address value, case-insensitive."""
        result = self.store.search("DANA", OPERATOR)
        self.assertEqual([c["id"] for c in result["contacts"]], [self.contact["id"]])
        result = self.store.search("example.com", OPERATOR)
        self.assertEqual([c["id"] for c in result["contacts"]], [self.contact["id"]])

    def test_search_messages_by_subject_and_body(self):
        """Core: Search. Message matched by subject and by body."""
        self.assertEqual(
            [m["id"] for m in self.store.search("quarterly", OPERATOR)["messages"]],
            [self.msg["id"]],
        )
        self.assertEqual(
            [m["id"] for m in self.store.search("HAPPENED", OPERATOR)["messages"]],
            [self.msg["id"]],
        )

    def test_search_deliveries_by_address(self):
        """Core: Search. Delivery matched by its address."""
        result = self.store.search("dana@example", OPERATOR)
        self.assertEqual(len(result["deliveries"]), 1)
        self.assertEqual(result["deliveries"][0]["message_id"], self.msg["id"])

    def test_search_no_match_and_shape(self):
        """Core: Search. No match -> empty lists under the three keys."""
        result = self.store.search("zzzz-nope", OPERATOR)
        self.assertEqual(result, {"contacts": [], "messages": [], "deliveries": []})

    def test_search_is_literal_not_regex(self):
        """Core: Search. Query is a literal substring, not a pattern."""
        result = self.store.search("d.*a", OPERATOR)
        self.assertEqual(result["contacts"], [])

    def test_search_validation(self):
        """Core: Search (SI-10). Non-string query -> ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.search(123, OPERATOR)


if __name__ == "__main__":
    unittest.main()
