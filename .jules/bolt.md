## 2024-05-24 - Pandas iloc bottleneck
**Learning:** Using Pandas `.iloc` inside iterative loops is a major performance bottleneck for this codebase. The `get_extrema` and `find_divergences` functions were heavily impacted by iterative index access.
**Action:** Pre-extract columns into NumPy arrays using `.values` for fast index access. Prefer inline range checks over helper function calls in tight loops.
