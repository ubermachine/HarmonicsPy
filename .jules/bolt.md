## 2025-07-17 - Pandas .iloc overhead in iterative loops
**Learning:** Avoid using Pandas `.iloc` inside iterative loops as it causes significant performance overhead in this codebase.
**Action:** Pre-extract columns into NumPy arrays using `.values` for fast index access. Prefer inline range checks over helper function calls in tight loops.
