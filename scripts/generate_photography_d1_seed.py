#!/usr/bin/env python3
"""Generate a private, one-time guarded D1 seed outside the repository."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def sql_value(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def insert(table: str, columns: tuple[str, ...], values: list[object]) -> str:
    return (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES "
        f"({', '.join(sql_value(value) for value in values)});"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--records", type=Path)
    parser.add_argument("--private-provenance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    output = args.output.resolve()
    if output == repo or repo in output.parents:
        raise ValueError("D1 seed contains private metadata and must stay outside the repository")
    records_path = (args.records or repo / "data" / "photography" / "photos.seed.json").resolve()
    records = json.loads(records_path.read_text(encoding="utf-8"))
    provenance = json.loads(args.private_provenance.read_text(encoding="utf-8"))
    private_by_id = {photo["id"]: photo for photo in provenance["photos"]}
    record_ids = {photo["id"] for photo in records["photos"]}
    if set(private_by_id) != record_ids:
        raise ValueError("Private provenance IDs must exactly match authoritative record IDs")

    seed_id = f"initial-{records['publishRevision']}"
    applied_at = max(photo["updatedAt"] for photo in records["photos"])
    lines = [
        "PRAGMA foreign_keys = ON;",
        "BEGIN IMMEDIATE;",
        "DROP TABLE IF EXISTS temp.photography_seed_guard;",
        "CREATE TEMP TABLE photography_seed_guard (ok INTEGER NOT NULL CHECK (ok = 1));",
        "INSERT INTO photography_seed_guard (ok)",
        "SELECT CASE WHEN",
        f"  NOT EXISTS (SELECT 1 FROM photography_seed_runs WHERE seed_id = {sql_value(seed_id)})",
        "  AND NOT EXISTS (SELECT 1 FROM photo_series)",
        "  AND NOT EXISTS (SELECT 1 FROM photos)",
        "  AND NOT EXISTS (SELECT 1 FROM photo_asset_versions)",
        "THEN 1 ELSE 0 END;",
        "",
    ]

    for sort_order, series in enumerate(records["series"], start=1):
        lines.append(insert(
            "photo_series",
            ("id", "number_label", "title", "description", "sort_order", "created_at", "updated_at"),
            [series["id"], series["number"], series["title"], series["description"], sort_order, applied_at, applied_at],
        ))

    photo_columns = (
        "id", "slug", "title", "series_id", "date_taken", "date_published",
        "location_display", "caption", "alt", "camera", "lens", "focal_length",
        "aperture", "shutter_speed", "iso", "orientation", "layout_hint",
        "featured", "allow_download", "sort_order", "status", "asset_version",
        "created_at", "updated_at",
    )
    asset_columns = (
        "photo_id", "asset_version", "master_object_key", "source_filename",
        "source_hash", "original_width", "original_height", "source_bytes",
        "processing_state", "processing_error", "created_at",
    )
    for photo in records["photos"]:
        lines.append(insert("photos", photo_columns, [
            photo["id"], photo["slug"], photo["title"], photo["seriesId"],
            photo.get("dateTaken"), photo.get("datePublished"), photo["locationDisplay"],
            photo["caption"], photo["alt"], photo.get("camera"), photo.get("lens"),
            photo.get("focalLength"), photo.get("aperture"), photo.get("shutterSpeed"),
            photo.get("iso"), photo["orientation"], photo["layoutHint"],
            photo["featured"], photo["allowDownload"], photo["sortOrder"],
            photo["status"], photo["assetVersion"], photo["createdAt"], photo["updatedAt"],
        ]))
        private = private_by_id[photo["id"]]
        if private["assetVersion"] != photo["assetVersion"]:
            raise ValueError(f"Asset version mismatch for {photo['id']}")
        lines.append(insert("photo_asset_versions", asset_columns, [
            photo["id"], photo["assetVersion"], private["masterObjectKey"],
            private["sourceFilename"], private["sourceHash"], private["originalWidth"],
            private["originalHeight"], private["sourceBytes"], "ready", None,
            photo["createdAt"],
        ]))

    lines.extend([
        "",
        insert("photography_seed_runs", ("seed_id", "photo_count", "applied_at"), [seed_id, len(records["photos"]), applied_at]),
        "DROP TABLE photography_seed_guard;",
        "COMMIT;",
        "",
    ])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Private D1 seed generated: {output}")
    print(f"Seed: {seed_id} ({len(records['photos'])} photos, guarded empty-database insert)")


if __name__ == "__main__":
    main()
