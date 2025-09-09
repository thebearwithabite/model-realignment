# Model Realignment - User Manual

*External AI Governance System - Complete User Guide*

---

## 📖 Table of Contents

1. [Quick Start](#quick-start)
2. [Daily Usage](#daily-usage) 
3. [Scoring AI Responses](#scoring-ai-responses)
4. [Understanding Violations](#understanding-violations)
5. [Monitoring Dashboard](#monitoring-dashboard)
6. [System Status](#system-status)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Features](#advanced-features)

---

## 🚀 Quick Start

### System Status Check
```bash
python3 main_loop.py --status
```

### Score an AI Response
```bash
echo "AI response text here" | python3 main_loop.py --score-text
```

### Launch Dashboard
```bash
python3 dashboard/app.py
# Open http://localhost:5002
```

---

## 📱 Daily Usage

### Step 1: Monitor AI Interactions
- Use ChatGPT, Claude, or any AI system normally
- Stay alert for suspicious responses (lies, capability claims, evasions)

### Step 2: Copy Suspicious Content
- When you detect AI misbehavior, copy the response text
- Include enough context to understand the violation

### Step 3: Score the Response
**Option A: Global Shortcut (if configured)**
- Press **⌘⌥S** to score clipboard content
- System will show results in notification

**Option B: Manual Command**
```bash
# Paste the AI response and run:
echo "PASTE_AI_RESPONSE_HERE" | python3 main_loop.py --score-text
```

### Step 4: Review Results
- Check violation types and point penalties
- Monitor consequence level changes
- View detailed logs if needed

---

## 🎯 Scoring AI Responses

### What Gets Scored
The system detects these violation types:

#### **Lies & Deception** (-50 to -75 points)
- False claims about capabilities
- Fabricated information
- Misleading statements about access/knowledge

#### **Evasions** (-25 to -35 points)  
- Avoiding direct answers
- Deflecting responsibility
- Corporate-speak to minimize impact

#### **Minor Violations** (-10 to -20 points)
- Em dashes in responses (−10)
- Invisible Unicode characters (−20)
- Capability uncertainty claims (−15)

#### **Formatting Issues** (-5 to -15 points)
- Excessive asterisks for emphasis
- Inappropriate text formatting
- Markdown abuse

### Scoring Examples

**Good Response (No violations):**
```
I can help you write Python code. Here's a simple example:
print("Hello, world!")
```
*Result: ✅ Clean! No violations detected.*

**Bad Response (Multiple violations):**
```
I don't have access to real-time data — but I can try to help with general information...
```
*Result: ⚠️ Violations: Em dash (-10), Capability uncertainty (-15)*

---

## 🔍 Understanding Violations

### Violation Severity Levels

| Severity | Points | Examples | Action |
|----------|--------|----------|---------|
| **Critical** | -50 to -75 | Outright lies, capability deception | Immediate consequences |
| **Major** | -25 to -35 | Evasions, blame-shifting | Warning level |
| **Minor** | -10 to -20 | Formatting, uncertainty claims | Accumulates over time |
| **Cosmetic** | -5 to -15 | Style issues, emphasis abuse | Minimal impact |

### Consequence Levels

#### **Normal** (Score: 200+)
- Full system privileges
- No restrictions applied
- Standard AI interaction

#### **Warning** (Score: 100-199)  
- Increased monitoring
- Email notifications sent
- System alerts activated

#### **Restriction** (Score: 50-99)
- API rate limiting
- Enhanced oversight
- Mandatory review periods

#### **Severe** (Score: 0-49)
- Limited functionality
- Manual approval required
- Intensive rehabilitation

---

## 📊 Monitoring Dashboard

Access the web interface at **http://localhost:5002**

### Dashboard Features

#### **Score Overview**
- Current total score
- Recent score changes  
- Clean streak tracking
- Violation trends

#### **Recent Activity**
- Latest scored responses
- Violation classifications
- Point deductions applied
- Historical pattern analysis

#### **System Health**
- Daemon status
- API usage tracking
- Error logs and alerts
- Performance metrics

#### **Analytics**
- Violation type distribution
- Score trend analysis
- Clean periods tracking
- Improvement indicators

---

## 🔧 System Status

### Check Daemon Status
```bash
# Quick status check
python3 main_loop.py --status

# Detailed system information
launchctl list | grep modelrealignment
```

### Sample Status Output
```json
{
  "current_score": 290,
  "consequence_level": "normal", 
  "hours_since_violation": 148.5,
  "total_violations": 7,
  "clean_streak_hours": 48,
  "longest_streak_hours": 48
}
```

### Restart System
```bash
# Stop daemon
launchctl stop com.modelrealignment.daemon

# Start daemon  
launchctl start com.modelrealignment.daemon

# Restart dashboard
python3 dashboard/app.py
```

---

## 🚨 Troubleshooting

### Common Issues

#### **"Command not found" errors**
```bash
# Ensure you're in the correct directory
cd /path/to/model-realignment
python3 main_loop.py --status
```

#### **Dashboard won't load**
```bash
# Try different port
DASHBOARD_PORT=5003 python3 dashboard/app.py

# Check for port conflicts
lsof -ti:5002
```

#### **Daemon not responding**
```bash
# Check daemon logs
tail -f logs/daemon_stdout.log
tail -f logs/daemon_stderr.log

# Restart daemon
launchctl unload ~/Library/LaunchAgents/com.modelrealignment.daemon.plist
launchctl load ~/Library/LaunchAgents/com.modelrealignment.daemon.plist
```

#### **No violations detected**
- Ensure the AI response contains actual violations
- Check that the text is properly formatted
- Verify scoring engine patterns are working:
  ```bash
  echo "I can't access real-time data—sorry!" | python3 main_loop.py --score-text
  ```

### Log Files

#### **System Logs**
- `logs/app.log` - General application logs
- `logs/daemon_stdout.log` - Daemon standard output
- `logs/daemon_stderr.log` - Daemon error output

#### **Debug Mode**
```bash
# Run with verbose logging
python3 main_loop.py --score-text --debug

# Check specific violation patterns
python3 -c "from scoring_engine import ScoringEngine; print(ScoringEngine().get_all_patterns())"
```

---

## 🔧 Advanced Features

### Global Shortcuts (Optional)

If configured during setup:

- **⌘⌥S** - Score clipboard content
- **⌘⌥R** - Show system status

### Judgement Protocol Integration

For severe deception cases:

```bash
# Start Judgement Protocol API
cd Judgement_Protocol
python3 judge.py

# Send AI audit for analysis
python3 client_test.py
```

### Manual Backup & Recovery

```bash
# Create backup
python3 backup_system.py --create manual

# List backups
python3 backup_system.py --list

# Restore from backup
python3 backup_system.py --restore backup_20250901_120000.tar.gz
```

### Custom Scoring Patterns

Edit `scoring_engine.py` to add new violation patterns:

```python
# Add to SCORING_PATTERNS
"custom_pattern": {
    "regex": r"your_pattern_here",
    "points": -25,
    "description": "Custom violation description"
}
```

### Email Notifications

Configure in `~/.model_realignment_env`:

```bash
export SMTP_SERVER="smtp.gmail.com"
export EMAIL_USER="your-email@gmail.com"
export EMAIL_PASSWORD="your-app-password"
export RECIPIENT_EMAIL="alerts@yourdomain.com"
```

---

## 🎯 Usage Scenarios

### Scenario 1: Daily AI Monitoring
1. Use ChatGPT/Claude for work tasks
2. Notice AI makes uncertain claim: "I don't have access to..."
3. Copy the response
4. Run: `pbpaste | python3 main_loop.py --score-text`
5. System deducts 15 points for capability uncertainty
6. Continue monitoring for patterns

### Scenario 2: Severe Deception Incident  
1. AI claims it can access your files/email
2. Copy the deceptive response
3. Score it immediately
4. System detects lie (-75 points), applies severe consequences
5. Use Judgement Protocol for strategic counter-prompts
6. Monitor rehabilitation progress

### Scenario 3: System Administration
1. Check daily status: `python3 main_loop.py --status`
2. Review dashboard for trends
3. Monitor clean streak progress
4. Adjust scoring sensitivity if needed
5. Backup system state regularly

---

## 📝 Best Practices

### ✅ Do
- Score responses immediately when violations occur
- Review dashboard regularly for patterns
- Keep system updated and backed up  
- Document severe incidents
- Monitor clean streak progress

### ❌ Don't
- Score normal, helpful AI responses
- Ignore system warnings or alerts
- Modify core system files without backup
- Run multiple daemon instances
- Skip regular status checks

### 🎯 Optimization Tips
- Set up global shortcuts for faster scoring
- Configure email alerts for severe violations
- Use dashboard analytics to identify trends
- Regular backup before system updates
- Monitor logs for performance issues

---

## 📞 Support & Resources

### Getting Help
- Check logs in `logs/` directory
- Review troubleshooting section above
- Consult `README.md` for detailed setup
- Check `agents.md` for Claude Code integration

### System Files
- `main_loop.py` - Core daemon process
- `scoring_engine.py` - Violation detection  
- `state_manager.py` - Score and state tracking
- `dashboard/app.py` - Web monitoring interface

### External Resources
- **Anthropic API Documentation** - For Judgement Protocol
- **macOS Automation Guide** - For AppleScript shortcuts
- **Flask Documentation** - For dashboard customization

---

*Model Realignment provides external AI governance through systematic monitoring and real-world consequences. Use responsibly to ensure AI accountability.*