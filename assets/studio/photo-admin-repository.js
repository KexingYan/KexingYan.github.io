const STORAGE_KEY = "kx-photography-studio-v1";

export const PUBLIC_PHOTO_FIELDS = Object.freeze([
  "id", "slug", "title", "seriesId", "dateTaken", "datePublished",
  "locationDisplay", "caption", "alt", "camera", "lens", "focalLength",
  "aperture", "shutterSpeed", "iso", "orientation", "layoutHint",
  "featured", "allowDownload", "sortOrder", "assetVersion", "updatedAt", "images",
]);

export const PRIVATE_ONLY_FIELDS = Object.freeze([
  "masterObjectKey", "sourceFilename", "sourceHash", "sourcePath", "sourceBytes",
  "originalWidth", "originalHeight", "processingState", "localPreviewUrl",
]);

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function now() {
  return new Date().toISOString();
}

function slugify(value) {
  return value
    .normalize("NFKD")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .toLowerCase() || "untitled-photograph";
}

function nextPhotoId(photos) {
  const maximum = photos.reduce((highest, photo) => {
    const match = /^P(\d+)$/.exec(photo.id || "");
    return match ? Math.max(highest, Number(match[1])) : highest;
  }, 0);
  return `P${String(maximum + 1).padStart(3, "0")}`;
}

function assertRecord(photo) {
  if (!/^P\d{3,}$/.test(photo.id || "")) throw new Error("A stable photo ID is required.");
  if (!photo.title?.trim()) throw new Error("Title is required.");
  if (!photo.seriesId) throw new Error("Series is required.");
  if (!photo.alt?.trim()) throw new Error("Alt text is required.");
}

export function toPublicPhoto(photo) {
  const publicPhoto = {};
  PUBLIC_PHOTO_FIELDS.forEach((field) => {
    if (photo[field] !== undefined) publicPhoto[field] = clone(photo[field]);
  });
  return publicPhoto;
}

export function buildPublicManifest(state) {
  const visibleSeries = state.series
    .filter((series) => !series.hidden)
    .sort((a, b) => a.sortOrder - b.sortOrder)
    .map(({ hidden, coverPhotoId, sortOrder, ...series }) => clone(series));
  const seriesOrder = new Map(visibleSeries.map((series, index) => [series.id, index]));
  const photos = state.photos
    .filter((photo) => photo.status === "published" && seriesOrder.has(photo.seriesId))
    .sort((a, b) => {
      const seriesDifference = seriesOrder.get(a.seriesId) - seriesOrder.get(b.seriesId);
      return seriesDifference || a.sortOrder - b.sortOrder || a.id.localeCompare(b.id);
    })
    .map(toPublicPhoto);
  return {
    schemaVersion: 1,
    publishRevision: `local-studio-${state.revision}`,
    assetMode: "local",
    assetBase: "/assets/photography/generated",
    series: visibleSeries,
    photos,
  };
}

export function buildPreviewManifest(state) {
  const previewState = clone(state);
  previewState.photos = previewState.photos
    .filter((photo) => photo.status !== "archived")
    .map((photo) => ({ ...photo, status: "published" }));
  return buildPublicManifest(previewState);
}

function initialState(seed, publicManifest) {
  const publicById = new Map(publicManifest.photos.map((photo) => [photo.id, photo]));
  return {
    schemaVersion: 1,
    revision: 1,
    lastPublishedAt: seed.photos
      .map((photo) => photo.datePublished)
      .filter(Boolean)
      .sort()
      .at(-1) || null,
    series: seed.series.map((series, index) => ({
      ...clone(series),
      sortOrder: index + 1,
      coverPhotoId: null,
      hidden: false,
    })),
    photos: seed.photos.map((photo) => ({
      ...clone(photo),
      images: clone(publicById.get(photo.id)?.images || null),
      originalWidth: publicById.get(photo.id)?.images?.display?.width || null,
      originalHeight: publicById.get(photo.id)?.images?.display?.height || null,
      processingState: "ready",
    })),
  };
}

export class LocalPhotoAdminRepository {
  constructor(options = {}) {
    this.storage = options.storage || window.localStorage;
    this.seedUrl = options.seedUrl || "/data/photography/photos.seed.json";
    this.manifestUrl = options.manifestUrl || "/assets/photography/data/photos.json";
    this.storageKey = options.storageKey || STORAGE_KEY;
    this.memoryState = null;
  }

  async initialize() {
    const existing = this.storage?.getItem(this.storageKey);
    if (existing) return JSON.parse(existing);
    const [seedResponse, manifestResponse] = await Promise.all([
      fetch(this.seedUrl),
      fetch(this.manifestUrl),
    ]);
    if (!seedResponse.ok || !manifestResponse.ok) {
      throw new Error("Could not load the local Photography fixtures.");
    }
    const state = initialState(await seedResponse.json(), await manifestResponse.json());
    this.write(state);
    return clone(state);
  }

  read() {
    const raw = this.storage?.getItem(this.storageKey);
    if (raw) return JSON.parse(raw);
    if (this.memoryState) return clone(this.memoryState);
    throw new Error("Repository is not initialized.");
  }

  write(state) {
    this.memoryState = clone(state);
    this.storage?.setItem(this.storageKey, JSON.stringify(state));
  }

  async listPhotos() {
    return clone(this.read().photos);
  }

  async getPhoto(id) {
    const photo = this.read().photos.find((item) => item.id === id);
    return photo ? clone(photo) : null;
  }

  async saveDraft(input) {
    assertRecord(input);
    const state = this.read();
    const index = state.photos.findIndex((photo) => photo.id === input.id);
    const record = {
      ...(index >= 0 ? state.photos[index] : {}),
      ...clone(input),
      slug: input.slug || slugify(input.title),
      status: "draft",
      createdAt: input.createdAt || now(),
      updatedAt: now(),
    };
    if (index >= 0) state.photos[index] = record;
    else state.photos.push(record);
    state.revision += 1;
    this.write(state);
    return clone(record);
  }

  async publishPhoto(id) {
    const state = this.read();
    const photo = state.photos.find((item) => item.id === id);
    if (!photo) throw new Error("Photograph not found.");
    assertRecord(photo);
    if (!photo.images || photo.processingState !== "ready") {
      throw new Error("Run the offline ingest pipeline before publishing this photograph.");
    }
    photo.status = "published";
    photo.datePublished ||= new Date().toISOString().slice(0, 10);
    photo.updatedAt = now();
    state.lastPublishedAt = now();
    state.revision += 1;
    this.write(state);
    return clone(photo);
  }

  async archivePhoto(id) {
    const state = this.read();
    const photo = state.photos.find((item) => item.id === id);
    if (!photo) throw new Error("Photograph not found.");
    photo.status = "archived";
    photo.updatedAt = now();
    state.revision += 1;
    this.write(state);
    return clone(photo);
  }

  async reorderPhotos(seriesId, orderedIds) {
    const state = this.read();
    const current = state.photos
      .filter((photo) => photo.seriesId === seriesId && photo.status !== "archived")
      .map((photo) => photo.id);
    if (current.length !== orderedIds.length || current.some((id) => !orderedIds.includes(id))) {
      throw new Error("Reorder must include every active photograph in the series exactly once.");
    }
    orderedIds.forEach((id, index) => {
      state.photos.find((photo) => photo.id === id).sortOrder = index + 1;
    });
    state.revision += 1;
    this.write(state);
    return this.listPhotos();
  }

  async listSeries() {
    return clone(this.read().series.sort((a, b) => a.sortOrder - b.sortOrder));
  }

  async updateSeries(input) {
    const state = this.read();
    const index = state.series.findIndex((series) => series.id === input.id);
    if (index < 0) throw new Error("Series not found.");
    state.series[index] = { ...state.series[index], ...clone(input) };
    state.revision += 1;
    this.write(state);
    return clone(state.series[index]);
  }

  async reorderSeries(orderedIds) {
    const state = this.read();
    if (state.series.length !== orderedIds.length || state.series.some((series) => !orderedIds.includes(series.id))) {
      throw new Error("Reorder must include every series exactly once.");
    }
    orderedIds.forEach((id, index) => {
      state.series.find((series) => series.id === id).sortOrder = index + 1;
    });
    state.revision += 1;
    this.write(state);
    return this.listSeries();
  }

  async prepareUpload(files) {
    const state = this.read();
    const proposals = [];
    let nextId = nextPhotoId(state.photos);
    for (const file of files) {
      if (!file.type.startsWith("image/")) throw new Error(`${file.name} is not an image.`);
      const id = nextId;
      const number = Number(id.slice(1)) + 1;
      nextId = `P${String(number).padStart(3, "0")}`;
      proposals.push({
        id,
        sourceFilename: file.name,
        sourceBytes: file.size,
        mimeType: file.type,
        localPreviewUrl: URL.createObjectURL(file),
        title: file.name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " "),
        processingState: "awaiting-local-ingest",
      });
    }
    return {
      persistentUpload: false,
      message: "Selection is browser-session only. Use scripts/ingest_photography.py to create durable assets.",
      proposals,
    };
  }

  async exportPublicManifest() {
    return buildPublicManifest(this.read());
  }

  async exportPreviewManifest() {
    return buildPreviewManifest(this.read());
  }

  async resetLocalFixture() {
    this.storage?.removeItem(this.storageKey);
    this.memoryState = null;
    return this.initialize();
  }
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`/api/photo-admin${path}`, {
    credentials: "same-origin",
    headers: options.body instanceof FormData ? options.headers : {
      "content-type": "application/json",
      ...options.headers,
    },
    ...options,
  });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    const error = new Error(payload?.error?.message || `Studio request failed (${response.status}).`);
    error.code = payload?.error?.code || "request_failed";
    error.status = response.status;
    error.fields = payload?.error?.fields;
    if (response.status === 401) error.message = "Your Access session expired. Reload Studio to sign in again.";
    throw error;
  }
  return payload;
}

async function decodeJpeg(file) {
  if (file.type !== "image/jpeg") throw new Error(`${file.name} is not a JPEG.`);
  if (file.size > 50 * 1024 * 1024) throw new Error(`${file.name} exceeds the 50 MiB limit.`);
  const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  if (!bitmap.width || !bitmap.height || bitmap.width > 12000 || bitmap.height > 12000 || bitmap.width * bitmap.height > 80_000_000) {
    bitmap.close();
    throw new Error(`${file.name} exceeds the 12,000px or 80MP limit.`);
  }
  return bitmap;
}

async function readBasicExif(file) {
  const bytes = new Uint8Array(await file.slice(0, 1024 * 1024).arrayBuffer());
  const view = new DataView(bytes.buffer);
  let offset = 2;
  while (offset + 10 < bytes.length) {
    if (bytes[offset] !== 0xff) break;
    const marker = bytes[offset + 1];
    const length = view.getUint16(offset + 2, false);
    if (marker === 0xe1 && String.fromCharCode(...bytes.slice(offset + 4, offset + 10)) === "Exif\0\0") {
      const tiff = offset + 10;
      const little = view.getUint16(tiff, false) === 0x4949;
      const u16 = (at) => view.getUint16(at, little);
      const u32 = (at) => view.getUint32(at, little);
      if (u16(tiff + 2) !== 42) return {};
      const values = {};
      const sizes = { 1: 1, 2: 1, 3: 2, 4: 4, 5: 8 };
      const readEntry = (entry) => {
        const type = u16(entry + 2);
        const count = u32(entry + 4);
        const size = (sizes[type] || 0) * count;
        const data = size <= 4 ? entry + 8 : tiff + u32(entry + 8);
        if (!size || data < 0 || data + size > bytes.length) return null;
        if (type === 2) return new TextDecoder().decode(bytes.slice(data, data + Math.max(0, count - 1))).trim();
        if (type === 3) return u16(data);
        if (type === 4) return u32(data);
        if (type === 5) {
          const denominator = u32(data + 4);
          return denominator ? u32(data) / denominator : null;
        }
        return null;
      };
      const readIfd = (ifdOffset) => {
        const start = tiff + ifdOffset;
        if (start + 2 > bytes.length) return;
        const count = u16(start);
        for (let index = 0; index < count; index += 1) {
          const entry = start + 2 + index * 12;
          if (entry + 12 > bytes.length) break;
          const tag = u16(entry);
          values[tag] = readEntry(entry);
        }
      };
      readIfd(u32(tiff + 4));
      if (values[0x8769]) readIfd(values[0x8769]);
      const exposure = values[0x829a];
      const make = values[0x010f] || "";
      const model = values[0x0110] || "";
      return {
        camera: `${make} ${model}`.trim() || null,
        lens: values[0xa434] || null,
        focalLength: values[0x920a] ? `${Math.round(values[0x920a] * 10) / 10} mm` : null,
        aperture: values[0x829d] ? `f/${Math.round(values[0x829d] * 10) / 10}` : null,
        shutterSpeed: exposure ? (exposure < 1 ? `1/${Math.round(1 / exposure)} s` : `${exposure} s`) : null,
        iso: values[0x8827] || null,
        dateTaken: typeof values[0x9003] === "string" ? values[0x9003].slice(0, 10).replace(/:/g, "-") : null,
      };
    }
    if (length < 2) break;
    offset += 2 + length;
  }
  return {};
}

async function derivative(bitmap, maximum, quality) {
  const scale = Math.min(1, maximum / Math.max(bitmap.width, bitmap.height));
  const width = Math.max(1, Math.round(bitmap.width * scale));
  const height = Math.max(1, Math.round(bitmap.height * scale));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d", { alpha: false, colorSpace: "srgb" });
  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = "high";
  context.drawImage(bitmap, 0, 0, width, height);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
  if (!blob) throw new Error("The browser could not encode a JPEG derivative.");
  return blob;
}

export class CloudflarePhotoAdminRepository {
  constructor() { this.state = null; }
  async initialize() { return this.refresh(); }
  read() {
    if (!this.state) throw new Error("Repository is not initialized.");
    return clone(this.state);
  }
  async refresh() {
    this.state = await apiRequest("/photos", { method: "GET", headers: {} });
    return this.read();
  }
  async listPhotos() { return clone((await this.refresh()).photos); }
  async getPhoto(id) {
    const payload = await apiRequest(`/photos/${encodeURIComponent(id)}`, { method: "GET", headers: {} });
    return payload.photo;
  }
  async saveDraft(photo) {
    const payload = await apiRequest(`/photos/${encodeURIComponent(photo.id)}`, {
      method: "PATCH", body: JSON.stringify({ ...photo, expectedUpdatedAt: photo.updatedAt }),
    });
    await this.refresh();
    return payload.photo;
  }
  async createDraft(photo) {
    const payload = await apiRequest("/photos", { method: "POST", body: JSON.stringify(photo) });
    await this.refresh();
    return payload.photo;
  }
  async archivePhoto(id, expectedUpdatedAt) {
    const payload = await apiRequest(`/photos/${encodeURIComponent(id)}/archive`, {
      method: "POST", body: JSON.stringify({ expectedUpdatedAt, confirm: true }),
    });
    await this.refresh();
    return payload.photo;
  }
  async reorderPhotos(seriesId, orderedPhotoIds) {
    await apiRequest("/photos/reorder", {
      method: "POST", body: JSON.stringify({ seriesId, orderedPhotoIds, expectedRevision: this.state.revision }),
    });
    return (await this.refresh()).photos;
  }
  async listSeries() { return clone((this.state || await this.refresh()).series); }
  async updateSeries(series) {
    const payload = await apiRequest(`/series/${encodeURIComponent(series.id)}`, {
      method: "PATCH", body: JSON.stringify({ ...series, expectedUpdatedAt: series.updatedAt }),
    });
    await this.refresh();
    return payload.series;
  }
  async reorderSeries() { throw new Error("Series reordering remains a controlled D1 operation in V1."); }
  async exportPreviewManifest() { return apiRequest("/preview", { method: "GET", headers: {} }); }
  async publishChanges() {
    const result = await apiRequest("/publish", {
      method: "POST", body: JSON.stringify({ confirm: true, expectedRevision: this.state.revision }),
    });
    await this.refresh();
    return result;
  }
  async prepareUpload(files) {
    const proposals = [];
    for (const file of files) {
      const bitmap = await decodeJpeg(file);
      const exif = await readBasicExif(file);
      proposals.push({
        id: `upload-${crypto.randomUUID()}`,
        file,
        sourceFilename: file.name,
        sourceBytes: file.size,
        mimeType: file.type,
        localPreviewUrl: URL.createObjectURL(file),
        title: file.name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " "),
        orientation: bitmap.height > bitmap.width ? "portrait" : "landscape",
        originalWidth: bitmap.width,
        originalHeight: bitmap.height,
        exif,
        processingState: "selected",
      });
      bitmap.close();
    }
    return { persistentUpload: true, message: "JPEGs validated locally. Save draft to generate and upload four derivatives.", proposals };
  }
  async uploadAssets(id, file, expectedUpdatedAt, replace = false) {
    const bitmap = await decodeJpeg(file);
    try {
      const form = new FormData();
      form.set("expectedUpdatedAt", expectedUpdatedAt);
      form.set("master", file, "master.jpg");
      const settings = { thumbnail: [480, 0.84], preview: [1280, 0.88], display: [2200, 0.9], download: [1800, 0.9] };
      for (const [variant, [maximum, quality]] of Object.entries(settings)) {
        form.set(variant, await derivative(bitmap, maximum, quality), `${variant}.jpg`);
      }
      const payload = await apiRequest(`/photos/${encodeURIComponent(id)}/${replace ? "replace" : "assets"}`, {
        method: "POST", body: form,
        headers: replace ? { "x-photography-confirm-replace": "replace" } : {},
      });
      await this.refresh();
      return payload;
    } finally { bitmap.close(); }
  }
}

export function createPhotoAdminRepository() {
  const local = ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
  return local ? new LocalPhotoAdminRepository() : new CloudflarePhotoAdminRepository();
}
