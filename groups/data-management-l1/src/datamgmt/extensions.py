"""Final GAPS batch extensions for the Data Management L1 singleton.

Clean-room, standard-library-only records extensions for the five
Extended functions new with this group's fork (Pagefreezer Website
Archiving), per ``BATCH.md`` in the group directory: 2 built as
in-substrate records surfaces (web crawling & snapshot capture;
archive storage, integrity sealing & replay records) and 3 shipped
as labeled reference implementations (web page rendering for
capture -- re-judged from build-extension, grounds in ``BATCH.md``;
change detection & dynamic monitoring; full-content search &
indexing over the archive). See ``BATCH.md`` for the per-entry
disposition and the re-judgment grounds.

The honesty bound is the group's own (``UNION-SPEC.md``,
core-boundary decision): the substrate models an archive's
governance; it does not capture a single web page. Nothing in this
module crawls, renders, detects, seals content, replays content,
indexes content, or searches content. What lands is the records
layer those engines' operation presupposes, over the core's own
records:

- A capture is recorded against a core ingestion record -- the
  substrate's capture-shaped record, which already carries the
  run's mode, record count, checksum, and status. Capture records
  add the crawl target they belong to and nothing else; counts and
  checksums are read from the core record, never restated as this
  module's own measurement.
- An archive seal records the checksum of the capture's core
  ingestion at seal time, derived at seal time from the core
  record. The seal is a governance record about integrity; no
  content is held, copied, or sealed here (``content_held`` is
  False on every archive record, and no record shape in this
  module can hold page content).
- A replay request is a labeled transport record
  (``reference_transport: True``): it records that replay was
  requested of the archive, by an opaque requester reference, for
  a stated purpose. Nothing is replayed and no content moves.

Design, following the core's doctrines and the category's shipped
batch units at L2 and L3-adjacent (same forms, adapted to this
tier's baseline -- Low / FAR 52.204-21; the siblings' Moderate/High
apparatus is not imported):

- This module is a wrapper around :class:`DataMgmtStore`; the core
  modules are untouched (byte-identical). Dataset, source, and
  ingestion existence and content are always read through the core
  store's public API, never re-implemented.
- RBAC goes through :mod:`datamgmt.access` exactly as the core
  enforces it: the extension maps each of its operations onto an
  existing core action (the core action set is fixed), checks it
  *before* any state change or id allocation for User-like actors,
  and records denied attempts on the core audit log with the
  extension action name suffixed ``:denied``. Plain-string actors
  carry identity but no role, mirroring the core convention.
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``.
- All references to sites, systems, and requesters are opaque
  ``*_ref`` strings; no record shape in this module can hold page
  content, a record payload, or an identifier value.
- Derived values are derived at read and never stored: the archive
  summary's counts and totals, and the content-index summary's
  latest reported figure.
- Archive sealing carries the category's separation-of-duties
  signature in a new surface: the sealer of a capture may never be
  the actor who recorded it, enforced at a single named seam
  (``_check_sealer_not_recorder``), mirroring the core's
  ``_check_decider_not_requester``. The seam is this unit's fresh
  negative control.
- The three reference surfaces carry ``reference_stub: True`` on
  every record they create (replay requests carry
  ``reference_transport: True`` instead, as a transport record),
  and each carries its ``*_here: False`` bound on its face: no
  page is rendered, no change is detected, no content is indexed
  or searched by this build. The core's registry-metadata search
  remains the only search that runs.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

RENDER_MODES = ("static", "dynamic_javascript", "dynamic_javascript_settled")
KNOWN_RENDER_MODES = frozenset(RENDER_MODES)
RENDER_OUTCOMES = ("reported_rendered", "reported_partial", "reported_failed")
KNOWN_RENDER_OUTCOMES = frozenset(RENDER_OUTCOMES)
CHANGE_OUTCOMES = (
    "reported_no_change",
    "reported_new_pages",
    "reported_changed_pages",
    "reported_mixed",
)
KNOWN_CHANGE_OUTCOMES = frozenset(CHANGE_OUTCOMES)


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
        raise ValidationError(
            "%s must be one of %s" % (what, ", ".join(names))
        )
    return value


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

    # -- Web crawling & snapshot capture (records form) -----------------
    # Crawl targets are definitions: an archive dataset, the site it
    # watches (an opaque reference), an optional core source the
    # captures arrive through, and the schedule held as a label.
    # Captures bind a target to one core ingestion record -- the
    # substrate's own record of a run -- so a capture can never claim
    # counts or a checksum the core did not record.

    def define_crawl_target(self, dataset_id, name, site_ref, actor,
                            source_id=None, schedule_label=None):
        """Define a crawl target for an archive dataset.

        Action: dataset_write. ``site_ref`` is an opaque reference
        to the site watched; no URL is fetched and nothing is
        crawled by this call (``captured_here`` is False on the
        record). ``source_id``, when given, must be a registered
        core source.
        """
        self._guard(actor, "dataset_write", "ext_crawl_target_define",
                    dataset_id)
        _non_empty(name, "crawl target name")
        _non_empty(site_ref, "site_ref")
        _string_or_none(schedule_label, "schedule_label")
        with self._lock:
            self._dataset(dataset_id)
            if source_id is not None:
                self.store.get_source(source_id)
            return self._create(
                "crawl_target", "cwt",
                {"dataset_id": dataset_id, "name": name,
                 "site_ref": site_ref, "source_id": source_id,
                 "schedule_label": schedule_label,
                 "captured_here": False},
                actor, "ext_crawl_target_define")

    def get_crawl_target(self, target_id, actor=None):
        """Return one crawl target record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_crawl_target_read",
                         target_id)
        return self._fetch("crawl_target", target_id)

    def list_crawl_targets(self, dataset_id=None, actor=None):
        """Return crawl target records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_crawl_target_read",
                         dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("crawl_target", dataset_id=dataset_id)

    def record_capture(self, target_id, ingestion_id, actor,
                       pages_reported=None):
        """Record a capture: a crawl target over a core ingestion.

        Action: ingest_record. The ingestion must exist in the core
        and must belong to the target's dataset; one ingestion backs
        at most one capture. The capture holds no counts or checksum
        of its own -- those live on the core ingestion record, which
        is where any reader (and the archive summary) takes them
        from. ``pages_reported`` is the crawler's own reported page
        count, stored as reported data, never verified here.
        """
        self._guard(actor, "ingest_record", "ext_capture_record", target_id)
        if pages_reported is not None:
            _nonneg_int(pages_reported, "pages_reported")
        with self._lock:
            target = self._get("crawl_target", target_id)
            ingestion = self.store.get_ingestion(ingestion_id)
            if ingestion["dataset_id"] != target["dataset_id"]:
                raise ValidationError(
                    "ingestion %r does not belong to the crawl target's "
                    "dataset %r" % (ingestion_id, target["dataset_id"])
                )
            for existing in self._list("capture"):
                if existing["ingestion_id"] == ingestion_id:
                    raise ValidationError(
                        "ingestion %r already backs capture %r"
                        % (ingestion_id, existing["id"])
                    )
            return self._create(
                "capture", "cap",
                {"target_id": target_id,
                 "dataset_id": target["dataset_id"],
                 "ingestion_id": ingestion_id,
                 "pages_reported": pages_reported,
                 "captured_here": False},
                actor, "ext_capture_record")

    def get_capture(self, capture_id, actor=None):
        """Return one capture record. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_capture_read", capture_id)
        return self._fetch("capture", capture_id)

    def list_captures(self, target_id=None, actor=None):
        """Return capture records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_capture_read", target_id)
        if target_id is not None:
            self._get("crawl_target", target_id)
        return self._list("capture", target_id=target_id)

    def archive_summary(self, dataset_id, actor=None):
        """Derived archive view for a dataset. Action: dataset_read.

        Counts of targets, captures, and seals are computed at read
        from this module's records; the record total is the core
        provenance view's total over completed ingestions. Nothing
        here is stored, and the bounds ride on the view itself:
        nothing was captured, sealed, or held by this build.
        """
        self._guard_read(actor, "dataset_read", "ext_archive_summary",
                         dataset_id)
        with self._lock:
            self._dataset(dataset_id)
            targets = [t for t in self._list("crawl_target")
                       if t["dataset_id"] == dataset_id]
            target_ids = {t["id"] for t in targets}
            captures = [c for c in self._list("capture")
                        if c["target_id"] in target_ids]
            capture_ids = {c["id"] for c in captures}
            seals = [s for s in self._list("archive_seal")
                     if s["capture_id"] in capture_ids]
            provenance = self.store.dataset_provenance(dataset_id)
            return {
                "dataset_id": dataset_id,
                "crawl_targets": len(targets),
                "captures": len(captures),
                "archive_seals": len(seals),
                "total_records": provenance["total_records"],
                "captured_here": False,
                "sealed_here": False,
                "content_held": False,
            }

    # -- Web page rendering for capture (reference) ---------------------
    # A labeled reference implementation (re-judged; see BATCH.md):
    # render profiles are definitions held as data, and render
    # reports store the renderer's outcome verbatim as reported.
    # No page is rendered by this build.

    def define_render_profile(self, name, mode, actor, wait_label=None):
        """Define a render profile. Action: dataset_write.

        ``mode`` names how the capture renderer treats a page
        (static fetch, or dynamic/JavaScript rendering, optionally
        waiting for the page to settle); the profile is the
        definition only -- no rendering is configured anywhere by
        recording it, and ``rendered_here`` is False.
        """
        self._guard(actor, "dataset_write", "ext_render_profile_define")
        _non_empty(name, "render profile name")
        _one_of(mode, KNOWN_RENDER_MODES, RENDER_MODES, "mode")
        _string_or_none(wait_label, "wait_label")
        with self._lock:
            return self._create(
                "render_profile", "rpf",
                {"name": name, "mode": mode, "wait_label": wait_label,
                 "reference_stub": True, "rendered_here": False},
                actor, "ext_render_profile_define")

    def get_render_profile(self, profile_id, actor=None):
        """Return one render profile record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_render_profile_read",
                         profile_id)
        return self._fetch("render_profile", profile_id)

    def list_render_profiles(self, actor=None):
        """Return render profile records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_render_profile_read")
        return self._list("render_profile")

    def record_render_report(self, capture_id, profile_id, outcome, actor,
                             pages_rendered=None):
        """Record a renderer's reported outcome for a capture.

        Action: ingest_record. ``outcome`` and ``pages_rendered``
        are the rendering engine's report, stored verbatim as
        reported; this build rendered nothing and verifies nothing
        about the report.
        """
        self._guard(actor, "ingest_record", "ext_render_report_record",
                    capture_id)
        _one_of(outcome, KNOWN_RENDER_OUTCOMES, RENDER_OUTCOMES, "outcome")
        if pages_rendered is not None:
            _nonneg_int(pages_rendered, "pages_rendered")
        with self._lock:
            self._get("capture", capture_id)
            self._get("render_profile", profile_id)
            return self._create(
                "render_report", "rrp",
                {"capture_id": capture_id, "profile_id": profile_id,
                 "outcome": outcome, "pages_rendered": pages_rendered,
                 "reference_stub": True, "rendered_here": False},
                actor, "ext_render_report_record")

    def get_render_report(self, report_id, actor=None):
        """Return one render report record. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_render_report_read",
                         report_id)
        return self._fetch("render_report", report_id)

    def list_render_reports(self, capture_id=None, actor=None):
        """Return render report records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_render_report_read",
                         capture_id)
        if capture_id is not None:
            self._get("capture", capture_id)
        return self._list("render_report", capture_id=capture_id)

    # -- Change detection & dynamic monitoring (reference) --------------
    # A labeled reference implementation: monitor definitions over
    # crawl targets, and change reports stored verbatim as the
    # monitoring engine's report. Nothing here fetches a page or
    # compares snapshots; ``detected_here`` is False throughout.

    def define_monitor(self, target_id, actor, cadence_label=None):
        """Define a change monitor over a crawl target.

        Action: dataset_write. The cadence is a label held as data;
        no schedule runs and no monitoring is performed by
        recording it.
        """
        self._guard(actor, "dataset_write", "ext_monitor_define", target_id)
        _string_or_none(cadence_label, "cadence_label")
        with self._lock:
            self._get("crawl_target", target_id)
            return self._create(
                "monitor", "mon",
                {"target_id": target_id, "cadence_label": cadence_label,
                 "reference_stub": True, "monitored_here": False,
                 "detected_here": False},
                actor, "ext_monitor_define")

    def get_monitor(self, monitor_id, actor=None):
        """Return one monitor record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_monitor_read",
                         monitor_id)
        return self._fetch("monitor", monitor_id)

    def list_monitors(self, target_id=None, actor=None):
        """Return monitor records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_monitor_read", target_id)
        if target_id is not None:
            self._get("crawl_target", target_id)
        return self._list("monitor", target_id=target_id)

    def record_change_report(self, monitor_id, outcome, actor,
                             pages_changed=None, note=None):
        """Record a monitoring engine's reported change outcome.

        Action: ingest_record. ``outcome`` and ``pages_changed``
        are stored verbatim as reported; this build compared no
        snapshots and detected nothing.
        """
        self._guard(actor, "ingest_record", "ext_change_report_record",
                    monitor_id)
        _one_of(outcome, KNOWN_CHANGE_OUTCOMES, CHANGE_OUTCOMES, "outcome")
        if pages_changed is not None:
            _nonneg_int(pages_changed, "pages_changed")
        _string_or_none(note, "note")
        with self._lock:
            self._get("monitor", monitor_id)
            return self._create(
                "change_report", "chg",
                {"monitor_id": monitor_id, "outcome": outcome,
                 "pages_changed": pages_changed, "note": note,
                 "reference_stub": True, "detected_here": False},
                actor, "ext_change_report_record")

    def get_change_report(self, report_id, actor=None):
        """Return one change report record. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_change_report_read",
                         report_id)
        return self._fetch("change_report", report_id)

    def list_change_reports(self, monitor_id=None, actor=None):
        """Return change report records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_change_report_read",
                         monitor_id)
        if monitor_id is not None:
            self._get("monitor", monitor_id)
        return self._list("change_report", monitor_id=monitor_id)

    # -- Archive storage, integrity sealing & replay (records form) -----
    # A seal binds a capture to the checksum of its core ingestion
    # record, read from the core at seal time: the integrity
    # statement is about the substrate's own record, and it is the
    # strongest statement this build can honestly make -- it holds
    # no captured content to seal. Sealing is guarded by the
    # separation-of-duties seam below. Replay is a labeled transport
    # record: a request, never a playback.

    def _check_sealer_not_recorder(self, capture, actor):
        """Separation of duties: the sealer is never the recorder.

        Mirrors the core's ``_check_decider_not_requester`` (the
        category's signature guard) in this unit's new surface.
        """
        if actor_name(actor) == capture["created_by"]:
            raise PermissionDenied("sealer may not be the capture recorder")

    def seal_capture(self, capture_id, actor):
        """Seal a capture against its core ingestion's checksum.

        Action: ingest_record. The checksum is read from the core
        ingestion record at seal time (an ingestion recorded
        without one seals as ``checksum: None`` -- the seal states
        what the core record holds, no more). One seal per capture.
        The actor who recorded the capture may not seal it
        (``_check_sealer_not_recorder``).
        """
        self._guard(actor, "ingest_record", "ext_archive_seal", capture_id)
        with self._lock:
            capture = self._get("capture", capture_id)
            self._check_sealer_not_recorder(capture, actor)
            for existing in self._list("archive_seal"):
                if existing["capture_id"] == capture_id:
                    raise ValidationError(
                        "capture %r already has seal %r"
                        % (capture_id, existing["id"])
                    )
            ingestion = self.store.get_ingestion(capture["ingestion_id"])
            return self._create(
                "archive_seal", "asl",
                {"capture_id": capture_id,
                 "ingestion_id": capture["ingestion_id"],
                 "checksum": ingestion["checksum"],
                 "sealed_here": False, "content_held": False},
                actor, "ext_archive_seal")

    def get_archive_seal(self, seal_id, actor=None):
        """Return one archive seal record. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_archive_seal_read",
                         seal_id)
        return self._fetch("archive_seal", seal_id)

    def list_archive_seals(self, capture_id=None, actor=None):
        """Return archive seal records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_archive_seal_read",
                         capture_id)
        if capture_id is not None:
            self._get("capture", capture_id)
        return self._list("archive_seal", capture_id=capture_id)

    def record_replay_request(self, seal_id, requester_ref, actor,
                              purpose=None):
        """Record a request to replay a sealed capture.

        Action: access_request. A labeled transport record: it
        records that replay was requested, by an opaque requester
        reference, for a stated purpose. Nothing is replayed, no
        content is served, and no content moves
        (``replayed_here`` is False, ``content_held`` is False).
        """
        self._guard(actor, "access_request", "ext_replay_request_record",
                    seal_id)
        _non_empty(requester_ref, "requester_ref")
        _string_or_none(purpose, "purpose")
        with self._lock:
            self._get("archive_seal", seal_id)
            return self._create(
                "replay_request", "rpl",
                {"seal_id": seal_id, "requester_ref": requester_ref,
                 "purpose": purpose, "reference_transport": True,
                 "replayed_here": False, "content_held": False},
                actor, "ext_replay_request_record")

    def get_replay_request(self, request_id, actor=None):
        """Return one replay request record. Action: access_read."""
        self._guard_read(actor, "access_read", "ext_replay_request_read",
                         request_id)
        return self._fetch("replay_request", request_id)

    def list_replay_requests(self, seal_id=None, actor=None):
        """Return replay request records. Action: access_read."""
        self._guard_read(actor, "access_read", "ext_replay_request_read",
                         seal_id)
        if seal_id is not None:
            self._get("archive_seal", seal_id)
        return self._list("replay_request", seal_id=seal_id)

    # -- Full-content search & indexing over the archive (reference) ----
    # A labeled reference implementation: index definitions and
    # reported index snapshots. No content is indexed and no
    # full-content search runs; the core's catalog search over
    # registry metadata remains the only search in this build.

    def define_content_index(self, name, actor, scope_label=None):
        """Define a full-content index over the archive.

        Action: dataset_write. The definition names the index and
        its scope as a label; building it indexes nothing
        (``indexed_here`` is False) and holds no content.
        """
        self._guard(actor, "dataset_write", "ext_content_index_define")
        _non_empty(name, "content index name")
        _string_or_none(scope_label, "scope_label")
        with self._lock:
            return self._create(
                "content_index", "cix",
                {"name": name, "scope_label": scope_label,
                 "reference_stub": True, "indexed_here": False,
                 "content_held": False},
                actor, "ext_content_index_define")

    def get_content_index(self, index_id, actor=None):
        """Return one content index record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_content_index_read",
                         index_id)
        return self._fetch("content_index", index_id)

    def list_content_indexes(self, actor=None):
        """Return content index records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_content_index_read")
        return self._list("content_index")

    def record_index_snapshot(self, index_id, documents_reported, actor,
                              checksum=None):
        """Record an indexing engine's reported index snapshot.

        Action: ingest_record. ``documents_reported`` and the
        optional ``checksum`` are the engine's report, stored
        verbatim as reported; this build indexed nothing and holds
        no indexed content.
        """
        self._guard(actor, "ingest_record", "ext_index_snapshot_record",
                    index_id)
        _nonneg_int(documents_reported, "documents_reported")
        _string_or_none(checksum, "checksum")
        with self._lock:
            self._get("content_index", index_id)
            return self._create(
                "index_snapshot", "isn",
                {"index_id": index_id,
                 "documents_reported": documents_reported,
                 "checksum": checksum,
                 "reference_stub": True, "indexed_here": False},
                actor, "ext_index_snapshot_record")

    def get_index_snapshot(self, snapshot_id, actor=None):
        """Return one index snapshot record. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_index_snapshot_read",
                         snapshot_id)
        return self._fetch("index_snapshot", snapshot_id)

    def list_index_snapshots(self, index_id=None, actor=None):
        """Return index snapshot records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_index_snapshot_read",
                         index_id)
        if index_id is not None:
            self._get("content_index", index_id)
        return self._list("index_snapshot", index_id=index_id)

    def content_index_summary(self, index_id, actor=None):
        """Derived view over an index's snapshots. Action: dataset_read.

        The latest reported document count is the most recent
        snapshot's reported figure, derived at read; nothing here
        is stored, and no search over content exists to run
        (``searched_here`` is False).
        """
        self._guard_read(actor, "dataset_read", "ext_content_index_summary",
                         index_id)
        with self._lock:
            self._get("content_index", index_id)
            snapshots = self._list("index_snapshot", index_id=index_id)
            latest = snapshots[-1]["documents_reported"] if snapshots else None
            return {
                "index_id": index_id,
                "snapshots": len(snapshots),
                "latest_documents_reported": latest,
                "indexed_here": False,
                "searched_here": False,
                "content_held": False,
            }
