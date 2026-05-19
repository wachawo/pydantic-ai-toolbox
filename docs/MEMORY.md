# MemoryToolset

[README](https://github.com/wachawo/pydantic-ai-toolkits/blob/main/README.md)

Local conversation buffer plus key/value scratchpad. Stdlib-only — no extra
required. State is held in memory and optionally persisted as a single JSON
file via an atomic temp-file + `os.replace` swap.

[Memory](https://github.com/wachawo/pydantic-ai-toolkits/blob/main/examples/memory_example.py) — Example three-turn conversation with persisted facts

```bash
pip install pydantic-ai-toolbox
```

```python
from pydantic_ai_toolbox import MemoryToolset

mem = MemoryToolset(
    storage_path="./memory.json",
    max_messages=200,
    max_chars=None,
    window=20,
    namespace="default",
    autosave=True,
)
```

Messages are appended in order and evicted oldest-first when either
`max_messages` or (if set) `max_chars` is exceeded. Facts are a JSON-serialisable
key/value map; both messages and facts are scoped by `namespace`.

## Constructor parameters

| Parameter      | Type                       | Default     | Notes                                                      |
|----------------|----------------------------|-------------|------------------------------------------------------------|
| `storage_path` | `str | PathLike | None`    | `None`      | Parent directory must exist. Loaded on construct if present|
| `max_messages` | `int`                      | `200`       | Must be > 0                                                |
| `max_chars`    | `int | None`               | `None`      | Optional total-char cap across messages                    |
| `window`       | `int`                      | `20`        | Default `k` for `get_recent_messages`                      |
| `namespace`    | `str`                      | `"default"` | Matches `^[A-Za-z0-9_.\-]{1,64}$`                          |
| `autosave`     | `bool`                     | `True`      | Persist after every mutation when `storage_path` is set    |

## Tools

| Tool                   | Signature                                          | Notes                                |
|------------------------|----------------------------------------------------|--------------------------------------|
| `add_message`          | `(role: str, content: str) -> str`                 | role in `user/assistant/system/tool` |
| `get_recent_messages`  | `(k: int | None = None) -> list[dict]`             | defaults to `window`                 |
| `get_all_messages`     | `() -> list[dict]`                                 | oldest first                         |
| `search_messages`      | `(query: str, limit: int = 10) -> list[dict]`      | case-insensitive substring           |
| `clear_messages`       | `() -> int`                                        | returns count cleared                |
| `set_fact`             | `(key: str, value: Any) -> bool`                   | value must be JSON-serialisable      |
| `get_fact`             | `(key: str) -> Any | None`                         | `None` if missing                    |
| `list_facts`           | `() -> dict[str, Any]`                             | values only                          |
| `delete_fact`          | `(key: str) -> bool`                               | `True` if existed                    |
| `summary`              | `() -> dict`                                       | namespace / counts / chars / path    |

## Persistence

When `storage_path` is set, the toolset serialises every namespace into a
single JSON file. Writes go to `<path>.tmp` and are committed with
`os.replace`, so readers never see a partial file.

```json
{
  "version": 1,
  "namespaces": {
    "default": {
      "messages": [
        {"id": "default-00000001", "role": "user", "content": "...", "ts": 1700000000.0}
      ],
      "facts": {
        "user.name": {"key": "user.name", "value": "Ada", "updated_ts": 1700000000.0}
      },
      "counter": 1
    }
  }
}
```

A snapshot with a different `version` is rejected on load.

## Read-only test seams

The `messages` and `facts` properties return deep copies of the current
namespace's state. They are intended for tests and introspection only;
mutating the returned objects does not affect the store.

```python
mem = MemoryToolset()
mem.add_message("user", "Hello")
mem.set_fact("favourite_color", "blue")

assert [m.role for m in mem.messages] == ["user"]
assert mem.facts["favourite_color"].value == "blue"
print(mem.summary())
```

## Working example

Three-turn flow: agent learns a name in turn 1, does unrelated work in
turn 2, recalls in turn 3 — even though no message history is carried
across runs. Full script:
`examples/memory_example.py`.

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai_toolbox import MemoryToolset

mem = MemoryToolset()
agent = Agent(
    model=OpenAIChatModel(
        "qwen3:8b",
        provider=OpenAIProvider(base_url="http://localhost:11434/v1", api_key="ollama"),
    ),
    toolsets=[mem],
    system_prompt=(
        "/no_think\n"
        "You are a helpful assistant with a persistent memory tool. "
        "When the user shares personal details, store them via `set_fact` "
        "using a clear key like `user_name`. When the user asks about "
        "something they told you earlier, look it up with `get_fact` or "
        "`list_facts` BEFORE answering. Do not invent facts."
    ),
)

agent.run_sync("Hi! My name is Alex.")              # → set_fact("user_name", "Alex")
agent.run_sync("What is 2 + 2 * 2?")                # → "6", no memory touched
agent.run_sync("Can you remind me what my name is?") # → get_fact, returns "Alex"
print(mem.list_facts())  # {'user_name': 'Alex'}
```

## Direct (no-agent) flow

The same flow without an LLM
(`tests/test_example_flows.py::TestMemoryFlow`):

```python
mem = MemoryToolset()
mem.set_fact("user_name", "Alex")
assert mem.get_fact("user_name") == "Alex"
assert mem.list_facts() == {"user_name": "Alex"}
```
