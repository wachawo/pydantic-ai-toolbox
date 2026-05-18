#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MemoryToolkit example: a three-turn conversation with a local Ollama model.

Runs against `qwen3:latest` via Ollama (OpenAI-compatible endpoint at
http://localhost:11434/v1). The agent has `MemoryToolkit` so facts learnt
in turn 1 are retrievable in turn 3 even though the conversation history
between runs is not carried over by the agent itself.

Prereqs:
- ollama running locally
- `ollama pull qwen3:latest`
- `pip install "pydantic-ai-toolkits[all]"` (only stdlib is strictly required for memory)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import find_dotenv, load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from pydantic_ai_toolkits import MemoryToolkit

LOGGING: dict[str, Any] = {
    "format": "%(asctime)s.%(msecs)03d [%(levelname)s]: (%(name)s) %(message)s",
    "level": logging.INFO,
    "datefmt": "%Y-%m-%d %H:%M:%S",
}
logging.basicConfig(**LOGGING)
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:latest")


def build_agent(mem: MemoryToolkit) -> Agent:
    logging.info(f"Building agent with Ollama model {OLLAMA_MODEL} at {OLLAMA_BASE_URL}")
    model = OpenAIChatModel(
        OLLAMA_MODEL,
        provider=OpenAIProvider(base_url=OLLAMA_BASE_URL, api_key="ollama"),
    )
    return Agent(
        model=model,
        toolsets=[mem],
        system_prompt=(
            "You are a helpful assistant with a persistent memory tool. "
            "When the user shares personal details (name, preferences, facts), "
            "store them via `set_fact` using a clear key like `user_name`. "
            "When the user asks about something they told you earlier, look "
            "it up with `get_fact` or `list_facts` BEFORE answering. "
            "Do not invent facts. Keep responses concise."
        ),
    )


def main() -> None:
    mem = MemoryToolkit()
    agent = build_agent(mem)

    turn1 = agent.run_sync("Hi! My name is Alex.")
    logger.info(f"Turn 1 (introduction): {turn1.output}")

    turn2 = agent.run_sync("What is 2 + 2 * 2?")
    logger.info(f"Turn 2 (arithmetic):   {turn2.output}")

    turn3 = agent.run_sync("Can you remind me what my name is?")
    logger.info(f"Turn 3 (recall):       {turn3.output}")

    logger.info(f"Stored facts after run: {mem.list_facts()}")


if __name__ == "__main__":
    main()
