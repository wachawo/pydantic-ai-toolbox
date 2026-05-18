# RAGToolkit

Local retrieval-augmented generation: recursive character splitter plus an
in-memory numpy vector index with cosine similarity. Requires the `[rag]`
extra (numpy). No external vector database; the index can be persisted
atomically as a `.npz` + `.json` pair.

```python
from pydantic_ai_toolkits import RAGToolkit

rag = RAGToolkit(
    embedder=my_embedder,
    chunk_size=1000,
    chunk_overlap=100,
    storage_path="./index",
    distance="cosine",
    max_results=20,
    namespace="default",
)
```

## Constructor parameters

| Parameter       | Type                       | Default     | Notes                                                  |
|-----------------|----------------------------|-------------|--------------------------------------------------------|
| `embedder`      | `Embedder`                 | required    | Callable `list[str] -> list[list[float]]`              |
| `chunk_size`    | `int`                      | `1000`      | Must be > 0                                            |
| `chunk_overlap` | `int`                      | `100`       | Must be >= 0 and strictly < `chunk_size`               |
| `storage_path`  | `str | PathLike | None`    | `None`      | Base path; parent directory must exist                  |
| `distance`      | `Literal["cosine"]`        | `"cosine"`  | Only cosine is supported in v1                         |
| `max_results`   | `int`                      | `20`        | Hard cap on `k` returned by `search`                   |
| `namespace`    | `str`                      | `"default"` | Matches `^[A-Za-z0-9_.\-]{1,64}$`                      |

## Tools

| Tool              | Signature                                                                  | Notes                                |
|-------------------|----------------------------------------------------------------------------|--------------------------------------|
| `add_text`        | `(text: str, metadata: dict | None = None, doc_id: str | None = None)`     | returns new chunk ids                |
| `add_file`        | `(path: str, metadata=None, doc_id=None, encoding="utf-8")`                | refuses files > 10 MB                |
| `add_documents`   | `(documents: list[dict]) -> list[str]`                                     | each dict: `{text, metadata?, id?}`  |
| `search`          | `(query: str, k: int | None = None, filter: dict | None = None)`           | exact-match metadata filter; capped at `max_results` |
| `count`           | `() -> int`                                                                | total chunks in the index            |
| `list_documents`  | `(limit: int | None = None, offset: int = 0) -> list[dict]`                | `{doc_id, chunks}`, sorted by id     |
| `delete_document` | `(doc_id: str) -> int`                                                     | returns chunks removed (0 if absent) |
| `clear`           | `() -> int`                                                                | drops every chunk                    |
| `save`            | `(path: str | None = None) -> str`                                         | writes `<base>.npz` + `<base>.json`  |
| `load`            | `(path: str | None = None) -> int`                                         | overwrites in-memory state           |

The `chunk_count` property mirrors `count()` and is intended for
introspection in tests.

## Embedder

`Embedder` is a `Protocol`. Any callable that maps a list of strings to a
matching list of equal-length float vectors is accepted — there is no base
class to subclass.

```python
from typing import Protocol


class Embedder(Protocol):
    def __call__(self, texts: list[str]) -> list[list[float]]: ...
```

A minimal deterministic stub (no external services), useful for tests:

```python
import hashlib


def stub_embedder(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for t in texts:
        digest = hashlib.sha256(t.encode("utf-8")).digest()[:32]
        out.append([(b - 128) / 128.0 for b in digest])
    return out
```

To swap in a real embedder (e.g. OpenAI), replace the callable without
touching the toolkit configuration.

## Document

`Document` is a simple dataclass used by `add_documents` callers and
internal helpers. Per-chunk metadata is augmented at ingest time with
`doc_id` and `chunk_index`.

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Document:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str | None = None
```

## Splitter behaviour

`RAGToolkit` uses a recursive character splitter with a fixed separators
ladder: `["\n\n", "\n", " ", ""]`. It picks the longest separator that
actually appears in the text and falls through to finer separators when a
chunk still exceeds `chunk_size`. Adjacent chunks share up to
`chunk_overlap` characters to keep context across boundaries.

## Persistence

`save()` writes two sibling files atomically:

- `<base>.npz` — the vector matrix saved via `numpy.savez`.
- `<base>.json` — a sidecar with the schema version, splitter config, and
  the index payload (`ids`, `texts`, `metas`, `doc_index`, `dim`).

Both writes go to `.tmp` files and are committed with `os.replace`. A
sidecar with an unexpected `version` is rejected on `load()`.

```json
{
  "version": 1,
  "namespace": "default",
  "chunk_size": 1000,
  "chunk_overlap": 100,
  "distance": "cosine",
  "index": {
    "ids": ["doc-1:000000"],
    "texts": ["..."],
    "metas": [{"doc_id": "doc-1", "chunk_index": 0}],
    "doc_index": {"doc-1": [0]},
    "dim": 32
  }
}
```

## Examples

Build a small index with the stub embedder:

```python
from pydantic_ai_toolkits import RAGToolkit

rag = RAGToolkit(embedder=stub_embedder, chunk_size=200, chunk_overlap=20)
rag.add_text("Cats purr when content.", metadata={"topic": "cats"}, doc_id="d1")
rag.add_text("Dogs bark at strangers.", metadata={"topic": "dogs"}, doc_id="d2")
print(rag.count())
```

Query with a metadata filter:

```python
hits = rag.search("happy felines", k=3, filter={"topic": "cats"})
for h in hits:
    print(h["id"], round(h["score"], 3), h["text"])
```
