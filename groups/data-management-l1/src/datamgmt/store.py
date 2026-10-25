"""Data management store: datasets, sources, ingestion, data quality,
access governance, retention policies, exports, and catalog search.

Clean-room implementation of the contract.

Permission convention (mirrors the communication group): store
methods take an ``actor``. When the actor is a User-like object (it
has a ``role`` attribute) the store calls
:func:`datamgmt.access.require` for the method's action *before* any
state change or id allocation, so a denied operation consumes no id
and changes nothing. Where a plain string is passed it carries
identity (for provenance) but no role, so there is nothing to enforce
against at this layer; the service layer, which knows the role
registry, is responsible for enforcement in that case -- and it
always passes User objects.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``ds-``, ``src-``, ``ing-``,
``qr-``, ``qc-``, ``ar-``, ``gr-``, ``rp-``, ``ex-``).

The store records every successful mutation and every search to its
audit log (when one is attached).
"""

import hashlib
import json
import re
import threading
from datetime import datetime, timedelta, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

CLASSIFICATIONS = ("public", "internal", "cui", "phi")
KNOWN_CLASSIFICATIONS = frozenset(CLASSIFICATIONS)
FIELD_TYPES = ("string", "integer", "number", "boolean", "date", "datetime")
KNOWN_FIELD_TYPES = frozenset(FIELD_TYPES)
SOURCE_KINDS = ("file", "database", "api", "stream", "manual")
KNOWN_SOURCE_KINDS = frozenset(SOURCE_KINDS)
INGEST_MODES = ("full", "incremental", "stream")
KNOWN_INGEST_MODES = frozenset(INGEST_MODES)
INGEST_STATUSES = ("completed", "failed")
KNOWN_INGEST_STATUSES = frozenset(INGEST_STATUSES)
QUALITY_KINDS = ("completeness", "uniqueness", "format", "range", "freshness")
KNOWN_QUALITY_KINDS = frozenset(QUALITY_KINDS)
DISPOSITIONS = ("delete", "archive", "review")
KNOWN_DISPOSITIONS = frozenset(DISPOSITIONS)
EXPORT_FORMATS = ("json", "csv")
KNOWN_EXPORT_FORMATS = frozenset(EXPORT_FORMATS)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _maybe_require(actor, action):
    """Enforce permissions when ``actor`` is a User-like object.

    Plain string actors carry identity (for provenance) but no role,
    so there is nothing to enforce against; enforcement for those
    happens in the service layer, which knows the role registry.
    """
    if actor is not None and hasattr(actor, "role"):
        require(actor, action)


def _require_actor(actor, action):
    """For writes: an actor must be present, then _maybe_require."""
    if actor is None:
        raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
    _maybe_require(actor, action)


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parse_iso_datetime(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 datetime string" % (what,))
    text = value.strip()
    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO-8601 datetime: %r" % (what, value)) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _coerce_now(now, what="now"):
    if now is None:
        return datetime.now(timezone.utc)
    if isinstance(now, datetime):
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now
    if isinstance(now, str):
        return _parse_iso_datetime(now, what)
    raise ValidationError("%s must be an ISO-8601 string or datetime" % (what,))


def _try_parse_datetime(value):
    """Parse ``value`` as a datetime, returning None when impossible."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        try:
            return _parse_iso_datetime(value, "value")
        except ValidationError:
            return None
    return None


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


def _validate_tags(tags):
    if tags is None:
        return []
    if not isinstance(tags, list):
        raise ValidationError("tags must be a list of non-empty strings")
    result = []
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip():
            raise ValidationError("each tag must be a non-empty string")
        result.append(tag)
    return result


def _validate_schema(schema):
    if schema is None:
        return []
    if not isinstance(schema, list):
        raise ValidationError("schema must be a list of field dicts")
    result = []
    seen = set()
    for field in schema:
        if not isinstance(field, dict):
            raise ValidationError("each schema field must be a dict")
        name = field.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("schema field name must be a non-empty string")
        if name in seen:
            raise ValidationError("duplicate schema field name: %r" % (name,))
        seen.add(name)
        ftype = field.get("type")
        if ftype not in KNOWN_FIELD_TYPES:
            raise ValidationError(
                "schema field type must be one of %s" % (", ".join(FIELD_TYPES),)
            )
        required = field.get("required", False)
        if not isinstance(required, bool):
            raise ValidationError("schema field required must be a bool")
        sensitive = field.get("sensitive", False)
        if not isinstance(sensitive, bool):
            raise ValidationError("schema field sensitive must be a bool")
        result.append(
            {"name": name, "type": ftype, "required": required, "sensitive": sensitive}
        )
    return result


def _validate_quality_params(kind, params):
    if kind in ("completeness", "uniqueness"):
        if params is None:
            return {}
        if not isinstance(params, dict):
            raise ValidationError("params must be a dict")
        return dict(params)
    if params is None or not isinstance(params, dict):
        raise ValidationError("params must be a dict for %s rules" % (kind,))
    if kind == "format":
        pattern = params.get("pattern")
        if not isinstance(pattern, str):
            raise ValidationError("format rules require params['pattern'] to be a string")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ValidationError(
                "format pattern is not a valid regex: %r" % (pattern,)
            ) from exc
    elif kind == "range":
        if "min" not in params and "max" not in params:
            raise ValidationError("range rules require at least one of params['min'] / params['max']")
        for key in ("min", "max"):
            if key in params and not _is_number(params[key]):
                raise ValidationError("range param %r must be numeric" % (key,))
    elif kind == "freshness":
        max_age = params.get("max_age_hours")
        if not _is_number(max_age) or max_age <= 0:
            raise ValidationError("freshness rules require params['max_age_hours'] to be a number > 0")
    return dict(params)


class DataMgmtStore:
    """In-memory store for the data management service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._datasets = {}
        self._sources = {}
        self._ingestions = {}
        self._quality_rules = {}
        self._quality_checks = {}
        self._access_requests = {}
        self._grants = {}
        self._retention_policies = {}
        self._exports = {}
        self._counters = {
            "ds": 0,
            "src": 0,
            "ing": 0,
            "qr": 0,
            "qc": 0,
            "ar": 0,
            "gr": 0,
            "rp": 0,
            "ex": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    @staticmethod
    def _copy_dataset(dataset):
        copied = dict(dataset)
        copied["tags"] = list(dataset["tags"])
        copied["schema"] = [dict(f) for f in dataset["schema"]]
        return copied

    @staticmethod
    def _copy_quality_rule(rule):
        copied = dict(rule)
        copied["params"] = dict(rule["params"])
        return copied

    def _get_dataset_record(self, dataset_id):
        dataset = self._datasets.get(dataset_id)
        if dataset is None:
            raise NotFoundError("dataset not found: %r" % (dataset_id,))
        return dataset

    def _get_source_record(self, source_id):
        source = self._sources.get(source_id)
        if source is None:
            raise NotFoundError("source not found: %r" % (source_id,))
        return source

    def _get_ingestion_record(self, ingestion_id):
        ingestion = self._ingestions.get(ingestion_id)
        if ingestion is None:
            raise NotFoundError("ingestion not found: %r" % (ingestion_id,))
        return ingestion

    def _get_quality_rule_record(self, rule_id):
        rule = self._quality_rules.get(rule_id)
        if rule is None:
            raise NotFoundError("quality rule not found: %r" % (rule_id,))
        return rule

    def _get_quality_check_record(self, check_id):
        check = self._quality_checks.get(check_id)
        if check is None:
            raise NotFoundError("quality check not found: %r" % (check_id,))
        return check

    def _get_access_request_record(self, request_id):
        request = self._access_requests.get(request_id)
        if request is None:
            raise NotFoundError("access request not found: %r" % (request_id,))
        return request

    def _get_grant_record(self, grant_id):
        grant = self._grants.get(grant_id)
        if grant is None:
            raise NotFoundError("grant not found: %r" % (grant_id,))
        return grant

    def _get_retention_policy_record(self, policy_id):
        policy = self._retention_policies.get(policy_id)
        if policy is None:
            raise NotFoundError("retention policy not found: %r" % (policy_id,))
        return policy

    def _get_export_record(self, export_id):
        export = self._exports.get(export_id)
        if export is None:
            raise NotFoundError("export not found: %r" % (export_id,))
        return export

    # -- datasets ------------------------------------------------------

    def create_dataset(self, name, description, actor, owner=None,
                       classification="internal", tags=None, schema=None):
        """Create a dataset. Action: dataset_write."""
        _require_actor(actor, "dataset_write")
        _validate_non_empty(name, "dataset name")
        _validate_non_empty(description, "dataset description")
        if classification not in KNOWN_CLASSIFICATIONS:
            raise ValidationError(
                "classification must be one of %s" % (", ".join(CLASSIFICATIONS),)
            )
        if owner is not None:
            _validate_non_empty(owner, "owner")
        clean_tags = _validate_tags(tags)
        clean_schema = _validate_schema(schema)
        with self._lock:
            dataset_id = self._next_id("ds")
            now = _utc_now()
            dataset = {
                "id": dataset_id,
                "name": name,
                "description": description,
                "owner": owner or actor_name(actor),
                "classification": classification,
                "tags": clean_tags,
                "schema": clean_schema,
                "schema_version": 1,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._datasets[dataset_id] = dataset
            self._audit(actor, "dataset_create", dataset_id, details={"name": name})
            return self._copy_dataset(dataset)

    def get_dataset(self, dataset_id, actor=None):
        """Return one dataset. Action: dataset_read."""
        _maybe_require(actor, "dataset_read")
        with self._lock:
            return self._copy_dataset(self._get_dataset_record(dataset_id))

    def list_datasets(self, actor=None):
        """Return datasets sorted by id. Action: dataset_read."""
        _maybe_require(actor, "dataset_read")
        with self._lock:
            datasets = sorted(self._datasets.values(), key=lambda d: _id_num(d["id"]))
            return [self._copy_dataset(d) for d in datasets]

    def update_dataset(self, dataset_id, actor, description=None, tags=None,
                       classification=None):
        """Update a dataset's mutable fields. Action: dataset_write."""
        _require_actor(actor, "dataset_write")
        if description is not None:
            _validate_non_empty(description, "dataset description")
        clean_tags = None
        if tags is not None:
            clean_tags = _validate_tags(tags)
        if classification is not None and classification not in KNOWN_CLASSIFICATIONS:
            raise ValidationError(
                "classification must be one of %s" % (", ".join(CLASSIFICATIONS),)
            )
        with self._lock:
            dataset = self._get_dataset_record(dataset_id)
            if description is not None:
                dataset["description"] = description
            if clean_tags is not None:
                dataset["tags"] = clean_tags
            if classification is not None:
                dataset["classification"] = classification
            dataset["updated_utc"] = _utc_now()
            self._audit(actor, "dataset_update", dataset_id)
            return self._copy_dataset(dataset)

    def update_schema(self, dataset_id, schema, actor):
        """Replace a dataset's schema. Action: dataset_write."""
        _require_actor(actor, "dataset_write")
        clean_schema = _validate_schema(schema)
        with self._lock:
            dataset = self._get_dataset_record(dataset_id)
            dataset["schema"] = clean_schema
            dataset["schema_version"] += 1
            dataset["updated_utc"] = _utc_now()
            self._audit(actor, "schema_update", dataset_id,
                        details={"schema_version": dataset["schema_version"]})
            return self._copy_dataset(dataset)

    # -- sources ---------------------------------------------------------

    def register_source(self, name, kind, actor, location=None):
        """Register a data source. Action: source_write."""
        _require_actor(actor, "source_write")
        _validate_non_empty(name, "source name")
        if kind not in KNOWN_SOURCE_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(SOURCE_KINDS),)
            )
        if location is not None and not isinstance(location, str):
            raise ValidationError("location must be a string")
        with self._lock:
            source_id = self._next_id("src")
            source = {
                "id": source_id,
                "name": name,
                "kind": kind,
                "location": location,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._sources[source_id] = source
            self._audit(actor, "source_register", source_id,
                        details={"name": name, "kind": kind})
            return dict(source)

    def get_source(self, source_id, actor=None):
        """Return one source. Action: source_read."""
        _maybe_require(actor, "source_read")
        with self._lock:
            return dict(self._get_source_record(source_id))

    def list_sources(self, actor=None):
        """Return sources sorted by id. Action: source_read."""
        _maybe_require(actor, "source_read")
        with self._lock:
            sources = sorted(self._sources.values(), key=lambda s: _id_num(s["id"]))
            return [dict(s) for s in sources]

    # -- ingestion ---------------------------------------------------------

    def record_ingestion(self, dataset_id, source_id, actor, mode="full",
                         record_count=0, checksum=None, status="completed",
                         notes=None):
        """Record an ingestion run. Action: ingest_record."""
        _require_actor(actor, "ingest_record")
        if mode not in KNOWN_INGEST_MODES:
            raise ValidationError(
                "mode must be one of %s" % (", ".join(INGEST_MODES),)
            )
        if status not in KNOWN_INGEST_STATUSES:
            raise ValidationError(
                "status must be one of %s" % (", ".join(INGEST_STATUSES),)
            )
        if not _is_int(record_count) or record_count < 0:
            raise ValidationError("record_count must be an integer >= 0")
        if checksum is not None and not isinstance(checksum, str):
            raise ValidationError("checksum must be a string")
        if notes is not None and not isinstance(notes, str):
            raise ValidationError("notes must be a string")
        with self._lock:
            self._get_dataset_record(dataset_id)
            self._get_source_record(source_id)
            ingestion_id = self._next_id("ing")
            ingestion = {
                "id": ingestion_id,
                "dataset_id": dataset_id,
                "source_id": source_id,
                "mode": mode,
                "record_count": record_count,
                "checksum": checksum,
                "status": status,
                "notes": notes,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._ingestions[ingestion_id] = ingestion
            self._audit(actor, "ingestion_record", ingestion_id,
                        details={"dataset_id": dataset_id, "source_id": source_id})
            return dict(ingestion)

    def get_ingestion(self, ingestion_id, actor=None):
        """Return one ingestion. Action: ingest_read."""
        _maybe_require(actor, "ingest_read")
        with self._lock:
            return dict(self._get_ingestion_record(ingestion_id))

    def list_ingestions(self, dataset_id=None, actor=None):
        """Return ingestions sorted by id. Action: ingest_read."""
        _maybe_require(actor, "ingest_read")
        with self._lock:
            if dataset_id is not None:
                self._get_dataset_record(dataset_id)
            ingestions = sorted(
                self._ingestions.values(), key=lambda i: _id_num(i["id"])
            )
            return [
                dict(i) for i in ingestions
                if dataset_id is None or i["dataset_id"] == dataset_id
            ]

    def dataset_provenance(self, dataset_id, actor=None):
        """Provenance for a dataset. Action: ingest_read."""
        _maybe_require(actor, "ingest_read")
        with self._lock:
            self._get_dataset_record(dataset_id)
            ingestions = sorted(
                (i for i in self._ingestions.values()
                 if i["dataset_id"] == dataset_id),
                key=lambda i: _id_num(i["id"]),
            )
            source_ids = sorted(
                {i["source_id"] for i in ingestions}, key=_id_num
            )
            sources = [
                dict(self._sources[sid]) for sid in source_ids
                if sid in self._sources
            ]
            sources.sort(key=lambda s: _id_num(s["id"]))
            total_records = sum(
                i["record_count"] for i in ingestions if i["status"] == "completed"
            )
            return {
                "dataset_id": dataset_id,
                "sources": sources,
                "ingestions": [dict(i) for i in ingestions],
                "total_records": total_records,
            }

    # -- quality -----------------------------------------------------------

    def create_quality_rule(self, dataset_id, name, kind, field, actor, params=None):
        """Create a quality rule for a dataset. Action: quality_write."""
        _require_actor(actor, "quality_write")
        _validate_non_empty(name, "quality rule name")
        if kind not in KNOWN_QUALITY_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(QUALITY_KINDS),)
            )
        _validate_non_empty(field, "field")
        clean_params = _validate_quality_params(kind, params)
        with self._lock:
            self._get_dataset_record(dataset_id)
            rule_id = self._next_id("qr")
            rule = {
                "id": rule_id,
                "dataset_id": dataset_id,
                "name": name,
                "kind": kind,
                "field": field,
                "params": clean_params,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._quality_rules[rule_id] = rule
            self._audit(actor, "quality_rule_create", rule_id,
                        details={"dataset_id": dataset_id, "kind": kind})
            return self._copy_quality_rule(rule)

    def get_quality_rule(self, rule_id, actor=None):
        """Return one quality rule. Action: quality_read."""
        _maybe_require(actor, "quality_read")
        with self._lock:
            return self._copy_quality_rule(self._get_quality_rule_record(rule_id))

    def list_quality_rules(self, dataset_id=None, actor=None):
        """Return quality rules sorted by id. Action: quality_read."""
        _maybe_require(actor, "quality_read")
        with self._lock:
            if dataset_id is not None:
                self._get_dataset_record(dataset_id)
            rules = sorted(
                self._quality_rules.values(), key=lambda r: _id_num(r["id"])
            )
            return [
                self._copy_quality_rule(r) for r in rules
                if dataset_id is None or r["dataset_id"] == dataset_id
            ]

    def run_quality_check(self, rule_id, records, actor, now=None):
        """Run a quality rule over ``records``. Action: quality_run."""
        _require_actor(actor, "quality_run")
        if not isinstance(records, list):
            raise ValidationError("records must be a list of dicts")
        for record in records:
            if not isinstance(record, dict):
                raise ValidationError("each record must be a dict")
        now_dt = _coerce_now(now)
        with self._lock:
            rule = self._get_quality_rule_record(rule_id)
            kind = rule["kind"]
            field = rule["field"]
            params = rule["params"]
            violations = 0
            seen = []
            for record in records:
                present = field in record
                value = record.get(field) if present else None
                if kind == "completeness":
                    if not present or value is None or value == "":
                        violations += 1
                elif kind == "uniqueness":
                    if present and value is not None:
                        if any(value == s for s in seen):
                            violations += 1
                        else:
                            seen.append(value)
                elif kind == "format":
                    if not present or value is None:
                        violations += 1
                    elif re.fullmatch(params["pattern"], str(value)) is None:
                        violations += 1
                elif kind == "range":
                    if (not present or value is None or isinstance(value, bool)
                            or not isinstance(value, (int, float))):
                        violations += 1
                    elif ("min" in params and value < params["min"]) or (
                            "max" in params and value > params["max"]):
                        violations += 1
                elif kind == "freshness":
                    parsed = _try_parse_datetime(value) if present else None
                    if parsed is None:
                        violations += 1
                    else:
                        age_hours = (now_dt - parsed).total_seconds() / 3600.0
                        if age_hours > params["max_age_hours"]:
                            violations += 1
            check_id = self._next_id("qc")
            passed = violations == 0
            check = {
                "id": check_id,
                "rule_id": rule_id,
                "dataset_id": rule["dataset_id"],
                "checked_utc": now_dt.isoformat(),
                "records_checked": len(records),
                "violations": violations,
                "passed": passed,
                "kind": kind,
                "field": field,
            }
            self._quality_checks[check_id] = check
            self._audit(actor, "quality_check_run", check_id,
                        details={"rule_id": rule_id, "violations": violations,
                                 "passed": passed})
            return dict(check)

    def get_quality_check(self, check_id, actor=None):
        """Return one quality check. Action: quality_read."""
        _maybe_require(actor, "quality_read")
        with self._lock:
            return dict(self._get_quality_check_record(check_id))

    def list_quality_checks(self, rule_id=None, dataset_id=None, actor=None):
        """Return quality checks sorted by id. Action: quality_read."""
        _maybe_require(actor, "quality_read")
        with self._lock:
            if rule_id is not None:
                self._get_quality_rule_record(rule_id)
            if dataset_id is not None:
                self._get_dataset_record(dataset_id)
            checks = sorted(
                self._quality_checks.values(), key=lambda c: _id_num(c["id"])
            )
            return [
                dict(c) for c in checks
                if (rule_id is None or c["rule_id"] == rule_id)
                and (dataset_id is None or c["dataset_id"] == dataset_id)
            ]

    # -- access governance ---------------------------------------------------

    def request_access(self, dataset_id, purpose, actor, duration_days=30):
        """Request access to a dataset. Action: access_request."""
        _require_actor(actor, "access_request")
        _validate_non_empty(purpose, "purpose")
        if not _is_int(duration_days) or duration_days < 1 or duration_days > 365:
            raise ValidationError("duration_days must be an integer between 1 and 365")
        with self._lock:
            self._get_dataset_record(dataset_id)
            requester = actor_name(actor)
            for existing in self._access_requests.values():
                if (existing["dataset_id"] == dataset_id
                        and existing["requester"] == requester
                        and existing["status"] == "requested"):
                    raise ValidationError(
                        "an open access request already exists for requester %r "
                        "on dataset %r" % (requester, dataset_id)
                    )
            request_id = self._next_id("ar")
            request = {
                "id": request_id,
                "dataset_id": dataset_id,
                "requester": requester,
                "purpose": purpose,
                "duration_days": duration_days,
                "status": "requested",
                "reason": None,
                "created_utc": _utc_now(),
                "decided_by": None,
                "decided_utc": None,
                "grant_id": None,
            }
            self._access_requests[request_id] = request
            self._audit(actor, "access_request", request_id,
                        details={"dataset_id": dataset_id})
            return dict(request)

    def _check_decider_not_requester(self, request, actor):
        if actor_name(actor) == request["requester"]:
            raise PermissionDenied("decider may not be the requester")

    def decide_access_request(self, request_id, approve, actor, reason=None):
        """Decide an access request. Action: access_decide."""
        _require_actor(actor, "access_decide")
        with self._lock:
            request = self._get_access_request_record(request_id)
            self._check_decider_not_requester(request, actor)
            if request["status"] != "requested":
                raise ValidationError(
                    "access request %r has already been decided (status is %r)"
                    % (request_id, request["status"])
                )
            if not isinstance(approve, bool):
                raise ValidationError("approve must be a bool")
            if reason is not None and not isinstance(reason, str):
                raise ValidationError("reason must be a string")
            now_dt = datetime.now(timezone.utc)
            now = now_dt.isoformat()
            grant_id = None
            if approve:
                grant_id = self._next_id("gr")
                grant = {
                    "id": grant_id,
                    "dataset_id": request["dataset_id"],
                    "grantee": request["requester"],
                    "purpose": request["purpose"],
                    "granted_by": actor_name(actor),
                    "created_utc": now,
                    "expires_utc": (
                        now_dt + timedelta(days=request["duration_days"])
                    ).isoformat(),
                    "revoked": False,
                    "revoked_utc": None,
                }
                self._grants[grant_id] = grant
                request["status"] = "approved"
                request["grant_id"] = grant_id
            else:
                request["status"] = "denied"
            request["decided_by"] = actor_name(actor)
            request["decided_utc"] = now
            request["reason"] = reason
            self._audit(actor, "access_decide", request_id,
                        details={"approve": approve, "grant_id": grant_id})
            return dict(request)

    def get_access_request(self, request_id, actor=None):
        """Return one access request. Action: access_read."""
        _maybe_require(actor, "access_read")
        with self._lock:
            return dict(self._get_access_request_record(request_id))

    def list_access_requests(self, dataset_id=None, actor=None):
        """Return access requests sorted by id. Action: access_read."""
        _maybe_require(actor, "access_read")
        with self._lock:
            if dataset_id is not None:
                self._get_dataset_record(dataset_id)
            requests = sorted(
                self._access_requests.values(), key=lambda r: _id_num(r["id"])
            )
            return [
                dict(r) for r in requests
                if dataset_id is None or r["dataset_id"] == dataset_id
            ]

    def get_grant(self, grant_id, actor=None):
        """Return one grant. Action: access_read."""
        _maybe_require(actor, "access_read")
        with self._lock:
            return dict(self._get_grant_record(grant_id))

    def list_grants(self, dataset_id=None, grantee=None, actor=None):
        """Return grants sorted by id. Action: access_read."""
        _maybe_require(actor, "access_read")
        with self._lock:
            if dataset_id is not None:
                self._get_dataset_record(dataset_id)
            grants = sorted(self._grants.values(), key=lambda g: _id_num(g["id"]))
            return [
                dict(g) for g in grants
                if (dataset_id is None or g["dataset_id"] == dataset_id)
                and (grantee is None or g["grantee"] == grantee)
            ]

    def revoke_grant(self, grant_id, actor):
        """Revoke a grant. Action: access_decide."""
        _require_actor(actor, "access_decide")
        with self._lock:
            grant = self._get_grant_record(grant_id)
            if grant["revoked"]:
                raise ValidationError("grant %r is already revoked" % (grant_id,))
            grant["revoked"] = True
            grant["revoked_utc"] = _utc_now()
            self._audit(actor, "grant_revoke", grant_id)
            return dict(grant)

    def active_grants(self, dataset_id, actor=None, now=None):
        """Return unrevoked, unexpired grants for a dataset.

        Action: access_read.
        """
        _maybe_require(actor, "access_read")
        now_dt = _coerce_now(now)
        with self._lock:
            self._get_dataset_record(dataset_id)
            grants = sorted(self._grants.values(), key=lambda g: _id_num(g["id"]))
            result = []
            for grant in grants:
                if grant["dataset_id"] != dataset_id:
                    continue
                if grant["revoked"]:
                    continue
                expires = _parse_iso_datetime(grant["expires_utc"], "expires_utc")
                if expires > now_dt:
                    result.append(dict(grant))
            return result

    # -- retention -------------------------------------------------------------

    def set_retention_policy(self, dataset_id, retention_days, disposition,
                             actor, legal_hold=False):
        """Set the retention policy for a dataset. Action: retention_write."""
        _require_actor(actor, "retention_write")
        if not _is_int(retention_days) or retention_days <= 0:
            raise ValidationError("retention_days must be an integer > 0")
        if disposition not in KNOWN_DISPOSITIONS:
            raise ValidationError(
                "disposition must be one of %s" % (", ".join(DISPOSITIONS),)
            )
        if not isinstance(legal_hold, bool):
            raise ValidationError("legal_hold must be a bool")
        with self._lock:
            self._get_dataset_record(dataset_id)
            for existing in self._retention_policies.values():
                if existing["dataset_id"] == dataset_id:
                    raise ValidationError(
                        "a retention policy already exists for dataset %r"
                        % (dataset_id,)
                    )
            policy_id = self._next_id("rp")
            now = _utc_now()
            policy = {
                "id": policy_id,
                "dataset_id": dataset_id,
                "retention_days": retention_days,
                "disposition": disposition,
                "legal_hold": legal_hold,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._retention_policies[policy_id] = policy
            self._audit(actor, "retention_set", policy_id,
                        details={"dataset_id": dataset_id})
            return dict(policy)

    def update_retention_policy(self, policy_id, actor, retention_days=None,
                                disposition=None, legal_hold=None):
        """Update a retention policy. Action: retention_write."""
        _require_actor(actor, "retention_write")
        if retention_days is not None and (
                not _is_int(retention_days) or retention_days <= 0):
            raise ValidationError("retention_days must be an integer > 0")
        if disposition is not None and disposition not in KNOWN_DISPOSITIONS:
            raise ValidationError(
                "disposition must be one of %s" % (", ".join(DISPOSITIONS),)
            )
        if legal_hold is not None and not isinstance(legal_hold, bool):
            raise ValidationError("legal_hold must be a bool")
        with self._lock:
            policy = self._get_retention_policy_record(policy_id)
            if retention_days is not None:
                policy["retention_days"] = retention_days
            if disposition is not None:
                policy["disposition"] = disposition
            if legal_hold is not None:
                policy["legal_hold"] = legal_hold
            policy["updated_utc"] = _utc_now()
            self._audit(actor, "retention_update", policy_id)
            return dict(policy)

    def get_retention_policy(self, policy_id, actor=None):
        """Return one retention policy. Action: retention_read."""
        _maybe_require(actor, "retention_read")
        with self._lock:
            return dict(self._get_retention_policy_record(policy_id))

    def retention_policy_for(self, dataset_id, actor=None):
        """Return the policy for a dataset, or None. Action: retention_read."""
        _maybe_require(actor, "retention_read")
        with self._lock:
            for policy in self._retention_policies.values():
                if policy["dataset_id"] == dataset_id:
                    return dict(policy)
            return None

    def list_retention_policies(self, actor=None):
        """Return retention policies sorted by id. Action: retention_read."""
        _maybe_require(actor, "retention_read")
        with self._lock:
            policies = sorted(
                self._retention_policies.values(), key=lambda p: _id_num(p["id"])
            )
            return [dict(p) for p in policies]

    def retention_due(self, actor=None, now=None):
        """Return datasets past their retention period. Action: retention_read."""
        _maybe_require(actor, "retention_read")
        now_dt = _coerce_now(now)
        with self._lock:
            due = []
            policies = sorted(
                self._retention_policies.values(),
                key=lambda p: _id_num(p["dataset_id"]),
            )
            for policy in policies:
                if policy["legal_hold"]:
                    continue
                dataset_id = policy["dataset_id"]
                dataset = self._datasets.get(dataset_id)
                if dataset is None:
                    continue
                reference_utc = dataset["created_utc"]
                latest = None
                latest_key = None
                for ingestion in self._ingestions.values():
                    if ingestion["dataset_id"] != dataset_id:
                        continue
                    if ingestion["status"] != "completed":
                        continue
                    parsed = _parse_iso_datetime(ingestion["created_utc"], "created_utc")
                    key = (parsed, _id_num(ingestion["id"]))
                    if latest_key is None or key > latest_key:
                        latest_key = key
                        latest = ingestion
                if latest is not None:
                    reference_utc = latest["created_utc"]
                reference_dt = _parse_iso_datetime(reference_utc, "reference_utc")
                age_days = (now_dt - reference_dt).days
                if age_days > policy["retention_days"]:
                    due.append({
                        "dataset_id": dataset_id,
                        "policy_id": policy["id"],
                        "disposition": policy["disposition"],
                        "legal_hold": False,
                        "reference_utc": reference_utc,
                        "age_days": age_days,
                    })
            due.sort(key=lambda d: _id_num(d["dataset_id"]))
            return due

    # -- export ------------------------------------------------------------------

    def export_dataset(self, dataset_id, actor, format="json", records=None):
        """Export a dataset. Action: export."""
        _require_actor(actor, "export")
        if format not in KNOWN_EXPORT_FORMATS:
            raise ValidationError(
                "format must be one of %s" % (", ".join(EXPORT_FORMATS),)
            )
        if records is not None:
            if not isinstance(records, list):
                raise ValidationError("records must be a list of dicts")
            for record in records:
                if not isinstance(record, dict):
                    raise ValidationError("each record must be a dict")
        with self._lock:
            dataset = self._get_dataset_record(dataset_id)
            if records is not None:
                checksum = hashlib.sha256(
                    json.dumps(records, sort_keys=True,
                               separators=(",", ":")).encode()
                ).hexdigest()
                record_count = len(records)
            else:
                checksum = None
                record_count = sum(
                    i["record_count"] for i in self._ingestions.values()
                    if i["dataset_id"] == dataset_id and i["status"] == "completed"
                )
            export_id = self._next_id("ex")
            export = {
                "id": export_id,
                "dataset_id": dataset_id,
                "format": format,
                "record_count": record_count,
                "checksum": checksum,
                "schema_version": dataset["schema_version"],
                "exported_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._exports[export_id] = export
            self._audit(actor, "export_create", export_id,
                        details={"dataset_id": dataset_id, "format": format})
            return dict(export)

    def get_export(self, export_id, actor=None):
        """Return one export. Action: dataset_read."""
        _maybe_require(actor, "dataset_read")
        with self._lock:
            return dict(self._get_export_record(export_id))

    def list_exports(self, dataset_id=None, actor=None):
        """Return exports sorted by id. Action: dataset_read."""
        _maybe_require(actor, "dataset_read")
        with self._lock:
            if dataset_id is not None:
                self._get_dataset_record(dataset_id)
            exports = sorted(self._exports.values(), key=lambda e: _id_num(e["id"]))
            return [
                dict(e) for e in exports
                if dataset_id is None or e["dataset_id"] == dataset_id
            ]

    # -- search --------------------------------------------------------------------

    def search(self, query_text, actor=None):
        """Literal case-insensitive substring search.

        Over datasets (name, description, tags, schema field names),
        sources (name, kind, location), and quality rules (name,
        field, kind). Returns {datasets, sources, quality_rules}.
        Action: catalog_read. Records a 'search' audit entry.
        """
        _maybe_require(actor, "catalog_read")
        if not isinstance(query_text, str):
            raise ValidationError("query must be a string")
        stripped = query_text.strip()
        needle = stripped.lower()
        with self._lock:
            if not stripped:
                result = {"datasets": [], "sources": [], "quality_rules": []}
            else:
                datasets = []
                for dataset in self._datasets.values():
                    haystacks = [
                        dataset["name"].lower(),
                        dataset["description"].lower(),
                        " ".join(dataset["tags"]).lower(),
                    ]
                    haystacks.extend(
                        f["name"].lower() for f in dataset["schema"]
                    )
                    if any(needle in h for h in haystacks):
                        datasets.append(dataset)
                datasets.sort(key=lambda d: _id_num(d["id"]))
                sources = []
                for source in self._sources.values():
                    haystacks = [
                        source["name"].lower(),
                        source["kind"].lower(),
                        (source["location"] or "").lower(),
                    ]
                    if any(needle in h for h in haystacks):
                        sources.append(source)
                sources.sort(key=lambda s: _id_num(s["id"]))
                rules = []
                for rule in self._quality_rules.values():
                    haystacks = [
                        rule["name"].lower(),
                        rule["field"].lower(),
                        rule["kind"].lower(),
                    ]
                    if any(needle in h for h in haystacks):
                        rules.append(rule)
                rules.sort(key=lambda r: _id_num(r["id"]))
                result = {
                    "datasets": [self._copy_dataset(d) for d in datasets],
                    "sources": [dict(s) for s in sources],
                    "quality_rules": [self._copy_quality_rule(r) for r in rules],
                }
            self._audit(actor, "search", query_text, details={"query": query_text})
            return result
