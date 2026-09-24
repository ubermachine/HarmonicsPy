## 2024-09-24 - Pandas .iloc performance bottleneck
**Learning:** Using Pandas `.iloc` inside iterative loops causes significant overhead in tight loops.
**Action:** Pre-extract columns into NumPy arrays using `.values` for fast index access. Prefer inline range checks over helper function calls in tight loops.
