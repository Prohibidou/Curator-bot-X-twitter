import base64
import json
import urllib.request


def select_target(targets, prefer):
    pages = [t for t in targets if t.get("type") == "page"]
    for t in pages:
        if prefer in (t.get("url") or ""):
            return t
    if pages:
        return pages[0]
    raise RuntimeError("no CDP page target found")


def discover_ws_url(port, prefer="x.com", opener=None):
    opener = opener or (lambda url: urllib.request.urlopen(url, timeout=5))
    with opener(f"http://127.0.0.1:{port}/json") as r:
        targets = json.loads(r.read().decode("utf-8"))
    t = select_target(targets, prefer)
    ws_url = t.get("webSocketDebuggerUrl")
    if not ws_url:
        raise RuntimeError("selected target has no webSocketDebuggerUrl (already has a devtools client?)")
    ws_url = ws_url.replace("localhost", "127.0.0.1")
    return ws_url, t.get("url", "")


class CDP:
    def __init__(self, ws):
        self._ws = ws
        self._id = 0

    def send(self, method, params=None):
        self._id += 1
        self._ws.send(json.dumps({"id": self._id, "method": method,
                                  "params": params or {}}))
        while True:
            msg = json.loads(self._ws.recv())
            if msg.get("id") == self._id:
                if "error" in msg:
                    raise RuntimeError(f"{method} failed: {msg['error']}")
                return msg.get("result", {})
            # otherwise it's an event or another id: keep reading

    def navigate(self, url):
        self.send("Page.navigate", {"url": url})

    def screenshot(self) -> bytes:
        res = self.send("Page.captureScreenshot", {"format": "png"})
        return base64.b64decode(res["data"])

    def move(self, x, y):
        self.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})

    def click(self, x, y):
        self.move(x, y)
        for t in ("mousePressed", "mouseReleased"):
            self.send("Input.dispatchMouseEvent",
                      {"type": t, "x": x, "y": y, "button": "left", "clickCount": 1,
                       "buttons": 1})

    def scroll(self, x, y, dy):
        self.send("Input.dispatchMouseEvent",
                  {"type": "mouseWheel", "x": x, "y": y, "deltaX": 0, "deltaY": dy})

    def type_text(self, s):
        self.send("Input.insertText", {"text": s})

    def press(self, key):
        for t in ("keyDown", "keyUp"):
            self.send("Input.dispatchKeyEvent", {"type": t, "key": key})

    def current_url(self) -> str:
        res = self.send("Page.getNavigationHistory")
        entries = res.get("entries", [])
        if not entries:
            return ""
        idx = res.get("currentIndex", len(entries) - 1)
        return entries[idx].get("url", "")

    def close(self):
        try:
            self._ws.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def connect(port, cfg=None, prefer="x.com", ws_factory=None):
    ws_url, _ = discover_ws_url(port, prefer)
    if ws_factory is None:
        import websocket
        ws_factory = lambda u: websocket.create_connection(u, timeout=30)
    cdp = CDP(ws_factory(ws_url))
    cdp.send("Page.enable")
    if cfg is not None:
        cdp.send("Emulation.setDeviceMetricsOverride",
                 {"width": cfg.window_width, "height": cfg.window_height,
                  "deviceScaleFactor": 1, "mobile": False})
    return cdp
