# Playbook — Memory Saturation

**Applies to:** `MEMORY_RESOURCES_EXHAUSTED`, high memory utilisation, GC overhead events, heap exhaustion, process OOM.

> **Before writing any DQL query in this playbook:** Apply the DQL Query Requirements from SKILL.md Global Rules. Every query must include `| fields` and `| limit`. Never repeat the same query with minor variations.

**Core question this playbook answers:**
> Which process is exhausting memory, is this a memory leak, a workload-driven growth event, or a GC failure — and is this an incident-specific event or a gradual trend that has now crossed a threshold?

---

## Investigation Priority Order

Memory saturation problems trace to one of five mechanisms:
1. A memory leak in a long-running process (heap grows monotonically over hours/days).
2. A workload spike causing transient heap growth beyond allocated limits.
3. GC overhead failure — GC is running but unable to reclaim enough heap, causing application stalls.
4. A deployment or configuration change that increased memory allocation per request.
5. A native/off-heap memory issue (memory-mapped files, direct buffers, native libs).

**Critical for this problem type:** Memory saturation is often a **gradual trend** that crosses a threshold at a moment that may not be the actual root cause event. The incident onset time may be hours after the underlying cause began. Look for the trend start, not just the threshold crossing.

---

## Step MEM-1 — Process and Host Scoping

Identify all affected hosts and process groups from the problem context.

For each affected host, retrieve over the investigation window + the 24 hours before onset:
- Host memory utilisation (overall)
- Per-process memory utilisation (JVM heap if Java/Kotlin/.NET, RSS/VSZ if native)

| Host | Peak memory % | Time of peak (UTC+8) | Top memory-consuming process | Process memory % |
|------|--------------|---------------------|------------------------------|-----------------|
| | | | | |

Extend the query window 24 hours before onset to detect gradual growth trends.

---

## Step MEM-2 — Memory Trend Analysis (Mandatory)

Retrieve host memory utilisation and per-process heap/memory over the **72 hours preceding** the problem onset.

Plot or tabulate at 1-hour intervals:

| Time (UTC+8) | Host memory % | Process heap / memory % | GC overhead % (if available) | Notes |
|--------------|---------------|------------------------|------------------------------|-------|
| Onset − 72h | | | | |
| Onset − 48h | | | | |
| Onset − 24h | | | | |
| Onset − 12h | | | | |
| Onset − 6h | | | | |
| Onset − 1h | | | | |
| Onset | | | | |
| Peak | | | | |

Identify the **trend shape**:
- **Monotonic growth (leak pattern):** Memory grows continuously without recycling. Root cause began well before the alert fired.
- **Sawtooth with incomplete recovery:** GC is running but not fully reclaiming — heap floor is rising. Indicates GC pressure or retention.
- **Sudden spike:** Memory jumped in one step. Correlates with a specific event (deployment, traffic spike, specific request type).
- **Plateau breach:** Memory has been near the threshold for a long time and finally crossed it. Alert noise is likely.

---

## Step MEM-3 — Baseline Comparison

Retrieve the same memory metrics for the same time of day over the previous 3 days:

| Entity | Incident peak memory % | Day −1 same time | Day −2 same time | Day −3 same time | Verdict |
|--------|----------------------|-----------------|-----------------|-----------------|---------| 
| | | | | | |

**Verdict rules:**
- If memory levels are comparable across all 4 windows: `Chronic condition / alert noise — threshold may be misconfigured`.
- If memory was lower on prior days and this occurrence is materially higher: `Incident-specific — valid signal`.
- If memory has been consistently growing across all prior days: `Gradual leak — root cause is ongoing, not incident-specific`.

---

## Step MEM-4 — Multi-Layer Metric Correlation

Retrieve **all related metrics across host, service, process, and related entity layers** during the investigation window. The goal is to establish **temporal ordering**: which metric spiked first, and which metrics followed as consequences.

**Metric layers to check:**

| Layer | Metrics | Entity | Notes |
|-------|---------|--------|-------|
| **Host-level** | Memory %, CPU %, disk I/O rate, disk I/O latency, network bytes/packets, NIC errors, paging rate | Affected host | Foundation layer |
| **Process-level** | Memory (heap/RSS/VSZ), CPU %, I/O read/write rate, disk I/O latency, page faults, packet retransmissions, connection resets, failed connections, bytes sent/received, context switch rate, thread count, GC pause time, GC overhead | Identified memory-consuming process | Explains what the process was doing |
| **Service-level** | Throughput (requests/min), response time (p50, p95, p99), error rate, database query latency, external call latency | All services on affected host | Application-layer impact |
| **Related entities** | Metrics from upstream/downstream services, database services, message brokers, cache services that the identified process interacts with | Any entity discovered via call traces or dependency topology | May reveal if memory growth originated externally |

**Temporal ordering table — record spike onset time for each metric:**

| Entity | Metric | Peak value | Baseline (avg prev 3 days, same time) | Spike onset time (UTC+8) | Spike observed? |
|--------|--------|------------|---------------------------------------|--------------------------|-----------------|
| Host | Memory % | | | | Yes / No |
| Host | Disk I/O rate | | | | Yes / No |
| Host | Paging rate | | | | Yes / No |
| Process (name: ) | Memory (heap/RSS) | | | | Yes / No |
| Process | CPU % | | | | Yes / No |
| Process | I/O rate | | | | Yes / No |
| Process | GC pause time | | | | Yes / No |
| Service (name: ) | Throughput | | | | Yes / No |
| Service | Response time (p95) | | | | Yes / No |
| Service | Error rate | | | | Yes / No |
| Related entity (name: ) | Metric (name: ) | | | | Yes / No |

**Temporal causation rules — identify the initiating metric:**

1. **Sort all metrics by spike onset time.** The metric that spikes earliest is the strongest candidate for the root cause.
2. **Establish the causal chain:**
   - If host disk I/O rate spikes at T1, host paging rate spikes at T2, and process memory spikes at T3 (T1 < T2 < T3) → **Disk I/O pressure is driving memory exhaustion** (OS is paging to manage contention).
   - If service throughput spikes at T1, process memory spikes at T2 → **Traffic-driven memory growth** (expected behavior if proportional).
   - If related entity (database) query latency spikes at T1, upstream service memory spikes at T2 → **Downstream slowness causing upstream memory accumulation** (request queuing).
   - If all metrics spike simultaneously → **Host-wide event or deployment** (check change events in MEM-5).

3. **If a metric spikes *after* the memory spike,** it is a consequence or collateral effect, not a root cause.

4. **If a related entity metric spikes *before* the process memory spike**, that related entity may be the initiating cause.

**Interpretation:**
- **If application impact is present** (service errors or latency up) → Proceed to MEM-5 (change events) and MEM-6 (traffic correlation) to confirm the mechanism.
- **If no application impact** (service throughput normal, errors normal) but process memory spikes → The spike may be driven by infrastructure operations (I/O, paging, network buffering). The root cause is whichever host/process metric spiked first.

---

## Step MEM-5 — GC Overhead Check (JVM / .NET Processes)

If the affected process is JVM-based (Java, Kotlin, Scala) or .NET:

1. Retrieve GC pause time / GC overhead metrics for the process over the investigation window.
2. Check for `GC_OVERHEAD_LIMIT_EXCEEDED` events or equivalent.
3. Look for a pattern of GC overhead increasing as heap fills.

| Time (UTC+8) | Heap used (%) | GC pause time (ms) | GC overhead (%) | GC type (minor/major/full) |
|--------------|---------------|-------------------|-----------------|---------------------------|
| | | | | |

**If GC overhead exceeds ~40% of CPU time:**
- The JVM is spending more time collecting than running application code. This is a near-OOM condition.
- The root cause is heap exhaustion, not CPU saturation (even if CPU appears high).

---

## Step MEM-6 — Change Event Check

Query change events on all affected hosts and process groups within ±30 minutes of **memory growth onset** (not just the alert time — use the trend start identified in MEM-2):
- Deployment events
- Configuration changes (especially JVM heap size settings, memory limits)
- Process restart events

| Time (UTC+8) | Event type | Entity | Description | Before memory growth onset? |
|--------------|------------|--------|-------------|------------------------------|
| | | | | Yes / No |

If a deployment precedes the memory growth trend start (not the alert time), the deployment is the primary hypothesis.

---

## Step MEM-7 — Traffic Correlation

Retrieve throughput for all services running on the affected host during the extended investigation window (72h + incident window):

Compare throughput trend with memory trend:

| Time period | Throughput (req/min) | Memory % | Correlated? |
|-------------|---------------------|---------|-------------|
| | | | Yes / No / Partial |

**If memory growth tracks throughput exactly:** Workload-driven growth. The mechanism is per-request memory allocation that exceeds capacity.

**If memory grows independently of throughput:** Leak pattern. The root cause is a specific code path, object, or cache that is not being released.

---

## Step MEM-8 — Process Restart and OOM Check

Check whether the process crashed or was restarted due to OOM:

- Query process availability events for all affected process groups in the investigation window.
- Check for `PROCESS_CRASH`, `PROCESS_RESTART`, `OUT_OF_MEMORY` events.

| Time (UTC+8) | Event | Process | OOM-induced? |
|--------------|-------|---------|-------------|
| | | | Yes / No / Unknown |

If an OOM-triggered restart occurred, record:
- The time of the restart (UTC+8).
- The time memory hit peak before the restart.
- Whether the service recovered after restart (memory returned to baseline).

Recovery after restart strongly suggests a memory leak rather than a permanent allocation growth issue.

---

## Step MEM-9 — Service Impact Assessment

Establish whether memory saturation caused measurable application-layer impact:

1. Retrieve error rate and response time for all services on the affected host during the investigation window.
2. Look for GC stall-induced response time spikes (response time spikes coinciding with GC pause peaks).

| Service | Error rate at peak | Error rate baseline | Response time at peak | Response time baseline | GC stall correlation? | Application impact? |
|---------|--------------------|---------------------|-----------------------|------------------------|----------------------|---------------------|
| | | | | | Yes / No | Yes / No |

---

## Step MEM-10 — Trace Analysis (Conditional)

Trace analysis applies for memory saturation only if application-layer impact was confirmed in MEM-9, specifically GC stall-induced latency.

If application impact confirmed:
- Query traces from the affected service during the memory peak period.
- Look for spans with long duration that correlate with GC pause times.
- Check for `OutOfMemoryError` or memory-related exception messages in span attributes.

If no application impact:
- Skip trace analysis. State: *"Trace analysis skipped — memory saturation did not produce measurable application-layer errors or latency. The event is infrastructure-level."*

---

## Step MEM-11 — Correlate and Establish Root Cause

Fill the correlation table:

| Timestamp (UTC+8) | Signal type | Entity | Finding | Confidence |
|-------------------|-------------|--------|---------|------------|
| | | | | Confirmed / Probable / Insufficient |

Apply the recurrence classification from Phase 1 Step 1.3.

**Root-cause gate — answer before writing the report:**
- [ ] Has the specific memory-consuming process been named?
- [ ] Has the trend shape been identified (leak / spike / plateau)?
- [ ] Has the trend start time been established (not just the alert time)?
- [ ] Has the baseline comparison (72h trend + previous 3 days same-time) been run?
- [ ] Have all metric layers (host, service, process, related entities) been checked and temporal ordering established?
- [ ] Has the metric that spiked first been identified as the root-cause initiator?
- [ ] Has GC overhead been checked for JVM/CLR processes?
- [ ] Has application-layer impact been confirmed or ruled out?
- [ ] Is the recurrence classification applied?

**Prohibited conclusions:**
- Do not conclude "memory saturation on [host]" without naming the specific process and the mechanism (leak, GC failure, allocation growth, infrastructure-driven).
- Do not use the alert time as the root cause timestamp — use the trend start time.
- Do not claim a gradual trend as a discrete incident root cause unless a deployment or specific event explains the trend start.
- Do not skip multi-layer metric correlation (MEM-4). If metrics from any layer (host, service, process, related entities) are unavailable, explicitly state why and document the limitation.
- Do not establish root cause based only on temporal coincidence — establish causation by ruling out alternative explanations (e.g., coincident but independent infrastructure events).
- **Do not treat automated events as root cause.** Automated system events (e.g., `GC_OVERHEAD_LIMIT_EXCEEDED`, `GC_RESTART`, `PROCESS_RESTART`, `OUT_OF_MEMORY_TRIGGERED_RESTART`, `AUTO_SCALING_EVENT`) are **responses to underlying conditions**, not root causes. They may indicate the underlying issue existed, but the root cause is the condition that triggered the automated action. Example: An `OUT_OF_MEMORY_TRIGGERED_RESTART` event does not *cause* memory saturation — memory saturation *triggers* the restart. Always identify the underlying metric or condition (leak, GC pressure, workload spike) that initiated the automated response. **Document these automated events in the Change & Topology Events section for timeline purposes, but cite the underlying condition as the root cause, not the automated event itself.**

---

## Sections to Populate in the Report

| Report section | Required? | Notes |
|----------------|-----------|-------|
| Problem Overview | Yes | |
| Hypotheses investigated | Yes | Internal notes only. Include: memory leak, GC failure, workload growth, deployment regression, alert noise |
| Root Cause | Yes | Must name: specific process, trend shape, mechanism, trend start time |
| Affected Entities | Yes | Focus on hosts and process groups |
| Change & Topology Events | Yes | Correlate to trend start, not alert time |
| Trace Analysis | Conditional | Only if GC stall-induced application impact confirmed |
| DB Procedure Ranking | No | Skip unless DB process is the memory consumer (state why skipped) |

---
