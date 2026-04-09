"""Shared pytest configuration and path setup."""
import sys
from pathlib import Path

# Add the backend directory to sys.path so that imports like
# `from services.grading_service import ...` resolve correctly.
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
