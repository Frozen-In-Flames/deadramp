"""Final GAPS batch extensions for Legal & Policy L2 — the
founding singleton's own gap entries.

Clean-room, standard-library-only extensions for the 7 open
entries of the GAPS.md section "Singleton 49 -- Legal & Policy L2
(1 fork, new category)" (inventory idx 485-490 and 492; see
``BATCH-SINGLETON49.md`` in the group directory for the per-entry
disposition). The section's other two entries (idx 491 identity
provider / federation, idx 493 FIPS-validated cryptography) were
already closed ``re-scoped`` under PLATFORM-LAYER.md and are not
this module's concern. This module is a wrapper around
:class:`LegalPolStore`; every core module -- and the remainder
additions' ``extensions.py`` -- is untouched and byte-identical
to the shipped build.

**The founding privacy rule binds absolutely, here as in the
core:** documents exist in this substrate ONLY as metadata +
SHA-256 records in the core document registry, and the legal
corpus exists ONLY as source records in the core library
registry. No entity shape in this module has a field that can
hold document content, corpus content, generated text, a prompt,
a model completion, or query text -- those fields **do not
exist**. Methods accept only their named parameters, so a caller
cannot smuggle a forbidden field into a record (pinned by tests:
an unexpected keyword raises ``TypeError``). Sessions,
executions, searches, documents, library sources, licensors, and
endpoints are opaque caller-supplied references or labels.

Honesty of form, per the batch brief: an "engine" or "runtime"
here is its in-substrate form -- records plus deterministic
derivations over the group's OWN records (core records and this
module's records):

- The legal corpus content is a content REGISTRY over core
  library sources: extent stored as reported counts and an
  optional corpus digest, append-only reported curation events
  whose latest label is the derived current state, and license
  records over opaque licensor references. The content itself is
  never held, curated, or licensed here.
- The sandbox runtime is provisioning-request records over core
  sandbox sessions plus reported outcome records; the core's
  single-use rule and its derived ``sandbox_consumed`` flag carry
  unchanged. No environment is provisioned, isolated, or torn
  down here.
- The code execution engine is job records bound to core
  execution records plus reported outcome records (outcome label
  verbatim, exit code as reported). The core records executions;
  this module records what an external engine reported about
  them. Nothing is executed here.
- The four stub-engine entries ship as labeled reference
  implementations: every record carries ``reference_stub: True``
  and state ``recorded_reference_only``. Agent runs are request
  and reported-outcome records (no inference, no orchestration,
  no retrieval runs here); model transport bridges are
  definition records (``reference_transport: True``; nothing is
  transported); search engines are definition records plus
  reported run records bound to core saved searches (nothing is
  indexed, ranked, or searched here; a run record holds a
  reported result count and never a query); document generation
  is request records plus reported outputs held as core document
  references (nothing is drafted or generated here); security
  monitoring is feed definitions plus reported observation
  records (nothing is monitored or scanned here).

Doctrines carried from the core: derived-never-stored for every
computed value (current curation state, outcome counts and
latest labels, core session flags read through the core's own
derived views); validation before mutation, so a failed
operation consumes no id and changes nothing; append-only audit
on the core store's log with ``ext_``-prefixed actions for every
successful extension mutation, and denied write attempts
recorded with a ``:denied`` suffix; RBAC via
:mod:`legalpol.access` -- corpus writes map to the core
``library_write`` action (the corpus hangs off the platform
library), every other extension write maps to ``document_write``
(the additions unit's convention: the extension surface is
records over the document/matter substrate), and agency-scoped
reads resolve the agency through the core store, which enforces
``agency_read`` and the agency membership boundary on every
operation. Nothing is scored.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

CURATION_EVENTS = (
    "reported_added", "reported_updated", "reported_withdrawn",
    "reported_recatalogued",
)
SEARCH_ENGINE_KINDS = ("full_text", "semantic", "hybrid")
SANDBOX_OUTCOMES = (
    "reported_provisioned", "reported_failed", "reported_torn_down",
)
EXECUTION_OUTCOMES = (
    "reported_completed", "reported_failed", "reported_timed_out",
    "reported_terminated",
)

_REFERENCE_STATE = "recorded_reference_only"
_HEX = frozenset("0123456789abcdef")


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


def _sha256(value, what):
    """A SHA-256 digest: exactly 64 lowercase hex characters."""
    if (not isinstance(value, str) or len(value) != 64
            or any(ch not in _HEX for ch in value)):
        raise ValidationError(
            "%s must be exactly 64 lowercase hex characters" % (what,))
    return value


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class LegalPolSingletonExtensions:
    """Extension surface wrapping one :class:`LegalPolStore`."""

    def __init__(self, store):
        self.store = store
        self._corpus_contents = {}
        self._curation_events = {}
        self._corpus_licenses = {}
        self._agent_runs = {}
        self._agent_run_outcomes = {}
        self._model_bridges = {}
        self._search_engines = {}
        self._search_engine_runs = {}
        self._sandbox_requests = {}
        self._sandbox_outcomes = {}
        self._execution_jobs = {}
        self._execution_outcomes = {}
        self._generation_requests = {}
        self._generation_outputs = {}
        self._monitoring_feeds = {}
        self._monitoring_observations = {}
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

    def _guard(self, actor, audit_action, rbac_action="document_write"):
        """Enforce an extension write permission before any state
        change. A denied attempt is recorded on the audit log with
        a ``:denied`` suffix before the error propagates; a missing
        actor is denied outright. A plain string carries identity
        but no role (the service layer enforces its role),
        matching the core convention."""
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (rbac_action,))
        if hasattr(actor, "role"):
            try:
                require(actor, rbac_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": rbac_action})
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
        record["created_utc"] = _utc_now()
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

    def _scoped(self, actor, agency_id, table, record_id, what):
        """Resolve one agency-scoped extension record."""
        self._agency(actor, agency_id)
        record = self._get(table, record_id, what)
        if record["agency_id"] != agency_id:
            raise NotFoundError(
                "%s not found in agency %s: %r" % (what, agency_id, record_id))
        return record

    def _session_in_workspace(self, actor, agency_id, workspace_id,
                              session_id):
        """Resolve a core session (derived view) and require it to
        sit in the named workspace of this agency."""
        session = self.store.get_session(agency_id, session_id, actor)
        if session["workspace_id"] != workspace_id:
            raise NotFoundError(
                "session not found in workspace %s: %r"
                % (workspace_id, session_id))
        return session

    # -- Legal corpus content (idx 486, built) --------------------------
    # Records form, over the PLATFORM library (the core's library
    # sources are not agency-scoped; corpus writes map to the
    # core ``library_write`` action, reads are open to any actor,
    # exactly as in the core): a content record registers the
    # REPORTED extent of one library source's corpus -- an item
    # count stored as reported and an optional corpus digest
    # (SHA-256 of the corpus as reported by its curator; the
    # digest is a record about the content, never the content).
    # Curation is append-only reported event records whose latest
    # label is the derived current state. Licensing is license
    # records over opaque licensor references. The content itself
    # is never held, curated, or licensed here:
    # ``content_held_here``, ``curated_here``, and
    # ``licensed_here`` are False on every record.

    @staticmethod
    def _current_curation_label(events):
        """The current curation state of a corpus content record:
        the LATEST recorded curation event label, or ``recorded``
        when no event has been recorded yet.

        MUTATION DRILL NOTE: this seam is this batch unit's fresh
        negative control target -- see tests/README.md."""
        if not events:
            return "recorded"
        return events[-1]["event_label"]

    def _curation_events_for(self, content_id):
        return self._sorted(
            [e for e in self._curation_events.values()
             if e["content_id"] == content_id])

    def register_corpus_content(self, actor, source_id, content_ref,
                                reported_item_count, content_sha256=None):
        """Register the reported extent of one library source's
        corpus content. Action: library_write."""
        self._guard(actor, "ext_corpus_content", rbac_action="library_write")
        self.store.get_library_source(source_id, actor)
        _non_empty(content_ref, "content_ref")
        _count(reported_item_count, "reported_item_count")
        if content_sha256 is not None:
            _sha256(content_sha256, "content_sha256")
        with self._lock:
            self._check_ref_unique(
                [c for c in self._corpus_contents.values()
                 if c["source_id"] == source_id],
                "content_ref", content_ref, "library source")
            return self._create(
                self._corpus_contents, "cor-",
                {"source_id": source_id, "content_ref": content_ref,
                 "reported_item_count": reported_item_count,
                 "content_sha256": content_sha256,
                 "content_held_here": False, "curated_here": False,
                 "licensed_here": False},
                actor, "ext_corpus_content")

    def get_corpus_content(self, actor, content_id):
        """Return one stored corpus content record (no derived
        state key). Reads are open to any actor, as in the core
        library."""
        return copy.deepcopy(
            self._get(self._corpus_contents, content_id, "corpus content"))

    def record_curation_event(self, actor, content_id, event_ref,
                              event_label):
        """Append one reported curation event to a corpus content
        record. Action: library_write."""
        self._guard(actor, "ext_curation_event", rbac_action="library_write")
        self._get(self._corpus_contents, content_id, "corpus content")
        _non_empty(event_ref, "event_ref")
        if event_label not in CURATION_EVENTS:
            raise ValidationError(
                "event_label must be one of %s"
                % (", ".join(CURATION_EVENTS),))
        with self._lock:
            self._check_ref_unique(
                [e for e in self._curation_events.values()
                 if e["content_id"] == content_id],
                "event_ref", event_ref, "corpus content record")
            return self._create(
                self._curation_events, "cev-",
                {"content_id": content_id, "event_ref": event_ref,
                 "event_label": event_label, "curated_here": False},
                actor, "ext_curation_event")

    def record_corpus_license(self, actor, content_id, license_ref,
                              licensor_ref, license_label):
        """Record one license over a corpus content record, the
        license label verbatim and the licensor an opaque
        reference. Action: library_write."""
        self._guard(actor, "ext_corpus_license", rbac_action="library_write")
        self._get(self._corpus_contents, content_id, "corpus content")
        _non_empty(license_ref, "license_ref")
        _non_empty(licensor_ref, "licensor_ref")
        _non_empty(license_label, "license_label")
        with self._lock:
            self._check_ref_unique(
                [r for r in self._corpus_licenses.values()
                 if r["content_id"] == content_id],
                "license_ref", license_ref, "corpus content record")
            return self._create(
                self._corpus_licenses, "lic-",
                {"content_id": content_id, "license_ref": license_ref,
                 "licensor_ref": licensor_ref,
                 "license_label": license_label, "licensed_here": False},
                actor, "ext_corpus_license")

    def corpus_content_view(self, actor, content_id):
        """A corpus content record plus derived state: the current
        curation state (latest recorded event label, via the
        seam), whether that state is withdrawn, the curation
        event count, and the license count. Nothing derived is
        stored."""
        view = self.get_corpus_content(actor, content_id)
        events = self._curation_events_for(content_id)
        current = self._current_curation_label(events)
        view["current_curation_state"] = current
        view["is_withdrawn"] = current == "reported_withdrawn"
        view["curation_event_count"] = len(events)
        view["license_count"] = sum(
            1 for r in self._corpus_licenses.values()
            if r["content_id"] == content_id)
        return view

    def list_corpus_contents(self, actor, source_id=None):
        """List corpus content records, optionally for one library
        source."""
        records = list(self._corpus_contents.values())
        if source_id is not None:
            records = [c for c in records if c["source_id"] == source_id]
        return copy.deepcopy(self._sorted(records))

    def corpus_summary(self, actor):
        """Deterministic counts over the platform library and this
        module's corpus records: sources, content records, sources
        with content, curation events by label, licenses. Method
        ``deterministic_counts`` -- counts only; nothing is
        inferred or scored, and no content is held."""
        sources = self.store.list_library_sources(actor)
        by_label = {}
        for event in self._curation_events.values():
            by_label[event["event_label"]] = (
                by_label.get(event["event_label"], 0) + 1)
        return {
            "library_source_count": len(sources),
            "content_record_count": len(self._corpus_contents),
            "sources_with_content": len(
                {c["source_id"] for c in self._corpus_contents.values()}),
            "curation_event_count": len(self._curation_events),
            "curation_events_by_label": by_label,
            "license_count": len(self._corpus_licenses),
            "method": "deterministic_counts",
            "content_held_here": False,
        }

    # -- AI agent runtime (idx 485, reference) --------------------------
    # Labeled reference form: an agent run is a request record
    # over a core session, and its outcome is a reported record
    # holding an opaque result reference plus an optional verbatim
    # reported label. Grounding / retrieval is named on the run
    # record as not performed (``retrieved_here`` False); the
    # model transport bridge is a definition record carrying
    # ``reference_transport: True``. No inference runs, nothing is
    # orchestrated, retrieved, or transported here.

    def record_agent_run(self, actor, agency_id, workspace_id, session_id,
                         run_ref, task_label=None):
        """Record one agent-run request over a core session.
        Action: document_write."""
        self._guard(actor, "ext_agent_run")
        self._agency(actor, agency_id)
        self.store.get_workspace(agency_id, workspace_id, actor)
        self._session_in_workspace(actor, agency_id, workspace_id, session_id)
        _non_empty(run_ref, "run_ref")
        if task_label is not None:
            _non_empty(task_label, "task_label")
        with self._lock:
            self._check_ref_unique(
                [r for r in self._agent_runs.values()
                 if r["session_id"] == session_id],
                "run_ref", run_ref, "session")
            return self._create(
                self._agent_runs, "arr-",
                {"agency_id": agency_id, "workspace_id": workspace_id,
                 "session_id": session_id, "run_ref": run_ref,
                 "task_label": task_label, "reference_stub": True,
                 "state": _REFERENCE_STATE, "inference_here": False,
                 "orchestrated_here": False, "retrieved_here": False},
                actor, "ext_agent_run")

    def record_agent_run_outcome(self, actor, agency_id, run_id, outcome_ref,
                                 result_ref=None, reported_label=None):
        """Record one reported agent-run outcome: an opaque result
        reference plus an optional verbatim reported label.
        Action: document_write."""
        self._guard(actor, "ext_agent_run_outcome")
        self._scoped(actor, agency_id, self._agent_runs, run_id, "agent run")
        _non_empty(outcome_ref, "outcome_ref")
        if result_ref is not None:
            _non_empty(result_ref, "result_ref")
        if reported_label is not None:
            _non_empty(reported_label, "reported_label")
        with self._lock:
            self._check_ref_unique(
                [o for o in self._agent_run_outcomes.values()
                 if o["run_id"] == run_id],
                "outcome_ref", outcome_ref, "agent run")
            return self._create(
                self._agent_run_outcomes, "aro-",
                {"agency_id": agency_id, "run_id": run_id,
                 "outcome_ref": outcome_ref, "result_ref": result_ref,
                 "reported_label": reported_label,
                 "reference_stub": True, "inference_here": False},
                actor, "ext_agent_run_outcome")

    def agent_run_view(self, actor, agency_id, run_id):
        """An agent-run record plus derived outcome state: the
        outcome count and the latest recorded outcome's reported
        label. Action: agency_read."""
        view = copy.deepcopy(
            self._scoped(actor, agency_id, self._agent_runs, run_id,
                         "agent run"))
        outcomes = self._sorted(
            [o for o in self._agent_run_outcomes.values()
             if o["run_id"] == run_id])
        view["outcome_count"] = len(outcomes)
        view["latest_reported_label"] = (
            outcomes[-1]["reported_label"] if outcomes else None)
        return view

    def list_agent_runs(self, actor, agency_id, session_id):
        """List agent-run records over one core session.
        Action: agency_read."""
        self._agency(actor, agency_id)
        return copy.deepcopy(self._sorted(
            [r for r in self._agent_runs.values()
             if r["agency_id"] == agency_id
             and r["session_id"] == session_id]))

    def define_model_bridge(self, actor, agency_id, bridge_ref,
                            endpoint_label):
        """Define one model transport bridge, as a labeled
        reference record. Action: document_write."""
        self._guard(actor, "ext_model_bridge")
        self._agency(actor, agency_id)
        _non_empty(bridge_ref, "bridge_ref")
        _non_empty(endpoint_label, "endpoint_label")
        with self._lock:
            self._check_ref_unique(
                self._in_agency(self._model_bridges, agency_id),
                "bridge_ref", bridge_ref, "agency")
            return self._create(
                self._model_bridges, "mbr-",
                {"agency_id": agency_id, "bridge_ref": bridge_ref,
                 "endpoint_label": endpoint_label,
                 "reference_stub": True, "reference_transport": True,
                 "state": _REFERENCE_STATE, "transported_here": False},
                actor, "ext_model_bridge")

    def list_model_bridges(self, actor, agency_id):
        """List model bridge definitions in an agency.
        Action: agency_read."""
        self._agency(actor, agency_id)
        return copy.deepcopy(self._sorted(
            self._in_agency(self._model_bridges, agency_id)))

    # -- Full-text & semantic search engines (idx 487, reference) -------
    # Labeled reference form: an engine is a definition record,
    # and a run is a reported record bound to the definition and
    # optionally to a core saved search, holding a result count
    # stored as reported. Nothing is indexed, ranked, or searched
    # here. There is no parameter that could accept query text --
    # the core's digest-only discipline carries unchanged (a
    # smuggled ``query_text`` keyword raises ``TypeError``).

    def define_search_engine(self, actor, agency_id, engine_ref, engine_kind):
        """Define one search engine, as a labeled reference
        record. Action: document_write."""
        self._guard(actor, "ext_search_engine")
        self._agency(actor, agency_id)
        _non_empty(engine_ref, "engine_ref")
        if engine_kind not in SEARCH_ENGINE_KINDS:
            raise ValidationError(
                "engine_kind must be one of %s"
                % (", ".join(SEARCH_ENGINE_KINDS),))
        with self._lock:
            self._check_ref_unique(
                self._in_agency(self._search_engines, agency_id),
                "engine_ref", engine_ref, "agency")
            return self._create(
                self._search_engines, "sen-",
                {"agency_id": agency_id, "engine_ref": engine_ref,
                 "engine_kind": engine_kind, "reference_stub": True,
                 "state": _REFERENCE_STATE, "indexed_here": False,
                 "ranked_here": False, "searched_here": False},
                actor, "ext_search_engine")

    def record_search_engine_run(self, actor, agency_id, engine_id, run_ref,
                                 reported_result_count, search_id=None):
        """Record one reported search-engine run. ``search_id``
        when given must name a core saved search in this agency.
        Action: document_write."""
        self._guard(actor, "ext_search_engine_run")
        self._scoped(actor, agency_id, self._search_engines, engine_id,
                     "search engine")
        if search_id is not None:
            self.store.get_search(agency_id, search_id, actor)
        _non_empty(run_ref, "run_ref")
        _count(reported_result_count, "reported_result_count")
        with self._lock:
            self._check_ref_unique(
                [r for r in self._search_engine_runs.values()
                 if r["engine_id"] == engine_id],
                "run_ref", run_ref, "search engine")
            return self._create(
                self._search_engine_runs, "srn-",
                {"agency_id": agency_id, "engine_id": engine_id,
                 "search_id": search_id, "run_ref": run_ref,
                 "reported_result_count": reported_result_count,
                 "reference_stub": True, "searched_here": False,
                 "ranked_here": False},
                actor, "ext_search_engine_run")

    def list_search_engines(self, actor, agency_id):
        """List search engine definitions in an agency.
        Action: agency_read."""
        self._agency(actor, agency_id)
        return copy.deepcopy(self._sorted(
            self._in_agency(self._search_engines, agency_id)))

    def list_search_engine_runs(self, actor, agency_id, engine_id):
        """List reported runs of one search engine definition.
        Action: agency_read."""
        self._scoped(actor, agency_id, self._search_engines, engine_id,
                     "search engine")
        return copy.deepcopy(self._sorted(
            [r for r in self._search_engine_runs.values()
             if r["engine_id"] == engine_id]))

    # -- Sandbox runtime (idx 488, built) --------------------------------
    # Records form: a provisioning request names a core SANDBOX
    # session (a non-sandbox session is refused), and outcomes are
    # append-only reported records. The runtime view reads the
    # core session's own derived flags (``sandbox_consumed``,
    # lifecycle status) through the core at read. The environment
    # itself -- isolation, resource limits, teardown -- is never
    # provisioned here: ``provisioned_here`` and ``runtime_here``
    # are False on every record. The core's single-use rule over
    # execution records is untouched and carries unchanged.

    def request_sandbox_provisioning(self, actor, agency_id, session_id,
                                     request_ref):
        """Record one sandbox provisioning request over a core
        sandbox session. Action: document_write."""
        self._guard(actor, "ext_sandbox_provisioning")
        self._agency(actor, agency_id)
        session = self.store.get_session(agency_id, session_id, actor)
        if not session["sandbox"]:
            raise ValidationError(
                "session %s is not a sandbox session; the sandbox "
                "runtime surface provisions sandbox sessions only"
                % (session_id,))
        _non_empty(request_ref, "request_ref")
        with self._lock:
            self._check_ref_unique(
                [r for r in self._sandbox_requests.values()
                 if r["session_id"] == session_id],
                "request_ref", request_ref, "session")
            return self._create(
                self._sandbox_requests, "sbp-",
                {"agency_id": agency_id,
                 "workspace_id": session["workspace_id"],
                 "session_id": session_id, "request_ref": request_ref,
                 "provisioned_here": False, "runtime_here": False},
                actor, "ext_sandbox_provisioning")

    def record_sandbox_outcome(self, actor, agency_id, request_id,
                               outcome_label):
        """Append one reported provisioning outcome to a request.
        Action: document_write."""
        self._guard(actor, "ext_sandbox_outcome")
        self._scoped(actor, agency_id, self._sandbox_requests, request_id,
                     "sandbox provisioning request")
        if outcome_label not in SANDBOX_OUTCOMES:
            raise ValidationError(
                "outcome_label must be one of %s"
                % (", ".join(SANDBOX_OUTCOMES),))
        with self._lock:
            return self._create(
                self._sandbox_outcomes, "sbo-",
                {"agency_id": agency_id, "request_id": request_id,
                 "outcome_label": outcome_label,
                 "provisioned_here": False, "runtime_here": False},
                actor, "ext_sandbox_outcome")

    def sandbox_runtime_view(self, actor, agency_id, request_id):
        """A provisioning request plus derived state: the outcome
        count, the latest recorded outcome label, and the core
        session's own derived flags read through the core at read
        (lifecycle status, ``sandbox_consumed``). Nothing derived
        is stored. Action: agency_read."""
        view = copy.deepcopy(
            self._scoped(actor, agency_id, self._sandbox_requests,
                         request_id, "sandbox provisioning request"))
        outcomes = self._sorted(
            [o for o in self._sandbox_outcomes.values()
             if o["request_id"] == request_id])
        session = self.store.get_session(
            agency_id, view["session_id"], actor)
        view["outcome_count"] = len(outcomes)
        view["latest_outcome_label"] = (
            outcomes[-1]["outcome_label"] if outcomes else None)
        view["session_status"] = session["status"]
        view["sandbox_consumed"] = session["sandbox_consumed"]
        return view

    def list_sandbox_requests(self, actor, agency_id, session_id):
        """List provisioning requests over one core session.
        Action: agency_read."""
        self._agency(actor, agency_id)
        return copy.deepcopy(self._sorted(
            [r for r in self._sandbox_requests.values()
             if r["agency_id"] == agency_id
             and r["session_id"] == session_id]))

    # -- Code execution engine (idx 489, built) --------------------------
    # Records form: a job binds one CORE execution record (the
    # core records that an execution was reported; this module
    # records what an external engine reported about it), and
    # outcomes are append-only reported records -- an outcome
    # label verbatim and an exit code stored as reported. Nothing
    # is executed here: ``executed_here`` is False on every
    # record.

    def _execution_in_session(self, actor, agency_id, session_id,
                              execution_id):
        for execution in self.store.list_executions(
                agency_id, session_id, actor):
            if execution["id"] == execution_id:
                return execution
        raise NotFoundError(
            "execution not found in session %s: %r"
            % (session_id, execution_id))

    def record_execution_job(self, actor, agency_id, session_id,
                             execution_id, job_ref):
        """Record one execution-engine job over a core execution
        record. Action: document_write."""
        self._guard(actor, "ext_execution_job")
        self._agency(actor, agency_id)
        execution = self._execution_in_session(
            actor, agency_id, session_id, execution_id)
        _non_empty(job_ref, "job_ref")
        with self._lock:
            self._check_ref_unique(
                [j for j in self._execution_jobs.values()
                 if j["execution_id"] == execution_id],
                "job_ref", job_ref, "execution")
            return self._create(
                self._execution_jobs, "ejb-",
                {"agency_id": agency_id, "session_id": session_id,
                 "execution_id": execution_id,
                 "execution_kind": execution["kind"],
                 "job_ref": job_ref, "executed_here": False},
                actor, "ext_execution_job")

    def record_execution_outcome(self, actor, agency_id, job_id,
                                 outcome_label, reported_exit_code=None):
        """Append one reported execution outcome to a job: the
        label verbatim and the exit code as reported (an integer;
        booleans and floats rejected, negatives accepted -- an
        exit code is a reported value, not a count).
        Action: document_write."""
        self._guard(actor, "ext_execution_outcome")
        self._scoped(actor, agency_id, self._execution_jobs, job_id,
                     "execution job")
        if outcome_label not in EXECUTION_OUTCOMES:
            raise ValidationError(
                "outcome_label must be one of %s"
                % (", ".join(EXECUTION_OUTCOMES),))
        if reported_exit_code is not None:
            if (isinstance(reported_exit_code, bool)
                    or not isinstance(reported_exit_code, int)):
                raise ValidationError(
                    "reported_exit_code must be an integer")
        with self._lock:
            return self._create(
                self._execution_outcomes, "ejo-",
                {"agency_id": agency_id, "job_id": job_id,
                 "outcome_label": outcome_label,
                 "reported_exit_code": reported_exit_code,
                 "executed_here": False},
                actor, "ext_execution_outcome")

    def execution_job_view(self, actor, agency_id, job_id):
        """A job record plus derived outcome state: the outcome
        count, the latest recorded outcome label, and its
        reported exit code. Action: agency_read."""
        view = copy.deepcopy(
            self._scoped(actor, agency_id, self._execution_jobs, job_id,
                         "execution job"))
        outcomes = self._sorted(
            [o for o in self._execution_outcomes.values()
             if o["job_id"] == job_id])
        view["outcome_count"] = len(outcomes)
        view["latest_outcome_label"] = (
            outcomes[-1]["outcome_label"] if outcomes else None)
        view["latest_reported_exit_code"] = (
            outcomes[-1]["reported_exit_code"] if outcomes else None)
        return view

    def list_execution_jobs(self, actor, agency_id, session_id):
        """List execution jobs over one core session.
        Action: agency_read."""
        self._agency(actor, agency_id)
        return copy.deepcopy(self._sorted(
            [j for j in self._execution_jobs.values()
             if j["agency_id"] == agency_id
             and j["session_id"] == session_id]))

    # -- Document generation engine (idx 490, reference) -----------------
    # Labeled reference form: a generation request names a core
    # workspace (and optionally a core session in it), and a
    # reported output is held as a CORE DOCUMENT reference (the
    # core document registry's metadata + checksum record) in the
    # request's workspace. No field can hold generated text --
    # the field does not exist -- and nothing is drafted or
    # generated here: ``generated_here`` and ``drafted_here`` are
    # False on every record.

    def record_generation_request(self, actor, agency_id, workspace_id,
                                  request_ref, session_id=None,
                                  purpose_label=None):
        """Record one document-generation request, as a labeled
        reference record. Action: document_write."""
        self._guard(actor, "ext_generation_request")
        self._agency(actor, agency_id)
        self.store.get_workspace(agency_id, workspace_id, actor)
        if session_id is not None:
            self._session_in_workspace(
                actor, agency_id, workspace_id, session_id)
        _non_empty(request_ref, "request_ref")
        if purpose_label is not None:
            _non_empty(purpose_label, "purpose_label")
        with self._lock:
            self._check_ref_unique(
                [r for r in self._generation_requests.values()
                 if r["workspace_id"] == workspace_id],
                "request_ref", request_ref, "workspace")
            return self._create(
                self._generation_requests, "gnr-",
                {"agency_id": agency_id, "workspace_id": workspace_id,
                 "session_id": session_id, "request_ref": request_ref,
                 "purpose_label": purpose_label,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "generated_here": False, "drafted_here": False},
                actor, "ext_generation_request")

    def record_generation_output(self, actor, agency_id, request_id,
                                 document_id):
        """Record one reported generation output as a core
        document reference in the request's workspace.
        Action: document_write."""
        self._guard(actor, "ext_generation_output")
        request = self._scoped(
            actor, agency_id, self._generation_requests, request_id,
            "generation request")
        document = self.store.get_document(agency_id, document_id, actor)
        if document["workspace_id"] != request["workspace_id"]:
            raise NotFoundError(
                "document not found in generation request workspace %s: %r"
                % (request["workspace_id"], document_id))
        with self._lock:
            for existing in self._generation_outputs.values():
                if (existing["request_id"] == request_id
                        and existing["document_id"] == document_id):
                    raise ValidationError(
                        "document %r is already recorded as an output "
                        "of generation request %s" % (document_id, request_id))
            return self._create(
                self._generation_outputs, "gno-",
                {"agency_id": agency_id, "request_id": request_id,
                 "document_id": document_id, "reference_stub": True,
                 "generated_here": False},
                actor, "ext_generation_output")

    def generation_request_view(self, actor, agency_id, request_id):
        """A generation request plus its derived output count and
        the recorded output document references.
        Action: agency_read."""
        view = copy.deepcopy(
            self._scoped(actor, agency_id, self._generation_requests,
                         request_id, "generation request"))
        outputs = self._sorted(
            [o for o in self._generation_outputs.values()
             if o["request_id"] == request_id])
        view["output_count"] = len(outputs)
        view["output_document_ids"] = [o["document_id"] for o in outputs]
        return view

    def list_generation_requests(self, actor, agency_id, workspace_id=None):
        """List generation requests in an agency, optionally for
        one workspace. Action: agency_read."""
        self._agency(actor, agency_id)
        records = self._in_agency(self._generation_requests, agency_id)
        if workspace_id is not None:
            records = [r for r in records
                       if r["workspace_id"] == workspace_id]
        return copy.deepcopy(self._sorted(records))

    # -- Security monitoring & platform security (idx 492, reference) ----
    # Labeled reference form (PLATFORM-LAYER.md: monitoring and
    # platform security services are the deployment platform's
    # layer): a feed is a definition record carrying
    # ``reference_transport: True``, and an observation is a
    # reported record -- the observation and severity labels
    # verbatim. Nothing is monitored, scanned, or detected here:
    # ``monitored_here`` and ``scanned_here`` are False on every
    # record, and an observation changes no core record.

    def define_monitoring_feed(self, actor, agency_id, feed_ref,
                               source_label):
        """Define one security monitoring feed, as a labeled
        reference record. Action: document_write."""
        self._guard(actor, "ext_monitoring_feed")
        self._agency(actor, agency_id)
        _non_empty(feed_ref, "feed_ref")
        _non_empty(source_label, "source_label")
        with self._lock:
            self._check_ref_unique(
                self._in_agency(self._monitoring_feeds, agency_id),
                "feed_ref", feed_ref, "agency")
            return self._create(
                self._monitoring_feeds, "mfd-",
                {"agency_id": agency_id, "feed_ref": feed_ref,
                 "source_label": source_label, "reference_stub": True,
                 "reference_transport": True, "state": _REFERENCE_STATE,
                 "monitored_here": False, "scanned_here": False},
                actor, "ext_monitoring_feed")

    def record_monitoring_observation(self, actor, agency_id, feed_id,
                                      observation_ref, observation_label,
                                      severity_label):
        """Record one reported monitoring observation, labels
        verbatim. Action: document_write."""
        self._guard(actor, "ext_monitoring_observation")
        self._scoped(actor, agency_id, self._monitoring_feeds, feed_id,
                     "monitoring feed")
        _non_empty(observation_ref, "observation_ref")
        _non_empty(observation_label, "observation_label")
        _non_empty(severity_label, "severity_label")
        with self._lock:
            self._check_ref_unique(
                [o for o in self._monitoring_observations.values()
                 if o["feed_id"] == feed_id],
                "observation_ref", observation_ref, "monitoring feed")
            return self._create(
                self._monitoring_observations, "mfo-",
                {"agency_id": agency_id, "feed_id": feed_id,
                 "observation_ref": observation_ref,
                 "observation_label": observation_label,
                 "severity_label": severity_label,
                 "reference_stub": True, "monitored_here": False},
                actor, "ext_monitoring_observation")

    def monitoring_feed_view(self, actor, agency_id, feed_id):
        """A feed record plus derived observation state: the
        observation count and counts by reported severity label.
        Action: agency_read."""
        view = copy.deepcopy(
            self._scoped(actor, agency_id, self._monitoring_feeds, feed_id,
                         "monitoring feed"))
        observations = [o for o in self._monitoring_observations.values()
                        if o["feed_id"] == feed_id]
        by_severity = {}
        for observation in observations:
            by_severity[observation["severity_label"]] = (
                by_severity.get(observation["severity_label"], 0) + 1)
        view["observation_count"] = len(observations)
        view["observations_by_severity"] = by_severity
        return view

    def list_monitoring_feeds(self, actor, agency_id):
        """List monitoring feed definitions in an agency.
        Action: agency_read."""
        self._agency(actor, agency_id)
        return copy.deepcopy(self._sorted(
            self._in_agency(self._monitoring_feeds, agency_id)))
