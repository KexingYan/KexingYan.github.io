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

// Future CloudflarePhotoAdminRepository will implement the same methods against
// /api/photo-admin/* after Cloudflare Access and server-side JWT validation exist.
