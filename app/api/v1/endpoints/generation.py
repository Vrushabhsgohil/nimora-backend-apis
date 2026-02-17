from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.schemas.generation import GenerationRequest, GenerationResponse
from app.services.orchestrator import VideoOrchestrator
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.post("/generate", response_model=GenerationResponse)
async def generate_video(request: GenerationRequest):
    """
    Generate a 5-second cinematic jewellery video based on the product description and image.
    """
    logger.info(f"Received video generation request for: {request.jewellery_type} - {request.product_description[:50]}...")
    
    try:
        orchestrator = VideoOrchestrator()
        result = await orchestrator.process_request(request)
        return result
    except Exception as e:
        logger.error(f"Error processing generation request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
