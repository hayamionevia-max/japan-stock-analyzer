from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
import json
import os

ALLOWED_HOSTS = {
    "query1.finance.yahoo.com",
    "query2.finance.yahoo.com",
}

ALLOWED_PATHS = (
    "/v8/finance/chart/",
    "/v7/finance/options/",
)


class PreviewHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/yahoo":
            return self.handle_yahoo_proxy(parsed)
        if parsed.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/yahoo":
            self.send_response(405)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            return
        if parsed.path == "/":
            self.path = "/index.html"
        return super().do_HEAD()

    def handle_yahoo_proxy(self, parsed):
        qs = parse_qs(parsed.query)
        target = qs.get("url", [""])[0]
        if not target:
            return self.send_json(400, {"error": "Missing url parameter"})

        try:
            target_url = urlparse(target)
            if target_url.hostname not in ALLOWED_HOSTS:
                return self.send_json(400, {"error": "Target host not allowed"})
            if not any(target_url.path.startswith(prefix) for prefix in ALLOWED_PATHS):
                return self.send_json(400, {"error": "Target path not allowed"})

            req = Request(
                target,
                headers={
                    "Accept": "application/json,text/plain,*/*",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                },
            )
            with urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                status = getattr(resp, "status", 200)
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    return self.send_json(502, {
                        "error": "Upstream response was not valid JSON",
                        "body": body[:500],
                    })
                return self.send_json(status, data)
        except Exception as exc:
            return self.send_json(500, {"error": str(exc)})

    def send_json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = ThreadingHTTPServer(("127.0.0.1", 8002), PreviewHandler)
    print("Japan Stock Analyzer preview server running on http://127.0.0.1:8002")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
