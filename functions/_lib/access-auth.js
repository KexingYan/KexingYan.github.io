import { HttpError } from "./http.js";

const encoder = new TextEncoder();
const keyCache = new Map();

function decodeBase64Url(value) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  const binary = atob(padded);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

function parsePart(value, label) {
  try {
    return JSON.parse(new TextDecoder().decode(decodeBase64Url(value)));
  } catch {
    throw new HttpError(401, "invalid_access_token", `Access token ${label} is malformed.`);
  }
}

function normalizedTeamDomain(env) {
  const configured = (env.CF_ACCESS_TEAM_DOMAIN || "").trim().replace(/^https?:\/\//, "").replace(/\/$/, "");
  if (!configured || !/^[a-z0-9.-]+\.cloudflareaccess\.com$/i.test(configured)) {
    throw new HttpError(503, "access_not_configured", "Access validation is not configured.");
  }
  return configured;
}

async function loadKey(teamDomain, kid) {
  const cacheKey = `${teamDomain}:${kid}`;
  const cached = keyCache.get(cacheKey);
  if (cached && cached.expiresAt > Date.now()) return cached.key;
  const response = await fetch(`https://${teamDomain}/cdn-cgi/access/certs`, {
    cf: { cacheTtl: 300, cacheEverything: true },
  });
  if (!response.ok) throw new HttpError(503, "access_keys_unavailable", "Access signing keys are unavailable.");
  const body = await response.json();
  const jwk = body.keys?.find((candidate) => candidate.kid === kid && candidate.kty === "RSA");
  if (!jwk) throw new HttpError(401, "unknown_access_key", "Access token signing key is not recognized.");
  const key = await crypto.subtle.importKey(
    "jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"],
  );
  keyCache.set(cacheKey, { key, expiresAt: Date.now() + 5 * 60 * 1000 });
  return key;
}

export async function requireOwner(request, env) {
  const token = request.headers.get("Cf-Access-Jwt-Assertion");
  if (!token) throw new HttpError(401, "access_token_missing", "Cloudflare Access authentication is required.");
  const parts = token.split(".");
  if (parts.length !== 3) throw new HttpError(401, "invalid_access_token", "Access token is malformed.");
  const header = parsePart(parts[0], "header");
  const claims = parsePart(parts[1], "claims");
  if (header.alg !== "RS256" || typeof header.kid !== "string") {
    throw new HttpError(401, "invalid_access_token", "Access token algorithm is not accepted.");
  }
  const teamDomain = normalizedTeamDomain(env);
  const expectedIssuer = `https://${teamDomain}`;
  const now = Math.floor(Date.now() / 1000);
  const audiences = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
  if (claims.iss !== expectedIssuer || !audiences.includes(env.CF_ACCESS_AUD)) {
    throw new HttpError(401, "invalid_access_token", "Access token issuer or audience is invalid.");
  }
  if (!Number.isFinite(claims.exp) || claims.exp <= now || (claims.nbf && claims.nbf > now + 30)) {
    throw new HttpError(401, "access_token_expired", "Access session has expired.");
  }
  if (!claims.sub || !claims.email) {
    throw new HttpError(401, "identity_missing", "Access token does not contain an authenticated identity.");
  }
  const key = await loadKey(teamDomain, header.kid);
  const verified = await crypto.subtle.verify(
    "RSASSA-PKCS1-v1_5",
    key,
    decodeBase64Url(parts[2]),
    encoder.encode(`${parts[0]}.${parts[1]}`),
  );
  if (!verified) throw new HttpError(401, "invalid_access_token", "Access token signature is invalid.");
  const owners = new Set((env.PHOTO_ADMIN_OWNER_EMAILS || "")
    .split(",").map((value) => value.trim().toLowerCase()).filter(Boolean));
  if (!owners.size) throw new HttpError(503, "owner_not_configured", "Studio owner allowlist is not configured.");
  if (!owners.has(String(claims.email).toLowerCase())) {
    throw new HttpError(403, "owner_forbidden", "This authenticated identity is not authorized for Photography Studio.");
  }
  return { sub: String(claims.sub), email: String(claims.email) };
}
