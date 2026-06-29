"""Configuration management for ai-commit."""

import os
import json
from pathlib import Path


DEFAULT_CONFIG = {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "api_key": "",  # prefer env var AI_COMMIT_API_KEY
    "base_url": "",  # for OpenAI-compatible, default = https://api.openai.com/v1
    "style": "conventional",  # conventional | imperative | short | detailed
    "max_diff_lines": 200,
    "language": "en",
}


def config_path() -> Path:
    """Return path to config file."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "ai-commit" / "config.json"
    return Path.home() / ".config" / "ai-commit" / "config.json"


def load() -> dict:
    """Load config, merging defaults with user config."""
    config = dict(DEFAULT_CONFIG)

    # Override from file
    path = config_path()
    if path.exists():
        try:
            with open(path) as f:
                file_config = json.load(f)
                config.update(file_config)
        except (json.JSONDecodeError, OSError):
            pass

    # Override from env vars
    env_overrides = {
        "api_key": "AI_COMMIT_API_KEY",
        "model": "AI_COMMIT_MODEL",
        "base_url": "AI_COMMIT_BASE_URL",
        "provider": "AI_COMMIT_PROVIDER",
    }
    for key, env_var in env_overrides.items():
        val = os.environ.get(env_var)
        if val:
            config[key] = val

    return config


def write(config: dict) -> None:
    """Write config to file."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)


def interactive_setup() -> dict:
    """Walk user through interactive setup."""
    cfg = load()

    print("ai-commit setup")
    print("===============")
    print()

    # Provider
    print("Supported providers: openai, anthropic, ollama, google, groq, custom")
    provider = input(f"AI provider [{cfg.get('provider', 'openai')}]: ").strip()
    if provider:
        cfg["provider"] = provider

    # API key
    current_key = cfg.get("api_key", "") or os.environ.get("AI_COMMIT_API_KEY", "")
    masked = current_key[:8] + "..." if len(current_key) > 8 else "(not set)"
    key_hint = input(f"API key [{masked}]: ").strip()
    if key_hint:
        cfg["api_key"] = key_hint

    # Model
    default_model = cfg.get("model", "gpt-4o-mini")
    model = input(f"Model [{default_model}]: ").strip()
    if model:
        cfg["model"] = model

    # Style
    print("Commit style: conventional (type(scope): msg), imperative, short, detailed")
    style = input(f"Style [{cfg.get('style', 'conventional')}]: ").strip()
    if style:
        cfg["style"] = style

    write(cfg)
    print(f"\nConfig written to {config_path()}")
    return cfg
