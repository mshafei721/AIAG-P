"""
AUX Test Harness Main Entry Point.

This module provides the main entry point for the AUX test harness CLI.
It can be run directly or via the installed CLI command.
"""

import sys
from pathlib import Path

# Add the src directory to Python path to enable imports
src_dir = Path(__file__).parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from aux.testing.cli import app

if __name__ == "__main__":
    app()