# PDF Quality and Accessibility Audit

**Audited file:** `papers/the-quantity-and-size-of-microloans.pdf`
**Audit date:** 2026-07-31
**Decision:** Safe descriptive metadata improvement; no structural rewrite

## Integrity and document inventory

| Check | Result |
|---|---|
| Integrity | Opens with strict `pypdf`; final EOF marker present; all pages render |
| Encryption / forms / JavaScript | None |
| Page count and size | 30 A4 pages |
| PDF version | 1.5, preserved after metadata update |
| File size | 505,050 → 510,338 bytes (+1.0%) |
| Fast Web View | No; unchanged |
| Creation date | 2026-07-09 21:49:17 CST, preserved |
| Metadata modification date | 2026-07-31 14:49:08 CST; technical metadata change, not a research revision |
| Fonts | Embedded and Unicode-mapped; Type 1C and Type 3 subsets |
| Selectable text | Present on all 30 pages; extraction produced text on every page |
| Bookmarks | 11 top-level entries and 21 total outline entries; preserved |
| Link annotations | 103 internal citation/section links across 19 pages; preserved |
| Image-only pages | None |
| Document language | Added `en-CA` |
| Tagged PDF | No `/StructTreeRoot`; not a tagged PDF |

## Verified metadata change

The following values were added without altering manuscript content:

- Title: *The Quantity and Size of Microloans Follow Different Development
  Logics: Evidence from Kiva*
- Author: Kexing Yan
- Subject: Student working paper examining microloan quantity and size across
  countries using Kiva data.
- Keywords: microfinance; microloans; Kiva; economic development; loan size;
  loan quantity; cross-country analysis; World Development Indicators
- Document language: `en-CA`

No DOI, journal, publisher, approval, grant, or peer-review claim was added.

The original SHA-256 was
`3c7444fa4582dcdd4b4dd232cddaeb5abe8cbf8ccf3868141f659326f09e4c9b`.
The metadata-improved SHA-256 is
`fd8d7d2e5c885dc37ee5ab9f31a3f28fe47b833d5555edaddd5dc30888179219`.

## Safety validation

The update used an incremental PDF write. Before replacement:

- all 30 pages were rendered before and after at the same resolution;
- every rendered page was pixel-identical;
- `pdftotext -layout` output was byte-identical;
- per-page extracted text was identical;
- page count, PDF 1.5 header, outline titles, and all 103 annotation targets
  were identical; and
- no form or script was introduced.

## Source-of-truth search

No LaTeX, bibliography, Quarto, Markdown manuscript, notebook, Typst, Word, R
Markdown, or PDF build script exists in the current website repository or its
tracked baseline. The PDF identifies LaTeX with `hyperref` as its creator, but
the source is not present here. Structural remediation was therefore not
attempted.

## Accessibility limitations

- The PDF has no semantic tag tree, programmatic heading hierarchy, table
  headers, figure alternative text, or guaranteed reading order.
- Extracted prose order is generally coherent, but this is not proof of
  assistive-technology reading order.
- Tables are visually labelled but lack tagged header relationships.
- Figures and the page-10 maps lack programmatic alternative text.
- Bookmarks improve navigation but do not substitute for tagging.
- Full PDF/UA compliance is not claimed.

The canonical HTML research page remains the primary accessible summary and
metadata representation. It conveys the research question, data, methodology,
qualified findings, limitations, status, and citations, but it is not a
line-by-line accessible replacement for all equations, tables, and appendices.

## Recommended source-level remediation

Obtain the original LaTeX project, then use a modern tagged-PDF workflow capable
of semantic headings, table structure, link text, and figure alternatives.
Re-export, visually compare all pages, test keyboard and screen-reader reading
order, and run an appropriate PDF accessibility checker. Do not retrofit tags
blindly into this compiled file.

## Delivery headers

`_headers` keeps the PDF indexable and inline, declares `application/pdf`,
`Content-Language: en-CA`, `nosniff`, and a one-hour revalidating public cache.
It does not force download or add `noindex`. These headers remain subject to
post-deployment Cloudflare verification.
