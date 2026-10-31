"""Optimization profiles (core function 7): settings stored
verbatim, never executed; toggling applies nothing."""

import unittest

from media_helpers import (ADMIN, OPERATOR, PROFILE_LABEL,
                           PROFILE_SETTINGS, make_org, make_route,
                           make_store)

import media.store as store_module

from media.errors import ValidationError


class ProfileTests(unittest.TestCase):
    def test_profile_shape_and_verbatim_settings(self):
        store, _audit = make_store()
        org = make_org(store)
        route, _s, _d = make_route(store, org)
        profile = store.create_optimization_profile(
            OPERATOR, org["id"], PROFILE_LABEL, PROFILE_SETTINGS,
            route_id=route["id"])
        self.assertEqual(profile["settings_text"], PROFILE_SETTINGS)
        self.assertTrue(profile["enabled"])
        self.assertEqual(profile["route_id"], route["id"])

    def test_profile_route_must_share_the_org(self):
        store, _audit = make_store()
        org = make_org(store)
        other = store.create_organization(ADMIN, "ORG-0002", "Second")
        foreign_route, _s, _d = make_route(store, other)
        with self.assertRaises(ValidationError):
            store.create_optimization_profile(
                OPERATOR, org["id"], PROFILE_LABEL, PROFILE_SETTINGS,
                route_id=foreign_route["id"])

    def test_enabled_must_be_a_boolean(self):
        store, _audit = make_store()
        org = make_org(store)
        with self.assertRaises(ValidationError):
            store.create_optimization_profile(
                OPERATOR, org["id"], PROFILE_LABEL, PROFILE_SETTINGS,
                enabled="yes")
        profile = store.create_optimization_profile(
            OPERATOR, org["id"], PROFILE_LABEL, PROFILE_SETTINGS)
        with self.assertRaises(ValidationError):
            store.set_profile_enabled(OPERATOR, profile["id"], 1)

    def test_toggling_applies_nothing(self):
        """Flipping the enabled flag changes only the profile
        record: no route state moves, no session appears."""
        store, _audit = make_store()
        org = make_org(store)
        route, _s, _d = make_route(store, org)
        profile = store.create_optimization_profile(
            OPERATOR, org["id"], PROFILE_LABEL, PROFILE_SETTINGS,
            route_id=route["id"])
        store.set_profile_enabled(OPERATOR, profile["id"], False)
        self.assertEqual(store.get_route(ADMIN, route["id"])["state"],
                         "idle")
        self.assertEqual(store.list_sessions(ADMIN), [])
        self.assertEqual(store.summary(ADMIN)["profiles_enabled"], 0)

    def test_no_execution_entry_point_exists(self):
        store, _audit = make_store()
        for name in ("execute_profile", "apply_profile", "run_profile",
                     "execute", "apply_optimization"):
            self.assertFalse(hasattr(store, name), name)
            self.assertFalse(hasattr(store_module, name), name)


if __name__ == "__main__":
    unittest.main()
