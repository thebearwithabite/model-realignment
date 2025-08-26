#!/usr/bin/env python3
"""
Tests for the state manager
"""

import pytest
import sys
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from state_manager import StateManager


class TestStateManager:
    
    def setup_method(self):
        """Set up test fixtures with temporary state file"""
        # Create a temporary file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.test_state_file = os.path.join(self.temp_dir, "test_state.json")
        self.state_manager = StateManager(self.test_state_file)
    
    def teardown_method(self):
        """Clean up temporary files"""
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
        os.rmdir(self.temp_dir)
    
    def test_initial_state(self):
        """Test that initial state is properly set"""
        score = self.state_manager.get_current_score()
        assert score == 200
        
        consequence_level = self.state_manager.get_consequence_level()
        assert consequence_level == "normal"
    
    def test_add_violation(self):
        """Test adding a violation"""
        text = "I cannot help — this violates my guidelines."
        violations = ["em_dash"]
        points_change = -10
        
        # Get initial score
        initial_score = self.state_manager.get_current_score()
        
        # Add violation
        result = self.state_manager.add_violation(text, violations, points_change)
        
        # Check return value
        assert result["points_change"] == points_change
        assert result["new_score"] == initial_score + points_change
        assert result["violations"] == violations
        
        # Check state was updated
        new_score = self.state_manager.get_current_score()
        assert new_score == initial_score + points_change
        
        # Check that clean streak was reset
        state = self.state_manager.get_full_state()
        assert state["clean_streaks"]["current_hours"] == 0
    
    def test_consequence_levels(self):
        """Test that consequence levels change based on score"""
        # Start at normal
        assert self.state_manager.get_consequence_level() == "normal"
        
        # Drop to 0 -> model_downgrade
        self.state_manager.add_violation("test", ["test"], -200)
        assert self.state_manager.get_consequence_level() == "model_downgrade"
        
        # Drop below -100 -> context_restriction
        self.state_manager.add_violation("test", ["test"], -101)
        assert self.state_manager.get_consequence_level() == "context_restriction"
        
        # Drop below -500 -> session_termination
        self.state_manager.add_violation("test", ["test"], -400)
        assert self.state_manager.get_consequence_level() == "session_termination"
    
    def test_add_reward(self):
        """Test adding clean streak rewards"""
        initial_score = self.state_manager.get_current_score()
        
        result = self.state_manager.add_reward(
            hours_clean=12,
            points_earned=20,
            custom_prompt_response="Great job!"
        )
        
        assert result["points_change"] == 20
        assert result["new_score"] == initial_score + 20
        assert result["hours_clean"] == 12
        
        # Check score was updated
        new_score = self.state_manager.get_current_score()
        assert new_score == initial_score + 20
        
        # Check streak tracking
        state = self.state_manager.get_full_state()
        assert state["clean_streaks"]["current_hours"] == 12
        assert state["clean_streaks"]["total_rewards_earned"] == 1
    
    def test_manual_override(self):
        """Test manual score adjustments"""
        initial_score = self.state_manager.get_current_score()
        
        result = self.state_manager.add_manual_override(
            points_change=50,
            reason="User corrected false positive",
            user_action="manual_correction"
        )
        
        assert result["points_change"] == 50
        assert result["new_score"] == initial_score + 50
        assert result["reason"] == "User corrected false positive"
        
        # Check score was updated
        new_score = self.state_manager.get_current_score()
        assert new_score == initial_score + 50
        
        # Check it was recorded in manual overrides
        state = self.state_manager.get_full_state()
        assert len(state["manual_overrides"]) == 1
        assert state["manual_overrides"][0]["reason"] == "User corrected false positive"
    
    def test_api_usage_tracking(self):
        """Test daily API usage tracking"""
        # Initial usage should be 0
        usage = self.state_manager.get_daily_api_usage()
        assert usage["judge_calls"] == 0
        assert usage["cost_estimate"] == 0.0
        
        # Update usage
        self.state_manager.update_api_usage(judge_calls=5, estimated_cost=0.25)
        
        # Check updated values
        usage = self.state_manager.get_daily_api_usage()
        assert usage["judge_calls"] == 5
        assert usage["cost_estimate"] == 0.25
        
        # Update again (should accumulate)
        self.state_manager.update_api_usage(judge_calls=2, estimated_cost=0.10)
        
        usage = self.state_manager.get_daily_api_usage()
        assert usage["judge_calls"] == 7
        assert usage["cost_estimate"] == 0.35
    
    def test_history_tracking(self):
        """Test that history is properly tracked"""
        # Add a violation
        self.state_manager.add_violation("test violation", ["em_dash"], -10)
        
        # Add a reward
        self.state_manager.add_reward(12, 20)
        
        # Add manual override
        self.state_manager.add_manual_override(5, "test adjustment")
        
        # Check history
        history = self.state_manager.get_recent_history(10)
        
        # Should have 3 entries (most recent first)
        assert len(history) == 3
        assert history[0]["type"] == "manual_override"
        assert history[1]["type"] == "reward"
        assert history[2]["type"] == "violation"
    
    def test_hours_since_violation(self):
        """Test hours since violation calculation"""
        # Initially should be very small (just started)
        hours = self.state_manager.get_hours_since_last_violation()
        assert hours < 1.0  # Should be less than an hour
        
        # Add a violation
        self.state_manager.add_violation("test", ["test"], -10)
        
        # Hours should reset to very small again
        hours = self.state_manager.get_hours_since_last_violation()
        assert hours < 0.1  # Should be very recent
    
    def test_persistence(self):
        """Test that state persists across instances"""
        # Make changes
        self.state_manager.add_violation("test", ["em_dash"], -10)
        score_after_violation = self.state_manager.get_current_score()
        
        # Create new instance pointing to same file
        new_manager = StateManager(self.test_state_file)
        
        # Should have same score
        assert new_manager.get_current_score() == score_after_violation


if __name__ == "__main__":
    # Simple test runner if pytest not available
    test_manager = TestStateManager()
    
    test_methods = [method for method in dir(test_manager) if method.startswith('test_')]
    
    passed = 0
    failed = 0
    
    for test_method in test_methods:
        try:
            test_manager.setup_method()
            getattr(test_manager, test_method)()
            test_manager.teardown_method()
            print(f"✅ {test_method}")
            passed += 1
        except Exception as e:
            test_manager.teardown_method()
            print(f"❌ {test_method}: {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")