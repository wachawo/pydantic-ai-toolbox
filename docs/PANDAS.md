# PandasToolkit

In-memory dataframe registry plus common analysis ops. Requires the
`[pandas]` extra.

```python
import pandas as pd
from pydantic_ai_toolkits import PandasToolkit

pd_kit = PandasToolkit(
    dataframes={"orders": pd.read_csv("orders.csv")},
    max_preview_rows=100,
    max_query_rows=1_000,
)
```

Dataframes are addressed by string name. Loaders register a frame under
a name; analysis tools read it back. Every row-returning tool caps output
at `max_query_rows` so token usage stays bounded.

## Tools

| Tool              | Signature                                                                            |
|-------------------|--------------------------------------------------------------------------------------|
| `list_dataframes` | `() -> list[dict]`                                                                   |
| `load_csv`        | `(name, path, **read_csv_kwargs) -> dict`                                            |
| `load_parquet`    | `(name, path) -> dict`                                                               |
| `head`            | `(name, n=5) -> list[dict]`                                                          |
| `describe`        | `(name) -> dict`                                                                     |
| `schema`          | `(name) -> dict`                                                                     |
| `query`           | `(name, expr, columns=None, limit=None) -> list[dict]`                               |
| `aggregate`       | `(name, group_by, column, agg="sum", limit=None) -> list[dict]`                      |
| `value_counts`    | `(name, column, limit=20) -> list[dict]`                                             |

Supported aggregations: `count`, `sum`, `mean`, `median`, `min`, `max`,
`std`, `var`, `nunique`.
