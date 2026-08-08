# Photography production architecture

Status as of 2026-08-08: Photography + Studio V1 passed production acceptance.
Production Pages deployment `1dffe75a-ddb2-4a67-a91f-51c396866a7c` serves the
public gallery and the Access-protected Studio/API. Rollback deployment
`5a950b89-63bd-4dc9-bbf5-576344ecf4e6` remains available. Phase G storage is
live with separate public/private R2 buckets, the D1 database,
`images.kexingyan.com`, 14 accepted masters and 56 accepted derivatives.
Migration `0003_admin_drafts.sql`, Pages bindings, server-only Access variables,
and the owner-only Access application are active.

## Phase G actual values and boundary

Deterministic target names:

- Public R2 bucket: `kexingyan-photography-public`
- Private R2 bucket: `kexingyan-photography-private`
- D1 database: `kexingyan-photography`
- Public hostname: `images.kexingyan.com`

These are the production resource names. Future maintenance must discover and
verify them before any write; never recreate them or infer replacements.

The checked-in `cloudflare/photography/wrangler.jsonc` is deliberately
non-deployable until `<D1_DATABASE_ID>` is replaced in an ignored copy named
`wrangler.resolved.jsonc`. It disables accidental guessing and does not use
Wrangler automatic provisioning.

## Decision

Use a hybrid Cloudflare architecture with two R2 buckets:

1. A **public Photography bucket** stores only versioned web derivatives and
   public-safe manifests. Attach `images.kexingyan.com` as its custom domain and
   disable the development `r2.dev` URL.
2. A **private master bucket** stores originals. It has no custom domain and no
   `r2.dev` public URL. Only the authenticated Pages Function receives its R2
   binding.
3. Cloudflare Pages continues to serve the static site. Public pages fetch the
   current manifest and JPEGs directly from the image domain; they do not proxy
   every public byte through a Function.
4. D1 is the private authoritative metadata store. A publish action
   produces an immutable public snapshot plus a small `current.json` pointer in
   the public bucket.

This is simpler and cheaper than proxying all public images while preserving a
hard security boundary around masters. Cloudflare documents that connecting a
custom domain makes bucket contents publicly available, which is why originals
must not share that bucket. Custom domains also enable Cloudflare Cache; `r2.dev`
is intended for development and does not provide the same caching controls.

## Why D1, not KV, R2 JSON, or Git JSON

D1 is the production authority because Studio requires ordered records,
draft/published state, asset-version history, constraints, and multi-record
reordering. D1 batch operations are transactional, and Time Travel supplies
point-in-time recovery. The schema is in
`migrations/photography/0001_initial.sql`.

KV is a poor authority for concurrent edits because writes are eventually
consistent and simultaneous writes to one key can overwrite one another. A
single R2 JSON object would require application-managed concurrency and whole-file
rewrites. Git-managed JSON is reviewable, but an owner Studio would need Git write
credentials and deployments for routine edits. Git remains appropriate for the
public-safe seed/schema and scripts, not live Studio mutations.

The public website does not query D1. Publishing exports only published fields to
a static manifest, keeping public reads fast and resilient.

## Object layout

Use the deterministic bucket names above after read-only discovery confirms they
do not conflict with existing resources.

Keys:

```text
private bucket
photography/originals/private/P014/v1/master.jpg

public bucket
photography/derivatives/thumbnail/P014-v1-thumbnail.jpg
photography/derivatives/preview/P014-v1-preview.jpg
photography/derivatives/display/P014-v1-display.jpg
photography/derivatives/download/P014-v1-download.jpg
photography/manifests/seed-2026-08-07-v1.json
photography/manifests/current.json
```

Human titles and source filenames are never storage identity. `P014` remains the
photo identity, and `v1` is the binary asset version. The public manifest contains
neither the master key nor source provenance.

## Cache policy and replacement

- Versioned derivatives: `Cache-Control: public, max-age=31536000, immutable`.
- Versioned manifest snapshots: the same immutable policy.
- `current.json`: `Cache-Control: public, max-age=60, must-revalidate`.
- Private masters: `Cache-Control: private, no-store`; no public route exists.

R2 custom-domain JSON responses may need an explicit Cache Rule because not all
content types are cached by default. Create a narrowly scoped rule for
`/photography/manifests/*`; never create one for a private bucket.

Replacing P014 keeps `id=P014`, increments `assetVersion` to 2, and writes new
`P014-v2-*` objects. Publish the immutable snapshot first and update
`current.json` last. Old versioned objects remain safe to serve until a later,
separately reviewed retention cleanup. R2 overwrites can remain cached until TTL
or purge, so immutable objects must never be replaced in place.

## Maintenance authentication and read-only discovery

Use this sequence before future maintenance. Do not paste credentials into chat,
Git, shell history, or public logs.

1. Install a supported Node.js LTS runtime if desired, then authenticate
   interactively with `npx wrangler@latest login`. Alternatively sign in to the
   Cloudflare Dashboard in the in-app browser and tell Codex when it is ready.
2. Verify the selected account before any write:

   ```sh
   npx wrangler@latest whoami
   npx wrangler@latest r2 bucket list
   npx wrangler@latest d1 list
   ```

3. In **DNS → Records** for `kexingyan.com`, search exactly for
   `images.kexingyan.com`. Do not edit or overwrite a result. In R2, list custom
   domains for any existing candidate public bucket.
4. Record the selected account, existing resource names, D1 database ID, zone ID,
   and DNS result in an owner-only location. Only the D1 database ID belongs in
   the ignored resolved Wrangler file; no IDs are guessed.

## Production setup record and future recovery procedure

The production resources already exist. The commands below are retained only as
a recovery/reference procedure; do not rerun creation, initial seed, or domain
attachment against the accepted environment.

1. If discovery found no suitable resources, create the two buckets and D1:

   ```sh
   npx wrangler@latest r2 bucket create kexingyan-photography-public
   npx wrangler@latest r2 bucket create kexingyan-photography-private
   npx wrangler@latest d1 create kexingyan-photography
   ```

   Keep public access disabled on both buckets initially. Copy
   `cloudflare/photography/wrangler.jsonc` to the ignored
   `wrangler.resolved.jsonc` and replace only `<D1_DATABASE_ID>` with the returned
   real ID.
2. Confirm that both `r2.dev` development URLs are disabled. Do not add any
   public domain to the private bucket.
3. Add CORS on the public bucket for origins `https://kexingyan.com` and
   `https://www.kexingyan.com`, methods `GET` and `HEAD`, and required response
   headers only. Do not allow credentials or wildcard mutation methods:

   ```sh
   npx wrangler@latest r2 bucket cors set kexingyan-photography-public \
     --file cloudflare/photography/public-bucket-cors.json
   npx wrangler@latest r2 bucket cors list kexingyan-photography-public
   ```

4. Add cache rules for the derivative and manifest prefixes described above.
5. Apply both D1 migrations, then the generated private seed. The seed succeeds
   only when its seed ID is absent and all Photography tables are empty; it does
   not upsert or overwrite later Studio edits:

   ```sh
   npx wrangler@latest d1 migrations apply PHOTOGRAPHY_DB --remote \
     --config cloudflare/photography/wrangler.resolved.jsonc
   npx wrangler@latest d1 execute PHOTOGRAPHY_DB --remote \
     --config cloudflare/photography/wrangler.resolved.jsonc \
     --file /owner-only/path/photography-d1-initial-seed.sql
   ```

6. Active Pages Function bindings:
   - `PHOTO_MASTERS`: private R2 bucket
   - `PHOTO_PUBLIC`: public R2 bucket
   - `PHOTOGRAPHY_DB`: D1 database
   - optional `IMAGES`: only after a processing proof of concept
7. Add non-secret Pages build variables:
   - `PHOTOGRAPHY_ASSET_BASE=https://images.kexingyan.com/photography/derivatives`
   - `PHOTOGRAPHY_MANIFEST_URL=https://images.kexingyan.com/photography/manifests/current.json`
8. Active server-only Access settings:
   - `CF_ACCESS_TEAM_DOMAIN`
   - `CF_ACCESS_AUD`
   - `PHOTO_ADMIN_OWNER_EMAILS`
   - `PHOTO_ADMIN_ALLOWED_ORIGINS`

9. Upload in this order from the reviewed private plan: 14 masters, 56 immutable
   derivatives, verify all derivative objects, immutable manifest snapshot, then
   `current.json` last. `wrangler r2 object put` must include the plan's content
   type, cache-control, and optional content-disposition. Before each write, get
   any existing deterministic key and compare its hash; skip identical content
   and stop on differing immutable content. Never delete or overwrite a master.
10. Only after all public objects verify, connect the custom domain using the
    verified zone ID or Dashboard. The CLI form is:

    ```sh
    npx wrangler@latest r2 bucket domain add kexingyan-photography-public \
      --domain images.kexingyan.com --zone-id '<VERIFIED_ZONE_ID>'
    ```

    First confirm that no DNS record occupies the hostname. Never run this with a
    guessed zone ID. Verify the private bucket still has no domain.

No R2 API token, account identifier, service token, owner email, or Access secret
belongs in Git or public JavaScript. No resolved `.dev.vars` file is checked in;
production owner and Access values remain in Cloudflare's server-side settings.

### Public-safe configuration

- Resource names and object prefixes above
- `PHOTOGRAPHY_ASSET_BASE`
- `PHOTOGRAPHY_MANIFEST_URL`
- `cloudflare/photography/public-bucket-cors.json`
- Binding names without IDs or credentials

### Secret or owner-only configuration

- Wrangler login/profile and API tokens
- Account and zone identifiers
- Resolved D1 database ID file
- Access audience, team domain, owner identity, and service tokens
- Private provenance, D1 seed SQL, R2 upload plan, and source paths/hashes

## Access and admin boundary

One self-hosted Cloudflare Access application now has two destinations,
`kexingyan.com/studio/*` and `kexingyan.com/api/photo-admin/*`, and an owner-only
allow policy using one-time PIN. Hiding Studio is not API authorization. Every Function validates the
`Cf-Access-Jwt-Assertion` signature, issuer, audience, expiry, and allowed owner
identity before reading private data or mutating anything. Mutation endpoints
also enforce origin/CSRF defenses and JSON content types. The owner's identity is
server-side configuration, never a value embedded in public JS.

## Processing strategy

V1 supports both controlled local ingest and the owner-only browser upload path:

```text
local: master -> Python/Pillow validation -> four derivatives -> draft package
online: owner browser -> decode/normalize -> four derivatives -> Pages Function
                    -> private/public R2 + D1 draft -> preview -> publish
```

The local path remains the safest batch/recovery workflow and never publishes
implicitly. Studio V1 also accepts owner-selected JPEGs, creates four browser
derivatives, stores the unchanged master privately, and leaves the result as a
draft until explicit Preview and Publish. Cloudflare Images is not part of V1.

## Local and production builds

Local development remains unchanged:

```sh
python3 scripts/generate_photography.py \
  --source /path/to/private-masters \
  --source-map /path/to/private-source-map.json \
  --private-manifest /path/to/private-provenance.json
python3 -m http.server 8000
```

Production staging deliberately excludes local JPEGs and the seed data:

```sh
python3 scripts/build_photography_release.py \
  --output dist \
  --asset-base "$PHOTOGRAPHY_ASSET_BASE" \
  --manifest-url "$PHOTOGRAPHY_MANIFEST_URL"
```

Production Pages deploys the release tree with Studio explicitly included behind
verified Access. The source tree remains usable locally, and the release tree
references the R2 image hostname.

## Final production flow

```text
Public
kexingyan.com/photography/
  -> public-safe current.json
  -> images.kexingyan.com
  -> public R2 versioned derivatives

Private
Cloudflare Access
  -> /studio/ and /api/photo-admin/*
  -> Pages Functions
  -> D1 + private/public R2 bindings

Publish
Draft -> Preview -> Validate -> immutable manifest -> verify
      -> current.json LAST -> D1 publish revision
```

## Non-destructive migration for P001–P014

1. Re-hash all 14 source masters and compare them with the private provenance.
2. Confirm the seed has unique stable IDs P001–P014 and `assetVersion=1`.
3. Generate/verify the 56 local versioned derivatives. Keep all current local
   files; do not rename, overwrite, or delete masters.
4. Generate a production-mode manifest outside Git.
5. Generate a private dry-run R2 plan with
   `scripts/prepare_photography_r2_plan.py`. Review all 72 planned writes: 14
   private masters, 56 public derivatives, and two public manifests.
6. After manual bucket setup and credentials approval, upload masters to the
   private bucket and verify hashes/metadata.
7. Upload versioned derivatives and the immutable manifest snapshot to the public
   bucket. Verify status, MIME, size, dimensions, and caching from the custom
   domain.
8. Upload `current.json` last. Build the production site against the R2 URLs and
   test the Photography page, lightbox, responsive sources, and downloads.
9. Only after production verification, remove any previously tracked derivative
   binaries from Git in a separately reviewed change. Local ignored derivatives
   and source masters remain untouched.

The current preparation script performs no network calls, uploads, deletions, or
Cloudflare changes.

The latest Phase G preflight verified 14 unchanged masters, 56 derivatives, no
GPS metadata, no public private-field leakage, 72 unique destinations, and
`current.json` last. Planned writes are 238,110,071 bytes private plus 37,288,845
bytes public, 275,398,916 bytes total. The public total includes two manifest
objects containing the same 23,699-byte payload.

## Rollback

Do not delete local derivatives during Phase G. Before switching the Pages build,
record the current build command/output directory and deployed version. Rollback
is to restore the previous Pages build/deployment that serves local site-hosted
assets; no R2 or D1 deletion is required. Because versioned R2 objects are
immutable and `current.json` is the only mutable public pointer, object rollback
can also restore a previously saved `current.json` after verifying its snapshot.
Never delete the D1 database, private masters, or old immutable derivatives as
part of rollback.

## Cloudflare references

- [R2 public buckets and custom domains](https://developers.cloudflare.com/r2/buckets/public-buckets/)
- [Cloudflare Cache with R2](https://developers.cloudflare.com/cache/interaction-cloudflare-products/r2/)
- [R2 Worker bindings](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/)
- [Pages bindings](https://developers.cloudflare.com/pages/functions/bindings/)
- [D1 overview](https://developers.cloudflare.com/d1/)
- [D1 batch transaction behavior](https://developers.cloudflare.com/d1/worker-api/d1-database/)
- [D1 Time Travel](https://developers.cloudflare.com/d1/reference/time-travel/)
- [KV write consistency](https://developers.cloudflare.com/kv/api/write-key-value-pairs/)
- [Validate Cloudflare Access JWTs](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/)
- [Cloudflare Images limits](https://developers.cloudflare.com/images/get-started/limits/)
- [R2 upload metadata](https://developers.cloudflare.com/r2/objects/upload-objects/)
- [R2 consistency and cached overwrites](https://developers.cloudflare.com/r2/reference/consistency/)
- [Wrangler configuration](https://developers.cloudflare.com/workers/wrangler/configuration/)
- [Wrangler R2 commands](https://developers.cloudflare.com/workers/wrangler/commands/r2/)
- [R2 CORS](https://developers.cloudflare.com/r2/buckets/cors/)
- [Wrangler D1 commands](https://developers.cloudflare.com/d1/wrangler-commands/)
