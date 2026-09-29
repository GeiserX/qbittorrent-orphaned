# Configuration

All configuration is done through environment variables.

| Variable | Default | Description |
|---|---|---|
| `QBIT_HOST` | `http://qbittorrent:8080` | qBittorrent Web UI URL |
| `QBIT_USER` | `admin` | Username for Web UI authentication |
| `QBIT_PASS` | `password` | Password for Web UI authentication |
| `CATEGORY_FOLDERS` | `Films=W:\Films;Shows=X:\Series` | Semicolon-separated `Category=Path` pairs. Categories must match those configured in qBittorrent. |
| `EXCLUDE_PATTERNS` | *(empty)* | Comma-separated substrings. Any file whose relative path contains one of these patterns (case-insensitive) is skipped. A comma inside a pattern is escaped as `\,` — see below. |
| `IGNORE_SUFFIXES` | *(empty)* | Comma-separated file extensions to ignore in addition to the built-in list. Leading dots are optional (e.g., `ass,ssa` or `.ass,.ssa`). |

## Category Folders Format

```
CATEGORY_NAME=ABSOLUTE_PATH;CATEGORY_NAME2=ABSOLUTE_PATH2
```

Each category name must match exactly what is configured in qBittorrent. Torrents with no category are grouped under the key `__UNCATEGORIZED__`.

Category names and paths may contain spaces and commas — write them literally, and quote only the variable as a whole:

```
CATEGORY_FOLDERS="Books, Comics & Manga=F:\Downloads\Books, Comics & Manga;TV & Movies=F:\Downloads\TV & Movies"
```

One category folder may sit inside another — mapping `__UNCATEGORIZED__` to qBittorrent's default save path, which is the parent of the per-category folders, is a common setup. Files under a nested folder are scanned as part of the category that owns that folder, and the overlap is noted on stderr, so it stays out of a redirected report.

## Patterns Containing Commas

`EXCLUDE_PATTERNS` is comma-separated, so a pattern that itself contains a comma is escaped with a backslash:

```
EXCLUDE_PATTERNS="Books\, Comics & Manga,sample"
```

Quote the whole value. Unquoted, the shell splits on the spaces and runs `Comics` and `Manga,sample` as commands, and Python receives just `Books,` — which is the very mistake this escape exists to prevent.

Note the difference from `CATEGORY_FOLDERS` above: that variable is *semicolon*-separated, so commas inside a category name or path need no escape. `EXCLUDE_PATTERNS` is comma-separated, so they do.

That is two patterns — `Books, Comics & Manga` and `sample`. Without the escape it would be three, and the stray `Books` would silently skip every path containing "books" — `Audiobooks/Dune.m4b`, for instance — while the stray `Comics & Manga` would skip `Comics & Manga Weekly.mkv`. Values with no `\,` in them are unaffected.

