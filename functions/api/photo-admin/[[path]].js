import { requireOwner } from "../../_lib/access-auth.js";
import { errorResponse, HttpError, json, readJson, requireMutationOrigin } from "../../_lib/http.js";
import {
  archiveDraft, createDraft, listArchive, reorderPhotos, saveDraft, updateSeries,
} from "../../_lib/photo-admin-store.js";
import { attachAssetPackage } from "../../_lib/photo-assets.js";
import { buildPreview, publishAll } from "../../_lib/photo-publish.js";

function routeParts(request) {
  const pathname = new URL(request.url).pathname.replace(/^\/api\/photo-admin\/?/, "");
  return pathname.split("/").filter(Boolean).map(decodeURIComponent);
}

function ensureBindings(env) {
  for (const name of ["PHOTOGRAPHY_DB", "PHOTO_PUBLIC", "PHOTO_MASTERS"]) {
    if (!env[name]) throw new HttpError(503, "binding_missing", `Required server binding ${name} is unavailable.`);
  }
}

async function handle(request, env, identity) {
  ensureBindings(env);
  const parts = routeParts(request);
  const method = request.method.toUpperCase();

  if (method === "GET" && (parts.length === 0 || parts.join("/") === "photos")) {
    const state = await listArchive(env);
    const requestedStatus = new URL(request.url).searchParams.get("status");
    if (requestedStatus) state.photos = state.photos.filter((photo) => photo.status === requestedStatus);
    return json(state);
  }
  if (method === "POST" && parts.join("/") === "photos") {
    return json({ photo: await createDraft(env, await readJson(request), identity) }, 201);
  }
  if (method === "POST" && parts.join("/") === "photos/reorder") {
    return json(await reorderPhotos(env, await readJson(request), identity));
  }
  if (method === "GET" && parts.join("/") === "preview") {
    return json(await buildPreview(env));
  }
  if (method === "POST" && parts.join("/") === "publish") {
    const input = await readJson(request);
    if (input.confirm !== true) throw new HttpError(422, "confirmation_required", "Publish requires explicit confirmation.");
    const state = await listArchive(env);
    if (Number(input.expectedRevision) !== state.revision) {
      throw new HttpError(409, "publish_conflict", "Archive changed after the publish summary was shown.", { currentRevision: state.revision });
    }
    return json(await publishAll(env, identity, state.revision));
  }
  if (parts[0] === "series" && parts[1] && method === "PATCH" && parts.length === 2) {
    return json({ series: await updateSeries(env, parts[1], await readJson(request)) });
  }
  if (parts[0] === "photos" && parts[1]) {
    const id = parts[1];
    if (!/^P\d{3,}$/.test(id)) throw new HttpError(404, "photo_not_found", "Photograph was not found.");
    if (method === "GET" && parts.length === 2) {
      const state = await listArchive(env);
      const photo = state.photos.find((item) => item.id === id);
      if (!photo) throw new HttpError(404, "photo_not_found", "Photograph was not found.");
      return json({ photo });
    }
    if (method === "PATCH" && parts.length === 2) return json({ photo: await saveDraft(env, id, await readJson(request), identity) });
    if (method === "POST" && parts[2] === "archive" && parts.length === 3) {
      const input = await readJson(request);
      if (input.confirm !== true) throw new HttpError(422, "confirmation_required", "Archive requires explicit confirmation.");
      return json({ photo: await archiveDraft(env, id, input, identity) });
    }
    if (method === "POST" && ["assets", "replace"].includes(parts[2]) && parts.length === 3) {
      if (parts[2] === "replace" && request.headers.get("x-photography-confirm-replace") !== "replace") {
        throw new HttpError(422, "confirmation_required", "Replacement requires explicit confirmation.");
      }
      return json(await attachAssetPackage(env, id, request, identity));
    }
  }
  throw new HttpError(404, "route_not_found", "Photography admin route was not found.");
}

export async function onRequest(context) {
  const requestId = crypto.randomUUID();
  try {
    if (context.request.method === "OPTIONS") {
      throw new HttpError(405, "method_not_allowed", "Cross-origin preflight is not supported.");
    }
    requireMutationOrigin(context.request, context.env);
    const identity = await requireOwner(context.request, context.env);
    return await handle(context.request, context.env, identity);
  } catch (error) {
    console.error(JSON.stringify({ requestId, code: error?.code || "internal_error", status: error?.status || 500 }));
    return errorResponse(error, requestId);
  }
}
