# Installation

<p>
  <img src="https://img.shields.io/badge/python-3.8%2B-3776AB.svg?logo=python&logoColor=white" alt="Python 3.8+"/>
  <img src="https://img.shields.io/badge/dependency-requests-green.svg" alt="requests"/>
</p>

## Install from PyPI

```bash
pip install qbittorrent-orphaned
```

## Standalone

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

## Docker

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

