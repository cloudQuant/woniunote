import logging
import os
import sys
import json
import threading
import time
import uuid
from functools import wraps

# Simple and reliable logging utilities for WoniuNote
# This module supports:
# 1. JSON-formatted logs
# 2. Trace IDs for request tracking
# 3. Performance monitoring
# 4. Automatic logging of function calls

# Set up a thread-local storage for the trace ID
_trace_id_local = threading.local()

# Generate a new trace ID (UUID)
def gen_trace_id():
    tid = str(uuid.uuid4())
    _trace_id_local.trace_id = tid
    return tid

# Get the current trace ID
def get_trace_id():
    # Try to get from thread local storage
    trace_id = getattr(_trace_id_local, 'trace_id', None)
    if trace_id:
        return trace_id
        
    # Try to get from Flask request headers if available
    try:
        from flask import has_request_context, request
        if has_request_context():
            header_trace_id = request.headers.get('X-Trace-Id')
            if header_trace_id:
                return header_trace_id
    except ImportError:
        pass
    except Exception:
        pass
        
    # Generate a new trace ID if none exists
    return gen_trace_id()

# Set the trace ID
def set_trace_id(trace_id):
    _trace_id_local.trace_id = trace_id

# Simple formatter that outputs logs in a structured format
class SimpleFormatter(logging.Formatter):
    def format(self, record):
        # Basic log data
        log_data = {
            'time': self.formatTime(record),
            'level': record.levelname,
            'module': record.name,
            'message': record.getMessage()
        }
        
        # Add trace ID
        try:
            log_data['trace_id'] = getattr(record, 'trace_id', get_trace_id())
        except:
            log_data['trace_id'] = 'unknown'
        
        # Add extra data if available
        if hasattr(record, 'extra_data'):
            try:
                extra = record.extra_data
                if isinstance(extra, dict):
                    for k, v in extra.items():
                        if k not in log_data:
                            log_data[k] = v
            except:
                pass
                
        # Convert to a string (fall back to simple format if JSON fails)
        try:
            return json.dumps(log_data, default=str, ensure_ascii=False)
        except:
            return f"[{log_data['time']}] {log_data['level']} {log_data['module']} - {log_data['message']} (trace_id: {log_data.get('trace_id', 'unknown')})"

# Default log level
LOG_LEVEL = logging.INFO

# Get or create a logger
def get_logger(name=None):
    logger = logging.getLogger(name)
    
    # Remove existing handlers
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(SimpleFormatter())
    logger.addHandler(console_handler)
    
    # Try to create file handler if possible
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(
            os.path.join(log_dir, 'woniunote.log'),
            encoding='utf-8'
        )
        file_handler.setFormatter(SimpleFormatter())
        logger.addHandler(file_handler)
    except:
        # If file logging fails, just continue with console logging
        pass
    
    logger.setLevel(LOG_LEVEL)
    logger.propagate = False
    return logger

# Setup logging system
def setup_logging():
    # Set up the root logger
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    
    # Remove existing handlers
    for handler in list(root.handlers):
        root.removeHandler(handler)
        
    # Add our handlers
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(SimpleFormatter())
    root.addHandler(console)
    
    # Quiet noisy loggers
    for noisy in ['werkzeug', 'sqlalchemy.engine']:
        logging.getLogger(noisy).setLevel(logging.WARNING)
        
    return root

# Performance monitoring decorator
def log_time(logger, msg_prefix="耗时"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = (time.time() - start) * 1000
                logger.info(
                    f"{msg_prefix} [{func.__name__}] {elapsed:.2f}ms", 
                    extra={'extra_data': {'elapsed_ms': elapsed, 'trace_id': get_trace_id()}}
                )
        return wrapper
    return decorator
