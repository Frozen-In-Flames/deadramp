"""Finding-ingestion tests.

Traces to: UNION-SPEC Core function 2 (Finding ingestion — one at a
time, in bulk (JSON), or as CSV scan results; a batch is atomic: one
bad row rejects the whole batch, nothing is partially applied, no ids
are consumed); Implementation contract for ``cyber/store.py``
ingest_finding / ingest_findings / ingest_findings_csv; control
families RA-5 and SI-10 (input validation).
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
    sample_finding_item,
)
from cyber.errors import NotFoundError, PermissionDenied, ValidationError

FINDING_KEYS = {
    "id", "title", "severity", "asset_id", "source", "description",
    "cve", "control_ids", "status", "assignee", "score", "band",
    "created_by", "created_utc", "updated_utc",
}


def _parse_ts(ts):
    """Parse a contract UTC ISO-8601 timestamp (must not raise)."""
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def _fresh_asset_store():
    """A bare store holding exactly one (medium) asset, no findings."""
    store = fresh_store()
    asset = make_asset(store, criticality="medium")
    return store, asset


class TestIngestSingle(unittest.TestCase):
    """Core: Finding ingestion — ingest_finding shape and validation."""

    def test_single_finding_shape_and_provenance(self):
        """Core: Finding ingestion. Contract: the finding dict is {id,
        title, severity, asset_id, source, description, cve,
        control_ids, status, assignee, score, band, created_by,
        created_utc, updated_utc} with status "new" and assignee
        None."""
        store, asset, finding = make_store()
        self.assertEqual(set(finding.keys()), FINDING_KEYS)
        self.assertEqual(finding["id"], "find-1")
        self.assertEqual(finding["title"], "Unpatched OpenSSL")
        self.assertEqual(finding["severity"], "high")
        self.assertEqual(finding["asset_id"], asset["id"])
        self.assertEqual(finding["source"], "scanner")
        self.assertEqual(finding["status"], "new")
        self.assertIsNone(finding["assignee"])
        self.assertEqual(finding["created_by"], "bob")
        _parse_ts(finding["created_utc"])  # must not raise
        _parse_ts(finding["updated_utc"])  # must not raise

    def test_single_finding_score_and_band_come_from_score_finding(self):
        """Core: Finding ingestion / Risk scoring. Contract: score/band
        come from score_finding(severity, asset.criticality) — the
        fixture's high severity on a high-criticality asset scores
        4 * 1.5 = 6.0, band high."""
        store, asset, finding = make_store()
        self.assertEqual((finding["score"], finding["band"]), (6.0, "high"))

    def test_single_finding_defaults_cve_none_and_control_ids_empty(self):
        """Core: Finding ingestion. Contract: item defaults are
        description "", cve None, control_ids []."""
        store, asset, finding = make_store()
        self.assertEqual(finding["description"], "")
        self.assertIsNone(finding["cve"])
        self.assertEqual(finding["control_ids"], [])

    def test_single_finding_preserves_explicit_fields(self):
        """Core: Finding ingestion. Contract: description, cve and
        control_ids given in the item are stored on the finding."""
        store, asset = _fresh_asset_store()
        finding = ingest_sample_finding(
            store, asset["id"], description="heartbleed-class exposure",
            cve="CVE-2014-0160", control_ids=["RA-5", "SI-2"],
        )
        self.assertEqual(finding["description"], "heartbleed-class exposure")
        self.assertEqual(finding["cve"], "CVE-2014-0160")
        self.assertEqual(finding["control_ids"], ["RA-5", "SI-2"])

    def test_ingest_unknown_asset_is_validation_error(self):
        """Core: Finding ingestion. Contract: asset_id 'must name an
        existing asset, else ValidationError'."""
        store, asset = _fresh_asset_store()
        with self.assertRaises(ValidationError):
            ingest_sample_finding(store, "asset-999999")

    def test_ingest_bad_severity_is_validation_error(self):
        """Core: Finding ingestion. Contract: severity must be in
        SEVERITIES, else ValidationError."""
        store, asset = _fresh_asset_store()
        with self.assertRaises(ValidationError):
            ingest_sample_finding(store, asset["id"], severity="extreme")

    def test_ingest_bad_control_id_is_validation_error(self):
        """Core: Finding ingestion / Control mapping. Contract: each
        control_ids entry 'must be in CONTROL_IDS, else
        ValidationError'."""
        store, asset = _fresh_asset_store()
        with self.assertRaises(ValidationError):
            ingest_sample_finding(store, asset["id"],
                                  control_ids=["XX-99"])
        with self.assertRaises(ValidationError):
            ingest_sample_finding(store, asset["id"],
                                  control_ids=["RA-5", "nope"])

    def test_ingest_empty_title_and_empty_source_are_validation_errors(self):
        """Core: Finding ingestion. Contract: title and source are
        non-empty strings."""
        store, asset = _fresh_asset_store()
        with self.assertRaises(ValidationError):
            ingest_sample_finding(store, asset["id"], title="")
        with self.assertRaises(ValidationError):
            ingest_sample_finding(store, asset["id"], source="")

    def test_viewer_cannot_ingest(self):
        """Core: Finding ingestion + Access control. ingest_finding
        takes action ingest, which viewer lacks."""
        store, asset = _fresh_asset_store()
        with self.assertRaises(PermissionDenied):
            ingest_sample_finding(store, asset["id"], actor=VIEWER)

    def test_failed_ingest_consumes_no_id(self):
        """Core: Finding ingestion. Contract: 'a failed operation
        consumes no id' — after a rejected ingest, the next successful
        finding still takes find-1 and is the only finding stored."""
        store, asset = _fresh_asset_store()
        with self.assertRaises(ValidationError):
            ingest_sample_finding(store, asset["id"], severity="extreme")
        finding = ingest_sample_finding(store, asset["id"])
        self.assertEqual(finding["id"], "find-1")
        self.assertEqual(len(store.list_findings(actor=ANALYST)), 1)

    def test_get_finding_roundtrip_and_unknown_is_not_found(self):
        """Core: Finding ingestion. Contract: get_finding returns the
        finding dict; an unknown id raises NotFoundError."""
        store, asset, finding = make_store()
        got = store.get_finding(finding["id"], actor=VIEWER)
        self.assertEqual(got["id"], finding["id"])
        with self.assertRaises(NotFoundError):
            store.get_finding("find-999999", actor=ANALYST)


class TestIngestBulk(unittest.TestCase):
    """Core: Finding ingestion — ingest_findings bulk atomicity (SI-10)."""

    def test_bulk_ingest_creates_all_items_in_order(self):
        """Core: Finding ingestion. Contract: ingest_findings returns
        a list of finding dicts, ids sequential in item order."""
        store, asset = _fresh_asset_store()
        items = [
            sample_finding_item(asset["id"], title="bulk-%d" % i)
            for i in range(3)
        ]
        created = store.ingest_findings(items, actor=ANALYST)
        self.assertEqual(
            [f["id"] for f in created], ["find-1", "find-2", "find-3"]
        )
        self.assertEqual(
            [f["title"] for f in created], ["bulk-0", "bulk-1", "bulk-2"]
        )
        self.assertEqual(len(store.list_findings(actor=ANALYST)), 3)

    def test_empty_bulk_is_validation_error(self):
        """Core: Finding ingestion. Contract: 'An empty list raises
        ValidationError.'"""
        store, asset = _fresh_asset_store()
        with self.assertRaises(ValidationError):
            store.ingest_findings([], actor=ANALYST)

    def test_bulk_with_one_bad_item_creates_nothing(self):
        """Core: Finding ingestion (SI-10). Contract: '**Atomic**:
        every item is validated before any is created; on any error
        nothing is created' — a batch whose middle item has a bad
        severity stores zero findings."""
        store, asset = _fresh_asset_store()
        items = [
            sample_finding_item(asset["id"], title="good-1"),
            sample_finding_item(asset["id"], title="bad",
                                severity="extreme"),
            sample_finding_item(asset["id"], title="good-2"),
        ]
        with self.assertRaises(ValidationError):
            store.ingest_findings(items, actor=ANALYST)
        self.assertEqual(store.list_findings(actor=ANALYST), [])

    def test_bulk_with_unknown_asset_creates_nothing(self):
        """Core: Finding ingestion (SI-10). Atomicity also covers an
        item naming a nonexistent asset: the whole batch is rejected."""
        store, asset = _fresh_asset_store()
        items = [
            sample_finding_item(asset["id"], title="good"),
            sample_finding_item("asset-999999", title="orphan"),
        ]
        with self.assertRaises(ValidationError):
            store.ingest_findings(items, actor=ANALYST)
        self.assertEqual(store.list_findings(actor=ANALYST), [])

    def test_bulk_with_bad_control_id_creates_nothing(self):
        """Core: Finding ingestion (SI-10). Atomicity also covers an
        item with an unknown control id: the whole batch is
        rejected."""
        store, asset = _fresh_asset_store()
        items = [
            sample_finding_item(asset["id"], title="good"),
            sample_finding_item(asset["id"], title="bad-control",
                                control_ids=["ZZ-1"]),
        ]
        with self.assertRaises(ValidationError):
            store.ingest_findings(items, actor=ANALYST)
        self.assertEqual(store.list_findings(actor=ANALYST), [])

    def test_failed_bulk_consumes_no_ids(self):
        """Core: Finding ingestion. Contract: a rejected batch
        consumes no ids — the next successful ingest still starts at
        find-1."""
        store, asset = _fresh_asset_store()
        with self.assertRaises(ValidationError):
            store.ingest_findings(
                [sample_finding_item(asset["id"], severity="extreme")],
                actor=ANALYST,
            )
        finding = ingest_sample_finding(store, asset["id"])
        self.assertEqual(finding["id"], "find-1")

    def test_bulk_writes_exactly_one_audit_entry(self):
        """Core: Finding ingestion / Audit log. Contract: bulk ingest
        writes 'One audit entry finding_ingest with details {"count":
        n, "ids": [...]}' — not one entry per item."""
        from cyber.audit import AuditLog
        audit = AuditLog()
        store = fresh_store(audit=audit)
        asset = make_asset(store, criticality="medium")
        items = [
            sample_finding_item(asset["id"], title="b-%d" % i)
            for i in range(3)
        ]
        created = store.ingest_findings(items, actor=ANALYST)
        entries = [
            e for e in audit.entries() if e["action"] == "finding_ingest"
        ]
        self.assertEqual(len(entries), 1)
        self.assertEqual(
            entries[0]["details"],
            {"count": 3, "ids": [f["id"] for f in created]},
        )


CSV_HEADER = "title,severity,asset_id,source,description,cve,control_ids\n"


class TestIngestCsv(unittest.TestCase):
    """Core: Finding ingestion — ingest_findings_csv (RA-5 scan output)."""

    def test_csv_ingest_creates_findings(self):
        """Core: Finding ingestion. Contract: the CSV 'must have a
        header row naming at least title,severity,asset_id,source' and
        its rows go through the same validation as ingest_findings."""
        store, asset = _fresh_asset_store()
        text = (
            CSV_HEADER
            + "Weak TLS,medium,%s,nessus,old cipher,,\n" % asset["id"]
            + "Open port,low,%s,nessus,,,\n" % asset["id"]
        )
        created = store.ingest_findings_csv(text, actor=ANALYST)
        self.assertEqual([f["id"] for f in created], ["find-1", "find-2"])
        self.assertEqual(created[0]["title"], "Weak TLS")
        self.assertEqual(created[0]["description"], "old cipher")
        self.assertEqual(created[1]["severity"], "low")

    def test_csv_control_ids_cell_is_semicolon_separated(self):
        """Core: Finding ingestion / Control mapping. Contract: the
        control_ids column is 'a semicolon-separated list, empty cell
        = []'."""
        store, asset = _fresh_asset_store()
        text = (
            CSV_HEADER
            + "Mapped,high,%s,scanner,,,AC-2;RA-5;SI-2\n" % asset["id"]
            + "Unmapped,high,%s,scanner,,,\n" % asset["id"]
        )
        created = store.ingest_findings_csv(text, actor=ANALYST)
        self.assertEqual(created[0]["control_ids"], ["AC-2", "RA-5", "SI-2"])
        self.assertEqual(created[1]["control_ids"], [])

    def test_csv_cve_cell_is_preserved_and_empty_cve_is_unset(self):
        """Core: Finding ingestion. Contract: the optional cve column
        feeds the item's cve, whose JSON-ingest default is None; an
        empty CSV cell therefore leaves it unset (None, or the empty
        string where an implementation keeps the raw cell — the
        contract pins the empty-cell rule only for control_ids)."""
        store, asset = _fresh_asset_store()
        text = (
            CSV_HEADER
            + "With CVE,critical,%s,scanner,,CVE-2021-44228,\n"
            % asset["id"]
            + "No CVE,low,%s,scanner,,,\n" % asset["id"]
        )
        created = store.ingest_findings_csv(text, actor=ANALYST)
        self.assertEqual(created[0]["cve"], "CVE-2021-44228")
        self.assertIn(created[1]["cve"], (None, ""))

    def test_csv_missing_required_header_is_validation_error(self):
        """Core: Finding ingestion (SI-10). Malformed CSV: a header
        row missing a required column (here asset_id) is rejected
        with ValidationError and creates nothing."""
        store, asset = _fresh_asset_store()
        text = "title,severity,source\nWeak TLS,medium,nessus\n"
        with self.assertRaises(ValidationError):
            store.ingest_findings_csv(text, actor=ANALYST)
        self.assertEqual(store.list_findings(actor=ANALYST), [])

    def test_csv_with_a_bad_row_is_atomic(self):
        """Core: Finding ingestion (SI-10). Contract: CSV ingest has
        'the same atomicity' as bulk — one bad row (unknown asset)
        rejects the whole file, creates nothing, consumes no ids."""
        store, asset = _fresh_asset_store()
        text = (
            CSV_HEADER
            + "Good,high,%s,scanner,,,\n" % asset["id"]
            + "Bad,high,asset-999999,scanner,,,\n"
        )
        with self.assertRaises(ValidationError):
            store.ingest_findings_csv(text, actor=ANALYST)
        self.assertEqual(store.list_findings(actor=ANALYST), [])
        finding = ingest_sample_finding(store, asset["id"])
        self.assertEqual(finding["id"], "find-1")

    def test_csv_with_bad_severity_is_validation_error(self):
        """Core: Finding ingestion (SI-10). Malformed CSV content: a
        severity outside SEVERITIES is rejected with
        ValidationError."""
        store, asset = _fresh_asset_store()
        text = CSV_HEADER + "Bad,extreme,%s,scanner,,,\n" % asset["id"]
        with self.assertRaises(ValidationError):
            store.ingest_findings_csv(text, actor=ANALYST)
        self.assertEqual(store.list_findings(actor=ANALYST), [])

    def test_csv_with_bad_control_id_is_validation_error(self):
        """Core: Finding ingestion (SI-10). Malformed CSV content: a
        control id outside CONTROL_IDS is rejected with
        ValidationError."""
        store, asset = _fresh_asset_store()
        text = (
            CSV_HEADER
            + "Bad,high,%s,scanner,,,XX-99\n" % asset["id"]
        )
        with self.assertRaises(ValidationError):
            store.ingest_findings_csv(text, actor=ANALYST)
        self.assertEqual(store.list_findings(actor=ANALYST), [])


if __name__ == "__main__":
    unittest.main()
