"""Final GAPS batch, third unit — LMS L2 no-signal addition.

Clean-room, standard-library-only extension for the one open entry
of the GAPS.md section "No-Signal Addition — Learning Management
L2 (Skillsoft Private Cloud, F1207261443)" (idx 971; see
``BATCH-NOSIGNAL.md`` in the group directory). This module is a
third wrapper around :class:`LmsStore`; every existing module —
the core modules, the first batch unit's ``extensions.py``, and
the second batch unit's ``extensions_addition.py`` — is untouched.

This fork arrived by a different route: the remainder census left
it in its no-signal set (its cached marketplace description is a
339-character company profile of Skillsoft only, from which no
function could be cited), and the live-docs research pass resolved
its category afterwards from Skillsoft's own Percipio platform
documentation — the platform this Private Cloud offering delivers
(ADDENDUM.md sections 7-9). It claims **zero families** under the
group's taxonomy applied verbatim, and the group total stays at 26
claims across 3 forks.

The entry names the hosting *service* itself: a vendor-operated
dedicated/private-cloud deployment of the learning platform — the
offering's entire classified function, registered from the
classified function, not from a claim (ADDENDUM.md section 9).
Hosting and managed delivery are deployment-layer acts performed
by the vendor's platform; this build is a single-tenant reference
deployment that an embedding organization runs, and it operates
no hosting service, provisions no cloud, hosts no platform, and
delivers no learning. The drafted disposition is therefore
``stub-engine`` and the surface is a labeled reference
implementation, in the house form:

- Hosting deployment records name a vendor-operated deployment
  by title, deployment kind, and opaque ``provider_ref`` /
  ``platform_ref`` references. An optional binding to a core
  course is **by id only** and must resolve (the hosted
  platform's catalogue records are Core 2 records; the binding is
  a cross-reference between records — the core record is never
  copied and never modified, pinned by test). Every record
  carries ``reference_stub: True`` and ``reference_transport:
  True`` and states on its face ``hosted_here: False``,
  ``provisioned_here: False``, ``managed_here: False``,
  ``delivered_here: False``, and ``content_held: False``.
- Managed delivery report records hold, verbatim, what the
  vendor's platform reported about a deployment's delivery: the
  outcome label stored exactly as reported (``outcome_basis:
  vendor_reported``) over the platform's access channels, and an
  optional reported learner count held exactly as reported
  (non-negative integers only). Nothing is transmitted, fetched,
  checked, hosted, or delivered by this call
  (``transmitted_here: False``).
- Views derive their computed values at read and never store
  them: a deployment view's delivery-report count and latest
  reported outcome label derive from the recorded reports via
  the ``_latest_outcome_label`` seam, and the hosting summary is
  deterministic counts over the recorded reference records,
  method-labeled as such. No usage, uptime, or learner figure
  beyond a count held exactly as reported is computed or claimed.

Doctrines carried from the core and the prior batch units: the
founding **no-score invariant binds this surface exactly as it
binds the core** — no record shape carries a score field and
nothing computes one, pinned by a recursive key scan; opaque
``*_ref`` strings only; derived-never-stored for every computed
value; append-only audit on the core store's log with
``extn_``-prefixed actions for every successful mutation; RBAC
via :mod:`lms.access` with the core's existing actions, enforced
before any state change or id allocation, so a failed operation
consumes no id and changes nothing; no public method accepts
``**kwargs``, so no content-, credential-, or score-shaped
argument can be smuggled past the signatures.
"""

import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

DEPLOYMENT_KINDS = ("private_cloud", "dedicated_private_cloud")
DELIVERY_CHANNELS = ("web_browser", "mobile_app", "hosted_platform")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


class LmsExtensionsNoSignal:
    """Third extension surface wrapping one :class:`LmsStore`."""

    def __init__(self, store):
        self.store = store
        self._deployments = {}
        self._delivery_reports = {}
        self._counters = {"hst": 0, "dlr": 0}
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

    # -- Private-cloud hosting deployments (labeled reference) --------
    # Deployment records are records ABOUT a vendor-operated
    # deployment. The hosting service itself — its provisioning,
    # its operation, its managed delivery — stays with the vendor;
    # every record says so.

    def create_hosting_deployment(self, title, deployment_kind, actor,
                                  provider_ref, platform_ref,
                                  core_course_id=None):
        """Record one vendor-operated hosting deployment — reference.

        Action: catalog_write. ``deployment_kind`` is one of
        DEPLOYMENT_KINDS (the offering's own kinds: a private-cloud
        deployment, dedicated to one customer). ``provider_ref``
        and ``platform_ref`` name the operating vendor and the
        delivered platform by opaque reference. An optional core
        binding is by id only and must resolve.
        """
        self._require_actor(actor, "catalog_write")
        _non_empty(title, "deployment title")
        _non_empty(provider_ref, "provider_ref")
        _non_empty(platform_ref, "platform_ref")
        if deployment_kind not in DEPLOYMENT_KINDS:
            raise ValidationError(
                "deployment_kind must be one of %s"
                % (", ".join(DEPLOYMENT_KINDS),))
        with self._lock:
            if core_course_id is not None:
                self.store.get_course(core_course_id, actor=None)
            deployment_id = self._next_id("hst")
            record = {
                "id": deployment_id,
                "title": title,
                "deployment_kind": deployment_kind,
                "provider_ref": provider_ref,
                "platform_ref": platform_ref,
                "core_course_id": core_course_id,
                "reference_stub": True,
                "reference_transport": True,
                "hosted_here": False,
                "provisioned_here": False,
                "managed_here": False,
                "delivered_here": False,
                "content_held": False,
                "state": "recorded_reference_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._deployments[deployment_id] = record
            self._audit(actor, "extn_hosting_deployment_create",
                        deployment_id,
                        details={"title": title,
                                 "deployment_kind": deployment_kind,
                                 "provider_ref": provider_ref,
                                 "reference_stub": True})
            return dict(record)

    def get_hosting_deployment(self, deployment_id, actor=None):
        """Return one deployment record. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            return dict(self._get(self._deployments, deployment_id,
                                  "hosting deployment"))

    def list_hosting_deployments(self, actor=None, deployment_kind=None,
                                 provider_ref=None):
        """Return deployment records. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        if deployment_kind is not None and deployment_kind not in DEPLOYMENT_KINDS:
            raise ValidationError(
                "deployment_kind must be one of %s"
                % (", ".join(DEPLOYMENT_KINDS),))
        with self._lock:
            records = list(self._deployments.values())
            if deployment_kind is not None:
                records = [r for r in records
                           if r["deployment_kind"] == deployment_kind]
            if provider_ref is not None:
                records = [r for r in records
                           if r["provider_ref"] == provider_ref]
            return [dict(r) for r in records]

    # -- Managed delivery reports (verbatim vendor reports) -----------

    def record_delivery_report(self, deployment_id, channel, outcome_label,
                               actor, reported_learner_count=None):
        """Record a managed delivery report — verbatim, labeled.

        Action: catalog_write. ``channel`` is one of the delivered
        platform's access channels. The outcome label is stored
        exactly as the vendor's platform reported it; an optional
        ``reported_learner_count`` is held exactly as reported
        (non-negative integers only — bools, floats, negatives,
        and numeric strings are rejected, no id consumed). Nothing
        is transmitted, fetched, hosted, or delivered here.
        """
        self._require_actor(actor, "catalog_write")
        if channel not in DELIVERY_CHANNELS:
            raise ValidationError(
                "channel must be one of %s"
                % (", ".join(DELIVERY_CHANNELS),))
        _non_empty(outcome_label, "outcome_label")
        if reported_learner_count is not None:
            if (isinstance(reported_learner_count, bool)
                    or not isinstance(reported_learner_count, int)
                    or reported_learner_count < 0):
                raise ValidationError(
                    "reported_learner_count must be a non-negative integer")
        with self._lock:
            self._get(self._deployments, deployment_id, "hosting deployment")
            report_id = self._next_id("dlr")
            record = {
                "id": report_id,
                "deployment_id": deployment_id,
                "channel": channel,
                "outcome_label": outcome_label,
                "reported_learner_count": reported_learner_count,
                "outcome_basis": "vendor_reported",
                "reference_stub": True,
                "reference_transport": True,
                "transmitted_here": False,
                "hosted_here": False,
                "delivered_here": False,
                "state": "recorded_reference_only",
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._delivery_reports[report_id] = record
            self._audit(actor, "extn_delivery_report_record", report_id,
                        details={"deployment_id": deployment_id,
                                 "channel": channel,
                                 "reference_transport": True})
            return dict(record)

    def list_delivery_reports(self, actor=None, deployment_id=None):
        """Return delivery report records. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            records = list(self._delivery_reports.values())
            if deployment_id is not None:
                records = [r for r in records
                           if r["deployment_id"] == deployment_id]
            return [dict(r) for r in records]

    @staticmethod
    def _latest_outcome_label(reports):
        """The latest recorded report's outcome label. Never stored.

        MUTATION DRILL NOTE: this seam is this unit's fresh
        negative control's load-bearing invariant — a view must
        read the LATEST recorded report's label, never the first.
        """
        return reports[-1]["outcome_label"] if reports else None

    def deployment_view(self, deployment_id, actor=None):
        """One deployment plus derived report facts. Action: catalog_read.

        The stored record carries no derived key; the view adds
        ``delivery_report_count`` and ``latest_outcome_label``
        derived at read from the recorded reports, with the
        derivation labeled by ``outcome_method``.
        """
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            record = self._get(self._deployments, deployment_id,
                               "hosting deployment")
            reports = [r for r in self._delivery_reports.values()
                       if r["deployment_id"] == deployment_id]
            view = dict(record)
            view["delivery_report_count"] = len(reports)
            view["latest_outcome_label"] = self._latest_outcome_label(reports)
            view["outcome_method"] = "latest_recorded_vendor_report"
            return view

    # -- Hosting summary (deterministic counts over the records) -------

    def hosting_summary(self, actor):
        """Counts over the recorded reference records. Action: report_read.

        Derived at read: deployment counts by kind, delivery
        report counts, and the latest reported outcome label
        across all recorded reports. Counts of THIS unit's
        records only — no hosting capacity, usage, uptime, or
        learner figure is computed or claimed.
        """
        self._require_actor(actor, "report_read")
        with self._lock:
            by_kind = {kind: 0 for kind in DEPLOYMENT_KINDS}
            for record in self._deployments.values():
                by_kind[record["deployment_kind"]] += 1
            reports = list(self._delivery_reports.values())
            return {
                "method": "deterministic_counts",
                "counts_basis": "recorded_reference_records_only",
                "reference_stub": True,
                "hosted_here": False,
                "deployments": len(self._deployments),
                "deployments_by_kind": by_kind,
                "delivery_reports": len(reports),
                "latest_outcome_label": self._latest_outcome_label(reports),
            }
