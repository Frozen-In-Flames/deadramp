import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from librarysys.access import User
from librarysys.audit import AuditLog
from librarysys.store import LibrarySysStore

ALICE = User("alice", "admin"); BOB = User("bob", "member"); CAROL = User("carol", "viewer")
DUE = "2027-01-01T00:00:00+00:00"; PAST = "2020-01-01T00:00:00+00:00"
NOW_LATE = "2027-06-01T00:00:00+00:00"

def seeded():
    store = LibrarySysStore(AuditLog())
    lib = store.create_library("lib-main", "Main Library", ALICE)
    store.add_member(lib["id"], "bob", ALICE); store.add_member(lib["id"], "carol", ALICE)
    item = store.create_item(lib["id"], "item-1", "Catalogued Work", BOB)
    return store, lib, item
