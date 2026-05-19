# FilesystemToolset

[README](https://github.com/wachawo/pydantic-ai-toolkits/blob/main/README.md)

Sandboxed file ops rooted at a single directory. No third-party
dependency beyond the standard library.

[Filesystem](https://github.com/wachawo/pydantic-ai-toolkits/blob/main/examples/filesystem_example.py) — Example Create / Read / Append / Delete files

```python
from pydantic_ai_toolbox import FilesystemToolset

fs = FilesystemToolset(
    root="./workspace",
    read_only=False,
    max_bytes=1_000_000,
    max_glob_results=500,
)
```

All tool arguments are paths **relative to `root`**. Absolute paths and
any `..` segments that escape `root` are rejected with `ValueError`.
With `read_only=True` (default), mutating tools raise `PermissionError`.

## Tools

| Tool          | Signature                                              | Notes                              |
|---------------|--------------------------------------------------------|------------------------------------|
| `list_dir`    | `(path: str = ".") -> list[str]`                       | dirs suffixed with `/`             |
| `read_file`   | `(path: str) -> str`                                   | rejects files over `max_bytes`     |
| `write_file`  | `(path: str, content: str, overwrite: bool = True)`    | creates parents                    |
| `append_file` | `(path: str, content: str) -> bool`                    | creates parents                    |
| `delete_file` | `(path: str) -> bool`                                  | refuses directories                |
| `make_dir`    | `(path: str) -> bool`                                  | `mkdir -p`                         |
| `stat`        | `(path: str) -> dict`                                  | kind, size, mtime ISO              |
| `glob`        | `(pattern: str = "**/*", include_dirs: bool = False)`  | capped at `max_glob_results`       |

## Working example

Six-turn agent flow: create → list → modify → read → delete → list. Full
script: `examples/filesystem_example.py`.

```python
import tempfile
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai_toolbox import FilesystemToolset

with tempfile.TemporaryDirectory() as tmp:
    fs = FilesystemToolset(root=tmp, read_only=False)

    agent = Agent(
        model=OpenAIChatModel(
            "qwen3:8b",
            provider=OpenAIProvider(base_url="http://localhost:11434/v1", api_key="ollama"),
        ),
        toolsets=[fs],
        system_prompt=(
            "/no_think\n"
            "You operate inside a sandboxed workspace. To create or overwrite "
            "a file call `write_file(path, content)`. To extend an existing "
            "file call `append_file`. To read use `read_file`. To list "
            "entries call `list_dir(path)`. To remove call `delete_file`. "
            "All paths are relative to the sandbox root — never use absolute "
            "paths or `..`."
        ),
    )

    agent.run_sync('Create a file named "notes.txt" with the text "hello".')
    agent.run_sync("List every file in the sandbox root.")          # ['notes.txt']
    agent.run_sync('Append a new line "second line" to notes.txt.')
    agent.run_sync("Read notes.txt and tell me what's in it.")      # 'hello\nsecond line'
    agent.run_sync("Delete notes.txt.")
    agent.run_sync("List every file in the sandbox root again.")    # []
```

The `/no_think` directive switches qwen3 out of its default chain-of-thought
mode — without it each turn generates 500-2000 reasoning tokens before any
tool call.

## Direct (no-agent) flow

If you just want the toolset's contract verified, the same flow without an
LLM is in `tests/test_example_flows.py::TestFilesystemFlow`:

```python
fs = FilesystemToolset(root=tmp_path, read_only=False)
fs.write_file("notes.txt", "hello")
assert "notes.txt" in fs.list_dir(".")
fs.append_file("notes.txt", "\nsecond line\n")
assert fs.read_file("notes.txt") == "hello\nsecond line\n"
fs.delete_file("notes.txt")
assert fs.list_dir(".") == []
```
