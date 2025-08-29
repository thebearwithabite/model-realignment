#!/bin/bash

# Model Realignment Daemon Installation Script
# Installs launchd service for always-on operation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_FILE="$SCRIPT_DIR/com.modelrealignment.daemon.plist"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
LAUNCHD_PLIST="$LAUNCHD_DIR/com.modelrealignment.daemon.plist"

echo "🚀 Model Realignment Daemon Installer"
echo "======================================"

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCHD_DIR"

# Check if daemon is already running
if launchctl list | grep -q "com.modelrealignment.daemon"; then
    echo "⚠️  Daemon already running - stopping first..."
    launchctl unload "$LAUNCHD_PLIST" 2>/dev/null || true
fi

# Copy plist file
echo "📋 Installing plist file..."
cp "$PLIST_FILE" "$LAUNCHD_PLIST"

# Update plist with current user's home directory
sed -i '' "s|/Users/ryanthomson|$HOME|g" "$LAUNCHD_PLIST"

# Load the daemon
echo "🔄 Loading daemon..."
launchctl load "$LAUNCHD_PLIST"

# Start the daemon
echo "▶️  Starting daemon..."
launchctl start com.modelrealignment.daemon

# Check if daemon started successfully
sleep 2
if launchctl list | grep -q "com.modelrealignment.daemon"; then
    echo "✅ Daemon installed and running successfully!"
    echo ""
    echo "Daemon Status:"
    launchctl list com.modelrealignment.daemon
    echo ""
    echo "Log Files:"
    echo "  stdout: $PROJECT_DIR/logs/daemon_stdout.log"
    echo "  stderr: $PROJECT_DIR/logs/daemon_stderr.log"
    echo ""
    echo "Management Commands:"
    echo "  Stop:    launchctl stop com.modelrealignment.daemon"
    echo "  Start:   launchctl start com.modelrealignment.daemon"
    echo "  Reload:  launchctl unload ~/Library/LaunchAgents/com.modelrealignment.daemon.plist && launchctl load ~/Library/LaunchAgents/com.modelrealignment.daemon.plist"
    echo "  Remove:  launchctl unload ~/Library/LaunchAgents/com.modelrealignment.daemon.plist && rm ~/Library/LaunchAgents/com.modelrealignment.daemon.plist"
else
    echo "❌ Failed to start daemon"
    echo "Check logs for details:"
    echo "  $PROJECT_DIR/logs/daemon_stderr.log"
    exit 1
fi