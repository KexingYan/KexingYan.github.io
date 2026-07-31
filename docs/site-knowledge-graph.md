# Site Knowledge Graph

**Scope:** Implemented canonical routes and entities through Phase 10
**Canonical domain:** `https://kexingyan.com`

## Core entities

| Entity | Stable `@id` | Type | Source of truth |
|---|---|---|---|
| Kexing Yan | `https://kexingyan.com/#person` | `Person` | Visible homepage biography and homepage JSON-LD |
| Official website | `https://kexingyan.com/#website` | `WebSite` | Homepage metadata and JSON-LD |
| Official profile | `https://kexingyan.com/#profile` | `ProfilePage` | `index.html` |
| University of Toronto | `https://kexingyan.com/#university-of-toronto` | `CollegeOrUniversity` | Visible affiliation and official university URL |
| Microloan student paper | `https://kexingyan.com/research/microloan-quantity-size/#article` | `ScholarlyArticle` | HTML research page and linked PDF |

## Canonical identity rules

- Use **Kexing Yan** as the primary English name and **严可行** as the Chinese
  alternate name.
- Every authored page references `https://kexingyan.com/#person`; it does not
  redefine a second Person object.
- Current University of Toronto status is represented as `affiliation`, not
  `alumniOf`.
- Do not add job titles, credentials, awards, memberships, publication venues,
  DOIs, peer-review claims, or educational history to schema unless matching
  visible and verified content supports them.

## Implemented relationships

```text
WebSite #website
└── publisher ──────────────> Person #person

ProfilePage #profile
├── isPartOf ───────────────> WebSite #website
└── mainEntity ─────────────> Person #person

Person #person
├── mainEntityOfPage ───────> ProfilePage #profile
├── affiliation ────────────> CollegeOrUniversity #university-of-toronto
└── sameAs ─────────────────> GitHub and LinkedIn

WebPage /research/.../#webpage
├── isPartOf ───────────────> WebSite #website
├── mainEntity ─────────────> ScholarlyArticle #article
└── breadcrumb ─────────────> BreadcrumbList #breadcrumb

ScholarlyArticle #article
├── author ─────────────────> Person #person
└── encoding ───────────────> Public PDF
```

The student paper is typed as `ScholarlyArticle` because it is a complete
academic manuscript. Its visible status and `creativeWorkStatus` both say
“Student working paper”; no journal, publisher, DOI, issue, volume, acceptance
date, or peer-review status is asserted.

## Canonical route and link inventory

| Canonical route | Purpose | Primary entity | Related entities | Structured-data type | Incoming internal links | Outgoing internal links | Source of truth |
|---|---|---|---|---|---|---|---|
| `/` | Official bilingual-capable profile and site navigation | Kexing Yan | Website, University of Toronto, student paper | `WebSite`, `ProfilePage`, `Person`, `CollegeOrUniversity` | Brand/home links and research breadcrumb | About, skills, research, experience, contact fragments; research page; PDF; résumés; GitHub; LinkedIn | `index.html` |
| `/research/microloan-quantity-size/` | Citation landing page and readable research summary | Microloan student paper | Kexing Yan, Website, PDF | `WebPage`, `ScholarlyArticle`, `BreadcrumbList` | Homepage research card and footer | Homepage sections, PDF, public code repository, World Development Indicators | `research/microloan-quantity-size/index.html` |
| `/papers/the-quantity-and-size-of-microloans.pdf` | Full student manuscript | Microloan student paper | Kexing Yan, HTML research page | PDF encoding referenced by `MediaObject` | Homepage and HTML research page | PDF-internal references only | `papers/the-quantity-and-size-of-microloans.pdf` |

`404.html`, résumé PDFs, repository documentation, and validation source are
not canonical indexable routes. The 404 page links to the homepage and research
section but is excluded from the sitemap and has `noindex`.

The noncanonical `/papers` and `/papers/` forms are exact 301 shortcuts to the
HTML research page because `/papers` is printed in the public English résumé.
They are declared in `_redirects` and excluded from the sitemap.

## Intentional deferrals

- No generic `/research/` index: with one paper, the homepage research section
  already supplies meaningful collection context.
- No `/projects/market-radar/`: Market Radar is not evidenced in the current
  repository or its intentional public links. See
  `docs/project-page-content-gaps.md`.
- No `/about/`: the verified biography, education, interests, links, and CV
  access already live on the homepage; a separate route would currently be
  duplicative.
- No `/media/`: there is no verified reusable portrait, pronunciation guide,
  approved biography package, or reuse licence.

## Language model

The canonical homepage document is English (`en-CA`). Its client-side language
control can replace visible text with Simplified Chinese and updates
`html[lang]` to `zh-Hans`, but it does not create a second crawlable URL.
Metadata remains English. With JavaScript disabled, visitors receive the
complete English version. No `hreflang` is emitted because stable
language-specific URLs do not exist.

## Maintenance map

| Content | Source |
|---|---|
| Canonical biography and Chinese translation | `index.html` |
| Homepage entity graph | JSON-LD in `index.html` |
| Research summary, status, citations, and article graph | `research/microloan-quantity-size/index.html` |
| Research presentation | `assets/css/research.css` |
| Full research manuscript | `papers/the-quantity-and-size-of-microloans.pdf` |
| Crawler intent | `robots.txt` and `docs/crawler-policy.md` |
| Discoverable canonical URLs | `sitemap.xml` |
| Legacy path mapping | `_redirects` |
| Indexing response headers | `_headers` |
| Public date governance | `scripts/site_dates.json` plus validator |
| Optional retrieval navigation | `llms.txt` |
| Local invariant checks | `scripts/validate_site.py` and `scripts/test_validate_site.py` |

For a factual change, update visible content first, then matching metadata,
JSON-LD, sitemap dates where meaningful, internal links, and documentation.
