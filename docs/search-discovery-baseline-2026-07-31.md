# Initial Search Discovery Baseline — 2026-07-31

This document records one controlled initial discovery and indexing-submission
cycle for `https://kexingyan.com/`. It is an operational baseline, not a
ranking report. Search-result observations are approximate, location-dependent,
and can change without notice.

## 1. Deployment commit

- Expected and locally checked-out commit:
  `d430685cd730d7c10b2fd7d68219c3a820a0488b`
- Branch: `main`

## 2. Deployment date

- Production deployment date: 2026-07-31
- The local commit timestamp is 2026-07-31 16:38:57 CST.
- The exact Cloudflare deployment completion timestamp was not re-opened or
  re-verified during this search-submission task.

## 3. Submission date and local time

- Initial submission cycle began: 2026-07-31 16:53:11 CST
- Google indexing requests were completed at approximately 16:55–16:59 CST.
- Bing URL submissions were recorded at 17:05 CST and 17:13 CST.

## 4. Google property status

- Property: `sc-domain:kexingyan.com`
- Type: Domain property
- Status: accessible and verified by existing Search Console access
- Search Console overview showed 11 total web-search clicks at review time.
- The Indexing report was still processing and stated that data should be
  checked again later.
- HTTPS report: 1 HTTPS page and 0 non-HTTPS pages.
- Manual actions: no issues detected.
- Security issues: no issues detected.
- Profile page enhancement: 1 valid item and 0 invalid items.

No ownership, user, or permission settings were changed.

## 5. Google sitemap status

- Sitemap: `https://kexingyan.com/sitemap.xml`
- Action: reviewed only; not resubmitted because a successful current entry
  already existed
- Submitted: 2026-07-26
- Last read: 2026-07-31
- Status: Success
- Discovered pages: 2
- Discovered videos: 0

## 6. Google homepage inspection

URL: `https://kexingyan.com/`

- Google index state: URL is on Google
- Referring sitemap: present
- Last crawl: 2026-07-29 15:41:40
- Crawled as: Googlebot smartphone
- Crawl allowed: Yes
- Page fetch: Successful
- Indexing allowed: Yes
- User-declared canonical: `https://kexingyan.com/`
- Google-selected canonical: inspected URL
- HTTPS: served over HTTPS
- Enhancement: one valid Profile page item
- Live test: run once on 2026-07-31 at approximately 16:55 CST
- Live result: URL is available to Google and can be indexed
- Rendered-output observation: the page was available to the mobile renderer;
  no blocking page-fetch or resource-loading problem was reported

Because the indexed crawl predated the 2026-07-31 deployment, indexing was
requested once. Search Console confirmed that the URL was added to a priority
crawl queue. The request was not repeated.

## 7. Google research-page inspection

URL: `https://kexingyan.com/research/microloan-quantity-size/`

- Google index state before submission: URL is not on Google
- Reason: URL is unknown to Google
- Referring sitemap in URL Inspection: none detected at that moment
- Last crawl and indexed canonical fields: not available because the URL had
  not been crawled
- Live test: run once on 2026-07-31 at approximately 16:57 CST
- Live result: URL is available to Google and can be indexed
- HTTP result in tested page: 200 OK
- Content type: `text/html`
- Resources: all tested resources loaded
- JavaScript console: no messages reported
- Structured data: one valid Breadcrumb item
- Rendered-output observation: the research title and visible
  “Student working paper” status were present; the page was not reported as a
  soft 404
- Tested metadata included the correct canonical URL and index/follow robots
  directive

The temporary difference between the sitemap report (two discovered pages) and
URL Inspection (no referring sitemap for this URL) is recorded as processing
lag, not as proof of a sitemap defect.

Indexing was requested once. Search Console confirmed that the URL was added to
a priority crawl queue. The request was not repeated.

## 8. Google indexing requests made

Exactly two Google indexing requests were made:

1. `https://kexingyan.com/`
2. `https://kexingyan.com/research/microloan-quantity-size/`

The research PDF was not submitted separately through Google URL Inspection.

## 9. Bing property status

- Property: `https://kexingyan.com/`
- Status: accessible through the existing Bing Webmaster Tools site
- Dashboard baseline: 0 clicks and 0 impressions for the displayed
  2026-04-30 to 2026-07-30 range
- Whether the property was originally imported from Google Search Console was
  not clearly shown and remains unverified.
- No ownership, user, permission, or linked-service settings were changed.

## 10. Bing sitemap status

- Sitemap: `https://kexingyan.com/sitemap.xml`
- Action: reviewed only; not resubmitted
- Submitted: 2026-07-26
- Last crawl: 2026-07-29
- Status: Success
- Discovered URLs: 2
- Errors: 0
- Warnings: 0

## 11. Bing homepage inspection

URL: `https://kexingyan.com/`

- Bing index state before submission: Discovered but not crawled
- Discovery date: 2026-07-26
- Search eligibility before crawl: URL could not yet appear on Bing
- Live URL test: run once on 2026-07-31 at 17:05 CST
- Live result: URL can be indexed by Bing, subject to Bing quality checks and
  indexing
- SEO/GEO issues in live test: none found
- Markup types found: 2
- Submission action: requested once
- Confirmation: Bing showed “Indexing requested.”

Bing did not expose an indexed-page canonical or last-crawl interpretation
because the page had not yet been crawled.

## 12. Bing research-page inspection

URL: `https://kexingyan.com/research/microloan-quantity-size/`

- Bing index state before submission: Not discovered
- Reason: the inspected URL was not known to Bing
- Live URL test: run once on 2026-07-31 at 17:10 CST
- Live result: URL can be indexed by Bing, subject to Bing quality checks and
  indexing
- SEO/GEO issues in live test: none found
- Markup types found: 2
- Submission action: requested once
- Confirmation: Bing reported a successful URL submission and showed
  “Indexing requested.”

Bing did not expose an indexed-page canonical, robots interpretation, or last
crawl because the URL was not yet known to its index. The successful live test
is evidence of current crawlability, not evidence of indexing.

## 13. Bing URL submissions made

Exactly two Bing URL submissions were made during this cycle:

1. `https://kexingyan.com/` — 2026-07-31 17:05 CST
2. `https://kexingyan.com/research/microloan-quantity-size/` —
   2026-07-31 17:13 CST

The Bing submission history also contained a pre-existing PDF submission dated
2026-07-27 08:53. The PDF was not resubmitted during this cycle. After the two
HTML submissions, Bing displayed 98 URL-submission quota units remaining and
two URLs submitted that day.

## 14. Current brand-search baseline

Search context:

- Date: 2026-07-31
- Google: Google Hong Kong results with personalization disabled using the
  `pws=0` parameter; the interface explicitly reported that results were not
  personalized. Location and IP context can still affect results.
- Bing: ordinary web results in the same Chrome session; the search interface
  was signed out of Bing.
- Positions below refer only to the visibly inspected first result page.

### Google

| Query | Baseline observation |
|---|---|
| `Kexing Yan` | `kexingyan.com` appeared as the first visible organic result with the title “Kexing Yan (严可行) \| Economics & Statistics.” Google also suggested the spelling “Kexin Yan,” so identity ambiguity remains. |
| `严可行` | The site did not appear on the inspected first page. Other people and unrelated phrase matches dominated. |
| `Kexing Yan University of Toronto` | The site appeared as the first visible organic result. The snippet identified Kexing Yan as an Honours BSc student at the University of Toronto. Google also broadened toward “Kexin Yan.” |
| `Kexing Yan Economics Statistics` | The site appeared as the first visible organic result with the canonical English/Chinese title and a matching academic snippet. Google also broadened toward “Kexin Yan.” |

### Bing

| Query | Baseline observation |
|---|---|
| `Kexing Yan` | The site did not appear on the inspected first page. IEEE, LinkedIn, and other same-name entities dominated; the owner’s LinkedIn result was visible near the top. |
| `严可行` | The site did not appear on the inspected first page. Unrelated people and phrase matches dominated. |
| `Kexing Yan University of Toronto` | The site did not appear on the inspected first page. The owner’s LinkedIn result was visible near the top. |
| `Kexing Yan Economics Statistics` | The site did not appear on the inspected first page. The owner’s LinkedIn result was the first visible organic result. |

No result was treated as a globally stable ranking position.

## 15. Current paper-title search baseline

Exact query:

`"The Quantity and Size of Microloans Follow Different Development Logics: Evidence from Kiva"`

- Google: the homepage appeared as the first visible organic result and showed
  the paper title in the snippet, but the dedicated research page and PDF did
  not appear as separate visible first-page results.
- Bing: neither the site, dedicated research page, nor PDF appeared in the
  inspected first-page web results. Bing showed general Kiva/microfinance
  results and a generated “Deep dive” entry related to the query.

## 16. Issues requiring later action

- Google URL Inspection had not yet associated the research page with the
  already-successful sitemap; recheck after processing completes.
- The Google research page was not indexed at submission time.
- Bing had not crawled the homepage and did not know the research page before
  submission.
- Bing’s ordinary first-page results did not yet show the website for the
  inspected brand/affiliation/field queries.
- The Chinese-name query did not show the site on the inspected first page of
  either Google or Bing.
- Both engines show substantial same-name or near-name ambiguity, especially
  “Kexin Yan.”
- Bing Recommendations displayed “No pages found.” Bing Site Scan had no
  previous scans; no new scan was initiated.

No crawl-blocking, canonical-conflict, mobile-rendering, blocked-resource, or
soft-404 problem was reported by the live inspection tests.

## 17. Screenshots captured

Dashboard and rendered-page views were visually inspected through the browser.
No screenshot files were saved to the repository because the dashboard views
could contain account context and were not required for the operational record.

## 18. Items not verifiable

- Exact Cloudflare deployment completion timestamp
- Whether the Bing property was originally imported from Google Search Console
- True global or logged-out rankings across countries, devices, and data centers
- Future crawl, indexing, ranking, rich-result, AI-grounding, or citation
  decisions
- Bing indexed-page canonical and last-crawl fields until Bing performs a crawl
- Whether Google will select the dedicated research page rather than the
  homepage for the exact paper-title query after reprocessing

## 19. Next review dates

- 7-day review: 2026-08-07
- 14-day review: 2026-08-14
- 28-day review: 2026-08-28

At each review, check:

- sitemap read/processed status
- homepage and research-page indexing state
- last crawl and selected canonical
- crawl errors or soft-404 classification
- brand and exact-title appearance
- dedicated research-page and PDF appearance
- ChatGPT referral traffic, if privacy-respecting analytics exists
- whether any genuine external link has been added

Do not repeat manual indexing requests daily or while the current requests are
still processing.

## 20. Submission limitation

Submission does not guarantee discovery, crawling, indexing, ranking, rich
results, inclusion in AI answers, grounding, citation, or any particular
processing time.

## Strategic decision: no IndexNow implementation

IndexNow was intentionally not implemented. The site currently has very few
public URLs and infrequent content changes, so sitemap discovery plus limited
manual submission is sufficient. Automated IndexNow would add key-management
and maintenance overhead without clear current value. Reconsider it only after
the site develops a recurring publication workflow.
