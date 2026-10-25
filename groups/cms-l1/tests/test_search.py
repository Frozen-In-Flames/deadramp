"""Search tests.

Traces to: Core function 8 -- Search / sibling claim family
search_discovery; SI-10.
"""

import unittest

from cms_helpers import ADMIN, AUTHOR, EDITOR, VIEWER, make_item, make_store
from cms.errors import ValidationError


def _populated():
    """Core: Search -- fixture with searchable items/assets/sites/tags."""
    store, site, _ = make_store()
    tag = store.create_tag(EDITOR, "Election Guide", "election-guide")
    item = make_item(store, site, title="City Budget Explainer", slug="city-budget",
                     body="How the council spends money",
                     metadata={"topic": "finance"}, tag_ids=[tag["id"]])
    store.register_asset(EDITOR, site["id"], "budget-chart.png", "image", 10)
    return store, site, tag, item


class TestSearch(unittest.TestCase):
    """Core: Search (search_discovery)."""

    def test_search_items_by_title_slug_body_metadata(self):
        """Core: Search. Items match on title, slug, body and metadata values."""
        store, site, tag, item = _populated()
        for q in ("budget", "city-budget", "council spends", "finance"):
            with self.subTest(q=q):
                result = store.search(VIEWER, q)
                self.assertEqual([i["id"] for i in result["items"]], [item["id"]])

    def test_search_assets_sites_tags(self):
        """Core: Search. Assets match filename/kind, sites name/slug, tags name/slug; result keys are items/assets/sites/tags."""
        store, site, tag, item = _populated()
        result = store.search(ADMIN, "budget-chart")
        self.assertEqual(set(result.keys()), {"items", "assets", "sites", "tags"})
        self.assertEqual(len(result["assets"]), 1)
        self.assertEqual([s["id"] for s in store.search(ADMIN, "main site")["sites"]], [site["id"]])
        self.assertEqual([s["id"] for s in store.search(ADMIN, "main-site")["sites"]], [site["id"]])
        self.assertEqual([t["id"] for t in store.search(ADMIN, "election")["tags"]], [tag["id"]])
        self.assertEqual(len(store.search(ADMIN, "image")["assets"]), 1)

    def test_search_case_insensitive_and_literal(self):
        """Core: Search. Case-insensitive; regex metacharacters are literal and do not explode."""
        store, site, tag, item = _populated()
        self.assertEqual(len(store.search(EDITOR, "BUDGET")["items"]), 1)
        self.assertEqual(store.search(EDITOR, ".*")["items"], [])
        self.assertEqual(store.search(EDITOR, "budget+")["items"], [])

    def test_search_blank_and_non_string(self):
        """Core: Search (SI-10). Blank query -> all empty; non-string -> ValidationError."""
        store, site, tag, item = _populated()
        self.assertEqual(store.search(AUTHOR, "   "),
                         {"items": [], "assets": [], "sites": [], "tags": []})
        with self.assertRaises(ValidationError):
            store.search(AUTHOR, 42)


if __name__ == "__main__":
    unittest.main()
