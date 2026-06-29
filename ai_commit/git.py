"""Git operations: get diffs, stage info, amend commits."""

import subprocess
import os


def _git(args: list[str], check: bool = True) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True, text=True, timeout=30,
        check=check,
    )
    return result.stdout


def is_git_repo() -> bool:
    """Check if cwd is inside a git repo."""
    try:
        _git(["rev-parse", "--git-dir"], check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_staged_diff() -> str:
    """Return the diff of staged changes (--cached)."""
    return _git(["diff", "--cached"])


def get_unstaged_diff() -> str:
    """Return the diff of unstaged tracked changes."""
    return _git(["diff"])


def get_full_diff() -> str:
    """Return diff of all changes (staged + unstaged)."""
    return _git(["diff", "HEAD"])


def get_branch_name() -> str:
    """Return current branch name."""
    try:
        return _git(["rev-parse", "--abbrev-ref", "HEAD"]).strip()
    except subprocess.CalledProcessError:
        return ""


def get_recent_commits(count: int = 5) -> list[str]:
    """Return recent commit messages for style reference."""
    try:
        output = _git(["log", f"-{count}", "--format=%s"])
        return [line.strip() for line in output.strip().split("\n") if line.strip()]
    except subprocess.CalledProcessError:
        return []


def stage_all() -> None:
    """Stage all changes (git add -A)."""
    _git(["add", "-A"])


def create_commit(message: str) -> bool:
    """Create a commit with the given message."""
    try:
        # Write message to temp file to avoid shell quoting issues
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, prefix="ai-commit-") as f:
            f.write(message)
            f.flush()
            _git(["commit", "-F", f.name])
        os.unlink(f.name)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Commit failed: {e.stderr.strip()}")
        return False


def install_hook() -> str:
    """Install as a prepare-commit-msg git hook. Returns path or error msg."""
    repo_root = _git(["rev-parse", "--show-toplevel"]).strip()
    hooks_dir = os.path.join(repo_root, ".git", "hooks")
    hook_path = os.path.join(hooks_dir, "prepare-commit-msg")

    hook_script = """#!/bin/sh
# ai-commit prepare-commit-msg hook
# Generates commit message from staged diff before editor opens.
exec ai-commit --write "$1"
"""

    os.makedirs(hooks_dir, exist_ok=True)
    with open(hook_path, "w") as f:
        f.write(hook_script)
    os.chmod(hook_path, 0o755)
    return hook_path
