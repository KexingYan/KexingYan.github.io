#!/usr/bin/env python3
"""Validate the static site and both Photography asset modes."""

from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []
VARIANTS = {"thumbnail": 480, "preview": 1280, "display": 2200, "download": 1800}
PRIVATE_FIELDS = {
    "masterObjectKey",
    "sourceFilename",
    "sourceHash",
    "sourcePath",
    "sourceBytes",
    "originalWidth",
    "originalHeight",
    "processingState",
}


class DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.refs: list[str] = []
        self.canonicals: list[str] = []
        self.json_ld: list[str] = []
        self._json_buffer: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if data.get("id"):
            self.ids.add(data["id"] or "")
        for key in ("href", "src"):
            if data.get(key):
                self.refs.append(data[key] or "")
        if data.get("srcset"):
            self.refs.extend(item.strip().split()[0] for item in (data["srcset"] or "").split(","))
        if tag == "link" and data.get("rel") == "canonical" and data.get("href"):
            self.canonicals.append(data["href"] or "")
        if tag == "script" and data.get("type") == "application/ld+json":
            self._json_buffer = []

    def handle_data(self, data: str) -> None:
        if self._json_buffer is not None:
            self._json_buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._json_buffer is not None:
            self.json_ld.append("".join(self._json_buffer))
            self._json_buffer = None


def fail(message: str) -> None:
    ERRORS.append(message)


def public_target(document: Path, ref: str) -> Path | None:
    parsed = urlparse(ref)
    if parsed.scheme in {"http", "https", "mailto", "tel"} or ref.startswith("//"):
        return None
    path = unquote(parsed.path)
    if not path:
        return None
    target = ROOT / path.lstrip("/") if path.startswith("/") else document.parent / path
    if path.endswith("/") or target.is_dir():
        target /= "index.html"
    return target.resolve()


def walk_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(key)
            keys.update(walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(walk_keys(child))
    return keys


def run_checked(command: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        fail(f"Command failed: {' '.join(command)}\n{exc.stdout}{exc.stderr}")
        return None


def validate_html() -> None:
    generated_available = (ROOT / "assets" / "photography" / "generated").is_dir()
    expected_canonicals = {
        ROOT / "index.html": "https://kexingyan.com/",
        ROOT / "photography" / "index.html": "https://kexingyan.com/photography/",
        ROOT / "photography" / "license" / "index.html": "https://kexingyan.com/photography/license/",
    }
    for path in ROOT.rglob("*.html"):
        if ".git" in path.parts or "dist" in path.parts:
            continue
        parser = DocumentParser()
        parser.feed(path.read_text(encoding="utf-8"))
        for raw in parser.json_ld:
            try:
                json.loads(raw)
            except json.JSONDecodeError as exc:
                fail(f"Invalid JSON-LD in {path.relative_to(ROOT)}: {exc}")
        for ref in parser.refs:
            target = public_target(path, ref)
            optional_derivative = "/assets/photography/generated/" in ref
            if target is not None and not target.exists() and not (
                optional_derivative and not generated_available
            ):
                fail(f"Broken internal reference in {path.relative_to(ROOT)}: {ref}")
            parsed = urlparse(ref)
            if parsed.path == "" and parsed.fragment and parsed.fragment not in parser.ids:
                fail(f"Missing fragment #{parsed.fragment} in {path.relative_to(ROOT)}")
        if path in expected_canonicals and parser.canonicals != [expected_canonicals[path]]:
            fail(f"Unexpected canonical in {path.relative_to(ROOT)}: {parser.canonicals}")


def validate_seed_and_local_manifest() -> None:
    seed_path = ROOT / "data" / "photography" / "photos.seed.json"
    manifest_path = ROOT / "assets" / "photography" / "data" / "photos.json"
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    seed_photos = seed.get("photos", [])
    photos = data.get("photos", [])
    series = data.get("series", [])
    generated_available = (ROOT / "assets" / "photography" / "generated").is_dir()

    if len(seed_photos) != 14 or len(photos) != 14:
        fail(f"Expected 14 seed/published photos, found {len(seed_photos)}/{len(photos)}")
    if data.get("schemaVersion") != seed.get("schemaVersion"):
        fail("Manifest schemaVersion differs from seed")
    if data.get("publishRevision") != seed.get("publishRevision"):
        fail("Manifest publishRevision differs from seed")
    if data.get("assetMode") != "local":
        fail("Committed development manifest must use local asset mode")
    if data.get("assetBase") != "/assets/photography/generated":
        fail("Unexpected local Photography asset base")
    if [item.get("id") for item in series] != [
        "city-drifting", "accidental-colour", "quiet-objects", "garden-notes"
    ]:
        fail("Series order or identifiers do not match the approved order")

    for collection_name, collection in (("seed", seed_photos), ("manifest", photos)):
        for key in ("id", "slug"):
            values = [photo.get(key) for photo in collection]
            if None in values or len(values) != len(set(values)):
                fail(f"Missing or duplicate photo {key} in {collection_name}")
        for photo in collection:
            if not isinstance(photo.get("assetVersion"), int) or photo["assetVersion"] < 1:
                fail(f"Invalid assetVersion for {photo.get('id')} in {collection_name}")

    leaked = walk_keys(data) & PRIVATE_FIELDS
    if leaked:
        fail(f"Private manifest fields leaked: {', '.join(sorted(leaked))}")
    manifest_text = manifest_path.read_text(encoding="utf-8")
    if "originals/private" in manifest_text:
        fail("Private R2 master prefix leaked into public manifest")

    series_ids = {item["id"] for item in series}
    for photo in photos:
        photo_id = photo.get("id", "unknown")
        if photo.get("seriesId") not in series_ids:
            fail(f"Unknown seriesId for {photo_id}")
        if not photo.get("alt", "").strip():
            fail(f"Missing alt text for {photo_id}")
        asset_version = photo.get("assetVersion")
        for variant, expected_edge in VARIANTS.items():
            image_data = photo.get("images", {}).get(variant, {})
            src = image_data.get("src", "")
            expected_pattern = rf"^/assets/photography/generated/{variant}/{photo_id}-v{asset_version}-{variant}\.jpg$"
            if not re.fullmatch(expected_pattern, src):
                fail(f"Invalid versioned {variant} target for {photo_id}: {src}")
                continue
            target = public_target(ROOT / "photography" / "index.html", src)
            if target is None or not target.is_file():
                if generated_available:
                    fail(f"Missing derivative for {photo_id}: {src}")
                elif max(image_data.get("width", 0), image_data.get("height", 0)) != expected_edge:
                    fail(f"Manifest dimensions are invalid for {photo_id} {variant}")
                continue
            with Image.open(target) as image:
                if max(image.size) != expected_edge:
                    fail(f"Unexpected {variant} dimensions for {photo_id}: {image.size}")
                if image.size != (image_data.get("width"), image_data.get("height")):
                    fail(f"Manifest dimensions differ for {photo_id} {variant}")
                if 34853 in image.getexif():
                    fail(f"GPS metadata found in {photo_id} {variant}")
                if image.getexif().get(315) != "Kexing Yan":
                    fail(f"Creator metadata missing in {photo_id} {variant}")
            if target.stat().st_size != image_data.get("bytes"):
                fail(f"Manifest byte size differs for {photo_id} {variant}")
        download_src = photo.get("images", {}).get("download", {}).get("src", "")
        if "/generated/download/" not in download_src or not download_src.endswith("-download.jpg"):
            fail(f"Download does not use personal-use derivative for {photo_id}")


def validate_production_mode() -> None:
    asset_base = "https://images.example.test/photography/derivatives"
    manifest_url = "https://images.example.test/photography/manifests/current.json"
    with tempfile.TemporaryDirectory(prefix="photography-validation-") as temporary:
        temp = Path(temporary)
        local_manifest = temp / "photos.local.json"
        result = run_checked([
            sys.executable,
            str(ROOT / "scripts" / "generate_photography.py"),
            "--manifest-only",
            "--asset-mode", "local",
            "--manifest-output", str(local_manifest),
        ])
        if result is None:
            return
        committed_local = json.loads(
            (ROOT / "assets" / "photography" / "data" / "photos.json").read_text(encoding="utf-8")
        )
        if json.loads(local_manifest.read_text(encoding="utf-8")) != committed_local:
            fail("Regenerated local manifest differs from the committed development manifest")

        production_manifest = temp / "photos.production.json"
        result = run_checked([
            sys.executable,
            str(ROOT / "scripts" / "generate_photography.py"),
            "--manifest-only",
            "--asset-mode", "production",
            "--asset-base", asset_base,
            "--manifest-output", str(production_manifest),
        ])
        if result is None:
            return
        data = json.loads(production_manifest.read_text(encoding="utf-8"))
        if data.get("assetMode") != "production" or data.get("assetBase") != asset_base:
            fail("Production manifest has incorrect asset mode/base")
        if walk_keys(data) & PRIVATE_FIELDS or "originals/private" in production_manifest.read_text(encoding="utf-8"):
            fail("Production manifest contains private provenance")
        for photo in data.get("photos", []):
            for variant in VARIANTS:
                expected = f"{asset_base}/{variant}/{photo['id']}-v{photo['assetVersion']}-{variant}.jpg"
                if photo["images"][variant]["src"] != expected:
                    fail(f"Unexpected production URL for {photo['id']} {variant}")
            if "/download/" not in photo["images"]["download"]["src"]:
                fail(f"Production download is not a derivative for {photo['id']}")

        release = temp / "release"
        result = run_checked([
            sys.executable,
            str(ROOT / "scripts" / "build_photography_release.py"),
            "--output", str(release),
            "--asset-base", asset_base,
            "--manifest-url", manifest_url,
        ])
        if result is None:
            return
        if (release / "assets" / "photography" / "generated").exists():
            fail("Production release contains local generated Photography assets")
        if (release / "data").exists():
            fail("Production release contains authoritative seed data")
        if (release / "studio").exists() or (release / "assets" / "studio").exists():
            fail("Production release contains the offline-only Studio prototype")
        config_text = (release / "assets" / "photography" / "config.js").read_text(encoding="utf-8")
        if manifest_url not in config_text or '"mode": "production"' not in config_text:
            fail("Production release config does not select the R2 manifest")
        release_html = "\n".join(path.read_text(encoding="utf-8") for path in release.rglob("*.html"))
        if "/assets/photography/generated" in release_html:
            fail("Production release HTML retains local Photography asset references")
        if asset_base not in release_html:
            fail("Production release HTML does not contain the configured asset base")


def validate_no_private_leaks() -> None:
    leak_patterns = [
        re.compile("/" + "Users/", re.I),
        re.compile(r"Desktop[/\\]web photo", re.I),
        re.compile(r"\bDSC\d{5}\.jpg\b", re.I),
        re.compile(r"\bIMG_\d{4}\.jpg\b", re.I),
        re.compile(r"\bdji_export_[\w-]+\.jpg\b", re.I),
    ]
    text_suffixes = {".html", ".css", ".js", ".json", ".xml", ".md", ".py", ".sql", ".txt"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "dist" in path.parts:
            continue
        if path.suffix.lower() not in text_suffixes and path.name not in {"_headers", ".gitignore"}:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in leak_patterns:
            if pattern.search(text):
                fail(f"Private source detail leaked in {path.relative_to(ROOT)}: {pattern.pattern}")


def validate_sitemap() -> None:
    path = ROOT / "sitemap.xml"
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        fail(f"Invalid sitemap XML: {exc}")
        return
    urls = {node.text for node in tree.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")}
    for required in {
        "https://kexingyan.com/",
        "https://kexingyan.com/photography/",
        "https://kexingyan.com/photography/license/",
    }:
        if required not in urls:
            fail(f"Missing sitemap URL: {required}")


def validate_cloudflare_foundation() -> None:
    config_path = ROOT / "cloudflare" / "photography" / "wrangler.jsonc"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    r2 = {item["binding"]: item["bucket_name"] for item in config.get("r2_buckets", [])}
    if r2 != {
        "PHOTO_PUBLIC": "kexingyan-photography-public",
        "PHOTO_MASTERS": "kexingyan-photography-private",
    }:
        fail(f"Unexpected Photography R2 bindings: {r2}")
    d1 = config.get("d1_databases", [])
    if len(d1) != 1 or d1[0].get("binding") != "PHOTOGRAPHY_DB":
        fail("Missing Photography D1 binding")
    elif d1[0].get("database_name") != "kexingyan-photography":
        fail("Unexpected Photography D1 database name")
    elif d1[0].get("database_id") != "<D1_DATABASE_ID>":
        fail("Template must retain an explicit unresolved D1 database ID")
    config_text = config_path.read_text(encoding="utf-8")
    for forbidden in ("account_id", "CF_ACCESS_AUD", "CF_ACCESS_TEAM_DOMAIN", "api_token"):
        if forbidden in config_text:
            fail(f"Owner/account-specific value must not be tracked in Wrangler template: {forbidden}")

    cors = json.loads(
        (ROOT / "cloudflare" / "photography" / "public-bucket-cors.json").read_text(encoding="utf-8")
    )
    expected_cors = {
        "origins": ["https://kexingyan.com", "https://www.kexingyan.com"],
        "methods": ["GET", "HEAD"],
    }
    if cors != {"rules": [{"allowed": expected_cors}]}:
        fail(f"Unexpected public bucket CORS policy: {cors}")

    seed_records = json.loads((ROOT / "data" / "photography" / "photos.seed.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="photography-d1-validation-") as temporary:
        temp = Path(temporary)
        provenance_path = temp / "private-provenance.json"
        private_photos = []
        for photo in seed_records["photos"]:
            private_photos.append({
                "id": photo["id"],
                "assetVersion": photo["assetVersion"],
                "masterObjectKey": f"photography/originals/private/{photo['id']}/v1/master.jpg",
                "sourceFilename": f"private-{photo['id']}.jpg",
                "sourceHash": "a" * 64,
                "originalWidth": 6000,
                "originalHeight": 4000,
                "sourceBytes": 30_000_000,
            })
        provenance_path.write_text(json.dumps({"photos": private_photos}), encoding="utf-8")
        seed_sql_path = temp / "seed.sql"
        result = run_checked([
            sys.executable,
            str(ROOT / "scripts" / "generate_photography_d1_seed.py"),
            "--private-provenance", str(provenance_path),
            "--output", str(seed_sql_path),
        ])
        if result is None:
            return
        connection = sqlite3.connect(":memory:")
        try:
            connection.executescript((ROOT / "migrations" / "photography" / "0001_initial.sql").read_text(encoding="utf-8"))
            connection.executescript((ROOT / "migrations" / "photography" / "0002_seed_ledger.sql").read_text(encoding="utf-8"))
            seed_sql = seed_sql_path.read_text(encoding="utf-8")
            connection.executescript(seed_sql)
            counts = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("photo_series", "photos", "photo_asset_versions", "photography_seed_runs")
            }
            if counts != {"photo_series": 4, "photos": 14, "photo_asset_versions": 14, "photography_seed_runs": 1}:
                fail(f"Unexpected local D1 seed counts: {counts}")
            first = connection.execute(
                "SELECT slug, series_id, sort_order, layout_hint, featured, allow_download, status, asset_version "
                "FROM photos WHERE id = 'P001'"
            ).fetchone()
            source = next(photo for photo in seed_records["photos"] if photo["id"] == "P001")
            expected = (
                source["slug"], source["seriesId"], source["sortOrder"], source["layoutHint"],
                int(source["featured"]), int(source["allowDownload"]), source["status"], source["assetVersion"],
            )
            if first != expected:
                fail("D1 seed does not preserve P001 authoritative fields")
            try:
                connection.executescript(seed_sql)
                fail("D1 seed can be applied twice; expected guarded failure")
            except sqlite3.IntegrityError:
                pass
        finally:
            connection.close()

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    staged_generated = [path for path in staged if path.startswith("assets/photography/generated/")]
    if staged_generated:
        fail(f"Generated Photography JPEGs are staged for Git: {staged_generated}")


def validate_studio_isolation() -> None:
    studio_files = [
        ROOT / "studio" / "index.html",
        ROOT / "studio" / "preview.html",
        ROOT / "studio" / "tests.html",
    ]
    for path in studio_files:
        text = path.read_text(encoding="utf-8")
        if 'name="robots" content="noindex, nofollow, noarchive"' not in text:
            fail(f"Studio route lacks strict noindex metadata: {path.relative_to(ROOT)}")
        if 'type="password"' in text.lower():
            fail(f"Studio contains a fake password field: {path.relative_to(ROOT)}")
    headers = (ROOT / "_headers").read_text(encoding="utf-8")
    if "/studio/*" not in headers or "X-Robots-Tag: noindex, nofollow" not in headers:
        fail("Studio lacks an X-Robots-Tag noindex header rule")

    public_entrypoints = [ROOT / "index.html", ROOT / "photography" / "index.html", ROOT / "sitemap.xml"]
    for path in public_entrypoints:
        if "/studio" in path.read_text(encoding="utf-8"):
            fail(f"Studio is exposed from public navigation/sitemap: {path.relative_to(ROOT)}")

    repository_text = (ROOT / "assets" / "studio" / "photo-admin-repository.js").read_text(encoding="utf-8")
    for method in (
        "listPhotos", "getPhoto", "saveDraft", "publishPhoto", "archivePhoto",
        "reorderPhotos", "listSeries", "updateSeries", "prepareUpload",
        "exportPublicManifest", "exportPreviewManifest",
    ):
        if f"{method}(" not in repository_text:
            fail(f"Local PhotoAdminRepository is missing {method}()")
    if 'fetch("/api/photo-admin/' in repository_text or "fetch('/api/photo-admin/" in repository_text:
        fail("Offline Studio repository attempts to call the future production admin API")


def validate_motion_polish() -> None:
    css = (ROOT / "assets" / "photography" / "photography.css").read_text(encoding="utf-8")
    script = (ROOT / "assets" / "photography" / "photography.js").read_text(encoding="utf-8")
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    photography_html = (ROOT / "photography" / "index.html").read_text(encoding="utf-8")

    for token in (
        "--motion-fast", "--motion-ui", "--motion-photo", "--motion-hero",
        "--ease-standard", "--ease-photo",
    ):
        if token not in css:
            fail(f"Photography motion token is missing: {token}")
    if "@media (prefers-reduced-motion: reduce)" not in css:
        fail("Photography CSS lacks a reduced-motion override")
    if "IntersectionObserver" not in script or "observer.unobserve(entry.target)" not in script:
        fail("Photography reveals are not one-shot IntersectionObserver enhancements")
    if 'addEventListener("scroll"' in script or "addEventListener('scroll'" in script:
        fail("Photography motion uses a continuous scroll listener")
    if "motion-pending" in photography_html:
        fail("Photography HTML hardcodes a hidden motion state")
    if "motion-pending" not in homepage or "IntersectionObserver" not in homepage:
        fail("Homepage Photography feature lacks progressive reveal enhancement")
    for forbidden in ("gsap", "framer-motion", "three.js", "locomotive-scroll"):
        if forbidden in (css + script + homepage).lower():
            fail(f"Photography motion introduced a forbidden animation dependency: {forbidden}")
    for required in (
        'id="photo-index"', 'id="lightbox"', 'id="download-license"',
        'event.key === "ArrowLeft"', 'event.key === "ArrowRight"',
        'addEventListener("cancel"', "lastLightboxTrigger.focus()",
    ):
        if required not in photography_html + script:
            fail(f"Photography interaction regression guard is missing: {required}")


def main() -> int:
    validate_html()
    validate_seed_and_local_manifest()
    validate_production_mode()
    validate_no_private_leaks()
    validate_sitemap()
    validate_cloudflare_foundation()
    validate_studio_isolation()
    validate_motion_polish()
    if ERRORS:
        print(f"FAILED: {len(ERRORS)} issue(s)")
        for error in ERRORS:
            print(f"- {error}")
        return 1
    print("PASS: HTML links, canonical URLs, JSON-LD, and sitemap XML")
    print("PASS: 14 unique records, asset versions, and four approved series")
    print("PASS: local manifest regenerates deterministically and resolves 56 versioned derivatives")
    print("PASS: production manifest emits configured HTTPS R2 URLs")
    print("PASS: production release excludes local JPEGs, authoritative seed data, and offline Studio")
    print("PASS: download targets are 1800px derivatives only")
    print("PASS: creator metadata and GPS stripping")
    print("PASS: no source paths, master keys, filenames, hashes, or private fields in public output")
    print("PASS: Wrangler resource template contains deterministic names and no account secrets")
    print("PASS: D1 schema and guarded initial seed apply locally; second seed is rejected")
    print("PASS: no generated Photography JPEG is staged for Git")
    print("PASS: Studio routes are noindex, publicly unlinked, and use an offline repository adapter")
    print("PASS: motion uses centralized tokens, one-shot observers, progressive enhancement, and reduced-motion overrides")
    return 0


if __name__ == "__main__":
    sys.exit(main())
