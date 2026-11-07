"""Final GAPS batch extensions for the Finance L3-adjacent
singleton build (Group 42).

Clean-room, standard-library-only records extensions for the 4
open entries this group's GAPS.md section carries: the founding
fork's own substance — a cloud infrastructure platform filed
under Finance, whose marketplace description tagged zero finance
claims (see ``UNION-SPEC.md``). 3 entries land built as
in-substrate records extensions and 1 ships as a labeled
reference implementation (the drafted stub-engine family). See
``BATCH.md`` in the group directory for the per-entry disposition.

Design, following the core's doctrines and the Finance L2 batch
module's proven conventions:

- This module is a wrapper around :class:`FinanceStore`; the core
  modules are untouched (byte-identical). Core state (programs)
  is always read through the core store's public API, never
  re-implemented, and no extension operation writes core state.
- **The platform layer is recorded, never operated.** The cloud
  infrastructure platform itself, its regions' sovereignty
  properties, its root-account screening operation, and its
  collaborative monitoring arrangement are the deployment layer
  this build runs *on* (PLATFORM-LAYER.md decision 6), not
  functions a records substrate performs. What lands here is the
  records layer in front of them: region and service-catalog
  records, provider attestation records stored verbatim,
  screening case and outcome records, and — as the batch's
  labeled reference implementation — monitoring arrangement and
  report records. Each record carries its honesty label on its
  face (``operated_here`` / ``verified_here`` / ``enforced_here``
  / ``screened_here`` / ``determined_here`` / ``monitored_here``
  — all ``False``).
- **Nothing is screened or determined here.** A screening case
  names a root account holder by an opaque caller reference
  only, and a screening report stores the platform operator's
  reported outcome label verbatim; this surface runs no check
  and computes no determination. No record shape has a field
  that could hold a real name, a government identifier, or any
  bank or account identifier — the absences are pinned by exact
  key-set tests and recursive key scans.
- **No money exists on this surface.** None of the four entries
  is a money function, so no record shape carries a ``*_cents``
  field (or any amount field) at all — pinned by the same scans.
  The category's standing named absences stand untouched:
  trading & investment execution above all. This module has no
  order, execution, or payment operation of any kind, and a
  test pins that absence.
- Derived values are derived at read and never stored: the
  platform posture counts, the screening summary, and the
  monitoring summary are computed over this surface's own
  records by the module-level seam :func:`_count_by_label` —
  the batch's fresh negative-control target. Stored records
  carry no derived key; tests pin that. Counts only: no posture
  value, rate, trend, forecast, average, or grand total is
  computed anywhere on this surface.
- RBAC goes through :mod:`finance.access` exactly as the core
  enforces it: each extension operation maps onto an existing
  core action — registrations / records onto ``enter``, outcome
  and attestation reports onto ``record``, reads and derived
  views onto ``read`` — checked *before* any state change or id
  allocation for User-like actors, with denied attempts recorded
  on the core audit log as ``ext_<action>:denied``. Program
  membership (the second boundary) is enforced through the core
  store's own access-checked program read. The High apparatus
  binds this surface through the core: extension actions land
  on the hash-chained, fail-closed audit log, and the separated
  ``auditor`` role — ``audit_read`` only — is denied every
  extension read and write while its core audit duty (reading
  and verifying the chain) works unchanged. Plain-string actors
  carry identity but no role, mirroring the core convention.
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``. If
  the audit write raises, the record insertion and its id roll
  back before the error propagates: no extension record exists
  whose audit entry does not.
- The stub-engine family ships as a labeled reference
  implementation: every record it creates carries
  ``reference_stub: True`` and ``reference_transport: True``.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

SERVICE_CATEGORIES = (
    "compute",
    "storage",
    "networking",
    "database",
    "other",
)
KNOWN_SERVICE_CATEGORIES = frozenset(SERVICE_CATEGORIES)
ATTESTATION_KINDS = (
    "personnel_eligibility",
    "physical_operation",
    "handling_environment",
    "authorization_boundary",
)
KNOWN_ATTESTATION_KINDS = frozenset(ATTESTATION_KINDS)
SCREENING_REPORT_OUTCOMES = (
    "reported_eligible",
    "reported_ineligible",
    "reported_pending",
)
KNOWN_SCREENING_REPORT_OUTCOMES = frozenset(SCREENING_REPORT_OUTCOMES)
MONITORING_REPORT_OUTCOMES = (
    "reported_healthy",
    "reported_degraded",
    "reported_incident",
    "reported_outage",
)
KNOWN_MONITORING_REPORT_OUTCOMES = frozenset(MONITORING_REPORT_OUTCOMES)


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


def _count_nonnegative(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer count" % (what,))
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _one_of(value, known, names, what):
    if value not in known:
        raise ValidationError(
            "%s must be one of %s" % (what, ", ".join(names)))
    return value


def _count_by_label(records, key, labels):
    """Count ``records`` per label of ``key`` over fixed ``labels``.

    Every label in ``labels`` appears in the result (zero when no
    record carries it), so a derived view's key set is stable.
    Counts only — the seam sums occurrences of recorded labels;
    it computes no value, rate, or total over record contents.
    This is the negative control's target.
    """
    counts = {label: 0 for label in labels}
    for record in records:
        counts[record[key]] += 1
    return counts


class FinanceExtensions:
    """GAPS-batch extension surface over a core FinanceStore."""

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
        """Enforce a permission, auditing a denial.

        Mirrors the core convention: an actor must be present;
        User-like actors are checked against the core permission
        matrix before anything changes; plain strings carry
        identity only.
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

    def _program(self, program_id, actor):
        """Core access-checked program read (membership + read role).

        Raises NotFoundError for an unknown program and
        PermissionDenied for a non-member, exactly as the core does.
        """
        return self.store.get_program(program_id, actor)

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
            try:
                self._audit(actor, audit_action, record_id,
                            details={"kind": kind})
            except Exception:
                # Fail closed: an operation whose audit write fails
                # does not proceed -- the insertion and the id roll
                # back before the error propagates.
                del self._records[(kind, record_id)]
                self._order.pop()
                self._counters[prefix] -= 1
                raise
            return copy.deepcopy(record)

    def _get(self, kind, record_id, program_id):
        record = self._records.get((kind, record_id))
        if record is None or record["program_id"] != program_id:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id, program_id):
        return copy.deepcopy(self._get(kind, record_id, program_id))

    def _list(self, kind, program_id, **filters):
        result = []
        for key in self._order:
            if key[0] != kind:
                continue
            record = self._records[key]
            if record["program_id"] != program_id:
                continue
            if all(record.get(f) == v for f, v in filters.items()):
                result.append(copy.deepcopy(record))
        return result

    # -- The cloud infrastructure platform itself (built) --------------
    #
    # The fork's actual product: regions operated as
    # infrastructure, with a service catalog. A records substrate
    # does not operate infrastructure; what lands is the catalog
    # layer in front of it — region records and per-region service
    # records held as data. ``operated_here`` is False on every
    # record and nothing is provisioned, started, or run.

    def register_region(self, program_id, region_ref, name_label, actor):
        """Register one provider region as a catalog record.

        ``region_ref`` is the caller's opaque reference for the
        region, unique within the program.
        """
        self._guard(actor, "enter", "ext_region_register")
        self._program(program_id, actor)
        _non_empty(region_ref, "region_ref")
        _non_empty(name_label, "name_label")
        for existing in self._list("region", program_id):
            if existing["region_ref"] == region_ref:
                raise ValidationError(
                    "region ref %r already exists in program %r"
                    % (region_ref, program_id)
                )
        return self._create(
            "region", "regn",
            {"program_id": program_id, "region_ref": region_ref,
             "name_label": name_label, "operated_here": False,
             "state": "recorded_reference_only"},
            actor, "ext_region_register")

    def record_region_service(self, program_id, region_id, service_ref,
                              category, actor, label=None):
        """Record one catalog service of a registered region.

        ``category`` is one of the catalog categories (compute,
        storage, networking, database, other); the service itself
        is named by an opaque caller reference and an optional
        label held as data.
        """
        self._guard(actor, "enter", "ext_region_service_record",
                    target=region_id)
        self._program(program_id, actor)
        _non_empty(service_ref, "service_ref")
        _one_of(category, KNOWN_SERVICE_CATEGORIES, SERVICE_CATEGORIES,
                "category")
        _string_or_none(label, "label")
        self._get("region", region_id, program_id)
        return self._create(
            "region_service", "rsvc",
            {"program_id": program_id, "region_id": region_id,
             "service_ref": service_ref, "category": category,
             "label": label, "operated_here": False},
            actor, "ext_region_service_record")

    def get_region(self, program_id, region_id, actor):
        """One region record. Action: read."""
        self._guard(actor, "read", "ext_region_get", target=region_id)
        self._program(program_id, actor)
        return self._fetch("region", region_id, program_id)

    def list_regions(self, program_id, actor):
        """All region records of a program. Action: read."""
        self._guard(actor, "read", "ext_region_list")
        self._program(program_id, actor)
        return self._list("region", program_id)

    def list_region_services(self, program_id, actor, region_id=None):
        """Service records, optionally of one region. Action: read."""
        self._guard(actor, "read", "ext_region_service_list")
        self._program(program_id, actor)
        filters = {}
        if region_id is not None:
            filters["region_id"] = region_id
        return self._list("region_service", program_id, **filters)

    # -- Region operations & sovereignty properties (built) ------------
    #
    # The regions' operating properties — US-citizen / US-soil
    # operation, the ITAR-regulated environment, the regions' own
    # FedRAMP High boundary — are the provider's properties of its
    # platform. What lands is the attestation layer: records of
    # the provider's property statements, stored verbatim as
    # stated. Nothing here verifies or enforces a property
    # (``verified_here`` / ``enforced_here`` are False on every
    # record), and no region record is changed by recording one.

    def record_region_attestation(self, program_id, region_id,
                                  attestation_kind, statement_label,
                                  actor):
        """Record a provider attestation about a region, verbatim.

        ``attestation_kind`` names the property family the
        statement belongs to (personnel eligibility, physical
        operation, handling environment, authorization boundary);
        ``statement_label`` is the provider's statement held as
        data, exactly as stated.
        """
        self._guard(actor, "record", "ext_region_attestation_record",
                    target=region_id)
        self._program(program_id, actor)
        _one_of(attestation_kind, KNOWN_ATTESTATION_KINDS,
                ATTESTATION_KINDS, "attestation_kind")
        _non_empty(statement_label, "statement_label")
        self._get("region", region_id, program_id)
        return self._create(
            "region_attestation", "ratt",
            {"program_id": program_id, "region_id": region_id,
             "attestation_kind": attestation_kind,
             "statement_label": statement_label,
             "attested_by_provider": True, "verified_here": False,
             "enforced_here": False},
            actor, "ext_region_attestation_record")

    def list_region_attestations(self, program_id, actor, region_id=None):
        """Attestation records, optionally of one region.

        Action: read.
        """
        self._guard(actor, "read", "ext_region_attestation_list")
        self._program(program_id, actor)
        filters = {}
        if region_id is not None:
            filters["region_id"] = region_id
        return self._list("region_attestation", program_id, **filters)

    def platform_posture(self, program_id, actor):
        """Derived at read: counts over region, service, and
        attestation records. Counts only — no property is assessed
        and no posture value is computed. Action: read."""
        self._guard(actor, "read", "ext_platform_posture")
        self._program(program_id, actor)
        regions = self._list("region", program_id)
        services = self._list("region_service", program_id)
        attestations = self._list("region_attestation", program_id)
        return {
            "program_id": program_id,
            "regions": len(regions),
            "services": len(services),
            "services_by_category": _count_by_label(
                services, "category", SERVICE_CATEGORIES),
            "attestations": len(attestations),
            "attestations_by_kind": _count_by_label(
                attestations, "attestation_kind", ATTESTATION_KINDS),
            "operated_here": False,
            "verified_here": False,
            "derived": True,
            "method": "counts_over_region_service_attestation_records",
        }

    # -- Eligibility screening of root account holders (built) ---------
    #
    # The platform's customer-screening operation, in its records
    # form: a screening case names a root account holder by an
    # opaque caller reference (never a name or an identifier), and
    # a screening report stores the operator's reported outcome
    # label verbatim. No check is run and no determination is
    # computed here (``screened_here`` / ``determined_here`` are
    # False on every record); a report leaves the case record
    # byte-identical.

    def record_screening_case(self, program_id, account_ref, actor,
                              basis_label=None):
        """Record a root-account screening case.

        ``account_ref`` is the caller's opaque reference for the
        account holder, unique within the program; ``basis_label``
        optionally names the stated basis for the screening, held
        as data.
        """
        self._guard(actor, "enter", "ext_screening_case_record")
        self._program(program_id, actor)
        _non_empty(account_ref, "account_ref")
        _string_or_none(basis_label, "basis_label")
        for existing in self._list("screening_case", program_id):
            if existing["account_ref"] == account_ref:
                raise ValidationError(
                    "account ref %r already has a screening case in "
                    "program %r" % (account_ref, program_id)
                )
        return self._create(
            "screening_case", "scrn",
            {"program_id": program_id, "account_ref": account_ref,
             "basis_label": basis_label, "screened_here": False,
             "determined_here": False, "state": "recorded_case_only"},
            actor, "ext_screening_case_record")

    def record_screening_report(self, program_id, case_id, outcome,
                                actor, detail=None):
        """Record a screening outcome, verbatim as reported.

        ``outcome`` is the screening operator's reported label
        from the fixed vocabulary; the determination was made
        there, not here.
        """
        self._guard(actor, "record", "ext_screening_report_record",
                    target=case_id)
        self._program(program_id, actor)
        _one_of(outcome, KNOWN_SCREENING_REPORT_OUTCOMES,
                SCREENING_REPORT_OUTCOMES, "outcome")
        _string_or_none(detail, "detail")
        self._get("screening_case", case_id, program_id)
        return self._create(
            "screening_report", "srpt",
            {"program_id": program_id, "case_id": case_id,
             "outcome": outcome, "detail": detail,
             "screened_here": False, "determined_here": False},
            actor, "ext_screening_report_record")

    def get_screening_case(self, program_id, case_id, actor):
        """One screening case record. Action: read."""
        self._guard(actor, "read", "ext_screening_case_get",
                    target=case_id)
        self._program(program_id, actor)
        return self._fetch("screening_case", case_id, program_id)

    def list_screening_cases(self, program_id, actor):
        """All screening case records of a program. Action: read."""
        self._guard(actor, "read", "ext_screening_case_list")
        self._program(program_id, actor)
        return self._list("screening_case", program_id)

    def list_screening_reports(self, program_id, actor, case_id=None):
        """Screening report records, optionally of one case.

        Action: read.
        """
        self._guard(actor, "read", "ext_screening_report_list")
        self._program(program_id, actor)
        filters = {}
        if case_id is not None:
            filters["case_id"] = case_id
        return self._list("screening_report", program_id, **filters)

    def screening_summary(self, program_id, actor):
        """Derived at read: case/report counts and the count of
        reports per reported outcome. Counts only — no eligibility
        rate or determination is computed. Action: read."""
        self._guard(actor, "read", "ext_screening_summary")
        self._program(program_id, actor)
        cases = self._list("screening_case", program_id)
        reports = self._list("screening_report", program_id)
        return {
            "program_id": program_id,
            "cases": len(cases),
            "reports": len(reports),
            "reports_by_outcome": _count_by_label(
                reports, "outcome", SCREENING_REPORT_OUTCOMES),
            "screened_here": False,
            "determined_here": False,
            "derived": True,
            "method": "counts_over_screening_case_report_records",
        }

    # -- Collaborative continuous monitoring (reference) ---------------
    #
    # Labeled reference implementation (the drafted stub-engine
    # entry). Collaborative continuous monitoring with the
    # provider is a provider-side arrangement over external
    # transport: what lands is the records layer in front of it —
    # arrangement records and status report records whose outcome
    # labels and event counts are stored as reported. Every
    # record carries ``reference_stub: True`` and
    # ``reference_transport: True``; ``monitored_here`` is False
    # on every record and nothing is monitored.

    def register_monitoring_arrangement(self, program_id,
                                        arrangement_ref, actor,
                                        scope_label=None):
        """Register a monitoring arrangement reference (stub).

        ``arrangement_ref`` is the caller's opaque reference for
        the arrangement, unique within the program;
        ``scope_label`` optionally names the arrangement's stated
        scope, held as data.
        """
        self._guard(actor, "enter", "ext_monitoring_arrangement_register")
        self._program(program_id, actor)
        _non_empty(arrangement_ref, "arrangement_ref")
        _string_or_none(scope_label, "scope_label")
        for existing in self._list("monitoring_arrangement", program_id):
            if existing["arrangement_ref"] == arrangement_ref:
                raise ValidationError(
                    "arrangement ref %r already exists in program %r"
                    % (arrangement_ref, program_id)
                )
        return self._create(
            "monitoring_arrangement", "marr",
            {"program_id": program_id,
             "arrangement_ref": arrangement_ref,
             "scope_label": scope_label, "reference_stub": True,
             "reference_transport": True, "monitored_here": False,
             "state": "recorded_arrangement_only"},
            actor, "ext_monitoring_arrangement_register")

    def record_monitoring_report(self, program_id, arrangement_id,
                                 outcome, actor, events_reported=None,
                                 detail=None):
        """Record a monitoring status report, as reported (stub).

        ``outcome`` is the arrangement's reported status label
        from the fixed vocabulary; ``events_reported`` is a count
        stored as reported by the monitoring side. No system was
        observed by this build.
        """
        self._guard(actor, "record", "ext_monitoring_report_record",
                    target=arrangement_id)
        self._program(program_id, actor)
        _one_of(outcome, KNOWN_MONITORING_REPORT_OUTCOMES,
                MONITORING_REPORT_OUTCOMES, "outcome")
        if events_reported is not None:
            _count_nonnegative(events_reported, "events_reported")
        _string_or_none(detail, "detail")
        self._get("monitoring_arrangement", arrangement_id, program_id)
        return self._create(
            "monitoring_report", "mrpt",
            {"program_id": program_id,
             "arrangement_id": arrangement_id, "outcome": outcome,
             "events_reported": events_reported, "detail": detail,
             "reference_stub": True, "reference_transport": True,
             "monitored_here": False},
            actor, "ext_monitoring_report_record")

    def get_monitoring_arrangement(self, program_id, arrangement_id,
                                   actor):
        """One monitoring arrangement record. Action: read."""
        self._guard(actor, "read", "ext_monitoring_arrangement_get",
                    target=arrangement_id)
        self._program(program_id, actor)
        return self._fetch(
            "monitoring_arrangement", arrangement_id, program_id)

    def list_monitoring_arrangements(self, program_id, actor):
        """All monitoring arrangement records. Action: read."""
        self._guard(actor, "read", "ext_monitoring_arrangement_list")
        self._program(program_id, actor)
        return self._list("monitoring_arrangement", program_id)

    def list_monitoring_reports(self, program_id, actor,
                                arrangement_id=None):
        """Monitoring report records, optionally of one arrangement.

        Action: read.
        """
        self._guard(actor, "read", "ext_monitoring_report_list")
        self._program(program_id, actor)
        filters = {}
        if arrangement_id is not None:
            filters["arrangement_id"] = arrangement_id
        return self._list("monitoring_report", program_id, **filters)

    def monitoring_summary(self, program_id, actor):
        """Derived at read: arrangement/report counts, the count
        of reports per reported outcome, and the total of reported
        event counts. Nothing is stored. Action: read."""
        self._guard(actor, "read", "ext_monitoring_summary")
        self._program(program_id, actor)
        arrangements = self._list("monitoring_arrangement", program_id)
        reports = self._list("monitoring_report", program_id)
        return {
            "program_id": program_id,
            "arrangements": len(arrangements),
            "reports": len(reports),
            "reports_by_outcome": _count_by_label(
                reports, "outcome", MONITORING_REPORT_OUTCOMES),
            "total_events_reported": sum(
                r["events_reported"] for r in reports
                if r["events_reported"] is not None),
            "reference_stub": True,
            "monitored_here": False,
            "derived": True,
            "method": "counts_over_monitoring_arrangement_report_records",
        }
