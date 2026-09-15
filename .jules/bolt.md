## 2024-10-27 - Avoid Pandas .iloc in Iterative Loops
**Learning:** Using Pandas `.iloc` inside iterative loops (e.g., in `get_extrema` and `find_divergences`) creates a severe performance bottleneck. Pandas lookup overhead dominates execution time when scanning large datasets or multiple symbols.
**Action:** Pre-extract columns into NumPy arrays using `.values` before the loop, and use standard array indexing. This simple change reduces execution time drastically.
