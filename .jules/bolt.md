## 2025-02-09 - Pandas iloc optimization
**Learning:** Performance anti-pattern for this codebase: Avoid using Pandas `.iloc` inside iterative loops in `custom_harmonics.py` (`get_extrema` and `find_divergences`).
**Action:** Pre-extract columns into NumPy arrays using `.values` for fast index access. This gives a ~28x speedup for `get_extrema` and ~2.7x for `find_divergences`.
