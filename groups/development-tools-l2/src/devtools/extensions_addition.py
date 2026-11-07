"""Final GAPS batch additions for the Development Tools L2 build.

Second batch unit in this group directory: clean-room,
standard-library-only records extensions for the 2 open entries
of the GAPS.md section "Remainder Addition -- Development Tools
L2 (+4 forks)" (inventory idx 578-579; see ``BATCH-ADDITION.md``
in the group directory for the per-entry disposition). The first
batch unit's module is ``extensions.py``; this module is separate
and every existing module, that one included, is untouched and
byte-identical. This module wraps a
:class:`~devtools.store.DevToolsStore` exactly as the first unit
does: extension records live in this object, core records are
only read (to bind extension records to real projects and
environments), and mutations append to the core audit log under
this unit's own ``exta_`` action prefix (distinct from the first
unit's ``ext_``).

Honesty of form, per the batch brief and this group's grammar --
definitions held as data plus outcomes recorded as reported is
the built form; a pointer at an external engine is the reference
form; nothing here executes:

- **No-code / low-code application development platform:
  visual application builder & runtime** (idx 578, built as
  drafted) lands as application *definition* records plus
  publication records reported by the external platform. A
  definition holds its components as data -- each an opaque
  ``component_ref`` under a recorded kind label -- and is
  versioned on revision; the definition is inert data, never
  interpreted. The builder surface that produces definitions
  and the runtime that would execute them are stated absent on
  every record (``built_here: False``, ``run_here: False``,
  ``executed_here: False``, ``rendered_here: False``); no
  application is built or run anywhere in this build, which is
  exactly the bound the group's ADDENDUM (gap 16) records. A
  publication record snapshots the definition revision it
  reports against and stores the platform's reported status
  verbatim. The application view (current revision, component
  count, publication count, latest reported status) is derived
  at read and stored nowhere. The same definitions-as-data form
  was built for this substance at Operations Management L2
  (application definitions, ``built_here: False``), CMS
  untiered (definition records, ``executed_here: False`` /
  ``rendered_here: False``), and GRC L3 (configuration
  definitions, same two labels) -- and it is this group's own
  founding grammar (pipeline definitions plus reported runs;
  release plans plus reported stages).
- **Compliance documentation & SSP generation tooling**
  (idx 579, reference as drafted) ships as a labeled reference
  implementation: generation reference records naming the
  target document, the framework / control-documentation
  source, and the system by opaque reference only, plus
  outcome records whose status labels are recorded verbatim as
  reported by the external tooling. No document content is
  accepted or held and nothing is generated
  (``generated_here: False``, ``document_held_here: False``;
  every record carries ``reference_stub: True`` and status
  ``recorded_reference_only``). The GRC groups built package
  generation as manifest assembly / a derived manifest view
  because the GRC substrate itself holds the records a package
  is assembled from (controls, evidence, findings); this
  substrate holds no control documentation and no compliance
  records of any kind, so there is nothing in-substrate to
  assemble a document from and the reference form is the
  honest one. The entry's own distinction is preserved: this
  is documentation generation, not the assessment automation
  the first unit recorded at idx 307.

Doctrines carried from the core and the first unit, unchanged:
opaque ``*_ref`` strings only; derived-never-stored (the
application view, the document-generation view, and the
addition summary are computed at call time and stored nowhere);
validation fully before mutation, so a failed operation
consumes no id and changes nothing; append-only audit including
denied attempts (``<action>:denied``); RBAC via the core
``access`` module, enforced before any state change. Plain-
string actors carry identity but no role, so -- as in the core
store -- there is nothing to enforce against at this layer for
them.

The latest-record rule lives at a single named seam
(:meth:`DevToolsExtensionsAddition._latest_label`): the current
reported state of an application or a document generation is
the *last* record reported for it. The seam is this unit's
fresh negative control.

RBAC action mapping (the core action set is fixed): application
definitions, revisions, publications, and the application view
ride the build family (``build_write`` / ``build_read``) -- the
application-building surface; document-generation reference and
outcome records ride ``project_write`` / ``project_read``, the
founding mapping for stub reference records; the addition
summary rides ``project_read``.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import _validate_non_empty, _validate_optional_str

APPLICATION_VIEW_METHOD = "derived_from_recorded_definition_and_publication_records"
DOCUMENT_GENERATION_VIEW_METHOD = "derived_from_recorded_outcome_records"
ADDITION_SUMMARY_METHOD = "exact_counts_over_addition_records"

APPLICATION_COMPONENT_KINDS = (
    "page", "form", "workflow", "data_model", "integration", "custom",
)
PUBLICATION_STATUSES = (
    "reported_published", "reported_failed", "reported_unpublished",
)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _validate_components(components):
    """Normalize a component list to a list of {component_ref, kind}.

    A component is a non-empty string (kind defaults to
    "custom") or a dict with a non-empty ``component_ref`` and
    a ``kind`` in APPLICATION_COMPONENT_KINDS. Component refs
    must be unique within the definition. Components are inert
    data: an opaque reference under a kind label, never code.
    """
    if not isinstance(components, list) or not components:
        raise ValidationError("application components must be a non-empty list")
    normalized = []
    seen = set()
    for component in components:
        if isinstance(component, str):
            component = {"component_ref": component, "kind": "custom"}
        if not isinstance(component, dict):
            raise ValidationError(
                "application components entries must be strings or objects"
            )
        ref = _validate_non_empty(component.get("component_ref"), "component_ref")
        kind = component.get("kind", "custom")
        if kind not in APPLICATION_COMPONENT_KINDS:
            raise ValidationError(
                "component kind must be one of %s"
                % (", ".join(APPLICATION_COMPONENT_KINDS),)
            )
        if ref in seen:
            raise ValidationError("duplicate component_ref %r" % (ref,))
        seen.add(ref)
        normalized.append({"component_ref": ref, "kind": kind})
    return normalized


class DevToolsExtensionsAddition:
    """Extension surface for the remainder-addition GAPS batch unit.

    Wraps a :class:`DevToolsStore`. All addition records live in
    this object; the core store's record sets are never written
    by this class (core records are only read, to bind addition
    records to real projects / environments, and to append to
    the core audit log).
    """

    def __init__(self, store):
        self.store = store
        self._applications = {}
        self._publications = {}
        self._doc_references = {}
        self._doc_outcomes = {}
        self._counters = {"app": 0, "apu": 0, "dgr": 0, "dgo": 0}
        self._lock = threading.RLock()

    # -- internal helpers (mirrors of the first unit's) -------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(
                actor_name(actor), action, target, details=details
            )

    def _enforce(self, actor, action, target):
        """Enforce for a User actor; audit the denied attempt, then raise."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit(actor, "%s:denied" % (action,), target)
                raise

    def _require_actor(self, actor, action, target):
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (action,)
            )
        self._enforce(actor, action, target)

    def _maybe_require(self, actor, action):
        if actor is not None and hasattr(actor, "role"):
            require(actor, action)

    @staticmethod
    def _copy(record):
        return copy.deepcopy(record)

    def _get(self, table, record_id, what):
        rec = table.get(record_id)
        if rec is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return rec

    def _sorted(self, table):
        return sorted(
            table.values(), key=lambda r: int(r["id"].rsplit("-", 1)[1])
        )

    def _core_project(self, project_id):
        return self.store.get_project(project_id)

    @staticmethod
    def _latest_label(records, key):
        """The latest-record seam: the last record's label wins.

        MUTATION DRILL NOTE: this seam is the load-bearing
        invariant of this unit's fresh negative control -- the
        current reported state of an application or a document
        generation is its *latest* reported record. An
        implementation that reads the earliest record instead
        reports a superseded state as current; that is the
        mutant the drill and ``test_gaps_batch_addition.py``
        reject.
        """
        return records[-1][key] if records else None

    # -- No-code / low-code platform (definition records) -------------

    def define_application(self, project_id, name, actor, components):
        """Define a no-code application. Action: build_write.

        An application *definition* record: its components are
        held as data (opaque ``component_ref`` under a recorded
        kind label), versioned from revision 1. The definition
        is inert: nothing interprets, builds, renders, or runs
        it in this build (``built_here: False``,
        ``run_here: False``, ``executed_here: False``,
        ``rendered_here: False`` on the record).
        """
        self._require_actor(actor, "build_write", project_id)
        _validate_non_empty(name, "application name")
        components = _validate_components(components)
        with self._lock:
            self._core_project(project_id)
            application_id = self._next_id("app")
            record = {
                "id": application_id,
                "project_id": project_id,
                "name": name,
                "components": components,
                "revision": 1,
                "definition_only": True,
                "built_here": False,
                "run_here": False,
                "executed_here": False,
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._applications[application_id] = record
            self._audit(actor, "exta_application_define", application_id,
                        details={"project_id": project_id, "name": name})
            return self._copy(record)

    def revise_application(self, application_id, actor, components):
        """Replace an application definition's components.

        Action: build_write. The revision increments; the
        components remain inert recorded data.
        """
        self._require_actor(actor, "build_write", application_id)
        components = _validate_components(components)
        with self._lock:
            record = self._get(
                self._applications, application_id, "application definition"
            )
            record["components"] = components
            record["revision"] += 1
            self._audit(actor, "exta_application_revise", application_id,
                        details={"revision": record["revision"]})
            return self._copy(record)

    def get_application(self, application_id, actor=None):
        """Return one application definition. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            return self._copy(
                self._get(self._applications, application_id,
                          "application definition")
            )

    def list_applications(self, project_id=None, actor=None):
        """Return application definitions. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            records = self._sorted(self._applications)
            if project_id is not None:
                records = [r for r in records
                           if r["project_id"] == project_id]
            return [self._copy(r) for r in records]

    def record_application_publication(self, application_id, actor,
                                       status="reported_published",
                                       application_ref=None,
                                       environment_id=None, note=None):
        """Record a publication outcome reported by the platform.

        Action: build_write. The status is the external
        platform's report, recorded verbatim; the record
        snapshots the definition revision it reports against.
        ``application_ref``, if given, names the built
        application by opaque reference -- it is never held
        here. ``environment_id``, if given, must name a core
        environment record. Nothing is built, published, or run
        in this build (``built_here: False``,
        ``run_here: False``, ``executed_here: False``).
        """
        self._require_actor(actor, "build_write", application_id)
        if status not in PUBLICATION_STATUSES:
            raise ValidationError(
                "status must be one of %s" % (", ".join(PUBLICATION_STATUSES),)
            )
        _validate_optional_str(application_ref, "application_ref")
        _validate_optional_str(note, "note")
        with self._lock:
            application = self._get(
                self._applications, application_id, "application definition"
            )
            if environment_id is not None:
                self.store.get_environment(environment_id)
            publication_id = self._next_id("apu")
            record = {
                "id": publication_id,
                "application_id": application_id,
                "project_id": application["project_id"],
                "definition_revision": application["revision"],
                "status": status,
                "application_ref": application_ref,
                "environment_id": environment_id,
                "note": note,
                "built_here": False,
                "run_here": False,
                "executed_here": False,
                "reported_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._publications[publication_id] = record
            self._audit(actor, "exta_application_publication_record",
                        publication_id,
                        details={"application_id": application_id,
                                 "status": status})
            return self._copy(record)

    def list_application_publications(self, application_id=None, actor=None):
        """Return application publication records. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            records = self._sorted(self._publications)
            if application_id is not None:
                records = [r for r in records
                           if r["application_id"] == application_id]
            return [self._copy(r) for r in records]

    def application_view(self, application_id, actor=None):
        """Derive an application's current reported state at read.

        Action: build_read. Current revision and component
        count come from the stored definition; the publication
        count and the latest reported status are derived from
        the publication records at call time (the latest status
        via the :meth:`_latest_label` seam). Computed at call
        time and stored nowhere: the stored definition record
        carries no count and no status field.
        """
        self._maybe_require(actor, "build_read")
        with self._lock:
            application = self._get(
                self._applications, application_id, "application definition"
            )
            publications = [
                r for r in self._sorted(self._publications)
                if r["application_id"] == application_id
            ]
            return {
                "application_id": application_id,
                "project_id": application["project_id"],
                "revision": application["revision"],
                "component_count": len(application["components"]),
                "publication_count": len(publications),
                "latest_publication_status": self._latest_label(
                    publications, "status"
                ),
                "method": APPLICATION_VIEW_METHOD,
            }

    # -- SSP / compliance documentation generation (reference) ---------
    #
    # Labeled reference implementation: each record carries
    # reference_stub: True and status "recorded_reference_only".
    # Creating one changes no core record (pinned by test); the
    # audit entries are the core log's own append-only record of
    # the addition mutation.

    def record_document_generation_reference(self, project_id, document_ref,
                                             actor, framework_ref=None,
                                             system_ref=None):
        """Reference record for documentation generation (idx 579).

        Action: project_write. Points at the target document,
        the framework / control-documentation source, and the
        system by opaque reference only; no document content is
        accepted or held and nothing is generated in this build
        (``generated_here: False``,
        ``document_held_here: False``).
        """
        self._require_actor(actor, "project_write", project_id)
        _validate_non_empty(document_ref, "document_ref")
        _validate_optional_str(framework_ref, "framework_ref")
        _validate_optional_str(system_ref, "system_ref")
        with self._lock:
            self._core_project(project_id)
            reference_id = self._next_id("dgr")
            record = {
                "id": reference_id,
                "kind": "documentation_generation",
                "project_id": project_id,
                "document_ref": document_ref,
                "framework_ref": framework_ref,
                "system_ref": system_ref,
                "reference_stub": True,
                "status": "recorded_reference_only",
                "generated_here": False,
                "document_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._doc_references[reference_id] = record
            self._audit(actor, "exta_document_generation_reference",
                        reference_id,
                        details={"project_id": project_id,
                                 "document_ref": document_ref})
            return self._copy(record)

    def record_document_generation_outcome(self, reference_id, status_label,
                                           actor, output_ref=None):
        """Record a generation outcome reported by external tooling.

        Action: project_write. The status label is stored
        exactly as reported and never interpreted.
        ``output_ref``, if given, names the generated document
        by opaque reference; the document itself is never held
        here (``generated_here: False``,
        ``document_held_here: False``).
        """
        self._require_actor(actor, "project_write", reference_id)
        _validate_non_empty(status_label, "status_label")
        _validate_optional_str(output_ref, "output_ref")
        with self._lock:
            reference = self._get(
                self._doc_references, reference_id,
                "document generation reference",
            )
            outcome_id = self._next_id("dgo")
            record = {
                "id": outcome_id,
                "reference_id": reference_id,
                "project_id": reference["project_id"],
                "status_label": status_label,
                "output_ref": output_ref,
                "reference_stub": True,
                "generated_here": False,
                "document_held_here": False,
                "reported_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._doc_outcomes[outcome_id] = record
            self._audit(actor, "exta_document_generation_outcome", outcome_id,
                        details={"reference_id": reference_id,
                                 "status_label": status_label})
            return self._copy(record)

    def get_document_generation_reference(self, reference_id, actor=None):
        """Return one document-generation reference. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            return self._copy(
                self._get(self._doc_references, reference_id,
                          "document generation reference")
            )

    def list_document_generation_references(self, project_id=None, actor=None):
        """Return document-generation references. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            records = self._sorted(self._doc_references)
            if project_id is not None:
                records = [r for r in records
                           if r["project_id"] == project_id]
            return [self._copy(r) for r in records]

    def list_document_generation_outcomes(self, reference_id=None, actor=None):
        """Return document-generation outcome records.

        Action: project_read.
        """
        self._maybe_require(actor, "project_read")
        with self._lock:
            records = self._sorted(self._doc_outcomes)
            if reference_id is not None:
                records = [r for r in records
                           if r["reference_id"] == reference_id]
            return [self._copy(r) for r in records]

    def document_generation_view(self, reference_id, actor=None):
        """Derive a generation reference's reported state at read.

        Action: project_read. The outcome count and the latest
        reported outcome label (via the :meth:`_latest_label`
        seam) are computed from the outcome records at call
        time and stored nowhere: the stored reference record
        carries no count and no outcome field.
        """
        self._maybe_require(actor, "project_read")
        with self._lock:
            self._get(self._doc_references, reference_id,
                      "document generation reference")
            outcomes = [
                r for r in self._sorted(self._doc_outcomes)
                if r["reference_id"] == reference_id
            ]
            return {
                "reference_id": reference_id,
                "outcome_count": len(outcomes),
                "latest_outcome_label": self._latest_label(
                    outcomes, "status_label"
                ),
                "method": DOCUMENT_GENERATION_VIEW_METHOD,
            }

    # -- Addition summary (derived) --------------------------------------

    def addition_summary(self, actor=None):
        """Derive exact counts over this unit's records at read.

        Action: project_read. Counts only, computed at call time
        and stored nowhere.
        """
        self._maybe_require(actor, "project_read")
        with self._lock:
            return {
                "applications": len(self._applications),
                "application_publications": len(self._publications),
                "document_generation_references": len(self._doc_references),
                "document_generation_outcomes": len(self._doc_outcomes),
                "method": ADDITION_SUMMARY_METHOD,
            }
