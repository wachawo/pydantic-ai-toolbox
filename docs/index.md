# pydantic-ai-toolbox

Modular, **independent** tool kits for [pydantic-ai](https://ai.pydantic.dev/)
agents. Each toolset is a small subclass of `FunctionToolset` you configure
once and plug into one or more agents through the standard `toolsets=`
argument.

## Why

- **Independent modules.** Installing the package does not pull in
  SQLAlchemy, pandas, or numpy — extras opt in. Importing one toolset
  does not import the others. A toolset module never imports another
  toolset.
- **Class-based.** Per-toolset configuration (sandbox root, DSN, vector
  store, row caps) lives on the instance, so individual tool signatures
  stay minimal.
- **Same shape across kits.** Construct, pass to `Agent(toolsets=[...])`,
  done.

## Five-line quickstart

```python
from pydantic_ai import Agent
from pydantic_ai_toolbox import FilesystemToolset, MemoryToolset

agent = Agent(
    "openai:gpt-4o-mini",
    toolsets=[
        FilesystemToolset(root="./workspace", read_only=False),
        MemoryToolset(storage_path="./memory.json"),
    ],
)
print(agent.run_sync("Remember that the workspace holds my draft notes.").output)
```

See [Install](INSTALL.md) and the per-toolset pages for everything else.
