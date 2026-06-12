#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SystemToolset example: ask a local Ollama model about the host machine.

Runs against `qwen3:latest` via Ollama (OpenAI-compatible endpoint at
http://localhost:11434/v1). The agent has `SystemToolset`, so questions like
"how much free disk space do I have?" are answered from real psutil data
instead of hallucinated numbers.

Prereqs:
- ollama running locally
- `ollama pull qwen3:latest`
- `pip install "pydantic-ai-toolbox[system]"`
"""

from __future__ import annotations

import logging
import os
from typing import Any

from pydantic_ai import Agent

from pydantic_ai_toolbox import SystemToolset

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


def main() -> None:
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    logging.info(f"Building agent with Ollama model {OLLAMA_MODEL} at {OLLAMA_BASE_URL}")
    model = OpenAIChatModel(
        OLLAMA_MODEL,
        provider=OpenAIProvider(base_url=OLLAMA_BASE_URL, api_key="ollama"),
    )

    agent = Agent(
        model=model,
        toolsets=[SystemToolset()],
        system_prompt=(
            "You are a sysadmin assistant. Answer questions about this machine "
            "using the system tools — never invent numbers. Be concise."
        ),
    )

    disk = agent.run_sync("How much free disk space do I have?")
    logger.info(f"Disk:      {disk.output}")

    memory = agent.run_sync("How much RAM is in use right now?")
    logger.info(f"Memory:    {memory.output}")

    processes = agent.run_sync("What are the three heaviest processes by memory?")
    logger.info(f"Processes: {processes.output}")


if __name__ == "__main__":
    main()
