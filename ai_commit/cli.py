"""CLI entry point for ai-commit."""

import sys
import click

from . import __version__, git, llm
from . import config as cfgmod


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="ai-commit")
@click.option("--install-hook", is_flag=True, help="Install as git prepare-commit-msg hook")
@click.option("--setup", is_flag=True, help="Run interactive setup")
@click.option("--stage/--no-stage", default=True, help="Auto-stage all changes before diffing")
@click.option("--amend", is_flag=True, help="Regenerate last commit message")
@click.option("--write", "-w", is_flag=False, flag_value="", help="Write generated message to file (for hooks)")
@click.option("--style", default=None, help="Override commit style (conventional, imperative, short, detailed)")
@click.pass_context
def main(ctx, install_hook, setup, stage, amend, write, style):
    """ai-commit: Write good git commit messages with any AI provider."""
    if ctx.invoked_subcommand is not None:
        return

    # Quick commands
    if setup:
        cfgmod.interactive_setup()
        return

    if install_hook:
        if not git.is_git_repo():
            click.echo("Not in a git repo.", err=True)
            sys.exit(1)
        hook_path = git.install_hook()
        click.echo(f"Hook installed: {hook_path}")
        return

    if amend:
        _do_amend(style)
        return

    if write is not None or write == "":
        # Called as hook: write message to COMMIT_EDITMSG file
        _do_hook(write)
        return

    _do_commit(stage, style)


def _do_commit(stage: bool, style_override: str | None):
    """Generate and create a commit."""
    if not git.is_git_repo():
        click.echo("Error: Not in a git repo.", err=True)
        sys.exit(1)

    if stage:
        git.stage_all()

    diff = git.get_staged_diff()
    if not diff.strip():
        # Try unstaged
        diff = git.get_full_diff()
        if not diff.strip():
            click.echo("No changes to commit.")
            sys.exit(1)
        click.echo("No staged changes. Committing all changes.", err=True)

    cfg = cfgmod.load()
    style = style_override or cfg.get("style", "conventional")

    click.echo("Generating commit message...", err=True)
    try:
        message = llm.generate_commit_message(diff, style=style)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"\n--- Generated message ---\n{message}\n")

    if not click.confirm("Create this commit?", default=True):
        click.echo("Aborted.")
        return

    if git.create_commit(message):
        click.echo("Commit created.")
    else:
        click.echo("Commit failed.", err=True)
        sys.exit(1)


def _do_amend(style_override: str | None):
    """Regenerate last commit message."""
    if not git.is_git_repo():
        click.echo("Error: Not in a git repo.", err=True)
        sys.exit(1)

    # Get diff since previous commit
    diff = git._git(["diff", "HEAD~1", "HEAD"])
    if not diff.strip():
        click.echo("No diff found for last commit.")
        sys.exit(1)

    cfg = cfgmod.load()
    style = style_override or cfg.get("style", "conventional")

    click.echo("Generating amended message...", err=True)
    try:
        message = llm.generate_commit_message(diff, style=style)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"\n--- Generated message ---\n{message}\n")

    if not click.confirm("Amend last commit with this message?", default=True):
        click.echo("Aborted.")
        return

    import tempfile, os, subprocess
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, prefix="ai-commit-") as f:
        f.write(message)
        f.flush()
        result = subprocess.run(["git", "commit", "--amend", "-F", f.name], capture_output=True, text=True, timeout=30)
    os.unlink(f.name)

    if result.returncode == 0:
        click.echo("Commit amended.")
    else:
        click.echo(f"Amend failed: {result.stderr.strip()}", err=True)
        sys.exit(1)


def _do_hook(commit_msg_file: str):
    """Called from prepare-commit-msg hook. Writes generated message to the file."""
    if not git.is_git_repo():
        return  # hook should not fail silently

    diff = git.get_staged_diff()
    if not diff.strip():
        return  # no diff, nothing to generate

    cfg = cfgmod.load()
    try:
        message = llm.generate_commit_message(diff, style=cfg.get("style", "conventional"))
    except Exception:
        return  # hook must not block the user

    # Only write if the file is empty (no user-written message yet)
    try:
        with open(commit_msg_file) as f:
            existing = f.read().strip()
        if existing:
            return  # user already wrote something
    except OSError:
        return

    try:
        with open(commit_msg_file, "w") as f:
            f.write(message + "\n")
    except OSError:
        pass


@main.command()
def config():
    """Show current config."""
    cfg = cfgmod.load()
    import json
    click.echo(json.dumps(cfg, indent=2))
