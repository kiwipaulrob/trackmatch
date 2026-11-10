"""String similarity 0..1 with an optional rapidfuzz accelerator.

`ratio(a, b)` uses rapidfuzz when installed, else difflib. Both backends
agree within 0.01 on everyday inputs; tests pin the stdlib behaviour and
only assert the tolerance band, never exact cross-backend equality.
"""

from difflib import SequenceMatcher

try:
    from rapidfuzz import fuzz as _fuzz

    BACKEND = "rapidfuzz"
except ImportError:  # stdlib fallback keeps core dependency-free
    _fuzz = None
    BACKEND = "stdlib"


def ratio(a, b):
    """Similarity in 0..1. Two empty strings are identical (1.0)."""
    a = a or ""
    b = b or ""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    if BACKEND == "rapidfuzz":
        return _fuzz.ratio(a, b) / 100.0
    return SequenceMatcher(None, a, b).ratio()
