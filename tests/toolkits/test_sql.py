#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for SQLToolkit (sqlite in-memory)."""

from __future__ import annotations

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy import text  # noqa: E402

from pydantic_ai_toolkits.toolkits.sql import SQLToolkit, is_select_only  # noqa: E402


def seed_engine(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, age INTEGER)"))
        conn.execute(text("INSERT INTO users (name, age) VALUES ('alice', 30), ('bob', 25), ('carol', 40)"))


@pytest.fixture
def rw_tk() -> SQLToolkit:
    tk = SQLToolkit(dsn="sqlite+pysqlite:///:memory:", read_only=False)
    seed_engine(tk.engine)
    return tk


@pytest.fixture
def ro_tk() -> SQLToolkit:
    tk = SQLToolkit(dsn="sqlite+pysqlite:///:memory:", read_only=True)
    seed_engine(tk.engine)
    return tk


class TestIsSelectOnly:
    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT * FROM t",
            "  select 1 ;",
            "WITH cte AS (SELECT 1) SELECT * FROM cte",
            "EXPLAIN SELECT * FROM t",
            "PRAGMA table_info(users)",
        ],
    )
    def test_accepts_reads(self, sql: str) -> None:
        assert is_select_only(sql) is True

    @pytest.mark.parametrize(
        "sql",
        [
            "INSERT INTO t VALUES (1)",
            "UPDATE t SET x=1",
            "DELETE FROM t",
            "DROP TABLE t",
            "SELECT 1; DROP TABLE t",  # multi-statement
            "",
            "   ",
            "-- only a comment",
        ],
    )
    def test_rejects_writes(self, sql: str) -> None:
        assert is_select_only(sql) is False


class TestSchema:
    def test_list_tables(self, ro_tk: SQLToolkit) -> None:
        assert "users" in ro_tk.list_tables()

    def test_list_views_empty(self, ro_tk: SQLToolkit) -> None:
        assert ro_tk.list_views() == []

    def test_describe_table(self, ro_tk: SQLToolkit) -> None:
        info = ro_tk.describe_table("users")
        names = [c["name"] for c in info["columns"]]
        assert names == ["id", "name", "age"]
        nullable_by_name = {c["name"]: c["nullable"] for c in info["columns"]}
        assert nullable_by_name["name"] is False


class TestQuery:
    def test_select_returns_rows(self, ro_tk: SQLToolkit) -> None:
        rows = ro_tk.query("SELECT name, age FROM users ORDER BY age")
        assert rows == [{"name": "bob", "age": 25}, {"name": "alice", "age": 30}, {"name": "carol", "age": 40}]

    def test_select_with_params(self, ro_tk: SQLToolkit) -> None:
        rows = ro_tk.query("SELECT name FROM users WHERE age >= :min_age", {"min_age": 30})
        assert {r["name"] for r in rows} == {"alice", "carol"}

    def test_query_caps_limit(self, ro_tk: SQLToolkit) -> None:
        rows = ro_tk.query("SELECT * FROM users", limit=1)
        assert len(rows) == 1

    def test_query_rejects_mutation(self, ro_tk: SQLToolkit) -> None:
        with pytest.raises(ValueError, match="read-only"):
            ro_tk.query("DELETE FROM users")


class TestExecute:
    def test_execute_blocked_in_read_only(self, ro_tk: SQLToolkit) -> None:
        with pytest.raises(PermissionError):
            ro_tk.execute("DELETE FROM users")

    def test_execute_works_when_writable(self, rw_tk: SQLToolkit) -> None:
        out = rw_tk.execute("DELETE FROM users WHERE name = :n", {"n": "bob"})
        assert out["rowcount"] == 1
        remaining = rw_tk.query("SELECT name FROM users ORDER BY name")
        assert [r["name"] for r in remaining] == ["alice", "carol"]
