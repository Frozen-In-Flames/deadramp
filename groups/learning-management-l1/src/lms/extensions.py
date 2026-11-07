"""Final GAPS batch extensions for the Learning Management L1 build.

Clean-room, standard-library-only extensions for the 6 open Extended
entries of Remainder Group 2 (see ``BATCH.md`` in the group directory
for the per-entry disposition). This module is a wrapper around
:class:`LmsStore`; every core module is untouched.

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — records plus deterministic derivations over the
group's OWN records.

- The branded portal engine is presentation DATA bound to the core
  organization registry: brand label, theme, and menu labels held as
  records, with the current presentation DERIVED at read from the
  append-only revision list. Nothing is rendered or served
  (``rendered_here: False`` on every view); the core's portal label
  and visibility rule stay exactly as shipped.
- The continuing-education engine is renewal-cycle records over the
  core CE records: cycle status (``satisfied`` / ``open`` /
  ``lapsed``) is DERIVED at read from the core records whose
  activity falls in the cycle period. Credit text stays verbatim
  end to end — never parsed, summed, or converted — so there is no
  credit accounting here beyond presence of records, exactly the
  boundary the core drew.
- The certificate service is issuance and verification-query records
  bound to core award records: an issuance record is a record OF an
  issuance act (``issued_here: False``), and a verification query
  records a caller-reported outcome verbatim
  (``verified_here: False``). The core award record is never
  modified by this surface.
- The authoring environment, the course posting workflow, and the
  system integration engines execute against systems outside this
  substrate (an authoring workspace, catalogs and portals, external
  systems), so they ship as labeled reference records:
  ``reference_stub: True``, state ``recorded_reference_only``.
  Nothing is authored, posted, published, transmitted, or synced.

Doctrines carried from the core: opaque ``*_ref`` strings only;
derived-never-stored for every computed value (portal current
presentation, CE cycle status and coverage, certificate service
counts); append-only audit on the core store's log with
``ext_``-prefixed actions for every successful mutation; RBAC via
:mod:`lms.access` with the core's existing actions, enforced before
any state change or id allocation, so a failed operation consumes
no id and changes nothing; learner scope mirrors the store's — a
learner-role actor may only read views whose ``learner_ref`` is
their own name.

No score or grade field appears anywhere in this surface: no key
here is named ``score`` / ``score_*`` / ``*_score`` or carries
``grade``, pinned by a recursive key scan in the tests — the
founding no-score invariant binds the extension exactly as it binds
the core. Credit text is read only as verbatim strings, never
interpreted.
"""

import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

AUTHORING_MODES = ("individual", "collaborative")
AUTHORING_CHECK_KINDS = ("section_508", "theme_and_menus", "plugin_review")
PUBLICATION_CHANNELS = (
    "community_catalog", "organization_portal", "external_link",
)
ISSUANCE_CHANNELS = ("portal", "email", "print", "registry_link")
INTEGRATION_DIRECTIONS = ("inbound", "outbound", "bidirectional")
REFERENCE_STATE = "recorded_reference_only"


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
        raise ValidationError(
            "%s must be an ISO date string (YYYY-MM-DD)" % (what,))
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationError(
            "%s is not a valid ISO date: %r" % (what, value)) from exc


def _coerce_as_of(as_of):
    if as_of is None:
        return date.today()
    if isinstance(as_of, datetime):
        return as_of.date()
    if isinstance(as_of, date):
        return as_of
    if isinstance(as_of, str):
        return _validate_date(as_of, "as_of")
    raise ValidationError("as_of must be an ISO date string or date")


class LmsExtensions:
    """Extension surface wrapping one :class:`LmsStore`."""

    def __init__(self, store):
        self.store = store
        self._authoring_drafts = {}
        self._authoring_sessions = {}
        self._authoring_checks = {}
        self._publication_records = {}
        self._portal_presentations = {}
        self._ce_cycles = {}
        self._issuance_records = {}
        self._verification_queries = {}
        self._integration_records = {}
        self._sync_reports = {}
        self._counters = {
            "dft": 0, "asx": 0, "ack": 0, "pub": 0, "ppr": 0,
            "crc": 0, "iss": 0, "vfy": 0, "int": 0, "syn": 0,
        }
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

    @staticmethod
    def _scope_check(actor, learner_ref):
        if (actor is not None and getattr(actor, "role", None) == "learner"
                and getattr(actor, "name", None) != learner_ref):
            raise PermissionDenied(
                "permission denied: learner %r may not access records of "
                "learner %r" % (getattr(actor, "name", None), learner_ref)
            )

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _require_learner(self, learner_ref):
        learners = self.store.list_learners()
        if learner_ref not in {l["ref"] for l in learners}:
            raise NotFoundError("learner not found: %r" % (learner_ref,))

    def _require_org(self, org_ref):
        organizations = self.store.list_organizations(actor=None)
        if org_ref not in {o["ref"] for o in organizations}:
            raise NotFoundError("organization not found: %r" % (org_ref,))

    # -- Learning content authoring environment (reference) -----------
    # The authoring workspace itself — rapid/collaborative editing,
    # theme and menu tooling, the plugin runtime, and the renderer
    # that would emit 508-conformant output — executes outside this
    # substrate. What the substrate honestly holds is records ABOUT
    # authoring: draft records bound to core catalog records,
    # session records, and caller-reported check outcomes. Every
    # record is a labeled reference; no content is authored here.

    def create_authoring_draft(self, title, actor, course_id=None,
                               content_item_id=None, linked_external_ref=None):
        """Record an authoring draft. Action: catalog_write.

        Stub-engine entry (idx 633): the record carries
        ``reference_stub: True``; the draft's content is never held.
        """
        self._require_actor(actor, "catalog_write")
        _non_empty(title, "authoring draft title")
        if linked_external_ref is not None:
            _string(linked_external_ref, "linked_external_ref")
        with self._lock:
            if course_id is not None:
                self.store.get_course(course_id, actor=None)
            if content_item_id is not None:
                item = self.store.get_content_item(content_item_id, actor=None)
                if (course_id is not None and item["course_id"] is not None
                        and item["course_id"] != course_id):
                    raise ValidationError(
                        "content item %r does not belong to course %r"
                        % (content_item_id, course_id))
            draft_id = self._next_id("dft")
            record = {
                "id": draft_id,
                "title": title,
                "course_id": course_id,
                "content_item_id": content_item_id,
                "linked_external_ref": linked_external_ref,
                "working_state": REFERENCE_STATE,
                "reference_stub": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._authoring_drafts[draft_id] = record
            self._audit(actor, "ext_authoring_draft_create", draft_id,
                        details={"title": title, "course_id": course_id})
            return dict(record)

    def get_authoring_draft(self, draft_id, actor=None):
        """Return one authoring draft record. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            return dict(self._get(self._authoring_drafts, draft_id,
                                  "authoring draft"))

    def list_authoring_drafts(self, actor=None, course_id=None):
        """Return authoring draft records. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            records = list(self._authoring_drafts.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            return [dict(r) for r in records]

    def record_authoring_session(self, draft_id, actor, mode, note=""):
        """Record an authoring session against a draft.

        Action: catalog_write. ``mode`` is ``individual`` or
        ``collaborative`` (CloudLCMS's own distinction); the session
        is a record of work in the external workspace, not the work.
        """
        self._require_actor(actor, "catalog_write")
        if mode not in AUTHORING_MODES:
            raise ValidationError(
                "mode must be one of %s" % (", ".join(AUTHORING_MODES),))
        _string(note, "note")
        with self._lock:
            self._get(self._authoring_drafts, draft_id, "authoring draft")
            session_id = self._next_id("asx")
            record = {
                "id": session_id,
                "draft_id": draft_id,
                "author_ref": actor_name(actor),
                "mode": mode,
                "note": note,
                "working_state": REFERENCE_STATE,
                "reference_stub": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._authoring_sessions[session_id] = record
            self._audit(actor, "ext_authoring_session_record", session_id,
                        details={"draft_id": draft_id, "mode": mode})
            return dict(record)

    def list_authoring_sessions(self, actor=None, draft_id=None):
        """Return authoring session records. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            records = list(self._authoring_sessions.values())
            if draft_id is not None:
                records = [r for r in records if r["draft_id"] == draft_id]
            return [dict(r) for r in records]

    def record_authoring_check(self, draft_id, actor, check_kind, outcome):
        """Record a caller-reported authoring check outcome.

        Action: catalog_write. The outcome (for example a Section
        508 conformance report from the authoring tool) is recorded
        verbatim as reported; this build runs no check and certifies
        no conformance — ``outcome_basis`` says so on the record.
        """
        self._require_actor(actor, "catalog_write")
        if check_kind not in AUTHORING_CHECK_KINDS:
            raise ValidationError(
                "check_kind must be one of %s"
                % (", ".join(AUTHORING_CHECK_KINDS),))
        _non_empty(outcome, "outcome")
        with self._lock:
            self._get(self._authoring_drafts, draft_id, "authoring draft")
            check_id = self._next_id("ack")
            record = {
                "id": check_id,
                "draft_id": draft_id,
                "check_kind": check_kind,
                "outcome": outcome,
                "outcome_basis": "caller_reported",
                "working_state": REFERENCE_STATE,
                "reference_stub": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._authoring_checks[check_id] = record
            self._audit(actor, "ext_authoring_check_record", check_id,
                        details={"draft_id": draft_id,
                                 "check_kind": check_kind})
            return dict(record)

    def list_authoring_checks(self, actor=None, draft_id=None):
        """Return authoring check records. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            records = list(self._authoring_checks.values())
            if draft_id is not None:
                records = [r for r in records if r["draft_id"] == draft_id]
            return [dict(r) for r in records]

    # -- Course posting & publication workflow (reference) ------------
    # Posting a course to a catalog or portal, and publishing a link
    # to external training, are acts against systems outside this
    # substrate. The substrate holds publication RECORDS bound to
    # core courses; creating one changes no core record and posts
    # nothing (``published_here: False`` on the record itself).

    def create_publication_record(self, course_id, channel, actor,
                                  target_org_ref=None, note=""):
        """Record a course posting/publication. Action: catalog_write.

        Stub-engine entry (idx 634): the record carries
        ``reference_stub: True`` and state ``recorded_reference_only``.
        A ``organization_portal`` posting requires the target
        organization reference, which must resolve to the core
        organization registry.
        """
        self._require_actor(actor, "catalog_write")
        if channel not in PUBLICATION_CHANNELS:
            raise ValidationError(
                "channel must be one of %s"
                % (", ".join(PUBLICATION_CHANNELS),))
        _string(note, "note")
        with self._lock:
            self.store.get_course(course_id, actor=None)
            if target_org_ref is not None:
                self._require_org(target_org_ref)
            if channel == "organization_portal" and target_org_ref is None:
                raise ValidationError(
                    "an organization_portal posting requires target_org_ref")
            record_id = self._next_id("pub")
            record = {
                "id": record_id,
                "course_id": course_id,
                "channel": channel,
                "target_org_ref": target_org_ref,
                "note": note,
                "state": REFERENCE_STATE,
                "published_here": False,
                "reference_stub": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._publication_records[record_id] = record
            self._audit(actor, "ext_publication_record_create", record_id,
                        details={"course_id": course_id, "channel": channel})
            return dict(record)

    def list_publication_records(self, actor=None, course_id=None):
        """Return publication records. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            records = list(self._publication_records.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            return [dict(r) for r in records]

    # -- Branded portal rendering & presentation engine (built) -------
    # The records form of TRAIN's branded portals: the presentation
    # itself (brand label, theme, menu labels) held as DATA bound to
    # a core organization, revised append-only. The current
    # presentation is derived at read from the revision list; the
    # stored record holds the initial presentation plus revisions,
    # never a "current" copy. Rendering and serving stay outside
    # (``rendered_here: False`` on every view).

    def create_portal_presentation(self, org_ref, actor, brand_label,
                                   theme="", menu_labels=None):
        """Record an organization's portal presentation.

        Action: organization_write (admin-only, mirroring the core
        organization registry). The organization reference must
        resolve to the core registry.
        """
        self._require_actor(actor, "organization_write")
        _non_empty(brand_label, "brand_label")
        _string(theme, "theme")
        if menu_labels is None:
            menu_labels = []
        menu_labels = _string_list(menu_labels, "menu_labels",
                                   allow_empty=True)
        with self._lock:
            self._require_org(org_ref)
            for existing in self._portal_presentations.values():
                if existing["org_ref"] == org_ref:
                    raise ValidationError(
                        "portal presentation already recorded for "
                        "organization %r" % (org_ref,))
            record_id = self._next_id("ppr")
            record = {
                "id": record_id,
                "org_ref": org_ref,
                "brand_label": brand_label,
                "theme": theme,
                "menu_labels": list(menu_labels),
                "revisions": [],
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._portal_presentations[record_id] = record
            self._audit(actor, "ext_portal_presentation_create", record_id,
                        details={"org_ref": org_ref,
                                 "brand_label": brand_label})
            return self._portal_view(record)

    def revise_portal_presentation(self, record_id, actor, brand_label,
                                   theme="", menu_labels=None, note=""):
        """Append a presentation revision. Action: organization_write.

        Revisions are append-only facts; the current presentation
        is derived from the latest one at read.
        """
        self._require_actor(actor, "organization_write")
        _non_empty(brand_label, "brand_label")
        _string(theme, "theme")
        _string(note, "note")
        if menu_labels is None:
            menu_labels = []
        menu_labels = _string_list(menu_labels, "menu_labels",
                                   allow_empty=True)
        with self._lock:
            record = self._get(self._portal_presentations, record_id,
                               "portal presentation")
            revision = {
                "brand_label": brand_label,
                "theme": theme,
                "menu_labels": list(menu_labels),
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            record["revisions"].append(revision)
            self._audit(actor, "ext_portal_presentation_revise", record_id,
                        details={"org_ref": record["org_ref"],
                                 "brand_label": brand_label})
            return self._portal_view(record)

    def _current_presentation(self, record):
        """Derive the current presentation: the latest revision wins.

        MUTATION DRILL NOTE: this read of the revision list is the
        load-bearing half of the portal negative control — a mutant
        that ignores revisions and always returns the initial
        presentation must fail the freshness expectations.
        """
        if record["revisions"]:
            latest = record["revisions"][-1]
            return {
                "brand_label": latest["brand_label"],
                "theme": latest["theme"],
                "menu_labels": list(latest["menu_labels"]),
            }
        return {
            "brand_label": record["brand_label"],
            "theme": record["theme"],
            "menu_labels": list(record["menu_labels"]),
        }

    def _portal_view(self, record):
        return {
            "id": record["id"],
            "org_ref": record["org_ref"],
            "current": self._current_presentation(record),
            "revision_count": len(record["revisions"]),
            "rendered_here": False,
            "recorded_by": record["recorded_by"],
            "recorded_utc": record["recorded_utc"],
        }

    def get_portal_presentation(self, record_id, actor=None):
        """Return one portal presentation view. Action: organization_read."""
        if actor is not None:
            self._require_actor(actor, "organization_read")
        with self._lock:
            record = self._get(self._portal_presentations, record_id,
                               "portal presentation")
            return self._portal_view(record)

    def list_portal_presentations(self, actor=None, org_ref=None):
        """Return portal presentation views. Action: organization_read."""
        if actor is not None:
            self._require_actor(actor, "organization_read")
        with self._lock:
            records = list(self._portal_presentations.values())
            if org_ref is not None:
                records = [r for r in records if r["org_ref"] == org_ref]
            return [self._portal_view(r) for r in records]

    # -- Continuing education management engine (built) ---------------
    # The records form of TRAIN's CE management: renewal-cycle
    # records over the core CE records. A cycle's coverage and
    # status are DERIVED at read from the core records for the
    # learner whose recorded_on falls inside the cycle period
    # (undated records count as in-period facts). Credit text —
    # the requirement's and every record's — stays verbatim and is
    # never parsed, summed, or converted: coverage is presence of
    # records and distinct activity references, never an arithmetic
    # over credit text. Renewal processing beyond this derivation
    # (notices, escalation) is not a records act and is not built.

    def create_ce_cycle(self, learner_ref, requirement_label, actor,
                        period_start, period_end, required_credit_text):
        """Create a CE renewal-cycle record. Action: continuing_ed_write."""
        self._require_actor(actor, "continuing_ed_write")
        _non_empty(learner_ref, "learner_ref")
        _non_empty(requirement_label, "requirement_label")
        _non_empty(required_credit_text, "required_credit_text")
        start = _validate_date(period_start, "period_start")
        end = _validate_date(period_end, "period_end")
        if end < start:
            raise ValidationError("period_end must not be before period_start")
        with self._lock:
            self._require_learner(learner_ref)
            cycle_id = self._next_id("crc")
            record = {
                "id": cycle_id,
                "learner_ref": learner_ref,
                "requirement_label": requirement_label,
                "period_start": period_start,
                "period_end": period_end,
                "required_credit_text": required_credit_text,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._ce_cycles[cycle_id] = record
            self._audit(actor, "ext_ce_cycle_create", cycle_id,
                        details={"learner_ref": learner_ref,
                                 "requirement_label": requirement_label})
            return dict(record)

    def _qualifying_ce_records(self, cycle):
        """Core CE records for the learner falling in the cycle period."""
        records = self.store.list_continuing_education(
            actor=None, learner_ref=cycle["learner_ref"])
        start = _validate_date(cycle["period_start"], "period_start")
        end = _validate_date(cycle["period_end"], "period_end")
        qualifying = []
        for record in records:
            if record["recorded_on"] is None:
                qualifying.append(record)
            else:
                recorded_on = _validate_date(record["recorded_on"],
                                             "recorded_on")
                if start <= recorded_on <= end:
                    qualifying.append(record)
        return qualifying

    def _derive_ce_cycle_status(self, cycle, as_of_date):
        """Derive satisfied/open/lapsed for a cycle. Never stored.

        MUTATION DRILL NOTE: the coverage branch of this derivation
        is the batch negative control's load-bearing invariant — a
        cycle with a qualifying core CE record in its period must
        read ``satisfied``, never ``open`` or ``lapsed``.
        """
        qualifying = self._qualifying_ce_records(cycle)
        if qualifying:
            return "satisfied"
        end = _validate_date(cycle["period_end"], "period_end")
        if as_of_date > end:
            return "lapsed"
        return "open"

    def _ce_cycle_view(self, cycle, as_of_date):
        qualifying = self._qualifying_ce_records(cycle)
        view = dict(cycle)
        view["recorded_record_count"] = len(qualifying)
        view["covered_activity_refs"] = sorted(
            {r["activity_ref"] for r in qualifying})
        view["credit_texts"] = [r["credit_text"] for r in qualifying]
        view["status"] = self._derive_ce_cycle_status(cycle, as_of_date)
        view["status_method"] = (
            "derived_from_core_continuing_education_records")
        view["as_of"] = as_of_date.isoformat()
        return view

    def get_ce_cycle(self, cycle_id, actor=None, as_of=None):
        """Return one CE cycle with derived coverage/status.

        Action: continuing_ed_read (+ learner scope).
        """
        if actor is not None:
            self._require_actor(actor, "continuing_ed_read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            record = self._get(self._ce_cycles, cycle_id, "CE cycle")
            self._scope_check(actor, record["learner_ref"])
            return self._ce_cycle_view(record, as_of_date)

    def list_ce_cycles(self, actor=None, learner_ref=None, as_of=None):
        """Return CE cycles with derived views. Action: continuing_ed_read."""
        if actor is not None:
            self._require_actor(actor, "continuing_ed_read")
        if learner_ref is not None:
            self._scope_check(actor, learner_ref)
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            records = list(self._ce_cycles.values())
            if learner_ref is not None:
                records = [r for r in records
                           if r["learner_ref"] == learner_ref]
            if actor is not None and getattr(actor, "role", None) == "learner":
                records = [r for r in records
                           if r["learner_ref"] == getattr(actor, "name", None)]
            return [self._ce_cycle_view(r, as_of_date) for r in records]

    # -- Certificate issuance & verification service (built) ----------
    # The records form of TRAIN's certificate service: issuance
    # records and verification-query records bound to core award
    # records. An issuance record records that an issuance was
    # effected through a channel — the substrate issues nothing
    # (``issued_here: False``); a verification query records a
    # caller-reported outcome verbatim — the substrate verifies
    # nothing (``verified_here: False``). Neither surface modifies
    # the core award record.

    def create_issuance_record(self, certificate_id, actor, channel):
        """Record a certificate issuance. Action: certificate_write."""
        self._require_actor(actor, "certificate_write")
        if channel not in ISSUANCE_CHANNELS:
            raise ValidationError(
                "channel must be one of %s" % (", ".join(ISSUANCE_CHANNELS),))
        with self._lock:
            certificate = self.store.get_certificate(certificate_id,
                                                     actor=None)
            record_id = self._next_id("iss")
            record = {
                "id": record_id,
                "certificate_id": certificate_id,
                "learner_ref": certificate["learner_ref"],
                "channel": channel,
                "state": "recorded",
                "issued_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._issuance_records[record_id] = record
            self._audit(actor, "ext_issuance_record_create", record_id,
                        details={"certificate_id": certificate_id,
                                 "channel": channel})
            return dict(record)

    def list_issuance_records(self, actor=None, certificate_id=None,
                              learner_ref=None):
        """Return issuance records. Action: certificate_read (+ scope)."""
        if actor is not None:
            self._require_actor(actor, "certificate_read")
        if learner_ref is not None:
            self._scope_check(actor, learner_ref)
        with self._lock:
            records = list(self._issuance_records.values())
            if certificate_id is not None:
                records = [r for r in records
                           if r["certificate_id"] == certificate_id]
            if learner_ref is not None:
                records = [r for r in records
                           if r["learner_ref"] == learner_ref]
            if actor is not None and getattr(actor, "role", None) == "learner":
                records = [r for r in records
                           if r["learner_ref"] == getattr(actor, "name", None)]
            return [dict(r) for r in records]

    def record_verification_query(self, certificate_id, actor, outcome_label):
        """Record a certificate verification query and its outcome.

        Action: certificate_write. The outcome is caller-reported
        and recorded verbatim; nothing is verified here.
        """
        self._require_actor(actor, "certificate_write")
        _non_empty(outcome_label, "outcome_label")
        with self._lock:
            certificate = self.store.get_certificate(certificate_id,
                                                     actor=None)
            record_id = self._next_id("vfy")
            record = {
                "id": record_id,
                "certificate_id": certificate_id,
                "learner_ref": certificate["learner_ref"],
                "outcome_label": outcome_label,
                "verified_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._verification_queries[record_id] = record
            self._audit(actor, "ext_verification_query_record", record_id,
                        details={"certificate_id": certificate_id,
                                 "outcome_label": outcome_label})
            return dict(record)

    def list_verification_queries(self, actor=None, certificate_id=None):
        """Return verification query records. Action: certificate_read."""
        if actor is not None:
            self._require_actor(actor, "certificate_read")
        with self._lock:
            records = list(self._verification_queries.values())
            if certificate_id is not None:
                records = [r for r in records
                           if r["certificate_id"] == certificate_id]
            if actor is not None and getattr(actor, "role", None) == "learner":
                records = [r for r in records
                           if r["learner_ref"] == getattr(actor, "name", None)]
            return [dict(r) for r in records]

    def certificate_service_view(self, certificate_id, actor=None):
        """Return the core award plus its service records and counts.

        Action: certificate_read (+ the core's learner scope, via
        the core certificate read). Counts are derived at read.
        """
        certificate = self.store.get_certificate(certificate_id, actor=actor)
        with self._lock:
            issuance = [dict(r) for r in self._issuance_records.values()
                        if r["certificate_id"] == certificate_id]
            queries = [dict(r) for r in self._verification_queries.values()
                       if r["certificate_id"] == certificate_id]
            return {
                "certificate": certificate,
                "issuance_records": issuance,
                "verification_queries": queries,
                "issuance_count": len(issuance),
                "verification_count": len(queries),
            }

    # -- System integration engines (reference) ------------------------
    # Connector runtimes against external systems execute outside
    # this substrate. The substrate holds integration records (the
    # systems TRAIN asserts integrations with, as opaque references
    # and directions) and caller-reported sync reports. Every record
    # is a labeled reference; nothing is transmitted or synced.

    def create_integration_record(self, system_ref, direction, actor,
                                  note=""):
        """Record an integration with an external system.

        Action: workflow_write. Stub-engine entry (idx 638): the
        record carries ``reference_stub: True``.
        """
        self._require_actor(actor, "workflow_write")
        _non_empty(system_ref, "system_ref")
        if direction not in INTEGRATION_DIRECTIONS:
            raise ValidationError(
                "direction must be one of %s"
                % (", ".join(INTEGRATION_DIRECTIONS),))
        _string(note, "note")
        with self._lock:
            record_id = self._next_id("int")
            record = {
                "id": record_id,
                "system_ref": system_ref,
                "direction": direction,
                "note": note,
                "state": REFERENCE_STATE,
                "reference_stub": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._integration_records[record_id] = record
            self._audit(actor, "ext_integration_record_create", record_id,
                        details={"system_ref": system_ref,
                                 "direction": direction})
            return dict(record)

    def list_integration_records(self, actor=None):
        """Return integration records. Action: workflow_read."""
        if actor is not None:
            self._require_actor(actor, "workflow_read")
        with self._lock:
            return [dict(r) for r in self._integration_records.values()]

    def record_sync_report(self, integration_id, actor, outcome_label,
                           record_count=None):
        """Record a caller-reported sync outcome for an integration.

        Action: workflow_write. The outcome is recorded verbatim as
        reported; no synchronization is performed here.
        """
        self._require_actor(actor, "workflow_write")
        _non_empty(outcome_label, "outcome_label")
        if record_count is not None:
            if (isinstance(record_count, bool)
                    or not isinstance(record_count, int) or record_count < 0):
                raise ValidationError(
                    "record_count must be a non-negative integer")
        with self._lock:
            self._get(self._integration_records, integration_id,
                      "integration record")
            record_id = self._next_id("syn")
            record = {
                "id": record_id,
                "integration_id": integration_id,
                "outcome_label": outcome_label,
                "record_count": record_count,
                "state": REFERENCE_STATE,
                "reference_stub": True,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._sync_reports[record_id] = record
            self._audit(actor, "ext_sync_report_record", record_id,
                        details={"integration_id": integration_id,
                                 "outcome_label": outcome_label})
            return dict(record)

    def list_sync_reports(self, actor=None, integration_id=None):
        """Return sync report records. Action: workflow_read."""
        if actor is not None:
            self._require_actor(actor, "workflow_read")
        with self._lock:
            records = list(self._sync_reports.values())
            if integration_id is not None:
                records = [r for r in records
                           if r["integration_id"] == integration_id]
            return [dict(r) for r in records]
