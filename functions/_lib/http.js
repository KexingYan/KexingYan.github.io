export class HttpError extends Error {
  constructor(status, code, message, fields = undefined) {
    super(message);
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

export function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "private, no-store",
      "x-content-type-options": "nosniff",
      ...extraHeaders,
    },
  });
}

export function errorResponse(error, requestId) {
  const status = error instanceof HttpError ? error.status : 500;
  const body = {
    error: {
      code: error instanceof HttpError ? error.code : "internal_error",
      message: error instanceof HttpError
        ? error.message
        : "The Photography service could not complete this request.",
      requestId,
    },
  };
  if (error instanceof HttpError && error.fields) body.error.fields = error.fields;
  return json(body, status);
}

export async function readJson(request, maximumBytes = 64 * 1024) {
  const type = request.headers.get("content-type") || "";
  if (!type.toLowerCase().startsWith("application/json")) {
    throw new HttpError(415, "unsupported_media", "Expected application/json.");
  }
  const length = Number(request.headers.get("content-length") || 0);
  if (length > maximumBytes) throw new HttpError(413, "request_too_large", "JSON request is too large.");
  const text = await request.text();
  if (new TextEncoder().encode(text).byteLength > maximumBytes) {
    throw new HttpError(413, "request_too_large", "JSON request is too large.");
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new HttpError(400, "invalid_json", "Request body is not valid JSON.");
  }
}

export function requireMutationOrigin(request, env) {
  if (["GET", "HEAD", "OPTIONS"].includes(request.method)) return;
  const origin = request.headers.get("origin");
  const allowed = new Set((env.PHOTO_ADMIN_ALLOWED_ORIGINS || "https://kexingyan.com")
    .split(",").map((value) => value.trim()).filter(Boolean));
  if (!origin || !allowed.has(origin)) {
    throw new HttpError(403, "origin_forbidden", "This request origin is not allowed.");
  }
}
