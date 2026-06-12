# Install

The base package brings in no heavy dependencies — extras opt in to
SQLAlchemy, pandas, or numpy as needed.

```bash
pip install pydantic-ai-toolbox                   # base only
pip install "pydantic-ai-toolbox[sql]"            # + SQLAlchemy
pip install "pydantic-ai-toolbox[pandas]"         # + pandas
pip install "pydantic-ai-toolbox[rag]"            # + numpy (vector math)
pip install "pydantic-ai-toolbox[all]"            # everything
```

`MemoryToolset` is stdlib-only and has no extra. Importing
`pydantic_ai_toolbox` and any unaffected toolset works without extras;
a missing extra only raises when you instantiate the toolset that needs
it.
