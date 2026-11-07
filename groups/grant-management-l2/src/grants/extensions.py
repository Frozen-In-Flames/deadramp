"""Final GAPS batch extensions for the Grant Management L2 singleton.

Clean-room, standard-library-only extensions for the 11 open entries
of Singleton 45 (see ``BATCH.md`` in the group directory for the
per-entry disposition). This module is a wrapper around
:class:`GrantsStore`; every core module is untouched and
byte-identical to the shipped group build.

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — records plus deterministic derivations over the
group's OWN records (core records and extension records).

- The applicant portal is portal-configuration records: branding
  and page/device data held as records, never rendered or served
  (``rendered_here`` / ``served_here`` are False on every record).
- The form designer is form-layout records: section/field placement
  held as data against a registered core form definition, validated
  against that definition's field names, never rendered.
- The document storage engine is vault records: an opaque storage
  reference bound to a core document record (metadata + checksum).
  Content is never held; ``verify_vault_content`` derives a boolean
  match from caller-supplied bytes against the recorded SHA-256 and
  stores nothing.
- Disbursement execution is disbursement RECORDS under a
  disbursement-cap invariant (the recorded disbursements against an
  award never exceed the award's recorded amount, integer cents,
  floats rejected). Recording a disbursement moves no money:
  ``disbursed_here`` / ``paid_here`` are False on every record.
- Reporting beyond registry summaries is dashboard definitions
  whose panels are derivations computed at run time from core
  records (counts and integer-cent sums; no stored results), and
  export records whose manifest counts are derived from core
  records at creation. Nothing is delivered anywhere.
- Delivery transport ships as receipts: every receipt carries
  ``reference_transport: True`` and state
  ``recorded_reference_only``. Nothing is sent, ever.
- Applicant matching is a deterministic presence match: recorded
  match criteria (required form-response field names, held as data)
  are checked against each application's recorded responses; the
  result lists missing fields as evidence. No ranking and no fit
  value is computed.
- Eligibility is a deterministic criteria check: criteria held as
  data, checks evaluated over the application's recorded fields and
  responses, and the determination DERIVED at read — never stored.
  Merit scoring is built in its records form only (DECISION.md
  re-judgment of form, grounds in ``BATCH.md``): scoring-RULE
  records held as data and never applied, plus review-outcome
  records whose outcome text is stored verbatim as reported by an
  external reviewer. This honors the founding doctrine, stated in
  the union spec's core-boundary decisions and pinned by the core's
  tests: nothing is scored in this build, by design, and no record
  shape carries a score field.
- Closeout is a readiness derivation (outstanding core report
  obligations and the presence of a reconciliation, computed at
  read) plus closeout records gated on that readiness. Financial
  reconciliation is records comparing the award's amount, the
  recorded disbursement total, and an externally reported figure,
  with variances derived at read in exact integer cents. No
  automation executes.
- The two stub-engine entries ship as labeled reference
  implementations: workflow-run references copy a core workflow
  definition's steps as data and change no application; signing
  references record an intended signing against a core document
  without signing it. Every such record carries
  ``reference_stub: True`` and state ``recorded_reference_only``.

Doctrines carried from the core: money is integer cents (booleans,
floats, and strings rejected at the boundary); failed operations
consume no id and change nothing; program membership and the role
matrix are enforced through the core store's own access checks,
layered with :mod:`grants.access` role checks for the extension's
actions; every successful extension mutation is recorded on the
core audit log with an ``ext_``-prefixed action, and denied write
attempts are recorded with a ``:denied`` suffix.
"""

import copy
import hashlib
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import APPLICATION_STATUSES

DEVICE_MODES = ("desktop", "tablet", "mobile")
DELIVERY_CHANNELS = ("email", "sms", "push")
DASHBOARD_METRICS = (
    "applications_by_status",
    "applications_total",
    "awards_count",
    "awarded_cents",
    "remaining_cents",
    "reports_by_status",
    "forms_count",
    "workflows_count",
    "notifications_count",
    "messages_count",
)
CRITERION_KINDS = (
    "max_requested_cents",
    "required_response_field",
    "response_field_equals",
    "application_status_in",
)

_REFERENCE_STATE = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _money(value, field, allow_zero=True):
    """Integer cents, mirroring the core store's money discipline."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents" % field)
    if allow_zero and value < 0:
        raise ValidationError("%s must not be negative" % field)
    if not allow_zero and value <= 0:
        raise ValidationError("%s must be positive" % field)
    return value


def _string_list(value, field, allow_empty=False):
    if not isinstance(value, (list, tuple)):
        raise ValidationError("%s must be a list of strings" % field)
    items = list(value)
    if not items and not allow_empty:
        raise ValidationError("%s must be a non-empty list" % field)
    for item in items:
        _text(item, field)
    return items


class GrantsExtensions:
    """Extension surface wrapping one :class:`GrantsStore`."""

    def __init__(self, store):
        self.store = store
        self._portal_configs = {}
        self._form_layouts = {}
        self._vault_records = {}
        self._disbursements = {}
        self._dashboards = {}
        self._exports = {}
        self._deliveries = {}
        self._match_criteria = {}
        self._eligibility_criteria = {}
        self._scoring_rules = {}
        self._review_outcomes = {}
        self._reconciliations = {}
        self._closeouts = {}
        self._workflow_run_refs = {}
        self._signing_refs = {}
        self._counters = {
            "ptl": 0, "fly": 0, "vlt": 0, "dis": 0, "dsh": 0,
            "exp": 0, "dlv": 0, "mtc": 0, "elc": 0, "scr": 0,
            "rvo": 0, "rec": 0, "clo": 0, "wfr": 0, "sgr": 0,
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

        Mirrors the sibling batch units' convention (a User-like
        actor is checked via :func:`grants.access.require`; a plain
        string carries identity but no role). A denied attempt is
        recorded on the audit log with a ``:denied`` suffix before
        the error propagates; a missing actor is denied outright.
        Program membership is enforced separately, through the core
        store's own access-checked reads.
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

    def _program(self, actor, program_id):
        """Core access-checked program read (role + membership)."""
        return self.store.get_program(actor, program_id)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    # -- Applicant portal web application --------------------------------
    # Records form: the portal's branding, page inventory, and device
    # adaptation modes held as configuration data. No page is
    # rendered and nothing is served from this substrate.

    def create_portal_configuration(self, program_id, brand_label, theme,
                                    pages, device_modes, actor):
        """Record a program's portal configuration. Action: record."""
        self._guard(actor, "record", "ext_portal_config_create")
        self._program(actor, program_id)
        _text(brand_label, "brand_label")
        if not isinstance(theme, dict):
            raise ValidationError("theme must be an object of string values")
        for key, value in theme.items():
            _text(key, "theme key")
            _text(value, "theme value")
        if not isinstance(pages, list) or not pages:
            raise ValidationError("pages must be a non-empty list")
        cleaned_pages = []
        seen_pages = set()
        for page in pages:
            if not isinstance(page, dict):
                raise ValidationError("each portal page must be an object")
            name = _text(page.get("name"), "page name")
            title = _text(page.get("title"), "page title")
            if name in seen_pages:
                raise ValidationError("duplicate portal page name: %r" % (name,))
            seen_pages.add(name)
            cleaned_pages.append({"name": name, "title": title})
        modes = _string_list(device_modes, "device_modes")
        for mode in modes:
            if mode not in DEVICE_MODES:
                raise ValidationError("unknown device mode: %r" % (mode,))
        with self._lock:
            for existing in self._portal_configs.values():
                if existing["program_id"] == program_id:
                    raise ValidationError(
                        "program %r already has a portal configuration"
                        % (program_id,))
            record = {
                "id": self._next_id("ptl"),
                "program_id": program_id,
                "brand_label": brand_label,
                "theme": dict(theme),
                "pages": cleaned_pages,
                "device_modes": modes,
                "rendered_here": False,
                "served_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._portal_configs[record["id"]] = record
        self._audit(actor, "ext_portal_config_create", record["id"],
                    {"program_id": program_id})
        return copy.deepcopy(record)

    def get_portal_configuration(self, actor, program_id):
        """The program's portal configuration record. Action: read."""
        self._maybe_require(actor, "read")
        self._program(actor, program_id)
        for record in self._portal_configs.values():
            if record["program_id"] == program_id:
                return copy.deepcopy(record)
        raise NotFoundError(
            "no portal configuration for program: %r" % (program_id,))

    # -- Form designer & form rendering engine ---------------------------
    # Records form: a layout is section/field placement data bound to
    # a registered core form definition. Placement is validated
    # against the definition's own field names — a deterministic
    # check over core records. Nothing is rendered.

    def create_form_layout(self, form_id, sections, actor):
        """Record a layout for a core form definition. Action: record."""
        self._guard(actor, "record", "ext_form_layout_create")
        form = self.store.get_form(actor, form_id)
        known_fields = [f["name"] for f in form["fields"]]
        if not isinstance(sections, list) or not sections:
            raise ValidationError("sections must be a non-empty list")
        cleaned = []
        placed = set()
        for section in sections:
            if not isinstance(section, dict):
                raise ValidationError("each layout section must be an object")
            title = _text(section.get("title"), "section title")
            field_names = _string_list(section.get("field_names"),
                                       "section field_names")
            for fname in field_names:
                if fname not in known_fields:
                    raise ValidationError(
                        "layout field %r is not a field of form %r"
                        % (fname, form_id))
                if fname in placed:
                    raise ValidationError(
                        "field %r is placed more than once" % (fname,))
                placed.add(fname)
            cleaned.append({"title": title, "field_names": field_names})
        with self._lock:
            record = {
                "id": self._next_id("fly"),
                "form_id": form_id,
                "program_id": form["program_id"],
                "sections": cleaned,
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._form_layouts[record["id"]] = record
        self._audit(actor, "ext_form_layout_create", record["id"],
                    {"form_id": form_id})
        return copy.deepcopy(record)

    def get_form_layout(self, actor, layout_id):
        """One form-layout record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._form_layouts, layout_id, "form layout")
        self._program(actor, record["program_id"])
        return copy.deepcopy(record)

    def list_form_layouts(self, actor, form_id):
        """Layouts recorded against a core form. Action: read."""
        self._maybe_require(actor, "read")
        form = self.store.get_form(actor, form_id)
        return [copy.deepcopy(r) for r in self._form_layouts.values()
                if r["form_id"] == form["id"]]

    # -- Document storage & content management engine --------------------
    # Records form: a vault record binds an opaque storage reference
    # to a core document record. The core holds metadata + checksum
    # only, and so does this surface — content is never held.

    def create_vault_record(self, document_id, storage_ref, actor,
                            retention_label=None):
        """Record where a document's content is held. Action: record."""
        self._guard(actor, "record", "ext_vault_record_create")
        document = self.store.get_document(actor, document_id)
        _text(storage_ref, "storage_ref")
        if retention_label is not None:
            _text(retention_label, "retention_label")
        with self._lock:
            record = {
                "id": self._next_id("vlt"),
                "document_id": document_id,
                "program_id": document["program_id"],
                "storage_ref": storage_ref,
                "retention_label": retention_label,
                "content_held": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._vault_records[record["id"]] = record
        self._audit(actor, "ext_vault_record_create", record["id"],
                    {"document_id": document_id})
        return copy.deepcopy(record)

    def get_vault_record(self, actor, vault_id):
        """One vault record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._vault_records, vault_id, "vault record")
        self._program(actor, record["program_id"])
        return copy.deepcopy(record)

    def list_vault_records(self, actor, document_id):
        """Vault records bound to a core document. Action: read."""
        self._maybe_require(actor, "read")
        document = self.store.get_document(actor, document_id)
        return [copy.deepcopy(r) for r in self._vault_records.values()
                if r["document_id"] == document["id"]]

    def verify_vault_content(self, actor, vault_id, content):
        """Verify caller-supplied bytes against the recorded checksum.

        A derivation, not a record: the SHA-256 of ``content`` is
        compared with the core document's recorded checksum and only
        the boolean outcome is returned. The content itself is never
        stored. Action: read.
        """
        self._maybe_require(actor, "read")
        record = self._get(self._vault_records, vault_id, "vault record")
        document = self.store.get_document(actor, record["document_id"])
        if not isinstance(content, (bytes, bytearray)):
            raise ValidationError("content must be bytes")
        digest = hashlib.sha256(bytes(content)).hexdigest()
        return {
            "vault_id": vault_id,
            "document_id": record["document_id"],
            "matches": digest == document["sha256"],
            "method": "sha256_verify_by_content",
            "content_stored": False,
        }

    # -- Payment / disbursement execution for awards ---------------------
    # Records form: a disbursement record is a record of an intended
    # or reported disbursement against an award. The disbursement
    # cap (below) keeps the recorded total within the award's
    # recorded amount; recording one moves no money.

    def _check_disbursement_cap(self, award, amount_cents):
        """Disbursement-cap invariant seam: the disbursements
        recorded against an award never exceed the award's recorded
        amount. Checked before anything is stored, so a rejected
        disbursement consumes no id and changes nothing. This seam
        is the mutation target of the batch's fresh negative control
        (see tests/README.md)."""
        disbursed = sum(
            d["amount_cents"] for d in self._disbursements.values()
            if d["award_id"] == award["id"]
        )
        if disbursed + amount_cents > award["amount_cents"]:
            raise ValidationError(
                "disbursement of %d cents would exceed the award amount: "
                "%d already recorded of %d"
                % (amount_cents, disbursed, award["amount_cents"])
            )

    def record_disbursement(self, award_id, amount_cents, actor,
                            payee_ref=None, note=""):
        """Record a disbursement against an award. Action: record."""
        self._guard(actor, "record", "ext_disbursement_create")
        award = self.store.get_award(actor, award_id)
        _money(amount_cents, "amount_cents", allow_zero=False)
        if payee_ref is not None:
            _text(payee_ref, "payee_ref")
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            self._check_disbursement_cap(award, amount_cents)
            record = {
                "id": self._next_id("dis"),
                "award_id": award_id,
                "program_id": award["program_id"],
                "amount_cents": amount_cents,
                "payee_ref": payee_ref,
                "note": note,
                "disbursed_here": False,
                "paid_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._disbursements[record["id"]] = record
        self._audit(actor, "ext_disbursement_create", record["id"],
                    {"award_id": award_id, "amount_cents": amount_cents})
        return copy.deepcopy(record)

    def get_disbursement(self, actor, disbursement_id):
        """One disbursement record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._disbursements, disbursement_id,
                           "disbursement")
        self._program(actor, record["program_id"])
        return copy.deepcopy(record)

    def list_disbursements(self, actor, award_id):
        """Disbursement records against an award. Action: read."""
        self._maybe_require(actor, "read")
        award = self.store.get_award(actor, award_id)
        return [copy.deepcopy(d) for d in self._disbursements.values()
                if d["award_id"] == award["id"]]

    def disbursement_summary(self, actor, award_id):
        """Recorded disbursement totals for an award, derived at
        read — the totals are never stored on the award or anywhere
        else. Action: read."""
        self._maybe_require(actor, "read")
        award = self.store.get_award(actor, award_id)
        records = [d for d in self._disbursements.values()
                   if d["award_id"] == award_id]
        disbursed = sum(d["amount_cents"] for d in records)
        return {
            "award_id": award_id,
            "award_cents": award["amount_cents"],
            "disbursed_cents": disbursed,
            "remaining_cents": award["amount_cents"] - disbursed,
            "disbursements": len(records),
            "method": "deterministic_sums",
        }

    # -- Reporting & analytics engines beyond registry summaries ---------
    # Dashboard definitions are records; running one derives every
    # panel value from core records at run time and stores nothing.
    # Export records carry a manifest of record counts derived from
    # core records at creation; no data is delivered anywhere.

    def create_dashboard(self, program_id, name, panels, actor):
        """Register a dashboard definition as data. Action: record."""
        self._guard(actor, "record", "ext_dashboard_create")
        self._program(actor, program_id)
        _text(name, "name")
        if not isinstance(panels, list) or not panels:
            raise ValidationError("panels must be a non-empty list")
        cleaned = []
        for panel in panels:
            if not isinstance(panel, dict):
                raise ValidationError("each dashboard panel must be an object")
            title = _text(panel.get("title"), "panel title")
            metric = panel.get("metric")
            if metric not in DASHBOARD_METRICS:
                raise ValidationError("unknown dashboard metric: %r" % (metric,))
            cleaned.append({"title": title, "metric": metric})
        with self._lock:
            record = {
                "id": self._next_id("dsh"),
                "program_id": program_id,
                "name": name,
                "panels": cleaned,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._dashboards[record["id"]] = record
        self._audit(actor, "ext_dashboard_create", record["id"],
                    {"program_id": program_id})
        return copy.deepcopy(record)

    def get_dashboard(self, actor, dashboard_id):
        """One dashboard definition record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._dashboards, dashboard_id, "dashboard")
        self._program(actor, record["program_id"])
        return copy.deepcopy(record)

    def _dashboard_metric_value(self, actor, program_id, metric, now):
        summary = self.store.program_summary(actor, program_id, now=now)
        if metric == "applications_by_status":
            return dict(summary["applications_by_status"])
        if metric == "applications_total":
            return sum(summary["applications_by_status"].values())
        if metric == "awards_count":
            return summary["awards"]
        if metric == "awarded_cents":
            return summary["awarded_cents"]
        if metric == "remaining_cents":
            return summary["remaining_cents"]
        if metric == "reports_by_status":
            return dict(summary["reports_by_status"])
        if metric == "forms_count":
            return len(self.store.list_forms(actor, program_id))
        if metric == "workflows_count":
            return len(self.store.list_workflows(actor, program_id))
        if metric == "notifications_count":
            return len(self.store.list_notifications(actor, program_id))
        if metric == "messages_count":
            return len(self.store.list_messages(actor, program_id))
        raise ValidationError("unknown dashboard metric: %r" % (metric,))

    def run_dashboard(self, actor, dashboard_id, now=None):
        """Derive a dashboard's panel values from core records.

        A derivation, not a record: nothing is stored, and running
        the same dashboard twice over unchanged records returns the
        same values. Action: read.
        """
        self._maybe_require(actor, "read")
        record = self._get(self._dashboards, dashboard_id, "dashboard")
        self._program(actor, record["program_id"])
        panels = []
        for panel in record["panels"]:
            panels.append({
                "title": panel["title"],
                "metric": panel["metric"],
                "value": self._dashboard_metric_value(
                    actor, record["program_id"], panel["metric"], now),
            })
        return {
            "dashboard_id": dashboard_id,
            "program_id": record["program_id"],
            "method": "deterministic_counts",
            "panels": panels,
        }

    def create_export_record(self, program_id, kind_label, actor):
        """Record an export with a manifest derived from core
        records at creation. The manifest is counts only; no record
        content is exported or delivered. Action: record."""
        self._guard(actor, "record", "ext_export_create")
        self._program(actor, program_id)
        _text(kind_label, "kind_label")
        applications = self.store.list_applications(actor, program_id)
        awards = self.store.list_awards(actor, program_id)
        documents = list(self.store.list_documents(
            actor, "program", program_id))
        for app in applications:
            documents.extend(self.store.list_documents(
                actor, "application", app["id"]))
        reports = 0
        for award in awards:
            documents.extend(self.store.list_documents(
                actor, "award", award["id"]))
            reports += len(self.store.list_reports(actor, award["id"]))
        manifest = {
            "applications": len(applications),
            "awards": len(awards),
            "reports": reports,
            "documents": len(documents),
            "forms": len(self.store.list_forms(actor, program_id)),
            "workflows": len(self.store.list_workflows(actor, program_id)),
            "notifications": len(self.store.list_notifications(
                actor, program_id)),
            "messages": len(self.store.list_messages(actor, program_id)),
        }
        with self._lock:
            record = {
                "id": self._next_id("exp"),
                "program_id": program_id,
                "kind_label": kind_label,
                "manifest": manifest,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._exports[record["id"]] = record
        self._audit(actor, "ext_export_create", record["id"],
                    {"program_id": program_id})
        return copy.deepcopy(record)

    def get_export_record(self, actor, export_id):
        """One export record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._exports, export_id, "export record")
        self._program(actor, record["program_id"])
        return copy.deepcopy(record)

    def list_export_records(self, actor, program_id):
        """Export records for a program. Action: read."""
        self._maybe_require(actor, "read")
        self._program(actor, program_id)
        return [copy.deepcopy(r) for r in self._exports.values()
                if r["program_id"] == program_id]

    # -- Notification & message delivery transport -----------------------
    # Records form: a delivery receipt binds a channel to a core
    # notification record. The receipt is the whole surface — the
    # transport is a labeled reference and nothing is delivered.

    def record_delivery(self, program_id, notification_id, channel, actor):
        """Record a delivery receipt for a notification. Action: record."""
        self._guard(actor, "record", "ext_delivery_create")
        self._program(actor, program_id)
        if channel not in DELIVERY_CHANNELS:
            raise ValidationError("unknown delivery channel: %r" % (channel,))
        known = {n["id"] for n in
                 self.store.list_notifications(actor, program_id)}
        if notification_id not in known:
            raise NotFoundError(
                "no such notification in this program: %r" % (notification_id,))
        with self._lock:
            record = {
                "id": self._next_id("dlv"),
                "program_id": program_id,
                "notification_id": notification_id,
                "channel": channel,
                "reference_transport": True,
                "state": _REFERENCE_STATE,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._deliveries[record["id"]] = record
        self._audit(actor, "ext_delivery_create", record["id"],
                    {"notification_id": notification_id, "channel": channel})
        return copy.deepcopy(record)

    def list_deliveries(self, actor, program_id):
        """Delivery receipts for a program. Action: read."""
        self._maybe_require(actor, "read")
        self._program(actor, program_id)
        return [copy.deepcopy(r) for r in self._deliveries.values()
                if r["program_id"] == program_id]

    # -- Applicant matching & opportunity recommendation -----------------
    # A deterministic presence match: the criteria (required
    # form-response field names) are held as data, and each
    # application in the program is checked for the presence of
    # those fields in its recorded responses. The result is evidence
    # per application — matched or the missing fields — in
    # application order. Nothing is ranked and no fit value exists.

    def create_match_criteria(self, program_id, required_response_fields,
                              actor):
        """Record match criteria for a program. Action: record."""
        self._guard(actor, "record", "ext_match_criteria_create")
        self._program(actor, program_id)
        fields = _string_list(required_response_fields,
                              "required_response_fields")
        if len(set(fields)) != len(fields):
            raise ValidationError("required_response_fields must be unique")
        with self._lock:
            record = {
                "id": self._next_id("mtc"),
                "program_id": program_id,
                "required_response_fields": fields,
                "method": "deterministic_presence_match",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._match_criteria[record["id"]] = record
        self._audit(actor, "ext_match_criteria_create", record["id"],
                    {"program_id": program_id})
        return copy.deepcopy(record)

    def get_match_criteria(self, actor, criteria_id):
        """One match-criteria record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._match_criteria, criteria_id,
                           "match criteria")
        self._program(actor, record["program_id"])
        return copy.deepcopy(record)

    def evaluate_matches(self, actor, criteria_id):
        """Derive presence matches for a program's applications.

        A derivation, not a record: for each application in the
        criteria's program (in creation order), whether every
        required field is present in the application's recorded
        form responses, with the missing fields listed as evidence.
        Action: read.
        """
        self._maybe_require(actor, "read")
        criteria = self._get(self._match_criteria, criteria_id,
                             "match criteria")
        self._program(actor, criteria["program_id"])
        required = criteria["required_response_fields"]
        matches = []
        for app in self.store.list_applications(actor,
                                                criteria["program_id"]):
            responses = app.get("responses") or {}
            missing = [f for f in required if f not in responses]
            matches.append({
                "application_id": app["id"],
                "org_id": app["org_id"],
                "matched": not missing,
                "missing_fields": missing,
            })
        return {
            "criteria_id": criteria_id,
            "program_id": criteria["program_id"],
            "method": "deterministic_presence_match",
            "matches": matches,
        }

    # -- Eligibility determination & merit-scoring engines ---------------
    # Eligibility: criteria held as data; the determination is a
    # deterministic check over the application's recorded fields,
    # derived at read and never stored. Merit scoring: records form
    # only — scoring rules held as data and never applied, and
    # review outcomes recorded verbatim as reported. Nothing in
    # either surface computes or stores a score (see BATCH.md).

    @staticmethod
    def _clean_criterion(criterion):
        if not isinstance(criterion, dict):
            raise ValidationError("each eligibility criterion must be an object")
        kind = criterion.get("kind")
        if kind not in CRITERION_KINDS:
            raise ValidationError("unknown eligibility criterion kind: %r" % (kind,))
        if kind == "max_requested_cents":
            value = _money(criterion.get("value_cents"), "value_cents",
                           allow_zero=False)
            return {"kind": kind, "value_cents": value}
        if kind == "required_response_field":
            return {"kind": kind,
                    "field": _text(criterion.get("field"), "field")}
        if kind == "response_field_equals":
            field = _text(criterion.get("field"), "field")
            value = criterion.get("value")
            if not isinstance(value, str):
                raise ValidationError("criterion value must be a string")
            return {"kind": kind, "field": field, "value": value}
        statuses = _string_list(criterion.get("statuses"), "statuses")
        for status in statuses:
            if status not in APPLICATION_STATUSES:
                raise ValidationError("unknown application status: %r" % (status,))
        return {"kind": kind, "statuses": statuses}

    def create_eligibility_criteria(self, program_id, criteria, actor):
        """Record eligibility criteria for a program. Action: record."""
        self._guard(actor, "record", "ext_eligibility_criteria_create")
        self._program(actor, program_id)
        if not isinstance(criteria, list) or not criteria:
            raise ValidationError("criteria must be a non-empty list")
        cleaned = [self._clean_criterion(c) for c in criteria]
        with self._lock:
            record = {
                "id": self._next_id("elc"),
                "program_id": program_id,
                "criteria": cleaned,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._eligibility_criteria[record["id"]] = record
        self._audit(actor, "ext_eligibility_criteria_create", record["id"],
                    {"program_id": program_id})
        return copy.deepcopy(record)

    def get_eligibility_criteria(self, actor, criteria_id):
        """One eligibility-criteria record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._eligibility_criteria, criteria_id,
                           "eligibility criteria")
        self._program(actor, record["program_id"])
        return copy.deepcopy(record)

    def list_eligibility_criteria(self, actor, program_id):
        """Eligibility criteria recorded for a program. Action: read."""
        self._maybe_require(actor, "read")
        self._program(actor, program_id)
        return [copy.deepcopy(r) for r in self._eligibility_criteria.values()
                if r["program_id"] == program_id]

    @staticmethod
    def _criterion_satisfied(criterion, app):
        kind = criterion["kind"]
        if kind == "max_requested_cents":
            return app["requested_cents"] <= criterion["value_cents"]
        responses = app.get("responses") or {}
        if kind == "required_response_field":
            return criterion["field"] in responses
        if kind == "response_field_equals":
            return responses.get(criterion["field"]) == criterion["value"]
        return app["status"] in criterion["statuses"]

    def evaluate_eligibility(self, actor, application_id, criteria_id=None):
        """Derive an eligibility determination for an application.

        A derivation, not a record: each recorded criterion is
        checked against the application's recorded fields and the
        per-criterion outcomes are returned with the determination.
        Nothing is stored — evaluating twice over unchanged records
        returns the same result, and no determination record exists
        to read back. With ``criteria_id`` omitted, the most recent
        criteria recorded for the application's program are used.
        Action: read.
        """
        self._maybe_require(actor, "read")
        app = self.store.get_application(actor, application_id)
        if criteria_id is None:
            recorded = [r for r in self._eligibility_criteria.values()
                        if r["program_id"] == app["program_id"]]
            if not recorded:
                raise NotFoundError(
                    "no eligibility criteria recorded for program: %r"
                    % (app["program_id"],))
            criteria = recorded[-1]
        else:
            criteria = self._get(self._eligibility_criteria, criteria_id,
                                 "eligibility criteria")
            if criteria["program_id"] != app["program_id"]:
                raise ValidationError(
                    "criteria %r belong to a different program" % (criteria_id,))
        checks = []
        for criterion in criteria["criteria"]:
            checks.append({
                "criterion": copy.deepcopy(criterion),
                "satisfied": self._criterion_satisfied(criterion, app),
            })
        return {
            "application_id": application_id,
            "criteria_id": criteria["id"],
            "checks": checks,
            "eligible": all(c["satisfied"] for c in checks),
            "method": "deterministic_criteria_check",
            "stored": False,
        }

    def create_scoring_rule(self, program_id, rule_text, actor):
        """Record a merit-scoring rule as data. The rule is held,
        never applied — no record in this build is scored.
        Action: record."""
        self._guard(actor, "record", "ext_scoring_rule_create")
        self._program(actor, program_id)
        _text(rule_text, "rule_text")
        with self._lock:
            record = {
                "id": self._next_id("scr"),
                "program_id": program_id,
                "rule_text": rule_text,
                "method": "recorded_rules_only",
                "applied_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._scoring_rules[record["id"]] = record
        self._audit(actor, "ext_scoring_rule_create", record["id"],
                    {"program_id": program_id})
        return copy.deepcopy(record)

    def list_scoring_rules(self, actor, program_id):
        """Scoring-rule records for a program. Action: read."""
        self._maybe_require(actor, "read")
        self._program(actor, program_id)
        return [copy.deepcopy(r) for r in self._scoring_rules.values()
                if r["program_id"] == program_id]

    def record_review_outcome(self, application_id, outcome_text, actor,
                              reported_by_ref=None):
        """Record a review outcome verbatim, as reported by an
        external reviewer. The outcome is reported data; nothing is
        computed from it and the core application record is not
        modified. Action: record."""
        self._guard(actor, "record", "ext_review_outcome_create")
        app = self.store.get_application(actor, application_id)
        _text(outcome_text, "outcome_text")
        if reported_by_ref is not None:
            _text(reported_by_ref, "reported_by_ref")
        with self._lock:
            record = {
                "id": self._next_id("rvo"),
                "application_id": application_id,
                "program_id": app["program_id"],
                "outcome_text": outcome_text,
                "reported_by_ref": reported_by_ref,
                "computed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._review_outcomes[record["id"]] = record
        self._audit(actor, "ext_review_outcome_create", record["id"],
                    {"application_id": application_id})
        return copy.deepcopy(record)

    def list_review_outcomes(self, actor, application_id):
        """Reported review outcomes for an application. Action: read."""
        self._maybe_require(actor, "read")
        app = self.store.get_application(actor, application_id)
        return [copy.deepcopy(r) for r in self._review_outcomes.values()
                if r["application_id"] == app["id"]]

    # -- Closeout automation & financial reconciliation engines ----------
    # Reconciliation records hold the externally reported figure;
    # every comparison value is derived at read in exact integer
    # cents. Closeout readiness is a derivation over core records;
    # a closeout record is gated on it and executes nothing.

    def create_reconciliation(self, award_id, reported_disbursed_cents,
                              actor, note=""):
        """Record a reconciliation against an award. Action: record."""
        self._guard(actor, "record", "ext_reconciliation_create")
        award = self.store.get_award(actor, award_id)
        _money(reported_disbursed_cents, "reported_disbursed_cents")
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            record = {
                "id": self._next_id("rec"),
                "award_id": award_id,
                "program_id": award["program_id"],
                "reported_disbursed_cents": reported_disbursed_cents,
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._reconciliations[record["id"]] = record
        self._audit(actor, "ext_reconciliation_create", record["id"],
                    {"award_id": award_id})
        return self._reconciliation_view(actor, record)

    def _reconciliation_view(self, actor, record):
        award = self.store.get_award(actor, record["award_id"])
        recorded = sum(d["amount_cents"] for d in self._disbursements.values()
                       if d["award_id"] == record["award_id"])
        view = copy.deepcopy(record)
        view["award_cents"] = award["amount_cents"]
        view["recorded_disbursed_cents"] = recorded
        view["remaining_vs_award_cents"] = award["amount_cents"] - recorded
        view["variance_vs_reported_cents"] = (
            record["reported_disbursed_cents"] - recorded)
        view["method"] = "deterministic_reconciliation"
        return view

    def get_reconciliation(self, actor, reconciliation_id):
        """One reconciliation, with derived comparisons. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._reconciliations, reconciliation_id,
                           "reconciliation")
        self._program(actor, record["program_id"])
        return self._reconciliation_view(actor, record)

    def list_reconciliations(self, actor, award_id):
        """Reconciliations recorded against an award. Action: read."""
        self._maybe_require(actor, "read")
        award = self.store.get_award(actor, award_id)
        return [self._reconciliation_view(actor, r)
                for r in self._reconciliations.values()
                if r["award_id"] == award["id"]]

    def closeout_readiness(self, actor, award_id, now=None):
        """Derive whether an award's closeout preconditions hold:
        every core post-award report obligation submitted, and at
        least one reconciliation recorded. A derivation, not a
        record. Action: read."""
        self._maybe_require(actor, "read")
        award = self.store.get_award(actor, award_id)
        reports = self.store.list_reports(actor, award_id, now=now)
        outstanding = [r for r in reports if r["status"] != "submitted"]
        reconciliations = [r for r in self._reconciliations.values()
                           if r["award_id"] == award_id]
        blockers = []
        if outstanding:
            blockers.append("reports_outstanding:%d" % len(outstanding))
        if not reconciliations:
            blockers.append("reconciliation_missing")
        disbursed = sum(d["amount_cents"] for d in self._disbursements.values()
                        if d["award_id"] == award_id)
        return {
            "award_id": award_id,
            "reports_total": len(reports),
            "reports_submitted": len(reports) - len(outstanding),
            "reports_outstanding": len(outstanding),
            "reconciliations": len(reconciliations),
            "award_cents": award["amount_cents"],
            "disbursed_cents": disbursed,
            "ready": not blockers,
            "blockers": blockers,
            "method": "deterministic_counts",
        }

    def record_closeout(self, award_id, actor, note=""):
        """Record a closeout for an award whose derived readiness
        holds. The record executes nothing. Action: record."""
        self._guard(actor, "record", "ext_closeout_create")
        award = self.store.get_award(actor, award_id)
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        readiness = self.closeout_readiness(actor, award_id)
        with self._lock:
            if not readiness["ready"]:
                raise ValidationError(
                    "award %r is not ready for closeout: %s"
                    % (award_id, ", ".join(readiness["blockers"])))
            for existing in self._closeouts.values():
                if existing["award_id"] == award_id:
                    raise ValidationError(
                        "award %r already has a closeout record" % (award_id,))
            record = {
                "id": self._next_id("clo"),
                "award_id": award_id,
                "program_id": award["program_id"],
                "note": note,
                "state": "recorded_only",
                "executed_here": False,
                "automation_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._closeouts[record["id"]] = record
        self._audit(actor, "ext_closeout_create", record["id"],
                    {"award_id": award_id})
        return copy.deepcopy(record)

    def list_closeouts(self, actor, award_id):
        """Closeout records against an award. Action: read."""
        self._maybe_require(actor, "read")
        award = self.store.get_award(actor, award_id)
        return [copy.deepcopy(r) for r in self._closeouts.values()
                if r["award_id"] == award["id"]]

    # -- Workflow execution engine (stub-engine) --------------------------
    # Labeled reference implementation: a run reference copies the
    # core workflow definition's steps as data. Registering one
    # changes no application and executes no step.

    def create_workflow_run_reference(self, workflow_id, actor):
        """Record a reference run of a workflow definition.
        Action: record."""
        self._guard(actor, "record", "ext_workflow_run_reference_create")
        workflow = self.store.get_workflow(actor, workflow_id)
        with self._lock:
            record = {
                "id": self._next_id("wfr"),
                "workflow_id": workflow_id,
                "program_id": workflow["program_id"],
                "steps": list(workflow["steps"]),
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workflow_run_refs[record["id"]] = record
        self._audit(actor, "ext_workflow_run_reference_create", record["id"],
                    {"workflow_id": workflow_id})
        return copy.deepcopy(record)

    def list_workflow_run_references(self, actor, workflow_id):
        """Run references recorded against a workflow. Action: read."""
        self._maybe_require(actor, "read")
        workflow = self.store.get_workflow(actor, workflow_id)
        return [copy.deepcopy(r) for r in self._workflow_run_refs.values()
                if r["workflow_id"] == workflow["id"]]

    # -- E-signature signing engine (stub-engine) -------------------------
    # Labeled reference implementation: a signing reference records
    # an intended signing against a core document. The ceremony and
    # its cryptographic binding are not here; the core document is
    # NOT signed by recording one (its signature event stays a core
    # record, made through the core's own operation).

    def create_signing_reference(self, document_id, actor, signer_ref=None):
        """Record a reference signing intent for a document.
        Action: record."""
        self._guard(actor, "record", "ext_signing_reference_create")
        document = self.store.get_document(actor, document_id)
        if signer_ref is not None:
            _text(signer_ref, "signer_ref")
        with self._lock:
            record = {
                "id": self._next_id("sgr"),
                "document_id": document_id,
                "program_id": document["program_id"],
                "signer_ref": signer_ref,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "ceremony_here": False,
                "cryptographic_binding": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._signing_refs[record["id"]] = record
        self._audit(actor, "ext_signing_reference_create", record["id"],
                    {"document_id": document_id})
        return copy.deepcopy(record)

    def list_signing_references(self, actor, document_id):
        """Signing references recorded against a document. Action: read."""
        self._maybe_require(actor, "read")
        document = self.store.get_document(actor, document_id)
        return [copy.deepcopy(r) for r in self._signing_refs.values()
                if r["document_id"] == document["id"]]
