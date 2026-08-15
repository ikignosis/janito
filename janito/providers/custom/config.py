"""Built-in configuration for the special "custom" provider.

``PROVIDER_CONFIG`` is the config entry for ``custom``: unlike
every other provider it has no built-in endpoint and no built-in default
model (and therefore no built-in model entries) -- both must be supplied
via config (``--set endpoint=...``, ``--set model=...``).  See
:mod:`janito.providers.template.config` for the full reference of every
CONFIG option.
"""

# Marker for the special "custom" provider: its endpoint is not built in and
# must be supplied via config (--set endpoint).
CUSTOM_ENDPOINT_MARKER = "CUSTOM_ENDPOINT"

#: The config entry for the ``custom`` provider.
PROVIDER_CONFIG: dict = {
    "default_model": None,
    "endpoint": CUSTOM_ENDPOINT_MARKER,
    "models": {},
}
