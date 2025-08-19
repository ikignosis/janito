"""
ProviderRegistry: Handles provider listing and selection logic for janito CLI.
"""

from rich.table import Table
from janito.cli.console import shared_console
from janito.providers.registry import LLMProviderRegistry
from janito.llm.auth import LLMAuthManager
import sys
from janito.exceptions import MissingProviderSelectionException


class ProviderRegistry:
    def list_providers(self):
        """List all supported LLM providers as a table using rich, showing if auth is configured and supported model names."""
        providers = self._get_provider_names()
        table = self._create_table()
        rows = self._get_all_provider_rows(providers)
        self._add_rows_to_table(table, rows)
        self._print_table(table)

    def _get_provider_names(self):
        from janito.providers.registry import LLMProviderRegistry

        return LLMProviderRegistry.list_providers()

    def _create_table(self):
        table = Table(title="Supported LLM Providers")
        table.add_column("Provider", style="cyan")
        table.add_column("Maintainer", style="yellow", justify="center")
        table.add_column("Model Names", style="magenta")
        return table

    def _get_all_provider_rows(self, providers):
        rows = []
        for p in providers:
            info = self._get_provider_info(p)
            # info is (provider_name, maintainer, model_names, skip)
            if len(info) == 4 and info[3]:
                continue  # skip providers flagged as not implemented
            rows.append(info[:3])

        # Group providers by openness (open-source first, then proprietary)
        open_providers = {"cerebras", "deepseek", "alibaba", "moonshot", "zai"}

        def sort_key(row):
            provider_name = row[0]
            is_open = provider_name in open_providers
            # Sort open providers alphabetically first, then proprietary alphabetically
            return (not is_open, provider_name)

        rows.sort(key=sort_key)
        return rows

    def _add_rows_to_table(self, table, rows):
        for idx, (p, maintainer, model_names) in enumerate(rows):
            table.add_row(p, maintainer, model_names)
            if idx != len(rows) - 1:
                table.add_section()

    def _print_table(self, table):
        """Print the table using rich when running in a terminal; otherwise fall back to a plain ASCII listing.
        This avoids UnicodeDecodeError when the parent process captures the output with a non-UTF8 encoding.
        """
        import sys

        if sys.stdout.isatty():
            # Safe to use rich's unicode output when attached to an interactive terminal.
            shared_console.print(table)
            return

        # Fallback: plain ASCII output (render without rich formatting)
        print("Supported LLM Providers")
        # Build header from column titles
        header_titles = [column.header or "" for column in table.columns]
        print(" | ".join(header_titles))
        # rich.table.Row objects in recent Rich versions don't expose a public `.cells` attribute.
        # Instead, cell content is stored in each column's private `_cells` list.
        for row_index, _ in enumerate(table.rows):
            cells_text = [str(column._cells[row_index]) for column in table.columns]
            ascii_row = " | ".join(cells_text).encode("ascii", "ignore").decode("ascii")
            print(ascii_row)

    def _get_provider_info(self, provider_name):
        provider_class = LLMProviderRegistry.get(provider_name)
        maintainer = getattr(provider_class, "MAINTAINER", "-")
        maintainer = f"👤 {maintainer}" if maintainer != "-" else maintainer
        model_names = self._get_model_names(provider_name)
        skip = False
        return (provider_name, maintainer, model_names, skip)

    def _get_model_names(self, provider_name):
        try:
            provider_class = LLMProviderRegistry.get(provider_name)
            module_parts = provider_class.__module__.split(".")
            # Build the correct import path: janito.providers.{provider}.model_info
            model_info_module = f"janito.providers.{provider_name}.model_info"
            model_info_mod = __import__(model_info_module, fromlist=["MODEL_SPECS"])

            # Handle different model spec variable names
            model_specs = None
            if hasattr(model_info_mod, "MODEL_SPECS"):
                model_specs = model_info_mod.MODEL_SPECS
            elif hasattr(model_info_mod, "MOONSHOT_MODEL_SPECS"):
                model_specs = model_info_mod.MOONSHOT_MODEL_SPECS

            if model_specs:
                default_model = getattr(provider_class, "DEFAULT_MODEL", None)
                model_names = []

                for model_key in model_specs.keys():
                    if model_key == default_model:
                        # Highlight the default model with color and star icon
                        model_names.append(f"[bold green]⭐ {model_key}[/bold green]")
                    else:
                        model_names.append(model_key)

                if provider_name == "moonshot":
                    return ", ".join(model_names)
                return ", ".join(model_names)
            return "-"
        except Exception as e:
            return "-"

    def _maintainer_sort_key(self, row):
        maint = row[1]
        is_needs_maint = "Needs maintainer" in maint
        return (is_needs_maint, row[2] != "✅ Auth")

    def get_provider(self, provider_name):
        """Return the provider class for the given provider name. Returns None if not found."""
        from janito.providers.registry import LLMProviderRegistry

        if not provider_name:
            print("Error: Provider name must be specified.")
            return None
        provider_class = LLMProviderRegistry.get(provider_name)
        if provider_class is None:
            available = ", ".join(LLMProviderRegistry.list_providers())
            print(
                f"Error: Provider '{provider_name}' is not recognized. Available providers: {available}."
            )
            return None
        return provider_class

    def get_instance(self, provider_name, config=None):
        """Return an instance of the provider for the given provider name, optionally passing a config object. Returns None if not found."""
        provider_class = self.get_provider(provider_name)
        if provider_class is None:
            return None
        if config is not None:
            return provider_class(config=config)
        return provider_class()


# For backward compatibility
def list_providers():
    """Legacy function for listing providers, now uses ProviderRegistry class."""
    ProviderRegistry().list_providers()
