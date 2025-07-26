"""
Structured logging utilities for AUX Protocol.

This module provides session logging, structured log formatting,
and log management for agent interactions.
"""

import json
import time
import logging
import logging.handlers
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class LogEventType(str, Enum):
    """Types of log events for structured logging."""
    
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    COMMAND_RECEIVED = "command_received"
    COMMAND_EXECUTED = "command_executed"
    COMMAND_FAILED = "command_failed"
    NAVIGATION = "navigation"
    INTERACTION = "interaction"
    EXTRACTION = "extraction"
    WAIT_CONDITION = "wait_condition"
    ERROR = "error"
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


@dataclass
class LogEvent:
    """Structured log event for session logging."""
    
    timestamp: float
    event_type: LogEventType
    session_id: str
    command_id: Optional[str] = None
    client_ip: Optional[str] = None
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None
    success: bool = True
    error_code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log event to dictionary."""
        result = asdict(self)
        # Convert timestamp to ISO format for readability
        result['timestamp_iso'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.timestamp))
        return result
    
    def to_json(self) -> str:
        """Convert log event to JSON string."""
        return json.dumps(self.to_dict(), default=str, separators=(',', ':'))


class SessionLogger:
    """
    Structured session logger for AUX Protocol.
    
    Provides machine-readable logging of all agent interactions
    and system events for analysis and debugging.
    """
    
    def __init__(self, log_file_path: str = "session.log", max_file_size_mb: int = 100, backup_count: int = 5):
        """
        Initialize session logger.
        
        Args:
            log_file_path: Path to session log file
            max_file_size_mb: Maximum log file size before rotation
            backup_count: Number of backup files to keep
        """
        self.log_file_path = log_file_path
        self.logger = logging.getLogger("aux.session")
        
        # Create log directory if it doesn't exist
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure rotating file handler
        handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        # Use simple formatter since we're logging JSON
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        # Clear existing handlers and add our handler
        self.logger.handlers.clear()
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        
        # Track active sessions
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
    def log_event(self, event: LogEvent) -> None:
        """
        Log a structured event.
        
        Args:
            event: Log event to record
        """
        self.logger.info(event.to_json())
        
        # Update session tracking
        if event.event_type == LogEventType.SESSION_START:
            self.active_sessions[event.session_id] = {
                'start_time': event.timestamp,
                'client_ip': event.client_ip,
                'command_count': 0,
                'last_activity': event.timestamp
            }
        elif event.event_type == LogEventType.SESSION_END:
            self.active_sessions.pop(event.session_id, None)
        elif event.session_id in self.active_sessions:
            session_info = self.active_sessions[event.session_id]
            session_info['last_activity'] = event.timestamp
            if event.command_id:
                session_info['command_count'] += 1
    
    def log_session_start(self, session_id: str, client_ip: Optional[str] = None, **kwargs) -> None:
        """Log session start event."""
        event = LogEvent(
            timestamp=time.time(),
            event_type=LogEventType.SESSION_START,
            session_id=session_id,
            client_ip=client_ip,
            message=f"Session {session_id} started",
            data=kwargs
        )
        self.log_event(event)
    
    def log_session_end(self, session_id: str, **kwargs) -> None:
        """Log session end event."""
        session_info = self.active_sessions.get(session_id, {})
        duration = time.time() - session_info.get('start_time', time.time())
        
        event = LogEvent(
            timestamp=time.time(),
            event_type=LogEventType.SESSION_END,
            session_id=session_id,
            message=f"Session {session_id} ended",
            data={
                'duration_seconds': duration,
                'command_count': session_info.get('command_count', 0),
                **kwargs
            }
        )
        self.log_event(event)
    
    def log_command_received(self, session_id: str, command_id: str, method: str, 
                           command_data: Dict[str, Any], client_ip: Optional[str] = None) -> None:
        """Log command received event."""
        event = LogEvent(
            timestamp=time.time(),
            event_type=LogEventType.COMMAND_RECEIVED,
            session_id=session_id,
            command_id=command_id,
            client_ip=client_ip,
            message=f"Command {method} received",
            data={
                'method': method,
                'command_data': command_data
            }
        )
        self.log_event(event)
    
    def log_command_executed(self, session_id: str, command_id: str, method: str,
                           execution_time_ms: int, response_data: Dict[str, Any]) -> None:
        """Log successful command execution."""
        event = LogEvent(
            timestamp=time.time(),
            event_type=LogEventType.COMMAND_EXECUTED,
            session_id=session_id,
            command_id=command_id,
            message=f"Command {method} executed successfully",
            execution_time_ms=execution_time_ms,
            success=True,
            data={
                'method': method,
                'response_data': response_data
            }
        )
        self.log_event(event)
    
    def log_command_failed(self, session_id: str, command_id: str, method: str,
                          error_message: str, error_code: str, execution_time_ms: int) -> None:
        """Log failed command execution."""
        event = LogEvent(
            timestamp=time.time(),
            event_type=LogEventType.COMMAND_FAILED,
            session_id=session_id,
            command_id=command_id,
            message=f"Command {method} failed: {error_message}",
            execution_time_ms=execution_time_ms,
            success=False,
            error_code=error_code,
            data={'method': method}
        )
        self.log_event(event)
    
    def log_navigation(self, session_id: str, command_id: str, url: str, 
                      final_url: str, load_time_ms: int, status_code: Optional[int] = None) -> None:
        """Log navigation event."""
        event = LogEvent(
            timestamp=time.time(),
            event_type=LogEventType.NAVIGATION,
            session_id=session_id,
            command_id=command_id,
            message=f"Navigated to {final_url}",
            execution_time_ms=load_time_ms,
            data={
                'original_url': url,
                'final_url': final_url,
                'status_code': status_code,
                'redirected': url != final_url
            }
        )
        self.log_event(event)
    
    def log_interaction(self, session_id: str, command_id: str, interaction_type: str,
                       selector: str, success: bool, **kwargs) -> None:
        """Log UI interaction event."""
        event = LogEvent(
            timestamp=time.time(),
            event_type=LogEventType.INTERACTION,
            session_id=session_id,
            command_id=command_id,
            message=f"{interaction_type} on {selector}",
            success=success,
            data={
                'interaction_type': interaction_type,
                'selector': selector,
                **kwargs
            }
        )
        self.log_event(event)
    
    def log_extraction(self, session_id: str, command_id: str, selector: str,
                      extract_type: str, elements_found: int, data_extracted: Any) -> None:
        """Log data extraction event."""
        event = LogEvent(
            timestamp=time.time(),
            event_type=LogEventType.EXTRACTION,
            session_id=session_id,
            command_id=command_id,
            message=f"Extracted {extract_type} from {elements_found} elements",
            data={
                'selector': selector,
                'extract_type': extract_type,
                'elements_found': elements_found,
                'data_size': len(str(data_extracted)) if data_extracted else 0
            }
        )
        self.log_event(event)
    
    def log_wait_condition(self, session_id: str, command_id: str, condition: str,
                          condition_met: bool, wait_time_ms: int, **kwargs) -> None:
        """Log wait condition event."""
        event = LogEvent(
            timestamp=time.time(),
            event_type=LogEventType.WAIT_CONDITION,
            session_id=session_id,
            command_id=command_id,
            message=f"Wait condition {condition} {'met' if condition_met else 'timeout'}",
            execution_time_ms=wait_time_ms,
            success=condition_met,
            data={
                'condition': condition,
                **kwargs
            }
        )
        self.log_event(event)
    
    def log_security_violation(self, session_id: str, client_ip: str, violation_type: str,
                             details: str, command_id: Optional[str] = None) -> None:
        """Log security violation event."""
        event = LogEvent(
            timestamp=time.time(),
            event_type=LogEventType.SECURITY_VIOLATION,
            session_id=session_id,
            command_id=command_id,
            client_ip=client_ip,
            message=f"Security violation: {violation_type}",
            success=False,
            data={
                'violation_type': violation_type,
                'details': details
            }
        )
        self.log_event(event)
    
    def log_rate_limit_exceeded(self, client_ip: str, session_id: Optional[str] = None) -> None:
        """Log rate limit exceeded event."""
        event = LogEvent(
            timestamp=time.time(),
            event_type=LogEventType.RATE_LIMIT_EXCEEDED,
            session_id=session_id or "unknown",
            client_ip=client_ip,
            message=f"Rate limit exceeded for {client_ip}",
            success=False
        )
        self.log_event(event)
    
    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific session."""
        return self.active_sessions.get(session_id)
    
    def get_all_session_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all active sessions."""
        return self.active_sessions.copy()


class StateTracker:
    """
    Tracks state changes for command responses.
    
    Provides before/after state comparison for UI interactions.
    """
    
    def __init__(self):
        """Initialize state tracker."""
        self.session_states: Dict[str, Dict[str, Any]] = {}
        
    def capture_state(self, session_id: str, state_type: str, state_data: Dict[str, Any]) -> None:
        """
        Capture state for a session.
        
        Args:
            session_id: Browser session ID
            state_type: Type of state (page, element, etc.)
            state_data: State data to capture
        """
        if session_id not in self.session_states:
            self.session_states[session_id] = {}
            
        self.session_states[session_id][state_type] = {
            'timestamp': time.time(),
            'data': state_data
        }
    
    def get_state_diff(self, session_id: str, state_type: str, new_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get state difference for a session.
        
        Args:
            session_id: Browser session ID
            state_type: Type of state to compare
            new_state: New state data
            
        Returns:
            State difference information
        """
        if session_id not in self.session_states:
            return {'type': 'initial_state', 'changes': new_state}
            
        old_state_info = self.session_states[session_id].get(state_type)
        if not old_state_info:
            return {'type': 'initial_state', 'changes': new_state}
        
        old_state = old_state_info['data']
        
        # Simple state comparison - could be enhanced
        changes = {}
        all_keys = set(old_state.keys()) | set(new_state.keys())
        
        for key in all_keys:
            old_value = old_state.get(key)
            new_value = new_state.get(key)
            
            if old_value != new_value:
                changes[key] = {
                    'old': old_value,
                    'new': new_value
                }
        
        return {
            'type': 'state_change',
            'changes': changes,
            'time_delta': time.time() - old_state_info['timestamp']
        }
    
    def cleanup_session_state(self, session_id: str) -> None:
        """Clean up state tracking for a session."""
        self.session_states.pop(session_id, None)


# Global instances
session_logger: Optional[SessionLogger] = None
state_tracker = StateTracker()


def init_session_logging(log_file_path: str = "session.log", max_file_size_mb: int = 100) -> SessionLogger:
    """
    Initialize global session logging.
    
    Args:
        log_file_path: Path to session log file
        max_file_size_mb: Maximum log file size before rotation
        
    Returns:
        Initialized session logger
    """
    global session_logger
    session_logger = SessionLogger(log_file_path, max_file_size_mb)
    return session_logger


def get_session_logger() -> Optional[SessionLogger]:
    """Get global session logger instance."""
    return session_logger


def get_state_tracker() -> StateTracker:
    """Get global state tracker instance."""
    return state_tracker