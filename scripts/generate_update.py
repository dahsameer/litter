#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


def request_json(url: str, headers: dict) -> list | dict:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def download_bytes(url: str, headers: dict) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()


def version_code_from_version(version: str) -> int:
    cleaned = version.strip().lstrip("vV")
    if not cleaned:
        return 0
    parts = [int(part) for part in re.findall(r"\d+", cleaned)]
    if not parts:
        return 0
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return parts[0] * 100 + parts[1]
    return parts[0] * 10000 + parts[1] * 100 + parts[2]


def version_info_from_apk_name(name: str) -> tuple[str | None, int | None]:
    match = re.search(r"[-_](?P<version>[0-9]+(?:\.[0-9]+)*)[-_](?P<versionCode>[0-9]+)\.apk$", name, re.IGNORECASE)
    if not match:
        return None, None
    version = match.group("version")
    version_code = int(match.group("versionCode"))
    return version, version_code


def normalize_release(release: dict, headers: dict) -> dict:
    assets = release.get("assets") or []
    apk_asset = next(
        (asset for asset in assets if isinstance(asset, dict) and asset.get("name", "").lower().endswith(".apk")),
        None,
    )

    if not apk_asset:
        release_name = release.get("tag_name") or release.get("name") or "<unknown>"
        raise ValueError(f"No APK asset found for release '{release_name}'")

    download_url = apk_asset.get("browser_download_url")
    apk_size = apk_asset.get("size", 0)
    sha256 = ""
    apk_version_code = None
    apk_version_name = None

    if download_url:
        body = download_bytes(download_url, headers)
        apk_size = len(body)
        sha256 = hashlib.sha256(body).hexdigest()
        apk_version_name, apk_version_code = version_info_from_apk_name(apk_asset.get("name", ""))

    version = apk_version_name or release.get("tag_name") or release.get("name") or ""
    version_code = apk_version_code if apk_version_code is not None else version_code_from_version(version)

    return {
        "version": version.lstrip("vV") if version else "",
        "versionCode": version_code,
        "publishedAt": release.get("published_at") or "",
        "downloadUrl": download_url,
        "releaseNotes": release.get("body") or "",
        "apkSize": apk_size,
        "prerelease": bool(release.get("prerelease", False)),
        "draft": bool(release.get("draft", False)),
        "sha256": sha256,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate latest.json and releases.json from GitHub releases.")
    parser.add_argument("--output-dir", "-o", default=".", help="Output directory for generated JSON files.")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY") or "dahsameer/litter", help="GitHub repository slug (owner/name).")
    args = parser.parse_args()

    repo = args.repo
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "release-metadata-generator",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    releases = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}"
        try:
            data = request_json(url, headers)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                print("Repository not found or no releases available.", file=sys.stderr)
                break
            raise
        if not isinstance(data, list):
            break
        if not data:
            break
        releases.extend(data)
        if len(data) < 100:
            break
        page += 1

    normalized = [normalize_release(release, headers) for release in releases]

    latest = normalized[0] if normalized else {}
    past_releases = normalized[1:] if len(normalized) > 1 else []

    latest_data = {
        "version": latest.get("version", ""),
        "versionCode": latest.get("versionCode", 0),
        "minimumVersionCode": past_releases[0].get("versionCode", 0) if past_releases else 0,
        "forceUpdate": False,
        "publishedAt": latest.get("publishedAt", ""),
        "downloadUrl": latest.get("downloadUrl", ""),
        "apkSize": latest.get("apkSize", 0),
        "releaseNotes": latest.get("releaseNotes", ""),
        "sha256": latest.get("sha256", ""),
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_path = output_dir / "latest.json"
    releases_path = output_dir / "releases.json"
    latest_path.write_text(json.dumps(latest_data, indent=2) + "\n", encoding="utf-8")
    releases_path.write_text(json.dumps(past_releases, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {latest_path} and {releases_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
