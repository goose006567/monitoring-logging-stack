"""Helpers for emitting Prometheus text exposition format (4.3 spec subset)."""


def fmt_metric(name, value, labels=None):
    if labels:
        lab = ",".join(f'{k}="{v}"' for k, v in labels.items())
        return f"{name}{{{lab}}} {value}"
    return f"{name} {value}"


def counter(name, value, labels=None):
    return fmt_metric(name, round(value, 4), labels)


def gauge(name, value, labels=None):
    return fmt_metric(name, round(value, 4), labels)


def body(series):
    lines = []
    for m in series:
        lines.append(f"# HELP {m['name']} simulated metric for {m['name']}")
        lines.append(f"# TYPE {m['name']} {m['type']}")
        lines.append(m["line"])
    return "\n".join(lines) + "\n"
