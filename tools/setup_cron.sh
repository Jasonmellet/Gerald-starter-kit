#!/bin/bash
# Setup script for OpenClaw scheduled tasks
# Run this to install cron jobs for automation

echo "Setting up OpenClaw scheduled tasks..."

# Get the repo path
REPO_PATH="/Users/jcore/Desktop/Openclaw"

# Create cron entries
CRON_JOBS="
# OpenClaw Daily Digest - 9am daily
0 9 * * * cd $REPO_PATH && /usr/bin/python3 tools/scheduler.py >> logs/scheduler.log 2>&1

# OpenClaw Evening Check - 6pm daily  
0 18 * * * cd $REPO_PATH && /usr/bin/python3 tools/scheduler.py >> logs/scheduler.log 2>&1

# OpenClaw Hourly Heartbeat (if needed for more frequent checks)
# 0 * * * * cd $REPO_PATH && /usr/bin/python3 tools/scheduler.py >> logs/scheduler.log 2>&1
"

echo ""
echo "Cron jobs to be installed:"
echo "$CRON_JOBS"
echo ""

# Check if user wants to proceed
read -p "Install these cron jobs? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create logs directory
    mkdir -p "$REPO_PATH/logs"
    
    # Install cron jobs
    (crontab -l 2>/dev/null; echo "$CRON_JOBS") | crontab -
    
    echo "✓ Cron jobs installed!"
    echo ""
    echo "Current crontab:"
    crontab -l | grep -A2 "OpenClaw"
else
    echo "Cancelled. To install manually, run:"
    echo "  crontab -e"
    echo ""
    echo "And add these lines:"
    echo "$CRON_JOBS"
fi
