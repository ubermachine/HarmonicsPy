## 2024-07-15 - Pandas .iloc performance anti-pattern
**Learning:** Using Pandas `.iloc` inside iterative loops (like the ones used in `get_extrema`, `find_divergences`, and `run_mass_scan` for custom indicators) is extremely slow and causes a massive bottleneck.
**Action:** Always extract columns to NumPy arrays via `.values` prior to iterating or indexing elements for fast O(1) lookups instead.
