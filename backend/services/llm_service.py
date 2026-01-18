"""
LLM Service for Text Labs
==========================

Gemini text and vision integration for intent parsing and layout evaluation.
"""

import os
import logging
import base64
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Try to import Vertex AI
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
    VERTEXAI_AVAILABLE = True
except ImportError:
    VERTEXAI_AVAILABLE = False
    logger.warning("vertexai not available, LLM features will be limited")


class LLMConfig(BaseModel):
    """Configuration for LLM service."""
    project_id: str = "deckster-xyz"
    location: str = "us-central1"
    text_model: str = "gemini-2.0-flash-001"
    vision_model: str = "gemini-2.0-flash-001"
    temperature: float = 0.7
    max_output_tokens: int = 2048


class LLMResponse(BaseModel):
    """Response from LLM."""
    success: bool
    content: str = ""
    error: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


class LLMService:
    """
    Service for Gemini text and vision operations.

    Used for:
    - Intent parsing from user messages
    - Layout evaluation with screenshots
    - Content suggestions and refinement
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._initialized = False
        self._text_model: Optional[GenerativeModel] = None
        self._vision_model: Optional[GenerativeModel] = None

    def _initialize(self) -> bool:
        """Initialize Vertex AI and models."""
        if self._initialized:
            return True

        if not VERTEXAI_AVAILABLE:
            logger.error("[LLM-SERVICE] vertexai not installed")
            return False

        try:
            # Initialize Vertex AI
            vertexai.init(
                project=self.config.project_id,
                location=self.config.location
            )

            # Initialize models
            self._text_model = GenerativeModel(self.config.text_model)
            self._vision_model = GenerativeModel(self.config.vision_model)

            self._initialized = True
            logger.info(f"[LLM-SERVICE] Initialized with project={self.config.project_id}")
            return True

        except Exception as e:
            logger.error(f"[LLM-SERVICE] Initialization failed: {e}")
            return False

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> LLMResponse:
        """
        Generate text response from Gemini.

        Args:
            prompt: User prompt
            system_instruction: Optional system context
            temperature: Override default temperature

        Returns:
            LLMResponse with generated content
        """
        if not self._initialize():
            return LLMResponse(
                success=False,
                error="LLM service not initialized"
            )

        try:
            # Build generation config
            gen_config = GenerationConfig(
                temperature=temperature or self.config.temperature,
                max_output_tokens=self.config.max_output_tokens,
            )

            # Add system instruction if provided
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"{system_instruction}\n\n{prompt}"

            # Generate response
            response = self._text_model.generate_content(
                full_prompt,
                generation_config=gen_config
            )

            content = response.text if response.text else ""

            logger.info(f"[LLM-SERVICE] Generated text, length={len(content)}")

            return LLMResponse(
                success=True,
                content=content
            )

        except Exception as e:
            logger.error(f"[LLM-SERVICE] Text generation failed: {e}")
            return LLMResponse(
                success=False,
                error=str(e)
            )

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        mime_type: str = "image/png"
    ) -> LLMResponse:
        """
        Analyze an image with Gemini Vision.

        Args:
            image_data: Raw image bytes
            prompt: Analysis prompt
            mime_type: Image MIME type

        Returns:
            LLMResponse with analysis
        """
        if not self._initialize():
            return LLMResponse(
                success=False,
                error="LLM service not initialized"
            )

        try:
            # Create image part
            image_part = Part.from_data(image_data, mime_type=mime_type)

            # Generate response with image
            response = self._vision_model.generate_content(
                [prompt, image_part],
                generation_config=GenerationConfig(
                    temperature=0.3,  # Lower temperature for analysis
                    max_output_tokens=self.config.max_output_tokens,
                )
            )

            content = response.text if response.text else ""

            logger.info(f"[LLM-SERVICE] Image analysis complete, length={len(content)}")

            return LLMResponse(
                success=True,
                content=content
            )

        except Exception as e:
            logger.error(f"[LLM-SERVICE] Image analysis failed: {e}")
            return LLMResponse(
                success=False,
                error=str(e)
            )

    async def parse_intent(self, user_message: str, context: Optional[str] = None) -> LLMResponse:
        """
        Parse user message to extract intent.

        Args:
            user_message: User's natural language input
            context: Optional conversation context

        Returns:
            LLMResponse with structured intent JSON
        """
        system_instruction = """You are an intent parser for a slide element builder.

Parse the user's message and extract:
- action: "add", "modify", "remove", "move", or "clear"
- component_type: One of "METRICS", "SEQUENTIAL", "COMPARISON", "SECTIONS", "CALLOUT", "TEXT_BULLETS", "BULLET_BOX", "TABLE", or "NUMBERED_LIST" (if applicable)
- count: number of instances (if mentioned)
- content_prompt: the content description for generation
- position_hint: "below", "right", "center", etc. (if mentioned)

Component keywords:
- METRICS: metrics, kpis, numbers, stats, statistics, data points
- SEQUENTIAL: steps, process, phases, workflow, stages, sequence, timeline
- COMPARISON: comparison, compare, vs, versus, pros cons, options, plans
- SECTIONS: sections, categories, topics, areas, pillars, points, features
- CALLOUT: callout, highlight, key points, takeaways, insights, sidebar
- TEXT_BULLETS: text bullets, bullet points, bullet list, simple bullets, features, benefits
- BULLET_BOX: bullet box, boxed bullets, bordered list, formal list, requirements
- TABLE: table, data table, grid, schedule, matrix, comparison table
- NUMBERED_LIST: numbered list, ordered list, priorities, rankings, top items, steps list

Respond with valid JSON only:
{
    "action": "add|modify|remove|move|clear",
    "component_type": "METRICS|SEQUENTIAL|COMPARISON|SECTIONS|CALLOUT|TEXT_BULLETS|BULLET_BOX|TABLE|NUMBERED_LIST|null",
    "count": <number or null>,
    "content_prompt": "<extracted content description>",
    "position_hint": "<position or null>",
    "confidence": <0.0-1.0>
}"""

        prompt = f"User message: {user_message}"
        if context:
            prompt = f"Context: {context}\n\n{prompt}"

        return await self.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.3  # Lower temperature for structured output
        )

    async def evaluate_layout(
        self,
        screenshot_data: bytes,
        current_elements: List[Dict[str, Any]],
        new_element: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Evaluate slide layout using vision.

        Args:
            screenshot_data: PNG screenshot of canvas
            current_elements: List of current element positions
            new_element: Optional newly added element

        Returns:
            LLMResponse with layout evaluation and suggestions
        """
        elements_desc = "\n".join([
            f"- {e.get('component_type')}: row {e.get('row')}, col {e.get('col')}, {e.get('width')}x{e.get('height')}"
            for e in current_elements
        ])

        prompt = f"""Evaluate this slide layout for visual quality and arrangement.

Current elements on canvas:
{elements_desc if elements_desc else "Empty canvas"}

{"New element added: " + str(new_element) if new_element else ""}

Analyze:
1. Is the layout balanced and visually appealing?
2. Are elements properly aligned?
3. Is there appropriate spacing between elements?
4. Does the arrangement support the content hierarchy?

Respond with JSON:
{{
    "is_optimal": true/false,
    "score": 0-100,
    "issues": ["list of issues found"],
    "suggestions": [
        {{"element_id": "...", "action": "move|resize", "new_row": X, "new_col": Y, "reason": "..."}}
    ]
}}"""

        return await self.analyze_image(
            image_data=screenshot_data,
            prompt=prompt,
            mime_type="image/png"
        )

    async def suggest_content(
        self,
        component_type: str,
        user_prompt: str,
        count: int
    ) -> LLMResponse:
        """
        Suggest content for component generation.

        Args:
            component_type: Type of atomic component
            user_prompt: User's content description
            count: Number of instances

        Returns:
            LLMResponse with refined content suggestions
        """
        system_instruction = f"""You are a content assistant for slide creation.

The user wants to create {count} {component_type} element(s).

Generate specific, professional content based on their description.
Make the content concise and impactful for presentation slides.

For METRICS: provide metric titles, values, and brief descriptions
For SEQUENTIAL: provide step titles and brief descriptions
For COMPARISON: provide column headers and comparison points
For SECTIONS: provide section titles and bullet points
For CALLOUT: provide callout title and key points
For TEXT_BULLETS: provide subtitle and bullet points
For BULLET_BOX: provide box heading and list items
For TABLE: provide column headers and row data
For NUMBERED_LIST: provide list title and numbered items"""

        return await self.generate_text(
            prompt=f"Create content for: {user_prompt}",
            system_instruction=system_instruction,
            temperature=0.7
        )
