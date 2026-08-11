#!/usr/bin/env python3
"""Generate the offline frontend release manifest from canonical VERSION_HISTORY.md."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "VERSION_HISTORY.md"
TARGET = ROOT / "frontend" / "src" / "config" / "versionHistory.json"
RELEASE = re.compile(r"^###\s+(\d+\.\d+\.\d+)\s+—\s+(\d{4}-\d{2}-\d{2})\s+—\s+(.+)$")


def build_manifest() -> dict:
    source = SOURCE.read_text(encoding="utf-8")
    current_match = re.search(r"Current version:\s*([0-9.]+)", source)
    releases: list[dict] = []
    current: dict | None = None
    active_bullet: str | None = None
    for line in source.splitlines():
        match = RELEASE.match(line)
        if match:
            if current and active_bullet:
                current["changes"].append(active_bullet)
            current = {"version": match.group(1), "date": match.group(2), "title": match.group(3), "changes": []}
            releases.append(current)
            active_bullet = None
            continue
        if line.startswith("### ") or line.startswith("## "):
            if current and active_bullet:
                current["changes"].append(active_bullet)
            current = None
            active_bullet = None
            continue
        if current is None:
            continue
        if line.startswith("- "):
            if active_bullet:
                current["changes"].append(active_bullet)
            active_bullet = line[2:].strip()
        elif active_bullet and line.startswith("  "):
            active_bullet += " " + line.strip()
        elif active_bullet and not line.strip():
            current["changes"].append(active_bullet)
            active_bullet = None
    if current and active_bullet:
        current["changes"].append(active_bullet)
    return {
        "current_version": current_match.group(1) if current_match else "unknown",
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "releases": releases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail when the checked-in manifest is stale")
    args = parser.parse_args()
    rendered = json.dumps(build_manifest(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != rendered:
            print("versionHistory.json is stale; run scripts/generate_version_manifest.py")
            return 1
        return 0
    TARGET.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
