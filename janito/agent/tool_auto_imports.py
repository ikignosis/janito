# janito/agent/tool_auto_imports.py
# This module imports all tool modules to ensure they are registered via their decorators.
# It should be imported only where tool auto-registration is needed, to avoid circular import issues.

import importlib
import pkgutil
from pathlib import Path

TOOLS_DIR = Path(__file__).parent / "tools"
PACKAGE_PREFIX = "janito.agent.tools."

for finder, name, ispkg in pkgutil.iter_modules([str(TOOLS_DIR)]):
    if name.startswith("_") or not name.endswith((".py", "")):
        continue
    # Avoid importing __init__.py or non-python files
    if name == "__init__":
        continue
    module_name = PACKAGE_PREFIX + name
    importlib.import_module(module_name)
