"""Queue tests.

Traces to: Core function 2 -- Queues; contract for
``ContactStore.create_queue/add_agent_to_queue/list_queues/
list_queue_members``.
"""

import unittest

from contact_helpers import OPERATOR, VIEWER, fresh_store, make_store
from contact.errors import NotFoundError, PermissionDenied, ValidationError


class TestQueues(unittest.TestCase):
    """Core 2: Queues."""

    def test_create_queue_shape_and_id(self):
        """Core 2: Queues. create_queue returns que- id, empty members, provenance."""
        store = fresh_store()
        queue = store.create_queue("support", OPERATOR)
        self.assertEqual(queue["id"], "que-1")
        self.assertEqual(queue["name"], "support")
        self.assertEqual(queue["members"], [])
        self.assertEqual(queue["created_by"], "bob")

    def test_add_agent_and_list_members(self):
        """Core 2: Queues. add_agent_to_queue appends; list_queue_members returns agent dicts."""
        store, agent, contact, queue = make_store()
        self.assertEqual(store.get_queue(queue["id"], VIEWER)["members"], [agent["id"]])
        members = store.list_queue_members(queue["id"], VIEWER)
        self.assertEqual([m["id"] for m in members], [agent["id"]])
        self.assertEqual(members[0]["name"], agent["name"])

    def test_duplicate_membership_validation(self):
        """Core 2: Queues. Duplicate membership -> ValidationError."""
        store, agent, contact, queue = make_store()
        with self.assertRaises(ValidationError):
            store.add_agent_to_queue(queue["id"], agent["id"], OPERATOR)

    def test_unknown_ids_not_found(self):
        """Core 2: Queues. Unknown queue/agent ids -> NotFoundError."""
        store, agent, contact, queue = make_store()
        with self.assertRaises(NotFoundError):
            store.add_agent_to_queue("que-999", agent["id"], OPERATOR)
        with self.assertRaises(NotFoundError):
            store.add_agent_to_queue(queue["id"], "agt-999", OPERATOR)
        with self.assertRaises(NotFoundError):
            store.list_queue_members("que-999", OPERATOR)

    def test_list_queues_and_validation(self):
        """Core 2: Queues (SI-10). list_queues in creation order; empty name -> ValidationError, no id consumed."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_queue("", OPERATOR)
        q1 = store.create_queue("a", OPERATOR)
        q2 = store.create_queue("b", OPERATOR)
        self.assertEqual((q1["id"], q2["id"]), ("que-1", "que-2"))
        self.assertEqual([q["id"] for q in store.list_queues(VIEWER)], ["que-1", "que-2"])

    def test_viewer_cannot_write_queue(self):
        """Core 2/11: Queues/RBAC. Viewer create/add -> PermissionDenied."""
        store, agent, contact, queue = make_store()
        with self.assertRaises(PermissionDenied):
            store.create_queue("x", VIEWER)
        agent2 = store.create_agent("Eve", OPERATOR)
        with self.assertRaises(PermissionDenied):
            store.add_agent_to_queue(queue["id"], agent2["id"], VIEWER)

    def test_queue_copies_are_copies(self):
        """Core 2: Queues. Mutating a returned queue's members does not mutate the store."""
        store, agent, contact, queue = make_store()
        queue["members"].append("agt-999")
        self.assertEqual(store.get_queue(queue["id"], OPERATOR)["members"], [agent["id"]])


if __name__ == "__main__":
    unittest.main()
