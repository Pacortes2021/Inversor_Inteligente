#!/usr/bin/env python3
"""Create a local-only inventory and copy of explicitly allowed legacy data."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ALLOWED_SUFFIXES = {".json", ".jsonl", ".log"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="explicit legacy data directory")
    parser.add_argument("--output", type=Path, default=Path("var/private-baseline"))
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    output = args.output.resolve()
    if output == source or source in output.parents:
        raise SystemExit("output must not be inside the source data directory")
    output.mkdir(parents=True, exist_ok=True)
    copy_root = output / "backup"
    copy_root.mkdir(exist_ok=True)
    files = []
    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        relative = path.relative_to(source)
        destination = copy_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        files.append({
            "relativePath": relative.as_posix(),
            "sizeBytes": path.stat().st_size,
            "sha256": digest(path),
        })
    manifest = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "sourceCategory": "explicit_legacy_data_directory",
        "fileCount": len(files),
        "files": files,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
