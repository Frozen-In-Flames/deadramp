"""Evaluation-harness tests.

Traces to: UNION-SPEC Core function 7 (Evaluation harness) and the
Implementation contract for ``create_eval_dataset`` /
``get_eval_dataset`` / ``list_eval_datasets`` / ``run_eval`` /
``get_eval_run``. Eval runs exercise the responder directly — not
metered as gateway traffic, no quota, no policy, no request record —
but (being operator-supplied test data) stored by design even in
zero-persistence mode.
"""

import unittest

from aigateway_helpers import (
    ADMIN,
    MEMBER,
    OTHER_MEMBER,
    VIEWER,
    make_store,
    register_rules_model,
)
from aigateway.errors import NotFoundError, PermissionDenied, ValidationError


def _echo_dataset(store, actor=MEMBER):
    return store.create_eval_dataset(
        "echo-basics",
        [
            {"prompt": "hello", "expected": "hello"},
            {"prompt": "bye", "expected": "hello"},
        ],
        actor,
    )


class TestEvalDatasets(unittest.TestCase):
    """Core function 7: evaluation datasets."""

    def setUp(self):
        self.store, self.audit, _ = make_store()

    def test_create_dataset_shape_and_case_ids(self):
        """Core 7: create_eval_dataset returns {id, name, cases,
        created_by, created_utc} with an evd- id; stored cases gain
        sequential case_ids case-1, case-2, ..."""
        dataset = _echo_dataset(self.store)
        self.assertEqual(
            set(dataset.keys()),
            {"id", "name", "cases", "created_by", "created_utc"},
        )
        self.assertEqual(dataset["id"], "evd-1")
        self.assertEqual(
            [c["case_id"] for c in dataset["cases"]], ["case-1", "case-2"]
        )
        self.assertEqual(dataset["cases"][0]["prompt"], "hello")
        self.assertEqual(dataset["created_by"], "bob")

    def test_create_dataset_validation(self):
        """Core 7 (SI-10): cases must be a non-empty list of dicts
        with string prompt/expected; match must be exact|contains;
        rubric must map names to substrings. Failures consume no id."""
        bad_case_sets = (
            [],
            "not-a-list",
            [{"expected": "x"}],
            [{"prompt": "x"}],
            [{"prompt": 1, "expected": "x"}],
            [{"prompt": "x", "expected": "y", "match": "fuzzy"}],
            [{"prompt": "x", "expected": "y", "rubric": {"tone": 3}}],
            [{"prompt": "x", "expected": "y", "rubric": "nope"}],
        )
        for cases in bad_case_sets:
            with self.subTest(cases=cases):
                with self.assertRaises(ValidationError):
                    self.store.create_eval_dataset("bad", cases, MEMBER)
        good = _echo_dataset(self.store)
        self.assertEqual(good["id"], "evd-1")

    def test_get_and_list_datasets(self):
        """Core 7: get_eval_dataset / list_eval_datasets return the
        stored datasets; unknown ids raise NotFoundError."""
        dataset = _echo_dataset(self.store)
        self.assertEqual(
            self.store.get_eval_dataset(dataset["id"], VIEWER)["id"],
            dataset["id"],
        )
        self.assertEqual(
            [d["id"] for d in self.store.list_eval_datasets(MEMBER)],
            [dataset["id"]],
        )
        with self.assertRaises(NotFoundError):
            self.store.get_eval_dataset("evd-999", ADMIN)

    def test_viewer_cannot_create_dataset(self):
        """Core 7+9: dataset creation is the eval_run action — a
        viewer raises PermissionDenied."""
        with self.assertRaises(PermissionDenied):
            _echo_dataset(self.store, actor=VIEWER)


class TestEvalRuns(unittest.TestCase):
    """Core function 7: evaluation runs and scoring."""

    def setUp(self):
        self.store, self.audit, _ = make_store()

    def test_run_shape_and_exact_scoring(self):
        """Core 7: run_eval returns {id, dataset_id, model,
        model_version, results, passed, total, score, created_by,
        created_utc} with an evr- id; exact scoring compares
        output.strip() == expected.strip(); score is passed/total
        as a float."""
        dataset = _echo_dataset(self.store)
        run = self.store.run_eval(dataset["id"], "echoer", MEMBER)
        self.assertEqual(
            set(run.keys()),
            {"id", "dataset_id", "model", "model_version", "results",
             "passed", "total", "score", "created_by", "created_utc"},
        )
        self.assertEqual(run["id"], "evr-1")
        self.assertEqual(run["passed"], 1)
        self.assertEqual(run["total"], 2)
        self.assertEqual(run["score"], 0.5)
        self.assertIsInstance(run["score"], float)
        first = run["results"][0]
        self.assertEqual(
            set(first.keys()),
            {"case_id", "prompt", "expected", "output", "passed",
             "rubric_results"},
        )
        self.assertTrue(first["passed"])
        self.assertFalse(run["results"][1]["passed"])

    def test_contains_match_is_case_insensitive(self):
        """Core 7: match 'contains' passes iff expected.lower() is a
        substring of output.lower()."""
        register_rules_model(self.store)
        dataset = self.store.create_eval_dataset(
            "contains-ds",
            [{"prompt": "say hello", "expected": "HI THERE",
              "match": "contains"}],
            MEMBER,
        )
        run = self.store.run_eval(dataset["id"], "ruler", MEMBER)
        self.assertEqual(run["score"], 1.0)

    def test_exact_match_strips_whitespace(self):
        """Core 7: exact scoring strips both sides before comparing."""
        dataset = self.store.create_eval_dataset(
            "strip-ds",
            [{"prompt": "  padded  ", "expected": "padded"}],
            MEMBER,
        )
        # Echo returns the prompt verbatim ('  padded  '); strip makes
        # it equal 'padded'.
        run = self.store.run_eval(dataset["id"], "echoer", MEMBER)
        self.assertEqual(run["passed"], 1)

    def test_rubric_criteria_must_all_pass(self):
        """Core 7: each rubric criterion passes iff its substring
        appears in the output (case-insensitive); a case passes iff
        its match passes AND every rubric criterion passes."""
        register_rules_model(self.store)
        dataset = self.store.create_eval_dataset(
            "rubric-ds",
            [
                {"prompt": "hello friend", "expected": "Hi there",
                 "rubric": {"greets": "hi", "warmth": "THERE"}},
                {"prompt": "hello friend", "expected": "Hi there",
                 "rubric": {"missing": "absent-substring"}},
            ],
            MEMBER,
        )
        run = self.store.run_eval(dataset["id"], "ruler", MEMBER)
        self.assertEqual(run["results"][0]["rubric_results"],
                         {"greets": True, "warmth": True})
        self.assertTrue(run["results"][0]["passed"])
        self.assertEqual(run["results"][1]["rubric_results"],
                         {"missing": False})
        self.assertFalse(run["results"][1]["passed"])
        self.assertEqual(run["score"], 0.5)

    def test_run_is_not_gateway_traffic(self):
        """Core 7: an eval run creates no request record, meters no
        usage, and is unaffected by quota or policy rules that would
        block the same prompts through the gateway."""
        self.store.add_rule("input", "term", "hello", ADMIN)
        self.store.set_quota("bob", 1, ADMIN)
        dataset = _echo_dataset(self.store)
        run = self.store.run_eval(dataset["id"], "echoer", MEMBER)
        self.assertEqual(run["total"], 2)
        self.assertEqual(self.store.list_requests(ADMIN), [])
        usage = self.store.usage_for("bob", MEMBER)
        self.assertEqual(usage["requests"], 0)
        self.assertEqual(usage["total_tokens"], 0)

    def test_run_audits_eval_run(self):
        """Core 7+10: a run audits 'eval_run'."""
        dataset = _echo_dataset(self.store)
        run = self.store.run_eval(dataset["id"], "echoer", MEMBER)
        entries = [e for e in self.audit.entries() if e["action"] == "eval_run"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["target"], run["id"])

    def test_run_unknown_dataset_or_model(self):
        """Core 7: unknown dataset/model ids raise NotFoundError."""
        dataset = _echo_dataset(self.store)
        with self.assertRaises(NotFoundError):
            self.store.run_eval("evd-999", "echoer", MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.run_eval(dataset["id"], "ghost", MEMBER)

    def test_get_eval_run_creator_or_admin_only(self):
        """Core 7: get_eval_run is the run's creator or a platform
        admin; others get PermissionDenied, unknown ids
        NotFoundError."""
        dataset = _echo_dataset(self.store)
        run = self.store.run_eval(dataset["id"], "echoer", MEMBER)
        self.assertEqual(self.store.get_eval_run(run["id"], MEMBER)["id"],
                         run["id"])
        self.assertEqual(self.store.get_eval_run(run["id"], ADMIN)["id"],
                         run["id"])
        with self.assertRaises(PermissionDenied):
            self.store.get_eval_run(run["id"], OTHER_MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.get_eval_run("evr-999", ADMIN)

    def test_eval_stored_even_in_zero_persistence_mode(self):
        """Core 7 (spec note): eval datasets/runs are operator-
        supplied test data, stored by design even when the store is
        in zero-persistence mode."""
        store, _, _ = make_store(zero_persistence=True)
        dataset = _echo_dataset(store)
        run = store.run_eval(dataset["id"], "echoer", MEMBER)
        self.assertEqual(run["results"][0]["output"], "hello")
        self.assertEqual(run["results"][0]["prompt"], "hello")


if __name__ == "__main__":
    unittest.main()
