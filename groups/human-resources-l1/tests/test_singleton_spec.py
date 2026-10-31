"""Singleton spec integrity and substrate cases for the Human
Resources L1 singleton (DeadRamp Phase 2 remainder, unit
new-singleton:Human Resources|L1).

Traces to: UNION-SPEC.md for the Human Resources L1 singleton.
The group's single fork (Qgenda, LLC / QGenda) was spec'd under
the category's EXISTING 25-family taxonomy applied verbatim —
the singleton extractor (../scratch/extract.py) parses the
TAXONOMY literal out of Group 21's shipped ``scratch/extract.py``
via ``ast`` (parsed, never executed, never re-typed) and
reproduces Group 21's ORIGINAL four shipped claim tables exactly
(38 claims, function ids and evidence) before tagging the
newcomer.

The newcomer claims **1 family**: ``ai_automation``, on its
first sentence ("QGenda is the leader in cloud-based call and
scheduling automation ..."). The basis is recorded at its exact
weight in UNION-SPEC.md and ../scratch/ARTIFACTS.md: the sentence
asserts scheduling *automation*; it contains no AI wording at
all (no standalone "AI", no "artificial intelligence"), and the
family is Extended in this category — this build implements no
AI function. The same automation-only weight as FedHire's and
GDC's claims at L2. The other 24 families tag nothing. The
fork's headline function — workforce call/scheduling for
healthcare organizations — has NO taxonomy family and is a
named gap, not a forced claim (the Perceptyx precedent at L2).

Citation accounting, pinned: the census recorded two citations,
both of which verify as strict verbatim substrings (they are the
description's two sentences). Citation 1 IS the claim's evidence
and tags ai_automation; citation 2 verifies and tags nothing.
Verification is not a claim, in either direction — both
directions are on record for this fork.

Named absences, pinned: all six of the category's named absences
were re-probed against THIS fork's description and all six stand
at this tier (zero hits each). The two absences retired at L2
(leave & time-off, time & attendance) retired on GDC's own words
there; QGenda's words contain neither leave nor attendance
wording — its substance is scheduling, which is neither — so
neither retirement carries to this tier.

The substrate cases exercise the shipped core as the newcomer
would use it: the workforce it schedules held as person and
position records keyed by opaque references (no clinician name
can be stored anywhere), counted by the report; and an
onboarding lifecycle case whose status is derived at read from
its task states. The second case DOES exercise the lifecycle
derivation, so this file contributes failures to the group's
signature ``_derive_case_status`` drill by design (the exact
count is recorded in tests/README.md).
"""

import ast
import json
import os
import re
import unittest

import hr_helpers as H

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

FORK_ID = "FR1924942935"
UNIT_ID = "new-singleton:Human Resources|L1"

ALL_FAMILIES = [
    "talent_acquisition",
    "applicant_tracking",
    "vacancy_announcements",
    "position_classification",
    "job_analysis",
    "hiring_assessments",
    "panel_review",
    "referral_certificates",
    "onboarding",
    "performance_management",
    "benefits_retirement",
    "personnel_actions_cases",
    "separation",
    "labor_relations",
    "awards_recognition",
    "workforce_planning",
    "talent_management",
    "talent_mobility",
    "recruiting_outreach",
    "learning_upskilling",
    "ai_automation",
    "reporting_analytics",
    "audit_compliance",
    "integrations",
    "access_control",
]

_S1 = (
    "QGenda is the leader in cloud-based call and scheduling "
    "automation (https://www.qgenda.com/customers/federal/)."
)
_S2 = (
    "Leading physician groups, hospitals, academic medical "
    "centers, and enterprise health systems use QGenda to "
    "optimize their workforce to allow them to provide the best "
    "possible patient care."
)

EXPECTED_CLAIMS = {
    FORK_ID: [("ai_automation", _S1)],
}

ABSENCE_PROBES = {
    "leave_time_off": r"(leave|time off|paid time off|vacation)",
    "policy_acknowledgements": r"(polic|acknowledg)",
    "payroll": r"(payroll)",
    "background_checks": r"(background check|background investigation)",
    "salary_compensation": r"(salary|compensation)",
    "time_attendance_literal": r"(time and attendance|timesheet)",
}

FORBIDDEN_KEYS = {
    "name", "ssn", "social_security_number", "salary",
    "compensation", "pay", "dob", "date_of_birth", "address",
    "phone", "email",
}


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _raw_product(fork_id):
    with open(os.path.join(_REPO_ROOT, "raw", "data_dump.json")) as fh:
        dump = json.load(fh)
    prods = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
    return {p["id"]: p for p in prods}[fork_id]


def _parse_taxonomy(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "TAXONOMY"
            for t in node.targets
        ):
            return [tuple(item) for item in ast.literal_eval(node.value)]
    raise AssertionError(f"no TAXONOMY literal in {path}")


def _tag(desc, taxonomy):
    """Group 21's tagging rule: first matching sentence per
    family, evidence truncated at 400 chars."""
    sents = re.split(r"(?<=[.!?])\s+", desc.replace("\r", " "))
    claims = []
    for tfid, label, pattern in taxonomy:
        rx = re.compile(pattern, re.IGNORECASE)
        for s in sents:
            if rx.search(s):
                ev = s.strip()
                if len(ev) > 400:
                    ev = ev[:397] + "..."
                claims.append({"function_id": tfid, "function": label,
                               "evidence": ev})
                break
    return claims


class TestSingletonSpecIntegrity(unittest.TestCase):
    """UNION-SPEC.md: membership, taxonomy-verbatim reproduction,
    literal claim table, verbatim description and evidence,
    census citation accounting, absence and near-miss pins."""

    def test_single_sheet_and_membership(self):
        """Exactly 1 sheet, and it is exactly the census unit's
        fork for this singleton."""
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs], [FORK_ID])
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = next(u for u in rem["build_units"]
                    if u["unit_id"] == UNIT_ID)
        self.assertEqual(unit["fork_ids"], [FORK_ID])
        census = next(f for f in rem["forks"]
                      if f["fork_id"] == FORK_ID)
        self.assertEqual(census["build_unit"], UNIT_ID)
        self.assertEqual(census["proposed_category"],
                         "Human Resources")

    def test_taxonomy_verbatim(self):
        """The taxonomy applied here is the category's one
        taxonomy: the TAXONOMY literal ast-parsed out of Group
        21's shipped extractor (25 families, in order), and
        every claimed family is one of them."""
        tax = _parse_taxonomy(os.path.join(
            _REPO_ROOT, "groups", "human-resources-l2", "scratch",
            "extract.py"))
        self.assertEqual([t[0] for t in tax], ALL_FAMILIES)
        sheet = _load_specs()[0]
        for claim in sheet["functions_claimed"]:
            self.assertIn(claim["function_id"], ALL_FAMILIES)

    def test_reproduction_of_original_tables(self):
        """Taxonomy-verbatim proof: re-tagging the original 4
        forks' cached descriptions with the parsed taxonomy
        reproduces their shipped claim tables exactly (38
        claims, ids + evidence), as snapshotted from the
        original ship (git 0a14d91)."""
        tax = _parse_taxonomy(os.path.join(
            _REPO_ROOT, "groups", "human-resources-l2", "scratch",
            "extract.py"))
        with open(os.path.join(_GROUP_ROOT, "scratch",
                               "original_specs.json")) as fh:
            original = json.load(fh)
        self.assertEqual(len(original), 4)
        for sheet in original:
            repro = _tag(_raw_product(sheet["fork_id"])
                         ["service_desc"], tax)
            self.assertEqual(repro, sheet["functions_claimed"],
                             sheet["fork_id"])
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in original), 38)

    def test_literal_claim_table(self):
        """The fork claims exactly ai_automation, with the
        pinned evidence sentence (its first sentence)."""
        sheet = _load_specs()[0]
        got = [(c["function_id"], c["evidence"])
               for c in sheet["functions_claimed"]]
        self.assertEqual(got, EXPECTED_CLAIMS[FORK_ID])

    def test_zero_claim_set(self):
        """The zero-claim set is the other 24 families — the
        description fires nothing else, raw hits equal claims
        (1 = 1), and nothing was removed."""
        sheet = _load_specs()[0]
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        self.assertEqual(set(ALL_FAMILIES) - claimed,
                         set(ALL_FAMILIES) - {"ai_automation"})

    def test_tier_fields(self):
        """The fork is FedRAMP LI-SaaS / Certified / L1 / SaaS /
        Public Cloud — its actual impact level recorded as-is,
        not rounded to Low. Its source record carries no
        business categories (uncategorized in the source; the
        DeadRamp category is the census proposal), and
        forks.json files it Uncategorized at L1."""
        sheet = _load_specs()[0]
        self.assertEqual(sheet["vendor"], "Qgenda, LLC")
        self.assertEqual(sheet["product"], "QGenda")
        self.assertEqual(sheet["fedramp_impact_level"], "LI-SaaS")
        self.assertEqual(sheet["authorization_status"],
                         "FedRAMP Certified")
        self.assertEqual(sheet["cmmc_tier"], "L1")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"], "Public Cloud")
        self.assertEqual(sheet["business_categories_in_source"], [])
        self.assertEqual(sheet["deadramp_category"],
                         "Human Resources")
        with open(os.path.join(_REPO_ROOT, "forks.json")) as fh:
            forks = json.load(fh)
        fork = next(f for f in forks if f["source_url"].rstrip("/")
                    .rsplit("/", 1)[-1] == FORK_ID)
        self.assertEqual(fork["category"],
                         "Uncategorized (none in source)")
        self.assertEqual(fork["cmmc_tier"], "L1")

    def test_description_equals_cached_source(self):
        """The sheet's description is the fork's own cached
        marketplace description, verbatim."""
        sheet = _load_specs()[0]
        self.assertEqual(sheet["description"],
                         _raw_product(FORK_ID)["service_desc"])
        self.assertEqual(sheet["description"], _S1 + " " + _S2)

    def test_evidence_is_verbatim(self):
        """The claim's evidence sentence appears verbatim in the
        fork's own description."""
        sheet = _load_specs()[0]
        for claim in sheet["functions_claimed"]:
            self.assertIn(claim["evidence"], sheet["description"])

    def test_census_citations_accounting(self):
        """Citation accounting: both census citations verify as
        strict verbatim substrings — they are the description's
        two sentences. Citation 1 IS the claim's evidence and
        tags ai_automation; citation 2 verifies and tags
        nothing. Verification is not a claim, in either
        direction."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        census = next(f for f in rem["forks"]
                      if f["fork_id"] == FORK_ID)
        self.assertEqual(census["citations"], [_S1, _S2])
        sheet = _load_specs()[0]
        self.assertIn(_S1, sheet["description"])
        self.assertIn(_S2, sheet["description"])
        evidences = [c["evidence"] for c in sheet["functions_claimed"]]
        self.assertEqual(evidences, [_S1])
        tax = _parse_taxonomy(os.path.join(
            _REPO_ROOT, "groups", "human-resources-l2", "scratch",
            "extract.py"))
        pattern = next(p for fid, _l, p in tax
                       if fid == "ai_automation")
        self.assertIsNotNone(re.search(pattern, _S1, re.IGNORECASE))
        self.assertIsNone(re.search(pattern, _S2, re.IGNORECASE))

    def test_no_exclusion_trap_for_newcomer(self):
        """No exclusion applied: the source record carries no
        certified-services catalogue of third-party hosted
        applications, and the description contains no
        scope-exclusion segment. Matched text is the full text."""
        self.assertEqual(_raw_product(FORK_ID)["certified_services"],
                         [])

    def test_named_absences_stand_at_this_tier(self):
        """All six of the category's named absences were
        re-probed against THIS fork's description and all six
        stand (zero hits each) — including the two retired at
        L2: QGenda's words contain no leave wording and no
        attendance wording, so neither L2 retirement carries to
        this tier. Scheduling is not attendance tracking."""
        desc = _load_specs()[0]["description"]
        for name, pattern in ABSENCE_PROBES.items():
            self.assertEqual(
                len(re.findall(pattern, desc, re.IGNORECASE)), 0,
                name)
        low = desc.lower()
        self.assertNotIn("attendance", low)
        self.assertNotIn("timesheet", low)
        self.assertNotIn("time tracking", low)

    def test_near_miss_pins_qgenda(self):
        """QGenda: the scheduling substance is present in its own
        words; the neighbouring families' operative phrases are
        absent, so every other family stays at zero."""
        desc = _load_specs()[0]["description"]
        low = desc.lower()
        # Substance present (the claim's basis and the gap):
        self.assertIn("scheduling automation", low)
        self.assertIn("workforce", low)
        self.assertIn("physician groups", low)
        self.assertIn("hospitals", low)
        # The claim is automation-weighted: no AI wording at all.
        self.assertIsNone(re.search(r"\bAI\b", desc))
        self.assertNotIn("artificial intelligence", low)
        # workforce_planning's operative phrases are absent:
        # "optimize their workforce" is an outcome phrase, not
        # the family's phrase.
        self.assertNotIn("workforce planning", low)
        self.assertNotIn("resource management", low)
        # No other family's phrase appears:
        self.assertNotIn("talent acquisition", low)
        self.assertNotIn("applicant tracking", low)
        self.assertNotIn("onboarding", low)
        self.assertNotIn("performance management", low)
        self.assertNotIn("benefits", low)
        self.assertNotIn("personnel actions", low)
        self.assertNotIn("case management", low)
        self.assertNotIn("separation", low)
        self.assertNotIn("labor relations", low)
        self.assertNotIn("talent management", low)
        self.assertNotIn("reporting", low)
        self.assertNotIn("audit", low)
        self.assertNotIn("integrat", low)
        self.assertNotIn("access control", low)


class TestSingletonSubstrateCases(unittest.TestCase):
    """Substrate cases for the singleton fork (UNION-SPEC.md core
    section). The core is carried; each case runs the fork's
    described surface through the records form it presupposes."""

    def test_qgenda_workforce_registry_records(self):
        """QGenda shape: the healthcare workforce the fork
        schedules, held as person records keyed by opaque
        caller-supplied references (Core 1) and the staffed
        roles as position records (Core 2), counted by the
        report (Core 10). The person shape is exactly the
        substrate's six keys — a scheduling product's real
        records are full of clinician names; this substrate
        holds none, by design (no field can)."""
        store = H.fresh_store()
        p1 = store.create_person("STAFF-2042", H.ADMIN,
                                 kind="employee")
        store.create_person("STAFF-2043", H.ADMIN, kind="employee")
        pos = store.create_position(
            "Attending Physician", H.ADMIN,
            organization="General Hospital")
        store.create_position("Charge Nurse", H.ADMIN,
                              organization="General Hospital")
        self.assertEqual(
            set(p1.keys()),
            {"id", "person_ref", "kind", "status", "created_by",
             "created_utc"})
        for record in (p1, pos):
            for key in record:
                self.assertNotIn(key.lower(), FORBIDDEN_KEYS)
        report = store.report(H.ADMIN)
        self.assertEqual(report["persons"], 2)
        self.assertEqual(report["positions"], 2)
        self.assertEqual(report["positions_by_status"]["vacant"], 2)

    def test_qgenda_onboarding_case_derivation(self):
        """QGenda shape: a newly scheduled clinician's
        onboarding worked as a lifecycle case with a task
        checklist (Core 6) — status derived at read from the
        task states, progressing not_started → in_progress →
        complete, never stored. The scheduling engine that
        would assign the clinician's shifts is Extended; this
        case records the entrance-on-duty checklist the
        substrate presupposes."""
        store = H.fresh_store()
        store.create_person("STAFF-2042", H.ADMIN, kind="employee")
        case = store.create_lifecycle_case(
            "STAFF-2042", "onboarding", H.SPECIALIST,
            task_titles=["Credentialing file opened",
                         "Schedule profile created"])
        self.assertEqual(case["status"], "not_started")
        store.set_task_state(case["id"], "t-1", "done", H.SPECIALIST)
        view = store.get_lifecycle_case(case["id"], H.SPECIALIST)
        self.assertEqual(view["status"], "in_progress")
        store.set_task_state(case["id"], "t-2", "done", H.SPECIALIST)
        view = store.get_lifecycle_case(case["id"], H.SPECIALIST)
        self.assertEqual(view["status"], "complete")
        self.assertTrue(view["complete"])


if __name__ == "__main__":
    unittest.main()
