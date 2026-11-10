"""Download the source files and record exactly what was downloaded."""
import hashlib
import json
from datetime import datetime, timezone

import requests

from procurement import config

CHUNK_SIZE_BYTES = 1024 * 1024  # stream 1 MB at a time instead of holding the whole file in memory
TIMEOUT_SECONDS = 120


def ted_url(year):
    return config.TED_URL_TEMPLATE.format(year=year)


def ted_zip_path(year):
    return config.TED_RAW_DIR / f"ted-contract-award-notices-{year}.zip"


def world_bank_csv_path():
    return config.WORLD_BANK_RAW_DIR / config.WORLD_BANK_FILE_NAME


def sha256_of_file(path):
    """Fingerprint a file, so results can be traced back to the exact input."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(CHUNK_SIZE_BYTES)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def download_file(url, destination):
    """Download `url` to `destination` unless it already exists.

    Returns True if a download happened, False if the file was already present.
    The file is written to a temporary `.part` name first and renamed only when
    complete, so an interrupted download never leaves a truncated file that a
    later run would mistake for a finished one.
    """
    if destination.exists():
        return False

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial_path = destination.with_name(destination.name + ".part")

    with requests.get(url, stream=True, timeout=TIMEOUT_SECONDS) as response:
        response.raise_for_status()
        with open(partial_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE_BYTES):
                handle.write(chunk)

    partial_path.replace(destination)
    return True


def read_manifest():
    if config.MANIFEST_PATH.exists():
        return json.loads(config.MANIFEST_PATH.read_text())
    return {}


def record_in_manifest(manifest, url, path):
    """Store source URL, size, fingerprint and download time for one file."""
    manifest[path.name] = {
        "url": url,
        "bytes": path.stat().st_size,
        "sha256": sha256_of_file(path),
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def download_sources(years):
    """Download every TED year and the World Bank file; return their local paths."""
    manifest = read_manifest()
    sources = [(ted_url(year), ted_zip_path(year)) for year in years]
    sources.append((config.WORLD_BANK_URL, world_bank_csv_path()))

    for url, path in sources:
        downloaded = download_file(url, path)
        if downloaded or path.name not in manifest:
            record_in_manifest(manifest, url, path)
        status = "downloaded" if downloaded else "already present"
        size_mb = path.stat().st_size / 1e6
        print(f"  {path.name}: {status} ({size_mb:,.0f} MB)")

    config.MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    return {
        "ted_zips": [ted_zip_path(year) for year in years],
        "world_bank_csv": world_bank_csv_path(),
    }
