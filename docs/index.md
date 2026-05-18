# pydantic-ai-toolkits

Modular, **independent** tool kits for [pydantic-ai](https://ai.pydantic.dev/)
agents. Each toolkit is a small subclass of `FunctionToolset` you configure
once and plug into one or more agents through the standard `toolsets=`
argument.

## Why

- **Independent modules.** Installing the package does not pull in
  SQLAlchemy, pandas, or numpy — extras opt in. Importing one toolkit
  does not import the others. A toolkit module never imports another
  toolkit.
- **Class-based.** Per-toolkit configuration (sandbox root, DSN, vector
  store, row caps) lives on the instance, so individual tool signatures
  stay minimal.
- **Same shape across kits.** Construct, pass to `Agent(toolsets=[...])`,
  done.

## Five-line quickstart

```python
from pydantic_ai import Agent
from pydantic_ai_toolkits import FilesystemToolkit, MemoryToolkit

agent = Agent(
    "openai:gpt-4o-mini",
    toolsets=[
        FilesystemToolkit(root="./workspace", read_only=False),
        MemoryToolkit(storage_path="./memory.json"),
    ],
)
print(agent.run_sync("Remember that the workspace holds my draft notes.").output)
```

See [Install](INSTALL.md) and the per-toolkit pages for everything else.
