"""Build the NSX metric field dictionary (docs/data/nsx-metric-fields.csv).

Joins three sources, all produced by tools/nsx_crawl.py:
  * the metric endpoint catalog   docs/nsx-metric-endpoint-catalog.md
  * the OpenAPI (Swagger 2.0) specs  <run>/spec/{manager,policy}.json
  * the lab responses                <run>/raw/{manager,policy}.jsonl

One CSV row per endpoint x leaf field. Columns:
  api, object_type, endpoint, field, type, category, formula, description,
  in_catalog, lab_result, in_spec, lab_observed

Categories are a keyword heuristic (see classify) and must be reviewed by a person.
Lab example values are deliberately not written: the lab inventory is git-ignored.

Usage:  python -I tools/build_metric_dictionary.py [run_dir]
        run_dir defaults to output/nsxman1-run1
"""
import csv
import json
import os
import re
import sys
import collections
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CATALOG = REPO / "docs" / "nsx-metric-endpoint-catalog.md"
OUT = REPO / "docs" / "data" / "nsx-metric-fields.csv"
MAX_DEPTH = 6
MAX_FIELDS = 4000
CATALOG_GAP = re.compile(r"statistics/|/stats$|/xstats$|/monitor$|/debug$|/lldp/interfaces$")


def catalog_endpoints(run):
    """Catalog endpoints, plus spec GETs that the catalog's keyword list missed."""
    rows, api = [], None
    for line in open(CATALOG, encoding="utf-8"):
        if line.startswith("## Manager API"):
            api = "manager"
        elif line.startswith("## Policy API"):
            api = "policy"
        m = re.match(r"^\| `([^`]+)` \| (.*?) \| (.*?) \|\s*$", line)
        if m and api and "?format=csv" not in m.group(1):
            rows.append((api, m.group(1), m.group(3), True))
    in_catalog = {(r[0], r[1]) for r in rows}
    for api in ("manager", "policy"):
        spec, _ = load_spec(run, api)
        for path, item in spec["paths"].items():
            if "?" in path or (api, path) in in_catalog or "get" not in item:
                continue
            if item["get"].get("deprecated") or not CATALOG_GAP.search(path):
                continue
            rows.append((api, path, "not in catalog", False))
    return rows


def load_spec(run, api):
    # Swagger 2.0: schemas live under "definitions"
    spec = json.load(open(run / "spec" / f"{api}.json", encoding="utf-8"))
    return spec, spec.get("definitions", {})


def resolve(s, defs):
    depth = 0
    while isinstance(s, dict) and "$ref" in s and depth < 10:
        s = defs.get(s["$ref"].split("/")[-1], {})
        depth += 1
    return s if isinstance(s, dict) else {}


def response_schema(spec, ep):
    item = spec["paths"].get(ep)
    if not item or "get" not in item or item["get"].get("deprecated"):
        return None
    resp = item["get"].get("responses", {}).get("200", {})
    if "$ref" in resp:
        return None
    if "schema" in resp:
        return resp["schema"]
    return (resp.get("content", {}).get("application/json") or {}).get("schema")


def merged(schema, defs, depth=0):
    """Resolve $ref and fold allOf (Swagger inheritance, e.g. the Resource base) into one object."""
    s = resolve(schema, defs)
    if "allOf" not in s or depth > 5:
        return s
    props, typ = {}, s.get("type")
    for part in s["allOf"]:
        p = merged(part, defs, depth + 1)
        props.update(p.get("properties") or {})
        typ = typ or p.get("type")
    base = {k: v for k, v in s.items() if k != "allOf"}
    base["properties"] = {**props, **(s.get("properties") or {})}
    base["type"] = typ or ("object" if base["properties"] else None)
    return base


def leaves(schema, defs, prefix="", depth=0, out=None):
    if out is None:
        out = []
    if depth > MAX_DEPTH or len(out) >= MAX_FIELDS:
        return out
    s = merged(schema, defs)
    t = s.get("type")
    if t == "array" or ("items" in s and t is None):
        leaves(s.get("items", {}), defs, prefix + "[]", depth + 1, out)
    elif "properties" in s or t == "object":
        for name, sub in (s.get("properties") or {}).items():
            leaves(sub, defs, f"{prefix}.{name}" if prefix else name, depth + 1, out)
    else:
        out.append((prefix, t or ("enum" if s.get("enum") else "unknown"),
                    (s.get("description") or s.get("title") or "").replace("\n", " ").strip()))
    return out


def lab_evidence(run):
    """(api, template) -> {field: type}; plus the HTTP status counts per template."""
    ev = collections.defaultdict(dict)
    status = {}
    for api in ("manager", "policy"):
        for line in open(run / "raw" / f"{api}.jsonl", encoding="utf-8"):
            r = json.loads(line)
            key = (api, r["template"])
            status.setdefault(key, collections.Counter())[r["status"]] += 1
            if r["status"] != 200:
                continue
            fields = ev[key]

            def walk(n, p, d=0):
                if d > 8:
                    return
                if isinstance(n, dict):
                    for k, v in n.items():
                        walk(v, f"{p}.{k}" if p else k, d + 1)
                elif isinstance(n, list):
                    for v in n[:5]:
                        walk(v, f"{p}[]", d + 1)
                elif n not in (None, "", [], {}):
                    kind = {bool: "boolean", int: "integer", float: "number"}.get(type(n), "string")
                    fields.setdefault(p, kind)
            walk(r.get("body"), "")
    return ev, status


OBJECT_RULES = [
    (r"alarms|/events|realized-state/alarms", "Alarms and events"),
    (r"/licenses", "Licensing"),
    (r"^/upgrade|/upgrade/", "Upgrade coordinator"),
    (r"/sites/status|switchover-status|/federation", "Federation (sites)"),
    (r"^/cluster/|^/cluster$", "NSX Manager cluster"),
    (r"^/node|^/reverse-proxy/node", "NSX Manager node"),
    (r"systemhealth/appliances|infra/sha/appliances|/sha/", "Manager appliance process and latency (SHA)"),
    (r"compute-managers|compute-collections|vc-folder", "Compute manager (vCenter)"),
    (r"transport-node-collections", "Transport node collection"),
    (r"transport-zones", "Transport zone"),
    (r"edge-transport-nodes|edge-clusters|edge-cluster|/edge-nodes/|inter-site", "Edge transport node and edge cluster"),
    (r"host-transport-nodes|transport-nodes/status|transport-nodes/\{node-id\}/(status|pnic|remote)", "Transport node (ESXi host or Edge)"),
    (r"transport-nodes/\{transport-node-id\}/(network|node)", "Transport node (ESXi host or Edge)"),
    (r"idfw|firewall/security/intrusion|intrusion-service|ids-policy|signatures|settings/firewall", "Security services (IDFW, IDS/IPS)"),
    (r"malware|napp|scrx|service-insertion|serviceinsertion|teaser", "Security platform services (NAPP, MPS, SCRX, service insertion)"),
    (r"ip-blocks|ip-address-usage|ipam|third-party", "IP address management (IP blocks)"),
    (r"capacity|/limits|quota", "Capacity dashboard and limits"),
    (r"ipsec-vpn|l2vpn|/vpn", "VPN (IPsec, L2VPN)"),
    (r"transit-gateways|tgw", "Transit gateway (VPC)"),
    (r"/vpcs/|/subnets/", "VPC and subnet"),
    (r"lb-|load-?balancer|/lbs|dlb|lb-services|lb-pools|virtual-servers|vpc-lbs", "Load balancer"),
    (r"segments|/ports/|mac-table|arp-proxy|arp-table|bep-", "Segment and port"),
    (r"domains/[^/]+/(security-policies|gateway-policies|bridge-policies|intrusion)|/security-policies/|/gateway-policies/", "Firewall policy and rule (DFW, gateway)"),
    (r"tier-0s|tier-1s|tier0|tier1|locale-services|route-controllers|routing-table|forwarding-table|bgp|ospf|nat|dns-forwarder|static-routes|tier-1-interface|tier-0-interface", "Tier-0 and Tier-1 gateway, routing"),
    (r"realized-state|/state$|/status$|compliance|cluster/backups", "Realization and platform status"),
]


def object_type(ep):
    for pat, name in OBJECT_RULES:
        if re.search(pat, ep):
            return name
    return "Other platform status"


TIMESTAMP = re.compile(r"(_time|_timestamp|timestamp|system_time|_revision|_create_time)$|time$", re.I)
DISK = re.compile(r"disk|file_system|partition|repository|nonconfig|storage|/config|mount", re.I)
AVAIL = re.compile(r"status|state|health|connect|reachab|heartbeat|uptime|up_count|down_count|degraded_count|unknown_count|admin_down|bfd|tunnel|runtime|deploy|liveness|running|severity|diagnostic|sync_paused|_sync|failover|lost|last_reported|pids|alive|operational|resolution|outage", re.I)
CONTENTION = re.compile(r"drop|reject|error|overflow|overlimit|flood|queue|throttl|rate_limit|outstanding|latency|wait|backlog|exhaust|_full|full_|miss|collision|congest|(^|_)hold|fail|too_long|deadlock|stale|retrans|no_route|hop_limit|unreachable|nombufs|mismatch|overrun|carrier|no_match|discard|ignored|unknown_unicast|unknown_l2|cutoff|out_of", re.I)
DENOM = re.compile(r"(^|[._])(total|max|overall|capacity|limit|threshold|allocated|size|quota)($|[_])|max_|_total$|total_|threshold", re.I)
CONSUMPTION = re.compile(r"cpu|mem|memory|load|usage|used|utiliz|percent|pct|pps|mbps|eps|bytes|packets|pkts|session|hit|throughput|rate|count|available|heap|swap|cache|buffer|slab|bandwidth|conn|flows|vnics|pnics|ips|popularity|rx|tx|reserved|occupancy|lookup|learn|arp|mac", re.I)
COUNTER = re.compile(r"(_bytes|_packets|_pkts|_drops?|_dropped|_errors?|_carrier|_collisions|_count|_misses|_hits|_rx|_tx|bytes|packets|drops|dropped|errors|pkts|_sessions?|_hit|_miss|_flood|_full|_fail|_failures|_reject)$", re.I)
COUNTER_WORD = re.compile(r"drop|error|packet|pkt|byte|reject|miss|hit|flood|carrier|coll|frame", re.I)
NOT_COUNTER = re.compile(r"pps|mbps|eps|percent|pct|usage|rate|per_second|_ratio|_mb$", re.I)
INVENTORY = re.compile(r"result_count|cursor|page|cpu_cores|cpu_sockets|form_factor|_schema|_self|_links|display_name|_protection|node_type|node_path|node_display|(^|_)id$|name$|path$|uuid|version|address|fqdn|mtu|description|title|file_system$|type$|number_of_|source$|software|build|serial|error_code|failure_code|error_id|(^|_)code$|interval|periodic", re.I)
STATUSISH = re.compile(r"status|state|health|connect|tunnel|bfd|runtime|deployment_status|lcp_|mpa_|mgmt_connection|liveness|reachab|severity", re.I)
LEAF_AVAIL = re.compile(r"status|state|health|connect|up_count|down_count|degraded|unknown_count|admin_down|bfd|tunnel|heartbeat|uptime|running|alive|diagnostic|neighbors_(up|down)|established|sync|severity|liveness|reachab|resolution|outage|enabled|active_|down|reset|expired|signaled|detection_time", re.I)
LEAF_CONTENTION = re.compile(r"drop|reject|error_count|failure_count|errors?$|overflow|overlimit|flood|queue|throttl|rate_limit|outstanding|latency|wait|backlog|exhaust|_full|full_|miss|collision|congest|(^|_)hold|fail|unsuccessful|too_long|deadlock|stale|retrans|no_route|hop_limit|unreachable|nombufs|mismatch|overrun|carrier|no_match|discard|ignored|unknown_unicast|unknown_l2|cutoff|out_of", re.I)
ID_LIKE = re.compile(r"(^|_)(id|code|uuid|label|version|index|rank|cursor|lease_version)$|error_code|error_id|failure_code|^(major|minor|vlan|local_port|remote_port|step_number|number_of_steps|interface_index)$")


def classify(field, typ):
    """First-pass category. Leaf name is tested before the parent path."""
    parts = field.split(".")
    leaf = parts[-1].replace("[]", "").lower()
    parents = ".".join(parts[:-1]).lower().replace("queues[]", "q")
    numeric = typ in ("integer", "number")
    if typ in ("string", "enum") or (typ == "boolean" and not LEAF_AVAIL.search(leaf)):
        return "Availability" if STATUSISH.search(leaf) else "Inventory and configuration"
    if typ == "boolean":
        return "Availability"
    if not numeric:
        return "Inventory and configuration"
    if TIMESTAMP.search(leaf):
        return "Timestamp (freshness)"
    if ID_LIKE.search(leaf):
        return "Inventory and configuration"
    if INVENTORY.search(leaf) and not LEAF_CONTENTION.search(leaf):
        return "Inventory and configuration"
    if DISK.search(parents + "." + leaf):
        return "Disk space (capacity)"
    if LEAF_CONTENTION.search(leaf):
        return "Contention"
    if LEAF_AVAIL.search(leaf):
        return "Availability"
    if DENOM.search(leaf) and not re.search(r"used|available|current", leaf):
        return "Capacity and threshold (denominator)"
    if CONSUMPTION.search(leaf):
        return "Consumption"
    if CONTENTION.search(parents):
        return "Contention"
    if AVAIL.search(parents):
        return "Availability"
    if CONSUMPTION.search(parents):
        return "Consumption"
    return "Inventory and configuration"


def formula_hint(field, category):
    leaf = field.split(".")[-1].replace("[]", "").lower()
    if category == "Availability":
        if leaf.endswith("_count"):
            return "Count of objects in this state; roll-up status is NSX-computed"
        if "time" in leaf:
            return "Timestamp of last change"
        return "Enumerated state value"
    if category == "Timestamp (freshness)":
        return "Epoch milliseconds: use to compute sample interval"
    if category == "Disk space (capacity)":
        return "Gauge; utilisation = used / total x 100"
    if category == "Capacity and threshold (denominator)":
        return "Denominator or threshold; not a metric by itself"
    if re.search(r"pps|mbps|eps", leaf):
        return "NSX-computed per-second rate (no delta needed)"
    if re.search(r"percent|pct", leaf):
        return "NSX-computed percentage"
    if "popularity" in leaf:
        return "NSX-computed: session count / rule age (Broadcom API doc)"
    if (COUNTER.search(leaf) or COUNTER_WORD.search(leaf)) and not NOT_COUNTER.search(leaf):
        return "Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1)"
    if re.search(r"usage|used", leaf):
        return "Gauge; utilisation = used / total x 100 where total is available"
    return "Gauge: instantaneous value"


def main():
    run = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "output" / "nsxman1-run1"
    eps = catalog_endpoints(run)
    ev, status = lab_evidence(run)
    specs = {api: load_spec(run, api) for api in ("manager", "policy")}
    rows = []
    skipped = collections.Counter()
    for api, ep, lab, in_catalog in eps:
        spec, defs = specs[api]
        sch = response_schema(spec, ep)
        if sch is None:
            skipped["no 200 JSON schema or deprecated"] += 1
            continue
        otype = object_type(ep)
        observed = ev.get((api, ep), {})
        spec_fields = leaves(sch, defs)
        known = {f for f, _, _ in spec_fields}
        extra = [(f, kind, "Not declared in the OpenAPI schema; observed in the lab response")
                 for f, kind in observed.items() if f and f not in known]
        extra_names = {f for f, _, _ in extra}
        for field, typ, fdesc in spec_fields + extra:
            if not field:  # a bare primitive response body has no field name
                continue
            cat = classify(field, typ)
            rows.append({
                "api": api,
                "object_type": otype,
                "endpoint": ep,
                "field": field,
                "type": typ,
                "category": cat,
                "formula": formula_hint(field, cat),
                "description": fdesc[:300],
                "in_catalog": "yes" if in_catalog else "no",
                "lab_result": lab,
                "in_spec": "no" if field in extra_names else "yes",
                "lab_observed": "yes" if field in observed else "no",
            })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("catalog endpoints:", len(eps), "skipped:", dict(skipped))
    print("rows:", len(rows), "-> ", OUT)
    for k, v in collections.Counter(r["category"] for r in rows).most_common():
        print(f"  {v:6d}  {k}")


if __name__ == "__main__":
    main()
