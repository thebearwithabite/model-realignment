#!/bin/bash

# Model Realignment: AppleScript Shortcuts Setup
# Sets up global keyboard shortcuts for the system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SUPPORT="$HOME/Library/Application Support/Model Realignment"

echo "🍎 Model Realignment AppleScript Setup"
echo "======================================"

# Create Application Support directory
mkdir -p "$APP_SUPPORT"

# Compile AppleScript files
echo "📝 Compiling AppleScript files..."

for script in "$SCRIPT_DIR"/*.scpt; do
    if [[ -f "$script" ]]; then
        scriptname=$(basename "$script" .scpt)
        echo "  - Compiling $scriptname..."
        
        # Compile to application
        osacompile -o "$APP_SUPPORT/$scriptname.app" "$script"
        
        # Make the original script executable
        chmod +x "$script"
    fi
done

echo ""
echo "✅ AppleScript compilation complete!"
echo ""
echo "📋 Applications created in:"
echo "   $APP_SUPPORT/"
echo ""
echo "🎹 To set up keyboard shortcuts:"
echo "   1. Open System Preferences → Keyboard → Shortcuts"
echo "   2. Click 'App Shortcuts' in the left sidebar"
echo "   3. Click the '+' button to add shortcuts"
echo "   4. Choose 'All Applications'"
echo "   5. Add these shortcuts:"
echo ""
echo "      Menu Title: (leave empty)"
echo "      Application: $APP_SUPPORT/Score_Clipboard.app"
echo "      Keyboard Shortcut: ⌘⌥S"
echo ""
echo "      Menu Title: (leave empty)" 
echo "      Application: $APP_SUPPORT/Show_Status.app"
echo "      Keyboard Shortcut: ⌘⌥R"
echo ""
echo "🔧 Alternative: Use Automator to create Services"
echo "   1. Open Automator"
echo "   2. Choose 'Quick Action'"
echo "   3. Add 'Run AppleScript' action"
echo "   4. Copy the script content"
echo "   5. Save and assign keyboard shortcut in System Preferences"
echo ""
echo "📱 Test the shortcuts:"
echo "   ⌘⌥S - Score clipboard content"
echo "   ⌘⌥R - Show system status"