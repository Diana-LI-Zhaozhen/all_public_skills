"""Configuration loader for the Financial Report RAG system."""

import os
from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: str = None) -> dict[str, Any]:
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.yaml"
    else:
        config_path = Path(config_path)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Override LLM API key from environment if not set
    if not config.get("llm", {}).get("api_key"):
        provider = config.get("llm", {}).get("provider", "")
        env_map = {
            "deepseek": "DEEPSEEK_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        env_var = env_map.get(provider, "")
        if env_var:
            config["llm"]["api_key"] = os.environ.get(env_var, "")

    # Ensure index directory exists
    index_dir = Path(config.get("paths", {}).get("index_dir", "./indexes"))
    index_dir.mkdir(parents=True, exist_ok=True)

    return config
