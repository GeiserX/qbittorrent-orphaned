#!/usr/bin/env python3
"""
orphan_detector.py – list files that are present on disk but absent from
                     any torrent managed by qBittorrent, grouped by category.

Environment Variables:
    QBIT_HOST           qBittorrent Web UI URL (default: http://qbittorrent:8080)
    QBIT_USER           qBittorrent username (default: admin)
    QBIT_PASS           qBittorrent password (default: password)
    CATEGORY_FOLDERS    Category to folder mapping (e.g., Films=/mnt/films;Shows=/mnt/shows)
    EXCLUDE_PATTERNS    Comma-separated patterns to exclude (e.g., " - 720p.mkv,sample")
    IGNORE_SUFFIXES     Additional file suffixes to ignore (comma-separated)
"""

from __future__ import annotations
import os
import re
import sys
import json
import requests
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set

##############################################################################
# 1. Configuration helpers
##############################################################################

def getenv(name: str, default: str) -> str:
    """Tiny getenv wrapper that also trims quotes added by some shells."""
    return os.getenv(name, default).strip(' "\'')

def parse_list(raw: str) -> List[str]:
    """Parse comma-separated list from env var."""
    return [p.strip() for p in raw.split(",") if p.strip()]

QBIT_HOST = getenv("QBIT_HOST", "http://qbittorrent:8080").rstrip("/")
QBIT_USER = getenv("QBIT_USER", "admin")
QBIT_PASS = getenv("QBIT_PASS", "password")

def parse_category_map(raw: str) -> Dict[str, Path]:
    """
    Convert  'Films=W:\\Films;Shows=/mnt/shows'  into a dict
               {'Films': Path('W:/Films'), ...}
    """
    pairs = [p for p in raw.split(";") if p.strip()]
    mapping: Dict[str, Path] = {}
    for pair in pairs:
        try:
            cat, folder = pair.split("=", 1)
        except ValueError:
            print(f"⚠️  Skipping malformed CATEGORY_FOLDERS entry: {pair!r}")
            continue
        mapping[cat.strip()] = Path(folder.strip())
    return mapping

CATEGORY_MAP = parse_category_map(getenv(
    "CATEGORY_FOLDERS",
    "Films=W:\\Films;"
    "Shows=X:\\Series"
))

# File suffixes to always ignore (metadata, images, etc.)
DEFAULT_IGNORE_SUFFIXES = {".nfo", ".jpg", ".jpeg", ".png", ".svg", ".bin", ".txt", ".srt", ".sub", ".idx"}
extra_suffixes = parse_list(getenv("IGNORE_SUFFIXES", ""))
IGNORE_SUFFIXES = DEFAULT_IGNORE_SUFFIXES | {s if s.startswith('.') else f'.{s}' for s in extra_suffixes}

# Patterns to exclude from orphan detection (e.g., transcoded versions)
# Patterns are matched case-insensitively against the full relative path
EXCLUDE_PATTERNS = parse_list(getenv("EXCLUDE_PATTERNS", ""))

##############################################################################
# 2. Connect to qBittorrent and fetch torrent file lists
##############################################################################

class Qbit:
    """Very small wrapper around the qBittorrent Web API v2."""

    def __init__(self, host: str, user: str, password: str) -> None:
        self.api = host + "/api/v2"
        self.session = requests.Session()
        self.login(user, password)

    def login(self, user: str, password: str) -> None:
        r = self.session.post(
            self.api + "/auth/login",
            data={"username": user, "password": password},
            timeout=10
        )
        if r.text != "Ok.":
            sys.exit(f"❌  Login to qBittorrent failed: {r.text}")

    def torrents(self) -> list[dict]:
        """Return list of torrents with at least hash, category."""
        r = self.session.get(self.api + "/torrents/info", timeout=20)
        r.raise_for_status()
        return r.json()

    def files_for(self, torrent_hash: str) -> list[dict]:
        r = self.session.get(
            self.api + "/torrents/files",
            params={"hash": torrent_hash},
            timeout=20
        )
        r.raise_for_status()
        return r.json()

def fetch_torrent_files(qbit: Qbit) -> Dict[str, Set[str]]:
    """
    Return {category → set(relative_path.lower())}.
    We store relative paths as qBittorrent reports them (inside the torrent),
    in lowercase so comparison is case-insensitive on Windows.
    """
    cat_files: Dict[str, Set[str]] = defaultdict(set)

    for t in qbit.torrents():
        category = t.get("category") or "__UNCATEGORIZED__"
        for f in qbit.files_for(t["hash"]):
            name = f["name"].replace("\\", "/").lower()
            cat_files[category].add(name)

    return cat_files

##############################################################################
# 3. Walk disk and detect orphaned files
##############################################################################

def should_exclude(path_str: str) -> bool:
    """Check if a path should be excluded based on EXCLUDE_PATTERNS."""
    path_lower = path_str.lower()
    for pattern in EXCLUDE_PATTERNS:
        if pattern.lower() in path_lower:
            return True
    return False

def on_disk(category: str, root: Path) -> Set[Path]:
    """
    Return every file under `root`, relative to `root`, excluding unwanted
    extensions and patterns.
    """
    files: Set[Path] = set()
    if not root.exists():
        print(f"⚠️  Folder for category '{category}' does not exist: {root}")
        return files

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in IGNORE_SUFFIXES:
            continue
        # Skip macOS resource fork files
        if path.name.startswith("._"):
            continue
        # Check exclude patterns
        rel_path = str(path.relative_to(root))
        if should_exclude(rel_path):
            continue
        files.add(path.relative_to(root))
    return files

def detect_orphans(cat_files: Dict[str, Set[str]]) -> Dict[str, list[Path]]:
    """
    Compare torrent files with real files per category and return
    {category → [orphan_path, …]} (full absolute paths).
    """
    orphans: Dict[str, list[Path]] = defaultdict(list)

    for category, folder in CATEGORY_MAP.items():
        disk_files = on_disk(category, folder)
        if not disk_files:
            continue

        torrent_files = cat_files.get(category, set())

        for rel_path in disk_files:
            rel_norm = str(rel_path).replace("\\", "/").lower()
            if rel_norm not in torrent_files:
                orphans[category].append(folder / rel_path)

    return orphans

##############################################################################
# 4. CLI
##############################################################################

def human_size(num: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if num < 1024 or unit == "TiB":
            return f"{num:,.0f} {unit}"
        num /= 1024

def main() -> None:
    qbit = Qbit(QBIT_HOST, QBIT_USER, QBIT_PASS)
    cat_files = fetch_torrent_files(qbit)
    orphans = detect_orphans(cat_files)

    if not orphans:
        print("✅  No orphaned files found.")
        return

    for category in sorted(orphans):
        print(f"\n===== {category} =====")
        for p in sorted(orphans[category]):
            try:
                size = p.stat().st_size
                print(f"{p}    ({human_size(size)})")
            except FileNotFoundError:
                # file disappeared while we were running
                print(f"{p}    (missing?)")

if __name__ == "__main__":
    main()
