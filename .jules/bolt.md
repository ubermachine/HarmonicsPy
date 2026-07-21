## 2024-07-21 - Avoiding .iloc in Pandas Loops
**Learning:** Using `.iloc` inside tight loops in pandas is a massive performance bottleneck. In this codebase, avoiding `.iloc` by pre-extracting columns into NumPy arrays (`.values`) sped up harmonic pattern scanning by over 6x (from 0.86s to 0.14s on 100k rows).
**Action:** When iterating over pandas DataFrames, always pre-extract necessary columns to NumPy arrays (`.values`) before the loop.
