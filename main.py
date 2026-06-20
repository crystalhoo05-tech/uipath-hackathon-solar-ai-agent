"""Run the API with: python main.py"""

import sys
from pathlib import Path

# Allow running without `pip install -e .`
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from dotenv import load_dotenv

load_dotenv()

from hackathon_ai_uipath.api.app import run

if __name__ == "__main__":
    run()
