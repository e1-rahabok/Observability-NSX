# NSX metrics: open questions

Everything I could not settle while writing the metric guides, in one place. Each guide refers to these items by their number, for example "(D9)".

- **D1** means "doubt number 1": an open question, not a decision.
- Each question says what it affects, what I am assuming until it is settled, and how to settle it.
- **Owner** shows who can close it: **Lab** (I can test it on nsxman1 with the existing read-only account), **Decision** (needs your choice), **Vendor** (Broadcom documentation or support).

Guides: [Formulas](NSX-Metrics-Formulas.md) · [Contention](NSX-Contention-Metrics.md) · [Consumption](NSX-Consumption-Metrics.md) · [Capacity](NSX-Capacity-Metrics.md) · [Availability and events](NSX-Availability-Metrics-and-Events.md)

---

## Summary

| ID | Question, in short | Owner | Blocks |
|---|---|---|---|
| [D1](#d1-how-often-do-cached-statistics-update) | How often do cached statistics refresh? | Lab | Polling interval, freshness |
| [D2](#d2-what-do-the-realization-status-values-mean) | What do the realization status values mean? | Vendor | Realization alerts |
| [D3](#d3-what-does-event-sensitivity-do) | What does event `sensitivity` do? | Vendor | Tuning alarms |
| [D4](#d4-does-the-memory-alarm-use-the-same-formula-as-the-field) | Does the memory alarm use the same formula as the field? | Lab | Memory alerting |
| [D5](#d5-how-is-edge-datapath-cpu-calculated) | How is Edge datapath CPU calculated? | Lab (needs an Edge) | Edge CPU |
| [D6](#d6-where-is-the-physical-nic-link-speed) | Where is the physical NIC link speed? | Vendor | NIC utilisation |
| [D7](#d7-fields-returned-but-not-in-the-spec) | 55 lab fields are missing from the spec | None (noted) | Field lists |
| [D8](#d8-what-do-some-internal-counter-names-measure) | What do some internal counter names measure? | Vendor | Flow-cache ratio, drop counters |
| [D9](#d9-host-tunnel-counts-are-zero-while-status-is-up) | Host tunnel counts are zero while status is UP | Lab | Tunnel alerts |
| [D10](#d10-are-the-timestamp-and-uptime-units-right) | Are the timestamp and uptime units right? | Vendor | Uptime and freshness |
| [D11](#d11-what-is-the-age-in-popularity_index) | What is the "age" in `popularity_index`? | Lab | DFW popularity |
| [D12](#d12-where-are-the-requested-alarm-names) | Where are the alarm names "controller out of sync" and "Edge process hang"? | Decision | Availability mapping |
| [D13](#d13-the-crawler-labels-host-statistics-as-property) | The crawler labels host statistics as `property` | Decision | Metric polling |
| [D14](#d14-are-the-category-lists-right) | Are the category lists right? | Decision | All category lists |
| [D15](#d15-what-the-auditor-role-cannot-read) | What the Auditor role cannot read | Decision | Coverage |
| [D16](#d16-are-the-config-and-nonconfig-disk-thresholds-right) | Are the `/config` and `/nonconfig` disk thresholds right? | Vendor or Lab | Manager disk alerts |
| [D17](#d17-is-there-a-metric-for-ip-pool-usage) | Is there a metric for IP pool usage? | Vendor | IP pool alerts |
| [D18](#d18-what-capacity-severity-applies-between-70-and-100) | What capacity severity applies between 70% and 100%? | Lab | Capacity alerts |

---

## D1. How often do cached statistics update?

- **Affects:** polling interval, how old a value can be, how often alarms can be checked. [Formulas §1, §6]
- **Conflict:** the lab README says cached values refresh "about every minute". Broadcom's summary of the NSX documentation says point-in-time values are collected periodically with a default interval of 300 s.
- **Assumption until settled:** poll no faster than once a minute, and treat any value as up to 5 minutes old.
- **To settle:** poll one field every 10 seconds for 15 minutes and count how often it changes.
- **Owner:** Lab.

## D2. What do the realization status values mean?

- **Affects:** realization and publish alerts. [Formulas §4.7]
- **Known:** Broadcom's 4.2 schema lists `publish_status` as `UNAVAILABLE, UNREALIZED, REALIZED, ERROR`. The lab returned `UNINITIALIZED`, which is not on that list. The `ConfigState` enum for `consolidated_status` did not render on the developer page.
- **Assumption until settled:** treat unknown values as "unknown", not as an error.
- **To settle:** read the `ConfigState` enum on the 9.1 developer page, or check objects in each state.
- **Owner:** Vendor.

## D3. What does event sensitivity do?

- **Affects:** how to tune alarms. [Formulas §4.8, Availability §4]
- **Known:** definitions carry `sensitivity` set to 80 for manager CPU and memory events and 100 elsewhere. No definition found.
- **Assumption until settled:** do not rely on it. Read it as NSX returns it.
- **To settle:** NSX 9.1 event-definition documentation.
- **Owner:** Vendor.

## D4. Does the memory alarm use the same formula as the field?

- **Affects:** whether `mem_used ÷ mem_total` predicts the manager memory alarm. [Formulas §4.1]
- **Known:** the high alarm is at 90% and the very high at 95%. The lab node is at 82.4% with no alarm. The field equals `mem_total − mem_available`. Broadcom's KB gives the thresholds, not the formula.
- **Assumption until settled:** the alarm uses this formula. The lab result fits but does not prove it.
- **To settle:** watch the field and the alarm together during a memory event, or test on a lab node.
- **Owner:** Lab.

## D5. How is Edge datapath CPU calculated?

- **Affects:** Edge CPU alerts. [Formulas §4.5, Consumption §2]
- **Known:** the schema gives per-core packet rates over 100 ms, and CPU sampled over 60 s. It gives no percentage formula.
- **Assumption until settled:** use the NSX value as it is, and do not recompute it.
- **To settle:** needs an Edge node in the lab. There is none now.
- **Owner:** Lab, once an Edge exists.

## D6. Where is the physical NIC link speed?

- **Affects:** physical NIC utilisation percentage. [Formulas §4.2, Consumption §2]
- **Known:** pNIC throughput is in Mb/s, but no link speed was in the responses I read.
- **Assumption until settled:** report throughput only, not utilisation.
- **To settle:** search the 9.1 spec for a link-speed field on the transport node or pNIC object.
- **Owner:** Vendor.

## D7. Fields returned but not in the spec

- **Affects:** field lists. Not blocking.
- **Known:** the lab returns 55 fields across 7 endpoints that the spec does not declare. Most are in the transport-zone status lists (`agent_status`, `file_systems`). These are marked † in the lists.
- **Assumption until settled:** the lab output is the truth for these fields.
- **Owner:** none needed.

## D8. What do some internal counter names measure?

- **Affects:** flow-cache hit ratio, the drop counter that has the big totals, and the packet-processing watch group. [Formulas §4.2]
- **Known:** the names `fastpath_flow_hit_pps`, `fastpath_flow_miss_pps`, `packet_processing_efficiency_watch` and `hostswitch_network_mismatch_packet_drops` have no public definition I could find. The closest schema (`FpCounters`) describes different counters.
- **Assumption until settled:** the hit ratio is hit ÷ (hit + miss), based on the names alone.
- **To settle:** Broadcom support for the 9.1 counter dictionary.
- **Owner:** Vendor.

## D9. Host tunnel counts are zero while status is UP

- **Affects:** tunnel and BFD alerts. [Formulas §4.2, §4.9; Consumption §2]
- **Known:** on all three lab hosts, the BFD counts are zero and the tunnel status says UP. Broadcom's KB says DEGRADED usually means a tunnel or BFD peer is down, and the counts can be incomplete.
- **Assumption until settled:** the counts do not show the real tunnel state on these hosts. Do not alert on the counts alone.
- **To settle:** list the BFD sessions on one host with the NSX CLI, using the command in the 9.1 CLI guide.
- **Owner:** Lab.

## D10. Are the timestamp and uptime units right?

- **Affects:** uptime and freshness calculations. [Formulas §2]
- **Known:** timestamps are epoch milliseconds, and this is verified: 1792384339000 is 2026-10-19 04:32 UTC, the crawl date. Uptime is in milliseconds by plausibility, since seconds would mean 37 years. The schema does not state the unit.
- **Assumption until settled:** uptime is milliseconds.
- **To settle:** the schema description for `uptime`.
- **Owner:** Vendor.

## D11. What is the "age" in `popularity_index`?

- **Affects:** DFW popularity ranking. [Formulas §4.4]
- **Known:** the schema says popularity is "sessions count divided by age of the rule". It gives no unit for age.
- **Assumption until settled:** do not compare popularity values across releases or rules created at different times.
- **To settle:** create a test rule in the lab and watch the value over time.
- **Owner:** Lab.

## D12. Where are the requested alarm names?

- **Affects:** the availability mapping for "NSX controller out of sync" and "NSX Edge process hang". [Availability §5]
- **Known:** neither name is an event in the 284 definitions. The closest matches are listed in the availability guide, with a confidence level for each.
- **Assumption until settled:** those matches are the working mapping.
- **To settle:** send the exact alarm text from your NSX UI or ticket history, and I will check it against the catalogue.
- **Owner:** Decision. This needs your input.

## D13. The crawler labels host statistics as `property`

- **Affects:** which endpoints the poller treats as metrics. [Formulas §6]
- **Known:** `kind_of` in `tools/nsx_crawl.py` (lines 55–57) checks only the last path segment. `…/statistics/monitor` and `…/statistics/debug` end in `monitor` and `debug`, so they are labelled `property`. The catalog left them out, and the README's advice to poll metric templates would skip them.
- **Assumption until settled:** these two endpoints are metrics, and the guides treat them that way.
- **To settle:** decide whether I should change the crawler to test for a `/statistics/` segment. I have not changed it.
- **Owner:** Decision. This needs your decision.

## D14. Are the category lists right?

- **Affects:** every list in the contention, consumption, capacity and availability guides.
- **Known:** the categories come from a keyword heuristic. Some fields are misfiled, for example `messages_sent` under availability.
- **Assumption until settled:** use the lists as a starting point, and check a field before you alert on it.
- **To settle:** your review of [`data/nsx-metric-fields.csv`](data/nsx-metric-fields.csv).
- **Owner:** Decision. Review wanted.

## D15. What the Auditor role cannot read

- **Affects:** coverage. Some metrics are not in this review.
- **Known:** the Auditor account gets HTTP 403 on `management-plane-health`, `infra/sites/agents/metrics`, and SHA monitor details.
- **Assumption until settled:** those metrics are out of scope.
- **To settle:** a read-only role that can see them. Say if you want that requested.
- **Owner:** Decision.

## D16. Are the `/config` and `/nonconfig` disk thresholds right?

- **Affects:** manager disk alerts. [Capacity §1.3]
- **Known:** the event definitions give 20% high and 30% very high for `/config` and `/nonconfig`. Other partitions use 80% and 90%. `/repository` uses 98%.
- **Assumption until settled:** do not rely on the 20% and 30% levels. They may be a metadata quirk.
- **To settle:** the event description text on your version, or the NSX UI.
- **Owner:** Vendor or Lab.

## D17. Is there a metric for IP pool usage?

- **Affects:** IP pool alerts. [Capacity §2.4]
- **Known:** neither spec has a pool-usage endpoint. The policy spec has `ip-allocations` lists only. The lab has an open `ip_pool_usage_very_high` alarm.
- **Assumption until settled:** the pool percentage would be allocations ÷ range size. This is my construction, not an NSX formula.
- **To settle:** find a pool-usage field in the 9.1 API. Otherwise, compare the derived figure with the alarm.
- **Owner:** Vendor, then Lab.

## D18. What capacity severity applies between 70% and 100%?

- **Affects:** capacity alert levels. [Capacity §2.2]
- **Known:** the lab shows INFO at 48.8% and WARNING at 100%. Global thresholds are 70% and 100%.
- **Assumption until settled:** no alert level between 70% and 100% has been set.
- **To settle:** a lab test at a few usage levels, or the capacity documentation.
- **Owner:** Lab.
