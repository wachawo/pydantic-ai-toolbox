# Examples

Runnable scripts demonstrating individual toolkits and combinations.

| Script              | What it shows                                       |
|---------------------|-----------------------------------------------------|
| `quickstart.py`     | Multiple toolkits attached to one agent             |
| `memory_example.py` | `MemoryToolkit` only: two-turn remember-and-recall  |
| `rag_example.py`    | `RAGToolkit` only: deterministic stub embedder      |

Run them from the repository root with extras installed:

```bash
pip install -e ".[all]"
python examples/quickstart.py
```

Set `LLM_MODEL` and `DATABASE_URL` to point at your model and database.
