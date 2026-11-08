"""Final GAPS batch, second unit — LMS L2 remainder addition.

Clean-room, standard-library-only extension for the one open entry
of the GAPS.md section "Remainder Addition — Learning Management
L2 (+1 fork)" (idx 678; see ``BATCH-ADDITION.md`` in the group
directory). This module is a second wrapper around
:class:`LmsStore`; every existing module — the core modules and
the first batch unit's ``extensions.py`` — is untouched.

The entry names the hosted off-the-shelf catalogue ITSELF:
thousands of video courses, ebooks, audiobooks, boot camps,
hands-on practice labs, and the assessment content it includes,
supplied by the addition fork's platform. That supply is content
hosted and delivered by an external platform; this substrate's
catalog holds records ABOUT content (core content items are
metadata), and it holds no content bytes, hosts nothing, and
delivers nothing. The drafted disposition is therefore
``stub-engine`` and the surface is a labeled reference
implementation, in the house form:

- Library item records name catalogue items by title and format
  — the format vocabulary is the fork's own list from its
  description (video courses, ebooks, audiobooks, boot camps,
  practice labs, and assessment content) — with the supplying
  platform named by an opaque ``provider_ref``. An item may bind
  to a core course and/or a core content item BY ID ONLY (the
  binding is a cross-reference between records; the core record
  is never copied and never modified, pinned by test). Every
  record carries ``reference_stub: True`` and
  ``reference_transport: True`` and states on its face
  ``hosted_here: False``, ``content_held: False``,
  ``delivered_here: False``.
- Assessment content is catalogue content, exactly as the
  addendum books it: the ``assessment_content`` format label
  names items IN the catalogue, never assessment administration.
  No item is administered here (``administered_here: False`` on
  every record), and no score shape exists anywhere on the
  surface — the founding no-score invariant binds this unit
  exactly as it binds the core, pinned by a recursive key scan.
- Access reports record, verbatim, what the external platform
  reported about an item's availability on a channel (the fork's
  own channels: web browser and mobile apps). Outcome labels are
  stored exactly as reported (``outcome_basis:
  platform_reported``); an optional reported item count is held
  exactly as reported, integers only. Nothing is transmitted,
  fetched, or checked here (``transmitted_here: False``).
- Practice-lab environment records name a lab environment by
  opaque reference only, bound to a library item whose format is
  ``practice_lab``. No environment is provisioned and no lab
  executes here (``provisioned_here: False``,
  ``executed_here: False``); no content-shaped, session-shaped,
  or credential-shaped parameter exists on the surface.
- Views derive their computed values at read and never store
  them: an item view's access-report count and latest reported
  outcome label derive from the recorded reports via the
  ``_latest_outcome_label`` seam, and the library summary is
  deterministic counts over the recorded reference records,
  method-labeled as such.

Doctrines carried from the core and the first batch unit: opaque
``*_ref`` strings only; append-only audit on the core store's log
with ``exta_``-prefixed actions for every successful mutation;
RBAC via :mod:`lms.access` with the core's existing actions,
enforced before any state change or id allocation, so a failed
operation consumes no id and changes nothing; no public method
accepts ``**kwargs``, so no content-, credential-, or
score-shaped argument can be smuggled past the signatures.
"""

import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

LIBRARY_FORMATS = (
    "video_course", "ebook", "audiobook", "boot_camp",
    "practice_lab", "assessment_content",
)
ACCESS_CHANNELS = ("web_browser", "mobile_app")


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


class LmsExtensionsAddition:
    """Second extension surface wrapping one :class:`LmsStore`."""

    def __init__(self, store):
        self.store = store
        self._library_items = {}
        self._access_reports = {}
        self._lab_environments = {}
        self._counters = {"lib": 0, "acc": 0, "lab": 0}
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

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    # -- Licensed content library (labeled reference) -------------------
    # Library items are records ABOUT the external platform's
    # catalogue. The catalogue itself — its content, its hosting,
    # its delivery — stays with the platform; every record says so.

    def create_library_item(self, title, format_kind, actor, provider_ref,
                            core_course_id=None, core_content_id=None):
        """Record one licensed-catalogue item — labeled reference.

        Action: catalog_write. ``format_kind`` is one of the fork's
        own format list (LIBRARY_FORMATS). ``provider_ref`` names
        the supplying platform by opaque reference. Optional core
        bindings are by id only and must resolve; a bound content
        item that belongs to a different course than
        ``core_course_id`` is rejected, mirroring the first unit's
        delivery-session mismatch rule.
        """
        self._require_actor(actor, "catalog_write")
        _non_empty(title, "library item title")
        _non_empty(provider_ref, "provider_ref")
        if format_kind not in LIBRARY_FORMATS:
            raise ValidationError(
                "format_kind must be one of %s"
                % (", ".join(LIBRARY_FORMATS),))
        with self._lock:
            if core_course_id is not None:
                self.store.get_course(core_course_id, actor=None)
            if core_content_id is not None:
                item = self.store.get_content_item(core_content_id,
                                                   actor=None)
                if (core_course_id is not None
                        and item["course_id"] is not None
                        and item["course_id"] != core_course_id):
                    raise ValidationError(
                        "content item %r does not belong to course %r"
                        % (core_content_id, core_course_id))
            item_id = self._next_id("lib")
            record = {
                "id": item_id,
                "title": title,
                "format_kind": format_kind,
                "provider_ref": provider_ref,
                "core_course_id": core_course_id,
                "core_content_id": core_content_id,
                "reference_stub": True,
                "reference_transport": True,
                "hosted_here": False,
                "content_held": False,
                "delivered_here": False,
                "administered_here": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._library_items[item_id] = record
            self._audit(actor, "exta_library_item_create", item_id,
                        details={"title": title,
                                 "format_kind": format_kind,
                                 "provider_ref": provider_ref,
                                 "reference_stub": True})
            return dict(record)

    def get_library_item(self, item_id, actor=None):
        """Return one library item record. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            return dict(self._get(self._library_items, item_id,
                                  "library item"))

    def list_library_items(self, actor=None, format_kind=None,
                           provider_ref=None):
        """Return library item records. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        if format_kind is not None and format_kind not in LIBRARY_FORMATS:
            raise ValidationError(
                "format_kind must be one of %s"
                % (", ".join(LIBRARY_FORMATS),))
        with self._lock:
            records = list(self._library_items.values())
            if format_kind is not None:
                records = [r for r in records
                           if r["format_kind"] == format_kind]
            if provider_ref is not None:
                records = [r for r in records
                           if r["provider_ref"] == provider_ref]
            return [dict(r) for r in records]

    # -- Access reports (verbatim platform reports) ---------------------

    def record_access_report(self, library_item_id, channel, outcome_label,
                             actor, reported_item_count=None):
        """Record a platform access report — verbatim, labeled.

        Action: catalog_write. ``channel`` is one of the fork's own
        access channels (web browser, mobile apps). The outcome
        label is stored exactly as the external platform reported
        it; an optional ``reported_item_count`` is held exactly as
        reported (non-negative integers only — bools and floats are
        rejected, no id consumed). Nothing is transmitted, fetched,
        or availability-checked by this call.
        """
        self._require_actor(actor, "catalog_write")
        if channel not in ACCESS_CHANNELS:
            raise ValidationError(
                "channel must be one of %s"
                % (", ".join(ACCESS_CHANNELS),))
        _non_empty(outcome_label, "outcome_label")
        if reported_item_count is not None:
            if (isinstance(reported_item_count, bool)
                    or not isinstance(reported_item_count, int)
                    or reported_item_count < 0):
                raise ValidationError(
                    "reported_item_count must be a non-negative integer")
        with self._lock:
            self._get(self._library_items, library_item_id, "library item")
            report_id = self._next_id("acc")
            record = {
                "id": report_id,
                "library_item_id": library_item_id,
                "channel": channel,
                "outcome_label": outcome_label,
                "reported_item_count": reported_item_count,
                "outcome_basis": "platform_reported",
                "reference_stub": True,
                "reference_transport": True,
                "transmitted_here": False,
                "state": "recorded_reference_only",
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._access_reports[report_id] = record
            self._audit(actor, "exta_access_report_record", report_id,
                        details={"library_item_id": library_item_id,
                                 "channel": channel,
                                 "reference_transport": True})
            return dict(record)

    def list_access_reports(self, actor=None, library_item_id=None):
        """Return access report records. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            records = list(self._access_reports.values())
            if library_item_id is not None:
                records = [r for r in records
                           if r["library_item_id"] == library_item_id]
            return [dict(r) for r in records]

    @staticmethod
    def _latest_outcome_label(reports):
        """The latest recorded report's outcome label. Never stored.

        MUTATION DRILL NOTE: this seam is this unit's fresh
        negative control's load-bearing invariant — a view must
        read the LATEST recorded report's label, never the first.
        """
        return reports[-1]["outcome_label"] if reports else None

    def library_item_view(self, item_id, actor=None):
        """One item plus derived report facts. Action: catalog_read.

        The stored record carries no derived key; the view adds
        ``access_report_count`` and ``latest_outcome_label``
        derived at read from the recorded reports, with the
        derivation labeled by ``outcome_method``.
        """
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            record = self._get(self._library_items, item_id, "library item")
            reports = [r for r in self._access_reports.values()
                       if r["library_item_id"] == item_id]
            view = dict(record)
            view["access_report_count"] = len(reports)
            view["latest_outcome_label"] = self._latest_outcome_label(reports)
            view["outcome_method"] = "latest_recorded_platform_report"
            return view

    # -- Practice-lab environments (labeled reference) ------------------

    def record_lab_environment(self, library_item_id, environment_ref, actor,
                               mode_label="hands_on"):
        """Record a practice-lab environment — labeled reference.

        Action: catalog_write. The bound library item must be a
        ``practice_lab`` item. The environment is named by opaque
        reference only; nothing is provisioned and no lab executes
        here.
        """
        self._require_actor(actor, "catalog_write")
        _non_empty(environment_ref, "environment_ref")
        _non_empty(mode_label, "mode_label")
        with self._lock:
            item = self._get(self._library_items, library_item_id,
                             "library item")
            if item["format_kind"] != "practice_lab":
                raise ValidationError(
                    "library item %r is not a practice_lab item"
                    % (library_item_id,))
            lab_id = self._next_id("lab")
            record = {
                "id": lab_id,
                "library_item_id": library_item_id,
                "environment_ref": environment_ref,
                "mode_label": mode_label,
                "reference_stub": True,
                "reference_transport": True,
                "provisioned_here": False,
                "executed_here": False,
                "content_held": False,
                "state": "recorded_reference_only",
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._lab_environments[lab_id] = record
            self._audit(actor, "exta_lab_environment_record", lab_id,
                        details={"library_item_id": library_item_id,
                                 "environment_ref": environment_ref,
                                 "reference_stub": True})
            return dict(record)

    def list_lab_environments(self, actor=None, library_item_id=None):
        """Return lab environment records. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            records = list(self._lab_environments.values())
            if library_item_id is not None:
                records = [r for r in records
                           if r["library_item_id"] == library_item_id]
            return [dict(r) for r in records]

    # -- Library summary (deterministic counts over the records) ---------

    def library_summary(self, actor):
        """Counts over the recorded reference records. Action: report_read.

        Derived at read: item counts by the fork's format list,
        report and lab counts, and the latest reported outcome
        label across all recorded reports. Counts of THIS unit's
        records only — no catalogue size, usage, or learner figure
        is computed or claimed.
        """
        self._require_actor(actor, "report_read")
        with self._lock:
            by_format = {kind: 0 for kind in LIBRARY_FORMATS}
            for record in self._library_items.values():
                by_format[record["format_kind"]] += 1
            reports = list(self._access_reports.values())
            return {
                "method": "deterministic_counts",
                "counts_basis": "recorded_reference_records_only",
                "reference_stub": True,
                "library_items": len(self._library_items),
                "items_by_format": by_format,
                "access_reports": len(reports),
                "lab_environments": len(self._lab_environments),
                "latest_outcome_label": self._latest_outcome_label(reports),
            }
