#!/usr/bin/env python3
"""Safely inspect and ingest new Photography masters into local draft assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError
from PIL.ExifTags import IFD


MAX_BYTES = 50 * 1024 * 1024
MAX_PIXELS = 80_000_000
MAX_DIMENSION = 12_000
VARIANTS = {
    "thumbnail": {"long_edge": 480, "quality": 85},
    "preview": {"long_edge": 1280, "quality": 89},
    "display": {"long_edge": 2200, "quality": 91},
    "download": {"long_edge": 1800, "quality": 91},
}
MIME_SIGNATURES = {
    "image/jpeg": lambda value: value.startswith(b"\xff\xd8\xff"),
    "image/png": lambda value: value.startswith(b"\x89PNG\r\n\x1a\n"),
}


@dataclass(frozen=True)
class Inspection:
    source: Path
    photo_id: str
    mime_type: str
    size_bytes: int
    sha256: str
    width: int
    height: int
    orientation: str
    exif: dict[str, object]


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def detect_mime(path: Path) -> str:
    header = path.read_bytes()[:16]
    for mime_type, matches in MIME_SIGNATURES.items():
        if matches(header):
            return mime_type
    guessed, _ = mimetypes.guess_type(path.name)
    raise ValueError(f"Unsupported image MIME/signature for {path.name}: {guessed or 'unknown'}")


def rational_text(value: object, suffix: str = "") -> str | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return str(value)
    rendered = f"{number:.2f}".rstrip("0").rstrip(".")
    return f"{rendered}{suffix}"


def extract_exif(image: Image.Image) -> dict[str, object]:
    exif = image.getexif()
    camera = " ".join(value for value in (str(exif.get(271, "")).strip(), str(exif.get(272, "")).strip()) if value) or None
    lens = None
    exposure = {}
    try:
        exposure = exif.get_ifd(IFD.Exif)
    except (KeyError, TypeError, AttributeError):
        exposure = {}
    lens = exposure.get(42036) or exif.get(42036)
    shutter = exposure.get(33434) or exif.get(33434)
    if shutter:
        try:
            seconds = float(shutter)
            shutter_text = f"1/{round(1 / seconds)} s" if 0 < seconds < 1 else f"{seconds:g} s"
        except (TypeError, ValueError, ZeroDivisionError):
            shutter_text = str(shutter)
    else:
        shutter_text = None
    date_value = exposure.get(36867) or exif.get(36867) or exif.get(306)
    date_taken = None
    if date_value:
        try:
            date_taken = datetime.strptime(str(date_value), "%Y:%m:%d %H:%M:%S").date().isoformat()
        except ValueError:
            date_taken = None
    return {
        "dateTaken": date_taken,
        "camera": camera,
        "lens": str(lens) if lens else None,
        "focalLength": rational_text(exposure.get(37386) or exif.get(37386), " mm"),
        "aperture": f"f/{rational_text(exposure.get(33437) or exif.get(33437))}" if (exposure.get(33437) or exif.get(33437)) else None,
        "shutterSpeed": shutter_text,
        "iso": exposure.get(34855) or exif.get(34855),
        "gpsPresentInMaster": bool(exif.get(34853)),
    }


def discover_sources(inputs: list[Path]) -> list[Path]:
    discovered: list[Path] = []
    for input_path in inputs:
        path = input_path.expanduser().resolve()
        if path.is_file():
            discovered.append(path)
        elif path.is_dir():
            discovered.extend(sorted(item for item in path.iterdir() if item.is_file() and not item.name.startswith(".")))
        else:
            raise FileNotFoundError(f"Input does not exist: {path}")
    unique = []
    seen = set()
    for path in discovered:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    if not unique:
        raise ValueError("No input files found")
    return unique


def existing_ids(records_path: Path, output_root: Path) -> set[str]:
    records = json.loads(records_path.read_text(encoding="utf-8"))
    ids = {photo["id"] for photo in records["photos"]}
    if output_root.exists():
        for child in output_root.iterdir():
            match = re.match(r"^(P\d{3,})-v\d+$", child.name)
            if match:
                ids.add(match.group(1))
    return ids


def allocate_ids(count: int, used: set[str], requested: str | None) -> list[str]:
    if requested:
        if count != 1:
            raise ValueError("--id can be used only with one input image")
        if not re.fullmatch(r"P\d{3,}", requested):
            raise ValueError("--id must match P followed by at least three digits")
        if requested in used:
            raise ValueError(f"Duplicate photo ID: {requested}")
        return [requested]
    highest = max((int(value[1:]) for value in used if re.fullmatch(r"P\d{3,}", value)), default=0)
    return [f"P{number:03d}" for number in range(highest + 1, highest + count + 1)]


def inspect_source(path: Path, photo_id: str) -> Inspection:
    size = path.stat().st_size
    if size > MAX_BYTES:
        raise ValueError(f"Encoded file exceeds 50 MiB: {path.name} ({size} bytes)")
    mime_type = detect_mime(path)
    try:
        with Image.open(path) as candidate:
            candidate.verify()
        with Image.open(path) as image:
            width, height = ImageOps.exif_transpose(image).size
            exif = extract_exif(image)
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValueError(f"Image decode failed for {path.name}: {exc}") from exc
    if width * height > MAX_PIXELS:
        raise ValueError(f"Decoded image exceeds 80 megapixels: {path.name} ({width}×{height})")
    if max(width, height) > MAX_DIMENSION:
        raise ValueError(f"Decoded image exceeds 12,000px dimension: {path.name} ({width}×{height})")
    return Inspection(
        source=path,
        photo_id=photo_id,
        mime_type=mime_type,
        size_bytes=size,
        sha256=sha256(path),
        width=width,
        height=height,
        orientation="portrait" if height > width else "landscape",
        exif=exif,
    )


def public_exif() -> Image.Exif:
    exif = Image.Exif()
    exif[270] = "Personal / Non-commercial use only · kexingyan.com"
    exif[315] = "Kexing Yan"
    exif[33432] = "© Kexing Yan"
    return exif


def normalized_srgb(opened: Image.Image) -> tuple[Image.Image, bytes]:
    srgb_profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
    srgb_bytes = srgb_profile.tobytes()
    rendered = ImageOps.exif_transpose(opened)
    source_profile = opened.info.get("icc_profile")
    if source_profile:
        try:
            rendered = ImageCms.profileToProfile(
                rendered,
                ImageCms.ImageCmsProfile(BytesIO(source_profile)),
                srgb_profile,
                outputMode="RGB",
            )
            return rendered, srgb_bytes
        except (ImageCms.PyCMSError, OSError):
            pass
    return rendered.convert("RGB"), srgb_bytes


def write_ingest(inspection: Inspection, output_root: Path, asset_version: int) -> Path:
    final = output_root / f"{inspection.photo_id}-v{asset_version}"
    if final.exists():
        raise FileExistsError(f"Refusing to overwrite existing ingest: {final}")
    output_root.mkdir(parents=True, exist_ok=True)
    original_hash = inspection.sha256
    with tempfile.TemporaryDirectory(prefix=f".{inspection.photo_id}-", dir=output_root) as temporary:
        staging = Path(temporary)
        images = {}
        with Image.open(inspection.source) as opened:
            rendered, srgb_profile = normalized_srgb(opened)
            for variant, settings in VARIANTS.items():
                image = rendered.copy()
                image.thumbnail((settings["long_edge"], settings["long_edge"]), Image.Resampling.LANCZOS)
                filename = f"{inspection.photo_id}-v{asset_version}-{variant}.jpg"
                destination = staging / "derivatives" / variant / filename
                destination.parent.mkdir(parents=True, exist_ok=True)
                image.save(
                    destination,
                    "JPEG",
                    quality=settings["quality"],
                    optimize=True,
                    progressive=True,
                    subsampling="4:4:4",
                    icc_profile=srgb_profile,
                    exif=public_exif(),
                )
                images[variant] = {
                    "relativePath": str(destination.relative_to(staging)),
                    "width": image.width,
                    "height": image.height,
                    "bytes": destination.stat().st_size,
                    "sha256": sha256(destination),
                }
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        title = re.sub(r"[-_]+", " ", inspection.source.stem).strip() or "Untitled photograph"
        record = {
            "id": inspection.photo_id,
            "slug": re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "untitled-photograph",
            "title": title,
            "seriesId": "",
            "dateTaken": inspection.exif["dateTaken"],
            "datePublished": None,
            "locationDisplay": "",
            "caption": "",
            "alt": "",
            "camera": inspection.exif["camera"],
            "lens": inspection.exif["lens"],
            "focalLength": inspection.exif["focalLength"],
            "aperture": inspection.exif["aperture"],
            "shutterSpeed": inspection.exif["shutterSpeed"],
            "iso": inspection.exif["iso"],
            "orientation": inspection.orientation,
            "layoutHint": "standard",
            "featured": False,
            "allowDownload": True,
            "sortOrder": 999,
            "status": "draft",
            "assetVersion": asset_version,
            "createdAt": created_at,
            "updatedAt": created_at,
            "masterObjectKey": f"photography/originals/private/{inspection.photo_id}/v{asset_version}/master{inspection.source.suffix.lower()}",
            "sourceFilename": inspection.source.name,
            "sourcePath": str(inspection.source),
            "sourceHash": inspection.sha256,
            "sourceBytes": inspection.size_bytes,
            "originalWidth": inspection.width,
            "originalHeight": inspection.height,
            "processingState": "derivatives-generated-local",
            "gpsPresentInMaster": inspection.exif["gpsPresentInMaster"],
            "images": images,
        }
        (staging / "draft.private.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if sha256(inspection.source) != original_hash:
            raise RuntimeError(f"Source changed during ingest: {inspection.source}")
        shutil.move(str(staging), final)
    return final


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--records", type=Path, default=repo / "data" / "photography" / "photos.seed.json")
    parser.add_argument("--output", type=Path, default=repo / ".local" / "photography-ingest")
    parser.add_argument("--id")
    parser.add_argument("--asset-version", type=int, default=1)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--confirm-write", action="store_true")
    args = parser.parse_args()
    if args.asset_version < 1:
        parser.error("--asset-version must be at least 1")

    output_root = args.output.expanduser().resolve()
    sources = discover_sources(args.inputs)
    used_ids = existing_ids(args.records.resolve(), output_root)
    photo_ids = allocate_ids(len(sources), used_ids, args.id)
    inspections = [inspect_source(source, photo_id) for source, photo_id in zip(sources, photo_ids)]
    for inspection in inspections:
        target = output_root / f"{inspection.photo_id}-v{args.asset_version}"
        if target.exists():
            raise FileExistsError(f"Duplicate ingest target: {target}")
        print(
            f"{inspection.photo_id}: {inspection.source.name} · {inspection.mime_type} · "
            f"{inspection.width}×{inspection.height} · {inspection.size_bytes} bytes · "
            f"sha256 {inspection.sha256}"
        )
        print(
            f"  EXIF: camera={inspection.exif['camera'] or '—'}; lens={inspection.exif['lens'] or '—'}; "
            f"date={inspection.exif['dateTaken'] or '—'}; GPS in master={'yes' if inspection.exif['gpsPresentInMaster'] else 'no'}"
        )
        print(f"  Target: {target} (draft only; four web derivatives; source unchanged)")
    if args.dry_run:
        print(f"DRY RUN: {len(inspections)} master(s) validated; no files or directories written")
        return
    written = [write_ingest(inspection, output_root, args.asset_version) for inspection in inspections]
    print(f"INGESTED: {len(written)} draft(s) into ignored local storage")
    print("PUBLISH STATUS: draft; no public manifest, seed, Git file, or cloud resource changed")


if __name__ == "__main__":
    main()
