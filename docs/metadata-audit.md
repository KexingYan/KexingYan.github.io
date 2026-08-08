# Metadata Audit

**Audit date:** 2026-07-31
**Scope:** Every public HTML route through Phase 15

## Route inventory

| Field | Homepage `/` | Research `/research/microloan-quantity-size/` | `404.html` |
|---|---|---|---|
| Title | `Kexing Yan (严可行) \| Economics & Statistics` | `Microloan Quantity and Size Research \| Kexing Yan` | `Page not found \| Kexing Yan` |
| Description | Factual student profile | Factual student-working-paper summary | Clear not-found explanation |
| Canonical | `https://kexingyan.com/` | Canonical research URL | None, intentionally |
| Robots | `index, follow` | `index, follow` | `noindex, follow` |
| Language | `en-CA`; client-side `zh-Hans` presentation at same URL | `en-CA` | `en-CA`, with marked Chinese paragraph |
| H1 | `Kexing Yan (严可行)` | Verified full paper title | `This page does not exist.` |
| OG type | `website` | `article` | None, intentionally |
| OG title/description/URL | Unique and canonical | Unique and canonical | None required |
| OG image | Shared 1200×630 identity preview | Intentional shared identity preview | None |
| OG image details | HTTPS secure URL, dimensions, alt | HTTPS secure URL, dimensions, alt | Not applicable |
| Twitter card | `summary_large_image`, title, description, image, alt | Same complete field set | None |
| Author metadata | Kexing Yan | Kexing Yan | None |
| Date metadata | `ProfilePage.dateModified` 2026-07-31 | `WebPage.dateModified` 2026-07-31; work `dateCreated` 2026-07-09 | None |
| Primary schema | WebSite, ProfilePage, Person, CollegeOrUniversity | WebPage, ScholarlyArticle, BreadcrumbList | None |
| Sitemap | Included | Included | Excluded |
| Indexability | Indexable | Indexable | Not indexable |

## Corrections completed

- Added `og:image:secure_url` on both indexable pages.
- Added research-page image dimensions and Open Graph/Twitter alt text.
- Kept image URLs absolute and aligned Twitter preview with Open Graph.
- Removed research `article:published_time` and work `datePublished`; the known
  2026-07-09 manuscript date is now `dateCreated`, not a guessed public date.
- Preserved a unique title, description, canonical URL, author, status, citation
  fields, and non-journal `ScholarlyArticle` interpretation.
- Kept the 404 page free of canonical, social, ProfilePage, and article schema.

## Validation coverage

The dependency-free validator now checks duplicate titles/descriptions,
canonical/OG URL agreement, absolute HTTPS preview URLs, secure URL agreement,
preview file existence, actual PNG dimensions, image alt text, Twitter fields,
JSON-LD conflicts, citation/date consistency, sitemap/indexability agreement,
and the centralized date source. Mutation tests cover missing alt text, wrong
image dimensions, stale dates, and broken `llms.txt` references.

## Language limitation

The homepage's canonical metadata and initial HTML remain English. The Chinese
presentation replaces visible text client-side and updates `html[lang]`; there
is no independent Chinese canonical URL or Chinese metadata document. No
`hreflang` is emitted. This is accurate but limits language-specific discovery.
