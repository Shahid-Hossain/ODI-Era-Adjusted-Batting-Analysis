"""Run every analysis script in order (01 -> 09). Usage: python src/run_all.py"""
import runpy
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
for script in sorted(SRC.glob("[0-9][0-9]_*.py")):
    print(f"\n=== {script.name}")
    runpy.run_path(str(script), run_name="__main__")
print("\nAll scripts finished. Charts in outputs/charts/, tables in outputs/tables/.")
