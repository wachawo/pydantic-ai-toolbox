# pydantic-ai-toolkits

[![CI](https://github.com/wachawo/pydantic-ai-toolkits/actions/workflows/ci.yml/badge.svg)](https://github.com/wachawo/pydantic-ai-toolkits/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pydantic-ai-toolkits.svg)](https://pypi.org/project/pydantic-ai-toolkits/)
[![Downloads](https://img.shields.io/pypi/dm/pydantic-ai-toolkits.svg)](https://pypi.org/project/pydantic-ai-toolkits/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/wachawo/pydantic-ai-toolkits/blob/main/LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/pydantic-ai-toolkits.svg)](https://pypi.org/project/pydantic-ai-toolkits/)

If you've used [pydantic-ai](https://github.com/pydantic/pydantic-ai), you already know
the feeling: it's the first agent framework that feels like a regular
Python library. Typed `RunContext`, a clean `FunctionToolset` protocol,
model providers swapped behind one string. After a decade of frameworks
that pretended to be Pythonic, this one actually is.

And then you sit down to wire up your agent, and realize: pydantic-ai
will happily call any tool you give it — but the tools themselves are
still on you. Want the agent to read a file? You write the sandbox.
Run a SQL query? You write the read-only guard and the schema
introspection. Search local documents? Text splitter, vector index,
cosine math, persistence — all you.

After the third project where you wrote those by hand, the shape stops
being interesting. This is them, written once:

```bash
pip install pydantic-ai-toolkits
```

```python
from pydantic_ai import Agent
from pydantic_ai_toolkits import (
    FilesystemToolkit, SQLToolkit, PandasToolkit, MemoryToolkit, RAGToolkit,
)

agent = Agent(
    "openai:gpt-4o-mini",
    toolsets=[
        FilesystemToolkit(root="./workspace", read_only=False),
        SQLToolkit(dsn="postgresql://user:pwd@localhost/app"),
        PandasToolkit(),
        MemoryToolkit(storage_path="./memory.json"),
        RAGToolkit(embedder=my_embedder),
    ],
    system_prompt="You are a data assistant.",
)

print(agent.run_sync("Read README.md from the workspace and summarise it.").output)
```

That's the whole story. Five toolkits, one `toolsets=[...]`, no new
framework on top of pydantic-ai — each toolkit is a thin
`FunctionToolset` subclass, exactly what pydantic-ai expects.

Each toolkit in isolation — runnable against a local/remote Ollama, no API keys:

- [Filesystem](examples/filesystem_example.py) — Example Create / Read / Append / Delete files
- [SQL](examples/sql_example.py) — Example INSERT, UPDATE, SELECT via SQLite
- [Pandas](examples/pandas_example.py) — Example load a CSV, count rows by condition
- [Memory](examples/memory_example.py) — Example three-turn conversation with persisted facts
- [RAG](examples/rag_example.py) — Example retrieve-then-answer, override the model prior
- [Quickstart](examples/quickstart.py) — Example minimal one-tool smoke test

---

## Install

```bash
pip install pydantic-ai-toolkits
```

The base install gives you `FilesystemToolkit` and `MemoryToolkit`
(stdlib only). The rest are opt-in so you only pull in what you use:

```bash
pip install "pydantic-ai-toolkits[sql]"      # + SQLAlchemy
pip install "pydantic-ai-toolkits[pandas]"   # + pandas + pyarrow
pip install "pydantic-ai-toolkits[rag]"      # + numpy
pip install "pydantic-ai-toolkits[all]"      # everything
```

Extras are independent — picking up one doesn't pull in the others.
Details: [docs/INSTALL.md](docs/INSTALL.md).

---

## Toolkits

| Toolkit                | What an agent can do with it                                   | Docs                                |
|------------------------|----------------------------------------------------------------|-------------------------------------|
| `FilesystemToolkit`    | List, read, write, append, delete, mkdir, stat, glob — under one sandbox root, with path-escape rejection and an optional read-only mode. | [docs/FILESYSTEM.md](docs/FILESYSTEM.md) |
| `SQLToolkit`           | List tables/views, describe schemas, run parameterised reads, optional `execute` for writes. Single-statement read-only by default. | [docs/SQL.md](docs/SQL.md)               |
| `PandasToolkit`        | Manage a named dataframe registry; load CSV/Parquet; head / describe / schema / query / aggregate / value_counts. | [docs/PANDAS.md](docs/PANDAS.md)         |
| `MemoryToolkit`        | Append/read/search messages; key-value scratchpad facts; optional atomic JSON persistence and per-namespace isolation. | [docs/MEMORY.md](docs/MEMORY.md)         |
| `RAGToolkit`           | Recursive character text splitter + in-memory numpy vector index with cosine search and per-document delete. | [docs/RAG.md](docs/RAG.md)               |

Tiny snippets to taste each one:

```python
# Filesystem — sandbox a workspace, then let the agent edit files
FilesystemToolkit(root="./workspace", read_only=False)

# SQL — read-only Postgres
SQLToolkit(dsn="postgresql://user:pwd@localhost/app")

# Pandas — start with an empty registry, agent loads CSVs as needed
PandasToolkit()

# Memory — persisted scratchpad, 200-message cap
MemoryToolkit(storage_path="./memory.json", max_messages=200)

# RAG — bring your own embedder
RAGToolkit(embedder=lambda texts: [embed(t) for t in texts])
```

Runnable end-to-end scripts live in [examples/](examples/) (see
[docs/EXAMPLES.md](docs/EXAMPLES.md)).

---

## What's not in here (and where to find it)

Before reaching for a toolkit here, check whether `pydantic-ai` already
ships the capability you need — most of the time it does:

| Need                                          | Use this                                                 |
|-----------------------------------------------|----------------------------------------------------------|
| Web search                                    | `pydantic_ai.common_tools.{duckduckgo, exa, tavily}` or `native_tools.WebSearchTool` |
| Fetch a page and convert to Markdown          | `pydantic_ai.common_tools.web_fetch.web_fetch_tool`      |
| Provider-side code execution / image gen      | `pydantic_ai.native_tools.{CodeExecutionTool, ImageGenerationTool, FileSearchTool}` |
| Provider-managed long-term memory             | `pydantic_ai.native_tools.MemoryTool`                    |
| Third-party MCP server (fs, postgres, …)      | `pydantic_ai.mcp.MCPServerStdio` / `MCPServerHTTP`       |

This package fills the gaps that aren't on that list — local sandboxed
filesystem access, generic SQL via SQLAlchemy, in-memory dataframe ops,
self-hosted conversation memory, and local RAG without an external
vector DB.

---

## Write your own toolkit

A toolkit is a `BaseToolkit` subclass whose public methods carry `@tool`:

```python
from pydantic_ai_toolkits import BaseToolkit, tool


class WeatherToolkit(BaseToolkit):
    """Look up current weather for a configurable provider."""

    def __init__(self, api_key: str, units: str = "metric") -> None:
        self.api_key = api_key
        self.units = units
        super().__init__()          # MUST be last — scans @tool methods

    @tool
    def current_temperature(self, city: str) -> float:
        """Return the current temperature for `city` in the configured units."""
        ...
```

Full rules, schema-mapping table, and the contribution checklist:
[docs/WRITING.md](docs/WRITING.md), [AGENTS.md](AGENTS.md).

---

## Install from git (latest unreleased)

```bash
pip install git+https://github.com/wachawo/pydantic-ai-toolkits.git
```

## Install from source (local development)

```bash
git clone git@github.com:wachawo/pydantic-ai-toolkits.git
cd pydantic-ai-toolkits
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
pip install -r requirements-dev.txt
pytest --cov          # 80% coverage gate
```

---

## Documentation

Rendered with MkDocs at [docs/](docs/):

- [Overview](docs/index.md)
- [Install](docs/INSTALL.md)
- Toolkits: [Filesystem](docs/FILESYSTEM.md), [SQL](docs/SQL.md), [Pandas](docs/PANDAS.md), [Memory](docs/MEMORY.md), [RAG](docs/RAG.md)
- [Write your own](docs/WRITING.md)
- [Examples](docs/EXAMPLES.md)
- [Building the docs site](docs/MKDOCS.md)
- [Changelog](CHANGELOG.md)

If something's off — a missing convenience method, an awkward
signature, a default that doesn't match your use case — the API is
intentionally small. Open an issue on
[GitHub](https://github.com/wachawo/pydantic-ai-toolkits/issues) and
say what you'd want instead.

---

## License

MIT.
