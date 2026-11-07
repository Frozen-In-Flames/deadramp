"""Final GAPS batch tests — Group 34 (Law Enforcement L2).

Pins the extension surface in ``src/lawenf/extensions.py``
against the group's 6 open Extended entries (see ``../BATCH.md``):

- The legal corpora themselves (idx 347) — built: corpus
  registrations, corpus-source links, maintenance and license
  records; content is never held.
- Citation-validation engines (idx 348) — built: validation
  requests + reported determinations, treatment verbatim,
  nothing determined here.
- Editorial enhancement systems (idx 349) — built: headnote
  records by digest, taxonomy assignments verbatim, enrichment
  stage reports.
- Corpus search & relevance engines (idx 350) — reference:
  run/outcome records, query named by digest only.
- AI/ML research assistance (idx 351) — reference:
  request/outcome records, no inference here.
- Document content storage, rendering & redaction (idx 352) —
  built: deposit/render/redaction records over core documents;
  recording one leaves the core document byte-identical.

Plus the batch's fresh negative control: the latest-label seam
``_latest_label`` — a mutant that reads the earliest record
must misstate every derived "latest" label.
"""

import hashlib
import inspect
import unittest

import lawenf_helpers as helpers
from lawenf.errors import (
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from lawenf.extensions import LawEnfExtensions

ADMIN = helpers.ADMIN
MEMBER = helpers.MEMBER
VIEWER = helpers.VIEWER
OUTSIDER = helpers.OUTSIDER

DOC_SHA256 = helpers.DOC_SHA256
QUERY_SHA256 = helpers.QUERY_SHA256
NOTE_SHA256 = helpers.NOTE_SHA256
OTHER_SHA256 = hashlib.sha256(b"redacted output bytes").hexdigest()


def make_ext():
    """Fresh core store + audit + matter, plus the extension."""
    store, audit, matter = helpers.make_store()
    return store, audit, matter, LawEnfExtensions(store)


def make_source(store, matter_id, ref="SRC-REF-1"):
    return store.create_source(matter_id, ref, "case_law", MEMBER)


def make_document(store, matter_id, ref="DOC-REF-1"):
    return store.register_document(matter_id, ref, DOC_SHA256, 128, MEMBER)


class TestCorporaBuilt(unittest.TestCase):
    """Idx 347 — the corpus registry surface; content never held."""

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]

    def test_register_shape_and_labels(self):
        corpus = self.ext.register_corpus(
            self.mid, "CORPUS-PRIMARY", "primary law, all jurisdictions",
            MEMBER)
        self.assertEqual(corpus["id"], "cor-1")
        self.assertEqual(corpus["corpus_ref"], "CORPUS-PRIMARY")
        self.assertEqual(
            corpus["coverage_label"], "primary law, all jurisdictions")
        self.assertFalse(corpus["content_held"])
        self.assertNotIn("reference_stub", corpus)

    def test_duplicate_ref_rejected_and_no_id_consumed(self):
        self.ext.register_corpus(self.mid, "CORPUS-A", "a", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_corpus(self.mid, "CORPUS-A", "again", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_corpus(self.mid, "CORPUS-B", "  ", MEMBER)
        second = self.ext.register_corpus(self.mid, "CORPUS-B", "b", MEMBER)
        self.assertEqual(second["id"], "cor-2")

    def test_link_binds_core_source_in_same_matter(self):
        corpus = self.ext.register_corpus(self.mid, "C", "cov", MEMBER)
        source = make_source(self.store, self.mid)
        link = self.ext.link_corpus_source(
            self.mid, corpus["id"], source["id"], MEMBER)
        self.assertEqual(link["id"], "csl-1")
        self.assertEqual(link["source_id"], source["id"])
        self.assertFalse(link["content_held"])
        self.assertEqual(
            len(self.ext.list_corpus_links(self.mid, corpus["id"], ADMIN)), 1)

    def test_link_to_cross_matter_source_rejected(self):
        corpus = self.ext.register_corpus(self.mid, "C", "cov", MEMBER)
        other = self.store.create_matter("MATTER-REF-002", MEMBER)
        foreign = make_source(self.store, other["id"], "SRC-FOREIGN")
        with self.assertRaises(NotFoundError):
            self.ext.link_corpus_source(
                self.mid, corpus["id"], foreign["id"], MEMBER)

    def test_maintenance_and_license_verbatim(self):
        corpus = self.ext.register_corpus(self.mid, "C", "cov", MEMBER)
        event = self.ext.record_corpus_maintenance(
            self.mid, corpus["id"], "Weekly Update #42 (West)", MEMBER)
        self.assertEqual(event["event_label"], "Weekly Update #42 (West)")
        self.assertFalse(event["maintained_here"])
        lic = self.ext.record_corpus_license(
            self.mid, corpus["id"], "Agency-wide, 12 seats", MEMBER)
        self.assertEqual(lic["license_label"], "Agency-wide, 12 seats")
        self.assertFalse(lic["content_held"])

    def test_view_derives_counts_and_latest(self):
        corpus = self.ext.register_corpus(self.mid, "C", "cov", MEMBER)
        source = make_source(self.store, self.mid)
        empty = self.ext.corpus_view(self.mid, corpus["id"], ADMIN)
        self.assertEqual(empty["linked_source_count"], 0)
        self.assertIsNone(empty["latest_maintenance_label"])
        self.ext.link_corpus_source(self.mid, corpus["id"], source["id"],
                                    MEMBER)
        self.ext.record_corpus_maintenance(
            self.mid, corpus["id"], "initial-load", MEMBER)
        self.ext.record_corpus_maintenance(
            self.mid, corpus["id"], "weekly-update", MEMBER)
        self.ext.record_corpus_license(self.mid, corpus["id"], "terms",
                                       MEMBER)
        view = self.ext.corpus_view(self.mid, corpus["id"], ADMIN)
        self.assertTrue(view["derived"])
        self.assertEqual(view["linked_source_count"], 1)
        self.assertEqual(view["maintenance_count"], 2)
        self.assertEqual(view["license_count"], 1)
        self.assertEqual(view["latest_maintenance_label"], "weekly-update")
        # The stored corpus record carries no derived key.
        stored = self.ext.get_corpus(self.mid, corpus["id"], ADMIN)
        self.assertNotIn("maintenance_count", stored)
        self.assertNotIn("latest_maintenance_label", stored)


class TestValidationBuilt(unittest.TestCase):
    """Idx 348 — validation requests; treatments reported, never
    determined here."""

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]

    def test_request_shape_and_source_binding(self):
        source = make_source(self.store, self.mid)
        req = self.ext.request_citation_validation(
            self.mid, "VAL-1", MEMBER, source_id=source["id"])
        self.assertEqual(req["id"], "val-1")
        self.assertEqual(req["source_id"], source["id"])
        self.assertFalse(req["determined_here"])
        with self.assertRaises(NotFoundError):
            self.ext.request_citation_validation(
                self.mid, "VAL-2", MEMBER, source_id="src-99")

    def test_determination_verbatim_and_view(self):
        req = self.ext.request_citation_validation(self.mid, "VAL-1", MEMBER)
        det = self.ext.record_validation_determination(
            self.mid, req["id"], "Followed; but see 2024 WL 118", MEMBER,
            engine_label="external-citator")
        self.assertEqual(det["treatment"], "Followed; but see 2024 WL 118")
        self.assertFalse(det["determined_here"])
        self.ext.record_validation_determination(
            self.mid, req["id"], "Distinguished", MEMBER)
        view = self.ext.validation_view(self.mid, req["id"], ADMIN)
        self.assertEqual(view["determination_count"], 2)
        self.assertEqual(view["latest_treatment"], "Distinguished")
        # No core citation check was created by the extension.
        self.assertEqual(self.store.list_citation_checks(self.mid, ADMIN),
                         [])


class TestEnhancementBuilt(unittest.TestCase):
    """Idx 349 — headnotes by digest, assignments verbatim,
    enrichment reports."""

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]
        self.source = make_source(self.store, self.mid)

    def test_headnote_shape_digest_only(self):
        head = self.ext.record_headnote(
            self.mid, "HN-1", self.source["id"], NOTE_SHA256, MEMBER)
        self.assertEqual(head["id"], "hed-1")
        self.assertEqual(head["note_sha256"], NOTE_SHA256)
        self.assertFalse(head["content_held"])
        with self.assertRaises(ValidationError):
            self.ext.record_headnote(
                self.mid, "HN-2", self.source["id"], "not-a-digest", MEMBER)

    def test_assignment_and_enrichment_verbatim(self):
        asg = self.ext.record_taxonomy_assignment(
            self.mid, "TX-1", self.source["id"], "Key Number 101k5", MEMBER)
        self.assertEqual(asg["class_label"], "Key Number 101k5")
        self.assertFalse(asg["assigned_here"])
        enr = self.ext.record_enrichment_report(
            self.mid, "ENR-1", self.source["id"], "headnote-pass",
            "Completed (vendor)", MEMBER)
        self.assertEqual(enr["outcome_label"], "Completed (vendor)")
        self.assertFalse(enr["enriched_here"])

    def test_enhancement_view(self):
        self.ext.record_headnote(
            self.mid, "HN-1", self.source["id"], NOTE_SHA256, MEMBER)
        self.ext.record_taxonomy_assignment(
            self.mid, "TX-1", self.source["id"], "Class A", MEMBER)
        self.ext.record_taxonomy_assignment(
            self.mid, "TX-2", self.source["id"], "Class B", MEMBER)
        view = self.ext.enhancement_view(self.mid, self.source["id"], ADMIN)
        self.assertEqual(view["headnote_count"], 1)
        self.assertEqual(view["assignment_count"], 2)
        self.assertEqual(view["enrichment_count"], 0)
        self.assertEqual(view["latest_class_label"], "Class B")


class TestCorpusSearchReference(unittest.TestCase):
    """Idx 350 — corpus search runs are labeled reference records;
    the query is a digest, never text."""

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]

    def test_run_shape_and_stub_labels(self):
        run = self.ext.record_corpus_search_run(
            self.mid, "RUN-1", QUERY_SHA256, MEMBER,
            engine_label="vendor-corpus-engine")
        self.assertEqual(run["id"], "csr-1")
        self.assertTrue(run["reference_stub"])
        self.assertFalse(run["searched_here"])
        self.assertFalse(run["ranked_here"])
        self.assertEqual(run["status"], "recorded_reference_only")
        self.assertEqual(run["query_sha256"], QUERY_SHA256)
        with self.assertRaises(ValidationError):
            self.ext.record_corpus_search_run(
                self.mid, "RUN-2", "plain text query", MEMBER)

    def test_outcome_and_result_count_validation(self):
        run = self.ext.record_corpus_search_run(
            self.mid, "RUN-1", QUERY_SHA256, MEMBER)
        out = self.ext.record_corpus_search_outcome(
            self.mid, run["id"], "completed-elsewhere", MEMBER,
            result_count=17)
        self.assertTrue(out["reference_stub"])
        self.assertEqual(out["result_count"], 17)
        for bad in (True, 1.5, -1):
            with self.assertRaises(ValidationError):
                self.ext.record_corpus_search_outcome(
                    self.mid, run["id"], "x", MEMBER, result_count=bad)
        view = self.ext.corpus_search_view(self.mid, run["id"], ADMIN)
        self.assertEqual(view["outcome_count"], 1)
        self.assertEqual(view["latest_outcome"], "completed-elsewhere")


class TestAssistanceReference(unittest.TestCase):
    """Idx 351 — assistance requests are labeled reference records;
    no inference runs here."""

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]

    def test_request_shape_and_stub_labels(self):
        req = self.ext.record_assistance_request(
            self.mid, "ASK-1", MEMBER, model_label="vendor-assistant",
            prompt_sha256=QUERY_SHA256)
        self.assertEqual(req["id"], "asr-1")
        self.assertTrue(req["reference_stub"])
        self.assertFalse(req["inference_here"])
        self.assertFalse(req["assisted_here"])
        self.assertEqual(req["status"], "recorded_reference_only")
        with self.assertRaises(ValidationError):
            self.ext.record_assistance_request(
                self.mid, "ASK-2", MEMBER, prompt_sha256="the prompt itself")

    def test_outcome_and_view(self):
        req = self.ext.record_assistance_request(self.mid, "ASK-1", MEMBER)
        out = self.ext.record_assistance_outcome(
            self.mid, req["id"], "answered-elsewhere", MEMBER,
            result_ref="answer-9")
        self.assertTrue(out["reference_stub"])
        self.assertFalse(out["output_held"])
        view = self.ext.assistance_view(self.mid, req["id"], ADMIN)
        self.assertEqual(view["outcome_count"], 1)
        self.assertEqual(view["latest_outcome"], "answered-elsewhere")


class TestDocumentOperationsBuilt(unittest.TestCase):
    """Idx 352 — content operation records over core documents;
    the core document is never changed by recording one."""

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]
        self.doc = make_document(self.store, self.mid)

    def test_deposit_render_redaction_shapes(self):
        dep = self.ext.record_content_deposit(
            self.mid, "DEP-1", self.doc["id"], "vault-ref-7", MEMBER)
        self.assertEqual(dep["id"], "dep-1")
        self.assertFalse(dep["stored_here"])
        self.assertFalse(dep["content_held"])
        ren = self.ext.record_render(
            self.mid, "REN-1", self.doc["id"], "PDF/A", MEMBER,
            output_sha256=OTHER_SHA256)
        self.assertEqual(ren["format_label"], "PDF/A")
        self.assertFalse(ren["rendered_here"])
        red = self.ext.record_redaction(
            self.mid, "RED-1", self.doc["id"], "applied-elsewhere", MEMBER,
            output_ref="doc-redacted-1", output_sha256=OTHER_SHA256)
        self.assertEqual(red["outcome_label"], "applied-elsewhere")
        self.assertFalse(red["redacted_here"])
        self.assertFalse(red["content_held"])

    def test_core_document_byte_identical_after_operations(self):
        before = self.store.get_document(self.mid, self.doc["id"], ADMIN)
        self.ext.record_content_deposit(
            self.mid, "DEP-1", self.doc["id"], "vault-ref-7", MEMBER)
        self.ext.record_render(
            self.mid, "REN-1", self.doc["id"], "HTML", MEMBER)
        self.ext.record_redaction(
            self.mid, "RED-1", self.doc["id"], "applied-elsewhere", MEMBER)
        after = self.store.get_document(self.mid, self.doc["id"], ADMIN)
        self.assertEqual(before, after)

    def test_unknown_document_rejected_and_view(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_content_deposit(
                self.mid, "DEP-X", "doc-99", "vault", MEMBER)
        self.ext.record_redaction(
            self.mid, "RED-1", self.doc["id"], "pending", MEMBER)
        self.ext.record_redaction(
            self.mid, "RED-2", self.doc["id"], "applied-elsewhere", MEMBER)
        view = self.ext.document_operations_view(
            self.mid, self.doc["id"], ADMIN)
        self.assertEqual(view["deposit_count"], 0)
        self.assertEqual(view["redaction_count"], 2)
        self.assertEqual(
            view["latest_redaction_outcome"], "applied-elsewhere")


class TestPrivacyShapePins(unittest.TestCase):
    """The hard privacy rule over the new surface: exact key sets,
    and no signature that could accept content or identity."""

    BANNED_PARAMS = {
        "content", "body", "text", "query_text", "note_text",
        "headnote_text", "prompt", "prompt_text", "subject",
        "subject_name", "person_name", "name", "email", "address",
    }

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]
        self.source = make_source(self.store, self.mid)
        self.doc = make_document(self.store, self.mid)

    def test_exact_key_sets(self):
        corpus = self.ext.register_corpus(self.mid, "C", "cov", MEMBER)
        self.assertEqual(set(corpus), {
            "id", "matter_id", "corpus_ref", "coverage_label",
            "content_held", "created_by", "created_utc"})
        link = self.ext.link_corpus_source(
            self.mid, corpus["id"], self.source["id"], MEMBER)
        self.assertEqual(set(link), {
            "id", "matter_id", "corpus_id", "source_id", "content_held",
            "created_by", "created_utc"})
        maint = self.ext.record_corpus_maintenance(
            self.mid, corpus["id"], "evt", MEMBER)
        self.assertEqual(set(maint), {
            "id", "matter_id", "corpus_id", "event_label",
            "maintained_here", "created_by", "created_utc"})
        lic = self.ext.record_corpus_license(
            self.mid, corpus["id"], "terms", MEMBER)
        self.assertEqual(set(lic), {
            "id", "matter_id", "corpus_id", "license_label",
            "content_held", "created_by", "created_utc"})
        req = self.ext.request_citation_validation(self.mid, "V", MEMBER)
        self.assertEqual(set(req), {
            "id", "matter_id", "validation_ref", "source_id",
            "determined_here", "created_by", "created_utc"})
        det = self.ext.record_validation_determination(
            self.mid, req["id"], "Followed", MEMBER)
        self.assertEqual(set(det), {
            "id", "matter_id", "validation_id", "treatment",
            "engine_label", "determined_here", "created_by", "created_utc"})
        head = self.ext.record_headnote(
            self.mid, "HN", self.source["id"], NOTE_SHA256, MEMBER)
        self.assertEqual(set(head), {
            "id", "matter_id", "headnote_ref", "source_id", "note_sha256",
            "content_held", "created_by", "created_utc"})
        asg = self.ext.record_taxonomy_assignment(
            self.mid, "TX", self.source["id"], "K1", MEMBER)
        self.assertEqual(set(asg), {
            "id", "matter_id", "assignment_ref", "source_id", "class_label",
            "assigned_here", "created_by", "created_utc"})
        enr = self.ext.record_enrichment_report(
            self.mid, "ENR", self.source["id"], "stage", "done", MEMBER)
        self.assertEqual(set(enr), {
            "id", "matter_id", "report_ref", "source_id", "stage_label",
            "outcome_label", "enriched_here", "created_by", "created_utc"})
        run = self.ext.record_corpus_search_run(
            self.mid, "RUN", QUERY_SHA256, MEMBER)
        self.assertEqual(set(run), {
            "id", "matter_id", "run_ref", "query_sha256", "engine_label",
            "reference_stub", "searched_here", "ranked_here", "status",
            "created_by", "created_utc"})
        out = self.ext.record_corpus_search_outcome(
            self.mid, run["id"], "done", MEMBER)
        self.assertEqual(set(out), {
            "id", "matter_id", "run_id", "outcome_label", "result_count",
            "reference_stub", "created_by", "created_utc"})
        ask = self.ext.record_assistance_request(self.mid, "ASK", MEMBER)
        self.assertEqual(set(ask), {
            "id", "matter_id", "request_ref", "model_label",
            "prompt_sha256", "reference_stub", "inference_here",
            "assisted_here", "status", "created_by", "created_utc"})
        aout = self.ext.record_assistance_outcome(
            self.mid, ask["id"], "done", MEMBER)
        self.assertEqual(set(aout), {
            "id", "matter_id", "request_id", "outcome_label", "result_ref",
            "reference_stub", "output_held", "created_by", "created_utc"})
        dep = self.ext.record_content_deposit(
            self.mid, "DEP", self.doc["id"], "vault", MEMBER)
        self.assertEqual(set(dep), {
            "id", "matter_id", "deposit_ref", "document_id", "storage_ref",
            "stored_here", "content_held", "created_by", "created_utc"})
        ren = self.ext.record_render(
            self.mid, "REN", self.doc["id"], "PDF", MEMBER)
        self.assertEqual(set(ren), {
            "id", "matter_id", "render_ref", "document_id", "format_label",
            "output_sha256", "rendered_here", "content_held", "created_by",
            "created_utc"})
        red = self.ext.record_redaction(
            self.mid, "RED", self.doc["id"], "done", MEMBER)
        self.assertEqual(set(red), {
            "id", "matter_id", "redaction_ref", "document_id",
            "outcome_label", "output_ref", "output_sha256", "redacted_here",
            "content_held", "created_by", "created_utc"})

    def test_no_signature_accepts_content_or_identity(self):
        for name, method in inspect.getmembers(
                LawEnfExtensions, predicate=inspect.isfunction):
            if name.startswith("_") and name != "_latest_label":
                continue
            params = inspect.signature(method).parameters
            for param in params.values():
                self.assertNotEqual(
                    param.kind, inspect.Parameter.VAR_KEYWORD,
                    "%s must not accept **kwargs" % name)
                self.assertNotIn(
                    param.name, self.BANNED_PARAMS,
                    "%s parameter %r could hold content/identity"
                    % (name, param.name))

    def test_smuggled_fields_raise_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.register_corpus(
                self.mid, "C2", "cov", MEMBER, content="the law itself")
        with self.assertRaises(TypeError):
            self.ext.record_headnote(
                self.mid, "HN2", self.source["id"], NOTE_SHA256, MEMBER,
                headnote_text="a headnote")
        with self.assertRaises(TypeError):
            self.ext.record_corpus_search_run(
                self.mid, "RUN2", QUERY_SHA256, MEMBER,
                query_text="qualified immunity")
        with self.assertRaises(TypeError):
            self.ext.record_assistance_request(
                self.mid, "ASK2", MEMBER, prompt="summarize this case")
        with self.assertRaises(TypeError):
            self.ext.record_content_deposit(
                self.mid, "DEP2", self.doc["id"], "vault", MEMBER,
                content=b"document bytes")
        with self.assertRaises(TypeError):
            self.ext.record_validation_determination(
                self.mid, "val-1", "Followed", MEMBER,
                subject_name="a person")


class TestAccessAndBoundaries(unittest.TestCase):
    """Both founding boundaries bind the new surface."""

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]

    def test_viewer_write_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_corpus(self.mid, "C", "cov", VIEWER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_corpus_register:denied", actions)

    def test_outsider_denied_by_membership(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_corpus(self.mid, "C", "cov", OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.ext.list_corpora(self.mid, OUTSIDER)

    def test_closed_matter_rejects_extension_writes(self):
        matter2 = self.store.create_matter("MATTER-REF-CLOSED", MEMBER)
        self.store.close_matter(matter2["id"], MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_corpus(matter2["id"], "C", "cov", MEMBER)

    def test_mutations_audited_and_admin_reads(self):
        corpus = self.ext.register_corpus(self.mid, "C", "cov", MEMBER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_corpus_register", actions)
        view = self.ext.corpus_view(self.mid, corpus["id"], ADMIN)
        self.assertEqual(view["corpus_ref"], "C")


class _EarliestLabelExtensions(LawEnfExtensions):
    """Mutant: the latest-label seam reads the earliest record."""

    @staticmethod
    def _latest_label(records, key):
        return records[0][key] if records else None


class TestLatestLabelNegativeControl(unittest.TestCase):
    """Fresh negative control for the latest-label seam.

    Canonical expectation: a derived view's "latest" label is the
    most recently recorded one. The mutant seam reads the earliest
    record and must misstate it.
    """

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]
        self.mutant = _EarliestLabelExtensions(self.store)
        corpus = self.ext.register_corpus(self.mid, "C", "cov", MEMBER)
        self.corpus_id = corpus["id"]
        self.ext.record_corpus_maintenance(
            self.mid, self.corpus_id, "initial-load", MEMBER)
        self.ext.record_corpus_maintenance(
            self.mid, self.corpus_id, "weekly-update", MEMBER)
        # The mutant shares the store but not the records; rebuild
        # the same stream on the mutant for a fair comparison.
        mcorpus = self.mutant.register_corpus(self.mid, "C", "cov", MEMBER)
        self.mcorpus_id = mcorpus["id"]
        self.mutant.record_corpus_maintenance(
            self.mid, self.mcorpus_id, "initial-load", MEMBER)
        self.mutant.record_corpus_maintenance(
            self.mid, self.mcorpus_id, "weekly-update", MEMBER)

    def test_canonical_latest_is_most_recent(self):
        view = self.ext.corpus_view(self.mid, self.corpus_id, ADMIN)
        self.assertEqual(view["latest_maintenance_label"], "weekly-update")
        self.assertEqual(view["maintenance_count"], 2)

    def test_mutant_reports_earliest(self):
        view = self.mutant.corpus_view(self.mid, self.mcorpus_id, ADMIN)
        self.assertEqual(view["latest_maintenance_label"], "initial-load")

    def test_mutant_outcome_is_not_the_canonical_expectation(self):
        with self.assertRaises(AssertionError):
            self.assertEqual(
                self.mutant.corpus_view(self.mid, self.mcorpus_id, ADMIN)
                ["latest_maintenance_label"],
                "weekly-update")


if __name__ == "__main__":
    unittest.main()
