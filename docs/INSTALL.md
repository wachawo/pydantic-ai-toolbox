# Install

The base package brings in no heavy dependencies — extras opt in to
SQLAlchemy, pandas, or numpy as needed.

```bash
pip install pydantic-ai-toolkits                   # base only
pip install "pydantic-ai-toolkits[sql]"            # + SQLAlchemy
pip install "pydantic-ai-toolkits[pandas]"         # + pandas
pip install "pydantic-ai-toolkits[rag]"            # + numpy (vector math)
pip install "pydantic-ai-toolkits[all]"            # everything
```

`MemoryToolkit` is stdlib-only and has no extra. Importing
`pydantic_ai_toolkits` and any unaffected toolkit works without extras;
a missing extra only raises when you instantiate the toolkit that needs
it.
