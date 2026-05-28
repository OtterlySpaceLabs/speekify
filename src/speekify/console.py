from __future__ import annotations

from rich.console import Console

console = Console(highlight=False)
error_console = Console(stderr=True, highlight=False)

__all__ = ["console", "error_console"]