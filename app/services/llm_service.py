import logging
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional

import anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

BOOKING_TOOL: dict[str, Any] = {
    "name": "book_interview",
    "description": (
        "Book and schedule an interview when the user provides their full name, email address, "
        "interview date (YYYY-MM-DD), and interview time (HH:MM). "
        "Call this tool only when all four parameters are provided by the user."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Full name of the person scheduling the interview.",
            },
            "email": {
                "type": "string",
                "description": "Valid email address of the candidate.",
            },
            "interview_date": {
                "type": "string",
                "description": "Date of the interview in YYYY-MM-DD format.",
            },
            "interview_time": {
                "type": "string",
                "description": "Time of the interview in HH:MM format (24-hour clock).",
            },
        },
        "required": ["name", "email", "interview_date", "interview_time"],
    },
}


@dataclass
class LLMResponse:
    """Structured response from LLM containing text and any tool calls."""

    text: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def __iter__(self):
        return iter((self.text, self.tool_calls))

    def __str__(self) -> str:
        return self.text


class LLMService:
    """Service for interacting with Anthropic Claude LLM with tool calling and query rewriting."""

    def __init__(self) -> None:
        self.client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
        )

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """
        Generate a response using Anthropic Messages API with optional tool use.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            system_prompt: System instructions and RAG context for the model.
            tools: Optional tool definitions for Anthropic Function Calling.
            max_tokens: Maximum response tokens.

        Returns:
            LLMResponse object containing text and list of tool calls.
        """
        kwargs: dict[str, Any] = {
            "model": settings.claude_model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = await self.client.messages.create(**kwargs)

        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for block in response.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
            elif getattr(block, "type", None) == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        return LLMResponse(
            text="".join(text_parts).strip(),
            tool_calls=tool_calls,
        )

    async def generate_response_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[tuple[str, Any], None]:
        """
        Stream response events using Anthropic Messages API.

        Yields tuples of (event_type, payload):
          - ("token", str_token)
          - ("tool_calls", list[dict])
        """
        kwargs: dict[str, Any] = {
            "model": settings.claude_model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield ("token", text)

            final_message = await stream.get_final_message()
            tool_calls: list[dict[str, Any]] = []
            for block in final_message.content:
                if getattr(block, "type", None) == "tool_use":
                    tool_calls.append(
                        {
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )
            if tool_calls:
                yield ("tool_calls", tool_calls)

    async def rewrite_query(
        self,
        message: str,
        history: list[dict[str, str]],
    ) -> str:
        """
        Reformulate a multi-turn user message into a standalone search query for vector retrieval.
        Resolves pronouns (it, its, this, that, they) based on recent context.
        """
        if not history or not message.strip():
            return message

        # Use the last 6 turns for fast and token-efficient context
        recent_history = history[-6:]
        formatted_history = "\n".join(
            f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}"
            for m in recent_history
        )

        prompt = (
            f"Conversation history:\n{formatted_history}\n\n"
            f"Latest user message: {message}\n\n"
            "Rewrite the latest user message into a concise, standalone search query for document retrieval. "
            "Resolve all ambiguous pronouns (such as it, its, this, that, they, these) using the conversation context. "
            "Do NOT answer the question. Return ONLY the rewritten query text without extra commentary."
        )

        try:
            response = await self.client.messages.create(
                model=settings.claude_model,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )
            first_block = response.content[0]
            rewritten = getattr(first_block, "text", str(first_block)).strip()
            # Strip outer quotation marks if model returned quoted string
            if (rewritten.startswith('"') and rewritten.endswith('"')) or (
                rewritten.startswith("'") and rewritten.endswith("'")
            ):
                rewritten = rewritten[1:-1].strip()

            if rewritten:
                logger.info(f"Rewrote query '{message}' -> '{rewritten}'")
                return rewritten
            return message
        except Exception as exc:
            logger.warning(f"Query rewriting failed, using original query: {exc}")
            return message


