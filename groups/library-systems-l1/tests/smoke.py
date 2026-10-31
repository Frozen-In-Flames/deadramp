"""Manual smoke: PYTHONPATH=src python3 tests/smoke.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from librarysys.access import User
from librarysys.audit import AuditLog
from librarysys.store import LibrarySysStore

s = LibrarySysStore(AuditLog())
alice, bob = User("alice", "admin"), User("bob", "member")
lib = s.create_library("lib-main", "Main Library", alice)
s.add_member(lib["id"], "bob", alice)
item = s.create_item(lib["id"], "item-1", "Catalogued Work", bob)
h = s.create_holding(lib["id"], item["id"], "h-1", "branch-a", 1, bob)
s.record_loan(lib["id"], h["id"], "loan-1", "patron-9", "2027-01-01T00:00:00+00:00", bob)
print("available after loan:", s.get_holding(lib["id"], h["id"], bob)["available_copies"])
print("report:", s.library_report(lib["id"], bob))
