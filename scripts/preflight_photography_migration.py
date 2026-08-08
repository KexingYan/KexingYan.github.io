#!/usr/bin/env python3
"""Validate the complete Photography migration plan without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from PIL import Image


VARIANTS = {"thumbnail": 480, "preview": 1280, "display": 2200, "download": 1800}
PRIVATE_FIELDS = {
    "masterObjectKey", "sourceFilename", "sourceHash", "sourcePath", "sourceBytes",
    "originalWidth", "originalHeight", "processingState",
}


def digest(path: Path, algorithm: str) -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def walk_keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            found.add(key)
            found.update(walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(walk_keys(child))
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--records", type=Path)
    parser.add_argument("--local-manifest", type=Path)
    parser.add_argument("--production-manifest", type=Path, required=True)
    parser.add_argument("--private-provenance", type=Path, required=True)
    parser.add_argument("--r2-plan", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    output = args.report_output.resolve()
    if output == repo or repo in output.parents:
        raise ValueError("Migration reports must remain outside the repository")
    records_path = (args.records or repo / "data" / "photography" / "photos.seed.json").resolve()
    local_path = (args.local_manifest or repo / "assets" / "photography" / "data" / "photos.json").resolve()
    records = json.loads(records_path.read_text(encoding="utf-8"))
    local = json.loads(local_path.read_text(encoding="utf-8"))
    production = json.loads(args.production_manifest.read_text(encoding="utf-8"))
    provenance = json.loads(args.private_provenance.read_text(encoding="utf-8"))
    plan = json.loads(args.r2_plan.read_text(encoding="utf-8"))

    errors: list[str] = []
    expected_ids = [f"P{number:03d}" for number in range(1, 15)]
    for label, photos in (
        ("records", records["photos"]),
        ("local manifest", local["photos"]),
        ("production manifest", production["photos"]),
        ("private provenance", provenance["photos"]),
    ):
        ids = sorted(photo["id"] for photo in photos)
        if ids != expected_ids:
            errors.append(f"{label} IDs are not exactly P001-P014")

    for label, manifest in (("local", local), ("production", production)):
        leaked = walk_keys(manifest) & PRIVATE_FIELDS
        text = json.dumps(manifest)
        if leaked or "originals/private" in text:
            errors.append(f"{label} public manifest contains private fields or master prefixes")
    if local.get("assetMode") != "local" or production.get("assetMode") != "production":
        errors.append("Manifest asset modes are incorrect")

    local_by_id = {photo["id"]: photo for photo in local["photos"]}
    private_by_id = {photo["id"]: photo for photo in provenance["photos"]}
    master_bytes = 0
    derivative_bytes = 0
    for photo_id in expected_ids:
        private = private_by_id[photo_id]
        master = Path(private["sourcePath"])
        if not master.is_file():
            errors.append(f"Missing master for {photo_id}")
            continue
        master_bytes += master.stat().st_size
        if master.stat().st_size != private["sourceBytes"]:
            errors.append(f"Master byte size changed for {photo_id}")
        if digest(master, "sha256") != private["sourceHash"]:
            errors.append(f"Master hash changed for {photo_id}")
        photo = local_by_id[photo_id]
        for variant, expected_edge in VARIANTS.items():
            src = photo["images"][variant]["src"]
            derivative = repo / src.lstrip("/")
            if not derivative.is_file():
                errors.append(f"Missing {variant} derivative for {photo_id}")
                continue
            derivative_bytes += derivative.stat().st_size
            with Image.open(derivative) as image:
                if max(image.size) != expected_edge:
                    errors.append(f"Wrong {variant} dimensions for {photo_id}: {image.size}")
                if 34853 in image.getexif():
                    errors.append(f"GPS EXIF found in {photo_id} {variant}")

    objects = plan.get("objects", [])
    destinations = [(item.get("bucketRole"), item.get("objectKey")) for item in objects]
    if len(destinations) != len(set(destinations)):
        errors.append("R2 plan contains duplicate object destinations")
    if len(objects) != 72:
        errors.append(f"Expected 72 planned objects, found {len(objects)}")
    if not objects or objects[-1].get("objectKey") != "photography/manifests/current.json" or not objects[-1].get("publishLast"):
        errors.append("current.json is not scheduled last")

    derivative_pattern = re.compile(
        r"^photography/derivatives/(thumbnail|preview|display|download)/"
        r"(P\d{3,})-v([1-9]\d*)-(thumbnail|preview|display|download)\.jpg$"
    )
    role_counts = Counter()
    role_bytes = Counter()
    for item in objects:
        role = item["bucketRole"]
        role_counts[role] += 1
        role_bytes[role] += item["bytes"]
        local_file = Path(item["localPath"])
        if not local_file.is_file():
            errors.append(f"Planned local object is missing: {item['objectKey']}")
            continue
        if local_file.stat().st_size != item["bytes"]:
            errors.append(f"Planned byte size changed: {item['objectKey']}")
        if digest(local_file, "sha256") != item.get("sha256"):
            errors.append(f"Planned SHA-256 changed: {item['objectKey']}")
        if digest(local_file, "md5") != item.get("md5"):
            errors.append(f"Planned MD5 changed: {item['objectKey']}")
        if role == "public-photography" and "/derivatives/" in item["objectKey"]:
            match = derivative_pattern.fullmatch(item["objectKey"])
            if not match or match.group(1) != match.group(4):
                errors.append(f"Unversioned or malformed public derivative key: {item['objectKey']}")
            if item.get("cacheControl") != "public, max-age=31536000, immutable":
                errors.append(f"Wrong immutable cache policy: {item['objectKey']}")
        if role == "private-masters":
            if not re.fullmatch(r"photography/originals/private/P\d{3,}/v[1-9]\d*/master\.jpg", item["objectKey"]):
                errors.append(f"Malformed private master key: {item['objectKey']}")
            if item.get("cacheControl") != "private, no-store":
                errors.append(f"Wrong private cache policy: {item['objectKey']}")
    if role_counts != {"private-masters": 14, "public-photography": 58}:
        errors.append(f"Unexpected R2 role counts: {dict(role_counts)}")

    report = {
        "schemaVersion": 1,
        "status": "failed" if errors else "ready-for-reviewed-external-execution",
        "networkCallsMade": False,
        "resourceNames": {
            "publicBucket": "kexingyan-photography-public",
            "privateBucket": "kexingyan-photography-private",
            "d1Database": "kexingyan-photography",
            "publicHostname": "images.kexingyan.com",
        },
        "verified": {
            "photoIds": expected_ids,
            "masterCount": 14,
            "masterHashesUnchanged": not any("Master hash" in error for error in errors),
            "derivativeCount": 56,
            "gpsMetadataAbsent": not any("GPS EXIF" in error for error in errors),
            "publicManifestPrivateFieldsAbsent": not any("public manifest" in error for error in errors),
            "destinationsUnique": len(destinations) == len(set(destinations)),
            "currentManifestScheduledLast": bool(objects and objects[-1].get("publishLast")),
        },
        "bytes": {
            "sourceMasters": master_bytes,
            "localDerivatives": derivative_bytes,
            "plannedPrivateBucket": role_bytes["private-masters"],
            "plannedPublicBucket": role_bytes["public-photography"],
            "plannedTotalWrites": sum(role_bytes.values()),
        },
        "objectCounts": dict(role_counts),
        "errors": errors,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Migration preflight report: {output}")
    print(f"Status: {report['status']}")
    print(f"Objects: {len(objects)}; planned bytes: {report['bytes']['plannedTotalWrites']}")
    if errors:
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
