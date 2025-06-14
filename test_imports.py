#!/usr/bin/env python
"""
Simple test script to verify imports work and discover available functions/classes
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.abspath('.'))

def test_imports():
    """Test various imports and discover what's available"""
    try:
        print("Testing woniunote import...")
        import woniunote
        print("✅ woniunote imported successfully")
        
        print("Testing woniunote.common import...")
        import woniunote.common
        print("✅ woniunote.common imported successfully")
        
        print("Testing simple_logger import...")
        from woniunote.common import simple_logger
        print(f"✅ simple_logger imported successfully. Available: {dir(simple_logger)}")
        
        print("Testing timer import...")
        from woniunote.common import timer
        print(f"✅ timer imported successfully. Available: {dir(timer)}")
        
        print("Testing utils import...")
        from woniunote.common import utils
        print(f"✅ utils imported successfully. Available functions: {[x for x in dir(utils) if not x.startswith('_')][:10]}...")
        
        print("Testing database import...")
        from woniunote.common import database
        print(f"✅ database imported successfully. Available: {[x for x in dir(database) if not x.startswith('_')]}")
        
        print("Testing cache_utils import...")
        from woniunote.common import cache_utils
        print(f"✅ cache_utils imported successfully. Available: {[x for x in dir(cache_utils) if not x.startswith('_')][:10]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1) 