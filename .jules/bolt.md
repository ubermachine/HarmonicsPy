## 2024-05-24 - Pandas iloc Loop Bottlenecks
**Learning:** Using Pandas `.iloc` inside iterative loops causes significant performance bottlenecks due to per-access overhead.
**Action:** Always pre-extract Pandas DataFrame columns into NumPy arrays using `.values` before iterating or accessing inside a tight loop to ensure fast index access.
