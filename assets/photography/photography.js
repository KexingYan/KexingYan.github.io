(function () {
  "use strict";

  const manifestUrl = window.PHOTOGRAPHY_CONFIG?.manifestUrl
    || "/assets/photography/data/photos.json";
  const gallery = document.querySelector("#series-list");
  const indexDialog = document.querySelector("#photo-index");
  const indexGrid = document.querySelector("#contact-sheet");
  const lightbox = document.querySelector("#lightbox");
  const licenseDialog = document.querySelector("#download-license");
  const indexButton = document.querySelector("#open-index");
  const indexClose = document.querySelector("#close-index");
  const lightboxClose = document.querySelector("#close-lightbox");
  const previousButton = document.querySelector("#previous-photo");
  const nextButton = document.querySelector("#next-photo");
  const downloadRequest = document.querySelector("#download-request");
  const licenseCancel = document.querySelector("#license-cancel");
  const downloadConfirm = document.querySelector("#download-confirm");

  if (!gallery || !indexDialog || !lightbox || !licenseDialog) return;

  let manifest;
  let orderedPhotos = [];
  let currentIndex = 0;
  let contactSheetBuilt = false;
  let touchStartX = null;
  let lastLightboxTrigger = null;

  const seriesById = new Map();
  const photoById = new Map();

  function yearOf(photo) {
    return photo.dateTaken ? photo.dateTaken.slice(0, 4) : "Undated";
  }

  function formatDate(value) {
    if (!value) return "Date not recorded";
    return new Intl.DateTimeFormat("en-CA", {
      year: "numeric",
      month: "long",
      day: "numeric",
      timeZone: "UTC",
    }).format(new Date(`${value}T00:00:00Z`));
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function imageFor(photo, variant, options) {
    const data = photo.images[variant];
    const image = document.createElement("img");
    image.src = data.src;
    image.alt = photo.alt;
    image.width = data.width;
    image.height = data.height;
    image.decoding = options?.decoding || "async";
    if (options?.loading) image.loading = options.loading;
    if (options?.responsive) {
      image.srcset = `${photo.images.preview.src} ${photo.images.preview.width}w, ${photo.images.display.src} ${photo.images.display.width}w`;
      image.sizes = photo.orientation === "portrait"
        ? "(max-width: 620px) 100vw, (max-width: 1100px) 58vw, 42vw"
        : "(max-width: 620px) 100vw, (max-width: 1500px) 88vw, 1420px";
    }
    return image;
  }

  function figureFor(photo) {
    const figure = element("figure", `photo-figure layout-${photo.layoutHint}`);
    figure.id = `photo-${photo.id}`;

    const button = element("button", "photo-open");
    button.type = "button";
    button.dataset.photoId = photo.id;
    button.setAttribute("aria-label", `View ${photo.title} in full-screen detail`);
    const clip = element("span", "image-clip");
    clip.append(imageFor(photo, "preview", { loading: "lazy", responsive: true }));
    button.append(clip);

    const caption = element("figcaption", "photo-caption");
    caption.append(element("strong", "", photo.title));
    caption.append(element("span", "", yearOf(photo)));
    figure.append(button, caption);
    return figure;
  }

  function renderSeries() {
    const fragment = document.createDocumentFragment();
    manifest.series.forEach((series) => {
      const section = element("section", "series");
      section.id = series.id;
      section.setAttribute("aria-labelledby", `${series.id}-title`);

      const heading = element("header", "series-heading");
      heading.append(element("span", "series-number", series.number));
      const title = element("h2", "", series.title);
      title.id = `${series.id}-title`;
      heading.append(title, element("p", "", series.description));

      const grid = element("div", "series-grid");
      orderedPhotos
        .filter((photo) => photo.seriesId === series.id && !photo.featured)
        .forEach((photo) => grid.append(figureFor(photo)));
      section.append(heading, grid);
      fragment.append(section);
    });
    gallery.replaceChildren(fragment);
  }

  function bindPhotoButtons(root) {
    root.querySelectorAll("[data-photo-id]").forEach((button) => {
      button.addEventListener("click", () => openLightboxById(button.dataset.photoId, button));
    });
  }

  function buildContactSheet() {
    if (contactSheetBuilt) return;
    const fragment = document.createDocumentFragment();
    orderedPhotos.forEach((photo, index) => {
      const button = element("button", "contact-item");
      button.type = "button";
      button.setAttribute("aria-label", `Open ${photo.title}`);
      button.append(imageFor(photo, "thumbnail", { loading: "lazy" }));

      const meta = element("span", "contact-meta");
      meta.append(
        element("span", "", String(index + 1).padStart(3, "0")),
        element("span", "", photo.title)
      );
      button.append(meta, element("span", "contact-series", seriesById.get(photo.seriesId).title));
      button.addEventListener("click", () => {
        lastLightboxTrigger = indexButton;
        indexDialog.close();
        openLightbox(index);
      });
      fragment.append(button);
    });
    indexGrid.append(fragment);
    contactSheetBuilt = true;
  }

  function syncModalState() {
    document.body.classList.toggle(
      "modal-open",
      indexDialog.open || lightbox.open || licenseDialog.open
    );
  }

  function openIndex() {
    buildContactSheet();
    indexDialog.showModal();
    syncModalState();
  }

  function addExifRow(list, label, value) {
    if (value === null || value === undefined || value === "") return;
    list.append(element("dt", "", label), element("dd", "", String(value)));
  }

  function renderLightbox(photo) {
    const imageWrap = document.querySelector("#lightbox-image");
    const image = imageFor(photo, "display", {});
    image.alt = photo.alt;
    imageWrap.replaceChildren(image);

    document.querySelector("#lightbox-count").textContent =
      `${String(currentIndex + 1).padStart(3, "0")} / ${String(orderedPhotos.length).padStart(3, "0")}`;
    document.querySelector("#lightbox-series").textContent = seriesById.get(photo.seriesId).title;
    document.querySelector("#lightbox-title").textContent = photo.title;
    document.querySelector("#lightbox-date").textContent = formatDate(photo.dateTaken);

    const exif = document.querySelector("#lightbox-exif");
    exif.replaceChildren();
    addExifRow(exif, "Camera", photo.camera);
    addExifRow(exif, "Lens", photo.lens);
    addExifRow(exif, "Focal length", photo.focalLength);
    addExifRow(exif, "Aperture", photo.aperture);
    addExifRow(exif, "Shutter", photo.shutterSpeed);
    addExifRow(exif, "ISO", photo.iso);

    downloadRequest.hidden = !photo.allowDownload;
    downloadRequest.dataset.photoId = photo.id;
  }

  function openLightbox(index, trigger) {
    if (!lightbox.open && trigger) lastLightboxTrigger = trigger;
    currentIndex = (index + orderedPhotos.length) % orderedPhotos.length;
    renderLightbox(orderedPhotos[currentIndex]);
    if (!lightbox.open) lightbox.showModal();
    syncModalState();
  }

  function openLightboxById(id, trigger) {
    const index = orderedPhotos.findIndex((photo) => photo.id === id);
    if (index >= 0) openLightbox(index, trigger);
  }

  function moveLightbox(delta) {
    openLightbox(currentIndex + delta);
  }

  function openDownloadLicense() {
    const photo = photoById.get(downloadRequest.dataset.photoId);
    if (!photo || !photo.allowDownload) return;
    downloadConfirm.href = photo.images.download.src;
    downloadConfirm.download = `${photo.slug}-kexing-yan-personal-use.jpg`;
    licenseDialog.showModal();
    syncModalState();
  }

  [indexDialog, lightbox, licenseDialog].forEach((dialog) => {
    dialog.addEventListener("close", syncModalState);
  });
  lightbox.addEventListener("close", () => {
    if (lastLightboxTrigger && lastLightboxTrigger.isConnected) {
      lastLightboxTrigger.focus();
    }
  });

  indexButton?.addEventListener("click", openIndex);
  indexClose?.addEventListener("click", () => indexDialog.close());
  lightboxClose?.addEventListener("click", () => lightbox.close());
  previousButton?.addEventListener("click", () => moveLightbox(-1));
  nextButton?.addEventListener("click", () => moveLightbox(1));
  downloadRequest?.addEventListener("click", openDownloadLicense);
  licenseCancel?.addEventListener("click", () => licenseDialog.close());
  downloadConfirm?.addEventListener("click", () => licenseDialog.close());

  lightbox.addEventListener("keydown", (event) => {
    if (licenseDialog.open) return;
    if (event.key === "ArrowLeft") moveLightbox(-1);
    if (event.key === "ArrowRight") moveLightbox(1);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (licenseDialog.open) {
      event.preventDefault();
      licenseDialog.close();
    } else if (lightbox.open) {
      event.preventDefault();
      lightbox.close();
    } else if (indexDialog.open) {
      event.preventDefault();
      indexDialog.close();
    }
  });

  const lightboxImage = document.querySelector("#lightbox-image");
  lightboxImage?.addEventListener("pointerdown", (event) => {
    touchStartX = event.clientX;
  });
  lightboxImage?.addEventListener("pointerup", (event) => {
    if (touchStartX === null) return;
    const distance = event.clientX - touchStartX;
    touchStartX = null;
    if (Math.abs(distance) < 55) return;
    moveLightbox(distance > 0 ? -1 : 1);
  });

  fetch(manifestUrl)
    .then((response) => {
      if (!response.ok) throw new Error(`Manifest request failed: ${response.status}`);
      return response.json();
    })
    .then((data) => {
      manifest = data;
      manifest.series.forEach((series) => seriesById.set(series.id, series));
      manifest.photos.forEach((photo) => photoById.set(photo.id, photo));
      orderedPhotos = manifest.series.flatMap((series) =>
        manifest.photos
          .filter((photo) => photo.seriesId === series.id)
          .sort((a, b) => a.sortOrder - b.sortOrder)
      );
      renderSeries();
      bindPhotoButtons(document);
    })
    .catch((error) => {
      console.error(error);
      gallery.textContent = "The photographic archive could not be loaded.";
      gallery.classList.add("photo-status");
    });
})();
