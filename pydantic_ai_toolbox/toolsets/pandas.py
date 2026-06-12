#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pandas dataframe toolset for pydantic-ai agents."""

from __future__ import annotations

import logging
from typing import Any

from ..base import BaseToolset, tool

logger = logging.getLogger(__name__)

DEFAULT_MAX_PREVIEW_ROWS = 100
DEFAULT_MAX_QUERY_ROWS = 1_000

SUPPORTED_AGG = {"count", "sum", "mean", "median", "min", "max", "std", "var", "nunique"}


class PandasToolset(BaseToolset):
    """Manage a named in-memory dataframe registry and expose common analysis ops.

    Dataframes are addressed by string name. Loaders register a frame under a
    name; analysis tools read it back. Row-returning tools cap output at
    `max_query_rows` to keep token usage bounded.
    """

    def __init__(
        self,
        dataframes: dict[str, Any] | None = None,
        max_preview_rows: int = DEFAULT_MAX_PREVIEW_ROWS,
        max_query_rows: int = DEFAULT_MAX_QUERY_ROWS,
    ) -> None:
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError(
                "PandasToolset requires pandas. Install via `pip install pydantic-ai-toolbox[pandas]`."
            ) from exc

        self.pd = pd
        self.dfs: dict[str, pd.DataFrame] = dict(dataframes or {})
        self.max_preview_rows = max_preview_rows
        self.max_query_rows = max_query_rows
        super().__init__()
        logger.info(f"PandasToolset ready: dataframes={list(self.dfs)}")

    def get_df(self, name: str) -> Any:
        if name not in self.dfs:
            raise KeyError(f"Unknown dataframe: {name!r}. Known: {list(self.dfs)}")
        return self.dfs[name]

    @tool
    def list_dataframes(self) -> list[dict]:
        """List registered dataframes with their row counts and columns."""
        return [{"name": name, "rows": int(len(df)), "columns": list(df.columns)} for name, df in self.dfs.items()]

    @tool
    def load_csv(self, name: str, path: str, **read_csv_kwargs: Any) -> dict:
        """Load a CSV file into the registry under `name`. Extra kwargs are passed to `pandas.read_csv`."""
        df = self.pd.read_csv(path, **read_csv_kwargs)
        self.dfs[name] = df
        logger.info(f"Loaded CSV {path} as {name!r} ({len(df)} rows, {len(df.columns)} cols)")
        return {"name": name, "rows": int(len(df)), "columns": list(df.columns)}

    @tool
    def load_parquet(self, name: str, path: str) -> dict:
        """Load a Parquet file into the registry under `name`."""
        df = self.pd.read_parquet(path)
        self.dfs[name] = df
        return {"name": name, "rows": int(len(df)), "columns": list(df.columns)}

    @tool
    def head(self, name: str, n: int = 5) -> list[dict]:
        """Return the first `n` rows of a dataframe as records."""
        n = min(n, self.max_preview_rows)
        return self.get_df(name).head(n).to_dict(orient="records")

    @tool
    def describe(self, name: str) -> dict:
        """Return summary statistics for the dataframe (numeric and categorical)."""
        return self.get_df(name).describe(include="all").to_dict()

    @tool
    def schema(self, name: str) -> dict:
        """Return per-column dtype and null count."""
        df = self.get_df(name)
        return {
            "rows": int(len(df)),
            "columns": [
                {"name": str(c), "dtype": str(df[c].dtype), "nulls": int(df[c].isna().sum())} for c in df.columns
            ],
        }

    @tool
    def query(self, name: str, expr: str, columns: list[str] | None = None, limit: int | None = None) -> list[dict]:
        """Filter a dataframe with `DataFrame.query(expr)` and return up to `limit` rows.

        `expr` uses pandas query syntax, e.g. `"price > 100 and country == 'US'"`.
        `columns` optionally projects to a subset.
        """
        cap = self.max_query_rows if limit is None else min(limit, self.max_query_rows)
        df = self.get_df(name).query(expr)
        if columns is not None:
            df = df[columns]
        return df.head(cap).to_dict(orient="records")

    @tool
    def aggregate(
        self,
        name: str,
        group_by: list[str],
        column: str,
        agg: str = "sum",
        limit: int | None = None,
    ) -> list[dict]:
        """Group by columns and aggregate one column with a named function (sum, mean, count, ...)."""
        if agg not in SUPPORTED_AGG:
            raise ValueError(f"Unsupported aggregation {agg!r}. Allowed: {sorted(SUPPORTED_AGG)}")
        cap = self.max_query_rows if limit is None else min(limit, self.max_query_rows)
        df = self.get_df(name)
        out = df.groupby(group_by)[column].agg(agg).reset_index()
        return out.head(cap).to_dict(orient="records")

    @tool
    def value_counts(self, name: str, column: str, limit: int = 20) -> list[dict]:
        """Return the most frequent values of a column as `[{value, count}, ...]`."""
        cap = min(limit, self.max_query_rows)
        series = self.get_df(name)[column].value_counts().head(cap)
        return [{"value": idx, "count": int(cnt)} for idx, cnt in series.items()]


def main() -> None:
    pass


if __name__ == "__main__":
    main()
