"""
Image Client for Text Labs
===========================

HTTP client for calling Image Service atomic image endpoints.

Supports AI-generated images with configurable:
- Style: realistic, illustration, corporate, abstract, minimalist
- Quality: draft, standard, high, ultra
- Position: grid-based positioning on slides
"""

import os
import httpx
from typing import Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

IMAGE_SERVICE_URL = os.getenv(
    "IMAGE_API_URL",
    "https://web-production-1b5df.up.railway.app"
)

VALID_STYLES = ["realistic", "illustration", "corporate", "abstract", "minimalist"]
VALID_QUALITIES = ["draft", "standard", "high", "ultra"]


class ImageResponse(BaseModel):
    """Response from image generation."""
    success: bool
    image_url: Optional[str] = None
    html: Optional[str] = None
    element_id: Optional[str] = None
    style: str = "realistic"
    quality: str = "standard"
    generation_time_ms: Optional[int] = None
    error: Optional[str] = None


class ImageClient:
    """
    HTTP client for Image Service atomic image endpoints.

    Usage:
        client = ImageClient()
        response = await client.generate(
            prompt="Modern office with team collaboration",
            presentation_id="pres-123",
            slide_id="slide-1",
            style="realistic",
            quality="standard"
        )
        if response.success:
            html = response.html
            image_url = response.image_url
    """

    def __init__(self, base_url: str = None, timeout: float = 60.0):
        """
        Initialize image client.

        Args:
            base_url: Image service URL (defaults to IMAGE_SERVICE_URL env var)
            timeout: Request timeout in seconds (default 60s for image generation)
        """
        self.base_url = base_url or IMAGE_SERVICE_URL
        self.timeout = timeout
        logger.info(f"[ImageClient] Initialized with base URL: {self.base_url}")

    async def generate(
        self,
        prompt: str,
        presentation_id: str,
        slide_id: str,
        style: str = "realistic",
        quality: str = "standard",
        grid_row: Optional[str] = None,
        grid_column: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        placeholder_mode: bool = False
    ) -> ImageResponse:
        """
        Generate an image via Image Service atomic endpoint.

        Args:
            prompt: Text description to generate image from
            presentation_id: Unique presentation identifier
            slide_id: Unique slide identifier
            style: One of realistic, illustration, corporate, abstract, minimalist
            quality: One of draft, standard, high, ultra
            grid_row: CSS grid row position (e.g., "4/14")
            grid_column: CSS grid column position (e.g., "2/18")
            aspect_ratio: Override aspect ratio (e.g., "16:9", "4:3", "1:1")
            placeholder_mode: If True, use placeholder instead of AI generation

        Returns:
            ImageResponse with success status and image URL/HTML
        """
        # Validate style
        if style not in VALID_STYLES:
            logger.warning(f"[ImageClient] Invalid style '{style}', defaulting to 'realistic'")
            style = "realistic"

        # Validate quality
        if quality not in VALID_QUALITIES:
            logger.warning(f"[ImageClient] Invalid quality '{quality}', defaulting to 'standard'")
            quality = "standard"

        # Build endpoint URL
        url = f"{self.base_url}/api/v1/images/atomic/generate"

        # Build payload
        payload = {
            "prompt": prompt,
            "presentation_id": presentation_id,
            "slide_id": slide_id,
            "placeholder_mode": placeholder_mode,
            "config": {
                "style": style,
                "quality": quality
            }
        }

        # Add optional position parameters
        if grid_row:
            payload["grid_row"] = grid_row
        if grid_column:
            payload["grid_column"] = grid_column
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio

        logger.info(f"[ImageClient] Generating image: {prompt[:50]}... (style={style}, quality={quality})")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)

                if response.status_code != 200:
                    error_msg = f"Image service error: HTTP {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("detail", {}).get("message", error_msg)
                        if isinstance(error_data.get("detail"), str):
                            error_msg = error_data.get("detail")
                    except Exception:
                        pass

                    logger.error(f"[ImageClient] {error_msg}")
                    return ImageResponse(
                        success=False,
                        style=style,
                        quality=quality,
                        error=error_msg
                    )

                data = response.json()

                if not data.get("success", True):
                    error_msg = data.get("error", "Image generation failed")
                    logger.error(f"[ImageClient] {error_msg}")
                    return ImageResponse(
                        success=False,
                        style=style,
                        quality=quality,
                        error=error_msg
                    )

                image_url = data.get("image_url")
                element_id = data.get("element_id")

                # Use HTML from service response if available, otherwise build locally (backward compat)
                html = data.get("html")
                if not html:
                    html = self._build_image_html(image_url, element_id, grid_row, grid_column)

                logger.info(f"[ImageClient] Successfully generated image: {element_id}")

                return ImageResponse(
                    success=True,
                    image_url=image_url,
                    html=html,
                    element_id=element_id,
                    style=style,
                    quality=quality,
                    generation_time_ms=data.get("generation_time_ms")
                )

        except httpx.TimeoutException:
            logger.error("[ImageClient] Timeout calling Image Service")
            return ImageResponse(
                success=False,
                style=style,
                quality=quality,
                error="Image service timeout - please try again"
            )
        except httpx.RequestError as e:
            logger.error(f"[ImageClient] Network error: {e}")
            return ImageResponse(
                success=False,
                style=style,
                quality=quality,
                error=f"Network error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"[ImageClient] Unexpected error: {e}")
            return ImageResponse(
                success=False,
                style=style,
                quality=quality,
                error=f"Unexpected error: {str(e)}"
            )

    def _build_image_html(
        self,
        image_url: str,
        element_id: str,
        grid_row: Optional[str] = None,
        grid_column: Optional[str] = None
    ) -> str:
        """
        Build HTML wrapper for the image.

        Args:
            image_url: URL of the generated image
            element_id: Unique element identifier
            grid_row: CSS grid row position
            grid_column: CSS grid column position

        Returns:
            HTML string for the image element
        """
        # Build inline style for positioning
        style_parts = [
            "width: 100%",
            "height: 100%",
            "object-fit: cover",
            "display: block"
        ]

        return f'''<div class="image-element" data-element-id="{element_id}" style="width: 100%; height: 100%; position: relative; overflow: hidden;">
    <img
        src="{image_url}"
        alt="AI-generated image"
        style="{'; '.join(style_parts)}"
        loading="lazy"
    />
</div>'''

    async def health_check(self) -> bool:
        """
        Check if Image Service is available.

        Returns:
            True if service is healthy, False otherwise
        """
        url = f"{self.base_url}/api/v1/images/atomic/health"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception:
            return False
