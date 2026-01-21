"""
Chart Client for Text Labs
===========================

HTTP client for calling Analytics Service atomic chart endpoints.

Supports all 14 atomic chart types:
- Basic: line, bar_vertical, bar_horizontal, pie, doughnut
- Correlation: scatter, bubble
- Radial: polar_area, radar
- Time Series: area, area_stacked
- Comparison: bar_grouped, bar_stacked
- Financial: waterfall

v7.5.40 Fix:
- Added element_id parameter to preserve chart data edits across regeneration
"""

import os
import httpx
from typing import Optional, List, Any
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

ANALYTICS_SERVICE_URL = os.getenv(
    "ANALYTICS_API_URL",
    "https://analytics-v30-production.up.railway.app"
)

VALID_CHART_TYPES = [
    "line", "bar_vertical", "bar_horizontal", "pie", "doughnut",
    "scatter", "bubble", "polar_area", "radar", "area",
    "area_stacked", "bar_grouped", "bar_stacked", "waterfall"
]

# Multi-series chart types that support series_names parameter
MULTI_SERIES_TYPES = ["area_stacked", "bar_grouped", "bar_stacked"]


class ChartResponse(BaseModel):
    """Response from chart generation."""
    success: bool
    html: Optional[str] = None
    chart_type: str
    chart_title: str = "Chart"
    insights_html: Optional[str] = None
    element_id: Optional[str] = None
    data_used: Optional[Any] = None
    generation_time_ms: Optional[int] = None
    error: Optional[str] = None
    # v3.8.1: Grid position returned by analytics service
    grid_position: Optional[dict] = None  # {start_col, start_row, width, height, grid_row, grid_column}


class ChartClient:
    """
    HTTP client for Analytics Service atomic chart endpoints.

    Usage:
        client = ChartClient()
        response = await client.generate(
            chart_type="line",
            narrative="Show quarterly revenue growth",
            presentation_id="pres-123",
            slide_id="slide-1"
        )
        if response.success:
            html = response.html
    """

    def __init__(self, base_url: str = None):
        """
        Initialize chart client.

        Args:
            base_url: Analytics service URL (defaults to ANALYTICS_SERVICE_URL env var)
        """
        self.base_url = base_url or ANALYTICS_SERVICE_URL
        logger.info(f"[ChartClient] Initialized with base URL: {self.base_url}")

    async def generate(
        self,
        chart_type: str,
        narrative: str,
        presentation_id: str,
        slide_id: str,
        chart_index: int = 0,
        include_insights: bool = False,
        series_names: Optional[List[str]] = None,
        width: int = 850,
        height: int = 500,
        enable_editor: bool = True,
        # v7.5.40 Fix: Preserve element_id on chart regeneration
        element_id: Optional[str] = None,
        # v3.8.1: Grid position parameters (optional)
        start_col: Optional[int] = None,
        start_row: Optional[int] = None,
        position_width: Optional[int] = None,
        position_height: Optional[int] = None
    ) -> ChartResponse:
        """
        Generate a chart via Analytics Service atomic endpoint.

        Args:
            chart_type: One of 14 valid chart types
            narrative: Text description to guide data generation
            presentation_id: Unique presentation identifier
            slide_id: Unique slide identifier for deterministic chart IDs
            chart_index: Chart index within slide (default 0)
            include_insights: Whether to generate Key Insights panel
            series_names: Custom series names for multi-series charts
            width: Chart width in pixels (default 850)
            height: Chart height in pixels (default 500)
            enable_editor: Enable interactive spreadsheet editor
            element_id: Existing element_id to preserve (for chart updates/regeneration).
                       Pass this when updating an existing chart to preserve data edits.
            start_col: Starting column position (1-32) for grid placement
            start_row: Starting row position (1-18) for grid placement
            position_width: Width in grid units (4-32), overrides pixel width
            position_height: Height in grid units (4-18), overrides pixel height

        Returns:
            ChartResponse with success status and HTML content
        """
        # Validate chart type
        if chart_type not in VALID_CHART_TYPES:
            logger.error(f"[ChartClient] Invalid chart type: {chart_type}")
            return ChartResponse(
                success=False,
                chart_type=chart_type,
                error=f"Invalid chart type: {chart_type}. Valid types: {', '.join(VALID_CHART_TYPES)}"
            )

        # Build endpoint URL
        url = f"{self.base_url}/api/v1/charts/atomic/{chart_type}"

        # Build payload
        payload = {
            "presentation_id": presentation_id,
            "slide_id": slide_id,
            "chart_index": chart_index,
            "narrative": narrative,
            "include_insights": include_insights,
            "width": width,
            "height": height,
            "enable_editor": enable_editor
        }

        # v7.5.40 Fix: Pass element_id to preserve chart data edits
        if element_id:
            payload["element_id"] = element_id
            logger.info(f"[ChartClient] Passing element_id for persistence: {element_id}")

        # Add series_names for multi-series chart types
        if series_names and chart_type in MULTI_SERIES_TYPES:
            payload["series_names"] = series_names

        # v3.8.1: Add grid position parameters if specified
        if start_col is not None:
            payload["start_col"] = start_col
        if start_row is not None:
            payload["start_row"] = start_row
        if position_width is not None:
            payload["position_width"] = position_width
        if position_height is not None:
            payload["position_height"] = position_height

        logger.info(f"[ChartClient] Generating {chart_type} chart: {narrative[:50]}...")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)

                if response.status_code != 200:
                    error_msg = f"Analytics service error: HTTP {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("detail", {}).get("message", error_msg)
                    except Exception:
                        pass

                    logger.error(f"[ChartClient] {error_msg}")
                    return ChartResponse(
                        success=False,
                        chart_type=chart_type,
                        error=error_msg
                    )

                data = response.json()

                if not data.get("success"):
                    error_msg = data.get("error", "Chart generation failed")
                    logger.error(f"[ChartClient] {error_msg}")
                    return ChartResponse(
                        success=False,
                        chart_type=chart_type,
                        error=error_msg
                    )

                # v3.8.1: Log grid_position if returned
                grid_pos = data.get("grid_position")
                if grid_pos:
                    logger.info(f"[ChartClient] Grid position: {grid_pos}")

                logger.info(f"[ChartClient] Successfully generated {chart_type} chart: {data.get('chart_title', 'Chart')}")

                return ChartResponse(
                    success=True,
                    html=data.get("chart_html"),
                    chart_type=chart_type,
                    chart_title=data.get("chart_title", "Chart"),
                    insights_html=data.get("insights_html"),
                    element_id=data.get("element_id"),
                    data_used=data.get("data_used"),
                    generation_time_ms=data.get("generation_time_ms"),
                    grid_position=grid_pos  # v3.8.1: Include grid position from analytics service
                )

        except httpx.TimeoutException:
            logger.error(f"[ChartClient] Timeout calling Analytics Service")
            return ChartResponse(
                success=False,
                chart_type=chart_type,
                error="Analytics service timeout - please try again"
            )
        except httpx.RequestError as e:
            logger.error(f"[ChartClient] Network error: {e}")
            return ChartResponse(
                success=False,
                chart_type=chart_type,
                error=f"Network error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"[ChartClient] Unexpected error: {e}")
            return ChartResponse(
                success=False,
                chart_type=chart_type,
                error=f"Unexpected error: {str(e)}"
            )

    async def get_catalog(self) -> dict:
        """
        Get list of available chart types from Analytics Service.

        Returns:
            Dictionary with count and chart_types list
        """
        url = f"{self.base_url}/api/v1/charts/atomic/catalog"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "count": len(VALID_CHART_TYPES),
                        "chart_types": VALID_CHART_TYPES,
                        "source": "fallback"
                    }
        except Exception as e:
            logger.warning(f"[ChartClient] Catalog fetch failed, using fallback: {e}")
            return {
                "count": len(VALID_CHART_TYPES),
                "chart_types": VALID_CHART_TYPES,
                "source": "fallback"
            }

    async def health_check(self) -> bool:
        """
        Check if Analytics Service is available.

        Returns:
            True if service is healthy, False otherwise
        """
        url = f"{self.base_url}/health"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception:
            return False
