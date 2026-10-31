"""Cross-cutting SI-10 input discipline: failed operations
consume no id and change nothing; and the scoring discipline --
no score / rating / health / posture / compliance-value key on
any view, recursively.
"""

import unittest

import sysadmin_helpers as H
from sysadmin.errors import ValidationError

FORBIDDEN_KEYS = {"score", "rating", "health", "health_score", "posture",
                  "compliance", "compliance_score", "risk", "risk_score",
                  "grade", "severity_score", "sla_met"}


def _scan(obj, path="$"):
    hits = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_KEYS:
                hits.append("%s.%s" % (path, key))
            hits.extend(_scan(value, "%s.%s" % (path, key)))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            hits.extend(_scan(value, "%s[%d]" % (path, i)))
    return hits


class TestStoreValidation(unittest.TestCase):
    def test_failed_create_consumes_no_id(self):
        store, org = H.make_store()
        with self.assertRaises(ValidationError):
            H.make_system(store, org, kind="hypervisor")
        system = H.make_system(store, org)
        self.assertEqual(system["id"], "sys-1")

    def test_failed_request_consumes_no_id_and_changes_nothing(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        with self.assertRaises(ValidationError):
            H.make_request(store, org, system, due_date="not-a-date")
        self.assertEqual(store.list_requests(H.MEMBER, org["id"]), [])
        request = H.make_request(store, org, system)
        self.assertEqual(request["id"], "req-1")

    def test_no_score_like_key_on_any_view(self):
        store, org = H.make_store()
        system, application = H.make_estate(store, org)
        request = H.make_request(store, org, system,
                                 application_id=application["id"])
        change = H.make_change(store, org, system)
        store.decide_change(H.STAFF, change["id"], True)
        control = H.make_control(store, org, system)
        views = [
            store.get_organization(H.MEMBER, org["id"]),
            store.get_system(H.MEMBER, system["id"]),
            store.get_application(H.MEMBER, application["id"]),
            store.get_request(H.MEMBER, request["id"],
                              as_of=H.AS_OF_AFTER_DUE),
            store.get_change(H.MEMBER, change["id"]),
            store.get_control(H.MEMBER, control["id"]),
            store.list_requests(H.MEMBER, org["id"]),
            store.organization_summary(H.MEMBER, org["id"]),
            store.search(H.MEMBER, "portal"),
        ]
        for view in views:
            self.assertEqual(_scan(view), [], view)


if __name__ == "__main__":
    unittest.main()
