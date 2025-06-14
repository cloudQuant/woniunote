#!/usr/bin/env python3
"""
Simple test runner that properly sets up the Python path
"""

import sys
import os
import subprocess
import time

# Add current directory to Python path
sys.path.insert(0, os.path.abspath('.'))

def run_test_with_path(test_file):
    """Run a test file with proper path setup"""
    cmd = [
        sys.executable, '-m', 'pytest',
        test_file,
        '-v',
        '--tb=short',
        '--disable-warnings'
    ]
    
    # Set environment variables
    env = os.environ.copy()
    env['PYTHONPATH'] = '.'
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=60
        )
        
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("Test timed out")
        return False
    except Exception as e:
        print(f"Error running test: {e}")
        return False

def main():
    """Run tests"""
    print("🧪 Running tests with proper path setup...")
    
    # Test the simple logger test
    test_file = "tests/unit/test_common_utils.py::TestSimpleLogger::test_logger_creation"
    
    print(f"\nTesting: {test_file}")
    success = run_test_with_path(test_file)
    
    if success:
        print("✅ Test passed!")
    else:
        print("❌ Test failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 