"""Privacy-discipline tests (HARD PRIVACY RULE) [L3].

Traces to: this category's hard privacy rule (UNION-SPEC.md) --
records are records and opaque references only: NO entity shape can
hold a name, email, phone number, date of birth, diagnosis, clinical
note, or any other real-identifier field, and no record anywhere
carries clinical content or a diagnostic field. Unknown JSON keys
are refused at the HTTP boundary (400) before the store is called,
so a caller cannot smuggle such a field into a record by adding it
to a request body; measurement records refuse extra fields exactly
like every other endpoint.
"""

import http.client
import json
import threading
import unittest

import health_helpers as H
from health.service import USERS, make_server
from health.store import HealthStore
from health.audit import AuditLog

FORBIDDEN_FIELDS = {
    "name", "email", "phone", "phone_number", "dob", "date_of_birth",
    "address", "ssn", "diagnosis", "note", "notes", "clinical_note",
    "identifier", "member_number", "insurer", "insurer_name",
    "benefits",
}

EXPECTED_KEYS = {
    "participant": {"id", "participant_ref", "kind",
                    "created_by", "created_utc"},
    "program": {"id", "title", "kind", "code", "description",
                "created_by", "created_utc"},
    "enrollment": {"id", "participant_id", "program_id", "kind", "status",
                   "created_by", "created_utc", "derived_status"},
    "measurement": {"id", "participant_id", "program_id", "metric_name",
                    "value", "unit", "recorded_on",
                    "created_by", "created_utc"},
    "plan": {"id", "participant_id", "program_id", "title", "kind",
             "due_date", "completed_on", "created_by", "created_utc",
             "derived_status"},
    "activity": {"id", "participant_id", "program_id", "title", "kind",
                 "starts_at", "ends_at", "state",
                 "created_by", "created_utc"},
    "eligibility": {"id", "participant_id", "program_id", "plan_ref",
                    "coverage_start", "coverage_end",
                    "created_by", "created_utc", "derived_status"},
}


def _all_entities(store, program, participant):
    enrollment = store.create_enrollment(
        participant["id"], program["id"], H.CLINICIAN)
    measurement = store.record_measurement(
        participant["id"], "glucose", 120, "mg/dL", "2026-06-10",
        H.CLINICIAN, program_id=program["id"])
    plan = store.create_plan(
        participant["id"], program["id"], "Daily checks",
        "2026-06-01", H.CLINICIAN)
    activity = store.create_activity(
        participant["id"], "Clinic visit", "2026-07-01T09:00:00Z",
        H.CLINICIAN, program_id=program["id"])
    eligibility = store.create_eligibility(
        participant["id"], "plan-alpha", "2026-01-01", H.ADMIN,
        coverage_end="2026-12-31")
    return {
        "participant": participant, "program": program,
        "enrollment": enrollment, "measurement": measurement,
        "plan": plan, "activity": activity, "eligibility": eligibility,
    }


class TestPrivacyShapes(unittest.TestCase):
    """Privacy: entity shapes carry no real-identifier or clinical fields."""

    def setUp(self):
        self.store, self.program, self.participant = H.make_store()
        self.entities = _all_entities(self.store, self.program, self.participant)

    def test_no_forbidden_fields_anywhere(self):
        """Privacy: no entity has a name/email/phone/dob/diagnosis/
        note/identifier/insurer field."""
        for kind, entity in self.entities.items():
            bad = FORBIDDEN_FIELDS & set(entity.keys())
            self.assertEqual(bad, set(), "%s carries forbidden fields %s" % (kind, bad))

    def test_exact_key_sets_per_entity(self):
        """Privacy: every entity carries EXACTLY its contract key set
        -- there is no spare field in which clinical content or an
        identifier could hide."""
        for kind, entity in self.entities.items():
            self.assertEqual(set(entity.keys()), EXPECTED_KEYS[kind], kind)

    def test_participant_keyed_by_opaque_reference_only(self):
        """Privacy: participants are keyed by the caller-supplied
        opaque participant_ref ("carol"), never by a real name."""
        self.assertEqual(self.participant["participant_ref"], "carol")

    def test_no_record_carries_clinical_content(self):
        """Privacy: no entity anywhere carries a diagnostic field or
        clinical free text -- the string 'diagnosis' appears in no
        key of any entity, and the report/scorecard aggregates carry
        counts only, with no clinical field either."""
        for kind, entity in self.entities.items():
            for key in entity.keys():
                self.assertNotIn("diagnosis", key, kind)
                self.assertNotIn("note", key, kind)
        report = self.store.report(H.ADMIN, as_of="2026-06-15")
        flat_keys = set(report.keys())
        self.assertEqual(FORBIDDEN_FIELDS & flat_keys, set())
        card = self.store.scorecard(
            self.program["id"], H.ADMIN, as_of="2026-06-15")
        self.assertEqual(FORBIDDEN_FIELDS & set(card.keys()), set())


class TestPrivacyHttpBoundary(unittest.TestCase):
    """Privacy over HTTP: unknown JSON keys are refused (400) at the
    boundary, before the store is called, and nothing is stored."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = HealthStore(audit=cls.audit)
        cls.server = make_server(
            "127.0.0.1", 0, cls.store, cls.audit, dict(USERS))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def _post(self, path, headers, body):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdrs = dict(headers)
        hdrs.setdefault("Content-Type", "application/json")
        conn.request("POST", path, body=json.dumps(body), headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
        conn.close()
        return status, json.loads(raw.decode("utf-8"))

    def _seed(self):
        admin = {"X-User": "alice", "X-Role": "admin"}
        suffix = str(len(self.store.list_participants(H.ADMIN)) + 1)
        status, program = self._post(
            "/programs", admin, {"title": "Privacy Program %s" % suffix})
        self.assertEqual(status, 201)
        status, participant = self._post(
            "/participants", admin,
            {"participant_ref": "ref-privacy-%s" % suffix})
        self.assertEqual(status, 201)
        return program, participant

    def test_measurement_refuses_extra_fields(self):
        """Privacy (SI-10/SI-12): POST /measurements with a smuggled
        'diagnosis' or 'note' key -> 400, and no measurement is stored."""
        program, participant = self._seed()
        clinician = {"X-User": "bob", "X-Role": "clinician"}
        base = {"participant_id": participant["id"], "metric_name": "glucose",
                "value": 120, "unit": "mg/dL", "recorded_on": "2026-06-10",
                "program_id": program["id"]}
        for extra in ({"diagnosis": "diabetes"}, {"note": "clinical note"},
                      {"name": "Real Name"}):
            body = dict(base)
            body.update(extra)
            status, payload = self._post("/measurements", clinician, body)
            self.assertEqual(status, 400, extra)
            self.assertIn("error", payload)
        self.assertEqual(self.store.list_measurements(H.ADMIN), [])

    def test_participant_and_program_refuse_identifier_fields(self):
        """Privacy: POST /participants with name/email/phone/dob and
        POST /programs with a diagnosis key -> 400, nothing stored."""
        admin = {"X-User": "alice", "X-Role": "admin"}
        before_participants = len(self.store.list_participants(H.ADMIN))
        before_programs = len(self.store.list_programs(H.ADMIN))
        for extra in ({"name": "Real Name"}, {"email": "a@example.com"},
                      {"phone": "555-0100"}, {"dob": "2000-01-01"}):
            body = {"participant_ref": "ref-smuggle"}
            body.update(extra)
            status, _ = self._post("/participants", admin, body)
            self.assertEqual(status, 400, extra)
        status, _ = self._post(
            "/programs", admin, {"title": "T", "diagnosis": "x"})
        self.assertEqual(status, 400)
        self.assertEqual(len(self.store.list_participants(H.ADMIN)),
                         before_participants)
        self.assertEqual(len(self.store.list_programs(H.ADMIN)),
                         before_programs)

    def test_plan_and_eligibility_refuse_clinical_and_identifier_fields(self):
        """Privacy: POST /plans with a 'note' key and POST /eligibility
        with a 'member_number' key -> 400, nothing stored."""
        program, participant = self._seed()
        clinician = {"X-User": "bob", "X-Role": "clinician"}
        admin = {"X-User": "alice", "X-Role": "admin"}
        status, _ = self._post(
            "/plans", clinician,
            {"participant_id": participant["id"], "program_id": program["id"],
             "title": "T", "due_date": "2026-06-01", "note": "x"})
        self.assertEqual(status, 400)
        status, _ = self._post(
            "/eligibility", admin,
            {"participant_id": participant["id"], "plan_ref": "p",
             "coverage_start": "2026-01-01", "member_number": "123"})
        self.assertEqual(status, 400)
        self.assertEqual(self.store.list_plans(H.ADMIN), [])
        self.assertEqual(self.store.list_eligibilities(H.ADMIN), [])


if __name__ == "__main__":
    unittest.main()
