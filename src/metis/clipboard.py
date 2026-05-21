"""Clipboard and terminal insertion utilities."""

import subprocess
import sys

from rich.console import Console

console = Console()


def copy_to_clipboard(text: str) -> bool:
    """Copy text to the system clipboard. Returns True on success."""
    try:
        if sys.platform == "darwin":
            proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            proc.communicate(text.encode("utf-8"))
        elif sys.platform.startswith("linux"):
            # try xclip, then xsel
            for cmd in (["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
                try:
                    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                    proc.communicate(text.encode("utf-8"))
                    break
                except FileNotFoundError:
                    continue
            else:
                return False
        else:
            return False
        return True
    except Exception:
        return False


def print_for_terminal(text: str):
    """Print the raw command so the user can see it (no Rich markup)."""
    console.print()
    console.print(f"[yellow]{text}[/yellow]")
    console.print()
