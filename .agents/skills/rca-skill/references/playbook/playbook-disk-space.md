# Playbook — Low Disk Space

**Applies to:** `DISK_LOW`, disk full events, low disk space problems.

> **Before writing any DQL query in this playbook:** Apply the DQL Query Requirements from SKILL.md Global Rules. Every query must include `| fields` and `| limit`. Never repeat the same query with minor variations.

**Core question this playbook answers:**
> Which disk volume is filling, what is consuming the space, what is the growth rate and time-to-full, and is this a sudden event or a predictable trend?

---

## Investigation Priority Order

Low disk space problems are almost always infrastructure-level and rarely require trace analysis. The investigation focuses on:
1. Which volume on which host is affected.
2. What is filling the disk (logs, data files, temp files, core dumps).
3. Growth rate — is this a sudden spike or a steady trend that has hit a threshold?
4. Time-to-full estimate — is this urgent?
5. Whether application-layer impact has already occurred or is imminent.

**Trace analysis is almost never relevant for disk space problems.** Skip it unless the disk issue has already caused service errors (e.g. write failures, log rotation failures causing process errors).

---

## Step DISK-1 — Volume and Host Identification

From the problem metadata, identify:
- The exact host(s) affected.
- The exact disk volume/mount point that is low (e.g. `/`, `/var`, `/opt`, `/data`).
- Current disk utilisation % and free space (GB/TB).

| Host | Mount point | Total size | Used | Free | Utilisation % | Time of alert (UTC+8) |
|------|------------|-----------|------|------|--------------|----------------------|
| | | | | | | |

---

## Step DISK-2 — Disk Growth Trend (Mandatory)

Retrieve disk utilisation for the affected volume over the **72 hours preceding** the alert:

| Time (UTC+8) | Disk utilisation % | Free space (GB) | Notes |
|--------------|--------------------|-----------------|-------|
| Onset − 72h | | | |
| Onset − 48h | | | |
| Onset − 24h | | | |
| Onset − 12h | | | |
| Onset − 6h | | | |
| Onset − 1h | | | |
| Alert time | | | |

Identify the **growth shape**:
- **Steady linear growth:** Predictable accumulation (logs, data ingestion). The alert was expected eventually — this is a capacity management issue, not an incident.
- **Sudden spike:** Disk filled rapidly in a short window. Likely a specific event: log explosion, core dump, large data write, runaway process output.
- **Plateau then spike:** Disk was already near capacity and a small additional write pushed it over threshold.

Estimate **growth rate** (GB/hour or GB/day) and compute time-to-full from current utilisation.

---

## Step DISK-3 — Baseline Comparison

Retrieve disk utilisation at the same time of day for the previous 3 days:

| Volume | Alert utilisation % | Day −1 same time | Day −2 same time | Day −3 same time | Verdict |
|--------|--------------------|-----------------|-----------------|-----------------|---------| 
| | | | | | |

**Verdict rules:**
- If disk utilisation has been steadily growing across all 4 windows at roughly the same rate: `Gradual capacity trend — not a discrete incident. Root cause is sustained growth without capacity management`.
- If disk utilisation spiked sharply compared to prior days: `Incident-specific spike — investigate specific write event`.
- If disk has been near threshold for multiple days: `Alert noise risk — threshold may need adjustment`.

---

## Step DISK-4 — Multi-Layer Metric Correlation

Retrieve **all related metrics across host, service, process, and related entity layers** during the investigation window. The goal is to establish **temporal ordering**: which metric spiked first, and which metrics followed as consequences.

**Metric layers to check:**

| Layer | Metrics | Entity | Notes |
|-------|---------|--------|-------|
| **Host-level** | Disk utilization %, disk I/O read/write rate, disk I/O latency, CPU %, memory %, network bytes/packets, NIC errors | Affected host | Foundation layer |
| **Process-level** | Disk write/read rate, CPU %, memory %, file handle count, page faults, bytes sent/received | Processes identified in DISK-5 (space consumer) or all processes on host if consumer unknown | Explains what is writing to disk |
| **Service-level** | Throughput (requests/min), response time (p50, p95, p99), error rate, database query latency, log ingestion rate | All services on affected host | Application-layer impact |
| **Related entities** | Metrics from log aggregators, data warehouses, backup services, message brokers, databases that write to the affected volume | Any entity discovered via deployment configuration or topology | May reveal if the disk growth originated externally |

**Temporal ordering table — record spike onset time for each metric:**

| Entity | Metric | Peak value | Baseline (avg prev 3 days, same time) | Spike onset time (UTC+8) | Spike observed? |
|--------|--------|------------|---------------------------------------|--------------------------|-----------------|
| Host | Disk utilization % | | | | Yes / No |
| Host | Disk I/O write rate | | | | Yes / No |
| Host | CPU % | | | | Yes / No |
| Host | Memory % | | | | Yes / No |
| Process (name: ) | Disk write rate | | | | Yes / No |
| Process | File handle count | | | | Yes / No |
| Service (name: ) | Throughput | | | | Yes / No |
| Service | Response time (p95) | | | | Yes / No |
| Service | Log ingestion rate | | | | Yes / No |
| Related entity (name: ) | Metric (name: ) | | | | Yes / No |

**Temporal causation rules — identify the initiating metric:**

1. **Sort all metrics by spike onset time.** The metric that spikes earliest is the strongest candidate for the root cause.
2. **Establish the causal chain:**
   - If service throughput spikes at T1 and disk write rate spikes at T2 (T2 > T1) → **Traffic-driven disk growth** (expected if proportional).
   - If related entity (log aggregator) throughput spikes at T1, and host disk utilization spikes at T2 → **Upstream log volume spike is filling the disk**.
   - If process CPU spikes at T1, disk I/O latency spikes at T2, and disk utilization spikes at T3 (T1 < T2 < T3) → **Process is causing I/O that is filling the disk**.
   - If all metrics spike simultaneously → **Host-wide event or deployment** (check change events in DISK-5).

3. **If a metric spikes *after* the disk utilization spike,** it is a consequence or collateral effect, not a root cause.

4. **If a related entity metric spikes *before* the host disk utilization spike**, that related entity may be the initiating cause.

**Interpretation:**
- **If application impact is present** (service errors or latency up, write failures logged) → Proceed to DISK-5 (change events) to confirm the mechanism.
- **If no application impact yet** (service errors normal, throughput normal) but disk is filling → The growth may be driven by background operations (backups, log rotation, archival). The root cause is whichever metric spiked first and the associated process/service responsible.

---

## Step DISK-5 — Change Event Check

Query change events on the affected host within ±30 minutes of disk growth spike onset (use the trend from DISK-2 to identify when growth accelerated, not just when the alert fired):

| Time (UTC+8) | Event type | Entity | Description | Before disk growth spike? |
|--------------|------------|--------|-------------|--------------------------|
| | | | | Yes / No |

Events to look for:
- Deployment (did a new version start writing more logs or data?)
- Configuration change (was log verbosity increased? Was a debug mode enabled?)
- Process restart (did a restart generate a core dump?)
- Scaling event (did new instances start writing to the same shared volume?)

---

## Step DISK-6 — Space Consumer Identification

This step requires host-level investigation. If Dynatrace does not expose disk consumer data, note this and recommend a manual `du` or equivalent command.

If host extension data or process metrics expose file write rates:

| Process / service | Estimated write rate (MB/min) | Likely file type | Path |
|-------------------|-----------------------------|-----------------|------|
| | | Logs / Data / Temp / Core dump | |

If Dynatrace data does not identify the consumer:
- State: *"Disk space consumer cannot be identified from Dynatrace telemetry alone. Recommended manual check: `du -sh /* | sort -rh | head -20` on [host name] to identify the largest directories."*
- Do not fabricate a consumer. Record as `Not available — manual investigation required`.

---

## Step DISK-7 — Application Impact Assessment

Check whether the low disk condition has already caused application-layer errors:

1. Query error rate and response time for all services on the affected host during the investigation window.
2. Look for `DISK_WRITE_ERROR`, file system full errors, or log rotation failure events in process events.

| Service | Error rate at alert time | Error rate baseline | Disk-related errors in events? | Application impact? |
|---------|--------------------------|---------------------|-------------------------------|---------------------|
| | | | Yes / No | Yes / No |

**If application impact confirmed:**
- Document the impact and the timestamp.
- Proceed to DISK-7 (trace analysis).

**If no application impact yet:**
- State: *"No application-layer impact detected at time of analysis. Disk saturation has not yet caused service errors, but projected time-to-full is [estimate]. Immediate remediation is recommended."*
- Skip trace analysis.

---

## Step DISK-8 — Trace Analysis (Conditional)

Trace analysis is only required if DISK-6 confirmed application-layer errors caused by disk issues (e.g. write failures, log pipeline failures causing service errors).

If relevant:
- Query traces with error status from the affected service during the investigation window.
- Look for spans with `DISK_WRITE`, `FILE_IO`, or similar operation names showing errors.
- Look for error messages referencing "no space left on device", "disk full", "write error".

If no application impact: *"Trace analysis skipped — disk saturation has not yet produced application-layer errors. No relevant traces available."*

---

## Step DISK-9 — Urgency and Time-to-Full Assessment

Based on the growth rate from DISK-2, estimate:

| Volume | Current utilisation % | Growth rate | Estimated time-to-full | Urgency |
|--------|----------------------|------------|----------------------|---------|
| | | GB/hour or GB/day | | Critical (<2h) / High (<12h) / Medium (<24h) / Low (>24h) |

This is a required field in the report regardless of whether application impact has occurred.

---

## Step DISK-10 — Correlate and Establish Root Cause

Fill the correlation table:

| Timestamp (UTC+8) | Signal type | Entity | Finding | Confidence |
|-------------------|-------------|--------|---------|------------|
| | | | | Confirmed / Probable / Insufficient |

Apply the recurrence classification from Phase 1 Step 1.3.

**Root-cause gate — answer before writing the report:**
- [ ] Has the specific affected volume and host been named?
- [ ] Has the growth trend shape been identified (gradual / spike / plateau)?
- [ ] Has the growth rate and time-to-full been estimated?
- [ ] Have all metric layers (host, service, process, related entities) been checked and temporal ordering established?
- [ ] Has the metric that spiked first been identified as the root-cause initiator?
- [ ] Has the space consumer been identified or explicitly noted as requiring manual investigation?
- [ ] Has application-layer impact been confirmed or ruled out?
- [ ] Is the recurrence classification applied?

**Prohibited conclusions:**
- Do not conclude "low disk space on [host]" without naming the specific volume, the mechanism (file type/process/service), the utilisation level, growth rate, and time-to-full.
- Do not claim a specific process or file type as the consumer without telemetry evidence or explicit statement of manual investigation required.
- Do not omit the urgency assessment.
- Do not skip multi-layer metric correlation (DISK-4). If metrics from any layer (host, service, process, related entities) are unavailable, explicitly state why and document the limitation.
- Do not establish root cause based only on temporal coincidence — establish causation by ruling out alternative explanations (e.g., coincident but independent host operations).
- **Do not treat automated events as root cause.** Automated system events (e.g., `LOG_ROTATION_FAILURE`, `BACKUP_STARTED`, `ARCHIVE_GENERATION`, `AUTO_CLEANUP_TRIGGERED`, `PROCESS_RESTART_ON_DISK_FULL`) are **responses to underlying conditions**, not root causes. They may indicate the underlying issue existed, but the root cause is the condition that triggered the automated action. Example: A `LOG_ROTATION_FAILURE` event does not *cause* low disk space — low disk space *triggers* the rotation failure. Always identify the underlying metric or process (file accumulation, service throughput spike, unmanaged growth) that initiated the condition leading to the automated response. **Document these automated events in the Change & Topology Events section for timeline purposes, but cite the underlying condition as the root cause, not the automated event itself.**

---

## Sections to Populate in the Report

| Report section | Required? | Notes |
|----------------|-----------|-------|
| Problem Overview | Yes | Include time-to-full estimate |
| Hypotheses investigated | Yes | Internal notes only. Include: log accumulation, data growth, deployment-triggered write increase, core dumps, alert noise |
| Root Cause | Yes | Must name: specific volume, growth mechanism, estimated urgency |
| Affected Entities | Yes | Focus on hosts; process groups only if a specific process is the consumer |
| Change & Topology Events | Yes | |
| Trace Analysis | Conditional | Only if disk-caused application errors confirmed |
| DB Procedure Ranking | No | Skip — state: "DB procedure ranking not applicable for disk space problems." |

---
