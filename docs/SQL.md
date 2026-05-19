# SQLToolset

[README](https://github.com/wachawo/pydantic-ai-toolkits/blob/main/README.md)

SQLAlchemy-backed schema introspection and parameterised queries.
Requires the `[sql]` extra.

[SQL](https://github.com/wachawo/pydantic-ai-toolkits/blob/main/examples/sql_example.py) — Example INSERT, UPDATE, SELECT via SQLite

```bash
pip install pydantic-ai-toolbox
```

```python
from pydantic_ai_toolbox import SQLToolset

db = SQLToolset(
    dsn="postgresql://user:pwd@localhost/app",
    read_only=True,
    max_rows=1_000,
)
```

By default the toolset accepts only `SELECT`/`WITH`/`SHOW`/`EXPLAIN`/`PRAGMA`
statements (single-statement, no trailing extras). Set `read_only=False`
to enable `execute()` against mutating statements.

## Tools

| Tool             | Signature                                                          | Notes                                  |
|------------------|--------------------------------------------------------------------|----------------------------------------|
| `list_tables`    | `(schema: str | None = None) -> list[str]`                         |                                        |
| `list_views`     | `(schema: str | None = None) -> list[str]`                         |                                        |
| `describe_table` | `(table: str, schema: str | None = None) -> dict`                  | name/type/nullable/default per col     |
| `query`          | `(sql: str, params: dict | None = None, limit: int | None = None)` | bind via `:name`; capped at `max_rows` |
| `execute`        | `(sql: str, params: dict | None = None) -> dict`                   | requires `read_only=False`             |

## Parameter style

`SQLToolset` runs statements through SQLAlchemy's `text()`, which uses
**named** placeholders. Always write `:name` and pass values via the
`params` dict whose keys match. Positional `?`-style placeholders will
raise `Incorrect number of bindings supplied`.

```python
db.execute(
    "INSERT INTO users (name, age) VALUES (:n, :a)",
    params={"n": "Alex", "a": 30},
)
```

## Working example

Three-turn agent flow over SQLite in a temp dir: INSERT → UPDATE → SELECT.
Full script: `examples/sql_example.py`.

```python
import tempfile
from pathlib import Path
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from sqlalchemy import create_engine, text
from pydantic_ai_toolbox import SQLToolset

with tempfile.TemporaryDirectory() as tmp:
    db_path = Path(tmp) / "demo.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, "
            "name TEXT NOT NULL, age INTEGER)"
        ))
    engine.dispose()

    sql = SQLToolset(dsn=f"sqlite:///{db_path}", read_only=False)
    agent = Agent(
        model=OpenAIChatModel(
            "qwen3:8b",
            provider=OpenAIProvider(base_url="http://localhost:11434/v1", api_key="ollama"),
        ),
        toolsets=[sql],
        system_prompt=(
            "/no_think\n"
            "You operate on a SQLite database via two tools: `query` for "
            "read-only SELECT statements, and `execute` for writes. "
            "ALWAYS use named SQLAlchemy placeholders like `:name`, NEVER "
            "positional `?`. Pass values via the `params` argument as a "
            "dict whose keys match the placeholders. Example: "
            "execute('INSERT INTO users (name, age) VALUES (:n, :a)', "
            "params={'n': 'Alex', 'a': 30})."
        ),
    )

    agent.run_sync("Insert a new user named Alex, age 30, into users.")
    agent.run_sync("Update Alex's age to 31.")
    agent.run_sync("Select every row from users and tell me what's there.")
    # → "id=1, name=Alex, age=31"
```

## Direct (no-agent) flow

The same sequence without an LLM
(`tests/test_example_flows.py::TestSQLFlow`):

```python
sql = SQLToolset(dsn=f"sqlite:///{db_path}", read_only=False)
sql.execute("INSERT INTO users (name, age) VALUES (:n, :a)", params={"n": "Alex", "a": 30})
sql.execute("UPDATE users SET age = :a WHERE name = :n", params={"a": 31, "n": "Alex"})
rows = sql.query("SELECT id, name, age FROM users ORDER BY id")
assert rows == [{"id": 1, "name": "Alex", "age": 31}]
```
