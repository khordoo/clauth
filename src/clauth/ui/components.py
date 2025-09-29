"""Reusable Rich components for the CLAUTH CLI."""

from contextlib import contextmanager
from typing import Callable, Iterable, Optional

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.status import Status
from rich.measure import Measurement
from rich.panel import Panel
from rich.rule import Rule
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
    title_text = Text(title, style="bold")
    try:
        title_text.apply_gradient(style("accent"), style("accent_alt"))
    except Exception:  # pragma: no cover - gradient requires rich>=13
        title_text.stylize(f"bold {style('accent')}")

    spacer = Text()
    pieces: list = [title_text, spacer]

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


class Spinner:
    """Context manager that shows a transient spinner with themed styling."""

    def __init__(self, message: str, *, spinner: str = "dots"):
        self.message = message
        self.spinner = spinner
        self._status: Status | None = None

    def __enter__(self):
        self._status = console.status(
            f"[bold {style('accent_alt')}] {self.message}",
            spinner=self.spinner,
            spinner_style=style("accent"),
        )
        return self._status.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self._status is not None
        return self._status.__exit__(exc_type, exc_val, exc_tb)


class WizardScreen:
    """Utility to manage a multi-step wizard layout with a banner and summaries."""

    def __init__(
        self,
        banner: Optional[Callable[[], None]] = None,
    ) -> None:
        self.banner = banner
        self.summaries: list[dict[str, Optional[str]]] = []

    def render(
        self,
        *,
        active_message: Optional[str] = None,
        card: Optional[dict] = None,
    ) -> None:
        console.clear()
        if self.banner:
            self.banner()

        for entry in self.summaries:
            render_status(
                entry.get("message", ""),
                level=entry.get("level", "info") or "info",
                footer=entry.get("footer"),
            )

        if active_message:
            render_status(active_message, level="info")

        if card:
            render_card(
                title=card.get("title"),
                body=card.get("body", ""),
                footer=card.get("footer"),
            )

    def add_summary(self, message: str, *, level: str = "info", footer: Optional[str] = None) -> None:
        self.summaries.append({"message": message, "level": level, "footer": footer})
        self.render()

    def add_summary_entry(self, summary: dict) -> None:
        self.add_summary(
            summary.get("message", ""),
            level=summary.get("level", "info") or "info",
            footer=summary.get("footer"),
        )

    @contextmanager
    def step(self, label: str, *, card: Optional[dict] = None):
        """Render a step header and optional card while executing the step."""
        self.render(active_message=label, card=card)
        yield
