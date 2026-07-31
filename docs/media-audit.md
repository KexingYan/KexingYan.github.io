# Media Audit

**Audit date:** 2026-07-31
**Scope:** Public image and media assets referenced through Phase 15

## Findings

The site has no public portrait or content `<img>` element. Its visual identity
uses browser icons, a text-based social preview, and CSS-only decorative shapes.
No stock image, university logo, fabricated portrait, local absolute image path,
or image-only presentation of a unique factual claim is present.

All PNG optimization in this phase was lossless. Pixel comparison returned no
difference before and after compression.

| Asset | Dimensions / format | Before → after | Public use | Visible purpose and accessibility | OG / schema | Ownership or licence | Remaining opportunity |
|---|---:|---:|---|---|---|---|---|
| `assets/images/kexing-yan-open-graph.png` | 1200×630 PNG, RGB | 648,094 → 477,432 B | Homepage and research-page social metadata | Text-based identity card. Both pages supply an accurate metadata alt description. The same name, affiliation, and academic areas also exist as HTML text. Not loaded as visible page content. | `og:image` and Twitter image; no unnecessary `ImageObject` | Repository-provided asset; copyright/reuse licence not documented | Keep PNG for broad preview compatibility; reconsider only if a future verified portrait or paper-specific source asset exists |
| `assets/icons/favicon-16x16.png` | 16×16 PNG, RGBA | 543 → 432 B | Homepage favicon | Browser decoration; HTML alt/caption not applicable | None | Repository-provided; licence not documented | None |
| `assets/icons/favicon-32x32.png` | 32×32 PNG, RGBA | 1,214 → 1,077 B | Homepage, research page, 404 page | Browser decoration; HTML alt/caption not applicable | None | Repository-provided; licence not documented | None |
| `assets/icons/favicon-48x48.png` | 48×48 PNG, RGBA | 2,123 → 1,878 B | Homepage favicon | Browser decoration | None | Repository-provided; licence not documented | None |
| `assets/icons/apple-touch-icon.png` | 180×180 PNG, RGBA | 18,277 → 15,017 B | Homepage and research page | Operating-system shortcut icon | None | Repository-provided; licence not documented | Add to 404 only if app-install consistency becomes necessary; not required for error recovery |
| `assets/icons/favicon-192x192.png` | 192×192 PNG, RGBA | 20,562 → 16,905 B | `site.webmanifest` | Install icon; declared intrinsic size in manifest | None | Repository-provided; licence not documented | None |
| `assets/icons/favicon-512x512.png` | 512×512 PNG, RGBA | 135,943 → 110,659 B | `site.webmanifest` | Install icon; declared intrinsic size in manifest | None | Repository-provided; licence not documented | None |
| `assets/icons/kx-logo.png` | 1024×1024 PNG, RGBA | 1,444,418 → 1,325,956 B | No longer referenced | Legacy high-resolution mark. The unsized favicon reference was removed because browsers could download 1.4 MB unnecessarily. | None | Repository-provided; licence not documented | Retain for now; remove only after owner confirms it is not an intentional source asset |

## Open Graph system

- Homepage and research page intentionally share the established 1200×630
  identity preview. Copying the same bitmap under a research filename would add
  no meaning and would create a duplicate asset.
- Research-specific context is supplied through its unique title, description,
  URL, type, and visible paper status. The preview does not claim to depict the
  paper or the author.
- Both indexable pages now define `og:image`, `og:image:secure_url`, dimensions,
  `og:image:alt`, Twitter image, and Twitter image alt using absolute HTTPS URLs.
- The 404 page intentionally has no social preview and remains `noindex`.
- No Twitter/X account handle is emitted.

## Referenced document media

PDF document media are not image assets, but they are linked from public pages
and were included in the inventory boundary:

| Asset | Format / size | Public use | Accessibility and indexing | Phase 11–15 action |
|---|---:|---|---|---|
| `papers/the-quantity-and-size-of-microloans.pdf` | 30-page PDF, 510,338 B | Research page and sitemap | Selectable text, bookmarks, and links; untagged. Intentionally indexable. See `docs/pdf-accessibility-audit.md`. | Verified metadata and language added with pixel-identical rendering |
| `assets/resume/Kexing-Yan-Resume-EN.pdf` | 1-page PDF, 35,666 B | Homepage English résumé links | Selectable but untagged; intentionally public with HTTP `noindex` | Audited only; unchanged |
| `assets/resume/Kexing-Yan-Resume-ZH.pdf` | 1-page PDF, 110,063 B | Homepage Chinese-state résumé links | Selectable but untagged; intentionally public with HTTP `noindex` | Audited only; unchanged |

Both résumé links have descriptive visible labels and open the selected language
version. Their existing metadata and content were not rewritten in this phase.
The Chinese résumé's Author metadata uses the alternate name `严可行` rather
than the primary English representation; because the file is noindexed and no
source is available in this scope, this remains a documented low-risk entity
consistency caveat rather than a binary-only rewrite.

## Delivery and layout risk

There are no visible content images, so `loading`, `decoding`, captions, and
intrinsic `<img>` dimensions are not applicable. The social image is fetched by
preview agents rather than during normal page rendering. Manifest icon sizes are
declared. `_headers` gives social images a one-day public cache and `nosniff`.

The validator confirms that preview URLs are HTTPS, local files exist, declared
PNG dimensions match the files, secure/image URLs agree, and required alt text is
present. Modern formats were not introduced because PNG has broad social-preview
and icon support, and the lossless reductions are already material.
