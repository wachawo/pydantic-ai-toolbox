#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLToolkit example: INSERT then UPDATE then SELECT via an agent.

A fresh SQLite file is created with one `users` table. The toolkit is
configured as read-write so `execute` can run mutations. The agent is
asked, in sequence, to:

  1. Insert a row for `Alex`, age 30.
  2. Update that row to age 31.
  3. Select all rows and report what it sees.

Each turn produces a separate run; the row state evolves on disk.

Prereqs:
- ollama running locally
- `ollama pull qwen3:latest`
- `pip install "pydantic-ai-toolkits[sql]"`
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from sqlalchemy import create_engine, text

from pydantic_ai_toolkits import SQLToolkit

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


def seed_database(db_path: Path) -> None:
    """Create an empty `users` table on first run."""
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS users"))
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, age INTEGER)"))
    engine.dispose()


def build_agent(sql: SQLToolkit) -> Agent:
    logging.info(f"Building agent with Ollama model {OLLAMA_MODEL} at {OLLAMA_BASE_URL}")
    model = OpenAIChatModel(
        OLLAMA_MODEL,
        provider=OpenAIProvider(base_url=OLLAMA_BASE_URL, api_key="ollama"),
    )
    return Agent(
        model=model,
        toolsets=[sql],
        system_prompt=(
            "/no_think\n"
            "You operate on a SQLite database via two tools: `query` for "
            "read-only SELECT statements, and `execute` for writes "
            "(INSERT/UPDATE/DELETE). "
            "ALWAYS use named SQLAlchemy placeholders like `:name`, "
            "NEVER positional `?` placeholders. Pass values via the "
            "`params` argument as a dict whose keys match the placeholders. "
            "Example: execute('INSERT INTO users (name, age) VALUES (:n, :a)', "
            "params={'n': 'Alex', 'a': 30}). "
            "After a successful write, summarise what changed. After a read, "
            "summarise the rows."
        ),
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "demo.db"
        seed_database(db_path)

        sql = SQLToolkit(dsn=f"sqlite:///{db_path}", read_only=False)
        agent = build_agent(sql)

        turn1 = agent.run_sync("Insert a new user named Alex, age 30, into the users table.")
        logger.info(f"Turn 1 (INSERT): {turn1.output}")

        turn2 = agent.run_sync("Update Alex's age to 31.")
        logger.info(f"Turn 2 (UPDATE): {turn2.output}")

        turn3 = agent.run_sync("Select every row from users and tell me what's there.")
        logger.info(f"Turn 3 (SELECT): {turn3.output}")


if __name__ == "__main__":
    main()
