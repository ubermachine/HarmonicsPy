## 2024-09-22 - Avoid Pandas .iloc in critical loops
**Learning:** Pandas `.iloc` has a significant overhead when called repeatedly inside an iterative loop, slowing down array traversals in critical paths.
**Action:** Pre-extract columns to NumPy arrays using `.values` before entering the loop to ensure fast index access for iterative logic.