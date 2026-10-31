"""Usage records; usage export manifests.

Traces to: Core functions 9 (Usage records) and 10 (Usage export
manifests) in UNION-SPEC.md — a usage quantity must be a positive
integer (booleans, floats, and strings are rejected at the boundary,
SI-10); an export manifest carries the record count, the total
quantity, and a SHA-256 checksum of the canonical exported set
(records sorted by id, each reduced to {id, kind, quantity,
created_utc}, JSON with sorted keys), computed at export time.
Window filtering is on the records' created_utc in [since, until].
"""

import hashlib
import json
import unittest

import legalpol_helpers as H
from legalpol.errors import NotFoundError, PermissionDenied, ValidationError


def recompute_checksum(records):
    """Independent recomputation of the export checksum from the
    usage records themselves (test-side canonicalization)."""
    ordered = sorted(records, key=lambda r: int(r["id"].split("-", 1)[1]))
    canonical = [
        {"id": r["id"], "kind": r["kind"], "quantity": r["quantity"],
         "created_utc": r["created_utc"]}
        for r in ordered
    ]
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class UsageFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.agency = H.make_store()
        self.aid = self.agency["id"]
        self.workspace = H.make_workspace(self.store, self.agency)
        self.wid = self.workspace["id"]


class TestUsageRecords(UsageFixture):
    """Core 9: usage records and the quantity discipline."""

    def test_record_usage_shape(self):
        """Core 9: usage shape is pinned."""
        usage = self.store.record_usage(self.aid, "USE-REF-1", "search", 12,
                                        H.MEMBER, workspace_id=self.wid)
        self.assertEqual(set(usage.keys()), {
            "id", "agency_id", "workspace_id", "session_id", "usage_ref",
            "kind", "quantity", "created_by", "created_utc"})
        self.assertEqual(usage["id"], "use-1")
        self.assertIsNone(usage["session_id"])

    def test_usage_kinds(self):
        """Core 9: kinds are search/session/execution/document/
        inference/export."""
        for i, kind in enumerate(
                ("search", "session", "execution", "document",
                 "inference", "export")):
            usage = self.store.record_usage(self.aid, "USE-%d" % i, kind, 1,
                                            H.MEMBER)
            self.assertEqual(usage["kind"], kind)
        with self.assertRaises(ValidationError):
            self.store.record_usage(self.aid, "USE-X", "login", 1, H.MEMBER)

    def test_quantity_discipline(self):
        """Core 9 / SI-10: bool, float, string, zero, and negative
        quantities are all rejected; the store is unchanged."""
        for bad in (True, False, 1.5, 2.0, "3", 0, -4, None):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.store.record_usage(self.aid, "USE-BAD", "search", bad,
                                        H.MEMBER)
        self.assertEqual(self.store.list_usage(self.aid, H.MEMBER), [])
        usage = self.store.record_usage(self.aid, "USE-OK", "search", 1,
                                        H.MEMBER)
        self.assertEqual(usage["id"], "use-1")

    def test_usage_ref_unique_and_links_checked(self):
        """Core 9: usage_ref is unique within the agency; linked
        workspace/session ids must exist in this agency."""
        session = H.make_session(self.store, self.agency, self.workspace)
        usage = self.store.record_usage(
            self.aid, "USE-1", "session", 1, H.MEMBER,
            session_id=session["id"], workspace_id=self.wid)
        self.assertEqual(usage["session_id"], session["id"])
        with self.assertRaises(ValidationError):
            self.store.record_usage(self.aid, "USE-1", "search", 1, H.MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.record_usage(self.aid, "USE-2", "search", 1, H.MEMBER,
                                    workspace_id="wsp-999")
        with self.assertRaises(NotFoundError):
            self.store.record_usage(self.aid, "USE-3", "search", 1, H.MEMBER,
                                    session_id="ses-999")

    def test_list_usage_kind_filter_and_boundary(self):
        """Core 9: the kind filter is validated and applied; the
        viewer may read usage but not record it; outsiders denied."""
        self.store.record_usage(self.aid, "USE-1", "search", 3, H.MEMBER)
        self.store.record_usage(self.aid, "USE-2", "inference", 5, H.MEMBER)
        searches = self.store.list_usage(self.aid, H.VIEWER, kind="search")
        self.assertEqual([u["usage_ref"] for u in searches], ["USE-1"])
        with self.assertRaises(ValidationError):
            self.store.list_usage(self.aid, H.MEMBER, kind="login")
        with self.assertRaises(PermissionDenied):
            self.store.record_usage(self.aid, "USE-3", "search", 1, H.VIEWER)
        with self.assertRaises(PermissionDenied):
            self.store.list_usage(self.aid, H.OUTSIDER)


class TestUsageExports(UsageFixture):
    """Core 10: export manifests with checksums over the exported set."""

    def _seed_usage(self):
        first = self.store.record_usage(self.aid, "USE-1", "search", 3,
                                        H.MEMBER)
        second = self.store.record_usage(self.aid, "USE-2", "inference", 5,
                                         H.MEMBER)
        third = self.store.record_usage(self.aid, "USE-3", "search", 2,
                                        H.MEMBER)
        return [first, second, third]

    def test_export_shape_and_checksum(self):
        """Core 10: export shape is pinned, and the checksum is
        recomputed independently here from the usage records."""
        seeded = self._seed_usage()
        export = self.store.export_usage(self.aid, "EXP-REF-1", H.MEMBER)
        self.assertEqual(set(export.keys()), {
            "id", "agency_id", "export_ref", "since", "until",
            "record_count", "total_quantity", "checksum", "created_by",
            "created_utc"})
        self.assertEqual(export["id"], "exp-1")
        self.assertEqual(export["record_count"], 3)
        self.assertEqual(export["total_quantity"], 10)
        records = self.store.list_usage(self.aid, H.MEMBER)
        self.assertEqual(export["checksum"], recompute_checksum(records))
        self.assertEqual([r["id"] for r in records],
                         [r["id"] for r in seeded])

    def test_export_empty_set_checksum(self):
        """Core 10: an export over no records checksums the empty
        canonical set and totals zero."""
        export = self.store.export_usage(self.aid, "EXP-EMPTY", H.MEMBER)
        self.assertEqual(export["record_count"], 0)
        self.assertEqual(export["total_quantity"], 0)
        self.assertEqual(export["checksum"], recompute_checksum([]))

    def test_export_window_filtering(self):
        """Core 10: [since, until] filters on created_utc, open-ended
        when a bound is None; bounds are inclusive."""
        seeded = self._seed_usage()
        stamps = [r["created_utc"] for r in seeded]
        windowed = self.store.export_usage(
            self.aid, "EXP-WIN", H.MEMBER,
            since=stamps[1], until=stamps[1])
        self.assertEqual(windowed["record_count"], 1)
        self.assertEqual(windowed["total_quantity"], 5)
        self.assertEqual(windowed["checksum"],
                         recompute_checksum([seeded[1]]))
        from_first = self.store.export_usage(
            self.aid, "EXP-FROM", H.MEMBER, since=stamps[0])
        self.assertEqual(from_first["record_count"], 3)
        past = self.store.export_usage(
            self.aid, "EXP-PAST", H.MEMBER, until="2000-01-01T00:00:00+00:00")
        self.assertEqual(past["record_count"], 0)
        with self.assertRaises(ValidationError):
            self.store.export_usage(self.aid, "EXP-BADWIN", H.MEMBER,
                                    since=stamps[2], until=stamps[0])
        with self.assertRaises(ValidationError):
            self.store.export_usage(self.aid, "EXP-BADTS", H.MEMBER,
                                    since="not-a-date")

    def test_export_ref_unique_and_permissions(self):
        """Core 10 / AC: export_ref is unique within the agency; the
        export action is held by member and admin but not viewer;
        outsiders are denied."""
        self.store.export_usage(self.aid, "EXP-1", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.export_usage(self.aid, "EXP-1", H.MEMBER)
        with self.assertRaises(PermissionDenied):
            self.store.export_usage(self.aid, "EXP-2", H.VIEWER)
        with self.assertRaises(PermissionDenied):
            self.store.export_usage(self.aid, "EXP-3", H.OUTSIDER)
        exports = self.store.list_exports(self.aid, H.VIEWER)
        self.assertEqual([e["export_ref"] for e in exports], ["EXP-1"])


if __name__ == "__main__":
    unittest.main()
