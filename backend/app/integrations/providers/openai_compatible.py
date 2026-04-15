import json
from dataclasses import dataclass
from urllib import error, request


@dataclass
class OpenAICompatibleConfig:
    provider_name: str
    base_url: str
    api_key: str


@dataclass
class OpenAICompatibleResult:
    provider_name: str
    model_name: str
    content: str
    raw_response: dict
    finish_reason: str | None
    usage: dict


class OpenAICompatibleClient:
    def __init__(self, config: OpenAICompatibleConfig) -> None:
        self.config = config

    def chat(
        self,
        *,
        model_name: str,
        messages: list[dict],
        temperature: float = 0.9,
        max_tokens: int = 1200,
    ) -> OpenAICompatibleResult:
        base_url = self.config.base_url.rstrip("/")
        endpoint = f"{base_url}/chat/completions"

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        http_request = request.Request(
            endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=60) as response:
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"{self.config.provider_name} returned HTTP {exc.code}: {body}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(
                f"Failed to connect to provider {self.config.provider_name}: {exc.reason}"
            ) from exc

        parsed = json.loads(body)
        choices = parsed.get("choices") or []
        if not choices:
            raise RuntimeError(
                f"{self.config.provider_name} returned no choices: {parsed}"
            )

        first_choice = choices[0]
        message = first_choice.get("message") or {}
        content = message.get("content") or ""

        return OpenAICompatibleResult(
            provider_name=self.config.provider_name,
            model_name=model_name,
            content=content,
            raw_response=parsed,
            finish_reason=first_choice.get("finish_reason"),
            usage=parsed.get("usage") or {},
        )
