"""Templates tests.

Traces to: Core function -- Templates; contract for
``create_template/render_template/get_template/list_templates``.
"""

import unittest

from comm_helpers import OPERATOR, VIEWER, fresh_store
from comm.errors import NotFoundError, PermissionDenied, ValidationError


class TestTemplates(unittest.TestCase):
    """Core: Templates."""

    def setUp(self):
        self.store = fresh_store()
        self.tpl = self.store.create_template(
            "welcome", "Hi {name}", "Hello {name}, code {code}", OPERATOR
        )

    def test_create_shape(self):
        """Core: Templates. create_template returns tpl-1 with subject/body verbatim."""
        self.assertEqual(self.tpl["id"], "tpl-1")
        self.assertEqual(self.tpl["subject"], "Hi {name}")
        self.assertEqual(self.store.get_template("tpl-1", VIEWER)["name"], "welcome")
        self.assertEqual(len(self.store.list_templates(VIEWER)), 1)

    def test_render_substitutes_all(self):
        """Core: Templates. render_template substitutes every placeholder -> (subject, body)."""
        subject, body = self.store.render_template("tpl-1", {"name": "Dana", "code": "42"})
        self.assertEqual(subject, "Hi Dana")
        self.assertEqual(body, "Hello Dana, code 42")

    def test_render_missing_variable(self):
        """Core: Templates. Missing variable -> ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.render_template("tpl-1", {"name": "Dana"})

    def test_render_extra_variables_ignored(self):
        """Core: Templates. Extra variables are ignored."""
        subject, _ = self.store.render_template(
            "tpl-1", {"name": "Dana", "code": "1", "extra": "x"}
        )
        self.assertEqual(subject, "Hi Dana")

    def test_render_unknown_template(self):
        """Core: Templates. Unknown template -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.render_template("tpl-999", {})

    def test_viewer_cannot_write_empty_name_no_id(self):
        """Core: Templates / Access control. Viewer template_write denied; empty name ValidationError, no id consumed."""
        with self.assertRaises(PermissionDenied):
            self.store.create_template("x", "s", "b", VIEWER)
        with self.assertRaises(ValidationError):
            self.store.create_template("", "s", "b", OPERATOR)
        self.assertEqual(self.store.create_template("ok", "s", "b", OPERATOR)["id"], "tpl-2")


if __name__ == "__main__":
    unittest.main()
