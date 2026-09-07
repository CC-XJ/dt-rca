# Playbook — Response Time Degradation

**Applies to:** `RESPONSE_TIME_DEGRADED`, slow request events, latency increase problems.

> **Before writing any DQL query in this playbook:** Apply the DQL Query Requirements from SKILL.md Global Rules. Every query must include `| fields` and `| limit`. Never repeat the same query with minor variations.

**Core question this playbook answers:**
> What specific operation, query, or dependency is causing requests to take longer, and is this incident-specific or a recurring pattern?

---

## Investigation Priority Order

Response-time problems almost always trace to one of four mechanisms:
1. A slow or lock-contended database query or stored procedure
2. A slow downstream dependency (external API, internal service)
3. A thread/connection pool exhaustion at the application layer
4. Increased request volume hitting a fixed capacity limit

This playbook investigates in that order. Do not skip to a conclusion from endpoint latency alone.

---

## Step RT-1 — Event Timeline

From the problem events already attached to the problem, build the chronological timeline.

| Timestamp (UTC+8) | Event type | Entity | Metric / value | Description |
|-------------------|------------|--------|----------------|-------------|
| | | | | |

Identify:
- Which **service or host** showed the first anomaly event.
- Whether the Davis AI suggested a root cause — record it but do not accept it without trace + metric validation.
- Whether a **deployment or config change event** precedes problem onset by ≤ 30 minutes. If yes, this is the primary hypothesis until disproved.

---

## Step RT-2 — Trace Analysis

### RT-2a — Identify slowest traces

Query traces for the primary affected service within the investigation window. Sort by duration descending. Select:
- **Trace 1:** Longest duration trace — root cause candidate.
- **Trace 2:** Second distinct long-duration trace (different endpoint if possible) — pattern confirmation.
- **Trace 3:** A trace from a downstream service showing elevated latency — downstream impact.

For each trace, build the full span waterfall:

| Seq | Span name | Service | Duration | Status | `url.path` | `url.query` | `db.query.text` | Key observation |
|-----|-----------|---------|----------|--------|-----------|------------|----------------|-----------------|
| | | | | | | | | |

Identify:
- The **deepest span** with the longest self-time — this is where time is actually being spent.
- Whether the slow span is a **DB call** (`db.*` attributes present).
- Whether the slow span is an **outbound HTTP call** to a downstream service.
- The exact **span name, duration, and timestamp** of the bottleneck span.

### RT-2b — DB Procedure and Query Ranking (Mandatory)

Even if the trace waterfall already points to a clear bottleneck, this step is mandatory.

Query all spans with `db.query.text` or `url.query` in the investigation window for the primary service and all affected hosts/process instances.

Produce two rankings:

**Top 5 by max duration:**

| Rank | `db.query.text` / `url.query` | Max duration | Avg duration | Count | Overlaps incident window? |
|------|-------------------------------|-------------|-------------|-------|--------------------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Top 5 by call count:**

| Rank | `db.query.text` / `url.query` | Count | Max duration | Avg duration | Overlaps incident window? |
|------|-------------------------------|-------|-------------|-------------|--------------------------|
| 1 | | | | | |

If stored procedures are present (e.g. `EXECUTE sp_*`, `EXEC proc_*`), add a dedicated **Top Stored Procedures** table with the same columns.

**Root-cause gate:** If any DB query or procedure ranks in the top 3 by duration AND overlaps the incident window, the root cause conclusion MUST explicitly name that query/procedure. An endpoint-only conclusion is not permitted when this evidence exists.

---

## Step RT-3 — Metric Analysis

For each affected entity, retrieve these metrics over the investigation window:

**Services:**
- Response time (p50, p90, p99)
- Error rate
- Throughput (requests/min)

**Hosts:**
- CPU utilisation
- Memory utilisation

**Process groups:**
- JVM / CLR heap usage (if applicable)
- Thread count / active threads
- Connection pool saturation (if instrumented)

For every metric that shows degradation, immediately retrieve the **same metric for the same time-of-day window over the previous 3 days**. Present as a comparison:

| Metric | Incident peak | Day −1 same time | Day −2 same time | Day −3 same time | Verdict |
|--------|--------------|-----------------|-----------------|-----------------|---------|
| | | | | | Normal baseline / Incident-specific spike / Worsening trend |

**Verdict rules:**
- If the incident value is within 20% of the average of the previous 3 days: `Normal baseline — do not claim as root cause alone`.
- If the incident value is materially higher with no comparable prior occurrence: `Incident-specific spike — valid root cause signal`.
- If the value has been trending upward across all 4 windows: `Worsening trend — root cause is gradual degradation`.

---

## Step RT-4 — Dependency Check

If the bottleneck span identified in RT-2a is an outbound call to another service or external endpoint:

1. Retrieve metrics for the downstream service over the same investigation window.
2. Check whether the downstream service has its own Davis problem in the same window.
3. Compare downstream response time baseline (previous 3 days, same time).

If the downstream service response time degraded **before** the primary service anomaly event, the root cause is in the downstream service. Note this explicitly and shift the primary affected entity accordingly.

---

## Step RT-5 — Thread / Connection Pool Exhaustion Check

If no slow DB query or downstream dependency is found, check for resource saturation at the application layer:

- Query thread count metrics for the affected process group over the investigation window.
- Query connection pool metrics if instrumented.
- Check for `PROCESS_THREAD_COUNT_HIGH` or similar Davis events on the affected process.

If thread count or connection pool saturation precedes response time degradation onset, this is the mechanism. Name the specific pool or thread type.

---

## Step RT-6 — Correlate and Establish Root Cause

Using the evidence from RT-1 through RT-5, fill the correlation table:

| Timestamp (UTC+8) | Signal type | Entity | Finding | Confidence |
|-------------------|-------------|--------|---------|------------|
| | | | | Confirmed / Probable / Insufficient |

Apply the confidence labels:
- **Confirmed** — bottleneck span named + DB query/procedure named (if present) + metric spike is incident-specific (not baseline) + mechanism evidenced across ≥2 signal types.
- **Probable** — consistent with evidence but the specific mechanism (query name, pool name) is not fully traced.
- **Insufficient** — symptom identified (latency high) but cause unclear.

Apply the recurrence classification established in Phase 1 Step 1.3. If the recurrence check found this is a recurring pattern, say so in the root cause and provide the classification label.

**Prohibited conclusions:**
- Do not conclude "high response time on [endpoint]" without naming the mechanism.
- Do not conclude "DB slowness" without naming the specific query or procedure.
- Do not conclude "host CPU pressure" as the root cause of response time unless CPU saturation is confirmed to have preceded the response time increase AND is incident-specific (not baseline).

---

## Sections to Populate in the Report

All sections apply for this problem type.

| Report section | Required? | Notes |
|----------------|-----------|-------|
| Problem Overview | Yes | |
| Hypotheses investigated | Yes | Internal notes only. Include at least: DB slowness, downstream dependency, deployment change, traffic spike |
| Root Cause | Yes | Must name specific operation, query, or procedure |
| Affected Entities | Yes | |
| Change & Topology Events | Yes | Mandatory — absence of change is also a finding |
| Trace Analysis | Yes | All 3 traces required; skip only if tracing is not instrumented |
| DB Procedure Ranking | Yes | Include even if not the root cause — document what was checked |

---
