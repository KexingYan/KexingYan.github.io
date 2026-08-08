import { HttpError } from "./http.js";

export const MAX_IMAGE_BYTES = 50 * 1024 * 1024;
export const MAX_IMAGE_EDGE = 12000;
export const MAX_IMAGE_PIXELS = 80_000_000;

export function inspectJpeg(buffer, declaredType = "") {
  const bytes = new Uint8Array(buffer);
  if (declaredType.toLowerCase() !== "image/jpeg") {
    throw new HttpError(415, "unsupported_media", "Only JPEG uploads are accepted.");
  }
  if (bytes.byteLength < 4 || bytes[0] !== 0xff || bytes[1] !== 0xd8 || bytes.at(-2) !== 0xff || bytes.at(-1) !== 0xd9) {
    throw new HttpError(415, "invalid_jpeg", "File does not have a valid JPEG signature.");
  }
  let offset = 2;
  let width = 0;
  let height = 0;
  let hasScan = false;
  while (offset + 3 < bytes.length) {
    if (bytes[offset] !== 0xff) { offset += 1; continue; }
    while (bytes[offset] === 0xff) offset += 1;
    const marker = bytes[offset++];
    if (marker === 0xd9) break;
    if (marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) continue;
    if (offset + 1 >= bytes.length) break;
    const length = (bytes[offset] << 8) | bytes[offset + 1];
    if (length < 2 || offset + length > bytes.length) {
      throw new HttpError(415, "malformed_jpeg", "JPEG segment structure is malformed.");
    }
    if (marker === 0xda) {
      hasScan = true;
      break;
    }
    const isSof = [0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf].includes(marker);
    if (isSof && length >= 7) {
      height = (bytes[offset + 3] << 8) | bytes[offset + 4];
      width = (bytes[offset + 5] << 8) | bytes[offset + 6];
    }
    offset += length;
  }
  if (!width || !height || !hasScan) throw new HttpError(415, "jpeg_decode_failed", "JPEG structure or dimensions could not be decoded.");
  if (width > MAX_IMAGE_EDGE || height > MAX_IMAGE_EDGE || width * height > MAX_IMAGE_PIXELS) {
    throw new HttpError(422, "image_dimensions_exceeded", "Image exceeds the 12,000px or 80MP limit.");
  }
  return { width, height, bytes: bytes.byteLength };
}

export async function inspectJpegFile(file) {
  if (!(file instanceof File)) throw new HttpError(400, "image_missing", "A JPEG file is required.");
  if (file.size <= 0 || file.size > MAX_IMAGE_BYTES) {
    throw new HttpError(413, "image_too_large", "JPEG must be no larger than 50 MiB.");
  }
  return inspectJpeg(await file.arrayBuffer(), file.type);
}
