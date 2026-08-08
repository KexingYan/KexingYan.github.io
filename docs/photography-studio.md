# Photography Studio V1 — local and production adapters

Studio is an owner-oriented contact sheet and editing desk at `/studio/`. Every
Studio document uses `noindex, nofollow, noarchive`; `_headers` adds the
equivalent crawler header. Studio is absent from public navigation and sitemap.
Localhost selects `LocalPhotoAdminRepository`; production selects
`CloudflarePhotoAdminRepository` and calls only the Access-protected API.

Do not deploy the source tree directly. The release builder includes Studio only
when both `--include-studio` and `--studio-access-protected` are supplied. That
acknowledgement is valid only after anonymous blocking and owner access are tested.

## Data boundary

Both repositories implement the same UI-facing operations:

- `listPhotos()` / `getPhoto(id)`
- `saveDraft(photo)` / `publishChanges()` / `archivePhoto(id)`
- `reorderPhotos(seriesId, ids)`
- `listSeries()` / `updateSeries(series)` / `reorderSeries(ids)`
- `prepareUpload(files)`
- `uploadAssets(id, file, expectedUpdatedAt, replace)`
- `exportPublicManifest()` / `exportPreviewManifest()`

The local implementation stores its fixture in browser `localStorage`. The
Cloudflare implementation uses D1 drafts, private/public R2 bindings, optimistic
timestamps and collection revisions; UI components contain no persistence logic.

## Production safety model

- Cloudflare Access protects exactly `kexingyan.com/studio/*` and
  `kexingyan.com/api/photo-admin/*`.
- The Function verifies RS256 signature, issuer, audience, expiry, `sub`, email,
  and a server-only owner email allowlist on every request.
- Mutations reject unapproved origins. Errors use a stable JSON envelope and do
  not return stack traces.
- Existing published rows remain authoritative while changes live in
  `photo_drafts`. Preview merges them through the same public allowlist transform.
- Publish checks objects, writes an immutable manifest, verifies it, changes
  `current.json` last, verifies it, then records D1 revision.
- Archive is soft state; replacement increments `assetVersion`; no route performs
  permanent deletion.

## Production upload

JPEG is the only accepted type. The browser proves it can decode the source,
normalizes orientation, extracts approved basic EXIF, and builds 480/1280/2200/
1800px sRGB derivatives. The server independently checks MIME, JPEG structure,
50 MiB, 12,000px, 80MP, derivative limits and aspect ratios, assigns keys, stores
the unchanged master privately, and verifies each derivative after public R2 put.
Canvas output strips GPS and other source EXIF from public derivatives.

`buildPublicManifest()` is an allowlist transform that includes published records
only. Drafts and archived records never enter it, and private source/master fields
are removed. `buildPreviewManifest()` uses the same transform after promoting a
temporary clone of non-archived records, allowing draft title, order, series and
layout changes to render in the public Photography visual system without changing
the real public manifest.

## Local workflow

1. Edit a record and choose **Save draft**.
2. Choose **Preview** to open the public Photography layout with a local preview
   snapshot. The ribbon clearly says that nothing is published.
3. Choose **Publish** to change local mock state only. Public JSON files remain
   unchanged.
4. Use **Reset local fixture** to discard browser-only edits and reload the safe
   seed.

File selection in **Add photographs** is deliberately session-only. It can create
a metadata draft, but that record remains `awaiting-local-ingest` and cannot be
published. Durable image processing uses the Python command below.

## Offline ingest

Dry-run one image or a directory:

```sh
python3 scripts/ingest_photography.py /path/to/image.jpg --dry-run
python3 scripts/ingest_photography.py "/path/to/new photos" --dry-run
```

Write an explicitly confirmed local draft package:

```sh
python3 scripts/ingest_photography.py /path/to/image.jpg --confirm-write
```

Output defaults to ignored `.local/photography-ingest/<id>-v<version>/`. The
command never writes to its source, public seed, public manifest, Git, or cloud.
It validates JPEG/PNG signatures and decoding, enforces 50 MiB / 80 MP / 12,000px
limits, proposes a non-filename stable ID, extracts approved EXIF, normalizes
orientation and sRGB, creates four JPEG derivatives, strips GPS from them, and
writes a private draft record. Existing IDs and output packages are never
overwritten.

Publishing the package into authoritative data remains an explicit future step;
ingest always stops at `status=draft`.

## Offline validation

```sh
python3 scripts/validate_offline_h0.py
python3 -m http.server 8000
```

The browser-only repository contract suite is at `/studio/tests.html`. It is
noindex, absent from public navigation and sitemap, and covered by the same
Cloudflare Access rule as all `/studio/*` paths in production.
