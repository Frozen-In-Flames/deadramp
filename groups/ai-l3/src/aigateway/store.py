"""AI gateway store: model & prompt-template registries, API keys,
quotas, sessions and request records, policy rules, the gateway
invoke() flow with its deterministic reference responder, and the
evaluation harness.

Clean-room implementation of the union spec's implementation contract.

Important honesty note: the responder is a deterministic *reference
stub* (``echo``, ``template``, or ``rules``). There is no learned model
in this build. Every invocation response says so, via
``reference_stub: True`` and the :data:`REFERENCE_NOTICE` text.

Conventions (following the shipped Collaboration L2 build):

- Every operation validates fully before it mutates anything: a failed
  operation consumes no id and changes nothing (a *blocked* invocation
  is not a failed operation in this sense -- the contract pins that it
  stores a blocked request record).
- Ids are sequential per object type with fixed prefixes (``mdl-``,
  ``tpl-``, ``key-``, ``ses-``, ``req-``, ``evd-``, ``evr-``,
  ``rule-``).
- The store records every successful mutation, every completed
  invocation, and every policy block to its audit log (when one is
  attached). Reads are not audited here; denied attempts and
  ``audit_read`` are the HTTP layer's responsibility, so nothing is
  recorded twice.
- Permission enforcement follows the sibling build: when the actor is
  a User-like object (has a ``role``), the operation's action is
  required against the permission matrix; plain string actors carry
  identity for provenance but no role to enforce against (the service
  layer enforces with full User objects).

High-baseline uplift (AU-5, fail closed): every audited operation is
wrapped by :func:`_fail_closed`. If recording the operation's audit
entry raises :class:`~aigateway.errors.AuditWriteError`, the store
state (registries, keys, quotas, sessions, request records, rules,
evaluation data, id counters) is restored to its pre-operation
snapshot and the error propagates -- an operation whose audit write
fails does not proceed, leaves no object behind, and consumes no id.
The snapshot is a deliberate deep copy: at register scale, correctness
beats cleverness.
"""

import copy
import functools
import hashlib
import re
import secrets
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import (
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    PolicyBlocked,
    QuotaExceeded,
    ValidationError,
)

REFERENCE_NOTICE = (
    "Reference responder: deterministic stub output. This build contains "
    "no learned model; output is produced by the registered responder "
    "behavior (echo, template, or rules)."
)

RESPONDERS = ("echo", "template", "rules")
MODEL_STATUSES = ("active", "deprecated")
RULE_SCOPES = ("input", "output", "both")
RULE_KINDS = ("term", "pattern")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _current_month():
    return datetime.now(timezone.utc).strftime("%Y-%m")


def estimate_tokens(text):
    """Pinned deterministic token estimator (~1 token per 4 chars).

    ``0`` for an empty string, else ``(len(text) + 3) // 4``. This is
    an estimator, stated as such -- not a real tokenizer.
    """
    if not text:
        return 0
    return (len(text) + 3) // 4


def _is_admin(actor):
    return getattr(actor, "role", None) == "admin"


def _maybe_require(actor, action):
    """Enforce permissions when ``actor`` is a User-like object."""
    if actor is not None and hasattr(actor, "role"):
        require(actor, action)


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_string(value, what):
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _validate_version(version, what="version"):
    if version is None:
        return None
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValidationError("%s must be a positive integer" % (what,))
    return version


def _fail_closed(method):
    """Wrap a store operation so an audit write failure rolls it back.

    High-baseline uplift (AU-5): the wrapped method runs against a
    snapshot of the store state; if it raises
    :class:`~aigateway.errors.AuditWriteError` (its audit entry could
    not be durably recorded), the snapshot is restored and the error
    propagates. Other exceptions keep the store's existing guarantee
    (validation happens before mutation, so nothing is half-applied).
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        snapshot = self._snapshot_state()
        try:
            return method(self, *args, **kwargs)
        except AuditWriteError:
            self._restore_state(snapshot)
            raise

    return wrapper


class AIGatewayStore:
    """In-memory store for the AI gateway service."""

    def __init__(self, audit=None, zero_persistence=False):
        self.audit = audit
        self.zero_persistence = bool(zero_persistence)
        self._models = {}  # id -> model dict
        self._templates = {}  # id -> template dict
        self._keys = {}  # id -> key dict (incl. private secret_hash)
        self._quotas = {}  # owner -> quota dict
        self._sessions = {}  # id -> session dict
        self._requests = {}  # id -> request dict (pinned public shape)
        self._request_order = []
        self._rules = {}  # id -> rule dict
        self._rule_order = []
        self._eval_datasets = {}  # id -> dataset dict
        self._eval_runs = {}  # id -> run dict
        self._counters = {
            "mdl": 0,
            "tpl": 0,
            "key": 0,
            "ses": 0,
            "req": 0,
            "evd": 0,
            "evr": 0,
            "rule": 0,
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
    def _copy(obj):
        return copy.deepcopy(obj)

    def _snapshot_state(self):
        """Deep-copy the mutable store state (AU-5 rollback image)."""
        return (
            copy.deepcopy(self._models),
            copy.deepcopy(self._templates),
            copy.deepcopy(self._keys),
            copy.deepcopy(self._quotas),
            copy.deepcopy(self._sessions),
            copy.deepcopy(self._requests),
            list(self._request_order),
            copy.deepcopy(self._rules),
            list(self._rule_order),
            copy.deepcopy(self._eval_datasets),
            copy.deepcopy(self._eval_runs),
            dict(self._counters),
        )

    def _restore_state(self, snapshot):
        """Restore a snapshot taken by :meth:`_snapshot_state`."""
        (
            self._models,
            self._templates,
            self._keys,
            self._quotas,
            self._sessions,
            self._requests,
            self._request_order,
            self._rules,
            self._rule_order,
            self._eval_datasets,
            self._eval_runs,
            self._counters,
        ) = snapshot

    # -- model registry ------------------------------------------------

    def _validate_model_config(self, responder, config):
        if config is None:
            config = {}
        if not isinstance(config, dict):
            raise ValidationError("config must be an object")
        config = copy.deepcopy(config)
        if responder == "template":
            if not isinstance(config.get("template"), str):
                raise ValidationError(
                    'responder "template" requires config["template"] to be a string'
                )
        elif responder == "rules":
            rules = config.get("rules")
            if not isinstance(rules, list):
                raise ValidationError(
                    'responder "rules" requires config["rules"] to be a list'
                )
            for rule in rules:
                if (
                    not isinstance(rule, dict)
                    or not isinstance(rule.get("match"), str)
                    or not isinstance(rule.get("response"), str)
                ):
                    raise ValidationError(
                        'each entry in config["rules"] must be a '
                        '{"match", "response"} pair of strings'
                    )
            if not isinstance(config.get("default"), str):
                raise ValidationError(
                    'responder "rules" requires config["default"] to be a string'
                )
        return config

    @_fail_closed
    def register_model(self, name, responder, actor, version=None,
                       provider="", capabilities=None, config=None):
        """Register a model (action ``registry_write``). Audits
        ``model_register``."""
        _maybe_require(actor, "registry_write")
        if actor is None or not actor_name(actor):
            raise PermissionDenied("permission denied: no user supplied")
        _validate_non_empty(name, "model name")
        if responder not in RESPONDERS:
            raise ValidationError(
                "responder must be one of %s" % (", ".join(RESPONDERS),)
            )
        _validate_string(provider, "provider")
        if capabilities is None:
            capabilities = []
        if not isinstance(capabilities, (list, tuple)) or any(
            not isinstance(c, str) for c in capabilities
        ):
            raise ValidationError("capabilities must be a list of strings")
        capabilities = list(capabilities)
        version = _validate_version(version)
        config = self._validate_model_config(responder, config)
        with self._lock:
            existing_versions = [
                m["version"] for m in self._models.values() if m["name"] == name
            ]
            if version is None:
                version = (max(existing_versions) + 1) if existing_versions else 1
            elif version in existing_versions:
                raise ValidationError(
                    "model %r version %d is already registered" % (name, version)
                )
            model_id = self._next_id("mdl")
            model = {
                "id": model_id,
                "name": name,
                "version": version,
                "provider": provider,
                "responder": responder,
                "capabilities": capabilities,
                "config": config,
                "status": "active",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._models[model_id] = model
            self._audit(actor, "model_register", model_id,
                        details={"name": name, "version": version})
            return self._copy(model)

    def _find_model(self, name, version=None):
        candidates = [m for m in self._models.values() if m["name"] == name]
        if not candidates:
            raise NotFoundError("model not found: %r" % (name,))
        if version is None:
            return max(candidates, key=lambda m: m["version"])
        for model in candidates:
            if model["version"] == version:
                return model
        raise NotFoundError(
            "model not found: %r version %r" % (name, version)
        )

    def get_model(self, name, actor, version=None):
        """Return one model dict (action ``read``); ``version=None``
        selects the highest version."""
        _maybe_require(actor, "read")
        _validate_non_empty(name, "model name")
        version = _validate_version(version)
        with self._lock:
            return self._copy(self._find_model(name, version))

    def list_models(self, actor):
        """Return all model dicts sorted by (name, version)."""
        _maybe_require(actor, "read")
        with self._lock:
            models = sorted(
                self._models.values(), key=lambda m: (m["name"], m["version"])
            )
            return [self._copy(m) for m in models]

    @_fail_closed
    def set_model_status(self, name, version, status, actor):
        """Set a model's status (action ``registry_write``). Audits
        ``model_status``."""
        _maybe_require(actor, "registry_write")
        _validate_non_empty(name, "model name")
        version = _validate_version(version)
        if version is None:
            raise ValidationError("version is required to set a model status")
        if status not in MODEL_STATUSES:
            raise ValidationError(
                "status must be one of %s" % (", ".join(MODEL_STATUSES),)
            )
        with self._lock:
            model = self._find_model(name, version)
            model["status"] = status
            self._audit(actor, "model_status", model["id"],
                        details={"name": name, "version": version,
                                 "status": status})
            return self._copy(model)

    # -- prompt template registry ---------------------------------------

    @_fail_closed
    def register_template(self, name, text, actor, version=None):
        """Register a prompt template (action ``registry_write``).
        Audits ``template_register``."""
        _maybe_require(actor, "registry_write")
        if actor is None or not actor_name(actor):
            raise PermissionDenied("permission denied: no user supplied")
        _validate_non_empty(name, "template name")
        _validate_string(text, "template text")
        version = _validate_version(version)
        with self._lock:
            existing_versions = [
                t["version"] for t in self._templates.values() if t["name"] == name
            ]
            if version is None:
                version = (max(existing_versions) + 1) if existing_versions else 1
            elif version in existing_versions:
                raise ValidationError(
                    "template %r version %d is already registered"
                    % (name, version)
                )
            template_id = self._next_id("tpl")
            template = {
                "id": template_id,
                "name": name,
                "version": version,
                "text": text,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._templates[template_id] = template
            self._audit(actor, "template_register", template_id,
                        details={"name": name, "version": version})
            return self._copy(template)

    def _find_template(self, name, version=None):
        candidates = [t for t in self._templates.values() if t["name"] == name]
        if not candidates:
            raise NotFoundError("template not found: %r" % (name,))
        if version is None:
            return max(candidates, key=lambda t: t["version"])
        for template in candidates:
            if template["version"] == version:
                return template
        raise NotFoundError(
            "template not found: %r version %r" % (name, version)
        )

    @staticmethod
    def _render_template_text(text, prompt):
        if "{prompt}" in text:
            return text.replace("{prompt}", prompt)
        return text

    def get_template(self, name, actor, version=None):
        """Return one template dict (action ``read``)."""
        _maybe_require(actor, "read")
        _validate_non_empty(name, "template name")
        version = _validate_version(version)
        with self._lock:
            return self._copy(self._find_template(name, version))

    def list_templates(self, actor):
        """Return all template dicts sorted by (name, version)."""
        _maybe_require(actor, "read")
        with self._lock:
            templates = sorted(
                self._templates.values(), key=lambda t: (t["name"], t["version"])
            )
            return [self._copy(t) for t in templates]

    # -- API keys ---------------------------------------------------------

    @_fail_closed
    def create_api_key(self, owner, actor):
        """Create an API key (action ``registry_write``).

        The actor must be the owner themself or a platform admin. The
        secret is returned only here; the store keeps only its SHA-256
        hex digest. Audits ``key_create`` (the secret is never audited).
        """
        _maybe_require(actor, "registry_write")
        if actor is None or not actor_name(actor):
            raise PermissionDenied("permission denied: no user supplied")
        _validate_non_empty(owner, "owner")
        if actor_name(actor) != owner and not _is_admin(actor):
            raise PermissionDenied(
                "permission denied: user %r may not create API keys for %r"
                % (actor_name(actor), owner)
            )
        with self._lock:
            secret = "sk-" + secrets.token_hex(20)
            key_id = self._next_id("key")
            record = {
                "id": key_id,
                "owner": owner,
                "secret_hash": hashlib.sha256(secret.encode("utf-8")).hexdigest(),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._keys[key_id] = record
            self._audit(actor, "key_create", key_id, details={"owner": owner})
            return {
                "id": key_id,
                "owner": owner,
                "secret": secret,
                "created_by": record["created_by"],
                "created_utc": record["created_utc"],
            }

    def authenticate_key(self, secret):
        """Return the owner's name for ``secret``, or ``None``.

        Not audited.
        """
        if not isinstance(secret, str) or not secret:
            return None
        digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        with self._lock:
            for record in self._keys.values():
                if secrets.compare_digest(record["secret_hash"], digest):
                    return record["owner"]
            return None

    def list_api_keys(self, actor):
        """Return key dicts without ``secret``/``secret_hash`` (action
        ``read``). A non-admin actor sees only their own keys."""
        _maybe_require(actor, "read")
        if actor is None or not actor_name(actor):
            raise PermissionDenied("permission denied: no user supplied")
        name = actor_name(actor)
        admin = _is_admin(actor)
        with self._lock:
            return [
                {
                    "id": r["id"],
                    "owner": r["owner"],
                    "created_by": r["created_by"],
                    "created_utc": r["created_utc"],
                }
                for r in self._keys.values()
                if admin or r["owner"] == name
            ]

    # -- quotas & usage ---------------------------------------------------

    @_fail_closed
    def set_quota(self, owner, token_limit, actor):
        """Set (or replace) an owner's monthly token quota (action
        ``admin``). Audits ``quota_set``."""
        _maybe_require(actor, "admin")
        _validate_non_empty(owner, "owner")
        if isinstance(token_limit, bool) or not isinstance(token_limit, int) \
                or token_limit <= 0:
            raise ValidationError("token_limit must be a positive integer")
        with self._lock:
            quota = {
                "owner": owner,
                "token_limit": token_limit,
                "updated_utc": _utc_now(),
            }
            self._quotas[owner] = quota
            self._audit(actor, "quota_set", owner,
                        details={"token_limit": token_limit})
            return dict(quota)

    def _require_owner_or_admin(self, owner, actor, what):
        if actor_name(actor) != owner and not _is_admin(actor):
            raise PermissionDenied(
                "permission denied: user %r may not access %s for %r"
                % (actor_name(actor), what, owner)
            )

    def get_quota(self, owner, actor):
        """Return the owner's quota dict, or ``None`` (action
        ``usage_read``; owner or platform admin only)."""
        _maybe_require(actor, "usage_read")
        _validate_non_empty(owner, "owner")
        self._require_owner_or_admin(owner, actor, "quota")
        with self._lock:
            quota = self._quotas.get(owner)
            return dict(quota) if quota is not None else None

    def _usage_owner_for_record(self, record):
        if record.get("key_id"):
            key = self._keys.get(record["key_id"])
            if key is not None:
                return key["owner"]
        return record["actor"]

    def _monthly_usage_locked(self, owner):
        month = _current_month()
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        requests = 0
        for request_id in self._request_order:
            record = self._requests[request_id]
            if not record["created_utc"].startswith(month):
                continue
            if self._usage_owner_for_record(record) != owner:
                continue
            usage = record["usage"]
            prompt_tokens += usage["prompt_tokens"]
            completion_tokens += usage["completion_tokens"]
            total_tokens += usage["total_tokens"]
            requests += 1
        return {
            "owner": owner,
            "month": month,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "requests": requests,
        }

    def usage_for(self, owner, actor):
        """Aggregate the owner's current-UTC-month usage (action
        ``usage_read``; owner or platform admin only). Blocked records
        are included, with the usage pinned under ``invoke``."""
        _maybe_require(actor, "usage_read")
        _validate_non_empty(owner, "owner")
        self._require_owner_or_admin(owner, actor, "usage")
        with self._lock:
            return self._monthly_usage_locked(owner)

    # -- sessions -----------------------------------------------------------

    @_fail_closed
    def create_session(self, title, actor):
        """Create a conversation session (action ``invoke``). Audits
        ``session_create``."""
        _maybe_require(actor, "invoke")
        if actor is None or not actor_name(actor):
            raise PermissionDenied("permission denied: no user supplied")
        _validate_non_empty(title, "session title")
        with self._lock:
            session_id = self._next_id("ses")
            session = {
                "id": session_id,
                "owner": actor_name(actor),
                "title": title,
                "turns": [],
                "created_utc": _utc_now(),
            }
            self._sessions[session_id] = session
            self._audit(actor, "session_create", session_id,
                        details={"title": title})
            return self._copy(session)

    def _find_session(self, session_id):
        session = self._sessions.get(session_id)
        if session is None:
            raise NotFoundError("session not found: %r" % (session_id,))
        return session

    def get_session(self, session_id, actor):
        """Return one session (action ``read``; owner or admin)."""
        _maybe_require(actor, "read")
        with self._lock:
            session = self._find_session(session_id)
            if session["owner"] != actor_name(actor) and not _is_admin(actor):
                raise PermissionDenied(
                    "permission denied: user %r may not read session %r"
                    % (actor_name(actor), session_id)
                )
            return self._copy(session)

    def list_sessions(self, actor):
        """Return the actor's own sessions (admin: all), chronological."""
        _maybe_require(actor, "read")
        name = actor_name(actor)
        admin = _is_admin(actor)
        with self._lock:
            return [
                self._copy(s)
                for s in self._sessions.values()
                if admin or s["owner"] == name
            ]

    # -- policy rules --------------------------------------------------------

    @_fail_closed
    def add_rule(self, scope, kind, value, actor):
        """Add a policy rule (action ``policy_write``). Audits
        ``policy_add``."""
        _maybe_require(actor, "policy_write")
        if scope not in RULE_SCOPES:
            raise ValidationError(
                "scope must be one of %s" % (", ".join(RULE_SCOPES),)
            )
        if kind not in RULE_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(RULE_KINDS),)
            )
        _validate_non_empty(value, "rule value")
        if kind == "pattern":
            try:
                re.compile(value)
            except re.error as exc:
                raise ValidationError(
                    "pattern value must compile as a regex: %r" % (value,)
                ) from exc
        with self._lock:
            rule_id = self._next_id("rule")
            rule = {
                "id": rule_id,
                "scope": scope,
                "kind": kind,
                "value": value,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._rules[rule_id] = rule
            self._rule_order.append(rule_id)
            self._audit(actor, "policy_add", rule_id,
                        details={"scope": scope, "kind": kind})
            return dict(rule)

    @_fail_closed
    def remove_rule(self, rule_id, actor):
        """Remove a policy rule (action ``policy_write``). Audits
        ``policy_remove``."""
        _maybe_require(actor, "policy_write")
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                raise NotFoundError("policy rule not found: %r" % (rule_id,))
            del self._rules[rule_id]
            self._rule_order.remove(rule_id)
            self._audit(actor, "policy_remove", rule_id)
            return dict(rule)

    def list_rules(self, actor):
        """Return policy rules in creation order (action ``read``)."""
        _maybe_require(actor, "read")
        with self._lock:
            return [dict(self._rules[rid]) for rid in self._rule_order]

    @staticmethod
    def _rule_matches(rule, text):
        if rule["kind"] == "term":
            return rule["value"].lower() in text.lower()
        return re.search(rule["value"], text) is not None

    def _first_policy_match(self, text, stage):
        """Return the first rule (creation order) applicable to
        ``stage`` ("input" or "output") that matches ``text``, or None.

        This is the gateway's single policy-evaluation point: the
        negative control's mutant is a version of this check that
        treats every text as clean (always returns None).
        """
        applicable = ("input", "both") if stage == "input" else ("output", "both")
        for rule_id in self._rule_order:
            rule = self._rules[rule_id]
            if rule["scope"] not in applicable:
                continue
            if self._rule_matches(rule, text):
                return rule
        return None

    # -- gateway & reference responder ---------------------------------------

    @staticmethod
    def _run_responder(model, effective_prompt):
        responder = model["responder"]
        config = model["config"]
        if responder == "echo":
            return effective_prompt
        if responder == "template":
            template_text = config["template"]
            if "{prompt}" in template_text:
                return template_text.replace("{prompt}", effective_prompt)
            return template_text
        # rules: first matching configured rule wins, else the default.
        lowered = effective_prompt.lower()
        for rule in config["rules"]:
            if rule["match"].lower() in lowered:
                return rule["response"]
        return config["default"]

    def _store_request_locked(self, model, actor, key_id, session_id,
                              prompt_value, output_value, usage, status,
                              withheld):
        request_id = self._next_id("req")
        record = {
            "id": request_id,
            "model": model["name"],
            "model_version": model["version"],
            "session_id": session_id,
            "actor": actor_name(actor),
            "key_id": key_id,
            "prompt": prompt_value,
            "output": output_value,
            "reference_stub": True,
            "responder": model["responder"],
            "notice": REFERENCE_NOTICE,
            "usage": usage,
            "status": status,
            "created_utc": _utc_now(),
        }
        if withheld:
            record["content_withheld"] = True
        self._requests[request_id] = record
        self._request_order.append(request_id)
        return record

    @_fail_closed
    def invoke(self, model_name, prompt, actor, version=None, key_id=None,
               session_id=None, template_name=None, template_version=None):
        """Invoke a registered model through the gateway (action
        ``invoke``). The 9 pinned steps are followed in order; see the
        union spec. Returns the stored request dict for a completion;
        raises :class:`PolicyBlocked` (carrying ``request_id``) for a
        blocked invocation and :class:`QuotaExceeded` (nothing stored)
        for a quota refusal.
        """
        _maybe_require(actor, "invoke")
        if actor is None or not actor_name(actor):
            raise PermissionDenied("permission denied: no user supplied")
        _validate_non_empty(model_name, "model name")
        _validate_string(prompt, "prompt")
        version = _validate_version(version)
        template_version = _validate_version(template_version,
                                             "template_version")
        with self._lock:
            # 1. Resolve the model; deprecated models refuse requests.
            model = self._find_model(model_name, version)
            if model["status"] == "deprecated":
                raise ValidationError(
                    "model %r version %d is deprecated"
                    % (model["name"], model["version"])
                )
            # 2. Key must exist and belong to the actor (admin excepted).
            key_record = None
            if key_id is not None:
                key_record = self._keys.get(key_id)
                if key_record is None:
                    raise NotFoundError("api key not found: %r" % (key_id,))
                if key_record["owner"] != actor_name(actor) \
                        and not _is_admin(actor):
                    raise PermissionDenied(
                        "permission denied: api key %r does not belong to %r"
                        % (key_id, actor_name(actor))
                    )
            # 3. Session must exist and belong to the actor (or admin).
            session = None
            if session_id is not None:
                session = self._find_session(session_id)
                if session["owner"] != actor_name(actor) \
                        and not _is_admin(actor):
                    raise PermissionDenied(
                        "permission denied: session %r does not belong to %r"
                        % (session_id, actor_name(actor))
                    )
            # 4. Render through the prompt template, if one is named.
            effective_prompt = prompt
            if template_name is not None:
                _validate_non_empty(template_name, "template name")
                template = self._find_template(template_name, template_version)
                effective_prompt = self._render_template_text(
                    template["text"], prompt
                )
            # 5. Quota pre-check (nothing stored, no responder runs).
            quota_owner = key_record["owner"] if key_record is not None \
                else actor_name(actor)
            quota = self._quotas.get(quota_owner)
            if quota is not None:
                current = self._monthly_usage_locked(quota_owner)
                if current["total_tokens"] + estimate_tokens(effective_prompt) \
                        > quota["token_limit"]:
                    raise QuotaExceeded(
                        "quota exceeded for owner %r: limit %d tokens"
                        % (quota_owner, quota["token_limit"])
                    )
            withheld = self.zero_persistence
            # 6. Input policy check.
            input_rule = self._first_policy_match(effective_prompt, "input")
            if input_rule is not None:
                prompt_tokens = estimate_tokens(effective_prompt)
                usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": 0,
                    "total_tokens": prompt_tokens,
                }
                record = self._store_request_locked(
                    model, actor, key_id, session_id,
                    None if withheld else effective_prompt, None,
                    usage, "blocked_input", withheld,
                )
                self._audit(actor, "invoke_blocked", record["id"],
                            details={"stage": "input",
                                     "rule_id": input_rule["id"]})
                raise PolicyBlocked(
                    "input blocked by policy rule %s" % (input_rule["id"],),
                    request_id=record["id"],
                )
            # 7. Run the (reference stub) responder.
            output = self._run_responder(model, effective_prompt)
            # 8. Output policy check.
            output_rule = self._first_policy_match(output, "output")
            if output_rule is not None:
                prompt_tokens = estimate_tokens(effective_prompt)
                completion_tokens = estimate_tokens(output)
                usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                }
                record = self._store_request_locked(
                    model, actor, key_id, session_id,
                    None if withheld else effective_prompt, None,
                    usage, "blocked_output", withheld,
                )
                self._audit(actor, "invoke_blocked", record["id"],
                            details={"stage": "output",
                                     "rule_id": output_rule["id"]})
                raise PolicyBlocked(
                    "output blocked by policy rule %s" % (output_rule["id"],),
                    request_id=record["id"],
                )
            # 9. Store the completion, append the session turn, audit.
            prompt_tokens = estimate_tokens(effective_prompt)
            completion_tokens = estimate_tokens(output)
            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
            record = self._store_request_locked(
                model, actor, key_id, session_id,
                None if withheld else effective_prompt,
                None if withheld else output,
                usage, "completed", withheld,
            )
            if session is not None:
                turn = {
                    "request_id": record["id"],
                    "prompt": None if withheld else effective_prompt,
                    "output": None if withheld else output,
                    "created_utc": record["created_utc"],
                }
                if withheld:
                    turn["content_withheld"] = True
                session["turns"].append(turn)
            self._audit(actor, "invoke", record["id"],
                        details={"model": model["name"],
                                 "total_tokens": usage["total_tokens"]})
            return self._copy(record)

    # -- request records -----------------------------------------------------

    def get_request(self, request_id, actor):
        """Return one request record (action ``read``; the invocation's
        actor or a platform admin only)."""
        _maybe_require(actor, "read")
        with self._lock:
            record = self._requests.get(request_id)
            if record is None:
                raise NotFoundError("request not found: %r" % (request_id,))
            if record["actor"] != actor_name(actor) and not _is_admin(actor):
                raise PermissionDenied(
                    "permission denied: user %r may not read request %r"
                    % (actor_name(actor), request_id)
                )
            return self._copy(record)

    def list_requests(self, actor, session_id=None):
        """Return the actor's own request records (admin: all),
        chronological, optionally filtered to one session."""
        _maybe_require(actor, "read")
        name = actor_name(actor)
        admin = _is_admin(actor)
        with self._lock:
            result = []
            for request_id in self._request_order:
                record = self._requests[request_id]
                if not admin and record["actor"] != name:
                    continue
                if session_id is not None and record["session_id"] != session_id:
                    continue
                result.append(self._copy(record))
            return result

    # -- evaluation harness ----------------------------------------------------

    @_fail_closed
    def create_eval_dataset(self, name, cases, actor):
        """Create an evaluation dataset (action ``eval_run``). Audits
        ``eval_dataset_create``."""
        _maybe_require(actor, "eval_run")
        if actor is None or not actor_name(actor):
            raise PermissionDenied("permission denied: no user supplied")
        _validate_non_empty(name, "dataset name")
        if not isinstance(cases, list) or not cases:
            raise ValidationError("cases must be a non-empty list")
        stored_cases = []
        for index, case in enumerate(cases, start=1):
            if not isinstance(case, dict):
                raise ValidationError("each case must be an object")
            if not isinstance(case.get("prompt"), str) \
                    or not isinstance(case.get("expected"), str):
                raise ValidationError(
                    "each case requires string 'prompt' and 'expected'"
                )
            match = case.get("match", "exact")
            if match not in ("exact", "contains"):
                raise ValidationError("case 'match' must be 'exact' or 'contains'")
            rubric = case.get("rubric")
            if rubric is not None:
                if not isinstance(rubric, dict) or any(
                    not isinstance(k, str) or not isinstance(v, str)
                    for k, v in rubric.items()
                ):
                    raise ValidationError(
                        "case 'rubric' must be an object of criterion "
                        "name -> expected substring"
                    )
            stored = copy.deepcopy(case)
            stored["case_id"] = "case-%d" % (index,)
            stored_cases.append(stored)
        with self._lock:
            dataset_id = self._next_id("evd")
            dataset = {
                "id": dataset_id,
                "name": name,
                "cases": stored_cases,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._eval_datasets[dataset_id] = dataset
            self._audit(actor, "eval_dataset_create", dataset_id,
                        details={"name": name})
            return self._copy(dataset)

    def get_eval_dataset(self, dataset_id, actor):
        """Return one evaluation dataset (action ``read``)."""
        _maybe_require(actor, "read")
        with self._lock:
            dataset = self._eval_datasets.get(dataset_id)
            if dataset is None:
                raise NotFoundError(
                    "eval dataset not found: %r" % (dataset_id,)
                )
            return self._copy(dataset)

    def list_eval_datasets(self, actor):
        """Return all evaluation datasets (action ``read``)."""
        _maybe_require(actor, "read")
        with self._lock:
            return [self._copy(d) for d in self._eval_datasets.values()]

    @_fail_closed
    def run_eval(self, dataset_id, model_name, actor, version=None):
        """Run an evaluation dataset against a registered model's
        responder, directly (action ``eval_run``): no quota, no
        policy, no metering, and no request record. Audits
        ``eval_run``."""
        _maybe_require(actor, "eval_run")
        _validate_non_empty(model_name, "model name")
        version = _validate_version(version)
        with self._lock:
            dataset = self._eval_datasets.get(dataset_id)
            if dataset is None:
                raise NotFoundError(
                    "eval dataset not found: %r" % (dataset_id,)
                )
            model = self._find_model(model_name, version)
            if model["status"] == "deprecated":
                raise ValidationError(
                    "model %r version %d is deprecated"
                    % (model["name"], model["version"])
                )
            results = []
            passed = 0
            for case in dataset["cases"]:
                output = self._run_responder(model, case["prompt"])
                match_rule = case.get("match", "exact")
                if match_rule == "contains":
                    match_ok = case["expected"].lower() in output.lower()
                else:
                    match_ok = output.strip() == case["expected"].strip()
                rubric_results = {}
                rubric = case.get("rubric") or {}
                for criterion, substring in rubric.items():
                    rubric_results[criterion] = substring.lower() in output.lower()
                case_passed = bool(match_ok and all(rubric_results.values()))
                if case_passed:
                    passed += 1
                results.append({
                    "case_id": case["case_id"],
                    "prompt": case["prompt"],
                    "expected": case["expected"],
                    "output": output,
                    "passed": case_passed,
                    "rubric_results": rubric_results,
                })
            total = len(dataset["cases"])
            run_id = self._next_id("evr")
            run = {
                "id": run_id,
                "dataset_id": dataset_id,
                "model": model["name"],
                "model_version": model["version"],
                "results": results,
                "passed": passed,
                "total": total,
                "score": (passed / total) if total else 0.0,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._eval_runs[run_id] = run
            self._audit(actor, "eval_run", run_id,
                        details={"dataset_id": dataset_id,
                                 "model": model["name"]})
            return self._copy(run)

    def get_eval_run(self, run_id, actor):
        """Return one evaluation run (action ``read``; the run's
        creator or a platform admin only)."""
        _maybe_require(actor, "read")
        with self._lock:
            run = self._eval_runs.get(run_id)
            if run is None:
                raise NotFoundError("eval run not found: %r" % (run_id,))
            if run["created_by"] != actor_name(actor) and not _is_admin(actor):
                raise PermissionDenied(
                    "permission denied: user %r may not read eval run %r"
                    % (actor_name(actor), run_id)
                )
            return self._copy(run)
