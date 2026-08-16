"""Permite ejecutar Talarium con:  python3 -m talarium"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
