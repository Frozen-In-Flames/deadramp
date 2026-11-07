"""Final GAPS batch extensions for Law Enforcement L1.

Clean-room, standard-library-only records extensions for the 5
open Extended entries of this group's union spec -- the Flock
Safety Platform's own engines, named from its description's own
verbs. Per-entry dispositions and the not-covered list are in
``BATCH.md`` in the group directory: 2 entries built as records
in-substrate (camera / sensor hardware, as a device registry;
public-safety collaboration & crime-analysis, as share and
reported-finding records), 3 shipped as labeled reference
implementations (license plate recognition, audio recognition,
video management & evidence capture) -- one of them, license
plate recognition, re-judged from its drafted build-extension
disposition, because recognition and matching against the real
world is execution, never records (the Law Enforcement
L3-adjacent unit's device-unlocking / evidence-extraction
precedent, and this batch's standing detection rule).

Design, following the core's doctrines:

- This module is a wrapper around :class:`LawEnfStore`; the
  core modules are untouched (byte-identical). Matter
  existence, membership, and lifecycle state are always read
  through the core store's public API, never re-implemented.
- **The hard privacy rule binds the whole surface, at its
  strictest.** Every record is keyed by an opaque
  caller-supplied ``*_ref`` string or a core record id, and
  holds metadata and SHA-256 digests only. No plate text, no
  vehicle identifier, no audio, no video, no image, no
  transcript, and no person's identifier is ever held: captured
  artifacts are named by their SHA-256 digest and byte count,
  exactly as the core's document registry names its documents.
  There is no parameter anywhere in this module that could
  accept any of those -- the batch tests pin that by signature
  (``TypeError``). Capabilities are attributed only as the
  fork's own listing states them; nothing here attributes
  facial recognition, predictive policing, or intelligence
  feeds to the fork, and nothing here builds them.
- **Records of the platform's work, never the platform's
  engines.** Recognition, detection, and capture run against
  the real world on the vendor's network; what this substrate
  builds is the records surface those functions presuppose --
  job records and reported outcome records for the three
  reference entries, device registrations and reported status
  records for the hardware entry, and share / receipt and
  analysis / finding records for the collaboration entry.
  Every record carries its boundary label (``recognized_here``
  / ``plates_read_here`` / ``matched_here`` /
  ``detected_here`` / ``captured_here`` / ``stored_here`` /
  ``manufactured_here`` / ``transmitted_here`` /
  ``shared_here`` / ``analyzed_here`` /
  ``patterns_computed_here`` / ``computed_here`` /
  ``content_held`` are False; the reference entries also carry
  ``reference_stub: True``, and the transport-shaped records
  carry ``reference_transport: True``). Outcome, status, and
  finding labels are recorded **verbatim** as reported -- the
  core's citation discipline: never normalized, never scored,
  never aggregated into a computed status. No score, rating,
  or risk figure exists anywhere on this surface.
- RBAC goes through :mod:`lawenf.access` exactly as the core
  enforces it: the extension maps each operation onto an
  existing core action (the core action set is fixed -- see
  the mapping in ``BATCH.md``), checks it *before* any state
  change or id allocation for actors that carry a role, and
  records denied attempts on the core audit log as
  ``ext_<action>:denied``. Matter membership -- the core's
  second boundary -- is enforced through the core store on
  every operation, and writes additionally require an open
  matter, mirroring the core's ``need_open`` discipline. At
  this tier the audit log is the founding plain append-only
  log: no Moderate/High apparatus (hash chains, lockout, the
  auditor role) is inherited downward, exactly as the union
  spec states.
- Derived values are derived at read and never stored: view
  counts and latest reported labels. Stored records carry no
  derived key; tests pin that. The latest-label derivation
  lives at a single named seam (``_latest_label``): the
  batch's fresh negative control.
- The extension surface is in-process only: the founding HTTP
  service layer is unchanged and does not expose extension
  operations.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None:
        _non_empty(value, what)
    return value


def _sha256_or_none(value, what):
    if value is not None:
        if not isinstance(value, str) or not _SHA256_RE.match(value):
            raise ValidationError(
                "%s must be exactly 64 lowercase hex characters" % (what,)
            )
    return value


def _count_or_none(value, what):
    if value is not None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValidationError("%s must be an integer >= 0" % (what,))
    return value


class LawEnfExtensions:
    """GAPS-batch extension surface over a core LawEnfStore."""

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

        Mirrors the core store: actors carrying a role are
        checked against the core permission matrix before
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

    def _matter(self, actor, matter_id, audit_action, need_open=False):
        """Resolve a matter through the core store (existence and
        membership enforced there); a membership denial is audited
        under the extension action name. Writes pass
        ``need_open=True`` and require an open matter, mirroring
        the core's child-record discipline."""
        try:
            matter = self.store.get_matter(matter_id, actor)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", matter_id)
            raise
        if need_open and matter["status"] != "open":
            raise ValidationError(
                "matter %s is closed; no new records may be added" % (matter_id,)
            )
        return matter

    def _create(self, kind, prefix, fields, actor, audit_action):
        """Commit a record, auditing before the commit.

        The audit entry is written to the core audit log first;
        only then is the record inserted and the id counter
        advanced -- a failed operation consumes no id and
        changes nothing, exactly as in the core store.
        """
        with self._lock:
            record_id = "%s-%d" % (prefix, self._counters.get(prefix, 0) + 1)
            record = {"id": record_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._audit(actor, audit_action, record_id,
                        details={"kind": kind})
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            return copy.deepcopy(record)

    def _get(self, kind, record_id, matter_id=None):
        record = self._records.get((kind, record_id))
        if record is None or (matter_id is not None
                              and record["matter_id"] != matter_id):
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id, matter_id=None):
        return copy.deepcopy(self._get(kind, record_id, matter_id))

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

    def _check_ref_unique(self, kind, matter_id, field, value, what):
        for record in self._list(kind, matter_id=matter_id):
            if record[field] == value:
                raise ValidationError(
                    "%s %r already exists in matter %s"
                    % (what, value, matter_id))

    @staticmethod
    def _latest_label(records, key):
        """The latest-label seam: the current reported label of a
        record stream is its most recently recorded label.

        Every derived view that reports a "latest" label goes
        through this single point. MUTATION DRILL NOTE: this seam
        is the batch unit's fresh negative-control target --
        reading the earliest record instead would silently
        misstate every current label while leaving the stored
        record shapes intact (see tests/README.md).
        """
        if not records:
            return None
        return records[-1][key]

    # -- License plate recognition engine & camera network ----------
    # Re-judged to a labeled reference implementation (drafted
    # build-extension; grounds in BATCH.md): plate reading and
    # vehicle matching are recognition against the real world --
    # sensing and matching executed by the camera network, not
    # records. What the substrate can honestly hold is the job
    # registry the capability's use presupposes: job records and
    # reported outcome records. No plate text and no vehicle
    # identifier exists in any field shape: an outcome names its
    # result by an opaque reference and an optional reported
    # count only. Every record carries ``reference_stub: True``,
    # ``recognized_here: False``, ``plates_read_here: False``,
    # and ``matched_here: False``.

    def record_lpr_job(self, matter_id, job_ref, actor, engine_label=None,
                       scope_label=None):
        """Record an LPR job (reference). Action: search_write."""
        self._guard(actor, "search_write", "ext_lpr_job", matter_id)
        _non_empty(job_ref, "job_ref")
        _string_or_none(engine_label, "engine_label")
        _string_or_none(scope_label, "scope_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_lpr_job", need_open=True)
            self._check_ref_unique("lpr_job", matter_id, "job_ref",
                                   job_ref, "job_ref")
            return self._create(
                "lpr_job", "lpr",
                {"matter_id": matter_id, "job_ref": job_ref,
                 "engine_label": engine_label, "scope_label": scope_label,
                 "reference_stub": True, "recognized_here": False,
                 "plates_read_here": False, "matched_here": False,
                 "status": "recorded_reference_only"},
                actor, "ext_lpr_job")

    def get_lpr_job(self, matter_id, job_id, actor=None):
        """Return one LPR job record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_lpr_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_lpr_read")
            return self._fetch("lpr_job", job_id, matter_id)

    def list_lpr_jobs(self, matter_id, actor=None):
        """List LPR job records in a matter. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_lpr_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_lpr_read")
            return self._list("lpr_job", matter_id=matter_id)

    def record_lpr_outcome(self, matter_id, job_id, outcome_label, actor,
                           result_ref=None, result_count=None):
        """Record a reported LPR outcome (reference); the outcome
        label is stored verbatim. Action: search_write."""
        self._guard(actor, "search_write", "ext_lpr_outcome", matter_id)
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(result_ref, "result_ref")
        _count_or_none(result_count, "result_count")
        with self._lock:
            self._matter(actor, matter_id, "ext_lpr_outcome", need_open=True)
            self._get("lpr_job", job_id, matter_id)
            return self._create(
                "lpr_outcome", "lpo",
                {"matter_id": matter_id, "job_id": job_id,
                 "outcome_label": outcome_label, "result_ref": result_ref,
                 "result_count": result_count, "reference_stub": True},
                actor, "ext_lpr_outcome")

    def list_lpr_outcomes(self, matter_id, job_id, actor=None):
        """List outcome records for a job. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_lpr_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_lpr_read")
            self._get("lpr_job", job_id, matter_id)
            return self._list("lpr_outcome", matter_id=matter_id,
                              job_id=job_id)

    def lpr_view(self, matter_id, job_id, actor=None):
        """Derived LPR view: outcome count and latest reported
        outcome. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_lpr_view", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_lpr_view")
            job = self._fetch("lpr_job", job_id, matter_id)
            outcomes = self._list("lpr_outcome", matter_id=matter_id,
                                  job_id=job_id)
            return {
                "matter_id": matter_id,
                "job_id": job_id,
                "job_ref": job["job_ref"],
                "derived": True,
                "outcome_count": len(outcomes),
                "latest_outcome": self._latest_label(
                    outcomes, "outcome_label"),
            }

    # -- Audio recognition sensors & detection ------------------------
    # Labeled reference implementation, as drafted (stub-engine):
    # audio recognition is detection against the real world by
    # the sensor layer -- execution, not records. Job records
    # name the sensor by an opaque reference only; outcome
    # records hold reported labels verbatim. No audio and no
    # transcript exists in any field shape. Every record carries
    # ``reference_stub: True``, ``detected_here: False``, and
    # ``recognized_here: False``.

    def record_audio_job(self, matter_id, job_ref, actor, sensor_ref=None,
                         engine_label=None):
        """Record an audio-recognition job (reference).

        Action: search_write."""
        self._guard(actor, "search_write", "ext_audio_job", matter_id)
        _non_empty(job_ref, "job_ref")
        _string_or_none(sensor_ref, "sensor_ref")
        _string_or_none(engine_label, "engine_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_audio_job", need_open=True)
            self._check_ref_unique("audio_job", matter_id, "job_ref",
                                   job_ref, "job_ref")
            return self._create(
                "audio_job", "aud",
                {"matter_id": matter_id, "job_ref": job_ref,
                 "sensor_ref": sensor_ref, "engine_label": engine_label,
                 "reference_stub": True, "detected_here": False,
                 "recognized_here": False,
                 "status": "recorded_reference_only"},
                actor, "ext_audio_job")

    def get_audio_job(self, matter_id, job_id, actor=None):
        """Return one audio job record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_audio_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_audio_read")
            return self._fetch("audio_job", job_id, matter_id)

    def list_audio_jobs(self, matter_id, actor=None):
        """List audio job records in a matter. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_audio_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_audio_read")
            return self._list("audio_job", matter_id=matter_id)

    def record_audio_outcome(self, matter_id, job_id, outcome_label, actor,
                             result_ref=None):
        """Record a reported audio outcome (reference); the
        outcome label is stored verbatim. Action: search_write."""
        self._guard(actor, "search_write", "ext_audio_outcome", matter_id)
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(result_ref, "result_ref")
        with self._lock:
            self._matter(actor, matter_id, "ext_audio_outcome",
                         need_open=True)
            self._get("audio_job", job_id, matter_id)
            return self._create(
                "audio_outcome", "auo",
                {"matter_id": matter_id, "job_id": job_id,
                 "outcome_label": outcome_label, "result_ref": result_ref,
                 "reference_stub": True},
                actor, "ext_audio_outcome")

    def list_audio_outcomes(self, matter_id, job_id, actor=None):
        """List outcome records for a job. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_audio_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_audio_read")
            self._get("audio_job", job_id, matter_id)
            return self._list("audio_outcome", matter_id=matter_id,
                              job_id=job_id)

    def audio_view(self, matter_id, job_id, actor=None):
        """Derived audio view: outcome count and latest reported
        outcome. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_audio_view", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_audio_view")
            job = self._fetch("audio_job", job_id, matter_id)
            outcomes = self._list("audio_outcome", matter_id=matter_id,
                                  job_id=job_id)
            return {
                "matter_id": matter_id,
                "job_id": job_id,
                "job_ref": job["job_ref"],
                "derived": True,
                "outcome_count": len(outcomes),
                "latest_outcome": self._latest_label(
                    outcomes, "outcome_label"),
            }

    # -- Video management & evidence-capture pipeline -----------------
    # Labeled reference implementation, as drafted (stub-engine):
    # the pipeline captures, stores, and serves video and audio
    # from the camera network -- media transport and content
    # storage over systems this substrate never holds; the
    # entry's own parenthetical states the bound (the substrate
    # captures nothing and stores no content). Capture job
    # records name the device by an opaque reference only;
    # outcome records name a captured artifact by its SHA-256
    # digest and byte count under exactly the core document
    # registry's discipline, never by content. Every record
    # carries ``reference_stub: True`` and
    # ``reference_transport: True``, with ``captured_here`` /
    # ``stored_here`` / ``content_held`` False.

    def record_capture_job(self, matter_id, job_ref, actor, device_ref=None,
                           format_label=None):
        """Record an evidence-capture job (reference).

        Action: search_write."""
        self._guard(actor, "search_write", "ext_capture_job", matter_id)
        _non_empty(job_ref, "job_ref")
        _string_or_none(device_ref, "device_ref")
        _string_or_none(format_label, "format_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_capture_job", need_open=True)
            self._check_ref_unique("capture_job", matter_id, "job_ref",
                                   job_ref, "job_ref")
            return self._create(
                "capture_job", "cap",
                {"matter_id": matter_id, "job_ref": job_ref,
                 "device_ref": device_ref, "format_label": format_label,
                 "reference_stub": True, "reference_transport": True,
                 "captured_here": False, "stored_here": False,
                 "content_held": False,
                 "status": "recorded_reference_only"},
                actor, "ext_capture_job")

    def get_capture_job(self, matter_id, job_id, actor=None):
        """Return one capture job record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_capture_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_capture_read")
            return self._fetch("capture_job", job_id, matter_id)

    def list_capture_jobs(self, matter_id, actor=None):
        """List capture job records in a matter. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_capture_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_capture_read")
            return self._list("capture_job", matter_id=matter_id)

    def record_capture_outcome(self, matter_id, job_id, outcome_label,
                               actor, output_sha256=None, size_bytes=None):
        """Record a reported capture outcome (reference); a
        captured artifact is named by digest + byte count only.

        Action: search_write."""
        self._guard(actor, "search_write", "ext_capture_outcome", matter_id)
        _non_empty(outcome_label, "outcome_label")
        _sha256_or_none(output_sha256, "output_sha256")
        _count_or_none(size_bytes, "size_bytes")
        with self._lock:
            self._matter(actor, matter_id, "ext_capture_outcome",
                         need_open=True)
            self._get("capture_job", job_id, matter_id)
            return self._create(
                "capture_outcome", "cao",
                {"matter_id": matter_id, "job_id": job_id,
                 "outcome_label": outcome_label,
                 "output_sha256": output_sha256, "size_bytes": size_bytes,
                 "reference_stub": True, "reference_transport": True,
                 "content_held": False},
                actor, "ext_capture_outcome")

    def list_capture_outcomes(self, matter_id, job_id, actor=None):
        """List outcome records for a job. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_capture_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_capture_read")
            self._get("capture_job", job_id, matter_id)
            return self._list("capture_outcome", matter_id=matter_id,
                              job_id=job_id)

    def capture_view(self, matter_id, job_id, actor=None):
        """Derived capture view: outcome count and latest
        reported outcome. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_capture_view", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_capture_view")
            job = self._fetch("capture_job", job_id, matter_id)
            outcomes = self._list("capture_outcome", matter_id=matter_id,
                                  job_id=job_id)
            return {
                "matter_id": matter_id,
                "job_id": job_id,
                "job_ref": job["job_ref"],
                "derived": True,
                "outcome_count": len(outcomes),
                "latest_outcome": self._latest_label(
                    outcomes, "outcome_label"),
            }

    # -- Camera / sensor hardware -------------------------------------
    # Built as the device registry surface: device registration
    # records (an opaque device reference, the caller's kind
    # label verbatim, an optional opaque site reference) and
    # reported status records (the status label verbatim as
    # reported by whatever system operates the device). The
    # manufactured devices themselves are hardware and are
    # outside a software build entirely -- nothing here
    # manufactures, operates, or observes a device
    # (``manufactured_here: False`` on every registration); the
    # registry is the records form the entry's fleet presupposes.
    # The current status derives at read through the
    # ``_latest_label`` seam; the stored registration carries no
    # current status.

    def register_device(self, matter_id, device_ref, kind_label, actor,
                        site_ref=None):
        """Register a camera / sensor device record.

        Action: document_write."""
        self._guard(actor, "document_write", "ext_device_register", matter_id)
        _non_empty(device_ref, "device_ref")
        _non_empty(kind_label, "kind_label")
        _string_or_none(site_ref, "site_ref")
        with self._lock:
            self._matter(actor, matter_id, "ext_device_register",
                         need_open=True)
            self._check_ref_unique("device_registration", matter_id,
                                   "device_ref", device_ref, "device_ref")
            return self._create(
                "device_registration", "dev",
                {"matter_id": matter_id, "device_ref": device_ref,
                 "kind_label": kind_label, "site_ref": site_ref,
                 "manufactured_here": False, "content_held": False},
                actor, "ext_device_register")

    def get_device(self, matter_id, device_id, actor=None):
        """Return one device registration. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_device_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_device_read")
            return self._fetch("device_registration", device_id, matter_id)

    def list_devices(self, matter_id, actor=None):
        """List device registrations in a matter. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_device_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_device_read")
            return self._list("device_registration", matter_id=matter_id)

    def record_device_status(self, matter_id, device_id, status_label,
                             actor):
        """Record a reported device status; the label is stored
        verbatim. Action: document_write."""
        self._guard(actor, "document_write", "ext_device_status", matter_id)
        _non_empty(status_label, "status_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_device_status",
                         need_open=True)
            self._get("device_registration", device_id, matter_id)
            return self._create(
                "device_status", "dst",
                {"matter_id": matter_id, "device_id": device_id,
                 "status_label": status_label},
                actor, "ext_device_status")

    def list_device_statuses(self, matter_id, device_id, actor=None):
        """List status records for a device. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_device_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_device_read")
            self._get("device_registration", device_id, matter_id)
            return self._list("device_status", matter_id=matter_id,
                              device_id=device_id)

    def device_view(self, matter_id, device_id, actor=None):
        """Derived device view: status count and the latest
        reported status. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_device_view", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_device_view")
            device = self._fetch("device_registration", device_id, matter_id)
            statuses = self._list("device_status", matter_id=matter_id,
                                  device_id=device_id)
            return {
                "matter_id": matter_id,
                "device_id": device_id,
                "device_ref": device["device_ref"],
                "derived": True,
                "status_count": len(statuses),
                "latest_status_label": self._latest_label(
                    statuses, "status_label"),
            }

    # -- Public-safety collaboration & crime-analysis platform --------
    # Built as records, in the tier family's adjudicated forms
    # (the L3-adjacent unit's information-sharing and forensic
    # analysis surfaces): share records binding an opaque target
    # reference to an opaque recipient reference, with receipt
    # records holding delivery outcomes verbatim as reported --
    # every record carries ``reference_transport: True`` and
    # ``transmitted_here: False`` (the share record also
    # ``shared_here: False``, ``content_held: False``): the
    # records describe shares effected on systems owned
    # elsewhere. Analysis records and finding records hold
    # reported labels verbatim; no pattern is computed and no
    # finding is derived here (``analyzed_here`` /
    # ``patterns_computed_here`` / ``computed_here`` False) --
    # findings are records; computing is an engine. Nothing
    # here predicts anything: no score-shaped key exists on
    # this surface.

    def record_share(self, matter_id, share_ref, target_ref, recipient_ref,
                     actor, scope_label=None):
        """Record an inter-agency share effected elsewhere.

        Action: annotation_write."""
        self._guard(actor, "annotation_write", "ext_share_record", matter_id)
        _non_empty(share_ref, "share_ref")
        _non_empty(target_ref, "target_ref")
        _non_empty(recipient_ref, "recipient_ref")
        _string_or_none(scope_label, "scope_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_share_record", need_open=True)
            self._check_ref_unique("collaboration_share", matter_id,
                                   "share_ref", share_ref, "share_ref")
            return self._create(
                "collaboration_share", "csh",
                {"matter_id": matter_id, "share_ref": share_ref,
                 "target_ref": target_ref, "recipient_ref": recipient_ref,
                 "scope_label": scope_label, "reference_transport": True,
                 "transmitted_here": False, "shared_here": False,
                 "content_held": False},
                actor, "ext_share_record")

    def get_share(self, matter_id, share_id, actor=None):
        """Return one share record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_share_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_share_read")
            return self._fetch("collaboration_share", share_id, matter_id)

    def list_shares(self, matter_id, actor=None):
        """List share records in a matter. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_share_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_share_read")
            return self._list("collaboration_share", matter_id=matter_id)

    def record_share_receipt(self, matter_id, share_id, outcome_label,
                             actor):
        """Record a reported share delivery outcome, verbatim.

        Action: annotation_write."""
        self._guard(actor, "annotation_write", "ext_share_receipt",
                    matter_id)
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_share_receipt",
                         need_open=True)
            self._get("collaboration_share", share_id, matter_id)
            return self._create(
                "share_receipt", "crp",
                {"matter_id": matter_id, "share_id": share_id,
                 "outcome_label": outcome_label,
                 "reference_transport": True},
                actor, "ext_share_receipt")

    def list_share_receipts(self, matter_id, share_id, actor=None):
        """List receipts for a share. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_share_read", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_share_read")
            self._get("collaboration_share", share_id, matter_id)
            return self._list("share_receipt", matter_id=matter_id,
                              share_id=share_id)

    def collaboration_view(self, matter_id, share_id, actor=None):
        """Derived collaboration view: receipt count and latest
        reported outcome. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_collaboration_view",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_collaboration_view")
            share = self._fetch("collaboration_share", share_id, matter_id)
            receipts = self._list("share_receipt", matter_id=matter_id,
                                  share_id=share_id)
            return {
                "matter_id": matter_id,
                "share_id": share_id,
                "share_ref": share["share_ref"],
                "derived": True,
                "receipt_count": len(receipts),
                "latest_outcome": self._latest_label(
                    receipts, "outcome_label"),
            }

    def record_analysis(self, matter_id, analysis_ref, actor,
                        method_label=None, document_id=None):
        """Record a crime-analysis record over registry metadata.

        Action: search_write."""
        self._guard(actor, "search_write", "ext_analysis_record", matter_id)
        _non_empty(analysis_ref, "analysis_ref")
        _string_or_none(method_label, "method_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_analysis_record",
                         need_open=True)
            if document_id is not None:
                self.store.get_document(matter_id, document_id, actor)
            self._check_ref_unique("analysis_record", matter_id,
                                   "analysis_ref", analysis_ref,
                                   "analysis_ref")
            return self._create(
                "analysis_record", "anl",
                {"matter_id": matter_id, "analysis_ref": analysis_ref,
                 "method_label": method_label, "document_id": document_id,
                 "analyzed_here": False, "patterns_computed_here": False,
                 "content_held": False},
                actor, "ext_analysis_record")

    def get_analysis(self, matter_id, analysis_id, actor=None):
        """Return one analysis record. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_analysis_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_analysis_read")
            return self._fetch("analysis_record", analysis_id, matter_id)

    def list_analyses(self, matter_id, actor=None):
        """List analysis records in a matter. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_analysis_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_analysis_read")
            return self._list("analysis_record", matter_id=matter_id)

    def record_analysis_finding(self, matter_id, analysis_id, result_ref,
                                actor, reported_label=None):
        """Record a reported analysis finding; the finding is a
        record, never a computation here. Action: search_write."""
        self._guard(actor, "search_write", "ext_analysis_finding", matter_id)
        _non_empty(result_ref, "result_ref")
        _string_or_none(reported_label, "reported_label")
        with self._lock:
            self._matter(actor, matter_id, "ext_analysis_finding",
                         need_open=True)
            self._get("analysis_record", analysis_id, matter_id)
            return self._create(
                "analysis_finding", "anf",
                {"matter_id": matter_id, "analysis_id": analysis_id,
                 "result_ref": result_ref, "reported_label": reported_label,
                 "computed_here": False},
                actor, "ext_analysis_finding")

    def list_analysis_findings(self, matter_id, analysis_id, actor=None):
        """List findings for an analysis. Action: matter_read."""
        self._guard_read(actor, "matter_read", "ext_analysis_read",
                         matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_analysis_read")
            self._get("analysis_record", analysis_id, matter_id)
            return self._list("analysis_finding", matter_id=matter_id,
                              analysis_id=analysis_id)

    def analysis_view(self, matter_id, analysis_id, actor=None):
        """Derived analysis view: finding count and latest
        reported label. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_analysis_view", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_analysis_view")
            analysis = self._fetch("analysis_record", analysis_id, matter_id)
            findings = self._list("analysis_finding", matter_id=matter_id,
                                  analysis_id=analysis_id)
            return {
                "matter_id": matter_id,
                "analysis_id": analysis_id,
                "analysis_ref": analysis["analysis_ref"],
                "derived": True,
                "finding_count": len(findings),
                "latest_reported_label": self._latest_label(
                    findings, "reported_label"),
            }

    # -- Extension reporting -------------------------------------------
    # Deterministic counts over the extension surface's own
    # records, derived at read -- the reporting-shaped slice of
    # the collaboration entry and the batch's standing reporting
    # form. The figures provably track registry state because
    # they are computed from it at read; no stored record
    # carries figures, and no figure is a score.

    def extension_report(self, matter_id, actor=None):
        """Derived counts over every extension record kind in a
        matter. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_report", matter_id)
        with self._lock:
            self._matter(actor, matter_id, "ext_report")
            kinds = (
                "lpr_job", "lpr_outcome", "audio_job", "audio_outcome",
                "capture_job", "capture_outcome", "device_registration",
                "device_status", "collaboration_share", "share_receipt",
                "analysis_record", "analysis_finding",
            )
            return {
                "matter_id": matter_id,
                "derived": True,
                "counts": {
                    kind: len(self._list(kind, matter_id=matter_id))
                    for kind in kinds
                },
            }
