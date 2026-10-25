"""Reporting tests.

Traces to: Core function 9 -- Reporting / sibling claim family
reporting; control family AU-6 (report_read is a read, not audit).
"""

import unittest

from cms_helpers import ADMIN, AUTHOR, EDITOR, PUBLISHER, VIEWER, drive_to_published, make_item, make_store


class TestReport(unittest.TestCase):
    """Core: Reporting (reporting)."""

    def test_empty_report(self):
        """Core: Report. A fresh store reports zero items/assets, all statuses at 0, 4 built-in types."""
        from cms_helpers import fresh_store
        report = fresh_store().registry_report(VIEWER)
        self.assertEqual(report["totals"]["items"], 0)
        self.assertEqual(report["totals"]["types"], 4)
        self.assertEqual(report["items_by_status"],
                         {"draft": 0, "in_review": 0, "approved": 0, "published": 0, "archived": 0})
        self.assertEqual(report["publish_records"], 0)

    def test_report_counts_from_state(self):
        """Core: Report. items_by_status/site/type, publish_records, assets_by_kind and totals are computed from registry state."""
        store, site, _ = make_store()
        i1 = make_item(store, site, slug="r-one")
        i2 = make_item(store, site, slug="r-two", type_id="ct-page")
        drive_to_published(store, i1)
        store.register_asset(EDITOR, site["id"], "a.png", "image", 1)
        store.register_asset(EDITOR, site["id"], "b.png", "image", 2)
        store.register_asset(EDITOR, site["id"], "c.pdf", "document", 3)
        store.create_tag(EDITOR, "T", "t-report")
        report = store.registry_report(ADMIN)
        self.assertEqual(report["items_by_status"]["published"], 1)
        self.assertEqual(report["items_by_status"]["draft"], 1)
        self.assertEqual(report["items_by_site"], {site["id"]: 2})
        self.assertEqual(report["items_by_type"], {"ct-article": 1, "ct-page": 1})
        self.assertEqual(report["publish_records"], 1)
        self.assertEqual(report["assets_by_kind"]["image"], 2)
        self.assertEqual(report["assets_by_kind"]["document"], 1)
        self.assertEqual(report["assets_by_kind"]["video"], 0)
        self.assertEqual(report["totals"]["sites"], 1)
        self.assertEqual(report["totals"]["items"], 2)
        self.assertEqual(report["totals"]["assets"], 3)
        self.assertEqual(report["totals"]["tags"], 1)
        self.assertEqual(report["totals"]["publish_records"], 1)

    def test_report_deterministic(self):
        """Core: Report. Repeated reports over unchanged state are identical, and readable by any role."""
        store, site, _ = make_store()
        make_item(store, site)
        self.assertEqual(store.registry_report(VIEWER), store.registry_report(PUBLISHER))


if __name__ == "__main__":
    unittest.main()
