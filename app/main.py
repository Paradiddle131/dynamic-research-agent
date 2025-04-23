import logging
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.endpoints import research

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="0.1.0"
)

app.include_router(
    research.router,
    prefix=settings.API_V1_STR + "/research",
    tags=["Research"]
)

@app.get("/", tags=["Root"])
async def read_root():
    """Root endpoint for the API."""
    logger.info("Root endpoint '/' accessed.")
    return {"message": f"Welcome to the {settings.PROJECT_NAME}!"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server with Uvicorn directly...")
    uvicorn.run(app, host=settings.SERVER_HOST, port=settings.SERVER_PORT)
