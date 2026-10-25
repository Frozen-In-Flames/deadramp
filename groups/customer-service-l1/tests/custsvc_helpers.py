"""Shared helpers for the custsvc test suite."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from custsvc.access import User  # noqa: E402
from custsvc.audit import AuditLog  # noqa: E402
from custsvc.store import CustsvcStore  # noqa: E402

ADMIN = User(name="alice", role="admin")
AGENT = User(name="bob", role="agent")
VIEWER = User(name="carol", role="viewer")

PAST_DUE = "2020-01-02T00:00:00+00:00"
FUTURE_DUE = "2999-01-02T00:00:00+00:00"
NOW = "2026-10-25T12:00:00+00:00"


def make_store(audit=None):
    """Fresh store + audit + one requester + two responders.

    Returns (store, audit, requester, responder1, responder2).
    """
    if audit is None:
        audit = AuditLog()
    store = CustsvcStore(audit=audit)
    requester = store.create_requester("citizen-001", "Citizen One", ADMIN)
    rsp1 = store.create_responder("Responder One", "tier-1", ADMIN)
    rsp2 = store.create_responder("Responder Two", "tier-1", ADMIN)
    return store, audit, requester, rsp1, rsp2


def make_case(store, requester, **kwargs):
    kwargs.setdefault("title", "Cannot access benefits portal")
    kwargs.setdefault("body", "Login fails with a generic error.")
    return store.create_case(kwargs.pop("title"), kwargs.pop("body"),
                             requester["ref"], AGENT, **kwargs)
