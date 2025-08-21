from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import search, properties, users
from app.core.config import settings
from app.core.elasticsearch import es_client
from app.modules.search.elasticsearch_service import elasticsearch_service
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Advanced Property Search API",
    description="API for advanced property search with lifestyle-based filters",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(properties.router, prefix="/api/v1/properties", tags=["properties"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        # Initialize Elasticsearch connection
        await es_client.connect()
        
        # Create properties index if it doesn't exist
        await elasticsearch_service.create_properties_index()
        
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        await es_client.disconnect()
        logger.info("Application shutdown completed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

@app.get("/")
async def root():
    return {"message": "Advanced Property Search API"}

@app.get("/health")
async def health_check():
    """Health check endpoint that verifies all services"""
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    try:
        # Check Elasticsearch
        es_healthy = await es_client.health_check()
        health_status["services"]["elasticsearch"] = "healthy" if es_healthy else "unhealthy"
        
        if not es_healthy:
            health_status["status"] = "degraded"
            
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
    
    return health_status