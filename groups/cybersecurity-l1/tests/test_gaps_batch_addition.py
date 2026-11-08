"""Final GAPS batch, second unit — Cybersecurity L1 addition surface.

Traces to: the 1 open entry of the "Remainder Addition —
Cybersecurity L1 (+1 fork)" section in the repo-root GAPS.md
(idx 662) and to gaps-batch/DECISION.md.

Entry idx 662: "Crowdsourced security testing & disclosure
coordination platform: researcher-community marketplace,
engagement management, and disclosure coordination (registered
from the fork's described function; no taxonomy family exists for
it — vulnerability management is scanning tooling and application
security is testing engines, and a human researcher marketplace is
neither. The findings its engagements produce are ingestible by
the Core today)" — drafted stub-engine, closed as drafted: a
labeled reference implementation. Every record on this surface
carries ``reference_stub: true``; no marketplace is operated, no
researcher is recruited or matched, nothing is tested, and no
disclosure is coordinated. The findings engagements produce are
named by opaque reference only and are never created here — they
remain ingestible by the founding Core, unchanged.
"""

import unittest

from cyber_helpers import ADMIN, ANALYST, VIEWER  # noqa: F401  (path setup)

from cyber.audit import AuditLog
from cyber.errors import NotFoundError, PermissionDenied, ValidationError
from cyber.extensions_addition import ExtensionAdditionStore


def fresh_add(audit=None):
    if audit is None:
        audit = AuditLog()
    return ExtensionAdditionStore(audit=audit), audit


def _all_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            keys |= _all_keys(value)
    return keys


def make_program(add, actor=ANALYST):
    return add.register_program(
        "prog-public-web", "Public web disclosure program",
        "scope-web-assets", actor=actor)


def make_engagement(add, program_id, actor=ANALYST):
    return add.create_engagement(
        program_id, "eng-website-review", "researcher-001", actor=actor)


class TestProgramRecords(unittest.TestCase):
    """idx 662, program half: the marketplace/coordination platform
    as labeled reference records."""

    def test_program_record_is_labeled_reference(self):
        add, _ = fresh_add()
        program = make_program(add)
        self.assertEqual(program["id"], "program-1")
        self.assertTrue(program["reference_stub"])
        self.assertFalse(program["marketplace_operated_here"])
        self.assertFalse(program["researchers_recruited_here"])
        self.assertFalse(program["coordinated_here"])
        programs = add.list_programs(actor=VIEWER)
        self.assertEqual(len(programs), 1)

    def test_address_shaped_refs_rejected(self):
        add, _ = fresh_add()
        for bad in ("10.0.0.1", "https://example.org/x", "host.example.org",
                    "has space"):
            with self.assertRaises(ValidationError):
                add.register_program(bad, "Title", "scope-a", actor=ANALYST)
            with self.assertRaises(ValidationError):
                add.register_program("prog-a", "Title", bad, actor=ANALYST)
        # No rejected registration consumed an id.
        program = make_program(add)
        self.assertEqual(program["id"], "program-1")


class TestEngagements(unittest.TestCase):
    """idx 662, engagement half: engagement management as reference
    records over opaque researcher references."""

    def test_engagement_lifecycle(self):
        add, _ = fresh_add()
        program = make_program(add)
        engagement = make_engagement(add, program["id"])
        self.assertEqual(engagement["id"], "eng-1")
        self.assertEqual(engagement["status"], "invited")
        self.assertTrue(engagement["reference_stub"])
        self.assertFalse(engagement["matched_here"])
        self.assertFalse(engagement["tested_here"])
        active = add.transition_engagement(engagement["id"], "active", actor=ANALYST)
        self.assertEqual(active["status"], "active")
        done = add.transition_engagement(engagement["id"], "completed", actor=ANALYST)
        self.assertEqual(done["status"], "completed")

    def test_engagement_requires_registered_program(self):
        add, _ = fresh_add()
        with self.assertRaises(NotFoundError):
            add.create_engagement(
                "program-99", "eng-a", "researcher-001", actor=ANALYST)

    def test_engagement_invalid_transition_rejected(self):
        add, _ = fresh_add()
        program = make_program(add)
        engagement = make_engagement(add, program["id"])
        with self.assertRaises(ValidationError):
            add.transition_engagement(engagement["id"], "completed", actor=ANALYST)
        # The rejected transition changed nothing.
        engagements = add.list_engagements(actor=ADMIN, status="invited")
        self.assertEqual(len(engagements), 1)


class TestDisclosures(unittest.TestCase):
    """idx 662, disclosure half: disclosure coordination as
    reference records; outcomes verbatim as reported; findings
    named by opaque reference only, never created here."""

    def test_disclosure_record_and_lifecycle(self):
        add, _ = fresh_add()
        program = make_program(add)
        engagement = make_engagement(add, program["id"])
        disclosure = add.record_disclosure(
            engagement["id"], "finding-ext-1", "confirmed_valid", actor=ANALYST)
        self.assertEqual(disclosure["id"], "disc-1")
        self.assertEqual(disclosure["status"], "reported")
        self.assertEqual(disclosure["reported_label"], "confirmed_valid")
        self.assertTrue(disclosure["reference_stub"])
        self.assertFalse(disclosure["coordinated_here"])
        triaged = add.transition_disclosure(disclosure["id"], "triaged", actor=ANALYST)
        self.assertEqual(triaged["status"], "triaged")
        disclosed = add.transition_disclosure(
            disclosure["id"], "disclosed", actor=ANALYST)
        self.assertEqual(disclosed["status"], "disclosed")

    def test_disclosure_requires_registered_engagement(self):
        add, _ = fresh_add()
        with self.assertRaises(NotFoundError):
            add.record_disclosure(
                "eng-99", "finding-ext-1", "confirmed_valid", actor=ANALYST)

    def test_disclosure_invalid_transition_rejected(self):
        add, _ = fresh_add()
        program = make_program(add)
        engagement = make_engagement(add, program["id"])
        disclosure = add.record_disclosure(
            engagement["id"], "finding-ext-1", "needs_more_info", actor=ANALYST)
        with self.assertRaises(ValidationError):
            add.transition_disclosure(disclosure["id"], "disclosed", actor=ANALYST)

    def test_address_shaped_finding_ref_rejected(self):
        add, _ = fresh_add()
        program = make_program(add)
        engagement = make_engagement(add, program["id"])
        with self.assertRaises(ValidationError):
            add.record_disclosure(
                engagement["id"], "203.0.113.7", "confirmed_valid", actor=ANALYST)
        # The rejected record consumed no id.
        disclosure = add.record_disclosure(
            engagement["id"], "finding-ext-1", "confirmed_valid", actor=ANALYST)
        self.assertEqual(disclosure["id"], "disc-1")


class TestDerivedViews(unittest.TestCase):
    """Derived views: counts and latest labels at read; stored
    records carry no derived keys."""

    def _history(self, add):
        program = make_program(add)
        engagement = make_engagement(add, program["id"])
        add.record_disclosure(
            engagement["id"], "finding-ext-1", "needs_more_info", actor=ANALYST)
        add.record_disclosure(
            engagement["id"], "finding-ext-2", "confirmed_valid", actor=ANALYST)
        return program, engagement

    def test_program_view_derives_counts_and_latest(self):
        add, _ = fresh_add()
        program, _ = self._history(add)
        view = add.program_view(actor=VIEWER, program_id=program["id"])
        self.assertEqual(view["engagement_count"], 1)
        self.assertEqual(view["engagements_by_status"], {"invited": 1})
        self.assertEqual(view["disclosure_count"], 2)
        self.assertEqual(view["latest_disclosure_label"], "confirmed_valid")

    def test_engagement_view_derives_latest(self):
        add, _ = fresh_add()
        _, engagement = self._history(add)
        view = add.engagement_view(actor=VIEWER, engagement_id=engagement["id"])
        self.assertEqual(view["disclosure_count"], 2)
        self.assertEqual(view["latest_disclosure_label"], "confirmed_valid")

    def test_stored_records_carry_no_derived_keys(self):
        add, _ = fresh_add()
        program, engagement = self._history(add)
        stored_program = add.list_programs(actor=ADMIN)[0]
        for key in ("engagement_count", "engagements_by_status",
                    "disclosure_count", "latest_disclosure_label"):
            self.assertNotIn(key, stored_program)
        stored_engagement = add.list_engagements(actor=ADMIN)[0]
        for key in ("disclosure_count", "latest_disclosure_label"):
            self.assertNotIn(key, stored_engagement)
        self.assertEqual(stored_engagement["id"], engagement["id"])

    def test_empty_program_view_latest_is_none(self):
        add, _ = fresh_add()
        program = make_program(add)
        view = add.program_view(actor=VIEWER, program_id=program["id"])
        self.assertEqual(view["disclosure_count"], 0)
        self.assertIsNone(view["latest_disclosure_label"])


class TestLatestLabelNegativeControl(unittest.TestCase):
    """Fresh negative control: the latest-label seam
    ``ExtensionAdditionStore._latest_label``. The canonical rule is
    that a view's current reported label is the *last* disclosure
    reported. An earliest-reading mutant must disagree, and treating
    the mutant's reading as the expectation must fail. Verified by
    live mutation in this tree (recorded in tests/README.md)."""

    def _history(self, add):
        program = make_program(add)
        engagement = make_engagement(add, program["id"])
        add.record_disclosure(
            engagement["id"], "finding-ext-1", "needs_more_info", actor=ANALYST)
        add.record_disclosure(
            engagement["id"], "finding-ext-2", "confirmed_valid", actor=ANALYST)
        return program

    def test_canonical_view_uses_latest_outcome(self):
        add, _ = fresh_add()
        program = self._history(add)
        view = add.program_view(actor=VIEWER, program_id=program["id"])
        self.assertEqual(view["latest_disclosure_label"], "confirmed_valid")

    def test_seam_directly(self):
        add, _ = fresh_add()
        records = [{"reported_label": "first"}, {"reported_label": "second"}]
        self.assertEqual(
            add._latest_label(records, "reported_label"), "second")

    def test_mutant_earliest_differs(self):
        class EarliestStore(ExtensionAdditionStore):
            def _latest_label(self, records, key):
                return records[0][key]

        canonical, _ = fresh_add()
        program = self._history(canonical)
        canonical_latest = canonical.program_view(
            actor=VIEWER, program_id=program["id"])["latest_disclosure_label"]

        mutant = EarliestStore(audit=AuditLog())
        m_program = self._history(mutant)
        mutant_latest = mutant.program_view(
            actor=VIEWER, program_id=m_program["id"])["latest_disclosure_label"]

        self.assertEqual(canonical_latest, "confirmed_valid")
        self.assertEqual(mutant_latest, "needs_more_info")
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_latest, canonical_latest)


class TestAccessAuditAndSummary(unittest.TestCase):
    """Cross-cutting: founding permission matrix, audited denials,
    counts-only summary, reference labels on every record."""

    def test_viewer_cannot_register_and_denial_is_audited(self):
        add, audit = fresh_add()
        with self.assertRaises(PermissionDenied):
            add.register_program(
                "prog-a", "Title", "scope-a", actor=VIEWER)
        denied = [e for e in audit.entries()
                  if e["action"] == "exta_program_register:denied"]
        self.assertEqual(len(denied), 1)
        # The denial consumed no id.
        program = make_program(add)
        self.assertEqual(program["id"], "program-1")

    def test_viewer_can_read(self):
        add, _ = fresh_add()
        make_program(add)
        self.assertEqual(len(add.list_programs(actor=VIEWER)), 1)

    def test_every_record_is_a_labeled_reference(self):
        add, _ = fresh_add()
        program = make_program(add)
        engagement = make_engagement(add, program["id"])
        add.record_disclosure(
            engagement["id"], "finding-ext-1", "confirmed_valid", actor=ANALYST)
        records = (add.list_programs(actor=ADMIN)
                   + add.list_engagements(actor=ADMIN)
                   + add.list_disclosures(actor=ADMIN))
        self.assertEqual(len(records), 3)
        for record in records:
            self.assertTrue(record["reference_stub"])

    def test_addition_summary_counts_only(self):
        add, _ = fresh_add()
        program = make_program(add)
        engagement = make_engagement(add, program["id"])
        add.record_disclosure(
            engagement["id"], "finding-ext-1", "confirmed_valid", actor=ANALYST)
        summary = add.addition_summary(actor=VIEWER)
        self.assertEqual(summary["records"],
                         {"programs": 1, "engagements": 1, "disclosures": 1})
        self.assertEqual(summary["total"], 3)
        for key in _all_keys(summary):
            self.assertNotIn("score", key)
            self.assertNotIn("rate", key)
            self.assertNotIn("grade", key)

    def test_no_score_anywhere_on_the_surface(self):
        add, _ = fresh_add()
        program = make_program(add)
        engagement = make_engagement(add, program["id"])
        add.record_disclosure(
            engagement["id"], "finding-ext-1", "confirmed_valid", actor=ANALYST)
        surface = (add.list_programs(actor=ADMIN)
                   + add.list_engagements(actor=ADMIN)
                   + add.list_disclosures(actor=ADMIN)
                   + [add.program_view(actor=ADMIN, program_id=program["id"])]
                   + [add.addition_summary(actor=ADMIN)])
        for key in _all_keys(surface):
            self.assertNotIn("score", key)


if __name__ == "__main__":
    unittest.main()
