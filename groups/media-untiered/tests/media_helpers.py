"""Shared fixtures for the media tests.

House shape, mirrored from the sibling groups: every test module
builds a fresh store wired to an in-memory audit log, with one
actor per role -- alice (admin), bob (operator), carol (viewer).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from media.access import User  # noqa: E402
from media.audit import AuditLog  # noqa: E402
from media.store import MediaStore  # noqa: E402

ADMIN = User("alice", "admin")
OPERATOR = User("bob", "operator")
VIEWER = User("carol", "viewer")

ORG_REF = "ORG-0001"
ORG_LABEL = "Agency video office (records label)"
SRC_REF = "NET-HQ"
SRC_LABEL = "HQ agency network"
DST_REF = "CLOUD-DEST"
DST_LABEL = "Commercial cloud destination"
ROUTE_LABEL = "HQ to cloud contribution"
DEVICE_REF = "ENC-01"
DEVICE_LABEL = "Field encoder 1"
PROFILE_LABEL = "Low latency profile"
PROFILE_SETTINGS = "mode=ll; buffer=minimal"
STARTED = "2026-01-10T10:00:00+00:00"
STOPPED = "2026-01-10T11:00:00+00:00"
AT = "2026-01-10T10:05:00+00:00"


def make_store():
    audit = AuditLog()
    return MediaStore(audit=audit), audit


def make_org(store, actor=ADMIN):
    return store.create_organization(actor, ORG_REF, ORG_LABEL)


def make_endpoints(store, org, actor=OPERATOR, tag=""):
    source = store.create_endpoint(
        actor, org["id"], SRC_REF + tag, SRC_LABEL, "agency_network")
    destination = store.create_endpoint(
        actor, org["id"], DST_REF + tag, DST_LABEL, "cloud_destination")
    return source, destination


def make_route(store, org, actor=OPERATOR, tag="", **kwargs):
    source, destination = make_endpoints(store, org, actor, tag=tag)
    route = store.create_route(
        actor, org["id"], ROUTE_LABEL, source["id"], destination["id"],
        **kwargs)
    return route, source, destination


def make_device(store, org, actor=OPERATOR, endpoint=None):
    return store.create_device(
        actor, org["id"], DEVICE_REF, DEVICE_LABEL,
        kind_label="encoder",
        endpoint_id=endpoint["id"] if endpoint is not None else None)
