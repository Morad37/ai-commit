# ai-commit

Write good git commit messages with any AI provider.

```
$ ai-commit
Generating commit message...

--- Generated message ---
feat(parser): add JSON schema validation for config files

- Validate config against JSON Schema on load
- Return clear error messages for invalid config
- Add test coverage for schema validation

Create this commit? [Y/n]: y
Commit created.
```

## Why this exists

Every other AI commit tool locks you into one provider. OpenAI only. Anthropic only. A local Ollama thing. If you switch providers, you switch tools.

`ai-commit` works with any provider. Same CLI, same workflow, swap the model in a config line.

## Install

```bash
pip install ai-commit
```

Or from source:

```bash
git clone https://github.com/Morad37/ai-commit
cd ai-commit
pip install .
```

## Setup

### Quick start (OpenAI / any OpenAI-compatible API)

```bash
export AI_COMMIT_API_KEY="sk-..."
ai-commit --setup
```

### Other providers

```bash
export AI_COMMIT_PROVIDER="anthropic"
export AI_COMMIT_API_KEY="sk-ant-..."
export AI_COMMIT_MODEL="claude-sonnet-4-20250514"

export AI_COMMIT_PROVIDER="ollama"
export AI_COMMIT_MODEL="llama3.2"
# Ollama defaults to http://localhost:11434

export AI_COMMIT_PROVIDER="groq"
export AI_COMMIT_BASE_URL="https://api.groq.com/openai/v1"
export AI_COMMIT_MODEL="llama3-70b-8192"
```

## Usage

```bash
# Stage all changes and generate commit
ai-commit

# Just generate a message for staged changes (no auto-stage)
ai-commit --no-stage

# Regenerate the last commit message
ai-commit --amend

# Auto-install as a git hook (runs before every commit)
ai-commit --install-hook

# Use a specific style
ai-commit --style conventional
ai-commit --style short
ai-commit --style detailed
```

### Git hook

```bash
ai-commit --install-hook
```

This installs a `prepare-commit-msg` hook that auto-generates the commit message before your editor opens. You can still edit it. If you already wrote a message, the hook leaves it alone.

## Configuration

Config file at `~/.config/ai-commit/config.json`:

```json
{
  "provider": "openai",
  "model": "gpt-4o-mini",
  "api_key": "",
  "base_url": "",
  "style": "conventional",
  "max_diff_lines": 200,
  "language": "en"
}
```

All fields can be overridden via environment variables:

| Variable | Overrides |
|---|---|
| `AI_COMMIT_API_KEY` | `api_key` |
| `AI_COMMIT_MODEL` | `model` |
| `AI_COMMIT_BASE_URL` | `base_url` |
| `AI_COMMIT_PROVIDER` | `provider` |

## Supported providers

- **OpenAI** (and any OpenAI-compatible API -- Groq, Together, Fireworks, OpenRouter, local vLLM, etc.)
- **Anthropic** (Claude)
- **Ollama** (local models)
- **Custom** -- set `base_url` to any OpenAI-compatible endpoint

## Commit styles

| Style | Example |
|---|---|
| `conventional` | `feat(parser): add JSON schema validation` |
| `imperative` | `Add JSON schema validation to the config parser` |
| `short` | `Add config validation` |
| `detailed` | Multi-line with bullet points explaining each change |

## How it works

1. Reads the staged diff (`git diff --cached`)
2. Sends it to your configured AI provider with a prompt tuned for commit messages
3. Returns a structured commit message
4. Either creates the commit or writes it to your editor via the hook

Only works in git repos. Only generates messages for staged changes (by default).

## License

MIT
