# Freshness and Date Governance

**Effective date:** 2026-07-31
**Machine-checked source:** `scripts/site_dates.json`

## Rules

1. `datePublished` is used only when the initial public publication date is
   known. It is omitted from the current pages because the undeployed repository
   cannot establish a live publication date.
2. `dateModified` represents a meaningful page-content or metadata revision,
   not a deployment, formatting-only edit, analytics change, or build time.
   The homepage ProfilePage uses a full, timezone-aware DateTime from the
   accepted content commit; visible dates and sitemap dates remain date-only.
3. Sitemap `lastmod` is manually governed and validated against this file; it is
   never generated from filesystem timestamps.
4. The manuscript date is represented as `dateCreated` and visibly labelled
   “Completed.” It is not treated as the website publication date.
5. PDF metadata modification is a technical file change, not a new paper
   revision.
6. Copyright year is independent of content freshness.
7. A reliable date may be omitted. Dates must not be guessed to fill a field.

## Date inventory

| Surface | Value | Meaning | Verification / maintenance |
|---|---:|---|---|
| Homepage visible update | 2026-07-31 | Meaningful profile, metadata, accessibility, and link revisions | Manual source plus validator |
| Homepage `ProfilePage.dateModified` | 2026-07-31T16:32:46+08:00 | Same homepage revision; timestamp from accepted content commit `a38c23d` | Validator-enforced |
| Homepage sitemap `lastmod` | 2026-07-31 | Same meaningful revision | Validator-enforced |
| Research visible page update | 2026-07-31 | Canonical HTML page and metadata review | Manual source plus validator |
| Research `WebPage.dateModified` | 2026-07-31 | Same HTML-page revision | Validator-enforced |
| Research sitemap `lastmod` | 2026-07-31 | Same HTML-page revision | Validator-enforced |
| Manuscript visible completion | 2026-07-09 | Date on visible paper title page | Verified PDF evidence |
| `ScholarlyArticle.dateCreated` | 2026-07-09 | Manuscript completion, not website publication | Validator-enforced |
| Citation and Dublin Core date | 2026-07-09 | Date used to cite the working paper | Validator-enforced |
| PDF CreationDate | 2026-07-09 | Original generated file metadata | Preserved |
| PDF ModDate | 2026-07-31 | Metadata/language update only | Recorded in PDF audit |
| PDF sitemap `lastmod` | 2026-07-31 | File bytes and discoverable metadata changed | Validator-enforced |
| Footer copyright | 2026 | Copyright notice only | Validator-enforced, not a freshness signal |
| Documentation dates | 2026-07-31 | Review/audit date | Manually maintained; not in sitemap |

## Maintenance process

For a meaningful update:

1. Edit the visible page and matching metadata.
2. Update only that route in `scripts/site_dates.json` and explain the reason.
3. Update the visible `<time>` and sitemap `lastmod` to the governed date. For
   the homepage, record the matching full ProfilePage DateTime separately as
   `structuredDataDateModified`; its calendar date must agree with the visible
   and sitemap date.
4. For a paper revision, verify the new title-page/revision date before changing
   `dateCreated`, citation fields, or PDF dates.
5. Run `python3 scripts/validate_site.py`.

For CSS, whitespace, image compression without changed meaning, documentation,
or deployment-only changes, do not advance public page dates. The central JSON
does not drive a runtime CMS; it is a small governance record whose duplicated
HTML/XML values are checked during validation.
