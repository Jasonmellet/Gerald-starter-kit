# Daily Security Summary Cron Job
# Runs every day at 8 AM

REPO_DIR="/Users/jcore/Desktop/Openclaw"
LOG_FILE="$REPO_DIR/memory/reports/cron-daily.log"
DATE=$(date +%Y-%m-%d)

echo "========== Daily Report: $DATE ==========" >> "$LOG_FILE"

cd "$REPO_DIR"

# Run CSO quick scan
echo "Running CSO quick scan..." >> "$LOG_FILE"
python3 "$REPO_DIR/tools/cso.py" --scan >> "$LOG_FILE" 2>&1

# Send daily report
python3 "$REPO_DIR/tools/scheduled_reports.py" --daily >> "$LOG_FILE" 2>&1

echo "========== End: $(date) ==========" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
