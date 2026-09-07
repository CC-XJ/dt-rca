# Playbook — CPU Saturation

**Applies to:** `CPU_SATURATED`, high CPU utilisation events, process CPU spike problems.

> **Before writing any DQL query in this playbook:** Apply the DQL Query Requirements from SKILL.md Global Rules. Every query must include `| fields` and `| limit`. Never repeat the same query with minor variations.

**Core question this playbook answers:**
> Which process or thread is consuming CPU, is this caused by a specific workload pattern or code path, and is this an incident-specific event or a recurring baseline behaviour?

---

## Investigation Priority Order

CPU saturation problems trace to one of five mechanisms:
1. A specific process is consuming abnormally high CPU due to a traffic or workload spike.
2. A deployment or configuration change introduced an inefficient code path (e.g. tight loop, excessive serialisation).
3. A runaway or zombie process consuming CPU independent of request traffic.
4. Scheduled job or batch process competing with live traffic.
5. A downstream dependency slowness causing upstream retry storms that amplify CPU usage.

**Important:** CPU saturation is frequently a chronic condition or alert noise. The recurrence pre-check from Phase 1 is especially critical for this problem type. Do not proceed to root cause without it.

---

## Step CPU-1 — Host and Process Scoping

Identify all affected hosts and their process groups from the problem context.

For each affected host, retrieve over the investigation window:
- CPU utilisation (overall host)
- Per-process CPU utilisation (break down by process group)

| Host | Peak CPU % | Time of peak (UTC+8) | Top CPU-consuming process at peak | CPU % of that process |
|------|-----------|---------------------|----------------------------------|-----------------------|
| | | | | |

Identify which **specific process** is responsible for the CPU spike, not just which host.

**Temporal alignment gate:**
- A process may only be used as the CPU root-cause candidate if its abnormal CPU activity overlaps the host spike window or clearly begins before the host peak.

- If a process first appears or first becomes abnormal **after** the host peak, treat it as downstream, incidental, or unrelated until proven otherwise.

- Do not merge later observations into the causal chain just because they share the same host or broad process family name.

- Record the earliest abnormal timestamp for the host and for each candidate process separately before drawing any conclusion.

---

## Step CPU-2 — Baseline Comparison (Mandatory Before Any Conclusion)

For each metric showing elevated CPU, retrieve the same metric at the same time of day for the previous 3 days:

| Host / Process | Incident peak CPU % | Day −1 same time | Day −2 same time | Day −3 same time | Verdict |
|----------------|--------------------|-----------------|-----------------|-----------------|---------| 
| | | | | | |

**Verdict rules:**
- If the incident CPU level is within the normal range of the previous 3 days: **do not claim CPU saturation as root cause**. Classify using the recurrence classification from Phase 1.
- If the incident CPU level is materially higher than the previous 3 days: `Incident-specific spike — valid signal`.
- If CPU has been trending upward across all 4 windows: `Worsening trend — likely capacity issue`.

This step is mandatory. Failure to run it means CPU saturation cannot be claimed as root cause.

---

## Step CPU-2a — Multi-Layer Metric Correlation

Retrieve **all related metrics across host, service, process, and related entity layers** during the investigation window. The goal is to establish **temporal ordering**: which metric spiked first, and which metrics followed as consequences.

**Metric layers to check:**

| Layer | Metrics | Entity | Notes |
|-------|---------|--------|-------|
| **Host-level** | CPU Usage, Memory Used, Availability, Network Traffic, Page Faults, Swap Usage, VM Memory Usage, Memory Compression, Memory Swapping | Affected host | Foundation layer |
| **Process-level** | Availability, CPU Usage, Mmeory Used, I/O, Traffic, Requests, Connectivity, TCP Connections, Packet Retransmissions, Round-trip times, Throughput | Identified CPU-consuming process | Explains what the process was doing |
| **Service-level** | Throughput (requests/min), response time (p50, p95, p99), error rate, database query latency, external call latency | All services on affected host | Application-layer impact |
| **Related entities** | Metrics from upstream/downstream services, database services, message brokers, external dependencies that the identified process interacts with | Any entity discovered via call traces or dependency topology | May reveal if the spike originated externally |

**Temporal ordering table — record spike onset time for each metric:**

| Entity | Metric | Peak value | Baseline (avg prev 3 days, same time) | Spike onset time (UTC+8) | Spike observed? |
|--------|--------|------------|---------------------------------------|--------------------------|-----------------|
| Host | CPU % | | | | Yes / No |
| Host | Disk I/O rate | | | | Yes / No |
| Host | Network errors/retransmissions | | | | Yes / No |
| Host | Paging rate | | | | Yes / No |
| Process (name: ) | CPU % | | | | Yes / No |
| Process | I/O rate | | | | Yes / No |
| Process | Network retransmissions | | | | Yes / No |
| Service (name: ) | Throughput | | | | Yes / No |
| Service | Response time (p95) | | | | Yes / No |
| Service | Error rate | | | | Yes / No |
| Related entity (name: ) | Metric (name: ) | | | | Yes / No |

**Temporal causation rules — identify the initiating metric:**

1. **Sort all metrics by spike onset time.** The metric that spikes earliest is the strongest candidate for the root cause.
2. **Establish the causal chain:**
   - If Host network retransmissions spike at T1, Process CPU spikes at T2 (T2 > T1), and Service throughput is normal → **Network operations are driving process CPU.**
   - If Service throughput spikes at T1, Process CPU spikes at T2, Host disk I/O spikes at T3 → **Traffic increase is driving the cascade** (expected behavior if proportional).
   - If Process metric spikes at T1, multiple other metrics spike shortly after → **Process-level event is initiating**.
   - If all metrics spike simultaneously → **Host-wide event** (e.g., deployment, config change, or external load).

3. **If a metric spikes *after* the CPU spike,** it is a consequence or collateral effect, not a root cause.

4. **If a related entity metric spikes *before* the process CPU spike**, that related entity may be the initiating cause (e.g., downstream database slowness causing upstream retry storms).

**Interpretation:**
- **If application impact is present** (service errors or latency up) → Proceed to CPU-4 (change events) and CPU-5 (process restart check) to confirm or exclude infrastructure events.
- **If no application impact** (service throughput normal, errors normal, latency normal) but process CPU and host CPU spike → The spike is infrastructure-level. The root cause is whichever host/process metric spiked first.

---

## Step CPU-3 — Change Event Check

Query change events on all affected hosts and process groups within ±30 minutes of problem onset:
- Deployment events
- Configuration change events
- Process restart events

| Time (UTC+8) | Event type | Entity | Description | Before problem onset? |
|--------------|------------|--------|-------------|----------------------|
| | | | | Yes / No |

If a deployment precedes the CPU spike and there is no corresponding traffic increase, the deployment likely introduced an inefficient code path.

---

## Step CPU-4 — Process Restart and Crash Check

Check whether the high CPU process crashed or restarted during or after the peak:

- Query process availability events for all affected process groups in the investigation window.
- Check for `PROCESS_CRASH`, `PROCESS_RESTART`, or `PROCESS_UNAVAILABLE` events.

| Time (UTC+8) | Event | Process | Preceded by CPU peak? |
|--------------|-------|---------|----------------------|
| | | | Yes / No |

If a process event is observed only **after** the host CPU peak, do not use it as the initiating cause of the spike. At most, treat it as a consequence, cleanup event, or secondary observation.

If a process crash follows a CPU peak, this is consistent with OOM or CPU starvation causing the crash. Note the sequence.

---

## Step CPU-5 — Service Impact Assessment

CPU saturation is an infrastructure event. Establish whether it caused measurable application-layer impact:

1. Retrieve error rate and response time for all services on the affected host during the investigation window.
2. Compare against baseline.

| Service | Error rate at peak | Error rate baseline | Response time at peak | Response time baseline | Application impact? |
|---------|--------------------|---------------------|-----------------------|------------------------|---------------------|
| | | | | | Yes / No |

**If no measurable application impact:**
- This is a strong signal for `Likely alert noise / likely false positive` classification — especially if the CPU level is habitual and requests are completing normally.
- State this explicitly. Do not manufacture a root cause narrative.

**If measurable application impact (errors or latency increase):**
- Document the impact on services and link the CPU peak timestamp to the service degradation onset.

---

## Step CPU-6 — Trace Analysis (Conditional)

Trace analysis applies for CPU saturation only if application-layer impact was confirmed in CPU-5.

If application impact is confirmed:
- Query traces from the affected service during the CPU peak period.
- Look for spans with abnormally long self-time (indicating CPU-bound computation, not I/O wait).
- Look for unusually high span counts per trace (indicating retry storms or loops).

| Seq | Span name | Service | Duration | Status | Span count in trace | Key observation |
|-----|-----------|---------|----------|--------|--------------------|-----------------| 
| | | | | | | |

If no application impact:
- Skip trace analysis. State: *"Trace analysis skipped — no measurable application-layer impact observed during the CPU saturation window. The event appears to be infrastructure-level only."*

---

## Step CPU-7 — Correlate and Establish Root Cause

Fill the correlation table:

| Timestamp (UTC+8) | Signal type | Entity | Finding | Confidence |
|-------------------|-------------|--------|---------|------------|
| | | | | Confirmed / Probable / Insufficient |

Apply the recurrence classification from Phase 1 Step 1.3.

**Root-cause gate — answer before writing the report:**
- [ ] Has the specific CPU-consuming process (not just host) been named?
- [ ] Has the baseline comparison (previous 3 days) been run and documented?
- [ ] Have all metric layers (host, service, process, related entities) been checked and temporal ordering established?
- [ ] Has the metric that spiked first been identified as the root-cause initiator?
- [ ] Has application-layer impact been confirmed or explicitly ruled out?
- [ ] Is the recurrence classification applied?

**Prohibited conclusions:**
- Do not conclude "CPU saturation on [host]" without naming the specific process and the metric that triggered the cascade.
- Do not claim CPU saturation as root cause if the CPU level is within the normal baseline range.
- Do not infer application impact — it must be evidenced by error rate or response time data.
- Do not skip multi-layer metric correlation (CPU-2a). If metrics from any layer (host, service, process, related entities) are unavailable, explicitly state why and document the limitation.
- Do not establish root cause based only on temporal coincidence — establish causation by ruling out alternative explanations (e.g., coincident but independent infrastructure events).
- Do not use a process that first appears after the host spike window as the cause of that spike.
- Do not promote a later-arriving metric to causal status unless you have established a direct causal link (e.g., process restart triggering I/O, not just coincidence).
- **Do not treat automated events as root cause.** Automated system events (e.g., `GC_RESTART`, `PROCESS_RESTART`, `AUTO_SCALING_EVENT`, `LOG_ROTATION`, `MEMORY_DUMP_GENERATION`) are **responses to underlying conditions**, not root causes. They may indicate the underlying issue existed, but the root cause is the condition that triggered the automated action. Example: A `GC_RESTART` event does not *cause* memory saturation — memory saturation *triggers* the GC restart. Always identify the underlying metric or condition that initiated the automated response. **Document these automated events in the Change & Topology Events section for timeline purposes, but cite the underlying condition as the root cause, not the automated event itself.**

---

## Sections to Populate in the Report

| Report section | Required? | Notes |
|----------------|-----------|-------|
| Problem Overview | Yes | |
| Hypotheses investigated | Yes | Internal notes only. Include: traffic spike, deployment regression, runaway process, scheduled job, alert noise |
| Root Cause | Yes | Must name: specific process, specific mechanism, whether application impact occurred |
| Affected Entities | Yes | Focus on hosts and process groups |
| Change & Topology Events | Yes | Key for distinguishing deployment regression from organic growth |
| Trace Analysis | Conditional | Only if application-layer impact confirmed |
| DB Procedure Ranking | No | Skip unless DB process is the CPU consumer (state why skipped) |

---
