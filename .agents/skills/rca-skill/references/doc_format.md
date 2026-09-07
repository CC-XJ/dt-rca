# RCA Template — Formatting Rules & Configuration

> This file defines all authoring rules, formatting constraints, URL templates, and metadata
> conventions for the RCA template (`rca-template-v6.md`). Edit this file to update any rule
> that applies globally. The v6 template uses a three-section report structure:
> `Problem Overview`, `Root Cause`, and `Recommended Actions`.

---

## 1. Environment Configuration

### Environment ID

| Key | Value |
|-----|-------|
| `env_id` | `cco92951` |
| `base_url` | `https://cco92951.apps.dynatrace.com` |

---

## 2. URL Templates

> **Always substitute `{env_id}` before constructing any link.**
> Replace `{env_id}` with `cco92951` in all URL templates before constructing any link.

| Name | URL Pattern |
|------|-------------|
| `problem-page` | `https://cco92951.apps.dynatrace.com/ui/apps/dynatrace.davis.problems/problem/<event-id>` |
| `problem-page-with-filters` | `https://cco92951.apps.dynatrace.com/ui/apps/dynatrace.davis.problems/problem/<event-id>?from=now%28%29-7d&to=now%28%29&filters=ID+%3D+P-<display-id>` |
| `distributed-traces` | `https://cco92951.apps.dynatrace.com/ui/apps/dynatrace.distributedtracing/explorer?filter=trace.id+%3D+<trace.id>&tf=<startISO>%3B<endISO>` |
| `service-detail` | `https://cco92951.apps.dynatrace.com/ui/apps/dynatrace.services/explorer/services?tf=<startISO>%3B<endISO>&detailsId=<SERVICE-ID>&problemId=<event-id>` |
| `service-events` | `https://cco92951.apps.dynatrace.com/ui/apps/dynatrace.services/explorer/services?tf=<startISO>%3B<endISO>&detailsId=<SERVICE-ID>&problemId=<event-id>&perspective=performance&sort=healthIndicators%3Adescending%3BcustomAlerts%3Adescending&detailsTab=events` |
| `host-metrics` | `https://cco92951.apps.dynatrace.com/ui/apps/dynatrace.infraops/explorer/Hosts?tf=<startISO>%3B<endISO>&problemId=<event-id>&fullPageId=<HOST-ID>` |
| `host-events` | `https://cco92951.apps.dynatrace.com/ui/apps/dynatrace.infraops/explorer/Hosts?perspective=Health&sort=healthIndicators%3Adescending&detailsId=<HOST-ID>&detailsTab=Events&tf=<startISO>%3B<endISO>` |
| `process-metrics` | `https://cco92951.apps.dynatrace.com/ui/apps/dynatrace.infraops/explorer/Processes?tf=<startISO>%3B<endISO>&problemId=<event-id>&fullPageId=<PROCESS_GROUP_INSTANCE-ID>` |

### Query String Format

> Two timeframe formats — do not mix them:

| App | Format |
|-----|--------|
| Problem detail page | `?from=<startISO>&to=<endISO>` — separate params, colons encoded as `%3A` |
| All explorer apps | `?tf=<startISO>%3B<endISO>` — single param, semicolon encoded as `%3B`, colons as `%3A` |

### URL Construction Rules

- **Substitute `cco92951` before use** in all URL templates.
- **Never include secrets.** This file contains non-sensitive environment identifiers only.
- **Scope all links to problem context.** Use the problem/event ID and its timeframe to populate all placeholders.
- **All URLs must be fully resolved** — no placeholder tokens (angle brackets) may remain in any URL in the final report.

---

## 3. Placeholder Reference

| Placeholder | Description |
|---|---|
| `<event-id>` | Full event/problem ID from `dt.davis.event_id` (e.g. `-7619925669591199870_1778564950362V2`) |
| `<display-id>` | Short display problem ID (e.g. `P-12345`) |
| `<SERVICE-ID>` | Dynatrace service entity leaf ID |
| `<HOST-ID>` | Dynatrace host entity leaf ID |
| `<PROCESS_GROUP_INSTANCE-ID>` | Dynatrace process group instance entity leaf ID |
| `<startISO>` | Investigation window start in ISO 8601 format, colons encoded as `%3A` in URLs |
| `<endISO>` | Investigation window end in ISO 8601 format, colons encoded as `%3A` in URLs |

---

## 4. Problem Identifier Rules

> Two problem identifiers — do not confuse them:

| Identifier | Source field | Where to use |
|------------|-------------|--------------|
| Display ID (e.g. `P-12345`) | `display_id` | Report text and headings only |
| Event ID (e.g. `-761992...V2`) | `dt.davis.event_id` | URL construction only (problem deep link) |

---

## 5a. Entity Display Rules

- **Always display entity name followed by its ID in brackets.**
  - Correct: `KBDOAPPS05 (HOST-1B329CASDF08)`
  - Wrong: `HOST-1B329CASDF08` (ID alone, no name)
- Never display an entity ID without its human-readable name.

## 5b. Entity ID Rules — Group and Leaf IDs

Always include **both** the group-level ID (for context) and the leaf-level ID (for deep links).

| Entity type | Group ID (display only) | Leaf ID (required for links) |
|-------------|------------------------|------------------------------|
| Hosts | `HOST_GROUP-*` | `HOST-*` |
| Processes | `PROCESS_GROUP-*` | `PROCESS_GROUP_INSTANCE-*` |

- Deep links must always use the leaf ID.
- If the problem payload returns only group-level IDs, resolve to leaf IDs before constructing any link — retain the group ID in the report.
- `HOST_GROUP-*` → `HOST-*` via Smartscape/entity query scoped to the incident window.
- `PROCESS_GROUP-*` → `PROCESS_GROUP_INSTANCE-*` via the same method.
- Before querying any ID-related fields (`trace.id`, `span.id`, etc.), use `toUid()` to convert display IDs to Dynatrace UID format.

---

## 6. Formatting Rules

### 6.1 Line Breaks & Whitespace

- After each metadata field in the header block, output a blank line between each item so they render on separate lines.
- In the causal chain, each step should be on a new line with a blank line between each item.
- In all bullet-point lists, place a blank line between each bullet so they do not collapse.
- In table cells, do not use line breaks — keep each cell to a single line.
- Between every section and subsection heading, insert one blank line above and below.
- Do not compress the output — readability takes priority over brevity.

### 6.2 Sections & Skipping

- Only populate subsections relevant to the problem type.
- Do not add top-level sections beyond the three sections defined in `rca-template-v6.md`.
- In `## 2. Root Cause`, write the causal chain as a chronological reasoning path: earliest trigger, progression, then confirmation.
- For each subsection that does not apply, write one line explaining why it was skipped.
- Never leave a section header with no content beneath it.

### 6.3 Trace Analysis

- There is no standalone trace section in v6. If distributed tracing is instrumented, include trace evidence inside `## 2. Root Cause` only when it materially supports the conclusion; otherwise state why it was skipped.
- Cap trace analysis at **3 traces**, in this fixed order:
  - **Trace 1 — Root Cause Trace:** The trace that directly exhibits the failure mechanism. Skip and state why if root cause is infrastructure-level.
  - **Trace 2 — Downstream Impact Trace:** A trace from a service downstream of the root cause.
  - **Trace 3 — Downstream Impact Trace:** A second downstream trace, distinct from Trace 2.
- If fewer than 3 traces are available, populate as many as exist and note what is missing and why.
- Flag spans with `status == ERROR` or HTTP ≥ 500.
- Identify and label the **first error span** — that is the error origin. State its sequence number, span name, service, and timestamp.
- Include `db.query.text` and `url.path` inline under the relevant span row. Record each unique query once only.
- Include `url.query` where available.

### 6.4 Hypotheses & Evidence

- There is no standalone hypotheses section in v6. Treat hypotheses as internal investigation notes. Record every hypothesis considered during investigation, including ruled-out ones, and reflect the important alternatives in `## 2. Root Cause` when relevant.
- Each hypothesis requires a specific signal reference: event timestamp / metric reading / trace ID + span name.
- A hypothesis without evidence must be marked as **Speculation**.
- Minimum hypotheses per problem type:
  - Response-time: DB slowness, downstream dependency, deployment change, traffic spike.
  - Failure-rate: Deployment regression, downstream dependency failure, specific endpoint defect, infrastructure failure.
  - CPU-saturation: Traffic spike, deployment regression, runaway process, scheduled job, alert noise.
  - Memory-saturation: Memory leak, GC failure, workload growth, deployment regression, alert noise.
  - Disk-space: Log accumulation, data growth, deployment-triggered write increase, core dumps, alert noise.
  - Multi-service: Shared infrastructure failure, deployment on origin service, dependency chain failure, independent coincident failures.

### 6.5 Root Cause & Evidence Standards

- Name the specific component, operation, query, or event — do not use category-level language without naming the specific mechanism.
- Every root-cause claim must cite at least two independent signal types with timestamps.
- Distinguish chronic baseline conditions from incident-specific triggers. A metric that is high in the current problem but similar in the previous 3 same-time windows must not be stated as root cause by itself.
- When recurrence is detected, the root-cause section must explicitly state the recurrence classification with evidence.
- Apply confidence labels:
  - **Confirmed** — earliest signal + mechanism evidenced across ≥2 independent signal types with timestamps.
  - **Probable** — consistent with evidence but mechanism not fully traced.
  - **Insufficient** — symptom identified, cause unclear.

### 6.6 Page Breaks

Insert a hard page break (`\newpage`) **before each of the following headings**:

- `## 2. Root Cause`
- `## 3. Recommended Actions`

Do not place page breaks elsewhere unless the template is updated to add new top-level sections.

---

## 7. Metrics Baseline Definition

> Scoped to the investigation window. **Baseline** = the pre-incident window immediately before onset.

For RCA decisions, baseline assessment uses three comparison windows:

- The same time-of-day window over the **previous 3 days**.
- Similar Davis problems/events on the same entities over the **previous 7 days**.

If the current signal is not materially different from those comparison windows, treat it as chronic background unless another signal clearly separates this incident.

**Materiality threshold:** A metric reading within 20% of the previous 3-day average at the same time of day is not materially different. A reading >20% above is a candidate signal — but must still be validated against the 14-day recurrence check.

---

## 8. Change Event Assessment Rules

- Include events within investigation window **±30 minutes** of problem onset.
- For memory-saturation and disk-space problems, compute ±30 minutes relative to the **trend start time**, not the alert time.
- A change event preceding `problemStart` is a primary cause candidate.
- Absence of change events is also a finding — note it explicitly: *"No deployment or configuration change events detected within ±30 minutes of problem onset."*

---

## 9. Problem-Type Routing

The model must classify the problem type before beginning investigation. Use the following mapping:

| Problem type | Trigger keywords / event names | Playbook |
|---|---|---|
| `response-time` | Response time degradation, slow requests, `RESPONSE_TIME_DEGRADED` | `playbook-response-time.md` |
| `failure-rate` | Failure rate increase, error spike, HTTP 5xx surge, `FAILURE_RATE_INCREASED` | `playbook-failure-rate.md` |
| `cpu-saturation` | CPU saturation, high CPU, `CPU_SATURATED` | `playbook-cpu-saturation.md` |
| `memory-saturation` | Memory saturation, GC overhead, heap exhaustion, `MEMORY_RESOURCES_EXHAUSTED` | `playbook-memory-saturation.md` |
| `disk-space` | Low disk space, disk full, `DISK_LOW` | `playbook-disk-space.md` |
| `multi-service` | Multiple services affected, cascading failure, propagation | `playbook-multi-service.md` |

If a problem matches more than one type, classify as `multi-service` and load both the origin-type playbook and `playbook-multi-service.md`.

---

## 10. Root Cause Evidence Rules

The `Root Cause` section in `rca-template-v6.md` is mandatory. Rules:

- It must be completed using evidence gathered before writing the final report.
- Every root-cause claim must be directly supported by the collected telemetry and the chronology in the causal chain.
- If a signal type cannot be queried, state the reason explicitly in the narrative or in the relevant table row.
- If the evidence is incomplete, downgrade the root cause confidence level accordingly and state what was missing.

---

## 11. Not-Available Audit Rules

After the report is drafted, perform a final audit:

- For every field marked `Not available`, re-query all available sources before accepting the absence.
- Sources to check: problem events, Davis events, service metrics, host metrics, process metrics, spans, traces.
- If after re-querying the data is still not found, retain `Not available` and add a note stating which sources were checked.
- Never use `Not available` as a placeholder to avoid investigation — it must represent genuinely absent data confirmed by a query attempt.

---

## 12. DQL Query Standards — Token Efficiency (Mandatory)

Every DQL query executed during investigation MUST follow these rules.
Violating them is the single largest source of token waste in this skill.

### 12.1 Always project only the fields you need

Never run a bare `fetch` without a `| fields` clause.
The Grail response includes schema type mappings for every field returned — each extra field adds ~200 chars of schema overhead even before the data rows.

**Wrong:**
```dql
fetch spans, from:"...", to:"..."
| filter dt.entity.service == "SERVICE-XXX"
```

**Right:**
```dql
fetch spans, from:"...", to:"..."
| filter dt.entity.service == "SERVICE-XXX"
| fields timestamp, trace.id, span.name, duration, span.status_code, db.query.text, url.path
```

Required fields per query type:

| Query type | Required fields |
|------------|----------------|
| spans (error) | `timestamp, trace.id, span.id, span.name, dt.entity.service, duration, span.status_code, http.response.status_code, db.query.text, url.path, url.query` |
| spans (slow) | `timestamp, trace.id, span.name, dt.entity.service, duration, db.query.text, url.path, url.query` |
| events | `timestamp, event.id, event.name, event.type, event.kind, event.category, dt.entity.host, dt.entity.service` |
| dt.davis.problems (recurrence) | `display_id, event.name, event.start, event.end, event.status, affected_entity_ids` |
| timeseries | Only the specific metric fields needed — never `*` |

### 12.2 Always add a `limit` to fetch queries

Every `fetch` query must end with `| limit N` where N is the minimum needed for the analysis:

| Query purpose | Limit |
|--------------|-------|
| Trace selection (error/slow) | `limit 20` — model selects 3 from this set |
| Event timeline | `limit 50` |
| Recurrence check (14d problems) | `limit 30` |
| DB procedure ranking | `limit 10` — only top 10 needed |
| Span detail for a specific trace | `limit 50` |

**Never run an unbounded fetch.** An unbounded `fetch events` returned 218,881 chars (~54,000 tokens) in this session. With `| fields` + `| limit 50`, the same query returns ~3,000 chars.

### 12.3 Use `summarize` before `fetch` for ranking queries

For DB procedure ranking and event counts, always aggregate server-side rather than fetching raw rows and counting in context.

**Wrong (fetches all rows):**
```dql
fetch spans, from:"...", to:"..."
| filter isNotNull(db.query.text)
| fields db.query.text, duration
```

**Right (aggregates server-side):**
```dql
fetch spans, from:"...", to:"..."
| filter isNotNull(db.query.text)
| summarize max_duration = max(duration), avg_duration = avg(duration), call_count = count(), by:{db.query.text}
| sort max_duration desc
| limit 5
```

### 12.4 Never repeat the same query with minor variations

If a query returns useful data, extract everything needed from it in one pass. Do not re-run the same `fetch spans` with a different `fields` clause — instead, include all required fields in the first query.

The session analysed showed the same spans query repeated **10 times** against the same timeframe. This added ~40,000 tokens to the context for no additional information gain.

If you need different aggregations of the same data, chain them with `| summarize` in a single query rather than issuing multiple queries.

### 12.5 Strip query metadata from your analysis

The Grail response always prepends a `Query metadata:` JSON block with `canonicalQuery`, `scannedRecords`, `scannedBytes`, `executionTimeMilliseconds`, and type mapping schemas. **Do not reproduce this metadata in your analysis or report.** Extract the data rows only. The metadata block alone can be 2,000–5,000 chars per query response.

### 12.6 For recurrence checks, use a summarise-first pattern

**Wrong:**
```dql
fetch dt.davis.problems, from:toTimestamp("..."), to:toTimestamp("...")
| filter event.name == "Multiple service problems"
| fields event.id, display_id, event.name, event.start, event.end, event.status, affected_entity_ids, root_cause_entity_id
| sort event.start asc
```
(Returns full payload for every matching problem — 96,900 chars in session.)

**Right:**
```dql
fetch dt.davis.problems, from:toTimestamp("..."), to:toTimestamp("...")
| filter event.name == "Multiple service problems"
| filter display_id != "P-XXXXXXX"
| summarize count = count(), first_seen = min(event.start), last_seen = max(event.start), by:{event.name, event.status}
| limit 10
```
Then follow up with a targeted fetch only if you need specific problem IDs.
