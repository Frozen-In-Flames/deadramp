"""Shared helpers for the Finance untiered set's test suite
(the founding Finance L2 build's suite, carried with the code).

Traces to: UNION-SPEC.md "Implementation contract" — the suite is runnable
with ``PYTHONPATH=src`` from the group directory; these helpers additionally
put ``src/`` (and the tests directory itself) on the path so the tests also
run standalone, mirroring ``accounting_helpers.py`` in the Accounting L2
group.

Canonical fixture (used across the suite): a program named
``acme-program`` owned by MEMBER (bob, platform role ``member``) with
VIEWER (carol, platform role ``viewer``) added as a second program
member. ADMIN (alice, platform role ``admin``) is deliberately *not* a
program member — she reaches programs through the platform admin role.
OUTSIDER (dave, platform role ``member``) belongs to no fixture program,
which makes him the canonical non-member for membership-boundary tests.
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

from finance.access import User  # noqa: E402
from finance.audit import AuditLog  # noqa: E402
from finance.store import FinanceStore  # noqa: E402

ADMIN = User("alice", "admin")
MEMBER = User("bob", "member")
VIEWER = User("carol", "viewer")
OUTSIDER = User("dave", "member")

# Registry as the HTTP layer / CLI sees it (demo identities per contract,
# plus dave as a second member-role identity for non-member checks).
USERS_REGISTRY = {
    "alice": "admin",
    "bob": "member",
    "carol": "viewer",
    "dave": "member",
}

PROGRAM_NAME = "acme-program"

# Canonical scenario dates / periods (one pay period, 2026-01, plus a
# second period, 2026-02, for period-filter tests).
PERIOD = "2026-01"
PERIOD_OTHER = "2026-02"
DATE_JAN = "2026-01-10"
DATE_JAN_2 = "2026-01-20"
DATE_FEB = "2026-02-10"


def fresh_store(audit=None):
    """A bare FinanceStore with no programs (for id-sequence tests).

    Traces to: UNION-SPEC Core 1 (Programs & members) — id sequences
    are observed from an empty store so the first id is deterministic.
    """
    return FinanceStore(audit=audit)


def make_store(audit=None):
    """Fresh store + audit log + the canonical program.

    Returns ``(store, audit, program_id)``: a FinanceStore with an
    AuditLog attached (the one passed in, or a new one), a program
    owned by MEMBER, and VIEWER added as a second member by the owner.

    Traces to: UNION-SPEC Core 1 (Programs & members) and Core 11
    (Audit log) — the fixture program exercises ``create_program``
    (audits ``program_create``) and ``add_member`` (``member_add``).
    """
    if audit is None:
        audit = AuditLog()
    store = FinanceStore(audit=audit)
    program = store.create_program(PROGRAM_NAME, MEMBER)
    store.add_member(program["id"], VIEWER.name, MEMBER)
    return store, audit, program["id"]


def make_participant(store, program_id, ref, kind, actor=MEMBER):
    """Create one participant of ``kind`` and return its dict.

    Traces to: UNION-SPEC Core 2 (Participant & traveler registry) —
    ``create_participant`` with an opaque ``ref`` and a kind.
    """
    return store.create_participant(program_id, ref, kind, actor)


def make_employee(store, program_id, ref="emp-1", actor=MEMBER):
    """Create an ``employee`` participant (the earned-wage kind).

    Traces to: UNION-SPEC Core 2 (Participant registry) / Core 3
    (Earned-wage accrual & access records) — only employees accrue.
    """
    return make_participant(store, program_id, ref, "employee", actor)


def make_traveler(store, program_id, ref="trav-1", actor=MEMBER):
    """Create a ``traveler`` participant (the booking kind).

    Traces to: UNION-SPEC Core 2 (Participant registry) / Core 4
    (Travel booking records) — only travelers hold bookings.
    """
    return make_participant(store, program_id, ref, "traveler", actor)


def make_accrual(store, program_id, participant_id, period=PERIOD,
                 earned_cents=100000, actor=MEMBER):
    """Record an accrual for an employee in ``period``.

    Traces to: UNION-SPEC Core 3 (Earned-wage accrual & access
    records) — ``record_accrual`` with integer cents.
    """
    return store.record_accrual(
        program_id, participant_id, period, earned_cents, actor
    )


def make_request(store, program_id, participant_id, period=PERIOD,
                 amount_cents=10000, date=DATE_JAN, actor=MEMBER):
    """File one earned-wage access request and return its dict.

    Traces to: UNION-SPEC Core 3 (Earned-wage access) / Core 8
    (Workflow & approvals) — ``request_access`` in status
    ``requested``.
    """
    return store.request_access(
        program_id, participant_id, period, amount_cents, date, actor
    )


def approved_request(store, program_id, participant_id, period=PERIOD,
                     amount_cents=10000, date=DATE_JAN, creator=MEMBER,
                     decider=ADMIN):
    """File a request and approve it with an actor other than its creator.

    The decider defaults to ADMIN — never the creator, as separation
    of duties (Core 8 / AC-5) requires. Returns the updated (approved)
    request dict.

    Traces to: UNION-SPEC Core 3 (Earned-wage access) + Core 8
    (Workflow & approvals, AC-5 separation of duties).
    """
    request = make_request(
        store, program_id, participant_id, period=period,
        amount_cents=amount_cents, date=date, actor=creator,
    )
    return store.decide_access(program_id, request["id"], True, decider)


def disbursed_request(store, program_id, participant_id, period=PERIOD,
                      amount_cents=10000, request_date=DATE_JAN,
                      disbursement_date=DATE_JAN_2, creator=MEMBER,
                      decider=ADMIN):
    """File, approve (by another), and disburse one access request.

    Returns ``(request_after_disbursement, disbursement)`` — the
    request is re-read so its status is ``disbursed`` and its
    ``disbursement_id`` is set.

    Traces to: UNION-SPEC Core 3 (Earned-wage access) — a disbursement
    record records, after the fact, that an approved amount moved on
    external rails; and Core 8 (Workflow & approvals).
    """
    approved = approved_request(
        store, program_id, participant_id, period=period,
        amount_cents=amount_cents, date=request_date, creator=creator,
        decider=decider,
    )
    disbursement = store.record_disbursement(
        program_id, approved["id"], disbursement_date, creator,
        method="payroll",
    )
    return store.get_access_request(program_id, approved["id"], creator), disbursement


def make_booking(store, program_id, participant_id, kind="air",
                 start_date=DATE_JAN, end_date="2026-01-12",
                 amount_cents=30000, actor=MEMBER):
    """Create one travel booking record for a traveler.

    Traces to: UNION-SPEC Core 4 (Travel booking records) —
    ``create_booking`` in status ``recorded``.
    """
    return store.create_booking(
        program_id, participant_id, kind, start_date, end_date,
        amount_cents, actor,
    )
