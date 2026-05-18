#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RAGToolkit example: tiny in-memory index with a deterministic stub embedder.

The stub embedder is purely local (sha256 -> floats), so the example runs
without external services. To swap in a real embedder (e.g. OpenAI
`text-embedding-3-small`), replace `stub_embedder` with any callable of
shape `(list[str]) -> list[list[float]]`; nothing else needs to change.

Real model access still requires API keys; the default model is taken
from `LLM_MODEL` and falls back to `openai:gpt-4o-mini`.
"""

from __future__ import annotations

import hashlib
import logging
import os

from pydantic_ai import Agent

from pydantic_ai_toolkits import RAGToolkit

LOGGING = {
    "format": "%(asctime)s.%(msecs)03d [%(levelname)s]: (%(name)s) %(message)s",
    "level": logging.INFO,
    "datefmt": "%Y-%m-%d %H:%M:%S",
}
logging.basicConfig(**LOGGING)
logger = logging.getLogger(__name__)


def stub_embedder(texts: list[str]) -> list[list[float]]:
    """Deterministic 32-dim embedder for examples and tests."""
    out: list[list[float]] = []
    for t in texts:
        digest = hashlib.sha256(t.encode("utf-8")).digest()[:32]
        out.append([(b - 128) / 128.0 for b in digest])
    return out


def build_agent(rag: RAGToolkit) -> Agent:
    agent = Agent(
        model=os.getenv("LLM_MODEL", "openai:gpt-4o-mini"),
        toolsets=[rag],
        system_prompt=(
            "You are a research assistant. Use the `search` tool to look up "
            "relevant passages before answering questions."
        ),
    )
    return agent


def main() -> None:
    rag = RAGToolkit(embedder=stub_embedder, chunk_size=200, chunk_overlap=20)
    rag.add_text(
        "Pydantic-AI agents use toolsets to expose callable tools to the model.",
        metadata={"topic": "pydantic-ai"},
        doc_id="d-toolsets",
    )
    rag.add_text(
        "RAGToolkit stores vectors in numpy and persists them as .npz + .json.",
        metadata={"topic": "rag"},
        doc_id="d-rag",
    )

    agent = build_agent(rag)
    reply = agent.run_sync("How does RAGToolkit persist its vectors?")
    logger.info(f"Agent reply: {reply.output}")
    logger.info(f"Index size: {rag.count()} chunks")


if __name__ == "__main__":
    main()
