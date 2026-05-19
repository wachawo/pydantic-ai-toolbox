#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PandasToolset example: load a CSV, count rows by condition.

Creates a small `sales.csv` on disk, points the toolset at it, then asks
the agent: how many rows have price > 20? The agent should call
`load_csv`, then `query` (or `value_counts`/`aggregate`), and report
the count.

Prereqs:
- ollama running locally
- `ollama pull qwen3:latest`
- `pip install "pydantic-ai-toolbox[pandas]"`
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from pydantic_ai import Agent

from pydantic_ai_toolbox import PandasToolset

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

SAMPLE_CSV = """country,price,qty
US,10,1
US,25,2
DE,30,3
FR,40,4
DE,15,5
US,50,2
FR,18,1
"""


def main() -> None:
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    logging.info(f"Building agent with Ollama model {OLLAMA_MODEL} at {OLLAMA_BASE_URL}")
    model = OpenAIChatModel(
        OLLAMA_MODEL,
        provider=OpenAIProvider(base_url=OLLAMA_BASE_URL, api_key="ollama"),
    )

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "sales.csv"
        csv_path.write_text(SAMPLE_CSV, encoding="utf-8")

        pd_kit = PandasToolset()
        agent = Agent(
            model=model,
            toolsets=[pd_kit],
            system_prompt=(
                "/no_think\n"
                "You analyse pandas dataframes through your tools. "
                "Workflow: FIRST call `load_csv(name, path)` and WAIT for its "
                "result. Only AFTER load_csv returns, in a NEW assistant turn, "
                "call `query(name, expr)` with a pandas-query expression like "
                "'price > 20'. Never call load_csv and query in the same response. "
                "The number of rows returned by `query` IS the count — do not "
                "invent numbers."
            ),
        )

        prompt = (
            f"There is a CSV at {csv_path}. Load it under the name 'sales' "
            "and tell me how many rows have price greater than 20."
        )
        reply = agent.run_sync(prompt)
        logger.info(f"Agent reply: {reply.output}")
        logger.info(f"Final python-side pd_kit.list_dataframes(): {pd_kit.list_dataframes()}")


if __name__ == "__main__":
    main()
