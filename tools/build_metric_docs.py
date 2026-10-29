"""Fill the GENERATED blocks of the metric guide from the field dictionary and the lab events.

Each doc under docs/ holds blocks delimited by

    <!-- BEGIN GENERATED: name -->
    ...replaced on every run...
    <!-- END GENERATED: name -->

Blocks written here:
  contention            docs/NSX-Contention-Metrics.md      category Contention, by object type
  consumption           docs/NSX-Consumption-Metrics.md     category Consumption, by object type
  capacity              docs/NSX-Capacity-Metrics.md        disk space + capacity denominators
  availability-fields   docs/NSX-Availability-Metrics-and-Events.md  category Availability
  availability-events   docs/NSX-Availability-Metrics-and-Events.md  availability events by node type
  resource-events       docs/NSX-Availability-Metrics-and-Events.md  resource-threshold events by node type

Run tools/build_metric_dictionary.py first. Stdlib only.

Usage: python -I tools/build_metric_docs.py [run_dir]
"""
import csv
import json
import re
import sys
import collections
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
CSV_PATH = DOCS / "data" / "nsx-metric-fields.csv"

NODE_TYPE_GROUPS = [
    ("NSX Manager", ["nsx_manager"]),
    ("NSX Global Manager", ["nsx_global_manager"]),
    ("NSX Edge and VNA (incl. public cloud gateway)", ["nsx_edge", "nsx_public_cloud_gateway"]),
    ("ESXi and KVM host transport nodes", ["nsx_esx", "nsx_kvm"]),
    ("DPU transport nodes", ["nsx_dpu"]),
    ("Bare-metal transport nodes", ["nsx_bms"]),
]

# Event families whose trigger is a resource level crossing a threshold.
RESOURCE_EVENT = re.compile(r"usage|cpu|memory|mem_|disk|limit|capacity|exhaust|mempool|throughput|buffer|cache|route|prefix|pool|occupancy|utili|size|quota|threshold|percent|hit_rate|queue|heap|nic_|ring|latency|arp_table|_count|bfd_profile|overlap", re.I)
AVAILABILITY_EVENT = re.compile(r"down|unreachable|lost|disconnect|unavailable|not running|stopped|status|fail|degraded|sync|heartbeat|deadlock|hang|unhealthy|connectivity|connection|timeout|unknown|overloaded|split.brain|cannot|can not|not responding|reachab|failover|active instance|redundancy|deactivat|dead|restart|no northbound|not configured|miss", re.I)


def esc(text):
    return (text or "").replace("|", "/").replace("\n", " ").strip()


def short(text, n):
    text = esc(text)
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def load_rows():
    with open(CSV_PATH, encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r["field"]]


def field_table(rows):
    """One row per (object type, field): endpoint count, lab status, formula, description."""
    merged = collections.OrderedDict()
    for r in rows:
        key = r["field"]
        m = merged.setdefault(key, {"type": r["type"], "endpoints": set(), "lab": False,
                                    "in_spec": True, "formula": r["formula"], "desc": ""})
        m["endpoints"].add(r["endpoint"])
        m["lab"] = m["lab"] or r["lab_observed"] == "yes"
        m["in_spec"] = m["in_spec"] and r["in_spec"] == "yes"
        if not m["desc"] and r["description"] and r["in_spec"] == "yes":
            m["desc"] = r["description"]
    lines = ["| Field | Type | Endpoints | Lab | Formula | Description |",
             "|---|---|---:|:-:|---|---|"]
    for field, m in sorted(merged.items(), key=lambda kv: (-len(kv[1]["endpoints"]), kv[0])):
        name = f"`{esc(field)}`" + ("" if m["in_spec"] else " †")
        lab = "✓" if m["lab"] else "–"
        desc = short(m["desc"], 140) if m["desc"] else "–"
        lines.append(f"| {name} | {m['type']} | {len(m['endpoints'])} | {lab} | {esc(m['formula'])} | {desc} |")
    return "\n".join(lines)


def by_object_type(rows, categories):
    selected = [r for r in rows if r["category"] in categories]
    groups = collections.defaultdict(list)
    for r in selected:
        groups[r["object_type"]].append(r)
    out = []
    for name, grp in sorted(groups.items(), key=lambda kv: -len({r["field"] for r in kv[1]})):
        fields = {r["field"] for r in grp}
        endpoints = {r["endpoint"] for r in grp}
        out.append(f"<details>\n<summary><b>{esc(name)}</b> — {len(fields)} fields, {len(endpoints)} endpoints</summary>\n\n"
                   f"{field_table(grp)}\n\n</details>\n")
    return "\n".join(out)


def load_events(run):
    events = {}
    for line in open(run / "raw" / "manager.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if r["template"] in ("/events", "/events/{event-id}") and r["status"] == 200:
            body = r["body"]
            for e in body.get("results", [body]) if isinstance(body, dict) else body:
                events.setdefault(e.get("event_type"), e)
    return list(events.values())


def event_table(events):
    lines = ["| Feature | Event type | Severity | Threshold | Fixed | Trigger (from the event definition) |",
             "|---|---|---|---:|:-:|---|"]
    for e in sorted(events, key=lambda e: (e.get("feature_name") or "", e.get("event_type") or "")):
        thr = e.get("threshold") or 0
        thr_txt = str(thr) if thr else "–"
        fixed = "–" if not thr else ("✓" if e.get("is_threshold_fixed") else "tunable")
        trigger = e.get("description") or e.get("summary") or ""
        lines.append(f"| {esc(e.get('feature_name'))} | `{esc(e.get('event_type'))}` | {e.get('severity')} | "
                     f"{thr_txt} | {fixed} | {short(trigger, 170)} |")
    return "\n".join(lines)


def events_by_node_type(events, pattern):
    """Events whose text matches pattern, grouped by the node types they apply to."""
    out = []
    for title, types in NODE_TYPE_GROUPS:
        picked = [e for e in events
                  if set(e.get("node_types") or []) & set(types)
                  and not e.get("is_disabled")
                  and pattern(e)]
        if not picked:
            continue
        out.append(f"<details>\n<summary><b>{title}</b> — {len(picked)} event types</summary>\n\n"
                   f"{event_table(picked)}\n\n</details>\n")
    return "\n".join(out)


def is_resource(e):
    text = f"{e.get('event_type')} {e.get('summary')}"
    return bool(RESOURCE_EVENT.search(text))


def is_availability(e):
    if is_resource(e):
        return False
    text = f"{e.get('event_type')} {e.get('summary')} {e.get('description')}"
    return bool(AVAILABILITY_EVENT.search(text))


def replace_block(text, name, body):
    pattern = re.compile(
        rf"(<!-- BEGIN GENERATED: {re.escape(name)} -->\n).*?(<!-- END GENERATED: {re.escape(name)} -->)",
        re.S)
    if not pattern.search(text):
        raise SystemExit(f"marker not found: {name}")
    return pattern.sub(lambda m: m.group(1) + body + "\n" + m.group(2), text, count=1)


def main():
    run = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "output" / "nsxman1-run1"
    rows = load_rows()
    events = load_events(run)
    blocks = {
        "contention": ("NSX-Contention-Metrics.md", by_object_type(rows, {"Contention"})),
        "consumption": ("NSX-Consumption-Metrics.md", by_object_type(rows, {"Consumption"})),
        "capacity": ("NSX-Capacity-Metrics.md",
                     by_object_type(rows, {"Disk space (capacity)", "Capacity and threshold (denominator)"})),
        "availability-fields": ("NSX-Availability-Metrics-and-Events.md", by_object_type(rows, {"Availability"})),
        "availability-events": ("NSX-Availability-Metrics-and-Events.md",
                                events_by_node_type(events, is_availability)),
        "resource-events": ("NSX-Availability-Metrics-and-Events.md",
                            events_by_node_type(events, is_resource)),
    }
    for name, (doc, body) in blocks.items():
        path = DOCS / doc
        path.write_text(replace_block(path.read_text(encoding="utf-8"), name, body), encoding="utf-8")
        print(f"{name:22s} -> docs/{doc} ({len(body.splitlines())} lines)")
    print("events total:", len(events),
          "availability:", sum(is_availability(e) for e in events),
          "resource:", sum(is_resource(e) for e in events))


if __name__ == "__main__":
    main()
