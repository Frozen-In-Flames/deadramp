"""Final GAPS batch extensions for the Contact Center L2 build.

One new module beside the core: :class:`ContactExtensions` wraps a
:class:`contact.store.ContactStore` and adds the records layer for
the eleven Extended / named-absence families in this group's
GAPS.md section (see ``../../BATCH.md`` for the per-entry
dispositions). Every existing core module is byte-identical to its
pre-batch state; this module only adds records of its own and reads
core records through the core's public API.

Honesty rules, enforced in code and pinned by tests:

- Persons are opaque references only. Person-shaped fields on this
  surface are ids of records already in the core directory (agents,
  contacts) -- whose shapes cannot hold a phone number, email
  address, or real identifier -- or opaque ``*_ref`` strings. No
  extension record shape contains a phone/email/identifier field;
  the test suite runs a recursive forbidden-key scan over every
  extension record and view.
- Derived values are derived at read and never stored: a PAM
  request's current state, a clearance case's current state, survey
  tallies, risk summaries, and SLA breach state under a recorded
  policy. Stored records carry no derived key; tests pin that.
- Nothing here executes against an external system. The five
  stub-engine families ship as labeled reference implementations:
  every record they create carries ``reference_stub: True``
  (connector sync records also ``reference_transport: True``), and
  the labels on each record state plainly what does not happen
  here (``collected_here``, ``connected_here``, ``detected_here``,
  ``inference_here`` ... are all False).
- The founding doctrine is not repealed: the core business-rule
  registry never executes, and nothing on this surface executes a
  rule either. Fraud rule records are definitions held as data.

RBAC: the core action set is fixed, so each extension operation
maps onto an existing core action and is checked before any state
change or id allocation, following the core convention (User-like
actors are enforced here; plain-string actors carry identity only
and are the service layer's responsibility). The mapping:

- PAM requests / sessions ......... case_write / case_read
- Identity risk signals ........... alert_write / alert_read
- Personnel-security cases ........ directory_write / directory_read
- Knowledge-base articles ......... interaction_write / interaction_read
- CSAT surveys .................... interaction_write / interaction_read
- SLA policies .................... rule_write / rule_read (admin-only
  write, like the core rule registry: policies are configuration)
- Observability references ........ alert_write / alert_read
- Telephony references ............ callback_write / callback_read
- Fraud rule definitions .......... rule_write / rule_read
- Fraud finding reports ........... alert_write / alert_read
- Connector references ............ interaction_write / interaction_read
- AI/ML references ................ alert_write / alert_read

Denied attempts by User-like actors are recorded on the core audit
log as ``ext_<action>:denied`` and every successful mutation as
``ext_<action>``. If an audit write fails, the record insertion and
its id roll back before the error propagates -- no extension record
exists whose audit entry does not.

Every operation validates fully before it mutates anything: a
failed operation consumes no id and changes nothing. Ids are
sequential per object type with fixed prefixes (``pam-``, ``pamo-``,
``pams-``, ``risk-``, ``rec-``, ``clr-``, ``clro-``, ``kb-``,
``kbrev-``, ``svy-``, ``svr-``, ``sla-``, ``obs-``, ``obsr-``,
``tel-``, ``route-``, ``fr-``, ``frf-``, ``con-``, ``conr-``,
``ml-``, ``mlr-``).
"""

import copy
import threading
from datetime import timedelta
from fractions import Fraction

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import (
    KNOWN_CASE_TYPES,
    KNOWN_PRIORITIES,
    NON_BREACHING_STATUSES,
    _coerce_now,
    _parse_iso_datetime,
    _utc_now,
    _validate_non_empty,
)


def _validate_optional_text(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string or None" % (what,))
    return value


def _validate_count(value, what):
    """A reported count: a non-negative int; booleans/floats rejected."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer count" % (what,))
    if value < 0:
        raise ValidationError("%s must be non-negative" % (what,))
    return value


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class ContactExtensions:
    """The GAPS-batch extension surface over a ContactStore."""

    def __init__(self, store):
        self.store = store
        self._pam_requests = {}
        self._pam_outcomes = {}
        self._pam_sessions = {}
        self._risk_signals = {}
        self._recommendations = {}
        self._clearance_cases = {}
        self._clearance_outcomes = {}
        self._articles = {}
        self._article_revisions = {}
        self._surveys = {}
        self._survey_responses = {}
        self._sla_policies = {}
        self._obs_sources = {}
        self._obs_reports = {}
        self._tel_sessions = {}
        self._routing_records = {}
        self._fraud_rules = {}
        self._fraud_findings = {}
        self._connectors = {}
        self._connector_syncs = {}
        self._models = {}
        self._model_outputs = {}
        self._counters = {
            "pam": 0, "pamo": 0, "pams": 0, "risk": 0, "rec": 0,
            "clr": 0, "clro": 0, "kb": 0, "kbrev": 0, "svy": 0,
            "svr": 0, "sla": 0, "obs": 0, "obsr": 0, "tel": 0,
            "route": 0, "fr": 0, "frf": 0, "con": 0, "conr": 0,
            "ml": 0, "mlr": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _guard(self, actor, action):
        """Enforce ``action`` for User-like actors, core convention.

        A missing actor is denied outright. A denied User-like actor
        is recorded on the core audit log as ``ext_<action>:denied``
        before the error propagates. Plain-string actors carry
        identity only (the service layer enforces for them).
        """
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (action,))
        if hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                if self.store.audit is not None:
                    self.store.audit.record(
                        actor_name(actor), "ext_%s:denied" % (action,),
                        "extensions", details={"action": action})
                raise

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(
                actor_name(actor), "ext_%s" % (action,), target,
                details=details)

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _commit(self, prefix, collection, record, actor, action, details=None):
        """Insert ``record`` and audit it, rolling both back on failure.

        The id is allocated by the caller before this runs; if the
        audit write raises, the record is removed and the counter
        restored, so a failed operation consumes no id and leaves no
        record whose audit entry does not exist.
        """
        collection[record["id"]] = record
        try:
            self._audit(actor, action, record["id"], details=details)
        except Exception:
            del collection[record["id"]]
            self._counters[prefix] -= 1
            raise
        return copy.deepcopy(record)

    @staticmethod
    def _get(collection, obj_id, what):
        record = collection.get(obj_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, obj_id))
        return record

    # -- PAM & Zero Trust (idx 152, built) ------------------------------
    # Records form: a privileged-access REQUEST record with its
    # just-in-time window held as data, outcome records storing a
    # reported grant state verbatim, and session records holding a
    # reported state label only. Nothing is granted, enforced,
    # recorded, or monitored here: ``granted_here`` /
    # ``enforced_here`` / ``content_held_here`` / ``monitored_here``
    # are False on every record. Identity and PAM engines stay with
    # the embedding organization (PLATFORM-LAYER.md decision 1);
    # this is the request log in front of them.

    def create_access_request(self, actor, agent_id, target_ref,
                              justification_ref=None, window_start=None,
                              window_end=None):
        """Record a privileged-access request. Action: case_write.

        Id prefix: pam-. The subject must be an agent already in
        the core directory. ``target_ref`` / ``justification_ref``
        are opaque references. The just-in-time window is held as
        data; recording a request grants nothing.
        """
        self._guard(actor, "case_write")
        _validate_non_empty(target_ref, "target_ref")
        _validate_optional_text(justification_ref, "justification_ref")
        start_dt = end_dt = None
        if window_start is not None:
            start_dt = _parse_iso_datetime(window_start, "window_start")
        if window_end is not None:
            end_dt = _parse_iso_datetime(window_end, "window_end")
        if start_dt is not None and end_dt is not None and end_dt <= start_dt:
            raise ValidationError("window_end must be after window_start")
        with self._lock:
            self.store.get_agent(agent_id, actor=actor)
            request_id = self._next_id("pam")
            now = _utc_now()
            record = {
                "id": request_id,
                "agent_id": agent_id,
                "target_ref": target_ref,
                "justification_ref": justification_ref,
                "window_start": window_start,
                "window_end": window_end,
                "granted_here": False,
                "enforced_here": False,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            return self._commit("pam", self._pam_requests, record, actor,
                                "pam_request_create",
                                details={"agent_id": agent_id})

    def record_access_outcome(self, actor, request_id, outcome_label):
        """Record a reported grant-state outcome for a request.

        Action: case_write. Id prefix: pamo-. The label is stored
        verbatim as reported by the privileged-access system; this
        build grants, denies, and revokes nothing itself.
        """
        self._guard(actor, "case_write")
        _validate_non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._get(self._pam_requests, request_id, "access request")
            outcome_id = self._next_id("pamo")
            record = {
                "id": outcome_id,
                "request_id": request_id,
                "outcome_label": outcome_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("pamo", self._pam_outcomes, record, actor,
                                "pam_outcome_record",
                                details={"request_id": request_id})

    def _pam_view(self, request):
        view = copy.deepcopy(request)
        outcomes = [o for o in self._pam_outcomes.values()
                    if o["request_id"] == request["id"]]
        outcomes.sort(key=lambda o: _id_num(o["id"]))
        view["current_state"] = (
            outcomes[-1]["outcome_label"] if outcomes else "requested")
        view["outcome_count"] = len(outcomes)
        view["derived"] = True
        return view

    def get_access_request(self, actor, request_id):
        """One access request with derived current state.

        Action: case_read. The stored record carries no
        ``current_state`` key; it is derived here from the recorded
        outcomes.
        """
        self._guard(actor, "case_read")
        with self._lock:
            request = self._get(self._pam_requests, request_id,
                                "access request")
            return self._pam_view(request)

    def list_access_requests(self, actor, agent_id=None):
        """Access requests with derived state. Action: case_read."""
        self._guard(actor, "case_read")
        with self._lock:
            requests = list(self._pam_requests.values())
            if agent_id is not None:
                requests = [r for r in requests if r["agent_id"] == agent_id]
            requests.sort(key=lambda r: _id_num(r["id"]))
            return [self._pam_view(r) for r in requests]

    def record_access_session(self, actor, request_id, session_ref,
                              reported_state):
        """Record a privileged-session record. Action: case_write.

        Id prefix: pams-. ``session_ref`` is an opaque reference to
        the session in the privileged-access system and
        ``reported_state`` its state as reported. No session content
        is held here and no session is monitored here.
        """
        self._guard(actor, "case_write")
        _validate_non_empty(session_ref, "session_ref")
        _validate_non_empty(reported_state, "reported_state")
        with self._lock:
            self._get(self._pam_requests, request_id, "access request")
            session_id = self._next_id("pams")
            record = {
                "id": session_id,
                "request_id": request_id,
                "session_ref": session_ref,
                "reported_state": reported_state,
                "content_held_here": False,
                "monitored_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("pams", self._pam_sessions, record, actor,
                                "pam_session_record",
                                details={"request_id": request_id})

    def list_access_sessions(self, actor, request_id=None):
        """Session records, optionally for one request.

        Action: case_read.
        """
        self._guard(actor, "case_read")
        with self._lock:
            sessions = list(self._pam_sessions.values())
            if request_id is not None:
                sessions = [s for s in sessions
                            if s["request_id"] == request_id]
            sessions.sort(key=lambda s: _id_num(s["id"]))
            return copy.deepcopy(sessions)

    # -- Identity risk analytics (idx 153, built) ------------------------
    # Records form: risk-signal records storing a reported signal
    # label verbatim, and recommendation records held as data. No
    # numeric field exists on either shape -- no risk score is
    # computed, stored, or derivable here (``computed_here`` is
    # False); summaries are counts over the recorded labels only.

    def record_risk_signal(self, actor, agent_id, signal_label,
                           source_ref=None):
        """Record a reported identity risk signal. Action: alert_write.

        Id prefix: risk-. The subject must be an agent already in
        the core directory; ``signal_label`` is stored verbatim as
        reported by the identity system.
        """
        self._guard(actor, "alert_write")
        _validate_non_empty(signal_label, "signal_label")
        _validate_optional_text(source_ref, "source_ref")
        with self._lock:
            self.store.get_agent(agent_id, actor=actor)
            signal_id = self._next_id("risk")
            record = {
                "id": signal_id,
                "agent_id": agent_id,
                "signal_label": signal_label,
                "source_ref": source_ref,
                "computed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("risk", self._risk_signals, record, actor,
                                "risk_signal_record",
                                details={"agent_id": agent_id})

    def record_recommendation(self, actor, agent_id, recommendation_label,
                              signal_id=None):
        """Record a prescriptive recommendation as data.

        Action: alert_write. Id prefix: rec-. The label is held
        verbatim; nothing here computes or applies it
        (``computed_here`` / ``applied_here`` are False).
        """
        self._guard(actor, "alert_write")
        _validate_non_empty(recommendation_label, "recommendation_label")
        with self._lock:
            self.store.get_agent(agent_id, actor=actor)
            if signal_id is not None:
                signal = self._get(self._risk_signals, signal_id,
                                   "risk signal")
                if signal["agent_id"] != agent_id:
                    raise ValidationError(
                        "risk signal %r belongs to a different agent"
                        % (signal_id,))
            rec_id = self._next_id("rec")
            record = {
                "id": rec_id,
                "agent_id": agent_id,
                "signal_id": signal_id,
                "recommendation_label": recommendation_label,
                "computed_here": False,
                "applied_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("rec", self._recommendations, record, actor,
                                "recommendation_record",
                                details={"agent_id": agent_id})

    def list_risk_signals(self, actor, agent_id=None):
        """Risk-signal records. Action: alert_read."""
        self._guard(actor, "alert_read")
        with self._lock:
            signals = list(self._risk_signals.values())
            if agent_id is not None:
                signals = [s for s in signals if s["agent_id"] == agent_id]
            signals.sort(key=lambda s: _id_num(s["id"]))
            return copy.deepcopy(signals)

    def list_recommendations(self, actor, agent_id=None):
        """Recommendation records. Action: alert_read."""
        self._guard(actor, "alert_read")
        with self._lock:
            recs = list(self._recommendations.values())
            if agent_id is not None:
                recs = [r for r in recs if r["agent_id"] == agent_id]
            recs.sort(key=lambda r: _id_num(r["id"]))
            return copy.deepcopy(recs)

    def risk_summary(self, actor, agent_id=None):
        """Counts over recorded signals and recommendations.

        Action: alert_read. Derived at read, stored nowhere;
        counts only -- no score is computed over the labels.
        """
        self._guard(actor, "alert_read")
        with self._lock:
            signals = list(self._risk_signals.values())
            recs = list(self._recommendations.values())
            if agent_id is not None:
                signals = [s for s in signals if s["agent_id"] == agent_id]
                recs = [r for r in recs if r["agent_id"] == agent_id]
            by_label = {}
            for signal in signals:
                label = signal["signal_label"]
                by_label[label] = by_label.get(label, 0) + 1
            return {
                "signals": len(signals),
                "signals_by_label": by_label,
                "recommendations": len(recs),
                "method": "deterministic_counts_over_recorded_signals",
                "derived": True,
            }

    # -- Personnel-security / facility-clearance depth (idx 157, built) --
    # Records form: clearance-case records over a subject already in
    # the core directory (the core directory itself rides a
    # clearance level as an attribute -- the SCCP pattern), with
    # outcome records stored verbatim as reported. The current
    # state is derived at read from the latest outcome; this build
    # adjudicates nothing (``adjudicated_here`` is False).

    def open_clearance_case(self, actor, subject_id, clearance_label):
        """Open a personnel-security case record.

        Action: directory_write. Id prefix: clr-. The subject must
        be an agent or contact already in the core directory;
        ``clearance_label`` is the recorded clearance level as data.
        """
        self._guard(actor, "directory_write")
        _validate_non_empty(clearance_label, "clearance_label")
        with self._lock:
            try:
                self.store.get_agent(subject_id, actor=actor)
            except NotFoundError:
                self.store.get_contact(subject_id, actor=actor)
            case_id = self._next_id("clr")
            now = _utc_now()
            record = {
                "id": case_id,
                "subject_id": subject_id,
                "clearance_label": clearance_label,
                "adjudicated_here": False,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            return self._commit("clr", self._clearance_cases, record, actor,
                                "clearance_case_open",
                                details={"subject_id": subject_id})

    def record_clearance_outcome(self, actor, case_id, outcome_label):
        """Record a reported outcome for a clearance case.

        Action: directory_write. Id prefix: clro-. The label is
        stored verbatim as reported by the personnel-security
        system; nothing is adjudicated here.
        """
        self._guard(actor, "directory_write")
        _validate_non_empty(outcome_label, "outcome_label")
        with self._lock:
            self._get(self._clearance_cases, case_id, "clearance case")
            outcome_id = self._next_id("clro")
            record = {
                "id": outcome_id,
                "case_id": case_id,
                "outcome_label": outcome_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("clro", self._clearance_outcomes, record,
                                actor, "clearance_outcome_record",
                                details={"case_id": case_id})

    def _clearance_view(self, case):
        view = copy.deepcopy(case)
        outcomes = [o for o in self._clearance_outcomes.values()
                    if o["case_id"] == case["id"]]
        outcomes.sort(key=lambda o: _id_num(o["id"]))
        view["current_state"] = (
            outcomes[-1]["outcome_label"] if outcomes else "open")
        view["outcome_count"] = len(outcomes)
        view["derived"] = True
        return view

    def get_clearance_case(self, actor, case_id):
        """One clearance case with derived current state.

        Action: directory_read. The stored record carries no
        ``current_state`` key; it is derived here.
        """
        self._guard(actor, "directory_read")
        with self._lock:
            case = self._get(self._clearance_cases, case_id,
                             "clearance case")
            return self._clearance_view(case)

    def list_clearance_cases(self, actor, subject_id=None):
        """Clearance cases with derived state.

        Action: directory_read.
        """
        self._guard(actor, "directory_read")
        with self._lock:
            cases = list(self._clearance_cases.values())
            if subject_id is not None:
                cases = [c for c in cases if c["subject_id"] == subject_id]
            cases.sort(key=lambda c: _id_num(c["id"]))
            return [self._clearance_view(c) for c in cases]

    # -- Knowledge-base articles (idx 160, built) -------------------------
    # The Customer Service groups' adjudicated form: an article
    # record holding only tags and provenance, with the text in
    # append-only revision records (kbrev-). The current title/body
    # and revision count are derived at read from the latest
    # revision. There is no update or delete API.

    def create_article(self, actor, title, body, tags=None):
        """Create an article and its first revision.

        Action: interaction_write. Id prefixes: kb- / kbrev-.
        """
        self._guard(actor, "interaction_write")
        _validate_non_empty(title, "article title")
        _validate_non_empty(body, "article body")
        tags = self._validate_tags(tags)
        with self._lock:
            article_id = self._next_id("kb")
            now = _utc_now()
            article = {
                "id": article_id,
                "tags": tags,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._articles[article_id] = article
            revision = self._append_revision(actor, article, title, body)
            try:
                self._audit(actor, "kb_article_create", article_id,
                            details={"revision": revision["id"]})
            except Exception:
                del self._article_revisions[revision["id"]]
                self._counters["kbrev"] -= 1
                del self._articles[article_id]
                self._counters["kb"] -= 1
                raise
            return self._article_view(article)

    def revise_article(self, actor, article_id, title=None, body=None):
        """Append a revision to an article. Action: interaction_write.

        Unchanged fields carry forward from the current revision,
        as in the core rule registry. Earlier revisions never
        change.
        """
        self._guard(actor, "interaction_write")
        if title is not None:
            _validate_non_empty(title, "article title")
        if body is not None:
            _validate_non_empty(body, "article body")
        if title is None and body is None:
            raise ValidationError(
                "revise_article requires title and/or body")
        with self._lock:
            article = self._get(self._articles, article_id, "article")
            current = self._current_revision(article_id)
            revision = self._append_revision(
                actor, article,
                title if title is not None else current["title"],
                body if body is not None else current["body"])
            previous_updated = article["updated_utc"]
            article["updated_utc"] = revision["created_utc"]
            try:
                self._audit(actor, "kb_article_revise", article_id,
                            details={"revision": revision["id"]})
            except Exception:
                del self._article_revisions[revision["id"]]
                self._counters["kbrev"] -= 1
                article["updated_utc"] = previous_updated
                raise
            return self._article_view(article)

    @staticmethod
    def _validate_tags(tags):
        if tags is None:
            return []
        if not isinstance(tags, (list, tuple)):
            raise ValidationError("tags must be a list of strings")
        result = []
        for tag in tags:
            if not isinstance(tag, str) or not tag.strip():
                raise ValidationError("each tag must be a non-empty string")
            result.append(tag)
        return result

    def _append_revision(self, actor, article, title, body):
        revision_id = self._next_id("kbrev")
        existing = [r for r in self._article_revisions.values()
                    if r["article_id"] == article["id"]]
        record = {
            "id": revision_id,
            "article_id": article["id"],
            "revision": len(existing) + 1,
            "title": title,
            "body": body,
            "created_by": actor_name(actor),
            "created_utc": _utc_now(),
        }
        self._article_revisions[revision_id] = record
        return record

    def _current_revision(self, article_id):
        revisions = [r for r in self._article_revisions.values()
                     if r["article_id"] == article_id]
        revisions.sort(key=lambda r: r["revision"])
        return revisions[-1]

    def _article_view(self, article):
        view = copy.deepcopy(article)
        current = self._current_revision(article["id"])
        view["title"] = current["title"]
        view["body"] = current["body"]
        view["revision_count"] = len(
            [r for r in self._article_revisions.values()
             if r["article_id"] == article["id"]])
        view["derived"] = True
        return view

    def get_article(self, actor, article_id):
        """One article with derived current text. Action: interaction_read.

        The stored article record holds no title/body keys; the
        current text is derived here from the latest revision.
        """
        self._guard(actor, "interaction_read")
        with self._lock:
            article = self._get(self._articles, article_id, "article")
            return self._article_view(article)

    def list_articles(self, actor):
        """All articles with derived current text.

        Action: interaction_read.
        """
        self._guard(actor, "interaction_read")
        with self._lock:
            articles = sorted(self._articles.values(),
                              key=lambda a: _id_num(a["id"]))
            return [self._article_view(a) for a in articles]

    def list_article_revisions(self, actor, article_id):
        """The full append-only revision history of an article.

        Action: interaction_read.
        """
        self._guard(actor, "interaction_read")
        with self._lock:
            self._get(self._articles, article_id, "article")
            revisions = [r for r in self._article_revisions.values()
                         if r["article_id"] == article_id]
            revisions.sort(key=lambda r: r["revision"])
            return copy.deepcopy(revisions)

    def search_articles(self, actor, query):
        """Literal substring search over current article text.

        Action: interaction_read. The registry-metadata pattern --
        not a search engine.
        """
        self._guard(actor, "interaction_read")
        if not isinstance(query, str) or not query.strip():
            raise ValidationError("query must be a non-empty string")
        needle = query.lower()
        with self._lock:
            results = []
            for article in self._articles.values():
                view = self._article_view(article)
                if (needle in view["title"].lower()
                        or needle in view["body"].lower()):
                    results.append(view)
            results.sort(key=lambda a: _id_num(a["id"]))
            return results

    # -- Satisfaction / CSAT surveys (idx 161, built) ----------------------
    # The Customer Service groups' adjudicated form: an instrument
    # record with its scale as recorded terms, responses storing a
    # rating verbatim (validated against the recorded scale) from a
    # respondent who is a contact already in the core directory,
    # and a tally derived at read with the mean as an exact
    # rational. The stored survey record carries no tally, score,
    # or aggregate key.

    def create_survey(self, actor, name, scale_min=1, scale_max=5,
                      case_id=None):
        """Create a survey instrument. Action: interaction_write.

        Id prefix: svy-. The scale is held as recorded terms
        (integers, ``scale_min`` < ``scale_max``); an optional core
        case link must exist.
        """
        self._guard(actor, "interaction_write")
        _validate_non_empty(name, "survey name")
        for value, what in ((scale_min, "scale_min"),
                            (scale_max, "scale_max")):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError("%s must be an integer" % (what,))
        if scale_min >= scale_max:
            raise ValidationError("scale_min must be below scale_max")
        with self._lock:
            if case_id is not None:
                self.store.get_case(case_id, actor=actor)
            survey_id = self._next_id("svy")
            record = {
                "id": survey_id,
                "name": name,
                "scale_min": scale_min,
                "scale_max": scale_max,
                "case_id": case_id,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("svy", self._surveys, record, actor,
                                "survey_create", details={"name": name})

    def record_survey_response(self, actor, survey_id, respondent_id,
                               rating, comment=None):
        """Record a survey response. Action: interaction_write.

        Id prefix: svr-. The respondent must be a contact already
        in the core directory (an opaque record whose shape cannot
        hold an identifier). ``rating`` must be an integer inside
        the instrument's recorded scale -- booleans and floats are
        rejected -- and is stored verbatim; ``comment`` is stored
        verbatim.
        """
        self._guard(actor, "interaction_write")
        _validate_optional_text(comment, "comment")
        with self._lock:
            survey = self._get(self._surveys, survey_id, "survey")
            self.store.get_contact(respondent_id, actor=actor)
            if isinstance(rating, bool) or not isinstance(rating, int):
                raise ValidationError("rating must be an integer")
            if not survey["scale_min"] <= rating <= survey["scale_max"]:
                raise ValidationError(
                    "rating %r is outside the survey's recorded scale "
                    "%d..%d" % (rating, survey["scale_min"],
                                survey["scale_max"]))
            response_id = self._next_id("svr")
            record = {
                "id": response_id,
                "survey_id": survey_id,
                "respondent_id": respondent_id,
                "rating": rating,
                "comment": comment,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("svr", self._survey_responses, record,
                                actor, "survey_response_record",
                                details={"survey_id": survey_id})

    def get_survey(self, actor, survey_id):
        """One survey instrument record. Action: interaction_read."""
        self._guard(actor, "interaction_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._surveys, survey_id, "survey"))

    def list_survey_responses(self, actor, survey_id):
        """Responses recorded for one survey.

        Action: interaction_read.
        """
        self._guard(actor, "interaction_read")
        with self._lock:
            self._get(self._surveys, survey_id, "survey")
            responses = [r for r in self._survey_responses.values()
                         if r["survey_id"] == survey_id]
            responses.sort(key=lambda r: _id_num(r["id"]))
            return copy.deepcopy(responses)

    def survey_tally(self, actor, survey_id):
        """The survey tally, derived at read. Action: interaction_read.

        Response count, the full-scale distribution, and the mean
        as an exact rational (numerator/denominator over the
        recorded ratings). Stored nowhere; the stored survey record
        carries no tally or score key.
        """
        self._guard(actor, "interaction_read")
        with self._lock:
            survey = self._get(self._surveys, survey_id, "survey")
            responses = [r for r in self._survey_responses.values()
                         if r["survey_id"] == survey_id]
            distribution = {
                str(value): 0
                for value in range(survey["scale_min"],
                                   survey["scale_max"] + 1)
            }
            total = 0
            for response in responses:
                distribution[str(response["rating"])] += 1
                total += response["rating"]
            mean = None
            if responses:
                exact = Fraction(total, len(responses))
                mean = {"numerator": exact.numerator,
                        "denominator": exact.denominator}
            return {
                "survey_id": survey_id,
                "response_count": len(responses),
                "distribution": distribution,
                "mean": mean,
                "method": "exact_rational_mean_of_recorded_ratings",
                "derived": True,
            }

    # -- SLA policy engine (idx 162, built) --------------------------------
    # The Customer Service L2 adjudicated form, extended with this
    # entry's own terms: a policy record holds per-priority
    # resolution targets in minutes as data, plus a business-hour
    # calendar reference and an escalation reference held as data
    # (calendar arithmetic and escalation execution belong to the
    # caller's systems; nothing here escalates or notifies). Breach
    # state under a policy is derived at read from the core case
    # record at the single seam ``_is_breached_under_policy``; a
    # case whose priority is not covered by the policy is never
    # breached under it, and terminal cases are never breached.
    # This derivation coexists with the core's own ``due_at``
    # derivation; neither replaces the other, and no sibling's SLA
    # terms are invented -- the terms are the operator's recorded
    # data.

    def create_sla_policy(self, actor, name, targets_minutes,
                          calendar_ref=None, escalation_ref=None):
        """Create an SLA policy record. Action: rule_write (admin).

        Id prefix: sla-. ``targets_minutes`` maps core priorities
        to positive integer minute targets; unknown priorities and
        boolean/float/non-positive terms are rejected at the
        boundary and consume no id. ``calendar_ref`` and
        ``escalation_ref`` are opaque references held as data.
        """
        self._guard(actor, "rule_write")
        _validate_non_empty(name, "policy name")
        targets = self._validate_targets(targets_minutes)
        _validate_optional_text(calendar_ref, "calendar_ref")
        _validate_optional_text(escalation_ref, "escalation_ref")
        with self._lock:
            policy_id = self._next_id("sla")
            record = {
                "id": policy_id,
                "name": name,
                "targets_minutes": targets,
                "calendar_ref": calendar_ref,
                "escalation_ref": escalation_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("sla", self._sla_policies, record, actor,
                                "sla_policy_create",
                                details={"name": name})

    @staticmethod
    def _validate_targets(targets_minutes):
        if not isinstance(targets_minutes, dict) or not targets_minutes:
            raise ValidationError(
                "targets_minutes must be a non-empty dict of "
                "priority -> minutes")
        result = {}
        for priority, minutes in targets_minutes.items():
            if priority not in KNOWN_PRIORITIES:
                raise ValidationError(
                    "targets_minutes keys must be core priorities: %s"
                    % (", ".join(sorted(KNOWN_PRIORITIES)),))
            if isinstance(minutes, bool) or not isinstance(minutes, int):
                raise ValidationError(
                    "target for priority %r must be an integer number "
                    "of minutes" % (priority,))
            if minutes <= 0:
                raise ValidationError(
                    "target for priority %r must be positive"
                    % (priority,))
            result[priority] = minutes
        return result

    def _is_breached_under_policy(self, case, policy, now_dt):
        """True iff ``case`` is breached under ``policy`` at ``now_dt``.

        MUTATION DRILL NOTE: this seam
        (``ContactExtensions._is_breached_under_policy`` in
        ``src/contact/extensions.py``) is the single derivation
        point for SLA breach under a recorded policy -- the batch's
        fresh negative control mutates it. A case whose priority
        the policy does not cover is never breached under it, a
        terminal case is never breached, and otherwise breach is
        ``now`` past the case's creation time plus the recorded
        target for its priority.
        """
        target = policy["targets_minutes"].get(case["priority"])
        if target is None:
            return False
        if case["status"] in NON_BREACHING_STATUSES:
            return False
        created_dt = _parse_iso_datetime(case["created_utc"], "created_utc")
        return now_dt > created_dt + timedelta(minutes=target)

    def get_sla_policy(self, actor, policy_id):
        """One SLA policy record. Action: rule_read."""
        self._guard(actor, "rule_read")
        with self._lock:
            return copy.deepcopy(
                self._get(self._sla_policies, policy_id, "SLA policy"))

    def list_sla_policies(self, actor):
        """All SLA policy records. Action: rule_read."""
        self._guard(actor, "rule_read")
        with self._lock:
            policies = sorted(self._sla_policies.values(),
                              key=lambda p: _id_num(p["id"]))
            return copy.deepcopy(policies)

    def sla_case_view(self, actor, policy_id, case_id, now=None):
        """A core case view plus its derived state under a policy.

        Action: rule_read (and case_read, via the core). The core
        case record is not touched; the ``sla`` block is derived
        here at read and stored nowhere.
        """
        self._guard(actor, "rule_read")
        now_dt = _coerce_now(now)
        with self._lock:
            policy = self._get(self._sla_policies, policy_id, "SLA policy")
            view = self.store.get_case(case_id, actor=actor, now=now_dt)
            case = self.store._get_case_record(case_id)
            target = policy["targets_minutes"].get(case["priority"])
            effective_due = None
            if target is not None:
                created_dt = _parse_iso_datetime(
                    case["created_utc"], "created_utc")
                effective_due = (
                    created_dt + timedelta(minutes=target)).isoformat()
            view["sla"] = {
                "policy_id": policy_id,
                "covered": target is not None,
                "target_minutes": target,
                "breached_under_policy": self._is_breached_under_policy(
                    case, policy, now_dt),
                "effective_due_at": effective_due,
                "calendar_ref": policy["calendar_ref"],
                "derived": True,
                "stored": False,
            }
            return view

    def sla_breach_report(self, actor, policy_id, now=None):
        """Breach counts under one policy, derived at read.

        Action: rule_read. Counts over core cases: covered and
        breached totals, breached by priority. Stored nowhere.
        """
        self._guard(actor, "rule_read")
        now_dt = _coerce_now(now)
        with self._lock:
            policy = self._get(self._sla_policies, policy_id, "SLA policy")
            cases = self.store.list_cases(actor=actor, now=now_dt)
            covered = 0
            breached = 0
            breached_by_priority = {}
            for view in cases:
                case = self.store._get_case_record(view["id"])
                if case["priority"] not in policy["targets_minutes"]:
                    continue
                covered += 1
                if self._is_breached_under_policy(case, policy, now_dt):
                    breached += 1
                    priority = case["priority"]
                    breached_by_priority[priority] = (
                        breached_by_priority.get(priority, 0) + 1)
            return {
                "policy_id": policy_id,
                "cases_total": len(cases),
                "covered": covered,
                "breached": breached,
                "breached_by_priority": breached_by_priority,
                "method": "deterministic_counts_over_core_records",
                "derived": True,
            }

    # -- Observability collection (idx 154, reference) ---------------------
    # Labeled reference implementation: collection-source references
    # and collection reports holding counts and labels as reported
    # by the collection system. Nothing is collected here and no
    # forecast is computed here (``collected_here`` /
    # ``forecast_computed_here`` are False).

    def register_collection_source(self, actor, source_ref, kind_label):
        """Register a collection-source reference.

        Action: alert_write. Id prefix: obs-. ``kind_label`` is the
        caller's label for the source kind (collector, metric
        collection, forecasting, ...) held as data.
        """
        self._guard(actor, "alert_write")
        _validate_non_empty(source_ref, "source_ref")
        _validate_non_empty(kind_label, "kind_label")
        with self._lock:
            source_id = self._next_id("obs")
            record = {
                "id": source_id,
                "source_ref": source_ref,
                "kind_label": kind_label,
                "reference_stub": True,
                "collected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("obs", self._obs_sources, record, actor,
                                "obs_source_register",
                                details={"source_ref": source_ref})

    def record_collection_report(self, actor, source_id, report_label,
                                 reported_count=None, window_label=None):
        """Record a collection report as reported.

        Action: alert_write. Id prefix: obsr-. Counts and window
        labels are stored verbatim as reported; nothing is
        collected or forecast here.
        """
        self._guard(actor, "alert_write")
        _validate_non_empty(report_label, "report_label")
        reported_count = _validate_count(reported_count, "reported_count")
        _validate_optional_text(window_label, "window_label")
        with self._lock:
            self._get(self._obs_sources, source_id, "collection source")
            report_id = self._next_id("obsr")
            record = {
                "id": report_id,
                "source_id": source_id,
                "report_label": report_label,
                "reported_count": reported_count,
                "window_label": window_label,
                "reference_stub": True,
                "collected_here": False,
                "forecast_computed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("obsr", self._obs_reports, record, actor,
                                "obs_report_record",
                                details={"source_id": source_id})

    def list_collection_sources(self, actor):
        """Collection-source references. Action: alert_read."""
        self._guard(actor, "alert_read")
        with self._lock:
            sources = sorted(self._obs_sources.values(),
                             key=lambda s: _id_num(s["id"]))
            return copy.deepcopy(sources)

    def list_collection_reports(self, actor, source_id=None):
        """Collection reports. Action: alert_read."""
        self._guard(actor, "alert_read")
        with self._lock:
            reports = list(self._obs_reports.values())
            if source_id is not None:
                reports = [r for r in reports
                           if r["source_id"] == source_id]
            reports.sort(key=lambda r: _id_num(r["id"]))
            return copy.deepcopy(reports)

    # -- Voice / telephony & callback connection (idx 155, reference) ------
    # Labeled reference implementation: telephony session records
    # and routing records holding states as reported by the media /
    # ACD systems. No media exists here and nothing connects or
    # routes here (``connected_here`` / ``media_here`` /
    # ``routed_here`` are False). A session reference is opaque --
    # no record shape can hold a phone number.

    def record_telephony_session(self, actor, session_ref, reported_state,
                                 case_id=None, callback_id=None):
        """Record a telephony session as reported.

        Action: callback_write. Id prefix: tel-. Optional core
        case/callback links must exist.
        """
        self._guard(actor, "callback_write")
        _validate_non_empty(session_ref, "session_ref")
        _validate_non_empty(reported_state, "reported_state")
        with self._lock:
            if case_id is not None:
                self.store.get_case(case_id, actor=actor)
            if callback_id is not None:
                self.store.get_callback(callback_id, actor=actor)
            session_id = self._next_id("tel")
            record = {
                "id": session_id,
                "session_ref": session_ref,
                "case_id": case_id,
                "callback_id": callback_id,
                "reported_state": reported_state,
                "reference_stub": True,
                "connected_here": False,
                "media_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("tel", self._tel_sessions, record, actor,
                                "tel_session_record",
                                details={"session_ref": session_ref})

    def record_routing_decision(self, actor, session_id, queue_id,
                                reported_label):
        """Record an ACD routing decision as reported.

        Action: callback_write. Id prefix: route-. The queue must
        exist in the core; recording the decision changes no core
        record -- queue membership and case assignment are
        untouched (``routed_here`` is False).
        """
        self._guard(actor, "callback_write")
        _validate_non_empty(reported_label, "reported_label")
        with self._lock:
            self._get(self._tel_sessions, session_id, "telephony session")
            self.store.get_queue(queue_id, actor=actor)
            routing_id = self._next_id("route")
            record = {
                "id": routing_id,
                "session_id": session_id,
                "queue_id": queue_id,
                "reported_label": reported_label,
                "reference_stub": True,
                "routed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("route", self._routing_records, record,
                                actor, "routing_record",
                                details={"session_id": session_id})

    def list_telephony_sessions(self, actor):
        """Telephony session records. Action: callback_read."""
        self._guard(actor, "callback_read")
        with self._lock:
            sessions = sorted(self._tel_sessions.values(),
                              key=lambda s: _id_num(s["id"]))
            return copy.deepcopy(sessions)

    def list_routing_records(self, actor, session_id=None):
        """Routing records. Action: callback_read."""
        self._guard(actor, "callback_read")
        with self._lock:
            records = list(self._routing_records.values())
            if session_id is not None:
                records = [r for r in records
                           if r["session_id"] == session_id]
            records.sort(key=lambda r: _id_num(r["id"]))
            return copy.deepcopy(records)

    # -- Claims adjudication & fraud detection (idx 156, reference) --------
    # Labeled reference implementation: fraud rule DEFINITIONS held
    # as data in this surface's own registry (never executed --
    # ``executed_here`` is False, and the core rule registry's
    # never-executes doctrine is untouched), plus finding reports
    # storing a detection system's labels verbatim. Nothing is
    # detected or adjudicated here (``detected_here`` /
    # ``adjudicated_here`` are False), and recording a finding
    # changes no core case.

    def register_fraud_rule(self, actor, name, case_type, condition,
                            action_text):
        """Register a fraud rule definition as data.

        Action: rule_write (admin). Id prefix: fr-. ``case_type``
        must be a known core case type or ``"all"``, as in the
        core rule registry. The definition is never executed.
        """
        self._guard(actor, "rule_write")
        _validate_non_empty(name, "rule name")
        if case_type != "all" and case_type not in KNOWN_CASE_TYPES:
            raise ValidationError(
                "case_type must be one of %s or 'all'"
                % (", ".join(sorted(KNOWN_CASE_TYPES)),))
        _validate_non_empty(condition, "rule condition")
        _validate_non_empty(action_text, "rule action_text")
        with self._lock:
            rule_id = self._next_id("fr")
            record = {
                "id": rule_id,
                "name": name,
                "case_type": case_type,
                "condition": condition,
                "action_text": action_text,
                "reference_stub": True,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("fr", self._fraud_rules, record, actor,
                                "fraud_rule_register",
                                details={"name": name})

    def record_fraud_finding(self, actor, case_id, finding_label,
                             rule_id=None):
        """Record a fraud finding as reported. Action: alert_write.

        Id prefix: frf-. The case must exist in the core; the
        finding label is stored verbatim as reported by the
        detection system. Recording a finding changes no core
        record.
        """
        self._guard(actor, "alert_write")
        _validate_non_empty(finding_label, "finding_label")
        with self._lock:
            self.store.get_case(case_id, actor=actor)
            if rule_id is not None:
                self._get(self._fraud_rules, rule_id, "fraud rule")
            finding_id = self._next_id("frf")
            record = {
                "id": finding_id,
                "case_id": case_id,
                "rule_id": rule_id,
                "finding_label": finding_label,
                "reference_stub": True,
                "detected_here": False,
                "adjudicated_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("frf", self._fraud_findings, record, actor,
                                "fraud_finding_record",
                                details={"case_id": case_id})

    def list_fraud_rules(self, actor):
        """Fraud rule definitions. Action: rule_read."""
        self._guard(actor, "rule_read")
        with self._lock:
            rules = sorted(self._fraud_rules.values(),
                           key=lambda r: _id_num(r["id"]))
            return copy.deepcopy(rules)

    def list_fraud_findings(self, actor, case_id=None):
        """Fraud finding reports. Action: alert_read."""
        self._guard(actor, "alert_read")
        with self._lock:
            findings = list(self._fraud_findings.values())
            if case_id is not None:
                findings = [f for f in findings
                            if f["case_id"] == case_id]
            findings.sort(key=lambda f: _id_num(f["id"]))
            return copy.deepcopy(findings)

    # -- Integration connectors (idx 158, reference) -----------------------
    # Labeled reference implementation: connector references and
    # sync reports holding states as reported. Nothing connects or
    # syncs here (``connected_here`` / ``synced_here`` are False);
    # records carry ``reference_stub: True`` and
    # ``reference_transport: True``.

    def register_connector(self, actor, connector_ref, system_label):
        """Register a connector reference. Action: interaction_write.

        Id prefix: con-. ``connector_ref`` is opaque;
        ``system_label`` is the caller's label for the external
        system, held as data.
        """
        self._guard(actor, "interaction_write")
        _validate_non_empty(connector_ref, "connector_ref")
        _validate_non_empty(system_label, "system_label")
        with self._lock:
            connector_id = self._next_id("con")
            record = {
                "id": connector_id,
                "connector_ref": connector_ref,
                "system_label": system_label,
                "reference_stub": True,
                "reference_transport": True,
                "connected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("con", self._connectors, record, actor,
                                "connector_register",
                                details={"connector_ref": connector_ref})

    def record_connector_sync(self, actor, connector_id, reported_state,
                              reported_count=None):
        """Record a connector sync as reported.

        Action: interaction_write. Id prefix: conr-. The state and
        count are stored verbatim as reported; nothing syncs here.
        """
        self._guard(actor, "interaction_write")
        _validate_non_empty(reported_state, "reported_state")
        reported_count = _validate_count(reported_count, "reported_count")
        with self._lock:
            self._get(self._connectors, connector_id, "connector")
            sync_id = self._next_id("conr")
            record = {
                "id": sync_id,
                "connector_id": connector_id,
                "reported_state": reported_state,
                "reported_count": reported_count,
                "reference_stub": True,
                "reference_transport": True,
                "synced_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("conr", self._connector_syncs, record,
                                actor, "connector_sync_record",
                                details={"connector_id": connector_id})

    def list_connectors(self, actor):
        """Connector references. Action: interaction_read."""
        self._guard(actor, "interaction_read")
        with self._lock:
            connectors = sorted(self._connectors.values(),
                                key=lambda c: _id_num(c["id"]))
            return copy.deepcopy(connectors)

    def list_connector_syncs(self, actor, connector_id=None):
        """Connector sync reports. Action: interaction_read."""
        self._guard(actor, "interaction_read")
        with self._lock:
            syncs = list(self._connector_syncs.values())
            if connector_id is not None:
                syncs = [s for s in syncs
                         if s["connector_id"] == connector_id]
            syncs.sort(key=lambda s: _id_num(s["id"]))
            return copy.deepcopy(syncs)

    # -- AI/ML models (idx 159, reference) ----------------------------------
    # Labeled reference implementation: model profile records and
    # reported-output records. Nothing is trained or inferred here
    # (``trained_here`` / ``inference_here`` are False); a reported
    # output is a verbatim label plus an opaque output reference,
    # and recording one creates no alert and changes no core
    # record -- the core's own ingest paths remain the only way
    # core records come to exist.

    def register_model(self, actor, model_ref, capability_label):
        """Register a model profile reference. Action: alert_write.

        Id prefix: ml-. ``model_ref`` is opaque; ``capability_label``
        is the caller's label for the model's capability, held as
        data.
        """
        self._guard(actor, "alert_write")
        _validate_non_empty(model_ref, "model_ref")
        _validate_non_empty(capability_label, "capability_label")
        with self._lock:
            model_id = self._next_id("ml")
            record = {
                "id": model_id,
                "model_ref": model_ref,
                "capability_label": capability_label,
                "reference_stub": True,
                "inference_here": False,
                "trained_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("ml", self._models, record, actor,
                                "model_register",
                                details={"model_ref": model_ref})

    def record_model_output(self, actor, model_id, output_label,
                            output_ref=None, case_id=None, alert_id=None):
        """Record a model output as reported. Action: alert_write.

        Id prefix: mlr-. The output is a verbatim label plus an
        opaque ``output_ref``; optional core case/alert links must
        exist. Recording an output creates no alert and changes no
        core record.
        """
        self._guard(actor, "alert_write")
        _validate_non_empty(output_label, "output_label")
        _validate_optional_text(output_ref, "output_ref")
        with self._lock:
            self._get(self._models, model_id, "model")
            if case_id is not None:
                self.store.get_case(case_id, actor=actor)
            if alert_id is not None:
                self.store.get_alert(alert_id, actor=actor)
            output_id = self._next_id("mlr")
            record = {
                "id": output_id,
                "model_id": model_id,
                "case_id": case_id,
                "alert_id": alert_id,
                "output_label": output_label,
                "output_ref": output_ref,
                "reference_stub": True,
                "inference_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._commit("mlr", self._model_outputs, record, actor,
                                "model_output_record",
                                details={"model_id": model_id})

    def list_models(self, actor):
        """Model profile references. Action: alert_read."""
        self._guard(actor, "alert_read")
        with self._lock:
            models = sorted(self._models.values(),
                            key=lambda m: _id_num(m["id"]))
            return copy.deepcopy(models)

    def list_model_outputs(self, actor, model_id=None):
        """Model output reports. Action: alert_read."""
        self._guard(actor, "alert_read")
        with self._lock:
            outputs = list(self._model_outputs.values())
            if model_id is not None:
                outputs = [o for o in outputs
                           if o["model_id"] == model_id]
            outputs.sort(key=lambda o: _id_num(o["id"]))
            return copy.deepcopy(outputs)
