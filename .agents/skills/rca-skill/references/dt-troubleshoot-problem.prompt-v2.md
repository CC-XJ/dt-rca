---
agent: agent
description: Troubleshoot an existing Dynatrace problem. Uses events, traces, and metrics to establish root cause without querying logs.
---

# Troubleshoot a Dynatrace Problem

## Rules

- **ALWAYS start with the problem.** Never do broad log searches. Use root_cause_agent first, then scope all queries to problem context.
- Before executing any DQL query through the MCP Server, the agent MUST load [`../../.agents/skills/dt-dql-essentials`]. This skill defines:
    - DQL syntax standards
    - query optimisation rules
    - field projection requirements
    - limit requirements
    - time-scoping requirements
    - Dynatrace entity lookup patterns
    - UID conversion patterns
    - common investigation queries

    The DQL reference skill must be loaded exactly once per RCA execution. Do not reload it for every query. Once loaded, all subsequent DQL queries must comply with the standards defined there.

- **NEVER run broad queries.** Broad searches hit data limits and return noise. Scope everything to the problem timeframe and affected entities.
- **NEVER suggest checking other environments.** This prompt is for production troubleshooting only. Only mention dev/staging if the user explicitly asks.
- **NEVER query logs.** Root cause analysis uses events, traces, and metrics only. If root cause cannot be determined from these, suggest the user to query logs manually using the scoped timeframe and affected entities provided.

## Input

This prompt accepts three input formats:

**Format A — Pre-filled structured input:**
> "At [timestamp], service [service-name] has the following problem: [problem message]. Explain the error and suggest how to fix it."

Extract `timestamp`, `service-name`, and `problem message` directly. Use the **Root Cause Agent** to confirm the matching problem silently. Extract `problemId`, affected entity IDs, and the exact timeframe, then proceed to step 3.

**Format B — Problem ID only:**
> Just a problem ID, e.g. `P-12345`, optionally accompanied by a date.

**Format C — Manual:**
If no structured input is provided, proceed from step 1.


*(Format B only)*
Use the **Root Cause Agent** to search for the problem using progressive time window expansion:

1. Search **today** (or the provided date). Inform the user: *"Searching for problem [ID] — checking today..."*
2. If not found, expand to **last 3 days**. Inform the user: *"Not found yet — expanding search to 3 days..."*
3. If still not found, expand to **last 7 days**. Inform the user: *"Still not found — expanding search to 7 days..."*
4. If not found after 7 days, stop and tell the user: *"Problem [ID] was not found within the last 7 days. Please verify the problem ID or check if it belongs to a different tenant."* Do NOT query anything further.

Once found, extract `problemId`, affected entity IDs, and the exact timeframe, then proceed to step 3.


## Steps

### 1. List active problems *(Format C only)*

Use the **Root Cause Agent** to retrieve all currently active problems on the tenant.

Present results as a table:

| # | Problem ID | Title | Severity | Status | Start Time | Affected Entities | event.id |
|---|---|---|---|---|---|---|---|

If there are no active problems, check for recently closed problems (last 7 days) and show those instead.

**If no problems exist at all in the last 7 days:**
- Confirm the service name is correct
- Confirm you are connected to the intended production tenant/environment
- Stop here and tell the user: *"No problems found in this environment in the last 7 days. The issue may have affected a different service, or was not raised as a Dynatrace problem."*

### 2. Select a problem *(Format C only)*

Ask the user: *"Which problem would you like to investigate? Please enter the number or Problem ID."*

Wait for their response before proceeding.

### 3. Extract problem context

From the problem metadata, extract and present:
- `problemId`
- `startTime` and `endTime` (use "now" if still active)
- Davis AI root cause assessment (if available)
- All affected entities — services, hosts, process groups
- All problem events attached to the problem (deployment events, config changes, anomaly detections, etc.)
- If any affected entity is a group-level ID (`HOST_GROUP-*` or `PROCESS_GROUP-*`), resolve to leaf IDs now.
- Retain the group-level ID — it will be shown in the report for context.
- Carry forward both IDs: group ID for display, leaf ID for all deep links.
- If multiple leaf entities are returned, carry forward the top 1–3 ranked by error count or response-time degradation. Keep their parent group ID alongside.
- Never use a group-level ID in a deep link.

Compute the investigation window:
queryFrom = startTime - 5 min
queryTo = endTime + 5 min  (or now + 5 min if still active)

Present a summary of what was extracted before proceeding.

### 4. Analyze problem events

From the events already attached to the problem, build a chronological timeline:

| Timestamp | Event Type | Entity | Description |
|---|---|---|---|

Order events by timestamp. Look for:
- **Deployment or config change events** — did anything change just before the problem started?
- **Anomaly detection events** — which metric breached first, and on which entity?
- **Dependency or propagation events** — did the problem originate in one service and spread to others?

Identify the **earliest event** in the timeline. This is the likely origin point.

If the problem metadata already contains a Davis AI root cause assessment, note it here but continue to validate it with traces and metrics.

### 5. Investigate traces

**Skip this step if the problem type is infrastructure-focused** (CPU Saturation, Memory Saturation, Low Disk Space). Infrastructure playbooks do not require trace analysis — proceed directly to Step 6 (Analyze Metrics).

**For application-level problems** (Failure Rate, Response Time Degradation, Multi-Service) — continue below:

Using the affected entities and investigation window from step 3, query traces scoped tightly to:
- The **primary affected service** identified in step 4
- The **problem timeframe only**

Do not run open or broad trace queries. If the affected service is unclear, use the entity identified as the earliest anomaly in the event timeline.

Build a call chain from the spans:

| Span | Service | Operation | Duration | Status | Parent Span |
|---|---|---|---|---|---|

Identify:
- The **first span with an error** (`status == ERROR` or HTTP ≥ 500) — this is the error origin
- Whether the error propagated upstream from a dependency
- The timestamp of the first erroring span — compare this against the event timeline from step 4

If no erroring spans are found, note this and proceed to metrics. Do not expand the trace query scope without first checking metrics.

- Once the spans are identified, get the total count without any filter to identify any patterns.
- Before exiting trace analysis, explicitly check whether any spans contain `db.query.text` or `url.query`. If found, record the stored procedure name, duration, and timestamp, also note down the total count of either `url.path` or `db.query.text`. This is mandatory — do not skip even if an app-layer root cause already appears likely.

### 6. Analyze metrics

For each affected entity identified in step 3, retrieve key metrics over the investigation window:

- **Services**: error rate, response time, throughput
- **Hosts**: CPU utilization, memory utilization
- **Process**: any relevant process-level metrics

Look for:
- Which metric degraded **first** relative to the problem start time
- Whether metric degradation aligns with the earliest event from step 4 and the first erroring span from step 5
- Any metric that degraded on a **dependency** before the primary service — this suggests the root cause is downstream
- For every degraded metric found, always retrieve the same metric for the same time-of-day window over the previous 3 days (This is to identify whether it is a common behaviour or an abnormal behaviour).

### 6a. Recurrence and alert-noise check

Before concluding root cause, perform a recurrence check over the last 14 days for the same affected entities:

- Query Davis problems with the same or similar `event.name` / symptom type on the same host, process, or service.
- Query Davis events with the same symptom class (for example restarts, memory saturation, CPU saturation, failure-rate spikes) on the same entities.
- Compare the incident window against recurring same-entity patterns.

Use this check to classify the scenario:

- **Recurring true issue** - the pattern repeats and still shows a clear incident-specific degradation signal or business impact.
- **Likely alert noise / likely false positive** - the pattern repeats frequently and this occurrence is not materially different from the baseline or from prior events.
- **Inconclusive recurring pattern** - recurrence exists, but the available telemetry cannot separate expected behavior from incident behavior.

Guardrails:

- Never claim a high host or process metric as root cause purely because it breached a threshold if the same level is present in the previous 3 same-time windows or in recent similar problems.
- When recurrence is found, say so explicitly and downgrade confidence unless an incident-specific signal clearly separates this problem from the recurring baseline.
- If the evidence supports likely alert noise, say that directly instead of forcing a root-cause narrative.

### 7. Correlate and establish root cause

Using the evidence from steps 4, 5, and 6, correlate findings by timestamp:

| Timestamp | Signal Type | Entity | Finding |
|---|---|---|---|

Use the chronological order to reason about causality:
- The signal that appears **earliest** in the timeline is the most likely root cause origin
- A deployment or config change just before anomaly detection strongly suggests that as the trigger
- An error originating in a dependency before the primary service confirms a downstream root cause

State a clear root cause hypothesis with supporting evidence from each signal type. Apply the following confidence labels:
- **Confirmed** — earliest signal + mechanism evidenced across ≥2 signal types
- **Probable** — consistent with evidence but mechanism not fully traced
- **Insufficient** — symptom identified, cause unclear

Never label an endpoint path as root cause unless the underlying mechanism (query, procedure, resource contention) is evidenced.
Never label a chronic or repeating threshold breach as root cause unless this occurrence shows an incident-specific departure from recent baseline and recurring patterns.

**If root cause cannot be determined from events, traces, and metrics:**
Do not query logs. Instead, tell the user:
*"Root cause could not be conclusively determined from available signals. To investigate further, query logs manually for [affected service/entity] between [queryFrom] and [queryTo]. Focus on ERROR and WARN level entries."*
