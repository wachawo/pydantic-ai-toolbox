#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public API for pydantic-ai-toolbox.

The base machinery (`BaseToolset`, `tool`) is loaded eagerly. Built-in
toolsets live in `pydantic_ai_toolbox.toolsets` and are exposed as
top-level attributes via lazy imports, so missing optional extras
never break `import pydantic_ai_toolbox`.

Each toolset module is self-contained — it depends only on `base` and
on its own optional third-party library; toolsets do not import one
another.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BaseToolset, tool

__version__ = "0.0.2"

__all__ = [
    "BaseToolset",
    "tool",
    "FilesystemToolset",
    "SQLToolset",
    "PandasToolset",
    "MemoryToolset",
    "RAGToolset",
    "Document",
    "Embedder",
]

if TYPE_CHECKING:
    # Eager imports for type checkers (PyCharm, pyright, mypy). At runtime
    # the lazy `__getattr__` below still controls when each toolset module
    # is actually imported, so missing extras only fail on first use.
    from .toolsets.filesystem import FilesystemToolset
    from .toolsets.memory import MemoryToolset
    from .toolsets.pandas import PandasToolset
    from .toolsets.rag import Document, Embedder, RAGToolset
    from .toolsets.sql import SQLToolset


def __getattr__(name: str):
    if name == "FilesystemToolset":
        from .toolsets.filesystem import FilesystemToolset

        return FilesystemToolset
    if name == "SQLToolset":
        from .toolsets.sql import SQLToolset

        return SQLToolset
    if name == "PandasToolset":
        from .toolsets.pandas import PandasToolset

        return PandasToolset
    if name == "MemoryToolset":
        from .toolsets.memory import MemoryToolset

        return MemoryToolset
    if name == "RAGToolset":
        from .toolsets.rag import RAGToolset

        return RAGToolset
    if name == "Document":
        from .toolsets.rag import Document

        return Document
    if name == "Embedder":
        from .toolsets.rag import Embedder

        return Embedder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
