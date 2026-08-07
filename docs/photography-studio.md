# Photography Studio V1 — offline prototype

Studio is an owner-oriented contact sheet and editing desk at `/studio/`. H0 is
strictly local development: it has no login form, production API, R2, D1, Access,
upload endpoint, sitemap entry, or public navigation link. Every Studio document
uses `noindex, nofollow, noarchive`; `_headers` adds the equivalent crawler header.
The production release builder excludes both `/studio/` and `/assets/studio/`.

Do not deploy the source tree directly while Studio lacks Cloudflare Access. A
future deployment must protect `/studio/*` and `/api/photo-admin/*` and must add
server-side Access JWT validation before the Cloudflare repository adapter is
enabled.

## Data boundary

`LocalPhotoAdminRepository` owns local persistence. UI code calls only its
methods:

- `listPhotos()` / `getPhoto(id)`
- `saveDraft(photo)` / `publishPhoto(id)` / `archivePhoto(id)`
- `reorderPhotos(seriesId, ids)`
- `listSeries()` / `updateSeries(series)` / `reorderSeries(ids)`
- `prepareUpload(files)`
- `exportPublicManifest()` / `exportPreviewManifest()`

The local implementation stores its fixture in browser `localStorage`. The future
`CloudflarePhotoAdminRepository` will implement the same contract against the
authenticated admin API; view and editor code should not change.

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

The browser-only repository contract suite is at `/studio/tests.html`; it is also
noindex and excluded from production output.
