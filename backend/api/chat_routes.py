"""
Chat Routes for Text Labs v2
=============================

Handle chat messages and orchestrate element generation.
Integrates with Layout Service for presentation display.

v2.1: LLM-Powered Parameter Understanding Layer
- Uses Gemini with Pydantic structured output for parameter extraction
- Specialized extractors understand component-specific semantics:
  - TABLE: "6 rows" is structural, NOT count
  - TEXT_BOX: "5 bullet points" is items_per_instance, NOT count
- User's Advanced settings override LLM extraction
- Guaranteed valid JSON responses with type safety
"""

import html
import json
import logging
import re
import uuid
from typing import Optional, List, Dict, Any, TypeVar, Type, Tuple, Union
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..models.chat_models import ChatRole
from ..models.canvas_models import PlacedElement, GridPosition
from ..models.orchestrator_models import (
    ComponentType, ActionType, Intent, COMPONENT_CONFIG, TextBoxConfigData, ChartConfigData,
    ImageConfigData, MetricsConfigData, TableConfigData
)
from ..models.extraction_models import (
    TableExtraction, TextBoxExtraction, MetricsExtraction,
    ChartExtraction, ImageExtraction
)
from ..canvas.state_manager import StateManager
from ..services.atomic_client import AtomicClient, AtomicContext
from ..services.chart_client import ChartClient
from ..services.image_client import ImageClient
from ..services.llm_service import LLMService
from ..services.layout_service_client import LayoutServiceClient, SlideContent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

# Type variable for config models
T = TypeVar('T', bound=BaseModel)


def merge_configs(
    llm_extracted: Dict[str, Any],
    user_config: Optional[T],
    config_class: Type[T]
) -> T:
    """
    Merge LLM-extracted parameters with user's Advanced settings.

    Priority (highest to lowest):
    1. User's explicit Advanced settings (if user_config provided and field is not None)
    2. LLM-extracted parameters (if not None)
    3. Model defaults

    Args:
        llm_extracted: Parameters extracted by LLM from user's text
        user_config: User's explicit config from Advanced UI (can be None)
        config_class: The Pydantic model class to create

    Returns:
        Merged config object with all parameters resolved
    """
    # Start with defaults from the model class
    result_dict = {}

    # Apply LLM-extracted values (non-null only)
    for key, value in llm_extracted.items():
        if value is not None:
            result_dict[key] = value

    # Apply user config values (these override LLM extraction)
    if user_config:
        user_dict = user_config.model_dump()
        for key, value in user_dict.items():
            if value is not None:
                result_dict[key] = value

    # Create the config object (Pydantic will apply remaining defaults)
    try:
        return config_class(**result_dict)
    except Exception as e:
        logger.warning(f"[CHAT] Error creating {config_class.__name__}: {e}")
        # Fall back to user config or defaults
        return user_config if user_config else config_class()


async def extract_and_merge_config(
    message: str,
    component_type: str,
    user_config: Optional[T],
    config_class: Type[T],
    llm: LLMService,
    fallback_infer_func
) -> Tuple[T, Optional[int]]:
    """
    Extract parameters using specialized LLM extractors and merge with user config.

    v2.1: Uses Pydantic structured output for guaranteed type safety.
    Each extractor has focused prompts that understand component-specific semantics:
    - TABLE: "6 rows" is structural (rows=6), NOT count
    - TEXT_BOX: "5 bullet points" is items_per_instance (items_per_instance=5), NOT count
    - METRICS: "3 metrics" is count (count=3)

    Falls back to keyword-based inference if LLM extraction fails.

    Args:
        message: User's natural language message
        component_type: Component type (METRICS, TABLE, TEXT_BOX, CHART, IMAGE)
        user_config: User's explicit config from Advanced UI
        config_class: The Pydantic model class to create
        llm: LLM service instance
        fallback_infer_func: Fallback function for keyword-based inference

    Returns:
        Tuple of (merged config, extracted count or None)
    """
    try:
        # Use specialized extractors based on component type (v2.1)
        # These now use Pydantic structured output internally
        component_upper = component_type.upper()
        if component_upper == "TABLE":
            llm_extracted = await llm.extract_table_params(message)
        elif component_upper == "TEXT_BOX":
            llm_extracted = await llm.extract_textbox_params(message)
        elif component_upper == "METRICS":
            llm_extracted = await llm.extract_metrics_params(message)
        elif component_upper == "CHART":
            llm_extracted = await llm.extract_chart_params(message)
        elif component_upper == "IMAGE":
            llm_extracted = await llm.extract_image_params(message)
        else:
            # Fallback to generic extraction for unknown types
            llm_extracted = await llm.extract_parameters(message, component_type)

        # Extract count before merging (count is not in config classes)
        extracted_count = llm_extracted.get("count")

        # Log extraction results with component-specific context
        non_null_params = {k: v for k, v in llm_extracted.items() if v is not None}
        logger.info(
            f"[CHAT] v2.1 Pydantic extraction for {component_type}: "
            f"count={extracted_count}, params={list(non_null_params.keys())}"
        )

        # For TABLE, log structural dimensions separately from count
        if component_upper == "TABLE":
            rows = llm_extracted.get("rows")
            cols = llm_extracted.get("columns")
            if rows or cols:
                logger.info(f"[CHAT] TABLE structural: rows={rows}, columns={cols} (distinct from count)")

        # For TEXT_BOX, log items_per_instance separately from count
        if component_upper == "TEXT_BOX":
            items = llm_extracted.get("items_per_instance")
            if items:
                logger.info(f"[CHAT] TEXT_BOX items_per_instance={items} (distinct from count)")

        # Merge with user config (user settings take priority)
        config = merge_configs(llm_extracted, user_config, config_class)
        return config, extracted_count

    except Exception as e:
        logger.warning(f"[CHAT] LLM extraction failed for {component_type}: {e}, falling back to keywords")
        # Fall back to keyword-based inference
        keyword_config = fallback_infer_func(message.lower())

        # Still apply user overrides if provided
        if user_config:
            user_dict = user_config.model_dump()
            keyword_dict = keyword_config.model_dump()
            for key, value in user_dict.items():
                if value is not None:
                    keyword_dict[key] = value
            return config_class(**keyword_dict), None

        return keyword_config, None


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


def get_or_load_presentation_id(session_id: str, sm: StateManager) -> Optional[str]:
    """Get presentation_id from cache or load from session file."""
    if session_id in session_presentations:
        return session_presentations[session_id]

    presentation_id = sm.get_presentation_id(session_id)
    if presentation_id:
        session_presentations[session_id] = presentation_id
        logger.info(f"[CHAT] Loaded presentation_id {presentation_id} from session {session_id}")

    return presentation_id


def save_presentation_id(session_id: str, presentation_id: str, sm: StateManager) -> None:
    """Save presentation_id to cache and persistent session storage."""
    session_presentations[session_id] = presentation_id
    sm.set_presentation_id(session_id, presentation_id)
    logger.info(f"[CHAT] Saved presentation_id {presentation_id} for session {session_id}")


class ChatRequest(BaseModel):
    """Request for chat message."""
    session_id: str
    message: str
    debug: bool = False  # v2.1: Enable debug mode to see extraction without calling atomic API
    # v2.2: Advanced mode fields - when provided, skip LLM parsing entirely
    component_type: Optional[str] = None  # Required when using advanced settings (e.g., "TABLE", "TEXT_BOX")
    count: Optional[int] = None  # Number of component instances to create
    image_config: Optional[ImageConfigData] = None  # Direct config for IMAGE (bypasses NLP parsing)
    # Position config for TEXT_BOX, METRICS, TABLE (bypasses NLP parsing)
    position_config: Optional[Dict[str, int]] = None  # {start_col, start_row, position_width, position_height}
    textbox_config: Optional[TextBoxConfigData] = None
    metrics_config: Optional[MetricsConfigData] = None
    table_config: Optional[TableConfigData] = None
    chart_config: Optional[ChartConfigData] = None  # Direct config for CHART (bypasses NLP parsing)


def has_advanced_config(request: ChatRequest) -> bool:
    """
    Check if user provided any advanced styling configuration.

    NOTE: This does NOT check for component_type - that's handled separately
    as a DETERMINISTIC route (Priority 1) before this function is called.

    This function checks for styling configs (*_config objects) which indicate
    the user modified Advanced Settings in the modal.

    Args:
        request: The chat request to check

    Returns:
        True if any styling config is provided, False otherwise
    """
    return any([
        request.table_config,
        request.textbox_config,
        request.metrics_config,
        request.chart_config,
        request.image_config
    ])


def build_intent_from_configs(request: ChatRequest) -> Intent:
    """
    Build Intent directly from user-provided configs (no LLM).

    v2.2: Fast path - when user provides advanced settings, we skip
    LLM parsing entirely and construct the intent from their explicit configs.

    Args:
        request: Chat request with advanced configs

    Returns:
        Intent built from the provided configs
    """
    # Determine component type from explicit field or infer from whichever config is provided
    component_type = None
    if request.component_type:
        try:
            component_type = ComponentType(request.component_type.upper())
        except ValueError:
            # Try lowercase
            try:
                component_type = ComponentType(request.component_type.lower())
            except ValueError:
                pass

    # Fallback: infer from which config is provided
    if not component_type:
        if request.table_config:
            component_type = ComponentType.TABLE
        elif request.textbox_config:
            component_type = ComponentType.TEXT_BOX
        elif request.metrics_config:
            component_type = ComponentType.METRICS
        elif request.chart_config:
            component_type = ComponentType.CHART
        elif request.image_config:
            component_type = ComponentType.IMAGE

    return Intent(
        action=ActionType.ADD,
        component_type=component_type,
        count=request.count or 1,
        content_prompt=request.message,
        table_config=request.table_config,
        textbox_config=request.textbox_config,
        metrics_config=request.metrics_config,
        chart_config=request.chart_config,
        image_config=request.image_config,
        confidence=1.0  # High confidence since user explicitly specified
    )


class DebugInfo(BaseModel):
    """
    Debug information for extraction testing (v2.1).

    Shows what the LLM extracted and what would be sent to atomic API,
    without actually making the API call. Useful for debugging extraction issues.
    """
    raw_llm_response: Optional[str] = None  # What the intent parsing LLM returned
    llm_parse_error: Optional[str] = None   # Why JSON parsing failed (if it did)
    fallback_used: Optional[str] = None     # Which parser was used (parse_intent_simple, etc.)
    parsed_intent: Optional[Dict[str, Any]] = None  # Intent extracted from message
    extracted_params: Optional[Dict[str, Any]] = None  # Parameters from specialized extractor
    would_send_to_atomic: Optional[Dict[str, Any]] = None  # What WOULD be sent to atomic endpoint


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
    debug: Optional[DebugInfo] = None  # v2.1: Debug info when debug=True


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

    # Extract count (look for numbers) - v2.1: Context-aware extraction
    # CRITICAL: Don't extract count from structural dimensions
    # - TABLE: "6 rows" or "3 columns" are structural, NOT count
    # - TEXT_BOX: "5 bullet points" or "4 items" are items_per_instance, NOT count
    count = None
    words = message_lower.split()

    # Words that indicate the number is structural, not count
    structural_indicators = {
        "rows", "row", "columns", "column", "cols", "col",  # TABLE structural
        "bullets", "bullet", "points", "point", "items", "item",  # TEXT_BOX items
        "chars", "characters",  # Character limits
    }

    # Words that indicate the number IS count (instance count)
    count_indicators = {
        "tables", "table",  # TABLE count
        "boxes", "box", "sections", "section",  # TEXT_BOX count
        "metrics", "metric", "kpis", "kpi",  # METRICS count
        "charts", "chart",  # CHART count
        "images", "image", "photos", "photo",  # IMAGE count
    }

    number_words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}

    for i, word in enumerate(words):
        num_value = None

        if word.isdigit():
            num_value = int(word)
        elif word in number_words:
            num_value = number_words[word]

        if num_value is not None:
            # Check next word for context
            next_word = words[i + 1] if i + 1 < len(words) else ""

            # If followed by structural indicator, skip (not count)
            if next_word in structural_indicators:
                continue

            # If followed by count indicator, this IS count
            if next_word in count_indicators:
                count = num_value
                break

            # For ambiguous cases, only set count if it's a reasonable value
            # and we haven't found a better match yet
            if count is None and num_value <= 6:
                # Check if this might be structural based on component type
                if component_type == ComponentType.TABLE:
                    # For TABLE, only accept as count if explicitly followed by "table(s)"
                    continue
                elif component_type == ComponentType.TEXT_BOX:
                    # For TEXT_BOX, only accept as count if explicitly followed by count indicator
                    continue
                else:
                    count = num_value
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

    # v2.1: Extract rows and columns from message (structural dimensions)
    # e.g., "6 rows" → rows=6, "3 columns" → columns=3
    number_words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

    # Extract rows: "6 rows", "six rows", "6 data rows"
    rows_match = re.search(r'(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:data\s+)?rows?', msg)
    if rows_match:
        rows_val = rows_match.group(1)
        config.rows = int(rows_val) if rows_val.isdigit() else number_words.get(rows_val, None)
        if config.rows and (config.rows < 2 or config.rows > 15):
            config.rows = max(2, min(15, config.rows))  # Clamp to valid range

    # Extract columns: "3 columns", "three columns"
    cols_match = re.search(r'(\d+|one|two|three|four|five|six|seven|eight)\s+columns?', msg)
    if cols_match:
        cols_val = cols_match.group(1)
        config.columns = int(cols_val) if cols_val.isdigit() else number_words.get(cols_val, None)
        if config.columns and (config.columns < 2 or config.columns > 8):
            config.columns = max(2, min(8, config.columns))  # Clamp to valid range

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
    # Check for color followed by "header", "table", or standalone before "table"
    for keyword, color in color_keywords.items():
        if f"{keyword} header" in msg or f"{keyword} table" in msg or keyword in msg:
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
    # Default position - NOT full page, use 16:9 aspect ratio (12 cols x 7 rows)
    else:
        config.grid_row = "4/11"       # 7 rows (rows 4-10 inclusive = 7 height)
        config.grid_column = "2/14"    # 12 cols (cols 2-13 inclusive = 12 width)
        config.aspect_ratio = "16:9"   # Default aspect ratio

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


class ParseResult(BaseModel):
    """Result from parse_intent_llm with optional debug info."""
    intent: Intent
    debug_info: Optional[DebugInfo] = None


async def parse_intent_llm(
    message: str,
    llm: LLMService,
    user_textbox_config: Optional[TextBoxConfigData] = None,
    user_metrics_config: Optional[MetricsConfigData] = None,
    user_table_config: Optional[TableConfigData] = None,
    user_chart_config: Optional[ChartConfigData] = None,
    user_image_config: Optional[ImageConfigData] = None,
    capture_debug: bool = False
) -> Union[Intent, ParseResult]:
    """
    Parse intent using LLM with comprehensive parameter extraction.

    v2.1: Uses LLM to extract ALL component parameters from natural language,
    then merges with user's Advanced settings (user settings take priority).

    Args:
        message: User message
        llm: LLM service
        user_*_config: Optional user-provided configs from Advanced UI
        capture_debug: If True, returns ParseResult with debug info

    Returns:
        Parsed Intent with LLM-extracted + user-merged configs,
        or ParseResult if capture_debug=True
    """
    # Initialize debug info if capturing
    debug_info = DebugInfo() if capture_debug else None

    # First, get intent (action, component type) via LLM
    response = await llm.parse_intent(message)

    # Capture raw LLM response for debugging
    if debug_info:
        debug_info.raw_llm_response = response.content if response.success else None

    # Initialize variables for both success and fallback paths
    component_type = None
    intent_data = {"action": "add", "content_prompt": message}
    used_fallback = False

    if not response.success:
        logger.warning(f"[CHAT] LLM intent parsing failed: {response.error}")
        if debug_info:
            debug_info.llm_parse_error = response.error
            debug_info.fallback_used = "parse_intent_simple"
        # Use fallback but still try specialized extractors
        fallback_intent = parse_intent_simple(message)
        component_type = fallback_intent.component_type
        intent_data = {"action": fallback_intent.action.value, "content_prompt": message, "count": fallback_intent.count}
        used_fallback = True
    else:
        try:
            # Parse JSON response
            intent_data = json.loads(response.content)

            # Map component type string to enum
            if intent_data.get("component_type"):
                try:
                    component_type = ComponentType(intent_data["component_type"])
                except ValueError:
                    pass

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"[CHAT] Failed to parse LLM response: {e}")
            if debug_info:
                debug_info.llm_parse_error = str(e)
                debug_info.fallback_used = "parse_intent_simple"
            # Use fallback
            fallback_intent = parse_intent_simple(message)
            component_type = fallback_intent.component_type
            intent_data = {"action": fallback_intent.action.value, "content_prompt": message, "count": fallback_intent.count}
            used_fallback = True

    # Capture parsed intent for debugging
    if debug_info:
        debug_info.parsed_intent = {
            "action": intent_data.get("action"),
            "component_type": component_type.value if component_type else None,
            "count": intent_data.get("count"),
            "content_prompt": intent_data.get("content_prompt"),
            "position_hint": intent_data.get("position_hint"),
            "confidence": intent_data.get("confidence"),
            "used_fallback": used_fallback
        }

    # Extract comprehensive parameters using LLM specialized extractors
    # v2.1: Specialized extractors understand component-specific semantics
    # (e.g., "6 rows" is structural for TABLE, not count)
    table_config = None
    textbox_config = None
    metrics_config = None
    chart_config = None
    image_config = None
    specialized_count = None  # Count from specialized extractor (overrides intent parsing)

    if component_type == ComponentType.TABLE:
        table_config, specialized_count = await extract_and_merge_config(
            message=message,
            component_type="TABLE",
            user_config=user_table_config,
            config_class=TableConfigData,
            llm=llm,
            fallback_infer_func=infer_table_config
        )
        logger.info(f"[CHAT] TABLE config: rows={table_config.rows}, columns={table_config.columns}, specialized_count={specialized_count}")

    elif component_type == ComponentType.TEXT_BOX:
        textbox_config, specialized_count = await extract_and_merge_config(
            message=message,
            component_type="TEXT_BOX",
            user_config=user_textbox_config,
            config_class=TextBoxConfigData,
            llm=llm,
            fallback_infer_func=infer_textbox_config
        )
        logger.info(f"[CHAT] TEXT_BOX config: items_per_instance={textbox_config.items_per_instance}, list_style={textbox_config.list_style}, specialized_count={specialized_count}")

    elif component_type == ComponentType.METRICS:
        metrics_config, specialized_count = await extract_and_merge_config(
            message=message,
            component_type="METRICS",
            user_config=user_metrics_config,
            config_class=MetricsConfigData,
            llm=llm,
            fallback_infer_func=infer_metrics_config
        )
        logger.info(f"[CHAT] METRICS config: color_scheme={metrics_config.color_scheme}, layout={metrics_config.layout}, specialized_count={specialized_count}")

    elif component_type == ComponentType.CHART:
        chart_config, specialized_count = await extract_and_merge_config(
            message=message,
            component_type="CHART",
            user_config=user_chart_config,
            config_class=ChartConfigData,
            llm=llm,
            fallback_infer_func=infer_chart_config
        )
        logger.info(f"[CHAT] CHART config: chart_type={chart_config.chart_type}, include_insights={chart_config.include_insights}, specialized_count={specialized_count}")

    elif component_type == ComponentType.IMAGE:
        image_config, specialized_count = await extract_and_merge_config(
            message=message,
            component_type="IMAGE",
            user_config=user_image_config,
            config_class=ImageConfigData,
            llm=llm,
            fallback_infer_func=infer_image_config
        )
        logger.info(f"[CHAT] IMAGE config: style={image_config.style}, quality={image_config.quality}, specialized_count={specialized_count}")

    # Use specialized_count if available, otherwise fall back to intent_data count
    # This ensures "6 rows" doesn't become count=6 for TABLE
    final_count = specialized_count if specialized_count is not None else intent_data.get("count")

    # Capture extracted params for debugging
    if debug_info:
        extracted = {}
        if table_config:
            extracted = table_config.model_dump()
        elif textbox_config:
            extracted = textbox_config.model_dump()
        elif metrics_config:
            extracted = metrics_config.model_dump()
        elif chart_config:
            extracted = chart_config.model_dump()
        elif image_config:
            extracted = image_config.model_dump()
        # Remove None values for cleaner output
        debug_info.extracted_params = {k: v for k, v in extracted.items() if v is not None}

    intent = Intent(
        action=ActionType(intent_data.get("action", "add")),
        component_type=component_type,
        count=final_count,
        content_prompt=intent_data.get("content_prompt", message),
        position_hint=intent_data.get("position_hint"),
        confidence=intent_data.get("confidence", 0.9),
        table_config=table_config,
        textbox_config=textbox_config,
        metrics_config=metrics_config,
        chart_config=chart_config,
        image_config=image_config
    )

    if capture_debug:
        return ParseResult(intent=intent, debug_info=debug_info)
    return intent


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
        # =====================================================================
        # ARCHITECTURAL RULE: Component Type Routing is DETERMINISTIC
        # =====================================================================
        # When user clicks a toolbar button (Text Box, Table, Chart, etc.),
        # the component_type is ALREADY DECIDED. No LLM should ever override this.
        #
        # ROUTING PRIORITIES:
        # 1. component_type provided + advanced config → Use config directly (skip LLM)
        # 2. component_type provided + NO advanced config → FIXED type, extract config via LLM
        # 3. NO component_type → This should NOT happen from toolbar (error/fallback)
        #
        # LLM Role: Extract CONFIGURATION only (rows, columns, colors, etc.)
        # LLM NOT Role: Determine component type (that comes from button click)
        # =====================================================================
        debug_info = None

        # PRIORITY 1: component_type provided (toolbar button click)
        # Component type is SACRED - 100% deterministic routing
        if request.component_type:
            # Parse the component type from request (this is FIXED, user clicked a button)
            try:
                component_type = ComponentType(request.component_type.upper())
            except ValueError:
                try:
                    component_type = ComponentType(request.component_type.lower())
                except ValueError:
                    logger.error(f"[CHAT] Invalid component_type: {request.component_type}")
                    return ChatResponse(
                        success=False,
                        response_text=f"Unknown component type: {request.component_type}",
                        error=f"Invalid component_type: {request.component_type}"
                    )

            logger.info(f"[CHAT] DETERMINISTIC ROUTE: User clicked {component_type.value} button")

            # Check if user provided advanced config (styling options)
            if has_advanced_config(request):
                # CASE 1A: component_type + advanced config → Skip LLM entirely
                logger.info(f"[CHAT] Advanced config provided - using direct config (no LLM)")
                intent = build_intent_from_configs(request)

                if request.debug:
                    debug_info = DebugInfo(
                        fallback_used="deterministic_advanced_config",
                        parsed_intent={
                            "action": intent.action.value,
                            "component_type": intent.component_type.value if intent.component_type else None,
                            "count": intent.count,
                            "content_prompt": intent.content_prompt,
                            "mode": "deterministic + advanced config (LLM skipped)"
                        }
                    )
            else:
                # CASE 1B: component_type + NO advanced config → Extract config via LLM
                # Component type is FIXED, but we parse configuration from user's text
                logger.info(f"[CHAT] Extracting {component_type.value} config from message (type is FIXED)")

                # Use component-specific extractors (these extract CONFIG, not component type)
                extracted_params = {}
                extracted_count = None

                if component_type == ComponentType.TABLE:
                    extracted_params, extracted_count = await extract_and_merge_config(
                        message=message,
                        component_type="TABLE",
                        user_config=request.table_config,
                        config_class=TableConfigData,
                        llm=llm,
                        fallback_infer_func=infer_table_config
                    )
                    table_config = extracted_params
                    textbox_config = None
                    metrics_config = None
                    chart_config = None
                    image_config = None

                elif component_type == ComponentType.TEXT_BOX:
                    extracted_params, extracted_count = await extract_and_merge_config(
                        message=message,
                        component_type="TEXT_BOX",
                        user_config=request.textbox_config,
                        config_class=TextBoxConfigData,
                        llm=llm,
                        fallback_infer_func=infer_textbox_config
                    )
                    textbox_config = extracted_params
                    table_config = None
                    metrics_config = None
                    chart_config = None
                    image_config = None

                elif component_type == ComponentType.METRICS:
                    extracted_params, extracted_count = await extract_and_merge_config(
                        message=message,
                        component_type="METRICS",
                        user_config=request.metrics_config,
                        config_class=MetricsConfigData,
                        llm=llm,
                        fallback_infer_func=infer_metrics_config
                    )
                    metrics_config = extracted_params
                    table_config = None
                    textbox_config = None
                    chart_config = None
                    image_config = None

                elif component_type == ComponentType.CHART:
                    extracted_params, extracted_count = await extract_and_merge_config(
                        message=message,
                        component_type="CHART",
                        user_config=request.chart_config,
                        config_class=ChartConfigData,
                        llm=llm,
                        fallback_infer_func=infer_chart_config
                    )
                    chart_config = extracted_params
                    table_config = None
                    textbox_config = None
                    metrics_config = None
                    image_config = None

                elif component_type == ComponentType.IMAGE:
                    extracted_params, extracted_count = await extract_and_merge_config(
                        message=message,
                        component_type="IMAGE",
                        user_config=request.image_config,
                        config_class=ImageConfigData,
                        llm=llm,
                        fallback_infer_func=infer_image_config
                    )
                    image_config = extracted_params
                    table_config = None
                    textbox_config = None
                    metrics_config = None
                    chart_config = None

                else:
                    # Unknown component type - shouldn't happen with valid enum
                    table_config = None
                    textbox_config = None
                    metrics_config = None
                    chart_config = None
                    image_config = None

                # Build intent with FIXED component type and extracted config
                intent = Intent(
                    action=ActionType.ADD,
                    component_type=component_type,  # FIXED - never changes
                    count=request.count or extracted_count or 1,
                    content_prompt=message,
                    table_config=table_config,
                    textbox_config=textbox_config,
                    metrics_config=metrics_config,
                    chart_config=chart_config,
                    image_config=image_config,
                    confidence=1.0  # High confidence - deterministic routing
                )

                if request.debug:
                    extracted_dict = {}
                    if extracted_params:
                        extracted_dict = extracted_params.model_dump() if hasattr(extracted_params, 'model_dump') else {}
                    debug_info = DebugInfo(
                        fallback_used="deterministic_with_config_extraction",
                        parsed_intent={
                            "action": intent.action.value,
                            "component_type": intent.component_type.value,
                            "count": intent.count,
                            "content_prompt": intent.content_prompt,
                            "mode": "deterministic (type FIXED, config extracted via LLM)"
                        },
                        extracted_params={k: v for k, v in extracted_dict.items() if v is not None}
                    )

        # PRIORITY 2: NO component_type provided
        # This should be rare - frontend should always send component_type when user clicks a button
        # This path is only for free-form chat without toolbar button click
        else:
            logger.warning("[CHAT] No component_type provided - this should be rare")
            logger.info("[CHAT] Using full LLM parsing (component type detection + config extraction)")
            parse_result = await parse_intent_llm(
                message=message,
                llm=llm,
                user_textbox_config=request.textbox_config,
                user_metrics_config=request.metrics_config,
                user_table_config=request.table_config,
                user_chart_config=request.chart_config,
                user_image_config=request.image_config,
                capture_debug=request.debug
            )

            # Handle ParseResult vs Intent return types
            if request.debug and isinstance(parse_result, ParseResult):
                intent = parse_result.intent
                debug_info = parse_result.debug_info
            else:
                intent = parse_result

        logger.info(f"[CHAT] Parsed intent: action={intent.action}, type={intent.component_type}, count={intent.count}")

        # v2.1: Debug mode - return extraction details without calling atomic API
        if request.debug:
            # Build what WOULD be sent to atomic API
            config = COMPONENT_CONFIG.get(intent.component_type, {}) if intent.component_type else {}
            count = intent.count or config.get("default_count", 1)

            atomic_payload = {
                "count": count,
                "content_prompt": intent.content_prompt
            }

            # Add component-specific config
            if intent.table_config:
                atomic_payload["table_config"] = {k: v for k, v in intent.table_config.model_dump().items() if v is not None}
            if intent.textbox_config:
                atomic_payload["textbox_config"] = {k: v for k, v in intent.textbox_config.model_dump().items() if v is not None}
            if intent.metrics_config:
                atomic_payload["metrics_config"] = {k: v for k, v in intent.metrics_config.model_dump().items() if v is not None}
            if intent.chart_config:
                atomic_payload["chart_config"] = {k: v for k, v in intent.chart_config.model_dump().items() if v is not None}
            if intent.image_config:
                atomic_payload["image_config"] = {k: v for k, v in intent.image_config.model_dump().items() if v is not None}

            if debug_info:
                debug_info.would_send_to_atomic = {
                    "endpoint": f"/v1.2/atomic/{intent.component_type.value}" if intent.component_type else None,
                    "payload": atomic_payload
                }

            return ChatResponse(
                success=True,
                response_text="Debug mode: extraction details in debug object. No API calls made.",
                action_taken="debug_only",
                debug=debug_info
            )

        # Get or create presentation for this session
        presentation_id = get_or_load_presentation_id(session_id, sm)
        viewer_url = None

        if not presentation_id:
            # Create a new presentation
            result = await lsc.create_presentation(canvas_state.slide_title or "Text Labs Slide")
            if result.success:
                presentation_id = result.presentation_id
                viewer_url = result.viewer_url
                save_presentation_id(session_id, presentation_id, sm)
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
                save_presentation_id(session_id, presentation_id, sm)

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
            count = intent.count or 1  # Default to 1 instance, not config default

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

                # Apply position_config to chart_config if provided (must happen before chart generation)
                if request.position_config:
                    pos = request.position_config
                    logger.info(f"[CHAT] Applying position_config to CHART: {pos}")
                    chart_config.start_col = pos.get('start_col')
                    chart_config.start_row = pos.get('start_row')
                    chart_config.position_width = pos.get('position_width')
                    chart_config.position_height = pos.get('position_height')

                # Create presentation if not exists (needed for slide_id)
                if not presentation_id:
                    result = await lsc.create_presentation(canvas_state.slide_title or "Text Labs Slide")
                    if result.success:
                        presentation_id = result.presentation_id
                        viewer_url = result.viewer_url
                        save_presentation_id(session_id, presentation_id, sm)
                    else:
                        return ChatResponse(
                            success=False,
                            response_text=f"Failed to create presentation: {result.error}",
                            error=result.error
                        )

                # Generate chart via Analytics Service
                # v3.8.1: Pass grid position parameters if specified
                chart_result = await cc.generate(
                    chart_type=chart_config.chart_type,
                    narrative=intent.content_prompt,
                    presentation_id=presentation_id,
                    slide_id=f"slide-{len(canvas_state.elements) if hasattr(canvas_state, 'elements') else 0}",
                    include_insights=chart_config.include_insights,
                    series_names=chart_config.series_names if chart_config.series_names else None,
                    width=850,
                    height=500,
                    start_col=chart_config.start_col,
                    start_row=chart_config.start_row,
                    position_width=chart_config.position_width,
                    position_height=chart_config.position_height
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

                # Wrap chart in complete HTML document with Chart.js CDN
                # Frontend will render this in iframe srcdoc for isolated script execution
                # Analytics Service provides stretch-to-fit styling (v3.7.18)
                element_html = f'''<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: transparent;
        }}
    </style>
</head>
<body>
    {chart_html_content}
</body>
</html>'''

                # Build position dict for canvas (similar to IMAGE handling)
                # CRITICAL: Always provide default grid position for CHART
                # Use grid_width/grid_height from COMPONENT_CONFIG as defaults
                if chart_config.start_col is not None:
                    # User provided position_config - use their values
                    start_col = chart_config.start_col
                    start_row = chart_config.start_row or 4
                    width = chart_config.position_width or grid_width
                    height = chart_config.position_height or grid_height
                else:
                    # No position provided - use defaults (content safe zone)
                    start_col = 2  # Start at column 2
                    start_row = 4  # Start at row 4
                    width = grid_width   # From COMPONENT_CONFIG (16)
                    height = grid_height  # From COMPONENT_CONFIG (12)

                chart_position = {
                    "grid_row": f"{start_row}/{start_row + height}",
                    "grid_column": f"{start_col}/{start_col + width}",
                    "start_col": start_col,
                    "start_row": start_row,
                    "width": width,
                    "height": height
                }

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

                # CRITICAL: Ensure grid_row/grid_column are set (image service requires them)
                # Default to 16:9 aspect ratio (12×7 grids) positioned at top-left of content safe zone
                if not image_config.grid_row:
                    image_config.grid_row = "4/11"       # 7 rows starting at row 4
                if not image_config.grid_column:
                    image_config.grid_column = "2/14"   # 12 cols starting at col 2
                if not image_config.aspect_ratio:
                    image_config.aspect_ratio = "16:9"

                # Create presentation if not exists (needed for slide_id)
                if not presentation_id:
                    result = await lsc.create_presentation(canvas_state.slide_title or "Text Labs Slide")
                    if result.success:
                        presentation_id = result.presentation_id
                        viewer_url = result.viewer_url
                        save_presentation_id(session_id, presentation_id, sm)
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
                    save_presentation_id(session_id, presentation_id, sm)
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

            # CRITICAL FIX: Compute grid_position with CSS grid format for frontend
            # The atomic_response.grid_position may not have grid_row/grid_column which
            # the frontend needs. In basic chat mode, we compute these from grid dimensions.
            # Advanced mode with position_config already sets these via the position handler.
            if request.position_config:
                # Advanced mode: use position_config values
                pos = request.position_config
                start_col = pos.get('start_col', 2)
                start_row = pos.get('start_row', 4)
                width = pos.get('position_width', grid_width)
                height = pos.get('position_height', grid_height)
            else:
                # Basic chat mode: use default positioning in content safe zone
                start_col = 2  # Start at column 2 (content safe zone)
                start_row = 4  # Start at row 4 (content safe zone)
                width = grid_width
                height = grid_height

            computed_position = {
                "grid_row": f"{start_row}/{start_row + height}",
                "grid_column": f"{start_col}/{start_col + width}",
                "start_col": start_col,
                "start_row": start_row,
                "width": width,
                "height": height
            }

            return ChatResponse(
                success=True,
                response_text=response_text,
                action_taken="add",
                element={
                    "component_type": intent.component_type.value,
                    "html": atomic_response.html,
                    "variants_used": atomic_response.variants_used,
                    "grid_position": computed_position  # Use computed position with CSS grid format
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

    # Check if session already has a presentation (loads from file if not in cache)
    presentation_id = get_or_load_presentation_id(session_id, sm)
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
            save_presentation_id(session_id, presentation_id, sm)
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

    # Get presentation ID if exists (loads from file if not in cache)
    presentation_id = get_or_load_presentation_id(session_id, sm)

    # Save session state (StateManager handles persistence)
    sm.save_session(session_id)

    logger.info(f"[CHAT] Saved session {session_id}, presentation: {presentation_id}")

    return {
        "success": True,
        "session_id": session_id,
        "presentation_id": presentation_id,
        "message": "Progress saved"
    }
