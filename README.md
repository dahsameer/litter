# Litter release hosting

This repository hosts a static Android release page on GitHub Pages and uses GitHub Releases as the source of truth.

## How publishing works

1. Create a GitHub Release with a tag such as `v1.4.2`.
2. Attach one or more APK files to that release.
3. Add release notes in the GitHub Release body.
4. Publish the release.

The workflow in [.github/workflows/generate-update.yml](.github/workflows/generate-update.yml) will:

- read all releases from the GitHub API,
- find the attached APK asset,
- calculate the APK size and SHA256 checksum,
- generate update.json,
- and publish index.html plus update.json to the gh-pages branch for GitHub Pages.

## GitHub Pages setup

Enable GitHub Pages for the repository and publish from the `gh-pages` branch root.

1. Go to the repository Settings → Pages.
2. Select the `gh-pages` branch.
3. Choose the root folder (`/`) as the publishing source.
4. Save and wait for the site to become available.

The workflow writes generated site files to `gh-pages`, so you do not need to commit these outputs to `main`.

## Files

- [index.html](index.html) — the static release homepage.
- [update.json](update.json) — generated metadata used by the website.
- [scripts/generate_update.py](scripts/generate_update.py) — the script that builds update.json.
