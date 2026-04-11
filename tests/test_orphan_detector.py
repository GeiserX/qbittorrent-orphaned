"""Tests for qbittorrent-orphaned orphan_detector.py"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from orphan_detector import (
    parse_list,
    parse_category_map,
    should_exclude,
    on_disk,
    detect_orphans,
    human_size,
)


class TestParseList:
    def test_comma_separated(self):
        assert parse_list("a, b, c") == ["a", "b", "c"]

    def test_empty_string(self):
        assert parse_list("") == []

    def test_single_item(self):
        assert parse_list("only") == ["only"]

    def test_trailing_comma(self):
        assert parse_list("a,b,") == ["a", "b"]


class TestParseCategoryMap:
    def test_basic_mapping(self):
        result = parse_category_map("Films=/mnt/films;Shows=/mnt/shows")
        assert result == {"Films": Path("/mnt/films"), "Shows": Path("/mnt/shows")}

    def test_single_category(self):
        result = parse_category_map("Movies=/data/movies")
        assert result == {"Movies": Path("/data/movies")}

    def test_empty_string(self):
        result = parse_category_map("")
        assert result == {}

    def test_windows_paths(self):
        result = parse_category_map("Films=W:\\Films;Shows=X:\\Series")
        assert "Films" in result
        assert "Shows" in result

    def test_malformed_entry_skipped(self):
        result = parse_category_map("ValidCat=/path;malformed_no_equals")
        assert "ValidCat" in result
        assert len(result) == 1


class TestShouldExclude:
    @patch("orphan_detector.EXCLUDE_PATTERNS", ["720p", "sample"])
    def test_matches_pattern(self):
        assert should_exclude("Movie/Movie - 720p.mkv") is True

    @patch("orphan_detector.EXCLUDE_PATTERNS", ["720p", "sample"])
    def test_case_insensitive(self):
        assert should_exclude("Movie/SAMPLE.mkv") is True

    @patch("orphan_detector.EXCLUDE_PATTERNS", ["720p", "sample"])
    def test_no_match(self):
        assert should_exclude("Movie/Movie.1080p.mkv") is False

    @patch("orphan_detector.EXCLUDE_PATTERNS", [])
    def test_empty_patterns(self):
        assert should_exclude("anything.mkv") is False


class TestOnDisk:
    def test_finds_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "movie.mkv").touch()
            (root / "subdir").mkdir()
            (root / "subdir" / "episode.mkv").touch()

            with patch("orphan_detector.IGNORE_SUFFIXES", {".nfo", ".jpg"}):
                with patch("orphan_detector.EXCLUDE_PATTERNS", []):
                    files = on_disk("TestCat", root)
            assert Path("movie.mkv") in files
            assert Path("subdir/episode.mkv") in files

    def test_ignores_suffixes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "movie.mkv").touch()
            (root / "cover.jpg").touch()
            (root / "info.nfo").touch()

            with patch("orphan_detector.IGNORE_SUFFIXES", {".nfo", ".jpg"}):
                with patch("orphan_detector.EXCLUDE_PATTERNS", []):
                    files = on_disk("TestCat", root)
            assert Path("movie.mkv") in files
            assert Path("cover.jpg") not in files
            assert Path("info.nfo") not in files

    def test_skips_macos_resource_forks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "._hidden").touch()
            (root / "real.mkv").touch()

            with patch("orphan_detector.IGNORE_SUFFIXES", set()):
                with patch("orphan_detector.EXCLUDE_PATTERNS", []):
                    files = on_disk("TestCat", root)
            assert Path("real.mkv") in files
            assert Path("._hidden") not in files

    def test_nonexistent_folder(self):
        with patch("orphan_detector.IGNORE_SUFFIXES", set()):
            with patch("orphan_detector.EXCLUDE_PATTERNS", []):
                files = on_disk("TestCat", Path("/nonexistent/path"))
        assert files == set()


class TestDetectOrphans:
    def test_detects_orphan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "tracked.mkv").touch()
            (root / "orphan.mkv").touch()

            torrent_files = {"TestCat": {"tracked.mkv"}}

            with patch("orphan_detector.CATEGORY_MAP", {"TestCat": root}):
                with patch("orphan_detector.IGNORE_SUFFIXES", set()):
                    with patch("orphan_detector.EXCLUDE_PATTERNS", []):
                        orphans = detect_orphans(torrent_files)

            assert "TestCat" in orphans
            orphan_names = [p.name for p in orphans["TestCat"]]
            assert "orphan.mkv" in orphan_names
            assert "tracked.mkv" not in orphan_names

    def test_no_orphans(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "tracked.mkv").touch()

            torrent_files = {"TestCat": {"tracked.mkv"}}

            with patch("orphan_detector.CATEGORY_MAP", {"TestCat": root}):
                with patch("orphan_detector.IGNORE_SUFFIXES", set()):
                    with patch("orphan_detector.EXCLUDE_PATTERNS", []):
                        orphans = detect_orphans(torrent_files)

            assert orphans == {} or all(len(v) == 0 for v in orphans.values())


class TestHumanSize:
    def test_bytes(self):
        assert "B" in human_size(500)

    def test_kibibytes(self):
        result = human_size(2048)
        assert "KiB" in result

    def test_mebibytes(self):
        result = human_size(5 * 1024 * 1024)
        assert "MiB" in result

    def test_gibibytes(self):
        result = human_size(3 * 1024 ** 3)
        assert "GiB" in result
