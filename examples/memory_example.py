#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MemoryToolkit example: a two-turn conversation that remembers a fact.

The agent is told a fact in turn one and asked to recall it in turn two.
Real model access requires API keys (e.g. `OPENAI_API_KEY`); the default
model is taken from `LLM_MODEL` and falls back to `openai:gpt-4o-mini`.
"""

from __future__ import annotations

import logging
import os

from pydantic_ai import Agent

from pydantic_ai_toolkits import MemoryToolkit

LOGGING = {
    "format": "%(asctime)s.%(msecs)03d [%(levelname)s]: (%(name)s) %(message)s",
    "level": logging.INFO,
    "datefmt": "%Y-%m-%d %H:%M:%S",
}
logging.basicConfig(**LOGGING)
logger = logging.getLogger(__name__)


def build_agent(mem: MemoryToolkit) -> Agent:
    agent = Agent(
        model=os.getenv("LLM_MODEL", "openai:gpt-4o-mini"),
        toolsets=[mem],
        system_prompt=(
            "You are a helpful assistant with a memory tool. When the user "
            "tells you something to remember, store it with `set_fact`. When "
            "they ask about a remembered detail, retrieve it with `get_fact` "
            "or `list_facts` first."
        ),
    )
    return agent


def main() -> None:
    mem = MemoryToolkit()
    agent = build_agent(mem)

    first = agent.run_sync("Please remember that my favourite colour is teal.")
    logger.info(f"Turn 1: {first.output}")

    second = agent.run_sync("What is my favourite colour?")
    logger.info(f"Turn 2: {second.output}")

    logger.info(f"Stored facts: {mem.summary()}")


if __name__ == "__main__":
    main()
