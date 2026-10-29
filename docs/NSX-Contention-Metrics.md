# NSX contention metrics

Contention metrics tell you that something is **saturated, queued, dropped, rejected or waiting**. Packets are lost or delayed, a table is full, a buffer has overflowed, or a rule is limiting traffic. They are the first place to look when an application is slow but no object reports as down.

- Companion guides: [Formulas and conventions](NSX-Metrics-Formulas.md) · [Consumption](NSX-Consumption-Metrics.md) · [Capacity](NSX-Capacity-Metrics.md) · [Availability and events](NSX-Availability-Metrics-and-Events.md)
- Lab: `nsxman1`, NSX 9.1.1.0, 3 ESXi hosts, no Edge, no segments, no gateways. Crawl 2026-10-19.
- Open questions: [NSX-Open-Questions.md](NSX-Open-Questions.md), numbered D1 to D18 and referred to by number in this guide.
- Evidence tags are defined in the [formulas guide](NSX-Metrics-Formulas.md): **[Lab]**, **[Doc]**, **[Derived]**, **[Open]**.

---

## 1. How to recognise a contention metric

Contention metrics are identified by the name of the field. NSX has no separate contention type, so this is the rule the category lists use.

| Signal | Name patterns | Examples (real field names) | What it means |
|---|---|---|---|
| Drop | `drop`, `dropped`, `discard` | `rx_dropped`, `tx_drops`, `firewall_total_packet_drops` | Packets discarded |
| Reject | `reject` | `firewall_packet_rejects`, `lb_reject_drops` | Connection refused by policy |
| Flood or overlimit | `flood`, `overlimit`, `rate_limit` | `icmp_flood_overlimit_drops`, `rx_rate_limit_bcast_drops` | A rate limit was hit |
| Table or state full | `_full`, `full_`, `table_full` | `mac_tbl_update_full`, `firewall_state_table_full_packet_drops` | A fixed-size table is exhausted |
| Miss | `miss`, `misses` | `fastpath_flow_miss_pps`, `rx_misses` | Work went to the slow path or was not found |
| Queue or backlog | `queue`, `backlog`, `too_long` | `tx_dispatch_queue_too_long_drops`, `queues[]` overflow | Work is waiting |
| Held | `hold`, `pending` | `arp_hold_pkt_drops`, `ns_hold_pkt_drops` | Packets held for a resolution that did not come |
| Memory exhausted | `no_mem`, `memory_drops`, `nombufs` | `no_mem_dropped_packets`, `rx_nombufs` | No buffer or memory to receive |
| Latency | `latency` | `service_datapath_pkt_latency` | Time delay (unit not stated, [Open]) |
| Error | `error`, `errors`, `failure` | `rx_errors`, `tx_errors`, `tx_ddhcp_arp_reply_failures` | The operation failed |
| Link | `carrier`, `collision` | `tx_carrier` (host only) | Physical link trouble |

**Counters are cumulative** ([Doc]). Turn each into a rate before you set a threshold: rate = (v₂ − v₁) ÷ (t₂ − t₁). See the [formulas guide](NSX-Metrics-Formulas.md#3-calculation-pattern-for-counters).

---

## 2. Contention by object type

| Object type | Main contention signals | Where it comes from | Lab status |
|---|---|---|---|
| **ESXi host transport node** | Datapath drops by module: L3, distributed firewall, overlay L2, switch security, virtual switch, fast path. Packet-processing efficiency: flow misses. | `…/host-transport-nodes/{id}/statistics/monitor` and `…/statistics/debug` | ✓ Observed |
| **Host and Edge interfaces** | `rx_dropped`, `tx_dropped`, `rx_errors`, `tx_errors`, `tx_carrier` | `…/network/interfaces/{if}/stats` | ✓ Observed (zero on vmnic0) |
| **Edge transport node** | NIC ring-buffer overflow, NIC transmit queue overflow, flow-cache miss, datapath drops, `rx_drop_no_match`, `rx_nombufs` | `…/edge-transport-nodes/…`, Edge dataplane stats | Spec only. No Edge in lab. |
| **Edge physical ports and queues** | Per-queue `rx_packets` and drops, `queues[]` overflow | `…/node/services/dataplane/physical-ports/{port}/stats` and `xstats` | Spec only |
| **Distributed firewall rule** | `match_drop_rule_rx/tx_drops` (per rule) | Policy security-policy statistics | Spec only for the rule counters; zero hits in lab |
| **Tier-0 and Tier-1 interfaces** | Interface drops, ARP proxy failures | `…/locale-services/…/interfaces/{if}/statistics` | Spec only |
| **Transit gateway (VPC)** | `dropped_packets` for internal and external traffic, rx and tx | Transit gateway statistics | Spec only in lab |
| **IPsec VPN session** | `ipsec_dropped_packets`, `ipsec_no_sa_dropped_packets`, `ipsec_pol_block_dropped_packets` | Session statistics | Spec only |
| **Federation (sites)** | Queue occupancy used to sync between sites (events) | Federation events | Event only |
| **NSX Manager node** | Interface drops and errors | `/node/network/interfaces/{if}/stats` | ✓ Observed |

---

## 3. Formulas

| Metric | Formula | Notes |
|---|---|---|
| Packet drop ratio | Δdrops ÷ Δpackets_in | Use the packet counter for the same object and direction |
| Interface error ratio | Δrx_errors ÷ Δrx_packets | Same for TX |
| Interface drop ratio | Δrx_dropped ÷ Δrx_packets | Same for TX |
| Flow-cache miss ratio | `fastpath_flow_miss_pps` ÷ (`fastpath_flow_hit_pps` + `fastpath_flow_miss_pps`) | [Derived]. A high ratio means the slow path is busy. |
| Slow-path share | `fastpath_slowpath_only_pps` ÷ total packets per second | [Derived] |
| Table pressure | Use the `*_full` counter as a rate. There is no depth field for these tables in the response. | [Derived]. The depth metric is [Open]. |
| Queue overflow % | `tx_queue_overflow_percentage` (event field) | Use the event. It already has a 2% fixed threshold ([Lab] event metadata). |

---

## 4. Event-driven contention signals

These events come from the NSX monitoring framework. Use them instead of recomputing when you can. Thresholds are from the event definitions in the lab ([Lab]). Fixed or tunable is in the [full event tables](NSX-Availability-Metrics-and-Events.md#resource-threshold-events).

| Event | Object | Threshold | Severity | Meaning |
|---|---|---|---|---|
| `edge_nic_out_of_receive_buffer` | Edge | 2% overflow | MEDIUM | Receive ring buffer overflowed, packets lost |
| `edge_nic_out_of_transmit_buffer` | Edge | 2% overflow | CRITICAL | Transmit ring buffer overflowed |
| `edge_nic_transmit_queue_overflow` | Edge | 2% overflow | CRITICAL | A transmit queue overflowed |
| `mega_flow_cache_hit_rate_low` | Edge | < 80% | MEDIUM | Flow-cache misses are high |
| `micro_flow_cache_hit_rate_low` | Edge | < 80% | MEDIUM | Micro-cache misses are high |
| `edge_datapath_mempool_high` | Edge | 85% | MEDIUM | Datapath memory pool nearly used |
| `edge_global_arp_table_usage_high` | Edge | 95% | MEDIUM | Global ARP table nearly full |
| `queue_occupancy_threshold_exceeded` | Federation | 70 | MEDIUM | Cross-site sync queue is filling |
| `resource_utilization_high` | Security (SCRX) | 95% | CRITICAL | Security datapath resource high |
| `dtgw_vlan_uplink_arp_fail` | Host | — | MEDIUM | ARP resolution failed on an uplink |

---

## 5. Lab readings (2026-10-19)

| Signal | Value | Reading |
|---|---|---|
| Datapath drops, current rate | 5.46 pps (`datapath_total_packet_drops_pps`) | [Lab] Low. Rate is NSX-computed. |
| Flow-cache misses, current rate | 220.9 pps against 37,524.9 pps hits | [Lab] Miss ratio ≈ 0.6% [Derived] |
| Slow-path only | 22.2 pps | [Lab] |
| `hostswitch_network_mismatch_packet_drops` | 4,053,653 (cumulative) | [Lab] Large. Cumulative since start, not a rate. |
| `vlan_tag_mismatch_tx_mcast` | 4,054,351 (cumulative) | [Lab] Same order as the mismatch drops above. This suggests one underlying cause, but it is not proven. Take two samples and compare the rates before you act. |
| `vlan_tag_mismatch_tx` | 1 | [Lab] |
| `vmnic0` drops and errors | `rx_dropped` 0, `tx_dropped` 0, `rx_errors` 0, `tx_errors` 0, `tx_carrier` 0 | [Lab] Physical NIC is clean |
| Distributed firewall drops | 0 in the host `distributed_firewall` debug counters and in the rule-statistics sample | [Lab] One sample. Zero is consistent with no rule drops, not proof of it. |
| Manager `eth0` | `rx_dropped` 271 (cumulative since boot), no errors | [Lab] A small, old count. Track its rate, not its total. `lo` has no drops. |

**Reading the two large counters.** Both are about traffic that the host could not match to a valid VLAN. Their size and their closeness suggest a repeated source, such as a multicast or broadcast sender on the wrong VLAN, or a port group that is not trunked for the right VLANs. This is a hypothesis to test, not a finding. The next step is to take two samples 5 minutes apart and see whether the counters still grow.

---

## 6. Full lists by object type

Generated from [`data/nsx-metric-fields.csv`](data/nsx-metric-fields.csv) by `tools/build_metric_docs.py`.

- **Field** is the path in the response. `[]` marks a list.
- **Endpoints** is how many endpoints return the field. Each endpoint is listed in the CSV.
- **Lab** ✓ means the field was seen in the lab's responses. – means it comes from the spec only.
- **†** means the spec does not declare the field, but the lab returns it.
- The category is a keyword heuristic. Check the field before you alert on it.

<!-- BEGIN GENERATED: contention -->
<details>
<summary><b>VPC and subnet</b> — 288 fields, 9 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `distributed_dhcp_server_packets.errors` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of DHCP errors. |
| `dropped_by_firewall_packets.rx_dropped` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of received packets dropped by distributed firewall rules due to rule actions. |
| `dropped_by_firewall_packets.tx_dropped` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of sent packets dropped by distributed firewall rules due to rule actions. |
| `dropped_by_security_packets.bpdu_filter_dropped` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of packets dropped by "BPDU filter". |
| `dropped_by_security_packets.dhcp_client_dropped_ipv4` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of IPv4 packets dropped by "DHCP client block". |
| `dropped_by_security_packets.dhcp_client_dropped_ipv6` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of IPv6 packets dropped by "DHCP client block". |
| `dropped_by_security_packets.dhcp_server_dropped_ipv4` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of IPv4 packets dropped by "DHCP server block". |
| `dropped_by_security_packets.dhcp_server_dropped_ipv6` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of IPv6 packets dropped by "DHCP server block". |
| `mac_learning.mac_not_learned_packets_dropped` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of packets with unknown source MAC address that are dropped without learning the source MAC address. Applicable only when the MA… |
| `results[].statistics.l7_reject_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Rejected counters received by the rule. |
| `results[].statistics.l7_reject_with_response_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Rejected with Response counters received by the rule. |
| `results[].statistics.results[].l7_reject_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Rejected counters received by the rule. |
| `results[].statistics.results[].l7_reject_with_response_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Rejected with Response counters received by the rule. |
| `rx_bytes.dropped` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |
| `rx_bytes.unknown_unicast` | integer | 2 | – | Gauge: instantaneous value | The number of unknown unicast packets or bytes. |
| `rx_packets.dropped` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |
| `rx_packets.unknown_unicast` | integer | 2 | – | Gauge: instantaneous value | The number of unknown unicast packets or bytes. |
| `tx_bytes.dropped` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |
| `tx_bytes.unknown_unicast` | integer | 2 | – | Gauge: instantaneous value | The number of unknown unicast packets or bytes. |
| `tx_packets.dropped` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |
| `tx_packets.unknown_unicast` | integer | 2 | – | Gauge: instantaneous value | The number of unknown unicast packets or bytes. |
| `errors` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of DHCP errors |
| `external_traffic.rx.destination_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to destination_unsupported |
| `external_traffic.rx.dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of error packets |
| `external_traffic.rx.firewall_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by firewall |
| `external_traffic.rx.ipsec_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by ipsec |
| `external_traffic.rx.ipsec_no_sa_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by ipsec no sa |
| `external_traffic.rx.ipsec_no_vti_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by ipsec no vti |
| `external_traffic.rx.ipv6_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped ipv6 packets |
| `external_traffic.rx.kni_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped kni packets |
| `external_traffic.rx.l4port_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped l4port_unsupported packets |
| `external_traffic.rx.malformed_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped malformed packets |
| `external_traffic.rx.no_receiver_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped no receiver packets |
| `external_traffic.rx.proto_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of proto unsupported packets dropped |
| `external_traffic.rx.redirect_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to redirection |
| `external_traffic.rx.rpf_check_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to rpf check |
| `external_traffic.rx.ttl_exceeded_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to exceeding ttl |
| `external_traffic.tx.destination_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to destination_unsupported |
| `external_traffic.tx.dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of error packets |
| `external_traffic.tx.firewall_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by firewall |
| `external_traffic.tx.ipsec_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by ipsec |
| `external_traffic.tx.ipsec_no_sa_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by ipsec no sa |
| `external_traffic.tx.ipsec_no_vti_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by ipsec no vti |
| `external_traffic.tx.ipv6_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped ipv6 packets |
| `external_traffic.tx.kni_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped kni packets |
| `external_traffic.tx.l4port_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped l4port_unsupported packets |
| `external_traffic.tx.malformed_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped malformed packets |
| `external_traffic.tx.no_receiver_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped no receiver packets |
| `external_traffic.tx.proto_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of proto unsupported packets dropped |
| `external_traffic.tx.redirect_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to redirection |
| `external_traffic.tx.rpf_check_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to rpf check |
| `external_traffic.tx.ttl_exceeded_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to exceeding ttl |
| `gateway_interface.rx.dad_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `gateway_interface.rx.destination_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `gateway_interface.rx.dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `gateway_interface.rx.firewall_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `gateway_interface.rx.frag_needed_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `gateway_interface.rx.ipsec_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `gateway_interface.rx.ipsec_no_sa_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `gateway_interface.rx.ipsec_no_vti_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `gateway_interface.rx.ipsec_pol_block_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `gateway_interface.rx.ipsec_pol_err_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `gateway_interface.rx.ipv6_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `gateway_interface.rx.kni_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `gateway_interface.rx.l4port_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `gateway_interface.rx.malformed_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `gateway_interface.rx.no_arp_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `gateway_interface.rx.no_linked_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `gateway_interface.rx.no_mem_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `gateway_interface.rx.no_receiver_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `gateway_interface.rx.no_route_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `gateway_interface.rx.non_ip_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `gateway_interface.rx.policy_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `gateway_interface.rx.proto_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `gateway_interface.rx.redirect_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `gateway_interface.rx.rpf_check_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `gateway_interface.rx.service_insert_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `gateway_interface.rx.ttl_exceeded_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `gateway_interface.tx.dad_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `gateway_interface.tx.destination_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `gateway_interface.tx.dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `gateway_interface.tx.firewall_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `gateway_interface.tx.frag_needed_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `gateway_interface.tx.ipsec_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `gateway_interface.tx.ipsec_no_sa_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `gateway_interface.tx.ipsec_no_vti_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `gateway_interface.tx.ipsec_pol_block_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `gateway_interface.tx.ipsec_pol_err_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `gateway_interface.tx.ipv6_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `gateway_interface.tx.kni_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `gateway_interface.tx.l4port_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `gateway_interface.tx.malformed_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `gateway_interface.tx.no_arp_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `gateway_interface.tx.no_linked_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `gateway_interface.tx.no_mem_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `gateway_interface.tx.no_receiver_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `gateway_interface.tx.no_route_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `gateway_interface.tx.non_ip_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `gateway_interface.tx.policy_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `gateway_interface.tx.proto_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `gateway_interface.tx.redirect_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `gateway_interface.tx.rpf_check_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `gateway_interface.tx.service_insert_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `gateway_interface.tx.ttl_exceeded_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `internal_traffic.rx.dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of error packets |
| `internal_traffic.tx.dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of error packets |
| `nsxt_fp.rx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx packet drops of ENS Fastpath / Not applicable for FC Module. |
| `nsxt_fp.rx_drops_sp` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx pkts drops of slowpath / Not applicable for FC Module. |
| `nsxt_fp.rx_drops_uplink` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx packet drops of ENS Uplink / Not applicable for FC Module. |
| `nsxt_fp.tx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx packet drops of ENS Fastpath / Count of packets dropped at FC lookup of vnic |
| `nsxt_fp.tx_drops_sp` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx pkts drops by slowpath / Not applicable for FC Module. |
| `nsxt_fp.tx_drops_uplink` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx packet drops of ENS Uplink / Count of packets dropped at FC lookup of Uplink. |
| `nsxt_swsec.bpdu_filter_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of packets dropped by BPDU Filtering. When the BPDU Filter is enabled, traffic to the configured BPDU destination MAC addresses |
| `nsxt_swsec.dhcp_client_block_ipv4_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv4 DHCP packets dropped by DHCP Client Block. DHCP Client Block prevents a VM from acquiring DHCP IP address by blocking DHCP r… |
| `nsxt_swsec.dhcp_client_block_ipv6_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of DHCPv6 packets dropped by DHCP Client Block. DHCP Client Block prevents a VM from acquiring DHCP IP address by blocking DHCP requ… |
| `nsxt_swsec.dhcp_client_validate_ipv4_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv4 DHCP packets dropped because addresses in the payload were not valid |
| `nsxt_swsec.dhcp_server_block_ipv4_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv4 DHCP packets dropped by DHCP Server Block. DHCP Server Block blocks traffic from a DHCP Server to a DHCP Client |
| `nsxt_swsec.dhcp_server_block_ipv6_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of DHCPv6 packets dropped by DHCP Server Block. DHCP Server Block blocks traffic from a DHCP Server to a DHCP Client |
| `nsxt_swsec.nd_parse_errors` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv 6 Router Advertisement packets dropped by RA Guard. |
| `nsxt_swsec.ra_guard_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv6 Neighbor Discovery (ND) packets which were not correctly parsed |
| `nsxt_swsec.rx_rate_limit_bcast_drops` | integer | 1 | – | Gauge: instantaneous value | Number of ingress packets dropped by broadcast Rate Limiting |
| `nsxt_swsec.rx_rate_limit_mcast_drops` | integer | 1 | – | Gauge: instantaneous value | Number of ingress packets dropped by multicast Rate Limiting |
| `nsxt_swsec.spoof_guard_arp_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv6 packets dropped by Spoof Guard. SpoofGuard protects against IP spoofing by maintaining a reference table of , VM names and I… |
| `nsxt_swsec.spoof_guard_ipv4_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv4 packets dropped by Spoof Guard. SpoofGuard protects against IP spoofing by maintaining a reference table of , VM names and I… |
| `nsxt_swsec.spoof_guard_ipv6_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv6 Neighbor Discovery (ND) packets dropped by Spoof Guard. SpoofGuard protects against ND Spoofing by filtering out ND packets… |
| `nsxt_swsec.spoof_guard_nd_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of ARP packets dropped by Spoof Guard. Spoof Guard protects against malicious ARP spoofing attacks by keeping track of , MAC and IP… |
| `nsxt_swsec.spoof_guard_non_ip_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of Non-IP packets dropped by Spoof Guard |
| `nsxt_swsec.tx_rate_limit_bcast_drops` | integer | 1 | – | Gauge: instantaneous value | Number of egress packets dropped by broadcast Rate Limiting |
| `nsxt_swsec.tx_rate_limit_mcast_drops` | integer | 1 | – | Gauge: instantaneous value | Number of egress packets dropped by multicast Rate Limiting |
| `nsxt_vdl2.arp_proxy_req_fail_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of ARPs failed to send on uplinks for CCP unaware bindings |
| `nsxt_vdl2.arp_proxy_resp_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of ARP response failed for each ARP suppressed packets |
| `nsxt_vdl2.leaf_rx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total drops at VDL2LeafInput IOChain of a switchport |
| `nsxt_vdl2.leaf_rx_ref_port_not_found_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | VDL2LeafInput drops as trunk port is not in logical switch |
| `nsxt_vdl2.leaf_rx_system_err_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | VDL2LeafInput drops on an LS due to system errors |
| `nsxt_vdl2.leaf_tx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total drops at VDL2LeafOutput IOChain of a switchport |
| `nsxt_vdl2.mac_tbl_lookup_flood` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of unicast packets flooded onto remote VTEPs due to MAC table full |
| `nsxt_vdl2.mac_tbl_lookup_full` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of VM MAC query to CCP failure due to MAC table full |
| `nsxt_vdl2.mac_tbl_update_full` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of packet's SMAC learning failed at uplink due to MAC table full |
| `nsxt_vdl2.mcast_proxy_rx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of BUM replicated packets dropped at MTEP TN at uplink input IOChain |
| `nsxt_vdl2.mcast_proxy_tx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of BUM packets dropped at uplink output IOChain |
| `nsxt_vdl2.nd_proxy_req_fail_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of ND packets failed to send on uplinks for CCP unaware bindings |
| `nsxt_vdl2.nd_proxy_resp_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of ND response failed for each ND suppressed packets |
| `nsxt_vdl2.nested_tn_mcast_proxy_diff_vlan_tx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of BUM replicated packet drops destined to nested TN |
| `nsxt_vdl2.nested_tn_mcast_proxy_same_vlan_tx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of BUM replicated packet drops destined to nested TN |
| `nsxt_vdl2.uplink_rx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets from underlay that are dropped at uplink input IOChain |
| `nsxt_vdl2.uplink_rx_guest_vlan_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drop at uplink input IOChain due to failure to remove guest VLAN tag |
| `nsxt_vdl2.uplink_rx_invalid_encap_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets dropped at uplink input IOChain due to incorrect Encap |
| `nsxt_vdl2.uplink_rx_mcast_invalid_dr_uplink_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of IP multicast packets dropped at unexpected DR uplink |
| `nsxt_vdl2.uplink_rx_system_err_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drop at uplink input IOChain due to system errors |
| `nsxt_vdl2.uplink_rx_wrong_dest_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drop at uplink port input IOChain due to incorrect destination VTEP IP |
| `nsxt_vdl2.uplink_tx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total DVS sent packet drops at uplink output IOChain |
| `nsxt_vdl2.uplink_tx_flood_rate_limit` | integer | 1 | – | Gauge: instantaneous value | Count of rate limited unknown unicast packets at uplink output IOChain |
| `nsxt_vdl2.uplink_tx_invalid_frame_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of invalid packets dropped at uplink IOChain |
| `nsxt_vdl2.uplink_tx_invalid_state_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet drops at uplink IOChain due to incorrect uplink VLAN configuration |
| `nsxt_vdl2.uplink_tx_nested_tn_repl_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets to nested TN dropped at uplink output IOChain |
| `nsxt_vdl2.uplink_tx_teaming_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets dropped at uplink IOChain due to uplink teaming failure |
| `nsxt_vdl2.uplink_tx_ucast_flood` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of unknown unicast packets at uplink output IOChain |
| `nsxt_vdrb.arp_hold_pkt_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The drops of packet(IPv4) pending on ARP resolution |
| `nsxt_vdrb.drop_route_ipv4_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet(IPv4) matching drop routes |
| `nsxt_vdrb.drop_route_ipv6_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet(IPv6) matching drop routes |
| `nsxt_vdrb.no_route_ipv4_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | No IPv4 routes |
| `nsxt_vdrb.no_route_ipv6_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | No IPv6 routes |
| `nsxt_vdrb.ns_hold_pkt_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The drops of packet(IPv6) pending on neighbor resolution |
| `nsxt_vdrb.pkt_attr_error_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packets which failed attribute operation |
| `nsxt_vdrb.rpf_ipv4_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Reverse path forwarding drops of packet(IPv4) |
| `nsxt_vdrb.rpf_ipv6_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Reverse path forwarding drops of packet(IPv6) |
| `nsxt_vdrb.rx_pkt_parsing_error_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packets failed to be parsed |
| `nsxt_vdrb.ttl_ipv4_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet(IPv4) drops due to low TTL |
| `nsxt_vdrb.ttl_ipv6_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet(IPv6) drops due to low TTL |
| `nsxt_vdrb.tx_dispatch_queue_too_long_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packets being tail dropped in the txDispatchQueue |
| `nsxt_vsip.alg_handler_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | alg handler error. |
| `nsxt_vsip.bad_offset_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | bad-offset. |
| `nsxt_vsip.bad_timestamp_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | bad-timestamp. |
| `nsxt_vsip.congestion_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | congestion. |
| `nsxt_vsip.fragment_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | fragment. |
| `nsxt_vsip.handshake_error_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | 3wh error. |
| `nsxt_vsip.icmp_err_pkt_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | icmp errpkt drop. |
| `nsxt_vsip.icmp_error_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | icmp error. |
| `nsxt_vsip.icmp_flood_overlimit_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | ICMP flood overlimit. |
| `nsxt_vsip.ignored_offloaded_fpdrops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Ignored offloaded FP. |
| `nsxt_vsip.ignored_offloaded_spdrops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Ignored offloaded SP |
| `nsxt_vsip.ip_option_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | ip-option. |
| `nsxt_vsip.l7_alert_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | L7 alert. |
| `nsxt_vsip.l7_attr_error_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | L7 attr error. |
| `nsxt_vsip.lb_reject_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | LB Reject. |
| `nsxt_vsip.match_drop_rule_rx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Rx pkts dropped by hitting drop/reject rule. |
| `nsxt_vsip.match_drop_rule_tx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Tx pkts dropped by hitting drop/reject rule. |
| `nsxt_vsip.memory_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | memory. |
| `nsxt_vsip.normalize_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | normalize. |
| `nsxt_vsip.other_flood_overlimit_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | OTHER flood overlimit. |
| `nsxt_vsip.pkts_frag_queued_v4_misc` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | pkts-frag-queued-v4. |
| `nsxt_vsip.pkts_frag_queued_v6_misc` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | pkts-frag-queued-v6. |
| `nsxt_vsip.proto_cksum_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | proto-cksum. |
| `nsxt_vsip.rx_ipv4_drop_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv4 drop packets |
| `nsxt_vsip.rx_ipv4_reject_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv4 reject packets. |
| `nsxt_vsip.rx_ipv6_drop_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv6 drop packets. |
| `nsxt_vsip.rx_ipv6_reject_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv6 reject packets. |
| `nsxt_vsip.rx_l2_drop_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received layer 2 drop packets. |
| `nsxt_vsip.seqno_bad_ack_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno bad ack |
| `nsxt_vsip.seqno_gt_max_ack_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno gt maxack |
| `nsxt_vsip.seqno_lt_minack_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno lt minack |
| `nsxt_vsip.seqno_old_ack_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno old ack |
| `nsxt_vsip.seqno_old_retrans_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno old retrans. |
| `nsxt_vsip.seqno_outside_window_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno outside window. |
| `nsxt_vsip.short_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | short. |
| `nsxt_vsip.spoof_guard_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | spoofguard. |
| `nsxt_vsip.state_insert_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | state-insert. |
| `nsxt_vsip.state_limit_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | state-limit. |
| `nsxt_vsip.state_mismatch_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | state-mismatch. |
| `nsxt_vsip.strict_no_syn_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | strict no syn. |
| `nsxt_vsip.syn_expected_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | SYN Expected. |
| `nsxt_vsip.syn_proxy_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | synproxy. |
| `nsxt_vsip.tcp_flood_overlimit_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | TCP flood overlimit. |
| `nsxt_vsip.tx_ipv4_drop_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv4 drop packets |
| `nsxt_vsip.tx_ipv4_reject_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv4 reject packets. |
| `nsxt_vsip.tx_ipv6_drop_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv6 drop packets. |
| `nsxt_vsip.tx_ipv6_reject_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv6 reject packets. |
| `nsxt_vsip.tx_l2_drop_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent layer 2 drop packets. |
| `nsxt_vsip.udp_flood_overlimit_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | UDP flood overlimit. |
| `nsxt_vswitch.forged_transmit_rx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to forged transmits disabled. |
| `nsxt_vswitch.unknown_unicast_rx_uplink_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Unknown unicast flooded packets received from uplink. |
| `nsxt_vswitch.unknown_unicast_tx_uplink_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Unknown unicast flooded packets sent on the uplink. |
| `nsxt_vswitch.vlan_tag_mismatch_rx` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to VLAN tag mismatch of packets received by vswitch. |
| `nsxt_vswitch.vlan_tag_mismatch_rx_mcast` | integer | 1 | – | Gauge: instantaneous value | Drops due to VLAN tag mismatch of packets received by vswitch. |
| `nsxt_vswitch.vlan_tag_mismatch_tx` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to VLAN tag mismatch of packets forwarded by vswitch. |
| `nsxt_vswitch.vlan_tag_mismatch_tx_mcast` | integer | 1 | – | Gauge: instantaneous value | Drops due to VLAN tag mismatch of packets forwarded by vswitch. |
| `nsxt_vswitch.vni_tag_mismatch_tx` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to VNI tag mismatch of packets forwarded by vswitch. |
| `nsxt_vswitch.vni_tag_mismatch_tx_mcast` | integer | 1 | – | Gauge: instantaneous value | Drops due to VNI tag mismatch of packets forwarded by vswitch. |
| `rx.dad_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `rx.destination_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `rx.dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `rx.firewall_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `rx.frag_needed_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `rx.ipsec_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `rx.ipsec_no_sa_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `rx.ipsec_no_vti_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `rx.ipsec_pol_block_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `rx.ipsec_pol_err_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `rx.ipv6_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `rx.kni_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `rx.l4port_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `rx.malformed_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `rx.no_arp_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `rx.no_linked_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `rx.no_mem_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `rx.no_receiver_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `rx.no_route_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `rx.non_ip_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `rx.policy_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `rx.proto_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `rx.redirect_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `rx.rpf_check_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `rx.service_insert_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `rx.ttl_exceeded_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `tx.dad_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `tx.destination_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `tx.dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `tx.firewall_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `tx.frag_needed_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `tx.ipsec_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `tx.ipsec_no_sa_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `tx.ipsec_no_vti_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `tx.ipsec_pol_block_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `tx.ipsec_pol_err_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `tx.ipv6_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `tx.kni_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `tx.l4port_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `tx.malformed_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `tx.no_arp_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `tx.no_linked_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `tx.no_mem_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `tx.no_receiver_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `tx.no_route_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `tx.non_ip_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `tx.policy_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `tx.proto_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `tx.redirect_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `tx.rpf_check_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `tx.service_insert_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `tx.ttl_exceeded_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `vlan_extension.vlan_to_vpc_bytes.dropped` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |
| `vlan_extension.vlan_to_vpc_bytes.unknown_unicast` | integer | 1 | – | Gauge: instantaneous value | The total unkown unicast packets or bytes |
| `vlan_extension.vlan_to_vpc_packets.dropped` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |
| `vlan_extension.vlan_to_vpc_packets.unknown_unicast` | integer | 1 | – | Gauge: instantaneous value | The total unkown unicast packets or bytes |
| `vlan_extension.vpc_to_vlan_bytes.dropped` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |
| `vlan_extension.vpc_to_vlan_bytes.unknown_unicast` | integer | 1 | – | Gauge: instantaneous value | The total unkown unicast packets or bytes |
| `vlan_extension.vpc_to_vlan_packets.dropped` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |
| `vlan_extension.vpc_to_vlan_packets.unknown_unicast` | integer | 1 | – | Gauge: instantaneous value | The total unkown unicast packets or bytes |

</details>

<details>
<summary><b>Segment and port</b> — 243 fields, 27 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `rx_bytes.dropped` | integer | 15 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |
| `rx_bytes.unknown_unicast` | integer | 15 | – | Gauge: instantaneous value | The number of unknown unicast packets or bytes. |
| `rx_packets.dropped` | integer | 15 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |
| `rx_packets.unknown_unicast` | integer | 15 | – | Gauge: instantaneous value | The number of unknown unicast packets or bytes. |
| `tx_bytes.dropped` | integer | 15 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |
| `tx_bytes.unknown_unicast` | integer | 15 | – | Gauge: instantaneous value | The number of unknown unicast packets or bytes. |
| `tx_packets.dropped` | integer | 15 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |
| `tx_packets.unknown_unicast` | integer | 15 | – | Gauge: instantaneous value | The number of unknown unicast packets or bytes. |
| `distributed_dhcp_server_packets.errors` | integer | 12 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of DHCP errors. |
| `dropped_by_firewall_packets.rx_dropped` | integer | 12 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of received packets dropped by distributed firewall rules due to rule actions. |
| `dropped_by_firewall_packets.tx_dropped` | integer | 12 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of sent packets dropped by distributed firewall rules due to rule actions. |
| `dropped_by_security_packets.bpdu_filter_dropped` | integer | 12 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of packets dropped by "BPDU filter". |
| `dropped_by_security_packets.dhcp_client_dropped_ipv4` | integer | 12 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of IPv4 packets dropped by "DHCP client block". |
| `dropped_by_security_packets.dhcp_client_dropped_ipv6` | integer | 12 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of IPv6 packets dropped by "DHCP client block". |
| `dropped_by_security_packets.dhcp_server_dropped_ipv4` | integer | 12 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of IPv4 packets dropped by "DHCP server block". |
| `dropped_by_security_packets.dhcp_server_dropped_ipv6` | integer | 12 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of IPv6 packets dropped by "DHCP server block". |
| `mac_learning.mac_not_learned_packets_dropped` | integer | 12 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of packets with unknown source MAC address that are dropped without learning the source MAC address. Applicable only when the MA… |
| `nsxt_fp.rx_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx packet drops of ENS Fastpath / Not applicable for FC Module. |
| `nsxt_fp.rx_drops_sp` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx pkts drops of slowpath / Not applicable for FC Module. |
| `nsxt_fp.rx_drops_uplink` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx packet drops of ENS Uplink / Not applicable for FC Module. |
| `nsxt_fp.tx_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx packet drops of ENS Fastpath / Count of packets dropped at FC lookup of vnic |
| `nsxt_fp.tx_drops_sp` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx pkts drops by slowpath / Not applicable for FC Module. |
| `nsxt_fp.tx_drops_uplink` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx packet drops of ENS Uplink / Count of packets dropped at FC lookup of Uplink. |
| `nsxt_swsec.bpdu_filter_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of packets dropped by BPDU Filtering. When the BPDU Filter is enabled, traffic to the configured BPDU destination MAC addresses |
| `nsxt_swsec.dhcp_client_block_ipv4_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv4 DHCP packets dropped by DHCP Client Block. DHCP Client Block prevents a VM from acquiring DHCP IP address by blocking DHCP r… |
| `nsxt_swsec.dhcp_client_block_ipv6_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of DHCPv6 packets dropped by DHCP Client Block. DHCP Client Block prevents a VM from acquiring DHCP IP address by blocking DHCP requ… |
| `nsxt_swsec.dhcp_client_validate_ipv4_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv4 DHCP packets dropped because addresses in the payload were not valid |
| `nsxt_swsec.dhcp_server_block_ipv4_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv4 DHCP packets dropped by DHCP Server Block. DHCP Server Block blocks traffic from a DHCP Server to a DHCP Client |
| `nsxt_swsec.dhcp_server_block_ipv6_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of DHCPv6 packets dropped by DHCP Server Block. DHCP Server Block blocks traffic from a DHCP Server to a DHCP Client |
| `nsxt_swsec.nd_parse_errors` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv 6 Router Advertisement packets dropped by RA Guard. |
| `nsxt_swsec.ra_guard_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv6 Neighbor Discovery (ND) packets which were not correctly parsed |
| `nsxt_swsec.rx_rate_limit_bcast_drops` | integer | 6 | – | Gauge: instantaneous value | Number of ingress packets dropped by broadcast Rate Limiting |
| `nsxt_swsec.rx_rate_limit_mcast_drops` | integer | 6 | – | Gauge: instantaneous value | Number of ingress packets dropped by multicast Rate Limiting |
| `nsxt_swsec.spoof_guard_arp_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv6 packets dropped by Spoof Guard. SpoofGuard protects against IP spoofing by maintaining a reference table of , VM names and I… |
| `nsxt_swsec.spoof_guard_ipv4_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv4 packets dropped by Spoof Guard. SpoofGuard protects against IP spoofing by maintaining a reference table of , VM names and I… |
| `nsxt_swsec.spoof_guard_ipv6_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of IPv6 Neighbor Discovery (ND) packets dropped by Spoof Guard. SpoofGuard protects against ND Spoofing by filtering out ND packets… |
| `nsxt_swsec.spoof_guard_nd_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of ARP packets dropped by Spoof Guard. Spoof Guard protects against malicious ARP spoofing attacks by keeping track of , MAC and IP… |
| `nsxt_swsec.spoof_guard_non_ip_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of Non-IP packets dropped by Spoof Guard |
| `nsxt_swsec.tx_rate_limit_bcast_drops` | integer | 6 | – | Gauge: instantaneous value | Number of egress packets dropped by broadcast Rate Limiting |
| `nsxt_swsec.tx_rate_limit_mcast_drops` | integer | 6 | – | Gauge: instantaneous value | Number of egress packets dropped by multicast Rate Limiting |
| `nsxt_vdl2.arp_proxy_req_fail_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of ARPs failed to send on uplinks for CCP unaware bindings |
| `nsxt_vdl2.arp_proxy_resp_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of ARP response failed for each ARP suppressed packets |
| `nsxt_vdl2.leaf_rx_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total drops at VDL2LeafInput IOChain of a switchport |
| `nsxt_vdl2.leaf_rx_ref_port_not_found_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | VDL2LeafInput drops as trunk port is not in logical switch |
| `nsxt_vdl2.leaf_rx_system_err_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | VDL2LeafInput drops on an LS due to system errors |
| `nsxt_vdl2.leaf_tx_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total drops at VDL2LeafOutput IOChain of a switchport |
| `nsxt_vdl2.mac_tbl_lookup_flood` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of unicast packets flooded onto remote VTEPs due to MAC table full |
| `nsxt_vdl2.mac_tbl_lookup_full` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of VM MAC query to CCP failure due to MAC table full |
| `nsxt_vdl2.mac_tbl_update_full` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of packet's SMAC learning failed at uplink due to MAC table full |
| `nsxt_vdl2.mcast_proxy_rx_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of BUM replicated packets dropped at MTEP TN at uplink input IOChain |
| `nsxt_vdl2.mcast_proxy_tx_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of BUM packets dropped at uplink output IOChain |
| `nsxt_vdl2.nd_proxy_req_fail_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of ND packets failed to send on uplinks for CCP unaware bindings |
| `nsxt_vdl2.nd_proxy_resp_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of ND response failed for each ND suppressed packets |
| `nsxt_vdl2.nested_tn_mcast_proxy_diff_vlan_tx_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of BUM replicated packet drops destined to nested TN |
| `nsxt_vdl2.nested_tn_mcast_proxy_same_vlan_tx_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of BUM replicated packet drops destined to nested TN |
| `nsxt_vdl2.uplink_rx_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets from underlay that are dropped at uplink input IOChain |
| `nsxt_vdl2.uplink_rx_guest_vlan_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drop at uplink input IOChain due to failure to remove guest VLAN tag |
| `nsxt_vdl2.uplink_rx_invalid_encap_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets dropped at uplink input IOChain due to incorrect Encap |
| `nsxt_vdl2.uplink_rx_mcast_invalid_dr_uplink_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of IP multicast packets dropped at unexpected DR uplink |
| `nsxt_vdl2.uplink_rx_system_err_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drop at uplink input IOChain due to system errors |
| `nsxt_vdl2.uplink_rx_wrong_dest_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drop at uplink port input IOChain due to incorrect destination VTEP IP |
| `nsxt_vdl2.uplink_tx_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total DVS sent packet drops at uplink output IOChain |
| `nsxt_vdl2.uplink_tx_flood_rate_limit` | integer | 6 | – | Gauge: instantaneous value | Count of rate limited unknown unicast packets at uplink output IOChain |
| `nsxt_vdl2.uplink_tx_invalid_frame_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of invalid packets dropped at uplink IOChain |
| `nsxt_vdl2.uplink_tx_invalid_state_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet drops at uplink IOChain due to incorrect uplink VLAN configuration |
| `nsxt_vdl2.uplink_tx_nested_tn_repl_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets to nested TN dropped at uplink output IOChain |
| `nsxt_vdl2.uplink_tx_teaming_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets dropped at uplink IOChain due to uplink teaming failure |
| `nsxt_vdl2.uplink_tx_ucast_flood` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of unknown unicast packets at uplink output IOChain |
| `nsxt_vdrb.arp_hold_pkt_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The drops of packet(IPv4) pending on ARP resolution |
| `nsxt_vdrb.drop_route_ipv4_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet(IPv4) matching drop routes |
| `nsxt_vdrb.drop_route_ipv6_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet(IPv6) matching drop routes |
| `nsxt_vdrb.no_route_ipv4_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | No IPv4 routes |
| `nsxt_vdrb.no_route_ipv6_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | No IPv6 routes |
| `nsxt_vdrb.ns_hold_pkt_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The drops of packet(IPv6) pending on neighbor resolution |
| `nsxt_vdrb.pkt_attr_error_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packets which failed attribute operation |
| `nsxt_vdrb.rpf_ipv4_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Reverse path forwarding drops of packet(IPv4) |
| `nsxt_vdrb.rpf_ipv6_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Reverse path forwarding drops of packet(IPv6) |
| `nsxt_vdrb.rx_pkt_parsing_error_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packets failed to be parsed |
| `nsxt_vdrb.ttl_ipv4_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet(IPv4) drops due to low TTL |
| `nsxt_vdrb.ttl_ipv6_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet(IPv6) drops due to low TTL |
| `nsxt_vdrb.tx_dispatch_queue_too_long_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packets being tail dropped in the txDispatchQueue |
| `nsxt_vsip.alg_handler_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | alg handler error. |
| `nsxt_vsip.bad_offset_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | bad-offset. |
| `nsxt_vsip.bad_timestamp_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | bad-timestamp. |
| `nsxt_vsip.congestion_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | congestion. |
| `nsxt_vsip.fragment_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | fragment. |
| `nsxt_vsip.handshake_error_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | 3wh error. |
| `nsxt_vsip.icmp_err_pkt_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | icmp errpkt drop. |
| `nsxt_vsip.icmp_error_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | icmp error. |
| `nsxt_vsip.icmp_flood_overlimit_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | ICMP flood overlimit. |
| `nsxt_vsip.ignored_offloaded_fpdrops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Ignored offloaded FP. |
| `nsxt_vsip.ignored_offloaded_spdrops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Ignored offloaded SP |
| `nsxt_vsip.ip_option_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | ip-option. |
| `nsxt_vsip.l7_alert_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | L7 alert. |
| `nsxt_vsip.l7_attr_error_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | L7 attr error. |
| `nsxt_vsip.lb_reject_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | LB Reject. |
| `nsxt_vsip.match_drop_rule_rx_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Rx pkts dropped by hitting drop/reject rule. |
| `nsxt_vsip.match_drop_rule_tx_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Tx pkts dropped by hitting drop/reject rule. |
| `nsxt_vsip.memory_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | memory. |
| `nsxt_vsip.normalize_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | normalize. |
| `nsxt_vsip.other_flood_overlimit_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | OTHER flood overlimit. |
| `nsxt_vsip.pkts_frag_queued_v4_misc` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | pkts-frag-queued-v4. |
| `nsxt_vsip.pkts_frag_queued_v6_misc` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | pkts-frag-queued-v6. |
| `nsxt_vsip.proto_cksum_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | proto-cksum. |
| `nsxt_vsip.rx_ipv4_drop_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv4 drop packets |
| `nsxt_vsip.rx_ipv4_reject_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv4 reject packets. |
| `nsxt_vsip.rx_ipv6_drop_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv6 drop packets. |
| `nsxt_vsip.rx_ipv6_reject_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv6 reject packets. |
| `nsxt_vsip.rx_l2_drop_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received layer 2 drop packets. |
| `nsxt_vsip.seqno_bad_ack_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno bad ack |
| `nsxt_vsip.seqno_gt_max_ack_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno gt maxack |
| `nsxt_vsip.seqno_lt_minack_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno lt minack |
| `nsxt_vsip.seqno_old_ack_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno old ack |
| `nsxt_vsip.seqno_old_retrans_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno old retrans. |
| `nsxt_vsip.seqno_outside_window_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno outside window. |
| `nsxt_vsip.short_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | short. |
| `nsxt_vsip.spoof_guard_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | spoofguard. |
| `nsxt_vsip.state_insert_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | state-insert. |
| `nsxt_vsip.state_limit_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | state-limit. |
| `nsxt_vsip.state_mismatch_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | state-mismatch. |
| `nsxt_vsip.strict_no_syn_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | strict no syn. |
| `nsxt_vsip.syn_expected_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | SYN Expected. |
| `nsxt_vsip.syn_proxy_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | synproxy. |
| `nsxt_vsip.tcp_flood_overlimit_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | TCP flood overlimit. |
| `nsxt_vsip.tx_ipv4_drop_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv4 drop packets |
| `nsxt_vsip.tx_ipv4_reject_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv4 reject packets. |
| `nsxt_vsip.tx_ipv6_drop_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv6 drop packets. |
| `nsxt_vsip.tx_ipv6_reject_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv6 reject packets. |
| `nsxt_vsip.tx_l2_drop_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent layer 2 drop packets. |
| `nsxt_vsip.udp_flood_overlimit_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | UDP flood overlimit. |
| `nsxt_vswitch.forged_transmit_rx_drops` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to forged transmits disabled. |
| `nsxt_vswitch.unknown_unicast_rx_uplink_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Unknown unicast flooded packets received from uplink. |
| `nsxt_vswitch.unknown_unicast_tx_uplink_pkts` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Unknown unicast flooded packets sent on the uplink. |
| `nsxt_vswitch.vlan_tag_mismatch_rx` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to VLAN tag mismatch of packets received by vswitch. |
| `nsxt_vswitch.vlan_tag_mismatch_rx_mcast` | integer | 6 | – | Gauge: instantaneous value | Drops due to VLAN tag mismatch of packets received by vswitch. |
| `nsxt_vswitch.vlan_tag_mismatch_tx` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to VLAN tag mismatch of packets forwarded by vswitch. |
| `nsxt_vswitch.vlan_tag_mismatch_tx_mcast` | integer | 6 | – | Gauge: instantaneous value | Drops due to VLAN tag mismatch of packets forwarded by vswitch. |
| `nsxt_vswitch.vni_tag_mismatch_tx` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to VNI tag mismatch of packets forwarded by vswitch. |
| `nsxt_vswitch.vni_tag_mismatch_tx_mcast` | integer | 6 | – | Gauge: instantaneous value | Drops due to VNI tag mismatch of packets forwarded by vswitch. |
| `per_node_statistics[].rx.dad_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `per_node_statistics[].rx.destination_unsupported_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `per_node_statistics[].rx.dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `per_node_statistics[].rx.firewall_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `per_node_statistics[].rx.frag_needed_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `per_node_statistics[].rx.ipsec_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `per_node_statistics[].rx.ipsec_no_sa_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `per_node_statistics[].rx.ipsec_no_vti_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `per_node_statistics[].rx.ipsec_pol_block_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `per_node_statistics[].rx.ipsec_pol_err_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `per_node_statistics[].rx.ipv6_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `per_node_statistics[].rx.kni_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `per_node_statistics[].rx.l4port_unsupported_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `per_node_statistics[].rx.malformed_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `per_node_statistics[].rx.no_arp_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `per_node_statistics[].rx.no_linked_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `per_node_statistics[].rx.no_mem_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `per_node_statistics[].rx.no_receiver_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `per_node_statistics[].rx.no_route_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `per_node_statistics[].rx.non_ip_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `per_node_statistics[].rx.policy_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `per_node_statistics[].rx.proto_unsupported_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `per_node_statistics[].rx.redirect_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `per_node_statistics[].rx.rpf_check_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `per_node_statistics[].rx.service_insert_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `per_node_statistics[].rx.ttl_exceeded_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `per_node_statistics[].tx.dad_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `per_node_statistics[].tx.destination_unsupported_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `per_node_statistics[].tx.dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `per_node_statistics[].tx.firewall_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `per_node_statistics[].tx.frag_needed_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `per_node_statistics[].tx.ipsec_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `per_node_statistics[].tx.ipsec_no_sa_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `per_node_statistics[].tx.ipsec_no_vti_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `per_node_statistics[].tx.ipsec_pol_block_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `per_node_statistics[].tx.ipsec_pol_err_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `per_node_statistics[].tx.ipv6_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `per_node_statistics[].tx.kni_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `per_node_statistics[].tx.l4port_unsupported_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `per_node_statistics[].tx.malformed_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `per_node_statistics[].tx.no_arp_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `per_node_statistics[].tx.no_linked_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `per_node_statistics[].tx.no_mem_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `per_node_statistics[].tx.no_receiver_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `per_node_statistics[].tx.no_route_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `per_node_statistics[].tx.non_ip_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `per_node_statistics[].tx.policy_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `per_node_statistics[].tx.proto_unsupported_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `per_node_statistics[].tx.redirect_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `per_node_statistics[].tx.rpf_check_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `per_node_statistics[].tx.service_insert_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `per_node_statistics[].tx.ttl_exceeded_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `rx.dad_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `rx.destination_unsupported_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `rx.dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `rx.firewall_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `rx.frag_needed_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `rx.ipsec_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `rx.ipsec_no_sa_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `rx.ipsec_no_vti_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `rx.ipsec_pol_block_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `rx.ipsec_pol_err_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `rx.ipv6_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `rx.kni_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `rx.l4port_unsupported_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `rx.malformed_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `rx.no_arp_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `rx.no_linked_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `rx.no_mem_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `rx.no_receiver_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `rx.no_route_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `rx.non_ip_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `rx.policy_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `rx.proto_unsupported_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `rx.redirect_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `rx.rpf_check_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `rx.service_insert_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `rx.ttl_exceeded_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `tx.dad_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `tx.destination_unsupported_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `tx.dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `tx.firewall_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `tx.frag_needed_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `tx.ipsec_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `tx.ipsec_no_sa_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `tx.ipsec_no_vti_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `tx.ipsec_pol_block_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `tx.ipsec_pol_err_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `tx.ipv6_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `tx.kni_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `tx.l4port_unsupported_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `tx.malformed_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `tx.no_arp_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `tx.no_linked_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `tx.no_mem_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `tx.no_receiver_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `tx.no_route_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `tx.non_ip_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `tx.policy_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `tx.proto_unsupported_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `tx.redirect_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `tx.rpf_check_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `tx.service_insert_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `tx.ttl_exceeded_dropped_packets` | integer | 6 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |

</details>

<details>
<summary><b>Edge transport node and edge cluster</b> — 226 fields, 18 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].hold_down_timer` | integer | 3 | – | Gauge: instantaneous value | Wait period (seconds) before declaring peer dead |
| `results[].maximum_hop_limit` | integer | 3 | – | Gauge: instantaneous value | This value is set on TTL(time to live) of BGP header. When router receives the BGP packet, it decrements the TTL. The default value of TTL… |
| `stats_per_site[].rx.dad_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `stats_per_site[].rx.destination_unsupported_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `stats_per_site[].rx.dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `stats_per_site[].rx.firewall_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `stats_per_site[].rx.frag_needed_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `stats_per_site[].rx.ipsec_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `stats_per_site[].rx.ipsec_no_sa_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `stats_per_site[].rx.ipsec_no_vti_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `stats_per_site[].rx.ipsec_pol_block_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `stats_per_site[].rx.ipsec_pol_err_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `stats_per_site[].rx.ipv6_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `stats_per_site[].rx.kni_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `stats_per_site[].rx.l4port_unsupported_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `stats_per_site[].rx.malformed_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `stats_per_site[].rx.no_arp_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `stats_per_site[].rx.no_linked_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `stats_per_site[].rx.no_mem_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `stats_per_site[].rx.no_receiver_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `stats_per_site[].rx.no_route_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `stats_per_site[].rx.non_ip_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `stats_per_site[].rx.policy_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `stats_per_site[].rx.proto_unsupported_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `stats_per_site[].rx.redirect_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `stats_per_site[].rx.rpf_check_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `stats_per_site[].rx.service_insert_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `stats_per_site[].rx.ttl_exceeded_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `stats_per_site[].stats_per_tunnel[].rx.dad_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `stats_per_site[].stats_per_tunnel[].rx.destination_unsupported_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `stats_per_site[].stats_per_tunnel[].rx.dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `stats_per_site[].stats_per_tunnel[].rx.firewall_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `stats_per_site[].stats_per_tunnel[].rx.frag_needed_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `stats_per_site[].stats_per_tunnel[].rx.ipsec_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `stats_per_site[].stats_per_tunnel[].rx.ipsec_no_sa_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `stats_per_site[].stats_per_tunnel[].rx.ipsec_no_vti_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `stats_per_site[].stats_per_tunnel[].rx.ipsec_pol_block_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `stats_per_site[].stats_per_tunnel[].rx.ipsec_pol_err_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `stats_per_site[].stats_per_tunnel[].rx.ipv6_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `stats_per_site[].stats_per_tunnel[].rx.kni_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `stats_per_site[].stats_per_tunnel[].rx.l4port_unsupported_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `stats_per_site[].stats_per_tunnel[].rx.malformed_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `stats_per_site[].stats_per_tunnel[].rx.no_arp_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `stats_per_site[].stats_per_tunnel[].rx.no_linked_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `stats_per_site[].stats_per_tunnel[].rx.no_mem_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `stats_per_site[].stats_per_tunnel[].rx.no_receiver_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `stats_per_site[].stats_per_tunnel[].rx.no_route_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `stats_per_site[].stats_per_tunnel[].rx.non_ip_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `stats_per_site[].stats_per_tunnel[].rx.policy_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `stats_per_site[].stats_per_tunnel[].rx.proto_unsupported_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `stats_per_site[].stats_per_tunnel[].rx.redirect_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `stats_per_site[].stats_per_tunnel[].rx.rpf_check_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `stats_per_site[].stats_per_tunnel[].rx.service_insert_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `stats_per_site[].stats_per_tunnel[].rx.ttl_exceeded_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `stats_per_site[].stats_per_tunnel[].tx.dad_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `stats_per_site[].stats_per_tunnel[].tx.destination_unsupported_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `stats_per_site[].stats_per_tunnel[].tx.dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `stats_per_site[].stats_per_tunnel[].tx.firewall_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `stats_per_site[].stats_per_tunnel[].tx.frag_needed_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `stats_per_site[].stats_per_tunnel[].tx.ipsec_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `stats_per_site[].stats_per_tunnel[].tx.ipsec_no_sa_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `stats_per_site[].stats_per_tunnel[].tx.ipsec_no_vti_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `stats_per_site[].stats_per_tunnel[].tx.ipsec_pol_block_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `stats_per_site[].stats_per_tunnel[].tx.ipsec_pol_err_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `stats_per_site[].stats_per_tunnel[].tx.ipv6_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `stats_per_site[].stats_per_tunnel[].tx.kni_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `stats_per_site[].stats_per_tunnel[].tx.l4port_unsupported_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `stats_per_site[].stats_per_tunnel[].tx.malformed_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `stats_per_site[].stats_per_tunnel[].tx.no_arp_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `stats_per_site[].stats_per_tunnel[].tx.no_linked_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `stats_per_site[].stats_per_tunnel[].tx.no_mem_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `stats_per_site[].stats_per_tunnel[].tx.no_receiver_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `stats_per_site[].stats_per_tunnel[].tx.no_route_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `stats_per_site[].stats_per_tunnel[].tx.non_ip_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `stats_per_site[].stats_per_tunnel[].tx.policy_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `stats_per_site[].stats_per_tunnel[].tx.proto_unsupported_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `stats_per_site[].stats_per_tunnel[].tx.redirect_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `stats_per_site[].stats_per_tunnel[].tx.rpf_check_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `stats_per_site[].stats_per_tunnel[].tx.service_insert_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `stats_per_site[].stats_per_tunnel[].tx.ttl_exceeded_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `stats_per_site[].tx.dad_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `stats_per_site[].tx.destination_unsupported_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `stats_per_site[].tx.dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `stats_per_site[].tx.firewall_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `stats_per_site[].tx.frag_needed_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `stats_per_site[].tx.ipsec_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `stats_per_site[].tx.ipsec_no_sa_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `stats_per_site[].tx.ipsec_no_vti_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `stats_per_site[].tx.ipsec_pol_block_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `stats_per_site[].tx.ipsec_pol_err_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `stats_per_site[].tx.ipv6_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `stats_per_site[].tx.kni_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `stats_per_site[].tx.l4port_unsupported_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `stats_per_site[].tx.malformed_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `stats_per_site[].tx.no_arp_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `stats_per_site[].tx.no_linked_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `stats_per_site[].tx.no_mem_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `stats_per_site[].tx.no_receiver_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `stats_per_site[].tx.no_route_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `stats_per_site[].tx.non_ip_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `stats_per_site[].tx.policy_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `stats_per_site[].tx.proto_unsupported_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `stats_per_site[].tx.redirect_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `stats_per_site[].tx.rpf_check_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `stats_per_site[].tx.service_insert_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `stats_per_site[].tx.ttl_exceeded_dropped_packets` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `edge_nodes[].neighbor_status[].connection_drop_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of connection drop |
| `member_status[].neighbor_status[].connection_drop_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of connection drop |
| `neighbor_status[].connection_drop_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of connection drop |
| `rx_stats.dad_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `rx_stats.destination_unsupported_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `rx_stats.dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `rx_stats.firewall_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `rx_stats.frag_needed_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `rx_stats.ipsec_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `rx_stats.ipsec_no_sa_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `rx_stats.ipsec_no_vti_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `rx_stats.ipsec_pol_block_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `rx_stats.ipsec_pol_err_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `rx_stats.ipv6_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `rx_stats.kni_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `rx_stats.l4port_unsupported_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `rx_stats.malformed_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `rx_stats.no_arp_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `rx_stats.no_linked_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `rx_stats.no_mem_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `rx_stats.no_receiver_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `rx_stats.no_route_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `rx_stats.non_ip_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `rx_stats.policy_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `rx_stats.proto_unsupported_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `rx_stats.redirect_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `rx_stats.rpf_check_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `rx_stats.service_insert_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `rx_stats.ttl_exceeded_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `tx_stats.dad_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `tx_stats.destination_unsupported_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `tx_stats.dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `tx_stats.firewall_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `tx_stats.frag_needed_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `tx_stats.ipsec_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `tx_stats.ipsec_no_sa_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `tx_stats.ipsec_no_vti_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `tx_stats.ipsec_pol_block_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `tx_stats.ipsec_pol_err_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `tx_stats.ipv6_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `tx_stats.kni_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `tx_stats.l4port_unsupported_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `tx_stats.malformed_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `tx_stats.no_arp_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `tx_stats.no_linked_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `tx_stats.no_mem_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `tx_stats.no_receiver_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `tx_stats.no_route_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `tx_stats.non_ip_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `tx_stats.policy_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `tx_stats.proto_unsupported_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `tx_stats.redirect_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `tx_stats.rpf_check_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `tx_stats.service_insert_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `tx_stats.ttl_exceeded_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `evpn_tunnel_status.bfd_diagnostic.echo_function_failed_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of tunnels with echo function failed diagnostic message |
| `results[].evpn_tunnel_status.bfd_diagnostic.echo_function_failed_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of tunnels with echo function failed diagnostic message |
| `results[].tunnel_status.bfd_diagnostic.echo_function_failed_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of tunnels with echo function failed diagnostic message |
| `rx.dad_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `rx.destination_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `rx.dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `rx.firewall_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `rx.frag_needed_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `rx.ipsec_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `rx.ipsec_no_sa_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `rx.ipsec_no_vti_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `rx.ipsec_pol_block_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `rx.ipsec_pol_err_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `rx.ipv6_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `rx.kni_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `rx.l4port_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `rx.malformed_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `rx.no_arp_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `rx.no_linked_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `rx.no_mem_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `rx.no_receiver_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `rx.no_route_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `rx.non_ip_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `rx.policy_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `rx.proto_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `rx.redirect_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `rx.rpf_check_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `rx.service_insert_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `rx.ttl_exceeded_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `rx_drop_no_match` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the edge transport node interface since the uptime due to one of the below reasons.  - MAC lookup fa… |
| `rx_dropped` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets dropped since the uptime |
| `rx_errors` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of erroneous incoming packets received on the interface since the uptime. This will be reset on transport node restart. |
| `rx_misses` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The Total number of incoming packets dropped on the edge transport node interface since the uptime.For DPDK interface this could be due to… |
| `rx_nombufs` | integer | 1 | – | Gauge: instantaneous value | The total number of incoming packets dropped on the edge transport node interface since the uptime due to Rx mBuf allocation failure. This… |
| `tunnel_status.bfd_diagnostic.echo_function_failed_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of tunnels with echo function failed diagnostic message |
| `tx.dad_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `tx.destination_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `tx.dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `tx.firewall_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `tx.frag_needed_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `tx.ipsec_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `tx.ipsec_no_sa_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `tx.ipsec_no_vti_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `tx.ipsec_pol_block_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `tx.ipsec_pol_err_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `tx.ipv6_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `tx.kni_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `tx.l4port_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `tx.malformed_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `tx.no_arp_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `tx.no_linked_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `tx.no_mem_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `tx.no_receiver_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `tx.no_route_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `tx.non_ip_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `tx.policy_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `tx.proto_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `tx.redirect_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `tx.rpf_check_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `tx.service_insert_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `tx.ttl_exceeded_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `tx_carrier` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets for carrier losses detected on transmit. Available only for Host Transport Node. |
| `tx_dropped` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets dropped on transmit since the uptime |
| `tx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of outgoing packets dropped on the DPDK interface of the edge transport node due to Tx buffer overflow since the uptime. T… |
| `tx_errors` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of erroneous packets failed to be transmitted since the uptime. This will be reset on transport node restart. |

</details>

<details>
<summary><b>Tier-0 and Tier-1 gateway, routing</b> — 221 fields, 38 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `per_node_statistics[].rx.dad_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `per_node_statistics[].rx.destination_unsupported_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `per_node_statistics[].rx.dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `per_node_statistics[].rx.firewall_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `per_node_statistics[].rx.frag_needed_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `per_node_statistics[].rx.ipsec_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `per_node_statistics[].rx.ipsec_no_sa_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `per_node_statistics[].rx.ipsec_no_vti_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `per_node_statistics[].rx.ipsec_pol_block_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `per_node_statistics[].rx.ipsec_pol_err_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `per_node_statistics[].rx.ipv6_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `per_node_statistics[].rx.kni_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `per_node_statistics[].rx.l4port_unsupported_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `per_node_statistics[].rx.malformed_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `per_node_statistics[].rx.no_arp_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `per_node_statistics[].rx.no_linked_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `per_node_statistics[].rx.no_mem_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `per_node_statistics[].rx.no_receiver_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `per_node_statistics[].rx.no_route_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `per_node_statistics[].rx.non_ip_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `per_node_statistics[].rx.policy_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `per_node_statistics[].rx.proto_unsupported_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `per_node_statistics[].rx.redirect_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `per_node_statistics[].rx.rpf_check_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `per_node_statistics[].rx.service_insert_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `per_node_statistics[].rx.ttl_exceeded_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `per_node_statistics[].tx.dad_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `per_node_statistics[].tx.destination_unsupported_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `per_node_statistics[].tx.dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `per_node_statistics[].tx.firewall_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `per_node_statistics[].tx.frag_needed_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `per_node_statistics[].tx.ipsec_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `per_node_statistics[].tx.ipsec_no_sa_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `per_node_statistics[].tx.ipsec_no_vti_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `per_node_statistics[].tx.ipsec_pol_block_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `per_node_statistics[].tx.ipsec_pol_err_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `per_node_statistics[].tx.ipv6_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `per_node_statistics[].tx.kni_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `per_node_statistics[].tx.l4port_unsupported_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `per_node_statistics[].tx.malformed_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `per_node_statistics[].tx.no_arp_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `per_node_statistics[].tx.no_linked_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `per_node_statistics[].tx.no_mem_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `per_node_statistics[].tx.no_receiver_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `per_node_statistics[].tx.no_route_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `per_node_statistics[].tx.non_ip_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `per_node_statistics[].tx.policy_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `per_node_statistics[].tx.proto_unsupported_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `per_node_statistics[].tx.redirect_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `per_node_statistics[].tx.rpf_check_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `per_node_statistics[].tx.service_insert_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `per_node_statistics[].tx.ttl_exceeded_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `rx.dad_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `rx.destination_unsupported_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `rx.dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `rx.firewall_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `rx.frag_needed_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `rx.ipsec_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `rx.ipsec_no_sa_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `rx.ipsec_no_vti_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `rx.ipsec_pol_block_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `rx.ipsec_pol_err_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `rx.ipv6_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `rx.kni_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `rx.l4port_unsupported_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `rx.malformed_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `rx.no_arp_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `rx.no_linked_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `rx.no_mem_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `rx.no_receiver_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `rx.no_route_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `rx.non_ip_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `rx.policy_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `rx.proto_unsupported_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `rx.redirect_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `rx.rpf_check_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `rx.service_insert_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `rx.ttl_exceeded_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `tx.dad_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `tx.destination_unsupported_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `tx.dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `tx.firewall_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `tx.frag_needed_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `tx.ipsec_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `tx.ipsec_no_sa_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `tx.ipsec_no_vti_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `tx.ipsec_pol_block_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `tx.ipsec_pol_err_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `tx.ipv6_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `tx.kni_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `tx.l4port_unsupported_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `tx.malformed_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `tx.no_arp_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `tx.no_linked_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `tx.no_mem_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `tx.no_receiver_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `tx.no_route_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `tx.non_ip_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `tx.policy_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `tx.proto_unsupported_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `tx.redirect_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `tx.rpf_check_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `tx.service_insert_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `tx.ttl_exceeded_dropped_packets` | integer | 11 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `members[].per_node_statistics[].rx.dad_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `members[].per_node_statistics[].rx.destination_unsupported_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `members[].per_node_statistics[].rx.dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `members[].per_node_statistics[].rx.firewall_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `members[].per_node_statistics[].rx.frag_needed_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `members[].per_node_statistics[].rx.ipsec_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `members[].per_node_statistics[].rx.ipsec_no_sa_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `members[].per_node_statistics[].rx.ipsec_no_vti_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `members[].per_node_statistics[].rx.ipsec_pol_block_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `members[].per_node_statistics[].rx.ipsec_pol_err_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `members[].per_node_statistics[].rx.ipv6_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `members[].per_node_statistics[].rx.kni_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `members[].per_node_statistics[].rx.l4port_unsupported_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `members[].per_node_statistics[].rx.malformed_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `members[].per_node_statistics[].rx.no_arp_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `members[].per_node_statistics[].rx.no_linked_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `members[].per_node_statistics[].rx.no_mem_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `members[].per_node_statistics[].rx.no_receiver_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `members[].per_node_statistics[].rx.no_route_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `members[].per_node_statistics[].rx.non_ip_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `members[].per_node_statistics[].rx.policy_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `members[].per_node_statistics[].rx.proto_unsupported_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `members[].per_node_statistics[].rx.redirect_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `members[].per_node_statistics[].rx.rpf_check_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `members[].per_node_statistics[].rx.service_insert_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `members[].per_node_statistics[].rx.ttl_exceeded_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `members[].per_node_statistics[].tx.dad_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `members[].per_node_statistics[].tx.destination_unsupported_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `members[].per_node_statistics[].tx.dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `members[].per_node_statistics[].tx.firewall_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `members[].per_node_statistics[].tx.frag_needed_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `members[].per_node_statistics[].tx.ipsec_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `members[].per_node_statistics[].tx.ipsec_no_sa_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `members[].per_node_statistics[].tx.ipsec_no_vti_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `members[].per_node_statistics[].tx.ipsec_pol_block_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `members[].per_node_statistics[].tx.ipsec_pol_err_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `members[].per_node_statistics[].tx.ipv6_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `members[].per_node_statistics[].tx.kni_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `members[].per_node_statistics[].tx.l4port_unsupported_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `members[].per_node_statistics[].tx.malformed_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `members[].per_node_statistics[].tx.no_arp_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `members[].per_node_statistics[].tx.no_linked_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `members[].per_node_statistics[].tx.no_mem_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `members[].per_node_statistics[].tx.no_receiver_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `members[].per_node_statistics[].tx.no_route_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `members[].per_node_statistics[].tx.non_ip_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `members[].per_node_statistics[].tx.policy_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `members[].per_node_statistics[].tx.proto_unsupported_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `members[].per_node_statistics[].tx.redirect_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `members[].per_node_statistics[].tx.rpf_check_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `members[].per_node_statistics[].tx.service_insert_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `members[].per_node_statistics[].tx.ttl_exceeded_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `summary.rx.dad_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `summary.rx.destination_unsupported_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `summary.rx.dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `summary.rx.firewall_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `summary.rx.frag_needed_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `summary.rx.ipsec_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `summary.rx.ipsec_no_sa_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `summary.rx.ipsec_no_vti_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `summary.rx.ipsec_pol_block_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `summary.rx.ipsec_pol_err_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `summary.rx.ipv6_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `summary.rx.kni_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `summary.rx.l4port_unsupported_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `summary.rx.malformed_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `summary.rx.no_arp_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `summary.rx.no_linked_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `summary.rx.no_mem_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `summary.rx.no_receiver_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `summary.rx.no_route_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `summary.rx.non_ip_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `summary.rx.policy_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `summary.rx.proto_unsupported_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `summary.rx.redirect_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `summary.rx.rpf_check_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `summary.rx.service_insert_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `summary.rx.ttl_exceeded_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `summary.tx.dad_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because source IP is not assigned to the logical port. For IPv6 address, it could be due to DAD (Duplic… |
| `summary.tx.destination_unsupported_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the destination address in the packet - broadcast, multicast, loopback or reserved address - is… |
| `summary.tx.dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot or ed… |
| `summary.tx.firewall_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to firewall rules or firewall state mismatch (For example, the expected sequence number in TCP wind… |
| `summary.tx.frag_needed_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because they could not be fragmented when their size was larger than the port MTU due to DF bit set in… |
| `summary.tx.ipsec_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `summary.tx.ipsec_no_sa_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to missing security association. The counts are from the time the logical router port was cre… |
| `summary.tx.ipsec_no_vti_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped  due to missing Virtual tunnel interface (VTI) in the security association. The counts are from t… |
| `summary.tx.ipsec_pol_block_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to a discard policy configured for the traffic. The counts are from the time the logical rout… |
| `summary.tx.ipsec_pol_err_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPSec packets dropped due to policy lookup failure for the packets in the security policy database. The counts are from… |
| `summary.tx.ipv6_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of IPv6 packets dropped on the port since the time the logical router port was created. This will be reset on edge reboot… |
| `summary.tx.kni_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets that the DPDK kernel NIC interface failed to send to the linux kernel. For example BGP packets, Load balancer e… |
| `summary.tx.l4port_unsupported_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  for having an unknown/unsupported L4 port (TCP or UDP) and destination IP which is owned by the logica… |
| `summary.tx.malformed_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of malformed packets dropped on the port due to IP checksum error by IP checksum verification or the physical NIC (vmxnet3… |
| `summary.tx.no_arp_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to incomplete ARP resolution of the next-hop. The counts are from the time the logical router port… |
| `summary.tx.no_linked_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the port did not have a linked peer port. For example, the logical router port is not connected… |
| `summary.tx.no_mem_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to insufficient memory. One such example is the mBuf pool memory. The counts are from the time the… |
| `summary.tx.no_receiver_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to absence of the receiver. This could happen when the protocol is not supported by the logical rou… |
| `summary.tx.no_route_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because no route exists for the IP destination of the packets. The counts are from the time the logical… |
| `summary.tx.non_ip_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of non-IP packets dropped  because only IP packets are allowed on the port. For example spanning tree BPDU packets. The co… |
| `summary.tx.policy_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of packets dropped due to connectivity policy. |
| `summary.tx.proto_unsupported_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped because the known protocols such  as ARP, ICMP, DHCP cannot be decoded/fully supported. Also, when the… |
| `summary.tx.redirect_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to redirection of packet to Kernel NIC Interface(KNI) failed. This could be due to either the redir… |
| `summary.tx.rpf_check_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped due to RPF check failure. It is applicable to both unicast and multicast. The counts are from the time… |
| `summary.tx.service_insert_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of service insertion packets dropped. |
| `summary.tx.ttl_exceeded_dropped_packets` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped  due to exceeded TTL. The counts are from the time the logical router port was created and will be rese… |
| `graceful_restart_config.timer.stale_route_timer` | integer | 3 | – | Gauge: instantaneous value | Maximum time (in seconds) before stale routes are removed from the RIB (Routing Information Base) when BGP restarts. |
| `results[].connection_drop_count` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of connection drop |
| `results[].maximum_hop_limit` | integer | 3 | – | Gauge: instantaneous value | Maximum number of hops allowed to reach BGP neighbor. |
| `instance_runtime_statistics[].interface_statistics[].dropped_by_security_packets.bpdu_filter_dropped` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of packets dropped by "BPDU filter". |
| `instance_runtime_statistics[].interface_statistics[].dropped_by_security_packets.dhcp_client_dropped_ipv4` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of IPv4 packets dropped by "DHCP client block". |
| `instance_runtime_statistics[].interface_statistics[].dropped_by_security_packets.dhcp_client_dropped_ipv6` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of IPv6 packets dropped by "DHCP client block". |
| `instance_runtime_statistics[].interface_statistics[].dropped_by_security_packets.dhcp_server_dropped_ipv4` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of IPv4 packets dropped by "DHCP server block". |
| `instance_runtime_statistics[].interface_statistics[].dropped_by_security_packets.dhcp_server_dropped_ipv6` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of IPv6 packets dropped by "DHCP server block". |
| `instance_runtime_statistics[].interface_statistics[].mac_learning.mac_not_learned_packets_dropped` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of packets with unknown source MAC address that are dropped without learning the source MAC address. Applicable only when the MA… |
| `instance_runtime_statistics[].interface_statistics[].rx_bytes.dropped` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |
| `instance_runtime_statistics[].interface_statistics[].rx_packets.dropped` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |
| `instance_runtime_statistics[].interface_statistics[].tx_bytes.dropped` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |
| `instance_runtime_statistics[].interface_statistics[].tx_packets.dropped` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The dropped packets or bytes |

</details>

<details>
<summary><b>Transport node (ESXi host or Edge)</b> — 189 fields, 11 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `rx_drop_no_match` | integer | 4 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the edge transport node interface since the uptime due to one of the below reasons.  - MAC lookup fa… |
| `rx_errors` | integer | 4 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of erroneous incoming packets received on the interface since the uptime. This will be reset on transport node restart. |
| `rx_misses` | integer | 4 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The Total number of incoming packets dropped on the edge transport node interface since the uptime.For DPDK interface this could be due to… |
| `rx_nombufs` | integer | 4 | – | Gauge: instantaneous value | The total number of incoming packets dropped on the edge transport node interface since the uptime due to Rx mBuf allocation failure. This… |
| `tx_drops` | integer | 4 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of outgoing packets dropped on the DPDK interface of the edge transport node due to Tx buffer overflow since the uptime. T… |
| `tx_errors` | integer | 4 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of erroneous packets failed to be transmitted since the uptime. This will be reset on transport node restart. |
| `results[].evpn_tunnel_status.bfd_diagnostic.echo_function_failed_count` | integer | 3 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of tunnels with echo function failed diagnostic message |
| `results[].tunnel_status.bfd_diagnostic.echo_function_failed_count` | integer | 3 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of tunnels with echo function failed diagnostic message |
| `evpn_tunnel_status.bfd_diagnostic.echo_function_failed_count` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of tunnels with echo function failed diagnostic message |
| `fast_path_sys_stats.host_enhanced_fastpath.insertion_errors` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of flow insertion failures. |
| `fast_path_sys_stats.host_enhanced_fastpath.miss` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packets that are processed by slowpath because of a flow miss. This has no overlap with the slowpath counters. |
| `fast_path_sys_stats.host_standard_fastpath.insertion_errors` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of flow insertion failures. |
| `fast_path_sys_stats.host_standard_fastpath.miss` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packets that are processed by slowpath because of a flow miss. This has no overlap with the slowpath counters. |
| `platform_packet_stats.host_uplink.rx_missed` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | RX missed reported by the driver. |
| `queues[].rx_errors` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of erroneous incoming packets received in the queue. The counts are from the time the edge dataplane is UP and will be res… |
| `queues[].tx_drops` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of outgoing packets dropped due to buffer overflow. The counts are from the time the edge dataplane is UP and will be rese… |
| `rx_dropped` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets dropped since the uptime |
| `tunnel_status.bfd_diagnostic.echo_function_failed_count` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of tunnels with echo function failed diagnostic message |
| `tx_carrier` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets for carrier losses detected on transmit. Available only for Host Transport Node. |
| `tx_dropped` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets dropped on transmit since the uptime |
| `packet_stats.datapath_l3.arp_hold_pkt_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The drops of packet(IPv4) pending on ARP resolution. |
| `packet_stats.datapath_l3.drop_route_ipv4_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet(IPv4) matching drop routes. |
| `packet_stats.datapath_l3.drop_route_ipv6_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet(IPv6) matching drop routes. |
| `packet_stats.datapath_l3.dtgw_ext_vlan_uplink_arp_fail` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | dtgw ext vlan uplink arp fail |
| `packet_stats.datapath_l3.no_route_ipv4_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | No IPv4 routes. |
| `packet_stats.datapath_l3.no_route_ipv6_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | No IPv6 routes. |
| `packet_stats.datapath_l3.ns_hold_pkt_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The drops of packet(IPv6) pending on neighbor resolution. |
| `packet_stats.datapath_l3.pkt_attr_error_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packets which failed attribute operation. |
| `packet_stats.datapath_l3.rpf_ipv4_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Reverse path forwarding drops of packet(IPv4). |
| `packet_stats.datapath_l3.rpf_ipv6_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Reverse path forwarding drops of packet(IPv6). |
| `packet_stats.datapath_l3.rx_pkt_parsing_error_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packets failed to be parsed. |
| `packet_stats.datapath_l3.ttl_ipv4_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet(IPv4) drops due to low TTL. |
| `packet_stats.datapath_l3.ttl_ipv6_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet(IPv6) drops due to low TTL. |
| `packet_stats.datapath_l3.tx_dispatch_queue_too_long_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packets being tail dropped in the txDispatchQueue. |
| `packet_stats.datapath_packet_drops.broadcast_rate_limiting_packet_drops` | integer | 1 | ✓ | Gauge: instantaneous value | Drops due to broadcast rate limiting. |
| `packet_stats.datapath_packet_drops.fastpath_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops by the Fastpath. |
| `packet_stats.datapath_packet_drops.firewall_flood_limit_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Firewall flood limit drops. |
| `packet_stats.datapath_packet_drops.firewall_internal_error_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to Firewall detected internal error. |
| `packet_stats.datapath_packet_drops.firewall_malformed_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drop due to Firewall detected malformed packet. |
| `packet_stats.datapath_packet_drops.firewall_packet_rejects` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to Firewall packet rejects. |
| `packet_stats.datapath_packet_drops.firewall_rule_received_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Firewall rule drops at RX. |
| `packet_stats.datapath_packet_drops.firewall_rule_transmitted_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Firewall rule drops at TX. |
| `packet_stats.datapath_packet_drops.firewall_scrx_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Firewall scrx packet drops. |
| `packet_stats.datapath_packet_drops.firewall_state_check_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Firewall state check drops. |
| `packet_stats.datapath_packet_drops.firewall_state_table_full_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to Firewall state table full. |
| `packet_stats.datapath_packet_drops.firewall_total_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Firewall total packet drops. |
| `packet_stats.datapath_packet_drops.hostswitch_network_mismatch_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | RX Drops at vswitch due to network mismatch. |
| `packet_stats.datapath_packet_drops.hostswitch_received_forged_mac_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | RX drops at vswtich due to forged mac. |
| `packet_stats.datapath_packet_drops.l3_hop_limit_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | L3 Drops due to hop limit (TTL). |
| `packet_stats.datapath_packet_drops.l3_neighbor_unreachable_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | L3 Drops due to unreachable neighbor. |
| `packet_stats.datapath_packet_drops.l3_no_route_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | L3 Drops due to no route. |
| `packet_stats.datapath_packet_drops.l3_reverse_path_forwarding_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | L3 drops due to reverse path forwarding. |
| `packet_stats.datapath_packet_drops.overlay_received_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Overlay RX drops. |
| `packet_stats.datapath_packet_drops.overlay_transmitted_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Overlay TX drops. |
| `packet_stats.datapath_packet_drops.overlay_uplink_received_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Overlay uplink RX drops. |
| `packet_stats.datapath_packet_drops.overlay_uplink_transmitted_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Overlay uplink TX drops. |
| `packet_stats.datapath_packet_drops.packet_parsing_error_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to parsing errors. |
| `packet_stats.datapath_packet_drops.spoof_guard_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to spoofguard. |
| `packet_stats.datapath_packet_drops.workload_bpdu_filter_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to BPDU filtering. |
| `packet_stats.datapath_packet_drops.workload_dhcp_not_allowed_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to workload DHCP not allowed. |
| `packet_stats.datapath_packet_drops.workload_ipv6_ra_guard_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to workload ipv6 router advertisement guard. |
| `packet_stats.datapath_system_error_packet_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet dropeed due to datapth system error drops. |
| `packet_stats.datapath_total_packet_drops_pps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | Datapath total packet drop rate. |
| `packet_stats.distributed_firewall.alg_handler_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | alg handler error. |
| `packet_stats.distributed_firewall.bad_offset_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | bad-offset. |
| `packet_stats.distributed_firewall.bad_timestamp_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | bad-timestamp. |
| `packet_stats.distributed_firewall.congestion_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | congestion. |
| `packet_stats.distributed_firewall.fragment_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | fragment. |
| `packet_stats.distributed_firewall.handshake_error_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | 3wh error. |
| `packet_stats.distributed_firewall.icmp_err_pkt_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | icmp errpkt drop. |
| `packet_stats.distributed_firewall.icmp_error_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | icmp error. |
| `packet_stats.distributed_firewall.icmp_flood_overlimit_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | ICMP flood overlimit. |
| `packet_stats.distributed_firewall.ignored_offloaded_fpdrops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Ignored offloaded FP. |
| `packet_stats.distributed_firewall.ignored_offloaded_spdrops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Ignored offloaded SP. |
| `packet_stats.distributed_firewall.ip_option_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | ip-option. |
| `packet_stats.distributed_firewall.l7_alert_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | L7 alert. |
| `packet_stats.distributed_firewall.l7_attr_error_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | L7 attr error. |
| `packet_stats.distributed_firewall.lb_reject_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | LB Reject. |
| `packet_stats.distributed_firewall.match_drop_rule_rx_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Rx pkts dropped by hitting drop/reject rule. |
| `packet_stats.distributed_firewall.match_drop_rule_tx_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Tx pkts dropped by hitting drop/reject rule. |
| `packet_stats.distributed_firewall.memory_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | memory. |
| `packet_stats.distributed_firewall.normalize_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | normalize. |
| `packet_stats.distributed_firewall.other_flood_overlimit_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | OTHER flood overlimit. |
| `packet_stats.distributed_firewall.pkts_frag_queued_v4_misc` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | pkts-frag-queued-v4. |
| `packet_stats.distributed_firewall.pkts_frag_queued_v6_misc` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | pkts-frag-queued-v6. |
| `packet_stats.distributed_firewall.proto_cksum_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | proto-cksum. |
| `packet_stats.distributed_firewall.rx_ipv4_drop_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv4 drop packets. |
| `packet_stats.distributed_firewall.rx_ipv4_reject_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv4 reject packets. |
| `packet_stats.distributed_firewall.rx_ipv6_drop_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv6 drop packets. |
| `packet_stats.distributed_firewall.rx_ipv6_reject_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received IPv6 reject packets. |
| `packet_stats.distributed_firewall.rx_l2_drop_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Received layer 2 drop packets. |
| `packet_stats.distributed_firewall.seqno_bad_ack_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno bad ack. |
| `packet_stats.distributed_firewall.seqno_gt_max_ack_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno gt maxack. |
| `packet_stats.distributed_firewall.seqno_lt_minack_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno lt minack. |
| `packet_stats.distributed_firewall.seqno_old_ack_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno old ack. |
| `packet_stats.distributed_firewall.seqno_old_retrans_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno old retrans. |
| `packet_stats.distributed_firewall.seqno_outside_window_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | seqno outside window. |
| `packet_stats.distributed_firewall.short_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | short. |
| `packet_stats.distributed_firewall.spoof_guard_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | spoofguard. |
| `packet_stats.distributed_firewall.state_insert_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | state-insert. |
| `packet_stats.distributed_firewall.state_limit_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | state-limit. |
| `packet_stats.distributed_firewall.state_mismatch_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | state-mismatch. |
| `packet_stats.distributed_firewall.strict_no_syn_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | strict no syn. |
| `packet_stats.distributed_firewall.syn_expected_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | SYN Expected. |
| `packet_stats.distributed_firewall.syn_proxy_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | synproxy. |
| `packet_stats.distributed_firewall.tcp_flood_overlimit_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | TCP flood overlimit. |
| `packet_stats.distributed_firewall.tx_ipv4_drop_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv4 drop packets. |
| `packet_stats.distributed_firewall.tx_ipv4_reject_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv4 reject packets. |
| `packet_stats.distributed_firewall.tx_ipv6_drop_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv6 drop packets. |
| `packet_stats.distributed_firewall.tx_ipv6_reject_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent IPv6 reject packets. |
| `packet_stats.distributed_firewall.tx_l2_drop_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Sent layer 2 drop packets. |
| `packet_stats.distributed_firewall.udp_flood_overlimit_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | UDP flood overlimit. |
| `packet_stats.fastpath.rx_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx packet drops of ENS Fastpath / Not applicable for FC Module. |
| `packet_stats.fastpath.rx_drops_sp` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx pkts drops of slowpath / Not applicable for FC Module. |
| `packet_stats.fastpath.rx_drops_uplink` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of rx packet drops of ENS Uplink / Not applicable for FC Module. |
| `packet_stats.fastpath.tx_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx packet drops of ENS Fastpath / Count of packets dropped at FC lookup of vnic. |
| `packet_stats.fastpath.tx_drops_sp` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx pkts drops by slowpath / Not applicable for FC Module. |
| `packet_stats.fastpath.tx_drops_uplink` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of tx packet drops of ENS Uplink / Count of packets dropped at FC lookup of Uplink. |
| `packet_stats.overlay_datapath_l2.arp_proxy_req_fail_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of ARPs failed to send on uplinks for CCP unaware bindings. |
| `packet_stats.overlay_datapath_l2.arp_proxy_resp_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of ARP response failed for each ARP suppressed packets. |
| `packet_stats.overlay_datapath_l2.leaf_rx_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total drops at VDL2LeafInput IOChain of a switchport. |
| `packet_stats.overlay_datapath_l2.leaf_rx_ref_port_not_found_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | VDL2LeafInput drops as trunk port is not in logical switch. |
| `packet_stats.overlay_datapath_l2.leaf_rx_system_err_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | VDL2LeafInput drops on an LS due to system errors. |
| `packet_stats.overlay_datapath_l2.leaf_tx_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total drops at VDL2LeafOutput IOChain of a switchport. |
| `packet_stats.overlay_datapath_l2.mac_tbl_lookup_flood` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of unicast packets flooded onto remote VTEPs due to MAC table full. |
| `packet_stats.overlay_datapath_l2.mac_tbl_lookup_full` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of VM MAC query to CCP failure due to MAC table full. |
| `packet_stats.overlay_datapath_l2.mac_tbl_update_full` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of packet's SMAC learning failed at uplink due to MAC table full. |
| `packet_stats.overlay_datapath_l2.mcast_proxy_rx_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of BUM replicated packets dropped at MTEP TN at uplink input IOChain. |
| `packet_stats.overlay_datapath_l2.mcast_proxy_tx_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of BUM packets dropped at uplink output IOChain. |
| `packet_stats.overlay_datapath_l2.nd_proxy_req_fail_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of ND packets failed to send on uplinks for CCP unaware bindings. |
| `packet_stats.overlay_datapath_l2.nd_proxy_resp_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of ND response failed for each ND suppressed packets. |
| `packet_stats.overlay_datapath_l2.nested_tn_mcast_proxy_diff_vlan_tx_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of BUM replicated packet drops destined to nested TN. |
| `packet_stats.overlay_datapath_l2.nested_tn_mcast_proxy_same_vlan_tx_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of BUM replicated packet drops destined to nested TN. |
| `packet_stats.overlay_datapath_l2.uplink_rx_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets from underlay that are dropped at uplink input IOChain. |
| `packet_stats.overlay_datapath_l2.uplink_rx_guest_vlan_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drop at uplink input IOChain due to failure to remove guest VLAN tag. |
| `packet_stats.overlay_datapath_l2.uplink_rx_invalid_encap_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets dropped at uplink input IOChain due to incorrect Encap. |
| `packet_stats.overlay_datapath_l2.uplink_rx_mcast_invalid_druplink_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of IP multicast packets dropped at unexpected DR uplink. |
| `packet_stats.overlay_datapath_l2.uplink_rx_system_err_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drop at uplink input IOChain due to system errors. |
| `packet_stats.overlay_datapath_l2.uplink_rx_wrong_dest_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drop at uplink port input IOChain due to incorrect destination VTEP IP. |
| `packet_stats.overlay_datapath_l2.uplink_tx_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total DVS sent packet drops at uplink output IOChain. |
| `packet_stats.overlay_datapath_l2.uplink_tx_invalid_frame_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of invalid packets dropped at uplink IOChain. |
| `packet_stats.overlay_datapath_l2.uplink_tx_invalid_state_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packet drops at uplink IOChain due to incorrect uplink VLAN configuration. |
| `packet_stats.overlay_datapath_l2.uplink_tx_nested_tn_repl_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets to nested TN dropped at uplink output IOChain. |
| `packet_stats.overlay_datapath_l2.uplink_tx_teaming_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of packets dropped at uplink IOChain due to uplink teaming failure. |
| `packet_stats.overlay_datapath_l2.uplink_tx_ucast_flood` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Count of unknown unicast packets at uplink output IOChain. |
| `packet_stats.packet_processing_efficiency_watch.fastpath_flow_miss_pps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | Rate at which packets are processed by slowpath because of a flow miss. This has no overlap with slowpath packets.. |
| `packet_stats.packet_processing_efficiency_watch.l3_dtgw_ext_vlan_uplink_neighbor_resolution_fail_pps` | number | 1 | – | NSX-computed per-second rate (no delta needed) | l3 dtgw ext vlan uplink neighbor resolution fail pps |
| `packet_stats.packet_processing_efficiency_watch.overlay_unsuccessful_control_plane_assisted_neighbor_resolution_rxpps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | Unsuccessful CCP assisted overlay neighbor resolution on RX. |
| `packet_stats.packet_processing_efficiency_watch.overlay_unsuccessful_mac_learning_due_to_table_full_rxpps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | Unsuccessful mac learning on RX side due to table full. |
| `packet_stats.packet_processing_efficiency_watch.overlay_unsuccessful_mac_learning_due_to_unknown_tunnel_endpoint_rxpps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | Unsuccessful mac learning on RX side due to unknown tunnel endpoint. |
| `packet_stats.switch_security.bpdu_filter_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packets dropped by BPDU Filter. |
| `packet_stats.switch_security.ddhcp_resp_pkt_alloc_ipv4_failures` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | ddhcp resp pkt alloc ipv4 failures. |
| `packet_stats.switch_security.dhcp_client_block_ipv4_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | IPv4 packets dropped by Client Block. |
| `packet_stats.switch_security.dhcp_client_block_ipv6_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | IPv6 packets dropped by Client Block. |
| `packet_stats.switch_security.dhcp_client_validate_ipv4_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | IPv4 packets dropped by Client Validate. |
| `packet_stats.switch_security.dhcp_server_block_ipv4_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | IPv4 packets dropped by Server Block. |
| `packet_stats.switch_security.dhcp_server_block_ipv6_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | IPv6 packets dropped by Server Block. |
| `packet_stats.switch_security.nd_parse_errors` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | IPv6 ND Parse Errors. |
| `packet_stats.switch_security.ra_guard_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Packets dropped by RA Guard. |
| `packet_stats.switch_security.rx_ddhcp_forged_mac_ipv4_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | rx ddhcp forged mac ipv4 drops. |
| `packet_stats.switch_security.rx_ddhcp_no_client_ip_ipv4_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | rx ddhcp no client ip ipv4 drops. |
| `packet_stats.switch_security.rx_ddhcp_parse_ipv4_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | rx ddhcp parse ipv4 drops. |
| `packet_stats.switch_security.rx_ddhcp_relay_pkt_ipv4_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | rx ddhcp relay pkt ipv4 drops. |
| `packet_stats.switch_security.rx_rate_limit_bcast_drops` | integer | 1 | ✓ | Gauge: instantaneous value | Rx Broadcast packets dropped by Rate Limit. |
| `packet_stats.switch_security.rx_rate_limit_mcast_drops` | integer | 1 | ✓ | Gauge: instantaneous value | Rx Multicast packets dropped by Rate Limit. |
| `packet_stats.switch_security.spoof_guard_arp_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | ARP packets dropped by Spoof Guard. |
| `packet_stats.switch_security.spoof_guard_ipv4_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | IPv4 packets dropped by Spoof Guard. |
| `packet_stats.switch_security.spoof_guard_ipv6_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | IPv6 packets dropped by Spoof Guard. |
| `packet_stats.switch_security.spoof_guard_nd_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | ND packets dropped by Spoof Guard. |
| `packet_stats.switch_security.spoof_guard_non_ip_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Non-IP packets dropped by Spoof Guard. |
| `packet_stats.switch_security.tx_ddhcp_arp_reply_failures` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Tx ddhcp arp reply failures. |
| `packet_stats.switch_security.tx_rate_limit_bcast_drops` | integer | 1 | ✓ | Gauge: instantaneous value | Tx Broadcast packets dropped by Rate Limit. |
| `packet_stats.switch_security.tx_rate_limit_mcast_drops` | integer | 1 | ✓ | Gauge: instantaneous value | Tx Multicast packets dropped by Rate Limit. |
| `packet_stats.unicast_packet_flooding.hostswitch_unknown_l2_unicast_from_uplink_rxpps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | Unknown L2 unicast packets receveied by hostswitch from the uplink. |
| `packet_stats.unicast_packet_flooding.hostswitch_unknown_l2_unicast_to_uplink_txpps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | Unknown L2 unicast packets sent by hostswtich to the uplink. |
| `packet_stats.unicast_packet_flooding.overlay_flooded_l2_unicast_to_uplink_txpps` | number | 1 | ✓ | NSX-computed per-second rate (no delta needed) | L2 overlay unicast TX packets flooded to the uplink. |
| `packet_stats.virtual_switch.forged_transmit_rx_drops` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to forged transmits disabled. |
| `packet_stats.virtual_switch.unknown_unicast_rx_uplink_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Unknown unicast flooded packets received from uplink. |
| `packet_stats.virtual_switch.unknown_unicast_tx_uplink_pkts` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Unknown unicast flooded packets sent on the uplink. |
| `packet_stats.virtual_switch.vlan_tag_mismatch_rx` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to VLAN tag mismatch of packets received by vswitch. |
| `packet_stats.virtual_switch.vlan_tag_mismatch_rx_mcast` | integer | 1 | ✓ | Gauge: instantaneous value | Drops due to VLAN tag mismatch of packets received by vswitch. |
| `packet_stats.virtual_switch.vlan_tag_mismatch_tx` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to VLAN tag mismatch of packets forwarded by vswitch. |
| `packet_stats.virtual_switch.vlan_tag_mismatch_tx_mcast` | integer | 1 | ✓ | Gauge: instantaneous value | Drops due to VLAN tag mismatch of packets forwarded by vswitch. |
| `packet_stats.virtual_switch.vni_tag_mismatch_tx` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Drops due to VNI tag mismatch of packets forwarded by vswitch. |
| `packet_stats.virtual_switch.vni_tag_mismatch_tx_mcast` | integer | 1 | ✓ | Gauge: instantaneous value | Drops due to VNI tag mismatch of packets forwarded by vswitch. |
| `scrx_stats.host_scrx.datapath_rx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | datapath_rx_drops |
| `scrx_stats.host_scrx.datapath_tx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | datapath_tx_drops |
| `scrx_stats.host_scrx.service_datapath_drop_pkts` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | service_datapath_drop_pkts |
| `scrx_stats.host_scrx.service_datapath_pkt_latency` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | service_datapath_pkt_latency |

</details>

<details>
<summary><b>Transit gateway (VPC)</b> — 49 fields, 3 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `rx.destination_unsupported_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to destination_unsupported |
| `rx.dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of error packets |
| `rx.firewall_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by firewall |
| `rx.ipsec_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by ipsec |
| `rx.ipsec_no_sa_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by ipsec no sa |
| `rx.ipsec_no_vti_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by ipsec no vti |
| `rx.ipv6_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped ipv6 packets |
| `rx.kni_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped kni packets |
| `rx.l4port_unsupported_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped l4port_unsupported packets |
| `rx.malformed_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped malformed packets |
| `rx.no_receiver_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped no receiver packets |
| `rx.proto_unsupported_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of proto unsupported packets dropped |
| `rx.redirect_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to redirection |
| `rx.rpf_check_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to rpf check |
| `rx.ttl_exceeded_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to exceeding ttl |
| `tx.destination_unsupported_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to destination_unsupported |
| `tx.dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of error packets |
| `tx.firewall_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by firewall |
| `tx.ipsec_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by ipsec |
| `tx.ipsec_no_sa_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by ipsec no sa |
| `tx.ipsec_no_vti_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by ipsec no vti |
| `tx.ipv6_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped ipv6 packets |
| `tx.kni_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped kni packets |
| `tx.l4port_unsupported_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped l4port_unsupported packets |
| `tx.malformed_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped malformed packets |
| `tx.no_receiver_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped no receiver packets |
| `tx.proto_unsupported_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of proto unsupported packets dropped |
| `tx.redirect_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to redirection |
| `tx.rpf_check_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to rpf check |
| `tx.ttl_exceeded_dropped_packets` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to exceeding ttl |
| `external_traffic.rx.destination_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to destination_unsupported |
| `external_traffic.rx.dropped_packets` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of error packets |
| `external_traffic.rx.firewall_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by firewall |
| `external_traffic.rx.ipsec_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by ipsec |
| `external_traffic.rx.ipsec_no_sa_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by ipsec no sa |
| `external_traffic.rx.ipsec_no_vti_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets by ipsec no vti |
| `external_traffic.rx.ipv6_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped ipv6 packets |
| `external_traffic.rx.kni_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped kni packets |
| `external_traffic.rx.l4port_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped l4port_unsupported packets |
| `external_traffic.rx.malformed_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped malformed packets |
| `external_traffic.rx.no_receiver_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped no receiver packets |
| `external_traffic.rx.proto_unsupported_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of proto unsupported packets dropped |
| `external_traffic.rx.redirect_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to redirection |
| `external_traffic.rx.rpf_check_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to rpf check |
| `external_traffic.rx.ttl_exceeded_dropped_packets` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of dropped packets due to exceeding ttl |
| `external_traffic.tx.dropped_packets` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of error packets |
| `internal_traffic.rx.dropped_packets` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of error packets |
| `internal_traffic.tx.dropped_packets` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of error packets |
| `internal_traffic.tx.policy_dropped_packets` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of packets dropped by connectivity policies |

</details>

<details>
<summary><b>Manager appliance process and latency (SHA)</b> — 10 fields, 4 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `latency_data[].packet_received` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Display the received packets. |
| `latency_data[].packet_transmitted` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Display the transmitted packets in Ping |
| `latency_data[].rtt_avg` | number | 2 | – | Gauge: instantaneous value | Display the average Round Trip Time in milliseconds. |
| `latency_data[].rtt_mdev` | number | 2 | – | Gauge: instantaneous value | Display the mean Round Trip Time in milliseconds. |
| `latency_data[].rtt_min` | number | 2 | – | Gauge: instantaneous value | Display the min Round Trip Time in milliseconds. |
| `results[].latency_data[].packet_received` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Display the received packets. |
| `results[].latency_data[].packet_transmitted` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Display the transmitted packets in Ping |
| `results[].latency_data[].rtt_avg` | number | 2 | – | Gauge: instantaneous value | Display the average Round Trip Time in milliseconds. |
| `results[].latency_data[].rtt_mdev` | number | 2 | – | Gauge: instantaneous value | Display the mean Round Trip Time in milliseconds. |
| `results[].latency_data[].rtt_min` | number | 2 | – | Gauge: instantaneous value | Display the min Round Trip Time in milliseconds. |

</details>

<details>
<summary><b>NSX Manager cluster</b> — 9 fields, 2 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `rx_drop_no_match` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the edge transport node interface since the uptime due to one of the below reasons.  - MAC lookup fa… |
| `rx_dropped` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets dropped since the uptime |
| `rx_errors` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of erroneous incoming packets received on the interface since the uptime. This will be reset on transport node restart. |
| `rx_misses` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The Total number of incoming packets dropped on the edge transport node interface since the uptime.For DPDK interface this could be due to… |
| `rx_nombufs` | integer | 2 | – | Gauge: instantaneous value | The total number of incoming packets dropped on the edge transport node interface since the uptime due to Rx mBuf allocation failure. This… |
| `tx_carrier` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets for carrier losses detected on transmit. Available only for Host Transport Node. |
| `tx_dropped` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets dropped on transmit since the uptime |
| `tx_drops` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of outgoing packets dropped on the DPDK interface of the edge transport node due to Tx buffer overflow since the uptime. T… |
| `tx_errors` | integer | 2 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of erroneous packets failed to be transmitted since the uptime. This will be reset on transport node restart. |

</details>

<details>
<summary><b>NSX Manager node</b> — 9 fields, 1 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `rx_drop_no_match` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of packets dropped on the edge transport node interface since the uptime due to one of the below reasons.  - MAC lookup fa… |
| `rx_dropped` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets dropped since the uptime |
| `rx_errors` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of erroneous incoming packets received on the interface since the uptime. This will be reset on transport node restart. |
| `rx_misses` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The Total number of incoming packets dropped on the edge transport node interface since the uptime.For DPDK interface this could be due to… |
| `rx_nombufs` | integer | 1 | – | Gauge: instantaneous value | The total number of incoming packets dropped on the edge transport node interface since the uptime due to Rx mBuf allocation failure. This… |
| `tx_carrier` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets for carrier losses detected on transmit. Available only for Host Transport Node. |
| `tx_dropped` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total packets dropped on transmit since the uptime |
| `tx_drops` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of outgoing packets dropped on the DPDK interface of the edge transport node due to Tx buffer overflow since the uptime. T… |
| `tx_errors` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of erroneous packets failed to be transmitted since the uptime. This will be reset on transport node restart. |

</details>

<details>
<summary><b>Upgrade coordinator</b> — 9 fields, 2 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `ccp_status.pre_upgrade_status.error_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total count of generated Failures in last execution of pre/post upgrade checks |
| `ccp_status.pre_upgrade_status.failure_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total count of generated failures or warnings in last execution of pre/post-upgrade checks |
| `component_status[].pre_upgrade_status.error_count` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total count of generated Failures in last execution of pre/post upgrade checks |
| `component_status[].pre_upgrade_status.failure_count` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total count of generated failures or warnings in last execution of pre/post-upgrade checks |
| `edge_status.pre_upgrade_status.error_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total count of generated Failures in last execution of pre/post upgrade checks |
| `edge_status.pre_upgrade_status.failure_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total count of generated failures or warnings in last execution of pre/post-upgrade checks |
| `host_status.pre_upgrade_status.error_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total count of generated Failures in last execution of pre/post upgrade checks |
| `host_status.pre_upgrade_status.failure_count` | integer | 1 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total count of generated failures or warnings in last execution of pre/post-upgrade checks |
| `results[].failed_count` | integer | 1 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of nodes in the upgrade unit group that failed upgrade |

</details>

<details>
<summary><b>VPN (IPsec, L2VPN)</b> — 5 fields, 5 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `aggregate_traffic_counters.dropped_packets_in` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of incoming packets dropped on inbound security association. |
| `aggregate_traffic_counters.dropped_packets_out` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of outgoing packets dropped on outbound security association. |
| `session_summary.failed_sessions` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The number of failed IPSec VPN sessions. |
| `traffic_summary_per_session[].traffic_counters.dropped_packets_in` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of incoming packets dropped on inbound security association. |
| `traffic_summary_per_session[].traffic_counters.dropped_packets_out` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of outgoing packets dropped on outbound security association. |

</details>

<details>
<summary><b>Firewall policy and rule (DFW, gateway)</b> — 4 fields, 14 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].statistics.l7_reject_count` | integer | 7 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Rejected counters received by the rule. |
| `results[].statistics.l7_reject_with_response_count` | integer | 7 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Rejected with Response counters received by the rule. |
| `results[].statistics.results[].l7_reject_count` | integer | 7 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Rejected counters received by the rule. |
| `results[].statistics.results[].l7_reject_with_response_count` | integer | 7 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Rejected with Response counters received by the rule. |

</details>

<details>
<summary><b>Security services (IDFW, IDS/IPS)</b> — 4 fields, 10 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].statistics.l7_reject_count` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Rejected counters received by the rule. |
| `results[].statistics.l7_reject_with_response_count` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Rejected with Response counters received by the rule. |
| `results[].statistics.results[].l7_reject_count` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Rejected counters received by the rule. |
| `results[].statistics.results[].l7_reject_with_response_count` | integer | 5 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Aggregated number of L7 Profile Rejected with Response counters received by the rule. |

</details>

<details>
<summary><b>Other platform status</b> — 3 fields, 6 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `errors` | integer | 3 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | The total number of DHCP errors |
| `num_full_sync` | integer | 2 | – | Gauge: instantaneous value | number of successful historical full sync initiated either by system or by API request. |
| `results[].agent_info.failed_agent_num` | integer | 1 | – | Gauge: instantaneous value | The number of failed agents |

</details>

<details>
<summary><b>Realization and platform status</b> — 3 fields, 3 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `counters.dropped_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of dropped observations for this round. |
| `logical_counters.dropped_count` | integer | 2 | – | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Total number of dropped observations for this round. |
| `agent_info.failed_agent_num` | integer | 1 | – | Gauge: instantaneous value | The number of failed agents |

</details>

<details>
<summary><b>Transport zone</b> — 2 fields, 3 endpoints</summary>

| Field | Type | Endpoints | Lab | Formula | Description |
|---|---|---:|:-:|---|---|
| `results[].evpn_tunnel_status.bfd_diagnostic.echo_function_failed_count` | integer | 3 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of tunnels with echo function failed diagnostic message |
| `results[].tunnel_status.bfd_diagnostic.echo_function_failed_count` | integer | 3 | ✓ | Cumulative counter: rate = (value_t2 - value_t1) / (t2 - t1) | Number of tunnels with echo function failed diagnostic message |

</details>

<!-- END GENERATED: contention -->
