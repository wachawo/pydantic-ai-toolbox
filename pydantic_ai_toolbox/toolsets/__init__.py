#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Built-in toolsets.

Each submodule is independent — importing one does not import the others
and does not pull in their optional third-party dependencies. The lazy
`__getattr__` below preserves that property at package level: a missing
extra only raises when the corresponding toolset is actually accessed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = [
    "FilesystemToolset",
    "SQLToolset",
    "PandasToolset",
    "MemoryToolset",
    "RAGToolset",
    "Document",
    "Embedder",
]

if TYPE_CHECKING:
    from .filesystem import FilesystemToolset
    from .memory import MemoryToolset
    from .pandas import PandasToolset
    from .rag import Document, Embedder, RAGToolset
    from .sql import SQLToolset


def __getattr__(name: str):
    if name == "FilesystemToolset":
        from .filesystem import FilesystemToolset

        return FilesystemToolset
    if name == "SQLToolset":
        from .sql import SQLToolset

        return SQLToolset
    if name == "PandasToolset":
        from .pandas import PandasToolset

        return PandasToolset
    if name == "MemoryToolset":
        from .memory import MemoryToolset

        return MemoryToolset
    if name == "RAGToolset":
        from .rag import RAGToolset

        return RAGToolset
    if name == "Document":
        from .rag import Document

        return Document
    if name == "Embedder":
        from .rag import Embedder

        return Embedder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
