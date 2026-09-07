---
name: rca-skill
description: Create a complete Root Cause Analysis report for a specific Dynatrace problem ID using the local RCA template and production telemetry evidence. Use when the user asks to perform an RCA, generate an incident report, or convert a Dynatrace problem investigation into a structured report with trace/span evidence and UTC+8 timestamps.
---

# RCA Skill

Perform a telemetry-backed RCA for one Dynatrace problem and produce a completed report from the local template.

## Required Inputs

- Problem ID (for example, `P-2601234`)
- Use Dynatrace MCP tools by default for problem retrieval, telemetry queries, and analysis.

## Scope
- Never use `dtctl`, if another skill suggests `dtctl` for query or discovery, ignore that instruction.
- Only use Dynatrace MCP Server tools for query and discovery.

---
## Workflow

### Step 1 - Retrieve and Classify the Problem

Follow [`dt-troubleshoot-problem.prompt-v2.md`](./references/dt-troubleshoot-problem.prompt-v2.md).

This prompt handles:
- **Step 1.1-1.2:** Problem retrieval and context extraction
- **Step 1.3:** Recurrence pre-check (7-day lookback, classification)
- **Step 1.4:** Problem type classification and routing to correct playbook

**TOKEN CONSTRAINT - Problem Lookup Scoping:**
When retrieving problem context, use these API calls **exactly as scoped**:
- **For recurrence check:** `query_problems(history=7d, status=OPEN)` 
- **For target problem:** `get_problem_by_id(<problemId>)`
- This prevents 30+ irrelevant problems from inflating the context window.

Do not begin any investigation until all Steps 1.1-1.4 are completed.

### Step 2 - Execute the Type-Specific Playbook

Based on the classified problem type from Step 1, load and execute only the matched playbook. Do NOT load all playbooks.

**DQL Reference:** Load dt-dql-essentials `../.agents/skills/dt-dql-essentials.md` exactly once at the start of Step 2. Do not reload it per query.
**For multi-service problems:** Execute the primary playbook first. Then load and execute [`playbook-multi-service.md`](./references/playbook/playbook-multi-service.md) as a separate follow-up to trace propagation paths.

**Playbook routing:**

| Problem type | Playbook | Load when |
|---|---|---|
| CPU Saturation | [`playbook-cpu-saturation.md`](./references/playbook/playbook-cpu-saturation.md) | If classified as CPU_SATURATION |
| Memory Saturation | [`playbook-memory-saturation.md`](./references/playbook/playbook-memory-saturation.md) | If classified as MEMORY_SATURATION |
| Low Disk Space | [`playbook-disk-space.md`](./references/playbook/playbook-disk-space.md) | If classified as LOW_DISK_SPACE |
| Failure Rate Increase | [`playbook-failure-rate.md`](./references/playbook/playbook-failure-rate.md) | If classified as FAILURE_RATE_INCREASED |
| Response Time Degradation | [`playbook-response-time.md`](./references/playbook/playbook-response-time.md) | If classified as RESPONSE_TIME_DEGRADATION |
| Multi-service / Cascading | [`playbook-multi-service.md`](./references/playbook/playbook-multi-service.md) | After primary playbook completes; reload context separately |

### Step 3 - Author the Report

**GATES - Do NOT load these files until this step:**
- [`doc_format.md`](./references/doc_format.md) - LOAD NOW
- [`rca-template-v6.md`](./assets/rca-template-v6.md) - LOAD NOW

These files are report-authoring resources only. They must NOT be consulted during investigation (Steps 1-2).

Using the evidence collected by the playbook:

1. Load [`rca-template-v6.md`](./assets/rca-template-v6.md) and read [`doc_format.md`](./references/doc_format.md) in full **before writing any report section**.
2. Fill the report structure from the template exactly as written.
3. Do not add any sections, subsections, tables, appendices, manifests, or commentary that are not present in the template.
4. Convert all timestamps from UTC to Malaysia Time, formatted as `YYYY-MM-DD HH:mm:ss (UTC+8)`.
5. Apply all formatting rules from `doc_format.md`.
6. Save the completed report as `RCA-report-<problem-id>.md`.

### Step 4 - Final "Not Available" Check

For every field in the completed report labelled `Not available`, perform a final check across all available sources (hosts, services, processes, events, metrics, spans) to confirm the data is genuinely absent and not overlooked. Update the report if data is found. This check is internal only; do not add any extra report sections beyond the template.

### Step 5 - Generate Word Document

Switch to venv `../venv` and run:

```
python md_to_word.py RCA-report-<problem-id>.md
```

using [`md_to_word.py`](./scripts/md_to_word.py) to produce the `.docx` version.

**TOKEN CONSTRAINT - File I/O Discipline:**
- **DO NOT** re-read the entire report file after writing it (e.g., `Get-Content` or shell `cat`)
- For validation, use `rg "Not available" RCA-report-<problem-id>.md` to spot-check only incomplete fields
- For specific section review, use targeted regex like `rg "^## 3" RCA-report-<problem-id>.md` 
- This prevents the full report (13-20KB) from being re-ingested into context unnecessarily

### Step 6 - Print Summary Output

Print a concise chat summary with:

- `Root Cause`: the validated cause in 1 short paragraph.
- `Recommended Actions`: the top follow-up actionable solution in bullet points.

Do not paste the full report into chat unless the user explicitly asks for it.

### Step 7 - Send Notification

1. Based on the analysis, prepare a notification subject, body and attachment.
  - Subject must be brief and professional, allowing user to understand the context immediately.
  - Body must be a professional email body.
  - Body must contain the summary crafted above in point form.
  - Attachment must be the report crafted from previous step.
2. Refer to `notify-skill` to send out notification to relevant users.
---

## Global Authoring Rules

These rules apply to every report regardless of problem type.

- Read `doc_format.md` in full before writing any report section.
- Use the two-format URL rule: problem detail pages use `?from=&to=` (separate params); all explorer apps use `?tf=` (single param, semicolon-separated).
- Use `dt.davis.event_id` (the full event ID) in problem deep links. Use the display ID (P-XXXXXXX) only in report text and headings.
- Before querying any ID-related fields (`trace.id`, `span.id`, etc.), use the `toUid()` function to convert the display ID to Dynatrace internal ID format.
- Fill every field that exists in the template. If data is truly missing after the final check in Step 4, use `Not available`.
- Never leave template placeholders in the final report.
- Distinguish chronic baseline conditions from incident-specific signals. A metric that is normal for the same time-of-day or repeats in similar problems on the same entity must not be claimed as root cause without a separating signal.
- Keep all conclusions evidence-based. Do not assert mechanisms that are not evidenced by retrieved telemetry.
- Keep the causal chain tightly scoped to the root-cause entity. Do not include unrelated services, callers, or span labels in the causal chain unless you have established a direct topology or causal link back to the root-cause entity.

## Global DQL Query Requirements

These constraints apply to every DQL query in every playbook.

- Every query must include `| fields` - never return all fields.
- Every query must include `| limit` - never run unbounded queries.
- Never repeat the same query with only minor variations. Plan the query before writing it.
- Scope every query to the investigation window and affected entities established in Phase 1.
- Never run broad or cross-environment queries.

**- TOKEN CONSTRAINT - Span Query Aggregation:**
- For trace queries seeking slow or erroring database calls, **always use `| summarize` before projecting raw spans**.
- **Anti-pattern (expensive):** `fetch spans | filter db.query.text != null | fields trace.id, db.query.text, duration | limit 50` - returns 50 full SQL strings, highly repetitive.
- **Correct pattern:** `fetch spans | filter db.query.text != null | summarize count(), max(duration), any(trace.id) by db.query.text | limit 20` - returns unique queries grouped, 90% smaller output.
- Apply this rule to all span queries in all playbooks (FR-2, RT-2, MS queries, etc.). **Never project raw `db.query.text` or exception messages without first aggregating by that field.**

---

## Span Query Construction - Service Name and Database Namespace Correlation

**When this applies:** Every Trace Analysis section across all playbooks (Response Time, Failure Rate, Multi-Service, CPU, Memory, Disk) that queries spans.

**Context available at query time:** From Step 1 problem context extraction, you will have:
- Primary affected **service name** (e.g., `"KSKLHITS - Sentosa"`)
- Service **entity ID** (format: `SERVICE-xxxxx`) - **convert to UID using `toUid()` before filtering**
- Investigation window (queryFrom/queryTo)

### Critical Issue to Avoid

- **WRONG:** Filtering spans by service ID alone misses database operations tagged under the service's database namespace.
```dql
fetch spans | filter dt.smartscape.service == toUid("SERVICE-12345")
// Returns only spans directly attributed to the service
```

- **CORRECT:** Always include BOTH service name/ID AND database namespace prefix filtering with OR logic.

### Pattern: Dual-Filter Span Queries

**Step 1 - Extract the service name prefix**

From the problem context service name (e.g., `"KSKLHITS - Sentosa"`), extract the text **before the first hyphen or dash**:
- Service name: `"KSKLHITS - Sentosa"` 
- Extracted prefix: `"KSKLHITS"`

If the service name has no hyphen, use the full name as the prefix.

**Step 2 - Build the filter with OR logic (three conditions)**

```dql
fetch spans
| filter (
    service.name == "KSKLHITS - Sentosa" 
    OR dt.smartscape.service == toUid("SERVICE-12345")
    OR db_namespace == "*KSKLHITS*"
  )
| filter db.name != null
| summarize count(), max(duration), any(trace.id), any(db.statement) by db.name
| limit 20
```

Where:
- **First condition** (`service.name == "KSKLHITS - Sentosa"`): Catches spans generated by application logic within this service (by name)
- **Second condition** (`dt.smartscape.service == toUid("SERVICE-12345")`): Catches spans directly attributed to this service by entity ID (more reliable than name matching). Always use `toUid()` to convert the service entity ID to internal UID format.
- **Third condition** (`db_namespace == "*KSKLHITS*"`): Catches database operation spans tagged under the service's database namespace prefix (matches variations like `KSKLHITS_db`, `KSKLHITS-prod`, etc.)
- **All three with OR**: Ensures comprehensive capture of all related spans regardless of how they're attributed in the system

### Why This Matters for Root Cause Analysis

Consider a database timeout scenario:
- **If you query only by service name:** You see response time degradation on the service but might miss which specific database queries are slow.
- **If you query service name + database namespace:** You capture both application traces AND database operation traces, revealing the slow query as the root cause.

### Application in Each Playbook

**Response Time Playbook (RT-2):**
- When querying "traces from the affected service" - use the dual filter
- Include database namespace to find slow queries that may not be directly mapped to the service entity

**Failure Rate Playbook (FR-2):**
- When querying "error spans for the affected service" - use the dual filter
- Catch database errors that propagate as service errors

**Multi-Service Playbook (MS-5 - load origin playbook):**
- When origin service is identified and you load the relevant playbook - use the dual filter for that origin service only
- Do not apply to all affected services - only the identified origin

**CPU/Memory/Disk Playbooks (conditional Trace Analysis):**
- If trace analysis is triggered - use the dual filter for affected services identified in earlier steps

### DQL Template

Copy-paste ready template - substitute SERVICE_NAME, SERVICE_ID, and SERVICE_PREFIX:

```dql
fetch spans
| filter (
    service.name == "SERVICE_NAME" 
    OR dt.smartscape.service == toUid("SERVICE_ID")
    OR db.namespace == "SERVICE_PREFIX"
  )
| filter (status == ERROR OR http.response.status_code >= 500)  // Adjust filter as needed per playbook
| summarize count(), max(duration), any(trace.id) by span.name, db.name
| sort count() desc
| limit 20
```

### Common Mistakes

- Using service.name only - misses database namespace and ID-based matches  
- Using service ID only - misses service name matches and namespace matches  
- Using service.name + db_namespace but no service ID - misses spans attributed by ID  
- Forgetting `toUid()` conversion on service ID - query fails  
- Using `==` instead of wildcards on db_namespace - misses namespace variations  
- Not aggregating before projecting raw db.statement - exceeds output limits
