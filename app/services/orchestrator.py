import os
import json
import aiofiles
import httpx
from typing import Dict, Any, Optional
from app.core.logging import get_logger
from app.agents.concept_agent import ConceptAgent
from app.agents.visual_director_agent import VisualDirectorAgent
from app.agents.prompt_refinement_agent import PromptRefinementAgent
from app.agents.qa_agent import QAAgent
from app.agents.continuity_agent import ContinuityControlAgent
from app.agents.generation_agent import GenerationAgent
from app.agents.image_analysis_agent import ImageAnalysisAgent
from app.schemas.generation import GenerationRequest, GenerationResponse
from app.schemas.agents import ImageAnalysisOutput

logger = get_logger(__name__)

class VideoOrchestrator:
    def __init__(self):
        self.image_analysis_agent = ImageAnalysisAgent()
        self.concept_agent = ConceptAgent()
        self.visual_director_agent = VisualDirectorAgent()
        self.prompt_refinement_agent = PromptRefinementAgent()
        self.qa_agent = QAAgent()
        self.continuity_agent = ContinuityControlAgent()
        self.generation_agent = GenerationAgent()
        
    async def process_request(self, request: GenerationRequest) -> GenerationResponse:
        logger.info(f"Starting orchestration for jewellery type: {request.jewellery_type}")
        
        # 0. Image Analysis
            
        logger.info("Executing Image Analysis Agent...")
        image_analysis = await self.image_analysis_agent.run(request.base64_image)
        visual_context = image_analysis.visual_context_summary
        logger.info(f"Visual Context Generated: {visual_context[:50]}...")
        
        # 1. Concept Generation
        logger.info("Executing Concept Agent...")
        # Construct concept input from new fields + visual context + description
        concept_input = (
            f"Jewellery Type: {request.jewellery_type}\n"
            f"Target Gender: {request.gender}\n"
            f"Video Theme: {request.video_type}\n"
            f"Model Included: {request.is_model}\n"
            f"Music Enabled: {request.is_music}\n"
            f"Duration: {request.duration} seconds\n"
            f"Product Description: {request.product_description or 'No description provided.'}\n"
            f"Visual Analysis: {visual_context}"
        )
        
        concept = await self.concept_agent.run(concept_input)
        
        # 2. Visual Direction
        logger.info("Executing Visual Director Agent...")
        # Visual Director needs visual context to plan lighting/camera
        visual_plan = await self.visual_director_agent.run(concept, visual_context=visual_context)
        
        # 3. Prompt Refinement Loop
        feedback = None
        final_prompt_output = None
        qa_score = 0.0
        max_iterations = 3
        iterations = 0
        
        # We need to capture continuity output for storage
        last_continuity_output = None
        last_qa_output = None
        
        for i in range(max_iterations):
            iterations = i + 1
            logger.info(f"Refinement Iteration {iterations}...")
            
            # Generate Prompt
            final_prompt_output = await self.prompt_refinement_agent.run(
                concept, visual_plan, feedback
            )
            
            # QA (Creative)
            qa_description = f"Target: {request.video_type} video for {request.jewellery_type}. Description: {request.product_description or 'None'}"
            qa_output = await self.qa_agent.run(
                final_prompt_output, qa_description
            )
            last_qa_output = qa_output
            qa_score = qa_output.score
            logger.info(f"QA Score: {qa_score}")
            
            if not qa_output.approved:
                logger.info(f"QA Rejected. Creative Feedback: {qa_output.feedback}")
                feedback = f"QA Creative Feedback: {qa_output.feedback}"
                continue
            
            # Continuity Control (Strict)
            logger.info("Executing Continuity Control Agent...")
            continuity_output = await self.continuity_agent.run(
                 final_prompt=final_prompt_output,
                 visual_plan=visual_plan,
                 is_model=request.is_model,
                 video_type=request.video_type
            )
            last_continuity_output = continuity_output

            if not continuity_output.approved:
                 logger.info(f"Continuity Rejected. Violation: {continuity_output.violation_type}")
                 feedback = f"STRICT RULE VIOLATION ({continuity_output.violation_type}): {continuity_output.feedback}"
                 continue

            # If both pass
            logger.info("QA and Continuity Approved.")
            break
            
        # 4. Video Generation
        if qa_score < 9.0:
            logger.warning(f"Proceeding with QA score {qa_score} after max retries.")
            
        logger.info("Executing Generation Agent...")
        generation_result = await self.generation_agent.run(
            prompt=final_prompt_output.final_prompt,
            image_url=request.base64_image, # Passing base64 directly as per plan/instruction
            video_type=request.video_type,
            duration=request.duration,
            is_music=request.is_music,
            is_model=request.is_model
        )
        
        # 5. Asset Storage
        await self._save_assets(
            generation_id=generation_result.generation_id,
            video_url=generation_result.video_url,
            concept=concept.model_dump(),
            visual_plan=visual_plan.model_dump(),
            final_prompt=final_prompt_output.model_dump(),
            qa_output=last_qa_output.model_dump() if last_qa_output else {},
            continuity_output=last_continuity_output.model_dump() if last_continuity_output else {}
        )
        
        return GenerationResponse(
            video_url=generation_result.video_url,
            generation_id=generation_result.generation_id,
            status=generation_result.status,
            concept=concept.model_dump(),
            visual_plan=visual_plan.model_dump(),
            final_prompt=final_prompt_output.final_prompt,
            qa_score=qa_score,
            feedback_iterations=iterations
        )

    async def _save_assets(self, generation_id: str, video_url: str, concept: Dict, visual_plan: Dict, final_prompt: Dict, qa_output: Dict, continuity_output: Dict):
        """
        Saves all generation assets to a local directory.
        """
        base_dir = "video_assets"
        generation_dir = os.path.join(base_dir, generation_id)
        
        try:
            os.makedirs(generation_dir, exist_ok=True)
            logger.info(f"Created asset directory: {generation_dir}")
            
            # Save JSON artifacts
            artifacts = {
                "concept.json": concept,
                "visual_plan.json": visual_plan,
                "final_prompt.json": final_prompt,
                "qa_output.json": qa_output,
                "continuity_output.json": continuity_output
            }
            
            for filename, data in artifacts.items():
                async with aiofiles.open(os.path.join(generation_dir, filename), "w") as f:
                    await f.write(json.dumps(data, indent=2))
            
            # Download and save video
            if video_url:
                logger.info(f"Downloading video from {video_url}...")
                async with httpx.AsyncClient() as client:
                    response = await client.get(video_url)
                    response.raise_for_status()
                    
                    video_path = os.path.join(generation_dir, "video.mp4")
                    async with aiofiles.open(video_path, "wb") as f:
                        await f.write(response.content)
                    logger.info(f"Video saved to {video_path}")
                    
        except Exception as e:
            logger.error(f"Failed to save assets for generation {generation_id}: {str(e)}", exc_info=True)
            # We don't raise here to avoid failing the response if storage fails
