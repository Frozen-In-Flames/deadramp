"""Final GAPS batch extensions for the Operations Management L1
singleton build (Group 52, OpenWater).

Clean-room extension surface for the 9 OPEN entries in this
group's section of the repo-root ``GAPS.md`` ("Singleton 52 --
Operations Management L1 (1 fork)"). See ``BATCH.md`` in the
group directory for the per-entry disposition.

Design, following the core's doctrines and this group's spec:

- This module wraps :class:`opsmgmt.store.OpsStore`; the core
  modules are untouched (byte-identical). Core records (projects,
  persons) are always read through the core store's public API,
  never re-implemented. The core code is the shipped Group 36
  code reused for this singleton; what is NOT reused from Group
  36 is the Moderate baseline claim -- everything here is stated
  against the Low / FAR 52.204-21 baseline only, and no
  Moderate-tier apparatus is imported.
- The fork's own surface is submission management and review &
  evaluation, and the founding spec is absolute on one point:
  **nothing in the substrate scores anything** -- inspection
  records hold verbatim outcomes only. The extension keeps that
  discipline exactly. Review records store a score and feedback
  **verbatim as reported** by the reviewer (a recorded score is a
  report, never a computation); no aggregate, average, ranking,
  or derived score exists anywhere in this module, and review
  summaries are counts only.
- The eight build-extension entries are built in their **records
  form**: form definitions held as data (never rendered),
  submission records bound to a form definition whose values are
  submitter-supplied labels/references for fields the form
  defines (not a content store), reviewer-assignment records
  whose current assignees derive at read, message templates and
  dispatch-request records with verbatim reported outcomes
  (nothing is sent), report definitions plus run records whose
  figures derive at read as counts and sums of recorded values
  over this substrate's own records (no new metric is invented),
  site/page definitions as data (nothing is published or
  rendered), gallery definitions plus item records holding
  opaque media references only (nothing is hosted), session
  records whose room/speaker conflicts derive at read from
  recorded times (nothing is booked externally), and payment
  records over integer-cent amounts (records, never execution
  against real rails -- ``paid_here: False`` throughout).
- The one stub-engine entry (third-party integrations) ships as
  a **labeled reference implementation**: every record carries
  ``reference_stub: True`` (event references additionally
  ``reference_transport: True``), ``connected_here: False`` and
  ``synced_here: False``. Nothing connects to or syncs with any
  external system. This matches the founding spec, which names
  integrations out-of-scope for the fork (its one raw taxonomy
  hit was removed as a scope-exclusion wording artifact).
- Identity stays with the embedding organization
  (PLATFORM-LAYER.md decision 1): no identity surface exists
  here at all.
- RBAC reuses the founding 16-action matrix with **no new
  actions**; each extension operation maps onto an existing core
  action, checked before any state change or id allocation for
  User-like actors, mirroring the core store's convention
  (plain-string actors carry identity but no role). Successful
  mutations are recorded on the core audit log with an
  ``ext_``-prefixed action name; denied attempts are recorded
  with the same name suffixed ``:denied`` before the denial
  propagates:

  ============================  ===============  ================
  surface                       write action     read action
  ============================  ===============  ================
  form definitions              workflow_write   workflow_read
  submissions / assignments     work_write       work_read
  reviews                       inspection_write inspection_read
  message templates             workflow_write   workflow_read
  dispatch requests / outcomes  work_write       work_read
  report definitions            workflow_write   workflow_read
  report runs                   work_write       report_read
  site definitions              workflow_write   workflow_read
  galleries / gallery items     asset_write      asset_read
  sessions                      work_write       work_read
  session conflicts view        --               report_read
  payments / payment outcomes   usage_write      usage_read
  payments summary              --               report_read
  integration references        work_write       work_read
  ============================  ===============  ================

  (Configuration-shaped surfaces ride ``workflow_write`` -- the
  admin-only configuration write, as the core workflow registry
  does; verbatim-outcome records ride ``inspection_write``, as
  the core inspection records do; money-shaped records ride
  ``usage_write``, as the core metering records do.)

- Derived values are derived at read and never stored: a
  submission's current reviewer ids and review count, a
  payment's current reported status, report-run figures, and
  session conflicts. Stored records carry no derived key; tests
  pin that.
- All ``*_ref`` parameters naming things outside this build are
  opaque tokens: whitespace, URLs, hostnames, and IP-shaped
  values are rejected at the boundary, so a record cannot
  quietly carry a real system's address. Links into the core
  substrate use core ids (``proj-``, ``per-``), validated
  through the core store. Submitter-supplied field values are
  short label/reference strings for fields the form defines --
  never documents, never containers.
- One derivation is stated as a named seam.
  ``_windows_overlap``: the half-open window overlap test
  behind the session-conflict derivation -- the batch's fresh
  negative control mutates it (see tests/README.md).
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


_IP_LIKE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

# -- option sets -------------------------------------------------------

DISPATCH_REPORTED_STATUSES = (
    "reported_sent",
    "reported_failed",
    "reported_suppressed",
)
PAYMENT_REPORTED_STATUSES = (
    "reported_paid",
    "reported_failed",
    "reported_refunded",
)
REPORT_METRICS = (
    "submission_count",
    "review_count",
    "dispatch_request_count",
    "payment_count",
    "payment_total_cents",
    "session_count",
    "session_conflict_count",
    "gallery_item_count",
)
INTEGRATION_KINDS = ("api", "file", "database", "messaging", "sso", "other")
INTEGRATION_EVENT_STATUSES = (
    "reported_success",
    "reported_partial",
    "reported_failed",
)

# -- validation helpers --------------------------------------------------


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_ref(value, what):
    """Validate an opaque reference token.

    A reference names a thing in the caller's own world; it is
    never an address and never an identifier issued by a real
    system. Whitespace, URLs, hostnames, and IP-shaped values are
    rejected so records cannot carry a real system's location.
    """
    _validate_non_empty(value, what)
    if any(ch.isspace() for ch in value):
        raise ValidationError("%s must be an opaque reference (no spaces)" % (what,))
    if "://" in value or "/" in value or _IP_LIKE.match(value):
        raise ValidationError("%s must be an opaque reference, not an address" % (what,))
    if "." in value:
        raise ValidationError("%s must be an opaque reference, not a hostname" % (what,))
    if len(value) > 128:
        raise ValidationError("%s is too long for an opaque reference" % (what,))
    return value


def _validate_choice(value, options, what):
    if value not in options:
        raise ValidationError("%s must be one of %s" % (what, ", ".join(options)))
    return value


def _validate_int(value, what, minimum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if minimum is not None and value < minimum:
        raise ValidationError("%s must be at least %d" % (what, minimum))
    return value


def _validate_scalar(value, what):
    """A reported value stored verbatim: a string, integer, or
    float. Booleans, None, and containers are rejected -- a
    reported value is a scalar, not a document."""
    if isinstance(value, bool) or value is None or not isinstance(
        value, (str, int, float)
    ):
        raise ValidationError("%s must be a string, integer, or float" % (what,))
    if isinstance(value, str) and not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_optional_text(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string or None" % (what,))
    return value


def _parse_iso_datetime(value, what):
    """Parse an ISO-8601 datetime exactly as the core store does."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 datetime string" % (what,))
    text = value.strip()
    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(
            "%s is not a valid ISO-8601 datetime: %r" % (what, value)
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _validate_form_fields(fields, what="fields"):
    """Form field definitions held as data: a list of objects,
    each with a non-empty ``name`` and a non-empty ``kind``;
    field names must be unique within the form."""
    if fields is None:
        return []
    if not isinstance(fields, list):
        raise ValidationError("%s must be a list of field objects" % (what,))
    if len(fields) > 100:
        raise ValidationError("%s may hold at most 100 entries" % (what,))
    cleaned = []
    seen = set()
    for field in fields:
        if not isinstance(field, dict):
            raise ValidationError("each entry in %s must be an object" % (what,))
        _validate_non_empty(field.get("name"), "field name")
        _validate_non_empty(field.get("kind"), "field kind")
        if field["name"] in seen:
            raise ValidationError(
                "duplicate field name in %s: %r" % (what, field["name"])
            )
        seen.add(field["name"])
        cleaned.append(copy.deepcopy(field))
    return cleaned


def _validate_pages(pages, what="pages"):
    """Site page definitions held as data: a list of objects,
    each with a non-empty ``kind`` and a non-empty ``label``."""
    if pages is None:
        return []
    if not isinstance(pages, list):
        raise ValidationError("%s must be a list of page objects" % (what,))
    if len(pages) > 100:
        raise ValidationError("%s may hold at most 100 entries" % (what,))
    cleaned = []
    for page in pages:
        if not isinstance(page, dict):
            raise ValidationError("each entry in %s must be an object" % (what,))
        _validate_non_empty(page.get("kind"), "page kind")
        _validate_non_empty(page.get("label"), "page label")
        cleaned.append(copy.deepcopy(page))
    return cleaned


def _validate_field_values(field_values, form):
    """Submitter-supplied values for one submission.

    Values ride only for fields the form defines, and each value
    is a short label/reference string -- the submission record
    holds the submitter's recorded answers as labels, not as a
    content store: containers, numbers, and documents are
    rejected.
    """
    if field_values is None:
        return {}
    if not isinstance(field_values, dict):
        raise ValidationError("field_values must be an object")
    defined = {field["name"] for field in form["fields"]}
    cleaned = {}
    for key, value in field_values.items():
        _validate_non_empty(key, "field_values key")
        if key not in defined:
            raise ValidationError(
                "field_values names a field the form does not define: %r" % (key,)
            )
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(
                "field value for %r must be a non-empty label/reference string"
                % (key,)
            )
        if len(value) > 512:
            raise ValidationError(
                "field value for %r is too long for a label/reference string"
                % (key,)
            )
        cleaned[key] = value
    return cleaned


# -- derivation seam -----------------------------------------------------


def _windows_overlap(a_start, a_end, b_start, b_end):
    """Half-open window overlap derivation for session conflicts.

    Two recorded session windows overlap iff each starts before
    the other ends: ``[start, end)`` -- a session that ends
    exactly when another begins does not overlap it. This is the
    single derivation point behind :meth:`OpsExtensions
    .session_conflicts`; the batch's fresh negative control
    mutates it (see tests/README.md).
    """
    return a_start < b_end and b_start < a_end


class OpsExtensions:
    """GAPS-batch extension surface over a core OpsStore."""

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

        Mirrors the core store: an actor must be present;
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
            record["updated_utc"] = record["created_utc"]
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            self._audit(actor, audit_action, record_id, details={"kind": kind})
            return copy.deepcopy(record)

    def _get(self, kind, record_id):
        record = self._records.get((kind, record_id))
        if record is None:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id):
        return copy.deepcopy(self._get(kind, record_id))

    def _list(self, collection, **filters):
        result = []
        for key in self._order:
            if key[0] != collection:
                continue
            record = self._records[key]
            if all(
                record.get(name) == value
                for name, value in filters.items()
                if value is not None
            ):
                result.append(copy.deepcopy(record))
        return result

    def _touch(self, record, actor, audit_action):
        record["updated_utc"] = _utc_now()
        self._audit(actor, audit_action, record["id"])

    # Core-record existence checks, read through the core store's
    # public API with no actor (internal reads; the caller's own
    # permission was already enforced by the guard).

    def _core_project(self, project_id):
        return self.store.get_project(project_id)

    def _core_person(self, person_id):
        return self.store.get_person(person_id)

    # -- Submission management --------------------------------------
    # Records form: form definitions held as data (fields as
    # definition objects; nothing is rendered), submission
    # records bound to a form definition carrying submitter
    # labels/references for defined fields only, and
    # reviewer-assignment records whose current assignees derive
    # at read. No intake engine runs here.

    def create_form_definition(self, name, actor, project_id=None,
                               fields=None, description=None):
        """Create a submission-form definition record.

        Action: workflow_write (configuration, as the core
        workflow registry). ``fields`` are held verbatim as data;
        each must be an object with a non-empty ``name`` and
        ``kind``, and names must be unique. The definition is
        data only: ``rendered_here: False``.
        """
        self._guard(actor, "workflow_write", "ext_form_create", name)
        _validate_non_empty(name, "form name")
        _validate_optional_text(description, "description")
        fields = _validate_form_fields(fields)
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "form_definition", "frm",
            {
                "name": name,
                "project_id": project_id,
                "fields": fields,
                "description": description,
                "version": 1,
                "rendered_here": False,
            },
            actor, "ext_form_create",
        )

    def update_form_definition(self, form_id, actor, fields=None,
                               description=None):
        """Replace a form definition's fields and/or description,
        bumping its version. Action: workflow_write. The
        definition is data; updating it renders nothing."""
        self._guard(actor, "workflow_write", "ext_form_update", form_id)
        record = self._get("form_definition", form_id)
        cleaned = None
        if fields is not None:
            cleaned = _validate_form_fields(fields)
        _validate_optional_text(description, "description")
        with self._lock:
            if cleaned is not None:
                record["fields"] = cleaned
            if description is not None:
                record["description"] = description
            record["version"] += 1
            self._touch(record, actor, "ext_form_update")
            return copy.deepcopy(record)

    def get_form_definition(self, form_id, actor=None):
        """Read one form definition. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_form_read", form_id)
        return self._fetch("form_definition", form_id)

    def list_form_definitions(self, actor=None, project_id=None):
        """List form definitions. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_form_read")
        return self._list("form_definition", project_id=project_id)

    def record_submission(self, form_id, actor, submitter_ref,
                          field_values=None):
        """Record a submission against a form definition.

        Action: work_write. ``submitter_ref`` is an opaque
        reference (never a real identifier). ``field_values``
        maps field names the form defines to the submitter's
        recorded label/reference strings -- labels, not content:
        this record is the intake record, not a content store.
        """
        self._guard(actor, "work_write", "ext_submission_record", form_id)
        form = self._get("form_definition", form_id)
        _validate_ref(submitter_ref, "submitter_ref")
        field_values = _validate_field_values(field_values, form)
        return self._create(
            "submission", "sub",
            {
                "form_id": form_id,
                "submitter_ref": submitter_ref,
                "field_values": field_values,
                "status": "recorded",
            },
            actor, "ext_submission_record",
        )

    def get_submission(self, submission_id, actor=None):
        """Read one submission record. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_submission_read",
                         submission_id)
        return self._fetch("submission", submission_id)

    def list_submissions(self, actor=None, form_id=None):
        """List submission records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_submission_read")
        return self._list("submission", form_id=form_id)

    def assign_reviewer(self, submission_id, reviewer_id, actor):
        """Assign a core directory person as a reviewer of a
        submission. Action: work_write. A duplicate ACTIVE
        assignment of the same reviewer to the same submission
        is a validation error; a withdrawn assignment does not
        block re-assignment."""
        self._guard(actor, "work_write", "ext_reviewer_assign",
                    submission_id)
        self._get("submission", submission_id)
        self._core_person(reviewer_id)
        for existing in self._list("reviewer_assignment",
                                   submission_id=submission_id,
                                   reviewer_id=reviewer_id):
            if existing["status"] == "active":
                raise ValidationError(
                    "person %r is already an active reviewer of "
                    "submission %r" % (reviewer_id, submission_id)
                )
        return self._create(
            "reviewer_assignment", "ras",
            {
                "submission_id": submission_id,
                "reviewer_id": reviewer_id,
                "status": "active",
            },
            actor, "ext_reviewer_assign",
        )

    def withdraw_reviewer_assignment(self, assignment_id, actor):
        """Withdraw an active reviewer assignment. Action:
        work_write. A withdrawn assignment no longer counts
        toward the submission's current reviewers."""
        self._guard(actor, "work_write", "ext_reviewer_withdraw",
                    assignment_id)
        record = self._get("reviewer_assignment", assignment_id)
        if record["status"] != "active":
            raise ValidationError(
                "reviewer assignment %r is not active" % (assignment_id,)
            )
        with self._lock:
            record["status"] = "withdrawn"
            self._touch(record, actor, "ext_reviewer_withdraw")
            return copy.deepcopy(record)

    def list_reviewer_assignments(self, actor=None, submission_id=None,
                                  reviewer_id=None, status=None):
        """List reviewer-assignment records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_reviewer_read")
        return self._list("reviewer_assignment",
                          submission_id=submission_id,
                          reviewer_id=reviewer_id, status=status)

    def submission_view(self, submission_id, actor=None):
        """One submission record plus its derived current state:
        ``current_reviewer_ids`` (the reviewer ids of ACTIVE
        assignments, in assignment order) and ``review_count``.
        Both are derived at read and never stored on the
        submission record. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_submission_read",
                         submission_id)
        view = self._fetch("submission", submission_id)
        active = self._list("reviewer_assignment",
                            submission_id=submission_id, status="active")
        view["current_reviewer_ids"] = [a["reviewer_id"] for a in active]
        view["review_count"] = len(
            self._list("review", submission_id=submission_id)
        )
        return view

    # -- Review & evaluation ------------------------------------------
    # Records form under the founding discipline: a review record
    # stores the reviewer's score and feedback VERBATIM as
    # reported. A recorded score is a report, never a
    # computation -- nothing in this build aggregates, averages,
    # ranks, or derives any score (score_computed_here: False on
    # every record; summaries are counts only). Review records
    # are immutable once written, as the core inspection records
    # are; corrections ride as new records.

    def record_review(self, submission_id, actor, score,
                      reviewer_id=None, feedback=None):
        """Record a review of a submission, storing ``score``
        and ``feedback`` exactly as reported.

        Action: inspection_write (a verbatim-outcome record, as
        the core inspections are). ``score`` is a scalar (string,
        integer, or float) stored verbatim; it is never combined
        with any other score. ``reviewer_id``, when given, must
        be a core directory person.
        """
        self._guard(actor, "inspection_write", "ext_review_record",
                    submission_id)
        self._get("submission", submission_id)
        _validate_scalar(score, "score")
        if reviewer_id is not None:
            self._core_person(reviewer_id)
        _validate_optional_text(feedback, "feedback")
        return self._create(
            "review", "rev",
            {
                "submission_id": submission_id,
                "reviewer_id": reviewer_id,
                "score": score,
                "feedback": feedback,
                "score_computed_here": False,
            },
            actor, "ext_review_record",
        )

    def get_review(self, review_id, actor=None):
        """Read one review record. Action: inspection_read."""
        self._guard_read(actor, "inspection_read", "ext_review_read",
                         review_id)
        return self._fetch("review", review_id)

    def list_reviews(self, actor=None, submission_id=None):
        """List review records. Action: inspection_read."""
        self._guard_read(actor, "inspection_read", "ext_review_read")
        return self._list("review", submission_id=submission_id)

    def review_summary(self, actor=None):
        """Derived review counts: total reviews and counts per
        submission. Counts only -- no score is aggregated,
        averaged, or ranked anywhere (``scores_aggregated:
        False``). Derived at read, never stored.
        Action: report_read."""
        self._guard_read(actor, "report_read", "ext_review_summary")
        reviews = self._list("review")
        by_submission = {}
        for review in reviews:
            key = review["submission_id"]
            by_submission[key] = by_submission.get(key, 0) + 1
        return {
            "reviews": len(reviews),
            "reviews_by_submission": by_submission,
            "scores_aggregated": False,
        }

    # -- Automated communications --------------------------------------
    # Records form: message-template records (template text held
    # verbatim as data) plus dispatch-request records with
    # verbatim reported outcomes. Nothing is sent from this
    # build (sent_here: False on every dispatch record).

    def create_message_template(self, name, actor, body_text,
                                subject_label=None, project_id=None):
        """Create a message-template record. Action:
        workflow_write (configuration). ``body_text`` is held
        verbatim as data; it is rendered nowhere and sent
        nowhere."""
        self._guard(actor, "workflow_write", "ext_template_create", name)
        _validate_non_empty(name, "template name")
        _validate_non_empty(body_text, "body_text")
        _validate_optional_text(subject_label, "subject_label")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "message_template", "msg",
            {
                "name": name,
                "subject_label": subject_label,
                "body_text": body_text,
                "project_id": project_id,
                "version": 1,
                "rendered_here": False,
            },
            actor, "ext_template_create",
        )

    def update_message_template(self, template_id, actor,
                                body_text=None, subject_label=None):
        """Replace a template's body and/or subject label,
        bumping its version. Action: workflow_write."""
        self._guard(actor, "workflow_write", "ext_template_update",
                    template_id)
        record = self._get("message_template", template_id)
        if body_text is not None:
            _validate_non_empty(body_text, "body_text")
        _validate_optional_text(subject_label, "subject_label")
        with self._lock:
            if body_text is not None:
                record["body_text"] = body_text
            if subject_label is not None:
                record["subject_label"] = subject_label
            record["version"] += 1
            self._touch(record, actor, "ext_template_update")
            return copy.deepcopy(record)

    def get_message_template(self, template_id, actor=None):
        """Read one message template. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_template_read",
                         template_id)
        return self._fetch("message_template", template_id)

    def list_message_templates(self, actor=None, project_id=None):
        """List message templates. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_template_read")
        return self._list("message_template", project_id=project_id)

    def record_dispatch_request(self, template_id, recipient_ref,
                                actor, submission_id=None):
        """Record a request to dispatch a template to a
        recipient named by an opaque reference. Action:
        work_write. The request is a record only: it carries
        ``sent_here: False`` and recording it sends nothing."""
        self._guard(actor, "work_write", "ext_dispatch_request",
                    template_id)
        self._get("message_template", template_id)
        _validate_ref(recipient_ref, "recipient_ref")
        if submission_id is not None:
            self._get("submission", submission_id)
        return self._create(
            "dispatch_request", "dsp",
            {
                "template_id": template_id,
                "recipient_ref": recipient_ref,
                "submission_id": submission_id,
                "status": "recorded",
                "sent_here": False,
            },
            actor, "ext_dispatch_request",
        )

    def record_dispatch_outcome(self, request_id, reported_status,
                                actor, note=None):
        """Record a dispatch outcome **as reported by the
        external sending system**. Action: work_write. The
        outcome is stored as reported; this build sent nothing
        and verifies nothing."""
        self._guard(actor, "work_write", "ext_dispatch_outcome",
                    request_id)
        self._get("dispatch_request", request_id)
        _validate_choice(reported_status, DISPATCH_REPORTED_STATUSES,
                         "reported_status")
        _validate_optional_text(note, "note")
        return self._create(
            "dispatch_outcome", "dso",
            {
                "request_id": request_id,
                "reported_status": reported_status,
                "note": note,
                "sent_here": False,
            },
            actor, "ext_dispatch_outcome",
        )

    def get_dispatch_request(self, request_id, actor=None):
        """Read one dispatch-request record. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_dispatch_read",
                         request_id)
        return self._fetch("dispatch_request", request_id)

    def list_dispatch_requests(self, actor=None, template_id=None,
                               submission_id=None):
        """List dispatch-request records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_dispatch_read")
        return self._list("dispatch_request", template_id=template_id,
                          submission_id=submission_id)

    def list_dispatch_outcomes(self, actor=None, request_id=None):
        """List dispatch-outcome records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_dispatch_read")
        return self._list("dispatch_outcome", request_id=request_id)

    # -- Reporting ------------------------------------------------------
    # Records form: report definitions held as data (a name, an
    # optional project scope, and a list of metric names from
    # REPORT_METRICS) plus report-run records. A run's figures
    # are derived at read from this substrate's own records --
    # counts of records and sums of recorded integer-cent
    # amounts only; no new metric is invented and nothing is
    # stored on the run record.

    def create_report_definition(self, name, actor, metrics,
                                 project_id=None, description=None):
        """Create a report definition record. Action:
        workflow_write (configuration). ``metrics`` must be a
        non-empty list of names from ``REPORT_METRICS``; the
        definition is data -- it computes nothing itself."""
        self._guard(actor, "workflow_write", "ext_report_definition",
                    name)
        _validate_non_empty(name, "report name")
        if not isinstance(metrics, list) or not metrics:
            raise ValidationError("metrics must be a non-empty list")
        cleaned = []
        for metric in metrics:
            _validate_choice(metric, REPORT_METRICS, "metric")
            if metric not in cleaned:
                cleaned.append(metric)
        _validate_optional_text(description, "description")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "report_definition", "rpd",
            {
                "name": name,
                "metrics": cleaned,
                "project_id": project_id,
                "description": description,
                "computed_here": False,
            },
            actor, "ext_report_definition",
        )

    def update_report_definition(self, definition_id, actor,
                                 metrics=None, description=None):
        """Replace a report definition's metric list and/or
        description. Action: workflow_write."""
        self._guard(actor, "workflow_write", "ext_report_definition",
                    definition_id)
        record = self._get("report_definition", definition_id)
        cleaned = None
        if metrics is not None:
            if not isinstance(metrics, list) or not metrics:
                raise ValidationError("metrics must be a non-empty list")
            cleaned = []
            for metric in metrics:
                _validate_choice(metric, REPORT_METRICS, "metric")
                if metric not in cleaned:
                    cleaned.append(metric)
        _validate_optional_text(description, "description")
        with self._lock:
            if cleaned is not None:
                record["metrics"] = cleaned
            if description is not None:
                record["description"] = description
            self._touch(record, actor, "ext_report_definition")
            return copy.deepcopy(record)

    def get_report_definition(self, definition_id, actor=None):
        """Read one report definition. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_report_read",
                         definition_id)
        return self._fetch("report_definition", definition_id)

    def list_report_definitions(self, actor=None, project_id=None):
        """List report definitions. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_report_read")
        return self._list("report_definition", project_id=project_id)

    def record_report_run(self, definition_id, actor):
        """Record that a report was run against a definition.
        Action: work_write. The run record stores no figures --
        figures are derived at read in :meth:`report_run_view`,
        so a run never carries a stale or fabricated number."""
        self._guard(actor, "work_write", "ext_report_run", definition_id)
        self._get("report_definition", definition_id)
        return self._create(
            "report_run", "rpr",
            {"definition_id": definition_id},
            actor, "ext_report_run",
        )

    def list_report_runs(self, actor=None, definition_id=None):
        """List report-run records. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_report_read")
        return self._list("report_run", definition_id=definition_id)

    def _form_project_id(self, form_id):
        form = self._records.get(("form_definition", form_id))
        return form["project_id"] if form is not None else None

    def _submission_project_id(self, submission_id):
        submission = self._records.get(("submission", submission_id))
        if submission is None:
            return None
        return self._form_project_id(submission["form_id"])

    def _dispatch_project_id(self, dispatch):
        """A dispatch request's project: its submission's form's
        project when it is bound to a submission, else its
        template's project."""
        if dispatch["submission_id"] is not None:
            return self._submission_project_id(dispatch["submission_id"])
        template = self._records.get(
            ("message_template", dispatch["template_id"]))
        return template["project_id"] if template is not None else None

    def _gallery_project_id(self, item):
        gallery = self._records.get(("gallery", item["gallery_id"]))
        return gallery["project_id"] if gallery is not None else None

    def _in_scope(self, record_project_id, scope_project_id):
        return scope_project_id is None or record_project_id == scope_project_id

    def _derive_metric(self, metric, scope_project_id):
        """One report figure, derived at read over the
        extension's own records: a count of records, or a sum of
        recorded integer-cent amounts. Nothing else is computed
        -- in particular no score, rate, or ratio is derived."""
        if metric == "submission_count":
            return len([
                s for s in self._list("submission")
                if self._in_scope(self._form_project_id(s["form_id"]),
                                  scope_project_id)
            ])
        if metric == "review_count":
            return len([
                r for r in self._list("review")
                if self._in_scope(
                    self._submission_project_id(r["submission_id"]),
                    scope_project_id)
            ])
        if metric == "dispatch_request_count":
            return len([
                d for d in self._list("dispatch_request")
                if self._in_scope(self._dispatch_project_id(d),
                                  scope_project_id)
            ])
        if metric == "payment_count":
            return len([
                p for p in self._list("payment")
                if self._in_scope(p["project_id"], scope_project_id)
            ])
        if metric == "payment_total_cents":
            return sum(
                p["amount_cents"] for p in self._list("payment")
                if self._in_scope(p["project_id"], scope_project_id)
            )
        if metric == "session_count":
            return len([
                s for s in self._list("session")
                if self._in_scope(s["project_id"], scope_project_id)
            ])
        if metric == "session_conflict_count":
            return len(self._derive_conflicts(scope_project_id))
        if metric == "gallery_item_count":
            return len([
                i for i in self._list("gallery_item")
                if self._in_scope(self._gallery_project_id(i),
                                  scope_project_id)
            ])
        raise ValidationError("unknown metric: %r" % (metric,))

    def report_run_view(self, run_id, actor=None):
        """One report-run record plus its figures, derived at
        read from the substrate's current records under the
        run's definition (metric list and project scope). The
        stored run record carries no figures. Action:
        report_read."""
        self._guard_read(actor, "report_read", "ext_report_read", run_id)
        run = self._fetch("report_run", run_id)
        definition = self._get("report_definition", run["definition_id"])
        figures = {}
        for metric in definition["metrics"]:
            figures[metric] = self._derive_metric(
                metric, definition["project_id"])
        view = dict(run)
        view["figures"] = figures
        return view

    # -- Program website builder ----------------------------------------
    # Records form: site definitions whose pages are held as data
    # (each page an object with a non-empty ``kind`` and
    # ``label``), versioned on update. Nothing is published,
    # rendered, or hosted (published_here / rendered_here:
    # False).

    def create_site_definition(self, name, actor, project_id=None,
                               pages=None, description=None):
        """Create a program-site definition record. Action:
        workflow_write (configuration). ``pages`` are held
        verbatim as data."""
        self._guard(actor, "workflow_write", "ext_site_create", name)
        _validate_non_empty(name, "site name")
        _validate_optional_text(description, "description")
        pages = _validate_pages(pages)
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "site_definition", "site",
            {
                "name": name,
                "project_id": project_id,
                "pages": pages,
                "description": description,
                "version": 1,
                "published_here": False,
                "rendered_here": False,
            },
            actor, "ext_site_create",
        )

    def update_site_definition(self, site_id, actor, pages=None,
                               description=None):
        """Replace a site definition's pages and/or description,
        bumping its version. Action: workflow_write."""
        self._guard(actor, "workflow_write", "ext_site_update", site_id)
        record = self._get("site_definition", site_id)
        cleaned = None
        if pages is not None:
            cleaned = _validate_pages(pages)
        _validate_optional_text(description, "description")
        with self._lock:
            if cleaned is not None:
                record["pages"] = cleaned
            if description is not None:
                record["description"] = description
            record["version"] += 1
            self._touch(record, actor, "ext_site_update")
            return copy.deepcopy(record)

    def get_site_definition(self, site_id, actor=None):
        """Read one site definition. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_site_read", site_id)
        return self._fetch("site_definition", site_id)

    def list_site_definitions(self, actor=None, project_id=None):
        """List site definitions. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_site_read")
        return self._list("site_definition", project_id=project_id)

    # -- Galleries --------------------------------------------------------
    # Records form: gallery definitions plus item records holding
    # an opaque media reference and an optional caption label.
    # No media content is held anywhere -- there is no content
    # field -- and nothing is hosted (hosted_here: False).

    def create_gallery(self, name, actor, project_id=None):
        """Create a gallery definition record. Action:
        asset_write."""
        self._guard(actor, "asset_write", "ext_gallery_create", name)
        _validate_non_empty(name, "gallery name")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "gallery", "gal",
            {
                "name": name,
                "project_id": project_id,
                "hosted_here": False,
            },
            actor, "ext_gallery_create",
        )

    def add_gallery_item(self, gallery_id, media_ref, actor,
                         caption_label=None):
        """Add an item record to a gallery, holding an opaque
        media reference only. Action: asset_write. The media
        itself is never uploaded, stored, or hosted here."""
        self._guard(actor, "asset_write", "ext_gallery_item", gallery_id)
        self._get("gallery", gallery_id)
        _validate_ref(media_ref, "media_ref")
        _validate_optional_text(caption_label, "caption_label")
        return self._create(
            "gallery_item", "gim",
            {
                "gallery_id": gallery_id,
                "media_ref": media_ref,
                "caption_label": caption_label,
                "hosted_here": False,
            },
            actor, "ext_gallery_item",
        )

    def get_gallery(self, gallery_id, actor=None):
        """Read one gallery record. Action: asset_read."""
        self._guard_read(actor, "asset_read", "ext_gallery_read",
                         gallery_id)
        return self._fetch("gallery", gallery_id)

    def list_galleries(self, actor=None, project_id=None):
        """List gallery records. Action: asset_read."""
        self._guard_read(actor, "asset_read", "ext_gallery_read")
        return self._list("gallery", project_id=project_id)

    def list_gallery_items(self, actor=None, gallery_id=None):
        """List gallery item records. Action: asset_read."""
        self._guard_read(actor, "asset_read", "ext_gallery_read")
        return self._list("gallery_item", gallery_id=gallery_id)

    def gallery_view(self, gallery_id, actor=None):
        """One gallery record plus its derived item count
        (derived at read, never stored). Action: asset_read."""
        self._guard_read(actor, "asset_read", "ext_gallery_read",
                         gallery_id)
        view = self._fetch("gallery", gallery_id)
        view["item_count"] = len(
            self._list("gallery_item", gallery_id=gallery_id))
        return view

    # -- Conference session scheduling ------------------------------------
    # Records form: session records (times, room label, optional
    # core-person speaker, optional core project). Conflicts --
    # two sessions sharing a room label, or one speaker, whose
    # recorded windows overlap -- are DERIVED at read from the
    # recorded times via the ``_windows_overlap`` seam; the
    # stored session record carries no conflict state. Nothing
    # is booked externally (booked_here: False on the view).

    def create_session(self, title, actor, starts_at, ends_at,
                       room_label=None, project_id=None,
                       speaker_id=None):
        """Create a session record. Action: work_write.
        ``ends_at`` must be after ``starts_at``; ``speaker_id``,
        when given, must be a core directory person."""
        self._guard(actor, "work_write", "ext_session_create", title)
        _validate_non_empty(title, "session title")
        start_dt = _parse_iso_datetime(starts_at, "starts_at")
        end_dt = _parse_iso_datetime(ends_at, "ends_at")
        if end_dt <= start_dt:
            raise ValidationError("ends_at must be after starts_at")
        _validate_optional_text(room_label, "room_label")
        if project_id is not None:
            self._core_project(project_id)
        if speaker_id is not None:
            self._core_person(speaker_id)
        return self._create(
            "session", "ses",
            {
                "title": title,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "room_label": room_label,
                "project_id": project_id,
                "speaker_id": speaker_id,
            },
            actor, "ext_session_create",
        )

    def get_session(self, session_id, actor=None):
        """Read one session record. Action: work_read. The
        stored record carries no derived conflict key."""
        self._guard_read(actor, "work_read", "ext_session_read",
                         session_id)
        return self._fetch("session", session_id)

    def list_sessions(self, actor=None, project_id=None, room_label=None):
        """List session records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_session_read")
        return self._list("session", project_id=project_id,
                          room_label=room_label)

    def _derive_conflicts(self, scope_project_id=None):
        """Derive session conflicts at read: pairs of sessions
        (in creation order) that share a room label or a speaker
        and whose recorded windows overlap under
        ``_windows_overlap``. Derived only -- never stored."""
        sessions = [
            s for s in self._list("session")
            if self._in_scope(s["project_id"], scope_project_id)
        ]
        windows = {
            s["id"]: (
                _parse_iso_datetime(s["starts_at"], "starts_at"),
                _parse_iso_datetime(s["ends_at"], "ends_at"),
            )
            for s in sessions
        }
        conflicts = []
        for index, first in enumerate(sessions):
            for second in sessions[index + 1:]:
                a_start, a_end = windows[first["id"]]
                b_start, b_end = windows[second["id"]]
                if not _windows_overlap(a_start, a_end, b_start, b_end):
                    continue
                if (first["room_label"] is not None
                        and first["room_label"] == second["room_label"]):
                    conflicts.append({
                        "session_a": first["id"],
                        "session_b": second["id"],
                        "reason": "room",
                    })
                if (first["speaker_id"] is not None
                        and first["speaker_id"] == second["speaker_id"]):
                    conflicts.append({
                        "session_a": first["id"],
                        "session_b": second["id"],
                        "reason": "speaker",
                    })
        return conflicts

    def session_conflicts(self, actor=None, project_id=None):
        """Derived conflicts view over session records:
        overlapping pairs sharing a room label or a speaker.
        Derived at read from recorded times; nothing is stored
        and nothing is booked (``booked_here: False``).
        Action: report_read."""
        self._guard_read(actor, "report_read", "ext_session_conflicts")
        conflicts = self._derive_conflicts(project_id)
        return {
            "conflicts": conflicts,
            "conflict_count": len(conflicts),
            "booked_here": False,
        }

    # -- Payments ---------------------------------------------------------
    # Records form: payment records over recorded integer-cent
    # amounts plus outcome records stored exactly as reported by
    # the external payment system. Records, never execution
    # against real rails (paid_here: False on every record); a
    # payment's current reported status derives at read from its
    # latest outcome record. Floats and booleans are rejected as
    # amounts, per the house money doctrine.

    def record_payment(self, actor, amount_cents, payer_ref=None,
                       project_id=None, submission_id=None,
                       note=None):
        """Record a payment of ``amount_cents`` integer cents.

        Action: usage_write (a money-shaped record, as the core
        metering records are). The amount must be an int >= 1;
        floats and booleans are rejected. Recording a payment
        moves no money.
        """
        self._guard(actor, "usage_write", "ext_payment_record")
        _validate_int(amount_cents, "amount_cents", minimum=1)
        if payer_ref is not None:
            _validate_ref(payer_ref, "payer_ref")
        if project_id is not None:
            self._core_project(project_id)
        if submission_id is not None:
            self._get("submission", submission_id)
        _validate_optional_text(note, "note")
        return self._create(
            "payment", "pay",
            {
                "amount_cents": amount_cents,
                "payer_ref": payer_ref,
                "project_id": project_id,
                "submission_id": submission_id,
                "note": note,
                "status": "recorded",
                "paid_here": False,
            },
            actor, "ext_payment_record",
        )

    def record_payment_outcome(self, payment_id, reported_status,
                               actor, note=None):
        """Record a payment outcome **as reported by the
        external payment system**. Action: usage_write. The
        outcome is stored as reported; this build executed no
        payment and verifies none."""
        self._guard(actor, "usage_write", "ext_payment_outcome",
                    payment_id)
        self._get("payment", payment_id)
        _validate_choice(reported_status, PAYMENT_REPORTED_STATUSES,
                         "reported_status")
        _validate_optional_text(note, "note")
        return self._create(
            "payment_outcome", "pyo",
            {
                "payment_id": payment_id,
                "reported_status": reported_status,
                "note": note,
                "paid_here": False,
            },
            actor, "ext_payment_outcome",
        )

    def get_payment(self, payment_id, actor=None):
        """Read one payment record. Action: usage_read."""
        self._guard_read(actor, "usage_read", "ext_payment_read",
                         payment_id)
        return self._fetch("payment", payment_id)

    def list_payments(self, actor=None, project_id=None,
                      submission_id=None):
        """List payment records. Action: usage_read."""
        self._guard_read(actor, "usage_read", "ext_payment_read")
        return self._list("payment", project_id=project_id,
                          submission_id=submission_id)

    def list_payment_outcomes(self, actor=None, payment_id=None):
        """List payment-outcome records. Action: usage_read."""
        self._guard_read(actor, "usage_read", "ext_payment_read")
        return self._list("payment_outcome", payment_id=payment_id)

    def payment_view(self, payment_id, actor=None):
        """One payment record plus its derived
        ``current_reported_status``: the reported status of its
        latest outcome record, or ``"recorded"`` when no outcome
        has been reported. Derived at read, never stored.
        Action: usage_read."""
        self._guard_read(actor, "usage_read", "ext_payment_read",
                         payment_id)
        view = self._fetch("payment", payment_id)
        outcomes = self._list("payment_outcome", payment_id=payment_id)
        view["current_reported_status"] = (
            outcomes[-1]["reported_status"] if outcomes else "recorded"
        )
        return view

    def payments_summary(self, actor=None):
        """Derived payment counts and the sum of recorded
        amounts (integer cents): counts and sums of recorded
        values only. Derived at read, never stored.
        Action: report_read."""
        self._guard_read(actor, "report_read", "ext_payments_summary")
        payments = self._list("payment")
        outcomes = self._list("payment_outcome")
        by_reported_status = {}
        for outcome in outcomes:
            key = outcome["reported_status"]
            by_reported_status[key] = by_reported_status.get(key, 0) + 1
        return {
            "payments": len(payments),
            "total_recorded_cents": sum(
                p["amount_cents"] for p in payments),
            "outcomes": len(outcomes),
            "outcomes_by_reported_status": by_reported_status,
            "paid_here": False,
        }

    # -- Third-party integrations (reference stub) -----------------------
    # Labeled reference implementation: integration reference
    # records plus event reference records carrying reported
    # statuses. Every record carries reference_stub: True (event
    # references additionally reference_transport: True),
    # connected_here: False, and synced_here: False. Nothing
    # connects to, syncs with, or moves through any external
    # system.

    def register_integration_reference(self, integration_ref, kind,
                                       actor, scope_ref=None):
        """Register a reference record of a third-party
        integration. Action: work_write. Carries
        ``reference_stub: True``; the integration it names lives
        outside this build and is not connected here."""
        self._guard(actor, "work_write", "ext_integration_reference",
                    integration_ref)
        _validate_ref(integration_ref, "integration_ref")
        _validate_choice(kind, INTEGRATION_KINDS, "kind")
        if scope_ref is not None:
            _validate_ref(scope_ref, "scope_ref")
        return self._create(
            "integration_reference", "int",
            {
                "integration_ref": integration_ref,
                "kind": kind,
                "scope_ref": scope_ref,
                "reference_stub": True,
                "connected_here": False,
                "synced_here": False,
            },
            actor, "ext_integration_reference",
        )

    def record_integration_event_reference(self, integration_id,
                                           reported_status, actor,
                                           note=None):
        """Record a reference of an integration event **as
        reported** by the external system. Action: work_write.
        Carries ``reference_stub: True`` and
        ``reference_transport: True``; no data moved through
        this build."""
        self._guard(actor, "work_write", "ext_integration_event",
                    integration_id)
        self._get("integration_reference", integration_id)
        _validate_choice(reported_status, INTEGRATION_EVENT_STATUSES,
                         "reported_status")
        _validate_optional_text(note, "note")
        return self._create(
            "integration_event_reference", "iev",
            {
                "integration_id": integration_id,
                "reported_status": reported_status,
                "note": note,
                "reference_stub": True,
                "reference_transport": True,
                "connected_here": False,
                "synced_here": False,
            },
            actor, "ext_integration_event",
        )

    def get_integration_reference(self, integration_id, actor=None):
        """Read one integration reference record. Action:
        work_read."""
        self._guard_read(actor, "work_read", "ext_integration_read",
                         integration_id)
        return self._fetch("integration_reference", integration_id)

    def list_integration_references(self, actor=None, kind=None):
        """List integration reference records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_integration_read")
        return self._list("integration_reference", kind=kind)

    def list_integration_event_references(self, actor=None,
                                          integration_id=None):
        """List integration event reference records. Action:
        work_read."""
        self._guard_read(actor, "work_read", "ext_integration_read")
        return self._list("integration_event_reference",
                          integration_id=integration_id)
