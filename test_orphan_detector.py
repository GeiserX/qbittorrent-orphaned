"""Tests for orphan_detector.py — targeting 90%+ coverage."""

from __future__ import annotations

import os
import sys
import importlib
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# Helper: import/reimport the module with controlled env vars
# ---------------------------------------------------------------------------

def _import_fresh(env_overrides: dict | None = None):
    """
    (Re)import orphan_detector with a clean environment so that module-level
    globals (QBIT_HOST, CATEGORY_MAP, etc.) pick up the patched env vars.
    """
    env = {
        "QBIT_HOST": "http://localhost:9090",
        "QBIT_USER": "testuser",
        "QBIT_PASS": "testpass",
        "CATEGORY_FOLDERS": "Movies=/tmp/movies;Shows=/tmp/shows",
        "EXCLUDE_PATTERNS": "",
        "IGNORE_SUFFIXES": "",
    }
    if env_overrides:
        env.update(env_overrides)

    with patch.dict(os.environ, env, clear=False):
        if "orphan_detector" in sys.modules:
            mod = importlib.reload(sys.modules["orphan_detector"])
        else:
            mod = importlib.import_module("orphan_detector")
    return mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_module():
    """Remove cached module so each test can reimport with its own env."""
    yield
    sys.modules.pop("orphan_detector", None)


# ===========================================================================
# 1. getenv
# ===========================================================================

class TestGetenv:
    def test_returns_default_when_var_unset(self):
        mod = _import_fresh()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("__TEST_UNSET__", None)
            assert mod.getenv("__TEST_UNSET__", "fallback") == "fallback"

    def test_returns_env_value(self):
        mod = _import_fresh()
        with patch.dict(os.environ, {"__TEST_SET__": "hello"}, clear=False):
            assert mod.getenv("__TEST_SET__", "nope") == "hello"

    def test_strips_surrounding_quotes(self):
        mod = _import_fresh()
        with patch.dict(os.environ, {"__TEST_Q__": '"quoted"'}, clear=False):
            assert mod.getenv("__TEST_Q__", "") == "quoted"

    def test_strips_single_quotes(self):
        mod = _import_fresh()
        with patch.dict(os.environ, {"__TEST_SQ__": "'single'"}, clear=False):
            assert mod.getenv("__TEST_SQ__", "") == "single"

    def test_strips_spaces(self):
        mod = _import_fresh()
        with patch.dict(os.environ, {"__TEST_SP__": "  spaced  "}, clear=False):
            assert mod.getenv("__TEST_SP__", "") == "spaced"


# ===========================================================================
# 2. parse_list
# ===========================================================================

class TestParseList:
    def test_basic_csv(self):
        mod = _import_fresh()
        assert mod.parse_list("a,b,c") == ["a", "b", "c"]

    def test_strips_whitespace(self):
        mod = _import_fresh()
        assert mod.parse_list(" a , b , c ") == ["a", "b", "c"]

    def test_empty_string(self):
        mod = _import_fresh()
        assert mod.parse_list("") == []

    def test_trailing_comma(self):
        mod = _import_fresh()
        assert mod.parse_list("a,b,") == ["a", "b"]

    def test_only_commas(self):
        mod = _import_fresh()
        assert mod.parse_list(",,,") == []


# ===========================================================================
# 3. parse_category_map
# ===========================================================================

class TestParseCategoryMap:
    def test_basic_parsing(self):
        mod = _import_fresh()
        result = mod.parse_category_map("Films=/mnt/films;Shows=/mnt/shows")
        assert result == {"Films": Path("/mnt/films"), "Shows": Path("/mnt/shows")}

    def test_empty_string(self):
        mod = _import_fresh()
        assert mod.parse_category_map("") == {}

    def test_malformed_entry_is_skipped(self, capsys):
        mod = _import_fresh()
        result = mod.parse_category_map("good=/ok;badentry;also_good=/yes")
        assert "good" in result
        assert "also_good" in result
        assert len(result) == 2
        captured = capsys.readouterr()
        assert "Skipping malformed" in captured.out

    def test_whitespace_trimmed(self):
        mod = _import_fresh()
        result = mod.parse_category_map("  Cat = /path/to/dir  ")
        assert result == {"Cat": Path("/path/to/dir")}

    def test_value_with_equals_sign(self):
        mod = _import_fresh()
        result = mod.parse_category_map("Key=val=ue")
        assert result == {"Key": Path("val=ue")}

    def test_windows_path(self):
        mod = _import_fresh()
        result = mod.parse_category_map("Films=W:\\Films")
        assert result["Films"] == Path("W:\\Films") or result["Films"] == Path("W:/Films")


# ===========================================================================
# 4. Module-level globals
# ===========================================================================

class TestModuleGlobals:
    def test_qbit_host_default(self):
        mod = _import_fresh({"QBIT_HOST": "http://myhost:1234"})
        assert mod.QBIT_HOST == "http://myhost:1234"

    def test_qbit_host_trailing_slash_stripped(self):
        mod = _import_fresh({"QBIT_HOST": "http://myhost:1234/"})
        assert mod.QBIT_HOST == "http://myhost:1234"

    def test_category_map_loaded(self):
        mod = _import_fresh({"CATEGORY_FOLDERS": "A=/a;B=/b"})
        assert "A" in mod.CATEGORY_MAP
        assert "B" in mod.CATEGORY_MAP

    def test_ignore_suffixes_includes_defaults(self):
        mod = _import_fresh()
        assert ".nfo" in mod.IGNORE_SUFFIXES
        assert ".jpg" in mod.IGNORE_SUFFIXES

    def test_ignore_suffixes_extra_with_dot(self):
        mod = _import_fresh({"IGNORE_SUFFIXES": ".mkv,.avi"})
        assert ".mkv" in mod.IGNORE_SUFFIXES
        assert ".avi" in mod.IGNORE_SUFFIXES

    def test_ignore_suffixes_extra_without_dot(self):
        mod = _import_fresh({"IGNORE_SUFFIXES": "mkv,avi"})
        assert ".mkv" in mod.IGNORE_SUFFIXES
        assert ".avi" in mod.IGNORE_SUFFIXES

    def test_exclude_patterns_loaded(self):
        mod = _import_fresh({"EXCLUDE_PATTERNS": "720p,sample"})
        assert mod.EXCLUDE_PATTERNS == ["720p", "sample"]


# ===========================================================================
# 5. Qbit class
# ===========================================================================

class TestQbit:
    def test_login_success(self):
        mod = _import_fresh()
        with patch("orphan_detector.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_resp = MagicMock()
            mock_resp.text = "Ok."
            mock_session.post.return_value = mock_resp

            qbit = mod.Qbit("http://host:8080", "user", "pass")
            mock_session.post.assert_called_once_with(
                "http://host:8080/api/v2/auth/login",
                data={"username": "user", "password": "pass"},
                timeout=10,
            )

    def test_login_failure_exits(self):
        mod = _import_fresh()
        with patch("orphan_detector.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_resp = MagicMock()
            mock_resp.text = "Fails."
            mock_session.post.return_value = mock_resp

            with pytest.raises(SystemExit, match="Login to qBittorrent failed"):
                mod.Qbit("http://host:8080", "user", "wrong")

    def test_torrents_returns_json(self):
        mod = _import_fresh()
        with patch("orphan_detector.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_login = MagicMock(text="Ok.")
            mock_torrents = MagicMock()
            mock_torrents.json.return_value = [{"hash": "abc", "category": "Movies"}]
            mock_session.post.return_value = mock_login
            mock_session.get.return_value = mock_torrents

            qbit = mod.Qbit("http://h:80", "u", "p")
            result = qbit.torrents()
            assert result == [{"hash": "abc", "category": "Movies"}]

    def test_files_for_returns_json(self):
        mod = _import_fresh()
        with patch("orphan_detector.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_login = MagicMock(text="Ok.")
            mock_files = MagicMock()
            mock_files.json.return_value = [{"name": "movie.mkv"}]
            mock_session.post.return_value = mock_login
            mock_session.get.return_value = mock_files

            qbit = mod.Qbit("http://h:80", "u", "p")
            result = qbit.files_for("abc123")
            assert result == [{"name": "movie.mkv"}]
            mock_session.get.assert_called_with(
                "http://h:80/api/v2/torrents/files",
                params={"hash": "abc123"},
                timeout=20,
            )


# ===========================================================================
# 6. fetch_torrent_files
# ===========================================================================

class TestFetchTorrentFiles:
    def test_groups_files_by_category(self):
        mod = _import_fresh()
        mock_qbit = MagicMock()
        mock_qbit.torrents.return_value = [
            {"hash": "h1", "category": "Movies"},
            {"hash": "h2", "category": "Shows"},
        ]
        mock_qbit.files_for.side_effect = lambda h: {
            "h1": [{"name": "Film/movie.mkv"}],
            "h2": [{"name": "Show\\episode.mkv"}],
        }[h]

        result = mod.fetch_torrent_files(mock_qbit)
        assert "film/movie.mkv" in result["Movies"]
        # backslash normalized to forward slash
        assert "show/episode.mkv" in result["Shows"]

    def test_uncategorized_torrents(self):
        mod = _import_fresh()
        mock_qbit = MagicMock()
        mock_qbit.torrents.return_value = [
            {"hash": "h1", "category": ""},
        ]
        mock_qbit.files_for.return_value = [{"name": "loose_file.avi"}]

        result = mod.fetch_torrent_files(mock_qbit)
        assert "loose_file.avi" in result["__UNCATEGORIZED__"]

    def test_none_category_treated_as_uncategorized(self):
        mod = _import_fresh()
        mock_qbit = MagicMock()
        mock_qbit.torrents.return_value = [
            {"hash": "h1", "category": None},
        ]
        mock_qbit.files_for.return_value = [{"name": "file.mkv"}]

        result = mod.fetch_torrent_files(mock_qbit)
        assert "file.mkv" in result["__UNCATEGORIZED__"]


# ===========================================================================
# 7. should_exclude
# ===========================================================================

class TestShouldExclude:
    def test_no_patterns_returns_false(self):
        mod = _import_fresh({"EXCLUDE_PATTERNS": ""})
        assert mod.should_exclude("any/path/file.mkv") is False

    def test_matching_pattern(self):
        mod = _import_fresh({"EXCLUDE_PATTERNS": "720p,sample"})
        assert mod.should_exclude("Movie/movie - 720p.mkv") is True

    def test_case_insensitive(self):
        mod = _import_fresh({"EXCLUDE_PATTERNS": "sample"})
        assert mod.should_exclude("Movie/SAMPLE.mkv") is True

    def test_no_match(self):
        mod = _import_fresh({"EXCLUDE_PATTERNS": "720p,sample"})
        assert mod.should_exclude("Movie/movie.1080p.mkv") is False


# ===========================================================================
# 8. on_disk
# ===========================================================================

class TestOnDisk:
    def test_nonexistent_folder_returns_empty(self, capsys):
        mod = _import_fresh()
        result = mod.on_disk("TestCat", Path("/nonexistent/path/xyz"))
        assert result == set()
        captured = capsys.readouterr()
        assert "does not exist" in captured.out

    def test_finds_files(self, tmp_path):
        mod = _import_fresh({"EXCLUDE_PATTERNS": "", "IGNORE_SUFFIXES": ""})
        (tmp_path / "movie.mkv").touch()
        (tmp_path / "sub" / "episode.avi").mkdir(parents=True, exist_ok=True)
        (tmp_path / "sub" / "episode.avi").rmdir()
        (tmp_path / "sub").mkdir(exist_ok=True)
        (tmp_path / "sub" / "episode.avi").touch()

        result = mod.on_disk("Cat", tmp_path)
        rel_paths = {str(p) for p in result}
        assert "movie.mkv" in rel_paths
        assert os.path.join("sub", "episode.avi") in rel_paths

    def test_ignores_default_suffixes(self, tmp_path):
        mod = _import_fresh()
        (tmp_path / "movie.mkv").touch()
        (tmp_path / "info.nfo").touch()
        (tmp_path / "cover.jpg").touch()

        result = mod.on_disk("Cat", tmp_path)
        names = {p.name for p in result}
        assert "movie.mkv" in names
        assert "info.nfo" not in names
        assert "cover.jpg" not in names

    def test_ignores_macos_resource_forks(self, tmp_path):
        mod = _import_fresh()
        (tmp_path / "._hidden").touch()
        (tmp_path / "real.mkv").touch()

        result = mod.on_disk("Cat", tmp_path)
        names = {p.name for p in result}
        assert "._hidden" not in names
        assert "real.mkv" in names

    def test_excludes_patterns(self, tmp_path):
        mod = _import_fresh({"EXCLUDE_PATTERNS": "720p"})
        (tmp_path / "movie - 720p.mkv").touch()
        (tmp_path / "movie - 1080p.mkv").touch()

        result = mod.on_disk("Cat", tmp_path)
        names = {p.name for p in result}
        assert "movie - 720p.mkv" not in names
        assert "movie - 1080p.mkv" in names

    def test_directories_are_not_included(self, tmp_path):
        mod = _import_fresh()
        (tmp_path / "subdir").mkdir()
        (tmp_path / "file.mkv").touch()

        result = mod.on_disk("Cat", tmp_path)
        names = {p.name for p in result}
        assert "subdir" not in names
        assert "file.mkv" in names


# ===========================================================================
# 9. detect_orphans
# ===========================================================================

class TestDetectOrphans:
    def test_no_orphans_when_all_files_in_torrents(self, tmp_path):
        cat_folder = tmp_path / "movies"
        cat_folder.mkdir()
        (cat_folder / "movie.mkv").touch()

        mod = _import_fresh({"CATEGORY_FOLDERS": f"Movies={cat_folder}"})
        cat_files = {"Movies": {"movie.mkv"}}
        result = mod.detect_orphans(cat_files)
        assert len(result) == 0

    def test_orphan_detected_when_not_in_torrents(self, tmp_path):
        cat_folder = tmp_path / "movies"
        cat_folder.mkdir()
        (cat_folder / "orphan.mkv").touch()

        mod = _import_fresh({"CATEGORY_FOLDERS": f"Movies={cat_folder}"})
        cat_files = {"Movies": set()}
        result = mod.detect_orphans(cat_files)
        assert "Movies" in result
        assert any("orphan.mkv" in str(p) for p in result["Movies"])

    def test_case_insensitive_matching(self, tmp_path):
        cat_folder = tmp_path / "movies"
        cat_folder.mkdir()
        (cat_folder / "Movie.MKV").touch()

        mod = _import_fresh({"CATEGORY_FOLDERS": f"Movies={cat_folder}"})
        cat_files = {"Movies": {"movie.mkv"}}
        result = mod.detect_orphans(cat_files)
        assert len(result) == 0

    def test_empty_disk_skipped(self, tmp_path):
        cat_folder = tmp_path / "empty"
        cat_folder.mkdir()

        mod = _import_fresh({"CATEGORY_FOLDERS": f"Movies={cat_folder}"})
        cat_files = {"Movies": {"something.mkv"}}
        result = mod.detect_orphans(cat_files)
        assert len(result) == 0

    def test_category_not_in_torrent_files(self, tmp_path):
        cat_folder = tmp_path / "movies"
        cat_folder.mkdir()
        (cat_folder / "orphan.mkv").touch()

        mod = _import_fresh({"CATEGORY_FOLDERS": f"Movies={cat_folder}"})
        # No "Movies" key in cat_files at all
        cat_files = {}
        result = mod.detect_orphans(cat_files)
        assert "Movies" in result


# ===========================================================================
# 10. human_size
# ===========================================================================

class TestHumanSize:
    def test_bytes(self):
        mod = _import_fresh()
        assert mod.human_size(500) == "500 B"

    def test_kibibytes(self):
        mod = _import_fresh()
        assert mod.human_size(2048) == "2 KiB"

    def test_mebibytes(self):
        mod = _import_fresh()
        result = mod.human_size(5 * 1024 * 1024)
        assert "MiB" in result

    def test_gibibytes(self):
        mod = _import_fresh()
        result = mod.human_size(3 * 1024 ** 3)
        assert "GiB" in result

    def test_tebibytes(self):
        mod = _import_fresh()
        result = mod.human_size(2 * 1024 ** 4)
        assert "TiB" in result

    def test_zero(self):
        mod = _import_fresh()
        assert mod.human_size(0) == "0 B"

    def test_very_large_stays_tib(self):
        mod = _import_fresh()
        result = mod.human_size(999 * 1024 ** 4)
        assert "TiB" in result


# ===========================================================================
# 11. main
# ===========================================================================

class TestMain:
    def test_main_no_orphans(self, capsys, tmp_path):
        cat_folder = tmp_path / "movies"
        cat_folder.mkdir()

        mod = _import_fresh({"CATEGORY_FOLDERS": f"Movies={cat_folder}"})

        with patch.object(mod, "Qbit") as MockQbit:
            mock_qbit = MockQbit.return_value
            mock_qbit.torrents.return_value = []

            mod.main()

        captured = capsys.readouterr()
        assert "No orphaned files found" in captured.out

    def test_main_with_orphans(self, capsys, tmp_path):
        cat_folder = tmp_path / "movies"
        cat_folder.mkdir()
        orphan_file = cat_folder / "orphan.mkv"
        orphan_file.write_bytes(b"x" * 2048)

        mod = _import_fresh({"CATEGORY_FOLDERS": f"Movies={cat_folder}"})

        with patch.object(mod, "Qbit") as MockQbit:
            mock_qbit = MockQbit.return_value
            mock_qbit.torrents.return_value = []

            mod.main()

        captured = capsys.readouterr()
        assert "Movies" in captured.out
        assert "orphan.mkv" in captured.out
        assert "KiB" in captured.out

    def test_main_orphan_file_disappears(self, capsys, tmp_path):
        cat_folder = tmp_path / "movies"
        cat_folder.mkdir()
        orphan_file = cat_folder / "ghost.mkv"
        orphan_file.touch()

        mod = _import_fresh({"CATEGORY_FOLDERS": f"Movies={cat_folder}"})

        with patch.object(mod, "Qbit") as MockQbit:
            mock_qbit = MockQbit.return_value
            mock_qbit.torrents.return_value = []

            # Delete the file after on_disk finds it but before main prints it
            original_detect = mod.detect_orphans

            def detect_then_delete(cat_files):
                result = original_detect(cat_files)
                orphan_file.unlink()
                return result

            with patch.object(mod, "detect_orphans", side_effect=detect_then_delete):
                mod.main()

        captured = capsys.readouterr()
        assert "missing?" in captured.out
