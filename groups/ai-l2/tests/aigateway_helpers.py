"""Shared helpers for the Artificial Intelligence (AI) L2 test suite.

Traces to: UNION-SPEC.md "Implementation contract" — the suite is
runnable with ``PYTHONPATH=src`` from the group directory; these helpers
additionally put ``src/`` (and the tests directory itself) on the path so
the tests also run standalone, mirroring ``collab_helpers.py`` in the
Collaboration L2 group.

Canonical fixture: ADMIN (alice, admin), MEMBER (bob, member), VIEWER
(carol, viewer), plus OTHER_MEMBER (dave, member) as a second member who
owns nothing in the fixture — the canonical non-owner for owner-or-admin
checks. Scratch files (audit JSONL) live only under the group's
``scratch/`` directory, never /tmp.
"""

import os
import shutil
import sys
import uuid

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_SRC_DIR = os.path.join(_GROUP_ROOT, "src")
_SCRATCH_DIR = os.path.join(_GROUP_ROOT, "scratch")
if os.path.isdir(_SRC_DIR) and _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from aigateway.access import User  # noqa: E402
from aigateway.audit import AuditLog  # noqa: E402
from aigateway.store import AIGatewayStore  # noqa: E402

ADMIN = User("alice", "admin")
MEMBER = User("bob", "member")
VIEWER = User("carol", "viewer")
OTHER_MEMBER = User("dave", "member")

USERS_REGISTRY = {
    "alice": "admin",
    "bob": "member",
    "carol": "viewer",
    "dave": "member",
}


def fresh_store(audit=None, zero_persistence=False):
    """A bare AIGatewayStore (audit attached only if given)."""
    return AIGatewayStore(audit=audit, zero_persistence=zero_persistence)


def make_store(audit=None, zero_persistence=False):
    """Fresh store + AuditLog + one echo model registered by ADMIN.

    Returns ``(store, audit, model)``.
    """
    if audit is None:
        audit = AuditLog()
    store = AIGatewayStore(audit=audit, zero_persistence=zero_persistence)
    model = store.register_model("echoer", "echo", ADMIN, provider="reference",
                                 capabilities=["text"])
    return store, audit, model


def register_echo(store, name="echoer", actor=ADMIN):
    """Register a plain echo model."""
    return store.register_model(name, "echo", actor)


def register_template_model(store, name="templater", template="Say: {prompt}",
                            actor=ADMIN):
    """Register a template-responder model."""
    return store.register_model(
        name, "template", actor, config={"template": template}
    )


def register_rules_model(store, name="ruler", actor=ADMIN):
    """Register a rules-responder model: 'hello' -> greeting, else default."""
    return store.register_model(
        name, "rules", actor,
        config={
            "rules": [{"match": "hello", "response": "Hi there"}],
            "default": "No rule matched",
        },
    )


def make_scratch_dir():
    """A unique directory under the group's scratch/ (never /tmp)."""
    os.makedirs(_SCRATCH_DIR, exist_ok=True)
    path = os.path.join(_SCRATCH_DIR, "test-" + uuid.uuid4().hex[:12])
    os.makedirs(path)
    return path


def remove_scratch_dir(path):
    """Remove a directory previously made by make_scratch_dir()."""
    if path and os.path.isdir(path) and _SCRATCH_DIR in os.path.abspath(path):
        shutil.rmtree(path, ignore_errors=True)
