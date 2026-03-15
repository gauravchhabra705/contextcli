from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status

from ctxcli.extractor import ConventionExtractor
from ctxcli.generator import ClaudeMdGenerator
from ctxcli.scanner import StackScanner

app = typer.Typer(
    name="ctx",
    help="Generate CLAUDE.md context files for your projects.",
    no_args_is_help=True,
)
console = Console()

_CLAUDE_MD = "CLAUDE.md"


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _resolve_path(path: Optional[str]) -> Path:
    return Path(path).resolve() if path else Path.cwd()


def _run_pipeline(
    target: Path, merge: bool = False, verbose: bool = False
) -> tuple[str, list]:
    """Scan → extract → generate.

    Returns (claude_md_content, scanned_files_list).
    """
    with Status("[bold cyan]Scanning stack...", console=console):
        stack = StackScanner(target).scan()

    with Status("[bold cyan]Extracting conventions...", console=console):
        conventions = ConventionExtractor(target).extract()

    with Status("[bold cyan]Generating CLAUDE.md...", console=console):
        if merge:
            existing_file = target / _CLAUDE_MD
            if existing_file.exists() and not stack.existing_claude_md:
                stack.existing_claude_md = existing_file.read_text(encoding="utf-8")
        else:
            stack.existing_claude_md = None
        content = ClaudeMdGenerator(stack, conventions).generate()

    return content, conventions.scanned_files


# --------------------------------------------------------------------------- #
# Commands                                                                     #
# --------------------------------------------------------------------------- #

@app.command()
def learn(
    path: Optional[str] = typer.Argument(
        None, help="Project directory (defaults to current directory)."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print CLAUDE.md to terminal without writing it."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show which files were scanned."
    ),
) -> None:
    """Scan a project and write CLAUDE.md."""
    target = _resolve_path(path)

    if not target.is_dir():
        console.print(f"[red]Error:[/red] '{target}' is not a directory.")
        raise typer.Exit(1)

    content, scanned = _run_pipeline(target, verbose=verbose)

    if verbose and scanned:
        console.print(f"\n[dim]Scanned {len(scanned)} files:[/dim]")
        for f in scanned:
            console.print(f"  [dim]{f.relative_to(target)}[/dim]")
        console.print()

    if dry_run:
        console.print(content)
        return

    dest = target / _CLAUDE_MD
    if dest.exists():
        overwrite = typer.confirm("CLAUDE.md exists. Overwrite?", default=False)
        if not overwrite:
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

    dest.write_text(content, encoding="utf-8")
    line_count = len(content.splitlines())
    console.print(f"[green]✓ CLAUDE.md generated — {line_count} lines written[/green]")
    console.print(
        "[dim]Open Claude Code in this folder and it will read this automatically.[/dim]"
    )


@app.command()
def show(
    path: Optional[str] = typer.Argument(
        None, help="Project directory (defaults to current directory)."
    ),
) -> None:
    """Pretty-print the existing CLAUDE.md using Rich panels."""
    target = _resolve_path(path)
    dest = target / _CLAUDE_MD

    if not dest.exists():
        console.print(f"[red]No CLAUDE.md found in {target}[/red]")
        console.print("Run [bold]ctx learn[/bold] to generate one.")
        raise typer.Exit(1)

    content = dest.read_text(encoding="utf-8")

    # Split into sections and render each as its own panel
    sections = content.split("\n\n")
    current_title = "CLAUDE.md"
    buffer: list[str] = []

    def _flush(title: str, body: list[str]) -> None:
        text = "\n".join(body).strip()
        if text:
            console.print(Panel(Markdown(text), title=title, border_style="cyan"))

    for block in sections:
        if block.startswith("# "):
            _flush(current_title, buffer)
            current_title = block.lstrip("# ").strip()
            buffer = []
        else:
            buffer.append(block)

    _flush(current_title, buffer)


@app.command()
def update(
    path: Optional[str] = typer.Argument(
        None, help="Project directory (defaults to current directory)."
    ),
) -> None:
    """Re-scan and regenerate CLAUDE.md, preserving previous context in Notes."""
    target = _resolve_path(path)

    if not target.is_dir():
        console.print(f"[red]Error:[/red] '{target}' is not a directory.")
        raise typer.Exit(1)

    content, _ = _run_pipeline(target, merge=True)

    dest = target / _CLAUDE_MD
    dest.write_text(content, encoding="utf-8")
    line_count = len(content.splitlines())
    console.print(f"[green]✓ CLAUDE.md updated — {line_count} lines written[/green]")
    console.print(
        "[dim]Open Claude Code in this folder and it will read this automatically.[/dim]"
    )


@app.command()
def install_hook(
    path: Optional[str] = typer.Argument(
        None, help="Project directory (defaults to current directory)."
    ),
) -> None:
    """Install a git post-commit hook that auto-updates CLAUDE.md."""
    from ctxcli.hooks import find_ctx_binary, generate_hook_content, make_executable

    target = _resolve_path(path)
    git_dir = target / ".git"

    if not git_dir.is_dir():
        console.print("[red]No git repository found. Run git init first.[/red]")
        raise typer.Exit(1)

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_path = hooks_dir / "post-commit"

    if hook_path.exists():
        overwrite = typer.confirm(
            "post-commit hook already exists. Overwrite?", default=False
        )
        if not overwrite:
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

    ctx_bin = find_ctx_binary()
    content = generate_hook_content(ctx_bin)
    hook_path.write_text(content, encoding="utf-8")
    make_executable(hook_path)

    console.print(
        "[green]✓ Hook installed — CLAUDE.md will update automatically on commit[/green]"
    )
    console.print("[dim]To remove: delete .git/hooks/post-commit[/dim]")


@app.command()
def uninstall_hook(
    path: Optional[str] = typer.Argument(
        None, help="Project directory (defaults to current directory)."
    ),
) -> None:
    """Remove the ctxcli post-commit hook."""
    from ctxcli.hooks import is_ctxcli_hook

    target = _resolve_path(path)
    hook_path = target / ".git" / "hooks" / "post-commit"

    if not hook_path.exists():
        console.print("[yellow]No post-commit hook found.[/yellow]")
        raise typer.Exit(0)

    content = hook_path.read_text(encoding="utf-8")

    if not is_ctxcli_hook(content):
        console.print(
            "[yellow]Warning: this hook was not installed by ctxcli.[/yellow]"
        )
        remove = typer.confirm("Remove it anyway?", default=False)
        if not remove:
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

    hook_path.unlink()
    console.print("[green]✓ Hook removed.[/green]")


if __name__ == "__main__":
    app()
