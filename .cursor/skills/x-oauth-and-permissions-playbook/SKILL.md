---
name: x-oauth-and-permissions-playbook
description: Configure and troubleshoot X OAuth callback flow, scopes, and app permissions for posting and DM operations. Use when the user reports X auth failures, callback mismatch errors, DM scope issues, or asks to set up OAuth tokens.
---

# X OAuth And Permissions Playbook

## Use when

- User asks to set up X OAuth callback flow
- OAuth shows "You weren't able to give access to the App"
- DM scopes or permissions are failing
- User needs tokens for post/reply/DM actions

## Required reads

- `X-CALLBACK-SETUP.md`
- `X-OAUTH-TROUBLESHOOTING.md`
- `docs/reference/x-api-manage-posts.md`

## Setup checklist

1. Callback server and tunnel/domain
   - Run callback server: `python3 tools/x_oauth_callback_server.py --port 8765`
   - Expose with HTTPS callback base (ngrok/domain)
2. Developer portal configuration
   - Add exact callback URL: `<base>/x/callback`
   - Ensure app permissions include write and DM access when needed
3. Environment variables
   - Confirm `X_CLIENT_ID`
   - Confirm `X_CALLBACK_BASE_URL` (no trailing slash)
   - Optional `X_CLIENT_SECRET` where applicable
4. Start flow
   - Open `<base>/x/start`
   - Confirm token file written to `credentials/x_oauth_tokens.json`

## Troubleshooting tree

1. Access denied during auth
   - Check app permission tier includes DM if requesting `dm.read`/`dm.write`
   - Temporarily test minimal scopes: `tweet.read users.read offline.access`
2. Callback mismatch
   - Ensure exact match between portal callback and runtime callback path
   - Confirm protocol and host are identical
3. 401/403 on write attempts after auth
   - Validate correct token source (user context vs app bearer token)
   - Re-run flow after permission updates
4. Reply-specific 403
   - Explain API reply policy limits from `docs/reference/x-api-manage-posts.md`

## Output format

```markdown
# X OAuth Status Report

- OAuth flow: <ok / partial / fail>
- Callback URL match: <ok / mismatch>
- App permissions: <ok / insufficient>
- Token file: <present / missing>

## Findings
- <issue and evidence>

## Actions taken
- <commands or config updates>

## Next step
- <single next action>
```

## Guardrails

- Never claim OAuth is fixed without either successful `/x/start` completion or verified token file output.
- Keep troubleshooting evidence-based and reference exact callback/scopes used.
