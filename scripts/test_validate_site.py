#!/usr/bin/env python3
"""Regression tests for validate_site.py."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from build_site import ROOT, build
from validate_site import DOMAIN, PERSON_ID, validate


class ValidatorTests(unittest.TestCase):
    def make_site(
        self,
        *,
        canonical: str = f"{DOMAIN}/",
        extra_head: str = "",
        extra_body: str = "",
        extra_graph: str = "",
        lastmod: str = "2026-07-31",
        profile_modified: object = "2026-07-31T16:32:46+08:00",
        redirects: str | None = None,
    ) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)

        homepage = f"""<!doctype html>
<html lang="en-CA">
<head>
  <meta charset="utf-8">
  <title>Kexing Yan</title>
  <meta name="description" content="Profile of Kexing Yan.">
  <meta name="robots" content="index, follow">
  <meta name="author" content="Kexing Yan">
  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{canonical}">
  <meta property="og:title" content="Kexing Yan">
  <meta property="og:description" content="Profile of Kexing Yan.">
  <meta property="og:image" content="{DOMAIN}/image.png">
  <meta property="og:image:secure_url" content="{DOMAIN}/image.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="Kexing Yan profile preview">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Kexing Yan">
  <meta name="twitter:description" content="Profile of Kexing Yan.">
  <meta name="twitter:image" content="{DOMAIN}/image.png">
  <meta name="twitter:image:alt" content="Kexing Yan profile preview">
  {extra_head}
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@graph": [
      {{
        "@type": "WebSite",
        "@id": "{DOMAIN}/#website",
        "url": "{DOMAIN}/"
      }},
      {{
        "@type": "ProfilePage",
        "@id": "{DOMAIN}/#profile",
        "url": "{DOMAIN}/",
        "dateModified": {json.dumps(profile_modified)},
        "mainEntity": {{"@id": "{PERSON_ID}"}}
      }},
      {{
        "@type": "Person",
        "@id": "{PERSON_ID}",
        "name": "Kexing Yan",
        "alternateName": "严可行",
        "url": "{DOMAIN}/"
      }}
      {extra_graph}
    ]
  }}
  </script>
</head>
<body>
  <a class="skip-link" href="#main-content">Skip</a>
  <main id="main-content"><h1>Kexing Yan</h1>{extra_body}</main>
  <time datetime="2026-07-31">31 July 2026</time>
  <footer>© 2026 Kexing Yan</footer>
</body>
</html>"""
        (root / "index.html").write_text(homepage, encoding="utf-8")
        (root / "image.png").write_bytes(
            b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" +
            (1200).to_bytes(4, "big") + (630).to_bytes(4, "big")
        )

        not_found = """<!doctype html>
<html lang="en-CA"><head>
<title>Not found</title>
<meta name="description" content="Page not found.">
<meta name="robots" content="noindex, follow">
</head><body>
<a class="skip-link" href="#main-content">Skip</a>
<main id="main-content"><h1>Not found</h1></main><footer>© 2026 Kexing Yan</footer>
</body></html>"""
        (root / "404.html").write_text(not_found, encoding="utf-8")

        robots = f"""User-agent: Googlebot
Allow: /
User-agent: Bingbot
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: ChatGPT-User
Allow: /
User-agent: Claude-SearchBot
Allow: /
User-agent: Claude-User
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: Perplexity-User
Allow: /
User-agent: Google-Extended
Allow: /
User-agent: GPTBot
Disallow: /
User-agent: ClaudeBot
Disallow: /
User-agent: *
Allow: /
Sitemap: {DOMAIN}/sitemap.xml
"""
        (root / "robots.txt").write_text(robots, encoding="utf-8")

        sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{DOMAIN}/</loc><lastmod>{lastmod}</lastmod></url>
</urlset>"""
        (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        (root / "_headers").write_text(
            """/assets/resume/*
  X-Robots-Tag: noindex
/papers/the-quantity-and-size-of-microloans.pdf
  Content-Type: application/pdf
  Content-Disposition: inline
  Content-Language: en-CA
  X-Content-Type-Options: nosniff
/llms.txt
  Content-Type: text/plain; charset=utf-8
""",
            encoding="utf-8",
        )
        (root / "scripts").mkdir()
        (root / "scripts" / "site_dates.json").write_text(
            json.dumps({
                "schemaVersion": 1,
                "copyrightYear": 2026,
                "pages": {
                    "/": {
                        "dateModified": "2026-07-31",
                        "structuredDataDateModified": profile_modified,
                        "sitemapLastmod": lastmod,
                    }
                },
                "works": {},
                "files": {},
            }),
            encoding="utf-8",
        )
        if redirects is not None:
            (root / "_redirects").write_text(redirects, encoding="utf-8")
        return root

    def assert_fails_with(self, root: Path, text: str) -> None:
        errors, _ = validate(root)
        self.assertTrue(
            any(text in error for error in errors),
            f"expected {text!r} in {errors}",
        )

    def test_valid_fixture_passes(self) -> None:
        errors, _ = validate(self.make_site())
        self.assertEqual(errors, [])

    def test_duplicate_description_is_rejected(self) -> None:
        root = self.make_site(
            extra_head='<meta name="description" content="Duplicate.">'
        )
        self.assert_fails_with(root, "description: expected exactly one")

    def test_lookalike_canonical_domain_is_rejected(self) -> None:
        root = self.make_site(canonical="https://kexingyan.com.evil.test/")
        self.assert_fails_with(root, "malformed canonical")

    def test_conflicting_person_definition_is_rejected(self) -> None:
        root = self.make_site(
            extra_graph=f""",
            {{
              "@type": "Person",
              "@id": "{PERSON_ID}",
              "name": "Different Name"
            }}"""
        )
        self.assert_fails_with(root, "conflicting definitions")

    def test_link_cannot_escape_repository(self) -> None:
        root = self.make_site(extra_body='<a href="../secret.txt">Bad</a>')
        self.assert_fails_with(root, "escapes repository root")

    def test_spa_fallback_is_rejected(self) -> None:
        root = self.make_site(redirects="/* /index.html 200\n")
        self.assert_fails_with(root, "soft 404s")

    def test_missing_redirect_destination_is_rejected(self) -> None:
        root = self.make_site(redirects="/old /missing/ 301\n")
        self.assert_fails_with(root, "missing destination")

    def test_missing_open_graph_alt_is_rejected(self) -> None:
        root = self.make_site()
        homepage = root / "index.html"
        homepage.write_text(
            homepage.read_text(encoding="utf-8").replace(
                'content="Kexing Yan profile preview">', 'content="">', 1
            ),
            encoding="utf-8",
        )
        self.assert_fails_with(root, "property og:image:alt: value is empty")

    def test_open_graph_dimension_mismatch_is_rejected(self) -> None:
        root = self.make_site()
        homepage = root / "index.html"
        homepage.write_text(
            homepage.read_text(encoding="utf-8").replace(
                'og:image:width" content="1200"',
                'og:image:width" content="1199"',
            ),
            encoding="utf-8",
        )
        self.assert_fails_with(root, "do not match file")

    def test_date_source_mismatch_is_rejected(self) -> None:
        root = self.make_site()
        source = root / "scripts" / "site_dates.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        data["pages"]["/"]["dateModified"] = "2026-07-30"
        source.write_text(json.dumps(data), encoding="utf-8")
        self.assert_fails_with(root, "visible updated date does not match")

    def test_profile_datetime_accepts_offset_and_z(self) -> None:
        for value in (
            "2026-07-31T16:32:46+08:00",
            "2026-07-31T08:32:46Z",
        ):
            with self.subTest(value=value):
                errors, _ = validate(self.make_site(profile_modified=value))
                self.assertEqual(errors, [])

    def test_invalid_profile_datetimes_are_rejected(self) -> None:
        for value in (
            "2026-07-31",
            "2026/07/31",
            "31-07-2026",
            "2026-07-31T16:32:46",
            "2026-02-30T12:00:00+08:00",
            "invalid",
        ):
            with self.subTest(value=value):
                self.assert_fails_with(
                    self.make_site(profile_modified=value),
                    "full ISO 8601 DateTime with seconds and timezone",
                )

    def test_profile_datetime_must_be_a_string(self) -> None:
        self.assert_fails_with(
            self.make_site(profile_modified=20260731),
            "ProfilePage.dateModified must be a string",
        )

    def test_future_profile_datetime_is_rejected(self) -> None:
        self.assert_fails_with(
            self.make_site(profile_modified="2999-07-31T16:32:46+08:00"),
            "ProfilePage.dateModified must not be in the future",
        )

    def test_profile_datetime_calendar_date_must_match_page_date(self) -> None:
        self.assert_fails_with(
            self.make_site(profile_modified="2026-07-30T16:32:46+08:00"),
            "datetime calendar date differs from page modification date",
        )

    def test_broken_llms_reference_is_rejected(self) -> None:
        root = self.make_site()
        (root / "llms.txt").write_text(
            f"# Site\n- Missing: {DOMAIN}/missing/\n", encoding="utf-8"
        )
        self.assert_fails_with(root, "missing local resource")

    def test_invalid_lastmod_is_rejected(self) -> None:
        root = self.make_site(lastmod="today")
        self.assert_fails_with(root, "invalid lastmod")

    def test_real_deployment_artifact_passes(self) -> None:
        build()
        errors, _ = validate(ROOT / "dist", source_root=ROOT, artifact=True)
        self.assertEqual(errors, [])

    def test_artifact_rejects_unexpected_internal_file(self) -> None:
        build()
        unexpected = ROOT / "dist" / "scripts" / "validator.py"
        unexpected.parent.mkdir()
        unexpected.write_text("# must not deploy\n", encoding="utf-8")
        self.addCleanup(build)
        errors, _ = validate(ROOT / "dist", source_root=ROOT, artifact=True)
        self.assertTrue(
            any("unexpected files" in error for error in errors), errors
        )


if __name__ == "__main__":
    unittest.main()
