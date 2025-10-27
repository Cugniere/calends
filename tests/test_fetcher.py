import pytest
import os
from unittest.mock import Mock, patch, mock_open
from calends.fetcher import ICalFetcher


@pytest.fixture(autouse=True)
def cleanup_cache():
    yield
    if os.path.exists(".calends.pkl"):
        os.remove(".calends.pkl")


class TestICalFetcher:
    def test_init_default_expiration(self):
        fetcher = ICalFetcher(show_progress=False)
        assert fetcher.cache is not None

    def test_init_custom_expiration(self):
        fetcher = ICalFetcher(cache_expiration=300, show_progress=False)
        assert fetcher.cache.expiration == 300


class TestFetchFromUrl:
    def test_invalid_url_empty(self):
        fetcher = ICalFetcher(show_progress=False)
        with pytest.raises(ValueError, match="Invalid URL"):
            fetcher.fetch_from_url("")

    def test_invalid_url_no_protocol(self):
        fetcher = ICalFetcher(show_progress=False)
        with pytest.raises(ValueError, match="Invalid URL"):
            fetcher.fetch_from_url("example.com/calendar.ics")

    def test_invalid_url_wrong_protocol(self):
        fetcher = ICalFetcher(show_progress=False)
        with pytest.raises(ValueError, match="Invalid URL"):
            fetcher.fetch_from_url("ftp://example.com/calendar.ics")

    @patch("calends.fetcher.urlopen")
    def test_fetch_from_url_success(self, mock_urlopen):
        ical_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Test Event
END:VEVENT
END:VCALENDAR"""

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = ical_content.encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetcher = ICalFetcher(show_progress=False)
        result = fetcher.fetch_from_url("https://example.com/calendar.ics")

        assert result == ical_content
        assert "BEGIN:VCALENDAR" in result

    @patch("calends.fetcher.urlopen")
    def test_fetch_from_url_caching(self, mock_urlopen):
        ical_content = """BEGIN:VCALENDAR
VERSION:2.0
END:VCALENDAR"""

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = ical_content.encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetcher = ICalFetcher(show_progress=False)
        url = "https://example.com/cache-test-calendar.ics"

        result1 = fetcher.fetch_from_url(url)
        result2 = fetcher.fetch_from_url(url)

        assert result1 == result2
        assert mock_urlopen.call_count == 1

    @patch("calends.fetcher.urlopen")
    def test_fetch_from_url_empty_response(self, mock_urlopen):
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"   "
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetcher = ICalFetcher(show_progress=False)
        with pytest.raises(ValueError, match="Empty response"):
            fetcher.fetch_from_url("https://example.com/empty-test.ics")

    @patch("calends.fetcher.urlopen")
    def test_fetch_from_url_invalid_ical(self, mock_urlopen):
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"This is not iCal content"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetcher = ICalFetcher(show_progress=False)
        with pytest.raises(ValueError, match="does not appear to be valid iCal format"):
            fetcher.fetch_from_url("https://example.com/invalid-test.ics")

    @patch("calends.fetcher.urlopen")
    def test_fetch_from_url_404_error(self, mock_urlopen):
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            "https://example.com/404-test.ics", 404, "Not Found", {}, None
        )

        fetcher = ICalFetcher(show_progress=False)
        with pytest.raises(Exception, match="not found \\(404\\)"):
            fetcher.fetch_from_url("https://example.com/404-test.ics")

    @patch("calends.fetcher.urlopen")
    def test_fetch_from_url_403_error(self, mock_urlopen):
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            "https://example.com/403-test.ics", 403, "Forbidden", {}, None
        )

        fetcher = ICalFetcher(show_progress=False)
        with pytest.raises(Exception, match="forbidden \\(403\\)"):
            fetcher.fetch_from_url("https://example.com/403-test.ics")

    @patch("calends.fetcher.urlopen")
    def test_fetch_from_url_401_error(self, mock_urlopen):
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            "https://example.com/401-test.ics", 401, "Unauthorized", {}, None
        )

        fetcher = ICalFetcher(show_progress=False)
        with pytest.raises(Exception, match="Authentication required \\(401\\)"):
            fetcher.fetch_from_url("https://example.com/401-test.ics")

    @patch("calends.fetcher.urlopen")
    def test_fetch_from_url_connection_error(self, mock_urlopen):
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Network unreachable")

        fetcher = ICalFetcher(show_progress=False)
        with pytest.raises(ConnectionError, match="Network error"):
            fetcher.fetch_from_url("https://example.com/connection-test.ics")


class TestFetch:
    def test_fetch_empty_source(self, capsys):
        fetcher = ICalFetcher(show_progress=False)
        result = fetcher.fetch("")

        assert result is None
        captured = capsys.readouterr()
        assert "Empty source" in captured.err

    def test_fetch_whitespace_source(self, capsys):
        fetcher = ICalFetcher(show_progress=False)
        result = fetcher.fetch("   ")

        assert result is None
        captured = capsys.readouterr()
        assert "Empty source" in captured.err

    def test_fetch_file_success(self, tmp_path):
        ical_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Test Event
END:VEVENT
END:VCALENDAR"""

        test_file = tmp_path / "calendar.ics"
        test_file.write_text(ical_content)

        fetcher = ICalFetcher(show_progress=False)
        result = fetcher.fetch(str(test_file))

        assert result == ical_content

    def test_fetch_file_not_found(self, capsys):
        fetcher = ICalFetcher(show_progress=False)
        result = fetcher.fetch("/nonexistent/path/calendar.ics")

        assert result is None
        captured = capsys.readouterr()
        assert "File not found" in captured.err

    def test_fetch_file_empty(self, tmp_path, capsys):
        test_file = tmp_path / "empty.ics"
        test_file.write_text("")

        fetcher = ICalFetcher(show_progress=False)
        result = fetcher.fetch(str(test_file))

        assert result is None
        captured = capsys.readouterr()
        assert "empty" in captured.err.lower()

    def test_fetch_file_invalid_ical(self, tmp_path, capsys):
        test_file = tmp_path / "invalid.ics"
        test_file.write_text("This is not iCal content")

        fetcher = ICalFetcher(show_progress=False)
        result = fetcher.fetch(str(test_file))

        assert result is None
        captured = capsys.readouterr()
        assert "does not appear to be valid iCal format" in captured.err

    def test_fetch_directory(self, tmp_path, capsys):
        fetcher = ICalFetcher(show_progress=False)
        result = fetcher.fetch(str(tmp_path))

        assert result is None
        captured = capsys.readouterr()
        assert "directory" in captured.err.lower()

    @patch("calends.fetcher.urlopen")
    def test_fetch_url_success(self, mock_urlopen):
        ical_content = """BEGIN:VCALENDAR
VERSION:2.0
END:VCALENDAR"""

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = ical_content.encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetcher = ICalFetcher(show_progress=False)
        result = fetcher.fetch("https://example.com/fetch-url-success-test.ics")

        assert result == ical_content

    @patch("calends.fetcher.urlopen")
    def test_fetch_url_http_protocol(self, mock_urlopen):
        ical_content = """BEGIN:VCALENDAR
VERSION:2.0
END:VCALENDAR"""

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = ical_content.encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetcher = ICalFetcher(show_progress=False)
        result = fetcher.fetch("http://example.com/calendar.ics")

        assert result == ical_content


class TestFetchMultiple:
    """Test parallel fetching of multiple sources."""

    @patch("calends.fetcher.urlopen")
    def test_fetch_multiple_urls(self, mock_urlopen):
        """Test fetching multiple URLs in parallel."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"BEGIN:VCALENDAR\nEND:VCALENDAR"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetcher = ICalFetcher(show_progress=False)
        sources = [
            "https://example.com/cal1-parallel.ics",
            "https://example.com/cal2-parallel.ics",
            "https://example.com/cal3-parallel.ics",
        ]

        results = fetcher.fetch_multiple(sources)

        assert len(results) == 3
        for source in sources:
            assert source in results
            assert results[source] is not None
            assert "BEGIN:VCALENDAR" in results[source]

    @patch("calends.fetcher.urlopen")
    def test_fetch_multiple_mixed_sources(self, mock_urlopen, tmp_path):
        """Test fetching mix of URLs and files."""
        # Create test file
        test_file = tmp_path / "test.ics"
        test_file.write_text("BEGIN:VCALENDAR\nEND:VCALENDAR")

        # Mock URL
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"BEGIN:VCALENDAR\nURL_CONTENT\nEND:VCALENDAR"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetcher = ICalFetcher(show_progress=False)
        sources = [
            str(test_file),
            "https://example.com/cal-mixed.ics",
        ]

        results = fetcher.fetch_multiple(sources)

        assert len(results) == 2
        assert results[str(test_file)] is not None
        assert "BEGIN:VCALENDAR" in results[str(test_file)]
        assert results["https://example.com/cal-mixed.ics"] is not None
        assert "URL_CONTENT" in results["https://example.com/cal-mixed.ics"]

    @patch("calends.fetcher.urlopen")
    def test_fetch_multiple_with_cache(self, mock_urlopen):
        """Test that fetch_multiple uses cache."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"BEGIN:VCALENDAR\nEND:VCALENDAR"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetcher = ICalFetcher(show_progress=False)
        url = "https://example.com/cached-parallel-test.ics"

        # First fetch - should call urlopen
        fetcher.fetch_from_url(url)
        call_count_1 = mock_urlopen.call_count

        # Second fetch via fetch_multiple - should use cache
        results = fetcher.fetch_multiple([url])

        assert results[url] is not None
        assert mock_urlopen.call_count == call_count_1  # No new call

    @patch("calends.fetcher.urlopen")
    def test_fetch_multiple_single_url(self, mock_urlopen):
        """Test fetch_multiple with single URL falls back to sequential."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"BEGIN:VCALENDAR\nEND:VCALENDAR"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetcher = ICalFetcher(show_progress=False)
        sources = ["https://example.com/single-parallel.ics"]

        results = fetcher.fetch_multiple(sources)

        assert len(results) == 1
        assert results[sources[0]] is not None

    def test_fetch_multiple_files_only(self, tmp_path):
        """Test fetch_multiple with only files (no parallel needed)."""
        file1 = tmp_path / "test1.ics"
        file2 = tmp_path / "test2.ics"
        file1.write_text("BEGIN:VCALENDAR\nFILE1\nEND:VCALENDAR")
        file2.write_text("BEGIN:VCALENDAR\nFILE2\nEND:VCALENDAR")

        fetcher = ICalFetcher(show_progress=False)
        sources = [str(file1), str(file2)]

        results = fetcher.fetch_multiple(sources)

        assert len(results) == 2
        assert "FILE1" in results[str(file1)]
        assert "FILE2" in results[str(file2)]

    @patch("calends.fetcher.urlopen")
    def test_fetch_multiple_with_failures(self, mock_urlopen):
        """Test fetch_multiple handles partial failures."""

        def side_effect(*args, **kwargs):
            url = args[0].full_url if hasattr(args[0], "full_url") else str(args[0])
            if "fail" in url:
                from urllib.error import HTTPError

                raise HTTPError(url, 404, "Not Found", {}, None)
            mock_response = Mock()
            mock_response.status = 200
            mock_response.read.return_value = b"BEGIN:VCALENDAR\nEND:VCALENDAR"
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            return mock_response

        mock_urlopen.side_effect = side_effect

        fetcher = ICalFetcher(show_progress=False)
        sources = [
            "https://example.com/success-parallel.ics",
            "https://example.com/fail-parallel.ics",
        ]

        results = fetcher.fetch_multiple(sources)

        assert len(results) == 2
        assert results["https://example.com/success-parallel.ics"] is not None
        assert results["https://example.com/fail-parallel.ics"] is None

    def test_fetch_multiple_empty_list(self):
        """Test fetch_multiple with empty list."""
        fetcher = ICalFetcher(show_progress=False)
        results = fetcher.fetch_multiple([])

        assert len(results) == 0
        assert results == {}
