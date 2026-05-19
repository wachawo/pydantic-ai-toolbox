#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for FilesystemToolset."""

from __future__ import annotations

from pathlib import Path

import pytest

from pydantic_ai_toolbox.toolsets.filesystem import FilesystemToolset


class TestConstructorValidation:
    def test_root_must_exist(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            FilesystemToolset(root=tmp_path / "missing")

    def test_root_must_be_directory(self, tmp_path: Path) -> None:
        f = tmp_path / "not-a-dir"
        f.write_text("x")
        with pytest.raises(NotADirectoryError):
            FilesystemToolset(root=f)

    def test_defaults_to_read_only(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace)
        assert tk.read_only is True


class TestListDir:
    def test_list_root(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace)
        entries = tk.list_dir(".")
        assert "hello.txt" in entries
        assert "nested/" in entries

    def test_list_nested(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace)
        entries = tk.list_dir("nested")
        assert "data.csv" in entries

    def test_list_non_dir_raises(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace)
        with pytest.raises(NotADirectoryError):
            tk.list_dir("hello.txt")


class TestReadFile:
    def test_read_existing(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace)
        assert tk.read_file("hello.txt").startswith("hello world")

    def test_read_missing_raises(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace)
        with pytest.raises(FileNotFoundError):
            tk.read_file("absent.txt")

    def test_read_too_large(self, tmp_workspace: Path) -> None:
        big = tmp_workspace / "big.txt"
        big.write_text("x" * 200)
        tk = FilesystemToolset(root=tmp_workspace, max_bytes=100)
        with pytest.raises(ValueError, match="too large"):
            tk.read_file("big.txt")


class TestWriteOps:
    def test_write_requires_writable(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace, read_only=True)
        with pytest.raises(PermissionError):
            tk.write_file("new.txt", "content")

    def test_write_creates_parents(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace, read_only=False)
        assert tk.write_file("a/b/c.txt", "hi") is True
        assert (tmp_workspace / "a" / "b" / "c.txt").read_text() == "hi"

    def test_write_refuses_overwrite_when_disabled(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace, read_only=False)
        tk.write_file("x.txt", "first")
        with pytest.raises(FileExistsError):
            tk.write_file("x.txt", "second", overwrite=False)

    def test_append_file(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace, read_only=False)
        tk.write_file("log.txt", "line1\n")
        tk.append_file("log.txt", "line2\n")
        assert (tmp_workspace / "log.txt").read_text() == "line1\nline2\n"

    def test_delete_file(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace, read_only=False)
        target = tmp_workspace / "doomed.txt"
        target.write_text("bye")
        tk.delete_file("doomed.txt")
        assert not target.exists()

    def test_delete_refuses_directory(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace, read_only=False)
        with pytest.raises(IsADirectoryError):
            tk.delete_file("nested")

    def test_make_dir(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace, read_only=False)
        tk.make_dir("brand/new")
        assert (tmp_workspace / "brand" / "new").is_dir()


class TestPathEscape:
    def test_rejects_parent_escape(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace)
        with pytest.raises(ValueError, match="escapes sandbox"):
            tk.read_file("../outside.txt")

    def test_rejects_absolute_path_outside(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace)
        with pytest.raises(ValueError, match="escapes sandbox"):
            tk.read_file("/etc/passwd")


class TestStat:
    def test_stat_file(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace)
        meta = tk.stat("hello.txt")
        assert meta["kind"] == "file"
        assert meta["size"] > 0
        assert "T" in meta["mtime"]

    def test_stat_dir(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace)
        assert tk.stat("nested")["kind"] == "dir"

    def test_stat_missing(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace)
        with pytest.raises(FileNotFoundError):
            tk.stat("absent")


class TestGlob:
    def test_glob_files_only(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace)
        results = tk.glob("**/*")
        assert "hello.txt" in results
        assert any(r.endswith("data.csv") for r in results)
        assert "nested" not in results  # dirs excluded by default

    def test_glob_include_dirs(self, tmp_workspace: Path) -> None:
        tk = FilesystemToolset(root=tmp_workspace)
        results = tk.glob("**/*", include_dirs=True)
        assert "nested" in results

    def test_glob_respects_limit(self, tmp_workspace: Path) -> None:
        for i in range(20):
            (tmp_workspace / f"f{i}.txt").write_text("x")
        tk = FilesystemToolset(root=tmp_workspace, max_glob_results=5)
        assert len(tk.glob("*.txt")) == 5
