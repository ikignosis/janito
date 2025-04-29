import sys
import os

sys.path.insert(0, os.path.abspath("."))
from janito.agent.tools.get_file_outline import GetFileOutlineTool

tool = GetFileOutlineTool()
result = tool.run("janito/agent/profile_manager.py")
print(result)
