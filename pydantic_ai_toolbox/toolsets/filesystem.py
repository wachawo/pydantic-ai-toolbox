#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sandboxed filesystem toolset for pydantic-ai agents."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from ..base import BaseToolset, tool

logger = logging.getLogger(__name__)

DEFAULT_MAX_BYTES = 1_000_000
DEFAULT_MAX_GLOB_RESULTS = 500


class FilesystemToolset(BaseToolset):
    """Read and (optionally) write files under a single sandbox directory.

    All tool arguments are paths relative to `root`. Absolute paths and any
    `..` segments that escape `root` are rejected. Writes raise when the
    toolset is configured as read-only.
    """

    def __init__(
        self,
        root: str | os.PathLike[str],
        read_only: bool = True,
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_glob_results: int = DEFAULT_MAX_GLOB_RESULTS,
        encoding: str = "utf-8",
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.exists():
            raise FileNotFoundError(f"Root directory does not exist: {self.root}")
        if not self.root.is_dir():
            raise NotADirectoryError(f"Root is not a directory: {self.root}")
        self.read_only = read_only
        self.max_bytes = max_bytes
        self.max_glob_results = max_glob_results
        self.encoding = encoding
        super().__init__()
        logger.info(f"FilesystemToolset ready: root={self.root} read_only={self.read_only}")

    def resolve(self, rel: str) -> Path:
        if rel is None or rel == "":
            return self.root
        candidate = (self.root / rel).expanduser().resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError(f"Path escapes sandbox root: {rel}") from exc
        return candidate

    def require_writable(self) -> None:
        if self.read_only:
            raise PermissionError("FilesystemToolset is configured as read-only")

    @tool
    def list_dir(self, path: str = ".") -> list[str]:
        """List entries of a directory relative to the sandbox root. Directory entries are suffixed with `/`."""
        target = self.resolve(path)
        if not target.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        return sorted((entry.name + "/" if entry.is_dir() else entry.name) for entry in target.iterdir())

    @tool
    def read_file(self, path: str) -> str:
        """Return the text contents of a file. Fails if the file exceeds `max_bytes`."""
        target = self.resolve(path)
        if not target.is_file():
            raise FileNotFoundError(f"Not a file: {path}")
        size = target.stat().st_size
        if size > self.max_bytes:
            raise ValueError(f"File too large: {size} bytes > limit {self.max_bytes}")
        return target.read_text(encoding=self.encoding, errors="replace")

    @tool
    def write_file(self, path: str, content: str, overwrite: bool = True) -> bool:
        """Write text to a file, creating parent directories as needed. Returns True on success."""
        self.require_writable()
        target = self.resolve(path)
        if target.exists() and not overwrite:
            raise FileExistsError(f"File exists and overwrite=False: {path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=self.encoding)
        logger.info(f"Wrote {len(content)} chars to {target}")
        return True

    @tool
    def append_file(self, path: str, content: str) -> bool:
        """Append text to a file, creating parent directories as needed."""
        self.require_writable()
        target = self.resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding=self.encoding) as fh:
            fh.write(content)
        return True

    @tool
    def delete_file(self, path: str) -> bool:
        """Delete a single file. Refuses to delete directories."""
        self.require_writable()
        target = self.resolve(path)
        if target.is_dir():
            raise IsADirectoryError(f"Refusing to delete a directory: {path}")
        target.unlink(missing_ok=False)
        logger.info(f"Deleted {target}")
        return True

    @tool
    def make_dir(self, path: str) -> bool:
        """Create a directory (and parents) relative to the sandbox root."""
        self.require_writable()
        target = self.resolve(path)
        target.mkdir(parents=True, exist_ok=True)
        return True

    @tool
    def stat(self, path: str) -> dict:
        """Return basic metadata: kind, size in bytes, mtime as ISO string."""
        from datetime import datetime, timezone

        target = self.resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        st = target.stat()
        kind = "dir" if target.is_dir() else "file" if target.is_file() else "other"
        mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
        return {"path": path, "kind": kind, "size": st.st_size, "mtime": mtime}

    @tool
    def glob(self, pattern: str = "**/*", include_dirs: bool = False) -> list[str]:
        """Find paths matching a glob pattern relative to the sandbox root. Result truncated to `max_glob_results`."""
        result: list[str] = []
        for entry in self.root.glob(pattern):
            if entry.is_file() or (include_dirs and entry.is_dir()):
                result.append(str(entry.relative_to(self.root)))
                if len(result) >= self.max_glob_results:
                    break
        return result


def main() -> None:
    pass


if __name__ == "__main__":
    main()
