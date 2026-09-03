import anthropic

from app.core.config import settings


class LLMService:
    """Service for interacting with Anthropic Claude LLM."""

    def __init__(self) -> None:
        self.client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
        )

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate a response using Anthropic Messages API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            system_prompt: System instructions and RAG context for the model.
            max_tokens: Maximum response tokens.

        Returns:
            Extracted text content from the assistant's reply.
        """
        response = await self.client.messages.create(
            model=settings.claude_model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        )

        first_block = response.content[0]
        if hasattr(first_block, "text"):
            return first_block.text
        return str(first_block)
