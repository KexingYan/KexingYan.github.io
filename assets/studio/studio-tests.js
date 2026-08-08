import {
  LocalPhotoAdminRepository,
  PRIVATE_ONLY_FIELDS,
} from "/assets/studio/photo-admin-repository.js";

const results = document.querySelector("#test-results");
const summary = document.querySelector("#test-summary");
const storageKey = `kx-studio-test-${Date.now()}`;
const repository = new LocalPhotoAdminRepository({ storageKey });
let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function test(name, callback) {
  const item = document.createElement("li");
  try {
    await callback();
    item.className = "pass";
    item.textContent = `PASS · ${name}`;
    passed += 1;
  } catch (error) {
    item.className = "fail";
    item.textContent = `FAIL · ${name} · ${error.message}`;
    failed += 1;
  }
  results.append(item);
}

function containsPrivateField(value) {
  if (Array.isArray(value)) return value.some(containsPrivateField);
  if (!value || typeof value !== "object") return false;
  return Object.entries(value).some(([key, child]) => PRIVATE_ONLY_FIELDS.includes(key) || containsPrivateField(child));
}

await repository.initialize();

await test("local adapter loads fourteen fixture records", async () => {
  assert((await repository.listPhotos()).length === 14, "wrong fixture count");
});

await test("draft records do not enter the public manifest", async () => {
  const photo = await repository.getPhoto("P014");
  await repository.saveDraft({ ...photo, title: "Draft Between Buildings", layoutHint: "wide", masterObjectKey: "private/test" });
  const manifest = await repository.exportPublicManifest();
  assert(!manifest.photos.some((item) => item.id === "P014"), "draft leaked publicly");
});

await test("preview includes draft fields and uses public-safe transform", async () => {
  const preview = await repository.exportPreviewManifest();
  const photo = preview.photos.find((item) => item.id === "P014");
  assert(photo?.title === "Draft Between Buildings", "draft title missing from preview");
  assert(photo?.layoutHint === "wide", "draft layout missing from preview");
  assert(!containsPrivateField(preview), "private field leaked into preview");
});

await test("published records transform without private fields", async () => {
  await repository.publishPhoto("P014");
  const manifest = await repository.exportPublicManifest();
  assert(manifest.photos.some((item) => item.id === "P014"), "published record missing");
  assert(!containsPrivateField(manifest), "private field leaked publicly");
});

await test("archived records are excluded publicly", async () => {
  await repository.archivePhoto("P014");
  assert(!(await repository.exportPublicManifest()).photos.some((item) => item.id === "P014"), "archived record leaked publicly");
});

await test("manual reorder persists and appears in preview", async () => {
  const before = (await repository.listPhotos()).filter((photo) => photo.seriesId === "garden-notes" && photo.status !== "archived").sort((a, b) => a.sortOrder - b.sortOrder).map((photo) => photo.id);
  const reversed = [...before].reverse();
  await repository.reorderPhotos("garden-notes", reversed);
  const persisted = (await repository.listPhotos()).filter((photo) => photo.seriesId === "garden-notes" && photo.status !== "archived").sort((a, b) => a.sortOrder - b.sortOrder).map((photo) => photo.id);
  const preview = await repository.exportPreviewManifest();
  const previewOrder = preview.photos.filter((photo) => photo.seriesId === "garden-notes").map((photo) => photo.id);
  assert(JSON.stringify(persisted) === JSON.stringify(reversed), "repository order did not persist");
  assert(JSON.stringify(previewOrder) === JSON.stringify(reversed), "preview order differs");
});

localStorage.removeItem(storageKey);
summary.textContent = `${passed} passed · ${failed} failed`;
summary.dataset.status = failed ? "failed" : "passed";
document.body.dataset.tests = failed ? "failed" : "passed";
