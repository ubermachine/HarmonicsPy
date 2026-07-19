## 2024-05-24 - Pandas .iloc bottleneck
**Learning:** Pandas `.iloc` row-by-row lookups inside loop comprehensions create a massive performance bottleneck, especially in the harmonic pattern scanner's `get_extrema` and `find_divergences` functions.
**Action:** Extract the entire column as a NumPy array first using `.values` before the loop, and use standard array indexing. Also convert simple single-line helper functions used in loops to inline statements to avoid Python function call overhead.
