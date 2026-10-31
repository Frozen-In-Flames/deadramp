"""Records store for the Library Systems L1 merged build.

Clean-room, standard library only. Records hold metadata and opaque
references only: a patron is an opaque ``patron_ref``; no field can
hold a real name or contact detail. A holding's ``available_copies``
and a loan's ``overdue`` and a hold's ``queue_position`` are derived
on read and never stored.

Signature invariant: a holding's active loans never exceed its
quantity, enforced by :meth:`_check_holding_availability` before
every loan is recorded.
"""
import re
from datetime import datetime, timezone

from .access import User, require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

HOLD_STATUSES = ("active", "fulfilled", "cancelled")
LOAN_STATUSES = ("active", "returned")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _parse_time(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 string" % field)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValidationError("%s must parse as ISO-8601: %r" % (field, value))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _require_ref(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _require_int(value, field, minimum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % field)
    if minimum is not None and value < minimum:
        raise ValidationError("%s must be >= %d" % (field, minimum))
    return value


class LibrarySysStore:
    def __init__(self, audit=None):
        self.audit = audit
        self._libraries = {}
        self._items = {}
        self._holdings = {}
        self._loans = {}
        self._holds = {}
        self._integrations = {}
        self._workflows = {}
        self._counters = {}

    # -- internals ------------------------------------------------------
    def _next_id(self, prefix):
        n = self._counters.get(prefix, 0) + 1
        self._counters[prefix] = n
        return "%s-%d" % (prefix, n)

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details)

    def _gate(self, lib_id, actor, action=None):
        lib = self._libraries.get(lib_id)
        if lib is None:
            raise NotFoundError("library not found: %r" % (lib_id,))
        name = actor_name(actor)
        is_admin = isinstance(actor, User) and actor.role == "admin"
        if not is_admin and name not in lib["members"]:
            raise PermissionDenied("actor %r is not a member of this library" % (name,))
        if action is not None and isinstance(actor, User):
            require(actor, action)
        return lib

    def _get_in_lib(self, table, lib_id, obj_id, what):
        obj = table.get(obj_id)
        if obj is None or obj["lib_id"] != lib_id:
            raise NotFoundError("%s not found: %r" % (what, obj_id))
        return obj

    # -- libraries (registry substrate) ---------------------------------
    def create_library(self, library_ref, label, actor):
        if isinstance(actor, User):
            require(actor, "lib_write")
        _require_ref(library_ref, "library_ref")
        _require_ref(label, "label")
        if any(l["library_ref"] == library_ref for l in self._libraries.values()):
            raise ValidationError("duplicate library_ref: %r" % (library_ref,))
        rec = {"id": self._next_id("lib"), "library_ref": library_ref,
               "label": label, "members": [actor_name(actor)],
               "created_by": actor_name(actor), "created_utc": _now()}
        self._libraries[rec["id"]] = rec
        self._audit(actor, "library_create", rec["id"])
        return dict(rec, members=list(rec["members"]))

    def list_libraries(self, actor):
        name = actor_name(actor)
        is_admin = isinstance(actor, User) and actor.role == "admin"
        out = [dict(l, members=list(l["members"])) for l in self._libraries.values()
               if is_admin or name in l["members"]]
        return out

    def get_library(self, lib_id, actor):
        lib = self._gate(lib_id, actor)
        return dict(lib, members=list(lib["members"]))

    def add_member(self, lib_id, username, actor):
        lib = self._libraries.get(lib_id)
        if lib is None:
            raise NotFoundError("library not found: %r" % (lib_id,))
        is_admin = isinstance(actor, User) and actor.role == "admin"
        if not is_admin and actor_name(actor) != lib["created_by"]:
            raise PermissionDenied("only the library creator or a platform admin may add members")
        _require_ref(username, "username")
        if username in lib["members"]:
            raise ValidationError("already a member: %r" % (username,))
        lib["members"].append(username)
        self._audit(actor, "member_add", lib_id)
        return dict(lib, members=list(lib["members"]))

    # -- catalogue items --------------------------------------------------
    def create_item(self, lib_id, item_ref, title, actor, format_label=None):
        self._gate(lib_id, actor, "catalogue_write")
        _require_ref(item_ref, "item_ref"); _require_ref(title, "title")
        if any(i["lib_id"] == lib_id and i["item_ref"] == item_ref for i in self._items.values()):
            raise ValidationError("duplicate item_ref in library: %r" % (item_ref,))
        rec = {"id": self._next_id("cat"), "lib_id": lib_id, "item_ref": item_ref,
               "title": title, "format_label": format_label,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._items[rec["id"]] = rec
        self._audit(actor, "item_create", rec["id"])
        return dict(rec)

    def list_items(self, lib_id, actor):
        self._gate(lib_id, actor)
        return [dict(i) for i in self._items.values() if i["lib_id"] == lib_id]

    def get_item(self, lib_id, item_id, actor):
        self._gate(lib_id, actor)
        return dict(self._get_in_lib(self._items, lib_id, item_id, "item"))

    # -- holdings ---------------------------------------------------------
    def create_holding(self, lib_id, item_id, holding_ref, branch_ref, quantity, actor):
        self._gate(lib_id, actor, "catalogue_write")
        self._get_in_lib(self._items, lib_id, item_id, "item")
        _require_ref(holding_ref, "holding_ref"); _require_ref(branch_ref, "branch_ref")
        _require_int(quantity, "quantity", minimum=1)
        if any(h["lib_id"] == lib_id and h["holding_ref"] == holding_ref for h in self._holdings.values()):
            raise ValidationError("duplicate holding_ref in library: %r" % (holding_ref,))
        rec = {"id": self._next_id("hld"), "lib_id": lib_id, "item_id": item_id,
               "holding_ref": holding_ref, "branch_ref": branch_ref, "quantity": quantity,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._holdings[rec["id"]] = rec
        self._audit(actor, "holding_create", rec["id"])
        return dict(rec)

    def _active_loans_for_holding(self, holding_id):
        return [l for l in self._loans.values()
                if l["holding_id"] == holding_id and l["status"] == "active"]

    def _holding_view(self, holding, now=None):
        view = dict(holding)
        view["available_copies"] = holding["quantity"] - len(
            self._active_loans_for_holding(holding["id"]))
        return view

    def get_holding(self, lib_id, holding_id, actor, now=None):
        self._gate(lib_id, actor)
        h = self._get_in_lib(self._holdings, lib_id, holding_id, "holding")
        return self._holding_view(h, now)

    def list_holdings(self, lib_id, actor, item_id=None, now=None):
        self._gate(lib_id, actor)
        return [self._holding_view(h, now) for h in self._holdings.values()
                if h["lib_id"] == lib_id and (item_id is None or h["item_id"] == item_id)]

    # -- circulation: loans ------------------------------------------------
    def _check_holding_availability(self, holding, active_loan_count):
        """The signature seam: active loans must stay below quantity."""
        if active_loan_count >= holding["quantity"]:
            raise ValidationError(
                "no available copies for holding %r" % (holding["holding_ref"],))

    def record_loan(self, lib_id, holding_id, loan_ref, patron_ref, due_at, actor):
        self._gate(lib_id, actor, "circulation_write")
        holding = self._get_in_lib(self._holdings, lib_id, holding_id, "holding")
        _require_ref(loan_ref, "loan_ref"); _require_ref(patron_ref, "patron_ref")
        _parse_time(due_at, "due_at")
        if any(l["lib_id"] == lib_id and l["loan_ref"] == loan_ref for l in self._loans.values()):
            raise ValidationError("duplicate loan_ref in library: %r" % (loan_ref,))
        self._check_holding_availability(
            holding, len(self._active_loans_for_holding(holding_id)))
        rec = {"id": self._next_id("lon"), "lib_id": lib_id,
               "item_id": holding["item_id"], "holding_id": holding_id,
               "loan_ref": loan_ref, "patron_ref": patron_ref, "due_at": due_at,
               "status": "active", "created_by": actor_name(actor),
               "created_utc": _now()}
        self._loans[rec["id"]] = rec
        self._audit(actor, "loan_record", rec["id"])
        return dict(rec)

    def _loan_view(self, loan, now=None):
        view = dict(loan)
        clock = _parse_time(now, "now") if now else datetime.now(timezone.utc)
        view["overdue"] = bool(loan["status"] == "active"
                               and clock > _parse_time(loan["due_at"], "due_at"))
        return view

    def get_loan(self, lib_id, loan_id, actor, now=None):
        self._gate(lib_id, actor)
        return self._loan_view(self._get_in_lib(self._loans, lib_id, loan_id, "loan"), now)

    def list_loans(self, lib_id, actor, holding_id=None, now=None):
        self._gate(lib_id, actor)
        return [self._loan_view(l, now) for l in self._loans.values()
                if l["lib_id"] == lib_id and (holding_id is None or l["holding_id"] == holding_id)]

    def return_loan(self, lib_id, loan_id, actor):
        self._gate(lib_id, actor, "circulation_write")
        loan = self._get_in_lib(self._loans, lib_id, loan_id, "loan")
        if loan["status"] != "active":
            raise ValidationError("loan is not active: %r" % (loan_id,))
        loan["status"] = "returned"
        self._audit(actor, "loan_return", loan_id)
        return self._loan_view(loan)

    # -- circulation: holds --------------------------------------------------
    def place_hold(self, lib_id, item_id, hold_ref, patron_ref, actor):
        self._gate(lib_id, actor, "circulation_write")
        self._get_in_lib(self._items, lib_id, item_id, "item")
        _require_ref(hold_ref, "hold_ref"); _require_ref(patron_ref, "patron_ref")
        if any(h["lib_id"] == lib_id and h["hold_ref"] == hold_ref for h in self._holds.values()):
            raise ValidationError("duplicate hold_ref in library: %r" % (hold_ref,))
        rec = {"id": self._next_id("hol"), "lib_id": lib_id, "item_id": item_id,
               "hold_ref": hold_ref, "patron_ref": patron_ref, "status": "active",
               "created_by": actor_name(actor), "created_utc": _now()}
        self._holds[rec["id"]] = rec
        self._audit(actor, "hold_place", rec["id"])
        return dict(rec)

    def _hold_view(self, hold):
        view = dict(hold)
        active = [h for h in self._holds.values()
                  if h["item_id"] == hold["item_id"] and h["status"] == "active"]
        view["queue_position"] = (active.index(hold) + 1) if hold in active else None
        return view

    def list_holds(self, lib_id, actor, item_id=None):
        self._gate(lib_id, actor)
        return [self._hold_view(h) for h in self._holds.values()
                if h["lib_id"] == lib_id and (item_id is None or h["item_id"] == item_id)]

    def _close_hold(self, lib_id, hold_id, actor, target_status, action):
        self._gate(lib_id, actor, "circulation_write")
        hold = self._get_in_lib(self._holds, lib_id, hold_id, "hold")
        if hold["status"] != "active":
            raise ValidationError("hold is not active: %r" % (hold_id,))
        hold["status"] = target_status
        self._audit(actor, action, hold_id)
        return self._hold_view(hold)

    def fulfill_hold(self, lib_id, hold_id, actor):
        return self._close_hold(lib_id, hold_id, actor, "fulfilled", "hold_fulfill")

    def cancel_hold(self, lib_id, hold_id, actor):
        return self._close_hold(lib_id, hold_id, actor, "cancelled", "hold_cancel")

    # -- registries ---------------------------------------------------------
    def register_integration(self, lib_id, integration_ref, system_ref, label, actor):
        self._gate(lib_id, actor, "registry_write")
        _require_ref(integration_ref, "integration_ref")
        _require_ref(system_ref, "system_ref"); _require_ref(label, "label")
        if any(i["lib_id"] == lib_id and i["integration_ref"] == integration_ref
               for i in self._integrations.values()):
            raise ValidationError("duplicate integration_ref in library: %r" % (integration_ref,))
        rec = {"id": self._next_id("int"), "lib_id": lib_id,
               "integration_ref": integration_ref, "system_ref": system_ref,
               "label": label, "created_by": actor_name(actor), "created_utc": _now()}
        self._integrations[rec["id"]] = rec
        self._audit(actor, "integration_register", rec["id"])
        return dict(rec)

    def list_integrations(self, lib_id, actor):
        self._gate(lib_id, actor)
        return [dict(i) for i in self._integrations.values() if i["lib_id"] == lib_id]

    def register_workflow(self, lib_id, workflow_ref, label, actor):
        self._gate(lib_id, actor, "registry_write")
        _require_ref(workflow_ref, "workflow_ref"); _require_ref(label, "label")
        if any(w["lib_id"] == lib_id and w["workflow_ref"] == workflow_ref
               for w in self._workflows.values()):
            raise ValidationError("duplicate workflow_ref in library: %r" % (workflow_ref,))
        rec = {"id": self._next_id("wfl"), "lib_id": lib_id,
               "workflow_ref": workflow_ref, "label": label,
               "created_by": actor_name(actor), "created_utc": _now()}
        self._workflows[rec["id"]] = rec
        self._audit(actor, "workflow_register", rec["id"])
        return dict(rec)

    def list_workflows(self, lib_id, actor):
        self._gate(lib_id, actor)
        return [dict(w) for w in self._workflows.values() if w["lib_id"] == lib_id]

    # -- reporting & search ---------------------------------------------------
    def library_report(self, lib_id, actor, now=None):
        if isinstance(actor, User):
            require(actor, "report_read")
        self._gate(lib_id, actor)
        items = [i for i in self._items.values() if i["lib_id"] == lib_id]
        holdings = [h for h in self._holdings.values() if h["lib_id"] == lib_id]
        loans = [self._loan_view(l, now) for l in self._loans.values() if l["lib_id"] == lib_id]
        holds = [h for h in self._holds.values() if h["lib_id"] == lib_id]
        return {
            "lib_id": lib_id,
            "item_count": len(items),
            "holding_count": len(holdings),
            "copies_total": sum(h["quantity"] for h in holdings),
            "available_copies_total": sum(
                h["quantity"] - len(self._active_loans_for_holding(h["id"])) for h in holdings),
            "loan_count": len(loans),
            "active_loans": sum(1 for l in loans if l["status"] == "active"),
            "overdue_loans": sum(1 for l in loans if l["overdue"]),
            "hold_count": len(holds),
            "active_holds": sum(1 for h in holds if h["status"] == "active"),
            "integration_count": sum(1 for i in self._integrations.values() if i["lib_id"] == lib_id),
            "workflow_count": sum(1 for w in self._workflows.values() if w["lib_id"] == lib_id),
        }

    def search_registry(self, actor, query):
        if isinstance(actor, User):
            require(actor, "lib_read")
        if not isinstance(query, str) or not query.strip():
            raise ValidationError("query must be a non-empty string")
        q = query.lower()
        libs = self.list_libraries(actor)
        lib_ids = {l["id"] for l in libs}
        def hit(*fields):
            return any(isinstance(f, str) and q in f.lower() for f in fields)
        return {
            "libraries": [l for l in libs if hit(l["library_ref"], l["label"])],
            "items": [dict(i) for i in self._items.values()
                      if i["lib_id"] in lib_ids and hit(i["item_ref"], i["title"], i["format_label"])],
            "integrations": [dict(i) for i in self._integrations.values()
                             if i["lib_id"] in lib_ids and hit(i["integration_ref"], i["system_ref"], i["label"])],
            "workflows": [dict(w) for w in self._workflows.values()
                          if w["lib_id"] in lib_ids and hit(w["workflow_ref"], w["label"])],
        }
