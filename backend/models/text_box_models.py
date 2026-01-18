"""
Text Box Configuration Models
=============================

Unified configuration model for all text-based slide components.
Replaces 7 separate component types with a single configurable TEXT_BOX.

Only METRICS and TABLE remain separate (unique HTML structures).
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class LayoutDirection(str, Enum):
    """How multiple text boxes are arranged."""
    HORIZONTAL = "horizontal"  # Side by side (1 row)
    VERTICAL = "vertical"      # Stacked (1 column)
    GRID = "grid"              # 2-column grid


class BackgroundStyle(str, Enum):
    """Background fill style for text boxes."""
    COLORED = "colored"        # Gradient or solid color background
    TRANSPARENT = "transparent"  # No background color


class CornerStyle(str, Enum):
    """Corner radius style."""
    ROUNDED = "rounded"  # 16px border-radius
    SQUARE = "square"    # 0px border-radius


class TitleStyle(str, Enum):
    """How the title/heading is styled."""
    PLAIN = "plain"            # Simple text, inherit color
    HIGHLIGHTED = "highlighted"  # Bold, slightly larger
    COLORED_BG = "colored-bg"   # Title in a colored badge/pill


class ListStyle(str, Enum):
    """Type of list markers."""
    BULLETS = "bullets"   # Unordered list with bullet points
    NUMBERS = "numbers"   # Ordered list with 1, 2, 3...
    NONE = "none"         # No list markers, just paragraphs


class ColorScheme(str, Enum):
    """Color theme for the boxes."""
    GRADIENT = "gradient"     # Multi-color gradients (purple, pink, cyan, etc.)
    SOLID = "solid"           # Solid colors (blue, green, orange, etc.)
    ACCENT_ONLY = "accent"    # White/transparent bg with colored accents


class TextAlign(str, Enum):
    """Text alignment within boxes."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class TextBoxConfig(BaseModel):
    """
    Unified configuration for text box components.

    This single model replaces:
    - SEQUENTIAL (numbered boxes)
    - COMPARISON (side-by-side boxes)
    - SECTIONS (colored titled sections)
    - CALLOUT (highlighted single box)
    - TEXT_BULLETS (bullet list)
    - BULLET_BOX (bordered bullet list)
    - NUMBERED_LIST (numbered list)
    """

    # Quantity & Layout
    count: int = Field(default=1, ge=1, le=6, description="Number of text boxes (1-6)")
    layout: LayoutDirection = Field(default=LayoutDirection.HORIZONTAL, description="Arrangement of boxes")

    # Box Styling
    background: BackgroundStyle = Field(default=BackgroundStyle.COLORED, description="Background fill")
    border: bool = Field(default=False, description="Show border around box")
    corners: CornerStyle = Field(default=CornerStyle.ROUNDED, description="Corner style")

    # Title/Heading
    show_title: bool = Field(default=True, description="Show title in each box")
    title_style: TitleStyle = Field(default=TitleStyle.PLAIN, description="Title styling")

    # List Items
    list_style: ListStyle = Field(default=ListStyle.BULLETS, description="List marker type")
    items_per_box: int = Field(default=4, ge=1, le=10, description="Number of items per box")

    # Theme
    color_scheme: ColorScheme = Field(default=ColorScheme.GRADIENT, description="Color theme")

    # Text Alignment
    text_align: TextAlign = Field(default=TextAlign.LEFT, description="Text alignment within boxes")

    class Config:
        use_enum_values = True


class TextBoxRequest(BaseModel):
    """Request model for generating text boxes."""
    config: TextBoxConfig = Field(default_factory=TextBoxConfig)
    content_prompt: Optional[str] = Field(default=None, description="Description of content to generate")
    items: Optional[List[str]] = Field(default=None, description="Pre-defined items (bypasses AI generation)")
    titles: Optional[List[str]] = Field(default=None, description="Pre-defined titles for each box")


class TextBoxResponse(BaseModel):
    """Response model for generated text boxes."""
    success: bool
    html: Optional[str] = None
    config_used: Optional[TextBoxConfig] = None
    error: Optional[str] = None


# Legacy type mapping for backward compatibility
LEGACY_TYPE_CONFIGS = {
    "SEQUENTIAL": TextBoxConfig(
        background=BackgroundStyle.COLORED,
        list_style=ListStyle.NUMBERS,
        show_title=True,
        title_style=TitleStyle.HIGHLIGHTED
    ),
    "COMPARISON": TextBoxConfig(
        count=2,
        layout=LayoutDirection.HORIZONTAL,
        border=True,
        background=BackgroundStyle.TRANSPARENT
    ),
    "SECTIONS": TextBoxConfig(
        background=BackgroundStyle.COLORED,
        title_style=TitleStyle.COLORED_BG,
        list_style=ListStyle.BULLETS
    ),
    "CALLOUT": TextBoxConfig(
        count=1,
        background=BackgroundStyle.COLORED,
        border=False,
        show_title=True
    ),
    "TEXT_BULLETS": TextBoxConfig(
        background=BackgroundStyle.TRANSPARENT,
        border=False,
        list_style=ListStyle.BULLETS
    ),
    "BULLET_BOX": TextBoxConfig(
        background=BackgroundStyle.TRANSPARENT,
        border=True,
        list_style=ListStyle.BULLETS
    ),
    "NUMBERED_LIST": TextBoxConfig(
        background=BackgroundStyle.TRANSPARENT,
        border=False,
        list_style=ListStyle.NUMBERS
    ),
}


def get_config_for_legacy_type(component_type: str, count: int = None) -> TextBoxConfig:
    """
    Convert legacy component type to TextBoxConfig.

    Args:
        component_type: One of SEQUENTIAL, COMPARISON, SECTIONS, CALLOUT,
                       TEXT_BULLETS, BULLET_BOX, NUMBERED_LIST
        count: Override the default count

    Returns:
        TextBoxConfig with appropriate settings
    """
    if component_type not in LEGACY_TYPE_CONFIGS:
        # Default to basic text bullets
        config = TextBoxConfig()
    else:
        config = LEGACY_TYPE_CONFIGS[component_type].model_copy()

    if count is not None:
        config.count = count

    return config
