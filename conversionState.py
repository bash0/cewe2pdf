"""Mutable state belonging to one CEWE-to-PDF conversion.

Rendering resources and settings live in :mod:`renderContext`.  This separate
object owns information which is discovered or created while a conversion is
under way, so it cannot accidentally leak into a later conversion in the same
Python process.
"""

from dataclasses import dataclass, field


@dataclass
class ConversionState:
    """Mutable per-conversion caches and temporary output files."""

    temporary_files: list[str] = field(default_factory=list)
    background_not_found_paths: set[str] = field(default_factory=set)
    passepartout_files: dict[int, str] | None = None
