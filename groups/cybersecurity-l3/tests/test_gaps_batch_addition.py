"""Final GAPS batch tests — Remainder Addition extension surface.

Traces to: GAPS.md section "Remainder Addition — Cybersecurity
L3-adjacent (+2 forks)" (idx 620 and idx 622; idx 621, HSM as a
Service, was already closed ``re-scoped`` under PLATFORM-LAYER.md
and is not part of this unit), ``../BATCH-ADDITION.md`` for the
per-entry dispositions, and ``../../gaps-batch/DECISION.md`` for the
batch pattern. The surface is
``cyber.extensions_addition.ExtensionAdditionStore``: the firewall
management & orchestration plane as a labeled reference
implementation (``reference_stub: True`` on every record), and the
inline email security platform in records form, on the same
hash-chained audit log, under the same RBAC, with the same
fail-closed discipline (AU-5) as the core and the first batch unit.

Category discipline pinned throughout: nothing here manages a
device, pushes or provisions anything, analyzes a policy, or
inspects, delivers, quarantines, or blocks a message. No record,
view, or summary on this surface carries a computed score, and no
function can accept message content or a mail address.
"""

import inspect
import os
import tempfile
import unittest

from cyber_helpers import ADMIN, ANALYST, AUDITOR, VIEWER

from cyber.audit import AuditLog
from cyber.errors import (
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from cyber.extensions_addition import ExtensionAdditionStore, latest_label


def make_ext(audit=None):
    if audit is None:
        audit = AuditLog()
    return ExtensionAdditionStore(audit=audit), audit


def _all_keys(obj):
    """Every dict key appearing anywhere inside ``obj``."""
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            keys |= _all_keys(value)
    return keys


class TestFirewallReferenceStub(unittest.TestCase):
    """GAPS idx 620: Firewall management & orchestration plane —
    labeled reference implementation; nothing is managed, pushed,
    provisioned, or analyzed here."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.device = self.ext.register_fw_device(
            "edge-fw-9", "ftd", actor=ANALYST
        )

    def test_device_record_is_labeled(self):
        self.assertEqual(self.device["id"], "fwd-1")
        self.assertIs(self.device["reference_stub"], True)
        self.assertEqual(self.device["status"], "recorded")
        self.assertEqual(
            set(self.device),
            {"id", "device_ref", "model_label", "status",
             "reference_stub", "created_by", "created_utc"},
        )

    def test_bad_model_label_and_address_ref_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_fw_device("edge-fw-9", "asa-x", actor=ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.register_fw_device("10.0.0.1", "ftd", actor=ANALYST)

    def test_policy_definition_is_data_never_pushed(self):
        policy = self.ext.create_fw_policy(
            "branch egress", self.device["id"],
            ["deny inbound tcp-22", "allow outbound udp-53"],
            actor=ANALYST,
        )
        self.assertIs(policy["reference_stub"], True)
        self.assertEqual(policy["status"], "recorded")
        self.assertEqual(
            policy["rules"],
            ["deny inbound tcp-22", "allow outbound udp-53"],
        )

    def test_empty_rules_and_unknown_device_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_fw_policy("p", self.device["id"], [],
                                      actor=ANALYST)
        with self.assertRaises(NotFoundError):
            self.ext.create_fw_policy("p", "fwd-99", ["r"], actor=ANALYST)

    def test_provisioning_and_analysis_are_reported_records(self):
        policy = self.ext.create_fw_policy(
            "branch egress", self.device["id"], ["allow outbound udp-53"],
            actor=ANALYST,
        )
        run = self.ext.record_fw_provisioning(
            self.device["id"], "completed", actor=ANALYST
        )
        analysis = self.ext.record_fw_analysis(
            policy["id"], "optimization_reported", actor=ANALYST
        )
        for record in (run, analysis):
            self.assertIs(record["reference_stub"], True)
            self.assertEqual(record["status"], "recorded")
        with self.assertRaises(NotFoundError):
            self.ext.record_fw_provisioning("fwd-99", "completed",
                                            actor=ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.record_fw_analysis(policy["id"], "score-42",
                                        actor=ANALYST)

    def test_device_view_derives_counts_and_latest(self):
        self.ext.create_fw_policy("p1", self.device["id"], ["r1"],
                                  actor=ANALYST)
        self.ext.record_fw_provisioning(self.device["id"], "completed",
                                        actor=ANALYST)
        self.ext.record_fw_provisioning(self.device["id"], "failed",
                                        actor=ANALYST)
        view = self.ext.fw_device_view(self.device["id"], actor=VIEWER)
        self.assertEqual(view["policy_count"], 1)
        self.assertEqual(view["provisioning_count"], 2)
        self.assertEqual(view["latest_provisioning_outcome"], "failed")
        stored = self.ext._data["fw_devices"][self.device["id"]]
        self.assertNotIn("policy_count", stored)
        self.assertNotIn("provisioning_count", stored)
        self.assertNotIn("latest_provisioning_outcome", stored)


class TestMailGatewayRecords(unittest.TestCase):
    """GAPS idx 622: Inline email security platform — records form:
    gateway registrations, declared policy records, and disposition
    records reported by the external platform. Named separately
    from the phishing family's simulation / training content."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.gateway = self.ext.register_mail_gateway(
            "mail-gw-1", "inline", actor=ANALYST
        )

    def test_gateway_record_shape(self):
        self.assertEqual(self.gateway["id"], "mlg-1")
        self.assertEqual(
            set(self.gateway),
            {"id", "gateway_ref", "deployment", "created_by",
             "created_utc"},
        )
        self.assertNotIn("reference_stub", self.gateway)

    def test_policy_declared_action_is_data(self):
        policy = self.ext.create_mail_policy(
            "exec impersonation", "bec", "quarantine", actor=ANALYST
        )
        self.assertEqual(policy["declared_action"], "quarantine")
        with self.assertRaises(ValidationError):
            self.ext.create_mail_policy("p", "carrier_pigeon", "block",
                                        actor=ANALYST)

    def test_dispositions_counts_and_latest_derived(self):
        self.ext.record_mail_disposition(
            self.gateway["id"], "msg-001", "delivered", "clean",
            actor=ANALYST,
        )
        self.ext.record_mail_disposition(
            self.gateway["id"], "msg-002", "quarantined", "phishing",
            actor=ANALYST,
        )
        self.ext.record_mail_disposition(
            self.gateway["id"], "msg-003", "blocked", "qr_code",
            actor=ANALYST,
        )
        view = self.ext.mail_gateway_view(self.gateway["id"], actor=VIEWER)
        self.assertEqual(view["disposition_count"], 3)
        self.assertEqual(
            view["dispositions_by_disposition"],
            {"delivered": 1, "quarantined": 1, "blocked": 1, "tagged": 0},
        )
        self.assertEqual(view["latest_disposition"], "blocked")
        stored = self.ext._data["mail_gateways"][self.gateway["id"]]
        self.assertNotIn("disposition_count", stored)
        self.assertNotIn("latest_disposition", stored)
        disposition = self.ext._data["mail_dispositions"]["mld-1"]
        self.assertNotIn("score", _all_keys(disposition))
        self.assertNotIn("band", _all_keys(disposition))

    def test_summary_counts_only(self):
        self.ext.create_mail_policy("p", "spam", "tag", actor=ANALYST)
        self.ext.record_mail_disposition(
            self.gateway["id"], "msg-001", "tagged", "spam", actor=ANALYST
        )
        summary = self.ext.mail_summary(actor=VIEWER)
        self.assertEqual(summary["gateways"], 1)
        self.assertEqual(summary["policies"], 1)
        self.assertEqual(summary["dispositions"], 1)
        self.assertEqual(
            summary["dispositions_by_category"],
            {"bec": 0, "phishing": 0, "malware": 0, "spam": 1,
             "qr_code": 0, "other": 0, "clean": 0},
        )

    def test_unknown_gateway_is_not_found(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_mail_disposition(
                "mlg-99", "msg-001", "delivered", "clean", actor=ANALYST
            )


class TestMailPrivacyBoundary(unittest.TestCase):
    """The mail surface holds no content and no address: messages are
    opaque refs, and address-shaped tokens are refused."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.gateway = self.ext.register_mail_gateway(
            "mail-gw-1", "api_based", actor=ANALYST
        )

    def test_email_address_as_message_ref_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.record_mail_disposition(
                self.gateway["id"], "user@example.com", "delivered",
                "clean", actor=ANALYST,
            )

    def test_hostname_and_url_refs_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_mail_gateway("mx.example.com", "inline",
                                           actor=ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.register_mail_gateway("https://gw.example", "inline",
                                           actor=ANALYST)

    def test_no_content_parameter_exists(self):
        """Privacy pin: no addition function can accept message
        content, a subject, or a sender/recipient."""
        forbidden = {"content", "payload", "message", "body", "text",
                     "subject", "sender", "recipient", "email",
                     "email_address", "headers"}
        for name, member in inspect.getmembers(ExtensionAdditionStore,
                                               inspect.isfunction):
            params = set(inspect.signature(member).parameters)
            self.assertFalse(
                params & forbidden,
                "%s accepts a content parameter" % name,
            )


class TestAccessAndAudit(unittest.TestCase):
    """RBAC via the core access module; denied attempts are audited;
    the auditor (AC-5) holds no permission on this surface."""

    def setUp(self):
        self.ext, self.audit = make_ext()

    def test_viewer_cannot_register_and_denial_is_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_mail_gateway("mail-gw-1", "inline",
                                           actor=VIEWER)
        denied = [e for e in self.audit.entries()
                  if e["action"] == "extension_addition_denied"]
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0]["actor"], "carol")
        self.assertEqual(self.audit.verify_chain(), (True, None))

    def test_auditor_holds_no_addition_permission(self):
        gateway = self.ext.register_mail_gateway("mail-gw-1", "inline",
                                                 actor=ANALYST)
        with self.assertRaises(PermissionDenied):
            self.ext.mail_gateway_view(gateway["id"], actor=AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.register_fw_device("edge-fw-9", "ftd", actor=AUDITOR)

    def test_mutations_are_audited_on_the_shared_chain(self):
        self.ext.register_fw_device("edge-fw-9", "asa", actor=ANALYST)
        self.ext.register_mail_gateway("mail-gw-1", "inline", actor=ANALYST)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("fw_device_register", actions)
        self.assertIn("mail_gateway_register", actions)
        self.assertEqual(self.audit.verify_chain(), (True, None))


class TestFailClosed(unittest.TestCase):
    """AU-5 at the addition surface: an audit write failure rolls the
    whole mutation back — no object, no id consumed."""

    def test_failed_audit_write_rolls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            ext = ExtensionAdditionStore(audit=log)
            if os.path.exists(path):
                os.remove(path)
            os.mkdir(path)
            with self.assertRaises(AuditWriteError):
                ext.register_mail_gateway("mail-gw-1", "inline",
                                          actor=ANALYST)
            self.assertEqual(ext._data["mail_gateways"], {})
            os.rmdir(path)
            gateway = ext.register_mail_gateway("mail-gw-1", "inline",
                                                actor=ANALYST)
            self.assertEqual(gateway["id"], "mlg-1")


class TestNoScoresAnywhere(unittest.TestCase):
    """Posture is counts only: a recursive scan over one of every
    addition record, view, and summary finds no score-shaped key."""

    def test_no_score_keys(self):
        ext, _ = make_ext()
        device = ext.register_fw_device("edge-fw-9", "ftd", actor=ANALYST)
        policy = ext.create_fw_policy("p", device["id"], ["r"],
                                      actor=ANALYST)
        ext.record_fw_provisioning(device["id"], "completed", actor=ANALYST)
        ext.record_fw_analysis(policy["id"], "conflict_reported",
                               actor=ANALYST)
        gateway = ext.register_mail_gateway("mail-gw-1", "inline",
                                            actor=ANALYST)
        ext.create_mail_policy("mp", "bec", "block", actor=ANALYST)
        ext.record_mail_disposition(gateway["id"], "msg-001", "blocked",
                                    "bec", actor=ANALYST)
        surfaces = [
            ext._data,
            ext.fw_device_view(device["id"], actor=VIEWER),
            ext.mail_gateway_view(gateway["id"], actor=VIEWER),
            ext.mail_summary(actor=VIEWER),
        ]
        for surface in surfaces:
            self.assertNotIn("score", _all_keys(surface))
            self.assertNotIn("band", _all_keys(surface))
            self.assertNotIn("confidence", _all_keys(surface))


class TestLatestLabelNegativeControl(unittest.TestCase):
    """Fresh negative control for this unit: the latest-value seam.

    ``latest_label`` is the single seam this module's derived views
    use for a latest reported value. The canonical expectation reads
    the most recent record; an earliest-reading mutant must NOT
    satisfy it. The mutation-verification record in tests/README.md
    reports the suite failure count when the real ``latest_label``
    is replaced by this mutant.
    """

    RECORDS = [
        {"outcome": "completed", "disposition": "delivered"},
        {"outcome": "failed", "disposition": "blocked"},
    ]
    EXPECTED_OUTCOME = "failed"
    EXPECTED_DISPOSITION = "blocked"

    @staticmethod
    def _mutant_latest_label(records, key):
        return records[0][key] if records else None

    def test_latest_label_matches_canonical(self):
        self.assertEqual(
            latest_label(self.RECORDS, "outcome"), self.EXPECTED_OUTCOME
        )
        self.assertEqual(
            latest_label(self.RECORDS, "disposition"),
            self.EXPECTED_DISPOSITION,
        )
        self.assertIsNone(latest_label([], "outcome"))

    def test_canonical_expectation_rejects_the_mutant(self):
        mutant = self._mutant_latest_label(self.RECORDS, "outcome")
        self.assertNotEqual(mutant, self.EXPECTED_OUTCOME)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant, self.EXPECTED_OUTCOME)


if __name__ == "__main__":
    unittest.main()
