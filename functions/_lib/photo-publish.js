import { HttpError } from "./http.js";
import { listArchive, validatePhoto } from "./photo-admin-store.js";

const PUBLIC_FIELDS = Object.freeze([
  "id", "slug", "title", "seriesId", "dateTaken", "datePublished", "locationDisplay",
  "caption", "alt", "camera", "lens", "focalLength", "aperture", "shutterSpeed", "iso",
  "orientation", "layoutHint", "featured", "allowDownload", "sortOrder", "assetVersion", "updatedAt",
]);
const REQUIRED_VARIANTS = ["thumbnail", "preview", "display"];

function now() { return new Date().toISOString(); }
function objectKey(id, version, variant) {
  return `photography/derivatives/${variant}/${id}-v${version}-${variant}.jpg`;
}

async function loadExistingManifest(env) {
  const object = await env.PHOTO_PUBLIC.get("photography/manifests/current.json");
  if (!object) throw new HttpError(503, "current_manifest_missing", "Current public manifest could not be read.");
  try { return { object, manifest: await object.json() }; }
  catch { throw new HttpError(503, "current_manifest_invalid", "Current public manifest is invalid."); }
}

async function imagesFor(env, photo, existingById) {
  const variants = [...REQUIRED_VARIANTS, ...(photo.allowDownload ? ["download"] : [])];
  const images = {};
  for (const variant of variants) {
    const key = objectKey(photo.id, photo.assetVersion, variant);
    const head = await env.PHOTO_PUBLIC.head(key);
    if (!head) throw new HttpError(422, "asset_missing", `${photo.id} is missing its ${variant} derivative.`);
    const row = await env.PHOTOGRAPHY_DB.prepare(`SELECT width, height, bytes FROM photo_asset_derivatives
      WHERE photo_id = ? AND asset_version = ? AND variant = ?`)
      .bind(photo.id, photo.assetVersion, variant).first();
    const previous = existingById.get(photo.id)?.images?.[variant];
    const metadata = row || (previous && previous.src?.includes(`${photo.id}-v${photo.assetVersion}-${variant}.jpg`) ? previous : null);
    if (!metadata?.width || !metadata?.height) throw new HttpError(422, "asset_metadata_missing", `${photo.id} ${variant} dimensions are unavailable.`);
    images[variant] = {
      src: `https://images.kexingyan.com/${key}`,
      width: Number(metadata.width),
      height: Number(metadata.height),
      bytes: Number(row?.bytes || previous?.bytes || head.size),
    };
  }
  return images;
}

export async function buildPreview(env) {
  const [state, existing] = await Promise.all([listArchive(env), loadExistingManifest(env)]);
  const existingById = new Map(existing.manifest.photos.map((photo) => [photo.id, photo]));
  const active = state.photos.filter((photo) => photo.status !== "archived");
  const featured = active.filter((photo) => photo.featured);
  if (featured.length !== 1) throw new HttpError(422, "featured_conflict", "Preview requires exactly one featured photograph.");
  const photos = [];
  for (const candidate of active) {
    const photo = validatePhoto(candidate, { forPublish: true });
    const publicPhoto = Object.fromEntries(PUBLIC_FIELDS.map((field) => [field, photo[field]]));
    publicPhoto.images = await imagesFor(env, photo, existingById);
    photos.push(publicPhoto);
  }
  const seriesOrder = new Map(state.series.map((series, index) => [series.id, index]));
  photos.sort((a, b) => (seriesOrder.get(a.seriesId) - seriesOrder.get(b.seriesId)) || a.sortOrder - b.sortOrder || a.id.localeCompare(b.id));
  return {
    schemaVersion: 1,
    publishRevision: `preview-${state.revision}`,
    assetMode: existing.manifest.assetMode || "production",
    assetBase: existing.manifest.assetBase || "https://images.kexingyan.com/photography/derivatives",
    series: state.series.map(({ sortOrder, updatedAt, ...series }) => series),
    photos,
    preview: { draftChanges: state.photos.filter((photo) => photo.hasDraft).length, collectionRevision: state.revision },
  };
}

function photoUpdate(db, photo, timestamp) {
  return db.prepare(`UPDATE photos SET slug = ?, title = ?, series_id = ?, date_taken = ?,
    date_published = ?, location_display = ?, caption = ?, alt = ?, camera = ?, lens = ?,
    focal_length = ?, aperture = ?, shutter_speed = ?, iso = ?, orientation = ?, layout_hint = ?,
    featured = ?, allow_download = ?, sort_order = ?, status = ?, asset_version = ?, updated_at = ?
    WHERE id = ?`)
    .bind(photo.slug, photo.title, photo.seriesId, photo.dateTaken || null,
      photo.status === "published" ? (photo.datePublished || timestamp.slice(0, 10)) : photo.datePublished || null,
      photo.locationDisplay || "", photo.caption || "", photo.alt, photo.camera, photo.lens,
      photo.focalLength, photo.aperture, photo.shutterSpeed, photo.iso,
      photo.orientation, photo.layoutHint, photo.featured ? 1 : 0, photo.allowDownload ? 1 : 0,
      photo.sortOrder, photo.status, photo.assetVersion, timestamp, photo.id);
}

export async function publishAll(env, identity, expectedRevision) {
  const preview = await buildPreview(env);
  const state = await listArchive(env);
  if (state.revision !== expectedRevision || preview.preview.collectionRevision !== expectedRevision) {
    throw new HttpError(409, "publish_conflict", "Archive changed while publish was being prepared.", {
      currentRevision: state.revision,
    });
  }
  const draftCount = state.photos.filter((photo) => photo.hasDraft).length;
  if (!draftCount) throw new HttpError(422, "nothing_to_publish", "There are no draft changes to publish.");
  const timestamp = now();
  const suffix = crypto.randomUUID().replace(/-/g, "").slice(0, 8);
  const revision = `studio-${timestamp.replace(/[-:.]/g, "").replace("Z", "Z")}-${suffix}`;
  const manifest = { ...preview, publishRevision: revision };
  delete manifest.preview;
  manifest.photos = manifest.photos.map((photo) => ({
    ...photo,
    status: undefined,
    updatedAt: timestamp,
    datePublished: photo.datePublished || timestamp.slice(0, 10),
  }));
  manifest.photos.forEach((photo) => { delete photo.status; });
  const body = JSON.stringify(manifest, null, 2) + "\n";
  const versionedKey = `photography/manifests/${revision}.json`;
  if (await env.PHOTO_PUBLIC.head(versionedKey)) throw new HttpError(409, "revision_exists", "Publish revision already exists.");
  const oldCurrent = await env.PHOTO_PUBLIC.get("photography/manifests/current.json");
  if (!oldCurrent) throw new HttpError(503, "current_manifest_missing", "Current manifest is unavailable; publish stopped.");
  const oldBody = await oldCurrent.arrayBuffer();
  await env.PHOTO_PUBLIC.put(versionedKey, body, {
    httpMetadata: { contentType: "application/json; charset=utf-8", cacheControl: "public, max-age=31536000, immutable" },
  });
  const versioned = await env.PHOTO_PUBLIC.get(versionedKey);
  if (!versioned || await versioned.text() !== body) throw new HttpError(503, "manifest_verification_failed", "Versioned manifest verification failed; public pointer was not changed.");
  await env.PHOTO_PUBLIC.put("photography/manifests/current.json", body, {
    httpMetadata: { contentType: "application/json; charset=utf-8", cacheControl: "public, max-age=60, must-revalidate" },
  });
  const current = await env.PHOTO_PUBLIC.get("photography/manifests/current.json");
  if (!current || await current.text() !== body) {
    await env.PHOTO_PUBLIC.put("photography/manifests/current.json", oldBody, oldCurrent.httpMetadata ? { httpMetadata: oldCurrent.httpMetadata } : undefined);
    throw new HttpError(503, "current_manifest_failed", "Current manifest update failed and the prior pointer was restored.");
  }
  try {
    const statements = [];
    for (const photo of state.photos) {
      const desired = { ...photo, status: photo.status === "archived" ? "archived" : "published" };
      statements.push(photoUpdate(env.PHOTOGRAPHY_DB, desired, timestamp));
    }
    statements.push(env.PHOTOGRAPHY_DB.prepare("DELETE FROM photo_drafts"));
    statements.push(env.PHOTOGRAPHY_DB.prepare(`INSERT INTO photo_publish_revisions (
      revision, manifest_object_key, photo_count, created_by_sub, created_at
    ) VALUES (?, ?, ?, ?, ?)`)
      .bind(revision, versionedKey, manifest.photos.length, identity.sub, timestamp));
    statements.push(env.PHOTOGRAPHY_DB.prepare(
      "UPDATE photography_admin_state SET collection_revision = collection_revision + 1, updated_at = ? WHERE singleton = 1",
    ).bind(timestamp));
    await env.PHOTOGRAPHY_DB.batch(statements);
  } catch (error) {
    await env.PHOTO_PUBLIC.put("photography/manifests/current.json", oldBody, {
      httpMetadata: oldCurrent.httpMetadata || { contentType: "application/json; charset=utf-8", cacheControl: "public, max-age=60, must-revalidate" },
    });
    throw new HttpError(503, "publish_database_failed", "Database commit failed and the previous public manifest was restored.");
  }
  return { revision, manifestObjectKey: versionedKey, photoCount: manifest.photos.length, draftChanges: draftCount, publishedAt: timestamp };
}
