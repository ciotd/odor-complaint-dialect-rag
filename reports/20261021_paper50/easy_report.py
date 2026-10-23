"""Compatibility entry point for the consolidated report."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name("build_report.py")),run_name="__main__")
