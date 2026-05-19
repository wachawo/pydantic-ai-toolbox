#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base class and decorator for class-based pydantic-ai toolsets."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar, overload

from pydantic_ai.toolsets import FunctionToolset

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

TOOL_MARKER_ATTR = "__toolset_tool__"
TOOL_NAME_ATTR = "__toolset_tool_name__"
TOOL_DESC_ATTR = "__toolset_tool_description__"
TOOL_TAKES_CTX_ATTR = "__toolset_tool_takes_ctx__"


@overload
def tool(fn: F) -> F: ...
@overload
def tool(
    *,
    name: str | None = ...,
    description: str | None = ...,
    takes_ctx: bool = ...,
) -> Callable[[F], F]: ...
def tool(
    fn: F | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    takes_ctx: bool = False,
) -> Callable[[F], F] | F:
    """Mark a method as a toolset tool.

    The marker is consumed by `BaseToolset.__init__`, which registers the bound
    method with the underlying `FunctionToolset`. Tool name defaults to the
    method name; description defaults to the method docstring.

    Use `takes_ctx=True` if the first parameter (after `self`) is a
    `RunContext[Deps]` that pydantic-ai should inject at call time.
    """

    def decorator(f: F) -> F:
        setattr(f, TOOL_MARKER_ATTR, True)
        setattr(f, TOOL_NAME_ATTR, name)
        setattr(f, TOOL_DESC_ATTR, description)
        setattr(f, TOOL_TAKES_CTX_ATTR, takes_ctx)
        return f

    if fn is None:
        return decorator
    return decorator(fn)


class BaseToolset(FunctionToolset):
    """Class-based toolset. Subclass and decorate methods with `@tool`.

    Subclasses configure themselves in `__init__` (paths, connections, limits)
    and then call `super().__init__()`, which scans `type(self)` for methods
    flagged by `@tool` and registers them as functions on the underlying
    `FunctionToolset`. The bound methods carry the toolset's configuration
    through `self`, so per-call arguments stay minimal.
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_decorated_methods()

    def register_decorated_methods(self) -> None:
        cls = type(self)
        for attr_name in dir(cls):
            if attr_name.startswith("_"):
                continue
            raw = getattr(cls, attr_name, None)
            if not callable(raw) or not getattr(raw, TOOL_MARKER_ATTR, False):
                continue
            bound = getattr(self, attr_name)
            tool_name = getattr(raw, TOOL_NAME_ATTR, None) or attr_name
            tool_desc = getattr(raw, TOOL_DESC_ATTR, None) or (raw.__doc__ or "").strip() or None
            takes_ctx = bool(getattr(raw, TOOL_TAKES_CTX_ATTR, False))
            self.add_function(
                bound,
                name=tool_name,
                takes_ctx=takes_ctx,
                description=tool_desc,
            )
            logger.debug(f"Registered tool {tool_name} from {cls.__name__}")


def main() -> None:
    pass


if __name__ == "__main__":
    main()
