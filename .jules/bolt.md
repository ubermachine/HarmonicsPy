## 2025-02-14 - Avoid Pandas .iloc in Iterative Loops
**Learning:** Using Pandas `.iloc` inside iterative loops causes severe performance degradation in this codebase (e.g., in `get_extrema` and `find_divergences`).
**Action:** Always pre-extract columns into NumPy arrays using `.values` for fast index access within tight loops.
