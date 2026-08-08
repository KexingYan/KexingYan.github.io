#!/usr/bin/env python3
"""Regression tests for the explicit deployment allowlist."""

from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from build_site import (
    FORBIDDEN_TOP_LEVEL,
    LOCAL_PHOTOGRAPHY_ASSET_BASE,
    PHOTOGRAPHY_MANIFEST_URL,
    PUBLIC_FILES,
    ROOT,
    build,
    ensure_safe_file,
    sha256,
)


class BuildSiteTests(unittest.TestCase):
    def test_allowlist_excludes_internal_and_unreferenced_files(self) -> None:
        self.assertFalse(any(path.endswith(".py") for path in PUBLIC_FILES))
        self.assertFalse(any(path.startswith("docs/") for path in PUBLIC_FILES))
        self.assertNotIn("README.md", PUBLIC_FILES)
        self.assertNotIn("assets/icons/kx-logo.png", PUBLIC_FILES)
        self.assertTrue(FORBIDDEN_TOP_LEVEL.isdisjoint(
            {path.split("/", 1)[0] for path in PUBLIC_FILES}
        ))

    def test_build_preserves_source_bytes_except_reviewed_photography_rewrites(self) -> None:
        manifest = build()
        self.assertEqual(manifest["fileCount"], len(PUBLIC_FILES))
        transformed = {
            "assets/photography/config.js",
            "index.html",
            "photography/index.html",
            "photography/license/index.html",
        }
        for record in manifest["files"]:
            relative = record["path"]
            self.assertEqual(record["sha256"], sha256(ROOT / "dist" / relative))
            if relative not in transformed:
                self.assertEqual(record["sha256"], sha256(ROOT / relative))
        config = (ROOT / "dist" / "assets/photography/config.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('"mode": "production"', config)
        self.assertIn(PHOTOGRAPHY_MANIFEST_URL, config)
        for relative in transformed - {"assets/photography/config.js"}:
            html = (ROOT / "dist" / relative).read_text(encoding="utf-8")
            self.assertNotIn(LOCAL_PHOTOGRAPHY_ASSET_BASE, html)

    def test_missing_required_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(RuntimeError, "required public file is missing"):
                ensure_safe_file(root, "missing.txt")

    def test_symlinked_public_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.txt"
            target.write_text("public", encoding="utf-8")
            link = root / "link.txt"
            link.symlink_to(target)
            with self.assertRaisesRegex(RuntimeError, "symlink"):
                ensure_safe_file(root, "link.txt")


if __name__ == "__main__":
    unittest.main()
