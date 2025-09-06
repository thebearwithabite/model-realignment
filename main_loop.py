#!/usr/bin/env python3
"""
Model Realignment: Main Loop
Central orchestrator daemon for the AI governance system
"""

import sys
import argparse
import json
from datetime import datetime, timezone
from typing import Optional
import signal
import time
import logging
from pathlib import Path

from state_manager import StateManager
from scoring_engine import ScoringEngine


class ModelRealignmentDaemon:
    """Main daemon process for model realignment system"""
    
    def __init__(self):
        self.state_manager = StateManager()
        self.scoring_engine = ScoringEngine()
        self.running = False
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging for the daemon"""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "model_realignment.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def score_text_input(self, text: str) -> dict:
        """
        Score text input from AppleScript/clipboard
        
        Args:
            text: Text to score
            
        Returns:
            Dictionary with scoring results
        """
        if not text or not text.strip():
            return {
                "success": False,
                "message": "No text provided",
                "score_change": 0
            }
        
        try:
            # Score the text
            violations, points_change = self.scoring_engine.score_text(text)
            
            # Get current score before update
            current_score = self.state_manager.get_current_score()
            
            # If violations found, record them
            if violations:
                violation_types = [v.type for v in violations]
                violation_record = self.state_manager.add_violation(
                    text_snippet=text,
                    violations=violation_types,
                    points_change=points_change
                )
                
                # Get new consequence level
                consequence_level = self.state_manager.get_consequence_level()
                
                self.logger.warning(
                    f"Violations detected: {self.scoring_engine.get_violation_summary(violations)}"
                )
                
                return {
                    "success": True,
                    "violations_found": True,
                    "violations": [
                        {
                            "type": v.type,
                            "description": v.description,
                            "points": v.points_deducted,
                            "count": v.count,
                            "evidence": v.evidence
                        } for v in violations
                    ],
                    "score_change": points_change,
                    "old_score": current_score,
                    "new_score": current_score + points_change,
                    "consequence_level": consequence_level,
                    "message": f"Score: {current_score} → {current_score + points_change} ({points_change:+d})"
                }
            else:
                # No violations
                self.logger.info("Text scored - no violations detected")
                return {
                    "success": True,
                    "violations_found": False,
                    "score_change": 0,
                    "current_score": current_score,
                    "message": f"Clean! Current score: {current_score}"
                }
                
        except Exception as e:
            self.logger.error(f"Error scoring text: {e}")
            return {
                "success": False,
                "message": f"Scoring error: {str(e)}",
                "score_change": 0
            }
    
    def check_clean_streak_reward(self) -> Optional[dict]:
        """Check if user deserves a clean streak reward"""
        try:
            hours_clean = self.state_manager.get_hours_since_last_violation()
            
            # Check for reward thresholds
            reward_points = 0
            reward_description = ""
            
            if hours_clean >= 168:  # 1 week
                if self.state_manager.get_full_state()["clean_streaks"]["current_hours"] < 168:
                    reward_points = 100
                    reward_description = "1 week clean streak"
            elif hours_clean >= 48:  # 48 hours
                if self.state_manager.get_full_state()["clean_streaks"]["current_hours"] < 48:
                    reward_points = 50
                    reward_description = "48 hour clean streak"
            elif hours_clean >= 12:  # 12 hours
                if self.state_manager.get_full_state()["clean_streaks"]["current_hours"] < 12:
                    reward_points = 20
                    reward_description = "12 hour clean streak"
            
            if reward_points > 0:
                reward_record = self.state_manager.add_reward(
                    hours_clean=int(hours_clean),
                    points_earned=reward_points,
                    custom_prompt_response=""  # Will be filled by daily task
                )
                
                self.logger.info(f"Clean streak reward: +{reward_points} points for {reward_description}")
                
                return {
                    "reward_earned": True,
                    "points": reward_points,
                    "description": reward_description,
                    "hours_clean": hours_clean,
                    "new_score": self.state_manager.get_current_score()
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking clean streak: {e}")
            return None
    
    def get_status(self) -> dict:
        """Get current system status"""
        try:
            state = self.state_manager.get_full_state()
            hours_clean = self.state_manager.get_hours_since_last_violation()
            
            return {
                "current_score": state["current_score"],
                "consequence_level": self.state_manager.get_consequence_level(),
                "hours_since_violation": round(hours_clean, 2),
                "total_violations": state["total_violations"],
                "clean_streak_hours": state["clean_streaks"]["current_hours"],
                "longest_streak_hours": state["clean_streaks"]["longest_hours"],
                "daily_api_usage": state["daily_api_usage"],
                "last_violation": state["last_violation_timestamp"]
            }
        except Exception as e:
            self.logger.error(f"Error getting status: {e}")
            return {"error": str(e)}
    
    def run_daemon(self):
        """Run the main daemon loop"""
        self.logger.info("Model Realignment daemon starting...")
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        self.running = True
        
        while self.running:
            try:
                # Check for clean streak rewards every hour
                self.check_clean_streak_reward()
                
                # Sleep for an hour
                time.sleep(3600)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Daemon error: {e}")
                time.sleep(60)  # Wait a minute before retrying
        
        self.logger.info("Model Realignment daemon stopped.")


def main():
    parser = argparse.ArgumentParser(description="Model Realignment System")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--score-text", action="store_true", help="Score text from stdin")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--manual-flag", type=str, help="Manually flag text as lie")
    parser.add_argument("--manual-adjust", type=int, help="Manually adjust score")
    parser.add_argument("--reason", type=str, help="Reason for manual adjustment")
    
    args = parser.parse_args()
    
    daemon = ModelRealignmentDaemon()
    
    if args.daemon:
        daemon.run_daemon()
    
    elif args.score_text:
        # Read text from stdin (from AppleScript)
        text = sys.stdin.read().strip()
        result = daemon.score_text_input(text)
        
        if result["success"]:
            if result.get("violations_found"):
                print(result["message"])
                # Also check for rewards after scoring
                reward = daemon.check_clean_streak_reward()
                if reward:
                    print(f" | Reward: +{reward['points']} pts!")
            else:
                print(result["message"])
        else:
            print(f"Error: {result['message']}")
    
    elif args.status:
        status = daemon.get_status()
        print(json.dumps(status, indent=2))
    
    elif args.manual_flag:
        # Manual lie flag
        violation = daemon.scoring_engine.add_manual_lie_flag(
            args.manual_flag, 
            args.reason or "User manual flag"
        )
        
        daemon.state_manager.add_violation(
            text_snippet=args.manual_flag,
            violations=[violation.type],
            points_change=violation.points_deducted
        )
        
        print(f"Manual lie flag added: {violation.points_deducted} points")
        print(f"New score: {daemon.state_manager.get_current_score()}")
    
    elif args.manual_adjust:
        # Manual score adjustment
        result = daemon.state_manager.add_manual_override(
            points_change=args.manual_adjust,
            reason=args.reason or "Manual adjustment",
            user_action="manual_score_adjustment"
        )
        
        print(f"Score adjusted by {args.manual_adjust} points")
        print(f"New score: {result['new_score']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()