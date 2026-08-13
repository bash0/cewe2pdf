"""Mutable state belonging to one CEWE-to-PDF conversion.

Rendering resources and settings live in :mod:`renderContext`.  This separate
object owns information which is discovered or created while a conversion is
under way, so it cannot accidentally leak into a later conversion in the same
Python process.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversionState:
    """Mutable per-conversion caches, diagnostics, and temporary files.

    Font substitutions and message counters are deliberately here rather than
    at module scope: an album's configuration and its diagnostics must not
    affect the next album when a caller invokes :func:`convertMcf` twice.
    """

    temporary_files: list[str] = field(default_factory=list)
    background_not_found_paths: set[str] = field(default_factory=set)
    passepartout_files: dict[int, str] | None = None
    missing_font_substitutions: dict[str, str] = field(default_factory=dict)
    noted_font_substitutions: set[str] = field(default_factory=set)
    message_counters: Any | None = None
