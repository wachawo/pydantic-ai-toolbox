#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Built-in toolkits.

Each submodule is independent — importing one does not import the others
and does not pull in their optional third-party dependencies. The lazy
`__getattr__` below preserves that property at package level: a missing
extra only raises when the corresponding toolkit is actually accessed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = [
    "FilesystemToolkit",
    "SQLToolkit",
    "PandasToolkit",
    "MemoryToolkit",
    "RAGToolkit",
    "Document",
    "Embedder",
]

if TYPE_CHECKING:
    from .filesystem import FilesystemToolkit
    from .memory import MemoryToolkit
    from .pandas import PandasToolkit
    from .rag import Document, Embedder, RAGToolkit
    from .sql import SQLToolkit


def __getattr__(name: str):
    if name == "FilesystemToolkit":
        from .filesystem import FilesystemToolkit

        return FilesystemToolkit
    if name == "SQLToolkit":
        from .sql import SQLToolkit

        return SQLToolkit
    if name == "PandasToolkit":
        from .pandas import PandasToolkit

        return PandasToolkit
    if name == "MemoryToolkit":
        from .memory import MemoryToolkit

        return MemoryToolkit
    if name == "RAGToolkit":
        from .rag import RAGToolkit

        return RAGToolkit
    if name == "Document":
        from .rag import Document

        return Document
    if name == "Embedder":
        from .rag import Embedder

        return Embedder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
