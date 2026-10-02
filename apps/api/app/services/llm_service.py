from app.core.config import settings
from app.schemas.verification import VerificationResponse


def generate_explanation(result: VerificationResponse) -> str:
    """Optional LLM layer.

    The MVP intentionally falls back to deterministic text when no provider is configured.
    Keep the LLM separate from the verification engine so model output never becomes the
    only source of truth.
    """
    if not settings.llm_enabled or not settings.openai_api_key:
        return result.explanation

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        prompt = (
            "Explain this supplier verification result in plain language. "
            "Do not invent facts. Make clear that the result is decision support, not certification.\n\n"
            + result.model_dump_json(indent=2)
        )
        response = client.responses.create(
            model=settings.openai_model,
            input=prompt,
        )
        return response.output_text.strip() or result.explanation
    except Exception:
        return result.explanation
