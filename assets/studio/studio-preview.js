const root = document.querySelector("#preview-content");
const raw = localStorage.getItem("kx-photography-preview-manifest");

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function year(photo) {
  return photo.dateTaken?.slice(0, 4) || "Undated";
}

function figure(photo, hero = false) {
  const item = node("figure", `${hero ? "hero-photo " : ""}photo-figure layout-${photo.layoutHint}`);
  item.id = `preview-${photo.id}`;
  const imageClip = node("span", "image-clip");
  const source = photo.images?.[hero ? "display" : "preview"];
  if (source) {
    const image = node("img");
    image.src = source.src;
    image.alt = photo.alt;
    image.width = source.width;
    image.height = source.height;
    image.loading = hero ? "eager" : "lazy";
    imageClip.append(image);
  } else {
    imageClip.append(node("span", "preview-missing", `${photo.id} · awaiting offline ingest`));
  }
  const caption = node("figcaption", "photo-caption");
  caption.append(node("strong", "", photo.title), node("span", "", year(photo)));
  item.append(imageClip, caption);
  return item;
}

if (!raw) {
  root.innerHTML = '<p class="photo-status">No draft preview is available. Return to Studio and choose Preview.</p>';
} else {
  const manifest = JSON.parse(raw);
  const fragment = document.createDocumentFragment();
  const hero = manifest.photos.find((photo) => photo.featured) || manifest.photos[0];
  if (hero) fragment.append(figure(hero, true));
  const seriesList = node("div", "series-list");
  manifest.series.forEach((series) => {
    const photos = manifest.photos.filter((photo) => photo.seriesId === series.id && photo.id !== hero?.id);
    if (!photos.length) return;
    const section = node("section", "series");
    const heading = node("header", "series-heading");
    heading.append(node("span", "series-number", series.number), node("h2", "", series.title), node("p", "", series.description));
    const grid = node("div", "series-grid");
    photos.forEach((photo) => grid.append(figure(photo)));
    section.append(heading, grid);
    seriesList.append(section);
  });
  fragment.append(seriesList);
  root.replaceChildren(fragment);
}
