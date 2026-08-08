# Validation Report

**Scope:** Phase 0–15 acceptance and implementation
**Validation date:** 2026-07-31
**Baseline commit:** `6202ce10b18cf6fe9aa88d39ca177c0ab76ec17a`
**Deployment performed:** No

## Implemented scope

- Phase 0–5 independently accepted after remediation; see
  `docs/phase-0-5-acceptance-review.md`.
- A canonical HTML page now makes the verified microloan student working paper
  readable and citable without opening its PDF.
- The research page has visible status, summary, methods, qualified findings,
  limitations, resources, and four citation formats.
- Metadata and a restrained `ScholarlyArticle` graph match the visible page.
- Market Radar, standalone About, and Media pages were intentionally deferred
  because verified content is insufficient or would duplicate the homepage.
- Homepage writing and links now point to the research summary without
  overstating causal mechanisms or publication status.
- The final canonical route/entity graph is documented in
  `docs/site-knowledge-graph.md`.
- Social previews now have complete secure URL, dimension, and alternative-text
  metadata; referenced PNGs were losslessly compressed.
- The paper PDF has verified descriptive metadata and document language while
  remaining visually and textually unchanged; structural tagging remains a
  source-level limitation.
- Public dates are governed through `scripts/site_dates.json` and checked
  against visible dates, JSON-LD, citation fields, and sitemap `lastmod`.
- A concise `llms.txt`, deployment manifest, read-only production verifier, and
  manual Cloudflare/Search Console checklists are prepared but not executed.

## Local commands

```sh
python3 scripts/build_site.py
python3 scripts/validate_site.py
python3 scripts/validate_site.py --root dist
python3 -m unittest discover -s scripts -p 'test_*.py' -v
xmllint --noout dist/sitemap.xml
git diff --check
python3 -m py_compile scripts/build_site.py scripts/validate_site.py scripts/test_build_site.py scripts/test_validate_site.py scripts/verify_production.py scripts/test_verify_production.py
python3 -m http.server 8002 --bind 127.0.0.1 --directory dist
```

There is no framework, package lint, or typecheck command. The dependency-free
build creates the release artifact in `dist`; serving the repository root is no
longer an accepted production simulation.

## Automated coverage

The validator checks:

- discovery of canonical indexable HTML routes;
- local file and fragment targets without repository-root escape;
- unique titles, descriptions, and canonical URLs;
- canonical/OG consistency and required social metadata;
- index/noindex expectations;
- H1 count and heading order;
- image alt text and dimensions;
- JSON-LD parsing, stable entities, conflicting definitions, and internal
  references;
- research status, citations, PDF link, article metadata, and canonical author
  reference;
- required crawler-policy tokens and sitemap directive;
- sitemap syntax, local targets, canonical coverage, and date format;
- rejection of catch-all 200 SPA fallbacks; and
- noindex headers for intentionally public résumé resources.

The artifact gate additionally enforces the exact public allowlist, internal
file exclusion, absence of symlinks and local paths, asset/reference closure,
manifest hashes/categories, and byte identity of the frozen paper PDF.

The validation suite additionally covers a duplicate description, deceptive
canonical domain, conflicting Person, path escape, SPA fallback, missing
redirect target, invalid `lastmod`, missing preview alt text, image-dimension
drift, date-source drift, broken `llms.txt` links, URL normalization, and a valid
fixture.

## Rendered-output review

Local browser review confirmed:

- desktop homepage and research-page layout;
- mobile homepage and research-page layout at a 390 x 844 viewport, with no
  horizontal overflow;
- one visible H1 per page;
- important identity and research content in initial HTML;
- semantic header/navigation/main/article/footer structure;
- skip-link target, focus styling, and keyboard eligibility;
- English/Chinese homepage switch, `html[lang]`, and CV target changes;
- working internal routes and fragments;
- readable research citations without JavaScript;
- parsed JSON-LD inventory and metadata consistency; and
- no page-script console errors.

Responsive CSS was also inspected at the 860/760/540/480-pixel breakpoints. It
collapses grids and navigation without introducing duplicate DOM content. A
true physical-device, multi-engine, screen-reader accessibility and visual lab
was not available locally and remains a post-deployment check. The in-app
browser's synthetic Tab action did not expose a reliable focus transition, so
the skip link was accepted from its native focusable anchor, visible `:focus`
rule, and existing `main tabindex="-1"` target—not from a claimed end-to-end
screen-reader result.

## Research evidence and PDF alignment

The 30-page PDF visibly identifies the title, Kexing Yan, University of
Toronto, and 9 July 2026. Its text supports the HTML page's data period,
methods, qualified findings, and limitations. PDF document metadata does not
alter the visible paper: verified Title, Author, Subject, Keywords, document
language, and a technical metadata modification date were added incrementally.
All 30 rendered pages, extracted text, bookmarks, and link annotations remained
identical. The document is still untagged; exporting a semantically tagged PDF
from the missing manuscript source remains the safest structural remediation.

The English résumé visibly prints `kexingyan.com/papers`. Rather than alter the
PDF, exact `/papers` and `/papers/` 301 rules now point to the canonical HTML
research page. No wildcard or 200 fallback was introduced.

## Deployment-dependent checks

After deployment:

1. Confirm an unknown path returns a genuine HTTP 404.
2. Confirm `www` redirects preserve the unknown path.
3. Confirm `/papers` and `/papers/` return one 301 to the canonical HTML
   research page without affecting the PDF URL.
4. Confirm `_headers` applies `X-Robots-Tag: noindex` to résumés and that
   documentation, scripts, `README.md`, governance data, and CI files return
   404 because they are absent from the deployed artifact.
5. Confirm the homepage, HTML research page, and PDF remain indexable.
6. Confirm robots and sitemap MIME types and bodies.
7. Confirm `llms.txt`, Open Graph assets, PDF headers, and configured cache
   policies are served as intended.
8. Check Cloudflare WAF/Bot settings do not challenge allowed crawlers.
9. Run Lighthouse/axe, keyboard, focus, contrast, and screen-reader smoke tests
   against the deployed site.

No deployment, commit, push, URL submission, indexing request, or dashboard
modification was performed.
