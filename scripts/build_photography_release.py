#!/usr/bin/env python3
"""Stage a production static site whose Photography assets are served by R2."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from urllib.parse import urlparse


ROOT_FILES = (
    "index.html",
    "_headers",
    "robots.txt",
    "sitemap.xml",
    "site.webmanifest",
    "baidu_verify_codeva-vWXLKxDtXl.html",
)
PUBLIC_DIRS = (
    "papers",
    "photography",
    "assets/icons",
    "assets/images",
    "assets/resume",
)
STUDIO_DIRS = (
    "studio",
    "assets/studio",
)
PHOTO_FILES = (
    "assets/photography/photography.css",
    "assets/photography/photography.js",
)
LOCAL_ASSET_BASE = "/assets/photography/generated"


def require_https(value: str, label: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{label} must be an absolute HTTPS URL")
    return value.rstrip("/")


def copy_file(repo: Path, output: Path, relative: str) -> None:
    source = repo / relative
    destination = output / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--asset-base", required=True)
    parser.add_argument("--manifest-url", required=True)
    parser.add_argument("--include-studio", action="store_true")
    parser.add_argument(
        "--studio-access-protected",
        action="store_true",
        help="Required acknowledgement that /studio/* and /api/photo-admin/* are protected by verified Cloudflare Access",
    )
    args = parser.parse_args()

    repo = args.repo.resolve()
    output = args.output.resolve()
    asset_base = require_https(args.asset_base, "--asset-base")
    manifest_url = require_https(args.manifest_url, "--manifest-url")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Release output must be absent or empty; refusing to overwrite it")
    output.mkdir(parents=True, exist_ok=True)

    for relative in ROOT_FILES:
        copy_file(repo, output, relative)
    for relative in PUBLIC_DIRS:
        shutil.copytree(repo / relative, output / relative, dirs_exist_ok=True)
    for relative in PHOTO_FILES:
        copy_file(repo, output, relative)
    if args.include_studio:
        if not args.studio_access_protected:
            raise ValueError("--include-studio requires --studio-access-protected")
        for relative in STUDIO_DIRS:
            shutil.copytree(repo / relative, output / relative, dirs_exist_ok=True)

    config_path = output / "assets" / "photography" / "config.js"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "window.PHOTOGRAPHY_CONFIG = Object.freeze(" +
        json.dumps({"mode": "production", "manifestUrl": manifest_url}, indent=2) +
        ");\n",
        encoding="utf-8",
    )

    absolute_local_base = "https://kexingyan.com" + LOCAL_ASSET_BASE
    for html_path in output.rglob("*.html"):
        html = html_path.read_text(encoding="utf-8")
        html = html.replace(absolute_local_base, asset_base)
        html = html.replace(LOCAL_ASSET_BASE, asset_base)
        html_path.write_text(html, encoding="utf-8")

    for forbidden in (output / "assets" / "photography" / "generated", output / "data"):
        if forbidden.exists():
            raise RuntimeError(f"Private or local-only path entered release output: {forbidden}")

    print(f"Production release staged at: {output}")
    print(f"Photography asset base: {asset_base}")
    print(f"Photography manifest: {manifest_url}")


if __name__ == "__main__":
    main()
