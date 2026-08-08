# Deployment Manifest

**Target:** Cloudflare Pages, explicit `dist/` static artifact
**Canonical origin:** `https://kexingyan.com`

**Build command:** `python3 scripts/build_site.py`
**Output directory:** `dist`
**Internal hash inventory:** `dist-manifest.json` (not deployed)

## Expected deployable files

- Profile and errors: `index.html`, `404.html`
- Discovery: `robots.txt`, `sitemap.xml`, `llms.txt`, `site.webmanifest`
- Cloudflare controls: `_headers`, `_redirects`
- Ownership verification: `baidu_verify_codeva-vWXLKxDtXl.html`
- Research: `research/microloan-quantity-size/index.html` and the accepted PDF
- Photography: public gallery, license, production R2 configuration, CSS, and JS
- Private Studio: noindex HTML/CSS/JS protected by Cloudflare Access
- Public identity assets: referenced CSS, six browser/install icons, and the
  Open Graph image listed by `scripts/build_site.py`
- Intentionally public noindex CVs: both linked language versions

The allowlist contains 35 files. `assets/icons/kx-logo.png` is deliberately
excluded because no deployed page or manifest references it.

## Files that must not deploy

- `.git/**`, local attachments, editor metadata, credentials, `.env*`
- `tmp/**`, PDF render PNGs, optimization candidates, caches
- `__pycache__/**`, `*.pyc`, `.DS_Store`
- `README.md`, `docs/**`, `scripts/**`, `.github/**`, `.gitignore`
- `scripts/site_dates.json` and `dist-manifest.json`
- the unreferenced `assets/icons/kx-logo.png`
- unpublished manuscript source, private datasets, raw Kiva data, API keys,
  private project files, or local configuration

## Public behavior contract

| Route/resource | Expected status | Expected type | Redirect / cache | Indexability |
|---|---:|---|---|---|
| `/` | 200 | `text/html` | No redirect; platform default cache | Indexable; self-canonical |
| `/research/microloan-quantity-size/` | 200 | `text/html` | No redirect; platform default cache | Indexable; self-canonical |
| `/photography/` | 200 | `text/html` | Public manifest and derivatives served from `images.kexingyan.com` | Indexable; self-canonical |
| `/photography/license/` | 200 | `text/html` | No redirect; platform default cache | Indexable; self-canonical |
| `/studio/` | 200 after Access | `text/html` | Cloudflare Access authentication required | `noindex, nofollow` |
| `/api/photo-admin/*` | API response after Access | Varies | Pages Functions; owner allowlist and Origin checks | Private API |
| `/papers/the-quantity-and-size-of-microloans.pdf` | 200 | `application/pdf` | Inline; 1-hour public revalidation | Indexable |
| `/papers` | 301 | n/a | To canonical HTML research page | Redirect source excluded from sitemap |
| `/papers/` | 301 | n/a | To canonical HTML research page | Redirect source excluded from sitemap |
| `/404.html` | 200 when requested directly | `text/html` | No redirect | `noindex, follow` |
| Unknown path | 404 | `text/html` | Must use custom error content, not 200 fallback | Not indexable |
| `/robots.txt` | 200 | `text/plain` | No challenge | Public policy file |
| `/sitemap.xml` | 200 | XML | No redirect | Discovery file, not a content page |
| `/llms.txt` | 200 | `text/plain; charset=utf-8` | No redirect | Navigation aid, not a ranking directive |
| `/assets/images/*` | 200 | image type | 1-day public cache | Asset only |
| `/assets/resume/*` | 200 | `application/pdf` | Platform default | HTTP `noindex` |
| `/docs/*`, `/scripts/*`, `/README.md` | Not deployed | n/a | n/a | Physically absent from artifact |

## Robots contract

Ordinary search and documented search/user-retrieval agents remain allowed;
`GPTBot` and `ClaudeBot` remain disallowed; `Google-Extended` remains an
intentional combined-use trade-off. Robots permission does not override WAF,
grant access, guarantee indexing, or protect private data.

## Post-deployment command

Run only after deployment is authorized:

```sh
python3 scripts/verify_production.py https://kexingyan.com/
```

Then manually inspect Cloudflare security events and complete the checklists in
`docs/cloudflare-manual-checklist.md` and
`docs/search-console-post-deployment.md`.

## Cloudflare Pages configuration

- Production branch: `main`
- Root directory: repository root
- Build command: `python3 scripts/build_site.py`
- Build output directory: `dist`
- Public build environment variables: none required
- Pages Functions: `functions/api/photo-admin/[[path]].js`
- Function bindings/secrets: D1, public/private R2, Access JWT settings, and
  owner allowlist configured only in Cloudflare
- Workers routes: none expected outside the scoped Pages Functions API
