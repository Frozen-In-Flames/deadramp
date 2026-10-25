"""Conversation & request-record tests, including zero-persistence.

Traces to: UNION-SPEC Core function 5 (Conversation & request records,
incl. the zero-persistence / ephemeral processing mode) and the
Implementation contract for ``create_session`` / ``get_session`` /
``list_sessions`` / ``get_request`` / ``list_requests`` and invoke
step 9; control flavor SC/SI data minimization for zero-persistence.
"""

import unittest

from aigateway_helpers import (
    ADMIN,
    MEMBER,
    OTHER_MEMBER,
    VIEWER,
    fresh_store,
    make_store,
)
from aigateway.errors import NotFoundError, PermissionDenied, PolicyBlocked
from aigateway.store import REFERENCE_NOTICE


class TestSessions(unittest.TestCase):
    """Core function 5: conversation sessions."""

    def setUp(self):
        self.store, self.audit, _ = make_store()

    def test_create_session_shape(self):
        """Core 5: create_session returns {id, owner, title, turns,
        created_utc} with a ses- id and turns starting empty."""
        session = self.store.create_session("My chat", MEMBER)
        self.assertEqual(
            set(session.keys()), {"id", "owner", "title", "turns", "created_utc"}
        )
        self.assertEqual(session["id"], "ses-1")
        self.assertEqual(session["owner"], "bob")
        self.assertEqual(session["turns"], [])

    def test_create_session_requires_invoke_permission(self):
        """Core 5+9: create_session is the 'invoke' action — a viewer
        cannot create a session."""
        with self.assertRaises(PermissionDenied):
            self.store.create_session("nope", VIEWER)

    def test_get_session_owner_or_admin_only(self):
        """Core 5: get_session is owner-or-admin; another member gets
        PermissionDenied, an unknown id NotFoundError."""
        session = self.store.create_session("private", MEMBER)
        self.assertEqual(
            self.store.get_session(session["id"], MEMBER)["id"], session["id"]
        )
        self.assertEqual(
            self.store.get_session(session["id"], ADMIN)["id"], session["id"]
        )
        with self.assertRaises(PermissionDenied):
            self.store.get_session(session["id"], OTHER_MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.get_session("ses-999", MEMBER)

    def test_list_sessions_scoped_and_chronological(self):
        """Core 5: list_sessions returns the actor's own sessions
        (admin: all), chronological."""
        first = self.store.create_session("one", MEMBER)
        second = self.store.create_session("two", OTHER_MEMBER)
        third = self.store.create_session("three", MEMBER)
        bob_ids = [s["id"] for s in self.store.list_sessions(MEMBER)]
        self.assertEqual(bob_ids, [first["id"], third["id"]])
        all_ids = [s["id"] for s in self.store.list_sessions(ADMIN)]
        self.assertEqual(all_ids, [first["id"], second["id"], third["id"]])

    def test_completed_invoke_appends_turn(self):
        """Core 5 / invoke step 9: a completed invocation with a
        session appends a turn {request_id, prompt, output,
        created_utc} to that session."""
        session = self.store.create_session("chat", MEMBER)
        record = self.store.invoke(
            "echoer", "turn one", MEMBER, session_id=session["id"]
        )
        fetched = self.store.get_session(session["id"], MEMBER)
        self.assertEqual(len(fetched["turns"]), 1)
        turn = fetched["turns"][0]
        self.assertEqual(
            set(turn.keys()), {"request_id", "prompt", "output", "created_utc"}
        )
        self.assertEqual(turn["request_id"], record["id"])
        self.assertEqual(turn["prompt"], "turn one")
        self.assertEqual(turn["output"], "turn one")

    def test_blocked_invoke_appends_no_turn(self):
        """Core 5 / invoke steps 6/8: blocked records never append
        session turns."""
        session = self.store.create_session("chat", MEMBER)
        self.store.add_rule("input", "term", "badword", ADMIN)
        with self.assertRaises(PolicyBlocked):
            self.store.invoke(
                "echoer", "badword", MEMBER, session_id=session["id"]
            )
        fetched = self.store.get_session(session["id"], MEMBER)
        self.assertEqual(fetched["turns"], [])

    def test_invoke_with_unknown_session_not_found(self):
        """Core 5 / invoke step 3: an unknown session_id raises
        NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.invoke("echoer", "hi", MEMBER, session_id="ses-999")

    def test_invoke_with_anothers_session_denied_but_admin_allowed(self):
        """Core 5 / invoke step 3: a session belongs to its owner; a
        platform admin may invoke into it."""
        session = self.store.create_session("bob's", MEMBER)
        with self.assertRaises(PermissionDenied):
            self.store.invoke(
                "echoer", "hi", OTHER_MEMBER, session_id=session["id"]
            )
        record = self.store.invoke(
            "echoer", "hi", ADMIN, session_id=session["id"]
        )
        self.assertEqual(record["session_id"], session["id"])


class TestRequestRecords(unittest.TestCase):
    """Core function 5: request records (operational metadata)."""

    def setUp(self):
        self.store, self.audit, _ = make_store()

    def test_record_carries_operational_metadata(self):
        """Core 5: every invocation leaves a record with model,
        actor, key, token counts, status, and timestamps (Consus's
        operational metadata)."""
        key = self.store.create_api_key("bob", MEMBER)
        record = self.store.invoke("echoer", "meta", MEMBER, key_id=key["id"])
        self.assertEqual(record["model"], "echoer")
        self.assertEqual(record["actor"], "bob")
        self.assertEqual(record["key_id"], key["id"])
        self.assertEqual(record["status"], "completed")
        self.assertIn("total_tokens", record["usage"])
        self.assertTrue(record["created_utc"])

    def test_get_request_actor_or_admin_only(self):
        """Core 5: get_request is the invocation's actor or a
        platform admin; others get PermissionDenied, unknown ids
        NotFoundError."""
        record = self.store.invoke("echoer", "mine", MEMBER)
        self.assertEqual(self.store.get_request(record["id"], MEMBER)["id"],
                         record["id"])
        self.assertEqual(self.store.get_request(record["id"], ADMIN)["id"],
                         record["id"])
        with self.assertRaises(PermissionDenied):
            self.store.get_request(record["id"], OTHER_MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.get_request("req-999", ADMIN)

    def test_list_requests_scoped_chronological_and_filtered(self):
        """Core 5: list_requests returns the actor's own records
        (admin: all), chronological, optionally filtered to one
        session."""
        s1 = self.store.create_session("s1", MEMBER)
        r1 = self.store.invoke("echoer", "one", MEMBER, session_id=s1["id"])
        r2 = self.store.invoke("echoer", "two", OTHER_MEMBER)
        r3 = self.store.invoke("echoer", "three", MEMBER)
        bob_ids = [r["id"] for r in self.store.list_requests(MEMBER)]
        self.assertEqual(bob_ids, [r1["id"], r3["id"]])
        all_ids = [r["id"] for r in self.store.list_requests(ADMIN)]
        self.assertEqual(all_ids, [r1["id"], r2["id"], r3["id"]])
        in_session = self.store.list_requests(MEMBER, session_id=s1["id"])
        self.assertEqual([r["id"] for r in in_session], [r1["id"]])


class TestZeroPersistence(unittest.TestCase):
    """Core function 5: zero-persistence mode (Consus's architecture:
    content processed ephemerally; only operational metadata persists)."""

    def setUp(self):
        self.store, self.audit, _ = make_store(zero_persistence=True)

    def test_completed_record_withholds_content_keeps_metadata(self):
        """Core 5 (zero-persistence): a stored completed record
        carries prompt/output as None and content_withheld True,
        while metadata (ids, model, actor, usage, status, timestamp,
        responder, notice) is stored in full."""
        session = self.store.create_session("ephemeral", MEMBER)
        record = self.store.invoke(
            "echoer", "secret prompt text", MEMBER, session_id=session["id"]
        )
        self.assertIsNone(record["prompt"])
        self.assertIsNone(record["output"])
        self.assertIs(record["content_withheld"], True)
        self.assertEqual(record["model"], "echoer")
        self.assertEqual(record["actor"], "bob")
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["usage"]["total_tokens"], 10)
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["notice"], REFERENCE_NOTICE)
        self.assertNotIn("secret prompt text", str(self.store.list_requests(ADMIN)))

    def test_session_turns_withhold_content(self):
        """Core 5 (zero-persistence): session turns also carry
        prompt/output as None and content_withheld True."""
        session = self.store.create_session("ephemeral", MEMBER)
        record = self.store.invoke(
            "echoer", "hidden words", MEMBER, session_id=session["id"]
        )
        fetched = self.store.get_session(session["id"], MEMBER)
        self.assertEqual(len(fetched["turns"]), 1)
        turn = fetched["turns"][0]
        self.assertIsNone(turn["prompt"])
        self.assertIsNone(turn["output"])
        self.assertIs(turn["content_withheld"], True)
        self.assertEqual(turn["request_id"], record["id"])

    def test_blocked_record_withholds_content(self):
        """Core 5 (zero-persistence): blocked records also withhold
        the prompt, keeping the blocked metadata and usage."""
        self.store.add_rule("input", "term", "badword", ADMIN)
        with self.assertRaises(PolicyBlocked) as ctx:
            self.store.invoke("echoer", "a badword prompt", MEMBER)
        record = self.store.get_request(ctx.exception.request_id, MEMBER)
        self.assertEqual(record["status"], "blocked_input")
        self.assertIsNone(record["prompt"])
        self.assertIsNone(record["output"])
        self.assertIs(record["content_withheld"], True)
        self.assertGreater(record["usage"]["prompt_tokens"], 0)

    def test_normal_mode_has_no_content_withheld_key(self):
        """Core 5: outside zero-persistence mode, records store
        content and carry no content_withheld key."""
        store = fresh_store()
        store.register_model("echoer", "echo", ADMIN)
        record = store.invoke("echoer", "visible", MEMBER)
        self.assertEqual(record["prompt"], "visible")
        self.assertEqual(record["output"], "visible")
        self.assertNotIn("content_withheld", record)


if __name__ == "__main__":
    unittest.main()
