from google.cloud import translate_v3 as translate
from typing import Optional
import logging
from ..config.settings import settings

logger = logging.getLogger(__name__)


class TranslatorService:
    """Service for translating text using Google Cloud Translation API v3."""

    def __init__(self):
        self.client = translate.TranslationServiceClient()
        self.project_id = settings.gcp_project_id
        self.location = settings.gcp_location

        # ECI terminology glossary for consistent translations
        self.glossary = {
            "BLO": "बूथ स्तरीय अधिकारी",
            "ERO": "निर्वाचन निबंधन अधिकारी",
            "Form 6": "प्रपत्र 6",
            "Form 8": "प्रपत्र 8",
            "EPIC": "मतदाता पहचान पत्र",
            "Voter ID": "मतदाता पहचान पत्र",
            "Constituency": "निर्वाचन क्षेत्र",
            "Polling Station": "मतदान केंद्र",
        }

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "en",
    ) -> Optional[str]:
        """
        Translate text to target language.
        Returns translated text or None if translation fails.
        """
        if target_language == source_language:
            return text

        try:
            parent = f"projects/{self.project_id}/locations/{self.location}"

            # Check if text contains glossary terms
            for term, translation in self.glossary.items():
                if term.lower() in text.lower():
                    # Simple replacement for glossary terms
                    text = text.replace(term, translation)

            response = self.client.translate_text(
                request={
                    "parent": parent,
                    "contents": [text],
                    "mime_type": "text/plain",
                    "source_language_code": source_language,
                    "target_language_code": target_language,
                }
            )

            if response.translations:
                return response.translations[0].translated_text

            return None

        except Exception as e:
            logger.error(f"Translation error: {e}")
            return None

    def get_supported_languages(self) -> list[str]:
        """Return list of supported language codes."""
        return ["en", "hi", "mr", "ta", "te", "bn", "kn", "gu", "pa"]


# Singleton instance
translator_service = TranslatorService()
