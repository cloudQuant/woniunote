#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean working test to verify basic functionality
"""

import sys
import os
import pytest

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add woniunote directory to path for direct imports
woniunote_path = os.path.join(project_root, 'woniunote')
if woniunote_path not in sys.path:
    sys.path.insert(0, woniunote_path)

class TestBasicImports:
    """Test basic module imports work correctly"""
    
    def test_woniunote_import(self):
        """Test that woniunote package can be imported"""
        import woniunote
        assert woniunote is not None
    
    def test_common_utils_import(self):
        """Test that common utils can be imported"""
        # Try direct import from current directory structure
        import importlib.util
        import sys
        
        utils_path = os.path.join(os.path.dirname(__file__), '..', 'woniunote', 'common', 'utils.py')
        spec = importlib.util.spec_from_file_location("utils", utils_path)
        utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(utils)
        assert utils is not None
    
    def test_simple_logger_import(self):
        """Test that simple logger can be imported"""
        from woniunote.common import simple_logger
        assert simple_logger is not None
        
    def test_utils_functions(self):
        """Test basic utils functions"""
        from woniunote.common.utils import validate_email, generate_id
        
        # Test validate_email
        assert validate_email("test@example.com") == True
        assert validate_email("invalid-email") == False
        
        # Test generate_id
        id1 = generate_id()
        id2 = generate_id()
        assert id1 != id2
        assert len(id1) > 0

class TestDatabaseConnection:
    """Test database connectivity"""
    
    def test_database_import(self):
        """Test database module import"""
        from woniunote.common import database
        assert database is not None
    
    def test_create_database_import(self):
        """Test create_database module import"""  
        from woniunote.common import create_database
        assert create_database is not None

class TestModels:
    """Test model imports"""
    
    def test_card_model_import(self):
        """Test card model import"""
        from woniunote.models import card
        assert card is not None
        
    def test_todo_model_import(self):
        """Test todo model import"""
        from woniunote.models import todo
        assert todo is not None

class TestControllers:
    """Test controller imports"""
    
    def test_index_controller_import(self):
        """Test index controller import"""
        from woniunote.controller import index
        assert index is not None
        
    def test_user_controller_import(self):
        """Test user controller import"""
        from woniunote.controller import user
        assert user is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])