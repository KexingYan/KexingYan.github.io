# Release Candidate Report

**Review date:** 2026-07-31
**Branch:** `main`
**HEAD before release commits:** `6202ce10b18cf6fe9aa88d39ca177c0ab76ec17a`
**Deployment performed:** No

## Release artifact

- Build command: `python3 scripts/build_site.py`
- Deployment output: `dist`
- File count: 21
- Total size: 1,349,362 bytes
- Deterministic manifest SHA-256:
  `ce6a412386385d8b3bc6854d49c6377e972a3b2173929829af4294471dddea0d`
- Internal manifest: `dist-manifest.json`; generated and not deployed

Largest public files:

| File | Bytes |
|---|---:|
| `papers/the-quantity-and-size-of-microloans.pdf` | 510,338 |
| `assets/images/kexing-yan-open-graph.png` | 477,432 |
| `assets/icons/favicon-512x512.png` | 110,659 |
| `assets/resume/Kexing-Yan-Resume-ZH.pdf` | 110,063 |
| `index.html` | 38,757 |
| `assets/resume/Kexing-Yan-Resume-EN.pdf` | 35,666 |

## Public routes and resources

HTML routes:

- `/`
- `/research/microloan-quantity-size/`
- `/404.html` as the direct error artifact
- `/baidu_verify_codeva-vWXLKxDtXl.html` for ownership verification

Other public resources include the accepted paper PDF, both intentionally
public noindex résumés, six browser/install icons, one Open Graph image, one
research stylesheet, `site.webmanifest`, `robots.txt`, `sitemap.xml`, and
`llms.txt`.

Redirects are exact only:

- `/papers` → `/research/microloan-quantity-size/` with 301
- `/papers/` → `/research/microloan-quantity-size/` with 301

Custom headers retain résumé `noindex`, inline PDF delivery with `en-CA` and a
one-hour revalidation cache, one-day social-image cache, and explicit plain-text
delivery for `llms.txt`.

## Excluded internal material

The exact artifact gate excludes `docs/`, `scripts/`, tests, README, CI source,
date-governance JSON, VCS data, ignored caches and renders, the generated
manifest, and unreferenced `assets/icons/kx-logo.png`. No Python file or symlink
exists in `dist`.

## PDF freeze

Frozen SHA-256:
`fd8d7d2e5c885dc37ee5ab9f31a3f28fe47b833d5555edaddd5dc30888179219`.

Source and artifact are each 510,338 bytes and 30 pages, with identical hashes
and the accepted Title, Author, Subject, Keywords, dates, language, and PDF 1.5
properties. No PDF rewrite occurred in final hardening.

## CI

`.github/workflows/validate-site.yml` runs on pull requests and pushes to
`main`, with `contents: read`. It checks out source, uses Python 3.12, builds
`dist`, validates source and artifact, runs unit tests and compilation, parses
the packaged sitemap with Python's standard library, and runs `git diff
--check`. It has no deployment job, token, secret, or write permission.

## Validation record

- Source validator: PASS
- `dist` validator: PASS
- Unit tests: 23 PASS
- Python compilation: PASS
- Packaged sitemap XML: PASS
- JSON-LD parsing: PASS
- Exact allowlist and manifest hashes: PASS
- No symlinks, internal files, local markers, or unknown files: PASS
- Two-build determinism comparison: PASS
- Build invoked from `/private/tmp`: PASS
- Desktop and 390×844 packaged rendering: PASS
- Homepage bilingual switch and résumé-target change: PASS
- Research stylesheet, status, citations, and PDF links: PASS
- Browser console warnings/errors: none
- `git diff --check`: PASS

Python's basic server does not emulate `_headers`, `_redirects`, Cloudflare 404
status, cache behavior, WAF, or bot management. Those remain unverified.

## Local release commits

No commit was created. Repository identity, author, remote, branch, diff,
binaries, secrets, and tests were verified, but the managed workspace denied
writing `.git/index.lock`. Use this exact three-commit plan in a normal Git
environment; it avoids partial hunks:

```sh
git add _headers _redirects 404.html index.html robots.txt sitemap.xml llms.txt assets/css/research.css assets/icons/apple-touch-icon.png assets/icons/favicon-16x16.png assets/icons/favicon-32x32.png assets/icons/favicon-48x48.png assets/icons/favicon-192x192.png assets/icons/favicon-512x512.png assets/icons/kx-logo.png assets/images/kexing-yan-open-graph.png research/microloan-quantity-size/index.html papers/the-quantity-and-size-of-microloans.pdf
git commit -m "feat: add authoritative research and discovery surfaces"

git add .gitignore .github/workflows/validate-site.yml scripts/build_site.py scripts/site_dates.json scripts/test_build_site.py scripts/test_validate_site.py scripts/test_verify_production.py scripts/validate_site.py scripts/verify_production.py
git commit -m "build: package and validate the public site artifact"

git add README.md docs
git commit -m "docs: record release readiness and deployment controls"
```

After each `git add`, inspect `git diff --cached --stat` and
`git diff --cached`. Then rerun the full release commands after the third
commit. HEAD before this proposed series is recorded above for rollback.

## Cloudflare configuration

- Production branch: `main`
- Root directory: repository root
- Build command: `python3 scripts/build_site.py`
- Output directory: `dist`
- Required environment variables: none
- Pages Functions: none
- Workers routes: none expected

## Release and verification commands

Push only after reviewing local commits:

```sh
git log --oneline 6202ce1..HEAD
git status --short
git push origin main
```

The connected Cloudflare Pages project is expected to trigger from the push to
`main`, run the documented build, and publish `dist`. Do not push until its
dashboard build/output fields match this report.

After deployment:

```sh
python3 scripts/verify_production.py https://kexingyan.com/
```

Then complete the Cloudflare and Search Console manual checklists. URL
submission remains a separate, later decision.

## Rollback

If production fails, use Cloudflare's previous successful deployment for the
fast operational rollback. For repository history, revert the release commits
in reverse order with `git revert <commit>`, rerun build and validation, review
the resulting commits, and push the reverts. Do not reset or rewrite `main`.

## Deployment blockers

Block deployment if any final build/validator/test fails; PDF hash changes;
`dist` includes an unknown, internal, local-path, secret, Python, or symlinked
file; canonical/JSON-LD/sitemap consistency fails; Cloudflare is still set to
publish the repository root; a catch-all 200 rewrite exists; or unrelated work
appears before push.

No local release-candidate blocker is currently present. Live Cloudflare
behavior is deliberately unresolved until an authorized deployment.
