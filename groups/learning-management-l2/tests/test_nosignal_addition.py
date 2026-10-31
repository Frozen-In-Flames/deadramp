"""No-signal addition (F1207261443, Skillsoft / Private Cloud):
spec integrity and substrate cases.

Traces to: ADDENDUM.md section 7 for Group 48 (Learning
Management, CMMC L2). This fork sat in the remainder census's
``no-signal-set``: its cached marketplace description is a
company profile of Skillsoft only -- the census recorded
citations [], no_signal true (reason "prose_only"), and the
classifier note "Description is a company profile of Skillsoft
only; no function stated for this Private Cloud offering." --
so no census build unit proposed a category for it. Its
category was resolved afterwards by the live-docs research
pass (``remainder/nosignal_report.json``, status "resolved",
existing category): Learning Management, on the sentence

    "With the Skillsoft Percipio Platform, you can experience
    multiple ways to learn."

from Skillsoft's official documentation portal. That sentence
is pinned here as the sheet's *classification* citation
(``classification_evidence`` / ``classification_source_url``)
-- kept distinct from claim evidence, and in fact asserted NOT
to occur in the cached description.

THE CAVEAT, pinned: the classification evidence is Skillsoft's
**Percipio platform documentation** -- the platform this
Private Cloud offering delivers. No Private Cloud-specific
function sentence exists on the official pages checked (the
report's notes say so verbatim, pinned below), and ADDENDUM
section 7 records the caveat in those terms (also pinned
below). The kinship is plain: the group's remainder-addition
fork (FR2118043605) IS Skillsoft's Percipio platform under a
different offering record; the two records are distinct forks
and both stand.

Spec'd under the group's EXISTING 26-family taxonomy applied
verbatim -- the no-signal extractor parses the TAXONOMY
literal out of the shipped ``scratch/extract.py`` via ``ast``
(parsed, never executed, never re-typed) and, before tagging,
reproduces BOTH shipped claim tables exactly from their cached
descriptions (PowerTrain 26 claims deep-equal; Percipio the
zero-claim table deep-equal) -- the taxonomy-verbatim proof.
The Private Cloud fork claims **zero** families, with **zero
raw hits**: its 339-character description is three sentences
of company profile ("produces learning management system
software and content", "one of the world's largest corporate
training providers", "an education provider to many U.S. DoD
and U.S. Federal organizations") in which no functional
pattern phrase of any of the 26 families appears. The
zero-claim outcome is pinned here, not hidden, with the
near-miss substance asserted present in the description. The
singleton's checked absences survive in both senses on this
fork's words (no score token, no certif-/credential token, no
assessment token at all).

The core is unchanged (no claimed family presupposes a records
form the build lacks), so the fork is additionally exercised
against the substrate through the records forms its classified
surface presupposes: an organization consuming the hosted
platform records its content in the catalogue (Core 2), its
learners' progress against that content (Core 7), a mandatory
assignment whose status derives at read (Core 9 -- that
assertion trips the group's signature ``_derive_status`` drill
by exactly one; see tests/README.md), and an experience
statement over a hosted content item (Core 8) with the exact
eight-key shape and no score field anywhere. The
vendor-operated private-cloud hosting itself is Extended
(ADDENDUM section 7), not implemented. Category boundary:
nothing here imports Education & Training functions; this is
the Learning Management taxonomy only, and the description's
"education provider" audience prose changes nothing about
that.
"""

import json
import os
import re
import subprocess
import unittest

from lms_helpers import ADMIN, INSTRUCTOR, make_store

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

SHIPPED_ORDER = [
    "F1405214357",   # PowerTrain Inc. -- PowerTrain Government
                     # Learning Enclave - SaaS
    "FR2118043605",  # Skillsoft -- Percipio (remainder addition)
]
NOSIGNAL_ID = "F1207261443"  # Skillsoft -- Private Cloud

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

# The literal claim table for the no-signal fork: it claims zero
# families under the taxonomy applied verbatim. Pinned, not hidden.
EXPECTED_CLAIMS = {NOSIGNAL_ID: []}

NOSIGNAL_DESCRIPTION = (
    "Skillsoft is a U.S. based educational technology "
    "company that produces learning management system "
    "software and content. It is one of the world's largest "
    "corporate training providers, with 10,000 customers, "
    "60 million users, and 2,400 employees as of 2014. "
    "Skillsoft is an education provider to many U.S. DoD "
    "and U.S. Federal organizations."
)

CLASSIFICATION_URL = (
    "https://documentation.skillsoft.com/en_us/"
    "compliance_trng/content/b_learner/lrnr_getting_started.htm"
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
    (case-insensitive) -- the group's pinned definition."""
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


class TestNoSignalSpecIntegrity(unittest.TestCase):
    """ADDENDUM section 7: membership, shipped-sheet
    immutability, the literal zero-claim table, verbatim
    description, the classification citation pins (including
    the platform-documentation caveat), the absence rechecks,
    and the near-miss pins."""

    def test_sheet_count_and_order(self):
        """3 sheets: the shipped singleton, the remainder
        addition, then the no-signal sheet."""
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs],
                         SHIPPED_ORDER + [NOSIGNAL_ID])

    def test_shipped_sheets_deep_equal_git_head(self):
        """The 2 previously shipped sheets are deep-equal to
        git HEAD -- the append changed neither of them."""
        head = subprocess.run(
            ["git", "-C", _REPO_ROOT, "show",
             "HEAD:groups/learning-management-l2/specs/specs.json"],
            capture_output=True, text=True, check=True).stdout
        head_specs = json.loads(head)
        self.assertEqual(len(head_specs), 2)
        self.assertEqual(_load_specs()[:2], head_specs)

    def test_membership_is_the_nosignal_fork(self):
        """The appended sheet is exactly Skillsoft / Private
        Cloud, the fork the census left in its no-signal set
        (citations [], flagged no_signal, classifier note: a
        company profile only) and the live-docs pass
        resolved."""
        specs = _load_specs()
        sheet = _sheet(specs, NOSIGNAL_ID)
        self.assertEqual(sheet["vendor"], "Skillsoft")
        self.assertEqual(sheet["product"], "Private Cloud")
        self.assertEqual(
            sheet["source_url"],
            "https://www.fedramp.gov/marketplace/products/F1207261443/")
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = next(u for u in rem["build_units"]
                    if u["unit_id"] == "no-signal-set")
        self.assertIn(NOSIGNAL_ID, unit["fork_ids"])
        census = next(f for f in rem["forks"]
                      if f["fork_id"] == NOSIGNAL_ID)
        self.assertTrue(census["no_signal"])
        self.assertEqual(census["no_signal_reason"], "prose_only")
        self.assertEqual(census["citations"], [])
        self.assertIn("company profile", census["classifier_note"])

    def test_literal_claim_table_zero(self):
        """Private Cloud claims zero families; pinned."""
        specs = _load_specs()
        got = [c["function_id"]
               for c in _sheet(specs, NOSIGNAL_ID)["functions_claimed"]]
        self.assertEqual(got, EXPECTED_CLAIMS[NOSIGNAL_ID])
        self.assertEqual(
            _sheet(specs, NOSIGNAL_ID)["functions_claimed"], [])

    def test_zero_claim_family_set_is_the_whole_taxonomy(self):
        """The no-signal fork's zero-claim set is all 26
        families of the group's taxonomy."""
        sheet = _sheet(_load_specs(), NOSIGNAL_ID)
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        self.assertEqual(set(ALL_FAMILIES) - claimed, set(ALL_FAMILIES))

    def test_group_totals_unchanged(self):
        """The no-signal addition adds no claims: the group
        total stays 26, and 2 of the group's 3 forks now
        carry zero claims (the Percipio addition and Private
        Cloud); only the founding fork claims."""
        specs = _load_specs()
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in specs), 26)
        zero = [s["fork_id"] for s in specs
                if not s["functions_claimed"]]
        self.assertEqual(zero, ["FR2118043605", NOSIGNAL_ID])

    def test_tier_fields(self):
        """Private Cloud is FedRAMP Moderate / Certified / L2 /
        SaaS, Public Cloud deployment, no business categories
        in the source (Uncategorized; the DeadRamp category
        came from the live-docs resolution) -- the group stays
        single-tier and the baseline is unchanged. (Public
        Cloud is the fork's own deployment property; it
        transfers nothing to the build.)"""
        sheet = _sheet(_load_specs(), NOSIGNAL_ID)
        self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
        self.assertEqual(sheet["cmmc_tier"], "L2")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["authorization_status"],
                         "FedRAMP Certified")
        self.assertEqual(sheet["deployment_model"], "Public Cloud")
        self.assertEqual(sheet["business_categories_in_source"], [])
        self.assertEqual(sheet["deadramp_category"],
                         "Learning Management")

    def test_description_equals_cached_sources(self):
        """The sheet's description is the fork's own cached
        marketplace description, verbatim -- identical in the
        raw dataset (whitespace-normalized per the group's
        convention) and in remainder/uncovered.json (the
        description of record)."""
        sheet = _sheet(_load_specs(), NOSIGNAL_ID)
        raw = _raw_product(NOSIGNAL_ID)["service_desc"]
        self.assertEqual(
            sheet["description"],
            re.sub(r"\s+", " ", raw).strip())
        with open(os.path.join(_REPO_ROOT, "remainder",
                               "uncovered.json")) as fh:
            unc = json.load(fh)
        urec = next(r for r in unc if r["fork_id"] == NOSIGNAL_ID)
        self.assertEqual(sheet["description"], urec["description"])
        self.assertEqual(sheet["description"], NOSIGNAL_DESCRIPTION)
        self.assertEqual(len(sheet["description"]), 339)

    def test_classification_fields_match_report(self):
        """The sheet's classification citation is exactly the
        live-docs report's entry: the verbatim sentence and
        its URL from remainder/nosignal_report.json, category
        Learning Management (an existing category, not a new
        one), status resolved. The sentence is documentation
        prose, NOT marketplace text: it does not occur in the
        cached description, which is what keeps the
        classification citation distinct from claim evidence."""
        with open(os.path.join(_REPO_ROOT, "remainder",
                               "nosignal_report.json")) as fh:
            report = json.load(fh)
        rep = next(r for r in report if r["fork_id"] == NOSIGNAL_ID)
        self.assertEqual(rep["status"], "resolved")
        self.assertEqual(rep["category_proposal"], "Learning Management")
        self.assertFalse(rep["is_new_category"])
        sheet = _sheet(_load_specs(), NOSIGNAL_ID)
        self.assertEqual(sheet["classification_evidence"],
                         rep["evidence_sentence"])
        self.assertEqual(sheet["classification_source_url"],
                         rep["source_url"])
        self.assertEqual(sheet["classification_source_url"],
                         CLASSIFICATION_URL)
        self.assertNotIn(sheet["classification_evidence"],
                         sheet["description"])

    def test_classification_caveat_platform_documentation(self):
        """The caveat, pinned on both records. (a) The report's
        own notes state the evidence is for the Percipio
        platform the Private Cloud offering delivers and that
        no separate Private Cloud-specific sentence was found
        -- the evidence is platform documentation, not an
        offering-specific page. (b) ADDENDUM section 7 records
        the caveat in the same terms. (c) The kinship is plain
        in the file itself: sheet 2 is Skillsoft's Percipio
        offering record and sheet 3 is Skillsoft's Private
        Cloud offering record -- two distinct forks of the
        same vendor, both standing."""
        with open(os.path.join(_REPO_ROOT, "remainder",
                               "nosignal_report.json")) as fh:
            report = json.load(fh)
        rep = next(r for r in report if r["fork_id"] == NOSIGNAL_ID)
        self.assertIn("Percipio learning platform", rep["notes"])
        self.assertIn("no separate Private Cloud-specific",
                      rep["notes"])
        with open(os.path.join(_GROUP_ROOT, "ADDENDUM.md")) as fh:
            addendum = fh.read()
        self.assertIn("Percipio platform documentation", addendum)
        self.assertIn("no Private Cloud-specific sentence", addendum)
        specs = _load_specs()
        self.assertEqual(_sheet(specs, "FR2118043605")["product"],
                         "Percipio")
        self.assertEqual(_sheet(specs, NOSIGNAL_ID)["vendor"],
                         "Skillsoft")
        self.assertNotEqual("FR2118043605", NOSIGNAL_ID)

    def test_all_claim_evidence_verbatim(self):
        """Every claim's evidence, group-wide, is a verbatim
        substring of its own fork's description (vacuous for
        Private Cloud's empty table, run anyway)."""
        for sheet in _load_specs():
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], sheet["description"])

    def test_named_absences_rechecked(self):
        """The singleton's checked absences, rechecked against
        the no-signal fork: all survive in BOTH senses -- the
        company profile contains no score token (not even a
        SCORM substring), no certif-/credential token, no
        assessment token of any kind, and no proctoring,
        authoring, discussion/social, virtual-classroom,
        gamification, or mobile vocabulary. The taxonomy
        itself still has no assessment, credential, or
        scoring family."""
        for family in ALL_FAMILIES:
            self.assertNotIn("assess", family)
            self.assertNotIn("credential", family)
            self.assertNotIn("score", family)
        desc = _sheet(_load_specs(), NOSIGNAL_ID)["description"]
        low = desc.lower()
        self.assertNotIn("score", low)
        self.assertNotIn("scorm", low)
        self.assertIsNone(re.search(r"certif|credential", low))
        self.assertNotIn("assess", low)
        self.assertNotIn("proctor", low)
        self.assertNotIn("authoring", low)
        self.assertNotIn("discussion", low)
        self.assertNotIn("virtual classroom", low)
        self.assertNotIn("gamif", low)
        self.assertNotIn("mobile", low)

    def test_near_miss_pins_private_cloud(self):
        """Private Cloud: company-profile substance is present
        in its own words; the families' operative pattern
        phrases are absent, so every family stays at its
        shipped count for this fork."""
        desc = _sheet(_load_specs(), NOSIGNAL_ID)["description"]
        low = desc.lower()
        # Substance present (ADDENDUM section 7):
        self.assertIn("learning management system software", low)
        self.assertIn("corporate training providers", low)
        self.assertIn("education provider", low)
        self.assertIn("produces", low)
        self.assertIn("content", low)
        # Family phrases absent:
        self.assertNotIn("management of elearning content", low)
        self.assertNotIn("mandatory training compliance", low)
        self.assertNotIn("competency management", low)
        self.assertNotIn("lesson plans", low)
        self.assertNotIn("configurable reports", low)
        self.assertNotIn("cloud environment that hosts", low)
        self.assertNotIn("multiple tenants", low)
        self.assertNotIn("multi-factor authentication", low)
        self.assertNotIn(
            "capture, store, and return data about learning "
            "experiences", low)
        self.assertNotIn(
            "tracking and analysis of learner activities", low)
        self.assertNotIn("career mapping enables", low)
        self.assertNotIn("candidate review system supports", low)
        self.assertNotIn("powersurvey supports", low)
        self.assertNotIn("mediawiki", low)
        self.assertNotIn("drupal", low)
        self.assertNotIn("api", low)


class TestNoSignalSubstrateCases(unittest.TestCase):
    """Substrate cases for the no-signal fork (ADDENDUM section
    7). The core is unchanged; each case runs the fork's
    classified surface -- an organization consuming the
    Percipio platform as a vendor-hosted private cloud --
    through the records forms it presupposes."""

    def test_private_cloud_progress_and_compliance_derivation(self):
        """Private Cloud shape: the hosted platform's content
        sits in the catalogue as records (Core 2), a learner's
        progress against the course is recorded in_progress
        (Core 7), and a compliance assignment over the same
        course (Core 9) derives its status at read -- current
        before the due date, **overdue** after it with only an
        in-progress record, completed once a completed
        progress record exists -- while the stored assignment
        carries no status field. The overdue assertion trips
        the group's signature ``_derive_status`` drill by
        exactly one (this method). Neither the progress record
        nor the report over these records carries a score
        field (recursive scan, Core 11). The vendor-operated
        hosting that delivers this platform is Extended --
        nothing here hosts anything."""
        store, _learner, course = make_store()
        store.create_content_item(
            "Percipio platform course (hosted catalogue record)",
            "mp4", ADMIN, course_id=course["id"])
        progress = store.record_progress(
            "carol", course["id"], "in_progress", INSTRUCTOR,
            percent_complete=25)
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

    def test_private_cloud_statement_shape(self):
        """Private Cloud shape: an experience statement over a
        hosted catalogue item (Core 8) carries EXACTLY the
        pinned eight keys, with a score-looking result text
        stored verbatim as a string and no score field
        anywhere (recursive scan of the statement and the
        report, Core 11). The platform runtime that would
        present this content to a learner is Extended --
        nothing here delivers anything."""
        store, _learner, course = make_store()
        item = store.create_content_item(
            "Percipio platform course (hosted catalogue record)",
            "mp4", ADMIN, course_id=course["id"])
        stmt = store.record_statement(
            "carol", "experienced", item["id"], INSTRUCTOR,
            context="Private Cloud hosted platform",
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
