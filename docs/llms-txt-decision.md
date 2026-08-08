# `llms.txt` Decision

**Decision date:** 2026-07-31
**Recommendation:** Implement a concise navigation file with explicit limits

## Evaluation

`llms.txt` has uneven and evolving ecosystem support. It is not a standard
search ranking control, does not guarantee crawling or citation, and does not
replace HTML, JSON-LD, `robots.txt`, or `sitemap.xml`. It also has no authority
to grant or deny crawler access; crawler policy remains in `robots.txt` and at
the HTTP/security layers.

The main risk is stale duplicated biography or abstract text. For this small
site, a short link-only file has low maintenance cost and gives retrieval tools
a human-readable map without mirroring the website.

## Implemented scope

`/llms.txt` contains only:

- a one-sentence verified site description;
- the canonical homepage;
- the canonical student-working-paper page;
- the paper PDF; and
- the intentionally public analysis-code repository.

It excludes email addresses, CVs, private work, local paths, future routes,
crawler directives, APIs, and copied abstracts. The validator resolves every
first-party URL and rejects local-development URLs or duplicated contact data.
The deployment verifier expects a plain-text 200 response.

Maintenance is simple: update the file only when canonical public resources are
added, removed, or renamed, and validate it with the rest of the site. It should
not be promoted as an SEO result or monitored as a ranking factor.

## Machine-readable person-file decision

`/data/person.json` is intentionally not implemented. The site has only one
person entity, already represented by visible homepage HTML and the canonical
Person JSON-LD node. A third biography copy would add more drift risk than
retrieval value without a shared content-generation system. Publications and
projects JSON files are also unjustified at the current collection size.
