#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quickstart: combine multiple toolkits inside a single pydantic-ai agent."""

from __future__ import annotations

import logging
import os

from pydantic_ai import Agent

from pydantic_ai_toolkits import (
    FilesystemToolkit,
    MemoryToolkit,
    PandasToolkit,
    SQLToolkit,
)

LOGGING = {
    "format": "%(asctime)s.%(msecs)03d [%(levelname)s]: (%(name)s) %(message)s",
    "level": logging.INFO,
    "datefmt": "%Y-%m-%d %H:%M:%S",
}
logging.basicConfig(**LOGGING)
logger = logging.getLogger(__name__)


def build_agent() -> Agent:
    fs = FilesystemToolkit(root="./workspace", read_only=False)
    db = SQLToolkit(dsn=os.getenv("DATABASE_URL", "sqlite:///demo.db"), read_only=True)
    pd_kit = PandasToolkit()
    mem = MemoryToolkit()

    agent = Agent(
        model=os.getenv("LLM_MODEL", "openai:gpt-4o-mini"),
        toolsets=[fs, db, pd_kit, mem],
        system_prompt=(
            "You are a data assistant. Use the filesystem tools to read and write "
            "local files, the SQL tools for read-only database queries, the pandas "
            "tools for in-memory analysis, and the memory tools to persist notes "
            "across messages."
        ),
    )
    return agent


def main() -> None:
    agent = build_agent()
    result = agent.run_sync("List the files in the workspace and summarise what you see.")
    logger.info(f"Agent reply: {result.output}")


if __name__ == "__main__":
    main()
