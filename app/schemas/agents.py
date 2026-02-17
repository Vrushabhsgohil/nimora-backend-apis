from typing import List, Optional
from pydantic import BaseModel, Field

# Concept Agent Schemas
class ConceptOutput(BaseModel):
    title: str = Field(..., description="Title of the cinematic concept")
    storytelling_concept: str = Field(..., description="The narrative arc and emotional tone of the video")
    aesthetic_direction: str = Field(..., description="Visual style, color palette, and mood")
    lighting_mood: str = Field(..., description="Description of lighting setup (e.g., soft, dramatic, golden hour)")
    product_focus_strategy: str = Field(..., description="How the jewellery pieces will be highlighted")
    narrative_flow: str = Field(..., description="Step-by-step flow of the 5-second commercial")

# Visual Director Agent Schemas
class SceneDetail(BaseModel):
    sequence_number: int
    description: str = Field(..., description="Detailed visual description of the scene")
    camera_angle: str = Field(..., description="Camera angle (e.g., macro, wide, panning)")
    camera_movement: str = Field(..., description="Movement description (e.g., slow zoom in, dolly track)")
    lighting_setup: str = Field(..., description="Specific lighting for this shot")
    focus_points: List[str] = Field(..., description="Specific details to focus on (e.g., diamond cut, metal texture)")
    duration_estimate: float = Field(..., description="Estimated duration in seconds")

class VisualDirectorOutput(BaseModel):
    visual_style_summary: str = Field(..., description="Overall visual cohesion plan")
    scenes: List[SceneDetail] = Field(..., description="Scene-by-scene breakdown")
    technical_notes: str = Field(..., description="Notes on reflection, texture, and stone physics")

# Prompt Refinement Agent Schemas
class PromptRefinementOutput(BaseModel):
    final_prompt: str = Field(..., description="The optimized prompt for the video generation model")
    individual_prompts: List[str] = Field(default_factory=list, description="A breakdown of prompts for each individual scene or segment")
    rationale: str = Field(..., description="Explanation of why this prompt structure was chosen")
    negative_prompt: Optional[str] = Field(None, description="Elements to avoid")

# QA Agent Schemas
class QAAgentOutput(BaseModel):
    score: float = Field(..., description="Quality score out of 10")
    feedback: str = Field(..., description="Detailed feedback on the prompt quality and alignment")
    critique_points: List[str] = Field(..., description="Specific points of critique")
    approved: bool = Field(..., description="True if score >= 9.0")

class GenerationOutput(BaseModel):
    video_url: str = Field(..., description="URL of the generated video")
    generation_id: str = Field(..., description="ID of the generation task")
    status: str = Field(..., description="Status of the generation (e.g., success, failed)")

# Image Analysis Agent Schemas
class ImageAnalysisOutput(BaseModel):
    jewellery_type: str = Field(..., description="Type of jewellery identified")
    materials: str = Field(..., description="Metal and finish details")
    gemstones: str = Field(..., description="Stone details, cuts, and settings")
    design_style: str = Field(..., description="Aesthetic style (Modern, Vintage, etc.)")
    detailed_features: str = Field(..., description="Engravings, filigree, structural elements")
    color_palette: str = Field(..., description="Dominant colors")
    visual_context_summary: str = Field(..., description="A concise paragraph summarizing the visual appearance for prompting")

class ContinuityControlOutput(BaseModel):
    score: float = Field(..., description="Compliance score out of 10. Must be 10.0 for approval.")
    feedback: str = Field(..., description="Detailed feedback on specific violations of strict rules.")
    violation_type: Optional[str] = Field(None, description="Type of violation (e.g., 'Product Change', 'Artificial Effect', 'Model Issue'). None if approved.")
    approved: bool = Field(False, description="True only if score is 10.0")
