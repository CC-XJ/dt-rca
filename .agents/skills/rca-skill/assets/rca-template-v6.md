<!--
Read ../references/doc_format.md before writing.

The following notes are instructions for the AI only.
Do NOT include any HTML comments in the generated report.
-->

<!-- *Before authoring this report:** Read [`doc_format.md`](../references/doc_format.md) in full.
> It defines all URL templates, placeholder substitution rules, formatting constraints,
> entity display conventions, and trace analysis rules.
> Do not proceed without consulting it - no rules are reproduced here. -->

---

# Root Cause Analysis - Problem [Display ID: P-XXXXXXX]

Time of Analysis (Date and Time):

---

## 1. Problem Overview

<!-- Use this section to capture incident metadata and the immediate problem context in a compact summary. Include the problem ID, severity, status, timeline, type, affected services/endpoints, detection source, Davis AI suggestion, and recurrence classification. -->

| Field | Value |
|-------|-------|
| Problem display ID | P-XXXXXXX |
| Severity | |
| Status | Active / Resolved |
| Onset time (UTC+8) | |
| Resolution time (UTC+8) | - leave blank if still active |
| Duration | |
| Problem type (classified) | response-time / failure-rate / cpu-saturation / memory-saturation / disk-space / multi-service |
| Affected service(s) | |
| Primary endpoint(s) | |
| Initial detection source | Davis AI / Alert / Manual |
| Davis AI root cause suggestion | |
| Recurrence classification | Recurring true issue / Likely alert noise / Inconclusive recurring pattern / No recurrence detected |

**Problem link:** [View in Dynatrace](https://cco92951.apps.dynatrace.com/ui/apps/dynatrace.davis.problems/problem/<event-id>)

---

\newpage

## 2. Root Cause

<!-- Explain the most likely root cause with a precise component, operation, query, or event name. Present a chronological evidence chain from the first abnormal signal through downstream symptoms to the confirmation point. Include direct impact evidence and keep any quoted query/text messages fully intact. -->

<!-- > **Full message rule:** Any `db.query.text`, `url.query`, or exception message appearing anywhere in this section must be reproduced **in full** - never truncated, summarised, or abbreviated with `...`.  Shortened forms such as `SELECT ... FROM ...` or `[UnionAll2]` are not acceptable. This applies only to `## 2. Root Cause`; any other sections may be truncated, summarised, or abbreviated. -->

**Primary cause:**

<!-- > Name the specific component, operation, query, or event - not a category.
> For response-time: name the slow query or procedure.
> For failure-rate: name the specific error and failing operation.
> For CPU/memory: name the specific process and mechanism.
> For disk: name the specific volume, growth mechanism, and time-to-full.
> For multi-service: name the origin entity and propagation path. -->

**Causal chain:**

<!-- Write this as a chronological evidence chain. Start with the earliest trigger or first abnormal signal, then list each downstream symptom or dependency effect in time order, and end with the evidence that confirms the root-cause entity. When read top to bottom, the chain should make the reasoning path obvious. -->

<!--  Scope rule: every item in the causal chain must be directly attributable to the root-cause entity or one of its immediate dependencies. Do not include unrelated services, callers, or span labels unless you have already established a topology or causal link to the root-cause entity. -->

1. [Earliest trigger / first abnormal signal - the specific initiating event or condition, with timestamp. If an exception message, `db.query.text`, or `url.query` is referenced here, reproduce it in full. This must be the first observed anomaly in the timeline.]

2. [Follow-on symptom / dependency effect - what changed next in the monitoring data, and how it connects to item 1.]

3. [Root-cause confirmation point - the entity, operation, or event that closes the chain and supports the final root cause conclusion, with timestamp.]

**Impacts:**

-

---

\newpage

## 3. Recommended Actions

<!-- List specific, actionable follow-up work tied directly to the identified root cause. Each recommendation should name the exact entity/component, explain why it is needed, and avoid vague or generic advice. -->
<!--  Recommendations must be specific and actionable - tied directly to the root cause identified in Section 2.
 Do not include generic advice. Every item must name the specific entity, query, process, or configuration to act on.
 If a recommendation cannot be made due to insufficient evidence, state why explicitly rather than leaving the row blank. -->

| No | Recommendation | Reason | Target entity/component |
|----|----------------|--------|-------------------------|
|    |                |        |                         |
