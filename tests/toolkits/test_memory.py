#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for MemoryToolkit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pydantic_ai_toolkits.toolkits.memory import (
    DEFAULT_MAX_MESSAGES,
    DEFAULT_WINDOW,
    MemoryToolkit,
)


def make_toolkit(tmp_path: Path, **overrides) -> MemoryToolkit:
    """Construct a MemoryToolkit using `tmp_path` for storage by default."""
    params: dict = {
        "storage_path": tmp_path / "mem.json",
        "max_messages": 100,
        "window": 5,
        "namespace": "test",
        "autosave": True,
    }
    params.update(overrides)
    return MemoryToolkit(**params)


class TestConstructorValidation:
    """Constructor argument validation."""

    def test_default_construction(self) -> None:
        tk = MemoryToolkit()
        assert tk.max_messages == DEFAULT_MAX_MESSAGES
        assert tk.window == DEFAULT_WINDOW
        assert tk.namespace == "default"
        assert tk.storage_path is None

    def test_max_messages_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="max_messages"):
            MemoryToolkit(max_messages=0)
        with pytest.raises(ValueError, match="max_messages"):
            MemoryToolkit(max_messages=-1)

    def test_max_chars_must_be_positive_or_none(self) -> None:
        MemoryToolkit(max_chars=None)
        MemoryToolkit(max_chars=10)
        with pytest.raises(ValueError, match="max_chars"):
            MemoryToolkit(max_chars=0)
        with pytest.raises(ValueError, match="max_chars"):
            MemoryToolkit(max_chars=-5)

    def test_window_must_be_non_negative(self) -> None:
        MemoryToolkit(window=1)
        MemoryToolkit(window=0)
        with pytest.raises(ValueError, match="window"):
            MemoryToolkit(window=-1)

    def test_namespace_regex_enforced(self) -> None:
        MemoryToolkit(namespace="abc.DEF_1-2")
        for bad in ("", "has space", "with/slash", "x" * 65, "тест"):
            with pytest.raises(ValueError, match="namespace"):
                MemoryToolkit(namespace=bad)

    def test_storage_parent_must_exist(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            MemoryToolkit(storage_path=tmp_path / "missing_dir" / "mem.json")

    def test_corrupted_json_raises_value_error(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.json"
        path.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(ValueError, match="Corrupted"):
            MemoryToolkit(storage_path=path)

    def test_unknown_schema_version_raises_value_error(self, tmp_path: Path) -> None:
        path = tmp_path / "wrongver.json"
        path.write_text(json.dumps({"version": 999, "namespaces": {}}), encoding="utf-8")
        with pytest.raises(ValueError, match="Unsupported"):
            MemoryToolkit(storage_path=path)


class TestAddMessage:
    """add_message validation, id format, eviction."""

    def test_role_allowlist(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        for role in ("user", "assistant", "system", "tool"):
            tk.add_message(role, "hello")
        with pytest.raises(ValueError, match="Invalid role"):
            tk.add_message("nobody", "hi")

    def test_empty_content_rejected(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        with pytest.raises(ValueError, match="non-empty"):
            tk.add_message("user", "")
        with pytest.raises(ValueError, match="non-empty"):
            tk.add_message("user", "   ")

    def test_id_format_deterministic(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path, namespace="abc")
        ids = [tk.add_message("user", f"m{i}") for i in range(3)]
        assert ids == ["abc-00000001", "abc-00000002", "abc-00000003"]

    def test_eviction_by_max_messages(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path, max_messages=3)
        for i in range(5):
            tk.add_message("user", f"m{i}")
        msgs = tk.get_all_messages()
        assert len(msgs) == 3
        assert [m["content"] for m in msgs] == ["m2", "m3", "m4"]

    def test_eviction_by_max_chars(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path, max_messages=100, max_chars=10)
        tk.add_message("user", "abcde")  # 5
        tk.add_message("user", "fghij")  # 10
        tk.add_message("user", "klmno")  # over → evict first
        msgs = tk.get_all_messages()
        assert sum(len(m["content"]) for m in msgs) <= 10
        assert [m["content"] for m in msgs] == ["fghij", "klmno"]

    def test_both_caps_bind_simultaneously(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path, max_messages=2, max_chars=100)
        for i in range(5):
            tk.add_message("user", f"msg{i}")
        msgs = tk.get_all_messages()
        assert len(msgs) == 2
        assert [m["content"] for m in msgs] == ["msg3", "msg4"]


class TestRetrieval:
    """get_recent_messages, get_all_messages, search_messages, clear_messages."""

    def test_get_recent_defaults_to_window(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path, window=3)
        for i in range(5):
            tk.add_message("user", f"m{i}")
        recent = tk.get_recent_messages()
        assert [m["content"] for m in recent] == ["m2", "m3", "m4"]

    def test_get_recent_k_zero(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        tk.add_message("user", "hello")
        assert tk.get_recent_messages(0) == []

    def test_get_recent_k_larger_than_len(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        tk.add_message("user", "a")
        tk.add_message("user", "b")
        recent = tk.get_recent_messages(100)
        assert len(recent) == 2

    def test_get_recent_negative_k(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        with pytest.raises(ValueError, match="k"):
            tk.get_recent_messages(-1)

    def test_get_all_messages(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        for i in range(3):
            tk.add_message("user", f"m{i}")
        msgs = tk.get_all_messages()
        assert [m["content"] for m in msgs] == ["m0", "m1", "m2"]
        # Each message dict carries id/role/content/ts
        for m in msgs:
            assert set(m.keys()) == {"id", "role", "content", "ts"}

    def test_search_case_insensitive(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        tk.add_message("user", "Hello World")
        tk.add_message("user", "another thing")
        tk.add_message("user", "hello again")
        hits = tk.search_messages("HELLO")
        assert [m["content"] for m in hits] == ["Hello World", "hello again"]

    def test_search_limit_clamping(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        for i in range(5):
            tk.add_message("user", f"hit{i}")
        hits = tk.search_messages("hit", limit=2)
        assert len(hits) == 2
        # Most recent kept (sliced as [-limit:])
        assert [m["content"] for m in hits] == ["hit3", "hit4"]

    def test_search_limit_zero(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        tk.add_message("user", "hit")
        assert tk.search_messages("hit", limit=0) == []

    def test_search_negative_limit(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        with pytest.raises(ValueError, match="limit"):
            tk.search_messages("x", limit=-1)

    def test_clear_messages_returns_count(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        for i in range(4):
            tk.add_message("user", f"m{i}")
        assert tk.clear_messages() == 4
        assert tk.get_all_messages() == []
        assert tk.clear_messages() == 0


class TestFacts:
    """set/get/list/delete_fact behaviour."""

    def test_set_fact_key_regex(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        tk.set_fact("foo.bar_1-2", "ok")
        for bad in ("", "has space", "ключ", "x" * 129):
            with pytest.raises(ValueError, match="Invalid fact key"):
                tk.set_fact(bad, "x")

    def test_set_fact_non_serialisable_rejected(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        with pytest.raises(ValueError, match="JSON-serialisable"):
            tk.set_fact("k", {1, 2, 3})

    def test_get_fact_missing_returns_none(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        assert tk.get_fact("missing") is None

    def test_get_fact_roundtrip(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        tk.set_fact("name", "victor")
        tk.set_fact("nested", {"a": [1, 2]})
        assert tk.get_fact("name") == "victor"
        assert tk.get_fact("nested") == {"a": [1, 2]}

    def test_list_facts_returns_deep_copy(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        tk.set_fact("k", {"list": [1, 2]})
        snapshot = tk.list_facts()
        snapshot["k"]["list"].append(99)
        snapshot["new_key"] = "injected"
        # Original store untouched
        assert tk.get_fact("k") == {"list": [1, 2]}
        assert tk.list_facts() == {"k": {"list": [1, 2]}}

    def test_delete_fact_true_false(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        tk.set_fact("k", 1)
        assert tk.delete_fact("k") is True
        assert tk.delete_fact("k") is False
        # No raise on missing
        assert tk.delete_fact("never") is False


class TestSummary:
    """summary() shape."""

    def test_summary_shape(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path, namespace="ns")
        tk.add_message("user", "hello")
        tk.add_message("assistant", "world!")
        tk.set_fact("k", 1)
        s = tk.summary()
        assert s["namespace"] == "ns"
        assert s["messages"] == 2
        assert s["facts"] == 1
        assert s["chars"] == len("hello") + len("world!")
        assert s["storage_path"] == str(tk.storage_path)

    def test_summary_no_storage(self) -> None:
        tk = MemoryToolkit()
        assert tk.summary()["storage_path"] is None


class TestPersistence:
    """Save/load round-trips and atomic writes."""

    def test_save_then_load_via_new_instance(self, tmp_path: Path) -> None:
        path = tmp_path / "mem.json"
        tk1 = MemoryToolkit(storage_path=path, namespace="ns", autosave=False)
        tk1.add_message("user", "first")
        tk1.set_fact("k", 42)
        tk1.store.save()  # explicit (autosave off)
        assert path.exists()
        tk2 = MemoryToolkit(storage_path=path, namespace="ns")
        assert [m["content"] for m in tk2.get_all_messages()] == ["first"]
        assert tk2.get_fact("k") == 42

    def test_autosave_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "mem.json"
        tk1 = MemoryToolkit(storage_path=path, namespace="ns", autosave=True)
        tk1.add_message("user", "auto")
        tk1.set_fact("a", "b")
        # New instance reads the file fresh
        tk2 = MemoryToolkit(storage_path=path, namespace="ns")
        assert [m["content"] for m in tk2.get_all_messages()] == ["auto"]
        assert tk2.get_fact("a") == "b"

    def test_atomic_write_tmp_gone(self, tmp_path: Path) -> None:
        path = tmp_path / "mem.json"
        tk = MemoryToolkit(storage_path=path, autosave=True)
        tk.add_message("user", "hi")
        assert path.exists()
        assert not path.with_suffix(path.suffix + ".tmp").exists()


class TestNowSeam:
    """`now_fn` injection for deterministic timestamps."""

    def test_now_callable_used(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path, now_fn=lambda: 1700000000.0)
        tk.add_message("user", "t")
        tk.set_fact("k", 1)
        msg = tk.get_all_messages()[0]
        assert msg["ts"] == 1700000000.0
        # Facts use now_fn too
        snap = tk.store.namespace(tk.namespace).facts["k"]
        assert snap.updated_ts == 1700000000.0


class TestReadOnlyProperties:
    """messages / facts properties return deep copies."""

    def test_messages_property_is_deep_copy(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        tk.add_message("user", "hello")
        snap = tk.messages
        snap.clear()
        assert len(tk.messages) == 1
        # Mutating content field on the copied dataclass leaves store intact
        snap2 = tk.messages
        snap2[0].content = "tampered"
        assert tk.messages[0].content == "hello"

    def test_facts_property_is_deep_copy(self, tmp_path: Path) -> None:
        tk = make_toolkit(tmp_path)
        tk.set_fact("k", {"a": [1]})
        snap = tk.facts
        snap["k"].value["a"].append(99)
        snap.pop("k")
        assert tk.get_fact("k") == {"a": [1]}


def main() -> None:
    pass


if __name__ == "__main__":
    main()
