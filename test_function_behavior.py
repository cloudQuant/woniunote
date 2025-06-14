#!/usr/bin/env python3
"""
Test script to understand actual function behavior
"""

import sys
import os

# Add project root to path
sys.path.insert(0, '.')

def test_functions():
    try:
        from woniunote.common.utils import validate_email, gen_email_code, get_memory_usage
        
        print("=== Email Validation Tests ===")
        test_emails = [
            "test@example.com",
            "invalid_email", 
            "email@123.123.123.123",
            "user..name@domain.com",
            "user@domain..com",
            "user name@domain.com"
        ]
        
        for email in test_emails:
            result = validate_email(email)
            print(f"validate_email('{email}'): {result}")
        
        print("\n=== Email Code Generation ===")
        code = gen_email_code()
        print(f"gen_email_code(): {code}")
        print(f"Length: {len(code)}")
        print(f"Is alphanumeric: {code.isalnum()}")
        
        print("\n=== Memory Usage ===")
        memory = get_memory_usage()
        print(f"get_memory_usage(): {memory}")
        print(f"Type: {type(memory)}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_functions() 