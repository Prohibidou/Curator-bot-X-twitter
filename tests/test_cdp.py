import json
import pytest
from curator.cdp import select_target, CDP, discover_ws_url


def test_select_target_prefers_matching_url():
    targets = [{"type": "page", "url": "https://google.com", "webSocketDebuggerUrl": "ws://a"},
               {"type": "page", "url": "https://x.com/home", "webSocketDebuggerUrl": "ws://b"},
               {"type": "background_page", "url": "https://x.com/x", "webSocketDebuggerUrl": "ws://c"}]
    assert select_target(targets, "x.com")["webSocketDebuggerUrl"] == "ws://b"


def test_select_target_falls_back_to_first_page():
    targets = [{"type": "page", "url": "https://google.com", "webSocketDebuggerUrl": "ws://a"}]
    assert select_target(targets, "x.com")["webSocketDebuggerUrl"] == "ws://a"


def test_select_target_raises_when_no_page():
    with pytest.raises(RuntimeError):
        select_target([{"type": "background_page", "url": "x"}], "x.com")


class FakeWS:
    """Echoes a result for each command id; can queue events to skip."""
    def __init__(self, events=None):
        self.sent = []
        self._events = list(events or [])
        self._pending = None

    def send(self, raw):
        msg = json.loads(raw)
        self.sent.append(msg)
        self._pending = msg["id"]

    def recv(self):
        if self._events:
            return json.dumps(self._events.pop(0))  # an event (no id)
        return json.dumps({"id": self._pending, "result": {"ok": self._pending}})


def test_send_matches_id_and_skips_events():
    ws = FakeWS(events=[{"method": "Page.frameNavigated", "params": {}}])
    cdp = CDP(ws)
    result = cdp.send("Page.enable")
    assert result == {"ok": 1}
    assert ws.sent[0]["method"] == "Page.enable"
    assert ws.sent[0]["id"] == 1


def test_click_dispatches_press_and_release():
    ws = FakeWS()
    cdp = CDP(ws)
    cdp.click(10, 20)
    types = [m["params"].get("type") for m in ws.sent if m["method"] == "Input.dispatchMouseEvent"]
    assert types == ["mouseMoved", "mousePressed", "mouseReleased"]
    assert ws.sent[-1]["params"]["x"] == 10 and ws.sent[-1]["params"]["y"] == 20


class FakeHTTPResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def read(self):
        return self._payload


def test_discover_ws_url_uses_ipv4_literal_and_normalizes_localhost():
    targets = [{"type": "page", "url": "https://x.com/home",
                "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/AB"}]
    payload = json.dumps(targets).encode("utf-8")
    requested = {}

    def fake_opener(url):
        requested["url"] = url
        return FakeHTTPResponse(payload)

    ws_url, page_url = discover_ws_url(9222, prefer="x.com", opener=fake_opener)
    assert requested["url"].startswith("http://127.0.0.1:")
    assert "127.0.0.1" in ws_url
    assert "localhost" not in ws_url
