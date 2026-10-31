"""Endpoints and routes (core functions 2 and 3): shapes,
uniqueness, cross-organization refusal, and the derived route
state."""

import unittest

from media_helpers import (ADMIN, OPERATOR, VIEWER, make_endpoints,
                           make_org, make_route, make_store)

from media.errors import NotFoundError, ValidationError


class EndpointTests(unittest.TestCase):
    def test_endpoint_shape_and_kinds(self):
        store, _audit = make_store()
        org = make_org(store)
        source, destination = make_endpoints(store, org)
        self.assertEqual(source["kind"], "agency_network")
        self.assertEqual(destination["kind"], "cloud_destination")
        self.assertEqual(
            set(source),
            {"id", "org_id", "ref", "label", "kind", "created_by",
             "created_utc"})

    def test_ref_unique_per_organization_only(self):
        store, _audit = make_store()
        org = make_org(store)
        other = store.create_organization(ADMIN, "ORG-0002", "Second")
        make_endpoints(store, org)
        with self.assertRaises(ValidationError):
            store.create_endpoint(OPERATOR, org["id"], "NET-HQ", "dup",
                                  "agency_network")
        twin = store.create_endpoint(OPERATOR, other["id"], "NET-HQ",
                                     "same ref, other org",
                                     "agency_network")
        self.assertEqual(twin["ref"], "NET-HQ")

    def test_ref_cannot_be_an_email_address(self):
        store, _audit = make_store()
        org = make_org(store)
        with self.assertRaises(ValidationError):
            store.create_endpoint(OPERATOR, org["id"], "a@b.example",
                                  "x", "agency_network")
        with self.assertRaises(ValidationError):
            store.create_endpoint(OPERATOR, org["id"], "has space",
                                  "x", "agency_network")

    def test_unknown_kind_and_unknown_org_refused(self):
        store, _audit = make_store()
        org = make_org(store)
        with self.assertRaises(ValidationError):
            store.create_endpoint(OPERATOR, org["id"], "NET-9", "x",
                                  "satellite")
        with self.assertRaises(NotFoundError):
            store.create_endpoint(OPERATOR, "org-99", "NET-9", "x",
                                  "agency_network")


class RouteTests(unittest.TestCase):
    def test_route_record_holds_labels_and_no_state_key(self):
        store, _audit = make_store()
        org = make_org(store)
        route, _s, _d = make_route(store, org)
        stored = store._routes[route["id"]]
        self.assertNotIn("state", stored)
        self.assertEqual(stored["encryption"], "aes_256")
        self.assertIsNone(stored["protocol_label"])
        self.assertEqual(route["state"], "idle")

    def test_route_state_is_derived_from_open_session(self):
        store, _audit = make_store()
        org = make_org(store)
        route, _s, _d = make_route(store, org)
        session = store.start_session(OPERATOR, route["id"])
        self.assertEqual(store.get_route(VIEWER, route["id"])["state"],
                         "live")
        store.stop_session(OPERATOR, session["id"])
        self.assertEqual(store.get_route(VIEWER, route["id"])["state"],
                         "idle")

    def test_route_requires_distinct_endpoints_of_one_org(self):
        store, _audit = make_store()
        org = make_org(store)
        other = store.create_organization(ADMIN, "ORG-0002", "Second")
        source, destination = make_endpoints(store, org)
        foreign, _fd = make_endpoints(store, other)
        with self.assertRaises(ValidationError):
            store.create_route(OPERATOR, org["id"], "same", source["id"],
                               source["id"])
        with self.assertRaises(ValidationError):
            store.create_route(OPERATOR, org["id"], "cross",
                               source["id"], foreign["id"])

    def test_encryption_label_vocabulary(self):
        store, _audit = make_store()
        org = make_org(store)
        source, destination = make_endpoints(store, org)
        with self.assertRaises(ValidationError):
            store.create_route(OPERATOR, org["id"], "bad", source["id"],
                               destination["id"], encryption="aes_128")
        plain = store.create_route(OPERATOR, org["id"], "plain",
                                   source["id"], destination["id"],
                                   encryption="none_stated",
                                   protocol_label="caller-stated")
        self.assertEqual(plain["encryption"], "none_stated")
        self.assertEqual(plain["protocol_label"], "caller-stated")

    def test_list_routes_filters_by_derived_state(self):
        store, _audit = make_store()
        org = make_org(store)
        route, _s, _d = make_route(store, org)
        self.assertEqual(
            [r["id"] for r in store.list_routes(ADMIN, state="idle")],
            [route["id"]])
        self.assertEqual(store.list_routes(ADMIN, state="live"), [])
        with self.assertRaises(ValidationError):
            store.list_routes(ADMIN, state="degraded")


if __name__ == "__main__":
    unittest.main()
