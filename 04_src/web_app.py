"""Entry point:  streamlit run 04_src/web_app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contract_intel.interfaces.webapp import main  # noqa: E402

main()
