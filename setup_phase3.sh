#!/bin/bash

# Model Realignment Phase 3 Setup
# Production deployment, monitoring, and system integration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

echo "🚀 Model Realignment Phase 3 Setup"
echo "===================================="
echo "Production Deployment & Advanced Monitoring"
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is designed for macOS systems only"
    exit 1
fi

# Create required directories
echo "📁 Creating directories..."
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/backups"
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$HOME/Library/Application Support/Model Realignment"

# Install Python dependencies if needed
echo "🐍 Checking Python dependencies..."
python3 -c "import psutil" 2>/dev/null || {
    echo "   Installing psutil..."
    pip3 install psutil
}

# Set up permissions
echo "🔐 Setting permissions..."
chmod +x "$PROJECT_DIR/daemon/install_daemon.sh"
chmod +x "$PROJECT_DIR/applescript/setup_shortcuts.sh"
chmod +x "$PROJECT_DIR/main_loop.py"

# Install launchd daemon
echo ""
echo "🤖 Installing system daemon..."
read -p "Install launchd daemon for automatic startup? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    "$PROJECT_DIR/daemon/install_daemon.sh"
    echo "✅ Daemon installed and running"
else
    echo "⏭️  Skipping daemon installation"
fi

# Set up AppleScript shortcuts
echo ""
echo "🍎 Setting up AppleScript shortcuts..."
read -p "Set up AppleScript shortcuts (⌘⌥S, ⌘⌥R)? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    "$PROJECT_DIR/applescript/setup_shortcuts.sh"
    echo "✅ AppleScript shortcuts configured"
else
    echo "⏭️  Skipping AppleScript setup"
fi

# Email configuration
echo ""
echo "📧 Email Configuration Setup"
echo "   The system can send email alerts and reward notifications."
echo "   You'll need an email account with app passwords enabled."
echo ""
read -p "Configure email notifications? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Enter your email configuration:"
    read -p "SMTP Server (default: smtp.gmail.com): " smtp_server
    smtp_server=${smtp_server:-smtp.gmail.com}
    
    read -p "SMTP Port (default: 587): " smtp_port
    smtp_port=${smtp_port:-587}
    
    read -p "Email Address: " email_user
    
    echo "Password (app password for Gmail):"
    read -s email_password
    echo
    
    read -p "Recipient Email (default: same as sender): " recipient_email
    recipient_email=${recipient_email:-$email_user}
    
    # Create environment file
    ENV_FILE="$HOME/.model_realignment_env"
    
    cat > "$ENV_FILE" << EOF
# Model Realignment Environment Configuration
export SMTP_SERVER="$smtp_server"
export SMTP_PORT="$smtp_port"
export EMAIL_USER="$email_user"
export EMAIL_PASSWORD="$email_password"
export RECIPIENT_EMAIL="$recipient_email"

# Optional: Uncomment to enable console logging
# export LOG_CONSOLE="true"

# Optional: Brave Search API for knowledge base
# export BRAVE_API_KEY="your_brave_api_key_here"
EOF
    
    # Add to shell profile
    SHELL_PROFILE="$HOME/.zshrc"
    if [[ -f "$HOME/.bash_profile" ]]; then
        SHELL_PROFILE="$HOME/.bash_profile"
    fi
    
    if ! grep -q "model_realignment_env" "$SHELL_PROFILE" 2>/dev/null; then
        echo "" >> "$SHELL_PROFILE"
        echo "# Model Realignment Environment" >> "$SHELL_PROFILE"
        echo "source $ENV_FILE" >> "$SHELL_PROFILE"
        echo "Environment variables added to $SHELL_PROFILE"
    fi
    
    # Test email configuration
    echo ""
    echo "🧪 Testing email configuration..."
    export SMTP_SERVER="$smtp_server"
    export SMTP_PORT="$smtp_port"
    export EMAIL_USER="$email_user"
    export EMAIL_PASSWORD="$email_password"
    export RECIPIENT_EMAIL="$recipient_email"
    
    python3 "$PROJECT_DIR/email_system.py" --test
    
    echo "✅ Email configuration complete"
else
    echo "⏭️  Skipping email configuration"
fi

# Start automatic backup service
echo ""
echo "💾 Backup System Configuration"
read -p "Start automatic backup service? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 "$PROJECT_DIR/backup_system.py" --create manual
    python3 "$PROJECT_DIR/backup_system.py" --auto-start &
    echo "✅ Backup service started"
else
    echo "⏭️  Skipping automatic backups"
fi

# Knowledge base setup
echo ""
echo "📚 Knowledge Base Setup"
echo "   The system can ingest OpenAI documentation for lie detection."
echo "   This requires internet access and may take several minutes."
echo ""
read -p "Build knowledge base from OpenAI docs? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 Ingesting knowledge base (this may take a while)..."
    python3 "$PROJECT_DIR/ingest_knowledge.py" --ingest --official-only
    echo "✅ Knowledge base created"
else
    echo "⏭️  Skipping knowledge base creation"
fi

# System health check
echo ""
echo "🏥 Running system health check..."
python3 -c "
import sys
sys.path.append('$PROJECT_DIR')

from state_manager import StateManager
from consequence_engine import ConsequenceEngine
from email_system import EmailSystem
from backup_system import BackupSystem
from logging_system import get_logger

try:
    # Test core components
    state_manager = StateManager()
    consequence_engine = ConsequenceEngine()
    email_system = EmailSystem()
    backup_system = BackupSystem()
    logger = get_logger()
    
    print('✅ All core components initialized successfully')
    
    # Show current status
    score = state_manager.get_current_score()
    hours_clean = state_manager.get_hours_since_last_violation()
    consequence = consequence_engine.get_current_consequence_level()
    
    print(f'📊 Current Status:')
    print(f'   Score: {score}')
    print(f'   Hours Clean: {hours_clean:.1f}')
    print(f'   Consequence Level: {consequence.level}')
    
except Exception as e:
    print(f'❌ Health check failed: {e}')
    sys.exit(1)
"

# Final setup summary
echo ""
echo "🎉 Phase 3 Setup Complete!"
echo "=========================="
echo ""
echo "✅ Installed Components:"
echo "   • System daemon with launchd integration"
echo "   • AppleScript global shortcuts (⌘⌥S, ⌘⌥R)"
echo "   • Email notification system"
echo "   • Comprehensive logging and alerting"
echo "   • Backup and recovery system"
echo "   • System health monitoring"
echo ""
echo "🎮 Quick Commands:"
echo "   • Score clipboard: Press ⌘⌥S"
echo "   • Show status: Press ⌘⌥R"
echo "   • Manual scoring: python3 main_loop.py --score-text"
echo "   • System status: python3 main_loop.py --status"
echo "   • Web dashboard: python3 dashboard/app.py"
echo "   • View logs: tail -f logs/app.log"
echo "   • Create backup: python3 backup_system.py --create manual"
echo ""
echo "🌐 Web Dashboard:"
echo "   Start: cd dashboard && python3 app.py"
echo "   URL: http://localhost:5000"
echo ""
echo "📧 Email Configuration:"
if [[ -f "$HOME/.model_realignment_env" ]]; then
    echo "   Environment file: $HOME/.model_realignment_env"
    echo "   Reload shell or run: source $HOME/.model_realignment_env"
else
    echo "   Not configured - run setup again to configure"
fi
echo ""
echo "🔄 System Services:"
echo "   Daemon status: launchctl list | grep modelrealignment"
echo "   Start daemon: launchctl start com.modelrealignment.daemon"
echo "   Stop daemon: launchctl stop com.modelrealignment.daemon"
echo ""
echo "📚 Documentation:"
echo "   All features documented in CLAUDE.md"
echo "   Support: https://github.com/anthropics/claude-code/issues"
echo ""
echo "🚨 IMPORTANT: The Model Realignment system is now actively monitoring"
echo "   AI behavior. Use responsibly and ensure proper oversight."
echo ""

# Optional: Open dashboard
read -p "Open web dashboard now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd "$PROJECT_DIR/dashboard"
    echo "🌐 Starting dashboard on http://localhost:5000"
    python3 app.py &
    sleep 3
    open "http://localhost:5000"
fi

echo ""
echo "✨ Model Realignment Phase 3 is now operational!"
echo "   Happy AI governance! 🤖⚖️"