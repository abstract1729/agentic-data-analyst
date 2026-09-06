SQL_TOOL_DESCRIPTION = (
    """Execute a read-only SQL query against the DuckDB database. 
    Use SQL for database-oriented analysis including filtering, 
    aggregation, grouping, joins, sorting, and temporal analysis. 
    Only use SQL when the required analysis can be performed 
    through the database."""
)


PYTHON_TOOL_DESCRIPTION = (
    """Execute Python/Pandas/NumPy analysis in a restricted environment. 
    IMPORTANT: The Python environment is intentionally sandboxed and does not support imports.
    NEVER generate:
        import pandas as pd
        import numpy as np
        from pandas import ...
        from numpy import ...

    These objects are already initialized:
        pd
        np
        query(sql)
    pandas is already available as `pd`. 
    NumPy is already available as `np`. 
    The read-only database helper is already available as 
    `query(sql)` and returns a Pandas DataFrame. 
    Use `query(sql)` to retrieve only the data required for analysis. 
    Use Python for statistical calculations, dataframe 
    transformations, and numerical analysis. 
    The final output must be stored in a variable named `result`. 
    Write normal Python code with actual line breaks; 
    do not encode newlines as literal `\\n` sequences."""
)