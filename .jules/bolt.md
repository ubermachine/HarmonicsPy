## 2025-03-01 - Avoid Pandas .iloc in Loops
**Learning:** Using Pandas `.iloc` to access individual rows inside iterative loops (like list comprehensions or standard `for` loops) causes significant performance overhead in this application's custom metrics calculations (e.g., in `get_extrema` and `find_divergences`).
**Action:** Always pre-extract columns into NumPy arrays using `.values` (e.g., `high_vals = df['High'].values`) and access them via standard indexing when inside tight loops.
