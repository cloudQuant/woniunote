"""
WoniuNote Tests Package

This package contains tests for WoniuNote application.
"""
import os
import sys

# Add the parent directory to the sys.path
# This ensures that we can import the woniunote package
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
