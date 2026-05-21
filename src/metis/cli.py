"""Metis CLI - a knowledge base for commands, snippets, and queries."""

import click
from rich.console import Console
from rich.table import Table

from metis.search import VectorSearch
from metis.store import Entry, Store
from metis.ui import interactive_browse, pick_from_list, prompt_action, render_table

__version__ = "0.1.0"
console = Console()


def get_store():
    return Store()


def get_vs():
    return VectorSearch()


@click.group(invoke_without_command=True)
@click.option("-V", "--version", is_flag=True, help="Show version.")
@click.option("-l", "--list", "list_kbs", is_flag=True, help="List all knowledge bases.")
@click.option("--kb", "new_kb", type=str, default=None, help="Create a new knowledge base.")
@click.pass_context
def cli(ctx, version, list_kbs, new_kb):
    """Metis - your terminal knowledge base."""
    if version:
        console.print(f"[bold cyan]metis[/bold cyan] v{__version__}")
        return
    if list_kbs:
        store = get_store()
        kbs = store.list_kbs()
        table = Table(title="Knowledge Bases", border_style="bright_blue", title_style="bold cyan")
        table.add_column("Name", style="bold green")
        table.add_column("Entries", style="yellow", justify="right")
        for kb in kbs:
            count = len(store.get_entries(kb))
            table.add_row(kb, str(count))
        total = len(store.get_entries())
        table.add_row("[dim]all[/dim]", f"[dim]{total}[/dim]")
        console.print(table)
        return
    if new_kb:
        store = get_store()
        if store.create_kb(new_kb):
            console.print(f"[green]Created knowledge base:[/green] [bold]{new_kb}[/bold]")
        else:
            console.print(f"[yellow]Knowledge base already exists:[/yellow] [bold]{new_kb}[/bold]")
        return
    if ctx.invoked_subcommand is None:
        # markup=False so backslashes and brackets in the art are never parsed
        owl_lines = [
            "          /\\_____/\\",
            "          /  \\   /  \\",
            "         /   >   -   \\",
            "        / \\___ V ___/ \\",
            "       |   |       |   |",
            "       |   | $  {} |   |",
            "       |   | >_ SQL|   |",
            "        \\  \\_______/  /",
            "         \\____ ___ __/",
            "             |   |",
            "          ___________",
            "         [   > _     ]",
            "          -----------",
        ]
        for line in owl_lines:
            console.print(line, style="cyan", markup=False, justify="center", highlight=False)
        console.print()
        metis_lines = [
            " ███╗   ███╗███████╗████████╗██╗███████╗",
            " ████╗ ████║██╔════╝╚══██╔══╝██║██╔════╝",
            " ██╔████╔██║█████╗     ██║   ██║███████╗",
            " ██║╚██╔╝██║██╔══╝     ██║   ██║╚════██║",
            " ██║ ╚═╝ ██║███████╗   ██║   ██║███████║",
            " ╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝╚══════╝",
        ]
        for line in metis_lines:
            console.print(line, style="bold cyan", markup=False, justify="center", highlight=False)
        console.print()
        console.print(
            "T E R M I N A L   K N O W L E D G E   B A S E",
            style="dim",
            markup=False,
            justify="center",
        )
        console.print()
        console.print(
            "  [dim]metis find[/dim]       browse & search your KB\n"
            "  [dim]metis add[/dim]        add a command or snippet\n"
            "  [dim]metis --help[/dim]     all commands",
            justify="center",
        )


@cli.command()
@click.option("--kb", default="default", help="Knowledge base to add to.")
@click.option("--title", "-t", prompt="Title", help="Short title / name for the entry.")
@click.option("--command", "-c", prompt="Command / snippet", help="The command or code snippet.")
@click.option("--description", "-d", default="", help="Optional description.")
@click.option("--tags", default="", help="Comma-separated tags.")
def add(kb, title, command, description, tags):
    """Add an entry to a knowledge base."""
    store = get_store()
    vs = get_vs()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    entry = Entry(
        id="", title=title, command=command, description=description, tags=tag_list, kb=kb
    )
    store.add_entry(entry)
    vs.index_entry(entry)
    console.print(
        f"[green]Added[/green] [bold]{entry.title}[/bold] to [magenta]{entry.kb}[/magenta] (id: {entry.id})"
    )


@cli.command()
@click.argument("query", nargs=-1)
@click.option("--kb", default=None, help="Search within a specific knowledge base.")
@click.option("--semantic", "-s", is_flag=True, help="Use vector/semantic search.")
@click.option("--pick", "-p", is_flag=True, help="Pick an entry to copy or print.")
def find(query, kb, semantic, pick):
    """Search entries by keyword or semantic similarity."""
    query_str = " ".join(query)
    store = get_store()

    if not query_str:
        # interactive TUI browser
        interactive_browse(store)
        return

    if semantic:
        vs = get_vs()
        ids = vs.search(query_str, kb=kb)
        entries = store.get_entries(kb)
        entry_map = {e.id: e for e in entries}
        results = [entry_map[i] for i in ids if i in entry_map]
    else:
        results = store.keyword_search(query_str, kb=kb)

    if pick:
        chosen = pick_from_list(results)
        if chosen:
            prompt_action(chosen)
    else:
        render_table(results, title=f"Results for '{query_str}'")


@cli.command()
@click.option("--kb", default=None, help="List entries from a specific knowledge base.")
@click.option("--pick", "-p", is_flag=True, help="Pick an entry to copy or print.")
def ls(kb, pick):
    """List all entries, optionally filtered by knowledge base."""
    store = get_store()
    entries = store.get_entries(kb)
    if pick:
        chosen = pick_from_list(entries)
        if chosen:
            prompt_action(chosen)
    else:
        render_table(entries, title=f"Entries{f' [{kb}]' if kb else ''}")


@cli.command()
@click.argument("entry_id")
def rm(entry_id):
    """Remove an entry by ID."""
    store = get_store()
    vs = get_vs()
    if store.delete_entry(entry_id):
        vs.delete_entry(entry_id)
        console.print(f"[red]Deleted[/red] entry {entry_id}")
    else:
        console.print(f"[yellow]Entry not found:[/yellow] {entry_id}")


@cli.command()
def reindex():
    """Rebuild the vector search index from all entries."""
    store = get_store()
    vs = get_vs()
    vs.reindex_all(store)
    count = len(store.get_entries())
    console.print(f"[green]Reindexed[/green] {count} entries.")


if __name__ == "__main__":
    cli()
