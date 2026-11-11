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

    # Character support checks: cache each font's Unicode cmap once per conversion.
    # None means that the font could not be inspected.
    font_character_maps: dict[str, set[int] | None] = field(default_factory=dict)

    # Used when ShowAllUnsupportedCharacters is False.
    # Each entry identifies one character/font combination already reported.
    unsupported_character_warnings: set[tuple[str, str]] = field(default_factory=set)    
    
    # Character support diagnostic and override settings.
    show_all_unsupported_characters: bool = True
    
    # Character handling rules, keyed by (font family, character).
    character_font_overrides: dict[tuple[str, str], tuple[str, str]] = field(default_factory=dict)
    character_replacements: dict[tuple[str, str], str] = field(default_factory=dict)

    # Optional font suggestion implementation. None means suggestions are disabled.
    font_suggestion_provider: Any | None = None

    # The output PDF is known before the album areas are rendered.  Image
    # handling uses it to recognise old, CEWE-saved copies of our generated
    # index PNGs, so they do not become an extra layer beneath a new index.
    output_file_name: str | None = None
    message_counters: Any | None = None
