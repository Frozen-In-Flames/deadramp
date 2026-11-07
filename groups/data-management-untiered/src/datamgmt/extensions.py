"""Final GAPS batch extensions for the Data Management untiered set.

Clean-room, standard-library-only records/derivation extensions for
the 10 open Extended entries of this set's union spec: 6 built as
in-substrate records plus deterministic derivations over the core's
own records, and 4 shipped as labeled reference implementations.
See ``BATCH.md`` in the group directory for the per-entry
disposition and the adjudication notes.

Design, following the core's doctrines and this set's tier
discipline:

- This module is a wrapper around :class:`DataMgmtStore`; the core
  modules are untouched (byte-identical). Dataset existence,
  retention policies, and retention due state are always read
  through the core store's public API, never re-implemented.
- **Tier null binds the whole surface.** The set's forks publish
  no FedRAMP impact level, so nothing here asserts or records a
  tier, a control baseline, or an equivalence: no record shape
  carries a tier-shaped key, and the batch tests scan every record
  and view recursively for one. The forks' documented control
  claims stay where the union spec put them -- in the spec, as the
  forks' claims about themselves.
- RBAC goes through :mod:`datamgmt.access` exactly as the core
  enforces it: the extension maps each of its operations onto an
  existing core action (the core action set is fixed), checks it
  *before* any state change or id allocation for User-like actors,
  and records denied attempts on the core audit log with the
  extension action name suffixed ``:denied``. Plain-string actors
  carry identity but no role, mirroring the core convention.
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``.
- All references to people, systems, datasets, and outputs are
  opaque ``*_ref`` strings or core record ids. No record shape in
  this module can hold a payload, an identifier value, a vector
  value, or extracted content; counts that describe an external
  engine's work are stored as reported, never computed here.
- Derived values are derived at read and never stored: warehouse
  rollups, graph degrees, ABAC decision outcomes, visualization
  series. Stored records carry no derived key; tests pin that.
- The ABAC decision derivation lives at a single named seam
  (``_attributes_satisfy``): a deterministic attribute-presence
  match over recorded attribute names, in the personalization
  precedent's form. The seam is the batch's fresh negative
  control. A decision is a record about a match; enforcement
  itself is not performed here (``enforced_here`` is False), and
  recording a decision changes no core access state.
- Nothing here executes against an external system. The four
  stub-engine families ship as labeled reference implementations:
  every record they create carries ``reference_stub: True`` (file
  transfers carry ``reference_transport: True``), and no model
  runs, no content is processed, no index is built, and no file
  moves.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

VECTOR_METRICS = ("cosine", "dot_product", "euclidean")
KNOWN_VECTOR_METRICS = frozenset(VECTOR_METRICS)
PRODUCTION_KINDS = ("archive", "ediscovery", "foia")
KNOWN_PRODUCTION_KINDS = frozenset(PRODUCTION_KINDS)
DISPOSITION_DECISIONS = ("approve", "defer", "reject")
KNOWN_DISPOSITION_DECISIONS = frozenset(DISPOSITION_DECISIONS)
QUERY_KINDS = ("count_records", "count_by_field", "sum_field", "field_histogram")
KNOWN_QUERY_KINDS = frozenset(QUERY_KINDS)
CHART_KINDS = ("bar", "table", "line", "summary")
KNOWN_CHART_KINDS = frozenset(CHART_KINDS)
ABAC_EFFECTS = ("permit", "deny")
KNOWN_ABAC_EFFECTS = frozenset(ABAC_EFFECTS)
PROCESSING_KINDS = ("ocr", "classification", "deduplication")
KNOWN_PROCESSING_KINDS = frozenset(PROCESSING_KINDS)
TRANSFER_PROTOCOLS = ("sftp", "https", "as2", "managed_service")
KNOWN_TRANSFER_PROTOCOLS = frozenset(TRANSFER_PROTOCOLS)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    return value


def _nonneg_int(value, what):
    _int(value, what)
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _one_of(value, known, names, what):
    if value not in known:
        raise ValidationError("%s must be one of %s" % (what, ", ".join(names)))
    return value


def _string_list(value, what):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError("%s must be a list of non-empty strings" % (what,))
    if len(value) > 50:
        raise ValidationError("%s may hold at most 50 entries" % (what,))
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError("each entry in %s must be a non-empty string" % (what,))
        result.append(item)
    return result


class DataMgmtExtensions:
    """GAPS-batch extension surface over a core DataMgmtStore."""

    def __init__(self, store):
        self.store = store
        self._records = {}  # (kind, id) -> dict
        self._order = []  # (kind, id) in creation order
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self.store, "audit", None)
        if audit is not None:
            audit.record(actor_name(actor), action, target, details=details)

    def _guard(self, actor, core_action, audit_action, target=None):
        """Enforce a write permission, auditing a denial.

        Mirrors the core store: an actor must be present; User-like
        actors are checked against the core permission matrix before
        anything changes; plain strings carry identity only.
        """
        try:
            if actor is None:
                raise PermissionDenied(
                    "permission denied: no user supplied for %r" % (core_action,)
                )
            if hasattr(actor, "role"):
                require(actor, core_action)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", target)
            raise

    def _guard_read(self, actor, core_action, audit_action, target=None):
        """Enforce a read permission when the actor carries a role."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, core_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", target)
                raise

    def _dataset(self, dataset_id):
        """Return the core dataset record (NotFoundError if absent)."""
        return self.store.get_dataset(dataset_id)

    def _create(self, kind, prefix, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            self._audit(actor, audit_action, record_id,
                        details={"kind": kind})
            return copy.deepcopy(record)

    def _get(self, kind, record_id):
        record = self._records.get((kind, record_id))
        if record is None:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id):
        return copy.deepcopy(self._get(kind, record_id))

    def _list(self, kind, **filters):
        result = []
        for key in self._order:
            if key[0] != kind:
                continue
            record = self._records[key]
            if all(record.get(name) == value for name, value in filters.items()
                   if value is not None):
                result.append(copy.deepcopy(record))
        return result

    # -- Vector database & embedding index (definition records) --------
    # A collection here is a definition: a name, an optional core
    # dataset binding, a reported dimension and a distance-metric
    # label. No vector value exists in any shape -- there is no
    # parameter that could accept one -- and no embedding is
    # computed: embedding jobs record counts exactly as reported.

    def define_vector_collection(self, name, actor, dataset_id=None,
                                 dimension=None, metric=None):
        """Register a vector-collection definition. Action: dataset_write.

        ``dimension`` is the collection's declared dimension as
        reported by the owning platform -- a property of the
        definition, not a vector. Nothing is indexed and no
        embedding is computed (``embeddings_computed_here`` is
        False).
        """
        self._guard(actor, "dataset_write", "ext_vector_collection_define",
                    dataset_id)
        _non_empty(name, "collection name")
        if dimension is not None:
            _nonneg_int(dimension, "dimension")
            if dimension == 0:
                raise ValidationError("dimension must be positive when given")
        if metric is not None:
            _one_of(metric, KNOWN_VECTOR_METRICS, VECTOR_METRICS, "metric")
        with self._lock:
            if dataset_id is not None:
                self._dataset(dataset_id)
            return self._create(
                "vector_collection", "vcol",
                {"name": name, "dataset_id": dataset_id,
                 "dimension_reported": dimension, "metric": metric,
                 "definition_only": True,
                 "embeddings_computed_here": False},
                actor, "ext_vector_collection_define")

    def get_vector_collection(self, collection_id, actor=None):
        """Return one vector-collection definition. Action: dataset_read."""
        self._guard_read(actor, "dataset_read",
                         "ext_vector_collection_read", collection_id)
        return self._fetch("vector_collection", collection_id)

    def list_vector_collections(self, dataset_id=None, actor=None):
        """Return vector-collection definitions. Action: dataset_read."""
        self._guard_read(actor, "dataset_read",
                         "ext_vector_collection_read", dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("vector_collection", dataset_id=dataset_id)

    def record_embedding_job(self, collection_id, actor,
                             documents_reported=0, embeddings_reported=0):
        """Record an embedding job's counts as reported.

        Action: ingest_record. The counts are the owning
        platform's report, stored verbatim; this build computes
        no embedding (``embeddings_computed_here`` is False).
        """
        self._guard(actor, "ingest_record", "ext_embedding_job_record",
                    collection_id)
        _nonneg_int(documents_reported, "documents_reported")
        _nonneg_int(embeddings_reported, "embeddings_reported")
        with self._lock:
            self._get("vector_collection", collection_id)
            return self._create(
                "embedding_job", "emb",
                {"collection_id": collection_id,
                 "documents_reported": documents_reported,
                 "embeddings_reported": embeddings_reported,
                 "embeddings_computed_here": False,
                 "status": "recorded_report"},
                actor, "ext_embedding_job_record")

    def list_embedding_jobs(self, collection_id=None, actor=None):
        """Return embedding job records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_embedding_job_read",
                         collection_id)
        if collection_id is not None:
            self._get("vector_collection", collection_id)
        return self._list("embedding_job", collection_id=collection_id)

    # -- Warehouse & analytics (configuration records) -----------------
    # A warehouse here is a configuration record: a name, an
    # optional core dataset binding, and a scale label recorded
    # verbatim as the owning platform reports it -- a label, never
    # a capacity claim by this build. Query runs record counts as
    # reported; no data is held and no query executes here.

    def register_warehouse(self, name, actor, scale_label=None,
                           dataset_id=None):
        """Register a warehouse configuration record.

        Action: dataset_write. ``scale_label`` is recorded
        verbatim as reported (for example a platform's own scale
        description); it is data about the platform, not a
        capacity this build provides. No data is held here
        (``data_held_here`` is False).
        """
        self._guard(actor, "dataset_write", "ext_warehouse_register",
                    dataset_id)
        _non_empty(name, "warehouse name")
        _string_or_none(scale_label, "scale_label")
        if scale_label is not None:
            _non_empty(scale_label, "scale_label")
        with self._lock:
            if dataset_id is not None:
                self._dataset(dataset_id)
            return self._create(
                "warehouse", "wrh",
                {"name": name, "dataset_id": dataset_id,
                 "scale_label_reported": scale_label,
                 "data_held_here": False,
                 "status": "configuration_record"},
                actor, "ext_warehouse_register")

    def get_warehouse(self, warehouse_id, actor=None):
        """Return one warehouse configuration record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_warehouse_read",
                         warehouse_id)
        return self._fetch("warehouse", warehouse_id)

    def list_warehouses(self, dataset_id=None, actor=None):
        """Return warehouse configuration records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_warehouse_read",
                         dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("warehouse", dataset_id=dataset_id)

    def record_warehouse_query_run(self, warehouse_id, actor,
                                   rows_reported=0, note=None):
        """Record a warehouse query run's counts as reported.

        Action: ingest_record. The run happened on the owning
        platform; this build records the report and executes
        nothing (``executed_here`` is False).
        """
        self._guard(actor, "ingest_record", "ext_warehouse_query_run_record",
                    warehouse_id)
        _nonneg_int(rows_reported, "rows_reported")
        _string_or_none(note, "note")
        with self._lock:
            self._get("warehouse", warehouse_id)
            return self._create(
                "warehouse_query_run", "wqr",
                {"warehouse_id": warehouse_id,
                 "rows_reported": rows_reported, "note": note,
                 "executed_here": False, "data_held_here": False,
                 "status": "recorded_report"},
                actor, "ext_warehouse_query_run_record")

    def list_warehouse_query_runs(self, warehouse_id=None, actor=None):
        """Return warehouse query run records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read",
                         "ext_warehouse_query_run_read", warehouse_id)
        if warehouse_id is not None:
            self._get("warehouse", warehouse_id)
        return self._list("warehouse_query_run", warehouse_id=warehouse_id)

    def warehouse_summary(self, warehouse_id, actor=None):
        """Derived rollup for one warehouse. Action: dataset_read.

        Run counts and reported-row totals are computed at read
        from the stored run records; the stored configuration
        record carries no totals.
        """
        self._guard_read(actor, "dataset_read", "ext_warehouse_summary",
                         warehouse_id)
        with self._lock:
            warehouse = self._get("warehouse", warehouse_id)
            runs = self._list("warehouse_query_run",
                              warehouse_id=warehouse_id)
            return {
                "warehouse_id": warehouse_id,
                "name": warehouse["name"],
                "dataset_id": warehouse["dataset_id"],
                "scale_label_reported": warehouse["scale_label_reported"],
                "query_runs": len(runs),
                "rows_reported_total": sum(r["rows_reported"] for r in runs),
                "data_held_here": False,
                "derived_at_read": True,
            }

    # -- Enterprise architecture graph (node / edge records) -----------
    # The graph platform's substrate in records form: nodes are
    # opaque references with a kind label, edges are recorded
    # relationships between two registered nodes. Relationship
    # degrees are derived at read from the edge records (the
    # Research untiered precedent); the stored node record carries
    # no degree.

    def register_graph_node(self, node_ref, kind_label, actor,
                            dataset_id=None):
        """Register an architecture graph node. Action: dataset_write.

        ``node_ref`` is an opaque reference supplied by the
        embedding organization and is unique in this registry.
        """
        self._guard(actor, "dataset_write", "ext_graph_node_register",
                    dataset_id)
        _non_empty(node_ref, "node_ref")
        _non_empty(kind_label, "kind_label")
        with self._lock:
            if dataset_id is not None:
                self._dataset(dataset_id)
            for existing in self._list("graph_node"):
                if existing["node_ref"] == node_ref:
                    raise ValidationError(
                        "a graph node with ref %r already exists (%s)"
                        % (node_ref, existing["id"]))
            return self._create(
                "graph_node", "gnod",
                {"node_ref": node_ref, "kind_label": kind_label,
                 "dataset_id": dataset_id},
                actor, "ext_graph_node_register")

    def get_graph_node(self, node_id, actor=None):
        """Return one graph node record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_graph_node_read",
                         node_id)
        return self._fetch("graph_node", node_id)

    def list_graph_nodes(self, dataset_id=None, actor=None):
        """Return graph node records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_graph_node_read",
                         dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("graph_node", dataset_id=dataset_id)

    def record_graph_edge(self, source_node_id, target_node_id,
                          relation_label, actor):
        """Record a relationship between two registered nodes.

        Action: dataset_write.
        """
        self._guard(actor, "dataset_write", "ext_graph_edge_record",
                    source_node_id)
        _non_empty(relation_label, "relation_label")
        with self._lock:
            self._get("graph_node", source_node_id)
            self._get("graph_node", target_node_id)
            return self._create(
                "graph_edge", "gedg",
                {"source_node_id": source_node_id,
                 "target_node_id": target_node_id,
                 "relation_label": relation_label},
                actor, "ext_graph_edge_record")

    def list_graph_edges(self, node_id=None, actor=None):
        """Return graph edge records. Action: dataset_read.

        With ``node_id``, edges touching the node in either
        direction.
        """
        self._guard_read(actor, "dataset_read", "ext_graph_edge_read",
                         node_id)
        with self._lock:
            edges = self._list("graph_edge")
            if node_id is not None:
                self._get("graph_node", node_id)
                edges = [e for e in edges
                         if e["source_node_id"] == node_id
                         or e["target_node_id"] == node_id]
            return edges

    def graph_node_view(self, node_id, actor=None):
        """Derived view of one node. Action: dataset_read.

        In/out/total degree are computed at read from the stored
        edge records; nothing derived is written back onto the
        node record.
        """
        self._guard_read(actor, "dataset_read", "ext_graph_node_view",
                         node_id)
        with self._lock:
            node = self._get("graph_node", node_id)
            edges = self._list("graph_edge")
            out_degree = sum(1 for e in edges
                             if e["source_node_id"] == node_id)
            in_degree = sum(1 for e in edges
                            if e["target_node_id"] == node_id)
            view = dict(node)
            view["out_degree"] = out_degree
            view["in_degree"] = in_degree
            view["degree"] = out_degree + in_degree
            view["derived_at_read"] = True
            return view

    # -- Policy enforcement plane & ABAC (definitions + decisions) -----
    # Policies are definitions held as data: a core dataset
    # binding, a list of required attribute *names*, and an effect
    # label. Subject attributes are recorded as names present --
    # presence only, never values. A decision record binds a
    # policy to a subject; the decision's outcome is derived at
    # read by the seam ``_attributes_satisfy`` (a deterministic
    # presence match, in the personalization precedent's form).
    # Enforcement itself is not performed: a decision changes no
    # core access state, and every record and view carries
    # ``enforced_here: False``.

    def define_abac_policy(self, name, dataset_id, required_attributes,
                           actor, effect="permit"):
        """Register an ABAC policy definition. Action: dataset_write.

        ``required_attributes`` is a list of attribute names; the
        definition is held as data and evaluated only by the
        decision derivation below.
        """
        self._guard(actor, "dataset_write", "ext_abac_policy_define",
                    dataset_id)
        _non_empty(name, "policy name")
        _one_of(effect, KNOWN_ABAC_EFFECTS, ABAC_EFFECTS, "effect")
        required = _string_list(required_attributes, "required_attributes")
        if not required:
            raise ValidationError(
                "required_attributes must name at least one attribute")
        with self._lock:
            self._dataset(dataset_id)
            return self._create(
                "abac_policy", "abac",
                {"name": name, "dataset_id": dataset_id,
                 "required_attributes": required, "effect": effect,
                 "definition_only": True, "enforced_here": False},
                actor, "ext_abac_policy_define")

    def get_abac_policy(self, policy_id, actor=None):
        """Return one ABAC policy definition. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_abac_policy_read",
                         policy_id)
        return self._fetch("abac_policy", policy_id)

    def list_abac_policies(self, dataset_id=None, actor=None):
        """Return ABAC policy definitions. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_abac_policy_read",
                         dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("abac_policy", dataset_id=dataset_id)

    def record_subject_attributes(self, subject_ref, attributes, actor):
        """Record attribute names present for an opaque subject.

        Action: dataset_write. Presence only: the record holds
        attribute *names*; no attribute value is accepted or
        stored. Attributes accumulate across records for the
        subject (the decision derivation reads the union).
        """
        self._guard(actor, "dataset_write",
                    "ext_subject_attributes_record", subject_ref)
        _non_empty(subject_ref, "subject_ref")
        present = _string_list(attributes, "attributes")
        if not present:
            raise ValidationError("attributes must name at least one attribute")
        with self._lock:
            return self._create(
                "subject_attributes", "suba",
                {"subject_ref": subject_ref, "attributes": present},
                actor, "ext_subject_attributes_record")

    def list_subject_attributes(self, subject_ref=None, actor=None):
        """Return subject attribute records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read",
                         "ext_subject_attributes_read", subject_ref)
        return self._list("subject_attributes", subject_ref=subject_ref)

    def _subject_attribute_names(self, subject_ref):
        names = set()
        for record in self._list("subject_attributes",
                                 subject_ref=subject_ref):
            names.update(record["attributes"])
        return names

    @staticmethod
    def _attributes_satisfy(required_attributes, present_attributes):
        """True iff every required attribute name is present.

        MUTATION DRILL NOTE: this seam is the single derivation
        point for ABAC decision outcomes -- the batch's fresh
        negative control mutates it. The match is presence only:
        attribute values are never recorded, so there is nothing
        else to compare.
        """
        present = set(present_attributes)
        return all(name in present for name in required_attributes)

    def record_abac_decision(self, policy_id, subject_ref, actor):
        """Record an ABAC decision binding a policy to a subject.

        Action: access_decide. The record binds the policy and
        the subject; the outcome is *not* stored on it -- it is
        derived at read by :meth:`abac_decision_view`. Recording
        a decision grants, denies, and changes nothing in the
        core's access governance (``enforced_here`` is False).
        """
        self._guard(actor, "access_decide", "ext_abac_decision_record",
                    policy_id)
        _non_empty(subject_ref, "subject_ref")
        with self._lock:
            policy = self._get("abac_policy", policy_id)
            return self._create(
                "abac_decision", "abdec",
                {"policy_id": policy_id,
                 "dataset_id": policy["dataset_id"],
                 "subject_ref": subject_ref,
                 "enforced_here": False,
                 "status": "decision_recorded"},
                actor, "ext_abac_decision_record")

    def get_abac_decision(self, decision_id, actor=None):
        """Return one ABAC decision record. Action: access_read."""
        self._guard_read(actor, "access_read", "ext_abac_decision_read",
                         decision_id)
        return self._fetch("abac_decision", decision_id)

    def list_abac_decisions(self, policy_id=None, actor=None):
        """Return ABAC decision records. Action: access_read."""
        self._guard_read(actor, "access_read", "ext_abac_decision_read",
                         policy_id)
        if policy_id is not None:
            self._get("abac_policy", policy_id)
        return self._list("abac_decision", policy_id=policy_id)

    def abac_decision_view(self, decision_id, actor=None):
        """Derived view of an ABAC decision. Action: access_read.

        ``matched`` is computed at read by the seam
        ``_attributes_satisfy`` over the policy's required
        attribute names and the subject's recorded attribute
        names; ``missing_attributes`` names the required names
        not recorded present. The stored decision record carries
        neither.
        """
        self._guard_read(actor, "access_read", "ext_abac_decision_view",
                         decision_id)
        with self._lock:
            decision = self._get("abac_decision", decision_id)
            policy = self._get("abac_policy", decision["policy_id"])
            present = self._subject_attribute_names(decision["subject_ref"])
            required = policy["required_attributes"]
            return {
                "decision_id": decision_id,
                "policy_id": decision["policy_id"],
                "dataset_id": decision["dataset_id"],
                "subject_ref": decision["subject_ref"],
                "effect": policy["effect"],
                "required_attributes": list(required),
                "present_attributes": sorted(present),
                "missing_attributes": [n for n in required
                                       if n not in present],
                "matched": self._attributes_satisfy(required, present),
                "enforced_here": False,
                "derived_at_read": True,
            }

    # -- Archive, eDiscovery & FOIA production --------------------------
    # Production records: a production (an archive production, an
    # eDiscovery production, a FOIA production) is recorded against
    # a core dataset with its counts as reported and a checksum
    # reference. This build holds no content, so it produces no
    # production package: the record states the production as the
    # archive platform's event, recorded here (``executed_here``
    # is False).
    #
    # Disposition follows the Data Management L2 / L3-adjacent
    # batch units' adjudicated form: disposition DECISION records
    # whose eligibility is derived at record time from the core's
    # retention schedules and ``retention_due`` evaluation, plus
    # execution *reference* records that execute nothing -- every
    # disposition record carries ``reference_stub: True`` and
    # ``disposition_executed: False``, per PLATFORM-LAYER.md
    # decision 4 (disposition is the embedding organization's
    # records schedule, executed at the deployment layer).

    def record_production(self, dataset_id, kind, actor,
                          records_reported=0, checksum=None):
        """Record a production event for a dataset. Action: export.

        ``kind`` is one of archive / ediscovery / foia. Counts are
        as reported by the producing platform; no content is held
        or produced here.
        """
        self._guard(actor, "export", "ext_production_record", dataset_id)
        _one_of(kind, KNOWN_PRODUCTION_KINDS, PRODUCTION_KINDS, "kind")
        _nonneg_int(records_reported, "records_reported")
        _string_or_none(checksum, "checksum")
        with self._lock:
            self._dataset(dataset_id)
            return self._create(
                "production", "prd",
                {"dataset_id": dataset_id, "kind": kind,
                 "records_reported": records_reported,
                 "checksum": checksum,
                 "content_held": False, "executed_here": False,
                 "status": "recorded_report"},
                actor, "ext_production_record")

    def get_production(self, production_id, actor=None):
        """Return one production record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_production_read",
                         production_id)
        return self._fetch("production", production_id)

    def list_productions(self, dataset_id=None, kind=None, actor=None):
        """Return production records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_production_read",
                         dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        if kind is not None:
            _one_of(kind, KNOWN_PRODUCTION_KINDS, PRODUCTION_KINDS, "kind")
        records = self._list("production", dataset_id=dataset_id)
        if kind is not None:
            records = [r for r in records if r["kind"] == kind]
        return records

    def record_disposition_decision(self, dataset_id, decision, actor,
                                    now=None, reason=None):
        """Record a disposition decision for a dataset.

        Action: retention_write. Eligibility is derived from the
        core's ``retention_due`` evaluation at ``now`` (default:
        the current time); a dataset under legal hold or inside
        its retention window records ``eligible: False``. The
        decision record carries ``reference_stub: True`` and
        ``disposition_executed: False``: recording a decision
        deletes and archives nothing.
        """
        self._guard(actor, "retention_write", "ext_disposition_decision",
                    dataset_id)
        _one_of(decision, KNOWN_DISPOSITION_DECISIONS,
                DISPOSITION_DECISIONS, "decision")
        _string_or_none(reason, "reason")
        with self._lock:
            self._dataset(dataset_id)
            policy = self.store.retention_policy_for(dataset_id)
            if policy is None:
                raise ValidationError(
                    "no retention policy exists for dataset %r; a "
                    "disposition decision requires the core schedule "
                    "first" % (dataset_id,))
            due = self.store.retention_due(actor, now=now)
            entry = next((d for d in due
                          if d["dataset_id"] == dataset_id), None)
            return self._create(
                "disposition_decision", "ddc",
                {"dataset_id": dataset_id, "policy_id": policy["id"],
                 "disposition": policy["disposition"],
                 "decision": decision,
                 "eligible": entry is not None,
                 "age_days": entry["age_days"] if entry else None,
                 "reference_utc": entry["reference_utc"] if entry else None,
                 "legal_hold": bool(policy["legal_hold"]),
                 "reason": reason,
                 "reference_stub": True,
                 "disposition_executed": False},
                actor, "ext_disposition_decision")

    def get_disposition_decision(self, decision_id, actor=None):
        """Return one disposition decision. Action: retention_read."""
        self._guard_read(actor, "retention_read",
                         "ext_disposition_decision_read", decision_id)
        return self._fetch("disposition_decision", decision_id)

    def list_disposition_decisions(self, dataset_id=None, actor=None):
        """Return disposition decisions. Action: retention_read."""
        self._guard_read(actor, "retention_read",
                         "ext_disposition_decision_read", dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("disposition_decision", dataset_id=dataset_id)

    def record_disposition_execution_reference(self, decision_id, actor,
                                               target_ref=None):
        """Record an execution reference for an approved decision.

        Action: retention_write. A reference record only: it
        states that execution is handed to the embedding
        organization's records schedule (PLATFORM-LAYER.md
        decision 4). It executes nothing (``executed`` is False)
        and carries ``reference_stub: True``.
        """
        self._guard(actor, "retention_write",
                    "ext_disposition_execution_reference", decision_id)
        _string_or_none(target_ref, "target_ref")
        if target_ref is not None:
            _non_empty(target_ref, "target_ref")
        with self._lock:
            decision = self._get("disposition_decision", decision_id)
            if decision["decision"] != "approve":
                raise ValidationError(
                    "an execution reference requires an approved "
                    "decision; decision %r is %r"
                    % (decision_id, decision["decision"]))
            return self._create(
                "disposition_execution", "dex",
                {"decision_id": decision_id,
                 "dataset_id": decision["dataset_id"],
                 "target_ref": target_ref,
                 "reference_stub": True,
                 "status": "recorded_reference_only",
                 "executed": False, "executed_by": None},
                actor, "ext_disposition_execution_reference")

    def list_disposition_execution_references(self, decision_id=None,
                                              actor=None):
        """Return execution reference records. Action: retention_read."""
        self._guard_read(actor, "retention_read",
                         "ext_disposition_execution_read", decision_id)
        if decision_id is not None:
            self._get("disposition_decision", decision_id)
        return self._list("disposition_execution", decision_id=decision_id)

    # -- Query & visualization (definition records) ---------------------
    # A query here is a definition in text-free structure: a kind
    # from a fixed set of derivation kinds, a field *name*, and an
    # optional scalar filter -- there is no parameter that could
    # accept query text. Runs are recorded as reports of runs that
    # happened on the owning platform (counts as reported); no
    # query executes here. A visualization is a definition; its
    # view is derived at read from stored run records and renders
    # nothing.

    def define_query(self, name, dataset_id, kind, actor, field=None,
                     value_equals=None, has_filter=False):
        """Register a query definition. Action: dataset_write.

        ``kind`` is one of count_records / count_by_field /
        sum_field / field_histogram. The field-shaped kinds
        require ``field`` (a field *name*). ``has_filter`` with
        ``value_equals`` (a string, integer, boolean, or null
        scalar) restricts the defined query to records whose
        field equals the given scalar.
        """
        self._guard(actor, "dataset_write", "ext_query_define", dataset_id)
        _non_empty(name, "query name")
        _one_of(kind, KNOWN_QUERY_KINDS, QUERY_KINDS, "kind")
        if kind in ("count_by_field", "sum_field", "field_histogram"):
            _non_empty(field, "field")
        elif field is not None:
            _non_empty(field, "field")
        if not isinstance(has_filter, bool):
            raise ValidationError("has_filter must be a bool")
        if has_filter and not (
                value_equals is None
                or isinstance(value_equals, (str, int, bool))):
            raise ValidationError(
                "value_equals must be a scalar (string, integer, "
                "boolean, or null)")
        with self._lock:
            self._dataset(dataset_id)
            return self._create(
                "query", "qry",
                {"name": name, "dataset_id": dataset_id, "kind": kind,
                 "field": field, "has_filter": has_filter,
                 "value_equals": value_equals if has_filter else None,
                 "definition_only": True, "executed_here": False},
                actor, "ext_query_define")

    def get_query(self, query_id, actor=None):
        """Return one query definition. Action: quality_read."""
        self._guard_read(actor, "quality_read", "ext_query_read", query_id)
        return self._fetch("query", query_id)

    def list_queries(self, dataset_id=None, actor=None):
        """Return query definitions. Action: quality_read."""
        self._guard_read(actor, "quality_read", "ext_query_read", dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("query", dataset_id=dataset_id)

    def record_query_run(self, query_id, actor, records_scanned_reported=0,
                         records_matched_reported=0):
        """Record a query run's counts as reported.

        Action: quality_run. The run happened on the owning
        platform; this build records the report and executes no
        query (``executed_here`` is False).
        """
        self._guard(actor, "quality_run", "ext_query_run_record", query_id)
        _nonneg_int(records_scanned_reported, "records_scanned_reported")
        _nonneg_int(records_matched_reported, "records_matched_reported")
        with self._lock:
            query = self._get("query", query_id)
            return self._create(
                "query_run", "qrs",
                {"query_id": query_id, "dataset_id": query["dataset_id"],
                 "kind": query["kind"],
                 "records_scanned_reported": records_scanned_reported,
                 "records_matched_reported": records_matched_reported,
                 "executed_here": False, "status": "recorded_report"},
                actor, "ext_query_run_record")

    def list_query_runs(self, query_id=None, actor=None):
        """Return query run records. Action: quality_read."""
        self._guard_read(actor, "quality_read", "ext_query_run_read",
                         query_id)
        if query_id is not None:
            self._get("query", query_id)
        return self._list("query_run", query_id=query_id)

    def define_visualization(self, name, query_id, chart_kind, actor):
        """Register a visualization definition over a query.

        Action: dataset_write. A definition only: nothing is
        rendered or served (``rendered_here`` is False).
        """
        self._guard(actor, "dataset_write", "ext_visualization_define",
                    query_id)
        _non_empty(name, "visualization name")
        _one_of(chart_kind, KNOWN_CHART_KINDS, CHART_KINDS, "chart_kind")
        with self._lock:
            self._get("query", query_id)
            return self._create(
                "visualization", "viz",
                {"name": name, "query_id": query_id,
                 "chart_kind": chart_kind, "definition_only": True,
                 "rendered_here": False},
                actor, "ext_visualization_define")

    def get_visualization(self, visualization_id, actor=None):
        """Return one visualization definition. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_visualization_read",
                         visualization_id)
        return self._fetch("visualization", visualization_id)

    def list_visualizations(self, query_id=None, actor=None):
        """Return visualization definitions. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_visualization_read",
                         query_id)
        if query_id is not None:
            self._get("query", query_id)
        return self._list("visualization", query_id=query_id)

    def visualization_view(self, visualization_id, actor=None):
        """Derived view of a visualization. Action: dataset_read.

        The series is the latest stored query-run *report* for
        the visualization's query, or None when no run has been
        recorded. No query is executed and nothing is rendered
        here (``rendered_here`` is False).
        """
        self._guard_read(actor, "dataset_read", "ext_visualization_view",
                         visualization_id)
        with self._lock:
            viz = self._get("visualization", visualization_id)
            runs = self._list("query_run", query_id=viz["query_id"])
            latest = runs[-1] if runs else None
            return {
                "visualization_id": visualization_id,
                "query_id": viz["query_id"],
                "chart_kind": viz["chart_kind"],
                "series": (
                    {"records_scanned_reported":
                     latest["records_scanned_reported"],
                     "records_matched_reported":
                     latest["records_matched_reported"]}
                    if latest else None),
                "latest_run_id": latest["id"] if latest else None,
                "runs_available": len(runs),
                "derived_from": (
                    "stored_query_run_reports" if latest else "no_runs"),
                "rendered_here": False,
                "executes_query": False,
            }

    # -- Stub-engine families: labeled reference implementations -------
    # Each surface below registers records about an engine the
    # build does not contain. Every record carries
    # ``reference_stub: True`` (file transfers:
    # ``reference_transport: True``) and a status of
    # ``recorded_reference_only``; run-shaped records state that
    # nothing executed here. This follows the house precedent for
    # stub engines (DECISION.md): records only, never execution,
    # and never a claim that an external system was touched.

    # AI/ML engines. This build computes nothing learned: model
    # records are declarations about models an external platform
    # contains, and run records hold outcomes as reported with
    # outputs referenced by opaque ref only.
    def register_model(self, name, actor, dataset_id=None, technique=None):
        """Register an AI/ML model record. Action: dataset_write.

        A declaration record about a model an external platform
        contains; this build trains and runs no model
        (``method`` is ``recorded_declaration_only``).
        """
        self._guard(actor, "dataset_write", "ext_model_register",
                    dataset_id)
        _non_empty(name, "model name")
        _string_or_none(technique, "technique")
        if technique is not None:
            _non_empty(technique, "technique")
        with self._lock:
            if dataset_id is not None:
                self._dataset(dataset_id)
            return self._create(
                "model", "mdl",
                {"name": name, "dataset_id": dataset_id,
                 "technique": technique, "reference_stub": True,
                 "status": "recorded_reference_only",
                 "method": "recorded_declaration_only",
                 "trained_here": False, "inference_here": False},
                actor, "ext_model_register")

    def get_model(self, model_id, actor=None):
        """Return one model record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_model_read", model_id)
        return self._fetch("model", model_id)

    def list_models(self, dataset_id=None, actor=None):
        """Return model records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_model_read", dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("model", dataset_id=dataset_id)

    def record_model_run(self, model_id, outcome, actor, output_ref=None):
        """Record a model run's outcome as reported.

        Action: dataset_write. The outcome is the owning
        platform's report, stored verbatim; any output is an
        opaque reference -- no output content enters this build
        and no inference runs here (``inference_here`` is False).
        """
        self._guard(actor, "dataset_write", "ext_model_run_record",
                    model_id)
        _non_empty(outcome, "outcome")
        _string_or_none(output_ref, "output_ref")
        if output_ref is not None:
            _non_empty(output_ref, "output_ref")
        with self._lock:
            self._get("model", model_id)
            return self._create(
                "model_run", "mrun",
                {"model_id": model_id, "outcome": outcome,
                 "output_ref": output_ref, "reference_stub": True,
                 "inference_here": False},
                actor, "ext_model_run_record")

    def list_model_runs(self, model_id=None, actor=None):
        """Return model run records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_model_run_read",
                         model_id)
        if model_id is not None:
            self._get("model", model_id)
        return self._list("model_run", model_id=model_id)

    # Document processing engines (OCR, classification,
    # deduplication). Jobs and outputs are records: an output is
    # an opaque reference with counts as reported -- no extracted
    # text or classified content exists in any shape here.
    def register_processing_job(self, kind, dataset_id, actor,
                                ingestion_id=None):
        """Register a document processing job. Action: dataset_write.

        ``kind`` is one of ocr / classification / deduplication.
        The job is a record about processing an external engine
        performs; nothing is processed here (``processed_here``
        is False, ``outputs_held`` is False).
        """
        self._guard(actor, "dataset_write", "ext_processing_job_register",
                    dataset_id)
        _one_of(kind, KNOWN_PROCESSING_KINDS, PROCESSING_KINDS, "kind")
        with self._lock:
            self._dataset(dataset_id)
            if ingestion_id is not None:
                ingestion = self.store.get_ingestion(ingestion_id)
                if ingestion["dataset_id"] != dataset_id:
                    raise ValidationError(
                        "ingestion %r does not belong to dataset %r"
                        % (ingestion_id, dataset_id))
            return self._create(
                "processing_job", "prc",
                {"kind": kind, "dataset_id": dataset_id,
                 "ingestion_id": ingestion_id,
                 "reference_stub": True,
                 "status": "recorded_reference_only",
                 "processed_here": False, "outputs_held": False},
                actor, "ext_processing_job_register")

    def get_processing_job(self, job_id, actor=None):
        """Return one processing job record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_processing_job_read",
                         job_id)
        return self._fetch("processing_job", job_id)

    def list_processing_jobs(self, dataset_id=None, actor=None):
        """Return processing job records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_processing_job_read",
                         dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("processing_job", dataset_id=dataset_id)

    def record_processing_output(self, job_id, output_ref, actor,
                                 records_reported=None):
        """Record an output reference for a processing job.

        Action: ingest_record. Only the opaque reference and a
        reported count are held; the output content itself never
        enters this build (``content_held`` is False).
        """
        self._guard(actor, "ingest_record", "ext_processing_output_record",
                    job_id)
        _non_empty(output_ref, "output_ref")
        if records_reported is not None:
            _nonneg_int(records_reported, "records_reported")
        with self._lock:
            self._get("processing_job", job_id)
            return self._create(
                "processing_output", "pro",
                {"job_id": job_id, "output_ref": output_ref,
                 "records_reported": records_reported,
                 "reference_stub": True, "content_held": False,
                 "processed_here": False},
                actor, "ext_processing_output_record")

    def list_processing_outputs(self, job_id=None, actor=None):
        """Return processing output records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_processing_output_read",
                         job_id)
        if job_id is not None:
            self._get("processing_job", job_id)
        return self._list("processing_output", job_id=job_id)

    # Managed file transfer transport.
    def record_file_transfer(self, dataset_id, source_id, actor,
                             record_count=0, checksum=None,
                             protocol="sftp"):
        """Record a managed file transfer. Action: ingest_record.

        Transfers are ingestion-shaped records. The record
        carries ``reference_transport: True``: it states that a
        transfer was reported over the named protocol; no file
        moves through this build (``moved_here`` and
        ``transferred_here`` are False).
        """
        self._guard(actor, "ingest_record", "ext_file_transfer_record",
                    dataset_id)
        _one_of(protocol, KNOWN_TRANSFER_PROTOCOLS,
                TRANSFER_PROTOCOLS, "protocol")
        _nonneg_int(record_count, "record_count")
        _string_or_none(checksum, "checksum")
        with self._lock:
            self._dataset(dataset_id)
            self.store.get_source(source_id)
            return self._create(
                "file_transfer", "trf",
                {"dataset_id": dataset_id, "source_id": source_id,
                 "protocol": protocol, "record_count": record_count,
                 "checksum": checksum,
                 "reference_transport": True,
                 "status": "recorded_reference_only",
                 "moved_here": False, "transferred_here": False},
                actor, "ext_file_transfer_record")

    def get_file_transfer(self, transfer_id, actor=None):
        """Return one file transfer record. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_file_transfer_read",
                         transfer_id)
        return self._fetch("file_transfer", transfer_id)

    def list_file_transfers(self, dataset_id=None, actor=None):
        """Return file transfer records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_file_transfer_read",
                         dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("file_transfer", dataset_id=dataset_id)

    # Search indexing engine. Definitions and reported snapshots
    # only: no index is built here, and the core's literal
    # substring search over registry metadata remains the only
    # search that runs.
    def define_search_index(self, name, actor, dataset_id=None):
        """Register a search-index definition. Action: dataset_write.

        A definition record only: no index is built, populated, or
        queried through this surface (``index_built_here`` is
        False).
        """
        self._guard(actor, "dataset_write", "ext_search_index_define",
                    dataset_id)
        _non_empty(name, "search index name")
        with self._lock:
            if dataset_id is not None:
                self._dataset(dataset_id)
            return self._create(
                "search_index", "idx",
                {"name": name, "dataset_id": dataset_id,
                 "reference_stub": True,
                 "status": "recorded_reference_only",
                 "index_built_here": False},
                actor, "ext_search_index_define")

    def get_search_index(self, index_id, actor=None):
        """Return one search-index definition. Action: catalog_read."""
        self._guard_read(actor, "catalog_read", "ext_search_index_read",
                         index_id)
        return self._fetch("search_index", index_id)

    def list_search_indexes(self, dataset_id=None, actor=None):
        """Return search-index definitions. Action: catalog_read."""
        self._guard_read(actor, "catalog_read", "ext_search_index_read",
                         dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("search_index", dataset_id=dataset_id)

    def record_index_snapshot(self, index_id, documents_reported, actor):
        """Record an index-size snapshot as reported externally.

        Action: ingest_record.
        """
        self._guard(actor, "ingest_record", "ext_index_snapshot_record",
                    index_id)
        _nonneg_int(documents_reported, "documents_reported")
        with self._lock:
            self._get("search_index", index_id)
            return self._create(
                "index_snapshot", "isn",
                {"index_id": index_id,
                 "documents_reported": documents_reported,
                 "reference_stub": True, "indexed_here": False,
                 "index_built_here": False},
                actor, "ext_index_snapshot_record")

    def list_index_snapshots(self, index_id=None, actor=None):
        """Return index snapshot records. Action: catalog_read."""
        self._guard_read(actor, "catalog_read", "ext_index_snapshot_read",
                         index_id)
        if index_id is not None:
            self._get("search_index", index_id)
        return self._list("index_snapshot", index_id=index_id)
