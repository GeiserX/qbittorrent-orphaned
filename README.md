# qbittorrent-orphaned

Find files on disk that aren't tracked by any qBittorrent torrent, grouped by category.

## Features

- Connects to qBittorrent via Web API v2
- Compares disk files with torrent-tracked files (case-insensitive)
- Groups orphaned files by category with sizes
- Configurable exclude patterns (e.g., transcoded versions)
- Ignores metadata files (.nfo, .jpg, etc.)

## Installation

```bash
pip install requests
```

## Usage

```bash
# Basic usage
QBIT_HOST=http://localhost:8080 \
QBIT_USER=admin \
QBIT_PASS=yourpassword \
CATEGORY_FOLDERS="Films=/mnt/media/films;Shows=/mnt/media/shows" \
python orphan_detector.py

# Exclude transcoded 720p versions (from media-transcoder, etc.)
EXCLUDE_PATTERNS=" - 720p.mkv" \
CATEGORY_FOLDERS="Films=/mnt/films;Shows=/mnt/shows" \
python orphan_detector.py

# Multiple exclude patterns
EXCLUDE_PATTERNS=" - 720p.mkv,sample,trailer" \
python orphan_detector.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QBIT_HOST` | `http://qbittorrent:8080` | qBittorrent Web UI URL |
| `QBIT_USER` | `admin` | qBittorrent username |
| `QBIT_PASS` | `password` | qBittorrent password |
| `CATEGORY_FOLDERS` | `Films=W:\Films;Shows=X:\Series` | Category to folder mapping (semicolon-separated) |
| `EXCLUDE_PATTERNS` | `` | Comma-separated patterns to exclude from detection |
| `IGNORE_SUFFIXES` | `` | Additional file suffixes to ignore (comma-separated) |

## Category Folders Format

```
CATEGORY_NAME=ABSOLUTE_PATH;CATEGORY_NAME2=ABSOLUTE_PATH2
```

Categories must match those configured in qBittorrent. Uncategorized torrents are grouped under `__UNCATEGORIZED__`.

## License

MIT