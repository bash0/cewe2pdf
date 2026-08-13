"""Values shared by the page-rendering helpers.

The converter still has some long-established module globals.  New rendering
helpers should receive this object instead of growing their own long list of
configuration and resource arguments.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class RenderContext:
    """Resources and conversion settings for one call to :func:`convertMcf`."""

    mcf_to_reportlab: float
    image_resolution: int
    image_quality: int
    background_resolution: int
    image_resampling_filter: Any
    default_config_section: Any
    clipart_files: dict[int, str]
    clipart_paths: tuple[str, ...]
    passepartout_folders: tuple[str, ...] = ()
