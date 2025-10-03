"""
FastAPI application for MCP Core.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uvicorn

from .endpoints import jobs_router, artifacts_router, health_router
from ..utils.logger import setup_logging

# Setup logging
setup_logging()

logger = logging.getLogger("mcp_api")

# Create FastAPI application
app = FastAPI(
    title="MCP Orchestrator",
    description="Microservice Control Platform - Central orchestrator for ML experiments and backtests",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": "internal_error"}
    )


# Include routers
app.include_router(health_router)
app.include_router(jobs_router)
app.include_router(artifacts_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "MCP Orchestrator",
        "version": "1.0.0",
        "description": "Central orchestrator for ML experiments and backtests",
        "endpoints": {
            "health": "/health",
            "jobs": "/jobs",
            "artifacts": "/artifacts",
            "docs": "/docs"
        }
    }


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """
    Run the FastAPI server.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload for development
    """
    logger.info(f"Starting MCP Orchestrator server on {host}:{port}")
    uvicorn.run(
        "mcp_core.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    run_server(reload=True)
