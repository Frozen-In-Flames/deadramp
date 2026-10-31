"""HTTP service layer. Auth via X-User / X-Role headers against the
user registry supplied by the embedding organization (hooks, not an
IdP). Denied attempts are audited; no stack trace is ever returned."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from .access import User, require
from .errors import LibrarySysError, NotFoundError, PermissionDenied, ValidationError

STATUS = {ValidationError: 400, PermissionDenied: 403, NotFoundError: 404}


def make_server(host, port, store, audit, users):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def log_message(self, *a): pass
        def _send(self, code, payload):
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)
        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}") if n else {}
        def _user(self):
            name = self.headers.get("X-User"); role = self.headers.get("X-Role")
            if name is None or users.get(name) != role:
                raise PermissionDenied("unknown user or mismatched role")
            return User(name, role)
        def _run(self, fn, action, code=200):
            try:
                user = self._user(); require(user, action)
                self._send(code, fn(user))
            except PermissionDenied as e:
                audit.record(self.headers.get("X-User"), action + ":denied", self.path)
                self._send(403, {"error": str(e)})
            except LibrarySysError as e:
                self._send(STATUS.get(type(e), 400), {"error": str(e)})
            except Exception as e:
                self._send(400, {"error": str(e)})
        def _parts(self):
            u = urlparse(self.path)
            return [p for p in u.path.split("/") if p], parse_qs(u.query)
        def do_GET(self):
            parts, q = self._parts()
            if parts == ["health"]:
                return self._send(200, {"status": "ok"})
            if parts == ["audit"]:
                return self._run(lambda u: {"entries": audit.entries()}, "audit_read")
            if parts == ["libraries"]:
                return self._run(lambda u: {"libraries": store.list_libraries(u)}, "lib_read")
            if parts == ["search"]:
                return self._run(lambda u: store.search_registry(u, (q.get("q") or [""])[0]), "lib_read")
            if len(parts) >= 2 and parts[0] == "libraries":
                lib = parts[1]
                if len(parts) == 2:
                    return self._run(lambda u: store.get_library(lib, u), "lib_read")
                if parts[2] == "items" and len(parts) == 3:
                    return self._run(lambda u: {"items": store.list_items(lib, u)}, "lib_read")
                if parts[2] == "holdings" and len(parts) == 3:
                    return self._run(lambda u: {"holdings": store.list_holdings(lib, u, item_id=(q.get("item_id") or [None])[0])}, "lib_read")
                if parts[2] == "loans" and len(parts) == 3:
                    return self._run(lambda u: {"loans": store.list_loans(lib, u)}, "lib_read")
                if parts[2] == "holds" and len(parts) == 3:
                    return self._run(lambda u: {"holds": store.list_holds(lib, u)}, "lib_read")
                if parts[2] == "integrations" and len(parts) == 3:
                    return self._run(lambda u: {"integrations": store.list_integrations(lib, u)}, "lib_read")
                if parts[2] == "workflows" and len(parts) == 3:
                    return self._run(lambda u: {"workflows": store.list_workflows(lib, u)}, "lib_read")
                if parts[2] == "report" and len(parts) == 3:
                    return self._run(lambda u: store.library_report(lib, u), "report_read")
            return self._send(404, {"error": "not found"})
        def do_POST(self):
            parts, q = self._parts()
            b = self._body() if self.command == "POST" else {}
            if parts == ["libraries"]:
                return self._run(lambda u: store.create_library(b["library_ref"], b["label"], u), "lib_write", 201)
            if len(parts) >= 2 and parts[0] == "libraries":
                lib = parts[1]
                if parts[2:] == ["members"]:
                    return self._run(lambda u: store.add_member(lib, b["username"], u), "lib_read")
                if parts[2:] == ["items"]:
                    return self._run(lambda u: store.create_item(lib, b["item_ref"], b["title"], u, format_label=b.get("format_label")), "catalogue_write", 201)
                if parts[2:] == ["holdings"]:
                    return self._run(lambda u: store.create_holding(lib, b["item_id"], b["holding_ref"], b["branch_ref"], b["quantity"], u), "catalogue_write", 201)
                if parts[2:] == ["loans"]:
                    return self._run(lambda u: store.record_loan(lib, b["holding_id"], b["loan_ref"], b["patron_ref"], b["due_at"], u), "circulation_write", 201)
                if len(parts) == 5 and parts[2] == "loans" and parts[4] == "return":
                    return self._run(lambda u: store.return_loan(lib, parts[3], u), "circulation_write")
                if parts[2:] == ["holds"]:
                    return self._run(lambda u: store.place_hold(lib, b["item_id"], b["hold_ref"], b["patron_ref"], u), "circulation_write", 201)
                if len(parts) == 5 and parts[2] == "holds" and parts[4] in ("fulfill", "cancel"):
                    fn = store.fulfill_hold if parts[4] == "fulfill" else store.cancel_hold
                    return self._run(lambda u: fn(lib, parts[3], u), "circulation_write")
                if parts[2:] == ["integrations"]:
                    return self._run(lambda u: store.register_integration(lib, b["integration_ref"], b["system_ref"], b["label"], u), "registry_write", 201)
                if parts[2:] == ["workflows"]:
                    return self._run(lambda u: store.register_workflow(lib, b["workflow_ref"], b["label"], u), "registry_write", 201)
            return self._send(404, {"error": "not found"})
    return ThreadingHTTPServer((host, port), Handler)
