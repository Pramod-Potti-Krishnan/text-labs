"""
Layout Service Client
=====================

Client for communicating with Layout Service.
"""

import logging
import ssl
import certifi
import aiohttp
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Production Layout Service URL
LAYOUT_SERVICE_URL = "https://web-production-f0d13.up.railway.app"


class SlideContent(BaseModel):
    """Content for a slide element."""
    slot_name: str
    content: str
    content_type: str = "html"  # html, text, image


class PresentationInfo(BaseModel):
    """Presentation information."""
    presentation_id: str
    slide_count: int = 1
    viewer_url: Optional[str] = None


class LayoutServiceResponse(BaseModel):
    """Response from Layout Service operations."""
    success: bool
    presentation_id: Optional[str] = None
    viewer_url: Optional[str] = None
    element_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class LayoutServiceClient:
    """Client for Layout Service API."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._session = None
        self.base_url = LAYOUT_SERVICE_URL
        logger.info(f"[LAYOUT-CLIENT] Initialized with timeout={timeout}, url={self.base_url}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            # Create SSL context using certifi for proper certificate verification
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                connector=connector
            )
        return self._session

    async def close(self):
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def get_viewer_url(self, presentation_id: str) -> str:
        """Get the viewer URL for a presentation."""
        return f"{self.base_url}/p/{presentation_id}"

    async def get_layout_suggestions(
        self,
        component_type: str,
        canvas_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get layout suggestions for component placement."""
        # Stub implementation for testing
        return {
            "success": True,
            "suggestions": [],
            "message": "Layout service stub"
        }

    async def create_presentation(
        self,
        title: str = "Text Labs Slide"
    ) -> LayoutServiceResponse:
        """Create a new presentation with C1-text layout."""
        payload = {
            "title": title,
            "template_id": "L25",
            "slides": [
                {
                    "layout": "C1-text",
                    "content": {
                        "title": title,
                        "subtitle": "",
                        "body": "",  # Empty initially
                        "logo": " "
                    }
                }
            ]
        }

        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/presentations",
                json=payload
            ) as resp:
                if resp.status == 200 or resp.status == 201:
                    data = await resp.json()
                    presentation_id = data.get("id")
                    viewer_url = f"{self.base_url}/p/{presentation_id}"
                    logger.info(f"[LAYOUT-CLIENT] Created presentation: {presentation_id}")
                    return LayoutServiceResponse(
                        success=True,
                        presentation_id=presentation_id,
                        viewer_url=viewer_url,
                        message="Presentation created"
                    )
                else:
                    error_text = await resp.text()
                    logger.error(f"[LAYOUT-CLIENT] Error creating presentation: {resp.status} - {error_text}")
                    return LayoutServiceResponse(
                        success=False,
                        error=f"Layout Service error: {resp.status} - {error_text}"
                    )
        except aiohttp.ClientError as e:
            logger.error(f"[LAYOUT-CLIENT] Connection error: {e}")
            return LayoutServiceResponse(
                success=False,
                error=f"Connection error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"[LAYOUT-CLIENT] Unexpected error: {e}")
            return LayoutServiceResponse(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    async def inject_content(
        self,
        presentation_id: str,
        slide_index: int,
        slot_name: str,
        content: str,
        content_type: str = "html"
    ) -> LayoutServiceResponse:
        """Inject content into a slide slot."""
        payload = {
            "slides": [
                {
                    "slide_index": slide_index,
                    "content": {
                        slot_name: content
                    }
                }
            ]
        }

        try:
            session = await self._get_session()
            async with session.patch(
                f"{self.base_url}/api/presentations/{presentation_id}",
                json=payload
            ) as resp:
                if resp.status == 200:
                    logger.info(f"[LAYOUT-CLIENT] Injected content into {slot_name}")
                    return LayoutServiceResponse(
                        success=True,
                        message=f"Content injected into {slot_name}"
                    )
                else:
                    error_text = await resp.text()
                    logger.error(f"[LAYOUT-CLIENT] Error injecting content: {resp.status}")
                    return LayoutServiceResponse(
                        success=False,
                        error=f"Failed to inject content: {resp.status} - {error_text}"
                    )
        except aiohttp.ClientError as e:
            logger.error(f"[LAYOUT-CLIENT] Connection error: {e}")
            return LayoutServiceResponse(
                success=False,
                error=f"Connection error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"[LAYOUT-CLIENT] Unexpected error: {e}")
            return LayoutServiceResponse(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    async def add_text_box(
        self,
        presentation_id: str,
        slide_index: int,
        content: str,
        grid_row: str = "4/18",
        grid_column: str = "2/32"
    ) -> LayoutServiceResponse:
        """Add a text box to a slide."""
        import uuid
        element_id = f"elem_{uuid.uuid4().hex[:8]}"

        # Use inject_content to add the text box to the body slot
        result = await self.inject_content(
            presentation_id=presentation_id,
            slide_index=slide_index,
            slot_name="body",
            content=content
        )

        if result.success:
            result.element_id = element_id
            result.message = "Text box added"

        return result
