"""Final GAPS batch tests — Remainder Singleton 64, Storage L2.

Traces to ``BATCH.md`` in this group directory and the 10 open
entries of the singleton's GAPS.md section (inventory idx
725–734). The founding disciplines bind every test here: no
shape may hold content (recursive forbidden-key scan over every
extension record and view), no cryptography is performed (the
module's import lines are scanned), nothing is captured,
delivered, executed, connected, or destroyed -- every entry
lands as records plus derivations over this group's own records,
with the honesty labels pinned per shape.

The fresh negative control is the enforcement-eligibility seam
(``StorageExtensions._derive_enforcement_eligibility``): an
enforcement decision for a disposed message must be refused,
because once disposition is recorded there is nothing left in
this substrate for a decision to concern. The external mutation
drill on the real module is recorded in ``tests/README.md``.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from storage.errors import (  # noqa: E402
    NotFoundError, PermissionDenied, ValidationError)
from storage.extensions import (  # noqa: E402
    FORBIDDEN_KEYS, StorageExtensions)

from storage_helpers import (  # noqa: E402
    ADMIN, OPERATOR, VIEWER, AFTER_BOUNDARY, BEFORE_BOUNDARY,
    make_archive, make_custody, make_message, make_store)


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.ext = StorageExtensions(self.store)
        self.org, self.policy, self.collection = make_archive(self.store)
        self.message = make_message(self.store, self.collection)
        self.custody = make_custody(self.store, self.org, self.collection)

    def make_disposed(self, ref="MSG-REF-DISP"):
        message = make_message(self.store, self.collection, ref=ref)
        self.store.record_disposition(
            ADMIN, message["id"], "shredded per schedule",
            at=AFTER_BOUNDARY)
        disposition = self.store.list_dispositions(
            ADMIN, message_id=message["id"])[0]
        return message, disposition

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]


# -- idx 725: archived payload storage plane --------------------------------

class TestPayloadCustody(BatchFixture):
    """Entry: payload storage plane -- built as payload custody
    records. No payload byte is held; the view's size match is
    derived at read and never stored."""

    def _record(self, **overrides):
        kwargs = dict(message_id=self.message["id"],
                      custodian_ref="CUSTODIAN-REF-9",
                      reported_size_bytes=2048,
                      checksum_ref="SHA-REF-1")
        kwargs.update(overrides)
        return self.ext.record_payload_custody(OPERATOR, **kwargs)

    def test_shape_and_labels(self):
        record = self._record()
        self.assertEqual(record["id"], "pay-1")
        self.assertEqual(
            set(record.keys()),
            {"id", "message_id", "collection_id", "custodian_ref",
             "reported_size_bytes", "checksum_ref",
             "content_held_here", "created_by", "created_utc"})
        self.assertIs(record["content_held_here"], False)
        self.assertEqual(record["collection_id"], self.collection["id"])

    def test_view_derives_size_match(self):
        record = self._record()
        view = self.ext.payload_custody_view(ADMIN, record["id"])
        self.assertEqual(view["recorded_size_bytes"], 2048)
        self.assertIs(view["size_matches_record"], True)
        stored = self.ext.list_payload_custodies(ADMIN)[0]
        self.assertNotIn("size_matches_record", stored)
        self.assertNotIn("recorded_size_bytes", stored)

    def test_view_reports_mismatch_as_data(self):
        record = self._record(reported_size_bytes=9999)
        view = self.ext.payload_custody_view(ADMIN, record["id"])
        self.assertIs(view["size_matches_record"], False)

    def test_one_record_per_message(self):
        self._record()
        with self.assertRaises(ValidationError):
            self._record()
        other = make_message(self.store, self.collection,
                             ref="MSG-REF-0002")
        second = self._record(message_id=other["id"])
        self.assertEqual(second["id"], "pay-2")

    def test_counts_must_be_integers(self):
        for bad in (1.5, True, "2048", -1):
            with self.assertRaises(ValidationError):
                self._record(reported_size_bytes=bad)
        self.assertEqual(self.ext.list_payload_custodies(ADMIN), [])

    def test_unknown_message(self):
        with self.assertRaises(NotFoundError):
            self._record(message_id="msg-99")


# -- idx 726: archive ingest pipeline ----------------------------------------

class TestIngestBatches(BatchFixture):
    """Entry: ingest pipeline -- built as ingest-batch records
    with counts stored as reported; a batch archives nothing."""

    def setUp(self):
        super().setUp()
        self.integration = self.store.create_integration(
            ADMIN, self.org["id"], "mail_platform",
            "Mail platform (registry label)")

    def _record(self, **overrides):
        kwargs = dict(collection_id=self.collection["id"],
                      integration_id=self.integration["id"],
                      source_label="journal mailbox J-1",
                      reported_message_count=12,
                      reported_byte_total=40960)
        kwargs.update(overrides)
        return self.ext.record_ingest_batch(OPERATOR, **kwargs)

    def test_shape_and_labels(self):
        record = self._record()
        self.assertEqual(record["id"], "ing-1")
        self.assertEqual(
            set(record.keys()),
            {"id", "collection_id", "integration_id", "source_label",
             "reported_message_count", "reported_byte_total",
             "captured_here", "created_by", "created_utc"})
        self.assertIs(record["captured_here"], False)

    def test_batch_changes_no_core_records(self):
        before_messages = self.store.list_messages(ADMIN)
        before_summary = self.store.summary(ADMIN)
        self._record()
        self.assertEqual(self.store.list_messages(ADMIN), before_messages)
        self.assertEqual(self.store.summary(ADMIN), before_summary)

    def test_directory_integration_refused(self):
        directory = self.store.create_integration(
            ADMIN, self.org["id"], "directory", "Directory (label)")
        with self.assertRaises(ValidationError):
            self._record(integration_id=directory["id"])

    def test_counts_must_be_integers(self):
        with self.assertRaises(ValidationError):
            self._record(reported_message_count=1.5)
        with self.assertRaises(ValidationError):
            self._record(reported_byte_total=False)


# -- idx 727: full-text content indexing & search (stub) ----------------------

class TestIndexReferences(BatchFixture):
    """Entry: full-text indexing -- stub-engine, shipped as a
    labeled reference record. No query surface exists."""

    def test_shape_and_labels(self):
        record = self.ext.record_index_reference(
            OPERATOR, self.collection["id"], "vendor index (label)", 1200)
        self.assertEqual(record["id"], "idx-1")
        self.assertEqual(
            set(record.keys()),
            {"id", "collection_id", "engine_label",
             "reported_document_count", "reference_stub",
             "index_built_here", "created_by", "created_utc"})
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["index_built_here"], False)

    def test_no_query_surface_exists(self):
        names = [n for n in dir(self.ext)
                 if "search" in n or "query" in n]
        self.assertEqual(names, [])
        with self.assertRaises(TypeError):
            self.ext.record_index_reference(
                OPERATOR, self.collection["id"], "engine", 1,
                query_text="anything")


# -- idx 728: encryption & decryption engine ----------------------------------

class TestEncryptionProfiles(BatchFixture):
    """Entry: encryption engine -- built as encryption profile
    records over the core custody records. Labels as data; the
    fork's posture is recorded as the fork's and does not
    transfer; nothing is encrypted here."""

    def _record(self, **overrides):
        kwargs = dict(custody_id=self.custody["id"],
                      algorithm_label="ALG-LABEL-1",
                      validation_label="vendor-stated posture (label)")
        kwargs.update(overrides)
        return self.ext.record_encryption_profile(OPERATOR, **kwargs)

    def test_shape_and_labels(self):
        record = self._record()
        self.assertEqual(record["id"], "enc-1")
        self.assertEqual(
            set(record.keys()),
            {"id", "custody_id", "collection_id", "algorithm_label",
             "validation_label", "validation_transfers",
             "encrypted_here", "created_by", "created_utc"})
        self.assertIs(record["encrypted_here"], False)
        self.assertIs(record["validation_transfers"], False)

    def test_one_profile_per_custody_record(self):
        self._record()
        with self.assertRaises(ValidationError):
            self._record()

    def test_unknown_custody(self):
        with self.assertRaises(NotFoundError):
            self._record(custody_id="key-99")


# -- idx 729: key management hardware & premise equipment (stub) --------------

class TestKeyHardware(BatchFixture):
    """Entry: key hardware -- stub-engine, shipped as inventory
    records. No key material is held."""

    def test_shape_and_labels(self):
        record = self.ext.record_key_hardware(
            OPERATOR, self.custody["id"], "custodian appliance (label)",
            "premise rack (label)")
        self.assertEqual(record["id"], "khw-1")
        self.assertEqual(
            set(record.keys()),
            {"id", "custody_id", "collection_id", "equipment_label",
             "location_label", "reference_stub",
             "key_material_held_here", "created_by", "created_utc"})
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["key_material_held_here"], False)

    def test_multiple_units_may_be_recorded(self):
        self.ext.record_key_hardware(
            OPERATOR, self.custody["id"], "unit A", "rack 1")
        second = self.ext.record_key_hardware(
            OPERATOR, self.custody["id"], "unit B", "rack 2")
        self.assertEqual(second["id"], "khw-2")


# -- idx 730: retrieval delivery transport & export files ---------------------

class TestDeliveries(BatchFixture):
    """Entry: delivery transport -- built as delivery records;
    the linked retrieval's status is derived at read."""

    def setUp(self):
        super().setUp()
        self.retrieval = self.store.create_retrieval(
            OPERATOR, self.message["id"], "batch", "data_file",
            "REQUESTER-REF-1")

    def test_shape_and_labels(self):
        record = self.ext.record_delivery(
            OPERATOR, self.retrieval["id"], "managed transfer (label)")
        self.assertEqual(record["id"], "dlv-1")
        self.assertEqual(
            set(record.keys()),
            {"id", "retrieval_id", "message_id", "transport_label",
             "reference_transport", "delivered_here", "created_by",
             "created_utc"})
        self.assertIs(record["reference_transport"], True)
        self.assertIs(record["delivered_here"], False)

    def test_view_derives_retrieval_status(self):
        record = self.ext.record_delivery(
            OPERATOR, self.retrieval["id"], "managed transfer (label)")
        view = self.ext.delivery_view(ADMIN, record["id"])
        self.assertEqual(view["retrieval_status"], "requested")
        self.store.complete_retrieval(OPERATOR, self.retrieval["id"])
        view = self.ext.delivery_view(ADMIN, record["id"])
        self.assertEqual(view["retrieval_status"], "completed")
        stored = self.ext.list_deliveries(ADMIN)[0]
        self.assertNotIn("retrieval_status", stored)

    def test_one_delivery_per_retrieval(self):
        self.ext.record_delivery(
            OPERATOR, self.retrieval["id"], "managed transfer (label)")
        with self.assertRaises(ValidationError):
            self.ext.record_delivery(
                OPERATOR, self.retrieval["id"], "other (label)")


class TestExportManifests(BatchFixture):
    """Entry: export file production -- built as manifest
    records describing files never produced; the file count is
    derived at read."""

    def test_shape_labels_and_derived_count(self):
        other = make_message(self.store, self.collection,
                             ref="MSG-REF-0002")
        record = self.ext.record_export_manifest(
            OPERATOR, self.collection["id"], "native export (label)",
            [self.message["id"], other["id"]])
        self.assertEqual(record["id"], "exp-1")
        self.assertEqual(
            set(record.keys()),
            {"id", "collection_id", "format_label", "message_ids",
             "reference_transport", "files_produced_here",
             "created_by", "created_utc"})
        self.assertIs(record["files_produced_here"], False)
        view = self.ext.export_manifest_view(ADMIN, record["id"])
        self.assertEqual(view["file_count"], 2)
        self.assertNotIn("file_count", record)

    def test_foreign_message_refused(self):
        org2 = self.store.create_organization(ADMIN, "ORG-0002", "x")
        policy2 = self.store.create_policy(ADMIN, "p2", 10)
        col2 = self.store.create_collection(
            ADMIN, org2["id"], "c2", policy2["id"], "native")
        foreign = make_message(self.store, col2, ref="MSG-FOREIGN")
        with self.assertRaises(ValidationError):
            self.ext.record_export_manifest(
                OPERATOR, self.collection["id"], "fmt",
                [foreign["id"]])

    def test_empty_manifest_refused(self):
        with self.assertRaises(ValidationError):
            self.ext.record_export_manifest(
                OPERATOR, self.collection["id"], "fmt", [])


# -- idx 731: supervision review console & workflow (stub) ---------------------

class TestConsole(BatchFixture):
    """Entry: supervision console -- stub-engine, shipped as
    definition and assignment records held as data. Definitions
    never execute; assignments route nothing and change no core
    review record."""

    def setUp(self):
        super().setUp()
        self.review = self.store.create_review(
            OPERATOR, self.message["id"], "REV-REF-1")
        self.definition = self.ext.record_console_definition(
            OPERATOR, self.collection["id"], "weekly queue (label)",
            ["REV-REF-1", "REV-REF-2"])

    def test_definition_shape_and_labels(self):
        self.assertEqual(self.definition["id"], "wfd-1")
        self.assertEqual(
            set(self.definition.keys()),
            {"id", "collection_id", "definition_label",
             "reviewer_refs", "reference_stub", "executed_here",
             "created_by", "created_utc"})
        self.assertIs(self.definition["reference_stub"], True)
        self.assertIs(self.definition["executed_here"], False)

    def test_assignment_shape_and_no_core_change(self):
        before = self.store.list_reviews(ADMIN)
        record = self.ext.record_console_assignment(
            OPERATOR, self.definition["id"], self.review["id"])
        self.assertEqual(record["id"], "wfa-1")
        self.assertEqual(
            set(record.keys()),
            {"id", "definition_id", "review_id", "message_id",
             "reviewer_ref", "reference_stub", "routed_here",
             "created_by", "created_utc"})
        self.assertIs(record["routed_here"], False)
        self.assertEqual(self.store.list_reviews(ADMIN), before)

    def test_assignment_requires_named_reviewer(self):
        other = self.store.create_review(
            OPERATOR, self.message["id"], "REV-OTHER")
        with self.assertRaises(ValidationError):
            self.ext.record_console_assignment(
                OPERATOR, self.definition["id"], other["id"])


# -- idx 732: policy enforcement execution -------------------------------------

class TestEnforcementDecisions(BatchFixture):
    """Entry: enforcement execution -- built as enforcement
    decision records gated by the eligibility seam. Recording a
    decision executes nothing and changes no core record."""

    def _record(self, **overrides):
        kwargs = dict(message_id=self.message["id"],
                      action="block_access", policy_ref="POL-REF-1",
                      at=BEFORE_BOUNDARY)
        kwargs.update(overrides)
        return self.ext.record_enforcement_decision(OPERATOR, **kwargs)

    def test_shape_and_labels(self):
        record = self._record()
        self.assertEqual(record["id"], "dec-1")
        self.assertEqual(
            set(record.keys()),
            {"id", "message_id", "action", "policy_ref",
             "executed_here", "created_by", "created_utc"})
        self.assertIs(record["executed_here"], False)

    def test_decision_changes_no_core_record(self):
        before_view = self.store.get_message(
            ADMIN, self.message["id"], now=BEFORE_BOUNDARY)
        before_enforcements = self.store.list_enforcements(ADMIN)
        self._record()
        self.assertEqual(
            self.store.get_message(
                ADMIN, self.message["id"], now=BEFORE_BOUNDARY),
            before_view)
        self.assertEqual(
            self.store.list_enforcements(ADMIN), before_enforcements)

    def test_view_derives_current_state(self):
        record = self._record()
        view = self.ext.enforcement_decision_view(
            ADMIN, record["id"], now=BEFORE_BOUNDARY)
        self.assertEqual(view["current_retention_state"], "retained")
        self.assertIs(view["currently_actionable"], True)
        self.store.record_disposition(
            ADMIN, self.message["id"], "shredded per schedule",
            at=AFTER_BOUNDARY)
        view = self.ext.enforcement_decision_view(
            ADMIN, record["id"], now=AFTER_BOUNDARY)
        self.assertEqual(view["current_retention_state"], "disposed")
        self.assertIs(view["currently_actionable"], False)
        stored = self.ext.list_enforcement_decisions(ADMIN)[0]
        self.assertNotIn("current_retention_state", stored)

    def test_unknown_action_refused(self):
        with self.assertRaises(ValidationError):
            self._record(action="delete_everything")


# -- idx 734: disposition execution ---------------------------------------------

class TestDispositionOutcomes(BatchFixture):
    """Entry: disposition execution -- built as disposition
    outcome records. The current outcome is derived at read;
    nothing is destroyed here."""

    def setUp(self):
        super().setUp()
        self.message2, self.disposition = self.make_disposed()

    def test_shape_and_labels(self):
        record = self.ext.record_disposition_outcome(
            OPERATOR, self.disposition["id"], "reported_destroyed")
        self.assertEqual(record["id"], "dout-1")
        self.assertEqual(
            set(record.keys()),
            {"id", "disposition_id", "message_id", "outcome_label",
             "destroyed_here", "created_by", "created_utc"})
        self.assertIs(record["destroyed_here"], False)
        self.assertEqual(record["message_id"], self.message2["id"])

    def test_current_outcome_derived_at_read(self):
        view = self.ext.disposition_outcome_view(
            ADMIN, self.disposition["id"])
        self.assertEqual(view["current_outcome_label"], "unreported")
        self.assertEqual(view["outcome_count"], 0)
        self.ext.record_disposition_outcome(
            OPERATOR, self.disposition["id"], "reported_pending")
        self.ext.record_disposition_outcome(
            OPERATOR, self.disposition["id"], "reported_destroyed")
        view = self.ext.disposition_outcome_view(
            ADMIN, self.disposition["id"])
        self.assertEqual(view["current_outcome_label"],
                         "reported_destroyed")
        self.assertEqual(view["outcome_count"], 2)
        self.assertIs(view["destroyed_here"], False)

    def test_outcomes_change_no_core_record(self):
        before = self.store.list_dispositions(ADMIN)
        self.ext.record_disposition_outcome(
            OPERATOR, self.disposition["id"], "reported_destroyed")
        self.assertEqual(self.store.list_dispositions(ADMIN), before)

    def test_unknown_disposition_and_label(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_disposition_outcome(
                OPERATOR, "dsp-99", "reported_destroyed")
        with self.assertRaises(ValidationError):
            self.ext.record_disposition_outcome(
                OPERATOR, self.disposition["id"], "destroyed")


# -- idx 733: mail platform & directory connectors (stub) -----------------------

class TestConnectorSyncs(BatchFixture):
    """Entry: connectors -- stub-engine, shipped as sync receipt
    records. Nothing connects; a receipt changes no core
    record."""

    def setUp(self):
        super().setUp()
        self.integration = self.store.create_integration(
            ADMIN, self.org["id"], "directory", "Directory (label)")

    def test_shape_and_labels(self):
        record = self.ext.record_connector_sync(
            OPERATOR, self.integration["id"], "bidirectional", 42)
        self.assertEqual(record["id"], "syn-1")
        self.assertEqual(
            set(record.keys()),
            {"id", "integration_id", "org_id", "kind",
             "direction_label", "reported_synced_count",
             "reference_stub", "reference_transport",
             "connected_here", "created_by", "created_utc"})
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["reference_transport"], True)
        self.assertIs(record["connected_here"], False)

    def test_receipt_changes_no_core_record(self):
        before_integrations = self.store.list_integrations(ADMIN)
        before_messages = self.store.list_messages(ADMIN)
        self.ext.record_connector_sync(
            OPERATOR, self.integration["id"], "inbound", 3)
        self.assertEqual(
            self.store.list_integrations(ADMIN), before_integrations)
        self.assertEqual(self.store.list_messages(ADMIN),
                         before_messages)

    def test_unknown_direction_refused(self):
        with self.assertRaises(ValidationError):
            self.ext.record_connector_sync(
                OPERATOR, self.integration["id"], "sideways", 1)


# -- cross-cutting pins ---------------------------------------------------------

def _all_keys(node):
    keys = set()
    if isinstance(node, dict):
        for key, value in node.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            keys |= _all_keys(value)
    return keys


class TestCrossCutting(BatchFixture):
    """The founding disciplines, pinned across the whole
    extension surface at once."""

    def _one_of_each(self):
        integration = self.store.create_integration(
            ADMIN, self.org["id"], "mail_platform", "Mail (label)")
        retrieval = self.store.create_retrieval(
            OPERATOR, self.message["id"], "batch", "data_file",
            "REQUESTER-REF-1")
        review = self.store.create_review(
            OPERATOR, self.message["id"], "REV-REF-1")
        definition = self.ext.record_console_definition(
            OPERATOR, self.collection["id"], "queue (label)",
            ["REV-REF-1"])
        _msg, disposition = self.make_disposed()
        records = [
            self.ext.record_payload_custody(
                OPERATOR, self.message["id"], "CUSTODIAN-REF-9", 2048,
                "SHA-REF-1"),
            self.ext.record_ingest_batch(
                OPERATOR, self.collection["id"], integration["id"],
                "journal J-1", 1, 10),
            self.ext.record_index_reference(
                OPERATOR, self.collection["id"], "engine (label)", 5),
            self.ext.record_encryption_profile(
                OPERATOR, self.custody["id"], "ALG-1", "posture (label)"),
            self.ext.record_key_hardware(
                OPERATOR, self.custody["id"], "unit (label)",
                "rack (label)"),
            self.ext.record_delivery(
                OPERATOR, retrieval["id"], "transport (label)"),
            self.ext.record_export_manifest(
                OPERATOR, self.collection["id"], "fmt (label)",
                [self.message["id"]]),
            definition,
            self.ext.record_console_assignment(
                OPERATOR, definition["id"], review["id"]),
            self.ext.record_enforcement_decision(
                OPERATOR, self.message["id"], "flag_for_review",
                "POL-REF-1", at=BEFORE_BOUNDARY),
            self.ext.record_disposition_outcome(
                OPERATOR, disposition["id"], "reported_destroyed"),
            self.ext.record_connector_sync(
                OPERATOR, integration["id"], "inbound", 2),
        ]
        records.append(self.ext.payload_custody_view(
            ADMIN, records[0]["id"]))
        records.append(self.ext.delivery_view(
            ADMIN, records[5]["id"]))
        records.append(self.ext.export_manifest_view(
            ADMIN, records[6]["id"]))
        records.append(self.ext.enforcement_decision_view(
            ADMIN, records[9]["id"], now=BEFORE_BOUNDARY))
        records.append(self.ext.disposition_outcome_view(
            ADMIN, disposition["id"]))
        return records

    def test_no_forbidden_key_anywhere(self):
        for record in self._one_of_each():
            found = _all_keys(record) & FORBIDDEN_KEYS
            self.assertEqual(found, set(),
                             "forbidden keys %r in %r"
                             % (found, record.get("id")))

    def test_content_kwargs_raise_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.record_payload_custody(
                OPERATOR, self.message["id"], "C", 1, "S",
                content="message body")
        with self.assertRaises(TypeError):
            self.ext.record_encryption_profile(
                OPERATOR, self.custody["id"], "A", "V",
                key_material="abcd")
        with self.assertRaises(TypeError):
            self.ext.record_key_hardware(
                OPERATOR, self.custody["id"], "E", "L",
                key_material="abcd")
        with self.assertRaises(TypeError):
            self.ext.record_console_definition(
                OPERATOR, self.collection["id"], "D", ["R"],
                subject="hello")

    def test_no_cryptographic_operation_in_module(self):
        import storage.extensions as extensions
        source = Path(extensions.__file__).read_text(encoding="utf-8")
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                for bad in ("hashlib", "hmac", "ssl", "Crypto",
                            "cryptography", "secrets"):
                    self.assertNotIn(bad, stripped)

    def test_denied_write_is_audited_and_consumes_no_id(self):
        integration = self.store.create_integration(
            ADMIN, self.org["id"], "mail_platform", "Mail (label)")
        with self.assertRaises(PermissionDenied):
            self.ext.record_ingest_batch(
                VIEWER, self.collection["id"], integration["id"],
                "journal J-1", 1, 10)
        self.assertIn("ext_ingest_batch_record:denied",
                      self.audit_actions())
        record = self.ext.record_ingest_batch(
            OPERATOR, self.collection["id"], integration["id"],
            "journal J-1", 1, 10)
        self.assertEqual(record["id"], "ing-1")
        self.assertIn("ext_ingest_batch_record", self.audit_actions())


# -- fresh negative control: the enforcement-eligibility seam -------------------

class _AlwaysEligibleExtensions(StorageExtensions):
    """Mutant seam: every message is enforcement-eligible,
    disposed or not -- the eligibility derivation removed."""

    @staticmethod
    def _derive_enforcement_eligibility(retention_state):
        return True


class TestEnforcementEligibilityNegativeControl(BatchFixture):
    """Fresh negative control for the batch: the eligibility seam
    ``_derive_enforcement_eligibility`` in
    ``storage/extensions.py``.

    Traced claim: **an enforcement decision is a record about a
    message this substrate still holds a live retention posture
    for; once the core's derivation reports ``disposed`` there is
    nothing left for a decision to concern, so recording one must
    be refused whole.** Each canonical case asserts (1) the real
    implementation raises ValidationError and stores nothing /
    consumes no id, (2) the mutant gate would NOT raise, and (3)
    treating the mutant's outcome as expected fails. The external
    drill (the seam patched in the real file) is recorded in
    tests/README.md.
    """

    def test_decision_for_disposed_message_refused(self):
        message, _disp = self.make_disposed()
        with self.assertRaises(ValidationError):
            self.ext.record_enforcement_decision(
                OPERATOR, message["id"], "block_disposition",
                "POL-REF-1", at=AFTER_BOUNDARY)
        self.assertEqual(
            self.ext.list_enforcement_decisions(ADMIN), [])
        good = self.ext.record_enforcement_decision(
            OPERATOR, self.message["id"], "block_access",
            "POL-REF-1", at=BEFORE_BOUNDARY)
        self.assertEqual(good["id"], "dec-1")

    def test_mutant_waves_the_decision_through(self):
        message, _disp = self.make_disposed()
        mutant = _AlwaysEligibleExtensions(self.store)
        waved = mutant.record_enforcement_decision(
            OPERATOR, message["id"], "block_disposition",
            "POL-REF-1", at=AFTER_BOUNDARY)
        self.assertEqual(waved["message_id"], message["id"])
        with self.assertRaises(AssertionError):
            with self.assertRaises(ValidationError):
                mutant.record_enforcement_decision(
                    OPERATOR, message["id"], "block_access",
                    "POL-REF-1", at=AFTER_BOUNDARY)


if __name__ == "__main__":
    unittest.main()
