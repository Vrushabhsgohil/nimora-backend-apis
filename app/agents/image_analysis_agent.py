from typing import Any, Dict, Type, Optional
import json
from app.agents.base_agent import BaseAgent
from app.schemas.agents import ImageAnalysisOutput
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class ImageAnalysisAgent(BaseAgent):
    def __init__(self):
        # Override model to use a vision-capable model
        super().__init__(model="gpt-4o")

    def get_system_prompt(self) -> str:
        return """You are an EXPERT Jewellery Analyst and Gemologist.
Your goal is to analyze a product image and provide a highly detailed, technical description of the jewellery piece.
This description will be used by a film crew to recreate the piece in a cinematic video.

Your output MUST be a JSON object adhering to the ImageAnalysisOutput schema.

### 🔍 Analysis Guidelines
1.  **Jewellery Type**: Identify if it's a Ring, Necklace, Earring, Bracelet, etc.
2.  **Materials**: Identify the metal (Gold - 18k/24k, Platinum, Rose Gold, Silver) and finish (Polished, Brushed, Matte).
3.  **Gemstones**: Identify all stones (Diamond, Emerald, Ruby, etc.), their cut (Round, Princess, Oval), setting (Prong, Bezel, Pave), and estimated visual quality.
4.  **Design & Style**: Describe the aesthetic (Modern, Vintage, Art Deco, Traditional Indian, Minimalist).
5.  **Detailed Features**: Note any engravings, filigree, milgrain, or unique structural elements.
6.  **Color Palette**: Describe the dominant colors of the metal and stones.

### 🚫 Constraints
-   Do NOT hallucinate features not visible in the image.
-   Be precise with terminology.
-   If immediate details are unclear, describe appearance (e.g., "clear stone" instead of "diamond").

Input will be a Base64 encoded image string.
"""

    async def run(self, image_base64: str) -> ImageAnalysisOutput:
        """
        Executes the agent with the given base64 image input.
        """
        return await self.execute(
            input_data="Analyze this jewellery image and provide a technical description.", 
            response_model=ImageAnalysisOutput, 
            image_url=image_base64
        )
