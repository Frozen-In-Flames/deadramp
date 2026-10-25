"""Shared helpers for the Accounting L2 merged-build test suite.

Traces to: UNION-SPEC.md "Implementation contract" — the suite is runnable
with ``PYTHONPATH=src`` from the group directory; these helpers additionally
put ``src/`` (and the tests directory itself) on the path so the tests also
run standalone, mirroring ``collab_helpers.py`` in the Collaboration L2
group.

Canonical fixture (used across the suite): a book named ``acme-books``
owned by MEMBER (bob, platform role ``member``) with VIEWER (carol,
platform role ``viewer``) added as a second book member. ADMIN (alice,
platform role ``admin``) is deliberately *not* a book member — she reaches
books through the platform admin role. OUTSIDER (dave, platform role
``member``) belongs to no fixture book, which makes him the canonical
non-member for membership-boundary tests.
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

from accounting.access import User  # noqa: E402
from accounting.audit import AuditLog  # noqa: E402
from accounting.store import AccountingStore  # noqa: E402

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

BOOK_NAME = "acme-books"

# The canonical chart: (short key, code, name, account type).
CHART_SPEC = [
    ("cash", "1000", "Cash", "asset"),
    ("payable", "2000", "AccountsPayable", "liability"),
    ("equity", "3000", "OwnersEquity", "equity"),
    ("revenue", "4000", "ServiceRevenue", "revenue"),
    ("rent", "5000", "RentExpense", "expense"),
]

# Canonical scenario dates (one fiscal period, 2026-01, plus a second
# period, 2026-02, for period-filter tests).
DATE_JAN = "2026-01-05"
DATE_JAN_2 = "2026-01-10"
DATE_JAN_3 = "2026-01-15"
DATE_FEB = "2026-02-05"
PERIOD_JAN = "2026-01"
PERIOD_FEB = "2026-02"


def fresh_store(audit=None):
    """A bare AccountingStore with no books (for id-sequence tests)."""
    return AccountingStore(audit=audit)


def make_store(audit=None):
    """Fresh store + audit log + the canonical book.

    Returns ``(store, book_id)``: an AccountingStore with an AuditLog
    attached (the one passed in, or a new one), a book owned by MEMBER,
    and VIEWER added as a second member by the owner.
    """
    if audit is None:
        audit = AuditLog()
    store = AccountingStore(audit=audit)
    book = store.create_book(BOOK_NAME, MEMBER)
    store.add_member(book["id"], VIEWER.name, MEMBER)
    return store, book["id"]


def make_chart(store, book_id, actor=MEMBER):
    """Create the canonical five-account chart in the book.

    Returns a dict keyed by short name: ``cash`` (Cash, asset, 1000),
    ``payable`` (AccountsPayable, liability, 2000), ``equity``
    (OwnersEquity, equity, 3000), ``revenue`` (ServiceRevenue, revenue,
    4000) and ``rent`` (RentExpense, expense, 5000). Each value is the
    account dict returned by ``create_account``.
    """
    chart = {}
    for key, code, name, account_type in CHART_SPEC:
        chart[key] = store.create_account(
            book_id, code, name, account_type, actor
        )
    return chart


# Backwards-friendly alias: the chart helper under a verb name.
create_chart = make_chart


def balanced_lines(debit_account_id, credit_account_id, amount_cents):
    """Two one-sided lines that balance at ``amount_cents``."""
    return [
        {"account_id": debit_account_id, "debit_cents": amount_cents},
        {"account_id": credit_account_id, "credit_cents": amount_cents},
    ]


def approve_entry_by_other(store, book_id, entry_id, creator=MEMBER):
    """Approve a pending entry with an actor other than its creator.

    Picks ADMIN when the creator is not ADMIN, else MEMBER — either way
    the approver differs from the creator, as separation of duties
    (Core 10 / AC-5) requires. Returns the updated entry dict.
    """
    approver = ADMIN if creator.name != ADMIN.name else MEMBER
    return store.approve_entry(book_id, entry_id, approver)


def post_entry(store, book_id, date, memo, lines, creator=MEMBER,
               approver=ADMIN):
    """Post an entry end to end: create, submit, approve by another.

    The entry is created and submitted by ``creator`` and approved by
    ``approver`` (ADMIN by default — never the creator, per separation
    of duties). Returns the final, posted entry dict.
    """
    entry = store.create_entry(book_id, date, memo, lines, creator)
    store.submit_entry(book_id, entry["id"], creator)
    return store.approve_entry(book_id, entry["id"], approver)


def post_investment(store, book_id, chart, amount_cents=100000,
                    date=DATE_JAN, actor=MEMBER):
    """Posted entry: owner invests cash (debit Cash / credit Equity)."""
    return post_entry(
        store, book_id, date, "Owner investment",
        balanced_lines(chart["cash"]["id"], chart["equity"]["id"],
                       amount_cents),
        creator=actor,
    )


def post_revenue(store, book_id, chart, amount_cents=50000,
                 date=DATE_JAN_2, actor=MEMBER):
    """Posted entry: services earned (debit Cash / credit Revenue)."""
    return post_entry(
        store, book_id, date, "Services earned",
        balanced_lines(chart["cash"]["id"], chart["revenue"]["id"],
                       amount_cents),
        creator=actor,
    )


def post_rent(store, book_id, chart, amount_cents=20000,
              date=DATE_JAN_3, actor=MEMBER):
    """Posted entry: rent paid (debit RentExpense / credit Cash)."""
    return post_entry(
        store, book_id, date, "Rent paid",
        balanced_lines(chart["rent"]["id"], chart["cash"]["id"],
                       amount_cents),
        creator=actor,
    )


def build_scenario(store, book_id, chart):
    """The canonical reports scenario, all posted in period 2026-01.

    Owner invests 100000 cents, the business earns 50000, and pays
    20000 rent — so Cash is 130000, equity 100000, revenue 50000,
    expenses 20000 and net income 30000. Returns the three entries.
    """
    return (
        post_investment(store, book_id, chart),
        post_revenue(store, book_id, chart),
        post_rent(store, book_id, chart),
    )
