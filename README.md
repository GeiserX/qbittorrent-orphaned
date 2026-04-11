<p align="center">
  <img src="https://raw.githubusercontent.com/GeiserX/qbittorrent-orphaned/main/docs/images/banner.svg" alt="qbittorrent-orphaned banner" width="900"/>
</p>

<p align="center">
  <a href="https://pypi.org/project/qbittorrent-orphaned/"><img src="https://img.shields.io/pypi/v/qbittorrent-orphaned.svg" alt="PyPI version"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-blue.svg" alt="License: GPL-3.0"/></a>
  <img src="https://img.shields.io/badge/python-3.8%2B-3776AB.svg?logo=python&logoColor=white" alt="Python 3.8+"/>
  <img src="https://img.shields.io/badge/dependency-requests-green.svg" alt="requests"/>
  <a href="https://codecov.io/gh/GeiserX/qbittorrent-orphaned"><img src="https://img.shields.io/codecov/c/github/GeiserX/qbittorrent-orphaned.svg" alt="Coverage"/></a>
</p>

---

**qbittorrent-orphaned** is a lightweight utility that identifies *orphaned files* -- files that exist on disk but are **not tracked by any torrent** in your qBittorrent instance. It connects to the qBittorrent Web API v2, walks the directories you configure, cross-references every file against every torrent, and reports what does not belong.

## What Are Orphaned Files?

When you remove a torrent from qBittorrent but keep the data on disk, or when external tools (transcoders, renaming scripts, etc.) create files that were never part of a torrent, those files become **orphans**. They consume storage without being seeded or managed. This tool finds them so you can decide what to keep and what to reclaim.

## Features

- **Single-file, pure Python** -- no build step, no complex dependencies, just `requests`.
- **Web API v2** -- authenticates and queries qBittorrent over HTTP; works locally or across a network.
- **Case-insensitive matching** -- handles mixed-case filenames on Windows and Linux alike.
- **Category-aware grouping** -- results are organized by qBittorrent category, with uncategorized torrents collected under `__UNCATEGORIZED__`.
- **Human-readable sizes** -- every orphan is printed alongside its size in KiB, MiB, GiB, etc.
- **Configurable metadata ignore list** -- common metadata files (`.nfo`, `.jpg`, `.png`, `.srt`, `.sub`, `.idx`, `.txt`, `.bin`, `.svg`) are skipped by default. You can extend this list.
- **Exclude patterns** -- filter out known non-torrent files (e.g., transcoded 720p copies) by substring match.
- **macOS-safe** -- automatically skips `._` resource fork files.

## Quick Start

### Install from PyPI

```bash
pip install qbittorrent-orphaned
```

### Standalone

```bash
QBIT_HOST=http://localhost:8080 \
QBIT_USER=admin \
QBIT_PASS=yourpassword \
CATEGORY_FOLDERS="Films=/mnt/media/films;Shows=/mnt/media/shows" \
qbittorrent-orphaned
```

You can also run the script directly without installing:

```bash
pip install requests

QBIT_HOST=http://localhost:8080 \
QBIT_USER=admin \
QBIT_PASS=yourpassword \
CATEGORY_FOLDERS="Films=/mnt/media/films;Shows=/mnt/media/shows" \
python orphan_detector.py
```

### Docker

There is no pre-built image yet, but you can run it easily with a one-liner:

```bash
docker run --rm \
  -e QBIT_HOST=http://qbittorrent:8080 \
  -e QBIT_USER=admin \
  -e QBIT_PASS=yourpassword \
  -e CATEGORY_FOLDERS="Films=/media/films;Shows=/media/shows" \
  -v /mnt/media:/media:ro \
  --network=host \
  python:3-alpine sh -c "pip install --quiet requests && python /app/orphan_detector.py"
```

Mount the script into the container if you prefer a cleaner approach:

```bash
docker run --rm \
  -v "$(pwd)/orphan_detector.py:/app/orphan_detector.py:ro" \
  -v /mnt/media:/media:ro \
  -e QBIT_HOST=http://qbittorrent:8080 \
  -e QBIT_USER=admin \
  -e QBIT_PASS=yourpassword \
  -e CATEGORY_FOLDERS="Films=/media/films;Shows=/media/shows" \
  python:3-alpine sh -c "pip install --quiet requests && python /app/orphan_detector.py"
```

> **Tip:** If qBittorrent runs in its own container, make sure both containers share a Docker network (or use `--network=host`) so the hostname resolves.

## Configuration

All configuration is done through environment variables.

| Variable | Default | Description |
|---|---|---|
| `QBIT_HOST` | `http://qbittorrent:8080` | qBittorrent Web UI URL |
| `QBIT_USER` | `admin` | Username for Web UI authentication |
| `QBIT_PASS` | `password` | Password for Web UI authentication |
| `CATEGORY_FOLDERS` | `Films=W:\Films;Shows=X:\Series` | Semicolon-separated `Category=Path` pairs. Categories must match those configured in qBittorrent. |
| `EXCLUDE_PATTERNS` | *(empty)* | Comma-separated substrings. Any file whose relative path contains one of these patterns (case-insensitive) is skipped. |
| `IGNORE_SUFFIXES` | *(empty)* | Comma-separated file extensions to ignore in addition to the built-in list. Leading dots are optional (e.g., `ass,ssa` or `.ass,.ssa`). |

### Category Folders Format

```
CATEGORY_NAME=ABSOLUTE_PATH;CATEGORY_NAME2=ABSOLUTE_PATH2
```

Each category name must match exactly what is configured in qBittorrent. Torrents with no category are grouped under the key `__UNCATEGORIZED__`.

## Example Output

```
===== Films =====
/mnt/media/films/Some.Movie.2023/Some.Movie.2023.mkv    (4,215 MiB)
/mnt/media/films/Old.Film.1999/Old.Film.1999.avi        (702 MiB)

===== Shows =====
/mnt/media/shows/Series.Name.S01/Episode.05.mkv          (1,102 MiB)
```

When no orphans are found the output is simply:

```
No orphaned files found.
```

## How It Works

1. **Authenticate** -- the script logs in to qBittorrent via `/api/v2/auth/login` and obtains a session cookie.
2. **Fetch torrents** -- it retrieves the full torrent list from `/api/v2/torrents/info`, then for each torrent calls `/api/v2/torrents/files` to get every file path the torrent manages.
3. **Index by category** -- all torrent file paths are normalized (forward slashes, lowercase) and grouped into a lookup set per category.
4. **Walk the filesystem** -- for each configured category folder, the script recursively enumerates files, skipping ignored suffixes, macOS resource forks, and exclude-pattern matches.
5. **Cross-reference** -- every disk file is checked against the corresponding category set. Files not present in any torrent are reported as orphans with their absolute path and human-readable size.

## License

[GPL-3.0](LICENSE)
