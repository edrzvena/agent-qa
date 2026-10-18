import pytest

from agent_qa.config import ConfigError, load_settings


def test_missing_key_raises():
    with pytest.raises(ConfigError):
        load_settings({})


def test_empty_key_raises():
    with pytest.raises(ConfigError):
        load_settings({"ANTHROPIC_API_KEY": ""})


def test_defaults():
    s = load_settings({"ANTHROPIC_API_KEY": "k"})
    assert s.api_key == "k"
    assert s.model == "claude-sonnet-5-5"
    assert s.max_steps == 30
    assert s.max_cost_usd == 1.0


def test_model_override():
    s = load_settings({"ANTHROPIC_API_KEY": "k", "AGENT_QA_MODEL": "x"})
    assert s.model == "x"
