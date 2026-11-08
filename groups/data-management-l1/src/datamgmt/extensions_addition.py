"""Final GAPS batch extensions, second unit — Data Management L1.

Clean-room, standard-library-only records extensions for the two
Extended functions registered by this group's remainder addition
fork (DevResults, FR2100845343), per ``BATCH-ADDITION.md`` in the
group directory: M&E / results-management platform functions and
data-capture tooling & collection instruments. Both close as
in-substrate records surfaces (``build-extension``, as drafted);
no entry was re-judged. The first batch unit's module
(``datamgmt.extensions``) and every core module are untouched
(byte-identical).

The honesty bound is the group's own (``UNION-SPEC.md`` and
``ADDENDUM.md``): the enlarged group holds **zero claims across
both forks** — the category substrate is carried, not claimed, and
these surfaces are the census-registered gaps of the addition
fork's *described* functions, not claims. What lands is the
records layer those functions' operation presupposes, over the
core's own records:

- A results framework is a definition held as data: a name, an
  opaque program reference, and an optional binding to a core
  dataset. Indicators are definitions too — a name, a unit held as
  a label, and optional baseline/target figures recorded as the
  framework's declared terms. Nothing here measures progress:
  a progress report binds an indicator to a core ingestion record
  (the substrate's own record of data arriving) and stores the
  reporting party's outcome label and optional reported value
  **verbatim as reported**. Progress state — report counts,
  counts by outcome, the latest reported outcome and value — is
  derived at read, over this module's records joined with the
  core provenance total, and is never stored.
- A collection instrument is a definition held as data: a name, a
  kind, and field definitions (name + kind) recorded against it.
  A capture run binds an instrument to a core ingestion record —
  the run takes its dataset and source from that core record,
  never from the caller — and stores the instrument's own reported
  record count verbatim as reported. No instrument is rendered,
  distributed, or filled in here, and no programme data is
  collected: ``collected_here`` is False on every record, and no
  record shape in this module can hold a response value, a record
  payload, or dataset content of any kind (the substrate's hard
  privacy rule — dataset content never enters any field shape).

Design, following the core's doctrines and this group's first
batch unit (same forms, same tier — Low / FAR 52.204-21; no
Moderate/High apparatus is imported: plain append-only audit, the
three-role matrix, no hash chain, no lockout, no auditor role):

- This module is a wrapper around :class:`DataMgmtStore`; dataset,
  source, and ingestion existence and content are always read
  through the core store's public API, never re-implemented.
- RBAC goes through :mod:`datamgmt.access` exactly as the core and
  the first extension module enforce it: each operation maps onto
  an existing core action (the core action set is fixed), checked
  *before* any state change or id allocation for User-like actors;
  denied attempts are recorded on the core audit log with the
  extension action name suffixed ``:denied``. Plain-string actors
  carry identity but no role, mirroring the core convention.
- Every successful mutation is recorded on the core store's audit
  log with an action name prefixed ``exta_`` (the second-unit
  prefix, distinct from the first unit's ``ext_``).
- All programs, instruments, and parties are opaque ``*_ref``
  strings or labels held as data.
- Derived values are derived at read and never stored: the
  results summary's counts, outcome tallies, and latest reported
  outcome/value, and the instrument summary's field/run counts,
  outcome tallies, and reported-record total.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

PROGRESS_OUTCOMES = (
    "reported_progressing",
    "reported_on_track",
    "reported_off_track",
    "reported_no_data",
)
KNOWN_PROGRESS_OUTCOMES = frozenset(PROGRESS_OUTCOMES)
INSTRUMENT_KINDS = (
    "survey_form",
    "field_form",
    "interview_guide",
    "observation_checklist",
    "mobile_form",
    "paper_form",
    "other",
)
KNOWN_INSTRUMENT_KINDS = frozenset(INSTRUMENT_KINDS)
FIELD_KINDS = ("text", "number", "date", "choice", "boolean", "free_text")
KNOWN_FIELD_KINDS = frozenset(FIELD_KINDS)
CAPTURE_OUTCOMES = (
    "reported_completed",
    "reported_partial",
    "reported_failed",
)
KNOWN_CAPTURE_OUTCOMES = frozenset(CAPTURE_OUTCOMES)


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


def _nonneg_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _number_or_none(value, what):
    """A reported figure, held verbatim: int/float, never bool."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("%s must be a number" % (what,))
    return value


def _one_of(value, known, names, what):
    if value not in known:
        raise ValidationError(
            "%s must be one of %s" % (what, ", ".join(names))
        )
    return value


class DataMgmtExtensionsAddition:
    """Second GAPS-batch extension surface over a core DataMgmtStore."""

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

        Mirrors the core store and the first extension module: an
        actor must be present; User-like actors are checked against
        the core permission matrix before anything changes; plain
        strings carry identity only.
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

    # -- M&E / results-management platform functions (records form) -----
    # Frameworks and indicators are definitions held as data.
    # Progress is never measured here: a progress report binds an
    # indicator to a core ingestion record and stores the reporting
    # party's outcome and value verbatim as reported; every figure
    # in the summary is derived at read from those records and the
    # core's provenance.

    def define_results_framework(self, name, program_ref, actor,
                                 dataset_id=None):
        """Define a results framework. Action: dataset_write.

        ``program_ref`` is an opaque reference to the programme the
        framework belongs to. ``dataset_id``, when given, must be a
        registered core dataset — the dataset the framework's
        results are recorded against. The framework is a definition
        only: no indicator is measured and no result is computed by
        recording it (``measured_here`` is False).
        """
        self._guard(actor, "dataset_write", "exta_framework_define",
                    dataset_id)
        _non_empty(name, "results framework name")
        _non_empty(program_ref, "program_ref")
        with self._lock:
            if dataset_id is not None:
                self.store.get_dataset(dataset_id)
            return self._create(
                "results_framework", "rfw",
                {"name": name, "program_ref": program_ref,
                 "dataset_id": dataset_id,
                 "measured_here": False, "values_held": False},
                actor, "exta_framework_define")

    def get_results_framework(self, framework_id, actor=None):
        """Return one results framework record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "exta_framework_read",
                         framework_id)
        return self._fetch("results_framework", framework_id)

    def list_results_frameworks(self, dataset_id=None, actor=None):
        """Return results framework records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "exta_framework_read",
                         dataset_id)
        if dataset_id is not None:
            self.store.get_dataset(dataset_id)
        return self._list("results_framework", dataset_id=dataset_id)

    def register_indicator(self, framework_id, name, actor, unit_label=None,
                           baseline_reported=None, target_reported=None):
        """Register an indicator under a results framework.

        Action: quality_write. The indicator is a definition: a
        name, a unit held as a label, and optional baseline/target
        figures recorded as the framework's declared terms (held
        verbatim as declared; nothing is measured against them
        here). Indicator names are unique within a framework.
        """
        self._guard(actor, "quality_write", "exta_indicator_register",
                    framework_id)
        _non_empty(name, "indicator name")
        _string_or_none(unit_label, "unit_label")
        _number_or_none(baseline_reported, "baseline_reported")
        _number_or_none(target_reported, "target_reported")
        with self._lock:
            self._get("results_framework", framework_id)
            for existing in self._list("indicator",
                                       framework_id=framework_id):
                if existing["name"] == name:
                    raise ValidationError(
                        "framework %r already has indicator %r"
                        % (framework_id, name)
                    )
            return self._create(
                "indicator", "ind",
                {"framework_id": framework_id, "name": name,
                 "unit_label": unit_label,
                 "baseline_reported": baseline_reported,
                 "target_reported": target_reported,
                 "measured_here": False},
                actor, "exta_indicator_register")

    def get_indicator(self, indicator_id, actor=None):
        """Return one indicator record. Action: quality_read."""
        self._guard_read(actor, "quality_read", "exta_indicator_read",
                         indicator_id)
        return self._fetch("indicator", indicator_id)

    def list_indicators(self, framework_id=None, actor=None):
        """Return indicator records. Action: quality_read."""
        self._guard_read(actor, "quality_read", "exta_indicator_read",
                         framework_id)
        if framework_id is not None:
            self._get("results_framework", framework_id)
        return self._list("indicator", framework_id=framework_id)

    def record_progress_report(self, indicator_id, ingestion_id, outcome,
                               actor, value_reported=None):
        """Record a reported progress outcome for an indicator.

        Action: ingest_record. The report binds the indicator to
        exactly one core ingestion record — the substrate's own
        record of the data the report rests on. When the
        indicator's framework names a dataset, the ingestion must
        belong to that dataset. One ingestion backs at most one
        progress report per indicator. ``outcome`` and
        ``value_reported`` are the reporting party's report, stored
        verbatim as reported: this build measured nothing, computed
        nothing, and verified nothing about the report
        (``measured_here`` / ``computed_here`` are False).
        """
        self._guard(actor, "ingest_record", "exta_progress_report_record",
                    indicator_id)
        _one_of(outcome, KNOWN_PROGRESS_OUTCOMES, PROGRESS_OUTCOMES,
                "outcome")
        _number_or_none(value_reported, "value_reported")
        with self._lock:
            indicator = self._get("indicator", indicator_id)
            framework = self._get("results_framework",
                                  indicator["framework_id"])
            ingestion = self.store.get_ingestion(ingestion_id)
            if (framework["dataset_id"] is not None
                    and ingestion["dataset_id"] != framework["dataset_id"]):
                raise ValidationError(
                    "ingestion %r does not belong to the framework's "
                    "dataset %r" % (ingestion_id, framework["dataset_id"])
                )
            for existing in self._list("progress_report",
                                       indicator_id=indicator_id):
                if existing["ingestion_id"] == ingestion_id:
                    raise ValidationError(
                        "ingestion %r already backs progress report %r "
                        "for indicator %r"
                        % (ingestion_id, existing["id"], indicator_id)
                    )
            return self._create(
                "progress_report", "prg",
                {"indicator_id": indicator_id,
                 "framework_id": indicator["framework_id"],
                 "ingestion_id": ingestion_id,
                 "outcome": outcome,
                 "value_reported": value_reported,
                 "measured_here": False, "computed_here": False},
                actor, "exta_progress_report_record")

    def get_progress_report(self, report_id, actor=None):
        """Return one progress report record. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "exta_progress_report_read",
                         report_id)
        return self._fetch("progress_report", report_id)

    def list_progress_reports(self, indicator_id=None, actor=None):
        """Return progress report records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "exta_progress_report_read",
                         indicator_id)
        if indicator_id is not None:
            self._get("indicator", indicator_id)
        return self._list("progress_report", indicator_id=indicator_id)

    @staticmethod
    def _latest_progress_report(reports):
        """The most recent progress report in a list, or None.

        The single seam the results summary's latest-outcome and
        latest-value derivations read through — this unit's fresh
        negative control mutates it.
        """
        return reports[-1] if reports else None

    def results_summary(self, framework_id, actor=None):
        """Derived results view for a framework. Action: dataset_read.

        Indicator and report counts and the per-outcome tallies are
        computed at read from this module's records; the latest
        reported outcome and value are the most recent progress
        report's, read through ``_latest_progress_report``; the
        record total is the core provenance view's total over
        completed ingestions of the framework's dataset (None when
        the framework names no dataset). Nothing here is stored,
        and the bounds ride on the view itself: progress was
        reported to this build, never measured by it.
        """
        self._guard_read(actor, "dataset_read", "exta_results_summary",
                         framework_id)
        with self._lock:
            framework = self._get("results_framework", framework_id)
            indicators = self._list("indicator", framework_id=framework_id)
            reports = self._list("progress_report",
                                 framework_id=framework_id)
            by_outcome = {}
            for report in reports:
                by_outcome[report["outcome"]] = \
                    by_outcome.get(report["outcome"], 0) + 1
            latest = self._latest_progress_report(reports)
            total_records = None
            if framework["dataset_id"] is not None:
                provenance = self.store.dataset_provenance(
                    framework["dataset_id"])
                total_records = provenance["total_records"]
            return {
                "framework_id": framework_id,
                "indicators": len(indicators),
                "progress_reports": len(reports),
                "reports_by_outcome": by_outcome,
                "latest_outcome": latest["outcome"] if latest else None,
                "latest_value_reported":
                    latest["value_reported"] if latest else None,
                "total_records": total_records,
                "measured_here": False,
                "computed_here": False,
                "values_held": False,
            }

    # -- Data-capture tooling & collection instruments (records form) ---
    # Instruments are definitions held as data: a kind, and field
    # definitions recorded against the instrument. A capture run
    # binds an instrument to a core ingestion record and takes its
    # dataset and source from that record. Nothing is rendered,
    # distributed, filled in, or collected by this build, and no
    # record shape can hold a response value or any data content.

    def define_collection_instrument(self, name, kind, actor,
                                     version_label=None):
        """Define a collection instrument. Action: dataset_write.

        ``kind`` names the instrument family (survey form, field
        form, interview guide, and so on); the definition is data
        only — no instrument is rendered, distributed, or fielded
        by recording it (``collected_here`` is False).
        """
        self._guard(actor, "dataset_write", "exta_instrument_define")
        _non_empty(name, "collection instrument name")
        _one_of(kind, KNOWN_INSTRUMENT_KINDS, INSTRUMENT_KINDS, "kind")
        _string_or_none(version_label, "version_label")
        with self._lock:
            return self._create(
                "collection_instrument", "cin",
                {"name": name, "kind": kind,
                 "version_label": version_label,
                 "collected_here": False, "content_held": False},
                actor, "exta_instrument_define")

    def get_collection_instrument(self, instrument_id, actor=None):
        """Return one collection instrument record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "exta_instrument_read",
                         instrument_id)
        return self._fetch("collection_instrument", instrument_id)

    def list_collection_instruments(self, actor=None):
        """Return collection instrument records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "exta_instrument_read")
        return self._list("collection_instrument")

    def add_instrument_field(self, instrument_id, field_name, field_kind,
                             actor, required=False):
        """Add a field definition to a collection instrument.

        Action: quality_write. A field definition is a name and a
        kind held as data — the shape an instrument declares, never
        a value it collected. Field names are unique within an
        instrument. ``required`` is a declared term of the
        definition, held as data; nothing validates responses
        against it here, because no responses exist here.
        """
        self._guard(actor, "quality_write", "exta_instrument_field_add",
                    instrument_id)
        _non_empty(field_name, "field_name")
        _one_of(field_kind, KNOWN_FIELD_KINDS, FIELD_KINDS, "field_kind")
        if not isinstance(required, bool):
            raise ValidationError("required must be a boolean")
        with self._lock:
            self._get("collection_instrument", instrument_id)
            for existing in self._list("instrument_field",
                                       instrument_id=instrument_id):
                if existing["field_name"] == field_name:
                    raise ValidationError(
                        "instrument %r already has field %r"
                        % (instrument_id, field_name)
                    )
            return self._create(
                "instrument_field", "cif",
                {"instrument_id": instrument_id,
                 "field_name": field_name, "field_kind": field_kind,
                 "required": required,
                 "collected_here": False, "content_held": False},
                actor, "exta_instrument_field_add")

    def get_instrument_field(self, field_id, actor=None):
        """Return one instrument field record. Action: quality_read."""
        self._guard_read(actor, "quality_read", "exta_instrument_field_read",
                         field_id)
        return self._fetch("instrument_field", field_id)

    def list_instrument_fields(self, instrument_id=None, actor=None):
        """Return instrument field records. Action: quality_read."""
        self._guard_read(actor, "quality_read",
                         "exta_instrument_field_read", instrument_id)
        if instrument_id is not None:
            self._get("collection_instrument", instrument_id)
        return self._list("instrument_field", instrument_id=instrument_id)

    def record_capture_run(self, instrument_id, ingestion_id, outcome,
                           actor, records_reported=None):
        """Record a capture run: an instrument over a core ingestion.

        Action: ingest_record. The ingestion must exist in the
        core; the run takes its dataset and source from that core
        record, never from the caller. One ingestion backs at most
        one capture run per instrument. ``outcome`` and
        ``records_reported`` are the instrument's own report,
        stored verbatim as reported — the count is a report about
        collection done elsewhere, not a count of anything held
        here (``collected_here`` is False; the core ingestion's own
        record count remains the core's figure, on the core
        record).
        """
        self._guard(actor, "ingest_record", "exta_capture_run_record",
                    instrument_id)
        _one_of(outcome, KNOWN_CAPTURE_OUTCOMES, CAPTURE_OUTCOMES,
                "outcome")
        if records_reported is not None:
            _nonneg_int(records_reported, "records_reported")
        with self._lock:
            self._get("collection_instrument", instrument_id)
            ingestion = self.store.get_ingestion(ingestion_id)
            for existing in self._list("capture_run",
                                       instrument_id=instrument_id):
                if existing["ingestion_id"] == ingestion_id:
                    raise ValidationError(
                        "ingestion %r already backs capture run %r "
                        "for instrument %r"
                        % (ingestion_id, existing["id"], instrument_id)
                    )
            return self._create(
                "capture_run", "crn",
                {"instrument_id": instrument_id,
                 "ingestion_id": ingestion_id,
                 "dataset_id": ingestion["dataset_id"],
                 "source_id": ingestion["source_id"],
                 "outcome": outcome,
                 "records_reported": records_reported,
                 "collected_here": False, "content_held": False},
                actor, "exta_capture_run_record")

    def get_capture_run(self, run_id, actor=None):
        """Return one capture run record. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "exta_capture_run_read",
                         run_id)
        return self._fetch("capture_run", run_id)

    def list_capture_runs(self, instrument_id=None, actor=None):
        """Return capture run records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "exta_capture_run_read",
                         instrument_id)
        if instrument_id is not None:
            self._get("collection_instrument", instrument_id)
        return self._list("capture_run", instrument_id=instrument_id)

    def instrument_summary(self, instrument_id, actor=None):
        """Derived view over an instrument. Action: dataset_read.

        Field and run counts and the per-outcome tallies are
        computed at read from this module's records; the reported
        record total is the sum of the runs' own reported counts,
        stated as a total of reports — runs that reported no count
        contribute nothing and are tallied separately as
        ``runs_without_reported_count``. Nothing here is stored,
        and nothing was collected by this build.
        """
        self._guard_read(actor, "dataset_read", "exta_instrument_summary",
                         instrument_id)
        with self._lock:
            self._get("collection_instrument", instrument_id)
            fields = self._list("instrument_field",
                                instrument_id=instrument_id)
            runs = self._list("capture_run", instrument_id=instrument_id)
            by_outcome = {}
            reported_total = 0
            without_count = 0
            for run in runs:
                by_outcome[run["outcome"]] = \
                    by_outcome.get(run["outcome"], 0) + 1
                if run["records_reported"] is None:
                    without_count += 1
                else:
                    reported_total += run["records_reported"]
            return {
                "instrument_id": instrument_id,
                "fields": len(fields),
                "capture_runs": len(runs),
                "runs_by_outcome": by_outcome,
                "total_records_reported": reported_total,
                "runs_without_reported_count": without_count,
                "collected_here": False,
                "content_held": False,
            }
