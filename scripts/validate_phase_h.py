#!/usr/bin/env python3
"""Static safety and architecture checks for Photography Studio Phase H."""

from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    studio = text("studio/index.html")
    sitemap = text("sitemap.xml")
    router = text("functions/api/photo-admin/[[path]].js")
    auth = text("functions/_lib/access-auth.js")
    publish = text("functions/_lib/photo-publish.js")
    adapter = text("assets/studio/photo-admin-repository.js")
    config = text("cloudflare/photography/wrangler.pages.example.jsonc")
    migration = text("migrations/photography/0003_admin_drafts.sql")

    require('name="robots" content="noindex, nofollow, noarchive"' in studio, "Studio must be noindex")
    require("/studio" not in sitemap and "photo-admin" not in sitemap, "Studio/API must not enter sitemap")
    require("requireOwner" in router and "requireMutationOrigin" in router, "Every API request must pass auth and origin checks")
    for claim in ("RS256", "claims.iss", "claims.aud", "claims.exp", "claims.sub", "claims.email"):
        require(claim in auth, f"Access validation missing {claim}")
    require("PHOTO_ADMIN_OWNER_EMAILS" in auth, "Server-side owner allowlist missing")
    require("@gmail.com" not in auth.lower() and "@gmail.com" not in config.lower(), "Owner email leaked into source")
    require("photography/manifests/current.json" in publish, "Publish pointer missing")
    require(publish.index("versionedKey") < publish.index('PHOTO_PUBLIC.put("photography/manifests/current.json"'), "Versioned manifest must precede current.json")
    require("photo_drafts" in migration and "photo_asset_derivatives" in migration, "Draft/derivative tables missing")
    require("CloudflarePhotoAdminRepository" in adapter and "LocalPhotoAdminRepository" in adapter, "Adapter separation missing")
    require("<D1_DATABASE_ID>" in config and "<ACCESS_TEAM>" in config, "Example config must remain non-deployable")
    require("CF_ACCESS_AUD" not in config and "PHOTO_ADMIN_OWNER_EMAILS" not in config, "Owner/AUD must not be committed")
    require("delete(" not in router.lower(), "Permanent delete route is forbidden")
    database = sqlite3.connect(":memory:")
    for migration_path in sorted((ROOT / "migrations" / "photography").glob("*.sql")):
        database.executescript(migration_path.read_text(encoding="utf-8"))
    tables = {row[0] for row in database.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    require({"photos", "photo_drafts", "photo_asset_derivatives", "photography_admin_state"} <= tables, "Admin migration tables missing")
    require(database.execute("SELECT collection_revision FROM photography_admin_state WHERE singleton = 1").fetchone() == (1,), "Admin revision seed invalid")
    print("PHASE_H_STATIC_VALIDATION: PASS")


if __name__ == "__main__":
    main()
