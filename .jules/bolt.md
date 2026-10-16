## 2026-07-12 - Pandas .iloc performance in tight loops
**Learning:** Using Pandas `.iloc` to access single row elements inside of nested list comprehensions or loops (e.g. for `extrema` detection across 500 symbols) is significantly slower than using raw NumPy arrays.
**Action:** When iterating and needing fast indexed access inside a tight loop, extract `.values` into a NumPy array first before the loop.
