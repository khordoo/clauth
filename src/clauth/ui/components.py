"""Reusable Rich components for the CLAUTH CLI."""

from typing import Iterable, Optional

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.measure import Measurement
from rich.panel import Panel
from rich.text import Text

from .theme import style


console = Console()


def _compute_width(padding: int = 4) -> int:
    """Return a width that keeps layouts readable in narrow terminals."""
    try:
        width = console.size.width
    except Exception:  # pragma: no cover - defensive fallback
        width = 80
    return max(40, min(width - padding, 78))


def render_banner(
    title: str,
    subtitle: Optional[str] = None,
    bullets: Optional[Iterable[str]] = None,
) -> Panel:
    """Render a welcome banner with optional bullet highlights."""
    title_text = Text(title, style=f"bold {style('accent')}")
    pieces: list[Text] = [title_text]

    if subtitle:
        subtitle_text = Text(subtitle, style=style("text_primary"))
        pieces.append(subtitle_text)

    if bullets:
        for bullet in bullets:
            bullet_text = Text(f"• {bullet}", style=style("text_muted"))
            pieces.append(bullet_text)

    group = Group(*pieces)
    panel = Panel(
        Align.left(group),
        box=box.ROUNDED,
        border_style=style("accent"),
        padding=(1, 2),
        width=_compute_width(),
    )
    console.print(panel)
    console.print()  # trailing blank line for breathing room
    return panel


def render_card(
    title: Optional[str],
    body: str,
    footer: Optional[str] = None,
    border_style: Optional[str] = None,
) -> Panel:
    """Render a generic informational card."""
    text_parts: list[Text] = []

    if body:
        text_parts.extend(
            Text(line, style=style("text_primary")) for line in body.splitlines()
        )

    group = Group(*text_parts) if text_parts else Text("", style=style("text_primary"))

    panel = Panel(
        Align.left(group),
        title=Text(title, style=f"bold {style('accent')}") if title else None,
        title_align="left",
        border_style=border_style or style("border"),
        box=box.ROUNDED,
        padding=(1, 2),
        width=_compute_width(),
    )
    console.print(panel)

    if footer:
        footer_text = Text(footer, style=style("text_muted"))
        console.print(Align.left(footer_text, width=_compute_width()))

    console.print()
    return panel


def render_status(
    message: str,
    level: str = "info",
    footer: Optional[str] = None,
) -> Text:
    """Render a status line with semantic coloring."""
    icons = {
        "success": "✔",
        "warning": "!",
        "error": "✖",
        "info": "•",
    }
    styles = {
        "success": style("success"),
        "warning": style("warning"),
        "error": style("error"),
        "info": style("accent_alt"),
    }

    icon = icons.get(level, icons["info"])
    text_style = styles.get(level, styles["info"])
    status_text = Text(f"{icon} {message}", style=text_style)
    console.print(status_text)

    if footer:
        footer_text = Text(footer, style=style("text_muted"))
        console.print(footer_text)

    console.print()
    return status_text


def measurement() -> Measurement:
    """Expose measurement helper for layout-aware callers."""
    return Measurement.get(console, console.options, " ")
