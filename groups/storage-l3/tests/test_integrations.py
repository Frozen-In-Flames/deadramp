"""Core function 11: the integration registry -- records only.
Registering an integration connects nothing, authenticates no
one, and moves no message; the registry's whole surface is
create / list / deactivate over records.
"""

import unittest

from storage.errors import NotFoundError, ValidationError

from storage_helpers import ADMIN, OPERATOR, make_archive, make_store


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org, self.policy, self.collection = make_archive(self.store)

    def test_register_both_kinds(self):
        mail = self.store.create_integration(
            OPERATOR, self.org["id"], "mail_platform", "Mail platform link")
        directory = self.store.create_integration(
            OPERATOR, self.org["id"], "directory", "Directory link")
        self.assertEqual(mail["status"], "active")
        self.assertEqual(directory["kind"], "directory")
        by_kind = self.store.list_integrations(ADMIN, kind="mail_platform")
        self.assertEqual([i["id"] for i in by_kind], [mail["id"]])
        self.assertEqual(len(self.store.list_integrations(
            ADMIN, org_id=self.org["id"])), 2)

    def test_registry_has_no_execution_surface(self):
        # The registry records integrations; it performs none.
        for name in ("connect", "sync", "send", "fetch", "authenticate",
                     "run", "execute"):
            self.assertFalse(hasattr(self.store, "%s_integration" % name),
                             name)

    def test_deactivate(self):
        record = self.store.create_integration(
            OPERATOR, self.org["id"], "directory", "Directory link")
        done = self.store.deactivate_integration(OPERATOR, record["id"])
        self.assertEqual(done["status"], "inactive")
        with self.assertRaises(ValidationError):
            self.store.deactivate_integration(OPERATOR, record["id"])
        with self.assertRaises(NotFoundError):
            self.store.deactivate_integration(OPERATOR, "int-99")

    def test_validation(self):
        with self.assertRaises(ValidationError):
            self.store.create_integration(OPERATOR, self.org["id"],
                                          "tape_library", "x")
        with self.assertRaises(NotFoundError):
            self.store.create_integration(OPERATOR, "org-99", "directory",
                                          "x")
        self.assertEqual(self.store.list_integrations(ADMIN), [])


if __name__ == "__main__":
    unittest.main()
