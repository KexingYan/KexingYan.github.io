# Final Pre-deployment Review

**Review date:** 2026-07-31
**Branch:** `main`
**HEAD:** `6202ce10b18cf6fe9aa88d39ca177c0ab76ec17a`
**Remote:** `https://github.com/KexingYan/KexingYan.github.io.git`
**Deployment, push, or dashboard change:** None

## Safety verdict

The repository identity and author configuration match Kexing Yan, and the
working tree contains the expected Phase 0–15 and release-hardening work. No
secret, private repository URL, personal financial data, Codex citation,
machine-specific absolute path, environment file, executable payload, or
unexplained binary change was found.

Local commits were not created. Five historical commits cannot be reconstructed
safely because multiple phases overlap inside the same files. A three-commit,
file-boundary plan is coherent, but this execution environment denied creation
of `.git/index.lock`, so even staging was unavailable. The worktree remains
unstaged and unchanged by that failed Git operation; the release report supplies
the exact commands for a normal Git environment.

## Changed-file disposition

“Personal” means intentionally public identity/contact content, not a secret.
All listed files should enter Git. Only rows marked **Yes** enter `dist`.

| Changed file | Class | Deploy | Local path | Personal | Secret | Generated | Rollback risk |
|---|---|---:|---:|---:|---:|---:|---|
| `.gitignore` | Internal repository control | No | No | No | No | No | Low |
| `.github/workflows/validate-site.yml` | Internal CI | No | No | No | No | No | Low |
| `README.md` | Internal documentation | No | No | Public identity only | No | No | Low |
| `_headers` | Public Cloudflare config | Yes | No | No | No | No | Medium: response semantics |
| `_redirects` | Public Cloudflare config | Yes | No | No | No | No | Medium: route semantics |
| `404.html` | Public error page | Yes | No | Public identity | No | No | Low |
| `index.html` | Public homepage | Yes | No | Public identity, email, profiles | No | No | Medium: primary route |
| `research/microloan-quantity-size/index.html` | Public research page | Yes | No | Public author/affiliation | No | No | Medium: canonical research route |
| `assets/css/research.css` | Public stylesheet | Yes | No | No | No | No | Low |
| `assets/icons/apple-touch-icon.png` | Public icon | Yes | No | No | No | No; lossless binary change | Low |
| `assets/icons/favicon-16x16.png` | Public icon | Yes | No | No | No | No; lossless binary change | Low |
| `assets/icons/favicon-32x32.png` | Public icon | Yes | No | No | No | No; lossless binary change | Low |
| `assets/icons/favicon-48x48.png` | Public icon | Yes | No | No | No | No; lossless binary change | Low |
| `assets/icons/favicon-192x192.png` | Public icon | Yes | No | No | No | No; lossless binary change | Low |
| `assets/icons/favicon-512x512.png` | Public icon | Yes | No | No | No | No; lossless binary change | Low |
| `assets/icons/kx-logo.png` | Source-only legacy asset | No | No | No | No | No; lossless binary change | Low; intentionally excluded |
| `assets/images/kexing-yan-open-graph.png` | Public social preview | Yes | No | Public identity | No | No; lossless binary change | Low |
| `papers/the-quantity-and-size-of-microloans.pdf` | Frozen public research PDF | Yes | No | Public author/affiliation | No | No; accepted metadata change | High: byte-frozen |
| `robots.txt` | Public crawler policy | Yes | No | No | No | No | Medium: crawler intent |
| `sitemap.xml` | Public discovery file | Yes | No | No | No | No | Medium: canonical inventory |
| `llms.txt` | Public navigation aid | Yes | No | Public identity | No | No | Low |
| `scripts/build_site.py` | Internal build tooling | No | No | No | No | No | Medium: artifact boundary |
| `scripts/validate_site.py` | Internal validation | No | No | No | No | No | Medium: release gate |
| `scripts/verify_production.py` | Internal read-only verifier | No | No | No | No | No | Low |
| `scripts/test_build_site.py` | Internal tests | No | No | No | No | No | Low |
| `scripts/test_validate_site.py` | Internal tests | No | Generic test paths only | No | Fake test tokens only | No | Low |
| `scripts/test_verify_production.py` | Internal tests | No | Generic test URL only | No | Fake credential test only | No | Low |
| `scripts/site_dates.json` | Internal date governance | No | No | No | No | No | Medium: freshness source |
| `docs/ai-discoverability-audit.md` | Internal historical audit | No | Generic command paths only | Public identity | No | No | Low |
| `docs/phase-0-5-acceptance-review.md` | Internal historical review | No | Generic `/private/tmp` example | Public identity | No | No | Low |
| `docs/crawler-policy.md` | Internal policy | No | No | No | No | No | Low |
| `docs/site-knowledge-graph.md` | Internal architecture | No | No | Public identity | No | No | Low |
| `docs/project-page-content-gaps.md` | Internal decision record | No | No | No | No | No | Low |
| `docs/media-audit.md` | Internal audit | No | No | Public identity | No | No | Low |
| `docs/pdf-accessibility-audit.md` | Internal audit | No | No | Public author | No | No | Low |
| `docs/freshness-policy.md` | Internal policy | No | No | No | No | No | Low |
| `docs/metadata-audit.md` | Internal audit | No | No | Public identity | No | No | Low |
| `docs/llms-txt-decision.md` | Internal decision record | No | No | Public identity | No | No | Low |
| `docs/cloudflare-manual-checklist.md` | Internal operations | No | No | No | No | No | Low |
| `docs/search-console-post-deployment.md` | Internal operations | No | No | No | No | No | Low |
| `docs/deployment-manifest.md` | Internal operations | No | No | No | No | No | Low |
| `docs/deployment-readiness.md` | Internal review | No | No | No | No | No | Low |
| `docs/validation-report.md` | Internal validation record | No | Generic localhost command | No | No | No | Low |
| `docs/final-predeployment-review.md` | Internal review | No | No | Public identity | No | No | Low |
| `docs/release-candidate-report.md` | Internal release record | No | No | Public identity | No | No | Low |

Unchanged but deployed sources—`site.webmanifest`, both résumé PDFs, and the
Baidu verification file—were also traced and allowlisted. The résumés contain
intentionally public contact details and retain HTTP `noindex`; noindex is not
treated as access control.

## Binary review and PDF freeze

- All eight changed PNG files are pixel-identical to their `HEAD` versions;
  only lossless encoding size changed.
- The unreferenced 1024×1024 `kx-logo.png` remains in Git but is excluded from
  `dist`.
- Accepted PDF SHA-256:
  `fd8d7d2e5c885dc37ee5ab9f31a3f28fe47b833d5555edaddd5dc30888179219`.
- Source and `dist` copies are both 510,338 bytes, 30 pages, PDF 1.5, and have
  identical hashes. No PDF-writing tool was used in this phase.

## Ignored and temporary material

Ignored `tmp/` contains earlier PDF renders, optimization candidates, and text
extractions. Ignored `scripts/__pycache__/` contains generated bytecode. Both
are local review output, are absent from `dist`, and must remain untracked.
Generated `dist/` and `dist-manifest.json` are also ignored; Cloudflare should
rebuild them from source.

## Sensitive-content review

Pattern scans and contextual inspection covered local home-directory markers,
localhost and loopback addresses, `file://`, environment names,
authorization/cookie/password terms, private keys, API keys, tokens, Codex
citations, editor files, and private-project terms. Matches were limited to
generic development commands, validator rejection markers, or documentation
explaining prohibited data.

The internal Market Radar decision record contains no project implementation
details: it states that evidence is insufficient and lists future disclosure
requirements. Nothing about Market Radar enters `dist`.

## Research Open Graph decision

The research page retains the existing 1200×630 identity preview. It is clear,
high-contrast, verified, and accompanied by research-specific title,
description, URL, type, and alt metadata. A second bitmap would add maintenance
and visual-review cost without a source artwork or material improvement. No
fake journal styling, portrait, DOI, or unsupported result was introduced.
