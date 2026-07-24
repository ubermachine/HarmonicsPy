## 2025-02-20 - Pandas .iloc overhead in tight loops
**Learning:** Using Pandas `.iloc` to access index or row data inside tight loops (like in list comprehensions or long running iterations) incurs significant function call and type checking overhead resulting in noticeable performance degradation.
**Action:** Always pre-extract Pandas DataFrame/Series columns to NumPy arrays using `.values` before iterating, which allows direct index access to primitive types, saving execution time inside loops.
