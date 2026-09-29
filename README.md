<p align="center">
  <img src="https://raw.githubusercontent.com/GeiserX/qbittorrent-orphaned/main/docs/images/banner.svg" alt="qbittorrent-orphaned" width="900"/>
</p>

<p align="center">
  <a href="https://pypi.org/project/qbittorrent-orphaned/"><img src="https://img.shields.io/pypi/v/qbittorrent-orphaned.svg" alt="PyPI version"/></a>
  <a href="https://github.com/GeiserX/qbittorrent-orphaned/actions/workflows/tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/GeiserX/qbittorrent-orphaned/tests.yml?label=tests" alt="Tests"/></a>
  <a href="https://github.com/GeiserX/qbittorrent-orphaned/blob/main/LICENSE"><img src="https://img.shields.io/github/license/GeiserX/qbittorrent-orphaned" alt="License"/></a>
  <a href="https://codecov.io/gh/GeiserX/qbittorrent-orphaned"><img src="https://img.shields.io/codecov/c/github/GeiserX/qbittorrent-orphaned.svg" alt="Coverage"/></a>
</p>

**qbittorrent-orphaned** is a lightweight utility that identifies *orphaned files* -- files that exist on disk but are **not tracked by any torrent** in your qBittorrent instance. It connects to the qBittorrent Web API v2, walks the directories you configure, cross-references every file against every torrent, and reports what does not belong.

## Features

- One Python file whose only dependency is `requests`.
- Talks to the qBittorrent Web API v2, locally or over the network.
- Groups results by qBittorrent category, with uncategorized torrents under `__UNCATEGORIZED__`.
- Matches paths case-insensitively and prints each orphan with a readable size.
- Skips common metadata files (`.nfo`, `.jpg`, `.srt` and others) and macOS `._` files. Add your own with `IGNORE_SUFFIXES`.
- Filters known non-torrent files, such as transcoded copies, with `EXCLUDE_PATTERNS`.
- Only reports. It never deletes anything.

## Quick start

```bash
pip install qbittorrent-orphaned
QBIT_HOST=http://localhost:8080 QBIT_USER=admin QBIT_PASS=yourpassword \
  CATEGORY_FOLDERS="Films=/mnt/media/films;Shows=/mnt/media/shows" qbittorrent-orphaned
```

Docker and running the script directly are in [Getting started](https://github.com/GeiserX/qbittorrent-orphaned/blob/main/docs/getting-started.md).

## Documentation

- [Getting started](https://github.com/GeiserX/qbittorrent-orphaned/blob/main/docs/getting-started.md): PyPI, running the script directly, Docker
- [Configuration](https://github.com/GeiserX/qbittorrent-orphaned/blob/main/docs/configuration.md): environment variables, the `CATEGORY_FOLDERS` format, patterns that contain commas
- [How it works](https://github.com/GeiserX/qbittorrent-orphaned/blob/main/docs/how-it-works.md): what counts as an orphan, the steps, example output, feature details

## License

[GPL-3.0-or-later](https://github.com/GeiserX/qbittorrent-orphaned/blob/main/LICENSE)
