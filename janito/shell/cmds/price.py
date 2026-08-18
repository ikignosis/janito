"""
/price command handler - displays per-model pricing for every built-in model.

Usage:
    /price

Renders a table with one row per built-in model: the provider, the model
name, and the estimated cost of a notional request of **1M input tokens
(cache miss) + 1M cached input tokens + 1M output tokens**, sorted by
cost from max to min.  The cost column is computed by the provider's
cost module (``janito.providers.<name>.cost``, the ``cost_*`` rate tables) via
:func:`janito.provider_accessors.get_provider_cost` with
``is_reference=True``, so reference (e.g. peak) rates apply and the returned
string carries no rate-band suffix (e.g. DeepSeek's ``(off-peak)``/``(peak)``
annotation).  Providers/models without a cost module show ``N/A``.
"""

from rich.console import Console
from rich.table import Table

from .base import CmdHandler
from .registry import register_command

#: The notional usage behind the price column: 1M input tokens (cache miss),
#: 1M cached input tokens and 1M output tokens.
_MILLION = 1_000_000


def _parse_cost(cost_str: str) -> float:
    """Parse a cost string into a float for sorting; returns -inf for N/A or invalid."""
    try:
        cleaned = cost_str.replace("$", "").split()[0]
        return float(cleaned)
    except (ValueError, IndexError, AttributeError):
        return float("-inf")


class PriceCmdHandler(CmdHandler):
    """Command handler for /price command."""

    @property
    def name(self) -> str:
        return "/price"

    def handle(self, shell, user_input: str) -> bool:
        """Handle the /price command."""
        if user_input.strip().lower() == self.name.lower():
            self._show_prices()
            return True
        return False

    @staticmethod
    def _show_prices() -> None:
        """Print a per-model pricing table for every built-in model."""
        from janito.provider_accessors import get_provider_cost
        from janito.provider_registry import _registry
        from janito.provider_validation import list_supported_providers

        table = Table(
            title="Model Pricing (per 1M tokens)",
            title_style="bold",
            header_style="bold cyan",
            box=None,
            pad_edge=False,
        )
        table.add_column("Provider", style="green", no_wrap=True)
        table.add_column("Model", style="cyan", no_wrap=True)
        table.add_column("1M in + 1M cache + 1M out", justify="right", no_wrap=True)

        rows: list[tuple[str, str, str]] = []
        for provider in list_supported_providers():
            found = _registry.get(provider)
            if found is None:
                continue
            for model in sorted(found.model_names()):
                cost = get_provider_cost(
                    provider,
                    model,
                    _MILLION,
                    _MILLION,
                    _MILLION,
                    is_reference=True,
                )
                rows.append((provider, model, cost))

        rows.sort(key=lambda item: _parse_cost(item[2]), reverse=True)

        for provider, model, cost in rows:
            table.add_row(provider, model, cost)
        Console(markup=False).print(table)


# Register this handler
_handler = PriceCmdHandler()
register_command(_handler)
