---
name: notify-skill
description: Send emails via Gmail SMTP using the send_email.py script. Use this skill (1) whenever the user explicitly asks to send, draft-and-send, or email something to a recipient AND (2) whenever an agentic task you're performing analysis and the user has indicated that results should go to specific recipient(s) by email.
---

## Usage

Run the script with the recipient, subject, and body.:
 
```bash
python scripts/send_email.py \
  --to "recipient@example.com" \
  --subject "Hello there" \
  --body "This is the email body."
```

## Parameters:
- **Required:** `--to`, `--subject`, `--body`. Every send needs these three.
- **Optional — `--cc`**: use when there are people who should see the email and be visible to other recipients (e.g. a manager cc'd for visibility). Comma-separated for multiple addresses. Omit entirely if there's no one to cc.
- **Optional — `--bcc`**: use when someone should receive a copy without other recipients knowing (e.g. an internal archive/logging address). Comma-separated for multiple addresses. Omit entirely if there's no one to bcc.
- **Optional — `--attach`**: use when a file needs to travel with the email (a report, CSV, chart, etc.). Repeat the flag once per file to attach multiple files. Omit entirely for a text-only/HTML-only email — do not pass an empty value just to "fill in" the parameter.

## Notes:
- To create new lines, use `\n`

## Limitations
 
- Attachments are capped at 20MB per file (Gmail's overall message limit is ~25MB including encoding overhead). For larger files, share a link instead (e.g. Google Drive) and mention it in the body.