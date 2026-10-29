"""Entry point:  python 04_src/cli.py search "<question>"   (same as: python -m contract_intel ...)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contract_intel.interfaces.cli import app  # noqa: E402

if __name__ == "__main__":
    app()
