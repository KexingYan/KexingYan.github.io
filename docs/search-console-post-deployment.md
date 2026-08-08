# Search Console Post-Deployment Checklist

Run this checklist only after the production verification script passes. Do not
promise indexing and do not repeatedly request indexing.

## Google Search Console

1. Inspect `https://kexingyan.com/`:
   - Google-selected versus user-declared canonical;
   - last crawl, response status, crawl permission, and indexing state;
   - rendered HTML contains the canonical name, affiliation, and research link;
   - mobile usability and blocked resources.
2. Inspect the canonical research page:
   - self-canonical URL and 200 response;
   - visible “Student working paper” status;
   - rendered summary, citations, author, and PDF link;
   - structured-data detection without a journal/DOI claim.
3. Review the submitted sitemap status and discovered URL count. Submit the
   canonical sitemap only after live XML verification; do not submit redirect,
   404, CV, documentation, or language-state URLs.
4. Review page indexing/crawl reports for soft 404s, duplicate canonicals,
   blocked resources, and `/papers` redirect handling.
5. Review Core Web Vitals only when sufficient field data exists; use
   Lighthouse as lab evidence, not a substitute for field data.
6. Check rich-result eligibility where relevant. A valid `ScholarlyArticle`
   graph does not guarantee a rich result.
7. Request indexing at most once for each changed canonical HTML page after all
   live checks pass. Normal crawling and sitemap discovery remain preferred.

## Bing Webmaster Tools

1. Inspect homepage and research-page response, canonical, crawl permission,
   rendered content, and blocked resources.
2. Confirm the sitemap parses and includes only the three intended canonical
   resources.
3. Review crawl errors for unknown paths, `/papers` redirects, PDF access, and
   bot/WAF responses.
4. Evaluate IndexNow only as an optional freshness notification after a
   meaningful content change. For a two-page static site it is not required;
   do not add credentials or automation without a maintenance need.
5. Submit canonical URLs only after production verification; do not repeatedly
   resubmit or interpret submission as an indexing guarantee.

Record the inspection date and observed status in an operational log outside
the public site if ongoing tracking is needed. Do not copy private dashboard
identifiers, tokens, or account data into the repository.
