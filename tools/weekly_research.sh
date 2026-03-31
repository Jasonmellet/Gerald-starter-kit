#!/bin/bash
# Weekly Self-Improvement Research Cron Job
# Runs every Monday at 9 AM
# Budget: $10/month (~$2.50/week)

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_FILE="$REPO_DIR/memory/api-usage/cron.log"
DATE=$(date +%Y-%m-%d)

echo "========== Research Cron: $DATE ==========" >> "$LOG_FILE"

cd "$REPO_DIR"

# Weekly research queries (rotating topics)
# Week 1: OpenClaw ecosystem
# Week 2: AI agent techniques
# Week 3: Marketing automation trends
# Week 4: LLM improvements

WEEK=$(date +%U)
WEEK_MOD=$((WEEK % 4))

case $WEEK_MOD in
    0)
        echo "Week $WEEK: OpenClaw ecosystem research (SECURITY FOCUS)" >> "$LOG_FILE"
        python3 tools/research_agent.py --query "OpenClaw security vulnerabilities malware skills" --results 10 >> "$LOG_FILE" 2>&1
        python3 tools/research_agent.py --query "OpenClaw infrastructure updates safe practices" --results 10 >> "$LOG_FILE" 2>&1
        ;;
    1)
        echo "Week $WEEK: AI agent techniques" >> "$LOG_FILE"
        python3 tools/research_agent.py --query "AI agent automation best practices 2025" --results 10 >> "$LOG_FILE" 2>&1
        python3 tools/research_agent.py --trends --keywords "AI agents,automation,LLM" >> "$LOG_FILE" 2>&1
        ;;
    2)
        echo "Week $WEEK: Marketing automation trends" >> "$LOG_FILE"
        python3 tools/research_agent.py --query "cold email automation trends 2025" --results 10 >> "$LOG_FILE" 2>&1
        python3 tools/research_agent.py --query "PPC AI optimization tools" --results 5 >> "$LOG_FILE" 2>&1
        ;;
    3)
        echo "Week $WEEK: LLM improvements" >> "$LOG_FILE"
        python3 tools/research_agent.py --query "LLM prompting techniques 2025" --results 10 >> "$LOG_FILE" 2>&1
        python3 tools/research_agent.py --trends --keywords "LLM,AI models,prompt engineering" >> "$LOG_FILE" 2>&1
        ;;
esac

# Run CSO security scan
echo "Running CSO security scan..." >> "$LOG_FILE"
python3 "$REPO_DIR/tools/cso.py" --scan >> "$LOG_FILE" 2>&1

# Generate security report
REPORT_FILE="$REPO_DIR/memory/security/report_$(date +%Y%m%d_%H%M%S).txt"
python3 "$REPO_DIR/tools/cso.py" --report > "$REPORT_FILE" 2>&1

# Send weekly digest email with security report
python3 "$REPO_DIR/tools/scheduled_reports.py" --weekly >> "$LOG_FILE" 2>&1

echo "========== End: $(date) ==========" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
