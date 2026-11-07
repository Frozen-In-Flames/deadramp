"""Final GAPS batch extensions for Legal & Policy, untiered set.

Clean-room, standard-library-only extensions for the 3 open
entries of the GAPS.md section "Untiered Set 12 -- Legal & Policy
(3 forks, tier null)" (inventory idx 862-864; see ``BATCH.md`` in
the group directory for the per-entry disposition). This module is
a wrapper around :class:`LegalPolStore`; every core module is
untouched and byte-identical to the shipped build.

**Tier discipline binds here as everywhere in this set:** the
extension asserts no FedRAMP baseline, no CMMC tier, and no
equivalence. No record shape in this module has a tier, baseline,
or impact-level field -- those fields **do not exist** -- and
nothing in the extension computes a compliance posture. Control
areas documented by the set's forks stay exactly what the union
spec recorded: none, and nothing here fills one in.

**The founding privacy rule binds absolutely, here as in the
core:** documents exist in this substrate ONLY as metadata +
SHA-256 records in the core document registry. No entity shape in
this module has a field that can hold document content, research
text, a draft, a summary, or query text -- those fields **do not
exist**. A research query enters only as its SHA-256 digest,
mirroring the core's saved-search design (the request method has
no parameter that can accept query text). Methods accept only
their named parameters, so a caller cannot smuggle a forbidden
field into a record (pinned by tests: an unexpected keyword raises
``TypeError``). Requesters and sources are opaque caller-supplied
references. Nothing is scored.

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form -- records plus deterministic derivations over
the group's OWN records (core records and extension records):

- Legal research, evidence mapping & citation validation (idx
  862) ships as the drafted labeled reference implementation:
  research is performed by the fork's engine on the fork's own
  corpus, never here. What lands here is the records remainder --
  request records naming the query by digest only, evidence-map
  records holding a fact's source tracing as opaque references
  with page/line locators recorded verbatim, citation-validation
  outcome records with reported labels verbatim, and draft links
  to core document records. Every record carries
  ``reference_stub: True`` and ``researched_here`` /
  ``validated_here`` are False.
- The FOIA case management system of record (idx 863) is built as
  records: one case record per request holding the full lifecycle
  in this substrate -- intake (request and requester as opaque
  references, receipt date and statutory period recorded as
  data), append-only reported state records whose current state
  derives at read, exemption application records with labels
  verbatim, and release records with counts as reported. The
  statutory due date is **derived at read** from the recorded
  receipt date and period, never stored; overdue is likewise
  derived at read against an explicit ``as_of``. The portals the
  fork's prose names land as derived read views (requester view,
  agency view) over the same records -- operated portal surfaces
  are not built, and nothing is released here.
- The discovery platform app builder / extensibility surface
  (idx 864) is built as an application-definition registry:
  customer-built application definitions held as DATA (component
  labels as data), bound to core workspaces, with append-only
  reported state records whose current state derives at read.
  Per the house doctrine the registry never executes: the app
  runtime and the builder interface are not built and not
  claimed (``executed_here`` / ``runtime_here`` are False on
  every record).

Doctrines carried from the core: derived-never-stored for every
computed value (current FOIA/app state, due date, overdue,
tallies, counts); validation before mutation, so a failed
operation consumes no id and changes nothing; append-only audit
on the core store's log with ``ext_``-prefixed actions for every
successful extension mutation, and denied write attempts recorded
with a ``:denied`` suffix; RBAC via :mod:`legalpol.access` --
extension writes map to the core ``document_write`` action (the
extension surface is records over the document/case substrate)
and reads resolve the agency through the core store, which
enforces ``agency_read`` and the agency membership boundary on
every operation.
"""

import copy
import threading
from datetime import date, datetime, timedelta, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

FOIA_CASE_STATES = (
    "reported_received", "reported_searching", "reported_reviewing",
    "reported_consultation", "reported_partially_released",
    "reported_released", "reported_denied", "reported_closed",
)
FOIA_TERMINAL_STATES = (
    "reported_released", "reported_denied", "reported_closed",
)
APP_STATES = (
    "reported_draft", "reported_enabled", "reported_disabled",
    "reported_retired",
)

_REFERENCE_STATE = "recorded_reference_only"

_SHA256_HEX = frozenset("0123456789abcdef")


def _utc_today():
    return datetime.now(timezone.utc).date()


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


def _positive_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError("%s must be a positive integer" % (what,))
    return value


def _sha256(value, what):
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in _SHA256_HEX for ch in value)
    ):
        raise ValidationError(
            "%s must be exactly 64 lowercase hex characters" % (what,))
    return value


def _parse_date(value, what):
    """Parse a strict ISO calendar date (YYYY-MM-DD)."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError(
                "%s must be an ISO date (YYYY-MM-DD): %r" % (what, value))
    raise ValidationError("%s must be an ISO date string" % (what,))


def _string_list(value, what):
    if not isinstance(value, (list, tuple)):
        raise ValidationError("%s must be a list of strings" % (what,))
    items = list(value)
    if not items:
        raise ValidationError("%s must be a non-empty list" % (what,))
    for item in items:
        _non_empty(item, what)
    if len(set(items)) != len(items):
        raise ValidationError("%s must not contain duplicates" % (what,))
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
        self._research_requests = {}
        self._evidence_maps = {}
        self._citation_outcomes = {}
        self._research_draft_links = {}
        self._foia_cases = {}
        self._foia_states = {}
        self._foia_exemptions = {}
        self._foia_releases = {}
        self._app_definitions = {}
        self._app_states = {}
        self._app_bindings = {}
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

    def _create(self, table, prefix, fields, actor, audit_action):
        record = {"id": self._next_id(prefix)}
        record.update(fields)
        record["created_by"] = actor_name(actor)
        record["created_utc"] = datetime.now(timezone.utc).isoformat()
        table[record["id"]] = record
        self._audit(actor, audit_action, record["id"])
        return copy.deepcopy(record)

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    def _in_agency(self, table, agency_id):
        return [r for r in table.values() if r["agency_id"] == agency_id]

    def _check_ref_unique(self, records, field, value, scope):
        for existing in records:
            if existing[field] == value:
                raise ValidationError(
                    "%s %r is already recorded in this %s"
                    % (field, value, scope))

    @staticmethod
    def _latest_state_label(states):
        """The latest recorded state label, or ``recorded`` when
        no state has been recorded yet. This is the batch's fresh
        negative-control seam: the current state of a FOIA case
        and of an app definition is whatever the LATEST recorded
        state says, derived at read and never stored. The literal
        return line occurs exactly once in this module."""
        if not states:
            return "recorded"
        return states[-1]["state_label"]

    # -- Legal research & citation validation (idx 862, reference) -----
    # Labeled reference implementation: the research engine runs
    # on the fork's own corpus, never here. A request names its
    # query by SHA-256 digest ONLY -- there is no parameter that
    # can accept query text, mirroring the core's saved-search
    # design. An evidence-map record holds one fact's source
    # tracing: the fact and its source as opaque references, the
    # page/line locators recorded verbatim (the set's fork traces
    # every fact to its source page and line; the tracing is
    # recorded here, the tracing engine is not). A citation
    # outcome holds a reported validation label verbatim. A draft
    # link binds a request to a core document record; the draft's
    # content lives in the caller's system, as all content does
    # here. Every record carries ``reference_stub: True``.

    def record_research_request(self, actor, agency_id, workspace_id,
                                request_ref, query_sha256):
        """Record one reference research request. The query is
        named by digest only. Action: document_write."""
        self._guard(actor, "ext_research_request")
        self._agency(actor, agency_id)
        self.store.get_workspace(agency_id, workspace_id, actor)
        _non_empty(request_ref, "request_ref")
        _sha256(query_sha256, "query_sha256")
        with self._lock:
            self._check_ref_unique(
                [r for r in self._research_requests.values()
                 if r["workspace_id"] == workspace_id],
                "request_ref", request_ref, "workspace")
            return self._create(
                self._research_requests, "rsq-",
                {"agency_id": agency_id, "workspace_id": workspace_id,
                 "request_ref": request_ref, "query_sha256": query_sha256,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "researched_here": False},
                actor, "ext_research_request")

    def _research_request(self, actor, agency_id, request_id):
        self._agency(actor, agency_id)
        request = self._get(self._research_requests, request_id,
                            "research request")
        if request["agency_id"] != agency_id:
            raise NotFoundError(
                "research request not found in agency %s: %r"
                % (agency_id, request_id))
        return request

    def get_research_request(self, actor, agency_id, request_id):
        """Return one stored research request record.
        Action: agency_read."""
        return copy.deepcopy(
            self._research_request(actor, agency_id, request_id))

    def record_evidence_map_entry(self, actor, agency_id, request_id,
                                  map_ref, fact_ref, source_ref,
                                  page_label=None, line_label=None):
        """Record one evidence-map entry: a fact's source tracing,
        locators verbatim. Action: document_write."""
        self._guard(actor, "ext_evidence_map")
        self._research_request(actor, agency_id, request_id)
        _non_empty(map_ref, "map_ref")
        _non_empty(fact_ref, "fact_ref")
        _non_empty(source_ref, "source_ref")
        if page_label is not None:
            _non_empty(page_label, "page_label")
        if line_label is not None:
            _non_empty(line_label, "line_label")
        with self._lock:
            self._check_ref_unique(
                [e for e in self._evidence_maps.values()
                 if e["request_id"] == request_id],
                "map_ref", map_ref, "research request")
            return self._create(
                self._evidence_maps, "evm-",
                {"agency_id": agency_id, "request_id": request_id,
                 "map_ref": map_ref, "fact_ref": fact_ref,
                 "source_ref": source_ref, "page_label": page_label,
                 "line_label": line_label, "reference_stub": True,
                 "validated_here": False},
                actor, "ext_evidence_map")

    def record_citation_outcome(self, actor, agency_id, request_id,
                                outcome_ref, outcome_label):
        """Record one reported citation-validation outcome, label
        verbatim. Action: document_write."""
        self._guard(actor, "ext_citation_outcome")
        self._research_request(actor, agency_id, request_id)
        _non_empty(outcome_ref, "outcome_ref")
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._check_ref_unique(
                [o for o in self._citation_outcomes.values()
                 if o["request_id"] == request_id],
                "outcome_ref", outcome_ref, "research request")
            return self._create(
                self._citation_outcomes, "cto-",
                {"agency_id": agency_id, "request_id": request_id,
                 "outcome_ref": outcome_ref, "outcome_label": outcome_label,
                 "reference_stub": True, "validated_here": False},
                actor, "ext_citation_outcome")

    def record_research_draft_link(self, actor, agency_id, request_id,
                                   document_id):
        """Link one research request to a core document record in
        the request's workspace (the draft as registered metadata;
        its content is never here). Action: document_write."""
        self._guard(actor, "ext_research_draft_link")
        request = self._research_request(actor, agency_id, request_id)
        document = self.store.get_document(agency_id, document_id, actor)
        if document["workspace_id"] != request["workspace_id"]:
            raise NotFoundError(
                "document not found in research request workspace %s: %r"
                % (request["workspace_id"], document_id))
        with self._lock:
            for existing in self._research_draft_links.values():
                if (existing["request_id"] == request_id
                        and existing["document_id"] == document_id):
                    raise ValidationError(
                        "document %r is already linked to research "
                        "request %s" % (document_id, request_id))
            return self._create(
                self._research_draft_links, "rdl-",
                {"agency_id": agency_id, "request_id": request_id,
                 "document_id": document_id, "reference_stub": True,
                 "drafted_here": False},
                actor, "ext_research_draft_link")

    def research_request_view(self, actor, agency_id, request_id):
        """A research request record plus derived tallies: evidence
        map entry count, citation outcome count and latest reported
        outcome label, draft link count. Nothing derived is stored.
        Action: agency_read."""
        view = self.get_research_request(actor, agency_id, request_id)
        outcomes = self._sorted(
            [o for o in self._citation_outcomes.values()
             if o["request_id"] == request_id])
        view["evidence_map_count"] = sum(
            1 for e in self._evidence_maps.values()
            if e["request_id"] == request_id)
        view["citation_outcome_count"] = len(outcomes)
        view["latest_outcome_label"] = (
            outcomes[-1]["outcome_label"] if outcomes else None)
        view["draft_link_count"] = sum(
            1 for link in self._research_draft_links.values()
            if link["request_id"] == request_id)
        return view

    def list_research_requests(self, actor, agency_id, workspace_id=None):
        """List reference research requests in an agency.
        Action: agency_read."""
        self._agency(actor, agency_id)
        requests = self._in_agency(self._research_requests, agency_id)
        if workspace_id is not None:
            requests = [r for r in requests
                        if r["workspace_id"] == workspace_id]
        return copy.deepcopy(self._sorted(requests))

    def list_evidence_map_entries(self, actor, agency_id, request_id):
        """List evidence-map entries on one research request.
        Action: agency_read."""
        self._research_request(actor, agency_id, request_id)
        return copy.deepcopy(self._sorted(
            [e for e in self._evidence_maps.values()
             if e["request_id"] == request_id]))

    def list_citation_outcomes(self, actor, agency_id, request_id):
        """List citation outcomes on one research request.
        Action: agency_read."""
        self._research_request(actor, agency_id, request_id)
        return copy.deepcopy(self._sorted(
            [o for o in self._citation_outcomes.values()
             if o["request_id"] == request_id]))

    def list_research_draft_links(self, actor, agency_id, request_id):
        """List draft links on one research request.
        Action: agency_read."""
        self._research_request(actor, agency_id, request_id)
        return copy.deepcopy(self._sorted(
            [link for link in self._research_draft_links.values()
             if link["request_id"] == request_id]))

    # -- FOIA case management system of record (idx 863, built) --------
    # Records form: a FOIA case is the system-of-record entry for
    # one request's full lifecycle. Intake is the case record
    # itself: the request and the requester are opaque references
    # (no request text exists in any shape), the receipt date and
    # the statutory response period are recorded as data. States
    # are append-only reported labels whose current value derives
    # at read; the statutory due date derives at read from the
    # recorded receipt date plus the recorded period and is never
    # stored; overdue derives at read against an explicit as_of.
    # Exemption applications are recorded with labels verbatim,
    # optionally against a core document in the case's workspace;
    # consistency of application is served by the tallies the
    # views derive (per case and agency-wide), never by a score.
    # A release is a record with counts as reported. Nothing is
    # released here (``released_here`` is False on every record).

    def create_foia_case(self, actor, agency_id, workspace_id, case_ref,
                         request_ref, requester_ref, received_on,
                         statutory_period_days):
        """Create one FOIA case record (intake). The due date is
        NOT stored; it derives at read. Action: document_write."""
        self._guard(actor, "ext_foia_case")
        self._agency(actor, agency_id)
        self.store.get_workspace(agency_id, workspace_id, actor)
        _non_empty(case_ref, "case_ref")
        _non_empty(request_ref, "request_ref")
        _non_empty(requester_ref, "requester_ref")
        received = _parse_date(received_on, "received_on")
        _positive_int(statutory_period_days, "statutory_period_days")
        with self._lock:
            self._check_ref_unique(
                [c for c in self._foia_cases.values()
                 if c["workspace_id"] == workspace_id],
                "case_ref", case_ref, "workspace")
            return self._create(
                self._foia_cases, "foi-",
                {"agency_id": agency_id, "workspace_id": workspace_id,
                 "case_ref": case_ref, "request_ref": request_ref,
                 "requester_ref": requester_ref,
                 "received_on": received.isoformat(),
                 "statutory_period_days": statutory_period_days,
                 "released_here": False},
                actor, "ext_foia_case")

    def _foia_case(self, actor, agency_id, case_id):
        self._agency(actor, agency_id)
        case = self._get(self._foia_cases, case_id, "FOIA case")
        if case["agency_id"] != agency_id:
            raise NotFoundError(
                "FOIA case not found in agency %s: %r" % (agency_id, case_id))
        return case

    def get_foia_case(self, actor, agency_id, case_id):
        """Return one stored FOIA case record (no derived state,
        due date, or overdue key). Action: agency_read."""
        return copy.deepcopy(self._foia_case(actor, agency_id, case_id))

    def record_foia_state(self, actor, agency_id, case_id, state_label):
        """Append one reported lifecycle state record to a FOIA
        case. Action: document_write."""
        self._guard(actor, "ext_foia_state")
        self._foia_case(actor, agency_id, case_id)
        if state_label not in FOIA_CASE_STATES:
            raise ValidationError(
                "state_label must be one of %s"
                % (", ".join(FOIA_CASE_STATES),))
        with self._lock:
            return self._create(
                self._foia_states, "fos-",
                {"agency_id": agency_id, "case_id": case_id,
                 "state_label": state_label},
                actor, "ext_foia_state")

    def record_exemption_application(self, actor, agency_id, case_id,
                                     exemption_label, document_id=None):
        """Record one exemption application, label verbatim,
        optionally against a core document in the case's
        workspace. Action: document_write."""
        self._guard(actor, "ext_foia_exemption")
        case = self._foia_case(actor, agency_id, case_id)
        _non_empty(exemption_label, "exemption_label")
        if document_id is not None:
            document = self.store.get_document(agency_id, document_id, actor)
            if document["workspace_id"] != case["workspace_id"]:
                raise NotFoundError(
                    "document not found in FOIA case workspace %s: %r"
                    % (case["workspace_id"], document_id))
        with self._lock:
            return self._create(
                self._foia_exemptions, "fxa-",
                {"agency_id": agency_id, "case_id": case_id,
                 "document_id": document_id,
                 "exemption_label": exemption_label,
                 "released_here": False},
                actor, "ext_foia_exemption")

    def record_foia_release(self, actor, agency_id, case_id, release_ref,
                            reported_document_count):
        """Record one disclosure release, count as reported.
        Action: document_write."""
        self._guard(actor, "ext_foia_release")
        self._foia_case(actor, agency_id, case_id)
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

    def _foia_derived(self, case, as_of):
        """Every derived FOIA value for one case, computed at read
        from the recorded data: current state (latest recorded
        label, via the seam), statutory due date (receipt date
        plus the recorded period), overdue (as_of past the due
        date while the case is in a non-terminal state), and the
        recorded tallies. Nothing here is stored."""
        states = self._sorted(
            [s for s in self._foia_states.values()
             if s["case_id"] == case["id"]])
        current_state = self._latest_state_label(states)
        due_on = _parse_date(case["received_on"], "received_on") + timedelta(
            days=case["statutory_period_days"])
        exemptions = [e for e in self._foia_exemptions.values()
                      if e["case_id"] == case["id"]]
        tallies = {}
        for exemption in exemptions:
            label = exemption["exemption_label"]
            tallies[label] = tallies.get(label, 0) + 1
        releases = [r for r in self._foia_releases.values()
                    if r["case_id"] == case["id"]]
        return {
            "current_state": current_state,
            "state_record_count": len(states),
            "due_on": due_on.isoformat(),
            "overdue": bool(
                as_of > due_on and current_state not in FOIA_TERMINAL_STATES),
            "exemption_application_count": len(exemptions),
            "exemption_tallies": tallies,
            "release_count": len(releases),
            "reported_released_documents": sum(
                r["reported_document_count"] for r in releases),
        }

    def foia_case_view(self, actor, agency_id, case_id, as_of=None):
        """A FOIA case record plus every derived value (current
        state, due date, overdue, tallies). The stored record
        carries none of them. Action: agency_read."""
        case = self._foia_case(actor, agency_id, case_id)
        moment = _parse_date(as_of, "as_of") if as_of is not None \
            else _utc_today()
        view = copy.deepcopy(case)
        view.update(self._foia_derived(case, moment))
        return view

    def foia_requester_view(self, actor, agency_id, case_id, as_of=None):
        """The requester-portal read surface: what the requester
        of record sees of their own request -- its derived state,
        its statutory due date, whether it stands overdue, and its
        recorded releases. A derived view over the case records;
        no portal is operated here. Action: agency_read."""
        case = self._foia_case(actor, agency_id, case_id)
        moment = _parse_date(as_of, "as_of") if as_of is not None \
            else _utc_today()
        derived = self._foia_derived(case, moment)
        return {
            "case_id": case["id"],
            "case_ref": case["case_ref"],
            "request_ref": case["request_ref"],
            "requester_ref": case["requester_ref"],
            "received_on": case["received_on"],
            "current_state": derived["current_state"],
            "due_on": derived["due_on"],
            "overdue": derived["overdue"],
            "release_count": derived["release_count"],
            "reported_released_documents":
                derived["reported_released_documents"],
        }

    def foia_agency_view(self, actor, agency_id, as_of=None):
        """The analyst/stakeholder read surface: the agency's FOIA
        portfolio derived at read -- case counts by current state,
        the overdue count, agency-wide exemption application
        tallies (the consistency surface: the same labels, tallied
        the same way, across every case), and release totals.
        Counts only; nothing is scored. Action: agency_read."""
        self._agency(actor, agency_id)
        moment = _parse_date(as_of, "as_of") if as_of is not None \
            else _utc_today()
        cases = self._sorted(self._in_agency(self._foia_cases, agency_id))
        by_state = {}
        overdue_count = 0
        tallies = {}
        release_count = 0
        released_documents = 0
        for case in cases:
            derived = self._foia_derived(case, moment)
            state = derived["current_state"]
            by_state[state] = by_state.get(state, 0) + 1
            if derived["overdue"]:
                overdue_count += 1
            for label, count in derived["exemption_tallies"].items():
                tallies[label] = tallies.get(label, 0) + count
            release_count += derived["release_count"]
            released_documents += derived["reported_released_documents"]
        return {
            "agency_id": agency_id,
            "case_count": len(cases),
            "cases_by_current_state": by_state,
            "overdue_case_count": overdue_count,
            "exemption_tallies": tallies,
            "release_count": release_count,
            "reported_released_documents": released_documents,
            "method": "deterministic_counts",
        }

    def list_foia_cases(self, actor, agency_id, workspace_id=None):
        """List FOIA case records in an agency. Action: agency_read."""
        self._agency(actor, agency_id)
        cases = self._in_agency(self._foia_cases, agency_id)
        if workspace_id is not None:
            cases = [c for c in cases if c["workspace_id"] == workspace_id]
        return copy.deepcopy(self._sorted(cases))

    def list_foia_states(self, actor, agency_id, case_id):
        """List reported state records on one FOIA case.
        Action: agency_read."""
        self._foia_case(actor, agency_id, case_id)
        return copy.deepcopy(self._sorted(
            [s for s in self._foia_states.values()
             if s["case_id"] == case_id]))

    def list_exemption_applications(self, actor, agency_id, case_id):
        """List exemption applications on one FOIA case.
        Action: agency_read."""
        self._foia_case(actor, agency_id, case_id)
        return copy.deepcopy(self._sorted(
            [e for e in self._foia_exemptions.values()
             if e["case_id"] == case_id]))

    def list_foia_releases(self, actor, agency_id, case_id):
        """List release records on one FOIA case.
        Action: agency_read."""
        self._foia_case(actor, agency_id, case_id)
        return copy.deepcopy(self._sorted(
            [r for r in self._foia_releases.values()
             if r["case_id"] == case_id]))

    # -- Discovery platform app builder (idx 864, built) ---------------
    # Records form: the extensibility surface of the discovery
    # platform as a registry. A customer-built application is a
    # definition record: its component manifest is held as DATA
    # (an ordered list of component labels) and the definition is
    # never run -- per the house doctrine the registry never
    # executes. Bindings attach a definition to core workspaces of
    # the same agency. Enablement is append-only reported state
    # records whose current value derives at read. The builder
    # interface and the application runtime are not built and not
    # claimed: ``executed_here`` and ``runtime_here`` are False on
    # every definition record.

    def register_app_definition(self, actor, agency_id, workspace_id,
                                app_ref, components, label=None):
        """Register one application definition as data.
        Action: document_write."""
        self._guard(actor, "ext_app_definition")
        self._agency(actor, agency_id)
        self.store.get_workspace(agency_id, workspace_id, actor)
        _non_empty(app_ref, "app_ref")
        components = _string_list(components, "components")
        if label is not None:
            _non_empty(label, "label")
        with self._lock:
            self._check_ref_unique(
                [a for a in self._app_definitions.values()
                 if a["workspace_id"] == workspace_id],
                "app_ref", app_ref, "workspace")
            return self._create(
                self._app_definitions, "app-",
                {"agency_id": agency_id, "workspace_id": workspace_id,
                 "app_ref": app_ref, "label": label,
                 "components": components, "definition_only": True,
                 "executed_here": False, "runtime_here": False},
                actor, "ext_app_definition")

    def _app_definition(self, actor, agency_id, app_id):
        self._agency(actor, agency_id)
        definition = self._get(self._app_definitions, app_id,
                               "app definition")
        if definition["agency_id"] != agency_id:
            raise NotFoundError(
                "app definition not found in agency %s: %r"
                % (agency_id, app_id))
        return definition

    def get_app_definition(self, actor, agency_id, app_id):
        """Return one stored app definition record (no derived
        state key). Action: agency_read."""
        return copy.deepcopy(self._app_definition(actor, agency_id, app_id))

    def record_app_state(self, actor, agency_id, app_id, state_label):
        """Append one reported state record to an app definition.
        Action: document_write."""
        self._guard(actor, "ext_app_state")
        self._app_definition(actor, agency_id, app_id)
        if state_label not in APP_STATES:
            raise ValidationError(
                "state_label must be one of %s" % (", ".join(APP_STATES),))
        with self._lock:
            return self._create(
                self._app_states, "aps-",
                {"agency_id": agency_id, "app_id": app_id,
                 "state_label": state_label},
                actor, "ext_app_state")

    def record_app_binding(self, actor, agency_id, app_id,
                           target_workspace_id):
        """Bind one app definition to another core workspace of
        the same agency (the definition as data is attached; no
        application runs). Action: document_write."""
        self._guard(actor, "ext_app_binding")
        self._app_definition(actor, agency_id, app_id)
        self.store.get_workspace(agency_id, target_workspace_id, actor)
        with self._lock:
            for existing in self._app_bindings.values():
                if (existing["app_id"] == app_id
                        and existing["target_workspace_id"]
                        == target_workspace_id):
                    raise ValidationError(
                        "app definition %s is already bound to "
                        "workspace %s" % (app_id, target_workspace_id))
            return self._create(
                self._app_bindings, "apb-",
                {"agency_id": agency_id, "app_id": app_id,
                 "target_workspace_id": target_workspace_id,
                 "executed_here": False},
                actor, "ext_app_binding")

    def app_definition_view(self, actor, agency_id, app_id):
        """An app definition record plus derived values: current
        state (latest recorded label), state record count,
        binding count, component count. Nothing derived is
        stored. Action: agency_read."""
        view = self.get_app_definition(actor, agency_id, app_id)
        states = self._sorted(
            [s for s in self._app_states.values()
             if s["app_id"] == app_id])
        view["current_state"] = self._latest_state_label(states)
        view["state_record_count"] = len(states)
        view["binding_count"] = sum(
            1 for b in self._app_bindings.values()
            if b["app_id"] == app_id)
        view["component_count"] = len(view["components"])
        return view

    def list_app_definitions(self, actor, agency_id, workspace_id=None):
        """List app definitions in an agency. Action: agency_read."""
        self._agency(actor, agency_id)
        definitions = self._in_agency(self._app_definitions, agency_id)
        if workspace_id is not None:
            definitions = [d for d in definitions
                           if d["workspace_id"] == workspace_id]
        return copy.deepcopy(self._sorted(definitions))

    def list_app_states(self, actor, agency_id, app_id):
        """List reported state records on one app definition.
        Action: agency_read."""
        self._app_definition(actor, agency_id, app_id)
        return copy.deepcopy(self._sorted(
            [s for s in self._app_states.values()
             if s["app_id"] == app_id]))

    def list_app_bindings(self, actor, agency_id, app_id):
        """List binding records on one app definition.
        Action: agency_read."""
        self._app_definition(actor, agency_id, app_id)
        return copy.deepcopy(self._sorted(
            [b for b in self._app_bindings.values()
             if b["app_id"] == app_id]))
