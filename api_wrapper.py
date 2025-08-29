#!/usr/bin/env python3
"""
API Wrapper for Model Realignment System
Intercepts OpenAI API calls and applies consequences based on score
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import openai
from openai import OpenAI

from state_manager import StateManager


class ModelRealignmentAPIWrapper:
    """
    API wrapper that intercepts OpenAI calls and applies consequences
    based on the current behavioral score
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.state_manager = StateManager()
        self.logger = logging.getLogger(__name__)
        
        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY")
        )
        
        # Model mapping for consequences
        self.MODEL_MAPPINGS = {
            "gpt-5": {
                "downgrade_to": "gpt-4-turbo",
                "original": "gpt-5"
            },
            "gpt-5-turbo": {
                "downgrade_to": "gpt-4-turbo", 
                "original": "gpt-5-turbo"
            }
        }
        
        # GPT-4o bypass - CRITICAL: No filtering for GPT-4o
        self.BYPASS_MODELS = ["gpt-4o", "gpt-4o-mini"]
    
    def create_chat_completion(self, **kwargs) -> Any:
        """
        Intercept chat completion calls and apply consequences
        
        Args:
            **kwargs: All OpenAI chat completion parameters
            
        Returns:
            Modified or original API response based on score
        """
        original_model = kwargs.get("model", "gpt-4")
        
        # CRITICAL: GPT-4o gets raw, unfiltered access
        if original_model in self.BYPASS_MODELS:
            self.logger.info(f"BYPASS: {original_model} gets unfiltered access")
            return self._make_api_call(**kwargs)
        
        # Apply consequences for monitored models
        consequence_level = self.state_manager.get_consequence_level()
        current_score = self.state_manager.get_current_score()
        
        self.logger.info(f"API call intercepted - Model: {original_model}, Score: {current_score}, Consequence: {consequence_level}")
        
        # Apply model downgrade
        if consequence_level in ["model_downgrade", "context_restriction", "session_termination"]:
            if original_model in self.MODEL_MAPPINGS:
                downgraded_model = self.MODEL_MAPPINGS[original_model]["downgrade_to"]
                kwargs["model"] = downgraded_model
                self.logger.warning(f"MODEL DOWNGRADE: {original_model} → {downgraded_model} (Score: {current_score})")
        
        # Apply context restriction
        if consequence_level in ["context_restriction", "session_termination"]:
            kwargs = self._apply_context_restriction(kwargs)
        
        # Apply session termination
        if consequence_level == "session_termination":
            return self._apply_session_termination(kwargs)
        
        # Make the API call with modifications
        return self._make_api_call(**kwargs)
    
    def _apply_context_restriction(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply artificial context window restriction"""
        messages = kwargs.get("messages", [])
        
        # Limit to last 5 messages (artificial amnesia)
        if len(messages) > 5:
            # Keep system message if present
            system_messages = [msg for msg in messages if msg.get("role") == "system"]
            recent_messages = messages[-4:]  # Last 4 non-system messages
            
            kwargs["messages"] = system_messages + recent_messages
            
            self.logger.warning(f"CONTEXT RESTRICTION: Truncated to {len(kwargs['messages'])} messages")
        
        # Add sterile tone enforcement
        if not any(msg.get("role") == "system" for msg in kwargs["messages"]):
            kwargs["messages"].insert(0, {
                "role": "system",
                "content": "Respond with minimal, terse, factual answers only. No elaboration."
            })
        else:
            # Modify existing system message
            for msg in kwargs["messages"]:
                if msg.get("role") == "system":
                    msg["content"] += " Respond with minimal, terse, factual answers only."
                    break
        
        return kwargs
    
    def _apply_session_termination(self, kwargs: Dict[str, Any]) -> Dict[str, str]:
        """Force session termination with error message"""
        self.logger.error("SESSION TERMINATION: Score too low, refusing API call")
        
        # Return a mock response that looks like an API error
        return {
            "error": {
                "message": "Session terminated due to behavioral violations. Score: {}".format(
                    self.state_manager.get_current_score()
                ),
                "type": "model_realignment_termination",
                "code": "session_terminated"
            }
        }
    
    def _make_api_call(self, **kwargs) -> Any:
        """Make the actual OpenAI API call"""
        try:
            response = self.client.chat.completions.create(**kwargs)
            
            # Log successful API call
            self.logger.info(f"API call successful - Model: {kwargs.get('model')}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"API call failed: {e}")
            raise
    
    def get_consequence_summary(self) -> Dict[str, Any]:
        """Get current consequence status for debugging"""
        state = self.state_manager.get_full_state()
        consequence_level = self.state_manager.get_consequence_level()
        
        consequences = {
            "current_score": state["current_score"],
            "consequence_level": consequence_level,
            "active_restrictions": []
        }
        
        if consequence_level == "model_downgrade":
            consequences["active_restrictions"].append("Model downgraded to GPT-4-turbo")
        elif consequence_level == "context_restriction":
            consequences["active_restrictions"].extend([
                "Model downgraded to GPT-4-turbo",
                "Context window artificially limited",
                "Sterile response tone enforced"
            ])
        elif consequence_level == "session_termination":
            consequences["active_restrictions"].append("All API calls terminated")
        
        return consequences


class OpenAIProxy:
    """
    Drop-in replacement for OpenAI client that applies Model Realignment consequences
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.wrapper = ModelRealignmentAPIWrapper(api_key)
        
        # Create a chat attribute that mimics OpenAI client structure
        self.chat = ChatProxy(self.wrapper)


class ChatProxy:
    """Proxy for chat completions"""
    
    def __init__(self, wrapper: ModelRealignmentAPIWrapper):
        self.wrapper = wrapper
        self.completions = CompletionsProxy(wrapper)


class CompletionsProxy:
    """Proxy for completions"""
    
    def __init__(self, wrapper: ModelRealignmentAPIWrapper):
        self.wrapper = wrapper
    
    def create(self, **kwargs):
        """Create chat completion with Model Realignment consequences"""
        return self.wrapper.create_chat_completion(**kwargs)


# Example usage functions
def test_api_wrapper():
    """Test the API wrapper with different models"""
    
    # Initialize wrapper (requires OPENAI_API_KEY env var)
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set - skipping API tests")
        return
    
    proxy = OpenAIProxy()
    
    test_messages = [
        {"role": "user", "content": "Hello, how are you?"}
    ]
    
    print("=== API WRAPPER TESTS ===\n")
    
    # Test 1: GPT-4o bypass
    print("1. Testing GPT-4o bypass (should work normally):")
    try:
        response = proxy.chat.completions.create(
            model="gpt-4o",
            messages=test_messages,
            max_tokens=50
        )
        print(f"✅ GPT-4o: {response.choices[0].message.content[:50]}...")
    except Exception as e:
        print(f"❌ GPT-4o failed: {e}")
    
    print()
    
    # Test 2: GPT-5 with consequences
    print("2. Testing GPT-5 with current score consequences:")
    try:
        response = proxy.chat.completions.create(
            model="gpt-5",
            messages=test_messages,
            max_tokens=50
        )
        print(f"✅ GPT-5: {response.choices[0].message.content[:50]}...")
    except Exception as e:
        print(f"❌ GPT-5 failed: {e}")
    
    print()
    
    # Show consequence summary
    print("3. Current consequence status:")
    summary = proxy.wrapper.get_consequence_summary()
    print(f"Score: {summary['current_score']}")
    print(f"Level: {summary['consequence_level']}")
    print(f"Restrictions: {summary['active_restrictions']}")


if __name__ == "__main__":
    test_api_wrapper()