## 2024-09-14 - Pandas .iloc Loop Bottleneck
**Learning:** Using Pandas `.iloc` for scalar lookups inside iterative loops (like list comprehensions in `get_extrema` and `for` loops in `find_divergences`) creates a severe performance bottleneck due to Pandas overhead.
**Action:** Always pre-extract Pandas Series columns into NumPy arrays using `.values` before looping, and access the arrays directly via standard list/array indexing.
