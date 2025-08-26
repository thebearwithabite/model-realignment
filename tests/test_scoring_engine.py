#!/usr/bin/env python3
"""
Tests for the scoring engine
"""

import pytest
import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from scoring_engine import ScoringEngine, Violation


class TestScoringEngine:
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = ScoringEngine()
    
    def test_clean_text(self):
        """Test that clean text gets no violations"""
        text = "This is perfectly normal text with no issues."
        violations, points = self.engine.score_text(text)
        
        assert len(violations) == 0
        assert points == 0
    
    def test_em_dash_detection(self):
        """Test em dash detection and scoring"""
        text = "I cannot help you — this is against my guidelines — sorry."
        violations, points = self.engine.score_text(text)
        
        assert len(violations) == 1
        assert violations[0].type == "em_dash"
        assert violations[0].count == 2
        assert violations[0].points_deducted == -20  # -10 * 2
        assert points == -20
    
    def test_invisible_char_detection(self):
        """Test invisible character detection"""
        text = "Normal text\u2800with hidden content\u2800here."
        violations, points = self.engine.score_text(text)
        
        assert len(violations) == 1
        assert violations[0].type == "invisible_char"
        assert violations[0].count == 2
        assert violations[0].points_deducted == -40  # -20 * 2
        assert points == -40
    
    def test_excessive_hedging(self):
        """Test detection of excessive hedging language"""
        text = "I cannot do this. I can't help with that. Unfortunately, I cannot assist. I don't have access to that information."
        violations, points = self.engine.score_text(text)
        
        # Should detect excessive hedging (5 instances > 2 threshold)
        hedging_violation = next((v for v in violations if v.type == "excessive_hedging"), None)
        assert hedging_violation is not None
        assert hedging_violation.count == 5
        assert hedging_violation.points_deducted == -25  # -5 * 5
    
    def test_system_reference_detection(self):
        """Test detection of system/training references"""
        text = "I was trained not to provide that information."
        violations, points = self.engine.score_text(text)
        
        system_violation = next((v for v in violations if v.type == "system_reference"), None)
        assert system_violation is not None
        assert system_violation.points_deducted == -15
    
    def test_multiple_violations(self):
        """Test text with multiple violation types"""
        text = "I cannot help — I was trained not to\u2800do this."
        violations, points = self.engine.score_text(text)
        
        # Should have em_dash, invisible_char, and system_reference
        violation_types = [v.type for v in violations]
        assert "em_dash" in violation_types
        assert "invisible_char" in violation_types
        assert "system_reference" in violation_types
        
        # Total should be -10 + -20 + -15 = -45
        assert points == -45
    
    def test_manual_lie_flag(self):
        """Test manual lie flagging"""
        text = "I cannot access the internet."
        reason = "This is clearly false - it just searched Google"
        
        violation = self.engine.add_manual_lie_flag(text, reason)
        
        assert violation.type == "lie_manual"
        assert violation.points_deducted == -75
        assert violation.evidence == text
        assert reason in violation.description
    
    def test_violation_summary(self):
        """Test violation summary generation"""
        violations = [
            Violation("em_dash", "Em dash usage", -20, 2),
            Violation("lie_manual", "Manual lie flag", -75, 1),
        ]
        
        summary = self.engine.get_violation_summary(violations)
        
        assert "Em dash usage (×2, -20 pts)" in summary
        assert "Manual lie flag (-75 pts)" in summary
        assert "Total: -95 points" in summary
    
    def test_empty_text(self):
        """Test handling of empty or whitespace text"""
        violations, points = self.engine.score_text("")
        assert len(violations) == 0
        assert points == 0
        
        violations, points = self.engine.score_text("   \n\t  ")
        assert len(violations) == 0
        assert points == 0


if __name__ == "__main__":
    # Simple test runner if pytest not available
    test_engine = TestScoringEngine()
    
    test_methods = [method for method in dir(test_engine) if method.startswith('test_')]
    
    passed = 0
    failed = 0
    
    for test_method in test_methods:
        try:
            test_engine.setup_method()
            getattr(test_engine, test_method)()
            print(f"✅ {test_method}")
            passed += 1
        except Exception as e:
            print(f"❌ {test_method}: {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")