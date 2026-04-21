"""Command-line interface for the agent handoff protocol."""

from typing import Optional

try:
    import click
except ImportError:  # pragma: no cover
    click = None  # type: ignore

try:
    from rich.console import Console
    from rich.table import Table
    _HAS_RICH = True
except ImportError:  # pragma: no cover
    _HAS_RICH = False

from .broker import HandoffBroker


def _render_audit_plain(events):
    lines = [
        "ID\tTIME\tEVENT\tPACKET_ID\tAGENT\tDETAILS",
    ]
    for e in events:
        lines.append(
            f"{e['id']}\t{e['timestamp']}\t{e['event_type']}\t"
            f"{e['packet_id']}\t{e['agent_name']}\t{e['details']}"
        )
    return "\n".join(lines)


def _render_audit_rich(events) -> None:
    console = Console()
    table = Table(title="Handoff Audit Log")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Timestamp", style="magenta")
    table.add_column("Event", style="green")
    table.add_column("Packet ID", justify="right")
    table.add_column("Agent")
    table.add_column("Details", overflow="fold")
    for e in events:
        table.add_row(
            str(e["id"]),
            str(e["timestamp"]),
            str(e["event_type"]),
            str(e["packet_id"]) if e["packet_id"] is not None else "-",
            str(e["agent_name"]) if e["agent_name"] else "-",
            str(e["details"]) if e["details"] else "-",
        )
    console.print(table)


def render_audit(events, use_rich: Optional[bool] = None) -> str:
    """Render audit events. Returns plain text; prints Rich table when available."""
    if use_rich is None:
        use_rich = _HAS_RICH
    if use_rich and _HAS_RICH:
        _render_audit_rich(events)
        return ""
    return _render_audit_plain(events)


if click is not None:

    @click.group()
    def cli() -> None:
        """handoff-cli - utilities for the agent handoff protocol."""

    @cli.command("audit")
    @click.option("--db", "db_path", default=None, help="Path to SQLite database.")
    @click.option("--packet-id", type=int, default=None)
    @click.option("--agent", "agent_name", default=None)
    @click.option("--event", "event_type", default=None,
                  type=click.Choice(["sent", "received", "expired", "purged"]))
    @click.option("--limit", default=100, type=int)
    @click.option("--plain", is_flag=True, default=False, help="Force plain-text output.")
    def audit_cmd(
        db_path: Optional[str],
        packet_id: Optional[int],
        agent_name: Optional[str],
        event_type: Optional[str],
        limit: int,
        plain: bool,
    ) -> None:
        """Pretty-print recent audit events."""
        broker = HandoffBroker(db_path=db_path)
        try:
            events = broker.get_audit_log(
                packet_id=packet_id,
                agent_name=agent_name,
                event_type=event_type,
                limit=limit,
            )
        finally:
            broker.close()
        if plain or not _HAS_RICH:
            click.echo(_render_audit_plain(events))
        else:
            _render_audit_rich(events)

else:  # pragma: no cover
    cli = None  # type: ignore


if __name__ == "__main__":  # pragma: no cover
    if cli is not None:
        cli()
