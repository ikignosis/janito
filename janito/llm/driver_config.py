from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class LLMDriverConfig:
    # For OpenAI and similar providers that distinguish between completion and response tokens
    max_completion_tokens: Optional[int] = None
    verbose_api: Optional[bool] = None
    verbose_http: Optional[bool] = None
    """
    Common configuration container for LLM drivers.
    - verbose_api: Print API trace info if set
    - verbose_http: Enable HTTP debugging if set
    
    Holds standard attributes that most LLM drivers require (used as a config or schema reference object).
    Inspired by the OpenAI driver, but fields are generic for most LLM backends.
    """
    model: str = None  # Model is required but can be set from CLI
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    stop: Optional[Any] = None  # list or string, depending on backend
    reasoning_effort: Optional[str] = None
    extra: dict = field(
        default_factory=dict
    )  # for provider-specific miscellaneous config fields

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d.update(d.pop("extra", {}))
        # Remove Nones (for compatibility)
        return {k: v for k, v in d.items() if v is not None}
