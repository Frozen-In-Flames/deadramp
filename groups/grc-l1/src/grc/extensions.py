"""Final-GAPS-batch extension surface for the GRC L1 core.

One new module, following the batch pattern in
``../../gaps-batch/DECISION.md``: :class:`GrcExtensions` wraps a
core :class:`grc.store.GrcStore` and adds records for the four
Extended functions registered under this group's GAPS.md section
(Singleton 43 — GRC L1, inventory idx 415–418). The core modules
are untouched.

The category doctrine binds every surface here, exactly as it
binds the core (see ``../UNION-SPEC.md`` and the core posture
tests): **posture is counts only — no computed score, rating,
grade, or percentage exists anywhere**, enforced over this
surface by the same recursive key scan the founding suite pins
(no key may contain ``score`` / ``rating`` / ``grade`` /
``percent`` — which is also why the boundary on the
reported-value records below is spelled ``computed_here``).
Statuses and outcomes a person or an external engine reports are
recorded **verbatim**, never computed. Anything date-based or
"latest"-shaped is **derived at read, never stored**.

Tier discipline: this group sits at the Low / L1 tier. The core's
plain append-only audit and its three-role matrix (admin /
member / viewer) are used unchanged — the Moderate/High apparatus
of the sibling tiers (hash-chained audit, lockout, auditor role)
is **not** inherited downward, and nothing in this module asserts
a baseline beyond the group's own spec.

What each engine-shaped entry becomes here (per-entry record in
``../BATCH.md``):

- **Questionnaire automation engine** (idx 415) — labeled
  reference implementation: questionnaire definition records
  holding the questions **as data** (``reference_stub: True``,
  ``administered_here: False``, ``reuse_applied_here: False`` —
  no prior answer is ever copied into a response by this build),
  and response records holding a respondent's answers verbatim
  as data, exactly as reported. Nothing administers a
  questionnaire, sends one, or reuses an answer here.
- **Trust Center publication** (idx 416) — *built* in
  publication-records form: a publication record stores **no
  figures at all** (requester, system, title, note, and the
  boundary labels ``published_here: False`` /
  ``exported_here: False``), release records hold a reported
  publication event verbatim, and the publication *view* is
  derived at read from the core's records — the system's
  posture counts (the core's own counts-only summary) plus
  release counts and the latest release label — so the view
  always tracks registry state while the stored record never
  gains a figure. No page is rendered, published, or exported;
  presenting the view on a customer-facing surface is the
  embedding organization's step, stated on the record. (The
  form mirrors the sibling GRC L2 unit's authorization-package
  records, idx 359, shipped.)
- **Vendor risk assessment engine** (idx 417) — labeled
  reference implementation in the category's adjudicated
  reported-value records form (sibling GRC L2 idx 357, GRC
  L3-adjacent idx 419/421, GRC untiered scoring surface):
  assessment-rule records hold a rule's text **as data**
  (``reference_stub: True``, ``method: recorded_rules_only``,
  ``applied_here: False`` — a rule is never applied to any
  record by this build), and vendor-assessment records hold an
  assessor's reported outcome and reported value **verbatim as
  labels** for a governed system (vendors are governed-system
  records in this substrate), carrying ``evaluated_here:
  False`` and ``computed_here: False``. This build evaluates no
  vendor and computes no value; aggregates over this surface
  are counts of the recorded labels only, and a vendor
  assessment creates no core finding.
- **Continuous-monitoring engine & evidence-collection
  integrations** (idx 418) — labeled reference implementation:
  collection-source records (definitions of API / telemetry
  sources an external engine connects through,
  ``reference_stub: True``, ``reference_transport: True``,
  ``connected_here: False``, ``collected_here: False``),
  monitoring-observation records (the intake of reported
  observations, ``monitored_here: False`` — an observation is
  recorded as reported, never produced by a check run here),
  and collection-run records holding what a collector reported
  (``collected_here: False``). Test-pinned boundaries: an
  observation creates **no** core indicator result and a
  collection run creates **no** core evidence record — core
  results and artifacts land through the core's own operations,
  by a person, exactly as the UNION-SPEC ruled.

Permissions ride the core's matrix unchanged (the same actions
the core enforces for the analogous records); reads require
``read``. Denied attempts raise :class:`PermissionDenied` and
change nothing — at this store-level surface, auditing a denial
is the HTTP layer's responsibility, exactly as in the core.
Successful extension mutations are written to the core's
append-only audit log (when one is attached) under ``ext_``
action names. Every operation validates fully before it
mutates: a failed operation consumes no id and changes nothing.
"""

import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, ValidationError

COLLECTION_KINDS = ("api", "telemetry")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_text(value, what):
    """Validate an optional free-text field (a string, may be empty)."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _validate_reported_count(value, what):
    """Validate a caller-reported count: an integer >= 0.

    Booleans and floats are rejected at the boundary: a reported
    count is a whole number a reporter supplied, never a computed
    quantity.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if value < 0:
        raise ValidationError("%s must be >= 0" % (what,))
    return value


def _validate_questions(value):
    """Validate a questionnaire's questions, held as data.

    The questions are a list of non-empty strings — the wording
    an external questionnaire engine would administer. They are
    data on the record, never a form this build renders or sends.
    """
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError("questions must be a list of strings")
    questions = []
    for question in value:
        _validate_non_empty(question, "question")
        questions.append(question)
    return questions


def _validate_answers(value):
    """Validate a response's answers, held verbatim as data.

    Answers are a mapping of question label to the respondent's
    answer text, recorded exactly as reported. Nothing here
    interprets, completes, or reuses an answer.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValidationError("answers must be a mapping of label to text")
    answers = {}
    for label, text in value.items():
        if not isinstance(label, str) or not label.strip():
            raise ValidationError("answer labels must be non-empty strings")
        if not isinstance(text, str):
            raise ValidationError("answer text must be a string")
        answers[label] = text
    return answers


def _counts_by_label(records, key):
    """Count records per verbatim label of ``key``, at read.

    Counts only: the helper tallies occurrences of labels that
    were recorded verbatim; it computes no value from the labels
    themselves.
    """
    counts = {}
    for record in records:
        label = record[key]
        counts[label] = counts.get(label, 0) + 1
    return counts


class GrcExtensions:
    """The final-GAPS-batch extension surface over a core store."""

    def __init__(self, store):
        self.store = store
        self.audit = store.audit
        self._questionnaires = {}  # id -> questionnaire definition record
        self._responses = {}  # id -> questionnaire response record
        self._publications = {}  # id -> trust center publication record
        self._releases = {}  # id -> publication release record
        self._vendor_rules = {}  # id -> vendor assessment rule record
        self._vendor_assessments = {}  # id -> vendor assessment record
        self._collection_sources = {}  # id -> collection source record
        self._observations = {}  # id -> monitoring observation record
        self._collection_runs = {}  # id -> collection run record
        self._counters = {
            "qnr": 0, "qrs": 0, "pub": 0, "prl": 0, "vru": 0,
            "vas": 0, "csrc": 0, "obs": 0, "crun": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers -------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    @staticmethod
    def _require(actor, action):
        require(actor, action)

    def _require_system(self, system_ref, actor):
        """Raise NotFoundError unless ``system_ref`` is governed."""
        self.store.get_system(system_ref, actor)

    @staticmethod
    def _get(table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    @staticmethod
    def _latest_label(records, key):
        """The ``key`` label of the most recently recorded record.

        The batch unit's derivation seam (see tests/README.md):
        views derive their "latest" label from the recorded
        stream at read; the value is never stored on any record.
        """
        return records[-1][key] if records else None

    # -- questionnaires (idx 415, reference) -------------------------

    def create_questionnaire(self, system_ref, title, actor, questions=None,
                             note=""):
        """Record a questionnaire definition as data.

        Reference implementation: the definition names the
        governed system it concerns and holds its questions as
        data. This build administers nothing and sends nothing
        (``administered_here: False``), and no answer reuse is
        ever applied by this build (``reuse_applied_here:
        False``) — reuse of prior answers is the external
        engine's automation, recorded here only as reported
        responses.
        """
        _validate_non_empty(title, "questionnaire title")
        questions = _validate_questions(questions)
        note = _validate_text(note, "questionnaire note")
        self._require(actor, "manage_assessments")
        with self._lock:
            self._require_system(system_ref, actor)
            questionnaire_id = self._next_id("qnr")
            record = {
                "id": questionnaire_id,
                "system_ref": system_ref,
                "title": title,
                "questions": questions,
                "note": note,
                "reference_stub": True,
                "administered_here": False,
                "reuse_applied_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._questionnaires[questionnaire_id] = record
            self._audit(actor, "ext_questionnaire_create", questionnaire_id,
                        details={"system_ref": system_ref})
            copied = dict(record)
            copied["questions"] = list(record["questions"])
            return copied

    def get_questionnaire(self, questionnaire_id, actor):
        """Return one questionnaire definition record."""
        self._require(actor, "read")
        with self._lock:
            record = self._get(
                self._questionnaires, questionnaire_id, "questionnaire")
            copied = dict(record)
            copied["questions"] = list(record["questions"])
            return copied

    def list_questionnaires(self, actor, system_ref=None):
        """Return questionnaire definition records, optionally
        filtered by governed system."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._questionnaires.values())
            if system_ref is not None:
                records = [
                    r for r in records if r["system_ref"] == system_ref]
            result = []
            for record in records:
                copied = dict(record)
                copied["questions"] = list(record["questions"])
                result.append(copied)
            return result

    def record_questionnaire_response(self, questionnaire_id, status, actor,
                                      respondent_ref="", answers=None,
                                      note=""):
        """Record one questionnaire response, verbatim as reported.

        ``status`` and the ``answers`` mapping are the responding
        party's own report, stored exactly as supplied; this
        build administered nothing and reused nothing
        (``administered_here: False``, ``reuse_applied_here:
        False`` on the definition; the response is a record of
        a report, not an act of this build).
        """
        _validate_non_empty(status, "response status")
        respondent_ref = _validate_text(respondent_ref, "respondent reference")
        answers = _validate_answers(answers)
        note = _validate_text(note, "response note")
        self._require(actor, "record_results")
        with self._lock:
            self._get(self._questionnaires, questionnaire_id, "questionnaire")
            response_id = self._next_id("qrs")
            record = {
                "id": response_id,
                "questionnaire_id": questionnaire_id,
                "status": status,
                "respondent_ref": respondent_ref,
                "answers": answers,
                "note": note,
                "reference_stub": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._responses[response_id] = record
            self._audit(actor, "ext_questionnaire_response_record", response_id,
                        details={"questionnaire_id": questionnaire_id})
            copied = dict(record)
            copied["answers"] = dict(record["answers"])
            return copied

    def list_questionnaire_responses(self, questionnaire_id, actor):
        """Return response records for one questionnaire."""
        self._require(actor, "read")
        with self._lock:
            self._get(self._questionnaires, questionnaire_id, "questionnaire")
            result = []
            for record in self._responses.values():
                if record["questionnaire_id"] == questionnaire_id:
                    copied = dict(record)
                    copied["answers"] = dict(record["answers"])
                    result.append(copied)
            return result

    def questionnaire_view(self, questionnaire_id, actor):
        """One questionnaire plus its derived response summary.

        The counts and the latest reported status are derived at
        read from the response records; the stored definition
        carries no derived key.
        """
        self._require(actor, "read")
        with self._lock:
            record = self._get(
                self._questionnaires, questionnaire_id, "questionnaire")
            responses = [
                r for r in self._responses.values()
                if r["questionnaire_id"] == questionnaire_id
            ]
            view = dict(record)
            view["questions"] = list(record["questions"])
            view["derived"] = True
            view["response_count"] = len(responses)
            view["responses_by_status"] = _counts_by_label(responses, "status")
            view["latest_response_status"] = self._latest_label(
                responses, "status")
            return view

    # -- trust center publications (idx 416, built) -------------------

    def create_publication(self, system_ref, title, actor, note=""):
        """Register a Trust Center publication record.

        The record stores **no figures at all**: it is the
        registry entry for publishing one governed system's
        security program description — who registered it, for
        which system, under what title. The published content
        is the view (see :meth:`publication_view`), derived at
        read from the core's records. Nothing is published or
        exported by this build (``published_here: False``,
        ``exported_here: False``): presenting the view on a
        customer-facing surface is the embedding organization's
        step.
        """
        _validate_non_empty(title, "publication title")
        note = _validate_text(note, "publication note")
        self._require(actor, "manage_assessments")
        with self._lock:
            self._require_system(system_ref, actor)
            publication_id = self._next_id("pub")
            record = {
                "id": publication_id,
                "system_ref": system_ref,
                "title": title,
                "note": note,
                "published_here": False,
                "exported_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._publications[publication_id] = record
            self._audit(actor, "ext_publication_create", publication_id,
                        details={"system_ref": system_ref})
            return dict(record)

    def get_publication(self, publication_id, actor):
        """Return one stored publication record (no figures)."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(
                self._publications, publication_id, "publication"))

    def list_publications(self, actor, system_ref=None):
        """Return publication records, optionally filtered by
        governed system."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._publications.values())
            if system_ref is not None:
                records = [
                    r for r in records if r["system_ref"] == system_ref]
            return [dict(r) for r in records]

    def record_publication_release(self, publication_id, label, actor,
                                   note=""):
        """Record one publication release event, verbatim.

        A release is the report that the publication's view was
        presented externally at a point in time; the ``label``
        (for example a version or channel label) is recorded
        exactly as reported. The presenting itself happened on
        the embedding organization's surface, not here
        (``published_here: False`` on the parent record).
        """
        _validate_non_empty(label, "release label")
        note = _validate_text(note, "release note")
        self._require(actor, "manage_assessments")
        with self._lock:
            self._get(self._publications, publication_id, "publication")
            release_id = self._next_id("prl")
            record = {
                "id": release_id,
                "publication_id": publication_id,
                "label": label,
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._releases[release_id] = record
            self._audit(actor, "ext_publication_release_record", release_id,
                        details={"publication_id": publication_id})
            return dict(record)

    def list_publication_releases(self, publication_id, actor):
        """Return release records for one publication."""
        self._require(actor, "read")
        with self._lock:
            self._get(self._publications, publication_id, "publication")
            return [
                dict(r) for r in self._releases.values()
                if r["publication_id"] == publication_id
            ]

    def publication_view(self, publication_id, actor, as_of=None):
        """The published view of one publication, derived at read.

        The view joins the stored publication record (which
        carries no figures) with the system's posture counts —
        the core's own counts-only summary, unmodified — and
        with release counts and the latest release label derived
        from the release records. Because everything is derived
        at read, the view tracks registry state: records added
        after the publication was registered appear in its next
        view, while the stored record never gains a figure.
        """
        self._require(actor, "read")
        with self._lock:
            record = self._get(
                self._publications, publication_id, "publication")
            system = self.store.get_system(record["system_ref"], actor)
            posture = self.store.posture_summary(actor, as_of=as_of)
            releases = [
                r for r in self._releases.values()
                if r["publication_id"] == publication_id
            ]
            view = dict(record)
            view["derived"] = True
            view["system_name"] = system["name"]
            view["posture"] = posture
            view["release_count"] = len(releases)
            view["latest_release_label"] = self._latest_label(
                releases, "label")
            return view

    # -- vendor risk assessment (idx 417, reference) -------------------

    def create_vendor_rule(self, title, rule_text, actor, system_ref=None,
                           note=""):
        """Record a vendor-assessment rule's text as data.

        Reference implementation: the rule is held verbatim as
        data (``method: recorded_rules_only``) and is **never
        applied** to any record by this build
        (``applied_here: False``) — applying an assessment rule
        to a vendor is the external engine's computation.
        """
        _validate_non_empty(title, "rule title")
        _validate_non_empty(rule_text, "rule text")
        note = _validate_text(note, "rule note")
        self._require(actor, "manage_assessments")
        with self._lock:
            if system_ref is not None:
                self._require_system(system_ref, actor)
            rule_id = self._next_id("vru")
            record = {
                "id": rule_id,
                "title": title,
                "rule_text": rule_text,
                "system_ref": system_ref,
                "note": note,
                "method": "recorded_rules_only",
                "reference_stub": True,
                "applied_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._vendor_rules[rule_id] = record
            self._audit(actor, "ext_vendor_rule_create", rule_id,
                        details={"system_ref": system_ref})
            return dict(record)

    def get_vendor_rule(self, rule_id, actor):
        """Return one vendor-assessment rule record."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(self._vendor_rules, rule_id, "vendor rule"))

    def list_vendor_rules(self, actor, system_ref=None):
        """Return vendor-assessment rule records, optionally
        filtered by governed system."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._vendor_rules.values())
            if system_ref is not None:
                records = [
                    r for r in records if r["system_ref"] == system_ref]
            return [dict(r) for r in records]

    def record_vendor_assessment(self, system_ref, outcome, actor,
                                 reported_label=None, assessor_ref="",
                                 rule_id=None, note=""):
        """Record one vendor assessment, verbatim as reported.

        The vendor is a governed-system record (the core registry
        holds vendors as governed parties, by opaque reference).
        ``outcome`` and the optional ``reported_label`` (the
        assessor's own value, in the assessor's own words) are
        stored exactly as reported: this build evaluates no
        vendor (``evaluated_here: False``) and computes no value
        (``computed_here: False``). Recording an assessment
        creates no core finding.
        """
        _validate_non_empty(outcome, "assessment outcome")
        if reported_label is not None:
            _validate_non_empty(reported_label, "reported label")
        assessor_ref = _validate_text(assessor_ref, "assessor reference")
        note = _validate_text(note, "assessment note")
        self._require(actor, "record_results")
        with self._lock:
            self._require_system(system_ref, actor)
            if rule_id is not None:
                self._get(self._vendor_rules, rule_id, "vendor rule")
            assessment_id = self._next_id("vas")
            record = {
                "id": assessment_id,
                "system_ref": system_ref,
                "outcome": outcome,
                "reported_label": reported_label,
                "assessor_ref": assessor_ref,
                "rule_id": rule_id,
                "note": note,
                "reference_stub": True,
                "evaluated_here": False,
                "computed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._vendor_assessments[assessment_id] = record
            self._audit(actor, "ext_vendor_assessment_record", assessment_id,
                        details={"system_ref": system_ref})
            return dict(record)

    def get_vendor_assessment(self, assessment_id, actor):
        """Return one vendor-assessment record."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(
                self._vendor_assessments, assessment_id, "vendor assessment"))

    def list_vendor_assessments(self, actor, system_ref=None):
        """Return vendor-assessment records, optionally filtered
        by governed system."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._vendor_assessments.values())
            if system_ref is not None:
                records = [
                    r for r in records if r["system_ref"] == system_ref]
            return [dict(r) for r in records]

    def vendor_assessment_summary(self, actor, system_ref=None):
        """Counts over the vendor-assessment surface, derived at
        read: assessments in total and per verbatim outcome
        label. Counts of recorded labels only — no value is
        aggregated, averaged, or computed."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._vendor_assessments.values())
            if system_ref is not None:
                records = [
                    r for r in records if r["system_ref"] == system_ref]
            return {
                "method": "deterministic_counts",
                "vendor_assessments_total": len(records),
                "by_outcome": _counts_by_label(records, "outcome"),
                "by_reported_label": _counts_by_label(
                    [r for r in records if r["reported_label"] is not None],
                    "reported_label"),
            }

    # -- monitoring & evidence collection (idx 418, reference) ---------

    def register_collection_source(self, kind, system_ref, label, actor,
                                   note=""):
        """Register a definition of an external collection source.

        Reference implementation: the record defines an API or
        telemetry source an external engine collects evidence
        or observations through. This build connects to nothing
        (``connected_here: False``) and collects nothing
        (``collected_here: False``); the definition is the
        registry entry the engine's reports are recorded
        against.
        """
        if kind not in COLLECTION_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(COLLECTION_KINDS),))
        _validate_non_empty(label, "source label")
        note = _validate_text(note, "source note")
        self._require(actor, "manage_indicators")
        with self._lock:
            self._require_system(system_ref, actor)
            source_id = self._next_id("csrc")
            record = {
                "id": source_id,
                "kind": kind,
                "system_ref": system_ref,
                "label": label,
                "note": note,
                "reference_stub": True,
                "reference_transport": True,
                "connected_here": False,
                "collected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._collection_sources[source_id] = record
            self._audit(actor, "ext_collection_source_create", source_id,
                        details={"system_ref": system_ref, "kind": kind})
            return dict(record)

    def get_collection_source(self, source_id, actor):
        """Return one collection-source definition record."""
        self._require(actor, "read")
        with self._lock:
            return dict(self._get(
                self._collection_sources, source_id, "collection source"))

    def list_collection_sources(self, actor, system_ref=None):
        """Return collection-source definition records,
        optionally filtered by governed system."""
        self._require(actor, "read")
        with self._lock:
            records = list(self._collection_sources.values())
            if system_ref is not None:
                records = [
                    r for r in records if r["system_ref"] == system_ref]
            return [dict(r) for r in records]

    def record_monitoring_observation(self, source_id, status, actor,
                                      control_id=None, note=""):
        """Record one monitoring observation, verbatim as reported.

        This is the continuous-monitoring **intake**: a record
        of what an external monitoring engine reported observing
        (its ``status``, in its own words, optionally against a
        catalog control — validated against the registry). This
        build monitors nothing (``monitored_here: False``): the
        observation is recorded, never produced by a check run
        here, and it creates **no** core indicator result — core
        results are recorded through the core's own operation,
        by a person.
        """
        _validate_non_empty(status, "observation status")
        note = _validate_text(note, "observation note")
        self._require(actor, "record_results")
        with self._lock:
            source = self._get(
                self._collection_sources, source_id, "collection source")
            if control_id is not None:
                known = {
                    control["id"] for control in self.store.list_controls(actor)
                }
                if control_id not in known:
                    raise ValidationError(
                        "unknown control id: %r" % (control_id,))
            observation_id = self._next_id("obs")
            record = {
                "id": observation_id,
                "source_id": source_id,
                "system_ref": source["system_ref"],
                "control_id": control_id,
                "status": status,
                "note": note,
                "reference_stub": True,
                "monitored_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._observations[observation_id] = record
            self._audit(actor, "ext_monitoring_observation_record",
                        observation_id, details={"source_id": source_id})
            return dict(record)

    def list_monitoring_observations(self, source_id, actor):
        """Return observation records for one collection source."""
        self._require(actor, "read")
        with self._lock:
            self._get(self._collection_sources, source_id, "collection source")
            return [
                dict(r) for r in self._observations.values()
                if r["source_id"] == source_id
            ]

    def record_collection_run(self, source_id, status, actor,
                              artifact_count=0, note=""):
        """Record one evidence-collection run, verbatim as
        reported.

        ``artifact_count`` is the collector's own reported count
        of artifacts it collected (a whole number it supplied;
        booleans, floats, and negatives are rejected). This
        build collected nothing (``collected_here: False``) and
        the run creates **no** core evidence record: artifacts
        land in the core registry through the core's own
        operation, filed by a person.
        """
        _validate_non_empty(status, "collection run status")
        artifact_count = _validate_reported_count(
            artifact_count, "artifact count")
        note = _validate_text(note, "collection run note")
        self._require(actor, "manage_evidence")
        with self._lock:
            self._get(self._collection_sources, source_id, "collection source")
            run_id = self._next_id("crun")
            record = {
                "id": run_id,
                "source_id": source_id,
                "status": status,
                "artifact_count": artifact_count,
                "note": note,
                "reference_stub": True,
                "reference_transport": True,
                "collected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._collection_runs[run_id] = record
            self._audit(actor, "ext_collection_run_record", run_id,
                        details={"source_id": source_id})
            return dict(record)

    def list_collection_runs(self, source_id, actor):
        """Return collection-run records for one source."""
        self._require(actor, "read")
        with self._lock:
            self._get(self._collection_sources, source_id, "collection source")
            return [
                dict(r) for r in self._collection_runs.values()
                if r["source_id"] == source_id
            ]

    def collection_source_view(self, source_id, actor):
        """One collection source plus its derived intake summary.

        Observation and run counts, the observations' verbatim
        status counts, the summed *reported* artifact counts,
        and the latest reported observation status are derived
        at read from the intake records; the stored definition
        carries no derived key.
        """
        self._require(actor, "read")
        with self._lock:
            record = self._get(
                self._collection_sources, source_id, "collection source")
            observations = [
                r for r in self._observations.values()
                if r["source_id"] == source_id
            ]
            runs = [
                r for r in self._collection_runs.values()
                if r["source_id"] == source_id
            ]
            view = dict(record)
            view["derived"] = True
            view["observation_count"] = len(observations)
            view["observations_by_status"] = _counts_by_label(
                observations, "status")
            view["latest_observation_status"] = self._latest_label(
                observations, "status")
            view["collection_run_count"] = len(runs)
            view["reported_artifacts_total"] = sum(
                r["artifact_count"] for r in runs)
            return view

    # -- cross-surface summary ------------------------------------------

    def extension_summary(self, actor):
        """Counts over the whole extension surface, derived at
        read. Counts only, in the core posture's own discipline:
        no value is computed from any recorded label."""
        self._require(actor, "read")
        with self._lock:
            return {
                "method": "deterministic_counts",
                "questionnaires": {
                    "total": len(self._questionnaires),
                    "responses_total": len(self._responses),
                    "responses_by_status": _counts_by_label(
                        list(self._responses.values()), "status"),
                },
                "publications": {
                    "total": len(self._publications),
                    "releases_total": len(self._releases),
                },
                "vendor": {
                    "rules_total": len(self._vendor_rules),
                    "assessments_total": len(self._vendor_assessments),
                    "assessments_by_outcome": _counts_by_label(
                        list(self._vendor_assessments.values()), "outcome"),
                },
                "monitoring": {
                    "sources_total": len(self._collection_sources),
                    "observations_total": len(self._observations),
                    "observations_by_status": _counts_by_label(
                        list(self._observations.values()), "status"),
                    "collection_runs_total": len(self._collection_runs),
                },
            }
