"""Root conftest — minimal, no DB init."""
import sys, os
_repo = os.path.dirname(os.path.abspath(__file__))
if _repo not in sys.path:
    sys.path.insert(0, _repo)
