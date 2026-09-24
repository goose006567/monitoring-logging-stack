"""Mock application exporter: request rate, latency, error rate on :9101."""
import os
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from format import counter, gauge, body

HOST, PORT = "127.0.0.1", 9101
HIGH_ERRORS = os.environ.get("HIGH_ERRORS") == "1"

LOCK = threading.Lock()
STATE = {"requests": 100_000, "errors": 250, "latency": 0.045}


def drift():
    with LOCK:
        s = STATE
        req_delta = random.randint(40, 120)
        s["requests"] += req_delta
        err_rate = 0.002 if not HIGH_ERRORS else 0.20
        s["errors"] += int(req_delta * err_rate)
        s["latency"] = max(0.01, min(2.0, s["latency"] + random.uniform(-0.005, 0.005)))
    threading.Timer(2.0, drift).start()


def collect():
    with LOCK:
        s = STATE
        return body([
            {"name": "app_http_requests_total", "type": "counter",
             "line": counter("app_http_requests_total", s["requests"])},
            {"name": "app_http_errors_total", "type": "counter",
             "line": counter("app_http_errors_total", s["errors"])},
            {"name": "app_request_latency_seconds", "type": "gauge",
             "line": gauge("app_request_latency_seconds", s["latency"])},
        ])


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_error(404)
            return
        data = collect().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    drift()
    print(f"[mock-app] prometheus metrics on {HOST}:{PORT}/metrics (HIGH_ERRORS={HIGH_ERRORS})")
    HTTPServer((HOST, PORT), Handler).serve_forever()
