"""Final GAPS batch tests — GRC L3-adjacent extension surface.

Traces to: GAPS.md section "Singleton 44 — GRC L3-adjacent
(1 fork)", the 12 registered Extended entries, closed by
``src/grc/extensions.py`` (see the group's BATCH.md for the
per-entry dispositions). The category doctrine binds the whole
surface: posture is counts only and **no score / rating / grade /
percent key exists anywhere** (the recursive scan below mirrors
``test_posture.py``); prediction labels are recorded verbatim and
never computed; date-based status is derived at read, never
stored; the High-baseline adaptations (hash-chained audit,
fail-closed writes, auditor separation) hold on the extension
surface exactly as on the Core.
"""

import hashlib
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
from grc.extensions import GrcExtensions, derive_grant_status
from grc.store import GrcStore

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


def make_extensions(audit=None):
    """Fresh core store (canonical fixture) + extension surface."""
    store, system, indicator = H.make_store(audit=audit)
    return GrcExtensions(store), store


class TestPredictionRecords(unittest.TestCase):
    """Entries 419 + 421: the fork's AI accreditation-prediction and
    risk-prediction engines close as PREDICTION RECORDS — labels
    reported by the fork's own engines, stored verbatim against
    governed systems/controls. No inference happens here."""

    def test_accreditation_prediction_recorded_verbatim(self):
        """419: an accreditation prediction label is stored verbatim
        with inference_here False — the build records the engine's
        reported output; it computes nothing."""
        ext, _ = make_extensions()
        record = ext.create_prediction(
            "accreditation", H.SYSTEM_REF, "Predicted COMPLIANT (vendor wording)",
            H.MEMBER, source_ref="archangel-engine", control_ids=["IA-2"],
        )
        self.assertEqual(record["id"], "pred-1")
        self.assertEqual(record["kind"], "accreditation")
        self.assertEqual(record["predicted_label"], "Predicted COMPLIANT (vendor wording)")
        self.assertIs(record["inference_here"], False)
        self.assertEqual(record["control_ids"], ["IA-2"])
        fetched = ext.get_prediction("pred-1", H.VIEWER)
        self.assertEqual(fetched, record)

    def test_risk_prediction_recorded_verbatim(self):
        """421: a risk prediction label is stored verbatim; any
        scoring engine belongs to the fork's engine, and none is
        computed or stored here."""
        ext, _ = make_extensions()
        record = ext.create_prediction(
            "risk", H.SYSTEM_REF, "elevated exposure expected Q3", H.MEMBER,
        )
        self.assertEqual(record["kind"], "risk")
        self.assertEqual(record["predicted_label"], "elevated exposure expected Q3")
        self.assertIs(record["inference_here"], False)

    def test_prediction_kind_validated(self):
        """419/421: kinds outside the two claimed prediction
        families are rejected and consume no id."""
        ext, _ = make_extensions()
        with self.assertRaises(ValidationError):
            ext.create_prediction("posture", H.SYSTEM_REF, "x", H.MEMBER)
        record = ext.create_prediction("risk", H.SYSTEM_REF, "ok", H.MEMBER)
        self.assertEqual(record["id"], "pred-1")

    def test_prediction_unknown_system_consumes_no_id(self):
        """419/421: a prediction against an unknown governed system
        is rejected whole (NotFoundError) and consumes no id."""
        ext, _ = make_extensions()
        with self.assertRaises(NotFoundError):
            ext.create_prediction("risk", "SYS-404", "x", H.MEMBER)
        with self.assertRaises(ValidationError):
            ext.create_prediction(
                "risk", H.SYSTEM_REF, "x", H.MEMBER, control_ids=["ZZ-9"],
            )
        record = ext.create_prediction("risk", H.SYSTEM_REF, "ok", H.MEMBER)
        self.assertEqual(record["id"], "pred-1")

    def test_prediction_permissions(self):
        """419/421: recording a prediction is recorded work
        (record_results) — viewer and auditor are denied; the
        auditor (AC-5) may not even read the records back."""
        ext, _ = make_extensions()
        with self.assertRaises(PermissionDenied):
            ext.create_prediction("risk", H.SYSTEM_REF, "x", H.VIEWER)
        with self.assertRaises(PermissionDenied):
            ext.create_prediction("risk", H.SYSTEM_REF, "x", H.AUDITOR)
        record = ext.create_prediction("risk", H.SYSTEM_REF, "ok", H.MEMBER)
        with self.assertRaises(PermissionDenied):
            ext.get_prediction(record["id"], H.AUDITOR)
        with self.assertRaises(PermissionDenied):
            ext.list_predictions(H.AUDITOR)

    def test_prediction_summary_counts_labels_only(self):
        """419/421: the summary aggregates prediction records as
        counts of the recorded labels — never a computed value."""
        ext, _ = make_extensions()
        ext.create_prediction("risk", H.SYSTEM_REF, "watch", H.MEMBER)
        ext.create_prediction("risk", H.SYSTEM_REF, "watch", H.MEMBER)
        ext.create_prediction("accreditation", H.SYSTEM_REF, "on track", H.MEMBER)
        summary = ext.extension_summary(H.ADMIN)
        self.assertEqual(summary["predictions"]["total"], 3)
        self.assertEqual(
            summary["predictions"]["by_kind"], {"accreditation": 1, "risk": 2},
        )
        self.assertEqual(
            summary["predictions"]["by_label"], {"watch": 2, "on track": 1},
        )


class TestProvenanceRecords(unittest.TestCase):
    """Entry 424: traceability, provenance & auditability — records
    linking artifacts to recorded sources with content hashes,
    riding the Core's evidence discipline (verify-by-content)."""

    def test_provenance_from_content_and_verify(self):
        """424: content is hashed (never retained) at record time;
        verification re-supplies content — original True, tampered
        False — exactly the Core evidence discipline."""
        ext, _ = make_extensions()
        record = ext.create_provenance(
            "artifact-7", "supplier-portal", H.MEMBER, content="manifest v1",
        )
        self.assertEqual(
            record["content_sha256"],
            hashlib.sha256(b"manifest v1").hexdigest(),
        )
        self.assertIsNone(record["evidence_id"])
        self.assertTrue(
            ext.verify_provenance(record["id"], "manifest v1", H.VIEWER),
        )
        self.assertFalse(
            ext.verify_provenance(record["id"], "manifest v2", H.VIEWER),
        )

    def test_provenance_from_core_evidence(self):
        """424: a provenance entry may link a Core evidence record
        and inherits its recorded checksum, so provenance and
        evidence verify against the same content."""
        ext, store = make_extensions()
        evidence = store.create_evidence(
            "scan report", "report-body", ["IA-2"], [H.SYSTEM_REF], actor=H.MEMBER,
        )
        record = ext.create_provenance(
            "artifact-9", "scanner-export", H.MEMBER, evidence_id=evidence["id"],
        )
        self.assertEqual(record["content_sha256"], evidence["sha256"])
        self.assertEqual(record["evidence_id"], evidence["id"])
        self.assertTrue(
            ext.verify_provenance(record["id"], "report-body", H.VIEWER),
        )

    def test_provenance_requires_exactly_one_source(self):
        """424: neither content nor evidence (or both) is a
        validation error and consumes no id; an unknown evidence id
        is NotFoundError."""
        ext, _ = make_extensions()
        with self.assertRaises(ValidationError):
            ext.create_provenance("a", "s", H.MEMBER)
        with self.assertRaises(ValidationError):
            ext.create_provenance("a", "s", H.MEMBER, content="x", evidence_id="ev-1")
        with self.assertRaises(NotFoundError):
            ext.create_provenance("a", "s", H.MEMBER, evidence_id="ev-404")
        record = ext.create_provenance("a", "s", H.MEMBER, content="x")
        self.assertEqual(record["id"], "prov-1")


class TestProcessDefinitionsAndMovements(unittest.TestCase):
    """Entry 425: low-/no-code process configuration designer &
    movement/service tracking — definitions as versioned data
    (never executed, never rendered) plus movement records over
    opaque subject references."""

    def test_definition_is_versioned_data_never_executed(self):
        """425: a definition is held verbatim as data; updates
        append versions; executed_here / rendered_here stay False;
        the caller's dict is deep-copied, so later caller edits do
        not reach the record."""
        ext, _ = make_extensions()
        definition = {"steps": [{"kind": "check_in"}], "gate": "north"}
        record = ext.create_process_definition("entry-flow", definition, H.ADMIN)
        self.assertEqual(record["version"], 1)
        self.assertIs(record["executed_here"], False)
        self.assertIs(record["rendered_here"], False)
        definition["steps"].append({"kind": "mutated"})
        stored = ext.get_process_definition(record["id"], H.VIEWER)
        self.assertEqual(len(stored["definition"]["steps"]), 1)
        updated = ext.update_process_definition(
            record["id"], {"steps": [], "gate": "south"}, H.ADMIN,
        )
        self.assertEqual(updated["version"], 2)
        self.assertEqual(len(updated["versions"]), 2)
        self.assertEqual(updated["versions"][0]["definition"]["gate"], "north")

    def test_definition_permissions_and_validation(self):
        """425: definitions are configuration records
        (manage_frameworks, admin only); a non-dict definition is
        rejected and consumes no id."""
        ext, _ = make_extensions()
        with self.assertRaises(PermissionDenied):
            ext.create_process_definition("x", {}, H.MEMBER)
        with self.assertRaises(ValidationError):
            ext.create_process_definition("x", ["not-a-dict"], H.ADMIN)
        record = ext.create_process_definition("x", {}, H.ADMIN)
        self.assertEqual(record["id"], "pdef-1")

    def test_movement_records_and_counts(self):
        """425: movement records note an opaque subject at a
        governed system under a verbatim kind label; the summary
        counts them by kind. Unknown systems/definitions are
        rejected and consume no id."""
        ext, _ = make_extensions()
        definition = ext.create_process_definition("entry-flow", {}, H.ADMIN)
        first = ext.record_movement(
            H.SYSTEM_REF, "subject-ref-1", "entry", H.MEMBER,
            definition_id=definition["id"],
        )
        self.assertEqual(first["id"], "move-1")
        ext.record_movement(H.SYSTEM_REF, "subject-ref-1", "service request", H.MEMBER)
        with self.assertRaises(NotFoundError):
            ext.record_movement("SYS-404", "s", "entry", H.MEMBER)
        with self.assertRaises(NotFoundError):
            ext.record_movement(H.SYSTEM_REF, "s", "entry", H.MEMBER,
                                definition_id="pdef-404")
        movements = ext.list_movements(H.VIEWER, system_ref=H.SYSTEM_REF)
        self.assertEqual(len(movements), 2)
        summary = ext.extension_summary(H.ADMIN)
        self.assertEqual(summary["movements"]["total"], 2)
        self.assertEqual(
            summary["movements"]["by_kind"], {"entry": 1, "service request": 1},
        )


class TestGrantRecords(unittest.TestCase):
    """Entry 426: grants lifecycle automation — lifecycle records
    over opaque program references with a guarded stage lifecycle;
    due-date status derived at read, never stored; no monetary
    field exists anywhere in this group and none is added."""

    def test_grant_lifecycle_and_history(self):
        """426: the stage lifecycle is guarded by a transition
        table with full history; an illegal transition is denied
        with the stage unchanged."""
        ext, _ = make_extensions()
        grant = ext.create_grant("PROG-1", H.MEMBER, system_ref=H.SYSTEM_REF,
                                 due_date="2026-06-30")
        self.assertEqual(grant["stage"], "pre_award")
        self.assertNotIn("amount", grant)
        grant = ext.transition_grant(grant["id"], "award", H.MEMBER)
        grant = ext.transition_grant(grant["id"], "active", H.MEMBER)
        self.assertEqual(
            [h["stage"] for h in grant["stage_history"]],
            ["pre_award", "award", "active"],
        )
        with self.assertRaises(ValidationError):
            ext.transition_grant(grant["id"], "pre_award", H.MEMBER)
        self.assertEqual(ext.get_grant(grant["id"], H.VIEWER)["stage"], "active")
        with self.assertRaises(ValidationError):
            ext.transition_grant(grant["id"], "bogus", H.MEMBER)

    def test_grant_status_is_derived_never_stored(self):
        """426: an open grant due 2026-06-30 derives its stage on
        the due date and "overdue" after it; a closed grant never
        derives overdue; the stored record carries no derived key
        (the Core's finding-derivation discipline, applied here)."""
        ext, _ = make_extensions()
        grant = ext.create_grant("PROG-2", H.MEMBER, due_date="2026-06-30")
        ext.transition_grant(grant["id"], "award", H.MEMBER)
        stored = ext.get_grant(grant["id"], H.VIEWER)
        self.assertNotIn("derived_status", stored)
        on_due = ext.get_grant(grant["id"], H.VIEWER, as_of="2026-06-30")
        self.assertEqual(on_due["derived_status"], "award")
        past_due = ext.get_grant(grant["id"], H.VIEWER, as_of="2026-07-01")
        self.assertEqual(past_due["derived_status"], "overdue")
        ext.transition_grant(grant["id"], "closed", H.MEMBER)
        closed = ext.get_grant(grant["id"], H.VIEWER, as_of="2026-07-01")
        self.assertEqual(closed["derived_status"], "closed")

    def test_grant_summary_counts_and_overdue(self):
        """426: the summary counts grants by recorded stage and
        derives the overdue count at the as-of date — counts only."""
        ext, _ = make_extensions()
        ext.create_grant("PROG-3", H.MEMBER, due_date="2026-06-30")
        other = ext.create_grant("PROG-4", H.MEMBER)
        ext.transition_grant(other["id"], "award", H.MEMBER)
        summary = ext.extension_summary(H.ADMIN, as_of="2026-07-01")
        self.assertEqual(summary["grants"]["total"], 2)
        self.assertEqual(summary["grants"]["by_stage"]["pre_award"], 1)
        self.assertEqual(summary["grants"]["by_stage"]["award"], 1)
        self.assertEqual(summary["grants"]["overdue"], 1)
        earlier = ext.extension_summary(H.ADMIN, as_of="2026-06-30")
        self.assertEqual(earlier["grants"]["overdue"], 0)


class TestDomainEcosystemRecords(unittest.TestCase):
    """Entries 427 + 428 + 429: supply-chain, healthcare, and
    emergency-response ecosystems as domain records over opaque
    references — recorded states and counts; nothing moves, no
    clinical data exists, nothing is dispatched."""

    def test_supply_events_verbatim_and_counted(self):
        """427: supply-chain events are recorded verbatim against a
        governed system and an opaque counterparty; counts by kind
        derive at read."""
        ext, _ = make_extensions()
        ext.record_supply_event(H.SYSTEM_REF, "CPTY-1", "shipment reported", H.MEMBER)
        ext.record_supply_event(H.SYSTEM_REF, "CPTY-2", "shipment reported", H.MEMBER)
        with self.assertRaises(NotFoundError):
            ext.record_supply_event("SYS-404", "CPTY-1", "x", H.MEMBER)
        summary = ext.extension_summary(H.ADMIN)
        self.assertEqual(summary["supply_events"]["total"], 2)
        self.assertEqual(
            summary["supply_events"]["by_kind"], {"shipment reported": 2},
        )

    def test_health_record_shape_holds_no_clinical_data(self):
        """428: the health program record shape is pinned to
        exactly the seven bookkeeping keys — there is no field that
        can hold a patient identifier or any clinical value, and the
        subject, when present, is an opaque reference only."""
        ext, _ = make_extensions()
        record = ext.record_health_record(
            "HLTH-PROG", "program enrollment", H.MEMBER,
            system_ref=H.SYSTEM_REF, subject_ref="opaque-ref-1",
        )
        self.assertEqual(
            set(record.keys()),
            {"id", "program_ref", "record_kind", "system_ref",
             "subject_ref", "recorded_by", "recorded_utc"},
        )
        summary = ext.extension_summary(H.ADMIN)
        self.assertEqual(
            summary["health_records"]["by_kind"], {"program enrollment": 1},
        )

    def test_emergency_event_lifecycle(self):
        """429: coordination events carry a guarded state lifecycle
        with history; the record holds no responder, location, or
        health field — nothing is dispatched or matched."""
        ext, _ = make_extensions()
        event = ext.create_emergency_event(H.SYSTEM_REF, "storm damage", H.MEMBER)
        self.assertEqual(event["state"], "reported")
        self.assertEqual(
            set(event.keys()),
            {"id", "system_ref", "event_kind", "state", "state_history",
             "recorded_by", "recorded_utc"},
        )
        with self.assertRaises(ValidationError):
            ext.transition_emergency_event(event["id"], "resolved", H.MEMBER)
        event = ext.transition_emergency_event(event["id"], "coordinating", H.MEMBER)
        event = ext.transition_emergency_event(event["id"], "resolved", H.MEMBER)
        self.assertEqual(
            [h["state"] for h in event["state_history"]],
            ["reported", "coordinating", "resolved"],
        )
        summary = ext.extension_summary(H.ADMIN)
        self.assertEqual(summary["emergency_events"]["by_state"]["resolved"], 1)


class TestAutomationRunRecords(unittest.TestCase):
    """Entry 430 (RPA half): automation run records — reported
    outcomes on the append-only ledger; no process executes here.
    The distributed-ledger half rides the provenance records
    (entry 424) and the Core's hash-chained audit; no chain
    consensus exists and none is claimed."""

    def test_run_records_are_reported_not_executed(self):
        """430: a run record stores the reported outcome verbatim
        with executed_here False; counts by outcome derive at read."""
        ext, _ = make_extensions()
        record = ext.record_automation_run("bot-ref-1", "completed (reported)", H.MEMBER)
        self.assertIs(record["executed_here"], False)
        ext.record_automation_run("bot-ref-1", "failed (reported)", H.MEMBER)
        summary = ext.extension_summary(H.ADMIN)
        self.assertEqual(summary["automation_runs"]["total"], 2)
        self.assertEqual(
            summary["automation_runs"]["by_outcome"],
            {"completed (reported)": 1, "failed (reported)": 1},
        )


class TestReferenceRecords(unittest.TestCase):
    """Entries 420 + 422 + 423 (stub-engine): labeled reference
    implementations — reference_stub records with the surface flag
    False. Nothing is monitored, no model runs, nothing is hosted."""

    def test_all_three_surfaces_labeled(self):
        """420/422/423: each surface's record carries
        reference_stub True and its own False flag
        (monitoring_here / inference_here / hosted_here)."""
        ext, _ = make_extensions()
        monitoring = ext.create_reference_record(
            "device_log_monitoring", "device-log feed (reference)", H.MEMBER,
        )
        self.assertIs(monitoring["reference_stub"], True)
        self.assertIs(monitoring["monitoring_here"], False)
        lake = ext.create_reference_record("ml_data_lake", "data lake (reference)", H.MEMBER)
        self.assertIs(lake["reference_stub"], True)
        self.assertIs(lake["inference_here"], False)
        factory = ext.create_reference_record(
            "software_factory_hosting", "software factory (reference)", H.MEMBER,
        )
        self.assertIs(factory["reference_stub"], True)
        self.assertIs(factory["hosted_here"], False)
        summary = ext.extension_summary(H.ADMIN)
        self.assertEqual(
            summary["reference_records"]["by_surface"],
            {"device_log_monitoring": 1, "ml_data_lake": 1,
             "software_factory_hosting": 1},
        )

    def test_unknown_surface_rejected(self):
        """420/422/423: an unregistered surface is a validation
        error and consumes no id."""
        ext, _ = make_extensions()
        with self.assertRaises(ValidationError):
            ext.create_reference_record("scoring_engine", "x", H.MEMBER)
        record = ext.create_reference_record("ml_data_lake", "x", H.MEMBER)
        self.assertEqual(record["id"], "ref-1")


class TestExtensionInvariants(unittest.TestCase):
    """Cross-surface doctrine pins: the no-score recursive scan over
    every record type and the summary; extension entries join the
    Core's hash-chained audit; extension writes fail closed."""

    def _exercise_every_surface(self, ext):
        ext.create_prediction("risk", H.SYSTEM_REF, "watch", H.MEMBER)
        ext.create_provenance("a-1", "s-1", H.MEMBER, content="body")
        definition = ext.create_process_definition("flow", {"steps": []}, H.ADMIN)
        ext.record_movement(H.SYSTEM_REF, "subj-1", "entry", H.MEMBER,
                            definition_id=definition["id"])
        ext.create_grant("PROG-9", H.MEMBER, due_date="2026-06-30")
        ext.record_supply_event(H.SYSTEM_REF, "CPTY-1", "reported", H.MEMBER)
        ext.record_health_record("HP", "enrollment", H.MEMBER)
        ext.create_emergency_event(H.SYSTEM_REF, "drill", H.MEMBER)
        ext.record_automation_run("bot-1", "reported done", H.MEMBER)
        ext.create_reference_record("ml_data_lake", "lake", H.MEMBER)

    def test_no_score_keys_anywhere_on_the_surface(self):
        """Doctrine: no key mentioning score / rating / grade /
        percent exists on any extension record or in the extension
        summary — the Core's posture scan, extended to the batch
        surface."""
        ext, _ = make_extensions()
        self._exercise_every_surface(ext)
        surfaces = [
            ext.list_predictions(H.ADMIN),
            ext.list_provenance(H.ADMIN),
            ext.list_process_definitions(H.ADMIN),
            ext.list_movements(H.ADMIN),
            ext.list_grants(H.ADMIN, as_of="2026-07-01"),
            ext.list_supply_events(H.ADMIN),
            ext.list_health_records(H.ADMIN),
            ext.list_emergency_events(H.ADMIN),
            ext.list_automation_runs(H.ADMIN),
            ext.list_reference_records(H.ADMIN),
            ext.extension_summary(H.ADMIN, as_of="2026-07-01"),
        ]
        for surface in surfaces:
            assert_no_score_keys(self, surface)

    def test_extension_writes_join_the_hash_chained_audit(self):
        """AU-9: extension mutations are entries in the same
        hash-chained audit log as the Core's, and the chain still
        verifies with them in it."""
        audit = AuditLog()
        ext, store = make_extensions(audit=audit)
        ext.create_prediction("risk", H.SYSTEM_REF, "watch", H.MEMBER)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("ext_prediction_create", actions)
        self.assertEqual(audit.verify_chain(), (True, None))

    def test_extension_write_fails_closed(self):
        """AU-5: when the audit write fails, the extension
        operation raises AuditWriteError, records nothing, and
        consumes no id — the repaired log's next successful write
        takes the id the failed one would have taken."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            ext, store = make_extensions(audit=audit)
            if os.path.exists(path):
                os.remove(path)
            os.mkdir(path)
            with self.assertRaises(AuditWriteError):
                ext.create_prediction("risk", H.SYSTEM_REF, "watch", H.MEMBER)
            self.assertEqual(ext.list_predictions(H.ADMIN), [])
            os.rmdir(path)
            record = ext.create_prediction("risk", H.SYSTEM_REF, "watch", H.MEMBER)
            self.assertEqual(record["id"], "pred-1")
            self.assertEqual(audit.verify_chain(), (True, None))


class TestGrantDerivationNegativeControl(unittest.TestCase):
    """Fresh negative control for the batch's new derivation.

    The traced claim: an open-stage grant due 2026-06-30 derives
    its stage at as_of 2026-06-30 and "overdue" at as_of
    2026-07-01. The mutant — the derivation with its overdue
    branch disabled — collapses both to the recorded stage.
    """

    GRANT = {"stage": "award", "due_date": "2026-06-30"}

    @staticmethod
    def _mutant_derive(grant, as_of=None):
        """The mutant: _grant_is_overdue disabled, so the overdue
        branch never fires (mirrors the live drill in
        tests/README.md, which patches the real function)."""
        return grant["stage"]

    def test_real_derivation_separates_the_canonical_pair(self):
        """The real derive_grant_status separates on-due-date from
        past-due-date for an open-stage grant."""
        self.assertEqual(
            derive_grant_status(self.GRANT, as_of="2026-06-30"), "award",
        )
        self.assertEqual(
            derive_grant_status(self.GRANT, as_of="2026-07-01"), "overdue",
        )

    def test_mutant_collapses_the_pair(self):
        """The mutant reads the recorded stage at both dates — it
        cannot produce "overdue" — and treating its output as the
        expected past-due outcome fails."""
        self.assertEqual(self._mutant_derive(self.GRANT, as_of="2026-07-01"), "award")
        with self.assertRaises(AssertionError):
            self.assertEqual(
                self._mutant_derive(self.GRANT, as_of="2026-07-01"), "overdue",
            )

    def test_end_to_end_through_the_extension(self):
        """End-to-end arm: the same separation through the
        extension's read views (get_grant with as_of)."""
        ext, _ = make_extensions()
        grant = ext.create_grant("PROG-NC", H.MEMBER, due_date="2026-06-30")
        ext.transition_grant(grant["id"], "award", H.MEMBER)
        self.assertEqual(
            ext.get_grant(grant["id"], H.VIEWER, as_of="2026-06-30")["derived_status"],
            "award",
        )
        self.assertEqual(
            ext.get_grant(grant["id"], H.VIEWER, as_of="2026-07-01")["derived_status"],
            "overdue",
        )
