# Photography owner API contract

Status: Studio V1 is deployed and passed authenticated-owner and anonymous-access
production acceptance. Pages Functions live under `functions/api/photo-admin/`;
Cloudflare Access, migration `0003_admin_drafts.sql`, Pages bindings, server-only
Access variables, D1, and both R2 bindings are active.

## Boundary and common behavior

All `/api/photo-admin/*` routes are protected by Cloudflare Access and repeat
authorization in the application layer. The Function validates the Access JWT
signature, issuer, audience, expiry, and configured owner identity. Mutations
also require an approved `Origin`, a JSON content type unless uploading, and a
CSRF control appropriate to the final cookie/token design.

Responses use JSON. Errors have this stable envelope:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "One or more fields are invalid.",
    "fields": { "alt": "Required before publishing." },
    "requestId": "opaque-request-id"
  }
}
```

Expected statuses are 400 malformed request, 401 missing/invalid Access identity,
403 valid but unauthorized identity/origin, 404 unknown record, 409 optimistic
concurrency or ordering conflict, 413 upload too large, 415 unsupported media,
422 valid JSON with invalid fields/state, and 500/503 internal or storage failure.
A failed publish never leaves `current.json` advanced; failed asset writes may
retain a failed version record or immutable orphan for later controlled cleanup.

## Read and metadata mutations

### `GET /api/photo-admin/photos`

Returns every draft, published, and archived authoritative record plus series,
ordered for Studio. Private fields may be returned only to the authenticated
owner; local source paths and credentials are never returned. Supports optional
`?status=draft|published|archived`.

### `POST /api/photo-admin/photos`

Creates a metadata draft. Body contains editable public fields from the photo
schema and may omit the server-generated `id`, timestamps, `status`, and
`assetVersion`. The server allocates the next stable ID, sets `status=draft`, and
validates slug uniqueness, series membership, enum fields, ISO range, dates, and
text limits. Returns `201` with the created record. It does not publish or expose
an empty asset.

### `PATCH /api/photo-admin/photos/:id`

Body contains only changed editable fields plus required `expectedUpdatedAt`.
IDs, created timestamps, private object keys, and asset versions are not directly
editable. The update uses optimistic concurrency; a stale timestamp returns 409
with the current record and changes nothing. Returns the updated record on 200.

### `POST /api/photo-admin/photos/reorder`

Body:

```json
{
  "seriesId": "garden-notes",
  "orderedPhotoIds": ["P003", "P004", "P002", "P007"],
  "expectedRevision": 12
}
```

The list must contain each active photo in that series exactly once. A D1 batch
updates all `sortOrder` values and the collection revision atomically. A stale or
incomplete list returns 409/422 with no partial reorder.

### `POST /api/photo-admin/publish`

Body contains `expectedRevision` and `confirm=true`. Validation requires every
active record to have a ready asset version, title, slug, series, alt text, legal
orientation/layout values, and a valid download derivative when
`allowDownload=true`. The immutable snapshot is written and read back first;
`current.json` is updated and read back last; only then is the D1 revision created.
If the final D1 batch fails, the handler restores the previous `current.json`.

### `POST /api/photo-admin/photos/:id/archive`

Body contains `expectedUpdatedAt` and `confirm=true`. It stages the record as an
archived draft. R2 objects are retained and this route never deletes masters or
immutable derivatives. The record disappears from the public manifest only after
the owner separately previews and publishes the draft.

## Image ingest and replacement

For the hybrid V1, the browser decodes the JPEG, extracts a conservative EXIF
subset, normalizes orientation through `createImageBitmap`, and produces four
sRGB canvas JPEGs. The Function independently enforces Content-Type, JPEG magic
and marker structure, encoded size, dimensions, megapixels, aspect ratio, fixed
variant limits, and server-owned keys before writing R2. The unmodified master is
written only to private R2.

### `POST /api/photo-admin/photos/:id/assets`

Purpose: attach the first asset to a draft. Use `multipart/form-data` with
`master`, `thumbnail`, `preview`, `display`, `download`, and
`expectedUpdatedAt`. Replacement uses `/photos/:id/replace` and an explicit
confirmation header. The browser never receives R2 credentials.

Validation order:

1. Require the fixed named parts and reject unknown form-part names; the Studio
   client sends one file for each required variant.
2. Accept `image/jpeg` only. PNG, HEIC and other formats are rejected in V1.
3. Enforce a 50 MiB encoded limit, suitable for the current 30–40 MB masters.
4. Verify magic bytes independently of extension and declared MIME.
5. The browser fully decodes the image before upload; the Function independently
   validates JPEG signature, marker structure and declared dimensions.
6. Enforce at most 80 megapixels and at most 12,000 pixels on either dimension.
7. Normalize orientation, strip metadata from derivatives, preserve only an
   approved sRGB profile, and generate all four expected JPEG derivatives.
8. Generate keys only from server-owned `photoId`, next `assetVersion`, and fixed
   variant names. Ignore the supplied filename for storage identity.
9. Verify derivative dimensions, MIME, bytes, and decode success before marking
   the version ready.

The private master is stored as
`photography/originals/private/<id>/v<version>/master.jpg`.
Public derivatives use `<id>-v<version>-<variant>.jpg`.

Replacement is a two-phase operation. It reserves `assetVersion + 1` in
`processing`, writes and validates new objects, then atomically marks the new
version ready and updates the photo. On failure, the current version remains
active and the new version is failed/abandoned for later cleanup. Immutable old
objects are never overwritten. The synchronous V1 response is 200 after storage
verification and includes processing state but no private master URL.

## Publish guarantees

The authoritative record contains public and private fields; the exporter uses an
explicit allowlist. Only `status=published` records enter the public manifest.
The public `download.src` always points to the 1800px personal-use derivative,
never the master. Manifest generation must fail closed if a requested derivative
or ready asset version is missing.

The implementation remains single-owner and low-volume: D1 batches, optimistic
revision checks, R2 object versioning, and an auditable publish revision are
sufficient. A general multi-user media-management system,
client-side passwords, and anonymous original downloads are explicitly out of
scope.
