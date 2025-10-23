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
        fetcher = ICalFetcher()
        assert fetcher.cache is not None

    def test_init_custom_expiration(self):
        fetcher = ICalFetcher(cache_expiration=300)
        assert fetcher.cache.expiration == 300


class TestFetchFromUrl:
    def test_invalid_url_empty(self):
        fetcher = ICalFetcher()
        with pytest.raises(ValueError, match="Invalid URL"):
            fetcher.fetch_from_url("")

    def test_invalid_url_no_protocol(self):
        fetcher = ICalFetcher()
        with pytest.raises(ValueError, match="Invalid URL"):
            fetcher.fetch_from_url("example.com/calendar.ics")

    def test_invalid_url_wrong_protocol(self):
        fetcher = ICalFetcher()
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

        fetcher = ICalFetcher()
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

        fetcher = ICalFetcher()
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

        fetcher = ICalFetcher()
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

        fetcher = ICalFetcher()
        with pytest.raises(ValueError, match="does not appear to be valid iCal format"):
            fetcher.fetch_from_url("https://example.com/invalid-test.ics")

    @patch("calends.fetcher.urlopen")
    def test_fetch_from_url_404_error(self, mock_urlopen):
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            "https://example.com/404-test.ics", 404, "Not Found", {}, None
        )

        fetcher = ICalFetcher()
        with pytest.raises(Exception, match="not found \\(404\\)"):
            fetcher.fetch_from_url("https://example.com/404-test.ics")

    @patch("calends.fetcher.urlopen")
    def test_fetch_from_url_403_error(self, mock_urlopen):
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            "https://example.com/403-test.ics", 403, "Forbidden", {}, None
        )

        fetcher = ICalFetcher()
        with pytest.raises(Exception, match="forbidden \\(403\\)"):
            fetcher.fetch_from_url("https://example.com/403-test.ics")

    @patch("calends.fetcher.urlopen")
    def test_fetch_from_url_401_error(self, mock_urlopen):
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            "https://example.com/401-test.ics", 401, "Unauthorized", {}, None
        )

        fetcher = ICalFetcher()
        with pytest.raises(Exception, match="Authentication required \\(401\\)"):
            fetcher.fetch_from_url("https://example.com/401-test.ics")

    @patch("calends.fetcher.urlopen")
    def test_fetch_from_url_connection_error(self, mock_urlopen):
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Network unreachable")

        fetcher = ICalFetcher()
        with pytest.raises(ConnectionError, match="Network error"):
            fetcher.fetch_from_url("https://example.com/connection-test.ics")


class TestFetch:
    def test_fetch_empty_source(self, capsys):
        fetcher = ICalFetcher()
        result = fetcher.fetch("")

        assert result is None
        captured = capsys.readouterr()
        assert "Empty source" in captured.err

    def test_fetch_whitespace_source(self, capsys):
        fetcher = ICalFetcher()
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

        fetcher = ICalFetcher()
        result = fetcher.fetch(str(test_file))

        assert result == ical_content

    def test_fetch_file_not_found(self, capsys):
        fetcher = ICalFetcher()
        result = fetcher.fetch("/nonexistent/path/calendar.ics")

        assert result is None
        captured = capsys.readouterr()
        assert "File not found" in captured.err

    def test_fetch_file_empty(self, tmp_path, capsys):
        test_file = tmp_path / "empty.ics"
        test_file.write_text("")

        fetcher = ICalFetcher()
        result = fetcher.fetch(str(test_file))

        assert result is None
        captured = capsys.readouterr()
        assert "empty" in captured.err.lower()

    def test_fetch_file_invalid_ical(self, tmp_path, capsys):
        test_file = tmp_path / "invalid.ics"
        test_file.write_text("This is not iCal content")

        fetcher = ICalFetcher()
        result = fetcher.fetch(str(test_file))

        assert result is None
        captured = capsys.readouterr()
        assert "does not appear to be valid iCal format" in captured.err

    def test_fetch_directory(self, tmp_path, capsys):
        fetcher = ICalFetcher()
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

        fetcher = ICalFetcher()
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

        fetcher = ICalFetcher()
        result = fetcher.fetch("http://example.com/calendar.ics")

        assert result == ical_content
