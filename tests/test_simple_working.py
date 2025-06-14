#!/usr/bin/env python3
"""
Simple working test to verify the test environment
"""

import sys
import os
import subprocess

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_basic_import():
    """Test basic woniunote import"""
    import woniunote
    assert woniunote is not None

def test_common_utils_import_via_subprocess():
    """Test common utils import via subprocess"""
    cmd = [
        sys.executable, '-c',
        'import sys; sys.path.insert(0, "."); from woniunote.common.utils import validate_email; print("SUCCESS")'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
    assert result.returncode == 0
    assert "SUCCESS" in result.stdout

def test_validate_email_function_via_subprocess():
    """Test validate_email function via subprocess"""
    cmd = [
        sys.executable, '-c',
        '''
import sys
sys.path.insert(0, ".")
from woniunote.common.utils import validate_email
assert validate_email("test@example.com") == True
assert validate_email("invalid_email") == False
print("VALIDATION_SUCCESS")
'''
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
    assert result.returncode == 0
    assert "VALIDATION_SUCCESS" in result.stdout

def test_gen_email_code_function_via_subprocess():
    """Test gen_email_code function via subprocess"""
    cmd = [
        sys.executable, '-c',
        '''
import sys
sys.path.insert(0, ".")
from woniunote.common.utils import gen_email_code
code = gen_email_code()
assert len(code) == 6
assert code.isalnum()
print("CODE_SUCCESS")
'''
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
    assert result.returncode == 0
    assert "CODE_SUCCESS" in result.stdout

def test_simple_logger_via_subprocess():
    """Test simple logger via subprocess"""
    cmd = [
        sys.executable, '-c',
        '''
import sys
sys.path.insert(0, ".")
from woniunote.common.simple_logger import get_simple_logger
logger = get_simple_logger("test")
assert logger is not None
logger.info("Test message")
print("LOGGER_SUCCESS")
'''
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
    assert result.returncode == 0
    assert "LOGGER_SUCCESS" in result.stdout

def test_timer_via_subprocess():
    """Test timer function via subprocess"""
    cmd = [
        sys.executable, '-c',
        '''
import sys
sys.path.insert(0, ".")
from woniunote.common.timer import can_use_minute
result = can_use_minute()
assert isinstance(result, int)
assert result > 0
print("TIMER_SUCCESS")
'''
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
    assert result.returncode == 0
    assert "TIMER_SUCCESS" in result.stdout 