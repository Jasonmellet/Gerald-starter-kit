#!/bin/bash
# Setup cron jobs for OpenClaw

cd /Users/jcore/Desktop/Openclaw

# Add cron entries
crontab -l > /tmp/current_crontab 2>/dev/null || echo "# New crontab" > /tmp/current_crontab

cat >> /tmp/current_crontab << 'EOF'

# OpenClaw Daily Schedule
# 8:30am - Collect data for digest
30 8 * * * cd /Users/jcore/Desktop/Openclaw && /usr/bin/python3 tools/scheduler.py >> logs/scheduler.log 2>&1
# 9:00am - Send daily digest email
0 9 * * * cd /Users/jcore/Desktop/Openclaw && /usr/bin/python3 tools/scheduler.py >> logs/scheduler.log 2>&1
# 6:00pm - Evening check
0 18 * * * cd /Users/jcore/Desktop/Openclaw && /usr/bin/python3 tools/scheduler.py >> logs/scheduler.log 2>&1
EOF

crontab /tmp/current_crontab
rm /tmp/current_crontab

echo "Cron jobs installed. Current crontab:"
crontab -l | grep -A5 "OpenClaw Daily"
