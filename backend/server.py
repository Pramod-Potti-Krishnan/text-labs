"""
Text Labs Server
=================

FastAPI server for chat-based slide element builder.

Features:
- Chat interface for natural language element creation
- Canvas state management with JSON persistence
- Integration with Railway-deployed Text Service v1.2
- Gemini LLM for intent parsing and vision evaluation
"""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import services
from .services.atomic_client import AtomicClient
from .services.chart_client import ChartClient
from .services.image_client import ImageClient
from .services.llm_service import LLMService
from .services.layout_service_client import LayoutServiceClient

# Import canvas manager
from .canvas.state_manager import StateManager

# Import API routers
from .api import chat_routes, canvas_routes, element_routes


# Shared service instances
state_manager: StateManager = None
atomic_client: AtomicClient = None
chart_client: ChartClient = None
image_client: ImageClient = None
llm_service: LLMService = None
layout_service_client: LayoutServiceClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global state_manager, atomic_client, chart_client, image_client, llm_service, layout_service_client

    logger.info("[TEXT-LABS] Starting up...")

    # Initialize state manager
    sessions_dir = Path(__file__).parent.parent / "sessions"
    state_manager = StateManager(sessions_dir=sessions_dir)

    # Initialize atomic client
    atomic_client = AtomicClient(
        timeout=60.0  # 60 second timeout for API calls
    )

    # Initialize chart client (for Analytics Service atomic charts)
    chart_client = ChartClient()

    # Initialize image client (for Image Service atomic images)
    image_client = ImageClient(
        timeout=60.0  # 60 second timeout for image generation
    )

    # Initialize LLM service
    llm_service = LLMService()

    # Initialize Layout Service client
    layout_service_client = LayoutServiceClient(
        timeout=30.0  # 30 second timeout for Layout Service
    )

    # Inject into route modules
    chat_routes.state_manager = state_manager
    chat_routes.atomic_client = atomic_client
    chat_routes.chart_client = chart_client
    chat_routes.image_client = image_client
    chat_routes.llm_service = llm_service
    chat_routes.layout_service_client = layout_service_client

    canvas_routes.state_manager = state_manager
    element_routes.state_manager = state_manager

    logger.info("[TEXT-LABS] Services initialized")

    yield

    # Cleanup
    logger.info("[TEXT-LABS] Shutting down...")
    if atomic_client:
        await atomic_client.close()
    if layout_service_client:
        await layout_service_client.close()


# Create FastAPI app
app = FastAPI(
    title="Text Labs",
    description="Chat-based slide element builder with AI orchestration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(chat_routes.router)
app.include_router(canvas_routes.router)
app.include_router(element_routes.router)


# Static files (frontend)
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    # Mount CSS and JS directories
    css_dir = frontend_dir / "css"
    js_dir = frontend_dir / "js"
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
    # Also mount the whole frontend as /static for any other assets
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
async def root():
    """Serve the frontend or return API info."""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "service": "Text Labs",
        "version": "1.0.0",
        "status": "running",
        "frontend": "Frontend not found. Create frontend/index.html",
        "endpoints": {
            "chat": "/api/chat/message",
            "canvas": "/api/canvas/state/{session_id}",
            "elements": "/api/element/{session_id}/{element_id}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "text-labs",
        "atomic_api": os.getenv("ATOMIC_API_URL", "https://web-production-5daf.up.railway.app")
    }


@app.get("/api/info")
async def api_info():
    """Get API information and component types."""
    return {
        "service": "Text Labs",
        "version": "1.0.0",
        "component_types": [
            {
                "type": "METRICS",
                "description": "KPI metrics cards",
                "keywords": ["metrics", "kpis", "numbers", "stats"],
                "count_range": [2, 4],
                "default_size": {"width": 28, "height": 8}
            },
            {
                "type": "SEQUENTIAL",
                "description": "Step-by-step process",
                "keywords": ["steps", "process", "phases", "workflow"],
                "count_range": [2, 6],
                "default_size": {"width": 28, "height": 10}
            },
            {
                "type": "COMPARISON",
                "description": "Side-by-side comparison",
                "keywords": ["comparison", "compare", "vs", "options"],
                "count_range": [2, 4],
                "default_size": {"width": 28, "height": 14}
            },
            {
                "type": "SECTIONS",
                "description": "Content sections with bullets",
                "keywords": ["sections", "categories", "topics", "areas"],
                "count_range": [2, 5],
                "default_size": {"width": 24, "height": 12}
            },
            {
                "type": "CALLOUT",
                "description": "Highlight callout box",
                "keywords": ["callout", "highlight", "key points", "insights"],
                "count_range": [1, 2],
                "default_size": {"width": 10, "height": 12}
            },
            {
                "type": "TEXT_BULLETS",
                "description": "Simple text boxes with bullet points",
                "keywords": ["text bullets", "bullet points", "features", "benefits"],
                "count_range": [1, 4],
                "default_size": {"width": 24, "height": 10}
            },
            {
                "type": "BULLET_BOX",
                "description": "Bordered rectangular boxes with bullets",
                "keywords": ["bullet box", "bordered list", "formal list", "requirements"],
                "count_range": [1, 4],
                "default_size": {"width": 24, "height": 12}
            },
            {
                "type": "TABLE",
                "description": "HTML data tables",
                "keywords": ["table", "data table", "grid", "matrix"],
                "count_range": [1, 2],
                "default_size": {"width": 28, "height": 10}
            },
            {
                "type": "NUMBERED_LIST",
                "description": "Ordered numbered lists",
                "keywords": ["numbered list", "ordered list", "priorities", "rankings"],
                "count_range": [1, 4],
                "default_size": {"width": 24, "height": 12}
            }
        ],
        "grid": {
            "columns": 32,
            "rows": 18,
            "cell_size_px": 60,
            "content_area": {
                "start_row": 4,
                "end_row": 18,
                "start_col": 2,
                "end_col": 32
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )
