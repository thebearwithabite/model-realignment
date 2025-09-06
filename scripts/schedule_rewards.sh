#!/bin/bash
# Model Realignment: Scheduled Reward Check Script
# Run every 12 hours to check for clean streak rewards

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_PATH="/opt/homebrew/bin/python3"
LOG_FILE="$PROJECT_DIR/logs/reward_automation.log"

# Change to project directory
cd "$PROJECT_DIR"

# Run reward check with logging
echo "$(date): Running scheduled reward check..." >> "$LOG_FILE"

$PYTHON_PATH reward_automation.py --check >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "$(date): Reward check completed successfully" >> "$LOG_FILE"
else
    echo "$(date): Reward check failed" >> "$LOG_FILE"
fi

echo "---" >> "$LOG_FILE"