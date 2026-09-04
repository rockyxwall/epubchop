#!/usr/bin/env python3
"""Backward-compatible runner for splitting Fantasy Simulator EPUB."""

import sys
from main import main

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv = ["main.py", "split", "Fantasy Simulator.epub", "--parts", "5"]
    main()
