from curator.config import Config
from curator.browser import Browser


def test_search_url_top_tab_and_encoding():
    b = Browser(Config.default())
    url = b.search_url("mars rover")
    assert url.startswith("https://x.com/search?")
    assert "q=mars%20rover" in url or "q=mars+rover" in url
    assert "f=top" in url
