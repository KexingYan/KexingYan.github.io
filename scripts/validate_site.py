#!/usr/bin/env python3
"""Deterministic validation for site sources and the packaged static artifact."""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

from build_site import (
    MANIFEST,
    PUBLIC_FILES,
    ReferenceParser,
    local_reference,
    sha256,
)


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://kexingyan.com"
VERIFICATION_HTML = {"baidu_verify_codeva-vWXLKxDtXl.html"}
PERSON_ID = f"{DOMAIN}/#person"
WEBSITE_ID = f"{DOMAIN}/#website"
PROFILE_ID = f"{DOMAIN}/#profile"
PROFILE_DATETIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$"
)


@dataclass
class Page:
    path: Path
    lang: str | None = None
    titles: list[str] = field(default_factory=list)
    metas: dict[str, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )
    property_metas: dict[str, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )
    canonicals: list[str] = field(default_factory=list)
    hrefs: list[str] = field(default_factory=list)
    ids: Counter[str] = field(default_factory=Counter)
    headings: list[tuple[int, dict[str, str | None]]] = field(
        default_factory=list
    )
    images: list[dict[str, str | None]] = field(default_factory=list)
    json_ld: list[str] = field(default_factory=list)
    main_ids: list[str | None] = field(default_factory=list)
    skip_targets: list[str] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)
    time_datetimes: list[str] = field(default_factory=list)

    @property
    def robots_tokens(self) -> set[str]:
        values = self.metas.get("robots", [])
        return {
            token.strip().lower()
            for value in values
            for token in value.split(",")
            if token.strip()
        }

    @property
    def indexable(self) -> bool:
        return "noindex" not in self.robots_tokens

    @property
    def visible_text(self) -> str:
        return " ".join(" ".join(self.text_parts).split())


class PageParser(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.page = Page(path=path)
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._suppressed_text_depth = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if tag in {"script", "style"}:
            self._suppressed_text_depth += 1
        element_id = attributes.get("id")
        if element_id:
            self.page.ids[element_id] += 1

        if tag == "html":
            self.page.lang = attributes.get("lang")
        elif tag == "title":
            self._capture = "title"
            self._buffer = []
        elif tag == "meta":
            content = attributes.get("content")
            name = (attributes.get("name") or "").strip().lower()
            prop = (attributes.get("property") or "").strip().lower()
            if name and content is not None:
                self.page.metas[name].append(content.strip())
            if prop and content is not None:
                self.page.property_metas[prop].append(content.strip())
        elif tag == "link":
            rel_tokens = {
                token.lower()
                for token in (attributes.get("rel") or "").split()
            }
            if "canonical" in rel_tokens:
                href = attributes.get("href")
                self.page.canonicals.append((href or "").strip())
        elif tag == "a":
            href = attributes.get("href")
            if href is not None:
                self.page.hrefs.append(href.strip())
            if "skip-link" in (attributes.get("class") or "").split():
                self.page.skip_targets.append((href or "").strip())
        elif tag == "main":
            self.page.main_ids.append(attributes.get("id"))
        elif len(tag) == 2 and tag[0] == "h" and tag[1].isdigit():
            self.page.headings.append((int(tag[1]), attributes))
        elif tag == "img":
            self.page.images.append(attributes)
        elif tag == "time":
            value = attributes.get("datetime")
            if value:
                self.page.time_datetimes.append(value.strip())
        elif (
            tag == "script"
            and attributes.get("type") == "application/ld+json"
        ):
            self._capture = "json-ld"
            self._buffer = []

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._capture == "title":
            self.page.titles.append("".join(self._buffer).strip())
            self._capture = None
            self._buffer = []
        elif tag == "script" and self._capture == "json-ld":
            self.page.json_ld.append("".join(self._buffer).strip())
            self._capture = None
            self._buffer = []
        if tag in {"script", "style"} and self._suppressed_text_depth:
            self._suppressed_text_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._capture is not None:
            self._buffer.append(data)
        elif not self._suppressed_text_depth and data.strip():
            self.page.text_parts.append(data.strip())


def parse_page(path: Path) -> Page:
    parser = PageParser(path)
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser.page


def page_route(path: Path, root: Path) -> str:
    relative = path.relative_to(root)
    if relative == Path("index.html"):
        return "/"
    if relative.name == "index.html":
        return f"/{relative.parent.as_posix().strip('/')}/"
    return f"/{relative.as_posix()}"


def valid_canonical(url: str, domain: str) -> bool:
    parsed = urlparse(url)
    expected = urlparse(domain)
    return (
        parsed.scheme == "https"
        and parsed.netloc == expected.netloc
        and not parsed.username
        and not parsed.password
        and parsed.port is None
        and not parsed.query
        and not parsed.fragment
        and bool(parsed.path)
    )


def parse_profile_datetime(value: object) -> datetime | None:
    """Parse the full timezone-aware DateTime Google requires for ProfilePage."""
    if not isinstance(value, str) or not PROFILE_DATETIME_PATTERN.fullmatch(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def png_dimensions(path: Path) -> tuple[int, int] | None:
    """Return PNG dimensions without adding an image-processing dependency."""
    try:
        with path.open("rb") as stream:
            header = stream.read(24)
    except OSError:
        return None
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", header[16:24])


def resolve_local_target(
    root: Path, source: Path, href: str, domain: str
) -> tuple[Path, str | None] | None:
    if not href or any(character.isspace() for character in href):
        raise ValueError("empty or whitespace-containing URL")
    parsed = urlparse(href)
    if parsed.scheme in {"mailto", "tel"}:
        if not parsed.path:
            raise ValueError(f"empty {parsed.scheme} target")
        return None
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        raise ValueError(f"unsupported URL scheme {parsed.scheme}")
    if parsed.netloc:
        if not parsed.scheme:
            raise ValueError("protocol-relative URL")
        if parsed.netloc != urlparse(domain).netloc:
            return None

    fragment = unquote(parsed.fragment) or None
    url_path = unquote(parsed.path)
    if not url_path:
        return source, fragment

    candidate = (
        root / url_path.lstrip("/")
        if url_path.startswith("/")
        else source.parent / url_path
    )
    if url_path.endswith("/"):
        candidate = candidate / "index.html"
    elif not candidate.suffix:
        directory_index = candidate / "index.html"
        html_file = candidate.with_suffix(".html")
        if directory_index.exists():
            candidate = directory_index
        elif html_file.exists():
            candidate = html_file

    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("local URL escapes repository root")
    return resolved, fragment


def json_objects(value: object) -> list[dict[str, object]]:
    objects: list[dict[str, object]] = []
    if isinstance(value, dict):
        objects.append(value)
        for child in value.values():
            objects.extend(json_objects(child))
    elif isinstance(value, list):
        for child in value:
            objects.extend(json_objects(child))
    return objects


def has_type(node: dict[str, object], type_name: str) -> bool:
    value = node.get("@type")
    if isinstance(value, str):
        return value == type_name
    return isinstance(value, list) and type_name in value


def one(values: list[str], label: str, errors: list[str]) -> str | None:
    if len(values) != 1:
        errors.append(f"{label}: expected exactly one, found {len(values)}")
        return None
    if not values[0]:
        errors.append(f"{label}: value is empty")
        return None
    return values[0]


def parse_headers(path: Path) -> dict[str, list[str]]:
    rules: dict[str, list[str]] = defaultdict(list)
    current: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if not raw_line[0].isspace():
            current = raw_line.strip()
            rules.setdefault(current, [])
        elif current:
            rules[current].append(raw_line.strip())
    return rules


def validate_artifact_boundary(
    root: Path, source_root: Path, errors: list[str]
) -> None:
    expected = set(PUBLIC_FILES)
    actual_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    missing = sorted(expected - actual_files)
    unexpected = sorted(actual_files - expected)
    if missing:
        errors.append(f"artifact missing allowlisted files: {missing}")
    if unexpected:
        errors.append(f"artifact contains unexpected files: {unexpected}")

    symlinks = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_symlink()
    )
    if symlinks:
        errors.append(f"artifact contains symlinks: {symlinks}")

    forbidden_names = {"README.md", ".gitignore", "dist-manifest.json"}
    forbidden_dirs = {".git", ".github", "docs", "scripts", "tmp", "__pycache__"}
    for relative in sorted(actual_files):
        path = Path(relative)
        if path.name in forbidden_names or forbidden_dirs.intersection(path.parts):
            errors.append(f"artifact exposes internal file: {relative}")
        if path.suffix.lower() == ".py" or path.name.endswith(".pyc"):
            errors.append(f"artifact exposes Python source/cache: {relative}")

    local_markers = (
        "/Users/",
        "klicy",
        "localhost",
        "127.0.0.1",
        "file://",
        "codex-file-citation",
    )
    text_suffixes = {".html", ".css", ".txt", ".xml", ".webmanifest", ""}
    for relative in sorted(actual_files):
        path = root / relative
        if path.suffix.lower() not in text_suffixes and path.name not in {
            "_headers", "_redirects"
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"artifact text file is not UTF-8: {relative}")
            continue
        for marker in local_markers:
            if marker.lower() in text.lower():
                errors.append(f"artifact exposes local marker {marker!r}: {relative}")

    for relative in sorted(actual_files):
        path = root / relative
        references: list[str] = []
        if path.suffix.lower() == ".html":
            parser = ReferenceParser()
            parser.feed(path.read_text(encoding="utf-8"))
            references = parser.references
        elif path.suffix.lower() == ".css":
            if "url(" in path.read_text(encoding="utf-8").lower():
                errors.append(
                    f"artifact CSS url() requires explicit parser support: {relative}"
                )
        elif path.name == "site.webmanifest":
            try:
                webmanifest = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"site.webmanifest: invalid JSON: {exc}")
            else:
                for icon in webmanifest.get("icons", []):
                    if isinstance(icon, dict) and isinstance(icon.get("src"), str):
                        references.append(icon["src"])
        for reference in references:
            try:
                target = local_reference(relative, reference)
            except RuntimeError as exc:
                errors.append(str(exc))
                continue
            if target is not None and target != relative and target not in actual_files:
                errors.append(
                    f"artifact reference is missing: {relative}: {reference} -> {target}"
                )

    if not MANIFEST.exists():
        errors.append("missing internal dist-manifest.json")
    else:
        try:
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"dist-manifest.json cannot be parsed: {exc}")
        else:
            records = manifest.get("files", [])
            if not isinstance(records, list):
                errors.append("dist-manifest.json files must be an array")
                records = []
            record_paths = {
                record.get("path") for record in records if isinstance(record, dict)
            }
            if record_paths != expected:
                errors.append("dist-manifest.json file set differs from allowlist")
            for record in records:
                if not isinstance(record, dict):
                    continue
                relative = record.get("path")
                if not isinstance(relative, str) or relative not in actual_files:
                    continue
                artifact = root / relative
                if record.get("size") != artifact.stat().st_size:
                    errors.append(f"manifest size mismatch: {relative}")
                if record.get("sha256") != sha256(artifact):
                    errors.append(f"manifest hash mismatch: {relative}")
                if record.get("category") != PUBLIC_FILES.get(relative):
                    errors.append(f"manifest category mismatch: {relative}")

    pdf_relative = "papers/the-quantity-and-size-of-microloans.pdf"
    artifact_pdf = root / pdf_relative
    source_pdf = source_root / pdf_relative
    if artifact_pdf.is_file() and source_pdf.is_file():
        if sha256(artifact_pdf) != sha256(source_pdf):
            errors.append("PDF FREEZE VIOLATION: dist PDF differs from accepted source")


def validate(
    root: Path = ROOT,
    domain: str = DOMAIN,
    *,
    source_root: Path | None = None,
    artifact: bool = False,
) -> tuple[list[str], list[str]]:
    root = root.resolve()
    source_root = (source_root or root).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    if artifact:
        validate_artifact_boundary(root, source_root, errors)

    html_files = sorted(
        path
        for path in root.rglob("*.html")
        if ".git" not in path.parts
        and path.name not in VERIFICATION_HTML
        and (
            artifact
            or not {"dist", "tmp", "__pycache__"}.intersection(
                path.relative_to(root).parts
            )
        )
    )
    pages: dict[Path, Page] = {}
    for path in html_files:
        try:
            pages[path.resolve()] = parse_page(path)
        except (OSError, UnicodeError) as exc:
            errors.append(f"{path.relative_to(root)}: cannot parse HTML: {exc}")

    if not pages:
        errors.append("no deployable HTML pages discovered")

    indexable_pages = {
        path: page for path, page in pages.items() if page.indexable
    }

    for path, page in pages.items():
        relative = path.relative_to(root)
        one(page.titles, f"{relative} title", errors)
        one(page.metas.get("description", []), f"{relative} description", errors)
        one(page.metas.get("robots", []), f"{relative} robots meta", errors)
        if not page.lang:
            errors.append(f"{relative}: missing html lang")
        if len(page.main_ids) != 1:
            errors.append(
                f"{relative}: expected one main landmark, found {len(page.main_ids)}"
            )
        duplicate_ids = sorted(
            identifier for identifier, count in page.ids.items() if count > 1
        )
        if duplicate_ids:
            errors.append(f"{relative}: duplicate element IDs {duplicate_ids}")
        levels = [level for level, _ in page.headings]
        if levels.count(1) != 1:
            errors.append(f"{relative}: expected exactly one H1")
        for previous, current in zip(levels, levels[1:]):
            if current > previous + 1:
                errors.append(
                    f"{relative}: heading jumps from H{previous} to H{current}"
                )
        for level, attributes in page.headings:
            if level == 1 and (
                "hidden" in attributes
                or attributes.get("aria-hidden") == "true"
                or "display:none" in (attributes.get("style") or "").replace(" ", "")
            ):
                errors.append(f"{relative}: primary H1 is explicitly hidden")
        for image in page.images:
            if image.get("alt") is None:
                errors.append(
                    f"{relative}: image {image.get('src')} is missing alt"
                )
            if not image.get("width") or not image.get("height"):
                errors.append(
                    f"{relative}: image {image.get('src')} needs dimensions"
                )
        for href in page.hrefs:
            try:
                target = resolve_local_target(root, path, href, domain)
            except ValueError as exc:
                errors.append(f"{relative}: invalid link {href!r}: {exc}")
                continue
            if target is None:
                continue
            target_path, fragment = target
            if not target_path.exists():
                errors.append(f"{relative}: broken internal link {href}")
                continue
            if fragment and target_path.suffix.lower() in {"", ".html"}:
                target_page = pages.get(target_path.resolve())
                if target_page is None:
                    errors.append(
                        f"{relative}: fragment points to unvalidated HTML {href}"
                    )
                elif fragment not in target_page.ids:
                    errors.append(f"{relative}: missing fragment target {href}")

        if "#main-content" not in page.skip_targets:
            errors.append(f"{relative}: missing skip link to #main-content")
        if "main-content" not in page.ids:
            errors.append(f"{relative}: missing #main-content target")

        if page.indexable:
            canonical = one(
                page.canonicals, f"{relative} canonical", errors
            )
            if canonical:
                if not valid_canonical(canonical, domain):
                    errors.append(f"{relative}: malformed canonical {canonical}")
                expected = f"{domain}{page_route(path, root)}"
                if canonical != expected:
                    errors.append(
                        f"{relative}: canonical {canonical} does not match {expected}"
                    )
            if "index" not in page.robots_tokens:
                errors.append(f"{relative}: missing explicit index directive")
            for name in ("author", "twitter:card", "twitter:title",
                         "twitter:description", "twitter:image",
                         "twitter:image:alt"):
                one(page.metas.get(name, []), f"{relative} meta {name}", errors)
            for prop in ("og:type", "og:url", "og:title", "og:description",
                         "og:image", "og:image:secure_url", "og:image:width",
                         "og:image:height", "og:image:alt"):
                value = one(
                    page.property_metas.get(prop, []),
                    f"{relative} property {prop}",
                    errors,
                )
                if prop == "og:url" and value and value != canonical:
                    errors.append(
                        f"{relative}: og:url does not match canonical"
                    )
            og_image_values = page.property_metas.get("og:image", [])
            secure_values = page.property_metas.get("og:image:secure_url", [])
            twitter_images = page.metas.get("twitter:image", [])
            if len(og_image_values) == 1:
                og_image = og_image_values[0]
                parsed_image = urlparse(og_image)
                if parsed_image.scheme != "https" or not parsed_image.netloc:
                    errors.append(f"{relative}: og:image must be absolute HTTPS")
                try:
                    image_target = resolve_local_target(root, path, og_image, domain)
                except ValueError as exc:
                    errors.append(f"{relative}: invalid og:image: {exc}")
                else:
                    if image_target is not None:
                        image_path = image_target[0]
                        if not image_path.is_file():
                            errors.append(f"{relative}: og:image file is missing")
                        elif image_path.suffix.lower() == ".png":
                            actual = png_dimensions(image_path)
                            try:
                                declared = (
                                    int(page.property_metas["og:image:width"][0]),
                                    int(page.property_metas["og:image:height"][0]),
                                )
                            except (IndexError, ValueError):
                                declared = None
                            if actual and declared and actual != declared:
                                errors.append(
                                    f"{relative}: og:image dimensions {declared} "
                                    f"do not match file {actual}"
                                )
                if secure_values == [og_image] and twitter_images != [og_image]:
                    errors.append(
                        f"{relative}: twitter:image must match the intentional preview"
                    )
            if len(og_image_values) == 1 and secure_values != og_image_values:
                errors.append(f"{relative}: og:image:secure_url must match og:image")
        else:
            if page.canonicals:
                warnings.append(
                    f"{relative}: noindex page has a canonical; review intent"
                )

    for field_name, values in {
        "title": [page.titles[0] for page in indexable_pages.values()
                  if len(page.titles) == 1],
        "description": [page.metas["description"][0]
                        for page in indexable_pages.values()
                        if len(page.metas.get("description", [])) == 1],
        "canonical": [page.canonicals[0]
                      for page in indexable_pages.values()
                      if len(page.canonicals) == 1],
    }.items():
        duplicates = sorted(
            value for value, count in Counter(values).items() if count > 1
        )
        if duplicates:
            errors.append(f"duplicate {field_name} across pages: {duplicates}")

    definitions: dict[str, list[tuple[Path, dict[str, object]]]] = defaultdict(list)
    references: set[str] = set()
    typed_without_id: list[tuple[Path, str]] = []
    for path, page in pages.items():
        for block_number, block in enumerate(page.json_ld, start=1):
            try:
                data = json.loads(block)
            except json.JSONDecodeError as exc:
                errors.append(
                    f"{path.relative_to(root)} JSON-LD {block_number}: {exc}"
                )
                continue
            for node in json_objects(data):
                identifier = node.get("@id")
                if isinstance(identifier, str):
                    references.add(identifier)
                    if len(node) > 1:
                        definitions[identifier].append((path, node))
                node_type = node.get("@type")
                if node_type and not isinstance(identifier, str):
                    type_values = (
                        [node_type] if isinstance(node_type, str) else node_type
                    )
                    if isinstance(type_values, list):
                        for type_value in type_values:
                            if type_value in {"Person", "WebSite", "ProfilePage"}:
                                typed_without_id.append((path, str(type_value)))

    for identifier, nodes in sorted(definitions.items()):
        if len(nodes) > 1:
            locations = [str(path.relative_to(root)) for path, _ in nodes]
            errors.append(
                f"JSON-LD @id {identifier} has conflicting definitions in {locations}"
            )
        if identifier.startswith(domain) and not valid_canonical(
            identifier.split("#", 1)[0] or f"{domain}/", domain
        ):
            errors.append(f"JSON-LD has malformed internal @id {identifier}")
    for path, type_name in typed_without_id:
        errors.append(
            f"{path.relative_to(root)}: JSON-LD {type_name} needs stable @id"
        )
    unresolved = sorted(
        identifier
        for identifier in references
        if identifier.startswith(domain) and identifier not in definitions
    )
    if unresolved:
        errors.append(f"JSON-LD unresolved internal @id references: {unresolved}")

    scholarly_articles = [
        (path, node)
        for nodes in definitions.values()
        for path, node in nodes
        if has_type(node, "ScholarlyArticle")
    ]
    for path, article in scholarly_articles:
        page = pages[path.resolve()]
        relative = path.relative_to(root)
        citation_title = one(
            page.metas.get("citation_title", []),
            f"{relative} citation_title",
            errors,
        )
        citation_author = one(
            page.metas.get("citation_author", []),
            f"{relative} citation_author",
            errors,
        )
        citation_date = one(
            page.metas.get("citation_publication_date", []),
            f"{relative} citation_publication_date",
            errors,
        )
        citation_pdf = one(
            page.metas.get("citation_pdf_url", []),
            f"{relative} citation_pdf_url",
            errors,
        )
        one(
            page.metas.get("citation_abstract", []),
            f"{relative} citation_abstract",
            errors,
        )
        if citation_title and citation_title != article.get("headline"):
            errors.append(
                f"{relative}: citation title and ScholarlyArticle headline differ"
            )
        if citation_author != "Kexing Yan":
            errors.append(f"{relative}: citation author must be Kexing Yan")
        if article.get("author") != {"@id": PERSON_ID}:
            errors.append(
                f"{relative}: ScholarlyArticle author must reference canonical Person"
            )
        if citation_date and citation_date.replace("/", "-") != article.get(
            "dateCreated"
        ):
            errors.append(
                f"{relative}: citation date and ScholarlyArticle dateCreated differ"
            )
        if "datePublished" in article:
            errors.append(
                f"{relative}: working paper must not treat its completion date "
                "as a verified publication date"
            )
        if citation_pdf:
            try:
                pdf_target = resolve_local_target(root, path, citation_pdf, domain)
            except ValueError as exc:
                errors.append(f"{relative}: invalid citation PDF URL: {exc}")
            else:
                if pdf_target is None or not pdf_target[0].is_file():
                    errors.append(f"{relative}: citation PDF is not a local file")
        status = str(article.get("creativeWorkStatus", "")).strip()
        if not status or status.lower() not in page.visible_text.lower():
            errors.append(
                f"{relative}: ScholarlyArticle status must be visible on the page"
            )
        for unsupported_meta in (
            "citation_doi",
            "citation_journal_title",
            "citation_volume",
            "citation_issue",
            "citation_publisher",
        ):
            if page.metas.get(unsupported_meta):
                errors.append(
                    f"{relative}: unsupported journal metadata {unsupported_meta}"
                )

    person_nodes = definitions.get(PERSON_ID, [])
    if len(person_nodes) != 1:
        errors.append("JSON-LD must define the canonical Person exactly once")
    else:
        _, person = person_nodes[0]
        if not has_type(person, "Person"):
            errors.append("canonical Person @id has the wrong type")
        if person.get("name") != "Kexing Yan":
            errors.append("canonical Person name must be Kexing Yan")
        alternate = person.get("alternateName")
        alternates = alternate if isinstance(alternate, list) else [alternate]
        if "严可行" not in alternates:
            errors.append("canonical Person is missing alternateName 严可行")
        if "alumniOf" in person:
            errors.append("current-student Person must not use alumniOf")
        if "jobTitle" in person:
            warnings.append(
                "canonical Person uses jobTitle; verify it is a real job title"
            )

    website_nodes = definitions.get(WEBSITE_ID, [])
    if len(website_nodes) != 1:
        errors.append("JSON-LD must define the canonical WebSite exactly once")
    elif (
        not has_type(website_nodes[0][1], "WebSite")
        or website_nodes[0][1].get("url") != f"{domain}/"
    ):
        errors.append("canonical WebSite type or URL is inconsistent")

    profile_nodes = definitions.get(PROFILE_ID, [])
    if len(profile_nodes) != 1:
        errors.append("JSON-LD must define the ProfilePage exactly once")
    else:
        profile = profile_nodes[0][1]
        main_entity = profile.get("mainEntity")
        if main_entity != {"@id": PERSON_ID}:
            errors.append("ProfilePage.mainEntity must reference canonical Person")
        modified = profile.get("dateModified")
        if not isinstance(modified, str):
            errors.append("ProfilePage.dateModified must be a string")
        else:
            parsed_modified = parse_profile_datetime(modified)
            if parsed_modified is None:
                errors.append(
                    "ProfilePage.dateModified must be a full ISO 8601 DateTime "
                    "with seconds and timezone"
                )
            elif parsed_modified.astimezone(timezone.utc) > (
                datetime.now(timezone.utc) + timedelta(minutes=5)
            ):
                errors.append("ProfilePage.dateModified must not be in the future")

    not_found = pages.get((root / "404.html").resolve())
    if not_found is None:
        errors.append("missing deployable 404.html")
    elif "noindex" not in not_found.robots_tokens:
        errors.append("404.html must be noindex")

    robots_path = root / "robots.txt"
    if not robots_path.exists():
        errors.append("missing robots.txt")
    else:
        robots = robots_path.read_text(encoding="utf-8")
        robot_groups: dict[str, list[str]] = defaultdict(list)
        current_agents: list[str] = []
        directives_started = False
        sitemap_directives: list[str] = []
        for raw_line in robots.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            key, value = (part.strip() for part in line.split(":", 1))
            lower_key = key.lower()
            if lower_key == "user-agent":
                if directives_started:
                    current_agents = []
                    directives_started = False
                current_agents.append(value)
            elif lower_key == "sitemap":
                sitemap_directives.append(value)
            elif current_agents:
                directives_started = True
                for agent in current_agents:
                    robot_groups[agent].append(f"{lower_key}:{value}")
        allowed = (
            "Googlebot", "Bingbot", "OAI-SearchBot", "ChatGPT-User",
            "Claude-SearchBot", "Claude-User", "PerplexityBot",
            "Perplexity-User", "Google-Extended", "*",
        )
        blocked = ("GPTBot", "ClaudeBot")
        for agent in allowed:
            if "allow:/" not in robot_groups.get(agent, []):
                errors.append(f"robots.txt: {agent} must allow /")
        for agent in blocked:
            if "disallow:/" not in robot_groups.get(agent, []):
                errors.append(f"robots.txt: {agent} must disallow /")
        if sitemap_directives != [f"{domain}/sitemap.xml"]:
            errors.append("robots.txt: expected one canonical sitemap directive")

    redirect_sources: set[str] = set()
    redirects_path = root / "_redirects"
    if redirects_path.exists():
        for line_number, raw_line in enumerate(
            redirects_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) < 2:
                errors.append(f"_redirects:{line_number}: malformed rule")
                continue
            source, destination = fields[:2]
            status = fields[2] if len(fields) > 2 else "302"
            if source in redirect_sources:
                errors.append(
                    f"_redirects:{line_number}: duplicate source {source}"
                )
            redirect_sources.add(source)
            if not source.startswith("/") or not destination:
                errors.append(
                    f"_redirects:{line_number}: source and destination must be paths"
                )
            if status not in {"200", "301", "302", "303", "307", "308"}:
                errors.append(
                    f"_redirects:{line_number}: unsupported status {status}"
                )
            if source == "/*" and destination in {"/", "/index.html"} and status == "200":
                errors.append("_redirects: SPA fallback would create soft 404s")
            try:
                target = resolve_local_target(
                    root, root / "index.html", destination, domain
                )
            except ValueError as exc:
                errors.append(
                    f"_redirects:{line_number}: invalid destination: {exc}"
                )
            else:
                if target is not None and not target[0].exists():
                    errors.append(
                        f"_redirects:{line_number}: missing destination {destination}"
                    )

    sitemap_path = root / "sitemap.xml"
    sitemap_urls: list[str] = []
    sitemap_lastmods: dict[str, str] = {}
    if not sitemap_path.exists():
        errors.append("missing sitemap.xml")
    else:
        try:
            tree = ElementTree.parse(sitemap_path)
            namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            for url_node in tree.findall(".//sm:url", namespace):
                locations = url_node.findall("sm:loc", namespace)
                if len(locations) != 1 or not locations[0].text:
                    errors.append("sitemap.xml: each url needs one loc")
                    continue
                url = locations[0].text.strip()
                sitemap_urls.append(url)
                if not valid_canonical(url, domain):
                    errors.append(f"sitemap.xml: malformed canonical URL {url}")
                parsed = urlparse(url)
                if parsed.path == "/404.html":
                    errors.append("sitemap.xml: 404 page must not be included")
                local = root / parsed.path.lstrip("/")
                if parsed.path == "/":
                    local = root / "index.html"
                elif parsed.path.endswith("/"):
                    local = local / "index.html"
                if not local.exists():
                    errors.append(f"sitemap.xml: missing local content for {url}")
                if parsed.path in redirect_sources:
                    errors.append(f"sitemap.xml: URL is redirected {url}")
                lastmods = url_node.findall("sm:lastmod", namespace)
                if len(lastmods) > 1:
                    errors.append(f"sitemap.xml: duplicate lastmod for {url}")
                elif lastmods:
                    value = (lastmods[0].text or "").strip()
                    sitemap_lastmods[url] = value
                    try:
                        parsed_date = date.fromisoformat(value)
                        if parsed_date > date.today():
                            errors.append(
                                f"sitemap.xml: future lastmod {value} for {url}"
                            )
                    except ValueError:
                        errors.append(
                            f"sitemap.xml: invalid lastmod {value!r} for {url}"
                        )
        except ElementTree.ParseError as exc:
            errors.append(f"sitemap.xml: invalid XML: {exc}")

    if len(sitemap_urls) != len(set(sitemap_urls)):
        errors.append("sitemap.xml: duplicate URLs")
    canonical_urls = {
        page.canonicals[0]
        for page in indexable_pages.values()
        if len(page.canonicals) == 1
    }
    missing = sorted(canonical_urls - set(sitemap_urls))
    if missing:
        errors.append(f"sitemap.xml: missing indexable canonicals {missing}")

    dates_path = source_root / "scripts" / "site_dates.json"
    if not dates_path.exists():
        errors.append("missing scripts/site_dates.json date source")
    else:
        try:
            date_data = json.loads(dates_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"scripts/site_dates.json: cannot parse: {exc}")
        else:
            page_dates = date_data.get("pages", {})
            if not isinstance(page_dates, dict):
                errors.append("scripts/site_dates.json: pages must be an object")
                page_dates = {}
            discovered_routes = {
                page_route(path, root) for path in indexable_pages
            }
            if set(page_dates) != discovered_routes:
                errors.append(
                    "scripts/site_dates.json: page routes differ from indexable "
                    f"HTML routes ({sorted(page_dates)} vs {sorted(discovered_routes)})"
                )
            works = date_data.get("works", {})
            for route, record in page_dates.items():
                if not isinstance(record, dict):
                    errors.append(f"date source {route}: record must be an object")
                    continue
                modified = str(record.get("dateModified", ""))
                sitemap_date = str(record.get("sitemapLastmod", ""))
                try:
                    date.fromisoformat(modified)
                    date.fromisoformat(sitemap_date)
                except ValueError:
                    errors.append(f"date source {route}: invalid ISO date")
                page_path = next(
                    (p for p in indexable_pages if page_route(p, root) == route),
                    None,
                )
                if page_path is None:
                    continue
                page = indexable_pages[page_path]
                if modified not in page.time_datetimes:
                    errors.append(
                        f"{page_path.relative_to(root)}: visible updated date "
                        f"does not match date source {modified}"
                    )
                node_id = PROFILE_ID if route == "/" else f"{domain}{route}#webpage"
                nodes = definitions.get(node_id, [])
                expected_structured_modified: object = modified
                if route == "/":
                    expected_structured_modified = record.get(
                        "structuredDataDateModified"
                    )
                    parsed_structured_modified = parse_profile_datetime(
                        expected_structured_modified
                    )
                    if parsed_structured_modified is None:
                        errors.append(
                            "date source /: invalid ProfilePage "
                            "structuredDataDateModified"
                        )
                    elif parsed_structured_modified.date().isoformat() != modified:
                        errors.append(
                            "date source /: ProfilePage datetime calendar date "
                            "differs from page modification date"
                        )
                if (
                    len(nodes) != 1
                    or nodes[0][1].get("dateModified")
                    != expected_structured_modified
                ):
                    errors.append(
                        f"{route}: JSON-LD dateModified does not match date source"
                    )
                if sitemap_lastmods.get(f"{domain}{route}") != sitemap_date:
                    errors.append(
                        f"{route}: sitemap lastmod does not match date source"
                    )
                work_key = record.get("work")
                if work_key:
                    work = works.get(work_key, {}) if isinstance(works, dict) else {}
                    created = str(work.get("dateCreated", ""))
                    citation = str(work.get("citationDate", ""))
                    articles = [
                        node for p, node in scholarly_articles if p.resolve() == page_path
                    ]
                    if len(articles) != 1 or articles[0].get("dateCreated") != created:
                        errors.append(
                            f"{route}: ScholarlyArticle dateCreated differs from date source"
                        )
                    citation_values = page.metas.get("citation_publication_date", [])
                    if [value.replace("/", "-") for value in citation_values] != [citation]:
                        errors.append(
                            f"{route}: citation date differs from date source"
                        )
                    if created not in page.time_datetimes:
                        errors.append(
                            f"{route}: visible work date differs from date source"
                        )
            file_dates = date_data.get("files", {})
            if isinstance(file_dates, dict):
                for route, record in file_dates.items():
                    if not isinstance(record, dict):
                        errors.append(f"date source {route}: file record must be an object")
                        continue
                    expected = str(record.get("sitemapLastmod", ""))
                    if sitemap_lastmods.get(f"{domain}{route}") != expected:
                        errors.append(
                            f"{route}: file sitemap lastmod differs from date source"
                        )
            copyright_year = str(date_data.get("copyrightYear", ""))
            for path, page in pages.items():
                if f"© {copyright_year}" not in page.visible_text:
                    errors.append(
                        f"{path.relative_to(root)}: copyright year differs from date source"
                    )

    llms_path = root / "llms.txt"
    if llms_path.exists():
        llms_text = llms_path.read_text(encoding="utf-8")
        if "localhost" in llms_text or "127.0.0.1" in llms_text:
            errors.append("llms.txt: local development URL exposed")
        if "@" in llms_text:
            errors.append("llms.txt: contact information should not be duplicated")
        llms_urls = {
            token.rstrip(").,>")
            for token in llms_text.replace("(", " ").replace(")", " ").split()
            if token.startswith("https://")
        }
        for url in sorted(llms_urls):
            parsed = urlparse(url)
            if parsed.netloc == urlparse(domain).netloc:
                try:
                    target = resolve_local_target(
                        root, root / "index.html", url, domain
                    )
                except ValueError as exc:
                    errors.append(f"llms.txt: invalid URL {url}: {exc}")
                else:
                    if target is None or not target[0].exists():
                        errors.append(f"llms.txt: missing local resource {url}")

    headers_path = root / "_headers"
    if not headers_path.exists():
        warnings.append("missing _headers; response-header policy not validated")
    else:
        header_rules = parse_headers(headers_path)
        resume_headers = " ".join(header_rules.get("/assets/resume/*", []))
        if "X-Robots-Tag: noindex" not in resume_headers:
            errors.append("_headers: résumé PDFs must retain X-Robots-Tag noindex")
        for obsolete in (
            "/docs/*",
            "/scripts/*",
            "/README.md",
            "/scripts/site_dates.json",
        ):
            if obsolete in header_rules:
                errors.append(
                    f"_headers: obsolete internal-resource rule remains: {obsolete}"
                )
        pdf_headers = " ".join(
            header_rules.get(
                "/papers/the-quantity-and-size-of-microloans.pdf", []
            )
        )
        for expected in (
            "Content-Type: application/pdf",
            "Content-Disposition: inline",
            "Content-Language: en-CA",
            "X-Content-Type-Options: nosniff",
        ):
            if expected not in pdf_headers:
                errors.append(f"_headers: research PDF missing {expected}")
        llms_headers = " ".join(header_rules.get("/llms.txt", []))
        if "Content-Type: text/plain; charset=utf-8" not in llms_headers:
            errors.append("_headers: llms.txt needs an explicit text content type")
        if artifact:
            for pattern in header_rules:
                if pattern.endswith("*"):
                    prefix = pattern.lstrip("/").removesuffix("*")
                    if not any(path.startswith(prefix) for path in PUBLIC_FILES):
                        errors.append(
                            f"_headers pattern matches no deployed file: {pattern}"
                        )
                else:
                    target = pattern.lstrip("/")
                    if target not in PUBLIC_FILES:
                        errors.append(f"_headers path is not deployed: {pattern}")

    return sorted(set(errors)), sorted(set(warnings))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        help="Validate a deployment artifact such as dist/ instead of the source tree.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.root is None:
        errors, warnings = validate()
        label = "source tree"
    else:
        errors, warnings = validate(
            args.root,
            source_root=ROOT,
            artifact=args.root.resolve() != ROOT.resolve(),
        )
        label = str(args.root)
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        print(f"Site validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Site validation passed: {label}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
