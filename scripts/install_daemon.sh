#!/bin/bash
# Model Realignment: Daemon Installation Script

set -e

PROJECT_DIR="/Users/ryanthomson/Github/model-realignment"
PLIST_FILE="$PROJECT_DIR/config/com.ryan.modelrealignment.plist"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"

echo "Installing Model Realignment daemon..."

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Create data directory if it doesn't exist
mkdir -p "$PROJECT_DIR/data"

# Copy plist to LaunchAgents directory
echo "Installing launch agent..."
cp "$PLIST_FILE" "$LAUNCHD_DIR/"

# Load the daemon
echo "Loading daemon..."
launchctl load "$LAUNCHD_DIR/com.ryan.modelrealignment.plist"

# Check if it's running
sleep 2
if launchctl list | grep -q "com.ryan.modelrealignment"; then
    echo "✅ Daemon installed and running successfully!"
    echo "Status: $(launchctl list | grep com.ryan.modelrealignment)"
else
    echo "❌ Daemon installation may have failed. Check logs:"
    echo "   $PROJECT_DIR/logs/daemon_stderr.log"
fi

echo ""
echo "Next steps:"
echo "1. Install AppleScript global shortcut:"
echo "   - Open 'score_clipboard.applescript' in Script Editor"
echo "   - Save as Application to Applications folder"
echo "   - Set up global shortcut in System Preferences > Keyboard > Shortcuts"
echo ""
echo "2. Test the system:"
echo "   python3 main_loop.py --status"
echo ""
echo "3. Check logs:"
echo "   tail -f $PROJECT_DIR/logs/model_realignment.log"