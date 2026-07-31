# Kexing Yan — Personal Academic Website

First-party academic profile for Kexing Yan (严可行), published at
<https://kexingyan.com/>.

The site is intentionally lightweight: hand-authored static HTML, CSS, and
JavaScript with no framework or runtime dependency. Important English content
is present in the initial HTML; the Simplified Chinese presentation is applied
by the homepage language switch.

## Build and local validation

Requires Python 3 from the standard development environment. No third-party
package installation is needed.

Build the explicit public artifact first. The build uses an allowlist and writes
only intentional public files to `dist/`; `docs/`, Python tooling, tests,
governance data, caches, and the unreferenced large logo are excluded.

```sh
python3 scripts/build_site.py
python3 scripts/validate_site.py
python3 scripts/validate_site.py --root dist
```

The validator checks:

- local links and fragment targets;
- unique titles, descriptions, and canonical URLs;
- index/noindex expectations;
- one H1 and non-skipping heading order;
- image alt text and dimensions;
- JSON-LD syntax and canonical entity IDs;
- crawler-policy coverage;
- sitemap syntax, canonical URLs, and local targets;
- the presence and `noindex` policy of `404.html`; and
- research-page citation metadata, status, PDF, and author-entity consistency;
- Open Graph image URLs, dimensions, secure URLs, and alt text;
- visible/JSON-LD/sitemap date consistency through `scripts/site_dates.json`;
  and
- first-party references in `llms.txt`.

Run the validator's regression tests as well:

```sh
python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

The source-tree check protects editorial and governance invariants. The `dist`
check is the release gate: it verifies the exact artifact file set, hashes,
links, metadata, JSON-LD, headers, redirects, PDF byte preservation, lack of
symlinks, and absence of internal or machine-local material.

For local visual review of the packaged site:

```sh
python3 -m http.server 8000 --directory dist
```

Then open <http://localhost:8000/>.

## Repository structure

```text
index.html                       Public canonical profile source
404.html                         Public Cloudflare Pages not-found source
research/                        Public canonical research-page source
assets/css/                      Public stylesheets
assets/icons/                    Public browser/install icons plus one excluded source asset
assets/images/                   Public Open Graph image
assets/resume/                   Public, noindex résumé PDFs
papers/                          Public research PDF
robots.txt, sitemap.xml          Public discovery sources
llms.txt, site.webmanifest       Public machine/browser navigation sources
_redirects, _headers             Public Cloudflare Pages configuration
scripts/build_site.py            Explicit public allowlist and packaging logic
scripts/validate_site.py         Source/artifact validator
scripts/site_dates.json          Internal date-governance source
scripts/test_*.py                Internal regression tests
scripts/verify_production.py     Internal read-only post-deployment checks
docs/                            Internal project documentation
dist/                            Generated public artifact; never hand-edit
dist-manifest.json               Generated internal artifact hash inventory
.github/workflows/               Internal validation-only CI
```

## Deployment

The intended Cloudflare Pages configuration is:

- production branch: `main`
- root directory: repository root
- build command: `python3 scripts/build_site.py`
- build output directory: `dist`
- required environment variables: none
- Pages Functions / Workers routes: none

Pushing to `main` may trigger the connected Cloudflare Pages project, so push
only after an authorized release review. Do not configure the repository root
as the output directory.

## Search and indexing

- Google Search Console ownership is verified with a Cloudflare DNS TXT
  record. No Google verification token belongs in `index.html`.
- The homepage canonical URL is `https://kexingyan.com/`.
- The public sitemap is `https://kexingyan.com/sitemap.xml`; it includes the
  homepage, the canonical HTML research page, and the public research paper.
- `_headers` applies `X-Robots-Tag: noindex` to résumé files. Internal
  documentation and validation source are physically absent from `dist`.
- `robots.txt` allows ordinary search and documented AI search/citation
  crawlers. Separate OpenAI and Anthropic training crawlers are blocked;
  Google-Extended is deliberately allowed because Google currently couples
  that control with specified Gemini grounding uses.
- `404.html` is intended to make Cloudflare Pages return a genuine 404 for
  unknown routes. The response status must be verified after deployment.
- `llms.txt` is a small navigation aid, not a ranking factor or crawler policy.
- The paper PDF carries verified title, author, subject, keywords, and language
  metadata. It remains untagged; see the accessibility audit.

After an authorized deployment, run the read-only production verifier:

```sh
python3 scripts/verify_production.py https://kexingyan.com/
```

Do not run it as a substitute for the Cloudflare and Search Console manual
checklists, and do not interpret an ordinary 403/429 response as proof of a
specific crawler policy.

## Maintenance workflows

### Frozen research PDF

The accepted research PDF is byte-frozen. Do not optimize, rewrite, linearize,
retag, or regenerate it during ordinary site work. After any intentional paper
replacement, review its metadata and accessibility, update the recorded hash,
dates and sitemap only when supported, then rebuild and validate `dist`.

### Dates

For a meaningful content revision, update the visible `<time>`, page JSON-LD,
`sitemap.xml`, and the matching record in `scripts/site_dates.json`. Do not
advance dates for deployment-only, whitespace, or CSS changes.

### New public routes and assets

1. Add the source file using its final canonical route.
2. Add only required files to `PUBLIC_FILES` in `scripts/build_site.py`.
3. Add unique metadata, structured data, internal links, and sitemap entry.
4. If the resource belongs in `llms.txt`, add only its canonical public URL.
5. For images, use descriptive names, verified alt text where visible, intrinsic
   dimensions, and intentional Open Graph fields where applicable.
6. Run the build, source validator, artifact validator, and tests.

Open Graph changes must retain absolute HTTPS URLs, 1200×630 declared and actual
dimensions, preview alt text, and Twitter-image alignment. The validator checks
these fields automatically.

## Canonical entity

- Primary name: **Kexing Yan**
- Chinese alternate name: **严可行**
- Website: `https://kexingyan.com/`
- Person ID: `https://kexingyan.com/#person`
- Website ID: `https://kexingyan.com/#website`

See:

- [`docs/ai-discoverability-audit.md`](docs/ai-discoverability-audit.md)
- [`docs/phase-0-5-acceptance-review.md`](docs/phase-0-5-acceptance-review.md)
- [`docs/crawler-policy.md`](docs/crawler-policy.md)
- [`docs/site-knowledge-graph.md`](docs/site-knowledge-graph.md)
- [`docs/validation-report.md`](docs/validation-report.md)
- [`docs/media-audit.md`](docs/media-audit.md)
- [`docs/pdf-accessibility-audit.md`](docs/pdf-accessibility-audit.md)
- [`docs/freshness-policy.md`](docs/freshness-policy.md)
- [`docs/metadata-audit.md`](docs/metadata-audit.md)
- [`docs/llms-txt-decision.md`](docs/llms-txt-decision.md)
- [`docs/deployment-readiness.md`](docs/deployment-readiness.md)
- [`docs/deployment-manifest.md`](docs/deployment-manifest.md)
- [`docs/cloudflare-manual-checklist.md`](docs/cloudflare-manual-checklist.md)
- [`docs/search-console-post-deployment.md`](docs/search-console-post-deployment.md)
- [`docs/final-predeployment-review.md`](docs/final-predeployment-review.md)
- [`docs/release-candidate-report.md`](docs/release-candidate-report.md)
