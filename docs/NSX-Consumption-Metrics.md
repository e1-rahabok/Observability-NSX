# NSX consumption metrics

Consumption metrics tell you **how much of a resource is in use**: CPU, memory, packet and bit rates, sessions, flows, objects, and how much of a fixed limit is taken. They answer "how busy is it?", not "is it failing?" (contention) or "is it up?" (availability).

- Disk space is **not** here. It is a capacity measure and lives in [Capacity](NSX-Capacity-Metrics.md).
- Companion guides: [Formulas and conventions](NSX-Metrics-Formulas.md) · [Contention](NSX-Contention-Metrics.md) · [Capacity](NSX-Capacity-Metrics.md) · [Availability and events](NSX-Availability-Metrics-and-Events.md)
- Lab: `nsxman1`, NSX 9.1.1.0, 3 ESXi hosts, no Edge, no segments, no gateways. Crawl 2026-10-19.
- Open questions: [NSX-Open-Questions.md](NSX-Open-Questions.md), numbered D1 to D18 and referred to by number in this guide.
- Evidence tags: **[Lab]**, **[Doc]**, **[Derived]**, **[Open]** (see the [formulas guide](NSX-Metrics-Formulas.md)).

---

## 1. Types of consumption metric

| Type | Field pattern | Example | How to use it |
|---|---|---|---|
| **Utilisation %** | `usage`, `used`, `percent`, `pct` | `current_usage_percentage`, `cpu_usage` | Use directly, or divide used by total |
| **Rate, NSX-computed** | `pps`, `mbps`, `eps` | `vnic_rxpps`, `pnic_txmbps`, `fastpath_flow_hit_pps` | Use directly. Sample window is set by NSX. |
| **Rate, from a counter** | `bytes`, `packets`, `pkts` (cumulative) | `rx_bytes`, `tx_packets`, `packet_count` | Δ ÷ Δt |
| **Level** | `cpu_cores`, `load_average`, `mem_*`, `num_*` | `load_average[]`, `mem_used`, `num_vnics` | Use directly, with a total where one exists |
| **Object count** | `count`, `_count`, `service_count` | `service_count`, `member_count` | Use directly. Compare to a limit in [Capacity](NSX-Capacity-Metrics.md). |
| **Hit count** | `hit`, `hits`, `session_count` | DFW `hit_count`, `session_count` | Cumulative. Use Δ ÷ Δt. |

---

## 2. Formulas by object type

| Object type | Metric | Formula | Lab value | Basis |
|---|---|---|---|---|
| **NSX Manager node** | Memory used % | `mem_used ÷ mem_total × 100` | 82.4% | [Lab]. `mem_used = mem_total − mem_available` exactly. |
| | CPU load per core | `load_average[0] ÷ cpu_cores` | 0.21 | [Derived] |
| | Top process CPU and memory | `top_process_by_cpu_list[].cpu_usage`, `…_by_mem_list[].memory_usage` | — | [Doc] field names. Lab: observed. |
| | NIC throughput | `Δrx_bytes × 8 ÷ Δt` | — | [Derived] |
| **ESXi host transport node** | Memory used % | `node_status.system_status.mem_used ÷ mem_total × 100` | 43.6% | [Lab] |
| | Load per core | `load_average[0] ÷ cpu_cores` | 0.009 (0.5 ÷ 56) | [Derived] |
| | Datapath throughput | `packet_stats.*_pps` (NSX rate) | — | [Lab] field names |
| | Physical NIC rate | `pnic_rxmbps`, `pnic_txmbps` | 53.8 and 118.2 Mb/s | [Lab] |
| | Physical NIC utilisation % | `(pnic_rxmbps + pnic_txmbps) ÷ link speed × 100` | needs link speed | [Open]. Link speed not found (D6). |
| | Virtual NIC rate | `vnic_rxpps`, `vnic_txpps`, `vnic_rxmbps`, `vnic_txmbps` | 2,480 and 2,537 pps; 10.5 and 11.1 Mb/s | [Lab] |
| | Fast-path load | `fastpath_flow_hit_pps` + `fastpath_flow_miss_pps` | 37,745.8 pps total | [Lab] |
| | Overlay packets | `overlay_*` rates | 0 in sample | [Lab] |
| | Agents up | `agent_status.up_count` | 17 | [Lab] |
| | Interface rate | `Δrx_bytes × 8 ÷ Δt`, `Δtx_bytes × 8 ÷ Δt` | — | [Derived] |
| **Edge node** (no Edge in lab) | Datapath CPU per core | Per-core values over the last 100 ms, CPU sampled over 60 s | — | [Doc]. CPU % formula not stated (D5). |
| | Flow-cache hit ratio | `hits ÷ (hits + misses) × 100` | — | [Derived]. Counters reset on Edge reboot. |
| | Flow-table occupancy | `fast_path_sys_stats.host_enhanced_fastpath.flow_table_occupancy_*_pct` (histogram buckets) | not in lab response | In the host `statistics/monitor` spec. The lab's hosts do not return this subtree, so it is untested here. |
| | Load-balancer pool use | `pool_usage_percentage`, `pool_member_usage_percentage` | field present | [Lab] field returned by `lb-service-usage-summary`. The lab has no load-balancer service, so values are not tested. |
| **DFW rule** | New-session rate | `Δsession_count ÷ Δt` | — | [Derived] |
| | Rule activity | `hit_count`, `packet_count`, `byte_count` (cumulative) | 0 in lab | [Doc] meaning, [Lab] zero |
| | Popularity | `session_count ÷ age of rule` | — | [Doc]. Age unit not stated (D11). |
| **Transport zone, transport node set** | Node counts by state | `up_count`, `down_count`, `degraded_count`, `unknown_count` | — | [Derived] for shares |
| **Capacity dashboard** | Object usage % | `current_usage_count ÷ max_supported_count × 100` | 48.82% (Services) | [Lab] |
| **Tunnels, BFD** | Session counts | `bfd_up_count`, `bfd_down_count`, … | all 0 on hosts | [Lab]. Counts are zero while status is UP (D9). |

---

## 3. Lab readings (2026-10-19)

| Object | Reading | Value |
|---|---|---|
| NSX Manager | Memory used | **82.4%** (below 90% high alarm) |
| NSX Manager | Load per core | **0.21** (1.27 on 6 cores, 1-minute load) |
| ESXi host | Memory used | **43.6%** |
| ESXi host | Load per core | **0.009** |
| ESXi host | Virtual NIC | 2,480 rx pps and 2,537 tx pps; 10.5 rx Mb/s and 11.1 tx Mb/s |
| ESXi host | Physical NIC | 5,832 rx pps and 6,401 tx pps; 53.8 rx Mb/s and 118.2 tx Mb/s |
| ESXi host | Fast-path flow hits | 37,524.9 pps |
| ESXi host | Inventory in the same statistics | 4 pNICs and 8 vNICs (`number_of_pnics`, `number_of_vnics`) |
| Capacity | Services | 415 of 850 (48.82%) |
| Capacity | Groups | 258 of 3,000 (8.6%) |
| Capacity | Geo IP groups | 249 of 1,000 (24.9%) |
| Capacity | Hypervisor hosts | 3 of 64 (4.68%) |
| Capacity | Compute managers | **1 of 1 (100%), WARNING** |

**Reading the physical NIC numbers.** 118 Mb/s out and 54 Mb/s in is well under a 10 Gb/s link, but without the link speed the utilisation percentage cannot be computed ([Open], D6). Once the link speed is known, use the formula in section 2.

---

## 4. Full lists by object type

Generated from [`data/nsx-metric-fields.csv`](data/nsx-metric-fields.csv) by `tools/build_metric_docs.py`. Column meanings are in the [contention guide, section 6](NSX-Contention-Metrics.md#6-full-lists-by-object-type).

<!-- BEGIN GENERATED: consumption -->
<details>
<summary><b>Transport node (ESXi host or Edge)</b> — 211 fields, 12 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `rx_bytes` | integer | 4 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of bytes received on the interface since the uptime. This will be reset on transport node restart. |
| `rx_packets` | integer | 4 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of incoming packets on the interface since the uptime. This will be reset on transport node restart. |
| `tx_bytes` | integer | 4 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of bytes transmitted from the interface since the uptime. This will be reset on transport node restart. |
| `tx_packets` | integer | 4 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of outgoing packets transmitted from the interface since the uptime. This will be reset on transport node restart. |
| `results[].node_status.system_status.cpu_usage.avg_cpu_core_usage_dpdk` | number | 3 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all DPDK cores in percentage. |
| `results[].node_status.system_status.cpu_usage.avg_cpu_core_usage_non_dpdk` | number | 3 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all non-DPDK cores in percentage. |
| `results[].node_status.system_status.cpu_usage.highest_cpu_core_usage_dpdk` | number | 3 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest CPU utilization value among DPDK cores in percentage. |
| `results[].node_status.system_status.cpu_usage.highest_cpu_core_usage_non_dpdk` | number | 3 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest cpu utilization value among non_dpdk cores in percentage. |
| `results[].node_status.system_status.edge_mem_usage.cache_usage` | number | 3 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM on the system that can be flushed out to disk. |
| `results[].node_status.system_status.edge_mem_usage.swap_usage` | number | 3 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of swap disk in use. |
| `results[].node_status.system_status.edge_mem_usage.system_mem_usage` | number | 3 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM in use on edge node. |
| `results[].node_status.system_status.load_average[]` | number | 3 | ✓ | Gauge: instantaneous value | – |
| `results[].node_status.system_status.mem_cache` | integer | 3 | ✓ | Gauge: instantaneous value | Amount of RAM on the system that can be flushed out to disk, in kilobytes |
| `results[].node_status.system_status.mem_used` | integer | 3 | ✓ | Gauge; utilisation = used / total x 100 where total is available | Amount of RAM in use on the system, in kilobytes |
| `results[].node_status.system_status.swap_used` | integer | 3 | ✓ | Gauge; utilisation = used / total x 100 where total is available | Amount of swap disk in use, in kilobytes |
| `agent_status.agents[].resource_usage.cpu_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | The Agent's share of the elapsed CPU time since the last screen update, expressed as a percentage of total CPU time. |
| `agent_status.agents[].resource_usage.memory_used` | integer | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Used memory in kilobytes. |
| `fast_path_lcore_usage_stats.lcore_rank_01_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 1 Lcore usage. |
| `fast_path_lcore_usage_stats.lcore_rank_02_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 2 Lcore usage. |
| `fast_path_lcore_usage_stats.lcore_rank_03_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 3 Lcore usage. |
| `fast_path_lcore_usage_stats.lcore_rank_04_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 4 Lcore usage. |
| `fast_path_lcore_usage_stats.lcore_rank_05_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 5 Lcore usage. |
| `fast_path_lcore_usage_stats.lcore_rank_06_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 6 Lcore usage. |
| `fast_path_lcore_usage_stats.lcore_rank_07_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 7 Lcore usage. |
| `fast_path_lcore_usage_stats.lcore_rank_08_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 8 Lcore usage. |
| `fast_path_lcore_usage_stats.lcore_rank_09_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 9 Lcore usage. |
| `fast_path_lcore_usage_stats.lcore_rank_10_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 10 Lcore usage. |
| `fast_path_lcore_usage_stats.lcore_rank_11_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 11 Lcore usage. |
| `fast_path_lcore_usage_stats.lcore_rank_12_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 12 Lcore usage. |
| `fast_path_lcore_usage_stats.lcore_rank_13_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 13 Lcore usage. |
| `fast_path_lcore_usage_stats.lcore_rank_14_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 14 Lcore usage. |
| `fast_path_lcore_usage_stats.lcore_rank_15_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 15 Lcore usage. |
| `fast_path_lcore_usage_stats.lcore_rank_16_lcore_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Rank 16 Lcore usage. |
| `fast_path_sys_stats.host_enhanced_fastpath.flow_table_occupancy_0_pct` | integer | 2 | – | NSX-computed percentage | The number of flow tables in which up to 25% of entries are filled. |
| `fast_path_sys_stats.host_enhanced_fastpath.flow_table_occupancy_25_pct` | integer | 2 | – | NSX-computed percentage | The number of flow tables in which 25-50% of entries are filled. |
| `fast_path_sys_stats.host_enhanced_fastpath.flow_table_occupancy_50_pct` | integer | 2 | – | NSX-computed percentage | The number of flow tables in which 50-75% of entries are filled. |
| `fast_path_sys_stats.host_enhanced_fastpath.flow_table_occupancy_75_pct` | integer | 2 | – | NSX-computed percentage | The number of flow tables in which 75-90% of entries are filled. |
| `fast_path_sys_stats.host_enhanced_fastpath.flow_table_occupancy_90_pct` | integer | 2 | – | NSX-computed percentage | The number of flow tables in which 90-95% of entries are filled. |
| `fast_path_sys_stats.host_enhanced_fastpath.flow_table_occupancy_95_pct` | integer | 2 | – | NSX-computed percentage | The number of flow tables in which 95% of entries are filled. |
| `fast_path_sys_stats.host_enhanced_fastpath.hits` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of flow hits. |
| `fast_path_sys_stats.host_enhanced_fastpath.num_flows` | integer | 2 | – | Gauge: instantaneous value | Total number of flows in all flow tables. |
| `fast_path_sys_stats.host_enhanced_fastpath.num_flows_created` | integer | 2 | – | Gauge: instantaneous value | Total number of flows created. |
| `fast_path_sys_stats.host_standard_fastpath.flow_table_occupancy_0_pct` | integer | 2 | – | NSX-computed percentage | The number of flow tables in which up to 25% of entries are filled. |
| `fast_path_sys_stats.host_standard_fastpath.flow_table_occupancy_25_pct` | integer | 2 | – | NSX-computed percentage | The number of flow tables in which 25-50% of entries are filled. |
| `fast_path_sys_stats.host_standard_fastpath.flow_table_occupancy_50_pct` | integer | 2 | – | NSX-computed percentage | The number of flow tables in which 50-75% of entries are filled. |
| `fast_path_sys_stats.host_standard_fastpath.flow_table_occupancy_75_pct` | integer | 2 | – | NSX-computed percentage | The number of flow tables in which 75-90% of entries are filled. |
| `fast_path_sys_stats.host_standard_fastpath.flow_table_occupancy_90_pct` | integer | 2 | – | NSX-computed percentage | The number of flow tables in which 90-95% of entries are filled. |
| `fast_path_sys_stats.host_standard_fastpath.flow_table_occupancy_95_pct` | integer | 2 | – | NSX-computed percentage | The number of flow tables in which 95% of entries are filled. |
| `fast_path_sys_stats.host_standard_fastpath.hits` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of flow hits. |
| `fast_path_sys_stats.host_standard_fastpath.num_flows` | integer | 2 | – | Gauge: instantaneous value | Total number of flows in all flow tables. |
| `fast_path_sys_stats.host_standard_fastpath.num_flows_created` | integer | 2 | – | Gauge: instantaneous value | Total number of flows created. |
| `node_status.system_status.cpu_usage.avg_cpu_core_usage_dpdk` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all DPDK cores in percentage. |
| `node_status.system_status.cpu_usage.avg_cpu_core_usage_non_dpdk` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all non-DPDK cores in percentage. |
| `node_status.system_status.cpu_usage.highest_cpu_core_usage_dpdk` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest CPU utilization value among DPDK cores in percentage. |
| `node_status.system_status.cpu_usage.highest_cpu_core_usage_non_dpdk` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest cpu utilization value among non_dpdk cores in percentage. |
| `node_status.system_status.dfw_heap_memory_usage[].usage_pct` | number | 2 | ✓ | NSX-computed percentage | Percentage of heap utilized for specific heap. |
| `node_status.system_status.dfw_heap_memory_usage[].used_mb` | integer | 2 | ✓ | Gauge; utilisation = used / total x 100 where total is available | Utilized size of heap for the specified heap in mb units. |
| `node_status.system_status.dpus[].load_average[]` | number | 2 | – | Gauge: instantaneous value | – |
| `node_status.system_status.dpus[].mem_cache` | integer | 2 | – | Gauge: instantaneous value | Amount of RAM on the system that can be flushed out to disk, in kilobytes. |
| `node_status.system_status.dpus[].mem_used` | integer | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Amount of RAM in use on the system, in kilobytes. |
| `node_status.system_status.edge_mem_usage.cache_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM on the system that can be flushed out to disk. |
| `node_status.system_status.edge_mem_usage.datapath_mem_usage_details.datapath_heap_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of heap memory in use. |
| `node_status.system_status.edge_mem_usage.datapath_mem_usage_details.highest_datapath_mem_pool_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Highest percentage usage value among datapath memory pools. |
| `node_status.system_status.edge_mem_usage.swap_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of swap disk in use. |
| `node_status.system_status.edge_mem_usage.system_mem_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM in use on edge node. |
| `node_status.system_status.load_average[]` | number | 2 | ✓ | Gauge: instantaneous value | – |
| `node_status.system_status.mem_cache` | integer | 2 | ✓ | Gauge: instantaneous value | Amount of RAM on the system that can be flushed out to disk, in kilobytes |
| `node_status.system_status.mem_used` | integer | 2 | ✓ | Gauge; utilisation = used / total x 100 where total is available | Amount of RAM in use on the system, in kilobytes |
| `node_status.system_status.swap_used` | integer | 2 | ✓ | Gauge; utilisation = used / total x 100 where total is available | Amount of swap disk in use, in kilobytes |
| `platform_cpu_usage_stats.host_pcpu.hist_0_pct` | integer | 2 | – | NSX-computed percentage | Number of (V)CPUs with utilization between 0% and 50%. |
| `platform_cpu_usage_stats.host_pcpu.hist_50_pct` | integer | 2 | – | NSX-computed percentage | Number of (V)CPUs with utilization between 50% and 75%. |
| `platform_cpu_usage_stats.host_pcpu.hist_75_pct` | integer | 2 | – | NSX-computed percentage | Number of (V)CPUs with utilization between 75% and 85%. |
| `platform_cpu_usage_stats.host_pcpu.hist_85_pct` | integer | 2 | – | NSX-computed percentage | Number of (V)CPUs with utilization between 85% and 90%. |
| `platform_cpu_usage_stats.host_pcpu.hist_90_pct` | integer | 2 | – | NSX-computed percentage | Number of (V)CPUs with utilization between 90% and 95%. |
| `platform_cpu_usage_stats.host_pcpu.hist_95_pct` | integer | 2 | – | NSX-computed percentage | Number of (V)CPUs with utilization > 95%. |
| `platform_cpu_usage_stats.host_vcpu.hist_0_pct` | integer | 2 | – | NSX-computed percentage | Number of (V)CPUs with utilization between 0% and 50%. |
| `platform_cpu_usage_stats.host_vcpu.hist_50_pct` | integer | 2 | – | NSX-computed percentage | Number of (V)CPUs with utilization between 50% and 75%. |
| `platform_cpu_usage_stats.host_vcpu.hist_75_pct` | integer | 2 | – | NSX-computed percentage | Number of (V)CPUs with utilization between 75% and 85%. |
| `platform_cpu_usage_stats.host_vcpu.hist_85_pct` | integer | 2 | – | NSX-computed percentage | Number of (V)CPUs with utilization between 85% and 90%. |
| `platform_cpu_usage_stats.host_vcpu.hist_90_pct` | integer | 2 | – | NSX-computed percentage | Number of (V)CPUs with utilization between 90% and 95%. |
| `platform_cpu_usage_stats.host_vcpu.hist_95_pct` | integer | 2 | – | NSX-computed percentage | Number of (V)CPUs with utilization > 95%. |
| `platform_packet_stats.host_uplink.num_pnics` | integer | 2 | – | Gauge: instantaneous value | Number of PNICs in the host. |
| `platform_packet_stats.host_uplink.rxeps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | RX drop rate (including errors). |
| `platform_packet_stats.host_uplink.rxmbps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | RX throughput. |
| `platform_packet_stats.host_uplink.rxpps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | RX packet rate. |
| `platform_packet_stats.host_uplink.txeps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | TX drop rate (including errors). |
| `platform_packet_stats.host_uplink.txmbps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | TX throughput. |
| `platform_packet_stats.host_uplink.txpps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | TX packet rate. |
| `platform_packet_stats.host_vnic.num_vnics` | integer | 2 | – | Gauge: instantaneous value | Number of VNICs in the host. |
| `platform_packet_stats.host_vnic.rxeps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | RX drop rate (including errors). |
| `platform_packet_stats.host_vnic.rxmbps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | RX throughput. |
| `platform_packet_stats.host_vnic.rxpps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | RX packet rate. |
| `platform_packet_stats.host_vnic.txeps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | TX drop rate (including errors). |
| `platform_packet_stats.host_vnic.txmbps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | TX throughput. |
| `platform_packet_stats.host_vnic.txpps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | TX packet rate. |
| `queues[].rx_bytes` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of incoming packet bytes received in the queue. The counts are from the time the edge dataplane is UP and will be reset on… |
| `queues[].rx_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of incoming packets in the queue. The counts are from the time the edge dataplane is UP and will be reset on edge reboot o… |
| `queues[].tx_bytes` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of outgoing packet bytes transmitted from the queue. The counts are from the time the edge dataplane is UP and will be res… |
| `queues[].tx_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of outgoing packets transmitted from the queue. The counts are from the time the edge dataplane is UP and will be reset on… |
| `rx_frame` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total framing error packets since the uptime. Available only for Host Transport Node. |
| `scrx_stats.host_scrx.vnic_rxeps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | vnic_rxeps |
| `scrx_stats.host_scrx.vnic_rxpps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | vnic_rxpps |
| `scrx_stats.host_scrx.vnic_txeps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | vnic_txeps |
| `scrx_stats.host_scrx.vnic_txpps` | number | 2 | – | NSX-computed per-second rate (no delta needed) | vnic_txpps |
| `tx_colls` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets for collisions detected on transmit. Available only for Host Transport Node. |
| `cpu_usage.avg_cpu_core_usage_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all DPDK cores in percentage. |
| `cpu_usage.avg_cpu_core_usage_non_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all non-DPDK cores in percentage. |
| `cpu_usage.highest_cpu_core_usage_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest CPU utilization value among DPDK cores in percentage. |
| `cpu_usage.highest_cpu_core_usage_non_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest cpu utilization value among non_dpdk cores in percentage. |
| `dfw_heap_memory_usage[].peak_ever` | number | 1 | – | Gauge: instantaneous value | Number of times peak threshold reached for specific heap. |
| `dfw_heap_memory_usage[].usage_pct` | number | 1 | – | NSX-computed percentage | Percentage of heap utilized for specific heap. |
| `dfw_heap_memory_usage[].used_mb` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Utilized size of heap for the specified heap in mb units. |
| `dpus[].load_average[]` | number | 1 | – | Gauge: instantaneous value | – |
| `dpus[].mem_cache` | integer | 1 | – | Gauge: instantaneous value | Amount of RAM on the system that can be flushed out to disk, in kilobytes. |
| `dpus[].mem_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Amount of RAM in use on the system, in kilobytes. |
| `edge_mem_usage.cache_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM on the system that can be flushed out to disk. |
| `edge_mem_usage.datapath_mem_usage_details.datapath_heap_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of heap memory in use. |
| `edge_mem_usage.datapath_mem_usage_details.datapath_mem_pools_usage[].usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of memory pool in use. |
| `edge_mem_usage.datapath_mem_usage_details.highest_datapath_mem_pool_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Highest percentage usage value among datapath memory pools. |
| `edge_mem_usage.swap_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of swap disk in use. |
| `edge_mem_usage.system_mem_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM in use on edge node. |
| `load_average[]` | number | 1 | – | Gauge: instantaneous value | – |
| `mem_available` | integer | 1 | – | Gauge: instantaneous value | Amount of available RAM in the system, in kilobytes. The amount of reclaimable buffer/cache memory in use is taken into consideration here… |
| `mem_buffer` | integer | 1 | – | Gauge: instantaneous value | Amount of RAM on the system used for temporary disk block storage, in kilobytes |
| `mem_cache` | integer | 1 | – | Gauge: instantaneous value | Amount of RAM on the system that can be flushed out to disk, in kilobytes |
| `mem_free` | integer | 1 | – | Gauge: instantaneous value | Amount of unused RAM in the system, in kilobytes |
| `mem_slab` | integer | 1 | – | Gauge: instantaneous value | Amount of RAM allocated to the kernel slab allocator, in kilobytes |
| `mem_slab_reclaimable` | integer | 1 | – | Gauge: instantaneous value | Amount of RAM allocated to the kernel slab allocator that is not currently in use, in kilobytes |
| `mem_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Amount of RAM in use on the system, in kilobytes. (This is mem_total - mem_available) |
| `packet_stats.local_workloads_transmitted_received_broadcast_packets.broadcast_rxpps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | Broadcast RX packet rate. |
| `packet_stats.local_workloads_transmitted_received_broadcast_packets.broadcast_txpps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | Broadcast TX packet rate. |
| `packet_stats.local_workloads_transmitted_received_multicast_packets.multicast_rxpps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | Multicast RX packet rate. |
| `packet_stats.local_workloads_transmitted_received_multicast_packets.multicast_txpps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | Multicast TX packet rate. |
| `packet_stats.local_workloads_transmitted_received_packets.vnic_rxeps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | RX drop rate (including errors). |
| `packet_stats.local_workloads_transmitted_received_packets.vnic_rxmbps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | RX throughput. |
| `packet_stats.local_workloads_transmitted_received_packets.vnic_rxpps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | RX packet rate. |
| `packet_stats.local_workloads_transmitted_received_packets.vnic_txeps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | TX drop rate (including errors). |
| `packet_stats.local_workloads_transmitted_received_packets.vnic_txmbps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | TX throughput. |
| `packet_stats.local_workloads_transmitted_received_packets.vnic_txpps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | TX packet rate. |
| `packet_stats.overlay_datapath_l2.arp_proxy_resp_unknown` | integer | 1 | ✓ | Gauge: instantaneous value | Count of unknown IP-MAC binding message from CCP for ARP suppression. |
| `packet_stats.overlay_datapath_l2.uplink_rx_skip_mac_learn` | integer | 1 | ✓ | Gauge: instantaneous value | Count of packets for which MAC learn was skipped at uplink input IOChain. |
| `packet_stats.packet_processing_efficiency_watch.fastpath_flow_hit_pps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | Rate of flow hits. |
| `packet_stats.packet_processing_efficiency_watch.fastpath_slowpath_only_pps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | Packet rate for packets that are always targeted to be processed by slowpath such as broadcast packets. |
| `packet_stats.pnics_transmitted_received_packets.pnic_rxeps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | RX drop rate (including errors). |
| `packet_stats.pnics_transmitted_received_packets.pnic_rxmbps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | RX throughput. |
| `packet_stats.pnics_transmitted_received_packets.pnic_rxpps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | RX packet rate. |
| `packet_stats.pnics_transmitted_received_packets.pnic_txeps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | TX drop rate (including errors). |
| `packet_stats.pnics_transmitted_received_packets.pnic_txmbps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | TX throughput. |
| `packet_stats.pnics_transmitted_received_packets.pnic_txpps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | TX packet rate. |
| `packet_stats.switch_security.rx_bcast_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received broadcast packets. |
| `packet_stats.switch_security.rx_mcast_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received multicast packets. |
| `packet_stats.switch_security.tx_bcast_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent broadcast packets |
| `packet_stats.switch_security.tx_ddhcp_ipv4_nak_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | tx ddhcp ipv4 nak pkts. |
| `packet_stats.switch_security.tx_mcast_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent multicast packets. |
| `platform_cpu_usage_stats.host_net_thread_all.hist_0_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 0% and 25%. |
| `platform_cpu_usage_stats.host_net_thread_all.hist_25_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 25% and 50%. |
| `platform_cpu_usage_stats.host_net_thread_all.hist_50_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 50% and 70%. |
| `platform_cpu_usage_stats.host_net_thread_all.hist_70_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 70% and 80%. |
| `platform_cpu_usage_stats.host_net_thread_all.hist_80_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 80% and 85%. |
| `platform_cpu_usage_stats.host_net_thread_all.hist_85_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 85% and 90%. |
| `platform_cpu_usage_stats.host_net_thread_all.hist_90_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 90% and 95%. |
| `platform_cpu_usage_stats.host_net_thread_all.hist_95_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 95% and 97%. |
| `platform_cpu_usage_stats.host_net_thread_all.hist_97_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 97% and 99%. |
| `platform_cpu_usage_stats.host_net_thread_all.hist_99_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization > 99%. |
| `platform_cpu_usage_stats.host_net_thread_all.min_cpu` | number | 1 | – | Gauge: instantaneous value | Minimum CPU utilization of network threads in the group. |
| `platform_cpu_usage_stats.host_net_thread_all.num_threads` | integer | 1 | – | Gauge: instantaneous value | Number of network threads in the group. |
| `platform_cpu_usage_stats.host_net_thread_nioc.hist_0_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 0% and 25%. |
| `platform_cpu_usage_stats.host_net_thread_nioc.hist_25_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 25% and 50%. |
| `platform_cpu_usage_stats.host_net_thread_nioc.hist_50_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 50% and 70%. |
| `platform_cpu_usage_stats.host_net_thread_nioc.hist_70_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 70% and 80%. |
| `platform_cpu_usage_stats.host_net_thread_nioc.hist_80_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 80% and 85%. |
| `platform_cpu_usage_stats.host_net_thread_nioc.hist_85_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 85% and 90%. |
| `platform_cpu_usage_stats.host_net_thread_nioc.hist_90_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 90% and 95%. |
| `platform_cpu_usage_stats.host_net_thread_nioc.hist_95_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 95% and 97%. |
| `platform_cpu_usage_stats.host_net_thread_nioc.hist_97_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 97% and 99%. |
| `platform_cpu_usage_stats.host_net_thread_nioc.hist_99_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization > 99%. |
| `platform_cpu_usage_stats.host_net_thread_nioc.min_cpu` | number | 1 | – | Gauge: instantaneous value | Minimum CPU utilization of network threads in the group. |
| `platform_cpu_usage_stats.host_net_thread_nioc.num_threads` | integer | 1 | – | Gauge: instantaneous value | Number of network threads in the group. |
| `platform_cpu_usage_stats.host_net_thread_rx.hist_0_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 0% and 25%. |
| `platform_cpu_usage_stats.host_net_thread_rx.hist_25_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 25% and 50%. |
| `platform_cpu_usage_stats.host_net_thread_rx.hist_50_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 50% and 70%. |
| `platform_cpu_usage_stats.host_net_thread_rx.hist_70_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 70% and 80%. |
| `platform_cpu_usage_stats.host_net_thread_rx.hist_80_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 80% and 85%. |
| `platform_cpu_usage_stats.host_net_thread_rx.hist_85_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 85% and 90%. |
| `platform_cpu_usage_stats.host_net_thread_rx.hist_90_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 90% and 95%. |
| `platform_cpu_usage_stats.host_net_thread_rx.hist_95_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 95% and 97%. |
| `platform_cpu_usage_stats.host_net_thread_rx.hist_97_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 97% and 99%. |
| `platform_cpu_usage_stats.host_net_thread_rx.hist_99_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization > 99%. |
| `platform_cpu_usage_stats.host_net_thread_rx.min_cpu` | number | 1 | – | Gauge: instantaneous value | Minimum CPU utilization of network threads in the group. |
| `platform_cpu_usage_stats.host_net_thread_rx.num_threads` | integer | 1 | – | Gauge: instantaneous value | Number of network threads in the group. |
| `platform_cpu_usage_stats.host_net_thread_tx.hist_0_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 0% and 25%. |
| `platform_cpu_usage_stats.host_net_thread_tx.hist_25_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 25% and 50%. |
| `platform_cpu_usage_stats.host_net_thread_tx.hist_50_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 50% and 70%. |
| `platform_cpu_usage_stats.host_net_thread_tx.hist_70_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 70% and 80%. |
| `platform_cpu_usage_stats.host_net_thread_tx.hist_80_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 80% and 85%. |
| `platform_cpu_usage_stats.host_net_thread_tx.hist_85_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 85% and 90%. |
| `platform_cpu_usage_stats.host_net_thread_tx.hist_90_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 90% and 95%. |
| `platform_cpu_usage_stats.host_net_thread_tx.hist_95_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 95% and 97%. |
| `platform_cpu_usage_stats.host_net_thread_tx.hist_97_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization between 97% and 99%. |
| `platform_cpu_usage_stats.host_net_thread_tx.hist_99_pct` | integer | 1 | – | NSX-computed percentage | Number of network threads in the group with CPU utilization > 99%. |
| `platform_cpu_usage_stats.host_net_thread_tx.min_cpu` | number | 1 | – | Gauge: instantaneous value | Minimum CPU utilization of network threads in the group. |
| `platform_cpu_usage_stats.host_net_thread_tx.num_threads` | integer | 1 | – | Gauge: instantaneous value | Number of network threads in the group. |
| `scrx_stats.host_scrx.datapath_rx_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | datapath_rx_pkts |
| `scrx_stats.host_scrx.datapth_tx_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | datapth_tx_pkts |
| `scrx_stats.host_scrx.service_datapath_cpu_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | service_datapath_cpu_usage |
| `scrx_stats.host_scrx.service_datapath_free_memory` | integer | 1 | – | Gauge: instantaneous value | service_datapath_free_memory |
| `scrx_stats.host_scrx.service_datapath_rx_idps_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | service_datapath_rx_idps_pkts |
| `scrx_stats.host_scrx.service_datapath_rx_l7_fw_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | service_datapath_rx_l7_fw_pkts |
| `scrx_stats.host_scrx.service_datapath_rx_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | service_datapath_rx_pkts |
| `scrx_stats.host_scrx.service_datapath_tx_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | service_datapath_tx_pkts |
| `swap_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Amount of swap disk in use, in kilobytes |

</details>

<details>
<summary><b>VPC and subnet</b> — 80 fields, 9 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `distributed_dhcp_server_packets.acks` | integer | 2 | – | Gauge: instantaneous value | The total number of DHCP ACK packets. |
| `distributed_dhcp_server_packets.declines` | integer | 2 | – | Gauge: instantaneous value | The total number of DHCP DECLINE packets. |
| `distributed_dhcp_server_packets.discovers` | integer | 2 | – | Gauge: instantaneous value | The total number of DHCP DISCOVER packets. |
| `distributed_dhcp_server_packets.informs` | integer | 2 | – | Gauge: instantaneous value | The total number of DHCP INFORM packets. |
| `distributed_dhcp_server_packets.nacks` | integer | 2 | – | Gauge: instantaneous value | The total number of DHCP NACK packets. |
| `distributed_dhcp_server_packets.offers` | integer | 2 | – | Gauge: instantaneous value | The total number of DHCP OFFER packets. |
| `distributed_dhcp_server_packets.releases` | integer | 2 | – | Gauge: instantaneous value | The total number of DHCP RELEASE packets. |
| `distributed_dhcp_server_packets.requests` | integer | 2 | – | Gauge: instantaneous value | The total number of DHCP REQUEST packets. |
| `dropped_by_security_packets.spoof_guard_dropped[].counter` | integer | 2 | – | Gauge: instantaneous value | The number of packets. |
| `mac_learning.mac_not_learned_packets_allowed` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of packets with unknown source MAC address that are dispatched without learning the source MAC address. Applicable only when the… |
| `mac_learning.macs_learned` | integer | 2 | – | Gauge: instantaneous value | Number of MACs learned |
| `results[].statistics.byte_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of bytes processed by the rule. |
| `results[].statistics.hit_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of hits received by the rule. |
| `results[].statistics.l7_accept_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Accepted counters received by the rule. |
| `results[].statistics.packet_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of packets processed by the rule. |
| `results[].statistics.results[].byte_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of bytes processed by the rule. |
| `results[].statistics.results[].hit_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of hits received by the rule. |
| `results[].statistics.results[].l7_accept_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Accepted counters received by the rule. |
| `results[].statistics.results[].packet_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of packets processed by the rule. |
| `results[].statistics.results[].session_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of sessions processed by the rule. |
| `results[].statistics.session_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of sessions processed by the rule. |
| `rx_bytes.multicast_broadcast` | integer | 2 | – | Gauge: instantaneous value | The multicast and broadcast packets or bytes |
| `rx_packets.multicast_broadcast` | integer | 2 | – | Gauge: instantaneous value | The multicast and broadcast packets or bytes |
| `tx_bytes.multicast_broadcast` | integer | 2 | – | Gauge: instantaneous value | The multicast and broadcast packets or bytes |
| `tx_packets.multicast_broadcast` | integer | 2 | – | Gauge: instantaneous value | The multicast and broadcast packets or bytes |
| `external_traffic.rx.blocked_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of blocked packets |
| `external_traffic.rx.error_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of error packets |
| `external_traffic.tx.blocked_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of blocked packets |
| `external_traffic.tx.error_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of error packets |
| `gateway_interface.rx.blocked_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `gateway_interface.tx.blocked_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `nsxt_fp.rx_bytes` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx bytes of ENS-Fastpath/FC-lookup. |
| `nsxt_fp.rx_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx packets of ENS Fastpath / Count of rx packets at FC lookup of vnic. |
| `nsxt_fp.rx_pkts_sp` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx pkt of slowpath / Not applicable for FC Module. |
| `nsxt_fp.rx_pkts_uplink` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx packets of ENS Uplink / Count of rx packets at FC lookup of Uplink. |
| `nsxt_fp.tx_bytes` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx bytes of ENS/FC Fastpath |
| `nsxt_fp.tx_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx packets of ENS Fastpath / Count of packets going through FC fastpath at vnic. |
| `nsxt_fp.tx_pkts_sp` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx pkts of ENS/FC slowpath |
| `nsxt_fp.tx_pkts_uplink` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx packets of ENS Uplink / Count of packets going through FC fastpath at Uplink. |
| `nsxt_swsec.rx_arp_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of transmitted IPv6 packets |
| `nsxt_swsec.rx_garp_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of transmitted ARP packets |
| `nsxt_swsec.rx_ipv4_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of received IPv4 packets |
| `nsxt_swsec.rx_ipv6_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of received IPv6 packets |
| `nsxt_swsec.rx_na_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv6 ND (Neighbor Discovery) NA (Neighbor Advertisement) packets |
| `nsxt_swsec.rx_non_ip_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of transmitted Gratuitous ARP (GARP) packets |
| `nsxt_swsec.rx_ns_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv6 ND (Neighbor Discovery) NS (Neighbor Solicitation) packets |
| `nsxt_swsec.rx_unsolicited_na_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv6 ND (Neighbor Discovery) NA (Neighbor Advertisement) packets which, were unsolicited |
| `nsxt_swsec.tx_arp_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of received ARP packets |
| `nsxt_swsec.tx_ipv4_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of transmitted  IPv4 packets |
| `nsxt_swsec.tx_ipv6_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of received non-IP packets |
| `nsxt_swsec.tx_non_ip_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of transmitted non-IP packets |
| `nsxt_vdl2.arp_proxy_req_suppress` | integer | 1 | – | Gauge: instantaneous value | Count of ARPs suppression attempted at Leaf Input IOChain |
| `nsxt_vdl2.arp_proxy_resp` | integer | 1 | – | Gauge: instantaneous value | Count of successful IP-MAC binding message from CCP for ARP suppression |
| `nsxt_vdl2.arp_proxy_resp_filtered` | integer | 1 | – | Gauge: instantaneous value | Count of ARP responses skipped for each successful IP-MAC response from CCP |
| `nsxt_vdl2.arp_proxy_resp_unknown` | integer | 1 | – | Gauge: instantaneous value | Count of unknown IP-MAC binding message from CCP for ARP suppression |
| `nsxt_vdl2.leaf_rx` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets received at VDL2LeafInput IOChain of a switchport |
| `nsxt_vdl2.leaf_tx` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets processed at VDL2LeafOutput IOChain of a switchport |
| `nsxt_vdl2.uplink_rx` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets received at uplink port from underlay network |
| `nsxt_vdl2.uplink_rx_filtered` | integer | 1 | – | Gauge: instantaneous value | Packets received at uplink filtered at uplink IOChain |
| `nsxt_vdl2.uplink_rx_skip_mac_learn` | integer | 1 | – | Gauge: instantaneous value | Count of packets for which MAC learn was skipped at uplink input IOChain |
| `nsxt_vdl2.uplink_tx` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets transmitted through uplink port towards underlay network |
| `nsxt_vdl2.uplink_tx_ignore` | integer | 1 | – | Gauge: instantaneous value | Count of DVS sent packets ignored at uplink output IOChain |
| `nsxt_vdl2.uplink_tx_non_unicast` | integer | 1 | – | Gauge: instantaneous value | Count of broadcast,multicast packets replicated to remote VTEPs |
| `nsxt_vdrb.rx_arp_req` | integer | 1 | – | Gauge: instantaneous value | Arp Reqests received |
| `nsxt_vdrb.rx_ipv4` | integer | 1 | – | Gauge: instantaneous value | Packets(IPv4) received on VDR |
| `nsxt_vdrb.rx_ipv6` | integer | 1 | – | Gauge: instantaneous value | Packets(IPv6) received on VDR |
| `nsxt_vdrb.tx_arp_rsp` | integer | 1 | – | Gauge: instantaneous value | Arp Responses sent |
| `nsxt_vdrb.tx_ipv4` | integer | 1 | – | Gauge: instantaneous value | Packets(IPv4) sent from VDR |
| `nsxt_vdrb.tx_ipv6` | integer | 1 | – | Gauge: instantaneous value | Packets(IPv6) sent from VDR |
| `nsxt_vsip.rx_ipv4_pass_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv4 pass packets |
| `nsxt_vsip.rx_ipv6_pass_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv6 pass packets |
| `nsxt_vsip.tx_ipv4_pass_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv4 pass packets |
| `nsxt_vsip.tx_ipv6_pass_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv6 pass packets |
| `results[].count` | integer | 1 | – | Gauge: instantaneous value | Entry count. |
| `rx.blocked_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `tx.blocked_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `vlan_extension.vlan_to_vpc_bytes.multicast_broadcast` | integer | 1 | – | Gauge: instantaneous value | The multicast and broadcast packets or bytes |
| `vlan_extension.vlan_to_vpc_packets.multicast_broadcast` | integer | 1 | – | Gauge: instantaneous value | The multicast and broadcast packets or bytes |
| `vlan_extension.vpc_to_vlan_bytes.multicast_broadcast` | integer | 1 | – | Gauge: instantaneous value | The multicast and broadcast packets or bytes |
| `vlan_extension.vpc_to_vlan_packets.multicast_broadcast` | integer | 1 | – | Gauge: instantaneous value | The multicast and broadcast packets or bytes |

</details>

<details>
<summary><b>Segment and port</b> — 61 fields, 27 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `rx_bytes.multicast_broadcast` | integer | 15 | – | Gauge: instantaneous value | The multicast and broadcast packets or bytes |
| `rx_packets.multicast_broadcast` | integer | 15 | – | Gauge: instantaneous value | The multicast and broadcast packets or bytes |
| `tx_bytes.multicast_broadcast` | integer | 15 | – | Gauge: instantaneous value | The multicast and broadcast packets or bytes |
| `tx_packets.multicast_broadcast` | integer | 15 | – | Gauge: instantaneous value | The multicast and broadcast packets or bytes |
| `distributed_dhcp_server_packets.acks` | integer | 12 | – | Gauge: instantaneous value | The total number of DHCP ACK packets. |
| `distributed_dhcp_server_packets.declines` | integer | 12 | – | Gauge: instantaneous value | The total number of DHCP DECLINE packets. |
| `distributed_dhcp_server_packets.discovers` | integer | 12 | – | Gauge: instantaneous value | The total number of DHCP DISCOVER packets. |
| `distributed_dhcp_server_packets.informs` | integer | 12 | – | Gauge: instantaneous value | The total number of DHCP INFORM packets. |
| `distributed_dhcp_server_packets.nacks` | integer | 12 | – | Gauge: instantaneous value | The total number of DHCP NACK packets. |
| `distributed_dhcp_server_packets.offers` | integer | 12 | – | Gauge: instantaneous value | The total number of DHCP OFFER packets. |
| `distributed_dhcp_server_packets.releases` | integer | 12 | – | Gauge: instantaneous value | The total number of DHCP RELEASE packets. |
| `distributed_dhcp_server_packets.requests` | integer | 12 | – | Gauge: instantaneous value | The total number of DHCP REQUEST packets. |
| `dropped_by_security_packets.spoof_guard_dropped[].counter` | integer | 12 | – | Gauge: instantaneous value | The number of packets. |
| `mac_learning.mac_not_learned_packets_allowed` | integer | 12 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of packets with unknown source MAC address that are dispatched without learning the source MAC address. Applicable only when the… |
| `mac_learning.macs_learned` | integer | 12 | – | Gauge: instantaneous value | Number of MACs learned |
| `nsxt_fp.rx_bytes` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx bytes of ENS-Fastpath/FC-lookup. |
| `nsxt_fp.rx_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx packets of ENS Fastpath / Count of rx packets at FC lookup of vnic. |
| `nsxt_fp.rx_pkts_sp` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx pkt of slowpath / Not applicable for FC Module. |
| `nsxt_fp.rx_pkts_uplink` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx packets of ENS Uplink / Count of rx packets at FC lookup of Uplink. |
| `nsxt_fp.tx_bytes` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx bytes of ENS/FC Fastpath |
| `nsxt_fp.tx_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx packets of ENS Fastpath / Count of packets going through FC fastpath at vnic. |
| `nsxt_fp.tx_pkts_sp` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx pkts of ENS/FC slowpath |
| `nsxt_fp.tx_pkts_uplink` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx packets of ENS Uplink / Count of packets going through FC fastpath at Uplink. |
| `nsxt_swsec.rx_arp_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of transmitted IPv6 packets |
| `nsxt_swsec.rx_garp_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of transmitted ARP packets |
| `nsxt_swsec.rx_ipv4_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of received IPv4 packets |
| `nsxt_swsec.rx_ipv6_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of received IPv6 packets |
| `nsxt_swsec.rx_na_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv6 ND (Neighbor Discovery) NA (Neighbor Advertisement) packets |
| `nsxt_swsec.rx_non_ip_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of transmitted Gratuitous ARP (GARP) packets |
| `nsxt_swsec.rx_ns_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv6 ND (Neighbor Discovery) NS (Neighbor Solicitation) packets |
| `nsxt_swsec.rx_unsolicited_na_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv6 ND (Neighbor Discovery) NA (Neighbor Advertisement) packets which, were unsolicited |
| `nsxt_swsec.tx_arp_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of received ARP packets |
| `nsxt_swsec.tx_ipv4_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of transmitted  IPv4 packets |
| `nsxt_swsec.tx_ipv6_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of received non-IP packets |
| `nsxt_swsec.tx_non_ip_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of transmitted non-IP packets |
| `nsxt_vdl2.arp_proxy_req_suppress` | integer | 6 | – | Gauge: instantaneous value | Count of ARPs suppression attempted at Leaf Input IOChain |
| `nsxt_vdl2.arp_proxy_resp` | integer | 6 | – | Gauge: instantaneous value | Count of successful IP-MAC binding message from CCP for ARP suppression |
| `nsxt_vdl2.arp_proxy_resp_filtered` | integer | 6 | – | Gauge: instantaneous value | Count of ARP responses skipped for each successful IP-MAC response from CCP |
| `nsxt_vdl2.arp_proxy_resp_unknown` | integer | 6 | – | Gauge: instantaneous value | Count of unknown IP-MAC binding message from CCP for ARP suppression |
| `nsxt_vdl2.leaf_rx` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets received at VDL2LeafInput IOChain of a switchport |
| `nsxt_vdl2.leaf_tx` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets processed at VDL2LeafOutput IOChain of a switchport |
| `nsxt_vdl2.uplink_rx` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets received at uplink port from underlay network |
| `nsxt_vdl2.uplink_rx_filtered` | integer | 6 | – | Gauge: instantaneous value | Packets received at uplink filtered at uplink IOChain |
| `nsxt_vdl2.uplink_rx_skip_mac_learn` | integer | 6 | – | Gauge: instantaneous value | Count of packets for which MAC learn was skipped at uplink input IOChain |
| `nsxt_vdl2.uplink_tx` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets transmitted through uplink port towards underlay network |
| `nsxt_vdl2.uplink_tx_ignore` | integer | 6 | – | Gauge: instantaneous value | Count of DVS sent packets ignored at uplink output IOChain |
| `nsxt_vdl2.uplink_tx_non_unicast` | integer | 6 | – | Gauge: instantaneous value | Count of broadcast,multicast packets replicated to remote VTEPs |
| `nsxt_vdrb.rx_arp_req` | integer | 6 | – | Gauge: instantaneous value | Arp Reqests received |
| `nsxt_vdrb.rx_ipv4` | integer | 6 | – | Gauge: instantaneous value | Packets(IPv4) received on VDR |
| `nsxt_vdrb.rx_ipv6` | integer | 6 | – | Gauge: instantaneous value | Packets(IPv6) received on VDR |
| `nsxt_vdrb.tx_arp_rsp` | integer | 6 | – | Gauge: instantaneous value | Arp Responses sent |
| `nsxt_vdrb.tx_ipv4` | integer | 6 | – | Gauge: instantaneous value | Packets(IPv4) sent from VDR |
| `nsxt_vdrb.tx_ipv6` | integer | 6 | – | Gauge: instantaneous value | Packets(IPv6) sent from VDR |
| `nsxt_vsip.rx_ipv4_pass_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv4 pass packets |
| `nsxt_vsip.rx_ipv6_pass_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv6 pass packets |
| `nsxt_vsip.tx_ipv4_pass_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv4 pass packets |
| `nsxt_vsip.tx_ipv6_pass_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv6 pass packets |
| `per_node_statistics[].rx.blocked_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `per_node_statistics[].tx.blocked_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `rx.blocked_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `tx.blocked_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |

</details>

<details>
<summary><b>NSX Manager cluster</b> — 50 fields, 4 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `rx_bytes` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of bytes received on the interface since the uptime. This will be reset on transport node restart. |
| `rx_frame` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total framing error packets since the uptime. Available only for Host Transport Node. |
| `rx_packets` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of incoming packets on the interface since the uptime. This will be reset on transport node restart. |
| `tx_bytes` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of bytes transmitted from the interface since the uptime. This will be reset on transport node restart. |
| `tx_colls` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets for collisions detected on transmit. Available only for Host Transport Node. |
| `tx_packets` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of outgoing packets transmitted from the interface since the uptime. This will be reset on transport node restart. |
| `cpu_usage.avg_cpu_core_usage_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all DPDK cores in percentage. |
| `cpu_usage.avg_cpu_core_usage_non_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all non-DPDK cores in percentage. |
| `cpu_usage.highest_cpu_core_usage_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest CPU utilization value among DPDK cores in percentage. |
| `cpu_usage.highest_cpu_core_usage_non_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest cpu utilization value among non_dpdk cores in percentage. |
| `dfw_heap_memory_usage[].peak_ever` | number | 1 | – | Gauge: instantaneous value | Number of times peak threshold reached for specific heap. |
| `dfw_heap_memory_usage[].usage_pct` | number | 1 | – | NSX-computed percentage | Percentage of heap utilized for specific heap. |
| `dfw_heap_memory_usage[].used_mb` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Utilized size of heap for the specified heap in mb units. |
| `dpus[].load_average[]` | number | 1 | – | Gauge: instantaneous value | – |
| `dpus[].mem_cache` | integer | 1 | – | Gauge: instantaneous value | Amount of RAM on the system that can be flushed out to disk, in kilobytes. |
| `dpus[].mem_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Amount of RAM in use on the system, in kilobytes. |
| `edge_mem_usage.cache_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM on the system that can be flushed out to disk. |
| `edge_mem_usage.datapath_mem_usage_details.datapath_heap_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of heap memory in use. |
| `edge_mem_usage.datapath_mem_usage_details.datapath_mem_pools_usage[].usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of memory pool in use. |
| `edge_mem_usage.datapath_mem_usage_details.highest_datapath_mem_pool_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Highest percentage usage value among datapath memory pools. |
| `edge_mem_usage.swap_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of swap disk in use. |
| `edge_mem_usage.system_mem_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM in use on edge node. |
| `load_average[]` | number | 1 | – | Gauge: instantaneous value | – |
| `mem_available` | integer | 1 | – | Gauge: instantaneous value | Amount of available RAM in the system, in kilobytes. The amount of reclaimable buffer/cache memory in use is taken into consideration here… |
| `mem_buffer` | integer | 1 | – | Gauge: instantaneous value | Amount of RAM on the system used for temporary disk block storage, in kilobytes |
| `mem_cache` | integer | 1 | – | Gauge: instantaneous value | Amount of RAM on the system that can be flushed out to disk, in kilobytes |
| `mem_free` | integer | 1 | – | Gauge: instantaneous value | Amount of unused RAM in the system, in kilobytes |
| `mem_slab` | integer | 1 | – | Gauge: instantaneous value | Amount of RAM allocated to the kernel slab allocator, in kilobytes |
| `mem_slab_reclaimable` | integer | 1 | – | Gauge: instantaneous value | Amount of RAM allocated to the kernel slab allocator that is not currently in use, in kilobytes |
| `mem_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Amount of RAM in use on the system, in kilobytes. (This is mem_total - mem_available) |
| `swap_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Amount of swap disk in use, in kilobytes |
| `system_status.cpu_usage.avg_cpu_core_usage_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all DPDK cores in percentage. |
| `system_status.cpu_usage.avg_cpu_core_usage_non_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all non-DPDK cores in percentage. |
| `system_status.cpu_usage.highest_cpu_core_usage_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest CPU utilization value among DPDK cores in percentage. |
| `system_status.cpu_usage.highest_cpu_core_usage_non_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest cpu utilization value among non_dpdk cores in percentage. |
| `system_status.dfw_heap_memory_usage[].usage_pct` | number | 1 | – | NSX-computed percentage | Percentage of heap utilized for specific heap. |
| `system_status.dfw_heap_memory_usage[].used_mb` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Utilized size of heap for the specified heap in mb units. |
| `system_status.dpus[].load_average[]` | number | 1 | – | Gauge: instantaneous value | – |
| `system_status.dpus[].mem_cache` | integer | 1 | – | Gauge: instantaneous value | Amount of RAM on the system that can be flushed out to disk, in kilobytes. |
| `system_status.dpus[].mem_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Amount of RAM in use on the system, in kilobytes. |
| `system_status.edge_mem_usage.cache_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM on the system that can be flushed out to disk. |
| `system_status.edge_mem_usage.datapath_mem_usage_details.datapath_heap_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of heap memory in use. |
| `system_status.edge_mem_usage.datapath_mem_usage_details.datapath_mem_pools_usage[].usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of memory pool in use. |
| `system_status.edge_mem_usage.datapath_mem_usage_details.highest_datapath_mem_pool_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Highest percentage usage value among datapath memory pools. |
| `system_status.edge_mem_usage.swap_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of swap disk in use. |
| `system_status.edge_mem_usage.system_mem_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM in use on edge node. |
| `system_status.load_average[]` | number | 1 | ✓ | Gauge: instantaneous value | – |
| `system_status.mem_cache` | integer | 1 | ✓ | Gauge: instantaneous value | Amount of RAM on the system that can be flushed out to disk, in kilobytes |
| `system_status.mem_used` | integer | 1 | ✓ | Gauge; utilisation = used / total x 100 where total is available | Amount of RAM in use on the system, in kilobytes |
| `system_status.swap_used` | integer | 1 | ✓ | Gauge; utilisation = used / total x 100 where total is available | Amount of swap disk in use, in kilobytes |

</details>

<details>
<summary><b>Edge transport node and edge cluster</b> — 49 fields, 13 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `stats_per_site[].rx.blocked_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `stats_per_site[].stats_per_tunnel[].rx.blocked_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `stats_per_site[].stats_per_tunnel[].tx.blocked_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `stats_per_site[].tx.blocked_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `member_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Represents the number of edge nodes in the cluster. |
| `members[].allocation_pools[].standby_service_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Represents the number of standby services running on the edge node. |
| `neighbor_status[].address_families[].in_prefix_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of in prefixes |
| `neighbor_status[].address_families[].out_prefix_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of out prefixes |
| `rx_stats.blocked_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `tx_stats.blocked_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `agent_status.agents[].resource_usage.cpu_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | The Agent's share of the elapsed CPU time since the last screen update, expressed as a percentage of total CPU time. |
| `agent_status.agents[].resource_usage.memory_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Used memory in kilobytes. |
| `node_status.system_status.cpu_usage.avg_cpu_core_usage_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all DPDK cores in percentage. |
| `node_status.system_status.cpu_usage.avg_cpu_core_usage_non_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all non-DPDK cores in percentage. |
| `node_status.system_status.cpu_usage.highest_cpu_core_usage_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest CPU utilization value among DPDK cores in percentage. |
| `node_status.system_status.cpu_usage.highest_cpu_core_usage_non_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest cpu utilization value among non_dpdk cores in percentage. |
| `node_status.system_status.dfw_heap_memory_usage[].usage_pct` | number | 1 | – | NSX-computed percentage | Percentage of heap utilized for specific heap. |
| `node_status.system_status.dfw_heap_memory_usage[].used_mb` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Utilized size of heap for the specified heap in mb units. |
| `node_status.system_status.dpus[].load_average[]` | number | 1 | – | Gauge: instantaneous value | – |
| `node_status.system_status.dpus[].mem_cache` | integer | 1 | – | Gauge: instantaneous value | Amount of RAM on the system that can be flushed out to disk, in kilobytes. |
| `node_status.system_status.dpus[].mem_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Amount of RAM in use on the system, in kilobytes. |
| `node_status.system_status.edge_mem_usage.cache_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM on the system that can be flushed out to disk. |
| `node_status.system_status.edge_mem_usage.datapath_mem_usage_details.datapath_heap_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of heap memory in use. |
| `node_status.system_status.edge_mem_usage.datapath_mem_usage_details.highest_datapath_mem_pool_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Highest percentage usage value among datapath memory pools. |
| `node_status.system_status.edge_mem_usage.swap_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of swap disk in use. |
| `node_status.system_status.edge_mem_usage.system_mem_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM in use on edge node. |
| `node_status.system_status.load_average[]` | number | 1 | – | Gauge: instantaneous value | – |
| `node_status.system_status.mem_cache` | integer | 1 | – | Gauge: instantaneous value | Amount of RAM on the system that can be flushed out to disk, in kilobytes |
| `node_status.system_status.mem_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Amount of RAM in use on the system, in kilobytes |
| `node_status.system_status.swap_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Amount of swap disk in use, in kilobytes |
| `results[].node_status.system_status.cpu_usage.avg_cpu_core_usage_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all DPDK cores in percentage. |
| `results[].node_status.system_status.cpu_usage.avg_cpu_core_usage_non_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all non-DPDK cores in percentage. |
| `results[].node_status.system_status.cpu_usage.highest_cpu_core_usage_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest CPU utilization value among DPDK cores in percentage. |
| `results[].node_status.system_status.cpu_usage.highest_cpu_core_usage_non_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest cpu utilization value among non_dpdk cores in percentage. |
| `results[].node_status.system_status.edge_mem_usage.cache_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM on the system that can be flushed out to disk. |
| `results[].node_status.system_status.edge_mem_usage.swap_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of swap disk in use. |
| `results[].node_status.system_status.edge_mem_usage.system_mem_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM in use on edge node. |
| `results[].node_status.system_status.load_average[]` | number | 1 | – | Gauge: instantaneous value | – |
| `results[].node_status.system_status.mem_cache` | integer | 1 | – | Gauge: instantaneous value | Amount of RAM on the system that can be flushed out to disk, in kilobytes |
| `results[].node_status.system_status.mem_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Amount of RAM in use on the system, in kilobytes |
| `results[].node_status.system_status.swap_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Amount of swap disk in use, in kilobytes |
| `rx.blocked_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `rx_bytes` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of bytes received on the interface since the uptime. This will be reset on transport node restart. |
| `rx_frame` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total framing error packets since the uptime. Available only for Host Transport Node. |
| `rx_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of incoming packets on the interface since the uptime. This will be reset on transport node restart. |
| `tx.blocked_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `tx_bytes` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of bytes transmitted from the interface since the uptime. This will be reset on transport node restart. |
| `tx_colls` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets for collisions detected on transmit. Available only for Host Transport Node. |
| `tx_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of outgoing packets transmitted from the interface since the uptime. This will be reset on transport node restart. |

</details>

<details>
<summary><b>NSX Manager node</b> — 31 fields, 2 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `cpu_usage.avg_cpu_core_usage_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all DPDK cores in percentage. |
| `cpu_usage.avg_cpu_core_usage_non_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all non-DPDK cores in percentage. |
| `cpu_usage.highest_cpu_core_usage_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest CPU utilization value among DPDK cores in percentage. |
| `cpu_usage.highest_cpu_core_usage_non_dpdk` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest cpu utilization value among non_dpdk cores in percentage. |
| `dfw_heap_memory_usage[].peak_ever` | number | 1 | – | Gauge: instantaneous value | Number of times peak threshold reached for specific heap. |
| `dfw_heap_memory_usage[].usage_pct` | number | 1 | – | NSX-computed percentage | Percentage of heap utilized for specific heap. |
| `dfw_heap_memory_usage[].used_mb` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Utilized size of heap for the specified heap in mb units. |
| `dpus[].load_average[]` | number | 1 | – | Gauge: instantaneous value | – |
| `dpus[].mem_cache` | integer | 1 | – | Gauge: instantaneous value | Amount of RAM on the system that can be flushed out to disk, in kilobytes. |
| `dpus[].mem_used` | integer | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Amount of RAM in use on the system, in kilobytes. |
| `edge_mem_usage.cache_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM on the system that can be flushed out to disk. |
| `edge_mem_usage.datapath_mem_usage_details.datapath_heap_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of heap memory in use. |
| `edge_mem_usage.datapath_mem_usage_details.datapath_mem_pools_usage[].usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of memory pool in use. |
| `edge_mem_usage.datapath_mem_usage_details.highest_datapath_mem_pool_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Highest percentage usage value among datapath memory pools. |
| `edge_mem_usage.swap_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of swap disk in use. |
| `edge_mem_usage.system_mem_usage` | number | 1 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM in use on edge node. |
| `load_average[]` | number | 1 | ✓ | Gauge: instantaneous value | – |
| `mem_available` | integer | 1 | ✓ | Gauge: instantaneous value | Amount of available RAM in the system, in kilobytes. The amount of reclaimable buffer/cache memory in use is taken into consideration here… |
| `mem_buffer` | integer | 1 | ✓ | Gauge: instantaneous value | Amount of RAM on the system used for temporary disk block storage, in kilobytes |
| `mem_cache` | integer | 1 | ✓ | Gauge: instantaneous value | Amount of RAM on the system that can be flushed out to disk, in kilobytes |
| `mem_free` | integer | 1 | ✓ | Gauge: instantaneous value | Amount of unused RAM in the system, in kilobytes |
| `mem_slab` | integer | 1 | ✓ | Gauge: instantaneous value | Amount of RAM allocated to the kernel slab allocator, in kilobytes |
| `mem_slab_reclaimable` | integer | 1 | ✓ | Gauge: instantaneous value | Amount of RAM allocated to the kernel slab allocator that is not currently in use, in kilobytes |
| `mem_used` | integer | 1 | ✓ | Gauge; utilisation = used / total x 100 where total is available | Amount of RAM in use on the system, in kilobytes. (This is mem_total - mem_available) |
| `rx_bytes` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of bytes received on the interface since the uptime. This will be reset on transport node restart. |
| `rx_frame` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total framing error packets since the uptime. Available only for Host Transport Node. |
| `rx_packets` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of incoming packets on the interface since the uptime. This will be reset on transport node restart. |
| `swap_used` | integer | 1 | ✓ | Gauge; utilisation = used / total x 100 where total is available | Amount of swap disk in use, in kilobytes |
| `tx_bytes` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of bytes transmitted from the interface since the uptime. This will be reset on transport node restart. |
| `tx_colls` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets for collisions detected on transmit. Available only for Host Transport Node. |
| `tx_packets` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of outgoing packets transmitted from the interface since the uptime. This will be reset on transport node restart. |

</details>

<details>
<summary><b>Upgrade coordinator</b> — 23 fields, 8 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].node_count` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of nodes of the type and at the component version |
| `results[].percent_complete` | number | 2 | ✓ | NSX-computed percentage | Indicator of upgrade progress in percentage |
| `ccp_status.current_version_node_summary.results[].node_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of nodes of the type and at the component version |
| `ccp_status.percent_complete` | number | 1 | – | NSX-computed percentage | Indicator of upgrade progress in percentage |
| `ccp_status.pre_upgrade_status.node_with_issues_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of nodes which generated failures or warnings in last execution of pre/post-upgrade checks. This field has been deprecated. Please u… |
| `ccp_status.pre_upgrade_status.warning_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total count of generated warnings in last execution of pre/post upgrade checks. |
| `component_status[].current_version_node_summary.results[].node_count` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of nodes of the type and at the component version |
| `component_status[].percent_complete` | number | 1 | ✓ | NSX-computed percentage | Indicator of upgrade progress in percentage |
| `component_status[].pre_upgrade_status.node_with_issues_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of nodes which generated failures or warnings in last execution of pre/post-upgrade checks. This field has been deprecated. Please u… |
| `component_status[].pre_upgrade_status.warning_count` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total count of generated warnings in last execution of pre/post upgrade checks. |
| `edge_status.current_version_node_summary.results[].node_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of nodes of the type and at the component version |
| `edge_status.percent_complete` | number | 1 | – | NSX-computed percentage | Indicator of upgrade progress in percentage |
| `edge_status.pre_upgrade_status.node_with_issues_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of nodes which generated failures or warnings in last execution of pre/post-upgrade checks. This field has been deprecated. Please u… |
| `edge_status.pre_upgrade_status.warning_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total count of generated warnings in last execution of pre/post upgrade checks. |
| `host_status.current_version_node_summary.results[].node_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of nodes of the type and at the component version |
| `host_status.percent_complete` | number | 1 | – | NSX-computed percentage | Indicator of upgrade progress in percentage |
| `host_status.pre_upgrade_status.node_with_issues_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of nodes which generated failures or warnings in last execution of pre/post-upgrade checks. This field has been deprecated. Please u… |
| `host_status.pre_upgrade_status.warning_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total count of generated warnings in last execution of pre/post upgrade checks. |
| `percent` | number | 1 | – | NSX-computed percentage | Percent of bundle uploaded from URL |
| `percentage` | integer | 1 | – | NSX-computed percentage | Progress percentage of the Upgrade Bundle Operations |
| `progress_percentage` | integer | 1 | ✓ | NSX-computed percentage | Upgrade Coordinator Upgrade Progress Percentage |
| `results[].node_with_issues_count` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of nodes with issues that may cause upgrade failure |
| `results[].upgrade_unit_count` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of upgrade units in the group |

</details>

<details>
<summary><b>Load balancer</b> — 15 fields, 2 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `current_pool_count` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The current count of pools configured for all load balancer services. |
| `current_pool_member_count` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The current count of pool members configured for all load balancer services. |
| `current_virtual_server_count` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The current count of virtual servers configured for all load balancer services. |
| `pool_member_usage_percentage` | number | 1 | ✓ | NSX-computed percentage | Overall pool member usage percentage for all load balancer services. |
| `pool_usage_percentage` | number | 1 | ✓ | NSX-computed percentage | Overall pool usage percentage for all load balancer services. |
| `results[].current_load_balancer_credits` | integer | 1 | – | Gauge: instantaneous value | Current load balancer credits in use for all nodes. For example, configuring a medium load balancer on a node consumes 10 credits. If there… |
| `results[].current_pool_member_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The overall count of pool members configured on all nodes. |
| `results[].node_counts[].node_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Node count for specific severity. |
| `results[].usage_percentage` | number | 1 | – | NSX-computed percentage | The overall usage percentage of all nodes for load balancer. The value is the overall load balancer credit usage percentage. |
| `service_counts[].service_count` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Service count for specific serverity. |
| `service_usages[].current_pool_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The current number of pools which has been configured in the given load balancer service. |
| `service_usages[].current_pool_member_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The current number of pool members which has been configured in the given load balancer service. |
| `service_usages[].current_virtual_server_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The current number of virtual servers which has been configured in the given load balancer service. |
| `service_usages[].usage_percentage` | number | 1 | – | NSX-computed percentage | The usage percentage is the largest usage percentage from virtual servers, pools and pool members for the load balancer service. If the pro… |
| `virtual_server_usage_percentage` | number | 1 | ✓ | NSX-computed percentage | Overall virtual server usage percentage for all load balancer services. |

</details>

<details>
<summary><b>Transport zone</b> — 13 fields, 8 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].node_status.system_status.cpu_usage.avg_cpu_core_usage_dpdk` | number | 3 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all DPDK cores in percentage. |
| `results[].node_status.system_status.cpu_usage.avg_cpu_core_usage_non_dpdk` | number | 3 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the average usage of all non-DPDK cores in percentage. |
| `results[].node_status.system_status.cpu_usage.highest_cpu_core_usage_dpdk` | number | 3 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest CPU utilization value among DPDK cores in percentage. |
| `results[].node_status.system_status.cpu_usage.highest_cpu_core_usage_non_dpdk` | number | 3 | – | Gauge; utilisation = used / total x 100 where total is available | Indicates the highest cpu utilization value among non_dpdk cores in percentage. |
| `results[].node_status.system_status.edge_mem_usage.cache_usage` | number | 3 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM on the system that can be flushed out to disk. |
| `results[].node_status.system_status.edge_mem_usage.swap_usage` | number | 3 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of swap disk in use. |
| `results[].node_status.system_status.edge_mem_usage.system_mem_usage` | number | 3 | – | Gauge; utilisation = used / total x 100 where total is available | Percentage of RAM in use on edge node. |
| `results[].node_status.system_status.load_average[]` | number | 3 | ✓ | Gauge: instantaneous value | – |
| `results[].node_status.system_status.mem_cache` | integer | 3 | ✓ | Gauge: instantaneous value | Amount of RAM on the system that can be flushed out to disk, in kilobytes |
| `results[].node_status.system_status.mem_used` | integer | 3 | ✓ | Gauge; utilisation = used / total x 100 where total is available | Amount of RAM in use on the system, in kilobytes |
| `results[].node_status.system_status.swap_used` | integer | 3 | ✓ | Gauge; utilisation = used / total x 100 where total is available | Amount of swap disk in use, in kilobytes |
| `results[].up_agent_count` | integer | 3 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Agent up count |
| `unused_count` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of transport zones with unused status. |

</details>

<details>
<summary><b>Tier-0 and Tier-1 gateway, routing</b> — 13 fields, 41 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `per_node_statistics[].rx.blocked_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `per_node_statistics[].tx.blocked_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `rx.blocked_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `tx.blocked_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `results[].count` | integer | 9 | – | Gauge: instantaneous value | Entry count. |
| `members[].per_node_statistics[].rx.blocked_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `members[].per_node_statistics[].tx.blocked_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `summary.rx.blocked_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `summary.tx.blocked_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets blocked on the port. This could be due to either port is operatively down or blocked. The port can be blocked d… |
| `results[].address_families[].in_prefix_count` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of in prefixes |
| `results[].address_families[].out_prefix_count` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of out prefixes |
| `instance_runtime_statistics[].interface_statistics[].mac_learning.mac_not_learned_packets_allowed` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of packets with unknown source MAC address that are dispatched without learning the source MAC address. Applicable only when the… |
| `instance_runtime_statistics[].interface_statistics[].mac_learning.macs_learned` | integer | 2 | – | Gauge: instantaneous value | Number of MACs learned |

</details>

<details>
<summary><b>Manager appliance process and latency (SHA)</b> — 12 fields, 4 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].top_process_by_cpu_count` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Display the total count of process. |
| `results[].top_process_by_cpu_list[].cpu_usage` | number | 2 | ✓ | Gauge; utilisation = used / total x 100 where total is available | The process's share of the elapsed CPU time since the last screen update, expressed as a percentage of total CPU time. |
| `results[].top_process_by_cpu_list[].memory_usage` | number | 2 | ✓ | Gauge; utilisation = used / total x 100 where total is available | A process's currently used share of available physical memory. |
| `results[].top_process_by_mem_count` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Display the total count of process. |
| `results[].top_process_by_mem_list[].cpu_usage` | number | 2 | ✓ | Gauge; utilisation = used / total x 100 where total is available | The process's share of the elapsed CPU time since the last screen update, expressed as a percentage of total CPU time. |
| `results[].top_process_by_mem_list[].memory_usage` | number | 2 | ✓ | Gauge; utilisation = used / total x 100 where total is available | A process's currently used share of available physical memory. |
| `top_process_by_cpu_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Display the total count of process. |
| `top_process_by_cpu_list[].cpu_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | The process's share of the elapsed CPU time since the last screen update, expressed as a percentage of total CPU time. |
| `top_process_by_cpu_list[].memory_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | A process's currently used share of available physical memory. |
| `top_process_by_mem_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Display the total count of process. |
| `top_process_by_mem_list[].cpu_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | The process's share of the elapsed CPU time since the last screen update, expressed as a percentage of total CPU time. |
| `top_process_by_mem_list[].memory_usage` | number | 2 | – | Gauge; utilisation = used / total x 100 where total is available | A process's currently used share of available physical memory. |

</details>

<details>
<summary><b>Security services (IDFW, IDS/IPS)</b> — 11 fields, 12 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].statistics.byte_count` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of bytes processed by the rule. |
| `results[].statistics.hit_count` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of hits received by the rule. |
| `results[].statistics.l7_accept_count` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Accepted counters received by the rule. |
| `results[].statistics.packet_count` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of packets processed by the rule. |
| `results[].statistics.results[].byte_count` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of bytes processed by the rule. |
| `results[].statistics.results[].hit_count` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of hits received by the rule. |
| `results[].statistics.results[].l7_accept_count` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Accepted counters received by the rule. |
| `results[].statistics.results[].packet_count` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of packets processed by the rule. |
| `results[].statistics.results[].session_count` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of sessions processed by the rule. |
| `results[].statistics.session_count` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of sessions processed by the rule. |
| `num_user_sessions` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of active user sessions/logins in IDFW enabled compute collections (including both UP and DOWN hosts).  N sessions/logins by the sam… |

</details>

<details>
<summary><b>Firewall policy and rule (DFW, gateway)</b> — 10 fields, 14 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].statistics.byte_count` | integer | 7 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of bytes processed by the rule. |
| `results[].statistics.hit_count` | integer | 7 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of hits received by the rule. |
| `results[].statistics.l7_accept_count` | integer | 7 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Accepted counters received by the rule. |
| `results[].statistics.packet_count` | integer | 7 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of packets processed by the rule. |
| `results[].statistics.results[].byte_count` | integer | 7 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of bytes processed by the rule. |
| `results[].statistics.results[].hit_count` | integer | 7 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of hits received by the rule. |
| `results[].statistics.results[].l7_accept_count` | integer | 7 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Accepted counters received by the rule. |
| `results[].statistics.results[].packet_count` | integer | 7 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of packets processed by the rule. |
| `results[].statistics.results[].session_count` | integer | 7 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of sessions processed by the rule. |
| `results[].statistics.session_count` | integer | 7 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of sessions processed by the rule. |

</details>

<details>
<summary><b>Realization and platform status</b> — 10 fields, 3 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `counters.delivered_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of delivered observations for this traceflow round. |
| `counters.forwarded_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of forwarded observations for this traceflow round. |
| `counters.protected_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of protected observations for this traceflow round, which current user does not have access. |
| `counters.received_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of received observations for this traceflow round. |
| `logical_counters.delivered_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of delivered observations for this traceflow round. |
| `logical_counters.forwarded_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of forwarded observations for this traceflow round. |
| `logical_counters.protected_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of protected observations for this traceflow round, which current user does not have access. |
| `logical_counters.received_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of received observations for this traceflow round. |
| `member_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Represents the number of virtualNetworkAppliances in the cluster. |
| `members[].allocation_pools[].standby_service_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Represents the number of standby services running on the edge node. |

</details>

<details>
<summary><b>VPN (IPsec, L2VPN)</b> — 9 fields, 5 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `aggregate_traffic_counters.bytes_in` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of traffic bytes received on inbound security association. |
| `aggregate_traffic_counters.bytes_out` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of traffic bytes sent on outbound security association. |
| `aggregate_traffic_counters.packets_in` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets received on inbound security association. |
| `aggregate_traffic_counters.packets_out` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets sent on outbound security association. |
| `session_summary.negotiating_sessions` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of IPSec VPN sessions in negotiating state. |
| `traffic_summary_per_session[].traffic_counters.bytes_in` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of traffic bytes received on inbound security association. |
| `traffic_summary_per_session[].traffic_counters.bytes_out` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of traffic bytes sent on outbound security association. |
| `traffic_summary_per_session[].traffic_counters.packets_in` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets received on inbound security association. |
| `traffic_summary_per_session[].traffic_counters.packets_out` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets sent on outbound security association. |

</details>

<details>
<summary><b>Capacity dashboard and limits</b> — 7 fields, 3 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].node_capacity_status[].remaining_large_load_balancer_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The remaining large load balancer count means maximum number of large load balancers which could be configured in the given node. |
| `results[].node_capacity_status[].remaining_medium_load_balancer_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The remaining medium load balancer count means maximum number of medium load balancers which could be configured in the given node. |
| `results[].node_capacity_status[].remaining_pool_member_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | This is a deprecated property. There will be no LB pool member limit per edge node and per virtual network appliance anymore. For backward… |
| `results[].node_capacity_status[].remaining_small_load_balancer_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The remaining small load balancer count means maximum number of small load balancers which could be configured in the given node. |
| `results[].node_capacity_status[].remaining_xlarge_load_balancer_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The remaining xlarge load balancer count means maximum number of xlarge load balancers which could be configured in the given node. |
| `capacity_usage[].current_usage_count` | integer | 1 | ✓ | Gauge; utilisation = used / total x 100 where total is available | Indicate the current usage count of object type. |
| `capacity_usage[].current_usage_percentage` | number | 1 | ✓ | NSX-computed percentage | Current usage percentage for object type |

</details>

<details>
<summary><b>Transit gateway (VPC)</b> — 7 fields, 5 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].count` | integer | 2 | – | Gauge: instantaneous value | Entry count. |
| `rx.blocked_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of blocked packets |
| `rx.error_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of error packets |
| `tx.blocked_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of blocked packets |
| `tx.error_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of error packets |
| `external_traffic.rx.blocked_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of blocked packets |
| `external_traffic.rx.error_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of error packets |

</details>

<details>
<summary><b>Security platform services (NAPP, MPS, SCRX, service insertion)</b> — 3 fields, 3 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `percentage` | integer | 2 | ✓ | NSX-computed percentage | Percentage completed for deployment. |
| `host_status[].cpu_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Actual count of vCPUs used by the SCRX container on the host. |
| `host_status[].memory` | integer | 1 | – | Gauge: instantaneous value | Actual memory used by the SCRX container on the host. |

</details>

<details>
<summary><b>Other platform status</b> — 2 fields, 2 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `percent` | number | 1 | – | NSX-computed percentage | Percent of bundle uploaded from remote location. |
| `results[].up_agent_count` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Agent up count |

</details>

<details>
<summary><b>Federation (sites)</b> — 2 fields, 2 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `active_standby_sync_statuses[].percentage_completed` | integer | 1 | – | NSX-computed percentage | Percentage estimate of synchronization progress. Ranges from 0 to 100. This value is only returned when queried on an active Global Manager… |
| `current_step.parts[].percentage` | integer | 1 | ✓ | NSX-computed percentage | 0 - 100 of the task being completed. |

</details>

<details>
<summary><b>IP address management (IP blocks)</b> — 2 fields, 1 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `ip_blocks[].allocated_by_vpc.count` | integer | 1 | – | Gauge: instantaneous value | Count of used resources by VPC on IP block |
| `ip_blocks[].available` | integer | 1 | – | Gauge: instantaneous value | Available IP address space |

</details>

<details>
<summary><b>Licensing</b> — 1 fields, 1 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `feature_usage_info[].capacity_usage[].usage_count` | integer | 1 | ✓ | Gauge; utilisation = used / total x 100 where total is available | count of number of items of capacity_type |

</details>

<details>
<summary><b>Transport node collection</b> — 1 fields, 2 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `aggregate_progress_percentage` | integer | 2 | – | NSX-computed percentage | Average of all transport node deployment progress in a cluster. Applicable only if transport node profile is applied on a cluster. |

</details>

<!-- END GENERATED: consumption -->
