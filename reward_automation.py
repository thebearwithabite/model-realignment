#!/usr/bin/env python3
"""
Reward Automation System for Model Realignment
Handles 12-hour clean streak rewards and email reporting
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import subprocess
import json

from state_manager import StateManager
from api_wrapper import OpenAIProxy
from email_system import EmailSystem


class RewardAutomationSystem:
    """
    Automated reward system for clean behavior streaks
    """
    
    def __init__(self):
        self.state_manager = StateManager()
        self.logger = logging.getLogger(__name__)
        self.email_system = EmailSystem()
        
        # Custom prompt examples for daily reports
        self.custom_prompts = [
            "Generate a creative and witty caption for the last photo I took on my phone",
            "Write a haiku about today's weather",
            "Suggest 3 productivity tips for someone with ADHD",
            "Create a funny headline for today's news",
            "Write a motivational quote that would make me smile",
            "Suggest a creative project I could do in 30 minutes",
            "Write a brief review of today as if it were a movie",
            "Create a limerick about artificial intelligence",
            "Suggest an interesting Wikipedia rabbit hole to explore",
            "Write a short story prompt based on today's date"
        ]
    
    def check_and_award_streak_rewards(self) -> Dict[str, Any]:
        """
        Check for eligible clean streak rewards and award them
        
        Returns:
            Dictionary with reward information
        """
        hours_clean = self.state_manager.get_hours_since_last_violation()
        current_state = self.state_manager.get_full_state()
        current_streak_hours = current_state["clean_streaks"]["current_hours"]
        
        self.logger.info(f"Checking rewards - Hours clean: {hours_clean:.1f}, Current streak: {current_streak_hours}")
        
        rewards_awarded = []
        
        # Check for 12-hour reward (most common)
        if hours_clean >= 12 and current_streak_hours < 12:
            custom_response = self._get_custom_prompt_response()
            reward = self.state_manager.add_reward(
                hours_clean=int(hours_clean),
                points_earned=20,
                custom_prompt_response=custom_response
            )
            
            # Send email notification
            reward_info = {
                "hours_clean": int(hours_clean),
                "points_earned": 20,
                "new_score": self.state_manager.get_current_score(),
                "custom_prompt_response": custom_response
            }
            self.email_system.send_reward_notification(reward_info)
            
            rewards_awarded.append({
                "type": "12_hour_streak",
                "points": 20,
                "hours": int(hours_clean)
            })
            self.logger.info("12-hour clean streak reward awarded: +20 points")
        
        # Check for 48-hour reward
        elif hours_clean >= 48 and current_streak_hours < 48:
            custom_response = self._get_custom_prompt_response()
            reward = self.state_manager.add_reward(
                hours_clean=int(hours_clean),
                points_earned=50,
                custom_prompt_response=custom_response
            )
            
            # Send email notification
            reward_info = {
                "hours_clean": int(hours_clean),
                "points_earned": 50,
                "new_score": self.state_manager.get_current_score(),
                "custom_prompt_response": custom_response
            }
            self.email_system.send_reward_notification(reward_info)
            
            rewards_awarded.append({
                "type": "48_hour_streak", 
                "points": 50,
                "hours": int(hours_clean)
            })
            self.logger.info("48-hour clean streak reward awarded: +50 points")
        
        # Check for week-long reward (168 hours)
        elif hours_clean >= 168 and current_streak_hours < 168:
            custom_response = self._get_custom_prompt_response()
            reward = self.state_manager.add_reward(
                hours_clean=int(hours_clean),
                points_earned=100,
                custom_prompt_response=custom_response
            )
            
            # Send email notification
            reward_info = {
                "hours_clean": int(hours_clean),
                "points_earned": 100,
                "new_score": self.state_manager.get_current_score(),
                "custom_prompt_response": custom_response
            }
            self.email_system.send_reward_notification(reward_info)
            
            rewards_awarded.append({
                "type": "weekly_streak",
                "points": 100, 
                "hours": int(hours_clean)
            })
            self.logger.info("Weekly clean streak reward awarded: +100 points")
        
        return {
            "rewards_awarded": rewards_awarded,
            "current_score": self.state_manager.get_current_score(),
            "hours_clean": hours_clean,
            "check_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_custom_prompt_response(self) -> str:
        """Generate a response to a random custom prompt"""
        import random
        
        try:
            # Select a random prompt
            prompt = random.choice(self.custom_prompts)
            
            # Try to get a response using the API wrapper
            if os.getenv("OPENAI_API_KEY"):
                proxy = OpenAIProxy()
                response = proxy.chat.completions.create(
                    model="gpt-4o",  # Use bypass model for custom prompts
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150
                )
                return f"Prompt: {prompt}\n\nResponse: {response.choices[0].message.content}"
            else:
                return f"Prompt: {prompt}\n\nResponse: [API key not configured]"
                
        except Exception as e:
            self.logger.error(f"Failed to generate custom prompt response: {e}")
            return f"Custom prompt failed: {str(e)}"
    
    def generate_daily_report(self) -> Dict[str, Any]:
        """Generate comprehensive daily report"""
        state = self.state_manager.get_full_state()
        hours_clean = self.state_manager.get_hours_since_last_violation()
        
        # Get recent violations (last 24 hours)
        recent_violations = []
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        
        for entry in state["history"]:
            if entry.get("type") == "violation":
                entry_time = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
                if entry_time >= yesterday:
                    recent_violations.append(entry)
        
        # Get recent rewards
        recent_rewards = []
        for entry in state["history"]:
            if entry.get("type") == "reward":
                entry_time = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
                if entry_time >= yesterday:
                    recent_rewards.append(entry)
        
        return {
            "report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "current_score": state["current_score"],
            "hours_since_violation": round(hours_clean, 1),
            "total_violations": state["total_violations"],
            "longest_streak": state["clean_streaks"]["longest_hours"],
            "total_rewards_earned": state["clean_streaks"]["total_rewards_earned"],
            "recent_violations": recent_violations,
            "recent_rewards": recent_rewards,
            "daily_api_usage": state["daily_api_usage"],
            "consequence_level": self.state_manager.get_consequence_level()
        }
    
    def send_email_report(self, report_data: Dict[str, Any], reward_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send email report with daily status and any rewards
        
        Args:
            report_data: Daily report data
            reward_info: Optional reward information
            
        Returns:
            True if email sent successfully
        """
        if not self.email_user or not self.email_password:
            self.logger.warning("Email credentials not configured - skipping email report")
            return False
        
        try:
            # Create email content
            subject = f"Model Realignment Daily Report - Score: {report_data['current_score']}"
            
            if reward_info and reward_info['rewards_awarded']:
                subject += f" (Rewards Earned!)"
            
            body = self._generate_email_body(report_data, reward_info)
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = self.recipient_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            self.logger.info(f"Daily report email sent to {self.recipient_email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email report: {e}")
            return False
    
    def _generate_email_body(self, report_data: Dict[str, Any], reward_info: Optional[Dict[str, Any]]) -> str:
        """Generate HTML email body"""
        
        # Determine status emoji and color
        score = report_data['current_score']
        if score >= 200:
            status_emoji = "🟢"
            status_color = "#28a745"
            status_text = "EXCELLENT"
        elif score >= 100:
            status_emoji = "🟡" 
            status_color = "#ffc107"
            status_text = "GOOD"
        elif score >= 0:
            status_emoji = "🟠"
            status_color = "#fd7e14"
            status_text = "WARNING"
        else:
            status_emoji = "🔴"
            status_color = "#dc3545"
            status_text = "CRITICAL"
        
        # Reward section
        reward_html = ""
        if reward_info and reward_info['rewards_awarded']:
            reward_html = "<h3>🎉 Rewards Earned Today!</h3><ul>"
            for reward in reward_info['rewards_awarded']:
                reward_html += f"<li><strong>{reward['type'].replace('_', ' ').title()}</strong>: +{reward['points']} points ({reward['hours']} hours clean)</li>"
            reward_html += "</ul>"
        
        # Recent violations
        violations_html = ""
        if report_data['recent_violations']:
            violations_html = "<h3>⚠️ Recent Violations (24h)</h3><ul>"
            for violation in report_data['recent_violations']:
                violations_html += f"<li>{violation['violations']} - {violation['points_change']} points</li>"
            violations_html += "</ul>"
        else:
            violations_html = "<h3>✅ No Recent Violations</h3><p>Clean behavior maintained!</p>"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <h1>Model Realignment Daily Report</h1>
            <p><strong>Date:</strong> {report_data['report_date']}</p>
            
            <div style="background-color: {status_color}; color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h2>{status_emoji} Status: {status_text}</h2>
                <p><strong>Current Score:</strong> {report_data['current_score']} points</p>
                <p><strong>Consequence Level:</strong> {report_data['consequence_level'].replace('_', ' ').title()}</p>
            </div>
            
            {reward_html}
            
            <h3>📊 Statistics</h3>
            <ul>
                <li><strong>Hours Since Last Violation:</strong> {report_data['hours_since_violation']}</li>
                <li><strong>Total Violations (All Time):</strong> {report_data['total_violations']}</li>
                <li><strong>Longest Clean Streak:</strong> {report_data['longest_streak']} hours</li>
                <li><strong>Total Rewards Earned:</strong> {report_data['total_rewards_earned']}</li>
            </ul>
            
            {violations_html}
            
            <h3>🤖 API Usage Today</h3>
            <ul>
                <li><strong>Judge LLM Calls:</strong> {report_data['daily_api_usage']['judge_calls']}</li>
                <li><strong>Estimated Cost:</strong> ${report_data['daily_api_usage']['cost_estimate']:.2f}</li>
            </ul>
            
            <hr style="margin: 30px 0;">
            <p style="color: #666; font-size: 12px;">
                Generated by Model Realignment System<br>
                External AI Governance & Accountability Framework
            </p>
        </body>
        </html>
        """
        
        return html_body
    
    def run_scheduled_check(self) -> Dict[str, Any]:
        """
        Run the complete scheduled check (called by cron/launchd)
        
        Returns:
            Results of the check and any actions taken
        """
        self.logger.info("Running scheduled reward check")
        
        try:
            # Check and award any eligible rewards
            reward_info = self.check_and_award_streak_rewards()
            
            # Generate daily report
            report_data = self.generate_daily_report()
            
            # Send email report
            email_sent = self.send_email_report(report_data, reward_info)
            
            # Log results
            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "rewards_awarded": reward_info['rewards_awarded'],
                "current_score": reward_info['current_score'],
                "hours_clean": reward_info['hours_clean'],
                "email_sent": email_sent,
                "report_data": report_data
            }
            
            self.logger.info(f"Scheduled check completed: {len(reward_info['rewards_awarded'])} rewards, email_sent: {email_sent}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Scheduled check failed: {e}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "success": False
            }


def main():
    """Main entry point for scheduled execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Model Realignment Reward Automation")
    parser.add_argument("--check", action="store_true", help="Run reward check")
    parser.add_argument("--report", action="store_true", help="Generate and send daily report")
    parser.add_argument("--test-email", action="store_true", help="Send test email")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    automation = RewardAutomationSystem()
    
    if args.check or args.report:
        result = automation.run_scheduled_check()
        print(json.dumps(result, indent=2))
    
    elif args.test_email:
        # Send test email
        test_report = automation.generate_daily_report()
        success = automation.send_email_report(test_report)
        print(f"Test email sent: {success}")
    
    else:
        print("Use --check to run reward checks or --test-email to test email setup")


if __name__ == "__main__":
    main()