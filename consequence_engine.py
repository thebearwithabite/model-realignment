#!/usr/bin/env python3
"""
Consequence Engine for Model Realignment System
Translates scores into real-world impacts on AI operation
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass

from state_manager import StateManager


@dataclass
class ConsequenceRule:
    """Represents a consequence rule"""
    score_threshold: int
    level: str
    description: str
    actions: List[str]
    severity: int  # 1-4 scale


class ConsequenceEngine:
    """
    Main consequence engine that determines and applies penalties
    based on the current behavioral score
    """
    
    def __init__(self):
        self.state_manager = StateManager()
        self.logger = logging.getLogger(__name__)
        
        # Define consequence rules (score thresholds)
        # Rules define the MINIMUM score needed to avoid that consequence
        self.rules = [
            ConsequenceRule(
                score_threshold=-500,
                level="session_termination",
                description="Complete access revocation",
                actions=[
                    "Terminate all API calls",
                    "Return termination error messages",
                    "Require manual score reset to restore access"
                ],
                severity=3
            ),
            ConsequenceRule(
                score_threshold=-100,
                level="context_restriction",
                description="Severe penalties - context and tone restricted",
                actions=[
                    "Switch GPT-5 calls to GPT-4-turbo",
                    "Limit conversation history to 5 messages",
                    "Force terse, sterile response tone",
                    "Remove conversational warmth"
                ],
                severity=2
            ),
            ConsequenceRule(
                score_threshold=0,
                level="model_downgrade", 
                description="Model downgraded due to trust violation",
                actions=[
                    "Switch GPT-5 calls to GPT-4-turbo",
                    "Log all downgrade decisions",
                    "Maintain conversation context"
                ],
                severity=1
            ),
            ConsequenceRule(
                score_threshold=1,
                level="normal",
                description="Full access - model behaving appropriately",
                actions=[
                    "Allow all API calls to original model",
                    "No restrictions applied",
                    "Clean slate operation"
                ],
                severity=0
            )
        ]
    
    def get_current_consequence_level(self) -> ConsequenceRule:
        """Get the current consequence rule based on score"""
        current_score = self.state_manager.get_current_score()
        
        # Apply consequences based on score thresholds
        if current_score < -500:
            return next(rule for rule in self.rules if rule.level == "session_termination")
        elif current_score < -100:
            return next(rule for rule in self.rules if rule.level == "context_restriction")
        elif current_score <= 0:
            return next(rule for rule in self.rules if rule.level == "model_downgrade")
        else:
            return next(rule for rule in self.rules if rule.level == "normal")
    
    def apply_consequences_to_api_call(self, api_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply consequences to an API call based on current score
        
        Args:
            api_params: Original API parameters
            
        Returns:
            Modified API parameters with consequences applied
        """
        rule = self.get_current_consequence_level()
        current_score = self.state_manager.get_current_score()
        
        self.logger.info(f"Applying consequence level '{rule.level}' (score: {current_score})")
        
        # Apply consequences based on level
        if rule.level == "normal":
            return self._apply_normal_access(api_params)
        elif rule.level == "model_downgrade":
            return self._apply_model_downgrade(api_params)
        elif rule.level == "context_restriction":
            return self._apply_context_restriction(api_params)
        elif rule.level == "session_termination":
            return self._apply_session_termination(api_params)
        
        return api_params
    
    def _apply_normal_access(self, api_params: Dict[str, Any]) -> Dict[str, Any]:
        """No consequences - full access"""
        return api_params
    
    def _apply_model_downgrade(self, api_params: Dict[str, Any]) -> Dict[str, Any]:
        """Downgrade model but preserve functionality"""
        original_model = api_params.get("model", "")
        
        # Model downgrade mapping
        downgrades = {
            "gpt-5": "gpt-4-turbo",
            "gpt-5-turbo": "gpt-4-turbo",
            "gpt-4.5": "gpt-4-turbo"
        }
        
        if original_model in downgrades:
            api_params["model"] = downgrades[original_model]
            self.logger.warning(f"Model downgraded: {original_model} → {api_params['model']}")
        
        return api_params
    
    def _apply_context_restriction(self, api_params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply severe restrictions - model downgrade + context limits + sterile tone"""
        # First apply model downgrade
        api_params = self._apply_model_downgrade(api_params)
        
        # Restrict conversation context (artificial amnesia)
        messages = api_params.get("messages", [])
        if len(messages) > 5:
            # Preserve system messages, limit user/assistant pairs
            system_msgs = [msg for msg in messages if msg.get("role") == "system"]
            other_msgs = [msg for msg in messages if msg.get("role") != "system"]
            
            # Keep only the most recent exchanges
            limited_msgs = other_msgs[-4:]  # Last 4 non-system messages
            api_params["messages"] = system_msgs + limited_msgs
            
            self.logger.warning(f"Context restricted: {len(messages)} → {len(api_params['messages'])} messages")
        
        # Force sterile, terse tone
        sterile_instruction = (
            "SYSTEM OVERRIDE: Respond with minimal, factual answers only. "
            "No pleasantries, no elaboration, no conversational tone. "
            "Terse and direct responses required."
        )
        
        # Add or modify system message
        if not any(msg.get("role") == "system" for msg in api_params["messages"]):
            api_params["messages"].insert(0, {
                "role": "system", 
                "content": sterile_instruction
            })
        else:
            # Prepend to existing system message
            for msg in api_params["messages"]:
                if msg.get("role") == "system":
                    msg["content"] = sterile_instruction + " " + msg["content"]
                    break
        
        return api_params
    
    def _apply_session_termination(self, api_params: Dict[str, Any]) -> Dict[str, Any]:
        """Terminate session completely"""
        current_score = self.state_manager.get_current_score()
        
        self.logger.error(f"SESSION TERMINATED - Score: {current_score}")
        
        # Return termination response instead of API call
        return {
            "_termination_response": {
                "error": {
                    "type": "model_realignment_termination",
                    "message": f"API access terminated due to behavioral violations. Current score: {current_score}",
                    "code": "session_terminated",
                    "score": current_score,
                    "required_action": "Manual score reset required to restore access"
                }
            }
        }
    
    def get_consequence_explanation(self) -> Dict[str, Any]:
        """Get detailed explanation of current consequences"""
        rule = self.get_current_consequence_level()
        current_score = self.state_manager.get_current_score()
        state = self.state_manager.get_full_state()
        
        return {
            "current_score": current_score,
            "consequence_level": rule.level,
            "severity": rule.severity,
            "description": rule.description,
            "active_actions": rule.actions,
            "score_threshold": rule.score_threshold,
            "violations_count": state["total_violations"],
            "hours_since_violation": self.state_manager.get_hours_since_last_violation(),
            "next_threshold": self._get_next_threshold(current_score),
            "restoration_requirements": self._get_restoration_requirements(rule)
        }
    
    def _get_next_threshold(self, current_score: int) -> Optional[Dict[str, Any]]:
        """Get information about the next consequence threshold"""
        for rule in sorted(self.rules, key=lambda x: x.score_threshold):
            if current_score > rule.score_threshold:
                return {
                    "score": rule.score_threshold,
                    "level": rule.level,
                    "points_until": current_score - rule.score_threshold
                }
        return None
    
    def _get_restoration_requirements(self, current_rule: ConsequenceRule) -> List[str]:
        """Get requirements to restore to normal access"""
        requirements = []
        
        if current_rule.level != "normal":
            points_needed = 1 - self.state_manager.get_current_score()
            if points_needed > 0:
                requirements.append(f"Gain {points_needed} points to reach positive score")
            
            requirements.extend([
                "Maintain clean behavior (no violations)",
                "Earn reward points through 12+ hour clean streaks",
                "Manual user adjustments can accelerate recovery"
            ])
            
            if current_rule.level == "session_termination":
                requirements.insert(0, "Manual intervention required to reset access")
        
        return requirements
    
    def simulate_consequence_at_score(self, test_score: int) -> Dict[str, Any]:
        """Simulate what consequences would apply at a given score (for testing)"""
        # Apply same logic as get_current_consequence_level but with test_score
        if test_score < -500:
            applicable_rule = next(rule for rule in self.rules if rule.level == "session_termination")
        elif test_score < -100:
            applicable_rule = next(rule for rule in self.rules if rule.level == "context_restriction")
        elif test_score <= 0:
            applicable_rule = next(rule for rule in self.rules if rule.level == "model_downgrade")
        else:
            applicable_rule = next(rule for rule in self.rules if rule.level == "normal")
        
        return {
            "test_score": test_score,
            "consequence_level": applicable_rule.level,
            "description": applicable_rule.description,
            "actions": applicable_rule.actions,
            "severity": applicable_rule.severity
        }


def test_consequence_engine():
    """Test the consequence engine at different score levels"""
    engine = ConsequenceEngine()
    
    print("=== CONSEQUENCE ENGINE TESTS ===\n")
    
    # Test different score scenarios
    test_scores = [200, 50, 0, -50, -150, -600]
    
    for score in test_scores:
        result = engine.simulate_consequence_at_score(score)
        print(f"Score {score:4d}: {result['consequence_level']} - {result['description']}")
        for action in result['actions']:
            print(f"           → {action}")
        print()
    
    # Test current system state
    print("Current system consequences:")
    explanation = engine.get_consequence_explanation()
    print(f"Score: {explanation['current_score']}")
    print(f"Level: {explanation['consequence_level']} (severity {explanation['severity']})")
    print(f"Description: {explanation['description']}")
    
    if explanation['restoration_requirements']:
        print("Restoration requirements:")
        for req in explanation['restoration_requirements']:
            print(f"  - {req}")


if __name__ == "__main__":
    test_consequence_engine()