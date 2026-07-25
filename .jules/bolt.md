## 2023-10-27 - Fast array access for Pandas Series in tight loops
**Learning:** Using Pandas `.iloc` for index-based access within iterative loops (like extrema and divergence detection) incurs significant overhead and acts as a performance bottleneck. Function calls within tight loops (like `in_range` checks) also slow down execution.
**Action:** Pre-extract Pandas columns to NumPy arrays using `.values` before iterating, and use these arrays for fast index access. Prefer inline condition checks over helper function calls inside intensive loops.
