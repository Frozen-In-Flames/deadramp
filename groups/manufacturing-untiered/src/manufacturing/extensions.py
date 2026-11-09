"""Final GAPS batch extensions for the Manufacturing untiered set
(Untiered Set 26).

Clean-room, standard-library-only records extensions for the 1
open entry this set's GAPS.md section carries. See ``BATCH.md``
in the group directory for the per-entry disposition, including
the re-judgment recorded there under
``gaps-batch/DECISION.md`` qualification 1.

This set is **untiered**: the member fork's FedRAMP impact level
is Unknown in the source, tier stays null, no baseline is
asserted, and no CMMC equivalence is drawn. Nothing in this
module names a tier, a baseline, or an impact level; the records
and views it produces carry no such key (pinned by recursive scan
in ``tests/test_gaps_batch.py``).

Design, following the core's doctrines:

- This module is a wrapper around
  :class:`ManufacturingStore`; the core modules are untouched
  (byte-identical). Core state (organizations, intent records,
  decision records) is read through the core store's public API,
  never re-implemented, and no extension operation writes core
  state (pinned by test: a full extension flow leaves every core
  record byte-identical).
- **The transformation engine is not built here.** The core
  records a transformation as a decision record's basis links to
  the intent records it rests on; it performs no transformation,
  exercises no intelligence, and judges no manufacturability
  (UNION-SPEC.md, core-boundary decision). The gap entry names
  the engine entire — the conversion of engineering intent into
  decisions, by whatever analysis the fork performs — and no
  deterministic derivation over the records this substrate holds
  constitutes that conversion: intent statements are
  caller-supplied engineering text stored verbatim, and a
  decision statement cannot be derived from them by any rule
  this build could state honestly. The surface therefore ships
  as a **labeled reference implementation**: transformation
  *request* records (the work an external engine is asked to do,
  defined over held intent records under the same basis
  discipline the core's decision-basis guard enforces) plus
  *outcome* records holding the external engine's reported
  outcome label verbatim. Every record carries
  ``reference_stub: True`` and ``state:
  "recorded_reference_only"``, with ``transformed_here``,
  ``intelligence_exercised_here``, and
  ``manufacturability_judged_here`` all False on its face.
- A request's basis follows the core's decision-basis guard in
  records form: non-empty, distinct, every intent existing and
  belonging to the request's organization, or the request is
  refused, records nothing, and consumes no id. An outcome may
  optionally name the core decision record the external engine's
  work produced; when it does, that decision must exist and
  belong to the same organization.
- Outcome labels are held **verbatim as reported** by the
  external engine (``outcome_basis: "engine_reported"``),
  validated against the reported-outcome vocabulary the surface
  defines. Nothing here computes an outcome, a score, a rate, or
  a yield: the summary is counts of this surface's own records
  only, stated as such.
- Views derive at read and store nothing derived: a request
  view adds ``outcome_count`` and ``latest_outcome_label``,
  the latter through the single seam
  :meth:`ManufacturingExtensions._latest_outcome_label` — the
  batch's fresh negative-control target. The stored request
  record's exact key set is pinned free of derived keys.
- RBAC goes through :mod:`manufacturing.access` exactly as the
  core enforces it: each extension operation maps onto an
  existing core action — creates onto ``decisions``, reads and
  derived views onto ``read`` — checked *before* any state
  change or id allocation for User-like actors. Plain-string
  actors carry identity but no role, mirroring the core
  convention.
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``.
- People are known only by opaque references, validated exactly
  as the core validates them (no whitespace, no ``@``, so no
  reference can be an email address). No field shape on this
  surface can hold engineering statement text, telemetry, or
  content of any kind: requests and outcomes name intent and
  decision records by id and people by opaque reference only,
  and the absence of any content-shaped parameter is pinned by
  signature scan and ``TypeError`` tests.
- Scoring and money discipline are the core's own, unchanged:
  nothing in this surface computes a score, rating, ranking, or
  rate, and no record carries a money shape; both absences are
  pinned by the recursive key scan the core's shape tests use,
  extended to this surface.
"""

import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

OUTCOME_LABELS = (
    "reported_transformed",
    "reported_partial",
    "reported_no_decision",
    "reported_failed",
)
KNOWN_OUTCOME_LABELS = frozenset(OUTCOME_LABELS)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _person_ref(value, field="person_ref"):
    """An opaque person reference, validated exactly as the core
    store validates one: non-empty, no whitespace, no ``@`` — a
    value of that shape cannot be an email address."""
    _text(value, field)
    if "@" in value or any(ch.isspace() for ch in value):
        raise ValidationError(
            "%s must be an opaque reference (no whitespace, no '@')"
            % field)
    return value


class ManufacturingExtensions:
    """GAPS-batch extension surface over a core ManufacturingStore."""

    def __init__(self, store):
        self.store = store
        self._requests = {}
        self._outcomes = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor, action, target, details)

    @staticmethod
    def _require_actor(actor, action):
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (action,))
        if hasattr(actor, "role"):
            require(actor, action)

    def _get_request(self, request_id):
        record = self._requests.get(request_id)
        if record is None:
            raise NotFoundError(
                "no such transformation request: %r" % (request_id,))
        return record

    def _check_basis(self, actor, org_id, basis_intent_ids):
        """The request-basis check, in the core decision-basis
        guard's records form: the basis must be a non-empty list
        of distinct intent record ids, every one existing and
        belonging to the request's organization. Reads go through
        the core store's public API; an unknown intent surfaces
        as the core's NotFoundError, re-raised as a validation
        refusal here so a failed request consumes no id."""
        if not basis_intent_ids:
            raise ValidationError(
                "a transformation request must rest on at least one "
                "engineering intent record: the transformation this "
                "set records is of engineering intent into decisions, "
                "and a request with no basis intent transforms nothing")
        basis = list(basis_intent_ids)
        if len(set(basis)) != len(basis):
            raise ValidationError("basis_intent_ids contains duplicates")
        for intent_id in basis:
            _text(intent_id, "basis intent id")
            try:
                intent = self.store.get_intent(actor, intent_id)
            except NotFoundError:
                raise ValidationError(
                    "basis intent %r does not exist" % (intent_id,))
            if intent["org_id"] != org_id:
                raise ValidationError(
                    "basis intent %r does not belong to organization %r"
                    % (intent_id, org_id))
        return basis

    @staticmethod
    def _copy_request(record):
        copied = dict(record)
        copied["basis_intent_ids"] = list(record["basis_intent_ids"])
        return copied

    # -- transformation requests (reference form) ----------------------

    def register_transformation_request(self, actor, org_id, label,
                                        basis_intent_ids,
                                        requested_by_ref):
        """Register a transformation request for an external engine.

        Action: ``decisions``. The request defines work an
        external transformation engine is asked to perform over
        held engineering intent records; nothing is transformed
        here. ``basis_intent_ids`` must satisfy the request-basis
        check (non-empty, distinct, existing, same organization).
        ``requested_by_ref`` is the requester's opaque reference.
        """
        self._require_actor(actor, "decisions")
        _text(label, "label")
        _person_ref(requested_by_ref, "requested_by_ref")
        with self._lock:
            self.store.get_organization(actor, org_id)
            basis = self._check_basis(actor, org_id, basis_intent_ids)
            record = {
                "id": self._mint("trq-"),
                "org_id": org_id,
                "label": label,
                "basis_intent_ids": basis,
                "requested_by_ref": requested_by_ref,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "transformed_here": False,
                "intelligence_exercised_here": False,
                "manufacturability_judged_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._requests[record["id"]] = record
        self._audit(actor, "ext_transformation_request", record["id"],
                    {"org_id": org_id, "basis_intent_ids": list(basis)})
        return self._copy_request(record)

    # -- transformation outcomes (reference form) ----------------------

    def record_transformation_outcome(self, actor, request_id,
                                      outcome_label,
                                      reported_decision_ref=None,
                                      core_decision_id=None):
        """Record an external engine's reported outcome for a request.

        Action: ``decisions``. ``outcome_label`` is stored
        verbatim as the external platform reported it, validated
        against the reported-outcome vocabulary.
        ``reported_decision_ref`` is an opaque reference to a
        decision the engine produced elsewhere, if it names one.
        ``core_decision_id``, when supplied, must name a core
        decision record of the request's organization — the
        landing place a reported transformation may cite; the
        outcome record creates no core decision.
        """
        self._require_actor(actor, "decisions")
        _text(outcome_label, "outcome_label")
        if outcome_label not in KNOWN_OUTCOME_LABELS:
            raise ValidationError(
                "outcome_label must be one of %r" % (OUTCOME_LABELS,))
        if reported_decision_ref is not None:
            _person_ref(reported_decision_ref, "reported_decision_ref")
        with self._lock:
            request = self._get_request(request_id)
            if core_decision_id is not None:
                _text(core_decision_id, "core_decision_id")
                decision = self.store.get_decision(actor, core_decision_id)
                if decision["org_id"] != request["org_id"]:
                    raise ValidationError(
                        "core decision %r does not belong to organization %r"
                        % (core_decision_id, request["org_id"]))
            record = {
                "id": self._mint("tro-"),
                "request_id": request_id,
                "org_id": request["org_id"],
                "outcome_label": outcome_label,
                "outcome_basis": "engine_reported",
                "reported_decision_ref": reported_decision_ref,
                "core_decision_id": core_decision_id,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "transformed_here": False,
                "intelligence_exercised_here": False,
                "manufacturability_judged_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._outcomes[record["id"]] = record
        self._audit(actor, "ext_transformation_outcome", record["id"],
                    {"request_id": request_id,
                     "outcome_label": outcome_label})
        return dict(record)

    # -- derived views ---------------------------------------------------

    @staticmethod
    def _latest_outcome_label(outcomes):
        """Latest-outcome seam: the outcome label of the most
        recently recorded outcome, or None when there are none.
        Pure derivation over the recorded outcomes; nothing about
        the latest outcome is stored anywhere. This is the batch's
        negative-control target."""
        return outcomes[-1]["outcome_label"] if outcomes else None

    def _request_view(self, record):
        view = self._copy_request(record)
        outcomes = [o for o in self._outcomes.values()
                    if o["request_id"] == record["id"]]
        view["outcome_count"] = len(outcomes)
        view["latest_outcome_label"] = self._latest_outcome_label(outcomes)
        return view

    def get_transformation_request(self, actor, request_id):
        """Return one transformation request view. Action: ``read``."""
        self._require_actor(actor, "read")
        with self._lock:
            return self._request_view(self._get_request(request_id))

    def list_transformation_requests(self, actor, org_id=None):
        """Return transformation request views. Action: ``read``."""
        self._require_actor(actor, "read")
        with self._lock:
            records = list(self._requests.values())
            if org_id is not None:
                records = [r for r in records if r["org_id"] == org_id]
            return [self._request_view(r) for r in records]

    def list_transformation_outcomes(self, actor, request_id=None):
        """Return transformation outcome records. Action: ``read``."""
        self._require_actor(actor, "read")
        with self._lock:
            records = list(self._outcomes.values())
            if request_id is not None:
                records = [r for r in records
                           if r["request_id"] == request_id]
            return [dict(r) for r in records]

    def transformation_summary(self, actor):
        """Counts computed on read over this surface's own records.

        Action: ``read``. Counts only: no scores, no rates, no
        rankings — the counts are counts of the reference records
        held here, stated as such.
        """
        self._require_actor(actor, "read")
        with self._lock:
            with_outcomes = {o["request_id"]
                             for o in self._outcomes.values()}
            by_label = {label: 0 for label in OUTCOME_LABELS}
            for outcome in self._outcomes.values():
                by_label[outcome["outcome_label"]] += 1
            return {
                "transformation_requests": len(self._requests),
                "transformation_outcomes": len(self._outcomes),
                "requests_with_outcomes": len(with_outcomes),
                "outcomes_by_label": by_label,
            }
