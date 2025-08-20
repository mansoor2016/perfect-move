from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import search, properties, users
from app.core.config import settings

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

@app.get("/")
async def root():
    return {"message": "Advanced Property Search API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}