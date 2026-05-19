#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for RAGToolset."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("numpy")  # RAGToolset requires numpy; skip the file cleanly if absent.

from pydantic_ai_toolbox.toolsets.rag import (  # noqa: E402
    DEFAULT_MAX_FILE_BYTES,
    RAGToolset,
    split_text_recursively,
)


def deterministic_embedder(texts: list[str]) -> list[list[float]]:
    """Stable 3-D embedding derived purely from the text (no randomness)."""
    return [[float(len(t)), float(sum(map(ord, t)) % 97), 1.0] for t in texts]


def constant_embedder(texts: list[str]) -> list[list[float]]:
    """Returns the same unit vector for every text — produces tied scores."""
    return [[1.0, 0.0, 0.0] for _ in texts]


def four_dim_embedder(texts: list[str]) -> list[list[float]]:
    """4-D embedder used to trigger dimension-mismatch errors."""
    return [[1.0, 2.0, 3.0, 4.0] for _ in texts]


def make_tk(
    tmp_path: Path | None = None,
    embedder=deterministic_embedder,
    **overrides,
) -> RAGToolset:
    """Construct a RAGToolset with sane defaults for tests."""
    params: dict = {
        "embedder": embedder,
        "chunk_size": 50,
        "chunk_overlap": 5,
        "max_results": 10,
        "namespace": "test",
    }
    if tmp_path is not None:
        params["storage_path"] = tmp_path / "rag"
    params.update(overrides)
    return RAGToolset(**params)


class TestConstructorValidation:
    """RAGToolset constructor argument validation."""

    def test_defaults(self) -> None:
        tk = RAGToolset(embedder=deterministic_embedder)
        assert tk.chunk_size > 0
        assert tk.namespace == "default"
        assert tk.storage_path is None

    def test_chunk_overlap_strictly_less_than_chunk_size(self) -> None:
        RAGToolset(embedder=deterministic_embedder, chunk_size=100, chunk_overlap=99)
        with pytest.raises(ValueError, match="strictly less"):
            RAGToolset(embedder=deterministic_embedder, chunk_size=100, chunk_overlap=100)
        with pytest.raises(ValueError, match="strictly less"):
            RAGToolset(embedder=deterministic_embedder, chunk_size=100, chunk_overlap=200)

    def test_chunk_size_positive(self) -> None:
        with pytest.raises(ValueError, match="chunk_size"):
            RAGToolset(embedder=deterministic_embedder, chunk_size=0)
        with pytest.raises(ValueError, match="chunk_size"):
            RAGToolset(embedder=deterministic_embedder, chunk_size=-1)

    def test_chunk_overlap_non_negative(self) -> None:
        with pytest.raises(ValueError, match="chunk_overlap"):
            RAGToolset(embedder=deterministic_embedder, chunk_overlap=-1)

    def test_max_results_positive(self) -> None:
        with pytest.raises(ValueError, match="max_results"):
            RAGToolset(embedder=deterministic_embedder, max_results=0)

    def test_distance_must_be_cosine(self) -> None:
        with pytest.raises(ValueError, match="cosine"):
            RAGToolset(embedder=deterministic_embedder, distance="euclidean")  # type: ignore[arg-type]

    def test_embedder_must_be_callable(self) -> None:
        with pytest.raises((TypeError, ValueError)):
            RAGToolset(embedder="not-callable")  # type: ignore[arg-type]

    def test_namespace_regex(self) -> None:
        RAGToolset(embedder=deterministic_embedder, namespace="a.B_1-2")
        for bad in ("", "has space", "x" * 65, "ключ"):
            with pytest.raises(ValueError, match="namespace"):
                RAGToolset(embedder=deterministic_embedder, namespace=bad)

    def test_storage_parent_must_exist(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            RAGToolset(
                embedder=deterministic_embedder,
                storage_path=tmp_path / "missing" / "rag",
            )


class TestAddText:
    """add_text splitting + embedding + id format."""

    def test_add_text_returns_ids_per_chunk(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path, chunk_size=20, chunk_overlap=2)
        text = "abc def\n\n" + ("X" * 100)
        ids = tk.add_text(text, doc_id="doc1")
        assert len(ids) >= 1
        assert tk.chunk_count == len(ids)
        assert all(i.startswith("doc1:") for i in ids)

    def test_add_text_rejects_empty(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path)
        with pytest.raises(ValueError):
            tk.add_text("")
        with pytest.raises(ValueError):
            tk.add_text("   ")

    def test_dim_pinned_first_insert(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path)
        tk.add_text("hello world", doc_id="d1")
        assert tk.index.dim == 3
        # Switch embedder dim and try again → ValueError on add
        tk.embedder = four_dim_embedder  # type: ignore[assignment]
        with pytest.raises(ValueError, match="dimension"):
            tk.add_text("another", doc_id="d2")


class TestAddFile:
    """add_file: missing, oversized, source metadata."""

    def test_add_file_missing(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path)
        with pytest.raises(FileNotFoundError):
            tk.add_file(str(tmp_path / "nope.txt"))

    def test_add_file_oversized(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "big.txt"
        path.write_text("x", encoding="utf-8")
        # Patch the size limit to be tiny so we don't have to materialise 10 MB.
        monkeypatch.setattr("pydantic_ai_toolbox.toolsets.rag.DEFAULT_MAX_FILE_BYTES", 0)
        # Re-import-bound reference inside the module:
        import pydantic_ai_toolbox.toolsets.rag as rag_mod

        assert rag_mod.DEFAULT_MAX_FILE_BYTES == 0
        tk = make_tk(tmp_path)
        with pytest.raises(ValueError, match="too large"):
            tk.add_file(str(path))

    def test_add_file_attaches_source_metadata(self, tmp_path: Path) -> None:
        path = tmp_path / "doc.txt"
        path.write_text("hello world", encoding="utf-8")
        tk = make_tk(tmp_path)
        ids = tk.add_file(str(path), doc_id="docA")
        assert ids
        hits = tk.search("hello", k=5)
        assert hits
        assert hits[0]["metadata"]["source"].endswith("doc.txt")
        assert hits[0]["metadata"]["doc_id"] == "docA"

    def test_default_max_file_bytes_constant_is_10mb(self) -> None:
        assert DEFAULT_MAX_FILE_BYTES == 10_000_000


class TestAddDocuments:
    """add_documents: batch ingest validation."""

    def test_add_documents_basic(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path)
        ids = tk.add_documents(
            [
                {"text": "first text", "id": "a"},
                {"text": "second text", "id": "b", "metadata": {"k": "v"}},
            ]
        )
        assert len(ids) >= 2
        assert tk.chunk_count == len(ids)

    def test_add_documents_missing_text(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path)
        with pytest.raises(ValueError, match="text"):
            tk.add_documents([{"id": "x"}])
        with pytest.raises(ValueError, match="text"):
            tk.add_documents([{"text": ""}])


class TestSearch:
    """search: k clamping, ties, ordering, filters."""

    def test_search_clamps_k(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path, max_results=3)
        for i in range(5):
            tk.add_text(f"chunk text {i}" * 3, doc_id=f"d{i}")
        hits = tk.search("chunk", k=100)
        assert len(hits) <= 3

    def test_search_k_zero(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path)
        tk.add_text("anything", doc_id="d")
        assert tk.search("anything", k=0) == []

    def test_search_negative_k(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path)
        tk.add_text("x", doc_id="d")
        with pytest.raises(ValueError, match="k"):
            tk.search("x", k=-1)

    def test_search_results_sorted_desc(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path, chunk_size=200, chunk_overlap=10)
        for i, t in enumerate(["alpha", "beta hello", "hello world hello"]):
            tk.add_text(t, doc_id=f"d{i}")
        hits = tk.search("hello", k=5)
        scores = [h["score"] for h in hits]
        assert scores == sorted(scores, reverse=True)

    def test_search_tie_break_stable_insertion_order(self, tmp_path: Path) -> None:
        # Constant embedder → every score is 1.0 → ties broken by insertion order.
        tk = make_tk(tmp_path, embedder=constant_embedder, max_results=10)
        for i in range(5):
            tk.add_text(f"chunk-{i}", doc_id=f"d{i}")
        hits = tk.search("query", k=5)
        # All scores equal; ids in insertion order
        assert [h["id"] for h in hits] == [f"d{i}:000000" for i in range(5)]

    def test_search_filter_exact_match(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path)
        tk.add_text("alpha text", doc_id="a", metadata={"lang": "en"})
        tk.add_text("alpha text", doc_id="b", metadata={"lang": "fr"})
        hits = tk.search("alpha", k=10, filter={"lang": "fr"})
        assert all(h["metadata"]["lang"] == "fr" for h in hits)
        assert any(h["metadata"]["doc_id"] == "b" for h in hits)

    def test_search_empty_query_rejected(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path)
        with pytest.raises(ValueError):
            tk.search("")


class TestDeleteAndClear:
    """delete_document and clear semantics."""

    def test_delete_document_removes_chunks(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path)
        tk.add_text("keep this", doc_id="keep")
        ids = tk.add_text("remove this content", doc_id="drop")
        n = tk.delete_document("drop")
        assert n == len(ids)
        # Search must not surface dropped chunks
        for hit in tk.search("remove", k=10):
            assert hit["metadata"]["doc_id"] != "drop"

    def test_delete_document_missing(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path)
        assert tk.delete_document("never-was") == 0

    def test_clear_empties(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path)
        tk.add_text("hello", doc_id="d1")
        tk.add_text("world", doc_id="d2")
        n = tk.clear()
        assert n >= 2
        assert tk.chunk_count == 0
        assert tk.search("hello", k=5) == []


class TestPersistence:
    """save/load round-trip and refusal cases."""

    def test_save_load_roundtrip(self, tmp_path: Path) -> None:
        base = tmp_path / "rag"
        tk = make_tk(tmp_path, storage_path=base)
        tk.add_text("hello there friend", doc_id="d1", metadata={"k": "v"})
        tk.add_text("another chunk of text", doc_id="d2")
        tk.index.consolidate()
        original_ids = list(tk.index.ids)
        original_texts = list(tk.index.texts)
        original_metas = [dict(m) for m in tk.index.metas]
        original_vectors = tk.index.vectors.copy()
        original_dim = tk.index.dim
        original_doc_index = {k: list(v) for k, v in tk.index.doc_index.items()}

        tk.save()
        # Fresh toolset, same path, then load.
        tk2 = RAGToolset(
            embedder=deterministic_embedder,
            chunk_size=50,
            chunk_overlap=5,
            max_results=10,
            namespace="test",
            storage_path=base,
        )
        tk2.load()
        assert tk2.index.ids == original_ids
        assert tk2.index.texts == original_texts
        assert tk2.index.metas == original_metas
        assert tk2.index.dim == original_dim
        assert tk2.index.doc_index == original_doc_index
        # Vectors preserved numerically
        import numpy as np

        assert np.allclose(tk2.index.vectors, original_vectors)

    def test_load_refuses_missing(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path, storage_path=tmp_path / "absent")
        with pytest.raises(FileNotFoundError):
            tk.load()

    def test_load_refuses_bad_schema_version(self, tmp_path: Path) -> None:
        base = tmp_path / "rag"
        tk = make_tk(tmp_path, storage_path=base)
        tk.add_text("hello", doc_id="d1")
        tk.save()
        # Corrupt the sidecar version
        json_path = base.with_suffix(base.suffix + ".json")
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        payload["version"] = 999
        json_path.write_text(json.dumps(payload), encoding="utf-8")
        tk2 = make_tk(tmp_path, storage_path=base)
        with pytest.raises(ValueError, match="Unsupported"):
            tk2.load()


class TestSplitter:
    """split_text_recursively behaviour (module-level wrapper)."""

    def test_chunks_respect_size_with_overlap_allowance(self) -> None:
        text = ("hello world " * 50).strip()
        chunks = split_text_recursively(text, chunk_size=40, chunk_overlap=5)
        assert chunks
        for chunk in chunks:
            assert len(chunk) <= 40 + 5

    def test_no_empty_chunks(self) -> None:
        text = "a\n\nb\n\n\n\nc d\n e"
        chunks = split_text_recursively(text, chunk_size=10, chunk_overlap=2)
        assert all(c.strip() for c in chunks)

    def test_recursive_split_on_double_newline_first(self) -> None:
        text = "para1 word\n\npara2 word"
        chunks = split_text_recursively(text, chunk_size=15, chunk_overlap=0)
        # Both paragraphs should appear as their own chunks (small enough already).
        joined = " ".join(chunks)
        assert "para1" in joined and "para2" in joined

    def test_char_split_fallback_on_long_unbreakable(self) -> None:
        text = "x" * 250  # No separators present except "" → char split fallback.
        chunks = split_text_recursively(text, chunk_size=50, chunk_overlap=0)
        # Every char goes through, total length preserved.
        assert sum(len(c) for c in chunks) == 250


class TestChunkCount:
    """chunk_count property and count() tool agree."""

    def test_chunk_count_property_and_count_tool(self, tmp_path: Path) -> None:
        tk = make_tk(tmp_path)
        assert tk.chunk_count == 0
        assert tk.count() == 0
        tk.add_text("hello world hello world hello", doc_id="d1")
        assert tk.chunk_count == tk.count()
        assert tk.count() > 0


def main() -> None:
    pass


if __name__ == "__main__":
    main()
