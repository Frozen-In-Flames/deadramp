"""Shared helpers for the Learning Management L1 sibling-group test suite.

Traces to: the contract for Learning Management L1 (remainder sibling group) -- the
suite is runnable with ``PYTHONPATH=src`` from the group directory;
these helpers additionally put ``src/`` on the path so tests also run
standalone.

Canonical fixture: a store with an AuditLog, one learner (ref
"carol", label "Carol Learner", created by ADMIN since learner_write
is admin-only) and one course ("Safety Basics", code "SAFE-101",
created by ADMIN since catalog_write is admin-only).
ADMIN=alice/admin, INSTRUCTOR=bob/instructor, LEARNER=carol/learner,
AUDITOR=dana/auditor. Learner-scoped records for the LEARNER actor use
learner_ref "carol" (the actor's own name).

L1 extensions: organization / certificate / continuing-education
helpers for Core functions 15-17 (organization registry, certificate
award records, continuing education records).
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

from lms.access import User  # noqa: E402
from lms.audit import AuditLog  # noqa: E402
from lms.store import LmsStore  # noqa: E402

ADMIN = User("alice", "admin")
INSTRUCTOR = User("bob", "instructor")
LEARNER = User("carol", "learner")
AUDITOR = User("dana", "auditor")

USERS = {
    "alice": "admin",
    "bob": "instructor",
    "carol": "learner",
    "dana": "auditor",
}
USERS_REGISTRY = USERS


def fresh_store(audit=None):
    """A bare LmsStore with nothing in it."""
    if audit is None:
        audit = AuditLog()
    return LmsStore(audit=audit)


def make_store(audit=None):
    """Fresh store + one learner + one course.

    Returns (store, learner, course): learner ref "carol" created by
    ADMIN, course "Safety Basics" (code "SAFE-101") created by ADMIN.
    """
    store = fresh_store(audit=audit)
    learner = store.create_learner("carol", "Carol Learner", ADMIN)
    course = store.create_course("Safety Basics", ADMIN, code="SAFE-101")
    return store, learner, course


def make_organization(store, ref="acme", label="Acme Health",
                      portal_label="Acme Portal", actor=None):
    """Core 15 helper: create an organization (organization_write is
    admin-only, so the default actor is ADMIN)."""
    return store.create_organization(
        ref, label, actor or ADMIN, portal_label=portal_label)


def make_org_store(audit=None):
    """Fresh store + one organization + one learner in that organization.

    Returns (store, organization, learner): organization ref "acme"
    created by ADMIN, learner ref "carol" created by ADMIN with
    org_ref "acme".
    """
    store = fresh_store(audit=audit)
    organization = make_organization(store)
    learner = store.create_learner("carol", "Carol Learner", ADMIN,
                                   org_ref="acme")
    return store, organization, learner


def make_certificate(store, learner_ref="carol", title="Safety Certificate",
                     actor=None, **kwargs):
    """Core 16 helper: record a certificate award (default actor
    INSTRUCTOR, who holds certificate_write)."""
    return store.record_certificate(learner_ref, title, actor or INSTRUCTOR,
                                    **kwargs)


def make_ce_record(store, learner_ref="carol", activity_ref="act-1",
                   credit_text="3.5 credits", actor=None, **kwargs):
    """Core 17 helper: record a continuing-education record (default
    actor INSTRUCTOR, who holds continuing_ed_write); the credit text
    is stored verbatim."""
    return store.record_continuing_education(
        learner_ref, activity_ref, credit_text, actor or INSTRUCTOR,
        **kwargs)
