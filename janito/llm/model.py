from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class LLMModelInfo:
    name: str
    context: Any = "N/A"
    max_input: Any = "N/A"
    max_cot: Any = "N/A"
    max_response: Any = "N/A"
    thinking_supported: Any = "N/A"
    thinking: bool = False
    default_temp: float = 0.2
    open: Optional[Any] = None
    category: Optional[str] = None
    driver: Optional[str] = None
    # This enables arbitrary provider-specific metadata
    other: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        if not self.open:
            d.pop("open")
        if not self.category:
            d.pop("category")
        if not self.driver:
            d.pop("driver")
        if not self.other:
            d.pop("other")
        return d

    @staticmethod
    def get_model_info(model_specs):
        """
        Standard get_model_info implementation for all providers:
        returns a list of model info dicts, one per model in the given MODEL_SPECS dict.
        """
        return [m.to_dict() for m in model_specs.values()]
