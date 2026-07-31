#!/usr/bin/env python3
"""Build the explicit, deterministic Cloudflare Pages artifact in dist/."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
MANIFEST = ROOT / "dist-manifest.json"
DOMAIN = "kexingyan.com"

# Public deployment is opt-in. Additions require an explicit review here.
PUBLIC_FILES: dict[str, str] = {
    "index.html": "html",
    "404.html": "html-error",
    "robots.txt": "discovery",
    "sitemap.xml": "discovery",
    "llms.txt": "discovery",
    "site.webmanifest": "manifest",
    "_headers": "cloudflare-config",
    "_redirects": "cloudflare-config",
    "baidu_verify_codeva-vWXLKxDtXl.html": "ownership-verification",
    "assets/css/research.css": "stylesheet",
    "assets/icons/apple-touch-icon.png": "icon",
    "assets/icons/favicon-16x16.png": "icon",
    "assets/icons/favicon-32x32.png": "icon",
    "assets/icons/favicon-48x48.png": "icon",
    "assets/icons/favicon-192x192.png": "icon",
    "assets/icons/favicon-512x512.png": "icon",
    "assets/images/kexing-yan-open-graph.png": "social-preview",
    "assets/resume/Kexing-Yan-Resume-EN.pdf": "resume",
    "assets/resume/Kexing-Yan-Resume-ZH.pdf": "resume",
    "research/microloan-quantity-size/index.html": "html",
    "papers/the-quantity-and-size-of-microloans.pdf": "research-pdf",
}

FORBIDDEN_TOP_LEVEL = {
    ".git",
    ".github",
    ".gitignore",
    "README.md",
    "docs",
    "scripts",
    "tmp",
}


class ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = dict(attrs)
        for name in ("href", "src"):
            value = (values.get(name) or "").strip()
            if value:
                self.references.append(value)
        if tag == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            if key in {"og:image", "og:image:secure_url", "twitter:image"}:
                value = (values.get("content") or "").strip()
                if value:
                    self.references.append(value)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_safe_file(root: Path, relative: str) -> Path:
    candidate = root / relative
    resolved_root = root.resolve()
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"required public file is missing: {relative}") from exc
    if not resolved.is_relative_to(resolved_root):
        raise RuntimeError(f"public file escapes source root: {relative}")
    cursor = candidate
    while cursor != root:
        if cursor.is_symlink():
            raise RuntimeError(f"public path contains a symlink: {relative}")
        cursor = cursor.parent
    if not candidate.is_file():
        raise RuntimeError(f"public path is not a regular file: {relative}")
    return candidate


def local_reference(source_relative: str, reference: str) -> str | None:
    parsed = urlparse(reference)
    if parsed.scheme in {"mailto", "tel", "data"}:
        return None
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        raise RuntimeError(
            f"unsupported URL scheme in {source_relative}: {reference}"
        )
    if parsed.netloc and parsed.netloc.lower() != DOMAIN:
        return None
    raw_path = unquote(parsed.path)
    if not raw_path:
        return source_relative
    if raw_path.startswith("/"):
        target = Path(raw_path.lstrip("/"))
    else:
        target = Path(source_relative).parent / raw_path
    if raw_path.endswith("/"):
        target /= "index.html"
    elif not target.suffix:
        directory_index = target / "index.html"
        html_file = target.with_suffix(".html")
        if directory_index.as_posix() in PUBLIC_FILES:
            target = directory_index
        elif html_file.as_posix() in PUBLIC_FILES:
            target = html_file
    normalized = Path(*[part for part in target.parts if part not in {"", "."}])
    if ".." in normalized.parts:
        raise RuntimeError(
            f"path traversal in {source_relative}: {reference}"
        )
    return normalized.as_posix()


def validate_allowlist_references(source_root: Path) -> None:
    allowed = set(PUBLIC_FILES)
    for relative in sorted(allowed):
        source = source_root / relative
        if source.suffix.lower() == ".html":
            parser = ReferenceParser()
            parser.feed(source.read_text(encoding="utf-8"))
            references = parser.references
        elif source.suffix.lower() == ".css":
            # Current CSS contains no url() references. Rejecting any future
            # syntax until it is explicitly parsed prevents silent omissions.
            css = source.read_text(encoding="utf-8")
            if "url(" in css.lower():
                raise RuntimeError(
                    f"CSS url() reference requires build parser review: {relative}"
                )
            references = []
        elif source.name == "site.webmanifest":
            try:
                webmanifest = json.loads(source.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid site.webmanifest: {exc}") from exc
            references = [
                icon["src"]
                for icon in webmanifest.get("icons", [])
                if isinstance(icon, dict) and isinstance(icon.get("src"), str)
            ]
        else:
            continue
        for reference in references:
            target = local_reference(relative, reference)
            if target is None or target == relative:
                continue
            if target not in allowed:
                raise RuntimeError(
                    f"{relative} references non-public or missing file: "
                    f"{reference} -> {target}"
                )


def prepare_output(output_root: Path, source_root: Path) -> None:
    expected = source_root.resolve() / "dist"
    if output_root.resolve(strict=False) != expected:
        raise RuntimeError(f"refusing to replace unexpected output path: {output_root}")
    if output_root.is_symlink():
        raise RuntimeError("refusing to replace a symlinked dist directory")
    if output_root.exists():
        if not output_root.is_dir():
            raise RuntimeError("dist exists but is not a directory")
        shutil.rmtree(output_root)
    output_root.mkdir(mode=0o755)


def build(
    source_root: Path = ROOT,
    output_root: Path = DIST,
    manifest_path: Path = MANIFEST,
) -> dict[str, object]:
    source_root = source_root.resolve()
    if output_root.resolve(strict=False) != source_root / "dist":
        raise RuntimeError("output must be the source root's dist directory")

    sources: dict[str, Path] = {}
    for relative in sorted(PUBLIC_FILES):
        if Path(relative).parts[0] in FORBIDDEN_TOP_LEVEL:
            raise RuntimeError(f"forbidden public allowlist entry: {relative}")
        sources[relative] = ensure_safe_file(source_root, relative)

    casefolded = [relative.casefold() for relative in sources]
    if len(casefolded) != len(set(casefolded)):
        raise RuntimeError("case-insensitive public path conflict")
    validate_allowlist_references(source_root)
    prepare_output(output_root, source_root)

    records: list[dict[str, object]] = []
    for relative, source in sources.items():
        destination = output_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        records.append(
            {
                "path": relative,
                "size": destination.stat().st_size,
                "sha256": sha256(destination),
                "category": PUBLIC_FILES[relative],
            }
        )

    actual = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*")
        if path.is_file()
    }
    expected = set(PUBLIC_FILES)
    if actual != expected:
        raise RuntimeError(
            f"artifact file set differs from allowlist: "
            f"missing={sorted(expected - actual)} unexpected={sorted(actual - expected)}"
        )
    if any(path.is_symlink() for path in output_root.rglob("*")):
        raise RuntimeError("deployment artifact contains a symlink")

    manifest: dict[str, object] = {
        "schemaVersion": 1,
        "fileCount": len(records),
        "totalSize": sum(int(record["size"]) for record in records),
        "files": records,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"Built {len(records)} files in {output_root.name}/ "
        f"({manifest['totalSize']} bytes); manifest: {manifest_path.name}"
    )
    return manifest


def main() -> int:
    try:
        build()
    except (OSError, UnicodeError, RuntimeError, ValueError) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
