"""Live smoke driver (not a unittest): real server, real requests.

Run: PYTHONPATH=src python3 tests/smoke.py

Flow: health; organization + members; provider; tenancy; environment
activated; template; deployment activated; second activation of the
same workload refused (400, the slot rule); account + utilization;
report shows the counts. Prints SMOKE OK on success.
"""

import http.client
import json
import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))

from cloudinfra.audit import AuditLog  # noqa: E402
from cloudinfra.service import USERS, make_server  # noqa: E402
from cloudinfra.store import CloudInfraStore  # noqa: E402


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
    raw = response.read().decode("utf-8")
    conn.close()
    return response.status, json.loads(raw) if raw else {}


def main():
    audit = AuditLog()
    store = CloudInfraStore(audit=audit)
    server = make_server("127.0.0.1", 0, store, audit, dict(USERS))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, body = call(port, "GET", "/health")
        assert status == 200 and body["status"] == "ok", (status, body)

        status, org = call(port, "POST", "/organizations", "alice", "admin",
                           {"org_ref": "org-smoke", "label": "Smoke Org"})
        assert status == 201, (status, org)
        oid = org["id"]
        status, _ = call(port, "POST", "/organizations/%s/members" % oid,
                         "alice", "admin", {"username": "bob"})
        assert status == 200, status

        status, provider = call(
            port, "POST", "/organizations/%s/providers" % oid,
            "bob", "member",
            {"provider_ref": "prv-aws", "label": "AWS US East/West"})
        assert status == 201, (status, provider)
        status, tenancy = call(
            port, "POST", "/organizations/%s/tenancies" % oid,
            "bob", "member",
            {"tenancy_ref": "ten-main", "label": "Main",
             "hosting_model": "boundary_protected",
             "provider_id": provider["id"]})
        assert status == 201, (status, tenancy)
        status, env = call(
            port, "POST", "/organizations/%s/environments" % oid,
            "bob", "member",
            {"environment_ref": "env-prod", "label": "Production",
             "tenancy_id": tenancy["id"], "residency_label": "U.S. soil"})
        assert status == 201, (status, env)
        status, env = call(
            port, "POST", "/organizations/%s/environments/%s/status"
            % (oid, env["id"]), "bob", "member", {"status": "active"})
        assert status == 200 and env["status"] == "active", (status, env)

        status, dep = call(
            port, "POST", "/organizations/%s/deployments" % oid,
            "bob", "member",
            {"tenancy_id": tenancy["id"], "deployment_ref": "dep-1",
             "workload_ref": "wl-search",
             "environment_id": env["id"],
             "encryption_label": "encryption at rest"})
        assert status == 201, (status, dep)
        status, dep2 = call(
            port, "POST", "/organizations/%s/deployments" % oid,
            "bob", "member",
            {"tenancy_id": tenancy["id"], "deployment_ref": "dep-2",
             "workload_ref": "wl-search"})
        assert status == 201, (status, dep2)
        status, dep = call(
            port, "POST", "/organizations/%s/deployments/%s/activate"
            % (oid, dep["id"]), "bob", "member")
        assert status == 200 and dep["status"] == "active", (status, dep)
        status, body = call(
            port, "POST", "/organizations/%s/deployments/%s/activate"
            % (oid, dep2["id"]), "bob", "member")
        assert status == 400 and "error" in body, (status, body)

        status, account = call(
            port, "POST", "/organizations/%s/accounts" % oid,
            "bob", "member",
            {"account_ref": "acc-1", "label": "Tenant account"})
        assert status == 201, (status, account)
        status, util = call(
            port, "POST", "/organizations/%s/accounts/%s/utilization"
            % (oid, account["id"]), "bob", "member",
            {"period": "2026-09", "units": 420})
        assert status == 201 and util["units"] == 420, (status, util)

        status, report = call(port, "GET", "/organizations/%s/report" % oid,
                              "bob", "member")
        assert status == 200, (status, report)
        assert report["deployments"]["by_status"] == \
            {"active": 1, "recorded": 1}, report
        assert report["utilization"]["units_by_period"] == {"2026-09": 420}
        assert report["tenancies"]["total"] == 1, report
    finally:
        server.shutdown()
        server.server_close()
    print("SMOKE OK")


if __name__ == "__main__":
    sys.exit(main())
