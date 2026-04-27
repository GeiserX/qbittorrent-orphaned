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
    def test_matches_pattern(self):
        import orphan_detector
        with patch.object(orphan_detector, "EXCLUDE_PATTERNS", ["720p", "sample"]):
            assert orphan_detector.should_exclude("Movie/Movie - 720p.mkv") is True

    def test_case_insensitive(self):
        import orphan_detector
        with patch.object(orphan_detector, "EXCLUDE_PATTERNS", ["720p", "sample"]):
            assert orphan_detector.should_exclude("Movie/SAMPLE.mkv") is True

    def test_no_match(self):
        import orphan_detector
        with patch.object(orphan_detector, "EXCLUDE_PATTERNS", ["720p", "sample"]):
            assert orphan_detector.should_exclude("Movie/Movie.1080p.mkv") is False

    def test_empty_patterns(self):
        import orphan_detector
        with patch.object(orphan_detector, "EXCLUDE_PATTERNS", []):
            assert orphan_detector.should_exclude("anything.mkv") is False


class TestOnDisk:
    def test_finds_files(self):
        import orphan_detector
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "movie.mkv").touch()
            (root / "subdir").mkdir()
            (root / "subdir" / "episode.mkv").touch()

            with patch.object(orphan_detector, "IGNORE_SUFFIXES", {".nfo", ".jpg"}), \
                 patch.object(orphan_detector, "EXCLUDE_PATTERNS", []):
                files = orphan_detector.on_disk("TestCat", root)
            assert Path("movie.mkv") in files
            assert Path("subdir/episode.mkv") in files

    def test_ignores_suffixes(self):
        import orphan_detector
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "movie.mkv").touch()
            (root / "cover.jpg").touch()
            (root / "info.nfo").touch()

            with patch.object(orphan_detector, "IGNORE_SUFFIXES", {".nfo", ".jpg"}), \
                 patch.object(orphan_detector, "EXCLUDE_PATTERNS", []):
                files = orphan_detector.on_disk("TestCat", root)
            assert Path("movie.mkv") in files
            assert Path("cover.jpg") not in files
            assert Path("info.nfo") not in files

    def test_skips_macos_resource_forks(self):
        import orphan_detector
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "._hidden").touch()
            (root / "real.mkv").touch()

            with patch.object(orphan_detector, "IGNORE_SUFFIXES", set()), \
                 patch.object(orphan_detector, "EXCLUDE_PATTERNS", []):
                files = orphan_detector.on_disk("TestCat", root)
            assert Path("real.mkv") in files
            assert Path("._hidden") not in files

    def test_nonexistent_folder(self):
        import orphan_detector
        with patch.object(orphan_detector, "IGNORE_SUFFIXES", set()), \
             patch.object(orphan_detector, "EXCLUDE_PATTERNS", []):
            files = orphan_detector.on_disk("TestCat", Path("/nonexistent/path"))
        assert files == set()


class TestDetectOrphans:
    def test_detects_orphan(self):
        import orphan_detector
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "tracked.mkv").touch()
            (root / "orphan.mkv").touch()

            torrent_files = {"TestCat": {"tracked.mkv"}}

            with patch.object(orphan_detector, "CATEGORY_MAP", {"TestCat": root}), \
                 patch.object(orphan_detector, "IGNORE_SUFFIXES", set()), \
                 patch.object(orphan_detector, "EXCLUDE_PATTERNS", []):
                orphans = orphan_detector.detect_orphans(torrent_files)

            assert "TestCat" in orphans
            orphan_names = [p.name for p in orphans["TestCat"]]
            assert "orphan.mkv" in orphan_names
            assert "tracked.mkv" not in orphan_names

    def test_no_orphans(self):
        import orphan_detector
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "tracked.mkv").touch()

            torrent_files = {"TestCat": {"tracked.mkv"}}

            with patch.object(orphan_detector, "CATEGORY_MAP", {"TestCat": root}), \
                 patch.object(orphan_detector, "IGNORE_SUFFIXES", set()), \
                 patch.object(orphan_detector, "EXCLUDE_PATTERNS", []):
                orphans = orphan_detector.detect_orphans(torrent_files)

            assert orphans == {} or all(len(v) == 0 for v in orphans.values())


class TestDetectOrphansEdgeCases:
    def test_empty_disk_files_skipped(self):
        """Cover line 170-171: empty disk_files triggers continue."""
        import orphan_detector
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Don't create any files — disk_files will be empty

            torrent_files = {"TestCat": {"something.mkv"}}

            with patch.object(orphan_detector, "CATEGORY_MAP", {"TestCat": root}), \
                 patch.object(orphan_detector, "IGNORE_SUFFIXES", set()), \
                 patch.object(orphan_detector, "EXCLUDE_PATTERNS", []):
                orphans = orphan_detector.detect_orphans(torrent_files)

            assert orphans == {} or all(len(v) == 0 for v in orphans.values())

    def test_exclude_pattern_in_on_disk(self):
        """Cover line 157: should_exclude triggers continue in on_disk."""
        import orphan_detector
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "movie.mkv").touch()
            (root / "movie - 720p.mkv").touch()

            with patch.object(orphan_detector, "IGNORE_SUFFIXES", set()), \
                 patch.object(orphan_detector, "EXCLUDE_PATTERNS", ["720p"]):
                files = orphan_detector.on_disk("TestCat", root)

            assert Path("movie.mkv") in files
            assert Path("movie - 720p.mkv") not in files


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

    def test_tebibytes(self):
        """Cover line 188-189: TiB branch (num >= 1024^4)."""
        result = human_size(5 * 1024 ** 4)
        assert "TiB" in result


class TestQbit:
    def test_init_and_login_success(self):
        """Cover lines 79-82, 84-88."""
        import orphan_detector
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Ok."
        mock_session.post.return_value = mock_response

        with patch("orphan_detector.requests.Session", return_value=mock_session):
            qbit = orphan_detector.Qbit("http://localhost:8080", "admin", "pass")

        assert qbit.api == "http://localhost:8080/api/v2"
        mock_session.post.assert_called_once_with(
            "http://localhost:8080/api/v2/auth/login",
            data={"username": "admin", "password": "pass"},
            timeout=10
        )

    def test_login_failure_exits(self):
        """Cover lines 90-91: login fails when response != 'Ok.'"""
        import orphan_detector
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Fails."
        mock_session.post.return_value = mock_response

        with patch("orphan_detector.requests.Session", return_value=mock_session):
            with pytest.raises(SystemExit) as exc_info:
                orphan_detector.Qbit("http://localhost:8080", "admin", "wrong")
        assert "Login to qBittorrent failed" in str(exc_info.value)

    def test_torrents(self):
        """Cover lines 93-97."""
        import orphan_detector
        mock_session = MagicMock()
        mock_login_resp = MagicMock()
        mock_login_resp.text = "Ok."
        mock_session.post.return_value = mock_login_resp

        torrent_data = [{"hash": "abc123", "category": "Films"}]
        mock_get_resp = MagicMock()
        mock_get_resp.json.return_value = torrent_data
        mock_get_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_get_resp

        with patch("orphan_detector.requests.Session", return_value=mock_session):
            qbit = orphan_detector.Qbit("http://localhost:8080", "admin", "pass")
            result = qbit.torrents()

        assert result == torrent_data
        mock_session.get.assert_called_with(
            "http://localhost:8080/api/v2/torrents/info", timeout=20
        )

    def test_files_for(self):
        """Cover lines 99-106."""
        import orphan_detector
        mock_session = MagicMock()
        mock_login_resp = MagicMock()
        mock_login_resp.text = "Ok."
        mock_session.post.return_value = mock_login_resp

        file_data = [{"name": "Movie/movie.mkv"}]
        mock_get_resp = MagicMock()
        mock_get_resp.json.return_value = file_data
        mock_get_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_get_resp

        with patch("orphan_detector.requests.Session", return_value=mock_session):
            qbit = orphan_detector.Qbit("http://localhost:8080", "admin", "pass")
            result = qbit.files_for("abc123")

        assert result == file_data
        mock_session.get.assert_called_with(
            "http://localhost:8080/api/v2/torrents/files",
            params={"hash": "abc123"},
            timeout=20
        )


class TestFetchTorrentFiles:
    def test_basic_fetch(self):
        """Cover lines 114-122."""
        import orphan_detector
        mock_session = MagicMock()
        mock_login_resp = MagicMock()
        mock_login_resp.text = "Ok."
        mock_session.post.return_value = mock_login_resp

        torrents = [
            {"hash": "aaa", "category": "Films"},
            {"hash": "bbb", "category": "Shows"},
            {"hash": "ccc", "category": ""},  # empty category -> __UNCATEGORIZED__
        ]
        files_map = {
            "aaa": [{"name": "Film1/film.mkv"}],
            "bbb": [{"name": "Show1\\episode.mkv"}],
            "ccc": [{"name": "Random/file.mkv"}],
        }

        def mock_get(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            if "torrents/info" in url:
                resp.json.return_value = torrents
            elif "torrents/files" in url:
                h = kwargs["params"]["hash"]
                resp.json.return_value = files_map[h]
            return resp

        mock_session.get.side_effect = mock_get

        with patch("orphan_detector.requests.Session", return_value=mock_session):
            qbit = orphan_detector.Qbit("http://localhost:8080", "admin", "pass")
            result = orphan_detector.fetch_torrent_files(qbit)

        assert "film1/film.mkv" in result["Films"]
        assert "show1/episode.mkv" in result["Shows"]
        assert "random/file.mkv" in result["__UNCATEGORIZED__"]


class TestMain:
    def test_main_no_orphans(self, capsys):
        """Cover lines 192-199: main with no orphans."""
        import orphan_detector
        mock_session = MagicMock()
        mock_login_resp = MagicMock()
        mock_login_resp.text = "Ok."
        mock_session.post.return_value = mock_login_resp

        mock_get_resp = MagicMock()
        mock_get_resp.json.return_value = []
        mock_get_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_get_resp

        with patch("orphan_detector.requests.Session", return_value=mock_session), \
             patch.object(orphan_detector, "QBIT_HOST", "http://localhost:8080"), \
             patch.object(orphan_detector, "QBIT_USER", "admin"), \
             patch.object(orphan_detector, "QBIT_PASS", "pass"), \
             patch.object(orphan_detector, "CATEGORY_MAP", {}):
            orphan_detector.main()

        captured = capsys.readouterr()
        assert "No orphaned files found" in captured.out

    def test_main_with_orphans(self, capsys):
        """Cover lines 201-209: main with orphans found."""
        import orphan_detector

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orphan_file = root / "orphan.mkv"
            orphan_file.write_bytes(b"x" * 2048)

            mock_session = MagicMock()
            mock_login_resp = MagicMock()
            mock_login_resp.text = "Ok."
            mock_session.post.return_value = mock_login_resp

            mock_get_resp = MagicMock()
            mock_get_resp.json.return_value = []
            mock_get_resp.raise_for_status = MagicMock()
            mock_session.get.return_value = mock_get_resp

            with patch("orphan_detector.requests.Session", return_value=mock_session), \
                 patch.object(orphan_detector, "QBIT_HOST", "http://localhost:8080"), \
                 patch.object(orphan_detector, "QBIT_USER", "admin"), \
                 patch.object(orphan_detector, "QBIT_PASS", "pass"), \
                 patch.object(orphan_detector, "CATEGORY_MAP", {"TestCat": root}), \
                 patch.object(orphan_detector, "IGNORE_SUFFIXES", set()), \
                 patch.object(orphan_detector, "EXCLUDE_PATTERNS", []):
                orphan_detector.main()

            captured = capsys.readouterr()
            assert "TestCat" in captured.out
            assert "orphan.mkv" in captured.out
            assert "KiB" in captured.out

    def test_main_orphan_file_not_found(self, capsys):
        """Cover lines 207-209: file disappears during run."""
        import orphan_detector

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orphan_file = root / "vanishing.mkv"
            orphan_file.touch()

            mock_session = MagicMock()
            mock_login_resp = MagicMock()
            mock_login_resp.text = "Ok."
            mock_session.post.return_value = mock_login_resp

            mock_get_resp = MagicMock()
            mock_get_resp.json.return_value = []
            mock_get_resp.raise_for_status = MagicMock()
            mock_session.get.return_value = mock_get_resp

            with patch("orphan_detector.requests.Session", return_value=mock_session), \
                 patch.object(orphan_detector, "QBIT_HOST", "http://localhost:8080"), \
                 patch.object(orphan_detector, "QBIT_USER", "admin"), \
                 patch.object(orphan_detector, "QBIT_PASS", "pass"), \
                 patch.object(orphan_detector, "CATEGORY_MAP", {"TestCat": root}), \
                 patch.object(orphan_detector, "IGNORE_SUFFIXES", set()), \
                 patch.object(orphan_detector, "EXCLUDE_PATTERNS", []):
                # Delete the file after on_disk found it but before main prints it
                original_stat = Path.stat
                def fake_stat(self, **kwargs):
                    if "vanishing" in str(self):
                        raise FileNotFoundError("gone")
                    return original_stat(self, **kwargs)

                with patch.object(Path, "stat", fake_stat):
                    orphan_detector.main()

            captured = capsys.readouterr()
            assert "vanishing.mkv" in captured.out
            assert "missing?" in captured.out
