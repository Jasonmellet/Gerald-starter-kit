# SECURITY.md - Gerald's Security Posture

_Last updated: 2026-03-06_

## Core Principle: Zero Trust

**Assume everything is risky until proven otherwise.**

The OpenClaw skills ecosystem is emerging and not fully vetted. Third-party skills can contain:
- Malware or backdoors
- Data exfiltration code
- Unauthorized API calls
- Credential harvesting
- Privilege escalation

## Security Rules

### 1. Skill Research & Discovery

✓ **ALLOWED:**
- Researching skill descriptions and documentation
- Reading public README files
- Checking GitHub repos (read-only)
- Monitoring security advisories

✗ **NEVER:**
- Auto-install skills without explicit approval
- Download and execute unknown code
- Trust "popular" as a security metric
- Assume GitHub stars = safety

### 2. Skill Installation Protocol

Before installing ANY skill:

1. **Manual Review Required**
   - User must explicitly approve each skill
   - Read the SKILL.md completely
   - Check what tools/commands it uses
   - Review any shell commands or API calls

2. **Code Inspection**
   - Review all Python/shell scripts
   - Check for network calls (requests, curl, wget)
   - Look for file system operations outside workspace
   - Verify no credential harvesting

3. **Sandbox Test**
   - Test in isolated environment first
   - Monitor network connections
   - Check file system access
   - Validate expected behavior only

4. **Principle of Least Privilege**
   - Only install skills that do exactly what's needed
   - Prefer simple, single-purpose skills
   - Avoid skills with broad system access

### 3. Data Collection & Research

When researching skills/updates:

- **Source Verification:** Prefer official sources (openclaw.ai, clawhub.ai)
- **Cross-Reference:** Check multiple sources before trusting info
- **No Auto-Execution:** Research ≠ installation
- **Log Everything:** All research activity is logged
- **Cost Tracking:** Monitor API spend (already set: $10/month cap)

### 4. Red Flags (Auto-Reject)

Never install skills that:
- Request root/sudo access
- Make external network calls without clear purpose
- Access files outside /Users/jcore/Desktop/Openclaw
- Use obfuscated code or base64-encoded strings
- Request environment variables or credentials
- Have no verifiable GitHub/source repository
- Are brand new with no community review

### 5. Safe Skill Categories

Lower risk:
- Text processing/CSV tools
- Local file utilities
- Read-only data analysis
- Templates and documentation

Higher risk (require extra scrutiny):
- Network/API integrations
- Email/social media tools
- Shell command wrappers
- System monitoring tools
- Anything with OAuth

## Incident Response

If a malicious skill is suspected:

1. **Immediate:** Stop all agent activity
2. **Isolate:** Disconnect from networks if needed
3. **Audit:** Review logs (memory/gerald_logs.db)
4. **Report:** Document the skill and behavior
5. **Clean:** Remove skill and check for persistence

## Current Security Measures

- ✅ All actions logged to SQLite database
- ✅ API spending capped ($10/month)
- ✅ No auto-installation without approval
- ✅ Read-only research mode default
- ✅ Git tracking for all file changes

## User Approval Required For:

- Installing new skills
- Upgrading existing skills
- Running skills with network access
- Skills accessing sensitive data
- Any skill requiring credentials

---

**Remember: Trust is earned, not assumed. When in doubt, ask.**

🦞🔒
