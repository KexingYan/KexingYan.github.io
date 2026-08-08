#!/usr/bin/env python3
"""Generate versioned derivatives and public-safe Photography manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageOps


VARIANTS = {
    "thumbnail": {"long_edge": 480, "quality": 85},
    "preview": {"long_edge": 1280, "quality": 89},
    "display": {"long_edge": 2200, "quality": 91},
    "download": {"long_edge": 1800, "quality": 91},
}

PUBLIC_PHOTO_FIELDS = (
    "id",
    "slug",
    "title",
    "seriesId",
    "dateTaken",
    "datePublished",
    "locationDisplay",
    "caption",
    "alt",
    "camera",
    "lens",
    "focalLength",
    "aperture",
    "shutterSpeed",
    "iso",
    "orientation",
    "layoutHint",
    "featured",
    "allowDownload",
    "sortOrder",
    "assetVersion",
    "updatedAt",
)


def make_public_exif() -> Image.Exif:
    exif = Image.Exif()
    exif[270] = "Personal / Non-commercial use only · kexingyan.com"
    exif[315] = "Kexing Yan"
    exif[33432] = "© Kexing Yan"
    return exif


def derivative_filename(photo: dict[str, object], variant: str) -> str:
    return f"{photo['id']}-v{photo['assetVersion']}-{variant}.jpg"


def public_asset_url(asset_base: str, photo: dict[str, object], variant: str) -> str:
    return f"{asset_base.rstrip('/')}/{variant}/{derivative_filename(photo, variant)}"


def generate_variant(
    image: Image.Image,
    output_path: Path,
    long_edge: int,
    quality: int,
    icc_profile: bytes | None,
    quality_boost: int,
) -> None:
    rendered = image.copy()
    rendered.thumbnail((long_edge, long_edge), Image.Resampling.LANCZOS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rendered.save(
        output_path,
        "JPEG",
        quality=min(95, quality + quality_boost),
        optimize=True,
        progressive=True,
        subsampling="4:4:4",
        icc_profile=icc_profile,
        exif=make_public_exif(),
    )


def inspect_derivative(path: Path, src: str) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing generated derivative: {path}")
    with Image.open(path) as image:
        width, height = image.size
    return {
        "src": src,
        "width": width,
        "height": height,
        "bytes": path.stat().st_size,
    }


def resolve_asset_base(
    mode: str,
    explicit_base: str | None,
    config: dict[str, object],
) -> str:
    if mode == "local":
        base = explicit_base or str(config["local"]["assetBase"])
        if not base.startswith("/"):
            raise ValueError("Local asset base must be a root-relative URL")
        return base.rstrip("/")

    env_name = str(config["production"]["assetBaseEnvironmentVariable"])
    base = explicit_base or os.environ.get(env_name)
    if not base:
        raise ValueError(f"Production mode requires --asset-base or {env_name}")
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Production asset base must be an absolute HTTPS URL")
    return base.rstrip("/")


def build_public_manifest(
    records: dict[str, object],
    generated: Path,
    asset_mode: str,
    asset_base: str,
) -> dict[str, object]:
    public_photos = []
    for photo in records["photos"]:
        if photo["status"] != "published":
            continue
        public_record = {field: photo.get(field) for field in PUBLIC_PHOTO_FIELDS}
        images = {}
        for variant in VARIANTS:
            filename = derivative_filename(photo, variant)
            local_path = generated / variant / filename
            images[variant] = inspect_derivative(
                local_path,
                public_asset_url(asset_base, photo, variant),
            )
        public_record["images"] = images
        public_photos.append(public_record)

    return {
        "schemaVersion": records["schemaVersion"],
        "publishRevision": records["publishRevision"],
        "assetMode": asset_mode,
        "assetBase": asset_base,
        "series": records["series"],
        "photos": public_photos,
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    repo_default = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=repo_default)
    parser.add_argument("--records", type=Path)
    parser.add_argument("--asset-config", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--source-map", type=Path)
    parser.add_argument("--private-manifest", type=Path)
    parser.add_argument("--manifest-output", type=Path)
    parser.add_argument("--asset-mode", choices=("local", "production"), default="local")
    parser.add_argument("--asset-base")
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args()

    repo = args.repo.resolve()
    records_path = (args.records or repo / "data" / "photography" / "photos.seed.json").resolve()
    config_path = (args.asset_config or repo / "config" / "photography-assets.json").resolve()
    manifest_output = (
        args.manifest_output or repo / "assets" / "photography" / "data" / "photos.json"
    ).resolve()
    generated = repo / "assets" / "photography" / "generated"
    records = json.loads(records_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    asset_base = resolve_asset_base(args.asset_mode, args.asset_base, config)

    private_photos = []
    if not args.manifest_only:
        missing_args = [
            name
            for name, value in (
                ("--source", args.source),
                ("--source-map", args.source_map),
                ("--private-manifest", args.private_manifest),
            )
            if value is None
        ]
        if missing_args:
            parser.error(f"Derivative generation requires: {', '.join(missing_args)}")

        source_dir = args.source.resolve()
        source_map = json.loads(args.source_map.read_text(encoding="utf-8"))
        source_by_id = source_map["sources"]
        record_ids = {photo["id"] for photo in records["photos"]}
        if set(source_by_id) != record_ids:
            raise ValueError("Private source-map IDs must exactly match seed record IDs")

        for photo in records["photos"]:
            source = source_dir / source_by_id[photo["id"]]
            if not source.is_file():
                raise FileNotFoundError(f"Missing source master for {photo['id']}")

            with Image.open(source) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
                icc_profile = opened.info.get("icc_profile")
                boost = 2 if photo["id"] in {"P011", "P013", "P014"} else 0
                for variant, settings in VARIANTS.items():
                    destination = generated / variant / derivative_filename(photo, variant)
                    generate_variant(
                        image,
                        destination,
                        settings["long_edge"],
                        settings["quality"],
                        icc_profile,
                        boost,
                    )
                original_width, original_height = image.size

            private_photos.append({
                "id": photo["id"],
                "assetVersion": photo["assetVersion"],
                "masterObjectKey": (
                    f"photography/originals/private/{photo['id']}/"
                    f"v{photo['assetVersion']}/master.jpg"
                ),
                "sourceFilename": source.name,
                "sourcePath": str(source),
                "sourceBytes": source.stat().st_size,
                "sourceHash": hashlib.sha256(source.read_bytes()).hexdigest(),
                "originalWidth": original_width,
                "originalHeight": original_height,
                "processingState": "derivatives-generated-local",
            })

        write_json(
            args.private_manifest.resolve(),
            {"sourceRoot": str(source_dir), "photos": private_photos},
        )

    manifest = build_public_manifest(records, generated, args.asset_mode, asset_base)
    write_json(manifest_output, manifest)
    action = "Validated" if args.manifest_only else "Generated"
    print(f"{action} {len(manifest['photos'])} published photos × {len(VARIANTS)} variants")
    print(f"Asset mode: {args.asset_mode} ({asset_base})")
    print(f"Public manifest: {manifest_output}")
    if args.private_manifest and not args.manifest_only:
        print(f"Private provenance: {args.private_manifest.resolve()}")


if __name__ == "__main__":
    main()
