#!/usr/bin/env python3
"""
Convenience script to check for A2A specification changes.
"""

import subprocess
import sys
import os

def main():
    """Run the spec change tracker."""
    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Build command to run the spec tracker
    cmd = [
        sys.executable,
        'spec_tracker/main.py'
    ] + sys.argv[1:]  # Forward all arguments
    
    try:
        # Run the command and capture exit code
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except FileNotFoundError:
        print("❌ Error: Python interpreter not found")
        return 1
    except KeyboardInterrupt:
        print("\n🛑 Analysis interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Error running spec change tracker: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 