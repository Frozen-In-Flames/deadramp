"""Final GAPS batch tests — GRC L3-adjacent addition surface
(second batch unit in this directory).

Traces to: GAPS.md section "Remainder Addition — GRC
L3-adjacent (+1 fork)", the Exiger addition's 2 registered
Extended entries, closed by ``src/grc/extensions_addition.py``
(see the group's BATCH-ADDITION.md for the per-entry
dispositions). The category doctrine binds the whole surface:
posture is counts only and **no score / rating / grade / percent
key exists anywhere** (the recursive scan below mirrors
``test_posture.py`` and the first batch unit's scan); reported
outcomes and values are recorded verbatim and never computed;
date-based status is derived at read, never stored; the
High-baseline adaptations (hash-chained audit, fail-closed
writes, auditor separation) hold on the addition surface exactly
as on the Core and the first unit's surface.
"""

import os
import tempfile
import unittest

import grc_helpers as H
from grc.audit import AuditLog
from grc.errors import (
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from grc.extensions_addition import (
    GrcExtensionsAddition,
    derive_third_party_review_status,
)
from grc.store import GrcStore  # noqa: F401  (fixture parity with unit 1)

FORBIDDEN_KEY_PARTS = ("score", "rating", "grade", "percent")


def assert_no_score_keys(case, node, path="$"):
    """Recursively assert no dict key anywhere in ``node`` mentions
    score / rating / grade / percent (the category doctrine, as
    enforced over the Core's posture output in test_posture.py)."""
    if isinstance(node, dict):
        for key, value in node.items():
            lowered = str(key).lower()
            for part in FORBIDDEN_KEY_PARTS:
                case.assertNotIn(
                    part, lowered,
                    "forbidden key part %r at %s.%s" % (part, path, key),
                )
            assert_no_score_keys(case, value, "%s.%s" % (path, key))
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            assert_no_score_keys(case, value, "%s[%d]" % (path, index))


def make_addition(audit=None):
    """Fresh core store (canonical fixture) + addition surface."""
    store, system, indicator = H.make_store(audit=audit)
    return GrcExtensionsAddition(store), store


class TestThirdPartyRecords(unittest.TestCase):
    """Idx 670 (registry half): third parties registered by opaque
    reference — the registry the fork's Third Party Management
    module presupposes. Registration researches nothing."""

    def test_registration_shape_and_no_research(self):
        """670: a registration record is pinned to exactly its
        eight bookkeeping keys and carries researched_here False —
        registering a third party investigates nothing about it."""
        ext, _ = make_addition()
        record = ext.register_third_party(
            "TP-100", H.MEMBER, system_ref=H.SYSTEM_REF,
            review_due_date="2026-06-30", note="carrier",
        )
        self.assertEqual(record["id"], "tpa-1")
        self.assertEqual(
            set(record.keys()),
            {"id", "third_party_ref", "system_ref", "review_due_date",
             "note", "researched_here", "recorded_by", "recorded_utc"},
        )
        self.assertIs(record["researched_here"], False)
        fetched = ext.get_third_party("tpa-1", H.VIEWER)
        self.assertEqual(fetched, record)

    def test_duplicate_ref_rejected_and_consumes_no_id(self):
        """670: a third-party reference is unique on this surface;
        a duplicate registration is rejected whole and the next
        distinct registration takes the next id."""
        ext, _ = make_addition()
        ext.register_third_party("TP-100", H.MEMBER)
        with self.assertRaises(ValidationError):
            ext.register_third_party("TP-100", H.MEMBER)
        record = ext.register_third_party("TP-200", H.MEMBER)
        self.assertEqual(record["id"], "tpa-2")

    def test_unknown_system_and_bad_date_consume_no_id(self):
        """670: an unknown governed system is NotFoundError and a
        malformed review due date is a validation error; neither
        consumes an id."""
        ext, _ = make_addition()
        with self.assertRaises(NotFoundError):
            ext.register_third_party("TP-100", H.MEMBER, system_ref="SYS-404")
        with self.assertRaises(ValidationError):
            ext.register_third_party(
                "TP-100", H.MEMBER, review_due_date="30/06/2026",
            )
        record = ext.register_third_party("TP-100", H.MEMBER)
        self.assertEqual(record["id"], "tpa-1")

    def test_review_status_is_derived_never_stored(self):
        """670: a third party with review due 2026-06-30 derives
        "current" on the due date and "review_overdue" after it;
        a record with no due date is always current; the stored
        record carries no derived key (the Core's
        finding-derivation discipline, applied here)."""
        ext, _ = make_addition()
        record = ext.register_third_party(
            "TP-100", H.MEMBER, review_due_date="2026-06-30",
        )
        stored = ext.get_third_party(record["id"], H.VIEWER)
        self.assertNotIn("derived_status", stored)
        on_due = ext.get_third_party(record["id"], H.VIEWER, as_of="2026-06-30")
        self.assertEqual(on_due["derived_status"], "current")
        past_due = ext.get_third_party(record["id"], H.VIEWER, as_of="2026-07-01")
        self.assertEqual(past_due["derived_status"], "review_overdue")
        undated = ext.register_third_party("TP-200", H.MEMBER)
        far_future = ext.get_third_party(undated["id"], H.VIEWER, as_of="2030-01-01")
        self.assertEqual(far_future["derived_status"], "current")

    def test_registration_permissions(self):
        """670: registration rides on governed systems
        (manage_systems) — viewer and auditor are denied; the
        auditor (AC-5) may not even read the records back."""
        ext, _ = make_addition()
        with self.assertRaises(PermissionDenied):
            ext.register_third_party("TP-100", H.VIEWER)
        with self.assertRaises(PermissionDenied):
            ext.register_third_party("TP-100", H.AUDITOR)
        record = ext.register_third_party("TP-100", H.MEMBER)
        with self.assertRaises(PermissionDenied):
            ext.get_third_party(record["id"], H.AUDITOR)
        with self.assertRaises(PermissionDenied):
            ext.list_third_parties(H.AUDITOR)


class TestDiligenceRecords(unittest.TestCase):
    """Idx 670 (diligence half): due-diligence records — the
    reported outcome of diligence performed elsewhere (the fork's
    Due Diligence Intelligence engine), stored verbatim against a
    registered third party, optionally linked to the Core
    evidence record the diligence produced."""

    def test_outcome_verbatim_and_evidence_link(self):
        """670: a diligence outcome is stored verbatim exactly as
        reported (vendor wording, mixed case), with
        researched_here False; a linked Core evidence record is
        the artifact the diligence produced — the record this
        surface keeps is the link, not the artifact."""
        ext, store = make_addition()
        tp = ext.register_third_party("TP-100", H.MEMBER)
        evidence = store.create_evidence(
            "diligence report", "report-body", ["IA-2"], [H.SYSTEM_REF],
            actor=H.MEMBER,
        )
        record = ext.record_diligence(
            tp["id"], "initial diligence", "Cleared WITH conditions (vendor wording)",
            H.MEMBER, evidence_id=evidence["id"],
        )
        self.assertEqual(record["id"], "ddq-1")
        self.assertEqual(
            record["outcome_label"], "Cleared WITH conditions (vendor wording)",
        )
        self.assertEqual(record["evidence_id"], evidence["id"])
        self.assertIs(record["researched_here"], False)

    def test_diligence_validation_consumes_no_id(self):
        """670: diligence against an unknown third party or an
        unknown evidence record is NotFoundError, an empty kind
        or outcome is a validation error, and none consumes an
        id."""
        ext, _ = make_addition()
        tp = ext.register_third_party("TP-100", H.MEMBER)
        with self.assertRaises(NotFoundError):
            ext.record_diligence("tpa-404", "initial", "ok", H.MEMBER)
        with self.assertRaises(NotFoundError):
            ext.record_diligence(tp["id"], "initial", "ok", H.MEMBER,
                                 evidence_id="ev-404")
        with self.assertRaises(ValidationError):
            ext.record_diligence(tp["id"], "initial", "", H.MEMBER)
        record = ext.record_diligence(tp["id"], "initial", "ok", H.MEMBER)
        self.assertEqual(record["id"], "ddq-1")

    def test_diligence_permissions(self):
        """670: recording diligence is recorded work
        (record_results) — viewer and auditor are denied, and the
        auditor may not read the records back."""
        ext, _ = make_addition()
        tp = ext.register_third_party("TP-100", H.MEMBER)
        with self.assertRaises(PermissionDenied):
            ext.record_diligence(tp["id"], "initial", "ok", H.VIEWER)
        with self.assertRaises(PermissionDenied):
            ext.record_diligence(tp["id"], "initial", "ok", H.AUDITOR)
        ext.record_diligence(tp["id"], "initial", "ok", H.MEMBER)
        with self.assertRaises(PermissionDenied):
            ext.list_diligence(H.AUDITOR)


class TestSupplyObservations(unittest.TestCase):
    """Idx 671: supply-chain observation records — a dimension
    label and a reported value, both verbatim, recorded against a
    registered third party. Nothing is measured here and no value
    is computed from another; the entry's own registration says
    no score follows from "Analytics"."""

    def test_observation_labels_verbatim_never_measured(self):
        """671: the reported value is held as the label it was
        reported as — never parsed into a number or rolled up —
        with measured_here / computed_here False on the record."""
        ext, _ = make_addition()
        tp = ext.register_third_party("TP-100", H.MEMBER)
        record = ext.record_supply_observation(
            tp["id"], "lead time", "14 days (carrier reported)", H.MEMBER,
            system_ref=H.SYSTEM_REF, source_ref="sdx-feed",
        )
        self.assertEqual(record["id"], "sco-1")
        self.assertEqual(record["reported_label"], "14 days (carrier reported)")
        self.assertIsInstance(record["reported_label"], str)
        self.assertIs(record["measured_here"], False)
        self.assertIs(record["computed_here"], False)

    def test_observation_requires_registered_third_party(self):
        """671: an observation against an unregistered third
        party or an unknown governed system is NotFoundError and
        consumes no id — visibility records attach to the
        registry, not to free-floating references."""
        ext, _ = make_addition()
        with self.assertRaises(NotFoundError):
            ext.record_supply_observation("tpa-404", "lead time", "x", H.MEMBER)
        tp = ext.register_third_party("TP-100", H.MEMBER)
        with self.assertRaises(NotFoundError):
            ext.record_supply_observation(
                tp["id"], "lead time", "x", H.MEMBER, system_ref="SYS-404",
            )
        record = ext.record_supply_observation(tp["id"], "lead time", "x", H.MEMBER)
        self.assertEqual(record["id"], "sco-1")

    def test_observation_filters(self):
        """671: observations list filtered by third party and by
        verbatim dimension label."""
        ext, _ = make_addition()
        first = ext.register_third_party("TP-100", H.MEMBER)
        second = ext.register_third_party("TP-200", H.MEMBER)
        ext.record_supply_observation(first["id"], "lead time", "a", H.MEMBER)
        ext.record_supply_observation(first["id"], "capacity", "b", H.MEMBER)
        ext.record_supply_observation(second["id"], "lead time", "c", H.MEMBER)
        self.assertEqual(
            len(ext.list_supply_observations(H.VIEWER, third_party_id=first["id"])),
            2,
        )
        self.assertEqual(
            len(ext.list_supply_observations(H.VIEWER, dimension_label="lead time")),
            2,
        )


class TestThirdPartyView(unittest.TestCase):
    """Idx 670 + 671 (derived view): the per-third-party view
    derives its counts and its latest diligence outcome at read
    from this surface's own records; the stored record never
    gains a figure."""

    def test_view_derives_counts_and_latest_outcome(self):
        """670/671: the view tracks registry state — records added
        after registration appear in the next view (diligence
        count, latest outcome by recording order, observation
        count, derived review status) — while the stored record
        keeps exactly its registration keys."""
        ext, _ = make_addition()
        tp = ext.register_third_party(
            "TP-100", H.MEMBER, review_due_date="2026-06-30",
        )
        empty = ext.third_party_view(tp["id"], H.VIEWER, as_of="2026-07-01")
        self.assertEqual(empty["diligence_count"], 0)
        self.assertIsNone(empty["latest_diligence_outcome"])
        self.assertEqual(empty["supply_observation_count"], 0)
        self.assertEqual(empty["derived_status"], "review_overdue")
        ext.record_diligence(tp["id"], "initial diligence", "cleared", H.MEMBER)
        ext.record_diligence(tp["id"], "periodic review", "escalated", H.MEMBER)
        ext.record_supply_observation(tp["id"], "lead time", "14 days", H.MEMBER)
        view = ext.third_party_view(tp["id"], H.VIEWER)
        self.assertEqual(view["diligence_count"], 2)
        self.assertEqual(view["latest_diligence_outcome"], "escalated")
        self.assertEqual(view["supply_observation_count"], 1)
        stored = ext.get_third_party(tp["id"], H.VIEWER)
        for key in ("diligence_count", "latest_diligence_outcome",
                    "supply_observation_count", "derived_status"):
            self.assertNotIn(key, stored)


class TestAdditionSummary(unittest.TestCase):
    """Idx 671 (analytics half): the addition summary is the
    Core's counts-only posture discipline applied to this
    surface's own records — counts of records and of their
    verbatim labels, derived at read. It is the whole of the
    "analytics" this substrate performs over the recorded
    observations."""

    def test_summary_counts_only_and_derived_status_buckets(self):
        """671: counts by derived review status flip with the
        as-of date over the same stored records; diligence counts
        by verbatim kind and outcome; observation counts by
        verbatim dimension — and nothing else is produced."""
        ext, _ = make_addition()
        due = ext.register_third_party(
            "TP-100", H.MEMBER, review_due_date="2026-06-30",
        )
        ext.register_third_party("TP-200", H.MEMBER)
        ext.record_diligence(due["id"], "initial diligence", "cleared", H.MEMBER)
        ext.record_diligence(due["id"], "periodic review", "cleared", H.MEMBER)
        ext.record_supply_observation(due["id"], "lead time", "a", H.MEMBER)
        ext.record_supply_observation(due["id"], "lead time", "b", H.MEMBER)
        summary = ext.addition_summary(H.ADMIN, as_of="2026-06-30")
        self.assertEqual(summary["third_parties"]["total"], 2)
        self.assertEqual(
            summary["third_parties"]["by_review_status"],
            {"current": 2, "review_overdue": 0},
        )
        self.assertEqual(summary["diligence"]["total"], 2)
        self.assertEqual(
            summary["diligence"]["by_kind"],
            {"initial diligence": 1, "periodic review": 1},
        )
        self.assertEqual(summary["diligence"]["by_outcome"], {"cleared": 2})
        self.assertEqual(summary["supply_observations"]["total"], 2)
        self.assertEqual(
            summary["supply_observations"]["by_dimension"], {"lead time": 2},
        )
        later = ext.addition_summary(H.ADMIN, as_of="2026-07-01")
        self.assertEqual(
            later["third_parties"]["by_review_status"],
            {"current": 1, "review_overdue": 1},
        )


class TestAdditionInvariants(unittest.TestCase):
    """Cross-surface doctrine pins for the addition: the no-score
    recursive scan over every record type, view, and the summary;
    addition writes joining the Core's hash-chained audit and
    failing closed; the auditor denied every addition operation
    while its core audit duty works; and the Trust Center ruling
    carried to this surface — recording on it creates no Core
    indicator result, evidence, or finding."""

    def _exercise(self, ext):
        tp = ext.register_third_party(
            "TP-100", H.MEMBER, system_ref=H.SYSTEM_REF,
            review_due_date="2026-06-30",
        )
        ext.record_diligence(tp["id"], "initial diligence", "cleared", H.MEMBER)
        ext.record_supply_observation(tp["id"], "lead time", "14 days", H.MEMBER)
        return tp

    def test_no_score_keys_anywhere_on_the_addition_surface(self):
        """Doctrine: no key mentioning score / rating / grade /
        percent exists on any addition record, view, or the
        addition summary — the Core's posture scan, extended to
        this surface. (The addition fork's "Analytics" module
        name licenses counts of records, never a score.)"""
        ext, _ = make_addition()
        tp = self._exercise(ext)
        surfaces = [
            ext.list_third_parties(H.ADMIN, as_of="2026-07-01"),
            ext.list_diligence(H.ADMIN),
            ext.list_supply_observations(H.ADMIN),
            ext.third_party_view(tp["id"], H.ADMIN, as_of="2026-07-01"),
            ext.addition_summary(H.ADMIN, as_of="2026-07-01"),
        ]
        for surface in surfaces:
            assert_no_score_keys(self, surface)

    def test_addition_writes_join_the_hash_chained_audit(self):
        """AU-9: addition mutations are entries in the same
        hash-chained audit log as the Core's (exta_ action names),
        and the chain still verifies with them in it."""
        audit = AuditLog()
        ext, store = make_addition(audit=audit)
        self._exercise(ext)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("exta_third_party_create", actions)
        self.assertIn("exta_diligence_create", actions)
        self.assertIn("exta_supply_observation_create", actions)
        self.assertEqual(audit.verify_chain(), (True, None))

    def test_addition_write_fails_closed(self):
        """AU-5: when the audit write fails, the addition
        operation raises AuditWriteError, records nothing, and
        consumes no id — the repaired log's next successful write
        takes the id the failed one would have taken."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            ext, store = make_addition(audit=audit)
            if os.path.exists(path):
                os.remove(path)
            os.mkdir(path)
            with self.assertRaises(AuditWriteError):
                ext.register_third_party("TP-100", H.MEMBER)
            self.assertEqual(ext.list_third_parties(H.ADMIN), [])
            os.rmdir(path)
            record = ext.register_third_party("TP-100", H.MEMBER)
            self.assertEqual(record["id"], "tpa-1")
            self.assertEqual(audit.verify_chain(), (True, None))

    def test_auditor_denied_everywhere_but_core_audit_duty_works(self):
        """AC-5: the auditor role is denied every addition
        operation — writes and reads alike — while its core audit
        duty (the hash-chained trail over Core and addition
        entries alike) verifies unchanged."""
        ext, store = make_addition()
        tp = self._exercise(ext)
        with self.assertRaises(PermissionDenied):
            ext.register_third_party("TP-200", H.AUDITOR)
        with self.assertRaises(PermissionDenied):
            ext.record_diligence(tp["id"], "review", "ok", H.AUDITOR)
        with self.assertRaises(PermissionDenied):
            ext.record_supply_observation(tp["id"], "lead time", "x", H.AUDITOR)
        with self.assertRaises(PermissionDenied):
            ext.get_third_party(tp["id"], H.AUDITOR)
        with self.assertRaises(PermissionDenied):
            ext.third_party_view(tp["id"], H.AUDITOR)
        with self.assertRaises(PermissionDenied):
            ext.addition_summary(H.AUDITOR)
        self.assertEqual(store.audit.verify_chain(), (True, None))
        self.assertTrue(len(store.audit.entries()) > 0)

    def test_addition_records_create_no_core_records(self):
        """Trust Center ruling, carried here: recording on the
        addition surface creates NO Core record — the Core's
        posture summary (findings, evidence, indicator results,
        and every other count) is byte-identical before and after
        a full addition flow. Diligence findings land in the Core
        only when a person files them there through the Core's
        own operations."""
        ext, store = make_addition()
        before = store.posture_summary(H.ADMIN, as_of="2026-07-01")
        self._exercise(ext)
        after = store.posture_summary(H.ADMIN, as_of="2026-07-01")
        self.assertEqual(before, after)
        self.assertEqual(store.list_findings(H.ADMIN), [])
        self.assertEqual(store.list_evidence(H.ADMIN), [])
        self.assertEqual(store.list_indicator_results(H.ADMIN), [])


class TestReviewDerivationNegativeControl(unittest.TestCase):
    """Fresh negative control for this unit's new derivation.

    The traced claim: a third-party record with review due
    2026-06-30 derives "current" at as_of 2026-06-30 and
    "review_overdue" at as_of 2026-07-01. The mutant — the
    derivation with its overdue branch disabled — collapses both
    to "current".
    """

    RECORD = {"third_party_ref": "TP-NC", "review_due_date": "2026-06-30"}

    @staticmethod
    def _mutant_derive(record, as_of=None):
        """The mutant: _third_party_review_is_overdue disabled, so
        the overdue branch never fires (mirrors the live drill in
        tests/README.md, which patches the real function)."""
        return "current"

    def test_real_derivation_separates_the_canonical_pair(self):
        """The real derive_third_party_review_status separates
        on-due-date from past-due-date for a dated record."""
        self.assertEqual(
            derive_third_party_review_status(self.RECORD, as_of="2026-06-30"),
            "current",
        )
        self.assertEqual(
            derive_third_party_review_status(self.RECORD, as_of="2026-07-01"),
            "review_overdue",
        )

    def test_mutant_collapses_the_pair(self):
        """The mutant reads "current" at both dates — it cannot
        produce "review_overdue" — and treating its output as the
        expected past-due outcome fails."""
        self.assertEqual(
            self._mutant_derive(self.RECORD, as_of="2026-07-01"), "current",
        )
        with self.assertRaises(AssertionError):
            self.assertEqual(
                self._mutant_derive(self.RECORD, as_of="2026-07-01"),
                "review_overdue",
            )

    def test_end_to_end_through_the_addition(self):
        """End-to-end arm: the same separation through the
        addition's read views (get_third_party with as_of)."""
        ext, _ = make_addition()
        tp = ext.register_third_party(
            "TP-NC", H.MEMBER, review_due_date="2026-06-30",
        )
        self.assertEqual(
            ext.get_third_party(tp["id"], H.VIEWER, as_of="2026-06-30")
            ["derived_status"],
            "current",
        )
        self.assertEqual(
            ext.get_third_party(tp["id"], H.VIEWER, as_of="2026-07-01")
            ["derived_status"],
            "review_overdue",
        )


if __name__ == "__main__":
    unittest.main()
