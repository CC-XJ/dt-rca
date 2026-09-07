# Playbook — Multi-Service / Cascading Failure

**Applies to:** Problems affecting multiple services simultaneously, cascading failures, service dependency problems, problems where Davis AI identifies multiple root causes or propagation across services.

> **Before writing any DQL query in this playbook:** Apply the DQL Query Requirements from SKILL.md Global Rules. Every query must include `| fields` and `| limit`. Never repeat the same query with minor variations.

**Core question this playbook answers:**
> Which service is the origin of the failure, how did it propagate to downstream services, and is the root cause at the application layer (code/query) or infrastructure layer (host/process)?

---

## Investigation Priority Order

Multi-service problems are almost always the result of one of three patterns:
1. **Upstream origin:** One service degrades and all its callers are affected (downstream callers see errors or slow responses because their dependency is broken).
2. **Shared infrastructure origin:** A host, database, or network resource is degraded and all services sharing it are affected.
3. **Independent coincident failures:** Multiple unrelated services fail simultaneously — usually triggered by a deployment, infrastructure event, or scheduled job.

The primary task is to find the **single origin** (or the shared resource) rather than analysing each affected service independently. Do not produce a separate root cause for each service.

---

## Step MS-1 — Problem Scope Mapping

Build a complete map of all affected services, hosts, and process groups from the problem metadata.

| Entity name | Type | Entity ID | First anomaly timestamp (UTC+8) | Symptom type | Davis AI suggested? |
|-------------|------|-----------|---------------------------------|-------------|---------------------|
| | Service | | | Error rate / Response time / Unavailable | Yes / No |
| | Host | | | CPU / Memory / Disk | Yes / No |
| | Process | | | Crash / Saturation | Yes / No |

Sort by **first anomaly timestamp**. The entity with the earliest anomaly timestamp is the primary origin candidate.

---

## Step MS-2 — Topology and Dependency Mapping

Before any trace or metric analysis, map the service call topology:

1. Query the service call graph for all affected services in the investigation window.
2. Identify which services call which.
3. Determine call direction: is the affected service an upstream caller, a downstream dependency, or both?

Build a dependency map (text form if visual is not available):

```
[Caller A] → [Caller B] → [Primary Affected Service] → [Downstream DB / External API]
                ↓
           [Caller C]
```

This map determines the propagation direction. Errors propagate **upstream** (from dependency to caller). If Service B calls Service C and Service C fails, Service B will show errors — but Service C is the origin.

---

## Step MS-3 — Change Event Priority Check

Query change events on **all affected entities** within ±30 minutes of the earliest anomaly timestamp from MS-1:

| Time (UTC+8) | Event type | Entity | Description | Before earliest anomaly? |
|--------------|------------|--------|-------------|--------------------------|
| | | | | Yes / No |

**If a deployment or config change precedes the earliest anomaly on any entity:**
- This is the primary hypothesis across all affected services.
- Identify whether the change was deployed to the origin entity or a shared dependency.
- A change on a shared database or shared infrastructure affects all dependent services simultaneously.

**If no change events:**
- Record explicitly. The cause is likely traffic, a dependency failure, or a latent defect triggered by a specific workload.

---

## Step MS-4 — Origin Service Identification

Using the dependency map from MS-2 and the anomaly timestamps from MS-1, identify the origin:

**Rule 1 — Earliest timestamp wins.** The service or host that showed the first anomaly event is the origin candidate.

**Rule 2 — Dependency direction.** If Service A calls Service B:
- Service B anomaly precedes Service A anomaly → root cause is in Service B.
- Service A anomaly precedes Service B anomaly → root cause is in Service A (or a shared resource upstream of A).

**Rule 3 — Shared resource check.** If multiple services on the same host degrade simultaneously, the host is the origin — not any individual service.

State the identified origin explicitly:
> *"Origin identified as: [entity name] ([entity ID]). Evidence: earliest anomaly timestamp at [time], upstream of all other affected services in the call graph."*

---

## Step MS-5 — Origin Investigation

Once the origin is identified, load and execute the relevant single-service playbook for the origin's symptom type:

| Origin symptom | Load this playbook |
|----------------|--------------------|
| Response time degradation | `playbook-response-time.md` Steps RT-2 through RT-6 |
| Failure rate increase | `playbook-failure-rate.md` Steps FR-2 through FR-6 |
| CPU saturation | `playbook-cpu-saturation.md` Steps CPU-2 through CPU-8 |
| Memory saturation | `playbook-memory-saturation.md` Steps MEM-2 through MEM-10 |
| Disk space | `playbook-disk-space.md` Steps DISK-2 through DISK-9 |

Execute the loaded playbook steps **only for the origin entity**. Do not repeat the full playbook for every affected service — that is analysis noise.

---

## Step MS-6 — Propagation Path Validation

After the origin investigation, validate the propagation path:

1. Select one downstream service that was affected.
2. Query its error rate and response time over the investigation window.
3. Confirm the degradation onset timestamp is **after** the origin anomaly timestamp.
4. Confirm the error type on the downstream service matches what would be expected from the origin failure (e.g. timeout errors if origin was slow, connection errors if origin was unavailable).

| Downstream service | Degradation onset (UTC+8) | After origin onset? | Error type | Consistent with origin failure? |
|-------------------|--------------------------|---------------------|------------|--------------------------------|
| | | Yes / No | | Yes / No / Inconsistent |

If the propagation path is inconsistent (downstream degraded before the origin, or error types don't match), revisit the origin identification in MS-4.

---

## Step MS-7 — DB Procedure and Query Ranking (Mandatory for Application-Origin Problems)

If the origin is application-layer (response time or failure rate on a service — not infrastructure):

Execute the DB procedure ranking from the relevant playbook for the **origin service only**.

If the origin is infrastructure-layer (CPU, memory, disk on a host):
- Skip DB ranking. State: *"DB procedure ranking not applicable — root cause origin is infrastructure-level ([entity name])."*

---

## Step MS-8 — Downstream Impact Summary

Produce a concise impact summary for all affected downstream services — do not perform a separate deep investigation for each:

| Downstream service | Impact type | Peak error rate / response time | Duration of impact | Recovered independently? |
|-------------------|--------------|---------------------------------|--------------------|--------------------------|
| | Error propagation / Latency increase / Unavailability | | | Yes (after origin resolved) / No (independent issue) |

If a downstream service did **not** recover after the origin was resolved, it may have an independent issue. Flag it and recommend a separate RCA.

---

## Step MS-9 — Correlate and Establish Root Cause

Fill the correlation table — include origin and at least one downstream service:

| Timestamp (UTC+8) | Signal type | Entity | Finding | Confidence |
|-------------------|-------------|--------|---------|------------|
| | | | | Confirmed / Probable / Insufficient |

Apply the recurrence classification from Phase 1 Step 1.3.

**Root-cause gate — answer before writing the report:**
- [ ] Is the single origin entity named with its earliest anomaly timestamp?
- [ ] Is the propagation direction validated (timestamps confirm downstream degraded after origin)?
- [ ] Has the origin symptom been investigated using the appropriate single-service playbook steps?
- [ ] Has the downstream impact been summarised without inflating the root cause count?
- [ ] Is the recurrence classification applied?

**Prohibited conclusions:**
- Do not produce a separate root cause for each affected service.
- Do not state "multiple services failed" without naming the single origin and propagation mechanism.
- Do not conclude shared infrastructure is the cause without checking that the degradation onset timestamps on all affected services are coincident (within 1–2 minutes of each other).

---

## Trace Analysis for Multi-Service Problems

Cap at 3 traces following the standard template selection order:
- **Trace 1 — Root cause trace:** A trace originating from the origin service that shows the failure mechanism.
- **Trace 2 — Propagation trace:** A trace from a downstream service showing the error as received from the upstream origin.
- **Trace 3 — Second propagation trace:** A trace from a second downstream service or a different endpoint on the same downstream service.

The propagation traces (2 and 3) should show the upstream error visible in the call chain — this validates the propagation path.

---

## Sections to Populate in the Report

| Report section | Required? | Notes |
|----------------|-----------|-------|
| Problem Overview | Yes | List all affected services; identify origin in "Primary endpoint(s)" |
| Hypotheses investigated | Yes | Internal notes only. Include: shared infrastructure failure, deployment on origin service, dependency chain failure, independent coincident failures |
| Root Cause | Yes | Must name single origin; describe propagation path; do not list each service as a separate cause |
| Affected Entities | Yes | Include all services, hosts, processes — group them by role (origin / downstream) |
| Change & Topology Events | Yes | |
| Trace Analysis | Yes | Follow multi-service trace selection above |
| DB Procedure Ranking | Conditional | Only for application-layer origins; skip for infrastructure origins |

---
