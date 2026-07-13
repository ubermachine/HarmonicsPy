## 2026-07-13 - [Pandas .iloc inside loops]
**Learning:** Avoid using Pandas `.iloc` inside iterative loops. Pre-extract columns into NumPy arrays using `.values` for fast index access. Prefer inline range checks over helper function calls in tight loops.
**Action:** Always extract `.values` before looping when accessing DataFrame elements by index in tight loops. Replace small helper functions with inline logic when they are called thousands of times in a loop.
