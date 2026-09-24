"""Mock node_exporter: system metrics (CPU, memory, disk, network) on :9100."""
import random
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from format import counter, gauge, body

HOST, PORT = "127.0.0.1", 9100
LOW_MEMORY = os.environ.get("LOW_MEMORY") == "1"

LOCK = threading.Lock()
STATE = {
    "cpu_v": 20.0,     # keeps changing
    "mem_avail": 300_000_000 if LOW_MEMORY else 4_000_000_000,
    "disk_avail": 120_000_000_000,
    "net_rx": 1_000_000,
    "net_tx": 500_000,
}


def drift():
    with LOCK:
        s = STATE
        s["cpu_v"] = max(2.0, min(98.0, s["cpu_v"] + random.uniform(-3, 3)))
        s["net_rx"] += random.uniform(50_000, 200_000)
        s["net_tx"] += random.uniform(20_000, 90_000)
    threading.Timer(2.0, drift).start()


def collect():
    with LOCK:
        s = STATE
        return body([
            {"name": "node_cpu_system_seconds_total", "type": "counter",
             "line": counter("node_cpu_system_seconds_total", 12_345, {"cpu": "0"})},
            {"name": "node_cpu_usage_percent", "type": "gauge",
             "line": gauge("node_cpu_usage_percent", s["cpu_v"])},
            {"name": "node_memory_MemAvailable_bytes", "type": "gauge",
             "line": gauge("node_memory_MemAvailable_bytes", s["mem_avail"])},
            {"name": "node_memory_MemTotal_bytes", "type": "gauge",
             "line": gauge("node_memory_MemTotal_bytes", 8_000_000_000)},
            {"name": "node_filesystem_avail_bytes", "type": "gauge",
             "line": gauge("node_filesystem_avail_bytes", s["disk_avail"], {"mountpoint": "/"})},
            {"name": "node_filesystem_size_bytes", "type": "gauge",
             "line": gauge("node_filesystem_size_bytes", 250_000_000_000, {"mountpoint": "/"})},
            {"name": "node_network_receive_bytes_total", "type": "counter",
             "line": counter("node_network_receive_bytes_total", s["net_rx"], {"device": "eth0"})},
            {"name": "node_network_transmit_bytes_total", "type": "counter",
             "line": counter("node_network_transmit_bytes_total", s["net_tx"], {"device": "eth0"})},
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
    print(f"[mock-node] prometheus metrics on {HOST}:{PORT}/metrics")
    HTTPServer((HOST, PORT), Handler).serve_forever()
