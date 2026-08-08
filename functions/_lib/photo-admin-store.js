import { HttpError } from "./http.js";

export const EDITABLE_FIELDS = Object.freeze([
  "slug", "title", "seriesId", "dateTaken", "locationDisplay", "caption", "alt",
  "camera", "lens", "focalLength", "aperture", "shutterSpeed", "iso",
  "orientation", "layoutHint", "featured", "allowDownload", "sortOrder",
]);

const LAYOUTS = new Set([
  "hero", "wide", "landscape", "portrait-left", "portrait-right",
  "pair-left", "pair-right", "panorama", "standard",
]);

function isoNow() { return new Date().toISOString(); }
function bool(value) { return value === true || value === 1; }
function clone(value) { return JSON.parse(JSON.stringify(value)); }

function rowToPhoto(row) {
  return {
    id: row.id,
    slug: row.slug,
    title: row.title,
    seriesId: row.series_id,
    dateTaken: row.date_taken,
    datePublished: row.date_published,
    locationDisplay: row.location_display,
    caption: row.caption,
    alt: row.alt,
    camera: row.camera,
    lens: row.lens,
    focalLength: row.focal_length,
    aperture: row.aperture,
    shutterSpeed: row.shutter_speed,
    iso: row.iso,
    orientation: row.orientation,
    layoutHint: row.layout_hint,
    featured: bool(row.featured),
    allowDownload: bool(row.allow_download),
    sortOrder: row.sort_order,
    status: row.status,
    assetVersion: row.asset_version,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function rowToSeries(row) {
  return {
    id: row.id,
    number: row.number_label,
    title: row.title,
    description: row.description,
    sortOrder: row.sort_order,
    updatedAt: row.updated_at,
  };
}

export function slugify(value) {
  return String(value || "").normalize("NFKD").replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-|-$/g, "").toLowerCase() || "untitled-photograph";
}

function text(value, maximum, label, required = false) {
  const output = value == null ? "" : String(value).trim();
  if (required && !output) throw new HttpError(422, "validation_failed", `${label} is required.`, { [label]: "Required." });
  if (output.length > maximum) throw new HttpError(422, "validation_failed", `${label} is too long.`, { [label]: `Maximum ${maximum} characters.` });
  return output;
}

export function validatePhoto(input, { forPublish = false } = {}) {
  const photo = clone(input);
  photo.title = text(photo.title, 160, "title", true);
  photo.slug = slugify(photo.slug || photo.title);
  photo.seriesId = text(photo.seriesId, 80, "seriesId", true);
  photo.alt = text(photo.alt, 500, "alt", forPublish);
  photo.caption = text(photo.caption, 1200, "caption");
  photo.locationDisplay = text(photo.locationDisplay, 160, "locationDisplay");
  for (const field of ["camera", "lens", "focalLength", "aperture", "shutterSpeed"]) {
    photo[field] = photo[field] == null || photo[field] === "" ? null : text(photo[field], 200, field);
  }
  if (!LAYOUTS.has(photo.layoutHint)) throw new HttpError(422, "validation_failed", "Layout is invalid.", { layoutHint: "Invalid layout." });
  if (!["portrait", "landscape"].includes(photo.orientation)) throw new HttpError(422, "validation_failed", "Orientation is invalid.", { orientation: "Invalid orientation." });
  if (photo.dateTaken && !/^\d{4}-\d{2}-\d{2}$/.test(photo.dateTaken)) throw new HttpError(422, "validation_failed", "Date must use YYYY-MM-DD.", { dateTaken: "Invalid date." });
  photo.featured = Boolean(photo.featured);
  photo.allowDownload = Boolean(photo.allowDownload);
  photo.sortOrder = Number.isInteger(photo.sortOrder) && photo.sortOrder >= 0 ? photo.sortOrder : 999;
  photo.iso = photo.iso == null || photo.iso === "" ? null : Number(photo.iso);
  if (photo.iso != null && (!Number.isInteger(photo.iso) || photo.iso < 1)) throw new HttpError(422, "validation_failed", "ISO is invalid.", { iso: "Positive integer required." });
  return photo;
}

async function assertSeries(db, id) {
  const row = await db.prepare("SELECT id FROM photo_series WHERE id = ?").bind(id).first();
  if (!row) throw new HttpError(422, "unknown_series", "Selected series does not exist.", { seriesId: "Unknown series." });
}

async function loadRows(db) {
  const [photoResult, draftResult, seriesResult, state] = await Promise.all([
    db.prepare("SELECT * FROM photos ORDER BY series_id, sort_order, id").all(),
    db.prepare("SELECT * FROM photo_drafts").all(),
    db.prepare("SELECT * FROM photo_series ORDER BY sort_order, id").all(),
    db.prepare("SELECT collection_revision, updated_at FROM photography_admin_state WHERE singleton = 1").first(),
  ]);
  const drafts = new Map((draftResult.results || []).map((row) => [row.photo_id, row]));
  const photos = (photoResult.results || []).map((row) => {
    const base = rowToPhoto(row);
    const draft = drafts.get(base.id);
    if (!draft) return { ...base, hasDraft: false, publishedStatus: base.status };
    return {
      ...base,
      ...JSON.parse(draft.payload_json),
      status: JSON.parse(draft.payload_json).status || "draft",
      updatedAt: draft.updated_at,
      hasDraft: true,
      draftRevision: draft.revision,
      publishedStatus: base.status,
    };
  });
  return {
    photos,
    series: (seriesResult.results || []).map(rowToSeries),
    revision: state?.collection_revision || 1,
    updatedAt: state?.updated_at || null,
  };
}

export async function listArchive(env) {
  const state = await loadRows(env.PHOTOGRAPHY_DB);
  const [assetRows, derivativeRows, currentObject, lastPublish] = await Promise.all([
    env.PHOTOGRAPHY_DB.prepare(
    "SELECT photo_id, asset_version, processing_state, original_width, original_height FROM photo_asset_versions ORDER BY asset_version DESC",
    ).all(),
    env.PHOTOGRAPHY_DB.prepare(
      "SELECT photo_id, asset_version, variant, width, height, bytes FROM photo_asset_derivatives",
    ).all(),
    env.PHOTO_PUBLIC?.get("photography/manifests/current.json") || null,
    env.PHOTOGRAPHY_DB.prepare(
      "SELECT MAX(created_at) AS published_at FROM photo_publish_revisions",
    ).first(),
  ]);
  const assets = new Map();
  for (const row of assetRows.results || []) {
    const key = `${row.photo_id}:${row.asset_version}`;
    if (!assets.has(key)) assets.set(key, row);
  }
  const generatedImages = new Map();
  for (const row of derivativeRows.results || []) {
    const key = `${row.photo_id}:${row.asset_version}`;
    if (!generatedImages.has(key)) generatedImages.set(key, {});
    generatedImages.get(key)[row.variant] = {
      src: `https://images.kexingyan.com/photography/derivatives/${row.variant}/${row.photo_id}-v${row.asset_version}-${row.variant}.jpg`,
      width: row.width,
      height: row.height,
      bytes: row.bytes,
    };
  }
  let currentById = new Map();
  if (currentObject) {
    try {
      const currentManifest = await currentObject.json();
      currentById = new Map((currentManifest.photos || []).map((photo) => [photo.id, photo]));
    } catch { currentById = new Map(); }
  }
  state.photos = state.photos.map((photo) => {
    const asset = assets.get(`${photo.id}:${photo.assetVersion}`);
    return {
      ...photo,
      images: generatedImages.get(`${photo.id}:${photo.assetVersion}`) || currentById.get(photo.id)?.images || null,
      processingState: asset?.processing_state || "missing",
      originalWidth: asset?.original_width || null,
      originalHeight: asset?.original_height || null,
    };
  });
  return { ...state, lastPublishedAt: lastPublish?.published_at || null };
}

export async function getEffectivePhoto(db, id) {
  const baseRow = await db.prepare("SELECT * FROM photos WHERE id = ?").bind(id).first();
  if (!baseRow) throw new HttpError(404, "photo_not_found", "Photograph was not found.");
  const base = rowToPhoto(baseRow);
  const draft = await db.prepare("SELECT * FROM photo_drafts WHERE photo_id = ?").bind(id).first();
  if (!draft) return { ...base, hasDraft: false, publishedStatus: base.status };
  const payload = JSON.parse(draft.payload_json);
  return {
    ...base,
    ...payload,
    status: payload.status || "draft",
    updatedAt: draft.updated_at,
    hasDraft: true,
    draftRevision: draft.revision,
    publishedStatus: base.status,
  };
}

export async function createDraft(env, input, identity) {
  const db = env.PHOTOGRAPHY_DB;
  const now = isoNow();
  const next = await db.prepare("SELECT COALESCE(MAX(CAST(SUBSTR(id, 2) AS INTEGER)), 0) + 1 AS value FROM photos").first();
  const id = `P${String(next.value).padStart(3, "0")}`;
  const photo = validatePhoto({
    ...input,
    id,
    orientation: input.orientation || "landscape",
    layoutHint: input.layoutHint || "standard",
    featured: Boolean(input.featured),
    allowDownload: input.allowDownload !== false,
    sortOrder: Number.isInteger(input.sortOrder) ? input.sortOrder : 999,
    status: "draft",
    assetVersion: 1,
    createdAt: now,
    updatedAt: now,
    datePublished: null,
  });
  await assertSeries(db, photo.seriesId);
  try {
    await db.batch([
      db.prepare(`INSERT INTO photos (
        id, slug, title, series_id, date_taken, date_published, location_display, caption, alt,
        camera, lens, focal_length, aperture, shutter_speed, iso, orientation, layout_hint,
        featured, allow_download, sort_order, status, asset_version, created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', 1, ?, ?)`)
        .bind(id, photo.slug, photo.title, photo.seriesId, photo.dateTaken || null,
          photo.locationDisplay, photo.caption, photo.alt, photo.camera, photo.lens,
          photo.focalLength, photo.aperture, photo.shutterSpeed, photo.iso,
          photo.orientation, photo.layoutHint, photo.featured ? 1 : 0,
          photo.allowDownload ? 1 : 0, photo.sortOrder, now, now),
      db.prepare("UPDATE photography_admin_state SET collection_revision = collection_revision + 1, updated_at = ? WHERE singleton = 1").bind(now),
    ]);
  } catch (error) {
    if (String(error).toLowerCase().includes("unique")) throw new HttpError(409, "slug_conflict", "A photograph already uses this slug.");
    throw error;
  }
  return { ...photo, hasDraft: true, publishedStatus: "draft", ownerSub: identity.sub };
}

export async function saveDraft(env, id, input, identity) {
  const db = env.PHOTOGRAPHY_DB;
  const current = await getEffectivePhoto(db, id);
  if (!input.expectedUpdatedAt || input.expectedUpdatedAt !== current.updatedAt) {
    throw new HttpError(409, "edit_conflict", "This photograph changed after it was opened.", { current });
  }
  const updated = validatePhoto({
    ...current,
    ...Object.fromEntries(EDITABLE_FIELDS.filter((field) => input[field] !== undefined).map((field) => [field, input[field]])),
  });
  updated.status = input.status === "archived" ? "archived" : "draft";
  updated.id = id;
  updated.assetVersion = current.assetVersion;
  await assertSeries(db, updated.seriesId);
  const now = isoNow();
  const payload = Object.fromEntries([
    ...EDITABLE_FIELDS,
    "id", "status", "assetVersion", "datePublished", "createdAt",
  ].map((field) => [field, updated[field]]));
  const statements = [
    db.prepare(`INSERT INTO photo_drafts (
      photo_id, payload_json, base_updated_at, revision, updated_by_sub, created_at, updated_at
    ) VALUES (?, ?, ?, 1, ?, ?, ?)
    ON CONFLICT(photo_id) DO UPDATE SET
      payload_json = excluded.payload_json,
      revision = photo_drafts.revision + 1,
      updated_by_sub = excluded.updated_by_sub,
      updated_at = excluded.updated_at`)
      .bind(id, JSON.stringify(payload), current.hasDraft ? current.baseUpdatedAt || current.createdAt : current.updatedAt, identity.sub, now, now),
  ];
  if (updated.featured) {
    const state = await loadRows(db);
    for (const other of state.photos.filter((photo) => photo.id !== id && photo.featured && photo.status !== "archived")) {
      const otherPayload = Object.fromEntries([
        ...EDITABLE_FIELDS, "id", "status", "assetVersion", "datePublished", "createdAt",
      ].map((field) => [field, other[field]]));
      otherPayload.featured = false;
      otherPayload.status = "draft";
      statements.push(db.prepare(`INSERT INTO photo_drafts (
        photo_id, payload_json, base_updated_at, revision, updated_by_sub, created_at, updated_at
      ) VALUES (?, ?, ?, 1, ?, ?, ?)
      ON CONFLICT(photo_id) DO UPDATE SET payload_json = excluded.payload_json,
        revision = photo_drafts.revision + 1, updated_by_sub = excluded.updated_by_sub,
        updated_at = excluded.updated_at`)
        .bind(other.id, JSON.stringify(otherPayload), other.updatedAt, identity.sub, now, now));
    }
  }
  statements.push(db.prepare("UPDATE photography_admin_state SET collection_revision = collection_revision + 1, updated_at = ? WHERE singleton = 1").bind(now));
  await db.batch(statements);
  return getEffectivePhoto(db, id);
}

export async function archiveDraft(env, id, input, identity) {
  const current = await getEffectivePhoto(env.PHOTOGRAPHY_DB, id);
  return saveDraft(env, id, { ...current, ...input, status: "archived", expectedUpdatedAt: input.expectedUpdatedAt }, identity);
}

export async function reorderPhotos(env, input, identity) {
  const state = await loadRows(env.PHOTOGRAPHY_DB);
  if (Number(input.expectedRevision) !== state.revision) {
    throw new HttpError(409, "reorder_conflict", "Archive order changed after it was loaded.", { currentRevision: state.revision });
  }
  const active = state.photos.filter((photo) => photo.seriesId === input.seriesId && photo.status !== "archived");
  const ids = Array.isArray(input.orderedPhotoIds) ? input.orderedPhotoIds : [];
  if (active.length !== ids.length || new Set(ids).size !== ids.length || active.some((photo) => !ids.includes(photo.id))) {
    throw new HttpError(422, "invalid_order", "Order must contain every active photograph in the series exactly once.");
  }
  const now = isoNow();
  const statements = ids.map((id, index) => {
    const current = active.find((photo) => photo.id === id);
    const payload = Object.fromEntries([
      ...EDITABLE_FIELDS, "id", "status", "assetVersion", "datePublished", "createdAt",
    ].map((field) => [field, current[field]]));
    payload.sortOrder = index + 1;
    payload.status = "draft";
    return env.PHOTOGRAPHY_DB.prepare(`INSERT INTO photo_drafts (
      photo_id, payload_json, base_updated_at, revision, updated_by_sub, created_at, updated_at
    ) VALUES (?, ?, ?, 1, ?, ?, ?)
    ON CONFLICT(photo_id) DO UPDATE SET payload_json = excluded.payload_json,
      revision = photo_drafts.revision + 1, updated_by_sub = excluded.updated_by_sub,
      updated_at = excluded.updated_at`)
      .bind(id, JSON.stringify(payload), current.updatedAt, identity.sub, now, now);
  });
  statements.push(env.PHOTOGRAPHY_DB.prepare(
    "UPDATE photography_admin_state SET collection_revision = collection_revision + 1, updated_at = ? WHERE singleton = 1 AND collection_revision = ?",
  ).bind(now, state.revision));
  await env.PHOTOGRAPHY_DB.batch(statements);
  return listArchive(env);
}

export async function updateSeries(env, id, input) {
  const current = await env.PHOTOGRAPHY_DB.prepare("SELECT * FROM photo_series WHERE id = ?").bind(id).first();
  if (!current) throw new HttpError(404, "series_not_found", "Series was not found.");
  if (!input.expectedUpdatedAt || input.expectedUpdatedAt !== current.updated_at) throw new HttpError(409, "series_conflict", "Series changed after it was opened.");
  const now = isoNow();
  const title = text(input.title ?? current.title, 160, "title", true);
  const description = text(input.description ?? current.description, 500, "description");
  await env.PHOTOGRAPHY_DB.batch([
    env.PHOTOGRAPHY_DB.prepare("UPDATE photo_series SET title = ?, description = ?, updated_at = ? WHERE id = ? AND updated_at = ?")
      .bind(title, description, now, id, current.updated_at),
    env.PHOTOGRAPHY_DB.prepare("UPDATE photography_admin_state SET collection_revision = collection_revision + 1, updated_at = ? WHERE singleton = 1").bind(now),
  ]);
  return rowToSeries(await env.PHOTOGRAPHY_DB.prepare("SELECT * FROM photo_series WHERE id = ?").bind(id).first());
}
