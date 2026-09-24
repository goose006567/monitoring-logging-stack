# Infrastructure Monitoring & Logging Stack

Prometheus · Grafana · Loki · Alertmanager — built and validated fully offline
against mock exporters that emit the real Prometheus text exposition format.

## Components

| Directory      | What it is                                                     |
| -------------- | -------------------------------------------------------------- |
| `exporters/`   | Mock exporters emitting real Prometheus-style metrics over HTTP |
| `prometheus/`  | `prometheus.yml` + `alert_rules.yml` (CPU, mem, disk, errors)  |
| `grafana/`     | Dashboard JSON with PromQL panels                              |
| `alertmanager/`| Slack routing config                                           |
| `loki/`        | Loki + promtail configs for centralized logging                |
| `miniprom/`    | Mini scraper + rule evaluator (PromQL subset) that proves it   |

## Run the demo (0 MB, no Docker)

```bash
# Terminal 1 - healthy stack
.venv/bin/python exporters/mock_node.py     # CPU/mem/disk/net on :9100
.venv/bin/python exporters/mock_app.py      # requests/errors/latency on :9101

# Terminal 2 - simulate pressure (forces LowMemory + HighErrorRate)
LOW_MEMORY=1  .venv/bin/python exporters/mock_node.py
HIGH_ERRORS=1 .venv/bin/python exporters/mock_app.py

# Terminal 3 - scrape the real Prometheus text format
.venv/bin/python miniprom/scraper.py

# Terminal 4 - evaluate the exported alert rules (PENDING -> FIRING)
.venv/bin/python miniprom/evaluate_alerts.py 5
```

Expected output: healthy stack shows **all rules OK**; with pressure,
`LowMemory` (warning) and `HighErrorRate` (critical) go PENDING then FIRING.

Setup: `python3.12 -m venv .venv && .venv/bin/pip install PyYAML`

## Deploy the real stack (needs ~750 MB + Docker)

`docker compose up` pulls prometheus, node-exporter, alertmanager, grafana,
loki, promtail. The mock exporters are replaced with the real images; all
configs above mount in unchanged.

## Why two gateways for alerts?

`alert_rules.yml` is what **real Prometheus** executes (full PromQL: `rate()`,
`for:`, `for: 5m` pending logic). `miniprom/` implements the same expressions
for a subset so the pipeline runs on a machine with no binaries — it is the
offline proof that the rules are correct.
