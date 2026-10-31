"""Core: Dataset registry (metadata + checksums only). Traces to
UNION-SPEC core functions 4 (data management — the registry form)
and 7 (open access & controlled access data — the access-tier
designation on every dataset record), SI-10 input validation, and
the privacy discipline: the pinned record shape has no field that
could hold dataset content. Content is hashed transiently for
verification and discarded, in the legal-records pattern."""

import hashlib
import unittest

import research_helpers as H
from research.errors import NotFoundError, PermissionDenied, ValidationError

EXPECTED_KEYS = {"id", "commons_id", "name", "description", "access_tier",
                 "sha256", "size_bytes", "created_by", "created_utc"}


class TestDatasets(unittest.TestCase):
    def setUp(self):
        self.store, self.commons, self.org = H.make_store()

    def _register(self, **overrides):
        return H.make_dataset(self.store, self.commons, **overrides)

    def test_create_shape_is_pinned_and_holds_no_content(self):
        dataset = self._register()
        self.assertEqual(set(dataset.keys()), EXPECTED_KEYS)
        self.assertTrue(dataset["id"].startswith("ds-"))
        self.assertEqual(dataset["commons_id"], self.commons["id"])
        self.assertEqual(dataset["access_tier"], "controlled")
        self.assertEqual(dataset["sha256"], H.SHA256_A)
        self.assertEqual(dataset["size_bytes"], 2048)
        for field in ("content", "data", "payload", "body", "records"):
            self.assertNotIn(field, dataset)

    def test_checksum_uppercase_normalized_to_lowercase(self):
        dataset = self._register(sha256="A" * 64)
        self.assertEqual(dataset["sha256"], "a" * 64)
        dataset = self._register(name="second-dataset",
                                 sha256=H.SHA256_B.upper())
        self.assertEqual(dataset["sha256"], H.SHA256_B)

    def test_bad_checksum_rejected(self):
        for bad in ("abc", "g" * 64, "a" * 63, "a" * 65, ""):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self._register(sha256=bad)
        self.assertEqual(
            self.store.list_datasets(H.MEMBER, self.commons["id"]), [])

    def test_size_bytes_validation(self):
        for bad in (-1, 1.5, True, "2048"):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self._register(size_bytes=bad)
        self.assertEqual(
            self.store.list_datasets(H.MEMBER, self.commons["id"]), [])

    def test_zero_size_and_open_tier_allowed(self):
        dataset = self._register(name="open-registry", access_tier="open",
                                 size_bytes=0)
        self.assertEqual(dataset["size_bytes"], 0)
        self.assertEqual(dataset["access_tier"], "open")

    def test_bad_tier_rejected(self):
        with self.assertRaises(ValidationError):
            self._register(access_tier="private")

    def test_verify_by_content(self):
        content = b"research dataset content, hashed and discarded"
        digest = hashlib.sha256(content).hexdigest()
        dataset = self._register(sha256=digest, size_bytes=len(content))
        result = self.store.verify_dataset(H.MEMBER, dataset["id"], content)
        self.assertEqual(set(result.keys()),
                         {"dataset_id", "sha256", "computed_sha256",
                          "matches"})
        self.assertEqual(result["dataset_id"], dataset["id"])
        self.assertEqual(result["sha256"], digest)
        self.assertEqual(result["computed_sha256"], digest)
        self.assertTrue(result["matches"])
        other = self.store.verify_dataset(H.MEMBER, dataset["id"],
                                          b"different bytes entirely")
        self.assertFalse(other["matches"])
        self.assertNotEqual(other["computed_sha256"], digest)
        # Verification stored nothing: the record is unchanged.
        self.assertEqual(
            set(self.store.get_dataset(H.MEMBER, dataset["id"]).keys()),
            EXPECTED_KEYS)

    def test_get_list_and_tier_filter(self):
        controlled = self._register()
        open_ds = self._register(name="open-registry", access_tier="open",
                                 sha256=H.SHA256_B)
        self.assertEqual(
            self.store.get_dataset(H.STAFF, open_ds["id"])["name"],
            "open-registry")
        all_datasets = self.store.list_datasets(H.MEMBER,
                                                self.commons["id"])
        self.assertEqual(len(all_datasets), 2)
        open_only = self.store.list_datasets(H.MEMBER, self.commons["id"],
                                             access_tier="open")
        self.assertEqual([d["id"] for d in open_only], [open_ds["id"]])
        controlled_only = self.store.list_datasets(
            H.MEMBER, self.commons["id"], access_tier="controlled")
        self.assertEqual([d["id"] for d in controlled_only],
                         [controlled["id"]])
        with self.assertRaises(NotFoundError):
            self.store.get_dataset(H.MEMBER, "ds-99")

    def test_outsider_denied(self):
        dataset = self._register()
        with self.assertRaises(PermissionDenied):
            self._register(actor=H.OUTSIDER, name="outsider-dataset")
        with self.assertRaises(PermissionDenied):
            self.store.get_dataset(H.OUTSIDER, dataset["id"])
        with self.assertRaises(PermissionDenied):
            self.store.list_datasets(H.OUTSIDER, self.commons["id"])
        with self.assertRaises(PermissionDenied):
            self.store.verify_dataset(H.OUTSIDER, dataset["id"], b"x")


if __name__ == "__main__":
    unittest.main()
