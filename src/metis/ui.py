"""Interactive TUI browser with KB navigation, search, and clipboard support."""

import os
import sys
import termios
import tty

from rich.console import Console
from rich.table import Table

from metis.clipboard import copy_to_clipboard

console = Console()

# ── terminal helpers ──────────────────────────────────────────────────────

# Alternate screen sequences — isolate the TUI from the normal scrollback
# buffer so cursor-home always means (1,1) of our private screen.
_ALT_ENTER = "\033[?1049h"
_ALT_EXIT = "\033[?1049l"
_HIDE_CURSOR = "\033[?25l"
_SHOW_CURSOR = "\033[?25h"
_CURSOR_HOME = "\033[H"
_ERASE_TAIL = "\033[J"


def _term_size():
    try:
        sz = os.get_terminal_size()
        return sz.lines, sz.columns
    except OSError:
        return 24, 80


def _begin_frame():
    """Clear the alternate screen and reset cursor to (1,1).

    On the private alternate screen buffer there is no scrollback to disturb,
    so a full clear (\033[2J) is safe and guarantees no stale characters remain
    to the right of shorter lines from a previous render.
    """
    sys.stdout.write("\033[2J" + _CURSOR_HOME)
    sys.stdout.flush()


def _end_frame():
    """Erase any content that may have slipped past the last print."""
    sys.stdout.write(_ERASE_TAIL)
    sys.stdout.flush()


# ── key reading ───────────────────────────────────────────────────────────


def _read_key():
    """Read a single keypress, handling escape sequences."""
    ch = sys.stdin.read(1)
    if ch == "\x1b":
        seq = sys.stdin.read(2)
        if seq == "[A":
            return "up"
        if seq == "[B":
            return "down"
        if seq == "[C":
            return "right"
        if seq == "[D":
            return "left"
        if seq == "" or seq[0] != "[":
            return "esc"
        return "unknown"
    if ch in ("\r", "\n"):
        return "enter"
    if ch in ("\x7f", "\x08"):
        return "backspace"
    if ch == "\x03":
        return "ctrl-c"
    if ch == "\x0b":  # Ctrl+K
        return "ctrl-k"
    if ch == "\x15":  # Ctrl+U
        return "ctrl-u"
    if ch == "\t":
        return "tab"
    return ch


# ── entry filtering / viewport ────────────────────────────────────────────


def _filter_entries(entries, query):
    if not query.strip():
        return list(entries)
    terms = query.lower().split()
    return [
        e
        for e in entries
        if all(
            t in f"{e.title} {e.command} {e.description} {' '.join(e.tags)}".lower() for t in terms
        )
    ]


def _clamp(idx, length):
    if length == 0:
        return 0
    return max(0, min(idx, length - 1))


def _view_window(sel, total, visible):
    """Sliding window: keep selected row roughly centred."""
    if total <= visible:
        return 0, total
    half = visible // 2
    start = max(0, min(sel - half, total - visible))
    return start, start + visible


# ── render functions ──────────────────────────────────────────────────────

# Fixed lines consumed outside the scrollable entry list:
#   KB screen:    header(1) + blank(1) + footer(1)  = 3
#   Entry screen: header(1) + mode(1) + blank(1) + footer(1) + footer_hint(1) = 5
# We add 1 extra spare to each so there is always a buffer row.
_KB_FIXED_LINES = 4
_ENTRY_FIXED_LINES = 6


def _render_kb_list(kbs, counts, sel):
    rows, _ = _term_size()
    visible = max(1, rows - _KB_FIXED_LINES)
    start, end = _view_window(sel, len(kbs), visible)

    _begin_frame()
    console.print("[bold cyan]Metis[/bold cyan] — Knowledge Bases", highlight=False, no_wrap=True)
    console.print()
    for i in range(start, end):
        kb = kbs[i]
        prefix = "▸ " if i == sel else "  "
        style = "bold reverse" if i == sel else ""
        count = counts.get(kb, 0)
        console.print(
            f"{prefix}[magenta]{kb:20s}[/magenta] [dim]{count} entries[/dim]",
            style=style,
            highlight=False,
            no_wrap=True,
        )
    scroll_hint = (
        f"  [dim]↑/↓ to scroll ({end}/{len(kbs)} shown)[/dim]" if len(kbs) > visible else ""
    )
    console.print(
        f"[dim]↑/↓ navigate  ·  →/Enter open  ·  q quit[/dim]{scroll_hint}",
        no_wrap=True,
    )
    _end_frame()


def _render_entry_list(kb_name, query, items, total, sel, search_mode):
    rows, _ = _term_size()
    visible = max(1, rows - _ENTRY_FIXED_LINES)
    start, end = _view_window(sel, len(items), visible)

    _begin_frame()

    # header — always 1 line
    count_str = f"[dim]({len(items)}/{total})[/dim]"
    console.print(
        f"[bold cyan]Metis[/bold cyan] > [magenta]{kb_name}[/magenta]  {count_str}",
        highlight=False,
        no_wrap=True,
    )

    # mode line — always 1 line
    if search_mode:
        console.print(
            f"[bold cyan]/ [/bold cyan]{query}[bold cyan]_[/bold cyan]",
            highlight=False,
            no_wrap=True,
        )
    else:
        filter_hint = f"  [dim italic]filter: {query}[/dim italic]" if query else ""
        console.print(
            f"[dim]Ctrl+K to search{filter_hint}[/dim]",
            highlight=False,
            no_wrap=True,
        )

    # blank separator — always 1 line
    console.print()

    # entry rows — exactly `visible` lines, each no_wrap so they never spill
    if not items:
        console.print("[dim]  No matching entries.[/dim]", no_wrap=True)
    else:
        for i in range(start, end):
            e = items[i]
            is_sel = i == sel
            prefix = "▸ " if is_sel else "  "
            style = "bold reverse" if is_sel else ""
            # Collapse embedded newlines so every entry occupies exactly 1 row
            cmd_oneline = e.command.replace("\n", " ").replace("\t", " ")
            tags = ", ".join(e.tags)
            tag_str = f" [cyan]({tags})[/cyan]" if tags else ""
            console.print(
                f"{prefix}[green]{e.title:28s}[/green] [yellow]{cmd_oneline[:50]}[/yellow]{tag_str}",
                style=style,
                highlight=False,
                no_wrap=True,
            )

    # footer — always 1 line (no \n prefix to keep line count exact)
    scroll_info = (
        f"  [dim]↑/↓ to scroll ({end}/{len(items)} shown)[/dim]" if len(items) > visible else ""
    )
    if search_mode:
        console.print(
            f"[dim]↑/↓ navigate  ·  Esc/Enter done  ·  Backspace delete  ·  q quit[/dim]{scroll_info}",
            no_wrap=True,
        )
    else:
        clear_hint = "  ·  Ctrl+U clear" if query else ""
        console.print(
            f"[dim]↑/↓ navigate  ·  c copy  ·  p print  ·  Ctrl+K search{clear_hint}  ·  ← back  ·  q quit[/dim]{scroll_info}",
            no_wrap=True,
        )
    _end_frame()


# ── public API ────────────────────────────────────────────────────────────


def render_table(entries, title="Results"):
    if not entries:
        console.print("[dim]No entries found.[/dim]")
        return
    table = Table(
        title=title, show_lines=False, border_style="bright_blue", title_style="bold cyan"
    )
    table.add_column("ID", style="dim", width=8)
    table.add_column("KB", style="magenta", width=14)
    table.add_column("Title", style="bold green")
    table.add_column("Command / Snippet", style="yellow", max_width=60)
    table.add_column("Tags", style="cyan")
    for e in entries:
        table.add_row(e.id, e.kb, e.title, e.command, ", ".join(e.tags))
    console.print(table)


def prompt_action(entry):
    """Non-interactive fallback for piped/non-TTY contexts."""
    console.print()
    console.print(f"[bold green]{entry.title}[/bold green]")
    console.print(f"[yellow]{entry.command}[/yellow]")
    console.print()
    console.print("[dim][c] Copy to clipboard  [p] Print to terminal  [q] Cancel[/dim]")
    if not sys.stdin.isatty():
        return
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            key = _read_key()
            if key in ("c", "C"):
                if copy_to_clipboard(entry.command):
                    console.print("[green]Copied to clipboard.[/green]")
                else:
                    console.print("[red]Clipboard not available.[/red]")
                    console.print(f"\n{entry.command}\n")
                return
            elif key in ("p", "P"):
                console.print(f"\n{entry.command}\n")
                return
            elif key in ("q", "Q", "esc", "ctrl-c"):
                return
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def pick_from_list(entries):
    """Numbered list picker for non-interactive use (--pick flag)."""
    if not entries:
        console.print("[dim]No entries found.[/dim]")
        return None
    table = Table(
        title="Pick an entry", show_lines=False, border_style="bright_blue", title_style="bold cyan"
    )
    table.add_column("#", style="bold", width=4, justify="right")
    table.add_column("KB", style="magenta", width=14)
    table.add_column("Title", style="bold green")
    table.add_column("Command / Snippet", style="yellow", max_width=60)
    for i, e in enumerate(entries, 1):
        table.add_row(str(i), e.kb, e.title, e.command)
    console.print(table)
    console.print()
    try:
        choice = input("Enter number (or q to cancel): ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if choice.lower() == "q" or not choice:
        return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(entries):
            return entries[idx]
    except ValueError:
        pass
    console.print("[yellow]Invalid selection.[/yellow]")
    return None


def interactive_browse(store):
    """Full interactive TUI: KB list → entry browser → copy/print action."""
    if not sys.stdin.isatty():
        console.print("[red]Interactive mode requires a TTY.[/red]")
        return

    kbs = ["all", *store.list_kbs()]
    counts = {kb: len(store.get_entries(kb if kb != "all" else None)) for kb in kbs}
    kb_sel = 0

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        # Enter alternate screen: isolated from scrollback, cursor-home is always (1,1)
        sys.stdout.write(_ALT_ENTER + _HIDE_CURSOR)
        sys.stdout.flush()

        # ── KB selector loop ─────────────────────────────────────────────
        while True:
            _render_kb_list(kbs, counts, kb_sel)
            key = _read_key()

            if key == "up":
                kb_sel = _clamp(kb_sel - 1, len(kbs))
            elif key == "down":
                kb_sel = _clamp(kb_sel + 1, len(kbs))
            elif key in ("enter", "right"):
                chosen_kb = kbs[kb_sel]
                kb_filter = None if chosen_kb == "all" else chosen_kb
                all_entries = store.get_entries(kb_filter)
                query = ""
                filtered = list(all_entries)
                entry_sel = 0
                search_mode = False

                # ── Entry browser loop ────────────────────────────────────
                back_to_kbs = False
                while True:
                    _render_entry_list(
                        chosen_kb, query, filtered, len(all_entries), entry_sel, search_mode
                    )
                    key = _read_key()

                    if search_mode:
                        if key in ("enter", "esc", "ctrl-k"):
                            search_mode = False
                        elif key == "backspace":
                            if query:
                                query = query[:-1]
                                filtered = _filter_entries(all_entries, query)
                                entry_sel = 0
                            else:
                                search_mode = False
                        elif key == "up":
                            entry_sel = _clamp(entry_sel - 1, len(filtered))
                        elif key == "down":
                            entry_sel = _clamp(entry_sel + 1, len(filtered))
                        elif key == "ctrl-c":
                            return
                        elif isinstance(key, str) and len(key) == 1 and key.isprintable():
                            query += key
                            filtered = _filter_entries(all_entries, query)
                            entry_sel = 0
                    else:
                        if key == "up":
                            entry_sel = _clamp(entry_sel - 1, len(filtered))
                        elif key == "down":
                            entry_sel = _clamp(entry_sel + 1, len(filtered))
                        elif key == "ctrl-k":
                            search_mode = True
                        elif key == "ctrl-u":
                            query = ""
                            filtered = list(all_entries)
                            entry_sel = 0
                        elif key in ("c", "C"):
                            if filtered:
                                entry = filtered[entry_sel]
                                sys.stdout.write(_ALT_EXIT + _SHOW_CURSOR)
                                sys.stdout.flush()
                                if copy_to_clipboard(entry.command):
                                    console.print("[green]Copied to clipboard.[/green]")
                                else:
                                    console.print("[red]Clipboard not available.[/red]")
                                    console.print(f"\n{entry.command}\n")
                                return
                        elif key in ("p", "P"):
                            if filtered:
                                entry = filtered[entry_sel]
                                sys.stdout.write(_ALT_EXIT + _SHOW_CURSOR)
                                sys.stdout.flush()
                                console.print(f"\n{entry.command}\n")
                                return
                        elif key in ("left", "tab", "esc", "backspace"):
                            back_to_kbs = True
                            break
                        elif key in ("q", "Q", "ctrl-c"):
                            return

                if back_to_kbs:
                    continue

            elif key in ("q", "Q", "ctrl-c"):
                return

    finally:
        sys.stdout.write(_ALT_EXIT + _SHOW_CURSOR)
        sys.stdout.flush()
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
