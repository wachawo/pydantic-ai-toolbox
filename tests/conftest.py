#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """A throw-away workspace directory with a couple of sample files."""
    (tmp_path / "hello.txt").write_text("hello world\n", encoding="utf-8")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "data.csv").write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    return tmp_path
