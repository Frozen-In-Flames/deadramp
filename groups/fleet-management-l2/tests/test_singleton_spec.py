"""Singleton spec integrity and substrate cases for the Fleet
Management L2 singleton (DeadRamp Phase 2 remainder, unit
new-singleton:Fleet Management|L2).

Traces to: UNION-SPEC.md for the Fleet Management L2 singleton. The
group's single fork (Geotab / Geotab Telematics Platform Government
(GTP Gov), FR1918150046, FedRAMP Moderate, FedRAMP Certified) was
spec'd under the category's EXISTING 17-family taxonomy applied
verbatim -- the extractor (../scratch/extract.py) parses the
TAXONOMY literal out of Group 32's shipped ``scratch/extract.py``
via ``ast`` (parsed, never executed, never re-typed) and reproduces
Group 32's two shipped claim tables exactly (12 claims) before
tagging the newcomer. That reproduction is re-run here as a test.

The newcomer claims **1 family**: ``telematics_gps``, on its only
sentence. The basis is recorded at its exact weight in UNION-SPEC.md
and ../scratch/ARTIFACTS.md: the sentence words "Telematics" (twice)
and words no GPS, live-streaming, or location token; the family is
Extended in this category, so the claim adds no Core function -- the
build is the category's fleet records substrate **carried** at
Moderate under the explicit core-boundary decision in UNION-SPEC.md.

Citation accounting, pinned: the fork's single census citation is
the entire description sentence; it verifies as a strict verbatim
substring AND is the claim evidence (the coincidence direction --
verification is still not a claim; the claim stands because the
taxonomy pattern fires).

The substrate cases exercise the shipped core as this fork's data
would land in it: vehicle registry + opaque operator records +
odometer usage readings under the monotonic rule, and a reservation
lifecycle round trip counted by the summary report. Neither case
touches the maintenance due-status derivation's overdue branch, so
this file adds no failure to the group's signature
``_derive_due_status`` drill (tests/README.md).
"""

import ast
import json
import re
import unittest
from pathlib import Path

import fleet_helpers as H

TESTS_DIR = Path(__file__).resolve().parent
GROUP_DIR = TESTS_DIR.parent
ROOT = GROUP_DIR.parents[1]
PARENT_DIR = ROOT / "groups" / "fleet-management-l1"
FORK_ID = "FR1918150046"
DESCRIPTION = (
    "The Geotab Telematics Platform (Government) (GTP Gov) is an "
    "end-to-end vehicle Telematics product, providing fleet "
    "management tools to Government fleets."
)
EXPECTED_CLAIMS = [
    {"function_id": "telematics_gps",
     "function": "Live telematics & GPS tracking",
     "evidence": DESCRIPTION},
]
ALL_FAMILY_IDS = [
    "vehicle_registry", "vehicle_reservation", "checkin_checkout",
    "usage_metering", "operator_records", "maintenance_inspection",
    "ev_charging", "payment_processing", "demand_forecasting",
    "reporting_analytics", "access_control", "telematics_gps",
    "dispatch_optimization", "eld_integration", "api_integrations",
    "audit_logging", "search",
]


def _load_specs():
    return json.loads((GROUP_DIR / "specs" / "specs.json").read_text())


def _parent_taxonomy():
    tree = ast.parse((PARENT_DIR / "scratch" / "extract.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id == "TAXONOMY":
            return ast.literal_eval(node.value)
    raise AssertionError("TAXONOMY literal not found in parent extract.py")


def _raw_products():
    dump = json.loads((ROOT / "raw" / "data_dump.json").read_text())
    fd = dump[3]["data"]["fedRAMPData"]
    return {p["id"]: p for p in fd["data"]["Products"]}


def _sentences(text):
    return re.split(r"(?<=[.!?])\s+", text.replace("\r", " "))


class TestSingletonSpec(unittest.TestCase):
    """Spec-sheet integrity pins for the singleton's one fork."""

    def test_single_sheet_and_membership(self):
        specs = _load_specs()
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["fork_id"], FORK_ID)
        rem = json.loads((ROOT / "remainder.json").read_text())
        units = [u for u in rem["build_units"]
                 if (u.get("unit_id") or u.get("name"))
                 == "new-singleton:Fleet Management|L2"]
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["fork_ids"], [FORK_ID])

    def test_taxonomy_verbatim_parent_tables_reproduced(self):
        taxonomy = _parent_taxonomy()
        self.assertEqual([t[0] for t in taxonomy], ALL_FAMILY_IDS)
        compiled = [(fid, re.compile(rx, re.I)) for fid, _label, rx in taxonomy]
        pmap = _raw_products()
        parent_specs = json.loads(
            (PARENT_DIR / "specs" / "specs.json").read_text())
        total = 0
        for sheet in parent_specs:
            desc = (pmap[sheet["fork_id"]].get("service_desc") or "").strip()
            got = []
            for tfid, rx in compiled:
                for s in _sentences(desc):
                    if rx.search(s):
                        ev = s.strip()
                        if len(ev) > 400:
                            ev = ev[:397] + "..."
                        label = dict((t[0], t[1]) for t in taxonomy)[tfid]
                        got.append({"function_id": tfid, "function": label,
                                    "evidence": ev})
                        break
            self.assertEqual(got, sheet["functions_claimed"])
            total += len(got)
        self.assertEqual(total, 12)

    def test_literal_claim_table(self):
        self.assertEqual(_load_specs()[0]["functions_claimed"], EXPECTED_CLAIMS)

    def test_zero_claim_set(self):
        claimed = {c["function_id"]
                   for c in _load_specs()[0]["functions_claimed"]}
        self.assertEqual(claimed, {"telematics_gps"})
        self.assertEqual(set(ALL_FAMILY_IDS) - claimed,
                         set(ALL_FAMILY_IDS) - {"telematics_gps"})
        self.assertEqual(len(set(ALL_FAMILY_IDS) - claimed), 16)

    def test_tier_fields(self):
        sheet = _load_specs()[0]
        self.assertEqual(sheet["vendor"], "Geotab")
        self.assertEqual(sheet["product"],
                         "Geotab Telematics Platform Government (GTP Gov)")
        self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
        self.assertEqual(sheet["cmmc_tier"], "L2")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"], "Government Community Cloud")
        self.assertEqual(sheet["business_categories_in_source"], [])
        self.assertEqual(sheet["deadramp_category"], "Fleet Management")

    def test_description_equals_cached_source(self):
        pmap = _raw_products()
        cached = (pmap[FORK_ID].get("service_desc") or "").strip()
        self.assertEqual(_load_specs()[0]["description"], cached)
        self.assertEqual(cached, DESCRIPTION)

    def test_evidence_is_verbatim(self):
        sheet = _load_specs()[0]
        for claim in sheet["functions_claimed"]:
            self.assertIn(claim["evidence"], sheet["description"])
        # One-sentence description: the evidence IS the whole text.
        self.assertEqual(sheet["functions_claimed"][0]["evidence"],
                         sheet["description"])

    def test_census_citation_verifies_and_is_the_claim_evidence(self):
        cls = json.loads((ROOT / "remainder" / "class_all.json").read_text())
        items = cls if isinstance(cls, list) else cls.get("classifications", [])
        entry = [c for c in items
                 if isinstance(c, dict) and c.get("fork_id") == FORK_ID]
        self.assertEqual(len(entry), 1)
        citations = entry[0].get("citations") or []
        self.assertEqual(len(citations), 1)
        self.assertIn(citations[0], _load_specs()[0]["description"])
        self.assertEqual(citations[0],
                         _load_specs()[0]["functions_claimed"][0]["evidence"])

    def test_no_exclusion_trap_for_newcomer(self):
        pmap = _raw_products()
        self.assertEqual(pmap[FORK_ID].get("certified_services") or [], [])
        sheet = _load_specs()[0]
        # The leveraged EVSE system (a different vendor's product,
        # record field only) manufactured no claim: no ev_charging.
        self.assertNotIn("ev_charging",
                         {c["function_id"] for c in sheet["functions_claimed"]})
        self.assertNotIn("FR2403745080", json.dumps(sheet))

    def test_absence_token_pins(self):
        desc = _load_specs()[0]["description"]
        # The claim's exact weight: telematics worded, GPS/live not.
        self.assertRegex(desc, r"(?i)telematics")
        for token in (r"\bgps\b", r"\blive\b", r"\blocation\b",
                      r"\bmaintenance\b", r"\binspection\b",
                      r"\bdispatch", r"\brouting\b", r"\broute\b",
                      r"electronic logging device", r"\beld\b",
                      r"hours-of-service", r"\baudit", r"\bsearch\b",
                      r"\bapi\b", r"\bfmis\b", r"fleet management information system",
                      r"odometer readings", r"usage statistics",
                      r"driver credentials", r"accepts payments",
                      r"reporting and analytics", r"charging"):
            self.assertIsNone(re.search(token, desc, re.I),
                              "unexpected token %r in description" % (token,))


class TestSubstrateCases(unittest.TestCase):
    """The carried substrate exercised in this fork's shape."""

    def test_telematics_shaped_usage_landing(self):
        # A telematics platform's data lands in the substrate as
        # registry + usage records: vehicle, opaque operator ref,
        # odometer readings under the monotonic rule. No streaming
        # or GPS function exists in the build (Extended).
        store, vehicle, operator = H.make_store()
        self.assertEqual(operator["operator_ref"], "OP-REF-001")
        self.assertEqual(set(operator.keys()),
                         {"id", "operator_ref", "credential_kind",
                          "credential_status", "created_by", "created_utc"})
        store.record_usage(vehicle["id"], 12000, H.MANAGER)
        store.record_usage(vehicle["id"], 12150, H.MANAGER)
        with self.assertRaises(Exception):
            store.record_usage(vehicle["id"], 12100, H.MANAGER)
        usage = store.list_usage(vehicle_id=vehicle["id"])
        self.assertEqual([u["odometer_reading"] for u in usage], [12000, 12150])

    def test_reservation_round_trip_and_summary(self):
        store, vehicle, operator = H.make_store()
        res = store.create_reservation(vehicle["id"], operator["operator_ref"],
                                       "2026-11-01", "2026-11-03", H.MANAGER)
        store.record_checkin(res["id"], "check_out", 12000, H.MANAGER)
        self.assertEqual(store.get_reservation(res["id"])["status"], "checked_out")
        store.record_checkin(res["id"], "check_in", 12150, H.MANAGER)
        self.assertEqual(store.get_reservation(res["id"])["status"], "returned")
        report = store.summary_report(H.ADMIN)
        self.assertEqual(report["counts"]["vehicles"], 1)
        self.assertEqual(report["counts"]["reservations"], 1)
        self.assertEqual(report["counts"]["checkins"], 2)
        self.assertEqual(report["vehicles"][0]["latest_odometer"], None)


if __name__ == "__main__":
    unittest.main()
