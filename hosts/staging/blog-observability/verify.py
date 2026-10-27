#!/usr/bin/env python3
"""Compatibility entry point; run on CT110."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[2] / 'infra/observability/verify.py'), run_name='__main__')
