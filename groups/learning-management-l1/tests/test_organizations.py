"""Organization registry & catalog visibility tests.

Traces to: Core function 15 (Organization & portal registry) --
organizations (``org-``): an opaque ``ref`` (unique), a label, and a
portal label; create_organization / get_organization /
list_organizations in ``lms/store.py``. organization_write is
admin-only and organization_read is a record read (Core function 13).
Also traces to: Core function 1 (a learner's optional ``org_ref``
must resolve to an existing organization's ref, else ValidationError)
and Core function 2 under boundary decision 6 (courses and content
items carry an owning organization and a visibility of
``organization`` or ``community``; for learner-role catalog reads a
learner sees community items plus their own organization's items --
an organization-visibility item of another organization, or any
organization item for an org-less learner, is excluded from lists and
a single get raises PermissionDenied; admin/instructor/auditor are
unrestricted). Control families: AC-2, AC-3, AC-6, SI-10.
"""

import unittest

from lms_helpers import (
    ADMIN, AUDITOR, INSTRUCTOR, LEARNER, fresh_store, make_organization,
    make_store,
)
from lms.access import User
from lms.errors import NotFoundError, PermissionDenied, ValidationError

ERIN = User("erin", "learner")
FRANK = User("frank", "learner")

ORG_KEYS = {"id", "ref", "label", "portal_label", "created_by", "created_utc"}


def _visibility_store():
    """Store with two organizations and three learners.

    Organizations: "acme" and "beta". Learners: carol in acme,
    erin in beta, frank with no organization.
    """
    store = fresh_store()
    store.create_organization("acme", "Acme Health", ADMIN,
                              portal_label="Acme Portal")
    store.create_organization("beta", "Beta Health", ADMIN,
                              portal_label="Beta Portal")
    store.create_learner("carol", "Carol Learner", ADMIN, org_ref="acme")
    store.create_learner("erin", "Erin Learner", ADMIN, org_ref="beta")
    store.create_learner("frank", "Frank Learner", ADMIN)
    return store


class TestOrganizations(unittest.TestCase):
    """Core 15: organization registry records."""

    def test_create_organization_shape_and_ids(self):
        """Core 15: creation returns an org- record carrying exactly {id, ref, label, portal_label, created_by, created_utc}; ids are sequential; portal_label defaults to ''."""
        store = fresh_store()
        first = make_organization(store)
        second = store.create_organization("beta", "Beta Health", ADMIN)
        self.assertEqual(first["id"], "org-1")
        self.assertEqual(second["id"], "org-2")
        self.assertEqual(set(first), ORG_KEYS)
        self.assertEqual(first["ref"], "acme")
        self.assertEqual(first["label"], "Acme Health")
        self.assertEqual(first["portal_label"], "Acme Portal")
        self.assertEqual(second["portal_label"], "")
        self.assertEqual(first["created_by"], "alice")
        self.assertIn("created_utc", first)
        self.assertEqual(store.get_organization(first["id"], ADMIN), first)

    def test_duplicate_ref_rejected_no_id_consumed(self):
        """Core 15 / SI-10: a duplicate organization ref -> ValidationError, changes nothing, and consumes no id."""
        store = fresh_store()
        store.create_organization("acme", "Acme Health", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_organization("acme", "Acme Again", ADMIN)
        self.assertEqual(len(store.list_organizations(ADMIN)), 1)
        nxt = store.create_organization("beta", "Beta Health", ADMIN)
        self.assertEqual(nxt["id"], "org-2")

    def test_validation_empty_ref_or_label(self):
        """Core 15 / SI-10: empty/blank ref or label -> ValidationError; failed creates consume no id."""
        store = fresh_store()
        for ref, label in (("", "X"), ("  ", "X"), ("acme", ""), ("acme", "  ")):
            with self.subTest(ref=ref, label=label):
                with self.assertRaises(ValidationError):
                    store.create_organization(ref, label, ADMIN)
        org = store.create_organization("acme", "Acme Health", ADMIN)
        self.assertEqual(org["id"], "org-1")

    def test_organization_write_admin_only(self):
        """Core 15 / Core 13: organization_write is admin-only -- instructor, learner and auditor may not create organizations, but every role may read them."""
        store = fresh_store()
        for actor in (INSTRUCTOR, LEARNER, AUDITOR):
            with self.subTest(actor=actor.name):
                with self.assertRaises(PermissionDenied):
                    store.create_organization("acme", "Acme Health", actor)
        self.assertEqual(store.list_organizations(ADMIN), [])
        org = store.create_organization("acme", "Acme Health", ADMIN)
        for actor in (ADMIN, INSTRUCTOR, LEARNER, AUDITOR):
            with self.subTest(actor=actor.name):
                self.assertEqual(
                    store.get_organization(org["id"], actor)["ref"], "acme")

    def test_get_and_list(self):
        """Core 15: get returns the record; list returns all organizations sorted by id; an unknown id -> NotFoundError."""
        store = fresh_store()
        store.create_organization("beta", "Beta Health", ADMIN)
        acme = store.create_organization("acme", "Acme Health", ADMIN)
        self.assertEqual(store.get_organization(acme["id"], AUDITOR)["ref"],
                         "acme")
        self.assertEqual(store.get_organization(acme["id"])["label"],
                         "Acme Health")
        self.assertEqual(
            [o["id"] for o in store.list_organizations(INSTRUCTOR)],
            ["org-1", "org-2"],
        )
        with self.assertRaises(NotFoundError):
            store.get_organization("org-999", ADMIN)


class TestLearnerOrganizationResolution(unittest.TestCase):
    """Core 1 / decision 6: learner org_ref resolution."""

    def test_valid_org_ref_stored(self):
        """Core 1: a learner created with an org_ref that resolves to an existing organization's ref stores that org_ref; a learner without one stores None."""
        store, _, _ = make_store()
        org = make_organization(store)
        member = store.create_learner("erin", "Erin Learner", ADMIN,
                                      org_ref=org["ref"])
        self.assertEqual(member["org_ref"], "acme")
        plain = store.create_learner("frank", "Frank Learner", ADMIN)
        self.assertIsNone(plain["org_ref"])

    def test_unknown_org_ref_rejected(self):
        """Core 1 / SI-10: a learner created with an org_ref that resolves to no organization -> ValidationError, changes nothing, and consumes no id."""
        store = fresh_store()
        make_organization(store)
        with self.assertRaises(ValidationError):
            store.create_learner("carol", "Carol Learner", ADMIN,
                                 org_ref="ghost-org")
        self.assertEqual(store.list_learners(ADMIN), [])
        learner = store.create_learner("carol", "Carol Learner", ADMIN,
                                       org_ref="acme")
        self.assertEqual(learner["id"], "lrn-1")
        self.assertEqual(learner["org_ref"], "acme")


class TestCatalogVisibility(unittest.TestCase):
    """Core 2 / decision 6: catalog visibility enforcement for learners."""

    def _courses(self, store):
        acme_course = store.create_course(
            "Acme Only Course", ADMIN, org_ref="acme",
            visibility="organization")
        beta_course = store.create_course(
            "Beta Only Course", ADMIN, org_ref="beta",
            visibility="organization")
        community = store.create_course("Community Course", ADMIN)
        return acme_course, beta_course, community

    def test_course_visibility_for_learners(self):
        """Decision 6: an organization-visibility course is invisible to a learner of another org and to an org-less learner (list excludes it; single get raises PermissionDenied) and visible to a same-org learner; a community course is visible to all learners."""
        store = _visibility_store()
        acme_course, beta_course, community = self._courses(store)

        carol_ids = [c["id"] for c in store.list_courses(LEARNER)]
        self.assertEqual(carol_ids, [acme_course["id"], community["id"]])
        self.assertEqual(store.get_course(acme_course["id"], LEARNER)["id"],
                         acme_course["id"])
        with self.assertRaises(PermissionDenied):
            store.get_course(beta_course["id"], LEARNER)

        erin_ids = [c["id"] for c in store.list_courses(ERIN)]
        self.assertEqual(erin_ids, [beta_course["id"], community["id"]])
        with self.assertRaises(PermissionDenied):
            store.get_course(acme_course["id"], ERIN)

        frank_ids = [c["id"] for c in store.list_courses(FRANK)]
        self.assertEqual(frank_ids, [community["id"]])
        with self.assertRaises(PermissionDenied):
            store.get_course(acme_course["id"], FRANK)
        self.assertEqual(store.get_course(community["id"], FRANK)["id"],
                         community["id"])

    def test_course_visibility_unrestricted_for_staff_roles(self):
        """Decision 6 / Core 13: admin, instructor and auditor are unrestricted -- they list and get organization-visibility courses of any organization."""
        store = _visibility_store()
        acme_course, beta_course, community = self._courses(store)
        for actor in (ADMIN, INSTRUCTOR, AUDITOR):
            with self.subTest(actor=actor.name):
                self.assertEqual(
                    [c["id"] for c in store.list_courses(actor)],
                    [acme_course["id"], beta_course["id"], community["id"]],
                )
                self.assertEqual(
                    store.get_course(beta_course["id"], actor)["id"],
                    beta_course["id"])

    def test_content_item_visibility_for_learners(self):
        """Decision 6: content items follow the same rule -- an organization-visibility item is excluded from another org's learner's list (and an org-less learner's list), present in a same-org learner's list, and a community item is visible to all learners."""
        store = _visibility_store()
        acme_item = store.create_content_item(
            "Acme Only Item", "pdf", ADMIN, org_ref="acme",
            visibility="organization")
        beta_item = store.create_content_item(
            "Beta Only Item", "pdf", ADMIN, org_ref="beta",
            visibility="organization")
        community = store.create_content_item("Community Item", "html", ADMIN)

        self.assertEqual(
            [i["id"] for i in store.list_content_items(LEARNER)],
            [acme_item["id"], community["id"]])
        self.assertEqual(
            [i["id"] for i in store.list_content_items(ERIN)],
            [beta_item["id"], community["id"]])
        self.assertEqual(
            [i["id"] for i in store.list_content_items(FRANK)],
            [community["id"]])
        with self.assertRaises(PermissionDenied):
            store.get_content_item(beta_item["id"], LEARNER)
        self.assertEqual(
            store.get_content_item(acme_item["id"], LEARNER)["id"],
            acme_item["id"])
        self.assertEqual(len(store.list_content_items(AUDITOR)), 3)

    def test_visibility_validation(self):
        """Decision 6 / SI-10: visibility='organization' without an org_ref -> ValidationError (course and content item); a bogus visibility -> ValidationError; an org_ref that resolves to no organization -> ValidationError; failed creates consume no id."""
        store = _visibility_store()
        with self.assertRaises(ValidationError):
            store.create_course("No Org", ADMIN, visibility="organization")
        with self.assertRaises(ValidationError):
            store.create_content_item("No Org", "pdf", ADMIN,
                                      visibility="organization")
        with self.assertRaises(ValidationError):
            store.create_course("Bogus", ADMIN, org_ref="acme",
                                visibility="private")
        with self.assertRaises(ValidationError):
            store.create_content_item("Bogus", "pdf", ADMIN, org_ref="acme",
                                      visibility="private")
        with self.assertRaises(ValidationError):
            store.create_course("Ghost Org", ADMIN, org_ref="ghost-org",
                                visibility="organization")
        with self.assertRaises(ValidationError):
            store.create_course("Ghost Org Community", ADMIN,
                                org_ref="ghost-org")
        course = store.create_course("Ok", ADMIN)
        self.assertEqual(course["id"], "crs-1")
        item = store.create_content_item("Ok", "pdf", ADMIN)
        self.assertEqual(item["id"], "cnt-1")


if __name__ == "__main__":
    unittest.main()
