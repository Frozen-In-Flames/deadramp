"""Policy-guardrail tests.

Traces to: UNION-SPEC Core function 6 (Policy guardrails — hooks) and
the Implementation contract for ``add_rule`` / ``remove_rule`` /
``list_rules`` and invoke steps 6 and 8. This is policy *plumbing*
(rules evaluated on input and output), not a safety model — the build
says so, and these tests trace only the plumbing claims.
"""

import unittest

from aigateway_helpers import ADMIN, MEMBER, VIEWER, make_store, register_rules_model
from aigateway.errors import (
    NotFoundError,
    PermissionDenied,
    PolicyBlocked,
    ValidationError,
)
from aigateway.store import estimate_tokens


class TestRuleManagement(unittest.TestCase):
    """Core function 6: policy rule registry."""

    def setUp(self):
        self.store, self.audit, _ = make_store()

    def test_add_rule_shape(self):
        """Core 6: add_rule returns {id, scope, kind, value,
        created_by, created_utc} with a rule- id."""
        rule = self.store.add_rule("both", "term", "spam", ADMIN)
        self.assertEqual(
            set(rule.keys()),
            {"id", "scope", "kind", "value", "created_by", "created_utc"},
        )
        self.assertEqual(rule["id"], "rule-1")
        self.assertEqual(rule["created_by"], "alice")

    def test_add_rule_validation(self):
        """Core 6 (SI-10): scope must be input|output|both and kind
        term|pattern, else ValidationError; failures consume no id."""
        with self.assertRaises(ValidationError):
            self.store.add_rule("middle", "term", "x", ADMIN)
        with self.assertRaises(ValidationError):
            self.store.add_rule("input", "fuzzy", "x", ADMIN)
        with self.assertRaises(ValidationError):
            self.store.add_rule("input", "term", "", ADMIN)
        rule = self.store.add_rule("input", "term", "x", ADMIN)
        self.assertEqual(rule["id"], "rule-1")

    def test_pattern_must_compile(self):
        """Core 6: a pattern value that does not compile as a regex
        raises ValidationError; a valid pattern is accepted."""
        with self.assertRaises(ValidationError):
            self.store.add_rule("input", "pattern", "[unclosed", ADMIN)
        rule = self.store.add_rule("input", "pattern", r"sec+ret", ADMIN)
        self.assertEqual(rule["kind"], "pattern")

    def test_list_rules_creation_order(self):
        """Core 6: list_rules returns rules in creation order."""
        self.store.add_rule("input", "term", "a", ADMIN)
        self.store.add_rule("output", "term", "b", ADMIN)
        self.store.add_rule("both", "pattern", "c", ADMIN)
        self.assertEqual(
            [r["id"] for r in self.store.list_rules(MEMBER)],
            ["rule-1", "rule-2", "rule-3"],
        )

    def test_remove_rule(self):
        """Core 6: remove_rule returns the removed dict and the rule
        no longer blocks; removing an unknown id raises
        NotFoundError."""
        rule = self.store.add_rule("input", "term", "spam", ADMIN)
        removed = self.store.remove_rule(rule["id"], ADMIN)
        self.assertEqual(removed["id"], rule["id"])
        self.assertEqual(self.store.list_rules(ADMIN), [])
        record = self.store.invoke("echoer", "spam eggs", MEMBER)
        self.assertEqual(record["status"], "completed")
        with self.assertRaises(NotFoundError):
            self.store.remove_rule("rule-999", ADMIN)

    def test_policy_write_requires_permission(self):
        """Core 6+9: policy_write is admin-only in the matrix — a
        member or viewer adding/removing a rule raises
        PermissionDenied."""
        with self.assertRaises(PermissionDenied):
            self.store.add_rule("input", "term", "x", MEMBER)
        with self.assertRaises(PermissionDenied):
            self.store.add_rule("input", "term", "x", VIEWER)
        rule = self.store.add_rule("input", "term", "x", ADMIN)
        with self.assertRaises(PermissionDenied):
            self.store.remove_rule(rule["id"], MEMBER)


class TestPolicyEnforcement(unittest.TestCase):
    """Core function 6: policy evaluation inside invoke()."""

    def setUp(self):
        self.store, self.audit, _ = make_store()

    def test_input_term_blocks_case_insensitively(self):
        """Core 6 / invoke step 6: a term rule matches as a
        case-insensitive substring of the effective prompt."""
        self.store.add_rule("input", "term", "Forbidden", ADMIN)
        with self.assertRaises(PolicyBlocked):
            self.store.invoke("echoer", "this is FORBIDDEN text", MEMBER)

    def test_blocked_input_record_and_exception_request_id(self):
        """Core 6 / invoke step 6: a blocked input stores a record
        with status 'blocked_input', output None, usage
        {prompt estimate, 0, prompt estimate}; PolicyBlocked carries
        that record's id as request_id."""
        self.store.add_rule("input", "term", "badword", ADMIN)
        prompt = "a badword appears"
        with self.assertRaises(PolicyBlocked) as ctx:
            self.store.invoke("echoer", prompt, MEMBER)
        request_id = ctx.exception.request_id
        self.assertTrue(request_id.startswith("req-"))
        record = self.store.get_request(request_id, MEMBER)
        self.assertEqual(record["status"], "blocked_input")
        self.assertIsNone(record["output"])
        self.assertEqual(record["prompt"], prompt)
        est = estimate_tokens(prompt)
        self.assertEqual(
            record["usage"],
            {"prompt_tokens": est, "completion_tokens": 0, "total_tokens": est},
        )

    def test_blocked_input_is_audited_with_stage_and_rule(self):
        """Core 6+10 / invoke step 6: the block audits
        'invoke_blocked' with details {stage: 'input', rule_id}."""
        rule = self.store.add_rule("input", "term", "badword", ADMIN)
        with self.assertRaises(PolicyBlocked):
            self.store.invoke("echoer", "badword", MEMBER)
        entries = [e for e in self.audit.entries() if e["action"] == "invoke_blocked"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(
            entries[0]["details"], {"stage": "input", "rule_id": rule["id"]}
        )

    def test_input_scoped_rule_does_not_block_output(self):
        """Core 6: an input-scoped rule is not evaluated on output —
        output that would match it still completes."""
        register_rules_model(self.store)
        self.store.add_rule("input", "term", "hi there", ADMIN)
        record = self.store.invoke("ruler", "hello", MEMBER)  # output 'Hi there'
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["output"], "Hi there")

    def test_output_rule_blocks_and_withholds_output(self):
        """Core 6 / invoke step 8: an output match stores a
        'blocked_output' record with output None and usage estimated
        over both prompt and the withheld output, audits stage
        'output', and raises PolicyBlocked."""
        register_rules_model(self.store)
        rule = self.store.add_rule("output", "term", "hi there", ADMIN)
        with self.assertRaises(PolicyBlocked) as ctx:
            self.store.invoke("ruler", "say hello", MEMBER)
        record = self.store.get_request(ctx.exception.request_id, MEMBER)
        self.assertEqual(record["status"], "blocked_output")
        self.assertIsNone(record["output"])
        prompt_est = estimate_tokens("say hello")
        output_est = estimate_tokens("Hi there")
        self.assertEqual(
            record["usage"],
            {"prompt_tokens": prompt_est,
             "completion_tokens": output_est,
             "total_tokens": prompt_est + output_est},
        )
        entries = [e for e in self.audit.entries() if e["action"] == "invoke_blocked"]
        self.assertEqual(entries[-1]["details"],
                         {"stage": "output", "rule_id": rule["id"]})

    def test_both_scope_blocks_either_stage(self):
        """Core 6: a 'both'-scoped rule is evaluated on input and on
        output."""
        self.store.add_rule("both", "term", "echo-me", ADMIN)
        # Input stage: the prompt itself carries the term.
        with self.assertRaises(PolicyBlocked) as ctx:
            self.store.invoke("echoer", "echo-me please", MEMBER)
        input_record = self.store.get_request(ctx.exception.request_id, MEMBER)
        self.assertEqual(input_record["status"], "blocked_input")
        # Output stage: a clean prompt whose (rules-model) output
        # carries the term is blocked as blocked_output.
        self.store.register_model(
            "defaulter", "rules", ADMIN,
            config={"rules": [], "default": "echo-me later"},
        )
        with self.assertRaises(PolicyBlocked) as ctx2:
            self.store.invoke("defaulter", "perfectly clean", MEMBER)
        output_record = self.store.get_request(ctx2.exception.request_id, MEMBER)
        self.assertEqual(output_record["status"], "blocked_output")

    def test_pattern_rule_matches_via_regex_search(self):
        """Core 6: a pattern rule matches via regex search (not just
        literal substring)."""
        self.store.add_rule("input", "pattern", r"\b\d{4}-\d{4}\b", ADMIN)
        with self.assertRaises(PolicyBlocked):
            self.store.invoke("echoer", "code 1234-5678 here", MEMBER)
        record = self.store.invoke("echoer", "no digits here", MEMBER)
        self.assertEqual(record["status"], "completed")

    def test_first_matching_rule_in_creation_order_blocks(self):
        """Core 6: rules evaluate in creation order; the first match
        is the one recorded in the audit details."""
        first = self.store.add_rule("input", "term", "bad", ADMIN)
        self.store.add_rule("input", "term", "badword", ADMIN)
        with self.assertRaises(PolicyBlocked):
            self.store.invoke("echoer", "a badword", MEMBER)
        entries = [e for e in self.audit.entries() if e["action"] == "invoke_blocked"]
        self.assertEqual(entries[0]["details"]["rule_id"], first["id"])

    def test_blocked_records_count_toward_usage(self):
        """Core 4+6: usage_for includes blocked records with their
        pinned usage."""
        self.store.add_rule("input", "term", "badword", ADMIN)
        with self.assertRaises(PolicyBlocked):
            self.store.invoke("echoer", "badword", MEMBER)  # est 2
        usage = self.store.usage_for("bob", MEMBER)
        self.assertEqual(usage["requests"], 1)
        self.assertEqual(usage["total_tokens"], estimate_tokens("badword"))

    def test_clean_prompt_completes_with_rules_present(self):
        """Core 6: rules that do not match do not block."""
        self.store.add_rule("both", "term", "never-appears", ADMIN)
        self.store.add_rule("both", "pattern", r"zzz+", ADMIN)
        record = self.store.invoke("echoer", "perfectly fine", MEMBER)
        self.assertEqual(record["status"], "completed")


if __name__ == "__main__":
    unittest.main()
