"""Live smoke driver (not a unittest): real server, real requests.

Run: PYTHONPATH=src python3 tests/smoke.py

Flow: health; organization + members; candidate; requisition;
pipeline; placement; in-bounds movement; out-of-bounds movement
rejected (400); event + registration + check-in; assessment with
a verbatim outcome label; video interview; report shows the
derived stage distribution. Prints SMOKE OK on success.
"""

import http.client
import json
import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))

from talentmgmt.audit import AuditLog  # noqa: E402
from talentmgmt.service import USERS, make_server  # noqa: E402
from talentmgmt.store import TalentMgmtStore  # noqa: E402


def call(port, method, path, user=None, role=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"Content-Type": "application/json"}
    if user is not None:
        headers["X-User"] = user
    if role is not None:
        headers["X-Role"] = role
    conn.request(method, path,
                 body=json.dumps(body) if body is not None else None,
                 headers=headers)
    response = conn.getresponse()
    raw = response.read()
    conn.close()
    return response.status, json.loads(raw) if raw else {}


def main():
    audit = AuditLog()
    store = TalentMgmtStore(audit=audit)
    server = make_server("127.0.0.1", 0, store, audit, dict(USERS))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, body = call(port, "GET", "/health")
        assert (status, body) == (200, {"status": "ok"}), (status, body)
        print("GET /health -> 200 {\"status\": \"ok\"}")

        status, org = call(port, "POST", "/organizations", "alice", "admin",
                           {"org_ref": "ORG-SMOKE", "label": "Smoke Org"})
        assert status == 201, (status, org)
        org_id = org["id"]
        print("organization %s created (201)" % org_id)
        status, _ = call(port, "POST", "/organizations/%s/members" % org_id,
                         "alice", "admin", {"username": "bob"})
        assert status == 200, status

        status, _ = call(port, "POST",
                         "/organizations/%s/candidates" % org_id,
                         "bob", "member",
                         {"candidate_ref": "CAN-SMOKE",
                          "label": "Smoke Candidate"})
        assert status == 201, status
        status, requisition = call(
            port, "POST", "/organizations/%s/requisitions" % org_id,
            "bob", "member",
            {"requisition_ref": "REQ-SMOKE", "title": "Smoke Role"})
        assert status == 201, (status, requisition)
        status, pipeline = call(
            port, "POST", "/organizations/%s/pipelines" % org_id,
            "bob", "member",
            {"pipeline_ref": "PIP-SMOKE",
             "requisition_id": requisition["id"],
             "stages": ["Applied", "Screen", "Interview", "Decision"]})
        assert status == 201, (status, pipeline)
        status, placement = call(
            port, "POST",
            "/organizations/%s/pipelines/%s/placements"
            % (org_id, pipeline["id"]),
            "bob", "member",
            {"placement_ref": "PLC-SMOKE", "candidate_ref": "CAN-SMOKE"})
        assert status == 201, (status, placement)
        placement_id = placement["id"]
        status, _ = call(
            port, "POST",
            "/organizations/%s/placements/%s/movements"
            % (org_id, placement_id),
            "bob", "member", {"movement_ref": "MOV-1", "stage_index": 2})
        assert status == 201, status
        print("movement MOV-1 recorded (201); derived stage: Interview")
        status, body = call(
            port, "POST",
            "/organizations/%s/placements/%s/movements"
            % (org_id, placement_id),
            "bob", "member", {"movement_ref": "MOV-2", "stage_index": 4})
        assert status == 400, (status, body)
        print("out-of-bounds movement -> 400: %s" % body["error"])

        status, event = call(
            port, "POST", "/organizations/%s/events" % org_id,
            "bob", "member",
            {"event_ref": "EVT-SMOKE", "title": "Smoke Fair",
             "kind": "virtual", "starts_at": "2030-04-01T15:00:00+00:00"})
        assert status == 201, (status, event)
        status, registration = call(
            port, "POST",
            "/organizations/%s/events/%s/registrations"
            % (org_id, event["id"]),
            "bob", "member",
            {"registration_ref": "REG-SMOKE",
             "candidate_ref": "CAN-SMOKE"})
        assert status == 201, (status, registration)
        status, _ = call(
            port, "POST",
            "/organizations/%s/registrations/%s/check-in"
            % (org_id, registration["id"]),
            "bob", "member")
        assert status == 200, status
        print("event registration + check-in recorded")

        status, assessment = call(
            port, "POST", "/organizations/%s/assessments" % org_id,
            "bob", "member",
            {"assessment_ref": "ASM-SMOKE",
             "candidate_ref": "CAN-SMOKE",
             "instrument_label": "Smoke Inventory"})
        assert status == 201, (status, assessment)
        status, done = call(
            port, "POST",
            "/organizations/%s/assessments/%s/complete"
            % (org_id, assessment["id"]),
            "bob", "member", {"outcome_label": "Completed at the fair"})
        assert status == 200, (status, done)
        assert done["outcome_label"] == "Completed at the fair", done
        status, _ = call(
            port, "POST", "/organizations/%s/interviews" % org_id,
            "bob", "member",
            {"interview_ref": "INT-SMOKE", "candidate_ref": "CAN-SMOKE",
             "kind": "video"})
        assert status == 201, status
        print("assessment completed with verbatim label; video "
              "interview scheduled")

        status, report = call(port, "GET",
                              "/organizations/%s/report" % org_id,
                              "alice", "admin")
        assert status == 200, (status, report)
        assert report["placements_by_stage"] == {"Interview": 1}, report
        assert report["checked_in_count"] == 1, report
        print("report: placements_by_stage={'Interview': 1}, "
              "checked_in_count=1")
        print("SMOKE OK")
        return 0
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())
