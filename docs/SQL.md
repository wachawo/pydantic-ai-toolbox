# SQLToolkit

SQLAlchemy-backed schema introspection and parameterised queries. Requires
the `[sql]` extra.

```python
from pydantic_ai_toolkits import SQLToolkit

db = SQLToolkit(
    dsn="postgresql://user:pwd@localhost/app",
    read_only=True,
    max_rows=1_000,
)
```

By default the toolkit accepts only `SELECT`/`WITH`/`SHOW`/`EXPLAIN`/`PRAGMA`
statements (single-statement, no trailing extras). Set `read_only=False`
to enable `execute()` against mutating statements.

## Tools

| Tool             | Signature                                                                | Notes                                |
|------------------|--------------------------------------------------------------------------|--------------------------------------|
| `list_tables`    | `(schema: str | None = None) -> list[str]`                               |                                      |
| `list_views`     | `(schema: str | None = None) -> list[str]`                               |                                      |
| `describe_table` | `(table: str, schema: str | None = None) -> dict`                        | name/type/nullable/default per col   |
| `query`          | `(sql: str, params: dict | None = None, limit: int | None = None)`       | bind via `:name`; capped at `max_rows` |
| `execute`        | `(sql: str, params: dict | None = None) -> dict`                         | requires `read_only=False`            |
