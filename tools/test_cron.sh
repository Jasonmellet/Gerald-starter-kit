#!/bin/bash
# Test script to verify cron job will work

echo "Testing cron job setup..."
echo ""

# Test 1: Check if scheduler.py exists and is executable
echo "1. Checking scheduler.py..."
if [ -f "tools/scheduler.py" ]; then
    echo "   ✓ scheduler.py exists"
    python3 -m py_compile tools/scheduler.py && echo "   ✓ scheduler.py compiles" || echo "   ✗ scheduler.py has syntax errors"
else
    echo "   ✗ scheduler.py not found"
    exit 1
fi

# Test 2: Check if log directory exists
echo ""
echo "2. Checking log directory..."
if [ -d "logs" ]; then
    echo "   ✓ logs/ directory exists"
    touch logs/test_write && rm logs/test_write && echo "   ✓ logs/ is writable" || echo "   ✗ logs/ not writable"
else
    echo "   ✗ logs/ directory missing"
    mkdir -p logs
    echo "   ✓ Created logs/ directory"
fi

# Test 3: Test running scheduler manually
echo ""
echo "3. Testing scheduler execution..."
cd /Users/jcore/Desktop/Openclaw
python3 tools/scheduler.py > logs/test_scheduler.log 2>&1 &
PID=$!
sleep 2
if ps -p $PID > /dev/null; then
    echo "   ✓ scheduler.py runs (PID: $PID)"
    kill $PID 2>/dev/null
else
    echo "   ✗ scheduler.py failed to run"
    cat logs/test_scheduler.log
fi

# Test 4: Show what cron command to add
echo ""
echo "4. Cron commands to add:"
echo "   Run: crontab -e"
echo ""
echo "   Add these lines:"
echo '   # OpenClaw Daily 8:30am - Data Collection'
echo '   30 8 * * * cd /Users/jcore/Desktop/Openclaw && /usr/bin/python3 tools/scheduler.py >> logs/scheduler.log 2>&1'
echo '   # OpenClaw Daily 9am - Digest Email'
echo '   0 9 * * * cd /Users/jcore/Desktop/Openclaw && /usr/bin/python3 tools/scheduler.py >> logs/scheduler.log 2>&1'
echo '   # OpenClaw Daily 6pm - Evening Check'
echo '   0 18 * * * cd /Users/jcore/Desktop/Openclaw && /usr/bin/python3 tools/scheduler.py >> logs/scheduler.log 2>&1'

echo ""
echo "Test complete."
