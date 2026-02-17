from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.api import api_router

# Setup logging
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "Niroma Backend APIs - Jewellery Video Generation Service"}
