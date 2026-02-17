from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class GenerationRequest(BaseModel):
    product_description: Optional[str] = Field(None, description="Detailed description of the product (Optional)")
    jewellery_type: str = Field(..., description="Type of jewellery (ring, necklace, etc.)")
    gender: str = Field(..., description="Target gender (male | female)")
    video_type: str = Field(..., description="Video type (ecommerce | ugc)")
    duration: int = Field(..., description="Duration in seconds (8 | 12)")
    base64_image: str = Field(..., description="Base64 encoded image string")
    is_music: bool = Field(..., description="Generate background music")
    is_model: bool = Field(..., description="Include a model in the video")
    model_consistency: bool = Field(True, description="Ensure human model features remain consistent")
    reference_video_path: Optional[str] = Field(None, description="Path to a reference video to maintain style or context")

class GenerationResponse(BaseModel):
    video_url: str = Field(..., description="The final video URL")
    generation_id: str
    status: str
    concept: Dict = Field(..., description="The generated concept")
    visual_plan: Dict = Field(..., description="The visual director's plan")
    final_prompt: str = Field(..., description="The final combined prompt used")
    individual_prompts: List[str] = Field(default_factory=list, description="List of individual prompts for each scene")
    qa_score: float = Field(..., description="Final QA score")
    feedback_iterations: int = Field(..., description="Number of refinement loops")
