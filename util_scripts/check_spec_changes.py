#!/usr/bin/env python3
"""Convenience script to check for A2A specification changes."""

import os
import subprocess
import sys


def main():
    """Run the spec change tracker."""
    # Get the project root directory (two levels up from this script)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Build command to run the spec tracker's main script
    # The spec_tracker/main.py script needs to be run from the project root
    spec_tracker_script = os.path.join(project_root, "spec_tracker", "main.py")

    cmd = [sys.executable, spec_tracker_script] + sys.argv[1:]  # Forward all arguments

    try:
        # Run the command from the project root and capture exit code
        result = subprocess.run(cmd, cwd=project_root, check=False)
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
