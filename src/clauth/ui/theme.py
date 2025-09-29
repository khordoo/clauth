"""Shared color theme definitions for the CLAUTH CLI."""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ColorTheme:
    """Semantic color tokens reused across the CLI."""

    background: str = "default"
    text_primary: str = "#ffffff"
    text_muted: str = "#9ca3af"
    accent: str = "#9966FF"
    accent_alt: str = "#38bdf8"
    selection: str = "#0ea5e8"
    success: str = "#22c55e"
    warning: str = "#facc15"
    error: str = "#f87171"
    danger: str = "#dc2626"
    border: str = "#9966FF"
    dim: str = "#6b7280"


THEME = ColorTheme()


def style(token: str) -> str:
    """Return the Rich color style for the requested token."""
    try:
        return getattr(THEME, token)
    except AttributeError as exc:  # pragma: no cover - defensive guard
        raise KeyError(f"Unknown theme token: {token}") from exc


def prompt_toolkit_color(color: str, *, bold: bool = False) -> str:
    """Convert a Rich color string to prompt-toolkit format."""
    prefix = f"fg:{color}" if color.startswith("#") else color
    return f"{prefix} bold" if bold else prefix


def inquirer_style() -> Dict[str, str]:
    """Generate an InquirerPy style map aligned with the theme."""
    return {
        "questionmark": "bold",
        "instruction": prompt_toolkit_color(style("text_muted")),
        "answer": prompt_toolkit_color(style("selection"), bold=True),
        "pointer": prompt_toolkit_color(style("selection")),
        "highlighted": prompt_toolkit_color(style("selection"), bold=True),
        "selected": prompt_toolkit_color(style("selection"), bold=True),
        "separator": prompt_toolkit_color(style("dim")),
        "border": prompt_toolkit_color(style("accent")),
    }
