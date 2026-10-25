"""Channels tests.

Traces to: Core function -- Channels; contract for
``create_channel/get_channel/list_channels/set_channel_enabled``;
channel kinds {email, sms, voice, push}; channel_write is admin-only.
"""

import unittest

from comm_helpers import ADMIN, OPERATOR, VIEWER, fresh_store
from comm.errors import NotFoundError, PermissionDenied, ValidationError


class TestChannels(unittest.TestCase):
    """Core: Channels."""

    def setUp(self):
        self.store = fresh_store()

    def test_create_all_kinds(self):
        """Core: Channels. Each known kind can be created, ids ch-N."""
        for i, kind in enumerate(("email", "sms", "voice", "push"), start=1):
            ch = self.store.create_channel(kind, kind + "-ch", ADMIN)
            self.assertEqual(ch["id"], "ch-%d" % i)
            self.assertEqual(ch["kind"], kind)
            self.assertTrue(ch["enabled"])

    def test_create_disabled_and_get_list(self):
        """Core: Channels. enabled=False honoured; get/list work for viewer (channel_read)."""
        ch = self.store.create_channel("sms", "sms-ch", ADMIN, enabled=False)
        self.assertFalse(ch["enabled"])
        self.assertEqual(self.store.get_channel(ch["id"], VIEWER)["id"], ch["id"])
        self.assertEqual(len(self.store.list_channels(VIEWER)), 1)

    def test_invalid_kind_and_empty_name(self):
        """Core: Channels (SI-10). Unknown kind / empty name -> ValidationError, no id consumed."""
        with self.assertRaises(ValidationError):
            self.store.create_channel("fax", "x", ADMIN)
        with self.assertRaises(ValidationError):
            self.store.create_channel("email", "", ADMIN)
        self.assertEqual(self.store.create_channel("email", "ok", ADMIN)["id"], "ch-1")

    def test_channel_write_admin_only(self):
        """Core: Channels / Access control. Operator and viewer cannot create channels or set enabled."""
        with self.assertRaises(PermissionDenied):
            self.store.create_channel("email", "x", OPERATOR)
        with self.assertRaises(PermissionDenied):
            self.store.create_channel("email", "x", VIEWER)
        ch = self.store.create_channel("email", "x", ADMIN)
        with self.assertRaises(PermissionDenied):
            self.store.set_channel_enabled(ch["id"], False, OPERATOR)

    def test_set_enabled(self):
        """Core: Channels. set_channel_enabled toggles enabled and returns channel."""
        ch = self.store.create_channel("email", "x", ADMIN)
        updated = self.store.set_channel_enabled(ch["id"], False, ADMIN)
        self.assertFalse(updated["enabled"])
        self.assertFalse(self.store.get_channel(ch["id"], ADMIN)["enabled"])
        with self.assertRaises(NotFoundError):
            self.store.set_channel_enabled("ch-999", True, ADMIN)
        with self.assertRaises(ValidationError):
            self.store.set_channel_enabled(ch["id"], "yes", ADMIN)


if __name__ == "__main__":
    unittest.main()
