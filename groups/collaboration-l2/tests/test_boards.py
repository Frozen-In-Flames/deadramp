"""Whiteboard tests.

Traces to: UNION-SPEC Core function 6 (Whiteboards — boards inside a
workspace holding positioned text cards (text plus x/y position) that
members can add and move; no raster canvas) / ranking row 17
(Whiteboarding, visual collaboration & co-authoring, 6 siblings);
Implementation contract for ``collab/store.py`` board/card methods;
control families AC-3 (membership boundary) and SI-10 (non-numeric
coordinates rejected; failed operations consume no id).
"""

import unittest

from collab_helpers import (
    ADMIN,
    MEMBER,
    OUTSIDER,
    VIEWER,
    add_sample_card,
    create_sample_board,
    fresh_store,
    make_store,
)
from collab.errors import NotFoundError, PermissionDenied, ValidationError

BOARD_KEYS = {"id", "workspace_id", "name", "created_by", "created_utc"}
CARD_KEYS = {
    "id", "board_id", "workspace_id", "text", "x", "y", "created_by",
    "created_utc",
}


class TestBoards(unittest.TestCase):
    """Core: Whiteboards — board creation and listing."""

    def setUp(self):
        self.store, self.ws_id = make_store()

    def test_create_board_returns_the_contract_dict(self):
        """Core: Whiteboards. Contract: create_board returns {id,
        workspace_id, name, created_by, created_utc} with a bd- id."""
        board = create_sample_board(self.store, self.ws_id, name="Sprint")
        self.assertEqual(set(board.keys()), BOARD_KEYS)
        self.assertEqual(board["id"], "bd-1")
        self.assertEqual(board["workspace_id"], self.ws_id)
        self.assertEqual(board["name"], "Sprint")
        self.assertEqual(board["created_by"], "bob")

    def test_board_ids_are_sequential(self):
        """Core: Whiteboards. Board ids increment bd-1, bd-2."""
        first = create_sample_board(self.store, self.ws_id, name="a")
        second = create_sample_board(self.store, self.ws_id, name="b")
        self.assertEqual([first["id"], second["id"]], ["bd-1", "bd-2"])

    def test_list_boards_returns_created_boards(self):
        """Core: Whiteboards. list_boards returns the workspace's
        boards for a member (read)."""
        create_sample_board(self.store, self.ws_id, name="a")
        create_sample_board(self.store, self.ws_id, name="b")
        names = [b["name"] for b in self.store.list_boards(self.ws_id, VIEWER)]
        self.assertEqual(names, ["a", "b"])

    def test_viewer_member_cannot_create_board(self):
        """Core: Whiteboards + Access control. Boards require
        board_edit, which viewer lacks."""
        with self.assertRaises(PermissionDenied):
            create_sample_board(self.store, self.ws_id, actor=VIEWER)

    def test_non_member_cannot_create_or_list_boards(self):
        """Core: Whiteboards (AC-3). Membership is enforced on boards."""
        with self.assertRaises(PermissionDenied):
            create_sample_board(self.store, self.ws_id, actor=OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.store.list_boards(self.ws_id, OUTSIDER)


class TestCards(unittest.TestCase):
    """Core: Whiteboards — positioned text cards."""

    def setUp(self):
        self.store, self.ws_id = make_store()
        self.board = create_sample_board(self.store, self.ws_id)

    def test_add_card_returns_the_contract_dict(self):
        """Core: Whiteboards. Contract: add_card returns {id, board_id,
        workspace_id, text, x, y, created_by, created_utc} with a
        card- id."""
        card = add_sample_card(
            self.store, self.ws_id, self.board["id"], text="Idea", x=10, y=20
        )
        self.assertEqual(set(card.keys()), CARD_KEYS)
        self.assertEqual(card["id"], "card-1")
        self.assertEqual(card["board_id"], self.board["id"])
        self.assertEqual(card["workspace_id"], self.ws_id)
        self.assertEqual(card["text"], "Idea")
        self.assertEqual(card["x"], 10)
        self.assertEqual(card["y"], 20)
        self.assertEqual(card["created_by"], "bob")

    def test_card_positions_accept_floats_and_negatives(self):
        """Core: Whiteboards. x/y are numbers — floats and negative
        coordinates are valid positions."""
        card = add_sample_card(
            self.store, self.ws_id, self.board["id"], x=-3.5, y=0.25
        )
        self.assertEqual(card["x"], -3.5)
        self.assertEqual(card["y"], 0.25)

    def test_non_numeric_x_is_validation_error(self):
        """Core: Whiteboards (SI-10). Contract: 'x/y must be numbers,
        else ValidationError' — a string x is rejected."""
        with self.assertRaises(ValidationError):
            add_sample_card(
                self.store, self.ws_id, self.board["id"], x="10", y=20
            )

    def test_non_numeric_y_is_validation_error(self):
        """Core: Whiteboards (SI-10). A string y is rejected the same
        way."""
        with self.assertRaises(ValidationError):
            add_sample_card(
                self.store, self.ws_id, self.board["id"], x=10, y="high"
            )

    def test_none_coordinate_is_validation_error(self):
        """Core: Whiteboards (SI-10). A missing (None) coordinate is
        not a number and is rejected."""
        with self.assertRaises(ValidationError):
            add_sample_card(
                self.store, self.ws_id, self.board["id"], x=None, y=20
            )

    def test_failed_add_card_consumes_no_id_and_stores_nothing(self):
        """Core: Whiteboards (SI-10). Rejected cards are never
        partially applied: the board stays empty and the next valid
        card is still card-1."""
        store = fresh_store()
        ws = store.create_workspace("solo", MEMBER)
        board = store.create_board(ws["id"], "b", MEMBER)
        with self.assertRaises(ValidationError):
            store.add_card(ws["id"], board["id"], "bad", "x", 1, MEMBER)
        self.assertEqual(store.list_cards(ws["id"], board["id"], MEMBER), [])
        card = store.add_card(ws["id"], board["id"], "good", 1, 1, MEMBER)
        self.assertEqual(card["id"], "card-1")

    def test_add_card_to_unknown_board_is_rejected(self):
        """Core: Whiteboards. Adding to a board that does not exist is
        rejected."""
        with self.assertRaises((NotFoundError, ValidationError)):
            add_sample_card(self.store, self.ws_id, "bd-999999")

    def test_list_cards_returns_the_boards_cards_in_order(self):
        """Core: Whiteboards. list_cards returns the board's cards in
        creation order for a member (read)."""
        add_sample_card(self.store, self.ws_id, self.board["id"], text="one")
        add_sample_card(self.store, self.ws_id, self.board["id"], text="two")
        texts = [
            c["text"]
            for c in self.store.list_cards(
                self.ws_id, self.board["id"], VIEWER
            )
        ]
        self.assertEqual(texts, ["one", "two"])

    def test_cards_are_scoped_to_their_board(self):
        """Core: Whiteboards. One board's list never shows another
        board's cards."""
        other = create_sample_board(self.store, self.ws_id, name="other")
        add_sample_card(self.store, self.ws_id, self.board["id"], text="here")
        add_sample_card(self.store, self.ws_id, other["id"], text="there")
        texts = [
            c["text"]
            for c in self.store.list_cards(self.ws_id, self.board["id"],
                                           MEMBER)
        ]
        self.assertEqual(texts, ["here"])

    def test_move_card_updates_the_position(self):
        """Core: Whiteboards. Contract: move_card returns the updated
        card dict with the new x/y, other fields unchanged."""
        card = add_sample_card(
            self.store, self.ws_id, self.board["id"], text="drag me",
            x=1, y=2,
        )
        moved = self.store.move_card(
            self.ws_id, self.board["id"], card["id"], 50, 60, MEMBER
        )
        self.assertEqual(moved["id"], card["id"])
        self.assertEqual(moved["x"], 50)
        self.assertEqual(moved["y"], 60)
        self.assertEqual(moved["text"], "drag me")
        listed = self.store.list_cards(self.ws_id, self.board["id"], MEMBER)
        self.assertEqual((listed[0]["x"], listed[0]["y"]), (50, 60))

    def test_move_unknown_card_is_not_found(self):
        """Core: Whiteboards. Moving a card that does not exist ->
        NotFoundError (or a validation rejection)."""
        with self.assertRaises((NotFoundError, ValidationError)):
            self.store.move_card(
                self.ws_id, self.board["id"], "card-999999", 1, 1, MEMBER
            )

    def test_viewer_member_can_read_but_cannot_add_or_move(self):
        """Core: Whiteboards + Access control. Viewer holds read, not
        board_edit: listing works, adding and moving are denied."""
        card = add_sample_card(self.store, self.ws_id, self.board["id"])
        self.assertEqual(
            len(self.store.list_cards(self.ws_id, self.board["id"], VIEWER)),
            1,
        )
        with self.assertRaises(PermissionDenied):
            add_sample_card(
                self.store, self.ws_id, self.board["id"], actor=VIEWER
            )
        with self.assertRaises(PermissionDenied):
            self.store.move_card(
                self.ws_id, self.board["id"], card["id"], 5, 5, VIEWER
            )

    def test_non_member_cannot_add_list_or_move_cards(self):
        """Core: Whiteboards (AC-3). A non-member is denied on every
        card operation."""
        card = add_sample_card(self.store, self.ws_id, self.board["id"])
        with self.assertRaises(PermissionDenied):
            add_sample_card(
                self.store, self.ws_id, self.board["id"], actor=OUTSIDER
            )
        with self.assertRaises(PermissionDenied):
            self.store.list_cards(self.ws_id, self.board["id"], OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.store.move_card(
                self.ws_id, self.board["id"], card["id"], 5, 5, OUTSIDER
            )

    def test_platform_admin_may_create_board_and_add_card(self):
        """Core: Whiteboards + Access control. The platform admin role
        satisfies the membership rule for boards."""
        board = create_sample_board(self.store, self.ws_id, actor=ADMIN)
        card = add_sample_card(
            self.store, self.ws_id, board["id"], actor=ADMIN
        )
        self.assertEqual(card["board_id"], board["id"])


if __name__ == "__main__":
    unittest.main()
