# Photography + Studio V1 release

Production acceptance completed successfully before repository consolidation.

## Summary

- Photography V1 presents 14 photographs across four curated series in an
  editorial responsive gallery with contact-sheet Index, keyboard-accessible
  lightbox, personal-use download license, and reduced-motion support.
- Motion Polish adds restrained one-shot discovery, hero, dialog, and homepage
  transitions without an animation dependency.
- Studio V1 is an owner-only contact sheet and editing desk protected by
  Cloudflare Access. It supports JPEG upload, EXIF-aware ingest, drafts, public
  layout preview, publish, manual ordering, versioned replacement, archive, and
  personal-download control.

## Architecture

Public reads follow:

```text
kexingyan.com/photography/
  -> public-safe manifest
  -> images.kexingyan.com
  -> public R2 derivatives
```

Private administration follows:

```text
Cloudflare Access
  -> /studio/ and /api/photo-admin/*
  -> Pages Functions
  -> D1 + private/public R2
```

Publishing follows:

```text
Draft -> Preview -> Validate -> immutable manifest -> verify
      -> current.json LAST -> D1 publish revision
```

D1 is authoritative for metadata, drafts, ordering, publish revisions, and asset
version history. Original masters remain in private R2; public R2 contains only
versioned derivatives and public-safe manifests.

## Security model

- Every admin request validates the Cloudflare Access JWT and server-side owner
  allowlist; mutations additionally validate Origin.
- Public serialization uses an explicit field allowlist. Private object keys,
  source paths, hashes, credentials, and owner configuration are never emitted
  to the public manifest or frontend configuration.
- Masters have no public R2/custom-domain route. Replacement increments
  `assetVersion`; archive is non-destructive.
- Uploads enforce JPEG type, encoded-size, dimension, megapixel, aspect-ratio,
  fixed-variant, optimistic-concurrency, and server-owned-key constraints.

## Production acceptance

- Accepted Pages deployment: `1dffe75a-ddb2-4a67-a91f-51c396866a7c`
- Rollback deployment: `5a950b89-63bd-4dc9-bbf5-576344ecf4e6`
- Public routes: `/`, `/photography/`, `/photography/license/`
- Private routes: `/studio/`, `/api/photo-admin/*`
- Public manifest: `https://images.kexingyan.com/photography/manifests/current.json`

Production acceptance verified anonymous Access blocking, authenticated owner
Studio/API operation, draft isolation, preview, publish revisioning, real JPEG
upload, private-master isolation, desktop/mobile layouts, and rollback readiness.

## Known limitations

- V1 is intentionally single-owner and JPEG-only.
- Series reordering remains a controlled D1 operation rather than a production
  Studio action.
- There is no permanent-delete route or automatic storage-retention cleanup.
- Local batch ingest remains the recovery and high-volume preparation workflow.
