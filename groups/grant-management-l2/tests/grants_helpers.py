"""Shared helpers for the Grant Management L2 merged-build test suite.

Traces to: UNION-SPEC.md "Implementation contract" — the suite is
runnable with ``PYTHONPATH=src`` from the group directory; these
helpers additionally put ``src/`` (and the tests directory itself)
on the path so the tests also run standalone, mirroring
``finance_helpers.py`` in the Finance L2 group.

Canonical fixture (used across the suite): a grant program named
``community-grants`` created by MEMBER (bob, platform role
``member``) with a budget of 1,000,000 cents and a 2026 window, and
an applicant organization ``ORG-100``. STAFF (erin, platform role
``member``) is added as a second program member by ADMIN — she is
the canonical decider, because the program's applications are
submitted by bob and the decider is never the submitter (AC-5).
ADMIN (alice) is deliberately *not* a program member — she reaches
programs through the platform admin role. OUTSIDER (dave, platform
role ``member``) belongs to no fixture program. VIEWER (carol,
platform role ``viewer``) is added as a program member in the notes
tests to prove internal notes stay internal even for members whose
role is read-only.
"""

import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_SRC_DIR = os.path.join(_GROUP_ROOT, "src")
if os.path.isdir(_SRC_DIR) and _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from grants.access import User  # noqa: E402
from grants.audit import AuditLog  # noqa: E402
from grants.store import GrantsStore  # noqa: E402

ADMIN = User("alice", "admin")
MEMBER = User("bob", "member")
STAFF = User("erin", "member")
VIEWER = User("carol", "viewer")
OUTSIDER = User("dave", "member")

# Registry as the HTTP layer / CLI sees it (demo identities per
# contract, plus erin and dave for member-role checks).
USERS_REGISTRY = {
    "alice": "admin",
    "bob": "member",
    "carol": "viewer",
    "erin": "member",
    "dave": "member",
}

PROGRAM_NAME = "community-grants"
BUDGET_CENTS = 1_000_000
OPENS_AT = "2026-01-01"
CLOSES_AT = "2026-12-31"
NOW_OPEN = "2026-06-01T00:00:00+00:00"

SHA256_A = "a" * 64
SHA256_B = "0123456789abcdef" * 4


def fresh_store(audit=None):
    """A bare GrantsStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return GrantsStore(audit=audit)


def make_program(store, actor=MEMBER, **overrides):
    """Create the canonical grant program (or a variant)."""
    kwargs = {
        "name": PROGRAM_NAME,
        "title": "Community Grants Program",
        "sponsor_ref": "SPONSOR-1",
        "opens_at": OPENS_AT,
        "closes_at": CLOSES_AT,
        "budget_cents": BUDGET_CENTS,
    }
    kwargs.update(overrides)
    return store.create_program(actor, **kwargs)


def make_store(audit=None):
    """Fresh store + canonical program + canonical applicant org.

    Returns (store, program, org). STAFF is a program member.
    """
    store = fresh_store(audit=audit)
    program = make_program(store)
    store.add_member(ADMIN, program["id"], STAFF.name)
    org = store.create_organization(MEMBER, "ORG-100", "Community Builders Alliance")
    return store, program, org


def make_application(store, program, org, actor=MEMBER, **overrides):
    """Create a draft application by ``actor`` (default bob)."""
    kwargs = {
        "requested_cents": 400_000,
        "summary": "After-school tutoring expansion",
    }
    kwargs.update(overrides)
    return store.create_application(actor, program["id"], org["id"], **kwargs)


def make_under_review(store, program, org, **overrides):
    """An application submitted by bob and under review."""
    app = make_application(store, program, org, **overrides)
    store.submit_application(MEMBER, app["id"])
    store.start_review(STAFF, app["id"])
    return store.get_application(STAFF, app["id"])


def make_award(store, program, org, amount_cents=400_000, **overrides):
    """A decided application and its award. Returns (application, result)."""
    app = make_under_review(store, program, org, **overrides)
    result = store.decide_application(STAFF, app["id"], True,
                                      amount_cents=amount_cents,
                                      note="Approved as reviewed")
    return store.get_application(STAFF, app["id"]), result
