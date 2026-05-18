#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public API for pydantic-ai-toolkits.

The base machinery (`BaseToolkit`, `tool`) is loaded eagerly. Built-in
toolkits live in `pydantic_ai_toolkits.toolkits` and are exposed as
top-level attributes via lazy imports, so missing optional extras
never break `import pydantic_ai_toolkits`.

Each toolkit module is self-contained — it depends only on `base` and
on its own optional third-party library; toolkits do not import one
another.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BaseToolkit, tool

__version__ = "0.0.2"

__all__ = [
    "BaseToolkit",
    "tool",
    "FilesystemToolkit",
    "SQLToolkit",
    "PandasToolkit",
    "MemoryToolkit",
    "RAGToolkit",
    "Document",
    "Embedder",
]

if TYPE_CHECKING:
    # Eager imports for type checkers (PyCharm, pyright, mypy). At runtime
    # the lazy `__getattr__` below still controls when each toolkit module
    # is actually imported, so missing extras only fail on first use.
    from .toolkits.filesystem import FilesystemToolkit
    from .toolkits.memory import MemoryToolkit
    from .toolkits.pandas import PandasToolkit
    from .toolkits.rag import Document, Embedder, RAGToolkit
    from .toolkits.sql import SQLToolkit


def __getattr__(name: str):
    if name == "FilesystemToolkit":
        from .toolkits.filesystem import FilesystemToolkit

        return FilesystemToolkit
    if name == "SQLToolkit":
        from .toolkits.sql import SQLToolkit

        return SQLToolkit
    if name == "PandasToolkit":
        from .toolkits.pandas import PandasToolkit

        return PandasToolkit
    if name == "MemoryToolkit":
        from .toolkits.memory import MemoryToolkit

        return MemoryToolkit
    if name == "RAGToolkit":
        from .toolkits.rag import RAGToolkit

        return RAGToolkit
    if name == "Document":
        from .toolkits.rag import Document

        return Document
    if name == "Embedder":
        from .toolkits.rag import Embedder

        return Embedder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
