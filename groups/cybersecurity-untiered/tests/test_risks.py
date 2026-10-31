"""Risk-register tests.

Traces to: UNION-SPEC Core function 5 (Risk register — standing risks
with likelihood × impact scoring (1–25) and bands, an owner, a
lifecycle, and links to the findings that evidence them);
Implementation contract for ``cyber/store.py`` create_risk / get_risk
/ list_risks / transition_risk and RISK_TRANSITIONS; control families
RA-3 and CA-5.
"""

import unittest
from datetime import datetime

from cyber_helpers import (
    ANALYST,
    VIEWER,
    create_sample_risk,
    fresh_store,
    ingest_sample_finding,
    make_asset,
    make_store,
)
from cyber.errors import NotFoundError, PermissionDenied, ValidationError
from cyber.store import RISK_TRANSITIONS

RISK_KEYS = {
    "id", "title", "description", "likelihood", "impact", "score",
    "band", "status", "owner", "finding_ids", "created_by",
    "created_utc", "updated_utc",
}

# Shortest legal path from "open" to each risk status.
PATH_TO = {
    "open": [],
    "monitoring": ["monitoring"],
    "treated": ["treated"],
    "closed": ["closed"],
}

ALLOWED = [
    ("open", "monitoring"), ("open", "treated"), ("open", "closed"),
    ("monitoring", "open"), ("monitoring", "treated"),
    ("monitoring", "closed"),
    ("treated", "monitoring"), ("treated", "closed"),
    ("closed", "open"),
]

FORBIDDEN = [
    ("treated", "open"),
    ("closed", "monitoring"), ("closed", "treated"), ("closed", "closed"),
    ("open", "open"), ("monitoring", "monitoring"),
    ("treated", "treated"),
]


def _parse_ts(ts):
    """Parse a contract UTC ISO-8601 timestamp (must not raise)."""
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


class TestCreateRisk(unittest.TestCase):
    """Core: Risk register — create shape, scoring, validation."""

    def test_create_risk_shape_score_and_provenance(self):
        """Core: Risk register. Contract: create_risk returns {id,
        title, description, likelihood, impact, score, band, status,
        owner, finding_ids, created_by, created_utc, updated_utc}
        with status "open" and score/band from risk_score/risk_band
        (the sample 4×5 = 20, band critical)."""
        store, asset, finding = make_store()
        risk = create_sample_risk(store, owner="ciso",
                                  finding_ids=[finding["id"]])
        self.assertEqual(set(risk.keys()), RISK_KEYS)
        self.assertEqual(risk["id"], "risk-1")
        self.assertEqual(risk["title"], "Ransomware exposure")
        self.assertEqual((risk["likelihood"], risk["impact"]), (4, 5))
        self.assertEqual((risk["score"], risk["band"]), (20, "critical"))
        self.assertEqual(risk["status"], "open")
        self.assertEqual(risk["owner"], "ciso")
        self.assertEqual(risk["finding_ids"], [finding["id"]])
        self.assertEqual(risk["created_by"], "bob")
        _parse_ts(risk["created_utc"])  # must not raise
        _parse_ts(risk["updated_utc"])  # must not raise

    def test_create_risk_defaults_owner_empty_and_finding_ids_empty(self):
        """Core: Risk register. Contract: create_risk defaults are
        owner "" and finding_ids None (stored as an empty list)."""
        store = fresh_store()
        risk = create_sample_risk(store)
        self.assertEqual(risk["owner"], "")
        self.assertEqual(risk["finding_ids"], [])

    def test_create_risk_rejects_empty_title(self):
        """Core: Risk register. Contract: 'title non-empty'."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            create_sample_risk(store, title="")

    def test_create_risk_rejects_out_of_range_likelihood_and_impact(self):
        """Core: Risk register. Contract: likelihood and impact are
        'integers in 1..5' — 0 and 6 on either axis are rejected."""
        store = fresh_store()
        for kwargs in ({"likelihood": 0}, {"likelihood": 6},
                       {"impact": 0}, {"impact": 6},
                       {"likelihood": -1}, {"impact": 99}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValidationError):
                    create_sample_risk(store, **kwargs)

    def test_create_risk_rejects_booleans_as_likelihood_and_impact(self):
        """Core: Risk register. Contract: 'booleans are not integers
        here' — True/False are rejected even though bool subclasses
        int in Python."""
        store = fresh_store()
        for kwargs in ({"likelihood": True}, {"impact": False},
                       {"likelihood": False}, {"impact": True}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValidationError):
                    create_sample_risk(store, **kwargs)

    def test_create_risk_rejects_non_integer_likelihood_and_impact(self):
        """Core: Risk register. Contract: likelihood/impact must be
        integers — floats and numeric strings are rejected."""
        store = fresh_store()
        for kwargs in ({"likelihood": 2.5}, {"impact": "3"},
                       {"likelihood": None}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValidationError):
                    create_sample_risk(store, **kwargs)

    def test_create_risk_accepts_the_range_corners(self):
        """Core: Risk register. The 1..5 corners are legal: 1×1 = 1
        (low) and 5×5 = 25 (critical)."""
        store = fresh_store()
        low = create_sample_risk(store, title="low", likelihood=1, impact=1)
        self.assertEqual((low["score"], low["band"]), (1, "low"))
        high = create_sample_risk(store, title="high", likelihood=5,
                                  impact=5)
        self.assertEqual((high["score"], high["band"]), (25, "critical"))

    def test_create_risk_with_unknown_finding_id_is_validation_error(self):
        """Core: Risk register. Contract: 'every id in finding_ids
        must name an existing finding, else ValidationError'."""
        store, asset, finding = make_store()
        with self.assertRaises(ValidationError):
            create_sample_risk(
                store, finding_ids=[finding["id"], "find-999999"]
            )
        with self.assertRaises(ValidationError):
            create_sample_risk(store, finding_ids=["find-999999"])

    def test_viewer_cannot_create_a_risk(self):
        """Core: Risk register + Access control. create_risk takes
        action manage_risks, which viewer lacks."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            create_sample_risk(store, actor=VIEWER)

    def test_failed_create_consumes_no_id(self):
        """Core: Risk register. Contract: 'a failed operation consumes
        no id' — after a rejected create, the next successful risk
        still takes risk-1."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            create_sample_risk(store, likelihood=9)
        risk = create_sample_risk(store)
        self.assertEqual(risk["id"], "risk-1")

    def test_get_risk_roundtrip_and_unknown_is_not_found(self):
        """Core: Risk register. Contract: get_risk returns the risk
        dict (action read); an unknown id raises NotFoundError."""
        store = fresh_store()
        risk = create_sample_risk(store)
        got = store.get_risk(risk["id"], actor=VIEWER)
        self.assertEqual(got["id"], risk["id"])
        with self.assertRaises(NotFoundError):
            store.get_risk("risk-999999", actor=ANALYST)


class TestRiskTransitions(unittest.TestCase):
    """Core: Risk register — transition_risk per RISK_TRANSITIONS."""

    def setUp(self):
        self.store = fresh_store()

    def risk_in(self, status):
        """Create a risk and drive it to ``status`` legally."""
        risk = create_sample_risk(self.store)
        for step in PATH_TO[status]:
            risk = self.store.transition_risk(
                risk["id"], step, actor=ANALYST
            )
        self.assertEqual(risk["status"], status)
        return risk

    def test_transition_map_matches_the_contract(self):
        """Core: Risk register. Contract: RISK_TRANSITIONS is exactly
        {"open": {monitoring, treated, closed}, "monitoring": {open,
        treated, closed}, "treated": {monitoring, closed}, "closed":
        {open}}."""
        expected = {
            "open": {"monitoring", "treated", "closed"},
            "monitoring": {"open", "treated", "closed"},
            "treated": {"monitoring", "closed"},
            "closed": {"open"},
        }
        actual = {k: set(v) for k, v in RISK_TRANSITIONS.items()}
        self.assertEqual(actual, expected)

    def test_every_allowed_transition_succeeds(self):
        """Core: Risk register. Contract: transition_risk accepts
        every (from, to) pair in RISK_TRANSITIONS and returns the
        updated risk dict."""
        for source, target in ALLOWED:
            with self.subTest(source=source, target=target):
                risk = self.risk_in(source)
                updated = self.store.transition_risk(
                    risk["id"], target, actor=ANALYST
                )
                self.assertEqual(updated["status"], target)

    def test_closed_risk_can_reopen_to_open(self):
        """Core: Risk register. Contract: RISK_TRANSITIONS["closed"]
        is {"open"} — unlike findings, a closed risk reopens (a risk
        that resurfaces)."""
        risk = self.risk_in("closed")
        updated = self.store.transition_risk(
            risk["id"], "open", actor=ANALYST
        )
        self.assertEqual(updated["status"], "open")

    def test_forbidden_transitions_are_rejected(self):
        """Core: Risk register. Contract: transitions outside
        RISK_TRANSITIONS raise ValidationError — including
        treated → open (treated risks do not reopen directly) and
        same-status no-ops."""
        for source, target in FORBIDDEN:
            with self.subTest(source=source, target=target):
                risk = self.risk_in(source)
                with self.assertRaises(ValidationError):
                    self.store.transition_risk(
                        risk["id"], target, actor=ANALYST
                    )
                self.assertEqual(
                    self.store.get_risk(risk["id"], actor=ANALYST)
                    ["status"],
                    source,
                )

    def test_unknown_status_is_rejected(self):
        """Core: Risk register. Contract: a new_status outside
        RISK_STATUSES is a ValidationError."""
        risk = self.risk_in("open")
        with self.assertRaises(ValidationError):
            self.store.transition_risk(risk["id"], "ignored",
                                        actor=ANALYST)

    def test_transition_unknown_risk_is_not_found(self):
        """Core: Risk register. transition_risk on an unknown id
        raises NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.transition_risk("risk-999999", "closed",
                                        actor=ANALYST)

    def test_viewer_cannot_transition_a_risk(self):
        """Core: Risk register + Access control. transition_risk
        takes action manage_risks, which viewer lacks."""
        risk = self.risk_in("open")
        with self.assertRaises(PermissionDenied):
            self.store.transition_risk(risk["id"], "closed", actor=VIEWER)


class TestListRisks(unittest.TestCase):
    """Core: Risk register — list_risks filters and sort order."""

    def setUp(self):
        self.store = fresh_store()
        # Scores: alpha 20, beta 10, gamma 20 (tie with alpha), delta 5.
        self.alpha = create_sample_risk(
            self.store, title="Alpha breach", description="edge systems",
            likelihood=4, impact=5,
        )
        self.beta = create_sample_risk(
            self.store, title="Beta outage", description="single region",
            likelihood=2, impact=5,
        )
        self.gamma = create_sample_risk(
            self.store, title="Gamma breach", description="edge systems",
            likelihood=5, impact=4,
        )
        self.delta = create_sample_risk(
            self.store, title="Delta drift", description="config drift",
            likelihood=1, impact=5,
        )
        self.store.transition_risk(self.beta["id"], "monitoring",
                                   actor=ANALYST)

    def test_list_risks_sorts_by_score_desc_then_id_asc(self):
        """Core: Risk register. Contract: list_risks returns risks
        'sorted by score descending, then id ascending' — the two
        20-point risks come first in id order."""
        listed = self.store.list_risks(actor=ANALYST)
        self.assertEqual(
            [r["id"] for r in listed],
            [self.alpha["id"], self.gamma["id"], self.beta["id"],
             self.delta["id"]],
        )

    def test_list_risks_status_filter(self):
        """Core: Risk register. Contract: list_risks filters by
        status when given."""
        monitoring = self.store.list_risks(actor=ANALYST,
                                           status="monitoring")
        self.assertEqual([r["id"] for r in monitoring], [self.beta["id"]])
        opened = self.store.list_risks(actor=ANALYST, status="open")
        self.assertEqual(len(opened), 3)
        self.assertEqual(
            self.store.list_risks(actor=ANALYST, status="closed"), []
        )

    def test_list_risks_q_matches_title_and_description_case_insensitively(self):
        """Core: Risk register. Contract: list_risks q is a substring
        'over title and description', case-insensitive."""
        by_title = self.store.list_risks(actor=ANALYST, q="BREACH")
        self.assertEqual(
            {r["id"] for r in by_title},
            {self.alpha["id"], self.gamma["id"]},
        )
        by_desc = self.store.list_risks(actor=ANALYST, q="Region")
        self.assertEqual([r["id"] for r in by_desc], [self.beta["id"]])
        self.assertEqual(self.store.list_risks(actor=ANALYST, q="zzz"), [])


if __name__ == "__main__":
    unittest.main()
