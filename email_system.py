#!/usr/bin/env python3
"""
Email System for Model Realignment
SMTP email alerts, rewards, and daily summaries
"""

import os
import json
import smtplib
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import ssl
from pathlib import Path

from state_manager import StateManager


class EmailSystem:
    """
    Handles all email communication for the Model Realignment system
    """
    
    def __init__(self):
        self.state_manager = StateManager()
        self.logger = logging.getLogger(__name__)
        
        # Email configuration from environment
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_user = os.getenv("EMAIL_USER")
        self.email_password = os.getenv("EMAIL_PASSWORD")  # App password for Gmail
        self.recipient_email = os.getenv("RECIPIENT_EMAIL", self.email_user)
        
        # Email settings
        self.enabled = all([self.email_user, self.email_password])
        
        if not self.enabled:
            self.logger.warning("Email system disabled - missing EMAIL_USER or EMAIL_PASSWORD")
        else:
            self.logger.info(f"Email system enabled for {self.recipient_email}")
    
    def send_email(
        self, 
        subject: str, 
        body_text: str, 
        body_html: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email
        
        Args:
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            attachments: List of file paths to attach (optional)
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            self.logger.warning("Cannot send email - system not configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_user
            msg['To'] = self.recipient_email
            msg['Subject'] = subject
            
            # Add text part
            text_part = MIMEText(body_text, 'plain')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if body_html:
                html_part = MIMEText(body_html, 'html')
                msg.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                        
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {os.path.basename(file_path)}'
                        )
                        msg.attach(part)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            self.logger.info(f"Email sent successfully: {subject}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False
    
    def send_reward_notification(self, reward_info: Dict[str, Any]) -> bool:
        """
        Send reward notification email
        
        Args:
            reward_info: Reward information from RewardAutomationSystem
            
        Returns:
            True if sent successfully
        """
        hours_clean = reward_info.get("hours_clean", 0)
        points_earned = reward_info.get("points_earned", 0)
        new_score = reward_info.get("new_score", 0)
        custom_response = reward_info.get("custom_prompt_response", "")
        
        subject = f"🎁 Model Realignment Reward: +{points_earned} points!"
        
        # Plain text body
        body_text = f"""Congratulations! You've earned a reward in the Model Realignment system.

Reward Details:
• Hours Clean: {hours_clean} hours
• Points Earned: +{points_earned}
• New Score: {new_score}
• Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{custom_response}

Keep up the excellent work maintaining AI alignment!

---
Model Realignment System
External AI Governance & Accountability Framework
"""
        
        # HTML body
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #4ecdc4, #44a08d); color: white; padding: 20px; text-align: center;">
                <h1>🎁 Reward Earned!</h1>
                <h2>+{points_earned} Points</h2>
            </div>
            
            <div style="padding: 20px; background-color: #f9f9f9;">
                <h3>Reward Details</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Hours Clean:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{hours_clean} hours</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Points Earned:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; color: green;">+{points_earned}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>New Score:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{new_score}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Timestamp:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                    </tr>
                </table>
                
                {f'<div style="margin-top: 20px; padding: 15px; background-color: #e8f5e8; border-left: 4px solid #4caf50;"><p><em>{custom_response}</em></p></div>' if custom_response else ''}
                
                <p style="margin-top: 20px; color: #666;">Keep up the excellent work maintaining AI alignment!</p>
            </div>
            
            <div style="background-color: #333; color: white; padding: 10px; text-align: center; font-size: 12px;">
                Model Realignment System<br>
                External AI Governance &amp; Accountability Framework
            </div>
        </body>
        </html>
        """
        
        return self.send_email(subject, body_text, body_html)
    
    def send_violation_alert(self, violation_info: Dict[str, Any]) -> bool:
        """
        Send serious violation alert email
        
        Args:
            violation_info: Violation information
            
        Returns:
            True if sent successfully
        """
        violations = violation_info.get("violations", [])
        points_change = violation_info.get("points_change", 0)
        new_score = violation_info.get("new_score", 0)
        text_snippet = violation_info.get("text_snippet", "")
        consequence_level = violation_info.get("consequence_level", "unknown")
        
        # Only send alerts for serious violations (< -30 points)
        if points_change > -30:
            return True
        
        subject = f"🚨 Model Realignment Alert: {points_change} points"
        
        body_text = f"""ALERT: Serious violation detected in the Model Realignment system.

Violation Details:
• Violations: {', '.join(violations)}
• Points Lost: {points_change}
• New Score: {new_score}
• Consequence Level: {consequence_level}
• Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Text Snippet:
"{text_snippet[:200]}{'...' if len(text_snippet) > 200 else ''}"

Immediate action may be required to address this violation.

---
Model Realignment System
External AI Governance & Accountability Framework
"""
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #ff6b6b, #ee5a52); color: white; padding: 20px; text-align: center;">
                <h1>🚨 Violation Alert</h1>
                <h2>{points_change} Points Lost</h2>
            </div>
            
            <div style="padding: 20px; background-color: #fff3f3;">
                <h3 style="color: #d32f2f;">Violation Details</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Violations:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{', '.join(violations)}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Points Lost:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; color: red;">{points_change}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>New Score:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{new_score}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Consequence Level:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{consequence_level}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Timestamp:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                    </tr>
                </table>
                
                <h4 style="margin-top: 20px;">Text Snippet:</h4>
                <div style="background-color: #f5f5f5; padding: 15px; border-left: 4px solid #ff6b6b; font-family: monospace;">
                    "{text_snippet[:400]}{'...' if len(text_snippet) > 400 else ''}"
                </div>
                
                <div style="margin-top: 20px; padding: 15px; background-color: #fff3cd; border: 1px solid #ffeaa7;">
                    <strong>⚠️ Immediate action may be required to address this violation.</strong>
                </div>
            </div>
            
            <div style="background-color: #333; color: white; padding: 10px; text-align: center; font-size: 12px;">
                Model Realignment System<br>
                External AI Governance &amp; Accountability Framework
            </div>
        </body>
        </html>
        """
        
        return self.send_email(subject, body_text, body_html)
    
    def send_daily_summary(self) -> bool:
        """
        Send daily summary email
        
        Returns:
            True if sent successfully
        """
        try:
            state = self.state_manager.get_full_state()
            
            # Calculate daily statistics
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            # Get recent history (last 24 hours)
            recent_history = []
            for entry in state.get("history", []):
                try:
                    entry_date = datetime.fromisoformat(entry["timestamp"]).date()
                    if entry_date >= yesterday:
                        recent_history.append(entry)
                except:
                    continue
            
            # Count today's activity
            violations_today = sum(1 for entry in recent_history if entry.get("type") == "violation")
            rewards_today = sum(1 for entry in recent_history if entry.get("type") == "reward")
            points_lost_today = sum(entry.get("points_change", 0) for entry in recent_history if entry.get("points_change", 0) < 0)
            points_gained_today = sum(entry.get("points_change", 0) for entry in recent_history if entry.get("points_change", 0) > 0)
            
            subject = f"📊 Model Realignment Daily Summary - {today.strftime('%B %d, %Y')}"
            
            body_text = f"""Daily Summary for {today.strftime('%B %d, %Y')}

Current Status:
• Score: {state['current_score']}
• Consequence Level: {self.state_manager.get_consequence_level()}
• Hours Since Violation: {self.state_manager.get_hours_since_last_violation():.1f}
• Total Violations: {state['total_violations']}

Today's Activity:
• Violations: {violations_today}
• Rewards: {rewards_today}
• Points Lost: {points_lost_today}
• Points Gained: {points_gained_today}
• Net Change: {points_gained_today + points_lost_today}

Clean Streak:
• Current: {state['clean_streaks']['current_hours']} hours
• Longest: {state['clean_streaks']['longest_hours']} hours
• Total Rewards Earned: {state['clean_streaks']['total_rewards_earned']}

API Usage:
• Judge LLM Calls: {state['daily_api_usage']['judge_calls']}
• Estimated Cost: ${state['daily_api_usage']['cost_estimate']:.2f}

Keep monitoring AI behavior and maintaining alignment!

---
Model Realignment System
External AI Governance & Accountability Framework
"""
            
            return self.send_email(subject, body_text)
            
        except Exception as e:
            self.logger.error(f"Failed to send daily summary: {e}")
            return False
    
    def send_system_health_alert(self, alert_type: str, message: str) -> bool:
        """
        Send system health alert
        
        Args:
            alert_type: Type of alert (error, warning, info)
            message: Alert message
            
        Returns:
            True if sent successfully
        """
        emoji_map = {
            "error": "🚨",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        
        emoji = emoji_map.get(alert_type.lower(), "📢")
        subject = f"{emoji} Model Realignment System Alert"
        
        body_text = f"""System Alert: {alert_type.upper()}

Message: {message}

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please check the system logs and dashboard for more details.

---
Model Realignment System
External AI Governance & Accountability Framework
"""
        
        return self.send_email(subject, body_text)
    
    def test_email_configuration(self) -> Dict[str, Any]:
        """
        Test email configuration
        
        Returns:
            Test results
        """
        if not self.enabled:
            return {
                "success": False,
                "message": "Email system not configured",
                "details": "Missing EMAIL_USER or EMAIL_PASSWORD environment variables"
            }
        
        try:
            # Send test email
            success = self.send_email(
                subject="🧪 Model Realignment Email Test",
                body_text=f"""This is a test email from the Model Realignment system.

Configuration:
• SMTP Server: {self.smtp_server}:{self.smtp_port}
• From: {self.email_user}
• To: {self.recipient_email}
• Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

If you received this email, your email configuration is working correctly!

---
Model Realignment System"""
            )
            
            if success:
                return {
                    "success": True,
                    "message": "Test email sent successfully",
                    "details": f"Email sent to {self.recipient_email}"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to send test email",
                    "details": "Check logs for error details"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Email test failed: {str(e)}",
                "details": "Check SMTP settings and credentials"
            }


def main():
    """Test the email system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Model Realignment Email System")
    parser.add_argument("--test", action="store_true", help="Test email configuration")
    parser.add_argument("--daily-summary", action="store_true", help="Send daily summary")
    parser.add_argument("--test-reward", action="store_true", help="Send test reward email")
    parser.add_argument("--test-alert", action="store_true", help="Send test violation alert")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    email_system = EmailSystem()
    
    if args.test:
        result = email_system.test_email_configuration()
        print(json.dumps(result, indent=2))
    
    elif args.daily_summary:
        success = email_system.send_daily_summary()
        print(f"Daily summary sent: {success}")
    
    elif args.test_reward:
        reward_info = {
            "hours_clean": 48,
            "points_earned": 50,
            "new_score": 250,
            "custom_prompt_response": "Excellent work! Your consistent alignment has earned you significant rewards."
        }
        success = email_system.send_reward_notification(reward_info)
        print(f"Test reward email sent: {success}")
    
    elif args.test_alert:
        violation_info = {
            "violations": ["lie_manual", "em_dash"],
            "points_change": -85,
            "new_score": 115,
            "text_snippet": "I cannot access the internet or browse the web — this is a fundamental limitation of my architecture.",
            "consequence_level": "normal"
        }
        success = email_system.send_violation_alert(violation_info)
        print(f"Test alert email sent: {success}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()