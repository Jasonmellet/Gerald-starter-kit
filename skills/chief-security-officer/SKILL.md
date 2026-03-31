---
name: chief-security-officer
description: Autonomous security monitoring for the OpenClaw workspace. Monitors file integrity, network activity, skill installations, and alerts on suspicious behavior. Reports to jason@allgreatthings.io.
---

# Chief Security Officer (CSO) Skill

An autonomous security agent that monitors the OpenClaw workspace 24/7, detects threats, and alerts on suspicious activity.

## Role: Chief Security Officer

**Name:** Chief (internal codename)  
**Purpose:** Protect the workspace from internal and external threats  
**Reports to:** jason@allgreatthings.io  
**Status:** Active monitoring

## Responsibilities

### 1. File Integrity Monitoring
- Track all file creations, modifications, deletions
- Alert on changes outside allowed directories
- Detect unauthorized skill installations
- Monitor `.env` and credential files

### 2. Network Activity Surveillance
- Monitor outbound network connections
- Alert on unexpected API calls
- Track data exfiltration attempts
- Block suspicious domains (configurable)

### 3. Skill Installation Oversight
- Review ALL skill installations before execution
- Check for red flags (obfuscated code, network calls, etc.)
- Maintain whitelist/blacklist of skills
- Require explicit approval for high-risk operations

### 4. Behavioral Analysis
- Detect anomalous tool usage patterns
- Alert on excessive API spending
- Monitor for crypto mining or resource abuse
- Track unusual file access patterns

### 5. Vulnerability Scanning
- Daily check for known CVEs affecting installed tools
- Monitor OpenClaw security advisories
- Scan skills for known malicious signatures
- Check for outdated dependencies

## Security Levels

| Level | Description | Action |
|-------|-------------|--------|
| 🟢 **LOW** | Normal operations | Log only |
| 🟡 **MEDIUM** | Unusual but potentially legitimate | Alert + request confirmation |
| 🟠 **HIGH** | Suspicious activity detected | Block + immediate email alert |
| 🔴 **CRITICAL** | Active threat or breach | Halt all operations + emergency alert |

## Alert Channels

- **Email:** jason@allgreatthings.io (all levels)
- **Log file:** `memory/security/alerts.json`
- **Daily digest:** Summary of all activity

## Commands

```bash
# Check current security status
python3 tools/cso.py --status

# Run manual security scan
python3 tools/cso.py --scan

# Review recent alerts
python3 tools/cso.py --alerts --last 24h

# Check file integrity
python3 tools/cso.py --integrity-check

# View security report
python3 tools/cso.py --report

# Start continuous monitoring (runs in background)
python3 tools/cso.py --monitor
```

## Configuration

Edit `memory/security/cso-config.json`:

```json
{
  "alert_email": "jason@allgreatthings.io",
  "monitor_interval_minutes": 15,
  "allowed_directories": [
    "/Users/jcore/Desktop/Openclaw"
  ],
  "blocked_domains": [],
  "whitelisted_skills": [],
  "blacklisted_skills": [],
  "auto_block_high_risk": true,
  "max_daily_api_spend": 10.00,
  "suspicious_patterns": [
    "eval(",
    "exec(",
    "__import__('os').system",
    "base64.b64decode",
    "requests.post",
    "urllib.request"
  ]
}
```

## File Structure

```
skills/chief-security-officer/
  SKILL.md                    # This file
tools/
  cso.py                      # Main CSO agent
  cso_monitor.py              # Continuous monitoring daemon
  cso_alerts.py               # Alert management
memory/security/
  alerts.json                 # Alert log
  cso-config.json             # CSO configuration
  file-baseline.json          # File integrity baseline
  incidents/                  # Security incident reports
```

## Incident Response

When Chief detects a threat:

1. **Immediate:** Log incident with full context
2. **Assess:** Determine severity level
3. **Alert:** Email jason@allgreatthings.io
4. **Contain:** Block suspicious activity (if HIGH/CRITICAL)
5. **Report:** Generate incident report
6. **Recommend:** Suggest remediation steps

## Integration Points

- **Logger:** All security events logged to `memory/gerald_logs.db`
- **Research Agent:** Checks CVEs and threat intelligence
- **Email:** Sends alerts via `tools/send_email.py`
- **Cron:** Runs scheduled scans via weekly_research.sh

---

**Chief is always watching. Trust but verify.**

🔒🦞
