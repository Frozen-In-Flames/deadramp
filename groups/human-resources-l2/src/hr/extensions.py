"""Final GAPS batch extensions for the Human Resources L2 build.

Clean-room, standard-library-only extensions for the 16 open Extended
entries of Group 21 (see ``BATCH.md`` in the group directory for the
per-entry disposition). This module is a wrapper around
:class:`HrStore`; every core module is untouched.

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form -- records plus deterministic derivations over the
group's OWN records.

- Matching, classification recommendation, workforce planning, and
  mobility matching are deterministic derivations over held records,
  labeled with their method; the rule or criteria behind each
  derivation are themselves records (a match rule, a classification
  reference, a planning scenario), so the inputs and the rule are
  inspectable from the records. Nothing is a learned model and no
  derivation hides a ranking: match views return their evidence per
  candidate, in application-id order.
- The weighted cumulative / consensus scoring entry is built in the
  only form the founding design permits. Core 5 stores human ratings
  verbatim and has NO aggregate field by design; the extension
  therefore computes at read time only, over the verbatim entries,
  with the weights recorded as data on a crediting-plan record (the
  job-analysis entry). The computed view is never stored, never
  written back onto an evaluation, a rating, or a person record, and
  no stored record anywhere in this surface carries an aggregate
  key -- pinned by test.
- The retirement benefits calculator is integer arithmetic over
  recorded inputs (service months against recorded plan accrual
  parameters), derived at read, paying nothing. It computes the
  accrual side exactly and no currency amount: converting an accrual
  fraction into money requires the member's pay figure, and no field
  in this build can hold a pay figure (the group's structural
  privacy rule), so the substrate states the boundary rather than
  smuggling the figure in.
- Anything that would post, sync, deliver, host, or execute against
  an external system ships as a labeled reference record instead:
  stub-engine records carry ``reference_stub: True`` (transport
  receipts also ``reference_transport: True``) and state
  ``recorded_reference_only``. Creating one changes no core record;
  pinned by test.

Doctrines carried from the core: opaque ``*_ref`` strings only (no
record shape here can hold a real name, SSN, DOB, salary, address,
phone, or email -- the same forbidden-key set the core privacy tests
use is pinned over these shapes too); derived-never-stored for every
computed value (match views, classification recommendations and
comparisons, score views, certificate entry views, program and
learning summaries, workforce analytics, scenario projections,
retirement estimates); append-only audit on the core store's log
with ``ext_``-prefixed actions for every successful extension
mutation (denied operations record nothing, the store-level
convention -- denial auditing lives in the service layer); RBAC via
:mod:`hr.access` with the core's existing actions, enforced before
any state change or id allocation, so a failed operation consumes
no id and changes nothing; employee scope mirrors the store's -- an
employee-role actor reads only views over their own records.

RBAC action mapping (the core action set is fixed): hiring-chain
extension records ride the application family; classification-side
configuration (references, job analyses, mobility listings, planning
scenarios) rides the position family; crediting plans and scoring
views ride the evaluation family; talent-development records
(programs, courses, assignments) ride the performance family;
retirement parameters and estimates ride the benefits family;
template and administrative reference records (connectors, sync and
hosting records) ride the case family; outreach records (career
sites, communities, events) ride the vacancy family; aggregate
analytics views require ``report_read``, as in the core report.
"""

import copy
import threading
from datetime import date, datetime, timezone
from fractions import Fraction

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

MATCH_STAGES_DEFAULT = (
    "applied", "screened", "referred", "selected", "not_selected", "withdrawn",
)
LISTING_KINDS = ("detail", "rotation", "exchange")
LISTING_STATES = ("open", "closed")
PROGRAM_KINDS = ("retention", "development", "mentoring")
ENROLLMENT_STATES = ("enrolled", "completed", "withdrawn")
LEARNING_STATES = ("assigned", "in_progress", "completed")
SITE_STATES = ("draft", "published", "archived")
EVENT_STATES = ("scheduled", "held", "cancelled")
CONNECTOR_DIRECTIONS = ("inbound", "outbound", "bidirectional")
TEMPLATE_SOURCES = {
    "position": ("id", "title", "series", "grade", "organization", "status"),
    "vacancy": ("id", "title", "status", "opens_on", "closes_on"),
}

# The core privacy test's forbidden-key set (tests/test_privacy.py):
# no extension record shape may carry any of these keys either.
FORBIDDEN_KEYS = {
    "name", "ssn", "social_security_number", "salary", "compensation",
    "pay", "dob", "date_of_birth", "address", "phone", "email",
}
# Aggregate keys are forbidden on every STORED extension record: the
# scoring computation's results are derived views, never stored.
AGGREGATE_KEYS = {
    "score", "average", "aggregate", "mean", "weighted_cumulative",
    "consensus", "consensus_spread", "total_rating",
}


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_string(value, what):
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _validate_int(value, what, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if minimum is not None and value < minimum:
        raise ValidationError("%s must be at least %d" % (what, minimum))
    if maximum is not None and value > maximum:
        raise ValidationError("%s must be at most %d" % (what, maximum))
    return value


def _validate_date(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO date string (YYYY-MM-DD)" % (what,))
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO date: %r" % (what, value)) from exc


def _maybe_require(actor, action):
    """Enforce permissions when ``actor`` is a User-like object."""
    if actor is not None and hasattr(actor, "role"):
        require(actor, action)


def _require_actor(actor, action):
    """For writes: an actor must be present, then _maybe_require."""
    if actor is None:
        raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
    _maybe_require(actor, action)


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class HrExtensions:
    """Extension surface over an :class:`HrStore` (final GAPS batch)."""

    def __init__(self, store):
        self.store = store
        self._match_rules = {}
        self._classification_refs = {}
        self._job_analyses = {}
        self._crediting_plans = {}
        self._certificates = {}
        self._career_sites = {}
        self._communities = {}
        self._community_members = {}
        self._events = {}
        self._event_registrations = {}
        self._listings = {}
        self._interests = {}
        self._programs = {}
        self._enrollments = {}
        self._scenarios = {}
        self._retirement_params = {}
        self._courses = {}
        self._learning = {}
        self._templates = {}
        self._documents = {}
        self._workflows = {}
        self._postings = {}
        self._assessment_content = {}
        self._assessment_deliveries = {}
        self._connectors = {}
        self._syncs = {}
        self._hosting = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self.store, "audit", None)
        if audit is not None:
            audit.record(actor_name(actor), "ext_" + action, target, details=details)

    @staticmethod
    def _is_employee(actor):
        return actor is not None and getattr(actor, "role", None) == "employee"

    def _scope_check(self, actor, person_ref):
        if self._is_employee(actor) and getattr(actor, "name", None) != person_ref:
            raise PermissionDenied(
                "permission denied: employee %r may not access records of person %r"
                % (getattr(actor, "name", None), person_ref)
            )

    def _scoped(self, actor, records):
        if self._is_employee(actor):
            name = getattr(actor, "name", None)
            return [r for r in records if r.get("person_ref") == name]
        return list(records)

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    def _person_exists(self, person_ref):
        return any(
            p["person_ref"] == person_ref
            for p in self.store.list_persons(actor=None)
        )

    def _require_person_ref(self, person_ref):
        if not self._person_exists(person_ref):
            raise NotFoundError("person not found: %r" % (person_ref,))

    def _panel_stats(self, application_id):
        """(panel entry count, any panel evaluation completed) for an
        application, read from the core evaluation records."""
        entries = 0
        completed = False
        for evaluation in self.store.list_evaluations(
            actor=None, application_id=application_id
        ):
            if evaluation["kind"] != "panel":
                continue
            entries += len(evaluation["entries"])
            if evaluation["state"] == "completed":
                completed = True
        return entries, completed

    def _evaluation_application(self, evaluation_id):
        evaluation = self.store.get_evaluation(evaluation_id, actor=None)
        application = self.store.get_application(evaluation["application_id"], actor=None)
        return evaluation, application

    # -- AI talent intelligence & matching engines ---------------------
    # Deterministic rule matching over the core records: the rule is
    # a record; the evaluation is a derived view carrying its
    # evidence per candidate. No learned model, no hidden ranking.

    def create_match_rule(self, vacancy_id, actor, min_panel_entries=0,
                          stages=None, require_completed_panel=False):
        """Create a candidate-match rule record for a vacancy.

        Action: application_write. The vacancy must exist.
        ``min_panel_entries`` is a non-negative integer threshold over
        the verbatim panel entries recorded on a candidate's panel
        evaluations; ``stages`` restricts the application stages
        considered (default: every stage).
        """
        _require_actor(actor, "application_write")
        _validate_int(min_panel_entries, "min_panel_entries", minimum=0)
        if not isinstance(require_completed_panel, bool):
            raise ValidationError("require_completed_panel must be a boolean")
        if stages is None:
            stage_list = list(MATCH_STAGES_DEFAULT)
        else:
            if not isinstance(stages, (list, tuple)) or not stages:
                raise ValidationError("stages must be a non-empty list")
            from .store import APPLICATION_STAGES
            for stage in stages:
                if stage not in APPLICATION_STAGES:
                    raise ValidationError(
                        "stage must be one of %s" % (", ".join(APPLICATION_STAGES),)
                    )
            stage_list = list(stages)
        with self._lock:
            self.store.get_vacancy(vacancy_id, actor=None)
            rule_id = self._next_id("mtr")
            record = {
                "id": rule_id,
                "vacancy_id": vacancy_id,
                "min_panel_entries": min_panel_entries,
                "stages": stage_list,
                "require_completed_panel": require_completed_panel,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._match_rules[rule_id] = record
            self._audit(actor, "match_rule_create", rule_id,
                        details={"vacancy_id": vacancy_id})
            return copy.deepcopy(record)

    def get_match_rule(self, rule_id, actor=None):
        """Return one match rule record. Action: application_read."""
        _maybe_require(actor, "application_read")
        with self._lock:
            record = self._match_rules.get(rule_id)
            if record is None:
                raise NotFoundError("match rule not found: %r" % (rule_id,))
            return copy.deepcopy(record)

    def list_match_rules(self, actor=None, vacancy_id=None):
        """Return match rule records. Action: application_read."""
        _maybe_require(actor, "application_read")
        with self._lock:
            records = list(self._match_rules.values())
            if vacancy_id is not None:
                records = [r for r in records if r["vacancy_id"] == vacancy_id]
            return [copy.deepcopy(r) for r in self._sorted(records)]

    def evaluate_match_rule(self, rule_id, actor=None):
        """Derive the candidates matching a rule. Never stored.

        Action: application_read. A candidate matches when their
        application to the rule's vacancy is in one of the rule's
        stages, the verbatim panel entries on their panel evaluations
        number at least the rule's threshold, and -- when the rule
        requires it -- at least one panel evaluation is completed.
        Every row carries the evidence the decision rests on; rows
        are in application-id order (no ranking). Employee actors see
        only their own rows. Method: ``deterministic_rule_match``.
        """
        _maybe_require(actor, "application_read")
        with self._lock:
            rule = self._match_rules.get(rule_id)
            if rule is None:
                raise NotFoundError("match rule not found: %r" % (rule_id,))
            matches = []
            applications = self.store.list_applications(
                actor=None, vacancy_id=rule["vacancy_id"]
            )
            for application in self._sorted(applications):
                if application["stage"] not in rule["stages"]:
                    continue
                entry_count, panel_completed = self._panel_stats(application["id"])
                if entry_count < rule["min_panel_entries"]:
                    continue
                if rule["require_completed_panel"] and not panel_completed:
                    continue
                matches.append({
                    "person_ref": application["person_ref"],
                    "application_id": application["id"],
                    "stage": application["stage"],
                    "panel_entry_count": entry_count,
                    "panel_completed": panel_completed,
                })
            matches = self._scoped(actor, matches)
            return {
                "rule_id": rule_id,
                "vacancy_id": rule["vacancy_id"],
                "method": "deterministic_rule_match",
                "derived": True,
                "stored": False,
                "matches": matches,
                "match_count": len(matches),
            }

    # -- Position classification intelligence ---------------------------
    # A classification reference library (records) plus a keyword
    # derivation over a position's recorded title. The recommendation
    # is a derived view returning every match with the keywords it
    # matched on; nothing is written onto the position record.

    def create_classification_reference(self, series, grade, title_keywords, actor):
        """Create a classification-library reference record.

        Action: position_write. ``title_keywords`` is a non-empty
        list of non-empty strings; a position title matches the
        reference when any keyword appears in it (case-insensitive
        substring).
        """
        _require_actor(actor, "position_write")
        _validate_non_empty(series, "series")
        _validate_non_empty(grade, "grade")
        if not isinstance(title_keywords, (list, tuple)) or not title_keywords:
            raise ValidationError("title_keywords must be a non-empty list")
        keywords = []
        for keyword in title_keywords:
            _validate_non_empty(keyword, "title keyword")
            keywords.append(keyword)
        with self._lock:
            ref_id = self._next_id("clr")
            record = {
                "id": ref_id,
                "series": series,
                "grade": grade,
                "title_keywords": keywords,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._classification_refs[ref_id] = record
            self._audit(actor, "classification_reference_create", ref_id,
                        details={"series": series, "grade": grade})
            return copy.deepcopy(record)

    def list_classification_references(self, actor=None):
        """Return classification reference records. Action: position_read."""
        _maybe_require(actor, "position_read")
        with self._lock:
            return [copy.deepcopy(r) for r in self._sorted(self._classification_refs.values())]

    def _classification_matches(self, position):
        title = position["title"].lower()
        matches = []
        for reference in self._sorted(self._classification_refs.values()):
            matched = [k for k in reference["title_keywords"] if k.lower() in title]
            if matched:
                matches.append({
                    "reference_id": reference["id"],
                    "series": reference["series"],
                    "grade": reference["grade"],
                    "matched_keywords": matched,
                })
        matches.sort(key=lambda m: (-len(m["matched_keywords"]), _id_num(m["reference_id"])))
        return matches

    def recommend_classification(self, position_id, actor=None):
        """Derive a series/grade recommendation for a position.

        Action: position_read. Deterministic keyword match of the
        position's recorded title against the classification
        reference library; the view returns every matching reference
        with its matched keywords, ordered by keyword-count then
        reference id, and ``recommended`` is the first match (or
        None). Method: ``deterministic_keyword_match``. The position
        record is never modified. Never stored.
        """
        _maybe_require(actor, "position_read")
        with self._lock:
            position = self.store.get_position(position_id, actor=None)
            matches = self._classification_matches(position)
            return {
                "position_id": position_id,
                "method": "deterministic_keyword_match",
                "derived": True,
                "stored": False,
                "matches": matches,
                "recommended": matches[0] if matches else None,
            }

    def classification_comparison(self, position_id, actor=None):
        """Derive whether a position's recorded classification agrees
        with the library recommendation. Action: position_read.
        Never stored."""
        _maybe_require(actor, "position_read")
        with self._lock:
            position = self.store.get_position(position_id, actor=None)
            matches = self._classification_matches(position)
            recommended = matches[0] if matches else None
            agrees = None
            if recommended is not None:
                agrees = (
                    recommended["series"] == position["series"]
                    and recommended["grade"] == position["grade"]
                )
            return {
                "position_id": position_id,
                "method": "deterministic_keyword_match",
                "derived": True,
                "stored": False,
                "recorded_series": position["series"],
                "recorded_grade": position["grade"],
                "recommended_series": recommended["series"] if recommended else None,
                "recommended_grade": recommended["grade"] if recommended else None,
                "agrees": agrees,
            }

    # -- Job analysis & crediting-plan tooling ---------------------------

    def create_job_analysis(self, position_id, competencies, actor):
        """Create a job-analysis record for a position.

        Action: position_write. The position must exist.
        ``competencies`` is a non-empty list of
        ``{competency_ref, description, level_label}`` entries; the
        level is a recorded label only, never interpreted
        numerically.
        """
        _require_actor(actor, "position_write")
        if not isinstance(competencies, (list, tuple)) or not competencies:
            raise ValidationError("competencies must be a non-empty list")
        cleaned = []
        seen = set()
        for entry in competencies:
            if not isinstance(entry, dict):
                raise ValidationError("each competency must be an object")
            ref = _validate_non_empty(entry.get("competency_ref"), "competency_ref")
            description = _validate_string(entry.get("description", ""), "description")
            level_label = _validate_non_empty(entry.get("level_label"), "level_label")
            if ref in seen:
                raise ValidationError("duplicate competency_ref: %r" % (ref,))
            seen.add(ref)
            cleaned.append({
                "competency_ref": ref,
                "description": description,
                "level_label": level_label,
            })
        with self._lock:
            self.store.get_position(position_id, actor=None)
            analysis_id = self._next_id("jan")
            record = {
                "id": analysis_id,
                "position_id": position_id,
                "competencies": cleaned,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._job_analyses[analysis_id] = record
            self._audit(actor, "job_analysis_create", analysis_id,
                        details={"position_id": position_id})
            return copy.deepcopy(record)

    def get_job_analysis(self, analysis_id, actor=None):
        """Return one job-analysis record. Action: position_read."""
        _maybe_require(actor, "position_read")
        with self._lock:
            record = self._job_analyses.get(analysis_id)
            if record is None:
                raise NotFoundError("job analysis not found: %r" % (analysis_id,))
            return copy.deepcopy(record)

    def list_job_analyses(self, actor=None, position_id=None):
        """Return job-analysis records. Action: position_read."""
        _maybe_require(actor, "position_read")
        with self._lock:
            records = list(self._job_analyses.values())
            if position_id is not None:
                records = [r for r in records if r["position_id"] == position_id]
            return [copy.deepcopy(r) for r in self._sorted(records)]

    def create_crediting_plan(self, vacancy_id, criteria, actor):
        """Create a crediting-plan record for a vacancy.

        Action: evaluation_write. ``criteria`` is a non-empty list of
        ``{evaluation_id, weight}`` entries: each evaluation must
        exist, be a panel evaluation, and belong (through its
        application) to this vacancy; each weight is a positive
        integer and the weights must sum to exactly 100. The weights
        are recorded as data -- they are the inspectable rule the
        scoring view computes with.
        """
        _require_actor(actor, "evaluation_write")
        if not isinstance(criteria, (list, tuple)) or not criteria:
            raise ValidationError("criteria must be a non-empty list")
        cleaned = []
        seen = set()
        total = 0
        for entry in criteria:
            if not isinstance(entry, dict):
                raise ValidationError("each criterion must be an object")
            evaluation_id = _validate_non_empty(entry.get("evaluation_id"), "evaluation_id")
            weight = _validate_int(entry.get("weight"), "weight", minimum=1)
            if evaluation_id in seen:
                raise ValidationError("duplicate evaluation_id: %r" % (evaluation_id,))
            seen.add(evaluation_id)
            total += weight
            cleaned.append({"evaluation_id": evaluation_id, "weight": weight})
        if total != 100:
            raise ValidationError("criterion weights must sum to 100 (got %d)" % (total,))
        with self._lock:
            self.store.get_vacancy(vacancy_id, actor=None)
            for criterion in cleaned:
                evaluation, application = self._evaluation_application(
                    criterion["evaluation_id"]
                )
                if evaluation["kind"] != "panel":
                    raise ValidationError(
                        "crediting-plan criteria must be panel evaluations: %r"
                        % (criterion["evaluation_id"],)
                    )
                if application["vacancy_id"] != vacancy_id:
                    raise ValidationError(
                        "evaluation %r does not belong to vacancy %r"
                        % (criterion["evaluation_id"], vacancy_id)
                    )
            plan_id = self._next_id("crp")
            record = {
                "id": plan_id,
                "vacancy_id": vacancy_id,
                "criteria": cleaned,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._crediting_plans[plan_id] = record
            self._audit(actor, "crediting_plan_create", plan_id,
                        details={"vacancy_id": vacancy_id})
            return copy.deepcopy(record)

    def get_crediting_plan(self, plan_id, actor=None):
        """Return one crediting-plan record. Action: evaluation_read."""
        _maybe_require(actor, "evaluation_read")
        with self._lock:
            record = self._crediting_plans.get(plan_id)
            if record is None:
                raise NotFoundError("crediting plan not found: %r" % (plan_id,))
            return copy.deepcopy(record)

    def list_crediting_plans(self, actor=None, vacancy_id=None):
        """Return crediting-plan records. Action: evaluation_read."""
        _maybe_require(actor, "evaluation_read")
        with self._lock:
            records = list(self._crediting_plans.values())
            if vacancy_id is not None:
                records = [r for r in records if r["vacancy_id"] == vacancy_id]
            return [copy.deepcopy(r) for r in self._sorted(records)]

    # -- Weighted cumulative & consensus scoring computation -------------
    # Derived at read over the verbatim rater entries, with weights
    # recorded as data on the crediting plan. The result is a view:
    # it is never stored, and computing it changes no record. Exact
    # arithmetic: ratings are read as their decimal representation
    # and carried as Fractions, so a view's values are exact.

    @staticmethod
    def _ratings_of(evaluation):
        return [Fraction(str(entry["rating"])) for entry in evaluation["entries"]]

    @staticmethod
    def _mean(values):
        if not values:
            return None
        return sum(values, Fraction(0)) / len(values)

    def _weighted_cumulative(self, weighted_means):
        """The weighted cumulative seam: sum(weight * mean) over the
        criteria, divided by the sum of the weights.

        MUTATION DRILL NOTE: this seam is the load-bearing invariant
        of the batch's fresh negative control -- the recorded weights
        must actually weight the result. An implementation that
        ignores the weights (a plain mean of criterion means) is the
        mutant the drill and ``test_gaps_batch.py`` reject.
        """
        total = sum((weight * mean for weight, mean in weighted_means), Fraction(0))
        weight_sum = sum(weight for weight, _ in weighted_means)
        return total / weight_sum

    def panel_score_view(self, crediting_plan_id, actor=None):
        """Derive the weighted cumulative score view for a plan.

        Action: evaluation_read. For each criterion, the criterion
        mean is the exact mean of that panel evaluation's verbatim
        ratings; the weighted cumulative combines the criterion
        means with the plan's recorded weights. A criterion whose
        panel has no entries yet contributes ``criterion_mean: None``
        and is excluded from the combination (named in
        ``pending_criteria``); if no criterion has entries, the
        weighted cumulative is None. Employee actors are denied
        unless every criterion's application is their own. The view
        is computed at read and stored nowhere; the underlying
        evaluation records are returned unchanged.
        """
        _maybe_require(actor, "evaluation_read")
        with self._lock:
            plan = self._crediting_plans.get(crediting_plan_id)
            if plan is None:
                raise NotFoundError("crediting plan not found: %r" % (crediting_plan_id,))
            criteria_views = []
            weighted_means = []
            pending = []
            for criterion in plan["criteria"]:
                evaluation, application = self._evaluation_application(
                    criterion["evaluation_id"]
                )
                if self._is_employee(actor):
                    self._scope_check(actor, application["person_ref"])
                ratings = self._ratings_of(evaluation)
                mean = self._mean(ratings)
                criteria_views.append({
                    "evaluation_id": criterion["evaluation_id"],
                    "application_id": application["id"],
                    "weight": criterion["weight"],
                    "rater_count": len(ratings),
                    "ratings": [entry["rating"] for entry in evaluation["entries"]],
                    "criterion_mean": mean,
                })
                if mean is None:
                    pending.append(criterion["evaluation_id"])
                else:
                    weighted_means.append((criterion["weight"], mean))
            return {
                "crediting_plan_id": crediting_plan_id,
                "vacancy_id": plan["vacancy_id"],
                "method": "weighted_mean_of_verbatim_ratings",
                "derived": True,
                "stored": False,
                "criteria": criteria_views,
                "pending_criteria": pending,
                "weighted_cumulative": (
                    self._weighted_cumulative(weighted_means) if weighted_means else None
                ),
            }

    def panel_consensus_view(self, evaluation_id, actor=None):
        """Derive the consensus view for one panel evaluation.

        Action: evaluation_read (+ employee scope through the
        application's person_ref). The view carries the verbatim
        ratings, their exact mean, and the consensus spread
        (max - min) -- all computed at read, stored nowhere.
        """
        _maybe_require(actor, "evaluation_read")
        with self._lock:
            evaluation, application = self._evaluation_application(evaluation_id)
            if evaluation["kind"] != "panel":
                raise ValidationError(
                    "consensus view is defined for panel evaluations: %r" % (evaluation_id,)
                )
            self._scope_check(actor, application["person_ref"])
            ratings = self._ratings_of(evaluation)
            spread = None
            if ratings:
                spread = max(ratings) - min(ratings)
            return {
                "evaluation_id": evaluation_id,
                "application_id": application["id"],
                "method": "verbatim_ratings_mean_and_spread",
                "derived": True,
                "stored": False,
                "rater_count": len(ratings),
                "ratings": [entry["rating"] for entry in evaluation["entries"]],
                "mean": self._mean(ratings),
                "consensus_spread": spread,
            }

    # -- Certificates of eligibles (assembled documents) ------------------
    # The referral stage is Core; the assembled certificate document
    # is an extension record. Assembly derives the referred
    # applications at assembly time and stores their ids as the
    # document's content; person_refs and the count are derived at
    # read from the core application records.

    def assemble_certificate(self, vacancy_id, actor):
        """Assemble a certificate-of-eligibles document record.

        Action: application_write. The vacancy must exist. The
        document's entries are the vacancy's applications currently
        at the ``referred`` stage, in application-id order.
        """
        _require_actor(actor, "application_write")
        with self._lock:
            self.store.get_vacancy(vacancy_id, actor=None)
            applications = self.store.list_applications(actor=None, vacancy_id=vacancy_id)
            referred = [
                a for a in self._sorted(applications) if a["stage"] == "referred"
            ]
            cert_id = self._next_id("crt")
            record = {
                "id": cert_id,
                "vacancy_id": vacancy_id,
                "application_ids": [a["id"] for a in referred],
                "annotations": [],
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._certificates[cert_id] = record
            self._audit(actor, "certificate_assemble", cert_id,
                        details={"vacancy_id": vacancy_id,
                                 "entries": len(referred)})
            return copy.deepcopy(record)

    def annotate_certificate(self, certificate_id, note, actor):
        """Append an annotation to a certificate document record.

        Action: application_write. Annotations are append-only.
        """
        _require_actor(actor, "application_write")
        _validate_non_empty(note, "note")
        with self._lock:
            record = self._certificates.get(certificate_id)
            if record is None:
                raise NotFoundError("certificate not found: %r" % (certificate_id,))
            record["annotations"].append({
                "note": note,
                "by": actor_name(actor),
                "utc": _utc_now(),
            })
            self._audit(actor, "certificate_annotate", certificate_id, details={})
            return copy.deepcopy(record)

    def _certificate_view(self, record, actor):
        entries = []
        for application_id in record["application_ids"]:
            application = self.store.get_application(application_id, actor=None)
            entries.append({
                "application_id": application_id,
                "person_ref": application["person_ref"],
                "stage": application["stage"],
            })
        if self._is_employee(actor):
            name = getattr(actor, "name", None)
            if any(e["person_ref"] != name for e in entries):
                raise PermissionDenied(
                    "permission denied: employee %r may not read a certificate "
                    "document covering other persons" % (name,)
                )
        view = copy.deepcopy(record)
        view["entries"] = entries
        view["entry_count"] = len(entries)
        return view

    def get_certificate(self, certificate_id, actor=None):
        """Return one certificate document with derived entries.

        Action: application_read. ``entry_count`` and the entry rows
        are derived at read from the core application records; an
        employee actor may read a certificate only when every entry
        is their own application.
        """
        _maybe_require(actor, "application_read")
        with self._lock:
            record = self._certificates.get(certificate_id)
            if record is None:
                raise NotFoundError("certificate not found: %r" % (certificate_id,))
            return self._certificate_view(record, actor)

    def list_certificates(self, actor=None, vacancy_id=None):
        """Return certificate documents with derived entries.

        Action: application_read. Employee actors see only
        certificates whose every entry is their own application.
        """
        _maybe_require(actor, "application_read")
        with self._lock:
            records = list(self._certificates.values())
            if vacancy_id is not None:
                records = [r for r in records if r["vacancy_id"] == vacancy_id]
            views = []
            for record in self._sorted(records):
                try:
                    views.append(self._certificate_view(record, actor))
                except PermissionDenied:
                    if self._is_employee(actor):
                        continue
                    raise
            return views

    # -- Career sites, talent communities, campus recruiting & events -----
    # Outreach records only: a career-site record is a configuration
    # record (nothing is served), a community is a membership
    # registry, an event is a recruiting-event record with
    # registrations. No page is published and no invitation is sent.

    def create_career_site(self, site_ref, title, actor):
        """Create a career-site configuration record (state draft).

        Action: vacancy_write. ``site_ref`` is unique. The record
        configures a site; this build serves nothing.
        """
        _require_actor(actor, "vacancy_write")
        _validate_non_empty(site_ref, "site_ref")
        _validate_non_empty(title, "site title")
        with self._lock:
            if any(s["site_ref"] == site_ref for s in self._career_sites.values()):
                raise ValidationError("site_ref already exists: %r" % (site_ref,))
            site_id = self._next_id("cst")
            record = {
                "id": site_id,
                "site_ref": site_ref,
                "title": title,
                "state": "draft",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._career_sites[site_id] = record
            self._audit(actor, "career_site_create", site_id,
                        details={"site_ref": site_ref})
            return copy.deepcopy(record)

    def set_career_site_state(self, site_id, state, actor):
        """Set a career-site record's state. Action: vacancy_write.

        The state is a recorded publication state of the
        configuration record; changing it publishes nothing.
        """
        _require_actor(actor, "vacancy_write")
        if state not in SITE_STATES:
            raise ValidationError("state must be one of %s" % (", ".join(SITE_STATES),))
        with self._lock:
            record = self._career_sites.get(site_id)
            if record is None:
                raise NotFoundError("career site not found: %r" % (site_id,))
            record["state"] = state
            self._audit(actor, "career_site_set_state", site_id, details={"state": state})
            return copy.deepcopy(record)

    def list_career_sites(self, actor=None):
        """Return career-site records. Action: vacancy_read (org-level)."""
        _maybe_require(actor, "vacancy_read")
        with self._lock:
            return [copy.deepcopy(r) for r in self._sorted(self._career_sites.values())]

    def create_community(self, community_ref, title, actor):
        """Create a talent-community registry record.

        Action: vacancy_write. ``community_ref`` is unique.
        """
        _require_actor(actor, "vacancy_write")
        _validate_non_empty(community_ref, "community_ref")
        _validate_non_empty(title, "community title")
        with self._lock:
            if any(c["community_ref"] == community_ref for c in self._communities.values()):
                raise ValidationError("community_ref already exists: %r" % (community_ref,))
            community_id = self._next_id("cmu")
            record = {
                "id": community_id,
                "community_ref": community_ref,
                "title": title,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._communities[community_id] = record
            self._audit(actor, "community_create", community_id,
                        details={"community_ref": community_ref})
            return copy.deepcopy(record)

    def add_community_member(self, community_id, person_ref, actor):
        """Record a person's membership in a talent community.

        Action: vacancy_write. The community and the person (by
        person_ref) must exist; a duplicate membership is a
        validation error.
        """
        _require_actor(actor, "vacancy_write")
        _validate_non_empty(person_ref, "person_ref")
        with self._lock:
            if community_id not in self._communities:
                raise NotFoundError("community not found: %r" % (community_id,))
            self._require_person_ref(person_ref)
            for member in self._community_members.values():
                if (member["community_id"] == community_id
                        and member["person_ref"] == person_ref):
                    raise ValidationError(
                        "person %r is already a member of community %r"
                        % (person_ref, community_id)
                    )
            member_id = self._next_id("cmm")
            record = {
                "id": member_id,
                "community_id": community_id,
                "person_ref": person_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._community_members[member_id] = record
            self._audit(actor, "community_member_add", member_id,
                        details={"community_id": community_id,
                                 "person_ref": person_ref})
            return copy.deepcopy(record)

    def list_community_members(self, community_id, actor=None):
        """Return a community's membership records.

        Action: vacancy_read. Employee actors see only their own
        membership records.
        """
        _maybe_require(actor, "vacancy_read")
        with self._lock:
            if community_id not in self._communities:
                raise NotFoundError("community not found: %r" % (community_id,))
            records = [
                m for m in self._community_members.values()
                if m["community_id"] == community_id
            ]
            return [copy.deepcopy(r) for r in self._sorted(self._scoped(actor, records))]

    def create_recruiting_event(self, title, event_on, actor):
        """Create a campus-recruiting event record (state scheduled).

        Action: vacancy_write. ``event_on`` is an ISO date.
        """
        _require_actor(actor, "vacancy_write")
        _validate_non_empty(title, "event title")
        _validate_date(event_on, "event_on")
        with self._lock:
            event_id = self._next_id("evt")
            record = {
                "id": event_id,
                "title": title,
                "event_on": event_on,
                "state": "scheduled",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._events[event_id] = record
            self._audit(actor, "recruiting_event_create", event_id,
                        details={"event_on": event_on})
            return copy.deepcopy(record)

    def set_recruiting_event_state(self, event_id, state, actor):
        """Set a recruiting event's state. Action: vacancy_write."""
        _require_actor(actor, "vacancy_write")
        if state not in EVENT_STATES:
            raise ValidationError("state must be one of %s" % (", ".join(EVENT_STATES),))
        with self._lock:
            record = self._events.get(event_id)
            if record is None:
                raise NotFoundError("recruiting event not found: %r" % (event_id,))
            record["state"] = state
            self._audit(actor, "recruiting_event_set_state", event_id,
                        details={"state": state})
            return copy.deepcopy(record)

    def register_for_event(self, event_id, person_ref, actor):
        """Record a person's registration for a recruiting event.

        Action: vacancy_write. The event and the person must exist;
        a duplicate registration is a validation error. The
        registration is a record; no invitation or confirmation is
        sent.
        """
        _require_actor(actor, "vacancy_write")
        _validate_non_empty(person_ref, "person_ref")
        with self._lock:
            if event_id not in self._events:
                raise NotFoundError("recruiting event not found: %r" % (event_id,))
            self._require_person_ref(person_ref)
            for registration in self._event_registrations.values():
                if (registration["event_id"] == event_id
                        and registration["person_ref"] == person_ref):
                    raise ValidationError(
                        "person %r is already registered for event %r"
                        % (person_ref, event_id)
                    )
            registration_id = self._next_id("evr")
            record = {
                "id": registration_id,
                "event_id": event_id,
                "person_ref": person_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._event_registrations[registration_id] = record
            self._audit(actor, "recruiting_event_register", registration_id,
                        details={"event_id": event_id, "person_ref": person_ref})
            return copy.deepcopy(record)

    def get_recruiting_event(self, event_id, actor=None):
        """Return one event record with its derived registration
        count. Action: vacancy_read (org-level record; the count is
        derived at read, never stored)."""
        _maybe_require(actor, "vacancy_read")
        with self._lock:
            record = self._events.get(event_id)
            if record is None:
                raise NotFoundError("recruiting event not found: %r" % (event_id,))
            view = copy.deepcopy(record)
            view["registration_count"] = sum(
                1 for r in self._event_registrations.values()
                if r["event_id"] == event_id
            )
            return view

    def list_event_registrations(self, event_id, actor=None):
        """Return an event's registration records.

        Action: vacancy_read. Employee actors see only their own
        registrations.
        """
        _maybe_require(actor, "vacancy_read")
        with self._lock:
            if event_id not in self._events:
                raise NotFoundError("recruiting event not found: %r" % (event_id,))
            records = [
                r for r in self._event_registrations.values()
                if r["event_id"] == event_id
            ]
            return [copy.deepcopy(r) for r in self._sorted(self._scoped(actor, records))]

    # -- Talent mobility & workforce-exchange marketplace engines ---------
    # Listing and interest records; the exchange "matching" is a
    # deterministic series-overlap derivation over the core records,
    # returning its evidence. No marketplace transaction occurs.

    def create_mobility_listing(self, position_id, kind, actor):
        """Create a mobility/exchange listing record for a position.

        Action: position_write. The position must exist; the listing
        starts ``open``.
        """
        _require_actor(actor, "position_write")
        if kind not in LISTING_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(LISTING_KINDS),))
        with self._lock:
            self.store.get_position(position_id, actor=None)
            listing_id = self._next_id("lst")
            record = {
                "id": listing_id,
                "position_id": position_id,
                "kind": kind,
                "state": "open",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._listings[listing_id] = record
            self._audit(actor, "mobility_listing_create", listing_id,
                        details={"position_id": position_id, "kind": kind})
            return copy.deepcopy(record)

    def set_mobility_listing_state(self, listing_id, state, actor):
        """Set a mobility listing's state. Action: position_write."""
        _require_actor(actor, "position_write")
        if state not in LISTING_STATES:
            raise ValidationError("state must be one of %s" % (", ".join(LISTING_STATES),))
        with self._lock:
            record = self._listings.get(listing_id)
            if record is None:
                raise NotFoundError("mobility listing not found: %r" % (listing_id,))
            record["state"] = state
            self._audit(actor, "mobility_listing_set_state", listing_id,
                        details={"state": state})
            return copy.deepcopy(record)

    def list_mobility_listings(self, actor=None, state=None):
        """Return mobility listing records. Action: position_read."""
        _maybe_require(actor, "position_read")
        with self._lock:
            records = list(self._listings.values())
            if state is not None:
                records = [r for r in records if r["state"] == state]
            return [copy.deepcopy(r) for r in self._sorted(records)]

    def record_mobility_interest(self, listing_id, person_ref, actor):
        """Record a person's interest in an open mobility listing.

        Action: application_write. The listing and the person must
        exist, the listing must be open, and a duplicate interest is
        a validation error.
        """
        _require_actor(actor, "application_write")
        _validate_non_empty(person_ref, "person_ref")
        with self._lock:
            listing = self._listings.get(listing_id)
            if listing is None:
                raise NotFoundError("mobility listing not found: %r" % (listing_id,))
            if listing["state"] != "open":
                raise ValidationError("mobility listing %r is not open" % (listing_id,))
            self._require_person_ref(person_ref)
            for interest in self._interests.values():
                if (interest["listing_id"] == listing_id
                        and interest["person_ref"] == person_ref):
                    raise ValidationError(
                        "person %r already recorded interest in listing %r"
                        % (person_ref, listing_id)
                    )
            interest_id = self._next_id("int")
            record = {
                "id": interest_id,
                "listing_id": listing_id,
                "person_ref": person_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._interests[interest_id] = record
            self._audit(actor, "mobility_interest_record", interest_id,
                        details={"listing_id": listing_id,
                                 "person_ref": person_ref})
            return copy.deepcopy(record)

    def list_mobility_interests(self, actor=None, listing_id=None, person_ref=None):
        """Return mobility interest records.

        Action: application_read (+ employee scope).
        """
        _maybe_require(actor, "application_read")
        if person_ref is not None:
            self._scope_check(actor, person_ref)
        with self._lock:
            records = list(self._interests.values())
            if listing_id is not None:
                records = [r for r in records if r["listing_id"] == listing_id]
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            return [copy.deepcopy(r) for r in self._sorted(self._scoped(actor, records))]

    def mobility_matches(self, person_ref, actor=None):
        """Derive a person's open-listing series matches. Never stored.

        Action: application_read (+ employee scope). Evidence: the
        occupational series of the positions behind every vacancy
        the person has applied to. An open listing matches when its
        position's recorded series is in that evidence set. Method:
        ``deterministic_series_overlap``.
        """
        _maybe_require(actor, "application_read")
        self._scope_check(actor, person_ref)
        with self._lock:
            self._require_person_ref(person_ref)
            series_seen = set()
            for application in self.store.list_applications(
                actor=None, person_ref=person_ref
            ):
                vacancy = self.store.get_vacancy(application["vacancy_id"], actor=None)
                position = self.store.get_position(vacancy["position_id"], actor=None)
                if position["series"]:
                    series_seen.add(position["series"])
            matches = []
            for listing in self._sorted(self._listings.values()):
                if listing["state"] != "open":
                    continue
                position = self.store.get_position(listing["position_id"], actor=None)
                if position["series"] and position["series"] in series_seen:
                    matches.append({
                        "listing_id": listing["id"],
                        "position_id": position["id"],
                        "kind": listing["kind"],
                        "series": position["series"],
                    })
            return {
                "person_ref": person_ref,
                "method": "deterministic_series_overlap",
                "derived": True,
                "stored": False,
                "evidence_series": sorted(series_seen),
                "matches": matches,
                "match_count": len(matches),
            }

    # -- Talent management suite depth beyond records ----------------------
    # Development-program records and enrollments: the suite depth
    # (retention / development / mentoring programs) as records over
    # the substrate, with derived per-program counts.

    def create_development_program(self, program_ref, title, kind, actor):
        """Create a talent-development program record.

        Action: performance_write. ``program_ref`` is unique.
        """
        _require_actor(actor, "performance_write")
        _validate_non_empty(program_ref, "program_ref")
        _validate_non_empty(title, "program title")
        if kind not in PROGRAM_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(PROGRAM_KINDS),))
        with self._lock:
            if any(p["program_ref"] == program_ref for p in self._programs.values()):
                raise ValidationError("program_ref already exists: %r" % (program_ref,))
            program_id = self._next_id("prg")
            record = {
                "id": program_id,
                "program_ref": program_ref,
                "title": title,
                "kind": kind,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._programs[program_id] = record
            self._audit(actor, "development_program_create", program_id,
                        details={"program_ref": program_ref, "kind": kind})
            return copy.deepcopy(record)

    def enroll_in_program(self, program_id, person_ref, actor):
        """Enroll a person in a development program.

        Action: performance_write. The program and the person must
        exist; a duplicate live enrollment (state not withdrawn) is
        a validation error.
        """
        _require_actor(actor, "performance_write")
        _validate_non_empty(person_ref, "person_ref")
        with self._lock:
            if program_id not in self._programs:
                raise NotFoundError("development program not found: %r" % (program_id,))
            self._require_person_ref(person_ref)
            for enrollment in self._enrollments.values():
                if (enrollment["program_id"] == program_id
                        and enrollment["person_ref"] == person_ref
                        and enrollment["state"] != "withdrawn"):
                    raise ValidationError(
                        "person %r already has a live enrollment in program %r"
                        % (person_ref, program_id)
                    )
            enrollment_id = self._next_id("enr")
            record = {
                "id": enrollment_id,
                "program_id": program_id,
                "person_ref": person_ref,
                "state": "enrolled",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._enrollments[enrollment_id] = record
            self._audit(actor, "program_enroll", enrollment_id,
                        details={"program_id": program_id,
                                 "person_ref": person_ref})
            return copy.deepcopy(record)

    def set_enrollment_state(self, enrollment_id, state, actor):
        """Set a program enrollment's state. Action: performance_write."""
        _require_actor(actor, "performance_write")
        if state not in ENROLLMENT_STATES:
            raise ValidationError(
                "state must be one of %s" % (", ".join(ENROLLMENT_STATES),)
            )
        with self._lock:
            record = self._enrollments.get(enrollment_id)
            if record is None:
                raise NotFoundError("enrollment not found: %r" % (enrollment_id,))
            record["state"] = state
            self._audit(actor, "program_enrollment_set_state", enrollment_id,
                        details={"state": state})
            return copy.deepcopy(record)

    def list_enrollments(self, actor=None, program_id=None, person_ref=None):
        """Return program enrollment records.

        Action: performance_read (+ employee scope).
        """
        _maybe_require(actor, "performance_read")
        if person_ref is not None:
            self._scope_check(actor, person_ref)
        with self._lock:
            records = list(self._enrollments.values())
            if program_id is not None:
                records = [r for r in records if r["program_id"] == program_id]
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            return [copy.deepcopy(r) for r in self._sorted(self._scoped(actor, records))]

    def program_summary(self, program_id, actor=None):
        """Derive a program's enrollment counts by state.

        Action: report_read (aggregate reporting, as in the core
        report). Counts are derived at read, never stored.
        """
        _maybe_require(actor, "report_read")
        with self._lock:
            if program_id not in self._programs:
                raise NotFoundError("development program not found: %r" % (program_id,))
            by_state = {state: 0 for state in ENROLLMENT_STATES}
            total = 0
            for enrollment in self._enrollments.values():
                if enrollment["program_id"] == program_id:
                    by_state[enrollment["state"]] += 1
                    total += 1
            return {
                "program_id": program_id,
                "method": "deterministic_counts",
                "derived": True,
                "stored": False,
                "enrollments": total,
                "enrollments_by_state": by_state,
            }

    # -- Workforce planning & resource-management analytics / models ------
    # Analytics are deterministic counts over the core records,
    # derived at read. A planning "model" is a scenario record (its
    # assumptions, as data) plus an integer projection derived at
    # read from the current records and those assumptions.

    def workforce_analytics(self, actor=None):
        """Derive workforce-planning counts over the core records.

        Action: report_read. Includes the derived vacancy rate in
        integer basis points (vacant positions / all positions,
        floor division; 0 when there are no positions). Method:
        ``deterministic_counts``. Never stored.
        """
        _maybe_require(actor, "report_read")
        with self._lock:
            persons = self.store.list_persons(actor=None)
            positions = self.store.list_positions(actor=None)
            vacancies = self.store.list_vacancies(actor=None)
            applications = self.store.list_applications(actor=None)
            lifecycle = self.store.list_lifecycle_cases(actor=None)
            vacant = sum(1 for p in positions if p["status"] == "vacant")
            total_positions = len(positions)
            vacancy_rate_bps = (
                vacant * 10000 // total_positions if total_positions else 0
            )
            applications_by_stage = {}
            for application in applications:
                stage = application["stage"]
                applications_by_stage[stage] = applications_by_stage.get(stage, 0) + 1
            lifecycle_by_status = {}
            for case in lifecycle:
                status = case["status"]
                lifecycle_by_status[status] = lifecycle_by_status.get(status, 0) + 1
            return {
                "method": "deterministic_counts",
                "derived": True,
                "stored": False,
                "persons": len(persons),
                "active_persons": sum(
                    1 for p in persons if p["status"] == "active"
                ),
                "positions": total_positions,
                "vacant_positions": vacant,
                "vacancy_rate_bps": vacancy_rate_bps,
                "vacancies": len(vacancies),
                "open_vacancies": sum(
                    1 for v in vacancies if v["status"] == "posted"
                ),
                "applications": len(applications),
                "applications_by_stage": applications_by_stage,
                "lifecycle_cases_by_status": lifecycle_by_status,
            }

    def create_planning_scenario(self, title, attrition_bps, horizon_periods, actor):
        """Create a workforce-planning scenario record.

        Action: position_write. The scenario stores its assumptions
        as data (``attrition_bps`` 0..10000, ``horizon_periods``
        1..40); the projection itself is derived at read, never
        stored on the scenario.
        """
        _require_actor(actor, "position_write")
        _validate_non_empty(title, "scenario title")
        _validate_int(attrition_bps, "attrition_bps", minimum=0, maximum=10000)
        _validate_int(horizon_periods, "horizon_periods", minimum=1, maximum=40)
        with self._lock:
            scenario_id = self._next_id("scn")
            record = {
                "id": scenario_id,
                "title": title,
                "attrition_bps": attrition_bps,
                "horizon_periods": horizon_periods,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._scenarios[scenario_id] = record
            self._audit(actor, "planning_scenario_create", scenario_id,
                        details={"attrition_bps": attrition_bps,
                                 "horizon_periods": horizon_periods})
            return copy.deepcopy(record)

    def get_planning_scenario(self, scenario_id, actor=None):
        """Return one planning scenario record. Action: position_read."""
        _maybe_require(actor, "position_read")
        with self._lock:
            record = self._scenarios.get(scenario_id)
            if record is None:
                raise NotFoundError("planning scenario not found: %r" % (scenario_id,))
            return copy.deepcopy(record)

    def scenario_projection(self, scenario_id, actor=None):
        """Derive a scenario's headcount projection. Never stored.

        Action: report_read. Integer arithmetic only: starting from
        the current count of active persons, each period's projected
        separations are ``headcount * attrition_bps // 10000``
        (floor), subtracted before the next period. The assumptions
        are echoed from the scenario record so the derivation is
        inspectable. Method: ``deterministic_integer_projection``.
        """
        _maybe_require(actor, "report_read")
        with self._lock:
            scenario = self._scenarios.get(scenario_id)
            if scenario is None:
                raise NotFoundError("planning scenario not found: %r" % (scenario_id,))
            headcount = sum(
                1 for p in self.store.list_persons(actor=None)
                if p["status"] == "active"
            )
            periods = []
            current = headcount
            for period in range(1, scenario["horizon_periods"] + 1):
                separations = current * scenario["attrition_bps"] // 10000
                current -= separations
                periods.append({
                    "period": period,
                    "projected_separations": separations,
                    "projected_headcount": current,
                })
            return {
                "scenario_id": scenario_id,
                "method": "deterministic_integer_projection",
                "derived": True,
                "stored": False,
                "assumptions": {
                    "attrition_bps": scenario["attrition_bps"],
                    "horizon_periods": scenario["horizon_periods"],
                },
                "starting_active_persons": headcount,
                "periods": periods,
            }

    # -- Retirement benefits calculator -------------------------------------
    # Integer accrual arithmetic over recorded inputs: a plan's
    # recorded accrual parameters and a recorded service-months
    # input. The estimate is derived at read and pays nothing. No
    # currency amount is computed: an amount requires the member's
    # pay figure, which no record in this build can hold (structural
    # privacy rule) -- the view states that boundary explicitly.

    def create_retirement_plan_parameters(self, plan_ref, accrual_bps_per_year,
                                          vesting_months, actor):
        """Create retirement plan-parameter records.

        Action: benefits_write. ``plan_ref`` is unique;
        ``accrual_bps_per_year`` is the plan's recorded accrual rate
        in basis points of the (externally held) pay base per year
        of service; ``vesting_months`` is the recorded vesting
        threshold in months of service.
        """
        _require_actor(actor, "benefits_write")
        _validate_non_empty(plan_ref, "plan_ref")
        _validate_int(accrual_bps_per_year, "accrual_bps_per_year",
                      minimum=1, maximum=10000)
        _validate_int(vesting_months, "vesting_months", minimum=0)
        with self._lock:
            if any(p["plan_ref"] == plan_ref for p in self._retirement_params.values()):
                raise ValidationError("plan_ref already exists: %r" % (plan_ref,))
            params_id = self._next_id("ppr")
            record = {
                "id": params_id,
                "plan_ref": plan_ref,
                "accrual_bps_per_year": accrual_bps_per_year,
                "vesting_months": vesting_months,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._retirement_params[params_id] = record
            self._audit(actor, "retirement_params_create", params_id,
                        details={"plan_ref": plan_ref})
            return copy.deepcopy(record)

    def retirement_estimate(self, person_ref, plan_ref, service_months, actor=None):
        """Derive a retirement accrual estimate. Never stored.

        Action: benefits_read (+ employee scope). Integer arithmetic
        over the recorded inputs: ``accrued_bps`` is
        ``service_months * accrual_bps_per_year // 12`` -- the
        accrued fraction, in basis points, of the member's pay base
        as recorded in the embedding organization's systems.
        ``currency_amount`` is None by design (see the section
        comment above); ``vested`` derives from the plan's recorded
        vesting threshold.
        """
        _maybe_require(actor, "benefits_read")
        self._scope_check(actor, person_ref)
        _validate_non_empty(person_ref, "person_ref")
        _validate_non_empty(plan_ref, "plan_ref")
        _validate_int(service_months, "service_months", minimum=0)
        with self._lock:
            self._require_person_ref(person_ref)
            params = None
            for record in self._retirement_params.values():
                if record["plan_ref"] == plan_ref:
                    params = record
                    break
            if params is None:
                raise NotFoundError("retirement plan parameters not found: %r" % (plan_ref,))
            accrued_bps = service_months * params["accrual_bps_per_year"] // 12
            return {
                "person_ref": person_ref,
                "plan_ref": plan_ref,
                "method": "integer_accrual_derivation",
                "derived": True,
                "stored": False,
                "service_months": service_months,
                "service_years": service_months // 12,
                "accrued_bps": accrued_bps,
                "vested": service_months >= params["vesting_months"],
                "currency_amount": None,
                "pays_nothing": True,
            }

    # -- Employee learning & upskilling delivery -----------------------------
    # Course-catalog and assignment records: the delivery surface as
    # records over the substrate, with a derived per-person summary.
    # No content is delivered to anyone by this build.

    def create_course(self, course_ref, title, actor):
        """Create a course-catalog record. Action: performance_write.

        ``course_ref`` is an opaque caller-supplied reference, unique.
        """
        _require_actor(actor, "performance_write")
        _validate_non_empty(course_ref, "course_ref")
        _validate_non_empty(title, "course title")
        with self._lock:
            if any(c["course_ref"] == course_ref for c in self._courses.values()):
                raise ValidationError("course_ref already exists: %r" % (course_ref,))
            course_id = self._next_id("crs")
            record = {
                "id": course_id,
                "course_ref": course_ref,
                "title": title,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._courses[course_id] = record
            self._audit(actor, "course_create", course_id,
                        details={"course_ref": course_ref})
            return copy.deepcopy(record)

    def assign_course(self, person_ref, course_id, actor):
        """Assign a course to a person (an assignment record).

        Action: performance_write. The person and the course must
        exist; a duplicate live assignment (state not completed) for
        the same person and course is a validation error.
        """
        _require_actor(actor, "performance_write")
        _validate_non_empty(person_ref, "person_ref")
        with self._lock:
            if course_id not in self._courses:
                raise NotFoundError("course not found: %r" % (course_id,))
            self._require_person_ref(person_ref)
            for assignment in self._learning.values():
                if (assignment["person_ref"] == person_ref
                        and assignment["course_id"] == course_id
                        and assignment["state"] != "completed"):
                    raise ValidationError(
                        "person %r already has a live assignment for course %r"
                        % (person_ref, course_id)
                    )
            assignment_id = self._next_id("lrn")
            record = {
                "id": assignment_id,
                "person_ref": person_ref,
                "course_id": course_id,
                "state": "assigned",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._learning[assignment_id] = record
            self._audit(actor, "learning_assign", assignment_id,
                        details={"person_ref": person_ref,
                                 "course_id": course_id})
            return copy.deepcopy(record)

    def set_learning_state(self, assignment_id, state, actor):
        """Set a learning assignment's state. Action: performance_write."""
        _require_actor(actor, "performance_write")
        if state not in LEARNING_STATES:
            raise ValidationError(
                "state must be one of %s" % (", ".join(LEARNING_STATES),)
            )
        with self._lock:
            record = self._learning.get(assignment_id)
            if record is None:
                raise NotFoundError("learning assignment not found: %r" % (assignment_id,))
            record["state"] = state
            self._audit(actor, "learning_set_state", assignment_id,
                        details={"state": state})
            return copy.deepcopy(record)

    def list_learning_assignments(self, actor=None, person_ref=None):
        """Return learning assignment records.

        Action: performance_read (+ employee scope).
        """
        _maybe_require(actor, "performance_read")
        if person_ref is not None:
            self._scope_check(actor, person_ref)
        with self._lock:
            records = list(self._learning.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            return [copy.deepcopy(r) for r in self._sorted(self._scoped(actor, records))]

    def learning_summary(self, person_ref, actor=None):
        """Derive a person's learning counts by state. Never stored.

        Action: performance_read (+ employee scope).
        """
        _maybe_require(actor, "performance_read")
        self._scope_check(actor, person_ref)
        with self._lock:
            self._require_person_ref(person_ref)
            by_state = {state: 0 for state in LEARNING_STATES}
            total = 0
            for assignment in self._learning.values():
                if assignment["person_ref"] == person_ref:
                    by_state[assignment["state"]] += 1
                    total += 1
            return {
                "person_ref": person_ref,
                "method": "deterministic_counts",
                "derived": True,
                "stored": False,
                "assignments": total,
                "assignments_by_state": by_state,
            }

    # -- Document & template assembly engines --------------------------------
    # Template records declare a source kind (position or vacancy)
    # and a body with ``{field}`` placeholders drawn from that kind's
    # recorded fields. Assembly is a deterministic substitution over
    # one core record, producing a document artifact record. No
    # other record is changed by assembly.

    def create_template(self, template_ref, title, source_kind, body, actor):
        """Create a document-template record.

        Action: case_write. ``template_ref`` is unique. The body's
        ``{field}`` placeholders are validated at creation against
        the recorded fields of ``source_kind``; an unknown
        placeholder is a validation error.
        """
        _require_actor(actor, "case_write")
        _validate_non_empty(template_ref, "template_ref")
        _validate_non_empty(title, "template title")
        if source_kind not in TEMPLATE_SOURCES:
            raise ValidationError(
                "source_kind must be one of %s" % (", ".join(sorted(TEMPLATE_SOURCES)),)
            )
        _validate_non_empty(body, "template body")
        placeholders = []
        rest = body
        while "{" in rest:
            head, _, rest = rest.partition("{")
            field, sep, rest = rest.partition("}")
            if not sep:
                raise ValidationError("template body has an unclosed placeholder")
            if field not in TEMPLATE_SOURCES[source_kind]:
                raise ValidationError(
                    "unknown placeholder {%s} for source kind %r" % (field, source_kind)
                )
            if field not in placeholders:
                placeholders.append(field)
        with self._lock:
            if any(t["template_ref"] == template_ref for t in self._templates.values()):
                raise ValidationError("template_ref already exists: %r" % (template_ref,))
            template_id = self._next_id("tpl")
            record = {
                "id": template_id,
                "template_ref": template_ref,
                "title": title,
                "source_kind": source_kind,
                "body": body,
                "placeholders": placeholders,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._templates[template_id] = record
            self._audit(actor, "template_create", template_id,
                        details={"template_ref": template_ref,
                                 "source_kind": source_kind})
            return copy.deepcopy(record)

    def get_template(self, template_id, actor=None):
        """Return one template record. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            record = self._templates.get(template_id)
            if record is None:
                raise NotFoundError("template not found: %r" % (template_id,))
            return copy.deepcopy(record)

    def assemble_document(self, template_id, source_id, actor):
        """Assemble a document artifact from a template and a record.

        Action: case_write. The source record must exist and match
        the template's source kind. Substitution is deterministic:
        each ``{field}`` is replaced by the source record's recorded
        value (empty string for a recorded None). The assembled text
        is stored on the document record -- the document IS the
        artifact; the source record is unchanged.
        """
        _require_actor(actor, "case_write")
        with self._lock:
            template = self._templates.get(template_id)
            if template is None:
                raise NotFoundError("template not found: %r" % (template_id,))
            if template["source_kind"] == "position":
                source = self.store.get_position(source_id, actor=None)
            else:
                source = self.store.get_vacancy(source_id, actor=None)
            text = template["body"]
            for field in template["placeholders"]:
                value = source.get(field)
                text = text.replace("{%s}" % (field,), "" if value is None else str(value))
            document_id = self._next_id("doc")
            record = {
                "id": document_id,
                "template_id": template_id,
                "source_kind": template["source_kind"],
                "source_id": source_id,
                "text": text,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._documents[document_id] = record
            self._audit(actor, "document_assemble", document_id,
                        details={"template_id": template_id,
                                 "source_id": source_id})
            return copy.deepcopy(record)

    def get_document(self, document_id, actor=None):
        """Return one assembled document record. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            record = self._documents.get(document_id)
            if record is None:
                raise NotFoundError("document not found: %r" % (document_id,))
            return copy.deepcopy(record)

    def list_documents(self, actor=None, template_id=None):
        """Return assembled document records. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            records = list(self._documents.values())
            if template_id is not None:
                records = [r for r in records if r["template_id"] == template_id]
            return [copy.deepcopy(r) for r in self._sorted(records)]

    # -- Stub-engine surfaces (labeled reference implementations) ------------
    # Records only, never execution. Every record in this section
    # carries ``reference_stub: True`` and state
    # ``recorded_reference_only``; transport-shaped records also
    # carry ``reference_transport: True``. Creating any of them
    # changes no core record.

    def create_workflow_definition(self, workflow_ref, title, steps, actor):
        """Record a hiring-workflow definition as reference data.

        Action: application_write. ``steps`` is a non-empty list of
        application stage names, recorded as data. The definition is
        never executed: no application changes stage because this
        record exists.
        """
        _require_actor(actor, "application_write")
        _validate_non_empty(workflow_ref, "workflow_ref")
        _validate_non_empty(title, "workflow title")
        from .store import APPLICATION_STAGES
        if not isinstance(steps, (list, tuple)) or not steps:
            raise ValidationError("steps must be a non-empty list")
        for step in steps:
            if step not in APPLICATION_STAGES:
                raise ValidationError(
                    "step must be one of %s" % (", ".join(APPLICATION_STAGES),)
                )
        with self._lock:
            if any(w["workflow_ref"] == workflow_ref for w in self._workflows.values()):
                raise ValidationError("workflow_ref already exists: %r" % (workflow_ref,))
            workflow_id = self._next_id("wfl")
            record = {
                "id": workflow_id,
                "workflow_ref": workflow_ref,
                "title": title,
                "steps": list(steps),
                "reference_stub": True,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workflows[workflow_id] = record
            self._audit(actor, "workflow_definition_record", workflow_id,
                        details={"workflow_ref": workflow_ref})
            return copy.deepcopy(record)

    def list_workflow_definitions(self, actor=None):
        """Return workflow definition reference records.

        Action: application_read.
        """
        _maybe_require(actor, "application_read")
        with self._lock:
            return [copy.deepcopy(r) for r in self._sorted(self._workflows.values())]

    def record_posting_request(self, vacancy_id, board_ref, actor):
        """Record a job-board posting/sync request as a reference
        transport receipt.

        Action: application_write. The vacancy must exist. Nothing
        is posted or synced anywhere; the receipt records that a
        posting was requested, in reference form.
        """
        _require_actor(actor, "application_write")
        _validate_non_empty(board_ref, "board_ref")
        with self._lock:
            self.store.get_vacancy(vacancy_id, actor=None)
            posting_id = self._next_id("pst")
            record = {
                "id": posting_id,
                "vacancy_id": vacancy_id,
                "board_ref": board_ref,
                "reference_stub": True,
                "reference_transport": True,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._postings[posting_id] = record
            self._audit(actor, "posting_request_record", posting_id,
                        details={"vacancy_id": vacancy_id,
                                 "board_ref": board_ref})
            return copy.deepcopy(record)

    def list_posting_requests(self, actor=None, vacancy_id=None):
        """Return posting-request reference receipts.

        Action: application_read.
        """
        _maybe_require(actor, "application_read")
        with self._lock:
            records = list(self._postings.values())
            if vacancy_id is not None:
                records = [r for r in records if r["vacancy_id"] == vacancy_id]
            return [copy.deepcopy(r) for r in self._sorted(records)]

    def create_assessment_content(self, content_ref, title, provider_ref, actor):
        """Record an assessment-content reference record.

        Action: evaluation_write. The record holds the content
        item's reference metadata only (an opaque content ref, a
        title, an opaque provider ref) -- no assessment content
        itself is held or delivered by this build.
        """
        _require_actor(actor, "evaluation_write")
        _validate_non_empty(content_ref, "content_ref")
        _validate_non_empty(title, "content title")
        _validate_non_empty(provider_ref, "provider_ref")
        with self._lock:
            if any(c["content_ref"] == content_ref
                   for c in self._assessment_content.values()):
                raise ValidationError("content_ref already exists: %r" % (content_ref,))
            content_id = self._next_id("cnt")
            record = {
                "id": content_id,
                "content_ref": content_ref,
                "title": title,
                "provider_ref": provider_ref,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assessment_content[content_id] = record
            self._audit(actor, "assessment_content_record", content_id,
                        details={"content_ref": content_ref})
            return copy.deepcopy(record)

    def record_assessment_delivery(self, evaluation_id, provider_ref, actor):
        """Record an assessment-delivery reference record.

        Action: evaluation_write. The evaluation must exist. Nothing
        is delivered to any provider; the record states that a
        delivery was arranged, in reference form, against the core
        evaluation record (which is unchanged).
        """
        _require_actor(actor, "evaluation_write")
        _validate_non_empty(provider_ref, "provider_ref")
        with self._lock:
            self.store.get_evaluation(evaluation_id, actor=None)
            delivery_id = self._next_id("dlv")
            record = {
                "id": delivery_id,
                "evaluation_id": evaluation_id,
                "provider_ref": provider_ref,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assessment_deliveries[delivery_id] = record
            self._audit(actor, "assessment_delivery_record", delivery_id,
                        details={"evaluation_id": evaluation_id})
            return copy.deepcopy(record)

    def list_assessment_deliveries(self, actor=None, evaluation_id=None):
        """Return assessment-delivery reference records.

        Action: evaluation_read (+ employee scope through each
        delivery's evaluation's application).
        """
        _maybe_require(actor, "evaluation_read")
        with self._lock:
            records = list(self._assessment_deliveries.values())
            if evaluation_id is not None:
                records = [r for r in records if r["evaluation_id"] == evaluation_id]
            views = []
            for record in self._sorted(records):
                if self._is_employee(actor):
                    _, application = self._evaluation_application(record["evaluation_id"])
                    if application["person_ref"] != getattr(actor, "name", None):
                        continue
                views.append(copy.deepcopy(record))
            return views

    def create_connector(self, connector_ref, system_label, direction, actor):
        """Record an integration-connector reference record.

        Action: case_write. ``system_label`` is an opaque label for
        the external system (for example "usajobs", "eopf", "nfc",
        "ibc", "agency_hris"); it names a system this build does not
        connect to. The record is reference data only.
        """
        _require_actor(actor, "case_write")
        _validate_non_empty(connector_ref, "connector_ref")
        _validate_non_empty(system_label, "system_label")
        if direction not in CONNECTOR_DIRECTIONS:
            raise ValidationError(
                "direction must be one of %s" % (", ".join(CONNECTOR_DIRECTIONS),)
            )
        with self._lock:
            if any(c["connector_ref"] == connector_ref for c in self._connectors.values()):
                raise ValidationError("connector_ref already exists: %r" % (connector_ref,))
            connector_id = self._next_id("con")
            record = {
                "id": connector_id,
                "connector_ref": connector_ref,
                "system_label": system_label,
                "direction": direction,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._connectors[connector_id] = record
            self._audit(actor, "connector_record", connector_id,
                        details={"connector_ref": connector_ref,
                                 "system_label": system_label})
            return copy.deepcopy(record)

    def record_sync(self, connector_id, record_kind, record_count, actor):
        """Record a connector sync as a reference transport receipt.

        Action: case_write. The connector must exist.
        ``record_count`` is the count as REPORTED for the sync, held
        as data; no record is moved, read from, or written to any
        external system, and no core record changes.
        """
        _require_actor(actor, "case_write")
        _validate_non_empty(record_kind, "record_kind")
        _validate_int(record_count, "record_count", minimum=0)
        with self._lock:
            if connector_id not in self._connectors:
                raise NotFoundError("connector not found: %r" % (connector_id,))
            sync_id = self._next_id("syn")
            record = {
                "id": sync_id,
                "connector_id": connector_id,
                "record_kind": record_kind,
                "record_count": record_count,
                "reference_stub": True,
                "reference_transport": True,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._syncs[sync_id] = record
            self._audit(actor, "sync_record", sync_id,
                        details={"connector_id": connector_id,
                                 "record_kind": record_kind})
            return copy.deepcopy(record)

    def list_connectors(self, actor=None):
        """Return connector reference records. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            return [copy.deepcopy(r) for r in self._sorted(self._connectors.values())]

    def list_syncs(self, actor=None, connector_id=None):
        """Return sync reference receipts. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            records = list(self._syncs.values())
            if connector_id is not None:
                records = [r for r in records if r["connector_id"] == connector_id]
            return [copy.deepcopy(r) for r in self._sorted(records)]

    def create_hosting_record(self, deployment_ref, actor, region_label=""):
        """Record the deployment/hosting reference record.

        Action: case_write. The record states this build's platform
        posture in reference form: a single-tenant reference
        deployment whose hosting substrate is a deployment property
        (PLATFORM-LAYER.md decision 6). It provisions nothing, hosts
        nothing, and claims no platform service.
        """
        _require_actor(actor, "case_write")
        _validate_non_empty(deployment_ref, "deployment_ref")
        _validate_string(region_label, "region_label")
        with self._lock:
            if any(h["deployment_ref"] == deployment_ref for h in self._hosting.values()):
                raise ValidationError(
                    "deployment_ref already exists: %r" % (deployment_ref,)
                )
            hosting_id = self._next_id("hst")
            record = {
                "id": hosting_id,
                "deployment_ref": deployment_ref,
                "region_label": region_label,
                "tenancy": "single_tenant_reference",
                "platform_layer": "deployment_property_per_PLATFORM-LAYER.md_decision_6",
                "reference_stub": True,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._hosting[hosting_id] = record
            self._audit(actor, "hosting_record", hosting_id,
                        details={"deployment_ref": deployment_ref})
            return copy.deepcopy(record)

    def list_hosting_records(self, actor=None):
        """Return hosting reference records. Action: case_read."""
        _maybe_require(actor, "case_read")
        with self._lock:
            return [copy.deepcopy(r) for r in self._sorted(self._hosting.values())]
