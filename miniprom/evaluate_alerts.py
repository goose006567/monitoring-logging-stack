"""Evaluate the exported alert rules against the mock exporters (PromQL subset).

Supports the exact rule shapes used in prometheus/alert_rules.yml:
  metric > N        metric < N
  (1 - a / b) > N     rate(a[5m]) / rate(b[5m]) > N
Multiple evaluation ticks simulate the `for:` pending/duration logic.
"""
import re
import sys
import time
import yaml
import urllib.request
from scraper import fetch

RULES_PATH = "prometheus/alert_rules.yml"
TICKS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
TICK_GAP = 2

SINGLE = re.compile(r"^(\w+)\s*(>|<)\s*([\d.]+)$")
RATIO = re.compile(r"^\(\s*1\s*-\s*(\w+)\s*/\s*(\w+)\s*\)\s*(>|<)\s*([\d.]+)$")
RATE_RATIO = re.compile(r"^rate\((\w+)\[\d+m\]\)\s*/\s*rate\((\w+)\[\d+m\]\)\s*(>|<)\s*([\d.]+)$")


def latest(series, name):
    values = series.get(name)
    if not values:
        return None
    # average across label sets for the demo
    return sum(values.values()) / len(values)


def rate_ratio(job, num_name, den_name, tries=4):
    """Sample num/den counter deltas from the same 1s windows; avg non-zero."""
    ratios = []
    for _ in range(tries):
        before = fetch(job)
        time.sleep(1)
        after = fetch(job)
        dn = latest(after, num_name) - latest(before, num_name)
        dd = latest(after, den_name) - latest(before, den_name)
        if dd:
            ratios.append(dn / dd)
    return (sum(ratios) / len(ratios)) if ratios else 0.0


def evaluate(expr, scraped):
    m = SINGLE.match(expr)
    if m:
        name, op, num = m.groups()
        v = latest(scraped.get("node", {}), name) or latest(scraped.get("app", {}), name)
        if v is None:
            return None, "no data"
        hit = v < float(num) if op == "<" else v > float(num)
        return v, ("TRIPPED" if hit else "ok")
    m = RATIO.match(expr)
    if m:
        a, b, op, num = m.groups()
        va, vb = latest(scraped["node"], a), latest(scraped["node"], b)
        if va is None or vb is None:
            return None, "no data"
        r = 1 - va / vb if vb else None
        return r, ("TRIPPED" if r and (r > float(num) if op == ">" else r < float(num)) else "ok")
    m = RATE_RATIO.match(expr)
    if m:
        a, b, op, num = m.groups()
        r = rate_ratio("app", a, b)
        return r, ("TRIPPED" if r and (r > float(num) if op == ">" else r < float(num)) else "ok")
    return None, "unsupported expr"


def main():
    rules = yaml.safe_load(open(RULES_PATH))
    streaks = {}
    for tick in range(1, TICKS + 1):
        print(f"\n== evaluation tick {tick}/{TICKS} ==")
        scraped = {j: fetch(j) for j in ("node", "app")}
        for group in rules["groups"]:
            for r in group["rules"]:
                value, status = evaluate(r["expr"], scraped)
                tag = r["alert"]
                if status == "TRIPPED":
                    streaks[tag] = streaks.get(tag, 0) + 1
                else:
                    if status == "ok":
                        streaks[tag] = 0
                    print(f"  {tag:<22} value={value!s:<12} -> OK")
                    continue
                state = "FIRING" if streaks[tag] >= 2 else "PENDING"
                print(f"  {tag:<22} value={value!s:<12} -> {state} (severity={r['labels']['severity']})")
        time.sleep(TICK_GAP)


if __name__ == "__main__":
    main()
