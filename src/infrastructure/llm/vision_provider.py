import base64
from typing import Optional
from openai import OpenAI
from logger import setup_logger
from config import OPENAI_API_KEY

logger = setup_logger(__name__)

class VisionProvider:
    """
    Handles image analysis to extract news claims using GPT-4o-mini Vision.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key or OPENAI_API_KEY)
        self.model = "gpt-4o-mini"

    def extract_claim(self, image_bytes: bytes) -> Optional[str]:
        """
        Takes image bytes, encodes to base64, and asks GPT-4o-mini to extract the core claim.
        """
        try:
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert OSINT analyst. Your task is to extract the primary factual claim "
                            "from any news post or social media screenshot provided. "
                            "Focus strictly on WHAT is being claimed. "
                            "Return ONLY the extracted claim as a single concise sentence. "
                            "If multiple claims exist, pick the most significant one. "
                            "If no claim is found, return an empty string."
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract the core claim from this image:"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "low" # Saves tokens, enough for text extraction
                                },
                            },
                        ],
                    }
                ],
                max_tokens=100,
            )
            
            claim = response.choices[0].message.content.strip()
            logger.info("Extracted claim from image: %s", claim)
            return claim if claim else None
            
        except Exception as e:
            logger.error("Vision analysis failed: %s", e)
            return None

# Singleton instance
vision_provider = VisionProvider()
