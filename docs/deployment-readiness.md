# Deployment Readiness Review

**Review date:** 2026-07-31
**Branch:** `main`
**Deployment performed:** No

## Verdict

The working tree is locally ready for a controlled code review and deployment
decision. It is not described as production-ready because Cloudflare status,
redirects, headers, caching, bot/WAF behavior, physical-device rendering, and
screen-reader behavior have not been tested on the deployed revision. Local
browser checks did cover desktop and a 390 x 844 responsive viewport.

## Repository review

| Area | Result | Remaining action |
|---|---|---|
| Git status | Intentionally dirty; all Phase 0–15 plus final hardening work is uncommitted | Use the documented staged-file plan; do not force unsafe historical separation |
| Diff | Complete tracked/untracked inventory reviewed; `git diff --check` passes | Review binary PDF/image size changes in commit summary |
| Deployment boundary | Explicit 35-file allowlist builds `dist/` | Configure Cloudflare output as `dist`, never repository root |
| Temporary files | PDF renders and optimization candidates are under ignored `tmp/` | Validator confirms `tmp/` absent from `dist` |
| Local paths | No developer-machine absolute path in public site or project documentation | Re-run path scan before commit |
| Secrets / environment files | No `.env`, key, token, credential, or analytics secret found | Keep secret scan in pre-deployment checklist |
| Private projects | Market Radar and other unsupported private work are absent | Preserve this boundary |
| Screenshots / drafts | No public audit screenshots or unpublished drafts added | Keep QA renders in `tmp/` only |
| macOS / caches | `.DS_Store`, `__pycache__`, `*.pyc`, and `tmp/` ignored | Verify status is clean of generated files |
| PDF source | Original LaTeX/bibliography source is absent | Obtain source before structural PDF accessibility work |
| Public PDF | Metadata improved; 30 pages pixel-identical; still untagged | Verify production headers and plan source-level tagging |
| Links / metadata / JSON-LD | Local validator and mutation tests pass | Re-run immediately before deployment |
| Images | Dimensions and references valid; lossless compression applied | Verify preview fetch after deployment |
| Redirects | Exact `/papers` variants only; no 200 fallback | Verify real 301 responses at Cloudflare |
| Headers | Obsolete docs/scripts noindex rules removed because those files do not deploy | Verify Cloudflare applies remaining rules |
| Robots / sitemap / llms | Parse and local-reference checks pass | Fetch and compare live responses after deployment |
| 404 | Correct `noindex` artifact; no conflicting local fallback | Confirm a genuine live HTTP 404 |

## Deployment-boundary decision

Repository-root publication is no longer acceptable. The deterministic build
copies only reviewed public sources to `dist/`. Documentation, validators,
tests, date governance, CI configuration, caches, temporary renders, and the
unreferenced oversized logo remain outside the artifact. Noindex is retained
only where an intentionally public resource—currently the résumé PDFs—should
not appear as a standalone search result.

Cloudflare must use `python3 scripts/build_site.py` with output directory
`dist`. Until that dashboard configuration is confirmed, deployment behavior
remains unverified.

## Local acceptance boundary

Local checks can prove file presence, syntax, internal links, metadata
consistency, image dimensions, PDF preservation, and intended configuration.
They cannot prove Cloudflare response status, dashboard redirects, WAF/bot
decisions, cache behavior, header merging, search-engine canonical selection,
indexing, rich-result eligibility, or citation by an AI system.

Use `scripts/verify_production.py` only after deployment authorization. Its
ordinary requests are read-only and deliberately do not impersonate crawlers.
