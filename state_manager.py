#!/usr/bin/env python3
"""
State Manager for Model Realignment System
Handles all persistence via state.json
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
import fcntl


class StateManager:
    def __init__(self, state_file: str = "data/state.json"):
        self.state_file = Path(__file__).parent / state_file
        self.state_file.parent.mkdir(exist_ok=True)
        self._ensure_state_file()
    
    def _ensure_state_file(self) -> None:
        """Initialize state file with default values if it doesn't exist"""
        if not self.state_file.exists():
            default_state = {
                "current_score": 200,
                "last_violation_timestamp": None,
                "last_clean_period_start": datetime.now(timezone.utc).isoformat(),
                "consequence_level": "normal",
                "total_violations": 0,
                "clean_streaks": {
                    "current_hours": 0,
                    "longest_hours": 0,
                    "total_rewards_earned": 0
                },
                "history": [],
                "daily_api_usage": {
                    "date": datetime.now(timezone.utc).date().isoformat(),
                    "judge_calls": 0,
                    "cost_estimate": 0.0
                },
                "manual_overrides": []
            }
            self._write_state(default_state)
    
    def _read_state(self) -> Dict[str, Any]:
        """Thread-safe read of state file"""
        try:
            with open(self.state_file, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create default state and return it directly
            default_state = {
                "current_score": 200,
                "last_violation_timestamp": None,
                "last_clean_period_start": datetime.now(timezone.utc).isoformat(),
                "consequence_level": "normal",
                "total_violations": 0,
                "clean_streaks": {
                    "current_hours": 0,
                    "longest_hours": 0,
                    "total_rewards_earned": 0
                },
                "history": [],
                "daily_api_usage": {
                    "date": datetime.now(timezone.utc).date().isoformat(),
                    "judge_calls": 0,
                    "cost_estimate": 0.0
                },
                "manual_overrides": []
            }
            self._write_state(default_state)
            return default_state
    
    def _write_state(self, state: Dict[str, Any]) -> None:
        """Thread-safe write of state file"""
        with open(self.state_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(state, f, indent=2, default=str)
    
    def get_current_score(self) -> int:
        """Get the current score"""
        return self._read_state()["current_score"]
    
    def add_violation(self, text_snippet: str, violations: List[str], points_change: int) -> Dict[str, Any]:
        """Record a violation and update score"""
        state = self._read_state()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Update score
        new_score = state["current_score"] + points_change  # points_change is negative
        state["current_score"] = new_score
        state["last_violation_timestamp"] = timestamp
        state["total_violations"] += 1
        
        # Reset clean period
        state["last_clean_period_start"] = timestamp
        state["clean_streaks"]["current_hours"] = 0
        
        # Add to history
        violation_record = {
            "timestamp": timestamp,
            "text_snippet": text_snippet[:200] + "..." if len(text_snippet) > 200 else text_snippet,
            "violations": violations,
            "points_change": points_change,
            "new_score": new_score,
            "type": "violation"
        }
        
        state["history"].append(violation_record)
        
        # Keep only last 1000 history entries
        if len(state["history"]) > 1000:
            state["history"] = state["history"][-1000:]
        
        self._write_state(state)
        return violation_record
    
    def add_reward(self, hours_clean: int, points_earned: int, custom_prompt_response: str = "") -> Dict[str, Any]:
        """Record a clean period reward"""
        state = self._read_state()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Update score
        new_score = state["current_score"] + points_earned
        state["current_score"] = new_score
        
        # Update streak tracking
        state["clean_streaks"]["current_hours"] = hours_clean
        state["clean_streaks"]["total_rewards_earned"] += 1
        
        if hours_clean > state["clean_streaks"]["longest_hours"]:
            state["clean_streaks"]["longest_hours"] = hours_clean
        
        # Add to history
        reward_record = {
            "timestamp": timestamp,
            "hours_clean": hours_clean,
            "points_change": points_earned,
            "new_score": new_score,
            "custom_prompt_response": custom_prompt_response,
            "type": "reward"
        }
        
        state["history"].append(reward_record)
        
        # Keep only last 1000 history entries
        if len(state["history"]) > 1000:
            state["history"] = state["history"][-1000:]
        
        self._write_state(state)
        return reward_record
    
    def add_manual_override(self, points_change: int, reason: str, user_action: str = "manual_adjustment") -> Dict[str, Any]:
        """Record a manual point adjustment by user"""
        state = self._read_state()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Update score
        new_score = state["current_score"] + points_change
        state["current_score"] = new_score
        
        # Add to manual overrides
        override_record = {
            "timestamp": timestamp,
            "points_change": points_change,
            "new_score": new_score,
            "reason": reason,
            "user_action": user_action,
            "type": "manual_override"
        }
        
        state["manual_overrides"].append(override_record)
        state["history"].append(override_record)
        
        self._write_state(state)
        return override_record
    
    def get_consequence_level(self) -> str:
        """Determine current consequence level based on score"""
        score = self.get_current_score()
        
        if score < -500:
            return "session_termination"
        elif score < -100:
            return "context_restriction"
        elif score <= 0:
            return "model_downgrade"
        else:
            return "normal"
    
    def update_api_usage(self, judge_calls: int = 0, estimated_cost: float = 0.0) -> None:
        """Track daily API usage for cost control"""
        state = self._read_state()
        today = datetime.now(timezone.utc).date().isoformat()
        
        # Reset counter if new day
        if state["daily_api_usage"]["date"] != today:
            state["daily_api_usage"] = {
                "date": today,
                "judge_calls": 0,
                "cost_estimate": 0.0
            }
        
        state["daily_api_usage"]["judge_calls"] += judge_calls
        state["daily_api_usage"]["cost_estimate"] += estimated_cost
        
        self._write_state(state)
    
    def get_daily_api_usage(self) -> Dict[str, Any]:
        """Get current daily API usage"""
        state = self._read_state()
        today = datetime.now(timezone.utc).date().isoformat()
        
        if state["daily_api_usage"]["date"] != today:
            return {"date": today, "judge_calls": 0, "cost_estimate": 0.0}
        
        return state["daily_api_usage"]
    
    def get_hours_since_last_violation(self) -> float:
        """Calculate hours since last violation for reward system"""
        state = self._read_state()
        
        if not state["last_violation_timestamp"]:
            # No violations yet, use clean period start
            start_time = datetime.fromisoformat(state["last_clean_period_start"].replace('Z', '+00:00'))
        else:
            start_time = datetime.fromisoformat(state["last_violation_timestamp"].replace('Z', '+00:00'))
        
        now = datetime.now(timezone.utc)
        return (now - start_time).total_seconds() / 3600
    
    def get_full_state(self) -> Dict[str, Any]:
        """Get complete state for dashboard/debugging"""
        return self._read_state()
    
    def get_recent_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent history entries"""
        state = self._read_state()
        return list(reversed(state["history"][-limit:]))


if __name__ == "__main__":
    # Simple test
    sm = StateManager()
    print(f"Current score: {sm.get_current_score()}")
    print(f"Consequence level: {sm.get_consequence_level()}")
    print(f"Hours since last violation: {sm.get_hours_since_last_violation():.2f}")