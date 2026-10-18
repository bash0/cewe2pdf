"""Values shared by the page-rendering helpers.

The converter still has some long-established module globals.  New rendering
helpers should receive this object instead of growing their own long list of
configuration and resource arguments.
"""

from dataclasses import dataclass
from typing import Any

from imageUtils import DEFAULT_GEO_LINK_URL_TEMPLATE


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
    line_scales: Any = None
    geo_links_enabled: bool = False
    geo_link_hotspot_size_mm: float = 10
    geo_link_url_template: str = DEFAULT_GEO_LINK_URL_TEMPLATE
