# FilesystemToolkit

Sandboxed file ops rooted at a single directory. No third-party dependency
beyond the standard library.

```python
from pydantic_ai_toolkits import FilesystemToolkit

fs = FilesystemToolkit(
    root="./workspace",
    read_only=False,
    max_bytes=1_000_000,
    max_glob_results=500,
)
```

All tool arguments are paths **relative to `root`**. Absolute paths and any
`..` segments that escape `root` are rejected with `ValueError`. With
`read_only=True` (default), mutating tools raise `PermissionError`.

## Tools

| Tool          | Signature                                              | Notes                              |
|---------------|--------------------------------------------------------|------------------------------------|
| `list_dir`    | `(path: str = ".") -> list[str]`                        | dirs suffixed with `/`             |
| `read_file`   | `(path: str) -> str`                                    | rejects files over `max_bytes`     |
| `write_file`  | `(path: str, content: str, overwrite: bool = True)`     | creates parents                    |
| `append_file` | `(path: str, content: str) -> bool`                     | creates parents                    |
| `delete_file` | `(path: str) -> bool`                                   | refuses directories                |
| `make_dir`    | `(path: str) -> bool`                                   | `mkdir -p`                         |
| `stat`        | `(path: str) -> dict`                                   | kind, size, mtime ISO              |
| `glob`        | `(pattern: str = "**/*", include_dirs: bool = False)`   | capped at `max_glob_results`       |
