from abc import ABC, abstractmethod
from typing import Any, Dict, Type, TypeVar, Optional
import json
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T', bound=BaseModel)

class BaseAgent(ABC):
    def __init__(self, model: str = settings.OPENAI_MODEL):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model
        self.name = self.__class__.__name__

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for the agent."""
        pass

    async def execute(self, input_data: Any, response_model: Type[T], context: Optional[Dict] = None, image_url: Optional[str] = None) -> T:
        """
        Executes the agent with the given input and returns a structured response.
        Supports multimodal input if image_url is provided.
        """
        # Use vision-capable model if image is provided
        current_model = self.model
        is_vision = False
        if image_url:
            is_vision = True
            # Force gpt-4o only if current model is known older text-only model (like gpt-3.5)
            # but usually we can trust the configured model if it's modern
            if not any(v in self.model.lower() for v in ["gpt-4", "4o", "4.1", "vision"]):
                current_model = "gpt-4o"
        
        logger.info(f"Agent {self.name} starting execution {'(Vision Mode)' if is_vision else ''}")
        
        # Initialize system prompt
        system_prompt = self.get_system_prompt()

        # Append JSON schema to system prompt for clarity
        json_schema = json.dumps(response_model.model_json_schema(), indent=2)
        system_prompt += f"\n\nRequired JSON Schema:\n{json_schema}"
        
        user_text = self._format_user_input(input_data, context)
        
        # Prepare content for multimodal or text-only
        if image_url:
            user_content = [
                {"type": "text", "text": user_text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_url}" if not image_url.startswith(("http", "data:")) else image_url
                    }
                }
            ]
        else:
            user_content = user_text
        
        try:
            response = await self.client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            refusal = getattr(response.choices[0].message, 'refusal', None)
            finish_reason = response.choices[0].finish_reason
            
            if not content:
                logger.error(f"Agent {self.name} received empty content. Finish reason: {finish_reason}, Refusal: {refusal}")
                logger.error(f"Full OpenAI response on error: {response.model_dump_json()}")
                
                if refusal:
                    raise ValueError(f"OpenAI Refusal: {refusal}")
                if finish_reason == "content_filter":
                    raise ValueError("OpenAI response was filtered due to content policy.")
                raise ValueError(f"Empty response from OpenAI (Finish Reason: {finish_reason})")

            logger.info(f"Agent {self.name} raw response received (Size: {len(content)} chars)")
            
            # Parse JSON
            parsed_json = json.loads(content)
            
            # Validate with Pydantic
            validated_output = response_model.model_validate(parsed_json)
            
            logger.info(f"Agent {self.name} execution successful")
            return validated_output

        except Exception as e:
            logger.error(f"Error in agent {self.name}: {str(e)}", exc_info=True)
            raise

    def _format_user_input(self, input_data: Any, context: Optional[Dict]) -> str:
        """
        Format the user input and context into a string prompt.
        Can be overridden by subclasses.
        """
        prompt = f"Input: {str(input_data)}\n"
        if context:
            prompt += f"Context: {json.dumps(context, default=str)}\n"
        
        prompt += "\nPlease provide your response in valid JSON format matching the required schema."
        return prompt
