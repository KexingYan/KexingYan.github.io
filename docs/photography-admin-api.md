# Photography owner API contract

Status: contract only. No routes, Studio UI, authentication bypass, or upload
handler are implemented in this phase.

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
422 valid JSON with invalid fields/state, 429 rate limited, and 500/503 internal
or storage failure. Failed mutations commit nothing and never advance a public
manifest pointer.

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

### `POST /api/photo-admin/photos/:id/publish`

Body contains `expectedUpdatedAt`. Validation requires a ready asset version,
title, slug, series, alt text, legal orientation/layout values, and a valid
download derivative when `allowDownload=true`. The transaction changes status
and records the publish revision. Public snapshot objects are written first;
`current.json` is updated last. Storage failure leaves the previous public pointer
intact and returns 503. Success returns the record and new manifest revision.

### `POST /api/photo-admin/photos/:id/archive`

Body contains `expectedUpdatedAt`. It marks the record archived, then republishes
the public manifest without it. R2 objects are retained; this route never deletes
masters or immutable derivatives. Returns the archived record and new manifest
revision.

## Image ingest and replacement

For the hybrid V1, the production endpoint is intentionally deferred. The same
contract governs the local publishing command and any later server handler.

### `POST /api/photo-admin/photos/:id/assets`

Purpose: attach the first asset to a draft or replace an existing image. Use
`multipart/form-data` with one `image` part and `expectedUpdatedAt`. A future
direct-to-R2 flow must issue only short-lived, single-object authorization after
the same owner checks; the browser never receives general R2 credentials.

Validation order:

1. Reject more than one file and unknown form parts.
2. Accept `image/jpeg` and `image/png`. Reject HEIC until the selected decoder and
   derivative pipeline are proven in production.
3. Enforce a 50 MiB encoded limit, suitable for the current 30–40 MB masters.
4. Verify magic bytes independently of extension and declared MIME.
5. Fully decode the image; reject truncation, decompression bombs, malformed
   profiles, and decode failures.
6. Enforce at most 80 megapixels and at most 12,000 pixels on either dimension.
7. Normalize orientation, strip metadata from derivatives, preserve only an
   approved sRGB profile, and generate all four expected JPEG derivatives.
8. Generate keys only from server-owned `photoId`, next `assetVersion`, and fixed
   variant names. Ignore the supplied filename for storage identity.
9. Verify derivative dimensions, MIME, bytes, and decode success before marking
   the version ready.

The private master is stored as
`photography/originals/private/<id>/v<version>/master.<approved-extension>`.
Public derivatives use `<id>-v<version>-<variant>.jpg`.

Replacement is a two-phase operation. It reserves `assetVersion + 1` in
`processing`, writes and validates new objects, then atomically marks the new
version ready and updates the photo. On failure, the current version remains
active and the new version is failed/abandoned for later cleanup. Immutable old
objects are never overwritten. The response is 202 while processing or 200 when
the local synchronous pipeline completes; it includes processing state but no
private master URL.

## Publish guarantees

The authoritative record contains public and private fields; the exporter uses an
explicit allowlist. Only `status=published` records enter the public manifest.
The public `download.src` always points to the 1800px personal-use derivative,
never the master. Manifest generation must fail closed if a requested derivative
or ready asset version is missing.

The implementation should remain single-owner and low-volume: D1 transactions,
R2 object versioning, an auditable publish revision, and idempotency keys for
uploads/publish are sufficient. A general multi-user media-management system,
client-side passwords, and anonymous original downloads are explicitly out of
scope.
