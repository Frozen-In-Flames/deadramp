"""Final GAPS batch, second unit -- the no-signal addition entries.

Extensions for the 4 open entries of the GAPS.md section
"No-Signal Addition -- Health & Wellness Untiered Set (HealthEdge,
FR2700137029)" (see ``BATCH-ADDITION.md`` in the group directory
for the per-entry disposition). This module is a wrapper around
:class:`HealthStore`; every existing module -- the six founding
modules and the first batch unit's ``extensions.py`` -- is
untouched and byte-identical to the shipped set build.

**Tier discipline carries into the addition:** this set is
untiered -- every member's FedRAMP impact level is "Unknown" in
the source dataset -- so nothing here asserts a baseline, a tier,
or a CMMC equivalence either. HealthEdge's own description
asserts no control language of any family, and no record in this
module asserts a control family: the regulatory-reporting entry
(975) is a derivation over this substrate's own records and is,
in its entry's own words, explicitly not a control claim. This
build is **not a medical device and claims no FDA status**.

**The category's HARD PRIVACY RULE binds absolutely, here as in
the core and the first unit:** records and opaque caller-supplied
references only. No entity shape in this module has a name,
contact, date-of-birth, member-number, insurer, diagnosis, or
free-text clinical field -- those fields **do not exist**. No
shape holds a monetary amount either: adjudication and pricing
operate over claim amounts and fee schedules, and there is no
amount field anywhere in this substrate for a price to be
computed from or recorded against (the first unit's claim
records hold none, deliberately). Methods accept only their
named parameters, so a caller cannot smuggle a forbidden field
into a record (pinned by tests: an unexpected keyword raises
``TypeError``).

Honesty of form, per the batch brief and DECISION.md
qualification 1:

- **Claims adjudication & pricing (entry 972) is RE-JUDGED to a
  labeled reference implementation.** The entry names the engine
  itself -- adjudication as a determination and pricing as a
  computation. A determination is an engine act and a price is a
  computation over amounts this substrate does not hold; neither
  has a records form that is the function's own substance. The
  records half of claims handling -- claim records with outcomes
  recorded as reported -- already exists in this build from the
  founding section's unit (its entry 850) and is not duplicated
  here. What lands is the reference registry: adjudication
  reference records and pricing-schedule reference records,
  every one carrying ``reference_stub: True`` and state
  ``recorded_reference_only``, with determinations recorded
  verbatim as reported (``adjudicated_here`` / ``priced_here`` /
  ``paid_here`` are False on every record).
- **Benefits administration (entry 973) is built** in its
  records form: benefit package definitions held as data (their
  components are opaque references), administration records
  bound to a core eligibility record of the same participant,
  and a summary that derives coverage counts at read from the
  core eligibility records themselves. Nothing is administered
  against a real plan here; the records are the substrate's own.
- **Care & utilization management workflows (entry 974) ship as
  a labeled reference implementation**, as drafted: utilization
  review is a determination over clinical content this substrate
  may not hold, so workflow definitions are held as data and
  never executed, and review cases/outcomes are recorded as
  reported (``reviewed_here`` / ``determined_here`` are False).
- **Regulatory compliance reporting (entry 975) is built** as
  report definition records, filing records (a filing is an act
  in the world; ``filed_here`` / ``submitted_here`` are False),
  and a report view that derives counts at read over the core
  substrate's own records -- ``method: deterministic_counts``,
  basis ``substrate_records_only``. No figure is a clinical
  quantity and no control family is asserted anywhere.

Doctrines carried from the core and the first unit:
derived-never-stored for every computed value (adjudication
current outcome and counts, coverage counts by plan reference
and derived status, utilization outcome counts and latest
label, report-view counts); append-only audit on the core
store's log with ``exta_``-prefixed actions for every successful
mutation, and denied write attempts recorded with a ``:denied``
suffix; RBAC via :mod:`health.access` with the core's existing
actions, enforced before any state change or id allocation, so
a failed operation consumes no id and changes nothing; member
scope mirrors the store's -- a member-role actor may only read
records whose participant's ``participant_ref`` is their own
name.
"""

import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

ADJUDICATION_OUTCOMES = ("approved", "denied", "pended")

_REFERENCE_STATE = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
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


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class HealthExtensionsAddition:
    """Second-unit extension surface wrapping one :class:`HealthStore`."""

    def __init__(self, store):
        self.store = store
        self._pricing_schedules = {}
        self._adjudication_references = {}
        self._adjudication_outcomes = {}
        self._benefit_packages = {}
        self._benefit_administrations = {}
        self._utilization_definitions = {}
        self._utilization_cases = {}
        self._utilization_outcomes = {}
        self._report_definitions = {}
        self._report_filings = {}
        self._counters = {
            "prs": 0, "adj": 0, "ado": 0, "bpk": 0, "bad": 0,
            "uwd": 0, "umc": 0, "umo": 0, "rpd": 0, "rfl": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    def _guard(self, actor, rbac_action, audit_action):
        """Enforce a write permission before any state change.

        Mirrors the core store's convention (a User-like actor is
        checked via :func:`health.access.require`; a plain string
        carries identity but no role). A denied attempt is recorded
        on the audit log with a ``:denied`` suffix before the error
        propagates; a missing actor is denied outright.
        """
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

    @staticmethod
    def _maybe_require(actor, rbac_action):
        if actor is not None and hasattr(actor, "role"):
            require(actor, rbac_action)

    @staticmethod
    def _is_member(actor):
        return actor is not None and getattr(actor, "role", None) == "member"

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _check_participant(self, participant_id, actor):
        """Validate that a participant exists (core getter; the
        core enforces the actor's participant_read and, for a
        member actor, member scope)."""
        return self.store.get_participant(participant_id, actor)

    def _member_participant_ids(self, actor):
        """The participant ids a member actor may read (their own)."""
        return {p["id"] for p in self.store.list_participants(actor)}

    def _scoped(self, actor, records, key="participant_id"):
        if self._is_member(actor):
            own = self._member_participant_ids(actor)
            return [r for r in records if r.get(key) in own]
        return list(records)

    def _scope_check_record(self, actor, record, key="participant_id"):
        if self._is_member(actor):
            own = self._member_participant_ids(actor)
            if record.get(key) not in own:
                raise PermissionDenied(
                    "permission denied: member %r may not access records of "
                    "another participant" % (getattr(actor, "name", None),))

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    def _check_unique(self, table, field, value, what):
        for existing in table.values():
            if existing[field] == value:
                raise ValidationError("%s %r is already registered" % (what, value))

    def _check_eligibility_belongs(self, participant_id, eligibility):
        """Eligibility-binding guard seam.

        MUTATION DRILL NOTE: this guard is the load-bearing
        invariant of this unit's fresh negative control -- a
        payer-side record (an adjudication reference, a benefits
        administration record) may bind only to a core eligibility
        record of the SAME participant it names. An implementation
        that skips the comparison and binds across participants is
        the mutant the drill and ``test_gaps_batch_addition.py``
        reject.
        """
        if eligibility["participant_id"] != participant_id:
            raise ValidationError(
                "eligibility record %r does not belong to participant %r"
                % (eligibility["id"], participant_id))

    # -- Health plan claims adjudication & pricing engine ---------------
    # RE-JUDGED to a labeled reference implementation (see the
    # module docstring and BATCH-ADDITION.md): the entry names
    # the engine itself. An adjudication reference is a registry
    # record of an external engine's reported activity against an
    # opaque claim reference and a core eligibility record; a
    # pricing schedule is a reference record for a schedule held
    # elsewhere. Every record carries ``reference_stub: True``
    # and state ``recorded_reference_only`` -- nothing is
    # adjudicated, priced, or paid here, and no amount exists in
    # any shape for a price to be recorded against.

    def create_pricing_schedule_reference(self, schedule_ref, label, actor):
        """Register a reference record for an external pricing schedule.

        Action: program_write. Labeled reference implementation:
        the schedule itself is held by the external pricing
        engine; only its opaque reference and a label live here.
        """
        self._guard(actor, "program_write", "exta_pricing_schedule_create")
        _non_empty(schedule_ref, "schedule_ref")
        _non_empty(label, "pricing schedule label")
        with self._lock:
            self._check_unique(self._pricing_schedules, "schedule_ref",
                               schedule_ref, "schedule_ref")
            record_id = self._next_id("prs")
            record = {
                "id": record_id,
                "schedule_ref": schedule_ref,
                "label": label,
                "reference_stub": True,
                "priced_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._pricing_schedules[record_id] = record
            self._audit(actor, "exta_pricing_schedule_create", record_id,
                        details={"schedule_ref": schedule_ref})
            return dict(record)

    def create_adjudication_reference(self, participant_id, eligibility_id,
                                      claim_ref, actor, requested_on,
                                      schedule_id=None):
        """Register a reference record for an external adjudication.

        Action: eligibility_write. The eligibility record must
        belong to the participant (the binding guard seam). The
        claim is named by an opaque ``claim_ref`` only -- its
        content never enters this substrate -- and the
        determination arrives later, as a reported outcome
        record. ``adjudicated_here``, ``priced_here``, and
        ``paid_here`` are False on every record.
        """
        self._guard(actor, "eligibility_write", "exta_adjudication_create")
        _non_empty(claim_ref, "claim_ref")
        _validate_date(requested_on, "requested_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            eligibility = self.store.get_eligibility(eligibility_id, actor)
            self._check_eligibility_belongs(participant_id, eligibility)
            if schedule_id is not None:
                self._get(self._pricing_schedules, schedule_id,
                          "pricing schedule reference")
            self._check_unique(self._adjudication_references, "claim_ref",
                               claim_ref, "claim_ref")
            record_id = self._next_id("adj")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "eligibility_id": eligibility_id,
                "claim_ref": claim_ref,
                "schedule_id": schedule_id,
                "requested_on": requested_on,
                "reference_stub": True,
                "adjudicated_here": False,
                "priced_here": False,
                "paid_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._adjudication_references[record_id] = record
            self._audit(actor, "exta_adjudication_create", record_id,
                        details={"participant_id": participant_id,
                                 "claim_ref": claim_ref})
            return dict(record)

    def record_adjudication_outcome(self, reference_id, outcome, actor,
                                    decided_on):
        """Record an adjudication outcome as reported by the engine.

        Action: eligibility_write. The outcome is a recorded
        label from the reported-outcome vocabulary; the current
        outcome of a reference is derived at read from its latest
        outcome record, never stored.
        """
        self._guard(actor, "eligibility_write", "exta_adjudication_outcome")
        if outcome not in ADJUDICATION_OUTCOMES:
            raise ValidationError(
                "outcome must be one of %s" % (", ".join(ADJUDICATION_OUTCOMES),))
        _validate_date(decided_on, "decided_on")
        with self._lock:
            self._get(self._adjudication_references, reference_id,
                      "adjudication reference")
            record_id = self._next_id("ado")
            record = {
                "id": record_id,
                "reference_id": reference_id,
                "outcome": outcome,
                "decided_on": decided_on,
                "reported_by_ref": actor_name(actor),
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._adjudication_outcomes[record_id] = record
            self._audit(actor, "exta_adjudication_outcome", record_id,
                        details={"reference_id": reference_id,
                                 "outcome": outcome})
            return dict(record)

    def _adjudication_view(self, reference):
        view = dict(reference)
        outcomes = [o for o in self._sorted(self._adjudication_outcomes.values())
                    if o["reference_id"] == reference["id"]]
        view["outcome_count"] = len(outcomes)
        view["current_outcome"] = outcomes[-1]["outcome"] if outcomes else None
        return view

    def get_adjudication_reference(self, reference_id, actor=None):
        """Return one adjudication reference view.

        Action: eligibility_read (+ member scope).
        """
        self._maybe_require(actor, "eligibility_read")
        with self._lock:
            reference = self._get(self._adjudication_references, reference_id,
                                  "adjudication reference")
            self._scope_check_record(actor, reference)
            return self._adjudication_view(reference)

    def list_adjudication_references(self, actor=None, participant_id=None):
        """Return adjudication reference views, optionally filtered.

        Action: eligibility_read (+ member scope).
        """
        self._maybe_require(actor, "eligibility_read")
        with self._lock:
            records = self._sorted(self._adjudication_references.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            records = self._scoped(actor, records)
            return [self._adjudication_view(r) for r in records]

    def list_pricing_schedule_references(self, actor=None):
        """Return pricing schedule reference records. Action: program_read."""
        self._maybe_require(actor, "program_read")
        with self._lock:
            return [dict(r)
                    for r in self._sorted(self._pricing_schedules.values())]

    def adjudication_summary(self, actor, participant_id=None):
        """Derived adjudication counts by current reported outcome.

        Action: report_read (+ member scope when a participant is
        named). Computed at read -- ``method:
        deterministic_counts``. Counts of recorded outcomes only;
        no amount is summed anywhere, because no amount exists in
        this substrate.
        """
        self._guard(actor, "report_read", "exta_adjudication_summary")
        with self._lock:
            if participant_id is not None:
                participant = self._check_participant(participant_id, actor)
                if self._is_member(actor) and \
                        participant["participant_ref"] != getattr(actor, "name", None):
                    raise PermissionDenied(
                        "permission denied: member %r may not access records "
                        "of another participant" % (getattr(actor, "name", None),))
            references = list(self._adjudication_references.values())
            if participant_id is not None:
                references = [r for r in references
                              if r["participant_id"] == participant_id]
            by_outcome = {outcome: 0 for outcome in ADJUDICATION_OUTCOMES}
            undecided = 0
            for reference in references:
                current = self._adjudication_view(reference)["current_outcome"]
                if current is None:
                    undecided += 1
                else:
                    by_outcome[current] += 1
            return {
                "participant_id": participant_id,
                "method": "deterministic_counts",
                "references": len(references),
                "by_current_outcome": by_outcome,
                "undecided": undecided,
            }

    # -- Benefits administration platform -------------------------------
    # Records form: a benefit package is a definition held as
    # data -- its components are opaque references to benefit
    # elements held elsewhere; nothing in the definition is
    # applied to anyone here. An administration record binds a
    # participant, one of that participant's OWN core eligibility
    # records (the binding guard seam), and a package, and holds
    # the administrator's action label verbatim. The summary
    # derives coverage counts at read from the core eligibility
    # records themselves -- counts of records and of their core
    # derived statuses, never benefit content.

    def create_benefit_package(self, package_ref, title, component_refs,
                               actor):
        """Register a benefit package definition as data.

        Action: program_write.
        """
        self._guard(actor, "program_write", "exta_benefit_package_create")
        _non_empty(package_ref, "package_ref")
        _non_empty(title, "benefit package title")
        component_refs = _string_list(component_refs, "component_refs")
        if len(set(component_refs)) != len(component_refs):
            raise ValidationError("component_refs must be duplicate-free")
        with self._lock:
            self._check_unique(self._benefit_packages, "package_ref",
                               package_ref, "package_ref")
            record_id = self._next_id("bpk")
            record = {
                "id": record_id,
                "package_ref": package_ref,
                "title": title,
                "component_refs": list(component_refs),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._benefit_packages[record_id] = record
            self._audit(actor, "exta_benefit_package_create", record_id,
                        details={"package_ref": package_ref})
            return dict(record)

    def record_benefit_administration(self, participant_id, eligibility_id,
                                      package_id, action_label, actor,
                                      recorded_on):
        """Record one benefits administration action as performed.

        Action: eligibility_write. The eligibility record must
        belong to the participant (the binding guard seam). The
        action label is the administrator's own, recorded
        verbatim; this build administers nothing against a real
        plan -- it records that the action was recorded.
        """
        self._guard(actor, "eligibility_write", "exta_benefit_admin_record")
        _non_empty(action_label, "action_label")
        _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._check_participant(participant_id, actor)
            eligibility = self.store.get_eligibility(eligibility_id, actor)
            self._check_eligibility_belongs(participant_id, eligibility)
            self._get(self._benefit_packages, package_id, "benefit package")
            record_id = self._next_id("bad")
            record = {
                "id": record_id,
                "participant_id": participant_id,
                "eligibility_id": eligibility_id,
                "package_id": package_id,
                "action_label": action_label,
                "recorded_on": recorded_on,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._benefit_administrations[record_id] = record
            self._audit(actor, "exta_benefit_admin_record", record_id,
                        details={"participant_id": participant_id,
                                 "package_id": package_id})
            return dict(record)

    def list_benefit_packages(self, actor=None):
        """Return benefit package definitions. Action: program_read."""
        self._maybe_require(actor, "program_read")
        with self._lock:
            return [dict(r)
                    for r in self._sorted(self._benefit_packages.values())]

    def list_benefit_administrations(self, actor=None, participant_id=None,
                                     package_id=None):
        """Return administration records, optionally filtered.

        Action: eligibility_read (+ member scope).
        """
        self._maybe_require(actor, "eligibility_read")
        with self._lock:
            records = self._sorted(self._benefit_administrations.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            if package_id is not None:
                records = [r for r in records if r["package_id"] == package_id]
            return [dict(r) for r in self._scoped(actor, records)]

    def benefits_administration_summary(self, actor, as_of=None):
        """Derived benefits administration summary.

        Action: report_read. Package and administration counts
        from this unit's records, and coverage counts derived at
        read from the CORE eligibility records (by opaque plan
        reference and by the core's own derived status at
        ``as_of``) -- ``method: deterministic_counts``. Never
        stored; no benefit content or amount appears anywhere.
        """
        self._guard(actor, "report_read", "exta_benefits_admin_summary")
        with self._lock:
            eligibilities = self.store.list_eligibilities(actor, as_of=as_of)
            by_plan_ref = {}
            by_status = {"upcoming": 0, "current": 0, "ended": 0}
            for record in eligibilities:
                by_plan_ref[record["plan_ref"]] = \
                    by_plan_ref.get(record["plan_ref"], 0) + 1
                by_status[record["derived_status"]] += 1
            return {
                "method": "deterministic_counts",
                "packages": len(self._benefit_packages),
                "administration_records": len(self._benefit_administrations),
                "coverage_records": len(eligibilities),
                "coverage_by_plan_ref": by_plan_ref,
                "coverage_by_derived_status": by_status,
            }

    # -- Care & utilization management workflows (labeled reference) ----
    # Stub-engine, as drafted: utilization review is a
    # determination over clinical content this substrate may not
    # hold. A workflow definition holds its step references as
    # DATA and is never executed here; a case record registers
    # that an external review exists against a participant under
    # an opaque case reference; an outcome record holds the
    # review's outcome label verbatim as reported. Every record
    # carries ``reference_stub: True`` and state
    # ``recorded_reference_only``; ``reviewed_here`` and
    # ``determined_here`` are False -- this build reviews nothing
    # and determines nothing.

    def create_utilization_workflow_definition(self, workflow_ref, step_refs,
                                               actor):
        """Register a utilization workflow definition as data.

        Action: program_write. Labeled reference implementation.
        """
        self._guard(actor, "program_write", "exta_utilization_def_create")
        _non_empty(workflow_ref, "workflow_ref")
        step_refs = _string_list(step_refs, "step_refs")
        with self._lock:
            self._check_unique(self._utilization_definitions, "workflow_ref",
                               workflow_ref, "workflow_ref")
            record_id = self._next_id("uwd")
            record = {
                "id": record_id,
                "workflow_ref": workflow_ref,
                "step_refs": list(step_refs),
                "reference_stub": True,
                "executed_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._utilization_definitions[record_id] = record
            self._audit(actor, "exta_utilization_def_create", record_id,
                        details={"workflow_ref": workflow_ref})
            return dict(record)

    def record_utilization_case(self, definition_id, participant_id,
                                case_ref, actor, opened_on):
        """Register a utilization review case reference.

        Action: plan_write. Only the opaque ``case_ref`` and the
        participant binding live here; the review itself happens
        in the external engine over content this substrate never
        holds.
        """
        self._guard(actor, "plan_write", "exta_utilization_case_record")
        _non_empty(case_ref, "case_ref")
        _validate_date(opened_on, "opened_on")
        with self._lock:
            self._get(self._utilization_definitions, definition_id,
                      "utilization workflow definition")
            self._check_participant(participant_id, actor)
            self._check_unique(self._utilization_cases, "case_ref",
                               case_ref, "case_ref")
            record_id = self._next_id("umc")
            record = {
                "id": record_id,
                "definition_id": definition_id,
                "participant_id": participant_id,
                "case_ref": case_ref,
                "opened_on": opened_on,
                "reference_stub": True,
                "reviewed_here": False,
                "determined_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._utilization_cases[record_id] = record
            self._audit(actor, "exta_utilization_case_record", record_id,
                        details={"definition_id": definition_id,
                                 "participant_id": participant_id})
            return dict(record)

    def record_utilization_outcome(self, case_id, outcome_label, actor,
                                   decided_on):
        """Record a utilization review outcome as reported.

        Action: plan_write. The label is the external review's
        own, stored verbatim; nothing here interprets it.
        """
        self._guard(actor, "plan_write", "exta_utilization_outcome_record")
        _non_empty(outcome_label, "outcome_label")
        _validate_date(decided_on, "decided_on")
        with self._lock:
            self._get(self._utilization_cases, case_id, "utilization case")
            record_id = self._next_id("umo")
            record = {
                "id": record_id,
                "case_id": case_id,
                "outcome_label": outcome_label,
                "decided_on": decided_on,
                "reported_by_ref": actor_name(actor),
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._utilization_outcomes[record_id] = record
            self._audit(actor, "exta_utilization_outcome_record", record_id,
                        details={"case_id": case_id})
            return dict(record)

    def _utilization_case_view(self, case):
        view = dict(case)
        outcomes = [o for o in self._sorted(self._utilization_outcomes.values())
                    if o["case_id"] == case["id"]]
        view["outcome_count"] = len(outcomes)
        view["latest_outcome_label"] = (
            outcomes[-1]["outcome_label"] if outcomes else None)
        return view

    def get_utilization_case(self, case_id, actor=None):
        """Return one utilization case view. Action: plan_read (+ scope)."""
        self._maybe_require(actor, "plan_read")
        with self._lock:
            case = self._get(self._utilization_cases, case_id,
                             "utilization case")
            self._scope_check_record(actor, case)
            return self._utilization_case_view(case)

    def list_utilization_cases(self, actor=None, participant_id=None,
                               definition_id=None):
        """Return utilization case views. Action: plan_read (+ scope)."""
        self._maybe_require(actor, "plan_read")
        with self._lock:
            records = self._sorted(self._utilization_cases.values())
            if participant_id is not None:
                records = [r for r in records
                           if r["participant_id"] == participant_id]
            if definition_id is not None:
                records = [r for r in records
                           if r["definition_id"] == definition_id]
            records = self._scoped(actor, records)
            return [self._utilization_case_view(r) for r in records]

    def list_utilization_definitions(self, actor=None):
        """Return utilization workflow definitions. Action: program_read."""
        self._maybe_require(actor, "program_read")
        with self._lock:
            return [dict(r)
                    for r in self._sorted(self._utilization_definitions.values())]

    def utilization_summary(self, actor):
        """Derived utilization counts. Action: report_read.

        Counts of definitions, cases, and reported outcome
        records only -- ``method: deterministic_counts``. No
        clinical quantity exists here to aggregate.
        """
        self._guard(actor, "report_read", "exta_utilization_summary")
        with self._lock:
            return {
                "method": "deterministic_counts",
                "definitions": len(self._utilization_definitions),
                "cases": len(self._utilization_cases),
                "outcomes": len(self._utilization_outcomes),
            }

    # -- Regulatory compliance reporting engine for payers --------------
    # Records form: a report definition is a registry record
    # (an opaque report reference, a title, a scope label held as
    # data); a filing record records that a report was prepared
    # or filed in the world, with its status label verbatim --
    # ``filed_here`` and ``submitted_here`` are False, because
    # filing is an act against a regulator, not a records
    # operation. The report VIEW is the engine's in-substrate
    # form: counts derived at read over the core substrate's own
    # records (participants, enrollments, eligibility records by
    # their core derived status), labeled
    # ``deterministic_counts`` with basis
    # ``substrate_records_only``. Per the entry's own text this
    # is explicitly NOT a control claim: no record or view in
    # this section asserts, names, or traces to any control
    # family, and the fork's description asserts no control
    # language of any kind (ADDENDUM.md section 3).

    def create_report_definition(self, report_ref, title, scope_label,
                                 actor):
        """Register a regulatory report definition. Action: program_write."""
        self._guard(actor, "program_write", "exta_report_definition_create")
        _non_empty(report_ref, "report_ref")
        _non_empty(title, "report definition title")
        _non_empty(scope_label, "scope_label")
        with self._lock:
            self._check_unique(self._report_definitions, "report_ref",
                               report_ref, "report_ref")
            record_id = self._next_id("rpd")
            record = {
                "id": record_id,
                "report_ref": report_ref,
                "title": title,
                "scope_label": scope_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._report_definitions[record_id] = record
            self._audit(actor, "exta_report_definition_create", record_id,
                        details={"report_ref": report_ref})
            return dict(record)

    def record_report_filing(self, definition_id, filing_ref, status_label,
                             actor, recorded_on):
        """Record a report filing as it stands in the world.

        Action: activity_write. The status label is recorded
        verbatim as reported; the filing itself was made against
        the regulator by the payer's own process, not by this
        substrate.
        """
        self._guard(actor, "activity_write", "exta_report_filing_record")
        _non_empty(filing_ref, "filing_ref")
        _non_empty(status_label, "status_label")
        _validate_date(recorded_on, "recorded_on")
        with self._lock:
            self._get(self._report_definitions, definition_id,
                      "report definition")
            self._check_unique(self._report_filings, "filing_ref",
                               filing_ref, "filing_ref")
            record_id = self._next_id("rfl")
            record = {
                "id": record_id,
                "definition_id": definition_id,
                "filing_ref": filing_ref,
                "status_label": status_label,
                "recorded_on": recorded_on,
                "filed_here": False,
                "submitted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._report_filings[record_id] = record
            self._audit(actor, "exta_report_filing_record", record_id,
                        details={"definition_id": definition_id,
                                 "filing_ref": filing_ref})
            return dict(record)

    def list_report_definitions(self, actor=None):
        """Return report definitions. Action: program_read."""
        self._maybe_require(actor, "program_read")
        with self._lock:
            return [dict(r)
                    for r in self._sorted(self._report_definitions.values())]

    def list_report_filings(self, actor=None, definition_id=None):
        """Return filing records, optionally filtered. Action: activity_read."""
        self._maybe_require(actor, "activity_read")
        with self._lock:
            records = self._sorted(self._report_filings.values())
            if definition_id is not None:
                records = [r for r in records
                           if r["definition_id"] == definition_id]
            return [dict(r) for r in records]

    def regulatory_report_view(self, definition_id, actor, as_of=None):
        """Derived report figures over the substrate's own records.

        Action: report_read. Every figure is a count of core
        records (or of this unit's filing records for the named
        definition), computed at read -- ``method:
        deterministic_counts``, ``basis: substrate_records_only``.
        Nothing is filed or submitted by producing this view, and
        no figure is a clinical quantity or a control assertion.
        """
        self._guard(actor, "report_read", "exta_regulatory_report_view")
        with self._lock:
            definition = self._get(self._report_definitions, definition_id,
                                   "report definition")
            participants = self.store.list_participants(actor)
            enrollments = self.store.list_enrollments(actor, as_of=as_of)
            eligibilities = self.store.list_eligibilities(actor, as_of=as_of)
            coverage_by_status = {"upcoming": 0, "current": 0, "ended": 0}
            for record in eligibilities:
                coverage_by_status[record["derived_status"]] += 1
            filings = [f for f in self._sorted(self._report_filings.values())
                       if f["definition_id"] == definition_id]
            return {
                "definition_id": definition_id,
                "report_ref": definition["report_ref"],
                "method": "deterministic_counts",
                "basis": "substrate_records_only",
                "participants": len(participants),
                "enrollments": len(enrollments),
                "coverage_records": len(eligibilities),
                "coverage_by_derived_status": coverage_by_status,
                "filings": len(filings),
                "latest_filing_status_label": (
                    filings[-1]["status_label"] if filings else None),
            }
