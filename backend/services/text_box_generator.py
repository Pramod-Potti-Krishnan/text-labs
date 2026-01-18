"""
Text Box HTML Generator
=======================

Generates HTML for text boxes based on TextBoxConfig.
Unified generator that replaces 7 separate component generators.
"""

import logging
from typing import List, Optional
from ..models.text_box_models import (
    TextBoxConfig,
    LayoutDirection,
    BackgroundStyle,
    CornerStyle,
    TitleStyle,
    ListStyle,
    ColorScheme,
    TextAlign
)

logger = logging.getLogger(__name__)


# Color palettes for different schemes
GRADIENT_COLORS = [
    "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",  # Purple
    "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",  # Pink
    "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",  # Cyan
    "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)",  # Green
    "linear-gradient(135deg, #fa709a 0%, #fee140 100%)",  # Orange-Pink
    "linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)",  # Pastel
]

SOLID_COLORS = [
    "#3b82f6",  # Blue
    "#10b981",  # Green
    "#f59e0b",  # Orange
    "#ef4444",  # Red
    "#8b5cf6",  # Purple
    "#06b6d4",  # Cyan
]

ACCENT_COLORS = [
    "#667eea",  # Purple
    "#f5576c",  # Pink
    "#4facfe",  # Cyan
    "#43e97b",  # Green
    "#fa709a",  # Rose
    "#fed6e3",  # Blush
]


class TextBoxGenerator:
    """Generates HTML for text boxes based on configuration."""

    def __init__(self):
        self.gradients = GRADIENT_COLORS
        self.solids = SOLID_COLORS
        self.accents = ACCENT_COLORS

    def generate(
        self,
        config: TextBoxConfig,
        items: List[str],
        titles: Optional[List[str]] = None
    ) -> str:
        """
        Generate HTML for configured text boxes.

        Args:
            config: TextBoxConfig with all styling options
            items: List of content items (distributed across boxes)
            titles: Optional list of titles (one per box)

        Returns:
            Complete HTML string ready for insertion
        """
        logger.info(f"[TEXT-BOX] Generating {config.count} boxes with config: {config}")

        # Distribute items across boxes
        items_per_box = self._distribute_items(items, config.count, config.items_per_box)

        # Generate titles if not provided
        if titles is None or len(titles) < config.count:
            titles = self._generate_default_titles(config.count, titles)

        # Generate each box
        boxes_html = []
        for i in range(config.count):
            box_items = items_per_box[i] if i < len(items_per_box) else []
            box_title = titles[i] if i < len(titles) else f"Section {i + 1}"

            box_html = self._render_box(
                index=i,
                title=box_title,
                items=box_items,
                config=config
            )
            boxes_html.append(box_html)

        # Wrap in layout container
        return self._wrap_with_layout(boxes_html, config)

    def _distribute_items(
        self,
        items: List[str],
        box_count: int,
        items_per_box: int
    ) -> List[List[str]]:
        """Distribute items evenly across boxes."""
        if not items:
            # Generate placeholder items
            items = [f"Item {i + 1}" for i in range(box_count * items_per_box)]

        result = []
        items_iter = iter(items)

        for _ in range(box_count):
            box_items = []
            for _ in range(items_per_box):
                try:
                    box_items.append(next(items_iter))
                except StopIteration:
                    break
            result.append(box_items)

        return result

    def _generate_default_titles(
        self,
        count: int,
        existing: Optional[List[str]] = None
    ) -> List[str]:
        """Generate default titles for boxes."""
        default_titles = [
            "Overview", "Features", "Benefits", "Process",
            "Details", "Summary"
        ]

        if existing:
            titles = list(existing)
        else:
            titles = []

        while len(titles) < count:
            idx = len(titles) % len(default_titles)
            titles.append(default_titles[idx])

        return titles[:count]

    def _render_box(
        self,
        index: int,
        title: str,
        items: List[str],
        config: TextBoxConfig
    ) -> str:
        """Render a single text box with all configured styles."""
        styles = self._compute_styles(config, index)

        # Start container
        html = f'<div style="{styles["container"]}">'

        # Add title if enabled
        if config.show_title and title:
            html += self._render_title(title, config, styles)

        # Add list items
        if items and config.list_style != ListStyle.NONE:
            html += self._render_list(items, config, styles)
        elif items:
            # No list style - render as paragraphs
            html += self._render_paragraphs(items, styles)

        html += '</div>'
        return html

    def _render_title(
        self,
        title: str,
        config: TextBoxConfig,
        styles: dict
    ) -> str:
        """Render title based on title_style."""
        if config.title_style == TitleStyle.COLORED_BG:
            # Title in a colored badge
            return f'''
            <div style="{styles["title_container"]}">
                <span style="{styles["title_badge"]}">{title}</span>
            </div>
            '''
        else:
            return f'<h3 style="{styles["title"]}">{title}</h3>'

    def _render_list(
        self,
        items: List[str],
        config: TextBoxConfig,
        styles: dict
    ) -> str:
        """Render list with bullets or numbers."""
        tag = "ol" if config.list_style == ListStyle.NUMBERS else "ul"
        html = f'<{tag} style="{styles["list"]}">'

        for item in items:
            html += f'<li style="{styles["list_item"]}">{item}</li>'

        html += f'</{tag}>'
        return html

    def _render_paragraphs(
        self,
        items: List[str],
        styles: dict
    ) -> str:
        """Render items as paragraphs (no bullets/numbers)."""
        html = '<div style="margin-top: 12px;">'
        for item in items:
            html += f'<p style="{styles["paragraph"]}">{item}</p>'
        html += '</div>'
        return html

    def _compute_styles(self, config: TextBoxConfig, index: int) -> dict:
        """Compute all CSS styles based on config."""
        styles = {}

        # Get text alignment value (handle both enum and string due to use_enum_values=True)
        if hasattr(config, 'text_align') and config.text_align:
            align = config.text_align.value if hasattr(config.text_align, 'value') else config.text_align
        else:
            align = "left"

        # ===== Container Styles =====
        container = [
            "padding: 24px",
            "display: flex",
            "flex-direction: column",
            f"text-align: {align}",  # Text alignment
        ]

        # Background
        if config.background == BackgroundStyle.COLORED:
            if config.color_scheme == ColorScheme.GRADIENT:
                container.append(f"background: {self.gradients[index % len(self.gradients)]}")
            elif config.color_scheme == ColorScheme.SOLID:
                container.append(f"background: {self.solids[index % len(self.solids)]}")
            else:  # ACCENT_ONLY
                container.append("background: #ffffff")
        else:
            container.append("background: transparent")

        # Border
        if config.border:
            container.append("border: 2px solid #e5e7eb")
        else:
            container.append("border: none")

        # Corners
        if config.corners == CornerStyle.ROUNDED:
            container.append("border-radius: 16px")
        else:
            container.append("border-radius: 0")

        # Shadow for colored backgrounds
        if config.background == BackgroundStyle.COLORED:
            container.append("box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1)")

        styles["container"] = "; ".join(container)

        # ===== Title Styles =====
        is_dark_bg = (
            config.background == BackgroundStyle.COLORED and
            config.color_scheme in [ColorScheme.GRADIENT, ColorScheme.SOLID]
        )
        text_color = "white" if is_dark_bg else "#1f2937"

        title_styles = [
            f"color: {text_color}",
            "margin: 0 0 16px 0",
            "font-weight: 700",
        ]

        if config.title_style == TitleStyle.HIGHLIGHTED:
            title_styles.append("font-size: 24px")
            title_styles.append("text-transform: uppercase")
            title_styles.append("letter-spacing: 0.5px")
        else:
            title_styles.append("font-size: 20px")

        styles["title"] = "; ".join(title_styles)

        # Title badge styles (for COLORED_BG title style)
        styles["title_container"] = "margin-bottom: 16px;"
        accent = self.accents[index % len(self.accents)]
        styles["title_badge"] = f"""
            display: inline-block;
            padding: 6px 16px;
            background: {accent};
            color: white;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        """.replace("\n", " ").strip()

        # ===== List Styles =====
        # Adjust padding based on alignment
        list_padding = "20px" if align == "left" else "0"
        list_styles = [
            "margin: 0",
            f"padding-left: {list_padding}",
            f"text-align: {align}",
        ]

        if config.list_style == ListStyle.BULLETS:
            list_styles.append("list-style-type: disc")
            if align != "left":
                list_styles.append("list-style-position: inside")  # Keep bullets visible when centered
        elif config.list_style == ListStyle.NUMBERS:
            list_styles.append("list-style-type: decimal")
            if align != "left":
                list_styles.append("list-style-position: inside")  # Keep numbers visible when centered

        styles["list"] = "; ".join(list_styles)

        # ===== List Item Styles =====
        item_styles = [
            f"color: {text_color if is_dark_bg else '#4b5563'}",
            "font-size: 16px",
            "line-height: 1.6",
            "margin-bottom: 8px",
        ]

        if is_dark_bg:
            item_styles.append("opacity: 0.95")

        styles["list_item"] = "; ".join(item_styles)

        # ===== Paragraph Styles (for list_style=NONE) =====
        styles["paragraph"] = f"""
            color: {text_color if is_dark_bg else '#4b5563'};
            font-size: 16px;
            line-height: 1.6;
            margin: 0 0 12px 0;
        """.replace("\n", " ").strip()

        return styles

    def _wrap_with_layout(
        self,
        boxes: List[str],
        config: TextBoxConfig
    ) -> str:
        """Wrap boxes in layout container."""
        boxes_html = "".join(boxes)

        if config.layout == LayoutDirection.HORIZONTAL:
            # Side by side
            cols = len(boxes)
            return f'''
            <div style="display: grid; grid-template-columns: repeat({cols}, 1fr); gap: 24px; padding: 0 40px 0 0; align-items: start;">
                {boxes_html}
            </div>
            '''

        elif config.layout == LayoutDirection.VERTICAL:
            # Stacked vertically
            return f'''
            <div style="display: flex; flex-direction: column; gap: 24px; padding: 0 40px 0 0;">
                {boxes_html}
            </div>
            '''

        else:  # GRID - 2 columns
            return f'''
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; padding: 0 40px 0 0; align-items: start;">
                {boxes_html}
            </div>
            '''


# Singleton instance
_generator = None


def get_text_box_generator() -> TextBoxGenerator:
    """Get singleton TextBoxGenerator instance."""
    global _generator
    if _generator is None:
        _generator = TextBoxGenerator()
    return _generator


def generate_text_box_html(
    config: TextBoxConfig,
    items: List[str],
    titles: Optional[List[str]] = None
) -> str:
    """
    Convenience function to generate text box HTML.

    Args:
        config: TextBoxConfig with all styling options
        items: List of content items
        titles: Optional list of titles

    Returns:
        HTML string
    """
    generator = get_text_box_generator()
    return generator.generate(config, items, titles)
