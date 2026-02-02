"""LLM service with support for Anthropic Claude and Ollama."""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from anthropic import AnthropicError, AsyncAnthropic

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.7
    ) -> tuple[str, int | None]:
        """
        Generate a response from the LLM.

        Args:
            system_prompt: System prompt for context
            user_prompt: User's question
            temperature: Temperature for generation (0-1)

        Returns:
            Tuple of (response_text, tokens_used)
        """
        pass

    @abstractmethod
    async def generate_stream(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.7
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Generate a streaming response from the LLM.

        Args:
            system_prompt: System prompt for context
            user_prompt: User's question
            temperature: Temperature for generation (0-1)

        Yields:
            dict: Event data with 'type' and 'data' keys
        """
        if False:
            yield

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name."""
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str | None = None):
        """Initialize Anthropic client."""
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")

        self.client = AsyncAnthropic(api_key=self.api_key)
        self.model = settings.ANTHROPIC_MODEL
        self.max_tokens = settings.ANTHROPIC_MAX_TOKENS

    async def generate(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.7
    ) -> tuple[str, int | None]:
        """Generate response using Claude."""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            # Extract text from response
            response_text = ""
            for block in message.content:
                if hasattr(block, "text"):
                    response_text += block.text

            # Get token usage
            tokens_used = None
            if hasattr(message, "usage"):
                tokens_used = message.usage.input_tokens + message.usage.output_tokens

            return response_text, tokens_used

        except AnthropicError as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    async def generate_stream(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.7
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Generate streaming response using Claude.

        Yields:
            dict: Event data with 'type' and 'data' keys
                - type: 'token' (text chunk), 'usage' (token stats), 'error' (error info)
                - data: The actual content
        """
        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield {"type": "token", "data": text}

                # Get final message for usage stats
                final_message = await stream.get_final_message()
                if hasattr(final_message, "usage"):
                    yield {
                        "type": "usage",
                        "data": {
                            "input_tokens": final_message.usage.input_tokens,
                            "output_tokens": final_message.usage.output_tokens,
                            "total_tokens": final_message.usage.input_tokens
                            + final_message.usage.output_tokens,
                        },
                    }

        except AnthropicError as e:
            logger.error(f"Anthropic streaming API error: {e}")
            yield {"type": "error", "data": str(e)}
            raise

    def get_provider_name(self) -> str:
        return "anthropic"

    def get_model_name(self) -> str:
        return self.model


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        """Initialize Ollama client."""
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT

    async def generate(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.7
    ) -> tuple[str, int | None]:
        """Generate response using Ollama."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": f"{system_prompt}\n\nUser: {user_prompt}\n\nAssistant:",
                        "stream": False,
                        "options": {"temperature": temperature},
                    },
                )
                response.raise_for_status()
                result = response.json()

                return result.get("response", ""), None

        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            raise

    async def generate_stream(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.7
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Generate streaming response using Ollama.

        Yields:
            dict: Event data with 'type' and 'data' keys
        """
        try:
            async with (
                httpx.AsyncClient(timeout=self.timeout) as client,
                client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": f"{system_prompt}\n\nUser: {user_prompt}\n\nAssistant:",
                        "stream": True,
                        "options": {"temperature": temperature},
                    },
                ) as response,
            ):
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line:
                        import json

                        data = json.loads(line)

                        if "response" in data:
                            yield {"type": "token", "data": data["response"]}

                        if data.get("done", False):
                            # Ollama doesn't provide token counts
                            yield {"type": "usage", "data": {"total_tokens": None}}

        except httpx.HTTPError as e:
            logger.error(f"Ollama streaming API error: {e}")
            yield {"type": "error", "data": str(e)}
            raise

    def get_provider_name(self) -> str:
        return "ollama"

    def get_model_name(self) -> str:
        return self.model


class LLMService:
    """
    LLM service with automatic fallback between providers.

    Tries primary provider first, falls back to secondary if enabled.
    """

    def __init__(self):
        """Initialize LLM service with configured providers."""
        self.primary_provider = self._create_provider(settings.LLM_PROVIDER)
        self.fallback_enabled = settings.LLM_FALLBACK_ENABLED

        # print("✅ LLM connected successfully")
        # print(f"   Host: {self.primary_provider}:{settings.OLLAMA_BASE_URL}")

        # Create fallback provider if enabled
        self.fallback_provider = None
        if self.fallback_enabled:
            fallback_type = "ollama" if settings.LLM_PROVIDER == "anthropic" else "anthropic"
            try:
                self.fallback_provider = self._create_provider(fallback_type)
                logger.info(f"LLM fallback enabled: {settings.LLM_PROVIDER} -> {fallback_type}")
            except Exception as e:
                logger.warning(f"Failed to initialize fallback provider: {e}")
                self.fallback_enabled = False

    def _create_provider(self, provider_type: str) -> LLMProvider:
        """Create an LLM provider instance."""
        if provider_type == "anthropic":
            return AnthropicProvider()
        elif provider_type == "ollama":
            return OllamaProvider()
        else:
            raise ValueError(f"Unknown LLM provider: {provider_type}")

    async def generate(
        self, system_prompt: str, user_prompt: str, temperature: float | None = None
    ) -> tuple[str, str, str, int | None]:
        """
        Generate response with automatic fallback.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            temperature: Temperature override (uses config default if None)

        Returns:
            Tuple of (response_text, provider_name, model_name, tokens_used)
        """
        temp = temperature if temperature is not None else settings.ANTHROPIC_TEMPERATURE

        # Try primary provider
        try:
            logger.info(
                f"Generating with primary provider: {self.primary_provider.get_provider_name()}"
            )
            response, tokens = await self.primary_provider.generate(
                system_prompt, user_prompt, temp
            )
            return (
                response,
                self.primary_provider.get_provider_name(),
                self.primary_provider.get_model_name(),
                tokens,
            )

        except Exception as e:
            logger.warning(f"Primary provider failed: {e}")

            # Try fallback if enabled
            if self.fallback_enabled and self.fallback_provider:
                try:
                    logger.info(
                        f"Trying fallback provider: {self.fallback_provider.get_provider_name()}"
                    )
                    response, tokens = await self.fallback_provider.generate(
                        system_prompt, user_prompt, temp
                    )
                    return (
                        response,
                        self.fallback_provider.get_provider_name(),
                        self.fallback_provider.get_model_name(),
                        tokens,
                    )
                except Exception as fallback_error:
                    logger.error(f"Fallback provider also failed: {fallback_error}")
                    raise RuntimeError(
                        f"Both LLM providers failed. Primary: {e}, Fallback: {fallback_error}"
                    ) from fallback_error

            # No fallback available
            raise RuntimeError(f"LLM generation failed: {e}") from e

    async def generate_stream(
        self, system_prompt: str, user_prompt: str, temperature: float | None = None
    ):
        """
        Generate streaming response with automatic fallback.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            temperature: Temperature override (uses config default if None)

        Yields:
            dict: Event data with 'type', 'data', 'provider', and 'model' keys
        """
        temp = temperature if temperature is not None else settings.ANTHROPIC_TEMPERATURE

        # Try primary provider
        try:
            logger.info(
                f"Streaming with primary provider: {self.primary_provider.get_provider_name()}"
            )

            async for event in self.primary_provider.generate_stream(
                system_prompt, user_prompt, temp
            ):
                # Add provider and model info to events
                event["provider"] = self.primary_provider.get_provider_name()
                event["model"] = self.primary_provider.get_model_name()
                yield event

        except Exception as e:
            logger.warning(f"Primary provider streaming failed: {e}")

            # Try fallback if enabled
            if self.fallback_enabled and self.fallback_provider:
                try:
                    logger.info(
                        f"Trying fallback provider: {self.fallback_provider.get_provider_name()}"
                    )

                    async for event in self.fallback_provider.generate_stream(
                        system_prompt, user_prompt, temp
                    ):
                        event["provider"] = self.fallback_provider.get_provider_name()
                        event["model"] = self.fallback_provider.get_model_name()
                        yield event

                except Exception as fallback_error:
                    logger.error(f"Fallback provider streaming also failed: {fallback_error}")
                    yield {
                        "type": "error",
                        "data": f"Both providers failed. Primary: {e}, Fallback: {fallback_error}",
                        "provider": "none",
                        "model": "none",
                    }
                    raise RuntimeError(
                        f"Both LLM providers failed. Primary: {e}, Fallback: {fallback_error}"
                    ) from fallback_error

            # No fallback available
            yield {
                "type": "error",
                "data": f"LLM generation failed: {e}",
                "provider": "none",
                "model": "none",
            }
            raise RuntimeError(f"LLM generation failed: {e}") from e
