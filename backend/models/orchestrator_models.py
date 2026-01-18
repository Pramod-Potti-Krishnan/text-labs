"""
Orchestrator Models for Text Labs
==================================

Models for intent parsing, component selection, and layout planning.
"""

from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field

from .canvas_models import GridPosition, PlacedElement


class ActionType(str, Enum):
    """Type of action requested by user."""
    ADD = "add"
    MODIFY = "modify"
    REMOVE = "remove"
    MOVE = "move"
    CLEAR = "clear"
    GENERATE = "generate"  # Trigger content generation for all elements


class ComponentType(str, Enum):
    """
    Atomic component types (5 types).

    - METRICS: Number-focused KPI cards (unique HTML structure)
    - TABLE: Grid-based data tables (unique HTML structure)
    - TEXT_BOX: Unified configurable text boxes (replaces 7 old types)
    - CHART: Data visualization charts (14 chart types via Analytics Service)
    - IMAGE: AI-generated images with configurable style and position
    """
    METRICS = "METRICS"
    TABLE = "TABLE"
    TEXT_BOX = "TEXT_BOX"
    CHART = "CHART"
    IMAGE = "IMAGE"


# Component configuration (5 types)
# TEXT_BOX replaces: SEQUENTIAL, COMPARISON, SECTIONS, CALLOUT, TEXT_BULLETS, BULLET_BOX, NUMBERED_LIST
# CHART connects to Analytics Service atomic chart endpoints
# IMAGE connects to Image Service atomic image endpoints
COMPONENT_CONFIG = {
    ComponentType.METRICS: {
        "endpoint": "METRICS",
        "count_range": (1, 4),
        "default_count": 3,
        "default_size": (28, 8),
        "single_size": (10, 8),
        # Strict keywords for METRICS - no "numbers" to avoid collision with "numbered"
        "keywords": ["metrics", "kpis", "stats", "statistics", "data points", "metric", "kpi"]
    },
    ComponentType.TABLE: {
        "endpoint": "TABLE",
        "count_range": (1, 2),
        "default_count": 1,
        "default_size": (28, 10),
        "single_size": (28, 10),
        "columns_range": (2, 6),
        "rows_range": (2, 10),
        # Strict keywords for TABLE - removed 'grid' to avoid collision with TEXT_BOX 'grid layout'
        "keywords": ["table", "data table", "schedule", "matrix"]
    },
    ComponentType.TEXT_BOX: {
        "endpoint": "TEXT_BOX",
        "count_range": (1, 6),
        "default_count": 3,
        "default_size": (28, 12),
        "single_size": (14, 10),
        "items_range": (1, 7),
        # TEXT_BOX is the fallback - catches everything that's not METRICS or TABLE
        # These keywords help with explicit matching, but TEXT_BOX is also the default
        "keywords": [
            # Bullet-related
            "bullets", "bullet points", "bullet list", "features", "benefits",
            # Numbered/steps-related
            "numbered", "numbered list", "ordered", "steps", "process", "phases",
            # Section-related
            "sections", "categories", "topics", "areas", "pillars",
            # Comparison/columns-related
            "comparison", "compare", "vs", "versus", "columns", "options",
            # Callout-related
            "callout", "highlight", "key points", "takeaways", "insights",
            # Generic text
            "text", "content", "list", "items", "points"
        ]
    },
    ComponentType.CHART: {
        "endpoint": "CHART",
        "count_range": (1, 2),
        "default_count": 1,
        "default_size": (14, 11),
        "single_size": (14, 11),
        # Chart keywords - check BEFORE TEXT_BOX in intent parsing
        "keywords": [
            "chart", "graph", "plot", "visualization", "visualize",
            "line chart", "bar chart", "pie chart", "doughnut chart",
            "scatter", "bubble", "radar", "waterfall", "area chart",
            "trend chart", "comparison chart", "histogram"
        ]
    },
    ComponentType.IMAGE: {
        "endpoint": "IMAGE",
        "count_range": (1, 4),
        "default_count": 1,
        "default_size": (14, 10),
        "single_size": (14, 10),
        # Image keywords - check BEFORE TEXT_BOX in intent parsing
        "keywords": [
            "image", "photo", "picture", "illustration", "visual", "graphic",
            "photograph", "artwork", "ai image", "generate image", "create image"
        ]
    },
}


class TextBoxConfigData(BaseModel):
    """TEXT_BOX configuration data (matching frontend textboxConfig)."""
    background: str = "colored"         # colored | transparent
    corners: str = "rounded"            # rounded | square
    border: bool = False
    show_title: bool = True
    title_style: str = "plain"          # plain | highlighted | colored-bg | neutral
    list_style: str = "bullets"         # bullets | numbers | none
    color_scheme: str = "accent"        # gradient | solid | accent (accent = pastel backgrounds)
    layout: str = "horizontal"          # horizontal | vertical | grid
    heading_align: str = "left"         # left | center | right (heading alignment)
    content_align: str = "left"         # left | center | right (bullet content alignment)
    theme_mode: str = "light"           # light | dark (affects text colors)
    placeholder_mode: bool = False      # True = lorem ipsum, False = AI generated
    title_min_chars: int = 30           # 5-500 min characters for title
    title_max_chars: int = 40           # 5-500 max characters for title
    item_min_chars: int = 80            # 5-500 min characters per bullet
    item_max_chars: int = 100           # 5-500 max characters per bullet
    color_variant: Optional[str] = None # purple, blue, red, green, cyan, orange, pink, teal
    grid_cols: Optional[int] = None     # 1-6 for grid layout
    # Grid positioning (optional, for canvas placement)
    start_col: Optional[int] = None     # Starting column (1-32)
    start_row: Optional[int] = None     # Starting row (1-18)
    position_width: Optional[int] = None  # Width in grid units (4-32)
    position_height: Optional[int] = None # Height in grid units (4-18)


class ChartConfigData(BaseModel):
    """CHART configuration data (matching frontend chartConfig)."""
    chart_type: str = "line"            # One of 14 valid chart types
    include_insights: bool = False      # Whether to include Key Insights panel
    series_names: List[str] = Field(default_factory=list)  # Custom series names for multi-series charts


class ImageConfigData(BaseModel):
    """IMAGE configuration data (matching frontend imageConfig).

    Grid positioning uses Layout Service compatible format:
    - Grid is 32 columns x 18 rows (60px per cell)
    - Content safe zone: rows 4-17, cols 2-31
    """
    style: str = "realistic"            # realistic | illustration | corporate | abstract | minimalist
    quality: str = "standard"           # draft | standard | high | ultra
    # CSS Grid format (derived from grid-based values)
    grid_row: Optional[str] = None      # CSS grid row position (e.g., "4/18")
    grid_column: Optional[str] = None   # CSS grid column position (e.g., "2/32")
    # Grid-based positioning (Layout Service compatible)
    start_col: Optional[int] = None     # Starting column (1-32)
    start_row: Optional[int] = None     # Starting row (1-18)
    width: Optional[int] = None         # Width in grid units (4-32)
    height: Optional[int] = None        # Height in grid units (4-18)
    # Aspect ratio (calculated from width/height if not provided)
    aspect_ratio: Optional[str] = None  # Aspect ratio (e.g., "16:9", "4:3", "1:1")
    placeholder_mode: bool = False      # True = placeholder, False = AI generated


class MetricsConfigData(BaseModel):
    """METRICS configuration data (matching frontend metricsConfig)."""
    corners: str = "rounded"            # rounded | square
    border: bool = False                # Show border around cards
    alignment: str = "center"           # left | center | right
    color_scheme: str = "gradient"      # gradient | solid | accent (pastel)
    layout: str = "horizontal"          # horizontal | vertical | grid
    placeholder_mode: bool = False      # True = lorem ipsum, False = AI generated
    color_variant: Optional[str] = None # purple, blue, red, green, cyan, orange, pink, teal, yellow, indigo
    # Grid positioning (optional, for canvas placement)
    start_col: Optional[int] = None     # Starting column (1-32)
    start_row: Optional[int] = None     # Starting row (1-18)
    position_width: Optional[int] = None  # Width in grid units (4-32)
    position_height: Optional[int] = None # Height in grid units (4-18)


class TableConfigData(BaseModel):
    """TABLE configuration data (matching frontend tableConfig)."""
    stripe_rows: bool = True            # Alternating row colors (banded rows linked to header color)
    corners: str = "square"             # rounded | square
    header_style: str = "solid"         # solid | pastel | minimal
    alignment: str = "left"             # left | center | right
    border_style: str = "light"         # none | light | medium | heavy
    layout: str = "horizontal"          # horizontal | vertical
    placeholder_mode: bool = False      # True = lorem ipsum, False = AI generated
    header_color: Optional[str] = None  # purple, blue, red, green, cyan, orange, pink, teal, yellow, indigo
    first_column_bold: bool = False     # Bold text in first column
    last_column_bold: bool = False      # Bold text in last column
    show_total_row: bool = False        # Show total row with double line above
    header_min_chars: int = 5           # 5-500 min characters for header cells
    header_max_chars: int = 25          # 5-500 max characters for header cells
    cell_min_chars: int = 10            # 5-500 min characters per body cell
    cell_max_chars: int = 50            # 5-500 max characters per body cell
    # Grid positioning (optional, for canvas placement)
    start_col: Optional[int] = None     # Starting column (1-32)
    start_row: Optional[int] = None     # Starting row (1-18)
    position_width: Optional[int] = None  # Width in grid units (4-32)
    position_height: Optional[int] = None # Height in grid units (4-18)


class Intent(BaseModel):
    """Parsed intent from user message."""
    action: ActionType
    component_type: Optional[ComponentType] = None
    count: Optional[int] = None
    items_per_instance: Optional[int] = None  # For flexible components
    content_prompt: str = ""
    position_hint: Optional[str] = None  # "below", "right", "center", etc.
    target_element_id: Optional[str] = None  # For modify/remove/move actions
    textbox_config: Optional[TextBoxConfigData] = None  # For TEXT_BOX component
    chart_config: Optional[ChartConfigData] = None  # For CHART component
    image_config: Optional[ImageConfigData] = None  # For IMAGE component
    metrics_config: Optional[MetricsConfigData] = None  # For METRICS component
    table_config: Optional[TableConfigData] = None  # For TABLE component
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ComponentSelection(BaseModel):
    """Selected component with parameters."""
    component_type: ComponentType
    count: int
    items_per_instance: Optional[int] = None
    grid_width: int
    grid_height: int
    content_prompt: str


class LayoutPlan(BaseModel):
    """Planned layout for a new element."""
    grid_position: GridPosition
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning: str = ""
    alternative_positions: List[GridPosition] = Field(default_factory=list)


class OrchestratorResponse(BaseModel):
    """Response from the orchestrator."""
    success: bool
    response_text: str
    action_taken: ActionType
    element: Optional[PlacedElement] = None
    suggestions: List[str] = Field(default_factory=list)
    reasoning: Optional[str] = None
    error: Optional[str] = None
