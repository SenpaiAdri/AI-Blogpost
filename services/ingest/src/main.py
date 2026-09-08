"""Thin CLI entrypoint — all pipeline logic lives in :mod:`pipeline`."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.orchestrator import main

if __name__ == "__main__":
    main()
