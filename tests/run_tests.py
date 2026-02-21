#!/usr/bin/env python
"""
Test runner script for Logifyx.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py -v           # Verbose output
    python run_tests.py --cov        # With coverage report
    python run_tests.py test_core    # Run specific test file
"""

import subprocess
import sys
import os

def main():
    # Change to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    # Base pytest command
    cmd = ["python", "-m", "pytest", "tests/"]
    
    # Add any command line args
    if len(sys.argv) > 1:
        # Check for special flags
        if "--cov" in sys.argv:
            cmd.extend(["--cov=logifyx", "--cov-report=term-missing"])
            sys.argv.remove("--cov")
        
        # Add remaining args
        cmd.extend(sys.argv[1:])
    else:
        # Default: verbose output
        cmd.append("-v")
    
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)
    
    # Run pytest
    result = subprocess.run(cmd)
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
