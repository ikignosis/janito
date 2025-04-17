import importlib
import os

# Dynamically import all tool modules in this directory (except __init__.py and tool_base.py)
_tool_dir = os.path.dirname(__file__)
for fname in os.listdir(_tool_dir):
    if fname.endswith('.py') and fname not in ('__init__.py', 'tool_base.py'):
        modname = fname[:-3]
        importlib.import_module(f'janito.agent.tools.{modname}')
