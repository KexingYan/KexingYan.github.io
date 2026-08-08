# Cloudflare Manual Review Checklist

**Purpose:** Post-deployment review; no dashboard change is authorized by this document

| Setting | Inspect and desired behavior | Possible conflict | Repository verification | Change necessary? |
|---|---|---|---|---|
| Pages production branch | Confirm `main`, repository-root build context, and `dist` output match documented deployment | Wrong branch or output serves stale/missing/internal files | Build and artifact validation only | Set build command and output exactly if current value differs |
| Custom domains | Confirm `kexingyan.com` and intended `www` binding | Unbound host, duplicate origin, certificate delay | No | Only if missing/misbound |
| Apex domain | Apex is canonical and serves the revision | Host duplication | Canonicals only | Correct if live behavior differs |
| `www` redirect | Preserve every path and query while redirecting to apex | Redirecting all paths to homepage creates soft 404s | `_redirects` does not govern dashboard host rules | Correct narrowly if test fails |
| SSL/TLS mode | Use a valid end-to-end mode appropriate to Pages; no insecure origin hop | Flexible/mismatched mode or redirect loops | No | Review; do not change blindly |
| Always Use HTTPS | HTTP should reach the HTTPS equivalent path | Loop or dropped path/query | No | Enable/correct only if HTTP remains exposed |
| Redirect Rules | No catch-all homepage rewrite; preserve exact repository `/papers` rules | Dashboard rule can override `_redirects` | `_redirects` only | Remove/adjust only conflicting rule |
| Bulk Redirects | Check for host/path rules affecting this domain | Stale import may override routes | No | Only if conflict exists |
| Transform Rules | Do not rewrite canonical paths, content types, or robots headers unexpectedly | Header/path mutation | `_headers` expresses intended values | Only if live output differs |
| Response Header Rules | Ensure they do not remove or contradict `_headers` | Duplicate CSP, robots, cache, content disposition | Partial local intent only | Reconcile narrowly |
| Cache Rules | Respect short PDF cache and avoid caching 404 HTML as 200 | Stale metadata, error caching | Intended cache documented | Change only proven conflict |
| Bot Fight Mode | Review events for challenges to allowed search/retrieval agents | Allowed crawler receives challenge/403 | No | Do not disable globally; create narrow evidence-based exception only |
| Super Bot Fight Mode | If available, inspect verified-bot treatment | Broad “likely automated” blocks | No | Narrow exception only when identity is verified |
| WAF managed rules | Review events after deployment | False positive on HTML/PDF/robots | No | Tune only the triggering rule/path |
| Custom firewall rules | Check user-agent, ASN, country, IP, and path conditions | Broad bot or geography block | No | Use verified operator identity/IP data, never UA alone |
| Rate limiting | Conservative verifier and normal crawler fetches should not be throttled | 429 from low-volume public reads | No | Adjust threshold only with evidence |
| Browser Integrity Check | Ensure it does not challenge ordinary public reads unexpectedly | False positive on non-browser clients | No | Keep unless verified conflict |
| Hotlink Protection | Social preview and favicon fetchers must receive assets | OG image may be blocked by referrer policy | Image references only | Add narrow asset allowance if proven |
| Email Address Obfuscation | Verify it does not rewrite `mailto:` links or initial HTML unexpectedly | Visible/DOM mismatch for contact links | No | Owner privacy decision; not required for SEO |
| Rocket Loader | Inline language and active-navigation scripts must execute in order | Delayed/reordered scripts break language state | Local source only | Disable for this site only if a live regression is observed |
| Automatic Platform Optimization | If present through another integration, confirm it does not rewrite static HTML | Stale cache or script modification | No | Not required for this static site |
| Pages Functions / Workers routes | Confirm only `/api/photo-admin/*` uses the Photography Pages Function and no catch-all intercepts static content | Soft 404, altered status/type, or an exposed admin API | Scoped Function plus Access and owner authorization | Remove or narrow any conflicting route |
| Deployment exclusions | Confirm the deployed file list matches the 35-file `dist` manifest | Publishing the repository root exposes docs and tools | Explicit allowlist and artifact validator | Set output to `dist`; investigate any extra live file |
| Asset cache invalidation | After metadata/image update, confirm new hash/content is served | Old OG or PDF persists | No | Purge only affected URLs if normal deploy invalidation fails |

## Crawler exception standard

Do not disable bot protection globally. First confirm the response in Security
Events, then verify the crawler through the operator's current official IP or
verified-bot mechanism where available. User-agent strings alone are spoofable.
Treat 403 or 429 from one ordinary verification request as a deployment symptom,
not proof that a named crawler is blocked.
