"""
Chat Routes for Text Labs v2
=============================

Handle chat messages and orchestrate element generation.
Integrates with Layout Service for presentation display.
"""

import html
import json
import logging
import re
import uuid
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..models.chat_models import ChatRole
from ..models.canvas_models import PlacedElement, GridPosition
from ..models.orchestrator_models import (
    ComponentType, ActionType, Intent, COMPONENT_CONFIG, TextBoxConfigData, ChartConfigData,
    ImageConfigData, MetricsConfigData, TableConfigData
)
from ..canvas.state_manager import StateManager
from ..services.atomic_client import AtomicClient, AtomicContext
from ..services.chart_client import ChartClient
from ..services.image_client import ImageClient
from ..services.llm_service import LLMService
from ..services.layout_service_client import LayoutServiceClient, SlideContent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


def _get_placeholder_mode(intent: Intent) -> bool:
    """
    Get placeholder_mode from the appropriate component config.

    This determines whether to use LLM-generated content (False) or
    placeholder/lorem ipsum content (True).

    Args:
        intent: Parsed user intent with component configs

    Returns:
        True for placeholder mode, False for LLM generation
    """
    if intent.textbox_config:
        return intent.textbox_config.placeholder_mode
    if intent.metrics_config:
        return getattr(intent.metrics_config, 'placeholder_mode', False)
    if intent.table_config:
        return getattr(intent.table_config, 'placeholder_mode', False)
    return False  # Default: use LLM generation

# Shared instances (initialized in server.py)
state_manager: Optional[StateManager] = None
atomic_client: Optional[AtomicClient] = None
chart_client: Optional[ChartClient] = None
image_client: Optional[ImageClient] = None
llm_service: Optional[LLMService] = None
layout_service_client: Optional[LayoutServiceClient] = None

# Session to presentation mapping
session_presentations: Dict[str, str] = {}


def get_state_manager() -> StateManager:
    """Dependency to get state manager."""
    if state_manager is None:
        raise HTTPException(500, "State manager not initialized")
    return state_manager


def get_atomic_client() -> AtomicClient:
    """Dependency to get atomic client."""
    if atomic_client is None:
        raise HTTPException(500, "Atomic client not initialized")
    return atomic_client


def get_chart_client() -> ChartClient:
    """Dependency to get chart client."""
    if chart_client is None:
        raise HTTPException(500, "Chart client not initialized")
    return chart_client


def get_image_client() -> ImageClient:
    """Dependency to get image client."""
    if image_client is None:
        raise HTTPException(500, "Image client not initialized")
    return image_client


def get_llm_service() -> LLMService:
    """Dependency to get LLM service."""
    if llm_service is None:
        raise HTTPException(500, "LLM service not initialized")
    return llm_service


def get_layout_service_client() -> LayoutServiceClient:
    """Dependency to get Layout Service client."""
    if layout_service_client is None:
        raise HTTPException(500, "Layout Service client not initialized")
    return layout_service_client


class ChatRequest(BaseModel):
    """Request for chat message."""
    session_id: str
    message: str
    image_config: Optional[ImageConfigData] = None  # Direct config for IMAGE (bypasses NLP parsing)
    # Position config for TEXT_BOX, METRICS, TABLE (bypasses NLP parsing)
    position_config: Optional[Dict[str, int]] = None  # {start_col, start_row, position_width, position_height}
    textbox_config: Optional[TextBoxConfigData] = None
    metrics_config: Optional[MetricsConfigData] = None
    table_config: Optional[TableConfigData] = None
    chart_config: Optional[ChartConfigData] = None  # Direct config for CHART (bypasses NLP parsing)


class ChatResponse(BaseModel):
    """Response from chat message."""
    success: bool
    response_text: str
    action_taken: Optional[str] = None
    element: Optional[dict] = None
    presentation_id: Optional[str] = None
    viewer_url: Optional[str] = None
    suggestions: List[str] = Field(default_factory=list)
    error: Optional[str] = None


def parse_intent_simple(message: str) -> Intent:
    """
    Simplified rule-based intent parsing.

    Uses 3-type system:
    1. METRICS - for number-focused KPI cards
    2. TABLE - for grid-based data tables
    3. TEXT_BOX - for everything else (configurable text boxes)

    Args:
        message: User message

    Returns:
        Parsed Intent
    """
    message_lower = message.lower()

    # Determine action
    # Use word boundary check to avoid false positives (e.g., "placeholder" triggering "place")
    import re
    words_in_message = set(re.findall(r'\b\w+\b', message_lower))

    action = ActionType.ADD
    if words_in_message & {"remove", "delete", "clear"}:
        action = ActionType.REMOVE if "clear" not in words_in_message else ActionType.CLEAR
    elif words_in_message & {"move", "position", "reposition"}:
        action = ActionType.MOVE
    elif words_in_message & {"change", "modify", "update", "edit"}:
        action = ActionType.MODIFY
    elif words_in_message & {"generate", "fill"} or "create content" in message_lower or "write content" in message_lower:
        action = ActionType.GENERATE

    # Component type detection (5 types)
    # Priority: METRICS > TABLE > CHART > IMAGE > TEXT_BOX (fallback)
    component_type = None
    textbox_config = None
    chart_config = None
    image_config = None
    metrics_config = None
    table_config = None

    # Check for METRICS first (strict matching)
    metrics_keywords = COMPONENT_CONFIG[ComponentType.METRICS]["keywords"]
    if any(keyword in message_lower for keyword in metrics_keywords):
        component_type = ComponentType.METRICS
        metrics_config = infer_metrics_config(message_lower)

    # Check for explicit TEXT_BOX keywords (before TABLE to avoid "grid layout" collision)
    elif "text box" in message_lower or "text_box" in message_lower or "textbox" in message_lower:
        component_type = ComponentType.TEXT_BOX
        textbox_config = infer_textbox_config(message_lower)

    # Check for TABLE (but exclude "grid layout" which is for TEXT_BOX layout)
    elif any(keyword in message_lower for keyword in COMPONENT_CONFIG[ComponentType.TABLE]["keywords"]):
        # Don't match TABLE if "grid" is followed by "layout" (TEXT_BOX layout arrangement)
        if "grid layout" in message_lower or "grid arrangement" in message_lower:
            component_type = ComponentType.TEXT_BOX
            textbox_config = infer_textbox_config(message_lower)
        else:
            component_type = ComponentType.TABLE
            table_config = infer_table_config(message_lower)

    # Check for CHART (before IMAGE and TEXT_BOX fallback)
    elif any(keyword in message_lower for keyword in COMPONENT_CONFIG[ComponentType.CHART]["keywords"]):
        component_type = ComponentType.CHART
        chart_config = infer_chart_config(message_lower)

    # Check for IMAGE (before TEXT_BOX fallback)
    elif any(keyword in message_lower for keyword in COMPONENT_CONFIG[ComponentType.IMAGE]["keywords"]):
        component_type = ComponentType.IMAGE
        image_config = infer_image_config(message_lower)

    # Everything else -> TEXT_BOX with inferred config
    else:
        component_type = ComponentType.TEXT_BOX
        textbox_config = infer_textbox_config(message_lower)

    # Extract count (look for numbers)
    count = None
    words = message_lower.split()
    for i, word in enumerate(words):
        if word.isdigit():
            count = int(word)
            break
        # Check for number words
        number_words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
        if word in number_words:
            count = number_words[word]
            break

    return Intent(
        action=action,
        component_type=component_type,
        count=count,
        content_prompt=message,
        textbox_config=textbox_config,
        chart_config=chart_config,
        image_config=image_config,
        metrics_config=metrics_config,
        table_config=table_config,
        confidence=0.8  # Simplified routing has better confidence
    )


def infer_textbox_config(message: str) -> TextBoxConfigData:
    """
    Infer TEXT_BOX configuration from natural language.

    Analyzes the message to determine styling preferences based on keywords.

    Args:
        message: Lowercase user message

    Returns:
        TextBoxConfigData with inferred settings
    """
    config = TextBoxConfigData()

    # Detect list style
    if any(kw in message for kw in ["numbered", "ordered", "steps", "process", "phases"]):
        config.list_style = "numbers"
    elif any(kw in message for kw in ["plain text", "paragraph", "no bullets", "no list"]):
        config.list_style = "none"
    else:
        config.list_style = "bullets"  # Default

    # Detect background style
    if any(kw in message for kw in ["transparent", "no background", "plain", "simple"]):
        config.background = "transparent"
    else:
        config.background = "colored"  # Default

    # Detect border
    if any(kw in message for kw in ["bordered", "box", "boxed", "framed"]):
        config.border = True
    else:
        config.border = False  # Default

    # Detect corners
    if any(kw in message for kw in ["square", "sharp", "angular"]):
        config.corners = "square"
    else:
        config.corners = "rounded"  # Default

    # Detect title style
    if any(kw in message for kw in ["bold title", "highlighted", "emphasized"]):
        config.title_style = "highlighted"
    elif any(kw in message for kw in ["badge", "tagged", "labeled"]):
        config.title_style = "colored-bg"
    elif any(kw in message for kw in ["neutral title", "neutral style", "muted title"]):
        config.title_style = "neutral"
    elif any(kw in message for kw in ["no title", "without title", "titleless"]):
        config.show_title = False
    else:
        config.title_style = "plain"  # Default

    # Detect color scheme - only set if explicitly requested, otherwise let server default apply
    if any(kw in message for kw in ["solid color", "flat"]):
        config.color_scheme = "solid"
    elif any(kw in message for kw in ["gradient", "colorful", "vibrant"]):
        config.color_scheme = "gradient"
    # If no color scheme keywords detected, don't override - let server default (accent) apply

    # Detect layout direction
    layout_keywords_vertical = ["vertical", "vertically", "stacked", "stack", "top to bottom", "column"]
    layout_keywords_grid = ["grid", "2x2", "2 column", "two column"]

    if any(kw in message for kw in layout_keywords_vertical):
        config.layout = "vertical"
    elif any(kw in message for kw in layout_keywords_grid):
        config.layout = "grid"
    # horizontal is the default, no need to explicitly set

    # Detect placeholder mode (lorem ipsum)
    if any(kw in message for kw in ["lorem ipsum", "placeholder", "dummy content", "sample text"]):
        config.placeholder_mode = True
    else:
        config.placeholder_mode = False

    # Extract character limits from message (e.g., "title 30-50 chars", "items 60-120 chars")
    title_chars_match = re.search(r'title\s+(\d+)-(\d+)\s+chars?', message)
    if title_chars_match:
        config.title_min_chars = int(title_chars_match.group(1))
        config.title_max_chars = int(title_chars_match.group(2))

    item_chars_match = re.search(r'items?\s+(\d+)-(\d+)\s+chars?', message)
    if item_chars_match:
        config.item_min_chars = int(item_chars_match.group(1))
        config.item_max_chars = int(item_chars_match.group(2))

    # Detect theme mode (for dark text on light bg vs light text on dark bg)
    if any(kw in message for kw in ["dark mode", "dark theme", "dark text"]):
        config.theme_mode = "dark"

    # Detect color variant
    color_keywords = {
        "purple": "purple", "blue": "blue", "red": "red",
        "green": "green", "cyan": "cyan", "orange": "orange",
        "pink": "pink", "teal": "teal"
    }
    for kw, variant in color_keywords.items():
        if kw in message:
            config.color_variant = variant
            break

    # Detect grid columns (only applies when layout is grid)
    if config.layout == "grid":
        grid_col_match = re.search(r'(\d+)\s*columns?', message)
        if grid_col_match:
            cols = int(grid_col_match.group(1))
            if 1 <= cols <= 6:
                config.grid_cols = cols

    return config


def infer_chart_config(message: str) -> ChartConfigData:
    """
    Infer CHART configuration from natural language.

    Analyzes the message to determine chart type and options based on keywords.

    Args:
        message: Lowercase user message

    Returns:
        ChartConfigData with inferred settings
    """
    config = ChartConfigData()
    msg = message.lower()

    # Detect chart type from keywords (more specific patterns first)
    if any(kw in msg for kw in ["stacked area", "area stacked"]):
        config.chart_type = "area_stacked"
    elif any(kw in msg for kw in ["grouped bar", "side by side bar", "multi-bar"]):
        config.chart_type = "bar_grouped"
    elif any(kw in msg for kw in ["stacked bar", "bar stacked"]):
        config.chart_type = "bar_stacked"
    elif any(kw in msg for kw in ["horizontal bar", "bar horizontal"]):
        config.chart_type = "bar_horizontal"
    elif any(kw in msg for kw in ["waterfall", "bridge chart", "income bridge"]):
        config.chart_type = "waterfall"
    elif any(kw in msg for kw in ["scatter", "correlation", "x-y plot"]):
        config.chart_type = "scatter"
    elif any(kw in msg for kw in ["bubble"]):
        config.chart_type = "bubble"
    elif any(kw in msg for kw in ["radar", "spider", "web chart"]):
        config.chart_type = "radar"
    elif any(kw in msg for kw in ["polar", "polar area"]):
        config.chart_type = "polar_area"
    elif any(kw in msg for kw in ["doughnut", "donut"]):
        config.chart_type = "doughnut"
    elif any(kw in msg for kw in ["pie", "share", "distribution"]):
        config.chart_type = "pie"
    elif any(kw in msg for kw in ["area chart", "filled line"]):
        config.chart_type = "area"
    elif any(kw in msg for kw in ["bar chart", "bar", "column"]):
        config.chart_type = "bar_vertical"
    elif any(kw in msg for kw in ["line", "trend", "over time", "growth", "timeline"]):
        config.chart_type = "line"
    # Default to line chart if no specific type detected
    else:
        config.chart_type = "line"

    # Detect insights preference
    if any(kw in msg for kw in ["insight", "analysis", "with insights", "key insights"]):
        config.include_insights = True

    return config


def infer_metrics_config(message: str) -> MetricsConfigData:
    """
    Infer METRICS configuration from natural language.

    Analyzes the message to determine styling preferences based on keywords.

    Args:
        message: Lowercase user message

    Returns:
        MetricsConfigData with inferred settings
    """
    config = MetricsConfigData()
    msg = message.lower()

    # Detect corners
    if any(kw in msg for kw in ["square", "sharp", "angular", "square corners"]):
        config.corners = "square"
    else:
        config.corners = "rounded"  # Default

    # Detect border
    if any(kw in msg for kw in ["bordered", "with border", "border"]):
        config.border = True
    else:
        config.border = False  # Default

    # Detect alignment
    if any(kw in msg for kw in ["left-aligned", "left aligned", "align left"]):
        config.alignment = "left"
    elif any(kw in msg for kw in ["right-aligned", "right aligned", "align right"]):
        config.alignment = "right"
    else:
        config.alignment = "center"  # Default for metrics

    # Detect color scheme
    if any(kw in msg for kw in ["solid color", "solid", "flat"]):
        config.color_scheme = "solid"
    elif any(kw in msg for kw in ["pastel", "accent", "light colors"]):
        config.color_scheme = "accent"
    else:
        config.color_scheme = "gradient"  # Default

    # Detect layout
    if any(kw in msg for kw in ["vertical", "stacked", "column"]):
        config.layout = "vertical"
    elif any(kw in msg for kw in ["grid", "2x2"]):
        config.layout = "grid"
    else:
        config.layout = "horizontal"  # Default

    return config


def infer_table_config(message: str) -> TableConfigData:
    """
    Infer TABLE configuration from natural language.

    Analyzes the message to determine styling preferences based on keywords.

    Args:
        message: Lowercase user message

    Returns:
        TableConfigData with inferred settings
    """
    config = TableConfigData()
    msg = message.lower()

    # Detect header color (must be before header style detection)
    color_keywords = {
        "purple": "purple", "violet": "purple",
        "blue": "blue", "azure": "blue",
        "green": "green", "emerald": "green",
        "red": "red", "crimson": "red",
        "cyan": "cyan", "aqua": "cyan",
        "orange": "orange", "amber": "orange",
        "pink": "pink", "magenta": "pink",
        "yellow": "yellow", "gold": "yellow",
        "teal": "teal", "turquoise": "teal",
        "indigo": "indigo"
    }
    for keyword, color in color_keywords.items():
        if f"{keyword} header" in msg or f"{keyword} table" in msg:
            config.header_color = color
            break

    # Detect row striping
    if any(kw in msg for kw in ["no stripe", "no stripes", "plain rows", "no alternating"]):
        config.stripe_rows = False
    else:
        config.stripe_rows = True  # Default

    # Detect corners
    if any(kw in msg for kw in ["rounded", "round corners", "rounded corners"]):
        config.corners = "rounded"
    else:
        config.corners = "square"  # Default for tables

    # Detect header style
    if any(kw in msg for kw in ["pastel header", "soft header", "light header"]):
        config.header_style = "pastel"
    elif any(kw in msg for kw in ["minimal header", "simple header", "plain header"]):
        config.header_style = "minimal"
    else:
        config.header_style = "solid"  # Default (solid header, flat header, bold header)

    # Detect alignment
    if any(kw in msg for kw in ["center-aligned", "center aligned", "centered"]):
        config.alignment = "center"
    elif any(kw in msg for kw in ["right-aligned", "right aligned"]):
        config.alignment = "right"
    else:
        config.alignment = "left"  # Default for tables

    # Detect border style
    if any(kw in msg for kw in ["no border", "borderless", "no borders"]):
        config.border_style = "none"
    elif any(kw in msg for kw in ["medium border", "thicker border"]):
        config.border_style = "medium"
    elif any(kw in msg for kw in ["heavy border", "thick border", "bold border"]):
        config.border_style = "heavy"
    else:
        config.border_style = "light"  # Default

    # Detect layout
    if any(kw in msg for kw in ["vertical", "stacked"]):
        config.layout = "vertical"
    else:
        config.layout = "horizontal"  # Default

    # Detect first column bold
    if any(kw in msg for kw in ["first column bold", "bold first column", "first col bold"]):
        config.first_column_bold = True

    # Detect last column bold
    if any(kw in msg for kw in ["last column bold", "bold last column", "last col bold"]):
        config.last_column_bold = True

    # Detect total row
    if any(kw in msg for kw in ["total row", "totals row", "summary row", "show total"]):
        config.show_total_row = True

    # Extract character limits from message (e.g., "header 20-25 chars", "cell 90-100 chars")
    header_char_match = re.search(r'header\s+(\d+)-(\d+)\s*chars?', msg)
    if header_char_match:
        config.header_min_chars = int(header_char_match.group(1))
        config.header_max_chars = int(header_char_match.group(2))

    cell_char_match = re.search(r'cell\s+(\d+)-(\d+)\s*chars?', msg)
    if cell_char_match:
        config.cell_min_chars = int(cell_char_match.group(1))
        config.cell_max_chars = int(cell_char_match.group(2))

    return config


def infer_image_config(message: str) -> ImageConfigData:
    """
    Infer IMAGE configuration from natural language.

    Analyzes the message to determine style, quality, and position preferences.

    Args:
        message: Lowercase user message

    Returns:
        ImageConfigData with inferred settings
    """
    config = ImageConfigData()
    msg = message.lower()

    # Detect style
    if any(kw in msg for kw in ["illustration", "illustrated", "cartoon", "drawn"]):
        config.style = "illustration"
    elif any(kw in msg for kw in ["corporate", "business", "professional", "formal"]):
        config.style = "corporate"
    elif any(kw in msg for kw in ["abstract", "artistic", "creative"]):
        config.style = "abstract"
    elif any(kw in msg for kw in ["minimalist", "simple", "clean", "minimal"]):
        config.style = "minimalist"
    else:
        config.style = "realistic"  # Default

    # Detect quality
    if any(kw in msg for kw in ["draft", "quick", "low quality", "fast"]):
        config.quality = "draft"
    elif any(kw in msg for kw in ["high quality", "high-quality", "detailed", "hd"]):
        config.quality = "high"
    elif any(kw in msg for kw in ["ultra", "ultra quality", "highest quality", "4k"]):
        config.quality = "ultra"
    else:
        config.quality = "standard"  # Default

    # Detect position presets
    if any(kw in msg for kw in ["full", "full size", "full width"]):
        config.grid_row = "4/18"
        config.grid_column = "2/32"
    elif any(kw in msg for kw in ["half left", "left half", "left side"]):
        config.grid_row = "4/18"
        config.grid_column = "2/17"
    elif any(kw in msg for kw in ["half right", "right half", "right side"]):
        config.grid_row = "4/18"
        config.grid_column = "17/32"
    elif any(kw in msg for kw in ["top left", "upper left"]):
        config.grid_row = "4/11"
        config.grid_column = "2/17"
    elif any(kw in msg for kw in ["top right", "upper right"]):
        config.grid_row = "4/11"
        config.grid_column = "17/32"
    elif any(kw in msg for kw in ["bottom left", "lower left"]):
        config.grid_row = "11/18"
        config.grid_column = "2/17"
    elif any(kw in msg for kw in ["bottom right", "lower right"]):
        config.grid_row = "11/18"
        config.grid_column = "17/32"
    # Default position (full width)
    else:
        config.grid_row = "4/18"
        config.grid_column = "2/32"

    # Detect aspect ratio
    if any(kw in msg for kw in ["square", "1:1"]):
        config.aspect_ratio = "1:1"
    elif any(kw in msg for kw in ["16:9", "widescreen", "wide"]):
        config.aspect_ratio = "16:9"
    elif any(kw in msg for kw in ["4:3"]):
        config.aspect_ratio = "4:3"
    elif any(kw in msg for kw in ["3:2"]):
        config.aspect_ratio = "3:2"
    elif any(kw in msg for kw in ["portrait", "vertical", "9:16"]):
        config.aspect_ratio = "9:16"

    # Detect placeholder mode
    if any(kw in msg for kw in ["placeholder", "dummy", "sample"]):
        config.placeholder_mode = True

    return config


async def parse_intent_llm(message: str, llm: LLMService) -> Intent:
    """
    Parse intent using LLM.

    Args:
        message: User message
        llm: LLM service

    Returns:
        Parsed Intent
    """
    response = await llm.parse_intent(message)

    if not response.success:
        logger.warning(f"[CHAT] LLM intent parsing failed: {response.error}")
        return parse_intent_simple(message)

    try:
        # Parse JSON response
        intent_data = json.loads(response.content)

        # Map component type string to enum
        component_type = None
        if intent_data.get("component_type"):
            try:
                component_type = ComponentType(intent_data["component_type"])
            except ValueError:
                pass

        # Infer component configs from message keywords (same as parse_intent_simple)
        table_config = None
        textbox_config = None
        metrics_config = None
        chart_config = None
        image_config = None

        if component_type == ComponentType.TABLE:
            table_config = infer_table_config(message.lower())
        elif component_type == ComponentType.TEXT_BOX:
            textbox_config = infer_textbox_config(message.lower())
        elif component_type == ComponentType.METRICS:
            metrics_config = infer_metrics_config(message.lower())
        elif component_type == ComponentType.CHART:
            chart_config = infer_chart_config(message.lower())
        elif component_type == ComponentType.IMAGE:
            image_config = infer_image_config(message.lower())

        return Intent(
            action=ActionType(intent_data.get("action", "add")),
            component_type=component_type,
            count=intent_data.get("count"),
            content_prompt=intent_data.get("content_prompt", message),
            position_hint=intent_data.get("position_hint"),
            confidence=intent_data.get("confidence", 0.9),
            table_config=table_config,
            textbox_config=textbox_config,
            metrics_config=metrics_config,
            chart_config=chart_config,
            image_config=image_config
        )

    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"[CHAT] Failed to parse LLM response: {e}")
        return parse_intent_simple(message)


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    sm: StateManager = Depends(get_state_manager),
    ac: AtomicClient = Depends(get_atomic_client),
    cc: ChartClient = Depends(get_chart_client),
    ic: ImageClient = Depends(get_image_client),
    llm: LLMService = Depends(get_llm_service),
    lsc: LayoutServiceClient = Depends(get_layout_service_client)
):
    """
    Process a chat message and generate response.

    The orchestrator will:
    1. Parse intent from message
    2. Select appropriate component
    3. Generate content via Atomic API
    4. Create/update presentation via Layout Service
    5. Return response with viewer URL
    """
    session_id = request.session_id
    message = request.message.strip()

    if not message:
        return ChatResponse(
            success=False,
            response_text="Please provide a message.",
            error="Empty message"
        )

    # Ensure session exists
    canvas_state = sm.get_canvas_state(session_id)
    if not canvas_state:
        sm.create_session(session_id)
        canvas_state = sm.get_canvas_state(session_id)

    # Add user message to chat
    sm.add_chat_message(session_id, ChatRole.USER, message)

    try:
        # Parse intent (try LLM, fallback to rules)
        intent = await parse_intent_llm(message, llm)
        logger.info(f"[CHAT] Parsed intent: action={intent.action}, type={intent.component_type}, count={intent.count}")

        # Get or create presentation for this session
        presentation_id = session_presentations.get(session_id)
        viewer_url = None

        if not presentation_id:
            # Create a new presentation
            result = await lsc.create_presentation(canvas_state.slide_title or "Text Labs Slide")
            if result.success:
                presentation_id = result.presentation_id
                viewer_url = result.viewer_url
                session_presentations[session_id] = presentation_id
                logger.info(f"[CHAT] Created presentation {presentation_id} for session {session_id}")
            else:
                logger.error(f"[CHAT] Failed to create presentation: {result.error}")
        else:
            viewer_url = lsc.get_viewer_url(presentation_id)

        # Handle different actions
        if intent.action == ActionType.CLEAR:
            # Create a new presentation for clean slate
            result = await lsc.create_presentation(canvas_state.slide_title or "Text Labs Slide")
            if result.success:
                presentation_id = result.presentation_id
                viewer_url = result.viewer_url
                session_presentations[session_id] = presentation_id

            sm.clear_canvas(session_id)
            response_text = "Slide cleared. Ready for new elements."
            sm.add_chat_message(
                session_id, ChatRole.ASSISTANT, response_text,
                suggestions=["Add 3 metrics", "Add comparison table", "Add process steps"]
            )
            return ChatResponse(
                success=True,
                response_text=response_text,
                action_taken="clear",
                presentation_id=presentation_id,
                viewer_url=viewer_url,
                suggestions=["Add 3 metrics", "Add comparison table", "Add process steps"]
            )

        if intent.action == ActionType.REMOVE:
            response_text = "To remove an element, use the edit buttons on the slide, or say 'clear' to start fresh."
            sm.add_chat_message(session_id, ChatRole.ASSISTANT, response_text)
            return ChatResponse(
                success=True,
                response_text=response_text,
                action_taken="remove",
                presentation_id=presentation_id,
                viewer_url=viewer_url
            )

        if intent.action == ActionType.ADD:
            if not intent.component_type:
                # Ask for clarification (simplified to 3 types)
                response_text = "What would you like to add? Options: metrics (KPIs/stats), table (data grid), or text boxes (bullets/steps/sections)."
                sm.add_chat_message(
                    session_id, ChatRole.ASSISTANT, response_text,
                    suggestions=["Add 3 metrics", "Add data table", "Add bullet points", "Add numbered steps"]
                )
                return ChatResponse(
                    success=True,
                    response_text=response_text,
                    action_taken="clarify",
                    presentation_id=presentation_id,
                    viewer_url=viewer_url,
                    suggestions=["Add 3 metrics", "Add data table", "Add bullet points", "Add numbered steps"]
                )

            # Get component config
            config = COMPONENT_CONFIG.get(intent.component_type, {})
            count = intent.count or config.get("default_count", 3)

            # Use single_size for count=1, default size otherwise
            if count == 1 and "single_size" in config:
                grid_width, grid_height = config["single_size"]
            else:
                grid_width, grid_height = config.get("default_size", (28, 12))

            # Handle CHART component separately (uses ChartClient, not AtomicClient)
            if intent.component_type == ComponentType.CHART:
                # Prefer direct chart_config from request over inferred config (bypasses NLP parsing)
                if request.chart_config:
                    chart_config = request.chart_config
                    logger.info(f"[CHAT] Using direct chart_config from request: chart_type={chart_config.chart_type}")
                else:
                    chart_config = intent.chart_config or ChartConfigData()

                # Create presentation if not exists (needed for slide_id)
                if not presentation_id:
                    result = await lsc.create_presentation(canvas_state.slide_title or "Text Labs Slide")
                    if result.success:
                        presentation_id = result.presentation_id
                        viewer_url = result.viewer_url
                        session_presentations[session_id] = presentation_id
                    else:
                        return ChatResponse(
                            success=False,
                            response_text=f"Failed to create presentation: {result.error}",
                            error=result.error
                        )

                # Generate chart via Analytics Service
                chart_result = await cc.generate(
                    chart_type=chart_config.chart_type,
                    narrative=intent.content_prompt,
                    presentation_id=presentation_id,
                    slide_id=f"slide-{len(canvas_state.elements) if hasattr(canvas_state, 'elements') else 0}",
                    include_insights=chart_config.include_insights,
                    series_names=chart_config.series_names if chart_config.series_names else None,
                    width=850,
                    height=500
                )

                if not chart_result.success:
                    response_text = f"Failed to generate {chart_config.chart_type.replace('_', ' ')} chart: {chart_result.error}"
                    sm.add_chat_message(session_id, ChatRole.ASSISTANT, response_text)
                    return ChatResponse(
                        success=False,
                        response_text=response_text,
                        error=chart_result.error,
                        presentation_id=presentation_id,
                        viewer_url=viewer_url
                    )

                # Build chart response
                chart_type_display = chart_config.chart_type.replace('_', ' ')
                response_text = f"Added {chart_type_display} chart: {chart_result.chart_title}"
                if chart_config.include_insights:
                    response_text += " with key insights"

                suggestions = ["Add another chart", "Add metrics", "Add text boxes", "Clear and start over"]

                sm.add_chat_message(
                    session_id, ChatRole.ASSISTANT, response_text,
                    suggestions=suggestions
                )

                # Build element data with chart HTML (and optionally insights HTML)
                # Wrap in iframe with srcdoc to allow scripts to execute
                chart_html_content = chart_result.html or ""
                if chart_config.include_insights and chart_result.insights_html:
                    chart_html_content = f'''<div class="chart-with-insights">
                        {chart_result.html}
                        {chart_result.insights_html}
                    </div>'''

                # Pass Analytics HTML directly to Layout Service
                # Layout Service already has Chart.js loaded globally, so charts render natively
                # This avoids double iframe nesting and preserves animations
                element_html = f'''<div class="chart-direct-container" style="width: 100%; height: 100%; position: relative; overflow: hidden;">
    {chart_html_content}
</div>'''

                # Build position dict for canvas (similar to IMAGE handling)
                chart_position = {}
                if chart_config.start_col is not None:
                    start_col = chart_config.start_col
                    start_row = chart_config.start_row or 4
                    width = chart_config.position_width or 14
                    height = chart_config.position_height or 11
                    chart_position["grid_row"] = f"{start_row}/{start_row + height}"
                    chart_position["grid_column"] = f"{start_col}/{start_col + width}"
                    chart_position["start_col"] = start_col
                    chart_position["start_row"] = start_row
                    chart_position["width"] = width
                    chart_position["height"] = height

                return ChatResponse(
                    success=True,
                    response_text=response_text,
                    action_taken="add",
                    element={
                        "component_type": "CHART",
                        "html": element_html,
                        "chart_type": chart_config.chart_type,
                        "chart_title": chart_result.chart_title,
                        "element_id": chart_result.element_id,
                        "data_used": chart_result.data_used,
                        "grid_position": chart_position if chart_position else None
                    },
                    presentation_id=presentation_id,
                    viewer_url=viewer_url,
                    suggestions=suggestions
                )

            # Handle IMAGE component separately (uses ImageClient, not AtomicClient)
            if intent.component_type == ComponentType.IMAGE:
                # Prefer direct image_config from request over inferred config (better position accuracy)
                if request.image_config:
                    image_config = request.image_config
                    logger.info(f"[CHAT] Using direct image_config from request: grid_row={image_config.grid_row}, grid_column={image_config.grid_column}")
                else:
                    image_config = intent.image_config or ImageConfigData()

                # Create presentation if not exists (needed for slide_id)
                if not presentation_id:
                    result = await lsc.create_presentation(canvas_state.slide_title or "Text Labs Slide")
                    if result.success:
                        presentation_id = result.presentation_id
                        viewer_url = result.viewer_url
                        session_presentations[session_id] = presentation_id
                    else:
                        return ChatResponse(
                            success=False,
                            response_text=f"Failed to create presentation: {result.error}",
                            error=result.error
                        )

                # Generate image via Image Service
                image_result = await ic.generate(
                    prompt=intent.content_prompt,
                    presentation_id=presentation_id,
                    slide_id=f"slide-{len(canvas_state.elements) if hasattr(canvas_state, 'elements') else 0}",
                    style=image_config.style,
                    quality=image_config.quality,
                    grid_row=image_config.grid_row,
                    grid_column=image_config.grid_column,
                    aspect_ratio=image_config.aspect_ratio,
                    placeholder_mode=image_config.placeholder_mode
                )

                if not image_result.success:
                    response_text = f"Failed to generate image: {image_result.error}"
                    sm.add_chat_message(session_id, ChatRole.ASSISTANT, response_text)
                    return ChatResponse(
                        success=False,
                        response_text=response_text,
                        error=image_result.error,
                        presentation_id=presentation_id,
                        viewer_url=viewer_url
                    )

                # Build image response
                response_text = f"Added {image_config.style} image"
                if image_config.quality != "standard":
                    response_text += f" ({image_config.quality} quality)"

                suggestions = ["Add another image", "Add text boxes", "Add chart", "Clear and start over"]

                sm.add_chat_message(
                    session_id, ChatRole.ASSISTANT, response_text,
                    suggestions=suggestions
                )

                # Build position dict for canvas (include both CSS grid and grid-based values)
                position = {}
                if image_config.grid_row:
                    position["grid_row"] = image_config.grid_row
                if image_config.grid_column:
                    position["grid_column"] = image_config.grid_column
                # Include grid-based values for Layout Service compatibility
                if image_config.start_col is not None:
                    position["start_col"] = image_config.start_col
                if image_config.start_row is not None:
                    position["start_row"] = image_config.start_row
                if image_config.width is not None:
                    position["width"] = image_config.width
                if image_config.height is not None:
                    position["height"] = image_config.height

                return ChatResponse(
                    success=True,
                    response_text=response_text,
                    action_taken="add",
                    element={
                        "component_type": "IMAGE",
                        "html": image_result.html,
                        "image_url": image_result.image_url,
                        "element_id": image_result.element_id,
                        "style": image_config.style,
                        "quality": image_config.quality,
                        "aspect_ratio": image_config.aspect_ratio,
                        "grid_position": position if position else None
                    },
                    presentation_id=presentation_id,
                    viewer_url=viewer_url,
                    suggestions=suggestions
                )

            # Generate component via Atomic API with placeholder mode
            # Placeholders are instant (no LLM call), user can "generate" later
            context = AtomicContext(
                slide_title=canvas_state.slide_title,
                slide_purpose="presentation slide",
                tone="professional"
            )

            # Apply position config from request to component configs (bypasses NLP)
            if request.position_config:
                pos = request.position_config
                logger.info(f"[CHAT] Applying position_config: {pos}")
                if intent.component_type == ComponentType.TEXT_BOX:
                    # Prefer direct config from request, fallback to inferred
                    if request.textbox_config:
                        intent.textbox_config = request.textbox_config
                    if not intent.textbox_config:
                        intent.textbox_config = TextBoxConfigData()
                    intent.textbox_config.start_col = pos.get('start_col')
                    intent.textbox_config.start_row = pos.get('start_row')
                    intent.textbox_config.position_width = pos.get('position_width')
                    intent.textbox_config.position_height = pos.get('position_height')
                elif intent.component_type == ComponentType.METRICS:
                    if request.metrics_config:
                        intent.metrics_config = request.metrics_config
                    if not intent.metrics_config:
                        intent.metrics_config = MetricsConfigData()
                    intent.metrics_config.start_col = pos.get('start_col')
                    intent.metrics_config.start_row = pos.get('start_row')
                    intent.metrics_config.position_width = pos.get('position_width')
                    intent.metrics_config.position_height = pos.get('position_height')
                elif intent.component_type == ComponentType.TABLE:
                    if request.table_config:
                        intent.table_config = request.table_config
                    if not intent.table_config:
                        intent.table_config = TableConfigData()
                    intent.table_config.start_col = pos.get('start_col')
                    intent.table_config.start_row = pos.get('start_row')
                    intent.table_config.position_width = pos.get('position_width')
                    intent.table_config.position_height = pos.get('position_height')
                elif intent.component_type == ComponentType.CHART:
                    if request.chart_config:
                        intent.chart_config = request.chart_config
                    if not intent.chart_config:
                        intent.chart_config = ChartConfigData()
                    intent.chart_config.start_col = pos.get('start_col')
                    intent.chart_config.start_row = pos.get('start_row')
                    intent.chart_config.position_width = pos.get('position_width')
                    intent.chart_config.position_height = pos.get('position_height')

                # Override grid dimensions with position dimensions when specified
                if pos.get('position_width'):
                    grid_width = pos.get('position_width')
                if pos.get('position_height'):
                    grid_height = pos.get('position_height')
                logger.info(f"[CHAT] Grid dimensions after position override: {grid_width}x{grid_height}")

            atomic_response = await ac.generate(
                component_type=intent.component_type,
                prompt=intent.content_prompt,
                count=count,
                grid_width=grid_width,
                grid_height=grid_height,
                context=context,
                placeholder_mode=_get_placeholder_mode(intent),  # Respect config (AI vs Lorem Ipsum)
                textbox_config=intent.textbox_config,  # Pass TEXT_BOX config if present
                metrics_config=intent.metrics_config,  # Pass METRICS config if present
                table_config=intent.table_config  # Pass TABLE config if present
            )

            if not atomic_response.success:
                response_text = f"Failed to generate {intent.component_type.value}: {atomic_response.error}"
                sm.add_chat_message(session_id, ChatRole.ASSISTANT, response_text)
                return ChatResponse(
                    success=False,
                    response_text=response_text,
                    error=atomic_response.error,
                    presentation_id=presentation_id,
                    viewer_url=viewer_url
                )

            # Create presentation if not exists
            if not presentation_id:
                result = await lsc.create_presentation(canvas_state.slide_title or "Text Labs Slide")
                if result.success:
                    presentation_id = result.presentation_id
                    viewer_url = result.viewer_url
                    session_presentations[session_id] = presentation_id
                else:
                    return ChatResponse(
                        success=False,
                        response_text=f"Failed to create presentation: {result.error}",
                        error=result.error
                    )

            # NOTE: We no longer update the slide body here.
            # The frontend will insert the element as a positioned text box
            # via postMessage to the Layout Service iframe.
            # This allows multiple independent, draggable elements on the slide.

            # Build response
            response_text = f"Added {count} {intent.component_type.value.lower()} element{'s' if count > 1 else ''}."

            # Suggestions for 4-type system
            suggestions = []
            if intent.component_type == ComponentType.METRICS:
                suggestions = ["Add text boxes below", "Add chart", "Add more metrics"]
            elif intent.component_type == ComponentType.TABLE:
                suggestions = ["Add metrics above", "Add chart", "Add another table"]
            elif intent.component_type == ComponentType.TEXT_BOX:
                suggestions = ["Add metrics", "Add chart", "Add more text boxes"]
            else:
                suggestions = ["Add metrics", "Add chart", "Add text boxes"]

            sm.add_chat_message(
                session_id, ChatRole.ASSISTANT, response_text,
                suggestions=suggestions
            )

            return ChatResponse(
                success=True,
                response_text=response_text,
                action_taken="add",
                element={
                    "component_type": intent.component_type.value,
                    "html": atomic_response.html,
                    "variants_used": atomic_response.variants_used,
                    "grid_position": atomic_response.grid_position  # Include grid position
                },
                presentation_id=presentation_id,
                viewer_url=viewer_url,
                suggestions=suggestions
            )

        if intent.action == ActionType.GENERATE:
            # Generate real LLM content for all elements on the slide
            # This replaces placeholder content with AI-generated content

            # Get all elements from canvas state
            elements = canvas_state.elements if hasattr(canvas_state, 'elements') else []

            if not elements:
                response_text = "No elements to generate content for. Add some elements first, then say 'generate' to fill them with AI content."
                sm.add_chat_message(session_id, ChatRole.ASSISTANT, response_text)
                return ChatResponse(
                    success=True,
                    response_text=response_text,
                    action_taken="generate",
                    presentation_id=presentation_id,
                    viewer_url=viewer_url,
                    suggestions=["Add 3 metrics", "Add process steps", "Add comparison"]
                )

            # Build rich context from full slide
            context = AtomicContext(
                slide_title=canvas_state.slide_title or "Presentation Slide",
                slide_purpose=canvas_state.slide_purpose if hasattr(canvas_state, 'slide_purpose') else "presentation slide",
                audience=canvas_state.audience if hasattr(canvas_state, 'audience') else None,
                tone=canvas_state.tone if hasattr(canvas_state, 'tone') else "professional"
            )

            generated_count = 0
            updated_elements = []

            for element in elements:
                try:
                    # Get component type from element
                    comp_type_str = element.component_type if hasattr(element, 'component_type') else None
                    if not comp_type_str:
                        continue

                    comp_type = ComponentType(comp_type_str) if isinstance(comp_type_str, str) else comp_type_str

                    # Regenerate with LLM (placeholder_mode=False)
                    atomic_response = await ac.generate(
                        component_type=comp_type,
                        prompt=element.original_prompt if hasattr(element, 'original_prompt') else intent.content_prompt,
                        count=element.instance_count if hasattr(element, 'instance_count') else 1,
                        grid_width=element.grid_width if hasattr(element, 'grid_width') else 28,
                        grid_height=element.grid_height if hasattr(element, 'grid_height') else 12,
                        context=context,
                        placeholder_mode=False  # Generate real content now
                    )

                    if atomic_response.success:
                        updated_elements.append({
                            "element_id": element.id if hasattr(element, 'id') else str(uuid.uuid4()),
                            "component_type": comp_type.value if hasattr(comp_type, 'value') else str(comp_type),
                            "html": atomic_response.html,
                            "variants_used": atomic_response.variants_used
                        })
                        generated_count += 1

                except Exception as e:
                    logger.warning(f"[CHAT] Failed to generate content for element: {e}")
                    continue

            if generated_count > 0:
                response_text = f"Generated AI content for {generated_count} element{'s' if generated_count > 1 else ''}."
                suggestions = ["Edit content", "Add more elements", "Clear and start over"]
            else:
                response_text = "Could not generate content. Try adding elements first."
                suggestions = ["Add 3 metrics", "Add process steps", "Add comparison"]

            sm.add_chat_message(session_id, ChatRole.ASSISTANT, response_text, suggestions=suggestions)

            return ChatResponse(
                success=True,
                response_text=response_text,
                action_taken="generate",
                element={"updated_elements": updated_elements} if updated_elements else None,
                presentation_id=presentation_id,
                viewer_url=viewer_url,
                suggestions=suggestions
            )

        # Default response for unhandled actions
        response_text = f"I understood your request as: {intent.action.value}. Let me know if you'd like to add specific elements."
        sm.add_chat_message(session_id, ChatRole.ASSISTANT, response_text)
        return ChatResponse(
            success=True,
            response_text=response_text,
            action_taken=intent.action.value,
            presentation_id=presentation_id,
            viewer_url=viewer_url
        )

    except Exception as e:
        logger.error(f"[CHAT] Error processing message: {e}")
        error_text = "Sorry, I encountered an error processing your request. Please try again."
        sm.add_chat_message(session_id, ChatRole.ASSISTANT, error_text)
        return ChatResponse(
            success=False,
            response_text=error_text,
            error=str(e)
        )


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    sm: StateManager = Depends(get_state_manager)
):
    """Get chat history for a session."""
    chat_session = sm.get_chat_session(session_id)

    if not chat_session:
        raise HTTPException(404, f"Session not found: {session_id}")

    messages = chat_session.get_context_messages(limit=limit)

    return {
        "session_id": session_id,
        "messages": [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "element_id": msg.element_id,
                "suggestions": msg.suggestions
            }
            for msg in messages
        ]
    }


@router.post("/presentation/{session_id}")
async def create_or_get_presentation(
    session_id: str,
    sm: StateManager = Depends(get_state_manager),
    lsc: LayoutServiceClient = Depends(get_layout_service_client)
):
    """
    Create or get a presentation for a session.
    Called on page load to show a slide immediately.
    """
    # Ensure session exists
    canvas_state = sm.get_canvas_state(session_id)
    if not canvas_state:
        sm.create_session(session_id)
        canvas_state = sm.get_canvas_state(session_id)

    # Check if session already has a presentation
    presentation_id = session_presentations.get(session_id)
    viewer_url = None

    if presentation_id:
        # Already have a presentation
        viewer_url = lsc.get_viewer_url(presentation_id)
        logger.info(f"[CHAT] Using existing presentation {presentation_id} for session {session_id}")
    else:
        # Create a new presentation
        result = await lsc.create_presentation(canvas_state.slide_title or "Text Labs Slide")
        if result.success:
            presentation_id = result.presentation_id
            viewer_url = result.viewer_url
            session_presentations[session_id] = presentation_id
            logger.info(f"[CHAT] Created presentation {presentation_id} for session {session_id}")
        else:
            logger.error(f"[CHAT] Failed to create presentation: {result.error}")
            raise HTTPException(500, f"Failed to create presentation: {result.error}")

    return {
        "session_id": session_id,
        "presentation_id": presentation_id,
        "viewer_url": viewer_url
    }


@router.post("/save/{session_id}")
async def save_progress(
    session_id: str,
    sm: StateManager = Depends(get_state_manager)
):
    """
    Save the current session progress.
    """
    canvas_state = sm.get_canvas_state(session_id)
    if not canvas_state:
        raise HTTPException(404, f"Session not found: {session_id}")

    # Get presentation ID if exists
    presentation_id = session_presentations.get(session_id)

    # Save session state (StateManager handles persistence)
    sm.save_session(session_id)

    logger.info(f"[CHAT] Saved session {session_id}, presentation: {presentation_id}")

    return {
        "success": True,
        "session_id": session_id,
        "presentation_id": presentation_id,
        "message": "Progress saved"
    }
