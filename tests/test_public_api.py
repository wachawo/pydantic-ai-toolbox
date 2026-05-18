#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public API surface: top-level lazy attribute access and re-exports."""

from __future__ import annotations

import pytest

import pydantic_ai_toolkits as pat
from pydantic_ai_toolkits import toolkits as pat_toolkits


def test_base_eager_exports() -> None:
    assert pat.BaseToolkit is not None
    assert callable(pat.tool)
    assert isinstance(pat.__version__, str)


@pytest.mark.parametrize(
    "name",
    ["FilesystemToolkit", "MemoryToolkit", "RAGToolkit", "SQLToolkit", "PandasToolkit", "Document", "Embedder"],
)
def test_lazy_attributes_resolve(name: str) -> None:
    if name == "RAGToolkit" or name in {"Document", "Embedder"}:
        pytest.importorskip("numpy")
    if name == "SQLToolkit":
        pytest.importorskip("sqlalchemy")
    if name == "PandasToolkit":
        pytest.importorskip("pandas")
    top_level = getattr(pat, name)
    sub_pkg = getattr(pat_toolkits, name)
    assert top_level is sub_pkg


def test_unknown_attribute_raises_at_top_level() -> None:
    missing = "NoSuchToolkit"
    with pytest.raises(AttributeError):
        getattr(pat, missing)


def test_unknown_attribute_raises_in_subpackage() -> None:
    missing = "NoSuchToolkit"
    with pytest.raises(AttributeError):
        getattr(pat_toolkits, missing)
