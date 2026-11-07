"""Final GAPS batch extensions for the Library Systems L1 build.

Records surfaces for the group's nine Extended functions, built over
the untouched core substrate (catalogue items, holdings, loans,
holds, integrations, workflows). Everything here is records:

- Discovery queries hold a SHA-256 digest of the query and opaque
  result references only. There is no parameter anywhere in this
  module that can accept query text, so raw query text cannot exist
  in a record (the Legal & Policy sandbox discipline).
- Preservation, knowledge, course-list, and accessibility records
  hold metadata, opaque references, and validated digests only;
  content bytes are never held (``bytes_held: False`` where a record
  speaks about content at all).
- Research activities, automation execution, and integration
  transport ship as labeled reference implementations: request and
  reported-outcome records only, nothing executes, connects, or
  transmits (``reference_stub: True`` / ``reference_transport:
  True`` on the records that carry those boundaries).
- No score, rank, or recommendation is computed anywhere; no field
  can hold money (the group has no money shape, per its spec); a
  patron is an opaque ``patron_ref`` and no field can hold a real
  name or contact detail.
"""
import re
from datetime import datetime, timezone

from .access import User, require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _require_ref(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _require_digest(value, field):
    if not isinstance(value, str) or not _DIGEST_RE.match(value):
        raise ValidationError("%s must be a 64-char lowercase hex SHA-256 digest" % field)
    return value


def _require_ref_list(value, field):
    if not isinstance(value, list) or any(
            not isinstance(v, str) or not v.strip() for v in value):
        raise ValidationError("%s must be a list of non-empty strings" % field)
    return list(value)


class LibraryExtensions:
    """GAPS-batch extension surface wrapping a LibrarySysStore."""

    def __init__(self, store):
        self.store = store
        self._queries = {}
        self._deliveries = {}
        self._preservation = {}
        self._fixity = {}
        self._course_lists = {}
        self._research = {}
        self._research_outcomes = {}
        self._knowledge = {}
        self._knowledge_links = {}
        self._access_requests = {}
        self._access_outcomes = {}
        self._automation_requests = {}
        self._automation_outcomes = {}
        self._transport_receipts = {}
        self._counters = {}

    # -- internals ------------------------------------------------------
    def _next_id(self, prefix):
        n = self._counters.get(prefix, 0) + 1
        self._counters[prefix] = n
        return "%s-%d" % (prefix, n)

    def _audit(self, actor, action, target):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target, None)

    def _gate(self, lib_id, actor, action):
        """Membership gate (via the core) plus a write permission.

        Denied write attempts are audited with a ``:denied`` suffix,
        matching the house pattern; failed operations consume no id.
        """
        self.store.get_library(lib_id, actor)
        if isinstance(actor, User):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit(actor, "ext_%s:denied" % action, lib_id)
                raise

    def _read_gate(self, lib_id, actor):
        self.store.get_library(lib_id, actor)

    def _get(self, table, lib_id, obj_id, what):
        obj = table.get(obj_id)
        if obj is None or obj["lib_id"] != lib_id:
            raise NotFoundError("%s not found: %r" % (what, obj_id))
        return obj

    # -- 991: discovery & delivery --------------------------------------
    def record_discovery_query(self, lib_id, query_digest, result_refs, actor):
        """Record one discovery query: digest + result refs only.

        The signature deliberately has no query-text parameter, so
        passing ``query_text=`` raises TypeError and raw query text
        can never be stored.
        """
        self._gate(lib_id, actor, "catalogue_write")
        _require_digest(query_digest, "query_digest")
        refs = _require_ref_list(result_refs, "result_refs")
        rec = {"id": self._next_id("dsc"), "lib_id": lib_id,
               "query_digest": query_digest, "result_refs": refs,
               "searched_here": False,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._queries[rec["id"]] = rec
        self._audit(actor, "ext_discovery_query_record", rec["id"])
        return self._query_view(rec)

    def _query_view(self, rec):
        view = dict(rec, result_refs=list(rec["result_refs"]))
        view["result_count"] = self._discovery_result_count(rec["result_refs"])
        return view

    def _discovery_result_count(self, result_refs):
        """Derivation seam: a query's result count is derived at
        read from its recorded result references, never stored."""
        return len(result_refs)

    def get_discovery_query(self, lib_id, query_id, actor):
        self._read_gate(lib_id, actor)
        return self._query_view(self._get(self._queries, lib_id, query_id, "discovery query"))

    def list_discovery_queries(self, lib_id, actor):
        self._read_gate(lib_id, actor)
        return [self._query_view(q) for q in self._queries.values()
                if q["lib_id"] == lib_id]

    def record_delivery_report(self, lib_id, query_id, item_id,
                               reported_outcome, actor):
        """A reported delivery outcome bound to a query and an item.

        Delivery itself happens outside this build; the report is
        recorded verbatim and the core item is never modified.
        """
        self._gate(lib_id, actor, "circulation_write")
        self._get(self._queries, lib_id, query_id, "discovery query")
        self.store.get_item(lib_id, item_id, actor)
        _require_ref(reported_outcome, "reported_outcome")
        rec = {"id": self._next_id("dlv"), "lib_id": lib_id,
               "query_id": query_id, "item_id": item_id,
               "reported_outcome": reported_outcome,
               "delivered_here": False,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._deliveries[rec["id"]] = rec
        self._audit(actor, "ext_delivery_report_record", rec["id"])
        return dict(rec)

    def list_delivery_reports(self, lib_id, actor, query_id=None):
        self._read_gate(lib_id, actor)
        return [dict(d) for d in self._deliveries.values()
                if d["lib_id"] == lib_id
                and (query_id is None or d["query_id"] == query_id)]

    # -- 992: digital preservation --------------------------------------
    def register_preservation_record(self, lib_id, item_id, preservation_ref,
                                     content_digest, actor):
        """Preservation metadata for a catalogue item: the record
        holds an opaque ref and a validated digest; the bytes
        themselves are never held here."""
        self._gate(lib_id, actor, "registry_write")
        self.store.get_item(lib_id, item_id, actor)
        _require_ref(preservation_ref, "preservation_ref")
        _require_digest(content_digest, "content_digest")
        if any(p["lib_id"] == lib_id and p["preservation_ref"] == preservation_ref
               for p in self._preservation.values()):
            raise ValidationError(
                "duplicate preservation_ref in library: %r" % (preservation_ref,))
        rec = {"id": self._next_id("prv"), "lib_id": lib_id,
               "item_id": item_id, "preservation_ref": preservation_ref,
               "content_digest": content_digest, "bytes_held": False,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._preservation[rec["id"]] = rec
        self._audit(actor, "ext_preservation_register", rec["id"])
        return dict(rec)

    def record_fixity_report(self, lib_id, preservation_id, reported_result,
                             actor):
        """A fixity check result, recorded verbatim as reported.
        This build computes no checksum over content it does not
        hold; the reported result is the record."""
        self._gate(lib_id, actor, "registry_write")
        self._get(self._preservation, lib_id, preservation_id,
                  "preservation record")
        _require_ref(reported_result, "reported_result")
        rec = {"id": self._next_id("fix"), "lib_id": lib_id,
               "preservation_id": preservation_id,
               "reported_result": reported_result, "verified_here": False,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._fixity[rec["id"]] = rec
        self._audit(actor, "ext_fixity_report_record", rec["id"])
        return dict(rec)

    def list_preservation_records(self, lib_id, actor):
        self._read_gate(lib_id, actor)
        return [dict(p) for p in self._preservation.values()
                if p["lib_id"] == lib_id]

    def list_fixity_reports(self, lib_id, actor, preservation_id=None):
        self._read_gate(lib_id, actor)
        return [dict(f) for f in self._fixity.values()
                if f["lib_id"] == lib_id
                and (preservation_id is None
                     or f["preservation_id"] == preservation_id)]

    # -- 993: course resource lists --------------------------------------
    def create_course_list(self, lib_id, list_ref, label, actor):
        self._gate(lib_id, actor, "catalogue_write")
        _require_ref(list_ref, "list_ref"); _require_ref(label, "label")
        if any(c["lib_id"] == lib_id and c["list_ref"] == list_ref
               for c in self._course_lists.values()):
            raise ValidationError("duplicate list_ref in library: %r" % (list_ref,))
        rec = {"id": self._next_id("crs"), "lib_id": lib_id,
               "list_ref": list_ref, "label": label, "entries": [],
               "created_by": actor_name(actor), "created_utc": _now()}
        self._course_lists[rec["id"]] = rec
        self._audit(actor, "ext_course_list_create", rec["id"])
        return self._course_list_view(rec)

    def _check_course_entry_absent(self, entries, item_id):
        """Guard seam (the batch's fresh negative control): an item
        may appear at most once on a course list."""
        if item_id in entries:
            raise ValidationError(
                "item already on course list: %r" % (item_id,))

    def add_course_list_entry(self, lib_id, list_id, item_id, actor):
        self._gate(lib_id, actor, "catalogue_write")
        lst = self._get(self._course_lists, lib_id, list_id, "course list")
        self.store.get_item(lib_id, item_id, actor)
        self._check_course_entry_absent(lst["entries"], item_id)
        lst["entries"].append(item_id)
        self._audit(actor, "ext_course_list_entry_add", list_id)
        return self._course_list_view(lst)

    def _course_list_view(self, rec):
        view = dict(rec, entries=list(rec["entries"]))
        view["entry_count"] = len(rec["entries"])
        return view

    def get_course_list(self, lib_id, list_id, actor):
        self._read_gate(lib_id, actor)
        return self._course_list_view(
            self._get(self._course_lists, lib_id, list_id, "course list"))

    def list_course_lists(self, lib_id, actor):
        self._read_gate(lib_id, actor)
        return [self._course_list_view(c) for c in self._course_lists.values()
                if c["lib_id"] == lib_id]

    # -- 994: research activities platform (reference) -------------------
    def register_research_activity(self, lib_id, activity_ref, label, actor):
        self._gate(lib_id, actor, "registry_write")
        _require_ref(activity_ref, "activity_ref"); _require_ref(label, "label")
        if any(r["lib_id"] == lib_id and r["activity_ref"] == activity_ref
               for r in self._research.values()):
            raise ValidationError(
                "duplicate activity_ref in library: %r" % (activity_ref,))
        rec = {"id": self._next_id("rsa"), "lib_id": lib_id,
               "activity_ref": activity_ref, "label": label,
               "reference_stub": True, "platform_operated_here": False,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._research[rec["id"]] = rec
        self._audit(actor, "ext_research_activity_register", rec["id"])
        return dict(rec)

    def record_research_outcome(self, lib_id, activity_id, reported_outcome,
                                actor):
        self._gate(lib_id, actor, "registry_write")
        self._get(self._research, lib_id, activity_id, "research activity")
        _require_ref(reported_outcome, "reported_outcome")
        rec = {"id": self._next_id("rso"), "lib_id": lib_id,
               "activity_id": activity_id,
               "reported_outcome": reported_outcome,
               "reference_stub": True,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._research_outcomes[rec["id"]] = rec
        self._audit(actor, "ext_research_outcome_record", rec["id"])
        return dict(rec)

    def list_research_activities(self, lib_id, actor):
        self._read_gate(lib_id, actor)
        return [dict(r) for r in self._research.values()
                if r["lib_id"] == lib_id]

    # -- 995: knowledge management ---------------------------------------
    def create_knowledge_record(self, lib_id, knowledge_ref, title, actor):
        self._gate(lib_id, actor, "registry_write")
        _require_ref(knowledge_ref, "knowledge_ref"); _require_ref(title, "title")
        if any(k["lib_id"] == lib_id and k["knowledge_ref"] == knowledge_ref
               for k in self._knowledge.values()):
            raise ValidationError(
                "duplicate knowledge_ref in library: %r" % (knowledge_ref,))
        rec = {"id": self._next_id("knw"), "lib_id": lib_id,
               "knowledge_ref": knowledge_ref, "title": title,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._knowledge[rec["id"]] = rec
        self._audit(actor, "ext_knowledge_create", rec["id"])
        return self._knowledge_view(rec)

    def link_knowledge_record(self, lib_id, knowledge_id, item_id, actor):
        """Link a knowledge record to a core catalogue item. The
        link is this build's own assertion, recorded as such."""
        self._gate(lib_id, actor, "registry_write")
        self._get(self._knowledge, lib_id, knowledge_id, "knowledge record")
        self.store.get_item(lib_id, item_id, actor)
        if any(l["lib_id"] == lib_id and l["knowledge_id"] == knowledge_id
               and l["item_id"] == item_id
               for l in self._knowledge_links.values()):
            raise ValidationError("duplicate knowledge link")
        rec = {"id": self._next_id("knl"), "lib_id": lib_id,
               "knowledge_id": knowledge_id, "item_id": item_id,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._knowledge_links[rec["id"]] = rec
        self._audit(actor, "ext_knowledge_link", rec["id"])
        return dict(rec)

    def _knowledge_view(self, rec):
        view = dict(rec)
        view["link_count"] = sum(
            1 for l in self._knowledge_links.values()
            if l["knowledge_id"] == rec["id"])
        return view

    def get_knowledge_record(self, lib_id, knowledge_id, actor):
        self._read_gate(lib_id, actor)
        return self._knowledge_view(
            self._get(self._knowledge, lib_id, knowledge_id,
                      "knowledge record"))

    def list_knowledge_records(self, lib_id, actor):
        self._read_gate(lib_id, actor)
        return [self._knowledge_view(k) for k in self._knowledge.values()
                if k["lib_id"] == lib_id]

    # -- 996: accessible delivery & rendering (reference) -----------------
    def record_accessibility_request(self, lib_id, item_id, requested_format,
                                     patron_ref, actor):
        """An accessibility request against a catalogue item. The
        rendering and delivery themselves are a delivery layer this
        build does not perform; the request is the record."""
        self._gate(lib_id, actor, "circulation_write")
        self.store.get_item(lib_id, item_id, actor)
        _require_ref(requested_format, "requested_format")
        _require_ref(patron_ref, "patron_ref")
        rec = {"id": self._next_id("acp"), "lib_id": lib_id,
               "item_id": item_id, "requested_format": requested_format,
               "patron_ref": patron_ref, "reference_stub": True,
               "rendered_here": False, "delivered_here": False,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._access_requests[rec["id"]] = rec
        self._audit(actor, "ext_accessibility_request_record", rec["id"])
        return dict(rec)

    def record_accessibility_outcome(self, lib_id, request_id,
                                     reported_outcome, actor):
        self._gate(lib_id, actor, "circulation_write")
        self._get(self._access_requests, lib_id, request_id,
                  "accessibility request")
        _require_ref(reported_outcome, "reported_outcome")
        rec = {"id": self._next_id("aco"), "lib_id": lib_id,
               "request_id": request_id,
               "reported_outcome": reported_outcome,
               "reference_stub": True,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._access_outcomes[rec["id"]] = rec
        self._audit(actor, "ext_accessibility_outcome_record", rec["id"])
        return dict(rec)

    def list_accessibility_requests(self, lib_id, actor):
        self._read_gate(lib_id, actor)
        return [dict(r) for r in self._access_requests.values()
                if r["lib_id"] == lib_id]

    # -- 997: automation engine (reference) --------------------------------
    def record_automation_request(self, lib_id, workflow_id, actor):
        """An execution request against a core workflow definition.
        The core registry never executes and neither does this
        surface: the request is a record, pinned to leave the core
        workflow record untouched."""
        self._gate(lib_id, actor, "registry_write")
        workflows = {w["id"]: w for w in self.store.list_workflows(lib_id, actor)}
        if workflow_id not in workflows:
            raise NotFoundError("workflow not found: %r" % (workflow_id,))
        rec = {"id": self._next_id("aur"), "lib_id": lib_id,
               "workflow_id": workflow_id, "reference_stub": True,
               "executed_here": False,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._automation_requests[rec["id"]] = rec
        self._audit(actor, "ext_automation_request_record", rec["id"])
        return dict(rec)

    def record_automation_outcome(self, lib_id, request_id, reported_outcome,
                                  actor):
        self._gate(lib_id, actor, "registry_write")
        self._get(self._automation_requests, lib_id, request_id,
                  "automation request")
        _require_ref(reported_outcome, "reported_outcome")
        rec = {"id": self._next_id("auo"), "lib_id": lib_id,
               "request_id": request_id,
               "reported_outcome": reported_outcome,
               "reference_stub": True,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._automation_outcomes[rec["id"]] = rec
        self._audit(actor, "ext_automation_outcome_record", rec["id"])
        return dict(rec)

    def list_automation_requests(self, lib_id, actor):
        self._read_gate(lib_id, actor)
        return [dict(r) for r in self._automation_requests.values()
                if r["lib_id"] == lib_id]

    # -- 998: integration transport (reference) -----------------------------
    def record_transport_receipt(self, lib_id, integration_id,
                                 reported_outcome, actor):
        """A transport receipt bound to a core integration record.
        The interface transports themselves connect elsewhere; this
        receipt records a reported outcome and transmits nothing."""
        self._gate(lib_id, actor, "registry_write")
        integrations = {i["id"]: i
                        for i in self.store.list_integrations(lib_id, actor)}
        if integration_id not in integrations:
            raise NotFoundError("integration not found: %r" % (integration_id,))
        _require_ref(reported_outcome, "reported_outcome")
        rec = {"id": self._next_id("trn"), "lib_id": lib_id,
               "integration_id": integration_id,
               "reported_outcome": reported_outcome,
               "reference_transport": True, "transmitted_here": False,
               "connected_here": False,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._transport_receipts[rec["id"]] = rec
        self._audit(actor, "ext_transport_receipt_record", rec["id"])
        return dict(rec)

    def list_transport_receipts(self, lib_id, actor, integration_id=None):
        self._read_gate(lib_id, actor)
        return [dict(t) for t in self._transport_receipts.values()
                if t["lib_id"] == lib_id
                and (integration_id is None
                     or t["integration_id"] == integration_id)]

    # -- summary (deterministic counts, derived at read) ---------------------
    def extension_summary(self, lib_id, actor):
        self._read_gate(lib_id, actor)
        def count(table):
            return sum(1 for r in table.values() if r["lib_id"] == lib_id)
        return {
            "lib_id": lib_id,
            "discovery_query_count": count(self._queries),
            "delivery_report_count": count(self._deliveries),
            "preservation_record_count": count(self._preservation),
            "fixity_report_count": count(self._fixity),
            "course_list_count": count(self._course_lists),
            "course_entry_count": sum(
                len(c["entries"]) for c in self._course_lists.values()
                if c["lib_id"] == lib_id),
            "research_activity_count": count(self._research),
            "research_outcome_count": count(self._research_outcomes),
            "knowledge_record_count": count(self._knowledge),
            "knowledge_link_count": count(self._knowledge_links),
            "accessibility_request_count": count(self._access_requests),
            "accessibility_outcome_count": count(self._access_outcomes),
            "automation_request_count": count(self._automation_requests),
            "automation_outcome_count": count(self._automation_outcomes),
            "transport_receipt_count": count(self._transport_receipts),
        }
