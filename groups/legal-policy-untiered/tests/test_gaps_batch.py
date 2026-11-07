"""Final GAPS batch tests — Legal & Policy, untiered set.

Pins the extension surface in ``src/legalpol/extensions.py`` per
GAPS.md section "Untiered Set 12 -- Legal & Policy (3 forks, tier
null)" (inventory idx 862-864; see ``../BATCH.md`` for the
per-entry disposition), the founding privacy discipline (no record
shape can hold document content, research text, a draft, or query
text — a research query enters as a SHA-256 digest only, mirroring
the core's saved-search design), and this set's tier discipline:
no extension record or view carries a tier, baseline, impact
level, or score-shaped key — those fields do not exist.

The batch's fresh negative control lives here:
``TestLatestStateNegativeControl`` mutates the extension's single
latest-state seam (``_latest_state_label`` — the literal return
line ``return states[-1]["state_label"]`` occurs exactly once in
``extensions.py``) to read the EARLIEST recorded state instead of
the latest, and pins that the canonical expectations reject the
mutant's outcomes — in the FOIA case view's current state, in its
derived overdue flag, in the agency view's by-state counts, and
in the app definition view.
"""

import unittest

from legalpol.errors import (
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from legalpol.extensions import LegalPolExtensions

import legalpol_helpers as H

ADMIN = H.ADMIN
MEMBER = H.MEMBER
VIEWER = H.VIEWER
OUTSIDER = H.OUTSIDER

FORBIDDEN_KEY_FRAGMENTS = (
    "tier", "baseline", "cmmc", "fedramp", "impact_level", "score",
    "rating", "summary", "signature", "content", "query_text",
    "research_text", "draft_text", "extracted",
)


def make_extensions():
    """Fresh store + canonical agency/workspace + extension surface."""
    store, audit, agency = H.make_store()
    workspace = H.make_workspace(store, agency)
    return LegalPolExtensions(store), store, audit, agency, workspace


def make_document(store, agency, workspace, doc_ref="DOC-REF-001",
                  sha256=H.DOC_SHA256):
    return store.register_document(
        agency["id"], workspace["id"], doc_ref, sha256, 128, MEMBER)


def _scan_keys(value, path="root"):
    """Yield (path, key) for every dict key in a nested structure."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield path, key
            yield from _scan_keys(item, path + "." + str(key))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _scan_keys(item, "%s[%d]" % (path, index))


def _scan_values(value):
    """Yield every string value in a nested structure."""
    if isinstance(value, dict):
        for item in value.values():
            yield from _scan_values(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _scan_values(item)
    elif isinstance(value, str):
        yield value


class BatchFixture(unittest.TestCase):
    def setUp(self):
        (self.ext, self.store, self.audit, self.agency,
         self.workspace) = make_extensions()
        self.aid = self.agency["id"]
        self.wid = self.workspace["id"]
        self.workspace2 = self.store.create_workspace(
            self.aid, "WSP-REF-002", "Second Workspace", MEMBER)
        self.doc = make_document(self.store, self.agency, self.workspace)
        self.doc2 = make_document(self.store, self.agency, self.workspace2,
                                  doc_ref="DOC-REF-002", sha256=H.SHA256_A)

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]

    def _research_request(self, request_ref="RSQ-REF-001"):
        return self.ext.record_research_request(
            MEMBER, self.aid, self.wid, request_ref, H.QUERY_SHA256)

    def _foia_case(self, case_ref="FOIA-REF-001", received_on="2026-01-05",
                   period=20):
        return self.ext.create_foia_case(
            MEMBER, self.aid, self.wid, case_ref, "REQ-REF-001",
            "REQUESTER-REF-1", received_on, period)

    def _app(self, app_ref="APP-REF-001", components=("search_panel",)):
        return self.ext.register_app_definition(
            MEMBER, self.aid, self.wid, app_ref, list(components))


class TestResearchReference(BatchFixture):
    """Idx 862 — legal research, evidence mapping & citation
    validation engine (reference, as drafted)."""

    def test_request_shape_pinned(self):
        request = self._research_request()
        self.assertEqual(request["id"], "rsq-1")
        self.assertEqual(
            set(request.keys()),
            {"id", "agency_id", "workspace_id", "request_ref",
             "query_sha256", "reference_stub", "state", "researched_here",
             "created_by", "created_utc"})
        self.assertIs(request["reference_stub"], True)
        self.assertEqual(request["state"], "recorded_reference_only")
        self.assertIs(request["researched_here"], False)
        self.assertEqual(request["query_sha256"], H.QUERY_SHA256)

    def test_query_text_cannot_enter(self):
        with self.assertRaises(TypeError):
            self.ext.record_research_request(
                MEMBER, self.aid, self.wid, "R-1", H.QUERY_SHA256,
                query_text=H.QUERY_TEXT)
        with self.assertRaises(TypeError):
            self.ext.record_research_request(
                MEMBER, self.aid, self.wid, "R-1", H.QUERY_SHA256,
                query=H.QUERY_TEXT)
        with self.assertRaises(ValidationError):
            self.ext.record_research_request(
                MEMBER, self.aid, self.wid, "R-1", "not-a-digest")
        # The query text appears in no field of the stored record.
        request = self._research_request()
        for value in _scan_values(request):
            self.assertNotIn(H.QUERY_TEXT, value)

    def test_duplicate_request_ref_consumes_no_id(self):
        self._research_request()
        with self.assertRaises(ValidationError):
            self._research_request()
        second = self._research_request("RSQ-REF-002")
        self.assertEqual(second["id"], "rsq-2")

    def test_evidence_map_entry_shape_and_locators_verbatim(self):
        request = self._research_request()
        entry = self.ext.record_evidence_map_entry(
            MEMBER, self.aid, request["id"], "MAP-REF-001", "FACT-REF-1",
            "SOURCE-REF-1", page_label="p. 412", line_label="lines 8-14")
        self.assertEqual(entry["id"], "evm-1")
        self.assertEqual(
            set(entry.keys()),
            {"id", "agency_id", "request_id", "map_ref", "fact_ref",
             "source_ref", "page_label", "line_label", "reference_stub",
             "validated_here", "created_by", "created_utc"})
        self.assertEqual(entry["page_label"], "p. 412")
        self.assertEqual(entry["line_label"], "lines 8-14")
        self.assertIs(entry["validated_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_evidence_map_entry(
                MEMBER, self.aid, request["id"], "MAP-REF-001",
                "FACT-REF-2", "SOURCE-REF-2")

    def test_citation_outcome_and_derived_view(self):
        request = self._research_request()
        self.ext.record_evidence_map_entry(
            MEMBER, self.aid, request["id"], "MAP-REF-001", "FACT-REF-1",
            "SOURCE-REF-1")
        self.ext.record_citation_outcome(
            MEMBER, self.aid, request["id"], "OUT-REF-001", "cited_source_ok")
        outcome = self.ext.record_citation_outcome(
            MEMBER, self.aid, request["id"], "OUT-REF-002",
            "citation_unverified")
        self.assertEqual(outcome["id"], "cto-2")
        self.assertIs(outcome["reference_stub"], True)
        self.assertIs(outcome["validated_here"], False)
        view = self.ext.research_request_view(MEMBER, self.aid, request["id"])
        self.assertEqual(view["evidence_map_count"], 1)
        self.assertEqual(view["citation_outcome_count"], 2)
        self.assertEqual(view["latest_outcome_label"], "citation_unverified")
        self.assertEqual(view["draft_link_count"], 0)
        # The stored record carries no derived key.
        stored = self.ext.get_research_request(MEMBER, self.aid,
                                               request["id"])
        self.assertNotIn("latest_outcome_label", stored)
        self.assertNotIn("evidence_map_count", stored)

    def test_draft_link_binds_core_document_in_workspace(self):
        request = self._research_request()
        link = self.ext.record_research_draft_link(
            MEMBER, self.aid, request["id"], self.doc["id"])
        self.assertEqual(link["id"], "rdl-1")
        self.assertIs(link["drafted_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_research_draft_link(
                MEMBER, self.aid, request["id"], self.doc["id"])
        # A document from another workspace does not bind.
        with self.assertRaises(NotFoundError):
            self.ext.record_research_draft_link(
                MEMBER, self.aid, request["id"], self.doc2["id"])
        with self.assertRaises(TypeError):
            self.ext.record_research_draft_link(
                MEMBER, self.aid, request["id"], self.doc["id"],
                draft_text="the draft itself")


class TestFoiaSystemOfRecord(BatchFixture):
    """Idx 863 — FOIA case management system of record (built)."""

    def test_case_shape_pinned_no_derived_keys_stored(self):
        case = self._foia_case()
        self.assertEqual(case["id"], "foi-1")
        self.assertEqual(
            set(case.keys()),
            {"id", "agency_id", "workspace_id", "case_ref", "request_ref",
             "requester_ref", "received_on", "statutory_period_days",
             "released_here", "created_by", "created_utc"})
        self.assertIs(case["released_here"], False)
        self.assertEqual(case["received_on"], "2026-01-05")
        stored = self.ext.get_foia_case(MEMBER, self.aid, case["id"])
        for derived in ("current_state", "due_on", "overdue"):
            self.assertNotIn(derived, stored)

    def test_intake_validation_and_no_id_consumed(self):
        for bad_received in ("Jan 5 2026", "2026-13-01", "", None):
            with self.assertRaises(ValidationError):
                self._foia_case(received_on=bad_received)
        for bad_period in (0, -1, True, 2.5, "20"):
            with self.assertRaises(ValidationError):
                self._foia_case(period=bad_period)
        case = self._foia_case()
        self.assertEqual(case["id"], "foi-1")
        with self.assertRaises(ValidationError):
            self._foia_case()
        second = self._foia_case(case_ref="FOIA-REF-002")
        self.assertEqual(second["id"], "foi-2")
        with self.assertRaises(TypeError):
            self.ext.create_foia_case(
                MEMBER, self.aid, self.wid, "FOIA-REF-003", "REQ-REF-9",
                "REQUESTER-REF-9", "2026-01-05", 20,
                request_text="the request itself")

    def test_current_state_derives_from_latest_recorded(self):
        case = self._foia_case()
        view = self.ext.foia_case_view(MEMBER, self.aid, case["id"],
                                       as_of="2026-01-10")
        self.assertEqual(view["current_state"], "recorded")
        self.ext.record_foia_state(MEMBER, self.aid, case["id"],
                                   "reported_received")
        self.ext.record_foia_state(MEMBER, self.aid, case["id"],
                                   "reported_reviewing")
        view = self.ext.foia_case_view(MEMBER, self.aid, case["id"],
                                       as_of="2026-01-10")
        self.assertEqual(view["current_state"], "reported_reviewing")
        self.assertEqual(view["state_record_count"], 2)
        with self.assertRaises(ValidationError):
            self.ext.record_foia_state(MEMBER, self.aid, case["id"],
                                       "reported_litigated")

    def test_due_date_and_overdue_derive_at_read(self):
        case = self._foia_case(received_on="2026-01-05", period=20)
        # Due date is receipt + 20 days, derived, never stored.
        view = self.ext.foia_case_view(MEMBER, self.aid, case["id"],
                                       as_of="2026-01-25")
        self.assertEqual(view["due_on"], "2026-01-25")
        self.assertIs(view["overdue"], False)
        view = self.ext.foia_case_view(MEMBER, self.aid, case["id"],
                                       as_of="2026-01-26")
        self.assertIs(view["overdue"], True)
        # A terminal recorded state retires the overdue derivation.
        self.ext.record_foia_state(MEMBER, self.aid, case["id"],
                                   "reported_released")
        view = self.ext.foia_case_view(MEMBER, self.aid, case["id"],
                                       as_of="2026-01-26")
        self.assertIs(view["overdue"], False)

    def test_exemption_applications_verbatim_and_tallied(self):
        case = self._foia_case()
        first = self.ext.record_exemption_application(
            MEMBER, self.aid, case["id"], "exemption_6",
            document_id=self.doc["id"])
        self.assertEqual(first["id"], "fxa-1")
        self.assertIs(first["released_here"], False)
        self.ext.record_exemption_application(
            MEMBER, self.aid, case["id"], "exemption_6")
        self.ext.record_exemption_application(
            MEMBER, self.aid, case["id"], "exemption_5")
        view = self.ext.foia_case_view(MEMBER, self.aid, case["id"],
                                       as_of="2026-01-10")
        self.assertEqual(view["exemption_application_count"], 3)
        self.assertEqual(view["exemption_tallies"],
                         {"exemption_6": 2, "exemption_5": 1})
        # A document from another workspace does not bind.
        with self.assertRaises(NotFoundError):
            self.ext.record_exemption_application(
                MEMBER, self.aid, case["id"], "exemption_1",
                document_id=self.doc2["id"])

    def test_releases_recorded_counts_as_reported(self):
        case = self._foia_case()
        release = self.ext.record_foia_release(
            MEMBER, self.aid, case["id"], "REL-REF-001", 12)
        self.assertEqual(release["id"], "frl-1")
        self.assertIs(release["released_here"], False)
        self.ext.record_foia_release(MEMBER, self.aid, case["id"],
                                     "REL-REF-002", 3)
        with self.assertRaises(ValidationError):
            self.ext.record_foia_release(MEMBER, self.aid, case["id"],
                                         "REL-REF-001", 1)
        with self.assertRaises(ValidationError):
            self.ext.record_foia_release(MEMBER, self.aid, case["id"],
                                         "REL-REF-003", -1)
        with self.assertRaises(ValidationError):
            self.ext.record_foia_release(MEMBER, self.aid, case["id"],
                                         "REL-REF-003", True)
        view = self.ext.foia_case_view(MEMBER, self.aid, case["id"],
                                       as_of="2026-01-10")
        self.assertEqual(view["release_count"], 2)
        self.assertEqual(view["reported_released_documents"], 15)

    def test_requester_view_shape_and_values(self):
        case = self._foia_case()
        self.ext.record_foia_state(MEMBER, self.aid, case["id"],
                                   "reported_received")
        self.ext.record_foia_release(MEMBER, self.aid, case["id"],
                                     "REL-REF-001", 4)
        view = self.ext.foia_requester_view(MEMBER, self.aid, case["id"],
                                            as_of="2026-01-26")
        self.assertEqual(
            set(view.keys()),
            {"case_id", "case_ref", "request_ref", "requester_ref",
             "received_on", "current_state", "due_on", "overdue",
             "release_count", "reported_released_documents"})
        self.assertEqual(view["current_state"], "reported_received")
        self.assertEqual(view["due_on"], "2026-01-25")
        self.assertIs(view["overdue"], True)
        self.assertEqual(view["reported_released_documents"], 4)

    def test_agency_view_portfolio_derivation(self):
        first = self._foia_case()
        self.ext.record_foia_state(MEMBER, self.aid, first["id"],
                                   "reported_received")
        self.ext.record_exemption_application(
            MEMBER, self.aid, first["id"], "exemption_6")
        second = self._foia_case(case_ref="FOIA-REF-002",
                                 received_on="2026-01-01", period=20)
        self.ext.record_foia_state(MEMBER, self.aid, second["id"],
                                   "reported_released")
        self.ext.record_exemption_application(
            MEMBER, self.aid, second["id"], "exemption_6")
        self.ext.record_exemption_application(
            MEMBER, self.aid, second["id"], "exemption_5")
        view = self.ext.foia_agency_view(MEMBER, self.aid,
                                         as_of="2026-02-01")
        self.assertEqual(view["case_count"], 2)
        self.assertEqual(view["cases_by_current_state"],
                         {"reported_received": 1, "reported_released": 1})
        self.assertEqual(view["overdue_case_count"], 1)
        self.assertEqual(view["exemption_tallies"],
                         {"exemption_6": 2, "exemption_5": 1})
        self.assertEqual(view["method"], "deterministic_counts")


class TestAppBuilder(BatchFixture):
    """Idx 864 — discovery platform app builder / extensibility
    (built as a definition registry; the registry never executes)."""

    def test_definition_shape_pinned(self):
        app = self._app(components=("search_panel", "export_button"))
        self.assertEqual(app["id"], "app-1")
        self.assertEqual(
            set(app.keys()),
            {"id", "agency_id", "workspace_id", "app_ref", "label",
             "components", "definition_only", "executed_here",
             "runtime_here", "created_by", "created_utc"})
        self.assertEqual(app["components"],
                         ["search_panel", "export_button"])
        self.assertIs(app["definition_only"], True)
        self.assertIs(app["executed_here"], False)
        self.assertIs(app["runtime_here"], False)
        stored = self.ext.get_app_definition(MEMBER, self.aid, app["id"])
        self.assertNotIn("current_state", stored)

    def test_component_manifest_validation(self):
        for bad in ([], ["a", "a"], ["a", 7], "notalist", None):
            with self.assertRaises(ValidationError):
                self.ext.register_app_definition(
                    MEMBER, self.aid, self.wid, "APP-BAD", bad)
        app = self._app()
        self.assertEqual(app["id"], "app-1")
        with self.assertRaises(ValidationError):
            self._app()

    def test_app_state_derives_at_read(self):
        app = self._app()
        view = self.ext.app_definition_view(MEMBER, self.aid, app["id"])
        self.assertEqual(view["current_state"], "recorded")
        self.assertEqual(view["component_count"], 1)
        self.ext.record_app_state(MEMBER, self.aid, app["id"],
                                  "reported_draft")
        self.ext.record_app_state(MEMBER, self.aid, app["id"],
                                  "reported_enabled")
        view = self.ext.app_definition_view(MEMBER, self.aid, app["id"])
        self.assertEqual(view["current_state"], "reported_enabled")
        self.assertEqual(view["state_record_count"], 2)
        with self.assertRaises(ValidationError):
            self.ext.record_app_state(MEMBER, self.aid, app["id"],
                                      "reported_running")

    def test_bindings_and_registry_never_executes(self):
        # Registering definitions, states, and bindings changes no
        # core record: the registry holds data, it runs nothing.
        before_doc = self.store.get_document(self.aid, self.doc["id"],
                                             MEMBER)
        before_report = self.store.agency_report(self.aid, MEMBER)
        app = self._app()
        self.ext.record_app_state(MEMBER, self.aid, app["id"],
                                  "reported_enabled")
        binding = self.ext.record_app_binding(
            MEMBER, self.aid, app["id"], self.workspace2["id"])
        self.assertEqual(binding["id"], "apb-1")
        self.assertIs(binding["executed_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_app_binding(
                MEMBER, self.aid, app["id"], self.workspace2["id"])
        view = self.ext.app_definition_view(MEMBER, self.aid, app["id"])
        self.assertEqual(view["binding_count"], 1)
        self.assertEqual(self.store.get_document(self.aid, self.doc["id"],
                                                 MEMBER), before_doc)
        self.assertEqual(self.store.agency_report(self.aid, MEMBER),
                         before_report)

    def test_binding_to_foreign_agency_workspace_rejected(self):
        other = self.store.create_agency("AGY-REF-002", "Other Agency",
                                         ADMIN)
        other_workspace = self.store.create_workspace(
            other["id"], "WSP-REF-900", "Foreign Workspace", ADMIN)
        app = self._app()
        with self.assertRaises(NotFoundError):
            self.ext.record_app_binding(
                MEMBER, self.aid, app["id"], other_workspace["id"])


class TestExtensionDiscipline(BatchFixture):
    """Cross-cutting: tier-null / no-content scans, RBAC, audit."""

    def _everything(self):
        request = self._research_request()
        self.ext.record_evidence_map_entry(
            MEMBER, self.aid, request["id"], "MAP-REF-001", "FACT-REF-1",
            "SOURCE-REF-1", page_label="p. 1")
        self.ext.record_citation_outcome(
            MEMBER, self.aid, request["id"], "OUT-REF-001", "verified")
        self.ext.record_research_draft_link(
            MEMBER, self.aid, request["id"], self.doc["id"])
        case = self._foia_case()
        self.ext.record_foia_state(MEMBER, self.aid, case["id"],
                                   "reported_received")
        self.ext.record_exemption_application(
            MEMBER, self.aid, case["id"], "exemption_6",
            document_id=self.doc["id"])
        self.ext.record_foia_release(MEMBER, self.aid, case["id"],
                                     "REL-REF-001", 2)
        app = self._app()
        self.ext.record_app_state(MEMBER, self.aid, app["id"],
                                  "reported_enabled")
        self.ext.record_app_binding(MEMBER, self.aid, app["id"],
                                    self.workspace2["id"])
        return [
            request,
            self.ext.research_request_view(MEMBER, self.aid, request["id"]),
            self.ext.list_evidence_map_entries(MEMBER, self.aid,
                                               request["id"]),
            self.ext.list_citation_outcomes(MEMBER, self.aid,
                                            request["id"]),
            self.ext.list_research_draft_links(MEMBER, self.aid,
                                               request["id"]),
            case,
            self.ext.foia_case_view(MEMBER, self.aid, case["id"],
                                    as_of="2026-01-10"),
            self.ext.foia_requester_view(MEMBER, self.aid, case["id"],
                                         as_of="2026-01-10"),
            self.ext.foia_agency_view(MEMBER, self.aid,
                                      as_of="2026-01-10"),
            self.ext.list_foia_states(MEMBER, self.aid, case["id"]),
            self.ext.list_exemption_applications(MEMBER, self.aid,
                                                 case["id"]),
            self.ext.list_foia_releases(MEMBER, self.aid, case["id"]),
            app,
            self.ext.app_definition_view(MEMBER, self.aid, app["id"]),
            self.ext.list_app_states(MEMBER, self.aid, app["id"]),
            self.ext.list_app_bindings(MEMBER, self.aid, app["id"]),
        ]

    def test_no_tier_or_score_shaped_key_anywhere(self):
        """Tier discipline + privacy: a recursive scan over every
        extension record and view finds no tier/baseline/CMMC/
        FedRAMP/impact key, no score-shaped key, and no content
        field."""
        for surface in self._everything():
            for path, key in _scan_keys(surface):
                for fragment in FORBIDDEN_KEY_FRAGMENTS:
                    self.assertNotIn(fragment, key, (path, key))

    def test_rbac_denied_writes_are_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_foia_case(
                VIEWER, self.aid, self.wid, "FOIA-X", "REQ-X",
                "REQUESTER-X", "2026-01-05", 20)
        self.assertIn("ext_foia_case:denied", self.audit_actions())
        with self.assertRaises(PermissionDenied):
            self.ext.record_research_request(
                VIEWER, self.aid, self.wid, "RSQ-X", H.QUERY_SHA256)
        self.assertIn("ext_research_request:denied", self.audit_actions())

    def test_membership_boundary_binds_reads(self):
        self._foia_case()
        with self.assertRaises(PermissionDenied):
            self.ext.list_foia_cases(OUTSIDER, self.aid)
        with self.assertRaises(PermissionDenied):
            self.ext.foia_agency_view(OUTSIDER, self.aid)

    def test_successful_writes_are_audited(self):
        self._research_request()
        self._foia_case()
        self._app()
        for action in ("ext_research_request", "ext_foia_case",
                       "ext_app_definition"):
            self.assertIn(action, self.audit_actions())


class MutantLatestExtensions(LegalPolExtensions):
    """Mutant: the latest-state seam reads the EARLIEST recorded
    state instead of the latest."""

    @staticmethod
    def _latest_state_label(states):
        if not states:
            return "recorded"
        return states[0]["state_label"]


class TestLatestStateNegativeControl(unittest.TestCase):
    """Fresh mutation-verified negative control (batch).

    Canonical expectation: with FOIA states [reported_received,
    reported_released] recorded in that order, the derived current
    state is the LATEST label, ``reported_released`` — a terminal
    state, so the case is not overdue even past its due date; and
    an app definition with states [reported_draft,
    reported_enabled] currently reads ``reported_enabled``. The
    mutant (earliest-label derivation) must NOT produce those
    outcomes, and treating the mutant's outcomes as the expected
    outcomes must fail.
    """

    def _build(self, ext_class):
        store, audit, agency = H.make_store()
        workspace = H.make_workspace(store, agency)
        ext = ext_class(store)
        case = ext.create_foia_case(
            MEMBER, agency["id"], workspace["id"], "FOIA-REF-001",
            "REQ-REF-001", "REQUESTER-REF-1", "2026-01-05", 20)
        ext.record_foia_state(MEMBER, agency["id"], case["id"],
                              "reported_received")
        ext.record_foia_state(MEMBER, agency["id"], case["id"],
                              "reported_released")
        app = ext.register_app_definition(
            MEMBER, agency["id"], workspace["id"], "APP-REF-001",
            ["search_panel"])
        ext.record_app_state(MEMBER, agency["id"], app["id"],
                             "reported_draft")
        ext.record_app_state(MEMBER, agency["id"], app["id"],
                             "reported_enabled")
        return ext, agency, case, app

    def test_current_state_is_latest_canonical(self):
        ext, agency, case, app = self._build(LegalPolExtensions)
        view = ext.foia_case_view(MEMBER, agency["id"], case["id"],
                                  as_of="2026-02-01")
        self.assertEqual(view["current_state"], "reported_released")
        self.assertIs(view["overdue"], False)
        app_view = ext.app_definition_view(MEMBER, agency["id"], app["id"])
        self.assertEqual(app_view["current_state"], "reported_enabled")

    def test_mutant_reads_earliest_not_latest(self):
        ext, agency, case, app = self._build(MutantLatestExtensions)
        view = ext.foia_case_view(MEMBER, agency["id"], case["id"],
                                  as_of="2026-02-01")
        self.assertEqual(view["current_state"], "reported_received")
        self.assertIs(view["overdue"], True)
        app_view = ext.app_definition_view(MEMBER, agency["id"], app["id"])
        self.assertEqual(app_view["current_state"], "reported_draft")

    def test_canonical_expectation_rejects_mutant(self):
        ext, agency, case, _app = self._build(MutantLatestExtensions)
        view = ext.foia_case_view(MEMBER, agency["id"], case["id"],
                                  as_of="2026-02-01")
        with self.assertRaises(AssertionError):
            self.assertEqual(view["current_state"], "reported_released")
        with self.assertRaises(AssertionError):
            self.assertIs(view["overdue"], False)

    def test_mutant_changes_agency_view_counts(self):
        canonical, agency, _case, _app = self._build(LegalPolExtensions)
        mutant, agency2, _case2, _app2 = self._build(MutantLatestExtensions)
        self.assertEqual(
            canonical.foia_agency_view(
                MEMBER, agency["id"], as_of="2026-02-01")
            ["cases_by_current_state"], {"reported_released": 1})
        self.assertEqual(
            canonical.foia_agency_view(
                MEMBER, agency["id"], as_of="2026-02-01")
            ["overdue_case_count"], 0)
        self.assertEqual(
            mutant.foia_agency_view(
                MEMBER, agency2["id"], as_of="2026-02-01")
            ["cases_by_current_state"], {"reported_received": 1})
        self.assertEqual(
            mutant.foia_agency_view(
                MEMBER, agency2["id"], as_of="2026-02-01")
            ["overdue_case_count"], 1)


if __name__ == "__main__":
    unittest.main()
