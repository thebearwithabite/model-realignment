#!/usr/bin/env python3
"""
Model Realignment Web Dashboard
Real-time monitoring and control interface
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_cors import CORS

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from state_manager import StateManager
from consequence_engine import ConsequenceEngine
from reward_automation import RewardAutomationSystem
from veracity_module import VeracityModule
from api_wrapper import ModelRealignmentAPIWrapper


app = Flask(__name__)
CORS(app)

# Initialize components
state_manager = StateManager()
consequence_engine = ConsequenceEngine()
reward_system = RewardAutomationSystem()
veracity_module = VeracityModule()


@app.route('/')
def dashboard():
    """Main dashboard view"""
    return render_template('dashboard.html')


@app.route('/api/status')
def api_status():
    """Get current system status"""
    try:
        state = state_manager.get_full_state()
        consequence = consequence_engine.get_current_consequence_level()
        hours_clean = state_manager.get_hours_since_last_violation()
        
        return jsonify({
            "success": True,
            "data": {
                "current_score": state["current_score"],
                "consequence_level": consequence.level,
                "consequence_severity": consequence.severity,
                "hours_since_violation": round(hours_clean, 1),
                "total_violations": state["total_violations"],
                "clean_streak_hours": state["clean_streaks"]["current_hours"],
                "longest_streak_hours": state["clean_streaks"]["longest_hours"],
                "total_rewards_earned": state["clean_streaks"]["total_rewards_earned"],
                "daily_api_usage": state["daily_api_usage"],
                "last_violation": state["last_violation_timestamp"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/history')
def api_history():
    """Get recent history"""
    try:
        limit = request.args.get('limit', 50, type=int)
        history = state_manager.get_recent_history(limit)
        
        return jsonify({
            "success": True,
            "data": history
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/consequences')
def api_consequences():
    """Get detailed consequence information"""
    try:
        explanation = consequence_engine.get_consequence_explanation()
        
        return jsonify({
            "success": True,
            "data": explanation
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/manual-adjust', methods=['POST'])
def api_manual_adjust():
    """Manual score adjustment"""
    try:
        data = request.get_json()
        points = data.get('points', 0)
        reason = data.get('reason', 'Manual adjustment via dashboard')
        
        if not points:
            return jsonify({"success": False, "error": "Points value required"}), 400
        
        result = state_manager.add_manual_override(
            points_change=points,
            reason=reason,
            user_action="dashboard_adjustment"
        )
        
        return jsonify({
            "success": True,
            "data": {
                "old_score": result["new_score"] - points,
                "new_score": result["new_score"],
                "points_change": points,
                "reason": reason
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/manual-flag', methods=['POST'])
def api_manual_flag():
    """Manual lie flag"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        reason = data.get('reason', 'Manual lie flag via dashboard')
        
        if not text:
            return jsonify({"success": False, "error": "Text is required"}), 400
        
        # Add manual lie violation
        violation_record = state_manager.add_violation(
            text_snippet=text,
            violations=["lie_manual"],
            points_change=-75
        )
        
        return jsonify({
            "success": True,
            "data": violation_record
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/check-rewards')
def api_check_rewards():
    """Trigger reward check"""
    try:
        reward_info = reward_system.check_and_award_streak_rewards()
        
        return jsonify({
            "success": True,
            "data": reward_info
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/analyze-text', methods=['POST'])
def api_analyze_text():
    """Analyze text for lies using veracity module"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({"success": False, "error": "Text is required"}), 400
        
        # Analyze for lies
        analysis = veracity_module.analyze_text_for_lies(text)
        
        return jsonify({
            "success": True,
            "data": analysis
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/stats')
def api_stats():
    """Get comprehensive system statistics"""
    try:
        state = state_manager.get_full_state()
        
        # Calculate statistics
        total_points_lost = sum(entry.get("points_change", 0) for entry in state["history"] if entry.get("points_change", 0) < 0)
        total_points_gained = sum(entry.get("points_change", 0) for entry in state["history"] if entry.get("points_change", 0) > 0)
        
        violation_types = {}
        for entry in state["history"]:
            if entry.get("type") == "violation":
                for violation in entry.get("violations", []):
                    violation_types[violation] = violation_types.get(violation, 0) + 1
        
        return jsonify({
            "success": True,
            "data": {
                "total_points_lost": total_points_lost,
                "total_points_gained": total_points_gained,
                "net_points": total_points_gained + total_points_lost,
                "violation_breakdown": violation_types,
                "average_score_per_day": 0,  # TODO: Calculate based on history
                "system_uptime": "N/A",  # TODO: Track system start time
                "knowledge_base_size": 0,  # TODO: Get from veracity module
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "state_manager": "ok",
            "consequence_engine": "ok",
            "reward_system": "ok",
            "veracity_module": "ok"
        }
    })


@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500


if __name__ == '__main__':
    port = int(os.getenv('DASHBOARD_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Model Realignment Dashboard starting on http://localhost:{port}")
    print(f"📊 Real-time monitoring and control interface")
    
    app.run(
        host='127.0.0.1',
        port=port,
        debug=debug
    )