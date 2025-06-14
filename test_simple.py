#!/usr/bin/env python3
"""
Simple test script to verify functionality
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.abspath('.'))

def test_simple_logger():
    """Test simple logger functionality"""
    try:
        from woniunote.common.simple_logger import get_simple_logger
        
        logger = get_simple_logger('test_module')
        print(f"✅ Logger created: {logger.name}")
        
        # Test basic methods
        logger.info("Test info message")
        logger.error("Test error message")
        print("✅ Logger methods work")
        
        return True
    except Exception as e:
        print(f"❌ Logger test failed: {e}")
        return False

def test_timer():
    """Test timer functionality"""
    try:
        from woniunote.common.timer import can_use_minute
        
        result = can_use_minute()
        print(f"✅ Timer function works: {result}")
        
        return True
    except Exception as e:
        print(f"❌ Timer test failed: {e}")
        return False

def test_utils():
    """Test utils functionality"""
    try:
        from woniunote.common.utils import validate_email, read_config, gen_email_code
        from datetime import datetime
        
        # Test gen_email_code (instead of generate_id)
        code1 = gen_email_code()
        code2 = gen_email_code()
        assert code1 != code2
        print(f"✅ gen_email_code works: {code1}")
        
        # Test read_config
        try:
            config = read_config()
            print(f"✅ read_config works: {type(config)}")
        except Exception as e:
            print(f"⚠️ read_config failed (expected): {e}")
        
        # Test validate_email
        assert validate_email("test@example.com") == True
        assert validate_email("invalid_email") == False
        print("✅ validate_email works")
        
        return True
    except Exception as e:
        print(f"❌ Utils test failed: {e}")
        return False

def test_cache_utils():
    """Test cache utils functionality"""
    try:
        from woniunote.common.cache_utils import CacheManager
        
        cache_manager = CacheManager()
        print(f"✅ CacheManager created: {cache_manager}")
        
        return True
    except Exception as e:
        print(f"❌ Cache utils test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running simple functionality tests...")
    
    tests = [
        test_simple_logger,
        test_timer,
        test_utils,
        test_cache_utils
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 