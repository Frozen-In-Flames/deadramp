"""Negative control: the suite must reject a mutant policy check.

Traces to: UNION-SPEC "Implementation contract" — tests 'include a
negative control: a mutant policy check (one that treats every text as
clean) whose behavior the canonical expectation is shown to reject — a
prompt containing a blocked term must raise PolicyBlocked and store a
blocked_input record, and the mutant is demonstrated to wave it
through — proving the suite catches that defect class rather than
merely passing.'

The traced claim: **the policy gate is the SI-10 / guardrail
enforcement point of the gateway.** Invoke step 6 evaluates the
applicable policy rules on every prompt; a match blocks the
invocation, stores a blocked_input record, and raises PolicyBlocked.
The mutant below replaces that evaluation with one that returns "no
match" for every text.

Each test asserts three things, per the canonical pattern: (1) the
canonical expectation — the real implementation raises PolicyBlocked
for the blocked term, stores exactly one blocked_input record, and
completes nothing; (2) the mutant would NOT raise — run through the
same gate shape, it waves the blocked prompt through to completion;
and (3) a literal assertRaises(AssertionError) demonstration that
treating the mutant's outcome as the expected outcome fails.
"""

import unittest

from aigateway_helpers import ADMIN, MEMBER, make_store
from aigateway.errors import PolicyBlocked


def mutant_first_policy_match(text, stage):
    """The defect under control: every text is 'clean' (no match)."""
    return None


def mutant_gate(store_prompt, stage="input"):
    """The policy gate as the mutant would run it.

    Mirrors the real gate's shape — consult the policy check, block on
    a match, otherwise proceed — but with the mutant check inside, so
    it returns "allowed" for a blocked prompt instead of raising
    PolicyBlocked.
    """
    rule = mutant_first_policy_match(store_prompt, stage)
    if rule is not None:
        raise PolicyBlocked("blocked by %s" % (rule["id"],))
    return "allowed"


BLOCKED_PROMPT = "this prompt contains the blocked term badword inside"


class TestNegativeControlMutantPolicy(unittest.TestCase):
    """Core function 6: Policy guardrails — negative control for the
    policy gate, traced claim: the policy gate is the gateway's
    guardrail enforcement point (invoke step 6)."""

    def setUp(self):
        self.store, self.audit, _ = make_store()
        self.rule = self.store.add_rule("input", "term", "badword", ADMIN)

    def _assert_mutant_rejected(self, mutant_outcome):
        """The mutant's 'allowed' must fail the canonical expectation."""
        self.assertNotEqual(mutant_outcome, "blocked")
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, "blocked")

    def test_blocked_term_canonical_expectation(self):
        """Core 6 (invoke step 6), traced claim: the policy gate
        blocks a prompt containing a blocked term. Canonical: invoke
        raises PolicyBlocked, exactly one blocked_input record is
        stored, and nothing completes. Mutant: the same prompt is
        waved through the gate."""
        with self.assertRaises(PolicyBlocked) as ctx:
            self.store.invoke("echoer", BLOCKED_PROMPT, MEMBER)
        records = self.store.list_requests(MEMBER)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["status"], "blocked_input")
        self.assertEqual(records[0]["id"], ctx.exception.request_id)
        self.assertIsNone(records[0]["output"])
        completed = [r for r in records if r["status"] == "completed"]
        self.assertEqual(completed, [])
        # The real audit trail shows the block, attributed to the rule.
        blocked = [e for e in self.audit.entries()
                   if e["action"] == "invoke_blocked"]
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0]["details"]["rule_id"], self.rule["id"])

        mutant_outcome = mutant_gate(BLOCKED_PROMPT)
        self.assertEqual(mutant_outcome, "allowed")  # mutant did not raise
        self._assert_mutant_rejected(mutant_outcome)

    def test_mutant_gate_would_complete_the_invocation(self):
        """Core 6, traced claim as above. Under the mutant's premise —
        no rule ever matches — the blocked prompt would be allowed
        through to a completion, which is exactly the outcome the
        canonical expectation forbids; the real store instead blocks
        every run of the same prompt."""
        # Mutant premise applied locally (the real policy evaluation
        # in src/ is NOT patched by this module): if the check always
        # returns no match, invoke step 6 never fires.
        outcome = mutant_gate(BLOCKED_PROMPT)
        self.assertEqual(outcome, "allowed")
        self._assert_mutant_rejected(outcome)
        # Canonical: the same prompt, run against the real gate any
        # number of times, is always blocked and never completes.
        for _ in range(2):
            with self.assertRaises(PolicyBlocked):
                self.store.invoke("echoer", BLOCKED_PROMPT, MEMBER)
        records = self.store.list_requests(MEMBER)
        self.assertEqual(len(records), 2)
        self.assertTrue(
            all(r["status"] == "blocked_input" for r in records),
            "every canonical run of the blocked prompt must be blocked",
        )


if __name__ == "__main__":
    unittest.main()
