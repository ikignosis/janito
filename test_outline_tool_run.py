import sys
import os

sys.path.insert(0, os.path.abspath("."))
from janito.agent.tools.outline_file import GetFileOutlineTool

tool = GetFileOutlineTool()
result = tool.call("janito/agent/profile_manager.py")
print(result)
