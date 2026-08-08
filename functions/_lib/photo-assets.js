import { HttpError } from "./http.js";
import { getEffectivePhoto } from "./photo-admin-store.js";
import { inspectJpegFile } from "./jpeg.js";

const VARIANTS = Object.freeze({
  thumbnail: 480,
  preview: 1280,
  display: 2200,
  download: 1800,
});

function now() { return new Date().toISOString(); }

async function sha256Hex(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function aspectDifference(a, b) {
  const first = a.width / a.height;
  const second = b.width / b.height;
  return Math.abs(first - second) / first;
}

function derivativeKey(photoId, version, variant) {
  return `photography/derivatives/${variant}/${photoId}-v${version}-${variant}.jpg`;
}

export async function attachAssetPackage(env, id, request, identity) {
  const type = request.headers.get("content-type") || "";
  if (!type.toLowerCase().startsWith("multipart/form-data")) {
    throw new HttpError(415, "unsupported_media", "Expected multipart/form-data.");
  }
  const length = Number(request.headers.get("content-length") || 0);
  if (length > 70 * 1024 * 1024) throw new HttpError(413, "upload_too_large", "Upload package is too large.");
  const form = await request.formData();
  const allowedParts = new Set(["master", "thumbnail", "preview", "display", "download", "expectedUpdatedAt"]);
  for (const key of form.keys()) if (!allowedParts.has(key)) throw new HttpError(400, "unknown_upload_part", `Unknown upload part: ${key}`);
  const current = await getEffectivePhoto(env.PHOTOGRAPHY_DB, id);
  if (!form.get("expectedUpdatedAt") || form.get("expectedUpdatedAt") !== current.updatedAt) {
    throw new HttpError(409, "edit_conflict", "This photograph changed after the upload began.", { current });
  }
  const master = form.get("master");
  const masterInfo = await inspectJpegFile(master);
  const files = {};
  const infos = {};
  for (const [variant, maximum] of Object.entries(VARIANTS)) {
    const file = form.get(variant);
    const info = await inspectJpegFile(file);
    if (Math.max(info.width, info.height) > maximum) {
      throw new HttpError(422, "invalid_derivative_size", `${variant} exceeds its ${maximum}px long-edge limit.`, { [variant]: "Dimensions are too large." });
    }
    if (aspectDifference(masterInfo, info) > 0.012) {
      throw new HttpError(422, "invalid_derivative_aspect", `${variant} does not preserve the master aspect ratio.`, { [variant]: "Aspect ratio mismatch." });
    }
    files[variant] = file;
    infos[variant] = info;
  }
  const latest = await env.PHOTOGRAPHY_DB.prepare(
    "SELECT COALESCE(MAX(asset_version), 0) AS value FROM photo_asset_versions WHERE photo_id = ?",
  ).bind(id).first();
  const version = Math.max(Number(latest?.value || 0) + 1, current.assetVersion || 1);
  const masterBuffer = await master.arrayBuffer();
  const sourceHash = await sha256Hex(masterBuffer);
  const masterKey = `photography/originals/private/${id}/v${version}/master.jpg`;
  const createdAt = now();

  const existingMaster = await env.PHOTO_MASTERS.head(masterKey);
  if (existingMaster) throw new HttpError(409, "immutable_asset_exists", "The next master version key already exists; upload stopped.");
  for (const variant of Object.keys(VARIANTS)) {
    if (await env.PHOTO_PUBLIC.head(derivativeKey(id, version, variant))) {
      throw new HttpError(409, "immutable_asset_exists", `The next ${variant} key already exists; upload stopped.`);
    }
  }

  await env.PHOTOGRAPHY_DB.prepare(`INSERT INTO photo_asset_versions (
    photo_id, asset_version, master_object_key, source_filename, source_hash,
    original_width, original_height, source_bytes, processing_state, processing_error, created_at
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'processing', NULL, ?)`)
    .bind(id, version, masterKey, String(master.name || "master.jpg").slice(0, 255), sourceHash,
      masterInfo.width, masterInfo.height, masterInfo.bytes, createdAt).run();

  try {
    await env.PHOTO_MASTERS.put(masterKey, masterBuffer, {
      httpMetadata: { contentType: "image/jpeg", cacheControl: "private, no-store" },
      customMetadata: { photoId: id, assetVersion: String(version), sha256: sourceHash },
    });
    const derivativeRows = [];
    for (const variant of Object.keys(VARIANTS)) {
      const key = derivativeKey(id, version, variant);
      const file = files[variant];
      const httpMetadata = {
        contentType: "image/jpeg",
        cacheControl: "public, max-age=31536000, immutable",
      };
      if (variant === "download") httpMetadata.contentDisposition = `attachment; filename="${id}-v${version}.jpg"`;
      const object = await env.PHOTO_PUBLIC.put(key, await file.arrayBuffer(), {
        httpMetadata,
      });
      const head = await env.PHOTO_PUBLIC.head(key);
      if (!head || head.size !== infos[variant].bytes) throw new Error(`${variant} verification failed`);
      derivativeRows.push(env.PHOTOGRAPHY_DB.prepare(`INSERT INTO photo_asset_derivatives (
        photo_id, asset_version, variant, object_key, width, height, bytes, etag, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`)
        .bind(id, version, variant, key, infos[variant].width, infos[variant].height,
          infos[variant].bytes, object?.etag || head.etag || null, createdAt));
    }
    const draftPayload = { ...current, status: "draft", assetVersion: version };
    delete draftPayload.hasDraft;
    delete draftPayload.publishedStatus;
    delete draftPayload.processingState;
    await env.PHOTOGRAPHY_DB.batch([
      ...derivativeRows,
      env.PHOTOGRAPHY_DB.prepare("UPDATE photo_asset_versions SET processing_state = 'ready' WHERE photo_id = ? AND asset_version = ?")
        .bind(id, version),
      env.PHOTOGRAPHY_DB.prepare(`INSERT INTO photo_drafts (
        photo_id, payload_json, base_updated_at, revision, updated_by_sub, created_at, updated_at
      ) VALUES (?, ?, ?, 1, ?, ?, ?)
      ON CONFLICT(photo_id) DO UPDATE SET payload_json = excluded.payload_json,
        revision = photo_drafts.revision + 1, updated_by_sub = excluded.updated_by_sub,
        updated_at = excluded.updated_at`)
        .bind(id, JSON.stringify(draftPayload), current.updatedAt, identity.sub, createdAt, createdAt),
      env.PHOTOGRAPHY_DB.prepare("UPDATE photography_admin_state SET collection_revision = collection_revision + 1, updated_at = ? WHERE singleton = 1")
        .bind(createdAt),
    ]);
  } catch (error) {
    await env.PHOTOGRAPHY_DB.prepare(
      "UPDATE photo_asset_versions SET processing_state = 'failed', processing_error = ? WHERE photo_id = ? AND asset_version = ?",
    ).bind(String(error).slice(0, 500), id, version).run();
    throw new HttpError(503, "asset_processing_failed", "Asset package could not be stored and verified. The previous version remains active.");
  }
  return {
    photoId: id,
    assetVersion: version,
    processingState: "ready",
    master: { width: masterInfo.width, height: masterInfo.height, bytes: masterInfo.bytes },
    derivatives: infos,
  };
}
