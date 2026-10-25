"""Asset-inventory tests.

Traces to: UNION-SPEC Core function 1 (Asset inventory — a register of
assets with provenance; criticality changes recompute the scores of
that asset's findings); Implementation contract for ``cyber/store.py``
create_asset / get_asset / list_assets / update_asset; control
families CM-8 and RA-3.
"""

import unittest
from datetime import datetime

from cyber_helpers import (
    ANALYST,
    VIEWER,
    fresh_store,
    ingest_sample_finding,
    make_asset,
    make_store,
)
from cyber.errors import NotFoundError, PermissionDenied, ValidationError

ASSET_KEYS = {
    "id", "name", "kind", "owner", "criticality", "tags",
    "created_by", "created_utc", "updated_utc",
}


def _parse_ts(ts):
    """Parse a contract UTC ISO-8601 timestamp (must not raise)."""
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


class TestCreateAsset(unittest.TestCase):
    """Core: Asset inventory — create shape, provenance, validation."""

    def test_create_asset_shape_and_provenance(self):
        """Core: Asset inventory. Contract: create_asset returns {id,
        name, kind, owner, criticality, tags, created_by, created_utc,
        updated_utc}; created_by is the actor (provenance)."""
        store = fresh_store()
        asset = make_asset(store, tags=["edge", "prod"])
        self.assertEqual(set(asset.keys()), ASSET_KEYS)
        self.assertEqual(asset["id"], "asset-1")
        self.assertEqual(asset["name"], "core-server-01")
        self.assertEqual(asset["kind"], "server")
        self.assertEqual(asset["owner"], "it-ops")
        self.assertEqual(asset["criticality"], "high")
        self.assertEqual(asset["tags"], ["edge", "prod"])
        self.assertEqual(asset["created_by"], "bob")
        _parse_ts(asset["created_utc"])  # must not raise
        _parse_ts(asset["updated_utc"])  # must not raise

    def test_create_asset_tags_default_to_empty_list(self):
        """Core: Asset inventory. Contract: tags defaults to []."""
        store = fresh_store()
        asset = make_asset(store)
        self.assertEqual(asset["tags"], [])

    def test_asset_ids_are_sequential_with_asset_prefix(self):
        """Core: Asset inventory. Contract: 'Ids are sequential per
        object type with fixed prefixes (asset-, find-, risk-)'."""
        store = fresh_store()
        first = make_asset(store, name="a-1")
        second = make_asset(store, name="a-2")
        self.assertEqual((first["id"], second["id"]), ("asset-1", "asset-2"))

    def test_every_asset_kind_is_accepted(self):
        """Core: Asset inventory. Contract: kind in ASSET_KINDS
        (server, workstation, mobile, network, cloud, application,
        database, other)."""
        store = fresh_store()
        for kind in ("server", "workstation", "mobile", "network",
                     "cloud", "application", "database", "other"):
            with self.subTest(kind=kind):
                asset = make_asset(store, name="k-%s" % kind, kind=kind)
                self.assertEqual(asset["kind"], kind)

    def test_create_asset_rejects_empty_name_and_owner(self):
        """Core: Asset inventory. Contract: 'name and owner must be
        non-empty strings'."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            make_asset(store, name="")
        with self.assertRaises(ValidationError):
            make_asset(store, owner="")
        with self.assertRaises(ValidationError):
            make_asset(store, name=None)

    def test_create_asset_rejects_unknown_kind_and_criticality(self):
        """Core: Asset inventory. Contract: kind in ASSET_KINDS and
        criticality in CRITICALITIES, else ValidationError."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            make_asset(store, kind="toaster")
        with self.assertRaises(ValidationError):
            make_asset(store, criticality="extreme")

    def test_create_asset_rejects_non_list_or_non_string_tags(self):
        """Core: Asset inventory. Contract: 'tags a list of strings'."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            make_asset(store, tags="prod")
        with self.assertRaises(ValidationError):
            make_asset(store, tags=["ok", 7])

    def test_viewer_cannot_create_an_asset(self):
        """Core: Asset inventory + Access control. create_asset takes
        action manage_assets, which viewer lacks."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            make_asset(store, actor=VIEWER)

    def test_failed_create_consumes_no_id(self):
        """Core: Asset inventory. Contract: 'a failed operation
        consumes no id and changes nothing' — after a rejected create,
        the next successful create still takes asset-1."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            make_asset(store, kind="toaster")
        asset = make_asset(store)
        self.assertEqual(asset["id"], "asset-1")
        self.assertEqual(len(store.list_assets(actor=ANALYST)), 1)


class TestGetAndListAssets(unittest.TestCase):
    """Core: Asset inventory — get_asset / list_assets (action read)."""

    def test_get_asset_roundtrip_and_viewer_may_read(self):
        """Core: Asset inventory. Contract: get_asset(asset_id, actor)
        returns the asset dict; read is held by every role."""
        store, asset, finding = make_store()
        got = store.get_asset(asset["id"], actor=VIEWER)
        self.assertEqual(got["id"], asset["id"])
        self.assertEqual(got["name"], asset["name"])

    def test_get_unknown_asset_is_not_found(self):
        """Core: Asset inventory. Contract: get_asset on an unknown id
        raises NotFoundError."""
        store, asset, finding = make_store()
        with self.assertRaises(NotFoundError):
            store.get_asset("asset-999999", actor=ANALYST)

    def test_list_assets_is_in_id_order(self):
        """Core: Asset inventory. Contract: list_assets returns 'asset
        dicts in id order'."""
        store = fresh_store()
        ids = [make_asset(store, name="a-%d" % i)["id"] for i in range(3)]
        listed = store.list_assets(actor=ANALYST)
        self.assertEqual([a["id"] for a in listed], ids)

    def test_list_assets_q_matches_name_and_owner_case_insensitively(self):
        """Core: Asset inventory. Contract: list_assets q is 'a
        case-insensitive substring over name and owner'."""
        store = fresh_store()
        make_asset(store, name="Core-Server", owner="it-ops")
        make_asset(store, name="laptop-7", owner="Sec-Ops")
        make_asset(store, name="db-1", owner="data-team")
        by_name = store.list_assets(actor=ANALYST, q="core-server")
        self.assertEqual([a["name"] for a in by_name], ["Core-Server"])
        by_owner = store.list_assets(actor=ANALYST, q="SEC-OPS")
        self.assertEqual([a["name"] for a in by_owner], ["laptop-7"])
        self.assertEqual(store.list_assets(actor=ANALYST, q="zzz"), [])


class TestUpdateAsset(unittest.TestCase):
    """Core: Asset inventory — update_asset and rescoring (RA-3)."""

    def test_update_owner_and_tags(self):
        """Core: Asset inventory. Contract: update_asset returns the
        updated asset dict with the given fields changed."""
        store, asset, finding = make_store()
        updated = store.update_asset(
            asset["id"], actor=ANALYST, owner="sec-ops", tags=["prod"]
        )
        self.assertEqual(updated["owner"], "sec-ops")
        self.assertEqual(updated["tags"], ["prod"])
        self.assertEqual(updated["name"], asset["name"])
        self.assertEqual(
            store.get_asset(asset["id"], actor=ANALYST)["owner"], "sec-ops"
        )

    def test_update_requires_at_least_one_field(self):
        """Core: Asset inventory. Contract: update_asset — 'at least
        one field must be given'."""
        store, asset, finding = make_store()
        with self.assertRaises(ValidationError):
            store.update_asset(asset["id"], actor=ANALYST)

    def test_update_validates_values_as_create_does(self):
        """Core: Asset inventory. Contract: update values are
        'validated as in create_asset' (criticality in CRITICALITIES,
        owner non-empty, tags a list of strings)."""
        store, asset, finding = make_store()
        with self.assertRaises(ValidationError):
            store.update_asset(asset["id"], actor=ANALYST,
                               criticality="extreme")
        with self.assertRaises(ValidationError):
            store.update_asset(asset["id"], actor=ANALYST, owner="")
        with self.assertRaises(ValidationError):
            store.update_asset(asset["id"], actor=ANALYST, tags="prod")

    def test_update_unknown_asset_is_not_found(self):
        """Core: Asset inventory. Contract: update_asset on an unknown
        id raises NotFoundError."""
        store, asset, finding = make_store()
        with self.assertRaises(NotFoundError):
            store.update_asset("asset-999999", actor=ANALYST, owner="x")

    def test_viewer_cannot_update_an_asset(self):
        """Core: Asset inventory + Access control. update_asset takes
        action manage_assets, which viewer lacks."""
        store, asset, finding = make_store()
        with self.assertRaises(PermissionDenied):
            store.update_asset(asset["id"], actor=VIEWER, owner="sec-ops")

    def test_failed_update_changes_nothing(self):
        """Core: Asset inventory. Contract: 'Every method validates
        fully before mutating' — a rejected update leaves the stored
        asset untouched."""
        store, asset, finding = make_store()
        with self.assertRaises(ValidationError):
            store.update_asset(asset["id"], actor=ANALYST,
                               criticality="extreme")
        got = store.get_asset(asset["id"], actor=ANALYST)
        self.assertEqual(got["criticality"], "high")
        self.assertEqual(got["owner"], asset["owner"])

    def test_criticality_change_rescores_that_assets_findings(self):
        """Core: Asset inventory / Risk scoring. Contract (Core 1):
        'Criticality changes recompute the scores of that asset's
        findings' — a high-severity finding goes 4*1.0=4.0/medium on a
        medium asset to 4*2.0=8.0/critical when the asset becomes
        critical."""
        store = fresh_store()
        asset = make_asset(store, criticality="medium")
        finding = ingest_sample_finding(store, asset["id"], severity="high")
        self.assertEqual((finding["score"], finding["band"]), (4.0, "medium"))
        store.update_asset(asset["id"], actor=ANALYST, criticality="critical")
        rescored = store.get_finding(finding["id"], actor=ANALYST)
        self.assertEqual((rescored["score"], rescored["band"]), (8.0, "critical"))

    def test_criticality_change_leaves_other_assets_findings_alone(self):
        """Core: Asset inventory / Risk scoring. Contract: rescoring
        applies to 'that asset's findings' — findings on other assets
        keep their score and band."""
        store = fresh_store()
        first = make_asset(store, name="first", criticality="medium")
        second = make_asset(store, name="second", criticality="medium")
        mine = ingest_sample_finding(store, first["id"], severity="high")
        theirs = ingest_sample_finding(store, second["id"], severity="high")
        store.update_asset(first["id"], actor=ANALYST, criticality="critical")
        self.assertEqual(
            store.get_finding(theirs["id"], actor=ANALYST)["score"], 4.0
        )
        self.assertEqual(
            store.get_finding(mine["id"], actor=ANALYST)["score"], 8.0
        )


if __name__ == "__main__":
    unittest.main()
