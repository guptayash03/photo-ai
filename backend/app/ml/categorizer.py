import base64
import json
import logging

import google.generativeai as genai

from app.config import get_settings

logger = logging.getLogger(__name__)

CATEGORIES = [
    "document", "prescription", "receipt", "people",
    "travel", "pet", "food", "nature", "other"
]

CATEGORIZATION_PROMPT = """Analyze this image and classify it into exactly ONE of these categories:
- document: scanned documents, pages of text, printed papers, ID cards
- prescription: medical prescriptions, pharmacy labels, medication instructions
- receipt: shopping receipts, bills, invoices, purchase records
- people: photos of people, group photos, portraits, selfies
- travel: travel photos, landmarks, scenic views, vacation photos, cityscapes
- pet: photos of pets or animals (dogs, cats, birds, etc.)
- food: photos of food, meals, restaurants, cooking
- nature: landscapes, flowers, trees, sunsets, natural scenery without people
- other: anything that doesn't fit the above categories

Respond ONLY with a JSON object in this exact format:
{"category": "<category_name>", "confidence": <0.0-1.0>}

Do not include any other text."""


class ImageCategorizer:
    _model = None

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            settings = get_settings()
            genai.configure(api_key=None)  # Uses GOOGLE_APPLICATION_CREDENTIALS
            cls._model = genai.GenerativeModel(settings.GEMINI_MODEL)
        return cls._model

    async def categorize(self, image_bytes: bytes) -> tuple[str, float]:
        try:
            model = self._get_model()
            image_part = {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            }
            response = model.generate_content(
                [CATEGORIZATION_PROMPT, image_part],
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=100,
                ),
            )

            result_text = response.text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1].rsplit("```", 1)[0]

            result = json.loads(result_text)
            category = result.get("category", "other")
            confidence = float(result.get("confidence", 0.5))

            if category not in CATEGORIES:
                category = "other"

            return category, confidence

        except Exception as e:
            logger.warning(f"Gemini categorization failed: {e}")
            return "other", 0.0
