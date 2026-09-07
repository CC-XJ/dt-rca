# Dynatrace RCA Skill

This project provides a telemetry-backed Root Cause Analysis (RCA) workflow for Dynatrace problems. The primary capability is `rca-skill`: it retrieves a Dynatrace problem, investigates the affected services and infrastructure with Dynatrace MCP tools, produces a structured RCA report, converts the report to Word, and can notify stakeholders by email.

The supporting `notify-skill` sends the completed report and RCA summary through Gmail SMTP.

## What This Project Does

Given a Dynatrace problem ID such as `P-26083227`, the RCA workflow:

1. Retrieves the target problem and checks for recurrence over the previous seven days.
2. Classifies the problem and loads only the matching investigation playbook.
3. Queries Dynatrace telemetry through MCP, including metrics, logs, services, hosts, traces, and spans as required.
4. Separates incident-specific evidence from chronic baseline conditions.
5. Fills the local RCA template with evidence-based findings and Malaysia Time timestamps (`UTC+8`).
6. Saves the Markdown report as `RCA-report-<problem-id>.md`.
7. Converts the Markdown report to `RCA-report-<problem-id>.docx`.
8. Prints a concise root-cause and recommended-actions summary.
9. Optionally emails the summary with the generated report attached.

The workflow is designed to keep the causal chain tied to the affected entity and to avoid unsupported conclusions.

## Repository Layout

```text
.
├── .agents/skills/rca-skill/       RCA workflow, playbooks, templates, and scripts
├── .agents/skills/notify-skill/    Gmail notification instructions and script
├── .claude/skills/                 Claude-compatible copy of the skills
├── skills-lock.json                Pinned Dynatrace skill sources and hashes
├── venv/                           Python environment for report conversion
├── RCA-report-*.md                 Generated RCA reports
└── RCA-report-*.docx               Generated Word reports
```

The RCA skill also depends on the Dynatrace DQL essentials skill during investigation. Other Dynatrace skills may be loaded by the selected playbook when the problem requires them.

## Prerequisites

- VS Code or another supported agent host with skill support.
- Access to a Dynatrace environment containing the problem and its telemetry.
- A configured Dynatrace MCP server with permission to query problems and telemetry.
- Python 3 and a virtual environment at `venv/` for Markdown-to-Word conversion.
- Gmail SMTP credentials configured for `notify-skill` if email delivery is required.

Do not put Dynatrace tokens, SMTP passwords, or other secrets in this repository. Configure them through the MCP host, environment variables, or the credential mechanism used by your agent environment.

## Set Up the Dynatrace Skills

### Option 1: Use the skills already in this project

This repository already contains the skills in both supported locations:

- `.agents/skills/` for agent environments that use the `.agents` convention.
- `.claude/skills/` for Claude-compatible environments.

Open the repository as the workspace in your agent host. The host should discover the skills from the corresponding directory. `skills-lock.json` records the upstream Dynatrace skill source and content hashes used by this project.

### Option 2: Install or refresh the upstream Dynatrace skills

For a new workspace, install the skills from the Dynatrace skills repository using the skill-installation mechanism provided by your agent host. The upstream source recorded by this project is:

```text
dynatrace/dynatrace-for-ai
```

After installation, verify that the workspace contains the relevant skill entry points:

```text
.agents/skills/rca-skill/SKILL.md
.agents/skills/notify-skill/SKILL.md
.agents/skills/dt-dql-essentials/SKILL.md
```

If the host supports lock-file validation, use `skills-lock.json` to confirm that the installed Dynatrace skills match the pinned source and hashes. Keep the RCA skill and its complete `assets/`, `references/`, and `scripts/` directories together; copying only `SKILL.md` is not sufficient.

### Configure Dynatrace MCP

The RCA workflow must use Dynatrace MCP tools for problem retrieval, discovery, DQL execution, and telemetry analysis. Configure the Dynatrace MCP server in the agent host according to that host's MCP configuration format, then authenticate it against the intended Dynatrace environment.

Before running an RCA, verify that the MCP server can:

- Query open problems and retrieve a problem by ID.
- Execute scoped DQL queries.
- Read the entities, metrics, logs, traces, and spans needed by the selected playbook.

The RCA skill explicitly does not use `dtctl` for query or discovery.

### Prepare the Python environment

From the repository root, create or activate the virtual environment used by the report conversion step and install the dependencies required by `md_to_word.py`:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Install the packages required by `md_to_word.py` if they are not already present in the environment. The exact package list should follow the script and the project lock or requirements used by your environment.

## Run an RCA

Ask the agent to perform an RCA for a specific Dynatrace problem ID, for example:

```text
Perform an RCA for Dynatrace problem P-26083227.
```

The agent should follow the staged workflow in `.agents/skills/rca-skill/SKILL.md`:

- Problem lookup and recurrence check use narrowly scoped calls.
- Only the playbook matching the classified problem type is loaded.
- DQL queries are scoped to the investigation window and affected entities.
- Queries include explicit `fields` and `limit` clauses.
- Span investigations aggregate database queries and exception data before projecting details.
- The final `Not available` check is completed before the report is considered finished.

### Supported problem types

The RCA skill currently routes to playbooks for:

- CPU saturation
- Memory saturation
- Low disk space
- Failure-rate increases
- Response-time degradation
- Multi-service or cascading problems

## Outputs

For problem ID `P-26083227`, a successful run produces:

```text
RCA-report-P-26083227.md
RCA-report-P-26083227.docx
```

The Markdown report follows the local RCA template. The Word document is generated with:

```powershell
.\venv\Scripts\Activate.ps1
python .agents\skills\rca-skill\scripts\md_to_word.py RCA-report-P-26083227.md
```

The report should contain no unresolved template placeholders. Values that remain genuinely unavailable after the final source check are recorded as `Not available`.

## Send the RCA by Email

`notify-skill` uses `send_email.py` and requires a recipient, subject, and body. Attach the generated report when distributing the RCA:

```powershell
python .agents\skills\notify-skill\scripts\send_email.py `
  --to "recipient@example.com" `
  --subject "RCA completed for P-26083227" `
  --body "Root Cause: <validated cause>\n\nRecommended Actions:\n- <action 1>\n- <action 2>" `
  --attach RCA-report-P-26083227.docx
```

Optional flags include `--cc`, `--bcc`, and multiple `--attach` values. Gmail limits each attachment to 20 MB and the complete message to approximately 25 MB.

Email delivery requires the SMTP configuration expected by `send_email.py`. Keep SMTP credentials outside the repository and test delivery with a non-production recipient first.

## Operational Rules

- Use Dynatrace MCP tools for all problem retrieval, discovery, and query work.
- Do not use `dtctl` for RCA investigation.
- Use the full Dynatrace event ID in problem deep links; use the display problem ID in report text.
- Convert entity IDs with `toUid()` before using them in ID-based DQL filters.
- Include service name, service entity ID, and the relevant database namespace when querying spans for a service.
- Convert report timestamps from UTC to `YYYY-MM-DD HH:mm:ss (UTC+8)`.
- Do not add sections outside the local RCA template.
- Do not claim a root cause without supporting telemetry.
- Do not commit credentials or generated sensitive reports unless the project policy allows it.

## Troubleshooting

**The agent cannot find the RCA skill**

Confirm that the workspace is opened at the repository root and that `.agents/skills/rca-skill/SKILL.md` or `.claude/skills/rca-skill/SKILL.md` exists. Reinstall or refresh the skills if the directory is incomplete.

**Problem retrieval works but telemetry queries fail**

Check Dynatrace MCP authentication, tenant permissions, the investigation time window, and whether the required DQL tools are available. The RCA workflow requires `dt-dql-essentials` during investigation.

**Word conversion fails**

Activate `venv`, confirm Python dependencies required by `.agents/skills/rca-skill/scripts/md_to_word.py` are installed, and rerun the conversion command from the repository root.

**Email sending fails**

Check the SMTP configuration used by `send_email.py`, validate the recipient and attachment path, and confirm the attachment is below Gmail's size limit. Never troubleshoot by placing credentials in the command line or source files.

## Related Skills

- `rca-skill`: primary Dynatrace problem investigation and report generation workflow.
- `notify-skill`: email delivery of the RCA summary and report.
- `dt-dql-essentials`: DQL guidance required by the RCA investigation.
- Additional Dynatrace observability skills: load only when the problem or playbook requires them.
