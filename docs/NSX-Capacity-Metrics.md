# NSX capacity metrics

Capacity metrics answer **how much room is left**. This guide keeps them apart from consumption, as requested, and has two parts:

1. **Disk space.** Partition and file-system size and use. This is a capacity measure, so it lives here and not in [Consumption](NSX-Consumption-Metrics.md).
2. **Capacity denominators and limits.** The maximum that NSX supports for each kind of object (services, rules, groups, hosts, gateways, IP blocks), and how close the system is to it.

- Companion guides: [Formulas](NSX-Metrics-Formulas.md) · [Contention](NSX-Contention-Metrics.md) · [Consumption](NSX-Consumption-Metrics.md) · [Availability and events](NSX-Availability-Metrics-and-Events.md)
- Lab: `nsxman1`, NSX 9.1.1.0. Crawl 2026-10-19.
- Open questions: [NSX-Open-Questions.md](NSX-Open-Questions.md), numbered D1 to D18 and referred to by number in this guide.
- Evidence tags: **[Lab]**, **[Doc]**, **[Derived]**, **[Open]**.

---

## 1. Disk space

### 1.1 Formula

| Metric | Formula | Fields |
|---|---|---|
| Partition used % | `used ÷ total × 100` | `file_systems[].used`, `file_systems[].total` |
| Node disk used % | `disk_space_used ÷ disk_space_total × 100` | `system_status.disk_space_used`, `disk_space_total` |
| Free space | `total − used` | same |

Each entry in `file_systems[]` carries `file_system`, `mount`, `type`, `total` and `used`. The units are not stated in the schema. The values look like kilobytes ([Derived], same convention as memory). The `disk_space_total` and `disk_space_used` fields on hosts read 0 in the lab, so use the per-file-system values there ([Lab]).

### 1.2 Lab: ESXi host root and ramdisks

The lab host reports its filesystems as `ramdisk`. Utilisation computed with the formula above ([Lab] values, [Derived] percentages):

| Mount | Used | Total | Used % |
|---|---:|---:|---:|
| `/` (root) | 24,504 | 32,768 | **74.8%** |
| `/vsantraces` | 88,540 | 307,200 | 28.8% |
| `/opt` | 4,316 | 32,768 | 13.2% |
| `/etc` | 2,836 | 28,672 | 9.9% |
| `/var/lib/vmware/nsx/nestdb/db` | 3,996 | 524,288 | 0.8% |
| `/var` | 1,336 | 49,152 | 2.7% |
| `/var/lib/vmware/hostd/stats` | 9,372 | 1,846,272 | 0.5% |
| `/tmp` | 1,108 | 262,144 | 0.4% |

**Reading the root figure.** At 74.8%, the root ramdisk is the fullest partition on the host. Ramdisk sizes are set by the hypervisor, not by NSX, and I found no NSX event for host ramdisks among the 284 event definitions. Whether 74.8% is a problem depends on how ESXi uses `/`, so check it on the host (`df`) before you act ([Open]).

### 1.3 Disk-space events

These are the NSX disk alarms in the lab's event definitions. Thresholds are as recorded in the event definition ([Lab]).

| Event | Object | High | Very high | Note |
|---|---|---:|---:|---|
| `manager_disk_usage_high` / `_very_high` | Manager partition | 80% | 90% | Standard pattern |
| `edge_disk_usage_high` / `_very_high` | Edge partition | 80% | 90% | Standard pattern |
| `manager_config_disk_usage_high` / `_very_high` | Manager `/config` | **20%** | **30%** | Unusual. Much lower than the standard pattern. [Open], D16. |
| `operations_db_disk_usage_high` / `_very_high` | Manager `/nonconfig` | **20%** | **30%** | Unusual, same values as `/config`. [Open], D16. |
| `operations_repository_disk_usage_very_high` | Manager `/repository` | — | 98% | Only a very-high level is defined |

**Why this matters.** If the `/config` and `/nonconfig` thresholds are really 20% and 30%, a manager could raise a "very high" alarm while there is still most of the partition free. Check the event description text on your version before you rely on these levels.

---

## 2. Capacity denominators and limits

### 2.1 Formula

| Metric | Formula | Lab value |
|---|---|---|
| Object usage % | `current_usage_count ÷ max_supported_count × 100` | Services: 415 ÷ 850 = **48.82%** ✓ matches the response's `current_usage_percentage` |
| Object headroom | `max_supported_count − current_usage_count` | Services: 435 |
| IP block used % | `used_ips_count ÷ overall_ips_count × 100` (strings, cast first) | 0 ÷ 65,536 = **0%** |
| Limit state | `/infra/limits/state` (consumption and operational state for limits) | Present in the lab |

### 2.2 Severity, verified in the lab

| Usage | Response severity | Source |
|---|---|---|
| 48.82% (Services) | **INFO** | [Lab] |
| 100% (Compute Managers, 1 of 1) | **WARNING** | [Lab] |

Global thresholds in the response: minimum **70%**, maximum **100%** ([Lab]). The lab confirms INFO below 70% and WARNING at 100%. What happens between 70% and 100% is **not confirmed** ([Open], D18).

### 2.3 Lab dashboard highlights

| Object | Used | Max | Used % | Severity |
|---|---:|---:|---:|---|
| **Compute Managers** | 1 | 1 | **100.0%** | **WARNING** |
| Geo IP groups | 249 | 1,000 | 24.9% | INFO |
| vSphere clusters prepared for NSX | 1 | 4 | 25.0% | INFO |
| Services | 415 | 850 | 48.8% | INFO |
| Groups | 258 | 3,000 | 8.6% | INFO |
| Groups based on IP sets or addresses | 250 | 3,000 | 8.3% | INFO |
| Hypervisor hosts (prepared) | 3 | 64 | 4.7% | INFO |
| Intrusion detection and prevention profiles | 1 | 25 | 4.0% | INFO |
| Security policy rules | 6 | 8,500 | 0.07% | INFO |
| Segments | 0 | 360 | 0% | INFO |
| Tier-0 gateways | 0 | 8 | 0% | INFO |

**The compute manager at 100%.** The system supports one compute manager, and one is registered. No more vCenters can be added until the limit changes. The response severity is WARNING ([Lab]). This is a design limit, not a fault.

**Open capacity alarms in the lab.** A `minimum_capacity_threshold` alarm is open, and an `ip_pool_usage_very_high` alarm is open. The alarm records do not name the object that breached a threshold, so I have not tied either one to a metric here ([Open], see 2.4).

### 2.4 Capacity gap: IP pool usage

The crawl has **no metric endpoint for IP pool usage**. The policy spec has `…/ip-pools/{id}/ip-allocations` (a list of allocations), but it is not a usage summary. The manager spec has no pool-usage endpoint at all. An IP-pool usage percentage would have to be derived ([Derived]):

> pool usage % = count(ip-allocations) ÷ size of the pool range × 100

This is my construction, not an NSX formula. The `ip_pool_usage_very_high` alarm is open, so the derived figure is worth checking against the alarm ([Open], D17).

---

## 3. Lab reading summary

| Question | Answer | Basis |
|---|---|---|
| Is any host partition near its limit? | Root ramdisk on the ESXi host, 74.8%. Check on the host. | [Lab] values, [Derived] percentage |
| Is the manager disk near an alarm? | No disk alarm is open. The manager returns `file_systems`, but I did not extract the `/config`, `/nonconfig` and `/repository` values for this summary. | [Lab] alarms. Partition values [Open]. |
| Is any object type at its maximum? | Compute managers, 1 of 1 (100%, WARNING) | [Lab] |
| Is the system near a global limit? | No. The highest object usage other than the compute manager is Services at 48.8%. | [Lab] |

---

## 4. Full lists by object type

Generated from [`data/nsx-metric-fields.csv`](data/nsx-metric-fields.csv) by `tools/build_metric_docs.py`. The first group is disk space. The second group is capacity denominators (`total`, `max`, `overall`, `capacity`, `limit`, `threshold`). Column meanings are in the [contention guide, section 6](NSX-Contention-Metrics.md#6-full-lists-by-object-type).

<!-- BEGIN GENERATED: capacity -->
<details>
<summary><b>Transport node (ESXi host or Edge)</b> — 41 fields, 8 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].node_status.system_status.disk_space_total` | integer | 3 | ✓ | Gauge; utilisation = used / total x 100 | Amount of disk space available on the system, in kilobytes. |
| `results[].node_status.system_status.disk_space_used` | integer | 3 | ✓ | Gauge; utilisation = used / total x 100 | Amount of disk space in use on the system, in kilobytes |
| `results[].node_status.system_status.edge_mem_usage.datapath_total_usage` | number | 3 | – | Denominator or threshold; not a metric by itself | Percentage of memory in use by datapath processes which includes RES and hugepage memory. |
| `results[].node_status.system_status.mem_total` | integer | 3 | ✓ | Denominator or threshold; not a metric by itself | Amount of RAM allocated to the system, in kilobytes |
| `results[].node_status.system_status.swap_total` | integer | 3 | ✓ | Denominator or threshold; not a metric by itself | Amount of disk available for swap, in kilobytes |
| `agent_status.agents[].resource_usage.memory_total` | integer | 2 | – | Denominator or threshold; not a metric by itself | Total available memory in kilobytes. |
| `fast_path_sys_stats.host_enhanced_fastpath.flow_table_size` | integer | 2 | – | Denominator or threshold; not a metric by itself | The number of flow table entries in a flow table. |
| `fast_path_sys_stats.host_standard_fastpath.flow_table_size` | integer | 2 | – | Denominator or threshold; not a metric by itself | The number of flow table entries in a flow table. |
| `node_status.system_status.dfw_heap_memory_usage[].total_mb` | integer | 2 | ✓ | Denominator or threshold; not a metric by itself | Total size of heap for the specified heap in mb units. |
| `node_status.system_status.disk_space_total` | integer | 2 | ✓ | Gauge; utilisation = used / total x 100 | Amount of disk space available on the system, in kilobytes. |
| `node_status.system_status.disk_space_used` | integer | 2 | ✓ | Gauge; utilisation = used / total x 100 | Amount of disk space in use on the system, in kilobytes |
| `node_status.system_status.dpus[].mem_total` | integer | 2 | – | Denominator or threshold; not a metric by itself | System Amount of RAM allocated to the system, in kilobytes. |
| `node_status.system_status.edge_mem_usage.datapath_total_usage` | number | 2 | – | Denominator or threshold; not a metric by itself | Percentage of memory in use by datapath processes which includes RES and hugepage memory. |
| `node_status.system_status.file_systems[].total` | integer | 2 | ✓ | Gauge; utilisation = used / total x 100 | File system size in kilobytes |
| `node_status.system_status.file_systems[].used` | integer | 2 | ✓ | Gauge; utilisation = used / total x 100 | Amount of file system used in kilobytes |
| `node_status.system_status.mem_total` | integer | 2 | ✓ | Denominator or threshold; not a metric by itself | Amount of RAM allocated to the system, in kilobytes |
| `node_status.system_status.swap_total` | integer | 2 | ✓ | Denominator or threshold; not a metric by itself | Amount of disk available for swap, in kilobytes |
| `platform_cpu_usage_stats.host_pcpu.total_cpu` | number | 2 | – | Denominator or threshold; not a metric by itself | Sum of utilization of all (V)CPUs on the host. |
| `platform_cpu_usage_stats.host_vcpu.total_cpu` | number | 2 | – | Denominator or threshold; not a metric by itself | Sum of utilization of all (V)CPUs on the host. |
| `platform_packet_stats.host_uplink.rx_error_total` | integer | 2 | – | Denominator or threshold; not a metric by itself | Total RX drop (including errors) reported by the driver. |
| `dfw_heap_memory_usage[].total_mb` | integer | 1 | – | Denominator or threshold; not a metric by itself | Total size of heap for the specified heap in mb units. |
| `disk_space_total` | integer | 1 | – | Gauge; utilisation = used / total x 100 | Amount of disk space available on the system, in kilobytes. |
| `disk_space_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 | Amount of disk space in use on the system, in kilobytes |
| `dpus[].mem_total` | integer | 1 | – | Denominator or threshold; not a metric by itself | System Amount of RAM allocated to the system, in kilobytes. |
| `edge_mem_usage.datapath_total_usage` | number | 1 | – | Denominator or threshold; not a metric by itself | Percentage of memory in use by datapath processes which includes RES and hugepage memory. |
| `file_systems[].total` | integer | 1 | – | Gauge; utilisation = used / total x 100 | File system size in kilobytes |
| `file_systems[].used` | integer | 1 | – | Gauge; utilisation = used / total x 100 | Amount of file system used in kilobytes |
| `mem_total` | integer | 1 | – | Denominator or threshold; not a metric by itself | Amount of RAM allocated to the system, in kilobytes |
| `packet_stats.distributed_firewall.src_limit_misc` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | src-limit. |
| `platform_cpu_usage_stats.host_net_thread_all.max_cpu` | number | 1 | – | Denominator or threshold; not a metric by itself | Maximum CPU utilization of network threads in the group. |
| `platform_cpu_usage_stats.host_net_thread_all.total_cpu` | number | 1 | – | Denominator or threshold; not a metric by itself | Sum of CPU utilization of network threads in the group. |
| `platform_cpu_usage_stats.host_net_thread_nioc.max_cpu` | number | 1 | – | Denominator or threshold; not a metric by itself | Maximum CPU utilization of network threads in the group. |
| `platform_cpu_usage_stats.host_net_thread_nioc.total_cpu` | number | 1 | – | Denominator or threshold; not a metric by itself | Sum of CPU utilization of network threads in the group. |
| `platform_cpu_usage_stats.host_net_thread_rx.max_cpu` | number | 1 | – | Denominator or threshold; not a metric by itself | Maximum CPU utilization of network threads in the group. |
| `platform_cpu_usage_stats.host_net_thread_rx.total_cpu` | number | 1 | – | Denominator or threshold; not a metric by itself | Sum of CPU utilization of network threads in the group. |
| `platform_cpu_usage_stats.host_net_thread_tx.max_cpu` | number | 1 | – | Denominator or threshold; not a metric by itself | Maximum CPU utilization of network threads in the group. |
| `platform_cpu_usage_stats.host_net_thread_tx.total_cpu` | number | 1 | – | Denominator or threshold; not a metric by itself | Sum of CPU utilization of network threads in the group. |
| `results[].node_status.system_status.file_systems[].total` † | integer | 1 | ✓ | Gauge; utilisation = used / total x 100 | – |
| `results[].node_status.system_status.file_systems[].used` † | integer | 1 | ✓ | Gauge; utilisation = used / total x 100 | – |
| `scrx_stats.host_scrx.service_datapath_total_memory` | integer | 1 | – | Denominator or threshold; not a metric by itself | service_datapath_total_memory |
| `swap_total` | integer | 1 | – | Denominator or threshold; not a metric by itself | Amount of disk available for swap, in kilobytes |

</details>

<details>
<summary><b>Edge transport node and edge cluster</b> — 40 fields, 18 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `member_status[].total_bgp_sessions` | integer | 3 | – | Denominator or threshold; not a metric by itself | Total number of inter-site IBGP sessions. |
| `stats_per_site[].rx.total_bytes` | integer | 3 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `stats_per_site[].rx.total_packets` | integer | 3 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `stats_per_site[].stats_per_tunnel[].rx.total_bytes` | integer | 3 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `stats_per_site[].stats_per_tunnel[].rx.total_packets` | integer | 3 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `stats_per_site[].stats_per_tunnel[].tx.total_bytes` | integer | 3 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `stats_per_site[].stats_per_tunnel[].tx.total_packets` | integer | 3 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `stats_per_site[].tx.total_bytes` | integer | 3 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `stats_per_site[].tx.total_packets` | integer | 3 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `total_bytes` | integer | 3 | – | Denominator or threshold; not a metric by itself | Provides the total number of bytes processed on the NAT rules since the time the rules were created. |
| `total_packets` | integer | 3 | – | Denominator or threshold; not a metric by itself | Provides the total number of packets processed on the NAT rules since the time the rules were created. |
| `edge_nodes[].neighbor_status[].total_in_prefix_count` | integer | 2 | – | Denominator or threshold; not a metric by itself | Sum of in prefixes counts across all address families. |
| `edge_nodes[].neighbor_status[].total_out_prefix_count` | integer | 2 | – | Denominator or threshold; not a metric by itself | Sum of out prefixes counts across all address families. |
| `member_status[].neighbor_status[].total_in_prefix_count` | integer | 2 | – | Denominator or threshold; not a metric by itself | Sum of in prefixes counts across all address families. |
| `member_status[].neighbor_status[].total_out_prefix_count` | integer | 2 | – | Denominator or threshold; not a metric by itself | Sum of out prefixes counts across all address families. |
| `neighbor_status[].total_in_prefix_count` | integer | 2 | – | Denominator or threshold; not a metric by itself | Sum of in prefixes counts across all address families. |
| `neighbor_status[].total_out_prefix_count` | integer | 2 | – | Denominator or threshold; not a metric by itself | Sum of out prefixes counts across all address families. |
| `rx_stats.total_bytes` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `rx_stats.total_packets` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `tx_stats.total_bytes` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `tx_stats.total_packets` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `agent_status.agents[].resource_usage.memory_total` | integer | 1 | – | Denominator or threshold; not a metric by itself | Total available memory in kilobytes. |
| `node_status.system_status.dfw_heap_memory_usage[].total_mb` | integer | 1 | – | Denominator or threshold; not a metric by itself | Total size of heap for the specified heap in mb units. |
| `node_status.system_status.disk_space_total` | integer | 1 | – | Gauge; utilisation = used / total x 100 | Amount of disk space available on the system, in kilobytes. |
| `node_status.system_status.disk_space_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 | Amount of disk space in use on the system, in kilobytes |
| `node_status.system_status.dpus[].mem_total` | integer | 1 | – | Denominator or threshold; not a metric by itself | System Amount of RAM allocated to the system, in kilobytes. |
| `node_status.system_status.edge_mem_usage.datapath_total_usage` | number | 1 | – | Denominator or threshold; not a metric by itself | Percentage of memory in use by datapath processes which includes RES and hugepage memory. |
| `node_status.system_status.file_systems[].total` | integer | 1 | – | Gauge; utilisation = used / total x 100 | File system size in kilobytes |
| `node_status.system_status.file_systems[].used` | integer | 1 | – | Gauge; utilisation = used / total x 100 | Amount of file system used in kilobytes |
| `node_status.system_status.mem_total` | integer | 1 | – | Denominator or threshold; not a metric by itself | Amount of RAM allocated to the system, in kilobytes |
| `node_status.system_status.swap_total` | integer | 1 | – | Denominator or threshold; not a metric by itself | Amount of disk available for swap, in kilobytes |
| `results[].node_status.system_status.disk_space_total` | integer | 1 | – | Gauge; utilisation = used / total x 100 | Amount of disk space available on the system, in kilobytes. |
| `results[].node_status.system_status.disk_space_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 | Amount of disk space in use on the system, in kilobytes |
| `results[].node_status.system_status.edge_mem_usage.datapath_total_usage` | number | 1 | – | Denominator or threshold; not a metric by itself | Percentage of memory in use by datapath processes which includes RES and hugepage memory. |
| `results[].node_status.system_status.mem_total` | integer | 1 | – | Denominator or threshold; not a metric by itself | Amount of RAM allocated to the system, in kilobytes |
| `results[].node_status.system_status.swap_total` | integer | 1 | – | Denominator or threshold; not a metric by itself | Amount of disk available for swap, in kilobytes |
| `rx.total_bytes` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `rx.total_packets` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `tx.total_bytes` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `tx.total_packets` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |

</details>

<details>
<summary><b>VPC and subnet</b> — 38 fields, 11 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].statistics.max_session_count` | integer | 2 | – | Denominator or threshold; not a metric by itself | Maximum value of sessions count of all rules of the type. This is aggregated statistic which are computed with lower frequency compared to… |
| `results[].statistics.results[].max_session_count` | integer | 2 | – | Denominator or threshold; not a metric by itself | Maximum value of sessions count of all rules of the type. This is aggregated statistic which are computed with lower frequency compared to… |
| `results[].statistics.results[].total_session_count` | integer | 2 | – | Denominator or threshold; not a metric by itself | Aggregated number of sessions processed by all the rules This is aggregated statistic which are computed with lower frequency compared to i… |
| `results[].statistics.total_session_count` | integer | 2 | – | Denominator or threshold; not a metric by itself | Aggregated number of sessions processed by all the rules This is aggregated statistic which are computed with lower frequency compared to i… |
| `rx_bytes.total` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total packets or bytes |
| `rx_packets.total` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total packets or bytes |
| `tx_bytes.total` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total packets or bytes |
| `tx_packets.total` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total packets or bytes |
| `external_traffic.rx.total_bytes` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of bytes |
| `external_traffic.rx.total_packets` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of packets |
| `external_traffic.tx.total_bytes` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of bytes |
| `external_traffic.tx.total_packets` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of packets |
| `gateway_interface.rx.total_bytes` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `gateway_interface.rx.total_packets` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `gateway_interface.tx.total_bytes` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `gateway_interface.tx.total_packets` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `internal_traffic.rx.total_bytes` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of bytes |
| `internal_traffic.rx.total_packets` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of packets |
| `internal_traffic.tx.total_bytes` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of bytes |
| `internal_traffic.tx.total_packets` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of packets |
| `ip_pool_stats[].allocated_number` | integer | 1 | – | Denominator or threshold; not a metric by itself | allocated number. COULD BE INACCURATE, REFERENCE ONLY. |
| `ip_pool_stats[].allocated_percentage` | integer | 1 | – | Denominator or threshold; not a metric by itself | allocated percentage. COULD BE INACCURATE, REFERENCE ONLY. |
| `ip_pool_stats[].pool_size` | integer | 1 | – | Denominator or threshold; not a metric by itself | pool size |
| `nsxt_vsip.src_limit_misc` | integer | 1 | – | Denominator or threshold; not a metric by itself | src-limit. |
| `results[].per_node_statistics[].total_bytes` | integer | 1 | – | Denominator or threshold; not a metric by itself | Provides the total number of bytes processed on the NAT rules since the time the rules were created. |
| `results[].per_node_statistics[].total_packets` | integer | 1 | – | Denominator or threshold; not a metric by itself | Provides the total number of packets processed on the NAT rules since the time the rules were created. |
| `results[].rule_statistics[].total_bytes` | integer | 1 | – | Denominator or threshold; not a metric by itself | Provides the total number of bytes processed on the NAT rules since the time the rules were created. |
| `results[].rule_statistics[].total_packets` | integer | 1 | – | Denominator or threshold; not a metric by itself | Provides the total number of packets processed on the NAT rules since the time the rules were created. |
| `results[].statistics.total_bytes` | integer | 1 | – | Denominator or threshold; not a metric by itself | Provides the total number of bytes processed on the NAT rules since the time the rules were created. |
| `results[].statistics.total_packets` | integer | 1 | – | Denominator or threshold; not a metric by itself | Provides the total number of packets processed on the NAT rules since the time the rules were created. |
| `rx.total_bytes` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `rx.total_packets` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `tx.total_bytes` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `tx.total_packets` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `vlan_extension.vlan_to_vpc_bytes.total` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number includes all traffic: multicast, broadcast, unknown unicast, known unicast, and dropped packets. |
| `vlan_extension.vlan_to_vpc_packets.total` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number includes all traffic: multicast, broadcast, unknown unicast, known unicast, and dropped packets. |
| `vlan_extension.vpc_to_vlan_bytes.total` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number includes all traffic: multicast, broadcast, unknown unicast, known unicast, and dropped packets. |
| `vlan_extension.vpc_to_vlan_packets.total` | integer | 1 | – | Denominator or threshold; not a metric by itself | The total number includes all traffic: multicast, broadcast, unknown unicast, known unicast, and dropped packets. |

</details>

<details>
<summary><b>Tier-0 and Tier-1 gateway, routing</b> — 30 fields, 43 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `per_node_statistics[].rx.total_bytes` | integer | 11 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `per_node_statistics[].rx.total_packets` | integer | 11 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `per_node_statistics[].tx.total_bytes` | integer | 11 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `per_node_statistics[].tx.total_packets` | integer | 11 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `rx.total_bytes` | integer | 11 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `rx.total_packets` | integer | 11 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `tx.total_bytes` | integer | 11 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `tx.total_packets` | integer | 11 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `members[].per_node_statistics[].rx.total_bytes` | integer | 5 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `members[].per_node_statistics[].rx.total_packets` | integer | 5 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `members[].per_node_statistics[].tx.total_bytes` | integer | 5 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `members[].per_node_statistics[].tx.total_packets` | integer | 5 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `results[].per_node_statistics[].total_bytes` | integer | 5 | – | Denominator or threshold; not a metric by itself | Provides the total number of bytes processed on the NAT rules since the time the rules were created. |
| `results[].per_node_statistics[].total_packets` | integer | 5 | – | Denominator or threshold; not a metric by itself | Provides the total number of packets processed on the NAT rules since the time the rules were created. |
| `results[].rule_statistics[].total_bytes` | integer | 5 | – | Denominator or threshold; not a metric by itself | Provides the total number of bytes processed on the NAT rules since the time the rules were created. |
| `results[].rule_statistics[].total_packets` | integer | 5 | – | Denominator or threshold; not a metric by itself | Provides the total number of packets processed on the NAT rules since the time the rules were created. |
| `results[].statistics.total_bytes` | integer | 5 | – | Denominator or threshold; not a metric by itself | Provides the total number of bytes processed on the NAT rules since the time the rules were created. |
| `results[].statistics.total_packets` | integer | 5 | – | Denominator or threshold; not a metric by itself | Provides the total number of packets processed on the NAT rules since the time the rules were created. |
| `summary.rx.total_bytes` | integer | 5 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `summary.rx.total_packets` | integer | 5 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `summary.tx.total_bytes` | integer | 5 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `summary.tx.total_packets` | integer | 5 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `results[].total_in_prefix_count` | integer | 3 | – | Denominator or threshold; not a metric by itself | Sum of in prefixes counts across all address families. |
| `results[].total_out_prefix_count` | integer | 3 | – | Denominator or threshold; not a metric by itself | Sum of out prefixes counts across all address families. |
| `instance_runtime_statistics[].interface_statistics[].rx_bytes.total` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total packets or bytes |
| `instance_runtime_statistics[].interface_statistics[].rx_packets.total` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total packets or bytes |
| `instance_runtime_statistics[].interface_statistics[].tx_bytes.total` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total packets or bytes |
| `instance_runtime_statistics[].interface_statistics[].tx_packets.total` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total packets or bytes |
| `total_bytes` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | Provides the total number of bytes processed on the NAT rules since the time the rules were created. |
| `total_packets` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | Provides the total number of packets processed on the NAT rules since the time the rules were created. |

</details>

<details>
<summary><b>NSX Manager cluster</b> — 19 fields, 3 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `dfw_heap_memory_usage[].total_mb` | integer | 1 | – | Denominator or threshold; not a metric by itself | Total size of heap for the specified heap in mb units. |
| `disk_space_total` | integer | 1 | – | Gauge; utilisation = used / total x 100 | Amount of disk space available on the system, in kilobytes. |
| `disk_space_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 | Amount of disk space in use on the system, in kilobytes |
| `dpus[].mem_total` | integer | 1 | – | Denominator or threshold; not a metric by itself | System Amount of RAM allocated to the system, in kilobytes. |
| `edge_mem_usage.datapath_total_usage` | number | 1 | – | Denominator or threshold; not a metric by itself | Percentage of memory in use by datapath processes which includes RES and hugepage memory. |
| `file_systems[].total` | integer | 1 | – | Gauge; utilisation = used / total x 100 | File system size in kilobytes |
| `file_systems[].used` | integer | 1 | – | Gauge; utilisation = used / total x 100 | Amount of file system used in kilobytes |
| `mem_total` | integer | 1 | – | Denominator or threshold; not a metric by itself | Amount of RAM allocated to the system, in kilobytes |
| `swap_total` | integer | 1 | – | Denominator or threshold; not a metric by itself | Amount of disk available for swap, in kilobytes |
| `system_status.dfw_heap_memory_usage[].total_mb` | integer | 1 | – | Denominator or threshold; not a metric by itself | Total size of heap for the specified heap in mb units. |
| `system_status.disk_space_total` | integer | 1 | ✓ | Gauge; utilisation = used / total x 100 | Amount of disk space available on the system, in kilobytes. |
| `system_status.disk_space_used` | integer | 1 | ✓ | Gauge; utilisation = used / total x 100 | Amount of disk space in use on the system, in kilobytes |
| `system_status.dpus[].mem_total` | integer | 1 | – | Denominator or threshold; not a metric by itself | System Amount of RAM allocated to the system, in kilobytes. |
| `system_status.edge_mem_usage.datapath_total_usage` | number | 1 | – | Denominator or threshold; not a metric by itself | Percentage of memory in use by datapath processes which includes RES and hugepage memory. |
| `system_status.file_systems[].total` | integer | 1 | ✓ | Gauge; utilisation = used / total x 100 | File system size in kilobytes |
| `system_status.file_systems[].used` | integer | 1 | ✓ | Gauge; utilisation = used / total x 100 | Amount of file system used in kilobytes |
| `system_status.mem_total` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | Amount of RAM allocated to the system, in kilobytes |
| `system_status.swap_total` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | Amount of disk available for swap, in kilobytes |
| `total_steps` | integer | 1 | – | Denominator or threshold; not a metric by itself | Total number of steps in the entire restore process |

</details>

<details>
<summary><b>Transit gateway (VPC)</b> — 18 fields, 5 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `rx.total_bytes` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total number of bytes |
| `rx.total_packets` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total number of packets |
| `tx.total_bytes` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total number of bytes |
| `tx.total_packets` | integer | 2 | – | Denominator or threshold; not a metric by itself | The total number of packets |
| `external_traffic.rx.total_bytes` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | The total number of bytes |
| `external_traffic.rx.total_packets` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | The total number of packets |
| `external_traffic.tx.total_bytes` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | The total number of bytes |
| `external_traffic.tx.total_packets` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | The total number of packets |
| `internal_traffic.rx.total_bytes` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | The total number of bytes |
| `internal_traffic.rx.total_packets` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | The total number of packets |
| `internal_traffic.tx.total_bytes` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | The total number of bytes |
| `internal_traffic.tx.total_packets` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | The total number of packets |
| `results[].per_node_statistics[].total_bytes` | integer | 1 | – | Denominator or threshold; not a metric by itself | Provides the total number of bytes processed on the NAT rules since the time the rules were created. |
| `results[].per_node_statistics[].total_packets` | integer | 1 | – | Denominator or threshold; not a metric by itself | Provides the total number of packets processed on the NAT rules since the time the rules were created. |
| `results[].rule_statistics[].total_bytes` | integer | 1 | – | Denominator or threshold; not a metric by itself | Provides the total number of bytes processed on the NAT rules since the time the rules were created. |
| `results[].rule_statistics[].total_packets` | integer | 1 | – | Denominator or threshold; not a metric by itself | Provides the total number of packets processed on the NAT rules since the time the rules were created. |
| `results[].statistics.total_bytes` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | Provides the total number of bytes processed on the NAT rules since the time the rules were created. |
| `results[].statistics.total_packets` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | Provides the total number of packets processed on the NAT rules since the time the rules were created. |

</details>

<details>
<summary><b>Manager appliance process and latency (SHA)</b> — 14 fields, 8 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `latency_data[].rtt_max` | number | 2 | – | Denominator or threshold; not a metric by itself | Display the max Round Trip Time in milliseconds. |
| `results[].latency_data[].rtt_max` | number | 2 | – | Denominator or threshold; not a metric by itself | Display the max Round Trip Time in milliseconds. |
| `results[].top_process_by_cpu_list[].resident_memory_size` | number | 2 | ✓ | Denominator or threshold; not a metric by itself | The non-swapped physical memoery a task is using. |
| `results[].top_process_by_cpu_list[].shared_memory_size` | number | 2 | ✓ | Denominator or threshold; not a metric by itself | The amount of shared memory available to a process, not all of which is typically resident. It simply reflects memory that could be potenti… |
| `results[].top_process_by_cpu_list[].virtual_memory_size` | number | 2 | ✓ | Denominator or threshold; not a metric by itself | The total amount of virtual memory used by the process. It includes all code, data and shared libraries plus pages that have been swapped o… |
| `results[].top_process_by_mem_list[].resident_memory_size` | number | 2 | ✓ | Denominator or threshold; not a metric by itself | The non-swapped physical memoery a task is using. |
| `results[].top_process_by_mem_list[].shared_memory_size` | number | 2 | ✓ | Denominator or threshold; not a metric by itself | The amount of shared memory available to a process, not all of which is typically resident. It simply reflects memory that could be potenti… |
| `results[].top_process_by_mem_list[].virtual_memory_size` | number | 2 | ✓ | Denominator or threshold; not a metric by itself | The total amount of virtual memory used by the process. It includes all code, data and shared libraries plus pages that have been swapped o… |
| `top_process_by_cpu_list[].resident_memory_size` | number | 2 | – | Denominator or threshold; not a metric by itself | The non-swapped physical memoery a task is using. |
| `top_process_by_cpu_list[].shared_memory_size` | number | 2 | – | Denominator or threshold; not a metric by itself | The amount of shared memory available to a process, not all of which is typically resident. It simply reflects memory that could be potenti… |
| `top_process_by_cpu_list[].virtual_memory_size` | number | 2 | – | Denominator or threshold; not a metric by itself | The total amount of virtual memory used by the process. It includes all code, data and shared libraries plus pages that have been swapped o… |
| `top_process_by_mem_list[].resident_memory_size` | number | 2 | – | Denominator or threshold; not a metric by itself | The non-swapped physical memoery a task is using. |
| `top_process_by_mem_list[].shared_memory_size` | number | 2 | – | Denominator or threshold; not a metric by itself | The amount of shared memory available to a process, not all of which is typically resident. It simply reflects memory that could be potenti… |
| `top_process_by_mem_list[].virtual_memory_size` | number | 2 | – | Denominator or threshold; not a metric by itself | The total amount of virtual memory used by the process. It includes all code, data and shared libraries plus pages that have been swapped o… |

</details>

<details>
<summary><b>Segment and port</b> — 13 fields, 27 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `rx_bytes.total` | integer | 15 | – | Denominator or threshold; not a metric by itself | The total packets or bytes |
| `rx_packets.total` | integer | 15 | – | Denominator or threshold; not a metric by itself | The total packets or bytes |
| `tx_bytes.total` | integer | 15 | – | Denominator or threshold; not a metric by itself | The total packets or bytes |
| `tx_packets.total` | integer | 15 | – | Denominator or threshold; not a metric by itself | The total packets or bytes |
| `nsxt_vsip.src_limit_misc` | integer | 6 | – | Denominator or threshold; not a metric by itself | src-limit. |
| `per_node_statistics[].rx.total_bytes` | integer | 6 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `per_node_statistics[].rx.total_packets` | integer | 6 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `per_node_statistics[].tx.total_bytes` | integer | 6 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `per_node_statistics[].tx.total_packets` | integer | 6 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `rx.total_bytes` | integer | 6 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `rx.total_packets` | integer | 6 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |
| `tx.total_bytes` | integer | 6 | – | Denominator or threshold; not a metric by itself | The total number of bytes transferred since the time the logical router port was created. This will be reset on edge reboot or edge datapla… |
| `tx.total_packets` | integer | 6 | – | Denominator or threshold; not a metric by itself | The total number of packets transferred since the time the logical router port was created. This will be reset on edge reboot or edge datap… |

</details>

<details>
<summary><b>NSX Manager node</b> — 9 fields, 1 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `dfw_heap_memory_usage[].total_mb` | integer | 1 | – | Denominator or threshold; not a metric by itself | Total size of heap for the specified heap in mb units. |
| `disk_space_total` | integer | 1 | – | Gauge; utilisation = used / total x 100 | Amount of disk space available on the system, in kilobytes. |
| `disk_space_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 | Amount of disk space in use on the system, in kilobytes |
| `dpus[].mem_total` | integer | 1 | – | Denominator or threshold; not a metric by itself | System Amount of RAM allocated to the system, in kilobytes. |
| `edge_mem_usage.datapath_total_usage` | number | 1 | – | Denominator or threshold; not a metric by itself | Percentage of memory in use by datapath processes which includes RES and hugepage memory. |
| `file_systems[].total` | integer | 1 | ✓ | Gauge; utilisation = used / total x 100 | File system size in kilobytes |
| `file_systems[].used` | integer | 1 | ✓ | Gauge; utilisation = used / total x 100 | Amount of file system used in kilobytes |
| `mem_total` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | Amount of RAM allocated to the system, in kilobytes |
| `swap_total` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | Amount of disk available for swap, in kilobytes |

</details>

<details>
<summary><b>Load balancer</b> — 8 fields, 2 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `pool_capacity` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | Pool capacity means maximum number of pools which can be configured for all load balancer services. |
| `pool_member_capacity` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | Pool capacity means maximum number of pool members which can be configured for all load balancer services. |
| `results[].load_balancer_credit_capacity` | integer | 1 | – | Denominator or threshold; not a metric by itself | The load balancer credit capacity means the maximum credits which can be used for load balancer service configuration for all nodes. |
| `results[].pool_member_capacity` | integer | 1 | – | Denominator or threshold; not a metric by itself | This is a deprecated property. There is no LB pool member limit per edge node or per virtual network appliance anymore. For backward compat… |
| `service_usages[].pool_capacity` | integer | 1 | – | Denominator or threshold; not a metric by itself | Pool capacity means maximum number of pools which could be configured in the given load balancer service. |
| `service_usages[].pool_member_capacity` | integer | 1 | – | Denominator or threshold; not a metric by itself | Pool member capacity means maximum number of pool members which could be configured in the given load balancer service. |
| `service_usages[].virtual_server_capacity` | integer | 1 | – | Denominator or threshold; not a metric by itself | Virtual server capacity means maximum number of virtual servers which could be configured in the given load balancer service. |
| `virtual_server_capacity` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | Virtual server capacity means maximum number of virtual servers which can be configured for all load balancer services. |

</details>

<details>
<summary><b>Transport zone</b> — 7 fields, 3 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].node_status.system_status.disk_space_total` | integer | 3 | ✓ | Gauge; utilisation = used / total x 100 | Amount of disk space available on the system, in kilobytes. |
| `results[].node_status.system_status.disk_space_used` | integer | 3 | ✓ | Gauge; utilisation = used / total x 100 | Amount of disk space in use on the system, in kilobytes |
| `results[].node_status.system_status.edge_mem_usage.datapath_total_usage` | number | 3 | – | Denominator or threshold; not a metric by itself | Percentage of memory in use by datapath processes which includes RES and hugepage memory. |
| `results[].node_status.system_status.file_systems[].total` † | integer | 3 | ✓ | Gauge; utilisation = used / total x 100 | – |
| `results[].node_status.system_status.file_systems[].used` † | integer | 3 | ✓ | Gauge; utilisation = used / total x 100 | – |
| `results[].node_status.system_status.mem_total` | integer | 3 | ✓ | Denominator or threshold; not a metric by itself | Amount of RAM allocated to the system, in kilobytes |
| `results[].node_status.system_status.swap_total` | integer | 3 | ✓ | Denominator or threshold; not a metric by itself | Amount of disk available for swap, in kilobytes |

</details>

<details>
<summary><b>Capacity dashboard and limits</b> — 6 fields, 3 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].assigned_max_limit` | integer | 2 | – | Denominator or threshold; not a metric by itself | Assigned max workload count. |
| `capacity_usage[].max_supported_count` | integer | 1 | ✓ | Denominator or threshold; not a metric by itself | This is the maximum supported count for object type in consideration. |
| `capacity_usage[].max_threshold_percentage` | number | 1 | ✓ | Denominator or threshold; not a metric by itself | This indicates the maximum threshold percentage for object type. |
| `capacity_usage[].min_threshold_percentage` | number | 1 | ✓ | Denominator or threshold; not a metric by itself | This indicates the minimum threshold percentage for object type. |
| `meta_info.max_global_threshold_percentage` † | number | 1 | ✓ | Denominator or threshold; not a metric by itself | – |
| `meta_info.min_global_threshold_percentage` † | number | 1 | ✓ | Denominator or threshold; not a metric by itself | – |

</details>

<details>
<summary><b>Firewall policy and rule (DFW, gateway)</b> — 4 fields, 14 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].statistics.max_session_count` | integer | 7 | – | Denominator or threshold; not a metric by itself | Maximum value of sessions count of all rules of the type. This is aggregated statistic which are computed with lower frequency compared to… |
| `results[].statistics.results[].max_session_count` | integer | 7 | ✓ | Denominator or threshold; not a metric by itself | Maximum value of sessions count of all rules of the type. This is aggregated statistic which are computed with lower frequency compared to… |
| `results[].statistics.results[].total_session_count` | integer | 7 | ✓ | Denominator or threshold; not a metric by itself | Aggregated number of sessions processed by all the rules This is aggregated statistic which are computed with lower frequency compared to i… |
| `results[].statistics.total_session_count` | integer | 7 | – | Denominator or threshold; not a metric by itself | Aggregated number of sessions processed by all the rules This is aggregated statistic which are computed with lower frequency compared to i… |

</details>

<details>
<summary><b>Security services (IDFW, IDS/IPS)</b> — 4 fields, 10 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].statistics.max_session_count` | integer | 5 | – | Denominator or threshold; not a metric by itself | Maximum value of sessions count of all rules of the type. This is aggregated statistic which are computed with lower frequency compared to… |
| `results[].statistics.results[].max_session_count` | integer | 5 | – | Denominator or threshold; not a metric by itself | Maximum value of sessions count of all rules of the type. This is aggregated statistic which are computed with lower frequency compared to… |
| `results[].statistics.results[].total_session_count` | integer | 5 | – | Denominator or threshold; not a metric by itself | Aggregated number of sessions processed by all the rules This is aggregated statistic which are computed with lower frequency compared to i… |
| `results[].statistics.total_session_count` | integer | 5 | – | Denominator or threshold; not a metric by itself | Aggregated number of sessions processed by all the rules This is aggregated statistic which are computed with lower frequency compared to i… |

</details>

<details>
<summary><b>Other platform status</b> — 3 fields, 3 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `ip_pool_stats[].allocated_number` | integer | 3 | – | Denominator or threshold; not a metric by itself | allocated number. COULD BE INACCURATE, REFERENCE ONLY. |
| `ip_pool_stats[].allocated_percentage` | integer | 3 | – | Denominator or threshold; not a metric by itself | allocated percentage. COULD BE INACCURATE, REFERENCE ONLY. |
| `ip_pool_stats[].pool_size` | integer | 3 | – | Denominator or threshold; not a metric by itself | pool size |

</details>

<details>
<summary><b>IP address management (IP blocks)</b> — 2 fields, 3 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `projects[].vpc_subnets[].size` | integer | 2 | – | Denominator or threshold; not a metric by itself | This contains size of VPC subnets |
| `ip_blocks[].total` | integer | 1 | – | Denominator or threshold; not a metric by itself | Total ip address space |

</details>

<details>
<summary><b>VPN (IPsec, L2VPN)</b> — 1 fields, 5 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `session_summary.total_sessions` | integer | 5 | – | Denominator or threshold; not a metric by itself | The total number of IPSec VPN sessions configured. |

</details>

<!-- END GENERATED: capacity -->
