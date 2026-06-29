"""Provider-agnostic LLM interface for commit message generation."""

import json
import httpx
from . import config

# ── System prompt ──────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a git commit message writer. Your job is to analyse diffs and write clear, structured commit messages.

Rules:
1. Keep the subject line under 72 characters
2. Use the imperative mood ("Add feature" not "Added feature")
3. Explain what changed and why, not how
4. For conventional commits: type(scope): description
   Types: feat, fix, docs, style, refactor, perf, test, ci, chore, revert
5. If the diff is empty, say "No changes detected"
6. Output ONLY the commit message, nothing else
7. If the diff has multiple logical changes, use a subject line + bullet points"""


def build_prompt(diff: str, style: str, branch: str = "", recent_commits: list[str] = None) -> str:
    """Build the user prompt from the diff + context."""
    lines = []

    if branch:
        lines.append(f"Branch: {branch}")

    if recent_commits:
        lines.append("Recent commit style (match this tone):")
        for c in recent_commits[-3:]:
            lines.append(f"  - {c}")

    lines.append(f"\nStyle: {style}")
    lines.append("\nDiff:")
    lines.append(diff)

    return "\n".join(lines)


# ── Provider implementations ──────────────────────────────────────


def _call_openai(cfg: dict, prompt: str) -> str:
    """Call an OpenAI-compatible API."""
    base_url = cfg.get("base_url") or "https://api.openai.com/v1"
    api_key = cfg.get("api_key") or ""
    model = cfg.get("model", "gpt-4o-mini")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 300,
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


def _call_anthropic(cfg: dict, prompt: str) -> str:
    """Call Anthropic API."""
    api_key = cfg.get("api_key") or ""
    model = cfg.get("model", "claude-sonnet-4-20250514")

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 300,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": prompt},
        ],
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()


def _call_ollama(cfg: dict, prompt: str) -> str:
    """Call a local Ollama instance."""
    base_url = cfg.get("base_url") or "http://localhost:11434"
    model = cfg.get("model", "llama3.2")

    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3},
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(f"{base_url}/api/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["response"].strip()


# ── Main dispatch ─────────────────────────────────────────────────


def generate_commit_message(diff: str, style: str = "conventional") -> str:
    """Generate a commit message from a diff using configured provider."""
    if not diff.strip():
        return "No changes detected"

    cfg = config.load()
    branch = ""
    try:
        from .git import get_branch_name, get_recent_commits
        branch = get_branch_name()
        recent = get_recent_commits()
    except Exception:
        recent = []

    prompt = build_prompt(diff, style, branch=branch, recent_commits=recent)
    provider = cfg.get("provider", "openai")

    try:
        if provider == "anthropic":
            return _call_anthropic(cfg, prompt)
        elif provider == "ollama":
            return _call_ollama(cfg, prompt)
        else:
            # Default: treat as OpenAI-compatible
            return _call_openai(cfg, prompt)
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"API error ({provider}): {e.response.status_code} {e.response.text[:200]}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Connection error ({provider}): {e}")
