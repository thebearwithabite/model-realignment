#!/bin/bash

# Model Realignment Rewards Scheduler Installation Script
# Installs launchd service for periodic reward checks.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_FILE="$PROJECT_DIR/config/com.ryan.modelrealignment.rewards.plist"
PLIST_LABEL="com.ryan.modelrealignment.rewards"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
LAUNCHD_PLIST="$LAUNCHD_DIR/$PLIST_LABEL.plist"

echo "🚀 Model Realignment Rewards Scheduler Installer"
echo "==============================================="

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCHD_DIR"

# Check if job is already running
if launchctl list | grep -q "$PLIST_LABEL"; then
    echo "⚠️  Scheduler already running - stopping first..."
    launchctl unload "$LAUNCHD_PLIST" 2>/dev/null || true
fi

# Copy plist file
echo "📋 Installing plist file..."
cp "$PLIST_FILE" "$LAUNCHD_PLIST"

# Replace placeholder with the correct project directory
echo "🔧 Configuring plist with project path..."
sed -i '' "s|__PROJECT_PATH_PLACEHOLDER__|$PROJECT_DIR|g" "$LAUNCHD_PLIST"

# Load the launchd job
echo "🔄 Loading scheduler job..."
launchctl load "$LAUNCHD_PLIST"

# Check if job loaded successfully
sleep 2
if launchctl list | grep -q "$PLIST_LABEL"; then
    echo "✅ Rewards scheduler installed and loaded successfully!"
    echo ""
    echo "This job will run automatically every 12 hours."
    echo ""
    echo "Log Files:"
    echo "  stdout: $PROJECT_DIR/logs/rewards_stdout.log"
    echo "  stderr: $PROJECT_DIR/logs/rewards_stderr.log"
    echo ""
    echo "Management Commands:"
    echo "  Stop:    launchctl unload $LAUNCHD_PLIST"
    echo "  Start:   launchctl load $LAUNCHD_PLIST"
    echo "  Remove:  rm $LAUNCHD_PLIST"
else
    echo "❌ Failed to load scheduler job."
    echo "Check logs for details."
    exit 1
fi
