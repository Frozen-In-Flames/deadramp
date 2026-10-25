"""Model & prompt-template registry tests.

Traces to: UNION-SPEC Core function 1 (Model registry) and Core
function 2 (Prompt template registry); Implementation contract for
``register_model`` / ``get_model`` / ``list_models`` /
``set_model_status`` / ``register_template`` / ``get_template`` /
``list_templates`` in ``aigateway/store.py``.
"""

import unittest

from aigateway_helpers import ADMIN, MEMBER, VIEWER, fresh_store
from aigateway.errors import NotFoundError, PermissionDenied, ValidationError


class TestModelRegistry(unittest.TestCase):
    """Core function 1: Model registry."""

    def setUp(self):
        self.store = fresh_store()

    def test_register_model_shape_and_provenance(self):
        """Core 1: register_model returns {id, name, version, provider,
        responder, capabilities, config, status, created_by,
        created_utc} with status starting 'active' and an mdl- id."""
        model = self.store.register_model(
            "echoer", "echo", ADMIN, provider="reference",
            capabilities=["text", "chat"],
        )
        self.assertEqual(
            set(model.keys()),
            {"id", "name", "version", "provider", "responder",
             "capabilities", "config", "status", "created_by", "created_utc"},
        )
        self.assertEqual(model["id"], "mdl-1")
        self.assertEqual(model["version"], 1)
        self.assertEqual(model["status"], "active")
        self.assertEqual(model["created_by"], "alice")
        self.assertEqual(model["capabilities"], ["text", "chat"])
        self.assertEqual(model["config"], {})

    def test_version_auto_increments_per_name(self):
        """Core 1: an omitted version is the next integer for that
        name (1 for the first); a different name restarts at 1."""
        first = self.store.register_model("m", "echo", ADMIN)
        second = self.store.register_model("m", "echo", ADMIN)
        other = self.store.register_model("n", "echo", ADMIN)
        self.assertEqual((first["version"], second["version"]), (1, 2))
        self.assertEqual(other["version"], 1)
        self.assertEqual(
            (first["id"], second["id"], other["id"]),
            ("mdl-1", "mdl-2", "mdl-3"),
        )

    def test_explicit_version_and_duplicate_rejected(self):
        """Core 1: an explicit duplicate (name, version) raises
        ValidationError; an explicit non-duplicate version is kept,
        and the next auto version follows the highest."""
        model = self.store.register_model("m", "echo", ADMIN, version=5)
        self.assertEqual(model["version"], 5)
        with self.assertRaises(ValidationError):
            self.store.register_model("m", "echo", ADMIN, version=5)
        nxt = self.store.register_model("m", "echo", ADMIN)
        self.assertEqual(nxt["version"], 6)

    def test_invalid_version_rejected(self):
        """Core 1 (SI-10): a non-positive or non-integer version
        raises ValidationError."""
        for bad in (0, -1, "2", 1.5, True):
            with self.subTest(version=bad):
                with self.assertRaises(ValidationError):
                    self.store.register_model("m", "echo", ADMIN, version=bad)

    def test_invalid_responder_rejected_and_no_id_consumed(self):
        """Core 1: responder must be echo|template|rules, else
        ValidationError; a failed registration consumes no id."""
        with self.assertRaises(ValidationError):
            self.store.register_model("m", "neural-net", ADMIN)
        model = self.store.register_model("m", "echo", ADMIN)
        self.assertEqual(model["id"], "mdl-1")

    def test_template_responder_requires_template_config(self):
        """Core 1: responder 'template' requires config["template"]
        to be a string."""
        with self.assertRaises(ValidationError):
            self.store.register_model("m", "template", ADMIN)
        with self.assertRaises(ValidationError):
            self.store.register_model("m", "template", ADMIN, config={})
        with self.assertRaises(ValidationError):
            self.store.register_model(
                "m", "template", ADMIN, config={"template": 42}
            )
        ok = self.store.register_model(
            "m", "template", ADMIN, config={"template": "T: {prompt}"}
        )
        self.assertEqual(ok["config"]["template"], "T: {prompt}")

    def test_rules_responder_config_validation(self):
        """Core 1: responder 'rules' requires config["rules"] as a
        list of {match, response} string pairs and config["default"]
        as a string."""
        with self.assertRaises(ValidationError):
            self.store.register_model("m", "rules", ADMIN, config={})
        with self.assertRaises(ValidationError):
            self.store.register_model(
                "m", "rules", ADMIN,
                config={"rules": "nope", "default": "d"},
            )
        with self.assertRaises(ValidationError):
            self.store.register_model(
                "m", "rules", ADMIN,
                config={"rules": [{"match": "a"}], "default": "d"},
            )
        with self.assertRaises(ValidationError):
            self.store.register_model(
                "m", "rules", ADMIN,
                config={"rules": [{"match": "a", "response": "b"}]},
            )
        ok = self.store.register_model(
            "m", "rules", ADMIN,
            config={"rules": [{"match": "a", "response": "b"}], "default": "d"},
        )
        self.assertEqual(ok["responder"], "rules")

    def test_get_model_latest_and_specific_version(self):
        """Core 1: get_model with version=None selects the highest
        version; an explicit version selects exactly it."""
        self.store.register_model("m", "echo", ADMIN)
        v2 = self.store.register_model("m", "template", ADMIN,
                                       config={"template": "x"})
        latest = self.store.get_model("m", MEMBER)
        self.assertEqual(latest["id"], v2["id"])
        self.assertEqual(latest["version"], 2)
        v1 = self.store.get_model("m", MEMBER, version=1)
        self.assertEqual(v1["responder"], "echo")

    def test_get_model_not_found(self):
        """Core 1: an absent model (or version) raises NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_model("ghost", MEMBER)
        self.store.register_model("m", "echo", ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.get_model("m", MEMBER, version=99)

    def test_list_models_sorted_by_name_and_version(self):
        """Core 1: list_models returns all models sorted by
        (name, version)."""
        self.store.register_model("zeta", "echo", ADMIN)
        self.store.register_model("alpha", "echo", ADMIN, version=2)
        self.store.register_model("alpha", "echo", ADMIN, version=1)
        order = [(m["name"], m["version"]) for m in self.store.list_models(MEMBER)]
        self.assertEqual(order, [("alpha", 1), ("alpha", 2), ("zeta", 1)])

    def test_set_model_status_roundtrip_and_validation(self):
        """Core 1: set_model_status flips active<->deprecated and
        rejects any other status with ValidationError."""
        self.store.register_model("m", "echo", ADMIN)
        updated = self.store.set_model_status("m", 1, "deprecated", ADMIN)
        self.assertEqual(updated["status"], "deprecated")
        back = self.store.set_model_status("m", 1, "active", ADMIN)
        self.assertEqual(back["status"], "active")
        with self.assertRaises(ValidationError):
            self.store.set_model_status("m", 1, "retired", ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.set_model_status("ghost", 1, "active", ADMIN)

    def test_viewer_cannot_register_or_set_status(self):
        """Core 1 + 9: registry_write is not a viewer permission —
        register_model and set_model_status raise PermissionDenied
        for a viewer (AC-6 least privilege)."""
        with self.assertRaises(PermissionDenied):
            self.store.register_model("m", "echo", VIEWER)
        self.store.register_model("m", "echo", MEMBER)
        with self.assertRaises(PermissionDenied):
            self.store.set_model_status("m", 1, "deprecated", VIEWER)
        # ... but a viewer may read the registry.
        self.assertEqual(self.store.get_model("m", VIEWER)["name"], "m")

    def test_returned_model_is_a_copy(self):
        """Core 1: mutating a returned model dict does not corrupt
        the registry."""
        model = self.store.register_model("m", "echo", ADMIN)
        model["status"] = "deprecated"
        model["capabilities"].append("bogus")
        fresh = self.store.get_model("m", ADMIN)
        self.assertEqual(fresh["status"], "active")
        self.assertEqual(fresh["capabilities"], [])


class TestTemplateRegistry(unittest.TestCase):
    """Core function 2: Prompt template registry."""

    def setUp(self):
        self.store = fresh_store()

    def test_register_template_shape(self):
        """Core 2: register_template returns {id, name, version, text,
        created_by, created_utc} with a tpl- id."""
        tpl = self.store.register_template("greet", "Hello {prompt}", MEMBER)
        self.assertEqual(
            set(tpl.keys()),
            {"id", "name", "version", "text", "created_by", "created_utc"},
        )
        self.assertEqual(tpl["id"], "tpl-1")
        self.assertEqual(tpl["version"], 1)
        self.assertEqual(tpl["created_by"], "bob")

    def test_template_versions_like_models(self):
        """Core 2: version rules as for models — auto-increment per
        name, explicit duplicate raises ValidationError."""
        self.store.register_template("t", "one", ADMIN)
        second = self.store.register_template("t", "two", ADMIN)
        self.assertEqual(second["version"], 2)
        with self.assertRaises(ValidationError):
            self.store.register_template("t", "dup", ADMIN, version=2)
        self.assertEqual(self.store.get_template("t", ADMIN)["text"], "two")
        self.assertEqual(
            self.store.get_template("t", ADMIN, version=1)["text"], "one"
        )

    def test_template_not_found(self):
        """Core 2: an absent template raises NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_template("ghost", ADMIN)

    def test_list_templates_sorted(self):
        """Core 2: list_templates is sorted by (name, version)."""
        self.store.register_template("b", "x", ADMIN)
        self.store.register_template("a", "x", ADMIN, version=2)
        self.store.register_template("a", "x", ADMIN, version=1)
        order = [(t["name"], t["version"]) for t in self.store.list_templates(ADMIN)]
        self.assertEqual(order, [("a", 1), ("a", 2), ("b", 1)])

    def test_viewer_cannot_register_template(self):
        """Core 2 + 9: a viewer lacks registry_write for templates."""
        with self.assertRaises(PermissionDenied):
            self.store.register_template("t", "x", VIEWER)

    def test_failed_template_consumes_no_id(self):
        """Core 2 (SI-10): a failed registration changes nothing and
        consumes no tpl- id."""
        with self.assertRaises(ValidationError):
            self.store.register_template("", "x", ADMIN)
        tpl = self.store.register_template("ok", "x", ADMIN)
        self.assertEqual(tpl["id"], "tpl-1")


if __name__ == "__main__":
    unittest.main()
