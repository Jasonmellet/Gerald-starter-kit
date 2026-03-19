---
name: gmail-email-ops
description: Send and troubleshoot operational emails through Gerald's Gmail integration, including daily digests, meeting summaries, and custom messages. Use when the user asks Gerald to email updates, resend reports, test Gmail auth, or debug email send failures.
---

# Gmail Email Ops

## Use when

- User asks Gerald to send an email
- User asks for daily digest email behavior
- User asks to send meeting summary emails
- Email sending fails and needs troubleshooting

## Required reads

- `tools/gmail_client.py`
- `tools/send_email.py`
- `tools/daily_digest.py`

## Core commands

Run from repo root:

- Send meeting summary:
  - `python3 tools/send_email.py --meeting <summary_file> --to <email>`
- Send custom message:
  - `python3 tools/send_email.py --subject "<subject>" --body "<body>" --to <email>`
- Send from file body:
  - `python3 tools/send_email.py --subject "<subject>" --file <path> --to <email>`
- Daily digest:
  - `python3 tools/daily_digest.py`
- Daily digest dry test:
  - `python3 tools/daily_digest.py --test`

## Authentication behavior

1. Gmail credentials file must exist:
   - `credentials/gmail-credentials.json`
2. Token file path:
   - `credentials/gmail-token.pickle`
3. First send with `gmail.send` scope may trigger OAuth consent in browser.

## Troubleshooting checklist

1. Verify required files exist:
   - credentials JSON and token file paths
2. Re-auth if send permission is missing:
   - run a send command to trigger `authenticate_with_send()`
3. Check scheduler if digest is expected automatically:
   - `tools/scheduler.py` and cron entries
4. Confirm digest dedupe state:
   - `logs/daily_digest_state.json` controls "already sent today"

## Output format

```markdown
# Email Ops Report

- Request: <digest / meeting summary / custom email / troubleshoot>
- Result: <ok / partial / fail>
- Recipient: <email>

## Evidence
- Command run: <command>
- Auth status: <ok / failed / re-consent needed>
- Send result: <message id or error>

## Next step
- <single recommended action>
```

## Guardrails

- Never claim an email was sent without command success output.
- Avoid sharing secrets or raw credential values in responses.
