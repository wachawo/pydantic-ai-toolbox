#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for PandasToolset."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pandas")

import pandas as pd  # noqa: E402

from pydantic_ai_toolbox.toolsets.pandas import PandasToolset  # noqa: E402


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "country": ["US", "US", "DE", "FR", "DE"],
            "price": [10, 20, 30, 40, 50],
            "qty": [1, 2, 3, 4, 5],
        }
    )


@pytest.fixture
def tk(sample_df: pd.DataFrame) -> PandasToolset:
    return PandasToolset(dataframes={"sales": sample_df})


class TestRegistry:
    def test_empty_construction(self) -> None:
        assert PandasToolset().list_dataframes() == []

    def test_list_dataframes(self, tk: PandasToolset) -> None:
        entries = tk.list_dataframes()
        assert entries == [{"name": "sales", "rows": 5, "columns": ["country", "price", "qty"]}]

    def test_unknown_dataframe_raises(self, tk: PandasToolset) -> None:
        with pytest.raises(KeyError, match="Unknown dataframe"):
            tk.head("missing")


class TestLoaders:
    def test_load_csv(self, tmp_path: Path) -> None:
        csv = tmp_path / "data.csv"
        csv.write_text("a,b\n1,2\n3,4\n")
        tk = PandasToolset()
        info = tk.load_csv("d", str(csv))
        assert info == {"name": "d", "rows": 2, "columns": ["a", "b"]}
        assert tk.head("d", n=10) == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]

    def test_load_parquet(self, tmp_path: Path, sample_df: pd.DataFrame) -> None:
        pytest.importorskip("pyarrow")
        pq = tmp_path / "data.parquet"
        sample_df.to_parquet(pq)
        tk = PandasToolset()
        info = tk.load_parquet("p", str(pq))
        assert info["rows"] == 5


class TestAnalysisOps:
    def test_head_caps_at_preview(self, sample_df: pd.DataFrame) -> None:
        tk = PandasToolset(dataframes={"x": sample_df}, max_preview_rows=2)
        assert len(tk.head("x", n=99)) == 2

    def test_describe(self, tk: PandasToolset) -> None:
        out = tk.describe("sales")
        assert "price" in out and "qty" in out

    def test_schema(self, tk: PandasToolset) -> None:
        s = tk.schema("sales")
        assert s["rows"] == 5
        names = {c["name"] for c in s["columns"]}
        assert names == {"country", "price", "qty"}

    def test_query(self, tk: PandasToolset) -> None:
        rows = tk.query("sales", "price > 20")
        assert {r["country"] for r in rows} == {"DE", "FR"}

    def test_query_columns_projection(self, tk: PandasToolset) -> None:
        rows = tk.query("sales", "price > 0", columns=["country"])
        assert all(set(r.keys()) == {"country"} for r in rows)

    def test_query_cap(self, sample_df: pd.DataFrame) -> None:
        tk = PandasToolset(dataframes={"x": sample_df}, max_query_rows=2)
        assert len(tk.query("x", "qty >= 0")) == 2

    def test_aggregate(self, tk: PandasToolset) -> None:
        rows = tk.aggregate("sales", group_by=["country"], column="price", agg="sum")
        by_country = {r["country"]: r["price"] for r in rows}
        assert by_country["US"] == 30
        assert by_country["DE"] == 80

    def test_aggregate_rejects_unknown_agg(self, tk: PandasToolset) -> None:
        with pytest.raises(ValueError, match="Unsupported aggregation"):
            tk.aggregate("sales", group_by=["country"], column="price", agg="bogus")

    def test_value_counts(self, tk: PandasToolset) -> None:
        rows = tk.value_counts("sales", "country", limit=10)
        by = {r["value"]: r["count"] for r in rows}
        assert by["US"] == 2
        assert by["DE"] == 2
        assert by["FR"] == 1
