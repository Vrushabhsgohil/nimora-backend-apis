import asyncio
import httpx
import time
from typing import Any, Dict, Optional
from pydantic import ValidationError

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.agents import GenerationOutput

logger = get_logger(__name__)

class GenerationAgent:
    def __init__(self):
        self.api_key = settings.VIDU_API_KEY
        self.base_url = settings.VIDU_API_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def run(self, prompt: str, image_url: str, video_type: str = "promotional", duration: int = 10, is_music: bool = True, is_model: bool = True) -> GenerationOutput:
        """
        Generates a video using WaveSpeed Vidu Q3.
        """
        start_time = time.time()
        
        # Audio prompt injection
        audio_prompt = ""
        if is_music:
            if video_type.lower() == "ugc":
                 audio_prompt = ", soft ambient background music, warm, casual, feel-good, no vocals"
            else:  # ecommerce
                 audio_prompt = ", elegant luxury background score, cinematic, premium, sophisticated, no vocals"
        
        # Model prompt injection
        model_prompt = ""
        if is_model:
            if video_type.lower() == "ugc":
                model_prompt = ", woman wearing the jewellery naturally, candid moment, real skin texture, authentic pose, casual-elegant"
            else:  # ecommerce
                model_prompt = ", fashion model, elegant pose, premium styling, showcasing the jewellery, realistic skin texture"
        else:
            if video_type.lower() == "ugc":
                model_prompt = ", no people, no human, lifestyle flat-lay, product on casual surface, coffee table aesthetic"
            else:  # ecommerce
                model_prompt = (
                    ", no people, no human, product only, centered on solid contrasting studio background, "
                    "smooth 360 degree turntable rotation, product floating or resting on solid cyclorama surface"
                )
        
        # Video-type-specific visual style
        if video_type.lower() == "ugc":
            style_prompt = (
                ", natural daylight, window light, warm natural tones, real-world setting, "
                "authentic candid aesthetic, soft depth of field, subtle handheld camera feel, "
                "social-media-ready, emotionally relatable, lifestyle photography"
            )
        else:  # ecommerce
            style_prompt = (
                ", solid contrasting studio background, soft even top lighting with subtle side fill, "
                "smooth constant-speed 360 degree orbital rotation around the product, "
                "macro detailing of diamond facets and metal reflections during orbit, "
                "centered product framing, shallow depth of field, "
                "no harsh shadows, premium ecommerce hero-banner aesthetic, "
                "high-detail diamond sparkle, gold surface reflections, "
                "solid seamless studio cyclorama backdrop, product turntable showcase"
            )
        
        enhanced_prompt = (
            f"{prompt}{audio_prompt}{model_prompt}{style_prompt}, 8k resolution, highly detailed, "
            f"maintain 100% consistent product appearance, subject is locked to reference image, do not alter subject, "
            f"NO morphing, NO distortion, NO redesign, static geometry, sharp focus, rich colors, luxury aesthetic, "
            f"physically accurate reflections, realistic sparkle, no artificial glow, "
            f"preserve metal texture and stone shapes, avoid overexposure, avoid artificial blur, "
            f"slow smooth movement, no sudden cuts, no fast zoom"
        )
        
        # Movement amplitude: auto for ecommerce (allow smooth orbit), small for UGC
        movement_amp = "auto" if video_type.lower() == "ecommerce" else "small"
        
        payload = {
            "prompt": enhanced_prompt,
            "image": image_url,
            "duration": duration, 
            "resolution": "720p", 
            "movement_amplitude": movement_amp,
            "generate_audio": is_music
        }
        
        logger.info(f"Initiating video generation with prompt: {prompt[:50]}...")
        
        # Use a longer timeout as per user code (30s connect, but let's keep 120s total for safety in async)
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                # 1. Trigger Generation
                # User code uses: response = requests.post(url, ...)
                response = await client.post(
                    f"{self.base_url}/vidu/q3/image-to-video",
                    json=payload,
                    headers=self.headers
                )
                
                if response.status_code not in [200, 201]:
                    logger.error(f"WaveSpeed submission failed: {response.text}")
                    response.raise_for_status()

                data = response.json()
                # User code logic: inner = data.get("data", {}) if "data" in data else data
                inner = data.get("data", {}) if "data" in data else data
                
                generation_id = inner.get("id")
                # User code logic: poll_url = inner.get("urls", {}).get("get")
                poll_url = inner.get("urls", {}).get("get")
                
                if not generation_id:
                     raise ValueError(f"No generation ID returned: {data}")

                logger.info(f"Generation ID: {generation_id}")

                # 2. Poll for completion
                return await self._poll_generation(client, generation_id, poll_url, start_time)
                
            except httpx.HTTPError as e:
                logger.error(f"HTTP Error during generation: {str(e)}")
                if hasattr(e, 'response') and e.response:
                    logger.error(f"Response: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error in GenerationAgent: {str(e)}")
                raise

    async def _poll_generation(self, client: httpx.AsyncClient, generation_id: str, poll_url: Optional[str] = None, start_time: float = 0.0) -> GenerationOutput:
        # Increase retries to 10 minutes (300 * 2s = 600s)
        max_retries = 300 
        # User code uses poll_url or default construction
        url = poll_url or f"{self.base_url}/predictions/{generation_id}"
        
        for i in range(max_retries):
            # User code uses: requests.get(url, ...)
            response = await client.get(
                url,
                headers=self.headers
            )
            
            if response.status_code != 200:
                await asyncio.sleep(2)
                continue
            
            data = response.json()
            # User code logic: inner = data.get("data", {}) if "data" in data else data
            inner = data.get("data", {}) if "data" in data else data
            
            status = inner.get("status")

            # Log progress every 30 seconds (15 retries * 2s)
            if (i + 1) % 15 == 0:
                logger.info(f"Still polling generation {generation_id}... (Attempt {i+1}/{max_retries}, Status: {status})")
            
            if status == "completed" or status == "success":
                # User logic: output = inner.get("outputs") or inner.get("output")
                output = inner.get("outputs") or inner.get("output")
                
                # User logic: video_url = output[0] if isinstance(output, list) and output else output
                video_url = output[0] if isinstance(output, list) and output else output
                
                if not video_url:
                     # Fallback check
                     video_url = inner.get("url") or inner.get("video_url")

                if not video_url:
                    raise RuntimeError("Job completed but no URL returned")
                
                end_time = time.time()
                generation_time = end_time - start_time
                logger.info(f"Video generation completed in {generation_time:.2f} seconds")
                    
                return GenerationOutput(
                    video_url=video_url,
                    generation_id=generation_id,
                    status="success"
                )
            elif status in ["failed", "canceled"]:
                error_msg = inner.get("error", "Unknown error")
                raise RuntimeError(f"Generation failed: {error_msg}")
            
            await asyncio.sleep(2)
            
        raise TimeoutError(f"Generation timed out polling after {max_retries * 2} seconds.")
