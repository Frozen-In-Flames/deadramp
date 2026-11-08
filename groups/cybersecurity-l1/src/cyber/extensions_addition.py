"""Final GAPS batch, second unit — Cybersecurity L1 addition surface.

Clean-room extension surface for the one open entry of the
"Remainder Addition — Cybersecurity L1 (+1 fork)" section of the
repo-root ``GAPS.md`` (see ``BATCH-ADDITION.md`` in the group
directory): the crowdsourced security testing & disclosure
coordination platform registered from the HackerOne addition
fork's described function (ADDENDUM.md section 5).

The entry names a **human researcher marketplace and a platform
operated against live systems**: recruiting, matching, and
managing a community of independent security researchers,
engagement management, and vulnerability disclosure coordination.
None of that is a records function this substrate can perform —
there is no community here to recruit, no researcher is matched
or managed, no target is tested, and no disclosure is coordinated
with anyone. The entry was drafted stub-engine and closes as
drafted: a **labeled reference implementation**. What this module
holds is the registry side of such a platform's operation —
program records, engagement records, and disclosure records whose
outcome labels are stored exactly as the external platform
reported them — with every record carrying ``reference_stub:
true`` and its not-performed-here flags in its own shape.

The findings such engagements produce are **not** created here:
they are ingestible by the founding Core today, in the same
register scanner output lands in, and a disclosure record here
names one only by an opaque finding reference. No finding is
ingested, scored, or triaged by this module, and the founding
build's published deterministic formulas in :mod:`cyber.store`
remain the only scoring in the package. Extension views are
counts only, derived at read, never stored.

Category and tier discipline are the founding build's, unchanged:
references are **opaque** tokens (the validators are reused from
:mod:`cyber.extensions` — IP-shaped, URL, and hostname values are
rejected at the boundary, and no record shape can hold a
credential, an address, or PII); access control reuses the
founding permission matrix with audit actions prefixed ``exta_``;
denied attempts are recorded to the founding build's plain
append-only audit log with a ``:denied`` suffix. There is no
auditor role and no hash-chained audit at L1, and none is added
here.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .extensions import (
    _validate_non_empty,
    _validate_ref,
)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


ENGAGEMENT_TRANSITIONS = {
    "invited": {"active", "declined", "cancelled"},
    "active": {"completed", "cancelled"},
    "completed": set(),
    "declined": set(),
    "cancelled": set(),
}

DISCLOSURE_TRANSITIONS = {
    "reported": {"triaged", "closed"},
    "triaged": {"disclosed", "closed"},
    "disclosed": {"closed"},
    "closed": set(),
}


class ExtensionAdditionStore:
    """In-memory register for the crowdsourced-testing reference
    surface.

    Ids are sequential per collection with fixed prefixes. Every
    operation validates fully before it mutates anything: a failed
    operation consumes no id and changes nothing. Successful
    mutations and denied attempts are recorded to the attached
    audit log (when one is attached).
    """

    _COLLECTIONS = (
        "programs",
        "engagements",
        "disclosures",
    )

    def __init__(self, audit=None):
        self.audit = audit
        self._data = {name: {} for name in self._COLLECTIONS}
        self._counters = {name: 0 for name in self._COLLECTIONS}
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _require(self, actor, action, audit_action, target):
        """Enforce a founding permission, auditing a denial first."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", target)
                raise

    def _insert(self, collection, prefix, fields, actor, audit_action):
        self._counters[collection] += 1
        record_id = "%s-%d" % (prefix, self._counters[collection])
        now = _utc_now()
        record = {"id": record_id}
        record.update(fields)
        record["created_by"] = actor_name(actor)
        record["created_utc"] = now
        record["updated_utc"] = now
        self._data[collection][record_id] = record
        self._audit(actor, audit_action, record_id)
        return copy.deepcopy(record)

    def _get(self, collection, record_id, what):
        record = self._data[collection].get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _list(self, collection, actor, audit_action, filters=None):
        self._require(actor, "read", audit_action, collection)
        with self._lock:
            records = list(self._data[collection].values())
            for key, wanted in (filters or {}).items():
                if wanted is not None:
                    records = [r for r in records if r.get(key) == wanted]
            return copy.deepcopy(records)

    def _latest_label(self, records, key):
        """Latest-value seam: the current reported label is the
        *last* record's. Every "latest" derivation on this surface
        routes through here; this is the fresh negative control's
        mutation target (see tests/README.md)."""
        return records[-1][key]

    def _program_disclosures(self, program_id):
        engagement_ids = {
            record_id
            for record_id, record in self._data["engagements"].items()
            if record["program_id"] == program_id
        }
        return [
            record
            for record in self._data["disclosures"].values()
            if record["engagement_id"] in engagement_ids
        ]

    # -- disclosure programs (labeled reference records) -----------------

    def register_program(self, program_ref, title, scope_ref, actor):
        """Register a reference record for an external crowdsourced
        testing / disclosure program. Labeled ``reference_stub``:
        no marketplace is operated here, no researcher is recruited
        or matched, and no disclosure is coordinated — the record
        states each of those in its own fields."""
        _validate_ref(program_ref, "program reference")
        _validate_non_empty(title, "program title")
        _validate_ref(scope_ref, "scope reference")
        self._require(actor, "manage_assets", "exta_program_register", program_ref)
        with self._lock:
            return self._insert(
                "programs", "program",
                {
                    "program_ref": program_ref,
                    "title": title,
                    "scope_ref": scope_ref,
                    "reference_stub": True,
                    "marketplace_operated_here": False,
                    "researchers_recruited_here": False,
                    "coordinated_here": False,
                },
                actor, "exta_program_register",
            )

    def list_programs(self, actor):
        return self._list("programs", actor, "exta_program_list")

    # -- engagements (labeled reference records) --------------------------

    def create_engagement(self, program_id, engagement_ref, researcher_ref, actor):
        """Record an engagement under a registered program: a
        researcher named by opaque reference only, engaged by the
        external platform. Nothing is matched, invited, or tested
        here; the lifecycle below tracks the engagement as the
        platform reports it."""
        _validate_ref(engagement_ref, "engagement reference")
        _validate_ref(researcher_ref, "researcher reference")
        self._require(actor, "manage_risks", "exta_engagement_create", program_id)
        with self._lock:
            self._get("programs", program_id, "program")
            return self._insert(
                "engagements", "eng",
                {
                    "program_id": program_id,
                    "engagement_ref": engagement_ref,
                    "researcher_ref": researcher_ref,
                    "status": "invited",
                    "reference_stub": True,
                    "matched_here": False,
                    "tested_here": False,
                },
                actor, "exta_engagement_create",
            )

    def transition_engagement(self, engagement_id, new_status, actor):
        self._require(actor, "triage", "exta_engagement_transition", engagement_id)
        with self._lock:
            record = self._get("engagements", engagement_id, "engagement")
            current = record["status"]
            if new_status not in ENGAGEMENT_TRANSITIONS[current]:
                raise ValidationError(
                    "engagement cannot move from %r to %r" % (current, new_status)
                )
            record["status"] = new_status
            record["updated_utc"] = _utc_now()
            self._audit(actor, "exta_engagement_transition", engagement_id,
                        details={"from": current, "to": new_status})
            return copy.deepcopy(record)

    def list_engagements(self, actor, program_id=None, status=None):
        return self._list("engagements", actor, "exta_engagement_list",
                          {"program_id": program_id, "status": status})

    # -- disclosures (labeled reference records) --------------------------

    def record_disclosure(self, engagement_id, finding_ref, reported_label, actor):
        """Record one disclosure under an engagement, as reported
        by the external platform: the finding it concerns is named
        by an opaque reference only (the finding itself lives in
        the caller's world and, when it lands here, in the founding
        Core's register — never created by this module), and the
        outcome label is stored exactly as reported. No disclosure
        is coordinated, validated, or scored here."""
        _validate_ref(finding_ref, "finding reference")
        _validate_non_empty(reported_label, "reported label")
        self._require(actor, "ingest", "exta_disclosure_record", engagement_id)
        with self._lock:
            self._get("engagements", engagement_id, "engagement")
            return self._insert(
                "disclosures", "disc",
                {
                    "engagement_id": engagement_id,
                    "finding_ref": finding_ref,
                    "reported_label": reported_label,
                    "status": "reported",
                    "reference_stub": True,
                    "coordinated_here": False,
                },
                actor, "exta_disclosure_record",
            )

    def transition_disclosure(self, disclosure_id, new_status, actor):
        self._require(actor, "triage", "exta_disclosure_transition", disclosure_id)
        with self._lock:
            record = self._get("disclosures", disclosure_id, "disclosure")
            current = record["status"]
            if new_status not in DISCLOSURE_TRANSITIONS[current]:
                raise ValidationError(
                    "disclosure cannot move from %r to %r" % (current, new_status)
                )
            record["status"] = new_status
            record["updated_utc"] = _utc_now()
            self._audit(actor, "exta_disclosure_transition", disclosure_id,
                        details={"from": current, "to": new_status})
            return copy.deepcopy(record)

    def list_disclosures(self, actor, engagement_id=None, status=None):
        return self._list("disclosures", actor, "exta_disclosure_list",
                          {"engagement_id": engagement_id, "status": status})

    # -- derived views (counts and latest labels, at read) -----------------

    def program_view(self, actor, program_id):
        """Derived view of one program record: engagement and
        disclosure counts and the latest reported disclosure label,
        computed at read. The stored program record carries none of
        these keys (pinned by test)."""
        self._require(actor, "read", "exta_program_view", program_id)
        with self._lock:
            program = copy.deepcopy(self._get("programs", program_id, "program"))
            engagements = [
                r for r in self._data["engagements"].values()
                if r["program_id"] == program_id
            ]
            by_status = {}
            for record in engagements:
                by_status[record["status"]] = by_status.get(record["status"], 0) + 1
            disclosures = self._program_disclosures(program_id)
            program["engagement_count"] = len(engagements)
            program["engagements_by_status"] = by_status
            program["disclosure_count"] = len(disclosures)
            program["latest_disclosure_label"] = (
                self._latest_label(disclosures, "reported_label")
                if disclosures else None
            )
            return program

    def engagement_view(self, actor, engagement_id):
        """Derived view of one engagement record: its disclosure
        count and latest reported disclosure label, computed at
        read. The stored engagement record carries neither key."""
        self._require(actor, "read", "exta_engagement_view", engagement_id)
        with self._lock:
            engagement = copy.deepcopy(
                self._get("engagements", engagement_id, "engagement"))
            disclosures = [
                r for r in self._data["disclosures"].values()
                if r["engagement_id"] == engagement_id
            ]
            engagement["disclosure_count"] = len(disclosures)
            engagement["latest_disclosure_label"] = (
                self._latest_label(disclosures, "reported_label")
                if disclosures else None
            )
            return engagement

    def addition_summary(self, actor):
        """Derived summary over the addition collections: record
        counts only, computed at read, never stored. By design
        there is no score, rate, or grade anywhere in this view."""
        self._require(actor, "read", "exta_addition_summary", "extensions_addition")
        with self._lock:
            return {
                "records": {
                    name: len(self._data[name]) for name in self._COLLECTIONS
                },
                "total": sum(
                    len(records) for records in self._data.values()
                ),
            }
