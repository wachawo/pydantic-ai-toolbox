# PandasToolset

[README](https://github.com/wachawo/pydantic-ai-toolkits/blob/main/README.md)

In-memory dataframe registry plus common analysis ops. Requires the
`[pandas]` extra (which pulls in `pandas` and `pyarrow` so both CSV
and Parquet loaders work out of the box).

[Pandas](https://github.com/wachawo/pydantic-ai-toolkits/blob/main/examples/pandas_example.py) — Example load a CSV, count rows by condition

```python
import pandas as pd
from pydantic_ai_toolbox import PandasToolset

pd_kit = PandasToolset(
    dataframes={"orders": pd.read_csv("orders.csv")},
    max_preview_rows=100,
    max_query_rows=1_000,
)
```

Dataframes are addressed by string name. Loaders register a frame under
a name; analysis tools read it back. Every row-returning tool caps
output at `max_query_rows` so token usage stays bounded.

## Tools

| Tool              | Signature                                                       |
|-------------------|-----------------------------------------------------------------|
| `list_dataframes` | `() -> list[dict]`                                              |
| `load_csv`        | `(name, path, **read_csv_kwargs) -> dict`                       |
| `load_parquet`    | `(name, path) -> dict`                                          |
| `head`            | `(name, n=5) -> list[dict]`                                     |
| `describe`        | `(name) -> dict`                                                |
| `schema`          | `(name) -> dict`                                                |
| `query`           | `(name, expr, columns=None, limit=None) -> list[dict]`          |
| `aggregate`       | `(name, group_by, column, agg="sum", limit=None) -> list[dict]` |
| `value_counts`    | `(name, column, limit=20) -> list[dict]`                        |

Supported aggregations: `count`, `sum`, `mean`, `median`, `min`, `max`,
`std`, `var`, `nunique`.

## Sequencing load and analysis

An agent in a hurry will sometimes emit `load_csv` and `query` as
two parallel tool calls in the same assistant message. `query` then
races the load and fails with `Unknown dataframe`. The cure is in the
system prompt:

> Workflow: FIRST call `load_csv(name, path)` and WAIT for its result.
> Only AFTER load_csv returns, in a NEW assistant turn, call
> `query(name, expr)`. Never call load_csv and query in the same response.

## Working example

Single-prompt flow: load a CSV, count rows where price > 20. Full script:
`examples/pandas_example.py`.

```python
import tempfile
from pathlib import Path
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai_toolbox import PandasToolset

CSV = (
    "country,price,qty\n"
    "US,10,1\nUS,25,2\nDE,30,3\nFR,40,4\nDE,15,5\nUS,50,2\nFR,18,1\n"
)

with tempfile.TemporaryDirectory() as tmp:
    csv_path = Path(tmp) / "sales.csv"
    csv_path.write_text(CSV, encoding="utf-8")

    pd_kit = PandasToolset()
    agent = Agent(
        model=OpenAIChatModel(
            "qwen3:8b",
            provider=OpenAIProvider(base_url="http://localhost:11434/v1", api_key="ollama"),
        ),
        toolsets=[pd_kit],
        system_prompt=(
            "/no_think\n"
            "Workflow: FIRST call `load_csv(name, path)` and WAIT. Only "
            "AFTER it returns, in a NEW turn, call `query(name, expr)`. "
            "Never call load_csv and query in the same response. The "
            "number of rows returned by `query` IS the count."
        ),
    )

    reply = agent.run_sync(
        f"There is a CSV at {csv_path}. Load it as 'sales' and tell me "
        "how many rows have price greater than 20."
    )
    # → "The number of rows where price > 20 is 4."
```

## Direct (no-agent) flow

The same load + filter without an LLM
(`tests/test_example_flows.py::TestPandasFlow`):

```python
pd_kit = PandasToolset()
pd_kit.load_csv("sales", str(csv_path))
rows = pd_kit.query("sales", "price > 20", limit=1000)
assert len(rows) == 4
```
