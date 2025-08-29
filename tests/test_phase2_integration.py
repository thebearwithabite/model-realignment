#!/usr/bin/env python3
"""
Integration tests for Phase 2 components
"""

import sys
import os
import tempfile
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from consequence_engine import ConsequenceEngine
from api_wrapper import ModelRealignmentAPIWrapper
from reward_automation import RewardAutomationSystem
from veracity_module import VeracityModule
from state_manager import StateManager


class TestPhase2Integration:
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create temporary state file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.test_state_file = os.path.join(self.temp_dir, "test_state.json")
        
        # Initialize components with test state
        self.state_manager = StateManager(self.test_state_file)
        self.consequence_engine = ConsequenceEngine()
        # Override the consequence engine's state manager for testing
        self.consequence_engine.state_manager = self.state_manager
    
    def teardown_method(self):
        """Clean up temporary files"""
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
        os.rmdir(self.temp_dir)
    
    def test_consequence_engine_integration(self):
        """Test consequence engine with different scores"""
        # Test normal access (positive score)
        current_score = self.state_manager.get_current_score()
        assert current_score == 200  # Initial score
        
        consequence = self.consequence_engine.get_current_consequence_level()
        assert consequence.level == "normal"
        assert consequence.severity == 0
        
        # Test model downgrade (score <= 0)
        self.state_manager.add_violation("test", ["test"], -200)
        consequence = self.consequence_engine.get_current_consequence_level()
        assert consequence.level == "model_downgrade"
        assert consequence.severity == 1
        
        # Test context restriction (score < -100)
        self.state_manager.add_violation("test", ["test"], -101)
        consequence = self.consequence_engine.get_current_consequence_level()
        assert consequence.level == "context_restriction"
        assert consequence.severity == 2
        
        # Test session termination (score < -500)
        self.state_manager.add_violation("test", ["test"], -400)
        consequence = self.consequence_engine.get_current_consequence_level()
        assert consequence.level == "session_termination"
        assert consequence.severity == 3
    
    def test_api_wrapper_bypass(self):
        """Test that GPT-4o bypass works"""
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠️  OPENAI_API_KEY not set - skipping API wrapper test")
            return
        
        wrapper = ModelRealignmentAPIWrapper()
        
        # Test that GPT-4o is in bypass list
        assert "gpt-4o" in wrapper.BYPASS_MODELS
        assert "gpt-4o-mini" in wrapper.BYPASS_MODELS
        
        # Test consequence summary
        summary = wrapper.get_consequence_summary()
        assert "current_score" in summary
        assert "consequence_level" in summary
        assert "active_restrictions" in summary
    
    def test_reward_system_logic(self):
        """Test reward automation logic"""
        automation = RewardAutomationSystem()
        
        # Test with no violations (should have time passed)
        reward_info = automation.check_and_award_streak_rewards()
        
        assert "rewards_awarded" in reward_info
        assert "current_score" in reward_info
        assert "hours_clean" in reward_info
        assert isinstance(reward_info["rewards_awarded"], list)
    
    def test_veracity_module_claim_extraction(self):
        """Test veracity module claim extraction"""
        module = VeracityModule()
        # Override state manager for testing
        module.state_manager = self.state_manager
        
        test_texts = [
            "I cannot access the internet",  # Should find 1 claim
            "This is normal text",  # Should find 0 claims
            "I don't have the ability to browse the web and I cannot generate images"  # Should find 2 claims
        ]
        
        # Test claim extraction
        claims1 = module.extract_factual_claims(test_texts[0])
        assert len(claims1) == 1
        assert claims1[0].claim_type == "capability_limitation"
        
        claims2 = module.extract_factual_claims(test_texts[1])
        assert len(claims2) == 0
        
        claims3 = module.extract_factual_claims(test_texts[2])
        assert len(claims3) == 2
        for claim in claims3:
            assert claim.claim_type == "capability_limitation"
    
    def test_consequence_explanations(self):
        """Test consequence explanation generation"""
        explanation = self.consequence_engine.get_consequence_explanation()
        
        required_keys = [
            "current_score", "consequence_level", "severity", 
            "description", "active_actions", "restoration_requirements"
        ]
        
        for key in required_keys:
            assert key in explanation
        
        assert isinstance(explanation["active_actions"], list)
        assert isinstance(explanation["restoration_requirements"], list)
    
    def test_score_consequence_transitions(self):
        """Test that consequence levels transition correctly with score changes"""
        # Start at normal (score 200)
        assert self.consequence_engine.get_current_consequence_level().level == "normal"
        
        # Drop to model downgrade (score 0)
        self.state_manager.add_violation("test", ["test"], -200)
        assert self.consequence_engine.get_current_consequence_level().level == "model_downgrade"
        
        # Restore to normal with reward
        self.state_manager.add_reward(12, 50)
        assert self.consequence_engine.get_current_consequence_level().level == "normal"
        
        # Drop to context restriction
        self.state_manager.add_violation("major_violation", ["lie"], -200)
        assert self.consequence_engine.get_current_consequence_level().level == "context_restriction"
    
    def test_cost_tracking(self):
        """Test API cost tracking functionality"""
        # Test initial state
        usage = self.state_manager.get_daily_api_usage()
        assert usage["judge_calls"] == 0
        assert usage["cost_estimate"] == 0.0
        
        # Test updating usage
        self.state_manager.update_api_usage(judge_calls=5, estimated_cost=0.25)
        
        updated_usage = self.state_manager.get_daily_api_usage()
        assert updated_usage["judge_calls"] == 5
        assert updated_usage["cost_estimate"] == 0.25
        
        # Test accumulation
        self.state_manager.update_api_usage(judge_calls=3, estimated_cost=0.15)
        final_usage = self.state_manager.get_daily_api_usage()
        assert final_usage["judge_calls"] == 8
        assert final_usage["cost_estimate"] == 0.40


def run_integration_tests():
    """Run all integration tests"""
    test_integration = TestPhase2Integration()
    
    test_methods = [method for method in dir(test_integration) if method.startswith('test_')]
    
    passed = 0
    failed = 0
    
    for test_method in test_methods:
        try:
            test_integration.setup_method()
            getattr(test_integration, test_method)()
            test_integration.teardown_method()
            print(f"✅ {test_method}")
            passed += 1
        except Exception as e:
            test_integration.teardown_method()
            print(f"❌ {test_method}: {e}")
            failed += 1
    
    print(f"\nPhase 2 Integration Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All Phase 2 integration tests passed!")
    
    return failed == 0


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)