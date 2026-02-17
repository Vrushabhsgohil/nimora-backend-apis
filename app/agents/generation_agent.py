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
    
    # ---------------------------------------------------------------------------
    # Background color selection based on jewellery tonality in the prompt.
    # Called once and the result is threaded through every prompt section so
    # every agent layer speaks the same language and Vidu never gets mixed signals.
    # ---------------------------------------------------------------------------
    @staticmethod
    def _resolve_background(prompt: str) -> dict:
        """
        Inspect the prompt for metal/stone keywords and return a tight dict that
        describes the exact background to use.  Returning a dict keeps the data
        structured so downstream f-strings stay readable.

        Returns:
            {
                "color":       str  – e.g. "pure matte black"
                "hex":         str  – e.g. "#0A0A0A"
                "description": str  – single sentence used verbatim in the prompt
                "surface":     str  – physical material for the cyclorama
            }
        """
        p = prompt.lower()

        # Light / white metals & clear stones → very dark background for max contrast
        light_metal_keywords = [
            "silver", "platinum", "white gold", "palladium",
            "diamond", "moissanite", "white sapphire", "clear stone"
        ]
        # Warm / dark metals & coloured stones → light / neutral background
        warm_metal_keywords = [
            "yellow gold", "rose gold", "22k gold", "18k gold", "24k gold",
            "emerald", "ruby", "red stone", "green stone", "antique gold",
            "bronze", "copper tone"
        ]

        is_light = any(k in p for k in light_metal_keywords)
        is_warm  = any(k in p for k in warm_metal_keywords)

        if is_light and not is_warm:
            return {
                "color":       "deep slate gray",
                "hex":         "#1C1C1C",
                "description": (
                    "premium textured deep slate gray stone surface, realistic mineral grain, "
                    "high-end matte stone finish, zero background variation, "
                    "perfectly stable stone texture, no color drift, background locked to #1C1C1C stone throughout"
                ),
                "surface": "textured slate gray stone cyclorama"
            }
        elif is_warm and not is_light:
            return {
                "color":       "warm parchment gray",
                "hex":         "#E8E8E8",
                "description": (
                    "elegant light ash gray silk fabric surface, realistic micro-weave texture, "
                    "soft premium fabric sheen, zero background variation, "
                    "perfectly uniform light gray surface, background locked to #E8E8E8 silk throughout"
                ),
                "surface": "light gray silk cyclorama"
            }
        elif is_light and is_warm:
            # Mixed piece → premium gray marble
            return {
                "color":       "polished smoke gray",
                "hex":         "#2F2F2F",
                "description": (
                    "premium polished smoke gray marble surface, subtle realistic mineral veining, "
                    "luxury stone texture, zero background variation, perfectly uniform gray marble, "
                    "no shifts in veining, background locked to #2F2F2F marble throughout"
                ),
                "surface": "polished gray marble cyclorama"
            }
        else:
            # Unknown / generic → premium charcoal stone
            return {
                "color":       "rich charcoal gray",
                "hex":         "#121212",
                "description": (
                    "solid rich charcoal gray textured volcanic stone surface, microscopic stone grain, "
                    "premium tactile finish, zero background variation, perfectly uniform charcoal surface, "
                    "no gradients, no color cast, background locked to #121212 stone throughout"
                ),
                "surface": "charcoal gray textured stone cyclorama"
            }

    async def run(self, prompt: str, image_url: str, video_type: str = "promotional", duration: int = 10, is_music: bool = True, is_model: bool = True) -> GenerationOutput:
        """
        Generates a video using WaveSpeed Vidu Q3.
        """
        start_time = time.time()

        # ── 1. Resolve background once; reuse everywhere ─────────────────────
        bg = self._resolve_background(prompt)

        # ── 2. Audio prompt ───────────────────────────────────────────────────
        audio_prompt = ""
        if is_music:
            if video_type.lower() == "ugc":
                audio_prompt = ", soft ambient background music, warm, casual, feel-good, no vocals"
            else:
                audio_prompt = ", elegant luxury background score, cinematic, premium, sophisticated, no vocals"

        # ── 3. Model / no-model prompt ────────────────────────────────────────
        model_prompt = ""
        if is_model:
            if video_type.lower() == "ugc":
                model_prompt = (
                    ", woman wearing the jewellery appropriately on her body, candid moment, "
                    "real skin texture with visible pores, authentic pose, casual-elegant, "
                    "jewellery is perfectly fitted and properly worn"
                )
            else:
                model_prompt = (
                    ", high-end fashion model, elegant slow-motion pose, premium styling, "
                    "showcasing the jewellery by wearing it properly on her body, "
                    "realistic skin textures, high-fidelity human detail, "
                    "jewellery is perfectly positioned and worn naturally"
                )
        else:
            if video_type.lower() == "ugc":
                model_prompt = (
                    ", no people, no human, lifestyle flat-lay, "
                    "product on natural stone or wooden surface, cinematic close-up"
                )
            else:
                model_prompt = (
                    f", no people, no human, product only, "
                    f"product centered on {bg['surface']}, "
                    f"majestic ultra-slow 360-degree turntable rotation, "
                    f"product resting on high-end {bg['surface']}, "
                    f"background remains {bg['color']} in every single frame"
                )

        # ── 4. Style / background prompt ─────────────────────────────────────
        if video_type.lower() == "ugc":
            style_prompt = (
                ", natural daylight, warm golden hour tones, real-world lifestyle setting, "
                "authentic cinematic aesthetic, soft natural bokeh, "
                "slow-motion handheld breathing, photorealistic 8k, "
                "tactile textures, emotionally relatable"
            )
        else:
            if is_model:
                # Lifestyle background for models even in ecommerce
                style_prompt = (
                    ", elegant luxury lifestyle background, high-end interior setting, "
                    "cinematic lighting, premium editorial aesthetic, "
                    "ultra-slow constant-speed orbital camera movement, "
                    "cinematic depth of field, realistic environment, "
                    "luxurious atmosphere, photorealistic 8k"
                )
            else:
                # Solid background only for product-only shots
                style_prompt = (
                    f", {bg['description']}, "
                    f"background does NOT change colour or texture at any point, "
                    f"background remains {bg['color']} from first frame to last frame, "
                    "soft cinematic top-down key light plus subtle side fill, "
                    "ultra-slow constant-speed 360-degree orbital camera orbit, "
                    "macro detailing of diamond facets and physically accurate metal reflections, "
                    "perfectly centered product framing, cinematic depth of field, "
                    "no harsh shadows, premium ecommerce hero-commercial aesthetic, "
                    "physically accurate diamond sparkle, high-polish metal surface reflections, "
                    "majestic product showcase, no vignetting on background edges"
                )

        # ── 5. Product-lock block (injected verbatim, high token weight) ─────
        #    Repeated key phrases are intentional — repetition raises attention
        #    weight in diffusion-based models including Vidu Q3.
        product_lock = (
            "PRODUCT CONSISTENCY ABSOLUTE LOCK: "
            "the jewellery piece is 100% identical to the reference image in every frame, "
            "exact same shape, exact same stone count, exact same stone placement, "
            "exact same metal colour, exact same proportions, exact same design details, "
            "static product geometry throughout, no morphing whatsoever, "
            "no redesign, no extra stones, no missing stones, no size change, "
            "no style drift, subject locked to reference image, "
            "preserve every engraving and filigree detail as seen in reference, "
            "stone facets identical to reference, metal grain identical to reference"
        )

        # ── 6. Background-lock block ─────────────────────────────────────────
        background_lock = (
            f"BACKGROUND CONSISTENCY ABSOLUTE LOCK: "
            f"background is {bg['color']} (hex {bg['hex']}) and must NOT change in any frame, "
            f"zero background colour drift, zero background texture change, "
            f"no fade to different colour, no gradient appearing mid-video, "
            f"background remains perfectly uniform {bg['color']} from frame 0 to final frame, "
            f"background and product DO NOT swap or blend at any point"
        )

        # ── 7. Model-lock block (only if model consistency is enabled) ──────
        model_lock = ""
        if is_model:
            model_lock = (
                "MODEL CONSISTENCY ABSOLUTE LOCK: "
                "The human model's facial features, hair style, skin tone, and body proportions "
                "must remain 100% identical in every frame. Zero facial morphing, zero feature drift, "
                "clothing remains exactly the same throughout, preserve stable human identity."
            )

        # ── 8. Assemble full enhanced prompt ──────────────────────────────────
        enhanced_prompt = (
            f"{prompt}"
            f"{audio_prompt}"
            f"{model_prompt}"
            f"{style_prompt}, "
            f"8k resolution, RAW photo quality, photorealistic masterpiece, "
            f"physically accurate reflections, realistic sparkle, no artificial glow, "
            f"preserve metal grain texture and stone facet shapes, "
            f"avoid overexposure, avoid artificial blur, "
            f"super slow motion 120fps, majestic cinematic drift, "
            f"zero jitter, no sudden cuts, no fast zoom. "
            f"{product_lock}. "
            f"{background_lock}"
            f"{f'. {model_lock}' if model_lock else ''}."
        )

        # ── 8. Movement amplitude ─────────────────────────────────────────────
        # "small" for UGC keeps subtle handheld feel; "auto" for ecommerce
        # allows the smooth orbital rotation to play out.
        movement_amp = "auto" if video_type.lower() == "ecommerce" else "small"
        
        payload = {
            "prompt": enhanced_prompt,
            "image": image_url,
            "duration": duration,
            "resolution": "720p",
            "movement_amplitude": movement_amp,
            "generate_audio": is_music,
            # Disable Vidu's built-in prompt enhancer so our carefully engineered
            # prompt reaches the model unmodified — the enhancer can strip or
            # dilute the explicit background-lock and product-lock phrases.
            "enhance_prompt": False,
        }

        logger.info(f"Initiating video generation | type={video_type} | model={is_model} | bg={bg['color']}")
        logger.debug(f"Full enhanced prompt ({len(enhanced_prompt)} chars): {enhanced_prompt}")
        
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