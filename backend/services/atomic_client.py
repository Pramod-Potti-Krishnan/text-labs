"""
Atomic API Client for Text Labs
================================

HTTP client for calling Text Service v1.1 atomic endpoints on Railway.
All 3 types (METRICS, TABLE, TEXT_BOX) now call external API.
"""

import os
import logging
import uuid
from typing import Optional, Dict, Any, List
import httpx
from pydantic import BaseModel, Field

from ..models.orchestrator_models import (
    ComponentType, TextBoxConfigData, MetricsConfigData, TableConfigData
)

logger = logging.getLogger(__name__)

# Railway-deployed Text Service URL
ATOMIC_API_BASE_URL = os.getenv(
    "ATOMIC_API_URL",
    "https://web-production-5daf.up.railway.app"
)


class AtomicContext(BaseModel):
    """Context for content generation."""
    slide_title: Optional[str] = None
    slide_purpose: Optional[str] = None
    audience: Optional[str] = None
    tone: str = "professional"


class AtomicResponse(BaseModel):
    """Response from atomic API."""
    success: bool
    html: Optional[str] = None
    component_type: str
    instance_count: int
    arrangement: str
    variants_used: List[str] = Field(default_factory=list)
    character_counts: Dict[str, List[int]] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    # Grid position returned by text service v1.2
    grid_position: Optional[Dict[str, Any]] = None  # {start_col, start_row, width, height, grid_row, grid_column}


class AtomicClient:
    """
    Client for atomic component generation via external Text Service.

    3 Component Types (all call external API):
    - METRICS: Metrics cards with values and labels
    - TABLE: Styled HTML tables
    - TEXT_BOX: Configurable text boxes with LLM-generated content
    """

    # All component types now call external API
    ENDPOINT_MAP = {
        ComponentType.METRICS: "/v1.2/atomic/METRICS",
        ComponentType.TABLE: "/v1.2/atomic/TABLE",
        ComponentType.TEXT_BOX: "/v1.2/atomic/TEXT_BOX",
    }

    def __init__(self, base_url: Optional[str] = None, timeout: float = 60.0):
        self.base_url = base_url or ATOMIC_API_BASE_URL
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def generate(
        self,
        component_type: ComponentType,
        prompt: str,
        count: int,
        grid_width: int,
        grid_height: int,
        items_per_instance: Optional[int] = None,
        context: Optional[AtomicContext] = None,
        placeholder_mode: bool = False,
        textbox_config: Optional[TextBoxConfigData] = None,
        metrics_config: Optional[MetricsConfigData] = None,
        table_config: Optional[TableConfigData] = None
    ) -> AtomicResponse:
        """
        Generate atomic component via external API.

        All component types (METRICS, TABLE, TEXT_BOX) call external Text Service.

        Args:
            component_type: Type of component (METRICS, TABLE, TEXT_BOX)
            prompt: Content description for generation
            count: Number of component instances (1-N)
            grid_width: Available width in grid units (4-32)
            grid_height: Available height in grid units (4-18)
            items_per_instance: Number of items per instance
            context: Optional context for generation
            placeholder_mode: If True, use placeholder content (no LLM call)
            textbox_config: Configuration for TEXT_BOX component
            metrics_config: Configuration for METRICS component styling
            table_config: Configuration for TABLE component styling

        Returns:
            AtomicResponse with generated HTML and metadata
        """
        # Handle TEXT_BOX with different request format
        if component_type == ComponentType.TEXT_BOX:
            return await self._generate_text_box_external(
                prompt=prompt,
                count=count,
                items_per_instance=items_per_instance or 4,
                textbox_config=textbox_config,
                context=context,
                grid_width=grid_width,
                grid_height=grid_height
            )

        # METRICS and TABLE call external API
        endpoint = self.ENDPOINT_MAP.get(component_type)
        if not endpoint:
            return AtomicResponse(
                success=False,
                component_type=component_type.value,
                instance_count=0,
                arrangement="",
                error=f"Unknown component type: {component_type}"
            )

        # Build request data
        request_data = {
            "prompt": prompt,
            "count": count,
            "gridWidth": grid_width,
            "gridHeight": grid_height,
            "placeholder_mode": placeholder_mode,
        }

        # Add context if provided
        if context:
            request_data["context"] = context.model_dump(exclude_none=True)

        # Add METRICS config if provided
        if component_type == ComponentType.METRICS and metrics_config:
            request_data["metrics_config"] = {
                "corners": metrics_config.corners,
                "border": metrics_config.border,
                "alignment": metrics_config.alignment,
                "color_scheme": metrics_config.color_scheme,
                "layout": metrics_config.layout,
            }
            # Add optional color_variant if specified
            if metrics_config.color_variant:
                request_data["metrics_config"]["color_variant"] = metrics_config.color_variant
            # Also pass layout at top level for API compatibility
            request_data["layout"] = metrics_config.layout
            # Add position parameters if specified
            if metrics_config.start_col is not None:
                request_data["start_col"] = metrics_config.start_col
                request_data["start_row"] = metrics_config.start_row
                request_data["position_width"] = metrics_config.position_width
                request_data["position_height"] = metrics_config.position_height

        # Add TABLE config if provided
        if component_type == ComponentType.TABLE and table_config:
            request_data["table_config"] = {
                "stripe_rows": table_config.stripe_rows,
                "corners": table_config.corners,
                "header_style": table_config.header_style,
                "alignment": table_config.alignment,
                "border_style": table_config.border_style,
                "layout": table_config.layout,
                "first_column_bold": table_config.first_column_bold,
                "last_column_bold": table_config.last_column_bold,
                "show_total_row": table_config.show_total_row,
                "header_min_chars": table_config.header_min_chars,
                "header_max_chars": table_config.header_max_chars,
                "cell_min_chars": table_config.cell_min_chars,
                "cell_max_chars": table_config.cell_max_chars,
            }
            # Add optional header_color if specified
            if table_config.header_color:
                request_data["table_config"]["header_color"] = table_config.header_color
            # Also pass layout at top level for API compatibility
            request_data["layout"] = table_config.layout
            # Add position parameters if specified
            if table_config.start_col is not None:
                request_data["start_col"] = table_config.start_col
                request_data["start_row"] = table_config.start_row
                request_data["position_width"] = table_config.position_width
                request_data["position_height"] = table_config.position_height

        url = f"{self.base_url}{endpoint}"
        logger.info(f"[ATOMIC-CLIENT] Calling {url} with count={count}, grid={grid_width}x{grid_height}")

        try:
            client = await self._get_client()
            response = await client.post(url, json=request_data)
            response.raise_for_status()

            data = response.json()
            logger.info(
                f"[ATOMIC-CLIENT-OK] component={component_type.value}, "
                f"instances={data.get('instance_count')}, "
                f"html_chars={len(data.get('html') or '')}"
            )

            return AtomicResponse(**data)

        except httpx.TimeoutException:
            logger.error(f"[ATOMIC-CLIENT-TIMEOUT] Request to {url} timed out")
            return AtomicResponse(
                success=False,
                component_type=component_type.value,
                instance_count=0,
                arrangement="",
                error="Request timed out"
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"[ATOMIC-CLIENT-ERROR] HTTP {e.response.status_code}: {e.response.text}")
            return AtomicResponse(
                success=False,
                component_type=component_type.value,
                instance_count=0,
                arrangement="",
                error=f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            )

        except Exception as e:
            logger.error(f"[ATOMIC-CLIENT-ERROR] {type(e).__name__}: {e}")
            return AtomicResponse(
                success=False,
                component_type=component_type.value,
                instance_count=0,
                arrangement="",
                error=str(e)
            )

    async def _generate_text_box_external(
        self,
        prompt: str,
        count: int,
        items_per_instance: int,
        textbox_config: Optional[TextBoxConfigData] = None,
        context: Optional[AtomicContext] = None,
        grid_width: int = 28,
        grid_height: int = 12
    ) -> AtomicResponse:
        """
        Generate TEXT_BOX component via external Text Service v1.2 atomic API.

        Args:
            prompt: Content description
            count: Number of text boxes
            items_per_instance: Items per box
            textbox_config: Styling configuration
            context: Optional context for generation
            grid_width: Available width in grid units
            grid_height: Available height in grid units

        Returns:
            AtomicResponse with generated HTML
        """
        try:
            # Build request - only include required fields, let server use its defaults
            request_data = {
                "prompt": prompt or "Generate content for text boxes",
                "count": count,
                "items_per_box": items_per_instance,
                "gridWidth": grid_width,
                "gridHeight": grid_height,
            }

            # Only pass through textbox_config fields if config is provided
            # Server defaults are the source of truth - UAT client should not override
            if textbox_config:
                request_data.update({
                    "background_style": textbox_config.background,
                    "color_scheme": textbox_config.color_scheme,
                    "list_style": textbox_config.list_style,
                    "corners": textbox_config.corners,
                    "border": textbox_config.border,
                    "show_title": textbox_config.show_title,
                    "title_style": textbox_config.title_style,
                    "layout": textbox_config.layout,
                    "heading_align": textbox_config.heading_align,
                    "content_align": textbox_config.content_align,
                    "theme_mode": textbox_config.theme_mode,
                    "placeholder_mode": textbox_config.placeholder_mode,
                    "use_lorem_ipsum": textbox_config.placeholder_mode,
                    "title_min_chars": textbox_config.title_min_chars,
                    "title_max_chars": textbox_config.title_max_chars,
                    "item_min_chars": textbox_config.item_min_chars,
                    "item_max_chars": textbox_config.item_max_chars,
                })
                # Add new v1.2 fields if provided
                if textbox_config.color_variant:
                    request_data["color_variant"] = textbox_config.color_variant
                if textbox_config.grid_cols is not None:
                    request_data["grid_cols"] = textbox_config.grid_cols
                # Add position parameters if specified
                if textbox_config.start_col is not None:
                    request_data["start_col"] = textbox_config.start_col
                    request_data["start_row"] = textbox_config.start_row
                    request_data["position_width"] = textbox_config.position_width
                    request_data["position_height"] = textbox_config.position_height

            # Add context if provided
            if context:
                request_data["context"] = {
                    "slide_title": context.slide_title,
                    "slide_purpose": context.slide_purpose,
                    "audience": context.audience,
                    "tone": context.tone
                }

            url = f"{self.base_url}/v1.2/atomic/TEXT_BOX"
            logger.info(
                f"[ATOMIC-CLIENT] Calling TEXT_BOX API: {url}, "
                f"count={count}, items_per_box={items_per_instance}"
            )

            client = await self._get_client()
            response = await client.post(url, json=request_data)
            response.raise_for_status()

            data = response.json()

            logger.info(
                f"[ATOMIC-CLIENT-OK] TEXT_BOX from v1.2 API: "
                f"count={data.get('instance_count')}, html_chars={len(data.get('html') or '')}"
            )

            return AtomicResponse(**data)

        except httpx.TimeoutException:
            logger.error(f"[ATOMIC-CLIENT-TIMEOUT] TEXT_BOX request timed out")
            return AtomicResponse(
                success=False,
                component_type="TEXT_BOX",
                instance_count=0,
                arrangement="",
                error="Request timed out"
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"[ATOMIC-CLIENT-ERROR] TEXT_BOX HTTP {e.response.status_code}: {e.response.text}")
            return AtomicResponse(
                success=False,
                component_type="TEXT_BOX",
                instance_count=0,
                arrangement="",
                error=f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            )

        except Exception as e:
            logger.error(f"[ATOMIC-CLIENT-ERROR] TEXT_BOX generation failed: {e}")
            return AtomicResponse(
                success=False,
                component_type="TEXT_BOX",
                instance_count=0,
                arrangement="",
                error=str(e)
            )

    async def health_check(self) -> bool:
        """Check if the atomic API is healthy."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/v1.2/atomic/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"[ATOMIC-CLIENT-HEALTH] Failed: {e}")
            return False
