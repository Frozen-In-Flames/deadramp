"""Remainder addition (unit addition:learning-management-l2):
spec integrity and substrate cases for the 1 addition fork.

Traces to: ADDENDUM.md for Group 48 (Learning Management,
CMMC L2). The previously uncategorized fork (Skillsoft /
Percipio) was spec'd under the group's EXISTING 26-family
taxonomy applied verbatim — the additions extractor parses the
TAXONOMY literal out of the shipped ``scratch/extract.py`` via
``ast`` (parsed, never executed, never re-typed) and reproduces
the original fork's shipped claim table exactly (26 claims,
evidence included) before tagging the newcomer. The original
extractor carries no CORRECTIONS literal: its wording-artifact
corrections are prose in its docstring, applied by the same
reasoning, with the mechanical parts asserted (only
``service_desc`` is matched; the newcomer's
``certified_services`` is empty; the description's final
scope-exclusion sentence contributes zero raw hits, asserted,
so the matched text is the full text and nothing was removed).

The newcomer claims **0 families** — a zero-claim fork. Its
545-character description asserts a learning experience
platform in substance (it "authenticates users, tracks
learner's progress, and connects users to content"), but none
of the taxonomy's 26 verbatim pattern phrases appears in it:
the raw hit count is 0 across all 26 families, every sentence.
The group total stays 26 claims (1 of 2 forks claiming). The
single census citation verifies verbatim — it is the
description's first sentence — and tags nothing: verification
is not a claim, and census classification is not a claim
either, in either direction. The taxonomy has no assessment,
credential, or scoring family (the singleton's checked
absences); Percipio names "assessments" as catalogue content,
which changes none of that at claim level — the absences are
rechecked below, token by token.

Neither claim nor absence extends the core: ``src/`` is
byte-identical, and the category invariants hold — statement
records keep their exact eight-key shape with no score field
anywhere (scanned recursively in the substrate case below),
compliance status is derived never stored, and the workflow
registry never executes. The substrate cases exercise the
shipped core as the newcomer would use it: a learner's
progress record and a compliance assignment whose status is
derived at read (Core 7 + Core 9 — that assertion trips the
group's signature ``_derive_status`` drill by exactly one; see
tests/README.md), and catalogue content records with an LRS
statement over one of them (Core 2 + Core 8). The fork's
delivery runtime, its licensed content library, and its lab
environments are Extended (ADDENDUM section 5), not
implemented, and nothing in these cases claims them.
Category boundary: nothing here imports Education & Training
functions; this is the Learning Management taxonomy only.
"""

import json
import os
import re
import unittest

from lms_helpers import ADMIN, INSTRUCTOR, fresh_store, make_store

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

ORIGINAL_ORDER = [
    "F1405214357",   # PowerTrain Inc. — PowerTrain Government
                     # Learning Enclave - SaaS
]
UNIT_ORDER = [
    "FR2118043605",  # Skillsoft — Percipio
]

ALL_FAMILIES = [
    "hosting_platform",
    "identity_authentication",
    "learning_content_delivery",
    "ehri_data_collection_reporting",
    "training_authorization_forms",
    "individual_development_plans",
    "event_registration",
    "adjustable_workflow",
    "waitlist_management",
    "automated_notifications",
    "competency_management",
    "lesson_plans",
    "mandatory_training_compliance",
    "reporting",
    "multi_tenancy",
    "career_mapping",
    "succession_planning",
    "candidate_review",
    "employee_surveys",
    "knowledge_base_wiki",
    "web_cms_platform",
    "learning_experience_records",
    "learner_activity_tracking",
    "learning_analytics",
    "content_standards_distribution",
    "learning_content_management",
]

ORIGINAL_CLAIMS = {
    "F1405214357": ALL_FAMILIES,
}

# The literal claim table for the addition: zero claims.
EXPECTED_CLAIMS = {
    "FR2118043605": [],
}

NEWCOMER_DESCRIPTION = (
    "Skillsoft's Percipio is a SaaS learning experience "
    "platform that authenticates users, tracks learner's "
    "progress, and connects users to content and other "
    "optional services. Percipio offers 1000s of video-based "
    "courses along with ebooks, audiobooks, practice labs, "
    "boot camps, and assessments to help your workforce build "
    "skills. Percipio is accessible from both a web browser "
    "as well as Apple and Andriod mobile apps. The learning "
    "platform and mobile apps were assessed as in-boundary "
    "for FedRAMP. The external content providers are not "
    "assessed."
)

STATEMENT_KEYS = {
    "id", "learner_ref", "verb", "object_ref",
    "context", "result_text", "recorded_by", "recorded_utc",
}


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _sheet(specs, fork_id):
    return next(s for s in specs if s["fork_id"] == fork_id)


def _raw_product(fork_id):
    with open(os.path.join(_REPO_ROOT, "raw", "data_dump.json")) as fh:
        dump = json.load(fh)
    prods = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
    return {p["id"]: p for p in prods}[fork_id]


def _score_keys(obj):
    """Keys that would constitute a score field: exactly
    'score', or starting 'score_' / ending '_score'
    (case-insensitive) — the group's pinned definition."""
    bad = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = str(key).lower()
            if (lowered == "score" or lowered.startswith("score_")
                    or lowered.endswith("_score")):
                bad.add(key)
            bad |= _score_keys(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            bad |= _score_keys(value)
    return bad


class TestAdditionSpecIntegrity(unittest.TestCase):
    """ADDENDUM sections 1/2: membership, order, literal claim
    table, verbatim description, census citation accounting,
    exclusion accounting, absence rechecks, near-miss pins."""

    def test_sheet_count_and_order(self):
        """2 sheets: the shipped singleton untouched in place,
        then the addition in census unit order."""
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs],
                         ORIGINAL_ORDER + UNIT_ORDER)

    def test_membership_matches_remainder_unit(self):
        """The appended sheet is exactly the census unit's fork,
        extending exactly this group."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = next(u for u in rem["build_units"]
                    if u["unit_id"] == "addition:learning-management-l2")
        self.assertEqual(unit["fork_ids"], UNIT_ORDER)
        self.assertEqual(unit["extends_group"], "learning-management-l2")
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs[1:]],
                         unit["fork_ids"])

    def test_original_claim_table_stands(self):
        """The original fork's shipped claim table stands
        exactly: all 26 families, one claim each, in taxonomy
        order, with the shipped evidence sentences."""
        specs = _load_specs()
        sheet = _sheet(specs, "F1405214357")
        got = [c["function_id"] for c in sheet["functions_claimed"]]
        self.assertEqual(got, ORIGINAL_CLAIMS["F1405214357"])
        self.assertEqual(len(got), 26)
        evidence = {c["function_id"]: c["evidence"]
                    for c in sheet["functions_claimed"]}
        self.assertEqual(
            evidence["hosting_platform"],
            "The PowerTrain Government Enclave (PGE) is a secure, "
            "FedRAMP-authorized cloud environment that hosts a "
            "diverse portfolio of mission and enterprise "
            "applications.")
        self.assertEqual(
            evidence["learning_experience_records"],
            "Veracity LRS is a robust solution designed to "
            "capture, store, and return data about learning "
            "experiences in compliance with the Experience API "
            "(xAPI) specifications.")

    def test_literal_claim_table_zero_claims(self):
        """The addition fork claims exactly nothing: its
        functions_claimed list is empty — the pinned zero-claim
        table, not a missing one."""
        sheet = _sheet(_load_specs(), "FR2118043605")
        self.assertEqual(
            [c["function_id"] for c in sheet["functions_claimed"]],
            EXPECTED_CLAIMS["FR2118043605"])
        self.assertEqual(sheet["functions_claimed"], [])

    def test_zero_claim_family_set_is_the_whole_taxonomy(self):
        """The newcomer's zero-claim set is all 26 families of
        the group's taxonomy."""
        sheet = _sheet(_load_specs(), "FR2118043605")
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        self.assertEqual(set(ALL_FAMILIES) - claimed, set(ALL_FAMILIES))

    def test_group_totals(self):
        """The group total stays 26 claims; 1 of 2 forks claims.
        Every family is claimed by exactly the original fork."""
        specs = _load_specs()
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in specs), 26)
        zero = [s["fork_id"] for s in specs
                if not s["functions_claimed"]]
        self.assertEqual(zero, ["FR2118043605"])
        by_family = {}
        for s in specs:
            for c in s["functions_claimed"]:
                by_family.setdefault(
                    c["function_id"], []).append(s["fork_id"])
        self.assertEqual(len(by_family), 26)
        for family, forks in by_family.items():
            self.assertEqual(forks, ["F1405214357"], family)

    def test_addition_tier_fields(self):
        """The addition is FedRAMP Moderate / Certified / L2 /
        SaaS / Hybrid Cloud, so the group stays single-tier and
        the Moderate baseline is unchanged. (Hybrid Cloud is
        the fork's own deployment property; it transfers
        nothing to the build.) Its source record carries no
        business categories (uncategorized in the source); the
        DeadRamp category is the census proposal, Learning
        Management — strictly separate from Education &
        Training."""
        sheet = _sheet(_load_specs(), "FR2118043605")
        self.assertEqual(sheet["vendor"], "Skillsoft")
        self.assertEqual(sheet["product"], "Percipio")
        self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
        self.assertEqual(sheet["authorization_status"],
                         "FedRAMP Certified")
        self.assertEqual(sheet["cmmc_tier"], "L2")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"], "Hybrid Cloud")
        self.assertEqual(sheet["business_categories_in_source"], [])
        self.assertEqual(sheet["deadramp_category"],
                         "Learning Management")

    def test_description_equals_cached_source(self):
        """The addition sheet's description is the fork's own
        cached marketplace description under the group's
        original convention (whitespace normalized, words
        verbatim — including the source's own misspelling
        "Andriod", preserved, not corrected)."""
        sheet = _sheet(_load_specs(), "FR2118043605")
        raw = _raw_product("FR2118043605")["service_desc"]
        self.assertEqual(
            sheet["description"],
            re.sub(r"\s+", " ", raw).strip())
        self.assertEqual(sheet["description"], NEWCOMER_DESCRIPTION)
        self.assertEqual(len(sheet["description"]), 545)

    def test_census_citation_verifies_and_tags_nothing(self):
        """Citation accounting: the fork's single census
        citation verifies as a strict verbatim substring — it
        is the description's first sentence — and the census
        classified by substance ("Learning experience
        platform."). The claim pass reads the same text for
        the taxonomy's functional pattern phrases and finds
        none. Verification is not a claim, and classification
        is not a claim either, in either direction."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        census = {f["fork_id"]: f for f in rem["forks"]
                  if f["fork_id"] in UNIT_ORDER}
        cites = census["FR2118043605"]["citations"]
        self.assertEqual(len(cites), 1)
        sheet = _sheet(_load_specs(), "FR2118043605")
        self.assertIn(cites[0], sheet["description"])
        self.assertTrue(
            sheet["description"].startswith(cites[0]))
        self.assertEqual(sheet["functions_claimed"], [])

    def test_exclusion_segment_contributes_nothing(self):
        """Exclusion discipline, checked not assumed: the
        fork's source record carries no certified-services
        block, and the description's final sentence — "The
        external content providers are not assessed." — is a
        scope-exclusion segment (it places third-party content
        providers outside the authorization boundary). It
        contains no taxonomy pattern phrase, so it contributes
        zero raw hits: the matched text is the full text and
        nothing was removed. The in-boundary sentence before
        it is FedRAMP assurance prose about the fork's own
        authorization posture and likewise tags nothing."""
        self.assertEqual(
            _raw_product("FR2118043605")["certified_services"], [])
        desc = _sheet(_load_specs(), "FR2118043605")["description"]
        self.assertTrue(desc.endswith(
            "The external content providers are not assessed."))
        self.assertIn("were assessed as in-boundary for FedRAMP",
                      desc)

    def test_named_absences_rechecked(self):
        """The singleton's checked absences, rechecked against
        the newcomer. (a) The taxonomy itself still has no
        assessment, credential, or scoring family — no family
        id names one. (b) Scoring/grading and credential
        absences survive in BOTH senses for the newcomer: its
        text has no "score" token at all and no certif-/
        credential token. (c) The assessment absence survives
        at claim level but NOT as a substance absence:
        Percipio names "assessments" — as catalogue content in
        a format list, not as assessment administration; the
        substance is booked once, under the content-library
        gap (ADDENDUM section 5), never as a claim.
        (d) Proctoring, content authoring, discussion/social,
        virtual-classroom, and gamification absences survive
        in both senses (no tokens). (e) The mobile-application
        vocabulary observation changes: Percipio names mobile
        apps — its access surface, a platform property; no
        family exists for it and no claim or gap follows."""
        for family in ALL_FAMILIES:
            self.assertNotIn("assess", family)
            self.assertNotIn("credential", family)
            self.assertNotIn("score", family)
        desc = _sheet(_load_specs(), "FR2118043605")["description"]
        low = desc.lower()
        self.assertNotIn("score", low)
        self.assertIsNone(re.search(r"certif|credential", low))
        self.assertIn("assessments", low)
        self.assertNotIn("proctor", low)
        self.assertNotIn("authoring", low)
        self.assertNotIn("discussion", low)
        self.assertNotIn("virtual classroom", low)
        self.assertNotIn("gamif", low)
        self.assertIn("mobile apps", low)

    def test_near_miss_pins_percipio(self):
        """Percipio: the platform substance is present in its
        own words; the families' operative pattern phrases are
        absent, so every family stays at its shipped count for
        this fork."""
        desc = _sheet(_load_specs(), "FR2118043605")["description"]
        low = desc.lower()
        # Substance present (ADDENDUM sections 2 and 5):
        self.assertIn("authenticates users", low)
        self.assertIn("tracks learner's progress", low)
        self.assertIn("connects users to content", low)
        self.assertIn("video-based courses", low)
        self.assertIn("practice labs", low)
        self.assertIn("boot camps", low)
        self.assertIn("build skills", low)
        self.assertIn("learning experience platform", low)
        # Family tokens absent:
        self.assertNotIn("multi-factor authentication", low)
        self.assertNotIn("single sign-on", low)
        self.assertNotIn(
            "tracking and analysis of learner activities", low)
        self.assertNotIn("content delivery", low)
        self.assertNotIn("learning delivery", low)
        self.assertNotIn(
            "capture, store, and return data about learning "
            "experiences", low)
        self.assertNotIn("management of elearning content", low)
        self.assertNotIn("cloud environment that hosts", low)
        self.assertNotIn("competency management", low)
        self.assertNotIn("configurable reports", low)
        self.assertNotIn("registration", low)
        self.assertNotIn("multiple tenants", low)
        self.assertNotIn("scorm", low)
        self.assertNotIn("api", low)


class TestAdditionSubstrateCases(unittest.TestCase):
    """Substrate cases for the addition fork (ADDENDUM section
    3). The core is unchanged; each case runs the fork's
    described surface through the records form it presupposes."""

    def test_percipio_progress_and_compliance_derivation(self):
        """Percipio shape ("tracks learner's progress"): a
        progress record for the learner+course is recorded
        in_progress (Core 7), and a compliance assignment over
        the same course (Core 9) derives its status at read —
        current before the due date, **overdue** after it with
        only an in-progress record, completed once a completed
        progress record exists — while the stored assignment
        carries no status field. The overdue assertion trips
        the group's signature ``_derive_status`` drill by
        exactly one (this method). The progress record carries
        no score field, and neither does the report over these
        records (recursive scan, Core 11)."""
        store, _learner, course = make_store()
        progress = store.record_progress(
            "carol", course["id"], "in_progress", INSTRUCTOR,
            percent_complete=40)
        self.assertEqual(progress["status"], "in_progress")
        self.assertEqual(_score_keys(progress), set())
        assignment = store.create_compliance_assignment(
            "carol", course["id"], "2026-06-01", ADMIN)
        self.assertNotIn("status", assignment)
        before = store.compliance_status(
            assignment["id"], ADMIN, as_of="2026-05-15")
        self.assertEqual(before["status"], "current")
        after = store.compliance_status(
            assignment["id"], ADMIN, as_of="2026-06-15")
        self.assertEqual(after["status"], "overdue")
        self.assertFalse(after["completed"])
        store.record_progress(
            "carol", course["id"], "completed", INSTRUCTOR)
        done = store.compliance_status(
            assignment["id"], ADMIN, as_of="2026-06-15")
        self.assertEqual(done["status"], "completed")
        self.assertTrue(done["completed"])
        report = store.report(ADMIN, as_of="2026-06-15")
        self.assertEqual(_score_keys(report), set())

    def test_percipio_content_records_and_statement_shape(self):
        """Percipio shape ("connects users to content", a
        catalogue of video courses and practice labs): the
        catalogue holds the fork's content in records form —
        a video course as an ``mp4`` content item and a
        practice lab as an ``other`` content item (Core 2,
        standards from the original fork's own list) — and an
        experience statement over the video course (Core 8)
        carries EXACTLY the pinned eight keys, with a
        score-looking result text stored verbatim as a string
        and no score field anywhere (recursive scan of the
        statement and the report, Core 11). The delivery
        runtime that would present this content to a learner
        is Extended — nothing here delivers anything."""
        store, _learner, course = make_store()
        video = store.create_content_item(
            "Percipio video course (catalogue record)", "mp4",
            ADMIN, course_id=course["id"])
        lab = store.create_content_item(
            "Percipio practice lab (catalogue record)", "other",
            ADMIN, course_id=course["id"])
        self.assertEqual(video["standard"], "mp4")
        self.assertEqual(lab["standard"], "other")
        stmt = store.record_statement(
            "carol", "completed", video["id"], INSTRUCTOR,
            context="Percipio catalogue",
            result_text="score: 88/100")
        self.assertEqual(set(stmt), STATEMENT_KEYS)
        self.assertEqual(stmt["result_text"], "score: 88/100")
        self.assertIsInstance(stmt["result_text"], str)
        self.assertEqual(_score_keys(stmt), set())
        stored = store.get_statement(stmt["id"], ADMIN)
        self.assertEqual(set(stored), STATEMENT_KEYS)
        report = store.report(ADMIN, as_of="2026-06-15")
        self.assertEqual(_score_keys(report), set())


if __name__ == "__main__":
    unittest.main()
