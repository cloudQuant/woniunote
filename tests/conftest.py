#!/usr/bin/env python3
"""
pytest configuration and fixtures
"""

import sys
import os
import pytest

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Also add the current directory
current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Set testing environment variables
os.environ['TESTING'] = 'True'
os.environ['FLASK_ENV'] = 'testing'
os.environ['PYTHONPATH'] = project_root

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up the test environment"""
    # Ensure the project root is in the path
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Set up environment variables
    os.environ['TESTING'] = 'True'
    os.environ['FLASK_ENV'] = 'testing'
    
    # Try to import the main module to ensure it's available
    try:
        import woniunote
        print(f"✅ Successfully imported woniunote module from {woniunote.__file__}")
    except ImportError as e:
        print(f"⚠️ Warning: Could not import woniunote module: {e}")
    
    yield
    
    # Cleanup if needed
    pass

@pytest.fixture
def mock_config():
    """Provide a mock configuration for tests"""
    return {
        'database': {
            'host': 'localhost',
            'port': 3306,
            'user': 'test_user',
            'password': 'test_password',
            'name': 'test_db'
        },
        'app': {
            'secret_key': 'test_secret_key',
            'debug': True
        }
    }

@pytest.fixture
def temp_file():
    """Create a temporary file for testing"""
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path) 