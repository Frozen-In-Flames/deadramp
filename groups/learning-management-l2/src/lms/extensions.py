"""Final GAPS batch extensions for the Learning Management L2 build.

Clean-room, standard-library-only extensions for the 16 open Extended
entries of Singleton 48 (see ``BATCH.md`` in the group directory for
the per-entry disposition). This module is a wrapper around
:class:`LmsStore`; every core module is untouched.

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — records plus deterministic derivations over the
group's OWN records.

- The delivery engine is delivery-session records whose status is
  DERIVED at read from the core progress/registration records; no
  content is served to anyone.
- Packaging and the xAPI protocol surface are package-manifest and
  distribution records with conformance-shaped validation OF THE
  RECORDS; there is no SCORM player and no xAPI endpoint.
- Analytics and recommendations are deterministic derivations over
  held records, labeled with their method; nothing is a learned
  model, and nothing computes a score — aggregate counts and shares
  of records only, never a per-learner value.
- Anything that would execute against an external system ships as a
  labeled reference record instead: stub-engine records carry
  ``reference_stub: True``; transport receipts and xAPI forwarding
  records carry ``reference_transport: True``. Nothing is sent,
  signed, rendered, routed, or executed.
- The core workflow registry still never executes: the workflow
  entry is a stub by triage — an execution RECORD, definitions
  copied as data, labeled reference, changing no other record.

Doctrines carried from the core: opaque ``*_ref`` strings only (no
record shape here can hold a name, email, phone, or identifier for a
real person); derived-never-stored for every computed value (delivery
status, package conformance, analytics, recommendation gaps,
succession coverage, report results, survey tallies); append-only
audit on the core store's log with ``ext_``-prefixed actions for
every successful mutation; RBAC via :mod:`lms.access` with the
core's existing actions, enforced before any state change or id
allocation, so a failed operation consumes no id and changes
nothing; learner scope mirrors the store's — a learner-role actor
may only read views whose ``learner_ref`` is their own name.

No score field appears anywhere in this surface: no key here is
named ``score`` / ``score_*`` / ``*_score``, pinned by a recursive
key scan in the tests — the founding invariant binds the extension
exactly as it binds the core. Survey answers are recorded as text
verbatim (never parsed into numbers), competency levels are read
only as presence/absence of a record, never interpreted.
"""

import copy
import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

PACKAGE_STANDARDS = ("scorm_1_2", "scorm_2004", "aicc", "cmi5")
DELIVERY_MODES = ("self_paced", "instructor_led", "virtual", "live")
NOTIFICATION_TRIGGERS = (
    "compliance_overdue", "registration_created", "authorization_decided",
)
REPORT_SECTIONS = (
    "learners", "courses", "progress", "compliance", "statements",
    "registrations",
)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string(value, what):
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _string_list(value, what, allow_empty=False):
    if not isinstance(value, (list, tuple)):
        raise ValidationError("%s must be a list of strings" % (what,))
    items = list(value)
    if not allow_empty and not items:
        raise ValidationError("%s must be a non-empty list" % (what,))
    for item in items:
        _non_empty(item, what)
    return items


def _validate_date(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO date string (YYYY-MM-DD)" % (what,))
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO date: %r" % (what, value)) from exc


def _coerce_as_of(as_of):
    if as_of is None:
        return date.today()
    if isinstance(as_of, datetime):
        return as_of.date()
    if isinstance(as_of, date):
        return as_of
    if isinstance(as_of, str):
        return _validate_date(as_of, "as_of")
    raise ValidationError("as_of must be an ISO date string or date")


class LmsExtensions:
    """Extension surface wrapping one :class:`LmsStore`."""

    def __init__(self, store):
        self.store = store
        self._delivery_sessions = {}
        self._packages = {}
        self._distributions = {}
        self._forward_records = {}
        self._career_paths = {}
        self._succession_plans = {}
        self._applications = {}
        self._surveys = {}
        self._survey_responses = {}
        self._kb_articles = {}
        self._cms_pages = {}
        self._report_definitions = {}
        self._notification_rules = {}
        self._notification_receipts = {}
        self._ehri_records = {}
        self._authoring_drafts = {}
        self._form_workflows = {}
        self._execution_records = {}
        self._counters = {
            "dls": 0, "pkg": 0, "dst": 0, "fwd": 0, "crp": 0, "suc": 0,
            "app": 0, "svy": 0, "rsp": 0, "kba": 0, "pg": 0, "rpd": 0,
            "ntr": 0, "rcpt": 0, "ehr": 0, "dft": 0, "frm": 0, "exe": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    @staticmethod
    def _require_actor(actor, action):
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (action,))
        if hasattr(actor, "role"):
            require(actor, action)

    @staticmethod
    def _scope_check(actor, learner_ref):
        if (actor is not None and getattr(actor, "role", None) == "learner"
                and getattr(actor, "name", None) != learner_ref):
            raise PermissionDenied(
                "permission denied: learner %r may not access records of "
                "learner %r" % (getattr(actor, "name", None), learner_ref)
            )

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    # -- Learning delivery engine (records form) ------------------------
    # Delivery sessions bind a learner to a course (and optionally one
    # of its content items). The stored record carries NO status:
    # delivery status is derived at read from the core progress and
    # registration records, the founding derivation discipline.

    def create_delivery_session(self, learner_ref, course_id, actor,
                                content_id=None, mode="self_paced"):
        """Record a delivery session. Action: progress_write."""
        self._require_actor(actor, "progress_write")
        _non_empty(learner_ref, "learner_ref")
        if mode not in DELIVERY_MODES:
            raise ValidationError(
                "mode must be one of %s" % (", ".join(DELIVERY_MODES),))
        with self._lock:
            self.store.get_course(course_id, actor=None)
            # learner existence via the core registry
            learners = self.store.list_learners()
            if learner_ref not in {l["ref"] for l in learners}:
                raise NotFoundError("learner not found: %r" % (learner_ref,))
            if content_id is not None:
                item = self.store.get_content_item(content_id, actor=None)
                if item["course_id"] is not None and item["course_id"] != course_id:
                    raise ValidationError(
                        "content item %r does not belong to course %r"
                        % (content_id, course_id))
            session_id = self._next_id("dls")
            record = {
                "id": session_id,
                "learner_ref": learner_ref,
                "course_id": course_id,
                "content_id": content_id,
                "mode": mode,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._delivery_sessions[session_id] = record
            self._audit(actor, "ext_delivery_session_create", session_id,
                        details={"learner_ref": learner_ref,
                                 "course_id": course_id, "mode": mode})
            return dict(record)

    def _derive_delivery_status(self, learner_ref, course_id):
        """Derive delivery status from core records. Never stored.

        MUTATION DRILL NOTE: the completed branch of this derivation
        is the batch negative control's load-bearing invariant — a
        learner with a completed core progress record for the course
        must read ``completed``, never ``in_progress``.
        """
        progress = self.store.list_progress(actor=None, learner_ref=learner_ref,
                                            course_id=course_id)
        if any(p["status"] == "completed" for p in progress):
            return "completed"
        if progress:
            return "in_progress"
        sessions = [s for s in self._delivery_sessions.values()
                    if s["learner_ref"] == learner_ref
                    and s["course_id"] == course_id]
        return "enrolled" if sessions else "not_started"

    def _delivery_view(self, record):
        view = dict(record)
        view["status"] = self._derive_delivery_status(
            record["learner_ref"], record["course_id"])
        view["status_method"] = "derived_from_core_progress_records"
        return view

    def get_delivery_session(self, session_id, actor=None):
        """Return one session with derived status. Action: progress_read."""
        if actor is not None:
            self._require_actor(actor, "progress_read")
        with self._lock:
            record = self._get(self._delivery_sessions, session_id,
                               "delivery session")
            self._scope_check(actor, record["learner_ref"])
            return self._delivery_view(record)

    def list_delivery_sessions(self, actor=None, learner_ref=None,
                               course_id=None):
        """Return sessions with derived status. Action: progress_read."""
        if actor is not None:
            self._require_actor(actor, "progress_read")
        if learner_ref is not None:
            self._scope_check(actor, learner_ref)
        with self._lock:
            records = list(self._delivery_sessions.values())
            if learner_ref is not None:
                records = [r for r in records if r["learner_ref"] == learner_ref]
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            if actor is not None and getattr(actor, "role", None) == "learner":
                name = getattr(actor, "name", None)
                records = [r for r in records if r["learner_ref"] == name]
            return [self._delivery_view(r) for r in records]

    def delivery_status(self, learner_ref, course_id, actor=None):
        """Derived delivery status for one learner+course.

        Action: progress_read (+ learner scope).
        """
        if actor is not None:
            self._require_actor(actor, "progress_read")
        self._scope_check(actor, learner_ref)
        with self._lock:
            self.store.get_course(course_id, actor=None)
            return {
                "learner_ref": learner_ref,
                "course_id": course_id,
                "status": self._derive_delivery_status(learner_ref, course_id),
                "method": "derived_from_core_progress_records",
            }

    # -- SCORM / AICC / cmi5 packaging & distribution (records form) ----

    def create_package(self, title, standard, actor, course_id=None,
                       item_refs=None):
        """Record a package manifest. Action: catalog_write.

        Every ``item_refs`` entry must resolve to an existing core
        content item. The manifest records the packaging standard;
        conformance is derived at read (see :meth:`package_conformance`).
        """
        self._require_actor(actor, "catalog_write")
        _non_empty(title, "package title")
        if standard not in PACKAGE_STANDARDS:
            raise ValidationError(
                "standard must be one of %s" % (", ".join(PACKAGE_STANDARDS),))
        if item_refs is None:
            item_refs = []
        if not isinstance(item_refs, (list, tuple)):
            raise ValidationError("item_refs must be a list")
        item_refs = list(item_refs)
        with self._lock:
            if course_id is not None:
                self.store.get_course(course_id, actor=None)
            for ref in item_refs:
                self.store.get_content_item(ref, actor=None)
            package_id = self._next_id("pkg")
            record = {
                "id": package_id,
                "title": title,
                "standard": standard,
                "course_id": course_id,
                "item_refs": list(item_refs),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._packages[package_id] = record
            self._audit(actor, "ext_package_create", package_id,
                        details={"title": title, "standard": standard})
            return self._copy_package(record)

    @staticmethod
    def _copy_package(record):
        copied = dict(record)
        copied["item_refs"] = list(record["item_refs"])
        return copied

    def get_package(self, package_id, actor=None):
        """Return one package manifest. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            return self._copy_package(
                self._get(self._packages, package_id, "package"))

    def list_packages(self, actor=None, course_id=None):
        """Return package manifests. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            records = list(self._packages.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            return [self._copy_package(r) for r in records]

    def package_conformance(self, package_id, actor=None):
        """Conformance-shaped validation OF THE MANIFEST RECORD.

        Derived at read, never stored: checks that the manifest has
        at least one entry, that every entry still resolves, and
        that every entry's recorded core standard matches the
        manifest standard. This validates records; it does not run
        a package or claim a runtime conformance certification.
        Action: catalog_read.
        """
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            record = self._get(self._packages, package_id, "package")
            checks = []
            checks.append({
                "check": "has_entries",
                "passed": len(record["item_refs"]) > 0,
            })
            unresolved = []
            mismatched = []
            for ref in record["item_refs"]:
                try:
                    item = self.store.get_content_item(ref, actor=None)
                except NotFoundError:
                    unresolved.append(ref)
                    continue
                if item["standard"] != record["standard"]:
                    mismatched.append(ref)
            checks.append({"check": "entries_resolve", "passed": not unresolved})
            checks.append({
                "check": "entry_standards_match_manifest",
                "passed": not mismatched,
            })
            return {
                "package_id": record["id"],
                "standard": record["standard"],
                "checks": checks,
                "unresolved_refs": unresolved,
                "mismatched_refs": mismatched,
                "conformant": all(c["passed"] for c in checks),
                "method": "record_validation_only",
            }

    def record_distribution(self, package_id, target_ref, actor, note=""):
        """Record a distribution of a package to an opaque target.

        Action: catalog_write. A record of an intended/recorded
        distribution; nothing is deployed or delivered by this call.
        """
        self._require_actor(actor, "catalog_write")
        _non_empty(target_ref, "target_ref")
        _string(note, "note")
        with self._lock:
            self._get(self._packages, package_id, "package")
            distribution_id = self._next_id("dst")
            record = {
                "id": distribution_id,
                "package_id": package_id,
                "target_ref": target_ref,
                "note": note,
                "state": "recorded",
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._distributions[distribution_id] = record
            self._audit(actor, "ext_distribution_record", distribution_id,
                        details={"package_id": package_id,
                                 "target_ref": target_ref})
            return dict(record)

    def list_distributions(self, actor=None, package_id=None):
        """Return distribution records. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            records = list(self._distributions.values())
            if package_id is not None:
                records = [r for r in records if r["package_id"] == package_id]
            return [dict(r) for r in records]

    # -- xAPI protocol surface & LRS conformance (records form) ---------

    def statement_conformance(self, actor, learner_ref=None):
        """Conformance-shaped validation OF THE CORE STATEMENT RECORDS.

        Derived at read over the core LRS records: every statement
        carries exactly the core's eight keys (re-read from the core
        store, not assumed), verbs are non-empty, and result text is
        present only as a verbatim string. This validates the record
        set; there is no xAPI endpoint and no protocol certification
        is claimed. Action: experience_read (+ learner scope).
        """
        self._require_actor(actor, "experience_read")
        if learner_ref is not None:
            self._scope_check(actor, learner_ref)
        with self._lock:
            statements = self.store.list_statements(actor=None,
                                                    learner_ref=learner_ref)
            expected_keys = {
                "id", "learner_ref", "verb", "object_ref", "context",
                "result_text", "recorded_by", "recorded_utc",
            }
            shape_ok = all(set(s) == expected_keys for s in statements)
            verbs_ok = all(isinstance(s["verb"], str) and s["verb"].strip()
                           for s in statements)
            result_ok = all(
                s["result_text"] is None or isinstance(s["result_text"], str)
                for s in statements)
            by_verb = {}
            for s in statements:
                by_verb[s["verb"]] = by_verb.get(s["verb"], 0) + 1
            return {
                "statements_examined": len(statements),
                "checks": [
                    {"check": "exact_eight_key_shape", "passed": shape_ok},
                    {"check": "verbs_non_empty", "passed": verbs_ok},
                    {"check": "result_text_verbatim_string_only",
                     "passed": result_ok},
                ],
                "conformant": shape_ok and verbs_ok and result_ok,
                "statements_by_verb": by_verb,
                "method": "record_validation_only",
            }

    def record_statement_forward(self, statement_id, destination_ref, actor):
        """Record an intended statement forward — labeled transport.

        Action: experience_write. Nothing is transmitted: the record
        carries ``reference_transport: True`` and the recorded-only
        state, following the house transport precedent.
        """
        self._require_actor(actor, "experience_write")
        _non_empty(destination_ref, "destination_ref")
        with self._lock:
            self.store.get_statement(statement_id, actor=None)
            forward_id = self._next_id("fwd")
            record = {
                "id": forward_id,
                "statement_id": statement_id,
                "destination_ref": destination_ref,
                "reference_transport": True,
                "state": "recorded_reference_only",
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._forward_records[forward_id] = record
            self._audit(actor, "ext_statement_forward_record", forward_id,
                        details={"statement_id": statement_id,
                                 "destination_ref": destination_ref,
                                 "reference_transport": True})
            return dict(record)

    def list_statement_forwards(self, actor=None, statement_id=None):
        """Return statement forward records. Action: experience_read."""
        if actor is not None:
            self._require_actor(actor, "experience_read")
        with self._lock:
            records = list(self._forward_records.values())
            if statement_id is not None:
                records = [r for r in records if r["statement_id"] == statement_id]
            return [dict(r) for r in records]

    # -- Learning analytics & outcomes (deterministic derivations) ------

    def analytics_summary(self, actor, as_of=None):
        """Aggregate counts and record shares over the group's records.

        Derived at read. Counts and integer-basis-point shares OF
        RECORDS (progress records completed out of progress records,
        assignments by derived status); no per-learner value is
        computed and nothing is a score. Action: report_read.
        """
        self._require_actor(actor, "report_read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            progress = self.store.list_progress(actor=None)
            by_status = {"not_started": 0, "in_progress": 0, "completed": 0}
            for record in progress:
                by_status[record["status"]] += 1
            total = len(progress)
            completed = by_status["completed"]
            compliance = self.store.list_compliance(actor=None, as_of=as_of_date)
            compliance_by_status = {"current": 0, "overdue": 0, "completed": 0}
            for view in compliance:
                compliance_by_status[view["status"]] += 1
            statements = self.store.list_statements(actor=None)
            return {
                "as_of": as_of_date.isoformat(),
                "method": "deterministic_counts",
                "progress_records": total,
                "progress_by_status": by_status,
                "completed_share_bps": (
                    (completed * 10000) // total if total else None),
                "compliance_assignments": len(compliance),
                "compliance_by_status": compliance_by_status,
                "statements": len(statements),
                "delivery_sessions": len(self._delivery_sessions),
                "survey_responses": len(self._survey_responses),
            }

    def outcomes_by_course(self, actor):
        """Per-course outcome counts, derived at read.

        Action: report_read. For each core course: progress records
        by status and registration counts — counts only.
        """
        self._require_actor(actor, "report_read")
        with self._lock:
            rows = []
            for course in self.store.list_courses(actor=None):
                progress = self.store.list_progress(
                    actor=None, course_id=course["id"])
                by_status = {"not_started": 0, "in_progress": 0, "completed": 0}
                for record in progress:
                    by_status[record["status"]] += 1
                events = self.store.list_events(actor=None,
                                                course_id=course["id"])
                registrations = 0
                for event in events:
                    registrations += len(self.store.list_registrations(
                        actor=None, event_id=event["id"]))
                rows.append({
                    "course_id": course["id"],
                    "progress_records": len(progress),
                    "progress_by_status": by_status,
                    "events": len(events),
                    "registrations": registrations,
                })
            return {"method": "deterministic_counts", "courses": rows}

    # -- Career mapping & recommendation (deterministic gap derivation) -

    def create_career_path(self, name, actor, competency_ids=None,
                           course_ids=None, description=""):
        """Record a career path: required competencies + mapped courses.

        Action: plan_write. Competency and course ids must resolve
        to core records; order is preserved (recommendations follow
        path order, never a ranking).
        """
        self._require_actor(actor, "plan_write")
        _non_empty(name, "career path name")
        _string(description, "description")
        competency_ids = list(competency_ids or [])
        course_ids = list(course_ids or [])
        for ref in competency_ids + course_ids:
            _non_empty(ref, "path reference")
        with self._lock:
            for competency_id in competency_ids:
                self.store.get_competency(competency_id, actor=None)
            for course_id in course_ids:
                self.store.get_course(course_id, actor=None)
            path_id = self._next_id("crp")
            record = {
                "id": path_id,
                "name": name,
                "description": description,
                "competency_ids": competency_ids,
                "course_ids": course_ids,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._career_paths[path_id] = record
            self._audit(actor, "ext_career_path_create", path_id,
                        details={"name": name})
            return self._copy_path(record)

    @staticmethod
    def _copy_path(record):
        copied = dict(record)
        copied["competency_ids"] = list(record["competency_ids"])
        copied["course_ids"] = list(record["course_ids"])
        return copied

    def get_career_path(self, path_id, actor=None):
        """Return one career path. Action: plan_read."""
        if actor is not None:
            self._require_actor(actor, "plan_read")
        with self._lock:
            return self._copy_path(
                self._get(self._career_paths, path_id, "career path"))

    def list_career_paths(self, actor=None):
        """Return career paths. Action: plan_read."""
        if actor is not None:
            self._require_actor(actor, "plan_read")
        with self._lock:
            return [self._copy_path(r) for r in self._career_paths.values()]

    def recommend_training(self, learner_ref, path_id, actor=None):
        """Deterministic gap derivation for one learner on one path.

        Action: plan_read (+ learner scope). A competency is
        "covered" when ANY core learner-competency record exists for
        it (levels are never interpreted); a course is recommended
        when it is on the path and the learner has no completed core
        progress record for it. Order follows the path. The result
        is derived at read and labeled with its method; no ranking
        or score is produced.
        """
        if actor is not None:
            self._require_actor(actor, "plan_read")
        self._scope_check(actor, learner_ref)
        with self._lock:
            path = self._get(self._career_paths, path_id, "career path")
            learners = self.store.list_learners()
            if learner_ref not in {l["ref"] for l in learners}:
                raise NotFoundError("learner not found: %r" % (learner_ref,))
            held = {r["competency_id"] for r in
                    self.store.list_learner_competencies(
                        actor=None, learner_ref=learner_ref)}
            missing = [c for c in path["competency_ids"] if c not in held]
            covered = [c for c in path["competency_ids"] if c in held]
            recommended = []
            for course_id in path["course_ids"]:
                progress = self.store.list_progress(
                    actor=None, learner_ref=learner_ref, course_id=course_id)
                if not any(p["status"] == "completed" for p in progress):
                    recommended.append(course_id)
            return {
                "learner_ref": learner_ref,
                "path_id": path_id,
                "method": "deterministic_gap_match",
                "covered_competency_ids": covered,
                "missing_competency_ids": missing,
                "recommended_course_ids": recommended,
            }

    # -- Leadership succession planning (records + coverage derivation) -

    def create_succession_plan(self, role_ref, actor, candidate_refs=None,
                               competency_ids=None):
        """Record a succession plan for an opaque role reference.

        Action: plan_write. Candidates are learner references that
        must exist; required competencies must resolve to core
        competency definitions.
        """
        self._require_actor(actor, "plan_write")
        _non_empty(role_ref, "role_ref")
        candidate_refs = list(candidate_refs or [])
        competency_ids = list(competency_ids or [])
        for ref in candidate_refs + competency_ids:
            _non_empty(ref, "succession reference")
        with self._lock:
            learner_refs = {l["ref"] for l in self.store.list_learners()}
            for ref in candidate_refs:
                if ref not in learner_refs:
                    raise NotFoundError("learner not found: %r" % (ref,))
            for competency_id in competency_ids:
                self.store.get_competency(competency_id, actor=None)
            plan_id = self._next_id("suc")
            record = {
                "id": plan_id,
                "role_ref": role_ref,
                "candidate_refs": candidate_refs,
                "competency_ids": competency_ids,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._succession_plans[plan_id] = record
            self._audit(actor, "ext_succession_plan_create", plan_id,
                        details={"role_ref": role_ref})
            return self._copy_succession(record)

    @staticmethod
    def _copy_succession(record):
        copied = dict(record)
        copied["candidate_refs"] = list(record["candidate_refs"])
        copied["competency_ids"] = list(record["competency_ids"])
        return copied

    def get_succession_plan(self, plan_id, actor=None):
        """Return one succession plan. Action: plan_read."""
        if actor is not None:
            self._require_actor(actor, "plan_read")
        with self._lock:
            return self._copy_succession(
                self._get(self._succession_plans, plan_id, "succession plan"))

    def succession_coverage(self, plan_id, actor=None):
        """Derived per-candidate competency coverage for a plan.

        Action: plan_read. ``covers_all`` is a deterministic boolean
        rule over record presence (any learner-competency record
        counts; levels verbatim, never interpreted). No readiness
        score is computed.
        """
        if actor is not None:
            self._require_actor(actor, "plan_read")
        with self._lock:
            plan = self._get(self._succession_plans, plan_id, "succession plan")
            rows = []
            for ref in plan["candidate_refs"]:
                held = {r["competency_id"] for r in
                        self.store.list_learner_competencies(
                            actor=None, learner_ref=ref)}
                missing = [c for c in plan["competency_ids"] if c not in held]
                rows.append({
                    "candidate_ref": ref,
                    "covered_competency_ids": [
                        c for c in plan["competency_ids"] if c in held],
                    "missing_competency_ids": missing,
                    "covers_all": not missing,
                })
            return {
                "plan_id": plan_id,
                "role_ref": plan["role_ref"],
                "method": "deterministic_presence_match",
                "candidates": rows,
            }

    # -- Candidate review / talent acquisition (records form) -----------

    def create_application(self, candidate_ref, program_ref, actor,
                           note=""):
        """Record a candidate application. Action: authorization_write.

        ``candidate_ref`` and ``program_ref`` are opaque references;
        applicants need not be learners in the registry.
        """
        self._require_actor(actor, "authorization_write")
        _non_empty(candidate_ref, "candidate_ref")
        _non_empty(program_ref, "program_ref")
        _string(note, "note")
        with self._lock:
            application_id = self._next_id("app")
            record = {
                "id": application_id,
                "candidate_ref": candidate_ref,
                "program_ref": program_ref,
                "note": note,
                "state": "submitted",
                "reviewed_by": None,
                "reviewed_utc": None,
                "review_note": "",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._applications[application_id] = record
            self._audit(actor, "ext_application_create", application_id,
                        details={"candidate_ref": candidate_ref,
                                 "program_ref": program_ref})
            return dict(record)

    def review_application(self, application_id, decision, actor, note=""):
        """Record a review decision. Action: authorization_write.

        Separation of duties, mirroring the core SF-182 rule: the
        actor who created the application may not review it.
        """
        self._require_actor(actor, "authorization_write")
        if decision not in ("accepted", "declined"):
            raise ValidationError("decision must be one of accepted, declined")
        _string(note, "note")
        with self._lock:
            record = self._get(self._applications, application_id, "application")
            if record["state"] != "submitted":
                raise ValidationError(
                    "application %r has already been reviewed" % (application_id,))
            if actor_name(actor) == record["created_by"]:
                raise PermissionDenied(
                    "permission denied: the creator may not review their own "
                    "application")
            record["state"] = decision
            record["reviewed_by"] = actor_name(actor)
            record["reviewed_utc"] = _utc_now()
            record["review_note"] = note
            self._audit(actor, "ext_application_review", application_id,
                        details={"decision": decision})
            return dict(record)

    def get_application(self, application_id, actor=None):
        """Return one application. Action: authorization_read."""
        if actor is not None:
            self._require_actor(actor, "authorization_read")
        with self._lock:
            return dict(self._get(self._applications, application_id,
                                  "application"))

    def list_applications(self, actor=None, program_ref=None):
        """Return applications. Action: authorization_read."""
        if actor is not None:
            self._require_actor(actor, "authorization_read")
        with self._lock:
            records = list(self._applications.values())
            if program_ref is not None:
                records = [r for r in records if r["program_ref"] == program_ref]
            return [dict(r) for r in records]

    # -- Employee survey engine (records form) ----------------------------

    def create_survey(self, title, actor, questions=None):
        """Record a survey instrument. Action: workflow_write.

        Questions are text, stored verbatim; answers are text
        recorded verbatim — there is no numeric answer shape, so
        nothing in a survey can become a score.
        """
        self._require_actor(actor, "workflow_write")
        _non_empty(title, "survey title")
        questions = _string_list(questions, "questions")
        with self._lock:
            survey_id = self._next_id("svy")
            record = {
                "id": survey_id,
                "title": title,
                "questions": questions,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._surveys[survey_id] = record
            self._audit(actor, "ext_survey_create", survey_id,
                        details={"title": title})
            copied = dict(record)
            copied["questions"] = list(questions)
            return copied

    def get_survey(self, survey_id, actor=None):
        """Return one survey instrument. Action: workflow_read."""
        if actor is not None:
            self._require_actor(actor, "workflow_read")
        with self._lock:
            record = self._get(self._surveys, survey_id, "survey")
            copied = dict(record)
            copied["questions"] = list(record["questions"])
            return copied

    def record_survey_response(self, survey_id, respondent_ref, answers,
                               actor):
        """Record one response. Action: workflow_write.

        ``respondent_ref`` is opaque. ``answers`` must be a list of
        strings, one per survey question, stored verbatim.
        """
        self._require_actor(actor, "workflow_write")
        _non_empty(respondent_ref, "respondent_ref")
        if not isinstance(answers, (list, tuple)):
            raise ValidationError("answers must be a list of strings")
        answers = list(answers)
        for answer in answers:
            if not isinstance(answer, str):
                raise ValidationError("each answer must be a string")
        with self._lock:
            survey = self._get(self._surveys, survey_id, "survey")
            if len(answers) != len(survey["questions"]):
                raise ValidationError(
                    "answers must have one entry per question (%d)"
                    % (len(survey["questions"]),))
            response_id = self._next_id("rsp")
            record = {
                "id": response_id,
                "survey_id": survey_id,
                "respondent_ref": respondent_ref,
                "answers": list(answers),
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._survey_responses[response_id] = record
            self._audit(actor, "ext_survey_response_record", response_id,
                        details={"survey_id": survey_id,
                                 "respondent_ref": respondent_ref})
            copied = dict(record)
            copied["answers"] = list(answers)
            return copied

    def list_survey_responses(self, actor=None, survey_id=None):
        """Return survey responses. Action: workflow_read."""
        if actor is not None:
            self._require_actor(actor, "workflow_read")
        with self._lock:
            records = list(self._survey_responses.values())
            if survey_id is not None:
                records = [r for r in records if r["survey_id"] == survey_id]
            result = []
            for record in records:
                copied = dict(record)
                copied["answers"] = list(record["answers"])
                result.append(copied)
            return result

    def survey_summary(self, survey_id, actor=None):
        """Derived tallies for one survey. Action: workflow_read.

        Counts of responses and, per question, counts of identical
        verbatim answers. Answers are never parsed or averaged.
        """
        if actor is not None:
            self._require_actor(actor, "workflow_read")
        with self._lock:
            survey = self._get(self._surveys, survey_id, "survey")
            responses = [r for r in self._survey_responses.values()
                         if r["survey_id"] == survey_id]
            per_question = []
            for index, question in enumerate(survey["questions"]):
                counts = {}
                for response in responses:
                    answer = response["answers"][index]
                    counts[answer] = counts.get(answer, 0) + 1
                per_question.append({"question": question, "answers": counts})
            return {
                "survey_id": survey_id,
                "responses": len(responses),
                "per_question": per_question,
                "method": "verbatim_answer_counts",
            }

    # -- Knowledge base / wiki platform (records form, adjacent product) --

    def create_kb_article(self, title, body, actor, tags=None):
        """Record a knowledge-base article (version 1). Action: catalog_write."""
        self._require_actor(actor, "catalog_write")
        _non_empty(title, "article title")
        _string(body, "body")
        tags = _string_list(tags, "tags", allow_empty=True) if tags else []
        with self._lock:
            article_id = self._next_id("kba")
            record = {
                "id": article_id,
                "title": title,
                "tags": tags,
                "versions": [{"body": body, "recorded_by": actor_name(actor),
                              "recorded_utc": _utc_now()}],
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._kb_articles[article_id] = record
            self._audit(actor, "ext_kb_article_create", article_id,
                        details={"title": title})
            return self._kb_view(record)

    @staticmethod
    def _kb_view(record):
        view = {
            "id": record["id"],
            "title": record["title"],
            "tags": list(record["tags"]),
            "body": record["versions"][-1]["body"],
            "version_count": len(record["versions"]),
            "created_by": record["created_by"],
            "created_utc": record["created_utc"],
        }
        return view

    def revise_kb_article(self, article_id, body, actor):
        """Append a revision. Action: catalog_write. History is append-only."""
        self._require_actor(actor, "catalog_write")
        _string(body, "body")
        with self._lock:
            record = self._get(self._kb_articles, article_id, "article")
            record["versions"].append({
                "body": body, "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now()})
            self._audit(actor, "ext_kb_article_revise", article_id,
                        details={"version": len(record["versions"])})
            return self._kb_view(record)

    def get_kb_article(self, article_id, actor=None):
        """Return one article view (version count derived). Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            return self._kb_view(
                self._get(self._kb_articles, article_id, "article"))

    def search_kb(self, query, actor):
        """Substring search over article titles/bodies. Action: catalog_read."""
        self._require_actor(actor, "catalog_read")
        _non_empty(query, "query")
        needle = query.strip().lower()
        with self._lock:
            return [self._kb_view(r) for r in self._kb_articles.values()
                    if needle in r["title"].lower()
                    or needle in r["versions"][-1]["body"].lower()]

    # -- Web CMS platform (records form, adjacent product) ----------------

    def create_cms_page(self, slug, title, body, actor):
        """Record a CMS page in draft state. Action: catalog_write.

        Pages are records; nothing is rendered or served. ``slug``
        is unique across the page records.
        """
        self._require_actor(actor, "catalog_write")
        _non_empty(slug, "slug")
        _non_empty(title, "page title")
        _string(body, "body")
        with self._lock:
            for existing in self._cms_pages.values():
                if existing["slug"] == slug:
                    raise ValidationError("page slug %r already exists" % (slug,))
            page_id = self._next_id("pg")
            record = {
                "id": page_id,
                "slug": slug,
                "title": title,
                "body": body,
                "state": "draft",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._cms_pages[page_id] = record
            self._audit(actor, "ext_cms_page_create", page_id,
                        details={"slug": slug, "title": title})
            return dict(record)

    def publish_cms_page(self, page_id, actor):
        """Record the published state. Action: catalog_write."""
        self._require_actor(actor, "catalog_write")
        with self._lock:
            record = self._get(self._cms_pages, page_id, "page")
            if record["state"] == "published":
                raise ValidationError("page %r is already published" % (page_id,))
            record["state"] = "published"
            self._audit(actor, "ext_cms_page_publish", page_id,
                        details={"slug": record["slug"]})
            return dict(record)

    def get_cms_page(self, page_id, actor=None):
        """Return one page record. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            return dict(self._get(self._cms_pages, page_id, "page"))

    def list_cms_pages(self, actor=None, state=None):
        """Return page records. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            records = list(self._cms_pages.values())
            if state is not None:
                records = [r for r in records if r["state"] == state]
            return [dict(r) for r in records]

    # -- Configurable report builder & dashboards (definitions + runs) ----

    def create_report_definition(self, name, actor, sections=None):
        """Record a report definition. Action: workflow_write.

        ``sections`` must be a non-empty subset of REPORT_SECTIONS.
        The definition stores no results; running it derives counts
        at run time.
        """
        self._require_actor(actor, "workflow_write")
        _non_empty(name, "report definition name")
        sections = _string_list(sections, "sections")
        for section in sections:
            if section not in REPORT_SECTIONS:
                raise ValidationError(
                    "section must be one of %s" % (", ".join(REPORT_SECTIONS),))
        if len(set(sections)) != len(sections):
            raise ValidationError("sections must not repeat")
        with self._lock:
            definition_id = self._next_id("rpd")
            record = {
                "id": definition_id,
                "name": name,
                "sections": sections,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._report_definitions[definition_id] = record
            self._audit(actor, "ext_report_definition_create", definition_id,
                        details={"name": name, "sections": list(sections)})
            copied = dict(record)
            copied["sections"] = list(sections)
            return copied

    def get_report_definition(self, definition_id, actor=None):
        """Return one report definition. Action: workflow_read."""
        if actor is not None:
            self._require_actor(actor, "workflow_read")
        with self._lock:
            record = self._get(self._report_definitions, definition_id,
                               "report definition")
            copied = dict(record)
            copied["sections"] = list(record["sections"])
            return copied

    def run_report_definition(self, definition_id, actor, as_of=None):
        """Run a definition: derive each section's counts at run time.

        Action: report_read. Results are computed from the core
        records on every run and never stored on the definition.
        The dashboard form is this same run — a definition plus its
        derived result.
        """
        self._require_actor(actor, "report_read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            record = self._get(self._report_definitions, definition_id,
                               "report definition")
            results = {}
            for section in record["sections"]:
                if section == "learners":
                    results[section] = len(self.store.list_learners())
                elif section == "courses":
                    results[section] = len(self.store.list_courses(actor=None))
                elif section == "progress":
                    results[section] = len(self.store.list_progress(actor=None))
                elif section == "compliance":
                    views = self.store.list_compliance(actor=None,
                                                       as_of=as_of_date)
                    by_status = {"current": 0, "overdue": 0, "completed": 0}
                    for view in views:
                        by_status[view["status"]] += 1
                    results[section] = {
                        "assignments": len(views), "by_status": by_status}
                elif section == "statements":
                    results[section] = len(self.store.list_statements(actor=None))
                elif section == "registrations":
                    results[section] = len(
                        self.store.list_registrations(actor=None))
            return {
                "definition_id": record["id"],
                "name": record["name"],
                "as_of": as_of_date.isoformat(),
                "method": "deterministic_counts",
                "results": results,
            }

    # -- Notification automation & delivery transport (labeled receipts) --

    def create_notification_rule(self, name, trigger, recipient_ref, subject,
                                 actor):
        """Record a notification automation rule. Action: workflow_write."""
        self._require_actor(actor, "workflow_write")
        _non_empty(name, "rule name")
        if trigger not in NOTIFICATION_TRIGGERS:
            raise ValidationError(
                "trigger must be one of %s" % (", ".join(NOTIFICATION_TRIGGERS),))
        _non_empty(recipient_ref, "recipient_ref")
        _non_empty(subject, "subject")
        with self._lock:
            rule_id = self._next_id("ntr")
            record = {
                "id": rule_id,
                "name": name,
                "trigger": trigger,
                "recipient_ref": recipient_ref,
                "subject": subject,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._notification_rules[rule_id] = record
            self._audit(actor, "ext_notification_rule_create", rule_id,
                        details={"name": name, "trigger": trigger})
            return dict(record)

    def list_notification_rules(self, actor=None):
        """Return notification rules. Action: workflow_read."""
        if actor is not None:
            self._require_actor(actor, "workflow_read")
        with self._lock:
            return [dict(r) for r in self._notification_rules.values()]

    def evaluate_notification_rules(self, actor, as_of=None):
        """Evaluate rules deterministically and record transport receipts.

        Action: workflow_write. For each ``compliance_overdue``
        rule, one receipt per core assignment derived overdue at
        ``as_of`` whose learner matches the rule's recipient (or
        every overdue assignment when the rule's recipient is the
        literal ``*`` broadcast marker). Each receipt ALSO records a
        core notification record so the substrate's own registry
        shows it. Every receipt carries ``reference_transport:
        True`` and state ``recorded_reference_only`` — no email,
        SMS, or push is sent by this substrate, ever. Other triggers
        are recorded rules whose events live outside this evaluation
        pass; they create no receipts here.
        """
        self._require_actor(actor, "workflow_write")
        as_of_date = _coerce_as_of(as_of)
        created = []
        with self._lock:
            overdue = [v for v in self.store.list_compliance(
                actor=None, as_of=as_of_date) if v["status"] == "overdue"]
            for rule in self._notification_rules.values():
                if rule["trigger"] != "compliance_overdue":
                    continue
                for view in overdue:
                    if (rule["recipient_ref"] != "*"
                            and rule["recipient_ref"] != view["learner_ref"]):
                        continue
                    notification = self.store.record_notification(
                        view["learner_ref"], rule["subject"], actor,
                        body="", kind="compliance_overdue")
                    receipt_id = self._next_id("rcpt")
                    receipt = {
                        "id": receipt_id,
                        "rule_id": rule["id"],
                        "notification_id": notification["id"],
                        "recipient_ref": view["learner_ref"],
                        "assignment_id": view["id"],
                        "trigger": rule["trigger"],
                        "reference_transport": True,
                        "state": "recorded_reference_only",
                        "recorded_by": actor_name(actor),
                        "recorded_utc": _utc_now(),
                    }
                    self._notification_receipts[receipt_id] = receipt
                    self._audit(actor, "ext_notification_receipt_record",
                                receipt_id,
                                details={"rule_id": rule["id"],
                                         "assignment_id": view["id"],
                                         "reference_transport": True})
                    created.append(dict(receipt))
            return created

    def list_notification_receipts(self, actor=None, rule_id=None):
        """Return transport receipts. Action: workflow_read."""
        if actor is not None:
            self._require_actor(actor, "workflow_read")
        with self._lock:
            records = list(self._notification_receipts.values())
            if rule_id is not None:
                records = [r for r in records if r["rule_id"] == rule_id]
            return [dict(r) for r in records]

    # -- STUB: EHRI integration engine (labeled reference) ----------------

    def create_ehri_feed_record(self, period, actor, learner_refs=None):
        """Record an EHRI feed batch — labeled reference implementation.

        Action: compliance_write. ``period`` is ``YYYY-MM``. The
        record snapshots only a count and the opaque learner refs
        named by the caller; it carries ``reference_stub: True``.
        No feed is collected, transmitted, or reported anywhere.
        """
        self._require_actor(actor, "compliance_write")
        if not isinstance(period, str) or len(period) != 7 or period[4] != "-":
            raise ValidationError("period must be YYYY-MM: %r" % (period,))
        try:
            date.fromisoformat(period + "-01")
        except ValueError as exc:
            raise ValidationError("period must be YYYY-MM: %r" % (period,)) from exc
        learner_refs = list(learner_refs or [])
        for ref in learner_refs:
            _non_empty(ref, "learner_ref")
        with self._lock:
            known = {l["ref"] for l in self.store.list_learners()}
            for ref in learner_refs:
                if ref not in known:
                    raise NotFoundError("learner not found: %r" % (ref,))
            record_id = self._next_id("ehr")
            record = {
                "id": record_id,
                "period": period,
                "learner_refs": learner_refs,
                "learner_count": len(learner_refs),
                "reference_stub": True,
                "state": "recorded_reference_only",
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._ehri_records[record_id] = record
            self._audit(actor, "ext_ehri_feed_record", record_id,
                        details={"period": period, "reference_stub": True})
            copied = dict(record)
            copied["learner_refs"] = list(learner_refs)
            return copied

    def list_ehri_feed_records(self, actor=None):
        """Return EHRI feed records. Action: compliance_read."""
        if actor is not None:
            self._require_actor(actor, "compliance_read")
        with self._lock:
            result = []
            for record in self._ehri_records.values():
                copied = dict(record)
                copied["learner_refs"] = list(record["learner_refs"])
                result.append(copied)
            return result

    # -- STUB: content authoring tools & lesson-plan editor (reference) ---

    def create_authoring_draft(self, title, actor, lesson_plan_id=None,
                               sections=None):
        """Record an authoring draft — labeled reference implementation.

        Action: catalog_write. A draft is data (title, ordered
        section texts, optional core lesson-plan link); the editor
        that would compose it is not built. Every draft carries
        ``reference_stub: True``.
        """
        self._require_actor(actor, "catalog_write")
        _non_empty(title, "draft title")
        sections = _string_list(sections, "sections", allow_empty=True) \
            if sections else []
        with self._lock:
            if lesson_plan_id is not None:
                self.store.get_lesson_plan(lesson_plan_id, actor=None)
            draft_id = self._next_id("dft")
            record = {
                "id": draft_id,
                "title": title,
                "lesson_plan_id": lesson_plan_id,
                "revisions": [{"sections": list(sections),
                               "recorded_by": actor_name(actor),
                               "recorded_utc": _utc_now()}],
                "reference_stub": True,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._authoring_drafts[draft_id] = record
            self._audit(actor, "ext_authoring_draft_create", draft_id,
                        details={"title": title, "reference_stub": True})
            return self._draft_view(record)

    @staticmethod
    def _draft_view(record):
        return {
            "id": record["id"],
            "title": record["title"],
            "lesson_plan_id": record["lesson_plan_id"],
            "sections": list(record["revisions"][-1]["sections"]),
            "revision_count": len(record["revisions"]),
            "reference_stub": True,
            "state": record["state"],
            "created_by": record["created_by"],
            "created_utc": record["created_utc"],
        }

    def revise_authoring_draft(self, draft_id, sections, actor):
        """Append a draft revision. Action: catalog_write."""
        self._require_actor(actor, "catalog_write")
        sections = _string_list(sections, "sections", allow_empty=True)
        with self._lock:
            record = self._get(self._authoring_drafts, draft_id, "authoring draft")
            record["revisions"].append({
                "sections": list(sections), "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now()})
            self._audit(actor, "ext_authoring_draft_revise", draft_id,
                        details={"revision": len(record["revisions"])})
            return self._draft_view(record)

    def get_authoring_draft(self, draft_id, actor=None):
        """Return one draft view. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            return self._draft_view(
                self._get(self._authoring_drafts, draft_id, "authoring draft"))

    def list_authoring_drafts(self, actor=None):
        """Return draft views. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            return [self._draft_view(r) for r in self._authoring_drafts.values()]

    # -- STUB: SF-182 form rendering / routing / signature (reference) ----

    def create_form_workflow_record(self, authorization_id, actor, steps=None):
        """Record an SF-182 form workflow — labeled reference implementation.

        Action: authorization_write. The core authorization record
        and its recorded decision are the substance; this record
        holds the form's routing steps AS DATA (defaulting to
        render → route → sign). Nothing is rendered, routed, or
        signed. Every record carries ``reference_stub: True``.
        """
        self._require_actor(actor, "authorization_write")
        if steps is None:
            steps = ["render", "route", "sign"]
        steps = _string_list(steps, "steps")
        with self._lock:
            authorization = self.store.get_authorization(authorization_id,
                                                         actor=None)
            record_id = self._next_id("frm")
            record = {
                "id": record_id,
                "authorization_id": authorization_id,
                "learner_ref": authorization["learner_ref"],
                "authorization_state": authorization["state"],
                "steps": steps,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._form_workflows[record_id] = record
            self._audit(actor, "ext_form_workflow_record", record_id,
                        details={"authorization_id": authorization_id,
                                 "reference_stub": True})
            copied = dict(record)
            copied["steps"] = list(steps)
            return copied

    def list_form_workflow_records(self, actor=None, authorization_id=None):
        """Return form workflow records. Action: authorization_read."""
        if actor is not None:
            self._require_actor(actor, "authorization_read")
        with self._lock:
            records = list(self._form_workflows.values())
            if authorization_id is not None:
                records = [r for r in records
                           if r["authorization_id"] == authorization_id]
            result = []
            for record in records:
                copied = dict(record)
                copied["steps"] = list(record["steps"])
                result.append(copied)
            return result

    # -- STUB: workflow execution engine (reference; registry unchanged) --

    def create_execution_record(self, workflow_id, actor):
        """Record a would-be workflow execution — labeled reference.

        Action: workflow_write. The core workflow DEFINITION is
        copied as data into a reference record carrying
        ``reference_stub: True``. Executing nothing is the point:
        creating this record changes no core record and no other
        extension record — pinned by test, exactly as the core pins
        that registering a definition changes nothing.
        """
        self._require_actor(actor, "workflow_write")
        with self._lock:
            workflow = self.store.get_workflow(workflow_id, actor=None)
            record_id = self._next_id("exe")
            record = {
                "id": record_id,
                "workflow_id": workflow_id,
                "steps": list(workflow["steps"]),
                "reference_stub": True,
                "state": "recorded_reference_only",
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._execution_records[record_id] = record
            self._audit(actor, "ext_execution_record_create", record_id,
                        details={"workflow_id": workflow_id,
                                 "reference_stub": True})
            copied = dict(record)
            copied["steps"] = list(workflow["steps"])
            return copied

    def list_execution_records(self, actor=None, workflow_id=None):
        """Return execution records. Action: workflow_read."""
        if actor is not None:
            self._require_actor(actor, "workflow_read")
        with self._lock:
            records = list(self._execution_records.values())
            if workflow_id is not None:
                records = [r for r in records if r["workflow_id"] == workflow_id]
            result = []
            for record in records:
                copied = dict(record)
                copied["steps"] = list(record["steps"])
                result.append(copied)
            return result
