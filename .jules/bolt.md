## 2024-09-26 - Pandas `.iloc` Performance in Loops
**Learning:** Using `df['Column'].iloc[index]` inside loops (like in `get_extrema` and `find_divergences`) creates massive overhead due to Pandas indexing mechanisms. The current usage pattern takes O(N) but has a very high constant factor.
**Action:** Extract the column to a NumPy array first using `df['Column'].values` and index into that raw array. This reduced execution time by 30x in `get_extrema` and 6x in `find_divergences`.
