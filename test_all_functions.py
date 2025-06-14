#!/usr/bin/env python3
"""
Test script to catalog all available functions
"""

import sys
import os

# Add project root to path
sys.path.insert(0, '.')

def test_all_functions():
    try:
        from woniunote.common import utils
        
        print("=== Available Functions in utils module ===")
        
        # Get all functions
        functions = [name for name in dir(utils) if callable(getattr(utils, name)) and not name.startswith('_')]
        
        print(f"Found {len(functions)} functions:")
        for func_name in sorted(functions):
            func = getattr(utils, func_name)
            print(f"  - {func_name}: {func.__doc__.split('.')[0] if func.__doc__ else 'No description'}")
        
        print("\n=== Testing Key Functions ===")
        
        # Test validate_email
        print("validate_email:")
        print(f"  validate_email('test@example.com'): {utils.validate_email('test@example.com')}")
        print(f"  validate_email('invalid'): {utils.validate_email('invalid')}")
        
        # Test gen_email_code
        print("gen_email_code:")
        code = utils.gen_email_code()
        print(f"  gen_email_code(): {code} (length: {len(code)})")
        
        # Test get_memory_usage
        print("get_memory_usage:")
        memory = utils.get_memory_usage()
        print(f"  get_memory_usage(): {memory} (type: {type(memory)})")
        
        # Test validate_filename
        print("validate_filename:")
        print(f"  validate_filename('test.txt'): {utils.validate_filename('test.txt')}")
        print(f"  validate_filename('../test.txt'): {utils.validate_filename('../test.txt')}")
        
        # Test sanitize_input
        print("sanitize_input:")
        print(f"  sanitize_input('hello world'): '{utils.sanitize_input('hello world')}'")
        
        # Test generate_random_color
        print("generate_random_color:")
        color = utils.generate_random_color()
        print(f"  generate_random_color(): {color}")
        
        # Test hsv_to_rgb
        print("hsv_to_rgb:")
        rgb = utils.hsv_to_rgb(0.5, 0.8, 0.9)
        print(f"  hsv_to_rgb(0.5, 0.8, 0.9): {rgb}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_all_functions() 