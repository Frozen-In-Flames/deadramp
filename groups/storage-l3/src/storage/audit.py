"""Append-only audit log with optional JSONL persistence.

Each entry is a dict with keys ``ts`` (UTC ISO-8601 timestamp),
``actor``, ``action``, ``target`` and ``details``. Entries are only
ever appended -- there is no update or delete API -- and, when a path
is given, each entry is also written as one JSON line to that file.

High-baseline uplifts (FedRAMP High / CMMC L3-adjacent) [L3]:

- **Tamper-evident hash chain (AU-9, AU-3).** Every entry additionally
  carries ``seq`` (0-based sequence number), ``prev_hash`` and
  ``hash``. ``hash`` is the SHA-256 hex digest of the canonical JSON
  (``json.dumps(..., sort_keys=True, separators=(",", ":"))``) of
  ``{seq, ts, actor, action, target, details, prev_hash}``; the
  genesis entry's ``prev_hash`` is ``"0" * 64``.
  :meth:`AuditLog.verify_chain` recomputes the chain over the current
  entries so any in-place edit, deletion, or file tampering is
  detected at the first bad index.
- **Fail closed (AU-5).** If the JSONL append raises ``OSError``,
  :meth:`AuditLog.record` rolls back the in-memory append and raises
  :class:`~storage.errors.AuditWriteError`; in-memory state and file
  never diverge silently, and callers let the error propagate so the
  audited operation does not proceed.
- **Audit reduction & search (AU-7).** :meth:`AuditLog.query` returns
  entries filtered by actor, action, target and/or an ISO timestamp
  window (``since`` / ``until`` compared against the ``ts`` string).

This module's chain, fail-closed, and query mechanics are the proven
uplift of the sibling High groups (``groups/analytics-l3``, carried
through ``groups/development-tools-l3``) applied to this package (our
own Apache-2.0 code); the L2 version of this file was append-only
without them.
"""

import hashlib
import json
import os
import threading
from datetime import datetime, timezone

from .errors import AuditWriteError

GENESIS_PREV_HASH = "0" * 64


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def actor_name(actor):
    """Normalize an actor (string, User-like object, or None) to a name."""
    if actor is None:
        return None
    name = getattr(actor, "name", None)
    if isinstance(name, str):
        return name
    return str(actor)


def _entry_hash(seq, ts, actor, action, target, details, prev_hash):
    """SHA-256 hex of the canonical JSON of an entry's hashed fields."""
    payload = {
        "seq": seq,
        "ts": ts,
        "actor": actor,
        "action": action,
        "target": target,
        "details": details,
        "prev_hash": prev_hash,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AuditLog:
    """An append-only, hash-chained audit trail, in memory and on disk."""

    def __init__(self, path=None):
        self.path = path
        self._entries = []
        self._lock = threading.Lock()
        if path is not None:
            directory = os.path.dirname(os.path.abspath(path))
            os.makedirs(directory, exist_ok=True)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except ValueError:
                            continue
                        if isinstance(entry, dict):
                            self._entries.append(entry)

    def record(self, actor, action, target, details=None, ts=None):
        """Append one entry and return it.

        The entry is hash-chained to the previous entry. If a JSONL
        path is configured and the append raises ``OSError``, the
        in-memory append is rolled back and :class:`AuditWriteError`
        is raised (AU-5 fail closed). ``ts`` overrides the generated
        timestamp (used by tests and log replay).
        """
        with self._lock:
            seq = len(self._entries)
            prev_hash = (
                self._entries[-1].get("hash", GENESIS_PREV_HASH)
                if self._entries
                else GENESIS_PREV_HASH
            )
            ts = ts if ts is not None else _utc_now()
            actor = actor_name(actor)
            entry = {
                "ts": ts,
                "actor": actor,
                "action": action,
                "target": target,
                "details": details,
                "seq": seq,
                "prev_hash": prev_hash,
                "hash": _entry_hash(
                    seq, ts, actor, action, target, details, prev_hash
                ),
            }
            self._entries.append(entry)
            if self.path is not None:
                try:
                    with open(self.path, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(entry) + "\n")
                        fh.flush()
                except OSError as exc:
                    # Roll back: memory and file must never diverge.
                    self._entries.pop()
                    raise AuditWriteError(
                        "audit write failed for action %r: %s" % (action, exc)
                    ) from exc
        return dict(entry)

    def entries(self):
        """Return a copy of all entries, oldest first."""
        with self._lock:
            return [self._copy_entry(entry) for entry in self._entries]

    @staticmethod
    def _copy_entry(entry):
        copied = dict(entry)
        if isinstance(copied.get("details"), dict):
            copied["details"] = dict(copied["details"])
        return copied

    def verify_chain(self):
        """Recompute the hash chain over the current entries (AU-9).

        Returns ``(ok, first_bad_index)``: ``(True, None)`` when every
        entry carries intact hash fields linking it to its predecessor,
        otherwise ``(False, i)`` where ``i`` is the index of the first
        entry that is missing hash fields or whose stored ``seq`` /
        ``prev_hash`` / ``hash`` does not match the recomputation.
        """
        with self._lock:
            entries = list(self._entries)
        prev_hash = GENESIS_PREV_HASH
        for index, entry in enumerate(entries):
            seq = entry.get("seq")
            stored_prev = entry.get("prev_hash")
            stored_hash = entry.get("hash")
            if seq is None or stored_prev is None or stored_hash is None:
                return (False, index)
            if seq != index or stored_prev != prev_hash:
                return (False, index)
            expected = _entry_hash(
                seq,
                entry.get("ts"),
                entry.get("actor"),
                entry.get("action"),
                entry.get("target"),
                entry.get("details"),
                stored_prev,
            )
            if expected != stored_hash:
                return (False, index)
            prev_hash = stored_hash
        return (True, None)

    def query(self, actor=None, action=None, target=None, since=None, until=None):
        """Return entries matching all given filters (AU-7).

        ``since`` / ``until`` are ISO timestamp strings compared
        lexicographically against each entry's ``ts`` string (inclusive
        on both ends). Unfiltered parameters match everything.
        """
        with self._lock:
            entries = [self._copy_entry(entry) for entry in self._entries]
        result = []
        for entry in entries:
            if actor is not None and entry.get("actor") != actor:
                continue
            if action is not None and entry.get("action") != action:
                continue
            if target is not None and entry.get("target") != target:
                continue
            if since is not None and str(entry.get("ts", "")) < since:
                continue
            if until is not None and str(entry.get("ts", "")) > until:
                continue
            result.append(entry)
        return result
