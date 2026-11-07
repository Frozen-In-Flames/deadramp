"""Final GAPS batch extensions for Legal & Policy L2.

Clean-room, standard-library-only extensions for the 10 open
entries of the GAPS.md section "Remainder Addition -- Legal &
Policy L2 (+6 forks)" (inventory idx 561-570; see ``BATCH.md`` in
the group directory for the per-entry disposition). This module is
a wrapper around :class:`LegalPolStore`; every core module is
untouched and byte-identical to the shipped build.

**The founding privacy rule binds absolutely, here as in the
core:** documents exist in this substrate ONLY as metadata +
SHA-256 records in the core document registry. No entity shape in
this module has a field that can hold document content, extracted
text, a summary, a redaction, a signature value, or query text --
those fields **do not exist**. Methods accept only their named
parameters, so a caller cannot smuggle a forbidden field into a
record (pinned by tests: an unexpected keyword raises
``TypeError``). Matters, custodians, reviewers, requesters,
counterparties, and signers are opaque caller-supplied references.

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form -- records plus deterministic derivations over
the group's OWN records (core records and extension records):

- eDiscovery collection/processing is matter and collection
  records over core document references, with counts stored as
  reported; nothing is collected or processed here.
- Review is assignment records plus reviewer decisions recorded
  verbatim over document references; the reviewed content is never
  present, and a decision changes no core document record.
- Production is records; disposition is DECISION records whose
  eligibility is derived at read from recorded states (a document
  under an active legal hold is not eligible, and the decision
  write enforces it). Nothing is produced, destroyed, archived,
  or retained here -- retention enforcement is the embedding
  organization's records schedule (PLATFORM-LAYER.md decision 4).
- Legal hold is hold records whose current state derives at read
  from recorded state labels, with coverage over matter document
  references; preservation itself is performed by the custodian's
  systems, never here.
- AI document analysis is analysis-request records plus reported
  outputs held as opaque result references; no inference runs
  here and no output text exists in any shape. "Analytics" is a
  deterministic counts derivation over held records.
- OCR/extraction is job records with reported counts and result
  references; no extracted text exists in any shape.
- FOIA is case records with recorded states, exemption
  determinations recorded verbatim, and release records; nothing
  is released here and the request itself is an opaque reference.
- Contract lifecycle is agreement records over opaque party
  references with lifecycle state derived at read; no agreement
  is executed here.
- The two stub-engine entries ship as labeled reference
  implementations: every record carries ``reference_stub: True``
  and state ``recorded_reference_only``. The e-signature surface
  holds envelope and ceremony records only -- no field can hold
  a signature value, and nothing is signed. Agreement workflow
  definitions are held as data; per the house doctrine the
  registry never executes, and registering a definition changes
  no agreement record.

Doctrines carried from the core: derived-never-stored for every
computed value (current hold/FOIA/agreement state, coverage,
eligibility, counts); validation before mutation, so a failed
operation consumes no id and changes nothing; append-only audit
on the core store's log with ``ext_``-prefixed actions for every
successful extension mutation, and denied write attempts recorded
with a ``:denied`` suffix; RBAC via :mod:`legalpol.access` --
extension writes map to the core ``document_write`` action (the
extension surface is records over the document/matter substrate)
and reads resolve the agency through the core store, which
enforces ``agency_read`` and the agency membership boundary on
every operation.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

MATTER_KINDS = (
    "litigation", "investigation", "regulatory", "foia", "contract", "other",
)
REVIEW_DECISION_LABELS = (
    "responsive", "not_responsive", "privileged", "confidential",
    "needs_follow_up",
)
HOLD_STATES = (
    "reported_issued", "reported_acknowledged", "reported_released",
)
HOLD_ACTIVE_STATES = ("reported_issued", "reported_acknowledged")
DISPOSITION_LABELS = (
    "destroy_reported", "archive_reported", "retain_reported",
)
ANALYSIS_KINDS = (
    "summarization", "classification", "redaction", "assisted_review",
    "analytics",
)
FOIA_STATES = (
    "reported_received", "reported_processing",
    "reported_partially_released", "reported_released",
    "reported_denied", "reported_closed",
)
AGREEMENT_STATES = (
    "reported_draft", "reported_in_negotiation", "reported_executed",
    "reported_active", "reported_expired", "reported_terminated",
)
CEREMONY_LABELS = (
    "reported_sent", "reported_viewed", "reported_signed",
    "reported_declined", "reported_completed", "reported_voided",
)

_REFERENCE_STATE = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _count(value, what):
    """A non-negative integer count; booleans and floats rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be a non-negative integer" % (what,))
    if value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


def _cents(value, what):
    """An integer number of cents; booleans and floats rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents" % (what,))
    if value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


def _string_list(value, what):
    if not isinstance(value, (list, tuple)):
        raise ValidationError("%s must be a list of strings" % (what,))
    items = list(value)
    if not items:
        raise ValidationError("%s must be a non-empty list" % (what,))
    for item in items:
        _non_empty(item, what)
    return items


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class LegalPolExtensions:
    """Extension surface wrapping one :class:`LegalPolStore`."""

    def __init__(self, store):
        self.store = store
        self._matters = {}
        self._collections = {}
        self._collection_links = {}
        self._processing_runs = {}
        self._review_assignments = {}
        self._review_decisions = {}
        self._productions = {}
        self._production_links = {}
        self._disposition_decisions = {}
        self._holds = {}
        self._hold_states = {}
        self._hold_coverages = {}
        self._analysis_requests = {}
        self._analysis_results = {}
        self._extraction_jobs = {}
        self._foia_cases = {}
        self._foia_states = {}
        self._foia_determinations = {}
        self._foia_releases = {}
        self._agreements = {}
        self._agreement_states = {}
        self._envelopes = {}
        self._ceremonies = {}
        self._workflow_definitions = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    def _guard(self, actor, audit_action):
        """Enforce the extension write permission before any state
        change. Extension writes map to the core ``document_write``
        action. A denied attempt is recorded on the audit log with
        a ``:denied`` suffix before the error propagates; a missing
        actor is denied outright. A plain string carries identity
        but no role (the service layer enforces its role), matching
        the core convention."""
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for 'document_write'")
        if hasattr(actor, "role"):
            try:
                require(actor, "document_write")
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": "document_write"})
                raise

    def _agency(self, actor, agency_id):
        """Resolve an agency through the core store, which enforces
        the ``agency_read`` permission and the membership boundary
        (the platform admin reaches every agency)."""
        return self.store.get_agency(agency_id, actor)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _check_agency_of(self, actor, record):
        self._agency(actor, record["agency_id"])

    def _create(self, table, prefix, fields, actor, audit_action):
        record = {"id": self._next_id(prefix)}
        record.update(fields)
        record["created_by"] = actor_name(actor)
        record["created_utc"] = _utc_now()
        table[record["id"]] = record
        self._audit(actor, audit_action, record["id"])
        return copy.deepcopy(record)

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    def _in_agency(self, table, agency_id):
        return [r for r in table.values() if r["agency_id"] == agency_id]

    def _in_matter(self, table, matter_id):
        return [r for r in table.values() if r["matter_id"] == matter_id]

    def _check_ref_unique(self, records, field, value, scope):
        for existing in records:
            if existing[field] == value:
                raise ValidationError(
                    "%s %r is already recorded in this %s"
                    % (field, value, scope))

    def _matter(self, actor, agency_id, matter_id):
        self._agency(actor, agency_id)
        matter = self._get(self._matters, matter_id, "matter")
        if matter["agency_id"] != agency_id:
            raise NotFoundError(
                "matter not found in agency %s: %r" % (agency_id, matter_id))
        return matter

    def _document_in_matter(self, actor, matter):
        """Resolve a core document and require it to sit in the
        matter's workspace (the core's own scoping style)."""
        def resolve(document_id):
            document = self.store.get_document(
                matter["agency_id"], document_id, actor)
            if document["workspace_id"] != matter["workspace_id"]:
                raise NotFoundError(
                    "document not found in matter workspace %s: %r"
                    % (matter["workspace_id"], document_id))
            return document
        return resolve

    # -- Matters (substrate for idx 561-567) ---------------------------
    # A matter is the case container every discovery record hangs
    # from: an opaque matter reference in a core workspace. The
    # matter's substance is never here -- ``content_collected_here``
    # is False on every matter record.

    def create_matter(self, actor, agency_id, workspace_id, matter_ref,
                      kind, label=None):
        """Create one matter record. Action: document_write."""
        self._guard(actor, "ext_matter_create")
        self._agency(actor, agency_id)
        self.store.get_workspace(agency_id, workspace_id, actor)
        _non_empty(matter_ref, "matter_ref")
        if kind not in MATTER_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(MATTER_KINDS),))
        if label is not None:
            _non_empty(label, "label")
        with self._lock:
            self._check_ref_unique(
                [m for m in self._matters.values()
                 if m["workspace_id"] == workspace_id],
                "matter_ref", matter_ref, "workspace")
            return self._create(
                self._matters, "mat-",
                {"agency_id": agency_id, "workspace_id": workspace_id,
                 "matter_ref": matter_ref, "kind": kind, "label": label,
                 "content_collected_here": False},
                actor, "ext_matter_create")

    def get_matter(self, actor, agency_id, matter_id):
        """Return one matter record. Action: agency_read."""
        self._agency(actor, agency_id)
        matter = self._get(self._matters, matter_id, "matter")
        if matter["agency_id"] != agency_id:
            raise NotFoundError(
                "matter not found in agency %s: %r" % (agency_id, matter_id))
        return copy.deepcopy(matter)

    def list_matters(self, actor, agency_id, workspace_id=None):
        """List matter records in an agency. Action: agency_read."""
        self._agency(actor, agency_id)
        matters = self._in_agency(self._matters, agency_id)
        if workspace_id is not None:
            matters = [m for m in matters
                       if m["workspace_id"] == workspace_id]
        return copy.deepcopy(self._sorted(matters))

    # -- eDiscovery processing & collection (idx 561, built) -----------
    # Records form: a collection is a registry record over core
    # document references -- a source label and counts stored as
    # reported. Collection and processing happen on the source
    # systems; ``content_collected_here`` and
    # ``processing_performed_here`` are False on every record.

    def record_collection(self, actor, agency_id, matter_id, collection_ref,
                          source_label, reported_document_count,
                          reported_byte_count):
        """Record one collection over a matter. Action: document_write."""
        self._guard(actor, "ext_collection_record")
        matter = self._matter(actor, agency_id, matter_id)
        _non_empty(collection_ref, "collection_ref")
        _non_empty(source_label, "source_label")
        _count(reported_document_count, "reported_document_count")
        _count(reported_byte_count, "reported_byte_count")
        with self._lock:
            self._check_ref_unique(
                self._in_matter(self._collections, matter_id),
                "collection_ref", collection_ref, "matter")
            return self._create(
                self._collections, "col-",
                {"agency_id": agency_id, "matter_id": matter_id,
                 "collection_ref": collection_ref,
                 "source_label": source_label,
                 "reported_document_count": reported_document_count,
                 "reported_byte_count": reported_byte_count,
                 "content_collected_here": False,
                 "processing_performed_here": False},
                actor, "ext_collection_record")

    def link_collection_document(self, actor, agency_id, collection_id,
                                 document_id):
        """Link one core document reference to a collection.

        Action: document_write."""
        self._guard(actor, "ext_collection_link")
        self._agency(actor, agency_id)
        collection = self._get(self._collections, collection_id, "collection")
        if collection["agency_id"] != agency_id:
            raise NotFoundError(
                "collection not found in agency %s: %r"
                % (agency_id, collection_id))
        matter = self._matter(actor, agency_id, collection["matter_id"])
        self._document_in_matter(actor, matter)(document_id)
        with self._lock:
            for existing in self._collection_links.values():
                if (existing["collection_id"] == collection_id
                        and existing["document_id"] == document_id):
                    raise ValidationError(
                        "document %r is already linked to collection %s"
                        % (document_id, collection_id))
            return self._create(
                self._collection_links, "clk-",
                {"agency_id": agency_id, "collection_id": collection_id,
                 "document_id": document_id},
                actor, "ext_collection_link")

    def get_collection(self, actor, agency_id, collection_id):
        """Return one stored collection record. Action: agency_read."""
        self._agency(actor, agency_id)
        collection = self._get(self._collections, collection_id, "collection")
        if collection["agency_id"] != agency_id:
            raise NotFoundError(
                "collection not found in agency %s: %r"
                % (agency_id, collection_id))
        return copy.deepcopy(collection)

    def collection_view(self, actor, agency_id, collection_id):
        """A collection record plus counts derived at read: linked
        core documents and recorded processing runs. The stored
        record carries neither count. Action: agency_read."""
        view = self.get_collection(actor, agency_id, collection_id)
        view["linked_document_count"] = sum(
            1 for link in self._collection_links.values()
            if link["collection_id"] == collection_id)
        view["processing_run_count"] = sum(
            1 for run in self._processing_runs.values()
            if run["collection_id"] == collection_id)
        return view

    def list_collections(self, actor, agency_id, matter_id):
        """List collections in a matter. Action: agency_read."""
        self._matter(actor, agency_id, matter_id)
        return copy.deepcopy(self._sorted(
            self._in_matter(self._collections, matter_id)))

    def record_processing_run(self, actor, agency_id, collection_id, run_ref,
                              reported_processed_count, reported_error_count):
        """Record one processing run over a collection, counts as
        reported. Action: document_write."""
        self._guard(actor, "ext_processing_run_record")
        self._agency(actor, agency_id)
        collection = self._get(self._collections, collection_id, "collection")
        if collection["agency_id"] != agency_id:
            raise NotFoundError(
                "collection not found in agency %s: %r"
                % (agency_id, collection_id))
        _non_empty(run_ref, "run_ref")
        _count(reported_processed_count, "reported_processed_count")
        _count(reported_error_count, "reported_error_count")
        with self._lock:
            self._check_ref_unique(
                [r for r in self._processing_runs.values()
                 if r["collection_id"] == collection_id],
                "run_ref", run_ref, "collection")
            return self._create(
                self._processing_runs, "prc-",
                {"agency_id": agency_id, "collection_id": collection_id,
                 "run_ref": run_ref,
                 "reported_processed_count": reported_processed_count,
                 "reported_error_count": reported_error_count,
                 "processing_performed_here": False},
                actor, "ext_processing_run_record")

    def list_processing_runs(self, actor, agency_id, collection_id):
        """List processing runs over a collection. Action: agency_read."""
        self.get_collection(actor, agency_id, collection_id)
        return copy.deepcopy(self._sorted(
            [r for r in self._processing_runs.values()
             if r["collection_id"] == collection_id]))

    # -- Legal hold & preservation (idx 564, built) --------------------
    # Records form: a hold is a registry record over a matter, with
    # append-only reported state records and coverage records over
    # core document references. The hold's current state is DERIVED
    # at read from the latest recorded state label by the single
    # seam ``_current_hold_label`` and is never stored. Preservation
    # itself is performed by the custodian's systems:
    # ``preserved_here`` is False on every hold record.

    @staticmethod
    def _current_hold_label(states):
        """The current state of a hold: the LATEST recorded state
        label, or ``recorded`` when no state has been recorded yet.

        MUTATION DRILL NOTE: this seam is the batch unit's fresh
        negative control target -- see tests/README.md."""
        if not states:
            return "recorded"
        return states[-1]["state_label"]

    def _hold_states_for(self, hold_id):
        return self._sorted(
            [s for s in self._hold_states.values()
             if s["hold_id"] == hold_id])

    def _hold_is_active(self, hold_id):
        return (self._current_hold_label(self._hold_states_for(hold_id))
                in HOLD_ACTIVE_STATES)

    def create_hold(self, actor, agency_id, matter_id, hold_ref,
                    custodian_ref):
        """Create one legal hold record. Action: document_write."""
        self._guard(actor, "ext_hold_create")
        self._matter(actor, agency_id, matter_id)
        _non_empty(hold_ref, "hold_ref")
        _non_empty(custodian_ref, "custodian_ref")
        with self._lock:
            self._check_ref_unique(
                self._in_matter(self._holds, matter_id),
                "hold_ref", hold_ref, "matter")
            return self._create(
                self._holds, "hld-",
                {"agency_id": agency_id, "matter_id": matter_id,
                 "hold_ref": hold_ref, "custodian_ref": custodian_ref,
                 "preserved_here": False},
                actor, "ext_hold_create")

    def get_hold(self, actor, agency_id, hold_id):
        """Return one stored hold record (no derived state key).
        Action: agency_read."""
        self._agency(actor, agency_id)
        hold = self._get(self._holds, hold_id, "legal hold")
        if hold["agency_id"] != agency_id:
            raise NotFoundError(
                "legal hold not found in agency %s: %r" % (agency_id, hold_id))
        return copy.deepcopy(hold)

    def record_hold_state(self, actor, agency_id, hold_id, state_label):
        """Append one reported state record to a hold.
        Action: document_write."""
        self._guard(actor, "ext_hold_state")
        hold = self.get_hold(actor, agency_id, hold_id)
        if state_label not in HOLD_STATES:
            raise ValidationError(
                "state_label must be one of %s" % (", ".join(HOLD_STATES),))
        with self._lock:
            return self._create(
                self._hold_states, "hst-",
                {"agency_id": agency_id, "hold_id": hold_id,
                 "state_label": state_label, "preserved_here": False},
                actor, "ext_hold_state")

    def add_hold_coverage(self, actor, agency_id, hold_id, document_id):
        """Record that a hold covers one core document reference.
        Action: document_write."""
        self._guard(actor, "ext_hold_coverage")
        hold = self.get_hold(actor, agency_id, hold_id)
        matter = self._matter(actor, agency_id, hold["matter_id"])
        self._document_in_matter(actor, matter)(document_id)
        with self._lock:
            for existing in self._hold_coverages.values():
                if (existing["hold_id"] == hold_id
                        and existing["document_id"] == document_id):
                    raise ValidationError(
                        "document %r is already covered by hold %s"
                        % (document_id, hold_id))
            return self._create(
                self._hold_coverages, "hcv-",
                {"agency_id": agency_id, "hold_id": hold_id,
                 "document_id": document_id, "preserved_here": False},
                actor, "ext_hold_coverage")

    def hold_view(self, actor, agency_id, hold_id):
        """A hold record plus its derived state: current state
        (latest recorded label, via the seam), state record count,
        covered document references, and whether the hold is
        active. Nothing derived is stored. Action: agency_read."""
        view = self.get_hold(actor, agency_id, hold_id)
        states = self._hold_states_for(hold_id)
        coverages = self._sorted(
            [c for c in self._hold_coverages.values()
             if c["hold_id"] == hold_id])
        current = self._current_hold_label(states)
        view["current_state"] = current
        view["state_record_count"] = len(states)
        view["covered_document_ids"] = [c["document_id"] for c in coverages]
        view["covered_document_count"] = len(coverages)
        view["is_active"] = current in HOLD_ACTIVE_STATES
        return view

    def list_holds(self, actor, agency_id, matter_id):
        """List hold records in a matter. Action: agency_read."""
        self._matter(actor, agency_id, matter_id)
        return copy.deepcopy(self._sorted(
            self._in_matter(self._holds, matter_id)))

    # -- eDiscovery document review (idx 562, built) -------------------
    # Records form: an assignment pairs a core document reference
    # with an opaque reviewer reference; a decision records the
    # reviewer's determination label verbatim. The reviewed content
    # is never present -- ``content_reviewed_here`` is False on
    # every record -- and recording a decision changes no core
    # document record (pinned by test).

    def assign_review(self, actor, agency_id, matter_id, document_id,
                      reviewer_ref):
        """Assign one document reference to a reviewer reference.
        Action: document_write."""
        self._guard(actor, "ext_review_assign")
        matter = self._matter(actor, agency_id, matter_id)
        self._document_in_matter(actor, matter)(document_id)
        _non_empty(reviewer_ref, "reviewer_ref")
        with self._lock:
            return self._create(
                self._review_assignments, "rva-",
                {"agency_id": agency_id, "matter_id": matter_id,
                 "document_id": document_id, "reviewer_ref": reviewer_ref,
                 "content_reviewed_here": False},
                actor, "ext_review_assign")

    def record_review_decision(self, actor, agency_id, assignment_id,
                               decision_label):
        """Record one reviewer decision, label verbatim.
        Action: document_write."""
        self._guard(actor, "ext_review_decision")
        self._agency(actor, agency_id)
        assignment = self._get(
            self._review_assignments, assignment_id, "review assignment")
        if assignment["agency_id"] != agency_id:
            raise NotFoundError(
                "review assignment not found in agency %s: %r"
                % (agency_id, assignment_id))
        if decision_label not in REVIEW_DECISION_LABELS:
            raise ValidationError(
                "decision_label must be one of %s"
                % (", ".join(REVIEW_DECISION_LABELS),))
        with self._lock:
            return self._create(
                self._review_decisions, "rvd-",
                {"agency_id": agency_id, "assignment_id": assignment_id,
                 "decision_label": decision_label,
                 "content_reviewed_here": False},
                actor, "ext_review_decision")

    def list_review_assignments(self, actor, agency_id, matter_id):
        """List review assignments in a matter. Action: agency_read."""
        self._matter(actor, agency_id, matter_id)
        return copy.deepcopy(self._sorted(
            self._in_matter(self._review_assignments, matter_id)))

    def list_review_decisions(self, actor, agency_id, assignment_id):
        """List decisions recorded against one assignment.
        Action: agency_read."""
        self._agency(actor, agency_id)
        assignment = self._get(
            self._review_assignments, assignment_id, "review assignment")
        if assignment["agency_id"] != agency_id:
            raise NotFoundError(
                "review assignment not found in agency %s: %r"
                % (agency_id, assignment_id))
        return copy.deepcopy(self._sorted(
            [d for d in self._review_decisions.values()
             if d["assignment_id"] == assignment_id]))

    def assignment_view(self, actor, agency_id, assignment_id):
        """An assignment record plus derived decision state: the
        decision count and the latest recorded decision label.
        Action: agency_read."""
        self._agency(actor, agency_id)
        assignment = self._get(
            self._review_assignments, assignment_id, "review assignment")
        if assignment["agency_id"] != agency_id:
            raise NotFoundError(
                "review assignment not found in agency %s: %r"
                % (agency_id, assignment_id))
        view = copy.deepcopy(assignment)
        decisions = self._sorted(
            [d for d in self._review_decisions.values()
             if d["assignment_id"] == assignment_id])
        view["decision_count"] = len(decisions)
        view["latest_decision_label"] = (
            decisions[-1]["decision_label"] if decisions else None)
        return view

    # -- eDiscovery production, disposition & archiving (idx 563, built)
    # Records form: a production is a registry record over core
    # document references with counts stored as reported; nothing
    # is produced here. A disposition is a DECISION record: its
    # eligibility is derived at read from recorded states -- a
    # document covered by an ACTIVE legal hold (per the hold seam)
    # is not eligible, and the decision write enforces that --
    # while the disposition itself is executed by the embedding
    # organization's records schedule, never here
    # (``executed_here`` is False; PLATFORM-LAYER.md decision 4).

    def record_production(self, actor, agency_id, matter_id, production_ref,
                          reported_document_count):
        """Record one production over a matter.
        Action: document_write."""
        self._guard(actor, "ext_production_record")
        self._matter(actor, agency_id, matter_id)
        _non_empty(production_ref, "production_ref")
        _count(reported_document_count, "reported_document_count")
        with self._lock:
            self._check_ref_unique(
                self._in_matter(self._productions, matter_id),
                "production_ref", production_ref, "matter")
            return self._create(
                self._productions, "prd-",
                {"agency_id": agency_id, "matter_id": matter_id,
                 "production_ref": production_ref,
                 "reported_document_count": reported_document_count,
                 "production_executed_here": False},
                actor, "ext_production_record")

    def link_production_document(self, actor, agency_id, production_id,
                                 document_id):
        """Link one core document reference to a production.
        Action: document_write."""
        self._guard(actor, "ext_production_link")
        self._agency(actor, agency_id)
        production = self._get(self._productions, production_id, "production")
        if production["agency_id"] != agency_id:
            raise NotFoundError(
                "production not found in agency %s: %r"
                % (agency_id, production_id))
        matter = self._matter(actor, agency_id, production["matter_id"])
        self._document_in_matter(actor, matter)(document_id)
        with self._lock:
            for existing in self._production_links.values():
                if (existing["production_id"] == production_id
                        and existing["document_id"] == document_id):
                    raise ValidationError(
                        "document %r is already linked to production %s"
                        % (document_id, production_id))
            return self._create(
                self._production_links, "plk-",
                {"agency_id": agency_id, "production_id": production_id,
                 "document_id": document_id},
                actor, "ext_production_link")

    def production_view(self, actor, agency_id, production_id):
        """A production record plus its derived linked-document
        count. Action: agency_read."""
        self._agency(actor, agency_id)
        production = self._get(self._productions, production_id, "production")
        if production["agency_id"] != agency_id:
            raise NotFoundError(
                "production not found in agency %s: %r"
                % (agency_id, production_id))
        view = copy.deepcopy(production)
        view["linked_document_count"] = sum(
            1 for link in self._production_links.values()
            if link["production_id"] == production_id)
        return view

    def _active_hold_ids_for(self, matter_id, document_id):
        """Ids of holds in the matter that cover the document and
        whose derived current state is active (via the hold seam)."""
        result = []
        for hold in self._sorted(self._in_matter(self._holds, matter_id)):
            covered = any(
                c["hold_id"] == hold["id"] and c["document_id"] == document_id
                for c in self._hold_coverages.values())
            if covered and self._hold_is_active(hold["id"]):
                result.append(hold["id"])
        return result

    def disposition_view(self, actor, agency_id, matter_id, document_id):
        """Disposition eligibility for one document, derived at
        read from recorded states: the active holds covering it,
        the disposition decisions already recorded, and whether it
        is eligible. Nothing is executed. Action: agency_read."""
        matter = self._matter(actor, agency_id, matter_id)
        self._document_in_matter(actor, matter)(document_id)
        active = self._active_hold_ids_for(matter_id, document_id)
        decisions = [d for d in self._disposition_decisions.values()
                     if d["matter_id"] == matter_id
                     and d["document_id"] == document_id]
        return {
            "agency_id": agency_id,
            "matter_id": matter_id,
            "document_id": document_id,
            "under_active_hold": bool(active),
            "active_hold_ids": active,
            "disposition_decision_count": len(decisions),
            "eligible_for_disposition": not active,
            "executed_here": False,
            "method": "derived_from_recorded_states",
        }

    def record_disposition_decision(self, actor, agency_id, matter_id,
                                    document_id, decision_label):
        """Record one disposition decision. Refused while the
        document is covered by an active legal hold.
        Action: document_write."""
        self._guard(actor, "ext_disposition_decision")
        matter = self._matter(actor, agency_id, matter_id)
        self._document_in_matter(actor, matter)(document_id)
        if decision_label not in DISPOSITION_LABELS:
            raise ValidationError(
                "decision_label must be one of %s"
                % (", ".join(DISPOSITION_LABELS),))
        with self._lock:
            active = self._active_hold_ids_for(matter_id, document_id)
            if active:
                raise ValidationError(
                    "document %s is covered by active legal hold(s) %s; "
                    "a disposition decision cannot be recorded"
                    % (document_id, ", ".join(active)))
            return self._create(
                self._disposition_decisions, "dsp-",
                {"agency_id": agency_id, "matter_id": matter_id,
                 "document_id": document_id,
                 "decision_label": decision_label, "executed_here": False},
                actor, "ext_disposition_decision")

    def list_disposition_decisions(self, actor, agency_id, matter_id):
        """List disposition decisions in a matter.
        Action: agency_read."""
        self._matter(actor, agency_id, matter_id)
        return copy.deepcopy(self._sorted(
            self._in_matter(self._disposition_decisions, matter_id)))

    # -- AI document analysis for discovery (idx 565, built) -----------
    # Records form: an analysis request names a core document
    # reference and an analysis kind; a result record holds the
    # reported output as an OPAQUE RESULT REFERENCE plus an
    # optional verbatim reported label. No summary, classification,
    # or redaction text exists in any shape -- those fields do not
    # exist -- and no inference runs here (``inference_here`` is
    # False on every record). "Analytics" (below) is a
    # deterministic counts derivation over held records.

    def request_analysis(self, actor, agency_id, matter_id, document_id,
                         analysis_kind, request_ref):
        """Record one analysis request. Action: document_write."""
        self._guard(actor, "ext_analysis_request")
        matter = self._matter(actor, agency_id, matter_id)
        self._document_in_matter(actor, matter)(document_id)
        if analysis_kind not in ANALYSIS_KINDS:
            raise ValidationError(
                "analysis_kind must be one of %s"
                % (", ".join(ANALYSIS_KINDS),))
        _non_empty(request_ref, "request_ref")
        with self._lock:
            self._check_ref_unique(
                self._in_matter(self._analysis_requests, matter_id),
                "request_ref", request_ref, "matter")
            return self._create(
                self._analysis_requests, "anr-",
                {"agency_id": agency_id, "matter_id": matter_id,
                 "document_id": document_id, "analysis_kind": analysis_kind,
                 "request_ref": request_ref, "inference_here": False},
                actor, "ext_analysis_request")

    def record_analysis_result(self, actor, agency_id, request_id, result_ref,
                               reported_label=None):
        """Record one reported analysis output as an opaque result
        reference. Action: document_write."""
        self._guard(actor, "ext_analysis_result")
        self._agency(actor, agency_id)
        request = self._get(
            self._analysis_requests, request_id, "analysis request")
        if request["agency_id"] != agency_id:
            raise NotFoundError(
                "analysis request not found in agency %s: %r"
                % (agency_id, request_id))
        _non_empty(result_ref, "result_ref")
        if reported_label is not None:
            _non_empty(reported_label, "reported_label")
        with self._lock:
            return self._create(
                self._analysis_results, "anl-",
                {"agency_id": agency_id, "request_id": request_id,
                 "result_ref": result_ref, "reported_label": reported_label,
                 "inference_here": False},
                actor, "ext_analysis_result")

    def analysis_request_view(self, actor, agency_id, request_id):
        """An analysis request record plus its derived result
        count. Action: agency_read."""
        self._agency(actor, agency_id)
        request = self._get(
            self._analysis_requests, request_id, "analysis request")
        if request["agency_id"] != agency_id:
            raise NotFoundError(
                "analysis request not found in agency %s: %r"
                % (agency_id, request_id))
        view = copy.deepcopy(request)
        view["result_count"] = sum(
            1 for r in self._analysis_results.values()
            if r["request_id"] == request_id)
        return view

    def discovery_analytics(self, actor, agency_id, matter_id):
        """Deterministic counts over the matter's held records:
        collections, links, runs, review, analysis, extraction,
        productions, holds (active derived via the hold seam), and
        disposition decisions. Method ``deterministic_counts`` --
        counts only; nothing is inferred or scored.
        Action: agency_read."""
        self._matter(actor, agency_id, matter_id)
        collections = self._in_matter(self._collections, matter_id)
        collection_ids = {c["id"] for c in collections}
        # Review decisions carry no matter_id of their own; they
        # belong to the matter through their assignment.
        decisions = [d for d in self._review_decisions.values()
                     if self._review_assignments[d["assignment_id"]]
                     ["matter_id"] == matter_id]
        by_label = {}
        for decision in decisions:
            by_label[decision["decision_label"]] = (
                by_label.get(decision["decision_label"], 0) + 1)
        requests = self._in_matter(self._analysis_requests, matter_id)
        by_kind = {}
        for request in requests:
            by_kind[request["analysis_kind"]] = (
                by_kind.get(request["analysis_kind"], 0) + 1)
        holds = self._in_matter(self._holds, matter_id)
        return {
            "agency_id": agency_id,
            "matter_id": matter_id,
            "collections": len(collections),
            "collection_documents": sum(
                1 for link in self._collection_links.values()
                if link["collection_id"] in collection_ids),
            "processing_runs": sum(
                1 for run in self._processing_runs.values()
                if run["collection_id"] in collection_ids),
            "review_assignments": len(
                self._in_matter(self._review_assignments, matter_id)),
            "review_decisions": len(decisions),
            "review_decisions_by_label": by_label,
            "analysis_requests": len(requests),
            "analysis_requests_by_kind": by_kind,
            "extraction_jobs": len(
                self._in_matter(self._extraction_jobs, matter_id)),
            "productions": len(self._in_matter(self._productions, matter_id)),
            "holds_total": len(holds),
            "holds_active": sum(
                1 for hold in holds if self._hold_is_active(hold["id"])),
            "disposition_decisions": len(
                self._in_matter(self._disposition_decisions, matter_id)),
            "method": "deterministic_counts",
            "inference_here": False,
        }

    # -- OCR & document extraction (idx 566, built) --------------------
    # Records form: an extraction job names a core document
    # reference and holds counts stored as reported plus an opaque
    # result reference. No extracted text exists in any shape --
    # the field does not exist -- and nothing is extracted here
    # (``extracted_here`` is False on every record).

    def record_extraction_job(self, actor, agency_id, matter_id, document_id,
                              job_ref, reported_page_count,
                              reported_field_count, result_ref):
        """Record one OCR/extraction job. Action: document_write."""
        self._guard(actor, "ext_extraction_job")
        matter = self._matter(actor, agency_id, matter_id)
        self._document_in_matter(actor, matter)(document_id)
        _non_empty(job_ref, "job_ref")
        _count(reported_page_count, "reported_page_count")
        _count(reported_field_count, "reported_field_count")
        _non_empty(result_ref, "result_ref")
        with self._lock:
            self._check_ref_unique(
                self._in_matter(self._extraction_jobs, matter_id),
                "job_ref", job_ref, "matter")
            return self._create(
                self._extraction_jobs, "ocr-",
                {"agency_id": agency_id, "matter_id": matter_id,
                 "document_id": document_id, "job_ref": job_ref,
                 "reported_page_count": reported_page_count,
                 "reported_field_count": reported_field_count,
                 "result_ref": result_ref, "extracted_here": False},
                actor, "ext_extraction_job")

    def list_extraction_jobs(self, actor, agency_id, matter_id):
        """List extraction jobs in a matter. Action: agency_read."""
        self._matter(actor, agency_id, matter_id)
        return copy.deepcopy(self._sorted(
            self._in_matter(self._extraction_jobs, matter_id)))

    # -- FOIA & disclosure release (idx 567, built) --------------------
    # Records form: a FOIA case is a registry record in a core
    # workspace; the request itself and the requester are opaque
    # references -- no request text exists in any shape. States are
    # append-only reported labels whose current value derives at
    # read; exemption determinations are recorded verbatim as
    # labels; a release is a record with counts as reported.
    # Nothing is released here (``released_here`` is False).

    @staticmethod
    def _latest_state_label(states):
        """The latest recorded state label, or ``recorded`` when
        no state has been recorded yet."""
        if not states:
            return "recorded"
        return states[-1]["state_label"]

    def create_foia_case(self, actor, agency_id, workspace_id, case_ref,
                         request_ref, requester_ref):
        """Create one FOIA case record. Action: document_write."""
        self._guard(actor, "ext_foia_case")
        self._agency(actor, agency_id)
        self.store.get_workspace(agency_id, workspace_id, actor)
        _non_empty(case_ref, "case_ref")
        _non_empty(request_ref, "request_ref")
        _non_empty(requester_ref, "requester_ref")
        with self._lock:
            self._check_ref_unique(
                [c for c in self._foia_cases.values()
                 if c["workspace_id"] == workspace_id],
                "case_ref", case_ref, "workspace")
            return self._create(
                self._foia_cases, "foi-",
                {"agency_id": agency_id, "workspace_id": workspace_id,
                 "case_ref": case_ref, "request_ref": request_ref,
                 "requester_ref": requester_ref, "released_here": False},
                actor, "ext_foia_case")

    def get_foia_case(self, actor, agency_id, case_id):
        """Return one stored FOIA case record (no derived state
        key). Action: agency_read."""
        self._agency(actor, agency_id)
        case = self._get(self._foia_cases, case_id, "FOIA case")
        if case["agency_id"] != agency_id:
            raise NotFoundError(
                "FOIA case not found in agency %s: %r" % (agency_id, case_id))
        return copy.deepcopy(case)

    def record_foia_state(self, actor, agency_id, case_id, state_label):
        """Append one reported state record to a FOIA case.
        Action: document_write."""
        self._guard(actor, "ext_foia_state")
        self.get_foia_case(actor, agency_id, case_id)
        if state_label not in FOIA_STATES:
            raise ValidationError(
                "state_label must be one of %s" % (", ".join(FOIA_STATES),))
        with self._lock:
            return self._create(
                self._foia_states, "fos-",
                {"agency_id": agency_id, "case_id": case_id,
                 "state_label": state_label},
                actor, "ext_foia_state")

    def record_exemption_determination(self, actor, agency_id, case_id,
                                       exemption_label, document_id=None):
        """Record one exemption determination, label verbatim.
        Action: document_write."""
        self._guard(actor, "ext_foia_determination")
        case = self.get_foia_case(actor, agency_id, case_id)
        _non_empty(exemption_label, "exemption_label")
        if document_id is not None:
            document = self.store.get_document(agency_id, document_id, actor)
            if document["workspace_id"] != case["workspace_id"]:
                raise NotFoundError(
                    "document not found in FOIA case workspace %s: %r"
                    % (case["workspace_id"], document_id))
        with self._lock:
            return self._create(
                self._foia_determinations, "fxd-",
                {"agency_id": agency_id, "case_id": case_id,
                 "document_id": document_id,
                 "exemption_label": exemption_label,
                 "released_here": False},
                actor, "ext_foia_determination")

    def record_foia_release(self, actor, agency_id, case_id, release_ref,
                            reported_document_count):
        """Record one disclosure release, count as reported.
        Action: document_write."""
        self._guard(actor, "ext_foia_release")
        self.get_foia_case(actor, agency_id, case_id)
        _non_empty(release_ref, "release_ref")
        _count(reported_document_count, "reported_document_count")
        with self._lock:
            self._check_ref_unique(
                [r for r in self._foia_releases.values()
                 if r["case_id"] == case_id],
                "release_ref", release_ref, "FOIA case")
            return self._create(
                self._foia_releases, "frl-",
                {"agency_id": agency_id, "case_id": case_id,
                 "release_ref": release_ref,
                 "reported_document_count": reported_document_count,
                 "released_here": False},
                actor, "ext_foia_release")

    def foia_case_view(self, actor, agency_id, case_id):
        """A FOIA case record plus derived state: current state
        (latest recorded label), state record count, determination
        count, and release count. Nothing derived is stored.
        Action: agency_read."""
        view = self.get_foia_case(actor, agency_id, case_id)
        states = self._sorted(
            [s for s in self._foia_states.values()
             if s["case_id"] == case_id])
        view["current_state"] = self._latest_state_label(states)
        view["state_record_count"] = len(states)
        view["determination_count"] = sum(
            1 for d in self._foia_determinations.values()
            if d["case_id"] == case_id)
        view["release_count"] = sum(
            1 for r in self._foia_releases.values()
            if r["case_id"] == case_id)
        return view

    def list_foia_cases(self, actor, agency_id, workspace_id=None):
        """List FOIA case records in an agency. Action: agency_read."""
        self._agency(actor, agency_id)
        cases = self._in_agency(self._foia_cases, agency_id)
        if workspace_id is not None:
            cases = [c for c in cases if c["workspace_id"] == workspace_id]
        return copy.deepcopy(self._sorted(cases))

    # -- Contract lifecycle management (idx 569, built) ----------------
    # Records form: an agreement is a registry record over an
    # opaque counterparty reference, with an optional value held as
    # integer cents (data). Lifecycle states are append-only
    # reported labels whose current value derives at read and is
    # never stored. No agreement is executed here
    # (``executed_here`` is False on every agreement record).

    def create_agreement(self, actor, agency_id, workspace_id, agreement_ref,
                         counterparty_ref, value_cents=None):
        """Create one agreement record. Action: document_write."""
        self._guard(actor, "ext_agreement_create")
        self._agency(actor, agency_id)
        self.store.get_workspace(agency_id, workspace_id, actor)
        _non_empty(agreement_ref, "agreement_ref")
        _non_empty(counterparty_ref, "counterparty_ref")
        if value_cents is not None:
            _cents(value_cents, "value_cents")
        with self._lock:
            self._check_ref_unique(
                [a for a in self._agreements.values()
                 if a["workspace_id"] == workspace_id],
                "agreement_ref", agreement_ref, "workspace")
            return self._create(
                self._agreements, "agr-",
                {"agency_id": agency_id, "workspace_id": workspace_id,
                 "agreement_ref": agreement_ref,
                 "counterparty_ref": counterparty_ref,
                 "value_cents": value_cents, "executed_here": False},
                actor, "ext_agreement_create")

    def get_agreement(self, actor, agency_id, agreement_id):
        """Return one stored agreement record (no derived state
        key). Action: agency_read."""
        self._agency(actor, agency_id)
        agreement = self._get(self._agreements, agreement_id, "agreement")
        if agreement["agency_id"] != agency_id:
            raise NotFoundError(
                "agreement not found in agency %s: %r"
                % (agency_id, agreement_id))
        return copy.deepcopy(agreement)

    def record_agreement_state(self, actor, agency_id, agreement_id,
                               state_label):
        """Append one reported lifecycle state record to an
        agreement. Action: document_write."""
        self._guard(actor, "ext_agreement_state")
        self.get_agreement(actor, agency_id, agreement_id)
        if state_label not in AGREEMENT_STATES:
            raise ValidationError(
                "state_label must be one of %s"
                % (", ".join(AGREEMENT_STATES),))
        with self._lock:
            return self._create(
                self._agreement_states, "ags-",
                {"agency_id": agency_id, "agreement_id": agreement_id,
                 "state_label": state_label},
                actor, "ext_agreement_state")

    def agreement_view(self, actor, agency_id, agreement_id):
        """An agreement record plus its derived lifecycle state:
        current state (latest recorded label) and state record
        count. Nothing derived is stored. Action: agency_read."""
        view = self.get_agreement(actor, agency_id, agreement_id)
        states = self._sorted(
            [s for s in self._agreement_states.values()
             if s["agreement_id"] == agreement_id])
        view["current_state"] = self._latest_state_label(states)
        view["state_record_count"] = len(states)
        return view

    def list_agreements(self, actor, agency_id, workspace_id=None):
        """List agreement records in an agency. Action: agency_read."""
        self._agency(actor, agency_id)
        agreements = self._in_agency(self._agreements, agency_id)
        if workspace_id is not None:
            agreements = [a for a in agreements
                          if a["workspace_id"] == workspace_id]
        return copy.deepcopy(self._sorted(agreements))

    # -- Electronic signature (idx 568, reference) ---------------------
    # Labeled reference implementation: an envelope record names an
    # optional core agreement or document reference; a ceremony
    # record holds a reported ceremony label per opaque signer
    # reference. Every record carries ``reference_stub: True`` and
    # the envelopes carry state ``recorded_reference_only``. No
    # shape has a field that could hold a signature value -- the
    # field does not exist -- and nothing is signed here
    # (``signed_here`` is False on every record).

    def record_envelope(self, actor, agency_id, envelope_ref,
                        agreement_id=None, document_id=None):
        """Record one reference envelope. Action: document_write."""
        self._guard(actor, "ext_envelope_record")
        self._agency(actor, agency_id)
        _non_empty(envelope_ref, "envelope_ref")
        if agreement_id is not None:
            self.get_agreement(actor, agency_id, agreement_id)
        if document_id is not None:
            self.store.get_document(agency_id, document_id, actor)
        with self._lock:
            self._check_ref_unique(
                self._in_agency(self._envelopes, agency_id),
                "envelope_ref", envelope_ref, "agency")
            return self._create(
                self._envelopes, "env-",
                {"agency_id": agency_id, "agreement_id": agreement_id,
                 "document_id": document_id, "envelope_ref": envelope_ref,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "signed_here": False},
                actor, "ext_envelope_record")

    def record_ceremony_event(self, actor, agency_id, envelope_id,
                              signer_ref, ceremony_label):
        """Record one reported ceremony event on an envelope.
        Action: document_write."""
        self._guard(actor, "ext_ceremony_record")
        self._agency(actor, agency_id)
        envelope = self._get(self._envelopes, envelope_id, "envelope")
        if envelope["agency_id"] != agency_id:
            raise NotFoundError(
                "envelope not found in agency %s: %r"
                % (agency_id, envelope_id))
        _non_empty(signer_ref, "signer_ref")
        if ceremony_label not in CEREMONY_LABELS:
            raise ValidationError(
                "ceremony_label must be one of %s"
                % (", ".join(CEREMONY_LABELS),))
        with self._lock:
            return self._create(
                self._ceremonies, "sgn-",
                {"agency_id": agency_id, "envelope_id": envelope_id,
                 "signer_ref": signer_ref, "ceremony_label": ceremony_label,
                 "reference_stub": True, "signed_here": False},
                actor, "ext_ceremony_record")

    def list_envelopes(self, actor, agency_id):
        """List reference envelopes in an agency. Action: agency_read."""
        self._agency(actor, agency_id)
        return copy.deepcopy(self._sorted(
            self._in_agency(self._envelopes, agency_id)))

    def list_ceremony_events(self, actor, agency_id, envelope_id):
        """List ceremony events on one envelope. Action: agency_read."""
        self._agency(actor, agency_id)
        envelope = self._get(self._envelopes, envelope_id, "envelope")
        if envelope["agency_id"] != agency_id:
            raise NotFoundError(
                "envelope not found in agency %s: %r"
                % (agency_id, envelope_id))
        return copy.deepcopy(self._sorted(
            [c for c in self._ceremonies.values()
             if c["envelope_id"] == envelope_id]))

    # -- Agreement workflow automation (idx 570, reference) ------------
    # Labeled reference implementation: a workflow definition is
    # held as DATA (an ordered list of step labels). Per the house
    # doctrine the registry never executes: registering a
    # definition changes no agreement record (pinned by test), and
    # ``executed_here`` is False on every record.

    def register_workflow_definition(self, actor, agency_id, definition_ref,
                                     steps):
        """Register one workflow definition as data.
        Action: document_write."""
        self._guard(actor, "ext_workflow_definition")
        self._agency(actor, agency_id)
        _non_empty(definition_ref, "definition_ref")
        steps = _string_list(steps, "steps")
        with self._lock:
            self._check_ref_unique(
                self._in_agency(self._workflow_definitions, agency_id),
                "definition_ref", definition_ref, "agency")
            return self._create(
                self._workflow_definitions, "wfd-",
                {"agency_id": agency_id, "definition_ref": definition_ref,
                 "steps": steps, "reference_stub": True,
                 "state": _REFERENCE_STATE, "executed_here": False},
                actor, "ext_workflow_definition")

    def list_workflow_definitions(self, actor, agency_id):
        """List workflow definitions in an agency.
        Action: agency_read."""
        self._agency(actor, agency_id)
        return copy.deepcopy(self._sorted(
            self._in_agency(self._workflow_definitions, agency_id)))
