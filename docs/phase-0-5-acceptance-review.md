# Phase 0–5 Independent Acceptance Review

**Review date:** 2026-07-31
**Branch:** `main`
**Baseline commit:** `6202ce10b18cf6fe9aa88d39ca177c0ab76ec17a`
**Deployment or dashboard change:** None

## Scope and method

The repository was treated as unverified evidence. The review inspected the
complete Git status and diff, every changed and untracked file, static publish
configuration, generated browser DOM, metadata, every JSON-LD block, sitemap,
robots policy, response-header rules, PDFs, validator implementation, and
documentation.

The repository is a root-published static Cloudflare Pages site. It has no
framework, package manifest, compilation step, lint command, or type checker.
The deployable output is therefore the repository's public files themselves.

Commands used included:

```sh
git status --short
git branch --show-current
git diff --check
git diff
rg --files
python3 scripts/validate_site.py
python3 -m unittest discover -s scripts -p 'test_*.py' -v
(cd /private/tmp && python3 /path/to/repository/scripts/validate_site.py)
xmllint --noout sitemap.xml
python3 -m http.server 8002 --bind 127.0.0.1
pdfinfo papers/the-quantity-and-size-of-microloans.pdf
pdftotext -layout papers/the-quantity-and-size-of-microloans.pdf -
```

Browser review used the locally served site rather than `file:` URLs. It
inspected semantic DOM snapshots, computed visibility and focus state, language
behavior, link targets, metadata, JSON-LD parsing, desktop rendering, and
console output.

## Previous-claim results

| Previous claim | Status | Evidence and affected files | Rendered-output observation | Remaining risk and remediation |
|---|---|---|---|---|
| Repository and baseline audit | PASS WITH CAVEAT | `docs/ai-discoverability-audit.md`; Git and file inventory commands | Route and content observations match local output | Production headers/status cannot be proven locally; post-deployment checks remain |
| Static 404 page | PASS WITH CAVEAT | `404.html`, `_headers`; validator and local server | Clear bilingual recovery page, one H1, working skip target and links, matching visual language | Cloudflare's real unknown-path status is NOT VERIFIABLE LOCALLY; verify after deployment |
| Clear homepage H1 | PASS after remediation | `index.html`; DOM reported one visible H1 | Natural heading “Kexing Yan (严可行)” with factual supporting text | Chinese state is client-rendered at the same URL |
| Person, WebSite, ProfilePage, university JSON-LD | PASS after remediation | JSON parser inventory of `index.html` | One graph in initial HTML; no client execution needed | Rich-result eligibility or search interpretation is never guaranteed |
| Accessibility improvements | PASS WITH CAVEAT | `index.html`, `404.html`, `assets/css/research.css`; keyboard/DOM review | Skip links, landmarks, focus styles, reduced motion, native controls, logical headings | No screen-reader lab, multi-engine traversal, or third-party axe run |
| Bilingual UI and CV links | PASS WITH CAVEAT | `index.html`, both résumé PDFs | Language control updates visible text, accessible label, `html[lang]`, and résumé target; English remains usable without JS | No separate crawlable Chinese URL or Chinese metadata; intentionally no `hreflang` |
| Semantic footer | PASS | `index.html`, research page | Concise `contentinfo` with named navigation and real destinations | None material |
| Sitemap lastmod updates | PASS | `sitemap.xml`; XML parser and validator | Canonical HTML routes and intentional PDF are present; 404/state fragments absent | Dates require editorial discipline; validator can reject malformed/future dates but cannot prove editorial meaning |
| Crawler policy | PASS WITH CAVEAT | `robots.txt`, `docs/crawler-policy.md`; official operator documentation | Plain static file, exact documented tokens, sitemap directive | Cloudflare can still challenge/block allowed agents; policy cannot guarantee crawl, indexing, citation, or ranking |
| Zero-dependency validator | PASS after remediation | `scripts/validate_site.py`, `scripts/test_validate_site.py` | Deterministic successful output locally and from another working directory | It is a structural validator, not a browser engine, HTTP server, schema authority, or WCAG auditor |

## A1 — Validation script audit

The previous implementation was not accepted on reputation. It was read
line-by-line and exercised with mutation fixtures.

- **Actual output:** it discovers deployable HTML under the root-published
  tree and excludes non-route source/document paths. It does not mistake
  documentation for indexable HTML.
- **Route discovery:** routes are derived from files rather than a hard-coded
  page list. Stable entity IDs and required crawler tokens are intentional
  policy invariants, not route assumptions.
- **Metadata:** duplicate titles, descriptions, canonicals, Open Graph fields,
  and conflicting canonical URLs fail validation.
- **Structured data:** every block uses `json.loads`; duplicate/conflicting
  `@id` definitions, unresolved internal references, malformed internal URLs,
  duplicate Person/Website definitions, and author-ID drift fail.
- **Links and redirects:** local files and fragments are resolved without
  escaping the repository; `_redirects` is rejected if it introduces a
  catch-all 200 SPA fallback. Redirect response behavior still needs HTTP
  testing after deployment.
- **Accessibility:** H1 count, heading order, image alternatives/dimensions,
  skip target, and key language controls are structural checks. File existence
  is not treated as proof of keyboard, screen-reader, or contrast behavior.
- **Sitemap dates:** valid and non-future dates are checked. Editorial meaning
  is manually reviewed because no general validator can infer it.
- **Failure behavior:** exceptions are reported, failures exit non-zero, and no
  check silently converts an exception into a pass.
- **Portability:** repository root is resolved from the script location; a run
  from `/private/tmp` succeeds.
- **Determinism:** no network, current-build timestamp, or third-party package
  is used.

Eight regression tests prove rejection of duplicate descriptions, a deceptive
canonical host, conflicting Person definitions, repository-root escapes, an
SPA fallback, a missing redirect target, and invalid `lastmod`, plus acceptance
of a valid fixture.

Remaining caveat: HTTP statuses, rendered contrast, CSS media behavior, and
third-party Schema.org interpretation remain separate checks by design.

## A2 — 404 acceptance

`404.html` is in the publish root, has `noindex, follow`, has no canonical URL,
contains one clear H1, has a functional skip target, and links only to existing
homepage destinations. `_redirects` contains only two exact 301 forms of the
legacy `/papers` path; there is no wildcard rule, SPA router, framework
fallback, or script that converts unknown paths to `index.html`. The static
page is bilingual without requiring a language switch.

The local static server correctly serves the file itself but does not emulate
Cloudflare Pages unknown-route semantics. Therefore the production HTTP-status
claim is **NOT VERIFIABLE LOCALLY**.

After deployment, run:

```sh
curl -I https://kexingyan.com/a-definitely-nonexistent-test-path
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://kexingyan.com/a-definitely-nonexistent-test-path
curl -I https://kexingyan.com/404.html
curl -I -L https://www.kexingyan.com/a-definitely-nonexistent-test-path
curl -I https://kexingyan.com/papers
```

The nonexistent path must return a genuine final `404`, not a 200 response
containing 404-looking content. The `www` chain should preserve the requested
path before reaching the apex 404. A direct `/404.html` response may be 200,
but its HTML must retain `noindex`. `/papers` must return 301 with the research
page as its location; the PDF URL must continue to return its own file.

## A3 — Homepage content

**Status: PASS after remediation.**

The rendered DOM has exactly one visible H1: “Kexing Yan (严可行)”. It is not
duplicated by responsive markup. A concise paragraph immediately identifies
the University of Toronto, Economics, Statistics, Data Analytics, and the
site's student-research focus. The initial English text is readable HTML,
visible in computed styles, and does not require JavaScript. Heading order is
H1 → H2 → H3. The earlier keyword-heavy H1 was replaced with a natural name
heading and supporting description.

## A4 — Structured data

**Status: PASS after remediation.**

Every JSON-LD block parses as JSON. The homepage contains exactly one
definition each for:

- `https://kexingyan.com/#website`
- `https://kexingyan.com/#profile`
- `https://kexingyan.com/#person`
- `https://kexingyan.com/#university-of-toronto`

`ProfilePage.mainEntity` and `Person.mainEntityOfPage` use the canonical
references. The current-student relationship is `affiliation`; there is no
`alumniOf` or `jobTitle`. `knowsAbout` is limited to the three verified academic
areas. The university node is minimal and points to its official URL. Language
switching does not generate a second graph. The initial implementation's
unnecessary Website alternate name, university `sameAs`, and quasi-professional
job title were removed.

## A5 — Crawler policy

**Status: PASS WITH CAVEAT.**

Exact tokens were checked against current official operator documentation:
`Googlebot`, `Bingbot`, `OAI-SearchBot`, `GPTBot`, `ChatGPT-User`,
`ClaudeBot`, `Claude-SearchBot`, `Claude-User`, `PerplexityBot`,
`Perplexity-User`, and `Google-Extended`.

Search/citation and user-triggered agents are allowed. `GPTBot` and
`ClaudeBot` are blocked. `Google-Extended` is deliberately allowed with an
explicit trade-off: the control can govern specified future Gemini training
and Gemini grounding uses outside ordinary Search, so this is not a
grounding-only opt-in. Normal Google Search and its AI search features are
primarily controlled through Googlebot and Search controls. The documentation
also states that other training collection paths may exist, Cloudflare may
override effective access, robots is not security/privacy, and permission does
not guarantee discovery, indexing, citation, or ranking.

## A6 — Sitemap and lastmod

**Status: PASS.**

The XML parses. It contains only HTTPS apex canonical URLs: the homepage, the
complete HTML research page, and its intentional public PDF. There are no 404,
redirect, query-state, fragment, résumé, documentation, or nonexistent routes.
Trailing slashes match directory HTML canonicals. The homepage and research
page dates represent the 2026-07-31 content changes; the PDF date matches its
visible 2026-07-09 manuscript date and file metadata. Dates are static, not
generated on each build.

## A7 — Accessibility

**Status: PASS WITH CAVEAT.**

Manual DOM and keyboard checks confirmed skip-link focus visibility and valid
focus targets, logical landmarks/headings, descriptive links, native language
buttons, accessible CV labels, named footer navigation, and no duplicate H1.
Focus indicators are high-contrast and not clipped in inspected layouts. The
original low-emphasis `#8a8a8a` text token was darkened to `#6f6f6f` so small
labels no longer sit below the normal-text contrast threshold on the light
background.
Reduced-motion CSS removes transitions, animations, and smooth scrolling. The
homepage scroll spy adds `aria-current="location"` only to the section
currently intersecting; the research page uses `aria-current="page"` only for
Research. Mobile navigation remains a single DOM navigation rather than a
hidden duplicate.

Formal color calculations, a screen-reader smoke test, multiple browser
engines, and axe/Lighthouse remain manual follow-up checks.

## A8 — Bilingual implementation

**Status: PASS WITH CAVEAT.**

One static English H1 and one set of content nodes are translated in place;
there are no hidden duplicate language trees. The control has an accessible
group label, `html[lang]` changes between `en-CA` and `zh-Hans`, and English and
Chinese CV links remain separately named and correctly targeted. `localStorage`
is optional: storage access is guarded, and English remains complete when
JavaScript or storage is unavailable.

Both presentations share one canonical URL, while title, description, Open
Graph, JSON-LD, and initial HTML remain English. This limits direct Chinese
search discovery and deep-linking. The site correctly does not emit
`hreflang` or pretend that language-specific URLs exist.

## A9 — Documentation

**Status: PASS after remediation.**

Documentation was reconciled with the implementation. Future work is labeled
as deferred, route inventories match real files, Cloudflare manual checks are
explicit, and “AI optimization” is not presented as a measurable ranking
result. Repository documentation contains no developer-machine absolute paths.
The earlier graph's nonexistent `WebSite.contains` edge and stale Phase 5-only
route statements were corrected.

## A10 — Acceptance gate

| Area | Status | Evidence | Remaining risk | Action |
|---|---|---|---|---|
| Repository/build model | PASS | Static files and root-publish configuration inspected | Dashboard may differ from documented setup | Confirm Pages root and branch after deployment |
| Validator | PASS | Source audit, eight mutation tests, cwd-independent run | Not a browser/HTTP/schema service | Keep structural scope explicit |
| 404 | NOT VERIFIABLE LOCALLY | Correct static artifact and no conflicting route rules | True edge status depends on Cloudflare | Run documented curl checks |
| Homepage identity | PASS | One visible natural H1 and readable initial HTML | Chinese is client-side | Consider stable Chinese routes only with full maintenance capacity |
| Structured data | PASS | JSON parser inventory and stable-ID checks | Search interpretation external | Revalidate after content edits |
| Crawler policy | PASS WITH CAVEAT | Exact official tokens and documented trade-offs | Cloudflare may block allowed agents | Review dashboard and edge responses |
| Sitemap | PASS | XML parse, local target and canonical checks | Editorial dates need care | Update dates only for meaningful changes |
| Accessibility | PASS WITH CAVEAT | Manual DOM, keyboard, focus, motion, mobile CSS review | No screen-reader/axe lab | Run external accessibility audit after deployment |
| Bilingual behavior | PASS WITH CAVEAT | In-place translation and graceful English fallback | No crawlable Chinese URL | Documented; no fake `hreflang` |
| Documentation | PASS | Files reconciled against code and diff | Can become stale | Update with future route changes |

No Critical or High acceptance failure remains. The deployment-dependent 404
status and Cloudflare behavior are explicitly separated from local acceptance.

**PHASE 0–5 ACCEPTED**
