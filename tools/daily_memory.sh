#!/bin/bash
# Daily Memory Management
# Runs at end of day to create memory files and update long-term memory

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_FILE="$REPO_DIR/memory/memory-cron.log"
DATE=$(date +%Y-%m-%d)

echo "========== Memory Management: $DATE ==========" >> "$LOG_FILE"

cd "$REPO_DIR"

# Create daily memory file
echo "Creating daily memory file..." >> "$LOG_FILE"
python3 "$REPO_DIR/tools/memory_manager.py" --daily >> "$LOG_FILE" 2>&1

# Update long-term MEMORY.md
echo "Updating long-term memory..." >> "$LOG_FILE"
python3 "$REPO_DIR/tools/memory_manager.py" --update-memory >> "$LOG_FILE" 2>&1

echo "========== End: $(date) ==========" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
