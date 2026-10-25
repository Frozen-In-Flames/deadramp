"""Development-tools records store: project registry, issue tracking
with a lifecycle, code-review records, build records, release records,
artifact registry with checksums, environment & deployment records,
and search over the records.

Clean-room implementation. Records only: there is no CI execution,
no git hosting, no compiler, and no merge engine in this substrate.

Permission convention: store methods take an ``actor``. When the
actor is a User-like object (it has a ``role`` attribute) the store
calls :func:`devtools.access.require` for the method's action *before*
any state change or id allocation, so a denied operation consumes no
id and changes nothing, and the denied attempt is audited. Where a
plain string is passed it carries identity (for provenance) but no
role, so there is nothing to enforce against at this layer; the
service layer, which knows the role registry, is responsible for
enforcement in that case -- and it always passes User objects.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type: ``prj-``, ``iss-``, ``rev-``, ``bld-``, ``rel-``,
``art-``, ``env-``, ``dep-``.
"""

import hashlib
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

BUILD_STATUSES = ("queued", "running", "succeeded", "failed")
DEPLOYMENT_STATUSES = ("deployed", "failed", "rolled_back")

ISSUE_TRANSITIONS = {
    "open": {"in_progress", "closed"},
    "in_progress": {"resolved", "open"},
    "resolved": {"closed", "open"},
    "closed": {"open"},
}

REVIEW_TRANSITIONS = {
    "open": {"approved", "changes_requested", "closed"},
    "changes_requested": {"open", "closed"},
    "approved": {"merged", "closed"},
    "merged": set(),
    "closed": set(),
}


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_optional_str(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _content_bytes(content):
    if isinstance(content, str):
        return content.encode("utf-8")
    if isinstance(content, (bytes, bytearray)):
        return bytes(content)
    raise ValidationError("content must be a string or bytes")


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class DevToolsStore:
    """In-memory store for the development-tools records service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._projects = {}
        self._issues = {}
        self._reviews = {}
        self._builds = {}
        self._releases = {}
        self._artifacts = {}
        self._environments = {}
        self._deployments = {}
        self._counters = {
            "prj": 0, "iss": 0, "rev": 0, "bld": 0,
            "rel": 0, "art": 0, "env": 0, "dep": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _enforce(self, actor, action, target):
        """Enforce for a User actor; audit the denied attempt, then raise."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit(actor, "%s:denied" % (action,), target)
                raise

    def _require_actor(self, actor, action, target):
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
        self._enforce(actor, action, target)

    def _maybe_require(self, actor, action):
        if actor is not None and hasattr(actor, "role"):
            require(actor, action)

    def _get_project_record(self, project_id):
        rec = self._projects.get(project_id)
        if rec is None:
            raise NotFoundError("project not found: %r" % (project_id,))
        return rec

    def _get_issue_record(self, issue_id):
        rec = self._issues.get(issue_id)
        if rec is None:
            raise NotFoundError("issue not found: %r" % (issue_id,))
        return rec

    def _get_review_record(self, review_id):
        rec = self._reviews.get(review_id)
        if rec is None:
            raise NotFoundError("review not found: %r" % (review_id,))
        return rec

    def _get_build_record(self, build_id):
        rec = self._builds.get(build_id)
        if rec is None:
            raise NotFoundError("build not found: %r" % (build_id,))
        return rec

    def _get_release_record(self, release_id):
        rec = self._releases.get(release_id)
        if rec is None:
            raise NotFoundError("release not found: %r" % (release_id,))
        return rec

    def _get_artifact_record(self, artifact_id):
        rec = self._artifacts.get(artifact_id)
        if rec is None:
            raise NotFoundError("artifact not found: %r" % (artifact_id,))
        return rec

    def _get_environment_record(self, environment_id):
        rec = self._environments.get(environment_id)
        if rec is None:
            raise NotFoundError("environment not found: %r" % (environment_id,))
        return rec

    @staticmethod
    def _copy_build(record):
        copied = dict(record)
        if isinstance(copied.get("config"), dict):
            copied["config"] = dict(copied["config"])
        return copied

    # -- projects ------------------------------------------------------

    def create_project(self, name, actor, description=None, repo_url=None):
        """Create a project registry entry. Action: project_write."""
        self._require_actor(actor, "project_write", name if isinstance(name, str) else "project")
        _validate_non_empty(name, "project name")
        _validate_optional_str(description, "description")
        _validate_optional_str(repo_url, "repo_url")
        with self._lock:
            project_id = self._next_id("prj")
            record = {
                "id": project_id,
                "name": name,
                "description": description,
                "repo_url": repo_url,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._projects[project_id] = record
            self._audit(actor, "project_create", project_id, details={"name": name})
            return dict(record)

    def get_project(self, project_id, actor=None):
        """Return one project. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            return dict(self._get_project_record(project_id))

    def list_projects(self, actor=None):
        """Return projects sorted by id. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            records = sorted(self._projects.values(), key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    # -- issues --------------------------------------------------------

    def create_issue(self, project_id, title, actor, description=None, kind="issue", priority="medium"):
        """Create an issue record. Action: issue_write."""
        self._require_actor(actor, "issue_write", project_id)
        _validate_non_empty(title, "issue title")
        _validate_optional_str(description, "description")
        _validate_non_empty(kind, "kind")
        _validate_non_empty(priority, "priority")
        with self._lock:
            self._get_project_record(project_id)
            issue_id = self._next_id("iss")
            now = _utc_now()
            record = {
                "id": issue_id,
                "project_id": project_id,
                "title": title,
                "description": description,
                "kind": kind,
                "priority": priority,
                "status": "open",
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._issues[issue_id] = record
            self._audit(actor, "issue_create", issue_id, details={"project_id": project_id, "title": title})
            return dict(record)

    def get_issue(self, issue_id, actor=None):
        """Return one issue. Action: issue_read."""
        self._maybe_require(actor, "issue_read")
        with self._lock:
            return dict(self._get_issue_record(issue_id))

    def list_issues(self, project_id=None, status=None, actor=None):
        """Return issues, optionally filtered. Action: issue_read."""
        self._maybe_require(actor, "issue_read")
        with self._lock:
            records = sorted(self._issues.values(), key=lambda r: _id_num(r["id"]))
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            if status is not None:
                records = [r for r in records if r["status"] == status]
            return [dict(r) for r in records]

    def set_issue_status(self, issue_id, status, actor):
        """Transition an issue status. Action: issue_write.

        Lifecycle ONLY: open->{in_progress, closed},
        in_progress->{resolved, open}, resolved->{closed, open},
        closed->{open}. Any other transition (incl. same-state and
        unknown status) is a ValidationError, state unchanged.

        MUTATION DRILL NOTE: this gate is the load-bearing invariant
        for the negative-control drill.
        """
        self._require_actor(actor, "issue_write", issue_id)
        with self._lock:
            record = self._get_issue_record(issue_id)
            allowed = ISSUE_TRANSITIONS.get(record["status"], set())
            if status not in allowed:
                raise ValidationError(
                    "issue status transition %r -> %r is not allowed" % (record["status"], status)
                )
            record["status"] = status
            record["updated_utc"] = _utc_now()
            self._audit(actor, "issue_set_status", issue_id, details={"status": status})
            return dict(record)

    # -- reviews -------------------------------------------------------

    def create_review(self, project_id, title, actor, source_ref=None):
        """Create a code-review record. Action: review_write. Records only."""
        self._require_actor(actor, "review_write", project_id)
        _validate_non_empty(title, "review title")
        _validate_optional_str(source_ref, "source_ref")
        with self._lock:
            self._get_project_record(project_id)
            review_id = self._next_id("rev")
            record = {
                "id": review_id,
                "project_id": project_id,
                "title": title,
                "source_ref": source_ref,
                "state": "open",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._reviews[review_id] = record
            self._audit(actor, "review_create", review_id, details={"project_id": project_id})
            return dict(record)

    def get_review(self, review_id, actor=None):
        """Return one review record. Action: review_read."""
        self._maybe_require(actor, "review_read")
        with self._lock:
            return dict(self._get_review_record(review_id))

    def list_reviews(self, project_id=None, actor=None):
        """Return review records, optionally filtered. Action: review_read."""
        self._maybe_require(actor, "review_read")
        with self._lock:
            records = sorted(self._reviews.values(), key=lambda r: _id_num(r["id"]))
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            return [dict(r) for r in records]

    def set_review_state(self, review_id, state, actor):
        """Transition a review state. Action: review_write.

        Transitions ONLY: open->{approved, changes_requested, closed},
        changes_requested->{open, closed}, approved->{merged, closed};
        merged/closed are terminal. Else ValidationError.
        """
        self._require_actor(actor, "review_write", review_id)
        with self._lock:
            record = self._get_review_record(review_id)
            allowed = REVIEW_TRANSITIONS.get(record["state"], set())
            if state not in allowed:
                raise ValidationError(
                    "review state transition %r -> %r is not allowed" % (record["state"], state)
                )
            record["state"] = state
            self._audit(actor, "review_set_state", review_id, details={"state": state})
            return dict(record)

    # -- builds --------------------------------------------------------

    def record_build(self, project_id, actor, ref=None, status="succeeded", config=None):
        """Record a build. Action: build_write. Records only — nothing executes."""
        self._require_actor(actor, "build_write", project_id)
        _validate_optional_str(ref, "ref")
        if status not in BUILD_STATUSES:
            raise ValidationError("status must be one of %s" % (", ".join(BUILD_STATUSES),))
        if config is not None and not isinstance(config, dict):
            raise ValidationError("config must be an object")
        with self._lock:
            self._get_project_record(project_id)
            build_id = self._next_id("bld")
            record = {
                "id": build_id,
                "project_id": project_id,
                "ref": ref,
                "status": status,
                "config": dict(config) if isinstance(config, dict) else config,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._builds[build_id] = record
            self._audit(actor, "build_record", build_id, details={"project_id": project_id, "status": status})
            return self._copy_build(record)

    def get_build(self, build_id, actor=None):
        """Return one build record. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            return self._copy_build(self._get_build_record(build_id))

    def list_builds(self, project_id=None, actor=None):
        """Return build records, optionally filtered. Action: build_read."""
        self._maybe_require(actor, "build_read")
        with self._lock:
            records = sorted(self._builds.values(), key=lambda r: _id_num(r["id"]))
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            return [self._copy_build(r) for r in records]

    # -- releases ------------------------------------------------------

    def create_release(self, project_id, version, actor, notes=None, build_id=None):
        """Create a release record. Action: release_write.

        Duplicate version within the same project is a ValidationError;
        the same version in a different project is fine.
        """
        self._require_actor(actor, "release_write", project_id)
        _validate_non_empty(version, "version")
        _validate_optional_str(notes, "notes")
        with self._lock:
            self._get_project_record(project_id)
            if build_id is not None:
                self._get_build_record(build_id)
            for existing in self._releases.values():
                if existing["project_id"] == project_id and existing["version"] == version:
                    raise ValidationError(
                        "version %r already released for project %r" % (version, project_id)
                    )
            release_id = self._next_id("rel")
            record = {
                "id": release_id,
                "project_id": project_id,
                "version": version,
                "notes": notes,
                "build_id": build_id,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._releases[release_id] = record
            self._audit(actor, "release_create", release_id, details={"project_id": project_id, "version": version})
            return dict(record)

    def get_release(self, release_id, actor=None):
        """Return one release record. Action: release_read."""
        self._maybe_require(actor, "release_read")
        with self._lock:
            return dict(self._get_release_record(release_id))

    def list_releases(self, project_id=None, actor=None):
        """Return release records, optionally filtered. Action: release_read."""
        self._maybe_require(actor, "release_read")
        with self._lock:
            records = sorted(self._releases.values(), key=lambda r: _id_num(r["id"]))
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            return [dict(r) for r in records]

    # -- artifacts -----------------------------------------------------

    def register_artifact(self, project_id, name, actor, version=None, checksum=None, content=None):
        """Register an artifact by checksum. Action: artifact_write.

        If content (str -> utf-8, or bytes) is given, sha256 and size
        are computed from it. If both checksum and content are given
        and they differ -> ValidationError, nothing stored. If neither
        is given -> ValidationError. The stored record holds the
        checksum and size, NOT the content.
        """
        self._require_actor(actor, "artifact_write", project_id)
        _validate_non_empty(name, "artifact name")
        _validate_optional_str(version, "version")
        _validate_optional_str(checksum, "checksum")
        if checksum is not None and not checksum.strip():
            raise ValidationError("checksum must be a non-empty string")
        content_bytes = None
        computed = None
        if content is not None:
            content_bytes = _content_bytes(content)
            computed = hashlib.sha256(content_bytes).hexdigest()
            if checksum is not None and checksum != computed:
                raise ValidationError("checksum does not match content")
        if computed is None and checksum is None:
            raise ValidationError("an artifact record must carry a checksum: give checksum or content")
        sha256 = computed if computed is not None else checksum
        size_bytes = len(content_bytes) if content_bytes is not None else None
        with self._lock:
            self._get_project_record(project_id)
            artifact_id = self._next_id("art")
            record = {
                "id": artifact_id,
                "project_id": project_id,
                "name": name,
                "version": version,
                "sha256": sha256,
                "size_bytes": size_bytes,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._artifacts[artifact_id] = record
            self._audit(actor, "artifact_register", artifact_id, details={"project_id": project_id, "name": name})
            return dict(record)

    def verify_artifact(self, artifact_id, content, actor=None):
        """Return True iff sha256(content) equals the stored checksum.

        Action: artifact_read (for User actors).
        """
        self._maybe_require(actor, "artifact_read")
        content_bytes = _content_bytes(content)
        with self._lock:
            record = self._get_artifact_record(artifact_id)
            return hashlib.sha256(content_bytes).hexdigest() == record["sha256"]

    def get_artifact(self, artifact_id, actor=None):
        """Return one artifact record. Action: artifact_read."""
        self._maybe_require(actor, "artifact_read")
        with self._lock:
            return dict(self._get_artifact_record(artifact_id))

    def list_artifacts(self, project_id=None, actor=None):
        """Return artifact records, optionally filtered. Action: artifact_read."""
        self._maybe_require(actor, "artifact_read")
        with self._lock:
            records = sorted(self._artifacts.values(), key=lambda r: _id_num(r["id"]))
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            return [dict(r) for r in records]

    # -- environments & deployments -------------------------------------

    def create_environment(self, name, actor, tier=None):
        """Create an environment record. Action: deployment_write."""
        self._require_actor(actor, "deployment_write", name if isinstance(name, str) else "environment")
        _validate_non_empty(name, "environment name")
        _validate_optional_str(tier, "tier")
        with self._lock:
            env_id = self._next_id("env")
            record = {
                "id": env_id,
                "name": name,
                "tier": tier,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._environments[env_id] = record
            self._audit(actor, "environment_create", env_id, details={"name": name})
            return dict(record)

    def list_environments(self, actor=None):
        """Return environment records. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            records = sorted(self._environments.values(), key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    def get_environment(self, environment_id, actor=None):
        """Return one environment record. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            return dict(self._get_environment_record(environment_id))

    def record_deployment(self, environment_id, project_id, actor, release_id=None, artifact_id=None, status="deployed"):
        """Record a deployment. Action: deployment_write. Records only."""
        self._require_actor(actor, "deployment_write", environment_id)
        if status not in DEPLOYMENT_STATUSES:
            raise ValidationError("status must be one of %s" % (", ".join(DEPLOYMENT_STATUSES),))
        with self._lock:
            self._get_environment_record(environment_id)
            self._get_project_record(project_id)
            if release_id is not None:
                self._get_release_record(release_id)
            if artifact_id is not None:
                self._get_artifact_record(artifact_id)
            dep_id = self._next_id("dep")
            record = {
                "id": dep_id,
                "environment_id": environment_id,
                "project_id": project_id,
                "release_id": release_id,
                "artifact_id": artifact_id,
                "status": status,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._deployments[dep_id] = record
            self._audit(actor, "deployment_record", dep_id,
                        details={"environment_id": environment_id, "project_id": project_id, "status": status})
            return dict(record)

    def list_deployments(self, environment_id=None, project_id=None, actor=None):
        """Return deployment records, optionally filtered. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            records = sorted(self._deployments.values(), key=lambda r: _id_num(r["id"]))
            if environment_id is not None:
                records = [r for r in records if r["environment_id"] == environment_id]
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            return [dict(r) for r in records]

    # -- search ----------------------------------------------------------

    def search(self, query, actor):
        """Search records. Action: search (for User actors).

        Case-insensitive substring match over names/titles/versions.
        Empty query is a ValidationError.
        """
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied for 'search'")
        if hasattr(actor, "role"):
            try:
                require(actor, "search")
            except PermissionDenied:
                self._audit(actor, "search:denied", query if isinstance(query, str) else "search")
                raise
        _validate_non_empty(query, "query")
        needle = query.strip().lower()
        with self._lock:
            projects = [dict(r) for r in sorted(self._projects.values(), key=lambda r: _id_num(r["id"]))
                        if needle in r["name"].lower()]
            issues = [dict(r) for r in sorted(self._issues.values(), key=lambda r: _id_num(r["id"]))
                      if needle in r["title"].lower()]
            reviews = [dict(r) for r in sorted(self._reviews.values(), key=lambda r: _id_num(r["id"]))
                       if needle in r["title"].lower()]
            releases = [dict(r) for r in sorted(self._releases.values(), key=lambda r: _id_num(r["id"]))
                        if needle in r["version"].lower()]
            artifacts = [dict(r) for r in sorted(self._artifacts.values(), key=lambda r: _id_num(r["id"]))
                         if needle in r["name"].lower()
                         or (r.get("version") and needle in r["version"].lower())]
            return {
                "projects": projects,
                "issues": issues,
                "reviews": reviews,
                "releases": releases,
                "artifacts": artifacts,
            }
