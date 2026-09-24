"""Minimal Prometheus text-format scraper (parses 4.3 exposition format)."""
import urllib.request

TARGETS = {"node": ("127.0.0.1", 9100), "app": ("127.0.0.1", 9101)}


def fetch(job, timeout=5):
    host, port = TARGETS[job]
    with urllib.request.urlopen(f"http://{host}:{port}/metrics", timeout=timeout) as resp:
        return parse(resp.read().decode())


def parse(text):
    """Return {metric_name: {canonical_labels: value}} for gauges/counters."""
    series = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "{" in line:
            name, _, rest = line.partition("{")
            label_part, _, value = rest.partition("} ")
            labels = {
                k: v[1:-1] if v.startswith('"') else v
                for k, v in (p.split("=", 1) for p in label_part.split(",") if "=" in p)
            }
        else:
            name, _, value = line.partition(" ")
            labels = {}
        name = name.strip()
        value = value.strip()
        key = name + "_" + "&".join(f"{k}={v}" for k, v in sorted(labels.items()))
        series.setdefault(name, {})[key] = float(value)
    return series


if __name__ == "__main__":
    for job in TARGETS:
        print(f"== {job} ==")
        for name, series in fetch(job).items():
            for labels, value in series.items():
                print(f"  {name} {{{labels}}} = {value}")
