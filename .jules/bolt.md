## 2024-05-24 - Pandas .iloc performance in loops
**Learning:** Using Pandas `.iloc` inside iterative loops in this codebase causes significant performance bottlenecks.
**Action:** Pre-extract columns into NumPy arrays using `.values` for fast index access inside loops.

## 2024-05-24 - Function call overhead in tight loops
**Learning:** Helper functions like `in_range` inside tight loops (like nested iterations in pattern finding) introduce unnecessary function call overhead.
**Action:** Prefer inline range checks (e.g. `lo <= val <= hi`) over helper function calls in tight loops for better performance.
