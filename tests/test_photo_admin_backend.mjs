import assert from "node:assert/strict";
import test from "node:test";
import { webcrypto } from "node:crypto";

globalThis.crypto ||= webcrypto;

const { requireOwner } = await import("../functions/_lib/access-auth.js");
const { inspectJpeg, inspectJpegFile, MAX_IMAGE_BYTES } = await import("../functions/_lib/jpeg.js");

function base64url(value) {
  const bytes = typeof value === "string" ? new TextEncoder().encode(value) : new Uint8Array(value);
  return Buffer.from(bytes).toString("base64url");
}

async function fixture() {
  const pair = await crypto.subtle.generateKey(
    { name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" },
    true,
    ["sign", "verify"],
  );
  const jwk = await crypto.subtle.exportKey("jwk", pair.publicKey);
  jwk.kid = `test-${crypto.randomUUID()}`;
  const env = {
    CF_ACCESS_TEAM_DOMAIN: "example-team.cloudflareaccess.com",
    CF_ACCESS_AUD: "studio-audience",
    PHOTO_ADMIN_OWNER_EMAILS: "owner@example.com",
  };
  const token = async (overrides = {}) => {
    const header = base64url(JSON.stringify({ alg: "RS256", typ: "JWT", kid: jwk.kid }));
    const claims = base64url(JSON.stringify({
      iss: "https://example-team.cloudflareaccess.com",
      aud: ["studio-audience"],
      sub: "owner-sub",
      email: "owner@example.com",
      exp: Math.floor(Date.now() / 1000) + 300,
      ...overrides,
    }));
    const signature = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", pair.privateKey, new TextEncoder().encode(`${header}.${claims}`));
    return `${header}.${claims}.${base64url(signature)}`;
  };
  return { env, jwk, token };
}

test("Access JWT accepts only the configured owner", async () => {
  const { env, jwk, token } = await fixture();
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({ keys: [jwk] }), { status: 200 });
  try {
    const owner = await requireOwner(new Request("https://kexingyan.com/api/photo-admin/photos", {
      headers: { "Cf-Access-Jwt-Assertion": await token() },
    }), env);
    assert.equal(owner.email, "owner@example.com");
    await assert.rejects(
      requireOwner(new Request("https://kexingyan.com/api/photo-admin/photos", {
        headers: { "Cf-Access-Jwt-Assertion": await token({ email: "other@example.com" }) },
      }), env),
      (error) => error.status === 403 && error.code === "owner_forbidden",
    );
  } finally { globalThis.fetch = originalFetch; }
});

test("Access JWT rejects wrong issuer, audience, expiry, and signature", async () => {
  const { env, jwk, token } = await fixture();
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({ keys: [jwk] }), { status: 200 });
  try {
    await assert.rejects(
      requireOwner(new Request("https://kexingyan.com", { headers: { "Cf-Access-Jwt-Assertion": await token({ aud: ["wrong"] }) } }), env),
      (error) => error.status === 401,
    );
    await assert.rejects(
      requireOwner(new Request("https://kexingyan.com", { headers: { "Cf-Access-Jwt-Assertion": await token({ iss: "https://wrong.cloudflareaccess.com" }) } }), env),
      (error) => error.status === 401,
    );
    await assert.rejects(
      requireOwner(new Request("https://kexingyan.com", { headers: { "Cf-Access-Jwt-Assertion": await token({ exp: 1 }) } }), env),
      (error) => error.code === "access_token_expired",
    );
    const valid = await token();
    const tokenParts = valid.split(".");
    const signatureBytes = Buffer.from(tokenParts[2], "base64url");
    signatureBytes[0] ^= 0x01;
    const tampered = `${tokenParts[0]}.${tokenParts[1]}.${signatureBytes.toString("base64url")}`;
    await assert.rejects(
      requireOwner(new Request("https://kexingyan.com", { headers: { "Cf-Access-Jwt-Assertion": tampered } }), env),
      (error) => error.code === "invalid_access_token",
    );
  } finally { globalThis.fetch = originalFetch; }
});

function jpeg(width = 2, height = 2, includeScan = true) {
  const bytes = [
    0xff, 0xd8,
    0xff, 0xc0, 0x00, 0x0b, 0x08, height >> 8, height & 255, width >> 8, width & 255, 0x01, 0x01, 0x11, 0x00,
  ];
  if (includeScan) bytes.push(0xff, 0xda, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3f, 0x00, 0x00);
  bytes.push(0xff, 0xd9);
  return Uint8Array.from(bytes).buffer;
}

test("JPEG validation checks MIME, structure, and limits", () => {
  assert.deepEqual(inspectJpeg(jpeg(), "image/jpeg"), { width: 2, height: 2, bytes: 28 });
  assert.throws(() => inspectJpeg(jpeg(), "text/plain"), (error) => error.status === 415);
  assert.throws(() => inspectJpeg(new Uint8Array([1, 2, 3, 4]).buffer, "image/jpeg"), (error) => error.code === "invalid_jpeg");
  assert.throws(() => inspectJpeg(jpeg(12001, 2), "image/jpeg"), (error) => error.code === "image_dimensions_exceeded");
  assert.throws(() => inspectJpeg(jpeg(2, 2, false), "image/jpeg"), (error) => error.code === "jpeg_decode_failed");
});

test("upload file validation rejects oversized and fake JPEGs", async () => {
  await assert.rejects(
    inspectJpegFile(new File([new Uint8Array(MAX_IMAGE_BYTES + 1)], "large.jpg", { type: "image/jpeg" })),
    (error) => error.status === 413,
  );
  await assert.rejects(
    inspectJpegFile(new File(["plain text"], "fake.jpg", { type: "image/jpeg" })),
    (error) => error.code === "invalid_jpeg",
  );
});
