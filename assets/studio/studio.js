import {
  LocalPhotoAdminRepository,
} from "/assets/studio/photo-admin-repository.js";

const repository = new LocalPhotoAdminRepository();
const archiveGrid = document.querySelector("#archive-grid");
const message = document.querySelector("#studio-message");
const editor = document.querySelector("#photo-editor");
const editorForm = document.querySelector("#editor-form");
const addDialog = document.querySelector("#add-dialog");
const seriesDialog = document.querySelector("#series-dialog");
let state;
let selectedPhotoId = null;
let filters = { status: "all", series: "all", search: "", view: "grid" };
let draggedPhotoId = null;

function escapeHtml(value) {
  const node = document.createElement("span");
  node.textContent = value ?? "";
  return node.innerHTML;
}

function setMessage(text, error = false) {
  message.textContent = text;
  message.classList.toggle("error", error);
}

function displayDate(value) {
  if (!value) return "Not yet";
  const date = value.length === 10 ? new Date(`${value}T00:00:00Z`) : new Date(value);
  return new Intl.DateTimeFormat("en-CA", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" }).format(date);
}

function imageSource(photo, variant = "thumbnail") {
  return photo.localPreviewUrl || photo.images?.[variant]?.src || "";
}

async function refreshState() {
  state = repository.read();
  renderSummary();
  renderFilters();
  renderArchive();
}

function renderSummary() {
  document.querySelector("#photo-count").textContent = state.photos.length;
  document.querySelector("#series-count").textContent = state.series.length;
  document.querySelector("#last-published").textContent = displayDate(state.lastPublishedAt);
}

function renderFilters() {
  const seriesFilter = document.querySelector("#series-filter");
  const editorSeries = document.querySelector("#field-series");
  const options = [...state.series]
    .sort((a, b) => a.sortOrder - b.sortOrder)
    .map((series) => `<option value="${escapeHtml(series.id)}">${escapeHtml(series.number)} · ${escapeHtml(series.title)}</option>`)
    .join("");
  seriesFilter.innerHTML = `<option value="all">All series</option>${options}`;
  seriesFilter.value = filters.series;
  editorSeries.innerHTML = options;
}

function visiblePhotos() {
  const seriesOrder = new Map([...state.series].sort((a, b) => a.sortOrder - b.sortOrder).map((series, index) => [series.id, index]));
  return state.photos
    .filter((photo) => filters.status === "all" || photo.status === filters.status)
    .filter((photo) => filters.series === "all" || photo.seriesId === filters.series)
    .filter((photo) => photo.title.toLowerCase().includes(filters.search.toLowerCase()))
    .sort((a, b) => (seriesOrder.get(a.seriesId) - seriesOrder.get(b.seriesId)) || a.sortOrder - b.sortOrder || a.id.localeCompare(b.id));
}

function renderArchive() {
  const seriesById = new Map(state.series.map((series) => [series.id, series]));
  const photos = visiblePhotos();
  archiveGrid.classList.toggle("list-view", filters.view === "list");
  archiveGrid.innerHTML = photos.map((photo) => {
    const src = imageSource(photo);
    const image = src
      ? `<img src="${escapeHtml(src)}" alt="${escapeHtml(photo.alt || photo.title)}" loading="lazy" />`
      : `<span class="archive-placeholder">Awaiting ingest</span>`;
    return `<article class="archive-item" draggable="true" data-photo-id="${photo.id}" data-series-id="${photo.seriesId}">
      <button class="archive-card" type="button" data-edit-photo="${photo.id}">
        <span class="archive-image">${image}<span class="status-chip">${escapeHtml(photo.status)}</span></span>
        <span class="archive-meta">
          <span class="archive-title">${escapeHtml(photo.title)}</span>
          <span class="archive-id">${escapeHtml(photo.id)} · v${photo.assetVersion}</span>
          <span class="archive-series">${escapeHtml(seriesById.get(photo.seriesId)?.title || photo.seriesId)}</span>
        </span>
      </button>
      <div class="order-actions" aria-label="Order ${escapeHtml(photo.title)}">
        <button type="button" data-move="up" data-photo-id="${photo.id}">Move up</button>
        <button type="button" data-move="down" data-photo-id="${photo.id}">Move down</button>
      </div>
    </article>`;
  }).join("") || `<p class="studio-message">No photographs match these filters.</p>`;

  archiveGrid.querySelectorAll("[data-edit-photo]").forEach((button) => {
    button.addEventListener("click", () => openEditor(button.dataset.editPhoto));
  });
  archiveGrid.querySelectorAll("[data-move]").forEach((button) => {
    button.addEventListener("click", () => movePhoto(button.dataset.photoId, button.dataset.move));
  });
  archiveGrid.querySelectorAll(".archive-item").forEach((item) => {
    item.addEventListener("dragstart", () => { draggedPhotoId = item.dataset.photoId; });
    item.addEventListener("dragover", (event) => event.preventDefault());
    item.addEventListener("drop", async (event) => {
      event.preventDefault();
      if (!draggedPhotoId || draggedPhotoId === item.dataset.photoId) return;
      await dropPhoto(draggedPhotoId, item.dataset.photoId);
      draggedPhotoId = null;
    });
  });
}

async function movePhoto(id, direction) {
  const photo = state.photos.find((item) => item.id === id);
  const ordered = state.photos
    .filter((item) => item.seriesId === photo.seriesId && item.status !== "archived")
    .sort((a, b) => a.sortOrder - b.sortOrder)
    .map((item) => item.id);
  const index = ordered.indexOf(id);
  const target = direction === "up" ? index - 1 : index + 1;
  if (target < 0 || target >= ordered.length) return;
  [ordered[index], ordered[target]] = [ordered[target], ordered[index]];
  await repository.reorderPhotos(photo.seriesId, ordered);
  setMessage(`${photo.title} moved ${direction}. Preview reflects the new order.`);
  await refreshState();
}

async function dropPhoto(sourceId, targetId) {
  const source = state.photos.find((photo) => photo.id === sourceId);
  const target = state.photos.find((photo) => photo.id === targetId);
  if (!source || !target || source.seriesId !== target.seriesId) {
    setMessage("Drag ordering stays within one series. Use the editor to change series.", true);
    return;
  }
  const ordered = state.photos
    .filter((photo) => photo.seriesId === source.seriesId && photo.status !== "archived")
    .sort((a, b) => a.sortOrder - b.sortOrder)
    .map((photo) => photo.id);
  ordered.splice(ordered.indexOf(sourceId), 1);
  ordered.splice(ordered.indexOf(targetId), 0, sourceId);
  await repository.reorderPhotos(source.seriesId, ordered);
  setMessage("Contact-sheet order updated locally.");
  await refreshState();
}

function technicalRows(photo) {
  const dimensions = photo.originalWidth && photo.originalHeight
    ? `${photo.originalWidth} × ${photo.originalHeight}` : "Not recorded";
  return [
    ["Camera", photo.camera], ["Lens", photo.lens], ["Focal length", photo.focalLength],
    ["Aperture", photo.aperture], ["Shutter", photo.shutterSpeed], ["ISO", photo.iso],
    ["Dimensions", dimensions], ["Asset version", `v${photo.assetVersion}`],
  ].map(([term, value]) => `<dt>${term}</dt><dd>${escapeHtml(value ?? "—")}</dd>`).join("");
}

async function openEditor(id) {
  const photo = await repository.getPhoto(id);
  if (!photo) return;
  selectedPhotoId = id;
  document.querySelector("#editor-id").textContent = `${photo.id} · ${photo.status}`;
  document.querySelector("#editor-title").textContent = photo.title;
  document.querySelector("#field-id").value = photo.id;
  document.querySelector("#field-title").value = photo.title;
  document.querySelector("#field-series").value = photo.seriesId;
  document.querySelector("#field-date").value = photo.dateTaken || "";
  document.querySelector("#field-location").value = photo.locationDisplay || "";
  document.querySelector("#field-caption").value = photo.caption || "";
  document.querySelector("#field-alt").value = photo.alt || "";
  document.querySelector("#field-layout").value = photo.layoutHint;
  document.querySelector("#field-status").value = photo.status;
  document.querySelector("#field-featured").checked = photo.featured;
  document.querySelector("#field-download").checked = photo.allowDownload;
  const image = document.querySelector("#editor-image");
  image.src = imageSource(photo, "display");
  image.alt = photo.alt || photo.title;
  image.hidden = !image.src;
  document.querySelector("#processing-note").textContent = photo.processingState === "ready"
    ? "Four local derivatives ready."
    : "Awaiting offline ingest; browser selection is not a durable upload.";
  document.querySelector("#technical-list").innerHTML = technicalRows(photo);
  editor.showModal();
}

function recordFromEditor() {
  const current = state.photos.find((photo) => photo.id === selectedPhotoId);
  return {
    ...current,
    id: document.querySelector("#field-id").value,
    title: document.querySelector("#field-title").value.trim(),
    seriesId: document.querySelector("#field-series").value,
    dateTaken: document.querySelector("#field-date").value || null,
    locationDisplay: document.querySelector("#field-location").value.trim(),
    caption: document.querySelector("#field-caption").value.trim(),
    alt: document.querySelector("#field-alt").value.trim(),
    layoutHint: document.querySelector("#field-layout").value,
    status: document.querySelector("#field-status").value,
    featured: document.querySelector("#field-featured").checked,
    allowDownload: document.querySelector("#field-download").checked,
  };
}

async function saveEditorDraft() {
  const saved = await repository.saveDraft(recordFromEditor());
  selectedPhotoId = saved.id;
  await refreshState();
  setMessage(`${saved.title} saved as a local draft. Public Photography is unchanged.`);
  return saved;
}

editorForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try { await saveEditorDraft(); editor.close(); }
  catch (error) { setMessage(error.message, true); }
});

document.querySelector("#publish-photo").addEventListener("click", async () => {
  try {
    const saved = await saveEditorDraft();
    await repository.publishPhoto(saved.id);
    await refreshState();
    editor.close();
    setMessage(`${saved.title} published to local mock state only. No public file or cloud resource changed.`);
  } catch (error) { setMessage(error.message, true); }
});

document.querySelector("#archive-photo").addEventListener("click", async () => {
  try {
    const photo = await repository.archivePhoto(selectedPhotoId);
    await refreshState();
    editor.close();
    setMessage(`${photo.title} archived locally. No file was deleted.`);
  } catch (error) { setMessage(error.message, true); }
});

document.querySelector("#preview-photo").addEventListener("click", async () => {
  try {
    await saveEditorDraft();
    localStorage.setItem("kx-photography-preview-manifest", JSON.stringify(await repository.exportPreviewManifest()));
    window.open("/studio/preview.html", "photography-studio-preview");
    setMessage("Draft preview opened using the public Photography layout.");
  } catch (error) {
    setMessage(error.message, true);
  }
});

document.querySelectorAll("[data-close-dialog]").forEach((button) => {
  button.addEventListener("click", () => document.querySelector(`#${button.dataset.closeDialog}`).close());
});

document.querySelectorAll("[data-status]").forEach((button) => {
  button.addEventListener("click", () => {
    filters.status = button.dataset.status;
    document.querySelectorAll("[data-status]").forEach((item) => item.classList.toggle("active", item === button));
    renderArchive();
  });
});

document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", () => {
    filters.view = button.dataset.view;
    document.querySelectorAll("[data-view]").forEach((item) => item.classList.toggle("active", item === button));
    renderArchive();
  });
});

document.querySelector("#photo-search").addEventListener("input", (event) => { filters.search = event.target.value; renderArchive(); });
document.querySelector("#series-filter").addEventListener("change", (event) => { filters.series = event.target.value; renderArchive(); });
document.querySelector("#add-photos").addEventListener("click", () => addDialog.showModal());

const dropZone = document.querySelector("#drop-zone");
const fileInput = document.querySelector("#file-input");
dropZone.addEventListener("dragover", (event) => { event.preventDefault(); dropZone.classList.add("dragging"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragging"));
dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("dragging");
  prepareFiles(event.dataTransfer.files);
});
fileInput.addEventListener("change", () => prepareFiles(fileInput.files));

async function prepareFiles(files) {
  try {
    const result = await repository.prepareUpload([...files]);
    setMessage(result.message);
    const series = await repository.listSeries();
    document.querySelector("#ingest-proposals").innerHTML = result.proposals.map((proposal) => `
      <article class="ingest-proposal" data-proposal-id="${proposal.id}">
        <img src="${escapeHtml(proposal.localPreviewUrl)}" alt="Selected local preview" />
        <div class="ingest-proposal-fields">
          <input class="proposal-title full" aria-label="Title" value="${escapeHtml(proposal.title)}" />
          <select class="proposal-series" aria-label="Series">${series.map((item) => `<option value="${item.id}">${escapeHtml(item.title)}</option>`).join("")}</select>
          <input class="proposal-date" aria-label="Date" type="date" />
          <input class="proposal-caption full" aria-label="Caption" placeholder="Caption" />
          <input class="proposal-alt full" aria-label="Alt text" placeholder="Alt text required" />
          <select class="proposal-layout" aria-label="Layout"><option>standard</option><option>wide</option><option>portrait-left</option><option>portrait-right</option><option>panorama</option></select>
          <label><input class="proposal-download" type="checkbox" checked /> Allow download</label>
          <p class="honesty-note full">EXIF detected: pending offline ingest · ${escapeHtml(proposal.mimeType)} · ${Math.round(proposal.sourceBytes / 1024)} KiB</p>
        </div>
        <button type="button" data-save-proposal="${proposal.id}">Save draft</button>
      </article>`).join("");
    result.proposals.forEach((proposal) => {
      document.querySelector(`[data-save-proposal="${proposal.id}"]`).addEventListener("click", () => saveProposal(proposal));
    });
  } catch (error) { setMessage(error.message, true); }
}

async function saveProposal(proposal) {
  const root = document.querySelector(`[data-proposal-id="${proposal.id}"]`);
  try {
    await repository.saveDraft({
      ...proposal,
      slug: "",
      title: root.querySelector(".proposal-title").value.trim(),
      seriesId: root.querySelector(".proposal-series").value,
      dateTaken: root.querySelector(".proposal-date").value || null,
      datePublished: null,
      locationDisplay: "",
      caption: root.querySelector(".proposal-caption").value.trim(),
      alt: root.querySelector(".proposal-alt").value.trim(),
      camera: null, lens: null, focalLength: null, aperture: null, shutterSpeed: null, iso: null,
      orientation: "landscape",
      layoutHint: root.querySelector(".proposal-layout").value,
      featured: false,
      allowDownload: root.querySelector(".proposal-download").checked,
      sortOrder: 999,
      status: "draft",
      assetVersion: 1,
      images: null,
    });
    root.remove();
    await refreshState();
    setMessage(`${proposal.id} saved as metadata-only draft. Run offline ingest before publishing.`);
  } catch (error) { setMessage(error.message, true); }
}

document.querySelector("#manage-series").addEventListener("click", () => { renderSeriesEditor(); seriesDialog.showModal(); });

function renderSeriesEditor() {
  document.querySelector("#series-editor-list").innerHTML = [...state.series]
    .sort((a, b) => a.sortOrder - b.sortOrder)
    .map((series) => {
      const coverOptions = state.photos
        .filter((photo) => photo.seriesId === series.id && photo.status !== "archived")
        .map((photo) => `<option value="${photo.id}" ${series.coverPhotoId === photo.id ? "selected" : ""}>${escapeHtml(photo.title)}</option>`)
        .join("");
      return `<div class="series-entry" data-series-entry="${series.id}">
      <span class="series-number">${escapeHtml(series.number)}</span>
      <input class="series-title" aria-label="${escapeHtml(series.number)} title" value="${escapeHtml(series.title)}" />
      <input class="series-description" aria-label="${escapeHtml(series.number)} description" value="${escapeHtml(series.description)}" />
      <select class="series-cover" aria-label="${escapeHtml(series.number)} cover"><option value="">Automatic cover</option>${coverOptions}</select>
      <label><input class="series-hidden" type="checkbox" ${series.hidden ? "checked" : ""} /> Hidden</label>
      <span class="order-actions"><button type="button" data-series-move="up" data-series-id="${series.id}" aria-label="Move ${escapeHtml(series.title)} up">↑</button><button type="button" data-series-move="down" data-series-id="${series.id}" aria-label="Move ${escapeHtml(series.title)} down">↓</button><button type="button" data-save-series="${series.id}">Save</button></span>
    </div>`;
    }).join("");
  document.querySelectorAll("[data-save-series]").forEach((button) => button.addEventListener("click", () => saveSeries(button.dataset.saveSeries)));
  document.querySelectorAll("[data-series-move]").forEach((button) => button.addEventListener("click", () => moveSeries(button.dataset.seriesId, button.dataset.seriesMove)));
}

async function saveSeries(id) {
  const root = document.querySelector(`[data-series-entry="${id}"]`);
  await repository.updateSeries({
    id,
    title: root.querySelector(".series-title").value.trim(),
    description: root.querySelector(".series-description").value.trim(),
    coverPhotoId: root.querySelector(".series-cover").value || null,
    hidden: root.querySelector(".series-hidden").checked,
  });
  await refreshState();
  renderSeriesEditor();
  setMessage("Series changes saved locally and included in Preview.");
}

async function moveSeries(id, direction) {
  const ordered = [...state.series].sort((a, b) => a.sortOrder - b.sortOrder).map((series) => series.id);
  const index = ordered.indexOf(id);
  const target = direction === "up" ? index - 1 : index + 1;
  if (target < 0 || target >= ordered.length) return;
  [ordered[index], ordered[target]] = [ordered[target], ordered[index]];
  await repository.reorderSeries(ordered);
  await refreshState();
  renderSeriesEditor();
}

document.querySelector("#reset-fixture").addEventListener("click", async () => {
  if (!window.confirm("Reset only the local Studio fixture? Public Photography and source files are unaffected.")) return;
  await repository.resetLocalFixture();
  await refreshState();
  setMessage("Local Studio fixture reset from safe seed data.");
});

try {
  await repository.initialize();
  await refreshState();
  setMessage("Local fixture ready. Changes stay in this browser only.");
} catch (error) {
  setMessage(error.message, true);
}
