import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_MODEL = "claude-sonnet-5-5"


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str = DEFAULT_MODEL
    max_steps: int = 30
    max_cost_usd: float = 1.0


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    if env is None:
        load_dotenv()
        env = os.environ
    api_key = env.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ConfigError(
            "ANTHROPIC_API_KEY is missing. Put it in the .env file in the project root."
        )
    return Settings(api_key=api_key, model=env.get("AGENT_QA_MODEL") or DEFAULT_MODEL)
