# Playbook — Failure Rate Increase

**Applies to:** `FAILURE_RATE_INCREASED`, HTTP 5xx surge, error spike events.

> **Before writing any DQL query in this playbook:** Apply the DQL Query Requirements from SKILL.md Global Rules. Every query must include `| fields` and `| limit`. Never repeat the same query with minor variations.

**Core question this playbook answers:**
> What specific operation, service call, or input condition is producing errors, and is this a code-level failure, a dependency failure, or a configuration/deployment-triggered regression?

---

## Investigation Priority Order

Failure-rate problems trace to one of four mechanisms:
1. A deployment or configuration change introduced a code regression.
2. A downstream dependency began returning errors, causing upstream failure propagation.
3. A specific request pattern (endpoint, payload, query parameter) is triggering unhandled exceptions.
4. An infrastructure event (process crash, OOM, disk full) caused the service to fail requests.

This playbook investigates in that order. Always check for change events first.

---

## Step FR-1 — Change Event Priority Check

This is the first step — before any trace or metric analysis.

Query change events on all affected entities within the investigation window ± 30 minutes of `problemStart`:
- Deployment events
- Configuration change events
- Process restart events
- Scaling events

| Time (UTC+8) | Event type | Entity | Description | Before or after problem onset? |
|--------------|------------|--------|-------------|-------------------------------|
| | | | | |

**If a deployment or config change event precedes `problemStart` by ≤ 30 minutes:**
- This is the primary hypothesis. Mark it `Confirmed (pending trace validation)`.
- Continue with trace analysis to identify which specific endpoint or code path regressed.

**If no change events are found:**
- Record explicitly: *"No deployment or configuration change events detected within ±30 minutes of problem onset."*
- The root cause is likely a dependency failure or a traffic-triggered exposure of a latent defect.

---

## Step FR-2 — Error Span Identification

Query traces for the primary affected service within the investigation window. Filter for traces with `status == ERROR` or HTTP response code ≥ 500.

For the top 3 error-bearing traces (select by earliest timestamp, not by count):

| Seq | Span name | Service | Duration | Status | HTTP code | `url.path` | `url.query` | `db.query.text` | Error message / exception |
|-----|-----------|---------|----------|--------|-----------|-----------|------------|----------------|--------------------------|
| | | | | | | | | | |

Identify:
- The **first error span** — the span where the error originates (not where it is reported upstream).
- The **exact error message or exception type** on that span.
- Whether the error originates in a **DB call** (look for `db.*` attributes and error on the DB span).
- Whether the error originates in an **outbound HTTP call** to a downstream service (look for the child span, not the parent).
- The **timestamp** of the first error span — compare against the earliest event from FR-1.

### FR-2a — Error Pattern Grouping

Beyond the 3 traces, query the total count of error spans grouped by:
- `url.path` (which endpoints are failing)
- Error type / exception class (if available in span attributes)
- `db.query.text` (if DB errors are present)

| `url.path` | Error count | % of total requests | First error timestamp (UTC+8) |
|-----------|------------|--------------------|-----------------------------|
| | | | |

This reveals whether the error is **widespread** (all endpoints affected — suggests infrastructure or deployment) or **localised** (one endpoint — suggests a specific code path or input).

---

## Step FR-3 — DB Procedure and Query Ranking (Mandatory)

Query all spans with `db.query.text` in the investigation window. Filter for those with error status.

**Top 5 DB errors by count:**

| Rank | `db.query.text` | Error count | Error message | Overlaps incident window? |
|------|----------------|------------|---------------|--------------------------|
| | | | | |

If no DB errors are found, state this explicitly and move on. Do not skip this step silently.

If stored procedures are present with errors, add a dedicated stored procedure error table.

---

## Step FR-4 — Downstream Dependency Check

If the first error span (from FR-2) is an outbound call to another service or external endpoint:

1. Identify the downstream service name and entity ID.
2. Retrieve the error rate and response time for the downstream service over the investigation window.
3. Check whether the downstream service has its own Davis problem in the same window.
4. Compare downstream error rate baseline (previous 3 days, same time).

| Downstream entity | Error rate (incident) | Error rate (baseline avg) | Has own Davis problem? | Error onset before upstream? |
|-------------------|-----------------------|--------------------------|----------------------|------------------------------|
| | | | Yes / No | Yes / No |

If the downstream service error rate increased **before** the primary service failure rate, the root cause is in the downstream service. Shift the affected entity and root cause accordingly.

---

## Step FR-5 — Metric Validation

For the primary affected service, retrieve over the investigation window:
- Error rate (requests/min that returned error)
- Throughput
- Response time

For each metric showing degradation, retrieve the same metric for the previous 3 days at the same time of day:

| Metric | Incident value | Day −1 same time | Day −2 same time | Day −3 same time | Verdict |
|--------|---------------|-----------------|-----------------|-----------------|---------|
| Error rate | | | | | |
| Throughput | | | | | |

**Verdict rules:**
- Error rate at near-zero baseline that spikes to significant level during incident: `Incident-specific — valid root cause signal`.
- Error rate that regularly spikes at this time of day: `Recurring pattern — apply recurrence classification`.
- Throughput spike accompanying the error rate increase: `Traffic-triggered — consider volume hypothesis`.

---

## Step FR-6 — Correlate and Establish Root Cause

Fill the correlation table:

| Timestamp (UTC+8) | Signal type | Entity | Finding | Confidence |
|-------------------|-------------|--------|---------|------------|
| | | | | Confirmed / Probable / Insufficient |

Apply the recurrence classification from Phase 1 Step 1.3.

**Root-cause gate — answer before writing the report:**
- [ ] Is the first error span identified with its exact error message?
- [ ] Is the error scope (widespread vs localised) established?
- [ ] Is the upstream vs downstream origin resolved?
- [ ] If a change event was found, is the correlation to the error onset confirmed by timestamp?

**Prohibited conclusions:**
- Do not conclude "failure rate increased on [service]" without naming the error type and the failing operation.
- Do not conclude a deployment caused the failure unless the deployment timestamp precedes the first error span timestamp.
- Do not conclude a downstream dependency caused the failure unless the downstream error onset precedes the upstream failure rate increase.

---

## Sections to Populate in the Report

| Report section | Required? | Notes |
|----------------|-----------|-------|
| Problem Overview | Yes | |
| Hypotheses investigated | Yes | Internal notes only. Include: deployment regression, downstream dependency failure, specific endpoint defect, infrastructure failure |
| Root Cause | Yes | Must name: specific error, specific operation or endpoint, failure origin (upstream vs downstream) |
| Affected Entities | Yes | |
| Change & Topology Events | Yes | Critical for this problem type — must be first section checked |
| Trace Analysis | Yes | Focus on error traces, not slow traces |
| DB Procedure Ranking | Yes — errors only | Only error-bearing DB spans; skip if no DB errors found (state why) |

---
