#!/usr/bin/env python3
"""Unit tests for the production verifier's deterministic helpers."""

from __future__ import annotations

import unittest
from urllib.error import URLError

from verify_production import MAX_REQUESTS, MetadataParser, Verifier, normalize_base_url


class FailingOpener:
    def open(self, request, timeout):  # noqa: ANN001, ARG002
        raise URLError("offline test")


class ProductionVerifierTests(unittest.TestCase):
    def test_normalize_base_url(self) -> None:
        self.assertEqual(
            normalize_base_url("https://kexingyan.com/"),
            "https://kexingyan.com",
        )

    def test_rejects_credentialed_base_url(self) -> None:
        with self.assertRaises(ValueError):
            normalize_base_url("https://user:secret@kexingyan.com/")

    def test_rejects_non_http_base_url(self) -> None:
        with self.assertRaises(ValueError):
            normalize_base_url("file:///tmp/site")

    def test_metadata_parser_collects_canonical_and_preview(self) -> None:
        parser = MetadataParser()
        parser.feed(
            '<link rel="canonical" href="https://kexingyan.com/">'
            '<meta property="og:image" content="https://kexingyan.com/og.png">'
        )
        self.assertEqual(parser.canonicals, ["https://kexingyan.com/"])
        self.assertEqual(
            parser.properties["og:image"],
            ["https://kexingyan.com/og.png"],
        )

    def test_network_retry_never_exceeds_request_budget(self) -> None:
        verifier = Verifier("https://example.com", timeout=1)
        verifier.opener = FailingOpener()
        verifier.request_count = MAX_REQUESTS - 1

        response = verifier.fetch("/offline")

        self.assertEqual(verifier.request_count, MAX_REQUESTS)
        self.assertIsNotNone(response.network_error)


if __name__ == "__main__":
    unittest.main()
