"""Append-only audit log with optional JSONL persistence.

Each entry is a dict with keys ``ts`` (UTC ISO-8601 timestamp),
``actor``, ``action``, ``target`` and ``details``. Entries are only
ever appended -- there is no update or delete API -- and, when a
path is given, each entry is also written as one JSON line to that
file.
"""

import json
import os
import threading
from datetime import datetime, timezone


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


class AuditLog:
    """An append-only audit trail, in memory and optionally on disk."""

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

    def record(self, actor, action, target, details=None):
        """Append one entry and return it."""
        entry = {
            "ts": _utc_now(),
            "actor": actor_name(actor),
            "action": action,
            "target": target,
            "details": details,
        }
        with self._lock:
            self._entries.append(entry)
            if self.path is not None:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry) + "\n")
                    fh.flush()
        return dict(entry)

    def entries(self):
        """Return a copy of all entries, oldest first."""
        with self._lock:
            result = []
            for entry in self._entries:
                copied = dict(entry)
                if isinstance(copied.get("details"), dict):
                    copied["details"] = dict(copied["details"])
                result.append(copied)
            return result
