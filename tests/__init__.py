"""Local test package; adds the repository's src layout to sys.path."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
