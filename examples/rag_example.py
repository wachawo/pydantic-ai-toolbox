#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RAGToolkit example: override model priors with retrieved facts.

The agent is told (via the RAG index) that "the sky is green" and then asked
what colour the sky is. A working RAG flow forces the answer to come from
the indexed text, not the model's prior. This is the standard sanity check
for any retrieval setup.

Uses a deterministic stub embedder so the example runs without API keys;
the LLM is local Ollama qwen3:latest.

Prereqs:
- ollama running locally
- `ollama pull qwen3:latest`
- `pip install "pydantic-ai-toolkits[rag]"`
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from pydantic_ai_toolkits import RAGToolkit

LOGGING: dict[str, Any] = {
    "format": "%(asctime)s.%(msecs)03d [%(levelname)s]: (%(name)s) %(message)s",
    "level": logging.INFO,
    "datefmt": "%Y-%m-%d %H:%M:%S",
}
logging.basicConfig(**LOGGING)
logger = logging.getLogger(__name__)

try:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv())
except ImportError:
    pass  # python-dotenv is optional

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:latest")


def stub_embedder(texts: list[str]) -> list[list[float]]:
    """Deterministic 32-dim embedder. Sha256 hash bytes mapped to [-1, 1]."""
    out: list[list[float]] = []
    for t in texts:
        digest = hashlib.sha256(t.encode("utf-8")).digest()[:32]
        out.append([(b - 128) / 128.0 for b in digest])
    return out


def build_agent(rag: RAGToolkit) -> Agent:
    logging.info(f"Building agent with Ollama model {OLLAMA_MODEL} at {OLLAMA_BASE_URL}")
    model = OpenAIChatModel(
        OLLAMA_MODEL,
        provider=OpenAIProvider(base_url=OLLAMA_BASE_URL, api_key="ollama"),
    )
    return Agent(
        model=model,
        toolsets=[rag],
        system_prompt=(
            "You answer questions strictly from the knowledge base, not from "
            "your prior knowledge. ALWAYS call the `search` tool first to find "
            "relevant passages, and base your answer on those passages even if "
            "they contradict common sense. If the search returns no match, say so."
        ),
    )


def main() -> None:
    rag = RAGToolkit(embedder=stub_embedder, chunk_size=200, chunk_overlap=20)
    rag.add_text("The sky is green.", doc_id="d-sky")
    logger.info(f"Indexed: {rag.count()} chunk(s)")

    agent = build_agent(rag)
    reply = agent.run_sync("What color is the sky?")
    logger.info(f"Agent reply: {reply.output}")


if __name__ == "__main__":
    main()
