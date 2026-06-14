# Purpose: Test configuration that makes project modules importable from every pytest file.
# Reason: Centralized path setup keeps tests simple and prevents repeated sys.path edits.
"""Root conftest - ensures the project root is on sys.path for all tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
