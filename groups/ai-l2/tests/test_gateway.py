"""Gateway & reference-responder tests.

Traces to: UNION-SPEC Core function 3 (Gateway & reference responder)
and Core function 4's pinned estimator; Implementation contract for
``invoke`` (the 9 pinned steps) and ``estimate_tokens`` /
``REFERENCE_NOTICE`` in ``aigateway/store.py``.

Honesty trace: the responder is a deterministic reference stub. Every
test that inspects a response asserts ``reference_stub is True`` and
the exact REFERENCE_NOTICE text — the build contains no learned model
and must never present stub output as one.
"""

import unittest

from aigateway_helpers import (
    ADMIN,
    MEMBER,
    OTHER_MEMBER,
    VIEWER,
    make_store,
    register_rules_model,
    register_template_model,
)
from aigateway.errors import (
    NotFoundError,
    PermissionDenied,
    PolicyBlocked,
    ValidationError,
)
from aigateway.store import REFERENCE_NOTICE, estimate_tokens

EXPECTED_NOTICE = (
    "Reference responder: deterministic stub output. This build contains "
    "no learned model; output is produced by the registered responder "
    "behavior (echo, template, or rules)."
)


class TestEstimateTokens(unittest.TestCase):
    """Core function 4: the pinned estimate_tokens formula."""

    def test_reference_notice_text_is_exact(self):
        """Core 3: REFERENCE_NOTICE matches the contract verbatim."""
        self.assertEqual(REFERENCE_NOTICE, EXPECTED_NOTICE)

    def test_empty_string_is_zero(self):
        """Core 4: estimate_tokens('') is 0 (pinned)."""
        self.assertEqual(estimate_tokens(""), 0)

    def test_formula_is_len_plus_3_floor_div_4(self):
        """Core 4: estimate_tokens(text) == (len(text)+3)//4 for
        non-empty text (pinned)."""
        for text, expected in (
            ("a", 1), ("abcd", 1), ("abcde", 2), ("abcdefgh", 2),
            ("x" * 100, 25), ("hello world", 3),
        ):
            with self.subTest(length=len(text)):
                self.assertEqual(estimate_tokens(text), expected)
                self.assertEqual(estimate_tokens(text), (len(text) + 3) // 4)


class TestGatewayInvoke(unittest.TestCase):
    """Core function 3: Gateway & reference responder — invoke()."""

    def setUp(self):
        self.store, self.audit, _ = make_store()

    def test_echo_invoke_shape_and_stub_labeling(self):
        """Core 3: a completed invoke returns the pinned request-dict
        shape, echo output == prompt, reference_stub True, notice ==
        REFERENCE_NOTICE, status 'completed'."""
        record = self.store.invoke("echoer", "hello world", MEMBER)
        self.assertEqual(
            set(record.keys()),
            {"id", "model", "model_version", "session_id", "actor",
             "key_id", "prompt", "output", "reference_stub", "responder",
             "notice", "usage", "status", "created_utc"},
        )
        self.assertEqual(record["id"], "req-1")
        self.assertEqual(record["model"], "echoer")
        self.assertEqual(record["model_version"], 1)
        self.assertEqual(record["actor"], "bob")
        self.assertIsNone(record["key_id"])
        self.assertIsNone(record["session_id"])
        self.assertEqual(record["prompt"], "hello world")
        self.assertEqual(record["output"], "hello world")
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["notice"], REFERENCE_NOTICE)
        self.assertEqual(record["responder"], "echo")
        self.assertEqual(record["status"], "completed")
        self.assertEqual(
            record["usage"],
            {"prompt_tokens": 3, "completion_tokens": 3, "total_tokens": 6},
        )

    def test_template_responder_fills_model_template(self):
        """Core 3: responder 'template' fills the model's configured
        template with {prompt} replaced by the effective prompt; a
        template without the placeholder is used as-is."""
        register_template_model(self.store, template="Answer: {prompt}!")
        record = self.store.invoke("templater", "why", MEMBER)
        self.assertEqual(record["output"], "Answer: why!")
        self.assertIs(record["reference_stub"], True)
        register_template_model(self.store, name="fixed", template="constant")
        record2 = self.store.invoke("fixed", "anything", MEMBER)
        self.assertEqual(record2["output"], "constant")

    def test_rules_responder_first_match_then_default(self):
        """Core 3: responder 'rules' — the first rule whose match is a
        case-insensitive substring of the prompt wins, else the
        configured default."""
        register_rules_model(self.store)
        hit = self.store.invoke("ruler", "well HELLO there", MEMBER)
        self.assertEqual(hit["output"], "Hi there")
        miss = self.store.invoke("ruler", "goodbye", MEMBER)
        self.assertEqual(miss["output"], "No rule matched")

    def test_invoke_specific_model_version(self):
        """Core 3 / invoke step 1: an explicit version routes to that
        version's responder."""
        self.store.register_model("echoer", "template", ADMIN,
                                  config={"template": "V2 {prompt}"})
        record = self.store.invoke("echoer", "x", MEMBER, version=1)
        self.assertEqual(record["model_version"], 1)
        self.assertEqual(record["output"], "x")
        record2 = self.store.invoke("echoer", "x", MEMBER)
        self.assertEqual(record2["model_version"], 2)
        self.assertEqual(record2["output"], "V2 x")

    def test_invoke_unknown_model_not_found(self):
        """Core 3 / invoke step 1: an unknown model raises
        NotFoundError and stores nothing."""
        with self.assertRaises(NotFoundError):
            self.store.invoke("ghost", "hi", MEMBER)
        self.assertEqual(self.store.list_requests(MEMBER), [])

    def test_deprecated_model_refuses_requests(self):
        """Core 1+3 / invoke step 1: a deprecated model raises
        ValidationError and stores nothing."""
        self.store.set_model_status("echoer", 1, "deprecated", ADMIN)
        with self.assertRaises(ValidationError):
            self.store.invoke("echoer", "hi", MEMBER)
        self.assertEqual(self.store.list_requests(ADMIN), [])

    def test_invoke_audits_with_model_and_total_tokens(self):
        """Core 3+10: a completed invoke audits 'invoke' with details
        {model, total_tokens}."""
        record = self.store.invoke("echoer", "abcd", MEMBER)
        entries = [e for e in self.audit.entries() if e["action"] == "invoke"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["target"], record["id"])
        self.assertEqual(
            entries[0]["details"],
            {"model": "echoer", "total_tokens": record["usage"]["total_tokens"]},
        )

    def test_viewer_cannot_invoke(self):
        """Core 3+9: invoke is not a viewer permission."""
        with self.assertRaises(PermissionDenied):
            self.store.invoke("echoer", "hi", VIEWER)
        self.assertEqual(self.store.list_requests(ADMIN), [])

    def test_invoke_with_own_key_attributes_record(self):
        """Core 3 / invoke step 2: invoking with one's own key stores
        key_id on the record."""
        key = self.store.create_api_key("bob", MEMBER)
        record = self.store.invoke("echoer", "hi", MEMBER, key_id=key["id"])
        self.assertEqual(record["key_id"], key["id"])

    def test_invoke_with_unknown_key_not_found(self):
        """Core 3 / invoke step 2: an unknown key_id raises
        NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.invoke("echoer", "hi", MEMBER, key_id="key-999")

    def test_invoke_with_anothers_key_denied_but_admin_allowed(self):
        """Core 3 / invoke step 2: another member using bob's key gets
        PermissionDenied; a platform admin may use it."""
        key = self.store.create_api_key("bob", MEMBER)
        with self.assertRaises(PermissionDenied):
            self.store.invoke("echoer", "hi", OTHER_MEMBER, key_id=key["id"])
        record = self.store.invoke("echoer", "hi", ADMIN, key_id=key["id"])
        self.assertEqual(record["key_id"], key["id"])

    def test_prompt_template_renders_before_routing_and_metering(self):
        """Core 2+3 / invoke step 4: a named prompt template renders
        the prompt ({prompt} substitution); the rendered text is the
        effective prompt in the record, the output, and metering. A
        template without the placeholder is used as-is."""
        self.store.register_template("wrap", "Please: {prompt}.", MEMBER)
        record = self.store.invoke(
            "echoer", "help me", MEMBER, template_name="wrap"
        )
        self.assertEqual(record["prompt"], "Please: help me.")
        self.assertEqual(record["output"], "Please: help me.")
        self.assertEqual(
            record["usage"]["prompt_tokens"], estimate_tokens("Please: help me.")
        )
        self.store.register_template("fixed", "static text", MEMBER)
        record2 = self.store.invoke(
            "echoer", "ignored", MEMBER, template_name="fixed"
        )
        self.assertEqual(record2["prompt"], "static text")

    def test_invoke_with_unknown_template_not_found(self):
        """Core 3 / invoke step 4: an unknown template_name raises
        NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.invoke("echoer", "hi", MEMBER, template_name="ghost")

    def test_invoke_non_string_prompt_rejected(self):
        """Core 3 (SI-10): a non-string prompt raises ValidationError
        and stores nothing."""
        with self.assertRaises(ValidationError):
            self.store.invoke("echoer", 42, MEMBER)
        self.assertEqual(self.store.list_requests(ADMIN), [])

    def test_policy_blocked_is_not_a_completion(self):
        """Core 3+6: a policy-blocked invoke raises PolicyBlocked, so
        no 'completed' record exists for it (see test_policy.py for
        the blocked record itself)."""
        self.store.add_rule("input", "term", "badword", ADMIN)
        with self.assertRaises(PolicyBlocked):
            self.store.invoke("echoer", "a badword here", MEMBER)
        statuses = [r["status"] for r in self.store.list_requests(MEMBER)]
        self.assertEqual(statuses, ["blocked_input"])


if __name__ == "__main__":
    unittest.main()
