from app.core.config import get_settings
from app.core.exceptions import AppError
from app.integrations.providers.openai_compatible import (
    OpenAICompatibleClient,
    OpenAICompatibleConfig,
)
from app.schemas.models import ModelChatRequest, ModelChatResponse


MODEL_PROVIDER_RULES: list[tuple[tuple[str, ...], str]] = [
    (("qwen", "qwq"), "qwen"),
    (("deepseek",), "deepseek"),
    (("kimi", "moonshot"), "kimi"),
    (("claude",), "claude"),
]


class ModelRouterService:
    def _resolve_provider_name(self, model_name: str) -> str:
        normalized = model_name.strip().lower()
        for prefixes, provider_name in MODEL_PROVIDER_RULES:
            if normalized.startswith(prefixes):
                return provider_name
        raise AppError(f"Unsupported model routing target: {model_name}", 400)

    def _build_provider_config(self, provider_name: str) -> OpenAICompatibleConfig:
        settings = get_settings()

        provider_map = {
            "qwen": (settings.qwen_api_url, settings.qwen_api_key),
            "deepseek": (settings.deepseek_api_url, settings.deepseek_api_key),
            "kimi": (settings.kimi_api_url, settings.kimi_api_key),
            "claude": (settings.claude_api_url, settings.claude_api_key),
        }

        base_url, api_key = provider_map[provider_name]
        if not base_url or not api_key:
            raise AppError(
                f"Provider config is missing for {provider_name}. "
                f"Please check .env settings.",
                500,
            )

        return OpenAICompatibleConfig(
            provider_name=provider_name,
            base_url=base_url,
            api_key=api_key,
        )

    def chat(self, payload: ModelChatRequest) -> ModelChatResponse:
        provider_name = self._resolve_provider_name(payload.model_name)
        config = self._build_provider_config(provider_name)
        client = OpenAICompatibleClient(config)

        try:
            result = client.chat(
                model_name=payload.model_name,
                messages=payload.messages,
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
            )
        except RuntimeError as exc:
            raise AppError(str(exc), 502) from exc

        return ModelChatResponse(
            provider_name=result.provider_name,
            model_name=result.model_name,
            content=result.content,
            raw_response=result.raw_response,
            finish_reason=result.finish_reason,
            usage=result.usage,
        )
