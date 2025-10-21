"""Pytest configuration for the simple Lambda workshop."""

import os
import sys
from pathlib import Path

# Ensure src/ is importable without installing as a package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# Sensible defaults for environment variables so tests can focus on behaviour.
os.environ.setdefault("FILES_TABLE", "files_table")
