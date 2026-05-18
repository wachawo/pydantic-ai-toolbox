#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLAlchemy-backed SQL toolkit for pydantic-ai agents."""

from __future__ import annotations

import logging
import re
from typing import Any

from ..base import BaseToolkit, tool

logger = logging.getLogger(__name__)

DEFAULT_MAX_ROWS = 1_000

WRITE_STATEMENT_RE = re.compile(
    r"^\s*(insert|update|delete|drop|truncate|alter|create|grant|revoke|merge|replace|call|do)\b",
    re.IGNORECASE,
)
COMMENT_RE = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)


def is_select_only(sql: str) -> bool:
    """Return True if `sql` is a single read-only statement (SELECT/WITH/SHOW/EXPLAIN/PRAGMA)."""
    stripped = COMMENT_RE.sub("", sql).strip().rstrip(";").strip()
    if not stripped:
        return False
    if ";" in stripped:
        return False
    if WRITE_STATEMENT_RE.match(stripped):
        return False
    head = stripped.split(None, 1)[0].lower()
    return head in {"select", "with", "show", "explain", "describe", "desc", "pragma"}


class SQLToolkit(BaseToolkit):
    """Run schema introspection and parameterised queries against a SQLAlchemy URL.

    By default the toolkit is read-only: only SELECT/WITH/SHOW/EXPLAIN/PRAGMA
    statements pass the guard. Set `read_only=False` to enable `execute`
    against mutating statements.
    """

    def __init__(
        self,
        dsn: str,
        read_only: bool = True,
        max_rows: int = DEFAULT_MAX_ROWS,
        engine_kwargs: dict[str, Any] | None = None,
    ) -> None:
        try:
            from sqlalchemy import create_engine
        except ImportError as exc:
            raise ImportError(
                "SQLToolkit requires sqlalchemy. Install via `pip install pydantic-ai-toolkits[sql]`."
            ) from exc

        self.engine = create_engine(dsn, **(engine_kwargs or {}))
        self.read_only = read_only
        self.max_rows = max_rows
        super().__init__()
        logger.info(
            f"SQLToolkit ready: dsn={self.engine.url.render_as_string(hide_password=True)} read_only={self.read_only}"
        )

    @tool
    def list_tables(self, schema: str | None = None) -> list[str]:
        """List user table names, optionally restricted to a schema."""
        from sqlalchemy import inspect

        return list(inspect(self.engine).get_table_names(schema=schema))

    @tool
    def list_views(self, schema: str | None = None) -> list[str]:
        """List view names, optionally restricted to a schema."""
        from sqlalchemy import inspect

        return list(inspect(self.engine).get_view_names(schema=schema))

    @tool
    def describe_table(self, table: str, schema: str | None = None) -> dict:
        """Return column metadata (name, type, nullable, default) for a table."""
        from sqlalchemy import inspect

        cols = inspect(self.engine).get_columns(table, schema=schema)
        return {
            "table": table,
            "schema": schema,
            "columns": [
                {
                    "name": c["name"],
                    "type": str(c.get("type")),
                    "nullable": bool(c.get("nullable", True)),
                    "default": c.get("default"),
                }
                for c in cols
            ],
        }

    @tool
    def query(self, sql: str, params: dict | None = None, limit: int | None = None) -> list[dict]:
        """Run a read-only SQL statement and return rows as a list of dicts.

        `params` binds named parameters (`:name`). Rows are capped at
        `min(limit, max_rows)`; the cap defaults to the toolkit `max_rows`.
        """
        from sqlalchemy import text

        if not is_select_only(sql):
            raise ValueError("query() only accepts a single read-only statement (SELECT/WITH/SHOW/EXPLAIN/PRAGMA)")
        cap = self.max_rows if limit is None else min(limit, self.max_rows)
        with self.engine.connect() as conn:
            rs = conn.execute(text(sql), params or {})
            rows = rs.mappings().fetchmany(cap)
            return [dict(r) for r in rows]

    @tool
    def execute(self, sql: str, params: dict | None = None) -> dict:
        """Run a mutating SQL statement. Disabled when the toolkit is read-only.

        Returns the affected `rowcount` (driver-dependent; may be -1 for some statements).
        """
        from sqlalchemy import text

        if self.read_only:
            raise PermissionError("SQLToolkit is configured as read-only")
        with self.engine.begin() as conn:
            result = conn.execute(text(sql), params or {})
            return {"rowcount": result.rowcount}


def main() -> None:
    pass


if __name__ == "__main__":
    main()
