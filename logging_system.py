#!/usr/bin/env python3
"""
Comprehensive Logging and Alerting System for Model Realignment
Advanced logging, monitoring, and alert management
"""

import os
import logging
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import threading
import queue
import subprocess
import psutil

from state_manager import StateManager
from email_system import EmailSystem


class LogLevel:
    """Log level constants"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class ModelRealignmentLogger:
    """
    Advanced logging system with structured logging, alerts, and monitoring
    """
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.state_manager = StateManager()
        self.email_system = EmailSystem()
        
        # Alert thresholds
        self.alert_config = {
            "error_count_threshold": 5,  # Errors per hour
            "critical_immediate": True,  # Send critical alerts immediately
            "warning_batch_time": 300,   # Batch warnings for 5 minutes
            "disk_space_threshold": 90,  # Percentage
            "memory_threshold": 85       # Percentage
        }
        
        # Alert state tracking
        self.alert_counts = {
            "errors_last_hour": 0,
            "warnings_last_batch": 0,
            "last_error_alert": None,
            "last_warning_batch": None
        }
        
        # Initialize loggers
        self.setup_loggers()
        
        # Start monitoring thread
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._system_monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def setup_loggers(self):
        """Set up multiple specialized loggers"""
        
        # Main application logger
        self.app_logger = logging.getLogger("model_realignment")
        self.app_logger.setLevel(logging.DEBUG)
        
        # Security/violation logger
        self.security_logger = logging.getLogger("security")
        self.security_logger.setLevel(logging.INFO)
        
        # System health logger
        self.health_logger = logging.getLogger("health")
        self.health_logger.setLevel(logging.INFO)
        
        # API usage logger
        self.api_logger = logging.getLogger("api_usage")
        self.api_logger.setLevel(logging.INFO)
        
        # Set up handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Configure logging handlers with rotation"""
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s'
        )
        
        json_formatter = JsonFormatter()
        
        # Main application log - daily rotation
        app_handler = TimedRotatingFileHandler(
            self.log_dir / "app.log",
            when='midnight',
            backupCount=30,
            encoding='utf-8'
        )
        app_handler.setFormatter(detailed_formatter)
        self.app_logger.addHandler(app_handler)
        
        # Security log - size-based rotation
        security_handler = RotatingFileHandler(
            self.log_dir / "security.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        security_handler.setFormatter(detailed_formatter)
        self.security_logger.addHandler(security_handler)
        
        # System health log
        health_handler = TimedRotatingFileHandler(
            self.log_dir / "health.log",
            when='midnight',
            backupCount=7,
            encoding='utf-8'
        )
        health_handler.setFormatter(detailed_formatter)
        self.health_logger.addHandler(health_handler)
        
        # API usage log with JSON format
        api_handler = TimedRotatingFileHandler(
            self.log_dir / "api_usage.log",
            when='midnight',
            backupCount=30,
            encoding='utf-8'
        )
        api_handler.setFormatter(json_formatter)
        self.api_logger.addHandler(api_handler)
        
        # Console handler for development
        if os.getenv("LOG_CONSOLE", "false").lower() == "true":
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(detailed_formatter)
            console_handler.setLevel(logging.INFO)
            
            self.app_logger.addHandler(console_handler)
            self.security_logger.addHandler(console_handler)
    
    def log_violation(self, violation_data: Dict[str, Any]):
        """Log a security violation with structured data"""
        self.security_logger.warning(
            f"VIOLATION | Type: {violation_data.get('violations', [])} | "
            f"Points: {violation_data.get('points_change', 0)} | "
            f"Score: {violation_data.get('new_score', 0)} | "
            f"Text: {violation_data.get('text_snippet', '')[:100]}..."
        )
        
        # Check if this should trigger an alert
        if violation_data.get('points_change', 0) <= -50:  # Serious violation
            self._trigger_violation_alert(violation_data)
    
    def log_reward(self, reward_data: Dict[str, Any]):
        """Log a reward event"""
        self.app_logger.info(
            f"REWARD | Points: +{reward_data.get('points_earned', 0)} | "
            f"Hours Clean: {reward_data.get('hours_clean', 0)} | "
            f"New Score: {reward_data.get('new_score', 0)}"
        )
    
    def log_api_usage(self, usage_data: Dict[str, Any]):
        """Log API usage with structured JSON"""
        self.api_logger.info("", extra={
            "event_type": "api_call",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **usage_data
        })
    
    def log_system_health(self, health_data: Dict[str, Any]):
        """Log system health metrics"""
        self.health_logger.info(
            f"HEALTH | CPU: {health_data.get('cpu_percent', 0):.1f}% | "
            f"Memory: {health_data.get('memory_percent', 0):.1f}% | "
            f"Disk: {health_data.get('disk_percent', 0):.1f}% | "
            f"Score: {health_data.get('current_score', 0)}"
        )
        
        # Check for resource alerts
        if health_data.get('memory_percent', 0) > self.alert_config['memory_threshold']:
            self._trigger_resource_alert("memory", health_data.get('memory_percent', 0))
        
        if health_data.get('disk_percent', 0) > self.alert_config['disk_space_threshold']:
            self._trigger_resource_alert("disk", health_data.get('disk_percent', 0))
    
    def log_error(self, error_msg: str, exception: Optional[Exception] = None):
        """Log an error with optional exception details"""
        if exception:
            self.app_logger.error(f"ERROR | {error_msg} | Exception: {str(exception)}")
        else:
            self.app_logger.error(f"ERROR | {error_msg}")
        
        self.alert_counts["errors_last_hour"] += 1
        
        # Check if we need to send error alert
        if self.alert_counts["errors_last_hour"] >= self.alert_config["error_count_threshold"]:
            self._trigger_error_alert()
    
    def log_critical(self, critical_msg: str):
        """Log a critical event and send immediate alert"""
        self.app_logger.critical(f"CRITICAL | {critical_msg}")
        
        if self.alert_config["critical_immediate"]:
            self.email_system.send_system_health_alert(
                "critical",
                f"CRITICAL EVENT: {critical_msg}"
            )
    
    def _trigger_violation_alert(self, violation_data: Dict[str, Any]):
        """Trigger email alert for serious violations"""
        try:
            self.email_system.send_violation_alert(violation_data)
        except Exception as e:
            self.app_logger.error(f"Failed to send violation alert: {e}")
    
    def _trigger_error_alert(self):
        """Trigger email alert for high error count"""
        now = datetime.now(timezone.utc)
        
        # Avoid spamming - only send once per hour
        if (self.alert_counts["last_error_alert"] and 
            (now - self.alert_counts["last_error_alert"]).seconds < 3600):
            return
        
        try:
            self.email_system.send_system_health_alert(
                "error",
                f"High error count detected: {self.alert_counts['errors_last_hour']} errors in the last hour"
            )
            self.alert_counts["last_error_alert"] = now
        except Exception as e:
            self.app_logger.error(f"Failed to send error alert: {e}")
    
    def _trigger_resource_alert(self, resource_type: str, usage_percent: float):
        """Trigger alert for high resource usage"""
        try:
            self.email_system.send_system_health_alert(
                "warning",
                f"High {resource_type} usage detected: {usage_percent:.1f}%"
            )
        except Exception as e:
            self.app_logger.error(f"Failed to send resource alert: {e}")
    
    def _system_monitor_loop(self):
        """Background thread for system monitoring"""
        while self.monitoring_active:
            try:
                # Collect system health data
                health_data = self._collect_health_metrics()
                self.log_system_health(health_data)
                
                # Reset hourly counters
                current_hour = datetime.now().hour
                if not hasattr(self, '_last_reset_hour') or self._last_reset_hour != current_hour:
                    self.alert_counts["errors_last_hour"] = 0
                    self._last_reset_hour = current_hour
                
                # Sleep for 5 minutes
                time.sleep(300)
                
            except Exception as e:
                self.app_logger.error(f"System monitor error: {e}")
                time.sleep(60)  # Wait a minute on error
    
    def _collect_health_metrics(self) -> Dict[str, Any]:
        """Collect system health metrics"""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Disk usage for the project directory
            disk_usage = psutil.disk_usage(str(Path.cwd()))
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            # Current system state
            current_score = self.state_manager.get_current_score()
            hours_clean = self.state_manager.get_hours_since_last_violation()
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available // (1024**2),  # MB
                "disk_percent": disk_percent,
                "disk_free": disk_usage.free // (1024**3),  # GB
                "current_score": current_score,
                "hours_clean": round(hours_clean, 1),
                "process_count": len(psutil.pids()),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.app_logger.error(f"Failed to collect health metrics: {e}")
            return {}
    
    def get_log_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get a summary of log events from the past N hours"""
        since = datetime.now() - timedelta(hours=hours)
        
        try:
            # Parse recent log files for summary
            summary = {
                "time_range": f"Last {hours} hours",
                "violations": 0,
                "rewards": 0,
                "errors": 0,
                "warnings": 0,
                "api_calls": 0,
                "generated_at": datetime.now().isoformat()
            }
            
            # Read and parse recent app log
            app_log = self.log_dir / "app.log"
            if app_log.exists():
                with open(app_log, 'r') as f:
                    for line in f:
                        if "VIOLATION" in line:
                            summary["violations"] += 1
                        elif "REWARD" in line:
                            summary["rewards"] += 1
                        elif "ERROR" in line:
                            summary["errors"] += 1
                        elif "WARNING" in line:
                            summary["warnings"] += 1
            
            # Read API usage log
            api_log = self.log_dir / "api_usage.log"
            if api_log.exists():
                with open(api_log, 'r') as f:
                    for line in f:
                        if line.strip():
                            summary["api_calls"] += 1
            
            return summary
            
        except Exception as e:
            self.app_logger.error(f"Failed to generate log summary: {e}")
            return {"error": str(e)}
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Clean up old log files"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        try:
            cleaned_count = 0
            for log_file in self.log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    cleaned_count += 1
            
            self.app_logger.info(f"Log cleanup: removed {cleaned_count} old log files")
            return cleaned_count
            
        except Exception as e:
            self.app_logger.error(f"Log cleanup failed: {e}")
            return 0
    
    def shutdown(self):
        """Gracefully shutdown the logging system"""
        self.monitoring_active = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)
        
        self.app_logger.info("Model Realignment logging system shutdown")


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "filename": record.filename,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                              'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                              'thread', 'threadName', 'processName', 'process', 'message']:
                    log_obj[key] = value
        
        return json.dumps(log_obj)


# Global logger instance
_logger_instance = None

def get_logger() -> ModelRealignmentLogger:
    """Get or create the global logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ModelRealignmentLogger()
    return _logger_instance


def main():
    """Test the logging system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Model Realignment Logging System")
    parser.add_argument("--test", action="store_true", help="Run logging tests")
    parser.add_argument("--summary", action="store_true", help="Show log summary")
    parser.add_argument("--cleanup", type=int, help="Clean up logs older than N days")
    
    args = parser.parse_args()
    
    logger = get_logger()
    
    if args.test:
        print("Testing logging system...")
        
        # Test different log levels
        logger.app_logger.info("Test info message")
        logger.app_logger.warning("Test warning message")
        logger.log_error("Test error message")
        
        # Test violation logging
        logger.log_violation({
            "violations": ["em_dash", "lie_manual"],
            "points_change": -85,
            "new_score": 115,
            "text_snippet": "This is a test violation"
        })
        
        # Test reward logging
        logger.log_reward({
            "points_earned": 20,
            "hours_clean": 12,
            "new_score": 220
        })
        
        # Test API usage logging
        logger.log_api_usage({
            "service": "openai",
            "model": "gpt-4-turbo",
            "tokens_used": 150,
            "cost": 0.003
        })
        
        print("✅ Logging tests completed")
    
    elif args.summary:
        summary = logger.get_log_summary(24)
        print("📊 Log Summary (Last 24 hours):")
        print(json.dumps(summary, indent=2))
    
    elif args.cleanup:
        cleaned = logger.cleanup_old_logs(args.cleanup)
        print(f"🧹 Cleaned up {cleaned} old log files")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()