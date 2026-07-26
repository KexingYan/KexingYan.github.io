# KexingYan.github.io

Personal website for Kexing Yan, published at `https://kexingyan.com/`.

## Deployment

The `main` branch is the production source. Pushing to `main` triggers the
existing Cloudflare Pages deployment, which serves the custom domain
`kexingyan.com`.

## Search and indexing

- Google Search Console ownership is verified with a Cloudflare DNS TXT
  record. No Google verification token belongs in `index.html`.
- The homepage canonical URL is `https://kexingyan.com/`.
- The public sitemap is `https://kexingyan.com/sitemap.xml`; it includes the
  homepage and the public research paper.
- `_headers` applies `X-Robots-Tag: noindex` only to files under
  `/assets/resume/`. The homepage and public paper remain indexable.
