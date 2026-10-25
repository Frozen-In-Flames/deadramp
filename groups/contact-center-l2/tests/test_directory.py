"""Directory tests: agents and contacts.

Traces to: Core function 1 -- Directory; contract for
``ContactStore.create_agent/create_contact/get_*/list_*``.
Design constraint traced here: a contact ``reference`` is an opaque
external reference string, never a real phone number.
"""

import unittest

from contact_helpers import ADMIN, OPERATOR, VIEWER, fresh_store, make_store
from contact.errors import NotFoundError, PermissionDenied, ValidationError


class TestAgents(unittest.TestCase):
    """Core 1: Directory -- agents."""

    def test_create_agent_shape_and_id(self):
        """Core 1: Directory. create_agent returns agt- id, name, skills, attributes, provenance."""
        store = fresh_store()
        agent = store.create_agent("Dana", OPERATOR, skills=["billing"], attributes={"team": "s"})
        self.assertEqual(agent["id"], "agt-1")
        self.assertEqual(agent["name"], "Dana")
        self.assertEqual(agent["skills"], ["billing"])
        self.assertEqual(agent["attributes"], {"team": "s"})
        self.assertEqual(agent["created_by"], "bob")

    def test_create_agent_defaults(self):
        """Core 1: Directory. skills/attributes default to [] and {}."""
        store = fresh_store()
        agent = store.create_agent("Dana", OPERATOR)
        self.assertEqual(agent["skills"], [])
        self.assertEqual(agent["attributes"], {})

    def test_get_and_list_agents(self):
        """Core 1: Directory. get_agent/list_agents return copies sorted by id; viewer may read."""
        store, agent, contact, queue = make_store()
        self.assertEqual(store.get_agent(agent["id"], VIEWER)["id"], agent["id"])
        self.assertEqual([a["id"] for a in store.list_agents(VIEWER)], [agent["id"]])
        with self.assertRaises(NotFoundError):
            store.get_agent("agt-999", VIEWER)

    def test_agent_copies_are_copies(self):
        """Core 1: Directory. Mutating a returned agent does not mutate the store."""
        store = fresh_store()
        agent = store.create_agent("Dana", OPERATOR, skills=["a"], attributes={"k": "v"})
        agent["skills"].append("hacked")
        agent["attributes"]["k"] = "hacked"
        again = store.get_agent(agent["id"], OPERATOR)
        self.assertEqual(again["skills"], ["a"])
        self.assertEqual(again["attributes"], {"k": "v"})

    def test_agent_validation_and_no_id_on_failure(self):
        """Core 1: Directory (SI-10). Empty name / bad skills / bad attributes -> ValidationError, no id consumed."""
        store = fresh_store()
        for kwargs in ({"name": ""}, {"name": "  "}):
            with self.assertRaises(ValidationError):
                store.create_agent(kwargs["name"], OPERATOR)
        with self.assertRaises(ValidationError):
            store.create_agent("Dana", OPERATOR, skills="billing")
        with self.assertRaises(ValidationError):
            store.create_agent("Dana", OPERATOR, skills=[""])
        with self.assertRaises(ValidationError):
            store.create_agent("Dana", OPERATOR, attributes=["not-a-dict"])
        agent = store.create_agent("Dana", OPERATOR)
        self.assertEqual(agent["id"], "agt-1")

    def test_viewer_cannot_create_agent(self):
        """Core 1/11: Directory/RBAC. Viewer create_agent -> PermissionDenied, no id consumed."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_agent("Dana", VIEWER)
        self.assertEqual(store.create_agent("Dana", OPERATOR)["id"], "agt-1")


class TestContacts(unittest.TestCase):
    """Core 1: Directory -- contacts."""

    def test_create_contact_shape_and_id(self):
        """Core 1: Directory. create_contact returns ct- id with opaque reference and attributes."""
        store = fresh_store()
        contact = store.create_contact("Casey", OPERATOR, reference="EXT-9", attributes={"lang": "en"})
        self.assertEqual(contact["id"], "ct-1")
        self.assertEqual(contact["reference"], "EXT-9")
        self.assertEqual(contact["attributes"], {"lang": "en"})
        self.assertEqual(contact["created_by"], "bob")

    def test_create_contact_defaults(self):
        """Core 1: Directory. reference defaults to None, attributes to {}."""
        store = fresh_store()
        contact = store.create_contact("Casey", OPERATOR)
        self.assertIsNone(contact["reference"])
        self.assertEqual(contact["attributes"], {})

    def test_get_and_list_contacts(self):
        """Core 1: Directory. get_contact/list_contacts work for viewer; unknown id -> NotFoundError."""
        store, agent, contact, queue = make_store()
        self.assertEqual(store.get_contact(contact["id"], VIEWER)["id"], contact["id"])
        self.assertEqual([c["id"] for c in store.list_contacts(VIEWER)], [contact["id"]])
        with self.assertRaises(NotFoundError):
            store.get_contact("ct-999", VIEWER)

    def test_contact_validation_and_no_id_on_failure(self):
        """Core 1: Directory (SI-10). Empty name / non-string reference / bad attributes -> ValidationError, no id consumed."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_contact("", OPERATOR)
        with self.assertRaises(ValidationError):
            store.create_contact("Casey", OPERATOR, reference=12345)
        with self.assertRaises(ValidationError):
            store.create_contact("Casey", OPERATOR, attributes="x")
        self.assertEqual(store.create_contact("Casey", OPERATOR)["id"], "ct-1")

    def test_contact_copies_are_copies(self):
        """Core 1: Directory. Mutating a returned contact's attributes does not mutate the store."""
        store = fresh_store()
        contact = store.create_contact("Casey", OPERATOR, attributes={"k": "v"})
        contact["attributes"]["k"] = "hacked"
        self.assertEqual(store.get_contact(contact["id"], OPERATOR)["attributes"], {"k": "v"})

    def test_viewer_cannot_create_contact(self):
        """Core 1/11: Directory/RBAC. Viewer create_contact -> PermissionDenied."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_contact("Casey", VIEWER)
        self.assertEqual(store.create_contact("Casey", ADMIN)["id"], "ct-1")


if __name__ == "__main__":
    unittest.main()
