## 2024-05-24 - Pandas loop overhead
**Learning:** Pandas `.iloc` has a significant overhead when called repeatedly inside iterative loops.
**Action:** Pre-extract columns into NumPy arrays using `.values` before the loop and access indices on the array instead.
