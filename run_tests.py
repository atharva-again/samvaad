#!/usr/bin/env python3
"""
Test runner script for Samvaad RAG pipeline tests.
"""

import subprocess
import sys
import os

def run_tests(test_type=None):
    """Run tests based on type."""
    base_cmd = [sys.executable, "-m", "pytest"]

    if test_type == "unit":
        cmd = base_cmd + ["tests/unit/", "-m", "unit"]
    elif test_type == "integration":
        cmd = base_cmd + ["tests/integration/", "-m", "integration"]
    else:
        cmd = base_cmd + ["tests/"]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.path.dirname(__file__))
    return result.returncode

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        if test_type in ["unit", "integration"]:
            return run_tests(test_type)
        else:
            print("Usage: python run_tests.py [unit|integration]")
            print("  unit        - Run unit tests only")
            print("  integration - Run integration tests only")
            print("  (no arg)    - Run all tests")
            return 1
    else:
        return run_tests()

if __name__ == "__main__":
    sys.exit(main())