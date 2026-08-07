#!/usr/bin/env python3
"""Create a private, dry-run R2 upload plan without contacting Cloudflare."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse


VARIANTS = ("thumbnail", "preview", "display", "download")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digests(path: Path) -> dict[str, str]:
    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha256.update(chunk)
            md5.update(chunk)
    return {"sha256": sha256.hexdigest(), "md5": md5.hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--records", type=Path)
    parser.add_argument("--public-manifest", type=Path, required=True)
    parser.add_argument("--private-provenance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    records_path = (args.records or repo / "data" / "photography" / "photos.seed.json").resolve()
    output = args.output.resolve()
    if output == repo or repo in output.parents:
        raise ValueError("Upload plans contain private local paths and must stay outside the repository")

    records = json.loads(records_path.read_text(encoding="utf-8"))
    public_manifest = json.loads(args.public_manifest.read_text(encoding="utf-8"))
    provenance = json.loads(args.private_provenance.read_text(encoding="utf-8"))
    if public_manifest.get("assetMode") != "production":
        raise ValueError("R2 plan requires a production-mode public manifest")

    manifest_by_id = {photo["id"]: photo for photo in public_manifest["photos"]}
    provenance_by_id = {photo["id"]: photo for photo in provenance["photos"]}
    objects = []

    for photo in records["photos"]:
        photo_id = photo["id"]
        private = provenance_by_id[photo_id]
        master_path = Path(private["sourcePath"])
        master_digests = digests(master_path)
        if master_digests["sha256"] != private["sourceHash"]:
            raise ValueError(f"Master hash changed for {photo_id}")
        objects.append({
            "bucketRole": "private-masters",
            "localPath": private["sourcePath"],
            "objectKey": private["masterObjectKey"],
            "contentType": "image/jpeg",
            "cacheControl": "private, no-store",
            "bytes": private["sourceBytes"],
            "sha256": private["sourceHash"],
            "md5": master_digests["md5"],
        })

        public = manifest_by_id[photo_id]
        for variant in VARIANTS:
            image = public["images"][variant]
            filename = Path(urlparse(image["src"]).path).name
            local_path = repo / "assets" / "photography" / "generated" / variant / filename
            file_digests = digests(local_path)
            object_key = f"photography/derivatives/{variant}/{filename}"
            item = {
                "bucketRole": "public-photography",
                "localPath": str(local_path),
                "objectKey": object_key,
                "contentType": "image/jpeg",
                "cacheControl": "public, max-age=31536000, immutable",
                "bytes": image["bytes"],
                "sha256": file_digests["sha256"],
                "md5": file_digests["md5"],
            }
            if variant == "download":
                item["contentDisposition"] = (
                    f"attachment; filename=\"{photo['slug']}-kexing-yan-personal-use.jpg\""
                )
            objects.append(item)

    revision = records["publishRevision"]
    manifest_path = str(args.public_manifest.resolve())
    manifest_bytes = args.public_manifest.stat().st_size
    manifest_digests = digests(args.public_manifest.resolve())
    objects.extend([
        {
            "bucketRole": "public-photography",
            "localPath": manifest_path,
            "objectKey": f"photography/manifests/{revision}.json",
            "contentType": "application/json; charset=utf-8",
            "cacheControl": "public, max-age=31536000, immutable",
            "bytes": manifest_bytes,
            **manifest_digests,
        },
        {
            "bucketRole": "public-photography",
            "localPath": manifest_path,
            "objectKey": "photography/manifests/current.json",
            "contentType": "application/json; charset=utf-8",
            "cacheControl": "public, max-age=60, must-revalidate",
            "bytes": manifest_bytes,
            **manifest_digests,
            "publishLast": True,
        },
    ])

    plan = {
        "schemaVersion": 1,
        "dryRunOnly": True,
        "publishRevision": revision,
        "bucketRoles": {
            "public-photography": "<PUBLIC_R2_BUCKET_NAME>",
            "private-masters": "<PRIVATE_R2_BUCKET_NAME>",
        },
        "objects": objects,
        "verification": {
            "expectedPrivateMasters": len(records["photos"]),
            "expectedPublicDerivatives": len(records["photos"]) * len(VARIANTS),
            "expectedManifestObjects": 2,
            "deleteLocalFiles": False,
        },
    }
    write_json(output, plan)
    print(f"Dry-run upload plan: {output}")
    print(f"Objects: {len(objects)} (no network calls made)")


if __name__ == "__main__":
    main()
