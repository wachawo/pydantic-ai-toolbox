#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conversation and scratchpad memory toolkit for pydantic-ai agents."""

from __future__ import annotations

import contextlib
import copy
import json
import logging
import os
import re
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..base import BaseToolkit, tool

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
DEFAULT_MAX_MESSAGES = 200
DEFAULT_WINDOW = 20

ALLOWED_ROLES = frozenset({"user", "assistant", "system", "tool"})
NAMESPACE_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")
FACT_KEY_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,128}$")


@dataclass(slots=True)
class ChatMessage:
    """A single chat message stored in memory."""

    id: str
    role: str
    content: str
    ts: float


@dataclass(slots=True)
class Fact:
    """A single fact (key/value pair) stored in memory."""

    key: str
    value: Any
    updated_ts: float


@dataclass(slots=True)
class Namespace:
    """Per-namespace state held by the in-memory store."""

    messages: list[ChatMessage] = field(default_factory=list)
    facts: dict[str, Fact] = field(default_factory=dict)
    counter: int = 0


class MemoryStore:
    """Thread-safe in-memory store, optionally persisted as a single JSON file."""

    def __init__(self, storage_path: Path | None) -> None:
        self.lock = threading.RLock()
        self.namespaces: dict[str, Namespace] = {}
        self.storage_path = storage_path
        if storage_path is not None and storage_path.exists():
            self.load_from_file(storage_path)

    def namespace(self, name: str) -> Namespace:
        with self.lock:
            ns = self.namespaces.get(name)
            if ns is None:
                ns = Namespace()
                self.namespaces[name] = ns
            return ns

    def next_id(self, namespace: str) -> str:
        with self.lock:
            ns = self.namespace(namespace)
            ns.counter += 1
            return f"{namespace}-{ns.counter:08d}"

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            namespaces: dict[str, Any] = {}
            for name, ns in self.namespaces.items():
                namespaces[name] = {
                    "messages": [asdict(m) for m in ns.messages],
                    "facts": {k: asdict(f) for k, f in ns.facts.items()},
                    "counter": ns.counter,
                }
            return {"version": SCHEMA_VERSION, "namespaces": namespaces}

    def save(self) -> None:
        if self.storage_path is None:
            return
        with self.lock:
            payload = self.snapshot()
        atomic_write_json(self.storage_path, payload)
        logger.debug(f"MemoryToolkit snapshot persisted to {self.storage_path}")

    def load_from_file(self, path: Path) -> None:
        try:
            with path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Corrupted memory snapshot at {path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid memory snapshot at {path}: not a JSON object")
        version = payload.get("version")
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported memory snapshot version {version!r} at {path} " f"(expected {SCHEMA_VERSION})"
            )
        raw_namespaces = payload.get("namespaces") or {}
        if not isinstance(raw_namespaces, dict):
            raise ValueError(f"Invalid memory snapshot at {path}: namespaces must be an object")
        for name, raw in raw_namespaces.items():
            ns = Namespace()
            messages = raw.get("messages") or []
            facts = raw.get("facts") or {}
            counter = raw.get("counter")
            if not isinstance(messages, list) or not isinstance(facts, dict):
                raise ValueError(f"Invalid memory snapshot at {path}: namespace {name!r}")
            if not isinstance(counter, int):
                raise ValueError(f"Invalid memory snapshot at {path}: counter for {name!r}")
            for m in messages:
                ns.messages.append(ChatMessage(id=m["id"], role=m["role"], content=m["content"], ts=float(m["ts"])))
            for k, v in facts.items():
                ns.facts[k] = Fact(key=v["key"], value=v["value"], updated_ts=float(v["updated_ts"]))
            ns.counter = counter
            self.namespaces[name] = ns


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON to `path` atomically via a sibling `.tmp` file + os.replace."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            with contextlib.suppress(OSError):
                tmp.unlink()


def message_to_dict(m: ChatMessage) -> dict[str, Any]:
    return {"id": m.id, "role": m.role, "content": m.content, "ts": float(m.ts)}


class MemoryToolkit(BaseToolkit):
    """Conversation buffer + key/value scratchpad memory.

    Messages are appended in order and evicted oldest-first when either the
    `max_messages` count or the optional `max_chars` total are exceeded.
    Facts are a simple JSON-serialisable key/value map. State is held in
    memory and optionally persisted to a single JSON file via atomic writes.
    """

    def __init__(
        self,
        storage_path: str | os.PathLike[str] | None = None,
        max_messages: int = DEFAULT_MAX_MESSAGES,
        max_chars: int | None = None,
        window: int = DEFAULT_WINDOW,
        namespace: str = "default",
        autosave: bool = True,
        *,
        now_fn: Callable[[], float] | None = None,
    ) -> None:
        if max_messages <= 0:
            raise ValueError(f"max_messages must be > 0, got {max_messages}")
        if max_chars is not None and max_chars <= 0:
            raise ValueError(f"max_chars must be > 0 when set, got {max_chars}")
        if window < 0:
            raise ValueError(f"window must be >= 0, got {window}")
        if not NAMESPACE_RE.match(namespace):
            raise ValueError(f"Invalid namespace: {namespace!r}")

        path: Path | None = None
        if storage_path is not None:
            path = Path(storage_path).expanduser().resolve()
            if not path.parent.exists():
                raise FileNotFoundError(f"Parent directory does not exist: {path.parent}")

        self.storage_path = path
        self.max_messages = max_messages
        self.max_chars = max_chars
        self.window = window
        self.namespace = namespace
        self.autosave = autosave
        self.now_fn = now_fn or time.time
        self.store = MemoryStore(path)
        super().__init__()
        logger.info(
            f"MemoryToolkit ready: namespace={namespace} "
            f"max_messages={max_messages} max_chars={max_chars} "
            f"storage_path={path}"
        )

    @property
    def messages(self) -> list[ChatMessage]:
        """Deep copy of the current namespace's message list."""
        ns = self.store.namespace(self.namespace)
        return copy.deepcopy(ns.messages)

    @property
    def facts(self) -> dict[str, Fact]:
        """Deep copy of the current namespace's fact map."""
        ns = self.store.namespace(self.namespace)
        return copy.deepcopy(ns.facts)

    def enforce_caps(self, ns: Namespace) -> None:
        while len(ns.messages) > self.max_messages:
            ns.messages.pop(0)
        if self.max_chars is not None:
            total = sum(len(m.content) for m in ns.messages)
            while total > self.max_chars and ns.messages:
                removed = ns.messages.pop(0)
                total -= len(removed.content)

    def maybe_save(self) -> None:
        if self.autosave and self.storage_path is not None:
            self.store.save()

    @tool
    def add_message(self, role: str, content: str) -> str:
        """Append a message to the conversation buffer and return its assigned id.

        `role` must be one of "user", "assistant", "system", "tool". `content`
        must be non-empty after stripping. Eviction enforces both the message
        count and (if configured) the total character cap.
        """
        if role not in ALLOWED_ROLES:
            raise ValueError(f"Invalid role {role!r}. Allowed: {sorted(ALLOWED_ROLES)}")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content must be a non-empty string")
        msg_id = self.store.next_id(self.namespace)
        msg = ChatMessage(id=msg_id, role=role, content=content, ts=float(self.now_fn()))
        ns = self.store.namespace(self.namespace)
        ns.messages.append(msg)
        self.enforce_caps(ns)
        self.maybe_save()
        logger.debug(f"add_message {msg_id} role={role} len={len(content)}")
        return msg_id

    @tool
    def get_recent_messages(self, k: int | None = None) -> list[dict]:
        """Return the most recent `k` messages (defaults to `window`)."""
        if k is None:
            k = self.window
        if k < 0:
            raise ValueError(f"k must be >= 0, got {k}")
        ns = self.store.namespace(self.namespace)
        if k == 0:
            return []
        return [message_to_dict(m) for m in ns.messages[-k:]]

    @tool
    def get_all_messages(self) -> list[dict]:
        """Return every message in the current namespace, oldest first."""
        ns = self.store.namespace(self.namespace)
        return [message_to_dict(m) for m in ns.messages]

    @tool
    def search_messages(self, query: str, limit: int = 10) -> list[dict]:
        """Case-insensitive substring search across message contents (most-recent last)."""
        if not isinstance(query, str):
            raise ValueError("query must be a string")
        if limit < 0:
            raise ValueError(f"limit must be >= 0, got {limit}")
        if limit == 0:
            return []
        needle = query.lower()
        ns = self.store.namespace(self.namespace)
        hits: list[ChatMessage] = [m for m in ns.messages if needle in m.content.lower()]
        return [message_to_dict(m) for m in hits[-limit:]]

    @tool
    def clear_messages(self) -> int:
        """Drop every message in the current namespace; returns the count cleared."""
        ns = self.store.namespace(self.namespace)
        n = len(ns.messages)
        ns.messages.clear()
        self.maybe_save()
        logger.info(f"clear_messages namespace={self.namespace} cleared={n}")
        return n

    @tool
    def set_fact(self, key: str, value: Any) -> bool:
        """Store a JSON-serialisable value under `key` (overwrites). Returns True."""
        if not isinstance(key, str) or not FACT_KEY_RE.match(key):
            raise ValueError(f"Invalid fact key: {key!r}")
        try:
            json.dumps(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Fact value must be JSON-serialisable: {exc}") from exc
        ns = self.store.namespace(self.namespace)
        ns.facts[key] = Fact(key=key, value=value, updated_ts=float(self.now_fn()))
        self.maybe_save()
        logger.debug(f"set_fact {key!r} (namespace={self.namespace})")
        return True

    @tool
    def get_fact(self, key: str) -> Any | None:
        """Return the value of a fact, or None if the key is unknown."""
        if not isinstance(key, str) or not FACT_KEY_RE.match(key):
            raise ValueError(f"Invalid fact key: {key!r}")
        ns = self.store.namespace(self.namespace)
        fact = ns.facts.get(key)
        if fact is None:
            return None
        return copy.deepcopy(fact.value)

    @tool
    def list_facts(self) -> dict[str, Any]:
        """Return a deep-copied snapshot of every fact's value in this namespace."""
        ns = self.store.namespace(self.namespace)
        return {k: copy.deepcopy(f.value) for k, f in ns.facts.items()}

    @tool
    def delete_fact(self, key: str) -> bool:
        """Delete a fact. Returns True if the key existed, False otherwise."""
        if not isinstance(key, str) or not FACT_KEY_RE.match(key):
            raise ValueError(f"Invalid fact key: {key!r}")
        ns = self.store.namespace(self.namespace)
        existed = key in ns.facts
        if existed:
            del ns.facts[key]
            self.maybe_save()
        return existed

    @tool
    def summary(self) -> dict:
        """Return a small summary: namespace, message count, fact count, chars, storage path."""
        ns = self.store.namespace(self.namespace)
        chars = sum(len(m.content) for m in ns.messages)
        return {
            "namespace": self.namespace,
            "messages": len(ns.messages),
            "facts": len(ns.facts),
            "chars": chars,
            "storage_path": str(self.storage_path) if self.storage_path is not None else None,
        }


def main() -> None:
    pass


if __name__ == "__main__":
    main()
