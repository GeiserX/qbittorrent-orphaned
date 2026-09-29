# How it works

## What Are Orphaned Files?

When you remove a torrent from qBittorrent but keep the data on disk, or when external tools (transcoders, renaming scripts, etc.) create files that were never part of a torrent, those files become **orphans**. They consume storage without being seeded or managed. This tool finds them so you can decide what to keep and what to reclaim.

## Steps

1. **Authenticate** -- the script logs in to qBittorrent via `/api/v2/auth/login` and obtains a session cookie.
2. **Fetch torrents** -- it retrieves the full torrent list from `/api/v2/torrents/info`, then for each torrent calls `/api/v2/torrents/files` to get every file path the torrent manages.
3. **Index by category** -- all torrent file paths are normalized (forward slashes, lowercase) and grouped into a lookup set per category.
4. **Walk the filesystem** -- for each configured category folder, the script recursively enumerates files, skipping ignored suffixes, macOS resource forks, and exclude-pattern matches.
5. **Cross-reference** -- every disk file is checked against the corresponding category set. Files not present in any torrent are reported as orphans with their absolute path and human-readable size.

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

## Feature details

- **Single-file, pure Python** -- no build step, no complex dependencies, just `requests`.
- **Web API v2** -- authenticates and queries qBittorrent over HTTP; works locally or across a network.
- **Case-insensitive matching** -- handles mixed-case filenames on Windows and Linux alike.
- **Category-aware grouping** -- results are organized by qBittorrent category, with uncategorized torrents collected under `__UNCATEGORIZED__`.
- **Human-readable sizes** -- every orphan is printed alongside its size in KiB, MiB, GiB, etc.
- **Configurable metadata ignore list** -- common metadata files (`.nfo`, `.jpg`, `.png`, `.srt`, `.sub`, `.idx`, `.txt`, `.bin`, `.svg`) are skipped by default. You can extend this list.
- **Exclude patterns** -- filter out known non-torrent files (e.g., transcoded 720p copies) by substring match.
- **macOS-safe** -- automatically skips `._` resource fork files.
