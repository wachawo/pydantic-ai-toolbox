# pydantic-ai-toolkits

Modular, **independent** tool kits for [pydantic-ai](https://ai.pydantic.dev/)
agents. Each toolkit is a thin subclass of
`pydantic_ai.toolsets.FunctionToolset`. You configure one once (sandbox root,
DSN, vector store, ...) and pass it to one or more agents through the
standard `toolsets=` argument.

## Why "independent"

- The base package ships with no heavy dependencies; SQLAlchemy, pandas,
  and numpy are opt-in via extras.
- Toolkit modules **do not import each other**. Picking up
  `FilesystemToolkit` does not import `sqlalchemy`, `pandas`, or `numpy`.
- A missing extra only fails when the corresponding toolkit is actually
  instantiated — `import pydantic_ai_toolkits` always works.

## Relationship to pydantic-ai built-ins

Before reaching for a toolkit here, check whether pydantic-ai already
ships the capability you need:

| Need                                                | Use this                                                                     |
|-----------------------------------------------------|------------------------------------------------------------------------------|
| Web search                                          | `pydantic_ai.common_tools.{duckduckgo, exa, tavily}` or `native_tools.WebSearchTool` |
| Fetch a page and convert it to Markdown             | `pydantic_ai.common_tools.web_fetch.web_fetch_tool`                          |
| Provider-side code execution / image gen            | `pydantic_ai.native_tools.{CodeExecutionTool, ImageGenerationTool, FileSearchTool}` |
| Provider-managed long-term memory                   | `pydantic_ai.native_tools.MemoryTool`                                        |
| Bridge an external tool framework                   | `pydantic_ai.ext.*`                                                          |
| Plug in a third-party MCP server (fs, postgres, …)  | `pydantic_ai.mcp.MCPServerStdio` / `MCPServerHTTP`                           |

This library covers gaps the framework does not fill itself:

- **`FilesystemToolkit`** — local sandboxed filesystem (path-escape
  rejection, optional read-only). `native_tools.FileSearchTool` is
  OpenAI-side search over uploaded files, not local FS access.
- **`SQLToolkit`** — SQLAlchemy connection with a read-only guard.
- **`PandasToolkit`** — in-memory dataframe registry with common
  analysis ops.
- **`MemoryToolkit`** — local, agent-owned conversation/scratchpad
  memory (chat history, summary, buffer-window) — works without a
  provider memory feature and stores data on your side.
- **`RAGToolkit`** — local retrieval-augmented generation: text
  splitter, in-memory vector store, similarity search.

## Install

```bash
pip install pydantic-ai-toolkits                   # base only
pip install "pydantic-ai-toolkits[sql]"            # + SQLAlchemy
pip install "pydantic-ai-toolkits[pandas]"         # + pandas
pip install "pydantic-ai-toolkits[rag]"            # + numpy (for vector math)
pip install "pydantic-ai-toolkits[all]"            # everything
```

## Quickstart

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
        MemoryToolkit(),
        RAGToolkit(embedder=my_embedder),
    ],
    system_prompt="You are a data assistant.",
)

print(agent.run_sync("Read README.md from the workspace and summarise it.").output)
```

## Repository layout

```
pydantic-ai-toolkits/
├── pydantic_ai_toolkits/
│   ├── __init__.py          # public re-exports (lazy)
│   ├── base.py              # BaseToolkit + @tool decorator
│   ├── py.typed
│   └── toolkits/
│       ├── __init__.py
│       ├── filesystem.py    # no third-party deps
│       ├── sql.py           # extra: [sql]
│       ├── pandas.py        # extra: [pandas]
│       ├── memory.py        # extra: [memory] (stdlib only)
│       └── rag.py           # extra: [rag] (numpy)
├── tests/
├── examples/
├── docs/                    # mkdocs site
├── mkdocs.yml
├── pyproject.toml
├── requirements.txt
├── Makefile
├── .pre-commit-config.yaml
├── AGENTS.md
├── CHANGELOG.md
├── LICENSE
└── README.md
```

The shape mirrors `pydantic-ai`'s own repo (package directory at top level,
`toolkits/` subpackage analogous to `pydantic_ai/toolsets/` and
`pydantic_ai/common_tools/`, `tests/` flat at the top, `examples/` next to
it, mkdocs site under `docs/`).

## Toolkits

See [docs/](docs/) for the rendered reference. Short list:

- `FilesystemToolkit` — list / read / write / append / delete / mkdir /
  stat / glob, rooted at one directory.
- `SQLToolkit` — list_tables / list_views / describe_table / query /
  execute, with a read-only guard.
- `PandasToolkit` — list_dataframes / load_csv / load_parquet / head /
  describe / schema / query / aggregate / value_counts.
- `MemoryToolkit` — see [docs/MEMORY.md](docs/MEMORY.md).
- `RAGToolkit` — see [docs/RAG.md](docs/RAG.md).

## Writing your own toolkit

```python
from pydantic_ai_toolkits import BaseToolkit, tool


class WeatherToolkit(BaseToolkit):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        super().__init__()           # MUST be last — it scans @tool methods

    @tool
    def current_temperature(self, city: str) -> float:
        """Return the current temperature in Celsius for the given city."""
        ...
```

Rules:

1. Subclass `BaseToolkit`.
2. Configure `self.*` in `__init__`, then call `super().__init__()` as the
   last line.
3. Decorate every public method with `@tool`. Method name becomes the tool
   name; docstring becomes the description.
4. Use plain type hints — pydantic-ai builds the JSON schema from the
   signature.
5. Use `@tool(takes_ctx=True)` if the first method argument (after `self`)
   is a `RunContext[Deps]`.
6. Do not import another toolkit module from yours. Lazy-import any
   third-party library inside `__init__`.

See [AGENTS.md](AGENTS.md) for the full contribution guide and
[docs/](docs/) for the rendered site.

## Safety defaults

- `FilesystemToolkit` defaults to `read_only=True` and rejects path escapes.
- `SQLToolkit` defaults to `read_only=True` and refuses multi-statement input.
- `PandasToolkit` caps every row-returning tool at `max_query_rows`.
- `MemoryToolkit` caps message count and (optionally) total characters; persists atomically.
- `RAGToolkit` caps per-query result count and rejects oversized files in `add_file`.

## License

MIT.
