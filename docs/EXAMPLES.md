# Examples

Runnable scripts demonstrating individual toolsets and combinations.

| Script              | What it shows                                       |
|---------------------|-----------------------------------------------------|
| `quickstart.py`     | Multiple toolsets attached to one agent             |
| `memory_example.py` | `MemoryToolset` only: two-turn remember-and-recall  |
| `rag_example.py`    | `RAGToolset` only: deterministic stub embedder      |

Run them from the repository root with extras installed:

```bash
pip install -e ".[all]"
python examples/quickstart.py
```

Set `LLM_MODEL` and `DATABASE_URL` to point at your model and database.
