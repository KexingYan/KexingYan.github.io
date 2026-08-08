# AI Discoverability Audit

**Site:** <https://kexingyan.com/>
**Canonical person:** Kexing Yan (严可行)
**Baseline commit:** `6202ce10b18cf6fe9aa88d39ca177c0ab76ec17a`
**Audit date:** 2026-07-31
**Scope:** Phase 0 baseline, before implementation

## Executive baseline

The site is a small, hand-authored static website deployed from the `main`
branch to Cloudflare Pages. It has no framework, package manager, build step,
test suite, or generated content model. The production source is one
`index.html` file with inline CSS and JavaScript, plus public PDFs, icons,
`robots.txt`, `sitemap.xml`, a web manifest, and Cloudflare Pages `_headers`.

The current visual site is compact and readable. Its strongest machine-facing
features are a canonical homepage URL, useful visible identity text, a single
JSON-LD graph with stable Person and WebSite IDs, Open Graph metadata, an XML
sitemap, and readable default English content in the original HTML.

The highest-risk production issue is soft-404 behaviour: `/about`, `/research`,
`/projects`, `/llms.txt`, and a deliberately nonexistent audit path all return
HTTP 200 with the homepage. This creates duplicate crawlable URLs even though
the pages do not exist. The other major discoverability gap is that the only
research work has no dedicated HTML page and is discoverable only through a
homepage card and a PDF.

No source changes had been made when this baseline was recorded.

## Technology and operations

| Area | Baseline |
|---|---|
| Framework | None; hand-authored HTML5 |
| Framework version | Not applicable |
| Build system | None |
| Build command | None; repository contents are deployment artifacts |
| Test command | None |
| Deployment | Pushes to `main` trigger Cloudflare Pages |
| Production domain | `https://kexingyan.com/` |
| Canonical host | Apex domain; `www` redirects to apex |
| Default content language | English (`en-CA`) |
| Alternate visible language | Simplified Chinese (`zh-Hans`) via client-side text replacement |
| Analytics | Cloudflare Web Analytics beacon observed in production; not present in source |
| JavaScript dependence | Low for English content; high for Chinese translation and active navigation state |

## Route inventory

### Repository-backed public resources

| Route | Source | Intended status | Notes |
|---|---|---:|---|
| `/` | `index.html` | 200 | Single-page profile |
| `/robots.txt` | `robots.txt` | 200 | Blanket allow plus sitemap reference |
| `/sitemap.xml` | `sitemap.xml` | 200 | Homepage and paper PDF only |
| `/site.webmanifest` | `site.webmanifest` | 200 | App name and icons |
| `/baidu_verify_codeva-vWXLKxDtXl.html` | verification file | 200 | Baidu ownership verification |
| `/papers/the-quantity-and-size-of-microloans.pdf` | paper PDF | 200 | Thirty-page public paper |
| `/assets/resume/Kexing-Yan-Resume-EN.pdf` | résumé PDF | 200, `noindex` header | Intentionally public but excluded from indexing |
| `/assets/resume/Kexing-Yan-Resume-ZH.pdf` | résumé PDF | 200, `noindex` header | Intentionally public but excluded from indexing |
| `/assets/icons/*` | PNG icons | 200 | Favicons and application icons |
| `/assets/images/kexing-yan-open-graph.png` | PNG | 200 | 1200 × 630 social preview |

### Production route probes

The following production probes were made on 2026-07-31:

| Requested path | HTTP status | Content type | Result |
|---|---:|---|---|
| `/` | 200 | `text/html` | Homepage |
| `/about` | 200 | `text/html` | Homepage fallback; no About route |
| `/research` | 200 | `text/html` | Homepage fallback; no Research route |
| `/projects` | 200 | `text/html` | Homepage fallback; no Projects route |
| `/llms.txt` | 200 | `text/html` | Homepage fallback; no text file |
| `/nonexistent-audit-path` | 200 | `text/html` | Homepage fallback; soft 404 |
| `/robots.txt` | 200 | `text/plain` | Correct static file |
| `/sitemap.xml` | 200 | `application/xml` | Correct static file |

## Content inventory

### Biography and identity

Verified visible repository content identifies:

- Kexing Yan as the canonical English name.
- 严可行 as the Chinese alternate name.
- University of Toronto, St. George Campus as the affiliation.
- An Honours BSc path with Economics and Statistics double majors.
- Data Analytics, Econometrics, and Applied Research as focus areas.
- Toronto, Ontario, Canada as the visible location.
- Class of 2028.
- Availability for Summer 2027 internships.

These facts already appear in visible homepage copy. This audit does not
independently verify them outside the repository and does not introduce new
claims.

### Research

One public research work is present:

- **The Quantity and Size of Microloans Follow Different Development Logics:
  Evidence from Kiva**
- Visible date: July 2026
- Public PDF:
  `/papers/the-quantity-and-size-of-microloans.pdf`
- Public code repository:
  `https://github.com/KexingYan/kiva-microfinance-development`

The homepage provides two summary paragraphs, methods/tags, and links. There is
no dedicated publication HTML page. The PDF has no Title, Author, or Subject
metadata in the inspected file metadata.

### Projects

No dedicated project page or project collection exists in this repository.
The homepage references the Kiva research code repository, but it does not
contain verified content sufficient to create unrelated project pages during
the first implementation stage.

### Honours and activities

The homepage visibly lists:

- Participant, Online Economics and Finance Seminars — CFA Institute,
  2024–present.
- University of Toronto Entrance Scholarship.

These must not be expanded beyond the wording already present without
additional verified source material.

### Social identity and contact

Visible first-party links:

- GitHub: `https://github.com/KexingYan`
- LinkedIn: `https://linkedin.com/in/kexing-yan`
- Two intentionally public email links
- English and Chinese résumé PDFs

The résumé directory is covered by `X-Robots-Tag: noindex` in `_headers`.

## Existing search implementation

### Metadata

The homepage has a unique title, description, author, robots meta, canonical
URL, theme colour, Open Graph fields, Twitter card fields, icons, manifest, and
Baidu verification metadata. As there is only one genuine HTML route, no
cross-route uniqueness comparison is currently possible.

### Structured data

`index.html` contains one JSON-LD `@graph` with:

- `WebSite` at `https://kexingyan.com/#website`
- `ProfilePage` at `https://kexingyan.com/#profile`
- `Person` at `https://kexingyan.com/#person`
- University of Toronto affiliation
- `knowsAbout`
- GitHub and LinkedIn `sameAs`

The graph is a sound starting point and avoids multiple conflicting Person
objects. It is currently authored directly inside `index.html`, so it is not a
reusable source for future pages.

### Canonicals

The homepage canonical is correct. Production fallback URLs return the
homepage canonical, but they still respond with HTTP 200. Canonical markup is
not a replacement for correct 404 status behaviour.

### Sitemap

The sitemap is syntactically valid XML and contains the homepage plus the paper
PDF. It has no `lastmod` values and no publication HTML page.

### Robots and crawler permissions

`robots.txt` currently allows every conforming crawler:

```text
User-agent: *
Allow: /
```

It does not distinguish ordinary search, search/citation retrieval, training,
or user-triggered fetch agents. Cloudflare bot-management and WAF settings are
not represented in the repository and require a manual dashboard check.

### Redirects and status handling

- Production `www.kexingyan.com` returns a 301 to the apex homepage.
- No repository `_redirects` file exists.
- Unknown paths receive a 200 homepage fallback in production.
- No dedicated `404.html` exists.
- There is no documented trailing-slash policy beyond the homepage canonical.

## Rendering and accessibility baseline

The canonical English biography, research summary, honours, links, and contact
information are present directly in `index.html`. They do not require
JavaScript, tabs, modals, hover, canvas, or infinite scrolling.

The Chinese version is applied by JavaScript from an inline translation
dictionary and has no dedicated URL. A saved Chinese preference can hide
translatable nodes until the script applies translations. If that script
fails, a `finally` block is intended to reveal the content.

Positive accessibility features include semantic landmarks, a navigation
label, one H1, ordered H2/H3 headings, native links and buttons, definition-list
profile data, and language-state updates.

Current concerns include no skip link, no explicit `:focus-visible` treatment,
no reduced-motion override for smooth scrolling, a horizontally scrolling
mobile navigation list, and client-only alternate-language content. There are
no content `<img>` elements, so missing image alt attributes are not currently
an issue.

## Findings

Difficulty uses **Low**, **Medium**, or **High**. “Safe to automate” means the
repository change can be made without inventing facts or altering an external
dashboard.

| Severity | Affected file or route | Finding | Why it matters / audience | Recommended fix | Difficulty | Safe to automate |
|---|---|---|---|---|---|---|
| Critical | Production unknown routes | Unknown paths return HTTP 200 with the homepage (soft 404). | Search engines and AI systems may crawl duplicate URLs; humans receive no clear not-found state. Affects all three. | Add a static `404.html`; verify Cloudflare Pages 404 behaviour and remove any dashboard-level SPA fallback if configured. | Medium | Partly; dashboard check is manual |
| High | Research card and paper PDF | The research work has no dedicated HTML page. | A PDF-only detail source is harder to parse, navigate, cite, and connect to the Person entity. Affects all three. | Create one verified, canonical publication HTML page using only repository facts; link it from the homepage and sitemap. | Medium | Yes |
| High | No validation tooling | There is no build, test, link, metadata, JSON-LD, sitemap, or accessibility validation command. | Regressions can reach production unnoticed. Affects all three. | Add a dependency-free validation script and document the command. | Medium | Yes |
| High | `robots.txt` and Cloudflare dashboard | The repository allows all bots and does not document search/citation versus training intent; Cloudflare may override origin availability. | Search and citation agents can be accidentally blocked or training crawlers unintentionally allowed. Primarily affects search and AI systems. | Define an explicit policy, preserve search access, make the training choice explicit, and document required Cloudflare checks. | Low | Repository policy yes; dashboard no |
| Medium | `/about`, `/research`, `/projects` | These paths appear to exist because they return the homepage, but no such repository pages exist. | Misleading crawl and navigation signals; duplicate titles/descriptions/canonicals. Affects all three. | Do not advertise empty routes. Create only pages supported by verified content; otherwise ensure they 404. | Medium | Yes |
| Medium | `index.html` bilingual system | Chinese is produced only by client-side replacement at the same URL. | Crawlers usually receive English only; language-specific sharing, metadata, canonicalization, and `hreflang` are unavailable. Affects Chinese humans and machine systems. | Preserve the current toggle in Phase 1–5; document a future option for a separate `/zh/` route rather than adding duplicate partial pages now. | High | No, requires product decision |
| Medium | `index.html` JSON-LD | Structured data is embedded directly in the homepage and cannot be reused safely by future pages. | New pages may drift into conflicting Person entities. Primarily affects search and AI systems. | Establish documented canonical IDs and a small maintainable data/validation convention before adding detail pages. | Medium | Yes |
| Medium | `sitemap.xml` | Sitemap contains the homepage and PDF only and has no accurate `lastmod`. | Discovery and refresh signals are limited. Primarily affects search and AI systems. | Add canonical HTML detail pages when created; use meaningful file-backed modification dates only. | Low | Yes |
| Medium | Paper PDF metadata | The paper PDF lacks Title, Author, and Subject metadata. | PDF search results and document understanding have weaker identity signals. Affects search and AI systems. | Align PDF metadata with the future publication HTML page without changing paper content. | Medium | Yes, after citation fields are verified |
| Medium | `index.html` navigation | All primary navigation targets are same-page fragments. | The homepage carries every topic and provides few durable deep URLs for citation. Affects all three. | In Phase 1–5, keep the visual flow but create an authoritative About page only if existing verified content is sufficient; reserve research detail work for the next approved stage. | Medium | Yes |
| Medium | `index.html` | No visible last-reviewed or last-updated information exists. | Readers and retrieval systems cannot easily assess freshness. Affects all three. | Add dates only to content where a meaningful verified date exists; do not stamp every build. | Low | Yes |
| Medium | `_headers` and Cloudflare | Security headers are limited to `X-Robots-Tag` for résumés; no source-controlled CSP, permissions policy, or frame policy is present. | Human trust and browser security could be stronger, but strict policies can break inline scripts. Primarily affects humans. | Document as a later hardening item; do not add a strict CSP during Phase 0–5 without refactoring inline code and testing. | High | No |
| Medium | Homepage accessibility | No skip link, explicit keyboard focus treatment, or reduced-motion support. | Keyboard and motion-sensitive users receive a weaker experience. Affects humans and user-driven agents. | Add a skip link, `:focus-visible`, and `prefers-reduced-motion` handling without changing visual identity. | Low | Yes |
| Medium | Homepage H1 | The H1 describes the field but does not contain the canonical name. | The first heading alone does not identify the page subject, although the following summary does. Affects humans, search, and AI systems. | Make the opening heading identify “Kexing Yan (严可行)” naturally while preserving the concise factual summary. | Low | Yes |
| Low | `index.html` inline CSS/JS | All CSS and JavaScript are embedded in one 36 KB HTML file. | Maintainability is limited, but render performance is currently acceptable and there is no blocking stylesheet request. Primarily affects maintainers. | Avoid an architectural rewrite in Phase 1–5; extract only if reuse across verified detail pages justifies it. | Medium | Yes |
| Low | Mobile navigation | The navigation becomes two stacked rows and uses horizontal overflow for links. | It may be awkward at narrow widths. Affects humans. | Test at mobile widths and improve wrapping/focus visibility if needed. | Low | Yes |
| Low | Social preview | One 648 KB PNG is used for social sharing. | It is valid and correctly sized but could be compressed. Affects performance for preview fetchers. | Losslessly or carefully compress only if visual comparison confirms no material degradation. | Low | Yes |
| Informational | `index.html` | Canonical identity, Open Graph fields, visible copy, and JSON-LD already use “Kexing Yan” with “严可行” as the alternate name. | This is a strong entity-consistency baseline. Affects all three positively. | Preserve exact naming and stable IDs. | Low | Yes |
| Informational | `_headers` | Résumé PDFs are intentionally `noindex`. | Prevents search indexing of résumé files while leaving deliberate public links functional. | Preserve unless the owner makes a different privacy decision. | Low | Yes |
| Informational | Production host | `www` redirects to the apex domain with HTTP 301. | Host consolidation is correct. Affects search and AI systems positively. | Preserve and verify path-level redirects manually in Cloudflare. | Low | No |
| Informational | Images | No content images are used; icon and Open Graph assets have descriptive purposes and dimensions available in metadata. | There are no missing content-image alt attributes to repair. | Add visible context and alt text only when future content images are introduced. | Low | Yes |

## Broken, weak, and orphaned links

- Internal fragment links resolve to visible homepage sections.
- The paper PDF and Kiva code repository are linked from the research card.
- The PDF has no HTML parent/detail route, making it effectively an
  indexable document without a canonical publication landing page.
- There are no repository-backed orphan HTML pages because only one HTML page
  exists.
- External links must be checked in automated validation without treating
  transient third-party failures as build failures.

## Risks and regressions to avoid

1. Do not remove the existing bilingual toggle or canonical English fallback.
2. Do not rewrite the visual system merely to introduce multiple routes.
3. Do not expose résumé contents or change their `noindex` policy.
4. Do not expand scholarship, seminar, research, degree, date, or location
   claims beyond existing verified wording.
5. Do not create empty Research, Projects, Media, Contact, or Updates pages.
6. Do not create separate Chinese URLs without a complete language-routing and
   canonical strategy.
7. Do not add a strict Content Security Policy while the site relies on inline
   scripts and styles.
8. Do not use build-generated timestamps as content modification dates.
9. Do not submit URLs or modify Cloudflare, Google, Bing, or other dashboards
   from repository work.
10. Preserve the existing apex canonical and `www` redirect.

## Phase 0 validation record

- Repository clean at baseline: yes.
- Production homepage rendered and inspected in a browser: yes.
- Key content present in readable DOM: yes.
- Production route and status probes: completed.
- Sitemap XML syntax: valid via `xmllint --noout sitemap.xml`.
- PDF metadata: inspected with `pdfinfo`.
- Build: not applicable; no build system exists.
- Tests: not available.
- HTML validator: the installed `tidy` build is too old to recognise HTML5
  landmarks and is not a reliable pass/fail validator for this project.
- JSON-LD: browser inspection confirmed one parseable JSON-LD graph; a
  maintainable repository validation command is still required.

## Recommended implementation order after audit

1. Fix soft-404 handling and add a useful static 404 page.
2. Add dependency-free repository validation.
3. Improve accessibility and homepage entity clarity without redesigning.
4. Document and implement a deliberate crawler policy.
5. Stabilize the canonical knowledge-graph conventions and IDs.
6. Add only the authoritative About route supported by existing verified copy.
7. After design review, add the dedicated publication HTML page and subsequent
   Phase 6+ work.
